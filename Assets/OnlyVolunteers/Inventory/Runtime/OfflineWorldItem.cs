using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// An item lying in an offline test scene, picked up by LocalInventory (the networked game uses WorldItem).
    /// </summary>
    public sealed class OfflineWorldItem : MonoBehaviour
    {
        [SerializeField] private ItemDefinition definition;
        [SerializeField, Min(1)] private int count = 1;
        [Tooltip("Price per unit; 0 = the definition's base value.")]
        [SerializeField, Min(0)] private int unitValue;

        private static readonly List<OfflineWorldItem> Items = new();

        public ItemDefinition Definition => definition;
        public int Count => count;
        public int UnitValue => unitValue;

        public void Set(ItemDefinition itemDefinition, int itemCount, int value)
        {
            definition = itemDefinition;
            count = Mathf.Max(1, itemCount);
            unitValue = Mathf.Max(0, value);
        }

        private void OnEnable() => Items.Add(this);
        private void OnDisable() => Items.Remove(this);

        public static OfflineWorldItem Nearest(Vector3 from, float reach)
        {
            OfflineWorldItem best = null;
            float bestDistance = reach * reach;
            foreach (OfflineWorldItem item in Items)
            {
                if (item.definition == null) continue;
                float d = (item.transform.position - from).sqrMagnitude;
                if (d <= bestDistance)
                {
                    best = item;
                    bestDistance = d;
                }
            }
            return best;
        }

        public void Take(int amount)
        {
            count -= amount;
            if (count <= 0) Destroy(gameObject);
        }

        /// <summary>Drops the item as its world model (a grey box when it has none): a light physics body with a fitted
        /// collider, thrown with <paramref name="velocity"/>.</summary>
        public static OfflineWorldItem Spawn(ItemDefinition itemDefinition, int itemCount, int value, Vector3 position,
            Vector3 velocity = default)
        {
            var go = new GameObject($"Dropped_{(itemDefinition != null ? itemDefinition.DisplayName : "Item")}");
            go.transform.position = position;
            Transform model = ItemWorldModel.Build(itemDefinition, go.transform, false, false);
            Rigidbody body = ItemWorldModel.AddPhysics(go, itemDefinition, model);
            body.linearVelocity = velocity;
            // A little random tumble so two drops of the same organ do not land identically.
            body.angularVelocity = Random.insideUnitSphere * 3f;
            var item = go.AddComponent<OfflineWorldItem>();
            item.Set(itemDefinition, itemCount, value);
            return item;
        }
    }
}
