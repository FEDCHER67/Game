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

        // OV stage1: point grab. A body with IGrabPointTarget (the grey-box NPC) is held by a claimed point with the
        // profile it hands out; pointTarget is null on the original path (gurney, scalpel), which is unchanged.
        private IGrabPointTarget pointTarget;
        private int pointIndex = -1;
        private GrabPhysicsProfile pointProfile;
        private KccFirstPersonInput speedInput;

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

            // OV stage1: a heavy held point slows the player down (KccFirstPersonInput.ExternalSpeedScale).
            speedInput = GetComponent<KccFirstPersonInput>();

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
            // OV stage1: point grab has its own tick; the original one below is untouched.
            if (pointTarget != null)
            {
                HoldPoint();
                return;
            }

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

            // OV stage1: a point hold whose body was destroyed under it (grabbedBody reads null) is let go first.
            if (pointTarget != null)
                Release();

            Ray ray = new Ray(viewCamera.transform.position, viewCamera.transform.forward);
            if (!UnityEngine.Physics.Raycast(ray, out RaycastHit hit,
                profile.AcquireDistance, profile.AcquisitionLayers, QueryTriggerInteraction.Ignore))
                return;

            // OV stage1: a vehicle (the 1800 kg van, its doors) stops the ray but is never grabbed: the original path would
            // pull the van and clamp its speed to MaxLinearSpeed. It stays in AcquisitionLayers on purpose, so its walls
            // still block grabs of bodies inside a closed cargo bay. Scenes without a "Vehicle" layer are unaffected.
            int vehicleLayer = LayerMask.NameToLayer("Vehicle");
            if (vehicleLayer >= 0 && hit.collider.gameObject.layer == vehicleLayer)
                return;

            Rigidbody body = hit.rigidbody;
            if (!IsValidTarget(body))
                return;

            // OV stage1: bodies with grab points are held by a claimed point, or not at all if the claim is refused.
            if (body.TryGetComponent(out IGrabPointTarget pointBody))
            {
                TryAcquirePoint(body, pointBody, hit);
                return;
            }

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
            // OV stage1: point grab
            if (pointTarget != null)
            {
                ReleasePoint();
                return;
            }

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

        // ---------- OV stage1: point grab (IGrabPointTarget) ----------
        // Differences from the original path, on purpose:
        // - the target picks the point (nearest free one) and the profile (e.g. NpcGrabProfile: 350 N per holder);
        // - the body's CCD, interpolation and maxAngularVelocity are left alone: up to three holders share one body, and
        //   saving/restoring them per holder would clobber each other;
        // - damping and the speed limit are measured against what the player stands on (the van floor while riding in
        //   the cargo bay), not the world: on the ground that is zero, i.e. the same as the original path;
        // - a far-behind point slows the player (ExternalSpeedScale), reset to 1 on release.

        private void TryAcquirePoint(Rigidbody body, IGrabPointTarget target, RaycastHit hit)
        {
            if (!target.TryClaim(this, hit.point, out int point, out Vector3 local, out GrabPhysicsProfile claimed))
                return;
            GrabPhysicsProfile held = claimed != null ? claimed : profile;
            // The default profile found the body; the point's own profile decides whether it is in reach.
            if (hit.distance > held.AcquireDistance ||
                (held.AcquisitionLayers.value & (1 << hit.collider.gameObject.layer)) == 0)
            {
                target.Release(this, point);
                return;
            }

            grabbedBody = body;
            localGrabPoint = local;
            pointTarget = target;
            pointIndex = point;
            pointProfile = held;
            grabbedColliders = body.GetComponentsInChildren<Collider>();
            SetPointCollisionIgnored(true);
            body.WakeUp();
        }

        private void HoldPoint()
        {
            // Gone (destroyed body or target), turned kinematic, or the target took the point back (kicked free, woke up).
            bool targetDestroyed = pointTarget is UnityEngine.Object targetObject && targetObject == null;
            if (grabbedBody == null || viewCamera == null || grabbedBody.isKinematic || targetDestroyed ||
                !pointTarget.IsClaimValid(this, pointIndex))
            {
                Release();
                return;
            }

            Transform view = viewCamera.transform;
            Vector3 target = view.position + view.forward * pointProfile.HoldDistance;
            Vector3 worldGrabPoint = grabbedBody.transform.TransformPoint(localGrabPoint);
            Vector3 frameVelocity = FrameVelocity(worldGrabPoint);
            Vector3 error = target - worldGrabPoint;
            if (!GrabPhysicsSolver.TryCalculateRelative(error, frameVelocity,
                grabbedBody.GetPointVelocity(worldGrabPoint), grabbedBody.mass, pointProfile, out Vector3 force))
            {
                Release(); // beyond the break distance
                return;
            }

            GrabPhysicsSolver.ApplyForce(grabbedBody, worldGrabPoint, force);
            LimitVelocitiesRelative(grabbedBody, frameVelocity, pointProfile);
            if (speedInput != null)
                speedInput.ExternalSpeedScale = Mathf.Clamp(1f - (error.magnitude - 0.6f) / 1.0f, 0.35f, 1f);
        }

        // Velocity of whatever the player stands on (or rides in) at that point; zero on plain ground.
        private Vector3 FrameVelocity(Vector3 worldPoint)
        {
            Rigidbody frame = character != null && character.Motor != null ? character.Motor.AttachedRigidbody : null;
            return frame != null && frame != grabbedBody ? frame.GetPointVelocity(worldPoint) : Vector3.zero;
        }

        private static void LimitVelocitiesRelative(Rigidbody body, Vector3 frameVelocity, GrabPhysicsProfile limits)
        {
            Vector3 relative = body.linearVelocity - frameVelocity;
            if (relative.sqrMagnitude > limits.MaxLinearSpeed * limits.MaxLinearSpeed)
                body.linearVelocity = frameVelocity + relative.normalized * limits.MaxLinearSpeed;
            if (body.angularVelocity.sqrMagnitude > limits.MaxAngularSpeed * limits.MaxAngularSpeed)
                body.angularVelocity = body.angularVelocity.normalized * limits.MaxAngularSpeed;
        }

        private void ReleasePoint()
        {
            IGrabPointTarget target = pointTarget;
            int point = pointIndex;
            pointTarget = null;
            pointIndex = -1;
            pointProfile = null;
            if (!(target is UnityEngine.Object targetObject) || targetObject != null)
                target.Release(this, point);
            SetPointCollisionIgnored(false);
            if (grabbedBody != null)
                grabbedBody.WakeUp();
            if (speedInput != null)
                speedInput.ExternalSpeedScale = 1f;

            grabbedBody = null;
            grabbedColliders = null;
            localGrabPoint = Vector3.zero;
        }

        // Like SetPlayerCollisionIgnored, but skips colliders that are switched off or already gone: the NPC body removes
        // its collider when it wakes up, and the player is switched off in the van's driver seat. Unity refuses
        // IgnoreCollision on inactive colliders (and deactivation drops the pair anyway).
        private void SetPointCollisionIgnored(bool ignored)
        {
            if (!IsLive(playerCollider) || grabbedColliders == null)
                return;

            foreach (Collider heldCollider in grabbedColliders)
            {
                if (IsLive(heldCollider) && heldCollider != playerCollider)
                    UnityEngine.Physics.IgnoreCollision(heldCollider, playerCollider, ignored);
            }
        }

        private static bool IsLive(Collider c) => c != null && c.enabled && c.gameObject.activeInHierarchy;
    }
}
