using FishNet.Object;
using FishNet.Transporting;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Friendslop.Network.Physics
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(NetworkObject), typeof(CharacterController))]
    public sealed class NetworkPhysicsPlayer : NetworkBehaviour
    {
        private const string LogPrefix = "[Stage12.4]";
        private const float InputSendInterval = 1f / 30f;
        private const float InputStaleSeconds = 0.3f;

        [Header("View")]
        [SerializeField] private Camera ownerCamera;
        [SerializeField] private Renderer playerRenderer;
        [SerializeField, Min(0f)] private float eyeHeight = 1.55f;
        [SerializeField, Min(0f)] private float mouseSensitivity = 0.08f;

        [Header("Movement")]
        [SerializeField, Min(0f)] private float movementSpeed = 5f;
        [SerializeField] private float gravity = -25f;
        [SerializeField, Min(0f)] private float jumpHeight = 1.3f;
        [SerializeField, Min(0f)] private float pushForce = 14f;

        [Header("Interaction")]
        [SerializeField, Min(0f)] private float maxGrabDistance = 6f;
        [SerializeField, Min(0f)] private float holdDistance = 3f;

        private CharacterController _characterController;
        private Vector2 _serverMoveInput;
        private float _serverYaw;
        private float _serverPitch;
        private float _verticalVelocity;
        private float _lastServerInputAt;
        private bool _serverJumpRequested;
        private float _localYaw;
        private float _localPitch;
        private float _nextInputSendAt;
        private bool _pendingJump;
        private NetworkPhysicsBody _heldBody;

        internal Vector3 ServerEyePosition => transform.position + Vector3.up * eyeHeight;

        internal Vector3 ServerAimDirection => Quaternion.Euler(_serverPitch, _serverYaw, 0f) * Vector3.forward;

        internal Vector3 ServerHoldPoint => ServerEyePosition + ServerAimDirection * holdDistance;

        private void Awake()
        {
            _characterController = GetComponent<CharacterController>();
            if (ownerCamera == null)
                ownerCamera = GetComponentInChildren<Camera>(true);
            if (playerRenderer == null)
                playerRenderer = GetComponentInChildren<Renderer>(true);
        }

        public override void OnStartServer()
        {
            _characterController.enabled = true;
            transform.SetPositionAndRotation(GetSpawnPosition(Owner.ClientId), Quaternion.identity);
            _serverYaw = transform.eulerAngles.y;
            _lastServerInputAt = Time.unscaledTime;
        }

        public override void OnStartClient()
        {
            bool localOwner = IsOwner;
            if (ownerCamera != null)
            {
                ownerCamera.enabled = localOwner;
                AudioListener listener = ownerCamera.GetComponent<AudioListener>();
                if (listener != null)
                    listener.enabled = localOwner;
            }

            if (playerRenderer != null && localOwner)
                playerRenderer.enabled = false;

            if (!IsServerInitialized)
                _characterController.enabled = false;

            if (localOwner)
            {
                _localYaw = transform.eulerAngles.y;
                SetCursorLocked(true);
            }
        }

        public override void OnStopClient()
        {
            if (IsOwner)
                SetCursorLocked(false);
        }

        public override void OnStopServer()
        {
            ReleaseHeldBody("player stopped");
        }

        private void Update()
        {
            if (!IsOwner)
                return;

            HandleCursor();
            CaptureOwnerInput();
        }

        private void FixedUpdate()
        {
            if (!IsServerInitialized || !_characterController.enabled)
                return;

            Vector2 moveInput = Time.unscaledTime - _lastServerInputAt <= InputStaleSeconds
                ? _serverMoveInput
                : Vector2.zero;

            transform.rotation = Quaternion.Euler(0f, _serverYaw, 0f);
            Vector3 planar = transform.right * moveInput.x + transform.forward * moveInput.y;
            if (planar.sqrMagnitude > 1f)
                planar.Normalize();

            if (_characterController.isGrounded)
            {
                if (_serverJumpRequested)
                    _verticalVelocity = Mathf.Sqrt(jumpHeight * -2f * gravity);
                else if (_verticalVelocity < 0f)
                    _verticalVelocity = -2f;
            }

            _serverJumpRequested = false;
            _verticalVelocity += gravity * Time.fixedDeltaTime;
            Vector3 velocity = planar * movementSpeed + Vector3.up * _verticalVelocity;
            _characterController.Move(velocity * Time.fixedDeltaTime);
        }

        private void OnControllerColliderHit(ControllerColliderHit hit)
        {
            if (!IsServerInitialized || hit.rigidbody == null || hit.rigidbody.isKinematic)
                return;

            if (hit.rigidbody.GetComponent<NetworkPhysicsBody>() == null || hit.moveDirection.y < -0.3f)
                return;

            Vector3 direction = Vector3.ProjectOnPlane(hit.moveDirection, Vector3.up);
            if (direction.sqrMagnitude < 0.001f)
                direction = Vector3.ProjectOnPlane(-hit.normal, Vector3.up);
            if (direction.sqrMagnitude < 0.001f)
                return;

            hit.rigidbody.WakeUp();
            hit.rigidbody.AddForce(direction.normalized * pushForce, ForceMode.Force);
        }

        private void CaptureOwnerInput()
        {
            Keyboard keyboard = Keyboard.current;
            Mouse mouse = Mouse.current;

            if (Cursor.lockState == CursorLockMode.Locked && mouse != null)
            {
                Vector2 mouseDelta = mouse.delta.ReadValue() * mouseSensitivity;
                _localYaw = Mathf.Repeat(_localYaw + mouseDelta.x, 360f);
                _localPitch = Mathf.Clamp(_localPitch - mouseDelta.y, -85f, 85f);
                if (ownerCamera != null)
                    ownerCamera.transform.rotation = Quaternion.Euler(_localPitch, _localYaw, 0f);
            }

            Vector2 move = Vector2.zero;
            if (keyboard != null)
            {
                move.x = (keyboard.dKey.isPressed ? 1f : 0f) - (keyboard.aKey.isPressed ? 1f : 0f);
                move.y = (keyboard.wKey.isPressed ? 1f : 0f) - (keyboard.sKey.isPressed ? 1f : 0f);
                move = Vector2.ClampMagnitude(move, 1f);
                _pendingJump |= keyboard.spaceKey.wasPressedThisFrame;
            }

            if (Time.unscaledTime >= _nextInputSendAt)
            {
                _nextInputSendAt = Time.unscaledTime + InputSendInterval;
                SubmitInputServerRpc(move, _localYaw, _localPitch, _pendingJump, Channel.Unreliable);
                _pendingJump = false;
            }

            if (mouse != null && mouse.leftButton.wasReleasedThisFrame)
                ReleaseGrabServerRpc();

            if (mouse == null || Cursor.lockState != CursorLockMode.Locked)
                return;

            if (mouse.leftButton.wasPressedThisFrame)
                TryRequestGrab();
        }

        private void TryRequestGrab()
        {
            if (ownerCamera == null)
                return;

            Ray ray = ownerCamera.ViewportPointToRay(new Vector3(0.5f, 0.5f));
            if (!UnityEngine.Physics.Raycast(
                    ray,
                    out RaycastHit hit,
                    maxGrabDistance,
                    UnityEngine.Physics.DefaultRaycastLayers,
                    QueryTriggerInteraction.Ignore))
            {
                return;
            }

            NetworkPhysicsBody body = hit.rigidbody != null
                ? hit.rigidbody.GetComponent<NetworkPhysicsBody>()
                : null;
            if (body == null)
                return;

            Vector3 localGrabPoint = body.transform.InverseTransformPoint(hit.point);
            RequestGrabServerRpc(body.NetworkObject, localGrabPoint);
        }

        [ServerRpc]
        private void SubmitInputServerRpc(
            Vector2 moveInput,
            float yaw,
            float pitch,
            bool jumpRequested,
            Channel channel = Channel.Reliable)
        {
            if (!IsFinite(moveInput.x) || !IsFinite(moveInput.y) || !IsFinite(yaw) || !IsFinite(pitch))
                return;

            _serverMoveInput = Vector2.ClampMagnitude(moveInput, 1f);
            _serverYaw = Mathf.Repeat(yaw, 360f);
            _serverPitch = Mathf.Clamp(pitch, -85f, 85f);
            _serverJumpRequested |= jumpRequested;
            _lastServerInputAt = Time.unscaledTime;
        }

        [ServerRpc]
        private void RequestGrabServerRpc(NetworkObject targetObject, Vector3 localGrabPoint)
        {
            if (_heldBody != null || targetObject == null || targetObject.Owner.IsValid)
                return;

            if (!IsFinite(localGrabPoint.x) || !IsFinite(localGrabPoint.y) || !IsFinite(localGrabPoint.z))
                return;

            NetworkPhysicsBody body = targetObject.GetComponent<NetworkPhysicsBody>();
            if (body == null || !body.IsServerInitialized)
                return;

            Vector3 worldGrabPoint = body.transform.TransformPoint(localGrabPoint);
            Vector3 fromEye = worldGrabPoint - ServerEyePosition;
            if (fromEye.sqrMagnitude > maxGrabDistance * maxGrabDistance || fromEye.sqrMagnitude < 0.01f)
                return;

            if (!UnityEngine.Physics.Raycast(
                    ServerEyePosition,
                    fromEye.normalized,
                    out RaycastHit hit,
                    fromEye.magnitude + 0.05f,
                    UnityEngine.Physics.DefaultRaycastLayers,
                    QueryTriggerInteraction.Ignore)
                || hit.rigidbody == null
                || hit.rigidbody.GetComponent<NetworkPhysicsBody>() != body)
            {
                return;
            }

            if (Vector3.Distance(hit.point, worldGrabPoint) > 0.35f)
                return;

            Vector3 authoritativeLocalGrabPoint = body.transform.InverseTransformPoint(hit.point);
            if (body.TryAcquire(this, authoritativeLocalGrabPoint))
                _heldBody = body;
        }

        [ServerRpc]
        private void ReleaseGrabServerRpc()
        {
            ReleaseHeldBody("owner released");
        }

        private void ReleaseHeldBody(string reason)
        {
            NetworkPhysicsBody body = _heldBody;
            _heldBody = null;
            if (body != null)
                body.Release(this, reason);
        }

        private void HandleCursor()
        {
            Keyboard keyboard = Keyboard.current;
            Mouse mouse = Mouse.current;
            if (keyboard != null && keyboard.escapeKey.wasPressedThisFrame)
                SetCursorLocked(false);
            else if (mouse != null && mouse.rightButton.wasPressedThisFrame)
                SetCursorLocked(true);
        }

        private static Vector3 GetSpawnPosition(int connectionId)
        {
            float x = connectionId % 2 == 0 ? -3f : 3f;
            float z = -5f + (connectionId / 2) * 2f;
            return new Vector3(x, 0.05f, z);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static void SetCursorLocked(bool locked)
        {
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }
    }
}
