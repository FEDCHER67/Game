using System;
using System.Collections.Generic;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace OnlyVolunteers.UI.Pause
{
    /// <summary>
    /// W86 pause menu (Fedya 25.10, brief escape-pause-menu-graphics-settings): Escape opens a centred overlay with
    /// "Настройки графики" (working) and placeholder buttons (Звук, Управление, Главное меню, Выход: hover/press feedback, no action).
    /// The graphics page edits a draft of <see cref="GfxValues"/>; Apply saves and applies it (W86GraphicsSettingsV01), Back
    /// discards it, Defaults loads the approved defaults into the draft. Display mode changes ask Keep/Revert (15 s, unscaled).
    /// Input: one owner while open (OvMenuGate.Blocking; gameplay scripts return early). Escape is taken only when no context used
    /// it this frame (the operating table consumes its own; the van lettering field is skipped). Solo host: the world pauses
    /// (Time.timeScale 0, audio paused); with other players connected only this player's input is blocked. Everything the menu
    /// changed (time scale, audio, cursor, the walker's look/move locks) is put back on close, disable or destroy.
    /// UI built in code with the phone's uGUI helpers (PhoneUi), Muck-like layout in camouflage colours: khaki-rimmed olive cards with
    /// a camo edge, procedural leaves and twigs on the rims, inline word choices for short option lists. No prefab, no assets.
    /// </summary>
    [DefaultExecutionOrder(10000)]
    [DisallowMultipleComponent]
    public sealed class W86PauseMenuV01 : MonoBehaviour
    {
        public float ConfirmSeconds = 15f;

        // camo palette (Fedya 25.10: a Muck-like menu in camouflage colours, leaves and twigs on the edges)
        static readonly Color Dim = new(0.02f, 0.03f, 0.01f, .58f), Card = PhoneUi.Hex("#2B3022", .95f), Frame = PhoneUi.Hex("#9C8F5E"),
            Band = PhoneUi.Hex("#353B29", .96f), Divider = PhoneUi.Hex("#6E6A47"), Accent = PhoneUi.Hex("#E9D49A"), Text1 = PhoneUi.Hex("#F4F1E4"),
            Text2 = PhoneUi.Hex("#B9B795"), Dimmed = PhoneUi.Hex("#7F8468"), BtnBg = PhoneUi.Hex("#4A4F35"), BtnHover = PhoneUi.Hex("#5C6343"),
            BtnPress = PhoneUi.Hex("#6B7350"), Go = PhoneUi.Hex("#5D7F36"), GoHover = PhoneUi.Hex("#6E9440"), Placeholder = PhoneUi.Hex("#8A8D72");

        GameObject canvasGo, rootPage, gfxPage, confirmBox;
        Text confirmText;
        readonly List<Row> rows = new();
        GfxValues draft, applied, displayBefore;
        float confirmUntil = -1f;
        bool open;

        // state owned while open
        float savedTimeScale = 1f; bool pausedWorld, savedAudioPause;
        CursorLockMode savedLock; bool savedVisible;
        KccFirstPersonInput walker; bool savedMoveLock, savedLookSuspend;
        GameObject ownedEventSystem;

        sealed class Row
        {
            public Func<string> Value; public Action<int> Step; public Func<string> Note;
            public Text ValueText, NoteText; public GameObject Go;
            public Func<int> Index; public Text[] Choices; // inline choices (Muck-style words): the chosen one bright, the rest dimmed
        }

        void Awake() { OvMenuGate.MenuInstalled = true; }

        void Start()
        {
            W86GraphicsSettingsV01.ApplySavedAtStartup();
            applied = W86GraphicsSettingsV01.Load();
            Build();
            canvasGo.SetActive(false);
        }

        void OnDisable() { if (open) Close(); }
        void OnDestroy() { if (open) Close(); OvMenuGate.MenuInstalled = false; if (ownedEventSystem) Destroy(ownedEventSystem); }

        void LateUpdate()
        {
            if (confirmUntil > 0f)
            {
                float left = confirmUntil - Time.unscaledTime;
                if (left <= 0f) RevertDisplay();
                else confirmText.text = $"Оставить новый режим экрана?\nВозврат к прежнему через {Mathf.CeilToInt(left)} с.";
            }
            var kb = Keyboard.current;
            if (open) NavigateValues(kb);
            // both input paths: the legacy manager and the Input System (the editor can route the new one to editor updates)
            bool esc = Input.GetKeyDown(KeyCode.Escape) || (kb != null && kb.escapeKey.wasPressedThisFrame);
            if (esc && OvMenuGate.EscapeFree) HandleEscape();
        }

        /// <summary>One Escape: open from gameplay, or one step back (confirm → revert, graphics → root, root → close).</summary>
        public void HandleEscape()
        {
            if (!open) { if (!TextFieldOpen()) Open(); return; }
            if (confirmUntil > 0f) RevertDisplay();
            else if (gfxPage.activeSelf) ShowRoot();
            else Close();
        }

        // ---------------------------------------------------------------- open / close
        void Open()
        {
            open = true;
            OvMenuGate.Blocking = true;
            savedLock = Cursor.lockState; savedVisible = Cursor.visible;
            walker = null;
            foreach (var k in FindObjectsByType<KccFirstPersonInput>())
                if (k.isActiveAndEnabled) { walker = k; break; }
            if (walker) { savedMoveLock = walker.MovementLocked; savedLookSuspend = walker.LookSuspended; walker.MovementLocked = true; walker.LookSuspended = true; }
            pausedWorld = IsSolo();
            if (pausedWorld) { savedTimeScale = Time.timeScale; Time.timeScale = 0f; savedAudioPause = AudioListener.pause; AudioListener.pause = true; }
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            EnsureEventSystem();
            canvasGo.SetActive(true);
            ShowRoot();
        }

        void Close()
        {
            if (confirmUntil > 0f) RevertDisplay();
            open = false;
            if (canvasGo) canvasGo.SetActive(false);
            if (pausedWorld) { Time.timeScale = savedTimeScale; AudioListener.pause = savedAudioPause; pausedWorld = false; }
            if (walker)
            {
                walker.MovementLocked = savedMoveLock;
                walker.LookSuspended = savedLookSuspend; // its setter re-locks the cursor when look comes back
                walker = null;
            }
            else { Cursor.lockState = savedLock; Cursor.visible = savedVisible; }
            OvMenuGate.Blocking = false;
            EventSystem.current?.SetSelectedGameObject(null);
        }

        static bool IsSolo()
        {
            var nm = FishNet.InstanceFinder.NetworkManager;
            if (nm == null) return true;
            if (nm.IsServerStarted) return nm.ServerManager.Clients.Count <= 1;
            return !nm.IsClientStarted;
        }

        static bool TextFieldOpen()
        {
            foreach (var p in FindObjectsByType<OnlyVolunteers.Vehicles.Paint.VanPaintInteractor>())
                if (p.TextOpen) return true;
            return false;
        }

        void EnsureEventSystem()
        {
            if (EventSystem.current != null || FindAnyObjectByType<EventSystem>() != null) return;
            ownedEventSystem = new GameObject("[Pause] EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        }

        // ---------------------------------------------------------------- pages
        void ShowRoot()
        {
            draft = applied;
            rootPage.SetActive(true); gfxPage.SetActive(false); confirmBox.SetActive(false);
            Select(rootPage);
        }

        void ShowGraphics()
        {
            applied = W86GraphicsSettingsV01.Load();
            CopyDisplay(ref applied, W86GraphicsSettingsV01.CurrentDisplay()); // the window as it is now
            draft = applied;
            rootPage.SetActive(false); gfxPage.SetActive(true); confirmBox.SetActive(false);
            RefreshRows();
            Select(gfxPage);
        }

        void Apply()
        {
            bool displayChanged = !draft.SameDisplay(applied);
            if (displayChanged && !W86GraphicsSettingsV01.Supported(draft)) { CopyDisplay(ref draft, applied); displayChanged = false; } // unsupported: not applied
            W86GraphicsSettingsV01.ApplyQuality(draft);
            if (displayChanged)
            {
                displayBefore = applied;
                W86GraphicsSettingsV01.ApplyDisplay(draft);
                confirmUntil = Time.unscaledTime + ConfirmSeconds;
                confirmBox.SetActive(true);
                Select(confirmBox);
            }
            applied = draft;
            RefreshRows();
        }

        static void CopyDisplay(ref GfxValues to, GfxValues from)
        {
            to.ScreenMode = from.ScreenMode; to.Width = from.Width; to.Height = from.Height; to.RefreshNum = from.RefreshNum; to.RefreshDen = from.RefreshDen;
        }

        void KeepDisplay()
        {
            confirmUntil = -1f; confirmBox.SetActive(false);
            W86GraphicsSettingsV01.SaveDisplay(applied);
            Select(gfxPage);
        }

        void RevertDisplay()
        {
            confirmUntil = -1f; confirmBox.SetActive(false);
            W86GraphicsSettingsV01.ApplyDisplay(displayBefore);
            CopyDisplay(ref applied, displayBefore);
            draft = applied;
            RefreshRows();
            if (gfxPage.activeSelf) Select(gfxPage);
        }

        void Defaults()
        {
            var d = W86GraphicsSettingsV01.Defaults();
            // defaults are quality, VSync and the cap; the display mode stays as chosen
            CopyDisplay(ref d, draft);
            draft = d;
            RefreshRows();
        }

        // ---------------------------------------------------------------- rows
        void RefreshRows()
        {
            foreach (var r in rows)
            {
                if (r.ValueText) r.ValueText.text = r.Value();
                if (r.Choices != null)
                {
                    int sel = r.Index();
                    for (int i = 0; i < r.Choices.Length; i++)
                    {
                        bool on = i == sel;
                        r.Choices[i].color = on ? Text1 : Dimmed;
                        r.Choices[i].font = on ? PhoneUi.Heavy : PhoneUi.Regular;
                    }
                }
                if (r.NoteText && r.Note != null) r.NoteText.text = r.Note();
            }
        }

        void NavigateValues(Keyboard kb)
        {
            bool l = Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A) || (kb != null && (kb.leftArrowKey.wasPressedThisFrame || kb.aKey.wasPressedThisFrame));
            bool rt = Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D) || (kb != null && (kb.rightArrowKey.wasPressedThisFrame || kb.dKey.wasPressedThisFrame));
            int dir = l ? -1 : rt ? 1 : 0;
            if (dir == 0 || !gfxPage.activeSelf || confirmUntil > 0f) return;
            var sel = EventSystem.current ? EventSystem.current.currentSelectedGameObject : null;
            if (!sel) return;
            foreach (var r in rows)
                if (sel.transform.IsChildOf(r.Go.transform)) { r.Step(dir); RefreshRows(); return; }
        }

        static int Cycle(int i, int dir, int n) => Mathf.Clamp(i + dir, 0, n - 1);

        void BuildRows(Transform content)
        {
            var S = W86GraphicsSettingsV01.MsaaValues;
            Section(content, "Экран");
            AddStepper(content, "Разрешение", () => $"{draft.Width} × {draft.Height}", dir =>
            {
                var list = W86GraphicsSettingsV01.Resolutions();
                int i = list.FindIndex(r => r.x == draft.Width && r.y == draft.Height); if (i < 0) i = 0;
                var r2 = list[Mathf.Clamp(i - dir, 0, list.Count - 1)]; // the list runs largest first: "right" = bigger
                draft.Width = r2.x; draft.Height = r2.y;
                var rr = W86GraphicsSettingsV01.RefreshRates(r2.x, r2.y)[0]; draft.RefreshNum = rr.numerator; draft.RefreshDen = rr.denominator;
            }, null);
            AddStepper(content, "Частота обновления", () => $"{Hz(draft):0.#} Гц", dir =>
            {
                var list = W86GraphicsSettingsV01.RefreshRates(draft.Width, draft.Height);
                int i = list.FindIndex(r => r.numerator == draft.RefreshNum && r.denominator == draft.RefreshDen); if (i < 0) i = 0;
                var rr = list[Mathf.Clamp(i - dir, 0, list.Count - 1)]; draft.RefreshNum = rr.numerator; draft.RefreshDen = rr.denominator;
            }, () => "Частоты, которые сообщает монитор для выбранного разрешения.");
            AddChoice(content, "Режим экрана", new[] { "Полный экран", "Без рамки", "Окно" }, () => draft.ScreenMode, i => draft.ScreenMode = i,
                () => "Смена режима или разрешения попросит подтверждения: без него через 15 с вернётся прежний.");
            AddChoice(content, "Вертикальная синхронизация", new[] { "Выкл", "Вкл" }, () => draft.VSync, i => draft.VSync = i,
                () => "Убирает разрывы кадра: кадры идут с частотой монитора.");
            AddChoice(content, "Ограничение FPS", new[] { "Нет", "30", "60", "120", "144", "165", "240" },
                () => Mathf.Max(0, Array.IndexOf(W86GraphicsSettingsV01.FpsCaps, draft.FpsCap)), i => draft.FpsCap = W86GraphicsSettingsV01.FpsCaps[i],
                () => draft.VSync > 0 ? "Не действует: при включённой VSync частоту задаёт монитор." : "Верхний предел кадров в секунду.");

            Section(content, "Качество");
            AddChoice(content, "Пресет", W86GraphicsSettingsV01.PresetNames, () => W86GraphicsSettingsV01.PresetOf(draft),
                i => draft = W86GraphicsSettingsV01.Preset(i, draft),
                () => W86GraphicsSettingsV01.PresetOf(draft) < 0 ? "Сейчас: свои настройки. «Высокое» — одобренные по умолчанию."
                                                                 : "«Высокое» — одобренные настройки по умолчанию. Изменение строки ниже делает пресет «свои».");
            AddChoice(content, "Масштаб рендера", Array.ConvertAll(W86GraphicsSettingsV01.RenderScales, v => v + "%"),
                () => Math.Max(0, Array.IndexOf(W86GraphicsSettingsV01.RenderScales, draft.RenderScale)), i => draft.RenderScale = W86GraphicsSettingsV01.RenderScales[i],
                () => "Ниже 100% — больше FPS, картинка мягче.");
            AddChoice(content, "Текстуры", new[] { "Полные", "Половина", "Четверть" }, () => draft.Textures, i => draft.Textures = i,
                () => "Разрешение текстур. Ниже — меньше видеопамяти.");
            AddChoice(content, "Сглаживание", new[] { "Выкл", "2x", "4x", "8x" }, () => Math.Max(0, Array.IndexOf(S, draft.Msaa)), i => draft.Msaa = S[i],
                () => "MSAA: сглаживает края и тонкие детали вдали. SMAA High всегда включено поверх. 8x — максимум.");
            AddChoice(content, "Тени", new[] { "Выкл", "Низкие", "Высокие" }, () => draft.Shadows, i => draft.Shadows = i,
                () => draft.Shadows == 0 ? "Без теней от солнца." : draft.Shadows == 1 ? "До 50 м, карта 2048." : "До 120 м, карта 4096, мягкий край.");
            AddChoice(content, "Отражения", new[] { "Выкл", "Движ.", "Низкие", "Средние", "Высокие", "Оч. выс.", "Ультра" },
                () => draft.Reflections, i => draft.Reflections = i, () =>
                draft.Reflections == 0 ? "Свои отражения выключены: стёкла отражают стандартное небо Unity." :
                draft.Reflections == 1 ? "Картинка в стёклах обновляется при перемещении: дёшево, но сменяется рывками." :
                draft.Reflections == 6 ? "Весь куб отражений каждый кадр (1:1): максимум, только для самых мощных ПК. 256 px." :
                $"{FacesText(draft.Reflections)} за кадр: отражения обновляются долей от частоты кадров. " + (draft.Reflections >= 4 ? "256 px." : "128 px."));
            AddChoice(content, "Трава", new[] { "Выкл", "Низкая", "Средняя", "Высокая" }, () => draft.Grass, i => draft.Grass = i,
                () => "Дальность и густота травы.");
            AddChoice(content, "Детализация", new[] { "Близко", "Нормально", "Далеко" }, () => draft.Lod, i => draft.Lod = i,
                () => "Где здания переключаются на упрощённые версии. Близко — больше FPS, Далеко — детальнее вдали, но тяжелее.");
        }

        static string FacesText(int tier) => tier switch { 2 => "1 грань куба", 3 => "2 грани куба", 4 => "3 грани куба", 5 => "4 грани куба", _ => "" };

        static float Hz(GfxValues v) => v.RefreshDen == 0 ? 0f : (float)v.RefreshNum / v.RefreshDen;

        // ---------------------------------------------------------------- UI building (camo, Muck-like)
        void Build()
        {
            canvasGo = new GameObject("[Pause] Menu", typeof(RectTransform));
            canvasGo.transform.SetParent(transform, false);
            canvasGo.layer = 5;
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 200;
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = .5f;
            canvasGo.AddComponent<GraphicRaycaster>();
            var dim = Img(canvasGo.transform, "Dim", Dim); Stretch(dim.rectTransform); // also stops clicks reaching anything behind

            // root page
            rootPage = CamoPanel(canvasGo.transform, "Root", 540, 640, 11);
            Title(rootPage.transform, "Пауза", -30);
            Label(rootPage.transform, "Esc — вернуться в игру", 18, Text2, TextAnchor.UpperCenter).rectTransform.Anchor(0, 1, 1, 1, 0, -128, 0, -100);
            var list = new GameObject("Buttons", typeof(RectTransform)); list.transform.SetParent(rootPage.transform, false);
            ((RectTransform)list.transform).Anchor(0, 0, 1, 1, 58, 46, -58, -150);
            var v = list.AddComponent<VerticalLayoutGroup>(); v.spacing = 14; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            Btn(list.transform, "Настройки графики", ShowGraphics, true, 66, true);
            foreach (var p in new[] { "Звук", "Управление", "Главное меню", "Выход" }) Btn(list.transform, p, null, false, 60); // placeholders: no action yet

            // graphics page
            gfxPage = CamoPanel(canvasGo.transform, "Graphics", 1180, 920, 23);
            Title(gfxPage.transform, "Настройки графики", -26);
            var scroll = new GameObject("Scroll", typeof(RectTransform), typeof(Image), typeof(Mask), typeof(ScrollRect));
            scroll.transform.SetParent(gfxPage.transform, false);
            ((RectTransform)scroll.transform).Anchor(0, 0, 1, 1, 46, 116, -46, -112);
            scroll.GetComponent<Image>().color = new Color(1, 1, 1, .01f); scroll.GetComponent<Mask>().showMaskGraphic = false;
            var content = new GameObject("Content", typeof(RectTransform)); content.transform.SetParent(scroll.transform, false);
            var crt = (RectTransform)content.transform; crt.anchorMin = new Vector2(0, 1); crt.anchorMax = new Vector2(1, 1); crt.pivot = new Vector2(.5f, 1); crt.sizeDelta = Vector2.zero;
            var cv = content.AddComponent<VerticalLayoutGroup>(); cv.spacing = 4; cv.padding = new RectOffset(6, 6, 2, 12);
            cv.childControlHeight = true; cv.childControlWidth = true; cv.childForceExpandHeight = false;
            content.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var sr = scroll.GetComponent<ScrollRect>(); sr.content = crt; sr.horizontal = false; sr.scrollSensitivity = 40; sr.movementType = ScrollRect.MovementType.Clamped;
            BuildRows(content.transform);
            var foot = new GameObject("Footer", typeof(RectTransform)); foot.transform.SetParent(gfxPage.transform, false);
            ((RectTransform)foot.transform).Anchor(0, 0, 1, 0, 52, 34, -52, 94);
            var fh = foot.AddComponent<HorizontalLayoutGroup>(); fh.spacing = 16; fh.childControlWidth = true; fh.childControlHeight = true; fh.childForceExpandWidth = true;
            Btn(foot.transform, "Применить", Apply, true, 60, true);
            Btn(foot.transform, "По умолчанию", Defaults, true, 60);
            Btn(foot.transform, "Назад без сохранения", ShowRoot, true, 60);

            // display confirmation
            confirmBox = CamoPanel(canvasGo.transform, "Confirm", 660, 280, 37);
            confirmText = Label(confirmBox.transform, "", 24, Text1, TextAnchor.MiddleCenter, true); confirmText.rectTransform.Anchor(0, 0, 1, 1, 34, 104, -34, -24);
            var cb = new GameObject("Buttons", typeof(RectTransform)); cb.transform.SetParent(confirmBox.transform, false);
            ((RectTransform)cb.transform).Anchor(0, 0, 1, 0, 44, 28, -44, 88);
            var ch = cb.AddComponent<HorizontalLayoutGroup>(); ch.spacing = 16; ch.childControlWidth = true; ch.childControlHeight = true; ch.childForceExpandWidth = true;
            Btn(cb.transform, "Оставить", KeepDisplay, true, 56, true);
            Btn(cb.transform, "Вернуть", RevertDisplay, true, 56);
        }

        /// <summary>A khaki-framed olive card with a camouflage edge strip and a few leaves/twigs hanging over its rim.</summary>
        GameObject CamoPanel(Transform parent, string name, float w, float h, int seed)
        {
            var frame = Img(parent, name, Frame, true); Centre(frame.gameObject, w, h);
            var camo = new GameObject("Camo", typeof(RectTransform), typeof(RawImage)); camo.transform.SetParent(frame.transform, false);
            var ri = camo.GetComponent<RawImage>(); ri.texture = CamoTexture; ri.raycastTarget = false;
            ri.uvRect = new Rect(seed * .137f, seed * .071f, w / 256f, h / 256f);
            ((RectTransform)camo.transform).Anchor(0, 0, 1, 1, 6, 6, -6, -6);
            var card = Img(frame.transform, "Card", Card, true); ((RectTransform)card.transform).Anchor(0, 0, 1, 1, 20, 20, -20, -20);
            Decorate(frame.transform, w, h, seed);
            return frame.gameObject;
        }

        void Decorate(Transform panel, float w, float h, int seed)
        {
            var rnd = new System.Random(seed);
            int n = 7 + (int)((w + h) / 260f);
            for (int i = 0; i < n; i++)
            {
                // round the rim: pick a point on the border, push it a little outward
                float t = (float)rnd.NextDouble(); float per = 2 * (w + h); float d = t * per;
                Vector2 pos; float edgeAngle;
                if (d < w) { pos = new Vector2(d - w / 2, h / 2); edgeAngle = 90; }
                else if (d < w + h) { pos = new Vector2(w / 2, h / 2 - (d - w)); edgeAngle = 0; }
                else if (d < 2 * w + h) { pos = new Vector2(w / 2 - (d - w - h), -h / 2); edgeAngle = 270; }
                else { pos = new Vector2(-w / 2, -h / 2 + (d - 2 * w - h)); edgeAngle = 180; }
                bool twig = rnd.NextDouble() < .3;
                var go = new GameObject(twig ? "Twig" : "Leaf", typeof(RectTransform), typeof(Image)); go.transform.SetParent(panel, false); go.layer = 5;
                var img = go.GetComponent<Image>(); img.raycastTarget = false;
                img.sprite = twig ? TwigSprite : LeafSprites[rnd.Next(LeafSprites.Length)];
                float size = twig ? 70 + (float)rnd.NextDouble() * 50 : 34 + (float)rnd.NextDouble() * 30;
                var rt = (RectTransform)go.transform; rt.sizeDelta = new Vector2(size, size);
                rt.anchoredPosition = pos + (Vector2)(Quaternion.Euler(0, 0, edgeAngle) * Vector3.right) * (size * .18f);
                rt.localRotation = Quaternion.Euler(0, 0, edgeAngle - 90 + (float)(rnd.NextDouble() * 120 - 60));
            }
        }

        void Title(Transform panel, string text, float top)
        {
            var t = Label(panel, text, 44, Accent, TextAnchor.UpperCenter, true); t.fontStyle = FontStyle.Italic;
            t.rectTransform.Anchor(0, 1, 1, 1, 30, top - 64, -30, top - 4);
            Line(panel, top - 74, 120);
        }

        static void Line(Transform parent, float y, float inset)
        {
            var l = Img(parent, "Divider", Divider); ((RectTransform)l.transform).Anchor(0, 1, 1, 1, inset, y - 3, -inset, y);
        }

        void Section(Transform parent, string title)
        {
            var go = new GameObject(title, typeof(RectTransform)); go.transform.SetParent(parent, false);
            go.AddComponent<LayoutElement>().preferredHeight = 56;
            var t = Label(go.transform, title, 28, Accent, TextAnchor.LowerLeft, true); t.rectTransform.Anchor(0, 0, 1, 1, 14, 10, 0, 0);
            var l = Img(go.transform, "Divider", Divider); ((RectTransform)l.transform).Anchor(0, 0, 1, 0, 8, 2, -8, 5);
        }

        Row RowBase(Transform parent, string label, Func<string> note)
        {
            var go = Img(parent, label, Band, true).gameObject;
            go.AddComponent<LayoutElement>().preferredHeight = note != null ? 82 : 60;
            var row = new Row { Note = note, Go = go };
            Label(go.transform, label, 22, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 1, .34f, 1, 20, -54, 0, -6);
            if (note != null) { row.NoteText = Label(go.transform, "", 15, Text2, TextAnchor.UpperLeft); row.NoteText.rectTransform.Anchor(0, 0, 1, 0, 20, 6, -20, 32); }
            rows.Add(row);
            return row;
        }

        void AddStepper(Transform parent, string label, Func<string> value, Action<int> step, Func<string> note)
        {
            var row = RowBase(parent, label, note); row.Value = value; row.Step = step;
            var left = Btn(row.Go.transform, "‹", () => { step(-1); RefreshRows(); }, true, 0); ((RectTransform)left.transform).Anchor(.36f, 1, .36f, 1, 0, -52, 50, -8);
            var right = Btn(row.Go.transform, "›", () => { step(1); RefreshRows(); }, true, 0); ((RectTransform)right.transform).Anchor(1, 1, 1, 1, -70, -52, -20, -8);
            row.ValueText = Label(row.Go.transform, "", 22, Text1, TextAnchor.MiddleCenter, true); row.ValueText.rectTransform.Anchor(.36f, 1, 1, 1, 60, -54, -80, -6);
        }

        void AddChoice(Transform parent, string label, string[] options, Func<int> get, Action<int> set, Func<string> note)
        {
            var row = RowBase(parent, label, note);
            row.Index = get; row.Value = () => { int i = get(); return i >= 0 && i < options.Length ? options[i] : ""; };
            row.Step = dir => { int i = get(); set(i < 0 ? (dir > 0 ? 0 : options.Length - 1) : Cycle(i, dir, options.Length)); };
            var strip = new GameObject("Choices", typeof(RectTransform)); strip.transform.SetParent(row.Go.transform, false);
            ((RectTransform)strip.transform).Anchor(.36f, 1, 1, 1, 0, -54, -16, -6);
            var hl = strip.AddComponent<HorizontalLayoutGroup>(); hl.spacing = 6; hl.childControlWidth = true; hl.childControlHeight = true; hl.childForceExpandWidth = true;
            row.Choices = new Text[options.Length];
            for (int k = 0; k < options.Length; k++)
            {
                int idx = k;
                var b = new GameObject(options[k], typeof(RectTransform), typeof(Image), typeof(Button)); b.transform.SetParent(strip.transform, false); b.layer = 5;
                var img = b.GetComponent<Image>(); img.color = Color.white; // square option tiles
                var btn = b.GetComponent<Button>(); var c = btn.colors;
                c.normalColor = new Color(1, 1, 1, 0f); c.highlightedColor = BtnHover; c.pressedColor = BtnPress; c.selectedColor = new Color(BtnHover.r, BtnHover.g, BtnHover.b, .6f);
                c.colorMultiplier = 1f; c.fadeDuration = .06f; btn.colors = c;
                btn.onClick.AddListener(() => { set(idx); RefreshRows(); });
                var t = Label(b.transform, options[k], options.Length > 5 ? 18 : 21, Dimmed, TextAnchor.MiddleCenter); Stretch(t.rectTransform);
                t.horizontalOverflow = HorizontalWrapMode.Overflow;
                row.Choices[k] = t;
            }
        }

        Button Btn(Transform parent, string text, Action onClick, bool working, float height, bool primary = false)
        {
            // khaki rim + olive (or green) face, chunky label with a dark drop shadow
            var rim = Img(parent, text, Color.white); // square, 90-degree corners (Fedya 25.10)
            var b = rim.gameObject.AddComponent<Button>();
            var colors = b.colors;
            colors.normalColor = primary ? Go : BtnBg; colors.highlightedColor = primary ? GoHover : BtnHover; colors.pressedColor = BtnPress;
            colors.selectedColor = primary ? GoHover : BtnHover; colors.colorMultiplier = 1f; colors.fadeDuration = .06f; b.colors = colors;
            if (onClick != null) b.onClick.AddListener(() => onClick());
            if (height > 0) rim.gameObject.AddComponent<LayoutElement>().preferredHeight = height;
            var edge = rim.gameObject.AddComponent<Outline>(); edge.effectColor = Frame; edge.effectDistance = new Vector2(2.5f, -2.5f);
            var t = Label(rim.transform, text, height > 0 ? 25 : 28, working ? Text1 : Placeholder, TextAnchor.MiddleCenter, working);
            Stretch(t.rectTransform);
            return b;
        }

        static void Select(GameObject page)
        {
            var b = page.GetComponentInChildren<Selectable>();
            if (EventSystem.current && b) EventSystem.current.SetSelectedGameObject(b.gameObject);
        }

        static Image Img(Transform parent, string name, Color c, bool rounded = false)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image)); go.transform.SetParent(parent, false); go.layer = 5;
            var img = go.GetComponent<Image>(); img.color = c;
            if (rounded) { img.sprite = PhoneUi.Rounded; img.type = Image.Type.Sliced; }
            return img;
        }

        static Text Label(Transform parent, string text, int size, Color c, TextAnchor anchor, bool heavy = false)
        {
            var go = new GameObject("Text", typeof(RectTransform), typeof(Text)); go.transform.SetParent(parent, false); go.layer = 5;
            var t = go.GetComponent<Text>(); t.text = text; t.fontSize = size; t.color = c; t.alignment = anchor;
            t.font = heavy ? PhoneUi.Heavy : PhoneUi.Regular; t.raycastTarget = false; t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow;
            if (heavy) { var sh = go.AddComponent<Shadow>(); sh.effectColor = new Color(0.06f, 0.07f, 0.03f, .85f); sh.effectDistance = new Vector2(2f, -2f); }
            return t;
        }

        static void Centre(GameObject go, float w, float h)
        {
            var rt = (RectTransform)go.transform; rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(.5f, .5f); rt.sizeDelta = new Vector2(w, h); rt.anchoredPosition = Vector2.zero;
        }

        static void Stretch(RectTransform rt) { rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero; }

        // ---------------------------------------------------------------- procedural camo, leaves, twig (no assets)
        static Texture2D camoTex; static Sprite[] leafSprites; static Sprite twigSprite;
        static readonly Color[] CamoColors = { PhoneUi.Hex("#3E4A2A"), PhoneUi.Hex("#5B6438"), PhoneUi.Hex("#7A6B45"), PhoneUi.Hex("#262C1B") };

        static Texture2D CamoTexture
        {
            get
            {
                if (camoTex) return camoTex;
                const int N = 256; camoTex = new Texture2D(N, N, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Bilinear, name = "PauseCamo" };
                var px = new Color[N * N];
                for (int y = 0; y < N; y++) for (int x = 0; x < N; x++)
                {
                    // tileable blobs: noise sampled on a torus
                    float a = x / (float)N * Mathf.PI * 2, b = y / (float)N * Mathf.PI * 2;
                    float u = Mathf.Cos(a) * 1.6f + 5f, v = Mathf.Sin(a) * 1.6f + 5f, w2 = Mathf.Cos(b) * 1.6f + 9f, z = Mathf.Sin(b) * 1.6f + 9f;
                    float n1 = Mathf.PerlinNoise(u + w2 * .37f, v + z * .41f), n2 = Mathf.PerlinNoise(u * 2.1f + z, v * 2.1f + w2) * .45f;
                    float n = n1 + n2;
                    int k = n < .62f ? 3 : n < .82f ? 0 : n < 1.0f ? 1 : 2;
                    px[y * N + x] = CamoColors[k];
                }
                camoTex.SetPixels(px); camoTex.Apply(false, true);
                return camoTex;
            }
        }

        static Sprite[] LeafSprites
        {
            get
            {
                if (leafSprites != null) return leafSprites;
                var greens = new[] { PhoneUi.Hex("#4F6B2C"), PhoneUi.Hex("#6E8A3A"), PhoneUi.Hex("#8A7A3E"), PhoneUi.Hex("#3C5124") };
                leafSprites = new Sprite[greens.Length];
                for (int s = 0; s < greens.Length; s++)
                {
                    const int N = 64; var t = new Texture2D(N, N, TextureFormat.RGBA32, false) { name = "PauseLeaf" + s };
                    var px = new Color[N * N]; var col = greens[s]; var vein = Color.Lerp(col, Color.black, .35f);
                    for (int y = 0; y < N; y++) for (int x = 0; x < N; x++)
                    {
                        float fy = y / (N - 1f), fx = (x / (N - 1f) - .5f) * 2f;      // leaf along y, pointed at both ends
                        float half = Mathf.Sin(Mathf.Clamp01((fy - .06f) / .9f) * Mathf.PI) * (s % 2 == 0 ? .62f : .45f);
                        float d = Mathf.Abs(fx) - half;
                        float alpha = Mathf.Clamp01(-d * 20f);
                        if (fy < .08f && Mathf.Abs(fx) < .06f) alpha = 1f;          // stem
                        var c = Mathf.Abs(fx) < .045f ? vein : Color.Lerp(col, Color.white, .08f * (1 - fy));
                        c.a = alpha; px[y * N + x] = c;
                    }
                    t.SetPixels(px); t.Apply(false, true);
                    leafSprites[s] = Sprite.Create(t, new Rect(0, 0, N, N), new Vector2(.5f, .1f), 100f);
                }
                return leafSprites;
            }
        }

        static Sprite TwigSprite
        {
            get
            {
                if (twigSprite) return twigSprite;
                const int N = 96; var t = new Texture2D(N, N, TextureFormat.RGBA32, false) { name = "PauseTwig" };
                var px = new Color[N * N]; var bark = PhoneUi.Hex("#5A4528");
                void Stroke(Vector2 a, Vector2 b, float r)
                {
                    for (int y = 0; y < N; y++) for (int x = 0; x < N; x++)
                    {
                        var p = new Vector2(x, y); var ab = b - a; float k = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                        float d = Vector2.Distance(p, a + ab * k), rr = Mathf.Lerp(r, r * .45f, k);
                        float alpha = Mathf.Clamp01(rr - d + .5f);
                        if (alpha > px[y * N + x].a) { var c = bark; c.a = alpha; px[y * N + x] = c; }
                    }
                }
                Stroke(new Vector2(48, 4), new Vector2(50, 90), 3.2f);
                Stroke(new Vector2(49, 34), new Vector2(76, 58), 2.2f);
                Stroke(new Vector2(50, 56), new Vector2(24, 78), 2f);
                Stroke(new Vector2(50, 72), new Vector2(66, 88), 1.6f);
                t.SetPixels(px); t.Apply(false, true);
                twigSprite = Sprite.Create(t, new Rect(0, 0, N, N), new Vector2(.5f, .05f), 100f);
                return twigSprite;
            }
        }
    }

    static class RectExt
    {
        /// <summary>Anchors (min x/y, max x/y) and offsets (left, bottom, right, top) in one call.</summary>
        public static void Anchor(this RectTransform rt, float ax0, float ay0, float ax1, float ay1, float l, float b, float r, float t)
        {
            rt.anchorMin = new Vector2(ax0, ay0); rt.anchorMax = new Vector2(ax1, ay1); rt.offsetMin = new Vector2(l, b); rt.offsetMax = new Vector2(r, t);
        }
    }
}
