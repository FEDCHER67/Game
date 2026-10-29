using System.Collections.Generic;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>G48 as the ONE price source of the economy (EconomyPrices / BuyerCatalog.SyringePrices bound to the loaded
    /// catalogue, explicit id mapping, no fallback when unbound) and the C01 syringe sale through the shared fund
    /// (EconomySyringePayout: $10 then $8 into one fund, once per PortionId, XP in the same commit, save / reload / replay).</summary>
    public sealed class EconomyG48AndC01Tests
    {
        private EconomyCatalog catalog;

        [OneTimeSetUp]
        public void Load()
        {
            catalog = EconomyCatalog.Load(EconomyCoreTests.G48Path);
            EconomyPrices.Bind(catalog);
        }

        [SetUp]
        public void BindPrices()
        {
            EconomyPrices.Bind(catalog);
            BuyerCatalog.SyringePrices = new G48SyringePriceLookup(catalog);
        }

        [TearDown]
        public void Unbind() => BuyerCatalog.SyringePrices = null;

        // ---------- G48 price consistency ----------

        [Test]
        public void EconomyPrices_AreReadFromTheG48Catalogue_ByExplicitIds()
        {
            foreach (VanBranch b in new[] { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes })
                for (int tier = 1; tier <= 3; tier++)
                    Assert.That(EconomyPrices.VanTierPrice(b, tier), Is.EqualTo((int)catalog.GetPrice(EconomyPrices.VanCatalogId(b, tier))), b + " " + tier);
            foreach (PropertyOffer p in EconomyPrices.Properties)
                Assert.That(p.Price, Is.EqualTo((int)catalog.GetBasePrice(p.CatalogId)), p.Id);
            foreach (EquipmentOffer e in EconomyPrices.Equipment)
                Assert.That(e.Price, Is.EqualTo((int)catalog.GetPrice(e.CatalogId)), e.Id);
            foreach (ConsumableOffer c in EconomyPrices.Consumables)
                Assert.That(c.Price, Is.EqualTo((int)catalog.GetPrice(c.CatalogId)), c.Id);
            Assert.That(EconomyPrices.DeliveryGameHours, Is.EqualTo((double)catalog.DeliveryGameHours));
            Assert.That(EconomyPrices.VanInitialPrice, Is.EqualTo(400));
            Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseLab).Tables, Is.EqualTo(-1), "lab: no fixed table limit (null in G48)");
            Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseHamlet).Tables, Is.EqualTo(1));
            Assert.That(EconomyPrices.FindEquipment("rare_equipment").Available, Is.False);
        }

        [Test]
        public void Unbound_NoPricesNoPurchases_NeverAFallback()
        {
            try
            {
                EconomyPrices.Bind(null);
                Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 1), Is.EqualTo(-1));
                Assert.That(EconomyPrices.FindEquipment("knife").Available, Is.False);
                Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseRough).Price, Is.EqualTo(-1));
                EconomyState s = EconomyState.NewGame();
                s.Credit(200000, "test", "", "test:money");
                s.SetWorkshopUnlocked(true);
                s.SetFirstOrganBuyerMet(true);
                Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.ItemUnavailable));
                Assert.That(s.TryBuyProperty(EconomyPrices.BaseRough, 8100).Error, Is.EqualTo(PurchaseError.ItemUnavailable));
                Assert.That(s.TryOrderEquipment("knife", EconomyPrices.BaseHamlet, 100, "k1").Error, Is.EqualTo(PurchaseError.ItemUnavailable));
                Assert.That(s.Fund.Balance, Is.EqualTo(200000));
            }
            finally { EconomyPrices.Bind(catalog); }
        }

        [Test]
        public void SyringeAliases_ResolveToG48_AndABoundLookupNeverFallsBack()
        {
            Assert.That(BuyerCatalog.SyringePrice("c01_blood_first"), Is.EqualTo((int)catalog.GetPrice("blood_syringe_first")));
            Assert.That(BuyerCatalog.SyringePrice("c01_blood_repeat"), Is.EqualTo((int)catalog.GetPrice("blood_syringe_repeat")));
            Assert.That(SyringeRules.Price(SyringeKind.Blood), Is.EqualTo((int)catalog.GetPrice("syringe_blood")));
            BuyerCatalog.SyringePrices = new NoPrices();
            Assert.Throws<System.InvalidOperationException>(() => BuyerCatalog.SyringePrice("c01_blood_first"));
        }

        [Test]
        public void OrganQuote_UsesG48QualityAndBuyerCoefficient()
        {
            // buyer_first x1, Good (x1.5), not cooled (x0.9), first unit: 250 * 1.5 * 0.9 = 337.5
            decimal kidney = BuyerCatalog.UnitPrice(catalog, "buyer_first", ProductKind.Kidney, QualityTier.Good, 0, false, false, 0, false);
            Assert.That(kidney, Is.EqualTo(catalog.GetPrice("kidney") * catalog.QualityMultiplier(QualityTier.Good) * catalog.Get("uncooled_multiplier").Number("value")));
        }

        // ---------- C01 ----------

        private sealed class NoPrices : ISyringePriceLookup
        {
            public bool TryGetPrice(string id, out int dollars) { dollars = 0; return false; }
        }

        private static SyringeInstance Filled(string person, int portion, SyringeInstance reuse = null)
        {
            SyringeInstance s = reuse ?? SyringeInstance.New(SyringeKind.Blood);
            s.PersonId = person;
            s.Fill = 1;
            s.Portion = new BloodPortion { Id = person + "/blood/" + portion, PersonId = person, FreshSeconds = 60 };
            return s;
        }

        private sealed class World
        {
            public EconomyState Economy = EconomyState.NewGame();
            public SyringeSalesSave Sales = new SyringeSalesSave();
            public readonly List<string> Participants = new List<string> { "host" };
            public SyringeInstance LastAfter;
            public int Applied;

            public bool Sell(SyringeInstance syringe, SyringeReturnChoice choice = SyringeReturnChoice.TakeEmpty, string tx = null)
            {
                var rules = new SyringeSaleRules(Sales);
                var payout = new EconomySyringePayout(Economy, Participants, (next, after) => { Sales = next; LastAfter = after; Applied++; });
                return rules.TryConfirm(tx ?? "c01:" + syringe.Portion?.Id, syringe.Portion, syringe, Participants.Count, payout, out _, choice);
            }

            public World Reload()
            {
                var w = new World
                {
                    Economy = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(Economy.ToSave()))),
                    Sales = JsonUtility.FromJson<SyringeSalesSave>(JsonUtility.ToJson(Sales)),
                };
                return w;
            }
        }

        [Test]
        public void C01_First10ThenRepeat8_IntoTheOneFund_XpOncePerSale()
        {
            var w = new World();
            SyringeInstance syringe = Filled("NPC-A", 1);
            string item = syringe.ItemId;
            Assert.That(w.Sell(syringe), Is.True);
            Assert.That(w.Economy.Fund.Balance, Is.EqualTo(10));
            Assert.That(w.Economy.XpOf("host", "blood"), Is.EqualTo(55), "5 + one-time 50");
            Assert.That(syringe.ItemId, Is.EqualTo(item), "the same emptied syringe comes back");
            Assert.That(syringe.PersonId, Is.EqualTo("NPC-A"), "binding kept");
            Assert.That(syringe.Portion, Is.Null);
            Assert.That(w.Economy.Story.HasFact(OnlyVolunteers.Story.StoryFacts.TutorialSale), Is.True, "M01 outcome in the same commit");
            Filled("NPC-A", 2, syringe);
            Assert.That(w.Sell(syringe), Is.True);
            Assert.That(w.Economy.Fund.Balance, Is.EqualTo(18));
            Assert.That(w.Economy.XpOf("host", "blood"), Is.EqualTo(60));
            Assert.That(w.Economy.Fund.History.Count, Is.EqualTo(2), "one fund line per sold portion, no second wallet");
        }

        [Test]
        public void C01_ReplayRestoreOrNewTransaction_NeverPaysTwice()
        {
            var w = new World();
            SyringeInstance syringe = Filled("NPC-A", 1);
            string portion = syringe.Portion.Id;
            BloodPortion copy = syringe.Portion.Copy();
            Assert.That(w.Sell(syringe), Is.True);
            Assert.That(w.Sell(syringe, tx: "c01:" + portion), Is.True, "the same confirmation answers with its receipt");
            Assert.That(w.Economy.Fund.Balance, Is.EqualTo(10));
            World loaded = w.Reload();
            Assert.That(loaded.Sales.SoldPortions, Does.Contain(portion));
            Assert.That(loaded.Sales.FirstSyringeSold, Is.True);
            // the same portion presented again (e.g. an old copy) with a fresh transaction id: refused, nothing booked
            SyringeInstance forged = SyringeInstance.New(SyringeKind.Blood);
            forged.PersonId = "NPC-A"; forged.Portion = copy;
            Assert.That(loaded.Sell(forged, tx: "c01:other-tx"), Is.False);
            Assert.That(loaded.Economy.Fund.Balance, Is.EqualTo(10));
            Assert.That(loaded.Economy.XpOf("host"), Is.EqualTo(55));
            // the sale record lost but the fund key restored: the payout replays (no money, no XP), the record heals
            var lost = new World { Economy = loaded.Economy };
            SyringeInstance again = SyringeInstance.New(SyringeKind.Blood);
            again.PersonId = "NPC-A"; again.Portion = copy.Copy();
            Assert.That(lost.Sell(again), Is.True);
            Assert.That(lost.Economy.Fund.Balance, Is.EqualTo(10));
            Assert.That(lost.Economy.XpOf("host"), Is.EqualTo(55));
            Assert.That(lost.Sales.SoldPortions, Does.Contain(portion));
        }

        [Test]
        public void C01_LeaveWithBuyer_DiscardsThatInstanceOnly()
        {
            var w = new World();
            SyringeInstance syringe = Filled("NPC-B", 1);
            Assert.That(w.Sell(syringe, SyringeReturnChoice.LeaveWithBuyer), Is.True);
            Assert.That(w.LastAfter.Discarded, Is.True);
            Assert.That(w.LastAfter.ItemId, Is.EqualTo(syringe.ItemId));
            Assert.That(syringe.Discarded, Is.True);
            Assert.That(w.Economy.Fund.Balance, Is.EqualTo(10));
        }

        [Test]
        public void C01_TwoParticipants_EachGetXp_FundPaidOnce()
        {
            var w = new World();
            w.Participants.Add("client:1");
            Assert.That(w.Sell(Filled("NPC-C", 1)), Is.True);
            Assert.That(w.Economy.Fund.Balance, Is.EqualTo(10), "a team sale pays the fund once");
            Assert.That(w.Economy.XpOf("host"), Is.EqualTo(55));
            Assert.That(w.Economy.XpOf("client:1"), Is.EqualTo(55));
        }

        [Test]
        public void Calendar_DayWrapsAtMidnight_AndSurvivesReload()
        {
            EconomyState s = EconomyState.NewGame();
            Assert.That(s.TimeOfDay, Is.EqualTo(-1));
            s.ObserveClock(22.0);
            s.ObserveClock(23.9);
            s.ObserveClock(0.1);
            Assert.That(s.WorldDay, Is.EqualTo(1));
            s.ObserveClock(6.5);
            Assert.That(s.AbsoluteHours, Is.EqualTo(30.5).Within(1e-9));
            EconomyState loaded = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(s.ToSave())));
            Assert.That(loaded.AbsoluteHours, Is.EqualTo(30.5).Within(1e-9));
            // G49 daily find on this calendar: one record, start/load do not double, the next morning makes one more
            var daily = new DailySyringeFindSave();
            Assert.That(DailySyringeFindRules.Advance(daily, "W", (long)(loaded.AbsoluteHours * 3600), true), Is.True);
            Assert.That(DailySyringeFindRules.Advance(daily, "W", (long)(loaded.AbsoluteHours * 3600), true), Is.False);
            string id = daily.Uncollected.ItemId;
            loaded.AdvanceCalendar(24.0);
            Assert.That(DailySyringeFindRules.Advance(daily, "W", (long)(loaded.AbsoluteHours * 3600), true), Is.False, "uncollected: never piles up");
            Assert.That(daily.Uncollected.ItemId, Is.EqualTo(id));
        }
    }
}
