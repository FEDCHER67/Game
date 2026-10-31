using NUnit.Framework;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>V2 base P1 (Fedya 31.10): the GEAR shop purchase (one charge, refusals charge nothing, honest owned state,
    /// saved), the workshop open in V2 without the M06 gate, the engine-only upgrade group, the automatic dock thresholds
    /// (0.5 m/s, stable 0.5 s, once per visit) and the baton's own numbers next to the slap.</summary>
    public sealed class BaseV2P1Tests
    {
        private const string Baton = GearCatalogV2.Baton;

        [SetUp]
        public void BindG48() => EconomyPrices.Bind(OnlyVolunteers.Buyers.EconomyCatalog.Load(EconomyCoreTests.G48Path));

        private static EconomyState WithMoney(int money)
        {
            EconomyState s = EconomyState.NewGame();
            if (money > 0) s.Credit(money, "test", "test money", "test:basev2-fund");
            return s;
        }

        private static int Price => GearCatalogV2.Find(Baton).Price;

        // ---------- shop ----------

        [Test]
        public void Catalogue_has_only_the_baton_with_a_placeholder_price_and_an_effect()
        {
            Assert.AreEqual(1, GearCatalogV2.All.Count, "P1 sells one real item, no paid no-ops");
            GearOfferV2 b = GearCatalogV2.Find(Baton);
            Assert.NotNull(b);
            Assert.Greater(b.Price, 0);
            Assert.IsNotEmpty(b.Effect);
            Assert.AreEqual(GearCatalogV2.PlaceholderPrice, b.PriceNote);
            Assert.IsNull(GearCatalogV2.Find("medkit"), "the pharmacy sells nothing yet");
        }

        [Test]
        public void Buying_with_enough_money_charges_once_and_owns_it()
        {
            EconomyState s = WithMoney(1000);
            PurchaseResult r = s.TryBuyGear(Baton, Price, GearShopCheck.Good);
            Assert.True(r.Ok, r.Message);
            Assert.False(r.Replayed);
            Assert.AreEqual(1000 - Price, s.Fund.Balance);
            Assert.True(s.OwnsGear(Baton));
            Assert.True(s.ToSnapshot(5, true).OwnsGear(Baton), "clients see it owned");
        }

        [Test]
        public void A_repeated_press_never_charges_twice()
        {
            EconomyState s = WithMoney(1000);
            Assert.True(s.TryBuyGear(Baton, Price, GearShopCheck.Good).Ok);
            PurchaseResult again = s.TryBuyGear(Baton, Price, GearShopCheck.Good);
            Assert.False(again.Ok);
            Assert.AreEqual(PurchaseError.AlreadyOwned, again.Error);
            Assert.AreEqual(1000 - Price, s.Fund.Balance);
        }

        [Test]
        public void Not_enough_money_charges_nothing_and_owns_nothing()
        {
            EconomyState s = WithMoney(Price - 1);
            PurchaseResult r = s.TryBuyGear(Baton, Price, GearShopCheck.Good);
            Assert.False(r.Ok);
            Assert.AreEqual(PurchaseError.InsufficientFunds, r.Error);
            Assert.AreEqual(Price - 1, s.Fund.Balance);
            Assert.False(s.OwnsGear(Baton));
            Assert.False(s.ToSnapshot(5, true).OwnsGear(Baton));
        }

        [Test]
        public void Far_from_the_display_or_no_sight_charges_nothing()
        {
            EconomyState s = WithMoney(1000);
            Assert.False(s.TryBuyGear(Baton, Price, new GearShopCheck { InReach = false, SightClear = true }).Ok);
            Assert.False(s.TryBuyGear(Baton, Price, new GearShopCheck { InReach = true, SightClear = false }).Ok);
            Assert.AreEqual(1000, s.Fund.Balance);
            Assert.False(s.OwnsGear(Baton));
        }

        [Test]
        public void A_changed_price_or_unknown_item_charges_nothing()
        {
            EconomyState s = WithMoney(1000);
            Assert.AreEqual(PurchaseError.PriceChanged, s.TryBuyGear(Baton, Price - 10, GearShopCheck.Good).Error);
            Assert.AreEqual(PurchaseError.UnknownItem, s.TryBuyGear("laser_sword", 10, GearShopCheck.Good).Error);
            Assert.AreEqual(1000, s.Fund.Balance);
        }

        [Test]
        public void The_purchase_survives_save_and_load()
        {
            EconomyState s = WithMoney(1000);
            Assert.True(s.TryBuyGear(Baton, Price, GearShopCheck.Good).Ok);
            EconomyState loaded = EconomyState.FromSave(s.ToSave());
            Assert.True(loaded.OwnsGear(Baton));
            Assert.AreEqual(1000 - Price, loaded.Fund.Balance);
            Assert.AreEqual(PurchaseError.AlreadyOwned, loaded.TryBuyGear(Baton, Price, GearShopCheck.Good).Error, "no second charge after a load");
            Assert.AreEqual(1000 - Price, loaded.Fund.Balance);
        }

        // ---------- workshop in V2 ----------

        [Test]
        public void V2_base_opens_the_workshop_without_M06_and_engine_tier_can_be_bought()
        {
            EconomyState s = WithMoney(10000);
            Assert.False(s.WorkshopUnlocked, "a new world starts with the v1 gate closed");
            Assert.AreEqual(PurchaseError.WorkshopLocked, s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready).Error);
            Assert.True(BaseV2Rules.OpenWorkshop(s));
            Assert.False(BaseV2Rules.OpenWorkshop(s), "idempotent");
            Assert.True(s.WorkshopUnlocked);
            int price = EconomyPrices.VanTierPrice(VanBranch.Engine, 1);
            PurchaseResult r = s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            Assert.True(r.Ok, r.Message);
            Assert.AreEqual(1, s.VanTier(VanBranch.Engine));
            Assert.AreEqual(10000 - price, s.Fund.Balance);
            Assert.True(EconomyState.FromSave(s.ToSave()).WorkshopUnlocked);
        }

        [Test]
        public void P1_sells_only_the_engine_group()
        {
            Assert.True(BaseV2Rules.Sold(VanBranch.Engine));
            Assert.False(BaseV2Rules.Sold(VanBranch.Brakes));
            Assert.False(BaseV2Rules.Sold(VanBranch.Handling));
        }

        // ---------- dock ----------

        private static DockSignal Run(DockTrackerV2 t, float seconds, bool inZone = true, bool aligned = true, float speed = 0.3f, bool driver = true)
        {
            DockSignal last = DockSignal.None;
            for (float x = 0f; x < seconds - 1e-4f; x += 0.02f)
            {
                last = t.Step(inZone, aligned, speed, driver, 0.02f);
                if (last == DockSignal.Dock) return last;
            }
            return last;
        }

        [Test]
        public void Docks_after_half_a_second_slow_and_aligned()
        {
            var t = new DockTrackerV2();
            Assert.AreEqual(0.5f, t.MaxSpeed);
            Assert.AreEqual(0.5f, t.StableSeconds);
            Assert.AreEqual(DockSignal.Settling, Run(t, 0.46f));
            Assert.AreEqual(DockSignal.Dock, Run(t, 0.1f));
        }

        [Test]
        public void Too_fast_never_docks_and_a_fast_frame_restarts_the_count()
        {
            var t = new DockTrackerV2();
            Assert.AreEqual(DockSignal.None, Run(t, 3f, speed: 0.51f));
            Run(t, 0.4f, speed: 0.5f);
            t.Step(true, true, 0.9f, true, 0.02f);
            Assert.AreEqual(DockSignal.Settling, Run(t, 0.4f, speed: 0.5f), "restarted after the fast frame");
        }

        [Test]
        public void No_dock_without_a_driver_or_out_of_line()
        {
            var t = new DockTrackerV2();
            Assert.AreEqual(DockSignal.None, Run(t, 2f, driver: false));
            Assert.AreEqual(DockSignal.None, Run(t, 2f, aligned: false), "still creeping in: no hint yet");
            Assert.AreEqual(DockSignal.NeedsAlign, Run(t, 1.2f, aligned: false, speed: 0.02f), "stopped out of line: the hint");
            Assert.AreEqual(DockSignal.None, Run(t, 2f, inZone: false));
        }

        [Test]
        public void Docks_once_per_visit_until_the_van_leaves_the_zone()
        {
            var t = new DockTrackerV2();
            Assert.AreEqual(DockSignal.Dock, Run(t, 1f));
            Assert.False(t.Armed);
            Assert.AreEqual(DockSignal.None, Run(t, 3f), "lowered after the service: no second dock in place");
            Run(t, 0.1f, inZone: false);
            Assert.True(t.Armed);
            Assert.AreEqual(DockSignal.Dock, Run(t, 1f));
        }

        [Test]
        public void Alignment_accepts_either_way_round_within_tolerance()
        {
            Assert.True(DockTrackerV2.Aligned(0.3f, 0.8f, 8f, 0.6f, 1.2f, 15f));
            Assert.True(DockTrackerV2.Aligned(0f, 0f, 176f, 0.6f, 1.2f, 15f), "reversed in");
            Assert.False(DockTrackerV2.Aligned(0.7f, 0f, 0f, 0.6f, 1.2f, 15f));
            Assert.False(DockTrackerV2.Aligned(0f, 1.3f, 0f, 0.6f, 1.2f, 15f));
            Assert.False(DockTrackerV2.Aligned(0f, 0f, 40f, 0.6f, 1.2f, 15f));
        }

        // ---------- baton ----------

        [Test]
        public void Baton_has_its_own_reach_cooldown_and_steady_knockout()
        {
            var b = new BatonTuningV2();
            Assert.Greater(b.Reach, 2.3f, "reaches further than the slap (2.3 m)");
            Assert.Greater(b.Cooldown, 0.2f, "but swings slower than the slap (0.2 s)");
            Assert.AreEqual(4f, BatonRulesV2.KnockOut(b, 0));
            Assert.AreEqual(4f, BatonRulesV2.KnockOut(b, 5), "no ladder: the same every hit");
            Assert.False(BatonRulesV2.Ready(10.5f, 10f, b.Cooldown));
            Assert.True(BatonRulesV2.Ready(10.9f, 10f, b.Cooldown));
        }
    }
}
