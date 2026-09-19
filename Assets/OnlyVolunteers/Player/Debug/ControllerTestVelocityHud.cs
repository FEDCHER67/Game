using System.Globalization;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Debugging
{
    /// <summary>
    /// Temporary ControllerTest-only movement readout. It creates itself at runtime so the
    /// production Player prefab and production UI remain free of debug-only dependencies.
    /// </summary>
    public sealed class ControllerTestVelocityHud : MonoBehaviour
    {
        const string ControllerTestPath = "Assets/OnlyVolunteers/Scenes/ControllerTest.unity";
        static readonly Rect PanelRect = new Rect(12f, 12f, 250f, 112f);
        static readonly Rect TextRect = new Rect(24f, 22f, 226f, 90f);

        KccFirstPersonInput player;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void CreateForControllerTest()
        {
            if (SceneManager.GetActiveScene().path != ControllerTestPath ||
                Object.FindFirstObjectByType<ControllerTestVelocityHud>() != null)
            {
                return;
            }

            GameObject hudObject = new GameObject("[Debug] Velocity HUD");
            hudObject.AddComponent<ControllerTestVelocityHud>();
        }

        void Awake()
        {
            player = Object.FindFirstObjectByType<KccFirstPersonInput>();
        }

        void OnGUI()
        {
            var character = player != null ? player.Character : null;
            var motor = character != null ? character.Motor : null;
            Vector3 measuredVelocity = motor != null
                ? motor.Velocity
                : Vector3.zero;
            float horizontalSpeed = motor != null
                ? Vector3.ProjectOnPlane(measuredVelocity, motor.CharacterUp).magnitude
                : 0f;
            float verticalSpeed = motor != null
                ? Vector3.Dot(measuredVelocity, motor.CharacterUp)
                : 0f;
            string state = motor != null && motor.GroundingStatus.IsStableOnGround
                ? "Grounded"
                : "Airborne";
            string crouchState = motor != null &&
                motor.Capsule.height <= character.CrouchedCapsuleHeight + 0.01f
                    ? "Crouched"
                    : "Standing";

            GUI.Box(PanelRect, GUIContent.none);
            GUI.Label(
                TextRect,
                string.Format(
                    CultureInfo.InvariantCulture,
                    "Velocity: {0:F2} m/s\nVertical: {1:F2} m/s\nState: {2}\nCrouch: {3}",
                    horizontalSpeed,
                    verticalSpeed,
                    state,
                    crouchState));
        }
    }
}
