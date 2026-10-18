using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Items.Core
{
    public enum ItemIntentKind { SelectSlot, Use, Secondary, Take, Put, PickUp, Drop, Throw, Place, SetOpen, CarryBegin, CarryEnd, CarryThrow }
    public enum PressPhase { Begin, Hold, End }
    public enum TargetKind { None, Npc, Buyer, Teammate, Container, Surface }
    public enum TargetPart { Body, Arms, Legs }

    /// <summary>Untrusted intent fields. Never accept authoritative reach/LOS/facts from a client.</summary>
    public sealed class ItemIntent
    {
        public long RequestId, PressId;
        public ItemIntentKind Kind;
        public PressPhase Phase;
        public int Slot = -1;
        public string ItemId = "", ContainerId = "", TargetId = "";
        public TargetPart Part;
        public bool Open;
        public PlainVector Origin, Direction, Point, Normal;
        public double Charge;
        public ItemIntent Copy() => (ItemIntent)MemberwiseClone();
    }
    /// <summary>Host-resolved inputs, measured from server player/seat. No physics or transport in this library.</summary>
    public sealed class IntentContext
    {
        public string SenderPlayerId = "", OwnerPlayerId = "";
        public bool HasActivePlayer;
        public bool Driving, Phone, TableCamera, BuyerCamera, HoldingBody;
        public bool HasLineOfSight;
        public double Distance, OriginDistance;
        public bool HasSurface;
        public TargetKind Target;
        public bool Alive, Asleep, KnockedOut, Restrained, Struggling, StrapsOpen, HasTie, Downed;
        public bool HandsTied, FeetTied;
        public bool CanDrawBlood;
        public string DonorPatientId = "";
        public string ResolvedItemId = "", ResolvedContainerId = "", ResolvedTargetId = "";
        // Physical carrying of a bagged NPC remains outside the item ledger.
        public bool CarryingBody;
        public IntentContext Copy() => (IntentContext)MemberwiseClone();
    }
    internal sealed class ItemHold
    {
        public long Press;
        public string ItemId = "", Target = "";
        public TargetPart Part;
        public bool Secondary;
        public double Started, Last;
    }
    /// <summary>One instance per host ledger. Call synchronously on the host; replays never emit a second effect.</summary>
    public sealed class ItemIntentServer
    {
        private readonly ItemLedger ledger;
        private readonly Dictionary<string, ItemHold> holds = new Dictionary<string, ItemHold>(StringComparer.Ordinal);
        public ItemIntentServer(ItemLedger ledger) { this.ledger = ledger ?? throw new ArgumentNullException(nameof(ledger)); }
        public MoveResult Execute(ItemIntent request, IntentContext context, double now)
        {
            if (request == null || context == null) return MoveResult.Fail(ItemError.BadRequest);
            request = request.Copy(); context = context.Copy();
            // The connection-to-player map must be resolved by the transport adapter, never by payload.
            if (!context.HasActivePlayer || string.IsNullOrWhiteSpace(context.SenderPlayerId) || context.SenderPlayerId != context.OwnerPlayerId)
                return MoveResult.Fail(ItemError.NotOwner);
            lock (ledger.Gate)
                return ledger.Request(context.SenderPlayerId, request.RequestId, now, () => Dispatch(request, context, now));
        }
        public void PlayerLeft(string playerId, double now)
        { lock (ledger.Gate) { holds.Remove(playerId); ledger.LeavePlayer(playerId, now); } }
        private MoveResult Dispatch(ItemIntent r, IntentContext c, double now)
        {
            string actor = c.SenderPlayerId;
            if (!Enum.IsDefined(typeof(ItemIntentKind), r.Kind)) return MoveResult.Fail(ItemError.BadRequest);
            if ((r.Kind == ItemIntentKind.PickUp || r.Kind == ItemIntentKind.CarryBegin) && r.ItemId != c.ResolvedItemId ||
                (r.Kind == ItemIntentKind.Take || r.Kind == ItemIntentKind.Put || r.Kind == ItemIntentKind.SetOpen) && r.ContainerId != c.ResolvedContainerId ||
                r.Kind == ItemIntentKind.Use && r.TargetId != c.ResolvedTargetId) return MoveResult.Fail(ItemError.InvalidTarget);
            if (c.Driving || c.Phone || c.TableCamera || c.BuyerCamera)
            { holds.Remove(actor); return MoveResult.Fail(ItemError.Busy); }
            var carry = ledger.CarriedItem(actor);
            bool carryExit = r.Kind == ItemIntentKind.CarryEnd || r.Kind == ItemIntentKind.CarryThrow;
            if ((carry != null || c.CarryingBody) && !carryExit) return MoveResult.Fail(ItemError.TwoHandedOnly);
            if (c.HoldingBody) { holds.Remove(actor); return MoveResult.Fail(ItemError.EmptyHandsRequired); }
            if (r.Kind != ItemIntentKind.Use && r.Kind != ItemIntentKind.Secondary) holds.Remove(actor);
            var held = ledger.HeldItem(actor);
            ItemError Near(double distance) => !ItemCatalog.Finite(c.Distance) || c.Distance < 0 ? ItemError.BadRequest :
                c.Distance > distance ? ItemError.OutOfReach : !c.HasLineOfSight ? ItemError.NoLineOfSight : ItemError.None;
            MoveResult Fail(ItemError error) => MoveResult.Fail(error);
            switch (r.Kind)
            {
                case ItemIntentKind.SelectSlot: return ledger.SelectCore(actor, r.Slot);
                case ItemIntentKind.Use: case ItemIntentKind.Secondary: return Hold(r, c, held, now);
                case ItemIntentKind.Take:
                {
                    var e = Near(2.4); if (e != ItemError.None) return Fail(e);
                    var container = ledger.GetContainer(r.ContainerId); if (container == null) return Fail(ItemError.NoSuchContainer);
                    if (r.Slot < 0 || r.Slot >= container.Capacity) return Fail(ItemError.BadRequest);
                    var item = ledger.Get(container.Slots[r.Slot]);
                    if (item == null || r.ItemId != "" && item.Id != r.ItemId) return Fail(ItemError.NoSuchItem);
                    return Take(actor, item, now);
                }
                case ItemIntentKind.PickUp:
                {
                    var e = Near(4.0); if (e != ItemError.None) return Fail(e);
                    var item = ledger.Get(r.ItemId); if (item == null || item.Place != PlaceKind.World) return Fail(ItemError.NoSuchItem);
                    return Take(actor, item, now);
                }
                case ItemIntentKind.Put:
                {
                    if (held == null) return Fail(ItemError.NoActiveItem);
                    var e = Near(2.4); if (e != ItemError.None) return Fail(e);
                    return ledger.MoveCore(actor, held.Id, Destination.ToContainer(r.ContainerId, r.Slot), now);
                }
                case ItemIntentKind.SetOpen:
                {
                    var e = Near(2.4); if (e != ItemError.None) return Fail(e);
                    var box = ledger.GetContainer(r.ContainerId); if (box == null) return Fail(ItemError.NoSuchContainer);
                    if ((box.Kind == ContainerKind.Pockets || box.Kind == ContainerKind.Kit) && box.OwnerId != actor) return Fail(ItemError.NotOwner);
                    return new MoveResult { Error = ledger.SetOpen(r.ContainerId, r.Open), Effect = "SetOpen" };
                }
                case ItemIntentKind.CarryBegin:
                {
                    var e = Near(2.4); if (e != ItemError.None) return Fail(e);
                    var item = ledger.Get(r.ItemId); if (item == null) return Fail(ItemError.NoSuchItem);
                    if (item.Place != PlaceKind.World && item.Place != PlaceKind.Container) return Fail(ItemError.NotOwner);
                    return ledger.MoveCore(actor, r.ItemId, Destination.ToCarry(actor), now);
                }
                case ItemIntentKind.Drop: case ItemIntentKind.Throw: case ItemIntentKind.Place:
                case ItemIntentKind.CarryEnd: case ItemIntentKind.CarryThrow:
                {
                    var item = carryExit ? carry : held;
                    if (item == null) return Fail(ItemError.NoActiveItem);
                    if (!carryExit && r.Slot != ledger.GetPlayer(actor).ActiveSlot) return Fail(ItemError.NotOwner);
                    if (!r.Origin.IsFinite || !ItemCatalog.Finite(c.OriginDistance) || c.OriginDistance < 0 || c.OriginDistance > 2.4) return Fail(ItemError.BadRequest);
                    bool throwing = r.Kind == ItemIntentKind.Throw || r.Kind == ItemIntentKind.CarryThrow;
                    if (throwing && (!r.Direction.IsFinite || !ItemCatalog.Finite(r.Direction.LengthSquared) || r.Direction.LengthSquared < 1e-12 ||
                        !ItemCatalog.Finite(r.Charge) || r.Charge < 0 || r.Charge > 0.6)) return Fail(ItemError.BadRequest);
                    if (r.Kind == ItemIntentKind.Place)
                    {
                        var e = Near(2.4); if (e != ItemError.None) return Fail(e);
                        if (!c.HasSurface) return Fail(ItemError.NoSurface);
                        if (!r.Point.IsFinite || !r.Normal.IsFinite || !ItemCatalog.Finite(r.Normal.LengthSquared) || r.Normal.LengthSquared < 1e-12) return Fail(ItemError.BadRequest);
                    }
                    var result = ledger.MoveCore(actor, item.Id, Destination.ToWorld(), now);
                    if (result.Ok)
                    {
                        ledger.SetPose(new ItemPose { Id = item.Id, Position = r.Kind == ItemIntentKind.Place ? r.Point : r.Origin });
                        result.Effect = throwing ? "Throw" : "Place"; result.Amount = throwing ? 3 + 6 * r.Charge / 0.6 : 0;
                    }
                    return result;
                }
                default: return Fail(ItemError.BadRequest);
            }
        }
        private MoveResult Take(string actor, ItemRecord item, double now)
        {
            var result = ledger.MoveCore(actor, item.Id, ledger.PocketDestination(actor, item), now);
            if (result.Ok) ledger.SelectItem(actor, result.ItemId);
            return result;
        }
        private MoveResult Hold(ItemIntent r, IntentContext c, ItemRecord held, double now)
        {
            string actor = c.SenderPlayerId; bool secondary = r.Kind == ItemIntentKind.Secondary;
            MoveResult Refuse(ItemError error) { holds.Remove(actor); return MoveResult.Fail(error); }
            if (!Enum.IsDefined(typeof(PressPhase), r.Phase) || !Enum.IsDefined(typeof(TargetPart), r.Part) || r.PressId <= 0) return Refuse(ItemError.BadRequest);
            if (held == null) return Refuse(ItemError.NoActiveItem);
            var item = ledger.Find(held.Id); var d = ledger.Definition(item);
            if (!secondary)
            {
                if (c.Target != TargetKind.Npc || string.IsNullOrWhiteSpace(r.TargetId)) return Refuse(ItemError.InvalidTarget);
                if (!ItemCatalog.Finite(c.Distance) || c.Distance < 0) return Refuse(ItemError.BadRequest);
                if (c.Distance > 2.6) return Refuse(ItemError.OutOfReach);
                if (!c.HasLineOfSight) return Refuse(ItemError.NoLineOfSight);
                var error = PrimaryAllowed(d.Class, c, item); if (error != ItemError.None) return Refuse(error);
                if (d.Class == ItemClass.ZipTies && (r.Part == TargetPart.Legs ? c.FeetTied : c.HandsTied)) return Refuse(ItemError.InvalidTarget);
            }
            else if (d.Class != ItemClass.Organ && d.Class != ItemClass.BloodSyringe && d.Class != ItemClass.AnesthesiaSyringe) return Refuse(ItemError.InvalidTarget);
            if (r.Phase == PressPhase.Begin)
            {
                if (r.PressId <= ledger.LastPress(actor)) return Refuse(ItemError.StaleRequest);
                ledger.MarkPress(actor, r.PressId);
                holds[actor] = new ItemHold { Press = r.PressId, ItemId = item.Id, Target = r.TargetId, Part = r.Part, Secondary = secondary, Started = now, Last = now };
                return ItemLedger.Success(item);
            }
            if (!holds.TryGetValue(actor, out var hold) || hold.Press != r.PressId || hold.ItemId != item.Id || hold.Target != r.TargetId || hold.Part != r.Part || hold.Secondary != secondary)
                return Refuse(ItemError.WrongPhase);
            if (now - hold.Last > ledger.Tuning.HoldTimeoutSeconds) return Refuse(ItemError.HoldExpired);
            if (r.Phase == PressPhase.End) { holds.Remove(actor); return ItemLedger.Success(item); }
            double step = now - hold.Last; hold.Last = now;
            if (!secondary && d.Class == ItemClass.AnesthesiaSyringe)
                return new MoveResult { ItemId = item.Id, TargetId = r.TargetId, Effect = "Inject", Amount = ledger.Inject(item, step) };
            var t = ledger.Tuning;
            double required = secondary ? d.Class == ItemClass.BloodSyringe ? t.TransferHoldSeconds : d.Class == ItemClass.AnesthesiaSyringe ? t.RefillHoldSeconds : t.PackHoldSeconds :
                d.Class == ItemClass.BloodSyringe ? t.BloodHoldSeconds : t.TieHoldSeconds;
            if (now - hold.Started + 1e-12 < required) return ItemLedger.Success(item);
            holds.Remove(actor);
            if (secondary)
            {
                if (d.Class == ItemClass.BloodSyringe) return ledger.SealBlood(actor, item, now);
                var error = d.Class == ItemClass.Organ ? ledger.Package(actor, item) : ledger.Refill(actor, item);
                return new MoveResult { Error = error, ItemId = item.Id, Effect = error == ItemError.None ? d.Class == ItemClass.Organ ? "Package" : "Refill" : "" };
            }
            string effect;
            if (d.Class == ItemClass.BloodSyringe) { ledger.SetFill(item, 1, c.DonorPatientId, now); effect = "DrawBlood"; }
            else if (d.Class == ItemClass.Tool) effect = "CutTie";
            else { ledger.Consume(item.Id, 1); effect = d.Class == ItemClass.BodyBag ? "PackBody" : r.Part == TargetPart.Legs ? "TieFeet" : "TieHands"; }
            return new MoveResult { ItemId = item.Id, TargetId = r.TargetId, Effect = effect, Amount = 1 };
        }
        private static ItemError PrimaryAllowed(ItemClass cls, IntentContext c, ItemRecord item)
        {
            switch (cls)
            {
                case ItemClass.ZipTies: return c.Alive && (c.Downed || c.Asleep || c.KnockedOut) ? ItemError.None : ItemError.InvalidTarget;
                case ItemClass.AnesthesiaSyringe: return !c.Alive ? ItemError.InvalidTarget : item.Fill.Amount <= 0 ? ItemError.StockEmpty : ItemError.None;
                case ItemClass.BloodSyringe:
                    return !c.Alive || c.Struggling || !(c.Asleep || c.KnockedOut || c.Restrained) || !c.CanDrawBlood || string.IsNullOrWhiteSpace(c.DonorPatientId) ?
                        ItemError.InvalidTarget : item.Fill.Amount != 0 ? ItemError.NotEnough : ItemError.None;
                case ItemClass.BodyBag: return !c.Alive && c.StrapsOpen ? ItemError.None : ItemError.InvalidTarget;
                case ItemClass.Tool: return c.HasTie ? ItemError.None : ItemError.InvalidTarget;
                default: return ItemError.InvalidTarget;
            }
        }
    }
}
