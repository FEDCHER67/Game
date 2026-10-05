using System.Collections.Generic;
using FishNet.Object;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>All item definitions known to server and clients; ids are resolved here.</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Inventory/Item Database", fileName = "ItemDatabase")]
    public sealed class ItemDatabase : ScriptableObject, IItemCatalog
    {
        [SerializeField] private List<ItemDefinition> items = new List<ItemDefinition>();
        [Tooltip("Networked WorldItem prefab without its own definition, used to drop items that have no worldPrefab. " +
                 "It shows the item's world model. Must be in the FishNet spawnable prefabs.")]
        [SerializeField] private NetworkObject genericWorldPrefab;

        private Dictionary<int, ItemDefinition> byId;

        public IReadOnlyList<ItemDefinition> Items => items;
        public NetworkObject GenericWorldPrefab => genericWorldPrefab;

        /// <summary>The item's own networked prefab, else the generic one; null when neither is set.</summary>
        public NetworkObject WorldPrefabFor(ItemDefinition item) =>
            item == null ? null : item.WorldPrefab != null ? item.WorldPrefab : genericWorldPrefab;

        public ItemDefinition Get(int itemId)
        {
            EnsureLookup();
            return byId.TryGetValue(itemId, out ItemDefinition item) ? item : null;
        }

        public bool TryGet(int itemId, out ItemInfo info)
        {
            ItemDefinition item = Get(itemId);
            info = item != null ? item.ToInfo() : default;
            return item != null;
        }

        private void OnEnable() => byId = null;

        private void OnValidate()
        {
            byId = null;
            var seen = new HashSet<int>();
            foreach (ItemDefinition item in items)
                if (item != null && !seen.Add(item.Id))
                    Debug.LogError($"ItemDatabase: duplicate item id {item.Id} ({item.name})", this);
        }

        private void EnsureLookup()
        {
            if (byId != null) return;
            byId = new Dictionary<int, ItemDefinition>();
            foreach (ItemDefinition item in items)
                if (item != null && !byId.ContainsKey(item.Id))
                    byId.Add(item.Id, item);
        }
    }
}
