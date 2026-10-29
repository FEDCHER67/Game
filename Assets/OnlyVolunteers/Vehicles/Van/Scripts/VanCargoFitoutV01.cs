using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // The van's paid cargo-body fit-out on THIS machine (ECONOMY §6.2 + "Решение Феди 29.10 — удержание пленника"): the
    // bay's capacity (3 / 4 / 5, read by CaptureVanCapacity and the cargo HUD), containment I (floor rails, a D-ring per
    // place, a belt to each strapped captive: GreyboxVanCargo straps them and poses the belts) and containment II (padded
    // walls: GreyboxNpc does not knock). The economy applies it (TeamEconomy: the server state on the host, the snapshot on
    // clients); this component never buys, saves or decides anything itself.
    //
    // Data-driven by the van's cargo anchors, so a new van model only moves anchors: child "CargoAnchors" of the van root,
    // van-root space, names as below. Missing anchors are created from DefaultAnchors (VAN-TIER0-ASTRA-001 v02 measured off
    // VanSetupBuilder / VanInteriorColliders: floor 0.55, low walls x +-0.89 to 1.30 m, upper walls +-0.80, rear wheel
    // housings x +-0.52..0.89 z -2.04..-1.12 up to 0.85, sliding-door opening on +X z -0.92..0.42, rear opening z -2.21,
    // partition z 0.42), so the current prefab needs no rebuild; a model that ships its own CargoAnchors keeps them.
    //   Rail_<n>_A / Rail_<n>_B  floor rail end points (positions; the rail top is the anchor's y)
    //   Ring_<i>                 parking spot of D-ring i (i = 0..4, ring i is shown while i < capacity)
    //   Pad_<name>               padded panel box: position = centre, localScale = size (metres), rotation = the box's
    //   Door pads: Pad_RearLeft / Pad_RearRight are given in van space with the doors shut; their panels ride on the doors
    //   (VAN_Door_Rear_Left / VAN_Door_Rear_Right), built once the door is shut.
    // Visuals (child "CargoFitout", runtime meshes, no colliders: nothing here ever touches a player, an NPC or the van):
    // low-poly steel rails and D-rings, an orange webbing lap belt per strapped captive (from his D-ring up over the waist
    // or ankle, a buckle on top, down to a floor cup on the far side, as in the larger-van layout), quilted blue padding
    // (procedural diamond texture, metric UVs). About 0.2k triangles for I, 12 per panel for II.
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(100)] // after GreyboxVanCargo (-50) posed this frame's belts
    public sealed class VanCargoFitoutV01 : MonoBehaviour
    {
        public const int StockCapacity = 3;
        public const int MaxCapacity = 5;
        public const string AnchorsName = "CargoAnchors";
        public const string VisualsName = "CargoFitout";
        public const string RearLeftDoor = "VAN_Door_Rear_Left";
        public const string RearRightDoor = "VAN_Door_Rear_Right";
        private const string TrimMaterial = "VAN_Trim_Dark";
        private const float RailWidth = 0.04f, RailHeight = 0.012f;
        private const float BeltWidth = 0.045f, BeltThickness = 0.006f;
        private const float QuiltTile = 0.25f;

        [SerializeField] private int capacity = StockCapacity;
        [SerializeField] private bool restraints;
        [SerializeField] private bool padded;

        /// <summary>Lying NPCs the bay takes (3 stock, +1 per capacity step, at most 5).</summary>
        public int Capacity => capacity;
        /// <summary>Containment I bought: loaded NPCs are strapped up to the capacity.</summary>
        public bool Restraints => restraints;
        /// <summary>Containment II bought: padded walls, no knocking.</summary>
        public bool Padded => padded;
        /// <summary>Counts every applied change (logs, tests).</summary>
        public int Version { get; private set; }

        // Two rails along the walls in front of the rear wheel housings (the housings fill x +-0.52..0.89 behind z -1.12),
        // clear of the two lying lanes (x about +-0.4): the strap runs from the wall side over the waist.
        private static readonly (string name, Vector3 local)[] DefaultRails =
        {
            ("Rail_0_A", new Vector3(-0.72f, 0.55f, -1.06f)), ("Rail_0_B", new Vector3(-0.72f, 0.55f, 0.36f)),
            ("Rail_1_A", new Vector3(0.72f, 0.55f, -1.06f)), ("Rail_1_B", new Vector3(0.72f, 0.55f, 0.36f)),
        };
        private static readonly Vector3[] DefaultRings =
        {
            new(-0.72f, 0.55f, 0.15f), new(0.72f, 0.55f, 0.15f), new(-0.72f, 0.55f, -0.75f),
            new(0.72f, 0.55f, -0.75f), new(-0.72f, 0.55f, -0.30f),
        };
        // name, min, max (van root space, doors shut)
        private static readonly (string name, Vector3 min, Vector3 max)[] DefaultPads =
        {
            ("Pad_LeftLowFront", new(-0.89f, 0.57f, -1.10f), new(-0.855f, 1.30f, 0.40f)),
            ("Pad_LeftLowRear", new(-0.89f, 0.87f, -2.15f), new(-0.855f, 1.30f, -1.10f)),
            ("Pad_LeftHigh", new(-0.80f, 1.30f, -2.15f), new(-0.765f, 1.96f, 0.40f)),
            ("Pad_RightLowRear", new(0.855f, 0.87f, -2.15f), new(0.89f, 1.30f, -0.95f)),
            ("Pad_RightLowMid", new(0.855f, 0.57f, -1.10f), new(0.89f, 0.87f, -0.95f)),
            ("Pad_RightHigh", new(0.765f, 1.30f, -2.15f), new(0.80f, 1.96f, -0.95f)),
            ("Pad_Partition", new(-0.855f, 0.57f, 0.385f), new(0.855f, 1.96f, 0.42f)),
            // the rear doors' inner skin is at z -2.15 (frame) / -2.21 (glass): the panels sit just inside it
            ("Pad_RearLeft", new(-0.78f, 0.64f, -2.148f), new(-0.02f, 1.92f, -2.118f)),
            ("Pad_RearRight", new(0.02f, 0.64f, -2.148f), new(0.78f, 1.92f, -2.118f)),
        };

        private Transform anchors, visuals, railsRoot, ringsRoot, beltsRoot, padsRoot;
        private readonly List<(Vector3 a, Vector3 b)> rails = new();
        private readonly Transform[] ringParks = new Transform[MaxCapacity];
        private readonly Transform[] rings = new Transform[MaxCapacity];
        private const int BeltPieces = 4; // ring -> near side -> over the top -> far side -> floor cup
        private readonly Transform[][] belts = new Transform[MaxCapacity][];
        private readonly Transform[] buckles = new Transform[MaxCapacity];
        private readonly Transform[] cups = new Transform[MaxCapacity];
        private readonly int[] posedFrame = new int[MaxCapacity];
        private readonly Vector3[] posedAnchor = new Vector3[MaxCapacity];
        private readonly List<GameObject> doorPads = new();
        private readonly List<string> pendingDoorPads = new();
        private bool built;

        private static Material _metal, _rail, _webbing, _padding;
        private static Texture2D _quilt;
        private static Mesh _ringMesh, _beltMesh, _buckleMesh, _cupMesh;

        // ------------------------------------------------------------------ API

        public static VanCargoFitoutV01 Ensure(GameObject van)
        {
            if (van == null) return null;
            return van.TryGetComponent(out VanCargoFitoutV01 f) ? f : van.AddComponent<VanCargoFitoutV01>();
        }

        /// <summary>The fit-out of the van a carrier (its cargo bay) belongs to, or null.</summary>
        public static VanCargoFitoutV01 Of(ICarrier carrier)
        {
            if (carrier is not Component c || c == null) return null;
            return c.TryGetComponent(out VanCargoFitoutV01 f) ? f : c.GetComponentInParent<VanCargoFitoutV01>();
        }

        /// <summary>Containment II on the van of this carrier.</summary>
        public static bool IsPadded(ICarrier carrier)
        {
            VanCargoFitoutV01 f = Of(carrier);
            return f != null && f.padded;
        }

        public bool Matches(int newCapacity, bool newRestraints, bool newPadded) =>
            capacity == Mathf.Clamp(newCapacity, StockCapacity, MaxCapacity) && restraints == newRestraints && padded == newPadded && built;

        /// <summary>The purchases on this van now (idempotent: the same values change nothing).</summary>
        public void Apply(int newCapacity, bool newRestraints, bool newPadded)
        {
            newCapacity = Mathf.Clamp(newCapacity, StockCapacity, MaxCapacity);
            bool changed = newCapacity != capacity || newRestraints != restraints || newPadded != padded;
            capacity = newCapacity;
            restraints = newRestraints;
            padded = newPadded;
            EnsureBuilt();
            Refresh();
            if (changed) Version++;
        }

        /// <summary>Van-local point on the nearest floor rail (the strap's fitting slides on the track), from a world point.</summary>
        public Vector3 StrapAnchor(Vector3 world)
        {
            EnsureBuilt();
            Vector3 local = transform.InverseTransformPoint(world);
            Vector3 best = local;
            float bestD = float.MaxValue;
            foreach ((Vector3 a, Vector3 b) in rails)
            {
                Vector3 ab = b - a;
                float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector3.Dot(local - a, ab) / ab.sqrMagnitude) : 0f;
                Vector3 p = a + ab * t;
                float d = new Vector2(p.x - local.x, p.z - local.z).sqrMagnitude;
                if (d < bestD) { bestD = d; best = p; }
            }
            return best + Vector3.up * RailHeight;
        }

        /// <summary>A strap this frame: D-ring <paramref name="slot"/> stands at anchorLocal (van space); its lap belt runs from
        /// it to the near side of the body at targetWorld (the waist or an ankle), over its top (<paramref name="over"/> metres
        /// up, the buckle) and down the far side (<paramref name="halfWidth"/> from the middle) to a floor cup. Straps not
        /// posed in a frame are hidden (LateUpdate), their rings go back to their parking spots.</summary>
        public void PoseStrap(int slot, Vector3 anchorLocal, Vector3 targetWorld, float over = 0.2f, float halfWidth = 0.25f)
        {
            if (slot < 0 || slot >= MaxCapacity || !restraints) return;
            EnsureBuilt();
            posedFrame[slot] = Time.frameCount;
            posedAnchor[slot] = anchorLocal;
            Transform ring = rings[slot];
            if (ring != null)
            {
                ring.gameObject.SetActive(true);
                ring.localPosition = anchorLocal;
                ring.localRotation = RailRotation(anchorLocal);
            }
            if (belts[slot] == null) return;
            Vector3 p = transform.InverseTransformPoint(targetWorld);
            Vector3 a = anchorLocal + Vector3.up * 0.035f;
            Vector3 flat = new Vector3(p.x - a.x, 0f, p.z - a.z);
            float reach = flat.magnitude;
            Vector3 across = reach > 1e-3f ? flat / reach : Vector3.right;
            float half = Mathf.Clamp(halfWidth, 0.03f, 0.5f);
            float lift = Mathf.Max(0f, over);
            Vector3 near = p - across * Mathf.Min(half, reach) + Vector3.up * (lift * 0.35f);
            Vector3 top = p + Vector3.up * lift;
            Vector3 far = p + across * half + Vector3.up * (lift * 0.35f);
            Vector3 cup = new Vector3(far.x, anchorLocal.y, far.z) + across * 0.06f;
            Segment(belts[slot][0], a, near);
            Segment(belts[slot][1], near, top);
            Segment(belts[slot][2], top, far);
            Segment(belts[slot][3], far, cup);
            buckles[slot].gameObject.SetActive(true);
            buckles[slot].localPosition = top;
            buckles[slot].localRotation = Quaternion.LookRotation(across, Vector3.up);
            cups[slot].gameObject.SetActive(true);
            cups[slot].localPosition = cup;
            cups[slot].localRotation = Quaternion.LookRotation(across, Vector3.up);
        }

        // One straight piece of webbing between two van-space points (the unit belt mesh runs along +Z).
        private static void Segment(Transform t, Vector3 from, Vector3 to)
        {
            Vector3 d = to - from;
            float length = d.magnitude;
            if (length < 0.01f) { t.gameObject.SetActive(false); return; }
            t.gameObject.SetActive(true);
            Vector3 dir = d / length;
            t.localPosition = from;
            t.localRotation = Quaternion.LookRotation(dir, Mathf.Abs(Vector3.Dot(dir, Vector3.up)) > 0.98f ? Vector3.forward : Vector3.up);
            t.localScale = new Vector3(1f, 1f, length);
        }

        // ------------------------------------------------------------------ frame

        private void LateUpdate()
        {
            if (!built) return;
            int frame = Time.frameCount;
            for (int i = 0; i < MaxCapacity; i++)
            {
                if (belts[i] == null) continue;
                if (posedFrame[i] == frame) continue;
                foreach (Transform piece in belts[i]) if (piece.gameObject.activeSelf) piece.gameObject.SetActive(false);
                if (buckles[i].gameObject.activeSelf) buckles[i].gameObject.SetActive(false);
                if (cups[i].gameObject.activeSelf) cups[i].gameObject.SetActive(false);
                Park(i);
            }
            if (padded && pendingDoorPads.Count > 0) BuildDoorPads();
        }

        // ------------------------------------------------------------------ build

        private void EnsureBuilt()
        {
            if (built && anchors != null && visuals != null) return;
            built = false;
            anchors = Child(transform, AnchorsName);
            visuals = Child(transform, VisualsName);
            railsRoot = Child(visuals, "Rails");
            ringsRoot = Child(visuals, "Rings");
            beltsRoot = Child(visuals, "Belts");
            padsRoot = Child(visuals, "Padding");

            Material metal = MetalMaterial(), railMaterial = RailMaterial(metal), webbing = WebbingMaterial(metal), padding = PaddingMaterial(metal);

            // rails: pairs Rail_<n>_A / _B
            rails.Clear();
            foreach ((string name, Vector3 local) in DefaultRails) Anchor(name, local, Vector3.one);
            for (int n = 0; n < 16; n++)
            {
                Transform a = anchors.Find("Rail_" + n + "_A"), b = anchors.Find("Rail_" + n + "_B");
                if (a == null || b == null) continue;
                rails.Add((a.localPosition, b.localPosition));
                Transform r = Child(railsRoot, "Rail_" + n);
                Vector3 mid = (a.localPosition + b.localPosition) * 0.5f;
                Vector3 along = b.localPosition - a.localPosition;
                r.localPosition = mid + Vector3.up * (RailHeight * 0.5f);
                r.localRotation = along.sqrMagnitude > 1e-6f ? Quaternion.LookRotation(along.normalized, Vector3.up) : Quaternion.identity;
                r.localScale = Vector3.one;
                Show(r, BoxMesh(new Vector3(RailWidth, RailHeight, along.magnitude), 0.1f), railMaterial);
            }

            // D-rings + belts
            for (int i = 0; i < MaxCapacity; i++)
            {
                ringParks[i] = Anchor("Ring_" + i, DefaultRings[i], Vector3.one);
                rings[i] = Child(ringsRoot, "Ring_" + i);
                Show(rings[i], RingMesh(), railMaterial);
                belts[i] = new Transform[BeltPieces];
                for (int k = 0; k < BeltPieces; k++)
                {
                    belts[i][k] = Child(beltsRoot, "Belt_" + i + "_" + k);
                    Show(belts[i][k], BeltMesh(), webbing);
                    belts[i][k].gameObject.SetActive(false);
                }
                buckles[i] = Child(beltsRoot, "Buckle_" + i);
                Show(buckles[i], BuckleMesh(), railMaterial);
                cups[i] = Child(beltsRoot, "Cup_" + i);
                Show(cups[i], CupMesh(), metal);
                buckles[i].gameObject.SetActive(false);
                cups[i].gameObject.SetActive(false);
                posedFrame[i] = -1;
                Park(i);
            }

            // padded panels (the door ones ride on their doors)
            pendingDoorPads.Clear();
            foreach ((string name, Vector3 min, Vector3 max) in DefaultPads)
            {
                Transform anchor = Anchor(name, (min + max) * 0.5f, max - min);
                if (name == "Pad_RearLeft" || name == "Pad_RearRight") { pendingDoorPads.Add(name); continue; }
                Transform p = Child(padsRoot, name);
                p.localPosition = anchor.localPosition;
                p.localRotation = anchor.localRotation;
                p.localScale = Vector3.one;
                Show(p, BoxMesh(Abs(anchor.localScale), QuiltTile), padding);
            }
            // anchors added by a newer model beyond the defaults (Pad_* not in the table)
            foreach (Transform anchor in anchors)
            {
                if (!anchor.name.StartsWith("Pad_") || padsRoot.Find(anchor.name) != null || pendingDoorPads.Contains(anchor.name)) continue;
                Transform p = Child(padsRoot, anchor.name);
                p.localPosition = anchor.localPosition;
                p.localRotation = anchor.localRotation;
                Show(p, BoxMesh(Abs(anchor.localScale), QuiltTile), padding);
            }
            built = true;
        }

        private void Refresh()
        {
            if (railsRoot == null) return;
            railsRoot.gameObject.SetActive(restraints);
            ringsRoot.gameObject.SetActive(restraints);
            beltsRoot.gameObject.SetActive(restraints);
            for (int i = 0; i < MaxCapacity; i++)
                if (rings[i] != null) rings[i].gameObject.SetActive(i < capacity);
            padsRoot.gameObject.SetActive(padded);
            if (padded) BuildDoorPads();
            foreach (GameObject g in doorPads) if (g != null) g.SetActive(padded);
        }

        // Door panels: placed in van space while the door is shut, then parented to the door (they swing with it).
        private void BuildDoorPads()
        {
            for (int k = pendingDoorPads.Count - 1; k >= 0; k--)
            {
                string name = pendingDoorPads[k];
                VanDoor door = FindDoor(name == "Pad_RearLeft" ? RearLeftDoor : RearRightDoor);
                Transform anchor = anchors != null ? anchors.Find(name) : null;
                if (anchor == null) { pendingDoorPads.RemoveAt(k); continue; }
                if (door != null && door.Openness > 0.001f) continue; // wait until it is shut
                Transform parent = door != null ? door.transform : padsRoot;
                Transform p = parent.Find(name);
                if (p == null)
                {
                    p = new GameObject(name).transform;
                    p.SetParent(parent, false);
                }
                p.SetPositionAndRotation(anchors.TransformPoint(anchor.localPosition), anchors.rotation * anchor.localRotation);
                Vector3 ls = parent.lossyScale;
                p.localScale = new Vector3(ls.x != 0f ? 1f / ls.x : 1f, ls.y != 0f ? 1f / ls.y : 1f, ls.z != 0f ? 1f / ls.z : 1f);
                Show(p, BoxMesh(Abs(anchor.localScale), QuiltTile), PaddingMaterial(MetalMaterial()));
                p.gameObject.SetActive(padded);
                if (!doorPads.Contains(p.gameObject)) doorPads.Add(p.gameObject);
                pendingDoorPads.RemoveAt(k);
            }
        }

        private void Park(int slot)
        {
            Transform ring = rings[slot];
            if (ring == null || ringParks[slot] == null) return;
            Vector3 at = ringParks[slot].localPosition + Vector3.up * RailHeight;
            ring.localPosition = at;
            ring.localRotation = RailRotation(at);
        }

        // Along the nearest rail (the loop stands across it).
        private Quaternion RailRotation(Vector3 local)
        {
            Vector3 along = Vector3.forward;
            float bestD = float.MaxValue;
            foreach ((Vector3 a, Vector3 b) in rails)
            {
                Vector3 ab = b - a;
                if (ab.sqrMagnitude < 1e-6f) continue;
                float t = Mathf.Clamp01(Vector3.Dot(local - a, ab) / ab.sqrMagnitude);
                float d = (a + ab * t - local).sqrMagnitude;
                if (d < bestD) { bestD = d; along = ab.normalized; }
            }
            return Quaternion.LookRotation(along, Vector3.up);
        }

        private VanDoor FindDoor(string doorName)
        {
            foreach (VanDoor d in GetComponentsInChildren<VanDoor>(true)) if (d.name == doorName) return d;
            return null;
        }

        private Transform Anchor(string name, Vector3 local, Vector3 scale)
        {
            Transform t = anchors.Find(name);
            if (t != null) return t;
            t = new GameObject(name).transform;
            t.SetParent(anchors, false);
            t.localPosition = local;
            t.localRotation = Quaternion.identity;
            t.localScale = scale;
            return t;
        }

        private static Transform Child(Transform parent, string name)
        {
            Transform t = parent.Find(name);
            if (t != null) return t;
            t = new GameObject(name).transform;
            t.SetParent(parent, false);
            return t;
        }

        private static void Show(Transform t, Mesh mesh, Material material)
        {
            if (!t.TryGetComponent(out MeshFilter f)) f = t.gameObject.AddComponent<MeshFilter>();
            f.sharedMesh = mesh;
            if (!t.TryGetComponent(out MeshRenderer r)) r = t.gameObject.AddComponent<MeshRenderer>();
            r.sharedMaterial = material;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
        }

        private static Vector3 Abs(Vector3 v) => new(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));

        // ------------------------------------------------------------------ materials

        private Material MetalMaterial()
        {
            if (_metal != null) return _metal;
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
                foreach (Material m in r.sharedMaterials)
                    if (m != null && m.name == TrimMaterial) return _metal = m;
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            _metal = new Material(lit != null ? lit : Shader.Find("Standard")) { name = "VAN_CargoFit_Metal (runtime)" };
            Tint(_metal, new Color(0.24f, 0.25f, 0.26f), 0.2f, 0.3f);
            return _metal;
        }

        private static Material RailMaterial(Material metal)
        {
            if (_rail != null) return _rail;
            _rail = new Material(metal) { name = "VAN_CargoFit_Rail (runtime)" };
            Tint(_rail, new Color(0.66f, 0.68f, 0.70f), 0.3f, 0.5f);
            return _rail;
        }

        private static Material WebbingMaterial(Material metal)
        {
            if (_webbing != null) return _webbing;
            _webbing = new Material(metal) { name = "VAN_CargoFit_Webbing (runtime)" };
            Tint(_webbing, new Color(0.88f, 0.50f, 0.10f), 0f, 0.2f);
            return _webbing;
        }

        private static Material PaddingMaterial(Material metal)
        {
            if (_padding != null) return _padding;
            _padding = new Material(metal) { name = "VAN_CargoFit_Padding (runtime)" };
            Tint(_padding, new Color(0.36f, 0.42f, 0.55f), 0f, 0.08f);
            Texture2D quilt = QuiltTexture();
            if (_padding.HasProperty("_BaseMap")) _padding.SetTexture("_BaseMap", quilt);
            _padding.mainTexture = quilt;
            return _padding;
        }

        private static void Tint(Material m, Color c, float metallic, float smoothness)
        {
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", metallic);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smoothness);
            if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", null);
        }

        // One quilted diamond per tile: puffy cushion, darker stitched seams (a moving blanket).
        private static Texture2D QuiltTexture()
        {
            if (_quilt != null) return _quilt;
            const int n = 128;
            _quilt = new Texture2D(n, n, TextureFormat.RGBA32, true) { name = "VAN_CargoFit_Quilt (runtime)", wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Trilinear, anisoLevel = 4 };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float u = (x + 0.5f) / n, v = (y + 0.5f) / n;
                    float a = Mathf.Repeat(u + v, 1f), b = Mathf.Repeat(u - v, 1f);
                    float edge = Mathf.Min(Mathf.Min(a, 1f - a), Mathf.Min(b, 1f - b)); // 0 on a seam, 0.5 in the middle
                    float puff = Mathf.Sqrt(Mathf.Clamp01(edge / 0.25f));
                    float k = 0.62f + 0.38f * puff;
                    if (edge < 0.018f) k = 0.42f;
                    // stitch dashes along the seams
                    if (edge < 0.035f && edge >= 0.018f && Mathf.Repeat((a + b) * 10f, 1f) < 0.5f) k = 0.55f;
                    byte g = (byte)Mathf.RoundToInt(255f * Mathf.Clamp01(k));
                    px[y * n + x] = new Color32(g, g, g, 255);
                }
            _quilt.SetPixels32(px);
            _quilt.Apply(true, false);
            return _quilt;
        }

        // ------------------------------------------------------------------ meshes

        // A box centred on the origin with UVs in metres / tile (no stretching on long panels).
        private static Mesh BoxMesh(Vector3 size, float tile)
        {
            Vector3 h = size * 0.5f;
            var v = new List<Vector3>(24);
            var nrm = new List<Vector3>(24);
            var uv = new List<Vector2>(24);
            var tri = new List<int>(36);
            void Face(Vector3 n, Vector3 u, Vector3 w, float su, float sw)
            {
                int i = v.Count;
                Vector3 c = Vector3.Scale(n, h);
                Vector3 du = Vector3.Scale(u, h), dw = Vector3.Scale(w, h);
                v.Add(c - du - dw); v.Add(c + du - dw); v.Add(c + du + dw); v.Add(c - du + dw);
                for (int k = 0; k < 4; k++) nrm.Add(n);
                float tu = su / tile, tw = sw / tile;
                uv.Add(new Vector2(0f, 0f)); uv.Add(new Vector2(tu, 0f)); uv.Add(new Vector2(tu, tw)); uv.Add(new Vector2(0f, tw));
                tri.Add(i); tri.Add(i + 2); tri.Add(i + 1);
                tri.Add(i); tri.Add(i + 3); tri.Add(i + 2);
            }
            Face(Vector3.right, Vector3.forward, Vector3.up, size.z, size.y);
            Face(Vector3.left, Vector3.back, Vector3.up, size.z, size.y);
            Face(Vector3.up, Vector3.right, Vector3.forward, size.x, size.z);
            Face(Vector3.down, Vector3.right, Vector3.back, size.x, size.z);
            Face(Vector3.forward, Vector3.left, Vector3.up, size.x, size.y);
            Face(Vector3.back, Vector3.right, Vector3.up, size.x, size.y);
            var mesh = new Mesh { name = "VAN_CargoFit_Box" };
            mesh.SetVertices(v);
            mesh.SetNormals(nrm);
            mesh.SetUVs(0, uv);
            mesh.SetTriangles(tri, 0);
            mesh.RecalculateBounds();
            mesh.RecalculateTangents();
            return mesh;
        }

        // Unit-length strap along +Z (scaled to the belt's length).
        private static Mesh BeltMesh()
        {
            if (_beltMesh != null) return _beltMesh;
            Mesh m = BoxMesh(new Vector3(BeltWidth, BeltThickness, 1f), 1f);
            var verts = new List<Vector3>();
            m.GetVertices(verts);
            for (int i = 0; i < verts.Count; i++) verts[i] += new Vector3(0f, 0f, 0.5f);
            m.SetVertices(verts);
            m.RecalculateBounds();
            m.name = "VAN_CargoFit_Belt";
            return _beltMesh = m;
        }

        // The floor cup the far end of a lap belt hooks into.
        private static Mesh CupMesh()
        {
            if (_cupMesh != null) return _cupMesh;
            Mesh m = BoxMesh(new Vector3(0.07f, 0.012f, 0.05f), 1f);
            var verts = new List<Vector3>();
            m.GetVertices(verts);
            for (int i = 0; i < verts.Count; i++) verts[i] += new Vector3(0f, 0.006f, 0f);
            m.SetVertices(verts);
            m.RecalculateBounds();
            m.name = "VAN_CargoFit_Cup";
            return _cupMesh = m;
        }

        private static Mesh BuckleMesh()
        {
            if (_buckleMesh != null) return _buckleMesh;
            Mesh m = BoxMesh(new Vector3(0.065f, 0.018f, 0.05f), 1f);
            m.name = "VAN_CargoFit_Buckle";
            return _buckleMesh = m;
        }

        // A D-ring on its rail fitting: a base plate along the rail (+Z) and a half loop standing up across it.
        private static Mesh RingMesh()
        {
            if (_ringMesh != null) return _ringMesh;
            var v = new List<Vector3>();
            var tri = new List<int>();
            // base plate 0.07 x 0.008 x 0.045
            Mesh plate = BoxMesh(new Vector3(0.045f, 0.008f, 0.07f), 1f);
            var pv = new List<Vector3>();
            plate.GetVertices(pv);
            int[] pt = plate.triangles;
            foreach (Vector3 p in pv) v.Add(p + new Vector3(0f, 0.004f, 0f));
            tri.AddRange(pt);
            // half torus: radius 0.03 in the X-Y plane (across the rail), tube 0.0055, 8 x 6
            const int seg = 8, sides = 6;
            const float R = 0.035f, r = 0.0065f;
            int start = v.Count;
            for (int i = 0; i <= seg; i++)
            {
                float a = Mathf.PI * i / seg;
                var c = new Vector3(Mathf.Cos(a) * R, 0.008f + Mathf.Sin(a) * R, 0f);
                Vector3 outward = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f);
                for (int j = 0; j < sides; j++)
                {
                    float b = Mathf.PI * 2f * j / sides;
                    v.Add(c + (outward * Mathf.Cos(b) + Vector3.forward * Mathf.Sin(b)) * r);
                }
            }
            for (int i = 0; i < seg; i++)
                for (int j = 0; j < sides; j++)
                {
                    int a0 = start + i * sides + j, a1 = start + i * sides + (j + 1) % sides;
                    int b0 = a0 + sides, b1 = a1 + sides;
                    tri.Add(a0); tri.Add(b0); tri.Add(a1);
                    tri.Add(a1); tri.Add(b0); tri.Add(b1);
                }
            var mesh = new Mesh { name = "VAN_CargoFit_DRing" };
            mesh.SetVertices(v);
            mesh.SetTriangles(tri, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return _ringMesh = mesh;
        }
    }
}
