using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Session.Tests
{
    /// <summary>Start-menu flow v2 (Fedya 29.10: Играть → world cards → new world (name, Solo/Co-op, intro) → the sausage
    /// customisation → start / host lobby; Продолжить only with a save; Delete asks first; nothing is wiped otherwise).</summary>
    public sealed class MainMenuFlowV02Tests
    {
        static List<WorldSlotCard> Cards(params WorldSlotCard[] c) => new List<WorldSlotCard>(c);

        static WorldSlotCard World(int i, WorldModeStatus mode, long ticks = 1, bool loadable = true) =>
            new WorldSlotCard { Index = i, Occupied = true, Loadable = loadable, Name = "W" + i, Mode = mode, SavedTicksUtc = ticks, Problem = loadable ? "" : "повреждён" };

        [Test]
        public void Continue_is_offered_only_with_a_loadable_world_and_picks_the_newest()
        {
            Assert.False(new MainMenuFlowV2(() => Cards()).CanContinue);
            Assert.False(new MainMenuFlowV2(() => Cards(World(0, WorldModeStatus.Solo, 5, loadable: false))).CanContinue);
            var flow = new MainMenuFlowV2(() => Cards(World(0, WorldModeStatus.Solo, 5), World(3, WorldModeStatus.Solo, 9)));
            Assert.True(flow.CanContinue);
            var c = flow.Apply(MenuInputV2.Of(MenuActionV2.Continue));
            Assert.AreEqual(MenuCommandKindV2.LoadWorld, c.Kind);
            Assert.AreEqual(3, c.Slot);
            Assert.AreEqual(MenuScreenV2.Launching, flow.Screen);
        }

        [Test]
        public void Solo_new_world_goes_name_mode_customise_then_starts_with_the_choices()
        {
            var flow = new MainMenuFlowV2(() => Cards(World(0, WorldModeStatus.Solo)));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            Assert.AreEqual(MenuScreenV2.Worlds, flow.Screen);
            flow.Apply(MenuInputV2.OnSlot(MenuActionV2.NewInSlot, 0));
            Assert.AreEqual(MenuScreenV2.Worlds, flow.Screen, "an occupied slot is never a new world");
            StringAssert.Contains("занят", flow.ErrorText);
            flow.Apply(MenuInputV2.OnSlot(MenuActionV2.NewInSlot, 2));
            Assert.AreEqual(MenuScreenV2.NewWorld, flow.Screen);
            Assert.AreEqual("Мир 3", flow.DraftName);
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmNewWorld));
            Assert.AreEqual(MenuScreenV2.NewWorld, flow.Screen, "the mode must be chosen");
            flow.Apply(MenuInputV2.WithMode(MenuActionV2.SetMode, WorldMode.Solo));
            flow.Apply(MenuInputV2.WithText(MenuActionV2.SetName, "  Лесной\n мир  "));
            flow.Apply(MenuInputV2.WithFlag(MenuActionV2.SetIntro, false));
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmNewWorld));
            Assert.AreEqual(MenuScreenV2.Customise, flow.Screen);
            var save = flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmAppearance));
            Assert.AreEqual(MenuCommandKindV2.SaveAppearance, save.Kind);
            var start = flow.FollowUpAfterAppearance();
            Assert.AreEqual(MenuCommandKindV2.StartNewWorld, start.Kind);
            Assert.AreEqual(2, start.Slot);
            Assert.AreEqual(WorldMode.Solo, start.Mode);
            Assert.AreEqual("Лесной мир", start.Name);
            Assert.True(start.SkipIntro);
            Assert.AreEqual(MenuScreenV2.Launching, flow.Screen);
            Assert.AreEqual(MenuCommandKindV2.None, flow.Apply(MenuInputV2.Of(MenuActionV2.Back)).Kind, "no way back out of a launch");
        }

        [Test]
        public void Coop_new_world_hosts_a_lobby_and_starts_from_it()
        {
            var flow = new MainMenuFlowV2(() => Cards());
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            flow.Apply(MenuInputV2.OnSlot(MenuActionV2.NewInSlot, 0));
            flow.Apply(MenuInputV2.WithMode(MenuActionV2.SetMode, WorldMode.Multiplayer));
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmNewWorld));
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmAppearance));
            var host = flow.FollowUpAfterAppearance();
            Assert.AreEqual(MenuCommandKindV2.HostLobby, host.Kind);
            Assert.False(host.ForLoad);
            Assert.AreEqual(MenuScreenV2.HostLobby, flow.Screen);
            var start = flow.Apply(MenuInputV2.Of(MenuActionV2.StartSession));
            Assert.AreEqual(MenuCommandKindV2.StartNewWorld, start.Kind);
            Assert.AreEqual(WorldMode.Multiplayer, start.Mode);
            Assert.False(start.SkipIntro, "the intro is on unless the owner switched it off");
        }

        [Test]
        public void Leaving_the_host_lobby_closes_it_and_returns_to_the_customiser()
        {
            var flow = new MainMenuFlowV2(() => Cards());
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            flow.Apply(MenuInputV2.OnSlot(MenuActionV2.NewInSlot, 1));
            flow.Apply(MenuInputV2.WithMode(MenuActionV2.SetMode, WorldMode.Multiplayer));
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmNewWorld));
            flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmAppearance));
            Assert.AreEqual(MenuCommandKindV2.LeaveSession, flow.Apply(MenuInputV2.Of(MenuActionV2.Back)).Kind);
            Assert.AreEqual(MenuScreenV2.Customise, flow.Screen);
        }

        [Test]
        public void Loading_follows_the_saved_mode_and_a_legacy_world_asks_once()
        {
            var flow = new MainMenuFlowV2(() => Cards(World(0, WorldModeStatus.Solo), World(1, WorldModeStatus.Multiplayer), World(2, WorldModeStatus.LegacyNeedsChoice)));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            var solo = flow.Apply(MenuInputV2.OnSlot(MenuActionV2.LoadSlot, 0));
            Assert.AreEqual(MenuCommandKindV2.LoadWorld, solo.Kind);
            Assert.AreEqual(WorldMode.Solo, solo.Mode);

            flow = new MainMenuFlowV2(() => Cards(World(1, WorldModeStatus.Multiplayer)));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            var lobby = flow.Apply(MenuInputV2.OnSlot(MenuActionV2.LoadSlot, 1));
            Assert.AreEqual(MenuCommandKindV2.HostLobby, lobby.Kind);
            Assert.True(lobby.ForLoad);
            var load = flow.Apply(MenuInputV2.Of(MenuActionV2.StartSession));
            Assert.AreEqual(MenuCommandKindV2.LoadWorld, load.Kind);
            Assert.AreEqual(WorldMode.Unset, load.LegacyChoice);

            flow = new MainMenuFlowV2(() => Cards(World(2, WorldModeStatus.LegacyNeedsChoice)));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            Assert.AreEqual(MenuCommandKindV2.None, flow.Apply(MenuInputV2.OnSlot(MenuActionV2.LoadSlot, 2)).Kind);
            Assert.AreEqual(MenuScreenV2.LegacyModeChoice, flow.Screen);
            var legacy = flow.Apply(MenuInputV2.WithMode(MenuActionV2.ChooseLegacyMode, WorldMode.Solo));
            Assert.AreEqual(MenuCommandKindV2.LoadWorld, legacy.Kind);
            Assert.AreEqual(WorldMode.Solo, legacy.LegacyChoice);
        }

        [Test]
        public void Delete_asks_first_and_only_targets_that_slot()
        {
            var flow = new MainMenuFlowV2(() => Cards(World(4, WorldModeStatus.Solo)));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Play));
            Assert.AreEqual(MenuCommandKindV2.None, flow.Apply(MenuInputV2.OnSlot(MenuActionV2.DeleteSlot, 3)).Kind, "an empty slot has nothing to delete");
            Assert.AreEqual(MenuScreenV2.Worlds, flow.Screen);
            Assert.AreEqual(MenuCommandKindV2.None, flow.Apply(MenuInputV2.OnSlot(MenuActionV2.DeleteSlot, 4)).Kind);
            Assert.AreEqual(MenuScreenV2.DeleteConfirm, flow.Screen);
            flow.Apply(MenuInputV2.Of(MenuActionV2.Back));
            Assert.AreEqual(MenuScreenV2.Worlds, flow.Screen, "cancel deletes nothing");
            flow.Apply(MenuInputV2.OnSlot(MenuActionV2.DeleteSlot, 4));
            var del = flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmDelete));
            Assert.AreEqual(MenuCommandKindV2.DeleteWorld, del.Kind);
            Assert.AreEqual(4, del.Slot);
            Assert.AreEqual(MenuScreenV2.Worlds, flow.Screen);
        }

        [Test]
        public void Join_uses_the_joiners_own_look_then_address_with_real_errors()
        {
            var flow = new MainMenuFlowV2(() => Cards());
            flow.Apply(MenuInputV2.Of(MenuActionV2.Join));
            Assert.AreEqual(MenuScreenV2.Customise, flow.Screen);
            Assert.AreEqual(MenuCommandKindV2.SaveAppearance, flow.Apply(MenuInputV2.Of(MenuActionV2.ConfirmAppearance)).Kind);
            Assert.AreEqual(MenuCommandKindV2.None, flow.FollowUpAfterAppearance().Kind);
            Assert.AreEqual(MenuScreenV2.JoinAddress, flow.Screen);
            flow.Apply(MenuInputV2.Address("", 7791));
            StringAssert.Contains("адрес", flow.ErrorText);
            var connect = flow.Apply(MenuInputV2.Address(" 192.168.1.20 ", 7791));
            Assert.AreEqual(MenuCommandKindV2.ConnectToHost, connect.Kind);
            Assert.AreEqual("192.168.1.20", connect.Address);
            flow.Apply(MenuInputV2.WithText(MenuActionV2.ConnectFailed, "Хост не отвечает"));
            Assert.AreEqual(MenuScreenV2.JoinAddress, flow.Screen);
            Assert.AreEqual("Хост не отвечает", flow.ErrorText);
            flow.Apply(MenuInputV2.Address("127.0.0.1", 7791));
            flow.Apply(MenuInputV2.Of(MenuActionV2.Connected));
            Assert.AreEqual(MenuScreenV2.ClientLobby, flow.Screen);
            var ready = flow.Apply(MenuInputV2.Of(MenuActionV2.ToggleReady));
            Assert.AreEqual(MenuCommandKindV2.SetReady, ready.Kind);
            Assert.True(ready.Flag);
            flow.Apply(MenuInputV2.WithText(MenuActionV2.LobbyEnded, "Хост начал игру"));
            Assert.AreEqual(MenuScreenV2.Message, flow.Screen);
            Assert.AreEqual("Хост начал игру", flow.MessageText);
        }

        [Test]
        public void World_names_are_cleaned_and_never_empty()
        {
            Assert.AreEqual("Мир 2", MainMenuFlowV2.CleanName("   ", 1));
            Assert.AreEqual("ab", MainMenuFlowV2.CleanName("a;|b", 0));
            Assert.AreEqual(MainMenuFlowV2.MaxNameLength, MainMenuFlowV2.CleanName(new string('x', 80), 0).Length);
        }
    }
}
