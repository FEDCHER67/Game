using System;
using System.Collections.Generic;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Economy
{
    /// <summary>One paid cargo-body upgrade of the team van (ECONOMY §6.2 + "Решение Феди 29.10 — удержание пленника").
    /// Prices and prerequisites come from the catalogue (Buyers/Data/Economy_v02.json, refs.requires); nothing is priced
    /// here.</summary>
    public sealed class VanCargoOffer
    {
        /// <summary>Catalogue id = the saved id (EconomySaveData.vanCargo) = the charge key's suffix.</summary>
        public string Id = "";
        public string Title = "";
        public string Effect = "";
        /// <summary>Catalogue refs.requires ("" = none).</summary>
        public string Requires = "";
        /// <summary>-1 = no price (catalogue not loaded / not in this catalogue / open).</summary>
        public int Price = -1;
        /// <summary>False: listed with its price, never sold (UnavailableReason says why).</summary>
        public bool Purchasable;
        public string UnavailableReason = "";
    }

    /// <summary>
    /// The van's cargo-body upgrades (pure): ids, presentation, catalogue lookup and what the bought set means for the bay
    /// (capacity 3 / 4 / 5, straps, padded walls). Bought ids live in EconomyState (server), its save block and the snapshot
    /// every client gets; the runtime turns the set into the van's state (VanCargoFitoutV01) on every machine.
    /// Storage (van_storage, $1 500) is listed but not sold: there is no portable fridge / mounts / locker in the game yet
    /// (VAN_CARGO_CONTAINMENT_RU.md §4).
    /// </summary>
    public static class VanCargo
    {
        public const string Storage = "van_storage";
        public const string Capacity1 = "van_capacity_1";
        public const string Capacity2 = "van_capacity_2";
        public const string Containment1 = "van_containment_1";
        public const string Containment2 = "van_containment_2";
        public const int StockCapacity = 3;
        public const int MaxCapacity = 5;
        public const string KeyPrefix = "van:cargo:";
        public const string StorageUnavailable = "Пока недоступно: нет переносного холодильника и креплений — не продаётся";

        /// <summary>The workshop screen's order (storage last, greyed).</summary>
        public static readonly string[] Ids = { Capacity1, Capacity2, Containment1, Containment2, Storage };

        /// <summary>Deterministic charge key: one purchase per team world whatever the clients send.</summary>
        public static string Key(string id) => KeyPrefix + id;

        public static bool IsKnown(string id) => Array.IndexOf(Ids, id) >= 0;

        public static string Title(string id)
        {
            switch (id)
            {
                case Capacity1: return "Вместимость кузова I";
                case Capacity2: return "Вместимость кузова II";
                case Containment1: return "Фиксаторы кузова";
                case Containment2: return "Мягкий отсек";
                case Storage: return "Система хранения";
                default: return id ?? "";
            }
        }

        public static string Effect(string id)
        {
            switch (id)
            {
                case Capacity1: return "Кузов: 3 → 4 лежачих NPC";
                case Capacity2: return "Кузов: 4 → 5 лежачих NPC";
                case Containment1: return "Рейки в полу, каждый в кузове пристёгнут за пояс/лодыжку (до вместимости): очнувшийся не выберется; руки свободны — стучать может; выгрузка как обычно";
                case Containment2: return "Мягкие панели: пленник не стучит по стенам — ни анимации, ни звука; крики, свидетели и полиция как прежде";
                case Storage: return "Закрытый отсек на 12 мест и крепления двух переносных холодильников";
                default: return "";
            }
        }

        /// <summary>The offer as the bound catalogue prices it (null for an unknown id).</summary>
        public static VanCargoOffer Find(string id)
        {
            if (!IsKnown(id)) return null;
            var offer = new VanCargoOffer { Id = id, Title = Title(id), Effect = Effect(id), Price = EconomyPrices.Whole(id) };
            EconomyCatalog c = EconomyPrices.Catalog;
            string status = "";
            if (c != null)
            {
                try
                {
                    EconomyEntry e = c.Get(id);
                    status = e.Status ?? "";
                    if (e.References.TryGetValue("requires", out string req) && !string.IsNullOrEmpty(req)) offer.Requires = req;
                    if (e.References.TryGetValue("title_ru", out string title) && !string.IsNullOrEmpty(title)) offer.Title = title;
                }
                catch (Exception) { status = ""; }
            }
            if (c == null) offer.UnavailableReason = EconomyPrices.NotLoadedReason;
            else if (id == Storage) offer.UnavailableReason = StorageUnavailable;
            else if (offer.Price <= 0 || status != "confirmed") offer.UnavailableReason = "Цена в каталоге не назначена";
            offer.Purchasable = offer.UnavailableReason.Length == 0;
            return offer;
        }

        public static bool Owns(IEnumerable<string> owned, string id)
        {
            if (owned == null) return false;
            foreach (string o in owned) if (o == id) return true;
            return false;
        }

        /// <summary>Lying NPCs the bay takes: 3, +1 per capacity step, at most 5.</summary>
        public static int Capacity(IEnumerable<string> owned)
        {
            int n = StockCapacity + (Owns(owned, Capacity1) ? 1 : 0) + (Owns(owned, Capacity2) ? 1 : 0);
            return Math.Min(MaxCapacity, n);
        }

        /// <summary>Containment I: floor rails, loaded NPCs strapped up to the capacity.</summary>
        public static bool Restraints(IEnumerable<string> owned) => Owns(owned, Containment1);

        /// <summary>Containment II: padded walls (no knocking).</summary>
        public static bool Padded(IEnumerable<string> owned) => Owns(owned, Containment2);
    }

    /// <summary>The cargo-body purchases of the team world (server, committed with the fund in one call; saved in
    /// EconomySaveData.vanCargo, sent in EconomySnapshot.vanCargo).</summary>
    public sealed partial class EconomyState
    {
        private readonly List<string> vanCargo = new List<string>();

        /// <summary>Bought cargo-body upgrade ids, in purchase order.</summary>
        public IReadOnlyList<string> VanCargoOwned => vanCargo;
        public bool OwnsVanCargo(string id) => vanCargo.Contains(id);
        /// <summary>The bay's capacity from the paid steps (3 / 4 / 5).</summary>
        public int VanCapacity => VanCargo.Capacity(vanCargo);

        /// <summary>Buys one cargo-body upgrade (§6.2, §6.3). expectedPrice = the price the buyer saw: the server checks it
        /// against the catalogue. Same gates as the van tiers (workshop open, no legacy debug profile, van in the zone, on
        /// the handbrake, standing), plus the catalogue prerequisite; storage is never sold. Deterministic key
        /// van:cargo:&lt;id&gt;: bought once per team world, a repeat answers "already" without a second charge.</summary>
        public PurchaseResult TryBuyVanCargo(string id, int expectedPrice, VanShopCheck check)
        {
            VanCargoOffer offer = VanCargo.Find(id);
            if (offer == null) return Fail(PurchaseError.UnknownItem);
            if (vanCargo.Contains(offer.Id))
                return Fund.IsCommitted(VanCargo.Key(offer.Id)) ? Replay(offer.Price, "Уже установлено: " + offer.Title) : Fail(PurchaseError.AlreadyOwned);
            if (!WorkshopUnlocked) return Fail(PurchaseError.WorkshopLocked);
            if (VanLegacyDebugProfile) return Fail(PurchaseError.LegacyDebugProfile);
            if (!check.InZone) return Fail(PurchaseError.VanNotInZone);
            if (!check.Handbrake) return Fail(PurchaseError.HandbrakeOff);
            if (!check.Stopped) return Fail(PurchaseError.VanMoving);
            if (!offer.Purchasable)
            {
                PurchaseResult no = Fail(PurchaseError.ItemUnavailable, offer.Price);
                no.Message = offer.UnavailableReason;
                return no;
            }
            if (offer.Requires.Length > 0 && !vanCargo.Contains(offer.Requires))
            {
                PurchaseResult first = Fail(PurchaseError.RequiresUpgrade, offer.Price);
                first.Message = "Сначала нужно: " + VanCargo.Title(offer.Requires);
                return first;
            }
            if (expectedPrice != offer.Price) return Fail(PurchaseError.PriceChanged, offer.Price);
            FundResult paid = Fund.TryCharge(offer.Price, "van", "Мастерская: " + offer.Title, VanCargo.Key(offer.Id));
            if (paid.Status == FundStatus.Insufficient) return Fail(PurchaseError.InsufficientFunds, offer.Price);
            if (!paid.Ok) return Fail(PurchaseError.InvalidRequest, offer.Price);
            vanCargo.Add(offer.Id);
            Changed?.Invoke();
            return Done(offer.Price, "Установлено: " + offer.Title + " (−" + Money(offer.Price) + ")");
        }

        private void WriteVanCargo(EconomySaveData data) => data.vanCargo = new List<string>(vanCargo);

        /// <summary>A save restores exactly what was bought (an older block has none: nothing is granted).</summary>
        private void ReadVanCargo(EconomySaveData data)
        {
            vanCargo.Clear();
            if (data.vanCargo == null) return;
            foreach (string id in data.vanCargo)
                if (!string.IsNullOrEmpty(id) && id.Length <= 64 && !vanCargo.Contains(id)) vanCargo.Add(id);
        }

        private void SnapshotVanCargo(EconomySnapshot s) => s.vanCargo = new List<string>(vanCargo);
    }
}
