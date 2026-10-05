using System;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Hotbar inventory rules without Unity or networking. On the server NetworkInventory owns one
    /// instance and mirrors it to clients; tests drive it directly.
    /// Size is summed over all carried items and limited by Capacity.
    /// </summary>
    public sealed class InventoryModel
    {
        private readonly ItemStack[] slots;
        private readonly IItemCatalog catalog;

        public InventoryModel(int slotCount, int capacity, IItemCatalog catalog)
        {
            if (slotCount <= 0) throw new ArgumentOutOfRangeException(nameof(slotCount));
            if (capacity <= 0) throw new ArgumentOutOfRangeException(nameof(capacity));
            this.catalog = catalog ?? throw new ArgumentNullException(nameof(catalog));
            slots = new ItemStack[slotCount];
            Capacity = capacity;
        }

        /// <summary>Slot index whose contents changed.</summary>
        public event Action<int> SlotChanged;
        public event Action<int> SelectionChanged;
        public event Action<int> CashChanged;

        public int SlotCount => slots.Length;
        public int Capacity { get; }
        public int UsedCapacity { get; private set; }
        public int FreeCapacity => Capacity - UsedCapacity;
        public int SelectedIndex { get; private set; }
        public int Cash { get; private set; }
        public ItemStack Selected => slots[SelectedIndex];

        public ItemStack GetSlot(int index) => slots[index];

        /// <summary>How many of these items would fit right now (0 for unknown items).</summary>
        public int CountThatFits(int itemId, int count, int unitValue)
        {
            if (count <= 0 || !catalog.TryGet(itemId, out ItemInfo info) || info.Size <= 0 || info.MaxStack <= 0)
                return 0;
            int bySize = FreeCapacity / info.Size;
            int bySlots = 0;
            for (int i = 0; i < slots.Length && bySlots < count; i++)
            {
                ItemStack slot = slots[i];
                if (slot.IsEmpty) bySlots += info.MaxStack;
                else if (CanMerge(slot, itemId, unitValue)) bySlots += Math.Max(0, info.MaxStack - slot.Count);
            }
            return Math.Min(count, Math.Min(bySize, bySlots));
        }

        /// <summary>
        /// Adds as many items as fit: first into matching stacks, then into the selected slot if
        /// it is empty, then into the first empty slots. Returns the number added.
        /// </summary>
        public int TryAdd(int itemId, int count, int unitValue)
        {
            int toAdd = CountThatFits(itemId, count, unitValue);
            if (toAdd <= 0) return 0;
            catalog.TryGet(itemId, out ItemInfo info);
            int remaining = toAdd;
            for (int i = 0; i < slots.Length && remaining > 0; i++)
                if (!slots[i].IsEmpty && CanMerge(slots[i], itemId, unitValue))
                    remaining -= Fill(i, itemId, remaining, unitValue, info.MaxStack);
            if (remaining > 0 && slots[SelectedIndex].IsEmpty)
                remaining -= Fill(SelectedIndex, itemId, remaining, unitValue, info.MaxStack);
            for (int i = 0; i < slots.Length && remaining > 0; i++)
                if (slots[i].IsEmpty)
                    remaining -= Fill(i, itemId, remaining, unitValue, info.MaxStack);
            return toAdd - remaining;
        }

        /// <summary>Removes up to count items from a slot. Returns what was taken (empty on failure).</summary>
        public ItemStack TakeFromSlot(int index, int count)
        {
            if (index < 0 || index >= slots.Length || count <= 0 || slots[index].IsEmpty)
                return ItemStack.Empty;
            ItemStack slot = slots[index];
            int taken = Math.Min(count, slot.Count);
            slot.Count -= taken;
            Set(index, slot.Count > 0 ? slot : ItemStack.Empty);
            return new ItemStack(slot.ItemId, taken, slot.UnitValue);
        }

        public bool Select(int index)
        {
            if (index < 0 || index >= slots.Length) return false;
            if (index == SelectedIndex) return true;
            SelectedIndex = index;
            SelectionChanged?.Invoke(index);
            return true;
        }

        /// <summary>Cycles the selection by direction (wraps around), e.g. for the mouse wheel.</summary>
        public void SelectNext(int direction)
        {
            if (direction == 0) return;
            int step = direction > 0 ? 1 : -1;
            Select(((SelectedIndex + step) % slots.Length + slots.Length) % slots.Length);
        }

        /// <summary>
        /// Slot holding the single most expensive item (highest UnitValue), or -1 when empty.
        /// Ties go to the lowest slot index.
        /// </summary>
        public int MostValuableSlot()
        {
            int best = -1;
            for (int i = 0; i < slots.Length; i++)
                if (!slots[i].IsEmpty && (best < 0 || slots[i].UnitValue > slots[best].UnitValue))
                    best = i;
            return best;
        }

        /// <summary>One unit of the most expensive item (not removed), or empty.</summary>
        public ItemStack MostValuableItem()
        {
            int index = MostValuableSlot();
            return index < 0 ? ItemStack.Empty : new ItemStack(slots[index].ItemId, 1, slots[index].UnitValue);
        }

        /// <summary>Removes and returns one unit of the most expensive item (police confiscation).</summary>
        public ItemStack ConfiscateMostValuable()
        {
            int index = MostValuableSlot();
            return index < 0 ? ItemStack.Empty : TakeFromSlot(index, 1);
        }

        public void AddCash(int amount)
        {
            if (amount <= 0) return;
            SetCash((int)Math.Min(int.MaxValue, (long)Cash + amount));
        }

        public bool TrySpendCash(int amount)
        {
            if (amount < 0 || amount > Cash) return false;
            if (amount > 0) SetCash(Cash - amount);
            return true;
        }

        /// <summary>Removes percent of the cash, rounded down. Returns the amount taken.</summary>
        public int TakeCashPercent(int percent)
        {
            percent = Math.Max(0, Math.Min(100, percent));
            int taken = (int)((long)Cash * percent / 100);
            if (taken > 0) SetCash(Cash - taken);
            return taken;
        }

        /// <summary>
        /// Canon section 80, "if not rescued": minus 10% cash and the most expensive item.
        /// </summary>
        public ArrestResult ApplyArrestPenalty(int cashPercent = 10)
        {
            int cash = TakeCashPercent(cashPercent);
            return new ArrestResult(cash, ConfiscateMostValuable());
        }

        public void Clear()
        {
            for (int i = 0; i < slots.Length; i++)
                if (!slots[i].IsEmpty) Set(i, ItemStack.Empty);
        }

        private static bool CanMerge(ItemStack slot, int itemId, int unitValue) =>
            slot.ItemId == itemId && slot.UnitValue == unitValue;

        private int Fill(int index, int itemId, int count, int unitValue, int maxStack)
        {
            ItemStack slot = slots[index];
            int current = slot.IsEmpty ? 0 : slot.Count;
            int added = Math.Min(count, maxStack - current);
            if (added <= 0) return 0;
            Set(index, new ItemStack(itemId, current + added, unitValue));
            return added;
        }

        private void Set(int index, ItemStack value)
        {
            UsedCapacity += SizeOf(value) - SizeOf(slots[index]);
            slots[index] = value;
            SlotChanged?.Invoke(index);
        }

        private int SizeOf(ItemStack stack) =>
            !stack.IsEmpty && catalog.TryGet(stack.ItemId, out ItemInfo info) ? info.Size * stack.Count : 0;

        private void SetCash(int value)
        {
            Cash = value;
            CashChanged?.Invoke(value);
        }
    }

    public readonly struct ArrestResult
    {
        public readonly int CashTaken;
        public readonly ItemStack Confiscated;

        public ArrestResult(int cashTaken, ItemStack confiscated)
        {
            CashTaken = cashTaken;
            Confiscated = confiscated;
        }
    }
}
