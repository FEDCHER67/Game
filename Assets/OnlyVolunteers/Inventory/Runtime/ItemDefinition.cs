using FishNet.Object;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    public enum ItemKind
    {
        Other = 0,
        Organ = 1,
        Tool = 2,
    }

    /// <summary>
    /// One carriable item type (an organ, a tool...). The numeric Id is what goes over the network
    /// and into saves, so never reuse or renumber it.
    /// </summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Inventory/Item Definition", fileName = "Item_")]
    public sealed class ItemDefinition : ScriptableObject
    {
        [SerializeField, Min(1)] private int id = 1;
        [SerializeField] private string displayName = "Item";
        [Tooltip("Two or three letters shown in the hotbar when there is no icon.")]
        [SerializeField] private string shortLabel = "?";
        [SerializeField] private ItemKind kind;
        [SerializeField] private Sprite icon;
        [Tooltip("Capacity units this item uses. Larger than the inventory capacity means it can only be carried by hand.")]
        [SerializeField, Min(1)] private int size = 1;
        [SerializeField, Min(1)] private int maxStack = 1;
        [Tooltip("Value per item when nothing else (organ condition, a buyer) sets it. Placeholder until the economy is approved.")]
        [SerializeField, Min(0)] private int baseValue;
        [Tooltip("Networked prefab spawned when the item is dropped. Needs NetworkObject + WorldItem and must be in the FishNet spawnable prefabs.")]
        [SerializeField] private NetworkObject worldPrefab;

        public int Id => id;
        public string DisplayName => displayName;
        public string ShortLabel => shortLabel;
        public ItemKind Kind => kind;
        public Sprite Icon => icon;
        public int Size => size;
        public int MaxStack => maxStack;
        public int BaseValue => baseValue;
        public NetworkObject WorldPrefab => worldPrefab;

        public ItemInfo ToInfo() => new ItemInfo(id, size, maxStack);
    }
}
