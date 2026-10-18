using System;
using System.Linq;

namespace OnlyVolunteers.Items.Core
{
    public sealed partial class ItemLedger
    {
        internal ItemRecord Supply(string actor, ItemClass cls) => items.Values.Where(r => r.Place == PlaceKind.Container &&
            (r.ContainerId == PocketsId(actor) || r.ContainerId == KitId(actor)) && Definition(r).Class == cls)
            .OrderBy(r => r.Id, StringComparer.Ordinal).FirstOrDefault();
        public bool BloodExpired(string id, double now)
        {
            lock (Gate)
            {
                Time(now); var r = Find(id);
                if (r == null || Definition(r).Class != ItemClass.BloodSyringe || r.Fill.Amount <= 0 || r.Fill.FilledAt < 0) return false;
                double at = Detached(r) ? players[Owner(r)].DetachedAt : now;
                return r.Fill.AgeAtAnchor + at - r.Fill.FilledAt >= tuning.BloodExpirySeconds;
            }
        }
        public string BloodSaleIdentity(string id)
        { lock (Gate) { var r = Find(id); return r != null && Definition(r).Class == ItemClass.BloodSyringe && r.Fill.Amount == 1 ? r.Id + "#" + r.Fill.FillSeq : ""; } }
        /// <summary>Commit a confirmed blood-portion sale without selling the reusable syringe.</summary>
        public ItemError RetireBloodPortion(string id, int expectedFillSequence, double now)
        {
            lock (Gate)
            {
                Time(now);
                if (string.IsNullOrWhiteSpace(id) || expectedFillSequence <= 0) return ItemError.BadRequest;
                string identity = id + "#" + expectedFillSequence;
                if (retired.Contains(identity)) return ItemError.None;
                var r = Find(id); if (r == null) return ItemError.NoSuchItem;
                if (Detached(r)) return ItemError.PlayerAbsent;
                if (Definition(r).Class != ItemClass.BloodSyringe || r.Fill.Amount != 1 || r.Fill.FillSeq != expectedFillSequence) return ItemError.BadRequest;
                if (BloodExpired(id, now)) return ItemError.BloodExpired;
                ClearBlood(r); return ItemError.None;
            }
        }
        private void ClearBlood(ItemRecord r)
        {
            if (r.Fill.Amount == 1 && r.Fill.FillSeq > 0) retired.Add(r.Id + "#" + r.Fill.FillSeq);
            r.Fill.Amount = 0; r.Fill.DonorPatientId = ""; r.Fill.FilledAt = -1; r.Fill.AgeAtAnchor = 0; Touch(r);
        }
        internal ItemError Package(string actor, ItemRecord organ)
        {
            if (!organ.HasOrgan || organ.Organ.Packaged) return ItemError.NotAccepted;
            var pouch = Supply(actor, ItemClass.OrganPouch); if (pouch == null) return ItemError.MissingSupply;
            Consume(pouch.Id, 1); organ.Organ.Packaged = true; Touch(organ); return ItemError.None;
        }
        internal ItemError Refill(string actor, ItemRecord syringe)
        {
            var vials = items.Values.Where(r => r.Place == PlaceKind.Container &&
                (r.ContainerId == PocketsId(actor) || r.ContainerId == KitId(actor)) && Definition(r).Class == ItemClass.AnestheticVial && r.Fill.Amount > 0)
                .OrderBy(r => r.Id, StringComparer.Ordinal).ToArray();
            if (vials.Length == 0) return ItemError.MissingSupply;
            var vial = vials.FirstOrDefault(r => syringe.Fill.Amount == 0 || r.Fill.Formula == syringe.Fill.Formula);
            if (vial == null) return ItemError.FormulaMismatch;
            float amount = Math.Min(tuning.SyringeCapacity - syringe.Fill.Amount, vial.Fill.Amount);
            if (amount <= 0) return ItemError.NotEnough;
            syringe.Fill.Formula = vial.Fill.Formula; syringe.Fill.Amount += amount; vial.Fill.Amount -= amount;
            Touch(syringe); Touch(vial); return ItemError.None;
        }
        internal MoveResult SealBlood(string actor, ItemRecord syringe, double now)
        {
            if (BloodExpired(syringe.Id, now))
            { ClearBlood(syringe); return new MoveResult { ItemId = syringe.Id, Effect = "DiscardExpiredBlood" }; }
            if (syringe.Fill.Amount != 1) return MoveResult.Fail(ItemError.NotEnough);
            var bags = Supply(actor, ItemClass.EmptyBloodBag); if (bags == null) return MoveResult.Fail(ItemError.MissingSupply);
            var d = new ItemRecord { DefId = 110, HasFill = true, Fill = new FillData { Amount = 1, DonorPatientId = syringe.Fill.DonorPatientId } };
            defs.TryGet(110, out var bagDef);
            // A single consumed bag frees its own entry. A remaining stack needs another entry.
            var dest = Destination.ToContainer(bags.ContainerId, bags.Count == 1 ? bags.Slot : -1);
            if (bags.Count > 1)
            {
                var e = CanPlace(d, bagDef, dest, 1, out _, out _);
                if (e != ItemError.None)
                {
                    dest = Destination.ToContainer(PocketsId(actor)); e = CanPlace(d, bagDef, dest, 1, out _, out _);
                    if (e != ItemError.None) return MoveResult.Fail(e);
                }
            }
            // Reserve identity before consuming any supply (including overflow checks).
            d.Id = NewId(); Consume(bags.Id, 1);
            var result = Insert(d, bagDef, dest, now);
            if (!result.Ok) throw new InvalidOperationException("Validated blood transfer could not commit");
            ClearBlood(syringe);
            result.Effect = "SealBlood"; return result;
        }
        internal Destination PocketDestination(string actor, ItemRecord r)
        {
            var p = players[actor];
            if (p.ActiveSlot < 6 && !(p.ActiveSlot == p.KitSlot && HasKit(actor)) &&
                string.IsNullOrEmpty(Container(PocketsId(actor)).Slots[p.ActiveSlot])) return Destination.ToContainer(PocketsId(actor), p.ActiveSlot);
            return Destination.ToContainer(PocketsId(actor));
        }
        internal void SetFill(ItemRecord r, float amount, string donor, double now)
        {
            r.Fill.FillSeq = checked(r.Fill.FillSeq + 1);
            r.Fill.Amount = amount; r.Fill.DonorPatientId = donor ?? ""; r.Fill.FilledAt = now; r.Fill.AgeAtAnchor = 0; Touch(r);
        }
        internal float Inject(ItemRecord r, double duration)
        { float amount = Math.Min(r.Fill.Amount, (float)(duration * tuning.InjectionUnitsPerSecond)); r.Fill.Amount -= amount; Touch(r); return amount; }
        internal long LastPress(string actor) => players[actor].LastPressId;
        internal void MarkPress(string actor, long press) { players[actor].LastPressId = press; }
    }
}
