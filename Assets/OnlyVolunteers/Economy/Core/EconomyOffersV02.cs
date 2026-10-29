using System;
using System.Collections.Generic;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Economy
{
    /// <summary>Presentation and saved shop-id mapping for the v02 catalogue. Prices and gates stay in JSON.</summary>
    public static class EconomyOffersV02
    {
        public static string ResolveSavedId(string id) => id == "restraints5" ? "restraints4" : id;

        public static EquipmentOffer[] Equipment(EconomyCatalog catalog, EquipmentOffer[] previous)
        {
            if (catalog == null || catalog.Id != "economy_v02") return previous;
            var offers = new List<EquipmentOffer>(previous);
            var restraints = offers.Find(e => e.CatalogId == "patient_restraints");
            restraints.Id = "restraints4";
            restraints.Title = catalog.GetItem("patient_restraints").Reference("title_ru");
            restraints.Effect = "Четыре крепления стола; не полевые стяжки";
            foreach (string id in new[] { "direct_to_bag", "quick_release", "packing_station" })
            {
                EconomyEntry entry = catalog.GetItem(id);
                string reason = entry.Reference("unavailable_reason_ru");
                offers.Add(new EquipmentOffer
                {
                    Id = id, CatalogId = id, Title = entry.Reference("title_ru"), Effect = entry.EffectNote,
                    Price = EconomyPrices.Whole(id), Available = false, UnavailableReason = reason,
                });
            }
            return offers.ToArray();
        }

        public static ConsumableOffer[] Consumables(EconomyCatalog catalog, ConsumableOffer[] previous)
        {
            if (catalog == null || catalog.Id != "economy_v02") return previous;
            var offers = new List<ConsumableOffer>(previous);
            foreach (string id in new[] { "suture_kit", "patch" })
            {
                EconomyEntry entry = catalog.GetItem(id);
                offers.Add(new ConsumableOffer { Id = id, CatalogId = id, Title = entry.Reference("title_ru"),
                    Where = entry.WhereSold, Price = EconomyPrices.Whole(id) });
            }
            return offers.ToArray();
        }

        public static int RequiredLevel(EquipmentOffer offer)
        {
            EconomyCatalog catalog = EconomyPrices.Catalog;
            if (catalog == null || offer == null) return 1;
            EconomyEntry entry = catalog.GetItem(offer.CatalogId);
            return entry.Numbers.TryGetValue("required_level", out decimal? level) && level.HasValue
                ? checked((int)level.Value) : 1;
        }
    }
}
