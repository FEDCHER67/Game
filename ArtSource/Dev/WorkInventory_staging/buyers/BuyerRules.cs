using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Buyers
{
    /// <summary>Pure, deterministic, single-host rules. All public operations serialize on one gate.
    /// Snapshot and input objects are copied; callers never receive live mutable state.
    /// A sale is prepared on a private snapshot and published once, including its receipt.</summary>
    public sealed partial class BuyerRules
    {
        private readonly object gate = new object();
        private readonly IBuyerClock clock;
        private readonly IBuyerRandom random;
        private readonly BuyerTuning tuning;
        private BuyerWorldState state;

        public BuyerRules(IBuyerClock clock, IBuyerRandom random, BuyerWorldState saved = null, BuyerTuning tuning = null)
        {
            this.clock = clock ?? throw new ArgumentNullException(nameof(clock));
            this.random = random ?? throw new ArgumentNullException(nameof(random));
            this.tuning = (tuning ?? new BuyerTuning()).Copy();
            state = saved == null ? new BuyerWorldState() : saved.Copy();
            if (saved == null)
            {
                state.Buyers.Add(new BuyerState { Id = BuyerCatalog.BloodBuyer });
                state.Buyers.Add(new BuyerState { Id = BuyerCatalog.OrganBuyer });
            }
            Synchronize(state);
        }

        public BuyerWorldState Snapshot { get { lock (gate) { Synchronize(state); return state.Copy(); } } }
        public void Tick() { lock (gate) Synchronize(state); }
        private static BuyerState Buyer(BuyerWorldState s, string id) => s.Buyers.Find(b => b.Id == id) ?? throw new ArgumentException("Unknown buyer", nameof(id));
        private static ParticipantState Player(BuyerWorldState s, string id) => s.Participants.Find(p => p.Id == id) ?? throw new ArgumentException("Unknown participant", nameof(id));
        private static BuyerItemState Item(BuyerWorldState s, string id) => s.Items.Find(i => i.Id == id);
        private static bool Present(BuyerWorldState s, string id) => s.PresentParticipants.Contains(id);
        private static void Respect(BuyerState b, int delta) { b.Respect = Math.Max(0, Math.Min(100, b.Respect + delta)); }
        private static bool Active(MeetingState m) => m != null && (m.Phase == MeetingPhase.Scheduled || m.Phase == MeetingPhase.Waiting || m.ActiveGroup.HasValue);
        private static bool Accepts(string buyer, ProductKind kind) => buyer == BuyerCatalog.BloodBuyer ? !BuyerCatalog.IsOrgan(kind) : BuyerCatalog.IsOrgan(kind);
        private static TypeCounter Counter(BuyerState b, ProductKind kind)
        {
            var counter = b.Counters.Find(c => c.Kind == kind);
            if (counter == null) { counter = new TypeCounter { Kind = kind }; b.Counters.Add(counter); }
            return counter;
        }
        private static void ReleaseMeetingItems(BuyerWorldState s, string meetingId)
        {
            foreach (var item in s.Items) if (item.MeetingId == meetingId) item.MeetingId = "";
        }
        private static void ReleaseMeetingType(BuyerWorldState s, string meetingId, ProductKind kind)
        {
            foreach (var item in s.Items) if (item.MeetingId == meetingId && item.Kind == kind) item.MeetingId = "";
        }
        private void Synchronize(BuyerWorldState s)
        {
            long now = clock.GameSeconds;
            if (now < s.LastGameSeconds || now < 0 || now > long.MaxValue - 48 * BuyerCatalog.Hour)
                throw new ArgumentOutOfRangeException(nameof(clock), "Game time must be monotonic active-world seconds.");
            s.LastGameSeconds = now;
            foreach (var buyer in s.Buyers)
            {
                long day = now / BuyerCatalog.Day;
                if (buyer.SaturationDay != day)
                {
                    foreach (var counter in buyer.Counters) counter.Units = 0;
                    buyer.SaturationDay = day;
                }
                var m = buyer.Meeting;
                if (m == null || m.Phase == MeetingPhase.Cancelled || m.Phase == MeetingPhase.Completed) continue;
                // Older snapshots lack HadInteraction, but their negotiations/reservations prove attendance.
                m.HadInteraction |= m.HadSale || m.Negotiations.Count > 0 || s.Items.Exists(i => i.MeetingId == m.Id);
                if (now >= m.ExpiresAt)
                {
                    m.Phase = MeetingPhase.Expired;
                    if (!m.ActiveGroup.HasValue)
                    {
                        if (!m.HadInteraction && !m.PenaltyApplied) { Respect(buyer, -1); m.PenaltyApplied = true; }
                        ReleaseMeetingItems(s, m.Id);
                    }
                }
                else if (now >= m.ArrivalAt) m.Phase = MeetingPhase.Waiting;
            }
            var order = s.ActiveOrder;
            if (order != null && now >= order.Deadline && !order.LatePenaltyApplied)
            {
                Respect(Buyer(s, order.BuyerId), -4);
                order.LatePenaltyApplied = true;
            }
        }

        public void SetPresentParticipants(params string[] ids)
        {
            ids = ids == null ? null : (string[])ids.Clone();
            if (ids == null || ids.Length == 0) throw new ArgumentException("At least one participant is required.", nameof(ids));
            var unique = new HashSet<string>(StringComparer.Ordinal);
            foreach (string id in ids) if (string.IsNullOrWhiteSpace(id) || id == TeamHolderId || !unique.Add(id)) throw new ArgumentException("Distinct nonempty participant IDs required.", nameof(ids));
            lock (gate)
            {
                Synchronize(state);
                state.PresentParticipants = new List<string>(ids);
                foreach (string id in ids) if (!state.Participants.Exists(p => p.Id == id)) state.Participants.Add(new ParticipantState { Id = id });
            }
        }
        public bool IntroduceBuyer(string buyerId)
        {
            lock (gate)
            {
                Synchronize(state);
                var buyer = Buyer(state, buyerId);
                if (buyer.Introduced || !IsAvailable(state, buyerId)) return false;
                buyer.Introduced = true; Respect(buyer, 2); return true;
            }
        }
        private static bool IsAvailable(BuyerWorldState s, string id) => id == BuyerCatalog.BloodBuyer || id == BuyerCatalog.OrganBuyer && s.OrganContactUnlocked;
        public bool IsBuyerAvailable(string id) { lock (gate) { Synchronize(state); return IsAvailable(state, id); } }
        public bool BuyNegotiationUpgrade(string playerId, int nextLevel)
        {
            lock (gate)
            {
                Synchronize(state);
                var player = Player(state, playerId);
                if (!Present(state, playerId) || nextLevel != player.NegotiationLevel + 1 || nextLevel < 1 || nextLevel > 3) return false;
                int cost = BuyerCatalog.UpgradeCost(nextLevel);
                if (state.FreeXp < cost) return false;
                state.FreeXp -= cost; player.NegotiationLevel = nextLevel; return true;
            }
        }
        public void SetProgression(bool hasSaw, bool downtownAccess)
        {
            lock (gate) { Synchronize(state); state.HasSaw = hasSaw; state.HasDowntownAccess = downtownAccess; }
        }

        public bool RegisterItem(BuyerItemState item)
        {
            item = item == null ? null : item.Copy();
            if (item == null || string.IsNullOrWhiteSpace(item.Id) || !Enum.IsDefined(typeof(ProductKind), item.Kind)) return false;
            if (BuyerCatalog.IsOrgan(item.Kind)) BuyerCatalog.TierMultiplier(item.Quality);
            lock (gate)
            {
                Synchronize(state);
                if (Item(state, item.Id) != null || state.RemovedItemIds.Contains(item.Id) || item.Sold || item.MeetingId != "" || item.StashOrderId != "" ||
                    item.HolderId != TeamHolderId && !Present(state, item.HolderId)) return false;
                state.Items.Add(item.Copy()); return true;
            }
        }
        /// <summary>Authoritative operation/storage adapter supplies the actual quality immediately before sale.
        /// Blood ignores this property; this library does not run a second organ-spoilage simulation.</summary>
        public bool UpdateQuality(string itemId, QualityTier quality)
        {
            BuyerCatalog.TierMultiplier(quality);
            lock (gate)
            {
                Synchronize(state);
                var item = Item(state, itemId);
                if (item == null || item.Sold || !BuyerCatalog.IsOrgan(item.Kind) || quality > item.Quality) return false;
                item.Quality = quality; return true;
            }
        }
        public bool ScheduleMeeting(string buyerId, string meetingId, string negotiatorId, string baseId, string[] organLocations)
        {
            organLocations = organLocations == null ? null : (string[])organLocations.Clone();
            lock (gate)
            {
                Synchronize(state);
                var buyer = Buyer(state, buyerId);
                if (!IsAvailable(state, buyerId) || !Present(state, negotiatorId) || string.IsNullOrWhiteSpace(meetingId) ||
                    state.UsedMeetingIds.Contains(meetingId) || Active(buyer.Meeting)) return false;
                string location;
                if (buyerId == BuyerCatalog.BloodBuyer) location = baseId;
                else
                {
                    if (organLocations == null || organLocations.Length == 0 || Array.Exists(organLocations, string.IsNullOrWhiteSpace)) return false;
                    // The same injected RNG selects a fixed authored location; no location reroll on reopen.
                    location = organLocations[Roll() * organLocations.Length / 100];
                }
                if (string.IsNullOrWhiteSpace(location)) return false;
                buyer.Meeting = new MeetingState { Id = meetingId, LocationId = location, NegotiatorId = negotiatorId,
                    ArrivalAt = state.LastGameSeconds + BuyerCatalog.Hour, ExpiresAt = state.LastGameSeconds + 4 * BuyerCatalog.Hour };
                state.UsedMeetingIds.Add(meetingId); return true;
            }
        }
        public bool CancelMeeting(string buyerId)
        {
            lock (gate)
            {
                Synchronize(state);
                var buyer = Buyer(state, buyerId); var m = buyer.Meeting;
                if (EndSuccessfulMeeting(state, m)) return true;
                if (m == null || m.Phase == MeetingPhase.Cancelled || m.Phase == MeetingPhase.Completed || m.Phase == MeetingPhase.Expired && !m.ActiveGroup.HasValue) return false;
                if (state.LastGameSeconds >= m.ArrivalAt && !m.HadInteraction && !m.PenaltyApplied) { Respect(buyer, -1); m.PenaltyApplied = true; }
                m.Phase = MeetingPhase.Cancelled; m.ActiveGroup = null;
                ReleaseMeetingItems(state, m.Id); return true;
            }
        }
        /// <summary>A meeting with a completed sale can end normally, without charging cancellation.</summary>
        public bool CompleteMeeting(string buyerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                return EndSuccessfulMeeting(state, m);
            }
        }
        private static bool EndSuccessfulMeeting(BuyerWorldState s, MeetingState m)
        {
            if (m == null || !m.HadSale || m.Phase != MeetingPhase.Waiting && m.Phase != MeetingPhase.Expired) return false;
            m.Phase = MeetingPhase.Completed; m.ActiveGroup = null; ReleaseMeetingItems(s, m.Id); return true;
        }
        /// <summary>The host reports a present participant reaching the buyer before the wait expires.
        /// Starting a group or loading accepted goods also records interaction automatically.</summary>
        public bool RecordMeetingAttendance(string buyerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                if (m == null || m.Phase != MeetingPhase.Waiting || !Present(state, playerId)) return false;
                m.HadInteraction = true; return true;
            }
        }
        public bool BeginGroup(string buyerId, ProductKind kind, string negotiatorId)
        {
            lock (gate)
            {
                Synchronize(state);
                var buyer = Buyer(state, buyerId); var m = buyer.Meeting;
                if (m == null || !Present(state, negotiatorId) || m.NegotiatorId != negotiatorId || !Accepts(buyerId, kind)) return false;
                if (m.ActiveGroup.HasValue) return m.ActiveGroup == kind;
                if (m.Phase != MeetingPhase.Waiting || Counter(buyer, kind).BannedUntil > state.LastGameSeconds) return false;
                var n = m.Negotiations.Find(x => x.Kind == kind);
                if (n != null && (n.Phase == NegotiationPhase.Failed || n.Phase == NegotiationPhase.Left)) return false;
                if (kind == ProductKind.IntroSyringe && state.IntroSyringeSold) return false;
                if (n == null)
                {
                    n = new NegotiationState { Kind = kind, NegotiatorId = negotiatorId };
                    if (kind == ProductKind.IntroSyringe) n.Phase = NegotiationPhase.Agreed;
                    m.Negotiations.Add(n);
                }
                n.NegotiatorId = negotiatorId; m.ActiveGroup = kind; m.HadInteraction = true; return true;
            }
        }
        public bool FinishGroup(string buyerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                if (m == null || !m.ActiveGroup.HasValue) return false;
                m.ActiveGroup = null; Synchronize(state); return true;
            }
        }
        public bool ChangeNegotiator(string buyerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                if (!Active(m) || !Present(state, playerId)) return false;
                m.NegotiatorId = playerId;
                foreach (var n in m.Negotiations) n.NegotiatorId = playerId;
                return true;
            }
        }
        public bool LoadItem(string buyerId, string itemId, string holderId) => LoadItem(buyerId, itemId, holderId, out _);
        /// <summary>Compatibility overload reports the request error without charging respect.</summary>
        public bool LoadItem(string buyerId, string itemId, string holderId, out SaleError error)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting; var item = Item(state, itemId);
                error = SaleError.InvalidRequest;
                if (!Active(m) || item == null || item.Sold || item.HolderId != holderId || !Present(state, holderId) ||
                    !Accepts(buyerId, item.Kind) || item.StashOrderId != "" || item.MeetingId != "" && item.MeetingId != m.Id) return false;
                item.MeetingId = m.Id; m.HadInteraction = true; error = SaleError.None; return true;
            }
        }

        private int Roll()
        {
            int roll = random.NextPercent();
            if (roll < 0 || roll >= 100) throw new InvalidOperationException("RNG must return [0,100).");
            return roll;
        }
        private bool Ask(BuyerState buyer, NegotiationState n, string playerId, int ask, Action failed)
        {
            if (!Present(state, playerId) || n.NegotiatorId != playerId || n.Kind == ProductKind.IntroSyringe ||
                n.Phase != NegotiationPhase.Open && n.Phase != NegotiationPhase.CounterOffered ||
                n.AttemptsUsed >= 2 || n.AttemptsUsed > 0 && ask >= n.LastAsk || ask != 5 && ask != 10 && ask != 20) return false;
            int chance = BuyerCatalog.NegotiationChance(buyer.Respect, Player(state, playerId).NegotiationLevel, ask);
            bool accepted = Roll() < chance;
            n.AttemptsUsed++; n.LastAsk = ask;
            if (accepted) { n.AgreedPercent = ask; n.Phase = NegotiationPhase.Agreed; }
            else if (n.AttemptsUsed == 1) { n.CounterPercent = tuning.Counter(ask); n.Phase = NegotiationPhase.CounterOffered; }
            else { n.Phase = NegotiationPhase.Failed; Respect(buyer, -1); failed(); }
            return true;
        }
        private static bool AcceptCounter(NegotiationState n, string playerId)
        {
            if (n.NegotiatorId != playerId || n.Phase != NegotiationPhase.Open && n.Phase != NegotiationPhase.CounterOffered) return false;
            n.AgreedPercent = n.Phase == NegotiationPhase.Open ? 0 : n.CounterPercent;
            n.Phase = NegotiationPhase.Agreed; return true;
        }
        public bool AskMeeting(string buyerId, string playerId, int ask)
        {
            lock (gate)
            {
                Synchronize(state); var b = Buyer(state, buyerId); var m = b.Meeting;
                if (m == null || !m.ActiveGroup.HasValue) return false;
                return Ask(b, m.Negotiations.Find(n => n.Kind == m.ActiveGroup.Value), playerId, ask,
                    () => {
                        ProductKind kind = m.ActiveGroup.Value;
                        Counter(b, kind).BannedUntil = state.LastGameSeconds + 3 * BuyerCatalog.Hour;
                        ReleaseMeetingType(state, m.Id, kind); m.ActiveGroup = null;
                    });
            }
        }
        public bool AcceptMeetingPrice(string buyerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                return m != null && m.ActiveGroup.HasValue && Present(state, playerId) && AcceptCounter(m.Negotiations.Find(n => n.Kind == m.ActiveGroup.Value), playerId);
            }
        }
        public bool LeaveNegotiation(string buyerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var m = Buyer(state, buyerId).Meeting;
                if (m == null || !m.ActiveGroup.HasValue || m.NegotiatorId != playerId || !Present(state, playerId)) return false;
                var n = m.Negotiations.Find(x => x.Kind == m.ActiveGroup.Value);
                if (n.Phase != NegotiationPhase.Open && n.Phase != NegotiationPhase.CounterOffered) return false;
                n.Phase = NegotiationPhase.Left; m.ActiveGroup = null; return true;
            }
        }
    }
}
