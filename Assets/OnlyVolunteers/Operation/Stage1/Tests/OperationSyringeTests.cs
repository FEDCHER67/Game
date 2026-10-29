using NUnit.Framework;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    public sealed class OperationSyringeTests
    {
        private OperationTuning tuning;
        private OperationState patient;
        private OperationRules rules;
        [SetUp] public void SetUp()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>();
            patient = OperationRules.Create("npc-a", tuning); patient.onTable = patient.aligned = true;
            patient.restraints[0] = true; rules = new OperationRules(patient, tuning);
        }
        [TearDown] public void TearDown() { Object.DestroyImmediate(tuning); }
        [Test] public void CancelledDrawBindsNobodyAndDoesNotIncrementCounter()
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            rules.FillSyringe(s, 1, true, out bool completed); Assert.False(completed); Assert.IsEmpty(s.PersonId);
            SyringeRules.CancelDraw(s); Assert.AreEqual(0, patient.bloodPortions); Assert.AreEqual(0, s.Fill);
        }
        [Test] public void RefusalHappensBeforeExistingDrawAndLeavesCounterAndFillIntact()
        {
            var s = SyringeInstance.New(SyringeKind.Blood); s.PersonId = "another";
            Assert.AreEqual(SyringeUseResult.OtherPerson, rules.FillSyringe(s, 100, true, out bool done));
            Assert.False(done); Assert.AreEqual(0, patient.bloodPortions); Assert.AreEqual(0, s.Fill);
        }
        [Test] public void SameNpcKeepsCounterTwoLivingPortionsThirdFatalNoFourth()
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            for (int i = 1; i <= 3; i++)
            {
                Assert.AreEqual(SyringeUseResult.Success, rules.FillSyringe(s, tuning.bloodSeconds, true, out bool done));
                Assert.True(done); Assert.AreEqual(i, patient.bloodPortions); Assert.AreEqual(i < 3, patient.alive);
                Assert.AreEqual("npc-a", s.PersonId); Assert.AreEqual("npc-a/blood/" + i, s.Portion.Id); SyringeRules.Empty(s);
            }
            Assert.AreEqual(SyringeUseResult.InvalidTarget, rules.FillSyringe(s, 100, true, out _)); Assert.AreEqual(3, patient.bloodPortions);
        }
        [Test] public void CorpseRejectedAtBothOldAndNewEntryPoints()
        {
            patient.alive = false; float fill = 0;
            Assert.False(rules.CanDrawBlood(0)); Assert.False(rules.FillBlood(ref fill, 100)); Assert.AreEqual(0, fill);
            Assert.AreEqual(SyringeUseResult.InvalidTarget, rules.FillSyringe(SyringeInstance.New(SyringeKind.Blood), 100, true, out _));
            Assert.AreEqual(0, patient.bloodPortions);
        }
        [Test] public void DoseRefusedBeforeConsumptionAndFirstActualDoseBinds()
        {
            var s = SyringeInstance.New(SyringeKind.Anaesthesia);
            Assert.AreEqual(SyringeUseResult.Failed, rules.DoseSyringe(s, 0, true, out _)); Assert.IsEmpty(s.PersonId);
            Assert.AreEqual(SyringeUseResult.Success, rules.DoseSyringe(s, .1f, true, out float dose)); Assert.AreEqual(.1f, dose);
            patient.patientId = "npc-b";
            Assert.AreEqual(SyringeUseResult.OtherPerson, rules.DoseSyringe(s, .1f, true, out dose)); Assert.AreEqual(0, dose);
        }
        [Test] public void OperationSaveRoundTripPreservesItemPersonAndPortionIds()
        {
            var s = SyringeInstance.New(SyringeKind.Blood); rules.FillSyringe(s, tuning.bloodSeconds, true, out _);
            var loaded = JsonUtility.FromJson<OperationWorldState>(JsonUtility.ToJson(new OperationWorldState { patient = patient, bloodSyringe = s }));
            Assert.AreEqual(s.ItemId, loaded.bloodSyringe.ItemId); Assert.AreEqual(s.PersonId, loaded.bloodSyringe.PersonId);
            Assert.AreEqual(s.Portion.Id, loaded.bloodSyringe.Portion.Id); Assert.AreEqual(1, loaded.patient.bloodPortions);
        }
    }
}
