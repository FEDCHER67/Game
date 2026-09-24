using KinematicCharacterController.Examples;
using UnityEngine;

namespace OnlyVolunteers.Player
{
    // FPS input and game-specific speed selection; the official example owns movement and stance.
    public sealed class KccFirstPersonInput : MonoBehaviour
    {
        public ExampleCharacterController Character;
        public Camera ViewCamera;

        private const float WalkSpeed = 4.95f;
        private const float SprintSpeed = 8.6625f;
        private const float CrouchSpeed = 1.98f;
        private const float DiagonalSpeedMultiplier = 1.05f;
        private const float MouseSensitivity = 1.3f;
        private const float PitchLimit = 85f;
        private const float EyeInset = 0.15f;
        private const float CrouchCameraTransitionTime = 0.125f;
        private const float CrouchJumpResolveTime = 0.08f;
        private const float JumpPostGroundingGraceTime = 0.077f;
        private const float BhopPreGroundGrace = 0.09f;
        private const float BhopCapGrowth = 1.035f;
        private const float BhopMaxSpeed = 11.75f;
        private const float LongJumpMaxGain = 1.10f;
        private const float LongJumpMinArcDegrees = 8f;
        private const float LongJumpIdealArcMinDegrees = 12f;
        private const float LongJumpIdealArcMaxDegrees = 22f;
        private const float LongJumpMaxArcDegrees = 35f;
        private const float LongJumpReversalDegrees = 2f;
        private const int LongJumpIdealArcCount = 4;
        private const float AirTuckDistance = 0.35f;
        private const float AirTuckPathStep = 0.05f;

        private readonly Collider[] _airTuckOverlaps = new Collider[8];
        private readonly RaycastHit[] _airTuckHits = new RaycastHit[8];
        private float _yaw;
        private float _pitch;
        private float _standingCapsuleTop;
        private float _standingEyeHeight;
        private float _crouchedEyeHeight;
        private float _visualEyeHeight;
        private float _eyeTransitionSpeed;
        private float _airTuckCameraOffset;
        private float _airTuckCameraReleaseSpeed;
        private float _airborneSpeedLimit;
        private float _normalAirMoveSpeed;
        private float _bhopCap;
        private float _longJumpReferenceSpeed;
        private float _longJumpArcDegrees;
        private float _longJumpReversalDegrees;
        private float _longJumpQuality;
        private int _longJumpDirection;
        private float _lastAirJumpPressTime = float.NegativeInfinity;
        private float _landingHopTime;
        private float _stableMovementSharpness;
        private float _crouchJumpStableTime;
        private bool _visualCrouched;
        private bool _hadMovementInput;
        private bool _wasStableGrounded;
        private bool _airborneCrouchLatched;
        private bool _airborneEligibleForCrouchJump;
        private bool _canChainBhop;
        private bool _bhopChainActive;
        private bool _preserveLandingMomentum;

        private void Awake()
        {
            _yaw = Character.transform.eulerAngles.y;
            var capsule = Character.Motor.Capsule;
            _standingCapsuleTop = capsule.center.y + capsule.height * 0.5f;
            _standingEyeHeight = _standingCapsuleTop - EyeInset;
            _crouchedEyeHeight = Character.CrouchedCapsuleHeight - EyeInset;
            _visualCrouched = IsPhysicallyCrouched();
            _visualEyeHeight = _visualCrouched ? _crouchedEyeHeight : _standingEyeHeight;
            _eyeTransitionSpeed = Mathf.Abs(_standingEyeHeight - _crouchedEyeHeight) /
                CrouchCameraTransitionTime;
            _wasStableGrounded = Character.Motor.GroundingStatus.IsStableOnGround;
            Character.Motor.MaxVelocityForLedgeSnap = 12f;
            Character.Motor.UseFlatBaseForGroundChecks = true;
            Character.MaxStableMoveSpeed = WalkSpeed;
            Character.MaxAirMoveSpeed = WalkSpeed;
            _airborneSpeedLimit = WalkSpeed;
            _normalAirMoveSpeed = WalkSpeed;
            _stableMovementSharpness = Character.StableMovementSharpness;
            Character.AirAccelerationSpeed = 29f;
            Character.JumpScalableForwardSpeed = 0f;
            Character.JumpPreGroundingGraceTime = BhopPreGroundGrace;
            Character.JumpPostGroundingGraceTime = 0f;
        }

