using System;

namespace OnlyVolunteers.Buyers
{
    public sealed partial class BuyerRules
    {
        private static bool OrderEligible(BuyerWorldState s, OrderTemplate template) =>
            template == OrderTemplate.HamletKidney || template == OrderTemplate.StreamerBrain && s.HasSaw && s.HasDowntownAccess;

        public bool CreateOrderOffer(string offerId, string buyerId, OrderTemplate template, string sourceNpcId, string stashId, string negotiatorId)
        {
            lock (gate)
            {
                Synchronize(state); var b = Buyer(state, buyerId);
                if (buyerId != BuyerCatalog.OrganBuyer || !IsAvailable(state, buyerId) || b.Respect < 40 || !Present(state, negotiatorId) ||
                    !Enum.IsDefined(typeof(OrderTemplate), template) || !OrderEligible(state, template) || state.ActiveOrder != null ||
                    string.IsNullOrWhiteSpace(offerId) || string.IsNullOrWhiteSpace(sourceNpcId) || string.IsNullOrWhiteSpace(stashId) ||
                    state.Offers.Exists(o => o.Id == offerId || o.Template == template && !o.Accepted) || state.CompletedOrders.Contains(template)) return false;
                state.Offers.Add(new SpecialOrderOffer { Id = offerId, BuyerId = buyerId, Template = template,
                    SourceNpcId = sourceNpcId, StashId = stashId,
                    Negotiation = new NegotiationState { Kind = BuyerCatalog.OrderKind(template), NegotiatorId = negotiatorId } });
                return true;
            }
        }
        /// <summary>Reopens the SAME failed offer only after its cooldown. Accepted terms cannot reroll.</summary>
        public bool ChangeOrderNegotiator(string offerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var offer = state.Offers.Find(o => o.Id == offerId);
                if (offer == null || offer.Accepted || !Present(state, playerId) || state.LastGameSeconds < offer.BannedUntil) return false;
                if (offer.Negotiation.Phase == NegotiationPhase.Failed)
                    offer.Negotiation = new NegotiationState { Kind = BuyerCatalog.OrderKind(offer.Template) };
                offer.Negotiation.NegotiatorId = playerId; return true;
            }
        }
        public bool AskOrder(string offerId, string playerId, int ask)
        {
            lock (gate)
            {
                Synchronize(state); var offer = state.Offers.Find(o => o.Id == offerId);
                if (offer == null || offer.Accepted || state.LastGameSeconds < offer.BannedUntil) return false;
                return Ask(Buyer(state, offer.BuyerId), offer.Negotiation, playerId, ask,
                    () => offer.BannedUntil = state.LastGameSeconds + 3 * BuyerCatalog.Hour);
            }
        }
        public bool AcceptOrderPrice(string offerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var offer = state.Offers.Find(o => o.Id == offerId);
                return offer != null && !offer.Accepted && state.LastGameSeconds >= offer.BannedUntil && Present(state, playerId) && AcceptCounter(offer.Negotiation, playerId);
            }
        }
        public bool AcceptOrder(string offerId, string playerId)
        {
            lock (gate)
            {
                Synchronize(state); var offer = state.Offers.Find(o => o.Id == offerId);
                if (offer == null || offer.Accepted || state.ActiveOrder != null || !Present(state, playerId) ||
                    offer.Negotiation.NegotiatorId != playerId || offer.Negotiation.Phase != NegotiationPhase.Agreed ||
                    Buyer(state, offer.BuyerId).Respect < 40 || !OrderEligible(state, offer.Template)) return false;
                state.ActiveOrder = new SpecialOrderState { Id = offer.Id, BuyerId = offer.BuyerId, Template = offer.Template,
                    SourceNpcId = offer.SourceNpcId, StashId = offer.StashId, AgreedPercent = offer.Negotiation.AgreedPercent,
                    AcceptedAt = state.LastGameSeconds, Deadline = state.LastGameSeconds + 48 * BuyerCatalog.Hour };
                offer.Accepted = true;
                if (!state.OpenStashes.Contains(offer.StashId)) state.OpenStashes.Add(offer.StashId);
                return true;
            }
        }
        public bool RefuseOrder(string orderId)
        {
            lock (gate)
            {
                Synchronize(state); var order = state.ActiveOrder;
                if (order == null || order.Id != orderId) return false;
                if (!order.LatePenaltyApplied) Respect(Buyer(state, order.BuyerId), -2);
                ReleaseStash(state, order.Id); state.ActiveOrder = null; return true;
            }
        }
        private static void ReleaseStash(BuyerWorldState s, string orderId)
        {
            foreach (var item in s.Items) if (item.StashOrderId == orderId) item.StashOrderId = "";
        }
        public bool DepositInStash(string orderId, string itemId, string holderId)
        {
            lock (gate)
            {
                Synchronize(state); var order = state.ActiveOrder; var item = Item(state, itemId);
                if (order == null || order.Id != orderId || !state.OpenStashes.Contains(order.StashId) || item == null || item.Sold ||
                    !Present(state, holderId) || item.HolderId != holderId || item.MeetingId != "" || item.StashOrderId != "") return false;
                item.StashOrderId = orderId; return true;
            }
        }
        public bool WithdrawFromStash(string orderId, string itemId, string holderId)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (item == null || item.Sold || item.StashOrderId != orderId || item.HolderId != holderId || !Present(state, holderId)) return false;
                item.StashOrderId = ""; return true;
            }
        }
        private static SaleError OrderMismatch(SpecialOrderState order, BuyerItemState item)
        {
            if (item.Kind != BuyerCatalog.OrderKind(order.Template)) return SaleError.WrongKind;
            if (item.SourceNpcId != order.SourceNpcId || item.SourceNpcType != BuyerCatalog.OrderNpcType(order.Template)) return SaleError.WrongNpc;
            if (item.Quality < BuyerCatalog.OrderMinimum(order.Template)) return SaleError.LowQuality;
            if (!item.Packaged) return SaleError.PackagingRequired;
            return SaleError.None;
        }
        public SaleError PreviewOrderItem(string itemId)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (state.ActiveOrder == null) return SaleError.Unavailable;
                if (item == null) return SaleError.MissingItem;
                if (item.Sold) return SaleError.AlreadySold;
                return OrderMismatch(state.ActiveOrder, item);
            }
        }
    }
}
