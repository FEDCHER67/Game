using System;
using System.Collections.Generic;
using System.Globalization;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using Handle = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Handle;
using Part = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Part;

namespace OnlyVolunteers.Characters.Npc
{
    // Stage 9, first step (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §2-§4.2): a stunned NPC lies down as an 11-body
    // ragdoll instead of the stage-1 capsule. GreyboxNpc adds this component to every NPC root (no map-builder edits); the
    // bodies exist only while the NPC is down as a ragdoll: Activate builds 11 Rigidbodies, 11 capsules, 2 foot boxes,
    // 10 ConfigurableJoints and 11 NpcRagdollParts on the bones from the rig's NpcRagdollProfile (NpcRig, on the Buddy
    // prefabs); Deactivate removes them. Nothing runs for a walking NPC except, near the player and only in Ragdoll mode,
    // the bone motion tracking below.
    // - Built at the bones' current animated pose (no pop), the Animator off while ragdolled. Each joint's zero is the
    //   profile's reference pose (Idle; the shoulders: arms out to the sides), not the pose at the knockdown: the bone is
    //   turned there for a moment while its joint is made. Joint angles follow the profile; PhysX measures the hinge's X
    //   angle the other way round from Unity's rotations, so hinge axes are flipped here (checked by the EditMode test).
    // - Momentum: every body starts with the given velocity (the CharacterController's, or a vehicle's push) plus the
    //   animation's own motion of its bone relative to the root (tracked in LateUpdate within TrackRadius of the player,
    //   clamped to BoneMotionMax); a vehicle knock spins only the pelvis. GreyboxNpc then pushes the hit part.
    // - Any part can be grabbed (PhysicsGrabber finds NpcRagdollPart): up to MaxHolders holds per NPC, two hands may share
    //   a part. A hold sits on the part's capsule axis (limbs, head) or on the spine line (pelvis, chest), so a pull never
    //   twists a limb about itself. Handles (§3.4 A5): good = the stage-1 hand (240/260 N), thighs medium, pelvis and the
    //   belly bad (one hand cannot lift the hips). Holds damp with HoldMass (A1). F9 debug pins are holders too.
    // - Assists while held (§3.4, profile switches; second step of stage 9): A2 a hand's force on a limb or the head is
    //   spread up the chain to the trunk (SpreadShare at the joints); A3 every body gets Relief (20/35/45 % by holders on
    //   good or medium handles: a hand on the pelvis or the belly brings none, so A5 still holds) of its weight upward,
    //   gone the moment the last hand lets go; A4 joint drives: any holder keeps the waist and the
    //   neck roughly in line, two holders split above and below the pelvis drive the waist and the hips softly (the body
    //   sags in a U between them, ~0.2 m at the pelvis: the smoke test's r5c).
    //   A6 (leg lever) is not built: only if playtests show the legs folding on the van's edge.
    //   One hand alone on an arm or a leg (Fedya's playtest 2026-10-11: "by the leg you lift him into the air"): no relief
    //   and at most SoloLimbLift up (SoloLimbHeld), so the limb rises and the body drags on its back (smoke test r22).
    // - The van (GreyboxVanCargo, through INpcBody): loaded by its pelvis and collar like the capsule, at rest = every
    //   body; damped toward the van per body; teleports and ejection move the root with the bodies (MoveRigid,
    //   PlaceLying), so the root never stays far behind.
    // - Waking: Deactivate records the pose, removes the bodies and turns the Animator back on; the next frames blend every
    //   bone from the recorded pose to the animation (WakeBlend, head WakeBlendHead). The caller moves the root in between
    //   (NpcGetUp: the get-up and cargo sit-up clips, step 3); the recorded Hips pose is re-read in the moved armature, so
    //   nothing jumps on screen.
    // - Pushes on one part (step 3): a blow gives the struck part at most HitPartSpeed and a van door's push or shove at
    //   most DoorPartAccel / DoorPartShove; the rest moves the whole body (Spread), so a light limb is never whipped.
    // - Mode (F10, GreyboxInteractor) picks capsule or ragdoll for the next knockdown; at most Cap ragdolls are simulated,
    //   a knockdown beyond that gets the capsule (§2.7).
    // - Step 4: while Groggy, NpcStruggle owns the joint drives (DrivesTaken: SetTone then only records the carry tone;
    //   the struggle composes A4 into its own targets, Drive) and the rest test of the cargo bay looks at the trunk alone
    //   (the limbs move on their own). A kick's ankle impulse gives the shin at most KickPartSpeed (the motors kick).
    //   Stumble: the police officer's trip, built from the running pose and pitched forward about the feet, whatever F10
    //   says. Downed colliders meet police cars (CollideWithVehicles: the cars exclude the NPC layers for the standing
    //   crowd's sake; GPT review finding 3).
    // Not yet (later steps of stage 9): the sleep help, network sync.
    [DisallowMultipleComponent]
    public sealed class NpcRagdoll : MonoBehaviour, INpcBody
    {
        public const int DefaultCap = 12;
        public const int MaxHolders = 3;
        private const float ClaimInset = 0.03f;
        private const float PinToggleRadius = 0.25f;
        private const float TearRadius = 0.45f;
        private const float GroundProbe = 0.05f;
        private const string BoxName = "RagdollFootBox";

        /// <summary>F10 (GreyboxInteractor): the body the next free NPC gets when it goes down. Every Play session starts
        /// with the ragdoll (Fedya 2026-10-11: a knocked-out NPC must move part by part); F10 falls back to the stage-1
        /// capsule. Known: one player alone does not yet get a ragdoll in through the rear doors reliably (RagdollSmokeTest r6b).</summary>
        public static NpcBodyMode Mode = NpcBodyMode.Ragdoll;
        /// <summary>At most this many ragdolls at once; a knockdown beyond it gets the capsule (§2.7).</summary>
        public static int Cap = DefaultCap;
        /// <summary>Test hook (RagdollSmokeTest): track bone motion at any distance from the player.</summary>
        public static bool TrackAll;
        private static readonly HashSet<NpcRagdoll> Live = new();
        public static int ActiveCount => Live.Count;
        /// <summary>Milliseconds the last Activate took (component build), for the smoke test.</summary>
        public static double LastBuildMilliseconds { get; private set; }

        private static readonly Dictionary<(GrabPhysicsProfile, Handle, float, float), GrabPhysicsProfile> HandleProfiles = new();
        private static readonly Collider[] Overlap = new Collider[16];
        private static PhysicsMaterial _material;
        private static GreyboxPawn _pawn;
        private static float _nextPawnSearch;
        private static int _listenerFrame = -1;
        private static Vector3 _listener;
        private static bool _hasListener;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Mode = NpcBodyMode.Ragdoll;
            Cap = DefaultCap;
            TrackAll = false;
            Live.Clear();
            HandleProfiles.Clear();
            _pawn = null;
            _nextPawnSearch = 0f;
            _listenerFrame = -1;
        }

        /// <summary>One hold: who, on which part, where (the part body's frame: its rotation, metres), how strong.</summary>
        public struct Claim
        {
            public object Holder;
            public int Part;
            public Vector3 Local;
            public Handle Handle;
        }

        [NonSerialized] public readonly Claim[] Claims = new Claim[MaxHolders];

        public event Action<float, Collider> Impact;

        // Serialized so a script reload in Play mode keeps them (the components themselves survive it).
        [SerializeField, HideInInspector] private NpcRig _rig;
        [SerializeField, HideInInspector] private Transform[] _bones;
        [SerializeField, HideInInspector] private Transform[] _boxBones;
        [SerializeField, HideInInspector] private Rigidbody[] _bodies;
        [SerializeField, HideInInspector] private ConfigurableJoint[] _joints;
        [SerializeField, HideInInspector] private NpcRagdollPart[] _parts;
        [SerializeField, HideInInspector] private CapsuleCollider[] _capsules;
        [SerializeField, HideInInspector] private BoxCollider[] _boxes;
        [SerializeField, HideInInspector] private List<Collider> _colliders = new();
        [SerializeField, HideInInspector] private bool _active;
        [SerializeField, HideInInspector] private bool _grabbable;

        private bool _resolved;
        private string _problem;
        private Animator _animator;
        private CharacterController _controller;
        private GreyboxNpcBody _capsuleBody;
        private int _root = -1, _chest = -1, _head = -1;
        private Vector3 _pelvisForward = Vector3.forward; // the character's front in the pelvis bone's frame (Idle)
        private Vector3 _chestForward = Vector3.forward;  // and in the chest bone's frame

        // Bone motion tracking (walking NPCs near the player, Ragdoll mode only).
        private Vector3[] _trackPos;
        private Vector3[] _motion;
        private Vector3 _trackRoot;
        private int _trackedFrame = -10;
        private bool _hasMotion;

        // Build scratch.
        private Vector3[] _posePos;
        private Quaternion[] _poseRot;

        // Wake blend.
        private Transform[] _allBones;
        private bool[] _headBone;
        private Quaternion[] _snapRot;
        private Transform _hips;
        private Vector3 _hipsWorldPos, _hipsSnapPos;
        private Quaternion _hipsWorldRot, _hipsSnapRot;
        private bool _blending, _hipsPending;
        private float _blendTime, _blendScale = 1f;

        // A4: the carry tone the joints are driven with now (0 limp, 1 held, 2 carried by a split pair).
        private int _tone;
        // Step 4: NpcStruggle drives the joints (Groggy); SetTone only records the tone meanwhile.
        private bool _drivesTaken;

        private readonly List<Collider> _ignored = new();
        private float _restoreIgnoredAt;
        // IgnoreOverlapping: (own collider, vehicle collider) pairs ignored until they are apart.
        private readonly List<(Collider own, Collider other)> _grace = new();
        private float _impactSpeed;
        private Collider _impactOther;
        private Vector3 _impactPoint;
        private readonly List<DebugPin> _pins = new();

        private sealed class DebugPin
        {
            public int Slot;
            public Vector3 Anchor;
        }

        // ---------- State ----------

