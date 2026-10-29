using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// PLAYER HANDS v01 settings, loaded from Resources/<see cref="ResourceName"/> (Player/Hands/Resources) so no scene or
    /// player prefab needs a new reference. Presentation only: none of these values change reach, capsule, carry physics
    /// or authority.
    /// </summary>
    [CreateAssetMenu(menuName = "VOLUNTEERS ONLY/Hands/Player Arms Tuning v01")]
    public sealed class PlayerArmsTuningV01 : ScriptableObject
    {
        public const string ResourceName = "PlayerArmsTuningV01";

        [Header("Body")]
        [Tooltip("The customisable player sausage (Characters/PlayerSausage_W86/Prefabs/PLAYER_SAUSAGE_W86_v01.prefab).")]
        public GameObject BodyPrefab;
        [Tooltip("Uniform scale of the third-person body on the motor (the model is 1.75 m; the W86 capsule 1.80 m).")]
        public float BodyScale = 1f;
        [Tooltip("Animator states of the shared Sausage Buddy controller (idle, walk, run) and their clip speeds, m/s.")]
        public string IdleState = "Idle", WalkState = "Walk", RunState = "Run";
        public float WalkClipSpeed = 1.5f, RunClipSpeed = 3.2f, RunAbove = 5.2f;
        [Tooltip("Third person: share of the view pitch the head nods with.")]
        [Range(0f, 1f)] public float HeadPitchShare = 0.45f;

        [Header("First person")]
        [Tooltip("Uniform scale of the first-person arms rig (a little bigger than the body reads better at FPS scale).")]
        public float FpScale = 1.15f;
        [Tooltip("Where the middle of the shoulders sits in camera space (x right, y up, z forward), m. Fedya 30.10: the " +
                 "viewmodel 25% farther and 25% lower than v01 (was 0, -0.3, 0; hands at ~0.45 m forward, ~0.2 m down).")]
        public Vector3 FpShoulders = new Vector3(0f, -0.35f, 0.11f);
        [Tooltip("Fedya 30.10: no idle hands. An arm with nothing to do parks its wrist here (camera space, right arm; the " +
                 "left is mirrored): hanging down at the side, outside the view, so it rises into the frame when it is needed.")]
        public Vector3 FpPark = new Vector3(0.27f, -0.86f, 0.12f);
        [Tooltip("Seconds the arms stay drawn after the last use while they drop out of the view (then they are not drawn).")]
        public float FpHideAfter = 0.45f;
        [Tooltip("Elbow pole of the right arm in camera space, relative to the shoulder (mirrored for the left).")]
        public Vector3 FpPole = new Vector3(0.55f, -0.9f, -0.25f);
        [Tooltip("Mouse sway: degrees of lag per degree/second of look, its limit and the roll share.")]
        public float SwayGain = 0.012f, SwayMax = 4.5f, SwayRoll = 0.006f, SwayHz = 7f, SwayDamping = 0.55f;
        [Tooltip("Walk bob: amplitude (x side, y dip) at walking speed, cycles per metre, reference speed m/s.")]
        public Vector2 BobAmplitude = new Vector2(0.011f, 0.016f);
        public float BobCyclesPerMeter = 0.36f, BobReferenceSpeed = 4.7f;
        [Tooltip("Idle breathing: vertical amplitude (m) and rate (Hz).")]
        public float BreathAmplitude = 0.004f, BreathHz = 0.32f;
        [Tooltip("A first-person punch reaches less far into a wall nearer than this (m, from the camera).")]
        public float WallProbe = 0.55f;

        [Header("Punch (Q, the existing fist hit: presentation only)")]
        [Tooltip("First person, camera space (right arm; mirrored for the left): the fist cocked low at the side, then the " +
                 "strike end on the crosshair line, slightly right and low so the target stays readable.")]
        public Vector3 FpPunchCock = new Vector3(0.27f, -0.29f, 0.42f);
        public Vector3 FpPunchStrike = new Vector3(0.09f, -0.14f, 0.6f);
        [Tooltip("Third person: the farthest a punch reaches toward its target, as a share of the stretch cap (a comic rubber " +
                 "jab, never longer than the carry stretch).")]
        [Range(0.2f, 1f)] public float TpPunchReach = 0.8f;
        [Tooltip("Cartoon stars at a landed hit: how many, how big (m), how long (s).")]
        public int StarCount = 8;
        public float StarSize = 0.12f, StarLife = 0.6f;

        [Header("Look")]
        [Tooltip("Fedya 30.10: the player's sausage is fully matte (skin and clothes, first and third person): smoothness 0, " +
                 "no specular highlights, no environment reflections. The eyes keep their shine.")]
        public bool Matte = true;

        [Header("Third person")]
        [Tooltip("Elbow pole of the right arm in body space relative to the shoulder (mirrored for the left).")]
        public Vector3 TpPole = new Vector3(0.5f, -0.9f, -0.2f);

        [Header("Stretch")]
        [Tooltip("Longest arm, as a multiple of its rest length (the hand stops short beyond it). Fedya 30.10: v01's 6 / 1.7.")]
        public float MaxStretch = 3.53f;
        [Tooltip("Extra arm length (share) at heft 1 once stretched: heavy = sagging elbow. Fedya 30.10: the visible droop / " +
                 "1.7 (v01 0.35; 0.206 alone left ~1.3x, measured on the solved poses, so 0.17 with Comfort 0.95).")]
        public float SagPerHeft = 0.17f;
        [Tooltip("Share of the arm's reach it keeps as a slight bend before it starts to stretch (v01 0.92 = 8.7% slack in " +
                 "every stretched arm; 0.95 = 5.3%, part of the droop / 1.7).")]
        [Range(0.85f, 0.99f)] public float Comfort = 0.95f;
        [Tooltip("On in the asset (Fedya 30.10: «руки дотягивают»): a holding arm may grow past the cap just enough to touch " +
                 "its grip, straight, without extra sag (presentation only). Off: beyond the cap the hands stop short of a far " +
                 "grip (NPC point holds farther than ~1.5 m from the shoulder).")]
        public bool KeepGripBeyondCap;
        [Tooltip("Thinnest cross-section of a fully stretched arm.")]
        [Range(0.1f, 1f)] public float MinThickness = 0.6f;
        public ArmSpringsV01 Springs = ArmSpringsV01.Default;

        [Header("Network")]
        [Tooltip("Arm state packets per second at most while the hands move (unreliable; a change of hands/pose is reliable).")]
        public float SendRate = 20f;
        [Tooltip("A reliable keyframe at least this often while holding, s (late joiners also get the last one).")]
        public float KeyframeInterval = 1f;

        private static PlayerArmsTuningV01 loaded;

        /// <summary>The Resources asset, or a default instance without a body prefab (then the hands stay off).</summary>
        public static PlayerArmsTuningV01 Load()
        {
            if (loaded != null) return loaded;
            loaded = Resources.Load<PlayerArmsTuningV01>(ResourceName);
            if (loaded == null)
            {
                loaded = CreateInstance<PlayerArmsTuningV01>();
                loaded.hideFlags = HideFlags.DontSave;
            }
            return loaded;
        }
    }
}
