using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Player.Debugging
{
    // Debug reticle for the two player test scenes only.
    [DisallowMultipleComponent]
    public sealed class TestCrosshairHud : MonoBehaviour
    {
        private const string ControllerTestPath =
            "Assets/OnlyVolunteers/Scenes/ControllerTest.unity";
        private const string PhysicsInteractionTestPath =
            "Assets/OnlyVolunteers/Scenes/PhysicsInteractionTest.unity";

        private static readonly Color ShadowColor = new Color(0f, 0f, 0f, 0.65f);
        private static TestCrosshairHud instance;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void CreateForTestScene()
        {
            if (!IsTestScene() || Object.FindAnyObjectByType<TestCrosshairHud>() != null)
                return;

            new GameObject("[Debug] Crosshair").AddComponent<TestCrosshairHud>();
        }

        private static bool IsTestScene()
        {
            string path = SceneManager.GetActiveScene().path;
            return path == ControllerTestPath || path == PhysicsInteractionTestPath;
        }

        private void Awake()
        {
            if (instance != null && instance != this)
            {
                Destroy(this);
                return;
            }

            instance = this;
        }

        private void OnDestroy()
        {
            if (instance == this)
                instance = null;
        }

        private void OnGUI()
        {
            if (instance != this || Event.current.type != EventType.Repaint ||
                gameObject.scene.handle != SceneManager.GetActiveScene().handle)
                return;

            float scale = Mathf.Clamp(Screen.height / 1080f, 0.75f, 1.5f);
            int arm = Mathf.RoundToInt(5f * scale);
            int thickness = Mathf.RoundToInt(2f * scale);
            int gap = Mathf.RoundToInt(3f * scale);
            float centerX = Screen.width * 0.5f;
            float centerY = Screen.height * 0.5f;

            Color previousColor = GUI.color;
            GUI.color = ShadowColor;
            DrawArms(centerX, centerY, arm, thickness, gap, 1f);
            GUI.color = Color.white;
            DrawArms(centerX, centerY, arm, thickness, gap, 0f);
            GUI.color = previousColor;
        }

        private static void DrawArms(float centerX, float centerY, int arm,
            int thickness, int gap, float outline)
        {
            float halfGap = gap * 0.5f;
            float halfThickness = thickness * 0.5f;
            Texture2D texture = Texture2D.whiteTexture;

            GUI.DrawTexture(new Rect(centerX - halfGap - arm - outline,
                centerY - halfThickness - outline,
                arm + 2f * outline, thickness + 2f * outline), texture);
            GUI.DrawTexture(new Rect(centerX + halfGap - outline,
                centerY - halfThickness - outline,
                arm + 2f * outline, thickness + 2f * outline), texture);
            GUI.DrawTexture(new Rect(centerX - halfThickness - outline,
                centerY - halfGap - arm - outline,
                thickness + 2f * outline, arm + 2f * outline), texture);
            GUI.DrawTexture(new Rect(centerX - halfThickness - outline,
                centerY + halfGap - outline,
                thickness + 2f * outline, arm + 2f * outline), texture);
        }
    }
}
