// Adapted from OpenKCC's CapsuleColliderCast and KCCUtils bounce architecture.
// OpenKCC Copyright (C) 2023 Nicholas Maltbie, MIT License.
// See LICENSE.md in this directory for the complete license and adaptation notes.

using UnityEngine;

namespace OnlyVolunteers.ThirdParty.OpenKCCAdapted
{
    public readonly struct CapsuleMotorMoveResult
    {
        public CapsuleMotorMoveResult(
            Vector3 requestedDisplacement,
            Vector3 resolvedDisplacement,
            bool hitGround,
            bool hitCeiling,
            bool hitSide,
            int bounceCount)
        {
            RequestedDisplacement = requestedDisplacement;
            ResolvedDisplacement = resolvedDisplacement;
            HitGround = hitGround;
            HitCeiling = hitCeiling;
            HitSide = hitSide;
            BounceCount = bounceCount;
        }

        public Vector3 RequestedDisplacement { get; }
        public Vector3 ResolvedDisplacement { get; }
        public bool HitGround { get; }
        public bool HitCeiling { get; }
        public bool HitSide { get; }
        public int BounceCount { get; }
    }

    /// <summary>
    /// Small capsule-cast kinematic motor adapted from OpenKCC's cast/bounce model.
    /// It never asks Unity's CharacterController to depenetrate the player: requested
    /// displacement is swept, stopped at skin distance, and projected along contact planes.
    /// </summary>
    public sealed class OnlyVolunteersCapsuleMotor
    {
        const int MaximumBounces = 5;
        const int HitCapacity = 32;
        const int OverlapCapacity = 32;
        const float MovementEpsilon = 0.0001f;
        const float GroundProbeLift = 0.05f;

        readonly Transform owner;
        readonly CapsuleCollider capsule;
        readonly RaycastHit[] castHits = new RaycastHit[HitCapacity];
        readonly RaycastHit[] groundHits = new RaycastHit[HitCapacity];
        readonly Collider[] overlapHits = new Collider[OverlapCapacity];

        readonly float skinWidth;
        readonly float minimumGroundDot;
        readonly int collisionMask;

        public OnlyVolunteersCapsuleMotor(
            Transform owner,
            CapsuleCollider capsule,
            float skinWidth,
            float slopeLimitDegrees,
            int collisionMask)
        {
            this.owner = owner;
            this.capsule = capsule;
            this.skinWidth = Mathf.Max(0.001f, skinWidth);
            minimumGroundDot = Mathf.Cos(slopeLimitDegrees * Mathf.Deg2Rad);
            this.collisionMask = collisionMask;
        }

        public float Height => capsule.height;
        public float Radius => capsule.radius;
        public Vector3 Center => capsule.center;

        public void SetShape(float height, Vector3 center)
        {
            capsule.height = height;
            capsule.center = center;
        }

        public bool CanOccupy(float height, Vector3 center)
        {
            GetCapsule(
                owner.position,
                height,
                center,
                out Vector3 top,
                out Vector3 bottom,
                out float radius);

            // Stance changes are transactional and must be stricter than movement sweeps.
            // Test the complete final capsule, not the skin-shrunk sweep volume, so an
            // accepted stand can never begin with the real collider inside geometry.
            float queryRadius = radius;
            int count = Physics.OverlapCapsuleNonAlloc(
                top,
                bottom,
                queryRadius,
                overlapHits,
                collisionMask,
                QueryTriggerInteraction.Ignore);

            if (count >= overlapHits.Length)
            {
                return false;
            }

            for (int i = 0; i < count; i++)
            {
                if (IsEnvironmentCollider(overlapHits[i]))
                {
                    return false;
                }
            }

            return true;
        }

        public bool TryGetGround(float maximumDistance, out RaycastHit supportHit)
        {
            return TryGetGround(owner.position, maximumDistance, out supportHit);
        }

        public CapsuleMotorMoveResult Move(Vector3 requestedDisplacement)
        {
            Vector3 start = owner.position;
            Vector3 position = start;
            Vector3 remaining = requestedDisplacement;
            bool hitGround = false;
            bool hitCeiling = false;
            bool hitSide = false;
            int bounceCount = 0;

            while (remaining.sqrMagnitude > MovementEpsilon * MovementEpsilon &&
                bounceCount < MaximumBounces)
            {
                if (!Cast(position, remaining, out RaycastHit hit))
                {
                    position += remaining;
                    remaining = Vector3.zero;
                    break;
                }

                float remainingDistance = remaining.magnitude;
                Vector3 direction = remaining / remainingDistance;
                float travelDistance = Mathf.Clamp(hit.distance, 0f, remainingDistance);
                Vector3 travel = direction * travelDistance;
                position += travel;
                remaining -= travel;

                Vector3 contactNormal = hit.normal.normalized;
                float verticalNormal = Vector3.Dot(contactNormal, owner.up);
                float verticalMovement = Vector3.Dot(remaining, owner.up);

                if (verticalMovement < 0f && verticalNormal > 0f)
                {
                    if (TryGetGround(position, skinWidth + GroundProbeLift, out RaycastHit groundHit))
                    {
                        contactNormal = groundHit.normal.normalized;
                        verticalNormal = Vector3.Dot(contactNormal, owner.up);
                        hitGround = verticalNormal >= minimumGroundDot;
                    }
                    else
                    {
                        // A rounded capsule grazing a box lip can report an upward normal even
                        // though the nominal feet have no support. Treat that as a side contact
                        // so projection removes only the blocked horizontal component and the
                        // requested ballistic fall continues unchanged.
                        contactNormal = GetUnsupportedEdgeNormal(position, hit, remaining);
                        verticalNormal = 0f;
                    }
                }

                if (verticalMovement > 0f && verticalNormal < -0.01f)
                {
                    hitCeiling = true;
                }
                if (Mathf.Abs(verticalNormal) < minimumGroundDot)
                {
                    hitSide = true;
                }

                Vector3 projected = Vector3.ProjectOnPlane(remaining, contactNormal);
                if (projected.sqrMagnitude > remaining.sqrMagnitude)
                {
                    projected = projected.normalized * remaining.magnitude;
                }
                if (Vector3.Dot(projected, requestedDisplacement) < -MovementEpsilon)
                {
                    projected = Vector3.zero;
                }

                bool madeProgress = travel.sqrMagnitude > MovementEpsilon * MovementEpsilon ||
                    (projected - remaining).sqrMagnitude > MovementEpsilon * MovementEpsilon;
                remaining = projected;
                bounceCount++;

                if (!madeProgress)
                {
                    break;
                }
            }

            owner.position = position;
            return new CapsuleMotorMoveResult(
                requestedDisplacement,
                position - start,
                hitGround,
                hitCeiling,
                hitSide,
                bounceCount);
        }

