using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace OnlyVolunteers.Map.Look
{
    // Free camera for looking at the map look scene: WASD move, Q/E down/up, hold the right mouse button to look,
    // Shift for speed, mouse wheel changes the base speed.
    public sealed class LookFlyCamera : MonoBehaviour
    {
        public float Speed = 25f, FastMultiplier = 4f, LookSensitivity = 0.15f;

        private float yaw, pitch;

        private void OnEnable()
        {
            Vector3 e = transform.eulerAngles;
            yaw = e.y;
            pitch = e.x > 180f ? e.x - 360f : e.x;
        }

        private void Update()
        {
            ReadInput(out Vector3 move, out Vector2 look, out bool fast, out bool looking, out float wheel);
            if (Mathf.Abs(wheel) > 0.01f) Speed = Mathf.Clamp(Speed * (wheel > 0f ? 1.15f : 0.87f), 2f, 400f);
            if (looking)
            {
                yaw += look.x * LookSensitivity;
                pitch = Mathf.Clamp(pitch - look.y * LookSensitivity, -89f, 89f);
                transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            }
            float v = Speed * (fast ? FastMultiplier : 1f) * Time.unscaledDeltaTime;
            transform.position += (transform.right * move.x + transform.forward * move.z) * v + Vector3.up * (move.y * v);
        }

        private static void ReadInput(out Vector3 move, out Vector2 look, out bool fast, out bool looking, out float wheel)
        {
            move = Vector3.zero;
            look = Vector2.zero;
            fast = looking = false;
            wheel = 0f;
#if ENABLE_INPUT_SYSTEM
            Keyboard k = Keyboard.current;
            Mouse m = Mouse.current;
            if (k != null)
            {
                move.x = (k.dKey.isPressed ? 1f : 0f) - (k.aKey.isPressed ? 1f : 0f);
                move.z = (k.wKey.isPressed ? 1f : 0f) - (k.sKey.isPressed ? 1f : 0f);
                move.y = (k.eKey.isPressed ? 1f : 0f) - (k.qKey.isPressed ? 1f : 0f);
                fast = k.leftShiftKey.isPressed || k.rightShiftKey.isPressed;
            }
            if (m != null)
            {
                looking = m.rightButton.isPressed;
                look = m.delta.ReadValue();
                wheel = m.scroll.ReadValue().y;
            }
#elif ENABLE_LEGACY_INPUT_MANAGER
            move.x = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
            move.z = (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f);
            move.y = (Input.GetKey(KeyCode.E) ? 1f : 0f) - (Input.GetKey(KeyCode.Q) ? 1f : 0f);
            fast = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
            looking = Input.GetMouseButton(1);
            look = new Vector2(Input.GetAxisRaw("Mouse X"), Input.GetAxisRaw("Mouse Y")) * 10f;
            wheel = Input.mouseScrollDelta.y;
#endif
        }
    }
}
