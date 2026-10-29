using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Sky22V04;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// The team economy service of a FishNet session (ECONOMY_SALES_PROGRESSION_SPEC v01 §3.1, §10): ONE host-authoritative
    /// shared fund with its history, the paid van tiers, story / workshop flags, owned bases and equipment deliveries
    /// (EconomyState, pure rules). Host = server: single player is the same code path.
    ///
    /// Networking uses FishNet broadcasts, not a NetworkObject: no prefab has to be registered in the scenes' manual
    /// spawnable lists (the map uses OperationSpawnables_v02) and no scene is edited. Clients send intents
    /// (EconomyRequestBroadcast, never an amount); the server commits in order and answers the requester; every commit
    /// sends all clients a JSON snapshot (EconomyClientView), a joining client asks for one (Hello).
    ///
    /// Created by the session owner when its server starts (CaptureDirector on the map, NetworkSession in the network
    /// test); the save owner restores / migrates it (ServerLoad) and writes it (ServerSaveBlock) on ServerCommitted.
    /// </summary>
    [DefaultExecutionOrder(-150)]
    public sealed class TeamEconomy : MonoBehaviour
    {
        private const int SnapshotLines = 40;
        /// <summary>No sky clock in the scene: a game day = 45 real minutes (§7.2).</summary>
        private const float FallbackSecondsPerGameHour = 45f * 60f / 24f;
        /// <summary>A bigger jump of the sky clock in one frame is a set / scrub (a load, F12), not time passing.</summary>
        private const float MaxClockStepHours = 0.25f;

        public static TeamEconomy Instance { get; private set; }
        /// <summary>Server: a commit happened. The save owner writes the team save now (an economic commit is not left
        /// for the autosave, §10.4). Raised one frame after the commit, so goods despawned by a sale are gone.</summary>
        public static event Action ServerCommitted;
        /// <summary>Server: a short world message (delivery arrived / waits) for the HUD.</summary>
        public static event Action<string> Notice;
        /// <summary>Server: handles the story / capture-side request kinds (StoryMechanic, StoryMeetOrganBuyer, StoryC01Sale and
        /// the capture DEV aids). Set by the story runtime (OnlyVolunteers.Story.StoryDirector) of this session; the
        /// connection is the requester (host requests: the host's own client connection), the state is the server state.</summary>
        public static Func<EconomyRequestBroadcast, NetworkConnection, EconomyState, (bool ok, string text)> StoryHandler;

        private NetworkManager manager;
        private EconomyState state;
        private bool ready;
        private bool dirty;
        private int saveFrame = -1;
        private float nextDeliveryCheck;
        private float nextLocalPush;
        private float nextRemotePush;
        private float lastClockHour = -1f;
        private SkyClock22 clock;
        private float nextClockSearch;
        private VanController van;
        private float nextVanSearch;
        private string appliedVan = "";
        private readonly Dictionary<string, Action<bool, string>> pending = new Dictionary<string, Action<bool, string>>();
        private readonly Dictionary<string, GameObject> worldObjects = new Dictionary<string, GameObject>();

        public bool IsServer => manager != null && manager.IsServerStarted;
        public bool ServerReady => IsServer && state != null && ready;
        /// <summary>Server only (null elsewhere).</summary>
        public EconomyState ServerState => IsServer ? state : null;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Instance = null;
            ServerCommitted = null;
            Notice = null;
            StoryHandler = null;
            EconomyClientView.ResetForPlay();
            EconomyServerHooks.ResetForPlay();
        }

        /// <summary>The economy of this NetworkManager (made once; a new manager, e.g. after a scene reload, gets a new one).</summary>
        public static TeamEconomy Ensure(NetworkManager networkManager)
        {
            if (networkManager == null) return null;
            if (Instance != null && Instance.manager == networkManager) return Instance;
            if (Instance != null) Destroy(Instance.gameObject);
            // The ONE price source (G48 catalogue) is bound before anything quotes, sells or buys (ECONOMY §10.4).
            EconomyCatalogSource.Ensure();
            var go = new GameObject("[Economy] Team fund");
            var economy = go.AddComponent<TeamEconomy>();
            go.AddComponent<WorkshopPrompt>();
            go.AddComponent<OnlyVolunteers.Story.StoryDirector>();
            Instance = economy;
            economy.Bind(networkManager);
            return economy;
        }

        private void Bind(NetworkManager networkManager)
        {
            manager = networkManager;
            manager.ServerManager.RegisterBroadcast<EconomyRequestBroadcast>(OnServerRequest);
            manager.ClientManager.RegisterBroadcast<EconomySnapshotBroadcast>(OnClientSnapshot);
            manager.ClientManager.RegisterBroadcast<EconomyResultBroadcast>(OnClientResult);
            manager.ServerManager.OnServerConnectionState += OnServerState;
            manager.ServerManager.OnRemoteConnectionState += OnRemoteState;
            manager.ClientManager.OnClientConnectionState += OnClientState;
            if (manager.IsClientStarted && !manager.IsServerStarted) SendHello();
        }

        private void OnDestroy()
        {
            if (manager != null)
            {
                manager.ServerManager.UnregisterBroadcast<EconomyRequestBroadcast>(OnServerRequest);
                manager.ClientManager.UnregisterBroadcast<EconomySnapshotBroadcast>(OnClientSnapshot);
                manager.ClientManager.UnregisterBroadcast<EconomyResultBroadcast>(OnClientResult);
                manager.ServerManager.OnServerConnectionState -= OnServerState;
                manager.ServerManager.OnRemoteConnectionState -= OnRemoteState;
                manager.ClientManager.OnClientConnectionState -= OnClientState;
            }
            DropServerState();
            if (Instance == this)
            {
                Instance = null;
                EconomyClientView.Set(null);
            }
        }

        // ---------- server lifecycle ----------

        /// <summary>Server start: a new-game state. waitForExternalLoad = a save owner will call ServerLoad or
        /// ServerMarkReady; until then purchases answer "loading" and sales wait (nothing is lost on the load).</summary>
        public void ServerBegin(bool waitForExternalLoad)
        {
            if (!IsServer) { Debug.LogWarning("[ECON] ServerBegin without a started server", this); return; }
            SetState(EconomyState.NewGame());
            ready = false;
            if (!waitForExternalLoad) BecomeReady("new game");
            else PushSnapshot(true);
        }

        /// <summary>No save to load (new game / fresh start): the new-game state becomes the team's state.</summary>
        public void ServerMarkReady()
        {
            if (!IsServer || state == null || ready) return;
            BecomeReady("new game");
        }

        /// <summary>The team save's economy block (null / blockVersion 0 = a save from before the shared fund: migrated
        /// once from the legacy host cash, §10.3). The migrated block is written back at once.</summary>
        public void ServerLoad(EconomySaveData block, bool legacyHasCash, int legacyCash)
        {
            if (!IsServer) { Debug.LogWarning("[ECON] ServerLoad without a started server", this); return; }
            bool migrated = !FundMigration.HasBlock(block);
            SetState(FundMigration.LoadOrMigrate(block, legacyHasCash, legacyCash));
            ready = false;
            appliedVan = "";
            RebuildWorldObjects();
            BecomeReady(migrated ? "migrated (" + state.MigrationSource + ", legacy cash " + (legacyHasCash ? legacyCash.ToString() : "none") + ")" : "loaded");
            if (migrated) saveFrame = Time.frameCount + 1;
        }

        /// <summary>The block to write into the team save; null when this machine is not the authority.</summary>
        public EconomySaveData ServerSaveBlock() => IsServer && state != null ? state.ToSave() : null;

        private void BecomeReady(string how)
        {
            ready = true;
            lastClockHour = -1f;
            ApplyVan(state.VanLegacyDebugProfile, state.VanTier(VanBranch.Engine), state.VanTier(VanBranch.Handling), state.VanTier(VanBranch.Brakes));
            ApplyCargo(state.VanCargoOwned);
            PushSnapshot(true);
            Debug.Log($"[ECON] team fund ready: {how}; balance ${state.Fund.Balance}, van {(state.VanLegacyDebugProfile ? "legacy debug max" : $"E{state.VanTier(VanBranch.Engine)}/H{state.VanTier(VanBranch.Handling)}/B{state.VanTier(VanBranch.Brakes)}")}, workshop {(state.WorkshopUnlocked ? "open" : "locked")}, bases {string.Join(",", state.OwnedBases)}, deliveries {state.Deliveries.Count}", this);
        }

        private void SetState(EconomyState next)
        {
            if (state != null) state.Changed -= OnStateChanged;
            state = next;
            state.Changed += OnStateChanged;
            EconomyServerHooks.Credit = (amount, title, key) => ServerCredit(amount, "legacy", title, key).Ok;
            EconomyServerHooks.Charge = (amount, title, key) => ServerCharge(amount, "legacy", title, key).Ok;
        }

        private void DropServerState()
        {
            if (state != null) state.Changed -= OnStateChanged;
            state = null;
            ready = false;
            EconomyServerHooks.ResetForPlay();
            foreach (GameObject go in worldObjects.Values) if (go != null) Destroy(go);
            worldObjects.Clear();
        }

        private void OnStateChanged()
        {
            dirty = true;
            if (ready) saveFrame = Time.frameCount + 1;
        }

        private void OnServerState(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Stopped)
            {
                DropServerState();
                EconomyClientView.Set(null);
            }
        }

        private void OnClientState(ClientConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started && !IsServer) SendHello();
            else if (args.ConnectionState == LocalConnectionState.Stopped && !IsServer) EconomyClientView.Set(null);
        }

        // ---------- server: income / spend API (sales, rewards) ----------

        /// <summary>Sales and rewards may commit (false while the save is still loading: keep the goods, retry later).</summary>
        public bool ServerCanCommit => ServerReady;

        public FundResult ServerCredit(int amount, string kind, string title, string key)
        {
            if (!ServerReady) return new FundResult(FundStatus.Invalid, state != null ? state.Fund.Balance : 0, null);
            return state.Credit(amount, kind, title, key);
        }

        public FundResult ServerCharge(int amount, string kind, string title, string key)
        {
            if (!ServerReady) return new FundResult(FundStatus.Invalid, state != null ? state.Fund.Balance : 0, null);
            return state.Charge(amount, kind, title, key);
        }

        /// <summary>Server, WP02: a sale paid once into the fund TOGETHER with its XP and the once-per-world first-of-a-kind /
        /// first-blood bonuses, under one key, to every present participant (CORE_LOOP §3). Not ready: nothing booked.</summary>
        public SaleCommit ServerCommitSale(int amount, string title, string key, IList<OnlyVolunteers.Buyers.ProductKind> units)
        {
            if (!ServerReady) return new SaleCommit { Fund = new FundResult(FundStatus.Invalid, state != null ? state.Fund.Balance : 0, null) };
            return state.CommitSale(amount, "sale", title, key, units, false, ServerParticipants());
        }

        // ---------- participants: stable ids (WP02) ----------

        public const string HostParticipant = "host";
        private const string PlayerGuidPref = "OnlyVolunteers.PlayerGuid";
        private static string localPlayerGuid;
        private readonly Dictionary<int, string> participantIds = new Dictionary<int, string>();

        /// <summary>This machine's persistent player GUID (PlayerPrefs; "-player-guid &lt;id&gt;" overrides it, e.g. for two
        /// builds on one PC). A client sends it with its Hello; the host itself is always "host".</summary>
        public static string LocalPlayerGuid
        {
            get
            {
                if (!string.IsNullOrEmpty(localPlayerGuid)) return localPlayerGuid;
                string[] args = Environment.GetCommandLineArgs();
                int i = Array.IndexOf(args, "-player-guid");
                if (i >= 0 && i + 1 < args.Length && ValidGuid(args[i + 1])) return localPlayerGuid = args[i + 1];
                string saved = PlayerPrefs.GetString(PlayerGuidPref, "");
                if (!ValidGuid(saved))
                {
                    saved = Guid.NewGuid().ToString("N");
                    PlayerPrefs.SetString(PlayerGuidPref, saved);
                    PlayerPrefs.Save();
                }
                return localPlayerGuid = saved;
            }
        }

        private static bool ValidGuid(string id)
        {
            if (string.IsNullOrEmpty(id) || id.Length < 8 || id.Length > 40 || id == HostParticipant) return false;
            foreach (char ch in id) if (!(char.IsLetterOrDigit(ch) || ch == '-' || ch == '_')) return false;
            return true;
        }

        /// <summary>Server: the stable id of one connection ("host" for the host's own client, the client's GUID after its
        /// Hello, "client:N" before it). Personal ranks and XP lines use this id.</summary>
        public string ServerParticipantId(NetworkConnection c)
        {
            if (c == null || c.IsLocalClient) return HostParticipant;
            return participantIds.TryGetValue(c.ClientId, out string id) ? id : "client:" + c.ClientId;
        }

        private void RegisterParticipant(NetworkConnection c, string guid)
        {
            if (c == null || c.IsLocalClient) return;
            if (!ValidGuid(guid)) { Debug.LogWarning($"[ECON] client {c.ClientId} sent no valid player GUID: XP stays on client:{c.ClientId} this session", this); return; }
            foreach (var pair in participantIds)
                if (pair.Key != c.ClientId && pair.Value == guid && manager.ServerManager.Clients.TryGetValue(pair.Key, out NetworkConnection other) && other != null && other.IsActive)
                {
                    guid = guid + "~" + c.ClientId; // the same GUID twice at once (two builds sharing PlayerPrefs): this session only
                    Debug.LogWarning($"[ECON] player GUID already in this session: client {c.ClientId} is {guid} for now", this);
                    break;
                }
            participantIds[c.ClientId] = guid;
            Debug.Log($"[ECON] client {c.ClientId} is participant {guid}", this);
        }

        private void OnRemoteState(NetworkConnection c, RemoteConnectionStateArgs args)
        {
            if (c != null && args.ConnectionState == RemoteConnectionState.Stopped) participantIds.Remove(c.ClientId);
        }

        /// <summary>This machine's participant id as the server names it: "host" on the host, the persistent GUID on a client
        /// (what workshop / pharmacy states carry as their owner).</summary>
        public string LocalParticipantId => IsServer ? HostParticipant : LocalPlayerGuid;

        /// <summary>The host's own requests (direct on the server, or its local client connection).</summary>
        public static bool IsHostConnection(NetworkConnection c) =>
            c == null || c.IsLocalClient || (FishNet.InstanceFinder.ClientManager != null && c == FishNet.InstanceFinder.ClientManager.Connection);

        /// <summary>Server: where a requester's player stands, measured by the server (the host: the map pawn it controls;
        /// a remote client: its spawned player object). Null when the connection has no body in this scene.</summary>
        public static Vector3? ServerActorPosition(NetworkConnection c)
        {
            var capture = OnlyVolunteers.Capture.CaptureDirector.Instance;
            if (IsHostConnection(c))
            {
                if (capture != null && capture.Pawn != null) return capture.Pawn.Controlled ? capture.Pawn.Position : (Vector3?)null;
                Camera cam = Camera.main;
                return cam != null ? cam.transform.position : (Vector3?)null;
            }
            if (c != null && c.IsActive && c.FirstObject != null) return c.FirstObject.transform.position;
            return null;
        }

        /// <summary>Server: the feet of every player body in the scene (the host's pawn, also while it drives, and each remote
        /// client's player object), for "never push a player" checks of moving doors and lifts.</summary>
        public void ServerPlayerPositions(List<Vector3> into)
        {
            into.Clear();
            var capture = OnlyVolunteers.Capture.CaptureDirector.Instance;
            if (capture != null && capture.Pawn != null && capture.Pawn.Controlled) into.Add(capture.Pawn.Position);
            if (!IsServer) return;
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && !IsHostConnection(c) && c.FirstObject != null) into.Add(c.FirstObject.transform.position);
        }

        /// <summary>Server: the connection with this participant id (null if gone).</summary>
        public NetworkConnection ServerConnectionOf(string participant)
        {
            if (!IsServer || string.IsNullOrEmpty(participant)) return null;
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && ServerParticipantId(c) == participant) return c;
            return null;
        }

        /// <summary>Server: the stable ids of the present participants (XP each): "host" plus every connected client's GUID.</summary>
        public List<string> ServerParticipants()
        {
            var list = new List<string>();
            if (!IsServer) return list;
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive) { string id = ServerParticipantId(c); if (!list.Contains(id)) list.Add(id); }
            if (list.Count == 0) list.Add(HostParticipant);
            return list;
        }

        // ---------- per frame ----------

        private void Update()
        {
            if (!IsServer || state == null) return;
            if (ready)
            {
                TickClock();
                if (Time.unscaledTime >= nextDeliveryCheck)
                {
                    nextDeliveryCheck = Time.unscaledTime + 0.5f;
                    ProcessDeliveries();
                }
            }
            if (dirty)
            {
                dirty = false;
                ApplyVan(state.VanLegacyDebugProfile, state.VanTier(VanBranch.Engine), state.VanTier(VanBranch.Handling), state.VanTier(VanBranch.Brakes));
                if (ready) ApplyCargo(state.VanCargoOwned);
                PushSnapshot(true);
            }
            else if (Time.unscaledTime >= nextLocalPush)
            {
                // A van found only after the load (or a replaced van) gets the paid tiers too; a no-op once applied, so a
                // debug 7/8/9 preview stays until the next paid change or load.
                if (ready)
                {
                    ApplyVan(state.VanLegacyDebugProfile, state.VanTier(VanBranch.Engine), state.VanTier(VanBranch.Handling), state.VanTier(VanBranch.Brakes));
                    ApplyCargo(state.VanCargoOwned);
                }
                PushSnapshot(Time.unscaledTime >= nextRemotePush);
            }
            if (saveFrame >= 0 && Time.frameCount >= saveFrame)
            {
                saveFrame = -1;
                if (ready) ServerCommitted?.Invoke();
            }
        }

        private void TickClock()
        {
            if (clock == null && Time.unscaledTime >= nextClockSearch)
            {
                clock = FindAnyObjectByType<SkyClock22>();
                nextClockSearch = Time.unscaledTime + 5f;
            }
            if (clock != null)
            {
                float hour = clock.Hour;
                if (lastClockHour >= 0f)
                {
                    float step = hour - lastClockHour;
                    if (step < -12f) step += 24f;
                    if (step > 0f && step <= MaxClockStepHours) state.AdvanceWorldTime(step);
                }
                lastClockHour = hour;
                state.ObserveClock(hour); // the saved calendar (day + hour) behind schedules and 06:00 mornings
            }
            else
            {
                float hours = Time.deltaTime / FallbackSecondsPerGameHour;
                state.AdvanceWorldTime(hours);
                state.AdvanceCalendar(hours);
            }
        }

        // ---------- snapshots ----------

        private void PushSnapshot(bool toRemoteClients)
        {
            nextLocalPush = Time.unscaledTime + 1f;
            if (state == null) return;
            EconomySnapshot snapshot = state.ToSnapshot(SnapshotLines, ready);
            EconomyClientView.Set(snapshot);
            if (!toRemoteClients || manager == null || !manager.IsServerStarted) return;
            nextRemotePush = Time.unscaledTime + 5f;
            manager.ServerManager.Broadcast(new EconomySnapshotBroadcast { Json = JsonUtility.ToJson(snapshot) });
        }

        private void SendSnapshotTo(NetworkConnection connection)
        {
            if (state == null || connection == null || !connection.IsActive) return;
            string json = JsonUtility.ToJson(state.ToSnapshot(SnapshotLines, ready));
            manager.ServerManager.Broadcast(connection, new EconomySnapshotBroadcast { Json = json });
        }

        private void OnClientSnapshot(EconomySnapshotBroadcast message, Channel channel)
        {
            if (IsServer || string.IsNullOrEmpty(message.Json)) return; // the host reads its own state
            EconomySnapshot snapshot;
            try { snapshot = JsonUtility.FromJson<EconomySnapshot>(message.Json); }
            catch (Exception e) { Debug.LogWarning("[ECON] bad snapshot: " + e.Message, this); return; }
            if (snapshot == null) return;
            EconomyClientView.Set(snapshot);
            ApplyVan(snapshot.vanLegacyDebugProfile, snapshot.vanEngine, snapshot.vanHandling, snapshot.vanBrakes);
            if (snapshot.ready) ApplyCargo(snapshot.vanCargo);
        }

        private void SendHello()
        {
            if (manager != null && manager.IsClientStarted)
                manager.ClientManager.Broadcast(new EconomyRequestBroadcast { Kind = (byte)EconomyRequestKind.Hello, Key = "", Arg = LocalPlayerGuid, Arg2 = "" });
        }

        // ---------- requests ----------

        /// <summary>Any machine: ask the host for something. done(ok, message) runs on this machine when the answer
        /// arrives (at once on the host). Returns the request key.</summary>
        public string Request(EconomyRequestKind kind, string arg = "", string arg2 = "", int expected = 0, Action<bool, string> done = null)
        {
            string key = Guid.NewGuid().ToString("N");
            if (done != null) pending[key] = done;
            var message = new EconomyRequestBroadcast { Kind = (byte)kind, Key = key, Arg = arg ?? "", Arg2 = arg2 ?? "", Expected = expected };
            if (IsServer)
            {
                (bool ok, string text) = Process(message, true, manager.ClientManager.Connection);
                Deliver(key, ok, text);
            }
            else if (manager != null && manager.IsClientStarted)
                manager.ClientManager.Broadcast(message);
            else
                Deliver(key, false, "Нет связи с хостом");
            return key;
        }

        private void OnServerRequest(NetworkConnection connection, EconomyRequestBroadcast message, Channel channel)
        {
            if (connection == null || !connection.IsActive) return;
            if (message.Kind == (byte)EconomyRequestKind.Hello) { RegisterParticipant(connection, message.Arg); SendSnapshotTo(connection); return; }
            (bool ok, string text) = Process(message, connection.IsLocalClient, connection);
            manager.ServerManager.Broadcast(connection, new EconomyResultBroadcast { Key = message.Key, Ok = ok, Message = text });
        }

        private void OnClientResult(EconomyResultBroadcast message, Channel channel)
        {
            if (IsServer) return; // the host already delivered it directly
            Deliver(message.Key, message.Ok, message.Message);
        }

        private void Deliver(string key, bool ok, string text)
        {
            if (key != null && pending.TryGetValue(key, out Action<bool, string> done))
            {
                pending.Remove(key);
                try { done(ok, text); }
                catch (Exception e) { Debug.LogException(e, this); }
            }
        }

        private static bool Valid(string text) => text != null && text.Length <= 64;

        private (bool ok, string text) Process(EconomyRequestBroadcast m, bool fromHost, NetworkConnection from)
        {
            if (state == null) return (false, "Экономика не запущена");
            if (string.IsNullOrEmpty(m.Key) || !Valid(m.Key) || !Valid(m.Arg) || !Valid(m.Arg2)) return (false, "Неверный запрос");
            var kind = (EconomyRequestKind)m.Kind;
            if (kind >= EconomyRequestKind.DevWorkshop && !Debug.isDebugBuild)
                return (false, "Отладочные переключатели есть только в редакторе и dev-сборке");
            if (!ready) return (false, PurchaseResult.Explain(PurchaseError.NotReady));
            if (kind == EconomyRequestKind.StoryMechanic || kind == EconomyRequestKind.StoryMeetOrganBuyer || kind == EconomyRequestKind.StoryC01Sale ||
                kind == EconomyRequestKind.DevGiveTies || kind == EconomyRequestKind.DevGiveBloodSyringe || kind == EconomyRequestKind.DevNextMorning)
                return StoryHandler != null ? StoryHandler(m, from, state) : (false, "В этой сцене нет сюжетных взаимодействий");
            PurchaseResult r;
            switch (kind)
            {
                case EconomyRequestKind.VanTier:
                    if (!int.TryParse(m.Arg, out int branch) || branch < 0 || branch > 2) return (false, "Неверный запрос");
                    // the W86 workshop: tiers only on its lift, through the mechanic (WorkshopServiceV01 buys there)
                    if (VanInLiftZone()) return (false, "Улучшения — у механика: «Улучшить бусик» (бусик на подъёмнике)");
                    VanShopCheck check = MeasureVan();
                    r = state.TryBuyVanTier((VanBranch)branch, m.Expected, check);
                    Debug.Log($"[ECON] van {(VanBranch)branch} tier {m.Expected}: {(r.Ok ? (r.Replayed ? "replayed" : "PAID $" + r.Price) : "refused " + r.Error)} (zone {check.InZone}, handbrake {check.Handbrake}, stopped {check.Stopped}); fund ${state.Fund.Balance}", this);
                    return (r.Ok, r.Message);
                case EconomyRequestKind.Equipment:
                    r = state.TryOrderEquipment(m.Arg, m.Arg2, m.Expected, m.Key);
                    Debug.Log($"[ECON] equipment {m.Arg} -> {m.Arg2}: {(r.Ok ? (r.Replayed ? "replayed " : "PAID $" + r.Price + " ") + r.DeliveryId : "refused " + r.Error)}; fund ${state.Fund.Balance}", this);
                    return (r.Ok, r.Message);
                case EconomyRequestKind.Property:
                    r = state.TryBuyProperty(m.Arg, m.Expected);
                    Debug.Log($"[ECON] property {m.Arg}: {(r.Ok ? (r.Replayed ? "replayed" : "PAID $" + r.Price) : "refused " + r.Error)}; fund ${state.Fund.Balance}", this);
                    return (r.Ok, r.Message);
                case EconomyRequestKind.PhoneApp:
                {
                    int price = EconomyPrices.PhoneAppPrice(m.Arg);
                    if (price <= 0) return (false, "Неверный запрос");
                    FundResult f = state.Charge(price, "phone", "PayMarket: " + m.Arg, "phoneapp:" + m.Arg);
                    if (f.Ok) return (true, f.Replayed ? "Уже оплачено" : "Оплачено " + EconomyState.Money(price));
                    return (false, f.Status == FundStatus.Insufficient ? PurchaseResult.Explain(PurchaseError.InsufficientFunds) : "Неверный запрос");
                }
                case EconomyRequestKind.Skill:
                {
                    string who = fromHost ? HostParticipant : ServerParticipantId(from);
                    SkillPurchaseResult s = state.TryBuySkill(m.Arg, who, m.Expected);
                    Debug.Log($"[ECON] skill {m.Arg} rank {m.Expected} for {who}: {(s.Ok ? (s.Replayed ? "replayed" : "SPENT " + s.Cost + " XP") : "refused " + s.Error)}; free XP {state.FreeXp}, lifetime {state.LifetimeXp}, level {state.Level}", this);
                    return (s.Ok, s.Message);
                }
                case EconomyRequestKind.SwitchToProgression:
                    if (!fromHost) return (false, "Перевести слот на прогрессию может только хост");
                    return state.SwitchToProgression()
                        ? (true, "Слот переведён на прогрессию: бусик на ступени 0, деньги и имущество не тронуты")
                        : (false, "Слот уже в прогрессии");
                case EconomyRequestKind.DevWorkshop:
                    state.SetWorkshopUnlocked(m.Expected != 0);
                    return (true, "DEV: мастерская " + (state.WorkshopUnlocked ? "открыта" : "закрыта"));
                case EconomyRequestKind.DevOrganBuyer:
                    state.SetFirstOrganBuyerMet(m.Expected != 0);
                    return (true, "DEV: первый органный скупщик " + (state.FirstOrganBuyerMet ? "встречен" : "не встречен"));
                case EconomyRequestKind.DevCredit:
                {
                    FundResult f = state.Credit(5000, "dev", "DEV: тестовые деньги", "dev:credit:" + m.Key);
                    return (f.Ok, "DEV: +$5 000 в фонд (теперь " + EconomyState.Money(state.Fund.Balance) + ")");
                }
                case EconomyRequestKind.DevDeliveriesDue:
                {
                    int n = state.DevMakeDeliveriesDue();
                    return (true, n > 0 ? "DEV: " + n + " доставк(и) прибудут сейчас" : "DEV: нет заказов в пути");
                }
                case EconomyRequestKind.DevWorkshopZoneAtVan:
                {
                    VanController v = FindVan();
                    if (v == null) return (false, "В сцене нет фургона");
                    WorkshopZone.PlaceDev(v.transform.position, v.transform.eulerAngles.y);
                    return (true, "DEV: ремонтная зона мастерской поставлена вокруг фургона");
                }
                default:
                    return (false, "Неверный запрос");
            }
        }

        // ---------- van ----------

        private VanController FindVan()
        {
            if (van == null && Time.unscaledTime >= nextVanSearch)
            {
                van = FindAnyObjectByType<VanController>();
                nextVanSearch = Time.unscaledTime + 2f;
            }
            return van;
        }

        /// <summary>The van stands in a workshop zone served by the lift (WorkshopZone.LiftOnly).</summary>
        private bool VanInLiftZone()
        {
            VanController v = FindVan();
            if (v == null) return false;
            Rigidbody body = v.GetComponent<Rigidbody>();
            WorkshopZone z = WorkshopZone.Containing(body != null ? body.worldCenterOfMass : v.transform.position);
            return z != null && z.LiftOnly;
        }

        /// <summary>Server, at the moment of the commit (§6.3): zone, handbrake, standing still.</summary>
        public VanShopCheck MeasureVan()
        {
            VanController v = FindVan();
            if (v == null) return default;
            Rigidbody body = v.GetComponent<Rigidbody>();
            Vector3 centre = body != null ? body.worldCenterOfMass : v.transform.position;
            bool stopped = Mathf.Abs(v.SpeedKmh) < 1.5f && (body == null || body.linearVelocity.magnitude < 0.6f);
            return new VanShopCheck { InZone = WorkshopZone.Containing(centre) != null, Handbrake = v.Handbrake, Stopped = stopped };
        }

        private void ApplyVan(bool legacy, int engine, int handling, int brakes)
        {
            VanController v = FindVan();
            if (v == null || !v.TryGetComponent(out VanUpgrades upgrades)) return;
            string signature = legacy ? "legacy" : engine + "/" + handling + "/" + brakes;
            if (signature == appliedVan && upgrades.ProgressionActive == !legacy) return;
            appliedVan = signature;
            if (legacy) upgrades.UseLegacyDebugProfile();
            else upgrades.ApplyProgressionTiers(engine, handling, brakes);
            Debug.Log($"[ECON] van profile: {(legacy ? "legacy debug max (old StartAtMax slot)" : $"paid tiers engine {engine}, handling {handling}, brakes {brakes}")}; top speed {v.MaxSpeedKmh:0} km/h", this);
        }

        /// <summary>The paid cargo body on this machine's van (ECONOMY §6.2 + containment, Fedya 29.10): capacity 3 / 4 / 5,
        /// straps (containment I) and padded walls (II) with their visuals, VanCargoFitoutV01. Server: from its state; a
        /// client: from the snapshot (a late joiner gets it with the first one). A no-op once this van shows it.</summary>
        private void ApplyCargo(IReadOnlyList<string> owned)
        {
            VanController v = FindVan();
            if (v == null) return;
            int capacity = VanCargo.Capacity(owned);
            bool straps = VanCargo.Restraints(owned), padded = VanCargo.Padded(owned);
            if (v.TryGetComponent(out VanCargoFitoutV01 fitout) && fitout.Matches(capacity, straps, padded)) return;
            fitout = VanCargoFitoutV01.Ensure(v.gameObject);
            fitout.Apply(capacity, straps, padded);
            Debug.Log($"[ECON] van cargo body: capacity {capacity}, straps {(straps ? "on" : "off")}, padded walls {(padded ? "on" : "off")} ({(owned != null && owned.Count > 0 ? string.Join(",", owned) : "stock")})", this);
        }

        // ---------- deliveries ----------

        private void ProcessDeliveries()
        {
            foreach (DeliveryOrder order in state.DueDeliveries())
            {
                if (EconomyDeliveries.TryFindSlot(order, worldObjects, out int slot, out Vector3 position, out float yaw))
                {
                    if (!state.MarkArrived(order.id, slot, position.x, position.y, position.z, yaw)) continue;
                    SpawnWorldObject(state.FindDelivery(order.id));
                    Say($"Доставка {order.id}: ящик «{Title(order)}» ждёт на базе «{BaseTitle(order)}»");
                }
                else if (order.State == DeliveryState.Pending && state.MarkWaiting(order.id))
                    Say($"Доставка {order.id} ({Title(order)}) ждёт: на базе «{BaseTitle(order)}» нет свободного места для ящика");
            }
        }

        /// <summary>The host opened a delivered crate (E): the item, or its labelled placeholder, stands where it was.</summary>
        public bool ServerOpenCrate(string deliveryId)
        {
            if (!ServerReady) return false;
            DeliveryOrder order = state.FindDelivery(deliveryId);
            if (order == null || order.State != DeliveryState.Arrived) return false;
            Vector3 p = new Vector3(order.x, order.y, order.z);
            if (worldObjects.TryGetValue(deliveryId, out GameObject crate) && crate != null)
            {
                p = crate.transform.position;
                Destroy(crate);
            }
            worldObjects.Remove(deliveryId);
            if (!state.MarkOpened(deliveryId, p.x, p.y, p.z, order.yaw)) return false;
            SpawnWorldObject(state.FindDelivery(deliveryId));
            Say($"Распаковано: {Title(order)}");
            return true;
        }

        private void RebuildWorldObjects()
        {
            foreach (GameObject go in worldObjects.Values) if (go != null) Destroy(go);
            worldObjects.Clear();
            foreach (DeliveryOrder order in state.Deliveries)
                if (order.State == DeliveryState.Arrived || order.State == DeliveryState.Opened) SpawnWorldObject(order);
        }

        private void SpawnWorldObject(DeliveryOrder order)
        {
            if (order == null) return;
            if (worldObjects.TryGetValue(order.id, out GameObject old) && old != null) Destroy(old);
            GameObject go = order.State == DeliveryState.Arrived ? EconomyDeliveries.CreateCrate(order) : EconomyDeliveries.CreateUnpacked(order);
            if (go != null) worldObjects[order.id] = go;
        }

        private static string Title(DeliveryOrder order)
        {
            EquipmentOffer item = EconomyPrices.FindEquipment(order.itemId);
            return item != null ? item.Title : order.itemId;
        }

        private static string BaseTitle(DeliveryOrder order)
        {
            PropertyOffer place = EconomyPrices.FindProperty(order.baseId);
            return place != null ? place.Title : order.baseId;
        }

        private void Say(string text)
        {
            Debug.Log("[ECON] " + text, this);
            Notice?.Invoke(text);
        }
    }
}