        public bool Active => _active;
        public NpcRagdollProfile Profile => _rig != null ? _rig.Ragdoll : null;
        /// <summary>Profile found and every bone of it present on this NPC.</summary>
        public bool Ready => Resolve();
        /// <summary>Why the ragdoll cannot be built here (null when Ready).</summary>
        public string Problem => Resolve() ? null : _problem;
        /// <summary>Whether the next knockdown of this NPC can be a ragdoll: Ragdoll mode, under the cap, rig ready.</summary>
        public bool CanActivate => Mode == NpcBodyMode.Ragdoll && !_active && Live.Count < Cap && Ready;
        /// <summary>Step 4: whether it can trip as the ragdoll now (Stumble): under the cap, rig ready; F10 does not matter.</summary>
        public bool CanStumble => !_active && Live.Count < Cap && Ready;
        public int PartCount => Profile != null ? Profile.Parts.Length : 0;
        public IReadOnlyList<Collider> Colliders => _colliders;

        public bool Grabbable
        {
            get => _grabbable;
            set => _grabbable = value;
        }

        public int HolderCount
        {
            get
            {
                int n = 0;
                for (int i = 0; i < Claims.Length; i++)
                    if (Claims[i].Holder != null) n++;
                return n;
            }
        }

        /// <summary>Held, and only by the shins or feet.</summary>
        public bool OnlyLegsHeld
        {
            get
            {
                NpcRagdollProfile p = Profile;
                bool held = false;
                for (int i = 0; i < Claims.Length; i++)
                {
                    if (Claims[i].Holder == null) continue;
                    if (p == null || p.Parts[Claims[i].Part].Kind != Kind.Calf) return false;
                    held = true;
                }
                return held;
            }
        }

        /// <summary>Fedya's playtest 2026-10-11: one hold alone, on an arm or a leg (NpcRagdollProfile.SoloLimbRule): no A3
        /// relief, and that hand lifts at most SoloLimbLift, so the limb comes up and the trunk stays on the ground.</summary>
        public bool SoloLimbHeld
        {
            get
            {
                NpcRagdollProfile p = Profile;
                if (p == null || !p.SoloLimbRule) return false;
                int part = -1, holds = 0;
                for (int i = 0; i < Claims.Length; i++)
                {
                    if (Claims[i].Holder == null) continue;
                    holds++;
                    part = Claims[i].Part;
                }
                return holds == 1 && part >= 0 && part < p.Parts.Length && IsLimb(p.Parts[part].Kind);
            }
        }

        /// <summary>The force the last hold applied (after the solo-limb lift cap), for the smoke test.</summary>
        public Vector3 LastHoldForce { get; private set; }

        public Rigidbody MainBody => _active && _root >= 0 ? _bodies[_root] : null;
        public Rigidbody BodyOf(int part) => _active && _bodies != null && part >= 0 && part < _bodies.Length ? _bodies[part] : null;
        public ConfigurableJoint JointOf(int part) => _active && _joints != null && part >= 0 && part < _joints.Length ? _joints[part] : null;
        public Transform BoneOf(int part) => Resolve() && part >= 0 && part < _bones.Length ? _bones[part] : null;
        public bool HasRequiredBodies
        {
            get
            {
                if (!_active || !Resolve() || _hips == null || _bones == null || _bodies == null ||
                    _bones.Length != _bodies.Length || _root < 0 || _root >= _bodies.Length) return false;
                for (int i = 0; i < _bodies.Length; i++)
                    if (_bones[i] == null || _bodies[i] == null) return false;
                return true;
            }
        }
        /// <summary>The Hips bone (the pelvis part's): the get-up clips' root is placed by it (NpcGetUp).</summary>
        public Transform Hips => Resolve() ? _hips : null;
        /// <summary>The rig's Animator (NpcRig), off while the ragdoll is built.</summary>
        public Animator Animator => Resolve() ? _animator : null;
        /// <summary>The pose blend after waking is still running (the clip is not fully in charge of the bones yet).</summary>
        public bool Blending => _blending;

        /// <summary>The character's front (world, physics pose of the pelvis): up lying on its back, down on its belly.</summary>
        public Vector3 Front
        {
            get
            {
                if (!Resolve()) return transform.forward;
                Pose(_root, out _, out Quaternion pelvis);
                return pelvis * _pelvisForward;
            }
        }

        public Vector3 CenterOfMass
        {
            get
            {
                if (!_active) return transform.TransformPoint(0f, 0.75f, 0f);
                Vector3 sum = Vector3.zero;
                float mass = 0f;
                foreach (Rigidbody rb in _bodies)
                {
                    if (rb == null) continue;
                    sum += rb.worldCenterOfMass * rb.mass;
                    mass += rb.mass;
                }
                return mass > 0f ? sum / mass : transform.position;
            }
        }

        /// <summary>The pelvis or the chest touches something (ground, van floor, another body): a crawl hop has
        /// something to push off. Checked on demand (a crawl step), not every tick.</summary>
        public bool Grounded => _active && (Touches(_root) || Touches(_chest));

        // ---------- Setup ----------

        private void Awake()
        {
            TryGetComponent(out _controller);
            TryGetComponent(out _capsuleBody);
        }

        private void OnEnable()
        {
            if (_active) Live.Add(this); // after a script reload in Play mode the static set is empty again
        }

        private void OnDisable()
        {
            Live.Remove(this);
            RevokeAll();
        }

        private void OnDestroy() => Live.Remove(this);

        // Finds the rig, its profile and the bones (once). False with a Problem when something is missing; the NPC then
        // always goes down as the capsule.
        private bool Resolve()
        {
            if (_resolved) return _problem == null;
            _resolved = true;
            _problem = null;
            if (_rig == null) _rig = GetComponentInChildren<NpcRig>(true);
            NpcRagdollProfile p = Profile;
            if (p == null || p.Parts == null || p.Parts.Length == 0)
            {
                _problem = "no NpcRig with a ragdoll profile under the NPC";
                return false;
            }
            var byName = new Dictionary<string, Transform>();
            foreach (Transform t in _rig.GetComponentsInChildren<Transform>(true))
                if (!byName.ContainsKey(t.name)) byName.Add(t.name, t);
            int n = p.Parts.Length;
            _bones = new Transform[n];
            _boxBones = new Transform[n];
            for (int i = 0; i < n; i++)
            {
                Part part = p.Parts[i];
                if (part == null || !byName.TryGetValue(part.Bone, out _bones[i]))
                {
                    _problem = $"bone '{part?.Bone}' not found";
                    return false;
                }
                if (!string.IsNullOrEmpty(part.BoxBone) && !byName.TryGetValue(part.BoxBone, out _boxBones[i]))
                {
                    _problem = $"bone '{part.BoxBone}' not found";
                    return false;
                }
                if (part.Parent >= i || (part.Parent < 0 && _root >= 0))
                {
                    _problem = $"part {part.Name}: parents must come first, one root";
                    return false;
                }
                if (part.Parent < 0) _root = i;
            }
            _chest = p.IndexOf(Kind.Chest);
            _head = p.IndexOf(Kind.Head);
            if (_root < 0 || _chest < 0 || _head < 0)
            {
                _problem = "the profile needs a pelvis, a chest and a head";
                return false;
            }
            _pelvisForward = Quaternion.Inverse(p.Parts[_root].PoseRotation) * Vector3.forward;
            _chestForward = Quaternion.Inverse(p.Parts[_chest].PoseRotation) * Vector3.forward;
            _animator = _rig.Animator != null ? _rig.Animator : _rig.GetComponent<Animator>();
            _hips = _bones[_root];
            // Every bone under the armature (the Hips' parent), for the wake blend; the foot boxes are not bones.
            var all = new List<Transform>();
            foreach (Transform t in _hips.parent.GetComponentsInChildren<Transform>(true))
                if (t != _hips.parent && t.name != BoxName) all.Add(t);
            _allBones = all.ToArray();
            _snapRot = new Quaternion[_allBones.Length];
            _headBone = new bool[_allBones.Length];
            Transform head = _bones[_head], neck = head.parent;
            for (int k = 0; k < _allBones.Length; k++)
                _headBone[k] = _allBones[k] == neck || _allBones[k].IsChildOf(head);
            _posePos = new Vector3[n];
            _poseRot = new Quaternion[n];
            _trackPos = new Vector3[n];
            _motion = new Vector3[n];
            if (_bodies == null || _bodies.Length != n)
            {
                _bodies = new Rigidbody[n];
                _joints = new ConfigurableJoint[n];
                _parts = new NpcRagdollPart[n];
                _capsules = new CapsuleCollider[n];
                _boxes = new BoxCollider[n];
            }
            return true;
        }

        private static PhysicsMaterial Material(NpcRagdollProfile p) =>
            _material != null ? _material : _material = new PhysicsMaterial("NpcRagdoll")
            {
                dynamicFriction = p.DynamicFriction,
                staticFriction = Mathf.Max(p.DynamicFriction, p.StaticFriction),
                bounciness = 0f,
                frictionCombine = PhysicsMaterialCombine.Average,
                bounceCombine = PhysicsMaterialCombine.Minimum,
            };

        /// <summary>Step 4 (GPT review finding 3): a downed body's collider meets vehicles even where the vehicle's body
        /// excludes the NPC layers (police cars: PoliceCarMotor excludes NpcMask so the standing crowd, the same NpcBody
        /// layer, never stops them): the collider includes Vehicle with a higher override priority than the car's
        /// exclusion. The van collides with lying bodies anyway (the layer matrix). Off: the stage-1 behaviour.</summary>
        public static void CollideWithVehicles(Collider c, bool on)
        {
            if (c == null) return;
            c.includeLayers = on ? (LayerMask)OvLayers.VehicleMask : (LayerMask)0;
            c.layerOverridePriority = on ? 1 : 0;
        }

        private static float Scale(Transform t) => Mathf.Max(1e-6f, Mathf.Abs(t.lossyScale.x));

        private static bool IsLimb(Kind kind) => kind >= Kind.UpperArm;

        // ---------- On / off ----------

