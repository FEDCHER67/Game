using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Blood level shown in a blood bag on the tray (Fedya 2026-10-18: the bag fills as the syringe empties).
    /// Art contract for the coming blood bag v05: a child whose name contains "FILL" (e.g. BLOOD_FILL), its pivot at the
    /// empty end and its local +Y the fill direction; it is scaled 0..1 on Y. Until that art lands a placeholder red
    /// slab with the same contract is laid inside the current bag's bounds, so swapping the art needs no code change.
    /// (The syringe already follows the same idea through OperationTool's plunger/liquid fields.)</summary>
    public sealed class OperationBloodFill : MonoBehaviour
    {
        /// <summary>Largest side of a blood bag on the tray (the slot size; the sealed bag item uses the same).</summary>
        public const float TrayBagSize = 0.2f;
        // BLOOD-BAG v05 (blood_bag_v05_validation.json): BLOOD_LIQUID blend shapes Fill_025..Fill_100, cumulative
        // weight_k = clamp(4 fill - (k - 1), 0, 1); the imported mesh bounds are the empty film, so the full bounds are set.
        private static readonly string[] Shapes = { "Fill_025", "Fill_050", "Fill_075", "Fill_100" };
        private static readonly Bounds LiquidFullBounds = new Bounds(new Vector3(0f, 0f, 0.0838f), new Vector3(0.1154f, 0.0302f, 0.1676f));
        private SkinnedMeshRenderer liquid;
        private Renderer tubeLiquid;
        private readonly int[] shapeIndex = { -1, -1, -1, -1 };
        private Transform fill;
        private float restY = 1f, shown, target;
        private static Material placeholder;

        public float Shown => shown;

        public static OperationBloodFill Attach(Transform bag)
        {
            var view = bag.GetComponent<OperationBloodFill>();
            if (view == null) view = bag.gameObject.AddComponent<OperationBloodFill>();
            view.Build();
            return view;
        }

        public void SetTarget(float amount) => target = Mathf.Clamp01(amount);
        public void SetImmediate(float amount) { target = shown = Mathf.Clamp01(amount); Apply(shown); }
        public bool BlendShapes => liquid != null;

        private void Build()
        {
            if (fill != null || liquid != null) return;
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null || smr.sharedMesh.blendShapeCount < 4) continue;
                for (int k = 0; k < 4; k++) shapeIndex[k] = smr.sharedMesh.GetBlendShapeIndex(Shapes[k]);
                if (System.Array.IndexOf(shapeIndex, -1) >= 0) continue;
                liquid = smr; liquid.localBounds = LiquidFullBounds;
                break;
            }
            if (liquid != null)
            {
                foreach (var r in GetComponentsInChildren<Renderer>(true)) if (r.name == "BLOOD_TUBE_LIQUID") tubeLiquid = r;
                Apply(0f);
                return;
            }
            foreach (var t in GetComponentsInChildren<Transform>(true))
                if (t != transform && t.name.ToUpperInvariant().Contains("FILL")) { fill = t; break; }
            if (fill == null) fill = Placeholder();
            restY = Mathf.Max(1e-4f, fill.localScale.y);
            Apply(0f);
        }

        /// <summary>A thin red slab lying in the bag, growing from one end along the bag's long side.</summary>
        private Transform Placeholder()
        {
            var min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue); var max = -min;
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                if (!(r is MeshRenderer) || !r.TryGetComponent(out MeshFilter f) || f.sharedMesh == null) continue;
                var b = f.sharedMesh.bounds;
                for (int c = 0; c < 8; c++)
                {
                    var corner = new Vector3((c & 1) == 0 ? b.min.x : b.max.x, (c & 2) == 0 ? b.min.y : b.max.y, (c & 4) == 0 ? b.min.z : b.max.z);
                    Vector3 p = transform.InverseTransformPoint(r.transform.TransformPoint(corner));
                    min = Vector3.Min(min, p); max = Vector3.Max(max, p);
                }
            }
            if (min.x > max.x) { min = new Vector3(-0.055f, 0f, -0.085f); max = new Vector3(0.055f, 0.02f, 0.085f); }
            Vector3 size = max - min, centre = (min + max) * 0.5f;
            bool alongZ = size.z >= size.x;
            float length = (alongZ ? size.z : size.x) * 0.8f, width = (alongZ ? size.x : size.z) * 0.62f;
            var root = new GameObject("BLOOD_FILL (placeholder)").transform;
            root.SetParent(transform, false);
            // Pivot at the empty end, local +Y along the long side, a thin layer on the bag's top face (the pale empty bag is
            // opaque, so the blood shows from the table camera above).
            Vector3 start = centre - (alongZ ? Vector3.forward : Vector3.right) * length * 0.5f; start.y = max.y + 0.0015f;
            root.localPosition = start;
            root.localRotation = Quaternion.FromToRotation(Vector3.up, alongZ ? Vector3.forward : Vector3.right);
            var slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Destroy(slab.GetComponent<Collider>());
            slab.name = "fill"; slab.transform.SetParent(root, false);
            slab.transform.localScale = new Vector3(width, length, 0.002f);
            slab.transform.localPosition = new Vector3(0f, length * 0.5f, 0f);
            if (placeholder == null) placeholder = OperationVisuals.Lit("blood fill (placeholder)", new Color(0.62f, 0.03f, 0.08f), 0.55f);
            slab.GetComponent<Renderer>().sharedMaterial = placeholder;
            return root;
        }

        private void Apply(float amount)
        {
            if (liquid != null)
            {
                for (int k = 0; k < 4; k++) liquid.SetBlendShapeWeight(shapeIndex[k], Mathf.Clamp01(4f * amount - k) * 100f);
                liquid.enabled = amount >= 0.01f;
                if (tubeLiquid != null) tubeLiquid.enabled = amount >= 0.01f;
                return;
            }
            if (fill == null) return;
            fill.gameObject.SetActive(amount > 0.004f);
            var s = fill.localScale; fill.localScale = new Vector3(s.x, Mathf.Max(1e-4f, amount) * restY, s.z);
        }

        private void LateUpdate()
        {
            if (fill == null && liquid == null) return;
            // Smooth on every peer: the server's value arrives in steps.
            float next = Mathf.MoveTowards(shown, target, Time.deltaTime * 2.5f);
            if (Mathf.Approximately(next, shown) && Mathf.Approximately(shown, target)) return;
            shown = next; Apply(shown);
        }
    }
}
