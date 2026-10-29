using OnlyVolunteers.Inventory;
using System;
using System.Collections.Generic;
using System.IO;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Capture
{
    /// <summary>Composition root of capture → delivery stage A in the map play scene (CAPTURE_DELIVERY_SPEC v01 §9).
    /// Architecture (see docs/reports/CAPTURE_DELIVERY_STAGE_A.md): the map, its van, crowd, police and NPC capture stay
    /// offline; the scene also runs a FishNet solo host (server + local client over Tugboat) so the networked operation
    /// table is reused unchanged. The map's own KCC pawn is the host's NetworkPlayer (externalControl: it keeps its own
    /// control, camera, HUD and phone) and gets NetworkInventory + NetworkGrabber for the table's hands and carry.
    /// This object: starts the host, spawns the table (admission mode) at the base, gives the pawn to the local client,
    /// makes every knocked-down crowd NPC a capture identity (facts + OperationState + rolled grades), owns the field kit,
    /// the HUD and the save (D13).</summary>
    [DefaultExecutionOrder(-200)]
    public sealed class CaptureDirector : MonoBehaviour
    {
        public static CaptureDirector Instance { get; private set; }

        [Header("Scene")]
        public NetworkOperationTable TablePrefab;
        public Transform TableSpawn;
        public NetworkObject PawnNetworkObject;
        public string BaseName = "База B02 — сарай у хижины деда";
        [Tooltip("Operation tuning (dose, blood, death rules): the table prefab's own asset.")]
        public OperationTuning Tuning;
        [Header("Network")]
        public ushort Port = 7791;
        [Header("Save")]
        public bool LoadOnStart = true;
        public float AutosaveSeconds = 60f;
        public string SaveFileName = "capture_stageA_v01.json";

        public PatientRegistry Registry { get; private set; }
        public CaptureFieldKit Kit { get; private set; }
        public CaptureHud Hud { get; private set; }
        public CaptureTableBridge Bridge { get; private set; }
        public CaptureBodyBag BodyBagPrefab;
        public CaptureCorpseDisposal Disposal { get; private set; }
        public NetworkOperationTable Table { get; private set; }
        public GreyboxKccPawn Pawn { get; private set; }
        public VanController Van { get; private set; }
        public bool Ready { get; private set; }
        public bool Loaded { get; private set; }
        public string LastSaveNote { get; private set; } = "";
        public readonly Dictionary<string, CaptureFacts> Facts = new Dictionary<string, CaptureFacts>();
        /// <summary>G49: the world's syringe record (C01 sales, daily find); saved in CaptureSaveData.syringes.</summary>
        public SyringeSaveBlock Syringes = new SyringeSaveBlock();
        private OfflineWorldItem dailyFindItem;
        private float nextDailyCheck;
        private bool warnedDailyAnchor;

        private NetworkManager manager;
        private float nextAutosave;
        private bool hostStarted;
        private int portTries;
        private bool tableMode;
        private float playTime;

        /// <summary>The player's save file name; editor sessions and automated runs never touch it (their own slots).</summary>
        public string BaseSavePath => Path.Combine(Application.persistentDataPath, "OnlyVolunteers",
            // the start menu's world slot (29.10) first, then the test / editor overrides, then the scene's default file
            OnlyVolunteers.Session.WorldLaunchV01.Active && !string.IsNullOrEmpty(OnlyVolunteers.Session.WorldLaunchV01.SlotFile) ? OnlyVolunteers.Session.WorldLaunchV01.SlotFile :
            !string.IsNullOrEmpty(CaptureTestHooks.SaveSlot) ? CaptureTestHooks.SaveSlot :
#if UNITY_EDITOR
            "capture_stageA_editor.json");
#else
            SaveFileName);
#endif
        /// <summary>The file this session reads and writes: the base file, or the new file the player chose after a save
        /// that would not load (WP01, CaptureSaveStore.ResolveActive).</summary>
        public string SavePath => CaptureSaveStore.ResolveActive(BaseSavePath);

        /// <summary>WP01 (SV-13): the save did not load (newer version, corrupt, too old, failed while applying). Nothing
        /// is written until the player picks a way out on the prompt; the file itself is never written, moved or deleted.</summary>
        public bool WriteBlocked => blockedProbe != null;
        public SaveFileProbe BlockedSave => blockedProbe;
        private SaveFileProbe blockedProbe;
        private SaveFileProbe recoveryBackup;
        private string blockedText = "";
        private bool loadStarted;
        private OnlyVolunteers.Player.KccFirstPersonInput promptWalker;
        private bool promptSavedMove, promptSavedLook;

        // ---------- lifecycle ----------

        private void Awake()
        {
            Instance = this;
            Pawn = FindAnyObjectByType<GreyboxKccPawn>(FindObjectsInactive.Include);
            Van = FindAnyObjectByType<VanController>(FindObjectsInactive.Include);
            manager = FindAnyObjectByType<NetworkManager>();
            Registry = gameObject.AddComponent<PatientRegistry>();
            Disposal = gameObject.AddComponent<CaptureCorpseDisposal>(); Disposal.Init(this);
            Hud = CaptureHud.Create();
            var kitGo = new GameObject("[Capture] Field kit");
            kitGo.transform.SetParent(transform, false);
            Kit = kitGo.AddComponent<CaptureFieldKit>();
            gameObject.AddComponent<CaptureGrabArbiter>().Init(Pawn);
            BindCashDisplay();
            // The gurney brakes fully while any body is carried near it (a captured NPC, a corpse, a body bag).
            var mapGrabber = Pawn != null ? Pawn.GetComponentInChildren<PhysicsGrabber>(true) : null;
            OperationTableBrake.CarryingNear = (point, range) =>
            {
                float r2 = range * range;
                if (mapGrabber != null && mapGrabber.IsHolding && mapGrabber.GrabbedBody != null && (mapGrabber.GrabbedBody.worldCenterOfMass - point).sqrMagnitude < r2) return true;
                if (Disposal != null)
                    foreach (var corpse in Disposal.Corpses)
                        if (corpse != null && corpse.FieldNpc == null && corpse.Held && (corpse.Center - point).sqrMagnitude < r2) return true;
                return false;
            };
            if (Van != null && !Van.TryGetComponent(out CaptureVanCapacity _)) Van.gameObject.AddComponent<CaptureVanCapacity>();
            if (Tuning == null && TablePrefab != null) Tuning = TablePrefab.Tuning;
            // Body bag art for the wrapped-ragdoll bag (Rework 2026-10-18): the approved closed bag of the G34 prefab.
            if (BodyBagPrefab != null)
                foreach (var filter in BodyBagPrefab.GetComponentsInChildren<MeshFilter>(true))
                    if (filter.name == "SM_BodyBag_Closed" && filter.sharedMesh != null)
                    { OperationBodyBagWrap.SourceMesh = filter.sharedMesh; OperationBodyBagWrap.SourceMaterial = filter.GetComponent<Renderer>().sharedMaterial; }
            GameObject anesthesia = null, blood = null;
            var tools = TablePrefab != null ? ToolPrefabs(TablePrefab) : null;
            if (tools != null)
                foreach (var t in tools)
                {
                    if (t == null || t.Visual == null) continue;
                    if (t.Kind == OperationToolKind.Syringe) anesthesia = t.Visual.gameObject;
                    else if (t.Kind == OperationToolKind.BloodSyringe) blood = t.Visual.gameObject;
                }
            Kit.Init(Tuning, Pawn, Hud, anesthesia, blood);
            GreyboxNpc.Incident += OnIncident;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            gameObject.AddComponent<CaptureScenarioDriver>(); // dev-only test driver (PlayMode tests, -capture-scenario)
#endif
        }

        private static OperationTool[] ToolPrefabs(NetworkOperationTable prefab)
        {
            var field = typeof(NetworkOperationTable).GetField("toolPrefabs", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
            return field != null ? field.GetValue(prefab) as OperationTool[] : null;
        }

        private void OnDestroy()
        {
            GreyboxNpc.Incident -= OnIncident;
            TeamEconomy.ServerCommitted -= OnEconomyCommitted;
            TeamEconomy.Notice -= OnEconomyNotice;
            if (manager != null)
            {
                manager.ServerManager.OnServerConnectionState -= ServerState;
                manager.SceneManager.OnClientLoadedStartScenes -= ClientLoaded;
                manager.ClientManager.OnClientConnectionState -= ClientState;
            }
            if (Hud != null) Destroy(Hud.gameObject);
            if (Instance == this) Instance = null;
        }

        private void Start()
        {
            if (manager == null) { Debug.LogError("[CAPTURE] no FishNet NetworkManager in the scene", this); return; }
            manager.ServerManager.OnServerConnectionState += ServerState;
            manager.SceneManager.OnClientLoadedStartScenes += ClientLoaded;
            manager.ClientManager.OnClientConnectionState += ClientState;
            TeamEconomy.ServerCommitted += OnEconomyCommitted;
            TeamEconomy.Notice += OnEconomyNotice;
            StartHost();
        }

        /// <summary>ECONOMY spec v01 §10.4: an economic commit (sale, purchase, delivery step) is written at once, not left for
        /// the autosave. Before the save is loaded nothing is written (that would overwrite the player's save).</summary>
        private void OnEconomyCommitted()
        {
            if (Ready && Loaded && !WriteBlocked) Save(false);
        }

        private void OnEconomyNotice(string text) => Toast(text, CaptureHud.Neutral, 4f);

        private void StartHost()
        {
            if (manager.ServerManager.Started) return;
            // 29.10: a co-op world from the start menu listens on every interface on the menu's port; anything else stays the
            // loopback solo host it always was (a solo world is never offered on the network)
            bool coop = OnlyVolunteers.Session.WorldLaunchV01.Active && OnlyVolunteers.Session.WorldLaunchV01.Role == OnlyVolunteers.Session.LaunchRole.CoopHost;
            ushort basePort = coop ? OnlyVolunteers.Session.WorldLaunchV01.Port : Port;
            ushort port = (ushort)(basePort + portTries);
            // Skip ports another process (an operations build, a stale editor socket) holds: no "server failed" error.
            while (portTries < 10 && !UdpPortFree(port)) { portTries++; port = (ushort)(basePort + portTries); }
            string bind = coop ? "0.0.0.0" : "127.0.0.1";
            manager.TransportManager.Transport.SetMaximumClients(coop ? 4 : 1);
            manager.TransportManager.Transport.SetServerBindAddress(bind, IPAddressType.IPv4);
            bool ok = manager.ServerManager.StartConnection(port);
            Debug.Log($"[CAPTURE] {(coop ? "co-op" : "solo")} host: server on {bind}:{port} start={ok}");
        }

        private static bool UdpPortFree(ushort port)
        {
            try
            {
                using (var probe = new System.Net.Sockets.UdpClient(new System.Net.IPEndPoint(System.Net.IPAddress.Loopback, port))) { }
                using (var any = new System.Net.Sockets.UdpClient(new System.Net.IPEndPoint(System.Net.IPAddress.Any, port))) { }
                return true;
            }
            catch (System.Net.Sockets.SocketException) { return false; }
        }

        private void ServerState(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started)
            {
                hostStarted = true;
                // The team's shared fund (ECONOMY spec v01): host-authoritative; the save restores / migrates it.
                TeamEconomy.Ensure(manager)?.ServerBegin(waitForExternalLoad: LoadOnStart);
                SpawnTable();
                manager.ClientManager.StartConnection("127.0.0.1", manager.TransportManager.Transport.GetPort());
            }
            else if (args.ConnectionState == LocalConnectionState.Stopped && !hostStarted && portTries < 5)
            {
                portTries++; // port busy (e.g. an operations build running): try the next one
                StartHost();
            }
        }

        private void ClientState(ClientConnectionStateArgs args)
        {
            Debug.Log($"[CAPTURE] local client {args.ConnectionState}");
            if (args.ConnectionState == LocalConnectionState.Started) TeamEconomy.Ensure(manager);
        }

        private void ClientLoaded(NetworkConnection connection, bool asServer)
        {
            if (!asServer || PawnNetworkObject == null || !connection.IsActive) return;
            // 29.10: the scene pawn is the HOST's body; a remote client must never be given it (that took the host's player
            // away). Players of remote clients on the map are network milestone M1 (NETWORK_MAP_PLAN_v01): refused for now.
            if (!connection.IsLocalClient && !connection.IsHost)
            {
                Debug.LogWarning($"[CAPTURE] remote client {connection.ClientId} refused: co-op on the map needs network milestone M1 (players on the map)");
                manager.ServerManager.Kick(connection, FishNet.Managing.Server.KickReason.UnexpectedProblem);
                return;
            }
            if (!PawnNetworkObject.IsSpawned) manager.ServerManager.Spawn(PawnNetworkObject, connection);
            else PawnNetworkObject.GiveOwnership(connection);
            Debug.Log($"[CAPTURE] map pawn is the host player now (client {connection.ClientId})");
            Ready = true;
            if (LoadOnStart && !Loaded) Invoke(nameof(LoadAfterStart), 0.5f);
        }

        private void SpawnTable()
        {
            if (TablePrefab == null || TableSpawn == null) { Debug.LogError("[CAPTURE] table prefab or spawn missing", this); return; }
            Table = Instantiate(TablePrefab, TableSpawn.position, TableSpawn.rotation);
            Table.name = TablePrefab.name + " (base)";
            Table.ConfigureAdmission(Registry);
            if (Table.TryGetComponent(out PatientRegistry own) && own != Registry) own.enabled = false;
            manager.ServerManager.Spawn(Table.NetworkObject);
            if (Table.TryGetComponent(out NetworkPhysicsBody body)) NetworkSession.Active?.RegisterBody(body);
            Bridge = gameObject.AddComponent<CaptureTableBridge>();
            Bridge.Bind(Table, this, Pawn);
            Debug.Log($"[CAPTURE] table spawned at {TableSpawn.position} (admission mode)");
        }

        /// <summary>W86: one balance on screen. The money is the player's NetworkInventory (the first-buyer crate pays it,
        /// the capture save keeps it); the hotbar belongs to the map's LocalInventory (its start cash is not this money),
        /// so the hotbar's "$" reads the NetworkInventory. The phone binds itself (GreyboxPhone).</summary>
        private void BindCashDisplay()
        {
            var wallet = Pawn != null ? Pawn.GetComponent<NetworkInventory>() : null;
            if (wallet == null) return;
            foreach (var hud in Pawn.GetComponentsInChildren<InventoryHud>(true)) hud.CashSource = wallet;
        }

        /// <summary>Game time when the save was restored (the clocks run from here).</summary>
        public float LoadedAt { get; private set; }
        private void LoadAfterStart()
        {
            if (loadStarted) return;
            loadStarted = true;
            LoadedAt = Time.time;
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-capture-fresh") >= 0) { Loaded = true; TeamEconomy.Instance?.ServerMarkReady(); Toast("Новая игра", CaptureHud.Neutral); return; }
            if (!File.Exists(SavePath))
            {
                // New game: the shared fund starts empty (ES-01), the van at paid tier 0.
                Loaded = true;
                TeamEconomy.Instance?.ServerMarkReady();
                Toast("Поймай кого-нибудь в Хуторе и привези в сарай у хижины деда", CaptureHud.Neutral, 6f);
                return;
            }
            // WP01: a save that does not load is NOT a new game over it. Loaded stays false (no autosave, no commit save,
            // no quit save, the story waits) and the prompt offers the newest valid backup or a new game in a new file.
            if (Load()) Loaded = true;
        }

        // ---------- capture identities ----------

        private void OnIncident(GreyboxNpc npc, NpcIncident kind)
        {
            if (kind == NpcIncident.Stunned) Ensure(npc);
        }

        /// <summary>The capture identity of a downed NPC, made the first time (seeded intrinsic grades, D9).</summary>
        public CaptureNpc Ensure(GreyboxNpc npc)
        {
            if (npc == null || Tuning == null) return null;
            if (npc.TryGetComponent(out CaptureNpc existing) && existing.Facts != null) return existing;
            PatientRecord record = Registry.Ensure(npc);
            if (!Facts.TryGetValue(record.Id, out CaptureFacts facts))
            {
                facts = new CaptureFacts
                {
                    patientId = record.Id,
                    districtId = DistrictAt(npc.Center),
                    visual = VisualName(npc),
                };
                facts.npcTypeId = TypeIdFor(facts.visual);
                facts.intrinsic = CaptureGrades.RollIntrinsic(facts.patientId, facts.districtId, facts.npcTypeId);
                facts.rolled = true;
                facts.condition = npc.Condition;
                Facts[record.Id] = facts;
            }
            if (record.Operation == null)
            {
                record.Operation = OperationRules.Create(record.Id, Tuning);
                CaptureGrades.Apply(record.Operation, facts.intrinsic);
            }
            var c = existing != null ? existing : npc.gameObject.AddComponent<CaptureNpc>();
            c.Bind(facts, record.Operation, Tuning);
            Debug.Log($"[CAPTURE] captured {facts.patientId}: {facts.districtId}/{facts.npcTypeId} grades {facts.intrinsic[0]}/{facts.intrinsic[1]}/{facts.intrinsic[2]}");
            return c;
        }

        public static string DistrictAt(Vector3 world)
        {
            var crowd = CrowdDirector.Instance;
            if (crowd == null || crowd.Map == null) return "village";
            int d = crowd.DistrictAt(world);
            return d >= 0 && d < crowd.Map.Districts.Count ? crowd.Map.Districts[d].Id : "village";
        }

        public static string DistrictName(string id)
        {
            var crowd = CrowdDirector.Instance;
            if (crowd != null && crowd.Map != null)
                foreach (var d in crowd.Map.Districts) if (d.Id == id) return d.Name;
            return id == "village" ? "Хутор" : id;
        }

        private static string VisualName(GreyboxNpc npc)
        {
            var a = npc.GetComponentInChildren<Animator>(true);
            return a != null ? a.gameObject.name : "SausageBuddy_A";
        }

        public static string TypeIdFor(string visual)
        {
            string v = (visual ?? "").ToUpperInvariant().Replace("(CLONE)", "").Trim();
            if (v.StartsWith("SAUSAGEBUDDY_")) return "SAUSAGE_BUDDY_" + v.Substring("SAUSAGEBUDDY_".Length);
            return v.Length > 0 ? v : "SAUSAGE_BUDDY_A";
        }

        public static string TypeName(string typeId) =>
            typeId == "SAUSAGE_BUDDY_A" ? "Сосиска в худи" : typeId == "SAUSAGE_BUDDY_B" ? "Сосиска в кепке" : typeId;

        public void BeforeAdmit(CaptureNpc c)
        {
            PatientRecord record = Registry.Get(c.PatientId);
            if (record != null && record.Stage == PatientStage.Loaded) Registry.Move(record, PatientStage.Captured);
            if (record != null && record.Stage == PatientStage.Available) Registry.Move(record, PatientStage.Captured);
        }

        public void AfterAdmit(CaptureNpc c, bool ok)
        {
            if (!ok) { Toast("Стол не принял пациента", CaptureHud.Bad); return; }
            string grades = OperationText.Tier(c.State.organs[0].intrinsicGrade);
            Toast(c.State.alive ? "Пуф! Раздет и на столе. Встань к столу — E" : "Пуф! Труп на столе — органы ещё можно достать", CaptureHud.Good, 3.5f);
            Debug.Log($"[CAPTURE] on the table: {c.PatientId} blood={c.State.bloodPortions} sleep={c.State.sleepRemaining:F1} kidney L {grades}");
        }

        public void AfterRemove(string id)
        {
            PatientRecord record = Registry.Get(id);
            if (record != null)
            {
                if (record.Stage == PatientStage.Available) Registry.Move(record, PatientStage.Captured);
                if (record.Stage == PatientStage.Loaded) Registry.Move(record, PatientStage.Captured);
                if (record.Stage == PatientStage.Captured) Registry.Move(record, PatientStage.AtBase);
                if (record.Stage == PatientStage.AtBase) Registry.Move(record, PatientStage.InOperation);
                Registry.TryResolve(record, 0);
            }
            Facts.Remove(id);
            Toast("Всплеск… тело утонуло, следы убраны", CaptureHud.Neutral);
        }

        public void SetTableMode(bool on)
        {
            tableMode = on;
            Kit.Suspended = on;
        }

        public void Toast(string text, Color color, float seconds = 3f) => Hud?.Toast(text, color, seconds);

        // ---------- per frame ----------

        private void Update()
        {
            playTime += Time.deltaTime;
            if (WriteBlocked) { UpdatePrompt(); return; }
            if (Ready && Loaded && Time.unscaledTime >= nextDailyCheck) { nextDailyCheck = Time.unscaledTime + 1f; TickDailySyringe(); }
            // Safety net: a downed NPC that missed the incident (e.g. already lying at load) still gets an identity.
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && npc.isActiveAndEnabled && (npc.State == NpcState.Down || npc.InCargo) && !npc.TryGetComponent(out CaptureNpc _))
                    Ensure(npc);
            Keyboard key = OpsInput.Keyboard;
            if (key != null && key.kKey.wasPressedThisFrame && !tableMode && !OnlyVolunteers.UI.OvMenuGate.Blocking)
            {
                if (key.leftShiftKey.isPressed || key.rightShiftKey.isPressed) NewGame();
                else Save(true);
            }
            if (Ready && Loaded && AutosaveSeconds > 0f && Time.time >= nextAutosave)
            {
                nextAutosave = Time.time + AutosaveSeconds;
                if (playTime > 10f) Save(false);
            }
            Hud.SetVisible(!tableMode && Pawn != null && Pawn.Controlled);
            string corner = Bridge != null ? Bridge.RemoveHint : null;
            if (Bridge != null && Bridge.RemoveProgress > 0.01f) Hud.Ring(Bridge.RemoveProgress, CaptureHud.Warn, "упаковываю тело…");
            Hud.Corner(StatusLine() + (corner != null ? "\n<color=#FFB13B>" + corner + "</color>" : ""));
        }

        private string StatusLine()
        {
            int captured = 0, inVan = 0;
            foreach (var c in CaptureNpc.All) if (c != null && !c.Admitted && c.Npc != null) { captured++; if (c.Npc.InCargo) inVan++; }
            string table = Table != null && Table.HasPatient ? "на столе: пациент" : "стол свободен";
            float dist = Table != null && Pawn != null && Pawn.Controlled ? Vector3.Distance(Pawn.Position, Table.transform.position) : -1f;
            EconomySnapshot snap = EconomyClientView.Current;
            string fund = snap != null ? $"\nобщий фонд <b>{EconomyState.Money(snap.balance)}</b> · XP {snap.lifetimeXp} (свободно {snap.freeXp}) · уровень {snap.level}" : "";
            return $"<b>{BaseName}</b>{(dist >= 0f ? $" · {dist:0} м" : "")}\nпоймано {captured} · в бусике {inVan} · {table}{fund}\nK — сохранить · Shift+K — новая игра";
        }

        /// <summary>G49 daily find (economy §5.2, A24/A31): the ONE saved morning record advances on the active world's
        /// saved calendar (TeamEconomy, frozen while closed) — start, load and the 06:00 tick use this same call. A created
        /// syringe is materialized only at an authored anchor "WagonSyringeFind" (none is authored yet: the record keeps the
        /// uncollected instance and its id, nothing is invented). Picking it up moves the same instance into the hotbar.</summary>
        private void TickDailySyringe()
        {
            var economy = TeamEconomy.Instance;
            EconomyState state = economy != null ? economy.ServerState : null;
            if (state == null || !economy.ServerReady || state.TimeOfDay < 0) return;
            var daily = Syringes.Daily;
            if (string.IsNullOrEmpty(daily.WorldId)) daily.WorldId = Guid.NewGuid().ToString("N");
            if (DailySyringeFindRules.Advance(daily, daily.WorldId, (long)(state.AbsoluteHours * 3600.0), true))
                Debug.Log($"[CAPTURE] daily syringe find: morning {daily.LastMorning}, uncollected {daily.Uncollected?.ItemId}");
            if (daily.Uncollected == null) return;
            if (dailyFindItem != null)
            {
                if (dailyFindItem.Syringe == null || dailyFindItem.Count <= 0) dailyFindItem = null;
                else return;
            }
            var model = Kit != null && Kit.Inventory != null ? Kit.Inventory.Model : null;
            if (model != null)
                for (int i = 0; i < model.SlotCount; i++)
                    if (model.GetSlot(i).Syringe != null && model.GetSlot(i).Syringe.ItemId == daily.Uncollected.ItemId)
                    {
                        DailySyringeFindRules.Collect(daily, daily.Uncollected.ItemId);
                        Debug.Log("[CAPTURE] daily syringe collected (same instance in the hotbar)");
                        return;
                    }
            var anchor = OnlyVolunteers.Story.StoryAnchor.Find("WagonSyringeFind");
            ItemDefinition definition = Kit != null && Kit.Inventory != null && Kit.Inventory.Database != null ? Kit.Inventory.Database.Get(SyringeRules.BloodDefinitionId) : null;
            if (anchor == null || definition == null)
            {
                if (!warnedDailyAnchor) { warnedDailyAnchor = true; Debug.Log("[CAPTURE] daily syringe recorded but not placed: no authored WagonSyringeFind anchor in this scene"); }
                return;
            }
            foreach (var drop in FindObjectsByType<OfflineWorldItem>())
                if (drop.Syringe != null && drop.Syringe.ItemId == daily.Uncollected.ItemId) { dailyFindItem = drop; return; }
            int price;
            try { price = SyringeRules.Price(SyringeKind.Blood); } catch (Exception) { price = 0; }
            dailyFindItem = OfflineWorldItem.Spawn(definition, 1, price, anchor.transform.position + Vector3.up * 0.1f);
            dailyFindItem.SetSyringe(daily.Uncollected.Copy());
        }

        private void OnApplicationQuit()
        {
            // Quitting saves the game (D13); automated runs keep their own explicit saves.
            if (Ready && Loaded && !WriteBlocked && string.IsNullOrEmpty(CaptureTestHooks.SaveSlot)) Save(false);
        }

        // ---------- save / load (D13) ----------

        /// <summary>Writes the world (WP01: through CaptureSaveStore: checked text, three rotating backups, atomic replace,
        /// never over a newer-version file). Refused while the save is not loaded yet or a failed load blocks writing.
        /// A failure keeps the previous file and says so; it never reports "Сохранено".</summary>
        public bool Save(bool announce)
        {
            if (WriteBlocked || !Loaded)
            {
                LastSaveNote = WriteBlocked ? "save blocked: the save on disk did not load (" + blockedProbe.Status + ")" : "save refused: the save is not loaded yet";
                Debug.LogWarning("[CAPTURE] " + LastSaveNote);
                if (announce) Toast(WriteBlocked ? "Сохранение выключено: сначала выбери, что делать со старым файлом" : "Сохранение ещё загружается — не сохраняю", CaptureHud.Warn);
                return false;
            }
            try
            {
                var data = new CaptureSaveData { scene = SceneManager.GetActiveScene().path, savedUtc = DateTime.UtcNow.ToString("o"), playTime = playTime };
                CaptureSave.Write(this, data);
                CaptureSaveStore.Write(SavePath, JsonUtility.ToJson(data, true));
                LastSaveNote = $"saved {data.npcs.Count} NPCs, table patient={(data.table != null && data.table.patient != null ? data.table.patient.patientId : "-")}";
                Debug.Log($"[CAPTURE] {LastSaveNote} -> {SavePath}");
                if (announce) Toast("Сохранено", CaptureHud.Neutral, 1.5f);
                return true;
            }
            catch (Exception e)
            {
                LastSaveNote = e.Message;
                Debug.LogError("[CAPTURE] save failed: " + e);
                if (announce) Toast("Не сохранилось: " + e.Message, CaptureHud.Bad);
                return false;
            }
        }

        /// <summary>Loads the active save. v1 (before the shared fund) still loads: its cash is migrated into the fund once
        /// (FundMigration). WP01: a newer, too old or corrupt file, or one that fails while being applied, blocks writing
        /// and opens the prompt (returns false); it is never replaced by a new game.</summary>
        public bool Load()
        {
            string path = SavePath;
            SaveFileProbe probe = CaptureSaveStore.Probe(path);
            if (!probe.Loadable)
            {
                Debug.LogError($"[CAPTURE] save not loaded ({probe.Status} v{probe.Version} {probe.Error}): {path} — writing blocked, the file is left as it is");
                BlockWrites(probe, CaptureSaveStore.Explain(probe));
                return false;
            }
            var data = probe.Data;
            try
            {
                CaptureSave.Read(this, data);
            }
            catch (Exception e)
            {
                Debug.LogError("[CAPTURE] load failed while applying the save — writing blocked, the file is left as it is: " + e);
                probe.Error = e.Message;
                string message = (e.Message ?? "").Replace('\n', ' ');
                if (message.Length > 90) message = message.Substring(0, 90) + "…";
                BlockWrites(probe, "Сохранение не загрузилось целиком (" + message + ").");
                return false;
            }
            Toast($"Загружено: поймано {data.npcs.Count}" + (data.table != null && data.table.patient != null ? ", на столе пациент" : ""), CaptureHud.Neutral);
            Debug.Log($"[CAPTURE] loaded {data.npcs.Count} NPCs from {path}");
            return true;
        }

        /// <summary>Shift+K. A normal new game deletes the active file and its backups. While a failed load blocks writing,
        /// the file that failed is not deleted: this is the prompt's "new game in a new file".</summary>
        public void NewGame()
        {
            if (WriteBlocked) { ChooseNewFile(); return; }
            try { CaptureSaveStore.DeleteWithBackups(SavePath); }
            catch (Exception e) { Debug.LogWarning("[CAPTURE] could not delete the save: " + e.Message); }
            ReloadScene();
        }

        private void ReloadScene()
        {
            ClosePrompt();
            Loaded = false;
            if (manager != null)
            {
                if (manager.ClientManager.Started) manager.ClientManager.StopConnection();
                if (manager.ServerManager.Started) manager.ServerManager.StopConnection(true);
            }
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex >= 0 ? SceneManager.GetActiveScene().buildIndex : 0);
        }

        // ---------- WP01: a save that did not load ----------

        private void BlockWrites(SaveFileProbe probe, string reason)
        {
            blockedProbe = probe;
            recoveryBackup = CaptureSaveStore.NewestValidBackup(probe.Path);
            string file = Path.GetFileName(probe.Path);
            var text = new System.Text.StringBuilder();
            text.Append(reason).Append('\n');
            text.Append("Файл <b>").Append(file).Append("</b> не тронут, сохранение и автосохранение выключены.\n\n");
            if (recoveryBackup != null)
                text.Append("<b>1</b> — загрузить резервную копию от ").Append(recoveryBackup.WhenText()).Append(" (сыгранное после неё пропадёт)\n");
            else
                text.Append("<color=#9AA3AE>Целой резервной копии нет.</color>\n");
            text.Append("<b>2</b> — новая игра в новом файле (старый файл остаётся как есть)\n");
            text.Append("<b>3</b> — выйти из игры, ничего не меняя");
            blockedText = text.ToString();
            Debug.LogWarning("[CAPTURE] save prompt: backup " + (recoveryBackup != null ? recoveryBackup.Path + " (" + recoveryBackup.SavedUtc + ")" : "none"));
            OpenPrompt();
        }

        private void OpenPrompt()
        {
            Hud?.Prompt("Сохранение не загружено", blockedText);
            if (promptWalker == null)
            {
                foreach (var k in FindObjectsByType<OnlyVolunteers.Player.KccFirstPersonInput>())
                    if (k.isActiveAndEnabled) { promptWalker = k; break; }
                if (promptWalker != null)
                {
                    promptSavedMove = promptWalker.MovementLocked; promptSavedLook = promptWalker.LookSuspended;
                    promptWalker.MovementLocked = true; promptWalker.LookSuspended = true;
                }
            }
            OnlyVolunteers.UI.OvMenuGate.Blocking = true;
        }

        private void ClosePrompt()
        {
            if (Hud != null) Hud.HidePrompt();
            if (promptWalker != null)
            {
                promptWalker.MovementLocked = promptSavedMove;
                promptWalker.LookSuspended = promptSavedLook;
                promptWalker = null;
            }
            if (blockedProbe != null) OnlyVolunteers.UI.OvMenuGate.Blocking = false;
        }

        /// <summary>The prompt owns the keyboard while it is up: 1 backup, 2 new file, 3 quit. Escape does not open the
        /// pause menu over it (the menu would hand the input back to the game).</summary>
        private void UpdatePrompt()
        {
            OnlyVolunteers.UI.OvMenuGate.Blocking = true;
            if (Hud != null && !Hud.PromptVisible) Hud.Prompt("Сохранение не загружено", blockedText);
            Hud?.SetVisible(false);
            Keyboard key = OpsInput.Keyboard;
            if (key == null) return;
            if (key.escapeKey.wasPressedThisFrame) OnlyVolunteers.UI.OvMenuGate.ConsumeEscape();
            if (recoveryBackup != null && (key.digit1Key.wasPressedThisFrame || key.numpad1Key.wasPressedThisFrame)) ChooseBackup();
            else if (key.digit2Key.wasPressedThisFrame || key.numpad2Key.wasPressedThisFrame) ChooseNewFile();
            else if (key.digit3Key.wasPressedThisFrame || key.numpad3Key.wasPressedThisFrame) QuitUntouched();
        }

        /// <summary>Prompt 1: the newest valid backup is copied into a new file that becomes the active save; the scene
        /// reloads and loads it. The failed file and its backups stay as they are.</summary>
        public bool ChooseBackup()
        {
            if (!WriteBlocked || recoveryBackup == null) return false;
            try
            {
                string path = CaptureSaveStore.RestoreBackupToNewFile(BaseSavePath, recoveryBackup.Path, DateTime.UtcNow);
                Debug.Log($"[CAPTURE] save prompt: backup {recoveryBackup.Path} copied to {path}; reloading");
            }
            catch (Exception e)
            {
                Debug.LogError("[CAPTURE] could not restore the backup: " + e);
                Toast("Резервная копия не скопировалась: " + e.Message, CaptureHud.Bad, 5f);
                return false;
            }
            ReloadScene();
            return true;
        }

        /// <summary>Prompt 2: a new game whose first save goes to a new file; the failed file is not touched.</summary>
        public bool ChooseNewFile()
        {
            if (!WriteBlocked) return false;
            try
            {
                string path = CaptureSaveStore.StartNewFile(BaseSavePath, DateTime.UtcNow);
                Debug.Log($"[CAPTURE] save prompt: new game in {path}; reloading");
            }
            catch (Exception e)
            {
                Debug.LogError("[CAPTURE] could not start a new save file: " + e);
                Toast("Новый файл не создался: " + e.Message, CaptureHud.Bad, 5f);
                return false;
            }
            ReloadScene();
            return true;
        }

        private void QuitUntouched()
        {
            Debug.Log("[CAPTURE] save prompt: quit, nothing written");
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
    }

    /// <summary>One LMB, two grabbers on the map pawn: the map's PhysicsGrabber (NPC bodies, props) and the operation's
    /// NetworkGrabber (the patient, the gurney, operation items: NetworkPhysicsBody). Before the PhysicsGrabber reads the
    /// button, this hands a NetworkPhysicsBody under the crosshair to the NetworkGrabber alone.</summary>
    [DefaultExecutionOrder(-300)]
    public sealed class CaptureGrabArbiter : MonoBehaviour
    {
        private GreyboxKccPawn pawn;
        private PhysicsGrabber grabber;
        private bool parked, bagSuppressed, priorNetworkSuppressed;
        private NetworkGrabber networkGrabber;
        private NetworkInventory networkInventory;

        public void Init(GreyboxKccPawn owner)
        {
            pawn = owner;
            grabber = pawn != null ? pawn.GetComponentInChildren<PhysicsGrabber>(true) : null;
            networkGrabber = pawn != null ? pawn.GetComponent<NetworkGrabber>() : null;
            networkInventory = pawn != null ? pawn.GetComponent<NetworkInventory>() : null;
        }

        private void Update()
        {
            if (grabber == null || pawn == null || pawn.ViewCamera == null) return;
            // A body bag carried with E: LMB throws it, so neither grabber takes the button meanwhile. A field tool in hand
            // (round 2): LMB uses the tool; dragging only with empty hands (a body held when the tool is taken is let go).
            var director = CaptureDirector.Instance;
            bool bag = director != null && director.Disposal != null && director.Disposal.Hands != null && director.Disposal.Hands.Carrying != null;
            bool tool = director != null && director.Kit != null && director.Kit.Tool != FieldTool.Hands && !director.Kit.Suspended;
            if (tool && grabber.IsHolding && !grabber.ScriptDriven) grabber.ScriptRelease();
            if (bag || tool)
            {
                if (!bagSuppressed && networkGrabber != null) { priorNetworkSuppressed = networkGrabber.InputSuppressed; networkGrabber.InputSuppressed = true; }
                bagSuppressed = true; Park(true); return;
            }
            if (bagSuppressed) { if (networkGrabber != null) networkGrabber.InputSuppressed = priorNetworkSuppressed; bagSuppressed = false; }
            if (grabber.IsHolding) { if (parked) Park(false); return; }
            if (grabber.ScriptDriven && !parked) return; // a test drives it
            Transform eye = pawn.ViewCamera.transform;
            bool network = UnityEngine.Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, 3f, ~(1 << OvLayers.VehicleInterior), QueryTriggerInteraction.Ignore)
                           && hit.collider.GetComponentInParent<NetworkPhysicsBody>() != null;
            Park(network);
        }

        private void Park(bool on)
        {
            if (on == parked) return;
            parked = on;
            grabber.ScriptDriven = on;
        }
    }
}
