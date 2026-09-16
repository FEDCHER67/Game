using FishNet.Object;
using UnityEngine;

namespace Friendslop.Network
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(NetworkObject))]
    public sealed class NeutralNetworkPlayer : NetworkBehaviour
    {
        private FishNetSessionController _sessionController;
        private int _connectionId;
        private int _objectId;

        public override void OnStartClient()
        {
            base.OnStartClient();
            _sessionController = NetworkManager.GetComponent<FishNetSessionController>();
            _connectionId = Owner.ClientId;
            _objectId = ObjectId;
            _sessionController?.ObservePlayerSpawned(_connectionId, _objectId, IsOwner);
        }

        public override void OnStopClient()
        {
            _sessionController?.ObservePlayerDespawned(_connectionId, _objectId);
            _sessionController = null;
            base.OnStopClient();
        }
    }
}
