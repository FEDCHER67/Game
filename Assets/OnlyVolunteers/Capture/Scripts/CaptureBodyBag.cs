using FishNet.Object;
using FishNet.Object.Synchronizing;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>One persistent physical inventory cargo item. Packing never resolves its patient identity.</summary>
    [RequireComponent(typeof(WorldItem), typeof(NetworkPhysicsBody))]
    public sealed class CaptureBodyBag : NetworkBehaviour, IPhysicalInventoryItem
    {
        private readonly SyncVar<string> identity = new();
        private readonly SyncVar<NetworkObject> holder = new();
        private Rigidbody body;
        private Collider[] colliders;
        private NetworkInventory inventory;
        public string PatientId => identity.Value;
        public NetworkObject Holder => holder.Value;
        public WorldItem World => GetComponent<WorldItem>();
        private void Awake() { body = GetComponent<Rigidbody>(); colliders = GetComponentsInChildren<Collider>(true); }
        public void Initialize(string id) => identity.Value = id;
        public bool ServerTryHold(NetworkInventory owner)
        {
            if (!IsServerInitialized || owner == null || Holder != null || GetComponent<NetworkPhysicsBody>().HasHolder) return false;
            inventory = owner; holder.Value = owner.NetworkObject;
            body.isKinematic = true; body.useGravity = false;
            foreach (var collider in colliders) if (collider != null) collider.enabled = false;
            return true;
        }
        public void ServerRelease(Vector3 position, Vector3 velocity)
        {
            if (!IsServerInitialized) return;
            inventory = null; holder.Value = null;
            body.position = position; transform.position = position;
            body.isKinematic = false; body.useGravity = true;
            foreach (var collider in colliders) if (collider != null) collider.enabled = true;
            body.linearVelocity = Vector3.ClampMagnitude(velocity, 6f); body.angularVelocity = Vector3.zero;
        }
        private void FixedUpdate()
        {
            if (!IsServerInitialized || inventory == null) return;
            var player = inventory.GetComponent<NetworkPlayer>();
            if (player == null || player.Owner == null || !player.Owner.IsActive) { inventory.ServerReleasePhysical(transform.position, Vector3.zero); return; }
            Vector3 at = player.MotorPosition + Vector3.up * 1.15f + player.MotorForward * 0.75f;
            body.MovePosition(at); body.MoveRotation(Quaternion.LookRotation(player.MotorForward, Vector3.up));
        }
        private void LateUpdate()
        {
            var corpse = GetComponent<CaptureCorpse>();
            bool free = Holder == null && (corpse == null || !corpse.Sinking);
            foreach (var collider in colliders) if (collider != null) collider.enabled = free;
        }
    }
}
