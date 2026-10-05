using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// A networked item lying in the world that a NetworkInventory can pick up.
    /// Count and per-item value are server-owned, so an organ keeps its price when it is dropped
    /// and picked up again.
    /// </summary>
    [RequireComponent(typeof(NetworkObject))]
    public sealed class WorldItem : NetworkBehaviour
    {
        [SerializeField] private ItemDefinition definition;
        [SerializeField, Min(1)] private int initialCount = 1;
        [Tooltip("0 = use the definition's base value.")]
        [SerializeField, Min(0)] private int initialUnitValue;

        private readonly SyncVar<int> count = new SyncVar<int>();
        private readonly SyncVar<int> unitValue = new SyncVar<int>();

        public ItemDefinition Definition => definition;
        public int Count => count.Value;
        public int UnitValue => unitValue.Value;

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (count.Value <= 0) count.Value = initialCount;
            if (unitValue.Value <= 0) unitValue.Value = initialUnitValue > 0
                ? initialUnitValue : definition != null ? definition.BaseValue : 0;
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
    }
}
