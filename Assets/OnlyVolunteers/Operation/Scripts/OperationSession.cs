using System.Collections.Generic;
using OnlyVolunteers.Inventory;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// One operation at the table, offline: camera blends to the overhead view, the organ menu opens, the kidney
    /// mini-game runs, the kidney pops into the player's LocalInventory with a grade-based price, back to the menu.
    /// Esc in the menu ends the operation. Networking, the other organs and the co-op roles are in the draft only.
    /// </summary>
    public sealed class OperationSession : MonoBehaviour
    {
        private enum Phase
        {
            Idle,
            CameraIn,
            Menu,
            MiniGame,
            CameraOut,
        }

        private readonly struct OrganEntry
        {
            public readonly string Name;
            public readonly string Locked;

            public OrganEntry(string name, string locked)
            {
                Name = name;
                Locked = locked;
            }
        }

        // Unlock reasons follow docs/drafts/ECONOMY_PROGRESSION_DRAFT.md (tool levels), not approved.
        private static readonly OrganEntry[] LockedOrgans =
        {
            new OrganEntry("Печень", "в прототипе нет мини-игры"),
            new OrganEntry("Лёгкие", "нужен полевой скальпель (ур. 1)"),
            new OrganEntry("Сердце", "нужен скальпель ур. 2 и анестезия"),
            new OrganEntry("Глаза", "нужен профессиональный скальпель (ур. 3)"),
            new OrganEntry("Мозг", "нужен лазерный резак (ур. 5)"),
        };

        [SerializeField] private ItemDefinition kidneyItem;
        [SerializeField] private AudioSource sfx;
        [SerializeField, Min(0.1f)] private float cameraBlendSeconds = 0.45f;

        private readonly List<(string text, Vector3 world, Color color, float born)> comics =
            new List<(string, Vector3, Color, float)>();

        private Phase phase;
        private OperationTestPlayer player;
        private OperationTable table;
        private LocalInventory inventory;
        private KidneyMiniGame game;
        private Transform cam;
        private Transform camParent;
        private Vector3 camLocalPosition;
        private Quaternion camLocalRotation;
        private Vector3 blendFromPosition;
        private Quaternion blendFromRotation;
        private float blend;
        private float operationStarted;
        private string toast = "";
        private string lastItem = "";
        // Set when the tape step finishes before the kidney's flight lands: the arrival toast adds it under the item line.
        private string pendingSummary;
        private float toastUntil;

        public bool Active => phase != Phase.Idle;

        public void Configure(ItemDefinition kidney, AudioSource source)
        {
            kidneyItem = kidney;
            sfx = source;
        }

        public void Begin(OperationTestPlayer operatingPlayer, OperationTable operationTable)
        {
            if (Active || operatingPlayer == null || operatingPlayer.ViewCamera == null || !operationTable.Ready) return;
            player = operatingPlayer;
            table = operationTable;
            inventory = player.Inventory;
            player.ControlsEnabled = false;
            OperationTestPlayer.LockCursor(false);

            cam = player.ViewCamera.transform;
            camParent = cam.parent;
            camLocalPosition = cam.localPosition;
            camLocalRotation = cam.localRotation;
            cam.SetParent(null, true);
            StartBlend(Phase.CameraIn);
        }

        private void StartBlend(Phase blendPhase)
        {
            blendFromPosition = cam.position;
            blendFromRotation = cam.rotation;
            blend = 0f;
            phase = blendPhase;
        }

        private void Update()
        {
            Mouse mouse = Mouse.current;
            Keyboard keyboard = Keyboard.current;
            switch (phase)
            {
                case Phase.CameraIn:
                    if (Blend(table.CameraAnchor.position, table.CameraAnchor.rotation)) phase = Phase.Menu;
                    break;
                case Phase.Menu:
                    if (keyboard != null && keyboard.escapeKey.wasPressedThisFrame) StartBlend(Phase.CameraOut);
                    break;
                case Phase.MiniGame:
                    if (mouse == null || keyboard == null) break;
                    if (game.Current == KidneyMiniGame.Step.Tape && game.PoppedKidney != null) LaunchKidney();
                    if (game.Tick(mouse, keyboard)) FinishKidney();
                    break;
                case Phase.CameraOut:
                    if (Blend(camParent.TransformPoint(camLocalPosition), camParent.rotation * camLocalRotation)) End();
                    break;
            }
            comics.RemoveAll(c => Time.time - c.born > 1.1f);
        }

        private bool Blend(Vector3 position, Quaternion rotation)
        {
            blend = Mathf.Min(1f, blend + Time.deltaTime / cameraBlendSeconds);
            float t = Mathf.SmoothStep(0f, 1f, blend);
            cam.SetPositionAndRotation(Vector3.Lerp(blendFromPosition, position, t), Quaternion.Slerp(blendFromRotation, rotation, t));
            return blend >= 1f;
        }

        private void End()
        {
            cam.SetParent(camParent, false);
            cam.localPosition = camLocalPosition;
            cam.localRotation = camLocalRotation;
            player.ControlsEnabled = true;
            OperationTestPlayer.LockCursor(true);
            phase = Phase.Idle;
            player = null;
            table = null;
        }

        private void StartKidney()
        {
            OperationPatient patient = table.Patient;
            if (patient == null || patient.KidneysLeft <= 0) return;
            operationStarted = Time.time;
            game = new KidneyMiniGame(patient, patient.KidneysLeft == 1, player.ViewCamera, sfx, Comic);
            phase = Phase.MiniGame;
        }

        // The kidney leaves the body as soon as it pops (while the player tapes the slit), so the flight and the
        // inventory toast overlap the tape step instead of making the player wait.
        private void LaunchKidney()
        {
            Transform organ = game.PoppedKidney;
            OrganQuality quality = OrganGrading.Lower(table.Patient.Condition, game.Penalty);
            OperationPatient patient = table.Patient;
            Vector3 dropAt = organ.position;
            patient.TakeKidney();
            lastItem = ""; // the previous kidney's line must not show up in this operation's summary
            pendingSummary = null;
            OrganPop.Launch(organ, player.ViewCamera, () => AddToInventory(quality, dropAt));
            game.ClearPoppedKidney();
        }

        private void AddToInventory(OrganQuality quality, Vector3 dropAt)
        {
            if (kidneyItem == null)
            {
                Toast("Нет ItemDefinition почки — проверь OperationSession");
                return;
            }
            int value = OrganGrading.UnitValue(kidneyItem.BaseValue, quality);
            string grade = OrganGrading.Label(quality);
            if (inventory != null && inventory.Model != null && inventory.Model.TryAdd(kidneyItem.Id, 1, value) > 0)
            {
                lastItem = $"+ Почка  [{grade}]  ${value}";
                ToastArrival();
                return;
            }
            // Pockets full: the organ lands on the floor next to the table (canon 42: dropping it is the player's fault).
            OfflineWorldItem.Spawn(kidneyItem, 1, value, dropAt + Vector3.up * 0.2f);
            lastItem = $"Карманы полны — почка [{grade}] упала на пол (подбери: E)";
            ToastArrival();
        }

        // The flight can land after FinishKidney: keep its verdict under the item line instead of replacing it.
        private void ToastArrival()
        {
            Toast(pendingSummary != null ? lastItem + "\n" + pendingSummary : lastItem);
            pendingSummary = null;
        }

        private void FinishKidney()
        {
            game.Cleanup(true);
            float seconds = Time.time - operationStarted;
            int penalty = game.Penalty;
            string verdict = penalty == 0 ? "Чистая работа!" : game.Yanked ? "Рывок помял почку" : "Разрез вышел кривым";
            string summary = $"Почка за {seconds:0} с. {verdict}  (ровность разреза {Mathf.RoundToInt(game.Neatness * 100f)}%, соскальзываний {game.Slips})";
            if (lastItem.Length > 0) Toast(lastItem + "\n" + summary);
            else
            {
                pendingSummary = summary; // the kidney is still flying to the inventory
                Toast(summary);
            }
            game = null;
            phase = Phase.Menu;
        }

        private void Comic(string text, Vector3 world, Color color) => comics.Add((text, world, color, Time.time));

        private void Toast(string text)
        {
            toast = text;
            toastUntil = Time.time + 4f;
        }

        private void OnGUI()
        {
            if (phase == Phase.Menu) DrawMenu();
            if (phase == Phase.MiniGame && game != null) DrawMiniGame();
            DrawComics();
            if (Time.time < toastUntil)
                OperationGui.Shadowed(new Rect(0f, Screen.height * 0.74f, Screen.width, 72f), toast, OperationGui.Center(24),
                    new Color(1f, 0.95f, 0.6f));
        }

        private void DrawMenu()
        {
            OperationPatient patient = table.Patient;
            var panel = new Rect(24f, 60f, 360f, 360f);
            GUI.Box(panel, "");
            GUILayout.BeginArea(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, panel.height - 20f));
            GUILayout.Label("ЧТО ДОСТАЁМ?", OperationGui.Left(22));
            GUILayout.Label($"Пациент доставлен: {OrganGrading.Label(patient.Condition)}", OperationGui.Left(14));
            GUILayout.Space(8f);
            GUI.enabled = patient.KidneysLeft > 0;
            if (GUILayout.Button($"Почка  ×{patient.KidneysLeft}   (~{OrganGrading.UnitValue(kidneyItem != null ? kidneyItem.BaseValue : 0, patient.Condition)} $)",
                    GUILayout.Height(36f)))
                StartKidney();
            GUI.enabled = false;
            foreach (OrganEntry entry in LockedOrgans)
                GUILayout.Button($"{entry.Name} — {entry.Locked}", GUILayout.Height(28f));
            GUI.enabled = true;
            GUILayout.Space(10f);
            GUILayout.Label("[Esc] Закончить операцию", OperationGui.Left(14));
            GUILayout.EndArea();
        }

        private void DrawMiniGame()
        {
            OperationGui.Shadowed(new Rect(0f, 18f, Screen.width, 60f), game.Instruction, OperationGui.Center(22), Color.white);
            if (game.Current == KidneyMiniGame.Step.Pull)
            {
                // Tension bar: grows as the kidney stretches out; a yank fills it too fast.
                var back = new Rect(Screen.width * 0.5f - 160f, 80f, 320f, 16f);
                GUI.Box(back, "");
                Color old = GUI.color;
                GUI.color = Color.Lerp(new Color(0.4f, 0.9f, 0.4f), new Color(1f, 0.4f, 0.3f), game.Tension);
                GUI.DrawTexture(new Rect(back.x + 2f, back.y + 2f, (back.width - 4f) * Mathf.Clamp01(game.Tension), back.height - 4f),
                    Texture2D.whiteTexture);
                GUI.color = old;
            }
        }

        private void DrawComics()
        {
            Camera view = player != null ? player.ViewCamera : Camera.main;
            if (view == null) return;
            foreach (var comic in comics)
            {
                Vector3 screen = view.WorldToScreenPoint(comic.world);
                if (screen.z <= 0f) continue;
                float age = Time.time - comic.born;
                float rise = age * 60f;
                var color = new Color(comic.color.r, comic.color.g, comic.color.b, Mathf.Clamp01(1.4f - age * 1.3f));
                int size = Mathf.RoundToInt(Mathf.Lerp(40f, 30f, age));
                OperationGui.Shadowed(new Rect(screen.x - 300f, Screen.height - screen.y - 60f - rise, 600f, 60f), comic.text,
                    OperationGui.Center(size), color);
            }
        }
    }
}
