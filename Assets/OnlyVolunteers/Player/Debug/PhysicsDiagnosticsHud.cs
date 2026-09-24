using UnityEngine;

namespace OnlyVolunteers.Player.Debugging
{
    [DisallowMultipleComponent]
    public sealed class PhysicsDiagnosticsHud : MonoBehaviour
    {
        [SerializeField, Min(0.01f)] private float smoothingSeconds = 0.25f;

        private const float TextRefreshSeconds = 0.1f;

        private readonly GUIContent content = new GUIContent();
        private OnlyVolunteers.Player.KccFirstPersonInput player;
        private GUIStyle labelStyle;
        private GUIStyle shadowStyle;
        private float smoothedFrameSeconds;
        private float textRefreshTimer;
        private int cachedFontSize;

        private void Awake()
        {
            player = FindAnyObjectByType<OnlyVolunteers.Player.KccFirstPersonInput>();
            content.text = "FPS: --\nVelocity: 0.00 m/s";
        }

        private void Update()
        {
            float frameSeconds = Time.unscaledDeltaTime;
            if (frameSeconds <= 0f)
                return;

            if (smoothedFrameSeconds <= 0f)
            {
                smoothedFrameSeconds = frameSeconds;
            }
            else
            {
                float blend = 1f - Mathf.Exp(
                    -frameSeconds / Mathf.Max(0.01f, smoothingSeconds));
                smoothedFrameSeconds = Mathf.Lerp(smoothedFrameSeconds, frameSeconds, blend);
            }

            textRefreshTimer += frameSeconds;
            if (textRefreshTimer < TextRefreshSeconds)
                return;

            textRefreshTimer %= TextRefreshSeconds;

            float planarSpeed = 0f;
            var motor = player != null && player.Character != null
                ? player.Character.Motor
                : null;
            if (motor != null)
            {
                planarSpeed = Vector3.ProjectOnPlane(
                    motor.BaseVelocity, motor.CharacterUp).magnitude;
            }

            content.text = $"FPS: {1f / smoothedFrameSeconds:0}\n" +
                $"Velocity: {planarSpeed:0.00} m/s";
        }

        private void OnGUI()
        {
            float resolutionScale = Screen.height / 2160f;
            int fontSize = Mathf.Clamp(Mathf.RoundToInt(36f * resolutionScale), 18, 40);
            float padding = Mathf.Clamp(32f * resolutionScale, 16f, 40f);
            float width = Mathf.Clamp(520f * resolutionScale, 300f, 560f);
            float height = fontSize * 2.8f;

            EnsureStyles(fontSize);

            var labelRect = new Rect(
                Screen.width - padding - width,
                padding,
                width,
                height);
            float shadowOffset = Mathf.Clamp(2f * resolutionScale, 1f, 2f);
            var shadowRect = new Rect(
                labelRect.x + shadowOffset,
                labelRect.y + shadowOffset,
                labelRect.width,
                labelRect.height);

            GUI.Label(shadowRect, content, shadowStyle);
            GUI.Label(labelRect, content, labelStyle);
        }

        private void EnsureStyles(int fontSize)
        {
            if (labelStyle == null)
            {
                labelStyle = new GUIStyle(GUI.skin.label)
                {
                    alignment = TextAnchor.UpperRight,
                    richText = false,
                    wordWrap = false
                };
                labelStyle.normal.textColor = Color.white;

                shadowStyle = new GUIStyle(labelStyle);
                shadowStyle.normal.textColor = new Color(0f, 0f, 0f, 0.8f);
            }

            if (cachedFontSize == fontSize)
                return;

            cachedFontSize = fontSize;
            labelStyle.fontSize = fontSize;
            shadowStyle.fontSize = fontSize;
        }
    }
}