        private void OnEnable()
        {
            LockCursor();
        }

        private void OnDisable()
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }

        private void OnApplicationFocus(bool focused)
        {
            if (focused && isActiveAndEnabled)
                LockCursor();
        }

        private static void LockCursor()
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }

        private void Update()
        {
            if (Input.GetMouseButtonDown(0))
                LockCursor();

            float yawDelta = 0f;
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                yawDelta = Input.GetAxisRaw("Mouse X") * MouseSensitivity;
                _yaw = Mathf.Repeat(_yaw + yawDelta, 360f);
                _pitch = Mathf.Clamp(_pitch - Input.GetAxisRaw("Mouse Y") * MouseSensitivity,
                    -PitchLimit, PitchLimit);
            }

            float moveForward = Input.GetAxisRaw("Vertical");
            float moveRight = Input.GetAxisRaw("Horizontal");
            bool hasMovementInput = moveForward != 0f || moveRight != 0f;
            bool diagonalInput = moveForward != 0f && moveRight != 0f;
            bool crouchHeld = Input.GetKey(KeyCode.LeftControl);
            bool physicallyCrouched = IsPhysicallyCrouched();
            bool grounded = Character.Motor.GroundingStatus.IsStableOnGround;
            if (grounded && Character.JumpPostGroundingGraceTime == 0f)
                Character.JumpPostGroundingGraceTime = JumpPostGroundingGraceTime;

            if (_wasStableGrounded && !grounded)
            {
                _airborneEligibleForCrouchJump = !physicallyCrouched;
                _airborneSpeedLimit = Mathf.Max(Character.MaxAirMoveSpeed,
                    Vector3.ProjectOnPlane(Character.Motor.BaseVelocity,
                        Character.Motor.CharacterUp).magnitude);
                _longJumpReferenceSpeed = Mathf.Min(BhopMaxSpeed, _airborneSpeedLimit);
            }

            bool beginAirTuck = !grounded && crouchHeld &&
                _airborneEligibleForCrouchJump && !physicallyCrouched;
            if (beginAirTuck)
            {
                _airborneEligibleForCrouchJump = false;
                _airborneCrouchLatched = true;
                _crouchJumpStableTime = 0f;
            }

            if (_airborneCrouchLatched)
            {
                if (grounded)
                    _crouchJumpStableTime += Time.deltaTime;
                else
                    _crouchJumpStableTime = 0f;

                if (!crouchHeld && grounded &&
                    _crouchJumpStableTime >= CrouchJumpResolveTime)
                {
                    _airborneCrouchLatched = false;
                    _airborneEligibleForCrouchJump = false;
                }
            }

            bool effectiveCrouchHeld = crouchHeld || _airborneCrouchLatched;
            bool crouched = effectiveCrouchHeld || physicallyCrouched;
            bool jumpDown = !crouched && Input.GetKeyDown(KeyCode.Space);
            if (crouched || (!_wasStableGrounded && grounded) || (jumpDown && grounded))
                ResetLongJump();
            if (jumpDown && !grounded)
                _lastAirJumpPressTime = Time.time;

            // This timestamp tracks the KCC request; the example owns the jump buffer.
            bool timedAirPress = Time.time - _lastAirJumpPressTime <=
                BhopPreGroundGrace;
            bool landingHop = _canChainBhop && !crouched &&
                !_wasStableGrounded && grounded && (jumpDown || timedAirPress);
            if (landingHop)
            {
                float planarSpeed = Vector3.ProjectOnPlane(Character.Motor.BaseVelocity,
                    Character.Motor.CharacterUp).magnitude;
                _bhopCap = Mathf.Min(BhopMaxSpeed,
                    Mathf.Max(_bhopCap, planarSpeed) * BhopCapGrowth);
                _bhopChainActive = true;
                _preserveLandingMomentum = grounded;
                _landingHopTime = Time.time;
                _lastAirJumpPressTime = float.NegativeInfinity;
            }
            else if (crouched || (grounded &&
                ((!_wasStableGrounded && !timedAirPress) ||
                 (_preserveLandingMomentum &&
                  Time.time - _landingHopTime > BhopPreGroundGrace))))
            {
                ResetLongJump();
                _canChainBhop = false;
                _bhopChainActive = false;
                _preserveLandingMomentum = false;
                _bhopCap = 0f;
                Character.MaxAirMoveSpeed = _normalAirMoveSpeed;
                if (!grounded)
                    _airborneSpeedLimit = Mathf.Max(_normalAirMoveSpeed,
                        Vector3.ProjectOnPlane(Character.Motor.BaseVelocity,
                            Character.Motor.CharacterUp).magnitude);
            }
            if (_preserveLandingMomentum && !grounded)
                _preserveLandingMomentum = false;
            Character.StableMovementSharpness = _preserveLandingMomentum ||
                (_canChainBhop && !crouched && timedAirPress)
                ? 0f : _stableMovementSharpness;

            if (effectiveCrouchHeld)
                _visualCrouched = true;
            else if (!physicallyCrouched)
                _visualCrouched = false;

            if (!_wasStableGrounded && grounded && crouched)
                NormalizeCrouchedLandingVelocity();
            bool preserveTakeoffMomentum = jumpDown || landingHop ||
                _bhopChainActive || _preserveLandingMomentum ||
                (_canChainBhop && !crouched && timedAirPress);
            if (_hadMovementInput && !hasMovementInput && grounded &&
                !preserveTakeoffMomentum)
            {
                Vector3 up = Character.Motor.CharacterUp;
                Character.Motor.BaseVelocity = Vector3.Project(
                    Character.Motor.BaseVelocity, up);
            }
            _hadMovementInput = hasMovementInput;
            _wasStableGrounded = grounded;

            if (grounded)
            {
                float groundedSpeed = crouched
                    ? CrouchSpeed
                    : Input.GetKey(KeyCode.LeftShift) && hasMovementInput
                        ? SprintSpeed
                        : WalkSpeed;
                float targetSpeed = groundedSpeed *
                    (diagonalInput ? DiagonalSpeedMultiplier : 1f);

                Character.MaxStableMoveSpeed = targetSpeed;
                if (!_bhopChainActive)
                {
                    Character.MaxAirMoveSpeed = targetSpeed;
                    _normalAirMoveSpeed = targetSpeed;
                }
            }

            if (jumpDown && grounded && !landingHop)
                _canChainBhop = true;
            if (_bhopChainActive)
            {
                Character.MaxAirMoveSpeed = _bhopCap;
                _airborneSpeedLimit = _bhopCap;
            }
            if (!grounded && !crouched && moveForward > 0.5f)
                ScoreLongJumpArc(yawDelta);
            else if (!grounded)
            {
                _longJumpArcDegrees = 0f;
                _longJumpReversalDegrees = 0f;
                _longJumpDirection = 0;
            }
            if (!grounded && !crouched && _longJumpReferenceSpeed > 0f)
            {
                float mouseCap = Mathf.Min(BhopMaxSpeed, _longJumpReferenceSpeed *
                    Mathf.Lerp(1f, LongJumpMaxGain, _longJumpQuality / LongJumpIdealArcCount));
                Character.MaxAirMoveSpeed = Mathf.Min(BhopMaxSpeed,
                    Mathf.Max(Character.MaxAirMoveSpeed, mouseCap));
                _airborneSpeedLimit = Mathf.Min(BhopMaxSpeed,
                    Mathf.Max(_airborneSpeedLimit, mouseCap));
            }

            var inputs = new PlayerCharacterInputs
            {
                MoveAxisForward = moveForward,
                MoveAxisRight = moveRight,
                CameraRotation = Quaternion.Euler(0f, _yaw, 0f),
                JumpDown = jumpDown,
                CrouchDown = effectiveCrouchHeld,
                CrouchUp = !effectiveCrouchHeld
            };
            Character.SetInputs(ref inputs);

            if (beginAirTuck)
                TryAirTuck();
        }

        private void ResetLongJump()
        {
            _longJumpReferenceSpeed = 0f;
            _longJumpArcDegrees = 0f;
            _longJumpReversalDegrees = 0f;
            _longJumpQuality = 0f;
            _longJumpDirection = 0;
        }

        private void ScoreLongJumpArc(float yawDelta)
        {
            if (yawDelta == 0f)
                return;

            int direction = yawDelta > 0f ? 1 : -1;
            float degrees = Mathf.Abs(yawDelta);
            if (_longJumpDirection == 0)
                _longJumpDirection = direction;
            if (direction == _longJumpDirection)
            {
                _longJumpReversalDegrees = 0f;
                _longJumpArcDegrees += degrees;
                return;
            }

            _longJumpReversalDegrees += degrees;
            if (_longJumpReversalDegrees < LongJumpReversalDegrees)
                return;

            float arc = _longJumpArcDegrees;
            float quality = arc < LongJumpMinArcDegrees ? 0f
                : arc < LongJumpIdealArcMinDegrees
                    ? (arc - LongJumpMinArcDegrees) /
                      (LongJumpIdealArcMinDegrees - LongJumpMinArcDegrees)
                    : arc <= LongJumpIdealArcMaxDegrees ? 1f
                    : Mathf.Clamp01((LongJumpMaxArcDegrees - arc) /
                      (LongJumpMaxArcDegrees - LongJumpIdealArcMaxDegrees));
            _longJumpQuality = Mathf.Min(LongJumpIdealArcCount,
                _longJumpQuality + quality);
            _longJumpArcDegrees = _longJumpReversalDegrees;
            _longJumpReversalDegrees = 0f;
            _longJumpDirection = direction;
        }

        private void TryAirTuck()
        {
            // The example has already shrunk the capsule around its feet.
            var motor = Character.Motor;
            var capsule = motor.Capsule;
            float tuckDistance = AirTuckDistance;
            if (tuckDistance <= 0f)
                return;

            Vector3 start = motor.TransientPosition;
            Vector3 up = motor.CharacterUp;
            if (motor.CharacterCollisionsSweep(start, motor.TransientRotation, up,
                tuckDistance, out _, _airTuckHits) > 0)
                return;

            // Check the occupied volume along the path, including the destination.
            int steps = Mathf.CeilToInt(tuckDistance / AirTuckPathStep);
            for (int step = 1; step <= steps; step++)
            {
                Vector3 position = start + up * (tuckDistance * step / steps);
                if (motor.CharacterCollisionsOverlap(position, motor.TransientRotation,
                    _airTuckOverlaps) != 0)
                    return;
            }

            Vector3 tuckedPosition = start + up * tuckDistance;
            motor.SetPosition(tuckedPosition);
            _airTuckCameraOffset = -tuckDistance;
            _airTuckCameraReleaseSpeed = tuckDistance / CrouchCameraTransitionTime;
        }

        private void LateUpdate()
        {
            bool grounded = Character.Motor.GroundingStatus.IsStableOnGround;
            Vector3 characterUp = Character.Motor.CharacterUp;
            if (!grounded)
            {
                Vector3 verticalVelocity = Vector3.Project(Character.Motor.BaseVelocity,
                    characterUp);
                Vector3 planarVelocity = Character.Motor.BaseVelocity - verticalVelocity;
                if (planarVelocity.sqrMagnitude >
                    _airborneSpeedLimit * _airborneSpeedLimit)
                    Character.Motor.BaseVelocity = planarVelocity.normalized *
                        _airborneSpeedLimit + verticalVelocity;
            }

            float targetEyeHeight = _visualCrouched ? _crouchedEyeHeight : _standingEyeHeight;
            _visualEyeHeight = Mathf.MoveTowards(_visualEyeHeight, targetEyeHeight,
                _eyeTransitionSpeed * Time.deltaTime);

            Vector3 eye = Character.Motor.Capsule.center;
            eye.y = _visualEyeHeight;
            eye.y += _airTuckCameraOffset;
            _airTuckCameraOffset = Mathf.MoveTowards(_airTuckCameraOffset, 0f,
                Time.deltaTime * _airTuckCameraReleaseSpeed);

            ViewCamera.transform.SetPositionAndRotation(
                Character.transform.TransformPoint(eye),
                Quaternion.Euler(_pitch, _yaw, 0f));
        }

        private bool IsPhysicallyCrouched()
        {
            return Character.Motor.Capsule.height <= Character.CrouchedCapsuleHeight + 0.01f;
        }

        private void NormalizeCrouchedLandingVelocity()
        {
            Vector3 characterUp = Character.Motor.CharacterUp;
            Vector3 verticalVelocity = Vector3.Project(Character.Motor.BaseVelocity, characterUp);
            Vector3 planarVelocity = Character.Motor.BaseVelocity - verticalVelocity;
            if (planarVelocity.sqrMagnitude > CrouchSpeed * CrouchSpeed)
                Character.Motor.BaseVelocity = planarVelocity.normalized * CrouchSpeed +
                    verticalVelocity;
        }
    }
}
