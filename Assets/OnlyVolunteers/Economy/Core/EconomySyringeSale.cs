using System;
using System.Collections.Generic;
using OnlyVolunteers.Inventory;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// The ONE payout adapter of a C01 blood-in-syringe sale (G49 ISyringeSalePayout → ECONOMY §3.1, §5.3, §10.1). It books
    /// money and XP through EconomyState.CommitSale under one key per sold PortionId (never per reusable syringe ItemId),
    /// then hands the next sale record and the item outcome to the owner in the same call, so the fund line, its XP, the
    /// receipt / SoldPortions / first-sale flag and the emptied (or discarded) syringe are all in memory together before the
    /// one save of that commit. A duplicate key (replay, restored receipt, second confirmation) applies the record without
    /// paying or granting XP again. No balance of its own, no second sale API.
    /// </summary>
    public sealed class EconomySyringePayout : ISyringeSalePayout
    {
        public const string KeyPrefix = "sale:c01:portion:";

        private readonly EconomyState state;
        private readonly IList<string> participants;
        private readonly Action<SyringeSalesSave, SyringeInstance> apply;

        public FundResult Last { get; private set; }
        /// <summary>XP each present participant got for the last commit (the original grant for a replay).</summary>
        public int LastXpEach { get; private set; }
        private static readonly OnlyVolunteers.Buyers.ProductKind[] SyringeUnits = { OnlyVolunteers.Buyers.ProductKind.IntroSyringe };

        /// <param name="participants">Stable ids of the present participants (XP each), at least one.</param>
        /// <param name="apply">Stores the next sale record and the item outcome (must not throw).</param>
        public EconomySyringePayout(EconomyState state, IList<string> participants, Action<SyringeSalesSave, SyringeInstance> apply)
        {
            this.state = state ?? throw new ArgumentNullException(nameof(state));
            this.participants = participants ?? Array.Empty<string>();
            this.apply = apply ?? throw new ArgumentNullException(nameof(apply));
        }

        public static string Key(string portionId) => KeyPrefix + portionId;

        public bool TryCommit(SyringeSaleReceipt sale, SyringeSalesSave nextState, SyringeInstance itemAfter)
        {
            if (sale == null || nextState == null || string.IsNullOrEmpty(sale.PortionId) || sale.Amount <= 0) return false;
            string title = "C01: кровь в шприце (порция " + sale.PortionId + ")";
            // WP02: the economy computes the XP from its own world flags (5 per portion, +50 for the world's first blood
            // once, whatever sold it first). The caller syncs the syringe record's flag from the economy before quoting,
            // so the receipt's XpEach normally equals the grant; on a mismatch the economy's grant is what counts.
            SaleCommit commit = state.CommitSale(sale.Amount, "sale", title, Key(sale.PortionId), SyringeUnits, false, participants);
            Last = commit.Fund;
            LastXpEach = commit.XpEach;
            if (!Last.Ok) return false;
            apply(nextState, itemAfter);
            state.CommitTutorialSale("C01 syringe sale " + sale.TransactionId);
            return true;
        }
    }
}
