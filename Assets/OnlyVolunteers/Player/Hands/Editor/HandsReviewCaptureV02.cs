#if UNITY_EDITOR
using System.IO;
using System.Reflection;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Session;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Player.Hands.EditorTools
{
    /// <summary>
    /// PLAYER HANDS review shots (Hands_2026-10-30 v02): fixed first-person (the player's own camera, 876x715) and
    /// friend's-view (a side camera relative to the player, 700x571) renders for before/after sheets. Editor-only dev
    /// tool, called from the MCP console in a Play session whose saves are protected (Protect: no autosave, a test save
    /// slot). Presentation only: it moves the player, aims the view and drives the existing PhysicsGrabber script hooks
    /// the capture scenarios use; nothing here is part of the game.
    /// </summary>
    public static class HandsReviewCaptureV02
    {
        public static string Dir = @"C:\Dev\Game\Working\Reviews\Hands_2026-10-30\v02";
        public const string TestSlot = "hands_review_v02_test.json";

        private static readonly FieldInfo YawField = typeof(KccFirstPersonInput).GetField("_yaw", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly FieldInfo PitchField = typeof(KccFirstPersonInput).GetField("_pitch", BindingFlags.Instance | BindingFlags.NonPublic);

        public static GreyboxKccPawn Pawn => CaptureDirector.Instance != null ? CaptureDirector.Instance.Pawn : Object.FindAnyObjectByType<GreyboxKccPawn>();
        private static KccFirstPersonInput Kcc => Pawn != null ? Pawn.GetComponentInChildren<KccFirstPersonInput>(true) : null;
        private static PhysicsGrabber Grabber => Pawn != null ? Pawn.GetComponentInChildren<PhysicsGrabber>(true) : null;

        private const string ArmedKey = "OV.HandsReviewCaptureV02.Protect";

        // The protection must survive a domain reload in the middle of a Play session (another tool editing scripts makes
        // Unity recompile and reset statics, CaptureTestHooks.SaveSlot included): re-armed after every reload while
        // playing, and once more as Play is being left, before CaptureDirector's exit save.
        [InitializeOnLoadMethod]
        private static void Rearm()
        {
            EditorApplication.playModeStateChanged -= OnPlayMode;
            EditorApplication.playModeStateChanged += OnPlayMode;
            if (EditorApplication.isPlayingOrWillChangePlaymode && SessionState.GetBool(ArmedKey, false))
                EditorApplication.delayCall += () => { if (EditorApplication.isPlaying) Protect(); };
        }

        private static void OnPlayMode(PlayModeStateChange change)
        {
            if (!SessionState.GetBool(ArmedKey, false)) return;
            if (change == PlayModeStateChange.ExitingPlayMode) Protect();
            else if (change == PlayModeStateChange.EnteredEditMode) SessionState.SetBool(ArmedKey, false);
        }

        /// <summary>No autosave, no exit save into the player's slot: everything this session would write goes to TestSlot.</summary>
        public static string Protect()
        {
            SessionState.SetBool(ArmedKey, true);
            CaptureTestHooks.SaveSlot = TestSlot;
            var d = CaptureDirector.Instance;
            if (d != null) d.AutosaveSeconds = 0f;
            return $"slot={CaptureTestHooks.SaveSlot} autosave={(d != null ? d.AutosaveSeconds : -1f)} director={(d != null)} pawn={(Pawn != null)}";
        }

        public static void Place(Vector3 feet, float yaw, float pitch)
        {
            var pawn = Pawn;
            pawn.Teleport(feet, yaw);
            Look(yaw, pitch);
        }

        public static void Look(float yaw, float pitch)
        {
            var kcc = Kcc;
            YawField?.SetValue(kcc, Mathf.Repeat(yaw, 360f));
            PitchField?.SetValue(kcc, Mathf.Clamp(pitch, -85f, 85f));
            if (Pawn != null && Pawn.ViewCamera != null) Pawn.ViewCamera.transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
        }

        public static void LookAt(Vector3 world)
        {
            Vector3 eye = Pawn.ViewCamera.transform.position;
            Vector3 d = world - eye;
            Look(Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg, -Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg);
        }

        /// <summary>Nearest NPC to the player that is free or down, moved 'ahead' metres in front of the feet (free:
        /// standing there; then knocked down by a plain scripted Hit like the capture scenarios).</summary>
        public static GreyboxNpc StageNpc(float ahead, bool knockDown)
        {
            var pawn = Pawn;
            GreyboxNpc best = null;
            float bestD = float.MaxValue;
            foreach (var n in GreyboxNpc.All)
            {
                if (n == null || !n.isActiveAndEnabled) continue;
                if (n.State != NpcState.Free) continue;
                float dd = (n.transform.position - pawn.Position).sqrMagnitude;
                if (dd < bestD) { bestD = dd; best = n; }
            }
            if (best == null) return null;
            Vector3 fwd = Pawn.Body.forward; fwd.y = 0f; fwd.Normalize();
            var cc = best.GetComponent<CharacterController>();
            bool was = cc.enabled; cc.enabled = false;
            best.transform.SetPositionAndRotation(pawn.Position + fwd * ahead, Quaternion.LookRotation(-fwd));
            cc.enabled = was;
            UnityEngine.Physics.SyncTransforms();
            if (knockDown) best.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, best.Center);
            best.StunLeft = best.StunTotal = 600f; // stays down for the shots
            return best;
        }

        public static GreyboxNpc Npc(int index) => index >= 0 && index < GreyboxNpc.All.Count ? GreyboxNpc.All[index] : null;

        public static bool Grab(Vector3 point, float hold)
        {
            var g = Grabber;
            g.ScriptDriven = true;
            LookAt(point);
            bool ok = g.ScriptGrab();
            if (ok) g.PointHoldDistance = hold;
            return ok;
        }

        public static void Release()
        {
            var g = Grabber;
            if (g != null && g.IsHolding) g.ScriptRelease();
            if (g != null) g.ScriptDriven = false;
        }

        public static void Hold(float distance) { var g = Grabber; if (g != null && g.IsHolding) g.PointHoldDistance = distance; }

        public static void Dress(string top, string topColour = null)
        {
            var arms = PlayerArmsV01.Local;
            if (arms == null) return;
            var look = AppearanceProfileV01.Load().Copy();
            look.Set(AppearanceSlot.Top, top);
            if (!string.IsNullOrEmpty(topColour)) look.Set(AppearanceSlot.TopColour, topColour);
            arms.FirstPerson?.Dress(look); arms.Body?.Dress(look); arms.Echo?.Dress(look);
        }

        public static void Restyle() { var arms = PlayerArmsV01.Local; var look = AppearanceProfileV01.Load(); arms?.FirstPerson?.Dress(look); arms?.Body?.Dress(look); arms?.Echo?.Dress(look); }

        public static string Fp(string file, int w = 876, int h = 715)
        {
            var cam = Pawn.ViewCamera;
            return Render(cam, file, w, h);
        }

        /// <summary>Friend's view: a camera at the player's feet + yaw-relative offset (x right, y up, z forward) looking at
        /// the feet + lookLocal (same frame). The player's own first-person arms are hidden for the render.</summary>
        public static string Tp(string file, Vector3 offset, Vector3 lookLocal, float fov = 50f, int w = 700, int h = 571)
        {
            var pawn = Pawn;
            float yaw = pawn.ViewCamera.transform.eulerAngles.y;
            Quaternion frame = Quaternion.Euler(0f, yaw, 0f);
            Vector3 feet = pawn.Position;
            var go = new GameObject("[Hands review] TP camera");
            try
            {
                var cam = go.AddComponent<Camera>();
                cam.CopyFrom(pawn.ViewCamera);
                cam.fieldOfView = fov;
                cam.nearClipPlane = 0.05f;
                cam.cullingMask = pawn.ViewCamera.cullingMask;
                var src = pawn.ViewCamera.GetComponent<UniversalAdditionalCameraData>();
                var dst = go.GetComponent<UniversalAdditionalCameraData>() ?? go.AddComponent<UniversalAdditionalCameraData>();
                if (src != null) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; }
                go.transform.position = feet + frame * offset;
                go.transform.rotation = Quaternion.LookRotation(feet + frame * lookLocal - go.transform.position);
                var arms = PlayerArmsV01.Local;
                arms?.FirstPerson?.SetVisible(false);
                string r = Render(cam, file, w, h);
                arms?.FirstPerson?.SetVisible(true);
                return r;
            }
            finally { Object.DestroyImmediate(go); }
        }

        private static string Render(Camera cam, string file, int w, int h)
        {
            Directory.CreateDirectory(Dir);
            var rt = RenderTexture.GetTemporary(w, h, 24, RenderTextureFormat.ARGB32);
            rt.antiAliasing = 4;
            var prev = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            cam.targetTexture = prev;
            var active = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = active;
            RenderTexture.ReleaseTemporary(rt);
            string path = Path.Combine(Dir, file);
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            return path;
        }

        public static string State()
        {
            var arms = PlayerArmsV01.Local;
            var pawn = Pawn;
            if (arms == null || pawn == null) return "no local arms / pawn";
            var cam = pawn.ViewCamera.transform;
            return $"feet={pawn.Position:F2} yaw={cam.eulerAngles.y:F1} pitch={Mathf.DeltaAngle(0f, cam.eulerAngles.x):F1} intent={arms.Intent.Source} " +
                   $"state={arms.State} holding={(Grabber != null && Grabber.IsHolding)} hold={(Grabber != null ? Grabber.PointHoldDistance : 0f):F2} " +
                   $"fpStretch={(arms.FirstPerson != null ? arms.FirstPerson.StretchShown[0] : 0f):F2}/{(arms.FirstPerson != null ? arms.FirstPerson.StretchShown[1] : 0f):F2} " +
                   $"tpStretch={(arms.Body != null ? arms.Body.StretchShown[0] : 0f):F2}/{(arms.Body != null ? arms.Body.StretchShown[1] : 0f):F2} " +
                   $"fpDrawn={(arms.FirstPerson != null && arms.FirstPerson.Drawn.Count > 0 && arms.FirstPerson.Drawn[0] != null && arms.FirstPerson.Drawn[0].enabled)}";
        }

        /// <summary>The Q path as GreyboxInteractor runs it after its swing gate (a real FistHit on the NPC: it advances his
        /// repeat sequence), then the arms' one cue. Returns the contact.</summary>
        public static string RealPunch(GreyboxNpc npc)
        {
            var pawn = Pawn;
            var interactor = pawn.GetComponentInChildren<GreyboxInteractor>(true);
            WeaponStun weapon = interactor != null ? interactor.CurrentWeapon : WeaponStun.Fist;
            Vector3 head = npc.Center + Vector3.up * 0.45f;
            LookAt(head);
            Transform eye = pawn.ViewCamera.transform;
            var ray = new Ray(eye.position, (head - eye.position).normalized);
            var c = npc.FistHit(weapon, npc.ZoneAlong(ray), pawn.Position, head);
            PlayerArmsV01.LocalPunch(true, head, c.Multiplier);
            return $"contact #{c.Index} x{c.Multiplier:0.00} stun+{c.Stun:0.0}s stunned={c.Stunned} -> {npc.State} left={npc.StunLeft:0.0}s";
        }

        /// <summary>Presentation only (no hit): the arms' cue with a frozen time for key-pose shots.</summary>
        public static void ShowPunch(bool landed, Vector3 target, float strength, float freezeAt)
        {
            PlayerArmsV01.DebugPunchFreeze = freezeAt;
            PlayerArmsV01.LocalPunch(landed, target, strength);
        }

        public static void Unfreeze() { PlayerArmsV01.DebugPunchFreeze = -1f; Time.timeScale = 1f; }
    }
}
#endif
