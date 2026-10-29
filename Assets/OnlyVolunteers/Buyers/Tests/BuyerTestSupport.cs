using System;
using System.Linq;
using NUnit.Framework;
using OnlyVolunteers.Economy;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class TestClock : IBuyerClock { public long Now; public long GameSeconds => Now; }
    public sealed class TestRandom : IBuyerRandom
    {
        public int Value;
        public int Calls;
        public int NextPercent() { Calls++; return Value; }
    }

    public abstract class BuyerTestSupport
    {
        protected const string Organ = BuyerCatalog.OrganBuyer;
        protected const string Blood = BuyerCatalog.BloodBuyer;
        protected TestClock clock;
        protected TestRandom rng;
        protected BuyerRules rules;
        protected int sequence;
        /// <summary>WP02: the team economy of the test world (the ONE money / XP store; BuyerWorldState keeps none).</summary>
        protected EconomyState economyState;
        protected EconomyBuyerLedger economy;

        [SetUp]
        public void Setup()
        {
            clock = new TestClock(); rng = new TestRandom(); sequence = 0;
            rules = NewWorld(Seed());
        }
        /// <summary>A new world: a fresh economy and buyer rules from the seed; xp = team XP already earned (free).</summary>
        protected BuyerRules NewWorld(BuyerWorldState seed, long xp = 0)
        {
            economyState = EconomyState.NewGame();
            economy = new EconomyBuyerLedger(economyState);
            if (xp > 0) GrantXp(xp);
            return new BuyerRules(clock, rng, economy, seed);
        }
        /// <summary>The same world reloaded: the buyer snapshot again, the economy as it is.</summary>
        protected BuyerRules Reload(BuyerWorldState saved) => new BuyerRules(clock, rng, economy, saved);
        protected void GrantXp(long xp, string who = "seed") =>
            economyState.CommitSale(1, "test", "test XP", "test:xp:" + ++sequence, "test", (int)xp, new[] { who });
        /// <summary>A participant who already bought bargaining ranks 1..rank (with XP earned for them).</summary>
        protected void GiveBargainRank(string who, int rank)
        {
            for (int r = 1; r <= rank; r++)
            {
                GrantXp(EconomyState.SkillCost(EconomyState.SkillBargain, r));
                Assert.That(economy.TryBuyBargainRank(who, r), Is.True);
            }
        }
        protected static BuyerWorldState Seed(int respect = 30) => new BuyerWorldState {
            OrganContactUnlocked = true,
            PresentParticipants = { "p1", "p2" },
            Participants = { new ParticipantState { Id = "p1" }, new ParticipantState { Id = "p2" } },
            Buyers = { new BuyerState { Id = Blood }, new BuyerState { Id = Organ, Respect = respect } } };
        protected BuyerState B(string id = Organ) => rules.Snapshot.Buyers.Single(b => b.Id == id);
        protected BuyerItemState I(string id) => rules.Snapshot.Items.Single(i => i.Id == id);
        protected void Meeting(string buyer = Organ)
        {
            Assert.That(rules.ScheduleMeeting(buyer, "meeting-" + ++sequence, "p1", "base", new[] { "park-a", "park-b" }), Is.True);
            clock.Now += BuyerCatalog.Hour; rules.Tick();
        }
        protected void Group(ProductKind kind = ProductKind.Kidney, string buyer = Organ)
        {
            Assert.That(rules.BeginGroup(buyer, kind, B(buyer).Meeting.NegotiatorId), Is.True);
            if (B(buyer).Meeting.Negotiations.Single(n => n.Kind == kind).Phase != NegotiationPhase.Agreed)
                Assert.That(rules.AcceptMeetingPrice(buyer, B(buyer).Meeting.NegotiatorId), Is.True);
        }
        protected string Add(ProductKind kind = ProductKind.Kidney, QualityTier tier = QualityTier.Acceptable,
            bool cooled = true, bool packaged = false, string holder = "p1", string npc = "target", string npcType = "HAMLET_BODYBUILDER")
        {
            string id = "item-" + ++sequence;
            Assert.That(rules.RegisterItem(new BuyerItemState { Id = id, Kind = kind, Quality = tier,
                DeliveredCooled = cooled, Packaged = packaged, HolderId = holder, SourceNpcId = npc, SourceNpcType = npcType }), Is.True);
            return id;
        }
        protected SaleRequest Request(string[] ids, string buyer = Organ, string player = "p1") => new SaleRequest {
            ConfirmationId = "confirm-" + ++sequence, BuyerId = buyer,
            MeetingId = B(buyer).Meeting.Id, NegotiatorId = player, ItemIds = ids };
        protected SaleResult Sell(ProductKind kind = ProductKind.Kidney, string buyer = Organ, int count = 1)
        {
            Group(kind, buyer);
            string[] ids = Enumerable.Range(0, count).Select(_ => Add(kind)).ToArray();
            foreach (string id in ids) Assert.That(rules.LoadItem(buyer, id, "p1"), Is.True);
            var result = rules.ConfirmSale(Request(ids, buyer));
            Assert.That(result.Success, Is.True, result.Error.ToString()); return result;
        }
        protected void Offer(OrderTemplate template = OrderTemplate.HamletKidney, string id = "order")
        {
            Assert.That(rules.CreateOrderOffer(id, Organ, template, "target", "stash", "p1"), Is.True);
        }
        protected void Order(int percent = 0, OrderTemplate template = OrderTemplate.HamletKidney)
        {
            Offer(template);
            if (percent == 0) Assert.That(rules.AcceptOrderPrice("order", "p1"), Is.True);
            else { rng.Value = 0; Assert.That(rules.AskOrder("order", "p1", percent), Is.True); }
            Assert.That(rules.AcceptOrder("order", "p1"), Is.True);
        }
        protected SaleRequest StashRequest(string id) => new SaleRequest {
            ConfirmationId = "stash-confirm-" + ++sequence, BuyerId = Organ, OrderId = "order", NegotiatorId = "p1", ItemIds = new[] { id } };
        protected string Deposit(QualityTier tier = QualityTier.Good, bool cooled = true, bool packaged = true,
            string npc = "target", string npcType = "HAMLET_BODYBUILDER", ProductKind kind = ProductKind.Kidney)
        {
            string id = Add(kind, tier, cooled, packaged, npc: npc, npcType: npcType);
            Assert.That(rules.DepositInStash("order", id, "p1"), Is.True); return id;
        }
        protected void Respect40() { rules = NewWorld(Seed(40)); }
    }
}
