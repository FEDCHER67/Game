using System.Collections.Generic;

namespace OnlyVolunteers.Economy
{
    /// <summary>One item of the V2 base shop (GEAR armoury of the hangar; Fedya 31.10, plan P1): a team unlock bought once
    /// per world from the shared fund (every player of the team may carry it). Prices are P1 placeholders and say so.</summary>
    public sealed class GearOfferV2
    {
        public string Id = "";
        public string Title = "";
        /// <summary>What it does, in plain facts (the hover line shows it).</summary>
        public string Effect = "";
        public int Price;
        public string PriceNote = "";
    }

    /// <summary>The V2 shop catalogue (P1: the rubber baton only; nothing is sold before its effect works).</summary>
    public static class GearCatalogV2
    {
        public const string Baton = "baton_rubber";
        public const string PlaceholderPrice = "цена предварительная";

        private static readonly GearOfferV2[] Items =
        {
            new GearOfferV2
            {
                Id = Baton, Title = "Резиновая дубинка", Price = 250, PriceNote = PlaceholderPrice,
                Effect = "несмертельная: ЛКМ — удар по голове, валит на 4 с (всегда 4 с, пощёчина слабеет 5/3/2/1); " +
                         "достаёт на 2,8 м (ладонь 2,3 м), но удар раз в 0,9 с; X — достать/убрать",
            },
        };

        public static IReadOnlyList<GearOfferV2> All => Items;

        public static GearOfferV2 Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (GearOfferV2 g in Items) if (g.Id == id) return g;
            return null;
        }
    }

    /// <summary>What the server measured for a shop purchase at the moment of the commit.</summary>
    public struct GearShopCheck
    {
        /// <summary>The buyer stands within the display's reach.</summary>
        public bool InReach;
        /// <summary>A clear line from the buyer's eyes to the item.</summary>
        public bool SightClear;

        public static GearShopCheck Good => new GearShopCheck { InReach = true, SightClear = true };
    }

    public sealed partial class EconomyState
    {
        public static string GearKey(string id) => "gear:" + id;

        /// <summary>The team owns this V2 item. The deterministic charge key is the record: it is saved with the fund
        /// (committedKeys), so a load restores the purchase and a repeated request can never charge twice.</summary>
        public bool OwnsGear(string id) => !string.IsNullOrEmpty(id) && Fund.IsCommitted(GearKey(id));

        /// <summary>Buys one V2 shop item for the team. Checks in order: known item, not owned yet, the buyer at the display
        /// (server measurement), a real price, the price the buyer saw, funds. One commit charges and records ownership
        /// together (key gear:&lt;id&gt;); any refusal charges nothing.</summary>
        public PurchaseResult TryBuyGear(string id, int expectedPrice, GearShopCheck check)
        {
            GearOfferV2 offer = GearCatalogV2.Find(id);
            if (offer == null) return Fail(PurchaseError.UnknownItem);
            if (OwnsGear(id)) return Fail(PurchaseError.AlreadyOwned, offer.Price);
            if (!check.InReach || !check.SightClear)
            {
                PurchaseResult far = Fail(PurchaseError.InvalidRequest, offer.Price);
                far.Message = "Подойди к витрине и наведись на товар";
                return far;
            }
            if (offer.Price <= 0) return Fail(PurchaseError.ItemUnavailable);
            if (expectedPrice != offer.Price) return Fail(PurchaseError.PriceChanged, offer.Price);
            FundResult paid = Fund.TryCharge(offer.Price, "gear", "Снаряжение: " + offer.Title, GearKey(id));
            if (paid.Status == FundStatus.Insufficient) return Fail(PurchaseError.InsufficientFunds, offer.Price);
            if (paid.Status != FundStatus.Committed) return Fail(paid.Replayed ? PurchaseError.AlreadyOwned : PurchaseError.InvalidRequest, offer.Price);
            Changed?.Invoke();
            return Done(offer.Price, "Куплено: " + offer.Title + " (−" + Money(offer.Price) + ")");
        }

        /// <summary>Owned V2 items for the snapshot (clients show the display states from it).</summary>
        private void SnapshotGear(EconomySnapshot s)
        {
            s.gear = new List<string>();
            foreach (GearOfferV2 g in GearCatalogV2.All) if (OwnsGear(g.Id)) s.gear.Add(g.Id);
        }
    }
}
