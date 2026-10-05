using System;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Server-authoritative hotbar of one player. The server runs InventoryModel and mirrors it into
    /// SyncTypes; the owning client only sends requests (pick up, drop, select) and reads the mirror.
    /// Slots and cash are visible to the owner only; the selected index is visible to everyone so
    /// other players can later show what is in hand.
    /// </summary>
    [RequireComponent(typeof(NetworkObject))]
    public sealed class NetworkInventory : NetworkBehaviour, IInventoryView
    {
        private const float ServerReachTolerance = 1.5f;
        private const float MaxClientOriginOffset = 2.4f;
        // The client view is about 1.85 m above the KCC motor pivot; compare against that, not the feet.
        private const float EyeHeight = 1.7f;

        [SerializeField] private ItemDatabase database;
        [SerializeField, Range(1, 8)] private int slotCount = 6;
        [Tooltip("Total size units the player can carry.")]
        [SerializeField, Min(1)] private int capacity = 12;
        [SerializeField, Min(0.5f)] private float reach = 2.5f;
        [Tooltip("Transform that actually moves with the player on the server (the KCC motor). Defaults to this transform.")]
        [SerializeField] private Transform reachOrigin;
        [SerializeField, Min(0.2f)] private float dropDistance = 0.8f;
        [SerializeField] private LayerMask pickupLayers = ~0;

        private readonly SyncList<ItemStack> slots =
            new SyncList<ItemStack>(new SyncTypeSettings(ReadPermission.OwnerOnly));
        private readonly SyncVar<int> cash = new SyncVar<int>(new SyncTypeSettings(ReadPermission.OwnerOnly));
        private readonly SyncVar<int> selected = new SyncVar<int>();

        private InventoryModel model;
        private int predictedSelection = -1;
        private readonly RaycastHit[] hits = new RaycastHit[16];

        /// <summary>Client side (owner): any slot, selection or cash change. Also raised on host.</summary>
        public event Action Changed;
        /// <summary>Server: items moved from the world into this inventory.</summary>
        public event Action<ItemStack> ServerPickedUp;
        /// <summary>Server: one item was dropped and spawned as this WorldItem.</summary>
        public event Action<ItemStack, WorldItem> ServerDropped;
        /// <summary>Server: the arrest penalty was applied (cash taken, confiscated item).</summary>
        public event Action<ArrestResult> ServerArrested;

        public bool IsLocalOwner => IsClientInitialized && IsOwner;
        public ItemDatabase Database => database;
        public float Reach => reach;
        public int SlotCount => slots.Count;
        public ItemStack GetSlot(int index) => index >= 0 && index < slots.Count ? slots[index] : ItemStack.Empty;
        public int SelectedIndex => predictedSelection >= 0 ? predictedSelection : selected.Value;
        public int Cash => cash.Value;
        /// <summary>Server only; null on clients.</summary>
        public InventoryModel ServerModel => model;
        private Transform ReachOrigin => reachOrigin != null ? reachOrigin : transform;

        private void Awake()
        {
            if (database == null)
                Debug.LogError("NetworkInventory requires an ItemDatabase", this);
            slots.OnChange += OnSlotsChanged;
            cash.OnChange += OnIntChanged;
            selected.OnChange += OnSelectedChanged;
        }

        private void OnDestroy()
        {
            slots.OnChange -= OnSlotsChanged;
            cash.OnChange -= OnIntChanged;
            selected.OnChange -= OnSelectedChanged;
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (reachOrigin == null)
            {
                // The prefab root does not move on the server; the moving part carries the NetworkTransform.
                var moving = GetComponentInChildren<FishNet.Component.Transforming.NetworkTransform>(true);
                if (moving != null) reachOrigin = moving.transform;
                Debug.LogWarning("NetworkInventory: reachOrigin not set, using " + ReachOrigin.name, this);
            }
            if (database == null) return;
            model = new InventoryModel(slotCount, capacity, database);
            slots.Clear();
            for (int i = 0; i < slotCount; i++)
                slots.Add(ItemStack.Empty);
            model.SlotChanged += i => slots[i] = model.GetSlot(i);
            model.SelectionChanged += i => selected.Value = i;
            model.CashChanged += c => cash.Value = c;
        }

        public override void OnStopServer()
        {
            // Carried items disappear with the player for now; dropping them is an open design decision.
            model = null;
            base.OnStopServer();
        }

        public override void OnStopClient()
        {
            predictedSelection = -1;
            base.OnStopClient();
        }

        // ---------- Owner-side requests (called by InventoryInput) ----------

        /// <summary>Owner: raycast for a WorldItem and ask the server to pick it up.</summary>
        public bool RequestPickup(Ray ray)
        {
            if (!IsOwner || !IsClientInitialized) return false;
            WorldItem item = FindWorldItem(ray);
            if (item == null || !item.IsSpawned) return false;
            ServerPickup(item.NetworkObject);
            return true;
        }

        /// <summary>Owner: drop one item from the selected slot in front of the view.</summary>
        public bool RequestDropSelected(Ray view)
        {
            if (!IsOwner || !IsClientInitialized || GetSlot(SelectedIndex).IsEmpty) return false;
            ServerDrop(SelectedIndex, view.origin, view.direction);
            return true;
        }

        public void RequestSelect(int index)
        {
            if (!IsOwner || !IsClientInitialized || index < 0 || index >= SlotCount || index == SelectedIndex)
                return;
            predictedSelection = index;
            Changed?.Invoke();
            ServerSelect(index);
        }

        public void RequestSelectNext(int direction)
        {
            int count = SlotCount;
            if (count == 0 || direction == 0) return;
            int step = direction > 0 ? 1 : -1;
            RequestSelect(((SelectedIndex + step) % count + count) % count);
        }

        private WorldItem FindWorldItem(Ray ray)
        {
            int count = Physics.RaycastNonAlloc(ray, hits, reach, pickupLayers, QueryTriggerInteraction.Collide);
            WorldItem best = null;
            float bestDistance = float.MaxValue;
            for (int i = 0; i < count; i++)
            {
                Collider hit = hits[i].collider;
                if (hit == null || hit.transform.IsChildOf(transform) || hits[i].distance >= bestDistance)
                    continue;
                // Solid non-item geometry in front blocks the pickup; item triggers do not.
                WorldItem item = hit.GetComponentInParent<WorldItem>();
                if (item == null && hit.isTrigger) continue;
                best = item;
                bestDistance = hits[i].distance;
            }
            return best;
        }

        // ---------- Server RPCs ----------

        [ServerRpc]
        private void ServerPickup(NetworkObject target, NetworkConnection sender = null)
        {
            if (model == null || sender == null || sender != Owner || !sender.IsActive ||
                target == null || !target.IsSpawned)
                return;
            WorldItem item = target.GetComponent<WorldItem>();
            if (item == null || item.Definition == null || database.Get(item.Definition.Id) != item.Definition ||
                Vector3.Distance(item.transform.position, ReachOrigin.position) > reach + ServerReachTolerance)
                return;
            int itemId = item.Definition.Id;
            int unitValue = item.UnitValue;
            int added = model.TryAdd(itemId, item.Count, unitValue);
            if (added <= 0) return;
            item.ServerTake(added);
            ServerPickedUp?.Invoke(new ItemStack(itemId, added, unitValue));
        }

        [ServerRpc]
        private void ServerDrop(int slot, Vector3 origin, Vector3 direction, NetworkConnection sender = null)
        {
            if (model == null || sender == null || sender != Owner || !sender.IsActive ||
                slot < 0 || slot >= model.SlotCount || !IsFinite(origin) || !IsFinite(direction) ||
                direction.sqrMagnitude < 0.9f || direction.sqrMagnitude > 1.1f ||
                Vector3.Distance(origin, ReachOrigin.position + Vector3.up * EyeHeight) > MaxClientOriginOffset)
                return;
            ItemStack stack = model.GetSlot(slot);
            ItemDefinition definition = stack.IsEmpty ? null : database.Get(stack.ItemId);
            // The item's own prefab, else the database's generic one that shows the item's world model.
            NetworkObject prefab = database.WorldPrefabFor(definition);
            if (definition == null || prefab == null || prefab.GetComponent<WorldItem>() == null)
            {
                Debug.LogWarning($"NetworkInventory: item {stack.ItemId} has no WorldItem prefab and cannot be dropped", this);
                return;
            }

            Vector3 position = origin + direction * dropDistance;
            if (Physics.Raycast(origin, direction, out RaycastHit wall, dropDistance, ~0, QueryTriggerInteraction.Ignore)
                && !wall.collider.transform.IsChildOf(transform))
                position = wall.point - direction * 0.2f;
            // WorldItem has no physics: put the drop on the ground instead of leaving it at eye height.
            if (Physics.Raycast(position, Vector3.down, out RaycastHit floor, 3f, ~0, QueryTriggerInteraction.Ignore))
                position = floor.point + Vector3.up * 0.05f;
            Vector3 flat = Vector3.ProjectOnPlane(direction, Vector3.up);
            Quaternion rotation = flat.sqrMagnitude > 0.001f ? Quaternion.LookRotation(flat) : Quaternion.identity;

            ItemStack dropped = model.TakeFromSlot(slot, 1);
            NetworkObject instance = Instantiate(prefab, position, rotation);
            WorldItem worldItem = instance.GetComponent<WorldItem>();
            worldItem.ServerSetDefinition(definition);
            worldItem.ServerSetContents(dropped.Count, dropped.UnitValue);
            Spawn(instance);
            ServerDropped?.Invoke(dropped, worldItem);
        }

        [ServerRpc]
        private void ServerSelect(int index, NetworkConnection sender = null)
        {
            if (model == null || sender == null || sender != Owner) return;
            model.Select(index);
        }

        // ---------- Server API (police, buyers, operations) ----------

        /// <summary>Server: adds items directly (e.g. organs from an operation). Returns how many fit.</summary>
        public int ServerTryAdd(ItemDefinition definition, int count, int unitValue)
        {
            if (!IsServerInitialized || model == null || definition == null) return 0;
            return model.TryAdd(definition.Id, count, unitValue);
        }

        /// <summary>Server: removes up to count items from a slot (e.g. a sale). Returns what was taken.</summary>
        public ItemStack ServerTakeFromSlot(int slot, int count) =>
            IsServerInitialized && model != null ? model.TakeFromSlot(slot, count) : ItemStack.Empty;

        public void ServerAddCash(int amount)
        {
            if (IsServerInitialized && model != null) model.AddCash(amount);
        }

        public bool ServerTrySpendCash(int amount) =>
            IsServerInitialized && model != null && model.TrySpendCash(amount);

        /// <summary>Server: one unit of the most expensive carried item (not removed), or empty.</summary>
        public ItemStack ServerMostValuableItem() =>
            IsServerInitialized && model != null ? model.MostValuableItem() : ItemStack.Empty;

        /// <summary>Server: canon section 80 penalty (minus cashPercent of cash, most expensive item confiscated).</summary>
        public ArrestResult ServerApplyArrestPenalty(int cashPercent = 10)
        {
            if (!IsServerInitialized || model == null) return default;
            ArrestResult result = model.ApplyArrestPenalty(cashPercent);
            ServerArrested?.Invoke(result);
            return result;
        }

        // ---------- Sync callbacks ----------

        private void OnSlotsChanged(SyncListOperation op, int index, ItemStack previous, ItemStack next, bool asServer) =>
            Changed?.Invoke();

        private void OnIntChanged(int previous, int next, bool asServer) => Changed?.Invoke();

        private void OnSelectedChanged(int previous, int next, bool asServer)
        {
            if (next == predictedSelection) predictedSelection = -1;
            Changed?.Invoke();
        }

        private static bool IsFinite(Vector3 v) =>
            !float.IsNaN(v.x) && !float.IsNaN(v.y) && !float.IsNaN(v.z) &&
            !float.IsInfinity(v.x) && !float.IsInfinity(v.y) && !float.IsInfinity(v.z);
    }
}
