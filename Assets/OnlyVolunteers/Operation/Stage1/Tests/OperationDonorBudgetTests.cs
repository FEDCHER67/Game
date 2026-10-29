using NUnit.Framework;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>PLAYER stage (Fedya 29.10): the severe drug-intoxication donor rule inside OperationRules — one blood portion
    /// OR one organ in total, first successful extraction = ordinary death — and that ordinary donors and anaesthetised
    /// patients keep their existing rules.</summary>
    public sealed class OperationDonorBudgetTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        private const string Id = "FOREST_WAGON_ADDICT_01";

        [SetUp] public void SetUp()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>();
            state = OperationRules.Create(Id, tuning); state.onTable = state.aligned = true; state.knockedOut = false; state.dazedRemaining = 0;
            state.restraints[0] = true;
            rules = new OperationRules(state, tuning);
        }
        [TearDown] public void TearDown() { Object.DestroyImmediate(tuning); }

        private void Severe() => Assert.True(rules.MarkSevereDrugIntoxication("authored:test/WagonAddict01"));
        private void Ready(int organ)
        {
            var o = state.organs[organ]; o.cut = 1; for (int c = 0; c < o.connections.Length; c++) o.connections[c] = 1; o.pull = tuning.pullDistance;
        }

        [Test] public void SevereDonorFirstSyringeDrawMintsOnePortionThenDies()
        {
            Severe();
            var s = SyringeInstance.New(SyringeKind.Blood);
            Assert.AreEqual(SyringeUseResult.Success, rules.FillSyringe(s, tuning.bloodSeconds, true, out bool done));
            Assert.True(done);
            Assert.NotNull(s.Portion); Assert.AreEqual(Id + "/blood/1", s.Portion.Id); Assert.AreEqual(Id, s.PersonId);
            Assert.AreEqual(1, state.bloodPortions);
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Blood, state.deathCause);
            Assert.True(rules.DonorExhausted); Assert.AreEqual("blood:" + Id + "/blood/1", state.donor.spentOn);
            Assert.True(state.spoilStarted, "the ordinary death path ran (spoilage clock)");
        }

        [Test] public void NoSecondPortionFromTheSevereDonorOnAnyPath()
        {
            Severe();
            var s = SyringeInstance.New(SyringeKind.Blood);
            rules.FillSyringe(s, tuning.bloodSeconds, true, out _);
            var other = SyringeInstance.New(SyringeKind.Blood);
            Assert.AreNotEqual(SyringeUseResult.Success, rules.FillSyringe(other, tuning.bloodSeconds, true, out bool done)); Assert.False(done);
            float fill = 0; Assert.False(rules.FillBlood(ref fill, 100)); Assert.AreEqual(0, fill);
            Assert.False(rules.CollectBlood(100)); Assert.False(rules.CanDrawBlood(0));
            Assert.AreEqual(1, state.bloodPortions, "one portion, never a second one minted from the corpse");
        }

        [Test] public void SevereDonorLegacyKitFillAlsoSpendsAndKills()
        {
            Severe();
            float fill = 0;
            Assert.True(rules.FillBlood(ref fill, tuning.bloodSeconds));
            Assert.False(state.alive); Assert.True(rules.DonorExhausted);
        }

        [Test] public void CancelledOrPartialDrawDoesNotSpendTheAllowance()
        {
            Severe();
            var s = SyringeInstance.New(SyringeKind.Blood);
            rules.FillSyringe(s, tuning.bloodSeconds * 0.5f, true, out bool done); Assert.False(done);
            SyringeRules.CancelDraw(s);
            Assert.True(state.alive); Assert.False(rules.DonorExhausted); Assert.AreEqual(0, state.bloodPortions);
            Assert.AreEqual(SyringeUseResult.Success, rules.FillSyringe(s, tuning.bloodSeconds, true, out done)); Assert.True(done);
            Assert.False(state.alive);
        }

        [Test] public void AfterTheBloodDrawNoOrganFromThatBody()
        {
            Severe();
            rules.FillSyringe(SyringeInstance.New(SyringeKind.Blood), tuning.bloodSeconds, true, out _);
            Ready(0);
            Assert.False(rules.Extract(0, 0.5f), "ordinary corpse processing would allow it; this donor is spent");
            Assert.AreEqual(0, state.extracted); Assert.False(state.organs[0].removed);
        }

        [Test] public void SevereDonorFirstOrganKillsWithoutRollAndBlocksEverythingElse()
        {
            Severe(); state.sleepRemaining = 100f; // asleep on the table: irrelevant to the rule
            Ready(0);
            Assert.True(rules.Extract(0, 0.99f), "a first kidney would normally survive this roll");
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Extraction, state.deathCause);
            Assert.True(state.organs[0].fatal); Assert.AreEqual(1f, state.organs[0].deathChance);
            Assert.AreEqual(1, state.extracted, "one organ item, no duplicate");
            Ready(1); Assert.False(rules.Extract(1, 0.99f)); Assert.AreEqual(1, state.extracted);
            float fill = 0; Assert.False(rules.FillBlood(ref fill, 100));
        }

        [Test] public void SevereDonorDeadOfAnotherCauseStillHasExactlyOneOrgan()
        {
            Severe();
            rules.Die(DeathCause.Overdose);
            Assert.False(rules.DonorExhausted, "a death that is not an extraction spends nothing");
            Ready(0); Ready(2);
            Assert.True(rules.Extract(0, 0.5f)); Assert.True(rules.DonorExhausted);
            Assert.False(state.organs[0].fatal, "no second death");
            Assert.False(rules.Extract(2, 0.5f)); Assert.AreEqual(1, state.extracted);
        }

        [Test] public void ConditionAndSpendSurviveASaveRoundTrip()
        {
            Severe();
            var loadedFresh = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.True(loadedFresh.donor.SevereIntoxication); Assert.False(loadedFresh.donor.Exhausted);
            rules.FillSyringe(SyringeInstance.New(SyringeKind.Blood), tuning.bloodSeconds, true, out _);
            var world = JsonUtility.FromJson<OperationWorldState>(JsonUtility.ToJson(new OperationWorldState { patient = state }));
            var again = new OperationRules(world.patient, tuning);
            Assert.True(again.DonorExhausted);
            Ready(0); Assert.False(again.Extract(0, 0.5f));
        }

        [Test] public void OldSaveWithoutTheBlockIsAnOrdinaryDonor()
        {
            string json = JsonUtility.ToJson(state).Replace("\"donor\"", "\"donorRemovedForTest\"");
            var old = JsonUtility.FromJson<OperationState>(json);
            Assert.NotNull(old.donor); Assert.False(old.donor.SevereIntoxication);
        }

        [Test] public void OrdinaryDonorKeepsTwoLivingPortionsAndAFatalThird()
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            for (int i = 1; i <= 3; i++)
            {
                Assert.AreEqual(SyringeUseResult.Success, rules.FillSyringe(s, tuning.bloodSeconds, true, out bool done)); Assert.True(done);
                Assert.AreEqual(i < 3, state.alive); SyringeRules.Empty(s);
            }
            Assert.AreEqual("", state.donor.spentOn);
        }

        [Test] public void AnaesthetisedOrdinaryPatientIsNotLimitedToOne()
        {
            state.sleepRemaining = 100f; state.residual = tuning.suitableMinimum; // our normal anaesthetic, not the condition
            var s = SyringeInstance.New(SyringeKind.Blood);
            rules.FillSyringe(s, tuning.bloodSeconds, true, out _);
            Assert.True(state.alive); Assert.AreEqual(1, state.bloodPortions);
            Ready(0); Assert.True(rules.Extract(0, 0.99f));
            Assert.True(state.alive, "first kidney with a 0.99 roll survives as before");
            Assert.False(state.donor.SevereIntoxication);
        }

        [Test] public void ConditionCannotBeAddedAfterAnExtraction()
        {
            rules.FillSyringe(SyringeInstance.New(SyringeKind.Blood), tuning.bloodSeconds, true, out _);
            Assert.False(rules.MarkSevereDrugIntoxication("authored:late"));
            Assert.False(state.donor.SevereIntoxication);
        }
    }
}
