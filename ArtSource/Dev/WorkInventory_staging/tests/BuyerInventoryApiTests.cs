using System;
using System.Linq;
using System.Threading.Tasks;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using OnlyVolunteers.Buyers.Tests;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Tests
{
    public sealed class BuyerInventoryApiTests : BuyerTestSupport
    {
        [Test]
        public void TeamItemsRegisterWithoutInventingParticipants()
        {
            var item = new BuyerItemState { Id = "team-kidney", Kind = ProductKind.Kidney, Quality = QualityTier.Good };
            Assert.That(rules.RegisterTeamItem(item), Is.True); Assert.That(I(item.Id).HolderId, Is.EqualTo(BuyerRules.TeamHolderId));
            Assert.That(rules.Snapshot.Participants.Count, Is.EqualTo(2)); Assert.That(item.HolderId, Is.Empty);
            Assert.That(rules.RegisterTeamItem(item), Is.False);
        }
        [Test]
        public void TeamIdentityCannotBeParticipantOrLoadRemotely()
        {
            Assert.Throws<ArgumentException>(() => rules.SetPresentParticipants(BuyerRules.TeamHolderId));
            Assert.That(rules.RegisterTeamItem(new BuyerItemState { Id = "team", Kind = ProductKind.Kidney }), Is.True); Meeting();
            Assert.That(rules.LoadItem(Organ, "team", BuyerRules.TeamHolderId), Is.False);
            Assert.That(rules.SetItemHolder("team", "p2"), Is.True); Assert.That(rules.LoadItem(Organ, "team", "p2"), Is.True);
        }
        [Test]
        public void TeammateUnloadsWithoutResettingNegotiation()
        {
            Meeting(); string id = Add(); rules.LoadItem(Organ, id, "p1"); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99;
            rules.AskMeeting(Organ, "p1", 20); var before = B().Meeting.Negotiations.Single().Copy();
            Assert.That(rules.UnloadItem(Organ, id, "p2"), Is.True); Assert.That(I(id).HolderId, Is.EqualTo("p2")); Assert.That(I(id).MeetingId, Is.Empty);
            Assert.That(I(id).DeliveredCooled, Is.False); Assert.That(B().Meeting.Negotiations.Single().AttemptsUsed, Is.EqualTo(before.AttemptsUsed));
            Assert.That(B().Meeting.Negotiations.Single().CounterPercent, Is.EqualTo(before.CounterPercent));
        }
        [Test]
        public void UnloadFirstPreventsSaleWithoutRewardsOrPenalty()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); int respect = B().Respect;
            Assert.That(rules.UnloadItem(Organ, id), Is.True); var sale = rules.ConfirmSale(Request(new[] { id }));
            Assert.That(sale.Error, Is.EqualTo(SaleError.NotReserved)); Assert.That(rules.Snapshot.SharedFunds, Is.Zero); Assert.That(B().Respect, Is.EqualTo(respect));
        }
        [Test]
        public void SaleFirstPreventsUnloadRemovalAndResurrection()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); Assert.That(rules.ConfirmSale(Request(new[] { id })).Success, Is.True);
            Assert.That(rules.UnloadItem(Organ, id, "p2"), Is.False); Assert.That(rules.RemoveItem(id), Is.False);
            Assert.That(rules.SetDeliveredCooled(id, false), Is.False); Assert.That(rules.SetItemHolder(id, "p2"), Is.False);
            Assert.That(rules.RegisterTeamItem(new BuyerItemState { Id = id, Kind = ProductKind.Kidney }), Is.False);
        }
        [Test]
        public void ConcurrentSaleAndUnloadHaveOneWinner()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); var request = Request(new[] { id });
            bool unload = false; SaleResult sale = null;
            Parallel.Invoke(() => unload = rules.UnloadItem(Organ, id, "p2"), () => sale = rules.ConfirmSale(request));
            Assert.That((unload ? 1 : 0) + (sale.Success ? 1 : 0), Is.EqualTo(1));
            Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(sale.Success ? sale.Total : 0));
        }
        [TestCase(false, 225)]
        [TestCase(true, 250)]
        public void LoadReportsActualDeliveryLatch(bool cooled, int expected)
        {
            Meeting(); Group(); string id = Add(cooled:!cooled);
            Assert.That(rules.LoadItem(Organ, id, "p1", cooled, out var error), Is.True); Assert.That(error, Is.EqualTo(SaleError.None));
            Assert.That(rules.Quote(Request(new[] { id })).Total, Is.EqualTo(expected));
        }
        [Test]
        public void UpdatingLatchRefreshesQuoteAndPriceGuard()
        {
            Meeting(); Group(); string id = Add(cooled:false); rules.LoadItem(Organ, id, "p1"); var request = Request(new[] { id }); request.ExpectedTotal = 225;
            Assert.That(rules.SetDeliveredCooled(id, true), Is.True); Assert.That(rules.ConfirmSale(request).Error, Is.EqualTo(SaleError.PriceChanged)); Assert.That(I(id).Sold, Is.False);
        }
        [Test]
        public void FailedLoadDoesNotChangeLatch()
        {
            Meeting(); string id = Add(cooled:false);
            Assert.That(rules.LoadItem(Organ, id, "p2", true, out _), Is.False); Assert.That(I(id).DeliveredCooled, Is.False);
        }
        [Test]
        public void RemovedItemHasPersistentTombstone()
        {
            string id = Add(); var merchandise = I(id); Assert.That(rules.RemoveItem(id), Is.True); Assert.That(rules.RemoveItem(id), Is.False);
            Assert.That(rules.RegisterItem(merchandise), Is.False); Assert.That(rules.RegisterTeamItem(merchandise), Is.False);
            var save = InventoryJson.Read<BuyerWorldState>(InventoryJson.Write(rules.Snapshot)); rules = new BuyerRules(clock, rng, save);
            Assert.That(rules.RegisterTeamItem(merchandise), Is.False); Assert.That(rules.Snapshot.SharedFunds, Is.Zero);
        }
        [Test]
        public void RemovingReservedItemInvalidatesSaleWithoutRespectCost()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); int respect = B().Respect;
            rules.RemoveItem(id); Assert.That(rules.ConfirmSale(Request(new[] { id })).Error, Is.EqualTo(SaleError.MissingItem)); Assert.That(B().Respect, Is.EqualTo(respect));
        }
        [TestCase("missing")]
        [TestCase("p-absent")]
        public void UnloadRejectsUnknownRecipient(string recipient)
        {
            Meeting(); string id = Add(); rules.LoadItem(Organ, id, "p1"); Assert.That(rules.UnloadItem(Organ, id, recipient), Is.False); Assert.That(I(id).MeetingId, Is.Not.Empty);
        }
        [Test]
        public void HolderChangesRequireUnreservedLiveItems()
        {
            Meeting(); string id = Add(); rules.LoadItem(Organ, id, "p1"); Assert.That(rules.SetItemHolder(id, "p2"), Is.False);
            rules.UnloadItem(Organ, id); Assert.That(rules.SetItemHolder(id, "p2"), Is.True); Assert.That(rules.SetItemHolder(id, "unknown"), Is.False);
        }
        [Test]
        public void PackagingUpdateMakesExistingOrderProjectionEligible()
        {
            Respect40(); Order(); string id = Add(tier:QualityTier.Good, packaged:false);
            Assert.That(rules.PreviewOrderItem(id), Is.EqualTo(SaleError.PackagingRequired)); Assert.That(rules.SetPackaged(id, true), Is.True); Assert.That(rules.PreviewOrderItem(id), Is.EqualTo(SaleError.None));
        }
        [Test]
        public void BloodIgnoresCoolingApi()
        {
            string id = Add(ProductKind.BloodBag); Assert.That(rules.SetDeliveredCooled(id, true), Is.False); Assert.That(rules.SetPackaged(id, true), Is.False);
        }
    }
}
