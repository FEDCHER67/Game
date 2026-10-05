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

    /// <summary>Collider shape of a dropped item. Auto: a capsule along the longest side for long items, otherwise a box.</summary>
    public enum ItemColliderShape
    {
        Auto = 0,
        Box = 1,
        Sphere = 2,
        Capsule = 3,
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

        [Header("World model (dropped item)")]
        [Tooltip("Model shown when the item lies in the world (a prefab or an imported FBX). Empty = a small grey box.")]
        [SerializeField] private GameObject worldModel;
        [Tooltip("Largest side of the dropped model, metres. 0 = the model's own size.")]
        [SerializeField, Min(0f)] private float worldModelSize = 0.3f;
        [SerializeField] private ItemColliderShape colliderShape = ItemColliderShape.Auto;
        [Tooltip("Rigidbody mass of an offline drop, kg.")]
        [SerializeField, Min(0.01f)] private float dropMass = 0.4f;
        [Tooltip("0 = lands dead, 1 = rubber ball. Organs about 0.3.")]
        [SerializeField, Range(0f, 1f)] private float dropBounciness = 0.3f;
        [Tooltip("How much the model squashes on a hard landing (0 = rigid, 0.3 = jelly).")]
        [SerializeField, Range(0f, 0.5f)] private float dropSquish = 0.2f;

        public int Id => id;
        public string DisplayName => displayName;
        public string ShortLabel => shortLabel;
        public ItemKind Kind => kind;
        public Sprite Icon => icon;
        public int Size => size;
        public int MaxStack => maxStack;
        public int BaseValue => baseValue;
        public NetworkObject WorldPrefab => worldPrefab;
        public GameObject WorldModel => worldModel;
        public float WorldModelSize => worldModelSize;
        public ItemColliderShape ColliderShape => colliderShape;
        public float DropMass => dropMass;
        public float DropBounciness => dropBounciness;
        public float DropSquish => dropSquish;

        public ItemInfo ToInfo() => new ItemInfo(id, size, maxStack);
    }
}
