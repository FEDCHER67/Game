using FishNet.Object;
using FishNet.Object.Synchronizing;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Syringe = the anesthesia syringe (v01 name kept for the v01 builder).</summary>
    public enum OperationToolKind { Scalpel = 0, Syringe = 1, BloodSyringe = 2 }
    public enum ToolMode : byte { Docked = 0, Held = 1, Loose = 2, Returning = 3 }

    /// <summary>One physical networked tool of a table. The server owns its mode and, while it is loose, its physics;
    /// every client places it itself: docked in its tray slot, in a holder's hand at that holder's cursor, or flying
    /// back. It never gets lost: a loose tool flies back to its slot after a couple of seconds.</summary>
    [RequireComponent(typeof(Rigidbody))]
    public sealed class OperationTool : NetworkBehaviour
    {
        [SerializeField] private OperationToolKind kind;
        [SerializeField] private int stockIndex;
        [SerializeField] private Transform visual;
        [SerializeField] private Collider hoverCollider;
        [SerializeField] private Collider solidCollider;
        [Tooltip("Root (tip) position in slot space when docked: puts the tool's middle on the slot, resting on it.")]
        [SerializeField] private Vector3 dockOffset = new(-0.12f, 0.02f, 0f);
        [Tooltip("Rotation (slot space) that lays the tool flat along the slot's +X.")]
        [SerializeField] private Vector3 dockEuler = new(0, 0, -90);
        [Header("Syringe parts (optional)")]
        [SerializeField] private Transform[] plunger;
        [SerializeField] private Transform liquid;
        [SerializeField] private float plungerTravel = 0.06f;
        [SerializeField] private float liquidBottom = 0.08f;
        [SerializeField] private float liquidLength = 0.065f;

        private readonly SyncVar<int> holder = new(-1);
        private readonly SyncVar<byte> mode = new((byte)ToolMode.Docked);
        private readonly SyncVar<float> fill = new();
        private readonly SyncVar<NetworkObject> tableObject = new();
        private readonly SyncVar<Vector3> loosePosition = new(new SyncTypeSettings(0.05f));
        private readonly SyncVar<Quaternion> looseRotation = new(new SyncTypeSettings(0.05f));
        private Rigidbody body;
        private NetworkOperationTable table;
        private float modeTime;
        private float nextPose;
        private Vector3 flyFrom;
        private Quaternion flyFromRotation;
        private Vector3[] plungerRest;
        private Vector3 liquidRest;

        public OperationToolKind Kind => kind;
        public int StockIndex => stockIndex;
        public ToolSlot Slot => kind == OperationToolKind.Scalpel ? ToolSlot.Scalpel : kind == OperationToolKind.BloodSyringe ? ToolSlot.Blood : ToolSlot.Anesthesia;
        public int Holder => holder.Value;
        public ToolMode Mode => (ToolMode)mode.Value;
        public float Fill => fill.Value;
        public bool CollectBlood => kind == OperationToolKind.BloodSyringe;
        public NetworkOperationTable Table => table != null ? table : table = tableObject.Value != null ? tableObject.Value.GetComponent<NetworkOperationTable>() : null;
        public Transform Visual => visual;

        private void Awake()
        {
            body = GetComponent<Rigidbody>();
            body.isKinematic = true; body.useGravity = false; body.interpolation = RigidbodyInterpolation.None;
            if (plunger != null) { plungerRest = new Vector3[plunger.Length]; for (int i = 0; i < plunger.Length; i++) if (plunger[i] != null) plungerRest[i] = plunger[i].localPosition; }
            if (liquid != null) liquidRest = liquid.localScale;
            mode.OnChange += (a, b, server) => { modeTime = 0f; if ((ToolMode)b == ToolMode.Returning) { flyFrom = transform.position; flyFromRotation = transform.rotation; } };
        }

        // ---------- server ----------
        public void ServerInit(NetworkOperationTable owner)
        {
            table = owner; tableObject.Value = owner.NetworkObject;
            ServerDock();
        }
        public void ServerTake(int clientId)
        {
            holder.Value = clientId; mode.Value = (byte)ToolMode.Held; modeTime = 0f;
            body.isKinematic = true; body.useGravity = false; body.interpolation = RigidbodyInterpolation.None;
        }
        public void ServerDock()
        {
            holder.Value = -1; mode.Value = (byte)ToolMode.Docked; modeTime = 0f;
            body.isKinematic = true; body.useGravity = false; body.interpolation = RigidbodyInterpolation.None;
            if (Table != null) { var pose = Table.DockPose(this); transform.SetPositionAndRotation(pose.position, pose.rotation); }
        }
        /// <summary>Dropped where it is (holder left or disconnected): falls, then flies back to its slot.</summary>
        public void ServerDrop()
        {
            holder.Value = -1; mode.Value = (byte)ToolMode.Loose; modeTime = 0f;
            // The transform was driven while kinematic; hand that exact pose to the physics body before it falls.
            body.position = transform.position; body.rotation = transform.rotation;
            body.interpolation = RigidbodyInterpolation.Interpolate;
            body.isKinematic = false; body.useGravity = true;
            body.linearVelocity = Vector3.zero; body.angularVelocity = Random.insideUnitSphere * 2f;
            loosePosition.Value = transform.position; looseRotation.Value = transform.rotation;
        }
        public void ServerSetFill(float value) { if (Mathf.Abs(fill.Value - value) > 0.0005f || (value == 0f && fill.Value != 0f) || (value >= 1f && fill.Value < 1f)) fill.Value = value; }
        public void ServerHoldAt(Pose pose) { transform.SetPositionAndRotation(pose.position, pose.rotation); }
        public void ServerTick(float dt)
        {
            modeTime += dt;
            switch (Mode)
            {
                case ToolMode.Docked:
                    if (Table != null) { var pose = Table.DockPose(this); transform.SetPositionAndRotation(pose.position, pose.rotation); }
                    break;
                case ToolMode.Loose:
                    if (Time.time >= nextPose)
                    {
                        nextPose = Time.time + 0.05f; loosePosition.Value = transform.position; looseRotation.Value = transform.rotation;
                    }
                    if (modeTime >= (Table != null ? Table.Tuning.toolReturnSeconds : 2f))
                    {
                        body.isKinematic = true; body.useGravity = false; body.interpolation = RigidbodyInterpolation.None;
                        flyFrom = transform.position; flyFromRotation = transform.rotation;
                        mode.Value = (byte)ToolMode.Returning; modeTime = 0f;
                    }
                    break;
                case ToolMode.Returning:
                    if (Table == null) break;
                    float t = modeTime / Table.Tuning.toolFlySeconds;
                    if (t >= 1f) { ServerDock(); break; }
                    var dock = Table.DockPose(this);
                    transform.SetPositionAndRotation(Vector3.Lerp(flyFrom, dock.position, Smooth(t)) + Vector3.up * Mathf.Sin(t * Mathf.PI) * 0.12f,
                        Quaternion.Slerp(flyFromRotation, dock.rotation, Smooth(t)));
                    break;
            }
            bool solid = Mode == ToolMode.Loose;
            if (solidCollider != null && solidCollider.enabled != solid) solidCollider.enabled = solid;
        }

        // ---------- every peer ----------
        /// <summary>Docked pose for a slot frame whose +X is the lying direction and +Y is up.</summary>
        public Pose DockPoseFor(Pose slot)
        {
            return new Pose(slot.position + slot.rotation * dockOffset, slot.rotation * Quaternion.Euler(dockEuler));
        }
        private static Vector3 InverseScale(Transform t) { var s = t.lossyScale; return new Vector3(1f / Mathf.Max(1e-5f, s.x), 1f / Mathf.Max(1e-5f, s.y), 1f / Mathf.Max(1e-5f, s.z)); }
        private static float Smooth(float t) { t = Mathf.Clamp01(t); return t * t * (3f - 2f * t); }

        private void LateUpdate()
        {
            if (Table == null) return;
            if (!IsServerInitialized) modeTime += Time.deltaTime;
            bool hover = Mode == ToolMode.Docked || Mode == ToolMode.Loose;
            if (hoverCollider != null && hoverCollider.enabled != hover) hoverCollider.enabled = hover;
            if (!IsServerInitialized && solidCollider != null && solidCollider.enabled) solidCollider.enabled = false;
            switch (Mode)
            {
                case ToolMode.Docked:
                    var dock = Table.DockPose(this); transform.SetPositionAndRotation(dock.position, dock.rotation); break;
                case ToolMode.Held:
                    if (Table.TryHeldPose(this, Holder, out var held)) transform.SetPositionAndRotation(held.position, held.rotation);
                    break;
                case ToolMode.Loose:
                    if (!IsServerInitialized)
                        transform.SetPositionAndRotation(Vector3.Lerp(transform.position, loosePosition.Value, 1f - Mathf.Exp(-20f * Time.deltaTime)),
                            Quaternion.Slerp(transform.rotation, looseRotation.Value, 1f - Mathf.Exp(-20f * Time.deltaTime)));
                    break;
                case ToolMode.Returning:
                    if (!IsServerInitialized)
                    {
                        float t = modeTime / Table.Tuning.toolFlySeconds;
                        var d = Table.DockPose(this);
                        transform.SetPositionAndRotation(Vector3.Lerp(flyFrom, d.position, Smooth(t)) + Vector3.up * Mathf.Sin(Mathf.Clamp01(t) * Mathf.PI) * 0.12f,
                            Quaternion.Slerp(flyFromRotation, d.rotation, Smooth(t)));
                    }
                    break;
            }
            UpdateParts();
        }

        private void UpdateParts()
        {
            float f = Mathf.Clamp01(Fill);
            if (plunger != null && plungerRest != null && visual != null)
                for (int i = 0; i < plunger.Length; i++)
                {
                    if (plunger[i] == null) continue;
                    // Offset along the model's up axis (visual space), converted into the part's parent space.
                    Vector3 offset = plunger[i].parent.InverseTransformVector(visual.TransformVector(Vector3.up * (f * plungerTravel)));
                    plunger[i].localPosition = plungerRest[i] + offset;
                }
            if (liquid != null)
            {
                liquid.gameObject.SetActive(f > 0.01f);
                float h = Mathf.Max(0.0005f, f * liquidLength);
                liquid.localScale = new Vector3(liquidRest.x, h * 0.5f, liquidRest.z);
                liquid.localPosition = new Vector3(liquid.localPosition.x, liquidBottom + h * 0.5f, liquid.localPosition.z);
            }
        }
    }
}
