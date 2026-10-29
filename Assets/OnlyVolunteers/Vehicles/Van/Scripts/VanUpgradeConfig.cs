using System;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    [Serializable]
    public struct VanEngineLevel
    {
        [Tooltip("Multiplier on stock MotorTorque (reverse torque follows it).")]
        public float TorqueMultiplier;
        [Tooltip("Added to stock MaxSpeedKmh.")]
        public float MaxSpeedBonusKmh;
        [Tooltip("Added to stock ReverseSpeedKmh.")]
        public float ReverseSpeedBonusKmh;

        public VanEngineLevel(float torqueMultiplier, float maxSpeedBonusKmh, float reverseSpeedBonusKmh)
        {
            TorqueMultiplier = torqueMultiplier;
            MaxSpeedBonusKmh = maxSpeedBonusKmh;
            ReverseSpeedBonusKmh = reverseSpeedBonusKmh;
        }

        public static VanEngineLevel Stock => new(1f, 0f, 0f);
    }

    [Serializable]
    public struct VanBrakesLevel
    {
        [Tooltip("Multiplier on stock BrakeTorque.")]
        public float BrakeTorqueMultiplier;
        [Tooltip("Multiplier on stock HandbrakeTorque.")]
        public float HandbrakeTorqueMultiplier;
        [Tooltip("Multiplier on the stock forward friction of every wheel.")]
        public float ForwardGripMultiplier;

        public VanBrakesLevel(float brakeTorqueMultiplier, float handbrakeTorqueMultiplier, float forwardGripMultiplier)
        {
            BrakeTorqueMultiplier = brakeTorqueMultiplier;
            HandbrakeTorqueMultiplier = handbrakeTorqueMultiplier;
            ForwardGripMultiplier = forwardGripMultiplier;
        }

        public static VanBrakesLevel Stock => new(1f, 1f, 1f);
    }

    [Serializable]
    public struct VanHandlingLevel
    {
        [Tooltip("Multiplier on the stock sideways friction of every wheel (same effect as WheelFrictionCurve.stiffness).")]
        public float SidewaysGripMultiplier;
        [Tooltip("Multiplier on stock AntiRoll.")]
        public float AntiRollMultiplier;
        [Tooltip("Degrees added to stock HighSpeedSteerAngle (capped by MaxSteerAngle).")]
        public float HighSpeedSteerBonus;
        [Tooltip("Multiplier on stock SteerSpeed.")]
        public float SteerSpeedMultiplier;

        public VanHandlingLevel(float sidewaysGripMultiplier, float antiRollMultiplier, float highSpeedSteerBonus, float steerSpeedMultiplier)
        {
            SidewaysGripMultiplier = sidewaysGripMultiplier;
            AntiRollMultiplier = antiRollMultiplier;
            HighSpeedSteerBonus = highSpeedSteerBonus;
            SteerSpeedMultiplier = steerSpeedMultiplier;
        }

        public static VanHandlingLevel Stock => new(1f, 1f, 0f, 1f);
    }

    // ECONOMY spec v01 §6.1: one engine tier (0..III) of the paid progression. Top speed is absolute (the target limit),
    // the torque multiplier is relative to the tier-0 profile, not to whatever the scene's wheels happen to hold.
    [Serializable]
    public struct VanEngineTier
    {
        [Tooltip("Forward speed limit at this tier, km/h (absolute).")]
        public float TopSpeedKmh;
        [Tooltip("Multiplier on the tier-0 MotorTorque (reverse torque follows it).")]
        public float TorqueMultiplier;

        public VanEngineTier(float topSpeedKmh, float torqueMultiplier)
        {
            TopSpeedKmh = topSpeedKmh;
            TorqueMultiplier = torqueMultiplier;
        }
    }

    // ECONOMY spec v01 §6.1: the NEW tier-0 profile of the progression ("comfortable but weaker"), as scales on the van's
    // own scene values (the wheel colliders and VanController fields VanUpgrades captures as stock). Tiers I..III multiply
    // this profile. First playtest preset: the scene stock with the top speed limited to 70 km/h; tune here, on the real
    // van (spec: the new base torque / brakes are set by driving it, ES-48 needs a human test).
    [Serializable]
    public struct VanTierZeroProfile
    {
        public float TorqueScale;
        public float BrakeTorqueScale;
        public float HandbrakeTorqueScale;
        public float ForwardGripScale;
        public float SidewaysGripScale;
        public float AntiRollScale;
        public float SteerSpeedScale;
        [Tooltip("Degrees added to the stock HighSpeedSteerAngle at tier 0.")]
        public float HighSpeedSteerOffset;

        public static VanTierZeroProfile Default => new VanTierZeroProfile
        {
            TorqueScale = 1f, BrakeTorqueScale = 1f, HandbrakeTorqueScale = 1f, ForwardGripScale = 1f,
            SidewaysGripScale = 1f, AntiRollScale = 1f, SteerSpeedScale = 1f, HighSpeedSteerOffset = 0f,
        };
    }

    // Upgrade steps relative to the van's stock tuning. Each array holds levels 1..MaxLevel;
    // level 0 is always the stock values captured by VanUpgrades.
    // Two sets live here: the old debug/legacy levels (StartAtMax, debug keys 7/8/9; the old max ~147 km/h) and the paid
    // progression tiers 0..III of the team economy (§6.1; tier III ~115 km/h, calmer than the old max).
    [CreateAssetMenu(fileName = "VanUpgradeConfig", menuName = "OnlyVolunteers/Vehicles/Van Upgrade Config")]
    public sealed class VanUpgradeConfig : ScriptableObject
    {
        // ---------- paid progression (§6.1 table, index = tier 0..III) ----------

        private static readonly VanEngineTier[] DefaultProgressionEngine =
        {
            new(70f, 1f), new(85f, 1.12f), new(100f, 1.25f), new(115f, 1.40f),
        };

        // Brake torque, handbrake, forward grip of the brakes branch.
        private static readonly VanBrakesLevel[] DefaultProgressionBrakes =
        {
            new(1f, 1f, 1f), new(1.15f, 1.08f, 1.05f), new(1.30f, 1.16f, 1.10f), new(1.45f, 1.24f, 1.15f),
        };

        // Sideways grip, anti-roll, high-speed steer angle bonus (degrees), steer speed of the handling branch.
        private static readonly VanHandlingLevel[] DefaultProgressionHandling =
        {
            new(1f, 1f, 0f, 1f), new(1.06f, 1.12f, 1f, 1.10f), new(1.12f, 1.25f, 2f, 1.20f), new(1.20f, 1.40f, 3f, 1.30f),
        };

        public VanTierZeroProfile TierZero = VanTierZeroProfile.Default;
        public VanEngineTier[] ProgressionEngine = (VanEngineTier[])DefaultProgressionEngine.Clone();
        public VanBrakesLevel[] ProgressionBrakes = (VanBrakesLevel[])DefaultProgressionBrakes.Clone();
        public VanHandlingLevel[] ProgressionHandling = (VanHandlingLevel[])DefaultProgressionHandling.Clone();

        public static VanTierZeroProfile TierZeroOf(VanUpgradeConfig config) =>
            config != null ? config.TierZero : VanTierZeroProfile.Default;

        public static VanEngineTier ProgressionEngineAt(VanUpgradeConfig config, int tier) =>
            PickTier(config != null ? config.ProgressionEngine : null, DefaultProgressionEngine, tier);

        public static VanBrakesLevel ProgressionBrakesAt(VanUpgradeConfig config, int tier) =>
            PickTier(config != null ? config.ProgressionBrakes : null, DefaultProgressionBrakes, tier);

        public static VanHandlingLevel ProgressionHandlingAt(VanUpgradeConfig config, int tier) =>
            PickTier(config != null ? config.ProgressionHandling : null, DefaultProgressionHandling, tier);

        private static T PickTier<T>(T[] tiers, T[] defaults, int tier)
        {
            int i = Mathf.Clamp(tier, 0, defaults.Length - 1);
            return tiers != null && i < tiers.Length ? tiers[i] : defaults[i];
        }

        /// <summary>What a progression tier of a branch changes, for the workshop prompt ("макс. 85 км/ч, тяга ×1,12").</summary>
        public static string DescribeProgression(VanUpgradeConfig config, VanUpgradeCategory category, int tier)
        {
            var ru = System.Globalization.CultureInfo.GetCultureInfo("ru-RU");
            switch (category)
            {
                case VanUpgradeCategory.Engine:
                    VanEngineTier e = ProgressionEngineAt(config, tier);
                    return string.Format(ru, "макс. {0:0} км/ч, тяга ×{1:0.00}", e.TopSpeedKmh, e.TorqueMultiplier);
                case VanUpgradeCategory.Brakes:
                    VanBrakesLevel b = ProgressionBrakesAt(config, tier);
                    return string.Format(ru, "тормоза ×{0:0.00}, ручник ×{1:0.00}, сцепление ×{2:0.00}",
                        b.BrakeTorqueMultiplier, b.HandbrakeTorqueMultiplier, b.ForwardGripMultiplier);
                default:
                    VanHandlingLevel h = ProgressionHandlingAt(config, tier);
                    return string.Format(ru, "боковое сцепление ×{0:0.00}, стабилизатор ×{1:0.00}, руль ×{2:0.00}, +{3:0}° на скорости",
                        h.SidewaysGripMultiplier, h.AntiRollMultiplier, h.SteerSpeedMultiplier, h.HighSpeedSteerBonus);
            }
        }

        // ---------- legacy / debug levels (StartAtMax, debug keys 7/8/9) ----------

        private static readonly VanEngineLevel[] DefaultEngine =
        {
            new(1.12f, 10f, 2f),
            new(1.25f, 20f, 4f),
            new(1.60f, 42f, 8f),                 // max (the van starts here): ~147 km/h, Vadim 2026-10-16
        };

        private static readonly VanBrakesLevel[] DefaultBrakes =
        {
            new(1.15f, 1.10f, 1.08f),
            new(1.30f, 1.20f, 1.16f),
            new(1.60f, 1.35f, 1.32f),
        };

        private static readonly VanHandlingLevel[] DefaultHandling =
        {
            new(1.08f, 1.15f, 1f, 1.10f),
            new(1.16f, 1.30f, 2f, 1.20f),
            new(1.38f, 1.70f, 5f, 1.50f),        // max: more grip, steadier, quicker steering
        };

        public VanEngineLevel[] Engine = (VanEngineLevel[])DefaultEngine.Clone();
        public VanBrakesLevel[] Brakes = (VanBrakesLevel[])DefaultBrakes.Clone();
        public VanHandlingLevel[] Handling = (VanHandlingLevel[])DefaultHandling.Clone();

        // config may be null: the built-in defaults are used then.
        public static VanEngineLevel EngineAt(VanUpgradeConfig config, int level) =>
            level <= 0 ? VanEngineLevel.Stock : Pick(config != null ? config.Engine : null, DefaultEngine, level);

        public static VanBrakesLevel BrakesAt(VanUpgradeConfig config, int level) =>
            level <= 0 ? VanBrakesLevel.Stock : Pick(config != null ? config.Brakes : null, DefaultBrakes, level);

        public static VanHandlingLevel HandlingAt(VanUpgradeConfig config, int level) =>
            level <= 0 ? VanHandlingLevel.Stock : Pick(config != null ? config.Handling : null, DefaultHandling, level);

        private static T Pick<T>(T[] levels, T[] defaults, int level)
        {
            int i = Mathf.Min(level, defaults.Length) - 1;
            return levels != null && i < levels.Length ? levels[i] : defaults[i];
        }

        private void OnValidate()
        {
            Engine = Fit(Engine, DefaultEngine);
            Brakes = Fit(Brakes, DefaultBrakes);
            Handling = Fit(Handling, DefaultHandling);
            ProgressionEngine = Fit(ProgressionEngine, DefaultProgressionEngine);
            ProgressionBrakes = Fit(ProgressionBrakes, DefaultProgressionBrakes);
            ProgressionHandling = Fit(ProgressionHandling, DefaultProgressionHandling);
        }

        // Keeps exactly MaxLevel entries; missing ones are filled from the defaults.
        private static T[] Fit<T>(T[] levels, T[] defaults)
        {
            if (levels != null && levels.Length == defaults.Length) return levels;
            var fitted = (T[])defaults.Clone();
            if (levels != null) Array.Copy(levels, fitted, Mathf.Min(levels.Length, fitted.Length));
            return fitted;
        }
    }
}
