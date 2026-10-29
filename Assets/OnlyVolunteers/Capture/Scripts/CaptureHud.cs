using OnlyVolunteers.Phone;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Capture
{
    /// <summary>Stage A first-person HUD, built in code (uGUI, 1920×1080 reference like the operation HUD): the field-kit
    /// hotbar (Z ties, X anesthesia, C blood), a card for the captured NPC under the crosshair, a progress ring for holds,
    /// the anesthesia dose bar, toasts and one hint line. Hidden while the operation table view owns the screen.</summary>
    public sealed class CaptureHud : MonoBehaviour
    {
        public static readonly Color Good = PhoneUi.Hex("#5BE07A"), Warn = PhoneUi.Hex("#FFB13B"), Bad = PhoneUi.Hex("#FF4D5E"),
            Neutral = PhoneUi.Hex("#F2F4F7"), Muted = PhoneUi.Hex("#9AA3AE"), Sleep = PhoneUi.Hex("#7FB2FF");
        private static readonly Color PanelColor = new Color(0.07f, 0.08f, 0.1f, 0.82f);

        private Canvas canvas;
        private CanvasGroup group;
        private readonly Image[] slotBg = new Image[3];
        private readonly Text[] slotKey = new Text[3], slotName = new Text[3], slotInfo = new Text[3];
        private readonly Image[] slotBar = new Image[3];
        private RectTransform card;
        private Text cardTitle, cardBody;
        private RectTransform ring;
        private Image ringFill;
        private Text ringLabel;
        private RectTransform doseBar;
        private Image doseFill, doseOk, doseOver;
        private Text toastText;
        private float toastUntil;
        private Text hintText;
        private Text cornerText;

        public static CaptureHud Create()
        {
            var go = new GameObject("[Capture] HUD");
            DontDestroyOnLoad(go);
            return go.AddComponent<CaptureHud>();
        }

        private void Awake() => Build();

        private void Build()
        {
            var go = new GameObject("[Capture] Canvas", typeof(Canvas), typeof(CanvasScaler));
            go.transform.SetParent(transform, false);
            canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 35;
            var scaler = go.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;
            var root = (RectTransform)go.transform;
            group = go.AddComponent<CanvasGroup>();
            group.blocksRaycasts = false;
            group.interactable = false;

            // hotbar
            var bar = PhoneUi.Rect("Hotbar", root);
            bar.anchorMin = bar.anchorMax = new Vector2(0.5f, 0f);
            bar.pivot = new Vector2(0.5f, 0f);
            bar.anchoredPosition = new Vector2(0, 108);
            bar.sizeDelta = new Vector2(3 * 214 + 2 * 10, 74);
            string[] keys = { "Z", "X", "C" };
            for (int i = 0; i < 3; i++)
            {
                var slot = PhoneUi.Rect("Slot" + i, bar);
                slot.anchorMin = slot.anchorMax = new Vector2(0f, 0.5f);
                slot.pivot = new Vector2(0f, 0.5f);
                slot.anchoredPosition = new Vector2(i * 224, 0);
                slot.sizeDelta = new Vector2(214, 74);
                slotBg[i] = slot.gameObject.AddComponent<Image>();
                PhoneUi.SetRadius(slotBg[i], 16);
                slotBg[i].color = PanelColor;
                slotBg[i].raycastTarget = false;
                slotKey[i] = PhoneUi.Label(slot, keys[i], 26, Neutral, TextAnchor.MiddleCenter, true);
                Place(slotKey[i].rectTransform, new Vector2(0, 0.5f), new Vector2(26, 0), new Vector2(40, 60));
                slotName[i] = PhoneUi.Label(slot, "", 21, Neutral, TextAnchor.UpperLeft, true);
                Place(slotName[i].rectTransform, new Vector2(0, 1), new Vector2(124, -20), new Vector2(160, 30));
                slotInfo[i] = PhoneUi.Label(slot, "", 17, Muted, TextAnchor.UpperLeft);
                Place(slotInfo[i].rectTransform, new Vector2(0, 1), new Vector2(124, -46), new Vector2(160, 24));
                var back = PhoneUi.Panel(slot, "BarBack", new Color(1, 1, 1, 0.12f), 3);
                Place(back.rectTransform, new Vector2(0, 0), new Vector2(124, 7), new Vector2(160, 5));
                slotBar[i] = PhoneUi.Panel(slot, "Bar", Good, 3);
                slotBar[i].rectTransform.anchorMin = slotBar[i].rectTransform.anchorMax = new Vector2(0, 0);
                slotBar[i].rectTransform.pivot = new Vector2(0, 0.5f);
                slotBar[i].rectTransform.anchoredPosition = new Vector2(44, 7);
                slotBar[i].rectTransform.sizeDelta = new Vector2(160, 5);
            }
            // Round 2 (Fedya): the field tools live in the inventory hotbar (one kit slot); the old Z/X/C cards are not shown.
            bar.gameObject.SetActive(false);

            // target card (right of the crosshair)
            card = PhoneUi.Rect("Card", root);
            card.anchorMin = card.anchorMax = new Vector2(0.5f, 0.5f);
            card.pivot = new Vector2(0f, 0.5f);
            card.anchoredPosition = new Vector2(60, -10);
            card.sizeDelta = new Vector2(360, 170);
            var cbg = card.gameObject.AddComponent<Image>();
            PhoneUi.SetRadius(cbg, 16);
            cbg.color = PanelColor;
            cbg.raycastTarget = false;
            cardTitle = PhoneUi.Label(card, "", 22, Neutral, TextAnchor.UpperLeft, true);
            Place(cardTitle.rectTransform, new Vector2(0, 1), new Vector2(180, -22), new Vector2(330, 30));
            cardBody = PhoneUi.Label(card, "", 18, Neutral, TextAnchor.UpperLeft);
            Place(cardBody.rectTransform, new Vector2(0, 1), new Vector2(180, -100), new Vector2(330, 120));

            // hold ring
            ring = PhoneUi.Rect("Ring", root);
            ring.anchorMin = ring.anchorMax = new Vector2(0.5f, 0.5f);
            ring.sizeDelta = new Vector2(78, 78);
            var ringBack = ring.gameObject.AddComponent<Image>();
            ringBack.sprite = PhoneUi.Circle;
            ringBack.color = new Color(0, 0, 0, 0.35f);
            ringBack.raycastTarget = false;
            ringFill = PhoneUi.Picture(ring, "Fill", PhoneUi.Circle, Good);
            ringFill.rectTransform.Stretch();
            ringFill.type = Image.Type.Filled;
            ringFill.fillMethod = Image.FillMethod.Radial360;
            ringFill.fillOrigin = 2;
            ringFill.preserveAspect = false;
            var hole = PhoneUi.Picture(ring, "Hole", PhoneUi.Circle, new Color(0.07f, 0.08f, 0.1f, 0.85f));
            hole.rectTransform.Stretch(9, 9, 9, 9);
            ringLabel = PhoneUi.Label(ring, "", 18, Neutral, TextAnchor.MiddleCenter, true);
            Place(ringLabel.rectTransform, new Vector2(0.5f, 0f), new Vector2(0, -22), new Vector2(300, 28));

            // dose bar (under the crosshair while the anesthesia syringe is out)
            doseBar = PhoneUi.Rect("Dose", root);
            doseBar.anchorMin = doseBar.anchorMax = new Vector2(0.5f, 0.5f);
            doseBar.anchoredPosition = new Vector2(0, -92);
            doseBar.sizeDelta = new Vector2(300, 16);
            var db = doseBar.gameObject.AddComponent<Image>();
            PhoneUi.SetRadius(db, 8);
            db.color = new Color(0, 0, 0, 0.55f);
            db.raycastTarget = false;
            doseOk = PhoneUi.Panel(doseBar, "Ok", new Color(0.36f, 0.88f, 0.48f, 0.35f));
            doseOver = PhoneUi.Panel(doseBar, "Over", new Color(1f, 0.3f, 0.35f, 0.35f));
            doseFill = PhoneUi.Panel(doseBar, "Fill", Sleep, 6);

            toastText = PhoneUi.Label(root, "", 30, Neutral, TextAnchor.MiddleCenter, true);
            Place(toastText.rectTransform, new Vector2(0.5f, 1f), new Vector2(0, -210), new Vector2(1400, 90));
            var outline = toastText.gameObject.AddComponent<Outline>();
            outline.effectColor = new Color(0, 0, 0, 0.8f);
            outline.effectDistance = new Vector2(2, -2);

            hintText = PhoneUi.Label(root, "", 21, Neutral, TextAnchor.MiddleCenter);
            Place(hintText.rectTransform, new Vector2(0.5f, 0f), new Vector2(0, 200), new Vector2(1400, 34));
            var hout = hintText.gameObject.AddComponent<Outline>();
            hout.effectColor = new Color(0, 0, 0, 0.8f);
            hout.effectDistance = new Vector2(1.5f, -1.5f);

            cornerText = PhoneUi.Label(root, "", 17, Muted, TextAnchor.UpperLeft);
            Place(cornerText.rectTransform, new Vector2(0f, 1f), new Vector2(330, -150), new Vector2(620, 140));
            var cout = cornerText.gameObject.AddComponent<Outline>();
            cout.effectColor = new Color(0, 0, 0, 0.7f);

            card.gameObject.SetActive(false);
            ring.gameObject.SetActive(false);
            doseBar.gameObject.SetActive(false);
        }

        private static void Place(RectTransform r, Vector2 anchor, Vector2 position, Vector2 size)
        {
            r.anchorMin = r.anchorMax = anchor;
            r.pivot = new Vector2(0.5f, 0.5f);
            r.anchoredPosition = position;
            r.sizeDelta = size;
        }

        public void SetVisible(bool visible) => group.alpha = visible ? 1f : 0f;
        public bool Visible => group.alpha > 0.5f;

        public void Slot(int i, string name, string info, float bar, Color barColor, bool selected, bool usable)
        {
            slotName[i].text = name;
            slotInfo[i].text = info;
            slotBar[i].rectTransform.sizeDelta = new Vector2(160f * Mathf.Clamp01(bar), 5);
            slotBar[i].color = barColor;
            slotBg[i].color = selected ? new Color(0.24f, 0.36f, 0.62f, 0.92f) : PanelColor;
            slotKey[i].color = usable ? Neutral : Muted;
        }

        public void Card(string title, string body)
        {
            bool on = !string.IsNullOrEmpty(title);
            card.gameObject.SetActive(on);
            if (!on) return;
            cardTitle.text = title;
            cardBody.text = body;
        }

        public void Ring(float progress, Color color, string label)
        {
            bool on = progress >= 0f;
            ring.gameObject.SetActive(on);
            if (!on) return;
            ringFill.fillAmount = Mathf.Clamp01(progress);
            ringFill.color = color;
            ringLabel.text = label;
        }

        /// <summary>residual against the suitable window and the overdose line (operation tuning units).</summary>
        public void Dose(bool on, float residual, float suitableMin, float suitableMax, float overdose)
        {
            doseBar.gameObject.SetActive(on);
            if (!on) return;
            float full = overdose * 1.15f;
            Span(doseOk.rectTransform, suitableMin / full, suitableMax / full);
            Span(doseOver.rectTransform, overdose / full, 1f);
            Span(doseFill.rectTransform, 0f, Mathf.Clamp01(residual / full));
            doseFill.color = residual > overdose ? Bad : residual > suitableMax ? Warn : residual >= suitableMin ? Good : Sleep;
        }

        private static void Span(RectTransform r, float a, float b)
        {
            r.anchorMin = new Vector2(Mathf.Clamp01(a), 0f);
            r.anchorMax = new Vector2(Mathf.Clamp01(b), 1f);
            r.offsetMin = r.offsetMax = Vector2.zero;
        }

        public void Toast(string text, Color color, float seconds = 3f)
        {
            toastText.text = text;
            toastText.color = color;
            toastUntil = Time.unscaledTime + seconds;
        }

        // ---------- WP01: the save prompt (a save that would not load) ----------

        private GameObject promptCanvas;
        private Text promptTitle, promptBody;

        /// <summary>A centred panel on its own canvas (shown even while the HUD group is hidden): the reason a save did not
        /// load and the keys of the choices. Keyboard only; the director reads the keys.</summary>
        public void Prompt(string title, string body)
        {
            if (promptCanvas == null) BuildPrompt();
            promptTitle.text = title ?? "";
            promptBody.text = body ?? "";
            promptCanvas.SetActive(true);
        }

        public void HidePrompt()
        {
            if (promptCanvas != null) promptCanvas.SetActive(false);
        }

        public bool PromptVisible => promptCanvas != null && promptCanvas.activeSelf;
        public string PromptText => promptCanvas != null ? promptTitle.text + "\n" + promptBody.text : "";

        private void BuildPrompt()
        {
            promptCanvas = new GameObject("[Capture] Save prompt", typeof(Canvas), typeof(CanvasScaler));
            promptCanvas.transform.SetParent(transform, false);
            var c = promptCanvas.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            c.sortingOrder = 120;
            var scaler = promptCanvas.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;
            var root = (RectTransform)promptCanvas.transform;
            var shade = PhoneUi.Panel(root, "Shade", new Color(0f, 0f, 0f, 0.55f));
            shade.rectTransform.Stretch();
            shade.raycastTarget = false;
            var panel = PhoneUi.Panel(root, "Panel", new Color(0.07f, 0.08f, 0.1f, 0.94f), 18);
            panel.raycastTarget = false;
            Place(panel.rectTransform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1060, 470));
            promptTitle = PhoneUi.Label(panel.rectTransform, "", 34, Warn, TextAnchor.UpperLeft, true);
            Place(promptTitle.rectTransform, new Vector2(0.5f, 1f), new Vector2(0, -46), new Vector2(980, 50));
            promptBody = PhoneUi.Label(panel.rectTransform, "", 23, Neutral, TextAnchor.UpperLeft);
            promptBody.supportRichText = true;
            Place(promptBody.rectTransform, new Vector2(0.5f, 1f), new Vector2(0, -260), new Vector2(980, 360));
            promptCanvas.SetActive(false);
        }

        public void Hint(string text) => hintText.text = text ?? "";
        public void Corner(string text) => cornerText.text = text ?? "";
        public string LastHint => hintText != null ? hintText.text : "";
        public string LastToast => toastText != null ? toastText.text : "";

        private void Update()
        {
            float left = toastUntil - Time.unscaledTime;
            var c = toastText.color;
            c.a = Mathf.Clamp01(left / 0.4f);
            toastText.color = c;
        }

        /// <summary>For captures in batch mode (Screen Space Overlay is not in camera renders).</summary>
        public void RenderInto(Camera camera)
        {
            if (camera == null)
            {
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                return;
            }
            canvas.renderMode = RenderMode.ScreenSpaceCamera;
            canvas.worldCamera = camera;
            canvas.planeDistance = 0.4f;
        }
    }
}