        bool Cast(Vector3 position, Vector3 displacement, out RaycastHit closestHit)
        {
            closestHit = new RaycastHit { distance = float.PositiveInfinity };
            float distance = displacement.magnitude;
            if (distance <= MovementEpsilon)
            {
                return false;
            }

            GetCapsule(position, capsule.height, capsule.center,
                out Vector3 top, out Vector3 bottom, out float radius);
            float queryRadius = Mathf.Max(0.001f, radius - skinWidth);
            Vector3 direction = displacement / distance;
            int count = Physics.CapsuleCastNonAlloc(
                top,
                bottom,
                queryRadius,
                direction,
                castHits,
                distance + skinWidth,
                collisionMask,
                QueryTriggerInteraction.Ignore);

            bool found = false;
            for (int i = 0; i < count; i++)
            {
                RaycastHit candidate = castHits[i];
                if (!IsEnvironmentCollider(candidate.collider))
                {
                    continue;
                }

                candidate.distance = Mathf.Max(0f, candidate.distance - skinWidth);
                if (candidate.distance < closestHit.distance)
                {
                    closestHit = candidate;
                    found = true;
                }
            }

            return found;
        }

        bool TryGetGround(Vector3 position, float maximumDistance, out RaycastHit supportHit)
        {
            supportHit = new RaycastHit { distance = float.PositiveInfinity };
            Vector3 origin = position + owner.up * GroundProbeLift;
            int count = Physics.RaycastNonAlloc(
                origin,
                -owner.up,
                groundHits,
                GroundProbeLift + Mathf.Max(0f, maximumDistance),
                collisionMask,
                QueryTriggerInteraction.Ignore);

            bool found = false;
            for (int i = 0; i < count; i++)
            {
                RaycastHit candidate = groundHits[i];
                if (!IsEnvironmentCollider(candidate.collider) ||
                    Vector3.Dot(candidate.normal, owner.up) < minimumGroundDot)
                {
                    continue;
                }

                float belowFeet = Vector3.Dot(position - candidate.point, owner.up);
                if (belowFeet < -skinWidth || belowFeet > maximumDistance + skinWidth)
                {
                    continue;
                }

                if (candidate.distance < supportHit.distance)
                {
                    supportHit = candidate;
                    found = true;
                }
            }

            return found;
        }

        Vector3 GetUnsupportedEdgeNormal(
            Vector3 position,
            RaycastHit hit,
            Vector3 remaining)
        {
            Vector3 horizontalNormal = Vector3.ProjectOnPlane(hit.normal, owner.up);
            if (horizontalNormal.sqrMagnitude > MovementEpsilon * MovementEpsilon)
            {
                return horizontalNormal.normalized;
            }

            GetCapsule(position, capsule.height, capsule.center,
                out _, out Vector3 bottom, out _);
            horizontalNormal = Vector3.ProjectOnPlane(bottom - hit.point, owner.up);
            if (horizontalNormal.sqrMagnitude > MovementEpsilon * MovementEpsilon)
            {
                return horizontalNormal.normalized;
            }

            horizontalNormal = -Vector3.ProjectOnPlane(remaining, owner.up);
            return horizontalNormal.sqrMagnitude > MovementEpsilon * MovementEpsilon
                ? horizontalNormal.normalized
                : owner.right;
        }

        void GetCapsule(
            Vector3 rootPosition,
            float height,
            Vector3 center,
            out Vector3 top,
            out Vector3 bottom,
            out float radius)
        {
            Vector3 scale = owner.lossyScale;
            float verticalScale = Mathf.Abs(scale.y);
            float radialScale = Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            radius = capsule.radius * radialScale;
            float worldHeight = Mathf.Max(height * verticalScale, radius * 2f);
            Vector3 scaledCenter = Vector3.Scale(center, scale);
            Vector3 worldCenter = rootPosition + owner.rotation * scaledCenter;
            float centerToSphere = Mathf.Max(0f, worldHeight * 0.5f - radius);
            top = worldCenter + owner.up * centerToSphere;
            bottom = worldCenter - owner.up * centerToSphere;
        }

        bool IsEnvironmentCollider(Collider candidate)
        {
            return candidate != null &&
                candidate != capsule &&
                !candidate.transform.IsChildOf(owner) &&
                !Physics.GetIgnoreCollision(capsule, candidate);
        }
    }
}