        /// <summary>Becomes the ragdoll at the bones' current pose: every body gets 'velocity' plus its bone's own animated
        /// motion, the pelvis spins with 'angularVelocity' (at most KnockSpin). Ignores Mode and Cap (see CanActivate).</summary>
        public void Activate(Vector3 velocity, Vector3 angularVelocity)
        {
            if (_active || !Resolve()) return;
            long start = System.Diagnostics.Stopwatch.GetTimestamp();
            NpcRagdollProfile p = Profile;
            int n = p.Parts.Length;
            bool motion = _hasMotion && _trackedFrame >= Time.frameCount - 1;
            for (int i = 0; i < n; i++)
            {
                _posePos[i] = _bones[i].position;
                _poseRot[i] = _bones[i].rotation;
            }
            if (_animator != null) _animator.enabled = false;
            _blending = false;
            _colliders.Clear();
            // Bodies first, so every collider below lands on its own bone's body, not on a parent's.
            for (int i = 0; i < n; i++)
            {
                GameObject bone = _bones[i].gameObject;
                bone.layer = OvLayers.NpcBody;
                if (!bone.TryGetComponent(out _bodies[i])) _bodies[i] = bone.AddComponent<Rigidbody>();
            }
            PhysicsMaterial material = Material(p);
            for (int i = 0; i < n; i++) AddColliders(i, p, material);
            for (int i = 0; i < n; i++) SetupBody(i, p);
            for (int i = 0; i < n; i++)
                if (p.Parts[i].Parent >= 0) _joints[i] = MakeJoint(i, p);
            // Back to the pose it was in (MakeJoint turned the bones), then the momentum.
            for (int i = 0; i < n; i++) _bones[i].SetPositionAndRotation(_posePos[i], _poseRot[i]);
            for (int i = 0; i < n; i++)
            {
                Rigidbody rb = _bodies[i];
                Vector3 v = velocity;
                if (motion) v += Vector3.ClampMagnitude(_motion[i], p.BoneMotionMax);
                rb.linearVelocity = v;
                rb.angularVelocity = i == _root ? Vector3.ClampMagnitude(angularVelocity, p.KnockSpin) : Vector3.zero;
                rb.WakeUp();
                _parts[i] = _bones[i].gameObject.AddComponent<NpcRagdollPart>();
                _parts[i].Bind(this, i);
            }
            _active = true;
            _tone = 0; // the joints are made limp
            _drivesTaken = false;
            Live.Add(this);
            _hasMotion = false;
            LastBuildMilliseconds = (System.Diagnostics.Stopwatch.GetTimestamp() - start) * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
        }

        private void AddColliders(int i, NpcRagdollProfile p, PhysicsMaterial material)
        {
            Part part = p.Parts[i];
            Transform bone = _bones[i];
            float s = Scale(bone);
            var capsule = bone.gameObject.AddComponent<CapsuleCollider>();
            capsule.direction = part.Direction;
            capsule.radius = part.Radius / s;
            capsule.height = part.Height / s;
            capsule.center = part.Center / s;
            capsule.sharedMaterial = material;
            CollideWithVehicles(capsule, true);
            _capsules[i] = capsule;
            _colliders.Add(capsule);
            _boxes[i] = null;
            Transform foot = _boxBones[i];
            if (foot == null) return;
            // On a child of the foot bone, at unit scale, turned to lie flat in the Idle pose.
            var go = new GameObject(BoxName) { layer = OvLayers.NpcBody };
            go.transform.SetParent(foot, false);
            float fs = Scale(foot);
            go.transform.SetLocalPositionAndRotation(part.BoxCenter / fs, part.BoxRotation);
            go.transform.localScale = Vector3.one / fs;
            var box = go.AddComponent<BoxCollider>();
            box.size = part.BoxSize;
            box.sharedMaterial = material;
            CollideWithVehicles(box, true);
            _boxes[i] = box;
            _colliders.Add(box);
        }

        private void SetupBody(int i, NpcRagdollProfile p)
        {
            Rigidbody rb = _bodies[i];
            rb.mass = p.Parts[i].Mass;
            rb.linearDamping = p.LinearDamping;
            rb.angularDamping = p.AngularDamping;
            rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            rb.maxDepenetrationVelocity = p.MaxDepenetration;
            rb.maxAngularVelocity = p.MaxAngularVelocity;
            rb.solverIterations = p.SolverIterations;
            rb.solverVelocityIterations = p.SolverVelocityIterations;
            rb.sleepThreshold = p.SleepThreshold;
            rb.ResetCenterOfMass();
            rb.ResetInertiaTensor();
            if (IsLimb(p.Parts[i].Kind) && !Mathf.Approximately(p.LimbInertiaScale, 1f))
                rb.inertiaTensor *= p.LimbInertiaScale;
        }

        // The joint to the parent, made while the bone is turned to the profile's reference pose relative to its parent
        // (the joint keeps the relative rotation it is made in as its zero), with the pivot where the bone is now.
        private ConfigurableJoint MakeJoint(int i, NpcRagdollProfile p)
        {
            Part part = p.Parts[i];
            Transform bone = _bones[i], parent = _bones[part.Parent];
            Quaternion keep = bone.rotation;
            bone.rotation = parent.rotation * part.Reference;
            var joint = bone.gameObject.AddComponent<ConfigurableJoint>();
            joint.autoConfigureConnectedAnchor = false;
            joint.connectedBody = _bodies[part.Parent];
            joint.anchor = Vector3.zero;
            joint.connectedAnchor = parent.InverseTransformPoint(bone.position);
            // PhysX measures the X angle against Unity's sense of rotation: a hinge's flexion axis goes in flipped.
            joint.axis = part.Joint == NpcRagdollProfile.JointKind.Hinge ? -part.Axis : part.Axis;
            joint.secondaryAxis = part.Secondary;
            joint.xMotion = ConfigurableJointMotion.Locked;
            joint.yMotion = ConfigurableJointMotion.Locked;
            joint.zMotion = ConfigurableJointMotion.Locked;
            joint.angularXMotion = ConfigurableJointMotion.Limited;
            joint.angularYMotion = ConfigurableJointMotion.Limited;
            joint.angularZMotion = ConfigurableJointMotion.Limited;
            joint.lowAngularXLimit = new SoftJointLimit { limit = part.LowX };
            joint.highAngularXLimit = new SoftJointLimit { limit = part.HighX };
            joint.angularYLimit = new SoftJointLimit { limit = part.LimitY };
            joint.angularZLimit = new SoftJointLimit { limit = part.LimitZ };
            joint.projectionMode = JointProjectionMode.PositionAndRotation;
            joint.projectionDistance = p.ProjectionDistance;
            joint.projectionAngle = p.ProjectionAngle;
            joint.enablePreprocessing = false;
            joint.enableCollision = false;
            joint.rotationDriveMode = RotationDriveMode.Slerp;
            joint.slerpDrive = new JointDrive { positionSpring = 0f, positionDamper = 0f, maximumForce = float.MaxValue };
            bone.rotation = keep;
            return joint;
        }

        /// <summary>Back to a plain NPC: holds revoked, the bodies removed at once (DestroyImmediate, so it can go down
        /// again in the same frame; never from a collision callback), the Animator on, the pose blending from the lying
        /// one to the animation over the next frames. GreyboxNpc moves the root right after (standing up, sitting up).</summary>
        public void Deactivate() => Deactivate(1f);

        /// <summary>Deactivate with the wake blend 'blendScale' times as long (a body rolling over during the blend).</summary>
        public void Deactivate(float blendScale)
        {
            if (!_active) return;
            _blendScale = Mathf.Max(0.1f, blendScale);
            RevokeAll();
            RestoreIgnored();
            EndGrace(true);
            _impactSpeed = 0f;
            _impactOther = null;
            bool snapshot = HasRequiredBodies && _allBones != null;
            if (snapshot)
            {
                for (int k = 0; k < _allBones.Length; k++)
                    if (_allBones[k] != null) _snapRot[k] = _allBones[k].localRotation;
                _hipsWorldPos = _hips.position;
                _hipsWorldRot = _hips.rotation;
            }
            for (int i = 0; i < _bodies.Length; i++)
            {
                if (_joints[i] != null) DestroyImmediate(_joints[i]);
                _joints[i] = null;
            }
            for (int i = 0; i < _bodies.Length; i++)
            {
                if (_parts[i] != null) DestroyImmediate(_parts[i]);
                if (_boxes[i] != null) DestroyImmediate(_boxes[i].gameObject);
                if (_capsules[i] != null) DestroyImmediate(_capsules[i]);
                if (_bodies[i] != null) DestroyImmediate(_bodies[i]);
                _parts[i] = null;
                _boxes[i] = null;
                _capsules[i] = null;
                _bodies[i] = null;
            }
            _colliders.Clear();
            _active = false;
            _tone = 0;
            _drivesTaken = false;
            _grabbable = false;
            Live.Remove(this);
            if (_animator != null) _animator.enabled = true;
            _blending = snapshot;
            _hipsPending = snapshot;
            _blendTime = 0f;
        }

        /// <summary>A body that is already a ragdoll knocked again (a vehicle): every body gets 'velocity', the pelvis
        /// 'angularVelocity' (at most KnockSpin). Null keeps what they have.</summary>
        public void SetVelocity(Vector3? velocity, Vector3? angularVelocity)
        {
            if (!_active) return;
            for (int i = 0; i < _bodies.Length; i++)
            {
                Rigidbody rb = _bodies[i];
                if (rb == null) continue;
                if (velocity.HasValue) rb.linearVelocity = velocity.Value;
                if (angularVelocity.HasValue && i == _root) rb.angularVelocity = Vector3.ClampMagnitude(angularVelocity.Value, Profile.KnockSpin);
                rb.WakeUp();
            }
        }

        /// <summary>Step 4, a trip (§4.6, the fat police officer; GreyboxNpc.Stumble): becomes the ragdoll from the running
        /// pose with 'velocity', the whole body pitching forward about its feet (the root) at StumblePitch, the shins keeping
        /// StumbleFeet of the velocity (the feet caught). Ignores Mode (see CanStumble).</summary>
        public void Stumble(Vector3 velocity)
        {
            if (_active || !Resolve()) return;
            NpcRagdollProfile p = Profile;
            Activate(velocity, Vector3.zero);
            if (!_active) return;
            Vector3 forward = Flat(transform.forward);
            forward = forward.sqrMagnitude > 1e-6f ? forward.normalized : Vector3.forward;
            // A turn about the character's right takes up toward forward: the higher a body, the faster it goes forward.
            Vector3 spin = Vector3.Cross(Vector3.up, forward) * p.StumblePitch;
            Vector3 feet = transform.position;
            for (int i = 0; i < _bodies.Length; i++)
            {
                Rigidbody rb = _bodies[i];
                if (rb == null) continue;
                Vector3 own = p.Parts[i].Kind == Kind.Calf ? velocity * p.StumbleFeet : velocity;
                rb.linearVelocity = own + Vector3.Cross(spin, rb.worldCenterOfMass - feet);
                rb.angularVelocity = spin;
            }
        }

