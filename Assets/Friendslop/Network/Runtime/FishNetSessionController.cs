using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace Friendslop.Network
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(NetworkManager))]
    public sealed class FishNetSessionController : MonoBehaviour, ISessionController
    {
        private const string LogPrefix = "[Friendslop.Network]";

        [SerializeField] private NetworkManager networkManager;
        [SerializeField] private NetworkObject neutralPlayerPrefab;

        private readonly SessionLifecycle _lifecycle = new SessionLifecycle();
        private readonly ParticipantRegistry _observedParticipants = new ParticipantRegistry();
        private readonly ParticipantRegistry _serverParticipants = new ParticipantRegistry();
        private readonly Dictionary<int, int> _observedPlayerObjects = new Dictionary<int, int>();
        private readonly Dictionary<int, NetworkObject> _serverPlayers = new Dictionary<int, NetworkObject>();
        private readonly StopCompletionTracker _stopCompletion = new StopCompletionTracker();

        private Action<ServerConnectionStateArgs> _serverStateHandler;
        private Action<ClientConnectionStateArgs> _clientStateHandler;
        private Action<NetworkConnection, RemoteConnectionStateArgs> _remoteStateHandler;
        private Action<NetworkConnection, bool> _startScenesHandler;
        private Action _authenticatedHandler;
        private int? _localConnectionId;
        private string _clientAddress;
        private ushort _port;
        private LocalConnectionState _clientConnectionState = LocalConnectionState.Stopped;
        private LocalConnectionState _serverConnectionState = LocalConnectionState.Stopped;

        public SessionSnapshot Snapshot { get; private set; }
            = new SessionSnapshot(SessionState.Stopped, null, 0, null);

        public event Action<SessionSnapshot> SnapshotChanged;

        private void Awake()
        {
            if (networkManager == null)
                networkManager = GetComponent<NetworkManager>();

            if (networkManager == null || !networkManager.Initialized)
                Debug.LogError($"{LogPrefix} A ready FishNet NetworkManager is required on the same object.", this);
            if (neutralPlayerPrefab == null)
                Debug.LogError($"{LogPrefix} A neutral network player prefab must be assigned.", this);
        }

        private void OnDestroy()
        {
            UnsubscribeCallbacks();
        }

        public bool StartHost(ushort port)
        {
            if (!_stopCompletion.IsComplete)
            {
                Debug.LogWarning($"{LogPrefix} The previous session is still shutting down.", this);
                return false;
            }

            if (!_lifecycle.TryBeginHost(out int generation, out string error))
            {
                Debug.LogWarning($"{LogPrefix} {error}", this);
                return false;
            }

            PrepareAttempt(generation, "127.0.0.1", port);
            PublishSnapshot();

            if (port == 0)
            {
                FailAttempt(generation, "Host port must be greater than zero.");
                return false;
            }

            _serverConnectionState = LocalConnectionState.Starting;
            if (!networkManager.ServerManager.StartConnection(port))
            {
                _serverConnectionState = LocalConnectionState.Stopped;
                FailAttempt(generation, $"Could not start the host server on port {port}. The port may already be in use.");
                return false;
            }

            Debug.Log($"{LogPrefix} Host start requested on port {port} (generation {generation}).", this);
            return true;
        }

        public bool StartClient(string address, ushort port)
        {
            if (!_stopCompletion.IsComplete)
            {
                Debug.LogWarning($"{LogPrefix} The previous session is still shutting down.", this);
                return false;
            }

            if (!_lifecycle.TryBeginClient(out int generation, out string error))
            {
                Debug.LogWarning($"{LogPrefix} {error}", this);
                return false;
            }

            PrepareAttempt(generation, address, port);
            PublishSnapshot();

            if (string.IsNullOrWhiteSpace(address) || port == 0)
            {
                FailAttempt(generation, "Client address must be non-empty and port must be greater than zero.");
                return false;
            }

            _clientConnectionState = LocalConnectionState.Starting;
            if (!networkManager.ClientManager.StartConnection(address, port))
            {
                _clientConnectionState = LocalConnectionState.Stopped;
                FailAttempt(generation, $"Could not start a client connection to {address}:{port}.");
                return false;
            }

            Debug.Log($"{LogPrefix} Client start requested for {address}:{port} (generation {generation}).", this);
            return true;
        }

        public void Stop()
        {
            if (!_lifecycle.TryBeginStop())
                return;

            PublishSnapshot();
            Debug.Log($"{LogPrefix} Session stop requested (generation {_lifecycle.Generation}).", this);

            BeginTransportCleanup();
            networkManager.ClientManager.StopConnection();
            networkManager.ServerManager.StopConnection(true);
            TryCompleteStop(_lifecycle.Generation);
        }

        internal void ObservePlayerSpawned(int connectionId, int objectId, bool isLocalOwner)
        {
            if (_observedPlayerObjects.ContainsKey(connectionId) || !_observedParticipants.TryAdd(connectionId))
            {
                Debug.LogError($"{LogPrefix} Duplicate observed player for connection {connectionId}; object {objectId} was rejected.", this);
                return;
            }

            _observedPlayerObjects.Add(connectionId, objectId);
            Debug.Log($"{LogPrefix} Observed neutral player object {objectId} for connection {connectionId}; localOwner={isLocalOwner}.", this);
            PublishSnapshot();
        }

        internal void ObservePlayerDespawned(int connectionId, int objectId)
        {
            if (!_observedPlayerObjects.TryGetValue(connectionId, out int registeredObjectId)
                || registeredObjectId != objectId)
            {
                return;
            }

            _observedPlayerObjects.Remove(connectionId);
            _observedParticipants.Remove(connectionId);
            Debug.Log($"{LogPrefix} Removed neutral player object {objectId} for connection {connectionId}.", this);
            PublishSnapshot();
        }

        private void PrepareAttempt(int generation, string address, ushort port)
        {
            UnsubscribeCallbacks();
            ClearSessionData(despawnServerPlayers: false);
            _clientAddress = address;
            _port = port;
            _clientConnectionState = LocalConnectionState.Stopped;
            _serverConnectionState = LocalConnectionState.Stopped;
            _stopCompletion.Begin(waitForClient: false, waitForServer: false);
            SubscribeCallbacks(generation);
        }

        private void SubscribeCallbacks(int generation)
        {
            _serverStateHandler = args => OnServerConnectionState(generation, args);
            _clientStateHandler = args => OnClientConnectionState(generation, args);
            _remoteStateHandler = (connection, args) => OnRemoteConnectionState(generation, connection, args);
            _startScenesHandler = (connection, asServer) => OnClientLoadedStartScenes(generation, connection, asServer);
            _authenticatedHandler = () => OnAuthenticated(generation);

            networkManager.ServerManager.OnServerConnectionState += _serverStateHandler;
            networkManager.ClientManager.OnClientConnectionState += _clientStateHandler;
            networkManager.ServerManager.OnRemoteConnectionState += _remoteStateHandler;
            networkManager.SceneManager.OnClientLoadedStartScenes += _startScenesHandler;
            networkManager.ClientManager.OnAuthenticated += _authenticatedHandler;
        }

        private void UnsubscribeCallbacks()
        {
            if (networkManager == null || !networkManager.Initialized)
                return;

            if (_serverStateHandler != null)
                networkManager.ServerManager.OnServerConnectionState -= _serverStateHandler;
            if (_clientStateHandler != null)
                networkManager.ClientManager.OnClientConnectionState -= _clientStateHandler;
            if (_remoteStateHandler != null)
                networkManager.ServerManager.OnRemoteConnectionState -= _remoteStateHandler;
            if (_startScenesHandler != null)
                networkManager.SceneManager.OnClientLoadedStartScenes -= _startScenesHandler;
            if (_authenticatedHandler != null)
                networkManager.ClientManager.OnAuthenticated -= _authenticatedHandler;

            _serverStateHandler = null;
            _clientStateHandler = null;
            _remoteStateHandler = null;
            _startScenesHandler = null;
            _authenticatedHandler = null;
        }

        private void OnServerConnectionState(int generation, ServerConnectionStateArgs args)
        {
            if (generation != _lifecycle.Generation)
                return;

            _serverConnectionState = args.ConnectionState;
            if (args.ConnectionState == LocalConnectionState.Started
                && _lifecycle.State == SessionState.StartingHost)
            {
                _clientConnectionState = LocalConnectionState.Starting;
                if (!networkManager.ClientManager.StartConnection(_clientAddress, _port))
                {
                    _clientConnectionState = LocalConnectionState.Stopped;
                    FailAttempt(generation, $"The server started, but its local host client could not start on {_clientAddress}:{_port}.");
                }
                return;
            }

            if (args.ConnectionState != LocalConnectionState.Stopped)
                return;

            _stopCompletion.AcknowledgeServerStopped();
            if (_lifecycle.State == SessionState.Stopping)
            {
                TryCompleteStop(generation);
            }
            else if (_lifecycle.State == SessionState.Failed)
            {
                TryCompleteFailureCleanup();
            }
            else if (_lifecycle.State == SessionState.StartingHost || _lifecycle.State == SessionState.Host)
            {
                FailAttempt(generation, $"The host server stopped unexpectedly on port {_port}.");
            }
        }

        private void OnClientConnectionState(int generation, ClientConnectionStateArgs args)
        {
            if (generation != _lifecycle.Generation)
                return;

            _clientConnectionState = args.ConnectionState;
            if (args.ConnectionState != LocalConnectionState.Stopped)
                return;

            _stopCompletion.AcknowledgeClientStopped();
            if (_lifecycle.State == SessionState.Stopping)
            {
                TryCompleteStop(generation);
                return;
            }

            if (_lifecycle.State == SessionState.Failed)
            {
                TryCompleteFailureCleanup();
            }
            else if (_lifecycle.State == SessionState.StartingClient)
            {
                FailAttempt(generation, $"Could not connect to {_clientAddress}:{_port}. Verify that the host is running and the endpoint is correct.");
            }
            else if (_lifecycle.State == SessionState.StartingHost || _lifecycle.State == SessionState.Host
                || _lifecycle.State == SessionState.Client)
            {
                FailAttempt(generation, "The local client disconnected unexpectedly.");
            }
        }

        private void OnAuthenticated(int generation)
        {
            if (generation != _lifecycle.Generation)
                return;

            _localConnectionId = networkManager.ClientManager.Connection.ClientId;
            bool changed = _lifecycle.State == SessionState.StartingHost
                ? _lifecycle.TryMarkHostReady(generation)
                : _lifecycle.TryMarkClientReady(generation);

            if (!changed)
                return;

            Debug.Log($"{LogPrefix} Session reached {_lifecycle.State}; local connection {_localConnectionId.Value}.", this);
            PublishSnapshot();
        }

        private void OnClientLoadedStartScenes(int generation, NetworkConnection connection, bool asServer)
        {
            if (generation != _lifecycle.Generation || !asServer || !networkManager.ServerManager.Started)
                return;

            int connectionId = connection.ClientId;
            if (_serverParticipants.Contains(connectionId) || _serverPlayers.ContainsKey(connectionId))
            {
                Debug.LogError($"{LogPrefix} Duplicate player spawn request rejected for connection {connectionId}.", this);
                return;
            }

            if (neutralPlayerPrefab == null)
            {
                FailAttempt(generation, "The neutral player prefab is not assigned; accepted connection cannot receive a player.");
                return;
            }

            NetworkObject player = null;
            try
            {
                player = Instantiate(neutralPlayerPrefab);
                player.name = $"NeutralNetworkPlayer_{connectionId}";
                networkManager.ServerManager.Spawn(player, connection);
                networkManager.SceneManager.AddOwnerToDefaultScene(player);

                if (player.Owner != connection)
                    throw new InvalidOperationException($"Player ownership did not resolve to connection {connectionId}.");

                _serverPlayers.Add(connectionId, player);
                _serverParticipants.TryAdd(connectionId);
                Debug.Log($"{LogPrefix} Spawned neutral player object {player.ObjectId} for connection {connectionId}; owner={player.Owner.ClientId}.", this);
            }
            catch (Exception exception)
            {
                if (player != null)
                    Destroy(player.gameObject);
                FailAttempt(generation, $"Failed to spawn the neutral player for connection {connectionId}: {exception.Message}");
            }
        }

        private void OnRemoteConnectionState(
            int generation,
            NetworkConnection connection,
            RemoteConnectionStateArgs args)
        {
            if (generation != _lifecycle.Generation || args.ConnectionState != RemoteConnectionState.Stopped)
                return;

            RemoveServerPlayer(connection.ClientId);
        }

        private void RemoveServerPlayer(int connectionId)
        {
            _serverParticipants.Remove(connectionId);
            if (!_serverPlayers.TryGetValue(connectionId, out NetworkObject player))
                return;

            _serverPlayers.Remove(connectionId);
            if (player != null && player.IsSpawned && networkManager.ServerManager.Started)
                networkManager.ServerManager.Despawn(player);

            Debug.Log($"{LogPrefix} Server cleanup completed for connection {connectionId}.", this);
        }

        private void FailAttempt(int generation, string failure)
        {
            if (!_lifecycle.Fail(generation, failure))
                return;

            Debug.LogWarning($"{LogPrefix} {failure}", this);
            ClearSessionData(despawnServerPlayers: true);
            BeginTransportCleanup();
            networkManager.ClientManager.StopConnection();
            networkManager.ServerManager.StopConnection(true);
            PublishSnapshot();
            TryCompleteFailureCleanup();
        }

        private void TryCompleteStop(int generation)
        {
            if (!_stopCompletion.IsComplete)
                return;

            ClearSessionData(despawnServerPlayers: false);
            if (!_lifecycle.MarkStopped(generation))
                return;

            UnsubscribeCallbacks();
            Debug.Log($"{LogPrefix} Session stopped cleanly (generation {generation}).", this);
            PublishSnapshot();
        }

        private void TryCompleteFailureCleanup()
        {
            if (_lifecycle.State != SessionState.Failed || !_stopCompletion.IsComplete)
                return;

            UnsubscribeCallbacks();
            Debug.Log($"{LogPrefix} Failed session cleanup completed (generation {_lifecycle.Generation}).", this);
        }

        private void BeginTransportCleanup()
        {
            _stopCompletion.Begin(
                waitForClient: _clientConnectionState != LocalConnectionState.Stopped,
                waitForServer: _serverConnectionState != LocalConnectionState.Stopped);
        }

        private void ClearSessionData(bool despawnServerPlayers)
        {
            if (despawnServerPlayers && networkManager != null && networkManager.Initialized
                && networkManager.ServerManager.Started)
            {
                foreach (NetworkObject player in _serverPlayers.Values)
                {
                    if (player != null && player.IsSpawned)
                        networkManager.ServerManager.Despawn(player);
                }
            }

            _serverPlayers.Clear();
            _serverParticipants.Clear();
            _observedPlayerObjects.Clear();
            _observedParticipants.Clear();
            _localConnectionId = null;
        }

        private void PublishSnapshot()
        {
            Snapshot = new SessionSnapshot(
                _lifecycle.State,
                _localConnectionId,
                _observedParticipants.Count,
                _lifecycle.LastFailure);
            SnapshotChanged?.Invoke(Snapshot);
        }
    }
}
