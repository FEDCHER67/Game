using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace Friendslop.Network.Physics
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(NetworkObject), typeof(Rigidbody), typeof(Collider))]
    public sealed class NetworkPhysicsBody : NetworkBehaviour
    {
        private const string LogPrefix = "[Stage12.4]";

        [SerializeField, Min(0f)] private float springStrength = 120f;
        [SerializeField, Min(0f)] private float damping = 18f;
        [SerializeField, Min(0f)] private float maxForce = 1000f;

        private readonly GrabLeaseState _lease = new GrabLeaseState();
        private readonly SyncVar<int> _replicatedHolderConnectionId = new SyncVar<int>(-1);
        private Rigidbody _rigidbody;
        private NetworkPhysicsPlayer _holder;
        private Vector3 _localGrabPoint;

        public int HolderConnectionId => _replicatedHolderConnectionId.Value;

        public bool IsLeased => HolderConnectionId >= 0;

        private void Awake()
        {
            _rigidbody = GetComponent<Rigidbody>();
        }

        public override void OnStartServer()
        {
            _rigidbody.isKinematic = false;
            Debug.Log($"{LogPrefix} Shared body {ObjectId} entered server-authoritative simulation.", this);
        }

        public override void OnStartClient()
        {
            if (!IsServerInitialized)
                _rigidbody.isKinematic = true;
        }

        public override void OnStopServer()
        {
            ForceRelease("body stopped");
        }

        private void FixedUpdate()
        {
            if (!IsServerInitialized || _holder == null)
                return;

            if (!_holder.IsServerInitialized || !_holder.Owner.IsActive)
            {
                ForceRelease("holder unavailable");
                return;
            }

            if (_rigidbody.isKinematic)
            {
                ForceRelease("body became kinematic");
                return;
            }

            Vector3 worldGrabPoint = transform.TransformPoint(_localGrabPoint);
            Vector3 pointVelocity = _rigidbody.GetPointVelocity(worldGrabPoint);
            Vector3 force = (_holder.ServerHoldPoint - worldGrabPoint) * springStrength
                - pointVelocity * damping;

            _rigidbody.WakeUp();
            _rigidbody.AddForceAtPosition(
                Vector3.ClampMagnitude(force, maxForce),
                worldGrabPoint,
                ForceMode.Force);
        }

        internal bool TryAcquire(NetworkPhysicsPlayer player, Vector3 localGrabPoint)
        {
            if (!IsServerInitialized || player == null || !player.IsServerInitialized)
                return false;

            int connectionId = player.Owner.ClientId;
            if (!_lease.TryAcquire(connectionId))
            {
                Debug.Log($"{LogPrefix} Grab rejected for connection {connectionId} on body {ObjectId}; holder={HolderConnectionId}.", this);
                return false;
            }

            _holder = player;
            _localGrabPoint = localGrabPoint;
            _replicatedHolderConnectionId.Value = connectionId;
            _rigidbody.WakeUp();
            Debug.Log($"{LogPrefix} Grab lease granted: body={ObjectId} holder={connectionId}.", this);
            return true;
        }

        internal bool Release(NetworkPhysicsPlayer player, string reason)
        {
            if (player == null || _holder != player)
                return false;

            int connectionId = player.Owner.ClientId;
            if (!_lease.TryRelease(connectionId))
                return false;

            ClearLease(connectionId, reason);
            return true;
        }

        private bool ForceRelease(string reason)
        {
            int connectionId = _lease.HolderConnectionId ?? -1;
            if (!_lease.ForceRelease())
                return false;

            ClearLease(connectionId, reason);
            return true;
        }

        private void ClearLease(int connectionId, string reason)
        {
            _holder = null;
            _localGrabPoint = Vector3.zero;
            _replicatedHolderConnectionId.Value = -1;
            Debug.Log($"{LogPrefix} Grab lease released: body={ObjectId} holder={connectionId} reason='{reason}'.", this);
        }
    }
}
