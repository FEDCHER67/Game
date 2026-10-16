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

        public OperationTuning Tuning => tuning;
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
        public Vector3 SitePoint(int organ, Vector3 metres) => Anchors.Point(organ, metres);
        public Vector3 SiteLocal(int organ, Vector3 world) => Anchors.LocalMetres(organ, world);
        public Vector3 OrganPosition(int i) => Anchors.Point(i, new Vector3(0, 0, tuning.organLift));
        public Vector3 OrganNormal(int i) => Anchors.Normal(i);
        public Vector3 GuidePosition(int i, float along) => Anchors.Point(i, OperationGeometry.GuidePoint(tuning, i, along));
        public Vector3 ConnectionPosition(int i, int c) { OperationGeometry.Cord(tuning, i, c, out var a, out var r); return Anchors.Point(i, (a + r) * 0.5f); }

        /// <summary>Where a held tool hangs for a cursor point: its tip just above the surface.</summary>
        public Pose HeldToolPose(OperationToolKind kind, Vector3 point, Vector3 normal)
        {
            Vector3 flatBack = Vector3.ProjectOnPlane(-CameraPose.forward, transform.up).normalized;
            Vector3 right = Vector3.Cross(transform.up, flatBack).normalized;
            Vector3 tip = point + normal * tuning.toolHover;
            if (kind == OperationToolKind.Scalpel)
            {
                Vector3 toHandle = (transform.up * 0.8f + flatBack * 0.45f - right * 0.3f).normalized;
                return new Pose(tip, Basis(-toHandle, transform.up));
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
                pose = HeldToolPose(tool.Kind, transform.TransformPoint(c.smoothed), transform.up);
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
        }
        private void OnDestroy() => snapshot.OnChange -= Changed;

        public override void OnStartServer()
        {
            base.OnStartServer();
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
            world.patient = rules.State;
            rules.Cue += Hook;
            alignStartSet = false;
            falling = false; serverView.falling = false;
            SpawnPatient();
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
            foreach (var item in world.items) SpawnItem(item, null);
            Publish();
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
            if (cue == PatientCue.Extracted || cue == PatientCue.Death || cue == PatientCue.IncisionOpened) nextSnapshot = 0f;
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
            falling = true;
            fallEndsAt = Time.time + tuning.escapeFallSeconds;
            ReleaseGrabs();
            var rest = RestPose;
            patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
            ApplyPatientPhysics();
            noAlignUntil = fallEndsAt + 1f;
            serverView.falling = true; nextSnapshot = 0f;
        }
        /// <summary>End of the escape clip: the root goes to the KnockedOut root under the landed hips (same yaw as
        /// PatientRest, on the floor) and the body turns dynamic at rest, so nothing slides or snaps.</summary>
        private void Land()
        {
            falling = false; serverView.falling = false; nextSnapshot = 0f;
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
        }
        private void Publish()
        {
            serverView.patient = State; serverView.stock = world.anesthesiaStock; serverView.barrel = world.anesthesiaBarrel;
            serverView.blood = world.bloodFill; serverView.bagsUsedMask = world.bagsUsedMask;
            snapshot.Value = JsonUtility.ToJson(serverView);
            nextSnapshot = Time.time + tuning.snapshotInterval;
        }
        public void Save()
        {
            if (world == null || !IsServerInitialized || rules == null) return;
            world.patient = State;
            if (patient != null) { world.patientPosition = patient.transform.position; world.patientRotation = patient.transform.rotation; }
            world.items.Clear();
            foreach (var item in items) if (item != null && item.Data != null) world.items.Add(item.Data);
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
        public bool ServerOrLocalCanOperate(OperationState s) => s != null && s.onTable && s.aligned && (!s.alive || s.Sleeping || s.Torso);
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
            participants.Add(sender.ClientId, new Participant { id = sender.ClientId, player = player, inventory = inventory, received = Time.time, point = transform.InverseTransformPoint(RestPose.position) });
            Debug.Log($"[OPS] JOIN client={sender.ClientId} count={participants.Count}");
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
                        if (target.index >= 5) return;
                        if (!State.onTable || !State.aligned) { Hint(p, OpHint.NotOnTable); return; }
                        rules.ToggleRestraint(target.index);
                        Publish();
                        break;
                    case TargetKind.Tool:
                        RequestSelectServer(p, (ToolSlot)Mathf.Clamp(target.index, 1, 3));
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
            Debug.Log($"[OPS] LEAVE client={p.id} preserved cuts={State.organs[0].cut:F2}/{State.organs[1].cut:F2}/{State.organs[2].cut:F2} extracted={State.extracted} outputs={items.Count}");
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
            world.bagsUsedMask |= 1 << bag; world.bloodFill = 0f; world.bloodBagged++;
            var pose = BagPose(bag);
            var data = new OperationItemState { id = State.patientId + "/blood/" + world.bloodBagged, kind = 2, grade = 0, sealedBlood = true, position = pose.position + pose.up * 0.04f, rotation = pose.rotation };
            SpawnItem(data, null);
            Hint(p, OpHint.BagReady);
            ObserversCue(PatientCue.BagSealed, bag, p.id);
            CueReceived?.Invoke(PatientCue.BagSealed, bag, p.id);
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
            if (!kinematic) { patient.Body.position = patient.transform.position; patient.Body.rotation = patient.transform.rotation; }
            patient.Body.isKinematic = kinematic; patient.Body.useGravity = !kinematic;
            var rig = patient.GetComponent<OperationPatientRig>();
            if (rig != null) rig.SetPhysicsCollider(!kinematic);
        }
        private void FixedUpdate()
        {
            if (!IsServerInitialized || rules == null) return;
            float dt = Time.fixedDeltaTime;
            removedParticipants.Clear();
            foreach (var pair in participants)
                if (pair.Value.player == null || pair.Value.player.Owner == null || !pair.Value.player.Owner.IsActive || !InReach(pair.Value.player)) removedParticipants.Add(pair.Key);
            foreach (int id in removedParticipants) { ReleaseParticipant(participants[id], false); participants.Remove(id); }

            bool freeze = participants.Count > 0;
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
                if (OperationGeometry.OverPad(local, tuning) && patient.Body.linearVelocity.magnitude < 4f &&
                    rules.BeginAlignment(Vector3.Distance(patient.transform.position, RestPose.position)))
                {
                    alignFromLocal = transform.InverseTransformPoint(patient.transform.position);
                    alignFromRotation = Quaternion.Inverse(transform.rotation) * patient.transform.rotation;
                    alignStartSet = true;
                    ApplyPatientPhysics();
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
                if (p.tool != null) p.tool.ServerHoldAt(HeldToolPose(p.tool.Kind, world, transform.up));
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
                    if (slot == ToolSlot.Scalpel) Scalpel(p, dt);
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
