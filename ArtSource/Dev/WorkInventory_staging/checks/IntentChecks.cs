using System;
using System.Collections.Generic;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public static partial class Scenarios
    {
        private static IEnumerable<Scenario> Intents()
        {
            yield return new Scenario("BloodSale_RetiresPortionAndKeepsReusableTool", () => {
                var w = new World(); string id = w.Held(111, new FillData { Amount = 1, FilledAt = 0, FillSeq = 1 });
                Equal(ItemError.None, w.L.RetireBloodPortion(id, 1, 0)); True(w.L.IsRetired(id + "#1")); Equal(0f, w.L.Get(id).Fill.Amount);
                Equal("DrawBlood", w.Hold(false, 4.5).Effect); Equal(2, w.L.Get(id).Fill.FillSeq);
                Equal(ItemError.None, w.L.RetireBloodPortion(id, 1, w.Now)); Equal(1f, w.L.Get(id).Fill.Amount); Equal(id + "#2", w.L.BloodSaleIdentity(id));
            });
            yield return new Scenario("BloodSale_RejectsExpiredOrWrongFillSequence", () => {
                var w = new World(); string id = w.Held(111, new FillData { Amount = 1, FilledAt = 0, FillSeq = 1 });
                Equal(ItemError.BadRequest, w.L.RetireBloodPortion(id, 2, 0)); Equal(ItemError.BloodExpired, w.L.RetireBloodPortion(id, 1, 120)); Equal(1f, w.L.Get(id).Fill.Amount);
            });
            yield return new Scenario("Intent_ResolvedTargetMustMatchRequestedObject", () => {
                var w = new World(); string id = w.Mint(); var c = w.Context(); c.ResolvedItemId = "other-object";
                Equal(ItemError.InvalidTarget, w.Send(new ItemIntent { Kind = ItemIntentKind.PickUp, ItemId = id }, c).Error); Equal(PlaceKind.World, w.L.Get(id).Place);
            });
            yield return new Scenario("Tool_StandingUnrestrainedTargetCannotBeTied", () => {
                var w = new World(); string id = w.Held(114); var c = w.Context(); c.Asleep = false; c.Downed = false;
                Equal(ItemError.InvalidTarget, w.Hold(false, 1, c).Error); Equal(1, w.L.Get(id).Count);
            });
            yield return new Scenario("Tool_AlreadyTiedLimbConsumesNothing", () => {
                var w = new World(); string id = w.Held(114); var c = w.Context(); c.HandsTied = true;
                Equal(ItemError.InvalidTarget, w.Hold(false, 1, c).Error); Equal(1, w.L.Get(id).Count);
            });
            foreach (string block in new[] { "driving", "phone", "table", "buyer", "body" })
                yield return new Scenario("Intent_BlockedContextPreservesSelection_" + block, () => {
                    var w = new World(); string id = w.Held(112, new FillData { Amount = 1 }); var c = w.Context();
                    c.Driving = block == "driving"; c.Phone = block == "phone"; c.TableCamera = block == "table"; c.BuyerCamera = block == "buyer"; c.HoldingBody = block == "body";
                    Equal(block == "body" ? ItemError.EmptyHandsRequired : ItemError.Busy, w.Send(new ItemIntent { Kind = ItemIntentKind.SelectSlot, Slot = 255 }, c).Error);
                    Equal(id, w.L.HeldItem("p").Id);
                });
            yield return new Scenario("Intent_ConnectionOwnershipCannotBeForged", () => {
                var w = new World(); w.Held(112); var c = w.Context(); c.OwnerPlayerId = "q";
                Equal(ItemError.NotOwner, w.Send(new ItemIntent { Kind = ItemIntentKind.SelectSlot, Slot = 255 }, c).Error); Equal(0, w.L.GetPlayer("p").ActiveSlot);
            });
            yield return new Scenario("Intent_InactiveConnectionRefused", () => { var w = new World(); var c = w.Context(); c.HasActivePlayer = false; Equal(ItemError.NotOwner, w.Send(new ItemIntent { Kind = ItemIntentKind.SelectSlot, Slot = 255 }, c).Error); });
            foreach (var test in new[] { (4.0, true, ItemError.None), (4.001, true, ItemError.OutOfReach), (1.0, false, ItemError.NoLineOfSight), (double.NaN, true, ItemError.BadRequest) })
                yield return new Scenario("Intent_PickupReachAndLOS_" + test.Item1 + "_" + test.Item2, () => {
                    var w = new World(); string id = w.Mint(); var c = w.Context(); c.Distance = test.Item1; c.HasLineOfSight = test.Item2;
                    Equal(test.Item3, w.Send(new ItemIntent { Kind = ItemIntentKind.PickUp, ItemId = id }, c).Error);
                    if (test.Item3 == ItemError.None) Equal(id, w.L.HeldItem("p").Id); else Equal(PlaceKind.World, w.L.Get(id).Place);
                });
            foreach (var kind in new[] { ItemIntentKind.Take, ItemIntentKind.Put, ItemIntentKind.SetOpen, ItemIntentKind.CarryBegin, ItemIntentKind.Place })
                yield return new Scenario("Intent_ContainerReach_" + kind, () => {
                    var w = new World(); w.Held(102); string cooler = w.Cooler(); var c = w.Context(); c.Distance = 2.401;
                    Equal(ItemError.OutOfReach, w.Send(new ItemIntent { Kind = kind, ContainerId = cooler, ItemId = cooler, Slot = 0 }, c).Error);
                });
            yield return new Scenario("Intent_TakeStaleSocketDoesNotTakeReplacement", () => {
                var w = new World(); string tray = w.Box(ContainerKind.Tray); w.Mint(dest:Destination.ToContainer(tray));
                Equal(ItemError.NoSuchItem, w.Send(new ItemIntent { Kind = ItemIntentKind.Take, ContainerId = tray, Slot = 0, ItemId = "old-item" }).Error);
            });
            yield return new Scenario("Intent_PutSelectedItemThenTakeByTeammate", () => {
                var w = new World(); string id = w.Held(102), tray = w.Box(ContainerKind.Tray);
                True(w.Send(new ItemIntent { Kind = ItemIntentKind.Put, ContainerId = tray }).Ok); True(w.L.HeldItem("p") == null);
                True(w.Send(new ItemIntent { Kind = ItemIntentKind.Take, ContainerId = tray, Slot = 0, ItemId = id }, w.Context("q")).Ok); Equal(id, w.L.HeldItem("q").Id);
            });
            yield return new Scenario("Intent_DropIsGentleAndPoseIsPlainData", () => {
                var w = new World(); string id = w.Held(102); var result = w.Send(new ItemIntent { Kind = ItemIntentKind.Drop, Slot = 0, Origin = new PlainVector(1, 2, 3) });
                True(result.Ok); Equal(0.0, result.Amount); Equal(5, w.L.Get(id).Organ.Tier); Equal(3.0, w.L.GetPose(id).Position.Z);
            });
            foreach (double charge in new[] { 0.0, 0.3, 0.6 })
                yield return new Scenario("Intent_ThrowChargeSpeed_" + charge, () => {
                    var w = new World(); w.Held(102); var r = w.Send(new ItemIntent { Kind = ItemIntentKind.Throw, Slot = 0, Direction = new PlainVector(0, 0, 1), Charge = charge });
                    True(r.Ok); Near(charge == 0 ? 3 : charge == 0.3 ? 6 : 9, r.Amount);
                });
            foreach (string bad in new[] { "origin", "direction", "zero", "negativeCharge", "infiniteCharge", "farOrigin", "wrongSlot" })
                yield return new Scenario("Intent_RejectMalformedThrow_" + bad, () => {
                    var w = new World(); string id = w.Held(102); var c = w.Context();
                    var r = new ItemIntent { Kind = ItemIntentKind.Throw, Slot = 0, Direction = new PlainVector(0, 0, 1), Charge = .5 };
                    if (bad == "origin") r.Origin.X = double.NaN;
                    if (bad == "direction") r.Direction.Y = double.PositiveInfinity;
                    if (bad == "zero") r.Direction = default;
                    if (bad == "negativeCharge") r.Charge = -1;
                    if (bad == "infiniteCharge") r.Charge = double.PositiveInfinity;
                    if (bad == "farOrigin") c.OriginDistance = 2.401;
                    if (bad == "wrongSlot") r.Slot = 1;
                    True(!w.Send(r, c).Ok); Equal(PlaceKind.Container, w.L.Get(id).Place);
                });
            yield return new Scenario("Intent_PlaceRequiresSurfaceAndNormal", () => {
                var w = new World(); string id = w.Held(102); var c = w.Context(); c.HasSurface = false;
                Equal(ItemError.NoSurface, w.Send(new ItemIntent { Kind = ItemIntentKind.Place, Slot = 0 }, c).Error);
                c.HasSurface = true; Equal(ItemError.BadRequest, w.Send(new ItemIntent { Kind = ItemIntentKind.Place, Slot = 0 }, c).Error);
                True(w.Send(new ItemIntent { Kind = ItemIntentKind.Place, Slot = 0, Normal = new PlainVector(0, 1, 0), Point = new PlainVector(2, 0, 0) }, c).Ok); Equal(2.0, w.L.GetPose(id).Position.X);
            });
            yield return new Scenario("Intent_CarryThenThrowClosesLidAndBlocksTools", () => {
                var w = new World(); w.Held(112); string cooler = w.Cooler(); True(w.Send(new ItemIntent { Kind = ItemIntentKind.CarryBegin, ItemId = cooler }).Ok);
                Equal(ItemError.TwoHandedOnly, w.Send(new ItemIntent { Kind = ItemIntentKind.Use, PressId = 1, TargetId = "npc" }).Error);
                True(w.Send(new ItemIntent { Kind = ItemIntentKind.CarryThrow, Direction = new PlainVector(0, 1, 0), Charge = .6 }).Ok);
                Equal(PlaceKind.World, w.L.Get(cooler).Place); True(!w.L.GetContainer(cooler).Open);
            });
            foreach (TargetKind target in new[] { TargetKind.Buyer, TargetKind.Teammate, TargetKind.None })
                yield return new Scenario("Tool_RejectNonNpc_" + target, () => {
                    var w = new World(); string id = w.Held(112, new FillData { Amount = 1 }); var c = w.Context(); c.Target = target;
                    Equal(ItemError.InvalidTarget, w.Hold(false, 1, c).Error); Equal(1f, w.L.Get(id).Fill.Amount);
                });
            foreach (TargetPart part in new[] { TargetPart.Arms, TargetPart.Legs, TargetPart.Body })
                yield return new Scenario("Tool_TieConsumesExactlyOne_" + part, () => {
                    var w = new World(); string id = w.Held(114, count:2); var result = w.Hold(false, 1, part:part);
                    True(result.Ok); Equal(part == TargetPart.Legs ? "TieFeet" : "TieHands", result.Effect); Equal(1, w.L.Get(id).Count);
                });
            yield return new Scenario("Tool_TieEarlyReleaseConsumesNothing", () => {
                var w = new World(); string id = w.Held(114, count:2); w.Send(new ItemIntent { Kind = ItemIntentKind.Use, Phase = PressPhase.Begin, PressId = 1, TargetId = "npc" });
                w.Now = .25; w.Send(new ItemIntent { Kind = ItemIntentKind.Use, Phase = PressPhase.End, PressId = 1, TargetId = "npc" }); Equal(2, w.L.Get(id).Count);
            });
            yield return new Scenario("Tool_HoldTimeoutAndOldPressCannotResume", () => {
                var w = new World(); string id = w.Held(114); w.Send(new ItemIntent { Kind = ItemIntentKind.Use, PressId = 1, TargetId = "npc" }); w.Now = .501;
                Equal(ItemError.HoldExpired, w.Send(new ItemIntent { Kind = ItemIntentKind.Use, Phase = PressPhase.Hold, PressId = 1, TargetId = "npc" }).Error);
                Equal(ItemError.StaleRequest, w.Send(new ItemIntent { Kind = ItemIntentKind.Use, PressId = 1, TargetId = "npc" }).Error); Equal(1, w.L.Get(id).Count);
            });
            yield return new Scenario("Tool_DuplicateHoldDoesNotInjectTwice", () => {
                var w = new World(); string id = w.Held(112, new FillData { Amount = 1 }); w.Send(new ItemIntent { Kind = ItemIntentKind.Use, PressId = 1, TargetId = "npc" });
                w.Now = .5; var request = new ItemIntent { Kind = ItemIntentKind.Use, Phase = PressPhase.Hold, PressId = 1, TargetId = "npc" };
                var first = w.Send(request); Near(.25, first.Amount); var second = w.Send(request); True(second.Replayed); Near(.75, w.L.Get(id).Fill.Amount);
            });
            yield return new Scenario("Tool_AnesthesiaReleaseKeepsInjectedUnits", () => {
                var w = new World(); string id = w.Held(112, new FillData { Amount = 1 }); True(w.Hold(false, .5).Ok); Near(.75, w.L.Get(id).Fill.Amount);
            });
            yield return new Scenario("Tool_NoHoldAndInjectCombination", () => {
                var w = new World(); string id = w.Held(112, new FillData { Amount = 1 }); var c = w.Context(); c.HoldingBody = true;
                Equal(ItemError.EmptyHandsRequired, w.Hold(false, 1, c).Error); Equal(1f, w.L.Get(id).Fill.Amount);
            });
            foreach (string invalid in new[] { "corpse", "awake", "struggling", "noPortions" })
                yield return new Scenario("Tool_BloodRejects_" + invalid, () => {
                    var w = new World(); string id = w.Held(111); var c = w.Context(); c.Alive = invalid != "corpse"; c.Asleep = invalid != "awake";
                    c.Struggling = invalid == "struggling"; c.CanDrawBlood = invalid != "noPortions";
                    Equal(ItemError.InvalidTarget, w.Hold(false, 4.5, c).Error); Equal(0f, w.L.Get(id).Fill.Amount);
                });
            yield return new Scenario("Tool_BloodDrawDonorAndSequence", () => {
                var w = new World(); string id = w.Held(111); var r = w.Hold(false, 4.5); Equal("DrawBlood", r.Effect);
                Equal(1f, w.L.Get(id).Fill.Amount); Equal("donor", w.L.Get(id).Fill.DonorPatientId); Equal(id + "#1", w.L.BloodSaleIdentity(id));
                True(!w.L.BloodExpired(id, 124.499)); True(w.L.BloodExpired(id, 124.5));
            });
            yield return new Scenario("Tool_RefillUsesStockAndRespectsFormula", () => {
                var w = new World(); string id = w.Held(112, new FillData { Amount = 1, Formula = 1 });
                string vial = w.Mint(113, Destination.ToContainer(ItemLedger.KitId("p")), fill:new FillData { Amount = 5, Formula = 1 });
                True(w.Hold(true, 1).Ok); Equal(3f, w.L.Get(id).Fill.Amount); Equal(3f, w.L.Get(vial).Fill.Amount);
            });
            yield return new Scenario("Tool_RefillRejectsFormulaMixWithoutConsumption", () => {
                var w = new World(); string id = w.Held(112, new FillData { Amount = 1, Formula = 0 });
                string vial = w.Mint(113, Destination.ToContainer(ItemLedger.KitId("p")), fill:new FillData { Amount = 5, Formula = 2 });
                Equal(ItemError.FormulaMismatch, w.Hold(true, 1).Error); Equal(1f, w.L.Get(id).Fill.Amount); Equal(5f, w.L.Get(vial).Fill.Amount);
            });
            yield return new Scenario("Tool_EmptySyringeCanSwitchFormula", () => {
                var w = new World(); string id = w.Held(112); w.Mint(113, Destination.ToContainer(ItemLedger.KitId("p")), fill:new FillData { Amount = 1, Formula = 2 });
                True(w.Hold(true, 1).Ok); Equal(2, w.L.Get(id).Fill.Formula); Equal(1f, w.L.Get(id).Fill.Amount);
            });
            yield return new Scenario("Tool_PackConsumesOnePouch", () => {
                var w = new World(); string id = w.Held(102), pouch = w.Mint(115, Destination.ToContainer(ItemLedger.KitId("p")), count:2);
                True(w.Hold(true, 1).Ok); True(w.L.Get(id).Organ.Packaged); Equal(1, w.L.Get(pouch).Count);
                Equal(ItemError.NotAccepted, w.Hold(true, 1).Error); Equal(1, w.L.Get(pouch).Count);
            });
            yield return new Scenario("Tool_SealedBloodConsumesBagAndKeepsSyringe", () => {
                var w = new World(); string syringe = w.Held(111, new FillData { Amount = 1, FilledAt = 0, FillSeq = 1, DonorPatientId = "donor" });
                string bag = w.Mint(116, Destination.ToContainer(ItemLedger.KitId("p"))); var result = w.Hold(true, 1.2);
                True(result.Ok); True(w.L.IsRetired(bag)); Equal(110, w.L.Get(result.ItemId).DefId); Equal("donor", w.L.Get(result.ItemId).Fill.DonorPatientId); Equal(0f, w.L.Get(syringe).Fill.Amount);
                w.L.Settle(10000); Equal(1f, w.L.Get(result.ItemId).Fill.Amount);
            });
            yield return new Scenario("Tool_BloodTransferNoSpaceIsAtomic", () => {
                var w = new World(); string syringe = w.Held(111, new FillData { Amount = 1, FilledAt = 0, FillSeq = 1 });
                string bags = w.Mint(116, Destination.ToContainer(ItemLedger.PocketsId("p")), count:2);
                for (int i = 0; i < 4; i++) w.Mint(dest:Destination.ToContainer(ItemLedger.PocketsId("p")));
                Equal(ItemError.ContainerFull, w.Hold(true, 1.2).Error); Equal(2, w.L.Get(bags).Count); Equal(1f, w.L.Get(syringe).Fill.Amount);
            });
            yield return new Scenario("Tool_ExpiredBloodCanOnlyBeDiscarded", () => {
                var w = new World(); string id = w.Held(111, new FillData { Amount = 1, FilledAt = 0, FillSeq = 1 }); w.Now = 120;
                Equal("DiscardExpiredBlood", w.Hold(true, 1.2).Effect); Equal(0f, w.L.Get(id).Fill.Amount);
            });
            yield return new Scenario("Tool_CorpseBodyBagRequiresOpenStraps", () => {
                var w = new World(); string id = w.Held(202, count:2); var c = w.Context(); c.Alive = false; c.StrapsOpen = false;
                Equal(ItemError.InvalidTarget, w.Hold(false, 1, c).Error); c.StrapsOpen = true;
                Equal("PackBody", w.Hold(false, 1, c).Effect); Equal(1, w.L.Get(id).Count);
            });
        }
    }
}
