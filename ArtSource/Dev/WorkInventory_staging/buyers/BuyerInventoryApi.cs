namespace OnlyVolunteers.Buyers
{
    public sealed partial class BuyerRules
    {
        // Host-only merchandise holder. Never a participant, negotiator or XP recipient.
        public const string TeamHolderId = "@team";
        public bool RegisterTeamItem(BuyerItemState item)
        {
            if (item == null) return false;
            var copy = item.Copy(); copy.HolderId = TeamHolderId; return RegisterItem(copy);
        }
        /// <summary>Host reports an actual pickup/return. Reservations must be unloaded first.</summary>
        public bool SetItemHolder(string itemId, string holderId)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (item == null || item.Sold || item.MeetingId != "" || item.StashOrderId != "" ||
                    holderId != TeamHolderId && !Present(state, holderId)) return false;
                item.HolderId = holderId; return true;
            }
        }
        /// <summary>Host reports the ledger's latch. Inspection never calls this with false.</summary>
        public bool SetDeliveredCooled(string itemId, bool cooled)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (item == null || item.Sold || !BuyerCatalog.IsOrgan(item.Kind)) return false;
                item.DeliveredCooled = cooled; return true;
            }
        }
        public bool SetPackaged(string itemId, bool packaged)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (item == null || item.Sold || !BuyerCatalog.IsOrgan(item.Kind)) return false;
                item.Packaged = packaged; return true;
            }
        }
        public bool LoadItem(string buyerId, string itemId, string holderId, bool deliveredCooled, out SaleError error)
        {
            lock (gate)
            {
                if (!LoadItem(buyerId, itemId, holderId, out error)) return false;
                var item = Item(state, itemId);
                if (BuyerCatalog.IsOrgan(item.Kind)) item.DeliveredCooled = deliveredCooled;
                return true;
            }
        }
        public bool UnloadItem(string buyerId, string itemId) => UnloadItem(buyerId, itemId, TeamHolderId);
        /// <summary>Any present teammate may take unsold case goods; negotiation history is retained.</summary>
        public bool UnloadItem(string buyerId, string itemId, string recipientId)
        {
            lock (gate)
            {
                Synchronize(state);
                var buyer = state.Buyers.Find(b => b.Id == buyerId); var item = Item(state, itemId);
                if (buyer?.Meeting == null || item == null || item.Sold || item.MeetingId != buyer.Meeting.Id || item.StashOrderId != "" ||
                    recipientId != TeamHolderId && !Present(state, recipientId)) return false;
                item.MeetingId = ""; item.HolderId = recipientId; item.DeliveredCooled = false; return true;
            }
        }
        /// <summary>Disposal/confiscation, not a sale. Retain a persistent tombstone to prevent resurrection.</summary>
        public bool RemoveItem(string itemId)
        {
            lock (gate)
            {
                Synchronize(state); var item = Item(state, itemId);
                if (item == null || item.Sold) return false;
                state.Items.Remove(item); state.RemovedItemIds.Add(itemId); return true;
            }
        }
    }
}
