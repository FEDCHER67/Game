using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Buyers
{
    public sealed partial class BuyerRules
    {
        private static SaleRequest CopyRequest(SaleRequest r) => r == null ? null : new SaleRequest {
            ConfirmationId = r.ConfirmationId, BuyerId = r.BuyerId, MeetingId = r.MeetingId, OrderId = r.OrderId,
            NegotiatorId = r.NegotiatorId, ItemIds = r.ItemIds == null ? null : (string[])r.ItemIds.Clone(), ExpectedTotal = r.ExpectedTotal };
        private static SaleResult Error(SaleRequest r, SaleError error, string item = "") => new SaleResult {
            ConfirmationId = r == null ? "" : r.ConfirmationId, Error = error, ProblemItemId = item };
        private static bool WrongMerchandise(SaleError error) => error == SaleError.WrongKind || error == SaleError.WrongNpc ||
            error == SaleError.LowQuality || error == SaleError.PackagingRequired;
        /// <summary>The economy transaction key of one confirmed sale (one fund line, its XP, its flags).</summary>
        public static string SaleKey(string confirmationId) => "sale:buyers:" + confirmationId;
        private static string SaleTitle(string buyerId, List<BuyerItemState> goods) =>
            (buyerId == BuyerCatalog.BloodBuyer ? "Покупатель крови" : "Скупщик органов") + ": " + goods.Count + " шт. (" + goods[0].Kind + ")";

        private SaleResult BuildQuote(BuyerWorldState s, SaleRequest r, out List<BuyerItemState> goods)
        {
            goods = new List<BuyerItemState>();
            if (r == null || string.IsNullOrWhiteSpace(r.ConfirmationId) || r.ItemIds == null || r.ItemIds.Length == 0 ||
                Array.Exists(r.ItemIds, string.IsNullOrWhiteSpace) || new HashSet<string>(r.ItemIds, StringComparer.Ordinal).Count != r.ItemIds.Length ||
                !s.Buyers.Exists(b => b.Id == r.BuyerId) || r.MeetingId == null || r.OrderId == null || (r.MeetingId == "") == (r.OrderId == ""))
                return Error(r, SaleError.InvalidRequest);
            if (!Present(s, r.NegotiatorId)) return Error(r, SaleError.NotPresent);
            var buyer = Buyer(s, r.BuyerId);
            var order = r.OrderId == "" ? null : s.ActiveOrder;
            var m = buyer.Meeting;
            NegotiationState n = null;
            if (r.OrderId != "")
            {
                if (order == null || order.Id != r.OrderId || order.BuyerId != buyer.Id) return Error(r, SaleError.Unavailable);
                if (r.ItemIds.Length != 1) return Error(r, SaleError.InvalidRequest);
            }
            else
            {
                if (m == null || m.Id != r.MeetingId || !m.ActiveGroup.HasValue || m.Phase == MeetingPhase.Cancelled || m.Phase == MeetingPhase.Completed)
                    return Error(r, SaleError.Unavailable);
                if (m.NegotiatorId != r.NegotiatorId) return Error(r, SaleError.NotNegotiator);
                n = m.Negotiations.Find(x => x.Kind == m.ActiveGroup.Value);
                if (n == null || n.Phase != NegotiationPhase.Agreed || Counter(buyer, n.Kind).BannedUntil > s.LastGameSeconds) return Error(r, SaleError.Unavailable);
            }
            var portionIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (string id in r.ItemIds)
            {
                var item = Item(s, id);
                if (item == null) return Error(r, SaleError.MissingItem, id);
                if (item.Sold) return Error(r, SaleError.AlreadySold, id);
                if (!BuyerCatalog.IsOrgan(item.Kind) && item.BloodPortionId != "" && !portionIds.Add(item.BloodPortionId))
                    return Error(r, SaleError.InvalidRequest, id);
                if (!BuyerCatalog.IsOrgan(item.Kind) && item.BloodPortionId != "" &&
                    s.Items.Exists(other => other.Sold && other.BloodPortionId == item.BloodPortionId))
                    return Error(r, SaleError.AlreadySold, id);
                if (order != null ? item.StashOrderId != order.Id || item.MeetingId != "" : item.MeetingId != m.Id || item.StashOrderId != "")
                    return Error(r, SaleError.NotReserved, id);
                SaleError mismatch = order == null ? (!Accepts(buyer.Id, item.Kind) ? SaleError.WrongKind :
                    item.Kind != n.Kind ? SaleError.InvalidRequest : SaleError.None) : OrderMismatch(order, item);
                if (mismatch != SaleError.None) return Error(r, mismatch, id);
                if (item.Kind == ProductKind.IntroSyringe && r.ItemIds.Length != 1) return Error(r, SaleError.InvalidRequest, id);
                goods.Add(item);
            }
            goods.Sort((a, b) => { int quality = b.Quality.CompareTo(a.Quality); return quality != 0 ? quality : string.CompareOrdinal(a.Id, b.Id); });
            decimal total = 0;
            int units = order != null || !BuyerCatalog.IsOrgan(goods[0].Kind) ? 0 : Counter(buyer, goods[0].Kind).Units;
            foreach (var item in goods)
            {
                total += item.Kind == ProductKind.IntroSyringe
                    ? BuyerCatalog.SyringePrice(s.IntroSyringeSold ? "c01_blood_repeat" : "c01_blood_first")
                    : BuyerCatalog.UnitPrice(item.Kind, item.Quality, order == null ? n.AgreedPercent : order.AgreedPercent,
                    order != null && !order.LatePenaltyApplied, item.DeliveredCooled, units, order != null);
                if (BuyerCatalog.IsOrgan(item.Kind)) units = Math.Min(6, units + 1);
            }
            total = Math.Round(total, tuning.MoneyDecimalPlaces, MidpointRounding.AwayFromZero);
            if (r.ExpectedTotal.HasValue && r.ExpectedTotal.Value != total) return Error(r, SaleError.PriceChanged);
            return new SaleResult { ConfirmationId = r.ConfirmationId, Total = total };
        }
        /// <summary>Recomputed at the current active-world time; never reserves, sells or penalizes goods.</summary>
        public SaleResult Quote(SaleRequest request)
        {
            var r = CopyRequest(request);
            lock (gate) { Synchronize(state); return BuildQuote(state, r, out _); }
        }
        /// <summary>Retrying ANY recorded confirmation ID returns its original result, even after load.
        /// Rejected IDs are final too: retry a corrected request with a fresh ID.</summary>
        public SaleResult ConfirmSale(SaleRequest request)
        {
            var r = CopyRequest(request);
            lock (gate)
            {
                if (r != null && !string.IsNullOrWhiteSpace(r.ConfirmationId))
                {
                    var receipt = state.Receipts.Find(x => x.ConfirmationId == r.ConfirmationId);
                    if (receipt != null) return receipt.Copy();
                }
                var next = state.Copy();
                Synchronize(next);
                var result = BuildQuote(next, r, out var goods);
                if (result.Success)
                {
                    var buyer = Buyer(next, r.BuyerId);
                    var order = r.OrderId == "" ? null : next.ActiveOrder;
                    var booking = new BuyerSaleBooking { Key = SaleKey(r.ConfirmationId), Amount = result.Total, Title = SaleTitle(buyer.Id, goods) };
                    foreach (var item in goods)
                    {
                        booking.Units.Add(item.Kind);
                        if (BuyerCatalog.IsOrgan(item.Kind))
                        {
                            if (!buyer.SoldOrganTypes.Contains(item.Kind)) { buyer.SoldOrganTypes.Add(item.Kind); Respect(buyer, 2); }
                            else Respect(buyer, 1);
                            if (order == null) Counter(buyer, item.Kind).Units = Math.Min(6, Counter(buyer, item.Kind).Units + 1);
                        }
                        else
                        {
                            Respect(buyer, buyer.BloodSold ? 1 : 2); buyer.BloodSold = true;
                            if (item.Kind == ProductKind.IntroSyringe) next.IntroSyringeSold = true;
                            next.OrganContactUnlocked = true;
                        }
                        item.Sold = true; item.MeetingId = ""; item.StashOrderId = "";
                        result.SoldItemIds.Add(item.Id);
                    }
                    if (order != null)
                    {
                        if (!order.LatePenaltyApplied) { Respect(buyer, 5); booking.TimelyOrder = true; next.NextContactUnlocked = true; }
                        if (!next.CompletedOrders.Contains(order.Template)) next.CompletedOrders.Add(order.Template);
                        ReleaseStash(next, order.Id); next.ActiveOrder = null;
                    }
                    else { buyer.Meeting.HadSale = true; buyer.Meeting.ActiveGroup = null; }
                    result.Participants = new List<string>(next.PresentParticipants);
                    booking.Participants = new List<string>(result.Participants);
                    // WP02: money, XP and the first-of-a-kind / first-blood flags are booked in the economy in ONE transaction
                    // before anything here is published. Overflow throws (nothing booked, nothing published); a refusal
                    // publishes nothing either (the goods stay unsold and reserved).
                    BuyerBookingResult booked = economy.Book(booking);
                    if (!booked.Ok) return Error(r, SaleError.PaymentRefused);
                    result.XpEach = booked.XpEach;
                    result.TeamXp = booked.TeamXp;
                }
                else if (WrongMerchandise(result.Error))
                {
                    bool isOrder = r.OrderId != "";
                    string scope = isOrder ? r.OrderId : r.MeetingId;
                    if (!next.WrongItemAttempts.Exists(a => a.ScopeId == scope && a.IsOrder == isOrder && a.ItemId == result.ProblemItemId))
                    {
                        next.WrongItemAttempts.Add(new WrongItemAttempt { ScopeId = scope, IsOrder = isOrder, ItemId = result.ProblemItemId });
                        Respect(Buyer(next, r.BuyerId), -1);
                    }
                }
                if (r != null && !string.IsNullOrWhiteSpace(r.ConfirmationId)) next.Receipts.Add(result.Copy());
                // No user callbacks or external I/O between publication and receipt; overflow/exceptions leave state intact.
                state = next;
                return result.Copy();
            }
        }
    }
}
