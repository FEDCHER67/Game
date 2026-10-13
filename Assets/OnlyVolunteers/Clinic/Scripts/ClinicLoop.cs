using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Clinic
{
    // Field Clinic loop on the map (docs/Progress.md, docs/NextAction.md): catch an NPC -> load it into the van -> drive
    // to the base -> drag it onto the receiving pad -> cartoon operation at the table -> money -> save.
    // The one scene object of the loop (Map_Look_v17_Play: FC_ClinicLoop, added by OnlyVolunteers/Clinic/Add Patient Loop
    // To Open Map Scene). At runtime it adds the parts: PatientRegistry (ids and stages), ClinicStation (pad, table, lamp,
    // beacon) with ClinicDropOff (hand-over) and ClinicOperationRunner (the operation), and here: the reward, the save
    // (ClinicSave: loaded on start, K = quick save, also saved after every reward) and the objective panel.
    // Offline like the rest of the map: nothing here is networked (FishNet is untouched).
    public sealed class ClinicLoop : MonoBehaviour
    {
        [Header("Base (plan metres X/Z; the height comes from the ground)")]
        public string BaseName = "B01 Вагон";
        public Vector2 PadXZ = new(205.5f, 176f);
        public Vector2 TableXZ = new(209.5f, 180.5f);
        public float TableYaw = 20f;
        public float PadRadius = 2.5f;
        [Tooltip("The van counts as 'at the base' within this distance of the pad (objective panel only).")]
        public float ArrivedRadius = 25f;

        [Header("Reward and save")]
        [Tooltip("Inventory/Items/Item_Kidney.asset: its base value prices the operation (250 if empty).")]
        public ItemDefinition KidneyItem;
        [Tooltip("Quick save (Input System key; K is free in the map's key registry).")]
        public Key QuickSave = Key.K;
        public bool LoadOnStart = true;
        public bool ShowPanel = true;

        private static readonly Color RewardColor = new(1f, 0.82f, 0.2f);

        private PatientRegistry _registry;
        private ClinicStation _station;
        private ClinicDropOff _dropOff;
        private ClinicOperationRunner _runner;
        private GreyboxPawn _pawn;
        private VanController _van;
        private VanUpgrades _upgrades;
        private LocalInventory _inventory;
        private VanCameraRig _vanCamera;
        private string _toast = "";
        private Color _toastColor = Color.white;
        private float _toastUntil;
        private int _treatedThisSession;
        private int _earnedThisSession;
        private GUIStyle _panelStyle;

        public PatientRegistry Registry => _registry;
        public ClinicStation Station => _station;
        public ClinicDropOff DropOff => _dropOff;
        public ClinicOperationRunner Runner => _runner;
        public LocalInventory Inventory => _inventory;
        public string LastSaveNote { get; private set; } = "";
        public string LastLoadNote { get; private set; } = "";

        private void Awake()
        {
            _pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            _van = FindAnyObjectByType<VanController>(FindObjectsInactive.Include);
            _upgrades = _van != null ? _van.GetComponent<VanUpgrades>() : null;
            _vanCamera = FindAnyObjectByType<VanCameraRig>(FindObjectsInactive.Include);
            _inventory = _pawn != null ? _pawn.GetComponentInChildren<LocalInventory>(true) : null;
            if (_inventory == null) _inventory = FindAnyObjectByType<LocalInventory>(FindObjectsInactive.Include);

            _registry = gameObject.AddComponent<PatientRegistry>();
            var stationObject = new GameObject("FC_ClinicStation");
            stationObject.transform.SetParent(transform, false);
            _station = stationObject.AddComponent<ClinicStation>();
            _dropOff = stationObject.AddComponent<ClinicDropOff>();
            _runner = stationObject.AddComponent<ClinicOperationRunner>();
            _runner.Init(_registry, _station, KidneyItem);
            _dropOff.Init(_registry, _station);
            _station.ViewCamera = ActiveCamera;
            _runner.Finished += OnOperationFinished;
            _runner.Cancelled += _ => Toast("Операция отменена — пациент ждёт на столе (E)", Color.white);
            _dropOff.Admitted += OnAdmitted;
            if (_pawn == null || _inventory == null)
                Debug.LogWarning("[Clinic] no map pawn or LocalInventory found: the loop needs a map Play scene (Map_Look_v17_Play).", this);
        }

        private void Start()
        {
            _station.Build(new Vector3(PadXZ.x, 0f, PadXZ.y), new Vector3(TableXZ.x, 0f, TableXZ.y), TableYaw, PadRadius, _runner);
            if (LoadOnStart) Load();
        }

        private void Update()
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard != null && QuickSave != Key.None && keyboard[QuickSave].wasPressedThisFrame) Save(true);
            if (_station != null && !_runner.Active)
            {
                if (_dropOff.Settling) _station.SetMood(ClinicStation.Mood.PadBusy);
                else _station.SetMood(_station.Busy ? ClinicStation.Mood.Waiting : ClinicStation.Mood.Idle);
            }
        }

        // ---------- Events ----------

        private void OnAdmitted(PatientRecord record)
        {
            Toast($"Пациент принят ({OrganGrading.Label(record.Quality)}): он на столе. Подойди к столу — E, операция", new Color(0.6f, 1f, 0.6f));
            Sfx.PlayAt(SfxIds.UiPickup, _station.PadCenter);
        }

        private void OnOperationFinished(PatientRecord record, int paid, OrganQuality grade, string status)
        {
            if (paid > 0 && _inventory != null && _inventory.Model != null)
            {
                _inventory.Model.AddCash(paid);
                _treatedThisSession++;
                _earnedThisSession += paid;
                Toast($"+${paid}  — скупщик забрал почку [{OrganGrading.Label(grade)}]\n{status}", RewardColor);
                Vector3 at = ActiveCamera() != null ? ActiveCamera().transform.position : _station.PadCenter;
                Sfx.PlayAt(SfxIds.CashRegister, at);
                _station.Flash(RewardColor, 2f);
                Save(false);
            }
            else
            {
                Toast($"{status}\nЗа этого пациента уже заплатили — второй награды нет", Color.white);
            }
        }

        // ---------- Save / load ----------

        public bool Save(bool announce)
        {
            var data = new ClinicSaveData
            {
                money = _inventory != null ? _inventory.Cash : 0,
                completedPatients = new List<string>(_registry.Completed),
                engineLevel = _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Engine) : 0,
                brakesLevel = _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Brakes) : 0,
                handlingLevel = _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Handling) : 0,
            };
            bool ok = ClinicSave.Write(data, out string error);
            LastSaveNote = ok ? $"saved ${data.money}, {data.completedPatients.Count} patients, upgrades {data.engineLevel}/{data.brakesLevel}/{data.handlingLevel}" : error;
            Debug.Log($"[Clinic] {LastSaveNote} -> {ClinicSave.FilePath}");
            if (announce) Toast(ok ? $"Сохранено: ${data.money}, вылечено {data.completedPatients.Count}" : $"Не сохранилось: {error}", ok ? Color.white : new Color(1f, 0.5f, 0.4f));
            return ok;
        }

        public bool Load()
        {
            if (!ClinicSave.TryRead(out ClinicSaveData data, out string note))
            {
                LastLoadNote = $"no save ({note}): new game";
                Debug.Log($"[Clinic] {LastLoadNote} ({ClinicSave.FilePath})");
                return false;
            }
            _registry.LoadCompleted(data.completedPatients);
            if (_inventory != null && _inventory.Model != null)
            {
                int cash = _inventory.Model.Cash;
                if (data.money > cash) _inventory.Model.AddCash(data.money - cash);
                else if (data.money < cash) _inventory.Model.TrySpendCash(cash - data.money);
            }
            if (_upgrades != null)
            {
                _upgrades.TrySetLevel(VanUpgradeCategory.Engine, data.engineLevel);
                _upgrades.TrySetLevel(VanUpgradeCategory.Brakes, data.brakesLevel);
                _upgrades.TrySetLevel(VanUpgradeCategory.Handling, data.handlingLevel);
            }
            LastLoadNote = $"loaded ${data.money}, {data.completedPatients.Count} patients, upgrades {data.engineLevel}/{data.brakesLevel}/{data.handlingLevel} ({note})";
            Debug.Log($"[Clinic] {LastLoadNote} <- {ClinicSave.FilePath}");
            Toast($"Загружено сохранение: ${data.money}, вылечено {data.completedPatients.Count}", Color.white);
            return true;
        }

        // ---------- HUD ----------

        private Camera ActiveCamera()
        {
            if (_pawn != null && _pawn.Controlled && _pawn.ViewCamera != null) return _pawn.ViewCamera;
            if (_vanCamera != null && _vanCamera.isActiveAndEnabled && _vanCamera.TryGetComponent(out Camera c)) return c;
            return Camera.main;
        }

        private void Toast(string text, Color color)
        {
            _toast = text;
            _toastColor = color;
            _toastUntil = Time.time + 5f;
        }

        // The most advanced patient still in play decides the current step.
        private PatientStage Furthest(out bool any)
        {
            any = false;
            PatientStage best = PatientStage.Available;
            foreach (PatientRecord r in _registry.Records)
            {
                if (r.Stage == PatientStage.Resolved || r.Stage == PatientStage.Available) continue;
                if (!any || r.Stage > best) best = r.Stage;
                any = true;
            }
            return best;
        }

        private void OnGUI()
        {
            if (Time.time < _toastUntil)
                OperationGui.Shadowed(new Rect(0f, Screen.height * 0.30f, Screen.width, 70f), _toast, OperationGui.Center(24), _toastColor);
            if (!ShowPanel || _runner == null || _runner.Active) return;

            PatientStage stage = Furthest(out bool any);
            Vector3 from = _pawn != null && _pawn.Controlled ? _pawn.Position : _van != null ? _van.transform.position : Vector3.zero;
            Vector3 to = _station.PadCenter - from;
            to.y = 0f;
            bool vanThere = _van != null && Vector3.Distance(Flat(_van.transform.position), Flat(_station.PadCenter)) <= ArrivedRadius;
            int step = !any ? 1
                : stage == PatientStage.Captured ? (vanThere ? 4 : 2)
                : stage == PatientStage.Loaded ? (vanThere ? 4 : 3)
                : 5;

            var lines = new[]
            {
                "1. Поймай NPC: Q — оглушить, ЛКМ — тащить",
                "2. Затащи тело в бусик (боковая или задняя дверь)",
                $"3. Вези на базу {BaseName}: {to.magnitude:0} м, {Compass(to)}",
                "4. Вытащи тело в круг ПРИЁМКИ и отпусти",
                "5. У стола E — операция → деньги",
            };
            var sb = new System.Text.StringBuilder("ПОЛЕВАЯ КЛИНИКА\n");
            for (int i = 0; i < lines.Length; i++)
                sb.Append(i + 1 < step ? "  [x] " : i + 1 == step ? "  >>  " : "  [ ] ").Append(lines[i]).Append('\n');
            int cash = _inventory != null ? _inventory.Cash : 0;
            sb.Append($"Деньги ${cash} · вылечено {_registry.Completed.Count} · {QuickSave} — сохранить");
            if (!string.IsNullOrEmpty(_dropOff.LastRefusal) && _dropOff.Settling) sb.Append('\n').Append(_dropOff.LastRefusal);

            _panelStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 14, wordWrap = false, richText = false };
            const float width = 440f;
            float height = 22f + 19f * (lines.Length + 2) + (_dropOff.Settling && _dropOff.LastRefusal.Length > 0 ? 19f : 0f);
            var box = new Rect(Screen.width - width - 10f, 10f, width, height);
            GUI.Box(box, GUIContent.none);
            GUI.Label(new Rect(box.x + 8f, box.y + 4f, width - 12f, height - 6f), sb.ToString(), _panelStyle);
        }

        private static string Compass(Vector3 direction)
        {
            if (direction.sqrMagnitude < 4f) return "здесь";
            string[] names = { "север", "северо-восток", "восток", "юго-восток", "юг", "юго-запад", "запад", "северо-запад" };
            float angle = Mathf.Repeat(Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg + 22.5f, 360f);
            return "на " + names[Mathf.Clamp((int)(angle / 45f), 0, 7)];
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
