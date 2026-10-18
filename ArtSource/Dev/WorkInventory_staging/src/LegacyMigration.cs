// G39: deterministic conversion of the INVENTORY portion of CaptureSaveData v1.
// The host adapter supplies these plain DTOs and retains NPC/van/table-tool/fund blocks unchanged.
using System;
using System.Collections.Generic;
using System.Linq;

namespace OnlyVolunteers.Items.Core
{
    [Serializable]
    public sealed class LegacyKit
    { public int ties; public float anesthesiaBarrel = -1; public float anesthesiaStock = -1; public float bloodFill; public int bloodBags; public int tool; }
    [Serializable]
    public sealed class LegacyTableItem
    {
        public string id = ""; public int kind; public int grade; public float freshness; public bool sealedBlood; public bool expired;
        public PlainVector position; public PlainRotation rotation = PlainRotation.Identity;
    }
    [Serializable]
    public sealed class LegacyStack { public int itemId; public int count; public int unitValue; }
    [Serializable]
    public sealed class LegacyV1
    {
        public string hostPlayerId = "host";
        public PlainVector playerPosition;
        public LegacyKit kit = new LegacyKit();
        public int bodyBags;
        public string tableId = "legacy-table";
        public bool hasTable;
        public float tableAnesthesiaStock, tableAnesthesiaBarrel, tableBloodFill;
        public int bloodBagCount = 3, bagsUsedMask;
        public List<LegacyTableItem> tableItems = new List<LegacyTableItem>();
        public List<LegacyStack> hotbar = new List<LegacyStack>();
    }
    public sealed class LegacyIds
    {
        public int Kidney = 102, Liver = 103, BloodBag = 110, BloodSyringe = 111, AnesthesiaSyringe = 112, AnestheticVial = 113,
            ZipTies = 114, BodyBag = 202, IntroSyringe = 109, EmptyBloodBag = 116;
        public int[] OrganIds = { 101, 102, 103, 104, 105, 106 };
    }
    public sealed class MigrationReport
    {
        public int minted;
        public List<string> legacyTableIds = new List<string>();
        public List<string> overflowToWorld = new List<string>();
        public List<string> warnings = new List<string>();
        public float retainedTableAnesthesiaBarrel, retainedTableBloodFill;
    }
    public static class LegacyMigration
    {
        public static MigrationReport Apply(ItemLedger ledger, LegacyV1 v1, LegacyIds ids, IItemDefs defs, double now)
        {
            if (ledger == null || v1 == null || ids == null || defs == null) throw new ArgumentNullException(nameof(v1));
            if (ledger.Items.Any() || ledger.Snapshot(now).players.Count != 0) throw new InvalidOperationException("Migration requires a fresh ledger");
            if (string.IsNullOrWhiteSpace(v1.hostPlayerId) || !v1.playerPosition.IsFinite) throw new ArgumentException("Legacy player data");
            var rep = new MigrationReport { retainedTableAnesthesiaBarrel = v1.tableAnesthesiaBarrel, retainedTableBloodFill = v1.tableBloodFill };
            ledger.EnsurePlayer(v1.hostPlayerId);
            string pocket = ItemLedger.PocketsId(v1.hostPlayerId), kit = ItemLedger.KitId(v1.hostPlayerId);
            var selected = new Dictionary<int, string>();
            MoveResult Put(int defId, Func<Destination, MoveResult> mint, string label, string preferred = null)
            {
                defs.TryGet(defId, out var def);
                string destination = preferred ?? (def != null && ItemCatalog.KitOrder(def.Class) >= 0 ? kit : pocket);
                var res = mint(Destination.ToContainer(destination));
                if (!res.Ok && (res.Error == ItemError.ContainerFull || res.Error == ItemError.SlotOccupied) && destination != pocket)
                    res = mint(Destination.ToContainer(pocket));
                if (!res.Ok && (res.Error == ItemError.ContainerFull || res.Error == ItemError.SlotOccupied || res.Error == ItemError.TwoHandedOnly))
                {
                    res = mint(Destination.ToWorld());
                    if (res.Ok) { rep.overflowToWorld.Add(res.ItemId); ledger.SetPose(new ItemPose { Id = res.ItemId, Position = v1.playerPosition }); }
                }
                if (res.Ok) { rep.minted++; if (!selected.ContainsKey(defId)) selected.Add(defId, res.ItemId); }
                else rep.warnings.Add(label + ": " + res.Error);
                return res;
            }
            void Stack(int defId, int count, string label, string preferred = null)
            {
                if (count < 0 || count > 100000) { rep.warnings.Add(label + ": invalid count"); return; }
                if (!defs.TryGet(defId, out var def)) { rep.warnings.Add(label + ": unknown definition"); return; }
                while (count > 0) { int n = Math.Min(count, def.MaxStack); Put(defId, d => ledger.Mint(defId, n, d, now), label, preferred); count -= n; }
            }
            var k = v1.kit ?? new LegacyKit();
            Stack(ids.ZipTies, k.ties, "ties");
            Put(ids.AnesthesiaSyringe, d => ledger.MintFilled(ids.AnesthesiaSyringe, new FillData { Amount = Math.Max(0, k.anesthesiaBarrel) }, d, now), "anesthesia syringe");
            if (k.anesthesiaStock > 0) Put(ids.AnestheticVial, d => ledger.MintFilled(ids.AnestheticVial, new FillData { Amount = k.anesthesiaStock }, d, now), "field vial");
            Put(ids.BloodSyringe, d => ledger.MintFilled(ids.BloodSyringe, new FillData { Amount = k.bloodFill,
                FilledAt = k.bloodFill > 0 ? now : -1, FillSeq = k.bloodFill > 0 ? 1 : 0 }, d, now), "blood syringe");
            Stack(ids.BodyBag, v1.bodyBags, "body bags");
            Stack(ids.BloodBag, k.bloodBags, "blood bags");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var t in v1.tableItems ?? new List<LegacyTableItem>())
            {
                if (t == null || string.IsNullOrWhiteSpace(t.id) || !seen.Add(t.id)) { rep.warnings.Add("duplicate/missing table id"); continue; }
                if (!t.position.IsFinite || !t.rotation.IsValid) { rep.warnings.Add(t.id + ": invalid pose"); continue; }
                string donor = t.id.Contains("/") ? t.id.Substring(0, t.id.IndexOf('/')) : "";
                MoveResult res;
                if (t.kind == 0 || t.kind == 1)
                {
                    if (t.grade < 0 || t.grade > 4) { rep.warnings.Add(t.id + ": invalid capture grade"); continue; }
                    res = ledger.MintOrgan(t.id, t.kind == 0 ? ids.Kidney : ids.Liver,
                        new OrganData { Tier = Tier.FromCaptureGrade(t.grade), DonorPatientId = donor }, Destination.ToWorld(), now);
                }
                else if (t.kind == 2) res = ledger.MintFilled(ids.BloodBag, new FillData { Amount = 1, DonorPatientId = donor }, Destination.ToWorld(), now, t.id);
                else if (t.kind == 3)
                {
                    if (!ItemCatalog.Finite(t.freshness) || t.freshness < 0) { rep.warnings.Add(t.id + ": invalid freshness"); continue; }
                    // Legacy freshness is elapsed unsealed seconds. Preserve remaining time, never rejuvenate.
                    double elapsed = Math.Min(t.freshness, ledger.Tuning.BloodExpirySeconds);
                    bool expired = t.expired || elapsed >= ledger.Tuning.BloodExpirySeconds;
                    res = ledger.MintFilled(ids.IntroSyringe, new FillData { Amount = expired ? 0 : 1, DonorPatientId = donor,
                        FilledAt = now, FillSeq = 1 }, Destination.ToWorld(), now, t.id);
                    if (res.Ok && !expired) ledger.SetMigratedBloodAge(res.ItemId, elapsed);
                }
                else { rep.warnings.Add(t.id + ": unknown table kind"); continue; }
                if (res.Ok)
                { rep.minted++; rep.legacyTableIds.Add(t.id + "=>" + res.ItemId); ledger.SetPose(new ItemPose { Id = res.ItemId, Position = t.position, Rotation = t.rotation }); }
                else rep.warnings.Add(t.id + ": " + res.Error);
            }
            if (v1.hasTable)
            {
                string tray = "tray:" + v1.tableId; ledger.CreateContainer(tray, ContainerKind.Tray, v1.tableId, 6);
                if (v1.tableAnesthesiaStock > 0) Put(ids.AnestheticVial, d => ledger.MintFilled(ids.AnestheticVial,
                    new FillData { Amount = v1.tableAnesthesiaStock }, d, now), "table vial", tray);
                if (v1.bloodBagCount < 0 || v1.bloodBagCount > 31 || v1.bagsUsedMask < 0) rep.warnings.Add("table bag mask/count invalid");
                else
                {
                    int remaining = 0;
                    for (int i = 0; i < v1.bloodBagCount; i++) if ((v1.bagsUsedMask & (1 << i)) == 0) remaining++;
                    Stack(ids.EmptyBloodBag, remaining, "table empty bags", tray);
                }
            }
            int index = 0;
            foreach (var s in v1.hotbar ?? new List<LegacyStack>())
            {
                int row = index++;
                if (s == null || s.count < 0 || s.count > 100000) { rep.warnings.Add("invalid hotbar count"); continue; }
                if (s.count == 0) continue;
                if (!defs.TryGet(s.itemId, out var def)) { rep.warnings.Add("unknown hotbar definition " + s.itemId); continue; }
                if (def.Class == ItemClass.Organ)
                {
                    int tier = TierFromValue(def.BaseValueCents, s.unitValue * 100L);
                    for (int i = 0; i < s.count; i++)
                    { string id = "legacy/hotbar/" + row + "/" + i; Put(s.itemId, d => ledger.MintOrgan(id, s.itemId, new OrganData { Tier = tier }, d, now), "legacy organ"); }
                }
                else Stack(s.itemId, s.count, "legacy stack");
            }
            int toolDef = k.tool == 1 ? ids.ZipTies : k.tool == 2 ? ids.AnesthesiaSyringe : k.tool == 3 ? ids.BloodSyringe : 0;
            if (selected.TryGetValue(toolDef, out var selectedId)) ledger.SelectMigratedItem(v1.hostPlayerId, selectedId);
            return rep;
        }
        public static int TierFromValue(long baseCents, long unitCents)
        {
            int best = Tier.Acceptable; decimal error = decimal.MaxValue;
            if (baseCents <= 0) return best;
            for (int tier = 1; tier <= 5; tier++)
            { decimal e = Math.Abs(baseCents * (decimal)ItemLedger.TierMultiplier(tier) - unitCents); if (e < error) { error = e; best = tier; } }
            return best;
        }
    }
    public sealed partial class ItemLedger
    {
        internal void SelectMigratedItem(string actor, string item) { lock (Gate) SelectItem(actor, item); }
        internal void SetMigratedBloodAge(string id, double elapsed) { lock (Gate) { Find(id).Fill.AgeAtAnchor = elapsed; } }
    }
}
