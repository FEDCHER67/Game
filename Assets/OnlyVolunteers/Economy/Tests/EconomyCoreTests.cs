using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>ECONOMY_SALES_PROGRESSION_SPEC v01: shared fund idempotency (§3.1, §10.1), cash migration (§10.3), van tier
    /// prices and order (§6.1, §6.3), equipment delivery persistence (§4.1) and property (§7.1). Pure rules only; the
    /// scene, co-op and save file are checked in Play.</summary>
    public sealed class EconomyCoreTests
    {
        /// <summary>The G48 catalogue file the runtime bootstrap binds (Buyers/Data/Economy_v01.json): every price below is
        /// read through EconomyPrices from it, never from a copied table.</summary>
        public static string G48Path => System.IO.Path.Combine(Application.dataPath, "OnlyVolunteers/Buyers/Data/Economy_v01.json");

        [OneTimeSetUp]
        public void BindG48() => EconomyPrices.Bind(OnlyVolunteers.Buyers.EconomyCatalog.Load(G48Path));

        private static EconomyState Funded(int amount)
        {
            EconomyState s = EconomyState.NewGame();
            if (amount > 0) s.Credit(amount, "test", "test money", "test:fund");
            return s;
        }

        private static EconomyState RoundTrip(EconomyState s) =>
            FundMigration.LoadOrMigrate(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(s.ToSave())), true, 99999);

        // ---------- fund ----------

        [Test]
        public void Credit_SameKeyTwice_PaysOnce()
        {
            var fund = new FundLedger();
            Assert.That(fund.Credit(250, "sale", "kidney", "sale:K1").Status, Is.EqualTo(FundStatus.Committed));
            FundResult again = fund.Credit(250, "sale", "kidney", "sale:K1");
            Assert.That(again.Status, Is.EqualTo(FundStatus.Duplicate));
            Assert.That(again.Ok, Is.True);
            Assert.That(fund.Balance, Is.EqualTo(250));
            Assert.That(fund.History.Count, Is.EqualTo(1));
        }

        [Test]
        public void Charge_SameKeyTwice_ChargesOnce_AndNeverGoesNegative()
        {
            var fund = new FundLedger();
            fund.Credit(1000, "test", "", "c");
            Assert.That(fund.TryCharge(600, "buy", "", "buy:1").Status, Is.EqualTo(FundStatus.Committed));
            Assert.That(fund.TryCharge(600, "buy", "", "buy:1").Status, Is.EqualTo(FundStatus.Duplicate));
            Assert.That(fund.Balance, Is.EqualTo(400));
            Assert.That(fund.TryCharge(600, "buy", "", "buy:2").Status, Is.EqualTo(FundStatus.Insufficient));
            Assert.That(fund.Balance, Is.EqualTo(400));
        }

        [Test]
        public void RefusedCharge_IsNotRecorded_SoTheSameKeyCanSucceedLater()
        {
            var fund = new FundLedger();
            Assert.That(fund.TryCharge(100, "buy", "", "buy:x").Status, Is.EqualTo(FundStatus.Insufficient));
            fund.Credit(100, "sale", "", "sale:y");
            Assert.That(fund.TryCharge(100, "buy", "", "buy:x").Status, Is.EqualTo(FundStatus.Committed));
            Assert.That(fund.Balance, Is.EqualTo(0));
        }

        [Test]
        public void InvalidAmountsAndKeys_ChangeNothing()
        {
            var fund = new FundLedger();
            Assert.That(fund.Credit(0, "", "", "a").Status, Is.EqualTo(FundStatus.Invalid));
            Assert.That(fund.Credit(-5, "", "", "b").Status, Is.EqualTo(FundStatus.Invalid));
            Assert.That(fund.Credit(5, "", "", "").Status, Is.EqualTo(FundStatus.Invalid));
            Assert.That(fund.TryCharge(-5, "", "", "c").Status, Is.EqualTo(FundStatus.Invalid));
            Assert.That(fund.Balance, Is.EqualTo(0));
            Assert.That(fund.History.Count, Is.EqualTo(0));
        }

        [Test]
        public void HistoryLimit_DoesNotRemoveDuplicateProtection_AlsoAfterReload()
        {
            EconomyState s = EconomyState.NewGame();
            for (int i = 0; i < FundLedger.HistoryLimit + 50; i++) s.Credit(1, "sale", "", "sale:" + i);
            Assert.That(s.Fund.History.Count, Is.EqualTo(FundLedger.HistoryLimit));
            Assert.That(s.Credit(1, "sale", "", "sale:0").Status, Is.EqualTo(FundStatus.Duplicate));
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.Fund.Balance, Is.EqualTo(FundLedger.HistoryLimit + 50));
            Assert.That(loaded.Credit(1, "sale", "", "sale:0").Status, Is.EqualTo(FundStatus.Duplicate));
            Assert.That(loaded.Credit(1, "sale", "", "sale:249").Status, Is.EqualTo(FundStatus.Duplicate));
            Assert.That(loaded.Fund.Balance, Is.EqualTo(FundLedger.HistoryLimit + 50));
        }

        // ---------- migration (§10.3) ----------

        [Test]
        public void Migration_LegacyHostCash_MovesOnce_AndReloadDoesNotAddAgain()
        {
            EconomyState migrated = FundMigration.LoadOrMigrate(null, true, 1234);
            Assert.That(migrated.Fund.Balance, Is.EqualTo(1234));
            Assert.That(migrated.MigrationSource, Is.EqualTo(FundMigration.SourceLegacyCash));
            EconomySaveData block = JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(migrated.ToSave()));
            Assert.That(FundMigration.HasBlock(block), Is.True);
            // The legacy fields are still in the file: they must not be added a second time.
            EconomyState reloaded = FundMigration.LoadOrMigrate(block, true, 1234);
            Assert.That(reloaded.Fund.Balance, Is.EqualTo(1234));
            EconomyState third = FundMigration.LoadOrMigrate(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(reloaded.ToSave())), true, 1234);
            Assert.That(third.Fund.Balance, Is.EqualTo(1234));
            Assert.That(third.Fund.History.Count(e => e.key == FundMigration.LegacyCashKey), Is.EqualTo(1));
        }

        [Test]
        public void Migration_NoSavedCash_StartsAtZero_WithOneSystemLine()
        {
            EconomyState s = FundMigration.LoadOrMigrate(null, false, 777);
            Assert.That(s.Fund.Balance, Is.EqualTo(0));
            Assert.That(s.Fund.History.Count, Is.EqualTo(1));
            Assert.That(s.Fund.History[0].amount, Is.EqualTo(0));
            Assert.That(s.MigrationSource, Is.EqualTo(FundMigration.SourceNone));
        }

        [Test]
        public void Migration_ExistingBlock_IsTheOnlySource()
        {
            EconomyState s = Funded(500);
            EconomySaveData block = s.ToSave();
            EconomyState loaded = FundMigration.LoadOrMigrate(block, true, 10000);
            Assert.That(loaded.Fund.Balance, Is.EqualTo(500));
        }

        [Test]
        public void Migration_AbsentBlockInJson_ReadsAsNoBlock()
        {
            EconomySaveData empty = JsonUtility.FromJson<EconomySaveData>("{}");
            Assert.That(FundMigration.HasBlock(empty), Is.False);
            Assert.That(FundMigration.LoadOrMigrate(empty, true, 50).Fund.Balance, Is.EqualTo(50));
        }

        [Test]
        public void Migration_OldSlot_KeepsLegacyVanProfile_NoPaidTiers_NoRefund()
        {
            EconomyState s = FundMigration.LoadOrMigrate(null, true, 100);
            Assert.That(s.VanLegacyDebugProfile, Is.True);
            foreach (VanBranch b in new[] { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes })
                Assert.That(s.VanTier(b), Is.EqualTo(0));
            Assert.That(s.Fund.Balance, Is.EqualTo(100));
            s.SetWorkshopUnlocked(true);
            s.Credit(5000, "test", "", "t");
            PurchaseResult r = s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            Assert.That(r.Ok, Is.False);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.LegacyDebugProfile));
            Assert.That(s.Fund.Balance, Is.EqualTo(5100));
            Assert.That(s.SwitchToProgression(), Is.True);
            Assert.That(s.VanLegacyDebugProfile, Is.False);
            Assert.That(s.Fund.Balance, Is.EqualTo(5100));
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready).Ok, Is.True);
        }

        [Test]
        public void NewGame_IsProgression_WithEmptyFund_AndTheTwoFreeBases()
        {
            EconomyState s = EconomyState.NewGame();
            Assert.That(s.VanLegacyDebugProfile, Is.False);
            Assert.That(s.Fund.Balance, Is.EqualTo(0));
            Assert.That(s.OwnsBase(EconomyPrices.BaseWagon), Is.True);
            Assert.That(s.OwnsBase(EconomyPrices.BaseHamlet), Is.True);
            Assert.That(s.OwnsBase(EconomyPrices.BaseRough), Is.False);
        }

        // ---------- van tiers (§6.1, §6.3) ----------

        [Test]
        public void VanPrices_MatchTheSpec()
        {
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 1), Is.EqualTo(1500));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 2), Is.EqualTo(2250));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 3), Is.EqualTo(3250));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Handling, 1), Is.EqualTo(1000));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Handling, 3), Is.EqualTo(2750));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Brakes, 1), Is.EqualTo(750));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Brakes, 2), Is.EqualTo(1250));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Brakes, 3), Is.EqualTo(2000));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 0), Is.EqualTo(-1));
            Assert.That(EconomyPrices.VanTierPrice(VanBranch.Engine, 4), Is.EqualTo(-1));
            Assert.That(EconomyPrices.VanBranchTotal(VanBranch.Engine), Is.EqualTo(7000));
            Assert.That(EconomyPrices.VanBranchTotal(VanBranch.Handling), Is.EqualTo(5500));
            Assert.That(EconomyPrices.VanBranchTotal(VanBranch.Brakes), Is.EqualTo(4000));
        }

        [Test]
        public void VanTiers_BuyInOrder_AllNine_Cost16500()
        {
            EconomyState s = Funded(16500);
            s.SetWorkshopUnlocked(true);
            foreach (VanBranch b in new[] { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes })
                for (int t = 1; t <= 3; t++)
                {
                    PurchaseResult r = s.TryBuyVanTier(b, t, VanShopCheck.Ready);
                    Assert.That(r.Ok && !r.Replayed, Is.True, b + " " + t + ": " + r.Message);
                    Assert.That(s.VanTier(b), Is.EqualTo(t));
                }
            Assert.That(s.Fund.Balance, Is.EqualTo(0));
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 4, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.AlreadyMax));
        }

        [Test]
        public void VanTiers_NoSkipping_BranchesIndependent()
        {
            EconomyState s = Funded(10000);
            s.SetWorkshopUnlocked(true);
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 2, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.TierChanged));
            Assert.That(s.Fund.Balance, Is.EqualTo(10000));
            Assert.That(s.TryBuyVanTier(VanBranch.Brakes, 1, VanShopCheck.Ready).Ok, Is.True);
            Assert.That(s.VanTier(VanBranch.Brakes), Is.EqualTo(1));
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0));
            Assert.That(s.VanTier(VanBranch.Handling), Is.EqualTo(0));
        }

        [Test]
        public void VanTiers_RepeatedRequest_IsReplayed_NotChargedTwice()
        {
            EconomyState s = Funded(5000);
            s.SetWorkshopUnlocked(true);
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready).Ok, Is.True);
            PurchaseResult again = s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            Assert.That(again.Ok && again.Replayed, Is.True);
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(1));
            Assert.That(s.Fund.Balance, Is.EqualTo(3500));
        }

        [Test]
        public void VanTiers_ServerChecks_RefuseWithoutCharging()
        {
            EconomyState s = Funded(5000);
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.WorkshopLocked));
            s.SetWorkshopUnlocked(true);
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, new VanShopCheck { InZone = false, Handbrake = true, Stopped = true }).Error,
                Is.EqualTo(PurchaseError.VanNotInZone));
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, new VanShopCheck { InZone = true, Handbrake = false, Stopped = true }).Error,
                Is.EqualTo(PurchaseError.HandbrakeOff));
            Assert.That(s.TryBuyVanTier(VanBranch.Engine, 1, new VanShopCheck { InZone = true, Handbrake = true, Stopped = false }).Error,
                Is.EqualTo(PurchaseError.VanMoving));
            Assert.That(s.Fund.Balance, Is.EqualTo(5000));
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0));
        }

        [Test]
        public void VanTiers_NotEnoughMoney_NoPartialPayment()
        {
            EconomyState s = Funded(1499);
            s.SetWorkshopUnlocked(true);
            PurchaseResult r = s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(r.Message, Is.EqualTo("Недостаточно общих денег"));
            Assert.That(s.Fund.Balance, Is.EqualTo(1499));
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0));
        }

        [Test]
        public void VanTiers_SurviveReload_WithoutStacking()
        {
            EconomyState s = Funded(10000);
            s.SetWorkshopUnlocked(true);
            s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            s.TryBuyVanTier(VanBranch.Engine, 2, VanShopCheck.Ready);
            EconomyState a = RoundTrip(s);
            EconomyState b = RoundTrip(a);
            Assert.That(b.VanTier(VanBranch.Engine), Is.EqualTo(2));
            Assert.That(b.WorkshopUnlocked, Is.True);
            Assert.That(b.Fund.Balance, Is.EqualTo(10000 - 1500 - 2250));
            Assert.That(b.TryBuyVanTier(VanBranch.Engine, 2, VanShopCheck.Ready).Replayed, Is.True);
            Assert.That(b.Fund.Balance, Is.EqualTo(10000 - 1500 - 2250));
        }

        [Test]
        public void TwoBuyersAtOnce_OnlyTheFirstFits()
        {
            EconomyState s = Funded(2000);
            s.SetWorkshopUnlocked(true);
            PurchaseResult first = s.TryBuyVanTier(VanBranch.Engine, 1, VanShopCheck.Ready);
            PurchaseResult second = s.TryBuyVanTier(VanBranch.Handling, 1, VanShopCheck.Ready);
            Assert.That(first.Ok, Is.True);
            Assert.That(second.Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(s.Fund.Balance, Is.EqualTo(500));
        }

        // ---------- equipment delivery (§4.1) ----------

        [Test]
        public void Delivery_OneCommit_OneCharge_DueAfterOneGameHour()
        {
            EconomyState s = Funded(3000);
            PurchaseResult r = s.TryOrderEquipment("saw", EconomyPrices.BaseHamlet, 1500, "req-1");
            Assert.That(r.Ok, Is.True, r.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(1500));
            PurchaseResult again = s.TryOrderEquipment("saw", EconomyPrices.BaseHamlet, 1500, "req-1");
            Assert.That(again.Replayed, Is.True);
            Assert.That(again.DeliveryId, Is.EqualTo(r.DeliveryId));
            Assert.That(s.Fund.Balance, Is.EqualTo(1500));
            Assert.That(s.Deliveries.Count, Is.EqualTo(1));
            s.AdvanceWorldTime(0.99);
            Assert.That(s.DueDeliveries(), Is.Empty);
            s.AdvanceWorldTime(0.02);
            Assert.That(s.DueDeliveries().Select(d => d.id), Is.EquivalentTo(new[] { r.DeliveryId }));
        }

        [Test]
        public void Delivery_RequiresOwnedDeliveryBase_AndTheShownPrice()
        {
            EconomyState s = Funded(10000);
            Assert.That(s.TryOrderEquipment("saw", EconomyPrices.BaseRough, 1500, "a").Error, Is.EqualTo(PurchaseError.BaseNotOwned));
            Assert.That(s.TryOrderEquipment("saw", EconomyPrices.BaseWagon, 1500, "b").Error, Is.EqualTo(PurchaseError.BaseNoDelivery));
            Assert.That(s.TryOrderEquipment("saw", EconomyPrices.BaseHamlet, 1400, "c").Error, Is.EqualTo(PurchaseError.PriceChanged));
            Assert.That(s.TryOrderEquipment("nope", EconomyPrices.BaseHamlet, 1, "d").Error, Is.EqualTo(PurchaseError.UnknownItem));
            Assert.That(s.TryOrderEquipment("rare_equipment", EconomyPrices.BaseHamlet, 90000, "e").Error, Is.EqualTo(PurchaseError.ItemUnavailable));
            Assert.That(s.Fund.Balance, Is.EqualTo(10000));
            Assert.That(s.Deliveries, Is.Empty);
        }

        [Test]
        public void Delivery_WaitingOccupiedAnchor_KeepsOrder_AndSurvivesReload()
        {
            EconomyState s = Funded(6000);
            string id = s.TryOrderEquipment("cooler_stationary", EconomyPrices.BaseHamlet, 5000, "req-c").DeliveryId;
            s.AdvanceWorldTime(1.5);
            Assert.That(s.MarkWaiting(id), Is.True);
            EconomyState loaded = RoundTrip(s);
            DeliveryOrder d = loaded.FindDelivery(id);
            Assert.That(d.State, Is.EqualTo(DeliveryState.Waiting));
            Assert.That(loaded.DueDeliveries().Count, Is.EqualTo(1));
            Assert.That(loaded.Fund.Balance, Is.EqualTo(1000));
            Assert.That(loaded.MarkArrived(id, 0, 1f, 2f, 3f, 90f), Is.True);
            EconomyState again = RoundTrip(loaded);
            d = again.FindDelivery(id);
            Assert.That(d.State, Is.EqualTo(DeliveryState.Arrived));
            Assert.That(new[] { d.x, d.y, d.z, d.yaw }, Is.EqualTo(new[] { 1f, 2f, 3f, 90f }));
            Assert.That(again.DueDeliveries(), Is.Empty);
            Assert.That(again.MarkOpened(id, 4f, 5f, 6f, 0f), Is.True);
            Assert.That(again.MarkOpened(id, 4f, 5f, 6f, 0f), Is.False);
            EconomyState third = RoundTrip(again);
            Assert.That(third.FindDelivery(id).State, Is.EqualTo(DeliveryState.Opened));
            Assert.That(third.Fund.Balance, Is.EqualTo(1000));
            Assert.That(third.TryOrderEquipment("cooler_stationary", EconomyPrices.BaseHamlet, 5000, "req-c").Replayed, Is.True);
            Assert.That(third.Fund.Balance, Is.EqualTo(1000));
        }

        [Test]
        public void Delivery_TimerIsWorldTime_AndIdsNeverRepeatAfterReload()
        {
            EconomyState s = Funded(1000);
            string first = s.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r1").DeliveryId;
            s.AdvanceWorldTime(0.5);
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.WorldHours, Is.EqualTo(0.5).Within(1e-9));
            Assert.That(loaded.DueDeliveries(), Is.Empty);
            loaded.AdvanceWorldTime(-5);
            Assert.That(loaded.WorldHours, Is.EqualTo(0.5).Within(1e-9));
            string second = loaded.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r2").DeliveryId;
            Assert.That(second, Is.Not.EqualTo(first));
            loaded.AdvanceWorldTime(0.5);
            Assert.That(loaded.DueDeliveries().Select(d => d.id), Is.EquivalentTo(new[] { first }));
        }

        [Test]
        public void Delivery_SaveWithALaggingCounter_NeverMintsAnExistingId()
        {
            EconomyState s = Funded(1000);
            string first = s.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r1").DeliveryId;
            string second = s.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r2").DeliveryId;
            EconomySaveData data = s.ToSave();
            data.deliverySeq = 0; // partly written / hand-edited save
            EconomyState loaded = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(data)));
            string third = loaded.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r3").DeliveryId;
            Assert.That(third, Is.Not.EqualTo(first).And.Not.EqualTo(second));
            Assert.That(loaded.Deliveries.Select(d => d.id).Distinct().Count(), Is.EqualTo(3));
            Assert.That(loaded.Fund.Balance, Is.EqualTo(700));
        }

        [Test]
        public void Delivery_CannotArriveBeforeTheHour()
        {
            EconomyState s = Funded(1000);
            string id = s.TryOrderEquipment("tray", EconomyPrices.BaseHamlet, 100, "r").DeliveryId;
            Assert.That(s.MarkArrived(id, 0, 0, 0, 0, 0), Is.False);
            Assert.That(s.DevMakeDeliveriesDue(), Is.EqualTo(1));
            Assert.That(s.MarkArrived(id, 0, 0, 0, 0, 0), Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(900));
        }

        // ---------- property (§7.1) ----------

        [Test]
        public void Property_NeedsFirstOrganBuyer_ThenBuysOnce()
        {
            EconomyState s = Funded(40000);
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseRough, 8100).Error, Is.EqualTo(PurchaseError.StoryLocked));
            s.SetFirstOrganBuyerMet(true);
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseDowntown, 33750).Ok, Is.True);
            Assert.That(s.OwnsBase(EconomyPrices.BaseDowntown), Is.True);
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseDowntown, 33750).Replayed, Is.True);
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseHamlet, 0).Error, Is.EqualTo(PurchaseError.AlreadyOwned));
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseRough, 8100).Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(s.Fund.Balance, Is.EqualTo(40000 - 33750));
            Assert.That(RoundTrip(s).OwnsBase(EconomyPrices.BaseDowntown), Is.True);
        }

        [Test]
        public void PropertyPrices_MatchTheSpec()
        {
            Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseRough).Price, Is.EqualTo(8100));
            Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseDowntown).Price, Is.EqualTo(33750));
            Assert.That(EconomyPrices.FindProperty(EconomyPrices.BaseLab).Price, Is.EqualTo(135000));
            Assert.That(EconomyPrices.Properties.Where(p => p.Purchasable).Sum(p => p.Price), Is.EqualTo(176850));
            Assert.That(EconomyPrices.FindEquipment("cooler_portable").Price, Is.EqualTo(1000));
            Assert.That(EconomyPrices.FindEquipment("cooler_stationary").Price, Is.EqualTo(5000));
            Assert.That(EconomyPrices.FindEquipment("saw").Price, Is.EqualTo(1500));
        }
    }
}
