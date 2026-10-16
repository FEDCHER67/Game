using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Buyers
{
    // Append only: enum values are part of saved state. Quality tiers deliberately use 1..5.
    public enum ProductKind { Kidney, Liver, Lungs, Heart, Eye, Brain, BloodBag, IntroSyringe }
    public enum QualityTier { Damaged = 1, Acceptable, Good, Perfect, PerfectPlus }
    public enum NegotiationPhase { Open, CounterOffered, Agreed, Failed, Left }
    public enum MeetingPhase { Scheduled, Waiting, Expired, Cancelled, Completed }
    public enum OrderTemplate { HamletKidney, StreamerBrain }
    public enum SaleError { None, InvalidRequest, NotPresent, NotNegotiator, Unavailable, NotReserved,
        MissingItem, AlreadySold, WrongKind, WrongNpc, LowQuality, PackagingRequired, PriceChanged }

    /// <summary>Saved active-world seconds, with time 0 = 00:00. Never supply wall-clock or offline elapsed time.</summary>
    public interface IBuyerClock { long GameSeconds { get; } }
    /// <summary>Each call returns an integer in [0,100). No random calls for invalid asks.</summary>
    public interface IBuyerRandom { int NextPercent(); }

    [Serializable]
    public sealed class NegotiationState
    {
        public ProductKind Kind;
        public string NegotiatorId = "";
        public int AttemptsUsed;
        public int LastAsk;
        public int CounterPercent;
        public int AgreedPercent;
        public NegotiationPhase Phase;
        public NegotiationState Copy() => (NegotiationState)MemberwiseClone();
    }

    [Serializable]
    public sealed class MeetingState
    {
        public string Id = "";
        public string LocationId = "";
        public string NegotiatorId = "";
        public long ArrivalAt;
        public long ExpiresAt;
        public MeetingPhase Phase;
        public bool PenaltyApplied;
        public bool HadSale;
        public bool HadInteraction;
        public ProductKind? ActiveGroup;
        public List<NegotiationState> Negotiations = new List<NegotiationState>();
        public MeetingState Copy()
        {
            var copy = (MeetingState)MemberwiseClone();
            copy.Negotiations = Negotiations.ConvertAll(n => n.Copy());
            return copy;
        }
    }

    [Serializable]
    public sealed class TypeCounter
    {
        public ProductKind Kind;
        public int Units;
        public long BannedUntil;
        public TypeCounter Copy() => (TypeCounter)MemberwiseClone();
    }

    [Serializable]
    public sealed class BuyerState
    {
        public string Id = "";
        public int Respect = 30;
        public bool Introduced;
        public bool BloodSold;
        public long SaturationDay;
        public List<ProductKind> SoldOrganTypes = new List<ProductKind>();
        public List<TypeCounter> Counters = new List<TypeCounter>();
        public MeetingState Meeting;
        public BuyerState Copy()
        {
            var copy = (BuyerState)MemberwiseClone();
            copy.SoldOrganTypes = new List<ProductKind>(SoldOrganTypes);
            copy.Counters = Counters.ConvertAll(c => c.Copy());
            copy.Meeting = Meeting == null ? null : Meeting.Copy();
            return copy;
        }
    }

    /// <summary>A host-owned merchandise projection, not a second physical inventory.
    /// The adapter updates current quality before quotes/confirmation. Cooled delivery is provenance,
    /// independent of current storage and packaging; inspection must not clear it.</summary>
    [Serializable]
    public sealed class BuyerItemState
    {
        public string Id = "";
        public ProductKind Kind;
        public QualityTier Quality = QualityTier.Acceptable;
        public string SourceNpcId = "";
        public string SourceNpcType = "";
        public bool Packaged;
        public bool DeliveredCooled;
        public string HolderId = "";
        public string MeetingId = "";
        public string StashOrderId = "";
        public bool Sold;
        public BuyerItemState Copy() => (BuyerItemState)MemberwiseClone();
    }

    [Serializable]
    public sealed class ParticipantState
    {
        public string Id = "";
        public int NegotiationLevel;
        public long PersonalXp;
        public ParticipantState Copy() => (ParticipantState)MemberwiseClone();
    }

    [Serializable]
    public sealed class SpecialOrderOffer
    {
        public string Id = "";
        public string BuyerId = "";
        public OrderTemplate Template;
        public string SourceNpcId = "";
        public string StashId = "";
        public long BannedUntil;
        public bool Accepted;
        public NegotiationState Negotiation = new NegotiationState();
        public SpecialOrderOffer Copy()
        {
            var copy = (SpecialOrderOffer)MemberwiseClone();
            copy.Negotiation = Negotiation.Copy();
            return copy;
        }
    }

    [Serializable]
    public sealed class SpecialOrderState
    {
        public string Id = "";
        public string BuyerId = "";
        public OrderTemplate Template;
        public string SourceNpcId = "";
        public string StashId = "";
        public long AcceptedAt;
        public long Deadline;
        public int AgreedPercent;
        public bool LatePenaltyApplied;
        public SpecialOrderState Copy() => (SpecialOrderState)MemberwiseClone();
    }

    public sealed class SaleRequest
    {
        public string ConfirmationId = "";
        public string BuyerId = "";
        public string MeetingId = "";
        public string OrderId = "";
        public string NegotiatorId = "";
        public string[] ItemIds = Array.Empty<string>();
        public decimal? ExpectedTotal;
    }

    [Serializable]
    public sealed class SaleResult
    {
        public string ConfirmationId = "";
        public SaleError Error;
        public string ProblemItemId = "";
        public decimal Total;
        public long XpEach;
        public long TeamXp;
        public List<string> SoldItemIds = new List<string>();
        public List<string> Participants = new List<string>();
        public bool Success => Error == SaleError.None;
        public SaleResult Copy()
        {
            var copy = (SaleResult)MemberwiseClone();
            copy.SoldItemIds = new List<string>(SoldItemIds);
            copy.Participants = new List<string>(Participants);
            return copy;
        }
    }

    [Serializable]
    public sealed class WrongItemAttempt
    {
        public string ScopeId = "";
        public bool IsOrder;
        public string ItemId = "";
        public WrongItemAttempt Copy() => (WrongItemAttempt)MemberwiseClone();
    }

    /// <summary>Snapshot DTO. Persist the whole object, including receipts/tombstones; restore with a
    /// clock starting at LastGameSeconds. Only one BuyerRules authority may own a save at a time.</summary>
    [Serializable]
    public sealed class BuyerWorldState
    {
        public long LastGameSeconds;
        public decimal SharedFunds;
        public long LifetimeXp;
        public long FreeXp;
        public bool FirstBloodSold;
        public bool IntroSyringeSold;
        public bool OrganContactUnlocked;
        public bool NextContactUnlocked;
        public bool HasSaw;
        public bool HasDowntownAccess;
        public List<string> PresentParticipants = new List<string>();
        public List<ParticipantState> Participants = new List<ParticipantState>();
        public List<BuyerState> Buyers = new List<BuyerState>();
        public List<BuyerItemState> Items = new List<BuyerItemState>();
        public List<ProductKind> FirstOrganTypes = new List<ProductKind>();
        public List<string> UsedMeetingIds = new List<string>();
        public List<string> OpenStashes = new List<string>();
        public List<OrderTemplate> CompletedOrders = new List<OrderTemplate>();
        public List<SpecialOrderOffer> Offers = new List<SpecialOrderOffer>();
        public SpecialOrderState ActiveOrder;
        public List<WrongItemAttempt> WrongItemAttempts = new List<WrongItemAttempt>();
        public List<SaleResult> Receipts = new List<SaleResult>();

        public BuyerWorldState Copy()
        {
            var copy = (BuyerWorldState)MemberwiseClone();
            copy.PresentParticipants = new List<string>(PresentParticipants);
            copy.Participants = Participants.ConvertAll(p => p.Copy());
            copy.Buyers = Buyers.ConvertAll(b => b.Copy());
            copy.Items = Items.ConvertAll(i => i.Copy());
            copy.FirstOrganTypes = new List<ProductKind>(FirstOrganTypes);
            copy.UsedMeetingIds = new List<string>(UsedMeetingIds);
            copy.OpenStashes = new List<string>(OpenStashes);
            copy.CompletedOrders = new List<OrderTemplate>(CompletedOrders);
            copy.Offers = Offers.ConvertAll(o => o.Copy());
            copy.ActiveOrder = ActiveOrder == null ? null : ActiveOrder.Copy();
            copy.WrongItemAttempts = WrongItemAttempts.ConvertAll(a => a.Copy());
            copy.Receipts = Receipts.ConvertAll(r => r.Copy());
            return copy;
        }
    }
}
