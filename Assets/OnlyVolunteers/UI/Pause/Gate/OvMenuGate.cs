using UnityEngine;

namespace OnlyVolunteers.UI
{
    /// <summary>One switch every gameplay input reads (W86 pause menu, Fedya 25.10). Lives in its own tiny assembly so the
    /// Inventory and VanPaint assemblies can read it too. While <see cref="Blocking"/> is set a menu owns the keyboard and mouse:
    /// gameplay Update methods return early. Escape: a context that uses Escape this frame (the operating table, a text field)
    /// calls <see cref="ConsumeEscape"/>; the pause menu runs last in the frame and opens only on a free Escape.</summary>
    public static class OvMenuGate
    {
        public static bool Blocking { get; set; }
        /// <summary>A pause menu is installed in this scene: other scenes' Escape panels (NetworkSession) stay as they were.</summary>
        public static bool MenuInstalled { get; set; }
        /// <summary>Text inputs that use Escape themselves (the van lettering field) count up while open.</summary>
        public static int TextInputs { get; set; }

        static int escapeConsumedFrame = -1;
        public static void ConsumeEscape() => escapeConsumedFrame = Time.frameCount;
        public static bool EscapeFree => escapeConsumedFrame != Time.frameCount && TextInputs <= 0;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { Blocking = false; MenuInstalled = false; TextInputs = 0; escapeConsumedFrame = -1; }
    }
}