        /// <summary>INpcBody (the cargo bay's ejection): on its back, the pelvis over 'ground', the head along 'flatForward'.</summary>
        public void PlaceLying(Vector3 ground, Vector3 flatForward) => PlaceLying(ground, flatForward, true);

        /// <summary>How far the body reaches from the pelvis centre, lying straight in the Idle pose: to the head top and
        /// to the soles (metres; zero when the rig is not ready).</summary>
        public void LyingExtent(out float headward, out float footward)
        {
            headward = footward = 0f;
            if (!Resolve()) return;
            NpcRagdollProfile p = Profile;
            Part pelvis = p.Parts[_root], head = p.Parts[_head];
            float pelvisY = (pelvis.PosePosition + pelvis.PoseRotation * pelvis.Center).y;
            Vector3 top = head.Center + head.Up.normalized * (head.Height * 0.5f);
            headward = Mathf.Max(0f, (head.PosePosition + head.PoseRotation * top).y - pelvisY);
            footward = Mathf.Max(0f, pelvisY); // the soles are at the root
        }

        /// <summary>Lays the ragdoll flat in its Idle pose, the pelvis over 'ground' (a point on the ground), the head toward
        /// 'headDirection' (flattened), face up or down, at rest. The NPC root moves to 'ground' with it (upright, facing
        /// the head's way), so it never stays behind. For the cargo bay's ejection and scripted setups (RagdollSmokeTest).</summary>
        public void PlaceLying(Vector3 ground, Vector3 headDirection, bool faceUp)
        {
            if (!_active) return;
            NpcRagdollProfile p = Profile;
            Vector3 head = Flat(headDirection);
            head = head.sqrMagnitude > 1e-6f ? head.normalized : Vector3.forward;
            // The root first (the bones are its children); every simulated bone is then set in world space.
            transform.SetPositionAndRotation(ground, Quaternion.LookRotation(head));
            // The character frame lying down: its up (toward the head) along 'head', its front up or down.
            Quaternion frame = Quaternion.LookRotation(faceUp ? Vector3.up : Vector3.down, head);
            float lowest = float.MaxValue;
            for (int i = 0; i < p.Parts.Length; i++)
            {
                Part part = p.Parts[i];
                Quaternion r = frame * part.PoseRotation;
                Vector3 c = frame * part.PosePosition + r * part.Center;
                Vector3 axis = r * NpcRagdollProfile.AxisVector(part.Direction);
                float half = Mathf.Max(0f, part.Height * 0.5f - part.Radius);
                lowest = Mathf.Min(lowest, Mathf.Min((c - axis * half).y, (c + axis * half).y) - part.Radius);
                if (part.BoxSize == Vector3.zero) continue;
                // The foot box lies along the character's frame in the Idle pose (NpcRagdollBuilder).
                Vector3 e = part.BoxSize * 0.5f;
                for (int corner = 0; corner < 8; corner++)
                {
                    var o = new Vector3((corner & 1) == 0 ? -e.x : e.x, (corner & 2) == 0 ? -e.y : e.y, (corner & 4) == 0 ? -e.z : e.z);
                    lowest = Mathf.Min(lowest, (frame * (part.BoxPoseCenter + o)).y);
                }
            }
            Part pelvis = p.Parts[_root];
            Vector3 pelvisCentre = frame * (pelvis.PosePosition + pelvis.PoseRotation * pelvis.Center);
            var origin = new Vector3(ground.x - pelvisCentre.x, ground.y - lowest + 0.02f, ground.z - pelvisCentre.z);
            for (int i = 0; i < p.Parts.Length; i++)
                _bones[i].SetPositionAndRotation(origin + frame * p.Parts[i].PosePosition, frame * p.Parts[i].PoseRotation);
            for (int i = 0; i < p.Parts.Length; i++)
            {
                Rigidbody rb = _bodies[i];
                rb.position = _bones[i].position;
                rb.rotation = _bones[i].rotation;
                rb.linearVelocity = Vector3.zero;
                rb.angularVelocity = Vector3.zero;
            }
            Physics.SyncTransforms();
        }

        /// <summary>INpcBody (a van teleport): every body and the root moved rigidly by the van's move (the physics poses,
        /// not the interpolated transforms), given 'velocity' and no spin. The root keeps only its yaw.</summary>
        public void MoveRigid(Vector3 fromPos, Quaternion fromRot, Vector3 toPos, Quaternion toRot, Vector3 velocity)
        {
            if (!_active) return;
            Quaternion turn = toRot * Quaternion.Inverse(fromRot);
            int n = _bodies.Length;
            for (int i = 0; i < n; i++)
            {
                Rigidbody rb = _bodies[i];
                _posePos[i] = toPos + turn * (rb.position - fromPos);
                _poseRot[i] = turn * rb.rotation;
            }
            Vector3 forward = Flat(turn * transform.forward);
            transform.SetPositionAndRotation(toPos + turn * (transform.position - fromPos),
                forward.sqrMagnitude > 1e-6f ? Quaternion.LookRotation(forward) : transform.rotation);
            for (int i = 0; i < n; i++)
            {
                Rigidbody rb = _bodies[i];
                _bones[i].SetPositionAndRotation(_posePos[i], _poseRot[i]);
                rb.position = _posePos[i];
                rb.rotation = _poseRot[i];
                rb.linearVelocity = velocity;
                rb.angularVelocity = Vector3.zero;
            }
            Physics.SyncTransforms();
        }

        /// <summary>INpcBody: the fastest body relative to the frame's velocity at its centre of mass (the van's "at rest").
        /// Step 4: while it struggles (DrivesTaken) only the pelvis and the chest count: its limbs paw and kick on their own,
        /// it lies still when its trunk does.</summary>
        public float MaxRelativeSpeed(Func<Vector3, Vector3> frameVelocity)
        {
            if (!_active) return 0f;
            float worst = 0f;
            for (int i = 0; i < _bodies.Length; i++)
            {
                Rigidbody rb = _bodies[i];
                if (rb == null || (_drivesTaken && i != _root && i != _chest)) continue;
                Vector3 frame = frameVelocity != null ? frameVelocity(rb.worldCenterOfMass) : Vector3.zero;
                worst = Mathf.Max(worst, (rb.linearVelocity - frame).sqrMagnitude);
            }
            return Mathf.Sqrt(worst);
        }

        /// <summary>INpcBody (LoadedDamping): each body pulled toward the frame's velocity at its centre of mass, unless
        /// it is within settledSpeed already (any force wakes a body: a parked van's bodies must be able to sleep).</summary>
        public void DampToward(Func<Vector3, Vector3> frameVelocity, float perSecond, float settledSpeed)
        {
            if (!_active || frameVelocity == null) return;
            float settled = settledSpeed * settledSpeed;
            foreach (Rigidbody rb in _bodies)
            {
                if (rb == null) continue;
                Vector3 relative = rb.linearVelocity - frameVelocity(rb.worldCenterOfMass);
                if (relative.sqrMagnitude > settled) rb.AddForce(-relative * (rb.mass * perSecond));
            }
        }

        // ---------- Every frame ----------

        private void FixedUpdate()
        {
            if (!_active) return;
            if (_ignored.Count > 0 && Time.time >= _restoreIgnoredAt) RestoreIgnored();
            if (_grace.Count > 0) EndGrace(false);
            if (_impactSpeed > 0f) RaiseImpact();
            if (_pins.Count > 0) HoldPins();
            NpcRagdollProfile p = Profile;
            int holders = HolderCount;
            SetTone(p.CarryTone ? ToneFor(holders) : 0);
            // A3: lighter while held (before the solver step, like the hands' forces); a bad handle brings no relief
            // unless the profile says so (one hand on the pelvis must not lift the hips), nor does one hand alone on an
            // arm or a leg (SoloLimbHeld: one hand on an ankle lifted the whole body).
            float relief = SoloLimbHeld ? 0f : p.ReliefFor(p.BadHandleRelief ? holders : HoldersOn(Handle.Good) + HoldersOn(Handle.Medium));
            if (relief > 0f)
            {
                Vector3 up = -Physics.gravity * relief;
                foreach (Rigidbody rb in _bodies)
                    if (rb != null) rb.AddForce(up, ForceMode.Acceleration);
            }
        }

        // ---------- A4: carry tone ----------

        /// <summary>The carry tone the holds call for: 0 unheld (limp), 1 held, 2 held by two or more with one hold above the
        /// pelvis (head, chest, arms) and one below it (thighs, calves).</summary>
        public int ToneFor(int holders)
        {
            if (holders <= 0) return 0;
            if (holders < 2) return 1;
            bool above = false, below = false;
            NpcRagdollProfile p = Profile;
            for (int i = 0; i < Claims.Length; i++)
            {
                if (Claims[i].Holder == null) continue;
                Kind kind = p.Parts[Claims[i].Part].Kind;
                if (kind == Kind.Thigh || kind == Kind.Calf) below = true;
                else if (kind != Kind.Pelvis) above = true;
            }
            return above && below ? 2 : 1;
        }

        /// <summary>The joint drives of a carry tone (A4). Written only when the tone changes (a write wakes the bodies);
        /// public for the EditMode check of the drive directions. While the struggle drives the joints (DrivesTaken) the
        /// tone is only recorded (the struggle composes it into its own targets).</summary>
        public void SetTone(int tone)
        {
            if (!_active || tone == _tone) return;
            _tone = tone;
            if (!_drivesTaken) WriteTone(tone);
        }

