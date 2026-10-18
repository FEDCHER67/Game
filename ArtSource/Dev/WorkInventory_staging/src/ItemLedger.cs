// G39: one serialized host authority. Returned records are detached copies.
using System;
using System.Collections.Generic;
using System.Linq;

namespace OnlyVolunteers.Items.Core
{
    public sealed partial class ItemLedger
    {
        internal readonly object Gate = new object();
        private readonly IItemDefs defs;
        private readonly WorkItemTuning tuning;
        private readonly Dictionary<string, ItemRecord> items = new Dictionary<string, ItemRecord>(StringComparer.Ordinal);
        private readonly Dictionary<string, ContainerRecord> containers = new Dictionary<string, ContainerRecord>(StringComparer.Ordinal);
        private readonly HashSet<string> retired = new HashSet<string>(StringComparer.Ordinal);
        private readonly Dictionary<string, PlayerInventory> players = new Dictionary<string, PlayerInventory>(StringComparer.Ordinal);
        private readonly Dictionary<string, ActorReceipts> receipts = new Dictionary<string, ActorReceipts>(StringComparer.Ordinal);
        private readonly List<TierChange> tierChanges = new List<TierChange>();
        private readonly HashSet<string> changed = new HashSet<string>(StringComparer.Ordinal);
        private long nextSeq = 1;
        private double activeSeconds;

