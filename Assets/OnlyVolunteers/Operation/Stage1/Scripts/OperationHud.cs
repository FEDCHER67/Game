using System;
using System.Collections.Generic;
using OnlyVolunteers.Phone;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Operation HUD, uGUI built in code (no TextMeshPro in the project; Segoe UI via PhoneUi). Reference
    /// 1920x1080, scales with the screen. Patient card, panic/death banners, hotbar, one context hint at the cursor,
    /// progress ring, pull tension, other players' cursors, toasts and the patient's speech bubble.</summary>
    [DefaultExecutionOrder(12000)] // after OperationTableView placed the camera this frame
    public sealed class OperationHud : MonoBehaviour
    {
        private OperationTableView view;
        private NetworkOperationTable table;
        private Canvas canvas;
        private RectTransform root;
        private CanvasGroup tableGroup;
        // card
        private Text stateText, idText, sleepLabel, bloodLabel, strapLabel;
        private Image[] sleepPills = new Image[3];
        private Image[] drops = new Image[3];
        private Image[] strapBars = new Image[5];
        private Text[] organChips = new Text[3];
        private Image[] organChipBg = new Image[3];
        // banners
        private RectTransform panic; private Text panicText; private Image panicRing; private Text panicSeconds;
        private RectTransform dead; private Text deadText;
        // hotbar
        private readonly Image[] slotBg = new Image[4];
        private readonly Image[] slotFrame = new Image[4];
        private readonly Image[] slotFill = new Image[4];
        private readonly Text[] slotOwner = new Text[4];
        private readonly Text[] slotLabel = new Text[4];
        private RectTransform hotbar;
        // cursor
        private RectTransform reticle; private Image reticleImage;
        private RectTransform hintPill; private Text hintText; private Image hintBg;
        private RectTransform ring; private Image ringFill; private Image ringBack;
        private RectTransform tension; private Image tensionFill;
        private RectTransform card2; private Text card2Title, card2Tier, card2Price;
        private RectTransform bubble; private Text bubbleText;
        private RectTransform prompt; private Text promptText;
        private Text help;
        private Image flash; private Color flashColor; private float flashAt = -10f;
        private readonly Dictionary<int, (RectTransform rt, Image img, Text label)> remote = new();
        private readonly List<(RectTransform rt, Text text, float born, Vector3 world, bool isWorld)> toasts = new();
        private string hint = ""; private HintTone hintTone;
        private OpHint serverHint; private int serverArg; private float serverAt = -10f;
        private Sprite iconHand, iconAnesthesia, iconBlood, iconScalpel, ringSprite, dropSprite;

        public string CurrentHint => hint;
        public HintTone CurrentTone => hintTone;
        public string StateLine => stateText != null ? stateText.text : "";
        public bool PanicVisible => panic != null && panic.gameObject.activeSelf;
        public bool DeadVisible => dead != null && dead.gameObject.activeSelf;
        public string LastToast { get; private set; } = "";
        public Canvas Canvas => canvas;
        public string DebugLine { get; private set; } = "";

        private static Color C(string hex, float a = 1f) => PhoneUi.Hex(hex, a);
        private static readonly Color Panel = new(0.07f, 0.08f, 0.1f, 0.84f);
        private static readonly Color Good = C("#5BE07A"), Warn = C("#FFB13B"), Bad = C("#FF4D5E"), Neutral = C("#F2F4F7"), Muted = C("#9AA3AE");
        public static Color ToneColor(HintTone t) => t == HintTone.Good ? Good : t == HintTone.Warn ? Warn : t == HintTone.Bad ? Bad : Neutral;

        public void Bind(OperationTableView owner)
        {
            view = owner; table = owner.Table;
            BuildIcons();
            Build();
        }

        // ---------- build ----------
        private void Build()
        {
            var go = new GameObject("[Operation] Canvas", typeof(Canvas), typeof(CanvasScaler));
            go.transform.SetParent(transform, false);
            canvas = go.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 40;
            var scaler = go.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = 0.5f;
            root = (RectTransform)go.transform;
            var tableRoot = PhoneUi.Rect("Table", root).Stretch();
            tableGroup = tableRoot.gameObject.AddComponent<CanvasGroup>(); tableGroup.blocksRaycasts = false; tableGroup.interactable = false;

            BuildCard(tableRoot);
            BuildBanners(tableRoot);
            BuildHotbar(tableRoot);
            help = Label(tableRoot, "E / Esc — отойти   ·   колесо — приблизить   ·   ПКМ — положить", 17, Muted, TextAnchor.UpperRight);
            Place(help.rectTransform, new Vector2(1, 1), new Vector2(-24, -24), new Vector2(760, 30), new Vector2(1, 1));

            // remote cursors are created on demand under tableRoot
            reticle = PhoneUi.Rect("Reticle", tableRoot); reticle.sizeDelta = new Vector2(30, 30);
            reticleImage = reticle.gameObject.AddComponent<Image>(); reticleImage.sprite = ringSprite; reticleImage.raycastTarget = false;
            var dot = PhoneUi.Picture(reticle, "Dot", PhoneUi.Circle, Color.white); dot.rectTransform.sizeDelta = new Vector2(6, 6);

            ring = PhoneUi.Rect("ProgressRing", tableRoot); ring.sizeDelta = new Vector2(74, 74);
            ringBack = ring.gameObject.AddComponent<Image>(); ringBack.sprite = ringSprite; ringBack.color = new Color(0, 0, 0, 0.45f); ringBack.raycastTarget = false;
            ringFill = PhoneUi.Picture(ring, "Fill", ringSprite, Bad); ringFill.rectTransform.Stretch(); ringFill.type = Image.Type.Filled;
            ringFill.fillMethod = Image.FillMethod.Radial360; ringFill.fillOrigin = 2; ringFill.fillClockwise = true; ringFill.preserveAspect = false;

            tension = PhoneUi.Rect("Tension", tableRoot); tension.sizeDelta = new Vector2(26, 150);
            var tframe = PhoneUi.Panel(tension, "Frame", new Color(1, 1, 1, 0.9f), 13); tframe.rectTransform.Stretch(-3, -3, -3, -3);
            var tb = PhoneUi.Panel(tension, "Back", new Color(0.05f, 0.06f, 0.08f, 0.9f), 11); tb.rectTransform.Stretch();
            tensionFill = PhoneUi.Panel(tension, "Fill", Good, 8); tensionFill.rectTransform.anchorMin = new Vector2(0, 0); tensionFill.rectTransform.anchorMax = new Vector2(1, 0);
            tensionFill.rectTransform.pivot = new Vector2(0.5f, 0); tensionFill.rectTransform.offsetMin = new Vector2(4, 4); tensionFill.rectTransform.offsetMax = new Vector2(-4, 4);
            var tl = Label(tension, "тяни\nплавно", 15, Neutral, TextAnchor.UpperCenter, true); Place(tl.rectTransform, new Vector2(0.5f, 1), new Vector2(0, 46), new Vector2(90, 44), new Vector2(0.5f, 1));

            hintPill = PhoneUi.Rect("Hint", tableRoot); hintPill.pivot = new Vector2(0, 1);
            hintBg = hintPill.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(hintBg, 14); hintBg.color = new Color(0.05f, 0.06f, 0.08f, 0.82f); hintBg.raycastTarget = false;
            hintText = Label(hintPill, "", 22, Neutral, TextAnchor.MiddleLeft); hintText.rectTransform.Stretch(14, 4, 14, 4);
            hintText.horizontalOverflow = HorizontalWrapMode.Overflow;

            card2 = PhoneUi.Rect("OrganCard", tableRoot); card2.pivot = new Vector2(0, 0); card2.sizeDelta = new Vector2(300, 112);
            var cbg = card2.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(cbg, 16); cbg.color = Panel; cbg.raycastTarget = false;
            card2Title = Label(card2, "", 22, Neutral, TextAnchor.UpperLeft, true); Place(card2Title.rectTransform, new Vector2(0, 1), new Vector2(16, -10), new Vector2(270, 30), new Vector2(0, 1));
            card2Tier = Label(card2, "", 30, Good, TextAnchor.UpperLeft, true); Place(card2Tier.rectTransform, new Vector2(0, 1), new Vector2(16, -42), new Vector2(270, 38), new Vector2(0, 1));
            card2Price = Label(card2, "", 18, Muted, TextAnchor.UpperLeft); Place(card2Price.rectTransform, new Vector2(0, 1), new Vector2(16, -82), new Vector2(270, 24), new Vector2(0, 1));

            bubble = PhoneUi.Rect("Bubble", tableRoot); bubble.pivot = new Vector2(0.5f, 0);
            var bb = bubble.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(bb, 18); bb.color = new Color(1, 1, 1, 0.93f); bb.raycastTarget = false;
            bubbleText = Label(bubble, "", 26, C("#1B1B22"), TextAnchor.MiddleCenter, true); bubbleText.rectTransform.Stretch(12, 4, 12, 4);

            flash = PhoneUi.Panel(root, "Flash", new Color(1, 0, 0, 0), 0); flash.rectTransform.Stretch();

            prompt = PhoneUi.Rect("Prompt", root); Place(prompt, new Vector2(0.5f, 0.5f), new Vector2(0, -110), new Vector2(380, 56), new Vector2(0.5f, 0.5f));
            var pb = prompt.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(pb, 28); pb.color = new Color(0.05f, 0.06f, 0.08f, 0.8f); pb.raycastTarget = false;
            promptText = Label(prompt, "<b>[E]</b>  Встать к столу", 26, Neutral, TextAnchor.MiddleCenter); promptText.rectTransform.Stretch();
        }

        private void BuildCard(RectTransform parent)
        {
            var card = PhoneUi.Rect("PatientCard", parent);
            Place(card, new Vector2(0, 1), new Vector2(24, -24), new Vector2(380, 262), new Vector2(0, 1));
            var bg = card.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(bg, 20); bg.color = Panel; bg.raycastTarget = false;
            var title = Label(card, "ПАЦИЕНТ", 16, Muted, TextAnchor.UpperLeft, true); Place(title.rectTransform, new Vector2(0, 1), new Vector2(20, -14), new Vector2(200, 22), new Vector2(0, 1));
            idText = Label(card, "", 14, Muted, TextAnchor.UpperRight); Place(idText.rectTransform, new Vector2(1, 1), new Vector2(-18, -15), new Vector2(160, 22), new Vector2(1, 1));
            stateText = Label(card, "", 34, Neutral, TextAnchor.UpperLeft, true); Place(stateText.rectTransform, new Vector2(0, 1), new Vector2(20, -36), new Vector2(350, 44), new Vector2(0, 1));
            stateText.font = PhoneUi.Heavy;

            sleepLabel = Label(card, "Сон", 17, Muted, TextAnchor.MiddleLeft); Place(sleepLabel.rectTransform, new Vector2(0, 1), new Vector2(20, -92), new Vector2(70, 24), new Vector2(0, 1));
            for (int i = 0; i < 3; i++)
            {
                sleepPills[i] = PhoneUi.Panel(card, "Sleep" + i, Muted, 6);
                Place(sleepPills[i].rectTransform, new Vector2(0, 1), new Vector2(92 + i * 34, -96), new Vector2(28, 14), new Vector2(0, 1));
            }
            bloodLabel = Label(card, "Кровь", 17, Muted, TextAnchor.MiddleLeft); Place(bloodLabel.rectTransform, new Vector2(0, 1), new Vector2(204, -92), new Vector2(70, 24), new Vector2(0, 1));
            for (int i = 0; i < 3; i++)
            {
                drops[i] = PhoneUi.Picture(card, "Drop" + i, dropSprite, Muted);
                Place(drops[i].rectTransform, new Vector2(0, 1), new Vector2(270 + i * 30, -88), new Vector2(22, 28), new Vector2(0, 1));
            }
            // Strap diagram: a tiny top-down patient (head up) with five straps.
            strapLabel = Label(card, "Ремни", 17, Muted, TextAnchor.MiddleLeft); Place(strapLabel.rectTransform, new Vector2(0, 1), new Vector2(20, -128), new Vector2(120, 24), new Vector2(0, 1));
            var fig = PhoneUi.Rect("Figure", card); Place(fig, new Vector2(0, 1), new Vector2(20, -154), new Vector2(110, 96), new Vector2(0, 1));
            Color body = new(0.55f, 0.6f, 0.68f, 0.55f);
            Box(fig, "Head", new Vector2(55, 86), new Vector2(18, 18), body, 9);
            Box(fig, "Torso", new Vector2(55, 58), new Vector2(30, 40), body, 8);
            Box(fig, "ArmL", new Vector2(29, 58), new Vector2(10, 38), body, 5);
            Box(fig, "ArmR", new Vector2(81, 58), new Vector2(10, 38), body, 5);
            Box(fig, "LegL", new Vector2(47, 20), new Vector2(12, 38), body, 6);
            Box(fig, "LegR", new Vector2(63, 20), new Vector2(12, 38), body, 6);
            // Patient's left is screen right in this top-down figure? Keep it simple: L on the left like a mirror-less chart.
            strapBars[0] = Box(fig, "StrapArmL", new Vector2(29, 50), new Vector2(18, 6), Bad, 3);
            strapBars[1] = Box(fig, "StrapArmR", new Vector2(81, 50), new Vector2(18, 6), Bad, 3);
            strapBars[2] = Box(fig, "StrapLegL", new Vector2(47, 12), new Vector2(18, 6), Bad, 3);
            strapBars[3] = Box(fig, "StrapLegR", new Vector2(63, 12), new Vector2(18, 6), Bad, 3);
            strapBars[4] = Box(fig, "StrapTorso", new Vector2(55, 42), new Vector2(40, 7), Bad, 3);
            for (int i = 0; i < 3; i++)
            {
                organChipBg[i] = PhoneUi.Panel(card, "Organ" + i, new Color(1, 1, 1, 0.08f), 10);
                Place(organChipBg[i].rectTransform, new Vector2(0, 1), new Vector2(146, -130 - i * 40), new Vector2(216, 34), new Vector2(0, 1));
                organChips[i] = Label(organChipBg[i].rectTransform, "", 16, Neutral, TextAnchor.MiddleLeft); organChips[i].rectTransform.Stretch(10, 0, 8, 0);
            }
        }
        private Image Box(RectTransform parent, string name, Vector2 center, Vector2 size, Color color, float radius)
        {
            var img = PhoneUi.Panel(parent, name, color, radius);
            img.rectTransform.anchorMin = img.rectTransform.anchorMax = Vector2.zero; img.rectTransform.pivot = new Vector2(0.5f, 0.5f);
            img.rectTransform.anchoredPosition = center; img.rectTransform.sizeDelta = size;
            return img;
        }

        private void BuildBanners(RectTransform parent)
        {
            panic = PhoneUi.Rect("Panic", parent); Place(panic, new Vector2(0.5f, 1), new Vector2(0, -26), new Vector2(960, 96), new Vector2(0.5f, 1));
            var pbg = panic.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(pbg, 26); pbg.color = new Color(0.55f, 0.03f, 0.08f, 0.9f); pbg.raycastTarget = false;
            panicText = Label(panic, "ПРОСЫПАЕТСЯ! Срочно наркоз!", 38, Color.white, TextAnchor.MiddleLeft, true); panicText.font = PhoneUi.Heavy;
            panicText.horizontalOverflow = HorizontalWrapMode.Overflow;
            panicText.rectTransform.Stretch(112, 0, 20, 0);
            var ringRoot = PhoneUi.Rect("Ring", panic); Place(ringRoot, new Vector2(0, 0.5f), new Vector2(54, 0), new Vector2(72, 72), new Vector2(0.5f, 0.5f));
            var back = ringRoot.gameObject.AddComponent<Image>(); back.sprite = ringSprite; back.color = new Color(0, 0, 0, 0.35f); back.raycastTarget = false;
            panicRing = PhoneUi.Picture(ringRoot, "Fill", ringSprite, Color.white); panicRing.rectTransform.Stretch(); panicRing.type = Image.Type.Filled;
            panicRing.fillMethod = Image.FillMethod.Radial360; panicRing.fillOrigin = 2; panicRing.preserveAspect = false;
            panicSeconds = Label(ringRoot, "8", 28, Color.white, TextAnchor.MiddleCenter, true); panicSeconds.rectTransform.Stretch();
            dead = PhoneUi.Rect("Dead", parent); Place(dead, new Vector2(0.5f, 1), new Vector2(0, -26), new Vector2(640, 92), new Vector2(0.5f, 1));
            var dbg = dead.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(dbg, 26); dbg.color = new Color(0.12f, 0.12f, 0.14f, 0.9f); dbg.raycastTarget = false;
            deadText = Label(dead, "", 30, Color.white, TextAnchor.MiddleCenter, true); deadText.rectTransform.Stretch(16, 6, 16, 6);
            panic.gameObject.SetActive(false); dead.gameObject.SetActive(false);
        }

        private void BuildHotbar(RectTransform parent)
        {
            hotbar = PhoneUi.Rect("Hotbar", parent);
            Place(hotbar, new Vector2(0.5f, 0), new Vector2(0, 24), new Vector2(4 * 104 + 3 * 12, 104), new Vector2(0.5f, 0));
            string[] labels = { "Руки", "Наркоз", "Кровь", "Скальпель" };
            Sprite[] icons = { iconHand, iconAnesthesia, iconBlood, iconScalpel };
            for (int i = 0; i < 4; i++)
            {
                slotFrame[i] = PhoneUi.Panel(hotbar, "Frame" + i, new Color(1, 1, 1, 0), 21);
                Place(slotFrame[i].rectTransform, new Vector2(0, 0), new Vector2(i * 116 + 52, 52), new Vector2(112, 112), new Vector2(0.5f, 0.5f));
                var slot = PhoneUi.Rect("Slot" + i, hotbar); Place(slot, new Vector2(0, 0), new Vector2(i * 116 + 52, 52), new Vector2(104, 104), new Vector2(0.5f, 0.5f));
                slotBg[i] = slot.gameObject.AddComponent<Image>(); PhoneUi.SetRadius(slotBg[i], 18); slotBg[i].color = Panel; slotBg[i].raycastTarget = false;
                var icon = PhoneUi.Picture(slot, "Icon", icons[i], Color.white); Place(icon.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0, 8), new Vector2(64, 64), new Vector2(0.5f, 0.5f));
                var key = Label(slot, (i + 1).ToString(), 18, Muted, TextAnchor.UpperLeft, true); Place(key.rectTransform, new Vector2(0, 1), new Vector2(10, -6), new Vector2(24, 24), new Vector2(0, 1));
                slotLabel[i] = Label(slot, labels[i], 15, Neutral, TextAnchor.LowerCenter); Place(slotLabel[i].rectTransform, new Vector2(0.5f, 0), new Vector2(0, 6), new Vector2(100, 20), new Vector2(0.5f, 0));
                slotOwner[i] = Label(slot, "", 16, Neutral, TextAnchor.UpperRight, true); Place(slotOwner[i].rectTransform, new Vector2(1, 1), new Vector2(-8, -6), new Vector2(44, 22), new Vector2(1, 1));
                if (i == 1 || i == 2)
                {
                    var bar = PhoneUi.Panel(slot, "Bar", new Color(0, 0, 0, 0.5f), 3); Place(bar.rectTransform, new Vector2(1, 0.5f), new Vector2(-10, 4), new Vector2(8, 56), new Vector2(1, 0.5f));
                    slotFill[i] = PhoneUi.Panel(bar.rectTransform, "Fill", i == 1 ? C("#4AA8FF") : Bad, 3);
                    slotFill[i].rectTransform.anchorMin = new Vector2(0, 0); slotFill[i].rectTransform.anchorMax = new Vector2(1, 0); slotFill[i].rectTransform.pivot = new Vector2(0.5f, 0);
                    slotFill[i].rectTransform.offsetMin = Vector2.zero; slotFill[i].rectTransform.offsetMax = Vector2.zero;
                }
            }
        }

        private static Text Label(Transform parent, string text, int size, Color color, TextAnchor anchor, bool bold = false)
        {
            var t = PhoneUi.Label(parent, text, size, color, anchor, bold);
            var shadow = t.gameObject.AddComponent<Shadow>(); shadow.effectColor = new Color(0, 0, 0, 0.6f); shadow.effectDistance = new Vector2(1.5f, -1.5f);
            return t;
        }
        private static void Place(RectTransform rt, Vector2 anchor, Vector2 position, Vector2 size, Vector2 pivot)
        {
            rt.anchorMin = rt.anchorMax = anchor; rt.pivot = pivot; rt.anchoredPosition = position; rt.sizeDelta = size;
        }

        // ---------- procedural icons ----------
        private void BuildIcons()
        {
            ringSprite = Make(128, p => { float d = Mathf.Abs(p.magnitude - 0.42f) - 0.06f; return Fill(d, Color.white); });
            dropSprite = Make(96, p =>
            {
                p.y += 0.12f;
                float circle = p.magnitude - 0.3f;
                Vector2 q = new(Mathf.Abs(p.x), p.y - 0.12f);
                float tri = Mathf.Max(q.x * 0.82f + q.y * 0.57f - 0.24f, -q.y + 0.02f);
                return Fill(Mathf.Min(circle, tri), Color.white);
            });
            Color skin = C("#F2B48A"), outline = C("#20242B"), steel = C("#D9E1EA"), glass = new(0.88f, 0.94f, 1f, 1f);
            iconHand = Make(128, p =>
            {
                float palm = RoundBox(p - new Vector2(0, -0.12f), new Vector2(0.2f, 0.2f), 0.1f);
                float f1 = Capsule(p, new Vector2(-0.15f, 0.02f), new Vector2(-0.17f, 0.3f), 0.06f);
                float f2 = Capsule(p, new Vector2(-0.05f, 0.05f), new Vector2(-0.05f, 0.38f), 0.06f);
                float f3 = Capsule(p, new Vector2(0.05f, 0.05f), new Vector2(0.06f, 0.36f), 0.06f);
                float f4 = Capsule(p, new Vector2(0.15f, 0.02f), new Vector2(0.17f, 0.26f), 0.055f);
                float th = Capsule(p, new Vector2(0.17f, -0.15f), new Vector2(0.34f, 0.02f), 0.065f);
                float d = Mathf.Min(palm, Mathf.Min(Mathf.Min(f1, f2), Mathf.Min(Mathf.Min(f3, f4), th)));
                return Over(Fill(d - 0.025f, outline), Fill(d, skin));
            });
            iconAnesthesia = SyringeIcon(C("#3D9BFF"), steel, glass, outline);
            iconBlood = SyringeIcon(Bad, steel, glass, outline);
            iconScalpel = Make(128, p =>
            {
                p = Rotate(p, 40f);
                float handle = RoundBox(p - new Vector2(0, -0.17f), new Vector2(0.055f, 0.24f), 0.04f);
                Vector2 b = p - new Vector2(0, 0.2f);
                float blade = Mathf.Max(RoundBox(b, new Vector2(0.07f, 0.16f), 0.06f), b.x - 0.02f + b.y * 0.15f);
                float d = Mathf.Min(handle, blade);
                Color c = Over(Fill(d - 0.022f, outline), Over(Fill(handle, C("#5D6B7A")), Fill(blade, steel)));
                return c;
            });
        }
        private Sprite SyringeIcon(Color liquid, Color steel, Color glass, Color outline) => Make(128, p =>
        {
            p = Rotate(p, -40f);
            float barrel = RoundBox(p - new Vector2(0, -0.02f), new Vector2(0.085f, 0.2f), 0.03f);
            float fluid = RoundBox(p - new Vector2(0, -0.1f), new Vector2(0.07f, 0.11f), 0.02f);
            float flange = RoundBox(p - new Vector2(0, 0.19f), new Vector2(0.15f, 0.025f), 0.02f);
            float rod = RoundBox(p - new Vector2(0, 0.28f), new Vector2(0.025f, 0.08f), 0.01f);
            float thumb = RoundBox(p - new Vector2(0, 0.37f), new Vector2(0.09f, 0.02f), 0.015f);
            float needle = RoundBox(p - new Vector2(0, -0.32f), new Vector2(0.012f, 0.1f), 0.006f);
            float all = Mathf.Min(Mathf.Min(barrel, flange), Mathf.Min(Mathf.Min(rod, thumb), needle));
            Color c = Fill(all - 0.022f, outline);
            c = Over(c, Fill(Mathf.Min(rod, Mathf.Min(thumb, flange)), C("#B8C2CC")));
            c = Over(c, Fill(needle, steel));
            c = Over(c, Fill(barrel, glass));
            c = Over(c, Fill(fluid, liquid));
            return c;
        });
        private static Sprite Make(int size, Func<Vector2, Color> shader)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, hideFlags = HideFlags.DontSave };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                    px[y * size + x] = shader(new Vector2((x + 0.5f) / size - 0.5f, (y + 0.5f) / size - 0.5f));
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f);
        }
        private static Color Fill(float d, Color c) { c.a *= Mathf.Clamp01(0.5f - d * 128f); return c; }
        private static Color Over(Color under, Color over)
        {
            float a = over.a + under.a * (1f - over.a);
            if (a <= 0.0001f) return new Color(0, 0, 0, 0);
            Color c = (over * over.a + under * under.a * (1f - over.a)) / a; c.a = a; return c;
        }
        private static float RoundBox(Vector2 p, Vector2 half, float r)
        {
            Vector2 q = new(Mathf.Abs(p.x) - half.x + r, Mathf.Abs(p.y) - half.y + r);
            return new Vector2(Mathf.Max(q.x, 0), Mathf.Max(q.y, 0)).magnitude + Mathf.Min(Mathf.Max(q.x, q.y), 0) - r;
        }
        private static float Capsule(Vector2 p, Vector2 a, Vector2 b, float r)
        {
            Vector2 pa = p - a, ba = b - a; float h = Mathf.Clamp01(Vector2.Dot(pa, ba) / Vector2.Dot(ba, ba));
            return (pa - ba * h).magnitude - r;
        }
        private static Vector2 Rotate(Vector2 p, float degrees)
        {
            float a = degrees * Mathf.Deg2Rad, c = Mathf.Cos(a), s = Mathf.Sin(a);
            return new Vector2(p.x * c - p.y * s, p.x * s + p.y * c);
        }

        // ---------- public feedback ----------
        public void OnServerHint(OpHint h, int arg) { serverHint = h; serverArg = arg; serverAt = Time.unscaledTime; }
        public void Toast(string text, HintTone tone) => AddToast(text, tone, Vector3.zero, false);
        public void WorldToast(string text, Vector3 world, HintTone tone) => AddToast(text, tone, world, true);
        public void Flash(Color color) { flashColor = color; flashAt = Time.unscaledTime; }
        public void Pulse() { }
        private void AddToast(string text, HintTone tone, Vector3 world, bool isWorld)
        {
            if (root == null) return;
            LastToast = text;
            var t = Label(root, text, isWorld ? 30 : 30, ToneColor(tone), TextAnchor.MiddleCenter, true);
            t.font = PhoneUi.Heavy; t.horizontalOverflow = HorizontalWrapMode.Overflow;
            var o = t.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0, 0, 0, 0.75f); o.effectDistance = new Vector2(2, -2);
            t.rectTransform.sizeDelta = new Vector2(900, 50);
            if (isWorld)
            {
                // Stack world toasts that pop at about the same place instead of drawing them on top of each other.
                int near = 0;
                foreach (var other in toasts) if (other.isWorld && Time.unscaledTime - other.born < 1.2f && Vector3.Distance(other.world, world) < 0.25f) near++;
                world += table.transform.up * (0.11f * near);
            }
            toasts.Add((t.rectTransform, t, Time.unscaledTime, world, isWorld));
            if (toasts.Count > 6) { Destroy(toasts[0].rt.gameObject); toasts.RemoveAt(0); }
        }

        // ---------- per frame ----------
        private Camera UiCamera => canvas.renderMode == RenderMode.ScreenSpaceOverlay ? null : canvas.worldCamera;
        private bool ScreenToCanvas(Vector2 screen, out Vector2 local) => RectTransformUtility.ScreenPointToLocalPointInRectangle(root, screen, UiCamera, out local);
        private bool WorldToCanvas(Vector3 world, out Vector2 local)
        {
            local = default;
            var cam = view.ViewCamera;
            if (cam == null) return false;
            Vector3 s = cam.WorldToScreenPoint(world);
            if (s.z <= 0f) return false;
            return ScreenToCanvas(s, out local);
        }
        private static void At(RectTransform rt, Vector2 local) { rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); rt.anchoredPosition = local; }

        private void LateUpdate()
        {
            if (view == null || table == null || root == null) return;
            var cam = view.ViewCamera;
            if (view.CaptureMode && cam != null)
            {
                if (canvas.renderMode != RenderMode.ScreenSpaceCamera || canvas.worldCamera != cam)
                { canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = cam; canvas.planeDistance = cam.nearClipPlane + 0.05f; }
            }
            else if (canvas.renderMode != RenderMode.ScreenSpaceOverlay) canvas.renderMode = RenderMode.ScreenSpaceOverlay;

            prompt.gameObject.SetActive(view.PromptVisible && !view.Active);
            tableGroup.alpha = Mathf.Clamp01(view.Blend * 1.5f);
            tableGroup.gameObject.SetActive(view.Active || view.Blend > 0.01f);
            UpdateToasts();
            float f = Mathf.Clamp01(1f - (Time.unscaledTime - flashAt) / 0.45f);
            flash.color = new Color(flashColor.r, flashColor.g, flashColor.b, flashColor.a * f);
            if (!tableGroup.gameObject.activeSelf) return;
            var state = table.State; var netView = table.View;
            if (state == null) return;
            UpdateCard(state, netView);
            UpdateBanners(state);
            UpdateHotbar(netView);
            UpdateCursor(state, netView);
            UpdateRemote();
            UpdateBubble(state, netView);
        }

        private void UpdateToasts()
        {
            for (int i = toasts.Count - 1; i >= 0; i--)
            {
                var t = toasts[i]; float age = Time.unscaledTime - t.born;
                if (age > 1.9f || t.rt == null) { if (t.rt != null) Destroy(t.rt.gameObject); toasts.RemoveAt(i); continue; }
                Vector2 basePos;
                if (t.isWorld) { if (!WorldToCanvas(t.world, out basePos)) basePos = new Vector2(0, 120); basePos += new Vector2(0, 40); }
                else basePos = new Vector2(0, 160 + (toasts.Count - 1 - i) * 0);
                At(t.rt, basePos + new Vector2(0, age * 38f));
                float a = age < 0.12f ? age / 0.12f : Mathf.Clamp01((1.9f - age) / 0.5f);
                var c = t.text.color; c.a = a; t.text.color = c;
                t.rt.localScale = Vector3.one * (age < 0.12f ? Mathf.Lerp(1.4f, 1f, age / 0.12f) : 1f);
            }
            // screen toasts stack downward
            int n = 0;
            for (int i = toasts.Count - 1; i >= 0; i--)
            {
                if (toasts[i].isWorld) continue;
                float age = Time.unscaledTime - toasts[i].born;
                At(toasts[i].rt, new Vector2(0, 300 - n * 46 + age * 20f)); n++;
            }
        }

        public static string StateName(OperationState s, OperationView v, OperationTuning tuning, out HintTone tone)
        {
            tone = HintTone.Neutral;
            if (!s.alive) { tone = HintTone.Bad; return "Мёртв"; }
            if (!s.onTable) { tone = HintTone.Neutral; return s.knockedOut ? "В отключке" : "Не спит"; }
            if (!s.aligned) return "Укладываем…";
            if (s.Panicking) { tone = HintTone.Bad; return "Просыпается!"; }
            bool injecting = v != null && v.injecting;
            if (injecting && s.residual < tuning.suitableMinimum) { tone = HintTone.Warn; return "Засыпает"; }
            if (s.Sleeping)
            {
                if (s.residual > tuning.suitableMaximum) { tone = HintTone.Bad; return "Спит… слишком крепко"; }
                if (s.sleepRemaining < 8f) { tone = HintTone.Warn; return "Просыпается!"; }
                tone = HintTone.Good; return s.bloodPortions >= tuning.weakenedPortion ? "Спит · ослаблен" : "Спит";
            }
            if (s.Dazed) { tone = HintTone.Warn; return "Очухивается"; }
            if (s.bloodPortions >= tuning.weakenedPortion) { tone = HintTone.Warn; return "Ослаблен"; }
            tone = HintTone.Warn; return "Не спит";
        }

        private void UpdateCard(OperationState s, OperationView v)
        {
            var tuning = table.Tuning;
            stateText.text = StateName(s, v, tuning, out var tone);
            stateText.color = ToneColor(tone);
            idText.text = string.IsNullOrEmpty(s.patientId) ? "" : "№ " + s.patientId.Substring(Mathf.Max(0, s.patientId.Length - 5)).ToUpperInvariant();
            int depth = !s.Sleeping ? 0 : s.sleepRemaining >= 55f ? 3 : s.sleepRemaining >= 20f ? 2 : 1;
            for (int i = 0; i < 3; i++) sleepPills[i].color = i < depth ? C("#7FB2FF") : new Color(1, 1, 1, 0.14f);
            for (int i = 0; i < 3; i++) drops[i].color = i < s.bloodPortions ? Bad : new Color(1, 1, 1, 0.18f);
            int closed = 0;
            for (int i = 0; i < 5; i++) { strapBars[i].color = s.restraints[i] ? Good : new Color(1f, 0.32f, 0.36f, 0.55f); if (s.restraints[i]) closed++; }
            strapLabel.text = "Ремни " + closed + "/5";
            for (int i = 0; i < 3; i++)
            {
                var o = s.organs[i]; string text; Color bg;
                if (o.removed) { text = OperationText.OrganShort[i] + " · вынута"; bg = new Color(0.25f, 0.55f, 1f, 0.35f); if (i == 2) text = "Печень · вынута"; }
                else if (o.Opened && o.Released) { text = OperationText.OrganShort[i] + " · тяни!"; bg = new Color(0.35f, 0.85f, 0.4f, 0.35f); }
                else if (o.Opened) { text = OperationText.OrganShort[i] + " · связки " + (o.connections.Length - o.CordsLeft) + "/" + o.connections.Length; bg = new Color(1f, 0.75f, 0.2f, 0.3f); }
                else if (o.cut > 0.01f) { text = OperationText.OrganShort[i] + " · разрез " + Mathf.RoundToInt(o.cut * 100f) + "%"; bg = new Color(1f, 0.5f, 0.3f, 0.3f); }
                else { text = OperationText.OrganShort[i] + " · цела"; bg = new Color(1, 1, 1, 0.08f); }
                organChips[i].text = text; organChipBg[i].color = bg;
            }
        }

        private void UpdateBanners(OperationState s)
        {
            bool p = s.Panicking;
            panic.gameObject.SetActive(p);
            if (p)
            {
                float k = 1f + Mathf.Sin(Time.unscaledTime * 9f) * 0.035f;
                panic.localScale = new Vector3(k, k, 1f);
                float frac = Mathf.Clamp01(s.panicRemaining / Mathf.Max(0.1f, table.Tuning.rescueSeconds));
                panicRing.fillAmount = frac;
                panicSeconds.text = Mathf.CeilToInt(s.panicRemaining).ToString();
            }
            dead.gameObject.SetActive(!s.alive);
            if (!s.alive) deadText.text = "ПАЦИЕНТ МЁРТВ · " + OperationText.Death(s.deathCause) + "\n<size=20>органы ещё можно достать · F10 — новый пациент</size>";
        }

        private void UpdateHotbar(OperationView v)
        {
            ToolSlot mine = view.LocalSlot;
            for (int i = 0; i < 4; i++)
            {
                var slot = (ToolSlot)i;
                bool selected = slot == mine;
                var tool = slot == ToolSlot.Hands ? null : table.ToolOf(slot);
                int holder = tool != null && tool.Mode == ToolMode.Held ? tool.Holder : -1;
                bool other = holder >= 0 && holder != view.LocalClientId;
                Color otherColor = other ? OperationVisuals.PlayerColor(holder) : Color.white;
                slotFrame[i].color = selected ? new Color(1, 1, 1, 0.95f) : other ? new Color(otherColor.r, otherColor.g, otherColor.b, 0.9f) : new Color(1, 1, 1, 0f);
                slotBg[i].color = selected ? new Color(0.16f, 0.2f, 0.26f, 0.92f) : other ? new Color(otherColor.r * 0.3f, otherColor.g * 0.3f, otherColor.b * 0.3f, 0.88f) : Panel;
                slotOwner[i].text = other ? "P" + (holder + 1) : "";
                slotOwner[i].color = otherColor;
                slotBg[i].rectTransform.localScale = Vector3.one * (selected ? 1.06f : 1f);
                slotFrame[i].rectTransform.localScale = slotBg[i].rectTransform.localScale;
                if (slotFill[i] != null && v != null)
                {
                    float fill = i == 1 ? v.barrel / Mathf.Max(0.01f, table.Tuning.syringeCapacity) : v.blood;
                    var rt = slotFill[i].rectTransform;
                    rt.offsetMax = new Vector2(0, Mathf.Clamp01(fill) * 56f);
                }
            }
            if (v != null) slotLabel[1].text = "Наркоз · " + Mathf.CeilToInt(v.stock / Mathf.Max(0.01f, table.Tuning.syringeCapacity)) + " зап.";
        }

        private void UpdateRemote()
        {
            foreach (var pair in table.Cursors)
            {
                if (pair.Key == view.LocalClientId) continue;
                if (!remote.TryGetValue(pair.Key, out var r))
                {
                    var rt = PhoneUi.Rect("Cursor P" + (pair.Key + 1), tableGroup.transform); rt.sizeDelta = new Vector2(26, 26);
                    var img = rt.gameObject.AddComponent<Image>(); img.sprite = ringSprite; img.raycastTarget = false;
                    var label = Label(rt, "P" + (pair.Key + 1), 18, Color.white, TextAnchor.MiddleLeft, true);
                    Place(label.rectTransform, new Vector2(1, 0.5f), new Vector2(4, 12), new Vector2(60, 24), new Vector2(0, 0.5f));
                    remote[pair.Key] = r = (rt, img, label);
                }
                var c = pair.Value; bool fresh = Time.time - c.at < 1f;
                r.rt.gameObject.SetActive(fresh && WorldToCanvas(table.transform.TransformPoint(c.smoothed), out var local) && Assign(r.rt, local));
                Color col = OperationVisuals.PlayerColor(pair.Key);
                r.img.color = col; r.label.color = col;
                r.rt.localScale = Vector3.one * (c.pressed ? 0.75f : 1f);
            }
        }
        private static bool Assign(RectTransform rt, Vector2 local) { At(rt, local); return true; }
        /// <summary>Keeps a cursor-attached panel fully on screen (canvas-centred coordinates).</summary>
        private void KeepOnScreen(RectTransform rt)
        {
            var half = root.rect.size * 0.5f; var size = rt.sizeDelta; var pos = rt.anchoredPosition; var pivot = rt.pivot;
            float minX = -half.x + 12 + size.x * pivot.x, maxX = half.x - 12 - size.x * (1 - pivot.x);
            float top = PanicVisible || DeadVisible ? 140f : 12f; // never over the banners
            float minY = -half.y + 130 + size.y * pivot.y, maxY = half.y - top - size.y * (1 - pivot.y);
            rt.anchoredPosition = new Vector2(Mathf.Clamp(pos.x, minX, maxX), Mathf.Clamp(pos.y, minY, maxY));
        }

        private void UpdateBubble(OperationState s, OperationView v)
        {
            string text = null; var rig = table.PatientRig;
            if (rig != null && rig.Head != null && s.onTable && s.aligned)
            {
                var tuning = table.Tuning;
                if (!s.alive) text = "x_x";
                else if (s.Panicking) text = "А-А-А-А!";
                else if (s.residual > tuning.suitableMaximum)
                {
                    float over = (s.residual - tuning.suitableMaximum) / (tuning.overdoseAbove - tuning.suitableMaximum);
                    text = over < 0.3f ? "хм?.." : over < 0.7f ? "хватит?.." : "ХВАТИТ!!";
                }
                else if (s.Sleeping && !(v != null && v.injecting && s.residual < tuning.suitableMinimum)) text = s.sleepRemaining < 6f ? "м-м?.." : "Z z z";
                else if (v != null && v.injecting) text = s.residual < tuning.suitableMinimum * 0.5f ? "э-э?.." : "ммм… баиньки";
                else if (s.Dazed) text = "где я?..";
                else if (s.escapeProgress > 0.5f) text = "Я ухожу!";
                else text = "Отпустите!";
            }
            bubble.gameObject.SetActive(text != null && WorldToCanvas(rig.Head.position + table.transform.up * 0.3f, out var local) && Assign(bubble, local));
            if (text != null)
            {
                bubbleText.text = text;
                bubble.sizeDelta = new Vector2(Mathf.Max(90, bubbleText.preferredWidth + 30), 46);
                float wob = text == "ХВАТИТ!!" || text == "А-А-А-А!" ? Mathf.Sin(Time.unscaledTime * 30f) * 4f : 0f;
                bubble.anchoredPosition += new Vector2(wob, 0);
            }
        }

        private void UpdateCursor(OperationState s, OperationView v)
        {
            var tuning = table.Tuning;
            bool on = view.Active;
            reticle.gameObject.SetActive(on);
            if (!on) { hintPill.gameObject.SetActive(false); ring.gameObject.SetActive(false); tension.gameObject.SetActive(false); card2.gameObject.SetActive(false); return; }
            bool okCursor = ScreenToCanvas(view.CursorScreen, out var cursor);
            DebugLine = $"mode={canvas.renderMode} screen={view.CursorScreen} ok={okCursor} local={cursor} rect={root.rect.size} cam={(canvas.worldCamera != null ? canvas.worldCamera.pixelWidth + "x" + canvas.worldCamera.pixelHeight : "-")}";
            if (!okCursor) return;
            At(reticle, cursor);
            hint = ContextHint(s, v, out hintTone);
            if (Time.unscaledTime - serverAt < 1.6f) { string sh = ServerText(serverHint, serverArg, out var st); if (sh != null) { hint = sh; hintTone = st; } }
            reticleImage.color = ToneColor(hintTone);
            hintPill.gameObject.SetActive(!string.IsNullOrEmpty(hint));
            if (hintPill.gameObject.activeSelf)
            {
                hintText.text = hint; hintText.color = ToneColor(hintTone);
                hintPill.sizeDelta = new Vector2(hintText.preferredWidth + 28, 40);
                At(hintPill, cursor + new Vector2(26, -22)); hintPill.pivot = new Vector2(0, 1);
                var size = root.rect.size; var pos = hintPill.anchoredPosition;
                if (pos.x + hintPill.sizeDelta.x > size.x * 0.5f - 10) { pos.x = cursor.x - 26 - hintPill.sizeDelta.x; hintPill.anchoredPosition = pos; }
                KeepOnScreen(hintPill);
            }
            // progress ring: blood fill, cord snip, injection
            float progress = -1f; Color ringColor = Bad;
            var slot = view.LocalSlot; var press = view.PressTarget;
            if (view.Pressed && slot == ToolSlot.Blood && press.ArmSide >= 0 && v != null && v.drawing >= 0) { progress = v.blood; ringColor = Bad; }
            else if (slot == ToolSlot.Blood && v != null && v.blood > 0f && v.blood < 1f && view.Current.target.ArmSide >= 0) { progress = v.blood; ringColor = Bad; }
            else if (view.Pressed && slot == ToolSlot.Scalpel && press.kind == TargetKind.Cord && press.index < 3 && press.sub < s.organs[press.index].connections.Length)
            { progress = s.organs[press.index].connections[press.sub]; ringColor = C("#FFD23B"); }
            else if (view.Pressed && slot == ToolSlot.Anesthesia && v != null && v.injecting) { progress = Mathf.Clamp01(v.barrel / Mathf.Max(0.01f, tuning.syringeCapacity)); ringColor = C("#4AA8FF"); }
            ring.gameObject.SetActive(progress >= 0f);
            if (progress >= 0f) { At(ring, cursor); ringFill.fillAmount = Mathf.Clamp01(progress); ringFill.color = ringColor; }
            // tension
            bool pulling = view.Pressed && slot == ToolSlot.Hands && press.kind == TargetKind.Organ && press.index < 3 && s.organs[press.index].Released && !s.organs[press.index].removed;
            tension.gameObject.SetActive(pulling);
            if (pulling)
            {
                float t = Mathf.Clamp01(s.organs[press.index].pull / tuning.pullDistance);
                At(tension, cursor + new Vector2(-52, 20));
                tensionFill.rectTransform.offsetMax = new Vector2(-4, 4 + t * 142f);
                float over = Mathf.Clamp01((view.PullDrag - s.organs[press.index].pull) / tuning.pullDistance);
                tensionFill.color = Color.Lerp(Good, Bad, Mathf.Max(t * 0.6f, over));
            }
            // organ card
            var item = view.Current.item;
            if (view.Current.target.kind != TargetKind.Item) item = null;
            var held = view.HeldItem; if (item == null && held != null) item = held;
            card2.gameObject.SetActive(item != null);
            if (item != null)
            {
                At(card2, cursor + new Vector2(26, 28)); card2.pivot = new Vector2(0, 0);
                KeepOnScreen(card2);
                card2Title.text = item.Title;
                if (item.Kind == 2) { card2Tier.text = "Запечатан"; card2Tier.color = Bad; card2Price.text = "$" + tuning.bloodValue + " · не портится"; }
                else { card2Tier.text = OperationText.Tier(item.Grade); card2Tier.color = OperationText.TierColor(item.Grade); card2Price.text = "$" + item.World.UnitValue; }
            }
        }

        private string ServerText(OpHint h, int arg, out HintTone tone)
        {
            tone = HintTone.Bad;
            switch (h)
            {
                case OpHint.Squirming: return "Он дёргается — пристегни или усыпи";
                case OpHint.PatientDead: return "Пациент мёртв";
                case OpHint.NotOnTable: return "Сначала положи его на стол";
                case OpHint.ToolBusy: tone = HintTone.Warn; return "Это сейчас у P" + (arg + 1);
                case OpHint.SyringeEmpty: tone = HintTone.Warn; return "Шприц пуст — ПКМ, положи: заправится";
                case OpHint.SyringeFull: tone = HintTone.Warn; return "Шприц полный — кликни по пустому пакету";
                case OpHint.SyringeNotFull: tone = HintTone.Warn; return "Сначала набери полный шприц крови [3]";
                case OpHint.NoBags: tone = HintTone.Warn; return "Этот пакет уже занят";
                case OpHint.StartAtDot: tone = HintTone.Warn; return "Начни от зелёной точки и веди по пунктиру";
                case OpHint.CutCordsFirst: tone = HintTone.Warn; return "Сначала перережь связки скальпелем [4]";
                case OpHint.NoBloodLeft: return "Крови больше нет";
                case OpHint.WrongSpot: tone = HintTone.Warn; return "Не сюда";
                case OpHint.StockEmpty: return "Наркоз кончился (F10 — новый набор)";
                case OpHint.Refilled: tone = HintTone.Good; return "Шприц заправлен";
                case OpHint.BagReady: tone = HintTone.Good; return "Пакет готов!";
            }
            return null;
        }

        /// <summary>One line: what LMB does here, or why it is unavailable.</summary>
        private string ContextHint(OperationState s, OperationView v, out HintTone tone)
        {
            tone = HintTone.Neutral;
            var tuning = table.Tuning;
            var h = view.Current; var t = h.target; var slot = view.LocalSlot;
            var held = view.HeldItem;
            if (held != null)
            {
                if (t.kind == TargetKind.Tray || t.kind == TargetKind.BloodBag || t.kind == TargetKind.Item) { tone = HintTone.Good; return "ЛКМ — положить на лоток"; }
                return "Кликни по лотку · ПКМ — положить";
            }
            switch (t.kind)
            {
                case TargetKind.Tool:
                {
                    var tool = h.tool; if (tool == null) return "";
                    string name = tool.Slot == ToolSlot.Anesthesia ? "шприц с наркозом" : tool.Slot == ToolSlot.Blood ? "шприц для крови" : "скальпель";
                    tone = HintTone.Good; return "ЛКМ — взять " + name + " [" + ((int)tool.Slot + 1) + "]";
                }
                case TargetKind.Strap:
                    tone = HintTone.Good;
                    if (!s.onTable || !s.aligned) { tone = HintTone.Warn; return "Ремень · сначала уложи пациента"; }
                    return "ЛКМ — " + (s.restraints[t.index] ? "расстегнуть" : "застегнуть") + " ремень (" + OperationText.Straps[t.index] + ")";
                case TargetKind.BloodBag:
                    if (slot == ToolSlot.Blood && v != null && v.blood >= 1f) { tone = HintTone.Good; return "ЛКМ — перелить кровь в пакет"; }
                    return slot == ToolSlot.Blood ? "Сначала набери полный шприц" : "Пустой пакет · нужен шприц крови [3]";
                case TargetKind.Item:
                    if (h.item == null) return "";
                    tone = HintTone.Good; return "ЛКМ — взять";
                case TargetKind.Tray:
                    return "";
                case TargetKind.Cord:
                    if (slot == ToolSlot.Scalpel) { if (!table.ServerOrLocalCanOperate(s)) { tone = HintTone.Bad; return "Он дёргается — пристегни или усыпи"; } tone = HintTone.Good; return "Зажми ЛКМ — перерезать связку"; }
                    tone = HintTone.Warn; return "Связка · возьми скальпель [4]";
                case TargetKind.Organ:
                {
                    var o = s.organs[t.index];
                    if (slot == ToolSlot.Scalpel) { tone = HintTone.Bad; return "Это орган! Не тыкай скальпелем"; }
                    if (slot != ToolSlot.Hands) { tone = HintTone.Warn; return "Доставай руками [1]"; }
                    if (!o.Released) { tone = HintTone.Warn; return "Сначала перережь связки [4]"; }
                    if (!table.ServerOrLocalCanOperate(s)) { tone = HintTone.Bad; return "Он дёргается — пристегни или усыпи"; }
                    tone = HintTone.Good; return "Зажми ЛКМ и тяни вверх — плавно";
                }
                case TargetKind.Incision:
                {
                    var o = s.organs[t.index];
                    if (slot != ToolSlot.Scalpel) { tone = HintTone.Warn; return "Разрез · возьми скальпель [4]"; }
                    if (!table.ServerOrLocalCanOperate(s)) { tone = HintTone.Bad; return "Он дёргается — пристегни или усыпи"; }
                    if (view.Stroking) { tone = HintTone.Good; return "Веди по пунктиру… " + Mathf.RoundToInt(o.cut * 100f) + "%"; }
                    tone = HintTone.Good; return o.cut > 0.01f ? "Зажми ЛКМ там, где остановился, и веди дальше" : "Зажми ЛКМ у зелёной точки и веди по пунктиру";
                }
                case TargetKind.Body:
                {
                    if (!s.onTable || !s.aligned) { tone = HintTone.Warn; return "Сначала положи его на стол"; }
                    if (slot == ToolSlot.Anesthesia)
                    {
                        if (!s.alive) { tone = HintTone.Bad; return "Пациент мёртв"; }
                        if (!t.IsInjectionSite) { tone = HintTone.Warn; return "Коли в руку, плечо или шею"; }
                        if (v != null && v.barrel <= 0.001f) { tone = HintTone.Warn; return "Шприц пуст — ПКМ, положи: заправится"; }
                        tone = HintTone.Good; return view.Pressed ? "Вводим… следи за лицом" : "Зажми ЛКМ — ввести наркоз";
                    }
                    if (slot == ToolSlot.Blood)
                    {
                        if (t.ArmSide < 0) { tone = HintTone.Warn; return "Кровь берут из руки"; }
                        if (v != null && v.blood >= 1f) { tone = HintTone.Warn; return "Шприц полный — кликни по пустому пакету"; }
                        if (s.bloodPortions >= tuning.fatalPortion) { tone = HintTone.Bad; return "Крови больше нет"; }
                        bool ok = !s.alive || s.Sleeping || s.Torso || s.restraints[t.ArmSide];
                        if (!ok) { tone = HintTone.Bad; return "Он дёргается — пристегни или усыпи"; }
                        tone = HintTone.Good; return "Зажми ЛКМ — набрать кровь (" + Mathf.RoundToInt(tuning.bloodSeconds) + " с)";
                    }
                    if (slot == ToolSlot.Scalpel) { tone = HintTone.Warn; return "Режь по пунктиру"; }
                    if (!s.alive) { tone = HintTone.Bad; return "Пациент мёртв"; }
                    return "Пациент · наркоз [2] · кровь [3] · скальпель [4]";
                }
            }
            if (slot == ToolSlot.Hands && s.onTable && s.aligned && !s.Torso && s.alive && !s.Sleeping) { tone = HintTone.Warn; return "Пристегни ремни — кликни по ним"; }
            return "";
        }
    }
}
