using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Economy
{
    /// <summary>Where a pharmacy purchase goes on the server (the existing holders of each consumable).</summary>
    public enum PharmacyGoods : byte
    {
        /// <summary>A NEW G49 syringe instance in the buyer's hotbar (inventory capacity applies).</summary>
        BloodSyringe = 0,
        AnaesthesiaSyringe = 1,
        /// <summary>CaptureFieldKit.Ties (saved with the field kit).</summary>
        Ties = 2,
        /// <summary>CaptureCorpseDisposal.Stock (saved as bodyBags).</summary>
        BodyBag = 3,
        /// <summary>CaptureFieldKit.AnesthesiaStock in nominal doses (1.0 = the centre of the suitable range).</summary>
        AnaesthesiaStock = 4,
        /// <summary>No game system uses it yet (empty blood bag, organ bag, trash bag): the team's bought count is read from
        /// the committed pharmacy transaction keys of the fund (saved with the economy block, never cleared).</summary>
        TeamSupply = 5,
        /// <summary>The operating table's closing supplies (G53 catalogue v02: suture kit, patch): into the stock of the team's
        /// operating table (OperationWorldState.sutureKits / patches, saved with the table).</summary>
        TableSupply = 6,
    }

    /// <summary>One line of the city pharmacy's counter (ECONOMY spec v01 §4 first table). The price is never stored here:
    /// it is read from the ONE price accessor (EconomyPrices / G48) through the explicit consumable id mapping.</summary>
    public sealed class PharmacyOffer
    {
        /// <summary>G48 catalogue key (Buyers/Data/Economy_v01.json), also the counter card's catalog_key.</summary>
        public string CatalogId;
        /// <summary>The saved economy id of EconomyPrices.Consumables (syringe_anesthesia, zip_tie_x4, organ_pack...).</summary>
        public string ConsumableId;
        /// <summary>English display name = the printed counter card.</summary>
        public string Title;
        /// <summary>The card's unit text: "each", "/ pack", "/ vial".</summary>
        public string Unit;
        /// <summary>What one purchase delivers into its holder (4 ties for the pack, 10 nominal doses for a vial).</summary>
        public float Units;
        public PharmacyGoods Goods;

        /// <summary>Whole-dollar G48 price through EconomyPrices; -1 when the catalogue is not bound / the value is open.</summary>
        public int Price
        {
            get
            {
                ConsumableOffer c = EconomyPrices.FindConsumable(ConsumableId);
                return c != null && c.CatalogId == CatalogId ? c.Price : -1;
            }
        }

        public string PriceText => PharmacyRules.Money(Price);
        /// <summary>"Blood Syringe — $2 each", "Cable Ties — Pack of 4 — $20 / pack".</summary>
        public string CardText => Title + " — " + PriceText + " " + Unit;
    }

    public enum PharmacyRefusal
    {
        None, InvalidRequest, NotLoaded, UnknownItem, PriceChanged, NoRoom, InsufficientFunds,
        /// <summary>Outside the opening hours (PharmacyHours): the counter sells nothing, even to a purchase list opened earlier.</summary>
        Closed,
    }

    /// <summary>
    /// Opening hours of the city pharmacy (Fedya 29.10): every day 08:00 inclusive to 20:00 exclusive, no day off. The hour is
    /// the server's game clock (sky clock / saved calendar); an unknown hour (no clock yet) counts as open. The printed
    /// shop-window sheet (Pharmacy_labels_v02 info_sheet) and the night message use exactly <see cref="SignText"/> and
    /// <see cref="ClosedText"/>.
    /// </summary>
    public static class PharmacyHours
    {
        public const double OpenHour = 8.0, CloseHour = 20.0;
        public const string SignText = "Open daily 8:00–20:00";
        public const string ClosedText = "Closed — opens at 8:00";

        public static bool IsOpen(double hourOfDay)
        {
            if (double.IsNaN(hourOfDay) || double.IsInfinity(hourOfDay) || hourOfDay < 0.0) return true;
            double h = hourOfDay % 24.0;
            return h >= OpenHour && h < CloseHour;
        }

        /// <summary>Game hours until the next 08:00 (0 while open).</summary>
        public static double HoursUntilOpen(double hourOfDay)
        {
            if (IsOpen(hourOfDay)) return 0.0;
            double h = hourOfDay % 24.0;
            return h < OpenHour ? OpenHour - h : 24.0 - h + OpenHour;
        }
    }

    /// <summary>What a player's E on a pharmacy door gets (the server decides; staff pass through Hold, not through this).</summary>
    public enum PharmacyDoorAnswer : byte
    {
        Allowed = 0,
        /// <summary>The staff door between the sales floor and the stockroom: never for customers.</summary>
        StaffOnly = 1,
        /// <summary>A public door (street / courtyard) at night, seen from outside: "Closed — opens at 8:00".</summary>
        ClosedForNight = 2,
    }

    /// <summary>Door rules of the pharmacy (pure): public doors work during the opening hours; at night they stay shut for
    /// anybody outside, while somebody still inside can always open them to leave (nobody is ever locked in at closing).
    /// Closing an open door is always allowed. The staff-only door never opens for customers.</summary>
    public static class PharmacyDoorRules
    {
        public static PharmacyDoorAnswer Request(bool staffOnly, bool shopOpen, bool actorInside, bool wantOpen)
        {
            if (staffOnly) return PharmacyDoorAnswer.StaffOnly;
            if (!wantOpen || shopOpen || actorInside) return PharmacyDoorAnswer.Allowed;
            return PharmacyDoorAnswer.ClosedForNight;
        }

        /// <summary>A public door left open after closing time swings shut by itself (once its sweep is clear).</summary>
        public static bool CloseForNight(bool staffOnly, bool shopOpen, bool doorOpen) => !staffOnly && !shopOpen && doorOpen;

        public static string Explain(PharmacyDoorAnswer a) =>
            a == PharmacyDoorAnswer.StaffOnly ? "STAFF ONLY: дверь заперта (склад — со двора)" :
            a == PharmacyDoorAnswer.ClosedForNight ? PharmacyHours.ClosedText : "";
    }

    public struct PharmacyPurchase
    {
        public bool Ok;
        /// <summary>The same request id was already committed: nothing is charged or delivered again.</summary>
        public bool Replayed;
        public PharmacyRefusal Refusal;
        public int Price;
        public int Balance;
        public string Key;
        public string Message;
    }

    /// <summary>
    /// The city pharmacy's counter (Rough 04-H3, Pharmacy_W86): nine G48 consumables, bought singly (ties also as the pack of
    /// four, same unit price). Pure rules on the server's EconomyState: the price is the G48 value (the client's shown
    /// price must match it, else "price changed"), the room the server measured for the goods must fit the purchase, the
    /// shared fund is charged once per request id (FundLedger key "pharmacy:&lt;catalog key&gt;:&lt;request id&gt;": a replay
    /// answers with the first outcome and delivers nothing), a refusal books nothing. Delivery into the holders is the
    /// caller's job, done only for a fresh commit (Ok and not Replayed).
    /// </summary>
    public static class PharmacyRules
    {
        public const string Kind = "pharmacy";
        public const string KeyPrefix = "pharmacy:";
        /// <summary>ECONOMY §4: a basic vial is "about ten nominal uses" (OperationTuning units: 1.0 = one suitable dose).</summary>
        public const float NominalDosesPerVial = 10f;

        private static PharmacyOffer O(string key, string id, string title, string unit, float units, PharmacyGoods goods) =>
            new PharmacyOffer { CatalogId = key, ConsumableId = id, Title = title, Unit = unit, Units = units, Goods = goods };

        /// <summary>In the order of the counter cards (left to right seen from the customer: the pharmacy's
        /// Pharmacy_W86_anchors_v01.json price_cards), then the catalogue v02 closing supplies (no card). Improved / late
        /// anaesthetic stay unlock-gated: not sold here.</summary>
        public static readonly IReadOnlyList<PharmacyOffer> Offers = new[]
        {
            O("syringe_blood", "syringe_blood", "Blood Syringe", "each", 1f, PharmacyGoods.BloodSyringe),
            O("syringe_anaesthesia", "syringe_anesthesia", "Empty Anesthetic Syringe", "each", 1f, PharmacyGoods.AnaesthesiaSyringe),
            O("zip_tie", "zip_tie", "Cable Tie", "each", 1f, PharmacyGoods.Ties),
            O("zip_tie_pack_4", "zip_tie_x4", "Cable Ties — Pack of 4", "/ pack", 4f, PharmacyGoods.Ties),
            O("blood_bag_empty", "blood_bag_empty", "Empty Blood Bag", "each", 1f, PharmacyGoods.TeamSupply),
            O("organ_bag", "organ_pack", "Organ Bag", "each", 1f, PharmacyGoods.TeamSupply),
            O("body_bag", "body_bag", "Body Bag", "each", 1f, PharmacyGoods.BodyBag),
            O("trash_bag", "trash_bag", "Trash Bag", "each", 1f, PharmacyGoods.TeamSupply),
            O("anaesthesia_basic", "anesthesia_basic", "Basic Anesthetic", "/ vial", NominalDosesPerVial, PharmacyGoods.AnaesthesiaStock),
            // G53 catalogue v02 (Economy_v02.json): the closing supplies, sold at the pharmacy; no printed counter card, so they
            // are listed on the counter's purchase list only. With an older catalogue bound they have no price and cannot be bought.
            O("suture_kit", "suture_kit", "Suture Kit", "each", 1f, PharmacyGoods.TableSupply),
            O("patch", "patch", "Patch", "each", 1f, PharmacyGoods.TableSupply),
        };

        public static PharmacyOffer Find(string catalogId)
        {
            if (string.IsNullOrEmpty(catalogId)) return null;
            foreach (PharmacyOffer o in Offers) if (o.CatalogId == catalogId) return o;
            return null;
        }

        public static string Money(int dollars) => dollars < 0 ? "—" : "$" + dollars.ToString("N0", System.Globalization.CultureInfo.InvariantCulture);

        public static string TransactionKey(string catalogId, string requestId) => KeyPrefix + catalogId + ":" + requestId;

        /// <summary>How many of this offer the team has bought (committed pharmacy keys; replays are one key).</summary>
        public static int Bought(EconomyState state, string catalogId)
        {
            if (state == null || string.IsNullOrEmpty(catalogId)) return 0;
            string prefix = KeyPrefix + catalogId + ":";
            int n = 0;
            foreach (string k in state.Fund.CommittedKeys) if (k != null && k.StartsWith(prefix, StringComparison.Ordinal)) n++;
            return n;
        }

        public static string Explain(PharmacyRefusal r)
        {
            switch (r)
            {
                case PharmacyRefusal.None: return "";
                case PharmacyRefusal.NotLoaded: return EconomyPrices.NotLoadedReason;
                case PharmacyRefusal.UnknownItem: return "Такого товара в аптеке нет";
                case PharmacyRefusal.PriceChanged: return "Цена изменилась — проверь карточку";
                case PharmacyRefusal.NoRoom: return "Некуда положить: освободи слот в хотбаре";
                case PharmacyRefusal.InsufficientFunds: return "Недостаточно общих денег";
                case PharmacyRefusal.Closed: return PharmacyHours.ClosedText;
                default: return "Неверный запрос";
            }
        }

        /// <summary>
        /// Server: one purchase of one offer. shownPrice = the price on the buyer's card (must equal the G48 price now);
        /// room = how many units the server found room for (syringes: the hotbar; the field kit / disposal stock / team
        /// supply: unlimited). Order: replay (committed key) first, then catalogue, item, price, room, funds; only then the
        /// fund is charged (EconomyState.Charge -> Changed -> the save owner writes the team save).
        /// </summary>
        public static PharmacyPurchase TryBuy(EconomyState state, string catalogId, int shownPrice, string requestId, float room) =>
            TryBuy(state, catalogId, shownPrice, requestId, room, -1.0);

        /// <summary>The same purchase at a game hour (server clock): outside <see cref="PharmacyHours"/> a NEW request is
        /// refused as Closed and books nothing (also from a purchase list opened before closing time); a request id that was
        /// already committed still answers with its first outcome.</summary>
        public static PharmacyPurchase TryBuy(EconomyState state, string catalogId, int shownPrice, string requestId, float room, double hourOfDay)
        {
            var r = new PharmacyPurchase { Message = "" };
            if (state == null || string.IsNullOrEmpty(requestId) || requestId.Length > 64) return Refuse(r, PharmacyRefusal.InvalidRequest, state);
            PharmacyOffer offer = Find(catalogId);
            if (offer == null) return Refuse(r, PharmacyRefusal.UnknownItem, state);
            r.Key = TransactionKey(offer.CatalogId, requestId);
            if (state.Fund.IsCommitted(r.Key))
            {
                r.Ok = true; r.Replayed = true; r.Price = shownPrice; r.Balance = state.Fund.Balance;
                r.Message = "Уже оплачено";
                return r;
            }
            if (!PharmacyHours.IsOpen(hourOfDay)) return Refuse(r, PharmacyRefusal.Closed, state);
            if (!EconomyPrices.Bound) return Refuse(r, PharmacyRefusal.NotLoaded, state);
            int price = offer.Price;
            r.Price = price;
            if (price <= 0) return Refuse(r, PharmacyRefusal.NotLoaded, state);
            if (shownPrice != price) return Refuse(r, PharmacyRefusal.PriceChanged, state);
            if (room + 1e-4f < offer.Units) return Refuse(r, PharmacyRefusal.NoRoom, state);
            FundResult f = state.Charge(price, Kind, "Pharmacy: " + offer.Title, r.Key);
            r.Balance = f.Balance;
            if (f.Status == FundStatus.Insufficient) return Refuse(r, PharmacyRefusal.InsufficientFunds, state);
            if (!f.Ok) return Refuse(r, PharmacyRefusal.InvalidRequest, state);
            r.Ok = true;
            r.Replayed = f.Replayed;
            r.Message = "Куплено: " + offer.Title + " за " + Money(price);
            return r;
        }

        private static PharmacyPurchase Refuse(PharmacyPurchase r, PharmacyRefusal why, EconomyState state)
        {
            r.Ok = false;
            r.Refusal = why;
            r.Balance = state != null ? state.Fund.Balance : 0;
            r.Message = Explain(why);
            return r;
        }
    }
}