        /// <summary>Step 4: NpcStruggle drives every joint while true (Groggy); set back to false, every joint goes limp
        /// again and the carry tone's drives are written.</summary>
        public bool DrivesTaken
        {
            get => _drivesTaken;
            set
            {
                if (_drivesTaken == value) return;
                _drivesTaken = value;
                if (value || !_active) return;
                var limp = new JointDrive { positionSpring = 0f, positionDamper = 0f, maximumForce = float.MaxValue };
                foreach (ConfigurableJoint joint in _joints)
                {
                    if (joint == null) continue;
                    joint.rotationDriveMode = RotationDriveMode.Slerp;
                    joint.targetRotation = Quaternion.identity;
                    joint.slerpDrive = limp;
                }
                WriteTone(_tone);
            }
        }

        /// <summary>Step 4 (NpcStruggle, while DrivesTaken): a slerp drive on this part's joint toward 'target' (joint
        /// space: hinges flex about +X, see MakeJoint).</summary>
        public void Drive(int part, Quaternion target, float spring, float damper, float maxTorque)
        {
            ConfigurableJoint joint = JointOf(part);
            if (joint == null) return;
            if (joint.rotationDriveMode != RotationDriveMode.Slerp) joint.rotationDriveMode = RotationDriveMode.Slerp;
            joint.targetRotation = target;
            joint.slerpDrive = new JointDrive { positionSpring = spring, positionDamper = damper, maximumForce = maxTorque };
        }

        // The drives of a carry tone on the waist, the neck and the hips (every other joint is left as it is: limp).
        private void WriteTone(int tone)
        {
            NpcRagdollProfile p = Profile;
            var limp = new JointDrive { positionSpring = 0f, positionDamper = 0f, maximumForce = float.MaxValue };
            var held = new JointDrive { positionSpring = p.HeldSpring, positionDamper = p.HeldDamper, maximumForce = p.HeldMaxTorque };
            // The waist: in line while held; carried by a split pair, a soft spring the body sags against (a U, not a plank).
            ConfigurableJoint waist = _joints[_chest];
            if (waist != null)
            {
                waist.targetRotation = Quaternion.identity;
                waist.slerpDrive = tone == 0 ? limp : tone == 1 ? held : new JointDrive
                {
                    positionSpring = p.CarryWaistSpring, positionDamper = p.CarryDamper, maximumForce = p.CarryMaxTorque,
                };
            }
            // The neck: flexion only (the head still twists and flops sideways).
            ConfigurableJoint neck = _joints[_head];
            if (neck != null)
            {
                neck.rotationDriveMode = tone == 0 ? RotationDriveMode.Slerp : RotationDriveMode.XYAndZ;
                neck.targetRotation = Quaternion.identity;
                neck.angularXDrive = tone == 0 ? limp : held;
                neck.angularYZDrive = limp;
                neck.slerpDrive = limp;
            }
            // The hips: only when carried by a split pair, held slightly flexed. Joint space: a hinge's flexion axis went
            // in flipped (MakeJoint), so a target turn about +X is flexion (the EditMode test checks the direction).
            var hip = tone == 2
                ? new JointDrive { positionSpring = p.CarryHipSpring, positionDamper = p.CarryDamper, maximumForce = p.CarryMaxTorque }
                : limp;
            Quaternion flexed = Quaternion.AngleAxis(p.CarryHipFlexion, Vector3.right);
            for (int i = 0; i < _joints.Length; i++)
            {
                ConfigurableJoint joint = _joints[i];
                if (joint == null || p.Parts[i].Kind != Kind.Thigh) continue;
                joint.targetRotation = tone == 2 ? flexed : Quaternion.identity;
                joint.slerpDrive = hip;
            }
        }

        /// <summary>The carry tone the joints are driven with now (A4).</summary>
        public int Tone => _tone;

