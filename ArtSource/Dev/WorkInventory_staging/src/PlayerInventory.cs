using System;
using System.Collections.Generic;
using System.Linq;

namespace OnlyVolunteers.Items.Core
{
    [Serializable]
    public sealed class PlayerInventory
    {
        public string PlayerId = "";
        public bool Present = true;
        public int ActiveSlot = 255;
        public int KitSlot = 5;
        public string ActiveKitItemId = "";
        public double DetachedAt = -1;
        public long LastPressId;
        public PlayerInventory Copy() => (PlayerInventory)MemberwiseClone();
    }
    [Serializable]
    public sealed class RequestReceipt
    {
        public long RequestId;
        public MoveResult Result;
        public RequestReceipt Copy() => (RequestReceipt)MemberwiseClone();
    }
    [Serializable]
    public sealed class ActorReceipts
    {
        public string PlayerId = "";
        public long HighWater;
        public List<RequestReceipt> Results = new List<RequestReceipt>();
        public ActorReceipts Copy() => new ActorReceipts { PlayerId = PlayerId, HighWater = HighWater, Results = Results.ConvertAll(r => r.Copy()) };
    }

    public sealed partial class ItemLedger
    {
        public PlayerInventory EnsurePlayer(string id, int kitSlot = 5)
        {
            lock (Gate)
            {
                if (string.IsNullOrWhiteSpace(id) || kitSlot < 0 || kitSlot > 5) throw new ArgumentException("Valid persistent player id and kit slot required");
                if (!players.TryGetValue(id, out var p))
                {
                    p = new PlayerInventory { PlayerId = id, KitSlot = kitSlot }; players.Add(id, p);
                    CreateContainer(PocketsId(id), ContainerKind.Pockets, id, 6);
                    CreateContainer(KitId(id), ContainerKind.Kit, id, tuning.KitEntries);
                }
                return p.Copy();
            }
        }
        public PlayerInventory GetPlayer(string id) { lock (Gate) return id != null && players.TryGetValue(id, out var p) ? p.Copy() : null; }
        public ContainerRecord EnsurePockets(string id) { lock (Gate) { EnsurePlayer(id); return GetContainer(PocketsId(id)); } }
        private static bool IsPersonal(ContainerRecord c) => c.Kind == ContainerKind.Pockets || c.Kind == ContainerKind.Kit;
        private bool HasKit(string player) => Container(KitId(player))?.Slots.Any(id => !string.IsNullOrEmpty(id)) == true;
        private string Owner(ItemRecord r)
        {
            if (r.Place == PlaceKind.Carried) return r.CarrierId;
            if (r.Place != PlaceKind.Container) return "";
            var c = Container(r.ContainerId);
            if (c == null) return "";
            if (IsPersonal(c)) return c.OwnerId;
            // The only legal nested item is an organ/blood item in a cooler.
            if (c.Kind == ContainerKind.Cooler && Find(c.Id)?.Place == PlaceKind.Carried) return Find(c.Id).CarrierId;
            return "";
        }
        private bool Detached(ItemRecord r) { string id = Owner(r); return id != "" && players.TryGetValue(id, out var p) && !p.Present; }
        private bool DetachedContainer(ContainerRecord c) => IsPersonal(c) ? players.TryGetValue(c.OwnerId, out var p) && !p.Present :
            c.Kind == ContainerKind.Cooler && Find(c.Id) != null && Detached(Find(c.Id));
        public bool IsWorldAvailable(string id) { lock (Gate) { var r = Find(id); return r != null && !Detached(r); } }
        internal ItemError Access(string actor, ItemRecord r)
        {
            if (Detached(r)) return ItemError.PlayerAbsent;
            string owner = Owner(r);
            return owner != "" && owner != actor ? ItemError.NotOwner : ItemError.None;
        }
        internal MoveResult Request(string actor, long requestId, double now, Func<MoveResult> operation)
        {
            lock (Gate)
            {
                if (string.IsNullOrWhiteSpace(actor) || requestId <= 0) return MoveResult.Fail(ItemError.BadRequest);
                if (receipts.TryGetValue(actor, out var saved))
                {
                    var previous = saved.Results.Find(r => r.RequestId == requestId);
                    if (previous != null) { var replay = previous.Result; replay.Replayed = true; return replay; }
                    if (requestId <= saved.HighWater) return MoveResult.Fail(ItemError.StaleRequest);
                }
                if (!players.TryGetValue(actor, out var p)) return MoveResult.Fail(ItemError.NotOwner);
                if (!p.Present) return MoveResult.Fail(ItemError.PlayerAbsent);
                if (!ItemCatalog.Finite(now) || now < activeSeconds || now < 0) return MoveResult.Fail(ItemError.BadRequest);
                Time(now);
                var result = operation();
                if (saved == null) { saved = new ActorReceipts { PlayerId = actor }; receipts.Add(actor, saved); }
                saved.HighWater = requestId; saved.Results.Add(new RequestReceipt { RequestId = requestId, Result = result });
                if (saved.Results.Count > 64) saved.Results.RemoveAt(0);
                return result;
            }
        }
        public string[] KitCycle(string playerId)
        {
            lock (Gate)
                return (Container(KitId(playerId))?.Slots ?? Array.Empty<string>()).Select(Find).Where(r => r != null)
                    .OrderBy(r => ItemCatalog.KitOrder(Definition(r).Class)).ThenBy(r => r.DefId)
                    .ThenBy(r => r.Id, StringComparer.Ordinal).Select(r => r.Id).ToArray();
        }
        public ItemRecord HeldItem(string playerId)
        {
            lock (Gate)
            {
                if (!players.TryGetValue(playerId, out var p) || !p.Present || CarryCore(playerId) != null || p.ActiveSlot == 255) return null;
                if (p.ActiveSlot == p.KitSlot && HasKit(playerId)) return Find(p.ActiveKitItemId)?.Copy();
                return Find(Container(PocketsId(playerId)).Slots[p.ActiveSlot])?.Copy();
            }
        }
        private ItemRecord CarryCore(string playerId) => items.Values.FirstOrDefault(r => r.Place == PlaceKind.Carried && r.CarrierId == playerId);
        public ItemRecord CarriedItem(string playerId) { lock (Gate) return CarryCore(playerId)?.Copy(); }
        public MoveResult SelectSlot(string actor, long requestId, int slot, double now) => Request(actor, requestId, now, () => SelectCore(actor, slot));
        internal MoveResult SelectCore(string playerId, int slot)
        {
            var p = players[playerId];
            if (slot != 255 && (slot < 0 || slot > 5)) return MoveResult.Fail(ItemError.BadRequest);
            if (CarryCore(playerId) != null) return MoveResult.Fail(ItemError.TwoHandedOnly);
            if (slot == 255) { p.ActiveSlot = 255; p.ActiveKitItemId = ""; return new MoveResult { Slot = 255 }; }
            if (slot == p.KitSlot && HasKit(playerId))
            {
                var ordered = KitCycle(playerId);
                int n = p.ActiveSlot == slot ? Array.IndexOf(ordered, p.ActiveKitItemId) + 1 : 0;
                if (n >= ordered.Length) { p.ActiveSlot = 255; p.ActiveKitItemId = ""; }
                else { p.ActiveSlot = slot; p.ActiveKitItemId = ordered[n]; }
            }
            else
            {
                p.ActiveKitItemId = "";
                p.ActiveSlot = p.ActiveSlot == slot || string.IsNullOrEmpty(Container(PocketsId(playerId)).Slots[slot]) ? 255 : slot;
            }
            changed.Add(PocketsId(playerId)); return new MoveResult { Slot = p.ActiveSlot, ItemId = HeldItem(playerId)?.Id ?? "" };
        }
        internal void SelectItem(string actor, string id)
        {
            var p = players[actor]; var r = Find(id);
            if (r == null || r.Place != PlaceKind.Container) return;
            if (r.ContainerId == KitId(actor)) { p.ActiveSlot = p.KitSlot; p.ActiveKitItemId = id; }
            if (r.ContainerId == PocketsId(actor)) { p.ActiveSlot = r.Slot; p.ActiveKitItemId = ""; }
        }
        private void ClearMissingSelection()
        {
            foreach (var p in players.Values)
            {
                if (p.ActiveSlot == 255) continue;
                if (p.ActiveKitItemId != "" && (Find(p.ActiveKitItemId)?.ContainerId != KitId(p.PlayerId))) { p.ActiveSlot = 255; p.ActiveKitItemId = ""; }
                else if (p.ActiveKitItemId == "" && string.IsNullOrEmpty(Container(PocketsId(p.PlayerId)).Slots[p.ActiveSlot])) p.ActiveSlot = 255;
            }
        }
        public ItemError LeavePlayer(string id, double now)
        {
            lock (Gate)
            {
                Time(now); if (!players.TryGetValue(id, out var p)) return ItemError.NotOwner;
                if (!p.Present) return ItemError.None;
                foreach (var r in items.Values.Where(r => Owner(r) == id)) { SettleCore(r, now); changed.Add(r.Id); }
                p.Present = false; p.DetachedAt = now; return ItemError.None;
            }
        }
        public PlayerInventory RejoinPlayer(string id, double now)
        {
            lock (Gate)
            {
                Time(now); EnsurePlayer(id); var p = players[id];
                if (!p.Present)
                {
                    double pause = now - p.DetachedAt;
                    foreach (var r in items.Values.Where(r => Owner(r) == id))
                    {
                        // Preserve durations, not time spent disconnected. Provenance game time never shifts.
                        if (r.HasOrgan)
                        {
                            r.Organ.SettledAt += pause;
                            if (r.Organ.ColdSince >= 0) r.Organ.ColdSince += pause;
                            if (r.Organ.WarmSince >= 0) r.Organ.WarmSince += pause;
                            if (r.Organ.LastImpactAt >= 0) r.Organ.LastImpactAt += pause;
                        }
                        if (r.HasFill && r.Fill.FilledAt >= 0) r.Fill.FilledAt += pause;
                        changed.Add(r.Id);
                    }
                    p.Present = true; p.DetachedAt = -1;
                }
                return p.Copy();
            }
        }
        public ItemRecord MostValuableOf(string playerId, double now)
        {
            lock (Gate)
            {
                Time(now);
                if (!players.TryGetValue(playerId, out var p) || !p.Present) return null;
                return items.Values.Where(r => r.Place == PlaceKind.Carried && r.CarrierId == playerId ||
                    r.Place == PlaceKind.Container && (r.ContainerId == PocketsId(playerId) || r.ContainerId == KitId(playerId)))
                    .OrderByDescending(r => ValueCents(r, now)).ThenBy(r => r.Id, StringComparer.Ordinal).FirstOrDefault()?.Copy();
            }
        }
        public ItemRecord ConfiscateMostValuable(string playerId, double now)
        {
            lock (Gate)
            {
                var r = MostValuableOf(playerId, now); if (r == null) return null;
                // Confiscating a container takes the entire physical unit, unlike destruction which spills.
                var c = Container(r.Id);
                if (c != null) foreach (var id in (string[])c.Slots.Clone()) if (Find(id) != null) RetireCore(Find(id));
                RetireCore(Find(r.Id)); return r;
            }
        }
        /// <summary>Future knockout hook (§4.11). This explicit event drops only the held unit; leave never calls it.</summary>
        public MoveResult KnockOutHeldItem(string playerId, PlainVector position, double now)
        {
            lock (Gate)
            {
                Time(now);
                if (!position.IsFinite) return MoveResult.Fail(ItemError.BadRequest);
                if (!players.TryGetValue(playerId, out var p)) return MoveResult.Fail(ItemError.NotOwner);
                if (!p.Present) return MoveResult.Fail(ItemError.PlayerAbsent);
                var item = CarryCore(playerId) ?? Find(HeldItem(playerId)?.Id);
                if (item == null) return MoveResult.Fail(ItemError.NoActiveItem);
                var result = MoveCore(playerId, item.Id, Destination.ToWorld(), now);
                if (result.Ok) { SetPose(new ItemPose { Id = item.Id, Position = position }); p.ActiveSlot = 255; p.ActiveKitItemId = ""; }
                return result;
            }
        }
    }
}
