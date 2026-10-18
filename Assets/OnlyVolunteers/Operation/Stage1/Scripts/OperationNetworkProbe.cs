using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using FishNet.Managing;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Dev-only scenario driver (editor and development builds). It plays the operation like a person: virtual
    /// Mouse/Keyboard devices feed the real OperationTableView, NetworkGrabber and HUD; it never calls the table RPCs.
    /// The player's walking and mouse-look (legacy-input KCC) are set directly on the motor/yaw/pitch. Every check reads
    /// the authoritative server state. Started by OperationTestHooks.Runner.Begin(name) (PlayMode test) or by
    /// -ops-scenario &lt;name&gt; (standalone two-process runs).</summary>
    public sealed partial class OperationNetworkProbe : MonoBehaviour, IOperationScenarioRunner
    {
        private readonly List<string> log = new();
        public bool Busy { get; private set; }
        public string LastResult { get; private set; } = "";
        public IReadOnlyList<string> Log => log;

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private NetworkOperationTable table;
        private OperationTableView view;
        private NetworkPlayer player;
        private KccFirstPersonInput kcc;
        private Mouse vm;
        private Keyboard vk;
        private Vector2 mPos;
        private bool lmb, rmb;
        private readonly HashSet<Key> keys = new();
        private InputSettings priorSettings;
        private RenderTexture rt;
        private string output;
        private string scenario;
        private int failures;
        private int frameIndex;
        private bool recording;
        private float started;
        private readonly int captureWidth = 1920, captureHeight = 1080;

        private void Awake() { OperationTestHooks.Runner = this; }
        private void OnDestroy() { if (ReferenceEquals(OperationTestHooks.Runner, this)) OperationTestHooks.Runner = null; Teardown(); }
        private void Start()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "-ops-scenario");
            if (i >= 0 && i + 1 < args.Length) Begin(args[i + 1]);
        }

        public void Begin(string name)
        {
            if (Busy) return;
            Busy = true; finished = false; scenario = name; failures = 0; log.Clear(); LastResult = "";
            StartCoroutine(Run(name));
        }

        // ---------- plumbing ----------
        private void Line(string text)
        {
            string line = $"[OPS RUN {scenario} t={Time.time - started:F1}] {text}";
            log.Add(line); Debug.Log(line);
            if (output != null) File.AppendAllText(Path.Combine(output, "run-log.txt"), line + Environment.NewLine);
        }
        private bool Check(bool ok, string label)
        {
            if (!ok) failures++;
            Line((ok ? "PASS " : "FAIL ") + label);
            return ok;
        }
        private static string Argument(string key)
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, key);
            return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
        }
        private OperationState S => table.IsServerInitialized ? table.ServerRules?.State : table.State;
        private Camera Cam => player != null ? player.ViewCamera : null;

        private void SetupDevices()
        {
            priorSettings = InputSystem.settings;
            var settings = ScriptableObject.Instantiate(priorSettings);
            settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
#if UNITY_EDITOR
            settings.editorInputBehaviorInPlayMode = InputSettings.EditorInputBehaviorInPlayMode.AllDeviceInputAlwaysGoesToGameView;
#endif
            InputSystem.settings = settings;
            vm = InputSystem.AddDevice<Mouse>("OpsVirtualMouse");
            vk = InputSystem.AddDevice<Keyboard>("OpsVirtualKeyboard");
            OpsInput.MouseOverride = vm; OpsInput.KeyboardOverride = vk; OpsInput.CursorLockedOverride = true;
            vm.MakeCurrent(); vk.MakeCurrent();
        }
        private void Teardown()
        {
            if (OpsInput.MouseOverride == vm) OpsInput.MouseOverride = null;
            if (OpsInput.KeyboardOverride == vk) OpsInput.KeyboardOverride = null;
            OpsInput.CursorLockedOverride = false;
            if (vm != null && vm.added) InputSystem.RemoveDevice(vm);
            if (vk != null && vk.added) InputSystem.RemoveDevice(vk);
            vm = null; vk = null;
            if (priorSettings != null) { InputSystem.settings = priorSettings; priorSettings = null; }
            if (Cam != null && Cam.targetTexture == rt) Cam.targetTexture = null;
            if (view != null) view.CaptureMode = false;
            if (rt != null) { rt.Release(); Destroy(rt); rt = null; }
        }
        private void PushMouse(Vector2 scroll = default)
        {
            var st = new MouseState { position = mPos, scroll = scroll }.WithButton(MouseButton.Left, lmb).WithButton(MouseButton.Right, rmb);
            InputSystem.QueueStateEvent(vm, st);
        }
        private void PushKeys()
        {
            var arr = new Key[keys.Count]; keys.CopyTo(arr);
            InputSystem.QueueStateEvent(vk, new KeyboardState(arr));
        }
        private IEnumerator Frames(int n) { for (int i = 0; i < n; i++) yield return null; }
        private IEnumerator Tap(Key k) { keys.Add(k); PushKeys(); yield return Frames(2); keys.Remove(k); PushKeys(); yield return Frames(2); }
        private IEnumerator HoldKey(Key k, float seconds) { keys.Add(k); PushKeys(); float end = Time.time + seconds; while (Time.time < end) { PushKeys(); yield return null; } keys.Remove(k); PushKeys(); yield return Frames(2); }
        private IEnumerator MoveTo(Vector2 to, float seconds)
        {
            Vector2 from = mPos; float t0 = Time.time;
            while (Time.time - t0 < seconds) { float t = (Time.time - t0) / seconds; t = t * t * (3f - 2f * t); mPos = Vector2.Lerp(from, to, t); PushMouse(); yield return null; }
            mPos = to; PushMouse(); yield return Frames(2);
        }
        private IEnumerator Button(bool down) { lmb = down; PushMouse(); yield return Frames(2); }
        private IEnumerator Click() { yield return Button(true); yield return Button(false); }
        private IEnumerator RightClick() { rmb = true; PushMouse(); yield return Frames(2); rmb = false; PushMouse(); yield return Frames(2); }
        private IEnumerator Hold(float seconds) { lmb = true; PushMouse(); float end = Time.time + seconds; while (Time.time < end) { PushMouse(); yield return null; } lmb = false; PushMouse(); yield return Frames(3); }
        private IEnumerator Scroll(float y) { PushMouse(new Vector2(0, y)); yield return null; PushMouse(); yield return Frames(2); }
        private Vector2 Scr(Vector3 world) { var s = Cam.WorldToScreenPoint(world); return new Vector2(s.x, s.y); }
        private IEnumerator WaitFor(Func<bool> cond, float timeout, string label)
        {
            float end = Time.time + timeout;
            while (!cond() && Time.time < end) yield return null;
            Check(cond(), label);
        }

        private bool aimed;
        /// <summary>Moves the mouse like a person looking for the right spot: candidates in order until the view's
        /// real raycast reports the wanted target.</summary>
        private IEnumerator AimAt(Func<OpTarget, bool> want, IList<Vector3> candidates, string label, float seconds = 0.25f)
        {
            aimed = false;
            foreach (var c in candidates)
            {
                yield return MoveTo(Scr(c), seconds);
                yield return Frames(2);
                if (want(view.Current.target)) { aimed = true; break; }
                seconds = 0.08f;
            }
            if (!aimed) Line($"AIM miss {label}: hover={view.Current.target}");
        }
        private static Vector3[] Around(Vector3 c, Vector3 a, Vector3 b, float r)
        {
            var list = new List<Vector3> { c };
            for (int k = 1; k <= 2; k++) foreach (var d in new[] { a, -a, b, -b, a + b, a - b, -a + b, -a - b }) list.Add(c + d.normalized * r * k);
            return list.ToArray();
        }

        // ---------- capture ----------
        private void SetupCapture()
        {
            rt = new RenderTexture(captureWidth, captureHeight, 24, RenderTextureFormat.ARGB32) { name = "OpsCapture", antiAliasing = 2 };
            rt.Create();
            Cam.targetTexture = rt;
            view.CaptureMode = true;
        }
        private Texture2D Grab(int w, int h)
        {
            Canvas.ForceUpdateCanvases();
            Cam.Render();
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
            if (rt == null || output == null) return;
            var tex = Grab(captureWidth, captureHeight);
            File.WriteAllBytes(Path.Combine(output, name + ".png"), tex.EncodeToPNG()); Destroy(tex);
            Line("SHOT " + name + (view != null && view.Hud != null ? " hud: " + view.Hud.DebugLine + " hint=«" + view.Hud.CurrentHint + "»" : ""));
        }
        private IEnumerator Record()
        {
            string folder = Path.Combine(output, "frames"); Directory.CreateDirectory(folder);
            while (recording)
            {
                if (rt != null && Cam != null)
                {
                    var tex = Grab(960, 540);
                    File.WriteAllBytes(Path.Combine(folder, "f" + (frameIndex++).ToString("D5") + ".jpg"), tex.EncodeToJPG(82)); Destroy(tex);
                }
                yield return new WaitForSeconds(0.15f);
            }
        }

        // ---------- player ----------
        private void SetYawPitch(float yaw, float pitch)
        {
            var type = typeof(KccFirstPersonInput);
            type.GetField("_yaw", BindingFlags.Instance | BindingFlags.NonPublic)?.SetValue(kcc, Mathf.Repeat(yaw, 360f));
            type.GetField("_pitch", BindingFlags.Instance | BindingFlags.NonPublic)?.SetValue(kcc, Mathf.Clamp(pitch, -85f, 85f));
        }
        private void LookAt(Vector3 world)
        {
            Vector3 eye = Cam.transform.position; Vector3 d = world - eye;
            float yaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
            float pitch = -Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg;
            SetYawPitch(yaw, pitch);
        }
        private void Teleport(Vector3 foot) { kcc.Character.Motor.SetPosition(foot); kcc.Character.Motor.BaseVelocity = Vector3.zero; }
        private Vector3 TableFoot(Vector3 local) { var p = table.transform.TransformPoint(local); p.y = 0.02f; return p; }

        // ---------- scenario ----------
        private IEnumerator Run(string name)
        {
            started = Time.time;
            output = Argument("-ops-evidence");
            if (string.IsNullOrEmpty(output) && !string.IsNullOrEmpty(EvidenceRoot)) output = Path.Combine(EvidenceRoot, "run_" + name);
            if (string.IsNullOrEmpty(output)) output = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Working", "Reviews", "Operations", "stage1_v4", "run_" + name));
            output = FreshEvidenceFolder(output);
            Directory.CreateDirectory(output);
            OperationTestHooks.SaveSlot = Path.Combine(output, "operations_stage1_test_v04.json");
            if (name != "natural-rolls") OperationTestHooks.ForcedRoll = 0.99f;
            SetupDevices();
            var session = NetworkSession.Active;
            var manager = session != null ? session.GetComponent<NetworkManager>() : null;
            if (manager != null && !manager.ServerManager.Started && !manager.ClientManager.Started && !name.StartsWith("net-"))
                session.StartHost();
            float until = Time.time + 40f;
            while (Time.time < until && (player == null || table == null || (name != "g35-water" && (table.State == null || table.PatientObject == null))))
            {
                if (table == null) table = FindAnyObjectByType<NetworkOperationTable>();
                foreach (var p in FindObjectsByType<NetworkPlayer>()) if (p.IsOwner && p.IsClientInitialized) player = p;
                yield return null;
            }
            if (player == null || table == null) { Check(false, "startup (player/table spawned)"); Finish(); yield break; }
            view = table.GetComponent<OperationTableView>();
            kcc = player.GetComponent<KccFirstPersonInput>();
            if (!homeKnown) { tableHome = new Pose(table.transform.position, table.transform.rotation); homeKnown = true; }
            yield return new WaitForSeconds(0.8f);
            SetupCapture();
            mPos = new Vector2(captureWidth * 0.5f, captureHeight * 0.5f); PushMouse();
            Line($"START host={table.IsServerInitialized} client={player.OwnerId} patient={table.State?.patientId ?? "empty"} table={table.transform.position} rot={table.transform.eulerAngles}");
            IEnumerator body = name switch
            {
                "suite" => Suite(),
                "loop" => Loop(true),
                "edges" => Edges(),
                "rotated" => Rotated(),
                "hud720" => Hud720(),
                "evidence" => Evidence(),
                "v04-loop" => V04Loop(),
                "v04-guide-edges" => V04GuideEdges(),
                "v04-throw" => V04Throw(),
                "capture-kidney" => CaptureKidney(),
                "g35-straps" => G35Straps(),
                "g35-brake" => G35Brake(),
                "g35-corpse" => ClBag(),
                "cl-bag" => ClBag(),
                "cl-organ-scale" => ClOrganScale(),
                "cl-art-v03" => ClArtV03(),
                "g35-water" => G35Water(),
                "cl-straps" => ClStraps(),
                "net-host" => NetHost(),
                "net-client" => NetClient(),
                _ => null
            };
            if (body == null) Check(false, "unknown scenario " + name);
            else
            {
                recording = name == "loop" || name == "v04-loop" || name == "g35-corpse" || name == "g35-water" || name.StartsWith("cl-") || name.StartsWith("net-");
                if (name == "net-client" && table.Tuning.sharedAbdomen) StartCoroutine(V04RemoteCarry());
                if (recording) StartCoroutine(Record());
                yield return body;
                recording = false;
            }
            Finish();
        }
        private bool finished;
        /// <summary>loop, edges, rotated and hud720 one after another in one host session (one evidence folder each).</summary>
        private IEnumerator Suite()
        {
            string root = output;
            foreach (var sub in new[] { "loop", "edges", "rotated", "hud720" })
            {
                output = FreshEvidenceFolder(Path.Combine(Path.GetDirectoryName(root), "run_" + sub));
                Directory.CreateDirectory(output);
                int before = failures;
                scenario = sub;
                recording = sub == "loop";
                if (recording) StartCoroutine(Record());
                IEnumerator b = sub == "loop" ? Loop(true) : sub == "edges" ? Edges() : sub == "rotated" ? Rotated() : Hud720();
                yield return b;
                recording = false;
                Line("SUB RESULT " + (failures == before ? "PASS" : "FAIL " + (failures - before)));
                File.WriteAllText(Path.Combine(output, "final-state.json"), JsonUtility.ToJson(table.ServerRules.State, true));
                yield return new WaitForSeconds(0.5f);
            }
            output = root; scenario = "suite";
        }
        private void Finish()
        {
            if (finished) return;
            finished = true;
            LastResult = failures == 0 ? "PASS" : "FAIL " + failures;
            Line("RESULT " + LastResult);
            if (table != null && table.IsServerInitialized && table.ServerRules != null && output != null)
                File.WriteAllText(Path.Combine(output, "final-state.json"), JsonUtility.ToJson(table.ServerRules.State, true));
            Teardown();
            Busy = false;
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-ops-quit") >= 0) StartCoroutine(QuitSoon());
        }
        private IEnumerator QuitSoon() { yield return new WaitForSeconds(1.5f); Application.Quit(); }

        // ---------- steps ----------
        private IEnumerator CarryPatientOntoTable()
        {
            var body = table.PatientBody;
            Vector3 patientPos = body.transform.position;
            Vector3 away = (patientPos - table.transform.position); away.y = 0; away.Normalize();
            Teleport(patientPos + away * 1.2f + Vector3.up * 0.02f);
            yield return Frames(3);
            LookAt(patientPos + Vector3.up * 0.15f);
            yield return Frames(3);
            Shot("01_overview");
            float hold = 1.8f;
            if (Physics.Raycast(Cam.transform.position, Cam.transform.forward, out var grabHit, 3f, ~0, QueryTriggerInteraction.Ignore)) hold = grabHit.distance;
            yield return Button(true);
            yield return new WaitForSeconds(0.4f);
            Check(body.HasHolder || !table.IsServerInitialized, "physical grab took the patient (real LMB through NetworkGrabber)");
            // Look up to lift him, walk round to the table and hold him high over the pad, like a player would. The
            // existing grab spring (220 N/m, unchanged) sags ~0.55 m under 12 kg, so the hold point stays high. The
            // player is placed each frame so that eye + forward * grab distance lands exactly on the wanted point.
            Vector3 rest = table.RestPose.position;
            Vector3 start = kcc.Character.Motor.TransientPosition;
            float eye = Cam.transform.position.y - start.y;
            Vector3 grab = Cam.transform.position + Cam.transform.forward * hold;
            Vector3 up1 = new Vector3(grab.x, start.y + 1.85f, grab.z);
            Vector3 over = rest + table.transform.up * (1.85f - table.Tuning.padTop);
            Vector3 outward = -table.transform.right;
            Line($"CARRY hold={hold:F2} eye={eye:F2} grab={grab} over={over}");
            float t0 = Time.time; float nextLog = 0f;
            const float lift = 0.9f, traverse = 1.4f, settle = 0.7f;
            while (Time.time - t0 < lift + traverse + settle)
            {
                float e = Time.time - t0;
                Vector3 d = e < lift ? Vector3.Lerp(grab, up1, Mathf.SmoothStep(0f, 1f, e / lift))
                    : Vector3.Lerp(up1, over, Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((e - lift) / traverse)));
                float dy = start.y + eye - d.y;
                float dx = Mathf.Sqrt(Mathf.Max(0.04f, hold * hold - dy * dy));
                Vector3 foot = d + outward * dx; foot.y = start.y;
                Teleport(foot);
                Vector3 eyePos = foot + Vector3.up * eye, dir = d - eyePos;
                SetYawPitch(Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg, -Mathf.Atan2(dir.y, new Vector2(dir.x, dir.z).magnitude) * Mathf.Rad2Deg);
                lmb = true; PushMouse();
                if (Time.time >= nextLog) { nextLog = Time.time + 0.5f; Line($"CARRY t={e:F1} patient={body.transform.position} held={body.HasHolder} want={d}"); }
                yield return null;
            }
            yield return new WaitForSeconds(0.6f);
            Shot("02_carry");
            Line($"TABLE during the carry at {table.transform.position} frozen={table.Frozen} (brakes on while the patient is carried near it)");
            yield return Button(false);
            yield return WaitFor(() => S.onTable, 3f, "released over the pad -> auto-align starts");
            float alignStart = Time.time;
            yield return WaitFor(() => S.aligned, 3f, "patient slid into PatientRest");
            Line($"ALIGN took {Time.time - alignStart:F2}s distance={Vector3.Distance(body.transform.position, table.RestPose.position):F3}");
        }

        private IEnumerator EnterTable()
        {
            // beside the gurney toward the head end, clear of the instrument stand
            Teleport(TableFoot(new Vector3(-1.25f, 0f, 0.45f)));
            yield return Frames(2);
            LookAt(table.transform.TransformPoint(new Vector3(0, 0.75f, 0.1f)));
            yield return Frames(4);
            Check(view.PromptVisible, "prompt «[E] Встать к столу» visible");
            yield return Tap(Key.E);
            yield return WaitFor(() => view.Active && table.IsParticipant(player.OwnerId) || !table.IsServerInitialized && view.Active, 2f, "E -> table mode joined");
            yield return new WaitForSeconds(table.Tuning.cameraBlendSeconds + 0.15f);
            Check(view.CameraMode == TableCamera.Prep && Vector3.Distance(Cam.transform.position, view.ViewPose.position) < 0.05f,
                "E opens the PREP view (camera blended to it)");
        }

        private IEnumerator Straps(bool all)
        {
            bool wheeledOut = false;
            if (!table.Tuning.torsoStrap) all = true; // round 3: no torso strap, the four limb straps hold him down
            for (int i = 0; i < 5; i++)
            {
                if (!OperationStraps.Active(table.Tuning, i)) continue;
                if (!all && i != 4) continue;
                if (S.restraints[i]) continue;
                if (!wheeledOut && view.CameraMode != TableCamera.Prep)
                {
                    // Two table screens (v04 playtest): straps are clicked in PREP; Tab there like a player.
                    yield return Tap(Key.Tab);
                    yield return new WaitForSeconds(0.45f);
                    Check(view.CameraMode == TableCamera.Prep, "Tab opens the PREP view for the straps");
                    wheeledOut = true;
                }
                Collider hit = null;
                foreach (var tag in table.GetComponentsInChildren<OperationTargetTag>()) if (tag.kind == TargetKind.Strap && tag.index == i) hit = tag.GetComponent<Collider>();
                if (hit == null) { Check(false, "strap collider " + i); continue; }
                var b = hit.bounds;
                var candidates = new List<Vector3> { b.center, b.center + table.transform.up * b.extents.y * 0.5f, b.center + table.transform.forward * 0.02f, b.center - table.transform.forward * 0.02f };
                candidates.AddRange(StrapCandidates(b)); // v04 top camera: the centre of an open strap can lie under a tray tool
                yield return AimAt(t => t.kind == TargetKind.Strap && t.index == i, candidates, "strap " + i);
                if (!aimed) { Check(false, "strap " + i + " found under the cursor"); continue; }
                if (i == 0) Shot("03_strap_hover");
                yield return Click();
                yield return WaitFor(() => S.restraints[i], 1.5f, "strap " + OperationText.Straps[i] + " closed by click");
                yield return new WaitForSeconds(0.3f);
            }
            if (wheeledOut)
            {
                yield return Tap(Key.Tab);
                yield return new WaitForSeconds(0.45f);
            }
        }

        private IEnumerator Select(Key k, ToolSlot slot)
        {
            yield return Tap(k);
            yield return WaitFor(() => view.LocalSlot == slot, 1.5f, "key " + k + " -> " + slot);
        }

        private IEnumerator AimBody(Func<OpTarget, bool> want, BodyPart[] parts, string label)
        {
            var rig = table.PatientRig; var list = new List<Vector3>();
            foreach (var p in parts) { var cols = rig.PartColliders(p); if (cols == null) continue; foreach (var c in cols) { list.Add(c.bounds.center + table.transform.up * 0.03f); list.Add(c.bounds.center); } }
            yield return AimAt(want, list, label);
        }

        private IEnumerator Inject(float seconds, string label)
        {
            yield return Select(Key.Digit2, ToolSlot.Anesthesia);
            yield return AimBody(t => t.IsInjectionSite, new[] { BodyPart.ShoulderL, BodyPart.ArmL, BodyPart.Neck, BodyPart.ShoulderR, BodyPart.ArmR }, "injection site");
            if (!aimed) { Check(false, "injection site found under the cursor"); yield break; }
            Line($"INJECT {label} on {view.Current.target} for {seconds:F1}s residual={S.residual:F2}");
            lmb = true; PushMouse();
            float end = Time.time + seconds; bool shot = false;
            while (Time.time < end) { PushMouse(); if (!shot && Time.time > end - seconds * 0.45f && label == "main") { Shot("04_injecting"); shot = true; } yield return null; }
            lmb = false; PushMouse(); yield return Frames(3);
            Line($"INJECT done residual={S.residual:F2} sleep={S.sleepRemaining:F1} alive={S.alive}");
        }

        private IEnumerator CollectBlood(int bag)
        {
            yield return Select(Key.Digit3, ToolSlot.Blood);
            yield return AimBody(t => t.ArmSide >= 0, new[] { BodyPart.ArmR, BodyPart.ArmL, BodyPart.ShoulderR }, "arm for blood");
            if (!aimed) { Check(false, "arm found under the cursor"); yield break; }
            int before = S.bloodPortions;
            lmb = true; PushMouse();
            float end = Time.time + 2.2f; while (Time.time < end) { PushMouse(); yield return null; }
            lmb = false; PushMouse(); yield return new WaitForSeconds(0.5f);
            float kept = table.ServerWorld != null ? table.ServerWorld.bloodFill : table.View.blood;
            Check(kept > 0.4f && kept < 0.6f, $"blood progress kept after early release ({kept:F2})");
            lmb = true; PushMouse();
            end = Time.time + 2.6f; bool shot = false;
            bool angled = false; string angleNote = "";
            while (Time.time < end)
            {
                PushMouse();
                if (!shot && Time.time > end - 1.5f)
                {
                    Shot("05_blood_filling"); shot = true;
                    // Rework (Fedya 2026-10-18): the syringe is in the skin at ~30 deg while it draws.
                    var syringe = table.ToolOf(ToolSlot.Blood);
                    // The pose this frame shows (the tool's LateUpdate applies it after this coroutine step).
                    if (syringe != null && view.Current.hit && table.TryHeldPose(syringe, syringe.Holder, out var shown))
                    {
                        float toSkin = 90f - Vector3.Angle(shown.rotation * Vector3.up, view.Current.normal);
                        float tip = Vector3.Distance(shown.position, view.Current.point);
                        angled = Mathf.Abs(toSkin - table.Tuning.syringeSkinAngle) < 8f && tip < 0.012f;
                        angleNote = toSkin.ToString("F0") + " deg, tip " + (tip * 1000f).ToString("F0") + " mm from the skin point";
                    }
                }
                yield return null;
            }
            lmb = false; PushMouse(); yield return Frames(3);
            Check(angled, "while drawing, the syringe sits in the skin at ~" + table.Tuning.syringeSkinAngle.ToString("F0") + " deg (" + angleNote + ")");
            Check(S.bloodPortions == before + 1, "one blood portion counted when the syringe filled (" + S.bloodPortions + ")");
            var pose = table.BagPose(bag);
            yield return AimAt(t => t.kind == TargetKind.BloodBag && t.index == bag, new[] { pose.position + pose.up * 0.02f, pose.position }, "empty bag " + bag);
            if (!aimed) { Check(false, "empty bag found under the cursor"); yield break; }
            int items = table.ServerItems.Count;
            yield return Click();
            // Rework: the plunger goes down over bloodTransferSeconds; the syringe empties as the bag fills by the same amount.
            yield return new WaitForSeconds(table.Tuning.bloodTransferSeconds * 0.5f);
            float syringeHalf = table.View.blood, bagHalf = table.View.bagFill != null && bag < table.View.bagFill.Length ? table.View.bagFill[bag] : -1f;
            Shot("06a_blood_transfer");
            Check(syringeHalf > 0.15f && syringeHalf < 0.85f && Mathf.Abs(syringeHalf + bagHalf * Mathf.Max(1, table.Tuning.bloodPortionsPerBag) - 1f) < 0.12f,
                "mid-transfer: syringe " + syringeHalf.ToString("F2") + " + bag " + bagHalf.ToString("F2") + " = one portion");
            yield return WaitFor(() => table.ServerItems.Count == items + 1, table.Tuning.bloodTransferSeconds + 1.5f, "click empty bag -> sealed bag item spawned");
            if (table.ServerItems.Count > items)
            {
                var bagItem = table.ServerItems[table.ServerItems.Count - 1];
                Check(bagItem.Kind == 2 && bagItem.World.UnitValue == table.Tuning.bloodValue && bagItem.Data.sealedBlood, $"sealed bag {bagItem.Identity} ${bagItem.World.UnitValue} no grade, no spoilage");
            }
            Check(table.ServerWorld.bloodFill == 0f, "blood syringe empty again");
            yield return new WaitForSeconds(0.4f);
            Shot("06_blood_bag");
        }

        private IEnumerator Cut(int organ, bool sloppy = false, bool capture = false)
        {
            if (table.Tuning.sharedAbdomen)
            {
                if (!S.zoneOpened) yield return CutShared(OperationAbdomenGeometry.ZoneGuide, sloppy, capture);
                yield break;
            }
            if (view.LocalSlot != ToolSlot.Scalpel) yield return Select(Key.Digit4, ToolSlot.Scalpel);
            var tuning = table.Tuning;
            Vector3 n = table.OrganNormal(organ);
            yield return AimAt(t => t.kind == TargetKind.Incision && t.index == organ, new[] { table.GuidePosition(organ, 0f) + n * 0.004f, table.GuidePosition(organ, 0.04f) }, "incision start " + organ);
            if (!aimed) { Check(false, $"incision {organ}: start dot found under the cursor"); yield break; }
            if (capture) Shot("07_cut_start");
            yield return Button(true);
            // Human drag: ~0.3 s over the whole line with a small wobble (or a deliberately sloppy one).
            const int steps = 22; float stepTime = 0.32f / steps;
            Vector3 side = table.SitePoint(organ, tuning.guideAcross[organ] ? new Vector3(0, 0.01f, 0) : new Vector3(0.01f, 0, 0)) - table.SitePoint(organ, Vector3.zero);
            for (int s = 1; s <= steps; s++)
            {
                float a = (float)s / steps * 1.03f;
                Vector3 p = table.GuidePosition(organ, Mathf.Min(1.03f, a)) + n * 0.004f + side * (sloppy ? 3.2f : Mathf.Sin(s * 1.3f) * 0.6f);
                mPos = Scr(p); PushMouse();
                float e = Time.time + stepTime; while (Time.time < e) yield return null;
                if (capture && s == steps / 2) Shot("08_cutting");
            }
            yield return new WaitForSeconds(0.25f);
            yield return Button(false);
            yield return WaitFor(() => S.organs[organ].Opened, 1f, $"incision {organ} opened by a ~0.3 s drag (cut={S.organs[organ].cut:F2})");
        }

        private IEnumerator Snip(int organ, bool capture = false)
        {
            if (table.Tuning.sharedAbdomen && organ == 2)
            { if (!S.organs[2].Released) yield return CutShared(2, false, capture); yield break; }
            if (view.LocalSlot != ToolSlot.Scalpel) yield return Select(Key.Digit4, ToolSlot.Scalpel);
            yield return new WaitForSeconds(0.35f);
            if (capture) Shot("09_opened_cords");
            for (int c = 0; c < S.organs[organ].connections.Length; c++)
            {
                if (S.organs[organ].connections[c] >= 1f) continue;
                OperationGeometry.Cord(table.Tuning, organ, c, out var a, out var r);
                // Follow the visible small cord while the awake patient moves; never enlarge its target.
                aimed = false;
                float aimEnd = Time.time + 0.65f;
                while (Time.time < aimEnd)
                {
                    mPos = Scr(table.SitePoint(organ, (a + r) * 0.5f)); PushMouse(); yield return null;
                    var target = view.Current.target;
                    if (target.kind == TargetKind.Cord && target.index == organ && target.sub == c) { aimed = true; break; }
                }
                if (!aimed) { Check(false, $"cord {organ}/{c} found under the cursor"); continue; }
                int damage = S.organs[organ].damage;
                yield return Button(true);
                float holdEnd = Time.time + 0.42f;
                while (Time.time < holdEnd)
                { mPos = Scr(table.SitePoint(organ, (a + r) * 0.5f)); PushMouse(); yield return null; }
                yield return Button(false);
                yield return Settle();
                Check(S.organs[organ].connections[c] >= 1f, $"cord {organ}/{c} snipped by a 0.42 s hold");
                Check(S.organs[organ].damage == damage, $"snipping cord {organ}/{c} never counts as a direct cut");
            }
        }

        private IEnumerator Pull(int organ, float seconds, bool capture = false, bool tray = true, int slot = -1)
        {
            yield return Select(Key.Digit1, ToolSlot.Hands);
            Vector3 c = table.OrganPosition(organ);
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == organ, Around(c, table.transform.forward, table.transform.right, 0.012f), "organ " + organ);
            // v05 layout: the liver overlaps the centre of the right kidney on screen; look a little further out like a player.
            if (!aimed) yield return AimAt(t => t.kind == TargetKind.Organ && t.index == organ, Around(c, table.transform.forward, table.transform.right, 0.024f), "organ " + organ + " (wider)");
            if (!aimed) { Check(false, $"organ {organ} found under the cursor"); yield break; }
            yield return Button(true);
            Vector2 from = mPos; float dist = Cam.pixelHeight * table.Tuning.pullScreenFraction * 1.35f;
            float t0 = Time.time; bool shot = false;
            while (Time.time - t0 < seconds && !S.organs[organ].removed)
            {
                float t = (Time.time - t0) / seconds;
                mPos = from + new Vector2(0, dist * t); PushMouse();
                if (capture && !shot && t > 0.45f) { Shot(table.Tuning.sharedAbdomen ? "10_pulling_organ" + organ : "10_pulling"); shot = true; }
                yield return null;
            }
            float end = Time.time + 1f; while (!S.organs[organ].removed && Time.time < end) { mPos = from + new Vector2(0, dist); PushMouse(); yield return null; }
            Check(S.organs[organ].removed, $"organ {organ} pulled out with empty hands");
            yield return Button(false);
            yield return new WaitForSeconds(0.25f);
            yield return Settle();
            var held = player.GetComponent<OnlyVolunteers.Inventory.NetworkInventory>().PhysicalItem;
            Check(held != null, "detached organ is in hand (held at the cursor)");
            if (!tray || held == null) yield break;
            int target = slot >= 0 ? slot : FreeSlot();
            var pose = table.OrganSlotPose(target);
            var trayCenter = table.TrayAnchor != null ? table.TrayAnchor.position + table.transform.up * 0.7f : pose.position;
            yield return AimAt(t => t.kind == TargetKind.Tray || t.kind == TargetKind.BloodBag || t.kind == TargetKind.Item, new[] { pose.position + pose.up * 0.02f, pose.position, pose.position - table.transform.forward * 0.04f, pose.position + table.transform.right * 0.04f, trayCenter }, "tray slot " + target);
            if (!aimed) { Check(false, "tray found under the cursor"); yield break; }
            if (capture) Shot(table.Tuning.sharedAbdomen ? "11_organ_card_held_organ" + organ : "11_organ_card_held");
            yield return Click();
            yield return WaitFor(() => player.GetComponent<OnlyVolunteers.Inventory.NetworkInventory>().PhysicalItem == null, 1.5f, "click tray -> organ placed");
            yield return new WaitForSeconds(0.6f);
            float nearest = 9f; for (int i = 0; i < 3; i++) nearest = Mathf.Min(nearest, Vector3.Distance(held.transform.position, table.OrganSlotPose(i).position));
            Check(nearest < 0.12f, $"organ rests in a tray organ slot ({nearest:F2} m)");
        }
        private int FreeSlot()
        {
            for (int i = 0; i < 3; i++)
            {
                var pose = table.OrganSlotPose(i); bool free = true;
                foreach (var item in table.ServerItems) if (item != null && item.Holder == null && Vector3.Distance(item.transform.position, pose.position) < 0.08f) free = false;
                if (free) return i;
            }
            return 0;
        }

        private void LogOrgans()
        {
            for (int i = 0; i < 3; i++)
            {
                var o = S.organs[i];
                Line($"ORGAN {i} grade={o.Grade} intrinsic={o.intrinsicGrade} damage={o.damage} removed={o.removed} chance={o.deathChance:F2} rolled={o.rolled:F2} rollDone={o.rollCompleted} directCuts={o.directCuts} yanks={o.yanks} sloppy={o.sloppyApplied}");
            }
        }

        // ---------- scenarios ----------
        private IEnumerator Loop(bool fresh)
        {
            if (fresh && (S.onTable || S.extracted > 0 || !S.alive)) { yield return Tap(Key.F10); yield return new WaitForSeconds(1f); }
            Check(!S.onTable && S.alive && S.knockedOut, "fresh patient knocked out on the floor");
            yield return CarryPatientOntoTable();
            yield return EnterTable();
            Shot("01b_table_view");
            yield return Straps(true);
            Shot("03_straps_closed");
            Check(OperationStraps.AllClosed(S, table.Tuning), "all straps closed");
            yield return Inject(2.0f, "main");
            yield return WaitFor(() => S.Sleeping, 1f, "patient asleep after a 2 s hold");
            Check(S.alive && S.residual >= table.Tuning.suitableMinimum && S.residual <= table.Tuning.suitableMaximum, $"dose in the suitable range ({S.residual:F2})");
            yield return new WaitForSeconds(0.6f);
            Shot("05a_asleep");
            yield return CollectBlood(0);
            // kidney L
            yield return Cut(0, false, true);
            yield return Snip(0, true);
            yield return Pull(0, 0.9f, true);
            yield return MoveTo(Scr(table.OrganSlotPose(0).position), 0.2f);
            yield return Select(Key.Digit1, ToolSlot.Hands);
            yield return AimAt(t => t.kind == TargetKind.Item, new[] { table.OrganSlotPose(0).position + table.transform.up * 0.03f, table.OrganSlotPose(0).position }, "extracted kidney on tray");
            yield return new WaitForSeconds(0.2f);
            Shot("12_organ_card");
            Check(view.Current.item != null && view.Current.item.IsOrgan, "hovering an extracted organ shows its card");
            // kidney R and liver
            yield return Cut(1);
            yield return Snip(1);
            yield return Pull(1, 0.9f);
            yield return Cut(2);
            yield return Snip(2);
            yield return Pull(2, 0.9f);
            yield return new WaitForSeconds(0.5f);
            LogOrgans();
            for (int i = 0; i < 3; i++)
            {
                var o = S.organs[i];
                Check(o.removed && o.Grade == o.intrinsicGrade - o.damage, $"organ {i} extracted, grade {OperationText.Tier(o.Grade)}");
                Check(o.rollCompleted || !S.alive, $"organ {i} death roll recorded (chance {o.deathChance:F2})");
            }
            // One blood portion: +10 points on the first kidney. Lead decision 2026-10-18: the second kidney (extracted here
            // second) is a vital removal, chance 1, and kills; the liver then comes out of a corpse, which is never rolled.
            float[] expected = table.Tuning.liverOrBothKidneysFatal ? new[] { 0.2f, 1f, 0f } : new[] { 0.2f, 0.3f, 0.4f };
            for (int i = 0; i < 3; i++) Check(Mathf.Abs(S.organs[i].deathChance - expected[i]) < 0.001f, $"organ {i} chance {S.organs[i].deathChance:F2} = {expected[i]:F2}");
            Check(S.extracted == 3 && table.ServerItems.Count == 4, $"three organs + one bag exist exactly once ({table.ServerItems.Count} items)");
            var pres = table.GetComponent<OperationPresentation>();
            bool hidden = true;
            foreach (var t in table.PatientObject.GetComponentsInChildren<Transform>(true)) if (t.name == "Organ" && t.gameObject.activeInHierarchy) hidden = false;
            Check(hidden, "organ visuals in the body are hidden after extraction");
            yield return MoveTo(Scr(table.OrganSlotPose(1).position + table.transform.up * 0.25f), 0.3f);
            yield return new WaitForSeconds(0.3f);
            Shot("13_tray_results");
            // local zoom (a fine adjustment of the OPERATION view)
            if (view.CameraMode != TableCamera.Operation) { yield return Tap(Key.Tab); yield return new WaitForSeconds(0.45f); }
            yield return MoveTo(Scr(table.SitePoint(2, Vector3.zero)), 0.2f);
            yield return Scroll(120f); yield return Scroll(120f);
            yield return new WaitForSeconds(0.5f);
            Check(view.Zoom > 0.2f, $"mouse wheel zooms locally ({view.Zoom:F2})");
            Shot("14_zoomed");
            yield return Scroll(-120f); yield return Scroll(-120f); yield return Scroll(-120f);
            yield return new WaitForSeconds(0.5f);
            // Take a kidney off the tray and walk away with it: the existing first-person physical carry takes over.
            yield return Select(Key.Digit1, ToolSlot.Hands);
            var inv = player.GetComponent<OnlyVolunteers.Inventory.NetworkInventory>();
            var slot0 = table.OrganSlotPose(0);
            yield return AimAt(t => t.kind == TargetKind.Item, new[] { slot0.position + table.transform.up * 0.03f, slot0.position, slot0.position + table.transform.forward * 0.03f }, "kidney on the tray");
            if (aimed)
            {
                yield return Click();
                yield return WaitFor(() => inv.PhysicalItem != null, 1.5f, "click an organ on the tray -> it is in hand");
                yield return Tap(Key.E);
                yield return WaitFor(() => !view.Active, 1f, "E leaves table mode");
                yield return new WaitForSeconds(0.8f);
                Check(inv.PhysicalItem != null && Vector3.Distance(inv.PhysicalItem.transform.position, player.MotorPosition) < 1.6f, "leaving with an organ hands it to the first-person carry");
                Shot("15_carry_organ_away");
            }
            else
            {
                Check(false, "kidney on the tray found under the cursor");
                yield return Tap(Key.Escape);
                yield return WaitFor(() => !view.Active, 1f, "Esc leaves table mode");
            }
        }

        private IEnumerator Edges()
        {
            // 1) F10 -> fresh patient
            string before = S.patientId;
            yield return Tap(Key.F10);
            yield return WaitFor(() => S.patientId != before && S.alive && !S.onTable && S.extracted == 0, 2f, "F10 gives a fresh patient");
            // 2) awake, unrestrained patient escapes
            yield return Tap(Key.F9);
            yield return WaitFor(() => S.onTable && S.aligned, 1.5f, "F9 places the patient instantly");
            yield return EnterTable();
            Shot("e01_dazed");
            yield return WaitFor(() => S.escapes == 1 && !S.onTable, table.Tuning.dazedSeconds + table.Tuning.escapeSeconds + 2f, "awake unrestrained patient escapes");
            // v03: the escape clip plays with the root kept on PatientRest, then the root lands under the body.
            yield return new WaitForSeconds(1.0f);
            Check(Vector3.Distance(table.PatientBody.transform.position, table.RestPose.position) < 0.05f && !S.onTable, "escape clip plays with the root on PatientRest");
            Shot("e02a_escaping");
            yield return new WaitForSeconds(table.Tuning.escapeFallSeconds - 1.0f + 0.6f);
            var landedRoot = table.PatientBody.transform.position;
            Vector3 landedLocal = table.transform.InverseTransformPoint(landedRoot);
            Check(S.alive && landedRoot.y < table.transform.position.y + 0.45f, "escaped patient fell to the floor alive");
            Check(landedLocal.x < -1.2f, $"he left over his right side, away from the stand (table-local x={landedLocal.x:F2})");
            Transform hipsT = null;
            foreach (var t in table.PatientBody.GetComponentsInChildren<Transform>()) if (t.name == "mixamorig:Hips") hipsT = t;
            if (hipsT != null)
            {
                Vector3 h = table.PatientBody.transform.InverseTransformPoint(hipsT.position);
                Check(new Vector2(h.x, h.z).magnitude < 0.1f && h.y < 0.3f, $"landed pose lies on its root, no pop (hips root-local {h})");
            }
            yield return new WaitForSeconds(1.0f);
            Check(!S.onTable && Vector3.Distance(table.PatientBody.transform.position, landedRoot) < 0.05f, "no snapping back onto the table, no sliding");
            Shot("e02_escaped");
            yield return Tap(Key.Escape);
            yield return new WaitForSeconds(0.4f);
            // 3) panic + rescue: torso only, awake extraction, then a rescue injection
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.5f);
            yield return EnterTable();
            yield return Straps(false);
            yield return Cut(0);
            yield return Snip(0);
            // yank on the way: a one-frame flick
            yield return Select(Key.Digit1, ToolSlot.Hands);
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == 0, Around(table.OrganPosition(0), table.transform.forward, table.transform.right, 0.012f), "organ 0 (yank)");
            int dmg = S.organs[0].damage;
            yield return Button(true);
            mPos += new Vector2(0, Cam.pixelHeight * 0.4f); PushMouse();
            yield return new WaitForSeconds(0.6f);
            Check(S.organs[0].yanks == 1 && S.organs[0].damage == dmg + 1, $"yank: one fast flick costs exactly 1 grade (damage {dmg}->{S.organs[0].damage})");
            yield return WaitFor(() => S.organs[0].removed, 1.5f, "yanked organ still comes out");
            yield return Button(false);
            yield return WaitFor(() => S.Panicking, 1f, "awake extraction -> panic");
            yield return new WaitForSeconds(0.4f);
            Shot("15_panic_banner");
            Check(view.Hud != null && view.Hud.PanicVisible, "panic banner shown");
            yield return RightClick(); // organ to tray
            yield return Inject(2.0f, "rescue");
            yield return WaitFor(() => !S.Panicking && S.alive && S.Sleeping, 1f, "rescue injection inside 8 s cancels the shock");
            // 4) direct cut: a deliberate scalpel click on the organ body (cords snipped first, so nothing else is there)
            yield return Cut(1);
            yield return Snip(1);
            int d1 = S.organs[1].damage;
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            Vector3 c1 = table.OrganPosition(1);
            var directPoints = new List<Vector3>(Around(c1, table.transform.right, table.transform.forward, 0.006f));
            // v02's liver loop crosses the kidney's upper pole; deliberately click its visible lower bean.
            if (table.Tuning.anatomicalLayout)
                foreach (float y in new[] { -0.025f, -0.04f }) foreach (float x in new[] { 0f, -0.012f, 0.012f })
                    directPoints.Add(table.SitePoint(1, new Vector3(x, y, 0.015f)));
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == 1, directPoints, "organ 1 body (direct cut)");
            yield return Click();
            yield return new WaitForSeconds(0.3f);
            Check(S.organs[1].directCuts == 1 && S.organs[1].damage == d1 + 2, $"direct click on the organ: -2 (damage {d1}->{S.organs[1].damage})");
            Shot("e03_direct_cut");
            // dragging the blade across the organ (press elsewhere, move over it) is not a stab
            yield return MoveTo(Scr(table.GuidePosition(2, 0.5f)), 0.15f);
            lmb = true; PushMouse(); yield return Frames(2);
            yield return MoveTo(Scr(table.OrganPosition(1)), 0.25f);
            yield return MoveTo(Scr(table.GuidePosition(0, 0.5f)), 0.25f);
            lmb = false; PushMouse(); yield return Frames(3);
            Check(S.organs[1].directCuts == 1, "dragging the scalpel over the organ never adds a direct cut");
            // 5) a tool falling on the floor returns to its slot
            var scalpel = table.ToolOf(ToolSlot.Scalpel);
            yield return MoveTo(Scr(table.transform.TransformPoint(new Vector3(0.56f, 0.7f, -0.55f))), 0.2f);
            Line($"DROP hover={view.Current.target} at={view.Current.point} scalpel={scalpel.transform.position}");
            yield return Tap(Key.E);
            yield return WaitFor(() => scalpel.Mode == ToolMode.Loose, 1f, "leaving with the scalpel drops it");
            float lowest = 10f; float end = Time.time + 1.6f; float nextTrace = 0f;
            var srb = scalpel.GetComponent<Rigidbody>();
            while (Time.time < end)
            {
                lowest = Mathf.Min(lowest, scalpel.transform.position.y - table.transform.position.y);
                if (Time.time >= nextTrace) { nextTrace = Time.time + 0.25f; Line($"DROP trace mode={scalpel.Mode} pos={scalpel.transform.position} rb={srb.position} kin={srb.isKinematic} vel={srb.linearVelocity}"); }
                yield return null;
            }
            Check(lowest < 0.25f, $"dropped scalpel fell to the floor (y={lowest:F2})");
            yield return WaitFor(() => scalpel.Mode == ToolMode.Docked, 3f, "scalpel flew back to its tray slot after ~2 s");
            Check(Vector3.Distance(scalpel.transform.position, table.DockPose(scalpel).position) < 0.01f, "scalpel is exactly in its slot");
            // 6) overdose from zero and the dead-patient message
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.5f);
            yield return EnterTable();
            yield return Straps(false);
            yield return Inject(4.8f, "overdose");
            yield return WaitFor(() => !S.alive && S.deathCause == DeathCause.Overdose, 1f, "holding ~4.8 s more kills by overdose");
            yield return new WaitForSeconds(0.5f);
            Shot("e04_dead");
            Check(view.Hud.DeadVisible, "death banner «ПАЦИЕНТ МЁРТВ» shown");
            Check(S.organs[0].damage >= table.Tuning.earlyOverdoseLoss, "early overdose costs every organ 2 grades");
            float r = S.residual;
            yield return AimBody(t => t.IsInjectionSite, new[] { BodyPart.ArmR, BodyPart.ShoulderR, BodyPart.Neck }, "arm on corpse");
            lmb = true; PushMouse(); float e2 = Time.time + 0.6f; string seen = "";
            while (Time.time < e2) { PushMouse(); if (view.Hud.CurrentHint.Contains("мёртв")) seen = view.Hud.CurrentHint; yield return null; }
            lmb = false; PushMouse(); yield return Frames(3);
            Check(seen.Length > 0 && Mathf.Approximately(r, S.residual), $"injecting a corpse is refused with a clear message («{seen}»)");
            Shot("e05_dead_hint");
            // walking away: holding W for a moment leaves table mode (a tap does not)
            yield return HoldKey(Key.W, 0.06f);
            Check(view.Active, "a short W tap keeps table mode");
            yield return HoldKey(Key.W, 0.6f);
            yield return WaitFor(() => !view.Active, 1f, "holding W > 0.2 s leaves table mode");
        }

        private IEnumerator Rotated()
        {
            yield return TableHome(); // v04: earlier scenarios' ragdoll carries may have nudged the free gurney
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            var body = table.GetComponent<Rigidbody>();
            Vector3 p = table.transform.position + new Vector3(1.4f, 0f, 0.6f);
            Quaternion q = Quaternion.Euler(0f, 90f, 0f) * table.transform.rotation;
            body.position = p; body.rotation = q; table.transform.SetPositionAndRotation(p, q);
            body.linearVelocity = Vector3.zero; body.angularVelocity = Vector3.zero;
            yield return new WaitForSeconds(1f);
            Line($"TABLE moved to {table.transform.position} rot={table.transform.eulerAngles}");
            yield return CarryPatientOntoTable();
            yield return EnterTable();
            Shot("r01_rotated");
            yield return Straps(false);
            yield return Inject(2.0f, "rotated");
            yield return WaitFor(() => S.Sleeping, 1f, "rotated table: asleep");
            yield return Cut(2);
            yield return Snip(2);
            yield return Pull(2, 0.9f);
            Check(S.organs[2].removed && S.organs[2].damage == 0, "rotated+moved table: liver out with no damage (table-local validation)");
            yield return CollectBlood(1);
            Check(table.Frozen && table.GetComponent<Rigidbody>().isKinematic, "the gurney is frozen while someone is at the table");
            yield return Tap(Key.Escape);
            yield return new WaitForSeconds(0.3f);
            Check(!table.Frozen && !table.GetComponent<Rigidbody>().isKinematic, "the gurney is free again after everyone left");
            // Push the gurney (as the physical grab would move it): the patient on it follows the table pose.
            var tb = table.GetComponent<Rigidbody>();
            Vector3 moved = table.transform.position + table.transform.forward * 0.8f;
            tb.position = moved; table.transform.position = moved;
            yield return new WaitForSeconds(0.3f);
            float ride = Vector3.Distance(table.PatientBody.transform.position, table.RestPose.position);
            Check(ride < 0.01f, $"the patient rides along when the gurney moves ({ride:F3} m, table {table.transform.position}, v={tb.linearVelocity.magnitude:F2})");
        }

        // ---------- v03 animation evidence (patient states through the real table camera) ----------
        /// <summary>Extra camera, no HUD, table-local placement: layout overviews and the escape seen from aside.</summary>
        private void Overview(string name, Vector3 local, Vector3 lookLocal)
        {
            if (output == null) return;
            var go = new GameObject("OpsOverviewCam");
            var cam = go.AddComponent<Camera>();
            cam.fieldOfView = 50f; cam.nearClipPlane = 0.05f;
            Vector3 p = table.transform.TransformPoint(local);
            go.transform.SetPositionAndRotation(p, Quaternion.LookRotation(table.transform.TransformPoint(lookLocal) - p));
            var target = RenderTexture.GetTemporary(captureWidth, captureHeight, 24, RenderTextureFormat.ARGB32);
            cam.targetTexture = target; cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = target;
            var tex = new Texture2D(captureWidth, captureHeight, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, captureWidth, captureHeight), 0, 0); tex.Apply();
            RenderTexture.active = prev; cam.targetTexture = null; RenderTexture.ReleaseTemporary(target);
            File.WriteAllBytes(Path.Combine(output, name + ".png"), tex.EncodeToPNG()); Destroy(tex); Destroy(go);
            Line("OVERVIEW " + name);
        }
        private string AnimState()
        {
            var rig = table.PatientRig; if (rig == null || rig.Animator == null) return "?";
            var info = rig.Animator.GetCurrentAnimatorStateInfo(0);
            foreach (var n in new[] { "TableAwake", "TableAsleep", "Struggle", "Panic", "Dead", "EscapeFall", "KnockedOut", "ShockDeath" })
                if (info.IsName(n)) return n;
            return "?";
        }
        private IEnumerator Evidence()
        {
            var side = new Vector3(2.3f, 1.55f, -1.1f); var sideLook = new Vector3(-0.2f, 0.65f, 0.05f);
            var far = new Vector3(-3.4f, 2.0f, 1.4f); var farLook = new Vector3(-1.1f, 0.35f, -0.35f);
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            Overview("v00_knocked_out_floor", new Vector3(-2.4f, 1.5f, 1.2f), new Vector3(-1.15f, 0.1f, -0.1f));
            Check(AnimState() == "KnockedOut", "fresh patient on the floor plays KnockedOut (" + AnimState() + ")");
            yield return Tap(Key.F9);
            yield return WaitFor(() => S.onTable && S.aligned, 1.5f, "F9 places the patient");
            yield return new WaitForSeconds(0.5f);
            Overview("v01_stand_overview", new Vector3(-1.9f, 2.1f, -2.0f), new Vector3(0.15f, 0.62f, 0.15f));
            Overview("v01b_stand_far_side", side, sideLook);
            yield return EnterTable();
            frameIndex = 0; recording = true; StartCoroutine(Record());
            yield return new WaitForSeconds(0.6f);
            Check(AnimState() == "TableAwake", "awake (dazed) on the table plays TableAwake (" + AnimState() + ")");
            Shot("v02_awake_straps_open");
            Overview("v02b_straps_open_side", side, sideLook);
            yield return Straps(true);
            yield return WaitFor(() => !S.Dazed, table.Tuning.dazedSeconds + 1f, "daze over, strapped");
            yield return new WaitForSeconds(1.0f);
            Check(AnimState() == "Struggle", "strapped and awake plays Struggle (" + AnimState() + ")");
            Shot("v03_struggle");
            yield return new WaitForSeconds(0.45f);
            Shot("v03b_struggle");
            yield return Inject(2.0f, "evidence");
            yield return WaitFor(() => S.Sleeping, 1.5f, "asleep after a 2 s hold");
            yield return new WaitForSeconds(1.2f);
            Check(AnimState() == "TableAsleep", "asleep plays TableAsleep (" + AnimState() + ")");
            Shot("v04_asleep");
            // Panic: he wakes up after an organ came out (evidence shortcut: the server state is set directly).
            S.extracted = 1; S.sleepRemaining = 0.05f;
            yield return WaitFor(() => S.Panicking, 2f, "wakes up mid-operation -> panic");
            yield return new WaitForSeconds(0.7f);
            Check(AnimState() == "Panic", "panic plays Panic (" + AnimState() + ")");
            Shot("v05_panic");
            yield return new WaitForSeconds(0.5f);
            Shot("v05b_panic");
            yield return Inject(1.8f, "rescue");
            yield return WaitFor(() => !S.Panicking && S.Sleeping, 2f, "rescue injection -> asleep again");
            yield return new WaitForSeconds(1.0f);
            Shot("v06_rescued");
            yield return new WaitForSeconds(0.5f);
            recording = false;
            // Shock death: panic with the torso strapped runs out.
            S.sleepRemaining = 0.05f;
            yield return WaitFor(() => S.Panicking, 2f, "panic again");
            yield return WaitFor(() => !S.alive, table.Tuning.rescueSeconds + 2f, "no rescue -> death");
            Check(S.deathCause == DeathCause.Shock, "death cause Shock (" + S.deathCause + ")");
            yield return new WaitForSeconds(0.3f);
            Check(AnimState() == "ShockDeath", "shock death plays ShockDeath (" + AnimState() + ")");
            Shot("v07_shockdeath_a");
            yield return new WaitForSeconds(0.45f);
            Shot("v07_shockdeath_b");
            yield return new WaitForSeconds(2.2f);
            Check(AnimState() == "Dead", "after ShockDeath the patient plays Dead (" + AnimState() + ")");
            Shot("v08_dead");
            // Escape of an awake, unstrapped patient.
            yield return Tap(Key.Escape); yield return new WaitForSeconds(0.4f);
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.5f);
            yield return EnterTable();
            frameIndex = 100000; recording = true; StartCoroutine(Record());
            yield return WaitFor(() => S.escapes == 1, table.Tuning.dazedSeconds + table.Tuning.escapeSeconds + 2f, "awake unrestrained patient escapes");
            float t0 = Time.time;
            foreach (float at in new[] { 0.35f, 0.9f, 1.45f, 2.0f, 2.6f, 3.6f })
            {
                while (Time.time - t0 < at) yield return null;
                string tag = "v09_escape_" + ((int)(at * 100)).ToString("D3");
                Overview(tag + "_side", far, farLook);
                Shot(tag + "_table_cam");
            }
            recording = false;
            Check(AnimState() == "KnockedOut" && !S.onTable, "landed: KnockedOut on the floor (" + AnimState() + ")");
        }

        private IEnumerator Hud720()
        {
            // Same view at 1280x720 to check the layout scales.
            if (S.onTable == false) { yield return Tap(Key.F9); yield return new WaitForSeconds(0.5f); }
            yield return EnterTable();
            Cam.targetTexture = null; rt.Release(); Destroy(rt);
            rt = new RenderTexture(1280, 720, 24, RenderTextureFormat.ARGB32); rt.Create(); Cam.targetTexture = rt;
            yield return Frames(3);
            yield return AimBody(t => !t.IsNone, new[] { BodyPart.Torso, BodyPart.ArmR }, "patient");
            Canvas.ForceUpdateCanvases(); Cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(Path.Combine(output, "16_hud_1280x720.png"), tex.EncodeToPNG()); Destroy(tex);
            Line("SHOT 16_hud_1280x720");
            yield return Tap(Key.Escape);
        }

        // ---------- two processes ----------
        private IEnumerator Settle() { yield return new WaitForSeconds(table.IsServerInitialized ? 0.05f : 0.3f); }
        private IEnumerator NetHost()
        {
            yield return WaitFor(() => FindObjectsByType<NetworkPlayer>().Length >= 2, 40f, "client joined");
            yield return CarryPatientOntoTable();
            yield return EnterTable();
            yield return Straps(true);
            yield return Inject(2.0f, "main");
            yield return WaitFor(() => S.Sleeping, 1f, "host: patient asleep");
            yield return Cut(0);
            yield return Snip(0);
            yield return Select(Key.Digit1, ToolSlot.Hands); // the scalpel goes back to the tray for the client
            Shot("n01_host_ready");
            yield return WaitFor(() => table.ParticipantCount >= 2, 60f, "both players at the table");
            yield return Pull(0, 0.9f);
            yield return new WaitForSeconds(0.6f);
            Shot("n02_host_two_players");
            yield return WaitFor(() => S.organs[1].removed, 90f, "client extracted kidney R (seen on host)");
            yield return WaitFor(() => S.organs[2].Opened && S.organs[2].Released, 60f, "client opened the liver and snipped its cords");
            yield return WaitFor(() => table.View.pullers[2] >= 1, 30f, "client started pulling the liver");
            // Join the pull: two holders on one organ (spec 7).
            yield return Select(Key.Digit1, ToolSlot.Hands);
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == 2, Around(table.OrganPosition(2), table.transform.forward, table.transform.right, 0.012f), "liver (joint pull)");
            yield return Button(true);
            Vector2 from = mPos; float dist = Cam.pixelHeight * table.Tuning.pullScreenFraction * 1.35f;
            int peak = 0; float t0 = Time.time; bool shot = false; float k = 0f;
            while (!S.organs[2].removed && Time.time - t0 < 25f)
            {
                peak = Mathf.Max(peak, table.View.pullers[2]);
                bool clientGone = table.ParticipantCount == 1;
                // ease up while both hold (the shared average stays below the pop point), then finish alone, smoothly
                k = clientGone ? Mathf.MoveTowards(k, 1f, Time.deltaTime * 0.45f) : Mathf.MoveTowards(k, 0.5f, Time.deltaTime * 0.45f);
                mPos = from + new Vector2(0, dist * k); PushMouse();
                if (!shot && peak >= 2) { Shot("n03_host_joint_pull"); shot = true; }
                yield return null;
            }
            Check(peak >= 2, $"two players held the liver together (peak holders {peak})");
            Check(S.organs[2].removed, "host finished the joint pull after the client left");
            yield return Button(false);
            yield return new WaitForSeconds(0.3f);
            yield return RightClick();
            yield return new WaitForSeconds(0.8f);
            var ids = new HashSet<string>(); foreach (var item in table.ServerItems) if (item != null) ids.Add(item.Identity);
            Check(S.extracted == 3 && table.ServerItems.Count == 3 && ids.Count == 3, $"three organs, each exactly once ({table.ServerItems.Count} items, {ids.Count} ids)");
            Check(S.organs[1].removed && ids.Contains(S.organs[1].outputId), "the client's kidney survived the disconnect (no rollback)");
            var scalpel = table.ToolOf(ToolSlot.Scalpel);
            Check(scalpel != null && (scalpel.Mode == ToolMode.Docked || scalpel.Mode == ToolMode.Returning), "the client's scalpel is back in the tray");
            LogOrgans();
            Shot("n04_host_done");
            yield return Tap(Key.Escape);
        }
        private IEnumerator NetClient()
        {
            yield return WaitFor(() => S != null && S.onTable && S.aligned && S.Sleeping && OperationStraps.Held(S, table.Tuning), 120f, "client sees the host's prepared, sleeping patient");
            Teleport(TableFoot(new Vector3(-1.2f, 0f, 1.0f)));
            yield return Frames(2);
            LookAt(table.transform.TransformPoint(new Vector3(0, 0.75f, 0.2f)));
            yield return Frames(4);
            yield return Tap(Key.E);
            yield return WaitFor(() => view.Active, 2f, "client: E -> table mode");
            yield return new WaitForSeconds(0.6f);
            Check(Vector3.Distance(Cam.transform.position, view.ViewPose.position) < 0.05f, "client uses the same shared camera");
            yield return WaitFor(() => S.organs[0].Released && table.ToolOf(ToolSlot.Scalpel) != null && table.ToolOf(ToolSlot.Scalpel).Mode == ToolMode.Docked, 90f, "scalpel free for the client");
            yield return Cut(1);
            yield return Snip(1);
            yield return Pull(1, 0.9f, false, true, 1);
            Shot("n10_client_kidneyR");
            yield return Cut(2);
            yield return Snip(2);
            // Pull the liver gently and keep holding; the host joins; then this client vanishes mid-pull.
            yield return Select(Key.Digit1, ToolSlot.Hands);
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == 2, Around(table.OrganPosition(2), table.transform.forward, table.transform.right, 0.012f), "liver");
            yield return Button(true);
            Vector2 from = mPos; float t0 = Time.time;
            while (Time.time - t0 < 1f) { mPos = from + new Vector2(0, Cam.pixelHeight * table.Tuning.pullScreenFraction * 0.45f * (Time.time - t0)); PushMouse(); yield return null; }
            yield return WaitFor(() => table.View != null && table.View.pullers[2] >= 2, 30f, "client sees two holders on the liver");
            yield return new WaitForSeconds(0.8f);
            Line($"CLIENT quitting mid-pull liverPull={S.organs[2].pull:F3}");
            Shot("n11_client_joint_pull");
            if (output != null) File.WriteAllText(Path.Combine(output, "client-state.json"), JsonUtility.ToJson(table.State, true));
            Finish();
            Application.Quit();
        }
#else
        public void Begin(string scenario) { }
#endif
    }
}
