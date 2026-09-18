using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers
{
    /// <summary>
    /// Minimal Unity Input System compatibility bridge for the vendored TheFirstPerson
    /// FPSController. The project runs with Active Input Handling set to the Input System
    /// package only, where UnityEngine.Input calls throw, so this TFPInput asset supplies
    /// the donor controller with the same values the legacy default axes would have.
    ///
    /// Bindings: WASD move, mouse look, Left Shift run, Space jump, Left Ctrl crouch,
    /// Escape unlock cursor, Left Mouse relock cursor.
    /// </summary>
    [CreateAssetMenu(fileName = "TFPInputSystemBridge", menuName = "TFP/Input System Bridge")]
    public class TFPInputSystemBridge : TFPInput
    {
        // Unity's legacy "Mouse X"/"Mouse Y" axes scaled the raw mouse pixel delta by the
        // InputManager sensitivity. The bridge applies an explicit Inspector-tunable scale
        // to the raw immediate delta instead, so mouse feel no longer depends on
        // ProjectSettings/InputManager.asset.
        [SerializeField, Min(0)]
        private float mouseSensitivityScale = 0.007f;

        public override float XAxis()
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard == null)
            {
                return 0f;
            }

            float value = 0f;
            if (keyboard.aKey.isPressed)
            {
                value -= 1f;
            }
            if (keyboard.dKey.isPressed)
            {
                value += 1f;
            }
            return value;
        }

        public override float YAxis()
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard == null)
            {
                return 0f;
            }

            float value = 0f;
            if (keyboard.sKey.isPressed)
            {
                value -= 1f;
            }
            if (keyboard.wKey.isPressed)
            {
                value += 1f;
            }
            return value;
        }

        public override float XMouse()
        {
            Mouse mouse = Mouse.current;
            if (mouse == null)
            {
                return 0f;
            }
            return mouse.delta.ReadValue().x * mouseSensitivityScale;
        }

        public override float YMouse()
        {
            Mouse mouse = Mouse.current;
            if (mouse == null)
            {
                return 0f;
            }
            return mouse.delta.ReadValue().y * mouseSensitivityScale;
        }

        public override bool CrouchPressed()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.leftCtrlKey.wasPressedThisFrame;
        }

        public override bool CrouchHeld()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.leftCtrlKey.isPressed;
        }

        public override bool RunPressed()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.leftShiftKey.wasPressedThisFrame;
        }

        public override bool RunHeld()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.leftShiftKey.isPressed;
        }

        public override bool JumpHeld()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.spaceKey.isPressed;
        }

        public override bool JumpPressed()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.spaceKey.wasPressedThisFrame;
        }

        public override bool UnlockMouseButton()
        {
            Keyboard keyboard = Keyboard.current;
            return keyboard != null && keyboard.escapeKey.wasPressedThisFrame;
        }

        public override bool MousePressed()
        {
            Mouse mouse = Mouse.current;
            return mouse != null && mouse.leftButton.wasPressedThisFrame;
        }
    }
}
