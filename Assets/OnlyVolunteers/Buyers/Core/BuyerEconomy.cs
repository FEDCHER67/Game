using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Buyers
{
    /// <summary>One sale handed to the team economy: money, the sold units (for XP and the first-of-a-kind / first-blood
    /// flags) and who was present, all booked in ONE transaction under <see cref="Key"/>.</summary>
    public sealed class BuyerSaleBooking
    {
        public string Key = "";
        public string Title = "";
        public decimal Amount;
        /// <summary>Every sold unit in sale order (organs count 20 XP, blood 5; the economy adds the once-per-world bonuses).</summary>
        public List<ProductKind> Units = new List<ProductKind>();
        /// <summary>A special order handed in before its deadline: +150 XP each on top of the goods.</summary>
        public bool TimelyOrder;
        /// <summary>Stable ids of the participants present in the session (XP to each of them).</summary>
        public List<string> Participants = new List<string>();
    }

    public struct BuyerBookingResult
    {
        /// <summary>Booked now: money in the fund, XP granted, flags set.</summary>
        public bool Committed;
        /// <summary>This key was booked before: nothing booked again; XpEach / TeamXp are the original grant.</summary>
        public bool Replayed;
        public long XpEach;
        public long TeamXp;
        public bool Ok => Committed || Replayed;
    }

    /// <summary>The legacy money / XP a BuyerWorldState snapshot carried before WP02 (read once by the migration).</summary>
    public sealed class BuyerLegacyProgress
    {
        public decimal SharedFunds;
        public long LifetimeXp;
        public long FreeXp;
        public bool FirstBloodSold;
        public List<ProductKind> FirstOrganTypes = new List<ProductKind>();
        public List<ParticipantLegacy> Participants = new List<ParticipantLegacy>();

        public sealed class ParticipantLegacy
        {
            public string Id = "";
            public long PersonalXp;
            public int NegotiationLevel;
        }

        public bool Empty => SharedFunds == 0 && LifetimeXp == 0 && FreeXp == 0 && !FirstBloodSold && FirstOrganTypes.Count == 0 &&
                             Participants.TrueForAll(p => p.PersonalXp == 0 && p.NegotiationLevel == 0);
    }

    /// <summary>WP02 (CORE_LOOP §3, ECONOMY §3.4, §14.2.1): the team economy as the buyer rules see it. BuyerWorldState keeps
    /// no money or XP of its own: a sale's money, XP and first-of-a-kind / first-blood flags are booked here in one
    /// transaction, the personal bargaining ranks are read and bought here (from the team's free XP). Implemented over
    /// the one EconomyState by OnlyVolunteers.Economy.EconomyBuyerLedger.</summary>
    public interface IBuyerEconomy
    {
        /// <summary>Books one prepared sale. Must not call back into the buyer rules. A booking that does not fit (money
        /// overflow) throws OverflowException and books nothing; a refusal returns !Ok and books nothing.</summary>
        BuyerBookingResult Book(BuyerSaleBooking booking);
        /// <summary>The participant's bought bargaining rank 0..3.</summary>
        int BargainRank(string participantId);
        /// <summary>Buys the next bargaining rank of one participant from the team's FREE XP (500 / 1000 / 2000, in order).
        /// Atomic and idempotent: false when the rank is not the next one or the free XP does not cover it.</summary>
        bool TryBuyBargainRank(string participantId, int nextRank);
        /// <summary>Moves legacy snapshot money / XP / ranks / first flags into the economy exactly once (fixed keys: a
        /// second call with the same data books nothing). Throws when an amount cannot be represented.</summary>
        void MigrateLegacy(BuyerLegacyProgress legacy);
    }
}
