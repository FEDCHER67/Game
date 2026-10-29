using NUnit.Framework;
using OnlyVolunteers.Economy;

namespace OnlyVolunteers.Buyers.Tests
{
    /// <summary>WP02: BuyerWorldState keeps no money or XP. Every sale goes through the team economy (IBuyerEconomy) in one
    /// booking; an old snapshot's money / XP / ranks / first flags move into the economy exactly once; a refused booking
    /// publishes nothing.</summary>
    public sealed class BuyerEconomyStoreTests : BuyerTestSupport
    {
#pragma warning disable CS0618 // building a pre-WP02 snapshot on purpose
        private static BuyerWorldState LegacySnapshot()
        {
            var s = Seed();
            s.SharedFunds = 300; s.LifetimeXp = 3600; s.FreeXp = 1100; s.FirstBloodSold = true;
            s.FirstOrganTypes.Add(ProductKind.Kidney);
            s.Participants[0].PersonalXp = 1800;
            s.Participants[1].PersonalXp = 1800; s.Participants[1].NegotiationLevel = 3;
            return s;
        }
#pragma warning restore CS0618

        [Test]
        public void LegacySnapshotMovesIntoTheEconomyOnce()
        {
            var old = LegacySnapshot();
            rules = NewWorld(old);
            Assert.That(economyState.Fund.Balance, Is.EqualTo(300));
            Assert.That(economyState.LifetimeXp, Is.EqualTo(3600));
            Assert.That(economyState.FreeXp, Is.EqualTo(1100));
            Assert.That(rules.NegotiationLevel("p2"), Is.EqualTo(3));
            Assert.That(rules.NegotiationLevel("p1"), Is.Zero);
            Assert.That(economyState.FirstBloodGranted, Is.True);
            Assert.That(rules.Snapshot.TakeLegacy().Empty, Is.True, "the new snapshot carries no money or XP");
            // the same old snapshot loaded again into the same world: nothing is booked twice
            rules = Reload(old);
            Assert.That(economyState.Fund.Balance, Is.EqualTo(300));
            Assert.That(economyState.LifetimeXp, Is.EqualTo(3600));
            Assert.That(economyState.FreeXp, Is.EqualTo(1100));
            // the migrated first-of-a-kind flag holds: a kidney earns no second bonus
            Meeting(); Assert.That(Sell().XpEach, Is.EqualTo(20));
        }

        [Test]
        public void ASaleBooksMoneyXpAndFlagsInTheEconomyOnly()
        {
            Meeting(); var sale = Sell(ProductKind.Liver);
            Assert.That(sale.XpEach, Is.EqualTo(120)); Assert.That(sale.TeamXp, Is.EqualTo(240));
            Assert.That(economyState.Fund.Balance, Is.EqualTo((int)sale.Total));
            Assert.That(economyState.FirstKindGranted(ProductKind.Liver), Is.True);
            Assert.That(economyState.Fund.IsCommitted(BuyerRules.SaleKey(sale.ConfirmationId)), Is.True, "one fund line under the sale key");
            Assert.That(rules.Snapshot.TakeLegacy().Empty, Is.True);
        }

        [Test]
        public void BargainRankComesFromTheEconomy()
        {
            Assert.That(rules.BuyNegotiationUpgrade("p2", 1), Is.False, "no free XP");
            GrantXp(500);
            Assert.That(rules.BuyNegotiationUpgrade("p2", 1), Is.True);
            Assert.That(economyState.SkillRank(EconomyState.SkillBargain, "p2"), Is.EqualTo(1));
            Assert.That(rules.NegotiationLevel("p1"), Is.Zero, "not handed to everyone");
        }

        private sealed class RefusingEconomy : IBuyerEconomy
        {
            public bool Refuse = true;
            public readonly EconomyBuyerLedger Inner;
            public RefusingEconomy(EconomyBuyerLedger inner) { Inner = inner; }
            public BuyerBookingResult Book(BuyerSaleBooking booking) => Refuse ? default : Inner.Book(booking);
            public int BargainRank(string participantId) => Inner.BargainRank(participantId);
            public bool TryBuyBargainRank(string participantId, int nextRank) => Inner.TryBuyBargainRank(participantId, nextRank);
            public void MigrateLegacy(BuyerLegacyProgress legacy) => Inner.MigrateLegacy(legacy);
        }

        [Test]
        public void ARefusedBookingPublishesNothing_TheSameIdMayRetry()
        {
            var refusing = new RefusingEconomy(economy);
            rules = new BuyerRules(clock, rng, refusing, Seed());
            Meeting(); Group(); string id = Add(); rules.LoadItem(Organ, id, "p1");
            var request = Request(new[] { id });
            Assert.That(rules.ConfirmSale(request).Error, Is.EqualTo(SaleError.PaymentRefused));
            Assert.That(I(id).Sold, Is.False); Assert.That(rules.Snapshot.Receipts, Is.Empty);
            Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(economyState.Fund.Balance, Is.Zero);
            refusing.Refuse = false;
            Assert.That(rules.ConfirmSale(request).Success, Is.True);
            Assert.That(I(id).Sold, Is.True); Assert.That(economyState.Fund.Balance, Is.EqualTo(250));
        }
    }
}
