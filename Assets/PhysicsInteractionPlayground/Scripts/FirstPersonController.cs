using UnityEngine;
using UnityEngine.InputSystem;

namespace Friendslop.PhysicsPlayground
{
    [RequireComponent(typeof(CharacterController))]
    public sealed class FirstPersonController : MonoBehaviour
    {
        [SerializeField] private Transform cameraTransform;
        [SerializeField, Min(0f)] private float movementSpeed = 5f;
        [SerializeField, Min(0f)] private float groundAcceleration = 10f;
        [SerializeField, Min(0f)] private float groundFriction = 6f;
        [SerializeField, Min(0f)] private float airAcceleration = 10f;
        [SerializeField, Min(0f)] private float maxAirWishSpeed = 0.5f;
        [SerializeField, Min(0f)] private float mouseSensitivity = 0.08f;
        [SerializeField] private float gravity = -25f;
        [SerializeField, Min(0f)] private float jumpHeight = 1.3f;
        [SerializeField, Min(0.1f)] private float standingHeight = 1.8f;
        [SerializeField, Min(0.1f)] private float crouchingHeight = 1.1f;
        [SerializeField, Min(0f)] private float crouchTransitionSpeed = 8f;
        [SerializeField, Range(0.1f, 1f)] private float crouchMovementSpeedMultiplier = 0.7f;
        [SerializeField, Min(0f)] private float pushPower = 12f;

        private CharacterController characterController;
        private readonly Collider[] standingClearanceHits = new Collider[8];
        private Vector3 standingCameraLocalPosition;
        private Vector3 standingControllerCenter;
        private float controllerBottom;
        private float pitch;
        private Vector3 horizontalVelocity;
        private float verticalVelocity;
        private bool isCrouched;

        private void Awake()
        {
            characterController = GetComponent<CharacterController>();

            float minimumHeight = characterController.radius * 2f;
            standingHeight = Mathf.Max(standingHeight, minimumHeight);
            crouchingHeight = Mathf.Clamp(crouchingHeight, minimumHeight, standingHeight);
            controllerBottom = characterController.center.y - characterController.height * 0.5f;
            standingControllerCenter = characterController.center;
            standingControllerCenter.y = controllerBottom + standingHeight * 0.5f;

            if (cameraTransform == null)
            {
                Camera childCamera = GetComponentInChildren<Camera>();
                cameraTransform = childCamera != null ? childCamera.transform : null;
            }

            if (cameraTransform != null)
            {
                pitch = NormalizeAngle(cameraTransform.localEulerAngles.x);
                standingCameraLocalPosition = cameraTransform.localPosition;
            }
        }

        private void OnEnable()
        {
            SetCursorLocked(true);
        }

        private void OnDisable()
        {
            SetCursorLocked(false);
        }

        private void Update()
        {
            HandleCursor();

            if (Cursor.lockState == CursorLockMode.Locked)
            {
                Look();
            }

            UpdateCrouch();
            Move();
        }

        private void UpdateCrouch()
        {
            Keyboard keyboard = Keyboard.current;
            bool crouchHeld = keyboard != null && keyboard.leftCtrlKey.isPressed;
            bool belowStandingHeight = characterController.height < standingHeight - 0.01f;
            isCrouched = crouchHeld || (belowStandingHeight && !HasStandingClearance());

            float targetHeight = isCrouched ? crouchingHeight : standingHeight;
            float nextHeight = Mathf.MoveTowards(
                characterController.height,
                targetHeight,
                crouchTransitionSpeed * Time.deltaTime);

            Vector3 nextCenter = standingControllerCenter;
            nextCenter.y = controllerBottom + nextHeight * 0.5f;
            characterController.height = nextHeight;
            characterController.center = nextCenter;

            if (cameraTransform != null)
            {
                Vector3 targetCameraPosition = standingCameraLocalPosition;
                targetCameraPosition.y -= standingHeight - targetHeight;
                cameraTransform.localPosition = Vector3.MoveTowards(
                    cameraTransform.localPosition,
                    targetCameraPosition,
                    crouchTransitionSpeed * Time.deltaTime);
            }
        }

        private bool HasStandingClearance()
        {
            Vector3 worldCenter = transform.TransformPoint(standingControllerCenter);
            Vector3 up = transform.up;
            Vector3 scale = transform.lossyScale;
            float radiusScale = Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            float worldRadius = characterController.radius * radiusScale;
            float worldHeight = Mathf.Max(standingHeight * Mathf.Abs(scale.y), worldRadius * 2f);
            float halfCylinder = worldHeight * 0.5f - worldRadius;
            float clearanceRadius = Mathf.Max(0.01f, worldRadius - characterController.skinWidth * radiusScale);
            Vector3 bottom = worldCenter - up * halfCylinder;
            Vector3 top = worldCenter + up * halfCylinder;

            int hitCount = Physics.OverlapCapsuleNonAlloc(
                bottom,
                top,
                clearanceRadius,
                standingClearanceHits,
                Physics.DefaultRaycastLayers,
                QueryTriggerInteraction.Ignore);

            for (int i = 0; i < hitCount; i++)
            {
                Collider hit = standingClearanceHits[i];
                if (hit != null && hit != characterController && !hit.transform.IsChildOf(transform))
                {
                    return false;
                }
            }

            return hitCount < standingClearanceHits.Length;
        }

