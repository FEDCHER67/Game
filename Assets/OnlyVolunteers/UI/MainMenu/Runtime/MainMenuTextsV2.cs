namespace OnlyVolunteers.UI.MainMenu
{
    /// <summary>
    /// Every text the V2 start menu (MainMenu_V2_v01, Fedya 31.10) shows instead of the v1 one: no W86 label, no prologue,
    /// no v1 map words. Co-op is stated honestly: friends can sit in the lobby, but only the host enters the game for now.
    /// The controls are the ones that really work in VanOnly_v01 (KccFirstPersonInput: WASD, mouse, Shift, Ctrl, Space;
    /// GreyboxInteractor: E doors / get in, Q punch; GreyboxVanSeat: E get out; PhysicsGrabber / NetworkGrabber: LMB;
    /// VanDriveInput: WASD, Space handbrake, C camera, 1–4 / F doors; W86PauseMenuV01: Esc).
    /// </summary>
    public static class MainMenuTextsV2
    {
        public const string Subtitle = "кооператив до 4 игроков";
        public const string JoinSub = "в лобби друга по адресу";
        public const string CoopSub = "лобби для друзей; в игру пока входит только хост";
        public const string NoModeChip = "БЕЗ РЕЖИМА";
        public const string NoWorldHere = "Этот мир нельзя загрузить.";
        public const string HostLobbyNote = "Совместная игра пока не готова: друзья ждут в лобби, но в игру войдёте только вы.";
        public static string ClientLobbyNote(string where) =>
            "Вы в лобби хоста " + where + ". Войти в игру хоста пока нельзя: совместная игра ещё не готова.";
        public static string HostStartedNotice(string world) =>
            "Хост начал игру «" + world + "». Войти к нему пока нельзя: совместная игра ещё не готова.";
        public const string GraphicsNote = "Графика — та же страница, что в паузе: пресет, сглаживание, тени, масштаб рендера, режим экрана. " +
                                           "«Применить» сохраняет, «По умолчанию» — пресет Низкое; новый режим экрана нужно «Оставить», иначе через 15 с вернётся прежний.";
        public const string ControlsHeader = "Клавиши (переназначения пока нет):";

        public static readonly (string key, string what)[] Controls =
        {
            ("W A S D", "ходьба; в бусике — газ, тормоз, руль"),
            ("Мышь", "осмотр"),
            ("Shift", "бег"),
            ("Ctrl", "присесть"),
            ("Пробел", "прыжок; в бусике — ручник"),
            ("E", "двери бусика, сесть за руль и выйти"),
            ("ЛКМ", "схватить и тащить"),
            ("Q", "удар"),
            ("C", "в бусике: камера сзади / из кабины"),
            ("1–4, F", "в бусике: двери (F — все сразу)"),
            ("Esc", "пауза / назад"),
        };
    }
}
