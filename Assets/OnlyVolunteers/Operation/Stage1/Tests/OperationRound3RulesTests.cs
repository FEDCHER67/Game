using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>Round 3 (Fedya / lead, 2026-10-18): four limb straps (no torso strap), the per-strap unbuckle steps of an
    /// awake patient, suturing as the end of every operation and its release rules.</summary>
    public sealed class OperationRound3RulesTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        [SetUp] public void Setup()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>(); tuning.sharedAbdomen = true; tuning.torsoStrap = false;
            state = OperationRules.Create("round3", tuning); rules = new OperationRules(state, tuning);
            state.onTable = state.aligned = true; state.knockedOut = false;
        }
        [TearDown] public void Teardown() => Object.DestroyImmediate(tuning);
        private void StrapAll() { for (int i = 0; i < 4; i++) state.restraints[i] = true; }
        private void Open() { StrapAll(); state.sleepRemaining = 60f; for (int i = 1; i <= 40; i++) rules.CutSharedGuide(3, i / 40f, 0f, 0.04f); }
        private void SewAll() { for (int i = 1; i <= 60; i++) rules.Suture(i / 60f, 0f, 0.2f); }

        [Test] public void FourStraps_TorsoIsGoneAndOldSavesLoadItOpen()
        {
            Assert.AreEqual(4, OperationStraps.Count(tuning));
            Assert.False(rules.ToggleRestraint(4), "no torso strap to buckle");
            var old = OperationRules.Create("old-save", tuning); old.restraints[4] = true;
            var loaded = new OperationRules(old, tuning);
            Assert.False(old.restraints[4], "an old save's closed torso strap is not there any more");
            Assert.False(loaded.Held);
            StrapAll(); Assert.True(rules.Held, "all four limbs strapped hold him");
            state.restraints[2] = false; Assert.False(rules.Held);
        }
        [Test] public void FourStraps_AwakeAndAllStrapped_StrugglesNeverEscapes()
        {
            StrapAll(); state.dazedRemaining = 0f;
            rules.Tick(60f, 0f, false);
            Assert.True(state.onTable); Assert.AreEqual(0f, state.escapeProgress); Assert.True(state.LimbsStrapped);
            Assert.True(rules.CanOperate(false), "held down by the limbs: the operation may go on while he struggles");
        }
        [Test] public void FourStraps_AFreeHandUnbucklesTheRestOneByOneThenHeEscapes()
        {
            StrapAll(); state.restraints[0] = false; // the left hand is free
            int unbuckled = 0; rules.Cue += c => { if (c == PatientCue.Unbuckled) unbuckled++; };
            Assert.True(rules.NextUnbuckle(out int strap, out int hand)); Assert.AreEqual(1, strap); Assert.AreEqual(0, hand);
            for (int i = 0; i < 4 * 60; i++) rules.Tick(tuning.unbuckleSeconds / 50f, 0f, false);
            Assert.AreEqual(3, unbuckled, "right arm, left leg, right leg");
            Assert.AreEqual(3, rules.LastUnbuckledStrap, "the right leg strap went last"); Assert.AreEqual(0, rules.LastUnbuckledHand, "with the free left hand");
            Assert.True(OperationStraps.AllOpen(state, tuning));
            for (int i = 0; i < 100 && state.onTable; i++) rules.Tick(0.1f, 0f, false);
            Assert.False(state.onTable, "all straps open: he slides off (escape)");
            Assert.AreEqual(1, state.escapes);
        }
        [Test] public void FourStraps_BothArmsStrapped_NoUnbucklingEvenWithLegsFree()
        {
            state.restraints[0] = state.restraints[1] = true;
            Assert.False(rules.NextUnbuckle(out _, out _));
            rules.Tick(30f, 0f, false);
            Assert.True(state.onTable); Assert.True(state.restraints[0] && state.restraints[1]);
        }
        [Test] public void Suture_OnlyAfterTheOpening_FromTheTop_StitchByStitch()
        {
            Assert.False(rules.CanBeginSuture(0f, 0f), "nothing to sew before the opening");
            Assert.AreEqual(CutStep.None, rules.Suture(0.5f, 0f, 1f));
            Open();
            Assert.False(rules.CanBeginSuture(0.6f, 0f), "the seam starts at the top end");
            Assert.True(rules.CanBeginSuture(0.01f, 0f));
            int stitches = 0, sutured = 0; rules.Cue += c => { if (c == PatientCue.Stitch) stitches++; if (c == PatientCue.Sutured) sutured++; };
            for (int i = 1; i <= 30; i++) rules.Suture(i / 60f, 0f, 0.2f);
            Assert.That(state.zoneSuture, Is.InRange(0.45f, 0.55f)); Assert.AreEqual(rules.Stitches, stitches); Assert.False(state.sutured);
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.AreEqual(state.zoneSuture, loaded.zoneSuture, "the seam progress is saved");
            Assert.True(rules.CanBeginSuture(state.zoneSuture + 0.01f, 0f), "resumes where it stopped");
            for (int i = 31; i <= 60; i++) rules.Suture(i / 60f, 0f, 0.2f);
            Assert.True(state.sutured); Assert.AreEqual(tuning.sutureStitches, stitches); Assert.AreEqual(1, sutured);
            Assert.False(rules.CanBeginSuture(0.99f, 0f), "sewn once");
        }
        [Test] public void Suture_ClosedBellyBlocksOrgans()
        {
            Open(); var kidney = state.organs[0]; kidney.connections[0] = kidney.connections[1] = 1f;
            for (int c = 0; c < kidney.connections.Length; c++) kidney.connections[c] = 1f;
            SewAll(); Assert.True(state.sutured); Assert.False(state.CavityOpen);
            bool latched = false;
            Assert.False(rules.Pull(0, 1f, 1, 1f, ref latched), "no pulling through a sewn belly");
            Assert.False(rules.SnipCord(1, 0, 10f), "no cord cutting through a sewn belly");
            Assert.False(rules.Extract(0, 0.5f));
        }
        [Test] public void Suture_LivingPatientKeepsHisStrapsUntilSewn_DeadOneDoesNot()
        {
            Open(); state.sleepRemaining = 0f; state.dazedRemaining = 0f; state.restraints[0] = false;
            Assert.True(rules.MustSutureBeforeRelease);
            Assert.False(rules.ToggleRestraint(1), "a strap of a living patient with an open belly does not open");
            Assert.True(state.restraints[1]);
            Assert.True(rules.ToggleRestraint(0), "closing one is fine");
            state.restraints[0] = false; // a free hand...
            rules.Tick(30f, 0f, false);
            Assert.True(state.restraints[1] && state.restraints[2] && state.restraints[3], "...does not unbuckle anything while the belly is open");
            Assert.True(state.onTable, "and he does not escape");
            SewAll();
            Assert.False(rules.MustSutureBeforeRelease);
            Assert.True(rules.ToggleRestraint(1), "sewn up: the straps open again");
            var dead = OperationRules.Create("dead", tuning); var deadRules = new OperationRules(dead, tuning);
            dead.onTable = dead.aligned = true; dead.zoneOpened = true; for (int i = 0; i < 4; i++) dead.restraints[i] = true;
            deadRules.Die(DeathCause.Extraction);
            Assert.False(deadRules.MustSutureBeforeRelease);
            Assert.True(deadRules.ToggleRestraint(2), "a dead patient may be unstrapped unsewn");
        }
    }
}
