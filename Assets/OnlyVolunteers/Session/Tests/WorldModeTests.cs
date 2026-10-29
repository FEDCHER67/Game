using System;
using NUnit.Framework;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Session.Tests
{
    public sealed class WorldModeTests
    {
        const string Utc = "2026-10-29T10:00:00Z";

        [Test] public void NewWorldStoresItsModeAndAFreshPrologue()
        {
            var solo = WorldModeRules.CreateNew(WorldMode.Solo, Utc);
            Assert.AreEqual(WorldModeStatus.Solo, WorldModeRules.Status(solo));
            Assert.AreEqual(WorldProfileSaveBlock.CurrentBlockVersion, solo.blockVersion);
            Assert.AreEqual(PrologueStage.NotStarted, PrologueState.FromSave(solo.prologue).Stage);
            Assert.AreEqual(WorldModeStatus.Multiplayer, WorldModeRules.Status(WorldModeRules.CreateNew(WorldMode.Multiplayer, Utc)));
            Assert.Throws<ArgumentException>(() => WorldModeRules.CreateNew(WorldMode.Unset, Utc));
        }

        [Test] public void ModeIsImmutableAfterCreation()
        {
            var b = WorldModeRules.CreateNew(WorldMode.Solo, Utc);
            Assert.AreEqual(ModeChange.Refused, WorldModeRules.RequestChange(b, WorldMode.Multiplayer));
            Assert.AreEqual(ModeChange.Unchanged, WorldModeRules.RequestChange(b, WorldMode.Solo));
            Assert.False(WorldModeRules.ResolveLegacy(b, WorldMode.Multiplayer, Utc), "not a legacy world: no migration path");
            Assert.AreEqual(WorldMode.Solo, b.Mode);
        }

        [Test] public void ModeSurvivesASaveRoundTrip()
        {
            var b = WorldModeRules.CreateNew(WorldMode.Multiplayer, Utc);
            var copy = b.Copy(); copy.mode = (int)WorldMode.Solo; // a copy is independent
            Assert.AreEqual(WorldMode.Multiplayer, b.Mode);
            var loaded = b.Copy();
            Assert.AreEqual(WorldModeStatus.Multiplayer, WorldModeRules.Status(loaded));
            Assert.AreEqual(Utc, loaded.createdUtc);
        }

        [Test] public void LegacyWorldIsFlaggedNeverAutoAssigned()
        {
            var legacy = new WorldProfileSaveBlock(); // what an old save deserializes to: blockVersion 0
            Assert.AreEqual(WorldModeStatus.LegacyNeedsChoice, WorldModeRules.Status(legacy));
            Assert.True(WorldModeRules.NeedsMigrationChoice(legacy));
            Assert.AreEqual(ModeChange.Refused, WorldModeRules.RequestChange(legacy, WorldMode.Solo), "only the explicit migration choice sets it");
            Assert.AreEqual(WorldModeStatus.LegacyNeedsChoice, WorldModeRules.Status(legacy));
            Assert.AreEqual("Старый мир: режим не выбран", WorldModeRules.CardLabel(WorldModeRules.Status(legacy)));
        }

        [Test] public void LegacyExplicitChoiceIsOneTimeAndSkipsTheOpening()
        {
            var legacy = new WorldProfileSaveBlock();
            Assert.False(WorldModeRules.ResolveLegacy(legacy, WorldMode.Unset, Utc));
            Assert.True(WorldModeRules.ResolveLegacy(legacy, WorldMode.Multiplayer, Utc));
            Assert.AreEqual(WorldModeStatus.Multiplayer, WorldModeRules.Status(legacy));
            Assert.True(legacy.migratedFromLegacy);
            Assert.False(WorldModeRules.ResolveLegacy(legacy, WorldMode.Solo, Utc), "a second choice is refused");
            var p = PrologueState.FromSave(legacy.prologue);
            Assert.AreEqual(PrologueStage.Completed, p.Stage, "an old world never gets the opening retro-fitted");
            Assert.True(p.TramduroFired);
        }

        [Test] public void SoloWorldRejectsEveryRemoteJoinButTheHostItself()
        {
            Assert.AreEqual(JoinVerdict.Accept, WorldModeRules.DecideJoin(WorldModeStatus.Solo, true, 0));
            Assert.AreEqual(JoinVerdict.RejectSoloWorld, WorldModeRules.DecideJoin(WorldModeStatus.Solo, false, 1));
            Assert.AreEqual(JoinVerdict.RejectSoloWorld, WorldModeRules.DecideJoin(WorldModeStatus.Solo, false, 0));
            StringAssert.Contains("одиночный", WorldModeRules.Explain(JoinVerdict.RejectSoloWorld));
        }

        [Test] public void MultiplayerWorldStaysMultiplayerWithAnyParticipantCount()
        {
            var b = WorldModeRules.CreateNew(WorldMode.Multiplayer, Utc);
            var st = WorldModeRules.Status(b);
            Assert.AreEqual(JoinVerdict.Accept, WorldModeRules.DecideJoin(st, false, 1), "a lone host still accepts friends");
            Assert.AreEqual(JoinVerdict.Accept, WorldModeRules.DecideJoin(st, false, 3));
            Assert.AreEqual(JoinVerdict.RejectFull, WorldModeRules.DecideJoin(st, false, 4));
            Assert.AreEqual(WorldModeStatus.Multiplayer, WorldModeRules.Status(b), "participant changes never convert the mode");
        }

        [Test] public void NoWorldAndLegacyKeepTodaysJoinBehaviour()
        {
            Assert.AreEqual(JoinVerdict.Accept, WorldModeRules.DecideJoin(WorldModeStatus.NoWorld, false, 1));
            Assert.AreEqual(JoinVerdict.Accept, WorldModeRules.DecideJoin(WorldModeStatus.LegacyNeedsChoice, false, 1));
            Assert.AreEqual(WorldModeStatus.NoWorld, WorldModeRules.Status(null));
        }
    }
}
