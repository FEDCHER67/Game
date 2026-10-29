using System.IO;
using NUnit.Framework;
using OnlyVolunteers.Buyers;
using UnityEngine;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>City pharmacy, Fedya 29.10: open every day 08:00 (inclusive) to 20:00 (exclusive); at night the server refuses
    /// every new sale (also from a purchase list opened earlier) and books nothing; public doors stay shut for anybody outside
    /// ("Closed — opens at 8:00") but never lock somebody inside; the staff door never opens for customers; the G53 v02
    /// closing supplies (suture kit, patch) are sold at the catalogue price.</summary>
    public sealed class PharmacyHoursV01Tests
    {
        private EconomyCatalog previous;

        [SetUp]
        public void BindG48() { previous = EconomyPrices.Catalog; EconomyPrices.Bind(EconomyCatalog.Load(EconomyCoreTests.G48Path)); }

        [TearDown] public void Restore() => EconomyPrices.Bind(previous);

        private static EconomyState Funded(int amount)
        {
            EconomyState s = EconomyState.NewGame();
            s.Credit(amount, "test", "test money", "test:pharmacy-hours");
            return s;
        }

        [Test]
        public void Hours_EightInclusive_TwentyExclusive_EveryDay()
        {
            Assert.That(PharmacyHours.IsOpen(7.99), Is.False);
            Assert.That(PharmacyHours.IsOpen(8.0), Is.True, "08:00 inclusive");
            Assert.That(PharmacyHours.IsOpen(13.5), Is.True);
            Assert.That(PharmacyHours.IsOpen(19.999), Is.True);
            Assert.That(PharmacyHours.IsOpen(20.0), Is.False, "20:00 exclusive");
            Assert.That(PharmacyHours.IsOpen(23.9), Is.False);
            Assert.That(PharmacyHours.IsOpen(0.0), Is.False);
            for (int day = 0; day < 7; day++) Assert.That(PharmacyHours.IsOpen(day * 24 + 12.0), Is.True, "no day off: day " + day);
            Assert.That(PharmacyHours.IsOpen(-1.0), Is.True, "no clock yet: open");
            Assert.That(PharmacyHours.IsOpen(double.NaN), Is.True);
            Assert.That(PharmacyHours.HoursUntilOpen(22.0), Is.EqualTo(10.0).Within(1e-9));
            Assert.That(PharmacyHours.HoursUntilOpen(6.5), Is.EqualTo(1.5).Within(1e-9));
            Assert.That(PharmacyHours.HoursUntilOpen(9.0), Is.EqualTo(0.0));
        }

        [Test]
        public void Signs_AreExactlyTheApprovedEnglishTexts()
        {
            Assert.That(PharmacyHours.SignText, Is.EqualTo("Open daily 8:00–20:00"));
            Assert.That(PharmacyHours.ClosedText, Is.EqualTo("Closed — opens at 8:00"));
            Assert.That(PharmacyRules.Explain(PharmacyRefusal.Closed), Is.EqualTo(PharmacyHours.ClosedText));
            string script = Path.Combine(Application.dataPath, "../ArtSource/Buildings/Pharmacy_W86/Scripts/make_labels_v02.py");
            Assume.That(File.Exists(script), "the label atlas script v02 is in ArtSource");
            StringAssert.Contains("Open daily 8:00–20:00", File.ReadAllText(script), "the printed shop-window sheet");
        }

        [Test]
        public void Night_NewSaleRefused_BooksNothing_EvenFromAStaleList_ReplayStillAnswered()
        {
            EconomyState s = Funded(100);
            PharmacyOffer pack = PharmacyRules.Find("zip_tie_pack_4");
            PharmacyPurchase day = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-day", float.MaxValue, 19.5);
            Assert.That(day.Ok && !day.Replayed, day.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(80));

            long seq = s.Fund.Seq;
            // the list was opened at 19:58, the click arrives at 20:00: the server's clock decides
            PharmacyPurchase night = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-night", float.MaxValue, 20.0);
            Assert.That(night.Ok, Is.False);
            Assert.That(night.Refusal, Is.EqualTo(PharmacyRefusal.Closed));
            Assert.That(night.Message, Is.EqualTo(PharmacyHours.ClosedText));
            Assert.That(s.Fund.Balance, Is.EqualTo(80), "nothing charged");
            Assert.That(s.Fund.Seq, Is.EqualTo(seq), "no line booked");
            Assert.That(s.Fund.IsCommitted(night.Key), Is.False, "the same id may be bought in the morning");
            Assert.That(PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-night", float.MaxValue, 3.0).Refusal, Is.EqualTo(PharmacyRefusal.Closed));

            // a resend of the purchase committed before closing time still gets its first answer (not charged again)
            PharmacyPurchase replay = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-day", float.MaxValue, 23.0);
            Assert.That(replay.Ok && replay.Replayed, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(80));

            PharmacyPurchase morning = PharmacyRules.TryBuy(s, pack.CatalogId, pack.Price, "req-night", float.MaxValue, 8.0);
            Assert.That(morning.Ok && !morning.Replayed, morning.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(60));
        }

        [Test]
        public void Doors_LockedFromOutsideAtNight_NeverLockSomebodyIn_StaffDoorNeverForCustomers()
        {
            // public door (street / courtyard rear door)
            Assert.That(PharmacyDoorRules.Request(false, true, false, true), Is.EqualTo(PharmacyDoorAnswer.Allowed), "day, outside: open");
            Assert.That(PharmacyDoorRules.Request(false, false, false, true), Is.EqualTo(PharmacyDoorAnswer.ClosedForNight), "night, outside: locked");
            Assert.That(PharmacyDoorRules.Explain(PharmacyDoorAnswer.ClosedForNight), Is.EqualTo(PharmacyHours.ClosedText));
            Assert.That(PharmacyDoorRules.Request(false, false, true, true), Is.EqualTo(PharmacyDoorAnswer.Allowed), "night, inside: may always leave");
            Assert.That(PharmacyDoorRules.Request(false, false, false, false), Is.EqualTo(PharmacyDoorAnswer.Allowed), "closing a door is always fine");
            // the staff door between the sales floor and the stockroom
            foreach (bool open in new[] { true, false })
                foreach (bool inside in new[] { true, false })
                    Assert.That(PharmacyDoorRules.Request(true, open, inside, true), Is.EqualTo(PharmacyDoorAnswer.StaffOnly));
            // left open after closing time: a public door swings shut by itself, the staff door is handled by its own rule
            Assert.That(PharmacyDoorRules.CloseForNight(false, false, true), Is.True);
            Assert.That(PharmacyDoorRules.CloseForNight(false, true, true), Is.False);
            Assert.That(PharmacyDoorRules.CloseForNight(true, false, true), Is.False);
        }

        [Test]
        public void ClientWithoutRoom_IsRefusedBeforeCharging()
        {
            // the server measures room in the REQUESTER's holder; no room (or no holder) = refused, nothing booked
            EconomyState s = Funded(50);
            PharmacyOffer syringe = PharmacyRules.Find("syringe_anaesthesia");
            PharmacyPurchase r = PharmacyRules.TryBuy(s, syringe.CatalogId, syringe.Price, "client-7:req", 0f, 12.0);
            Assert.That(r.Refusal, Is.EqualTo(PharmacyRefusal.NoRoom));
            Assert.That(s.Fund.Balance, Is.EqualTo(50));
            Assert.That(PharmacyRules.Bought(s, syringe.CatalogId), Is.EqualTo(0));
        }

        [Test]
        public void CatalogueV02_SutureKitAndPatch_AreSoldAtTheCataloguePrice_IntoTheTableStock()
        {
            EconomyPrices.Bind(EconomyCatalog.Load(Path.Combine(Application.dataPath, "OnlyVolunteers/Buyers/Data/Economy_v02.json")));
            PharmacyOffer kit = PharmacyRules.Find("suture_kit"), patch = PharmacyRules.Find("patch");
            Assert.That(kit, Is.Not.Null);
            Assert.That(patch, Is.Not.Null);
            Assert.That(kit.Price, Is.EqualTo(5));
            Assert.That(patch.Price, Is.EqualTo(5));
            Assert.That(kit.CardText, Is.EqualTo("Suture Kit — $5 each"));
            Assert.That(patch.CardText, Is.EqualTo("Patch — $5 each"));
            Assert.That(kit.Goods, Is.EqualTo(PharmacyGoods.TableSupply));
            Assert.That(patch.Goods, Is.EqualTo(PharmacyGoods.TableSupply));
            EconomyState s = Funded(12);
            Assert.That(PharmacyRules.TryBuy(s, "suture_kit", 5, "k1", float.MaxValue, 10.0).Ok, Is.True);
            Assert.That(PharmacyRules.TryBuy(s, "patch", 5, "p1", float.MaxValue, 10.0).Ok, Is.True);
            Assert.That(PharmacyRules.TryBuy(s, "patch", 5, "p2", float.MaxValue, 10.0).Refusal, Is.EqualTo(PharmacyRefusal.InsufficientFunds));
            Assert.That(s.Fund.Balance, Is.EqualTo(2));
            // the nine older offers keep their prices with the v02 catalogue
            Assert.That(PharmacyRules.Find("anaesthesia_basic").Price, Is.EqualTo(200));
            Assert.That(PharmacyRules.Find("syringe_blood").Price, Is.EqualTo(2));
        }
    }
}
