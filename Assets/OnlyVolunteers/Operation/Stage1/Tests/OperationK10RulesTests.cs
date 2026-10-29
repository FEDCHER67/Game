using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>K10 (Fedya 29.10, variant В, refined): a living patient with the belly opened and not sewn may try to escape
    /// with a free strap (OB-02); he gets up and runs off the table, but pain shock (DeathCause.Shock, the existing death)
    /// kills him after a server-rolled 2..12 m of his own escape travel (rolled once, saved; Fedya 29.10 option б: inside the
    /// B02 yard), or after the backstop seconds of that locomotion if he gets stuck. He never gets further than 12 m alive. Carrying / the van / lying stunned do not
    /// count, so a recapture and a reclosure stay possible. The one spoilage clock is not restarted by that death, he dies
    /// once, and his organs stay harvestable. A sewn-up belly escapes by the normal rules.</summary>
    public sealed class OperationK10RulesTests
    {
        private const float Step = 0.02f;
        /// <summary>Metres per physics step at the field NPC's flee speed (4.5 m/s).</summary>
        private const float RunStep = 4.5f * Step;

        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        private readonly List<PatientCue> cues = new List<PatientCue>();

        [SetUp] public void Setup()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>(); tuning.sharedAbdomen = true; tuning.torsoStrap = false;
            state = OperationRules.Create("k10", tuning);
            Bind(state);
            state.onTable = state.aligned = true; state.knockedOut = false;
        }
        [TearDown] public void Teardown() => Object.DestroyImmediate(tuning);

        private void Bind(OperationState s)
        {
            rules = new OperationRules(s, tuning) { ShockRunRandom = () => 0.5f }; // 7 m
            cues.Clear(); rules.Cue += cues.Add;
        }
        private int Count(PatientCue cue) { int n = 0; foreach (var c in cues) if (c == cue) n++; return n; }
        private void StrapAll() { for (int i = 0; i < 4; i++) state.restraints[i] = true; }
        private void Open() { StrapAll(); state.sleepRemaining = 60f; for (int i = 1; i <= 40; i++) rules.CutSharedGuide(3, i / 40f, 0f, 0.04f); }
        private void SewAll() { for (int i = 1; i <= 60; i++) rules.Suture(i / 60f, 0f, 0.2f); }
        private void Wake() { state.sleepRemaining = 0f; state.dazedRemaining = 0f; }
        private void Clips() { tuning.escapeClips = true; tuning.escapeSpeed = 1.5f; }
        private float RunUntilOff(float max = 40f)
        {
            float t = 0f;
            while (state.onTable && t < max) { rules.Tick(Step, 0f, false); t += Step; }
            return t;
        }
        /// <summary>The field NPC runs at 4.5 m/s (CaptureNpc feeds the metres, the rules tick the time). Returns the metres
        /// he reached ALIVE (the fatal step is not counted: there he is already falling dead).</summary>
        private float RunInField(float maxSeconds = 30f)
        {
            float run = 0f;
            for (float t = 0f; t < maxSeconds && state.alive; t += Step)
            {
                rules.Tick(Step, 0f, false);
                if (!state.alive) break;
                rules.AdvanceShockRun(RunStep, Step);
                if (!state.alive) break;
                run += RunStep;
            }
            return run;
        }

        [Test] public void OpenedBelly_FreeHand_TriesToEscape_RunsOff_DiesOfPainShockWithin12m()
        {
            Open(); Assert.True(state.CavityOpen);
            Clips(); Wake(); state.restraints[0] = false; // the left hand is free (OB-02: any open strap = an attempt)
            RunUntilOff();
            Assert.GreaterOrEqual(Count(PatientCue.EscapeAttempt), 1, "the opened patient tries to escape now (OB-02)");
            Assert.AreEqual(1, Count(PatientCue.RanOff), "he gets up and runs off the table (the normal escape clips)");
            Assert.False(state.onTable); Assert.True(state.alive, "alive at the hand-off to the field");
            Assert.True(state.ShockRun, "but the run is doomed");
            Assert.AreEqual(7f, state.shockRunMeters, 1e-3f, "server roll 0.5 in 2..12 m");
            float run = RunInField();
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Shock, state.deathCause, "pain shock, the existing death");
            Assert.AreEqual(1, Count(PatientCue.Death)); Assert.AreEqual(1, Count(PatientCue.ShockDeath));
            Assert.That(state.shockRunCovered, Is.InRange(state.shockRunMeters, state.shockRunMeters + RunStep + 1e-4f));
            Assert.LessOrEqual(run, 12f, "never further than 12 m alive");
            Assert.Less(state.shockRunTime, tuning.shockRunMaxSeconds, "the distance killed him, not the backstop");
        }

        [TestCase(0f, 2f)]
        [TestCase(0.5f, 7f)]
        [TestCase(1f, 12f)]
        public void DoomedRun_DistanceIsRolledIn2To12m_AndKillsThere(float roll, float metres)
        {
            Open(); Wake();
            rules.ShockRunRandom = () => roll;
            state.onTable = state.aligned = false; // off the table (escaped, fell or carried)
            Assert.True(rules.ArmShockRun());
            Assert.AreEqual(metres, state.shockRunMeters, 1e-3f);
            float run = RunInField();
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Shock, state.deathCause);
            Assert.That(run, Is.InRange(metres - RunStep - 1e-3f, metres), "dies after the rolled distance");
            Assert.LessOrEqual(run, 12f, "inside the yard (Fedya 29.10, option б)");
        }

        [Test] public void DoomedRun_StuckWhileTryingToRun_TheBackstopKillsHim_SleepDoesNotCount()
        {
            Open(); state.onTable = state.aligned = false;
            Assert.True(rules.ArmShockRun());
            state.sleepRemaining = 30f; // asleep on the floor: nothing counts
            for (int i = 0; i < 500; i++) { rules.Tick(Step, 0f, false); Assert.False(rules.AdvanceShockRun(RunStep, Step)); }
            Assert.True(state.alive); Assert.AreEqual(0f, state.shockRunTime); Assert.AreEqual(0f, state.shockRunCovered);
            Wake();
            float t = 0f;
            while (state.alive && t < 30f) { rules.Tick(Step, 0f, false); rules.AdvanceShockRun(0f, Step); t += Step; } // running into a wall
            Assert.False(state.alive, "he never gets away alive, even stuck");
            Assert.AreEqual(DeathCause.Shock, state.deathCause);
            Assert.That(t, Is.EqualTo(tuning.shockRunMaxSeconds).Within(0.05f));
        }

        [Test] public void DoomedRun_Recaptured_CarriedBackAndSewn_Lives()
        {
            Open(); Clips(); Wake(); state.restraints[0] = false;
            RunUntilOff(); Assert.True(state.ShockRun);
            for (int i = 0; i < 50; i++) rules.AdvanceShockRun(RunStep, Step); // 4.5 m of running...
            Assert.True(state.alive);
            // ...knocked down and carried back: lying stunned / carried / in the van is not escape travel (not fed).
            for (int i = 0; i < 3000; i++) rules.Tick(Step, 0f, false);
            Assert.True(state.alive, "only his own escape locomotion kills him; the recapture is possible");
            state.onTable = state.aligned = true; state.sleepRemaining = 60f;
            Assert.False(rules.AdvanceShockRun(50f, 50f), "nothing counts on the table");
            SewAll(); Assert.True(state.sutured); Assert.False(state.ShockRun, "sewn up: the doom is lifted");
            Wake(); state.escapeStage = OperationEscape.Lying; cues.Clear();
            RunUntilOff();
            Assert.AreEqual(1, Count(PatientCue.RanOff)); Assert.False(state.ShockRun);
            RunInField(10f);
            Assert.True(state.alive, "a sewn-up runaway is a normal escapee (recapture rules unchanged)");
        }

        [Test] public void SuturedBelly_EscapesByTheNormalRules_NoDoom()
        {
            Open(); SewAll(); Assert.True(state.sutured); Assert.False(state.CavityOpen);
            Clips(); Wake(); state.restraints[0] = false;
            RunUntilOff();
            Assert.AreEqual(1, Count(PatientCue.RanOff)); Assert.False(state.onTable);
            Assert.False(state.ShockRun); Assert.AreEqual(0f, state.shockRunMeters);
            float run = RunInField(30f);
            Assert.True(state.alive, "a sewn-up runaway lives (normal OB-02 escape)");
            Assert.Greater(run, 100f);
            Assert.AreEqual(0, Count(PatientCue.Death));
        }

        [Test] public void SuturedBelly_AllFourStrapped_StillNoEscape()
        {
            Open(); SewAll(); Clips(); Wake();
            RunUntilOff(20f);
            Assert.True(state.onTable); Assert.AreEqual(0, Count(PatientCue.EscapeAttempt));
        }

        [Test] public void OpenedBelly_AllFourStrapped_NoAttempt_StaysOnTable()
        {
            Open(); Clips(); Wake();
            RunUntilOff(20f);
            Assert.True(state.onTable); Assert.True(state.alive); Assert.False(state.ShockRun);
            Assert.AreEqual(0, Count(PatientCue.EscapeAttempt), "all four closed: no escape (OB-02)");
        }

        [Test] public void ProceduralEscape_OpenedBelly_FallsOff_Doomed()
        {
            Open(); Wake(); state.restraints[0] = false; // escapeClips off: the round-3 unbuckle + EscapeFall
            RunUntilOff(60f);
            Assert.AreEqual(1, Count(PatientCue.Escaped)); Assert.AreEqual(1, Count(PatientCue.FailedEscapeFall));
            Assert.False(state.onTable); Assert.True(state.alive); Assert.True(state.ShockRun);
            RunInField();
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Shock, state.deathCause);
        }

        [Test] public void PainShockDeath_DoesNotRestartTheOneSpoilageClock()
        {
            Open();
            Assert.True(state.spoilStarted); Assert.AreEqual(OperationRules.SpoilByOpening, state.spoilCause);
            Assert.AreEqual(1, Count(PatientCue.SpoilageStarted));
            Clips(); Wake(); state.restraints[0] = false;
            float onTable = RunUntilOff();
            Assert.AreEqual(onTable, state.spoilAge, 0.05f, "the clock runs from the opening, also for the living");
            RunInField();
            Assert.False(state.alive);
            float atDeath = state.spoilAge;
            Assert.Greater(atDeath, onTable, "not reset to 0 by the death");
            Assert.AreEqual(OperationRules.SpoilByOpening, state.spoilCause, "death does not take over the clock");
            rules.Tick(10f, 0f, false);
            Assert.AreEqual(atDeath + 10f, state.spoilAge, 1e-3f, "it just continues");
            Assert.AreEqual(1, Count(PatientCue.SpoilageStarted));
        }

        [Test] public void PainShockDeath_HappensOnce()
        {
            Open(); Wake(); state.onTable = state.aligned = false; rules.ArmShockRun();
            Assert.True(rules.AdvanceShockRun(50f, 0f));
            Assert.False(state.alive); Assert.AreEqual(DeathCause.Shock, state.deathCause);
            float covered = state.shockRunCovered, time = state.shockRunTime;
            Assert.False(rules.AdvanceShockRun(10f, 1f), "a dead body does not die again");
            for (int i = 0; i < 600; i++) rules.Tick(Step, 0f, false);
            rules.Die(DeathCause.Shock); rules.Die(DeathCause.FailedEscape);
            Assert.AreEqual(1, Count(PatientCue.Death), "no double death");
            Assert.AreEqual(1, Count(PatientCue.ShockDeath));
            Assert.AreEqual(DeathCause.Shock, state.deathCause);
            Assert.AreEqual(covered, state.shockRunCovered); Assert.AreEqual(time, state.shockRunTime);
            Assert.False(rules.ArmShockRun(), "a dead body is not doomed again");
        }

        [Test] public void PainShockDeath_OrgansStayHarvestable()
        {
            Open(); Wake(); state.onTable = state.aligned = false; rules.ArmShockRun();
            rules.AdvanceShockRun(50f, 0f);
            Assert.False(state.alive); Assert.True(state.CavityOpen);
            state.onTable = state.aligned = true; // carried back and laid on the table
            var kidney = state.organs[0];
            for (int c = 0; c < kidney.connections.Length; c++) kidney.connections[c] = 1f;
            kidney.pull = tuning.pullDistance;
            Assert.True(rules.Extract(0, 0.5f), "the existing dead-body extraction");
            Assert.False(kidney.rollCompleted, "no death roll for a dead patient");
            Assert.AreEqual(1, state.extracted);
        }

        [Test] public void ArmShockRun_OnlyAnOpenLivingPatient_OnceAndSaved()
        {
            Assert.False(rules.ArmShockRun(), "never opened: no doom");
            Open(); Wake(); state.onTable = state.aligned = false;
            Assert.True(rules.ArmShockRun());
            rules.AdvanceShockRun(3f, 0.5f);
            rules.ShockRunRandom = () => 1f;
            Assert.True(rules.ArmShockRun(), "already doomed");
            Assert.AreEqual(7f, state.shockRunMeters, 1e-3f, "never re-rolled");
            Assert.AreEqual(3f, state.shockRunCovered, 1e-4f, "never restarted");
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.True(loaded.ShockRun); Assert.AreEqual(7f, loaded.shockRunMeters, 1e-3f); Assert.AreEqual(3f, loaded.shockRunCovered, 1e-4f);
            Assert.AreEqual(0.5f, loaded.shockRunTime, 1e-4f);
            var loadedRules = new OperationRules(loaded, tuning) { ShockRunRandom = () => 0f };
            Assert.True(loadedRules.ArmShockRun(), "a loaded / new owner's rules object (rejoin, hand-off) keeps the roll");
            Assert.AreEqual(7f, loaded.shockRunMeters, 1e-3f);
            loadedRules.AdvanceShockRun(3.9f, 0f); Assert.True(loaded.alive, "3 + 3.9 < 7");
            loadedRules.AdvanceShockRun(0.2f, 0f); Assert.False(loaded.alive, "the saved progress counts");
            var dead = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(loaded));
            var deadRules = new OperationRules(dead, tuning);
            Assert.False(dead.alive); Assert.False(deadRules.ArmShockRun()); Assert.False(deadRules.AdvanceShockRun(5f, 5f));
            Assert.False(dead.alive, "a saved dead runner never comes back alive");
            var old = JsonUtility.FromJson<OperationState>("{\"patientId\":\"old\",\"alive\":true}");
            Assert.False(old.ShockRun, "an older save is not doomed");
        }

        [Test] public void SewnUpAgain_TheDoomIsLifted()
        {
            Open(); state.onTable = state.aligned = false; Assert.True(rules.ArmShockRun());
            state.onTable = state.aligned = true; state.sleepRemaining = 60f; // caught, put back, asleep
            SewAll(); Assert.True(state.sutured);
            Assert.False(state.ShockRun); Assert.AreEqual(0f, state.shockRunMeters);
            state.onTable = state.aligned = false;
            Assert.False(rules.ArmShockRun(), "sewn: leaving the table is a normal escape");
        }

        [Test] public void ShockRunStep_HorizontalMetres_TeleportsDoNotCount()
        {
            Assert.AreEqual(1f, OperationRules.ShockRunStep(Vector3.zero, new Vector3(0.6f, 3f, 0.8f)), 1e-5f, "height ignored");
            Assert.AreEqual(0f, OperationRules.ShockRunStep(Vector3.zero, new Vector3(3f, 0f, 0f)), "a teleport");
            Assert.AreEqual(0f, OperationRules.ShockRunStep(Vector3.zero, new Vector3(float.NaN, 0f, 0f)));
            Open(); state.onTable = state.aligned = false; rules.ArmShockRun(); Wake();
            rules.AdvanceShockRun(float.NaN, float.NaN); rules.AdvanceShockRun(-5f, -1f);
            Assert.AreEqual(0f, state.shockRunCovered); Assert.AreEqual(0f, state.shockRunTime); Assert.True(state.alive);
        }

        [Test] public void ShockRunCounts_OnlyHisOwnLocomotion()
        {
            Assert.True(OperationRules.ShockRunCounts(onFeet: true, crawling: false, carried: false, inVehicle: false), "running");
            Assert.True(OperationRules.ShockRunCounts(false, true, false, false), "crawling away");
            Assert.False(OperationRules.ShockRunCounts(false, true, true, false), "carried");
            Assert.False(OperationRules.ShockRunCounts(false, false, false, true), "in the van");
            Assert.False(OperationRules.ShockRunCounts(true, false, false, true), "the van moving him");
            Assert.False(OperationRules.ShockRunCounts(false, false, false, false), "lying stunned / getting up");
        }

        // ---------- K10 panic v02 variants (Fedya 29.10): the opened patient frees himself in a panic ----------

        private void Run(float seconds) { for (float t = 0f; t < seconds && state.onTable; t += Step) rules.Tick(Step, 0f, false); }
        private List<int> Started() { var started = new List<int>(); rules.Cue += c => { if (c == PatientCue.EscapeStep) started.Add(state.escapeClip); }; return started; }

        [Test] public void Panic_IdsMapToTheirV01Base()
        {
            Assert.AreEqual(35, OperationEscape.Count); Assert.AreEqual(20, OperationEscape.V01Count);
            for (int id = OperationEscape.FirstPanic; id < OperationEscape.Count; id++)
            {
                int b = OperationEscape.BaseOf(id);
                Assert.Less(b, OperationEscape.V01Count); Assert.AreEqual(id, OperationEscape.PanicOf(b));
                StringAssert.StartsWith(OperationEscape.Clips[b].name + "_", OperationEscape.Clips[id].name);
                Assert.AreEqual(OperationEscape.Clips[b].strapA, OperationEscape.Clips[id].strapA, "same buckle logic");
            }
            Assert.AreEqual("Esc_Lie_UnbuckleArmR_ByL_Panic", OperationEscape.Clips[OperationEscape.PanicUnbuckleArmRByL].name);
            Assert.AreEqual("Esc_HopRun_R_BellyClutch", OperationEscape.Clips[OperationEscape.ClutchHopRunR].name);
            Assert.True(OperationEscape.IsHopRun(OperationEscape.ClutchHopRunL)); Assert.AreEqual(-1, OperationEscape.Side(OperationEscape.ClutchHopRunL));
            Assert.True(OperationEscape.IsStumble(OperationEscape.PanicStumbleOffR));
            Assert.AreEqual(-1, OperationEscape.PanicOf(OperationEscape.SlumpSit), "slumps have no panic variant");
            // Escape_Panic_v02 lengths (escape_clips_manifest_v02.json); StrapOpen times as v01.
            Assert.AreEqual(3.0f, rules.ClipData(OperationEscape.PanicUnbuckleArmRByL).seconds, 1e-5f);
            Assert.AreEqual(1.4f, rules.ClipData(OperationEscape.PanicUnbuckleArmRByL).openA, 1e-5f);
            Assert.AreEqual(1.2f, rules.ClipData(OperationEscape.PanicSitUp).seconds, 1e-5f);
            Assert.AreEqual(2.8f, rules.ClipData(OperationEscape.PanicUnbuckleLegsBoth).seconds, 1e-5f);
            Assert.AreEqual(1.08f, rules.ClipData(OperationEscape.PanicUnbuckleLegsBoth).openA, 1e-5f);
            Assert.AreEqual(1.4f, rules.ClipData(OperationEscape.PanicSwingOffR).seconds, 1e-5f);
            Assert.AreEqual(1.8f, rules.ClipData(OperationEscape.PanicStumbleOffL).seconds, 1e-5f);
            Assert.AreEqual(1.5f, rules.ClipData(OperationEscape.ClutchHopRunR).seconds, 1e-5f);
        }

        [Test] public void Panic_NotImported_OpenedPatientFallsBackToV01()
        {
            Open(); Clips(); Wake(); state.restraints[0] = false; // tuning default: every panic variant missing
            var started = Started();
            RunUntilOff();
            Assert.AreEqual(1, Count(PatientCue.RanOff)); Assert.True(state.ShockRun);
            Assert.IsNotEmpty(started);
            foreach (int id in started) Assert.False(OperationEscape.IsPanic(id), "v01 while the v02 clips are not imported");
        }

        [Test] public void Panic_Imported_OpenedPatientFreesHimselfInPanic_ThenRunsDoomed()
        {
            Open(); Clips(); Wake(); state.restraints[0] = false; tuning.escapePanicMissing = 0;
            var started = Started();
            var opened = new List<int>(); rules.Cue += c => { if (c == PatientCue.Unbuckled) opened.Add(rules.LastUnbuckledStrap); };
            rules.PreferredEscapeSide = 1;
            RunUntilOff();
            CollectionAssert.AreEqual(new[] { OperationEscape.PanicUnbuckleArmRByL, OperationEscape.PanicSitUp, OperationEscape.PanicUnbuckleLegsBoth,
                OperationEscape.PanicSwingOffR, OperationEscape.ClutchHopRunR }, started);
            CollectionAssert.AreEqual(new[] { 1, 3, 2 }, opened, "the same straps at the same buckle events");
            Assert.AreEqual(1, Count(PatientCue.RanOff)); Assert.True(state.ranOff); Assert.True(state.ShockRun);
        }

        [Test] public void Panic_TimingsComeFromTheImportedManifest()
        {
            Open(); Clips(); Wake(); state.restraints[0] = false; tuning.escapePanicMissing = 0;
            tuning.escapePanicTiming = new float[OperationEscape.PanicCount * 3];
            tuning.escapePanicTiming[0] = 3.2f; tuning.escapePanicTiming[1] = 1.9f; // PanicUnbuckleArmRByL: 3.2 s, StrapOpen at 1.9 s
            Assert.AreEqual(3.2f, rules.ClipData(OperationEscape.PanicUnbuckleArmRByL).seconds, 1e-5f);
            Assert.AreEqual(2.6f, rules.ClipData(OperationEscape.UnbuckleArmRByL).seconds, 1e-5f, "v01 untouched");
            Run(1.88f / 1.5f);
            Assert.AreEqual(OperationEscape.PanicUnbuckleArmRByL, state.escapeClip);
            Assert.True(state.restraints[1], "not at the v01 1.40 s: at the panic clip's own 1.90 s");
            Run(0.04f);
            Assert.False(state.restraints[1]);
        }

        [Test] public void Panic_SuturedBelly_KeepsV01()
        {
            Open(); SewAll(); Clips(); Wake(); state.restraints[0] = false; tuning.escapePanicMissing = 0;
            var started = Started();
            RunUntilOff();
            Assert.AreEqual(1, Count(PatientCue.RanOff)); Assert.False(state.ShockRun);
            foreach (int id in started) Assert.False(OperationEscape.IsPanic(id), "the ordinary OB-02 escape keeps v01");
        }

        [Test] public void Panic_InterruptedLikeItsV01Base()
        {
            Open(); Clips(); Wake(); state.restraints[0] = false; tuning.escapePanicMissing = 0;
            Run(0.5f);
            Assert.AreEqual(OperationEscape.PanicUnbuckleArmRByL, state.escapeClip);
            state.sleepRemaining = 30f;
            rules.Tick(Step, 0f, false);
            Assert.AreEqual(OperationEscape.SlumpLieReachR, state.escapeClip, "the v01 slump");
            Run(2f);
            Assert.True(state.onTable); Assert.True(state.restraints[1]);
        }
    }
}
