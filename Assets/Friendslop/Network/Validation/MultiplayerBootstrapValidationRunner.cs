using System;
using System.Collections;
using System.Linq;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using UnityEngine;

namespace Friendslop.Network.Validation
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(FishNetSessionController))]
    public sealed class MultiplayerBootstrapValidationRunner : MonoBehaviour
    {
        private const string Prefix = "[Stage12.2]";
        private const float StepTimeoutSeconds = 75f;

        private FishNetSessionController _session;
        private NetworkManager _networkManager;
        private bool _waitSucceeded;
        private string _address = "127.0.0.1";
        private ushort _port = 7770;
        private ushort _failedPort = 7771;

        private void Awake()
        {
            _session = GetComponent<FishNetSessionController>();
            _networkManager = GetComponent<NetworkManager>();
        }

        private void Start()
        {
            string role = GetArgument("--friendslop-role");
            if (string.IsNullOrEmpty(role))
                return;

            Application.runInBackground = true;
            _address = GetArgument("--friendslop-address") ?? _address;
            _port = ParsePort(GetArgument("--friendslop-port"), _port);
            _failedPort = ParsePort(GetArgument("--friendslop-failed-port"), (ushort)(_port + 1));

            if (string.Equals(role, "host", StringComparison.OrdinalIgnoreCase))
                StartCoroutine(RunHostScenario());
            else if (string.Equals(role, "client", StringComparison.OrdinalIgnoreCase))
                StartCoroutine(RunClientScenario());
            else
                Abort($"Unknown validation role '{role}'. Use host or client.");
        }

        private IEnumerator RunHostScenario()
        {
            if (!_session.StartHost(_port))
            {
                Abort("Host start request was rejected.");
                yield break;
            }

            yield return WaitFor(() => _session.Snapshot.State == SessionState.Host
                && _session.Snapshot.ParticipantCount == 1, StepTimeoutSeconds);
            if (!RequireWait("Host did not reach Host with exactly one neutral player."))
                yield break;
            if (!ValidateServerPlayers(1, out string failure))
            {
                Abort(failure);
                yield break;
            }

            EntityId hostObjectEntityId = GetOnlyPlayer(_session.Snapshot.LocalConnectionId.Value).GetEntityId();
            Debug.Log($"{Prefix} HOST_ONLY PASS participants=1 local={_session.Snapshot.LocalConnectionId.Value}.");

            yield return WaitFor(() => _session.Snapshot.ParticipantCount == 2, StepTimeoutSeconds);
            if (!RequireWait("External client did not produce exactly two observed players."))
                yield break;
            if (!ValidateServerPlayers(2, out failure))
            {
                Abort(failure);
                yield break;
            }

            NetworkConnection firstRemote = GetRemoteConnection();
            NetworkObject firstRemotePlayer = firstRemote.FirstObject;
            EntityId firstRemoteObjectEntityId = firstRemotePlayer.GetEntityId();
            int firstRemoteConnectionId = firstRemote.ClientId;
            Debug.Log($"{Prefix} EXTERNAL_CLIENT PASS participants=2 remote={firstRemoteConnectionId} owner={firstRemote.FirstObject.Owner.ClientId}.");

            yield return WaitFor(() => !_networkManager.ServerManager.Clients.ContainsKey(firstRemoteConnectionId)
                && (firstRemotePlayer == null || !firstRemotePlayer.IsSpawned), StepTimeoutSeconds);
            if (!RequireWait("Remote disconnect did not remove its original connection and player."))
                yield break;
            if (!_networkManager.ServerManager.Clients.ContainsKey(_session.Snapshot.LocalConnectionId.Value)
                || !GetOnlyPlayer(_session.Snapshot.LocalConnectionId.Value).GetEntityId().Equals(hostObjectEntityId))
            {
                Abort("Remote disconnect removed or replaced the host player.");
                yield break;
            }

            Debug.Log($"{Prefix} REMOTE_DISCONNECT PASS oldRemote={firstRemoteConnectionId} staleRemote=false hostPreserved=true.");

            yield return WaitFor(() => _session.Snapshot.ParticipantCount == 2, StepTimeoutSeconds);
            if (!RequireWait("Remote reconnect did not return the host to two players."))
                yield break;
            if (!ValidateServerPlayers(2, out failure))
            {
                Abort(failure);
                yield break;
            }

            NetworkConnection secondRemote = GetRemoteConnection();
            if (secondRemote.FirstObject.GetEntityId().Equals(firstRemoteObjectEntityId))
            {
                Abort("Reconnect reused the stale remote player instance.");
                yield break;
            }

            Debug.Log($"{Prefix} RECONNECT PASS participants=2 remote={secondRemote.ClientId} freshPlayer=true.");

            yield return WaitFor(() => _session.Snapshot.ParticipantCount == 1
                && _networkManager.ServerManager.Clients.Count == 1, StepTimeoutSeconds);
            if (!RequireWait("Second remote disconnect did not cleanly return to one player."))
                yield break;

            _session.Stop();
            yield return WaitFor(() => _session.Snapshot.State == SessionState.Stopped, StepTimeoutSeconds);
            if (!RequireWait("Host shutdown did not reach Stopped."))
                yield break;
            Debug.Log($"{Prefix} SHUTDOWN PASS.");

            if (!_session.StartHost(_port))
            {
                Abort("Restart host request was rejected.");
                yield break;
            }

            yield return WaitFor(() => _session.Snapshot.State == SessionState.Host
                && _session.Snapshot.ParticipantCount == 1, StepTimeoutSeconds);
            if (!RequireWait("Restarted host did not reach Host with one player."))
                yield break;
            if (!ValidateServerPlayers(1, out failure))
            {
                Abort(failure);
                yield break;
            }

            Debug.Log($"{Prefix} RESTART PASS participants=1.");
            _session.Stop();
            yield return WaitFor(() => _session.Snapshot.State == SessionState.Stopped, StepTimeoutSeconds);
            if (!RequireWait("Final host shutdown did not reach Stopped."))
                yield break;

            Debug.Log($"{Prefix} HOST_SEQUENCE PASS.");
            Application.Quit(0);
        }

        private IEnumerator RunClientScenario()
        {
            _session.StartClient(_address, _failedPort);
            yield return WaitFor(() => _session.Snapshot.State == SessionState.Failed, StepTimeoutSeconds);
            if (!RequireWait("Failed connection did not reach Failed."))
                yield break;
            if (string.IsNullOrWhiteSpace(_session.Snapshot.LastFailure)
                || _session.Snapshot.ParticipantCount != 0)
            {
                Abort("Failed connection did not expose an actionable error and clean partial state.");
                yield break;
            }

            Debug.Log($"{Prefix} FAILED_CONNECTION PASS diagnostic='{_session.Snapshot.LastFailure}'.");

            if (!_session.StartClient(_address, _port))
            {
                Abort("Valid client start after failure was rejected.");
                yield break;
            }

            yield return WaitFor(() => _session.Snapshot.State == SessionState.Client
                && _session.Snapshot.ParticipantCount == 2, StepTimeoutSeconds);
            if (!RequireWait("Valid client did not reach Client with two observed players."))
                yield break;
            Debug.Log($"{Prefix} CLIENT_CONNECT PASS participants=2 local={_session.Snapshot.LocalConnectionId.Value}.");

            yield return new WaitForSecondsRealtime(1f);
            _session.Stop();
            yield return WaitFor(() => _session.Snapshot.State == SessionState.Stopped, StepTimeoutSeconds);
            if (!RequireWait("Client disconnect did not reach Stopped."))
                yield break;

            if (!_session.StartClient(_address, _port))
            {
                Abort("Reconnect request was rejected.");
                yield break;
            }

            yield return WaitFor(() => _session.Snapshot.State == SessionState.Client
                && _session.Snapshot.ParticipantCount == 2, StepTimeoutSeconds);
            if (!RequireWait("Reconnected client did not reach Client with two observed players."))
                yield break;
            Debug.Log($"{Prefix} CLIENT_RECONNECT PASS participants=2 local={_session.Snapshot.LocalConnectionId.Value}.");

            yield return new WaitForSecondsRealtime(1f);
            _session.Stop();
            yield return WaitFor(() => _session.Snapshot.State == SessionState.Stopped, StepTimeoutSeconds);
            if (!RequireWait("Final client shutdown did not reach Stopped."))
                yield break;

            Debug.Log($"{Prefix} CLIENT_SEQUENCE PASS.");
            Application.Quit(0);
        }

        private IEnumerator WaitFor(Func<bool> predicate, float timeoutSeconds)
        {
            float deadline = Time.realtimeSinceStartup + timeoutSeconds;
            while (!predicate() && Time.realtimeSinceStartup < deadline)
                yield return null;

            _waitSucceeded = predicate();
        }

        private bool RequireWait(string failure)
        {
            if (_waitSucceeded)
                return true;

            Abort(failure);
            return false;
        }

        private bool ValidateServerPlayers(int expectedCount, out string failure)
        {
            if (_networkManager.ServerManager.Clients.Count != expectedCount)
            {
                failure = $"Expected {expectedCount} server connections but found {_networkManager.ServerManager.Clients.Count}.";
                return false;
            }

            foreach (NetworkConnection connection in _networkManager.ServerManager.Clients.Values)
            {
                if (connection.Objects.Count != 1 || connection.FirstObject == null)
                {
                    failure = $"Connection {connection.ClientId} does not own exactly one player object.";
                    return false;
                }

                NetworkObject player = connection.FirstObject;
                if (player.Owner != connection || player.GetComponent<NeutralNetworkPlayer>() == null)
                {
                    failure = $"Connection {connection.ClientId} has incorrect neutral-player ownership.";
                    return false;
                }
            }

            failure = null;
            return true;
        }

        private NetworkObject GetOnlyPlayer(int connectionId)
        {
            return _networkManager.ServerManager.Clients[connectionId].FirstObject;
        }

        private NetworkConnection GetRemoteConnection()
        {
            int localId = _session.Snapshot.LocalConnectionId.Value;
            return _networkManager.ServerManager.Clients.Values.Single(connection => connection.ClientId != localId);
        }

        private void Abort(string failure)
        {
            Debug.LogError($"{Prefix} FAIL {failure}");
            _session?.Stop();
            Application.Quit(2);
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