        /// <summary>How many holds are on this kind of handle.</summary>
        public int HoldersOn(Handle handle)
        {
            int n = 0;
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder != null && Claims[i].Handle == handle) n++;
            return n;
        }

        private void LateUpdate()
        {
            if (_blending) Blend();
            else if (!_active) Track();
        }

        // The animation's own motion of each simulated bone relative to the root (m/s), for the momentum at a knockdown.
        // Only in Ragdoll mode, only while walking (CharacterController on) and near the player.
        private void Track()
        {
            float dt = Time.deltaTime;
            if (Mode != NpcBodyMode.Ragdoll || dt <= 0f || (_controller != null && !_controller.enabled))
            {
                _hasMotion = false;
                return;
            }
            Vector3 root = transform.position;
            NpcRagdollProfile p = Profile;
            float radius = p != null ? p.TrackRadius : 30f;
            if ((!TrackAll && (!Listener(out Vector3 listener) || (listener - root).sqrMagnitude > radius * radius)) || !Resolve())
            {
                _hasMotion = false;
                _trackedFrame = -10;
                return;
            }
            bool consecutive = _trackedFrame == Time.frameCount - 1;
            for (int i = 0; i < _bones.Length; i++)
            {
                Vector3 now = _bones[i].position;
                if (consecutive) _motion[i] = (now - _trackPos[i] - (root - _trackRoot)) / dt;
                _trackPos[i] = now;
            }
            _trackRoot = root;
            _hasMotion = consecutive;
            _trackedFrame = Time.frameCount;
        }

        // Where the player is: the on-foot pawn, or the camera while driving. Looked up once per frame for all NPCs.
        private static bool Listener(out Vector3 position)
        {
            if (_listenerFrame != Time.frameCount)
            {
                _listenerFrame = Time.frameCount;
                if (_pawn == null && Time.unscaledTime >= _nextPawnSearch)
                {
                    _pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
                    _nextPawnSearch = Time.unscaledTime + 2f;
                }
                Camera main = Camera.main;
                _hasListener = true;
                if (_pawn != null && _pawn.Controlled) _listener = _pawn.Position;
                else if (main != null) _listener = main.transform.position;
                else _hasListener = false;
            }
            position = _listener;
            return _hasListener;
        }

        private void Blend()
        {
            NpcRagdollProfile p = Profile;
            if (p == null || _allBones == null)
            {
                _blending = false;
                return;
            }
            if (_hipsPending)
            {
                // The armature moved with the root (stood up, sat up): the recorded Hips pose relative to where it is now.
                Transform armature = _hips.parent;
                _hipsSnapPos = armature.InverseTransformPoint(_hipsWorldPos);
                _hipsSnapRot = Quaternion.Inverse(armature.rotation) * _hipsWorldRot;
                _hipsPending = false;
            }
            _blendTime += Time.deltaTime;
            float bodyTime = p.WakeBlend * _blendScale, headTime = p.WakeBlendHead * _blendScale;
            float body = Smooth(_blendTime / Mathf.Max(0.01f, bodyTime));
            float head = Smooth(_blendTime / Mathf.Max(0.01f, headTime));
            for (int k = 0; k < _allBones.Length; k++)
            {
                Transform b = _allBones[k];
                if (b == null) continue;
                float w = _headBone[k] ? head : body;
                if (b == _hips)
                {
                    b.localPosition = Vector3.Lerp(_hipsSnapPos, b.localPosition, w);
                    b.localRotation = Quaternion.Slerp(_hipsSnapRot, b.localRotation, w);
                }
                else b.localRotation = Quaternion.Slerp(_snapRot[k], b.localRotation, w);
            }
            if (_blendTime >= Mathf.Max(bodyTime, headTime)) _blending = false;
        }

        private static float Smooth(float x)
        {
            x = Mathf.Clamp01(x);
            return x * x * (3f - 2f * x);
        }

        // ---------- Geometry ----------

        /// <summary>Centre of a part's capsule (world, physics pose).</summary>
        public Vector3 PartCenter(int part)
        {
            Part pp = Profile.Parts[part];
            Pose(part, out Vector3 position, out Quaternion rotation);
            return position + rotation * pp.Center;
        }

        // The capsule's inner segment (between its cap centres), world, and its radius.
        public void CapsuleSegment(int part, out Vector3 a, out Vector3 b, out float radius)
        {
            Part pp = Profile.Parts[part];
            Pose(part, out Vector3 position, out Quaternion rotation);
            Vector3 c = position + rotation * pp.Center;
            Vector3 axis = rotation * NpcRagdollProfile.AxisVector(pp.Direction);
            float half = Mathf.Max(0f, pp.Height * 0.5f - pp.Radius);
            a = c - axis * half;
            b = c + axis * half;
            radius = pp.Radius;
        }

        // Physics pose while simulated (not the interpolated transform), the bone otherwise.
        private void Pose(int part, out Vector3 position, out Quaternion rotation)
        {
            Rigidbody rb = _active && _bodies != null ? _bodies[part] : null;
            if (rb != null)
            {
                position = rb.position;
                rotation = rb.rotation;
                return;
            }
            Transform bone = BoneOf(part);
            position = bone != null ? bone.position : transform.position;
            rotation = bone != null ? bone.rotation : transform.rotation;
        }

        /// <summary>World position of a landmark (physics pose): the pelvis centre, the top of the chest between the
        /// shoulders, the head centre, an ankle (the shin capsule's foot end). Standing estimates when not a ragdoll.</summary>
        public Vector3 Landmark(NpcLandmark landmark)
        {
            NpcRagdollProfile p = Profile;
            if (!Resolve() || p == null)
                return landmark switch
                {
                    NpcLandmark.Pelvis => transform.TransformPoint(0f, 0.87f, 0f),
                    NpcLandmark.Collar => transform.TransformPoint(0f, 1.3f, 0f),
                    NpcLandmark.Head => transform.TransformPoint(0f, 1.5f, 0f),
                    NpcLandmark.LeftAnkle => transform.TransformPoint(-0.12f, 0.1f, 0f),
                    _ => transform.TransformPoint(0.12f, 0.1f, 0f),
                };
            switch (landmark)
            {
                case NpcLandmark.Pelvis: return PartCenter(_root);
                case NpcLandmark.Head: return PartCenter(_head);
                case NpcLandmark.Collar:
                {
                    Pose(_chest, out Vector3 position, out Quaternion rotation);
                    Part chest = p.Parts[_chest];
                    return position + rotation * (chest.Center + chest.Up * chest.Radius);
                }
                default:
                {
                    int calf = p.IndexOf(Kind.Calf, landmark == NpcLandmark.LeftAnkle ? NpcSide.Left : NpcSide.Right);
                    if (calf < 0) return PartCenter(_root);
                    CapsuleSegment(calf, out _, out Vector3 end, out _);
                    return end;
                }
            }
        }

        /// <summary>The flat direction a body standing up from this pose should face (the get-up convention, §4.4): lying on
        /// its back it sits up toward its feet, on its belly it pushes up toward its head. Zero if undecided.</summary>
        public Vector3 StandFacing()
        {
            if (!_active) return Vector3.zero;
            Vector3 along = Flat(Landmark(NpcLandmark.Head) - Landmark(NpcLandmark.Pelvis));
            Pose(_root, out _, out Quaternion pelvis);
            Vector3 front = pelvis * _pelvisForward;
            Vector3 facing = front.y >= 0f ? -along : along;
            if (facing.sqrMagnitude < 1e-4f) facing = Flat(front);
            return facing.sqrMagnitude > 1e-6f ? facing.normalized : Vector3.zero;
        }

        /// <summary>The part whose capsule surface is nearest to a world point.</summary>
        public int NearestPart(Vector3 world)
        {
            int best = _root;
            float bestGap = float.MaxValue;
            for (int i = 0; i < PartCount; i++)
            {
                CapsuleSegment(i, out Vector3 a, out Vector3 b, out float r);
                float gap = (world - ClosestOnSegment(world, a, b)).magnitude - r;
                if (gap < bestGap)
                {
                    best = i;
                    bestGap = gap;
                }
            }
            return best;
        }

        /// <summary>Part index of one of this ragdoll's colliders (-1 if it is not one).</summary>
        public int PartOf(Collider c)
        {
            if (c == null || !_active) return -1;
            Rigidbody rb = c.attachedRigidbody;
            return rb != null && rb.TryGetComponent(out NpcRagdollPart part) && part.Owner == this ? part.Index : -1;
        }

        private bool Touches(int part)
        {
            if (part < 0 || _bodies[part] == null) return false;
            CapsuleSegment(part, out Vector3 a, out Vector3 b, out float r);
            int count = Physics.OverlapCapsuleNonAlloc(a, b, r + GroundProbe, Overlap, ~(1 << OvLayers.VehicleInterior),
                QueryTriggerInteraction.Ignore);
            bool touches = false;
            for (int i = 0; i < count; i++)
            {
                if (!touches && !Overlap[i].transform.IsChildOf(transform)) touches = true;
                Overlap[i] = null;
            }
            return touches;
        }

        // ---------- Hits (Q) ----------

        /// <summary>Hit zone of a swing along 'ray': the part the ray passes closest to (head; chest or pelvis = torso;
        /// arms and legs = limbs), with the stage-1 forgiveness: within HitZones.HeadReach of the head centre is a head hit.</summary>
        public HitZone ZoneAlong(Ray ray)
        {
            if (!_active) return HitZone.Torso;
            int best = _root;
            float bestGap = float.MaxValue;
            for (int i = 0; i < PartCount; i++)
            {
                CapsuleSegment(i, out Vector3 a, out Vector3 b, out float r);
                float gap = RaySegmentDistance(ray, a, b) - r;
                if (gap < bestGap)
                {
                    best = i;
                    bestGap = gap;
                }
            }
            return ZoneOf(best, RayPointDistance(ray, PartCenter(_head)));
        }

        /// <summary>Hit zone of a world point on the body (no view ray): the nearest part.</summary>
        public HitZone ZoneAt(Vector3 world) =>
            _active ? ZoneOf(NearestPart(world), Vector3.Distance(world, PartCenter(_head))) : HitZone.Torso;

        private HitZone ZoneOf(int part, float headDistance)
        {
            if (headDistance <= HitZones.HeadReach) return HitZone.Head;
            Kind kind = Profile.Parts[part].Kind;
            return kind == Kind.Head ? HitZone.Head : kind == Kind.Pelvis || kind == Kind.Chest ? HitZone.Torso : HitZone.Limb;
        }

        // ---------- Forces (GreyboxNpc) ----------

        // GreyboxNpc's impulses were tuned on the 40 kg stage-1 body: like the capsule, they scale with the mass.
        private float ImpulseScale
        {
            get
            {
                float reference = _capsuleBody != null && _capsuleBody.Mass > 0f ? _capsuleBody.Mass : 40f;
                return Profile.TotalMass / reference;
            }
        }

        /// <summary>An impulse at a world point (a blow), on the part nearest to it: the part takes at most HitPartSpeed of
        /// it there (a head hit still snaps the head back, a leg hit sweeps the legs), the rest moves every body by its
        /// mass, so a punch on a light limb jolts the whole body instead of whipping the limb. A point off the body (a
        /// sitter hit and laid down elsewhere in the bay) is pulled onto that part's capsule, so the impulse never comes
        /// with a long lever.</summary>
        public void Push(Vector3 impulse, Vector3 worldPoint)
        {
            if (!_active) return;
            int part = NearestPart(worldPoint);
            CapsuleSegment(part, out Vector3 a, out Vector3 b, out float radius);
            Vector3 axis = ClosestOnSegment(worldPoint, a, b);
            Vector3 at = axis + Vector3.ClampMagnitude(worldPoint - axis, radius);
            Spread(part, impulse * ImpulseScale, at, _bodies[part].mass * Profile.HitPartSpeed, ForceMode.Impulse);
        }

        /// <summary>A van door's push (Force) or shove (Impulse) on a part (VanDoor through NpcRagdollPart): the part
        /// takes at most DoorPartAccel / DoorPartShove of it, the rest pushes the whole body.</summary>
        public void DoorPush(int part, Vector3 amount, Vector3 worldPoint, ForceMode mode)
        {
            Rigidbody rb = BodyOf(part);
            if (rb == null) return;
            NpcRagdollProfile p = Profile;
            Spread(part, amount, worldPoint, rb.mass * (mode == ForceMode.Impulse ? p.DoorPartShove : p.DoorPartAccel), mode);
        }

        // 'amount' (a force or an impulse) on 'part' at 'at': at most 'own' of it there, the rest on every body by its mass,
        // at its centre of mass (the whole body pushed alike: the same momentum, no spin from it, no whipped limb).
        private void Spread(int part, Vector3 amount, Vector3 at, float own, ForceMode mode)
        {
            float size = amount.magnitude;
            Vector3 local = size > own && size > 1e-6f ? amount * (Mathf.Max(0f, own) / size) : amount;
            _bodies[part].AddForceAtPosition(local, at, mode);
            Vector3 rest = amount - local;
            if (rest.sqrMagnitude < 1e-10f) return;
            float total = 0f;
            foreach (Rigidbody rb in _bodies)
                if (rb != null) total += rb.mass;
            if (total <= 0f) return;
            foreach (Rigidbody rb in _bodies)
                if (rb != null) rb.AddForce(rest * (rb.mass / total), mode);
        }

        /// <summary>The get-up's side roll (§4.4 step 2): angular acceleration (rad/s2) on the pelvis and the chest about
        /// the body's long axis, turning the front toward up (onto its back) or down (onto its belly).</summary>
        public void RollToward(bool faceUp, float acceleration)
        {
            if (!_active) return;
            Vector3 axis = Vector3.Cross(Front, faceUp ? Vector3.up : Vector3.down);
            if (axis.sqrMagnitude < 1e-6f) return;
            axis.Normalize();
            _bodies[_root].AddTorque(axis * acceleration, ForceMode.Acceleration);
            _bodies[_chest].AddTorque(axis * acceleration, ForceMode.Acceleration);
        }

        /// <summary>A kick's ankle impulse. Step 4: the leg's motors kick (NpcStruggle.Kick, GreyboxNpc starts it), so with
        /// the struggle on the impulse is only a flick on top: the shin gets at most KickPartSpeed of it.</summary>
        public void Kick(NpcSide side, Vector3 impulse)
        {
            if (!_active) return;
            NpcRagdollProfile p = Profile;
            int calf = p.IndexOf(Kind.Calf, side);
            if (calf < 0) return;
            Vector3 ankle = Landmark(side == NpcSide.Left ? NpcLandmark.LeftAnkle : NpcLandmark.RightAnkle);
            Vector3 kick = impulse * ImpulseScale;
            float most = _bodies[calf].mass * p.KickPartSpeed;
            if (p.Struggle && kick.magnitude > most) kick = kick.normalized * most;
            _bodies[calf].AddForceAtPosition(kick, ankle, ForceMode.Impulse);
        }

        /// <summary>One crawl step, split between the pelvis and the chest: the push along the ground and a hop that
        /// gives the whole body's centre of mass 'hop' m/s up.</summary>
        public void Scoot(Vector3 push, float hop)
        {
            if (!_active) return;
            Vector3 impulse = 0.5f * (push * ImpulseScale + Vector3.up * (hop * Profile.TotalMass));
            _bodies[_root].AddForce(impulse, ForceMode.Impulse);
            _bodies[_chest].AddForce(impulse, ForceMode.Impulse);
        }

        /// <summary>Contacts of every ragdoll collider with these are ignored for a while, then restored (the van's knock
        /// before 2026-10-11, GreyboxNpc.LegacyVanKnock: the smoke test's before rows).</summary>
        public void IgnoreFor(IEnumerable<Collider> others, float seconds)
        {
            if (!_active) return;
            foreach (Collider c in others)
            {
                if (!IsLive(c) || c.isTrigger || c is WheelCollider || _colliders.Contains(c) || _ignored.Contains(c)) continue;
                foreach (Collider own in _colliders)
                    if (IsLive(own)) Physics.IgnoreCollision(own, c, true);
                _ignored.Add(c);
            }
            _restoreIgnoredAt = Time.time + seconds;
        }

        private void RestoreIgnored()
        {
            foreach (Collider c in _ignored)
            {
                if (!IsLive(c)) continue;
                foreach (Collider own in _colliders)
                    if (IsLive(own)) Physics.IgnoreCollision(own, c, false);
            }
            _ignored.Clear();
        }

        /// <summary>m: a grace pair (IgnoreOverlapping) collides again once its two colliders overlap by less than this.</summary>
        public const float GraceExit = 0.01f;

        /// <summary>INpcBody (a vehicle's knock, Fedya's playtest 2026-10-11): each ragdoll collider that overlaps one of
        /// 'others' now stops colliding with it until the two are apart again (checked every physics step); every other pair
        /// collides at once. So the parts born inside the bumper pass out of it, and no pair comes back into contact while
        /// overlapping: the old fixed 0.5 s let the van drive into the thrown body, then shut it in the windshield or a door.</summary>
        public void IgnoreOverlapping(IEnumerable<Collider> others)
        {
            if (!_active || others == null) return;
            foreach (Collider other in others)
            {
                if (!Touchable(other, _colliders)) continue;
                foreach (Collider own in _colliders)
                {
                    if (!IsLive(own) || Graced(own, other) || !Overlapping(own, other, 0f)) continue;
                    Physics.IgnoreCollision(own, other, true);
                    _grace.Add((own, other));
                }
            }
        }

        /// <summary>Pairs still in the knock's grace (the smoke test).</summary>
        public int GraceCount => _grace.Count;

        private bool Graced(Collider own, Collider other)
        {
            foreach ((Collider a, Collider b) in _grace)
                if (a == own && b == other) return true;
            return false;
        }

        // The grace pairs collide again once apart (or gone); all: every pair now (back to a plain NPC).
        private void EndGrace(bool all)
        {
            for (int i = _grace.Count - 1; i >= 0; i--)
            {
                (Collider own, Collider other) = _grace[i];
                bool live = IsLive(own) && IsLive(other);
                if (!all && live && Overlapping(own, other, GraceExit)) continue;
                if (live) Physics.IgnoreCollision(own, other, false);
                _grace.RemoveAt(i);
            }
        }

        /// <summary>A vehicle's collider a downed body can meet: live, solid, not a wheel, not the body's own, on a layer that
        /// touches NpcBody (the downed body's colliders also include Vehicle, CollideWithVehicles).</summary>
        public static bool Touchable(Collider c, ICollection<Collider> own) =>
            IsLive(c) && !c.isTrigger && !(c is WheelCollider) && (own == null || !own.Contains(c)) &&
            ((OvLayers.VehicleMask & (1 << c.gameObject.layer)) != 0 || !Physics.GetIgnoreLayerCollision(OvLayers.NpcBody, c.gameObject.layer));

        /// <summary>Whether two colliders overlap by more than 'depth' (m), at their bodies' physics poses (an interpolated
        /// body's transform trails it). One of them must be a primitive (ComputePenetration).</summary>
        public static bool Overlapping(Collider a, Collider b, float depth)
        {
            Bounds ab = a.bounds;
            ab.Expand(0.02f);
            if (!ab.Intersects(b.bounds)) return false;
            ColliderPose(a, out Vector3 pa, out Quaternion qa);
            ColliderPose(b, out Vector3 pb, out Quaternion qb);
            return Physics.ComputePenetration(a, pa, qa, b, pb, qb, out _, out float d) && d > depth;
        }

        /// <summary>A collider's world pose from its body's physics pose (Rigidbody position and rotation).</summary>
        public static void ColliderPose(Collider c, out Vector3 position, out Quaternion rotation)
        {
            Rigidbody rb = c.attachedRigidbody;
            Transform t = c.transform;
            if (rb == null)
            {
                position = t.position;
                rotation = t.rotation;
                return;
            }
            Transform bt = rb.transform;
            Quaternion inverse = Quaternion.Inverse(bt.rotation);
            position = rb.position + rb.rotation * (inverse * (t.position - bt.position));
            rotation = rb.rotation * (inverse * t.rotation);
        }

        private static bool IsLive(Collider c) => c != null && c.enabled && c.gameObject.activeInHierarchy;

        // ---------- Contacts ----------

        // From NpcRagdollPart: the strongest torso or head contact of the tick (flopping limbs would spam), raised in the
        // next FixedUpdate. Its own limbs and kinematic bodies (players' KCC capsules) do not count.
        internal void OnPartCollision(int part, Collision collision)
        {
            if (!_active || collision.contactCount == 0) return;
            Kind kind = Profile.Parts[part].Kind;
            if (kind != Kind.Pelvis && kind != Kind.Chest && kind != Kind.Head) return;
            Collider other = collision.collider;
            if (other == null || other.transform.IsChildOf(transform)) return;
            if (collision.rigidbody != null && collision.rigidbody.isKinematic) return;
            ContactPoint contact = collision.GetContact(0);
            float speed = Mathf.Abs(Vector3.Dot(collision.relativeVelocity, contact.normal));
            if (speed <= _impactSpeed) return;
            _impactSpeed = speed;
            _impactOther = other;
            _impactPoint = contact.point;
        }

        private void RaiseImpact()
        {
            float speed = _impactSpeed;
            Collider other = _impactOther;
            _impactSpeed = 0f;
            _impactOther = null;
            Thud(speed, other, _impactPoint);
            Impact?.Invoke(speed, other);
        }

        // A body landing, as GreyboxNpcBody does it (same thresholds): louder the harder; the library's cooldown stops spam.
        private void Thud(float speed, Collider other, Vector3 point)
        {
            float min = _capsuleBody != null ? _capsuleBody.ThudMinSpeed : 1.2f;
            float full = _capsuleBody != null ? _capsuleBody.ThudFullSpeed : 6f;
            if (speed < min || other == null) return;
            string id = other.gameObject.layer == OvLayers.Vehicle ? SfxIds.ThudVan : SfxIds.ThudGround;
            Sfx.PlayAt(id, point, Mathf.Lerp(0.35f, 1f, Mathf.InverseLerp(min, Mathf.Max(min + 0.01f, full), speed)));
        }

        // ---------- Holds (NpcRagdollPart -> PhysicsGrabber) ----------

        /// <summary>Claims a hold on 'part' for 'holder' (one per holder, at most MaxHolders per NPC). point = the slot,
        /// local = the hold in the part body's frame, profile = the part's handle.</summary>
        public bool TryClaim(object holder, int part, Vector3 hit, out int point, out Vector3 local, out GrabPhysicsProfile profile)
        {
            point = -1;
            local = Vector3.zero;
            profile = null;
            if (holder == null || !_grabbable || !_active || !isActiveAndEnabled || part < 0 || part >= PartCount ||
                _bodies[part] == null || SlotOf(holder) >= 0)
                return false;
            point = FreeSlot();
            if (point < 0) return false;
            local = ClaimLocal(part, hit, out Handle handle);
            profile = HandleProfile(handle);
            Claims[point] = new Claim { Holder = holder, Part = part, Local = local, Handle = handle };
            return true;
        }

        public bool IsClaimValid(object holder, int point, int part) =>
            holder != null && point >= 0 && point < Claims.Length && ReferenceEquals(Claims[point].Holder, holder) &&
            Claims[point].Part == part && _grabbable && _active && isActiveAndEnabled && _bodies[part] != null;

        public void Release(object holder, int point)
        {
            if (point < 0 || point >= Claims.Length || !ReferenceEquals(Claims[point].Holder, holder)) return;
            Claims[point] = default;
            if (holder is DebugPin pin) _pins.Remove(pin);
        }

        /// <summary>Every holder lets go (woke up).</summary>
        public void RevokeAll()
        {
            Array.Clear(Claims, 0, Claims.Length);
            _pins.Clear();
        }

        public float HoldMassOf(int part)
        {
            NpcRagdollProfile p = Profile;
            if (p != null && p.UseHoldMass) return p.HoldMass;
            Rigidbody rb = BodyOf(part);
            return rb != null ? rb.mass : 1f;
        }

        /// <summary>A hand's force on the held part. A2 (SpreadForce): on a limb or the head only (1 - SpreadShare) of it
        /// goes to the held bone at the hold; the rest is split evenly over its parents up to the trunk (the chest or the
        /// pelvis), each share at the joint where the bone below hangs on it. A forearm: 60 % at the hand's hold, 20 % to
        /// the upper arm at the elbow, 20 % to the chest at the shoulder. Trunk holds are not spread. One hand alone on an
        /// arm or a leg (SoloLimbHeld) lifts at most SoloLimbLift (Fedya's playtest 2026-10-11): the limb comes up, the
        /// trunk stays down; sideways the handle's cap is unchanged (dragging).</summary>
        public void ApplyHoldForce(int part, Vector3 worldPoint, Vector3 force)
        {
            Rigidbody rb = BodyOf(part);
            if (rb == null) return;
            NpcRagdollProfile p = Profile;
            if (force.y > p.SoloLimbLift && SoloLimbHeld) force.y = p.SoloLimbLift;
            LastHoldForce = force;
            Kind kind = p.Parts[part].Kind;
            if (!p.SpreadForce || p.SpreadShare <= 0f || kind == Kind.Pelvis || kind == Kind.Chest)
            {
                GrabPhysicsSolver.ApplyForce(rb, worldPoint, force);
                return;
            }
            int links = 0;
            for (int c = part; ; c = p.Parts[c].Parent)
            {
                int parent = p.Parts[c].Parent;
                if (parent < 0) break;
                links++;
                Kind up = p.Parts[parent].Kind;
                if (up == Kind.Chest || up == Kind.Pelvis) break;
            }
            if (links == 0)
            {
                GrabPhysicsSolver.ApplyForce(rb, worldPoint, force);
                return;
            }
            float share = Mathf.Clamp01(p.SpreadShare);
            GrabPhysicsSolver.ApplyForce(rb, worldPoint, force * (1f - share));
            Vector3 each = force * (share / links);
            for (int c = part, k = 0; k < links; k++, c = p.Parts[c].Parent)
            {
                Rigidbody parentBody = _bodies[p.Parts[c].Parent];
                if (parentBody == null) continue;
                // The joint of bone c sits at its own body's origin (anchor zero).
                parentBody.AddForceAtPosition(each, _bodies[c].position, ForceMode.Force);
            }
        }

        /// <summary>World position of the hold in a slot (physics pose).</summary>
        public Vector3 ClaimWorld(int slot)
        {
            Claim c = Claims[slot];
            Rigidbody rb = BodyOf(c.Part);
            return rb != null ? rb.position + rb.rotation * c.Local : CenterOfMass;
        }

        /// <summary>Tears one hold loose: a hold on the kicking leg first (an ankle landmark), then the one nearest the
        /// landmark (within TearRadius), then a random one.</summary>
        public bool Tear(NpcLandmark preferred)
        {
            if (HolderCount == 0) return false;
            NpcRagdollProfile p = Profile;
            int slot = -1;
            if (preferred == NpcLandmark.LeftAnkle || preferred == NpcLandmark.RightAnkle)
            {
                NpcSide side = preferred == NpcLandmark.LeftAnkle ? NpcSide.Left : NpcSide.Right;
                for (int i = 0; i < Claims.Length && slot < 0; i++)
                {
                    if (Claims[i].Holder == null) continue;
                    Part part = p.Parts[Claims[i].Part];
                    if ((part.Kind == Kind.Calf || part.Kind == Kind.Thigh) && part.Side == side) slot = i;
                }
            }
            if (slot < 0)
            {
                Vector3 at = Landmark(preferred);
                float best = TearRadius;
                for (int i = 0; i < Claims.Length; i++)
                {
                    if (Claims[i].Holder == null) continue;
                    float d = Vector3.Distance(ClaimWorld(i), at);
                    if (d > best) continue;
                    best = d;
                    slot = i;
                }
            }
            if (slot < 0)
            {
                int pick = UnityEngine.Random.Range(0, HolderCount);
                for (int i = 0; i < Claims.Length && slot < 0; i++)
                    if (Claims[i].Holder != null && pick-- == 0) slot = i;
            }
            if (slot < 0) return false;
            Release(Claims[slot].Holder, slot);
            return true;
        }

        private int SlotOf(object holder)
        {
            for (int i = 0; i < Claims.Length; i++)
                if (ReferenceEquals(Claims[i].Holder, holder)) return i;
            return -1;
        }

        private int FreeSlot()
        {
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder == null) return i;
            return -1;
        }

        // Where a hold on 'part' sits, in the part body's frame: limbs and the head on their capsule axis, between the cap
        // centres (the stage-1 trick: a pull never twists a limb about itself); the pelvis and chest on the spine line
        // through the capsule's middle, inside the body (no roll). The chest's top CollarBand of its depth along the spine
        // is the collar (good handle), the rest the belly (bad).
        private Vector3 ClaimLocal(int part, Vector3 world, out Handle handle)
        {
            NpcRagdollProfile p = Profile;
            Part pp = p.Parts[part];
            Pose(part, out Vector3 position, out Quaternion rotation);
            Vector3 l = Quaternion.Inverse(rotation) * (world - position);
            handle = pp.Handle;
            if (pp.Kind == Kind.Pelvis || pp.Kind == Kind.Chest)
            {
                float s = Vector3.Dot(l - pp.Center, pp.Up);
                if (pp.Kind == Kind.Chest) handle = s >= pp.Radius * (1f - 2f * p.CollarBand) ? Handle.Good : Handle.Bad;
                float reach = Mathf.Max(0f, pp.Radius - ClaimInset);
                return pp.Center + pp.Up * Mathf.Clamp(s, -reach, reach);
            }
            Vector3 axis = NpcRagdollProfile.AxisVector(pp.Direction);
            float half = Mathf.Max(0f, pp.Height * 0.5f - pp.Radius);
            return pp.Center + axis * Mathf.Clamp(Vector3.Dot(l - pp.Center, axis), -half, half);
        }

        // The stage-1 hand (this NPC's GreyboxNpcBody profile, NpcGrabProfile.asset) with the handle's force caps; made once
        // per base profile and handle, never saved.
        private GrabPhysicsProfile HandleProfile(Handle handle)
        {
            GrabPhysicsProfile basis = _capsuleBody != null ? _capsuleBody.Profile : GreyboxNpcBody.FallbackProfile;
            Vector2 force = Profile.Force(handle);
            var key = (basis, handle, force.x, force.y);
            if (HandleProfiles.TryGetValue(key, out GrabPhysicsProfile made) && made != null) return made;
            made = Instantiate(basis);
            made.name = $"{basis.name} ({handle})";
            made.hideFlags = HideFlags.DontSave;
            JsonUtility.FromJsonOverwrite(string.Format(CultureInfo.InvariantCulture,
                "{{\"maxForce\":{0},\"soloHorizontalMaxForce\":{1}}}", force.x, force.y), made);
            HandleProfiles[key] = made;
            return made;
        }

        /// <summary>How far a hand reaches to take hold (the handle profiles share the stage-1 hand's reach).</summary>
        public float GrabReach => (_capsuleBody != null ? _capsuleBody.Profile : GreyboxNpcBody.FallbackProfile).AcquireDistance;

        /// <summary>For the grab hint: the part a grab at 'world' on collider 'hit' would take (accusative, "взять за ..."),
        /// with " — тяжело" on bad handles; null if the grab would be refused.</summary>
        public string GrabHintName(Collider hit, Vector3 world)
        {
            if (!_grabbable || !_active || HolderCount >= MaxHolders) return null;
            int part = PartOf(hit);
            if (part < 0) return null;
            NpcRagdollProfile p = Profile;
            Part pp = p.Parts[part];
            ClaimLocal(part, world, out Handle handle);
            string name = pp.Hint;
            if (pp.Kind == Kind.Chest)
            {
                // The collar band: the chest from the front, the collar at the back of the neck; below it the belly.
                Pose(part, out Vector3 position, out Quaternion rotation);
                float front = Vector3.Dot(Quaternion.Inverse(rotation) * (world - position) - pp.Center, _chestForward);
                name = handle == Handle.Bad ? "живот" : front >= 0f ? "грудь" : "ворот";
            }
            else if (pp.Kind == Kind.Calf && hit is BoxCollider) name = "ступню";
            return handle == Handle.Bad ? name + " — тяжело" : name;
        }

        // ---------- F9 debug pins (offline stand-ins for other holders) ----------

        /// <summary>Pins the hold point nearest to 'point' on the hit part, 'lift' metres above where it is now, held like a
        /// player's hand on that handle. Within PinToggleRadius of an existing pin it removes that pin instead.</summary>
        public bool TogglePin(Collider hit, Vector3 point, float lift)
        {
            int part = PartOf(hit);
            if (part < 0) return false;
            Pose(part, out Vector3 position, out Quaternion rotation);
            Vector3 at = position + rotation * ClaimLocal(part, point, out _);
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin old = _pins[i];
                if (Vector3.Distance(ClaimWorld(old.Slot), at) > PinToggleRadius) continue;
                Release(old, old.Slot);
                return false;
            }
            var pin = new DebugPin();
            if (!TryClaim(pin, part, point, out int slot, out _, out _)) return false;
            pin.Slot = slot;
            pin.Anchor = ClaimWorld(slot) + Vector3.up * lift;
            _pins.Add(pin);
            return true;
        }

        public void UnpinAll()
        {
            for (int i = _pins.Count - 1; i >= 0; i--)
                Release(_pins[i], _pins[i].Slot);
        }

        private void HoldPins()
        {
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin pin = _pins[i];
                Claim c = Claims[pin.Slot];
                if (!ReferenceEquals(c.Holder, pin) || !IsClaimValid(pin, pin.Slot, c.Part))
                {
                    _pins.RemoveAt(i);
                    continue;
                }
                // Shaped like a player's hand (PhysicsGrabber's point hold, anchor at rest).
                GrabPhysicsProfile profile = HandleProfile(c.Handle);
                Vector3 world = ClaimWorld(pin.Slot);
                Vector3 velocity = _bodies[c.Part].GetPointVelocity(world);
                Vector3 error = pin.Anchor - world;
                float mass = HoldMassOf(c.Part);
                Vector3 force;
                bool held = profile.SoloHorizontalMaxForce > 0f
                    ? GrabPhysicsSolver.TryCalculateRelativeGrounded(error, Vector3.zero, velocity, mass, profile, out force)
                    : GrabPhysicsSolver.TryCalculateRelative(error, Vector3.zero, velocity, mass, profile, out force);
                if (!held)
                {
                    Release(pin, pin.Slot);
                    continue;
                }
                ApplyHoldForce(c.Part, world, force);
            }
        }

        // ---------- Maths ----------

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        private static Vector3 ClosestOnSegment(Vector3 p, Vector3 a, Vector3 b)
        {
            Vector3 ab = b - a;
            float len = ab.sqrMagnitude;
            return len < 1e-10f ? a : a + ab * Mathf.Clamp01(Vector3.Dot(p - a, ab) / len);
        }

        private static float RayPointDistance(Ray ray, Vector3 p)
        {
            float along = Mathf.Max(0f, Vector3.Dot(p - ray.origin, ray.direction));
            return (p - (ray.origin + ray.direction * along)).magnitude;
        }

        // Shortest distance between a ray (t >= 0) and the segment a-b.
        private static float RaySegmentDistance(Ray ray, Vector3 a, Vector3 b)
        {
            Vector3 d1 = ray.direction.normalized, d2 = b - a, r = ray.origin - a;
            float e = Vector3.Dot(d2, d2), c = Vector3.Dot(d1, r), f = Vector3.Dot(d2, r);
            float s, t;
            if (e < 1e-10f)
            {
                t = 0f;
                s = Mathf.Max(0f, -c);
            }
            else
            {
                float bb = Vector3.Dot(d1, d2);
                float denominator = e - bb * bb;
                s = denominator > 1e-10f ? Mathf.Max(0f, (bb * f - c * e) / denominator) : 0f;
                t = (bb * s + f) / e;
                if (t < 0f)
                {
                    t = 0f;
                    s = Mathf.Max(0f, -c);
                }
                else if (t > 1f)
                {
                    t = 1f;
                    s = Mathf.Max(0f, bb - c);
                }
            }
            return (ray.origin + d1 * s - (a + d2 * t)).magnitude;
        }

        // Holds red, landmarks yellow.
        private void OnDrawGizmosSelected()
        {
            if (!_active) return;
            Gizmos.color = Color.yellow;
            for (int l = 0; l <= (int)NpcLandmark.RightAnkle; l++)
                Gizmos.DrawWireSphere(Landmark((NpcLandmark)l), 0.04f);
            Gizmos.color = Color.red;
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder != null)
                    Gizmos.DrawWireSphere(ClaimWorld(i), 0.06f);
        }
    }
}
