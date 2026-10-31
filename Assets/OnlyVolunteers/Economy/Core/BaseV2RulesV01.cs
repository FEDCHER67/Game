using System;

namespace OnlyVolunteers.Economy
{
    /// <summary>The V2 base (hangar, Fedya 31.10, plan P1), pure rules: the workshop has no story gate, and only the
    /// upgrade group that already changes the driving is sold (the engine tiers).</summary>
    public static class BaseV2Rules
    {
        /// <summary>P1 sells ONE real upgrade group: the engine (top speed and pull). Brakes / handling stay in the code
        /// for later stages; cargo bodies are v1.</summary>
        public static readonly VanBranch[] SoldBranches = { VanBranch.Engine };

        /// <summary>V2 base: the workshop is open from the start (no M06 rival task; the v1 map keeps its gate). True when
        /// this call opened it.</summary>
        public static bool OpenWorkshop(EconomyState state)
        {
            if (state == null || state.WorkshopUnlocked) return false;
            state.SetWorkshopUnlocked(true);
            return true;
        }

        public static bool Sold(VanBranch branch) => Array.IndexOf(SoldBranches, branch) >= 0;
    }

    public enum DockSignal : byte
    {
        /// <summary>Nothing to do (out of the zone, too fast, no driver, or already docked this visit).</summary>
        None,
        /// <summary>In the zone, aligned and slow: counting the stable time.</summary>
        Settling,
        /// <summary>Slow in the zone but not lined up with the lift for a second: tell the driver.</summary>
        NeedsAlign,
        /// <summary>Docked now (once per visit: the zone must be left before the next dock).</summary>
        Dock,
    }

    /// <summary>
    /// Automatic docking at the workshop lift (plan P1 §2 "Workshop arrival"): the team van, with someone at the wheel, in
    /// the dock zone, lined up with the lift and moving at most <see cref="MaxSpeed"/> m/s for <see cref="StableSeconds"/>
    /// without a break docks once. Any frame faster, out of line or without a driver restarts the count; leaving the zone
    /// re-arms it (a van lowered after the service does not dock again until it has driven out). A van standing still out of
    /// line for a second gets the "line up" hint. Starting tuning 0.5 m/s /
    /// 0.5 s (plan recommendation, not yet playtested).
    /// </summary>
    public sealed class DockTrackerV2
    {
        public const float DefaultMaxSpeed = 0.5f;
        public const float DefaultStableSeconds = 0.5f;
        public const float AlignHintSeconds = 1f;
        /// <summary>The "line up" hint is only for a van that stands (nearly) still out of line, not one still creeping in.</summary>
        public const float HintBelowSpeed = 0.1f;

        public float MaxSpeed { get; }
        public float StableSeconds { get; }
        public float Stable { get; private set; }
        public bool Armed { get; private set; } = true;
        private float misaligned;

        public DockTrackerV2(float maxSpeed = DefaultMaxSpeed, float stableSeconds = DefaultStableSeconds)
        {
            MaxSpeed = maxSpeed > 0f ? maxSpeed : DefaultMaxSpeed;
            StableSeconds = stableSeconds > 0f ? stableSeconds : DefaultStableSeconds;
        }

        public DockSignal Step(bool inZone, bool aligned, float speed, bool driverIn, float dt)
        {
            if (!inZone)
            {
                Armed = true;
                Stable = 0f;
                misaligned = 0f;
                return DockSignal.None;
            }
            if (!Armed || !driverIn || float.IsNaN(speed) || speed > MaxSpeed)
            {
                Stable = 0f;
                misaligned = 0f;
                return DockSignal.None;
            }
            if (!(dt >= 0f)) dt = 0f;
            if (!aligned)
            {
                Stable = 0f;
                misaligned = speed < HintBelowSpeed ? misaligned + dt : 0f;
                return misaligned >= AlignHintSeconds ? DockSignal.NeedsAlign : DockSignal.None;
            }
            misaligned = 0f;
            Stable += dt;
            if (Stable + 1e-5f < StableSeconds) return DockSignal.Settling;
            Armed = false;
            Stable = 0f;
            return DockSignal.Dock;
        }

        /// <summary>No auto dock until the van has left the zone (a service already runs, or it was cancelled).</summary>
        public void Disarm()
        {
            Armed = false;
            Stable = 0f;
        }

        /// <summary>Lined up with the lift: van root within the tolerance of the park point (across, along) and its yaw
        /// within tolYaw of the park yaw, nose in or reversed (the lift takes it either way round).</summary>
        public static bool Aligned(float localX, float localZ, float yawDelta, float tolAcross, float tolAlong, float tolYaw)
        {
            float y = yawDelta % 360f;
            if (y > 180f) y -= 360f;
            if (y < -180f) y += 360f;
            if (Math.Abs(y) > 90f) y = y > 0f ? y - 180f : y + 180f;
            return Math.Abs(localX) <= tolAcross && Math.Abs(localZ) <= tolAlong && Math.Abs(y) <= tolYaw;
        }
    }

    /// <summary>The rubber baton (V2 shop item, Fedya 31.10): its own numbers next to Vadim's slap (CaptureV2Tuning:
    /// reach 2.3 m, 0.2 s cooldown, knock-out ladder 5/3/2/1 s, charge). The baton reaches further and always knocks out
    /// for the same time, but swings slowly and cannot be charged.</summary>
    public sealed class BatonTuningV2
    {
        public float Reach = 2.8f;
        /// <summary>The target must still be this close at the contact.</summary>
        public float LungeReach = 3.3f;
        /// <summary>Seconds from the press to the contact (the overhead swing).</summary>
        public float Windup = 0.16f;
        /// <summary>Seconds from one contact to the next swing.</summary>
        public float Cooldown = 0.9f;
        public float KnockOutSeconds = 4f;
    }

    public static class BatonRulesV2
    {
        public static bool Ready(float now, float lastSwing, float cooldown) => now - lastSwing >= cooldown - 1e-4f;

        /// <summary>Seconds out cold for the baton's hit number hitIndex of one catch: the same every time (the slap's
        /// ladder shortens; the baton is the reliable tool).</summary>
        public static float KnockOut(BatonTuningV2 t, int hitIndex) => t != null && t.KnockOutSeconds > 0f ? t.KnockOutSeconds : 4f;
    }
}
