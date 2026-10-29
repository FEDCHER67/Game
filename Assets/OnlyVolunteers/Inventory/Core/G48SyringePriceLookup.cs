using System;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Inventory
{
    /// <summary>One read from G48. C01 aliases retain the IDs agreed in the G49 brief.</summary>
    public sealed class G48SyringePriceLookup : ISyringePriceLookup
    {
        private readonly EconomyCatalog catalog;
        public G48SyringePriceLookup(EconomyCatalog catalog) { this.catalog = catalog ?? throw new ArgumentNullException(nameof(catalog)); }
        public bool TryGetPrice(string id, out int dollars)
        {
            string dataId = id == "c01_blood_first" ? "blood_syringe_first" : id == "c01_blood_repeat" ? "blood_syringe_repeat" : id;
            dollars = 0;
            if (!catalog.TryGetPrice(dataId, out decimal price)) return false;
            if (price != decimal.Truncate(price)) throw new InvalidOperationException("Syringe price must be whole dollars");
            dollars = checked((int)price); return true;
        }
    }
}
