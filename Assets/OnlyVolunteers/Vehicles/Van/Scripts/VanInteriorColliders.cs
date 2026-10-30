using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Extra van colliders for riding in and loading the cargo bay (NPC capture stage 1, draft section 3):
    // - StepSlide / StepRear: ~0.28 m steps under the sliding door and the rear doors. Visible (dark trim material), the
    //   model has none. The player walks on the ramps below, not on these (they stay for looks and for NPC bodies).
    // - Partition: invisible, floor to roof behind the front seats (the driver stays visible from the bay).
    // - LeftWallLow / RightWallLow thickened outward to 0.12 m and the Roof 0.05 m thicker upward: the 5 cm boxes were
    //   thin enough for a fast body to tunnel through. The inside of the bay (1.04 m between the arches) is unchanged.
    // - RampSlide / RampRear (Fedya's playtest, 2026-10-05: the steps needed a jump): invisible slopes from the wheels'
    //   contact height over the outer edge of each step up to the edge of the floor (rear: the bumper top). The KCC never steps
    //   onto a dynamic rigidbody (KinematicCharacterMotor.EvaluateHitStability skips DetectSteps for it), so on the van
    //   only slopes and edges lower than ~0.17 m (capsule radius 0.35 at the 60 degree stability limit) are walkable;
    //   a 48/55 degree slope is. Layer VehicleInterior, which PhysX ignores entirely: only the grey-box KCC player, which
    //   adds that layer to its motor's CollidableLayers (GreyboxKccPawn), walks on them; NPC bodies, the world and the van
    //   never touch them. They sit on their own kinematic Rigidbody ("Ramps"), so the van's mass and inertia stay as they
    //   were. Stand on the ramp by walking (W), then Ctrl to crouch in under the door top.
    // - Loading surfaces (Fedya's playtests, 2026-10-05): Floor, BumperRear, both steps and the rear wheel housings
    //   (HousingRearLeft/Right, which a body pushed in through the rear doors rubs along) get a smooth material (0.3,
    //   combined by Minimum) at runtime, so it wins over the NPC body's Average-combined high grip: a body leaning on the
    //   floor edge or the bumper slides in when pushed by the ankles, while on the ground its far end still holds and
    //   pivots. Loaded bodies are kept in place by GreyboxVanCargo.LoadedDamping. Play mode only: an edit-time Build
    //   (VanSetupBuilder) must not bake a non-asset material into the prefab.
    // - SlideRear (stage 9, NPC ragdoll): an invisible slide for NPC bodies only, on layer NpcSlide, which collides with
    //   NpcBody and nothing else (the player, the van, vehicles, props and the world never touch it). A ragdoll dragged in
    //   alone through the rear doors jammed with its hips hooked over the bumper's outer top edge (0.62 m) and its legs
    //   hanging against the vertical bumper face: pulled level, nothing turned the pull into lift (RagdollSmokeTest r6b, 2
    //   runs of 3). The slide runs from the ground 0.57 m behind the bumper up to its top edge (46 degrees), slippery (0.05,
    //   Minimum, Play mode only), so hips and legs ride up it. Its own kinematic body, like the ramps; switched off when the
    //   project has no NpcSlide layer (it would block everything). Fedya's playtest 2026-10-11: it works only while a rear
    //   door is open and the van stands (SlideMaxSpeed); otherwise it excludes every layer. It reaches the ground behind the
    //   bumper, so a van driving or backing over a lying body met the body with it (backing over one at 8 km/h it held the
    //   chest for 3 s in the smoke test).
    // Then every collider of the van, doors and wheels included, goes on layer Vehicle (when the project has it); the
    // ramps then go on VehicleInterior (or are switched off when the project has no such layer).
    // Runtime setup, idempotent by child name: an existing Van.prefab instance (grey-box scenes) gets it in Awake without a
    // prefab rebuild, and VanSetupBuilder bakes the same children into a rebuilt prefab (Build at edit time).
    // Boxes are given in the model's Blender coordinates (min..max, Z up, -Y forward, +X = vehicle left), mapped to
    // van-root space like VanSetupBuilder: root = (-bx, bz, -by) + offset, the offset read off the prefab's "Floor" box
    // (0, 0, -0.02 for VAN-TIER0 v02), so the boxes follow a re-imported model.
    // ModelRevision picks the table set: 2 = v02 (Van.prefab, every existing scene, the default), 5 = v05 (Van_v05.prefab,
    // Vadim 30.10: v02 stretched to 6.15 x 2.16 x 2.6 m, bulkhead behind the seats; VanOnly scene). Same boxes, v05 sizes.
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-200)]
    public sealed class VanInteriorColliders : MonoBehaviour
    {
        private const string Container = "Colliders";
        private const string VehicleLayerName = "Vehicle"; // OvLayers.Vehicle (10)
        private const string StepMaterial = "VAN_Trim_Dark";

        [Tooltip("Draw the two new steps (the model has no step mesh).")]
        public bool ShowSteps = true;

        [Tooltip("Stage 9 (Fedya's playtest 2026-10-11): the NPC body slide works only while a rear door is open and the van " +
                 "is slower than this (m/s).")]
        public float SlideMaxSpeed = 1f;
        [Tooltip("Model layout the boxes follow: 2 = VAN-TIER0-ASTRA-001 v02 (Van.prefab), 5 = v05 (Van_v05.prefab). Set before " +
                 "Build (the prefab bakes it).")]
        public int ModelRevision = 2;

        /// <summary>Test hook (RagdollSmokeTest's before rows): the body slide always on, as before 2026-10-11.</summary>
        public static bool LegacyBodySlide;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => LegacyBodySlide = false;

        private readonly List<BoxCollider> _slides = new();
        private bool _slideOn = true;
        private Rigidbody _vanBody;
        private VanDoor[] _rearDoors;

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

        // Ramps, Blender coordinates: centre of the low (outer) edge, centre of the high (inner) edge, half the width.
        // RampSlide: through the step's outer top edge (-1.18, 0.28) and the floor edge (-0.94, 0.55), 48 degrees, down to
        // the wheels' contact height (0). RampRear: 55 degrees down from the bumper's outer top edge (2.36, 0.62), passing
        // ~3 cm above the step's outer edge. Both below the KCC's 60 degree stability limit.
        private static readonly (string name, Vector3 low, Vector3 high, Vector3 halfWidth)[] Ramps =
        {
            ("RampSlide", new(-1.429f, 0.23f, 0f), new(-0.94f, 0.23f, 0.55f), new(0f, 0.67f, 0f)),
            ("RampRear", new(0f, 2.794f, 0f), new(0f, 2.36f, 0.62f), new(0.80f, 0f, 0f)),
        };
        private const string RampBody = "Ramps";
        private const string RampLayerName = "VehicleInterior"; // OvLayers.VehicleInterior (11)
        private const float RampThickness = 0.12f;

        // Body slides (stage 9), Blender coordinates like the ramps: SlideRear from the ground at y 2.93 (0.57 m behind the
        // bumper's outer face) up to 4 cm inside its outer top edge, 5 mm above its top (2.32, 0.625): 46 degrees.
        private static readonly (string name, Vector3 low, Vector3 high, Vector3 halfWidth)[] BodySlides =
        {
            ("SlideRear", new(0f, 2.93f, 0f), new(0f, 2.32f, 0.625f), new(0.80f, 0f, 0f)),
        };
        private const string SlideBody = "BodySlides";
        private const string SlideLayerName = "NpcSlide"; // OvLayers.NpcSlide (14)
        private const float SlideFriction = 0.05f;
        private static PhysicsMaterial _slippery;

        private static readonly string[] SmoothSurfaces =
            { "Floor", "BumperRear", "StepSlide", "StepRear", "HousingRearLeft", "HousingRearRight" };
        private const float SmoothFriction = 0.3f;
        private static PhysicsMaterial _smooth;

        // v05 (build_van.py --revision 5): floor 0.557, skin x +-1.081, inner walls +-1.031, inner roof 2.54, bulkhead
        // y -0.534..-0.494, sliding door y -0.492..1.054, rear wall y 3.116, rear sill 0.65, bumper to y 3.315, doors x +-0.92.
        private static readonly Vector3 FloorMinV05 = new(-1.081f, -1.9915f, 0.2895f);
        private static readonly Vector3 FloorMaxV05 = new(1.081f, 3.1156f, 0.5566f);
        private static readonly (string name, Vector3 min, Vector3 max, bool step)[] AddedV05 =
        {
            ("StepSlide", new(-1.321f, -0.492f, 0.20f), new(-1.081f, 1.0544f, 0.28f), true),
            ("StepRear", new(-0.92f, 3.3147f, 0.20f), new(0.92f, 3.5147f, 0.30f), true),
            ("Partition", new(-1.031f, -0.534f, 0.5566f), new(1.031f, -0.494f, 2.54f), false),
        };
        private static readonly (string name, Vector3 min, Vector3 max)[] ResizedV05 =
        {
            ("LeftWallLow", new(1.031f, -0.535f, 0.5566f), new(1.151f, 3.1156f, 1.5583f)),
            ("RightWallLow", new(-1.151f, 1.0544f, 0.5566f), new(-1.031f, 3.1156f, 1.5583f)),
            ("Roof", new(-0.92f, -1.1598f, 2.54f), new(0.92f, 3.1156f, 2.65f)),
        };
        // RampSlide through the step's outer top edge (-1.321, 0.28) and the floor edge (-1.081, 0.557), 49 degrees; RampRear
        // 55 degrees down from the bumper's outer top edge (3.315, 0.65), 6 cm over the step's outer edge.
        private static readonly (string name, Vector3 low, Vector3 high, Vector3 halfWidth)[] RampsV05 =
        {
            ("RampSlide", new(-1.564f, 0.2812f, 0f), new(-1.081f, 0.2812f, 0.5566f), new(0f, 0.7732f, 0f)),
            ("RampRear", new(0f, 3.77f, 0f), new(0f, 3.3147f, 0.6501f), new(0.92f, 0f, 0f)),
        };
        private static readonly (string name, Vector3 low, Vector3 high, Vector3 halfWidth)[] BodySlidesV05 =
        {
            ("SlideRear", new(0f, 3.885f, 0f), new(0f, 3.275f, 0.655f), new(0.92f, 0f, 0f)),
        };

        private bool V05 => ModelRevision >= 5;

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
                _offset = RootCentre(floorBox) - Axes(V05 ? (FloorMinV05 + FloorMaxV05) * 0.5f : (FloorMin + FloorMax) * 0.5f);

            Material stepMaterial = ShowSteps ? FindMaterial(StepMaterial) : null;
            foreach ((string name, Vector3 min, Vector3 max, bool step) in V05 ? AddedV05 : Added)
            {
                if (step && ShowSteps) VisibleBox(container, name, min, max, stepMaterial);
                else ColliderBox(container, name, min, max);
            }
            foreach ((string name, Vector3 min, Vector3 max) in V05 ? ResizedV05 : Resized)
                if (container.Find(name) is Transform t && t.TryGetComponent(out BoxCollider box))
                    SetBox(box, min, max);
            if (Application.isPlaying)
                foreach (string name in SmoothSurfaces)
                    if (container.Find(name) is Transform t && t.TryGetComponent(out BoxCollider box))
                        box.sharedMaterial = Smooth;

            int layer = LayerMask.NameToLayer(VehicleLayerName);
            if (layer < 0)
            {
                Debug.LogWarning($"[Van] Layer '{VehicleLayerName}' is missing (ProjectSettings/TagManager); van colliders stay on their layers.");
                return;
            }
            foreach (Collider c in GetComponentsInChildren<Collider>(true))
                c.gameObject.layer = layer;
            BuildRamps(container);
            BuildSlides(container);
        }

        // ---------- Body slides (stage 9) ----------

        private void BuildSlides(Transform container)
        {
            Transform holder = container.Find(SlideBody);
            int layer = LayerMask.NameToLayer(SlideLayerName);
            if (layer < 0)
            {
                Debug.LogWarning($"[Van] Layer '{SlideLayerName}' is missing (ProjectSettings/TagManager); the NPC body slide is off.");
                if (holder != null) holder.gameObject.SetActive(false);
                return;
            }
            if (holder == null)
            {
                holder = new GameObject(SlideBody).transform;
                holder.SetParent(container, false);
            }
            holder.gameObject.SetActive(true);
            holder.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            holder.localScale = Vector3.one;
            if (!holder.TryGetComponent(out Rigidbody body)) body = holder.gameObject.AddComponent<Rigidbody>();
            body.isKinematic = true;
            body.useGravity = false;
            body.interpolation = RigidbodyInterpolation.None;
            holder.gameObject.layer = layer;
            foreach ((string name, Vector3 low, Vector3 high, Vector3 halfWidth) in V05 ? BodySlidesV05 : BodySlides)
            {
                Ramp(holder, name, low, high, halfWidth, layer);
                if (!Application.isPlaying || !(holder.Find(name) is Transform t) || !t.TryGetComponent(out BoxCollider box)) continue;
                box.sharedMaterial = Slippery;
                if (!_slides.Contains(box)) _slides.Add(box);
            }
        }

        // The slide is for loading at a standstill (SlideMaxSpeed, a rear door open). Off, it excludes every layer: the shape
        // stays, because switching a collider off and on drops its ignore pairs (the standing NPCs' with the van). Coming on
        // under a body it pushes the body out, as it always did with a body laid there.
        private void FixedUpdate()
        {
            if (_slides.Count == 0) return;
            bool on = LegacyBodySlide || SlideWanted();
            if (on == _slideOn) return;
            _slideOn = on;
            foreach (BoxCollider slide in _slides)
            {
                if (slide == null) continue;
                slide.excludeLayers = on ? 0 : ~0;
                slide.layerOverridePriority = on ? 0 : 100;
            }
        }

        private bool SlideWanted()
        {
            if (_vanBody == null) _vanBody = GetComponent<Rigidbody>();
            if (_vanBody != null && _vanBody.linearVelocity.sqrMagnitude > SlideMaxSpeed * SlideMaxSpeed) return false;
            if (_rearDoors == null)
            {
                var rear = new List<VanDoor>();
                foreach (VanDoor door in GetComponentsInChildren<VanDoor>(true))
                    if (door.name.Contains("Rear")) rear.Add(door);
                _rearDoors = rear.ToArray();
            }
            if (_rearDoors.Length == 0) return true; // no rear doors found: on, as before
            foreach (VanDoor door in _rearDoors)
                if (door != null && door.Openness > 0.3f) return true;
            return false;
        }

        private static PhysicsMaterial Slippery => _slippery != null ? _slippery : _slippery = new PhysicsMaterial("VanBodySlide")
        {
            staticFriction = SlideFriction,
            dynamicFriction = SlideFriction,
            bounciness = 0f,
            frictionCombine = PhysicsMaterialCombine.Minimum,
            bounceCombine = PhysicsMaterialCombine.Minimum,
            hideFlags = HideFlags.DontSave,
        };

        // ---------- Ramps ----------

        private void BuildRamps(Transform container)
        {
            Transform holder = container.Find(RampBody);
            if (holder == null)
            {
                holder = new GameObject(RampBody).transform;
                holder.SetParent(container, false);
            }
            holder.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            holder.localScale = Vector3.one;
            // Its own kinematic body: the boxes are not part of the van's compound collider (mass, inertia).
            if (!holder.TryGetComponent(out Rigidbody body)) body = holder.gameObject.AddComponent<Rigidbody>();
            body.isKinematic = true;
            body.useGravity = false;
            body.interpolation = RigidbodyInterpolation.None;

            int layer = LayerMask.NameToLayer(RampLayerName);
            if (layer < 0)
                Debug.LogWarning($"[Van] Layer '{RampLayerName}' is missing (ProjectSettings/TagManager); the step ramps are off.");
            holder.gameObject.layer = layer >= 0 ? layer : 0;
            foreach ((string name, Vector3 low, Vector3 high, Vector3 halfWidth) in V05 ? RampsV05 : Ramps)
                Ramp(holder, name, low, high, halfWidth, layer);
        }

        // A box whose top face runs from the low edge to the high edge, RampThickness thick below it.
        private void Ramp(Transform holder, string name, Vector3 low, Vector3 high, Vector3 halfWidth, int layer)
        {
            Vector3 a = RootPoint(low);
            Vector3 b = RootPoint(high);
            Vector3 slope = b - a;
            Vector3 across = Axes(halfWidth);
            Vector3 normal = Vector3.Cross(slope, across).normalized;
            if (normal.y < 0f) normal = -normal;
            Quaternion rootRotation = Quaternion.LookRotation(slope.normalized, normal);
            Vector3 centre = (a + b) * 0.5f - normal * (RampThickness * 0.5f);

            Transform t = holder.Find(name);
            if (t == null)
            {
                t = new GameObject(name).transform;
                t.SetParent(holder, false);
            }
            t.SetPositionAndRotation(transform.TransformPoint(centre), transform.rotation * rootRotation);
            t.localScale = Vector3.one;
            if (!t.TryGetComponent(out BoxCollider box)) box = t.gameObject.AddComponent<BoxCollider>();
            box.center = Vector3.zero;
            box.size = new Vector3(across.magnitude * 2f, RampThickness, slope.magnitude);
            box.enabled = layer >= 0; // on Default it would collide with everything
            t.gameObject.layer = layer >= 0 ? layer : 0;
        }

        private static PhysicsMaterial Smooth => _smooth != null ? _smooth : _smooth = new PhysicsMaterial("VanLoadingSurface")
        {
            staticFriction = SmoothFriction,
            dynamicFriction = SmoothFriction,
            bounciness = 0f,
            frictionCombine = PhysicsMaterialCombine.Minimum,
            bounceCombine = PhysicsMaterialCombine.Minimum,
            hideFlags = HideFlags.DontSave,
        };

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
