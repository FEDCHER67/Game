using System;
using System.Collections.Generic;
using FishNet;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Characters.Npc;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>Server -> clients: where the mechanic is and what he does (MECHANIC_W86 v01).</summary>
    public struct WorkshopMechanicStateBroadcast : IBroadcast
    {
        public uint Seq;
        public Vector3 Position;
        public float Yaw;
        public byte Action;
        /// <summary>Increments with every new action (a gag after a gag restarts the clip).</summary>
        public ushort Serial;
        /// <summary>Seconds since the action started on the server (a late joiner starts mid-clip).</summary>
        public float Age;
        public float Speed;
    }

    /// <summary>One stop of the mechanic's routine: a route node and what he does there (Idle = his home spot: he waits
    /// there, approachable, for HomeDwellSeconds).</summary>
    [Serializable]
    public struct MechanicStop
    {
        public int Node;
        public MechanicAction Work;
    }

    /// <summary>A no-go box in the workshop frame (building-local, axis aligned): pit, lift, van path, loading area, other
    /// bays, outside. The route is built clear of them; at run time a leg into one is refused.</summary>
    [Serializable]
    public struct MechanicKeepOut
    {
        public string Name;
        public Vector3 Center;
        public Vector3 Size;
    }

    /// <summary>
    /// The workshop mechanic's brain (MECHANIC_W86 v01, Workshop_W86): the ONE owner of his movement and actions. The server
    /// (the host, or any authority) runs it; clients only show the state it broadcasts. Priorities, highest first:
    /// 1. the upgrade performance (WorkshopServiceV01.Performance): at the lift's control box he turns to the van and plays
    ///    Mech_Upgrade_Perform; the service commits the purchase at its Poof;
    /// 2. a lift session: he walks to the control box and works it (raising / lowering), attends the owner while it is up;
    /// 3. attention: a player within 2.5 m (horizontal, same level, inside the workshop, clear sight) or the conversation
    ///    participant: he stops cleanly, turns smoothly (Mech_Attend_Enter / _Loop) and lets go at 3.5 m after a short delay
    ///    (Mech_Attend_Exit), then resumes;
    /// 4. a wrench gag every 20-45 active seconds while idle (never in dialogue, hand-in, service or attention);
    /// 5. the routine: home spot (approachable, by the desk) -> workbench (Mech_Work_InspectPart) -> beside the east lift
    ///    post (Mech_Work_CheckBay) -> parts shelf (Mech_Work_WipeBench) -> home, along integrator-checked legs (Nodes /
    ///    Links) that keep out of the pit, the lift, the van path and loading area, the other bays and the road.
    /// He waits for a player standing in his way and for a van parked across a leg (and heads home if it stays), walks
    /// without a collider (never shoves anybody) and stands as a solid capsule only where no player is.
    /// Network: FishNet broadcasts like WorkshopServiceV01 (no NetworkObject): the state at 10 Hz while he moves or turns,
    /// at once on a new action, 1 Hz otherwise; a joining client gets it with the workshop's Hello (current action and its
    /// age: no replayed puffs or purchases).
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-30)]
    public sealed class WorkshopMechanicBrainV01 : MonoBehaviour
    {
        public static WorkshopMechanicBrainV01 Instance { get; private set; }

        [Header("Route (children of W86_Workshop_Anchors, set by the integrator)")]
        [Tooltip("The workshop frame (building root) the keep-out boxes are measured in.")]
        public Transform Frame;
        [Tooltip("Route nodes on the floor: stops (their forward = where he faces to work) and via points.")]
        public Transform[] Nodes = new Transform[0];
        [Tooltip("Clear straight legs between nodes (indices into Nodes), checked by the integrator.")]
        public Vector2Int[] Links = new Vector2Int[0];
        [Tooltip("The routine in order; [0] = his home spot (Work = Idle: he waits there, approachable).")]
        public MechanicStop[] Stops = new MechanicStop[0];
        [Tooltip("Node where he works the lift and performs upgrades (the control box point).")]
        public int ServiceNode = -1;
        public MechanicKeepOut[] KeepOut = new MechanicKeepOut[0];

        [Header("Tuning")]
        public float WalkSpeed = 1.2f;
        public float TurnDegreesPerSecond = 200f;
        [Tooltip("Seconds he waits at his home spot between rounds (random in the range).")]
        public Vector2 HomeDwellSeconds = new Vector2(14f, 28f);
        [Tooltip("Seconds he stands after a work clip before walking on.")]
        public Vector2 StopDwellSeconds = new Vector2(1.5f, 3.5f);
        [Tooltip("Active seconds between optional wrench gags.")]
        public Vector2 GagIntervalSeconds = new Vector2(MechanicGagClock.DefaultMinInterval, MechanicGagClock.DefaultMaxInterval);
        public float GagQuietAfterBusy = MechanicGagClock.DefaultQuietAfterBusy;
        [Tooltip("Attention: start radius (m, horizontal), release radius, release delay (s), max level difference (m).")]
        public float AttentionStartRadius = MechanicAttention.DefaultStart;
        public float AttentionReleaseRadius = MechanicAttention.DefaultRelease;
        public float AttentionReleaseDelay = MechanicAttention.DefaultReleaseDelay;
        public float AttentionMaxLevel = MechanicAttention.DefaultMaxLevel;
        [Tooltip("He stops walking when a player is this close ahead (m).")]
        public float PlayerClearance = 0.95f;
        [Tooltip("Seconds a van parked across his leg may block him before he heads home instead.")]
        public float VanBlockedGiveUp = 4f;
        public float EyeHeight = 1.55f;
        [Tooltip("Within this angle (deg) of the van he counts as facing it (the aim starts).")]
        public float FacingTolerance = 12f;
        [Tooltip("The puff material (Characters/Mechanic_W86/Fx/MechanicPuff_v01.mat).")]
        public Material PuffMaterial;

        // ---- server state
        private enum Leg : byte { Dwell, Walk, Work, Gag, Attend, AttendExit, Service }
        private Leg leg = Leg.Dwell;
        private Leg resumeLeg = Leg.Dwell;
        private MechanicAction action = MechanicAction.Idle;
        private float age;
        private ushort serial;
        private Vector3 pos;
        private float yaw, speed, dwell, blockedFor, sense;
        private int stop, fromNode = -1;
        private readonly List<int> path = new List<int>();
        private int pathAt;
        private bool started, facingVan;
        private MechanicGagClock gags;
        private MechanicAttention attention;
        private readonly List<AttentionCandidate> candidates = new List<AttentionCandidate>();
        private readonly Dictionary<string, Vector3> candidateFeet = new Dictionary<string, Vector3>();
        private readonly List<Vector3> bodies = new List<Vector3>();
        private readonly RaycastHit[] hits = new RaycastHit[16];
        private Collider standCollider;
        private CharacterController standController;
        private float nextVanLook;
        private Bounds vanLocal;
        private Transform vanTransform;
        // ---- network
        private NetworkManager manager;
        private bool bound;
        private uint seq;
        private float nextPush, nextBeat;
        private ushort pushedSerial = ushort.MaxValue;
        private byte pushedAction = byte.MaxValue;
        private WorkshopMechanicStateBroadcast? view;
        private float viewAt;
        private bool viewSnapped;
        // ---- presentation
        private WorkshopMechanicV01 owner;
        private Transform bodyShown;
        private MechanicW86PresenterV01 presenter;
        private NpcAnimDriver crowdDriver;

        /// <summary>Server: he stands at his service point facing the van (the performance's aim may start).</summary>
        public bool FacingVan => facingVan;
        public MechanicAction Action => action;
        public Vector3 BodyPosition => Body != null ? Body.position : transform.position;
        public bool HasBody => Body != null;
        public string AttentionTarget => attention != null ? attention.Target : "";
        /// <summary>Where he works the lift and performs upgrades (his service node), null without a route.</summary>
        public Vector3? ServicePosition => ServiceNode >= 0 && ServiceNode < Nodes.Length && Nodes[ServiceNode] != null ? Nodes[ServiceNode].position : (Vector3?)null;

        /// <summary>His spawned body (null until WorkshopMechanicV01 spawned it).</summary>
        public Transform Body => owner != null ? owner.Body : null;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Instance = null;

        private void Awake()
        {
            owner = GetComponent<WorkshopMechanicV01>();
            Nodes ??= new Transform[0];
            Links ??= new Vector2Int[0];
            Stops ??= new MechanicStop[0];
            KeepOut ??= new MechanicKeepOut[0];
        }

        private void OnEnable() => Instance = this;

        private void OnDisable()
        {
            Unbind();
            if (Instance == this) Instance = null;
        }

        // ================================================================== binding

        private void Bind()
        {
            NetworkManager nm = InstanceFinder.NetworkManager;
            if (nm == null || bound && nm == manager) return;
            Unbind();
            manager = nm;
            manager.ClientManager.RegisterBroadcast<WorkshopMechanicStateBroadcast>(OnClientState);
            manager.ClientManager.OnClientConnectionState += OnClientConnection;
            bound = true;
        }

        private void Unbind()
        {
            if (!bound || manager == null) { bound = false; return; }
            manager.ClientManager.UnregisterBroadcast<WorkshopMechanicStateBroadcast>(OnClientState);
            manager.ClientManager.OnClientConnectionState -= OnClientConnection;
            bound = false;
        }

        private void OnClientConnection(ClientConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Stopped) { view = null; viewSnapped = false; started = false; }
        }

        /// <summary>Server: the current state to one (joining) client (called from the workshop's Hello).</summary>
        public void SendStateTo(NetworkConnection c)
        {
            if (manager == null || c == null || !c.IsActive || !manager.IsServerStarted) return;
            manager.ServerManager.Broadcast(c, Snapshot());
        }

        private WorkshopMechanicStateBroadcast Snapshot() => new WorkshopMechanicStateBroadcast
        {
            Seq = ++seq, Position = pos, Yaw = yaw, Action = (byte)action, Serial = serial, Age = age, Speed = speed,
        };

        private void Push()
        {
            if (manager == null || !manager.IsServerStarted) return;
            float t = Time.unscaledTime;
            bool changed = pushedSerial != serial || pushedAction != (byte)action;
            bool moving = speed > 0.01f || leg == Leg.Attend || leg == Leg.Service || leg == Leg.Walk;
            if (!(changed || moving && t >= nextPush || t >= nextBeat)) return;
            pushedSerial = serial;
            pushedAction = (byte)action;
            nextPush = t + 0.1f;
            nextBeat = t + 1f;
            if (manager.ServerManager.Clients.Count <= 1) return;
            WorkshopMechanicStateBroadcast s = Snapshot();
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && !c.IsLocalClient) manager.ServerManager.Broadcast(c, s);
        }

        private void OnClientState(WorkshopMechanicStateBroadcast s, Channel channel)
        {
            if (WorkshopServiceV01.Authority) return;
            if (view.HasValue && s.Seq != 0 && s.Seq < view.Value.Seq && view.Value.Seq - s.Seq < 1000000) return;
            view = s;
            viewAt = Time.unscaledTime;
        }

        // ================================================================== per frame

        private void Update()
        {
            Bind();
            Transform body = Body;
            if (body == null) return;
            if (body != bodyShown)
            {
                bodyShown = body;
                presenter = body.GetComponent<MechanicW86PresenterV01>();
                crowdDriver = presenter == null ? body.GetComponent<NpcAnimDriver>() : null;
                standCollider = body.GetComponent<CapsuleCollider>();
                standController = body.GetComponent<CharacterController>();
                started = false;
                viewSnapped = false;
            }
            float dt = Mathf.Min(Time.deltaTime, 0.1f);
            if (WorkshopServiceV01.Authority) ServerTick(body, dt);
            else ClientTick(body, dt);
        }

        // ================================================================== client view

        private void ClientTick(Transform body, float dt)
        {
            if (!view.HasValue) return;
            WorkshopMechanicStateBroadcast s = view.Value;
            float k = 1f - Mathf.Exp(-12f * dt);
            Vector3 p = body.position;
            if (!viewSnapped || (p - s.Position).sqrMagnitude > 9f) p = s.Position; else p = Vector3.Lerp(p, s.Position, k);
            float y = viewSnapped ? Mathf.LerpAngle(body.eulerAngles.y, s.Yaw, k) : s.Yaw;
            body.SetPositionAndRotation(p, Quaternion.Euler(0f, y, 0f));
            float shownAge = s.Age + (Time.unscaledTime - viewAt);
            Present((MechanicAction)s.Action, s.Serial, shownAge, s.Speed, !viewSnapped);
            viewSnapped = true;
            SetStanding(s.Speed <= 0.01f, p);
        }

        // ================================================================== server

        private void Begin(Transform body)
        {
            started = true;
            pos = body.position;
            yaw = body.eulerAngles.y;
            int seed = Environment.TickCount ^ (int)(transform.position.x * 1000f);
            gags = new MechanicGagClock(seed, 2, GagIntervalSeconds.x, GagIntervalSeconds.y, GagQuietAfterBusy);
            attention = new MechanicAttention(AttentionStartRadius, AttentionReleaseRadius, AttentionReleaseDelay, AttentionMaxLevel);
            stop = 0;
            fromNode = NearestNode(pos);
            path.Clear();
            pathAt = 0;
            leg = Leg.Dwell;
            dwell = Range(HomeDwellSeconds) * 0.5f;
            SetAction(MechanicAction.Idle);
        }

        private void ServerTick(Transform body, float dt)
        {
            if (!started) Begin(body);
            age += dt;
            speed = 0f;
            WorkshopServiceV01 service = WorkshopServiceV01.Instance;
            bool perform = service != null && service.Performance.Busy;
            bool holds = service != null && service.Session.HoldsVan;
            bool talk = service != null && service.TalkerCount > 0;
            // attention (10 Hz is plenty for a 2.5 / 3.5 m hysteresis)
            sense += dt;
            if (sense >= 0.1f)
            {
                Gather(service);
                attention.Tick(sense, candidates);
                sense = 0f;
            }
            bool suppressed = talk || holds || perform || attention.Active || leg == Leg.Attend || leg == Leg.AttendExit;
            int gag = gags.Tick(dt, leg == Leg.Dwell && action == MechanicAction.Idle && workPending == MechanicAction.Idle, suppressed);
            facingVan = false;

            if (perform || holds) Service(service, perform, dt);
            else if (attention.Active && attention.Target.Length > 0 && candidateFeet.TryGetValue(attention.Target, out Vector3 who)) Attend(who, dt);
            else Routine(gag, dt);

            body.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            Present(action, serial, age, speed, false);
            SetStanding(speed <= 0.01f, pos);
            Push();
        }

        private void SetAction(MechanicAction a)
        {
            action = a;
            age = 0f;
            serial = unchecked((ushort)(serial + 1));
        }

        private void Present(MechanicAction a, int s, float t, float v, bool snap)
        {
            if (presenter != null) presenter.Show(a, s, t, v, snap);
            else if (crowdDriver != null && v > 0.01f) crowdDriver.SetMove(v);
        }

        // ---------------------------------------------------------------- the lift session and the performance

        private void Service(WorkshopServiceV01 service, bool perform, float dt)
        {
            if (leg == Leg.Attend || leg == Leg.AttendExit) attention.Clear();
            if (leg != Leg.Service && leg != Leg.Walk) path.Clear();
            Transform point = ServiceNode >= 0 && ServiceNode < Nodes.Length && Nodes[ServiceNode] != null ? Nodes[ServiceNode] : service.ControlPoint;
            if (point == null) point = transform;
            Vector3 flat = point.position - pos;
            flat.y = 0f;
            UpgradePerformance perf = service.Performance;
            bool aiming = perform && (perf.Stage == UpgradeStage.Aiming || perf.Stage == UpgradeStage.After);
            if (aiming && flat.magnitude > 0.12f)
            {
                // the aim began before he reached the box (held up on the way): he stops and performs where he stands,
                // so the clip and its Poof stay on the server's clock
                path.Clear();
                leg = Leg.Service;
                Perform(perf, service, point, dt);
                return;
            }
            if (flat.magnitude > 0.12f)
            {
                // walk to the control box (along the route when it has the node)
                if (leg != Leg.Walk || path.Count == 0 || path[path.Count - 1] != ServiceNode)
                {
                    leg = Leg.Walk;
                    if (!Plan(ServiceNode)) { path.Clear(); }
                    if (action != MechanicAction.Walk) SetAction(MechanicAction.Walk);
                }
                if (path.Count > 0) FollowPath(dt);
                else StepToward(point.position, dt);
                return;
            }
            pos = new Vector3(point.position.x, Mathf.MoveTowards(pos.y, point.position.y, 2f * dt), point.position.z);
            path.Clear();
            fromNode = ServiceNode;
            leg = Leg.Service;
            if (perform)
            {
                Perform(perf, service, point, dt);
                return;
            }
            // the lift moves: he works the box; it is up: he attends the owner when he is near, else the box
            LiftPhase phase = service.Phase;
            bool ownerNear = phase == LiftPhase.Up && candidateFeet.TryGetValue(service.Owner, out Vector3 ownerFeet) &&
                             Flat(ownerFeet - pos) <= AttentionReleaseRadius + 1f;
            if (ownerNear && candidateFeet.TryGetValue(service.Owner, out Vector3 o))
            {
                TurnToward(o, dt);
                if (action != MechanicAction.Attend) SetAction(MechanicAction.Attend);
            }
            else
            {
                TurnTo(point.eulerAngles.y, dt);
                if (action == MechanicAction.Attend) SetAction(MechanicAction.AttendExit);
                else if (action == MechanicAction.AttendExit && age >= MechanicClips.Seconds(MechanicAction.AttendExit)) SetAction(MechanicAction.Idle);
                else if (action != MechanicAction.Idle && action != MechanicAction.AttendExit) SetAction(MechanicAction.Idle);
            }
        }

        /// <summary>Turns to the van's aim point and plays Mech_Upgrade_Perform on the performance's own clock (its Poof at
        /// 1.70 s is when the service commits the purchase).</summary>
        private void Perform(UpgradePerformance p, WorkshopServiceV01 service, Transform point, float dt)
        {
            Vector3 van = service.AimPoint ?? service.HeldVanCentre ?? point.position + point.forward * 2.5f;
            float err = TurnToward(van, dt);
            Vector3 flat = point.position - pos;
            flat.y = 0f;
            facingVan = flat.magnitude <= 0.12f && Mathf.Abs(err) <= FacingTolerance;
            if (p.Stage == UpgradeStage.Aiming || p.Stage == UpgradeStage.After)
            {
                if (action != MechanicAction.Upgrade || p.Serial != perfSerial)
                {
                    SetAction(MechanicAction.Upgrade);
                    perfSerial = p.Serial;
                }
                age = p.Age; // the clip follows the server's performance clock exactly
            }
            else if (action != MechanicAction.Idle) SetAction(MechanicAction.Idle);
        }

        private int perfSerial = -1;

        // ---------------------------------------------------------------- attention

        private void Attend(Vector3 who, float dt)
        {
            if (leg != Leg.Attend)
            {
                if (leg != Leg.AttendExit) resumeLeg = leg == Leg.Work || leg == Leg.Gag ? Leg.Dwell : leg;
                leg = Leg.Attend;
                SetAction(MechanicAction.Attend);
            }
            TurnToward(who, dt);
        }

        private void EndAttention()
        {
            leg = Leg.AttendExit;
            SetAction(MechanicAction.AttendExit);
        }

        // ---------------------------------------------------------------- the routine

        private void Routine(int gag, float dt)
        {
            switch (leg)
            {
                case Leg.Attend:
                    EndAttention();
                    return;
                case Leg.AttendExit:
                    if (age < MechanicClips.Seconds(MechanicAction.AttendExit)) return;
                    leg = resumeLeg == Leg.Walk && path.Count > 0 ? Leg.Walk : Leg.Dwell;
                    if (leg == Leg.Dwell && dwell <= 0f) dwell = Range(StopDwellSeconds);
                    SetAction(leg == Leg.Walk ? MechanicAction.Walk : MechanicAction.Idle);
                    return;
                case Leg.Service:
                    // the session ended: back to the routine from the control box, home first
                    leg = Leg.Dwell;
                    dwell = 0f;
                    stop = Stops.Length > 0 ? Stops.Length - 1 : 0; // next = home
                    SetAction(MechanicAction.Idle);
                    return;
                case Leg.Work:
                case Leg.Gag:
                    FaceStop(dt);
                    if (age < MechanicClips.Seconds(action)) return;
                    if (leg == Leg.Work) dwell = Range(StopDwellSeconds);
                    leg = Leg.Dwell;
                    SetAction(MechanicAction.Idle);
                    return;
                case Leg.Walk:
                    if (action != MechanicAction.Walk) SetAction(MechanicAction.Walk);
                    if (path.Count == 0 || pathAt >= path.Count) { Arrive(); return; }
                    FollowPath(dt);
                    if (pathAt >= path.Count) Arrive();
                    return;
                default: // Dwell
                {
                    float err = FaceStop(dt);
                    if (workPending != MechanicAction.Idle)
                    {
                        if (Mathf.Abs(err) > 8f) return;
                        leg = Leg.Work;
                        SetAction(workPending);
                        workPending = MechanicAction.Idle;
                        return;
                    }
                    if (gag >= 0)
                    {
                        leg = Leg.Gag;
                        SetAction(gag == 0 ? MechanicAction.GagWrenchGun : MechanicAction.GagCockNod);
                        return;
                    }
                    if (action != MechanicAction.Idle) SetAction(MechanicAction.Idle);
                    dwell -= dt;
                    if (dwell > 0f || Stops.Length < 2) return;
                    NextStop();
                    return;
                }
            }
        }

        private void NextStop()
        {
            for (int tries = 0; tries < Stops.Length; tries++)
            {
                stop = (stop + 1) % Stops.Length;
                if (Plan(Stops[stop].Node))
                {
                    leg = Leg.Walk;
                    SetAction(MechanicAction.Walk);
                    return;
                }
            }
            dwell = Range(StopDwellSeconds);
        }

        private void Arrive()
        {
            path.Clear();
            pathAt = 0;
            MechanicStop s = stop >= 0 && stop < Stops.Length ? Stops[stop] : default;
            leg = Leg.Dwell;
            SetAction(MechanicAction.Idle);
            // a work stop: turn to the bench / shelf / post first (Dwell), the clip starts once he faces it
            workPending = MechanicClips.IsWork(s.Work) ? s.Work : MechanicAction.Idle;
            dwell = workPending != MechanicAction.Idle ? 0f : stop == 0 ? Range(HomeDwellSeconds) : Range(StopDwellSeconds);
        }

        private MechanicAction workPending = MechanicAction.Idle;

        /// <summary>Turns to the current stop's working direction; returns the remaining error (deg), 0 when there is none.</summary>
        private float FaceStop(float dt)
        {
            int node = stop >= 0 && stop < Stops.Length ? Stops[stop].Node : -1;
            if (node >= 0 && node < Nodes.Length && Nodes[node] != null && fromNode == node) return TurnTo(Nodes[node].eulerAngles.y, dt);
            if (owner != null && owner.Spot != null && stop == 0 && Flat(owner.Spot.position - pos) < 0.3f) return TurnTo(owner.Spot.eulerAngles.y, dt);
            return 0f;
        }

        // ---------------------------------------------------------------- walking

        private void FollowPath(float dt)
        {
            if (pathAt >= path.Count) return;
            Transform n = Nodes[path[pathAt]];
            if (n == null) { path.Clear(); return; }
            if (StepToward(n.position, dt))
            {
                fromNode = path[pathAt];
                pathAt++;
                blockedFor = 0f;
            }
        }

        /// <summary>One walking step toward a point: turns first when it is far off his heading, waits for a player ahead
        /// or a van across the leg. True on arrival.</summary>
        private bool StepToward(Vector3 target, float dt)
        {
            Vector3 to = target - pos;
            to.y = 0f;
            float dist = to.magnitude;
            if (dist <= 0.06f)
            {
                pos = new Vector3(target.x, pos.y, target.z);
                return true;
            }
            Vector3 dir = to / dist;
            float err = TurnTo(Quaternion.LookRotation(dir).eulerAngles.y, dt);
            float along = Mathf.Clamp01(1f - Mathf.Abs(err) / 75f); // a sharp corner: turn on the spot first
            bool blocked = PlayerAhead(pos, dir) || VanAcross(pos, target);
            if (blocked)
            {
                blockedFor += dt;
                if (blockedFor > VanBlockedGiveUp && leg == Leg.Walk && Stops.Length > 0 && stop != 0 && VanAcross(pos, target))
                {
                    // a van parked across the route: give the stop up and go home another way (or wait)
                    blockedFor = 0f;
                    stop = 0;
                    if (!Plan(Stops[0].Node)) path.Clear();
                }
                return false;
            }
            blockedFor = 0f;
            float step = Mathf.Min(WalkSpeed * along * dt, dist);
            pos += dir * step;
            pos.y = Mathf.MoveTowards(pos.y, target.y, 2f * dt);
            speed = step / Mathf.Max(1e-4f, dt);
            return false;
        }

        private float TurnToward(Vector3 point, float dt)
        {
            Vector3 d = point - pos;
            d.y = 0f;
            if (d.sqrMagnitude < 1e-4f) return 0f;
            return TurnTo(Quaternion.LookRotation(d).eulerAngles.y, dt);
        }

        /// <summary>Turns smoothly (eased near the end, no snap); returns the remaining error (deg).</summary>
        private float TurnTo(float targetYaw, float dt)
        {
            float err = Mathf.DeltaAngle(yaw, targetYaw);
            float rate = TurnDegreesPerSecond * Mathf.Clamp(Mathf.Abs(err) / 45f, 0.35f, 1f);
            yaw = Mathf.MoveTowardsAngle(yaw, targetYaw, rate * dt);
            return Mathf.DeltaAngle(yaw, targetYaw);
        }

        // ---------------------------------------------------------------- planning (a handful of nodes: plain Dijkstra)

        private bool Plan(int goal)
        {
            path.Clear();
            pathAt = 0;
            if (goal < 0 || goal >= Nodes.Length || Nodes[goal] == null) return false;
            int startA = fromNode >= 0 && fromNode < Nodes.Length ? fromNode : NearestNode(pos);
            if (startA < 0) return false;
            if (startA == goal)
            {
                path.Add(goal);
                return true;
            }
            int n = Nodes.Length;
            var dist = new float[n];
            var prev = new int[n];
            var done = new bool[n];
            for (int i = 0; i < n; i++) { dist[i] = float.MaxValue; prev[i] = -1; }
            // from where he stands: straight to the node he came from (he is on its leg)
            dist[startA] = Flat(Nodes[startA].position - pos);
            for (int iter = 0; iter < n; iter++)
            {
                int u = -1;
                for (int i = 0; i < n; i++) if (!done[i] && dist[i] < float.MaxValue && (u < 0 || dist[i] < dist[u])) u = i;
                if (u < 0 || u == goal) break;
                done[u] = true;
                foreach (Vector2Int l in Links)
                {
                    int v = l.x == u ? l.y : l.y == u ? l.x : -1;
                    if (v < 0 || v >= n || done[v] || Nodes[v] == null) continue;
                    float d = dist[u] + Flat(Nodes[v].position - Nodes[u].position);
                    if (d < dist[v]) { dist[v] = d; prev[v] = u; }
                }
            }
            if (dist[goal] == float.MaxValue) return false;
            for (int v = goal; v >= 0; v = prev[v]) path.Insert(0, v);
            // already on the first node: skip it
            if (path.Count > 1 && Flat(Nodes[path[0]].position - pos) < 0.1f) path.RemoveAt(0);
            return true;
        }

        private int NearestNode(Vector3 p)
        {
            int best = -1;
            float bd = float.MaxValue;
            for (int i = 0; i < Nodes.Length; i++)
            {
                if (Nodes[i] == null) continue;
                float d = Flat(Nodes[i].position - p);
                if (d < bd) { bd = d; best = i; }
            }
            return best;
        }

        // ---------------------------------------------------------------- sensing

        private void Gather(WorkshopServiceV01 service)
        {
            candidates.Clear();
            candidateFeet.Clear();
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy != null && economy.IsServer)
            {
                foreach (string id in economy.ServerParticipants())
                {
                    Vector3? feet = TeamEconomy.ServerActorPosition(economy.ServerConnectionOf(id));
                    if (feet.HasValue) AddCandidate(id, feet.Value, service);
                }
            }
            else
            {
                Vector3? feet = LocalFeet();
                if (feet.HasValue) AddCandidate(TeamEconomy.HostParticipant, feet.Value, service);
            }
        }

        private static Vector3? LocalFeet()
        {
            var capture = OnlyVolunteers.Capture.CaptureDirector.Instance;
            if (capture != null) return capture.Pawn != null && capture.Pawn.Controlled ? capture.Pawn.Position : (Vector3?)null;
            return null;
        }

        private void AddCandidate(string id, Vector3 feet, WorkshopServiceV01 service)
        {
            if (string.IsNullOrEmpty(id) || candidateFeet.ContainsKey(id)) return;
            Vector3 d = feet - pos;
            var c = new AttentionCandidate
            {
                Id = id, Dx = d.x, Dz = d.z, Dy = d.y,
                Talking = service != null && service.IsTalking(id),
            };
            c.Visible = InsideWorkshop(feet) && Flat(d) <= AttentionReleaseRadius + 1.5f && SightClear(feet);
            candidates.Add(c);
            candidateFeet[id] = feet;
        }

        /// <summary>Inside the workshop building (its footprint, floor level): nobody outside the doors or on the roof.</summary>
        private bool InsideWorkshop(Vector3 world)
        {
            Transform f = Frame != null ? Frame : transform;
            Vector3 l = f.InverseTransformPoint(world);
            return Mathf.Abs(l.x) <= 12f && l.z >= -6f && l.z <= 5.8f && l.y > -0.6f && l.y < 2.2f;
        }

        /// <summary>A clear line from his eyes to the player's (walls, floors, a van in between block it).</summary>
        private bool SightClear(Vector3 feet)
        {
            Vector3 a = pos + Vector3.up * EyeHeight, b = feet + Vector3.up * EyeHeight;
            Vector3 d = b - a;
            float len = d.magnitude;
            if (len < 0.3f) return true;
            int n = Physics.RaycastNonAlloc(a, d / len, hits, len, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                Collider c = hits[i].collider;
                if (c == null) continue;
                if (bodyShown != null && c.transform.IsChildOf(bodyShown)) continue;
                if (hits[i].distance > len - 0.6f) continue; // the player's own capsule
                if (c.attachedRigidbody != null && c.attachedRigidbody.GetComponentInParent<OnlyVolunteers.Player.KccFirstPersonInput>() != null) continue;
                return false;
            }
            return true;
        }

        private bool PlayerAhead(Vector3 from, Vector3 dir)
        {
            bodies.Clear();
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy != null && economy.IsServer) economy.ServerPlayerPositions(bodies);
            else { Vector3? me = LocalFeet(); if (me.HasValue) bodies.Add(me.Value); }
            foreach (Vector3 b in bodies)
            {
                Vector3 d = b - from;
                if (Mathf.Abs(d.y) > 1.5f) continue;
                d.y = 0f;
                if (d.magnitude < PlayerClearance && Vector3.Dot(d, dir) > 0f) return true;
            }
            return false;
        }

        /// <summary>A van (the team van or any VanController) parked across the leg from 'a' to 'b'.</summary>
        private bool VanAcross(Vector3 a, Vector3 b)
        {
            if (Time.unscaledTime >= nextVanLook)
            {
                nextVanLook = Time.unscaledTime + 0.5f;
                var v = FindAnyObjectByType<OnlyVolunteers.Vehicles.VanController>();
                vanTransform = v != null ? v.transform : null;
                if (v != null) vanLocal = WorkshopServiceV01.VanBodyBoundsOf(v);
            }
            if (vanTransform == null) return false;
            WorkshopServiceV01 service = WorkshopServiceV01.Instance;
            if (service != null && service.Session.HoldsVan) return false; // on the lift: it moves with the lift, he works the box
            Vector3 la = vanTransform.InverseTransformPoint(a), lb = vanTransform.InverseTransformPoint(b);
            Bounds box = vanLocal;
            box.Expand(new Vector3(0.9f, 0f, 0.9f)); // his radius + the doors' first swing
            // sample the leg (it is short): any point inside the van's footprint blocks it
            for (int i = 0; i <= 8; i++)
            {
                Vector3 p = Vector3.Lerp(la, lb, i / 8f);
                if (Mathf.Abs(p.x - box.center.x) <= box.extents.x && Mathf.Abs(p.z - box.center.z) <= box.extents.z && p.y > box.min.y - 1f && p.y < box.max.y) return true;
            }
            return false;
        }

        /// <summary>Standing he is a solid capsule players walk round; walking (or with a player right on him) he has no
        /// collider, so he never shoves or lifts anybody.</summary>
        private void SetStanding(bool standing, Vector3 at)
        {
            bool solid = standing && !PlayerWithin(at, 0.75f);
            if (standCollider != null && standCollider.enabled != solid) standCollider.enabled = solid;
            if (standController != null && standController.enabled != solid) standController.enabled = solid;
        }

        private bool PlayerWithin(Vector3 at, float r)
        {
            bodies.Clear();
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy != null && economy.IsServer) economy.ServerPlayerPositions(bodies);
            else { Vector3? me = LocalFeet(); if (me.HasValue) bodies.Add(me.Value); }
            foreach (Vector3 b in bodies)
            {
                Vector3 d = b - at;
                if (Mathf.Abs(d.y) < 2f && Flat(d) < r) return true;
            }
            return false;
        }

        // ---------------------------------------------------------------- helpers

        private static float Flat(Vector3 d) => new Vector2(d.x, d.z).magnitude;

        private static float Range(Vector2 r) => UnityEngine.Random.Range(Mathf.Min(r.x, r.y), Mathf.Max(r.x, r.y));

        /// <summary>A world point inside one of the keep-out boxes (for checks; the route itself is built clear).</summary>
        public bool InKeepOut(Vector3 world, float radius, out string which)
        {
            which = "";
            Transform f = Frame != null ? Frame : transform;
            Vector3 l = f.InverseTransformPoint(world);
            foreach (MechanicKeepOut k in KeepOut)
            {
                Vector3 e = k.Size * 0.5f + new Vector3(radius, 0f, radius);
                if (Mathf.Abs(l.x - k.Center.x) <= e.x && Mathf.Abs(l.z - k.Center.z) <= e.z && Mathf.Abs(l.y - k.Center.y) <= e.y) { which = k.Name; return true; }
            }
            return false;
        }
    }
}
