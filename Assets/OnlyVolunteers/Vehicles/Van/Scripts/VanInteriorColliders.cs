using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Extra van colliders for riding in and loading the cargo bay (NPC capture stage 1, draft section 3):
    // - StepSlide / StepRear: ~0.28 m steps under the sliding door and the rear doors, so a crouched KCC player climbs to
    //   the 0.55 m floor in two steps (the KCC step limit is 0.5 m). Visible (dark trim material), the model has none.
    // - Partition: invisible, floor to roof behind the front seats (the driver stays visible from the bay).
    // - LeftWallLow / RightWallLow thickened outward to 0.12 m and the Roof 0.05 m thicker upward: the 5 cm boxes were
    //   thin enough for a fast body to tunnel through. The inside of the bay (1.04 m between the arches) is unchanged.
    // Then every collider of the van, doors and wheels included, goes on layer Vehicle (when the project has it).
    // Runtime setup, idempotent by child name: an existing Van.prefab instance (grey-box scenes) gets it in Awake without a
    // prefab rebuild, and VanSetupBuilder bakes the same children into a rebuilt prefab (Build at edit time).
    // Boxes are given in the model's Blender coordinates (min..max, Z up, -Y forward, +X = vehicle left), mapped to
    // van-root space like VanSetupBuilder: root = (-bx, bz, -by) + offset, the offset read off the prefab's "Floor" box
    // (0, 0, -0.02 for VAN-TIER0 v02), so the boxes follow a re-imported model.
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-200)]
    public sealed class VanInteriorColliders : MonoBehaviour
    {
        private const string Container = "Colliders";
        private const string VehicleLayerName = "Vehicle"; // OvLayers.Vehicle (10)
        private const string StepMaterial = "VAN_Trim_Dark";

        [Tooltip("Draw the two new steps (the model has no step mesh).")]
        public bool ShowSteps = true;

        // VanSetupBuilder's Floor box, the reference for the Blender -> van-root offset.
        private static readonly Vector3 FloorMin = new(-0.94f, -1.70f, 0.35f);
        private static readonly Vector3 FloorMax = new(0.94f, 2.19f, 0.55f);

        private static readonly (string name, Vector3 min, Vector3 max, bool step)[] Added =
        {
            ("StepSlide", new(-1.18f, -0.44f, 0.20f), new(-0.94f, 0.90f, 0.28f), true),
            ("StepRear", new(-0.80f, 2.36f, 0.20f), new(0.80f, 2.56f, 0.30f), true),
            ("Partition", new(-0.89f, -0.50f, 0.55f), new(0.89f, -0.44f, 1.98f), false),
        };

        // Existing VanSetupBuilder boxes, resized (absolute numbers, so running twice changes nothing).
        private static readonly (string name, Vector3 min, Vector3 max)[] Resized =
        {
            ("LeftWallLow", new(0.89f, -0.44f, 0.55f), new(1.01f, 2.19f, 1.30f)),
            ("RightWallLow", new(-1.01f, 0.90f, 0.55f), new(-0.89f, 2.19f, 1.30f)),
            ("Roof", new(-0.80f, -0.99f, 1.98f), new(0.80f, 2.19f, 2.13f)),
        };

        private Vector3 _offset = new(0f, 0f, -0.02f);

        private void Awake() => Build();

        /// <summary>Adds or updates the extra boxes and puts every van collider on layer Vehicle. Safe to call again.</summary>
        public void Build()
        {
            Transform container = transform.Find(Container);
            if (container == null)
            {
                container = new GameObject(Container).transform;
                container.SetParent(transform, false);
            }
            if (container.Find("Floor") is Transform floor && floor.TryGetComponent(out BoxCollider floorBox))
                _offset = RootCentre(floorBox) - Axes((FloorMin + FloorMax) * 0.5f);

            Material stepMaterial = ShowSteps ? FindMaterial(StepMaterial) : null;
            foreach ((string name, Vector3 min, Vector3 max, bool step) in Added)
            {
                if (step && ShowSteps) VisibleBox(container, name, min, max, stepMaterial);
                else ColliderBox(container, name, min, max);
            }
            foreach ((string name, Vector3 min, Vector3 max) in Resized)
                if (container.Find(name) is Transform t && t.TryGetComponent(out BoxCollider box))
                    SetBox(box, min, max);

            int layer = LayerMask.NameToLayer(VehicleLayerName);
            if (layer < 0)
            {
                Debug.LogWarning($"[Van] Layer '{VehicleLayerName}' is missing (ProjectSettings/TagManager); van colliders stay on their layers.");
                return;
            }
            foreach (Collider c in GetComponentsInChildren<Collider>(true))
                c.gameObject.layer = layer;
        }

        private static Vector3 Axes(Vector3 b) => new(-b.x, b.z, -b.y);
        private Vector3 RootPoint(Vector3 b) => Axes(b) + _offset;
        private static Vector3 RootSize(Vector3 min, Vector3 max)
        {
            Vector3 s = Axes(max - min);
            return new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z));
        }

        private Vector3 RootCentre(BoxCollider box) => transform.InverseTransformPoint(box.transform.TransformPoint(box.center));

        // Collider only: a plain child with a BoxCollider in van-root space.
        private void ColliderBox(Transform container, string name, Vector3 min, Vector3 max)
        {
            Transform t = container.Find(name);
            if (t == null)
            {
                t = new GameObject(name).transform;
                t.SetParent(container, false);
            }
            if (!t.TryGetComponent(out BoxCollider box)) box = t.gameObject.AddComponent<BoxCollider>();
            SetBox(box, min, max);
        }

        // Collider plus a cube mesh: the child sits at the box centre, scaled to its size.
        private void VisibleBox(Transform container, string name, Vector3 min, Vector3 max, Material material)
        {
            Transform t = container.Find(name);
            if (t == null)
            {
                t = new GameObject(name).transform;
                t.SetParent(container, false);
            }
            t.SetLocalPositionAndRotation(
                container.InverseTransformPoint(transform.TransformPoint(RootPoint((min + max) * 0.5f))),
                Quaternion.Inverse(container.rotation) * transform.rotation);
            t.localScale = RootSize(min, max);
            if (!t.TryGetComponent(out BoxCollider box)) box = t.gameObject.AddComponent<BoxCollider>();
            box.center = Vector3.zero;
            box.size = Vector3.one;
            if (!t.TryGetComponent(out MeshFilter filter)) filter = t.gameObject.AddComponent<MeshFilter>();
            if (filter.sharedMesh == null) filter.sharedMesh = CubeMesh();
            if (!t.TryGetComponent(out MeshRenderer renderer)) renderer = t.gameObject.AddComponent<MeshRenderer>();
            if (material != null) renderer.sharedMaterial = material;
            else if (renderer.sharedMaterial == null) renderer.enabled = false; // no van material found: collider only
        }

        // Box given in Blender min/max -> centre/size in the collider's own space (its transform is normally identity).
        private void SetBox(BoxCollider box, Vector3 min, Vector3 max)
        {
            Transform t = box.transform;
            box.center = t.InverseTransformPoint(transform.TransformPoint(RootPoint((min + max) * 0.5f)));
            Vector3 s = t.InverseTransformVector(transform.TransformVector(RootSize(min, max)));
            box.size = new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z));
        }

        private Material FindMaterial(string materialName)
        {
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
                foreach (Material m in r.sharedMaterials)
                    if (m != null && m.name == materialName)
                        return m;
            return null;
        }

        private static Mesh _cube;

        // Unity's built-in cube mesh, taken from a throwaway primitive (no collider ever touches the van).
        private static Mesh CubeMesh()
        {
            if (_cube != null) return _cube;
            GameObject temp = GameObject.CreatePrimitive(PrimitiveType.Cube);
            _cube = temp.GetComponent<MeshFilter>().sharedMesh;
            DestroyImmediate(temp);
            return _cube;
        }
    }
}
