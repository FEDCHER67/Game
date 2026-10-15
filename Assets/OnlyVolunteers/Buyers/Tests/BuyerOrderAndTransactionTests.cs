using System;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.Threading.Tasks;
using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class BuyerOrderAndTransactionTests : BuyerTestSupport
    {
        [Test]
        public void BUY26_BUY28_OrderAcceptedAfterNegotiationOneTeamSlotAndFortyEightHours()
        {
            Respect40(); string id = Add(tier: QualityTier.Good, packaged: true); Offer();
            Assert.That(rules.AcceptOrder("order", "p1"), Is.False); Assert.That(rules.Snapshot.ActiveOrder, Is.Null);
            clock.Now = 20000; rules.AcceptOrderPrice("order", "p1"); rules.AcceptOrder("order", "p1");
            var order = rules.Snapshot.ActiveOrder; Assert.That(order.AcceptedAt, Is.EqualTo(20000));
            Assert.That(order.Deadline, Is.EqualTo(20000 + 172800));
            Assert.That(order.SourceNpcId, Is.EqualTo("target"));
            Assert.That(rules.CreateOrderOffer("another", Organ, OrderTemplate.HamletKidney, "target2", "s2", "p2"), Is.False);
            Assert.That(rules.DepositInStash("order", id, "p1"), Is.True);
            Assert.That(rules.ConfirmSale(StashRequest(id)).Success, Is.True, "Organ obtained before acceptance is valid.");
        }
        [Test]
        public void BUY29_BUY47_SpecialMultipliersAreSequentialIgnoreSaturationAndAllowNoCooler()
        {
            Respect40(); Meeting(); Sell(count: 8); Order(20);
            string id = Deposit(cooled: false); var result = rules.ConfirmSale(StashRequest(id));
            Assert.That(result.Total, Is.EqualTo(540)); // 250 * 1.6 * 1.20 * 1.25 * .90
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).Units, Is.EqualTo(6));
            Assert.That(100m * 1.25m * 1.20m, Is.EqualTo(150m));
        }
        [Test]
        public void BUY30_FailedOrderNegotiationNoSlotOrDeadlineAndThreeHourOfferBan()
        {
            Respect40(); Offer(); rng.Value = 99; rules.AskOrder("order", "p1", 20); rules.AskOrder("order", "p1", 10);
            Assert.That(B().Respect, Is.EqualTo(39)); Assert.That(rules.Snapshot.ActiveOrder, Is.Null);
            Assert.That(rules.Snapshot.OpenStashes, Is.Empty);
            Assert.That(rules.ChangeOrderNegotiator("order", "p2"), Is.False);
            Assert.That(rules.CreateOrderOffer("bypass", Organ, OrderTemplate.HamletKidney, "target", "stash", "p1"), Is.False);
            clock.Now = 10799; Assert.That(rules.ChangeOrderNegotiator("order", "p2"), Is.False);
            clock.Now = 10800; Assert.That(rules.ChangeOrderNegotiator("order", "p2"), Is.True);
            Assert.That(rules.Snapshot.Offers[0].Negotiation.AttemptsUsed, Is.Zero);
            Assert.That(rules.AcceptOrder("order", "p2"), Is.False);
        }
        [Test]
        public void BUY22_BUY41_OrderHandoffPreservesTermsAttemptsAndUsesReplacementSkill()
        {
            var seed = Seed(40); seed.Participants[1].NegotiationLevel = 3; rules = new BuyerRules(clock, rng, seed);
            Offer(); rng.Value = 99; rules.AskOrder("order", "p1", 20); rules.SetPresentParticipants("p2");
            Assert.That(rules.ChangeOrderNegotiator("order", "p2"), Is.True);
            rng.Value = 64; rules.AskOrder("order", "p2", 10); // level 3 respect: 50 + 15 = 65
            Assert.That(rules.Snapshot.Offers[0].Negotiation.AttemptsUsed, Is.EqualTo(2));
            Assert.That(rules.Snapshot.Offers[0].Negotiation.AgreedPercent, Is.EqualTo(10));
            Assert.That(rules.AcceptOrder("order", "p2"), Is.True);
        }
        [Test]
        public void BUY31_BUY43_BUY53_OnTimeOrderStacksRespectOrganXpAnd150Each()
        {
            Respect40(); Order(); string id = Deposit(); clock.Now = rules.Snapshot.ActiveOrder.Deadline - 1;
            var result = rules.ConfirmSale(StashRequest(id));
            Assert.That(result.Total, Is.EqualTo(500)); Assert.That(result.XpEach, Is.EqualTo(270)); Assert.That(result.TeamXp, Is.EqualTo(540));
            Assert.That(B().Respect, Is.EqualTo(47)); Assert.That(rules.Snapshot.NextContactUnlocked, Is.True);
            Assert.That(rules.Snapshot.ActiveOrder, Is.Null);
        }
        [Test]
        public void BUY43_RepeatOrganSpecialStacksOnePlusFiveRespect()
        {
            Respect40(); Meeting(); Sell(); Order(); string id = Deposit(); int before = B().Respect;
            var result = rules.ConfirmSale(StashRequest(id)); Assert.That(B().Respect, Is.EqualTo(before + 6));
            Assert.That(result.XpEach, Is.EqualTo(170));
        }
        [Test]
        public void BUY32_BUY42_DeadlineAppliesMinusFourOnceKeepsSlotAndNegotiatedPercent()
        {
            Respect40(); Order(20); string id = Deposit(); long deadline = rules.Snapshot.ActiveOrder.Deadline;
            clock.Now = deadline; rules.Tick(); rules.Tick(); Assert.That(B().Respect, Is.EqualTo(36));
            Assert.That(rules.Snapshot.ActiveOrder, Is.Not.Null);
            Assert.That(rules.CreateOrderOffer("busy", Organ, OrderTemplate.HamletKidney, "target", "stash", "p1"), Is.False);
            var result = rules.ConfirmSale(StashRequest(id));
            Assert.That(result.Total, Is.EqualTo(480)); Assert.That(result.XpEach, Is.EqualTo(120));
            Assert.That(B().Respect, Is.EqualTo(38)); Assert.That(rules.Snapshot.NextContactUnlocked, Is.False);
        }
        [TestCase(false,38)] [TestCase(true,36)]
        public void BUY33_RefusalBeforeDeadlineMinusTwoAfterDeadlineNoExtraPenalty(bool late, int respect)
        {
            Respect40(); Order(); string id = Deposit();
            if (late) clock.Now = rules.Snapshot.ActiveOrder.Deadline;
            Assert.That(rules.RefuseOrder("order"), Is.True); Assert.That(rules.RefuseOrder("order"), Is.False);
            Assert.That(B().Respect, Is.EqualTo(respect)); Assert.That(rules.Snapshot.ActiveOrder, Is.Null);
            Assert.That(I(id).Sold, Is.False); Assert.That(I(id).StashOrderId, Is.Empty);
        }
        [Test]
        public void BUY34_StashOpensOnAcceptanceCanWithdrawUntilConfirmedThenPaysImmediately()
        {
            Respect40(); Offer(); string id = Add(tier: QualityTier.Good, packaged: true);
            Assert.That(rules.DepositInStash("order", id, "p1"), Is.False);
            rules.AcceptOrderPrice("order", "p1"); rules.AcceptOrder("order", "p1");
            Assert.That(rules.Snapshot.OpenStashes, Does.Contain("stash"));
            rules.DepositInStash("order", id, "p1"); Assert.That(rules.Snapshot.SharedFunds, Is.Zero);
            Assert.That(rules.WithdrawFromStash("order", id, "p1"), Is.True);
            Assert.That(rules.ConfirmSale(StashRequest(id)).Error, Is.EqualTo(SaleError.NotReserved));
            rules.DepositInStash("order", id, "p1"); Assert.That(rules.ConfirmSale(StashRequest(id)).Success, Is.True);
            Assert.That(I(id).Sold, Is.True); Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(500));
            Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(540));
            Assert.That(rules.WithdrawFromStash("order", id, "p1"), Is.False);
        }
        [TestCase("npc",SaleError.WrongNpc)] [TestCase("type",SaleError.WrongKind)]
        [TestCase("tier",SaleError.LowQuality)] [TestCase("pack",SaleError.PackagingRequired)]
        [TestCase("npc-type",SaleError.WrongNpc)]
        public void BUY26_BUY35_BUY48_WrongItemPreviewAndOnePenaltyPerInstance(string fault, SaleError expected)
        {
            Respect40(); Order(); string id = Deposit(tier: fault == "tier" ? QualityTier.Acceptable : QualityTier.Good,
                packaged: fault != "pack", npc: fault == "npc" ? "impostor" : "target",
                npcType: fault == "npc-type" ? "OTHER" : "HAMLET_BODYBUILDER", kind: fault == "type" ? ProductKind.Liver : ProductKind.Kidney);
            Assert.That(rules.PreviewOrderItem(id), Is.EqualTo(expected)); Assert.That(B().Respect, Is.EqualTo(40));
            var request = StashRequest(id); Assert.That(rules.Quote(request).Error, Is.EqualTo(expected)); Assert.That(B().Respect, Is.EqualTo(40));
            Assert.That(rules.ConfirmSale(request).Error, Is.EqualTo(expected)); rules.ConfirmSale(request); rules.ConfirmSale(StashRequest(id));
            Assert.That(B().Respect, Is.EqualTo(39)); Assert.That(I(id).Sold, Is.False);
            Assert.That(rules.Snapshot.SharedFunds, Is.Zero); Assert.That(rules.Snapshot.LifetimeXp, Is.Zero);
        }
        [Test]
        public void BUY48_PenaltyIsPerItemAndScopedToEachMeeting()
        {
            Meeting(); Group(); string a = Add(ProductKind.Liver), b = Add(ProductKind.Liver);
            rules.LoadItem(Organ, a, "p1"); rules.LoadItem(Organ, b, "p1");
            rules.ConfirmSale(Request(new[] { a })); rules.ConfirmSale(Request(new[] { a })); rules.ConfirmSale(Request(new[] { b }));
            Assert.That(B().Respect, Is.EqualTo(28));
            rules.CancelMeeting(Organ); Meeting(); Group(); rules.LoadItem(Organ, a, "p1");
            rules.ConfirmSale(Request(new[] { a })); Assert.That(B().Respect, Is.EqualTo(26));
        }
        [Test]
        public void BUY49_RespectDropDoesNotInvalidateAcceptedOrder()
        {
            Respect40(); Order(); Meeting(); rules.CancelMeeting(Organ); Assert.That(B().Respect, Is.EqualTo(39));
            string id = Deposit(); Assert.That(rules.ConfirmSale(StashRequest(id)).Success, Is.True);
        }
        [Test]
        public void BUY46_BestQualityFirstRegardlessOfLoadOrRequestOrder()
        {
            Meeting(); Group(); string low = Add(tier: QualityTier.Damaged), high = Add(tier: QualityTier.PerfectPlus);
            rules.LoadItem(Organ, low, "p1"); rules.LoadItem(Organ, high, "p1");
            Assert.That(rules.Quote(Request(new[] { low, high })).Total, Is.EqualTo(1121));
            Assert.That(rules.Quote(Request(new[] { high, low })).Total, Is.EqualTo(1121));
            var result = rules.ConfirmSale(Request(new[] { low, high })); Assert.That(result.SoldItemIds, Is.EqualTo(new[] { high, low }));
        }
        [TestCase(false,false)] [TestCase(true,false)] [TestCase(false,true)]
        public void BUY56_StreamerOfferNeedsSawAndDowntown(bool saw, bool downtown)
        {
            Respect40(); rules.SetProgression(saw, downtown);
            Assert.That(rules.CreateOrderOffer("streamer", Organ, OrderTemplate.StreamerBrain, "target", "stash", "p1"), Is.False);
        }
        [TestCase(QualityTier.Good,SaleError.LowQuality)] [TestCase(QualityTier.Perfect,SaleError.None)] [TestCase(QualityTier.PerfectPlus,SaleError.None)]
        public void BUY54_BUY56_StreamerRequiresPerfectTierAndCorrectNpc(QualityTier tier, SaleError expected)
        {
            Respect40(); rules.SetProgression(true, true); Order(template: OrderTemplate.StreamerBrain);
            string id = Deposit(tier, npcType: "OLD_STREAMER", kind: ProductKind.Brain);
            Assert.That(rules.PreviewOrderItem(id), Is.EqualTo(expected));
        }
        [Test]
        public void BUY37_ConcurrentConfirmationsWithSameIdPublishOnceAndReturnOriginalReceipt()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); var request = Request(new[] { id });
            var results = new SaleResult[32]; Parallel.For(0, results.Length, n => results[n] = rules.ConfirmSale(request));
            Assert.That(results.All(r => r.Success && r.Total == 250 && r.XpEach == 120), Is.True);
            Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(250)); Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(240));
            Assert.That(B().Respect, Is.EqualTo(32)); Assert.That(rules.Snapshot.Receipts.Count, Is.EqualTo(1));
            results[0].Total = 999; results[0].SoldItemIds.Clear(); Assert.That(rules.ConfirmSale(request).Total, Is.EqualTo(250));
        }
        [Test]
        public void BUY37_CompetingIdsAndInvalidBatchCannotPartiallySellOrReward()
        {
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1");
            var invalid = rules.ConfirmSale(Request(new[] { id, "missing" }));
            Assert.That(invalid.Error, Is.EqualTo(SaleError.MissingItem)); Assert.That(I(id).Sold, Is.False);
            Assert.That(rules.Snapshot.SharedFunds, Is.Zero); Assert.That(rules.Snapshot.FreeXp, Is.Zero);
            var requests = Enumerable.Range(0, 16).Select(_ => Request(new[] { id })).ToArray(); var results = new SaleResult[16];
            Parallel.For(0, 16, n => results[n] = rules.ConfirmSale(requests[n]));
            Assert.That(results.Count(r => r.Success), Is.EqualTo(1)); Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(250));
            Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(240));
        }
        [Test]
        public void BUY37_SoldIdentityCannotBeRegisteredOrSoldAgainInAnotherGroup()
        {
            Meeting(); var sold = Sell(); string id = sold.SoldItemIds[0];
            var duplicate = I(id); duplicate.Sold = false;
            Assert.That(rules.RegisterItem(duplicate), Is.False);
            Group(); Assert.That(rules.LoadItem(Organ, id, "p1"), Is.False);
            Assert.That(rules.ConfirmSale(Request(new[] { id })).Error, Is.EqualTo(SaleError.AlreadySold));
            Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(250)); Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(240));
        }
        [Test]
        public void BUY37_OverflowRollsBackAllSaleChangesAndNoReceiptIsPublished()
        {
            var seed = Seed(); seed.SharedFunds = decimal.MaxValue; rules = new BuyerRules(clock, rng, seed);
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1"); var req = Request(new[] { id });
            Assert.Throws<OverflowException>(() => rules.ConfirmSale(req));
            Assert.That(I(id).Sold, Is.False); Assert.That(rules.Snapshot.LifetimeXp, Is.Zero);
            Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(rules.Snapshot.Receipts, Is.Empty);
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).Units, Is.Zero);
        }
        [Test]
        public void BUY38_SavedBansNegotiationAttemptsAndWrongItemPenaltiesCannotReset()
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99;
            rules.AskMeeting(Organ, "p1", 20); rules.AskMeeting(Organ, "p1", 10);
            rules.BeginGroup(Organ, ProductKind.Liver, "p1"); rules.AskMeeting(Organ, "p1", 20);
            var saved = rules.Snapshot; rules = new BuyerRules(clock, rng, saved);
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).BannedUntil, Is.EqualTo(14400));
            Assert.That(B().Meeting.Negotiations.Single(n => n.Kind == ProductKind.Liver).AttemptsUsed, Is.EqualTo(1));
            Assert.That(rules.AskMeeting(Organ, "p1", 20), Is.False);
            rules.AcceptMeetingPrice(Organ, "p1"); string wrong = Add(); rules.LoadItem(Organ, wrong, "p1");
            rules.ConfirmSale(Request(new[] { wrong })); int respect = B().Respect;
            rules = new BuyerRules(clock, rng, rules.Snapshot); rules.ConfirmSale(Request(new[] { wrong }));
            Assert.That(B().Respect, Is.EqualTo(respect));
        }
        [Test]
        public void BUY38_SaveRoundTripRetainsRelationsContactsXpTimersSaturationOrdersAndReceipts()
        {
            Respect40(); rules.IntroduceBuyer(Organ); Meeting(); var sold = Sell();
            Order(10); string stash = Deposit(); var saved = rules.Snapshot;
            var serializer = new DataContractSerializer(typeof(BuyerWorldState)); BuyerWorldState loaded;
            using (var stream = new MemoryStream()) { serializer.WriteObject(stream, saved); stream.Position = 0; loaded = (BuyerWorldState)serializer.ReadObject(stream); }
            var resumedClock = new TestClock { Now = loaded.LastGameSeconds };
            var resumed = new BuyerRules(resumedClock, rng, loaded); var restored = resumed.Snapshot;
            Assert.That(restored.ActiveOrder.Deadline, Is.EqualTo(saved.ActiveOrder.Deadline));
            Assert.That(restored.Buyers[1].Meeting.ExpiresAt, Is.EqualTo(saved.Buyers[1].Meeting.ExpiresAt));
            Assert.That(restored.Buyers[1].Respect, Is.EqualTo(saved.Buyers[1].Respect));
            Assert.That(restored.Buyers[1].Introduced, Is.True); Assert.That(restored.OrganContactUnlocked, Is.True);
            Assert.That(restored.FirstOrganTypes, Is.EqualTo(saved.FirstOrganTypes)); Assert.That(restored.LifetimeXp, Is.EqualTo(saved.LifetimeXp));
            Assert.That(restored.FreeXp, Is.EqualTo(saved.FreeXp)); Assert.That(restored.SharedFunds, Is.EqualTo(saved.SharedFunds));
            Assert.That(restored.Participants.Select(p => p.PersonalXp), Is.EqualTo(saved.Participants.Select(p => p.PersonalXp)));
            Assert.That(restored.Buyers[1].Counters[0].Units, Is.EqualTo(1)); Assert.That(restored.Items.Single(i => i.Id == stash).StashOrderId, Is.EqualTo("order"));
            Assert.That(resumed.ConfirmSale(new SaleRequest { ConfirmationId = sold.ConfirmationId }).Total, Is.EqualTo(sold.Total));
            Assert.That(resumed.Snapshot.LifetimeXp, Is.EqualTo(saved.LifetimeXp));
            // Neither loading nor repeated reads charge real elapsed/offline time.
            Assert.That(resumed.Snapshot.LastGameSeconds, Is.EqualTo(saved.LastGameSeconds));
            saved.Buyers[1].Respect = 0; restored.ActiveOrder.Deadline = 0;
            Assert.That(resumed.Snapshot.Buyers[1].Respect, Is.GreaterThan(0));
            Assert.That(resumed.Snapshot.ActiveOrder.Deadline, Is.GreaterThan(0));
        }
    }
}
