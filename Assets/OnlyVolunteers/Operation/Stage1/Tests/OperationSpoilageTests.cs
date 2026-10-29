using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>WP05 (OPERATIONS_BASES_INTEGRATION v01 §1, §3, §4; OB-03…OB-07): ONE spoilage clock per patient from the
    /// earlier of the first opening and death, also for a living patient; 45 s grace then a grade every 40 s (first loss at
    /// +85 s, then +125 / +165); never restarted or doubled by death, reopening, suturing, a table change or a load; the
    /// first opening raises one warning cue. Closing consumes one suture kit per closure (reserved while sewing, kept over
    /// interruptions and loads) or one patch.</summary>
    public sealed class OperationSpoilageTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        private readonly List<PatientCue> cues = new List<PatientCue>();

        private sealed class Stock : IOperationSupplies
        {
            public readonly Dictionary<string, int> Count = new Dictionary<string, int>();
            public int Taken;
            public bool TryTake(string id)
            {
                if (!Count.TryGetValue(id, out int n) || n <= 0) return false;
                Count[id] = n - 1; Taken++; return true;
            }
        }

        [SetUp] public void Setup()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>(); tuning.sharedAbdomen = true; tuning.torsoStrap = false;
            state = OperationRules.Create("spoil", tuning); Bind(state);
            state.onTable = state.aligned = true; state.knockedOut = false;
            for (int i = 0; i < 4; i++) state.restraints[i] = true;
            state.sleepRemaining = 1000f; // asleep and strapped: the living patient lies still for the whole test
        }
        [TearDown] public void Teardown() => Object.DestroyImmediate(tuning);

        private void Bind(OperationState s)
        {
            cues.Clear();
            rules = new OperationRules(s, tuning);
            rules.Cue += c => cues.Add(c);
        }
        private void Open() { for (int i = 1; i <= 40; i++) rules.CutSharedGuide(3, i / 40f, 0f, 0.04f); }
        private void SewAll() { for (int i = 1; i <= 60; i++) rules.Suture(i / 60f, 0f, 0.2f); }
        private void Reopen() { for (int i = 1; i <= 30; i++) rules.CutSharedGuide(3, i / 30f, 0f, 0.1f); }
        private int Damage(int organ = 0) => state.organs[organ].damage;
        private int Count(PatientCue cue) { int n = 0; foreach (var c in cues) if (c == cue) n++; return n; }

        [Test] public void KeepsTheExisting45And40Seconds()
        {
            Assert.AreEqual(45f, tuning.corpseGraceSeconds);
            Assert.AreEqual(40f, tuning.corpseGradeSeconds);
        }

        [Test] public void LivingPatient_FirstOpeningStartsTheClock_AndWarnsOnce()
        {
            rules.Tick(500f, 0f, false);
            Assert.False(state.spoilStarted, "closed and alive: nothing spoils");
            Assert.AreEqual(0, Damage());
            Open();
            Assert.True(state.zoneOpened); Assert.True(state.alive);
            Assert.True(state.spoilStarted); Assert.AreEqual(OperationRules.SpoilByOpening, state.spoilCause);
            Assert.AreEqual(1, Count(PatientCue.SpoilageStarted), "one warning cue with the first opening");
            rules.Tick(84.99f, 0f, false);
            Assert.AreEqual(0, Damage(), "84.99 s: still inside grace + the first step");
            rules.Tick(0.02f, 0f, false);
            foreach (var o in state.organs) Assert.AreEqual(1, o.damage, "85 s: every remaining organ −1, alive or not");
            Assert.True(state.alive);
            rules.Tick(40f, 0f, false);
            Assert.AreEqual(2, Damage(), "125 s");
            rules.Tick(40f, 0f, false);
            Assert.AreEqual(3, Damage(), "165 s");
            Assert.AreEqual(1, Count(PatientCue.SpoilageStarted));
        }

        [Test] public void DeathAfterOpening_DoesNotRestartTheClock()
        {
            Open();
            rules.Tick(60f, 0f, false);
            rules.Die(DeathCause.Extraction);
            rules.Tick(25.01f, 0f, false);
            Assert.AreEqual(1, Damage(), "85 s after the OPENING, not 25 s after death");
            Assert.AreEqual(OperationRules.SpoilByOpening, state.spoilCause);
        }

        [Test] public void DeathBeforeOpening_StartsIt_TheLaterOpeningDoesNotRestart()
        {
            rules.Die(DeathCause.Blood);
            Assert.True(state.spoilStarted); Assert.AreEqual(OperationRules.SpoilByDeath, state.spoilCause);
            Assert.AreEqual(0, Count(PatientCue.SpoilageStarted), "death has its own cue; the warning is the opening's");
            rules.Tick(70f, 0f, false);
            Open();
            Assert.AreEqual(0, Count(PatientCue.SpoilageStarted), "already running: no second start");
            rules.Tick(15.01f, 0f, false);
            Assert.AreEqual(1, Damage(), "85 s after death");
        }

        [Test] public void SutureReopenAndLoad_NeitherRestartNorDouble()
        {
            Open();
            rules.Tick(50f, 0f, false);
            SewAll(); Assert.True(state.sutured);
            rules.Tick(10f, 0f, false);
            Reopen(); Assert.True(state.CavityOpen);
            Assert.AreEqual(1, Count(PatientCue.SpoilageStarted), "the reopening is not a first opening");
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.True(loaded.spoilStarted); Assert.AreEqual(60f, loaded.spoilAge, 0.001f, "the clock is saved");
            state = loaded; Bind(state); // a new table / a load builds new rules over the same state
            rules.Tick(24.99f, 0f, false);
            Assert.AreEqual(0, Damage(), "84.99 s in total");
            rules.Tick(0.02f, 0f, false);
            Assert.AreEqual(1, Damage(), "exactly one step at 85 s, not two");
            Assert.AreEqual(1, state.corpseLoss);
        }

        [Test] public void RemovedOrgans_KeepTheirGrade()
        {
            Open();
            var kidney = state.organs[0];
            for (int c = 0; c < kidney.connections.Length; c++) kidney.connections[c] = 1f;
            kidney.pull = tuning.pullDistance;
            Assert.True(rules.Extract(0, 0.99f));
            int grade = kidney.Grade;
            rules.Tick(200f, 0f, false);
            Assert.AreEqual(grade, kidney.Grade, "an extracted organ is not spoiled by the body clock");
            Assert.Greater(state.organs[1].damage, 0);
        }

        [Test] public void OldSave_DeadBody_ContinuesFromItsDeathClock()
        {
            state.alive = false; state.deathAge = 100f; state.corpseLoss = 1;
            foreach (var o in state.organs) o.damage = 1;
            Bind(state);
            Assert.True(state.spoilStarted); Assert.AreEqual(100f, state.spoilAge, 0.001f);
            Assert.AreEqual(0, Count(PatientCue.SpoilageStarted), "a migration warns nobody");
            rules.Tick(25.01f, 0f, false);
            Assert.AreEqual(2, Damage(), "125 s: one more step, the old one is not applied twice");
        }

        [Test] public void OldSave_LivingOpenedPatient_StartsAtTheLoad()
        {
            state.zoneOpened = true; state.zoneCut = 1f; foreach (var o in state.organs) o.cut = 1f;
            Bind(state);
            Assert.True(state.spoilStarted); Assert.AreEqual(0f, state.spoilAge);
            Assert.AreEqual(0, Count(PatientCue.SpoilageStarted));
        }

        // ---------- suture kit / patch ----------

        [Test] public void OneSutureKitPerClosure_ReservedOverInterruptionsAndLoads()
        {
            var stock = new Stock(); stock.Count[OperationSupplies.SutureKitId] = 2;
            rules.Supplies = stock;
            Open();
            Assert.False(state.sutureKitReserved);
            rules.Suture(0.2f, 0f, 0.5f); // a first stroke, then the players let go
            Assert.True(state.sutureKitReserved); Assert.AreEqual(1, stock.Taken);
            Assert.Less(state.zoneSuture, 1f);
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            Assert.True(loaded.sutureKitReserved, "the reservation is saved");
            state = loaded; Bind(state); rules.Supplies = stock;
            SewAll(); // resumed (another player or after the load): the same kit
            Assert.True(state.sutured); Assert.AreEqual(1, stock.Taken, "no second kit for the same closure");
            Reopen(); Assert.False(state.sutureKitReserved, "a reopened belly needs a new kit");
            SewAll(); Assert.True(state.sutured); Assert.AreEqual(2, stock.Taken);
        }

        [Test] public void NoSutureKit_NoStitch()
        {
            var stock = new Stock();
            rules.Supplies = stock;
            Open();
            Assert.AreEqual(CutStep.NoSupply, rules.Suture(0.2f, 0f, 0.5f));
            Assert.AreEqual(0f, state.zoneSuture); Assert.False(state.sutureKitReserved);
            Assert.True(rules.MustSutureBeforeRelease, "still open: the living patient stays strapped");
            stock.Count[OperationSupplies.SutureKitId] = 1;
            Assert.AreEqual(CutStep.Advanced, rules.Suture(0.2f, 0f, 0.5f));
        }

        [Test] public void APatchIsConsumedOnce_NoneLeavesTheBodyOpen()
        {
            var stock = new Stock(); stock.Count[OperationSupplies.PatchId] = 1;
            rules.Supplies = stock;
            Open(); rules.Die(DeathCause.Extraction);
            Assert.True(rules.PatchIfOpen()); Assert.True(state.skinPatched); Assert.AreEqual(1, stock.Taken);
            Assert.False(rules.PatchIfOpen(), "already patched: nothing more taken"); Assert.AreEqual(1, stock.Taken);
            var other = OperationRules.Create("other", tuning); var otherRules = new OperationRules(other, tuning) { Supplies = stock };
            other.onTable = other.aligned = true;
            for (int i = 1; i <= 40; i++) otherRules.CutSharedGuide(3, i / 40f, 0f, 0.04f);
            otherRules.Die(DeathCause.Extraction);
            Assert.False(otherRules.PatchIfOpen(), "no patch left"); Assert.False(other.skinPatched); Assert.True(other.CavityOpen);
        }

        [Test] public void WithoutASupplySource_ClosingIsNotGated()
        {
            Open(); SewAll();
            Assert.True(state.sutured, "rules without a supply source (tests, dev scenes) sew as before");
        }
    }
}
