using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization.Json;
using System.Text;

namespace OnlyVolunteers.Items.Core
{
    [Serializable]
    public struct PlainVector
    {
        public double X, Y, Z;
        public PlainVector(double x, double y, double z) { X = x; Y = y; Z = z; }
        public bool IsFinite => ItemCatalog.Finite(X) && ItemCatalog.Finite(Y) && ItemCatalog.Finite(Z);
        public double LengthSquared => X * X + Y * Y + Z * Z;
    }
    [Serializable]
    public struct PlainRotation
    {
        public double X, Y, Z, W;
        public static PlainRotation Identity => new PlainRotation { W = 1 };
        public bool IsValid => ItemCatalog.Finite(X) && ItemCatalog.Finite(Y) && ItemCatalog.Finite(Z) && ItemCatalog.Finite(W) &&
            Math.Abs(X * X + Y * Y + Z * Z + W * W - 1) < 0.001;
    }
    [Serializable]
    public sealed class ItemPose
    {
        public string Id = "";
        public PlainVector Position;
        public PlainRotation Rotation = PlainRotation.Identity;
        public ItemPose Copy() => (ItemPose)MemberwiseClone();
    }
    [Serializable]
    public sealed class LedgerSave
    {
        public int version = 2;
        public long nextSeq = 1;
        public double activeSeconds;
        public List<ItemRecord> items = new List<ItemRecord>();
        public List<ContainerRecord> containers = new List<ContainerRecord>();
        public List<string> retiredIds = new List<string>();
        public List<ActorReceipts> receipts = new List<ActorReceipts>();
    }
    /// <summary>Inventory fragment for the host's v2 WORLD save. The adapter retains all other world blocks.</summary>
    [Serializable]
    public sealed class InventorySaveV2
    {
        public int version = 2;
        public LedgerSave items = new LedgerSave();
        public List<PlayerInventory> players = new List<PlayerInventory>();
        public List<ItemPose> itemPoses = new List<ItemPose>();
    }
    public sealed partial class ItemLedger
    {
        private readonly Dictionary<string, ItemPose> poses = new Dictionary<string, ItemPose>(StringComparer.Ordinal);
        public ItemError SetPose(ItemPose pose)
        {
            lock (Gate)
            {
                if (pose == null || !pose.Position.IsFinite || !pose.Rotation.IsValid) return ItemError.BadRequest;
                var r = Find(pose.Id); if (r == null) return ItemError.NoSuchItem;
                if (Detached(r)) return ItemError.PlayerAbsent;
                if (r.Place != PlaceKind.World && r.Place != PlaceKind.Carried) return ItemError.BadRequest;
                poses[r.Id] = pose.Copy(); return ItemError.None;
            }
        }
        public ItemPose GetPose(string id) { lock (Gate) return id != null && poses.TryGetValue(id, out var p) ? p.Copy() : null; }
        public InventorySaveV2 Snapshot(double now)
        {
            lock (Gate)
            {
                Settle(now);
                return new InventorySaveV2 {
                    items = new LedgerSave { nextSeq = nextSeq, activeSeconds = now,
                        items = items.Values.OrderBy(r => r.Id, StringComparer.Ordinal).Select(r => r.Copy()).ToList(),
                        containers = containers.Values.OrderBy(c => c.Id, StringComparer.Ordinal).Select(c => c.Copy()).ToList(),
                        retiredIds = retired.OrderBy(id => id, StringComparer.Ordinal).ToList(),
                        receipts = receipts.Values.OrderBy(a => a.PlayerId, StringComparer.Ordinal).Select(a => a.Copy()).ToList() },
                    players = players.Values.OrderBy(p => p.PlayerId, StringComparer.Ordinal).Select(p => p.Copy()).ToList(),
                    itemPoses = items.Values.Where(r => r.Place == PlaceKind.World || r.Place == PlaceKind.Carried)
                        .OrderBy(r => r.Id, StringComparer.Ordinal).Select(r => poses.TryGetValue(r.Id, out var p) ? p.Copy() : new ItemPose { Id = r.Id }).ToList()
                };
            }
        }
        public static ItemLedger Restore(InventorySaveV2 save, IItemDefs defs, WorkItemTuning tuning = null)
        {
            void Require(bool condition, string detail) { if (!condition) throw new InvalidDataException("Invalid inventory save: " + detail); }
            Require(save != null && save.version == 2 && save.items != null && save.items.version == 2, "version");
            var s = save.items;
            Require(s.nextSeq > 0 && s.nextSeq < long.MaxValue && ItemCatalog.Finite(s.activeSeconds) && s.activeSeconds >= 0, "clock/counter");
            Require(s.items != null && s.containers != null && s.retiredIds != null && s.receipts != null && save.players != null && save.itemPoses != null, "missing lists");
            var l = new ItemLedger(defs, tuning) { nextSeq = s.nextSeq, activeSeconds = s.activeSeconds };
            foreach (var p in save.players)
            {
                Require(p != null && !string.IsNullOrWhiteSpace(p.PlayerId) && !l.players.ContainsKey(p.PlayerId) && p.KitSlot >= 0 && p.KitSlot < 6 &&
                    (p.ActiveSlot == 255 || p.ActiveSlot >= 0 && p.ActiveSlot < 6) && ItemCatalog.Finite(p.DetachedAt) &&
                    (p.Present ? p.DetachedAt == -1 : p.DetachedAt >= 0 && p.DetachedAt <= s.activeSeconds) && p.LastPressId >= 0 &&
                    p.ActiveKitItemId != null && (p.ActiveKitItemId == "" || p.ActiveSlot == p.KitSlot), "player");
                l.players.Add(p.PlayerId, p.Copy());
            }
            foreach (var c in s.containers)
            {
                Require(c != null && !string.IsNullOrWhiteSpace(c.Id) && !l.containers.ContainsKey(c.Id) && c.Capacity == l.Capacity(c.Kind) && c.Capacity > 0 && c.Slots != null, "container");
                var copy = c.Copy(); Array.Resize(ref copy.Slots, copy.Capacity); l.containers.Add(copy.Id, copy);
                if (IsPersonal(c)) Require(l.players.ContainsKey(c.OwnerId) && c.Id == (c.Kind == ContainerKind.Kit ? KitId(c.OwnerId) : PocketsId(c.OwnerId)), "personal container owner");
                if (IsPersonal(c) || c.Kind == ContainerKind.Tray || c.Kind == ContainerKind.ReturnTray) copy.Open = true;
            }
            foreach (var p in l.players.Values) Require(l.Container(PocketsId(p.PlayerId)) != null && l.Container(KitId(p.PlayerId)) != null, "missing player containers");
            foreach (string id in s.retiredIds) Require(!string.IsNullOrWhiteSpace(id) && l.retired.Add(id), "retired identity");
            foreach (var r in s.items)
            {
                Require(r != null && !string.IsNullOrWhiteSpace(r.Id) && !l.items.ContainsKey(r.Id) && !l.retired.Contains(r.Id) && defs.TryGet(r.DefId, out _), "item identity/definition");
                defs.TryGet(r.DefId, out var d);
                Require(r.Count > 0 && r.Count <= d.MaxStack && r.Revision >= 0 && r.ContainerId != null && r.CarrierId != null && r.Organ != null && r.Fill != null && r.HasOrgan == (d.Class == ItemClass.Organ) &&
                    r.HasFill == ItemCatalog.HasFill(d.Class) && r.Place >= PlaceKind.Container && r.Place <= PlaceKind.Carried, "item state");
                if (r.HasOrgan)
                {
                    var o = r.Organ;
                    Require(o.Kind == d.Organ && o.Tier >= 1 && o.Tier <= 5 && ItemCatalog.Finite(o.Progress) && o.Progress >= 0 && o.Progress < 1 &&
                        ItemCatalog.Finite(o.SettledAt) && o.SettledAt >= 0 && o.SettledAt <= s.activeSeconds && o.ExtractedAtGameSeconds >= 0 &&
                        ItemCatalog.Finite(o.ColdSince) && o.ColdSince >= -1 && o.ColdSince <= s.activeSeconds &&
                        ItemCatalog.Finite(o.WarmSince) && o.WarmSince >= -1 && o.WarmSince <= s.activeSeconds &&
                        ItemCatalog.Finite(o.LastColdStint) && o.LastColdStint >= 0 && ItemCatalog.Finite(o.LastImpactAt) && o.LastImpactAt <= s.activeSeconds &&
                        (o.Tier != 1 || o.Progress == 0), "organ");
                }
                if (r.HasFill) Require(l.ValidFill(d, r.Fill, s.activeSeconds), "fill");
                l.items.Add(r.Id, r.Copy());
            }
            foreach (var c in l.containers.Values)
            {
                if (c.Kind == ContainerKind.Cooler) Require(c.Id == c.OwnerId && l.Definition(l.Find(c.Id))?.Class == ItemClass.Cooler, "orphan cooler");
                for (int n = 0; n < c.Capacity; n++)
                { var r = l.Find(c.Slots[n]); if (r == null || r.Place != PlaceKind.Container || r.ContainerId != c.Id || r.Slot != n) c.Slots[n] = null; }
            }
            var carriers = new HashSet<string>(StringComparer.Ordinal);
            foreach (var r in l.items.Values)
            {
                var d = l.Definition(r);
                if (d.Class == ItemClass.Cooler) Require(l.Container(r.Id)?.Kind == ContainerKind.Cooler, "missing cooler contents");
                if (r.Place == PlaceKind.Carried)
                {
                    Require(d.TwoHanded && l.players.ContainsKey(r.CarrierId) && carriers.Add(r.CarrierId), "carry");
                    l.Container(r.Id).Open = false;
                }
                if (r.Place != PlaceKind.Container) { r.ContainerId = ""; r.Slot = -1; if (r.Place == PlaceKind.World) r.CarrierId = ""; continue; }
                var c = l.Container(r.ContainerId);
                if (c == null || r.Slot < 0 || r.Slot >= c.Capacity || c.Slots[r.Slot] != r.Id)
                {
                    // Never expose an absent player's belongings through the repair path.
                    Require(c == null || !IsPersonal(c) && !l.DetachedContainer(c), "damaged private inventory");
                    Require(!r.ContainerId.StartsWith("pockets:", StringComparison.Ordinal) && !r.ContainerId.StartsWith("kit:", StringComparison.Ordinal), "orphan private inventory");
                    r.Place = PlaceKind.World; r.ContainerId = ""; r.Slot = -1; r.CarrierId = "";
                    if (r.HasOrgan) { r.Organ.ColdSince = -1; r.Organ.LastColdStint = 0; r.Organ.WarmSince = -1; r.Organ.CaseColdLatch = false; }
                }
                else Require(Accepts(c.Kind, d) && c.UpgradePurchased, "incompatible container or unpurchased storage");
            }
            foreach (var p in l.players.Values) Require(!l.HasKit(p.PlayerId) || string.IsNullOrEmpty(l.Container(PocketsId(p.PlayerId)).Slots[p.KitSlot]), "kit/pocket collision");
            foreach (var r in l.items.Values.Where(r => r.HasOrgan))
            {
                Require(!r.Organ.CaseColdLatch || r.Place == PlaceKind.Container && l.Container(r.ContainerId).Kind == ContainerKind.BuyerCase, "latch outside case");
                Require(WorkItemTuning.IsCold(l.StorageCore(r)) == (r.Organ.ColdSince >= 0), "cold history disagrees with storage");
                if (l.Detached(r)) Require(r.Organ.SettledAt <= l.players[l.Owner(r)].DetachedAt, "detached item clock");
            }
            foreach (var a in s.receipts)
            {
                Require(a != null && l.players.ContainsKey(a.PlayerId) && !l.receipts.ContainsKey(a.PlayerId) && a.HighWater > 0 && a.Results != null && a.Results.Count <= 64, "receipts");
                long prev = 0;
                foreach (var r in a.Results) { Require(r != null && r.RequestId > prev && r.RequestId <= a.HighWater && Enum.IsDefined(typeof(ItemError), r.Result.Error), "receipt order"); prev = r.RequestId; }
                l.receipts.Add(a.PlayerId, a.Copy());
            }
            foreach (var pose in save.itemPoses)
            {
                Require(pose != null && pose.Position.IsFinite && pose.Rotation.IsValid && l.Find(pose.Id) != null && !l.poses.ContainsKey(pose.Id), "pose");
                Require(l.Find(pose.Id).Place != PlaceKind.Container, "stored item pose"); l.poses.Add(pose.Id, pose.Copy());
            }
            l.ClearMissingSelection(); return l;
        }
    }
    public static class InventoryJson
    {
        public static string Write<T>(T data)
        {
            using (var stream = new MemoryStream()) { new DataContractJsonSerializer(typeof(T)).WriteObject(stream, data); return Encoding.UTF8.GetString(stream.ToArray()); }
        }
        public static T Read<T>(string text)
        {
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(text ?? throw new ArgumentNullException(nameof(text)))) )
                return (T)new DataContractJsonSerializer(typeof(T)).ReadObject(stream);
        }
    }
    /// <summary>Host-only writer for the inventory fragment. Production saves compose it into the world transaction.</summary>
    public static class InventorySaveFile
    {
        public static void Write(string path, InventorySaveV2 save, bool isHost)
        {
            if (!isHost) throw new UnauthorizedAccessException("Only the host writes inventory saves");
            string json = InventoryJson.Write(save); string temp = path + ".tmp";
            using (var stream = new FileStream(temp, FileMode.Create, FileAccess.Write, FileShare.None))
            { byte[] bytes = Encoding.UTF8.GetBytes(json); stream.Write(bytes, 0, bytes.Length); stream.Flush(true); }
            if (File.Exists(path)) File.Replace(temp, path, path + ".bak"); else File.Move(temp, path);
        }
        public static InventorySaveV2 Load(string path, bool isHost)
        {
            if (!isHost) throw new UnauthorizedAccessException("Only the host loads authoritative inventory");
            return InventoryJson.Read<InventorySaveV2>(File.ReadAllText(path, Encoding.UTF8));
        }
        public static string V1BackupPath(string source) => Path.Combine(Path.GetDirectoryName(source) ?? "", Path.GetFileNameWithoutExtension(source) + ".v1.bak");
        // Exact original bytes, create-once. Publish the NEW v2 file only after migration/validation succeeds.
        public static InventorySaveV2 MigrateV1(string source, string destination, LegacyV1 input, IItemDefs definitions, bool isHost, out MigrationReport report)
        {
            if (!isHost) throw new UnauthorizedAccessException("Only the host migrates saves");
            string backup = V1BackupPath(source);
            var paths = new[] { source, backup, destination, destination + ".tmp", destination + ".bak" }.Select(Path.GetFullPath);
            if (paths.Distinct(StringComparer.OrdinalIgnoreCase).Count() != 5) throw new ArgumentException("Source, v1 backup and v2 publication paths must be distinct");
            if (File.Exists(destination)) throw new IOException("v2 already exists; load it instead of migrating again");
            var ledger = new ItemLedger(definitions);
            report = LegacyMigration.Apply(ledger, input, new LegacyIds(), definitions, 0);
            if (report.warnings.Count != 0) throw new InvalidDataException(string.Join("; ", report.warnings));
            var save = ledger.Snapshot(0); ItemLedger.Restore(save, definitions);
            byte[] original = File.ReadAllBytes(source);
            if (File.Exists(backup))
            { if (!original.SequenceEqual(File.ReadAllBytes(backup))) throw new IOException("Existing v1 backup does not match source"); }
            else using (var stream = new FileStream(backup, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            { stream.Write(original, 0, original.Length); stream.Flush(true); }
            Write(destination, save, true); return save;
        }
    }
}
