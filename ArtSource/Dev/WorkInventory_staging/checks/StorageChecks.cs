using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public static partial class Scenarios
    {
        private static IEnumerable<Scenario> Storage()
        {
            foreach (double at in new[] { 299.999, 300, 600, 1200, 50000 })
                yield return new Scenario("Spoilage_RoomBoundary_" + at, () => {
                    var w = new World(); string id = w.Mint(); w.L.Settle(at);
                    Equal(at < 300 ? 5 : at < 600 ? 4 : at < 1200 ? 3 : 1, w.L.Get(id).Organ.Tier);
                    if (at >= 1200) Equal(0.0, w.L.Get(id).Organ.Progress);
                });
            foreach (double at in new[] { 1499.999, 1500, 3000 })
                yield return new Scenario("Spoilage_CoolerBoundary_" + at, () => {
                    var w = new World(); string cooler = w.Cooler(), id = w.Mint(dest:Destination.ToContainer(cooler)); w.L.Settle(at);
                    Equal(at < 1500 ? 5 : at < 3000 ? 4 : 3, w.L.Get(id).Organ.Tier);
                });
            yield return new Scenario("Spoilage_PoweredFridgeAndPowerLoss", () => {
                var w = new World(); string fridge = w.Box(ContainerKind.Fridge), id = w.Mint(dest:Destination.ToContainer(fridge));
                w.L.SetPowered(fridge, false, 100000); Equal(5, w.L.Get(id).Organ.Tier); w.L.Settle(100300); Equal(4, w.L.Get(id).Organ.Tier);
                w.L.SetPowered(fridge, true, 100300); w.L.Settle(200000); Equal(4, w.L.Get(id).Organ.Tier);
            });
            yield return new Scenario("Spoilage_FractionSurvivesRoomCoolerMove", () => {
                var w = new World(); string cooler = w.Cooler(), id = w.Mint(); w.Now = 150;
                True(w.Move(id, Destination.ToContainer(cooler)).Ok); Near(0.5, w.L.Get(id).Organ.Progress); Near(900, w.L.NextGradeLossAt(id, 150));
                w.L.Settle(899.999); Equal(5, w.L.Get(id).Organ.Tier); w.L.Settle(900); Equal(4, w.L.Get(id).Organ.Tier);
            });
            yield return new Scenario("Spoilage_ExactEventTimesForLargeTick", () => {
                var w = new World(); string id = w.Mint(); w.L.Settle(1000); var events = w.L.DrainTierChanges();
                Equal(3, events.Length); Near(300, events[0].At); Near(600, events[1].At); Near(900, events[2].At); Equal(id, events[0].ItemId);
            });
            yield return new Scenario("Spoilage_QueriesAndPackagingNeverRestoreTier", () => {
                var w = new World(); string id = w.Held(102); w.Mint(115, Destination.ToContainer(ItemLedger.KitId("p")));
                w.Now = 300; Near(600, w.L.NextGradeLossAt(id, 300)); Equal(4, w.L.Get(id).Organ.Tier);
                True(w.Hold(true, 1).Ok); True(w.L.Get(id).Organ.Packaged); Equal(4, w.L.Get(id).Organ.Tier);
                w.L.Settle(600); Equal(3, w.L.Get(id).Organ.Tier);
            });
            foreach (var test in new[] { (59.999, 0.0, false), (60.0, 0.0, true), (60.0, 60.0, true), (60.0, 60.001, false), (10.0, 5.0, false) })
                yield return new Scenario("ColdChain_StintGap_" + test.Item1 + "_" + test.Item2, () => {
                    var w = new World(); string cooler = w.Cooler(), box = w.Box(ContainerKind.BuyerCase), id = w.Mint(dest:Destination.ToContainer(cooler));
                    w.Now = test.Item1; w.Move(id, Destination.ToContainer(ItemLedger.PocketsId("p"))); w.Now += test.Item2;
                    w.Move(id, Destination.ToContainer(box)); Equal(test.Item3, w.L.Get(id).Organ.CaseColdLatch);
                });
            yield return new Scenario("ColdChain_LatchSurvivesInspectionButClearsOnUnload", () => {
                var w = new World(); string cooler = w.Cooler(), box = w.Box(ContainerKind.BuyerCase), id = w.Mint(dest:Destination.ToContainer(cooler));
                w.Now = 60; w.Move(id, Destination.ToContainer(box)); w.Now = 1000; w.L.Settle(w.Now); True(w.L.Get(id).Organ.CaseColdLatch);
                w.Move(id, Destination.ToContainer(ItemLedger.PocketsId("p"))); True(!w.L.Get(id).Organ.CaseColdLatch);
                w.Move(id, Destination.ToContainer(box)); True(!w.L.Get(id).Organ.CaseColdLatch);
            });
            yield return new Scenario("ColdChain_WarmOnlyIsNeverCooled", () => {
                var w = new World(); string box = w.Box(ContainerKind.BuyerCase), id = w.Mint(); w.Now = 60; w.Move(id, Destination.ToContainer(box)); True(!w.L.Get(id).Organ.CaseColdLatch);
            });
            yield return new Scenario("ColdChain_PowerRestorationNeedsNewStint", () => {
                var w = new World(); string fridge = w.Box(ContainerKind.Fridge), id = w.Mint(dest:Destination.ToContainer(fridge));
                w.L.SetPowered(fridge, false, 60); w.L.SetPowered(fridge, true, 100); True(!w.L.IsDeliveredCold(w.L.Get(id), 159.99)); True(w.L.IsDeliveredCold(w.L.Get(id), 160));
            });
            foreach (var test in new[] { (2.4, 0), (2.4001, 1), (0.0, 0), (double.NaN, 0), (double.PositiveInfinity, 0) })
                yield return new Scenario("Impact_OrganThreshold_" + test.Item1, () => {
                    var w = new World(); string id = w.Mint(); Equal(test.Item2, w.L.ApplyImpact(id, test.Item1, 0)); Equal(5 - test.Item2, w.L.Get(id).Organ.Tier);
                });
            yield return new Scenario("Impact_CooldownDoesNotExtendOnRejectedContacts", () => {
                var w = new World(); string id = w.Mint(); Equal(1, w.L.ApplyImpact(id, 3, 0)); Equal(0, w.L.ApplyImpact(id, 3, .5)); Equal(1, w.L.ApplyImpact(id, 3, .6)); Equal(3, w.L.Get(id).Organ.Tier);
            });
            foreach (var test in new[] { (4.0, 0), (4.01, 2) })
                yield return new Scenario("Impact_ThrownCoolerAllOrgans_" + test.Item1, () => {
                    var w = new World(); string cooler = w.Cooler(); w.Mint(dest:Destination.ToContainer(cooler)); w.Mint(103, Destination.ToContainer(cooler));
                    string blood = w.Mint(110, Destination.ToContainer(cooler)); Equal(test.Item2, w.L.ApplyImpact(cooler, test.Item1, 0)); Equal(1f, w.L.Get(blood).Fill.Amount);
                });
            yield return new Scenario("Impact_DamagedFloor", () => { var w = new World(); string id = w.Mint(tier:1); Equal(0, w.L.ApplyImpact(id, 99, 0)); Equal(1, w.L.Get(id).Organ.Tier); });
            foreach (var test in new[] { (ContainerKind.Fridge, 24), (ContainerKind.Tray, 6), (ContainerKind.BuyerCase, 8), (ContainerKind.Stash, 4), (ContainerKind.ReturnTray, 8) })
                yield return new Scenario("Capacity_" + test.Item1, () => {
                    var w = new World(); string box = w.Box(test.Item1);
                    for (int i = 0; i < test.Item2; i++) w.Mint(dest:Destination.ToContainer(box));
                    Equal(ItemError.ContainerFull, w.L.MintOrgan("overflow", 102, new OrganData(), Destination.ToContainer(box), 0).Error);
                    Equal(test.Item2, w.L.GetContainer(box).Slots.Count(s => !string.IsNullOrEmpty(s)));
                });
            yield return new Scenario("Capacity_SixPocketsAndSeventhRefusedWithoutBurningId", () => {
                var w = new World(); for (int i = 0; i < 6; i++) w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p")));
                Equal(ItemError.ContainerFull, w.L.MintOrgan("seventh", 102, new OrganData(), Destination.ToContainer(ItemLedger.PocketsId("p")), 0).Error);
                True(w.L.MintOrgan("seventh", 102, new OrganData(), Destination.ToWorld(), 0).Ok);
            });
            yield return new Scenario("Stack_MergeSplitAndRetireIdentity", () => {
                var w = new World(); string a = w.Mint(114, Destination.ToContainer(ItemLedger.PocketsId("p")), count:5);
                string b = w.Mint(114, count:4); True(w.Move(b, Destination.ToContainer(ItemLedger.PocketsId("p"))).Ok);
                Equal(9, w.L.Get(a).Count); True(w.L.IsRetired(b));
                var split = w.Move(a, Destination.ToWorld(), count:3); Equal(6, w.L.Get(a).Count); Equal(3, w.L.Get(split.ItemId).Count); True(a != split.ItemId);
                Equal(ItemError.None, w.L.Consume(split.ItemId, 3)); True(w.L.IsRetired(split.ItemId));
            });
            yield return new Scenario("Stack_FullStackUsesNextSlot", () => {
                var w = new World(); string a = w.Mint(114, Destination.ToContainer(ItemLedger.PocketsId("p")), count:20);
                string b = w.Mint(114, Destination.ToContainer(ItemLedger.PocketsId("p")), count:1); True(a != b); Equal(20, w.L.Get(a).Count);
            });
            yield return new Scenario("Ownership_CannotTakeOtherPlayerPockets", () => {
                var w = new World(); string id = w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p")));
                Equal(ItemError.NotOwner, w.Move(id, Destination.ToContainer(ItemLedger.PocketsId("q")), "q").Error);
                Equal(ItemError.NotOwner, w.Move(id, Destination.ToContainer(ItemLedger.PocketsId("q"))).Error);
            });
            yield return new Scenario("Ownership_CarriedCoolerCannotBeStolen", () => { var w = new World(); string id = w.Cooler(); w.Move(id, Destination.ToCarry("p")); Equal(ItemError.NotOwner, w.Move(id, Destination.ToWorld(), "q").Error); });
            yield return new Scenario("Container_ClosedTransferAndCarriedOpenRefused", () => {
                var w = new World(); string cooler = w.Cooler(false), id = w.Mint(); Equal(ItemError.ContainerClosed, w.Move(id, Destination.ToContainer(cooler)).Error);
                w.L.SetOpen(cooler, true); w.Move(id, Destination.ToContainer(cooler)); w.Move(cooler, Destination.ToCarry("p"));
                True(!w.L.GetContainer(cooler).Open); Equal(ItemError.Busy, w.L.SetOpen(cooler, true)); Equal(ItemError.ContainerClosed, w.Move(id, Destination.ToWorld()).Error);
                Equal(StorageClass.PortableCooler, w.L.StorageOf(w.L.Get(id)));
            });
            yield return new Scenario("Container_CoolerCannotNest", () => { var w = new World(); string a = w.Cooler(), b = w.Cooler(); Equal(ItemError.TwoHandedOnly, w.Move(a, Destination.ToContainer(b)).Error); Equal(ItemError.NotAccepted, w.Move(a, Destination.ToContainer(a)).Error); });
            yield return new Scenario("Container_DestroyCoolerSpillsAndStopsCooling", () => {
                var w = new World(); string cooler = w.Cooler(), id = w.Mint(dest:Destination.ToContainer(cooler)); w.L.Settle(100); w.L.Retire(cooler);
                Equal(PlaceKind.World, w.L.Get(id).Place); Equal(StorageClass.Room, w.L.StorageOf(w.L.Get(id))); True(w.L.IsRetired(cooler)); Near(100, w.L.Get(id).Organ.WarmSince);
            });
            yield return new Scenario("Van_PurchaseEnablesShelfAndExactlyTwoMounts", () => {
                var w = new World(); w.L.EnsureVan("v"); string organ = w.Mint(), a = w.Cooler(), b = w.Cooler(), c = w.Cooler();
                Equal(ItemError.UpgradeRequired, w.Move(organ, Destination.ToContainer("vanshelf:v")).Error); Equal(ItemError.UpgradeRequired, w.Move(a, Destination.ToContainer("vanmount:v:0")).Error);
                w.L.PurchaseVanStorage("v"); True(w.Move(organ, Destination.ToContainer("vanshelf:v")).Ok); True(w.Move(a, Destination.ToContainer("vanmount:v:0")).Ok); True(w.Move(b, Destination.ToContainer("vanmount:v:1")).Ok);
                Equal(ItemError.ContainerFull, w.Move(c, Destination.ToContainer("vanmount:v:0")).Error); Equal(PlaceKind.World, w.L.Get(c).Place);
            });
            yield return new Scenario("Receipts_RepeatPayloadCannotMoveTwice", () => {
                var w = new World(); string id = w.Mint(); var first = w.L.Move("p", 1, id, Destination.ToContainer(ItemLedger.PocketsId("p")), 0);
                var second = w.L.Move("p", 1, id, Destination.ToWorld(), 100); True(second.Replayed); Equal(first.ItemId, second.ItemId); Equal(PlaceKind.Container, w.L.Get(id).Place); Equal(0.0, w.L.ActiveSeconds);
            });
            yield return new Scenario("Receipts_EvictedRequestCannotReplay", () => {
                var w = new World(); string id = w.Mint();
                for (int i = 1; i <= 65; i++) w.L.Move("p", i, "missing", Destination.ToWorld(), 0);
                Equal(ItemError.StaleRequest, w.L.Move("p", 1, id, Destination.ToContainer(ItemLedger.PocketsId("p")), 0).Error); Equal(PlaceKind.World, w.L.Get(id).Place);
                Equal(64, w.L.Snapshot(0).items.receipts[0].Results.Count);
            });
            yield return new Scenario("Receipts_FailuresAreDeduplicated", () => {
                var w = new World(); w.L.Move("p", 1, "missing", Destination.ToWorld(), 0); string id = w.Mint();
                Equal(ItemError.NoSuchItem, w.L.Move("p", 1, id, Destination.ToContainer(ItemLedger.PocketsId("p")), 0).Error);
            });
            yield return new Scenario("Race_ConcurrentExtractionOnlyOneIdentity", () => {
                var w = new World(); var results = new MoveResult[20]; Parallel.For(0, results.Length, i => results[i] = w.L.MintOrgan("same", 102, new OrganData(), Destination.ToWorld(), 0));
                Equal(1, results.Count(r => r.Ok)); Equal(1, w.L.Items.Count());
            });
            yield return new Scenario("Race_SameKidneyOnlyOnePlayerWins", () => {
                var w = new World(); string id = w.Mint(); var results = new MoveResult[2];
                Parallel.Invoke(() => results[0] = w.L.Move("p", 1, id, Destination.ToContainer(ItemLedger.PocketsId("p")), 0), () => results[1] = w.L.Move("q", 1, id, Destination.ToContainer(ItemLedger.PocketsId("q")), 0));
                Equal(1, results.Count(r => r.Ok)); Equal(1, w.L.Items.Count());
            });
            yield return new Scenario("Race_LastCoolerSlotOnlyOneFits", () => {
                var w = new World(); string cooler = w.Cooler(); for (int i = 0; i < 7; i++) w.Mint(dest:Destination.ToContainer(cooler)); string a = w.Mint(), b = w.Mint(); var results = new MoveResult[2];
                Parallel.Invoke(() => results[0] = w.L.Move("p", 1, a, Destination.ToContainer(cooler), 0), () => results[1] = w.L.Move("q", 1, b, Destination.ToContainer(cooler), 0));
                Equal(1, results.Count(r => r.Ok)); Equal(8, w.L.GetContainer(cooler).Slots.Count(s => !string.IsNullOrEmpty(s)));
            });
            yield return new Scenario("Isolation_ReturnedRecordsAndContainersAreCopies", () => {
                var w = new World(); string id = w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p"))); w.L.Get(id).Organ.Tier = 1;
                w.L.GetContainer(ItemLedger.PocketsId("p")).Slots[0] = "broken"; Equal(5, w.L.Get(id).Organ.Tier); Equal(id, w.L.GetContainer(ItemLedger.PocketsId("p")).Slots[0]);
            });
        }
    }
}
