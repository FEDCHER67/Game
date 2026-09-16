using UnityEngine;
using UnityEngine.UI;

namespace Friendslop.PhysicsPlayground
{
    public sealed class CenterCrosshair : MonoBehaviour
    {
        [SerializeField] private PhysicsGrabber grabber;
        [SerializeField, Min(0f)] private float dotSize = 4f;
        [SerializeField, Min(0f)] private float lineLength = 12f;
        [SerializeField, Min(0f)] private float lineThickness = 2f;
        [SerializeField, Min(0f)] private float lineGap = 4f;
        [SerializeField] private Color neutralColor = new Color(0.85f, 0.85f, 0.85f, 1f);
        [SerializeField] private Color interactableColor = new Color(1f, 0.85f, 0.2f, 1f);
        [SerializeField] private Color grabbedColor = new Color(1f, 0.45f, 0.1f, 1f);

        private readonly Image[] parts = new Image[5];
        private Color appliedColor;

        private void Awake()
        {
            if (grabber == null)
            {
                grabber = GetComponentInParent<PhysicsGrabber>();
            }

            if (grabber == null)
            {
                grabber = FindAnyObjectByType<PhysicsGrabber>();
            }

            Build();
            ApplyColor(GetTargetColor());
        }

        private void LateUpdate()
        {
            Color targetColor = GetTargetColor();
            if (targetColor != appliedColor)
            {
                ApplyColor(targetColor);
            }
        }

        private Color GetTargetColor()
        {
            if (grabber == null)
            {
                return neutralColor;
            }

            if (grabber.IsGrabbing)
            {
                return grabbedColor;
            }

            return grabber.HasValidGrabTarget ? interactableColor : neutralColor;
        }

        private void Build()
        {
            RectTransform root = CreateRect(transform, "Crosshair");
            root.anchorMin = new Vector2(0.5f, 0.5f);
            root.anchorMax = new Vector2(0.5f, 0.5f);
            root.pivot = new Vector2(0.5f, 0.5f);
            root.anchoredPosition = Vector2.zero;
            root.sizeDelta = Vector2.zero;

            float lineOffset = lineGap + lineLength * 0.5f;

            parts[0] = CreatePart(root, "Dot", new Vector2(dotSize, dotSize), Vector2.zero);
            parts[1] = CreatePart(root, "Line Top", new Vector2(lineThickness, lineLength), new Vector2(0f, lineOffset));
            parts[2] = CreatePart(root, "Line Bottom", new Vector2(lineThickness, lineLength), new Vector2(0f, -lineOffset));
            parts[3] = CreatePart(root, "Line Left", new Vector2(lineLength, lineThickness), new Vector2(-lineOffset, 0f));
            parts[4] = CreatePart(root, "Line Right", new Vector2(lineLength, lineThickness), new Vector2(lineOffset, 0f));
        }

        private void ApplyColor(Color color)
        {
            appliedColor = color;

            for (int i = 0; i < parts.Length; i++)
            {
                parts[i].color = color;
            }
        }

        private static RectTransform CreateRect(Transform parent, string objectName)
        {
            GameObject child = new GameObject(objectName, typeof(RectTransform));
            RectTransform rect = (RectTransform)child.transform;
            rect.SetParent(parent, false);
            return rect;
        }

        private static Image CreatePart(RectTransform parent, string partName, Vector2 size, Vector2 position)
        {
            RectTransform rect = CreateRect(parent, partName);
            rect.anchorMin = new Vector2(0.5f, 0.5f);
            rect.anchorMax = new Vector2(0.5f, 0.5f);
            rect.pivot = new Vector2(0.5f, 0.5f);
            rect.sizeDelta = size;
            rect.anchoredPosition = position;

            Image image = rect.gameObject.AddComponent<Image>();
            image.raycastTarget = false;
            return image;
        }
    }
}
