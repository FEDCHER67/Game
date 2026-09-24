using System;
using System.Collections;
using FishNet.Object;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkObject), typeof(Rigidbody))]
    public sealed class NetworkPhysicsBody : NetworkBehaviour
    {
        [SerializeField] private GrabPhysicsProfile profile;
        private Rigidbody body;
        private NetworkGrabber holder;
        private Vector3 localGrabPoint;
        private Vector3 target;
        private float lastTargetTime;
        private Collider holderCollider;

        public Rigidbody Body => body;
        public bool HasHolder => holder != null;

        private void Awake()
        {
            body = GetComponent<Rigidbody>();
            if (profile == null)
                Debug.LogError("NetworkPhysicsBody requires a GrabPhysicsProfile", this);
        }

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
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (NetworkObject.ObjectId == 0 &&
                Array.Exists(Environment.GetCommandLineArgs(), x => x == "-ov-smoke-grab"))
                StartCoroutine(GrabPositionProbe());
#endif
        }

        private IEnumerator LogSettledPosition()
        {
            yield return new WaitForSeconds(3f);
            if (IsClientStarted)
                Debug.Log($"[OV Network] body position id={NetworkObject.ObjectId}, pos={transform.position}");
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator GrabPositionProbe()
        {
            float[] times = { 4f, 8f, 12f, 16f, 20f };
            float previous = 0f;
            foreach (float time in times)
            {
                yield return new WaitForSeconds(time - previous);
                previous = time;
                if (!IsClientStarted) yield break;
                Debug.Log($"[OV Smoke] body id={NetworkObject.ObjectId}, time={time:F0}, " +
                    $"server={IsServerStarted}, kinematic={body.isKinematic}, held={HasHolder}, position={transform.position}");
            }
        }
#endif

        public override void OnStopServer()
        {
            Release();
            base.OnStopServer();
        }

        public bool TryAcquire(NetworkGrabber requester, Vector3 worldPoint, Vector3 initialTarget)
        {
            if (!IsServerStarted || !NetworkObject.IsSpawned || holder != null || profile == null ||
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

            if (!GrabPhysicsSolver.TryCalculate(body, localGrabPoint, target, profile,
                out Vector3 worldPoint, out Vector3 force))
            {
                Release();
                return;
            }

            GrabPhysicsSolver.ApplyForce(body, worldPoint, force);
            GrabPhysicsSolver.LimitVelocities(body, profile);
        }
    }
}
