using System;
using System.Collections.Generic;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Session;
using OnlyVolunteers.UI.Pause;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace OnlyVolunteers.UI.MainMenu
{
    /// <summary>What the start menu needs from the world/network side. Stage 2 (scene placement) implements it on the menu
    /// scene's session object: the five world slots (WP07), hosting/joining through the existing FishNet session and loading
    /// the world. Outcomes come back through <see cref="W86MainMenuV01.Report"/> (Connected, ConnectFailed + the real
    /// transport reason, Disconnected, SessionStarted, LaunchFailed).</summary>
    public interface IMainMenuBackend
    {
        IReadOnlyList<WorldSlotCard> Slots();
        /// <summary>The lobby while hosting or joined (null otherwise).</summary>
        LobbyRoster Lobby { get; }
        void HostLobby(int slot);
        void Connect(string address, ushort port);
        void Leave();
        void SetReady(bool ready);
        /// <summary>New world: the mode is already fixed in WorldSessionV01; start it with the lobby's ready participants.</summary>
        void StartNewWorld(int slot, WorldMode mode);
        void LoadWorld(int slot);
        /// <summary>Does the player avatar have this mesh part? (null binding = no model yet: only colours are offered)</summary>
        bool HasPart(AppearanceSlot slot, string optionId);
    }

    /// <summary>
    /// W86 start menu (PLAYER stage, 29.10): the UI of <see cref="MainMenuFlow"/> — Continue / New game (Solo or Multiplayer,
    /// chosen once) / Load (five world cards with their mode) / Join / Appearance / Settings / Quit. Built in code like the
    /// pause menu (camo palette, Segoe fonts) with square 90-degree corners everywhere. Settings → Graphics opens the pause
    /// menu's own graphics page (W86PauseMenuV01.OpenGraphicsFromMenu: same Apply/Keep/Revert, Low default); Sound offers
    /// only the master volume (no mixer buses exist); no language row (no localisation system exists). The customiser edits
    /// the local look (AppearanceProfileV01) with a flat full-body swatch figure and turns an optional 3D preview root.
    /// NOT placed in any scene yet (stage 2); without a backend the world/network buttons report that honestly.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class W86MainMenuV01 : MonoBehaviour
    {
        [Tooltip("A component implementing IMainMenuBackend (stage 2). Empty = UI only.")]
        public MonoBehaviour Backend;
        [Tooltip("Optional 3D avatar preview root, turned slowly while the customiser is open.")]
        public Transform PreviewRoot;
        public float PreviewDegreesPerSecond = 30f;

        static readonly Color Dim = new(0.02f, 0.03f, 0.01f, .72f), Card = PhoneUi.Hex("#2B3022", .96f), Frame = PhoneUi.Hex("#9C8F5E"),
            Band = PhoneUi.Hex("#353B29", .96f), Accent = PhoneUi.Hex("#E9D49A"), Text1 = PhoneUi.Hex("#F4F1E4"), Text2 = PhoneUi.Hex("#B9B795"),
            Dimmed = PhoneUi.Hex("#7F8468"), BtnBg = PhoneUi.Hex("#4A4F35"), BtnHover = PhoneUi.Hex("#5C6343"), BtnPress = PhoneUi.Hex("#6B7350"),
            Go = PhoneUi.Hex("#5D7F36"), GoHover = PhoneUi.Hex("#6E9440"), Bad = PhoneUi.Hex("#C7664F");

        MainMenuFlow flow;
        IMainMenuBackend backend;
        PlayerAppearance draft;
        GameObject canvasGo, page;
        string address = "127.0.0.1", port = "7770";
        GameObject ownedEventSystem;
        bool graphicsOverlay;

        public MenuScreen CurrentScreen => flow != null ? flow.Screen : MenuScreen.Main;

        void Awake()
        {
            backend = Backend as IMainMenuBackend;
            flow = new MainMenuFlow(() => backend != null ? backend.Slots() : Array.Empty<WorldSlotCard>());
            draft = AppearanceProfileV01.Load();
        }

        void Start()
        {
            W86GraphicsSettingsV01.ApplySavedAtStartup();
            W86AudioSettingsV01.ApplySavedAtStartup();
            EnsureEventSystem();
            BuildCanvas();
            Render();
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
        }

        void OnDestroy() { if (ownedEventSystem) Destroy(ownedEventSystem); }

        void Update()
        {
            if (PreviewRoot != null && flow.Screen == MenuScreen.Customise)
                PreviewRoot.Rotate(0f, PreviewDegreesPerSecond * Time.unscaledDeltaTime, 0f, Space.World);
            if (graphicsOverlay) return; // the pause menu's graphics page owns Escape while it is open
            var kb = Keyboard.current;
            bool esc = Input.GetKeyDown(KeyCode.Escape) || (kb != null && kb.escapeKey.wasPressedThisFrame);
            if (!esc) return;
            OvMenuGate.ConsumeEscape(); // the start menu owns Escape in its scene: the pause menu never opens here
            Report(MenuInput.Of(MenuAction.Back));
        }

        /// <summary>Feeds one action/outcome into the flow, performs its command and redraws.</summary>
        public void Report(MenuInput input)
        {
            Perform(flow.Apply(input));
            Render();
        }

        void Do(MenuAction a) => Report(MenuInput.Of(a));

        void Perform(MenuCommand c)
        {
            switch (c.Kind)
            {
                case MenuCommandKind.SaveAppearance: AppearanceProfileV01.Save(draft); break;
                case MenuCommandKind.OpenGraphics:
                {
                    var pause = FindAnyObjectByType<W86PauseMenuV01>();
                    if (pause == null) { Debug.LogWarning("[OV Menu] no W86PauseMenuV01 in this scene: graphics page unavailable"); flow.Apply(MenuInput.Of(MenuAction.Back)); break; }
                    graphicsOverlay = true;
                    pause.OpenGraphicsFromMenu(() => { graphicsOverlay = false; Report(MenuInput.Of(MenuAction.Back)); });
                    break;
                }
                case MenuCommandKind.QuitGame:
#if UNITY_EDITOR
                    UnityEditor.EditorApplication.isPlaying = false;
#else
                    Application.Quit();
#endif
                    break;
                case MenuCommandKind.StartNewWorld:
                    if (!NeedBackend()) break;
                    WorldSessionV01.BeginNewWorld(c.Mode); // the one moment the mode is chosen
                    backend.StartNewWorld(c.Slot, c.Mode);
                    break;
                case MenuCommandKind.LoadWorld:
                    if (!NeedBackend()) break;
                    if (c.LegacyChoice != WorldMode.Unset) WorldSessionV01.RequestLegacyChoice(c.LegacyChoice);
                    backend.LoadWorld(c.Slot);
                    break;
                case MenuCommandKind.HostLobby: if (NeedBackend()) backend.HostLobby(c.Slot); break;
                case MenuCommandKind.ConnectToHost: if (NeedBackend()) backend.Connect(c.Address, c.Port); break;
                case MenuCommandKind.LeaveSession: backend?.Leave(); break;
                case MenuCommandKind.SetReady: backend?.SetReady(c.Flag); break;
            }
        }

        bool NeedBackend()
        {
            if (backend != null) return true;
            flow.Apply(MenuInput.Failure(MenuAction.LaunchFailed, "Меню ещё не подключено к миру и сети (этап 2): запуск отсюда пока недоступен."));
            return false;
        }

        // ---------------------------------------------------------------- screens
        void Render()
        {
            if (canvasGo == null) return;
            if (page != null) Destroy(page);
            switch (flow.Screen)
            {
                case MenuScreen.Main: RenderMain(); break;
                case MenuScreen.NewGameMode:
                    Page("Новая игра", 760, 520);
                    Note("Режим выбирается один раз при создании мира и потом не меняется.");
                    Button("Одиночная игра", () => Do(MenuAction.ChooseSolo), true, 76);
                    Note("Только вы. К одиночному миру нельзя подключиться.");
                    Button("Совместная игра (до 4)", () => Do(MenuAction.ChooseMultiplayer), true, 76);
                    Note("Друзья подключаются к вашему миру; можно играть и одному.");
                    Button("Назад", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.Customise: RenderCustomise(); break;
                case MenuScreen.SoloSlot:
                case MenuScreen.HostSlot:
                    Page(flow.Screen == MenuScreen.SoloSlot ? "Свободный слот — одиночный мир" : "Свободный слот — совместный мир", 900, 760);
                    SlotList(newWorld: true);
                    Button("Назад", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.HostLobby: RenderLobby(host: true); break;
                case MenuScreen.ClientLobby: RenderLobby(host: false); break;
                case MenuScreen.JoinAddress: RenderJoin(); break;
                case MenuScreen.Connecting:
                    Page("Подключение…", 700, 360);
                    Note("Ждём ответа хоста.");
                    Button("Отмена", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.LoadList:
                    Page("Загрузить мир", 900, 760);
                    SlotList(newWorld: false);
                    Button("Назад", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.LegacyModeChoice:
                    Page("Старый мир: выберите режим", 820, 560);
                    Note("Этот мир создан до выбора режима. Выберите один раз — потом режим не меняется. Деньги, вещи и прогресс мира не трогаются; заставка в нём не запускается.");
                    Button("Одиночный", () => Report(MenuInput.LegacyMode(WorldMode.Solo)), true, 70);
                    Button("Совместный", () => Report(MenuInput.LegacyMode(WorldMode.Multiplayer)), true, 70);
                    Button("Назад", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.Settings:
                    Page("Настройки", 620, 460);
                    Button("Графика", () => Do(MenuAction.OpenGraphics), true, 66);
                    Button("Звук", () => Do(MenuAction.OpenAudio), true, 66);
                    Button("Назад", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.Graphics: break; // the pause menu's graphics page is on screen
                case MenuScreen.Audio: RenderAudio(); break;
                case MenuScreen.QuitConfirm:
                    Page("Выйти из игры?", 620, 340);
                    Button("Выйти", () => Do(MenuAction.ConfirmQuit), true, 62);
                    Button("Отмена", () => Do(MenuAction.Back), false, 56);
                    break;
                case MenuScreen.Launching:
                    Page("Загрузка мира…", 620, 260);
                    break;
                case MenuScreen.Message:
                    Page("", 720, 360);
                    Note(flow.MessageText, Text1, 24);
                    Button("OK", () => Do(MenuAction.Back), true, 58);
                    break;
            }
        }

        void RenderMain()
        {
            Page("VOLUNTEERS ONLY", 620, 820);
            var newest = flow.Newest();
            Button(newest != null ? "Продолжить — " + newest.Name : "Продолжить", () => Do(MenuAction.Continue), newest != null, 66, primary: newest != null);
            Button("Новая игра", () => Do(MenuAction.NewGame), true, 66, primary: newest == null);
            Button("Загрузить", () => Do(MenuAction.Load), true, 60);
            Button("Присоединиться", () => Do(MenuAction.Join), true, 60);
            Button("Внешность", () => Do(MenuAction.EditAppearance), true, 60);
            Button("Настройки", () => Do(MenuAction.Settings), true, 60);
            Button("Выход", () => Do(MenuAction.Quit), true, 60);
        }

        void RenderCustomise()
        {
            Page(flow.DraftJoining ? "Ваша внешность (для чужого мира)" : "Внешность", 1240, 900);
            var body = Row(page.transform.Find("List"), 640);
            var left = Column(body.transform, 760);
            Func<AppearanceSlot, string, bool> present = backend != null ? backend.HasPart : (Func<AppearanceSlot, string, bool>)null;
            foreach (var slot in AppearanceCatalogV01.Slots)
            {
                var s = slot;
                var options = AppearanceRules.Selectable(s, present);
                var current = AppearanceCatalogV01.Find(s, draft.Get(s));
                bool usable = options.Count > 0;
                Stepper(left.transform, AppearanceCatalogV01.SlotLabel(s),
                    usable ? (current != null ? current.Label : "") : "появится с моделью игрока",
                    usable ? (Action<int>)(dir => { draft.Set(s, AppearanceRules.Cycle(s, draft.Get(s), dir, present)); Render(); }) : null,
                    AppearanceCatalogV01.IsColourSlot(s) && current != null ? current.Hex : null);
            }
            var right = Column(body.transform, 380);
            Figure(right.transform);
            Note("Только внешний вид: не влияет на рост, скорость, силу и деньги.");
            var foot = Row(page.transform.Find("List"), 66);
            Button(foot.transform, "Готово", () => Do(MenuAction.ConfirmAppearance), true, 0, primary: true);
            Button(foot.transform, "По умолчанию", () => { draft = AppearanceRules.Default(); Render(); }, true, 0);
            Button(foot.transform, "Назад", () => { draft = AppearanceProfileV01.Load(); Do(MenuAction.Back); }, true, 0);
        }

        void RenderLobby(bool host)
        {
            Page(host ? "Лобби — вы хост" : "Лобби", 860, 760);
            var lobby = backend?.Lobby;
            if (lobby == null) Note("Нет данных лобби.");
            else foreach (var m in lobby.Members)
                    Note((m.IsHost ? "★ " : "• ") + (string.IsNullOrEmpty(m.Name) ? m.PlayerId : m.Name) + (m.IsHost || m.Ready ? " — готов" : " — не готов"),
                        m.IsHost || m.Ready ? Text1 : Text2, 24);
            if (host)
            {
                string why = "";
                bool can = lobby != null && lobby.CanStart(out why);
                if (!can && !string.IsNullOrEmpty(why)) Note(why, Bad, 18);
                Button("Начать (заставка)", () => Do(MenuAction.StartSession), can, 68, primary: true);
            }
            else Button(flow.LocalReady ? "Не готов" : "Готов", () => Do(MenuAction.ToggleReady), true, 68, primary: !flow.LocalReady);
            Button(host ? "Закрыть лобби" : "Выйти из лобби", () => Do(MenuAction.Back), true, 56);
        }

        void RenderJoin()
        {
            Page("Присоединиться", 760, 560);
            Note("Адрес и порт компьютера хоста (локальная сеть или прямое подключение). Steam-поиска пока нет.");
            Field("Адрес", address, s => address = s);
            Field("Порт", port, s => port = s);
            if (!string.IsNullOrEmpty(flow.ErrorText)) Note(flow.ErrorText, Bad, 20);
            Button("Подключиться", () =>
            {
                ushort.TryParse(port, out ushort p);
                Report(MenuInput.Address(address, p));
            }, true, 66, primary: true);
            Button("Назад", () => Do(MenuAction.Back), false, 56);
        }

        void RenderAudio()
        {
            Page("Звук", 820, 420);
            float v = W86AudioSettingsV01.LoadMaster();
            int i = W86AudioSettingsV01.NearestStep(v);
            Stepper(page.transform.Find("List"), "Общая громкость", W86AudioSettingsV01.Steps[i] + "%", dir =>
            {
                int k = Mathf.Clamp(i + dir, 0, W86AudioSettingsV01.Steps.Length - 1);
                W86AudioSettingsV01.ApplyMaster(W86AudioSettingsV01.Steps[k] / 100f, true);
                Render();
            }, null);
            Note("Раздельной громкости музыки и эффектов пока нет: в проекте нет микшера.");
            Button("Назад", () => Do(MenuAction.Back), false, 56);
        }

        void SlotList(bool newWorld)
        {
            var cards = backend != null ? backend.Slots() : Array.Empty<WorldSlotCard>();
            for (int i = 0; i < MainMenuFlow.SlotCount; i++)
            {
                WorldSlotCard card = null;
                foreach (var c in cards) if (c.Index == i) card = c;
                bool occupied = card != null && card.Occupied;
                string title = occupied ? $"{i + 1}. {card.Name}" : $"{i + 1}. Свободно";
                string sub = occupied ? (WorldModeRules.CardLabel(card.Mode) + (string.IsNullOrEmpty(card.SavedText) ? "" : " · " + card.SavedText) +
                                         (card.Loadable ? "" : " · " + card.Problem)) : "";
                bool enabled = newWorld ? !occupied : occupied;
                int slot = i;
                var b = Button(occupied ? title + "\n" + sub : title, () => Report(MenuInput.SlotPick(slot)), enabled, 92);
                b.GetComponentInChildren<Text>().fontSize = 22;
            }
            if (!string.IsNullOrEmpty(flow.ErrorText)) Note(flow.ErrorText, Bad, 18);
        }

        /// <summary>Flat full-body swatch figure (until the 3D avatar preview exists): hair, head, torso, arms, legs.</summary>
        void Figure(Transform parent)
        {
            var box = Img(parent, "Figure", Band);
            box.gameObject.AddComponent<LayoutElement>().preferredHeight = 520;
            Color skin = AppearanceProfileV01.Swatch(draft, AppearanceSlot.Skin, Color.white);
            Color hair = AppearanceProfileV01.Swatch(draft, AppearanceSlot.HairColour, Color.black);
            Color top = AppearanceProfileV01.Swatch(draft, AppearanceSlot.TopColour, Color.grey);
            Color bottom = AppearanceProfileV01.Swatch(draft, AppearanceSlot.BottomColour, Color.grey);
            void Part(string n, Color c, float x, float y, float w, float h)
            {
                var r = Img(box.transform, n, c).rectTransform;
                r.anchorMin = r.anchorMax = new Vector2(.5f, 0f); r.pivot = new Vector2(.5f, 0f);
                r.sizeDelta = new Vector2(w, h); r.anchoredPosition = new Vector2(x, y);
            }
            Part("LegL", bottom, -26, 40, 40, 190); Part("LegR", bottom, 26, 40, 40, 190);
            Part("Torso", top, 0, 225, 120, 150); Part("ArmL", top, -78, 245, 32, 130); Part("ArmR", top, 78, 245, 32, 130);
            Part("HandL", skin, -78, 225, 28, 24); Part("HandR", skin, 78, 225, 28, 24);
            Part("Head", skin, 0, 380, 74, 84); Part("Hair", hair, 0, 446, 80, 24);
            Part("ShoeL", PhoneUi.Hex("#26272A"), -26, 26, 46, 16); Part("ShoeR", PhoneUi.Hex("#26272A"), 26, 26, 46, 16);
        }

        // ---------------------------------------------------------------- UI building (square corners, camo palette)
        void BuildCanvas()
        {
            canvasGo = new GameObject("[Menu] Start", typeof(RectTransform));
            canvasGo.transform.SetParent(transform, false); canvasGo.layer = 5;
            var canvas = canvasGo.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 150; // under the pause overlay (200)
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = .5f;
            canvasGo.AddComponent<GraphicRaycaster>();
            var dim = Img(canvasGo.transform, "Dim", Dim); Stretch(dim.rectTransform);
        }

        void Page(string title, float w, float h)
        {
            page = new GameObject("Page", typeof(RectTransform)); page.transform.SetParent(canvasGo.transform, false); page.layer = 5;
            var rt = (RectTransform)page.transform; rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(.5f, .5f); rt.sizeDelta = new Vector2(w, h);
            var frame = Img(page.transform, "Frame", Frame); Stretch(frame.rectTransform);
            var card = Img(page.transform, "Card", Card); card.rectTransform.Anchor(0, 0, 1, 1, 8, 8, -8, -8);
            if (!string.IsNullOrEmpty(title))
            {
                var t = Label(page.transform, title, 40, Accent, TextAnchor.UpperCenter, true); t.fontStyle = FontStyle.Italic;
                t.rectTransform.Anchor(0, 1, 1, 1, 24, -84, -24, -22);
            }
            var list = new GameObject("List", typeof(RectTransform)); list.transform.SetParent(page.transform, false);
            ((RectTransform)list.transform).Anchor(0, 0, 1, 1, 48, 36, -48, string.IsNullOrEmpty(title) ? -36 : -104);
            var v = list.AddComponent<VerticalLayoutGroup>(); v.spacing = 12; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            v.childAlignment = TextAnchor.UpperCenter;
        }

        Transform List => page.transform.Find("List");

        GameObject Row(Transform parent, float height)
        {
            var go = new GameObject("Row", typeof(RectTransform)); go.transform.SetParent(parent, false);
            go.AddComponent<LayoutElement>().preferredHeight = height;
            var h = go.AddComponent<HorizontalLayoutGroup>(); h.spacing = 16; h.childControlWidth = true; h.childControlHeight = true; h.childForceExpandWidth = true;
            return go;
        }

        GameObject Column(Transform parent, float width)
        {
            var go = new GameObject("Column", typeof(RectTransform)); go.transform.SetParent(parent, false);
            go.AddComponent<LayoutElement>().preferredWidth = width;
            var v = go.AddComponent<VerticalLayoutGroup>(); v.spacing = 6; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            return go;
        }

        void Note(string text, Color? color = null, int size = 19)
        {
            text ??= "";
            var t = Label(List, text, size, color ?? Text2, TextAnchor.MiddleCenter);
            t.gameObject.AddComponent<LayoutElement>().preferredHeight = Mathf.Max(30, size * 1.5f * (1 + text.Length / 70));
        }

        Button Button(string text, Action onClick, bool enabled, float height, bool primary = false) => Button(List, text, onClick, enabled, height, primary);

        Button Button(Transform parent, string text, Action onClick, bool enabled, float height, bool primary = false)
        {
            var img = Img(parent, text, Color.white); // square, 90-degree corners
            var b = img.gameObject.AddComponent<UnityEngine.UI.Button>();
            var c = b.colors;
            c.normalColor = primary ? Go : BtnBg; c.highlightedColor = primary ? GoHover : BtnHover; c.pressedColor = BtnPress;
            c.selectedColor = primary ? GoHover : BtnHover; c.disabledColor = new Color(BtnBg.r, BtnBg.g, BtnBg.b, .45f); c.colorMultiplier = 1f; c.fadeDuration = .06f;
            b.colors = c; b.interactable = enabled;
            if (onClick != null) b.onClick.AddListener(() => onClick());
            if (height > 0) img.gameObject.AddComponent<LayoutElement>().preferredHeight = height;
            var edge = img.gameObject.AddComponent<Outline>(); edge.effectColor = Frame; edge.effectDistance = new Vector2(2.5f, -2.5f);
            var t = Label(img.transform, text, 25, enabled ? Text1 : Dimmed, TextAnchor.MiddleCenter, true); Stretch(t.rectTransform);
            return b;
        }

        void Stepper(Transform parent, string label, string value, Action<int> step, string swatchHex)
        {
            var row = Img(parent, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 58;
            Label(row.transform, label, 22, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .38f, 1, 18, 0, 0, 0);
            var v = Label(row.transform, value, 22, step != null ? Text1 : Dimmed, TextAnchor.MiddleCenter, step != null);
            v.rectTransform.Anchor(.38f, 0, 1, 1, 60, 0, -60, 0);
            if (!string.IsNullOrEmpty(swatchHex))
            {
                var sw = Img(row.transform, "Swatch", PhoneUi.Hex(swatchHex)); sw.rectTransform.Anchor(.38f, .5f, .38f, .5f, 62, -14, 90, 14);
            }
            if (step == null) return;
            var l = Button(row.transform, "‹", () => step(-1), true, 0); ((RectTransform)l.transform).Anchor(.38f, 0, .38f, 1, 0, 6, 46, -6);
            var r = Button(row.transform, "›", () => step(1), true, 0); ((RectTransform)r.transform).Anchor(1, 0, 1, 1, -52, 6, -6, -6);
        }

        InputField Field(string label, string value, Action<string> changed)
        {
            var row = Img(List, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 60;
            Label(row.transform, label, 22, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .3f, 1, 18, 0, 0, 0);
            var box = Img(row.transform, "Input", PhoneUi.Hex("#1E2218")); box.rectTransform.Anchor(.3f, 0, 1, 1, 0, 8, -12, -8);
            var text = Label(box.transform, "", 22, Text1, TextAnchor.MiddleLeft); text.rectTransform.Anchor(0, 0, 1, 1, 12, 0, -12, 0);
            text.supportRichText = false;
            var field = box.gameObject.AddComponent<InputField>(); field.textComponent = text; field.text = value; field.characterLimit = 64;
            field.onValueChanged.AddListener(s => changed(s));
            return field;
        }

        static Image Img(Transform parent, string name, Color c)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image)); go.transform.SetParent(parent, false); go.layer = 5;
            var img = go.GetComponent<Image>(); img.color = c; // no sprite: square corners
            return img;
        }

        static Text Label(Transform parent, string text, int size, Color c, TextAnchor anchor, bool heavy = false)
        {
            var go = new GameObject("Text", typeof(RectTransform), typeof(Text)); go.transform.SetParent(parent, false); go.layer = 5;
            var t = go.GetComponent<Text>(); t.text = text ?? ""; t.fontSize = size; t.color = c; t.alignment = anchor;
            t.font = heavy ? PhoneUi.Heavy : PhoneUi.Regular; t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow;
            if (heavy) { var sh = go.AddComponent<Shadow>(); sh.effectColor = new Color(0.06f, 0.07f, 0.03f, .85f); sh.effectDistance = new Vector2(2f, -2f); }
            return t;
        }

        static void Stretch(RectTransform rt) { rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero; }

        void EnsureEventSystem()
        {
            if (EventSystem.current != null || FindAnyObjectByType<EventSystem>() != null) return;
            ownedEventSystem = new GameObject("[Menu] EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        }
    }
}
