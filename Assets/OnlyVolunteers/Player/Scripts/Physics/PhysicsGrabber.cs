using KinematicCharacterController;
using KinematicCharacterController.Examples;
using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    public sealed class PhysicsGrabber : MonoBehaviour
    {
        [SerializeField] private ExampleCharacterController character;
        [SerializeField] private Camera viewCamera;
        [SerializeField] private GrabPhysicsProfile profile;

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

            if (profile == null)
            {
                Debug.LogError("PhysicsGrabber requires a GrabPhysicsProfile", this);
                enabled = false;
            }
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

            Vector3 target = viewCamera.transform.position +
                viewCamera.transform.forward * profile.HoldDistance;
            if (!GrabPhysicsSolver.TryCalculate(grabbedBody, localGrabPoint, target, profile,
                out Vector3 worldGrabPoint, out Vector3 force))
            {
                Release();
                return;
            }

            GrabPhysicsSolver.ApplyForce(grabbedBody, worldGrabPoint, force);
            GrabPhysicsSolver.LimitVelocities(grabbedBody, profile);
        }

        private void TryAcquire()
        {
            if (viewCamera == null || profile == null)
                return;

            Ray ray = new Ray(viewCamera.transform.position, viewCamera.transform.forward);
            if (!UnityEngine.Physics.Raycast(ray, out RaycastHit hit,
                profile.AcquireDistance, profile.AcquisitionLayers, QueryTriggerInteraction.Ignore))
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
                originalMaxAngularVelocity, profile.MaxAngularSpeed);
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

        private void OnDisable()
        {
            Release();
        }
    }
}
