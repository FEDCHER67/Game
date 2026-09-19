using KinematicCharacterController.Examples;
using UnityEngine;

namespace OnlyVolunteers.Player
{
    // FPS input and game-specific speed selection; the official example owns physical movement and stance.
    public sealed class KccFirstPersonInput : MonoBehaviour
    {
        public ExampleCharacterController Character;
        public Camera ViewCamera;

        private const float WalkSpeed = 4.95f;
        private const float SprintSpeed = 8.6625f;
        private const float CrouchSpeed = 1.98f;
        private const float MouseSensitivity = 1.3f;
        private const float PitchLimit = 85f;
        private const float EyeInset = 0.15f;
        private const float CrouchCameraTransitionTime = 0.125f;
        private const float ContactCompensationWindow = 0.15f;
        private const float MinContactCorrection = 0.0005f;
        private const float MaxContactCompensation = 0.15f;
        private const float CrouchJumpResolveTime = 0.08f;
        private const float LedgeAssistMinHeight = 1.7f;
        private const float LedgeAssistMaxHeight = 2.25f;
        private const float LedgeAssistProbeBack = 0.3f;
        private const float LedgeAssistProbeUp = 0.25f;
        private const float LedgeAssistProbeDistance = 0.5f;
        private const float LedgeAssistMaxVerticalMiss = 0.15f;
        private const float LedgeAssistVelocityReduction = 1f;
        private float _yaw;
        private float _pitch;
        private float _standingEyeHeight;
        private float _crouchedEyeHeight;
        private float _visualEyeHeight;
        private float _eyeTransitionSpeed;
        private float _cameraVerticalCompensation;
        private float _compensationReleaseSpeed;
        private float _contactCompensationWindow;
        private float _lastPhysicalRootY;
        private bool _hasLastPhysicalRootY;
        private bool _visualCrouched;
        private bool _wasStableGrounded;
        private bool _airborneCrouchLatched;
        private bool _airborneEligibleForCrouchJump;
        private bool _crouchJumpActive;
        private bool _ledgeAssistConsumed;
        private float _crouchJumpStableTime;
        private float _crouchJumpStartHeight;
        private readonly RaycastHit[] _ledgeAssistHits = new RaycastHit[4];

        private void Awake()
        {
            _yaw = Character.transform.eulerAngles.y;
            var capsule = Character.Motor.Capsule;
            _standingEyeHeight = capsule.center.y + capsule.height * 0.5f - EyeInset;
            _crouchedEyeHeight = Character.CrouchedCapsuleHeight - EyeInset;
            _visualCrouched = IsPhysicallyCrouched();
            _visualEyeHeight = _visualCrouched ? _crouchedEyeHeight : _standingEyeHeight;
            _eyeTransitionSpeed = Mathf.Abs(_standingEyeHeight - _crouchedEyeHeight) /
                CrouchCameraTransitionTime;
            _wasStableGrounded = Character.Motor.GroundingStatus.IsStableOnGround;
            Character.MaxStableMoveSpeed = WalkSpeed;
            Character.MaxAirMoveSpeed = WalkSpeed;
            Character.JumpScalableForwardSpeed = 0f;
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

            if (Cursor.lockState == CursorLockMode.Locked)
            {
                _yaw = Mathf.Repeat(_yaw + Input.GetAxisRaw("Mouse X") * MouseSensitivity, 360f);
                _pitch = Mathf.Clamp(_pitch - Input.GetAxisRaw("Mouse Y") * MouseSensitivity,
                    -PitchLimit, PitchLimit);
            }

            float moveForward = Input.GetAxisRaw("Vertical");
            float moveRight = Input.GetAxisRaw("Horizontal");
            bool hasMovementInput = moveForward != 0f || moveRight != 0f;
            bool crouchHeld = Input.GetKey(KeyCode.LeftControl);
            bool physicallyCrouched = IsPhysicallyCrouched();
            bool grounded = Character.Motor.GroundingStatus.IsStableOnGround;

            if (_wasStableGrounded && !grounded)
            {
                _airborneEligibleForCrouchJump = !physicallyCrouched;
                _ledgeAssistConsumed = false;
                _crouchJumpStartHeight = Vector3.Dot(
                    Character.Motor.TransientPosition, Character.Motor.CharacterUp);
            }

            if (!grounded && crouchHeld && _airborneEligibleForCrouchJump)
            {
                _airborneCrouchLatched = true;
                _crouchJumpActive = true;
                _crouchJumpStableTime = 0f;
            }

            if (_crouchJumpActive)
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
                    _crouchJumpActive = false;
                }
            }

            bool effectiveCrouchHeld = crouchHeld || _airborneCrouchLatched;
            bool crouched = effectiveCrouchHeld || physicallyCrouched;

            if (effectiveCrouchHeld)
                _visualCrouched = true;
            else if (!physicallyCrouched)
            {
                if (_visualCrouched)
                    _compensationReleaseSpeed = Mathf.Abs(_cameraVerticalCompensation) /
                        CrouchCameraTransitionTime;
                _visualCrouched = false;
            }

            if (!_wasStableGrounded && grounded && crouched)
                NormalizeCrouchedLandingVelocity();

            if (_crouchJumpActive && !grounded)
                TryApplyCrouchJumpLedgeAssist();
            _wasStableGrounded = grounded;

