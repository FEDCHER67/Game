using System;
using FishNet.Managing;
using FishNet.Object;
using UnityEngine;

namespace Friendslop.Network.Physics.Validation
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(FishNetSessionController), typeof(NetworkManager))]
    public sealed class NetworkPhysicsTortureRunner : MonoBehaviour
    {
        private const string LogPrefix = "[Stage12.4]";

        [SerializeField] private NetworkObject sharedBodyPrefab;
        [SerializeField] private Vector3[] sharedBodySpawnPositions =
        {
            new Vector3(-2f, 1.25f, 2f),
            new Vector3(0f, 1.25f, 2f),
            new Vector3(2f, 1.25f, 2f),
            new Vector3(0f, 3f, 4f)
        };

        private FishNetSessionController _session;
        private NetworkManager _networkManager;
        private string _role = "idle";
        private string _address = "127.0.0.1";
        private ushort _port = 7770;
        private bool _worldSpawned;

        private void Awake()
        {
            _session = GetComponent<FishNetSessionController>();
            _networkManager = GetComponent<NetworkManager>();
            Application.runInBackground = true;
        }

        private void Start()
        {
            string requestedRole = GetArgument("--friendslop-role");
            _address = GetArgument("--friendslop-address") ?? _address;
            _port = ParsePort(GetArgument("--friendslop-port"), _port);

            if (string.Equals(requestedRole, "host", StringComparison.OrdinalIgnoreCase))
                StartHost();
            else if (string.Equals(requestedRole, "client", StringComparison.OrdinalIgnoreCase))
                StartClient();
        }

        private void Update()
        {
            if (!_worldSpawned && _networkManager.ServerManager.Started)
                SpawnSharedWorld();
        }

        private void OnGUI()
        {
            GUILayout.BeginArea(new Rect(12f, 12f, 470f, Screen.height - 24f), GUI.skin.box);
            GUILayout.Label("Stage 12.4 — Network Physics Torture Test");
            GUILayout.Label($"Role: {_role}  Session: {_session.Snapshot.State}  Participants: {_session.Snapshot.ParticipantCount}");
            GUILayout.Label("WASD move | Mouse look | Space jump | Hold LMB grab | Release LMB drop");
            GUILayout.Label("Esc unlocks cursor | RMB relocks cursor");

            if (_role == "idle")
            {
                if (GUILayout.Button("Start Host"))
                    StartHost();
                if (GUILayout.Button("Start Client"))
                    StartClient();
            }
            else if (GUILayout.Button("Stop Session"))
            {
                _session.Stop();
                _role = "stopping";
            }

            NetworkPhysicsBody[] bodies = FindObjectsByType<NetworkPhysicsBody>(FindObjectsSortMode.InstanceID);
            foreach (NetworkPhysicsBody body in bodies)
            {
                string holder = body.IsLeased ? body.HolderConnectionId.ToString() : "none";
                GUILayout.Label($"Body {body.ObjectId}: holder={holder} pos={body.transform.position:F2}");
            }

            if (!string.IsNullOrWhiteSpace(_session.Snapshot.LastFailure))
                GUILayout.Label($"Last failure: {_session.Snapshot.LastFailure}");
            GUILayout.EndArea();
        }

        private void StartHost()
        {
            if (_session.StartHost(_port))
            {
                _role = "host";
                Debug.Log($"{LogPrefix} Host requested on port {_port}.", this);
            }
        }

        private void StartClient()
        {
            if (_session.StartClient(_address, _port))
            {
                _role = "client";
                Debug.Log($"{LogPrefix} Client requested for {_address}:{_port}.", this);
            }
        }

        private void SpawnSharedWorld()
        {
            if (sharedBodyPrefab == null)
            {
                Debug.LogError($"{LogPrefix} Shared body prefab is not assigned.", this);
                return;
            }

            _worldSpawned = true;
            foreach (Vector3 position in sharedBodySpawnPositions)
            {
                NetworkObject body = Instantiate(sharedBodyPrefab, position, Quaternion.identity);
                _networkManager.ServerManager.Spawn(body);
            }

            Debug.Log($"{LogPrefix} Spawned {sharedBodySpawnPositions.Length} ownerless shared bodies.", this);
        }

        private static string GetArgument(string name)
        {
            string prefix = name + "=";
            foreach (string argument in Environment.GetCommandLineArgs())
            {
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    return argument.Substring(prefix.Length);
            }

            return null;
        }

        private static ushort ParsePort(string value, ushort fallback)
        {
            return ushort.TryParse(value, out ushort port) && port > 0 ? port : fallback;
        }
    }
}
