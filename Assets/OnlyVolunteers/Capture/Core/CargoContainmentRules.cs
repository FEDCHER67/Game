using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Capture
{
    /// <summary>
    /// Van cargo containment (ECONOMY §6.2, "Решение Феди 29.10 — удержание пленника"; research
    /// Working/Reviews/VanContainment_2026-10-29/VAN_CARGO_CONTAINMENT_RU.md §3), pure rules:
    /// - Containment I "Фиксаторы кузова" (van_containment_1): floor rails; every NPC loaded in the team van's bay is
    ///   strapped at the waist or ankle, up to the van's capacity (load order: the first ones keep their straps). A strapped
    ///   captive who wakes up cannot leave the bay: no run for an open door, no crawl out, no getting out when thrown about.
    ///   Nothing about him changes (identity, OperationState, ties, sleep, blood, Condition): the strap is derived from
    ///   "loaded in this bay" + the purchase, never saved on him. Hands stay free (he still knocks). Unloading as usual: a
    ///   lying body is grabbed and dragged out (the hold overrides the strap), an awake sitter is knocked out or sedated
    ///   first. A flip or the sea still throws everyone out (a catastrophe, canon §30).
    /// - Containment II "Мягкий отсек" (van_containment_2, needs I): padded walls: no knock on the wall at all (no clip, no
    ///   thud, no knock event), checked where tied hands block the knock. Screams, whimpers, witnesses, police unchanged.
    /// </summary>
    public static class CargoContainmentRules
    {
        /// <summary>The stock cargo bay: 3 lying NPCs (CAPTURE D5, ECONOMY §6.2).</summary>
        public const int StockCapacity = 3;
        /// <summary>Capacity I + II: 5 lying NPCs, the confirmed maximum (D5).</summary>
        public const int MaxCapacity = 5;

        /// <summary>Bay capacity from the two paid capacity steps (3 -> 4 -> 5). II without I (never sold that way) still
        /// counts, clamped to the maximum: the purchase rules keep the order, a load never invents or drops a step.</summary>
        public static int Capacity(bool capacityI, bool capacityII)
        {
            int n = StockCapacity + (capacityI ? 1 : 0) + (capacityII ? 1 : 0);
            return Math.Max(StockCapacity, Math.Min(MaxCapacity, n));
        }

        /// <summary>A loaded captive may try to leave the bay on his own (run / crawl for an open door, get out when thrown)
        /// unless he is strapped (containment I). Ties: hands + feet are CaptureRules.CanLeaveVanAlone's own rule.</summary>
        public static bool CanTryEscape(bool strapped) => !strapped;

        /// <summary>The one knock gate: tied hands (CaptureRules.CanUseHands) or padded walls (containment II) = no knock:
        /// no clip, no thud, no knock event.</summary>
        public static bool CanKnock(bool handsBound, bool paddedWalls) => !handsBound && !paddedWalls;
    }

    /// <summary>
    /// Which loaded NPC holds which strap (containment I), pure and deterministic. Slots 0..Capacity-1 are the van's
    /// D-rings: one NPC per ring. Every update gets the NPCs loaded in this bay right now; the ones that already hold a strap
    /// keep it (by slot), the ones gone (unloaded, dragged out, destroyed) free theirs, newcomers take the lowest free slot
    /// in the order given, while there is one below the capacity. More bodies than the capacity: the extra ones ride
    /// unstrapped (the van is overloaded anyway: its doors do not close). Without the upgrade nobody is strapped.
    /// </summary>
    public sealed class CargoStrapBook<T> where T : class
    {
        private readonly List<T> slots = new List<T>();
        private readonly List<T> scratch = new List<T>();

        public int Capacity { get; private set; } = CargoContainmentRules.StockCapacity;
        public bool Installed { get; private set; }
        /// <summary>Strapped NPCs right now.</summary>
        public int Count
        {
            get
            {
                int n = 0;
                foreach (T s in slots) if (s != null) n++;
                return n;
            }
        }

        /// <summary>The slot (D-ring) of an NPC, -1 = not strapped.</summary>
        public int SlotOf(T who)
        {
            if (who == null) return -1;
            for (int i = 0; i < slots.Count; i++) if (ReferenceEquals(slots[i], who)) return i;
            return -1;
        }

        public bool IsStrapped(T who) => SlotOf(who) >= 0;

        /// <summary>Who holds a slot (null = free).</summary>
        public T At(int slot) => slot >= 0 && slot < slots.Count ? slots[slot] : null;

        /// <summary>One pass: installed = containment I bought; capacity = the bay's; loaded = the NPCs in the bay now (new
        /// ones get slots in this order). Returns the NPCs strapped in this pass (newcomers), for logs.</summary>
        public List<T> Update(bool installed, int capacity, IReadOnlyList<T> loaded)
        {
            scratch.Clear();
            Installed = installed;
            Capacity = Math.Max(0, Math.Min(CargoContainmentRules.MaxCapacity, capacity));
            if (!installed)
            {
                slots.Clear();
                return scratch;
            }
            // a slot above the capacity (never in play: capacity only grows) and anyone no longer loaded: free
            for (int i = 0; i < slots.Count; i++)
                if (slots[i] != null && (i >= Capacity || !Contains(loaded, slots[i]))) slots[i] = null;
            while (slots.Count > Capacity) slots.RemoveAt(slots.Count - 1);
            while (slots.Count < Capacity) slots.Add(null);
            if (loaded == null) return scratch;
            foreach (T who in loaded)
            {
                if (who == null || SlotOf(who) >= 0) continue;
                int free = slots.IndexOf(null);
                if (free < 0) break;
                slots[free] = who;
                scratch.Add(who);
            }
            return scratch;
        }

        public void Clear() => slots.Clear();

        private static bool Contains(IReadOnlyList<T> list, T who)
        {
            if (list == null) return false;
            for (int i = 0; i < list.Count; i++) if (ReferenceEquals(list[i], who)) return true;
            return false;
        }
    }
}
