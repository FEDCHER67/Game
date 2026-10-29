using System;
using System.Collections.Generic;
using System.Globalization;
using FishNet;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    public enum WorkshopRequestKind : byte
    {
        /// <summary>A client's workshop came up: send it the lift state (late join).</summary>
        Hello = 0,
        /// <summary>"Upgrade van" at the mechanic: start (or reopen) the lift session.</summary>
        Start = 1,
        /// <summary>Arg = row kind + "|" + row arg (van_branch|0), Expected = the tier shown as next.</summary>
        Buy = 2,
        /// <summary>"Done": the lift goes down, the session ends at the bottom.</summary>
        Done = 3,
        /// <summary>The mechanic's conversation opened (Arg "1") or closed ("0") on this machine: he attends the talker and
        /// does no gags meanwhile (MECHANIC_W86 v01).</summary>
        Talk = 4,
    }

    public struct WorkshopRequestBroadcast : IBroadcast
    {
        public byte Kind;
        public string Key;
        public string Arg;
        public int Expected;
    }

    public struct WorkshopResultBroadcast : IBroadcast
    {
        public string Key;
        public bool Ok;
        public string Message;
    }

    /// <summary>Server -> clients: the mechanic's upgrade was committed now: the cartoon puff on the van (one-shot, never
    /// replayed to a late joiner).</summary>
    public struct WorkshopPuffBroadcast : IBroadcast
    {
        public Vector3 Position;
        public Vector3 Outward;
    }

    /// <summary>Server -> clients: the lift and the van on it.</summary>
    public struct WorkshopStateBroadcast : IBroadcast
    {
        public uint Seq;
        public byte Phase;
        public float Height;
        public float Swing;
        public string Owner;
        public bool VanHeld;
        public Vector3 VanPosition;
        public Quaternion VanRotation;
    }

    /// <summary>
    /// The workshop's lift and its ONE upgrade session (Workshop_W86 middle bay; Fedya 29.10). FishNet broadcasts like
    /// TeamEconomy (no NetworkObject; the solo host runs the same path). The server owns the session (LiftSession: one owner,
    /// phases, height), the van on the lift and every purchase: "Upgrade van" at the mechanic starts it when the team van
    /// stands in the repair zone over the pit, stopped, with nobody at the wheel and nobody in the way; the van becomes
    /// kinematic (its seat refuses drivers), settles onto the pads and rides up with the lift (1.6 m in 4 s); purchases go
    /// through EconomyState.TryBuyVanTier with the deterministic van:&lt;branch&gt;:&lt;tier&gt; key (fund charged once per
    /// world, saved by the economy commit); "Done" lowers it and gives the van back its physics. Movement pauses while a
    /// player or a free NPC is where the van or the lift arms move (nobody is ever pushed). The owner disconnecting or
    /// walking away lowers the lift by itself; a server stop puts the van back down at once. Clients get the state at 10 Hz
    /// while it moves, else 1 Hz, and on joining; they show the lift height and hold their view of the van on it.
    /// Lives on W86_Workshop_Anchors (integrator: PlaceWorkshopZone, data from Workshop_W86_lift_v01.json):
    /// <see cref="LiftParts"/> = the six moving nodes (two carriages, four arms; they rise by the lift height in their local
    /// +Y), <see cref="LiftArms"/> / <see cref="ArmEngagedYaw"/> = the arms and their swing-in yaw (they swing in under the
    /// sills before the rise and back out of the wheel path after it), <see cref="VanPark"/> = where the van stands (lift
    /// centre, yaw 180), <see cref="ControlPoint"/> = where the mechanic works the control box.
    /// MECHANIC_W86 v01 (29.10): a purchase is no longer committed on the click. The server validates the selection (the very
    /// purchase rules on a throw-away copy of the state, WorkshopUpgradePreview), then the mechanic performs it
    /// (<see cref="Performance"/>: he turns to the van and aims his wrench) and the purchase is committed ONCE at the clip's
    /// Poof (1.70 s): fund charged and tier applied together, the puff broadcast, and only then the buyer's request is
    /// answered. A refusal at that moment = no puff, no charge; the owner leaving / disconnecting / "Done" before it = nothing
    /// charged, the mechanic free again. One performance at a time; repeated clicks are refused while it runs.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-40)]
    public sealed class WorkshopServiceV01 : MonoBehaviour
    {
        public static WorkshopServiceV01 Instance { get; private set; }

        public WorkshopZone Zone;
        [Tooltip("Van centre on the floor over the pit, nose to the back wall (the lift's pad frame).")]
        public Transform VanPark;
        [Tooltip("The lift's moving parts (carriages + arms): they rise by the lift height along their local up.")]
        public Transform[] LiftParts = new Transform[0];
        [Tooltip("The swinging arms (a subset of LiftParts) and their engaged local yaw (degrees).")]
        public Transform[] LiftArms = new Transform[0];
        public float[] ArmEngagedYaw = new float[0];
        [Tooltip("Lift data (Workshop_W86_lift_v01.json travel; ~4 s rise per Fedya's brief; the arms swing in ~1.5 s).")]
        public float LiftTravel = LiftSession.DefaultTravel;
        public float LiftSeconds = LiftSession.DefaultSeconds;
        public float ArmSwingSeconds = LiftSession.DefaultSwingSeconds;
        [Tooltip("Where the mechanic stands at the control box while the lift works (faces the box).")]
        public Transform ControlPoint;
        [Tooltip("Where the session owner must stay (metres from the repair zone) - farther lowers the lift by itself.")]
        public float OwnerLeash = 14f;
        [Tooltip("Mechanic anchor (the Start request is measured from it).")]
        public Transform Mechanic;
        public float MechanicReach = 4.5f;
        [Tooltip("How far the van may stand off the pads (across, along, yaw) and still be settled onto them.")]
        public Vector3 PadTolerance = new Vector3(0.6f, 1.2f, 15f);

        private LiftSession session = new LiftSession();
        private NetworkManager manager;
        private bool bound;
        private uint seq;
        private float nextPush, nextBeat;
        private string lastSignature = "";
        private readonly Dictionary<string, Action<bool, string>> pending = new Dictionary<string, Action<bool, string>>();
        private readonly List<Vector3> players = new List<Vector3>();
        private Vector3[] partBase = new Vector3[0];
        private Quaternion[] armBase = new Quaternion[0];
        private Collider[][] partColliders = new Collider[0][];
        private float shownHeight, shownSwing;
        // the van held by the server (or, on a client, its own copy held to the server's pose)
        private VanController heldVan;
        private Rigidbody heldBody;
        private bool wasKinematic;
        private RigidbodyInterpolation wasInterpolation;
        private GreyboxVanSeat heldSeat;
        private float seatDistance;
        private Vector3 restPos, padPos;
        private Quaternion restRot, padRot;
        private float align;
        private VanController van;
        private float nextVanSearch;
        private WorkshopStateBroadcast? view;
        private bool loadSnapDone;
        // MECHANIC_W86 v01: the upgrade performance, its deferred answer, who has the mechanic's conversation open
        // the aim waits up to 15 s for him to reach the lift box and face the van (he walks there as soon as the lift starts,
        // so he is normally there before anything can be selected)
        private readonly UpgradePerformance performance = new UpgradePerformance(UpgradePerformance.DefaultPoofSeconds, UpgradePerformance.DefaultClipSeconds, 15f);
        private bool deferReply;
        private string perfReplyKey;
        private NetworkConnection perfReplyTo;
        private Action<bool, string> perfLocalDone;
        private readonly Dictionary<string, float> talkers = new Dictionary<string, float>();
        private readonly List<string> talkerScratch = new List<string>();

        public LiftSession Session => session;
        /// <summary>Server: the mechanic's current upgrade performance (MECHANIC_W86 v01).</summary>
        public UpgradePerformance Performance => performance;
        /// <summary>Server: participants with the mechanic's conversation open.</summary>
        public int TalkerCount => talkers.Count;
        public bool IsTalking(string participant) => !string.IsNullOrEmpty(participant) && talkers.ContainsKey(participant);
        /// <summary>The centre of the van the lift holds (null when none).</summary>
        public Vector3? HeldVanCentre => heldVan != null ? heldVan.transform.TransformPoint(VanBodyBoundsOf(heldVan).center) : (Vector3?)null;
        /// <summary>Server, during a performance: the point on the held van he aims at and the puff appears on (chosen at
        /// its start with a clear sight line from his service point).</summary>
        public Vector3? AimPoint => performance.Busy && heldVan != null && aimSet ? heldVan.transform.TransformPoint(aimLocal) : (Vector3?)null;
        private Vector3 aimLocal, aimOutwardLocal;
        private bool aimSet;
        public float Height => Authority ? session.Height : shownHeight;
        public float Travel => session.Travel;
        public LiftPhase Phase => session.Phase;
        public string Owner => session.Owner;

        public static bool Authority
        {
            get
            {
                NetworkManager nm = InstanceFinder.NetworkManager;
                return nm == null || nm.IsServerStarted || !nm.IsClientStarted;
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Instance = null;

        private void Awake()
        {
            session = new LiftSession(LiftTravel, LiftSeconds, ArmSwingSeconds);
            CacheParts();
        }

        private void OnEnable() => Instance = this;

        private void OnDisable()
        {
            Unbind();
            // a server stop / scene unload must not leave the van kinematic up in the air: put it back on the floor now
            if (heldVan != null) { session.Abort("shutdown"); ReleaseVan(true); }
            if (performance.Busy && performance.Cancel("shutdown")) Debug.Log("[WORKSHOP] shutdown during the mechanic's upgrade: cancelled before the poof, nothing charged", this);
            talkers.Clear();
            if (Instance == this) Instance = null;
        }

        private void CacheParts()
        {
            LiftParts ??= new Transform[0];
            LiftArms ??= new Transform[0];
            partBase = new Vector3[LiftParts.Length];
            partColliders = new Collider[LiftParts.Length][];
            for (int i = 0; i < LiftParts.Length; i++)
            {
                partBase[i] = LiftParts[i] != null ? LiftParts[i].localPosition : Vector3.zero;
                partColliders[i] = LiftParts[i] != null ? LiftParts[i].GetComponentsInChildren<Collider>(true) : new Collider[0];
            }
            armBase = new Quaternion[LiftArms.Length];
            for (int i = 0; i < LiftArms.Length; i++) armBase[i] = LiftArms[i] != null ? LiftArms[i].localRotation : Quaternion.identity;
        }

        // ================================================================== binding

        private void Bind()
        {
            NetworkManager nm = InstanceFinder.NetworkManager;
            if (nm == null || bound && nm == manager) return;
            Unbind();
            manager = nm;
            manager.ServerManager.RegisterBroadcast<WorkshopRequestBroadcast>(OnServerRequest);
            manager.ClientManager.RegisterBroadcast<WorkshopResultBroadcast>(OnClientResult);
            manager.ClientManager.RegisterBroadcast<WorkshopStateBroadcast>(OnClientState);
            manager.ClientManager.RegisterBroadcast<WorkshopPuffBroadcast>(OnClientPuff);
            manager.ClientManager.OnClientConnectionState += OnClientConnection;
            manager.ServerManager.OnServerConnectionState += OnServerConnection;
            bound = true;
            if (manager.IsClientStarted && !manager.IsServerStarted) SendHello();
        }

        private void Unbind()
        {
            if (!bound || manager == null) { bound = false; return; }
            manager.ServerManager.UnregisterBroadcast<WorkshopRequestBroadcast>(OnServerRequest);
            manager.ClientManager.UnregisterBroadcast<WorkshopResultBroadcast>(OnClientResult);
            manager.ClientManager.UnregisterBroadcast<WorkshopStateBroadcast>(OnClientState);
            manager.ClientManager.UnregisterBroadcast<WorkshopPuffBroadcast>(OnClientPuff);
            manager.ClientManager.OnClientConnectionState -= OnClientConnection;
            manager.ServerManager.OnServerConnectionState -= OnServerConnection;
            bound = false;
        }

        private void OnClientConnection(ClientConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started && manager != null && !manager.IsServerStarted) SendHello();
            if (args.ConnectionState == LocalConnectionState.Stopped && !Authority) { view = null; if (heldVan != null) ReleaseVan(false); }
        }

        private void OnServerConnection(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Stopped && heldVan != null) { session.Abort("server stopped"); ReleaseVan(true); }
            if (args.ConnectionState == LocalConnectionState.Stopped)
            {
                if (performance.Busy) performance.Cancel("server stopped");
                talkers.Clear();
            }
        }

        private void SendHello()
        {
            if (manager != null && manager.IsClientStarted)
                manager.ClientManager.Broadcast(new WorkshopRequestBroadcast { Kind = (byte)WorkshopRequestKind.Hello, Key = "", Arg = "" });
        }

        // ================================================================== requests (any machine)

        /// <summary>This machine's participant id as the server sees it (the session owner check of the screen).</summary>
        public static string LocalParticipant => TeamEconomy.Instance != null ? TeamEconomy.Instance.LocalParticipantId : TeamEconomy.HostParticipant;

        public bool MineSession => session.Active && session.Owner == LocalParticipant;

        public string Request(WorkshopRequestKind kind, string arg, int expected, Action<bool, string> done)
        {
            Bind();
            string key = Guid.NewGuid().ToString("N");
            var m = new WorkshopRequestBroadcast { Kind = (byte)kind, Key = key, Arg = arg ?? "", Expected = expected };
            if (Authority)
            {
                deferReply = false;
                (bool ok, string text) = Process(m, manager != null ? manager.ClientManager.Connection : null);
                if (deferReply)
                {
                    // answered at the performance's Poof (or its cancel), like a remote client's request
                    deferReply = false;
                    perfReplyKey = key;
                    perfReplyTo = null;
                    perfLocalDone = done ?? ((_, __) => { });
                }
                else done?.Invoke(ok, text);
            }
            else if (manager != null && manager.IsClientStarted)
            {
                if (done != null) pending[key] = done;
                manager.ClientManager.Broadcast(m);
            }
            else done?.Invoke(false, "Нет связи с хостом");
            return key;
        }

        private void OnServerRequest(NetworkConnection connection, WorkshopRequestBroadcast m, Channel channel)
        {
            if (connection == null || !connection.IsActive) return;
            if (m.Kind == (byte)WorkshopRequestKind.Hello)
            {
                SendState(connection);
                WorkshopMechanicBrainV01.Instance?.SendStateTo(connection); // the mechanic's current action (no replayed puffs)
                return;
            }
            deferReply = false;
            (bool ok, string text) = Process(m, connection);
            if (deferReply)
            {
                deferReply = false;
                perfReplyKey = m.Key;
                perfReplyTo = connection;
                perfLocalDone = null;
                return;
            }
            manager.ServerManager.Broadcast(connection, new WorkshopResultBroadcast { Key = m.Key, Ok = ok, Message = text });
        }

        private void OnClientResult(WorkshopResultBroadcast r, Channel channel)
        {
            if (Authority) return;
            if (r.Key != null && pending.TryGetValue(r.Key, out Action<bool, string> done))
            {
                pending.Remove(r.Key);
                try { done(r.Ok, r.Message); } catch (Exception e) { Debug.LogException(e, this); }
            }
        }

        // ================================================================== server

        private (bool, string) Process(WorkshopRequestBroadcast m, NetworkConnection from)
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) return (false, "Экономика не запущена");
            if (string.IsNullOrEmpty(m.Key) || m.Key.Length > 64 || (m.Arg != null && m.Arg.Length > 64)) return (false, "Неверный запрос");
            string who = economy.ServerParticipantId(from);
            switch ((WorkshopRequestKind)m.Kind)
            {
                case WorkshopRequestKind.Start:
                {
                    LiftStartCheck check = Measure(economy, from);
                    bool reopen = session.Active && session.Owner == who;
                    WorkshopRefusal r = session.TryStart(who, check);
                    if (r != WorkshopRefusal.None)
                    {
                        Debug.Log($"[WORKSHOP] lift start by {who} refused: {r} (zone {check.VanInZone}, aligned {check.VanAligned}, stopped {check.VanStopped}, driven {check.SomeoneDriving}, in the way {check.BodyInWay}, near {check.ActorNear})", this);
                        return (false, WorkshopRules.Explain(r));
                    }
                    if (reopen) return (true, session.Phase == LiftPhase.Up ? "Бусик на подъёмнике" : "Поднимаю…");
                    AttachVan(van);
                    Debug.Log($"[WORKSHOP] lift session of {who}: arms in ({session.SwingSeconds:0.#} s), raising the van {van.name} ({session.Travel:0.##} m in {session.Seconds:0.#} s)", this);
                    Push(true);
                    return (true, "Механик поднимает бусик…");
                }
                case WorkshopRequestKind.Done:
                {
                    WorkshopRefusal r = session.Finish(who);
                    if (r != WorkshopRefusal.None) return (false, WorkshopRules.Explain(r));
                    Debug.Log($"[WORKSHOP] lift session of {who}: done, lowering", this);
                    Push(true);
                    return (true, "Опускаю бусик");
                }
                case WorkshopRequestKind.Buy:
                    return Buy(economy, who, m.Arg, m.Expected);
                case WorkshopRequestKind.Talk:
                {
                    if (m.Arg == "1") talkers[who] = Time.unscaledTime;
                    else talkers.Remove(who);
                    return (true, "");
                }
                default:
                    return (false, "Неверный запрос");
            }
        }

        /// <summary>A selected upgrade: validated now (nothing charged), then performed by the mechanic; the purchase itself
        /// is committed at the performance's Poof (<see cref="TickPerformance"/>) and the request is answered then.</summary>
        private (bool, string) Buy(TeamEconomy economy, string who, string arg, int expected)
        {
            if (!economy.ServerReady) return (false, PurchaseResult.Explain(PurchaseError.NotReady));
            string[] parts = (arg ?? "").Split('|');
            if (parts.Length != 2) return (false, "Неверный запрос");
            if (parts[0] == WorkshopUpgradeRows.VanBranchKind)
            {
                if (!int.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out int b) || b < 0 || b > 2) return (false, "Неверный запрос");
                if (performance.Busy) return (false, WorkshopRules.Explain(WorkshopRefusal.MechanicBusy)); // a repeated click
                PurchaseResult preview = WorkshopUpgradePreview.VanTier(economy.ServerState, session, who, (VanBranch)b, expected, VanInZone());
                if (!preview.Ok || preview.Replayed)
                {
                    Debug.Log($"[WORKSHOP] {who} selects {(VanBranch)b} tier {expected}: {(preview.Replayed ? "already bought (replay, no performance)" : "refused " + preview.Error + " " + preview.Message)}", this);
                    return (preview.Ok, preview.Message);
                }
                WorkshopRefusal r = performance.TryBegin(who, parts[0], parts[1], expected);
                if (r != WorkshopRefusal.None) return (false, WorkshopRules.Explain(r));
                ChooseAim();
                deferReply = true;
                Debug.Log($"[WORKSHOP] {who} selects {(VanBranch)b} tier {expected} (${preview.Price}): valid, the mechanic performs it (commit at the poof, {performance.PoofSeconds:0.00} s into the clip)", this);
                return (true, "Механик берётся за дело…");
            }
            if (parts[0] == WorkshopUpgradeRows.VanCargoKind)
            {
                // cargo body (Fedya 29.10): the same pipeline, Expected = the price shown, Arg = the catalogue id
                string id = parts[1];
                if (!VanCargo.IsKnown(id)) return (false, "Неверный запрос");
                if (performance.Busy) return (false, WorkshopRules.Explain(WorkshopRefusal.MechanicBusy));
                PurchaseResult preview = WorkshopUpgradePreview.CargoUpgrade(economy.ServerState, session, who, id, expected, VanInZone());
                if (!preview.Ok || preview.Replayed)
                {
                    Debug.Log($"[WORKSHOP] {who} selects cargo {id} (${expected}): {(preview.Replayed ? "already bought (replay, no performance)" : "refused " + preview.Error + " " + preview.Message)}", this);
                    return (preview.Ok, preview.Message);
                }
                WorkshopRefusal r = performance.TryBegin(who, parts[0], id, expected);
                if (r != WorkshopRefusal.None) return (false, WorkshopRules.Explain(r));
                ChooseAim();
                deferReply = true;
                Debug.Log($"[WORKSHOP] {who} selects cargo {id} (${preview.Price}): valid, the mechanic performs it (commit at the poof, {performance.PoofSeconds:0.00} s into the clip)", this);
                return (true, "Механик берётся за дело…");
            }
            return (false, "Это улучшение пока не продаётся");
        }

        private bool VanInZone() => heldVan != null && (Zone == null || Zone.Contains(padPos + Vector3.up * 0.8f));

        /// <summary>Server, every physics step: the performance's clock (MECHANIC_W86 v01). The commit runs once, at the
        /// Poof, through the same purchase rules (WorkshopRules.TryBuyVanTier: session, unlock, zone, tier order, funds,
        /// deterministic key); its result is the answer to the buyer's request.</summary>
        private void TickPerformance(TeamEconomy economy, float dt)
        {
            if (!performance.Busy) return;
            bool ownerHere = economy != null && economy.IsServer && economy.ServerConnectionOf(performance.Owner) != null;
            bool valid = ownerHere && session.Active && session.Owner == performance.Owner && session.Phase == LiftPhase.Up && heldVan != null;
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            bool facing = brain == null || !brain.HasBody || brain.FacingVan;
            UpgradeCue cue = performance.Tick(dt, valid, facing, () => CommitPerformance(economy));
            switch (cue)
            {
                case UpgradeCue.Begin:
                    Debug.Log($"[WORKSHOP] the mechanic aims at the van ({performance.Kind}|{performance.Arg} tier {performance.Expected} for {performance.Owner})", this);
                    break;
                case UpgradeCue.Poof:
                    Puff();
                    ReplyPerformance(true, performance.Result.Message);
                    break;
                case UpgradeCue.Failed:
                    ReplyPerformance(false, string.IsNullOrEmpty(performance.Result?.Message) ? "Не вышло — ничего не списано" : performance.Result.Message);
                    break;
                case UpgradeCue.Cancelled:
                    Debug.Log($"[WORKSHOP] upgrade performance for {performance.Owner} cancelled before the poof ({performance.LastEnd}): nothing charged", this);
                    ReplyPerformance(false, "Механик опустил ключ: покупка отменена, деньги не списаны");
                    break;
            }
        }

        private PurchaseResult CommitPerformance(TeamEconomy economy)
        {
            try
            {
                if (economy == null || !economy.ServerReady) return new PurchaseResult { Ok = false, Error = PurchaseError.NotReady, Message = PurchaseResult.Explain(PurchaseError.NotReady) };
                if (performance.Kind == WorkshopUpgradeRows.VanBranchKind &&
                    int.TryParse(performance.Arg, NumberStyles.Integer, CultureInfo.InvariantCulture, out int b) && b >= 0 && b <= 2)
                {
                    PurchaseResult r = WorkshopRules.TryBuyVanTier(economy.ServerState, session, performance.Owner, (VanBranch)b, performance.Expected, VanInZone());
                    Debug.Log($"[WORKSHOP] POOF: {performance.Owner} buys {(VanBranch)b} tier {performance.Expected} on the lift: {(r.Ok ? (r.Replayed ? "replayed (no puff)" : "PAID $" + r.Price + ", applied") : "refused " + r.Error + " " + r.Message)}; fund ${economy.ServerState.Fund.Balance}", this);
                    return r;
                }
                if (performance.Kind == WorkshopUpgradeRows.VanCargoKind && VanCargo.IsKnown(performance.Arg))
                {
                    PurchaseResult r = WorkshopRules.TryBuyVanCargo(economy.ServerState, session, performance.Owner, performance.Arg, performance.Expected, VanInZone());
                    Debug.Log($"[WORKSHOP] POOF: {performance.Owner} buys cargo {performance.Arg} (${performance.Expected}) on the lift: {(r.Ok ? (r.Replayed ? "replayed (no puff)" : "PAID $" + r.Price + ", applied") : "refused " + r.Error + " " + r.Message)}; fund ${economy.ServerState.Fund.Balance}", this);
                    return r;
                }
                return new PurchaseResult { Ok = false, Error = PurchaseError.ItemUnavailable, Message = "Это улучшение пока не продаётся" };
            }
            catch (Exception e)
            {
                Debug.LogException(e, this);
                return null;
            }
        }

        private void ReplyPerformance(bool ok, string text)
        {
            string key = perfReplyKey;
            NetworkConnection to = perfReplyTo;
            Action<bool, string> local = perfLocalDone;
            perfReplyKey = null;
            perfReplyTo = null;
            perfLocalDone = null;
            if (string.IsNullOrEmpty(key)) return;
            if (local != null)
            {
                try { local(ok, text); } catch (Exception e) { Debug.LogException(e, this); }
            }
            else if (to != null && to.IsActive && manager != null && manager.IsServerStarted)
                manager.ServerManager.Broadcast(to, new WorkshopResultBroadcast { Key = key, Ok = ok, Message = text });
        }

        /// <summary>Where on the held van he aims and the puff appears: the side facing his service point, the nearest spot
        /// along it with a clear line from his eyes (the lift post stands right beside him).</summary>
        private void ChooseAim()
        {
            aimSet = false;
            if (heldVan == null) return;
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            Vector3 from = brain != null && brain.ServicePosition.HasValue ? brain.ServicePosition.Value
                : ControlPoint != null ? ControlPoint.position : brain != null && brain.HasBody ? brain.BodyPosition : transform.position;
            ClearAimPoint(heldVan, from, brain != null ? brain.Body : null, out Vector3 at, out Vector3 outward);
            aimLocal = heldVan.transform.InverseTransformPoint(at);
            aimOutwardLocal = heldVan.transform.InverseTransformDirection(outward);
            aimSet = true;
        }

        /// <summary>The puff point on the van's side facing 'from' with a clear sight line from 1.5 m above it (tries the
        /// nearest spot, then a little further along the side each way).</summary>
        public static void ClearAimPoint(VanController v, Vector3 from, Transform ignore, out Vector3 at, out Vector3 outward)
        {
            PuffPoint(v, from, out at, out outward);
            Transform t = v.transform;
            Bounds b = VanBodyBoundsOf(v);
            Vector3 eye = from + Vector3.up * 1.5f;
            Vector3 l = t.InverseTransformPoint(at);
            foreach (float o in new[] { 0f, 0.7f, -0.7f, 1.2f, -1.2f, 1.7f, -1.7f })
            {
                float z = Mathf.Clamp(l.z + o, b.min.z + 0.35f, b.max.z - 0.35f);
                Vector3 p = t.TransformPoint(new Vector3(l.x, l.y, z));
                if (SightTo(eye, p, t, ignore)) { at = p; return; }
            }
        }

        private static readonly RaycastHit[] sightHits = new RaycastHit[16];

        private static bool SightTo(Vector3 eye, Vector3 p, Transform van, Transform ignore)
        {
            Vector3 d = p - eye;
            float len = d.magnitude;
            if (len < 0.05f) return true;
            int n = Physics.RaycastNonAlloc(eye, d / len, sightHits, len, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                Transform h = sightHits[i].collider != null ? sightHits[i].collider.transform : null;
                if (h == null || h.IsChildOf(van) || ignore != null && h.IsChildOf(ignore)) continue;
                return false;
            }
            return true;
        }

        /// <summary>The cartoon puff on the side of the held van that faces the mechanic (its renderers' bounds, so a
        /// redesigned van body works too): on this machine and, as a one-shot cue, on every connected client.</summary>
        private void Puff()
        {
            if (heldVan == null) return;
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            Vector3 at, outward;
            if (aimSet) { at = heldVan.transform.TransformPoint(aimLocal); outward = heldVan.transform.TransformDirection(aimOutwardLocal); }
            else
            {
                Vector3 from = brain != null && brain.HasBody ? brain.BodyPosition : ControlPoint != null ? ControlPoint.position : transform.position;
                PuffPoint(heldVan, from, out at, out outward);
            }
            WorkshopPuffFxV01.Spawn(at, outward, brain != null ? brain.PuffMaterial : null);
            if (manager == null || !manager.IsServerStarted) return;
            var cue = new WorkshopPuffBroadcast { Position = at, Outward = outward };
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && !c.IsLocalClient) manager.ServerManager.Broadcast(c, cue);
        }

        private void OnClientPuff(WorkshopPuffBroadcast p, Channel channel)
        {
            if (Authority) return;
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            WorkshopPuffFxV01.Spawn(p.Position, p.Outward, brain != null ? brain.PuffMaterial : null);
        }

        /// <summary>A point just outside the van's side nearest to 'from', at mid length and a little above mid height
        /// (from the van's renderers, so a redesigned van body works without new numbers).</summary>
        public static void PuffPoint(VanController v, Vector3 from, out Vector3 at, out Vector3 outward)
        {
            Transform t = v.transform;
            Bounds b = VanBodyBoundsOf(v);
            Vector3 lf = t.InverseTransformPoint(from);
            float side = lf.x >= b.center.x ? 1f : -1f;
            float z = Mathf.Clamp(lf.z, b.min.z + b.size.z * 0.3f, b.max.z - b.size.z * 0.3f);
            Vector3 local = new Vector3(side > 0f ? b.max.x : b.min.x, b.min.y + b.size.y * 0.55f, z);
            outward = t.TransformDirection(new Vector3(side, 0f, 0f)).normalized;
            at = t.TransformPoint(local) + outward * 0.12f;
        }

        /// <summary>The van's collider footprint in its own frame.</summary>
        public static Bounds VanLocalBoundsOf(VanController v) => VanLocalBounds(v);

        /// <summary>The van's visible body in its own frame, from each renderer's own mesh box (exact at any yaw; a world
        /// AABB of a turned van would be inflated). Falls back to the collider footprint.</summary>
        public static Bounds VanBodyBoundsOf(VanController v)
        {
            Transform t = v.transform;
            var b = new Bounds();
            bool any = false;
            foreach (Renderer r in v.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled || r is ParticleSystemRenderer || r is TrailRenderer || r is LineRenderer) continue;
                Bounds w = r.localBounds;
                for (int i = 0; i < 8; i++)
                {
                    Vector3 corner = new Vector3((i & 1) == 0 ? w.min.x : w.max.x, (i & 2) == 0 ? w.min.y : w.max.y, (i & 4) == 0 ? w.min.z : w.max.z);
                    Vector3 l = t.InverseTransformPoint(r.transform.TransformPoint(corner));
                    if (!any) { b = new Bounds(l, Vector3.zero); any = true; } else b.Encapsulate(l);
                }
            }
            return any ? b : VanLocalBounds(v);
        }

        /// <summary>The server's own measurement for a lift start.</summary>
        private LiftStartCheck Measure(TeamEconomy economy, NetworkConnection from)
        {
            var c = new LiftStartCheck { Ready = economy.ServerReady, WorkshopUnlocked = economy.ServerState != null && economy.ServerState.WorkshopUnlocked };
            Vector3? actor = TeamEconomy.ServerActorPosition(from);
            Vector3 mech = Mechanic != null ? Mechanic.position : transform.position;
            // the mechanic walks his route now (MECHANIC_W86 v01): near his body counts as well as near his anchor
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            // (29.10) near his body: the same reach as his conversation menu (MechanicTalkReach), so "Улучшить бусик" chosen in
            // the open menu is never refused for distance
            Vector3 toBody = actor.HasValue && brain != null && brain.HasBody ? actor.Value - brain.BodyPosition : Vector3.positiveInfinity;
            c.ActorNear = actor.HasValue && ((actor.Value - mech).sqrMagnitude <= MechanicReach * MechanicReach ||
                                             brain != null && brain.HasBody && MechanicTalkReach.ServerAccepts(toBody.x, toBody.y, toBody.z));
            VanController v = FindVan();
            if (v == null) return c;
            c.VanFound = true;
            Rigidbody body = v.GetComponent<Rigidbody>();
            Vector3 centre = body != null ? body.worldCenterOfMass : v.transform.position;
            c.VanInZone = Zone == null ? Vector3.Distance(centre, VanPark != null ? VanPark.position : transform.position) < 3f : Zone.Contains(centre);
            c.VanAligned = Aligned(v, out _, out _);
            c.VanStopped = Mathf.Abs(v.SpeedKmh) < 1.5f && (body == null || body.linearVelocity.magnitude < 0.4f);
            var seat = v.GetComponent<GreyboxVanSeat>();
            c.SomeoneDriving = seat != null && seat.Driving;
            c.BodyInWay = BodyInWay(v, 0f);
            return c;
        }

        private VanController FindVan()
        {
            if (van == null && Time.unscaledTime >= nextVanSearch)
            {
                van = FindAnyObjectByType<VanController>();
                nextVanSearch = Time.unscaledTime + 2f;
            }
            return van;
        }

        /// <summary>The van over the pads within the tolerance (either way round); the pad pose it settles onto.</summary>
        private bool Aligned(VanController v, out Vector3 pad, out Quaternion rot)
        {
            Transform park = VanPark != null ? VanPark : transform;
            Vector3 local = park.InverseTransformPoint(v.transform.position);
            float yaw = Mathf.DeltaAngle(park.eulerAngles.y, v.transform.eulerAngles.y);
            bool reversed = Mathf.Abs(yaw) > 90f;
            float yawOff = reversed ? Mathf.DeltaAngle(180f, yaw) : yaw;
            rot = Quaternion.Euler(0f, park.eulerAngles.y + (reversed ? 180f : 0f), 0f);
            pad = new Vector3(park.position.x, v.transform.position.y, park.position.z);
            return Mathf.Abs(local.x) <= PadTolerance.x && Mathf.Abs(local.z) <= PadTolerance.y && Mathf.Abs(yawOff) <= PadTolerance.z;
        }

        private void AttachVan(VanController v)
        {
            if (v == null) return;
            heldVan = v;
            heldBody = v.GetComponent<Rigidbody>();
            heldSeat = v.GetComponent<GreyboxVanSeat>();
            restPos = heldBody != null ? heldBody.position : v.transform.position;
            restRot = heldBody != null ? heldBody.rotation : v.transform.rotation;
            Aligned(v, out padPos, out padRot);
            padPos.y = restPos.y;
            align = 0f;
            if (heldBody != null)
            {
                wasKinematic = heldBody.isKinematic;
                wasInterpolation = heldBody.interpolation;
                heldBody.linearVelocity = Vector3.zero;
                heldBody.angularVelocity = Vector3.zero;
                heldBody.isKinematic = true;
                heldBody.interpolation = RigidbodyInterpolation.Interpolate;
            }
            v.Throttle = 0f;
            v.Handbrake = true;
            // nobody gets in while it is on the lift (the seat's own reach check refuses everyone)
            if (heldSeat != null) { seatDistance = heldSeat.EnterDistance; heldSeat.EnterDistance = -1f; }
        }

        /// <summary>The van's physics back (lowered: as it stands; atOnce = a stop / unload: straight down onto the pads).</summary>
        private void ReleaseVan(bool atOnce)
        {
            if (heldVan == null) return;
            if (atOnce && heldBody != null && Authority)
            {
                heldBody.position = padPos;
                heldBody.rotation = padRot;
                heldVan.transform.SetPositionAndRotation(padPos, padRot);
            }
            if (heldBody != null)
            {
                heldBody.isKinematic = wasKinematic;
                heldBody.interpolation = wasInterpolation;
                if (!wasKinematic) { heldBody.linearVelocity = Vector3.zero; heldBody.angularVelocity = Vector3.zero; }
            }
            if (heldSeat != null && heldSeat.EnterDistance < 0f) heldSeat.EnterDistance = seatDistance > 0f ? seatDistance : 3.5f;
            heldVan.Handbrake = true;
            Debug.Log($"[WORKSHOP] van {heldVan.name} back on its wheels{(atOnce ? " (set down at once)" : "")}", this);
            heldVan = null; heldBody = null; heldSeat = null;
            SetPartColliders(true);
        }

        /// <summary>A player or a free NPC where the van and the lift arms move (the van's footprint + a body radius, from
        /// below the floor to above the roof).</summary>
        private bool BodyInWay(VanController v, float height)
        {
            if (v == null) return false;
            Transform t = v.transform;
            Bounds local = VanLocalBounds(v);
            local.Expand(new Vector3(0.9f, 0f, 0.9f));
            float floor = (VanPark != null ? VanPark.position.y : t.position.y) - 0.4f;
            float top = floor + height + local.size.y + 2.4f;
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy != null && economy.IsServer) economy.ServerPlayerPositions(players);
            else players.Clear();
            foreach (Vector3 p in players) if (Inside(t, local, p, floor, top)) return true;
            foreach (GreyboxNpc n in GreyboxNpc.All)
                if (n != null && n.isActiveAndEnabled && !n.InCargo && Inside(t, local, n.transform.position, floor, top)) return true;
            return false;
        }

        private static bool Inside(Transform t, Bounds local, Vector3 world, float floor, float top)
        {
            if (world.y < floor - 0.5f || world.y > top) return false;
            Vector3 p = t.InverseTransformPoint(world);
            return Mathf.Abs(p.x - local.center.x) <= local.extents.x && Mathf.Abs(p.z - local.center.z) <= local.extents.z;
        }

        private static Bounds VanLocalBounds(VanController v)
        {
            var b = new Bounds(new Vector3(0f, 1.2f, 0f), new Vector3(2.0f, 2.4f, 5.2f));
            bool any = false;
            foreach (Collider c in v.GetComponentsInChildren<Collider>())
            {
                if (c.isTrigger || c is WheelCollider) continue;
                Bounds w = c.bounds;
                for (int i = 0; i < 8; i++)
                {
                    Vector3 corner = new Vector3((i & 1) == 0 ? w.min.x : w.max.x, (i & 2) == 0 ? w.min.y : w.max.y, (i & 4) == 0 ? w.min.z : w.max.z);
                    Vector3 l = v.transform.InverseTransformPoint(corner);
                    if (!any) { b = new Bounds(l, Vector3.zero); any = true; } else b.Encapsulate(l);
                }
            }
            return b;
        }

        private void Update()
        {
            Bind();
            if (!Authority) ClientView();
        }

        private void FixedUpdate()
        {
            if (!Authority) return;
            TeamEconomy economy = TeamEconomy.Instance;
            TickPerformance(economy, Time.fixedDeltaTime);
            PruneTalkers(economy);
            if (session.Active && economy != null && economy.IsServer)
            {
                // the owner gone (disconnected) or walked off: down by itself, nothing is bought on the way
                if (economy.ServerConnectionOf(session.Owner) == null) { session.Abort("owner disconnected"); Debug.Log("[WORKSHOP] session owner left the game: lowering the van", this); }
                else
                {
                    Vector3? at = TeamEconomy.ServerActorPosition(economy.ServerConnectionOf(session.Owner));
                    Vector3 zone = Zone != null ? Zone.transform.position : transform.position;
                    if (at.HasValue && (at.Value - zone).sqrMagnitude > OwnerLeash * OwnerLeash && session.Phase != LiftPhase.Lowering)
                    { session.Abort("owner walked away"); Debug.Log("[WORKSHOP] session owner walked away: lowering the van", this); }
                }
            }
            if (session.HoldsVan && heldVan == null)
            {
                // a session without a van (it was removed): end it without moving anything
                session.Abort("van gone");
                while (session.HoldsVan) session.Tick(1f, false);
            }
            if (heldVan != null)
            {
                bool blocked = BodyInWay(heldVan, session.Height);
                bool changed = session.Tick(Time.fixedDeltaTime, blocked);
                float h = session.Height;
                // the van is set exactly onto the park point first (the arms pass 5 cm from the tyres), then rides up
                align = Mathf.Max(align, Mathf.Clamp01(session.Swing * 2.5f));
                Vector3 pos = Vector3.Lerp(restPos, padPos, align) + Vector3.up * h;
                Quaternion rot = Quaternion.Slerp(restRot, padRot, align);
                if (heldBody != null) { heldBody.MovePosition(pos); heldBody.MoveRotation(rot); }
                else heldVan.transform.SetPositionAndRotation(pos, rot);
                Parts(h, session.Swing, session.Phase == LiftPhase.Raising || session.Phase == LiftPhase.Lowering);
                if (changed) { Debug.Log($"[WORKSHOP] lift {session.Phase} (height {h:0.00} m)", this); Push(true); }
                if (!session.HoldsVan) ReleaseVan(false);
            }
            else Parts(session.Height, session.Swing, false);
            AfterLoadSnap();
            Push(false);
        }

        /// <summary>Talkers whose connection is gone (disconnect without closing the menu) stop counting.</summary>
        private void PruneTalkers(TeamEconomy economy)
        {
            if (talkers.Count == 0) return;
            if (economy == null || !economy.IsServer) { talkers.Clear(); return; }
            talkerScratch.Clear();
            foreach (string id in talkers.Keys) if (economy.ServerConnectionOf(id) == null) talkerScratch.Add(id);
            foreach (string id in talkerScratch) talkers.Remove(id);
        }

        /// <summary>A save written while the van was up stores it 1.6 m above the pads: right after the load it is set down
        /// onto them (once, before it can fall), so it never drops from the lift height.</summary>
        private void AfterLoadSnap()
        {
            if (loadSnapDone) return;
            var capture = OnlyVolunteers.Capture.CaptureDirector.Instance;
            if (capture != null && !capture.Loaded) return;
            loadSnapDone = true;
            VanController v = FindAnyObjectByType<VanController>();
            if (v == null || session.HoldsVan || VanPark == null) return;
            Rigidbody body = v.GetComponent<Rigidbody>();
            Vector3 centre = body != null ? body.worldCenterOfMass : v.transform.position;
            float above = v.transform.position.y - VanPark.position.y;
            if (Zone == null || !Zone.Contains(centre - Vector3.up * Mathf.Max(0f, above)) || above < 0.5f || above > 2.4f) return;
            Vector3 p = new Vector3(v.transform.position.x, VanPark.position.y + 0.05f, v.transform.position.z);
            if (body != null) { body.position = p; body.linearVelocity = Vector3.zero; body.angularVelocity = Vector3.zero; }
            v.transform.position = p;
            Debug.Log($"[WORKSHOP] the save had the van {above:0.00} m up on the lift: set down onto the pads", this);
        }

        private void Parts(float h, float swing, bool moving)
        {
            if (LiftParts.Length != partBase.Length || LiftArms.Length != armBase.Length) CacheParts();
            for (int i = 0; i < LiftParts.Length; i++)
                if (LiftParts[i] != null) LiftParts[i].localPosition = partBase[i] + Vector3.up * h;
            for (int i = 0; i < LiftArms.Length; i++)
                if (LiftArms[i] != null)
                    LiftArms[i].localRotation = armBase[i] * Quaternion.Euler(0f, (i < ArmEngagedYaw.Length ? ArmEngagedYaw[i] : 0f) * Mathf.SmoothStep(0f, 1f, swing), 0f);
            // moving colliders never push or lift a player: off while anything moves, back at rest
            SetPartColliders(!moving);
        }

        private bool partCollidersOn = true;

        private void SetPartColliders(bool on)
        {
            if (partCollidersOn == on) return;
            partCollidersOn = on;
            foreach (Collider[] cs in partColliders)
                if (cs != null) foreach (Collider c in cs) if (c != null) c.enabled = on;
        }

        private void Push(bool now)
        {
            if (manager == null || !manager.IsServerStarted) return;
            float t = Time.unscaledTime;
            bool moving = session.Phase == LiftPhase.Raising || session.Phase == LiftPhase.Lowering;
            string sig = session.Phase + "|" + session.Owner + "|" + (heldVan != null);
            bool changed = sig != lastSignature;
            if (!(now || changed || moving && t >= nextPush || t >= nextBeat)) return;
            lastSignature = sig;
            nextPush = t + 0.1f;
            nextBeat = t + 1f;
            if (manager.ServerManager.Clients.Count <= 1) return;
            WorkshopStateBroadcast s = Snapshot();
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && !c.IsLocalClient) manager.ServerManager.Broadcast(c, s);
        }

        private WorkshopStateBroadcast Snapshot()
        {
            var s = new WorkshopStateBroadcast { Seq = ++seq, Phase = (byte)session.Phase, Height = session.Height, Swing = session.Swing, Owner = session.Owner, VanHeld = heldVan != null, VanRotation = Quaternion.identity };
            if (heldVan != null) { s.VanPosition = heldVan.transform.position; s.VanRotation = heldVan.transform.rotation; }
            return s;
        }

        private void SendState(NetworkConnection c)
        {
            if (manager == null || c == null || !c.IsActive) return;
            manager.ServerManager.Broadcast(c, Snapshot());
        }

        // ================================================================== client view

        private void OnClientState(WorkshopStateBroadcast s, Channel channel)
        {
            if (Authority) return;
            if (view.HasValue && s.Seq != 0 && s.Seq < view.Value.Seq && view.Value.Seq - s.Seq < 1000000) return;
            view = s;
            session.Set((LiftPhase)s.Phase, s.Height, s.Swing, s.Owner);
        }

        private void ClientView()
        {
            if (!view.HasValue) return;
            WorkshopStateBroadcast s = view.Value;
            float k = 1f - Mathf.Exp(-10f * Time.deltaTime);
            shownHeight = Mathf.Lerp(shownHeight, s.Height, k);
            shownSwing = Mathf.Lerp(shownSwing, s.Swing, k);
            Parts(shownHeight, shownSwing, s.Phase == (byte)LiftPhase.Raising || s.Phase == (byte)LiftPhase.Lowering);
            // this machine's own copy of the team van follows the server's (the map van is not a network object yet)
            if (s.VanHeld)
            {
                VanController v = FindVan();
                if (v == null) return;
                if (heldVan != v) AttachVan(v);
                Vector3 p = Vector3.Lerp(v.transform.position, s.VanPosition, k);
                Quaternion r = Quaternion.Slerp(v.transform.rotation, s.VanRotation, k);
                if (heldBody != null) { heldBody.MovePosition(p); heldBody.MoveRotation(r); } else v.transform.SetPositionAndRotation(p, r);
            }
            else if (heldVan != null) ReleaseVan(false);
        }
    }
}