            if (grounded)
            {
                float groundedSpeed = crouched
                    ? CrouchSpeed
                    : Input.GetKey(KeyCode.LeftShift) && hasMovementInput
                        ? SprintSpeed
                        : WalkSpeed;

                Character.MaxStableMoveSpeed = groundedSpeed;
                Character.MaxAirMoveSpeed = groundedSpeed;
            }

            var inputs = new PlayerCharacterInputs
            {
                MoveAxisForward = moveForward,
                MoveAxisRight = moveRight,
                CameraRotation = Quaternion.Euler(0f, _yaw, 0f),
                JumpDown = !crouched && Input.GetKeyDown(KeyCode.Space),
                CrouchDown = effectiveCrouchHeld,
                CrouchUp = !effectiveCrouchHeld
            };
            Character.SetInputs(ref inputs);
        }

        private void LateUpdate()
        {
            var capsule = Character.Motor.Capsule;
            float deltaTime = Time.deltaTime;
            float targetEyeHeight = _visualCrouched ? _crouchedEyeHeight : _standingEyeHeight;
            _visualEyeHeight = Mathf.MoveTowards(_visualEyeHeight, targetEyeHeight,
                _eyeTransitionSpeed * deltaTime);

            if (_crouchJumpActive &&
                !Character.Motor.GroundingStatus.IsStableOnGround)
                _contactCompensationWindow = ContactCompensationWindow;
            else
                _contactCompensationWindow = Mathf.Max(0f,
                    _contactCompensationWindow - deltaTime);

            if (!_visualCrouched)
                _cameraVerticalCompensation = Mathf.MoveTowards(
                    _cameraVerticalCompensation, 0f,
                    _compensationReleaseSpeed * deltaTime);

            float physicalRootY = Character.transform.position.y;
            bool hasContact = Character.Motor.GroundingStatus.FoundAnyGround ||
                Character.Motor.LastGroundingStatus.FoundAnyGround;
            if (_hasLastPhysicalRootY && _crouchJumpActive && _visualCrouched &&
                IsPhysicallyCrouched() &&
                _contactCompensationWindow > 0f && hasContact)
            {
                float actualRootDelta = physicalRootY - _lastPhysicalRootY;
                float expectedRootDelta = Character.Motor.Velocity.y * deltaTime;
                float contactCorrection = actualRootDelta - expectedRootDelta;
                if (Mathf.Abs(contactCorrection) >= MinContactCorrection &&
                    Mathf.Abs(contactCorrection) <= MaxContactCompensation)
                {
                    _cameraVerticalCompensation = Mathf.Clamp(
                        _cameraVerticalCompensation - contactCorrection,
                        -MaxContactCompensation, MaxContactCompensation);
                }
            }
            _lastPhysicalRootY = physicalRootY;
            _hasLastPhysicalRootY = true;

            Vector3 eye = capsule.center;
            eye.y = _visualEyeHeight;
            Vector3 renderedEye = Character.transform.TransformPoint(eye) +
                Vector3.up * _cameraVerticalCompensation;
            ViewCamera.transform.SetPositionAndRotation(renderedEye,
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

        private void TryApplyCrouchJumpLedgeAssist()
        {
            if (_ledgeAssistConsumed)
                return;

            Vector3 characterUp = Character.Motor.CharacterUp;
            Vector3 planarVelocity = Vector3.ProjectOnPlane(
                Character.Motor.BaseVelocity, characterUp);
            if (planarVelocity.magnitude <= CrouchSpeed ||
                Vector3.Dot(Character.Motor.BaseVelocity, characterUp) > 0.75f)
                return;

            Vector3 planarDirection = planarVelocity.normalized;
            Vector3 probeOrigin = Character.Motor.TransientPosition -
                planarDirection * LedgeAssistProbeBack + characterUp * LedgeAssistProbeUp;
            int hitCount = Physics.RaycastNonAlloc(probeOrigin, -characterUp,
                _ledgeAssistHits, LedgeAssistProbeDistance,
                Character.Motor.CollidableLayers, QueryTriggerInteraction.Ignore);
            bool foundWalkableSurface = false;
            float nearestDistance = float.PositiveInfinity;
            RaycastHit hit = default(RaycastHit);
            for (int i = 0; i < hitCount; i++)
            {
                RaycastHit candidate = _ledgeAssistHits[i];
                if (candidate.collider == Character.Motor.Capsule ||
                    candidate.distance >= nearestDistance ||
                    Vector3.Angle(characterUp, candidate.normal) >
                    Character.Motor.MaxStableSlopeAngle)
                    continue;

                foundWalkableSurface = true;
                nearestDistance = candidate.distance;
                hit = candidate;
            }
            if (!foundWalkableSurface)
                return;

            float ledgeHeight = Vector3.Dot(hit.point, characterUp) - _crouchJumpStartHeight;
            float verticalMiss = Vector3.Dot(
                hit.point - Character.Motor.TransientPosition, characterUp);
            if (ledgeHeight < LedgeAssistMinHeight || ledgeHeight > LedgeAssistMaxHeight ||
                Mathf.Abs(verticalMiss) > LedgeAssistMaxVerticalMiss)
                return;

            Character.Motor.BaseVelocity -= planarDirection *
                Mathf.Min(LedgeAssistVelocityReduction, planarVelocity.magnitude);
            _ledgeAssistConsumed = true;
        }
    }
}
