using System;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Contents of one hotbar slot. ItemId 0 means empty. UnitValue is per item, so two hearts
    /// of different condition never merge into one stack.
    /// Public mutable fields keep the struct serializable by FishNet.
    /// </summary>
    [Serializable]
    public struct ItemStack : IEquatable<ItemStack>
    {
        public int ItemId;
        public int Count;
        public int UnitValue;

        public ItemStack(int itemId, int count, int unitValue)
        {
            ItemId = itemId;
            Count = count;
            UnitValue = unitValue;
        }

        public static ItemStack Empty => default;
        public bool IsEmpty => ItemId == 0 || Count <= 0;
        public long TotalValue => (long)UnitValue * Count;

        public bool Equals(ItemStack other) =>
            ItemId == other.ItemId && Count == other.Count && UnitValue == other.UnitValue;
        public override bool Equals(object obj) => obj is ItemStack other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(ItemId, Count, UnitValue);
        public override string ToString() => IsEmpty ? "(empty)" : $"{ItemId} x{Count} @{UnitValue}";
    }

    /// <summary>Static per-type data the core needs; the Unity side builds it from ItemDefinition.</summary>
    public readonly struct ItemInfo
    {
        public readonly int Id;
        public readonly int Size;
        public readonly int MaxStack;

        public ItemInfo(int id, int size, int maxStack)
        {
            Id = id;
            Size = size;
            MaxStack = maxStack;
        }
    }

    public interface IItemCatalog
    {
        bool TryGet(int itemId, out ItemInfo info);
    }
}
