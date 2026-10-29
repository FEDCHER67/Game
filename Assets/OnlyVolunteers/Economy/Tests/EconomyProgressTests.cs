using System.Collections.Generic;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>WP02: the ONE XP store of a team world in EconomyState (CORE_LOOP v01 §3, §4, CP-01…04, CP-07, CP-08;
    /// ECONOMY v01 §3.4): lifetime / free XP, the level curve, sale XP with the once-per-world first-of-a-kind and first-blood
    /// bonuses in the same commit as the money, skills bought atomically from free XP (personal bargaining ranks per stable
    /// participant id), the save round trip, the v1 block and the once-only move of the old BuyerWorldState money / XP.</summary>
    public sealed class EconomyProgressTests
    {
        private static readonly string[] Solo = { "host" };
        private static readonly string[] Duo = { "host", "0f3c9a1e2b7d4c58a6e1f2b3c4d5e6f7" };
        private int seq;

        private SaleCommit Sell(EconomyState s, IList<string> who, params ProductKind[] units) =>
            s.CommitSale(100, "sale", "test sale", "sale:test:" + ++seq, units, false, who);

        private void Grant(EconomyState s, int xp, string who = "host") =>
            s.CommitSale(1, "test", "test XP", "test:xp:" + ++seq, "test", xp, new[] { who });

        private static EconomyState RoundTrip(EconomyState s) =>
            EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(s.ToSave())));

        // ---------- level curve (CP-04) ----------

        [TestCase(0, 1)] [TestCase(499, 1)] [TestCase(500, 2)] [TestCase(1499, 2)]
        [TestCase(1500, 3)] [TestCase(3499, 3)] [TestCase(3500, 4)] [TestCase(100000, 4)]
        public void LevelFollowsLifetimeXp(int lifetime, int level) => Assert.That(EconomyState.LevelFor(lifetime), Is.EqualTo(level));

        [Test]
        public void NextLevelThresholds()
        {
            Assert.That(EconomyState.NextLevelAt(1), Is.EqualTo(500));
            Assert.That(EconomyState.NextLevelAt(2), Is.EqualTo(1500));
            Assert.That(EconomyState.NextLevelAt(3), Is.EqualTo(3500));
            Assert.That(EconomyState.NextLevelAt(4), Is.EqualTo(-1));
        }

        /// <summary>CP-01 (CORE §3 example): spending 500 of 650 leaves 150 free and 650 lifetime; the level stays.</summary>
        [Test]
        public void SpendingFreeXpNeverLowersTheLevel()
        {
            var s = EconomyState.NewGame();
            Grant(s, 650);
            Assert.That(s.Level, Is.EqualTo(2));
            SkillPurchaseResult r = s.TryBuySkill(EconomyState.SkillBargain, "host", 1);
            Assert.That(r.Ok && !r.Replayed, Is.True, r.Message);
            Assert.That(s.FreeXp, Is.EqualTo(150));
            Assert.That(s.LifetimeXp, Is.EqualTo(650));
            Assert.That(s.Level, Is.EqualTo(2));
        }

        // ---------- sale XP in the money commit (CP-02, CP-03) ----------

        [Test]
        public void OrganSaleXp_FirstOfAKindOncePerWorld_OnlyTheFirstUnit()
        {
            var s = EconomyState.NewGame();
            SaleCommit first = Sell(s, Solo, ProductKind.Kidney, ProductKind.Kidney, ProductKind.Kidney);
            Assert.That(first.XpEach, Is.EqualTo(3 * 20 + 100));
            Assert.That(Sell(s, Solo, ProductKind.Kidney).XpEach, Is.EqualTo(20), "no second kidney bonus");
            Assert.That(Sell(s, Solo, ProductKind.Liver).XpEach, Is.EqualTo(120));
            Assert.That(Sell(s, Solo, ProductKind.Brain).XpEach, Is.EqualTo(270));
            Assert.That(s.FirstKinds, Is.EquivalentTo(new[] { "Kidney", "Liver", "Brain" }));
            EconomyState loaded = RoundTrip(s);
            Assert.That(Sell(loaded, Solo, ProductKind.Liver).XpEach, Is.EqualTo(20), "the flag survives the save");
        }

        [Test]
        public void FirstBloodOncePerWorld_WhateverSellsItFirst()
        {
            var s = EconomyState.NewGame();
            Assert.That(Sell(s, Solo, ProductKind.BloodBag).XpEach, Is.EqualTo(55));
            Assert.That(s.FirstBloodGranted, Is.True);
            Assert.That(Sell(s, Solo, ProductKind.IntroSyringe).XpEach, Is.EqualTo(5), "the syringe after the bag: no second +50");
            Assert.That(Sell(RoundTrip(s), Solo, ProductKind.BloodBag).XpEach, Is.EqualTo(5));
        }

        [Test]
        public void TimelySpecialOrderAdds150()
        {
            var s = EconomyState.NewGame();
            SaleCommit c = s.CommitSale(500, "sale", "order", "sale:order:1", new[] { ProductKind.Kidney }, true, Solo);
            Assert.That(c.XpEach, Is.EqualTo(20 + 100 + 150));
        }

        /// <summary>CP-03: each present participant gets the XP, the team the sum; the money is paid once.</summary>
        [Test]
        public void TeamXpIsTheSumOfThePresent_MoneyOnce()
        {
            var s = EconomyState.NewGame();
            SaleCommit c = Sell(s, Duo, ProductKind.Kidney);
            Assert.That(c.XpEach, Is.EqualTo(120));
            Assert.That(c.TeamXp, Is.EqualTo(240));
            Assert.That(s.LifetimeXp, Is.EqualTo(240));
            Assert.That(s.Fund.Balance, Is.EqualTo(100));
            Assert.That(s.XpOf("host"), Is.EqualTo(120));
            Assert.That(s.XpOf(Duo[1]), Is.EqualTo(120), "personal statistic per stable id");
        }

        /// <summary>CP-02 / CP-07: a repeated key (retry, restored receipt) pays and grants nothing again.</summary>
        [Test]
        public void ReplayedSaleKeyBooksNothing_AndAnswersWithTheOriginalGrant()
        {
            var s = EconomyState.NewGame();
            SaleCommit c = s.CommitSale(250, "sale", "kidney", "sale:k:1", new[] { ProductKind.Kidney }, false, Duo);
            SaleCommit again = s.CommitSale(250, "sale", "kidney", "sale:k:1", new[] { ProductKind.Kidney }, false, Duo);
            Assert.That(again.Fund.Status, Is.EqualTo(FundStatus.Duplicate));
            Assert.That(again.XpEach, Is.EqualTo(c.XpEach));
            Assert.That(s.Fund.Balance, Is.EqualTo(250));
            Assert.That(s.LifetimeXp, Is.EqualTo(240));
        }

        [Test]
        public void ReachingAThresholdIsInTheSameCommit()
        {
            var s = EconomyState.NewGame();
            Grant(s, 430);
            SaleCommit c = Sell(s, Solo, ProductKind.Kidney); // 430 + 120 = 550
            Assert.That(c.LevelBefore, Is.EqualTo(1));
            Assert.That(c.LevelAfter, Is.EqualTo(2));
            Assert.That(c.LevelUp, Is.True);
            Assert.That(s.ToSnapshot(5, true).level, Is.EqualTo(2));
        }

        [Test]
        public void AFundThatCannotHoldTheSaleBooksNothing()
        {
            var s = EconomyState.NewGame();
            s.Credit(int.MaxValue - 10, "test", "nearly full", "test:full");
            SaleCommit c = Sell(s, Solo, ProductKind.Kidney);
            Assert.That(c.Overflow, Is.True);
            Assert.That(c.Ok, Is.False);
            Assert.That(s.LifetimeXp, Is.Zero);
            Assert.That(s.FirstKinds, Is.Empty);
        }

        // ---------- skills (CP-08) ----------

        [Test]
        public void SkillRanksInOrder_PricesAndMaxima()
        {
            var s = EconomyState.NewGame();
            Grant(s, 10000);
            Assert.That(s.TryBuySkill(EconomyState.SkillDosage, "", 2).Error, Is.EqualTo(SkillError.RankChanged));
            Assert.That(s.TryBuySkill(EconomyState.SkillDosage, "", 1).Cost, Is.EqualTo(500));
            Assert.That(s.TryBuySkill(EconomyState.SkillDosage, "", 2).Cost, Is.EqualTo(1000));
            Assert.That(s.TryBuySkill(EconomyState.SkillDosage, "", 3).Cost, Is.EqualTo(2000));
            Assert.That(s.TryBuySkill(EconomyState.SkillDosage, "", 4).Error, Is.EqualTo(SkillError.AlreadyMax));
            Assert.That(s.TryBuySkill(EconomyState.SkillFormula, "", 1).Cost, Is.EqualTo(1000));
            Assert.That(s.TryBuySkill(EconomyState.SkillFormula, "", 2).Cost, Is.EqualTo(3000));
            Assert.That(s.TryBuySkill(EconomyState.SkillFormula, "", 3).Error, Is.EqualTo(SkillError.AlreadyMax));
            Assert.That(s.SpentXp, Is.EqualTo(7500));
            Assert.That(s.FreeXp, Is.EqualTo(2500));
            Assert.That(s.TryBuySkill("unknown", "", 1).Error, Is.EqualTo(SkillError.UnknownSkill));
            Assert.That(s.TryBuySkill(EconomyState.SkillBargain, "", 1).Error, Is.EqualTo(SkillError.NoParticipant));
        }

        /// <summary>CORE §3: a personal bargaining rank belongs to one participant and is not handed to everyone.</summary>
        [Test]
        public void BargainRanksArePersonal_PaidFromTheTeamsFreeXp()
        {
            var s = EconomyState.NewGame();
            Grant(s, 1000);
            Assert.That(s.TryBuySkill(EconomyState.SkillBargain, "host", 1).Ok, Is.True);
            Assert.That(s.SkillRank(EconomyState.SkillBargain, "host"), Is.EqualTo(1));
            Assert.That(s.SkillRank(EconomyState.SkillBargain, Duo[1]), Is.Zero);
            Assert.That(s.TryBuySkill(EconomyState.SkillBargain, Duo[1], 1).Ok, Is.True, "the other player buys his own first rank");
            Assert.That(s.FreeXp, Is.Zero);
            Assert.That(s.ToSnapshot(5, true).SkillRank(EconomyState.SkillBargain, Duo[1]), Is.EqualTo(1));
        }

        /// <summary>CP-08: two spends competing for the same free XP never both pay with it; a repeat is a replay.</summary>
        [Test]
        public void TwoSpendsNeverPayWithTheSameXp_ARepeatIsAReplay()
        {
            var s = EconomyState.NewGame();
            Grant(s, 600);
            SkillPurchaseResult a = s.TryBuySkill(EconomyState.SkillDosage, "", 1);
            SkillPurchaseResult b = s.TryBuySkill(EconomyState.SkillBargain, "host", 1);
            Assert.That(a.Ok && !a.Replayed, Is.True);
            Assert.That(b.Ok, Is.False);
            Assert.That(b.Error, Is.EqualTo(SkillError.InsufficientXp));
            SkillPurchaseResult again = s.TryBuySkill(EconomyState.SkillDosage, "", 1);
            Assert.That(again.Ok && again.Replayed, Is.True);
            Assert.That(s.FreeXp, Is.EqualTo(100));
            Assert.That(s.XpSpends.Count, Is.EqualTo(1));
        }

        // ---------- save ----------

        [Test]
        public void TheStoreSurvivesTheSave()
        {
            var s = EconomyState.NewGame();
            Sell(s, Duo, ProductKind.BloodBag);
            Sell(s, Duo, ProductKind.Liver);
            Grant(s, 600);
            s.TryBuySkill(EconomyState.SkillBargain, Duo[1], 1);
            EconomySaveData block = s.ToSave();
            Assert.That(block.blockVersion, Is.EqualTo(2));
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.LifetimeXp, Is.EqualTo(s.LifetimeXp));
            Assert.That(loaded.FreeXp, Is.EqualTo(s.FreeXp));
            Assert.That(loaded.Level, Is.EqualTo(s.Level));
            Assert.That(loaded.FirstBloodGranted, Is.True);
            Assert.That(loaded.FirstKinds, Is.EqualTo(new[] { "Liver" }));
            Assert.That(loaded.SkillRank(EconomyState.SkillBargain, Duo[1]), Is.EqualTo(1));
            Assert.That(loaded.TryBuySkill(EconomyState.SkillBargain, Duo[1], 1).Replayed, Is.True, "no second payment after a load");
        }

        /// <summary>A version 1 block (before WP02): its XP lines stay, the first blood is derived from them once.</summary>
        [Test]
        public void Version1BlockLoads_FirstBloodFromItsBloodXp()
        {
            var v1 = new EconomySaveData { blockVersion = 1, balance = 10 };
            v1.xp.Add(new XpEntry { key = "sale:c01:portion:A/blood/1", participant = "host", category = "blood", amount = 55 });
            v1.xp.Add(new XpEntry { key = "sale:c01:portion:A/blood/1", participant = "client:1", category = "blood", amount = 55 });
            EconomyState s = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(v1)));
            Assert.That(s.LifetimeXp, Is.EqualTo(110));
            Assert.That(s.FreeXp, Is.EqualTo(110));
            Assert.That(s.FirstBloodGranted, Is.True);
            Assert.That(s.XpOf("client:1"), Is.EqualTo(55), "old connection-id lines stay as statistics");
            Assert.That(Sell(s, Solo, ProductKind.BloodBag).XpEach, Is.EqualTo(5));
            Assert.That(s.ToSave().blockVersion, Is.EqualTo(2));
        }

        // ---------- once-only move of the old BuyerWorldState money / XP ----------

        private static BuyerLegacyProgress Legacy()
        {
            var legacy = new BuyerLegacyProgress { SharedFunds = 300, LifetimeXp = 3600, FreeXp = 1100, FirstBloodSold = true };
            legacy.FirstOrganTypes.Add(ProductKind.Kidney);
            legacy.Participants.Add(new BuyerLegacyProgress.ParticipantLegacy { Id = "p1", PersonalXp = 1800 });
            legacy.Participants.Add(new BuyerLegacyProgress.ParticipantLegacy { Id = "p2", PersonalXp = 1800, NegotiationLevel = 3 });
            return legacy;
        }

        [Test]
        public void LegacyBuyerProgressMovesOnce_ExactLifetimeFreeRanksAndFlags()
        {
            var s = EconomyState.NewGame();
            Assert.That(s.MigrateBuyerLegacy(Legacy()), Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(300));
            Assert.That(s.LifetimeXp, Is.EqualTo(3600));
            Assert.That(s.FreeXp, Is.EqualTo(1100));
            Assert.That(s.SkillRank(EconomyState.SkillBargain, "p2"), Is.EqualTo(3));
            Assert.That(s.SkillRank(EconomyState.SkillBargain, "p1"), Is.Zero);
            Assert.That(s.XpOf("p1"), Is.EqualTo(1800));
            Assert.That(s.FirstBloodGranted, Is.True);
            Assert.That(s.FirstKindGranted(ProductKind.Kidney), Is.True);
            Assert.That(s.MigrateBuyerLegacy(Legacy()), Is.False, "the same legacy data a second time books nothing");
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.MigrateBuyerLegacy(Legacy()), Is.False, "nor after a save / load");
            Assert.That(loaded.Fund.Balance, Is.EqualTo(300));
            Assert.That(loaded.LifetimeXp, Is.EqualTo(3600));
            Assert.That(loaded.FreeXp, Is.EqualTo(1100));
        }

        [Test]
        public void LegacyRemainderAndImpossibleAmounts()
        {
            var s = EconomyState.NewGame();
            s.MigrateBuyerLegacy(new BuyerLegacyProgress { LifetimeXp = 3500, FreeXp = 3500 });
            Assert.That(s.LifetimeXp, Is.EqualTo(3500));
            Assert.That(s.FreeXp, Is.EqualTo(3500));
            Assert.That(s.XpOf(EconomyState.LegacyTeamParticipant), Is.EqualTo(3500));
            Assert.Throws<System.OverflowException>(() => EconomyState.NewGame().MigrateBuyerLegacy(new BuyerLegacyProgress { SharedFunds = decimal.MaxValue }));
            Assert.Throws<System.OverflowException>(() => EconomyState.NewGame().MigrateBuyerLegacy(new BuyerLegacyProgress { SharedFunds = 10.5m }));
            Assert.Throws<System.ArgumentOutOfRangeException>(() => EconomyState.NewGame().MigrateBuyerLegacy(new BuyerLegacyProgress { LifetimeXp = 10, FreeXp = 20 }));
        }

        // ---------- the C01 syringe payout reads the world's flag ----------

        [Test]
        public void C01SyringeAfterABloodBag_NoSecondFirstBloodBonus()
        {
            var catalog = EconomyCatalog.Load(EconomyCoreTests.G48Path);
            EconomyPrices.Bind(catalog);
            BuyerCatalog.SyringePrices = new G48SyringePriceLookup(catalog);
            try
            {
                var s = EconomyState.NewGame();
                Assert.That(Sell(s, Solo, ProductKind.BloodBag).XpEach, Is.EqualTo(55));
                var sales = new SyringeSalesSave { FirstBloodXpGranted = s.FirstBloodGranted }; // the caller's sync (StoryDirector)
                var rules = new SyringeSaleRules(sales);
                SyringeInstance syringe = SyringeInstance.New(SyringeKind.Blood);
                syringe.PersonId = "NPC-Z"; syringe.Fill = 1;
                syringe.Portion = new BloodPortion { Id = "NPC-Z/blood/1", PersonId = "NPC-Z", FreshSeconds = 60 };
                var payout = new EconomySyringePayout(s, Solo, (next, after) => { });
                Assert.That(rules.TryConfirm("c01:NPC-Z/blood/1", syringe.Portion, syringe, 1, payout, out SyringeSaleReceipt receipt), Is.True);
                Assert.That(payout.LastXpEach, Is.EqualTo(5));
                Assert.That(receipt.XpEach, Is.EqualTo(5), "the receipt agrees with the economy");
                Assert.That(s.XpOf("host"), Is.EqualTo(60));
            }
            finally { BuyerCatalog.SyringePrices = null; }
        }
    }
}
