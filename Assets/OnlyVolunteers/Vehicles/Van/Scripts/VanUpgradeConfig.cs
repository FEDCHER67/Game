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

    // Upgrade steps relative to the van's stock tuning. Each array holds levels 1..MaxLevel;
    // level 0 is always the stock values captured by VanUpgrades.
    [CreateAssetMenu(fileName = "VanUpgradeConfig", menuName = "OnlyVolunteers/Vehicles/Van Upgrade Config")]
    public sealed class VanUpgradeConfig : ScriptableObject
    {
        private static readonly VanEngineLevel[] DefaultEngine =
        {
            new(1.12f, 10f, 2f),
            new(1.25f, 20f, 4f),
            new(1.40f, 30f, 6f),
        };

        private static readonly VanBrakesLevel[] DefaultBrakes =
        {
            new(1.15f, 1.10f, 1.08f),
            new(1.30f, 1.20f, 1.16f),
            new(1.50f, 1.30f, 1.25f),
        };

        private static readonly VanHandlingLevel[] DefaultHandling =
        {
            new(1.08f, 1.15f, 1f, 1.10f),
            new(1.16f, 1.30f, 2f, 1.20f),
            new(1.25f, 1.50f, 3f, 1.30f),
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
