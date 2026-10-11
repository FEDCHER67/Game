using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Code-built uGUI helpers: sprites, fonts and the few widgets the phone uses.
    public static class PhoneUi
    {
        private const int RoundedSize = 128;
        private const float RoundedRadius = 60f;

        private static readonly Dictionary<string, Sprite> Loaded = new();
        private static Sprite rounded;
        private static Sprite circle;
        private static Sprite arrow;
        private static Font regular;
        private static Font heavy;

        public static readonly Color White = Color.white;
        public static readonly Color Ink = Hex("#1B1B22");
        public static readonly Color Muted = Hex("#8A8F98");

        public static Font Regular => regular != null ? regular : regular = LoadFont("Segoe UI");
        public static Font Heavy => heavy != null ? heavy : heavy = LoadFont("Segoe UI Black");

        public static Color Hex(string hex, float alpha = 1f)
        {
            ColorUtility.TryParseHtmlString(hex, out Color color);
            color.a = alpha;
            return color;
        }

        private static Font LoadFont(string osName)
        {
            if (Array.IndexOf(Font.GetOSInstalledFontNames(), osName) >= 0)
                return Font.CreateDynamicFontFromOSFont(osName, 32);
            return Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        }

        public static Sprite Icon(string name)
        {
            if (Loaded.TryGetValue(name, out Sprite sprite) && sprite != null)
                return sprite;
            var texture = Resources.Load<Texture2D>("Phone/" + name);
            if (texture == null)
            {
                Debug.LogWarning("[Phone] missing texture Phone/" + name);
                return Circle;
            }
            sprite = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height),
                new Vector2(0.5f, 0.5f), 100f);
            Loaded[name] = sprite;
            return sprite;
        }

        public static Sprite Rounded => rounded != null ? rounded : rounded = BuildRounded();
        public static Sprite Circle => circle != null ? circle : circle = BuildCircle();
        public static Sprite Arrow => arrow != null ? arrow : arrow = BuildArrow();

        private static Texture2D NewTexture(int size, string name)
        {
            return new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                name = name,
                wrapMode = TextureWrapMode.Clamp,
                filterMode = FilterMode.Bilinear,
                hideFlags = HideFlags.DontSave
            };
        }

        private static Sprite BuildRounded()
        {
            var texture = NewTexture(RoundedSize, "PhoneRounded");
            var pixels = new Color32[RoundedSize * RoundedSize];
            float half = RoundedSize * 0.5f;
            for (int y = 0; y < RoundedSize; y++)
            for (int x = 0; x < RoundedSize; x++)
            {
                float qx = Mathf.Abs(x + 0.5f - half) - (half - RoundedRadius);
                float qy = Mathf.Abs(y + 0.5f - half) - (half - RoundedRadius);
                float outside = new Vector2(Mathf.Max(qx, 0f), Mathf.Max(qy, 0f)).magnitude +
                    Mathf.Min(Mathf.Max(qx, qy), 0f) - RoundedRadius;
                byte a = (byte)(Mathf.Clamp01(0.5f - outside) * 255f);
                pixels[y * RoundedSize + x] = new Color32(255, 255, 255, a);
            }
            texture.SetPixels32(pixels);
            texture.Apply();
            var border = new Vector4(RoundedRadius, RoundedRadius, RoundedRadius, RoundedRadius);
            return Sprite.Create(texture, new Rect(0, 0, RoundedSize, RoundedSize),
                new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, border);
        }

        private static Sprite BuildCircle()
        {
            const int size = 128;
            var texture = NewTexture(size, "PhoneCircle");
            var pixels = new Color32[size * size];
            float r = size * 0.5f;
            for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float d = new Vector2(x + 0.5f - r, y + 0.5f - r).magnitude - (r - 1f);
                pixels[y * size + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(0.5f - d) * 255f));
            }
            texture.SetPixels32(pixels);
            texture.Apply();
            return Sprite.Create(texture, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f);
        }

        private static Sprite BuildArrow()
        {
            const int size = 64;
            const int samples = 4;
            var texture = NewTexture(size, "PhoneArrow");
            var pixels = new Color32[size * size];
            Vector2 tip = new(32f, 60f), left = new(8f, 6f), right = new(56f, 6f), notch = new(32f, 20f);
            for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                int hits = 0;
                for (int sy = 0; sy < samples; sy++)
                for (int sx = 0; sx < samples; sx++)
                {
                    var p = new Vector2(x + (sx + 0.5f) / samples, y + (sy + 0.5f) / samples);
                    if (InTriangle(p, tip, left, notch) || InTriangle(p, tip, notch, right))
                        hits++;
                }
                pixels[y * size + x] = new Color32(255, 255, 255, (byte)(hits * 255 / (samples * samples)));
            }
            texture.SetPixels32(pixels);
            texture.Apply();
            return Sprite.Create(texture, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f);
        }

        private static bool InTriangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d1 = (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y);
            float d2 = (p.x - c.x) * (b.y - c.y) - (b.x - c.x) * (p.y - c.y);
            float d3 = (p.x - a.x) * (c.y - a.y) - (c.x - a.x) * (p.y - a.y);
            bool negative = d1 < 0 || d2 < 0 || d3 < 0;
            bool positive = d1 > 0 || d2 > 0 || d3 > 0;
            return !(negative && positive);
        }

        // ---------- layout ----------

        public static RectTransform Rect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = parent != null ? parent.gameObject.layer : 5;
            var rect = (RectTransform)go.transform;
            rect.SetParent(parent, false);
            return rect;
        }

        public static RectTransform Stretch(this RectTransform rect, float left = 0, float top = 0,
            float right = 0, float bottom = 0)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = new Vector2(left, bottom);
            rect.offsetMax = new Vector2(-right, -top);
            return rect;
        }

        // Pins a rect to the top edge of its parent: y and height in pixels from the top.
        public static RectTransform Top(this RectTransform rect, float y, float height,
            float left = 0, float right = 0)
        {
            rect.anchorMin = new Vector2(0, 1);
            rect.anchorMax = new Vector2(1, 1);
            rect.pivot = new Vector2(0.5f, 1);
            rect.offsetMin = new Vector2(left, -y - height);
            rect.offsetMax = new Vector2(-right, -y);
            return rect;
        }

        public static RectTransform Bottom(this RectTransform rect, float y, float height,
            float left = 0, float right = 0)
        {
            rect.anchorMin = new Vector2(0, 0);
            rect.anchorMax = new Vector2(1, 0);
            rect.pivot = new Vector2(0.5f, 0);
            rect.offsetMin = new Vector2(left, y);
            rect.offsetMax = new Vector2(-right, y + height);
            return rect;
        }

        // Fixed-size rect placed by its centre relative to an anchor point of the parent.
        public static RectTransform Place(this RectTransform rect, Vector2 anchor, Vector2 position,
            Vector2 size)
        {
            rect.anchorMin = rect.anchorMax = anchor;
            rect.pivot = new Vector2(0.5f, 0.5f);
            rect.anchoredPosition = position;
            rect.sizeDelta = size;
            return rect;
        }

        // ---------- widgets ----------

        public static Image Panel(Transform parent, string name, Color color, float radius = 0f)
        {
            var image = Rect(name, parent).gameObject.AddComponent<Image>();
            image.color = color;
            image.raycastTarget = false;
            if (radius > 0f)
                SetRadius(image, radius);
            return image;
        }

        public static void SetRadius(Image image, float radius)
        {
            image.sprite = Rounded;
            image.type = Image.Type.Sliced;
            image.pixelsPerUnitMultiplier = RoundedRadius / Mathf.Max(1f, radius);
        }

        public static Image Picture(Transform parent, string name, Sprite sprite, Color? tint = null)
        {
            var image = Rect(name, parent).gameObject.AddComponent<Image>();
            image.sprite = sprite;
            image.preserveAspect = true;
            image.color = tint ?? Color.white;
            image.raycastTarget = false;
            return image;
        }

        public static Text Label(Transform parent, string text, int size, Color color,
            TextAnchor anchor = TextAnchor.MiddleLeft, bool bold = false, bool heavyFont = false)
        {
            var label = Rect("Text", parent).gameObject.AddComponent<Text>();
            label.font = heavyFont ? Heavy : Regular;
            label.fontStyle = bold || heavyFont ? FontStyle.Bold : FontStyle.Normal;
            label.fontSize = size;
            label.color = color;
            label.alignment = anchor;
            label.text = text;
            label.horizontalOverflow = HorizontalWrapMode.Wrap;
            label.verticalOverflow = VerticalWrapMode.Overflow;
            label.raycastTarget = false;
            label.supportRichText = true;
            return label;
        }

        public static Button Button(Transform parent, string name, Color color, float radius,
            UnityAction onClick)
        {
            var image = Panel(parent, name, color, radius);
            image.raycastTarget = true;
            var button = image.gameObject.AddComponent<Button>();
            var colors = button.colors;
            colors.highlightedColor = new Color(0.92f, 0.92f, 0.92f);
            colors.pressedColor = new Color(0.75f, 0.75f, 0.75f);
            colors.disabledColor = new Color(0.7f, 0.7f, 0.7f, 0.6f);
            colors.fadeDuration = 0.06f;
            button.colors = colors;
            if (onClick != null)
                button.onClick.AddListener(onClick);
            return button;
        }

        public static Button TextButton(Transform parent, string text, Color color, Color textColor,
            int size, float radius, UnityAction onClick)
        {
            var button = Button(parent, "Button_" + text, color, radius, onClick);
            Label(button.transform, text, size, textColor, TextAnchor.MiddleCenter, true)
                .rectTransform.Stretch(6, 0, 6, 0);
            return button;
        }

        // Invisible clickable area over an existing rect.
        public static Button HitArea(Transform parent, string name, UnityAction onClick)
        {
            var button = Button(parent, name, new Color(1, 1, 1, 0), 0, onClick);
            button.transition = Selectable.Transition.None;
            return button;
        }

        public static ScrollRect Scroll(Transform parent, string name, out RectTransform content,
            float spacing = 0f, RectOffset padding = null)
        {
            var root = Rect(name, parent);
            var scroll = root.gameObject.AddComponent<ScrollRect>();
            var viewport = Rect("Viewport", root).Stretch();
            viewport.gameObject.AddComponent<RectMask2D>();
            var hit = viewport.gameObject.AddComponent<Image>();
            hit.color = new Color(0, 0, 0, 0);
            content = Rect("Content", viewport);
            content.anchorMin = new Vector2(0, 1);
            content.anchorMax = new Vector2(1, 1);
            content.pivot = new Vector2(0.5f, 1);
            content.offsetMin = content.offsetMax = Vector2.zero;
            var layout = content.gameObject.AddComponent<VerticalLayoutGroup>();
            layout.spacing = spacing;
            layout.padding = padding ?? new RectOffset(0, 0, 0, 0);
            layout.childControlWidth = true;
            layout.childControlHeight = true;
            layout.childForceExpandWidth = true;
            layout.childForceExpandHeight = false;
            content.gameObject.AddComponent<ContentSizeFitter>().verticalFit =
                ContentSizeFitter.FitMode.PreferredSize;
            scroll.viewport = viewport;
            scroll.content = content;
            scroll.horizontal = false;
            scroll.movementType = ScrollRect.MovementType.Clamped;
            scroll.scrollSensitivity = 40f;
            scroll.inertia = true;
            return scroll;
        }

        public static LayoutElement Height(GameObject go, float height)
        {
            if (!go.TryGetComponent(out LayoutElement element))
                element = go.AddComponent<LayoutElement>();
            element.minHeight = element.preferredHeight = height;
            return element;
        }

        public static void Clear(Transform parent)
        {
            // Deactivate first: layout groups ignore inactive children before Destroy completes.
            for (int i = parent.childCount - 1; i >= 0; i--)
            {
                var child = parent.GetChild(i).gameObject;
                child.SetActive(false);
                UnityEngine.Object.Destroy(child);
            }
        }

        // Standard app header that also sits under the status bar.
        public static Text Header(RectTransform root, string title, Color color, out Text subtitle,
            UnityAction back)
        {
            var bar = Panel(root, "Header", color);
            bar.rectTransform.Top(0, PhoneLayout.HeaderHeight);
            var titleLabel = Label(bar.transform, title, 24, White, TextAnchor.MiddleLeft, false, true);
            titleLabel.rectTransform.Top(PhoneLayout.StatusHeight + 2, 32, back != null ? 56 : 18, 12);
            subtitle = Label(bar.transform, "", 14, new Color(1, 1, 1, 0.72f));
            subtitle.rectTransform.Top(PhoneLayout.StatusHeight + 34, 20, back != null ? 57 : 19, 12);
            if (back != null)
            {
                var button = HitArea(bar.transform, "Back", back);
                ((RectTransform)button.transform).Place(new Vector2(0, 1),
                    new Vector2(28, -PhoneLayout.StatusHeight - 28), new Vector2(52, 52));
                Label(button.transform, "‹", 44, White, TextAnchor.MiddleCenter)
                    .rectTransform.Stretch(0, -6, 0, 6);
            }
            return titleLabel;
        }

        public static string Money(int amount) =>
            (amount < 0 ? "−$" : "$") + Mathf.Abs(amount).ToString("N0",
                System.Globalization.CultureInfo.InvariantCulture);
    }

    public static class PhoneLayout
    {
        public const float Width = 392f;
        public const float Height = 852f;
        public const float StatusHeight = 30f;
        public const float HeaderHeight = 92f;
    }
}
