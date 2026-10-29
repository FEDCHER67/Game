using System;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Inventory
{
    public enum SyringeKind { None, Blood, Anaesthesia }
    public enum SyringeUseResult { Success, InvalidTarget, WrongType, OtherPerson, LegacyUnknown, Failed }

    [Serializable]
    public sealed class BloodPortion
    {
        public string Id = "";
        public string PersonId = "";
        public bool Sealed;
        public float FreshSeconds;
        public BloodPortion Copy() => (BloodPortion)MemberwiseClone();
        public bool Saleable => !string.IsNullOrWhiteSpace(Id) && !string.IsNullOrWhiteSpace(PersonId) &&
            (Sealed || FreshSeconds > 0 && !float.IsInfinity(FreshSeconds));
    }

    /// <summary>Persistent physical instance, distinct from the numeric ItemDefinition id. Move this record with the item.</summary>
    [Serializable]
    public sealed class SyringeInstance
    {
        public string ItemId = "";
        public SyringeKind Kind;
        public string PersonId = "";
        public bool LegacyUnknown;
        public bool Discarded;
        public float Fill;
        public string PendingPersonId = "";
        public BloodPortion Portion;
        public static SyringeInstance New(SyringeKind kind, string id = null)
        {
            if (kind != SyringeKind.Blood && kind != SyringeKind.Anaesthesia) throw new ArgumentOutOfRangeException(nameof(kind));
            return new SyringeInstance { ItemId = id ?? Guid.NewGuid().ToString("N"), Kind = kind };
        }
        public SyringeInstance Copy()
        {
            var copy = (SyringeInstance)MemberwiseClone();
            copy.Portion = Portion?.Copy();
            return copy;
        }
    }

    public static class SyringeRules
    {
        public const string OtherPersonNotice = "Этот шприц уже использован на другом человеке";
        // IDs reserved here are separate from the kit (301) and disposal supplies (302).
        public const int BloodDefinitionId = 303, AnaesthesiaDefinitionId = 304;
        public static string PriceId(SyringeKind kind) => kind == SyringeKind.Blood ? "syringe_blood" :
            kind == SyringeKind.Anaesthesia ? "syringe_anaesthesia" : throw new ArgumentOutOfRangeException(nameof(kind));
        public static int Price(SyringeKind kind) => BuyerCatalog.SyringePrice(PriceId(kind));
        public static SyringeUseResult Check(SyringeInstance item, SyringeKind expected, string personId, bool alive, bool valid)
        {
            if (item == null || item.Discarded || string.IsNullOrWhiteSpace(item.ItemId) || item.Kind != expected || expected == SyringeKind.None)
                return SyringeUseResult.WrongType;
            if (item.LegacyUnknown) return SyringeUseResult.LegacyUnknown;
            if (!string.IsNullOrEmpty(item.PersonId) && item.PersonId != personId) return SyringeUseResult.OtherPerson;
            return alive && valid && !string.IsNullOrWhiteSpace(personId) ? SyringeUseResult.Success : SyringeUseResult.InvalidTarget;
        }
        /// <summary>Call only for a committed use. Hover/cancel never calls apply; a failed apply binds nothing.</summary>
        public static SyringeUseResult TryUse(SyringeInstance item, SyringeKind expected, string personId,
            bool alive, bool valid, Func<bool> apply)
        {
            var check = Check(item, expected, personId, alive, valid);
            if (check != SyringeUseResult.Success) return check;
            if (apply == null || !apply()) return SyringeUseResult.Failed;
            item.PersonId = personId;
            return SyringeUseResult.Success;
        }
        public static BloodPortion Pack(SyringeInstance item)
        {
            if (item == null || item.Discarded || item.Portion == null || !item.Portion.Saleable) return null;
            var portion = item.Portion;
            portion.Sealed = true;
            item.Portion = null; item.Fill = 0; item.PendingPersonId = ""; // permanent binding stays
            return portion;
        }
        public static void Empty(SyringeInstance item) { if (item != null) { item.Portion = null; item.Fill = 0; item.PendingPersonId = ""; } }
        public static void CancelDraw(SyringeInstance item)
        {
            if (item == null || item.Portion != null) return;
            item.PendingPersonId = ""; item.Fill = 0;
        }
        public static void TickFreshness(SyringeInstance item, float activeSeconds)
        {
            if (item?.Portion == null || item.Portion.Sealed || activeSeconds <= 0 || float.IsNaN(activeSeconds) || float.IsInfinity(activeSeconds)) return;
            item.Portion.FreshSeconds = Math.Max(0, item.Portion.FreshSeconds - activeSeconds);
        }
    }
}
