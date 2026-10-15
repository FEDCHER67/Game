using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>The devices the operation table reads. Normally the current mouse/keyboard; the dev scenario driver
    /// points it at its own virtual devices so automated runs go through exactly the same view code.</summary>
    public static class OpsInput
    {
        public static Mouse MouseOverride;
        public static Keyboard KeyboardOverride;
        public static Mouse Mouse => MouseOverride != null ? MouseOverride : Mouse.current;
        public static Keyboard Keyboard => KeyboardOverride != null ? KeyboardOverride : Keyboard.current;
        public static Vector2 Position => Mouse != null ? Mouse.position.ReadValue() : Vector2.zero;
        public static bool Down(Key key) { var k = Keyboard; return k != null && k[key].wasPressedThisFrame; }
        public static bool Held(Key key) { var k = Keyboard; return k != null && k[key].isPressed; }
        /// <summary>Automated runs in batch mode / hidden windows cannot lock the OS cursor; the scenario driver sets this
        /// so the first-person code paths that require a locked cursor behave as they do for a player.</summary>
        public static bool CursorLockedOverride;
        public static bool CursorLocked => CursorLockedOverride || Cursor.lockState == CursorLockMode.Locked;
    }
}
