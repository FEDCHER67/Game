using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>What the workshop mechanic is doing (server-chosen, synced as a byte; MECHANIC_W86 v01).</summary>
    public enum MechanicAction : byte
    {
        Idle = 0,
        /// <summary>Following his route (the clip follows the speed: walk, or idle while he waits).</summary>
        Walk = 1,
        InspectPart = 2,
        WipeBench = 3,
        CheckBay = 4,
        GagWrenchGun = 5,
        GagCockNod = 6,
        /// <summary>Attending a player: Mech_Attend_Enter, then Mech_Attend_Loop.</summary>
        Attend = 7,
        AttendExit = 8,
        /// <summary>The upgrade performance (aim, poof, pleased).</summary>
        Upgrade = 9,
    }

    /// <summary>The mechanic's clips: Animator state names of Mechanic_W86_v02.controller (v01 the same) and their lengths
    /// (ArtSource/Characters/MECHANIC_W86/Animations_v03/clips_mechanic_v03.json, 30 fps; v03 kept every length and event frame).</summary>
    public static class MechanicClips
    {
        public const string Idle = "Idle", Walk = "Walk";
        public const string InspectPart = "Mech_Work_InspectPart", WipeBench = "Mech_Work_WipeBench", CheckBay = "Mech_Work_CheckBay";
        public const string GagWrenchGun = "Mech_Gag_WrenchGun", GagCockNod = "Mech_Gag_CockNod";
        public const string AttendEnter = "Mech_Attend_Enter", AttendLoop = "Mech_Attend_Loop", AttendExit = "Mech_Attend_Exit";
        public const string Upgrade = "Mech_Upgrade_Perform";
        public const string WalkRateParam = "WalkRate";
        /// <summary>Authored ground speed of the shared Walk_v04 (SausageBuddy clips.json).</summary>
        public const float WalkClipSpeed = 1.5f;
        public const float AttendEnterSeconds = 0.7667f, AttendLoopSeconds = 3.9667f;

        public static string State(MechanicAction a)
        {
            switch (a)
            {
                case MechanicAction.InspectPart: return InspectPart;
                case MechanicAction.WipeBench: return WipeBench;
                case MechanicAction.CheckBay: return CheckBay;
                case MechanicAction.GagWrenchGun: return GagWrenchGun;
                case MechanicAction.GagCockNod: return GagCockNod;
                case MechanicAction.Attend: return AttendLoop;
                case MechanicAction.AttendExit: return AttendExit;
                case MechanicAction.Upgrade: return Upgrade;
                case MechanicAction.Walk: return Walk;
                default: return Idle;
            }
        }

        /// <summary>Length of a one-shot action's clip (0 = looping / open-ended).</summary>
        public static float Seconds(MechanicAction a)
        {
            switch (a)
            {
                case MechanicAction.InspectPart: return 5.5667f;
                case MechanicAction.WipeBench: return 6.1667f;
                case MechanicAction.CheckBay: return 5.5667f;
                case MechanicAction.GagWrenchGun: return 4.1667f;
                case MechanicAction.GagCockNod: return 3.5667f;
                case MechanicAction.AttendExit: return 0.6667f;
                case MechanicAction.Upgrade: return UpgradePerformance.DefaultClipSeconds;
                default: return 0f;
            }
        }

        public static bool IsWork(MechanicAction a) => a == MechanicAction.InspectPart || a == MechanicAction.WipeBench || a == MechanicAction.CheckBay;
        public static bool IsGag(MechanicAction a) => a == MechanicAction.GagWrenchGun || a == MechanicAction.GagCockNod;
    }

    /// <summary>
    /// Presentation of MECHANIC_W86 (on the prefab root, next to its Animator): plays the action the brain (server, or the
    /// client's copy of the server's state) asks for, cross-faded, at the right time into the clip (a late joiner starts
    /// mid-clip), his carry walk at the real speed, and the face cues of clips_mechanic_v03.json on the Face blend shapes
    /// (Blink, Blink_L, Blink_R, Surprised, Worried, Happy; written after the Animator) plus idle blinks. The wrench never
    /// leaves the right hand: it is skinned rigidly to mixamorig:RightHand and the Animator's HandGrip_R override layer
    /// keeps the finger grip over every clip. It decides nothing: animation events (OnMechanicCue) are presentation only.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class MechanicW86PresenterV01 : MonoBehaviour
    {
        [Tooltip("clips_mechanic_v03.json (face cues per clip; the v01 file has the same format).")]
        public TextAsset FaceCues;
        [Tooltip("Cross-fade between actions (s).")]
        public float Fade = 0.25f;

        [Serializable] private sealed class CueFile { public CueClip[] clips; }
        [Serializable] private sealed class CueClip { public string state; public CueKey[] face_cues; }
        [Serializable] private sealed class CueKey { public string shape; public float seconds; public float value; }

        private static readonly string[] Shapes = { "Blink", "Blink_L", "Blink_R", "Surprised", "Worried", "Happy" };
        private const int BlinkShape = 0;

        private Animator animator;
        private int walkRateId;
        private bool hasWalkRate;
        private string shownState = "";
        private int shownSerial = int.MinValue;
        private MechanicAction shownAction;
        private float shownAge;
        // face
        private readonly Dictionary<string, List<(float t, float v)>[]> tracks = new Dictionary<string, List<(float, float)>[]>();
        private readonly List<(SkinnedMeshRenderer r, int[] index)> faces = new List<(SkinnedMeshRenderer, int[])>();
        private readonly float[] weights = new float[Shapes.Length];
        private float nextBlink, blinkEnd;
        private bool faceReady;

        public MechanicAction ShownAction => shownAction;
        public string ShownState => shownState;
        public string LastCue { get; private set; } = "";

        private void Awake() => Resolve();

        private bool Resolve()
        {
            if (animator == null)
            {
                animator = GetComponent<Animator>();
                if (animator == null) animator = GetComponentInChildren<Animator>(true);
                if (animator != null)
                {
                    walkRateId = Animator.StringToHash(MechanicClips.WalkRateParam);
                    hasWalkRate = false;
                    foreach (AnimatorControllerParameter p in animator.parameters) if (p.nameHash == walkRateId) hasWalkRate = true;
                }
            }
            if (!faceReady) BuildFace();
            return animator != null;
        }

        /// <summary>Shows one moment of the mechanic: action (+ its serial: a new instance restarts the clip), seconds since
        /// it started, his ground speed. snap: jump without a blend (spawn, late join).</summary>
        public void Show(MechanicAction action, int serial, float age, float speed, bool snap = false)
        {
            if (!Resolve() || !animator.isActiveAndEnabled || animator.runtimeAnimatorController == null) return;
            age = Mathf.Max(0f, age);
            string state;
            float t;
            switch (action)
            {
                case MechanicAction.Idle:
                    state = MechanicClips.Idle; t = -1f; break;
                case MechanicAction.Walk:
                    state = speed > 0.05f ? MechanicClips.Walk : MechanicClips.Idle; t = -1f; break;
                case MechanicAction.Attend:
                    if (age < MechanicClips.AttendEnterSeconds) { state = MechanicClips.AttendEnter; t = age; }
                    else { state = MechanicClips.AttendLoop; t = (age - MechanicClips.AttendEnterSeconds) % MechanicClips.AttendLoopSeconds; }
                    break;
                default:
                    state = MechanicClips.State(action); t = Mathf.Min(age, Mathf.Max(0f, MechanicClips.Seconds(action) - 0.02f)); break;
            }
            bool restart = serial != shownSerial && action != MechanicAction.Idle && action != MechanicAction.Walk && action != MechanicAction.Attend;
            if (state != shownState || restart)
            {
                bool continuing = shownState == MechanicClips.AttendEnter && state == MechanicClips.AttendLoop;
                float offset = t > 0.12f ? t : 0f; // joined mid-clip (late join / a late message): start there
                if (snap || shownState.Length == 0) animator.Play(state, 0, t > 0f ? t / Mathf.Max(0.01f, ClipLength(action, state)) : 0f);
                else animator.CrossFadeInFixedTime(state, continuing ? 0.12f : Fade, 0, continuing ? t : offset);
                shownState = state;
            }
            if (hasWalkRate)
                animator.SetFloat(walkRateId, speed > 0.05f ? Mathf.Clamp(speed / MechanicClips.WalkClipSpeed, 0.5f, 1.6f) : 1f);
            shownSerial = serial;
            shownAction = action;
            shownAge = age;
        }

        private static float ClipLength(MechanicAction action, string state)
        {
            if (state == MechanicClips.AttendEnter) return MechanicClips.AttendEnterSeconds;
            if (state == MechanicClips.AttendLoop) return MechanicClips.AttendLoopSeconds;
            float s = MechanicClips.Seconds(action);
            return s > 0f ? s : 1f;
        }

        /// <summary>Animation events of the mechanic's clips (Raise, Pew, Poof, Knock...): presentation only, never a grant.</summary>
        public void OnMechanicCue(string cue) => LastCue = cue ?? "";

        // ------------------------------------------------------------------ face

        private void BuildFace()
        {
            faceReady = true;
            faces.Clear();
            foreach (SkinnedMeshRenderer r in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (r.sharedMesh == null || !(r.name == "Face" || r.name.StartsWith("Face_LOD", StringComparison.Ordinal))) continue;
                var index = new int[Shapes.Length];
                bool any = false;
                for (int i = 0; i < Shapes.Length; i++) { index[i] = r.sharedMesh.GetBlendShapeIndex(Shapes[i]); any |= index[i] >= 0; }
                if (any) faces.Add((r, index));
            }
            tracks.Clear();
            if (FaceCues == null) return;
            CueFile file;
            try { file = JsonUtility.FromJson<CueFile>(FaceCues.text); }
            catch (Exception e) { Debug.LogWarning("[MECHANIC] face cues unreadable: " + e.Message, this); return; }
            if (file?.clips == null) return;
            foreach (CueClip c in file.clips)
            {
                if (c == null || string.IsNullOrEmpty(c.state) || c.face_cues == null) continue;
                var perShape = new List<(float, float)>[Shapes.Length];
                foreach (CueKey k in c.face_cues)
                {
                    int s = Array.IndexOf(Shapes, k?.shape);
                    if (s < 0) continue;
                    (perShape[s] ??= new List<(float, float)>()).Add((k.seconds, Mathf.Clamp01(k.value) * 100f));
                }
                foreach (var list in perShape) list?.Sort((a, b) => a.Item1.CompareTo(b.Item1));
                tracks[c.state] = perShape;
            }
        }

        private static float Sample(List<(float t, float v)> keys, float t)
        {
            if (keys == null || keys.Count == 0) return 0f;
            if (t <= keys[0].t) return keys[0].v;
            for (int i = 1; i < keys.Count; i++)
                if (t <= keys[i].t)
                {
                    float span = keys[i].t - keys[i - 1].t;
                    return span <= 1e-4f ? keys[i].v : Mathf.Lerp(keys[i - 1].v, keys[i].v, (t - keys[i - 1].t) / span);
                }
            return keys[keys.Count - 1].v;
        }

        private void LateUpdate()
        {
            if (faces.Count == 0) return;
            string state = shownState;
            float t = shownAge;
            if (state == MechanicClips.AttendLoop) t = (shownAge - MechanicClips.AttendEnterSeconds) % MechanicClips.AttendLoopSeconds;
            tracks.TryGetValue(state ?? "", out List<(float, float)>[] track);
            bool cueBlink = track != null && (track[BlinkShape] != null || track[1] != null || track[2] != null);
            if (Time.time >= nextBlink) { blinkEnd = Time.time + 0.12f; nextBlink = Time.time + UnityEngine.Random.Range(2.2f, 5.5f); }
            float k = 650f * Time.deltaTime;
            for (int i = 0; i < Shapes.Length; i++)
            {
                float target = track != null ? Sample(track[i], t) : 0f;
                if (i == BlinkShape && !cueBlink && Time.time < blinkEnd) target = 100f;
                weights[i] = Mathf.MoveTowards(weights[i], target, i == BlinkShape ? k * 2.5f : k);
            }
            foreach ((SkinnedMeshRenderer r, int[] index) in faces)
            {
                if (r == null) continue;
                for (int i = 0; i < index.Length; i++) if (index[i] >= 0) r.SetBlendShapeWeight(index[i], weights[i]);
            }
        }
    }
}
