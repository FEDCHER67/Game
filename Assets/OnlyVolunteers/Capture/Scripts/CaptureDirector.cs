using OnlyVolunteers.Inventory;
using System;
using System.Collections.Generic;
using System.IO;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using OnlyVolunteers.Clinic;
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

        private NetworkManager manager;
        private float nextAutosave;
        private bool hostStarted;
        private int portTries;
        private bool tableMode;
        private float playTime;

        /// <summary>The player's save; editor sessions and automated runs never touch it (their own slots).</summary>
        public string SavePath => Path.Combine(Application.persistentDataPath, "OnlyVolunteers",
            !string.IsNullOrEmpty(CaptureTestHooks.SaveSlot) ? CaptureTestHooks.SaveSlot :
#if UNITY_EDITOR
            "capture_stageA_editor.json");
#else
            SaveFileName);
#endif

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
            StartHost();
        }

        private void StartHost()
        {
            if (manager.ServerManager.Started) return;
            ushort port = (ushort)(Port + portTries);
            // Skip ports another process (an operations build, a stale editor socket) holds: no "server failed" error.
            while (portTries < 10 && !UdpPortFree(port)) { portTries++; port = (ushort)(Port + portTries); }
            manager.TransportManager.Transport.SetMaximumClients(4);
            manager.TransportManager.Transport.SetServerBindAddress("127.0.0.1", IPAddressType.IPv4);
            bool ok = manager.ServerManager.StartConnection(port);
            Debug.Log($"[CAPTURE] solo host: server on 127.0.0.1:{port} start={ok}");
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
        }

        private void ClientLoaded(NetworkConnection connection, bool asServer)
        {
            if (!asServer || PawnNetworkObject == null || !connection.IsActive) return;
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

        /// <summary>Game time when the save was restored (the clocks run from here).</summary>
        public float LoadedAt { get; private set; }
        private void LoadAfterStart()
        {
            Loaded = true; LoadedAt = Time.time;
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-capture-fresh") >= 0) { Toast("Новая игра", CaptureHud.Neutral); return; }
            if (File.Exists(SavePath)) Load();
            else Toast("Поймай кого-нибудь в Хуторе и привези в сарай у хижины деда", CaptureHud.Neutral, 6f);
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
            // Safety net: a downed NPC that missed the incident (e.g. already lying at load) still gets an identity.
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && npc.isActiveAndEnabled && (npc.State == NpcState.Down || npc.InCargo) && !npc.TryGetComponent(out CaptureNpc _))
                    Ensure(npc);
            Keyboard key = OpsInput.Keyboard;
            if (key != null && key.kKey.wasPressedThisFrame && !tableMode)
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
            return $"<b>{BaseName}</b>{(dist >= 0f ? $" · {dist:0} м" : "")}\nпоймано {captured} · в бусике {inVan} · {table}\nK — сохранить · Shift+K — новая игра";
        }

        private void OnApplicationQuit()
        {
            // Quitting saves the game (D13); automated runs keep their own explicit saves.
            if (Ready && Loaded && string.IsNullOrEmpty(CaptureTestHooks.SaveSlot)) Save(false);
        }

        // ---------- save / load (D13) ----------

        public bool Save(bool announce)
        {
            try
            {
                var data = new CaptureSaveData { scene = SceneManager.GetActiveScene().path, savedUtc = DateTime.UtcNow.ToString("o"), playTime = playTime };
                CaptureSave.Write(this, data);
                Directory.CreateDirectory(Path.GetDirectoryName(SavePath));
                string tmp = SavePath + ".tmp";
                File.WriteAllText(tmp, JsonUtility.ToJson(data, true));
                if (File.Exists(SavePath)) File.Replace(tmp, SavePath, SavePath + ".bak");
                else File.Move(tmp, SavePath);
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

        public bool Load()
        {
            try
            {
                var data = JsonUtility.FromJson<CaptureSaveData>(File.ReadAllText(SavePath));
                if (data == null || data.version != CaptureSaveData.CurrentVersion) { Toast("Сохранение не подходит — новая игра", CaptureHud.Warn); return false; }
                CaptureSave.Read(this, data);
                Toast($"Загружено: поймано {data.npcs.Count}" + (data.table != null && data.table.patient != null ? ", на столе пациент" : ""), CaptureHud.Neutral);
                Debug.Log($"[CAPTURE] loaded {data.npcs.Count} NPCs from {SavePath}");
                return true;
            }
            catch (Exception e)
            {
                Debug.LogError("[CAPTURE] load failed: " + e);
                Toast("Сохранение не читается — новая игра", CaptureHud.Warn);
                return false;
            }
        }

        public void NewGame()
        {
            try
            {
                if (File.Exists(SavePath)) File.Delete(SavePath);
                if (File.Exists(SavePath + ".bak")) File.Delete(SavePath + ".bak");
            }
            catch (Exception e) { Debug.LogWarning("[CAPTURE] could not delete the save: " + e.Message); }
            Loaded = false;
            if (manager != null)
            {
                if (manager.ClientManager.Started) manager.ClientManager.StopConnection();
                if (manager.ServerManager.Started) manager.ServerManager.StopConnection(true);
            }
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex >= 0 ? SceneManager.GetActiveScene().buildIndex : 0);
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
