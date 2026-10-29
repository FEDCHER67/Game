using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>City pharmacy (Pharmacy_W86, Rough 04-H3): the counter sells the nine G48 consumables at the catalogue price,
    /// charges the shared fund once per request, refuses without money / room / a current price and books nothing then,
    /// and the printed counter cards say exactly what the catalogue charges.</summary>
    public sealed class PharmacyRulesV01Tests
    {
        private EconomyCatalog catalog;

        [OneTimeSetUp]
        public void Load() => catalog = EconomyCatalog.Load(EconomyCoreTests.G48Path);

        [SetUp]
        public void Bind() => EconomyPrices.Bind(catalog);

        private static EconomyState Funded(int amount)
        {
            EconomyState s = EconomyState.NewGame();
            if (amount > 0) s.Credit(amount, "test", "test money", "test:pharmacy-fund");
            return s;
        }

        [Test]
        public void Offers_AreTheNineCatalogueConsumables_PricedFromG48()
        {
            var expected = new Dictionary<string, int>
            {
                ["syringe_blood"] = 2, ["syringe_anaesthesia"] = 2, ["zip_tie"] = 5, ["zip_tie_pack_4"] = 20, ["blood_bag_empty"] = 5,
                ["organ_bag"] = 10, ["body_bag"] = 5, ["trash_bag"] = 5, ["anaesthesia_basic"] = 200,
            };
            Assert.That(PharmacyRules.Offers.Count, Is.EqualTo(11), "nine G48 consumables + the two v02 closing supplies");
            foreach (PharmacyOffer o in PharmacyRules.Offers)
            {
                if (o.Goods == PharmacyGoods.TableSupply)
                {
                    Assert.That(o.Price, Is.EqualTo(-1), o.CatalogId + ": not in the v01 catalogue - no price, cannot be bought");
                    continue;
                }
                Assert.That(expected.ContainsKey(o.CatalogId), o.CatalogId + " is not a pharmacy item");
                Assert.That(o.Price, Is.EqualTo((int)catalog.GetPrice(o.CatalogId)), o.CatalogId + ": price = G48");
                Assert.That(o.Price, Is.EqualTo(expected[o.CatalogId]), o.CatalogId + ": approved price");
                ConsumableOffer c = EconomyPrices.FindConsumable(o.ConsumableId);
                Assert.That(c, Is.Not.Null, o.ConsumableId + ": explicit runtime id of EconomyPrices.Consumables");
                Assert.That(c.CatalogId, Is.EqualTo(o.CatalogId), o.ConsumableId + " maps to " + o.CatalogId);
                StringAssert.Contains("pharmacy", catalog.Get(o.CatalogId).WhereSold ?? "pharmacy", o.CatalogId + ": sold at the pharmacy");
            }
            Assert.That(PharmacyRules.Find("head_bag"), Is.Null, "the head bag belongs to the underground seller");
            Assert.That(PharmacyRules.Find("anaesthesia_improved"), Is.Null, "improved anaesthetic stays unlock-gated");
            Assert.That(PharmacyRules.Find("zip_tie_pack_4").Units, Is.EqualTo(4f));
            Assert.That(PharmacyRules.Find("anaesthesia_basic").Units, Is.EqualTo(PharmacyRules.NominalDosesPerVial));
        }

        [Test]
        public void Purchase_ChargesTheCataloguePriceOnce_ReplayDeliversNothing()
        {
            EconomyState s = Funded(100);
            int changed = 0;
            s.Changed += () => changed++;
            PharmacyOffer pack = PharmacyRules.Find("zip_tie_pack_4");
            PharmacyPurchase first = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-1", float.MaxValue);
            Assert.That(first.Ok && !first.Replayed, first.Message);
            Assert.That(first.Price, Is.EqualTo(20));
            Assert.That(s.Fund.Balance, Is.EqualTo(80));
            Assert.That(changed, Is.EqualTo(1), "one commit -> one save trigger");
            Assert.That(s.Fund.History[s.Fund.History.Count - 1].amount, Is.EqualTo(-20));
            Assert.That(s.Fund.History[s.Fund.History.Count - 1].kind, Is.EqualTo(PharmacyRules.Kind));

            PharmacyPurchase again = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-1", float.MaxValue);
            Assert.That(again.Ok && again.Replayed, "the same request answers with the first outcome");
            Assert.That(s.Fund.Balance, Is.EqualTo(80), "a replay is not charged twice");
            Assert.That(changed, Is.EqualTo(1));
            Assert.That(PharmacyRules.Bought(s, pack.CatalogId), Is.EqualTo(1));

            PharmacyPurchase second = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-2", float.MaxValue);
            Assert.That(second.Ok && !second.Replayed);
            Assert.That(s.Fund.Balance, Is.EqualTo(60), "a new request is a new purchase");
            Assert.That(PharmacyRules.Bought(s, pack.CatalogId), Is.EqualTo(2));
        }

        [Test]
        public void Purchase_InsufficientFunds_IsRefusedAndBooksNothing()
        {
            EconomyState s = Funded(150);
            PharmacyOffer vial = PharmacyRules.Find("anaesthesia_basic");
            long seq = s.Fund.Seq;
            PharmacyPurchase r = PharmacyRules.TryBuy(s, vial.CatalogId, vial.Price, "req-v", float.MaxValue);
            Assert.That(r.Ok, Is.False);
            Assert.That(r.Refusal, Is.EqualTo(PharmacyRefusal.InsufficientFunds));
            Assert.That(s.Fund.Balance, Is.EqualTo(150));
            Assert.That(s.Fund.Seq, Is.EqualTo(seq), "no line booked");
            Assert.That(s.Fund.IsCommitted(r.Key), Is.False, "a refused key may be retried");

            s.Credit(50, "test", "more", "test:more");
            PharmacyPurchase retry = PharmacyRules.TryBuy(s, vial.CatalogId, vial.Price, "req-v", float.MaxValue);
            Assert.That(retry.Ok && !retry.Replayed, retry.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(0), "balance never negative, exactly $200 spent");
        }

        [Test]
        public void Purchase_StalePriceUnknownItemNoRoomOrUnbound_AreRefused()
        {
            EconomyState s = Funded(1000);
            PharmacyOffer syringe = PharmacyRules.Find("syringe_blood");
            Assert.That(PharmacyRules.TryBuy(s, syringe.CatalogId, syringe.Price + 1, "a", 1f).Refusal, Is.EqualTo(PharmacyRefusal.PriceChanged));
            Assert.That(PharmacyRules.TryBuy(s, "head_bag", 10, "b", 1f).Refusal, Is.EqualTo(PharmacyRefusal.UnknownItem));
            Assert.That(PharmacyRules.TryBuy(s, syringe.CatalogId, syringe.Price, "c", 0f).Refusal, Is.EqualTo(PharmacyRefusal.NoRoom), "full hotbar");
            Assert.That(PharmacyRules.TryBuy(s, syringe.CatalogId, syringe.Price, "", 1f).Refusal, Is.EqualTo(PharmacyRefusal.InvalidRequest));
            try
            {
                EconomyPrices.Bind(null);
                Assert.That(PharmacyRules.TryBuy(s, syringe.CatalogId, 2, "d", 1f).Refusal, Is.EqualTo(PharmacyRefusal.NotLoaded), "never a fallback price");
            }
            finally { EconomyPrices.Bind(catalog); }
            Assert.That(s.Fund.Balance, Is.EqualTo(1000), "nothing charged by any refusal");
        }

        [Test]
        public void CounterCards_ShowExactlyWhatTheCatalogueCharges()
        {
            string path = Path.Combine(Application.dataPath, "OnlyVolunteers/Art/Buildings/Pharmacy_W86/Pharmacy_labels_v01_regions.json");
            Assume.That(File.Exists(path), "the pharmacy label regions are imported: " + path);
            var cards = JsonUtility.FromJson<CardFile>(File.ReadAllText(path)).price_cards;
            Assert.That(cards, Is.Not.Null.And.Count.EqualTo(9));
            foreach (Card c in cards)
            {
                PharmacyOffer o = PharmacyRules.Find(c.catalog_key);
                Assert.That(o, Is.Not.Null, c.catalog_key + ": a printed card must be a sold item");
                Assert.That(c.label, Is.EqualTo(o.Title), c.catalog_key + ": card label = shop title");
                Assert.That(c.price, Is.EqualTo(o.PriceText), c.catalog_key + ": card price = G48 price");
                Assert.That(c.unit, Is.EqualTo(o.Unit), c.catalog_key + ": card unit = what one purchase is");
            }
        }

        [System.Serializable] private sealed class CardFile { public List<Card> price_cards; }
        [System.Serializable] private sealed class Card { public string catalog_key; public string label; public string price; public string unit; }
    }
}
