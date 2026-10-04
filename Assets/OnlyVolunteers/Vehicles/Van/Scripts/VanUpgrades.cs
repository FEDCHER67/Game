using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Auto-shop upgrades of the van: Engine, Brakes and Handling, levels 0..MaxLevel.
    // Level 0 is the stock tuning read from VanController and its wheel colliders on first use.
    // Values are pushed only when a level changes. Not networked: a network layer just calls TrySetLevel.
    [DisallowMultipleComponent]
    [RequireComponent(typeof(VanController))]
    public sealed class VanUpgrades : MonoBehaviour
    {
        public const int MaxLevel = 3;
        private const int CategoryCount = 3;

        [Tooltip("Optional. Without it the built-in default levels are used.")]
        public VanUpgradeConfig Config;

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

        private void Awake() => CaptureStock();

        public int GetLevel(VanUpgradeCategory category) => IsValid(category) ? _levels[(int)category] : 0;

        // False for an unknown category or a level outside 0..MaxLevel. Setting the current level is a no-op.
        public bool TrySetLevel(VanUpgradeCategory category, int level)
        {
            if (!IsValid(category) || level < 0 || level > MaxLevel) return false;
            if (_levels[(int)category] == level) return true;
            CaptureStock();
            _levels[(int)category] = level;
            Apply(category, level);
            LevelChanged?.Invoke(category, level);
            return true;
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
