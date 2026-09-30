using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Props.TableAstra
{
    /// <summary>Planar trailing caster contact kinematics. Does not move or apply forces to the cart.</summary>
    [DisallowMultipleComponent]
    public sealed class TableAstraCasterMotion : MonoBehaviour
    {
        [Serializable]
        private sealed class Caster
        {
            public string suffix;
            [NonSerialized] public Transform steer, roll;
            [NonSerialized] public Quaternion restSteer, restRoll;
            [NonSerialized] public Vector3 steerAxis, rollAxis, restForward, previousPosition, previousForward;
            [NonSerialized] public double heading, spin, axleSign;
            [NonSerialized] public bool reversing;
        }

        [SerializeField] private Transform rigRoot;
        [SerializeField] private Rigidbody movingBody;
        [SerializeField, Min(0f)] private float teleportDistance = 1.5f;
        [SerializeField, Range(1f, 180f)] private float teleportYawDegrees = 120f;
        [SerializeField] private Caster[] casters =
        {
            new Caster { suffix = "Foot_Left" }, new Caster { suffix = "Foot_Right" },
            new Caster { suffix = "Head_Left" }, new Caster { suffix = "Head_Right" }
        };

        private const float ModelRadius = 0.105f;
        private const float ModelTrail = 0.035f;
        private Vector3 groundUp, rootUp, previousRootPosition;
        private float worldScale;
        private bool ready;

        private void Awake()
        {
            if (rigRoot == null) rigRoot = FindUnique(transform, "RIG_Table_Root");
            // Unity may collapse/rename the FBX's single top node to the asset filename.
            if (rigRoot == null)
            {
                Transform marker = FindUnique(transform, "RIG_GroundUp");
                if (marker != null) rigRoot = marker.parent;
            }
            if (rigRoot == null || !UniformScale(rigRoot))
            {
                Fail("missing/duplicate RIG_Table_Root or nonpositive/nonuniform scale in its ancestors");
                return;
            }
            if (movingBody == null) movingBody = GetComponentInParent<Rigidbody>();
            Transform upMarker = FindUnique(rigRoot, "RIG_GroundUp");
            if (upMarker == null || upMarker.parent != rigRoot || casters == null || casters.Length != 4)
            {
                Fail("expected RIG_GroundUp directly under the rig root and four caster entries");
                return;
            }
            worldScale = rigRoot.TransformVector(Vector3.right).magnitude;
            Vector3 upOffset = upMarker.position - rigRoot.position;
            if (!Near(upOffset.magnitude / worldScale, 0.1f))
            {
                Fail("RIG_GroundUp must be 0.1 model metres above the root");
                return;
            }
            groundUp = upOffset.normalized;
            rootUp = rigRoot.InverseTransformDirection(groundUp);
            var names = new HashSet<string>();
            float? contactHeight = null;
            foreach (Caster caster in casters)
            {
                if (caster == null || string.IsNullOrEmpty(caster.suffix) || !names.Add(caster.suffix))
                {
                    Fail("null, unnamed or duplicate caster entry");
                    return;
                }
                caster.steer = FindUnique(rigRoot, "RIG_CasterSteer_" + caster.suffix);
                caster.roll = FindUnique(rigRoot, "RIG_WheelRoll_" + caster.suffix);
                Transform axle = FindUnique(rigRoot, "RIG_WheelAxle_" + caster.suffix);
                Transform radius = FindUnique(rigRoot, "RIG_WheelRadius_" + caster.suffix);
                if (caster.steer == null || caster.roll == null || axle == null || radius == null ||
                    caster.steer.parent != rigRoot || caster.roll.parent != caster.steer ||
                    axle.parent != caster.roll || radius.parent != caster.roll || !UniformScale(caster.roll))
                {
                    Fail("missing, duplicate or misparented pivots/markers, or invalid scale: " + caster.suffix);
                    return;
                }
                Vector3 offset = caster.roll.position - caster.steer.position;
                Vector3 trail = Vector3.ProjectOnPlane(offset, groundUp);
                Vector3 axleOffset = axle.position - caster.roll.position;
                Vector3 radiusOffset = radius.position - caster.roll.position;
                Vector3 forward = -trail.normalized;
                Vector3 axleDirection = axleOffset.normalized;
                float wheelContactHeight = Vector3.Dot(radius.position - rigRoot.position, groundUp) / worldScale;
                if (!contactHeight.HasValue) contactHeight = wheelContactHeight;
                if (!Near(trail.magnitude / worldScale, ModelTrail) ||
                    Vector3.Dot(offset, groundUp) >= 0f || !Near(wheelContactHeight, contactHeight.Value) ||
                    !Near(axleOffset.magnitude / worldScale, 0.1f) ||
                    !Near(radiusOffset.magnitude / worldScale, ModelRadius) ||
                    Vector3.Dot(radiusOffset.normalized, -groundUp) < 0.9999f ||
                    Mathf.Abs(Vector3.Dot(axleDirection, groundUp)) > 0.001f ||
                    Mathf.Abs(Vector3.Dot(axleDirection, forward)) > 0.001f)
                {
                    Fail("incorrect rest geometry: " + caster.suffix +
                        "; trail=" + (trail.magnitude / worldScale) +
                        "; vertical=" + (Vector3.Dot(offset, groundUp) / worldScale) +
                        "; axle marker=" + (axleOffset.magnitude / worldScale) +
                        "; radius=" + (radiusOffset.magnitude / worldScale) +
                        "; radius/down dot=" + Vector3.Dot(radiusOffset.normalized, -groundUp) +
                        "; axle/up dot=" + Vector3.Dot(axleDirection, groundUp) +
                        "; axle/heading dot=" + Vector3.Dot(axleDirection, forward));
                    return;
                }
                caster.restSteer = caster.steer.localRotation;
                caster.restRoll = caster.roll.localRotation;
                caster.steerAxis = caster.steer.InverseTransformDirection(groundUp).normalized;
                caster.rollAxis = caster.roll.InverseTransformDirection(axleDirection).normalized;
                caster.restForward = Quaternion.Inverse(caster.steer.rotation) * forward;
                caster.axleSign = Math.Sign(Vector3.Dot(Vector3.Cross(axleDirection, groundUp), forward));
            }
            ready = true;
            CapturePose();
        }

        private void OnEnable()
        {
            if (ready) CapturePose();
        }

        private Vector3 ReferenceForward(Caster caster) => caster.steer.parent.rotation * caster.restSteer * caster.restForward;

        private void CapturePose()
        {
            previousRootPosition = rigRoot.position;
            foreach (Caster caster in casters)
            {
                caster.previousPosition = caster.steer.position;
                caster.previousForward = ReferenceForward(caster);
            }
        }

        private void LateUpdate()
        {
            Advance(Time.deltaTime);
        }

        // Kept separate from the Unity callback so actual imported transforms can be checked deterministically.
        private void Advance(float dt)
        {
            if (!ready || dt <= 0f) return;
            if (Vector3.Dot(rigRoot.TransformDirection(rootUp), groundUp) < 0.9999f ||
                !UniformScale(rigRoot) || !Near(rigRoot.TransformVector(Vector3.right).magnitude, worldScale))
            {
                Fail("runtime tilt or scale change: this controller requires a fixed planar ground and fixed uniform scale");
                return;
            }
            float yaw = Vector3.SignedAngle(casters[0].previousForward, ReferenceForward(casters[0]), groundUp);
            bool teleport = Mathf.Abs(yaw) > teleportYawDegrees;
            foreach (Caster caster in casters)
                teleport |= teleportDistance > 0f &&
                    (caster.steer.position - caster.previousPosition).sqrMagnitude > teleportDistance * teleportDistance;
            if (teleport)
            {
                CapturePose();
                return;
            }
            Vector3 rootVelocity = (rigRoot.position - previousRootPosition) / dt;
            float yawRate = yaw * Mathf.Deg2Rad / dt;
            bool dynamicBody = movingBody != null && !movingBody.isKinematic;
            foreach (Caster caster in casters)
            {
                Vector3 reference;
                Vector3 velocity;
                if (dynamicBody)
                {
                    reference = ReferenceForward(caster);
                    velocity = movingBody.GetPointVelocity(caster.steer.position);
                }
                else
                {
                    Quaternion toMidpoint = Quaternion.AngleAxis(-0.5f * yaw, groundUp);
                    reference = toMidpoint * ReferenceForward(caster);
                    Vector3 midpointOffset = toMidpoint * (caster.steer.position - rigRoot.position);
                    velocity = rootVelocity + Vector3.Cross(groundUp * yawRate, midpointOffset);
                }
                Vector3 lateral = Vector3.Cross(groundUp, reference);
                CasterKinematics.Advance(ref caster.heading, ref caster.spin, ref caster.reversing,
                    Vector3.Dot(velocity, reference), Vector3.Dot(velocity, lateral), yawRate,
                    dt, ModelTrail * worldScale, ModelRadius * worldScale, caster.axleSign);
                // Store continuous double angles; reduce only the quaternion input for precision.
                caster.steer.localRotation = caster.restSteer * Quaternion.AngleAxis(
                    (float)(caster.heading * 180.0 / Math.PI % 360.0), caster.steerAxis);
                caster.roll.localRotation = caster.restRoll * Quaternion.AngleAxis(
                    (float)(caster.spin * 180.0 / Math.PI % 360.0), caster.rollAxis);
            }
            CapturePose();
        }

        private void Fail(string reason)
        {
            Debug.LogError("TABLE-ASTRA-001: " + reason + ". See TableAstra/SETUP.md.", this);
            ready = false;
            enabled = false;
        }

        private static bool Near(float actual, float expected) => Mathf.Abs(actual - expected) <= 0.0005f;

        private static bool UniformScale(Transform value)
        {
            for (Transform node = value; node != null; node = node.parent)
            {
                Vector3 scale = node.localScale;
                if (scale.x <= 0f || scale.y <= 0f || scale.z <= 0f ||
                    Mathf.Abs(scale.x - scale.y) > scale.x * 0.0001f ||
                    Mathf.Abs(scale.x - scale.z) > scale.x * 0.0001f) return false;
            }
            return true;
        }

        private static Transform FindUnique(Transform parent, string objectName)
        {
            Transform result = null;
            foreach (Transform child in parent.GetComponentsInChildren<Transform>(true))
                if (child.name == objectName)
                {
                    if (result != null) return null;
                    result = child;
                }
            return result;
        }
    }
}
