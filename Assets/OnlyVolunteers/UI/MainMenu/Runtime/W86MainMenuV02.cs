using System;
using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Session;
using OnlyVolunteers.UI.Pause;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace OnlyVolunteers.UI.MainMenu
{
    /// <summary>
    /// W86 start menu v2 (Fedya 29.10: "a normal menu like the co-op indies"): a full-screen shot of our world (the forest
    /// wagon, rendered by the game, slowly drifting), the title top-left, a vertical list of big buttons (Продолжить only
    /// with a save, Играть, Присоединиться, Настройки, Выход) with hover/press feedback and sound, the version bottom-right.
    /// Sub-screens are square-cornered camo cards (the pause menu's palette) with a back button; Esc = back. Играть → five
    /// world cards (name, Соло/Кооп, date, play time; New / Load / Delete with a confirm) → new world (name, Solo / Co-op
    /// chosen once, intro on/off) → the sausage customiser (rotating 3D preview) → the world / the host lobby (players,
    /// ready, connect info). Settings: tabs Графика (the pause menu's own graphics page: Apply / Defaults / Keep-Revert, Low
    /// default), Звук (the mixer buses, Apply / Revert), Управление (the current keys; no rebinding exists). The flow is the
    /// pure <see cref="MainMenuFlowV2"/>; worlds are <see cref="WorldSlotsV01"/> + <see cref="WorldLaunchV01"/>; the lobby
    /// is <see cref="W86MenuLobbyV01"/>. UI built in code (uGUI), no prefab.
    /// 31.10 (menu for V2): <see cref="Edition"/> picks the game. V1Map (MainMenu_v01, the default) is unchanged. V2
    /// (MainMenu_V2_v01): Играть loads <see cref="GameScenePath"/> (VanOnly_v01), own five slots, no prologue choice, no
    /// "old world" screen, a plain dark gradient instead of the backdrop shot, no version label, the V2 controls and honest
    /// co-op texts (<see cref="MainMenuTextsV2"/>). The menu sets <see cref="WorldLaunchV01.Target"/> on Awake.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class W86MainMenuV02 : MonoBehaviour
    {
        public W86MenuLobbyV01 Lobby;
        public W86AvatarPreviewV01 Preview;
        [Tooltip("The backdrop shot (V1: UI/MainMenu/Art/MenuBackdrop_Wagon_v01.jpg). Empty in V2: a plain dark gradient.")]
        public Texture2D Backdrop;
        public AudioClip ClickClip, HoverClip;
        [Tooltip("Shown in the footer after the title; empty = none (V2).")]
        public string VersionLabel = "W86";
        [Header("Game (31.10)")]
        [Tooltip("V1Map = the W86 map menu (MainMenu_v01: the map, its old save, the prologue). V2 = MainMenu_V2_v01: VanOnly, own saves, no prologue.")]
        public GameEditionV01 Edition = GameEditionV01.V1Map;
        [Tooltip("The scene Играть loads; empty = the edition's default (V1: Map_W85_Play_v02, V2: VanOnly_v01). Must be in Build Settings.")]
        public string GameScenePath = "";

        bool V2 => Edition == GameEditionV01.V2;

        // the pause menu's camo palette
        static readonly Color Card = PhoneUi.Hex("#2B3022", .95f), Frame = PhoneUi.Hex("#9C8F5E"), Band = PhoneUi.Hex("#353B29", .96f),
            Band2 = PhoneUi.Hex("#30352A", .96f), Accent = PhoneUi.Hex("#E9D49A"), Text1 = PhoneUi.Hex("#F4F1E4"), Text2 = PhoneUi.Hex("#B9B795"),
            Dimmed = PhoneUi.Hex("#7F8468"), BtnBg = PhoneUi.Hex("#4A4F35", .94f), BtnHover = PhoneUi.Hex("#5C6343"), BtnPress = PhoneUi.Hex("#6B7350"),
            Go = PhoneUi.Hex("#5D7F36"), GoHover = PhoneUi.Hex("#6E9440"), Bad = PhoneUi.Hex("#C7664F"), Good = PhoneUi.Hex("#8FC25A"),
            Danger = PhoneUi.Hex("#7A3A2C"), DangerHover = PhoneUi.Hex("#934634");

        MainMenuFlowV2 flow;
        PlayerAppearance draft;
        GameObject canvasGo, title, mainList, page, footer;
        RawImage backdrop;
        Image shade;
        AudioSource sfx;
        GameObject ownedEventSystem;
        string address = "127.0.0.1", port = WorldLaunchV01.DefaultPort.ToString();
        bool graphicsOverlay;
        int settingsTab;
        readonly float[] audioDraft = new float[4];
        bool audioDirty;
        List<WorldSlotCard> cards = new List<WorldSlotCard>();
        float lastRenderAt;

        public MenuScreenV2 CurrentScreen => flow != null ? flow.Screen : MenuScreenV2.Main;
        public MainMenuFlowV2 Flow => flow;

        void Awake()
        {
            // which game Играть starts and where the pause menu comes back to (this menu's own scene)
            WorldLaunchV01.Configure(WorldLaunchTargetV01.For(Edition, GameScenePath, gameObject.scene.path));
            flow = new MainMenuFlowV2(() => cards);
            draft = AppearanceProfileV01.Load();
            if (Lobby != null) { Lobby.Report += Report; Lobby.Changed += OnLobbyChanged; }
        }

        void Start()
        {
            Time.timeScale = 1f;
            AudioListener.pause = false;
            W86GraphicsSettingsV01.ApplySavedAtStartup();
            OvAudioMixerV01.ApplySaved();
            RefreshCards();
            EnsureEventSystem();
            sfx = new GameObject("[Menu] Sound").AddComponent<AudioSource>();
            sfx.transform.SetParent(transform, false);
            sfx.playOnAwake = false; sfx.spatialBlend = 0f;
            sfx.outputAudioMixerGroup = OvAudioMixerV01.Group(OvAudioBus.VoiceUi);
            if (HoverClip == null) HoverClip = Tick(1250f, 0.035f, 0.18f);
            if (ClickClip == null) ClickClip = Tick(620f, 0.07f, 0.35f);
            BuildCanvas();
            Render();
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            Debug.Log($"[OV Menu] start menu v2: {cards.FindAll(c => c.Occupied).Count} world(s), continue={flow.CanContinue}");
        }

        void OnDestroy()
        {
            if (Lobby != null) { Lobby.Report -= Report; Lobby.Changed -= OnLobbyChanged; }
            if (ownedEventSystem) Destroy(ownedEventSystem);
        }

        void OnLobbyChanged()
        {
            if (flow.Screen == MenuScreenV2.HostLobby || flow.Screen == MenuScreenV2.ClientLobby) Render();
        }

        void Update()
        {
            DriftBackdrop();
            if (graphicsOverlay) return; // the pause menu's graphics page owns Escape while it is open
            var kb = Keyboard.current;
            bool esc = Input.GetKeyDown(KeyCode.Escape) || (kb != null && kb.escapeKey.wasPressedThisFrame);
            if (esc)
            {
                OvMenuGate.ConsumeEscape(); // the start menu owns Escape in its scene: the pause menu never opens here
                if (flow.Screen != MenuScreenV2.Main) Back();
                return;
            }
            bool nav = kb != null && (kb.upArrowKey.wasPressedThisFrame || kb.downArrowKey.wasPressedThisFrame || kb.tabKey.wasPressedThisFrame);
            if (nav && EventSystem.current != null && EventSystem.current.currentSelectedGameObject == null)
            {
                var first = (page != null ? page : mainList)?.GetComponentInChildren<Selectable>();
                if (first != null) first.Select();
            }
        }

        // ================================================================== flow

        public void Report(MenuInputV2 input)
        {
            Perform(flow.Apply(input));
            Render();
        }

        void Do(MenuActionV2 a) => Report(MenuInputV2.Of(a));

        void Back()
        {
            if (flow.Screen == MenuScreenV2.Settings && audioDirty) RevertAudio();
            if (flow.Screen == MenuScreenV2.Customise) draft = AppearanceProfileV01.Load();
            Do(MenuActionV2.Back);
        }

        void Perform(MenuCommandV2 c)
        {
            switch (c.Kind)
            {
                case MenuCommandKindV2.SaveAppearance:
                    AppearanceProfileV01.Save(draft);
                    Perform(flow.FollowUpAfterAppearance());
                    break;
                case MenuCommandKindV2.HostLobby:
                {
                    string herr = "нет сетевого лобби в сцене меню.";
                    if (Lobby == null || !Lobby.Host(WorldLaunchV01.DefaultPort, c.Name, out herr))
                        flow.Apply(MenuInputV2.WithText(MenuActionV2.LaunchFailed, "Лобби не открылось: " + herr));
                }
                    break;
                case MenuCommandKindV2.StartNewWorld:
                {
                    int participants = Participants();
                    var cmd = c;
                    Launch(() =>
                    {
                        if (!WorldLaunchV01.StartNew(cmd.Slot, cmd.Mode, cmd.Name, cmd.SkipIntro, participants, WorldLaunchV01.DefaultPort, out string e))
                            Report(MenuInputV2.WithText(MenuActionV2.LaunchFailed, e));
                    });
                    break;
                }
                case MenuCommandKindV2.LoadWorld:
                {
                    int participants = Participants();
                    var cmd = c;
                    Launch(() =>
                    {
                        if (!WorldLaunchV01.StartLoad(cmd.Slot, cmd.Mode, cmd.LegacyChoice, participants, WorldLaunchV01.DefaultPort, out string e))
                            Report(MenuInputV2.WithText(MenuActionV2.LaunchFailed, e));
                    });
                    break;
                }
                case MenuCommandKindV2.DeleteWorld:
                    if (!WorldSlotsV01.Delete(c.Slot, out string derr)) flow.Apply(MenuInputV2.WithText(MenuActionV2.LaunchFailed, "Не удалось удалить: " + derr));
                    RefreshCards();
                    break;
                case MenuCommandKindV2.ConnectToHost:
                {
                    string cerr = "Нет сетевого лобби в сцене меню.";
                    if (Lobby == null || !Lobby.Connect(c.Address, c.Port, out cerr))
                        flow.Apply(MenuInputV2.WithText(MenuActionV2.ConnectFailed, cerr));
                }
                    break;
                case MenuCommandKindV2.LeaveSession: Lobby?.Shutdown(true); break;
                case MenuCommandKindV2.SetReady: Lobby?.SetReady(c.Flag); break;
                case MenuCommandKindV2.QuitGame:
#if UNITY_EDITOR
                    UnityEditor.EditorApplication.isPlaying = false;
#else
                    Application.Quit();
#endif
                    break;
            }
        }

        int Participants()
        {
            if (Lobby == null || Lobby.Current != W86MenuLobbyV01.Role.Host) return 1;
            return Mathf.Max(1, Lobby.Roster.StartingParticipants().Count);
        }

        /// <summary>Host lobby: tell the guests and close it; then release the menu's network and load the world.</summary>
        void Launch(Action load)
        {
            void Go()
            {
                Lobby?.ReleaseForWorld();
                load();
            }
            if (Lobby != null && Lobby.Current == W86MenuLobbyV01.Role.Host) Lobby.HostStart(Go);
            else Go();
        }

        void RefreshCards() { cards = WorldSlotsV01.Cards(); }

        // ================================================================== screens

        void Render()
        {
            if (canvasGo == null) return;
            lastRenderAt = Time.unscaledTime;
            if (page != null) Destroy(page);
            page = null;
            bool main = flow.Screen == MenuScreenV2.Main;
            mainList.SetActive(main);
            title.SetActive(main); // the sub-screen cards take the middle of the screen
            shade.color = main ? new Color(1, 1, 1, 1) : new Color(1, 1, 1, .55f);
            if (Preview != null) Preview.Show(flow.Screen == MenuScreenV2.Customise);
            switch (flow.Screen)
            {
                case MenuScreenV2.Main: RenderMain(); break;
                case MenuScreenV2.Worlds: RenderWorlds(); break;
                case MenuScreenV2.NewWorld: RenderNewWorld(); break;
                case MenuScreenV2.Customise: RenderCustomise(); break;
                case MenuScreenV2.HostLobby: RenderLobby(true); break;
                case MenuScreenV2.ClientLobby: RenderLobby(false); break;
                case MenuScreenV2.JoinAddress: RenderJoin(); break;
                case MenuScreenV2.Connecting:
                {
                    var body = Panel("Подключение…", 760, 380);
                    Note(body, "Подключаемся к " + address + ":" + port + ". Ждём ответа хоста.", Text1, 24);
                    Foot(body, ("Отмена", Back, false));
                    break;
                }
                case MenuScreenV2.LegacyModeChoice when V2: // V2 has no old worlds (WorldSlotsV01 never offers one); never shown
                {
                    var body = Panel("", 800, 320);
                    Note(body, MainMenuTextsV2.NoWorldHere, Text1, 24);
                    Foot(body, ("‹  Назад", Back, false));
                    break;
                }
                case MenuScreenV2.LegacyModeChoice:
                {
                    var body = Panel("Старый мир: выберите режим", 900, 560);
                    Note(body, "«" + flow.DraftName + "» создан до выбора режима. Выберите один раз — потом режим не меняется. Деньги, вещи и прогресс не трогаются; вступление в нём не запускается.", Text2, 21);
                    var row = Row(body, 120);
                    Big(row.transform, "Соло", "только вы", () => Report(MenuInputV2.WithMode(MenuActionV2.ChooseLegacyMode, WorldMode.Solo)), false);
                    Big(row.transform, "Кооп", "друзья подключаются к вашему миру", () => Report(MenuInputV2.WithMode(MenuActionV2.ChooseLegacyMode, WorldMode.Multiplayer)), false);
                    Foot(body, ("‹  Назад", Back, false));
                    break;
                }
                case MenuScreenV2.DeleteConfirm:
                {
                    var card = flow.Card(flow.DraftSlot);
                    var body = Panel("Удалить мир?", 800, 420);
                    Note(body, "«" + (card != null ? card.Name : "") + "» (слот " + (flow.DraftSlot + 1) + ") будет удалён вместе с резервными копиями. Это нельзя отменить.", Text1, 23);
                    Foot(body, ("Удалить навсегда", () => Do(MenuActionV2.ConfirmDelete), true, Danger), ("Отмена", Back, false));
                    break;
                }
                case MenuScreenV2.Settings: RenderSettings(); break;
                case MenuScreenV2.QuitConfirm:
                {
                    var body = Panel("Выйти из игры?", 700, 320);
                    Foot(body, ("Выйти", () => Do(MenuActionV2.ConfirmQuit), true, Danger), ("Отмена", Back, false));
                    break;
                }
                case MenuScreenV2.Launching:
                {
                    var body = Panel("", 900, 260);
                    var t = Label(body, "Загрузка мира «" + (string.IsNullOrEmpty(flow.DraftName) ? "…" : flow.DraftName) + "»…", 36, Accent, TextAnchor.MiddleCenter, true);
                    t.gameObject.AddComponent<LayoutElement>().preferredHeight = 120;
                    break;
                }
                case MenuScreenV2.Message:
                {
                    var body = Panel("", 860, 400);
                    var t = Label(body, flow.MessageText, 24, Text1, TextAnchor.MiddleCenter);
                    t.gameObject.AddComponent<LayoutElement>().preferredHeight = 200;
                    Foot(body, ("OK", Back, true));
                    break;
                }
            }
        }

        void RenderMain()
        {
            foreach (Transform c in mainList.transform) Destroy(c.gameObject);
            var newest = flow.Newest();
            if (newest != null) MainButton("Продолжить", "«" + newest.Name + "» · " + newest.SavedText, () => Do(MenuActionV2.Continue), true);
            MainButton("Играть", "миры: новый, загрузить, удалить", () => Do(MenuActionV2.Play), newest == null);
            MainButton("Присоединиться", V2 ? MainMenuTextsV2.JoinSub : "к миру друга по адресу", () => Do(MenuActionV2.Join), false);
            MainButton("Настройки", "графика, звук, управление", () => Do(MenuActionV2.Settings), false);
            MainButton("Выход", "", () => Do(MenuActionV2.Quit), false);
        }

        void RenderWorlds()
        {
            RefreshCards();
            var body = Panel("Миры", 1240, 900);
            Note(body, "Пять слотов. Новый мир — только в свободный слот; удаление спрашивает подтверждение.", Text2, 19);
            for (int i = 0; i < WorldSlotsV01.Count; i++)
            {
                WorldSlotCard card = cards.Find(c => c.Index == i) ?? new WorldSlotCard { Index = i };
                int slot = i;
                var row = Img(body, "Slot" + i, i % 2 == 0 ? Band : Band2);
                row.gameObject.AddComponent<LayoutElement>().preferredHeight = 118;
                var num = Label(row.transform, (i + 1).ToString(), 54, card.Occupied ? Accent : Dimmed, TextAnchor.MiddleCenter, true);
                num.rectTransform.Anchor(0, 0, 0, 1, 10, 0, 96, 0);
                if (card.Occupied)
                {
                    var name = Label(row.transform, card.Name, 30, Text1, TextAnchor.LowerLeft, true);
                    name.rectTransform.Anchor(0, .5f, 1, 1, 110, 0, -420, -10);
                    string mode = card.Mode == WorldModeStatus.Solo ? "СОЛО" : card.Mode == WorldModeStatus.Multiplayer ? "КООП"
                        : V2 ? MainMenuTextsV2.NoModeChip : "СТАРЫЙ МИР · режим не выбран";
                    Chip(row.transform, mode, card.Mode == WorldModeStatus.Multiplayer ? Go : card.Mode == WorldModeStatus.Solo ? PhoneUi.Hex("#4F6B7A") : PhoneUi.Hex("#7A6B45"), 110, 16, mode.Length > 6 ? 330 : 96);
                    var meta = Label(row.transform, card.Loadable ? card.SavedText : card.Problem, 19, card.Loadable ? Text2 : Bad, TextAnchor.MiddleLeft);
                    meta.rectTransform.Anchor(0, 0, 1, .5f, mode.Length > 6 ? 452 : 218, 10, -420, -4);
                    var load = Btn(row.transform, "Загрузить", () => Report(MenuInputV2.OnSlot(MenuActionV2.LoadSlot, slot)), card.Loadable, 0, true, 24);
                    ((RectTransform)load.transform).Anchor(1, 0, 1, 1, -400, 22, -190, -22);
                    var del = Btn(row.transform, "Удалить", () => Report(MenuInputV2.OnSlot(MenuActionV2.DeleteSlot, slot)), true, 0, false, 22, Danger, DangerHover);
                    ((RectTransform)del.transform).Anchor(1, 0, 1, 1, -176, 22, -22, -22);
                }
                else
                {
                    var name = Label(row.transform, "Свободный слот", 28, Dimmed, TextAnchor.MiddleLeft, true);
                    name.rectTransform.Anchor(0, 0, 1, 1, 110, 0, -420, 0);
                    var nw = Btn(row.transform, "Новый мир", () => Report(MenuInputV2.OnSlot(MenuActionV2.NewInSlot, slot)), true, 0, true, 24);
                    ((RectTransform)nw.transform).Anchor(1, 0, 1, 1, -400, 22, -22, -22);
                }
            }
            if (!string.IsNullOrEmpty(flow.ErrorText)) Note(body, flow.ErrorText, Bad, 19);
            Foot(body, ("‹  Назад", Back, false));
        }

        void RenderNewWorld()
        {
            var body = Panel("Новый мир — слот " + (flow.DraftSlot + 1), 1100, 860);
            Field(body, "Название", flow.DraftName, s => flow.Apply(MenuInputV2.WithText(MenuActionV2.SetName, s)), MainMenuFlowV2.MaxNameLength);
            Note(body, "Сколько игроков — выбирается один раз: потом режим мира не меняется.", Accent, 20);
            var row = Row(body, 150);
            Big(row.transform, "Соло", "только вы; к соло-миру нельзя подключиться", () => { Report(MenuInputV2.WithMode(MenuActionV2.SetMode, WorldMode.Solo)); }, flow.DraftMode == WorldMode.Solo);
            Big(row.transform, "Кооп (до 4)", V2 ? MainMenuTextsV2.CoopSub : "друзья подключаются к вашему миру; можно играть и одному", () => { Report(MenuInputV2.WithMode(MenuActionV2.SetMode, WorldMode.Multiplayer)); }, flow.DraftMode == WorldMode.Multiplayer);
            if (!V2) // V2: no prologue (WorldLaunchV01 skips it and the hook never runs)
                Choice(body, "Вступление", new[] { "Показать", "Пропустить" }, flow.DraftSkipIntro ? 1 : 0,
                    i => Report(MenuInputV2.WithFlag(MenuActionV2.SetIntro, i == 0)), "Пролог у вагонов; пропуск ведёт к тому же обучению без наград.");
            if (!string.IsNullOrEmpty(flow.ErrorText)) Note(body, flow.ErrorText, Bad, 20);
            Foot(body, ("Далее — внешность  ›", () => Do(MenuActionV2.ConfirmNewWorld), true), ("‹  Назад", Back, false));
        }

        void RenderCustomise()
        {
            var body = Panel(flow.DraftJoining ? "Твоя сосиска (для чужого мира)" : "Твоя сосиска", 1500, 940);
            var row = Row(body, 690);
            // preview
            var pv = Img(row.transform, "PreviewBox", Band2);
            pv.gameObject.AddComponent<LayoutElement>().preferredWidth = 500;
            if (Preview != null)
            {
                Preview.Show(true);
                Preview.Apply(draft);
                var raw = new GameObject("Preview", typeof(RectTransform), typeof(RawImage));
                raw.transform.SetParent(pv.transform, false);
                var ri = raw.GetComponent<RawImage>(); ri.texture = Preview.Texture; ri.raycastTarget = true;
                ((RectTransform)raw.transform).Anchor(0, 0, 1, 1, 8, 40, -8, -8);
                var trig = raw.AddComponent<EventTrigger>();
                var e = new EventTrigger.Entry { eventID = EventTriggerType.Drag };
                e.callback.AddListener(d => Preview.Drag(((PointerEventData)d).delta.x));
                trig.triggers.Add(e);
                var hint = Label(pv.transform, "тяни мышью, чтобы повернуть", 16, Dimmed, TextAnchor.MiddleCenter);
                hint.rectTransform.Anchor(0, 0, 1, 0, 0, 6, 0, 36);
            }
            else Label(pv.transform, "превью недоступно", 20, Dimmed, TextAnchor.MiddleCenter).rectTransform.Anchor(0, 0, 1, 1, 0, 0, 0, 0);
            // options
            var col = Column(row.transform, 880);
            Func<AppearanceSlot, string, bool> present = Preview != null ? Preview.HasPart : (Func<AppearanceSlot, string, bool>)((s, id) => AppearanceCatalogV01.IsValid(s, id));
            foreach (var slot in new[] { AppearanceSlot.Skin, AppearanceSlot.Hair, AppearanceSlot.HairColour, AppearanceSlot.FacialHair, AppearanceSlot.Top,
                         AppearanceSlot.TopColour, AppearanceSlot.Bottom, AppearanceSlot.BottomColour, AppearanceSlot.Accessory })
            {
                var s = slot;
                var options = AppearanceRules.Selectable(s, present);
                var current = AppearanceCatalogV01.Find(s, draft.Get(s));
                int idx = current != null ? options.FindIndex(o => o.Id == current.Id) : -1;
                string value = current != null ? current.Label + (options.Count > 1 ? "   " + (idx + 1) + "/" + options.Count : "") : "";
                Stepper(col.transform, AppearanceCatalogV01.SlotLabel(s), value,
                    options.Count > 0 ? (Action<int>)(dir => { draft.Set(s, AppearanceRules.Cycle(s, draft.Get(s), dir, present)); Render(); }) : null,
                    AppearanceCatalogV01.IsColourSlot(s) && current != null ? current.Hex : null);
            }
            string note = Preview != null && Preview.PlaceholderParts
                ? "Модель игрока не найдена: превью показывает обычную сосиску и меняет только цвета; выбор сохраняется."
                : "Только внешний вид: не влияет на рост, скорость, силу и деньги.";
            Note(body, note, Text2, 18);
            Foot(body, ("Готово  ›", () => Do(MenuActionV2.ConfirmAppearance), true), ("Случайно", Randomise, false),
                 ("По умолчанию", () => { draft = AppearanceRules.Default(); Render(); }, false), ("‹  Назад", Back, false));
        }

        void Randomise()
        {
            Func<AppearanceSlot, string, bool> present = Preview != null ? Preview.HasPart : (Func<AppearanceSlot, string, bool>)((s, id) => AppearanceCatalogV01.IsValid(s, id));
            foreach (var s in AppearanceCatalogV01.Slots)
            {
                var options = AppearanceRules.Selectable(s, present);
                if (options.Count > 0) draft.Set(s, options[UnityEngine.Random.Range(0, options.Count)].Id);
            }
            Render();
        }

        void RenderLobby(bool host)
        {
            string world = Lobby != null && !string.IsNullOrEmpty(Lobby.WorldName) ? Lobby.WorldName : flow.DraftName;
            var body = Panel(host ? "Лобби — «" + world + "»" : "Лобби — «" + world + "»", 1160, 880);
            if (host)
            {
                var ips = W86MenuLobbyV01.LocalAddresses();
                string where = ips.Count > 0 ? string.Join("  ·  ", ips.ToArray()) : "адрес этого компьютера";
                Note(body, "Друзья: «Присоединиться» → адрес  " + where + "   порт  " + (Lobby != null ? Lobby.Port : WorldLaunchV01.DefaultPort), Accent, 21);
                Note(body, "Через интернет — по внешнему IP с открытым портом (UDP). Steam-поиска пока нет.", Text2, 17);
            }
            else if (V2) Note(body, MainMenuTextsV2.ClientLobbyNote(address + ":" + port), Text2, 19);
            else Note(body, "Вы в лобби хоста " + address + ":" + port + ". Нажмите «Готов», когда будете готовы.", Text2, 19);
            var roster = Lobby != null ? Lobby.Roster : null;
            if (roster == null || roster.Count == 0) Note(body, "Никого нет.", Dimmed, 20);
            else foreach (var m in roster.Members)
            {
                var row = Img(body, "Member", Band);
                row.gameObject.AddComponent<LayoutElement>().preferredHeight = 70;
                var n = Label(row.transform, (string.IsNullOrEmpty(m.Name) ? m.PlayerId : m.Name), 26, Text1, TextAnchor.MiddleLeft, true);
                n.rectTransform.Anchor(0, 0, 1, 1, 112, 0, -260, 0);
                if (Lobby.Looks.TryGetValue(m.PlayerId, out var look))
                {
                    Swatch(row.transform, AppearanceProfileV01.Swatch(look, AppearanceSlot.Skin, Color.white), 18);
                    Swatch(row.transform, AppearanceProfileV01.Swatch(look, AppearanceSlot.TopColour, Color.grey), 48);
                    Swatch(row.transform, AppearanceProfileV01.Swatch(look, AppearanceSlot.BottomColour, Color.grey), 78);
                }
                string state = m.IsHost ? "ХОСТ" : m.Ready ? "ГОТОВ" : "НЕ ГОТОВ";
                var chip = Chip(row.transform, state, m.IsHost ? PhoneUi.Hex("#7A6B45") : m.Ready ? Go : Danger, 0, 0, 200);
                ((RectTransform)chip.transform).Anchor(1, 0, 1, 1, -230, 14, -24, -14);
            }
            if (host)
            {
                string why = "";
                bool can = roster != null && roster.CanStart(out why);
                if (!can && !string.IsNullOrEmpty(why)) Note(body, why, Bad, 19);
                Note(body, V2 ? MainMenuTextsV2.HostLobbyNote : "Пока совместная игра на карте не готова (сетевой этап M1), друзья увидят сообщение, а мир откроется у вас.", Dimmed, 16);
                Foot(body, ("Начать игру  ›", () => Do(MenuActionV2.StartSession), can), ("‹  Закрыть лобби", Back, false));
            }
            else Foot(body, (flow.LocalReady ? "Не готов" : "Готов", () => Do(MenuActionV2.ToggleReady), !flow.LocalReady), ("‹  Выйти из лобби", Back, false));
        }

        void RenderJoin()
        {
            var body = Panel("Присоединиться", 900, 620);
            Note(body, "Адрес и порт компьютера хоста (его лобби показывает их). Локальная сеть или прямое подключение.", Text2, 20);
            Field(body, "Адрес", address, s => address = s, 64);
            Field(body, "Порт", port, s => port = s, 5);
            if (!string.IsNullOrEmpty(flow.ErrorText)) Note(body, flow.ErrorText, Bad, 20);
            Foot(body, ("Подключиться  ›", () => { ushort.TryParse(port, out ushort p); Report(MenuInputV2.Address(address, p)); }, true), ("‹  Назад", Back, false));
        }

        void RenderSettings()
        {
            var body = Panel("Настройки", 1180, 860);
            var tabs = Row(body, 64);
            string[] names = { "Графика", "Звук", "Управление" };
            for (int i = 0; i < names.Length; i++)
            {
                int k = i;
                var b = Btn(tabs.transform, names[i], () => { if (settingsTab == 1 && k != 1 && audioDirty) RevertAudio(); settingsTab = k; Render(); }, true, 0, settingsTab == i, 24);
            }
            if (settingsTab == 0)
            {
                Note(body, V2 ? MainMenuTextsV2.GraphicsNote : "Графика — та же страница, что в паузе: качество, тени, трава, дальность, сглаживание, режим экрана. «Применить» сохраняет, «По умолчанию» — пресет Низкое; новый режим экрана нужно «Оставить», иначе он вернётся через 15 с.", Text2, 20);
                var pause = FindAnyObjectByType<W86PauseMenuV01>();
                var open = Btn(body, "Открыть настройки графики", () =>
                {
                    if (pause == null) return;
                    graphicsOverlay = true;
                    pause.OpenGraphicsFromMenu(() => { graphicsOverlay = false; Render(); });
                }, pause != null, 70, true, 26);
                if (pause == null) Note(body, "Страница графики недоступна в этой сцене.", Bad, 18);
            }
            else if (settingsTab == 1)
            {
                if (!audioDirty) LoadAudioDraft();
                bool mixer = OvAudioMixerV01.HasMixer;
                foreach (var bus in OvAudioMixerV01.Buses)
                {
                    if (!mixer && bus != OvAudioBus.Master) continue;
                    var b = bus;
                    SliderRow(body, OvAudioMixerV01.Label(bus), OvAudioMixerV01.Hint(bus), audioDraft[(int)bus], v =>
                    {
                        audioDraft[(int)b] = v; audioDirty = true;
                        OvAudioMixerV01.Set(b, v, false); // heard at once; kept only on Apply
                        UpdateAudioFoot();
                    });
                }
                if (!mixer) Note(body, "Микшер не найден: доступна только общая громкость.", Bad, 18);
                Note(body, "Музыки в игре пока нет — её ползунок появится вместе с ней. Язык один (русский): переключателя нет.", Dimmed, 16);
            }
            else if (V2)
            {
                Note(body, MainMenuTextsV2.ControlsHeader, Accent, 20);
                foreach (var (k, what) in MainMenuTextsV2.Controls) KeyRow(body, k, what);
            }
            else
            {
                Note(body, "Текущие клавиши (переназначения пока нет):", Accent, 20);
                foreach (var (k, what) in new[]
                         {
                             ("W A S D", "ходьба"), ("Shift", "бег"), ("Ctrl", "присесть"), ("Пробел", "прыжок / ручник в бусике"), ("Мышь", "осмотр"),
                             ("E", "взаимодействие: двери, бусик, предметы, механик, касса"), ("ЛКМ", "взять / тащить тело, инструмент"), ("Q", "удар"),
                             ("1–9", "слоты"), ("Tab", "телефон"), ("K", "сохранить"), ("Esc", "пауза / назад"),
                         })
                    KeyRow(body, k, what);
            }
            if (settingsTab == 1)
                Foot(body, ("Применить", ApplyAudio, true), ("Отменить изменения", () => { RevertAudio(); Render(); }, false),
                     ("По умолчанию", () => { for (int i = 0; i < audioDraft.Length; i++) { audioDraft[i] = 1f; OvAudioMixerV01.Set((OvAudioBus)i, 1f, false); } audioDirty = true; Render(); }, false),
                     ("‹  Назад", Back, false));
            else Foot(body, ("‹  Назад", Back, false));
            UpdateAudioFoot();
        }

        void LoadAudioDraft() { foreach (var b in OvAudioMixerV01.Buses) audioDraft[(int)b] = OvAudioMixerV01.Load(b); }

        void ApplyAudio()
        {
            foreach (var b in OvAudioMixerV01.Buses) OvAudioMixerV01.Set(b, audioDraft[(int)b], true);
            audioDirty = false;
            Play(ClickClip, 1f);
            Render();
        }

        void RevertAudio()
        {
            audioDirty = false;
            LoadAudioDraft();
            OvAudioMixerV01.ApplySaved();
        }

        void UpdateAudioFoot() { }

        // ================================================================== backdrop

        void DriftBackdrop()
        {
            if (backdrop == null || backdrop.texture == null || Backdrop == null) return; // the V2 gradient stays still
            float t = Time.unscaledTime;
            float texAspect = backdrop.texture.width / (float)Mathf.Max(1, backdrop.texture.height);
            float screenAspect = Screen.width / (float)Mathf.Max(1, Screen.height);
            float w = 1f, h = 1f;
            if (screenAspect > texAspect) h = texAspect / screenAspect; else w = screenAspect / texAspect;
            float zoom = 0.9f + 0.025f * Mathf.Sin(t * 0.045f);
            w *= zoom; h *= zoom;
            float cx = 0.5f + (1f - w) * 0.45f * Mathf.Sin(t * 0.027f), cy = 0.5f + (1f - h) * 0.4f * Mathf.Sin(t * 0.019f + 1.3f);
            cx = Mathf.Clamp(cx, w * 0.5f, 1f - w * 0.5f); cy = Mathf.Clamp(cy, h * 0.5f, 1f - h * 0.5f);
            backdrop.uvRect = new Rect(cx - w * 0.5f, cy - h * 0.5f, w, h);
        }

        // ================================================================== building blocks

        void BuildCanvas()
        {
            canvasGo = new GameObject("[Menu] Start v2", typeof(RectTransform));
            canvasGo.transform.SetParent(transform, false); canvasGo.layer = 5;
            var canvas = canvasGo.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 150; // under the pause overlay (200)
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = .5f;
            canvasGo.AddComponent<GraphicRaycaster>();

            var bg = new GameObject("Backdrop", typeof(RectTransform), typeof(RawImage)); bg.transform.SetParent(canvasGo.transform, false);
            backdrop = bg.GetComponent<RawImage>(); backdrop.texture = Backdrop; backdrop.raycastTarget = false;
            backdrop.color = Backdrop != null ? Color.white : PhoneUi.Hex("#1E2418");
            if (Backdrop == null && V2) { backdrop.texture = GradientTexture; backdrop.color = Color.white; } // until the V2 backdrop picture exists
            Stretch((RectTransform)bg.transform);
            var sh = new GameObject("Shade", typeof(RectTransform), typeof(Image)); sh.transform.SetParent(canvasGo.transform, false);
            shade = sh.GetComponent<Image>(); shade.sprite = ShadeSprite(); shade.raycastTarget = false; shade.type = Image.Type.Simple;
            Stretch((RectTransform)sh.transform);

            title = new GameObject("Title", typeof(RectTransform)); title.transform.SetParent(canvasGo.transform, false);
            ((RectTransform)title.transform).Anchor(0, 1, 0, 1, 96, -300, 1100, -70);
            var t1 = Label(title.transform, "VOLUNTEERS ONLY", 92, Accent, TextAnchor.UpperLeft, true); t1.fontStyle = FontStyle.Italic;
            t1.rectTransform.Anchor(0, 0, 1, 1, 0, 80, 0, 0);
            var strip = new GameObject("Camo", typeof(RectTransform), typeof(RawImage)); strip.transform.SetParent(title.transform, false);
            var sri = strip.GetComponent<RawImage>(); sri.texture = CamoTexture; sri.uvRect = new Rect(0, 0, 3.4f, .09f); sri.raycastTarget = false;
            ((RectTransform)strip.transform).Anchor(0, 0, 0, 0, 4, 64, 640, 82);
            var t2 = Label(title.transform, V2 ? MainMenuTextsV2.Subtitle : "кооператив до 4 игроков · W86", 26, Text2, TextAnchor.UpperLeft, true);
            t2.rectTransform.Anchor(0, 0, 1, 0, 6, 0, 0, 56);

            mainList = new GameObject("MainButtons", typeof(RectTransform)); mainList.transform.SetParent(canvasGo.transform, false);
            ((RectTransform)mainList.transform).Anchor(0, 0, 0, 1, 96, 150, 700, -380);
            var v = mainList.AddComponent<VerticalLayoutGroup>(); v.spacing = 16; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            v.childAlignment = TextAnchor.UpperLeft;

            footer = new GameObject("Footer", typeof(RectTransform)); footer.transform.SetParent(canvasGo.transform, false);
            Stretch((RectTransform)footer.transform);
            string label = string.IsNullOrEmpty(VersionLabel) ? "" : VersionLabel + " · ";
            var ver = Label(footer.transform, "VOLUNTEERS ONLY · " + label + "v" + Application.version + " · " + BuildStamp(), 18, new Color(Text2.r, Text2.g, Text2.b, .8f), TextAnchor.LowerRight);
            ver.rectTransform.Anchor(1, 0, 1, 0, -900, 18, -28, 48);
            var hint = Label(footer.transform, "Esc — назад   ·   мышь или стрелки и Enter", 17, new Color(Text2.r, Text2.g, Text2.b, .7f), TextAnchor.LowerLeft);
            hint.rectTransform.Anchor(0, 0, 0, 0, 28, 18, 900, 48);
        }

        static string BuildStamp()
        {
#if UNITY_EDITOR
            return "редактор";
#else
            return Application.buildGUID.Length > 8 ? "сборка " + Application.buildGUID.Substring(0, 8) : "сборка";
#endif
        }

        void MainButton(string text, string sub, Action onClick, bool primary)
        {
            var b = Btn(mainList.transform, "", onClick, true, sub.Length > 0 ? 92 : 78, primary, 36);
            var label = Label(b.transform, text, 38, Text1, TextAnchor.UpperLeft, true);
            label.rectTransform.Anchor(0, 0, 1, 1, 34, sub.Length > 0 ? 10 : 0, -20, sub.Length > 0 ? -10 : -16);
            if (sub.Length > 0)
            {
                var s = Label(b.transform, sub, 18, Text2, TextAnchor.LowerLeft);
                s.rectTransform.Anchor(0, 0, 1, 0, 36, 10, -20, 40);
            }
            else label.alignment = TextAnchor.MiddleLeft;
            b.GetComponent<MenuButtonFxV01>().Slide = 14f;
        }

        Transform Panel(string titleText, float w, float h)
        {
            page = new GameObject("Page", typeof(RectTransform)); page.transform.SetParent(canvasGo.transform, false); page.layer = 5;
            var rt = (RectTransform)page.transform; rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(.5f, .5f);
            rt.sizeDelta = new Vector2(w, h); rt.anchoredPosition = new Vector2(0, -40);
            var frame = Img(page.transform, "Frame", Frame); Stretch(frame.rectTransform);
            var camo = new GameObject("Camo", typeof(RectTransform), typeof(RawImage)); camo.transform.SetParent(page.transform, false);
            var ri = camo.GetComponent<RawImage>(); ri.texture = CamoTexture; ri.raycastTarget = false; ri.uvRect = new Rect(.13f, .07f, w / 256f, h / 256f);
            ((RectTransform)camo.transform).Anchor(0, 0, 1, 1, 6, 6, -6, -6);
            var card = Img(page.transform, "Card", Card); card.rectTransform.Anchor(0, 0, 1, 1, 20, 20, -20, -20);
            float top = -36;
            if (!string.IsNullOrEmpty(titleText))
            {
                var t = Label(page.transform, titleText, 44, Accent, TextAnchor.UpperLeft, true); t.fontStyle = FontStyle.Italic;
                t.rectTransform.Anchor(0, 1, 1, 1, 52, -100, -52, -34);
                var line = Img(page.transform, "Line", PhoneUi.Hex("#6E6A47")); line.rectTransform.Anchor(0, 1, 1, 1, 52, -110, -52, -107);
                top = -124;
            }
            var list = new GameObject("Body", typeof(RectTransform)); list.transform.SetParent(page.transform, false);
            ((RectTransform)list.transform).Anchor(0, 0, 1, 1, 52, 120, -52, top);
            var v = list.AddComponent<VerticalLayoutGroup>(); v.spacing = 12; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            v.childAlignment = TextAnchor.UpperLeft;
            return list.transform;
        }

        void Foot(Transform body, params (string text, Action onClick, bool primary)[] buttons) =>
            FootColored(body, Array.ConvertAll(buttons, b => (b.text, b.onClick, b.primary, (Color?)null)));

        void Foot(Transform body, (string text, Action onClick, bool primary, Color color) first, params (string text, Action onClick, bool primary)[] rest)
        {
            var all = new List<(string, Action, bool, Color?)> { (first.text, first.onClick, first.primary, first.color) };
            foreach (var r in rest) all.Add((r.text, r.onClick, r.primary, null));
            FootColored(body, all.ToArray());
        }

        void FootColored(Transform body, (string text, Action onClick, bool primary, Color? color)[] buttons)
        {
            var foot = new GameObject("Footer", typeof(RectTransform)); foot.transform.SetParent(page.transform, false);
            ((RectTransform)foot.transform).Anchor(0, 0, 1, 0, 52, 40, -52, 104);
            var h = foot.AddComponent<HorizontalLayoutGroup>(); h.spacing = 16; h.childControlWidth = true; h.childControlHeight = true; h.childForceExpandWidth = true;
            h.reverseArrangement = false;
            foreach (var b in buttons)
            {
                bool back = b.text.StartsWith("‹", StringComparison.Ordinal) || b.text == "Отмена";
                if (b.color.HasValue) Btn(foot.transform, b.text, b.onClick, true, 0, false, 25, b.color.Value, Color.Lerp(b.color.Value, Color.white, .15f));
                else Btn(foot.transform, b.text, b.onClick, true, 0, b.primary && !back, 25);
            }
        }

        void Note(Transform parent, string text, Color color, int size)
        {
            text ??= "";
            var t = Label(parent, text, size, color, TextAnchor.MiddleLeft);
            t.gameObject.AddComponent<LayoutElement>().preferredHeight = Mathf.Max(30, size * 1.45f * (1 + text.Length / 95));
        }

        GameObject Row(Transform parent, float height)
        {
            var go = new GameObject("Row", typeof(RectTransform)); go.transform.SetParent(parent, false);
            var le = go.AddComponent<LayoutElement>(); le.preferredHeight = height; le.flexibleHeight = 0f; // no stretching into spare room
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

        /// <summary>A big selectable card (the mode / legacy choice): title + one line, the chosen one lit.</summary>
        void Big(Transform parent, string head, string sub, Action onClick, bool chosen)
        {
            var b = Btn(parent, "", onClick, true, 0, chosen, 30);
            var t = Label(b.transform, head, 36, Text1, TextAnchor.UpperCenter, true); t.rectTransform.Anchor(0, 0, 1, 1, 14, 0, -14, -18);
            var s = Label(b.transform, sub, 19, chosen ? Text1 : Text2, TextAnchor.LowerCenter); s.rectTransform.Anchor(0, 0, 1, 1, 18, 16, -18, 0);
            if (chosen) { var mark = Img(b.transform, "Chosen", Accent); mark.rectTransform.Anchor(0, 0, 1, 0, 0, 0, 0, 6); }
        }

        void Choice(Transform parent, string label, string[] options, int current, Action<int> pick, string note)
        {
            var row = Img(parent, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 66;
            Label(row.transform, label, 24, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .3f, 1, 22, 0, 0, 0);
            float x0 = .3f, step = .2f;
            for (int i = 0; i < options.Length; i++)
            {
                int k = i;
                var b = Btn(row.transform, options[i], () => pick(k), true, 0, i == current, 22);
                ((RectTransform)b.transform).Anchor(x0 + step * i, 0, x0 + step * (i + 1), 1, 4, 8, -4, -8);
            }
            if (!string.IsNullOrEmpty(note))
            {
                var n = Label(row.transform, note, 16, Text2, TextAnchor.MiddleLeft);
                n.rectTransform.Anchor(x0 + step * options.Length, 0, 1, 1, 14, 0, -14, 0);
            }
        }

        void Stepper(Transform parent, string label, string value, Action<int> step, string swatchHex)
        {
            var row = Img(parent, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 66;
            Label(row.transform, label, 23, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .36f, 1, 20, 0, 0, 0);
            var v = Label(row.transform, value, 23, step != null ? Text1 : Dimmed, TextAnchor.MiddleCenter, step != null);
            v.rectTransform.Anchor(.36f, 0, 1, 1, 60, 0, -60, 0);
            if (!string.IsNullOrEmpty(swatchHex))
            {
                var sw = Img(row.transform, "Swatch", PhoneUi.Hex(swatchHex)); sw.rectTransform.Anchor(.36f, .5f, .36f, .5f, 66, -15, 96, 15);
                sw.gameObject.AddComponent<Outline>().effectColor = Frame;
            }
            if (step == null) return;
            var l = Btn(row.transform, "‹", () => step(-1), true, 0, false, 30); ((RectTransform)l.transform).Anchor(.36f, 0, .36f, 1, 0, 8, 50, -8);
            var r = Btn(row.transform, "›", () => step(1), true, 0, false, 30); ((RectTransform)r.transform).Anchor(1, 0, 1, 1, -56, 8, -6, -8);
        }

        void SliderRow(Transform parent, string label, string hint, float value, Action<float> changed)
        {
            var row = Img(parent, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 84;
            Label(row.transform, label, 24, Accent, TextAnchor.UpperLeft, true).rectTransform.Anchor(0, 0, .34f, 1, 22, 0, 0, -12);
            Label(row.transform, hint, 15, Text2, TextAnchor.LowerLeft).rectTransform.Anchor(0, 0, .34f, 1, 22, 10, 0, 0);
            var pct = Label(row.transform, Mathf.RoundToInt(value * 100f) + "%", 24, Text1, TextAnchor.MiddleRight, true);
            pct.rectTransform.Anchor(1, 0, 1, 1, -110, 0, -22, 0);
            var sgo = new GameObject("Slider", typeof(RectTransform)); sgo.transform.SetParent(row.transform, false);
            ((RectTransform)sgo.transform).Anchor(.34f, .5f, 1, .5f, 10, -14, -130, 14);
            var track = Img(sgo.transform, "Track", PhoneUi.Hex("#1E2218")); track.rectTransform.Anchor(0, .3f, 1, .7f, 0, 0, 0, 0);
            var fillArea = new GameObject("Fill Area", typeof(RectTransform)); fillArea.transform.SetParent(sgo.transform, false);
            ((RectTransform)fillArea.transform).Anchor(0, .3f, 1, .7f, 0, 0, 0, 0);
            var fill = Img(fillArea.transform, "Fill", Go); fill.rectTransform.Anchor(0, 0, 0, 1, 0, 0, 0, 0);
            var handleArea = new GameObject("Handle Area", typeof(RectTransform)); handleArea.transform.SetParent(sgo.transform, false);
            ((RectTransform)handleArea.transform).Anchor(0, 0, 1, 1, 10, 0, -10, 0);
            var handle = Img(handleArea.transform, "Handle", Accent); handle.rectTransform.sizeDelta = new Vector2(20, 0);
            handle.rectTransform.anchorMin = new Vector2(0, 0); handle.rectTransform.anchorMax = new Vector2(0, 1);
            var slider = sgo.AddComponent<Slider>();
            slider.fillRect = fill.rectTransform; slider.handleRect = handle.rectTransform; slider.targetGraphic = handle;
            slider.minValue = 0f; slider.maxValue = 1f; slider.wholeNumbers = false; slider.direction = Slider.Direction.LeftToRight;
            slider.SetValueWithoutNotify(value);
            var colors = slider.colors; colors.highlightedColor = Color.white; colors.pressedColor = PhoneUi.Hex("#FFF2C8"); slider.colors = colors;
            slider.onValueChanged.AddListener(x => { pct.text = Mathf.RoundToInt(x * 100f) + "%"; changed(x); });
        }

        void KeyRow(Transform parent, string key, string what)
        {
            var row = Img(parent, key, Band2); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 40;
            Label(row.transform, key, 21, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .28f, 1, 22, 0, 0, 0);
            Label(row.transform, what, 20, Text1, TextAnchor.MiddleLeft).rectTransform.Anchor(.28f, 0, 1, 1, 0, 0, -16, 0);
        }

        InputField Field(Transform parent, string label, string value, Action<string> changed, int limit)
        {
            var row = Img(parent, label, Band); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 68;
            Label(row.transform, label, 24, Accent, TextAnchor.MiddleLeft, true).rectTransform.Anchor(0, 0, .26f, 1, 22, 0, 0, 0);
            var box = Img(row.transform, "Input", PhoneUi.Hex("#1E2218")); box.rectTransform.Anchor(.26f, 0, 1, 1, 0, 10, -14, -10);
            box.gameObject.AddComponent<Outline>().effectColor = PhoneUi.Hex("#6E6A47");
            var text = Label(box.transform, "", 24, Text1, TextAnchor.MiddleLeft); text.rectTransform.Anchor(0, 0, 1, 1, 14, 0, -14, 0);
            text.supportRichText = false;
            var field = box.gameObject.AddComponent<InputField>(); field.textComponent = text; field.text = value ?? ""; field.characterLimit = limit;
            field.onValueChanged.AddListener(s => changed(s));
            return field;
        }

        GameObject Chip(Transform parent, string text, Color color, float x, float y, float width)
        {
            var img = Img(parent, "Chip", color);
            img.rectTransform.Anchor(0, 0, 0, .5f, x, y, x + width, -6);
            var t = Label(img.transform, text, 17, Text1, TextAnchor.MiddleCenter, true); Stretch(t.rectTransform);
            return img.gameObject;
        }

        void Swatch(Transform parent, Color c, float x)
        {
            var s = Img(parent, "Swatch", c); s.rectTransform.Anchor(0, .5f, 0, .5f, x, -13, x + 24, 13);
            s.gameObject.AddComponent<Outline>().effectColor = Frame;
        }

        Button Btn(Transform parent, string text, Action onClick, bool enabled, float height, bool primary, int fontSize, Color? normal = null, Color? hover = null)
        {
            var img = Img(parent, string.IsNullOrEmpty(text) ? "Button" : text, Color.white); // square, 90-degree corners
            img.raycastTarget = true;
            var b = img.gameObject.AddComponent<Button>();
            var c = b.colors;
            c.normalColor = normal ?? (primary ? Go : BtnBg); c.highlightedColor = hover ?? (primary ? GoHover : BtnHover); c.pressedColor = BtnPress;
            c.selectedColor = hover ?? (primary ? GoHover : BtnHover); c.disabledColor = new Color(BtnBg.r, BtnBg.g, BtnBg.b, .4f); c.colorMultiplier = 1f; c.fadeDuration = .07f;
            b.colors = c; b.interactable = enabled;
            if (onClick != null) b.onClick.AddListener(() => { Play(ClickClip, 1f); onClick(); });
            if (height > 0) img.gameObject.AddComponent<LayoutElement>().preferredHeight = height;
            var edge = img.gameObject.AddComponent<Outline>(); edge.effectColor = Frame; edge.effectDistance = new Vector2(2.5f, -2.5f);
            if (!string.IsNullOrEmpty(text))
            {
                var t = Label(img.transform, text, fontSize, enabled ? Text1 : Dimmed, TextAnchor.MiddleCenter, true); Stretch(t.rectTransform);
            }
            var fx = img.gameObject.AddComponent<MenuButtonFxV01>();
            fx.Bar = Img(img.transform, "HoverBar", Accent); fx.Bar.rectTransform.Anchor(0, 0, 0, 1, 0, 0, 6, 0); fx.Bar.enabled = false;
            fx.Hovered = () => { if (b.interactable) Play(HoverClip, .55f); };
            fx.Target = b;
            return b;
        }

        void Play(AudioClip clip, float volume)
        {
            if (sfx == null || clip == null) return;
            if (sfx.outputAudioMixerGroup == null) sfx.outputAudioMixerGroup = OvAudioMixerV01.Group(OvAudioBus.VoiceUi);
            sfx.PlayOneShot(clip, volume);
        }

        static AudioClip Tick(float freq, float seconds, float gain)
        {
            int rate = 44100, n = Mathf.Max(64, (int)(rate * seconds));
            var data = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)rate, env = Mathf.Exp(-t * 70f) * Mathf.Clamp01(i / 40f);
                data[i] = gain * env * (Mathf.Sin(2f * Mathf.PI * freq * t) * .8f + Mathf.Sin(2f * Mathf.PI * freq * 2.01f * t) * .2f);
            }
            var clip = AudioClip.Create("MenuTick" + (int)freq, n, 1, rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        static Image Img(Transform parent, string name, Color c)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image)); go.transform.SetParent(parent, false); go.layer = 5;
            var img = go.GetComponent<Image>(); img.color = c; img.raycastTarget = false; // no sprite: square corners
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
            ownedEventSystem = new GameObject("[Menu] EventSystem", typeof(EventSystem), typeof(UnityEngine.InputSystem.UI.InputSystemUIInputModule));
        }

        // ---------------------------------------------------------------- procedural art (no assets)
        static Texture2D camoTex, gradientTex; static Sprite shadeSprite;

        /// <summary>V2 backdrop placeholder (Fedya 31.10: a new picture comes later through references): a plain dark olive
        /// gradient, lighter at the top; the shade sprite still darkens the left side under the buttons.</summary>
        static Texture2D GradientTexture
        {
            get
            {
                if (gradientTex) return gradientTex;
                const int H = 256;
                gradientTex = new Texture2D(2, H, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "MenuGradientV2" };
                Color top = PhoneUi.Hex("#2A3122"), bottom = PhoneUi.Hex("#0D100A");
                var px = new Color[2 * H];
                for (int y = 0; y < H; y++)
                {
                    float k = y / (H - 1f); k = k * k * (3f - 2f * k);
                    px[y * 2] = px[y * 2 + 1] = Color.Lerp(bottom, top, k);
                }
                gradientTex.SetPixels(px); gradientTex.Apply(false, true);
                return gradientTex;
            }
        }
        static readonly Color[] CamoColors = { PhoneUi.Hex("#3E4A2A"), PhoneUi.Hex("#5B6438"), PhoneUi.Hex("#7A6B45"), PhoneUi.Hex("#262C1B") };

        static Texture2D CamoTexture
        {
            get
            {
                if (camoTex) return camoTex;
                const int N = 256; camoTex = new Texture2D(N, N, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Bilinear, name = "MenuCamo" };
                var px = new Color[N * N];
                for (int y = 0; y < N; y++) for (int x = 0; x < N; x++)
                {
                    float a = x / (float)N * Mathf.PI * 2, b = y / (float)N * Mathf.PI * 2;
                    float u = Mathf.Cos(a) * 1.6f + 5f, v = Mathf.Sin(a) * 1.6f + 5f, w2 = Mathf.Cos(b) * 1.6f + 9f, z = Mathf.Sin(b) * 1.6f + 9f;
                    float n = Mathf.PerlinNoise(u + w2 * .37f, v + z * .41f) + Mathf.PerlinNoise(u * 2.1f + z, v * 2.1f + w2) * .45f;
                    px[y * N + x] = CamoColors[n < .62f ? 3 : n < .82f ? 0 : n < 1.0f ? 1 : 2];
                }
                camoTex.SetPixels(px); camoTex.Apply(false, true);
                return camoTex;
            }
        }

        /// <summary>Dark on the left (under the title and the buttons), clear on the right, a soft vignette.</summary>
        static Sprite ShadeSprite()
        {
            if (shadeSprite) return shadeSprite;
            const int W = 256, H = 144;
            var t = new Texture2D(W, H, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "MenuShade" };
            var px = new Color[W * H];
            for (int y = 0; y < H; y++) for (int x = 0; x < W; x++)
            {
                float fx = x / (W - 1f), fy = y / (H - 1f);
                float left = Mathf.Clamp01(1f - fx / 0.55f); left = left * left * (3f - 2f * left);
                float dx = fx - .5f, dy = fy - .5f, vig = Mathf.Clamp01((dx * dx * 1.2f + dy * dy * 1.8f) * 1.6f);
                float a = Mathf.Clamp01(left * .78f + vig * .55f + .08f);
                px[y * W + x] = new Color(0.02f, 0.03f, 0.01f, a);
            }
            t.SetPixels(px); t.Apply(false, true);
            shadeSprite = Sprite.Create(t, new Rect(0, 0, W, H), new Vector2(.5f, .5f), 100f);
            return shadeSprite;
        }
    }

    /// <summary>Hover / press feedback of a menu button: an accent bar on the left, the label slides a little, a soft tick.</summary>
    public sealed class MenuButtonFxV01 : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler, ISelectHandler, IDeselectHandler, IPointerDownHandler, IPointerUpHandler
    {
        public Image Bar;
        public Selectable Target;
        public Action Hovered;
        public float Slide = 6f;
        bool over, down;
        float k;
        RectTransform[] labels;
        Vector2[] basePos;

        void Start()
        {
            var texts = GetComponentsInChildren<Text>(true);
            labels = new RectTransform[texts.Length];
            basePos = new Vector2[texts.Length];
            for (int i = 0; i < texts.Length; i++) { labels[i] = texts[i].rectTransform; basePos[i] = labels[i].anchoredPosition; }
        }

        public void OnPointerEnter(PointerEventData e) { over = true; Hovered?.Invoke(); }
        public void OnPointerExit(PointerEventData e) { over = false; down = false; }
        public void OnSelect(BaseEventData e) { over = true; Hovered?.Invoke(); }
        public void OnDeselect(BaseEventData e) { over = false; }
        public void OnPointerDown(PointerEventData e) { down = true; }
        public void OnPointerUp(PointerEventData e) { down = false; }

        void Update()
        {
            bool live = Target == null || Target.interactable;
            float want = live && over ? 1f : 0f;
            k = Mathf.MoveTowards(k, want, Time.unscaledDeltaTime * 9f);
            if (Bar != null) Bar.enabled = k > 0.02f;
            if (Bar != null) Bar.color = new Color(Bar.color.r, Bar.color.g, Bar.color.b, k);
            if (labels == null) return;
            float push = down && live ? 0.6f : 1f;
            for (int i = 0; i < labels.Length; i++)
                if (labels[i] != null) labels[i].anchoredPosition = basePos[i] + new Vector2(Slide * k * push, down && live ? -1.5f : 0f);
            transform.localScale = Vector3.one * (down && live ? 0.985f : 1f);
        }
    }
}
