using System;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Spring settings of one arm (see <see cref="ArmChannelV01"/>).</summary>
    [Serializable]
    public struct ArmSpringsV01
    {
        [Tooltip("Hand following its grip while holding (Hz, damping < 1 = a little wobble).")]
        public float TrackHz, TrackDamping;
        [Tooltip("Hand flying back after a release (lower, springier: the snap-back with overshoot).")]
        public float ReleaseHz, ReleaseDamping;
        [Tooltip("How long after a release the springier settings apply, s.")]
        public float ReleaseTime;
        [Tooltip("Arm length (stretch) following the reach it needs: low damping = the rubbery wobble.")]
        public float StretchHz, StretchDamping;
        [Tooltip("The springs may squash the arm to this length on the snap-back (overshoot below 1).")]
        public float MinStretch;
        [Tooltip("Third person: seconds to blend from the body clip to the hold and back.")]
        public float BlendTime;

        public static ArmSpringsV01 Default => new ArmSpringsV01
        {
            TrackHz = 9f, TrackDamping = 0.62f,
            ReleaseHz = 5.2f, ReleaseDamping = 0.3f, ReleaseTime = 0.8f,
            // Fedya 30.10 (exaggeration / 1.7): damping 0.26 -> 0.40 cuts the length overshoot from ~43% to ~25% of a
            // change, and the snap-back squash floor 0.78 -> 0.87 (22% -> 13%).
            StretchHz = 6.5f, StretchDamping = 0.40f,
            MinStretch = 0.87f, BlendTime = 0.16f,
        };
    }

    /// <summary>
    /// The springy state of one arm of one rig: where the wrist is aimed (a point in the caller's frame: camera space for
    /// the first-person arms, body space for the third-person body), how long the arm is, and (third person) how much the
    /// hold overrides the body clip. Plain C#, deterministic for a given dt sequence; EditMode tests drive it directly.
    /// </summary>
    public sealed class ArmChannelV01
    {
        public Vector3 Wrist { get; private set; }
        public float Stretch { get; private set; } = 1f;
        public float Weight { get; private set; }
        public bool Active { get; private set; }
        public bool Initialised { get; private set; }
        public float StretchVelocity => stretchVelocity;

        private Vector3 wristVelocity;
        private float stretchVelocity;
        private float releasedFor = 999f;

        public void Snap(Vector3 wrist, float stretch = 1f)
        {
            Wrist = wrist; wristVelocity = Vector3.zero;
            Stretch = stretch; stretchVelocity = 0f;
            Initialised = true;
        }

        /// <summary>Moves the wrist toward <paramref name="goal"/>: tight while holding, springy after a release.</summary>
        public bool Springy => !Active && releasedFor < lastReleaseTime;
        private float lastReleaseTime;

        public void TickWrist(Vector3 goal, bool active, in ArmSpringsV01 springs, float dt)
        {
            if (!Initialised) Snap(goal);
            if (Active && !active) releasedFor = 0f;
            Active = active;
            releasedFor += Mathf.Max(0f, dt);
            lastReleaseTime = springs.ReleaseTime;
            bool springy = !active && releasedFor < springs.ReleaseTime;
            Vector3 v = wristVelocity;
            Wrist = ArmStretchMath.Spring(Wrist, ref v, goal,
                springy ? springs.ReleaseHz : springs.TrackHz, springy ? springs.ReleaseDamping : springs.TrackDamping, dt);
            wristVelocity = v;
            float blend = springs.BlendTime > 1e-4f ? Mathf.Max(0f, dt) / springs.BlendTime : 1f;
            // Third person keeps the hold on while the released hand still flies back (the overshoot shows), then
            // blends into the body clip.
            Weight = Mathf.MoveTowards(Weight, active || springy ? 1f : 0f, blend);
        }

        /// <summary>Direct drive by a keyed motion (the punch): wrist, arm length and hold weight are set as given and the
        /// velocities zeroed. The channel counts as holding meanwhile, so the first TickWrist with active = false after
        /// the drive is a release (the springy snap-back from where the drive left the arm).</summary>
        public void Drive(Vector3 wrist, float stretch, float weight)
        {
            Wrist = wrist; wristVelocity = Vector3.zero;
            Stretch = Mathf.Max(0.3f, stretch); stretchVelocity = 0f;
            Weight = Mathf.Clamp01(weight);
            Active = true;
            Initialised = true;
        }

        /// <summary>Moves the arm length toward the stretch the wrist needs now (already soft-clamped by the caller).
        /// Underdamped: overshoots (a squash below 1 on the snap-back), never below MinStretch or above
        /// <paramref name="maxStretch"/>.</summary>
        public void TickStretch(float needed, float maxStretch, in ArmSpringsV01 springs, float dt)
        {
            if (!Initialised) Snap(Wrist, needed);
            float v = stretchVelocity;
            float s = ArmStretchMath.Spring(Stretch, ref v, needed, springs.StretchHz, springs.StretchDamping, dt);
            float lo = Mathf.Clamp(springs.MinStretch, 0.3f, 1f), hi = Mathf.Max(1f, maxStretch);
            if (s < lo) { s = lo; if (v < 0f) v = 0f; }
            if (s > hi) { s = hi; if (v > 0f) v = 0f; }
            Stretch = s;
            stretchVelocity = v;
        }
    }
}
