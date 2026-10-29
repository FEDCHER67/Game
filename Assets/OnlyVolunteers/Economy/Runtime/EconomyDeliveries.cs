using System.Collections.Generic;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// Where equipment crates of one base are put down (§4.1). Place it in a scene at the base's yard / door; its Slots are
    /// local offsets tried in order. A slot is free when the ground is found near the anchor height and a crate-sized box
    /// above it touches nothing but that ground (another crate, a player, a wall, the van all count as occupied).
    /// Without an anchor in the scene, the hamlet base uses a provisional ring around the capture table spawn; other bases
    /// then wait ("no free place") until an anchor is authored. Nothing is lost or paid again meanwhile.
    /// </summary>
    public sealed class BaseDeliveryAnchor : MonoBehaviour
    {
        public static readonly List<BaseDeliveryAnchor> All = new List<BaseDeliveryAnchor>();

        public string BaseId = EconomyPrices.BaseHamlet;
        [Tooltip("Crate positions in this transform's frame, tried in order.")]
        public Vector3[] Slots =
        {
            new Vector3(0f, 0f, 0f), new Vector3(1.3f, 0f, 0f), new Vector3(-1.3f, 0f, 0f),
            new Vector3(0f, 0f, 1.3f), new Vector3(1.3f, 0f, 1.3f), new Vector3(-1.3f, 0f, 1.3f),
        };
        [Tooltip("Ground found further than this above / below the anchor does not count (roofs, holes), m.")]
        public float MaxHeightDifference = 1.2f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();

        private void OnEnable() { if (!All.Contains(this)) All.Add(this); }
        private void OnDisable() => All.Remove(this);

        public static BaseDeliveryAnchor For(string baseId)
        {
            foreach (BaseDeliveryAnchor a in All)
                if (a != null && a.isActiveAndEnabled && a.BaseId == baseId) return a;
            return null;
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.color = new Color(1f, 0.7f, 0.2f, 0.7f);
            foreach (Vector3 s in Slots) Gizmos.DrawWireCube(s + Vector3.up * 0.35f, EconomyDeliveries.CrateSize);
        }
    }

    /// <summary>The delivered crate (closed). E on foot opens it on the host (GreyboxUses: the map's single E handler).</summary>
    public sealed class DeliveryCrate : MonoBehaviour, IGreyboxUse
    {
        public string DeliveryId = "";
        public string Title = "";

        private void OnEnable() { if (!GreyboxUses.All.Contains(this)) GreyboxUses.All.Add(this); }
        private void OnDisable() => GreyboxUses.All.Remove(this);

        public bool Offer(GreyboxPawn pawn, out string label)
        {
            label = null;
            TeamEconomy economy = TeamEconomy.Instance;
            if (pawn == null || economy == null || !economy.IsServer) return false;
            Vector3 d = pawn.Position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > 2.4f * 2.4f) return false;
            label = "E — открыть ящик: " + Title;
            return true;
        }

        public void Use(GreyboxPawn pawn) => TeamEconomy.Instance?.ServerOpenCrate(DeliveryId);
    }

    /// <summary>A world-space label that turns to the camera.</summary>
    public sealed class EconomyLabel : MonoBehaviour
    {
        private void LateUpdate()
        {
            Camera cam = Camera.main;
            if (cam == null) return;
            Vector3 away = transform.position - cam.transform.position;
            if (away.sqrMagnitude > 1e-4f) transform.rotation = Quaternion.LookRotation(away, Vector3.up);
        }

        public static TextMesh Create(Transform parent, string text, Vector3 localPosition, float size, Color color)
        {
            var go = new GameObject("Label");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            // The parent may be scaled (a cube): keep the text at world size.
            Vector3 s = parent.lossyScale;
            go.transform.localScale = new Vector3(1f / Mathf.Max(0.01f, s.x), 1f / Mathf.Max(0.01f, s.y), 1f / Mathf.Max(0.01f, s.z));
            var mesh = go.AddComponent<TextMesh>();
            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            mesh.font = font;
            go.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            mesh.text = text;
            mesh.characterSize = size;
            mesh.fontSize = 48;
            mesh.anchor = TextAnchor.LowerCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.color = color;
            go.AddComponent<EconomyLabel>();
            return mesh;
        }
    }

    /// <summary>Placement and the placeholder objects of equipment deliveries (host side).</summary>
    public static class EconomyDeliveries
    {
        public static readonly Vector3 CrateSize = new Vector3(0.9f, 0.7f, 0.9f);
        private const string ItemPrefabFolder = "Economy/Equipment/";
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        private static readonly int ColorId = Shader.PropertyToID("_Color");
        private static readonly int GroundMask = ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.NpcSlide) | (1 << OvLayers.Player) | OvLayers.NpcMask);
        private static readonly Collider[] Overlaps = new Collider[16];

        /// <summary>A free slot at the order's base, or false (no anchor in this scene / every slot occupied).</summary>
        public static bool TryFindSlot(DeliveryOrder order, Dictionary<string, GameObject> placed, out int slot, out Vector3 position, out float yaw)
        {
            slot = -1;
            position = default;
            yaw = 0f;
            BaseDeliveryAnchor anchor = BaseDeliveryAnchor.For(order.baseId) ?? Fallback(order.baseId);
            if (anchor == null) return false;
            for (int i = 0; i < anchor.Slots.Length; i++)
            {
                Vector3 p = anchor.transform.TransformPoint(anchor.Slots[i]);
                if (!Physics.Raycast(p + Vector3.up * 1.5f, Vector3.down, out RaycastHit ground, 4f, GroundMask, QueryTriggerInteraction.Ignore)) continue;
                if (Mathf.Abs(ground.point.y - anchor.transform.position.y) > anchor.MaxHeightDifference) continue;
                if (Occupied(ground.point, anchor.transform.rotation, ground.collider)) continue;
                slot = i;
                position = ground.point;
                yaw = anchor.transform.eulerAngles.y;
                return true;
            }
            return false;
        }

        private static bool Occupied(Vector3 ground, Quaternion rotation, Collider groundCollider)
        {
            Vector3 half = CrateSize * 0.5f;
            Vector3 centre = ground + Vector3.up * (half.y + 0.06f);
            int n = Physics.OverlapBoxNonAlloc(centre, half, Overlaps, rotation, ~0, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
                if (Overlaps[i] != null && Overlaps[i] != groundCollider) return true;
            return false;
        }

        /// <summary>Provisional hamlet anchor until one is authored in the scene: a ring around the capture table spawn
        /// (the base B02 shed). Other bases have no fallback: their crates wait for an authored anchor.</summary>
        private static BaseDeliveryAnchor Fallback(string baseId)
        {
            if (baseId != EconomyPrices.BaseHamlet) return null;
            CaptureDirector director = CaptureDirector.Instance;
            if (director == null || director.TableSpawn == null) return null;
            var go = new GameObject("[Economy] Delivery anchor (provisional, hamlet)");
            go.transform.SetPositionAndRotation(director.TableSpawn.position, Quaternion.Euler(0f, director.TableSpawn.eulerAngles.y, 0f));
            var anchor = go.AddComponent<BaseDeliveryAnchor>();
            anchor.BaseId = EconomyPrices.BaseHamlet;
            var slots = new List<Vector3>();
            foreach (float radius in new[] { 2.4f, 3.6f, 4.8f })
                for (int k = 0; k < 8; k++)
                {
                    float a = k * Mathf.PI / 4f;
                    slots.Add(new Vector3(Mathf.Sin(a) * radius, 0f, Mathf.Cos(a) * radius));
                }
            anchor.Slots = slots.ToArray();
            Debug.Log("[ECON] no BaseDeliveryAnchor for the hamlet base in this scene: provisional ring around the table spawn " + director.TableSpawn.position);
            return anchor;
        }

        public static GameObject CreateCrate(DeliveryOrder order)
        {
            EquipmentOffer item = EconomyPrices.FindEquipment(order.itemId);
            string title = item != null ? item.Title : order.itemId;
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "DeliveryCrate_" + order.id;
            go.transform.SetPositionAndRotation(new Vector3(order.x, order.y + CrateSize.y * 0.5f + 0.02f, order.z), Quaternion.Euler(0f, order.yaw, 0f));
            go.transform.localScale = CrateSize;
            Tint(go, new Color(0.55f, 0.38f, 0.2f));
            var crate = go.AddComponent<DeliveryCrate>();
            crate.DeliveryId = order.id;
            crate.Title = title;
            EconomyLabel.Create(go.transform, "Ящик: " + title + "\n" + order.id + " · E — открыть", new Vector3(0f, 0.75f, 0f), 0.05f, new Color(1f, 0.92f, 0.7f));
            return go;
        }

        /// <summary>The unpacked item: its prefab (Resources/Economy/Equipment/&lt;id&gt;) when one exists, else a labelled
        /// placeholder box. It keeps its place across save / load (the delivery record holds it).</summary>
        public static GameObject CreateUnpacked(DeliveryOrder order)
        {
            EquipmentOffer item = EconomyPrices.FindEquipment(order.itemId);
            string title = item != null ? item.Title : order.itemId;
            var position = new Vector3(order.x, order.y, order.z);
            var rotation = Quaternion.Euler(0f, order.yaw, 0f);
            GameObject prefab = Resources.Load<GameObject>(ItemPrefabFolder + order.itemId);
            if (prefab != null)
            {
                GameObject real = Object.Instantiate(prefab, position, rotation);
                real.name = prefab.name + "_" + order.id;
                return real;
            }
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "Equipment_" + order.itemId + "_" + order.id + " (placeholder)";
            var size = new Vector3(0.6f, 0.5f, 0.6f);
            go.transform.SetPositionAndRotation(new Vector3(order.x, order.y + size.y * 0.5f + 0.02f, order.z), rotation);
            go.transform.localScale = size;
            Tint(go, new Color(0.35f, 0.55f, 0.75f));
            EconomyLabel.Create(go.transform, title + "\n(заглушка — модели ещё нет)", new Vector3(0f, 0.55f, 0f), 0.045f, Color.white);
            return go;
        }

        private static void Tint(GameObject go, Color color)
        {
            if (!go.TryGetComponent(out Renderer renderer)) return;
            var block = new MaterialPropertyBlock();
            block.SetColor(BaseColor, color);
            block.SetColor(ColorId, color);
            renderer.SetPropertyBlock(block);
        }
    }
}
