using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Auto-shop upgrades of the van: Engine, Brakes and Handling, levels 0..MaxLevel.
    // Level 0 is the stock tuning read from VanController and its wheel colliders on first use.
    // Values are pushed only when a level changes. Not networked: a network layer just calls TrySetLevel.
    //
    // Two profiles (ECONOMY spec v01 §6.1, §6.3, §10.3.5):
    // - Progression (the team economy drives it: TeamEconomy calls ApplyProgressionTiers with the PAID tiers from the team
    //   save): tier 0 is the new comfortable-but-weaker profile (VanUpgradeConfig.TierZero, top speed 70 km/h), tiers
    //   I..III multiply it (top speed 85/100/115). StartAtMax is ignored. Debug keys 7/8/9 (TrySetLevel) only preview a
    //   tier in editor / development builds: nothing is paid, nothing is saved; the next paid tier change or load puts
    //   the paid tiers back.
    // - Legacy / debug (no economy in the scene, or an old StartAtMax slot): the old levels exactly as before (StartAtMax,
    //   max ~147 km/h). Old StartAtMax is never converted into paid tiers.
    [DisallowMultipleComponent]
    [RequireComponent(typeof(VanController))]
    public sealed class VanUpgrades : MonoBehaviour
    {
        public const int MaxLevel = 3;
        private const int CategoryCount = 3;

        [Tooltip("Optional. Without it the built-in default levels are used.")]
        public VanUpgradeConfig Config;

        // Vadim 2026-10-16 (TASK-000684): the van is always fully tuned from the very start (engine, brakes and
        // handling at MaxLevel); a save or the debug keys cannot lower it while this is on.
        // ECONOMY spec v01 (Fedya 2026-10-28 brief): a DEBUG / legacy option only now. Ignored (off) while the team economy
        // runs the paid progression (ProgressionActive); scenes without the economy keep the old behaviour.
        [Tooltip("DEBUG / legacy: start with every category at MaxLevel and never go below it. Ignored in the paid progression (team economy).")]
        public bool StartAtMax = true;

        // (category, new level), raised after the new values are applied.
        public event Action<VanUpgradeCategory, int> LevelChanged;

        private readonly int[] _levels = new int[CategoryCount];
        private VanController _van;
        private WheelCollider[] _wheels;
        private bool _captured;

        private float _motorTorque;
        private float _maxSpeedKmh;
        private float _reverseSpeedKmh;
        private float _brakeTorque;
        private float _handbrakeTorque;
        private float _antiRoll;
        private float _highSpeedSteerAngle;
        private float _steerSpeed;
        private float[] _forwardExtremum;
        private float[] _forwardAsymptote;
        private float[] _sideExtremum;
        private float[] _sideAsymptote;

        /// <summary>True while the team economy's paid tiers drive the van (StartAtMax is then off).</summary>
        public bool ProgressionActive { get; private set; }
        /// <summary>A debug key previewed another tier than the paid one (not paid, not saved).</summary>
        public bool DebugOverride { get; private set; }

        private void Awake() => CaptureStock();

        private void Start()
        {
            if (!StartAtMax || ProgressionActive) return;
            for (int c = 0; c < CategoryCount; c++) TrySetLevel((VanUpgradeCategory)c, MaxLevel);
        }

        public int GetLevel(VanUpgradeCategory category) => IsValid(category) ? _levels[(int)category] : 0;

        // False for an unknown category or a level outside 0..MaxLevel. Setting the current level is a no-op.
        // Progression: a debug preview only (editor / development builds), see the class comment.
        public bool TrySetLevel(VanUpgradeCategory category, int level)
        {
            if (!IsValid(category) || level < 0 || level > MaxLevel) return false;
            if (ProgressionActive)
            {
                if (!Debug.isDebugBuild) return false;
                if (_levels[(int)category] == level) return true;
                _levels[(int)category] = level;
                ApplyProgression(category, level);
                DebugOverride = true;
                Debug.Log($"[VAN] debug preview {category} tier {level} (not paid, not saved; the paid tiers return on the next paid change or load)", this);
                LevelChanged?.Invoke(category, level);
                return true;
            }
            if (StartAtMax) level = MaxLevel;
            if (_levels[(int)category] == level) return true;
            CaptureStock();
            _levels[(int)category] = level;
            Apply(category, level);
            LevelChanged?.Invoke(category, level);
            return true;
        }

        /// <summary>Team economy (server and clients): the paid tiers 0..III of each branch. Every value is recomputed from
        /// the captured stock, so applying the same tiers again (a reload, a snapshot) never stacks anything.</summary>
        public void ApplyProgressionTiers(int engine, int handling, int brakes)
        {
            CaptureStock();
            ProgressionActive = true;
            DebugOverride = false;
            SetProgression(VanUpgradeCategory.Engine, engine);
            SetProgression(VanUpgradeCategory.Brakes, brakes);
            SetProgression(VanUpgradeCategory.Handling, handling);
        }

        /// <summary>Team economy, old StartAtMax slot (§10.3.5): the legacy / debug profile at its old maximum.</summary>
        public void UseLegacyDebugProfile()
        {
            CaptureStock();
            ProgressionActive = false;
            DebugOverride = false;
            for (int c = 0; c < CategoryCount; c++)
            {
                bool changed = _levels[c] != MaxLevel;
                _levels[c] = MaxLevel;
                Apply((VanUpgradeCategory)c, MaxLevel);
                if (changed) LevelChanged?.Invoke((VanUpgradeCategory)c, MaxLevel);
            }
        }

        private void SetProgression(VanUpgradeCategory category, int tier)
        {
            tier = Mathf.Clamp(tier, 0, MaxLevel);
            bool changed = _levels[(int)category] != tier;
            _levels[(int)category] = tier;
            ApplyProgression(category, tier);
            if (changed) LevelChanged?.Invoke(category, tier);
        }

        private static bool IsValid(VanUpgradeCategory category) => (uint)category < CategoryCount;

        private void CaptureStock()
        {
            if (_captured) return;
            _captured = true;
            _van = GetComponent<VanController>();
            _motorTorque = _van.MotorTorque;
            _maxSpeedKmh = _van.MaxSpeedKmh;
            _reverseSpeedKmh = _van.ReverseSpeedKmh;
            _brakeTorque = _van.BrakeTorque;
            _handbrakeTorque = _van.HandbrakeTorque;
            _antiRoll = _van.AntiRoll;
            _highSpeedSteerAngle = _van.HighSpeedSteerAngle;
            _steerSpeed = _van.SteerSpeed;

            var wheels = new List<WheelCollider>(4);
            foreach (WheelCollider w in new[] { _van.Front.Left, _van.Front.Right, _van.Rear.Left, _van.Rear.Right })
                if (w != null && !wheels.Contains(w)) wheels.Add(w);
            _wheels = wheels.ToArray();
            _forwardExtremum = new float[_wheels.Length];
            _forwardAsymptote = new float[_wheels.Length];
            _sideExtremum = new float[_wheels.Length];
            _sideAsymptote = new float[_wheels.Length];
            for (int i = 0; i < _wheels.Length; i++)
            {
                WheelFrictionCurve forward = _wheels[i].forwardFriction;
                _forwardExtremum[i] = forward.extremumValue;
                _forwardAsymptote[i] = forward.asymptoteValue;
                WheelFrictionCurve side = _wheels[i].sidewaysFriction;
                _sideExtremum[i] = side.extremumValue;
                _sideAsymptote[i] = side.asymptoteValue;
            }
        }

        // Progression: the same fields as Apply below, from the stock x the tier-0 profile x the tier's multipliers.
        private void ApplyProgression(VanUpgradeCategory category, int tier)
        {
            VanTierZeroProfile zero = VanUpgradeConfig.TierZeroOf(Config);
            switch (category)
            {
                case VanUpgradeCategory.Engine:
                    VanEngineTier engine = VanUpgradeConfig.ProgressionEngineAt(Config, tier);
                    _van.MotorTorque = _motorTorque * zero.TorqueScale * engine.TorqueMultiplier;
                    _van.MaxSpeedKmh = engine.TopSpeedKmh;
                    _van.ReverseSpeedKmh = _reverseSpeedKmh;
                    break;

                case VanUpgradeCategory.Brakes:
                    VanBrakesLevel brakes = VanUpgradeConfig.ProgressionBrakesAt(Config, tier);
                    _van.BrakeTorque = _brakeTorque * zero.BrakeTorqueScale * brakes.BrakeTorqueMultiplier;
                    _van.HandbrakeTorque = _handbrakeTorque * zero.HandbrakeTorqueScale * brakes.HandbrakeTorqueMultiplier;
                    for (int i = 0; i < _wheels.Length; i++)
                    {
                        WheelFrictionCurve forward = _wheels[i].forwardFriction;
                        float k = zero.ForwardGripScale * brakes.ForwardGripMultiplier;
                        forward.extremumValue = _forwardExtremum[i] * k;
                        forward.asymptoteValue = _forwardAsymptote[i] * k;
                        _wheels[i].forwardFriction = forward;
                    }
                    break;

                case VanUpgradeCategory.Handling:
                    VanHandlingLevel handling = VanUpgradeConfig.ProgressionHandlingAt(Config, tier);
                    _van.AntiRoll = _antiRoll * zero.AntiRollScale * handling.AntiRollMultiplier;
                    _van.HighSpeedSteerAngle = Mathf.Min(_highSpeedSteerAngle + zero.HighSpeedSteerOffset + handling.HighSpeedSteerBonus,
                        Mathf.Max(_van.MaxSteerAngle, _highSpeedSteerAngle));
                    _van.SteerSpeed = _steerSpeed * zero.SteerSpeedScale * handling.SteerSpeedMultiplier;
                    for (int i = 0; i < _wheels.Length; i++)
                    {
                        WheelFrictionCurve side = _wheels[i].sidewaysFriction;
                        float k = zero.SidewaysGripScale * handling.SidewaysGripMultiplier;
                        side.extremumValue = _sideExtremum[i] * k;
                        side.asymptoteValue = _sideAsymptote[i] * k;
                        _wheels[i].sidewaysFriction = side;
                    }
                    break;
            }
        }

        private void Apply(VanUpgradeCategory category, int level)
        {
            switch (category)
            {
                case VanUpgradeCategory.Engine:
                    VanEngineLevel engine = VanUpgradeConfig.EngineAt(Config, level);
                    _van.MotorTorque = _motorTorque * engine.TorqueMultiplier;
                    _van.MaxSpeedKmh = _maxSpeedKmh + engine.MaxSpeedBonusKmh;
                    _van.ReverseSpeedKmh = _reverseSpeedKmh + engine.ReverseSpeedBonusKmh;
                    break;

                case VanUpgradeCategory.Brakes:
                    VanBrakesLevel brakes = VanUpgradeConfig.BrakesAt(Config, level);
                    _van.BrakeTorque = _brakeTorque * brakes.BrakeTorqueMultiplier;
                    _van.HandbrakeTorque = _handbrakeTorque * brakes.HandbrakeTorqueMultiplier;
                    for (int i = 0; i < _wheels.Length; i++)
                    {
                        WheelFrictionCurve forward = _wheels[i].forwardFriction;
                        forward.extremumValue = _forwardExtremum[i] * brakes.ForwardGripMultiplier;
                        forward.asymptoteValue = _forwardAsymptote[i] * brakes.ForwardGripMultiplier;
                        _wheels[i].forwardFriction = forward;
                    }
                    break;

                case VanUpgradeCategory.Handling:
                    VanHandlingLevel handling = VanUpgradeConfig.HandlingAt(Config, level);
                    _van.AntiRoll = _antiRoll * handling.AntiRollMultiplier;
                    _van.HighSpeedSteerAngle = Mathf.Min(_highSpeedSteerAngle + handling.HighSpeedSteerBonus,
                        Mathf.Max(_van.MaxSteerAngle, _highSpeedSteerAngle));
                    _van.SteerSpeed = _steerSpeed * handling.SteerSpeedMultiplier;
                    // VanController owns the rear stiffness (cached in its Awake, rewritten for the handbrake),
                    // so grip is scaled through the curve values, which stiffness multiplies anyway.
                    for (int i = 0; i < _wheels.Length; i++)
                    {
                        WheelFrictionCurve side = _wheels[i].sidewaysFriction;
                        side.extremumValue = _sideExtremum[i] * handling.SidewaysGripMultiplier;
                        side.asymptoteValue = _sideAsymptote[i] * handling.SidewaysGripMultiplier;
                        _wheels[i].sidewaysFriction = side;
                    }
                    break;
            }
        }
    }
}
