using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>Round 4 (Fedya's build_v04 playtest): reopening a sutured / patched belly (decision 4), the clip-driven
    /// escape (Escape_v01: strap opening at the StrapOpen events, the chain, interrupts, the exit side, ~1.5x speed).</summary>
    public sealed class OperationRound4RulesTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        [SetUp] public void Setup()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>(); tuning.sharedAbdomen = true; tuning.torsoStrap = false;
            state = OperationRules.Create("round4", tuning); rules = new OperationRules(state, tuning);
            state.onTable = state.aligned = true; state.knockedOut = false;
        }
        [TearDown] public void Teardown() => Object.DestroyImmediate(tuning);
        private void StrapAll() { for (int i = 0; i < 4; i++) state.restraints[i] = true; }
        private void Cut(OperationRules r) { for (int i = 1; i <= 40; i++) r.CutSharedGuide(3, i / 40f, 0f, 0.04f); }
        private void Open() { StrapAll(); state.sleepRemaining = 60f; Cut(rules); }
        private void SewAll() { for (int i = 1; i <= 60; i++) rules.Suture(i / 60f, 0f, 0.2f); }
        /// <summary>One quick stroke along the line (0.1 s samples).</summary>
        private void Stroke(OperationRules r) { for (int i = 1; i <= 30; i++) r.CutSharedGuide(3, i / 30f, 0f, 0.1f); }

        [Test] public void Reopen_DeadSuturedBody_OneStrokeOpensIt_InsidesAsTheyWere()
        {
            Open();
            var kidney = state.organs[0];
            for (int c = 0; c < kidney.connections.Length; c++) kidney.connections[c] = 1f;
            int damage = kidney.damage;
            SewAll(); Assert.True(state.sutured);
            rules.Die(DeathCause.Extraction);
            Assert.True(state.BellyClosed);
            Assert.True(rules.CanBeginSharedGuide(3, 0f, 0f), "the scalpel may start on the seam again (Fedya's bug)");
            int reopened = 0, opened = 0; rules.Cue += c => { if (c == PatientCue.Reopened) reopened++; if (c == PatientCue.IncisionOpened) opened++; };
            Stroke(rules);
            Assert.AreEqual(1, reopened); Assert.AreEqual(0, opened, "not a first opening: no new waste, no sloppy check");
            Assert.False(state.sutured); Assert.True(state.CavityOpen); Assert.AreEqual(0f, state.zoneSuture);
            Assert.True(kidney.Released, "released connections stay released"); Assert.AreEqual(damage, kidney.damage, "no new damage");
            Assert.True(rules.CanBeginSuture(0.01f, 0f), "and it can be sewn up again");
            SewAll(); Assert.True(state.sutured);
        }
        [Test] public void Reopen_IsOneStroke_NotASecondFullCut()
        {
            Open(); SewAll(); rules.Die(DeathCause.Extraction);
            // The cursor at the far end at once: the speed cap decides (the first cut 0.7 m/s, the reopening 2.5x).
            int reopen = 0;
            while (state.BellyClosed && reopen < 200) { reopen++; rules.CutSharedGuide(3, 1f, 0f, 0.05f); }
            var fresh = OperationRules.Create("fresh", tuning); var freshRules = new OperationRules(fresh, tuning);
            fresh.onTable = fresh.aligned = true;
            int first = 0;
            while (!fresh.zoneOpened && first < 200) { first++; freshRules.CutSharedGuide(3, 1f, 0f, 0.05f); }
            Assert.False(state.BellyClosed); Assert.True(fresh.zoneOpened);
            Assert.Less(reopen * 2, first, "one quick stroke: well under half the time of the first cut");
        }
        [Test] public void Reopen_SkinPatchOfADeadBodyOffTheTable()
        {
            Open(); rules.Die(DeathCause.Extraction);
            rules.PatchIfOpen();
            Assert.True(state.skinPatched); Assert.False(state.CavityOpen, "the patch closes the cavity");
            Assert.False(rules.CanBeginSuture(0.01f, 0f), "a patch is not sewn: reopen first");
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.True(loaded.skinPatched, "the patch is saved (and travels in the table view)");
            var again = new OperationRules(loaded, tuning);
            Stroke(again);
            Assert.False(loaded.skinPatched); Assert.True(loaded.CavityOpen);
            Assert.True(again.CanBeginSuture(0.01f, 0f));
        }
        [Test] public void Reopen_SpoilageContinues()
        {
            Open(); SewAll(); rules.Die(DeathCause.Extraction);
            rules.Tick(tuning.corpseGraceSeconds + tuning.corpseGradeSeconds * 2f + 1f, 0f, false);
            int loss = state.corpseLoss; Assert.Greater(loss, 0);
            Stroke(rules); Assert.True(state.CavityOpen);
            rules.Tick(tuning.corpseGradeSeconds + 0.5f, 0f, false);
            Assert.Greater(state.corpseLoss, loss, "the organs keep spoiling after the reopening");
        }

        // ---------- escape clips ----------
        private void Clips() { tuning.escapeClips = true; tuning.escapeSpeed = 1.5f; state.dazedRemaining = 0f; state.sleepRemaining = 0f; }
        private void Run(float seconds, float step = 0.02f) { for (float t = 0f; t < seconds && state.onTable; t += step) rules.Tick(step, 0f, false); }

        [Test] public void EscapeClips_OneArmStrapped_FreeHandThenSitUpLegsSwingHop_InTheContractTime()
        {
            Clips(); StrapAll(); state.restraints[0] = false; // Fedya's example: the left hand is free
            var started = new System.Collections.Generic.List<int>(); int ranOff = 0;
            var opened = new System.Collections.Generic.List<int>();
            rules.Cue += c =>
            {
                if (c == PatientCue.EscapeStep) started.Add(state.escapeClip);
                if (c == PatientCue.Unbuckled) opened.Add(rules.LastUnbuckledStrap);
                if (c == PatientCue.RanOff) ranOff++;
            };
            rules.PreferredEscapeSide = 1;
            float expected = OperationEscape.PlanSeconds(new[] { false, true, true, true }) / tuning.escapeSpeed;
            float t = 0f;
            while (state.onTable && t < 30f) { rules.Tick(0.02f, 0f, false); t += 0.02f; }
            CollectionAssert.AreEqual(new[] { OperationEscape.UnbuckleArmRByL, OperationEscape.SitUp, OperationEscape.UnbuckleLegsBoth,
                OperationEscape.SwingOffR, OperationEscape.HopRunR }, started);
            CollectionAssert.AreEqual(new[] { 1, 3, 2 }, opened, "right wrist, then the legs at the clip's StrapOpen events (R then L)");
            Assert.AreEqual(1, ranOff); Assert.False(state.onTable); Assert.True(state.ranOff); Assert.AreEqual(1, state.escapeSide);
            Assert.That(t, Is.EqualTo(expected).Within(0.1f), "one arm + both legs: 8.9 s authored (contract) / 1.5");
        }
        [Test] public void EscapeClips_StrapOpensExactlyAtTheEvent()
        {
            Clips(); StrapAll(); state.restraints[0] = false;
            Run(1.39f / 1.5f);
            Assert.True(state.restraints[1], "not before 1.40 s authored");
            Run(0.04f);
            Assert.False(state.restraints[1], "open at 1.40 s authored (0.93 s at 1.5x)");
            Assert.AreEqual(0, rules.LastUnbuckledHand, "by the left hand");
        }
        [Test] public void EscapeClips_BothArmsStrapped_NoEscape()
        {
            Clips(); state.restraints[0] = state.restraints[1] = true;
            Run(20f);
            Assert.True(state.onTable); Assert.AreEqual(-1, state.escapeClip);
        }
        [Test] public void EscapeClips_InjectionDuringTheReach_SlumpsBackLying()
        {
            Clips(); StrapAll(); state.restraints[0] = false;
            Run(0.5f);
            Assert.AreEqual(OperationEscape.UnbuckleArmRByL, state.escapeClip);
            int slumps = 0; rules.Cue += c => { if (c == PatientCue.EscapeSlump) slumps++; };
            state.sleepRemaining = 30f;
            rules.Tick(0.02f, 0f, false);
            Assert.AreEqual(1, slumps); Assert.AreEqual(OperationEscape.SlumpLieReachR, state.escapeClip);
            Run(2f);
            Assert.AreEqual(-1, state.escapeClip); Assert.AreEqual(OperationEscape.Lying, state.escapeStage);
            Assert.True(state.restraints[1], "interrupted before the buckle opened"); Assert.True(state.onTable);
        }
        [Test] public void EscapeClips_StrapClosedWhileSitting_SlumpsSit()
        {
            Clips(); state.restraints[2] = true; // only the left leg strapped
            Run((OperationEscape.Clips[OperationEscape.SitUp].seconds + 0.3f) / 1.5f);
            Assert.AreEqual(OperationEscape.UnbuckleLegL, state.escapeClip);
            Assert.True(rules.ToggleRestraint(0), "a player straps his left wrist");
            rules.Tick(0.02f, 0f, false);
            Assert.AreEqual(OperationEscape.SlumpSit, state.escapeClip);
        }
        [Test] public void EscapeClips_ExitSideAwayFromThePlayer_AndMissingLeftClipsFallBackRight()
        {
            Clips(); rules.PreferredEscapeSide = -1;
            Run(10f);
            Assert.AreEqual(-1, state.escapeSide, "the player stood on his right: he leaves over his left");
            var other = OperationRules.Create("r", tuning); var otherRules = new OperationRules(other, tuning);
            other.onTable = other.aligned = true; other.knockedOut = false;
            tuning.escapeMissingClips = 1 << OperationEscape.SwingOffL;
            otherRules.PreferredEscapeSide = -1;
            for (int i = 0; i < 500 && other.onTable; i++) otherRules.Tick(0.02f, 0f, false);
            Assert.AreEqual(1, other.escapeSide, "no left clips imported: his right side");
        }
        [Test] public void EscapeClips_StateIsSaved()
        {
            Clips(); StrapAll(); state.restraints[0] = false;
            Run(0.7f);
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.AreEqual(state.escapeClip, loaded.escapeClip); Assert.AreEqual(state.escapeClipTime, loaded.escapeClipTime, 1e-5f);
            var old = JsonUtility.FromJson<OperationState>("{\"patientId\":\"old\"}");
            Assert.AreEqual(-1, old.escapeClip, "an old save has no clip playing");
        }
    }
}
