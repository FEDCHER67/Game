using NUnit.Framework;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>Pure DonorBudget rules (no Unity objects: also run outside the editor).</summary>
    public sealed class OperationDonorBudgetRulesTests
    {
        [Test] public void OrdinaryDonorIsNeverLimited()
        {
            var b = new DonorBudget();
            Assert.False(DonorBudgetRules.LimitsToOne(b));
            Assert.True(DonorBudgetRules.Allows(b, DonorExtraction.Blood)); Assert.True(DonorBudgetRules.Allows(b, DonorExtraction.Organ));
            Assert.False(DonorBudgetRules.TrySpend(b, DonorExtraction.Blood, "x/blood/1"), "nothing to spend for an ordinary donor");
            Assert.AreEqual("", b.spentOn);
            Assert.True(DonorBudgetRules.Allows(null, DonorExtraction.Organ), "an old save without the block = ordinary");
        }

        [Test] public void MarkingNeedsProvenanceAndAnUntouchedDonor()
        {
            Assert.False(DonorBudgetRules.MarkSevereDrugIntoxication(new DonorBudget(), " ", 0, 0));
            Assert.False(DonorBudgetRules.MarkSevereDrugIntoxication(new DonorBudget(), "authored:test", 1, 0), "not after a blood portion");
            Assert.False(DonorBudgetRules.MarkSevereDrugIntoxication(new DonorBudget(), "authored:test", 0, 1), "not after an organ");
            var b = new DonorBudget();
            Assert.True(DonorBudgetRules.MarkSevereDrugIntoxication(b, " authored:Forest/WagonAddict01 ", 0, 0));
            Assert.AreEqual("authored:Forest/WagonAddict01", b.conditionSource);
            Assert.True(DonorBudgetRules.MarkSevereDrugIntoxication(b, "authored:again", 0, 0), "a repeat is harmless");
            Assert.AreEqual("authored:Forest/WagonAddict01", b.conditionSource, "the first provenance stands");
        }

        [Test] public void OneSharedExtractionForBloodOrOrgan()
        {
            var b = new DonorBudget();
            DonorBudgetRules.MarkSevereDrugIntoxication(b, "authored:test", 0, 0);
            Assert.True(DonorBudgetRules.Allows(b, DonorExtraction.Blood));
            Assert.True(DonorBudgetRules.TrySpend(b, DonorExtraction.Organ, "p/organ/0"));
            Assert.True(b.Exhausted); Assert.AreEqual("organ:p/organ/0", b.spentOn);
            Assert.False(DonorBudgetRules.Allows(b, DonorExtraction.Blood), "the organ used the blood allowance too");
            Assert.False(DonorBudgetRules.Allows(b, DonorExtraction.Organ));
            Assert.False(DonorBudgetRules.TrySpend(b, DonorExtraction.Blood, "p/blood/1"), "a concurrent request finds it spent");
            Assert.AreEqual("organ:p/organ/0", b.spentOn);
        }

        [Test] public void MarkingIsRefusedOnceSpent()
        {
            var b = new DonorBudget { spentOn = "blood:p/blood/1" };
            Assert.False(DonorBudgetRules.MarkSevereDrugIntoxication(b, "authored:test", 0, 0));
        }
    }
}
