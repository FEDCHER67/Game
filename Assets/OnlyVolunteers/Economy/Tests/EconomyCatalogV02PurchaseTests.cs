using System.IO;
using System.Linq;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    public sealed class EconomyCatalogV02PurchaseTests
    {
        private EconomyCatalog previous;
        private EconomyCatalog catalog;
        private static string DataPath(string name) => Path.Combine(Application.dataPath, "OnlyVolunteers/Buyers/Data", name);

        [SetUp]
        public void Bind()
        {
            previous = EconomyPrices.Catalog;
            catalog = EconomyCatalog.Load(DataPath("Economy_v02.json"));
            EconomyPrices.Bind(catalog);
        }

        [TearDown] public void Restore() => EconomyPrices.Bind(previous);

        private static EconomyState Funded(int lifetime = 0, int spent = 0)
        {
            EconomyState s = EconomyState.NewGame();
            s.Credit(100000, "test", "fund", "test:fund");
            if (lifetime > 0) s.CommitSale(1, "test", "XP", "test:xp", "test", lifetime, new[] { "host" });
            if (spent > 0) Assert.That(s.TryBuySkill(EconomyState.SkillBargain, "host", 1).Ok, Is.True);
            return s;
        }

        [Test]
        public void RuntimeResourcePointsAtTheNewFileWithItsOwnGuid()
        {
            string assetPath = "Assets/OnlyVolunteers/Economy/Resources/EconomyCatalogSource.asset";
            var source = AssetDatabase.LoadAssetAtPath<ScriptableObject>(assetPath);
            Assert.That(source, Is.Not.Null);
            var serialized = new SerializedObject(source);
            var json = serialized.FindProperty("Json").objectReferenceValue as TextAsset;
            Assert.That(AssetDatabase.GetAssetPath(json), Is.EqualTo("Assets/OnlyVolunteers/Buyers/Data/Economy_v02.json"));
            Assert.That(EconomyCatalog.FromJson(json.text).Id, Is.EqualTo("economy_v02"));
        }

        [Test]
        public void EveryShopPriceUsesV02_RestraintsAndConsumablesAreMapped()
        {
            foreach (EquipmentOffer offer in EconomyPrices.Equipment)
                Assert.That(offer.Price, Is.EqualTo(catalog.GetPrice(offer.CatalogId)), offer.Id);
            foreach (ConsumableOffer offer in EconomyPrices.Consumables)
                Assert.That(offer.Price, Is.EqualTo(catalog.GetPrice(offer.CatalogId)), offer.Id);
            Assert.That(EconomyPrices.FindEquipment("restraints5"), Is.SameAs(EconomyPrices.FindEquipment("restraints4")));
            Assert.That(EconomyPrices.FindEquipment("restraints4").Title, Does.Contain("четырёх"));
            Assert.That(EconomyPrices.FindConsumable("suture_kit").Price, Is.EqualTo(5));
            Assert.That(EconomyPrices.FindConsumable("patch").Price, Is.EqualTo(5));
        }

        [TestCase("direct_to_bag", 499, 2, false)]
        [TestCase("direct_to_bag", 500, 2, true)]
        [TestCase("quick_release", 1499, 3, false)]
        [TestCase("quick_release", 1500, 3, true)]
        [TestCase("packing_station", 3499, 4, false)]
        [TestCase("packing_station", 3500, 4, true)]
        public void GatesReadTheXpStore_ReservedDevicesRemainUnavailable(string id, int xp, int required, bool atLevel)
        {
            EconomyState s = Funded(xp);
            int balance = s.Fund.Balance;
            long seq = s.Fund.Seq;
            var offer = EconomyPrices.FindEquipment(id);
            Assert.That(EconomyOffersV02.RequiredLevel(offer), Is.EqualTo(required));
            PurchaseResult result = s.TryOrderEquipment(id, EconomyPrices.BaseHamlet, offer.Price, "device");
            Assert.That(result.Error, Is.EqualTo(atLevel ? PurchaseError.ItemUnavailable : PurchaseError.LevelLocked));
            Assert.That(result.Message, atLevel ? Does.Contain("не реализована") : Does.Contain("уровень команды " + required));
            Assert.That(s.Fund.Balance, Is.EqualTo(balance));
            Assert.That(s.Fund.Seq, Is.EqualTo(seq));
            Assert.That(s.Deliveries, Is.Empty);
            Assert.That(s.LifetimeXp, Is.EqualTo(xp));
            Assert.That(s.Fund.IsCommitted(EconomyState.EquipmentKey("device")), Is.False);
        }

        [TestCase("direct_to_bag", 500)]
        [TestCase("quick_release", 1500)]
        [TestCase("packing_station", 3500)]
        public void ReadyDeviceUsesLifetimeAfterSkillSpendAndReload_OnePaidOrder(string id, int xp)
        {
            // Simulate a future functioning device, independently of its current reserved status.
            var offer = EconomyPrices.FindEquipment(id);
            offer.Available = true;
            offer.UnavailableReason = "";
            EconomyState s = Funded(xp, 500);
            s = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(s.ToSave())));
            int balance = s.Fund.Balance;
            PurchaseResult wrongPrice = s.TryOrderEquipment(id, EconomyPrices.BaseHamlet, 1, "order");
            Assert.That(wrongPrice.Error, Is.EqualTo(PurchaseError.PriceChanged));
            PurchaseResult first = s.TryOrderEquipment(id, EconomyPrices.BaseHamlet, offer.Price, "order");
            Assert.That(first.Ok && !first.Replayed, Is.True, first.Message);
            PurchaseResult replay = s.TryOrderEquipment(id, EconomyPrices.BaseHamlet, offer.Price, "order");
            Assert.That(replay.Ok && replay.Replayed, Is.True);
            Assert.That(replay.DeliveryId, Is.EqualTo(first.DeliveryId));
            Assert.That(s.Fund.Balance, Is.EqualTo(balance - offer.Price));
            Assert.That(s.FreeXp, Is.EqualTo(xp - 500));
            Assert.That(s.LifetimeXp, Is.EqualTo(xp));
            Assert.That(s.Deliveries.Count, Is.EqualTo(1));
        }

        [TestCase(0)] [TestCase(1)] [TestCase(2)] [TestCase(3)]
        public void V01SavedRestraintsMigrateInEveryDeliveryState_WithoutRepayment(int state)
        {
            EconomyPrices.Bind(EconomyCatalog.Load(DataPath("Economy_v01.json")));
            EconomyState old = Funded();
            PurchaseResult paid = old.TryOrderEquipment("restraints5", EconomyPrices.BaseHamlet, 500, "old");
            Assert.That(paid.Ok, Is.True);
            EconomySaveData save = old.ToSave();
            save.deliveries[0].state = state;
            EconomyPrices.Bind(catalog);
            EconomyState s = EconomyState.FromSave(save);
            Assert.That(save.deliveries[0].itemId, Is.EqualTo("restraints5"), "input save is not mutated");
            Assert.That(s.Deliveries.Single().itemId, Is.EqualTo("restraints4"));
            Assert.That(s.Deliveries.Single().state, Is.EqualTo(state));
            Assert.That(s.Fund.Balance, Is.EqualTo(old.Fund.Balance));
            Assert.That(s.Fund.Seq, Is.EqualTo(old.Fund.Seq));
            Assert.That(s.TryOrderEquipment("restraints4", EconomyPrices.BaseHamlet, 500, "old").Replayed, Is.True);
            EconomyState again = EconomyState.FromSave(s.ToSave());
            Assert.That(again.Deliveries.Single().itemId, Is.EqualTo("restraints4"));
            Assert.That(again.Deliveries.Single().id, Is.EqualTo(paid.DeliveryId));
            Assert.That(again.Fund.Balance, Is.EqualTo(old.Fund.Balance));
        }

        [TestCase("restraints5")] [TestCase("restraints4")] [TestCase("knife")]
        public void OrdinaryEquipmentRemainsPurchasableAtLevelOne(string id)
        {
            EconomyState s = Funded();
            var offer = EconomyPrices.FindEquipment(id);
            var result = s.TryOrderEquipment(id, EconomyPrices.BaseHamlet, offer.Price, "ordinary");
            Assert.That(result.Ok, Is.True, result.Message);
            Assert.That(s.Deliveries.Single().itemId, Is.EqualTo(offer.Id));
        }
    }
}
