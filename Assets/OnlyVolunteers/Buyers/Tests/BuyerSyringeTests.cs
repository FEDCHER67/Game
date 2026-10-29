using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class BuyerSyringeTests : BuyerTestSupport
    {
        [Test] public void RepeatSyringeAfterSnapshotReloadHasEightDollarsAndNoNewBonus()
        {
            Meeting(Blood); Sell(ProductKind.IntroSyringe, Blood);
            rules = Reload(rules.Snapshot);
            var second = Sell(ProductKind.IntroSyringe, Blood);
            Assert.AreEqual(8, second.Total); Assert.AreEqual(5, second.XpEach);
        }
        [Test] public void PortionCannotSellAsSyringeThenBagWithDifferentMerchandiseIds()
        {
            Meeting(Blood); Group(ProductKind.IntroSyringe, Blood);
            Assert.True(rules.RegisterItem(new BuyerItemState { Id = "syringe-content", HolderId = "p1", Kind = ProductKind.IntroSyringe,
                BloodPortionId = "npc/blood/1", SyringeItemId = "same-physical-item" }));
            rules.LoadItem(Blood, "syringe-content", "p1"); Assert.True(rules.ConfirmSale(Request(new[] { "syringe-content" }, Blood)).Success);
            Group(ProductKind.BloodBag, Blood);
            Assert.True(rules.RegisterItem(new BuyerItemState { Id = "forged-bag", HolderId = "p1", Kind = ProductKind.BloodBag, BloodPortionId = "npc/blood/1" }));
            rules.LoadItem(Blood, "forged-bag", "p1");
            Assert.AreEqual(SaleError.AlreadySold, rules.ConfirmSale(Request(new[] { "forged-bag" }, Blood)).Error);
        }
    }
}