        public ItemLedger(IItemDefs defs, WorkItemTuning tuning = null)
        {
            this.defs = defs ?? throw new ArgumentNullException(nameof(defs));
            this.tuning = (tuning ?? new WorkItemTuning()).Copy(); this.tuning.Validate();
        }
        public WorkItemTuning Tuning => tuning.Copy();
        public double ActiveSeconds { get { lock (Gate) return activeSeconds; } }
        public IEnumerable<ItemRecord> Items { get { lock (Gate) return items.Values.Select(r => r.Copy()).OrderBy(r => r.Id, StringComparer.Ordinal).ToArray(); } }
        internal ItemRecord Find(string id) => id != null && items.TryGetValue(id, out var r) ? r : null;
        internal ContainerRecord Container(string id) => id != null && containers.TryGetValue(id, out var c) ? c : null;
        internal ItemDef Definition(ItemRecord r) => r != null && defs.TryGet(r.DefId, out var d) ? d : null;
        public ItemRecord Get(string id) { lock (Gate) return Find(id)?.Copy(); }
        public ContainerRecord GetContainer(string id) { lock (Gate) return Container(id)?.Copy(); }
        public bool IsRetired(string id) { lock (Gate) return id != null && retired.Contains(id); }
        public static string PocketsId(string playerId) => "pockets:" + playerId;
        public static string KitId(string playerId) => "kit:" + playerId;
        public TierChange[] DrainTierChanges() { lock (Gate) { var a = tierChanges.ToArray(); tierChanges.Clear(); return a; } }
        public string[] DrainChangedIds() { lock (Gate) { var a = changed.OrderBy(x => x, StringComparer.Ordinal).ToArray(); changed.Clear(); return a; } }
        private void Touch(ItemRecord r) { r.Revision = checked(r.Revision + 1); changed.Add(r.Id); }
        internal void Time(double now)
        {
            if (!ItemCatalog.Finite(now) || now < activeSeconds || now < 0) throw new ArgumentOutOfRangeException(nameof(now), "Use monotonic active-world seconds.");
            activeSeconds = now;
        }
        private string NewId()
        {
            string id;
            do { id = "I-" + nextSeq.ToString("D6", System.Globalization.CultureInfo.InvariantCulture); nextSeq = checked(nextSeq + 1); }
            while (items.ContainsKey(id) || containers.ContainsKey(id) || retired.Contains(id));
            return id;
        }
        public ContainerRecord CreateContainer(string id, ContainerKind kind, string ownerId, int capacity)
        {
            lock (Gate)
            {
                if (string.IsNullOrWhiteSpace(id) || containers.ContainsKey(id) || capacity != Capacity(kind) || capacity < 1 ||
                    !Enum.IsDefined(typeof(ContainerKind), kind)) return null;
                if ((kind == ContainerKind.Pockets || kind == ContainerKind.Kit) && string.IsNullOrWhiteSpace(ownerId)) return null;
                if (kind == ContainerKind.Cooler && (Find(id) == null || Definition(Find(id)).Class != ItemClass.Cooler || ownerId != id)) return null;
                var c = new ContainerRecord { Id = id, Kind = kind, OwnerId = ownerId ?? "", Capacity = capacity, Slots = new string[capacity],
                    Open = kind != ContainerKind.Cooler && kind != ContainerKind.Fridge && kind != ContainerKind.Stash,
                    UpgradePurchased = kind != ContainerKind.VanShelf && kind != ContainerKind.VanCoolerMount };
                containers.Add(id, c); changed.Add(id); return c.Copy();
            }
        }
        private int Capacity(ContainerKind kind)
        {
            switch (kind)
            {
                case ContainerKind.Pockets: return 6;
                case ContainerKind.Kit: return tuning.KitEntries;
                case ContainerKind.VanShelf: return 12;
                case ContainerKind.VanCoolerMount: return 1;
                case ContainerKind.Cooler: case ContainerKind.BuyerCase: case ContainerKind.ReturnTray: return 8;
                case ContainerKind.Fridge: return 24;
                case ContainerKind.Tray: return 6;
                case ContainerKind.Stash: return 4;
                default: return 0;
            }
        }
        public void EnsureVan(string vanId, bool purchased = false)
        {
            lock (Gate)
            {
                if (string.IsNullOrWhiteSpace(vanId)) throw new ArgumentException("Van id required");
                if (Container("vanshelf:" + vanId) == null) CreateContainer("vanshelf:" + vanId, ContainerKind.VanShelf, vanId, 12);
                for (int n = 0; n < 2; n++) if (Container("vanmount:" + vanId + ":" + n) == null)
                    CreateContainer("vanmount:" + vanId + ":" + n, ContainerKind.VanCoolerMount, vanId, 1);
                if (purchased) PurchaseVanStorage(vanId);
            }
        }
        // Monotonic ownership flag: no removal of an occupied purchased upgrade.
        public void PurchaseVanStorage(string vanId)
        {
            lock (Gate) foreach (var c in containers.Values)
                if (c.OwnerId == vanId && (c.Kind == ContainerKind.VanShelf || c.Kind == ContainerKind.VanCoolerMount))
                { c.UpgradePurchased = true; changed.Add(c.Id); }
        }
        public ItemError SetOpen(string id, bool open)
        {
            lock (Gate)
            {
                var c = Container(id); if (c == null) return ItemError.NoSuchContainer;
                if (DetachedContainer(c)) return ItemError.PlayerAbsent;
                if (!c.UpgradePurchased) return ItemError.UpgradeRequired;
                if (c.Kind == ContainerKind.Pockets || c.Kind == ContainerKind.Kit || c.Kind == ContainerKind.Tray || c.Kind == ContainerKind.ReturnTray)
                    return open ? ItemError.None : ItemError.BadRequest;
                if (c.Kind == ContainerKind.Cooler && Find(c.Id)?.Place == PlaceKind.Carried) return ItemError.Busy;
                c.Open = open; changed.Add(id); return ItemError.None;
            }
        }
        public void SetPowered(string id, bool powered, double now)
        {
            lock (Gate)
            {
                Time(now); var c = Container(id);
                if (c == null || c.Kind != ContainerKind.Fridge || c.Powered == powered) return;
                foreach (var item in c.Slots.Select(Find).Where(r => r != null))
                { SettleCore(item, now); if (item.HasOrgan) { Cold(item.Organ, c.Powered, powered, now); Touch(item); } }
                c.Powered = powered; changed.Add(id);
            }
        }
        public MoveResult Mint(int defId, int count, Destination dest, double now)
        {
            lock (Gate)
            {
                Time(now);
                if (!defs.TryGet(defId, out var d) || d.Class == ItemClass.Organ || count < 1 || count > d.MaxStack) return MoveResult.Fail(ItemError.BadRequest);
                var r = new ItemRecord { DefId = defId, Count = count, HasFill = ItemCatalog.HasFill(d.Class) };
                if (d.Class == ItemClass.BloodBag) r.Fill.Amount = 1;
                return Insert(r, d, dest, now);
            }
        }
        public MoveResult MintFilled(int defId, FillData fill, Destination dest, double now, string stableId = null)
        {
            lock (Gate)
            {
                Time(now);
                if (!defs.TryGet(defId, out var d) || !ValidFill(d, fill, now)) return MoveResult.Fail(ItemError.BadRequest);
                if (stableId != null && (string.IsNullOrWhiteSpace(stableId) || items.ContainsKey(stableId) || retired.Contains(stableId) || containers.ContainsKey(stableId)))
                    return MoveResult.Fail(ItemError.AlreadyExists);
                return Insert(new ItemRecord { Id = stableId ?? "", DefId = defId, HasFill = true, Fill = fill.Copy() }, d, dest, now);
            }
        }
        private bool ValidFill(ItemDef d, FillData f, double now) => f != null && ItemCatalog.HasFill(d.Class) && ItemCatalog.Finite(f.Amount) && f.Amount >= 0 &&
            f.Formula >= 0 && f.Formula <= 2 && f.FillSeq >= 0 && ItemCatalog.Finite(f.FilledAt) && f.FilledAt >= -1 && f.FilledAt <= now &&
            ItemCatalog.Finite(f.AgeAtAnchor) && f.AgeAtAnchor >= 0 && f.AgeAtAnchor <= tuning.BloodExpirySeconds &&
            (d.Class != ItemClass.BloodSyringe || f.Amount == 0 || f.FilledAt >= 0 && f.FillSeq > 0) &&
            (d.Class != ItemClass.BloodBag || f.Amount == 1) && (d.Class != ItemClass.BloodSyringe || f.Amount <= 1) &&
            (d.Class != ItemClass.AnesthesiaSyringe || f.Amount <= tuning.SyringeCapacity);
        public MoveResult MintOrgan(string id, int defId, OrganData organ, Destination dest, double now)
        {
            lock (Gate)
            {
                Time(now);
                if (string.IsNullOrWhiteSpace(id) || organ == null || !defs.TryGet(defId, out var d) || d.Class != ItemClass.Organ ||
                    organ.Tier < 1 || organ.Tier > 5 || !ItemCatalog.Finite(organ.Progress) || organ.Progress < 0 || organ.Progress >= 1 || organ.ExtractedAtGameSeconds < 0)
                    return MoveResult.Fail(ItemError.BadRequest);
                if (items.ContainsKey(id) || retired.Contains(id) || containers.ContainsKey(id)) return MoveResult.Fail(ItemError.AlreadyExists);
                var o = organ.Copy(); o.Kind = d.Organ; o.SettledAt = now; o.ColdSince = -1; o.WarmSince = -1;
                o.LastColdStint = 0; o.CaseColdLatch = false; o.LastImpactAt = -1e9;
                if (o.Tier == 1) o.Progress = 0;
                return Insert(new ItemRecord { Id = id, DefId = defId, HasOrgan = true, Organ = o }, d, dest, now);
            }
        }
        private MoveResult Insert(ItemRecord r, ItemDef d, Destination dest, double now)
        {
            var error = CanPlace(r, d, dest, r.Count, out int slot, out var merge);
            if (error != ItemError.None) return MoveResult.Fail(error);
            if (merge != null) { merge.Count += r.Count; Touch(merge); return Success(merge); }
            if (r.Id == "") r.Id = NewId();
            items.Add(r.Id, r);
            if (d.Class == ItemClass.Cooler) CreateContainer(r.Id, ContainerKind.Cooler, r.Id, d.ContainerSlots);
            Place(r, dest, slot);
            if (r.HasOrgan) Cold(r.Organ, false, WorkItemTuning.IsCold(StorageCore(r)), now);
            Touch(r); return Success(r);
        }
        internal static MoveResult Success(ItemRecord r) => new MoveResult { ItemId = r.Id, Slot = r.Slot };
        public MoveResult Move(string actor, long requestId, string id, Destination dest, double now, int count = 0) =>
            Request(actor, requestId, now, () => MoveCore(actor, id, dest, now, count));
        internal MoveResult MoveCore(string actor, string id, Destination dest, double now, int count = 0)
        {
            var r = Find(id); if (r == null) return MoveResult.Fail(ItemError.NoSuchItem);
            var access = Access(actor, r); if (access != ItemError.None) return MoveResult.Fail(access);
            if (dest.Place == PlaceKind.Carried && dest.CarrierId != actor) return MoveResult.Fail(ItemError.NotOwner);
            var to = dest.Place == PlaceKind.Container ? Container(dest.ContainerId) : null;
            if (to != null && IsPersonal(to) && to.OwnerId != actor) return MoveResult.Fail(ItemError.NotOwner);
            if (count < 0 || count > r.Count) return MoveResult.Fail(ItemError.NotEnough);
            if (count == 0) count = r.Count;
            var from = r.Place == PlaceKind.Container ? Container(r.ContainerId) : null;
            if (from != null && !from.Open) return MoveResult.Fail(ItemError.ContainerClosed);
            if (r.Place == PlaceKind.Container && dest.Place == PlaceKind.Container && r.ContainerId == dest.ContainerId &&
                (dest.Slot == -1 || dest.Slot == r.Slot)) return Success(r);
            if (dest.ContainerId == r.Id && dest.Place == PlaceKind.Container) return MoveResult.Fail(ItemError.NotAccepted);
            var error = CanPlace(r, Definition(r), dest, count, out int slot, out var merge);
            if (error != ItemError.None) return MoveResult.Fail(error);
            SettleCore(r, now);
            if (count < r.Count)
            {
                string partId = merge == null ? NewId() : "";
                r.Count -= count; Touch(r);
                if (merge != null) { merge.Count += count; Touch(merge); return Success(merge); }
                var part = new ItemRecord { Id = partId, DefId = r.DefId, Count = count };
                items.Add(part.Id, part); Place(part, dest, slot); Touch(part); return Success(part);
            }
            bool wasCold = WorkItemTuning.IsCold(StorageCore(r));
            bool sameCase = from != null && to != null && from.Id == to.Id && from.Kind == ContainerKind.BuyerCase;
            Unplace(r);
            if (merge != null)
            { items.Remove(r.Id); retired.Add(r.Id); changed.Add(r.Id); merge.Count += count; Touch(merge); ClearMissingSelection(); return Success(merge); }
            Place(r, dest, slot);
            if (r.HasOrgan)
            {
                Cold(r.Organ, wasCold, WorkItemTuning.IsCold(StorageCore(r)), now);
                if (!sameCase) r.Organ.CaseColdLatch = to?.Kind == ContainerKind.BuyerCase && DeliveredColdCore(r, now);
            }
            if (Definition(r).Class == ItemClass.Cooler && dest.Place == PlaceKind.Carried) Container(r.Id).Open = false;
            Touch(r); ClearMissingSelection(); return Success(r);
        }
        private ItemError CanPlace(ItemRecord r, ItemDef d, Destination dest, int count, out int slot, out ItemRecord merge)
        {
            slot = -1; merge = null;
            if (count < 1 || count > d.MaxStack || dest.Slot < -1) return ItemError.BadRequest;
            if (dest.Place == PlaceKind.World) return ItemError.None;
            if (dest.Place == PlaceKind.Carried)
            {
                if (!d.TwoHanded) return ItemError.NotTwoHanded;
                if (string.IsNullOrWhiteSpace(dest.CarrierId) || !players.TryGetValue(dest.CarrierId, out var p)) return ItemError.NotOwner;
                if (!p.Present) return ItemError.PlayerAbsent;
                return items.Values.Any(o => o != r && o.Place == PlaceKind.Carried && o.CarrierId == dest.CarrierId) ? ItemError.SlotOccupied : ItemError.None;
            }
            if (dest.Place != PlaceKind.Container) return ItemError.BadRequest;
            var c = Container(dest.ContainerId); if (c == null) return ItemError.NoSuchContainer;
            if (DetachedContainer(c)) return ItemError.PlayerAbsent;
            if (!c.UpgradePurchased) return ItemError.UpgradeRequired;
            if (!c.Open) return ItemError.ContainerClosed;
            if (!Accepts(c.Kind, d)) return d.TwoHanded ? ItemError.TwoHandedOnly : ItemError.NotAccepted;
            if (c.Kind == ContainerKind.Kit && players.TryGetValue(c.OwnerId, out var owner) &&
                !string.IsNullOrEmpty(Container(PocketsId(owner.PlayerId)).Slots[owner.KitSlot])) return ItemError.SlotOccupied;
            if (dest.Slot >= c.Capacity) return ItemError.BadRequest;
            bool Reserved(int s) => c.Kind == ContainerKind.Pockets && players.TryGetValue(c.OwnerId, out var p) && p.KitSlot == s && HasKit(p.PlayerId);
            if (dest.Slot >= 0)
            {
                if (Reserved(dest.Slot)) return ItemError.SlotOccupied;
                var occupant = Find(c.Slots[dest.Slot]);
                if (occupant == null || occupant == r) { slot = dest.Slot; return ItemError.None; }
                if (CanMerge(occupant, r, d, count)) { slot = dest.Slot; merge = occupant; return ItemError.None; }
                return ItemError.SlotOccupied;
            }
            for (int n = 0; n < c.Capacity; n++)
            { var o = Find(c.Slots[n]); if (!Reserved(n) && o != null && CanMerge(o, r, d, count)) { slot = n; merge = o; return ItemError.None; } }
            for (int n = 0; n < c.Capacity; n++) if (!Reserved(n) && string.IsNullOrEmpty(c.Slots[n])) { slot = n; return ItemError.None; }
            return ItemError.ContainerFull;
        }
        private static bool CanMerge(ItemRecord into, ItemRecord r, ItemDef d, int count) => into != r && into.DefId == r.DefId &&
            ItemCatalog.Stackable(d.Class) && !into.HasOrgan && !into.HasFill && !r.HasOrgan && !r.HasFill && count <= d.MaxStack - into.Count;
        public static bool Accepts(ContainerKind kind, ItemDef d)
        {
            if (d == null || !Enum.IsDefined(typeof(ContainerKind), kind)) return false;
            if (d.TwoHanded) return kind == ContainerKind.VanCoolerMount && d.Class == ItemClass.Cooler;
            switch (kind)
            {
                case ContainerKind.VanCoolerMount: return false;
                case ContainerKind.Kit: return ItemCatalog.KitOrder(d.Class) >= 0;
                case ContainerKind.Cooler: case ContainerKind.Fridge:
                    return d.Class == ItemClass.Organ || d.Class == ItemClass.BloodBag || d.Class == ItemClass.BloodSyringe;
                case ContainerKind.BuyerCase: case ContainerKind.Stash: return d.Class == ItemClass.Organ;
                default: return true;
            }
        }
        private void Place(ItemRecord r, Destination dest, int slot)
        {
            if (dest.Place == PlaceKind.Container) poses.Remove(r.Id);
            r.Place = dest.Place; r.ContainerId = ""; r.CarrierId = ""; r.Slot = -1;
            if (dest.Place == PlaceKind.Container)
            { var c = Container(dest.ContainerId); c.Slots[slot] = r.Id; r.ContainerId = c.Id; r.Slot = slot; changed.Add(c.Id); }
            if (dest.Place == PlaceKind.Carried) r.CarrierId = dest.CarrierId;
        }
        private void Unplace(ItemRecord r)
        {
            if (r.Place == PlaceKind.Container) { var c = Container(r.ContainerId); c.Slots[r.Slot] = null; changed.Add(c.Id); }
            r.Place = PlaceKind.None; r.ContainerId = ""; r.Slot = -1; r.CarrierId = "";
        }
        public ItemError Consume(string id, int count)
        {
            lock (Gate)
            {
                var r = Find(id); if (r == null) return ItemError.NoSuchItem;
                if (Detached(r)) return ItemError.PlayerAbsent;
                if (!ItemCatalog.Stackable(Definition(r).Class)) return ItemError.NotAccepted;
                if (count < 1 || count > r.Count) return ItemError.NotEnough;
                r.Count -= count; if (r.Count == 0) RetireCore(r); else Touch(r); return ItemError.None;
            }
        }
        public ItemError Retire(string id)
        {
            lock (Gate)
            {
                var r = Find(id); if (r == null) return ItemError.NoSuchItem;
                if (Detached(r)) return ItemError.PlayerAbsent;
                RetireCore(r); return ItemError.None;
            }
        }
        private void RetireCore(ItemRecord r)
        {
            var own = Container(r.Id);
            if (own != null)
            {
                foreach (var id in (string[])own.Slots.Clone())
                {
                    var child = Find(id); if (child == null) continue;
                    SettleCore(child, activeSeconds); bool cold = WorkItemTuning.IsCold(StorageCore(child));
                    Unplace(child); Place(child, Destination.ToWorld(), -1);
                    if (poses.TryGetValue(r.Id, out var pose)) { var spill = pose.Copy(); spill.Id = child.Id; poses[child.Id] = spill; }
                    if (child.HasOrgan) { Cold(child.Organ, cold, false, activeSeconds); child.Organ.CaseColdLatch = false; }
                    Touch(child);
                }
                containers.Remove(r.Id);
            }
            Unplace(r); items.Remove(r.Id); poses.Remove(r.Id); retired.Add(r.Id); changed.Add(r.Id); ClearMissingSelection();
        }
        public ItemRecord FirstOfClass(string containerId, ItemClass cls)
        { lock (Gate) return Container(containerId)?.Slots.Select(Find).FirstOrDefault(r => r != null && Definition(r).Class == cls)?.Copy(); }
        private StorageClass StorageCore(ItemRecord r)
        {
            var c = r.Place == PlaceKind.Container ? Container(r.ContainerId) : null;
            return c?.Kind == ContainerKind.Cooler ? StorageClass.PortableCooler : c?.Kind == ContainerKind.Fridge ?
                (c.Powered ? StorageClass.FridgePowered : StorageClass.FridgeUnpowered) : StorageClass.Room;
        }
        public StorageClass StorageOf(ItemRecord r) { lock (Gate) return r == null ? StorageClass.Room : StorageCore(Find(r.Id) ?? r); }
        public void Settle(double now) { lock (Gate) { Time(now); foreach (var r in items.Values) SettleCore(r, now); } }
        public void SettleItem(ItemRecord r, double now) { lock (Gate) { Time(now); var actual = r == null ? null : Find(r.Id); if (actual != null) SettleCore(actual, now); } }
        private void SettleCore(ItemRecord r, double now)
        {
            if (!r.HasOrgan || Detached(r)) return;
            var o = r.Organ; double dt = now - o.SettledAt; if (dt <= 0) return;
            double rate = tuning.SecondsPerGrade(StorageCore(r));
            if (o.Tier > 1 && !double.IsInfinity(rate))
            {
                double firstAt = o.SettledAt + (1 - o.Progress) * rate;
                double progress = o.Progress + dt / rate;
                int lost = 0;
                while (progress >= 1 - 1e-12 && o.Tier > 1)
                {
                    int from = o.Tier--; progress -= 1;
                    tierChanges.Add(new TierChange { ItemId = r.Id, From = from, To = o.Tier, At = firstAt + lost++ * rate });
                }
                o.Progress = o.Tier == 1 ? 0 : Math.Max(0, progress);
            }
            o.SettledAt = now; Touch(r);
        }
        public double NextGradeLossAt(string id, double now)
        {
            lock (Gate)
            {
                Time(now); var r = Find(id); if (r == null || !r.HasOrgan || Detached(r)) return double.PositiveInfinity;
                SettleCore(r, now); return r.Organ.Tier == 1 ? double.PositiveInfinity : now + (1 - r.Organ.Progress) * tuning.SecondsPerGrade(StorageCore(r));
            }
        }
        private static void Cold(OrganData o, bool was, bool cold, double now)
        {
            if (was == cold) return;
            if (cold) o.ColdSince = now;
            else { o.LastColdStint = o.ColdSince >= 0 ? now - o.ColdSince : 0; o.WarmSince = now; o.ColdSince = -1; }
        }
        private bool DeliveredColdCore(ItemRecord r, double now)
        {
            if (!r.HasOrgan) return false; var o = r.Organ;
            if (WorkItemTuning.IsCold(StorageCore(r))) return o.ColdSince >= 0 && now - o.ColdSince >= tuning.MinColdStintSeconds;
            return o.WarmSince >= 0 && o.LastColdStint >= tuning.MinColdStintSeconds && now - o.WarmSince <= tuning.MaxWarmGapSeconds;
        }
        public bool IsDeliveredCold(ItemRecord r, double now)
        { lock (Gate) { Time(now); var actual = r == null ? null : Find(r.Id); return actual != null && !Detached(actual) && DeliveredColdCore(actual, now); } }
        // The adapter supplies measured server impact speed. Equality is not above threshold.
        public int ApplyImpact(string id, double speed, double now)
        {
            lock (Gate)
            {
                Time(now); var r = Find(id);
                if (r == null || Detached(r) || !ItemCatalog.Finite(speed) || speed < 0) return 0;
                if (r.HasOrgan) return speed > tuning.OrganImpactSpeed && ImpactCore(r, now) ? 1 : 0;
                if (Definition(r).Class != ItemClass.Cooler || speed <= tuning.CoolerImpactSpeed) return 0;
                int n = 0;
                foreach (var child in Container(r.Id).Slots.Select(Find)) if (child != null && child.HasOrgan && ImpactCore(child, now)) n++;
                return n;
            }
        }
        private bool ImpactCore(ItemRecord r, double now)
        {
            SettleCore(r, now); var o = r.Organ;
            if (o.Tier == 1 || now - o.LastImpactAt + 1e-12 < tuning.ImpactCooldownSeconds) return false;
            int from = o.Tier--; o.LastImpactAt = now; if (o.Tier == 1) o.Progress = 0; Touch(r);
            tierChanges.Add(new TierChange { ItemId = r.Id, From = from, To = o.Tier, At = now }); return true;
        }
        public static double TierMultiplier(int tier)
        { Tier.ToCaptureGrade(tier); return new[] { 0.3, 1, 1.6, 2.6, 4.2 }[tier - 1]; }
        public long ValueCents(ItemRecord r, double now)
        {
            lock (Gate)
            {
                Time(now); var actual = r == null ? null : Find(r.Id); if (actual == null) return 0;
                SettleCore(actual, now); var d = Definition(actual);
                return checked((long)Math.Round((decimal)d.BaseValueCents * actual.Count * (actual.HasOrgan ? (decimal)TierMultiplier(actual.Organ.Tier) : 1), MidpointRounding.AwayFromZero));
            }
        }
    }
}
