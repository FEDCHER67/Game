using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public static partial class Scenarios
    {
        private static IEnumerable<Scenario> Saves()
        {
            yield return new Scenario("Migration_BackupCannotBeUsedAsV2Destination", () => {
                string root = TestDirectory(), source = Path.Combine(root, "original.json"); File.WriteAllText(source, "original");
                Throws<ArgumentException>(() => InventorySaveFile.MigrateV1(source, InventorySaveFile.V1BackupPath(source), new LegacyV1(), ItemCatalog.CreateDefaults(), true, out _));
                Equal("original", File.ReadAllText(source)); True(!File.Exists(InventorySaveFile.V1BackupPath(source)));
            });
            yield return new Scenario("Save_JsonRoundTripExactAndNoOfflineSpoilage", () => {
                var w = new World(); string cooler = w.Cooler(), id = w.Mint(dest:Destination.ToContainer(cooler)); w.Held(112); w.Move(cooler, Destination.ToCarry("p"));
                w.L.SetPose(new ItemPose { Id = cooler, Position = new PlainVector(10, 2, -8) });
                w.L.LeavePlayer("p", 200); var first = w.L.Snapshot(300); string json = InventoryJson.Write(first);
                var loaded = InventoryJson.Read<InventorySaveV2>(json); var l = ItemLedger.Restore(loaded, w.Defs);
                Equal(json, InventoryJson.Write(l.Snapshot(300))); Equal(5, l.Get(id).Organ.Tier); Equal(0, l.GetPlayer("p").ActiveSlot);
                l.RejoinPlayer("p", 10000); Equal(cooler, l.CarriedItem("p").Id); Near(200.0 / 1500, l.Get(id).Organ.Progress);
                Equal(-8.0, l.GetPose(cooler).Position.Z);
            });
            yield return new Scenario("Save_ReceiptsAndRetiredIdentitiesSurvive", () => {
                var w = new World(); string id = w.Mint(); var result = w.L.Move("p", 1, id, Destination.ToContainer(ItemLedger.PocketsId("p")), 0); w.L.Retire(id);
                var l = ItemLedger.Restore(InventoryJson.Read<InventorySaveV2>(InventoryJson.Write(w.L.Snapshot(0))), w.Defs);
                True(l.Move("p", 1, id, Destination.ToWorld(), 0).Replayed); Equal(ItemError.AlreadyExists, l.MintOrgan(id, 102, new OrganData(), Destination.ToWorld(), 0).Error);
                Equal(result.ItemId, l.Move("p", 1, id, Destination.ToWorld(), 0).ItemId);
            });
            yield return new Scenario("Save_KitSubselectionSurvives", () => {
                var w = new World(); w.Mint(114, Destination.ToContainer(ItemLedger.KitId("p"))); string syringe = w.Mint(112, Destination.ToContainer(ItemLedger.KitId("p")));
                w.L.SelectSlot("p", w.Next(), 5, 0); w.L.SelectSlot("p", w.Next(), 5, 0);
                var l = ItemLedger.Restore(w.L.Snapshot(0), w.Defs); Equal(syringe, l.HeldItem("p").Id); Equal(5, l.GetPlayer("p").ActiveSlot);
            });
            yield return new Scenario("Save_PurchasedVanFlagsAndMountedCoolerSurvive", () => {
                var w = new World(); w.L.EnsureVan("v", true); string cooler = w.Cooler(); w.Move(cooler, Destination.ToContainer("vanmount:v:0"));
                var l = ItemLedger.Restore(w.L.Snapshot(0), w.Defs); True(l.GetContainer("vanshelf:v").UpgradePurchased); Equal(cooler, l.GetContainer("vanmount:v:0").Slots[0]);
            });
            yield return new Scenario("Save_RestoreAndInputSnapshotsAreIsolated", () => {
                var w = new World(); string id = w.Mint(); var save = w.L.Snapshot(0); var l = ItemLedger.Restore(save, w.Defs);
                save.items.items[0].Organ.Tier = 1; save.players[0].ActiveSlot = 3; Equal(5, l.Get(id).Organ.Tier); Equal(5, w.L.Get(id).Organ.Tier);
            });
            yield return new Scenario("Save_OrphanTeamItemRepairedToWorld", () => {
                var w = new World(); string tray = w.Box(ContainerKind.Tray), id = w.Mint(dest:Destination.ToContainer(tray)); var save = w.L.Snapshot(0);
                save.items.containers.Single(c => c.Id == tray).Slots[0] = "ghost"; var l = ItemLedger.Restore(save, w.Defs); Equal(PlaceKind.World, l.Get(id).Place);
                True(string.IsNullOrEmpty(l.GetContainer(tray).Slots[0]));
            });
            yield return new Scenario("Save_PrivateOrphanIsRejectedWithoutLeakingItems", () => {
                var w = new World(); w.Held(102); w.L.LeavePlayer("p", 0); var save = w.L.Snapshot(0); save.items.containers.Single(c => c.Id == ItemLedger.PocketsId("p")).Slots[0] = "";
                Throws<InvalidDataException>(() => ItemLedger.Restore(save, w.Defs));
            });
            foreach (string malformed in new[] { "futureVersion", "duplicate", "retiredLive", "invalidTier", "nanClock", "unknownDef", "badCapacity", "badFill", "badPose" })
                yield return new Scenario("Save_RejectMalformed_" + malformed, () => {
                    var w = new World(); string id = w.Mint(); w.Mint(111); var s = w.L.Snapshot(0);
                    var organ = s.items.items.Single(r => r.Id == id);
                    if (malformed == "futureVersion") s.version = 3;
                    if (malformed == "duplicate") s.items.items.Add(organ.Copy());
                    if (malformed == "retiredLive") s.items.retiredIds.Add(id);
                    if (malformed == "invalidTier") organ.Organ.Tier = 0;
                    if (malformed == "nanClock") s.items.activeSeconds = double.NaN;
                    if (malformed == "unknownDef") organ.DefId = 9999;
                    if (malformed == "badCapacity") s.items.containers[0].Capacity = 99999;
                    if (malformed == "badFill") s.items.items.Single(r => r.DefId == 111).Fill.Amount = float.PositiveInfinity;
                    if (malformed == "badPose") s.itemPoses[0].Position.Z = double.NaN;
                    Throws<InvalidDataException>(() => ItemLedger.Restore(s, w.Defs));
                });
            yield return new Scenario("Save_HostOnlyAtomicWriteAndBackup", () => {
                string root = TestDirectory(); string path = Path.Combine(root, "inventory.json"); var w = new World(); w.Mint();
                Throws<UnauthorizedAccessException>(() => InventorySaveFile.Write(path, w.L.Snapshot(0), false)); True(!File.Exists(path) && !File.Exists(path + ".tmp"));
                InventorySaveFile.Write(path, w.L.Snapshot(0), true); string original = File.ReadAllText(path); w.Mint(103); InventorySaveFile.Write(path, w.L.Snapshot(0), true);
                Equal(original, File.ReadAllText(path + ".bak")); Equal(2, InventorySaveFile.Load(path, true).items.items.Count); True(!File.Exists(path + ".tmp"));
                Throws<UnauthorizedAccessException>(() => InventorySaveFile.Load(path, false));
            });
            yield return new Scenario("Migration_LegacyKitTableIdsGradesAndTool", () => {
                var l = new ItemLedger(ItemCatalog.CreateDefaults());
                var old = new LegacyV1 { hostPlayerId = "host", kit = new LegacyKit { ties = 7, anesthesiaBarrel = 1.2f, anesthesiaStock = 8, bloodFill = .4f, bloodBags = 3, tool = 3 }, bodyBags = 2 };
                old.tableItems.Add(new LegacyTableItem { id = "patient/kidney/0", kind = 0, grade = 2, position = new PlainVector(1, 2, 3) });
                old.tableItems.Add(new LegacyTableItem { id = "patient/blood/0", kind = 2 }); old.hotbar.Add(new LegacyStack { itemId = 102, count = 2, unitValue = 400 });
                var report = LegacyMigration.Apply(l, old, new LegacyIds(), ItemCatalog.CreateDefaults(), 0);
                Equal(0, report.warnings.Count); Equal(12, report.minted); Equal(3, l.Get("patient/kidney/0").Organ.Tier); True(l.Get("patient/blood/0") != null);
                Equal(7, l.FirstOfClass(ItemLedger.KitId("host"), ItemClass.ZipTies).Count); Equal(111, l.HeldItem("host").DefId); Equal(3.0, l.GetPose("patient/kidney/0").Position.Z);
                Equal(3, LegacyMigration.TierFromValue(25000, 40000));
            });
            yield return new Scenario("Migration_SplitsStacksAndPositionsOverflow", () => {
                var l = new ItemLedger(ItemCatalog.CreateDefaults()); var v1 = new LegacyV1 { kit = new LegacyKit { ties = 45, bloodBags = 20 }, bodyBags = 12, playerPosition = new PlainVector(9, 0, 3) };
                var r = LegacyMigration.Apply(l, v1, new LegacyIds(), ItemCatalog.CreateDefaults(), 0);
                Equal(0, r.warnings.Count); True(r.overflowToWorld.Count > 0); Equal(45, l.Items.Where(i => i.DefId == 114).Sum(i => i.Count)); Equal(12, l.Items.Where(i => i.DefId == 202).Sum(i => i.Count));
                foreach (string id in r.overflowToWorld) Equal(9.0, l.GetPose(id).Position.X);
            });
            yield return new Scenario("Migration_DeterministicIdsAndNoSecondApply", () => {
                var defs = ItemCatalog.CreateDefaults(); var a = new ItemLedger(defs); var b = new ItemLedger(defs); var old = new LegacyV1(); old.hotbar.Add(new LegacyStack { itemId = 102, count = 2, unitValue = 250 });
                LegacyMigration.Apply(a, old, new LegacyIds(), defs, 0); LegacyMigration.Apply(b, old, new LegacyIds(), defs, 0); Equal(InventoryJson.Write(a.Snapshot(0)), InventoryJson.Write(b.Snapshot(0)));
                Throws<InvalidOperationException>(() => LegacyMigration.Apply(a, old, new LegacyIds(), defs, 0));
            });
            yield return new Scenario("Migration_TableStockMaskAndPartialToolsRetained", () => {
                var defs = ItemCatalog.CreateDefaults(); var l = new ItemLedger(defs); var old = new LegacyV1 { hasTable = true, tableAnesthesiaStock = 5, tableAnesthesiaBarrel = .7f, tableBloodFill = .2f, bloodBagCount = 3, bagsUsedMask = 5 };
                var r = LegacyMigration.Apply(l, old, new LegacyIds(), defs, 0); Equal(0, r.warnings.Count); Equal(.7f, r.retainedTableAnesthesiaBarrel); Equal(.2f, r.retainedTableBloodFill);
                Equal(5f, l.FirstOfClass("tray:legacy-table", ItemClass.AnestheticVial).Fill.Amount); Equal(1, l.FirstOfClass("tray:legacy-table", ItemClass.EmptyBloodBag).Count);
            });
            yield return new Scenario("Migration_IntroBloodPreservesRemainingExpiry", () => {
                var defs = ItemCatalog.CreateDefaults(); var l = new ItemLedger(defs); var old = new LegacyV1(); old.tableItems.Add(new LegacyTableItem { id = "blood-old", kind = 3, freshness = 90 });
                var r = LegacyMigration.Apply(l, old, new LegacyIds(), defs, 0); Equal(0, r.warnings.Count); True(!l.BloodExpired("blood-old", 29.99)); True(l.BloodExpired("blood-old", 30));
            });
            yield return new Scenario("Migration_FileBackupExactBytesAndOnceOnly", () => {
                string root = TestDirectory(), source = Path.Combine(root, "capture_stageA_v01.json"), target = Path.Combine(root, "inventory_v2.json");
                byte[] original = System.Text.Encoding.UTF8.GetBytes("{\"version\":1,\"npcs\":[\"preserve\"]}\r\n"); File.WriteAllBytes(source, original);
                InventorySaveFile.MigrateV1(source, target, new LegacyV1(), ItemCatalog.CreateDefaults(), true, out var r); Equal(0, r.warnings.Count);
                True(original.SequenceEqual(File.ReadAllBytes(InventorySaveFile.V1BackupPath(source)))); True(original.SequenceEqual(File.ReadAllBytes(source)));
                Throws<IOException>(() => InventorySaveFile.MigrateV1(source, target, new LegacyV1(), ItemCatalog.CreateDefaults(), true, out _));
            });
            yield return new Scenario("Migration_ExistingDifferentBackupIsNeverOverwritten", () => {
                string root = TestDirectory(), source = Path.Combine(root, "old.json"), target = Path.Combine(root, "new.json"); File.WriteAllText(source, "original"); File.WriteAllText(InventorySaveFile.V1BackupPath(source), "different");
                Throws<IOException>(() => InventorySaveFile.MigrateV1(source, target, new LegacyV1(), ItemCatalog.CreateDefaults(), true, out _)); True(!File.Exists(target)); Equal("different", File.ReadAllText(InventorySaveFile.V1BackupPath(source)));
            });
        }
        private static string TestDirectory()
        {
            string dir = Path.Combine(@"C:\Dev\Game\ArtSource\Dev\WorkInventory_staging\tmp", Guid.NewGuid().ToString("N")); Directory.CreateDirectory(dir); return dir;
        }
    }
}
