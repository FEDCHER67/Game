using System;
using OnlyVolunteers.Buyers;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// Points at the ONE economy data file, G53's Buyers/Data/Economy_v02.json (a plain TextAsset, not moved or copied),
    /// from a Resources asset so editor and builds load it the same way. Ensure() is the bootstrap of the price source
    /// (called by TeamEconomy.Ensure and lazily by UI): it parses the catalogue once, binds EconomyPrices (van tiers,
    /// bases, equipment, consumables, delivery time) and BuyerCatalog.SyringePrices (G49 aliases c01_blood_first/repeat ->
    /// blood_syringe_first/repeat). A missing or unreadable file binds an always-unavailable lookup: prices are then
    /// refused with a reason, never taken from a temporary fallback.
    /// </summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Economy Catalog Source", fileName = "EconomyCatalogSource")]
    public sealed class EconomyCatalogSource : ScriptableObject
    {
        public const string ResourcePath = "EconomyCatalogSource";

        [Tooltip("Buyers/Data/Economy_v02.json (G53).")]
        public TextAsset Json;

        private static EconomyCatalog loaded;
        private static bool tried;

        public static EconomyCatalog Catalog => loaded;
        public static string Error { get; private set; } = "";

        /// <summary>Loads once and (re)binds both price consumers; returns the catalogue or null when unavailable.</summary>
        public static EconomyCatalog Ensure()
        {
            if (!tried)
            {
                tried = true;
                try
                {
                    var source = Resources.Load<EconomyCatalogSource>(ResourcePath);
                    if (source == null || source.Json == null) Error = "Resources/" + ResourcePath + " or its Json is missing";
                    else loaded = BuyerCatalog.LoadEconomy(source.Json.text);
                }
                catch (Exception e) { Error = e.Message; loaded = null; }
                if (loaded != null) Debug.Log($"[ECON] G48 catalogue loaded: {loaded.Id}, {loaded.Entries.Count} entries");
                else Debug.LogError("[ECON] G48 economy catalogue NOT loaded (" + Error + "): prices are unavailable");
            }
            if (EconomyPrices.Catalog != loaded || (loaded == null && EconomyPrices.Bound)) EconomyPrices.Bind(loaded);
            if (!(BuyerCatalog.SyringePrices is G48SyringePriceLookup) || loaded == null)
                BuyerCatalog.SyringePrices = loaded != null ? new G48SyringePriceLookup(loaded) : (ISyringePriceLookup)new Unavailable();
            return loaded;
        }

        private sealed class Unavailable : ISyringePriceLookup
        {
            public bool TryGetPrice(string id, out int dollars) { dollars = 0; return false; }
        }
    }
}
