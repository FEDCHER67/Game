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

        // OV stage1: point grab. A body with IGrabPointTarget (the grey-box NPC) is held at a point the target picks (the
        // NPC: wherever the ray hit, on its axis) with the profile it hands out; pointTarget is null on the original path
        // (gurney, scalpel), which is unchanged.
        private IGrabPointTarget pointTarget;
        private int pointIndex = -1;
        private GrabPhysicsProfile pointProfile;
        private KccFirstPersonInput speedInput;

        // OV stage1 (Fedya's second playtest): the point hold starts at the distance the point was grabbed at and the mouse
        // wheel moves it nearer or farther (MinPointHold .. the point profile's HoldDistance, which is the longest hold).
        private float pointHoldDistance;
        private const float MinPointHold = 0.6f, WheelStep = 0.1f;
        // OV stage1 (review): the held point is on the body's axis, off the view ray by up to its radius. At grab the
        // hold distance is the point's depth along the view and the sideways rest is kept in view space, fading out over
        // PointOffsetFade s, so the body does not jump toward the crosshair when grabbed.
        private Vector3 pointViewOffset;
        private float pointGrabTime;
        private const float PointOffsetFade = 0.3f;
        // Held colliders whose pair with the player (PhysX ignore + the KCC's IgnoredColliders) is restored only once the
        // two no longer overlap, so a body let go of inside the player's capsule is not shot out of it.
        private readonly System.Collections.Generic.List<Collider> apartPending = new();
        private static readonly System.Predicate<Collider> DeadCollider = c => c == null;

        // OV stage1 test hook (Map/Scripts/Dev/NpcLoadingTest): a script grabs and lets go instead of the mouse; the hold is
        // the same code. Off by default: with false, Update is the original one.
        [System.NonSerialized] public bool ScriptDriven;

        public bool ScriptGrab()
        {
            if (grabbedBody == null)
            {
                TryAcquire();
                // The test re-aims its camera straight at the claimed point before the next physics step.
                pointViewOffset = Vector3.zero;
            }
            return grabbedBody != null;
        }

        /// <summary>OV stage1: where the point hold pulls the held point now (world; the view point when not holding one).</summary>
        public Vector3 PointHoldTarget
        {
            get
            {
                if (viewCamera == null)
                    return transform.position;
                Transform view = viewCamera.transform;
                Vector3 target = view.position + view.forward * pointHoldDistance;
                if (pointTarget == null)
                    return target;
                float fade = 1f - Mathf.Clamp01((Time.fixedTime - pointGrabTime) / PointOffsetFade);
                return fade > 0f ? target + view.rotation * pointViewOffset * fade : target;
            }
        }

        public void ScriptRelease() => Release();

        /// <summary>OV stage1: current point hold distance (0 when not holding a point); set clamps it like the wheel.</summary>
        public float PointHoldDistance
        {
            get => pointTarget != null ? pointHoldDistance : 0f;
            set
            {
                if (pointTarget != null)
                    pointHoldDistance = Mathf.Clamp(value, MinPointHold, Mathf.Max(MinPointHold, pointProfile.HoldDistance));
            }
        }

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
            if (ScriptDriven)
                return; // OV stage1 test hook

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
            // OV stage1: the wheel moves a held point nearer or farther (point path only).
            else if (pointTarget != null && Input.mouseScrollDelta.y != 0f)
                PointHoldDistance = pointHoldDistance + Input.mouseScrollDelta.y * WheelStep;
        }

        private void FixedUpdate()
        {
            // OV stage1: pairs left ignored after a point release come back once player and body are apart.
            if (apartPending.Count > 0)
                RestoreWhenApart();

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

            // OV stage1: layer VehicleInterior (the van's invisible step ramps, which only the grey-box player's KCC walks
            // on) never stops the ray. Layers are project-wide, so this applies in every scene; in NetworkTest nothing
            // sits on that layer, so its grabs behave as before.
            int acquisitionLayers = profile.AcquisitionLayers;
            int interiorLayer = LayerMask.NameToLayer("VehicleInterior");
            if (interiorLayer >= 0)
                acquisitionLayers &= ~(1 << interiorLayer);
            Ray ray = new Ray(viewCamera.transform.position, viewCamera.transform.forward);
            if (!UnityEngine.Physics.Raycast(ray, out RaycastHit hit,
                profile.AcquireDistance, acquisitionLayers, QueryTriggerInteraction.Ignore))
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

            // OV stage1: bodies with IGrabPointTarget are held at the point they hand out (the NPC body: where the ray hit,
            // on its axis), or not at all if the claim is refused.
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
            // OV stage1: nothing left to wait for once switched off (the driver seat switches the player off).
            FlushApartPending();
        }

        // ---------- OV stage1: point grab (IGrabPointTarget) ----------
        // Differences from the original path, on purpose:
        // - the target picks the point (the NPC body: anywhere on its axis, where the ray hit) and the profile (e.g.
        //   NpcGrabProfile: 200 N up/down, 220 N sideways per holder);
        // - the hold distance starts at the depth of the point along the view when grabbed (MinPointHold .. the profile's
        //   HoldDistance, the longest hold), the rest of the offset from the crosshair fades out over PointOffsetFade, and
        //   the mouse wheel changes it by WheelStep; the original path keeps the fixed HoldDistance;
        // - while holding, the player's KCC ignores the held colliders (ExampleCharacterController.IgnoredColliders, its
        //   existing public list), like the PhysX pair that is ignored anyway: the player can step over or into the body
        //   it holds. On release both come back only once the player and the body no longer overlap (checked every
        //   FixedUpdate), so the body is not shoved out of the capsule at the depenetration speed;
        // - the body's CCD, interpolation and maxAngularVelocity are left alone: up to three holders share one body, and
        //   saving/restoring them per holder would clobber each other;
        // - damping and the speed limit are measured against what the player stands on (the van floor while riding in
        //   the cargo bay), not the world: on the ground that is zero, i.e. the same as the original path;
        // - a far-behind point slows the player (ExternalSpeedScale), reset to 1 on release;
        // - ScriptDriven / ScriptGrab / ScriptRelease / PointHoldDistance: a test script (NpcLoadingTest) aims the camera and
        //   grabs instead of the mouse; off by default;
        // - OV stage1 fix (2026-10-05): when the profile has SoloHorizontalMaxForce (NpcGrabProfile: 220 N), the sideways
        //   part of the force is capped on its own and the vertical part by MaxForce (GrabPhysicsSolver's existing
        //   TryCalculateRelativeGrounded): lifting a body's end then tilts it about its other end instead of pulling that
        //   end along the ground. Profiles without it (0, the default) keep the plain clamp. The point is taken from the
        //   body's physics pose (Rigidbody position/rotation), not its interpolated transform.

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
            // The hand keeps the point where it was grabbed (the wheel changes it): no snap toward a fixed distance. The
            // hold distance is the point's depth along the view; what is left over (the point sits on the body's axis,
            // off the view ray) is kept in view space and fades out, so neither a lifted end nor a lying body jumps.
            Transform view = viewCamera.transform;
            Vector3 claimWorld = body.position + body.rotation * local;
            pointHoldDistance = Mathf.Clamp(Vector3.Dot(claimWorld - view.position, view.forward),
                MinPointHold, Mathf.Max(MinPointHold, held.HoldDistance));
            pointViewOffset = Quaternion.Inverse(view.rotation) *
                (claimWorld - (view.position + view.forward * pointHoldDistance));
            pointGrabTime = Time.fixedTime;
            grabbedColliders = body.GetComponentsInChildren<Collider>();
            foreach (Collider heldCollider in grabbedColliders)
            {
                apartPending.Remove(heldCollider); // still waiting from an earlier hold: held again now
                if (IsLive(heldCollider) && heldCollider != playerCollider)
                    SetKccIgnored(heldCollider, true);
            }
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

            Vector3 target = PointHoldTarget;
            Vector3 worldGrabPoint = grabbedBody.position + grabbedBody.rotation * localGrabPoint;
            Vector3 frameVelocity = FrameVelocity(worldGrabPoint);
            Vector3 error = target - worldGrabPoint;
            Vector3 pointVelocity = grabbedBody.GetPointVelocity(worldGrabPoint);
            Vector3 force;
            bool held = pointProfile.SoloHorizontalMaxForce > 0f
                ? GrabPhysicsSolver.TryCalculateRelativeGrounded(error, frameVelocity, pointVelocity,
                    grabbedBody.mass, pointProfile, out force)
                : GrabPhysicsSolver.TryCalculateRelative(error, frameVelocity, pointVelocity,
                    grabbedBody.mass, pointProfile, out force);
            if (!held)
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
            pointViewOffset = Vector3.zero;
            if (!(target is UnityEngine.Object targetObject) || targetObject != null)
                target.Release(this, point);
            ReleasePointCollisions();
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

        // On release: each held collider gets its pair with the player back at once if they do not overlap, otherwise once
        // they have come apart (RestoreWhenApart). Colliders that are gone or switched off (or a switched-off player) lost
        // the PhysX pair already; only the KCC entry is dropped.
        private void ReleasePointCollisions()
        {
            if (grabbedColliders == null)
                return;

            bool playerLive = IsLive(playerCollider);
            foreach (Collider heldCollider in grabbedColliders)
            {
                if (ReferenceEquals(heldCollider, playerCollider))
                    continue;
                if (!playerLive || !IsLive(heldCollider))
                    SetKccIgnored(heldCollider, false);
                else if (Overlapping(heldCollider))
                {
                    if (!apartPending.Contains(heldCollider))
                        apartPending.Add(heldCollider);
                }
                else
                    RestorePair(heldCollider);
            }
        }

        private void RestoreWhenApart()
        {
            if (character != null && character.IgnoredColliders != null)
                character.IgnoredColliders.RemoveAll(DeadCollider);
            bool playerLive = IsLive(playerCollider);
            for (int i = apartPending.Count - 1; i >= 0; i--)
            {
                Collider heldCollider = apartPending[i];
                if (!playerLive || !IsLive(heldCollider))
                    SetKccIgnored(heldCollider, false); // the PhysX pair went with the switched-off collider
                else if (Overlapping(heldCollider))
                    continue;
                else
                    RestorePair(heldCollider);
                apartPending.RemoveAt(i);
            }
        }

        private void FlushApartPending()
        {
            foreach (Collider heldCollider in apartPending)
                RestorePair(heldCollider);
            apartPending.Clear();
        }

        private void RestorePair(Collider heldCollider)
        {
            if (IsLive(heldCollider) && IsLive(playerCollider))
                UnityEngine.Physics.IgnoreCollision(heldCollider, playerCollider, false);
            SetKccIgnored(heldCollider, false);
        }

        // Physics poses, not the drawn ones: this runs in the physics tick and the body is interpolated.
        private bool Overlapping(Collider heldCollider)
        {
            Vector3 playerPosition;
            Quaternion playerRotation;
            if (character != null && character.Motor != null && playerCollider.transform == character.Motor.transform)
            {
                playerPosition = character.Motor.TransientPosition;
                playerRotation = character.Motor.TransientRotation;
            }
            else
                PhysicsPose(playerCollider, out playerPosition, out playerRotation);
            PhysicsPose(heldCollider, out Vector3 heldPosition, out Quaternion heldRotation);
            return UnityEngine.Physics.ComputePenetration(playerCollider, playerPosition, playerRotation,
                heldCollider, heldPosition, heldRotation, out _, out _);
        }

        // A collider's pose from its rigidbody's simulated pose (its transform when it has no rigidbody).
        private static void PhysicsPose(Collider c, out Vector3 position, out Quaternion rotation)
        {
            Transform t = c.transform;
            Rigidbody rb = c.attachedRigidbody;
            if (rb == null)
            {
                position = t.position;
                rotation = t.rotation;
                return;
            }
            Transform rt = rb.transform;
            if (t == rt)
            {
                position = rb.position;
                rotation = rb.rotation;
                return;
            }
            Quaternion toBody = Quaternion.Inverse(rt.rotation);
            position = rb.position + rb.rotation * (toBody * (t.position - rt.position));
            rotation = rb.rotation * (toBody * t.rotation);
        }

        private void SetKccIgnored(Collider heldCollider, bool ignored)
        {
            if (character == null || character.IgnoredColliders == null)
                return;
            System.Collections.Generic.List<Collider> list = character.IgnoredColliders;
            if (!ignored)
                list.Remove(heldCollider);
            else if (heldCollider != null && !list.Contains(heldCollider))
                list.Add(heldCollider);
        }

        private static bool IsLive(Collider c) => c != null && c.enabled && c.gameObject.activeInHierarchy;
    }
}
