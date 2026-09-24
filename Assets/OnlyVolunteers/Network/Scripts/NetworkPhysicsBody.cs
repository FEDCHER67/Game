using System.Collections;
using FishNet.Object;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkObject), typeof(Rigidbody))]
    public sealed class NetworkPhysicsBody : NetworkBehaviour
    {
        private const float SpringStrength = 220f;
        private const float DampingRatio = 1f;
        private const float MaxForce = 900f;
        private const float MaxSpeed = 12f;
        private const float MaxAngularSpeed = 25f;
        private const float BreakDistance = 4.5f;

        private Rigidbody body;
        private NetworkGrabber holder;
        private Vector3 localGrabPoint;
        private Vector3 target;
        private float lastTargetTime;
        private Collider holderCollider;

        public Rigidbody Body => body;
        public bool HasHolder => holder != null;

        private void Awake() => body = GetComponent<Rigidbody>();

        public override void OnStartServer()
        {
            base.OnStartServer();
            body.isKinematic = false;
            body.useGravity = true;
            body.interpolation = RigidbodyInterpolation.Interpolate;
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            if (!IsServerStarted)
            {
                body.isKinematic = true;
                body.useGravity = false;
            }
            Debug.Log($"[OV Network] observed body={NetworkObject.ObjectId}, server={IsServerStarted}, kinematic={body.isKinematic}");
            StartCoroutine(LogSettledPosition());
        }

        private IEnumerator LogSettledPosition()
        {
            yield return new WaitForSeconds(3f);
            if (IsClientStarted)
                Debug.Log($"[OV Network] body position id={NetworkObject.ObjectId}, pos={transform.position}");
        }

        public override void OnStopServer()
        {
            Release();
            base.OnStopServer();
        }

        public bool TryAcquire(NetworkGrabber requester, Vector3 worldPoint, Vector3 initialTarget)
        {
            if (!IsServerStarted || !NetworkObject.IsSpawned || holder != null ||
                requester == null || !requester.IsValidHolder || body == null ||
                body.isKinematic || body.mass <= 0f)
                return false;

            holder = requester;
            localGrabPoint = transform.InverseTransformPoint(worldPoint);
            target = initialTarget;
            lastTargetTime = Time.time;
            holderCollider = requester.PlayerCollider;
            SetHolderCollisionIgnored(true);
            body.WakeUp();
            Debug.Log($"[OV Network] grab granted: body={name}, connection={requester.OwnerId}");
            return true;
        }

        public void SetTarget(NetworkGrabber requester, Vector3 newTarget)
        {
            if (holder != requester) return;
            target = newTarget;
            lastTargetTime = Time.time;
        }

        public void Release(NetworkGrabber requester)
        {
            if (holder == requester) Release();
        }

        public void Release()
        {
            if (holder == null) return;
            var previous = holder;
            SetHolderCollisionIgnored(false);
            holder = null;
            holderCollider = null;
            previous.ServerBodyReleased(this);
            Debug.Log($"[OV Network] grab released: body={name}");
        }

        private void SetHolderCollisionIgnored(bool ignored)
        {
            if (holderCollider == null) return;
            foreach (var collider in GetComponentsInChildren<Collider>())
                if (collider != holderCollider)
                    Physics.IgnoreCollision(collider, holderCollider, ignored);
        }

        private void FixedUpdate()
        {
            if (!IsServerStarted || holder == null) return;
            if (!holder.IsValidHolder || Time.time - lastTargetTime > 0.8f)
            {
                Release();
                return;
            }

            Vector3 worldPoint = transform.TransformPoint(localGrabPoint);
            Vector3 error = target - worldPoint;
            if (!Finite(error) || error.sqrMagnitude > BreakDistance * BreakDistance)
            {
                Release();
                return;
            }

            Vector3 velocity = body.GetPointVelocity(worldPoint);
            float damping = 2f * DampingRatio * Mathf.Sqrt(SpringStrength * Mathf.Max(0.01f, body.mass));
            Vector3 force = error * SpringStrength - velocity * damping;
            if (!Finite(force)) { Release(); return; }

            body.WakeUp();
            body.AddForceAtPosition(Vector3.ClampMagnitude(force, MaxForce), worldPoint, ForceMode.Force);
            if (body.linearVelocity.sqrMagnitude > MaxSpeed * MaxSpeed)
                body.linearVelocity = body.linearVelocity.normalized * MaxSpeed;
            if (body.angularVelocity.sqrMagnitude > MaxAngularSpeed * MaxAngularSpeed)
                body.angularVelocity = body.angularVelocity.normalized * MaxAngularSpeed;
        }

        internal static bool Finite(Vector3 v) =>
            !float.IsNaN(v.x) && !float.IsInfinity(v.x) &&
            !float.IsNaN(v.y) && !float.IsInfinity(v.y) &&
            !float.IsNaN(v.z) && !float.IsInfinity(v.z);
    }
}
