using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// A networked item lying in the world that a NetworkInventory can pick up.
    /// Count and per-item value are server-owned, so an organ keeps its price when it is dropped
    /// and picked up again.
    /// A prefab with its own definition shows its own renderers; a generic prefab (no definition, see
    /// ItemDatabase.GenericWorldPrefab) gets the item id from the server and shows the item's world model.
    /// </summary>
    public interface IPhysicalInventoryItem
    {
        bool ServerTryHold(NetworkInventory inventory);
        void ServerRelease(Vector3 position, Vector3 velocity);
    }

    [RequireComponent(typeof(NetworkObject))]
    public sealed class WorldItem : NetworkBehaviour
    {
        // Presentation observers live outside the Inventory assembly (e.g. the water audio watcher).
        public static event System.Action<WorldItem> Enabled;
        private void OnEnable() => Enabled?.Invoke(this);

        [SerializeField] private ItemDefinition definition;
        [SerializeField, Min(1)] private int initialCount = 1;
        [Tooltip("0 = use the definition's base value.")]
        [SerializeField, Min(0)] private int initialUnitValue;
        [Tooltip("Resolves the synced item id on a generic prefab (no definition set). Not needed otherwise.")]
        [SerializeField] private ItemDatabase database;

        private readonly SyncVar<int> count = new SyncVar<int>();
        private readonly SyncVar<int> unitValue = new SyncVar<int>();
        /// <summary>Set by the server on a generic prefab; 0 when the prefab's own definition is used.</summary>
        private readonly SyncVar<int> itemId = new SyncVar<int>();

        private ItemDefinition resolved;
        private bool visualBuilt;

        public ItemDefinition Definition
        {
            get
            {
                if (definition != null) return definition;
                if (resolved == null && itemId.Value > 0 && database != null) resolved = database.Get(itemId.Value);
                return resolved;
            }
        }
        public int Count => count.Value;
        public int UnitValue => unitValue.Value;
        // Server authoritative metadata; NetworkInventory must move Stack (see G49 report), not re-create by type id.
        private readonly SyncVar<SyringeInstance> syringe = new SyncVar<SyringeInstance>();
        public SyringeInstance Syringe => syringe.Value;
        public ItemStack Stack => new ItemStack(Definition != null ? Definition.Id : 0, Count, UnitValue, Syringe);
        public void ServerSetSyringe(SyringeInstance instance) { syringe.Value = instance?.Copy(); }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (count.Value <= 0) count.Value = initialCount;
            ItemDefinition item = Definition;
            if (unitValue.Value <= 0) unitValue.Value = initialUnitValue > 0
                ? initialUnitValue : item != null ? item.BaseValue : 0;
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            itemId.OnChange += OnItemIdChanged;
            TryBuildVisual();
        }

        public override void OnStopClient()
        {
            itemId.OnChange -= OnItemIdChanged;
            base.OnStopClient();
        }

        /// <summary>Server only, call between Instantiate and Spawn on a generic prefab (used when dropping).</summary>
        public void ServerSetDefinition(ItemDefinition item)
        {
            if (definition != null || item == null) return;
            resolved = item;
            itemId.Value = item.Id;
        }

        /// <summary>Server only, call between Instantiate and Spawn (used when dropping).</summary>
        public void ServerSetContents(int newCount, int newUnitValue)
        {
            count.Value = Mathf.Max(1, newCount);
            unitValue.Value = Mathf.Max(0, newUnitValue);
        }

        /// <summary>Server only. Removes picked-up items and despawns when nothing is left.</summary>
        public void ServerTake(int taken)
        {
            if (!IsServerInitialized || taken <= 0) return;
            int left = count.Value - taken;
            if (left > 0) count.Value = left;
            else Despawn();
        }

        private void OnItemIdChanged(int previous, int next, bool asServer)
        {
            if (asServer) return;
            if (!IsServerInitialized) resolved = null; // on a host keep the server's authoritative reference
            TryBuildVisual();
        }

        // Client presentation: the world model plus a trigger collider for the owner's pick-up ray. Skipped when the
        // prefab already has its own renderers. No Rigidbody: the server places drops on the floor (NetworkInventory).
        private void TryBuildVisual()
        {
            if (visualBuilt || GetComponentInChildren<Renderer>(true) != null) return;
            ItemDefinition item = Definition;
            if (item == null) return;
            ItemWorldModel.Build(item, transform, true, true);
            visualBuilt = true;
        }
    }
}
