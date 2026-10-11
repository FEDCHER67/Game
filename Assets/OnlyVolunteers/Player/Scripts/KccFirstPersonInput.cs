using KinematicCharacterController.Examples;
using UnityEngine;

namespace OnlyVolunteers.Player
{
    // FPS input and game-specific speed selection; the official example owns movement and stance.
    public sealed class KccFirstPersonInput : MonoBehaviour
    {
        public ExampleCharacterController Character;
        public Camera ViewCamera;

        // OV stage1: set by other systems, never by this script. JumpBlocked: no jump (e.g. riding in the van's cargo bay).
        // ExternalSpeedScale multiplies the grounded target speed (e.g. dragging a heavy body); at 1 it changes nothing.
        [System.NonSerialized] public bool JumpBlocked;
        [System.NonSerialized] public float ExternalSpeedScale = 1f;

        private const float WalkSpeed = 4.7025f;
        private const float SprintSpeed = 8.229375f;
        private const float CrouchSpeed = 1.881f;
        private const float StoopSpeed = 2.5f; // OV stage1: stooped in the cargo bay, no sprint
        private const float DiagonalSpeedMultiplier = 1.05f;
        private const float MouseSensitivity = 1.3f;
        private const float PitchLimit = 85f;
        private const float EyeInset = 0.15f;
        private const float CrouchCameraTransitionTime = 0.125f;
        private const float CrouchJumpResolveTime = 0.08f;
        private const float JumpPostGroundingGraceTime = 0.077f;
        private const float BhopPreGroundGrace = 0.09f;
        private const float BhopCapGrowth = 1.035f;
        private const float BhopMaxSpeed = 11.1625f;
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
        private float _stoopedEyeHeight; // OV stage1
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
        private bool _lookSuspended;

        // While the phone is out the player stands still (no walking or jumping).
        public bool MovementLocked { get; set; }

        // A screen UI (the phone) needs a free cursor instead of mouse look.
        public bool LookSuspended
        {
            get => _lookSuspended;
            set
            {
                if (_lookSuspended == value)
                    return;
                _lookSuspended = value;
                if (!isActiveAndEnabled)
                    return;
                if (value)
                    ReleaseCursor();
                else
                    LockCursor();
            }
        }

        private void Awake()
        {
            _yaw = Character.transform.eulerAngles.y;
            var capsule = Character.Motor.Capsule;
            _standingCapsuleTop = capsule.center.y + capsule.height * 0.5f;
            _standingEyeHeight = _standingCapsuleTop - EyeInset;
            _crouchedEyeHeight = Character.CrouchedCapsuleHeight - EyeInset;
            _stoopedEyeHeight = Character.StoopedCapsuleHeight - EyeInset; // OV stage1: 1.35 - 0.15 = 1.20
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
            Character.AirAccelerationSpeed = 31.03f;
            Character.JumpScalableForwardSpeed = 0f;
            Character.JumpPreGroundingGraceTime = BhopPreGroundGrace;
            Character.JumpPostGroundingGraceTime = 0f;
        }

        private void OnEnable()
        {
            if (_lookSuspended)
                ReleaseCursor();
            else
                LockCursor();
        }

        private void OnDisable()
        {
            ReleaseCursor();
        }

        private void OnApplicationFocus(bool focused)
        {
            if (focused && isActiveAndEnabled && !_lookSuspended)
                LockCursor();
        }

        private static void ReleaseCursor()
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }

        private static void LockCursor()
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }

        private void Update()
        {
            if (Input.GetMouseButtonDown(0) && !_lookSuspended)
                LockCursor();

            float yawDelta = 0f;
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                yawDelta = Input.GetAxisRaw("Mouse X") * MouseSensitivity;
                _yaw = Mathf.Repeat(_yaw + yawDelta, 360f);
                _pitch = Mathf.Clamp(_pitch - Input.GetAxisRaw("Mouse Y") * MouseSensitivity,
                    -PitchLimit, PitchLimit);
            }

            float moveForward = MovementLocked ? 0f : Input.GetAxisRaw("Vertical");
            float moveRight = MovementLocked ? 0f : Input.GetAxisRaw("Horizontal");
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
            // OV stage1: no jump while stooped (low roof) or while another system blocks it (cargo bay).
            bool stooped = !crouched && Character.IsStooped;
            bool jumpDown = !crouched && !stooped && !JumpBlocked && !MovementLocked && Input.GetKeyDown(KeyCode.Space);
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
                    : stooped // OV stage1
                        ? StoopSpeed
                        : Input.GetKey(KeyCode.LeftShift) && hasMovementInput
                            ? SprintSpeed
                            : WalkSpeed;
                float targetSpeed = groundedSpeed *
                    (diagonalInput ? DiagonalSpeedMultiplier : 1f) *
                    ExternalSpeedScale; // OV stage1: 1 unless something (a held body) slows the player down

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

            // OV stage1: three eye levels (crouched 0.85, stooped 1.20, standing 1.85).
            float targetEyeHeight = _visualCrouched ? _crouchedEyeHeight
                : Character.IsStooped ? _stoopedEyeHeight : _standingEyeHeight;
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

        // OV stage1: called by a carrier (the van's cargo bay, GreyboxCargoRider) when it lets go of the player. The motor
        // adds the carrier's velocity on its next tick (PreserveAttachedRigidbodyMomentum); widen the air speed cap to
        // that planar speed so LateUpdate does not clip a jump out of a moving van back to walking speed. While grounded
        // it changes nothing (the cap is recomputed on leaving the ground). Long jumps still cap air speed at BhopMaxSpeed.
        public void AllowAirSpeed(float planarSpeed)
        {
            _airborneSpeedLimit = Mathf.Max(_airborneSpeedLimit, planarSpeed);
        }

        // OV stage1: turns the view with whatever the player rides in (the van's cargo bay), so a passenger keeps facing
        // the same way relative to a turning van. Called per frame by the carrier code; unused otherwise.
        public void AddYaw(float degrees)
        {
            _yaw = Mathf.Repeat(_yaw + degrees, 360f);
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
