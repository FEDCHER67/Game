using NUnit.Framework;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>Stage A rules (CAPTURE_DELIVERY_SPEC v01): organ grades by district / type / condition (CD-07), the field
    /// blood rule (CD-05), the tie rows (CD-06), the condition loss applied once at extraction and the field portions in the
    /// extraction death chance (CD-04), the field overdose (CD-03, the unchanged operation dose rules).</summary>
    public sealed class CaptureRulesTests
    {
        private static OperationTuning Tuning()
        {
            var t = ScriptableObject.CreateInstance<OperationTuning>();
            t.sharedAbdomen = false;
            return t;
        }

        [TestCase("village", CaptureGrades.Row.Hamlet)]
        [TestCase("transition", CaptureGrades.Row.Hamlet)]
        [TestCase("industrial", CaptureGrades.Row.Hamlet)]
        [TestCase("forest", CaptureGrades.Row.Rough)]
        [TestCase("residential", CaptureGrades.Row.Rough)]
        [TestCase("old_town", CaptureGrades.Row.Downtown)]
        [TestCase("beach", CaptureGrades.Row.Downtown)]
        [TestCase("elite", CaptureGrades.Row.Elite)]
        [TestCase("fields", CaptureGrades.Row.Elite)]
        [TestCase("tramduro", CaptureGrades.Row.Tramduro)]
        [TestCase("nowhere", CaptureGrades.Row.Hamlet)]
        public void DistrictRows(string district, CaptureGrades.Row row) => Assert.AreEqual(row, CaptureGrades.RowFor(district));

        /// <summary>CD-07: over ≥1,000 seeded identities each row's grades match the table within ±5 %.</summary>
        [TestCase("forest")]
        [TestCase("village")]
        [TestCase("old_town")]
        [TestCase("elite")]
        [TestCase("tramduro")]
        public void IntrinsicGradesFollowTheDistrictTable(string district)
        {
            const int identities = 2000;
            var counts = new int[5];
            for (int i = 0; i < identities; i++)
                foreach (int g in CaptureGrades.RollIntrinsic("P-roll-" + district + "-" + i, district, "SAUSAGE_BUDDY_A")) counts[g]++;
            float[] want = CaptureGrades.Weights(CaptureGrades.RowFor(district));
            int total = identities * CaptureGrades.Organs;
            for (int g = 0; g < 5; g++)
            {
                float share = counts[g] / (float)total;
                Assert.That(Mathf.Abs(share - want[g]), Is.LessThanOrEqualTo(0.05f), $"{district} grade {g}: {share:P1} vs {want[g]:P0}");
            }
        }

        [Test]
        public void SameIdentityAlwaysRollsTheSameGrades()
        {
            for (int i = 0; i < 50; i++)
            {
                string id = "P-" + i.ToString("x10");
                CollectionAssert.AreEqual(CaptureGrades.RollIntrinsic(id, "village", "SAUSAGE_BUDDY_B"), CaptureGrades.RollIntrinsic(id, "village", "SAUSAGE_BUDDY_B"));
            }
        }

        [Test]
        public void TypeShiftsApplyAndClamp()
        {
            for (int i = 0; i < 200; i++)
            {
                string id = "P-shift-" + i;
                int[] plain = CaptureGrades.RollIntrinsic(id, "village", "SAUSAGE_BUDDY_A");
                int[] junkie = CaptureGrades.RollIntrinsic(id, "village", "FOREST_OD_JUNKIE");
                int[] drunk = CaptureGrades.RollIntrinsic(id, "village", "BAD_DRUNK");
                int[] gym = CaptureGrades.RollIntrinsic(id, "village", "HAMLET_BODYBUILDER");
                int[] granny = CaptureGrades.RollIntrinsic(id, "village", "HAMLET_GRANNY");
                Assert.AreEqual(Mathf.Max(0, plain[2] - 1), junkie[2], "junkie: liver -1");
                Assert.AreEqual(plain[0], junkie[0], "junkie: kidneys unchanged");
                Assert.AreEqual(Mathf.Max(0, plain[2] - 1), drunk[2], "drunk: liver -1");
                Assert.AreEqual(Mathf.Min(4, plain[0] + 1), gym[0], "bodybuilder: kidney +1");
                Assert.AreEqual(Mathf.Min(4, plain[1] + 1), gym[1], "bodybuilder: kidney +1");
                Assert.AreEqual(plain[2], gym[2], "bodybuilder: liver unchanged");
                for (int o = 0; o < 3; o++) Assert.AreEqual(Mathf.Max(0, plain[o] - 1), granny[o], "granny: every organ -1");
            }
            Assert.AreEqual(-1, CaptureGrades.LungShift("BAD_VAPER"));
            Assert.AreEqual(1, CaptureGrades.LungShift("HAMLET_BODYBUILDER"));
        }

        [TestCase(100f, 0)] [TestCase(75f, 0)] [TestCase(74.9f, 1)] [TestCase(60f, 1)] [TestCase(50f, 1)]
        [TestCase(49.9f, 2)] [TestCase(25f, 2)] [TestCase(24.9f, 3)] [TestCase(0f, 3)]
        public void ConditionLossTiers(float condition, int loss) => Assert.AreEqual(loss, CaptureGrades.ConditionLoss(condition));

        private static void ReadyToExtract(OperationState s, int organ, OperationTuning t)
        {
            var o = s.organs[organ];
            o.cut = 1f;
            for (int c = 0; c < o.connections.Length; c++) o.connections[c] = 1f;
            o.pull = t.pullDistance;
        }

        /// <summary>CD-07: condition 60 removes exactly one grade, at extraction, once per organ, floored at «Убитое».</summary>
        [Test]
        public void ConditionLossLandsAtExtractionOnce()
        {
            var t = Tuning();
            var s = OperationRules.Create("P-cond", t);
            CaptureGrades.Apply(s, new[] { 2, 0, 3 });
            s.conditionLoss = CaptureGrades.ConditionLoss(60f);
            var rules = new OperationRules(s, t);
            Assert.AreEqual(2, s.organs[0].Grade, "before extraction the grade is untouched");
            ReadyToExtract(s, 0, t);
            Assert.IsTrue(rules.Extract(0, 0.99f));
            Assert.AreEqual(1, s.organs[0].Grade, "Хорошее -> Сойдёт at extraction");
            Assert.AreEqual(3, s.organs[2].Grade, "the liver still in the body keeps its grade");
            ReadyToExtract(s, 1, t);
            Assert.IsTrue(rules.Extract(1, 0.99f));
            Assert.AreEqual(0, s.organs[1].Grade, "floored at Убитое");
            Assert.IsFalse(rules.Extract(0, 0.99f), "an organ comes out (and loses) only once");
            Assert.AreEqual(1, s.organs[0].Grade);
        }

        /// <summary>CD-04: two portions drawn in the field: the first kidney's death chance is 30 %.</summary>
        [Test]
        public void FieldBloodCountsInTheExtractionDeathChance()
        {
            var t = Tuning();
            var s = OperationRules.Create("P-blood", t);
            var rules = new OperationRules(s, t);
            rules.Tick(0.02f, t.suitableMinimum, false); // asleep
            float fill = 0f;
            Assert.IsTrue(rules.FillBlood(ref fill, t.bloodSeconds + 0.01f));
            fill = 0f;
            Assert.IsTrue(rules.FillBlood(ref fill, t.bloodSeconds + 0.01f));
            Assert.AreEqual(2, s.bloodPortions);
            Assert.IsTrue(s.alive, "two portions weaken, they do not kill");
            ReadyToExtract(s, 0, t);
            Assert.IsTrue(rules.Extract(0, 0.99f));
            Assert.AreEqual(0.3f, s.organs[0].deathChance, 1e-4f);
        }

        /// <summary>CD-03: the same overdose line in the field.</summary>
        [Test]
        public void FieldOverdoseKills()
        {
            var t = Tuning();
            var s = OperationRules.Create("P-od", t);
            var rules = new OperationRules(s, t);
            for (int i = 0; i < 300 && s.alive; i++) rules.Tick(0.02f, t.dosePerSecond * 0.02f, false);
            Assert.IsFalse(s.alive);
            Assert.AreEqual(DeathCause.Overdose, s.deathCause);
        }

        /// <summary>CD-05: no blood from an awake, unrestrained NPC or a corpse; yes when asleep, out cold or hands tied.</summary>
        [Test]
        public void FieldBloodRule()
        {
            var t = Tuning();
            var s = OperationRules.Create("P-b", t);
            var none = new Restraints();
            Assert.AreEqual(FieldRefusal.Squirming, CaptureRules.CanDrawBlood(s, false, none, t.fatalPortion));
            Assert.AreEqual(FieldRefusal.None, CaptureRules.CanDrawBlood(s, true, none, t.fatalPortion), "knocked out cold");
            Assert.AreEqual(FieldRefusal.None, CaptureRules.CanDrawBlood(s, false, new Restraints { hands = true }, t.fatalPortion), "hands tied");
            Assert.AreEqual(FieldRefusal.Squirming, CaptureRules.CanDrawBlood(s, false, new Restraints { feet = true }, t.fatalPortion), "feet alone do not hold an arm still");
            s.sleepRemaining = 10f;
            Assert.AreEqual(FieldRefusal.None, CaptureRules.CanDrawBlood(s, false, none, t.fatalPortion), "asleep");
            s.bloodPortions = t.fatalPortion;
            Assert.AreEqual(FieldRefusal.NoBloodLeft, CaptureRules.CanDrawBlood(s, false, none, t.fatalPortion));
            s.bloodPortions = 0;
            new OperationRules(s, t).Die(DeathCause.Overdose);
            Assert.AreEqual(FieldRefusal.Dead, CaptureRules.CanDrawBlood(s, true, new Restraints { hands = true }, t.fatalPortion));
        }

        /// <summary>CD-06 rows and the strap that cuts each tie.</summary>
        [Test]
        public void TieRows()
        {
            var none = new Restraints();
            var hands = new Restraints { hands = true };
            var feet = new Restraints { feet = true };
            var both = new Restraints { hands = true, feet = true };
            Assert.IsTrue(CaptureRules.CanUseHands(none) && CaptureRules.CanUseHands(feet));
            Assert.IsFalse(CaptureRules.CanUseHands(hands) || CaptureRules.CanUseHands(both));
            Assert.IsFalse(CaptureRules.StaysDown(none) || CaptureRules.StaysDown(hands));
            Assert.IsTrue(CaptureRules.StaysDown(feet) && CaptureRules.StaysDown(both), "feet tied: no running");
            Assert.IsTrue(CaptureRules.CanLeaveVanAlone(hands) && CaptureRules.CanLeaveVanAlone(feet));
            Assert.IsFalse(CaptureRules.CanLeaveVanAlone(both), "both: cannot leave the van alone");
            Assert.AreEqual(1f, CaptureRules.CarryResistance(feet));
            Assert.AreEqual(0.7f, CaptureRules.CarryResistance(both), 1e-6f);
            Assert.AreEqual(TieTarget.Feet, CaptureRules.ChooseTie(none, TieTarget.Feet));
            Assert.AreEqual(TieTarget.Hands, CaptureRules.ChooseTie(none, TieTarget.None));
            Assert.AreEqual(TieTarget.Feet, CaptureRules.ChooseTie(hands, TieTarget.Hands), "the hands are taken: the feet next");
            Assert.AreEqual(TieTarget.None, CaptureRules.ChooseTie(both, TieTarget.Hands));
            var straps = new bool[5];
            straps[1] = true;
            var after = CaptureRules.AfterStraps(both, straps);
            Assert.IsFalse(after.hands); Assert.IsTrue(after.feet);
            straps[3] = true;
            after = CaptureRules.AfterStraps(both, straps);
            Assert.IsFalse(after.Any);
        }
    }
}
