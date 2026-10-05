using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Grey-box on-foot test character (Fedya: walk around as the Sausage Buddy and get into the van).
    // WASD relative to the camera, Shift runs. Not the networked player; the Buddy has only Idle and a panic run so far.
    // Alternative to the first-person KCC pawn (menu "... walk as Buddy"), seen through GreyboxFollowCamera on Main Camera.
    [RequireComponent(typeof(CharacterController))]
    public sealed class GreyboxWalker : GreyboxPawn
    {
        public float WalkSpeed = 2.4f;
        public float RunSpeed = 5.5f;
        public float TurnSpeed = 720f;
        public float Gravity = 20f;
        public Transform CameraTransform;
        public GreyboxFollowCamera Follow;

        private CharacterController _controller;
        private Animator _animator;
        private GreyboxFace _face;
        private float _verticalSpeed;
        private string _state;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            _animator = GetComponentInChildren<Animator>();
            _face = new GreyboxFace(gameObject);
            // Scenes built before the pawn split referenced the follow camera only from the van seat; it sits on CameraTransform.
            if (Follow == null && CameraTransform != null) Follow = CameraTransform.GetComponent<GreyboxFollowCamera>();
        }

        public override Transform Body => transform;

        public override void SetControlled(bool on)
        {
            gameObject.SetActive(on);
            if (Follow != null) Follow.enabled = on;
        }

        private void Update()
        {
            float x = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
            float z = (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f);
            Vector3 forward = CameraTransform != null
                ? Vector3.ProjectOnPlane(CameraTransform.forward, Vector3.up).normalized
                : transform.forward;
            Vector3 move = forward * z + Vector3.Cross(Vector3.up, forward) * x;
            if (move.sqrMagnitude > 1f) move.Normalize();
            bool moving = move.sqrMagnitude > 0.01f;
            bool running = Input.GetKey(KeyCode.LeftShift);

            if (moving)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(move), TurnSpeed * Time.deltaTime);
            _verticalSpeed = _controller.isGrounded ? -1f : _verticalSpeed - Gravity * Time.deltaTime;
            _controller.Move((move * (running ? RunSpeed : WalkSpeed) + Vector3.up * _verticalSpeed) * Time.deltaTime);

            Play(moving ? "Run" : "Idle", moving ? (running ? 1.15f : 0.6f) : 1f);
            // Plain C# state does not survive a script reload in Play mode; rebuild it instead of throwing every frame.
            _face ??= new GreyboxFace(gameObject);
            _face.Set("Happy", running ? 0f : 60f, 200f);
            _face.TickBlink();
        }

        private void LateUpdate() => _face?.Apply();

        private void Play(string state, float speed)
        {
            if (_animator == null) return;
            _animator.speed = speed;
            if (_state == state) return;
            _animator.CrossFadeInFixedTime(state, 0.15f);
            _state = state;
        }

        public override void Teleport(Vector3 position, float yawDegrees)
        {
            _controller.enabled = false;
            transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yawDegrees, 0f));
            _controller.enabled = true;
            _verticalSpeed = 0f;
            if (TryGetComponent(out SeaReturnTracker tracker)) tracker.Rebase();
            if (Follow != null) Follow.SnapBehind(transform);
        }
    }
}
