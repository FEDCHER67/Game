using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using FishNet.Transporting;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Replicated view of the table: the patient plus the shared consumables.</summary>
    [Serializable]
    public sealed class OperationView
    {
        public OperationState patient;
        public float stock;
        public float barrel;
        public float blood;
        public int bagsUsedMask;
        public bool injecting;
        public int drawing = -1;
        /// <summary>Fill (0..1) of each empty blood bag on the tray; it rises while a syringe empties into it.</summary>
        public float[] bagFill = new float[0];
        public int[] pullers = new int[3];
        /// <summary>The escape clip (Op_EscapeFall) is playing: the root stays on PatientRest until it lands.</summary>
        public bool falling;
    }

    /// <summary>One authoritative operating table (a pushable gurney). Clients only send intents: the selected tool,
    /// the target under their cursor with its table-local hit point, buttons and the pull drag. The server validates
    /// everything in table-local / incision-local space; only FixedUpdate spends time, stock or detaches organs.</summary>
    public sealed class NetworkOperationTable : NetworkBehaviour
    {
        [SerializeField] private OperationTuning tuning;
        [SerializeField] private NetworkPhysicsBody patientPrefab;
        [Tooltip("Anesthesia syringe, blood syringe, scalpel.")]
        [SerializeField] private OperationTool[] toolPrefabs;
        [Tooltip("Kidney, liver, sealed blood bag.")]
        [SerializeField] private OperationPhysicalItem[] merchandisePrefabs;
        [SerializeField] private ItemDefinition[] merchandiseDefinitions;
        [SerializeField] private PatientRegistry registry;
        [Tooltip("Dev scene default: every host start gets a fresh patient. The save loads only when this is on or with -ops-load.")]
        [SerializeField] private bool loadSavedOperation;

        private readonly SyncVar<string> snapshot = new();
        private readonly SyncVar<NetworkObject> patientObject = new();
        private readonly Dictionary<int, Participant> participants = new();
        private readonly List<int> removedParticipants = new();
        private readonly List<OperationTool> tools = new();
        private readonly List<OperationPhysicalItem> items = new();
        private readonly bool[] yankLatched = new bool[3];
        private readonly float[] pullSums = new float[3];
        private readonly int[] pullHolders = new int[3];
        private readonly Participant[] outputHolders = new Participant[3];
        private readonly Dictionary<string, Transform> named = new();
        private readonly Dictionary<int, RemoteCursor> cursors = new();
        private OperationWorldState world;
        private OperationRules rules;
        private OperationView mirror;
        private readonly OperationView serverView = new();
        private NetworkPhysicsBody patient;
        private Rigidbody tableBody;
        private PatientRecord record;
        private float nextSnapshot;
        // Rework 2026-10-18: a full blood syringe empties into a bag over tuning.bloodTransferSeconds.
        private int transferBag = -1, transferClient = -1;
        private float transferProgress;
        private float[] bagFills = new float[0];
        public bool Transferring => transferBag >= 0;
        /// <summary>The transfer's source is a player's field blood syringe (stage A), not the table's own syringe.</summary>
        private const int FieldClient = -2;
        private System.Action<float> fieldFill;
        /// <summary>Server: the empty bag slot 'bag' can take blood now (not used, no transfer running).</summary>
        public bool BagFree(int bag) => IsServerInitialized && world != null && bag >= 0 && bag < tuning.bloodBagCount && (world.bagsUsedMask & (1 << bag)) == 0 && transferBag < 0;
        /// <summary>Server, stage A (Fedya round 2): a player walks up with the blood syringe he filled in the field and
        /// empties it into an empty table bag: the same smooth transfer as the table's own syringe (the plunger goes down
        /// through 'setFieldFill' 1 → 0 while the bag fills by the same amount, synced), then the bag is sealed into one
        /// blood item. The portion was already counted on the NPC when it was drawn; the bag value is counted once here.</summary>
        public bool ServerFieldTransfer(int bag, System.Action<float> setFieldFill)
        {
            if (!BagFree(bag) || setFieldFill == null) return false;
            transferBag = bag; transferClient = FieldClient; transferProgress = 0f; fieldFill = setFieldFill;
            Debug.Log($"[OPS] BLOOD TRANSFER (field syringe) start bag={bag}");
            return true;
        }

        // ---------- round 3: the field kit on the table patient (a player standing by the table, not in its view) ----------
        private float fieldDose;
        /// <summary>Server, stage A (round 3): the field anaesthesia syringe on the table patient. The table syringe's own
        /// rule (alive, on the table and aligned, an injection site: arm, shoulder or neck); the dose joins the next rules
        /// tick exactly like the table syringe's (same residual, sleep and overdose model). Returns the amount accepted
        /// (at most a tenth of a second's push per call); 'refusal' says why nothing was.</summary>
        public float ServerFieldDose(BodyPart part, float amount, out OpHint refusal)
        {
            refusal = OpHint.None;
            if (!IsServerInitialized || !admissionMode || !HasPatient) { refusal = OpHint.NotOnTable; return 0f; }
            if (!State.alive) { refusal = OpHint.PatientDead; return 0f; }
            if (!rules.CanInject) { refusal = OpHint.NotOnTable; return 0f; }
            if (!new OpTarget(TargetKind.Body, (int)part).IsInjectionSite) { refusal = OpHint.WrongSpot; return 0f; }
            if (!OperationRules.Finite(amount) || amount <= 0f) return 0f;
            float accepted = Mathf.Min(amount, tuning.dosePerSecond * 0.1f);
            fieldDose += accepted;
            return accepted;
        }
        /// <summary>Server, stage A (round 3): the field blood syringe on the table patient's arm: the table's own rule
        /// (OperationRules.CanDrawBlood: asleep, held down, that arm strapped, or dead; a portion left) and FillBlood
        /// (portions, weakness, death cues), the fill living in the player's syringe. 'portion' is true when it filled.</summary>
        public OpHint ServerFieldDrawBlood(BodyPart part, ref float fill, float seconds, out bool portion)
        {
            portion = false;
            if (!IsServerInitialized || !admissionMode || !HasPatient) return OpHint.NotOnTable;
            int arm = new OpTarget(TargetKind.Body, (int)part).ArmSide;
            if (arm < 0) return OpHint.WrongSpot;
            if (!State.onTable || !State.aligned) return OpHint.NotOnTable;
            if (fill >= 1f) return OpHint.SyringeFull;
            if (State.bloodPortions >= tuning.fatalPortion) return OpHint.NoBloodLeft;
            if (!rules.CanDrawBlood(arm)) return OpHint.Squirming;
            if (!OperationRules.Finite(seconds) || seconds <= 0f) return OpHint.None;
            portion = rules.FillBlood(ref fill, Mathf.Min(seconds, 0.1f));
            if (portion) nextSnapshot = 0f;
            return OpHint.None;
        }

        /// <summary>The escape clip is playing (the root stays on PatientRest until it lands).</summary>
        public bool PatientFalling => falling;

        /// <summary>Server, admission mode, round 3 (Fedya's bug: a living patient off the table "stopped being a person"):
        /// a LIVING patient who is off the table (the escape fall has landed, or he was taken off), held by nobody, leaves
        /// the table's ownership with the same OperationState, so the caller makes him a field NPC again (he gets up and
        /// runs, can be hit, tied, injected and bled). Returns his state and where his body lies, or null when he stays.</summary>
        public OperationState ServerDischargeLiving(out Vector3 pelvis, out Vector3 headDirection, out bool faceUp)
        {
            pelvis = Vector3.zero; headDirection = Vector3.forward; faceUp = true;
            if (!IsServerInitialized || !admissionMode || !HasPatient || (falling && !runOff)) return null;
            var s = rules.State;
            if (!s.alive || s.onTable || patient.HasHolder) return null;
            Transform hips = null, head = null;
            foreach (Transform t in patient.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "mixamorig:Hips") hips = t;
                else if (t.name == "mixamorig:Head") head = t;
            }
            pelvis = hips != null ? hips.position : patient.transform.position;
            Vector3 toHead = head != null && hips != null ? head.position - hips.position : patient.transform.right;
            toHead = Vector3.ProjectOnPlane(toHead, Vector3.up);
            headDirection = toHead.sqrMagnitude > 1e-4f ? toHead.normalized : Vector3.forward;
            faceUp = hips == null || Vector3.Dot(hips.forward, Vector3.up) > -0.2f;
            s.onTable = false; s.aligned = false; s.knockedOut = false; s.escapeProgress = 0f; s.unbuckleProgress = 0f;
            Array.Clear(s.restraints, 0, s.restraints.Length);
            falling = false; runOff = false; serverView.falling = false;
            fieldDose = 0f;
            GetComponent<OperationPresentation>()?.ReleasePatientVisuals();
            Abdomen?.ReleasePatientVisuals();
            string id = ServerRemovePatient(true);
            Debug.Log($"[OPS] DISCHARGED living patient={id} at {pelvis} (back to the field)");
            return s;
        }
        private float nextSave;
        private bool frozen;
        private bool alignStartSet;
        private Vector3 alignFromLocal;
        private Quaternion alignFromRotation;
        private int ctxOrgan = -1, ctxClient = -1;
        private int fellFrame = -1;
        private float noAlignUntil;
        private bool falling;
        private float fallEndsAt;
        /// <summary>Round 4: the escape clips ended with him on his feet (HopRun) or face down (Stumble_Off): the root stays
        /// on PatientRest holding the last clip pose until the capture bridge hands him to the field (fallback: Land).</summary>
        private bool runOff;
        public bool PatientRanOff => falling && runOff;
        private float nextSideAt;
        // Capture -> delivery stage A (map scene, CAPTURE_DELIVERY_SPEC v01 D3/D4): the table starts empty and takes the
        // captured NPC's own OperationState when he is laid on it (ServerAdmit). It never writes the dev operation save.
        private bool admissionMode;
        public OperationAbdomen Abdomen { get; private set; }
        public bool AdmissionMode => admissionMode;
        public bool HasPatient => rules != null && patient != null;
        /// <summary>Server: raised after the patient object was spawned (fresh, admitted or restored).</summary>
        public event Action<NetworkPhysicsBody> ServerPatientSpawned;

        public OperationTuning Tuning => tuning;
        public NetworkPhysicsBody PatientPrefab => patientPrefab;
        public OperationState State => IsServerInitialized ? rules?.State : mirror?.patient;
        public OperationView View => IsServerInitialized ? serverView : mirror;
        public NetworkObject PatientObject => patientObject.Value;
        public NetworkPhysicsBody PatientBody => patientObject.Value != null ? patientObject.Value.GetComponent<NetworkPhysicsBody>() : null;
        public OperationRules ServerRules => rules;
        public OperationWorldState ServerWorld => world;
        public IReadOnlyList<OperationPhysicalItem> ServerItems => items;
        public int ParticipantCount => participants.Count;
        public OperationPatientAnchors Anchors => PatientObject != null ? PatientObject.GetComponent<OperationPatientAnchors>() : null;
        public OperationPatientRig PatientRig => PatientObject != null ? PatientObject.GetComponent<OperationPatientRig>() : null;
        public bool AnatomyReady => Anchors != null && Anchors.Valid;
        public bool Frozen => frozen;
        /// <summary>Cue, organ index (or -1), client id (or -1). Raised on every peer.</summary>
        public event Action<PatientCue, int, int> CueReceived;
        public event Action<PatientCue> AnimationHook;
        public event Action<OpHint, int> HintReceived;
        public IReadOnlyDictionary<int, RemoteCursor> Cursors => cursors;

        public sealed class RemoteCursor
        {
            public Vector3 local;
            public Vector3 smoothed;
            public bool pressed;
            public ToolSlot slot;
            public float at;
        }

        private const float PrepClickDelay = 0.1f;
        public sealed class Participant
        {
            public int id;
            public NetworkPlayer player;
            public NetworkInventory inventory;
            public OperationTool tool;
            public uint sequence;
            public uint pressId;
            public bool pressStart;
            public bool pressed;
            public OpTarget pressTarget;
            public OpTarget target;
            public Vector3 point;
            public Vector3 lastPoint;
            public float pullTarget;
            public float received;
            public int strokeOrgan = -1;
            public bool strokeRejected;
            public int pullOrgan = -1;
            public OpHint lastHint;
            public float hintAt;
            public bool directDone;
            public TableCamera cameraMode = TableCamera.Prep;
            /// <summary>Server time the participant's view became PREP (strap clicks need the PREP camera to have blended in).</summary>
            public float prepSince;
        }

        // ---------- named anchors ----------
        private Transform Find(string name)
        {
            if (named.TryGetValue(name, out var t) && t != null) return t;
            t = FindDeep(transform, name);
            named[name] = t;
            return t;
        }
        private static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            for (int i = 0; i < root.childCount; i++) { var r = FindDeep(root.GetChild(i), name); if (r != null) return r; }
            return null;
        }
        public Transform PatientRest => Find("PatientRest");
        public Transform CameraAnchor => Find("CameraAnchor");
        public Transform TrayAnchor => Find("TrayAnchor");
        public Transform Slot(string name) => Find(name);
        public Transform StrapTransform(int i) => Find(StrapNames[i]);
        public static readonly string[] StrapNames = { "STRAP_ARM_L", "STRAP_ARM_R", "STRAP_LEG_L", "STRAP_LEG_R", "STRAP_TORSO" };
        public static readonly string[] ToolSlotNames = { "SLOT_SYRINGE_ANESTHESIA", "SLOT_SYRINGE_BLOOD", "SLOT_SCALPEL" };
        public static string BagSlotName(int i) => "SLOT_BLOODBAG_" + (i + 1);
        public static string OrganSlotName(int i) => "SLOT_ORGAN_" + (i + 1);

        public Pose RestPose
        {
            get
            {
                var rest = PatientRest;
                return rest != null ? new Pose(rest.position, rest.rotation)
                    : new Pose(transform.TransformPoint(tuning.patientRest), transform.rotation * Quaternion.Euler(0, 180, 0));
            }
        }
        public Pose CameraPose
        {
            get
            {
                if (tuning.sharedAbdomen)
                    return new Pose(transform.TransformPoint(tuning.cameraPosition), Quaternion.LookRotation(-transform.up, transform.forward));
                var anchor = CameraAnchor;
                if (anchor != null && !tuning.overrideCameraAnchor) return new Pose(anchor.position, anchor.rotation);
                Vector3 p = transform.TransformPoint(tuning.cameraPosition);
                return new Pose(p, Quaternion.LookRotation(transform.TransformPoint(tuning.cameraLookAt) - p));
            }
        }
        // Slot frames ignore the slot transforms' own axes (props FBX slots keep Blender axes): position from the slot,
        // orientation from the table (tools lie along the table's length; bags and organs square to it).
        private Quaternion ToolSlotRotation => transform.rotation * Quaternion.Euler(0f, -90f, 0f);
        public Pose DockPose(OperationTool tool)
        {
            int i = tool.Kind == OperationToolKind.Syringe ? 0 : tool.Kind == OperationToolKind.BloodSyringe ? 1 : 2;
            var slot = Find(ToolSlotNames[i]);
            Vector3 p = slot != null ? slot.position : transform.TransformPoint(tuning.trayPosition + new Vector3(0.135f, 0.69f, 0.165f - i * 0.165f));
            // Round 3: the needle holder lies on the stand next to the scalpel (its own SLOT_SUTURE when the stand has one).
            if (tool.Kind == OperationToolKind.Suture)
            {
                var own = Find("SLOT_SUTURE");
                p = own != null ? own.position : p + transform.right * -0.06f;
            }
            return tool.DockPoseFor(new Pose(p, ToolSlotRotation));
        }
        public Pose BagPose(int i)
        {
            var slot = Find(BagSlotName(i));
            return new Pose(slot != null ? slot.position : transform.TransformPoint(tuning.trayPosition + new Vector3(0f, 0.69f, 0.165f - i * 0.165f)), transform.rotation);
        }
        public Pose OrganSlotPose(int i)
        {
            var slot = Find(OrganSlotName(i));
            return new Pose(slot != null ? slot.position : transform.TransformPoint(tuning.trayPosition + new Vector3(-0.135f, 0.69f, 0.165f - i * 0.165f)), transform.rotation);
        }

        // ---------- geometry ----------
        public Vector3 SitePoint(int organ, Vector3 metres) => tuning.sharedAbdomen && organ == OperationAbdomenGeometry.ZoneGuide ? Abdomen.Point(organ, metres) : Anchors.Point(organ, metres);
        public Vector3 SiteLocal(int organ, Vector3 world) => tuning.sharedAbdomen && organ == OperationAbdomenGeometry.ZoneGuide ? Abdomen.Local(organ, world) : Anchors.LocalMetres(organ, world);
        public Vector3 OrganPosition(int i) => Anchors.Point(i, new Vector3(0, 0, tuning.organLift));
        public Vector3 OrganNormal(int i) => tuning.sharedAbdomen && i == OperationAbdomenGeometry.ZoneGuide ? transform.up : Anchors.Normal(i);
        public Vector3 GuidePosition(int i, float along) => SitePoint(i, tuning.sharedAbdomen ? OperationAbdomenGeometry.Point(tuning, i, along) : OperationGeometry.GuidePoint(tuning, i, along));
        public Vector2 GuideCoordinates(int i, Vector3 local) => tuning.sharedAbdomen ? Abdomen.Coordinates(i, local) : OperationGeometry.GuideCoordinates(tuning, i, local);
        public float GuideProgress(int i) => tuning.sharedAbdomen ? Abdomen.Progress(i) : State.organs[i].cut;
        public Vector3 ConnectionPosition(int i, int c) { OperationGeometry.Cord(tuning, i, c, out var a, out var r); return Anchors.Point(i, (a + r) * 0.5f); }

        /// <summary>Where a held tool hangs for a cursor point: its tip just above the surface.</summary>
        public Pose HeldToolPose(OperationToolKind kind, Vector3 point, Vector3 normal, bool inSkin = false)
        {
            Vector3 flatBack = Vector3.ProjectOnPlane(-CameraPose.forward, transform.up).normalized;
            if (flatBack.sqrMagnitude < 0.0001f) flatBack = -transform.forward;
            Vector3 right = Vector3.Cross(transform.up, flatBack).normalized;
            Vector3 tip = point + normal * tuning.toolHover;
            if (kind == OperationToolKind.Scalpel || kind == OperationToolKind.Suture)
            {
                Vector3 toHandle = (transform.up * 0.8f + flatBack * 0.45f - right * 0.3f).normalized;
                return new Pose(tip, Basis(-toHandle, transform.up));
            }
            if (inSkin)
            {
                // Drawing blood / injecting (Fedya 2026-10-18): the needle tip in the skin, the barrel at ~30 deg to it,
                // leaning toward the shared camera so the plunger and the rising blood are in view.
                Vector3 along = Vector3.ProjectOnPlane(flatBack - right * 0.6f, normal);
                if (along.sqrMagnitude < 1e-6f) along = Vector3.ProjectOnPlane(-transform.forward, normal);
                along.Normalize();
                float a = tuning.syringeSkinAngle * Mathf.Deg2Rad;
                Vector3 barrel = (normal * Mathf.Sin(a) + along * Mathf.Cos(a)).normalized;
                return new Pose(point - normal * 0.004f, Basis(Vector3.Cross(barrel, along).normalized, barrel));
            }
            // Syringe in profile for the shared camera: needle at the cursor, plunger up and to the left.
            Vector3 up = (transform.up * 0.62f + flatBack * 0.15f - right * 0.62f).normalized;
            return new Pose(tip, Basis(Vector3.Cross(up, flatBack).normalized, up));
        }
        /// <summary>Rotation whose +X is x and whose +Y leans to upHint.</summary>
        public static Quaternion Basis(Vector3 x, Vector3 upHint)
        {
            x.Normalize();
            Vector3 z = Vector3.Cross(x, upHint);
            if (z.sqrMagnitude < 1e-6f) z = Vector3.Cross(x, Vector3.forward);
            z.Normalize();
            return Quaternion.LookRotation(z, Vector3.Cross(z, x));
        }
        private OperationTableView localView;
        public bool TryHeldPose(OperationTool tool, int holderId, out Pose pose)
        {
            pose = default;
            var view = localView != null ? localView : localView = GetComponent<OperationTableView>();
            if (view != null && view.LocalClientId == holderId && view.Active) return view.TryLocalHeldPose(tool.Kind, out pose);
            if (cursors.TryGetValue(holderId, out var c) && Time.time - c.at < 2f)
            {
                var v = View;
                bool inSkin = v != null && ((tool.Kind == OperationToolKind.BloodSyringe && v.drawing >= 0) || (tool.Kind == OperationToolKind.Syringe && v.injecting));
                pose = HeldToolPose(tool.Kind, transform.TransformPoint(c.smoothed), transform.up, inSkin);
                return true;
            }
            if (IsServerInitialized && participants.TryGetValue(holderId, out var p))
            { pose = HeldToolPose(tool.Kind, transform.TransformPoint(p.point), transform.up); return true; }
            return false;
        }
        public OperationTool ToolOf(ToolSlot slot)
        {
            foreach (var t in FindToolsCached()) if (t != null && t.Slot == slot) return t;
            return null;
        }
        private readonly List<OperationTool> clientTools = new();
        private float toolsFoundAt = -10f;
        public List<OperationTool> FindToolsCached()
        {
            if (IsServerInitialized) return tools;
            if (Time.unscaledTime - toolsFoundAt > 1f || clientTools.Exists(t => t == null))
            {
                toolsFoundAt = Time.unscaledTime; clientTools.Clear();
                foreach (var t in FindObjectsByType<OperationTool>()) if (t.Table == this) clientTools.Add(t);
            }
            return clientTools;
        }

        // ---------- lifecycle ----------
        private void Awake()
        {
            snapshot.OnChange += Changed;
            tableBody = GetComponent<Rigidbody>();
            if (GetComponent<OperationTableBrake>() == null) gameObject.AddComponent<OperationTableBrake>();
            if (tuning != null && tuning.sharedAbdomen)
            {
                Abdomen = gameObject.AddComponent<OperationAbdomen>(); Abdomen.Bind(this);
            }
        }
        private void OnDestroy() => snapshot.OnChange -= Changed;

        /// <summary>Stage A adapter, before Spawn: start empty, use the scene's patient registry, never load or write the
        /// dev operation save.</summary>
        public void ConfigureAdmission(PatientRegistry sceneRegistry)
        {
            admissionMode = true;
            loadSavedOperation = false;
            if (sceneRegistry != null) registry = sceneRegistry;
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (admissionMode)
            {
                world = new OperationWorldState { v02 = true, anesthesiaStock = tuning.anesthesiaStock, anesthesiaBarrel = tuning.syringeCapacity };
                SpawnTools();
                Publish();
                Debug.Log("[OPS] WORLD admission mode: empty table, waiting for a captured patient");
                return;
            }
            bool wantLoad = loadSavedOperation || HasArgument("-ops-load");
            bool load = wantLoad && ClinicSave.TryReadOperation(out world, out _);
            if (!load) world = FreshWorld();
            else MigrateLoaded(world);
            if (registry == null) registry = GetComponent<PatientRegistry>();
            StartWorld();
            Debug.Log($"[OPS] WORLD patient={world.patient.patientId} restored={load} outputs={items.Count} slot={ClinicSave.OperationFilePath}");
        }
        private OperationWorldState FreshWorld()
        {
            var w = new OperationWorldState
            {
                v02 = true,
                patient = OperationRules.Create(PatientLifecycle.NewId(), tuning),
                anesthesiaStock = tuning.anesthesiaStock,
                anesthesiaBarrel = tuning.syringeCapacity,
            };
            w.patient.knockedOut = true;
            Vector3 spawn = transform.TransformPoint(tuning.floorSpawn);
            if (Physics.Raycast(spawn + Vector3.up * 1.5f, Vector3.down, out var hit, 4f, ~0, QueryTriggerInteraction.Ignore) && hit.rigidbody == null)
                spawn.y = hit.point.y + 0.02f;
            w.patientPosition = spawn;
            // The KnockedOut clip lies prone along its root's X axis (head toward +X): yaw -90 lays him alongside the gurney,
            // head toward the head end.
            w.patientRotation = transform.rotation * Quaternion.Euler(0, -90, 0);
            return w;
        }
        private void MigrateLoaded(OperationWorldState w)
        {
            if (!w.v02)
            {
                w.v02 = true; w.anesthesiaStock = tuning.anesthesiaStock; w.anesthesiaBarrel = tuning.syringeCapacity; w.bloodFill = 0f;
                int bags = 0; foreach (var item in w.items) if (item.sealedBlood) bags++;
                w.bagsUsedMask = (1 << Mathf.Min(3, bags)) - 1; w.bloodBagged = bags;
            }
            if (w.patient.onTable && w.patient.aligned) w.patient.knockedOut = false;
        }
        private void StartWorld()
        {
            record = registry != null ? registry.EnsureOperationPatient(world.patient.patientId, world.patient) : null;
            rules = new OperationRules(record != null ? record.Operation : world.patient, tuning);
            rules.MigrateSharedOpening();
            world.patient = rules.State;
            rules.Cue += Hook;
            alignStartSet = false;
            falling = false; serverView.falling = false;
            SpawnPatient();
            SpawnTools();
            foreach (var item in world.items) SpawnItem(item, null);
            Publish();
        }
        private void SpawnTools()
        {
            if (tools.Count == 0)
            {
                foreach (var prefab in toolPrefabs)
                {
                    if (prefab == null) continue;
                    var tool = Instantiate(prefab, transform.position + Vector3.up, Quaternion.identity);
                    tool.name = prefab.name;
                    Spawn(tool.NetworkObject);
                    tool.ServerInit(this);
                    tools.Add(tool);
                }
            }
            else foreach (var tool in tools) if (tool != null) tool.ServerDock();
        }

        // ---------- stage A admission (map scene) ----------
        /// <summary>Server, admission mode: the captured NPC's own state becomes the patient (same identity, counters and
        /// organ grades). The patient object is spawned at the given pose (over the pad); the existing release-over-pad
        /// magnet snap then aligns him in FixedUpdate. Every patient gets a fresh table kit (stock, barrel, bags).</summary>
        public bool ServerAdmit(OperationState state, Vector3 position, Quaternion rotation)
        {
            if (!IsServerInitialized || !admissionMode || state == null || state.organs == null || state.organs.Length != 3 || patient != null) return false;
            state.onTable = false; state.aligned = false; state.knockedOut = true; state.escapeProgress = 0f;
            world.patient = state;
            world.patientPosition = position; world.patientRotation = rotation;
            world.anesthesiaStock = tuning.anesthesiaStock; world.anesthesiaBarrel = tuning.syringeCapacity; world.bloodFill = 0f; world.bagsUsedMask = 0;
            BindRules(state);
            alignStartSet = false; falling = false; serverView.falling = false; noAlignUntil = 0f;
            SpawnPatient();
            foreach (var tool in tools) if (tool != null) tool.ServerDock();
            Publish();
            Debug.Log($"[OPS] ADMIT patient={state.patientId} alive={state.alive} sleep={state.sleepRemaining:F1} residual={state.residual:F2} blood={state.bloodPortions} conditionLoss={state.conditionLoss} grades={state.organs[0].intrinsicGrade}/{state.organs[1].intrinsicGrade}/{state.organs[2].intrinsicGrade}");
            return true;
        }
        private void BindRules(OperationState state)
        {
            record = registry != null ? registry.EnsureOperationPatient(state.patientId, state) : null;
            rules = new OperationRules(record != null && record.Operation != null ? record.Operation : state, tuning);
            rules.MigrateSharedOpening();
            world.patient = rules.State;
            rules.Cue += Hook;
        }
        /// <summary>Server, admission mode: the patient (a resolved body) leaves the table for good. Returns his id.</summary>
        public string ServerRemovePatient(bool despawn = true)
        {
            if (!IsServerInitialized || !admissionMode || rules == null) return null;
            string id = rules.State.patientId;
            foreach (var p in participants.Values) ReleaseParticipant(p, true);
            participants.Clear();
            if (despawn && patient != null && patient.IsSpawned) Despawn(patient.NetworkObject);
            patient = null; patientObject.Value = null;
            rules.Cue -= Hook; rules = null; record = null;
            world.patient = null; alignStartSet = false; falling = false; serverView.falling = false;
            foreach (var tool in tools) if (tool != null) tool.ServerDock();
            Publish();
            Debug.Log($"[OPS] REMOVED patient={id}");
            return id;
        }
        public NetworkPhysicsBody ServerDetachCorpse()
        {
            if (!IsServerInitialized || !admissionMode || !HasPatient || State.alive) return null;
            foreach (bool closed in State.restraints) if (closed) return null;
            var body = patient;
            State.onTable = false; State.aligned = false; noAlignUntil = float.PositiveInfinity;
            rules.PatchIfOpen(); // round 4: the plain skin patch is state now (a scalpel stroke reopens it on the table)
            ApplyPatientPhysics();
            GetComponent<OperationPresentation>()?.ReleasePatientVisuals();
            Abdomen?.ReleasePatientVisuals();
            body.GetComponent<OperationPatientRagdoll>()?.ServerCorpse();
            ServerRemovePatient(false);
            return body;
        }

        /// <summary>Server, admission mode: restore a saved table (the patient on or by it, outputs, stock).</summary>
        public void ServerRestore(OperationWorldState saved)
        {
            if (!IsServerInitialized || !admissionMode || saved == null) return;
            ServerRemovePatient();
            foreach (var item in items) if (item != null && item.IsSpawned) Despawn(item.NetworkObject);
            items.Clear();
            world = saved;
            world.v02 = true;
            world.items ??= new List<OperationItemState>();
            if (world.hasTablePose && tableBody != null)
            {
                // The gurney first, then its patient and outputs (saved in world space) land on it, not beside it.
                tableBody.linearVelocity = Vector3.zero; tableBody.angularVelocity = Vector3.zero;
                tableBody.position = world.tablePosition; tableBody.rotation = world.tableRotation;
                transform.SetPositionAndRotation(world.tablePosition, world.tableRotation);
                Physics.SyncTransforms();
            }
            bool hasPatient = world.patient != null && !string.IsNullOrEmpty(world.patient.patientId) && world.patient.organs != null && world.patient.organs.Length == 3;
            if (hasPatient)
            {
                if (world.patient.onTable && world.patient.aligned) world.patient.knockedOut = false;
                BindRules(world.patient);
                alignStartSet = false; falling = false; serverView.falling = false;
                SpawnPatient();
            }
            else world.patient = null;
            foreach (var tool in tools) if (tool != null) tool.ServerDock();
            foreach (var item in world.items) SpawnItem(item, null)?.SuppressImpactsFor(2f); // settling after a load is no drop
            Publish();
            Debug.Log($"[OPS] RESTORED table patient={(hasPatient ? world.patient.patientId : "-")} outputs={items.Count}");
        }
        /// <summary>Server: the world as it is now (patient pose, outputs), for a save.</summary>
        public OperationWorldState SnapshotWorld()
        {
            if (world == null) return null;
            // A blood transfer is 1.2 s of animation: a save in the middle finishes it, or the portion would be lost (the
            // progress is not saved and a half-empty syringe cannot be poured again). Round-2 review item 2.
            if (IsServerInitialized && transferBag >= 0) TickTransfer(10f);
            world.patient = rules != null ? rules.State : null;
            world.hasTablePose = true; world.tablePosition = transform.position; world.tableRotation = transform.rotation;
            if (patient != null) { world.patientPosition = patient.transform.position; world.patientRotation = patient.transform.rotation; }
            world.items.Clear();
            foreach (var item in items) if (item != null && item.Data != null) world.items.Add(item.Data);
            return world;
        }
        private void SpawnPatient()
        {
            Vector3 position = world.patientPosition; Quaternion rotation = world.patientRotation;
            if (rules.State.onTable) { var rest = RestPose; position = rest.position; rotation = rest.rotation; }
            patient = Instantiate(patientPrefab, position, rotation);
            patient.name = "Patient " + rules.State.patientId;
            Spawn(patient.NetworkObject);
            patient.Body.mass = tuning.patientMass;
            patient.Body.constraints = RigidbodyConstraints.FreezeRotation;
            NetworkSession.Active?.RegisterBody(patient);
            patientObject.Value = patient.NetworkObject;
            var rig = patient.GetComponent<OperationPatientRig>();
            if (rig != null) rig.SetFloorPose(!rules.State.onTable); // KnockedOut lies along the root's X axis
            ApplyPatientPhysics();
            ServerPatientSpawned?.Invoke(patient);
        }
        public override void OnStartClient() { base.OnStartClient(); Changed("", snapshot.Value, false); }
        public override void OnStopServer()
        {
            Save();
            foreach (var p in participants.Values) ReleaseParticipant(p, true);
            participants.Clear();
            if (rules != null) rules.Cue -= Hook;
            base.OnStopServer();
        }

        // ---------- cues ----------
        private void Hook(PatientCue cue)
        {
            AnimationHook?.Invoke(cue);
            CueReceived?.Invoke(cue, ctxOrgan, ctxClient);
            ObserversCue(cue, ctxOrgan, ctxClient);
            if (cue == PatientCue.FailedEscapeFall) FallOffTable();
            if (cue == PatientCue.RanOff) RunOffTable();
            if (cue == PatientCue.Extracted || cue == PatientCue.Death || cue == PatientCue.IncisionOpened || cue == PatientCue.Reopened) nextSnapshot = 0f;
            Debug.Log($"[OPS] CUE {cue} organ={ctxOrgan} client={ctxClient} patient={State.patientId}");
        }
        [ObserversRpc(ExcludeServer = true)]
        private void ObserversCue(PatientCue cue, int organ, int client)
        {
            AnimationHook?.Invoke(cue);
            CueReceived?.Invoke(cue, organ, client);
        }
        [TargetRpc]
        private void TargetHint(NetworkConnection target, OpHint hint, int arg) => HintReceived?.Invoke(hint, arg);
        private void Hint(Participant p, OpHint hint, int arg = 0)
        {
            if (p.lastHint == hint && Time.time - p.hintAt < 0.8f) return;
            if (p.lastHint != hint) Debug.Log($"[OPS] HINT client={p.id} {hint} arg={arg}");
            p.lastHint = hint; p.hintAt = Time.time;
            var conn = p.player != null ? p.player.Owner : null;
            if (conn == null || !conn.IsActive) return;
            if (conn.IsLocalClient) HintReceived?.Invoke(hint, arg);
            else TargetHint(conn, hint, arg);
        }
        private void FallOffTable()
        {
            if (patient == null || fellFrame == Time.frameCount) return;
            fellFrame = Time.frameCount;
            var s = rules.State;
            s.onTable = false; s.aligned = false; s.knockedOut = true;
            alignStartSet = false;
            // The EscapeFall clip (Op_EscapeFall_Mirror_v01) carries the whole escape (sit up, swing the legs off the
            // patient's right side = the camera side, away from the stand, stumble, splat) relative to PatientRest, so the root stays there, kinematic, while the clip plays on every peer.
            // When it ends the root jumps under the landed body (Land) and the KnockedOut clip continues from there.
            falling = true; runOff = false;
            fallEndsAt = Time.time + tuning.EscapeFallDuration;
            ReleaseGrabs();
            var rest = RestPose;
            patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
            ApplyPatientPhysics();
            noAlignUntil = fallEndsAt + 1f;
            serverView.falling = true; nextSnapshot = 0f;
        }
        /// <summary>End of the escape clip: the root goes to the KnockedOut root under the landed hips (same yaw as
        /// PatientRest, on the floor) and the body turns dynamic at rest, so nothing slides or snaps.</summary>
        /// <summary>Round 4: end of the escape clips (PatientCue.RanOff): hold the last pose on PatientRest, kinematic, until
        /// the capture bridge discharges him (admission mode, at once); the dev scene lands him after a moment.</summary>
        private void RunOffTable()
        {
            if (patient == null) return;
            alignStartSet = false;
            falling = true; runOff = true;
            fallEndsAt = Time.time + (admissionMode ? 3f : 0.3f);
            ReleaseGrabs();
            var rest = RestPose;
            patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
            ApplyPatientPhysics();
            noAlignUntil = fallEndsAt + 1f;
            serverView.falling = true; nextSnapshot = 0f;
        }
        /// <summary>Round 4: where the field NPC takes over after HopRun (RUN0 / RUN0_L, on the floor) and his run direction.</summary>
        public Vector3 RunOffPoint(int side, out Vector3 forward)
        {
            forward = transform.rotation * (Quaternion.Euler(0f, OperationEscape.Run0Yaw(side), 0f) * Vector3.forward);
            return transform.TransformPoint(OperationEscape.Run0Local(side));
        }
        /// <summary>Round 4: the exit side away from the nearest player (his right = table-local -X).</summary>
        private void UpdateEscapeSide()
        {
            if (Time.time < nextSideAt || rules == null) return;
            nextSideAt = Time.time + 0.5f;
            float best = float.PositiveInfinity; Vector3 nearest = Vector3.zero; bool any = false;
            foreach (var player in FindObjectsByType<NetworkPlayer>(FindObjectsSortMode.None))
            {
                if (player == null) continue;
                // W86: the moving body (MotorPosition, as InReach), not the root: the capture map pawn's root stays where it
                // spawned, so the root picked the side toward the player once the left-exit clips (v01b) were imported.
                Vector3 at = player.MotorPosition;
                float d = (at - transform.position).sqrMagnitude;
                if (d < best) { best = d; nearest = at; any = true; }
            }
            if (!any && Camera.main != null) { nearest = Camera.main.transform.position; any = true; }
            if (!any) return;
            float x = transform.InverseTransformPoint(nearest).x;
            rules.PreferredEscapeSide = x < 0f ? -1 : 1;
        }
        private void Land()
        {
            falling = false; runOff = false; serverView.falling = false; nextSnapshot = 0f;
            if (patient == null) return;
            var rest = RestPose;
            Vector3 p = rest.position + rest.rotation * tuning.escapeLandingOffset;
            float floorY = transform.position.y;
            foreach (var hit in Physics.RaycastAll(p + transform.up * 1.2f, -transform.up, 2.5f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (hit.rigidbody != null || hit.collider.transform.IsChildOf(patient.transform)) continue;
                if (hit.point.y > floorY - 0.6f && hit.point.y < floorY + 0.3f) { floorY = hit.point.y; break; }
            }
            p.y = floorY + 0.003f;
            patient.transform.SetPositionAndRotation(p, rest.rotation);
            var rig = patient.GetComponent<OperationPatientRig>();
            if (rig != null) rig.SetFloorPose(true); // before the body turns dynamic: the box must lie along the landed pose
            ApplyPatientPhysics();
            patient.Body.linearVelocity = Vector3.zero; patient.Body.angularVelocity = Vector3.zero;
            noAlignUntil = Time.time + 1f;
            string overlaps = "";
            if (patient.TryGetComponent(out BoxCollider box))
                foreach (var c in Physics.OverlapBox(patient.transform.TransformPoint(box.center), box.size * 0.5f, patient.transform.rotation, ~0, QueryTriggerInteraction.Ignore))
                    if (!c.transform.IsChildOf(patient.transform)) overlaps += " " + c.name;
            Debug.Log($"[OPS] LANDED patient={State.patientId} at table-local {transform.InverseTransformPoint(p)} overlaps:{(overlaps.Length > 0 ? overlaps : " none")}");
        }
        private float RestLocalZ() => transform.InverseTransformPoint(RestPose.position).z;

        private void Changed(string previous, string next, bool asServer)
        {
            if (asServer || string.IsNullOrEmpty(next)) return;
            mirror = JsonUtility.FromJson<OperationView>(next);
            // JsonUtility writes a missing patient (admission mode, empty table) as an empty object.
            if (mirror != null && mirror.patient != null && string.IsNullOrEmpty(mirror.patient.patientId)) mirror.patient = null;
        }
        private void Publish()
        {
            serverView.patient = State; serverView.stock = world.anesthesiaStock; serverView.barrel = world.anesthesiaBarrel;
            serverView.blood = world.bloodFill; serverView.bagsUsedMask = world.bagsUsedMask;
            if (bagFills.Length != tuning.bloodBagCount) bagFills = new float[tuning.bloodBagCount];
            serverView.bagFill = bagFills;
            snapshot.Value = JsonUtility.ToJson(serverView);
            nextSnapshot = Time.time + tuning.snapshotInterval;
        }
        public void Save()
        {
            if (world == null || !IsServerInitialized) return;
            // Stage A: the capture save (Capture/CaptureSave) snapshots the table itself; the dev operation file is never touched.
            if (admissionMode) { SnapshotWorld(); nextSave = Time.time + tuning.saveInterval; return; }
            if (rules == null) return;
            SnapshotWorld();
            ClinicSave.WriteOperation(world, out _); nextSave = Time.time + tuning.saveInterval;
        }

        // ---------- participants ----------
        private NetworkPlayer PlayerFor(NetworkConnection connection)
        {
            if (connection == null || !connection.IsActive) return null;
            foreach (var obj in connection.Objects)
                if (obj != null && obj.TryGetComponent(out NetworkPlayer player)) return player;
            return null;
        }
        private bool InReach(NetworkPlayer player) => player != null && Vector3.Distance(player.MotorPosition, transform.position) <= tuning.tableReach;
        private bool Valid(NetworkConnection sender, out Participant p)
        {
            p = null;
            return sender != null && sender.IsActive && participants.TryGetValue(sender.ClientId, out p) && InReach(p.player);
        }
        public bool IsParticipant(int clientId) => participants.ContainsKey(clientId);
        /// <summary>The same rule as OperationRules.CanOperate (nobody holds the patient in stage 1), for client hints.</summary>
        public bool ServerOrLocalCanOperate(OperationState s) => s != null && s.onTable && s.aligned && (!s.alive || s.Sleeping || OperationStraps.Held(s, tuning));
        public OperationTool ParticipantTool(int clientId) => participants.TryGetValue(clientId, out var p) ? p.tool : null;

        [ServerRpc(RequireOwnership = false)]
        public void RequestJoin(bool join, NetworkConnection sender = null)
        {
            var player = PlayerFor(sender);
            if (player == null) return;
            if (!join)
            {
                if (participants.Remove(sender.ClientId, out var old)) ReleaseParticipant(old, false);
                return;
            }
            if (!InReach(player) || participants.ContainsKey(sender.ClientId)) return;
            var inventory = player.GetComponent<NetworkInventory>();
            if (inventory == null) { Debug.LogError("[OPS] player prefab requires NetworkInventory", player); return; }
            participants.Add(sender.ClientId, new Participant { id = sender.ClientId, player = player, inventory = inventory, received = Time.time, prepSince = Time.time, point = transform.InverseTransformPoint(RestPose.position) });
            Debug.Log($"[OPS] JOIN client={sender.ClientId} count={participants.Count}");
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestCameraMode(TableCamera mode, NetworkConnection sender = null)
        {
            if (!Valid(sender, out var p) || (mode != TableCamera.Prep && mode != TableCamera.Operation)) return;
            if (mode == TableCamera.Prep && p.cameraMode != TableCamera.Prep) p.prepSince = Time.time;
            p.cameraMode = mode;
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestSelect(ToolSlot slot, NetworkConnection sender = null)
        {
            if (!Valid(sender, out var p)) return;
            if (slot == ToolSlot.Hands) DockTool(p);
            else RequestSelectServer(p, slot);
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestReturn(NetworkConnection sender = null)
        {
            if (!Valid(sender, out var p)) return;
            if (p.inventory.PhysicalItem != null) { PlaceOnTray(p, -1); return; }
            DockTool(p);
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestClick(int targetCode, Vector3 local, NetworkObject item, NetworkConnection sender = null)
        {
            if (!Valid(sender, out var p) || !OperationGeometry.InWorkVolume(local)) return;
            var target = OpTarget.FromCode(targetCode);
            ctxClient = p.id;
            try
            {
                switch (target.kind)
                {
                    case TargetKind.Strap:
                        // PREP only, and not in the same instant the client claims it switched (a real switch blends the
                        // camera first): a client cannot unbuckle from OPERATION by sending "PREP + click" together.
                        if (target.index >= 5 || p.cameraMode != TableCamera.Prep || Time.time - p.prepSince < PrepClickDelay) return;
                        // The exact strap triangles also exist on a server without presentation (headless/dedicated).
                        var straps = OperationStrapTargets.Install(this);
                        if (straps == null || !straps.Contains(target.index, transform.TransformPoint(local))) return;
                        if (!State.onTable || !State.aligned) { Hint(p, OpHint.NotOnTable); return; }
                        if (State.restraints[target.index] && rules.MustSutureBeforeRelease) { Hint(p, OpHint.SutureFirst); return; }
                        rules.ToggleRestraint(target.index);
                        Publish();
                        break;
                    case TargetKind.Tool:
                        RequestSelectServer(p, (ToolSlot)Mathf.Clamp(target.index, 1, (int)ToolSlot.Suture));
                        break;
                    case TargetKind.BloodBag:
                        FillBag(p, target.index);
                        break;
                    case TargetKind.Tray:
                        if (p.inventory.PhysicalItem != null) PlaceOnTray(p, target.index - 1);
                        break;
                    case TargetKind.Item:
                        PickItem(p, item);
                        break;
                }
            }
            finally { ctxClient = -1; }
        }
        private void RequestSelectServer(Participant p, ToolSlot slot)
        {
            OperationTool wanted = null;
            foreach (var t in tools) if (t != null && t.Slot == slot) wanted = t;
            if (wanted == null || wanted == p.tool) return;
            if (wanted.Holder >= 0 && wanted.Holder != p.id) { Hint(p, OpHint.ToolBusy, wanted.Holder); return; }
            if (p.inventory.PhysicalItem != null) PlaceOnTray(p, -1);
            DockTool(p);
            p.tool = wanted; wanted.ServerTake(p.id);
            p.pressed = false; p.strokeOrgan = -1; p.pullOrgan = -1;
            Debug.Log($"[OPS] TOOL client={p.id} takes {slot}");
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestPointer(uint sequence, uint pressId, bool pressed, int pressTarget, int target, Vector3 local, float pull, NetworkConnection sender = null)
        {
            if (!Valid(sender, out var p) || sequence <= p.sequence || !OperationGeometry.InWorkVolume(local) || !OperationRules.Finite(pull)) return;
            p.sequence = sequence; p.received = Time.time;
            p.point = local;
            p.target = OpTarget.FromCode(target);
            p.pullTarget = Mathf.Clamp(pull, -tuning.pullDistance, tuning.pullDistance * 1.5f);
            if (pressed && pressId != p.pressId)
            {
                p.pressId = pressId; p.pressStart = true; p.pressTarget = OpTarget.FromCode(pressTarget);
                p.strokeOrgan = -1; p.strokeRejected = false; p.directDone = false; p.lastPoint = local;
                TryDirectCut(p, local);
            }
            if (!pressed) { p.pullOrgan = -1; p.strokeOrgan = -1; }
            p.pressed = pressed;
            byte flags = (byte)((pressed ? 1 : 0) | (p.target.IsNone ? 0 : 2));
            ObserversCursor(p.id, local, flags, (byte)(p.tool != null ? p.tool.Slot : ToolSlot.Hands));
        }

        [ObserversRpc]
        private void ObserversCursor(int id, Vector3 local, byte flags, byte slot, Channel channel = Channel.Unreliable)
        {
            if (!cursors.TryGetValue(id, out var c)) cursors[id] = c = new RemoteCursor { smoothed = local };
            c.local = local; c.pressed = (flags & 1) != 0; c.slot = (ToolSlot)slot; c.at = Time.time;
        }

        [ServerRpc(RequireOwnership = false)]
        public void RequestDev(byte command, NetworkConnection sender = null)
        {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (admissionMode) return; // stage A: F9/F10 belong to the map (pins, body mode); patients come from capture
            var player = PlayerFor(sender);
            if (player == null) return;
            if (command == 9) DevPlaceOnTable();
            else if (command == 10) ResetOperation();
#endif
        }

        /// <summary>Dev F9: the patient lies on the table at once.</summary>
        public void DevPlaceOnTable()
        {
            if (!IsServerInitialized || patient == null) return;
            if (State.onTable && State.aligned) return;
            ReleaseGrabs();
            rules.ForcePlace();
            var rest = RestPose; patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
            ApplyPatientPhysics();
            if (record != null && record.Stage < PatientStage.AtBase) registry.Move(record, PatientStage.AtBase);
            Publish();
        }

        /// <summary>Dev F10: a fresh patient on the floor, tools back in the tray, fresh bags and stock.</summary>
        public void ResetOperation()
        {
            if (!IsServerInitialized) return;
            Save();
            foreach (var p in participants.Values)
            {
                if (p.inventory != null && p.inventory.PhysicalItem != null) p.inventory.ServerReleasePhysical(p.inventory.PhysicalItem.transform.position, Vector3.zero);
                p.tool = null; p.pressed = false; p.pullOrgan = -1; p.strokeOrgan = -1;
            }
            foreach (var item in items) if (item != null && item.IsSpawned) Despawn(item.NetworkObject);
            items.Clear();
            if (patient != null && patient.IsSpawned) Despawn(patient.NetworkObject);
            patient = null;
            if (rules != null) rules.Cue -= Hook;
            Array.Clear(yankLatched, 0, 3);
            world = FreshWorld();
            StartWorld();
            foreach (var tool in tools) if (tool != null) tool.ServerDock();
            Debug.Log($"[OPS] RESET new patient={world.patient.patientId}");
            Save();
        }

        private void DockTool(Participant p)
        {
            if (p.tool == null) return;
            var tool = p.tool; p.tool = null;
            tool.ServerDock();
            if (tool.Kind == OperationToolKind.Syringe) Refill(p);
        }
        private void Refill(Participant p)
        {
            float missing = tuning.syringeCapacity - world.anesthesiaBarrel;
            if (missing <= 0.001f) return;
            float add = Mathf.Min(missing, world.anesthesiaStock);
            if (add <= 0f) { if (p != null) Hint(p, OpHint.StockEmpty); return; }
            world.anesthesiaStock -= add; world.anesthesiaBarrel += add;
            if (p != null) Hint(p, OpHint.Refilled);
        }
        private void ReleaseParticipant(Participant p, bool stopping)
        {
            if (p.tool != null)
            {
                var tool = p.tool; p.tool = null;
                if (stopping) tool.ServerDock();
                else { tool.ServerHoldAt(HeldToolPose(tool.Kind, transform.TransformPoint(p.point), transform.up)); tool.ServerDrop(); }
            }
            if (p.inventory != null && p.inventory.PhysicalItem != null && p.inventory.PhysicalItem.TryGetComponent(out OperationPhysicalItem held))
                held.LeaveTable();
            p.pressed = false; p.pullOrgan = -1;
            cursors.Remove(p.id);
            if (State != null) Debug.Log($"[OPS] LEAVE client={p.id} preserved cuts={State.organs[0].cut:F2}/{State.organs[1].cut:F2}/{State.organs[2].cut:F2} extracted={State.extracted} outputs={items.Count}");
        }

        // ---------- items ----------
        private bool SlotFree(Pose slot)
        {
            foreach (var item in items)
                if (item != null && item.Holder == null && Vector3.Distance(item.transform.position, slot.position) < 0.07f) return false;
            return true;
        }
        private void PlaceOnTray(Participant p, int preferred)
        {
            var held = p.inventory.PhysicalItem;
            if (held == null) return;
            Pose pose = default; bool found = false;
            if (preferred >= 0 && preferred < 3 && SlotFree(OrganSlotPose(preferred))) { pose = OrganSlotPose(preferred); found = true; }
            for (int i = 0; i < 3 && !found; i++) if (SlotFree(OrganSlotPose(i))) { pose = OrganSlotPose(i); found = true; }
            if (!found) pose = OrganSlotPose(1);
            if (held.TryGetComponent(out OperationPhysicalItem op)) op.LeaveTable();
            held.transform.rotation = pose.rotation;
            p.inventory.ServerReleasePhysical(pose.position + pose.up * 0.05f, Vector3.zero);
        }
        private void PickItem(Participant p, NetworkObject target)
        {
            if (target == null || !target.IsSpawned || !target.TryGetComponent(out OperationPhysicalItem item) || !items.Contains(item) ||
                item.Holder != null || Vector3.Distance(item.transform.position, transform.position) > 2.5f) return;
            if (p.inventory.PhysicalItem != null) return;
            DockTool(p);
            p.inventory.ServerHoldPhysical(item.World);
        }
        private void FillBag(Participant p, int bag)
        {
            if (bag < 0 || bag >= tuning.bloodBagCount) return;
            if (p.tool == null || p.tool.Kind != OperationToolKind.BloodSyringe) { Hint(p, OpHint.SyringeNotFull); return; }
            if (world.bloodFill < 1f) { Hint(p, OpHint.SyringeNotFull); return; }
            if ((world.bagsUsedMask & (1 << bag)) != 0) { Hint(p, OpHint.NoBags); return; }
            if (transferBag >= 0) return; // one syringe, one transfer at a time
            transferBag = bag; transferClient = p.id; transferProgress = 0f;
            Debug.Log($"[OPS] BLOOD TRANSFER start bag={bag} client={p.id}");
        }
        /// <summary>The plunger goes down: the syringe empties and the bag fills by the same amount; then it is sealed.</summary>
        private void TickTransfer(float dt)
        {
            if (transferBag < 0) return;
            if (bagFills.Length != tuning.bloodBagCount) bagFills = new float[tuning.bloodBagCount];
            transferProgress = Mathf.Min(1f, transferProgress + dt / Mathf.Max(0.05f, tuning.bloodTransferSeconds));
            if (transferClient == FieldClient) fieldFill?.Invoke(1f - transferProgress);
            else world.bloodFill = 1f - transferProgress;
            bagFills[transferBag] = transferProgress / Mathf.Max(1, tuning.bloodPortionsPerBag);
            if (Time.time >= nextSnapshot - tuning.snapshotInterval * 0.5f) Publish();
            if (transferProgress < 1f) return;
            int bag = transferBag; transferBag = -1;
            bool field = transferClient == FieldClient; fieldFill = null;
            participants.TryGetValue(transferClient, out var p);
            CompleteBag(p, bag, field);
        }
        private void CompleteBag(Participant p, int bag, bool field = false)
        {
            world.bagsUsedMask |= 1 << bag; if (!field) world.bloodFill = 0f; world.bloodBagged++;
            if (bag < bagFills.Length) bagFills[bag] = 0f;
            var pose = BagPose(bag);
            var data = new OperationItemState { id = (field ? "field" : State != null ? State.patientId : "blood") + "/blood/" + world.bloodBagged, kind = 2, grade = 0, sealedBlood = true, position = pose.position + pose.up * 0.04f, rotation = pose.rotation };
            SpawnItem(data, null);
            if (p != null) Hint(p, OpHint.BagReady);
            int client = p != null ? p.id : transferClient;
            ObserversCue(PatientCue.BagSealed, bag, client);
            CueReceived?.Invoke(PatientCue.BagSealed, bag, client);
            Debug.Log($"[OPS] BAG id={data.id} bag={bag} value={tuning.bloodValue}");
            Publish(); Save();
        }
        private OperationPhysicalItem SpawnItem(OperationItemState data, Participant holder)
        {
            foreach (var existing in items) if (existing != null && existing.Identity == data.id) return existing;
            int prefab = data.kind >= 2 ? 2 : data.kind;
            var item = Instantiate(merchandisePrefabs[prefab], data.position, data.rotation);
            item.Initialize(data, tuning, merchandiseDefinitions[prefab]);
            Spawn(item.NetworkObject);
            NetworkSession.Active?.RegisterBody(item.GetComponent<NetworkPhysicsBody>());
            items.Add(item);
            if (holder != null) { DockTool(holder); holder.inventory.ServerHoldPhysical(item.World); }
            return item;
        }

        // ---------- simulation ----------
        private void ReleaseGrabs()
        {
            // The physical grab cannot hold a kinematic body; the holders' next packets are simply ignored.
            if (patient != null && patient.Body != null) { patient.Body.linearVelocity = Vector3.zero; }
        }
        private void ApplyPatientPhysics()
        {
            if (patient == null) return;
            bool kinematic = rules.State.onTable || falling;
            var ragdoll = patient.GetComponent<OperationPatientRagdoll>();
            if (ragdoll != null) ragdoll.ServerTableState(kinematic);
            if (!kinematic) { patient.Body.position = patient.transform.position; patient.Body.rotation = patient.transform.rotation; }
            patient.Body.isKinematic = kinematic; patient.Body.useGravity = !kinematic;
            var rig = patient.GetComponent<OperationPatientRig>();
            if (rig != null) rig.SetPhysicsCollider(!kinematic);
        }
        private void FixedUpdate()
        {
            // A field-syringe transfer runs with or without a patient on the table.
            if (IsServerInitialized && transferBag >= 0 && transferClient == FieldClient) TickTransfer(Time.fixedDeltaTime);
            if (!IsServerInitialized || rules == null) return;
            float dt = Time.fixedDeltaTime;
            removedParticipants.Clear();
            foreach (var pair in participants)
                if (pair.Value.player == null || pair.Value.player.Owner == null || !pair.Value.player.Owner.IsActive || !InReach(pair.Value.player)) removedParticipants.Add(pair.Key);
            foreach (int id in removedParticipants) { ReleaseParticipant(participants[id], false); participants.Remove(id); }

            // v04: brakes on while someone carries the patient near the gurney too (the dangling ragdoll would shove it).
            bool loading = patient != null && patient.HasHolder && !rules.State.onTable &&
                Vector3.Distance(patient.transform.position, transform.position) < tuning.tableReach;
            // Any other body carried near it (a captured NPC on the map grab, a corpse or body bag): brakes on too, so a
            // body hauled onto the pad never shoves the gurney away (Claude rework; thrown/loose bodies still nudge it).
            if (!loading && OperationTableBrake.CarryingNear != null) loading = OperationTableBrake.CarryingNear(transform.position, tuning.tableReach);
            bool freeze = participants.Count > 0 || loading;
            if (tableBody != null && freeze != frozen)
            {
                frozen = freeze;
                if (freeze) { tableBody.linearVelocity = Vector3.zero; tableBody.angularVelocity = Vector3.zero; }
                tableBody.isKinematic = freeze;
            }

            var s = rules.State;
            if (patient != null && !s.onTable && !falling && !patient.HasHolder && Time.time >= noAlignUntil)
            {
                Vector3 local = transform.InverseTransformPoint(patient.transform.position + transform.up * 0.1f);
                // Retain the approved release-over-pad check. A settled ragdoll can also arrive with its handle
                // beside the pad while its actual body rests on it.
                Vector3 alignmentPoint = patient.transform.position;
                var ragdoll = patient.GetComponent<OperationPatientRagdoll>();
                if (!OperationGeometry.OverPad(local, tuning) && ragdoll != null && ragdoll.Active)
                { alignmentPoint = ragdoll.PlacementPoint; local = transform.InverseTransformPoint(alignmentPoint); }
                if (OperationGeometry.OverPad(local, tuning) && patient.Body.linearVelocity.magnitude < 4f &&
                    rules.BeginAlignment(Vector3.Distance(alignmentPoint, RestPose.position)))
                {
                    // v04: the ragdoll hands the body back first (it re-seats the root under the lying body), then the
                    // slide starts from there.
                    ApplyPatientPhysics();
                    alignFromLocal = transform.InverseTransformPoint(patient.transform.position);
                    alignFromRotation = Quaternion.Inverse(transform.rotation) * patient.transform.rotation;
                    alignStartSet = true;
                    if (record != null && record.Stage < PatientStage.AtBase) registry.Move(record, PatientStage.AtBase);
                }
            }

            float dose = 0f; serverView.injecting = false; serverView.drawing = -1;
            Array.Clear(pullSums, 0, 3); Array.Clear(pullHolders, 0, 3); Array.Clear(outputHolders, 0, 3);
            foreach (var p in participants.Values)
            {
                bool fresh = Time.time - p.received <= tuning.inputTimeout;
                if (!fresh) { p.pressed = false; p.pullOrgan = -1; p.strokeOrgan = -1; }
                Vector3 world = transform.TransformPoint(p.point);
                if (p.inventory.PhysicalItem != null && p.inventory.PhysicalItem.TryGetComponent(out OperationPhysicalItem heldItem))
                    heldItem.SetTableTarget(world + transform.up * 0.1f);
                if (p.tool != null)
                {
                    bool inSkin = p.pressed && ((p.tool.Kind == OperationToolKind.BloodSyringe && p.pressTarget.ArmSide >= 0) ||
                                                (p.tool.Kind == OperationToolKind.Syringe && p.pressTarget.IsInjectionSite));
                    p.tool.ServerHoldAt(HeldToolPose(p.tool.Kind, world, transform.up, inSkin));
                }
                if (!p.pressed) { p.pressStart = false; continue; }
                var slot = p.tool != null ? p.tool.Slot : ToolSlot.Hands;
                ctxClient = p.id;
                switch (slot)
                {
                    case ToolSlot.Anesthesia: dose += Inject(p, dt); break;
                    case ToolSlot.Blood: DrawBlood(p, dt); break;
                }
                ctxClient = -1;
            }
            dose += fieldDose; fieldDose = 0f; // round 3: the field syringe of a player by the table
            UpdateEscapeSide();
            rules.Tick(dt, dose, false);

            // Patient pose: slide onto the rest pose, then follow the (possibly moving) gurney.
            if (patient != null && s.onTable)
            {
                var rest = RestPose;
                if (!s.aligned && alignStartSet)
                {
                    float t = 1f - Mathf.Clamp01(s.alignment / Mathf.Max(0.01f, tuning.alignmentSeconds));
                    t = t * t * (3f - 2f * t);
                    Vector3 from = transform.TransformPoint(alignFromLocal);
                    Quaternion fromRot = transform.rotation * alignFromRotation;
                    patient.transform.SetPositionAndRotation(Vector3.Lerp(from, rest.position, t) + transform.up * Mathf.Sin(t * Mathf.PI) * 0.08f,
                        Quaternion.Slerp(fromRot, rest.rotation, t));
                }
                else patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
                if (falling) { falling = false; serverView.falling = false; }
                if (!patient.Body.isKinematic) ApplyPatientPhysics();
            }
            else if (patient != null && falling)
            {
                var rest = RestPose;
                patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
                if (Time.time >= fallEndsAt) Land();
            }
            else if (patient != null && patient.Body.isKinematic) ApplyPatientPhysics();

            if (AnatomyReady)
            {
                foreach (var p in participants.Values)
                {
                    if (!p.pressed) continue;
                    ctxClient = p.id;
                    var slot = p.tool != null ? p.tool.Slot : ToolSlot.Hands;
                    if (slot == ToolSlot.Suture) SutureStroke(p, dt);
                    else if (slot == ToolSlot.Scalpel) Scalpel(p, dt);
                    else if (slot == ToolSlot.Hands) Hands(p);
                    p.pressStart = false;
                    ctxClient = -1;
                }
            }
            for (int i = 0; i < 3; i++)
            {
                serverView.pullers[i] = pullHolders[i];
                ctxOrgan = i;
                bool canPull = rules.CanOperate(false);
                if (rules.Pull(i, pullHolders[i] > 0 && canPull ? pullSums[i] / pullHolders[i] : 0, canPull ? pullHolders[i] : 0, dt, ref yankLatched[i]))
                    Detach(i, outputHolders[i]);
                ctxOrgan = -1;
            }
            foreach (var p in participants.Values) p.pressStart = false;
            foreach (var tool in tools) if (tool != null) tool.ServerTick(dt);
            var anesthesia = tools.Find(t => t != null && t.Kind == OperationToolKind.Syringe);
            if (anesthesia != null) anesthesia.ServerSetFill(world.anesthesiaBarrel / Mathf.Max(0.01f, tuning.syringeCapacity));
            if (transferClient != FieldClient) TickTransfer(dt);
            var bloodTool = tools.Find(t => t != null && t.Kind == OperationToolKind.BloodSyringe);
            if (bloodTool != null) bloodTool.ServerSetFill(world.bloodFill);
            if (Time.time >= nextSnapshot) Publish();
            if (Time.time >= nextSave) Save();
        }

        private float Inject(Participant p, float dt)
        {
            if (!p.pressTarget.IsInjectionSite) { if (p.pressStart && p.pressTarget.kind == TargetKind.Body) Hint(p, OpHint.WrongSpot); return 0f; }
            if (!State.alive) { Hint(p, OpHint.PatientDead); return 0f; }
            if (!rules.CanInject) { Hint(p, OpHint.NotOnTable); return 0f; }
            if (!ValidBodyPoint(p.pressTarget.Part, p.point)) return 0f;
            if (world.anesthesiaBarrel <= 0.0001f) { Hint(p, OpHint.SyringeEmpty); return 0f; }
            float amount = Mathf.Min(world.anesthesiaBarrel, tuning.dosePerSecond * dt);
            world.anesthesiaBarrel -= amount;
            serverView.injecting = true;
            return amount;
        }
        private void DrawBlood(Participant p, float dt)
        {
            int arm = p.pressTarget.ArmSide;
            if (arm < 0) { if (p.pressStart && p.pressTarget.kind == TargetKind.Body) Hint(p, OpHint.WrongSpot); return; }
            if (!State.onTable || !State.aligned) { Hint(p, OpHint.NotOnTable); return; }
            if (world.bloodFill >= 1f) { Hint(p, OpHint.SyringeFull); return; }
            if (State.bloodPortions >= tuning.fatalPortion) { Hint(p, OpHint.NoBloodLeft); return; }
            if (!rules.CanDrawBlood(arm)) { Hint(p, OpHint.Squirming); return; }
            if (!ValidBodyPoint(p.pressTarget.Part, p.point)) return;
            serverView.drawing = arm;
            rules.FillBlood(ref world.bloodFill, dt);
        }
        private bool ValidBodyPoint(BodyPart part, Vector3 local)
        {
            var rig = PatientRig;
            if (rig == null) return true;
            return rig.DistanceToPart(part, transform.TransformPoint(local)) <= 0.12f;
        }
        private void Scalpel(Participant p, float dt)
        {
            var t = p.pressTarget;
            if (t.kind == TargetKind.Incision && tuning.sharedAbdomen)
            { if (Abdomen.IsGuide(t.index)) SharedStroke(p, t.index, dt); return; }
            if (t.kind == TargetKind.Incision && t.index < 3) { Stroke(p, t.index, dt); return; }
            if (t.kind == TargetKind.Cord && t.index < 3)
            {
                int i = t.index, c = t.sub;
                var organ = State.organs[i];
                if (organ.removed || !organ.Opened || c >= organ.connections.Length) return;
                OperationGeometry.Cord(tuning, i, c, out var a, out var r);
                Vector3 local = SiteLocal(i, transform.TransformPoint(p.point));
                bool onCord = OperationGeometry.DistanceToSegment(local, a, r) <= tuning.cordHitRadius || (p.target.kind == TargetKind.Cord && p.target.index == i && p.target.sub == c);
                if (!onCord) return;
                if (!rules.CanOperate(false)) { Hint(p, OpHint.Squirming); return; }
                ctxOrgan = i; rules.SnipCord(i, c, dt); ctxOrgan = -1;
                return;
            }
            if (t.kind == TargetKind.Body && p.pressStart) Hint(p, OpHint.StartAtDot);
        }
        /// <summary>A deliberate scalpel press that starts ON the organ body (event, handled when the press arrives so a
        /// quick click is never lost between physics ticks). Never from a drag, never next to a living cord.</summary>
        private void TryDirectCut(Participant p, Vector3 pointLocal)
        {
            var t = p.pressTarget;
            if (p.tool == null || p.tool.Kind != OperationToolKind.Scalpel || t.kind != TargetKind.Organ || t.index >= 3 || p.directDone || !AnatomyReady) return;
            int i = t.index; var organ = State.organs[i];
            p.directDone = true;
            if (organ.removed || !organ.Opened) return;
            Vector3 local = SiteLocal(i, transform.TransformPoint(pointLocal));
            if (new Vector2(local.x, local.y).magnitude > tuning.organHitRadius || Mathf.Abs(local.z) > 0.08f) return;
            for (int c = 0; c < organ.connections.Length; c++)
            {
                if (organ.connections[c] >= 1f) continue;
                OperationGeometry.Cord(tuning, i, c, out var a, out var r);
                if (OperationGeometry.DistanceToSegment(local, a, r) <= tuning.cordHitRadius * 0.25f) return;
            }
            if (!rules.CanOperate(false)) { Hint(p, OpHint.Squirming); return; }
            ctxOrgan = i; ctxClient = p.id; rules.DirectCut(i); ctxOrgan = -1; ctxClient = -1;
            Debug.Log($"[OPS] DIRECT CUT organ={i} client={p.id} damage={organ.damage}");
            Publish();
        }
        private void Stroke(Participant p, int i, float dt)
        {
            var organ = State.organs[i];
            if (organ.removed || organ.Opened || p.strokeRejected) return;
            Vector3 local = SiteLocal(i, transform.TransformPoint(p.point));
            if (Mathf.Abs(local.z) > tuning.incisionSurfaceTolerance) return;
            Vector2 g = OperationGeometry.GuideCoordinates(tuning, i, local);
            if (p.strokeOrgan != i)
            {
                if (!rules.CanBeginCut(i, g.x, g.y)) { p.strokeRejected = true; Hint(p, OpHint.StartAtDot, i); return; }
                if (!rules.CanOperate(false)) { p.strokeRejected = true; Hint(p, OpHint.Squirming); return; }
                p.strokeOrgan = i;
                p.lastPoint = p.point;
            }
            if (!rules.CanOperate(false)) { Hint(p, OpHint.Squirming); return; }
            ctxOrgan = i;
            var step = rules.CutTowards(i, g.x, g.y, dt);
            if (step == CutStep.OffLine)
            {
                float travel = Vector3.Distance(p.point, p.lastPoint) / tuning.IncisionLength(i);
                rules.AddOffLine(i, travel);
            }
            ctxOrgan = -1;
            p.lastPoint = p.point;
        }
        private void SharedStroke(Participant p, int guide, float dt)
        {
            if (p.strokeRejected || !AnatomyReady) return;
            if (!rules.CanOperate(false)) { if (p.pressStart) Hint(p, OpHint.Squirming); return; }
            Vector3 local = SiteLocal(guide, transform.TransformPoint(p.point));
            if (Mathf.Abs(local.z) > tuning.incisionSurfaceTolerance) return;
            Vector2 g = GuideCoordinates(guide, local);
            if (p.strokeOrgan != guide)
            {
                if (!rules.CanBeginSharedGuide(guide, g.x, g.y))
                {
                    p.strokeRejected = true; Hint(p, OpHint.StartAtDot, guide);
                    Debug.Log($"[OPS] STROKE refused guide={guide} along={g.x:F3} offset={g.y:F3} z={local.z:F3} progress={rules.GuideProgress(guide):F2}");
                    return;
                }
                p.strokeOrgan = guide; p.lastPoint = p.point;
            }
            float travel = Vector3.Distance(p.point, p.lastPoint) / OperationAbdomenGeometry.GuideLength(tuning, guide);
            ctxOrgan = guide == OperationAbdomenGeometry.ZoneGuide ? -1 : guide;
            rules.CutSharedGuide(guide, g.x, g.y, dt, travel);
            ctxOrgan = -1; p.lastPoint = p.point;
        }
        private const int SutureStrokeId = 103;
        /// <summary>Round 3: the needle holder sews the incision up, stroke by stroke along the same line as the cut, from the
        /// top end. Server-authoritative: the rules advance the seam (OperationRules.Suture); the state travels in the view.</summary>
        private void SutureStroke(Participant p, float dt)
        {
            if (p.strokeRejected || !AnatomyReady) return;
            var s = State;
            if (!s.zoneOpened || s.sutured || s.skinPatched) { if (p.pressStart) Hint(p, OpHint.NothingToSuture); return; }
            if (!rules.CanOperate(false)) { if (p.pressStart) Hint(p, OpHint.Squirming); return; }
            int guide = OperationAbdomenGeometry.ZoneGuide;
            Vector3 local = SiteLocal(guide, transform.TransformPoint(p.point));
            if (Mathf.Abs(local.z) > tuning.incisionSurfaceTolerance) return;
            Vector2 g = GuideCoordinates(guide, local);
            if (p.strokeOrgan != SutureStrokeId)
            {
                if (!rules.CanBeginSuture(g.x, g.y)) { p.strokeRejected = true; Hint(p, OpHint.StitchFromTop); return; }
                p.strokeOrgan = SutureStrokeId;
            }
            ctxClient = p.id;
            if (rules.Suture(g.x, g.y, dt) == CutStep.Completed) { Debug.Log($"[OPS] SUTURED patient={s.patientId} client={p.id}"); nextSnapshot = 0f; }
            ctxClient = -1;
        }
        private void Hands(Participant p)
        {
            var t = p.pressTarget;
            if (t.kind != TargetKind.Organ || t.index >= 3 || p.inventory.PhysicalItem != null) return;
            int i = t.index; var organ = State.organs[i];
            if (organ.removed || !organ.Opened) return;
            if (!organ.Released) { if (p.pressStart) Hint(p, OpHint.CutCordsFirst, i); return; }
            if (!rules.CanOperate(false)) { if (p.pressStart) Hint(p, OpHint.Squirming); return; }
            p.pullOrgan = i;
            pullSums[i] += p.pullTarget; pullHolders[i]++;
            outputHolders[i] ??= p;
        }
        private void Detach(int index, Participant p)
        {
            // State is claimed synchronously before Spawn; later RPCs/ticks see removed=true, so no organ is ever made twice.
            ctxOrgan = index; ctxClient = p != null ? p.id : -1;
            float roll = OperationTestHooks.ForcedRoll ?? ArgumentFloat("-ops-roll") ?? UnityEngine.Random.value;
            bool done = rules.Extract(index, roll);
            ctxOrgan = -1; ctxClient = -1;
            if (!done) return;
            var organ = State.organs[index];
            var data = new OperationItemState
            {
                id = organ.outputId, kind = index == 2 ? 1 : 0, organIndex = index, grade = organ.Grade,
                position = OrganPosition(index) + OrganNormal(index) * tuning.pullDistance,
                rotation = transform.rotation
            };
            SpawnItem(data, p);
            if (record != null && record.Stage == PatientStage.AtBase) registry.Move(record, PatientStage.InOperation);
            Debug.Log($"[OPS] EXTRACT id={data.id} grade={data.grade} chance={organ.deathChance:F2} roll={organ.rolled:F5} holders={pullHolders[index]} outputs={items.Count}");
            Save(); Publish();
        }

        private void Update()
        {
            foreach (var c in cursors.Values) c.smoothed = Vector3.Lerp(c.smoothed, c.local, 1f - Mathf.Exp(-18f * Time.deltaTime));
        }

        public static bool HasArgument(string arg) => Array.IndexOf(Environment.GetCommandLineArgs(), arg) >= 0;
        public static float? ArgumentFloat(string key)
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, key);
            return i >= 0 && i + 1 < args.Length && float.TryParse(args[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v) ? v : (float?)null;
        }
    }
}
