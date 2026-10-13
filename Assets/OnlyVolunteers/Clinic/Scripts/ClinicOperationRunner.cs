using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Clinic
{
    // The operation on the map (Field Clinic loop): the existing three-step cartoon kidney mini-game (Operation/
    // KidneyMiniGame: cut along the dotted line, pull it out, three strips of duct tape) on the table's stand-in, run with
    // the map's first-person KCC player instead of the OperationTest walker. Gameplay abstraction only, no medicine.
    // - Begin: AtBase -> InOperation. The player stands still with a free cursor (KccFirstPersonInput.MovementLocked /
    //   LookSuspended, like the phone); the hands (grab, E/Q, inventory) and the phone are off. The view camera blends to
    //   the table's overhead anchor; this runs after the KCC's LateUpdate (execution order), so its pose wins each frame.
    // - Esc before the kidney is out: cancelled, InOperation -> AtBase, the patient stays strapped on the table, E retries.
    //   Once it is out the tape step finishes the job (Esc only reminds).
    // - Done: grade = the patient's starting grade lowered by the mini-game's penalty (OrganGrading), money =
    //   OrganGrading.UnitValue(kidney base value, grade). PatientRegistry.TryResolve pays exactly once per PatientId; then
    //   the camera blends back, controls return, and the stand-in leaves the table.
    // The organ is paid for at once (a buyer is not in the loop yet); it does not go into the inventory.
    [DefaultExecutionOrder(10000)]
    public sealed class ClinicOperationRunner : MonoBehaviour
    {
        private enum Phase { Idle, CameraIn, MiniGame, CameraOut }

        public float CameraBlendSeconds = 0.45f;

        private readonly List<(string text, Vector3 world, Color color, float born)> _comics = new();
        private readonly List<(Behaviour behaviour, bool wasEnabled)> _hands = new();

        private PatientRegistry _registry;
        private ClinicStation _station;
        private PatientRecord _record;
        private GreyboxPawn _pawn;
        private KccFirstPersonInput _kcc;
        private Camera _camera;
        private KidneyMiniGame _game;
        private Phase _phase;
        private float _blend;
        private float _startedAt;
        private bool _finished;
        private Vector3 _fromPosition;
        private Quaternion _fromRotation;
        private int _kidneyBaseValue = 250;

        public bool Active => _phase != Phase.Idle;
        public KidneyMiniGame Game => _game;
        public string Status { get; private set; } = "";
        /// <summary>Paid for this operation (0 if the reward was refused as a repeat).</summary>
        public System.Action<PatientRecord, int, OrganQuality, string> Finished;
        public System.Action<PatientRecord> Cancelled;

        public void Init(PatientRegistry registry, ClinicStation station, ItemDefinition kidney)
        {
            _registry = registry;
            _station = station;
            if (kidney != null) _kidneyBaseValue = kidney.BaseValue;
        }

        public int RewardFor(OrganQuality quality) => OrganGrading.UnitValue(_kidneyBaseValue, quality);

        public bool Begin(GreyboxPawn pawn, ClinicStation station, PatientRecord record)
        {
            if (Active || pawn == null || pawn.ViewCamera == null || station.Patient == null || !station.Table.Ready) return false;
            if (!pawn.TryGetComponent(out _kcc)) _kcc = pawn.GetComponentInChildren<KccFirstPersonInput>();
            PhoneController phone = FindAnyObjectByType<PhoneController>();
            if (phone != null && phone.IsOpen) return false;
            if (!_registry.Move(record, PatientStage.InOperation)) return false;
            _pawn = pawn;
            _record = record;
            _camera = pawn.ViewCamera;
            _finished = false;
            LockPlayer(true, phone);
            station.SetMood(ClinicStation.Mood.Operating);
            _fromPosition = _camera.transform.position;
            _fromRotation = _camera.transform.rotation;
            _blend = 0f;
            _phase = Phase.CameraIn;
            _startedAt = Time.time;
            Status = "";
            return true;
        }

        private void Update()
        {
            if (_phase != Phase.MiniGame || _game == null) return;
            Mouse mouse = Mouse.current;
            Keyboard keyboard = Keyboard.current;
            if (mouse == null || keyboard == null) return;
            if (keyboard.escapeKey.wasPressedThisFrame)
            {
                if (_game.Current == KidneyMiniGame.Step.Cut || _game.Current == KidneyMiniGame.Step.Pull)
                {
                    Cancel();
                    return;
                }
                Comic("Сначала заклей скотчем!", _station.Patient.transform.position + Vector3.up * 0.5f, new Color(1f, 0.85f, 0.3f));
            }
            if (_game.Current == KidneyMiniGame.Step.Tape && _game.PoppedKidney != null) LaunchKidney();
            if (_game.Tick(mouse, keyboard)) Finish();
        }

        // After KccFirstPersonInput.LateUpdate (execution order 10000): the view camera's pose is ours while operating.
        private void LateUpdate()
        {
            if (_phase == Phase.Idle || _camera == null) return;
            Transform anchor = _station.Table.CameraAnchor;
            Transform cam = _camera.transform;
            switch (_phase)
            {
                case Phase.CameraIn:
                    if (Blend(_fromPosition, _fromRotation, anchor.position, anchor.rotation))
                    {
                        _phase = Phase.MiniGame;
                        _game = new KidneyMiniGame(_station.Patient, false, _camera, _station.Audio, Comic);
                    }
                    break;
                case Phase.MiniGame:
                    cam.SetPositionAndRotation(anchor.position, anchor.rotation);
                    break;
                case Phase.CameraOut:
                    // The KCC put the eye pose on the camera this frame: blend from the table view to it.
                    if (Blend(anchor.position, anchor.rotation, cam.position, cam.rotation)) End();
                    break;
            }
            _comics.RemoveAll(c => Time.time - c.born > 1.1f);
        }

        private bool Blend(Vector3 fromPos, Quaternion fromRot, Vector3 toPos, Quaternion toRot)
        {
            _blend = Mathf.Min(1f, _blend + Time.deltaTime / Mathf.Max(0.05f, CameraBlendSeconds));
            float t = Mathf.SmoothStep(0f, 1f, _blend);
            _camera.transform.SetPositionAndRotation(Vector3.Lerp(fromPos, toPos, t), Quaternion.Slerp(fromRot, toRot, t));
            return _blend >= 1f;
        }

        // The kidney leaves the body as soon as it pops (the tape step goes on meanwhile), as in OperationSession.
        private void LaunchKidney()
        {
            Transform organ = _game.PoppedKidney;
            _station.Patient.TakeKidney();
            _game.ClearPoppedKidney();
            OrganPop.Launch(organ, _camera, null);
        }

        private void Finish()
        {
            _game.Cleanup(true);
            OrganQuality grade = OrganGrading.Lower(_record.Quality, _game.Penalty);
            int value = RewardFor(grade);
            bool paid = _registry.TryResolve(_record, value);
            string verdict = _game.Penalty == 0 ? "Чистая работа!" : _game.Yanked ? "Рывок помял почку" : "Разрез вышел кривым";
            Status = $"Почка [{OrganGrading.Label(grade)}] за {Time.time - _startedAt:0} с. {verdict}";
            _finished = true;
            _game = null;
            Finished?.Invoke(_record, paid ? value : 0, grade, Status);
            StartOut();
        }

        private void Cancel()
        {
            _game.Cleanup(false);
            _game = null;
            _registry.Move(_record, PatientStage.AtBase);
            Status = "Операция отменена: пациент ждёт на столе (E — снова)";
            Cancelled?.Invoke(_record);
            StartOut();
        }

        private void StartOut()
        {
            _blend = 0f;
            _phase = Phase.CameraOut;
        }

        private void End()
        {
            _phase = Phase.Idle;
            LockPlayer(false, null);
            if (_finished) _station.Discharge();
            else _station.SetMood(ClinicStation.Mood.Waiting);
            _record = null;
            _pawn = null;
            _camera = null;
        }

        // The player stands still with a free cursor; hands and phone are off and come back as they were.
        private void LockPlayer(bool locked, PhoneController phone)
        {
            if (locked)
            {
                _hands.Clear();
                Hold(_pawn.GetComponentInChildren<GreyboxInteractor>(true)); // first: its OnDisable re-enables the inventory
                Hold(_pawn.GetComponentInChildren<InventoryInput>(true));
                Hold(_pawn.GetComponentInChildren<PhysicsGrabber>(true));
                Hold(phone);
                if (_kcc != null)
                {
                    _kcc.MovementLocked = true;
                    _kcc.LookSuspended = true;
                }
                return;
            }
            if (_kcc != null)
            {
                _kcc.MovementLocked = false;
                _kcc.LookSuspended = false;
            }
            for (int i = _hands.Count - 1; i >= 0; i--)
                if (_hands[i].behaviour != null) _hands[i].behaviour.enabled = _hands[i].wasEnabled;
            _hands.Clear();
        }

        private void Hold(Behaviour behaviour)
        {
            if (behaviour == null) return;
            _hands.Add((behaviour, behaviour.enabled));
            behaviour.enabled = false;
        }

        private void Comic(string text, Vector3 world, Color color) => _comics.Add((text, world, color, Time.time));

        private void OnGUI()
        {
            if (_phase == Phase.MiniGame && _game != null)
            {
                OperationGui.Shadowed(new Rect(0f, 18f, Screen.width, 60f), _game.Instruction, OperationGui.Center(22), Color.white);
                if (_game.Current == KidneyMiniGame.Step.Pull)
                {
                    var back = new Rect(Screen.width * 0.5f - 160f, 80f, 320f, 16f);
                    GUI.Box(back, "");
                    Color old = GUI.color;
                    GUI.color = Color.Lerp(new Color(0.4f, 0.9f, 0.4f), new Color(1f, 0.4f, 0.3f), _game.Tension);
                    GUI.DrawTexture(new Rect(back.x + 2f, back.y + 2f, (back.width - 4f) * Mathf.Clamp01(_game.Tension), back.height - 4f),
                        Texture2D.whiteTexture);
                    GUI.color = old;
                }
                string esc = _game.Current == KidneyMiniGame.Step.Tape ? "" : "[Esc] — отменить операцию (пациент останется на столе)";
                OperationGui.Shadowed(new Rect(0f, Screen.height - 46f, Screen.width, 30f), esc, OperationGui.Center(16), new Color(1f, 1f, 1f, 0.85f));
            }
            if (_camera == null) return;
            foreach (var comic in _comics)
            {
                Vector3 screen = _camera.WorldToScreenPoint(comic.world);
                if (screen.z <= 0f) continue;
                float age = Time.time - comic.born;
                var color = new Color(comic.color.r, comic.color.g, comic.color.b, Mathf.Clamp01(1.4f - age * 1.3f));
                OperationGui.Shadowed(new Rect(screen.x - 300f, Screen.height - screen.y - 60f - age * 60f, 600f, 60f), comic.text,
                    OperationGui.Center(Mathf.RoundToInt(Mathf.Lerp(40f, 30f, age))), color);
            }
        }

        private void OnDisable()
        {
            if (_phase != Phase.Idle && _pawn != null) LockPlayer(false, null);
        }
    }
}
