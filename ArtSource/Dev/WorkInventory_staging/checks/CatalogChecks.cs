using System;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public static partial class Scenarios
    {
        private static IEnumerable<Scenario> Catalog()
        {
            foreach (var d in ItemCatalog.CreateDefaults().All)
                yield return new Scenario("Catalog_MintAndRoundTrip_" + d.Key, () => {
                    var w = new World(); string id = w.Mint(d.Id); var r = w.L.Get(id);
                    Equal(d.Class == ItemClass.Organ, r.HasOrgan); Equal(ItemCatalog.HasFill(d.Class), r.HasFill);
                    Equal(1, r.Count); Equal(d.Id, r.DefId);
                    var restored = ItemLedger.Restore(w.L.Snapshot(0), w.Defs); Equal(r.DefId, restored.Get(id).DefId);
                    if (d.Class == ItemClass.Cooler) { Equal(8, restored.GetContainer(id).Capacity); True(!restored.GetContainer(id).Open); }
                });
            for (int grade = 0; grade < 5; grade++)
            {
                int g = grade;
                yield return new Scenario("Quality_CaptureMapping_" + g, () => { Equal(g + 1, Tier.FromCaptureGrade(g)); Equal(g, Tier.ToCaptureGrade(g + 1)); Equal((g + 1) * 20, Tier.DisplayPercent(g + 1)); });
            }
            foreach (int invalid in new[] { -1, 5, int.MaxValue })
                yield return new Scenario("Quality_RejectInvalidCaptureGrade_" + invalid, () => Throws<ArgumentOutOfRangeException>(() => Tier.FromCaptureGrade(invalid)));
            foreach (int invalid in new[] { 0, 6, -1 })
                yield return new Scenario("Quality_RejectInvalidTier_" + invalid, () => Throws<ArgumentOutOfRangeException>(() => Tier.ToCaptureGrade(invalid)));
            foreach (int id in new[] { 114, 115, 116, 117, 202 })
                yield return new Scenario("Stack_RejectOversizedMint_" + id, () => {
                    var w = new World(); w.Defs.TryGet(id, out var d);
                    Equal(ItemError.BadRequest, w.L.Mint(id, d.MaxStack + 1, Destination.ToWorld(), 0).Error); True(!w.L.Items.Any());
                });
            yield return new Scenario("Catalog_DefinitionsAreDefensiveCopies", () => {
                var d = new ItemDef { Id = 900, Key = "ties", Class = ItemClass.ZipTies, MaxStack = 2 }; var t = new ItemDefTable().Add(d); d.MaxStack = 999;
                t.TryGet(900, out var a); Equal(2, a.MaxStack); a.MaxStack = 99; t.TryGet(900, out var b); Equal(2, b.MaxStack);
            });
            yield return new Scenario("Catalog_RejectStatefulStacks", () => Throws<ArgumentException>(() => new ItemDefTable().Add(new ItemDef { Id = 1, Key = "organ", Class = ItemClass.Organ, MaxStack = 2 })));
            foreach (var test in new[] { (0.0, 0.0), (44.9, 0.0), (45.0, 0.0), (65.0, .5), (85.0, 0.0), (105.0, .5) })
                yield return new Scenario("Corpse_UnfinishedInterval_" + test.Item1, () => Near(test.Item2, ItemCatalog.CorpseProgress(test.Item1)));
            yield return new Scenario("Provenance_TwinRoleMatchesButUnrelatedTypeDoesNot", () => {
                var w = new World(); var o = w.L.Get(w.Mint()).Organ; o.Packaged = true;
                True(ItemCatalog.MatchesOrder(o, "lineage-1", "HAMLET_BODYBUILDER", OrganKind.Kidney, 3, true));
                o.DonorPatientId = "twin-patient"; o.DonorPersonId = "twin-person";
                True(ItemCatalog.MatchesOrder(o, "lineage-1", "HAMLET_BODYBUILDER", OrganKind.Kidney, 3, true));
                o.DonorRoleKey = "another-bodybuilder";
                True(!ItemCatalog.MatchesOrder(o, "lineage-1", "HAMLET_BODYBUILDER", OrganKind.Kidney, 3, true));
            });
            yield return new Scenario("Provenance_PatientFallback", () => Equal("patient", ItemCatalog.OrderSource(new OrganData { DonorPatientId = "patient" })));
            yield return new Scenario("Tuning_CopyCannotChangeLiveRules", () => { var w = new World(); w.L.Tuning.RoomSecondsPerGrade = 1; string id = w.Mint(); w.L.Settle(1); Equal(5, w.L.Get(id).Organ.Tier); });
            yield return new Scenario("Tuning_InvalidZeroRateRejected", () => Throws<ArgumentException>(() => new ItemLedger(ItemCatalog.CreateDefaults(), new WorkItemTuning { RoomSecondsPerGrade = 0 })));
        }
    }
}
