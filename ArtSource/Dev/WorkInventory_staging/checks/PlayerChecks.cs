using System;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public static partial class Scenarios
    {
        private static IEnumerable<Scenario> Players()
        {
            yield return new Scenario("Knockout_DropsHeldItemAndPreservesOtherPockets", () => {
                var w = new World(); string held = w.Held(102), other = w.Mint(103, Destination.ToContainer(ItemLedger.PocketsId("p")));
                True(w.L.KnockOutHeldItem("p", new PlainVector(2, 0, 0), 0).Ok); Equal(PlaceKind.World, w.L.Get(held).Place);
                Equal(PlaceKind.Container, w.L.Get(other).Place); Equal(255, w.L.GetPlayer("p").ActiveSlot); Equal(2.0, w.L.GetPose(held).Position.X);
            });
            yield return new Scenario("Knockout_DropsCarriedCoolerWithItsContents", () => {
                var w = new World(); string cooler = w.Cooler(), inside = w.Mint(dest:Destination.ToContainer(cooler)); w.Move(cooler, Destination.ToCarry("p"));
                True(w.L.KnockOutHeldItem("p", default, 0).Ok); Equal(PlaceKind.World, w.L.Get(cooler).Place); Equal(cooler, w.L.Get(inside).ContainerId);
            });
            yield return new Scenario("Knockout_CannotExposeAbsentPlayerInventory", () => {
                var w = new World(); string id = w.Held(102); w.L.LeavePlayer("p", 0);
                Equal(ItemError.PlayerAbsent, w.L.KnockOutHeldItem("p", default, 0).Error); Equal(PlaceKind.Container, w.L.Get(id).Place);
            });
            yield return new Scenario("Selection_SingleSlotTogglesEmptyHands", () => {
                var w = new World(); string id = w.Held(102); Equal(id, w.L.HeldItem("p").Id);
                True(w.L.SelectSlot("p", w.Next(), 0, 0).Ok); Equal(255, w.L.GetPlayer("p").ActiveSlot); True(w.L.HeldItem("p") == null);
            });
            yield return new Scenario("Selection_KitCyclesInOrderThenEmptyHands", () => {
                var w = new World(); var expected = new Dictionary<int, string>();
                foreach (int id in new[] { 202, 111, 116, 114, 110, 112 }) expected[id] = w.Mint(id, Destination.ToContainer(ItemLedger.KitId("p")));
                foreach (int id in new[] { 114, 112, 111, 116, 110, 202 })
                { w.L.SelectSlot("p", w.Next(), 5, 0); Equal(expected[id], w.L.HeldItem("p").Id); }
                w.L.SelectSlot("p", w.Next(), 5, 0); True(w.L.HeldItem("p") == null); Equal(255, w.L.GetPlayer("p").ActiveSlot);
                w.L.SelectSlot("p", w.Next(), 5, 0); Equal(expected[114], w.L.HeldItem("p").Id);
            });
            yield return new Scenario("Selection_KitOccupiesOneOfSixPockets", () => {
                var w = new World(); w.Mint(114, Destination.ToContainer(ItemLedger.KitId("p")));
                for (int i = 0; i < 5; i++) w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p")));
                Equal(ItemError.ContainerFull, w.L.MintOrgan("extra", 102, new OrganData(), Destination.ToContainer(ItemLedger.PocketsId("p")), 0).Error);
                Equal(6, w.L.GetContainer(ItemLedger.PocketsId("p")).Capacity);
            });
            yield return new Scenario("Selection_OccupiedKitKeyPreventsAddingKit", () => {
                var w = new World(); w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p"), 5));
                Equal(ItemError.SlotOccupied, w.L.Mint(114, 1, Destination.ToContainer(ItemLedger.KitId("p")), 0).Error);
            });
            yield return new Scenario("Selection_EmptySlotAndExplicit255", () => { var w = new World(); w.Held(102); w.L.SelectSlot("p", w.Next(), 4, 0); Equal(255, w.L.GetPlayer("p").ActiveSlot); w.L.SelectSlot("p", w.Next(), 0, 0); w.L.SelectSlot("p", w.Next(), 255, 0); True(w.L.HeldItem("p") == null); });
            yield return new Scenario("Selection_RemovingSelectedKitToolClearsSelection", () => { var w = new World(); string id = w.Mint(114, Destination.ToContainer(ItemLedger.KitId("p"))); w.L.SelectSlot("p", w.Next(), 5, 0); w.L.Consume(id, 1); Equal(255, w.L.GetPlayer("p").ActiveSlot); });
            yield return new Scenario("Carry_TwoHandsBlockSelectionAndSecondCarry", () => {
                var w = new World(); w.Held(112); string cooler = w.Cooler(), second = w.Cooler();
                w.Move(cooler, Destination.ToCarry("p")); True(w.L.HeldItem("p") == null); Equal(ItemError.TwoHandedOnly, w.L.SelectSlot("p", w.Next(), 0, 0).Error);
                Equal(ItemError.SlotOccupied, w.Move(second, Destination.ToCarry("p")).Error); Equal(ItemError.TwoHandedOnly, w.Move(cooler, Destination.ToContainer(ItemLedger.PocketsId("p"))).Error);
            });
            yield return new Scenario("Leave_WholeInventoryAndCarriedContentsRemainExact", () => {
                var w = new World(); string organ = w.Held(102), blood = w.Mint(110, Destination.ToContainer(ItemLedger.KitId("p"))), cooler = w.Cooler();
                string inside = w.Mint(103, Destination.ToContainer(cooler)); w.Move(cooler, Destination.ToCarry("p"));
                w.L.LeavePlayer("p", 100); var before = w.L.Snapshot(100); w.L.Settle(10000);
                foreach (string id in new[] { organ, blood, cooler, inside }) True(!w.L.IsWorldAvailable(id), id);
                Equal(PlaceKind.Carried, w.L.Get(cooler).Place); Equal(cooler, w.L.Get(inside).ContainerId);
                Equal(ItemError.PlayerAbsent, w.L.Move("q", 1, cooler, Destination.ToCarry("q"), 10000).Error);
                Equal(ItemError.PlayerAbsent, w.L.Retire(inside)); Equal(0, w.L.ApplyImpact(cooler, 9, 10000));
                w.L.RejoinPlayer("p", 10000); var after = w.L.Snapshot(10000);
                foreach (var old in before.items.items)
                {
                    var current = after.items.items.Single(r => r.Id == old.Id); Equal(old.DefId, current.DefId); Equal(old.Count, current.Count);
                    Equal(old.Place, current.Place); Equal(old.ContainerId, current.ContainerId); Equal(old.Slot, current.Slot); Equal(old.CarrierId, current.CarrierId);
                    Equal(old.Organ.Tier, current.Organ.Tier); Near(old.Organ.Progress, current.Organ.Progress); Equal(old.Organ.DonorPatientId, current.Organ.DonorPatientId);
                }
                Equal(0, w.L.GetPlayer("p").ActiveSlot); Equal(cooler, w.L.CarriedItem("p").Id);
            });
            yield return new Scenario("Leave_BloodExpiryFreezesAndResumes", () => {
                var w = new World(); string id = w.Mint(111, Destination.ToContainer(ItemLedger.KitId("p")), fill:new FillData { Amount = 1, FilledAt = 0, FillSeq = 1 });
                w.L.LeavePlayer("p", 60); True(!w.L.BloodExpired(id, 10000)); w.L.RejoinPlayer("p", 10000);
                True(!w.L.BloodExpired(id, 10059.99)); True(w.L.BloodExpired(id, 10060));
            });
            yield return new Scenario("Leave_DoesNotEarnFreeColdStint", () => {
                var w = new World(); string cooler = w.Cooler(), id = w.Mint(dest:Destination.ToContainer(cooler)); w.Move(cooler, Destination.ToCarry("p"));
                w.L.LeavePlayer("p", 10); w.L.RejoinPlayer("p", 10000);
                True(!w.L.IsDeliveredCold(w.L.Get(id), 10000)); True(w.L.IsDeliveredCold(w.L.Get(id), 10050));
            });
            yield return new Scenario("Leave_IsIdempotentAndDoesNotResetFreezeAnchor", () => {
                var w = new World(); w.Held(102); w.L.LeavePlayer("p", 10); w.L.LeavePlayer("p", 100); Near(10, w.L.GetPlayer("p").DetachedAt);
                w.L.RejoinPlayer("p", 100); Equal(5, w.L.HeldItem("p").Organ.Tier);
            });
            yield return new Scenario("Leave_OtherPlayersAndWorldKeepSpoiling", () => {
                var w = new World(); string personal = w.Held(102), world = w.Mint(); w.L.LeavePlayer("p", 0); w.L.Settle(300);
                Equal(5, w.L.Get(personal).Organ.Tier); Equal(4, w.L.Get(world).Organ.Tier);
            });
            yield return new Scenario("Arrest_OnlyMostValuableItemConfiscated", () => {
                var w = new World(); string kidney = w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p"))), liver = w.Mint(103, Destination.ToContainer(ItemLedger.PocketsId("p")), tier:2);
                string teamHeart = w.Mint(101); Equal(kidney, w.L.MostValuableOf("p", 0).Id);
                Equal(kidney, w.L.ConfiscateMostValuable("p", 0).Id); True(w.L.IsRetired(kidney)); True(w.L.Get(liver) != null && w.L.Get(teamHeart) != null);
            });
            yield return new Scenario("Arrest_CarriedCoolerIsOneConfiscatedUnit", () => {
                var w = new World(); string cooler = w.Cooler(), inside = w.Mint(tier:1, dest:Destination.ToContainer(cooler)); w.Move(cooler, Destination.ToCarry("p"));
                Equal(cooler, w.L.ConfiscateMostValuable("p", 0).Id); True(w.L.IsRetired(cooler) && w.L.IsRetired(inside));
            });
            yield return new Scenario("Arrest_KitSuppliesParticipateAndAbsentIsUnavailable", () => {
                var w = new World(); string ties = w.Mint(114, Destination.ToContainer(ItemLedger.KitId("p")), count:20); Equal(ties, w.L.MostValuableOf("p", 0).Id);
                w.L.LeavePlayer("p", 0); True(w.L.MostValuableOf("p", 0) == null);
            });
            yield return new Scenario("Snapshot_LateJoinContainsVisibleCoolerAndPrivateBlocks", () => {
                var w = new World(); string cooler = w.Cooler(), organ = w.Mint(dest:Destination.ToContainer(cooler)); w.Held(112);
                var s = w.L.Snapshot(0); Equal(2, s.players.Count); Equal(6, s.items.containers.Single(c => c.Id == ItemLedger.PocketsId("p")).Capacity);
                True(s.items.containers.Single(c => c.Id == cooler).Open); Equal(organ, s.items.containers.Single(c => c.Id == cooler).Slots[0]);
            });
        }
    }
}
