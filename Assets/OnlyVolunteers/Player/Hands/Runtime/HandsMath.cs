using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Pure math of the first-person hands: no scene, no time source; covered by EditMode tests.</summary>
    public static class HandsMath
    {
        private const float Epsilon = 1e-5f;

        /// <summary>Two-bone IK in world space. Root (shoulder) at <paramref name="root"/>, bone lengths
        /// <paramref name="upperLength"/> and <paramref name="lowerLength"/>. The elbow bends towards
        /// <paramref name="poleHint"/>. An unreachable target is clamped onto the reach sphere (arm almost straight,
        /// kept at <paramref name="maxStretch"/> of full length so the elbow never snaps through).</summary>
        /// <returns>True when the target was reachable without clamping.</returns>
        public static bool SolveTwoBone(Vector3 root, float upperLength, float lowerLength, Vector3 target,
            Vector3 poleHint, out Vector3 elbow, out Vector3 end, float maxStretch = 0.999f)
        {
            Vector3 toTarget = target - root;
            float distance = toTarget.magnitude;
            Vector3 dir = distance > Epsilon ? toTarget / distance : Vector3.forward;

            float maxReach = (upperLength + lowerLength) * Mathf.Clamp01(maxStretch);
            float minReach = Mathf.Abs(upperLength - lowerLength) + Epsilon;
            bool reachable = distance <= maxReach && distance >= minReach;
            float d = Mathf.Clamp(distance, minReach, Mathf.Max(minReach, maxReach));

            // Bend direction: the pole hint projected off the root->target axis.
            Vector3 bend = Vector3.ProjectOnPlane(poleHint - root, dir);
            if (bend.sqrMagnitude < Epsilon * Epsilon)
            {
                bend = Vector3.ProjectOnPlane(Vector3.down, dir);
                if (bend.sqrMagnitude < Epsilon * Epsilon) bend = Vector3.ProjectOnPlane(Vector3.forward, dir);
            }
            bend.Normalize();

            // Law of cosines: the angle at the root between the target axis and the upper bone.
            float cosA = Mathf.Clamp((upperLength * upperLength + d * d - lowerLength * lowerLength) /
                                     (2f * upperLength * d), -1f, 1f);
            float sinA = Mathf.Sqrt(Mathf.Max(0f, 1f - cosA * cosA));

            elbow = root + dir * (upperLength * cosA) + bend * (upperLength * sinA);
            end = root + dir * d;
            return reachable;
        }

        /// <summary>Exact critically damped spring step (no overshoot from rest). <paramref name="halfLife"/> is the
        /// time to cover half the remaining distance; 0 snaps.</summary>
        public static float SpringStep(float value, ref float velocity, float target, float halfLife, float dt)
        {
            if (halfLife <= Epsilon) { velocity = 0f; return target; }
            if (dt <= 0f) return value;
            // Critical damping y: from rest, e^(-y t)(1 + y t) = 0.5 at y t = 1.678347, so t = halfLife exactly.
            float y = 1.678347f / halfLife;
            float j0 = value - target;
            float j1 = velocity + j0 * y;
            float e = Mathf.Exp(-y * dt);
            velocity = e * (velocity - j1 * y * dt);
            return e * (j0 + j1 * dt) + target;
        }

        public static Vector3 SpringStep(Vector3 value, ref Vector3 velocity, Vector3 target, float halfLife, float dt)
        {
            float vx = velocity.x, vy = velocity.y, vz = velocity.z;
            var r = new Vector3(SpringStep(value.x, ref vx, target.x, halfLife, dt),
                SpringStep(value.y, ref vy, target.y, halfLife, dt),
                SpringStep(value.z, ref vz, target.z, halfLife, dt));
            velocity = new Vector3(vx, vy, vz);
            return r;
        }

        /// <summary>Weapon-style sway: the view model lags behind the look. <paramref name="lookVelocity"/> is
        /// (yaw, pitch) in degrees per second; returns (pitch, yaw, roll) offset degrees, each clamped to
        /// <paramref name="maxDegrees"/>. Gains are degrees of offset per degree/second of look.</summary>
        public static Vector3 SwayAngles(Vector2 lookVelocity, float gain, float maxDegrees, float rollGain)
        {
            float yaw = Mathf.Clamp(-lookVelocity.x * gain, -maxDegrees, maxDegrees);
            float pitch = Mathf.Clamp(-lookVelocity.y * gain, -maxDegrees, maxDegrees);
            float roll = Mathf.Clamp(-lookVelocity.x * rollGain, -maxDegrees, maxDegrees);
            return new Vector3(pitch, yaw, roll);
        }

        /// <summary>Advances the walk-bob phase (radians) by distance walked; <paramref name="cyclesPerMeter"/> is
        /// one left+right step pair per cycle.</summary>
        public static float AdvanceBobPhase(float phase, float planarSpeed, float cyclesPerMeter, float dt)
        {
            phase += Mathf.Max(0f, planarSpeed) * cyclesPerMeter * dt * 2f * Mathf.PI;
            return Mathf.Repeat(phase, 2f * Mathf.PI);
        }

        /// <summary>Figure-eight bob offset: sideways once per cycle, vertical dip twice (each footstep).
        /// <paramref name="weight"/> 0..1 (usually speed / reference speed).</summary>
        public static Vector3 BobOffset(float phase, float weight, Vector2 amplitude)
        {
            weight = Mathf.Clamp01(weight);
            float x = Mathf.Sin(phase) * amplitude.x;
            float y = -Mathf.Abs(Mathf.Sin(phase)) * amplitude.y;
            return new Vector3(x, y, 0f) * weight;
        }

        /// <summary>Scale for view-space x/y so a point keeps its screen position when drawn by a view-model camera
        /// with <paramref name="viewModelFov"/> instead of the world camera's <paramref name="worldFov"/>
        /// (vertical FOVs in degrees). Multiply view-space x and y by it, keep z.</summary>
        public static float FovCompensation(float worldFov, float viewModelFov)
        {
            float w = Mathf.Tan(Mathf.Clamp(worldFov, 1f, 179f) * 0.5f * Mathf.Deg2Rad);
            float v = Mathf.Tan(Mathf.Clamp(viewModelFov, 1f, 179f) * 0.5f * Mathf.Deg2Rad);
            return v / w;
        }

        public static Vector3 WorldToViewModelSpace(Vector3 viewLocal, float worldFov, float viewModelFov)
        {
            float k = FovCompensation(worldFov, viewModelFov);
            return new Vector3(viewLocal.x * k, viewLocal.y * k, viewLocal.z);
        }

        /// <summary>How far to pull the view model back (0 none .. 1 full) when a wall is
        /// <paramref name="hitDistance"/> ahead and the hands reach <paramref name="reach"/>.</summary>
        public static float WallRetract(float hitDistance, float reach)
        {
            if (reach <= Epsilon || hitDistance >= reach) return 0f;
            return Mathf.Clamp01(1f - Mathf.Max(0f, hitDistance) / reach);
        }

        /// <summary>One-shot use kick: 0 at start, peaks at <paramref name="attack"/> of the duration, back to 0 at end.</summary>
        public static float UseKick(float elapsed, float duration, float attack = 0.3f)
        {
            if (duration <= Epsilon || elapsed <= 0f || elapsed >= duration) return 0f;
            float t = elapsed / duration;
            attack = Mathf.Clamp(attack, 0.05f, 0.95f);
            return t < attack ? Mathf.Sin(t / attack * Mathf.PI * 0.5f)
                : Mathf.Cos((t - attack) / (1f - attack) * Mathf.PI * 0.5f);
        }

        // --- poses (position + rotation) ---

        public static Pose Multiply(Pose parent, Pose local) =>
            new Pose(parent.position + parent.rotation * local.position, parent.rotation * local.rotation);

        public static Pose Inverse(Pose p)
        {
            Quaternion inv = Quaternion.Inverse(p.rotation);
            return new Pose(inv * -p.position, inv);
        }

        /// <summary>Where an item must be so its grip socket (<paramref name="socketInItem"/>, item-local) lies on
        /// the hand's grip point (<paramref name="handGripWorld"/>).</summary>
        public static Pose ItemPoseFromGrip(Pose handGripWorld, Pose socketInItem) =>
            Multiply(handGripWorld, Inverse(socketInItem));

        /// <summary>Where a hand bone must be so its grip point (<paramref name="gripInHand"/>, hand-local) lies on
        /// <paramref name="socketWorld"/>.</summary>
        public static Pose HandPoseFromSocket(Pose socketWorld, Pose gripInHand) =>
            Multiply(socketWorld, Inverse(gripInHand));

        public static Pose Lerp(Pose a, Pose b, float t)
        {
            t = Mathf.Clamp01(t);
            return new Pose(Vector3.LerpUnclamped(a.position, b.position, t), Quaternion.Slerp(a.rotation, b.rotation, t));
        }

        /// <summary>Weighted rotation average (normalised quaternion sum with hemisphere fix); good for the
        /// small spread between hand poses. Weights need not sum to 1.</summary>
        public static Quaternion BlendRotations(Quaternion[] rotations, float[] weights, int count)
        {
            Vector4 acc = Vector4.zero;
            Quaternion first = Quaternion.identity;
            bool haveFirst = false;
            for (int i = 0; i < count; i++)
            {
                float w = weights[i];
                if (w <= 0f) continue;
                Quaternion q = rotations[i];
                if (!haveFirst) { first = q; haveFirst = true; }
                if (Quaternion.Dot(first, q) < 0f) w = -w;
                acc += new Vector4(q.x, q.y, q.z, q.w) * w;
            }
            float m = acc.magnitude;
            if (m < Epsilon) return haveFirst ? first : Quaternion.identity;
            acc /= m;
            return new Quaternion(acc.x, acc.y, acc.z, acc.w);
        }
    }
}
