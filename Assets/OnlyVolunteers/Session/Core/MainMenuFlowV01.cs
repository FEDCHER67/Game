using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Session
{
    public enum MenuScreen
    {
        Main = 0, NewGameMode = 1, Customise = 2, SoloSlot = 3, HostSlot = 4, HostLobby = 5, JoinAddress = 6, Connecting = 7,
        ClientLobby = 8, LoadList = 9, LegacyModeChoice = 10, Settings = 11, Graphics = 12, Audio = 13, QuitConfirm = 14,
        Launching = 15, Message = 16,
    }

    public enum MenuAction
    {
        NewGame, Continue, Load, Join, EditAppearance, Settings, Quit, Back,
        ChooseSolo, ChooseMultiplayer, ConfirmAppearance, PickSlot, ChooseLegacyMode, SubmitAddress,
        Connected, ConnectFailed, Disconnected, ToggleReady, StartSession, SessionStarted, LaunchFailed,
        OpenGraphics, OpenAudio, ConfirmQuit,
    }

    /// <summary>What the runtime must do after a transition (network, files, application). Pure data.</summary>
    public enum MenuCommandKind
    {
        None, SaveAppearance, HostLobby, StartNewWorld, LoadWorld, ConnectToHost, LeaveSession, SetReady, OpenGraphics, QuitGame,
    }

    public struct MenuInput
    {
        public MenuAction Action;
        public int Slot;
        public WorldMode Mode;
        public string Text;
        public ushort Port;
        public bool Flag;
        public static MenuInput Of(MenuAction a) => new MenuInput { Action = a, Slot = -1 };
        public static MenuInput SlotPick(int slot) => new MenuInput { Action = MenuAction.PickSlot, Slot = slot };
        public static MenuInput LegacyMode(WorldMode mode) => new MenuInput { Action = MenuAction.ChooseLegacyMode, Mode = mode, Slot = -1 };
        public static MenuInput Address(string address, ushort port) => new MenuInput { Action = MenuAction.SubmitAddress, Text = address, Port = port, Slot = -1 };
        public static MenuInput Failure(MenuAction a, string reason) => new MenuInput { Action = a, Text = reason, Slot = -1 };
    }

    public struct MenuCommand
    {
        public MenuCommandKind Kind;
        public int Slot;
        public WorldMode Mode;
        /// <summary>LoadWorld of a legacy world: the owner's explicit one-time mode choice (Unset = none needed).</summary>
        public WorldMode LegacyChoice;
        public string Address;
        public ushort Port;
        public bool Flag;
        public static readonly MenuCommand None = default;
    }

    /// <summary>One world slot as the menu shows it (filled by the save owner; five slots, SAVE_PROGRESS v01 §2 / WP07).</summary>
    public sealed class WorldSlotCard
    {
        public int Index;
        public bool Occupied;
        public bool Loadable;
        public string Name = "";
        public string SavedText = "";
        public long SavedTicksUtc;
        public WorldModeStatus Mode;
        /// <summary>Why an occupied slot cannot be loaded (newer/corrupt save), player-facing.</summary>
        public string Problem = "";
    }

    /// <summary>
    /// The start-menu flow as a pure state machine (PLAYER stage brief §2):
    /// Main → New game → Solo / Multiplayer → customise → (Solo: empty slot → new world → intro) / (Multiplayer: empty slot →
    /// host lobby → ready → intro with the ready participants). Join: customise (the joiner's OWN look) → address → connect →
    /// lobby → the host starts. Continue = newest loadable world; Load = the slot list; a legacy world asks its one-time mode
    /// choice first. Settings: graphics (the existing pause-menu page, Low default), audio (only what works). Quit asks first.
    /// New game only goes into an EMPTY slot (never wipes a world); all five full → a message. Back always steps back and
    /// leaves a lobby/connection through LeaveSession. The runtime performs each returned <see cref="MenuCommand"/> and
    /// reports outcomes back as actions (Connected, ConnectFailed, SessionStarted, LaunchFailed...).
    /// </summary>
    public sealed class MainMenuFlow
    {
        public const int SlotCount = 5;
        readonly Func<IReadOnlyList<WorldSlotCard>> slots;
        readonly Stack<MenuScreen> history = new Stack<MenuScreen>();

        public MenuScreen Screen { get; private set; } = MenuScreen.Main;
        /// <summary>The mode of the world being created (New game) or Unset.</summary>
        public WorldMode DraftMode { get; private set; }
        /// <summary>Customise was opened by Join (the next step is the address) or from the main menu (back to Main).</summary>
        public bool DraftJoining { get; private set; }
        public bool DraftAppearanceOnly { get; private set; }
        public int DraftSlot { get; private set; } = -1;
        public string MessageText { get; private set; } = "";
        public string ErrorText { get; private set; } = "";
        public bool LocalReady { get; private set; }

        public MainMenuFlow(Func<IReadOnlyList<WorldSlotCard>> slots) { this.slots = slots ?? (() => Array.Empty<WorldSlotCard>()); }

        IReadOnlyList<WorldSlotCard> Slots => slots() ?? Array.Empty<WorldSlotCard>();

        public bool HasEmptySlot() { foreach (var s in Slots) if (!s.Occupied) return true; return Slots.Count < SlotCount; }

        public int FirstEmptySlot()
        {
            var taken = new HashSet<int>();
            foreach (var s in Slots) if (s.Occupied) taken.Add(s.Index);
            for (int i = 0; i < SlotCount; i++) if (!taken.Contains(i)) return i;
            return -1;
        }

        /// <summary>The newest loadable world (Continue), or null.</summary>
        public WorldSlotCard Newest()
        {
            WorldSlotCard best = null;
            foreach (var s in Slots) if (s.Occupied && s.Loadable && (best == null || s.SavedTicksUtc > best.SavedTicksUtc)) best = s;
            return best;
        }

        WorldSlotCard Card(int index) { foreach (var s in Slots) if (s.Index == index) return s; return null; }

        void Go(MenuScreen next) { history.Push(Screen); Screen = next; ErrorText = ""; }

        void Reset(MenuScreen to)
        {
            history.Clear(); Screen = to; DraftMode = WorldMode.Unset; DraftJoining = false; DraftAppearanceOnly = false; DraftSlot = -1;
            LocalReady = false; ErrorText = "";
        }

        void ShowMessage(string text) { MessageText = text ?? ""; Go(MenuScreen.Message); }

        public MenuCommand Apply(MenuInput input)
        {
            switch (input.Action)
            {
                case MenuAction.Back: return Back();
                case MenuAction.LaunchFailed:
                    Reset(MenuScreen.Main); ShowMessage(string.IsNullOrEmpty(input.Text) ? "Не удалось запустить мир." : input.Text);
                    return MenuCommand.None;
                case MenuAction.Disconnected:
                    if (Screen == MenuScreen.ClientLobby || Screen == MenuScreen.Connecting)
                    {
                        Screen = MenuScreen.JoinAddress; LocalReady = false;
                        ErrorText = string.IsNullOrEmpty(input.Text) ? "Соединение с хостом потеряно." : input.Text;
                    }
                    return MenuCommand.None;
            }

            switch (Screen)
            {
                case MenuScreen.Main: return OnMain(input);
                case MenuScreen.NewGameMode:
                    if (input.Action == MenuAction.ChooseSolo || input.Action == MenuAction.ChooseMultiplayer)
                    {
                        DraftMode = input.Action == MenuAction.ChooseSolo ? WorldMode.Solo : WorldMode.Multiplayer;
                        DraftJoining = false; DraftAppearanceOnly = false;
                        Go(MenuScreen.Customise);
                    }
                    return MenuCommand.None;
                case MenuScreen.Customise:
                    if (input.Action != MenuAction.ConfirmAppearance) return MenuCommand.None;
                    if (DraftAppearanceOnly) { Reset(MenuScreen.Main); }
                    else if (DraftJoining) Go(MenuScreen.JoinAddress);
                    else Go(DraftMode == WorldMode.Solo ? MenuScreen.SoloSlot : MenuScreen.HostSlot);
                    return new MenuCommand { Kind = MenuCommandKind.SaveAppearance };
                case MenuScreen.SoloSlot:
                case MenuScreen.HostSlot:
                    return OnNewWorldSlot(input);
                case MenuScreen.HostLobby:
                    if (input.Action == MenuAction.StartSession)
                    {
                        Go(MenuScreen.Launching);
                        return new MenuCommand { Kind = MenuCommandKind.StartNewWorld, Slot = DraftSlot, Mode = WorldMode.Multiplayer };
                    }
                    return MenuCommand.None;
                case MenuScreen.JoinAddress:
                    if (input.Action != MenuAction.SubmitAddress) return MenuCommand.None;
                    if (string.IsNullOrWhiteSpace(input.Text) || input.Port == 0) { ErrorText = "Укажите адрес и порт хоста."; return MenuCommand.None; }
                    Go(MenuScreen.Connecting);
                    return new MenuCommand { Kind = MenuCommandKind.ConnectToHost, Address = input.Text.Trim(), Port = input.Port };
                case MenuScreen.Connecting:
                    if (input.Action == MenuAction.Connected) { Screen = MenuScreen.ClientLobby; LocalReady = false; }
                    else if (input.Action == MenuAction.ConnectFailed)
                    {
                        Screen = MenuScreen.JoinAddress;
                        ErrorText = string.IsNullOrEmpty(input.Text) ? "Не удалось подключиться." : input.Text;
                    }
                    return MenuCommand.None;
                case MenuScreen.ClientLobby:
                    if (input.Action == MenuAction.ToggleReady)
                    {
                        LocalReady = !LocalReady;
                        return new MenuCommand { Kind = MenuCommandKind.SetReady, Flag = LocalReady };
                    }
                    if (input.Action == MenuAction.SessionStarted) Go(MenuScreen.Launching);
                    return MenuCommand.None;
                case MenuScreen.LoadList: return OnLoadPick(input);
                case MenuScreen.LegacyModeChoice:
                    if (input.Action != MenuAction.ChooseLegacyMode || (input.Mode != WorldMode.Solo && input.Mode != WorldMode.Multiplayer))
                        return MenuCommand.None;
                    Go(MenuScreen.Launching);
                    return new MenuCommand { Kind = MenuCommandKind.LoadWorld, Slot = DraftSlot, LegacyChoice = input.Mode, Mode = input.Mode };
                case MenuScreen.Settings:
                    if (input.Action == MenuAction.OpenGraphics) { Go(MenuScreen.Graphics); return new MenuCommand { Kind = MenuCommandKind.OpenGraphics }; }
                    if (input.Action == MenuAction.OpenAudio) Go(MenuScreen.Audio);
                    return MenuCommand.None;
                case MenuScreen.QuitConfirm:
                    return input.Action == MenuAction.ConfirmQuit ? new MenuCommand { Kind = MenuCommandKind.QuitGame } : MenuCommand.None;
                default:
                    return MenuCommand.None;
            }
        }

        MenuCommand OnMain(MenuInput input)
        {
            switch (input.Action)
            {
                case MenuAction.NewGame:
                    if (!HasEmptySlot()) { ShowMessage("Все пять миров заняты. Новый мир можно начать только в свободном слоте."); return MenuCommand.None; }
                    DraftMode = WorldMode.Unset; Go(MenuScreen.NewGameMode); return MenuCommand.None;
                case MenuAction.Continue:
                {
                    var newest = Newest();
                    if (newest == null) { ShowMessage("Нет мира, который можно продолжить."); return MenuCommand.None; }
                    return BeginLoad(newest);
                }
                case MenuAction.Load: Go(MenuScreen.LoadList); return MenuCommand.None;
                case MenuAction.Join:
                    DraftJoining = true; DraftAppearanceOnly = false; DraftMode = WorldMode.Unset; Go(MenuScreen.Customise); return MenuCommand.None;
                case MenuAction.EditAppearance:
                    DraftAppearanceOnly = true; DraftJoining = false; Go(MenuScreen.Customise); return MenuCommand.None;
                case MenuAction.Settings: Go(MenuScreen.Settings); return MenuCommand.None;
                case MenuAction.Quit: Go(MenuScreen.QuitConfirm); return MenuCommand.None;
                default: return MenuCommand.None;
            }
        }

        MenuCommand OnNewWorldSlot(MenuInput input)
        {
            if (input.Action != MenuAction.PickSlot) return MenuCommand.None;
            if (input.Slot < 0 || input.Slot >= SlotCount) return MenuCommand.None;
            var card = Card(input.Slot);
            if (card != null && card.Occupied) { ErrorText = "Этот слот занят. Новый мир — только в свободный слот."; return MenuCommand.None; }
            DraftSlot = input.Slot;
            if (DraftMode == WorldMode.Solo)
            {
                Go(MenuScreen.Launching);
                return new MenuCommand { Kind = MenuCommandKind.StartNewWorld, Slot = DraftSlot, Mode = WorldMode.Solo };
            }
            Go(MenuScreen.HostLobby);
            return new MenuCommand { Kind = MenuCommandKind.HostLobby, Slot = DraftSlot, Mode = WorldMode.Multiplayer };
        }

        MenuCommand OnLoadPick(MenuInput input)
        {
            if (input.Action != MenuAction.PickSlot) return MenuCommand.None;
            var card = Card(input.Slot);
            if (card == null || !card.Occupied) return MenuCommand.None;
            return BeginLoad(card);
        }

        MenuCommand BeginLoad(WorldSlotCard card)
        {
            if (!card.Loadable) { ShowMessage(string.IsNullOrEmpty(card.Problem) ? "Этот мир не загружается." : card.Problem); return MenuCommand.None; }
            DraftSlot = card.Index;
            if (card.Mode == WorldModeStatus.LegacyNeedsChoice) { Go(MenuScreen.LegacyModeChoice); return MenuCommand.None; }
            Go(MenuScreen.Launching);
            return new MenuCommand { Kind = MenuCommandKind.LoadWorld, Slot = card.Index,
                Mode = card.Mode == WorldModeStatus.Solo ? WorldMode.Solo : WorldMode.Multiplayer };
        }

        MenuCommand Back()
        {
            if (Screen == MenuScreen.Launching || Screen == MenuScreen.Main) return MenuCommand.None;
            var leaving = Screen;
            if (history.Count == 0) { Reset(MenuScreen.Main); return MenuCommand.None; }
            Screen = history.Pop(); ErrorText = "";
            if (Screen == MenuScreen.Connecting) Screen = MenuScreen.JoinAddress; // never "back" into a finished attempt
            if (Screen == MenuScreen.Main) Reset(MenuScreen.Main);
            if (leaving == MenuScreen.HostLobby || leaving == MenuScreen.ClientLobby || leaving == MenuScreen.Connecting)
            {
                LocalReady = false;
                return new MenuCommand { Kind = MenuCommandKind.LeaveSession };
            }
            return MenuCommand.None;
        }
    }

    public sealed class LobbyMember
    {
        public string PlayerId = "";
        public string Name = "";
        public bool IsHost;
        public bool Ready;
    }

    /// <summary>
    /// The host's lobby before a multiplayer world starts: up to four members by stable id, a ready flag each. A reconnect
    /// with the same id is the same member (not a second one). The host starts when every other member is ready; the intro
    /// then runs with exactly <see cref="StartingParticipants"/>.
    /// </summary>
    public sealed class LobbyRoster
    {
        readonly List<LobbyMember> members = new List<LobbyMember>();
        public IReadOnlyList<LobbyMember> Members => members;
        public int Count => members.Count;

        LobbyMember Find(string id) => members.Find(m => m.PlayerId == id);

        public bool Join(string playerId, string name, bool isHost)
        {
            if (!PlayerIds.IsValid(playerId)) return false;
            var m = Find(playerId);
            if (m != null) { m.Name = name ?? m.Name; m.Ready = isHost; return true; }
            if (members.Count >= WorldModeRules.MaxParticipants) return false;
            if (isHost && members.Exists(x => x.IsHost)) return false;
            members.Add(new LobbyMember { PlayerId = playerId, Name = name ?? "", IsHost = isHost, Ready = isHost });
            return true;
        }

        public bool Leave(string playerId) => members.RemoveAll(m => m.PlayerId == playerId && !m.IsHost) > 0;

        public bool SetReady(string playerId, bool ready)
        {
            var m = Find(playerId);
            if (m == null || m.IsHost) return false;
            m.Ready = ready;
            return true;
        }

        /// <summary>The host is present and every other member is ready. <paramref name="reason"/> names who is not.</summary>
        public bool CanStart(out string reason)
        {
            reason = "";
            if (!members.Exists(m => m.IsHost)) { reason = "Нет хоста."; return false; }
            var waiting = members.FindAll(m => !m.IsHost && !m.Ready);
            if (waiting.Count == 0) return true;
            var names = new List<string>();
            foreach (var m in waiting) names.Add(string.IsNullOrEmpty(m.Name) ? m.PlayerId : m.Name);
            reason = "Ждём готовности: " + string.Join(", ", names);
            return false;
        }

        public List<string> StartingParticipants()
        {
            var ids = new List<string>();
            foreach (var m in members) if (m.IsHost || m.Ready) ids.Add(m.PlayerId);
            return ids;
        }
    }
}
