using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Network;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Scene object of the dev scene: when the server starts it spawns the operating table (a pushable gurney
    /// prefab with the gameplay components) at this transform and registers it with the existing grab allow-list.</summary>
    public sealed class OperationStage1Spawner : MonoBehaviour
    {
        [SerializeField] private NetworkOperationTable tablePrefab;
        private NetworkManager manager;
        private NetworkOperationTable spawned;
        public NetworkOperationTable Spawned => spawned;

        private void Start()
        {
            manager = FindAnyObjectByType<NetworkManager>();
            if (manager == null || tablePrefab == null) { Debug.LogError("[OPS] spawner needs a NetworkManager and a table prefab", this); return; }
            manager.ServerManager.OnServerConnectionState += OnServerState;
            if (manager.ServerManager.Started) SpawnTable();
        }
        private void OnDestroy()
        {
            if (manager != null && manager.ServerManager != null) manager.ServerManager.OnServerConnectionState -= OnServerState;
        }
        private void OnServerState(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started) SpawnTable();
            else if (args.ConnectionState == LocalConnectionState.Stopped) spawned = null;
        }
        private void SpawnTable()
        {
            if (spawned != null) return;
            spawned = Instantiate(tablePrefab, transform.position, transform.rotation);
            spawned.name = tablePrefab.name;
            manager.ServerManager.Spawn(spawned.NetworkObject);
            var body = spawned.GetComponent<NetworkPhysicsBody>();
            if (body != null) NetworkSession.Active?.RegisterBody(body);
        }
    }
}