        private void HandleCursor()
        {
            Keyboard keyboard = Keyboard.current;
            Mouse mouse = Mouse.current;

            if (keyboard != null && keyboard.escapeKey.wasPressedThisFrame)
            {
                SetCursorLocked(false);
            }
            else if (mouse != null && mouse.leftButton.wasPressedThisFrame && Cursor.lockState != CursorLockMode.Locked)
            {
                SetCursorLocked(true);
            }
        }

        private void Look()
        {
            if (cameraTransform == null || Mouse.current == null)
            {
                return;
            }

            Vector2 mouseDelta = Mouse.current.delta.ReadValue() * mouseSensitivity;
            transform.Rotate(Vector3.up, mouseDelta.x, Space.Self);

            pitch = Mathf.Clamp(pitch - mouseDelta.y, -89f, 89f);
            cameraTransform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        private void Move()
        {
            Vector2 movementInput = Vector2.zero;
            Keyboard keyboard = Keyboard.current;

            if (keyboard != null)
            {
                movementInput.x = (keyboard.dKey.isPressed ? 1f : 0f) - (keyboard.aKey.isPressed ? 1f : 0f);
                movementInput.y = (keyboard.wKey.isPressed ? 1f : 0f) - (keyboard.sKey.isPressed ? 1f : 0f);
                movementInput = Vector2.ClampMagnitude(movementInput, 1f);
            }

            float currentMovementSpeed = movementSpeed * (isCrouched ? crouchMovementSpeedMultiplier : 1f);
            float inputMagnitude = movementInput.magnitude;
            Vector3 planarWish = transform.right * movementInput.x + transform.forward * movementInput.y;
            Vector3 wishDirection = planarWish.sqrMagnitude > 0f ? planarWish.normalized : Vector3.zero;
            float wishSpeed = currentMovementSpeed * inputMagnitude;

            if (characterController.isGrounded)
            {
                float horizontalSpeed = horizontalVelocity.magnitude;
                if (horizontalSpeed > 0f)
                {
                    float drop = Mathf.Max(horizontalSpeed, currentMovementSpeed) * groundFriction * Time.deltaTime;
                    float retainedSpeed = Mathf.Max(0f, horizontalSpeed - drop);
                    horizontalVelocity *= retainedSpeed / horizontalSpeed;
                }

                if (wishSpeed > 0f)
                {
                    // Projection cap: stop accelerating once velocity projected onto wishDirection reaches wishSpeed.
                    float addSpeed = wishSpeed - Vector3.Dot(horizontalVelocity, wishDirection);
                    if (addSpeed > 0f)
                    {
                        horizontalVelocity +=
                            wishDirection * Mathf.Min(groundAcceleration * wishSpeed * Time.deltaTime, addSpeed);
                    }
                }

                if (verticalVelocity < 0f)
                {
                    verticalVelocity = -2f;
                }

                if (keyboard != null && keyboard.spaceKey.wasPressedThisFrame)
                {
                    verticalVelocity = Mathf.Sqrt(jumpHeight * -2f * gravity);
                }
            }
            else if (wishSpeed > 0f)
            {
                float cappedWishSpeed = Mathf.Min(wishSpeed, maxAirWishSpeed);
                float addSpeed = cappedWishSpeed - Vector3.Dot(horizontalVelocity, wishDirection);
                if (addSpeed > 0f)
                {
                    horizontalVelocity +=
                        wishDirection * Mathf.Min(airAcceleration * wishSpeed * Time.deltaTime, addSpeed);
                }
            }

            verticalVelocity += gravity * Time.deltaTime;
            Vector3 velocity = horizontalVelocity + Vector3.up * verticalVelocity;
            characterController.Move(velocity * Time.deltaTime);
        }

        private void OnControllerColliderHit(ControllerColliderHit hit)
        {
            Rigidbody body = hit.rigidbody;
            if (body == null || body.isKinematic || hit.moveDirection.y < -0.3f)
            {
                return;
            }

            Vector3 pushDirection = Vector3.ProjectOnPlane(hit.moveDirection, Vector3.up);
            if (pushDirection.sqrMagnitude < 0.001f)
            {
                pushDirection = Vector3.ProjectOnPlane(-hit.normal, Vector3.up);
            }

            if (pushDirection.sqrMagnitude > 0.001f)
            {
                body.AddForce(pushDirection.normalized * pushPower, ForceMode.Force);
            }
        }

        private static void SetCursorLocked(bool isLocked)
        {
            Cursor.lockState = isLocked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !isLocked;
        }

        private static float NormalizeAngle(float angle)
        {
            return angle > 180f ? angle - 360f : angle;
        }
    }
}
