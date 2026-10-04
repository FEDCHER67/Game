using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>All item definitions known to server and clients; ids are resolved here.</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Inventory/Item Database", fileName = "ItemDatabase")]
    public sealed class ItemDatabase : ScriptableObject, IItemCatalog
    {
        [SerializeField] private List<ItemDefinition> items = new List<ItemDefinition>();

        private Dictionary<int, ItemDefinition> byId;

        public IReadOnlyList<ItemDefinition> Items => items;

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
