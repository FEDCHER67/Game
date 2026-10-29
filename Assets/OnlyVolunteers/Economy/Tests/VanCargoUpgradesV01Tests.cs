using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>Van cargo body (ECONOMY §6.2 + "Решение Феди 29.10 — удержание пленника"): catalogue prices and prerequisites,
    /// capacity 3 / 4 / 5 from the purchases, containment flags, storage never sold, every gate charges nothing, one charge
    /// per world (deterministic key, replay), save / snapshot round trips (old blocks get nothing), the workshop rows and the
    /// mechanic's Poof pipeline (preview charges nothing, the commit runs once).</summary>
    public sealed class VanCargoUpgradesV01Tests
    {
        private const string Host = "host";
        private EconomyCatalog previous;

        [SetUp]
        public void BindV02()
        {
            previous = EconomyPrices.Catalog;
            EconomyPrices.Bind(EconomyCatalog.Load(Path.Combine(Application.dataPath, "OnlyVolunteers/Buyers/Data/Economy_v02.json")));
        }

        [TearDown] public void Restore() => EconomyPrices.Bind(previous);

        private static EconomyState Open(int money)
        {
            EconomyState s = EconomyState.NewGame();
            s.SetWorkshopUnlocked(true);
            if (s.VanLegacyDebugProfile) s.SwitchToProgression();
            if (money > 0) s.Credit(money, "test", "test money", "test:cargo-fund");
            return s;
        }

        private static LiftSession Raised(string owner)
        {
            var l = new LiftSession();
            Assert.That(l.TryStart(owner, LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.None));
            l.Tick(l.SwingSeconds + l.Seconds + 0.1f, false);
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Up));
            return l;
        }

        private static PurchaseResult Buy(EconomyState s, string id) => s.TryBuyVanCargo(id, VanCargo.Find(id).Price, VanShopCheck.Ready);

        // ---------- catalogue ----------

        [TestCase(VanCargo.Capacity1, 2000, "", true)]
        [TestCase(VanCargo.Capacity2, 4000, VanCargo.Capacity1, true)]
        [TestCase(VanCargo.Containment1, 1500, "", true)]
        [TestCase(VanCargo.Containment2, 2500, VanCargo.Containment1, true)]
        [TestCase(VanCargo.Storage, 1500, "", false)]
        public void Offers_PricesAndPrerequisitesFromTheCatalogue(string id, int price, string requires, bool purchasable)
        {
            VanCargoOffer o = VanCargo.Find(id);
            Assert.That(o.Price, Is.EqualTo(price), id);
            Assert.That(o.Requires, Is.EqualTo(requires), id);
            Assert.That(o.Purchasable, Is.EqualTo(purchasable), id);
            Assert.That(o.Title, Is.Not.Empty);
            Assert.That(o.Effect, Is.Not.Empty);
            if (!purchasable) Assert.That(o.UnavailableReason, Does.Contain("Пока недоступно"));
        }

        [Test]
        public void Offers_ContainmentTitlesAreFedyasNames_UnknownIdIsNull()
        {
            Assert.That(VanCargo.Find(VanCargo.Containment1).Title, Is.EqualTo("Фиксаторы кузова"));
            Assert.That(VanCargo.Find(VanCargo.Containment2).Title, Is.EqualTo("Мягкий отсек"));
            Assert.That(VanCargo.Find("van_cage"), Is.Null);
            Assert.That(VanCargo.Key(VanCargo.Containment2), Is.EqualTo("van:cargo:van_containment_2"));
        }

        [Test]
        public void Offers_WithoutTheirCatalogueEntryAreNeverPurchasable()
        {
            EconomyPrices.Bind(EconomyCatalog.Load(EconomyCoreTests.G48Path)); // v01: no containment entries
            Assert.That(VanCargo.Find(VanCargo.Containment1).Purchasable, Is.False);
            EconomyPrices.Bind(null);
            Assert.That(VanCargo.Find(VanCargo.Capacity1).Purchasable, Is.False);
            Assert.That(VanCargo.Find(VanCargo.Capacity1).Price, Is.EqualTo(-1));
        }

        // ---------- what the purchases mean for the bay ----------

        [Test]
        public void Capacity_FollowsThePurchases_3_4_5()
        {
            EconomyState s = Open(100000);
            Assert.That(s.VanCapacity, Is.EqualTo(3));
            Assert.That(Buy(s, VanCargo.Capacity1).Ok, Is.True);
            Assert.That(s.VanCapacity, Is.EqualTo(4));
            Assert.That(Buy(s, VanCargo.Capacity2).Ok, Is.True);
            Assert.That(s.VanCapacity, Is.EqualTo(5));
            EconomySnapshot snap = s.ToSnapshot(5, true);
            Assert.That(VanCargo.Capacity(snap.vanCargo), Is.EqualTo(5), "clients read the same capacity from the snapshot");
            Assert.That(VanCargo.Capacity(null), Is.EqualTo(3));
            Assert.That(VanCargo.Capacity(new[] { VanCargo.Capacity2, VanCargo.Capacity1, VanCargo.Capacity2 }), Is.EqualTo(5), "never above the maximum");
        }

        [Test]
        public void Containment_FlagsFollowThePurchases()
        {
            EconomyState s = Open(100000);
            Assert.That(VanCargo.Restraints(s.VanCargoOwned) || VanCargo.Padded(s.VanCargoOwned), Is.False);
            Assert.That(Buy(s, VanCargo.Containment1).Ok, Is.True);
            Assert.That(VanCargo.Restraints(s.VanCargoOwned), Is.True);
            Assert.That(VanCargo.Padded(s.VanCargoOwned), Is.False, "I alone: hands free, still knocks");
            Assert.That(Buy(s, VanCargo.Containment2).Ok, Is.True);
            EconomySnapshot snap = s.ToSnapshot(5, true);
            Assert.That(VanCargo.Restraints(snap.vanCargo) && VanCargo.Padded(snap.vanCargo), Is.True);
            Assert.That(s.VanCapacity, Is.EqualTo(3), "containment adds no place");
        }

        // ---------- purchase rules ----------

        [Test]
        public void Purchase_ChargesOnce_ARepeatIsAReplay()
        {
            EconomyState s = Open(10000);
            PurchaseResult first = Buy(s, VanCargo.Containment1);
            Assert.That(first.Ok && !first.Replayed, Is.True, first.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(8500));
            Assert.That(s.Fund.IsCommitted(VanCargo.Key(VanCargo.Containment1)), Is.True);
            PurchaseResult again = Buy(s, VanCargo.Containment1);
            Assert.That(again.Ok && again.Replayed, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(8500), "never charged twice");
            Assert.That(s.VanCargoOwned.Count(id => id == VanCargo.Containment1), Is.EqualTo(1));
        }

        [Test]
        public void Purchase_StepsNeedThePreviousOne_NothingCharged()
        {
            EconomyState s = Open(100000);
            PurchaseResult r = Buy(s, VanCargo.Capacity2);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.RequiresUpgrade));
            Assert.That(r.Message, Does.Contain("Вместимость кузова I"));
            r = Buy(s, VanCargo.Containment2);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.RequiresUpgrade));
            Assert.That(r.Message, Does.Contain("Фиксаторы кузова"));
            Assert.That(s.Fund.Balance, Is.EqualTo(100000));
            Assert.That(s.VanCargoOwned, Is.Empty);
        }

        [Test]
        public void Purchase_StorageIsNeverSold()
        {
            EconomyState s = Open(100000);
            PurchaseResult r = s.TryBuyVanCargo(VanCargo.Storage, 1500, VanShopCheck.Ready);
            Assert.That(r.Ok, Is.False);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.ItemUnavailable));
            Assert.That(r.Message, Does.Contain("Пока недоступно"));
            Assert.That(s.Fund.Balance, Is.EqualTo(100000));
            Assert.That(s.OwnsVanCargo(VanCargo.Storage), Is.False);
        }

        [Test]
        public void Purchase_EveryGateRefusesWithoutCharging()
        {
            int price = VanCargo.Find(VanCargo.Capacity1).Price;
            EconomyState locked = EconomyState.NewGame();
            locked.Credit(10000, "test", "fund", "test:locked");
            Assert.That(locked.TryBuyVanCargo(VanCargo.Capacity1, price, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.WorkshopLocked));
            EconomyState legacy = FundMigration.LoadOrMigrate(null, true, 10000);
            legacy.SetWorkshopUnlocked(true);
            Assert.That(legacy.TryBuyVanCargo(VanCargo.Capacity1, price, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.LegacyDebugProfile));

            EconomyState s = Open(10000);
            VanShopCheck c = VanShopCheck.Ready; c.InZone = false;
            Assert.That(s.TryBuyVanCargo(VanCargo.Capacity1, price, c).Error, Is.EqualTo(PurchaseError.VanNotInZone));
            c = VanShopCheck.Ready; c.Handbrake = false;
            Assert.That(s.TryBuyVanCargo(VanCargo.Capacity1, price, c).Error, Is.EqualTo(PurchaseError.HandbrakeOff));
            c = VanShopCheck.Ready; c.Stopped = false;
            Assert.That(s.TryBuyVanCargo(VanCargo.Capacity1, price, c).Error, Is.EqualTo(PurchaseError.VanMoving));
            Assert.That(s.TryBuyVanCargo(VanCargo.Capacity1, price - 1, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.PriceChanged));
            Assert.That(s.TryBuyVanCargo("van_cage", 1, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.UnknownItem));
            Assert.That(s.Fund.Balance, Is.EqualTo(10000));
            Assert.That(locked.Fund.Balance, Is.EqualTo(10000));

            EconomyState poor = Open(1999);
            Assert.That(poor.TryBuyVanCargo(VanCargo.Capacity1, price, VanShopCheck.Ready).Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(poor.Fund.Balance, Is.EqualTo(1999));
            Assert.That(poor.VanCargoOwned, Is.Empty);
        }

        // ---------- save / snapshot ----------

        [Test]
        public void Save_RoundTripKeepsThePurchases_ALoadNeverChargesOrGrants()
        {
            EconomyState s = Open(100000);
            Buy(s, VanCargo.Capacity1);
            Buy(s, VanCargo.Containment1);
            EconomySaveData data = s.ToSave();
            string json = JsonUtility.ToJson(data);
            EconomyState loaded = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(json));
            Assert.That(loaded.VanCargoOwned, Is.EqualTo(new[] { VanCargo.Capacity1, VanCargo.Containment1 }));
            Assert.That(loaded.VanCapacity, Is.EqualTo(4));
            Assert.That(loaded.Fund.Balance, Is.EqualTo(s.Fund.Balance));
            Assert.That(Buy(loaded, VanCargo.Capacity1).Replayed, Is.True, "the key survives the load: no second charge");
            Assert.That(loaded.Fund.Balance, Is.EqualTo(s.Fund.Balance));

            // a block written before the cargo body: the field is absent -> nothing bought
            string old = json.Replace("\"vanCargo\":[\"van_capacity_1\",\"van_containment_1\"],", "");
            Assert.That(old, Is.Not.EqualTo(json), "the test removed the field");
            EconomyState legacy = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(old));
            Assert.That(legacy.VanCargoOwned, Is.Empty);
            Assert.That(legacy.VanCapacity, Is.EqualTo(3));
            var nulled = new EconomySaveData { blockVersion = EconomyState.BlockVersion, vanCargo = null };
            Assert.That(EconomyState.FromSave(nulled).VanCargoOwned, Is.Empty);
        }

        [Test]
        public void Snapshot_JsonCarriesThePurchasesToClients()
        {
            EconomyState s = Open(100000);
            Buy(s, VanCargo.Containment1);
            Buy(s, VanCargo.Containment2);
            EconomySnapshot client = JsonUtility.FromJson<EconomySnapshot>(JsonUtility.ToJson(s.ToSnapshot(5, true)));
            Assert.That(client.OwnsVanCargo(VanCargo.Containment2), Is.True);
            Assert.That(VanCargo.Padded(client.vanCargo), Is.True);
        }

        // ---------- the workshop: rows and the Poof pipeline ----------

        [Test]
        public void Rows_CargoBodyListedWithPrices_StorageGreyed_StepsBlockedUntilTheirPrerequisite()
        {
            EconomyState s = Open(100000);
            List<WorkshopUpgradeRow> rows = WorkshopUpgradeRows.Build(s.ToSnapshot(5, true)).Where(r => r.Kind == WorkshopUpgradeRows.VanCargoKind).ToList();
            Assert.That(rows.Select(r => r.Arg), Is.EqualTo(VanCargo.Ids));
            foreach (WorkshopUpgradeRow r in rows)
            {
                Assert.That(r.Single, Is.True);
                Assert.That(r.Expected, Is.EqualTo(r.NextPrice), "a single purchase sends the price shown");
                Assert.That(r.NextPrice, Is.EqualTo(VanCargo.Find(r.Arg).Price));
            }
            WorkshopUpgradeRow Row(string id) => rows.First(r => r.Arg == id);
            Assert.That(Row(VanCargo.Capacity1).Blocked, Is.Empty);
            Assert.That(Row(VanCargo.Containment1).Blocked, Is.Empty);
            Assert.That(Row(VanCargo.Capacity2).Blocked, Does.Contain("Вместимость кузова I"));
            Assert.That(Row(VanCargo.Containment2).Blocked, Does.Contain("Фиксаторы кузова"));
            Assert.That(Row(VanCargo.Storage).Blocked, Does.Contain("Пока недоступно"));
            Assert.That(Row(VanCargo.Storage).NextPrice, Is.EqualTo(1500), "storage shows its price, greyed");

            Buy(s, VanCargo.Containment1);
            rows = WorkshopUpgradeRows.Build(s.ToSnapshot(5, true)).Where(r => r.Kind == WorkshopUpgradeRows.VanCargoKind).ToList();
            Assert.That(Row(VanCargo.Containment1).AtMax, Is.True);
            Assert.That(Row(VanCargo.Containment1).Blocked, Is.EqualTo("установлено"));
            Assert.That(Row(VanCargo.Containment2).Blocked, Is.Empty);
        }

        [Test]
        public void Workshop_PreviewChargesNothing_ThePoofCommitsOnce()
        {
            EconomyState s = Open(10000);
            LiftSession lift = Raised(Host);
            int price = VanCargo.Find(VanCargo.Capacity1).Price;
            PurchaseResult preview = WorkshopUpgradePreview.CargoUpgrade(s, lift, Host, VanCargo.Capacity1, price, true);
            Assert.That(preview.Ok && !preview.Replayed, Is.True, preview.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(10000), "the preview runs on a copy");
            Assert.That(s.OwnsVanCargo(VanCargo.Capacity1), Is.False);

            var p = new UpgradePerformance();
            Assert.That(p.TryBegin(Host, WorkshopUpgradeRows.VanCargoKind, VanCargo.Capacity1, price), Is.EqualTo(WorkshopRefusal.None));
            Assert.That(p.TryBegin(Host, WorkshopUpgradeRows.VanCargoKind, VanCargo.Capacity1, price), Is.EqualTo(WorkshopRefusal.MechanicBusy), "a second click");
            int commits = 0;
            System.Func<PurchaseResult> commit = () => { commits++; return WorkshopRules.TryBuyVanCargo(s, lift, p.Owner, p.Arg, p.Expected, true); };
            var cues = new List<UpgradeCue>();
            for (int i = 0; i < 400 && p.Busy; i++) cues.Add(p.Tick(0.02f, true, true, commit));
            Assert.That(commits, Is.EqualTo(1));
            Assert.That(cues, Has.Member(UpgradeCue.Poof));
            Assert.That(s.Fund.Balance, Is.EqualTo(10000 - price));
            Assert.That(s.VanCapacity, Is.EqualTo(4));

            // the same selection again: the preview answers "already" (a replay, no performance, nothing charged)
            PurchaseResult again = WorkshopUpgradePreview.CargoUpgrade(s, lift, Host, VanCargo.Capacity1, price, true);
            Assert.That(again.Replayed, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(10000 - price));
        }

        [Test]
        public void Workshop_OnlyTheLiftOwnerWithTheVanUpBuys()
        {
            EconomyState s = Open(10000);
            int price = VanCargo.Find(VanCargo.Containment1).Price;
            Assert.That(WorkshopRules.TryBuyVanCargo(s, new LiftSession(), Host, VanCargo.Containment1, price, true).Ok, Is.False, "no session");
            LiftSession lift = Raised(Host);
            Assert.That(WorkshopRules.TryBuyVanCargo(s, lift, "guest-1", VanCargo.Containment1, price, true).Ok, Is.False, "not the owner");
            Assert.That(WorkshopRules.TryBuyVanCargo(s, lift, Host, VanCargo.Containment1, price, false).Error, Is.EqualTo(PurchaseError.VanNotInZone));
            Assert.That(s.Fund.Balance, Is.EqualTo(10000));
            Assert.That(WorkshopRules.TryBuyVanCargo(s, lift, Host, VanCargo.Containment1, price, true).Ok, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(8500));
        }
    }
}
