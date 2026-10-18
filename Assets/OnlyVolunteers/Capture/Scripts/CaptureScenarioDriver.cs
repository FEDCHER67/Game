using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace OnlyVolunteers.Capture
{
    /// <summary>Dev-only scenario driver of stage A (editor and development builds), the capture counterpart of the
    /// operation's OperationNetworkProbe. Input that the game reads through the Input System (the field kit Z/X/C + RMB,
    /// the table view, the NetworkGrabber, K save) is fed through virtual Mouse/Keyboard devices exactly like a player.
    /// Input the map reads through the legacy Input API cannot be simulated; at that boundary the driver calls the same
    /// entry points the key handlers call (Q = GreyboxNpc.Hit as GreyboxInteractor does, LMB carry = the map's
    /// PhysicsGrabber in its ScriptDriven mode as NpcLoadingTest does, E at a door = GreyboxVanCargo.ToggleDoor, E at the
    /// driver door = GreyboxVanSeat.Enter, W/A/S/D = KCC character inputs and van throttle/steer set after the legacy
    /// readers each frame). Every check reads the authoritative state. Started through CaptureTestHooks.Runner.Begin
    /// (PlayMode tests) or -capture-scenario &lt;name&gt;.</summary>
    [DefaultExecutionOrder(100)]
    public sealed partial class CaptureScenarioDriver : MonoBehaviour, IOperationScenarioRunner
    {
        private readonly List<string> log = new List<string>();
        public bool Busy { get; private set; }
        public string LastResult { get; private set; } = "";
        public IReadOnlyList<string> Log => log;

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private CaptureDirector d;
        private GreyboxKccPawn pawn;
        private KccFirstPersonInput kcc;
        private PhysicsGrabber grabber;
        private VanController van;
        private GreyboxVanCargo cargo;
        private GreyboxVanSeat seat;
        private CaptureVanCapacity capacity;
        private Mouse vm;
        private Keyboard vk;
        private Vector2 mPos;
        private bool lmb, rmb;
        private readonly HashSet<Key> keys = new HashSet<Key>();
        private InputSettings priorSettings;
        private RenderTexture rt;
        private Camera shotCamera;
        private string output;
        private string scenario;
        private int failures;
        private bool recording;
        private int frameIndex;
        private float started;
        private const int CaptureWidth = 1920, CaptureHeight = 1080;

        // scripted movement (applied after the legacy readers, every frame)
        private bool walking;
        private Vector3 walkTarget;
        private float walkSpeedScale = 1f;
        private bool crouch;
        private bool holdInputs; // keep feeding the character inputs (crouch) while not walking
        private bool driving;
        private float throttle, steer;
        private bool handbrake;

        private void Awake() { CaptureTestHooks.Runner = this; }
        private void OnDestroy() { if (ReferenceEquals(CaptureTestHooks.Runner, this)) CaptureTestHooks.Runner = null; Teardown(); }
        private void Start()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "-capture-scenario");
            if (i >= 0 && i + 1 < args.Length) Begin(args[i + 1]);
        }

        public void Begin(string name)
        {
            if (Busy) return;
            Busy = true; scenario = name; failures = 0; warnings = 0; log.Clear(); LastResult = "";
            StartCoroutine(Run(name));
        }

        // ---------- plumbing ----------
        private void Line(string text)
        {
            string line = $"[CAPTURE RUN {scenario} t={Time.time - started:F1}] {text}";
            log.Add(line);
            Debug.Log(line);
            if (output != null) File.AppendAllText(Path.Combine(output, "run-log.txt"), line + Environment.NewLine);
        }
        private bool Check(bool ok, string label)
        {
            if (!ok) failures++;
            Line((ok ? "PASS " : "FAIL ") + label);
            return ok;
        }
        private void Info(string text) => Line("INFO " + text);
        private int warnings;
        /// <summary>A scripted stand-in for a legacy-input action (the LMB carry) that did not work this run: the step is
        /// completed by placement so the rest of the loop is still checked; counted and reported, not a rule failure.</summary>
        private void Warn(string text) { warnings++; Line("WARN " + text); }

        private static string Folder(string requested)
        {
            string candidate = requested;
            for (int revision = 2; Directory.Exists(candidate); revision++) candidate = requested + "_" + revision.ToString("D2");
            return candidate;
        }
        public static string EvidenceRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Working", "Reviews", "Capture", "stageA"));

        private IEnumerator Run(string name)
        {
            started = Time.time;
            output = Folder(Path.Combine(EvidenceRoot, "run_" + name));
            Directory.CreateDirectory(output);
            if (string.IsNullOrEmpty(CaptureTestHooks.SaveSlot)) CaptureTestHooks.SaveSlot = "capture_stageA_test.json";
            OperationTestHooks.ForcedRoll = 0.99f;
            float until = Time.time + 30f;
            while ((CaptureDirector.Instance == null || !CaptureDirector.Instance.Ready || !CaptureDirector.Instance.Loaded || CaptureDirector.Instance.Table == null) && Time.time < until) yield return null;
            d = CaptureDirector.Instance;
            if (d == null || !d.Ready || d.Table == null) { Check(false, "startup: solo host, table and pawn ready"); Finish(); yield break; }
            pawn = d.Pawn;
            kcc = pawn.GetComponent<KccFirstPersonInput>();
            grabber = pawn.GetComponentInChildren<PhysicsGrabber>(true);
            van = d.Van;
            cargo = van.GetComponent<GreyboxVanCargo>();
            seat = van.GetComponent<GreyboxVanSeat>();
            capacity = van.GetComponent<CaptureVanCapacity>();
            SetupDevices();
            SetupCapture(pawn.ViewCamera);
            Line($"START scene={UnityEngine.SceneManagement.SceneManager.GetActiveScene().name} host={d.Table.IsServerInitialized} pawn={pawn.Position} table={d.Table.transform.position}");
            IEnumerator body = name switch
            {
                "loop" => Loop(),
                "save-a" => SaveA(),
                "save-b" => SaveB(),
                "push" => Push(),
                "rules" => Rules(),
                "carry" => CarryOnly(),
                "corpse" => Corpse(),
                "corpse-reload" => CorpseReload(),
                "water" => CorpseWater(),
                "straps" => StrapsOnTable(),
                "gurney" => GurneyNudge(),
                "bag-field" => FieldBag(),
                "gurney2" => GurneyPush(),
                "carry-speed" => CarrySpeed(),
                "field-blood" => FieldBlood(),
                "internals" => Internals(),
                _ => null,
            };
            if (body == null) Check(false, "unknown scenario " + name);
            else
            {
                recording = name == "loop";
                if (recording) StartCoroutine(Record());
                yield return body;
                recording = false;
            }
            Finish();
        }

        private void Finish()
        {
            LastResult = failures == 0 ? "PASS" : "FAIL " + failures;
            if (warnings > 0) Line("WARNINGS " + warnings);
            Line("RESULT " + LastResult);
            walking = driving = false;
            Teardown();
            Busy = false;
        }

        private void SetupDevices()
        {
            if (vm != null) return;
            priorSettings = InputSystem.settings;
            var settings = ScriptableObject.Instantiate(priorSettings);
            settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
#if UNITY_EDITOR
            settings.editorInputBehaviorInPlayMode = InputSettings.EditorInputBehaviorInPlayMode.AllDeviceInputAlwaysGoesToGameView;
#endif
            InputSystem.settings = settings;
            vm = InputSystem.AddDevice<Mouse>("CaptureVirtualMouse");
            vk = InputSystem.AddDevice<Keyboard>("CaptureVirtualKeyboard");
            OpsInput.MouseOverride = vm; OpsInput.KeyboardOverride = vk; OpsInput.CursorLockedOverride = true;
            vm.MakeCurrent(); vk.MakeCurrent();
            mPos = new Vector2(CaptureWidth * 0.5f, CaptureHeight * 0.5f);
        }

        private void Teardown()
        {
            if (vm != null && OpsInput.MouseOverride == vm) OpsInput.MouseOverride = null;
            if (vk != null && OpsInput.KeyboardOverride == vk) OpsInput.KeyboardOverride = null;
            if (vm != null) OpsInput.CursorLockedOverride = false;
            if (vm != null && vm.added) InputSystem.RemoveDevice(vm);
            if (vk != null && vk.added) InputSystem.RemoveDevice(vk);
            vm = null; vk = null;
            if (priorSettings != null) { InputSystem.settings = priorSettings; priorSettings = null; }
            ReleaseCapture();
            if (grabber != null && grabber.ScriptDriven) { grabber.ScriptRelease(); grabber.ScriptDriven = false; }
        }

        private void PushMouse(Vector2 scroll = default)
        {
            if (vm == null) return;
            var st = new MouseState { position = mPos, scroll = scroll }.WithButton(MouseButton.Left, lmb).WithButton(MouseButton.Right, rmb);
            InputSystem.QueueStateEvent(vm, st);
        }
        private void PushKeys()
        {
            if (vk == null) return;
            var arr = new Key[keys.Count]; keys.CopyTo(arr);
            InputSystem.QueueStateEvent(vk, new KeyboardState(arr));
        }
        private IEnumerator Frames(int n) { for (int i = 0; i < n; i++) yield return null; }
        private IEnumerator Tap(Key k) { keys.Add(k); PushKeys(); yield return Frames(2); keys.Remove(k); PushKeys(); yield return Frames(2); }
        private IEnumerator Chord(Key modifier, Key k) { keys.Add(modifier); PushKeys(); yield return Frames(1); keys.Add(k); PushKeys(); yield return Frames(2); keys.Remove(k); keys.Remove(modifier); PushKeys(); yield return Frames(2); }
        private IEnumerator WaitFor(Func<bool> cond, float timeout, string label)
        {
            float end = Time.time + timeout;
            while (!cond() && Time.time < end) yield return null;
            Check(cond(), label);
        }

        /// <summary>Holds the LEFT mouse button for 'seconds' (a field tool in hand: round 2), re-aiming at 'aim' every frame
        /// (a moving, kicking body).</summary>
        private IEnumerator HoldLeft(float seconds, Func<Vector3> aim, Action each = null)
        {
            if (aim != null) LookAt(aim());
            yield return Frames(1);
            lmb = true; PushMouse();
            float end = Time.time + seconds;
            while (Time.time < end)
            {
                if (aim != null) LookAt(aim());
                PushMouse();
                each?.Invoke();
                yield return null;
            }
            lmb = false; PushMouse();
            yield return Frames(3);
        }

        /// <summary>The real hotbar keys: 1 = bare hands, then the kit slot's key (2) until the wanted tool is in hand (it
        /// cycles ties, anesthesia, blood, empty hands).</summary>
        private IEnumerator TakeTool(FieldTool want)
        {
            yield return Tap(Key.Digit1);
            for (int i = 0; i < 4 && want != FieldTool.Hands && d.Kit.Tool != want; i++) yield return Tap(Key.Digit2);
            Info("hotbar: " + d.Kit.Tool + " in hand (slot " + (d.Kit.Inventory != null && d.Kit.Inventory.Model != null ? d.Kit.Inventory.Model.SelectedIndex + 1 : 0) + ")");
        }

        private int SlotWithKit()
        {
            var m = d.Kit.Inventory != null ? d.Kit.Inventory.Model : null;
            if (m == null) return -1;
            for (int i = 0; i < m.SlotCount; i++) { var st = m.GetSlot(i); if (!st.IsEmpty && st.ItemId == CaptureFieldKit.KitItemId) return i; }
            return -1;
        }

        // ---------- player ----------
        private static readonly FieldInfo YawField = typeof(KccFirstPersonInput).GetField("_yaw", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly FieldInfo PitchField = typeof(KccFirstPersonInput).GetField("_pitch", BindingFlags.Instance | BindingFlags.NonPublic);
        private void SetYawPitch(float yaw, float pitch)
        {
            YawField?.SetValue(kcc, Mathf.Repeat(yaw, 360f));
            PitchField?.SetValue(kcc, Mathf.Clamp(pitch, -85f, 85f));
        }
        private void LookAt(Vector3 world)
        {
            Vector3 eye = pawn.ViewCamera.transform.position;
            Vector3 dir = world - eye;
            float yaw = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg;
            float pitch = -Mathf.Atan2(dir.y, new Vector2(dir.x, dir.z).magnitude) * Mathf.Rad2Deg;
            SetYawPitch(yaw, pitch);
            pawn.ViewCamera.transform.rotation = Quaternion.Euler(Mathf.Clamp(pitch, -85f, 85f), yaw, 0f); // this frame already
        }
        private void Teleport(Vector3 foot, float yaw)
        {
            pawn.Teleport(foot, yaw);
        }
        private float Yaw => YawField != null ? (float)YawField.GetValue(kcc) : 0f;

        /// <summary>Walks the real KCC character (its inputs set after the legacy reader each frame) to 'to'.</summary>
        private IEnumerator WalkTo(Vector3 to, float timeout, float speedScale = 1f, Func<Vector3> look = null)
        {
            walkTarget = to; walkSpeedScale = speedScale; walking = true;
            float end = Time.time + timeout;
            while (Time.time < end)
            {
                Vector3 flat = to - pawn.Position; flat.y = 0f;
                if (flat.magnitude < 0.25f) break;
                if (look != null) LookAt(look());
                yield return null;
            }
            walking = false;
            yield return Frames(2);
        }

        private void Update()
        {
            if (vk != null)
            {
                bool changed = crouch ? keys.Add(Key.LeftCtrl) : keys.Remove(Key.LeftCtrl);
                if (changed) PushKeys();
            }
            // After VanDriveInput (0) read the keys, before CaptureVanCapacity (200) may veto them: like a driver's W.
            if (driving && van != null)
            {
                van.Throttle = throttle;
                van.Steer = steer;
                van.Handbrake = handbrake;
            }
            if ((walking || holdInputs) && kcc != null && pawn != null && pawn.Controlled)
            {
                Vector3 flat = walkTarget - pawn.Position; flat.y = 0f;
                float yaw = Mathf.Atan2(flat.x, flat.z) * Mathf.Rad2Deg;
                // Move toward the target whatever the camera looks at (a carry looks back at the body).
                float camYaw = Yaw;
                Vector3 local = Quaternion.Euler(0f, -camYaw, 0f) * flat.normalized;
                var inputs = new PlayerCharacterInputs
                {
                    MoveAxisForward = Mathf.Clamp(local.z, -1f, 1f) * walkSpeedScale,
                    MoveAxisRight = Mathf.Clamp(local.x, -1f, 1f) * walkSpeedScale,
                    CameraRotation = Quaternion.Euler(0f, camYaw, 0f),
                    CrouchDown = crouch, CrouchUp = !crouch,
                };
                if (!walking || flat.magnitude < 0.25f) { inputs.MoveAxisForward = 0f; inputs.MoveAxisRight = 0f; }
                kcc.Character.SetInputs(ref inputs);
                _ = yaw;
            }
        }


        // ---------- capture ----------
        private void SetupCapture(Camera camera)
        {
            ReleaseCapture();
            if (camera == null) return;
            rt = new RenderTexture(CaptureWidth, CaptureHeight, 24, RenderTextureFormat.ARGB32) { name = "CaptureShots", antiAliasing = 2 };
            rt.Create();
            shotCamera = camera;
            camera.targetTexture = rt;
            d?.Hud?.RenderInto(camera);
            var view = d != null && d.Table != null ? d.Table.GetComponent<OperationTableView>() : null;
            if (view != null) view.CaptureMode = true;
        }
        private void ReleaseCapture()
        {
            if (shotCamera != null && shotCamera.targetTexture == rt) shotCamera.targetTexture = null;
            shotCamera = null;
            d?.Hud?.RenderInto(null);
            if (rt != null) { rt.Release(); Destroy(rt); rt = null; }
        }
        private void UseCamera(Camera camera)
        {
            if (camera == shotCamera) return;
            SetupCapture(camera);
        }
        private Texture2D Grab(int w, int h)
        {
            Canvas.ForceUpdateCanvases();
            shotCamera.Render();
            var small = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(rt, small);
            var prev = RenderTexture.active; RenderTexture.active = small;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(small);
            return tex;
        }
        private void Shot(string name)
        {
            if (rt == null || output == null || shotCamera == null) return;
            var tex = Grab(CaptureWidth, CaptureHeight);
            File.WriteAllBytes(Path.Combine(output, name + ".png"), tex.EncodeToPNG());
            Destroy(tex);
            Line("SHOT " + name + " toast=«" + (d != null && d.Hud != null ? d.Hud.LastToast : "") + "»");
        }
        /// <summary>A third-person look at a point (for the cloud, the van and the table), without moving the player.</summary>
        private void Overview(string name, Vector3 eye, Vector3 at, float fov = 55f)
        {
            if (output == null) return;
            var go = new GameObject("CaptureOverviewCam");
            var cam = go.AddComponent<Camera>();
            cam.fieldOfView = fov; cam.nearClipPlane = 0.05f; cam.farClipPlane = 600f;
            go.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(at - eye));
            var target = new RenderTexture(CaptureWidth, CaptureHeight, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 };
            cam.targetTexture = target;
            cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = target;
            var tex = new Texture2D(CaptureWidth, CaptureHeight, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, CaptureWidth, CaptureHeight), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(Path.Combine(output, name + ".png"), tex.EncodeToPNG());
            Destroy(tex); cam.targetTexture = null; target.Release(); Destroy(target); Destroy(go);
            Line("SHOT " + name + " (overview)");
        }
        private IEnumerator Record()
        {
            string folder = Path.Combine(output, "frames");
            Directory.CreateDirectory(folder);
            while (recording)
            {
                if (rt != null && shotCamera != null)
                {
                    var tex = Grab(960, 540);
                    File.WriteAllBytes(Path.Combine(folder, "f" + (frameIndex++).ToString("D5") + ".jpg"), tex.EncodeToJPG(80));
                    Destroy(tex);
                }
                yield return new WaitForSeconds(0.12f);
            }
        }
#else
        public void Begin(string name) { LastResult = "FAIL dev-only"; }
#endif
    }
}
