using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Session.Tests
{
    public sealed class MainMenuFlowTests
    {
        readonly List<WorldSlotCard> cards = new List<WorldSlotCard>();
        MainMenuFlow flow;

        [SetUp] public void SetUp() { cards.Clear(); flow = new MainMenuFlow(() => cards); }

        WorldSlotCard Add(int index, WorldModeStatus mode, long ticks, bool loadable = true) =>
            Add(new WorldSlotCard { Index = index, Occupied = true, Loadable = loadable, Mode = mode, SavedTicksUtc = ticks, Name = "W" + index });
        WorldSlotCard Add(WorldSlotCard c) { cards.Add(c); return c; }
        MenuCommand Do(MenuAction a) => flow.Apply(MenuInput.Of(a));

        [Test] public void SoloNewGameGoesThroughCustomiseIntoAnEmptySlot()
        {
            Add(0, WorldModeStatus.Solo, 5);
            Do(MenuAction.NewGame); Assert.AreEqual(MenuScreen.NewGameMode, flow.Screen);
            Do(MenuAction.ChooseSolo); Assert.AreEqual(MenuScreen.Customise, flow.Screen);
            Assert.AreEqual(MenuCommandKind.SaveAppearance, Do(MenuAction.ConfirmAppearance).Kind);
            Assert.AreEqual(MenuScreen.SoloSlot, flow.Screen);
            var refused = flow.Apply(MenuInput.SlotPick(0));
            Assert.AreEqual(MenuCommandKind.None, refused.Kind, "an occupied slot is never overwritten by New game");
            Assert.IsNotEmpty(flow.ErrorText);
            var start = flow.Apply(MenuInput.SlotPick(1));
            Assert.AreEqual(MenuCommandKind.StartNewWorld, start.Kind);
            Assert.AreEqual(WorldMode.Solo, start.Mode); Assert.AreEqual(1, start.Slot);
            Assert.AreEqual(MenuScreen.Launching, flow.Screen);
        }

        [Test] public void MultiplayerNewGameHostsALobbyThenStartsWithMultiplayerMode()
        {
            Do(MenuAction.NewGame); Do(MenuAction.ChooseMultiplayer); Do(MenuAction.ConfirmAppearance);
            Assert.AreEqual(MenuScreen.HostSlot, flow.Screen);
            var host = flow.Apply(MenuInput.SlotPick(2));
            Assert.AreEqual(MenuCommandKind.HostLobby, host.Kind); Assert.AreEqual(MenuScreen.HostLobby, flow.Screen);
            var start = Do(MenuAction.StartSession);
            Assert.AreEqual(MenuCommandKind.StartNewWorld, start.Kind); Assert.AreEqual(WorldMode.Multiplayer, start.Mode); Assert.AreEqual(2, start.Slot);
        }

        [Test] public void BackFromLobbyLeavesTheSession()
        {
            Do(MenuAction.NewGame); Do(MenuAction.ChooseMultiplayer); Do(MenuAction.ConfirmAppearance); flow.Apply(MenuInput.SlotPick(0));
            Assert.AreEqual(MenuCommandKind.LeaveSession, Do(MenuAction.Back).Kind);
            Assert.AreEqual(MenuScreen.HostSlot, flow.Screen);
            Do(MenuAction.Back); Do(MenuAction.Back); Do(MenuAction.Back);
            Assert.AreEqual(MenuScreen.Main, flow.Screen);
            Assert.AreEqual(WorldMode.Unset, flow.DraftMode);
        }

        [Test] public void AllFiveSlotsFullBlocksNewGameWithAMessage()
        {
            for (int i = 0; i < 5; i++) Add(i, WorldModeStatus.Multiplayer, i);
            Do(MenuAction.NewGame);
            Assert.AreEqual(MenuScreen.Message, flow.Screen); StringAssert.Contains("пять", flow.MessageText);
            Do(MenuAction.Back); Assert.AreEqual(MenuScreen.Main, flow.Screen);
        }

        [Test] public void JoinUsesTheJoinersOwnCustomiseThenAddressAndShowsRealErrors()
        {
            Do(MenuAction.Join); Assert.AreEqual(MenuScreen.Customise, flow.Screen); Assert.True(flow.DraftJoining);
            Assert.AreEqual(MenuCommandKind.SaveAppearance, Do(MenuAction.ConfirmAppearance).Kind);
            Assert.AreEqual(MenuScreen.JoinAddress, flow.Screen);
            Assert.AreEqual(MenuCommandKind.None, flow.Apply(MenuInput.Address("", 7770)).Kind); Assert.IsNotEmpty(flow.ErrorText);
            var c = flow.Apply(MenuInput.Address(" 192.168.1.20 ", 7770));
            Assert.AreEqual(MenuCommandKind.ConnectToHost, c.Kind); Assert.AreEqual("192.168.1.20", c.Address); Assert.AreEqual(7770, c.Port);
            flow.Apply(MenuInput.Failure(MenuAction.ConnectFailed, "Хост не отвечает (таймаут)"));
            Assert.AreEqual(MenuScreen.JoinAddress, flow.Screen); Assert.AreEqual("Хост не отвечает (таймаут)", flow.ErrorText);
            flow.Apply(MenuInput.Address("192.168.1.20", 7770)); Do(MenuAction.Connected);
            Assert.AreEqual(MenuScreen.ClientLobby, flow.Screen);
            var ready = Do(MenuAction.ToggleReady); Assert.AreEqual(MenuCommandKind.SetReady, ready.Kind); Assert.True(ready.Flag);
            flow.Apply(MenuInput.Failure(MenuAction.Disconnected, "Это одиночный мир"));
            Assert.AreEqual(MenuScreen.JoinAddress, flow.Screen); Assert.False(flow.LocalReady);
        }

        [Test] public void ContinueLoadsTheNewestLoadableWorld()
        {
            Add(0, WorldModeStatus.Solo, 10); Add(3, WorldModeStatus.Multiplayer, 30); Add(4, WorldModeStatus.Solo, 99, loadable: false);
            var c = Do(MenuAction.Continue);
            Assert.AreEqual(MenuCommandKind.LoadWorld, c.Kind); Assert.AreEqual(3, c.Slot); Assert.AreEqual(WorldMode.Multiplayer, c.Mode);
            Assert.AreEqual(WorldMode.Unset, c.LegacyChoice);
        }

        [Test] public void ContinueWithNothingShowsAMessage()
        {
            Do(MenuAction.Continue); Assert.AreEqual(MenuScreen.Message, flow.Screen);
        }

        [Test] public void LegacyWorldAsksTheOneTimeModeChoiceBeforeLoading()
        {
            Add(1, WorldModeStatus.LegacyNeedsChoice, 1);
            Do(MenuAction.Load); Assert.AreEqual(MenuScreen.LoadList, flow.Screen);
            Assert.AreEqual(MenuCommandKind.None, flow.Apply(MenuInput.SlotPick(1)).Kind);
            Assert.AreEqual(MenuScreen.LegacyModeChoice, flow.Screen);
            Assert.AreEqual(MenuCommandKind.None, flow.Apply(MenuInput.LegacyMode(WorldMode.Unset)).Kind);
            var c = flow.Apply(MenuInput.LegacyMode(WorldMode.Solo));
            Assert.AreEqual(MenuCommandKind.LoadWorld, c.Kind); Assert.AreEqual(WorldMode.Solo, c.LegacyChoice); Assert.AreEqual(1, c.Slot);
        }

        [Test] public void UnloadableWorldExplainsWhy()
        {
            Add(new WorldSlotCard { Index = 2, Occupied = true, Loadable = false, Problem = "Сохранение повреждено" });
            Do(MenuAction.Load); flow.Apply(MenuInput.SlotPick(2));
            Assert.AreEqual(MenuScreen.Message, flow.Screen); Assert.AreEqual("Сохранение повреждено", flow.MessageText);
        }

        [Test] public void SettingsGraphicsAudioAndQuitConfirm()
        {
            Do(MenuAction.Settings); Assert.AreEqual(MenuScreen.Settings, flow.Screen);
            Assert.AreEqual(MenuCommandKind.OpenGraphics, Do(MenuAction.OpenGraphics).Kind);
            Do(MenuAction.Back); Assert.AreEqual(MenuScreen.Settings, flow.Screen);
            Do(MenuAction.OpenAudio); Assert.AreEqual(MenuScreen.Audio, flow.Screen);
            Do(MenuAction.Back); Do(MenuAction.Back); Assert.AreEqual(MenuScreen.Main, flow.Screen);
            Do(MenuAction.Quit); Assert.AreEqual(MenuScreen.QuitConfirm, flow.Screen);
            Assert.AreEqual(MenuCommandKind.None, Do(MenuAction.Back).Kind); Assert.AreEqual(MenuScreen.Main, flow.Screen);
            Do(MenuAction.Quit); Assert.AreEqual(MenuCommandKind.QuitGame, Do(MenuAction.ConfirmQuit).Kind);
        }

        [Test] public void EditAppearanceFromMainReturnsToMain()
        {
            Do(MenuAction.EditAppearance); Assert.AreEqual(MenuScreen.Customise, flow.Screen);
            Assert.AreEqual(MenuCommandKind.SaveAppearance, Do(MenuAction.ConfirmAppearance).Kind);
            Assert.AreEqual(MenuScreen.Main, flow.Screen);
        }

        [Test] public void LaunchFailureReturnsToMainWithTheReason()
        {
            Do(MenuAction.NewGame); Do(MenuAction.ChooseSolo); Do(MenuAction.ConfirmAppearance); flow.Apply(MenuInput.SlotPick(0));
            Assert.AreEqual(MenuCommandKind.None, Do(MenuAction.Back).Kind, "no back out of a launch in progress");
            flow.Apply(MenuInput.Failure(MenuAction.LaunchFailed, "Порт занят"));
            Assert.AreEqual(MenuScreen.Message, flow.Screen); Assert.AreEqual("Порт занят", flow.MessageText);
            Do(MenuAction.Back); Assert.AreEqual(MenuScreen.Main, flow.Screen);
        }
    }

    public sealed class LobbyRosterTests
    {
        const string A = "aaaaaaaa1111", B = "bbbbbbbb2222", C = "cccccccc3333";

        [Test] public void HostStartsWhenEveryoneElseIsReady()
        {
            var r = new LobbyRoster();
            Assert.True(r.Join(PlayerIds.Host, "Федя", true));
            Assert.True(r.CanStart(out _), "a lone host may start a multiplayer world");
            Assert.True(r.Join(A, "Вадим", false));
            Assert.False(r.CanStart(out string why)); StringAssert.Contains("Вадим", why);
            Assert.True(r.SetReady(A, true));
            Assert.True(r.CanStart(out _));
            CollectionAssert.AreEqual(new[] { PlayerIds.Host, A }, r.StartingParticipants());
        }

        [Test] public void ReconnectIsTheSameMemberAndFourIsTheLimit()
        {
            var r = new LobbyRoster();
            r.Join(PlayerIds.Host, "H", true); r.Join(A, "a", false); r.SetReady(A, true);
            Assert.True(r.Join(A, "a2", false)); Assert.AreEqual(2, r.Count);
            Assert.False(r.Members[1].Ready, "a reconnect has to ready up again");
            r.Join(B, "b", false); r.Join(C, "c", false);
            Assert.False(r.Join("dddddddd4444", "d", false)); Assert.AreEqual(4, r.Count);
            Assert.False(r.Join("client:7", "x", false), "temporary ids are refused");
        }

        [Test] public void LeaveRemovesOnlyThatGuestNeverTheHost()
        {
            var r = new LobbyRoster();
            r.Join(PlayerIds.Host, "H", true); r.Join(A, "a", false);
            Assert.False(r.Leave(PlayerIds.Host)); Assert.True(r.Leave(A)); Assert.AreEqual(1, r.Count);
            Assert.False(r.SetReady(PlayerIds.Host, false), "the host is always ready");
        }
    }
}
