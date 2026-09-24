using KinematicCharacterController;
using KinematicCharacterController.Examples;
using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    public sealed class PhysicsGrabber : MonoBehaviour
    {
        [SerializeField] private ExampleCharacterController character;
        [SerializeField] private Camera viewCamera;
        [SerializeField, Min(0.1f)] private float maxAcquireDistance = 2.8f;
        [SerializeField, Min(0.1f)] private float holdDistance = 2.25f;
        [SerializeField, Min(1f)] private float springStrength = 220f;
        [SerializeField, Range(0.1f, 2f)] private float dampingRatio = 1f;
        [SerializeField, Min(1f)] private float maxHoldingForce = 900f;
        [SerializeField, Min(1f)] private float maxHeldSpeed = 12f;
        [SerializeField, Min(1f)] private float maxHeldAngularSpeed = 25f;
        [SerializeField, Min(0.5f)] private float breakDistance = 4.5f;
        [SerializeField] private LayerMask acquisitionLayers = ~0;

        private Rigidbody grabbedBody;
        private Vector3 localGrabPoint;
        private CollisionDetectionMode originalCollisionDetection;
        private RigidbodyInterpolation originalInterpolation;
        private float originalMaxAngularVelocity;
        private Collider[] grabbedColliders;
        private Collider playerCollider;

        public Rigidbody GrabbedBody => grabbedBody;
        public bool IsHolding => grabbedBody != null;

        private void Reset()
        {
            var input = GetComponent<KccFirstPersonInput>();
            if (input == null)
                return;

            character = input.Character;
            viewCamera = input.ViewCamera;
        }

        private void Awake()
        {
            if (character == null || viewCamera == null)
            {
                var input = GetComponent<KccFirstPersonInput>();
                if (input != null)
                {
                    character ??= input.Character;
                    viewCamera ??= input.ViewCamera;
                }
            }

            if (character != null && character.Motor != null)
                playerCollider = character.Motor.Capsule;
        }

        private void Update()
        {
            if (Cursor.lockState != CursorLockMode.Locked)
            {
                if (grabbedBody != null)
                    Release();
                return;
            }

            if (grabbedBody == null)
            {
                if (Input.GetMouseButtonDown(0))
                    TryAcquire();
                return;
            }

            if (Input.GetMouseButtonUp(0) || !Input.GetMouseButton(0))
                Release();
        }

        private void FixedUpdate()
        {
            if (grabbedBody == null || viewCamera == null)
                return;

            if (grabbedBody.isKinematic)
            {
                Release();
                return;
            }

            Vector3 worldGrabPoint = grabbedBody.transform.TransformPoint(localGrabPoint);
            Vector3 target = viewCamera.transform.position +
                viewCamera.transform.forward * holdDistance;
            Vector3 error = target - worldGrabPoint;
            if (!IsFinite(error) || error.sqrMagnitude > breakDistance * breakDistance)
            {
                Release();
                return;
            }

            Vector3 pointVelocity = grabbedBody.GetPointVelocity(worldGrabPoint);
            float damping = 2f * dampingRatio *
                Mathf.Sqrt(springStrength * Mathf.Max(0.01f, grabbedBody.mass));
            Vector3 force = error * springStrength - pointVelocity * damping;
            if (!IsFinite(force))
            {
                Release();
                return;
            }

            grabbedBody.WakeUp();
            grabbedBody.AddForceAtPosition(
                Vector3.ClampMagnitude(force, maxHoldingForce),
                worldGrabPoint,
                ForceMode.Force);

            if (grabbedBody.linearVelocity.sqrMagnitude > maxHeldSpeed * maxHeldSpeed)
                grabbedBody.linearVelocity =
                    grabbedBody.linearVelocity.normalized * maxHeldSpeed;
            if (grabbedBody.angularVelocity.sqrMagnitude >
                maxHeldAngularSpeed * maxHeldAngularSpeed)
                grabbedBody.angularVelocity =
                    grabbedBody.angularVelocity.normalized * maxHeldAngularSpeed;
        }

        private void TryAcquire()
        {
            if (viewCamera == null)
                return;

            Ray ray = new Ray(viewCamera.transform.position, viewCamera.transform.forward);
            if (!UnityEngine.Physics.Raycast(ray, out RaycastHit hit,
                maxAcquireDistance, acquisitionLayers, QueryTriggerInteraction.Ignore))
                return;

            Rigidbody body = hit.rigidbody;
            if (!IsValidTarget(body))
                return;

            grabbedBody = body;
            localGrabPoint = body.transform.InverseTransformPoint(hit.point);
            originalCollisionDetection = body.collisionDetectionMode;
            originalInterpolation = body.interpolation;
            originalMaxAngularVelocity = body.maxAngularVelocity;
            grabbedColliders = body.GetComponentsInChildren<Collider>();

            body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            body.interpolation = RigidbodyInterpolation.Interpolate;
            body.maxAngularVelocity = Mathf.Min(
                originalMaxAngularVelocity, maxHeldAngularSpeed);
            SetPlayerCollisionIgnored(true);
            body.WakeUp();
        }

        private bool IsValidTarget(Rigidbody body)
        {
            if (body == null || body.isKinematic || body.mass <= 0f)
                return false;
            if (body.transform.IsChildOf(transform))
                return false;
            if (body.GetComponent<KinematicCharacterMotor>() != null)
                return false;
            if (character != null && character.Motor.AttachedRigidbody == body)
                return false;
            return true;
        }

        private void Release()
        {
            if (grabbedBody != null)
            {
                SetPlayerCollisionIgnored(false);
                grabbedBody.collisionDetectionMode = originalCollisionDetection;
                grabbedBody.interpolation = originalInterpolation;
                grabbedBody.maxAngularVelocity = originalMaxAngularVelocity;
                grabbedBody.WakeUp();
            }

            grabbedBody = null;
            grabbedColliders = null;
            localGrabPoint = Vector3.zero;
        }

        private void SetPlayerCollisionIgnored(bool ignored)
        {
            if (playerCollider == null || grabbedColliders == null)
                return;

            foreach (Collider heldCollider in grabbedColliders)
            {
                if (heldCollider != null && heldCollider != playerCollider)
                    UnityEngine.Physics.IgnoreCollision(
                        heldCollider, playerCollider, ignored);
            }
        }

        private static bool IsFinite(Vector3 value)
        {
            return !float.IsNaN(value.x) && !float.IsInfinity(value.x) &&
                !float.IsNaN(value.y) && !float.IsInfinity(value.y) &&
                !float.IsNaN(value.z) && !float.IsInfinity(value.z);
        }

        private void OnDisable()
        {
            Release();
        }
    }
}
