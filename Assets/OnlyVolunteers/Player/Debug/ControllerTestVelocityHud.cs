using System.Globalization;
using TheFirstPerson;
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
        static readonly Rect PanelRect = new Rect(12f, 12f, 220f, 94f);
        static readonly Rect TextRect = new Rect(22f, 20f, 200f, 78f);

        FPSController fpsController;

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
            fpsController = Object.FindFirstObjectByType<FPSController>();
        }

        void OnGUI()
        {
            Vector3 measuredVelocity = fpsController != null
                ? fpsController.MeasuredVelocity
                : Vector3.zero;
            float horizontalSpeed = new Vector2(measuredVelocity.x, measuredVelocity.z).magnitude;
            string state = GetStateLabel();
            string crouchState = GetCrouchStateLabel();

            GUI.Box(PanelRect, GUIContent.none);
            GUI.Label(
                TextRect,
                string.Format(
                    CultureInfo.InvariantCulture,
                    "Velocity: {0:F2} m/s\nVertical: {1:F2} m/s\nState: {2}\nCrouch: {3}",
                    horizontalSpeed,
                    measuredVelocity.y,
                    state,
                    crouchState));
        }

        string GetStateLabel()
        {
            if (fpsController == null)
            {
                return "No Controller";
            }
            if (!fpsController.HasValidGroundSupport)
            {
                return "Airborne";
            }
            return fpsController.IsCrouched ? "Crouched" : "Grounded";
        }

        string GetCrouchStateLabel()
        {
            if (fpsController == null)
            {
                return "Standing";
            }
            if (fpsController.IsStandingBlocked)
            {
                return "Blocked";
            }
            if (fpsController.IsCrouched)
            {
                return "Crouched";
            }
            return fpsController.HasCrouchLandingIntent ? "Landing Intent" : "Standing";
        }
    }
}
