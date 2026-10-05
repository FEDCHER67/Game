using System;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Offline inventory for test scenes without a network session (the map grey-box): the same InventoryModel,
    /// HUD and input as NetworkInventory, but pick-up takes the nearest OfflineWorldItem around the owner,
    /// which suits a third-person test character better than a view ray.
    /// </summary>
    public sealed class LocalInventory : MonoBehaviour, IInventoryView
    {
        [SerializeField] private ItemDatabase database;
        [SerializeField, Range(1, 8)] private int slotCount = 6;
        [Tooltip("Total size units the player can carry.")]
        [SerializeField, Min(1)] private int capacity = 12;
        [SerializeField, Min(0.5f)] private float reach = 2.5f;
        [SerializeField, Min(0)] private int startCash;

        private InventoryModel model;

        public event Action Changed;

        public bool IsLocalOwner => model != null;
        public ItemDatabase Database => database;
        public int SlotCount => model?.SlotCount ?? 0;
        public int SelectedIndex => model?.SelectedIndex ?? 0;
        public int Cash => model?.Cash ?? 0;
        public InventoryModel Model => model;

        /// <summary>Editor/builder setup before the scene runs.</summary>
        public void Configure(ItemDatabase itemDatabase, int slots, int carryCapacity, int cash)
        {
            database = itemDatabase;
            slotCount = Mathf.Clamp(slots, 1, 8);
            capacity = Mathf.Max(1, carryCapacity);
            startCash = Mathf.Max(0, cash);
        }

        private void Awake()
        {
            if (database == null)
            {
                Debug.LogError("LocalInventory requires an ItemDatabase", this);
                return;
            }
            model = new InventoryModel(slotCount, capacity, database);
            model.SlotChanged += _ => Changed?.Invoke();
            model.SelectionChanged += _ => Changed?.Invoke();
            model.CashChanged += _ => Changed?.Invoke();
            if (startCash > 0) model.AddCash(startCash);
        }

        public ItemStack GetSlot(int index) =>
            model != null && index >= 0 && index < model.SlotCount ? model.GetSlot(index) : ItemStack.Empty;

        public void RequestSelect(int index)
        {
            if (model != null && index >= 0 && index < model.SlotCount) model.Select(index);
        }

        public void RequestSelectNext(int direction)
        {
            if (model != null && direction != 0) model.SelectNext(direction > 0 ? 1 : -1);
        }

        public bool RequestPickup(Ray ray)
        {
            if (model == null) return false;
            OfflineWorldItem item = OfflineWorldItem.Nearest(transform.position, reach);
            if (item == null || item.Definition == null) return false;
            int unitValue = item.UnitValue > 0 ? item.UnitValue : item.Definition.BaseValue;
            int added = model.TryAdd(item.Definition.Id, item.Count, unitValue);
            if (added <= 0) return false;
            item.Take(added);
            return true;
        }

        public bool RequestDropSelected(Ray view)
        {
            if (model == null) return false;
            ItemStack selected = model.GetSlot(model.SelectedIndex);
            if (selected.IsEmpty || database.Get(selected.ItemId) == null) return false;
            ItemStack taken = model.TakeFromSlot(model.SelectedIndex, 1);
            // Drop where the player looks (the KCC body faces its last movement, not the first-person view).
            Vector3 forward = Vector3.ProjectOnPlane(view.direction, Vector3.up);
            if (forward.sqrMagnitude < 1e-4f) forward = Vector3.ProjectOnPlane(transform.forward, Vector3.up);
            forward.Normalize();
            OfflineWorldItem.Spawn(database.Get(taken.ItemId), 1, taken.UnitValue, transform.position + forward + Vector3.up * 0.3f);
            return true;
        }
    }
}
