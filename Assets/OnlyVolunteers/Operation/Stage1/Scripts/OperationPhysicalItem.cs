using FishNet.Object;
using FishNet.Object.Synchronizing;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Physical merchandise (organ or sealed blood bag). It stays spawned while held, so a handoff or a
    /// disconnect can never destroy its identity. In table mode it hangs at its holder's cursor; outside it uses the
    /// existing first-person physical carry of NetworkInventory.</summary>
    [RequireComponent(typeof(WorldItem), typeof(NetworkPhysicsBody))]
    public sealed class OperationPhysicalItem : NetworkBehaviour, IPhysicalInventoryItem
    {
        [SerializeField] private OperationTuning tuning;
        private readonly SyncVar<string> identity = new();
        private readonly SyncVar<int> grade = new();
        private readonly SyncVar<int> kind = new();
        private readonly SyncVar<int> organIndex = new(-1);
        private readonly SyncVar<NetworkObject> holder = new();
        private WorldItem world;
        private Rigidbody body;
        private Collider[] colliders;
        private NetworkInventory inventory;
        private float nextImpact;
        private Vector3 target;
        private bool tableTarget;
        public OperationItemState Data { get; private set; }
        public string Identity => identity.Value;
        public int Grade => grade.Value;
        public int Kind => kind.Value;
        public int OrganIndex => organIndex.Value;
        public NetworkObject Holder => holder.Value;
        public WorldItem World => world;
        public bool IsOrgan => Kind <= 1;
        public string Title => Kind == 2 ? "Пакет крови" : Kind == 3 ? "Шприц с кровью" :
            OrganIndex >= 0 && OrganIndex < 3 ? OperationText.Organs[OrganIndex] : Kind == 1 ? "Печень" : "Почка";
        public string Inspection => Kind == 2 ? "Пакет крови · $" + (tuning != null ? tuning.bloodValue : 50) + " · не портится" :
            Title + " · " + OperationText.Tier(Grade);
        private void Awake() { world = GetComponent<WorldItem>(); body = GetComponent<Rigidbody>(); colliders = GetComponentsInChildren<Collider>(true); }
        private bool sized;
        private void LateUpdate()
        {
            // One organ size everywhere: in the body, on the tray, in the hand, dropped (OperationOrganSize).
            if (!sized && IsOrgan && OrganIndex >= 0 && world != null && world.Definition != null)
                sized = OrganV03() || OperationOrganSize.Fit(transform, world.Definition.WorldModelSize);
            if (!sized && Kind == 2 && !string.IsNullOrEmpty(Identity)) sized = BagV05();
            bool free = Holder == null;
            foreach (var c in colliders) if (c != null && c.enabled != free) c.enabled = free;
        }
        public override void OnStartServer() { base.OnStartServer(); if (Data != null) RefreshValue(); }
        public void Initialize(OperationItemState data, OperationTuning config, ItemDefinition definition)
        {
            Data = data; tuning = config; identity.Value = data.id; grade.Value = data.grade; kind.Value = data.kind; organIndex.Value = data.organIndex;
            world = GetComponent<WorldItem>();
            world.ServerSetDefinition(definition); RefreshValue();
        }
        private void RefreshValue()
        {
            grade.Value = Data.grade; kind.Value = Data.kind; organIndex.Value = Data.organIndex;
            int value = Data.kind >= 2 ? (Data.kind == 2 ? tuning.bloodValue : 0) : OrganGrading.UnitValue(world.Definition.BaseValue, (OrganQuality)Mathf.Clamp(Data.grade, 0, 4));
            world.ServerSetContents(1, value);
        }
        public bool ServerTryHold(NetworkInventory owner)
        {
            if (!IsServerInitialized || owner == null || holder.Value != null || GetComponent<NetworkPhysicsBody>().HasHolder) return false;
            inventory = owner; holder.Value = owner.NetworkObject;
            body.isKinematic = true; body.useGravity = false;
            foreach (var c in colliders) if (c != null) c.enabled = false;
            return true;
        }
        public void ServerRelease(Vector3 position, Vector3 velocity)
        {
            if (!IsServerInitialized) return;
            inventory = null; holder.Value = null; tableTarget = false;
            transform.position = position; body.position = position; body.rotation = transform.rotation;
            body.isKinematic = false; body.useGravity = true;
            foreach (var c in colliders) if (c != null) c.enabled = true;
            // Round 3: a charged throw (ThrowCharge, server-computed) may leave faster than the old 6 m/s cap.
            body.linearVelocity = Vector3.ClampMagnitude(velocity, OnlyVolunteers.Inventory.ThrowCharge.MaxSpeedLight + OnlyVolunteers.Inventory.ThrowCharge.LiftFull);
            body.angularVelocity = Vector3.zero;
            nextImpact = Time.time + 0.4f; // a gentle placement never counts as a drop
        }
        /// <summary>v03: the very ORGAN_*_v03 mesh that sat in the body, unscaled (1:1), front side up on the tray.</summary>
        private bool OrganV03()
        {
            if (tuning == null || !tuning.anatomyV03 || tuning.organModelsV03 == null || OrganIndex >= tuning.organModelsV03.Length || tuning.organModelsV03[OrganIndex] == null) return false;
            var holder = ReplaceModel(tuning.organModelsV03[OrganIndex], Quaternion.Euler(-90f, 0f, 0f));
            if (holder == null) return false;
            RefitCollider(holder);
            return true;
        }
        /// <summary>v05 bag, full: the same model as the tray's bags, laid flat at their size.</summary>
        private bool BagV05()
        {
            if (tuning == null || tuning.bloodBagModel == null) return false;
            var holder = ReplaceModel(tuning.bloodBagModel, Quaternion.identity);
            if (holder == null) return false;
            var model = holder.GetChild(holder.childCount - 1);
            OperationPresentation.LayFlat(model, holder);
            OperationPresentation.Fit(model, holder, OperationBloodFill.TrayBagSize, true);
            OperationBloodFill.Attach(model).SetImmediate(1f);
            RefitCollider(holder);
            return true;
        }
        /// <summary>Replaces the item's model under its WorldModel child (keeping that child's collider, refitted).</summary>
        private Transform ReplaceModel(GameObject source, Quaternion rotation)
        {
            var holder = transform.Find(ItemWorldModel.ChildName);
            if (holder == null) return null;
            for (int i = holder.childCount - 1; i >= 0; i--) { var c = holder.GetChild(i).gameObject; c.SetActive(false); Destroy(c); }
            holder.localScale = Vector3.one;
            var copy = OperationPresentation.VisualCopy(source, source.name).transform;
            copy.SetParent(holder, false); copy.localPosition = Vector3.zero; copy.localRotation = rotation; copy.localScale = Vector3.one;
            return holder;
        }
        private void RefitCollider(Transform holder)
        {
            if (holder.TryGetComponent(out BoxCollider box))
            {
                var bounds = new Bounds(); bool any = false;
                foreach (var r in holder.GetComponentsInChildren<Renderer>())
                {
                    var wb = r.bounds;
                    for (int k = 0; k < 8; k++)
                    {
                        var p = holder.InverseTransformPoint(new Vector3((k & 1) == 0 ? wb.min.x : wb.max.x, (k & 2) == 0 ? wb.min.y : wb.max.y, (k & 4) == 0 ? wb.min.z : wb.max.z));
                        if (!any) { bounds = new Bounds(p, Vector3.zero); any = true; } else bounds.Encapsulate(p);
                    }
                }
                if (any) { box.center = bounds.center; box.size = bounds.size; }
            }
            colliders = GetComponentsInChildren<Collider>(true);
        }
        public void SetTableTarget(Vector3 position) { target = position; tableTarget = true; }
        public void LeaveTable() => tableTarget = false;
        private void FixedUpdate()
        {
            if (!IsServerInitialized || Data == null) return;
            if (inventory != null)
            {
                var player = inventory.GetComponent<NetworkPlayer>();
                if (player == null || player.Owner == null || !player.Owner.IsActive) inventory.ServerReleasePhysical(transform.position, Vector3.zero);
                else
                {
                    Vector3 at = tableTarget ? target : player.MotorPosition + Vector3.up * 1.3f + player.MotorForward * 0.55f;
                    body.MovePosition(at);
                }
            }
            if (Data.kind == 3 && !Data.expired)
            { Data.freshness += Time.fixedDeltaTime; if (Data.freshness >= tuning.unsealedBloodSeconds) Data.expired = true; }
            Data.position = transform.position; Data.rotation = transform.rotation;
        }
        /// <summary>Server: no landing damage for a while (a restored item settling on its tray or the floor is no drop).</summary>
        public void SuppressImpactsFor(float seconds) => nextImpact = Mathf.Max(nextImpact, Time.time + seconds);

        private void OnCollisionEnter(Collision collision)
        {
            if (!IsServerInitialized || Data == null || Data.kind >= 2 || Time.time < nextImpact ||
                collision.relativeVelocity.magnitude < tuning.impactSpeed) return;
            nextImpact = Time.time + tuning.impactCooldown;
            Data.grade = Mathf.Max(0, Data.grade - tuning.impactLoss); RefreshValue();
            Debug.Log($"[OPS] IMPACT id={Identity} grade={Data.grade} speed={collision.relativeVelocity.magnitude:F2}");
        }
    }
}
