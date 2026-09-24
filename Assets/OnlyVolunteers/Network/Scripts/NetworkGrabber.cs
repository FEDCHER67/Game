using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkPlayer))]
    public sealed class NetworkGrabber : NetworkBehaviour
    {
        private const float AcquireDistance = 2.8f;
        private const float HoldDistance = 2.25f;
        private const float SendInterval = 0.05f;

        private NetworkPlayer player;
        private NetworkPhysicsBody serverHeld;
        private NetworkObject clientHeld;
        private bool pending;
        private float nextSend;

        public Collider PlayerCollider => player != null ? player.PlayerCollider : null;
        public bool IsValidHolder => IsServerStarted && Owner != null && Owner.IsActive;

        private void Awake() => player = GetComponent<NetworkPlayer>();

        public override void OnStopServer()
        {
            if (serverHeld != null) serverHeld.Release(this);
            base.OnStopServer();
        }

        public override void OnStopClient()
        {
            clientHeld = null;
            pending = false;
            base.OnStopClient();
        }

        private void Update()
        {
            if (!IsOwner || player == null || player.ViewCamera == null) return;
            if (Cursor.lockState != CursorLockMode.Locked)
            {
                if (clientHeld != null || pending) ReleaseClient();
                return;
            }

            if (Input.GetMouseButtonUp(0) || (clientHeld != null && !Input.GetMouseButton(0)))
            {
                ReleaseClient();
                return;
            }

            if (Input.GetMouseButtonDown(0) && clientHeld == null && !pending)
            {
                Ray ray = new Ray(player.ViewCamera.transform.position, player.ViewCamera.transform.forward);
                if (Physics.Raycast(ray, out RaycastHit hit, AcquireDistance, ~0, QueryTriggerInteraction.Ignore))
                {
                    var networkBody = hit.rigidbody != null
                        ? hit.rigidbody.GetComponent<NetworkPhysicsBody>() : null;
                    if (networkBody != null && networkBody.NetworkObject.IsSpawned)
                    {
                        pending = true;
                        ServerTryGrab(networkBody.NetworkObject, ray.origin, ray.direction);
                    }
                }
            }

            if (clientHeld != null && Time.unscaledTime >= nextSend)
            {
                nextSend = Time.unscaledTime + SendInterval;
                Vector3 target = player.ViewCamera.transform.position +
                    player.ViewCamera.transform.forward * HoldDistance;
                ServerHoldTarget(target, Channel.Unreliable);
            }
        }

        private void ReleaseClient()
        {
            clientHeld = null;
            pending = false;
            if (IsClientStarted) ServerRelease();
        }

        [ServerRpc]
        private void ServerTryGrab(NetworkObject candidate, Vector3 origin, Vector3 direction,
            NetworkConnection sender = null)
        {
            if (sender == null || sender != Owner || !sender.IsActive ||
                serverHeld != null || candidate == null || !candidate.IsSpawned ||
                !NetworkPhysicsBody.Finite(origin) || !NetworkPhysicsBody.Finite(direction) ||
                direction.sqrMagnitude < 0.9f || direction.sqrMagnitude > 1.1f ||
                Vector3.Distance(origin, transform.position) > 2.4f)
            {
                if (sender != null && sender.IsActive) TargetGrabResult(sender, null);
                return;
            }

            var body = candidate.GetComponent<NetworkPhysicsBody>();
            if (body == null || !body.IsServerStarted || body.Body == null ||
                NetworkSession.Active == null || !NetworkSession.Active.IsAllowedBody(body) ||
                body.transform.IsChildOf(transform) ||
                Vector3.Distance(body.transform.position, transform.position) > AcquireDistance + 2f)
            {
                TargetGrabResult(sender, null);
                return;
            }

            Ray ray = new Ray(origin, direction.normalized);
            if (!Physics.Raycast(ray, out RaycastHit hit, AcquireDistance, ~0, QueryTriggerInteraction.Ignore) ||
                hit.rigidbody != body.Body ||
                !body.TryAcquire(this, hit.point, origin + direction.normalized * HoldDistance))
            {
                TargetGrabResult(sender, null);
                return;
            }

            serverHeld = body;
            TargetGrabResult(sender, candidate);
        }

        [TargetRpc]
        private void TargetGrabResult(NetworkConnection target, NetworkObject body)
        {
            pending = false;
            if (body != null && IsOwner && Input.GetMouseButton(0) &&
                Cursor.lockState == CursorLockMode.Locked)
            {
                clientHeld = body;
                nextSend = 0f;
            }
            else if (body != null)
            {
                ServerRelease();
            }
        }

        [ServerRpc]
        private void ServerHoldTarget(Vector3 target, Channel channel = Channel.Unreliable)
        {
            if (serverHeld == null || Owner == null || !Owner.IsActive ||
                !NetworkPhysicsBody.Finite(target) ||
                Vector3.Distance(target, transform.position) > 5f)
                return;
            serverHeld.SetTarget(this, target);
        }

        [ServerRpc]
        private void ServerRelease()
        {
            if (serverHeld != null) serverHeld.Release(this);
        }

        public void ServerBodyReleased(NetworkPhysicsBody body)
        {
            if (serverHeld != body) return;
            serverHeld = null;
            if (Owner != null && Owner.IsActive)
                TargetReleased(Owner);
        }

        [TargetRpc]
        private void TargetReleased(NetworkConnection target)
        {
            clientHeld = null;
            pending = false;
        }
    }
}
