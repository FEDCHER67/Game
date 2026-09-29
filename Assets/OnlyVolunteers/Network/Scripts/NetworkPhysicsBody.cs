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
        private const int MaxHolders = 4;
        private const float TargetTimeout = 0.8f;
        private const float TargetVelocityFilter = 0.05f;
        private const float MaxTargetVelocity = 6f;
        private readonly Hold[] holds = new Hold[MaxHolders];
        private readonly Vector3[] forcePoints = new Vector3[MaxHolders];
        private readonly Vector3[] forces = new Vector3[MaxHolders];
        private readonly Vector3[] errors = new Vector3[MaxHolders];
        private readonly Vector3[] pointVelocities = new Vector3[MaxHolders];
        private readonly Vector3[] targetVelocities = new Vector3[MaxHolders];
        private readonly Hold[] validHolds = new Hold[MaxHolders];
        private Collider[] bodyColliders;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private bool measureFeel;
        private bool measureSprint;
        private float nextSprintLog;
        private int sprintContacts;
        private float feelWindowStart;
        private float feelErrorSum;
        private float feelSpeedSum;
        private int feelSamples;
#endif

        private sealed class Hold
        {
            public NetworkGrabber Grabber;
            public uint Id;
            public Vector3 LocalPoint;
            public Vector3 Target;
            public Vector3 TargetVelocity;
            public float LastTargetTime;
            public uint LastSequence;
            public Collider PlayerCollider;
            public bool[] IgnoredBeforeGrab;
        }

        public Rigidbody Body => body;
        public bool GroundPlaneFollow => profile != null && profile.GroundPlaneFollow;
        public int ActiveHolderCount
        {
            get
            {
                int count = 0;
                for (int i = 0; i < holds.Length; i++)
                    if (holds[i] != null) count++;
                return count;
            }
        }
        public bool HasHolder => ActiveHolderCount > 0;

        private void Awake()
        {
            body = GetComponent<Rigidbody>();
            bodyColliders = GetComponentsInChildren<Collider>();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            measureFeel = Array.Exists(Environment.GetCommandLineArgs(), x =>
                x == "-ov-smoke-feel" || x == "-ov-smoke-feel-opposed");
            measureSprint = Array.Exists(Environment.GetCommandLineArgs(), x =>
                x == "-ov-smoke-gurney-sprint" || x == "-ov-smoke-gurney-sprint-z");
#endif
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
            for (int i = 0; i < holds.Length; i++)
                ReleaseAt(i);
            base.OnStopServer();
        }

        public bool TryAcquire(NetworkGrabber requester, uint holdId, Vector3 worldPoint, Vector3 initialTarget)
        {
            if (!IsServerStarted || !NetworkObject.IsSpawned || holdId == 0 || profile == null ||
                requester == null || !requester.IsValidHolder || body == null ||
                body.isKinematic || float.IsNaN(body.mass) || float.IsInfinity(body.mass) || body.mass <= 0f ||
                !GrabPhysicsSolver.IsFinite(worldPoint) || !GrabPhysicsSolver.IsFinite(initialTarget))
                return false;

            int free = -1;
            for (int i = 0; i < holds.Length; i++)
            {
                if (holds[i] != null && holds[i].Grabber == requester) return false;
                if (holds[i] == null && free < 0) free = i;
            }
            if (free < 0) return false;

            Vector3 localPoint = transform.InverseTransformPoint(worldPoint);
            if (!GrabPhysicsSolver.IsFinite(localPoint)) return false;
            var hold = new Hold
            {
                Grabber = requester,
                Id = holdId,
                LocalPoint = localPoint,
                Target = initialTarget,
                LastTargetTime = Time.time,
                PlayerCollider = requester.PlayerCollider,
                IgnoredBeforeGrab = new bool[bodyColliders.Length]
            };
            holds[free] = hold;
            IgnoreHolderCollisions(hold);
            body.WakeUp();
            Debug.Log($"[OV Network] grab granted: body={name}, connection={requester.OwnerId}, " +
                $"activeHolders={ActiveHolderCount}, initialGap={Vector3.Distance(worldPoint, initialTarget):F3}");
            return true;
        }

        public void SetTarget(NetworkGrabber requester, uint holdId, uint sequence, Vector3 newTarget)
        {
            if (sequence == 0 || !GrabPhysicsSolver.IsFinite(newTarget)) return;
            for (int i = 0; i < holds.Length; i++)
            {
                Hold hold = holds[i];
                if (hold == null || hold.Grabber != requester || hold.Id != holdId) continue;
                if (sequence <= hold.LastSequence)
                {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if (measureFeel)
                        Debug.Log($"[OV Feel] stale target rejected body={name}, connection={requester.OwnerId}, " +
                            $"sequence={sequence}, newest={hold.LastSequence}");
#endif
                    return;
                }
                float dt = Mathf.Max(0.02f, Time.time - hold.LastTargetTime);
                Vector3 velocity = (newTarget - hold.Target) / dt;
                if (!GrabPhysicsSolver.IsFinite(velocity)) return;
                float maxTargetSpeed = profile.GroundPlaneFollow ? profile.SoloMaxLinearSpeed :
                    Mathf.Min(MaxTargetVelocity, profile.MaxLinearSpeed);
                velocity = Vector3.ClampMagnitude(velocity, maxTargetSpeed);
                float alpha = dt / (TargetVelocityFilter + dt);
                hold.TargetVelocity = Vector3.Lerp(hold.TargetVelocity, velocity, alpha);
                hold.Target = newTarget;
                hold.LastTargetTime = Time.time;
                hold.LastSequence = sequence;
                return;
            }
        }

        public void Release(NetworkGrabber requester, uint holdId)
        {
            for (int i = 0; i < holds.Length; i++)
                if (holds[i] != null && holds[i].Grabber == requester && holds[i].Id == holdId)
                {
                    ReleaseAt(i);
                    return;
                }
        }

        private void ReleaseAt(int index)
        {
            Hold hold = holds[index];
            if (hold == null) return;
            holds[index] = null;
            RestoreHolderCollisions(hold);
            hold.Grabber.ServerBodyReleased(this, hold.Id);
            Debug.Log($"[OV Network] grab released: body={name}, connection={hold.Grabber.OwnerId}, activeHolders={ActiveHolderCount}");
        }

        private void IgnoreHolderCollisions(Hold hold)
        {
            if (hold.PlayerCollider == null) return;
            for (int i = 0; i < bodyColliders.Length; i++)
            {
                Collider collider = bodyColliders[i];
                if (collider != null && collider != hold.PlayerCollider)
                {
                    hold.IgnoredBeforeGrab[i] = Physics.GetIgnoreCollision(collider, hold.PlayerCollider);
                    Physics.IgnoreCollision(collider, hold.PlayerCollider, true);
                }
            }
        }

        private void RestoreHolderCollisions(Hold hold)
        {
            if (hold.PlayerCollider == null) return;
            for (int i = 0; i < bodyColliders.Length; i++)
            {
                Collider collider = bodyColliders[i];
                if (collider != null && collider != hold.PlayerCollider)
                    Physics.IgnoreCollision(collider, hold.PlayerCollider, hold.IgnoredBeforeGrab[i]);
            }
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private void OnCollisionStay(Collision collision)
        {
            if (measureSprint && name.StartsWith("NetworkTableAstra"))
                sprintContacts += collision.contactCount;
        }
#endif

        private void FixedUpdate()
        {
            if (!IsServerStarted || !HasHolder) return;
            int count = 0;
            float errorSum = 0f;
            for (int i = 0; i < holds.Length; i++)
            {
                Hold hold = holds[i];
                if (hold == null) continue;
                Vector3 motor = hold.Grabber.MotorPosition;
                if (!hold.Grabber.IsValidHolder || Time.time - hold.LastTargetTime > TargetTimeout ||
                    !GrabPhysicsSolver.IsFinite(motor) ||
                    !GrabPhysicsSolver.IsFinite(hold.Target) ||
                    Vector3.Distance(hold.Target, motor) > 5f)
                {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if (measureSprint && name.StartsWith("NetworkTableAstra"))
                        Debug.Log($"[OV Gurney Sprint] server release preflight valid={hold.Grabber.IsValidHolder}, " +
                            $"targetAge={Time.time - hold.LastTargetTime:F3}, target={hold.Target}, motor={motor}, " +
                            $"targetMotorDistance={Vector3.Distance(hold.Target, motor):F3}");
#endif
                    ReleaseAt(i);
                    continue;
                }
                Vector3 worldPoint = transform.TransformPoint(hold.LocalPoint);
                if (!GrabPhysicsSolver.IsFinite(worldPoint))
                {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if (measureSprint && name.StartsWith("NetworkTableAstra"))
                        Debug.Log($"[OV Gurney Sprint] server release nonfinite point={worldPoint}");
#endif
                    ReleaseAt(i);
                    continue;
                }
                Vector3 error = hold.Target - worldPoint;
                Vector3 pointVelocity = body.GetPointVelocity(worldPoint);
                if (!GrabPhysicsSolver.IsFinite(error) ||
                    !GrabPhysicsSolver.IsFinite(pointVelocity) ||
                    error.sqrMagnitude > profile.BreakDistance * profile.BreakDistance ||
                    Vector3.Distance(worldPoint, motor) > profile.AcquireDistance + 2.4f)
                {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if (measureSprint && name.StartsWith("NetworkTableAstra"))
                        Debug.Log($"[OV Gurney Sprint] server release physics target={hold.Target}, " +
                            $"point={worldPoint}, error={error.magnitude:F3}, motor={motor}, " +
                            $"pointMotorDistance={Vector3.Distance(worldPoint, motor):F3}, " +
                            $"velocity={body.linearVelocity}, contacts={sprintContacts}");
#endif
                    ReleaseAt(i);
                    continue;
                }
                forcePoints[count] = worldPoint;
                errors[count] = error;
                pointVelocities[count] = pointVelocity;
                float targetAge = Time.time - hold.LastTargetTime;
                targetVelocities[count] = hold.TargetVelocity *
                    Mathf.Clamp01((0.25f - targetAge) / 0.1f);
                validHolds[count] = hold;
                errorSum += error.magnitude;
                count++;
            }
            if (count == 0) return;
            if (count > 1 && profile.GroundPlaneFollow)
                for (int i = 0; i < count; i++)
                    targetVelocities[i] = Vector3.ClampMagnitude(targetVelocities[i],
                        profile.MaxLinearSpeed);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (measureFeel && name.StartsWith("NetworkTableAstra"))
                RecordFeelSample(count, errorSum / count);
#endif
            // The gurney follows a moving holder even with only one hand on it.
            for (int i = 0; i < count; i++)
            {
                bool calculated;
                if (count == 1 && profile.GroundPlaneFollow)
                    calculated = GrabPhysicsSolver.TryCalculateRelativeGrounded(errors[i],
                        targetVelocities[i], pointVelocities[i], body.mass, profile, out forces[i]);
                else if (count == 1)
                    calculated = GrabPhysicsSolver.TryCalculate(errors[i], pointVelocities[i],
                        body.mass, profile, out forces[i]);
                else
                    calculated = GrabPhysicsSolver.TryCalculateRelative(errors[i], targetVelocities[i],
                        pointVelocities[i], body.mass / count, profile, out forces[i]);
                if (!calculated)
                {
                    Release(validHolds[i].Grabber, validHolds[i].Id);
                    continue;
                }
                GrabPhysicsSolver.ApplyForce(body, forcePoints[i], forces[i]);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if (measureSprint && name.StartsWith("NetworkTableAstra") && Time.time >= nextSprintLog)
                {
                    nextSprintLog = Time.time + 0.1f;
                    Debug.Log($"[OV Gurney Sprint] server force target={validHolds[i].Target}, " +
                        $"point={forcePoints[i]}, error={errors[i].magnitude:F3}, " +
                        $"targetVelocity={targetVelocities[i]}, bodyVelocity={body.linearVelocity}, " +
                        $"force={forces[i]}, contacts={sprintContacts}");
                    sprintContacts = 0;
                }
#endif
            }
            GrabPhysicsSolver.LimitVelocities(body, profile,
                count == 1 && profile.GroundPlaneFollow
                    ? profile.SoloMaxLinearSpeed : profile.MaxLinearSpeed);
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private void RecordFeelSample(int count, float meanError)
        {
            if (count != 2)
            {
                feelSamples = 0;
                feelErrorSum = 0f;
                feelSpeedSum = 0f;
                feelWindowStart = Time.time;
                return;
            }
            if (feelSamples == 0) feelWindowStart = Time.time;
            feelErrorSum += meanError;
            feelSpeedSum += body.linearVelocity.magnitude;
            feelSamples++;
            if (Time.time - feelWindowStart < 1f) return;
            Debug.Log($"[OV Feel] server body={name}, holders=2, meanError={feelErrorSum / feelSamples:F3}, " +
                $"meanSpeed={feelSpeedSum / feelSamples:F3}, samples={feelSamples}, t={Time.time:F1}");
            feelSamples = 0;
            feelErrorSum = 0f;
            feelSpeedSum = 0f;
        }
#endif
    }
}
