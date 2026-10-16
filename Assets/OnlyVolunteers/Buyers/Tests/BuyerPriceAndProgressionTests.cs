using System;
using System.Linq;
using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class BuyerPriceAndProgressionTests : BuyerTestSupport
    {
        [Test]
        public void BUY01_FirstBloodUnlocksOrganContact()
        {
            var seed = Seed(); seed.OrganContactUnlocked = false; rules = new BuyerRules(clock, rng, seed);
            Assert.That(rules.IsBuyerAvailable(Organ), Is.False);
            Meeting(Blood); Sell(ProductKind.BloodBag, Blood);
            Assert.That(rules.IsBuyerAvailable(Organ), Is.True);
        }
        [Test]
        public void BUY02_BUY44_IntroSyringeIsTenDollarsOnceNoBargainingAndFirstBloodRewards()
        {
            Meeting(Blood); Group(ProductKind.IntroSyringe, Blood);
            Assert.That(rules.AskMeeting(Blood, "p1", 5), Is.False);
            string id = Add(ProductKind.IntroSyringe); rules.LoadItem(Blood, id, "p1");
            var receipt = rules.ConfirmSale(Request(new[] { id }, Blood));
            Assert.That(receipt.Total, Is.EqualTo(10)); Assert.That(receipt.XpEach, Is.EqualTo(55));
            Assert.That(receipt.TeamXp, Is.EqualTo(110)); Assert.That(B(Blood).Respect, Is.EqualTo(32));
            Assert.That(rules.BeginGroup(Blood, ProductKind.IntroSyringe, "p1"), Is.False);
            var next = Sell(ProductKind.BloodBag, Blood);
            Assert.That(next.XpEach, Is.EqualTo(5)); Assert.That(B(Blood).Respect, Is.EqualTo(33));
        }
        [Test]
        public void BUY44_IntroSyringeAfterBloodBagHasNoSecondFirstBloodBonus()
        {
            Meeting(Blood); var bag = Sell(ProductKind.BloodBag, Blood);
            Assert.That(bag.XpEach, Is.EqualTo(55)); Assert.That(B(Blood).Respect, Is.EqualTo(32));
            var syringe = Sell(ProductKind.IntroSyringe, Blood);
            Assert.That(syringe.Total, Is.EqualTo(10)); Assert.That(syringe.XpEach, Is.EqualTo(5)); Assert.That(syringe.TeamXp, Is.EqualTo(10));
            Assert.That(B(Blood).Respect, Is.EqualTo(33)); Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(120));
            Assert.That(rules.Snapshot.FreeXp, Is.EqualTo(120)); Assert.That(rules.Snapshot.SharedFunds, Is.EqualTo(60));
            Assert.That(rules.Snapshot.IntroSyringeSold, Is.True); Assert.That(rules.Snapshot.FirstBloodSold, Is.True);
        }
        [Test]
        public void BUY03_BUY04_BloodHasFixedBaseAndNoQualityCoolingOrSaturation()
        {
            Meeting(Blood); var sale = Sell(ProductKind.BloodBag, Blood, 10);
            Assert.That(sale.Total, Is.EqualTo(500));
            Assert.That(B(Blood).Counters.All(c => c.Units == 0), Is.True);
            foreach (QualityTier tier in Enum.GetValues(typeof(QualityTier)))
                Assert.That(BuyerCatalog.UnitPrice(ProductKind.BloodBag, tier, 20, false, false, 6, false), Is.EqualTo(60));
        }
        [Test]
        public void BUY11_BUY12_CooledDeliverySurvivesInspectionAndUncooledCostsTenPercent()
        {
            Meeting(); Group(); string cold = Add(), warm = Add(cooled: false);
            rules.LoadItem(Organ, cold, "p1"); rules.LoadItem(Organ, warm, "p1");
            Assert.That(I(cold).DeliveredCooled, Is.True);
            Assert.That(rules.Quote(Request(new[] { cold })).Total, Is.EqualTo(250));
            Assert.That(rules.Quote(Request(new[] { warm })).Total, Is.EqualTo(225));
        }
        [TestCase(QualityTier.Damaged, 75)] [TestCase(QualityTier.Acceptable, 250)]
        [TestCase(QualityTier.Good, 400)] [TestCase(QualityTier.Perfect, 650)] [TestCase(QualityTier.PerfectPlus, 1050)]
        public void BUY13_AllFiveTiersSellWithoutPackaging(QualityTier tier, int price)
        {
            Meeting(); Group(); string id = Add(tier: tier); rules.LoadItem(Organ, id, "p1");
            Assert.That(rules.ConfirmSale(Request(new[] { id })).Total, Is.EqualTo(price));
            Assert.That(I(id).Sold, Is.True);
        }
        [Test]
        public void BUY13_AllSixOrganKindsUseOperationBasePrices()
        {
            decimal[] expected = {250,350,450,1000,200,1200};
            for (int k = 0; k < 6; k++) Assert.That(BuyerCatalog.BasePrice((ProductKind)k), Is.EqualTo(expected[k]));
            Meeting(); foreach (ProductKind kind in Enum.GetValues(typeof(ProductKind)))
                if (BuyerCatalog.IsOrgan(kind)) Assert.That(Sell(kind).Success, Is.True);
        }
        [Test]
        public void BUY14_ConfirmationUsesActualQualityAndOptionalPriceGuard()
        {
            Meeting(); Group(); string id = Add(tier: QualityTier.PerfectPlus); rules.LoadItem(Organ, id, "p1");
            var request = Request(new[] { id }); Assert.That(rules.Quote(request).Total, Is.EqualTo(1050));
            rules.UpdateQuality(id, QualityTier.Good); request.ExpectedTotal = 1050;
            Assert.That(rules.ConfirmSale(request).Error, Is.EqualTo(SaleError.PriceChanged));
            Assert.That(I(id).Sold, Is.False); Assert.That(rules.Snapshot.SharedFunds, Is.Zero);
            request = Request(new[] { id }); Assert.That(rules.ConfirmSale(request).Total, Is.EqualTo(400));
        }
        [Test]
        public void BUY14_UpdateQualityOnlyDegradesAndRejectsImprovement()
        {
            string id = Add(tier: QualityTier.Perfect);
            Assert.That(rules.UpdateQuality(id, QualityTier.PerfectPlus), Is.False); Assert.That(I(id).Quality, Is.EqualTo(QualityTier.Perfect));
            Assert.That(rules.UpdateQuality(id, QualityTier.Perfect), Is.True);
            Assert.That(rules.UpdateQuality(id, QualityTier.Good), Is.True); Assert.That(I(id).Quality, Is.EqualTo(QualityTier.Good));
            Assert.That(rules.UpdateQuality(id, QualityTier.Perfect), Is.False); Assert.That(I(id).Quality, Is.EqualTo(QualityTier.Good));
            Assert.That(rules.UpdateQuality(id, QualityTier.Damaged), Is.True);
            Assert.That(rules.UpdateQuality(id, QualityTier.Acceptable), Is.False); Assert.That(I(id).Quality, Is.EqualTo(QualityTier.Damaged));
            Assert.That(rules.UpdateQuality(Add(ProductKind.BloodBag), QualityTier.Damaged), Is.False);
            Assert.That(rules.UpdateQuality("missing", QualityTier.Damaged), Is.False);
        }
        [Test]
        public void BUY15_BUY16_PerUnitSaturationStopsAtSeventyAndResetsAtMidnight()
        {
            decimal[] expected = {1m,.95m,.90m,.85m,.80m,.75m,.70m,.70m};
            for (int i = 0; i < expected.Length; i++) Assert.That(BuyerCatalog.SaturationMultiplier(i), Is.EqualTo(expected[i]));
            Meeting(); var sale = Sell(count: 8); Assert.That(sale.Total, Is.EqualTo(1663)); // 250 * 6.65 = 1662.50, rounded once.
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).Units, Is.EqualTo(6));
            clock.Now = BuyerCatalog.Day; rules.Tick();
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).Units, Is.Zero);
        }
        [Test]
        public void BUY15_MidnightBetweenQuoteAndConfirmRecomputesSaturation()
        {
            clock.Now = BuyerCatalog.Day - 4000; Meeting(); Sell(); Group();
            string id = Add(); rules.LoadItem(Organ, id, "p1");
            var request = Request(new[] { id }); Assert.That(rules.Quote(request).Total, Is.EqualTo(238));
            clock.Now = BuyerCatalog.Day; Assert.That(rules.ConfirmSale(request).Total, Is.EqualTo(250));
        }
        [Test]
        public void BUY17_DifferentTypesHaveSeparateTermsAndRespectDoesNotMultiplyPrice()
        {
            Meeting(); Group(); Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.False);
            SellAfterGroup(); Assert.That(Sell(ProductKind.Liver).Total, Is.EqualTo(350));
            Assert.That(B().Meeting.Negotiations.Count, Is.EqualTo(2));
            foreach (int respect in new[] {0,19,20,39,40,59,60,79,80,100})
            {
                rules = new BuyerRules(clock, rng, Seed(respect)); Meeting(); Group();
                string id = Add(); rules.LoadItem(Organ, id, "p1");
                Assert.That(B().Respect, Is.EqualTo(respect));
                var request = Request(new[] { id });
                Assert.That(rules.Quote(request).Total, Is.EqualTo(250), "Quote at respect " + respect);
                Assert.That(rules.ConfirmSale(request).Total, Is.EqualTo(250), "Sale at respect " + respect);
            }
        }
        private void SellAfterGroup() { string id = Add(); rules.LoadItem(Organ, id, "p1"); Assert.That(rules.ConfirmSale(Request(new[] { id })).Success, Is.True); }
        [Test]
        public void BUY23_BUY24_BUY51_RespectStartsThirtyAndAcquaintanceOnlyOnce()
        {
            Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(rules.IntroduceBuyer(Organ), Is.True);
            Assert.That(rules.IntroduceBuyer(Organ), Is.False); Assert.That(B().Respect, Is.EqualTo(32));
            Meeting(); Sell(count: 3); Assert.That(B().Respect, Is.EqualTo(36));
            Sell(); Assert.That(B().Respect, Is.EqualTo(37));
        }
        [TestCase(0,1,"ууу хиляк")] [TestCase(19,1,"ууу хиляк")]
        [TestCase(20,2,"новобранец")] [TestCase(39,2,"новобранец")]
        [TestCase(40,3,"бывалый")] [TestCase(59,3,"бывалый")]
        [TestCase(60,4,"проверенный")] [TestCase(79,4,"проверенный")]
        [TestCase(80,5,"своячок")] [TestCase(100,5,"своячок")]
        public void BUY23_BUY51_RespectRangesAndNames(int value, int level, string name)
        { Assert.That(BuyerCatalog.RespectLevel(value), Is.EqualTo(level)); Assert.That(BuyerCatalog.RespectName(value), Is.EqualTo(name)); }
        [Test]
        public void BUY23_RespectClampsAtBothEnds()
        {
            rules = new BuyerRules(clock, rng, Seed(100)); Meeting(); Sell(count: 10); Assert.That(B().Respect, Is.EqualTo(100));
            rules = new BuyerRules(clock, rng, Seed(0)); Meeting(); rules.CancelMeeting(Organ); Assert.That(B().Respect, Is.Zero);
        }
        [Test]
        public void BUY25_ZeroRespectAllowsTradingButFortyRequiredForNewOrders()
        {
            rules = new BuyerRules(clock, rng, Seed(0)); Meeting(); Assert.That(Sell().Success, Is.True);
            Assert.That(rules.CreateOrderOffer("o", Organ, OrderTemplate.HamletKidney, "target", "stash", "p1"), Is.False);
            rules = new BuyerRules(clock, rng, Seed(39)); Assert.That(rules.CreateOrderOffer("o", Organ, OrderTemplate.HamletKidney, "target", "stash", "p1"), Is.False);
            Respect40(); Offer();
        }
        [Test]
        public void BUY36_BUY52_AbdominalSetAndBloodPays630TeamXpAndOnlyOnlinePlayers()
        {
            Meeting(); Sell(count: 2); Sell(ProductKind.Liver); Meeting(Blood); Sell(ProductKind.BloodBag, Blood);
            Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(630)); Assert.That(rules.Snapshot.FreeXp, Is.EqualTo(630));
            rules.SetPresentParticipants("p1", "p3"); Sell(ProductKind.BloodBag, Blood);
            Assert.That(rules.Snapshot.Participants.Single(p => p.Id == "p2").PersonalXp, Is.EqualTo(315));
            Assert.That(rules.Snapshot.Participants.Single(p => p.Id == "p3").PersonalXp, Is.EqualTo(5));
        }
        [TestCase(ProductKind.Kidney,100)] [TestCase(ProductKind.Liver,100)] [TestCase(ProductKind.Eye,100)]
        [TestCase(ProductKind.Lungs,150)] [TestCase(ProductKind.Heart,200)] [TestCase(ProductKind.Brain,250)]
        public void BUY52_NewTypeBonusOncePerSaveOnlyFirstUnit(ProductKind kind, int bonus)
        {
            Meeting(); Assert.That(Sell(kind, count: 3).XpEach, Is.EqualTo(60 + bonus));
            Assert.That(Sell(kind, count: 4).XpEach, Is.EqualTo(80));
        }
        [TestCase(QualityTier.Damaged,"Убитое 20%","#8C7B6B")]
        [TestCase(QualityTier.Acceptable,"Сойдёт 40%","#C2B23A")]
        [TestCase(QualityTier.Good,"Хорошее 60%","#4DC25A")]
        [TestCase(QualityTier.Perfect,"Отличное 80%","#3E8DFF")]
        [TestCase(QualityTier.PerfectPlus,"Идеальное 100%","#A75CFF")]
        public void BUY54_TierLabelsAndColorData(QualityTier tier, string label, string color)
        { Assert.That(BuyerCatalog.QualityLabel(tier), Is.EqualTo(label)); Assert.That(BuyerCatalog.QualityColor(tier), Is.EqualTo(color)); }
        [Test]
        public void BUY55_UpgradesOrderedAndSpendOnlyFreeTeamXp()
        {
            rules = new BuyerRules(clock, rng, Seed(xp: 3500));
            Assert.That(rules.BuyNegotiationUpgrade("p1", 2), Is.False);
            Assert.That(rules.BuyNegotiationUpgrade("p1", 1), Is.True); Assert.That(rules.Snapshot.FreeXp, Is.EqualTo(3000));
            Assert.That(rules.BuyNegotiationUpgrade("p1", 1), Is.False);
            Assert.That(rules.BuyNegotiationUpgrade("p1", 2), Is.True); Assert.That(rules.Snapshot.FreeXp, Is.EqualTo(2000));
            Assert.That(rules.BuyNegotiationUpgrade("p1", 3), Is.True); Assert.That(rules.Snapshot.FreeXp, Is.Zero);
            Assert.That(rules.Snapshot.LifetimeXp, Is.EqualTo(3500)); Assert.That(rules.Snapshot.Participants[0].PersonalXp, Is.Zero);
            Assert.That(rules.BuyNegotiationUpgrade("p2", 1), Is.False); Assert.That(rules.BuyNegotiationUpgrade("p1", 4), Is.False);
        }
    }
}
