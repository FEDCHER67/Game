using System.Globalization;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Minimal hotbar for the local owner: a thin, mostly transparent row at the bottom edge that
    /// fades out after a few seconds without changes. Built in code at runtime, so it needs no
    /// prefab or scene edits; only the owner's instance creates a canvas.
    /// </summary>
    public sealed class InventoryHud : MonoBehaviour
    {
        [Tooltip("NetworkInventory or LocalInventory. Defaults to the one on this object or a parent.")]
        [SerializeField] private MonoBehaviour inventorySource;
        private IInventoryView inventory;

        [Header("Layout (reference 1920x1080)")]
        [SerializeField, Min(24f)] private float slotSize = 46f;
        [SerializeField, Min(0f)] private float spacing = 6f;
        [SerializeField, Min(0f)] private float bottomMargin = 18f;

        [Header("Look")]
        [SerializeField, Range(0f, 1f)] private float backgroundAlpha = 0.18f;
        [SerializeField, Range(0f, 1f)] private float selectedBackgroundAlpha = 0.26f;
        [SerializeField, Range(0f, 1f)] private float outlineAlpha = 0.16f;
        [SerializeField, Range(0f, 1f)] private float selectedOutlineAlpha = 0.5f;
        [SerializeField, Range(0f, 1f)] private float contentAlpha = 0.8f;

        [Header("Fade")]
        [SerializeField, Min(0f)] private float visibleSeconds = 3f;
        [SerializeField, Min(0.01f)] private float fadeSeconds = 0.6f;
        [Tooltip("Alpha of the whole hotbar after fading. 0 hides it completely.")]
        [SerializeField, Range(0f, 1f)] private float idleAlpha = 0f;

        private sealed class SlotView
        {
            public Image Background;
            public Image[] Outline;
            public Image Icon;
            public Text Label;
            public Text Count;
        }

        private GameObject canvasObject;
        private CanvasGroup group;
        private RectTransform bar;
        private SlotView[] views = new SlotView[0];
        private Text itemName;
        private Text cashText;
        private Font font;
        private bool dirty;
        private float lastActivity;
        private int lastSelected = -1;

        private void Awake()
        {
            inventory = inventorySource as IInventoryView ?? GetComponentInParent<IInventoryView>();
        }

        private void OnEnable()
        {
            if (inventory != null) inventory.Changed += MarkDirty;
        }

        private void OnDisable()
        {
            if (inventory != null) inventory.Changed -= MarkDirty;
            if (canvasObject != null) canvasObject.SetActive(false);
        }

        private void OnDestroy()
        {
            if (canvasObject != null) Destroy(canvasObject);
        }

        private void MarkDirty()
        {
            dirty = true;
            lastActivity = Time.unscaledTime;
        }

        private void LateUpdate()
        {
            bool show = inventory != null && inventory.IsLocalOwner && inventory.SlotCount > 0;
            if (!show)
            {
                if (canvasObject != null && canvasObject.activeSelf) canvasObject.SetActive(false);
                return;
            }
            if (canvasObject == null) Build();
            if (!canvasObject.activeSelf)
            {
                canvasObject.SetActive(true);
                MarkDirty();
            }
            if (views.Length != inventory.SlotCount) RebuildSlots();
            if (dirty) Refresh();

            float idle = Time.unscaledTime - lastActivity - visibleSeconds;
            group.alpha = idle <= 0f ? 1f : Mathf.Lerp(1f, idleAlpha, idle / fadeSeconds);
        }

        private void Build()
        {
            font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            canvasObject = new GameObject("[Inventory] HUD", typeof(Canvas), typeof(CanvasScaler), typeof(CanvasGroup));
            var canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = canvasObject.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;
            group = canvasObject.GetComponent<CanvasGroup>();
            group.interactable = false;
            group.blocksRaycasts = false;

            bar = NewRect("Hotbar", canvasObject.transform);
            bar.anchorMin = bar.anchorMax = new Vector2(0.5f, 0f);
            bar.pivot = new Vector2(0.5f, 0f);
            bar.anchoredPosition = new Vector2(0f, bottomMargin);

            itemName = NewText("SelectedName", bar, 13, TextAnchor.LowerCenter);
            var nameRect = itemName.rectTransform;
            nameRect.anchorMin = new Vector2(0f, 1f);
            nameRect.anchorMax = new Vector2(1f, 1f);
            nameRect.pivot = new Vector2(0.5f, 0f);
            nameRect.sizeDelta = new Vector2(240f, 18f);
            nameRect.anchoredPosition = new Vector2(0f, 4f);

            cashText = NewText("Cash", bar, 13, TextAnchor.MiddleLeft);
            var cashRect = cashText.rectTransform;
            cashRect.anchorMin = cashRect.anchorMax = new Vector2(1f, 0.5f);
            cashRect.pivot = new Vector2(0f, 0.5f);
            cashRect.sizeDelta = new Vector2(120f, slotSize);
            cashRect.anchoredPosition = new Vector2(spacing * 2f, 0f);
        }

        private void RebuildSlots()
        {
            foreach (SlotView view in views)
                Destroy(view.Background.gameObject);
            int count = inventory.SlotCount;
            views = new SlotView[count];
            bar.sizeDelta = new Vector2(count * slotSize + (count - 1) * spacing, slotSize);
            for (int i = 0; i < count; i++)
                views[i] = NewSlot(i);
            lastSelected = -1;
            dirty = true;
        }

        private SlotView NewSlot(int index)
        {
            RectTransform root = NewRect($"Slot{index + 1}", bar);
            root.anchorMin = root.anchorMax = root.pivot = new Vector2(0f, 0f);
            root.sizeDelta = new Vector2(slotSize, slotSize);
            root.anchoredPosition = new Vector2(index * (slotSize + spacing), 0f);
            var view = new SlotView { Background = root.gameObject.AddComponent<Image>() };
            view.Background.raycastTarget = false;

            // Four 1 px lines instead of an Outline effect, which would double the fill alpha.
            view.Outline = new Image[4];
            for (int side = 0; side < 4; side++)
            {
                RectTransform line = NewRect("Line", root);
                bool horizontal = side < 2;
                line.anchorMin = horizontal ? new Vector2(0f, side) : new Vector2(side - 2, 0f);
                line.anchorMax = horizontal ? new Vector2(1f, side) : new Vector2(side - 2, 1f);
                line.pivot = new Vector2(0.5f, 0.5f);
                line.sizeDelta = horizontal ? new Vector2(0f, 1f) : new Vector2(1f, 0f);
                line.anchoredPosition = Vector2.zero;
                view.Outline[side] = line.gameObject.AddComponent<Image>();
                view.Outline[side].raycastTarget = false;
            }

            RectTransform icon = NewRect("Icon", root);
            icon.anchorMin = Vector2.zero;
            icon.anchorMax = Vector2.one;
            icon.offsetMin = new Vector2(7f, 7f);
            icon.offsetMax = new Vector2(-7f, -7f);
            view.Icon = icon.gameObject.AddComponent<Image>();
            view.Icon.preserveAspect = true;
            view.Icon.raycastTarget = false;

            view.Label = NewText("Label", root, 13, TextAnchor.MiddleCenter);
            Stretch(view.Label.rectTransform, 2f);
            view.Count = NewText("Count", root, 11, TextAnchor.LowerRight);
            Stretch(view.Count.rectTransform, 3f);
            return view;
        }

        private void Refresh()
        {
            dirty = false;
            ItemDatabase database = inventory.Database;
            int selected = inventory.SelectedIndex;
            for (int i = 0; i < views.Length; i++)
            {
                SlotView view = views[i];
                ItemStack stack = inventory.GetSlot(i);
                ItemDefinition item = stack.IsEmpty || database == null ? null : database.Get(stack.ItemId);
                bool isSelected = i == selected;

                view.Background.color = new Color(0f, 0f, 0f, isSelected ? selectedBackgroundAlpha : backgroundAlpha);
                var line = new Color(1f, 1f, 1f, isSelected ? selectedOutlineAlpha : outlineAlpha);
                foreach (Image side in view.Outline) side.color = line;

                bool hasIcon = item != null && item.Icon != null;
                view.Icon.enabled = hasIcon;
                view.Icon.sprite = hasIcon ? item.Icon : null;
                view.Icon.color = new Color(1f, 1f, 1f, isSelected ? 1f : contentAlpha);
                view.Label.text = item != null && !hasIcon ? item.ShortLabel : string.Empty;
                view.Label.color = new Color(1f, 1f, 1f, contentAlpha);
                view.Count.text = !stack.IsEmpty && stack.Count > 1 ? stack.Count.ToString() : string.Empty;
                view.Count.color = new Color(1f, 1f, 1f, contentAlpha);
            }

            ItemStack current = inventory.GetSlot(selected);
            ItemDefinition currentItem = current.IsEmpty || database == null ? null : database.Get(current.ItemId);
            itemName.text = currentItem != null
                ? $"{currentItem.DisplayName}  ${current.UnitValue.ToString("N0", CultureInfo.InvariantCulture)}"
                : string.Empty;
            itemName.color = new Color(1f, 1f, 1f, contentAlpha * 0.85f);
            cashText.text = "$" + inventory.Cash.ToString("N0", CultureInfo.InvariantCulture);
            cashText.color = new Color(1f, 1f, 1f, contentAlpha * 0.7f);
            if (selected != lastSelected)
            {
                lastSelected = selected;
                lastActivity = Time.unscaledTime;
            }
        }

        private static RectTransform NewRect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rect = (RectTransform)go.transform;
            rect.SetParent(parent, false);
            return rect;
        }

        private Text NewText(string name, Transform parent, int size, TextAnchor anchor)
        {
            var text = NewRect(name, parent).gameObject.AddComponent<Text>();
            text.font = font;
            text.fontSize = size;
            text.alignment = anchor;
            text.raycastTarget = false;
            text.horizontalOverflow = HorizontalWrapMode.Overflow;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            return text;
        }

        private static void Stretch(RectTransform rect, float inset)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = new Vector2(inset, inset);
            rect.offsetMax = new Vector2(-inset, -inset);
        }
    }
}
