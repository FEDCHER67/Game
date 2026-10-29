using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Session
{
    public enum MenuScreenV2
    {
        Main = 0, Worlds = 1, NewWorld = 2, Customise = 3, HostLobby = 4, JoinAddress = 5, Connecting = 6, ClientLobby = 7,
        LegacyModeChoice = 8, DeleteConfirm = 9, Settings = 10, QuitConfirm = 11, Launching = 12, Message = 13,
    }

    public enum MenuActionV2
    {
        Play, Continue, Join, Settings, Quit, Back,
        NewInSlot, LoadSlot, DeleteSlot, ConfirmDelete,
        SetMode, SetIntro, SetName, ConfirmNewWorld,
        ConfirmAppearance, ChooseLegacyMode, SubmitAddress,
        Connected, ConnectFailed, Disconnected, LobbyEnded, ToggleReady, StartSession, LaunchFailed, ConfirmQuit,
    }

    public enum MenuCommandKindV2
    {
        None, SaveAppearance, HostLobby, StartNewWorld, LoadWorld, DeleteWorld, ConnectToHost, LeaveSession, SetReady, QuitGame,
    }

    public struct MenuInputV2
    {
        public MenuActionV2 Action;
        public int Slot;
        public WorldMode Mode;
        public string Text;
        public ushort Port;
        public bool Flag;
        public static MenuInputV2 Of(MenuActionV2 a) => new MenuInputV2 { Action = a, Slot = -1 };
        public static MenuInputV2 OnSlot(MenuActionV2 a, int slot) => new MenuInputV2 { Action = a, Slot = slot };
        public static MenuInputV2 WithMode(MenuActionV2 a, WorldMode mode) => new MenuInputV2 { Action = a, Mode = mode, Slot = -1 };
        public static MenuInputV2 WithText(MenuActionV2 a, string text) => new MenuInputV2 { Action = a, Text = text, Slot = -1 };
        public static MenuInputV2 WithFlag(MenuActionV2 a, bool flag) => new MenuInputV2 { Action = a, Flag = flag, Slot = -1 };
        public static MenuInputV2 Address(string address, ushort port) => new MenuInputV2 { Action = MenuActionV2.SubmitAddress, Text = address, Port = port, Slot = -1 };
    }

    public struct MenuCommandV2
    {
        public MenuCommandKindV2 Kind;
        public int Slot;
        public WorldMode Mode;
        /// <summary>LoadWorld of a legacy world: the owner's explicit one-time mode choice (Unset = none needed).</summary>
        public WorldMode LegacyChoice;
        public string Name;
        public bool SkipIntro;
        /// <summary>HostLobby: the lobby is for loading an existing world (false = a new world).</summary>
        public bool ForLoad;
        public string Address;
        public ushort Port;
        public bool Flag;
        public static readonly MenuCommandV2 None = default;
    }

    /// <summary>
    /// The start-menu flow v2 (Fedya 29.10: "a normal menu like the co-op indie games"), pure:
    /// Main [Продолжить only with a save] / Играть / Присоединиться / Настройки / Выход.
    /// Играть → the five world cards: an empty card → New world (name, Solo / Co-op: immutable, the intro on or skipped) →
    /// the sausage customisation → Solo: the world starts (intro hook) / Co-op: the host lobby → everyone ready → start.
    /// An occupied card → Load (Solo: starts; Co-op: the host lobby first; a legacy world asks its one-time mode first) or
    /// Delete (asks to confirm; only that slot's files). Присоединиться → the joiner's OWN look → address:port → connect
    /// (real transport errors) → the client lobby (ready) → the host starts. Back (and Esc) always steps back and leaves a
    /// lobby/connection through LeaveSession. New worlds only go into EMPTY slots: nothing is ever wiped without the
    /// explicit Delete + confirm. The runtime performs each returned <see cref="MenuCommandV2"/> and reports outcomes.
    /// </summary>
    public sealed class MainMenuFlowV2
    {
        public const int SlotCount = MainMenuFlow.SlotCount;
        public const int MaxNameLength = 32;
        readonly Func<IReadOnlyList<WorldSlotCard>> slots;
        readonly Stack<MenuScreenV2> history = new Stack<MenuScreenV2>();

        public MenuScreenV2 Screen { get; private set; } = MenuScreenV2.Main;
        public int DraftSlot { get; private set; } = -1;
        public WorldMode DraftMode { get; private set; }
        public string DraftName { get; private set; } = "";
        public bool DraftSkipIntro { get; private set; }
        /// <summary>The lobby/launch is for an existing world (Load) rather than a new one.</summary>
        public bool DraftLoad { get; private set; }
        public WorldMode DraftLegacyChoice { get; private set; }
        public bool DraftJoining { get; private set; }
        public bool LocalReady { get; private set; }
        public string MessageText { get; private set; } = "";
        public string ErrorText { get; private set; } = "";

        public MainMenuFlowV2(Func<IReadOnlyList<WorldSlotCard>> slots) { this.slots = slots ?? (() => Array.Empty<WorldSlotCard>()); }

        IReadOnlyList<WorldSlotCard> Slots => slots() ?? Array.Empty<WorldSlotCard>();

        public WorldSlotCard Card(int index) { foreach (var s in Slots) if (s.Index == index) return s; return null; }

        /// <summary>The newest loadable world (Продолжить), or null (then the button is not shown).</summary>
        public WorldSlotCard Newest()
        {
            WorldSlotCard best = null;
            foreach (var s in Slots) if (s.Occupied && s.Loadable && (best == null || s.SavedTicksUtc > best.SavedTicksUtc)) best = s;
            return best;
        }

        public bool CanContinue => Newest() != null;

        public static string DefaultName(int slot) => "Мир " + (slot + 1);

        /// <summary>A world name as saved: trimmed, control characters removed, at most <see cref="MaxNameLength"/>; empty →
        /// the slot's default name.</summary>
        public static string CleanName(string name, int slot)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char ch in (name ?? "").Trim()) if (!char.IsControl(ch) && ch != ';' && ch != '|') sb.Append(ch);
            string s = sb.ToString().Trim();
            if (s.Length > MaxNameLength) s = s.Substring(0, MaxNameLength).Trim();
            return s.Length > 0 ? s : DefaultName(slot);
        }

        void Go(MenuScreenV2 next) { history.Push(Screen); Screen = next; ErrorText = ""; }

        void Reset(MenuScreenV2 to)
        {
            history.Clear(); Screen = to; ErrorText = "";
            DraftSlot = -1; DraftMode = WorldMode.Unset; DraftName = ""; DraftSkipIntro = false; DraftLoad = false;
            DraftLegacyChoice = WorldMode.Unset; DraftJoining = false; LocalReady = false;
        }

        void ShowMessage(string text) { Reset(MenuScreenV2.Main); MessageText = text ?? ""; Go(MenuScreenV2.Message); }

        public MenuCommandV2 Apply(MenuInputV2 input)
        {
            switch (input.Action)
            {
                case MenuActionV2.Back: return Back();
                case MenuActionV2.LaunchFailed:
                    ShowMessage(string.IsNullOrEmpty(input.Text) ? "Не удалось запустить мир." : input.Text);
                    return MenuCommandV2.None;
                case MenuActionV2.LobbyEnded:
                    // the host started or closed the lobby (client side), or the host's own server stopped
                    if (Screen == MenuScreenV2.ClientLobby || Screen == MenuScreenV2.Connecting || Screen == MenuScreenV2.HostLobby)
                        ShowMessage(string.IsNullOrEmpty(input.Text) ? "Лобби закрыто." : input.Text);
                    return MenuCommandV2.None;
                case MenuActionV2.Disconnected:
                    if (Screen == MenuScreenV2.ClientLobby || Screen == MenuScreenV2.Connecting)
                    {
                        Screen = MenuScreenV2.JoinAddress; LocalReady = false;
                        ErrorText = string.IsNullOrEmpty(input.Text) ? "Соединение с хостом потеряно." : input.Text;
                    }
                    return MenuCommandV2.None;
            }

            switch (Screen)
            {
                case MenuScreenV2.Main: return OnMain(input);
                case MenuScreenV2.Worlds: return OnWorlds(input);
                case MenuScreenV2.DeleteConfirm:
                    if (input.Action != MenuActionV2.ConfirmDelete) return MenuCommandV2.None;
                    int slot = DraftSlot;
                    Back();
                    return new MenuCommandV2 { Kind = MenuCommandKindV2.DeleteWorld, Slot = slot };
                case MenuScreenV2.NewWorld: return OnNewWorld(input);
                case MenuScreenV2.Customise:
                    if (input.Action != MenuActionV2.ConfirmAppearance) return MenuCommandV2.None;
                    if (DraftJoining) Go(MenuScreenV2.JoinAddress);
                    else if (DraftMode == WorldMode.Solo) Go(MenuScreenV2.Launching);
                    else Go(MenuScreenV2.HostLobby);
                    // the look is saved first; the runtime then performs the follow-up of the screen we are on now
                    return new MenuCommandV2 { Kind = MenuCommandKindV2.SaveAppearance };
                case MenuScreenV2.LegacyModeChoice:
                    if (input.Action != MenuActionV2.ChooseLegacyMode || (input.Mode != WorldMode.Solo && input.Mode != WorldMode.Multiplayer))
                        return MenuCommandV2.None;
                    DraftLegacyChoice = input.Mode; DraftMode = input.Mode;
                    if (input.Mode == WorldMode.Solo) { Go(MenuScreenV2.Launching); return LoadCommand(); }
                    Go(MenuScreenV2.HostLobby);
                    return new MenuCommandV2 { Kind = MenuCommandKindV2.HostLobby, Slot = DraftSlot, Mode = WorldMode.Multiplayer, ForLoad = true, Name = DraftName };
                case MenuScreenV2.HostLobby:
                    if (input.Action != MenuActionV2.StartSession) return MenuCommandV2.None;
                    Go(MenuScreenV2.Launching);
                    return DraftLoad ? LoadCommand() : NewWorldCommand();
                case MenuScreenV2.JoinAddress:
                    if (input.Action != MenuActionV2.SubmitAddress) return MenuCommandV2.None;
                    if (string.IsNullOrWhiteSpace(input.Text) || input.Port == 0) { ErrorText = "Укажите адрес и порт хоста."; return MenuCommandV2.None; }
                    Go(MenuScreenV2.Connecting);
                    return new MenuCommandV2 { Kind = MenuCommandKindV2.ConnectToHost, Address = input.Text.Trim(), Port = input.Port };
                case MenuScreenV2.Connecting:
                    if (input.Action == MenuActionV2.Connected) { Screen = MenuScreenV2.ClientLobby; LocalReady = false; }
                    else if (input.Action == MenuActionV2.ConnectFailed)
                    {
                        Screen = MenuScreenV2.JoinAddress;
                        ErrorText = string.IsNullOrEmpty(input.Text) ? "Не удалось подключиться." : input.Text;
                    }
                    return MenuCommandV2.None;
                case MenuScreenV2.ClientLobby:
                    if (input.Action != MenuActionV2.ToggleReady) return MenuCommandV2.None;
                    LocalReady = !LocalReady;
                    return new MenuCommandV2 { Kind = MenuCommandKindV2.SetReady, Flag = LocalReady };
                case MenuScreenV2.QuitConfirm:
                    return input.Action == MenuActionV2.ConfirmQuit ? new MenuCommandV2 { Kind = MenuCommandKindV2.QuitGame } : MenuCommandV2.None;
                default:
                    return MenuCommandV2.None;
            }
        }

        /// <summary>After SaveAppearance the runtime asks what to do next on the screen the flow moved to.</summary>
        public MenuCommandV2 FollowUpAfterAppearance()
        {
            if (DraftJoining) return MenuCommandV2.None;
            if (Screen == MenuScreenV2.Launching && DraftMode == WorldMode.Solo) return NewWorldCommand();
            if (Screen == MenuScreenV2.HostLobby) return new MenuCommandV2 { Kind = MenuCommandKindV2.HostLobby, Slot = DraftSlot, Mode = WorldMode.Multiplayer, Name = DraftName };
            return MenuCommandV2.None;
        }

        MenuCommandV2 NewWorldCommand() => new MenuCommandV2
        {
            Kind = MenuCommandKindV2.StartNewWorld, Slot = DraftSlot, Mode = DraftMode, Name = CleanName(DraftName, DraftSlot), SkipIntro = DraftSkipIntro,
        };

        MenuCommandV2 LoadCommand() => new MenuCommandV2
        {
            Kind = MenuCommandKindV2.LoadWorld, Slot = DraftSlot, Mode = DraftMode, LegacyChoice = DraftLegacyChoice, Name = DraftName,
        };

        MenuCommandV2 OnMain(MenuInputV2 input)
        {
            switch (input.Action)
            {
                case MenuActionV2.Play: Go(MenuScreenV2.Worlds); return MenuCommandV2.None;
                case MenuActionV2.Continue:
                {
                    var newest = Newest();
                    if (newest == null) { ShowMessage("Нет мира, который можно продолжить."); return MenuCommandV2.None; }
                    return BeginLoad(newest);
                }
                case MenuActionV2.Join:
                    DraftJoining = true; DraftMode = WorldMode.Unset; Go(MenuScreenV2.Customise); return MenuCommandV2.None;
                case MenuActionV2.Settings: Go(MenuScreenV2.Settings); return MenuCommandV2.None;
                case MenuActionV2.Quit: Go(MenuScreenV2.QuitConfirm); return MenuCommandV2.None;
                default: return MenuCommandV2.None;
            }
        }

        MenuCommandV2 OnWorlds(MenuInputV2 input)
        {
            if (input.Slot < 0 || input.Slot >= SlotCount) return MenuCommandV2.None;
            var card = Card(input.Slot);
            bool occupied = card != null && card.Occupied;
            switch (input.Action)
            {
                case MenuActionV2.NewInSlot:
                    if (occupied) { ErrorText = "Этот слот занят. Новый мир — только в свободный слот (или сначала удалите старый)."; return MenuCommandV2.None; }
                    DraftSlot = input.Slot; DraftMode = WorldMode.Unset; DraftName = DefaultName(input.Slot); DraftSkipIntro = false; DraftLoad = false;
                    Go(MenuScreenV2.NewWorld);
                    return MenuCommandV2.None;
                case MenuActionV2.LoadSlot:
                    if (!occupied) return MenuCommandV2.None;
                    return BeginLoad(card);
                case MenuActionV2.DeleteSlot:
                    if (!occupied) return MenuCommandV2.None;
                    DraftSlot = input.Slot;
                    Go(MenuScreenV2.DeleteConfirm);
                    return MenuCommandV2.None;
                default: return MenuCommandV2.None;
            }
        }

        MenuCommandV2 OnNewWorld(MenuInputV2 input)
        {
            switch (input.Action)
            {
                case MenuActionV2.SetMode:
                    if (input.Mode == WorldMode.Solo || input.Mode == WorldMode.Multiplayer) { DraftMode = input.Mode; ErrorText = ""; }
                    return MenuCommandV2.None;
                case MenuActionV2.SetIntro: DraftSkipIntro = !input.Flag; return MenuCommandV2.None;
                case MenuActionV2.SetName: DraftName = input.Text ?? ""; return MenuCommandV2.None;
                case MenuActionV2.ConfirmNewWorld:
                    if (DraftMode != WorldMode.Solo && DraftMode != WorldMode.Multiplayer) { ErrorText = "Выберите: соло или кооп."; return MenuCommandV2.None; }
                    DraftName = CleanName(DraftName, DraftSlot);
                    DraftJoining = false;
                    Go(MenuScreenV2.Customise);
                    return MenuCommandV2.None;
                default: return MenuCommandV2.None;
            }
        }

        MenuCommandV2 BeginLoad(WorldSlotCard card)
        {
            if (!card.Loadable) { ShowMessage(string.IsNullOrEmpty(card.Problem) ? "Этот мир не загружается." : card.Problem); return MenuCommandV2.None; }
            DraftSlot = card.Index; DraftLoad = true; DraftName = card.Name ?? ""; DraftLegacyChoice = WorldMode.Unset;
            if (card.Mode == WorldModeStatus.LegacyNeedsChoice) { DraftMode = WorldMode.Unset; Go(MenuScreenV2.LegacyModeChoice); return MenuCommandV2.None; }
            DraftMode = card.Mode == WorldModeStatus.Solo ? WorldMode.Solo : WorldMode.Multiplayer;
            if (DraftMode == WorldMode.Solo) { Go(MenuScreenV2.Launching); return LoadCommand(); }
            Go(MenuScreenV2.HostLobby);
            return new MenuCommandV2 { Kind = MenuCommandKindV2.HostLobby, Slot = DraftSlot, Mode = WorldMode.Multiplayer, ForLoad = true, Name = DraftName };
        }

        MenuCommandV2 Back()
        {
            if (Screen == MenuScreenV2.Launching || Screen == MenuScreenV2.Main) return MenuCommandV2.None;
            var leaving = Screen;
            if (history.Count == 0) { Reset(MenuScreenV2.Main); return MenuCommandV2.None; }
            Screen = history.Pop(); ErrorText = "";
            if (Screen == MenuScreenV2.Connecting) Screen = MenuScreenV2.JoinAddress; // never "back" into a finished attempt
            if (Screen == MenuScreenV2.Launching) Screen = MenuScreenV2.Main;
            if (Screen == MenuScreenV2.Main) Reset(MenuScreenV2.Main);
            if (leaving == MenuScreenV2.HostLobby || leaving == MenuScreenV2.ClientLobby || leaving == MenuScreenV2.Connecting)
            {
                LocalReady = false;
                return new MenuCommandV2 { Kind = MenuCommandKindV2.LeaveSession };
            }
            return MenuCommandV2.None;
        }
    }
}
