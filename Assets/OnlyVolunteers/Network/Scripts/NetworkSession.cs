using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Managing.Server;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkManager))]
    public sealed class NetworkSession : MonoBehaviour
    {
        private const int MaxPlayers = 4;
        private const int TestBodyCount = 8;
        private const ushort DefaultPort = 7770;

        [SerializeField] private NetworkPlayer playerPrefab;
        [SerializeField] private NetworkPhysicsBody bodyPrefab;
        [SerializeField] private Transform[] playerSpawns = new Transform[MaxPlayers];
        [SerializeField] private Transform[] bodySpawns = new Transform[TestBodyCount];
        [SerializeField] private Camera menuCamera;

        private readonly Dictionary<int, NetworkPlayer> players = new();
        private readonly Dictionary<int, int> slots = new();
        private readonly List<NetworkPhysicsBody> bodies = new();
        private NetworkManager manager;
        private NetworkPlayer localPlayer;
        private string address = "127.0.0.1";
        private string portText = DefaultPort.ToString();
        private string status = "Offline";
        private bool hostRequested;
        private bool starting;
        private bool panelOpen = true;

        public static NetworkSession Active { get; private set; }
        public int ParticipantCount => manager != null && manager.ServerManager.Started
            ? players.Count : manager != null && manager.ClientManager.Started
                ? manager.ClientManager.Clients.Count : 0;

        private void Awake()
        {
            if (Active != null && Active != this)
            {
                Debug.LogError("[OV Network] Duplicate session composition");
                enabled = false;
                return;
            }
            Active = this;
            manager = GetComponent<NetworkManager>();
            Application.runInBackground = true;
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }

        private void Start()
        {
            manager.ServerManager.OnServerConnectionState += ServerStateChanged;
            manager.ServerManager.OnRemoteConnectionState += RemoteStateChanged;
            manager.SceneManager.OnClientLoadedStartScenes += ClientLoadedStartScenes;
            manager.ClientManager.OnClientConnectionState += ClientStateChanged;
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "-ov-port" && i + 1 < args.Length) portText = args[++i];
                else if (args[i] == "-ov-client")
                {
                    if (i + 1 < args.Length && !args[i + 1].StartsWith("-"))
                        address = args[++i];
                }
            }

            if (Array.Exists(args, x => x == "-ov-host")) StartHost();
            else if (Array.Exists(args, x => x == "-ov-client")) StartClient();
        }

        private void OnDestroy()
        {
            if (manager != null && manager.Initialized)
            {
                manager.ServerManager.OnServerConnectionState -= ServerStateChanged;
                manager.ServerManager.OnRemoteConnectionState -= RemoteStateChanged;
                manager.SceneManager.OnClientLoadedStartScenes -= ClientLoadedStartScenes;
                manager.ClientManager.OnClientConnectionState -= ClientStateChanged;
            }
            if (Active == this) Active = null;
        }

        private bool TryPort(out ushort port)
        {
            if (ushort.TryParse(portText, out port) && port != 0) return true;
            status = "Port must be 1–65535";
            return false;
        }

        public void StartHost()
        {
            if (starting || manager.ServerManager.Started || manager.ClientManager.Started || !TryPort(out ushort port))
                return;
            starting = true;
            hostRequested = true;
            manager.TransportManager.Transport.SetMaximumClients(MaxPlayers);
            manager.TransportManager.Transport.SetServerBindAddress("0.0.0.0", IPAddressType.IPv4);
            status = "Starting host";
            if (!manager.ServerManager.StartConnection(port))
            {
                hostRequested = false;
                starting = false;
                status = "Server start failed";
            }
        }

        public void StartClient()
        {
            if (starting || manager.ServerManager.Started || manager.ClientManager.Started || !TryPort(out ushort port))
                return;
            starting = true;
            hostRequested = false;
            status = "Connecting to " + address + ":" + port;
            if (!manager.ClientManager.StartConnection(address, port))
            {
                starting = false;
                status = "Client start failed";
            }
        }

        public void StopSession()
        {
            hostRequested = false;
            starting = false;
            status = "Stopping";
            if (manager.ServerManager.Started) DespawnSessionObjects();
            if (manager.ClientManager.Started) manager.ClientManager.StopConnection();
            if (manager.ServerManager.Started) manager.ServerManager.StopConnection(true);
            LocalPlayerChanged(null);
        }

        public bool IsAllowedBody(NetworkPhysicsBody body) =>
            manager != null && manager.ServerManager.Started && bodies.Contains(body);

        private void ServerStateChanged(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started)
            {
                Debug.Log("[OV Network] server started");
                SpawnBodies();
                if (hostRequested)
                {
                    status = "Starting local client";
                    manager.ClientManager.StartConnection("127.0.0.1", manager.TransportManager.Transport.GetPort());
                }
            }
            else if (args.ConnectionState == LocalConnectionState.Stopped)
            {
                hostRequested = false;
                starting = false;
                CleanupLocalReferences();
                status = "Server stopped";
            }
        }

        private void ClientStateChanged(ClientConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started)
            {
                starting = false;
                status = manager.ServerManager.Started ? "Host connected" : "Client connected";
                Debug.Log("[OV Network] client transport connected; ID assigned on player spawn");
            }
            else if (args.ConnectionState == LocalConnectionState.Stopped)
            {
                starting = false;
                status = manager.ServerManager.Started ? "Server only" : "Disconnected";
                LocalPlayerChanged(null);
            }
        }

        private void RemoteStateChanged(NetworkConnection connection, RemoteConnectionStateArgs args)
        {
            if (args.ConnectionState != RemoteConnectionState.Stopped) return;
            int id = connection.ClientId;
            if (players.TryGetValue(id, out var player))
            {
                players.Remove(id);
                slots.Remove(id);
                if (player != null && player.NetworkObject.IsSpawned)
                    manager.ServerManager.Despawn(player.NetworkObject);
                Debug.Log($"[OV Network] player despawned id={id}, participants={players.Count}");
            }
        }

        private void ClientLoadedStartScenes(NetworkConnection connection, bool asServer)
        {
            if (!asServer || !connection.IsActive || players.ContainsKey(connection.ClientId)) return;
            if (players.Count >= MaxPlayers)
            {
                manager.ServerManager.Kick(connection, KickReason.UnexpectedProblem);
                return;
            }

            int slot = 0;
            while (slots.ContainsValue(slot) && slot < MaxPlayers) slot++;
            if (slot >= MaxPlayers || playerPrefab == null || playerSpawns.Length <= slot ||
                playerSpawns[slot] == null)
            {
                manager.ServerManager.Kick(connection, KickReason.UnexpectedProblem);
                return;
            }

            var spawn = playerSpawns[slot];
            var player = Instantiate(playerPrefab, spawn.position, spawn.rotation);
            manager.ServerManager.Spawn(player.NetworkObject, connection);
            manager.SceneManager.AddOwnerToDefaultScene(player.NetworkObject);
            players.Add(connection.ClientId, player);
            slots.Add(connection.ClientId, slot);
            Debug.Log($"[OV Network] player spawned id={connection.ClientId}, slot={slot}, participants={players.Count}");
        }

        private void SpawnBodies()
        {
            if (bodyPrefab == null || bodies.Count != 0) return;
            float[] masses = { 5f, 5f, 5f, 20f, 20f, 50f, 50f, 100f };
            for (int i = 0; i < masses.Length && i < bodySpawns.Length; i++)
            {
                if (bodySpawns[i] == null) continue;
                var body = Instantiate(bodyPrefab, bodySpawns[i].position, bodySpawns[i].rotation);
                body.name = "NetworkBody_" + masses[i] + "kg_" + i;
                body.Body.mass = masses[i];
                manager.ServerManager.Spawn(body.NetworkObject);
                bodies.Add(body);
            }
            Debug.Log($"[OV Network] server bodies spawned={bodies.Count}");
        }

        private void DespawnSessionObjects()
        {
            foreach (var player in players.Values)
                if (player != null && player.NetworkObject.IsSpawned)
                    manager.ServerManager.Despawn(player.NetworkObject);
            foreach (var body in bodies)
                if (body != null && body.NetworkObject.IsSpawned)
                    manager.ServerManager.Despawn(body.NetworkObject);
            players.Clear();
            slots.Clear();
            bodies.Clear();
        }

        private void CleanupLocalReferences()
        {
            foreach (var player in players.Values) if (player != null) Destroy(player.gameObject);
            foreach (var body in bodies) if (body != null) Destroy(body.gameObject);
            players.Clear();
            slots.Clear();
            bodies.Clear();
        }

        public void LocalPlayerChanged(NetworkPlayer player)
        {
            localPlayer = player;
            panelOpen = player == null;
            if (menuCamera != null)
            {
                menuCamera.enabled = player == null;
                var audio = menuCamera.GetComponent<AudioListener>();
                if (audio != null) audio.enabled = player == null;
            }
            if (player == null)
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
        }

        private void Update()
        {
            if (localPlayer != null && Input.GetKeyDown(KeyCode.Escape))
            {
                panelOpen = !panelOpen;
                localPlayer.SetPanelOpen(panelOpen);
            }
        }

        private void OnGUI()
        {
            if (!panelOpen && localPlayer != null) return;
            GUILayout.BeginArea(new Rect(16, 16, 340, 260), GUI.skin.box);
            GUILayout.Label("VOLUNTEERS ONLY — Network Test");
            GUILayout.BeginHorizontal();
            GUILayout.Label("Address", GUILayout.Width(65));
            address = GUILayout.TextField(address);
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            GUILayout.Label("Port", GUILayout.Width(65));
            portText = GUILayout.TextField(portText, 5);
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Host")) StartHost();
            if (GUILayout.Button("Client")) StartClient();
            if (GUILayout.Button("Disconnect / Stop")) StopSession();
            GUILayout.EndHorizontal();
            GUILayout.Label("State: " + status);
            GUILayout.Label("Role: " + (manager.ServerManager.Started ? "Host" :
                manager.ClientManager.Started ? "Client" : "Offline"));
            GUILayout.Label("Participants: " + ParticipantCount + " / " + MaxPlayers);
            GUILayout.Label("Local ID: " + (manager.ClientManager.Started
                ? manager.ClientManager.Connection.ClientId.ToString() : "—"));
            GUILayout.Label("Esc: show / hide panel");
            GUILayout.EndArea();
        }
    }
}
