using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // v17 phase A street and yard dressing from the look json "v17" props (map_plan_v17.py places them, so the crowd,
    // police and colliders see the same things): registry prefabs (read only, LOD0 meshes) and a few procedural kinds
    // (clock column, laundry poles, dumpster pad walls, lattice pylons with wires). Merged per cell, material and
    // category under a one-level LODGroup that culls small props at ~70 m, cars at ~120 m and the rest at the fog end;
    // small props cast no shadows. Colliders: one box per solid prop (prefab bounds), boxes for the procedural parts.
    public static class V3Props17
    {
        private const float SmallCell = 24f, CarCell = 40f, BigCell = 80f;
        private const float SmallCull = 70f, CarCull = 120f, BigCull = 400f;

        private sealed class Part
        {
            public Mesh Mesh;
            public int Sub;
            public Material Mat;
            public Matrix4x4 Local;
        }

        private sealed class Cached
        {
            public List<Part> Parts = new();
            public Bounds Bounds;
            public Vector3 Scale = Vector3.one;
        }

        private sealed class Group
        {
            public string Name;
            public float Cull, Cell;
            public bool Cast;
            public Vector3 Centre;
            public readonly Dictionary<Material, List<CombineInstance>> Merge = new();
            public readonly V3Mesh Proc = new();
        }

        private static readonly HashSet<string> Small = new()
        {
            "prop/lamp_oldtown_single", "prop/lamp_oldtown_double", "prop/lamp_soviet", "prop/lamp_soviet_broken", "prop/bin", "prop/fire_hydrant",
            "prop/sign_stop", "prop/sign_giveway", "prop/bus_stop_sign", "prop/bench_park", "prop/bench_soviet", "prop/bench_soviet_broken",
            "prop/trashbin_concrete", "prop/carpet_rack", "prop/garbage_container_closed", "prop/garbage_container_open", "prop/play_swings",
            "prop/play_slide", "prop/play_sandbox", "prop/play_carousel", "prop/play_horizontal_bar", "prop/play_carpet_rack", "proc/laundry_poles",
        };

        public static void Build(LookData d, HeightModel hm, MapLookRegistry registry, V3Store store, Transform parent, List<string> log)
        {
            if (V3LookData.Props == null || V3LookData.Props.Count == 0) return;
            var root = new GameObject("Props_v17").transform;
            root.SetParent(parent, false);
            var colRoot = new GameObject("Props_v17_Colliders").transform;
            colRoot.SetParent(root, false);
            var groups = new Dictionary<string, Group>();
            var cache = new Dictionary<string, Cached>();
            int placed = 0, missing = 0, colliders = 0;
            var missingKeys = new HashSet<string>();
            var pylons = new List<Vector3>();
            foreach (V3LookData.Prop p in V3LookData.Props)
            {
                bool car = p.Key.Contains("car_") || p.Key.Contains("van_");
                bool small = Small.Contains(p.Key);
                string cat = small ? "small" : car ? "car" : "big";
                float cell = small ? SmallCell : car ? CarCell : BigCell;
                bool cast = p.Cast && !small;
                int cx = Mathf.FloorToInt(p.X / cell), cz = Mathf.FloorToInt(p.Y / cell);
                string gk = $"{cat}_{cx}_{cz}_{(cast ? 1 : 0)}";
                if (!groups.TryGetValue(gk, out Group g))
                    groups[gk] = g = new Group
                    {
                        Name = $"Props17_{cat}_{cx}_{cz}{(cast ? "" : "_ns")}",
                        Cull = small ? SmallCull : car ? CarCull : BigCull,
                        Cell = cell,
                        Cast = cast,
                        Centre = new Vector3((cx + 0.5f) * cell, 0f, (cz + 0.5f) * cell),
                    };
                float y = hm.Height(p.X, p.Y);
                var pos = new Vector3(p.X, y, p.Y);
                Quaternion rot = Quaternion.Euler(0f, p.Yaw, 0f);
                if (p.Key.StartsWith("proc/"))
                {
                    colliders += Procedural(p, pos, rot, g, registry, cache, colRoot);
                    if (p.Key == "proc/pylon") pylons.Add(pos);
                    placed++;
                    continue;
                }
                Cached c = Get(registry, p.Key, cache);
                if (c == null)
                {
                    missing++;
                    missingKeys.Add(p.Key);
                    continue;
                }
                Matrix4x4 world = Matrix4x4.TRS(pos, rot, c.Scale * p.Scale);
                foreach (Part part in c.Parts)
                {
                    if (!g.Merge.TryGetValue(part.Mat, out var list)) g.Merge[part.Mat] = list = new List<CombineInstance>();
                    list.Add(new CombineInstance { mesh = part.Mesh, subMeshIndex = part.Sub, transform = world * part.Local });
                }
                if (p.Solid && c.Bounds.size.sqrMagnitude > 0.01f)
                {
                    Vector3 size = Vector3.Scale(c.Bounds.size, c.Scale * p.Scale);
                    Vector3 centre = Vector3.Scale(c.Bounds.center, c.Scale * p.Scale);
                    colliders += Box(colRoot, pos + rot * centre, new Vector3(Mathf.Max(0.2f, size.x), Mathf.Max(0.3f, size.y), Mathf.Max(0.2f, size.z)), rot);
                }
                placed++;
            }
            Wires(pylons, groups);
            int objects = 0, subs = 0;
            var keys = new List<string>(groups.Keys);
            keys.Sort(string.CompareOrdinal);
            foreach (string k in keys) objects += Emit(groups[k], root, store, ref subs);
            log.Add($"props v17: {placed} placed ({missing} missing: {string.Join(", ", missingKeys)}), {objects} merged cell objects, {subs} submeshes, {colliders} box colliders");
        }

        private static Cached Get(MapLookRegistry registry, string key, Dictionary<string, Cached> cache)
        {
            if (cache.TryGetValue(key, out Cached c)) return c;
            PrefabSlot slot = registry.ExactPrefabSlot(key);
            if (slot == null || slot.prefab == null)
            {
                cache[key] = null;
                return null;
            }
            c = new Cached { Scale = slot.scale };
            GameObject prefab = slot.prefab;
            Matrix4x4 toRoot = prefab.transform.worldToLocalMatrix;
            var renderers = new List<Renderer>();
            LODGroup lg = prefab.GetComponentInChildren<LODGroup>();
            if (lg != null && lg.GetLODs().Length > 0) renderers.AddRange(lg.GetLODs()[0].renderers);
            else renderers.AddRange(prefab.GetComponentsInChildren<MeshRenderer>());
            bool first = true;
            foreach (Renderer r in renderers)
            {
                if (!(r is MeshRenderer mr)) continue;
                var mf = mr.GetComponent<MeshFilter>();
                if (mf == null || mf.sharedMesh == null) continue;
                Matrix4x4 local = toRoot * mf.transform.localToWorldMatrix;
                Material[] mats = mr.sharedMaterials;
                for (int i = 0; i < mf.sharedMesh.subMeshCount && i < mats.Length; i++)
                    if (mats[i] != null) c.Parts.Add(new Part { Mesh = mf.sharedMesh, Sub = i, Mat = mats[i], Local = local });
                Bounds mb = mf.sharedMesh.bounds;
                for (int k = 0; k < 8; k++)
                {
                    Vector3 corner = mb.center + Vector3.Scale(mb.extents, new Vector3((k & 1) == 0 ? -1 : 1, (k & 2) == 0 ? -1 : 1, (k & 4) == 0 ? -1 : 1));
                    Vector3 q = local.MultiplyPoint3x4(corner);
                    if (first) { c.Bounds = new Bounds(q, Vector3.zero); first = false; }
                    else c.Bounds.Encapsulate(q);
                }
            }
            cache[key] = c.Parts.Count > 0 ? c : null;
            return cache[key];
        }

        private static int Procedural(V3LookData.Prop p, Vector3 pos, Quaternion rot, Group g, MapLookRegistry registry, Dictionary<string, Cached> cache, Transform colRoot)
        {
            V3Mesh m = g.Proc;
            Vector3 X = rot * Vector3.right, Z = rot * Vector3.forward;
            switch (p.Key)
            {
                case "proc/clock_column":
                {
                    m.Box("3c_concrete_panels", pos + Vector3.up * 0.25f, new Vector3(1.7f, 0.5f, 1.7f), rot, V3Palette.C("paving.dark"));
                    m.Box("3b_plaster_stucco", pos + Vector3.up * 2.6f, new Vector3(0.9f, 4.2f, 0.9f), rot, V3Palette.C("chalk"));
                    m.Box("3c_concrete_panels", pos + Vector3.up * 4.8f, new Vector3(1.2f, 0.2f, 1.2f), rot, V3Palette.C("grey.light"));
                    Cached top = Get(registry, "prop/clock_tower_top", cache);
                    if (top != null)
                    {
                        Matrix4x4 w = Matrix4x4.TRS(pos + Vector3.up * 4.9f, rot, top.Scale * 0.5f);
                        foreach (Part part in top.Parts)
                        {
                            if (!g.Merge.TryGetValue(part.Mat, out var list)) g.Merge[part.Mat] = list = new List<CombineInstance>();
                            list.Add(new CombineInstance { mesh = part.Mesh, subMeshIndex = part.Sub, transform = w * part.Local });
                        }
                    }
                    else m.Box("6a_painted_metal_panels", pos + Vector3.up * 5.6f, new Vector3(1.1f, 1.2f, 1.1f), rot, V3Palette.C("ink"));
                    return Box(colRoot, pos + Vector3.up * 2.6f, new Vector3(1.7f, 5.2f, 1.7f), rot);
                }
                case "proc/laundry_poles":
                {
                    Color metal = V3Palette.C("grey.dark");
                    for (int s = -1; s <= 1; s += 2)
                    {
                        Vector3 b = pos + Z * (3f * s);
                        m.Box("6b_lightly_weathered_metal", b + Vector3.up * 1.15f, new Vector3(0.08f, 2.3f, 0.08f), rot, metal);
                        m.Box("6b_lightly_weathered_metal", b + Vector3.up * 2.25f, new Vector3(1.5f, 0.07f, 0.07f), rot, metal);
                    }
                    for (int k = 0; k < 4; k++)
                    {
                        float off = -0.6f + k * 0.4f;
                        m.Box("6b_lightly_weathered_metal", pos + X * off + Vector3.up * 2.2f, new Vector3(0.02f, 0.02f, 6f), rot, V3Palette.C("chalk"));
                    }
                    // A few hanging sheets (bright accents in a muted yard).
                    string[] cols = { "red", "cobalt", "chalk", "mustard" };
                    for (int k = 0; k < 3; k++)
                        m.Box("5a_wood_planks_fences", pos + X * (-0.2f + k * 0.4f) + Z * (-1.6f + k * 1.4f) + Vector3.up * 1.75f, new Vector3(0.02f, 0.9f, 1.1f), rot, V3Palette.C(cols[(Mathf.Abs((int)p.X) + k) % cols.Length]));
                    return 0;
                }
                case "proc/dumpster_pad":
                {
                    Color conc = V3Palette.C("grey.light");
                    m.Box("3c_concrete_panels", pos + Vector3.up * 0.06f, new Vector3(2.8f, 0.12f, 5.6f), rot * Quaternion.Euler(0f, 90f, 0f) * Quaternion.Euler(0f, -90f, 0f), conc);
                    m.Box("3c_concrete_panels", pos - X * 1.35f + Vector3.up * 0.7f, new Vector3(0.15f, 1.4f, 5.6f), rot, conc);
                    m.Box("3c_concrete_panels", pos + Z * 2.75f + Vector3.up * 0.7f, new Vector3(2.8f, 1.4f, 0.15f), rot, conc);
                    m.Box("3c_concrete_panels", pos - Z * 2.75f + Vector3.up * 0.7f, new Vector3(2.8f, 1.4f, 0.15f), rot, conc);
                    int n = Box(colRoot, pos - X * 1.35f + Vector3.up * 0.7f, new Vector3(0.2f, 1.4f, 5.6f), rot);
                    n += Box(colRoot, pos + Z * 2.75f + Vector3.up * 0.7f, new Vector3(2.8f, 1.4f, 0.2f), rot);
                    n += Box(colRoot, pos - Z * 2.75f + Vector3.up * 0.7f, new Vector3(2.8f, 1.4f, 0.2f), rot);
                    // The containers themselves (registry props, not solid in the data): one box for the three.
                    n += Box(colRoot, pos + X * 0.2f + Vector3.up * 0.7f, new Vector3(1.6f, 1.4f, 5.0f), rot);
                    return n;
                }
                case "proc/pylon":
                {
                    Color steel = V3Palette.C("grey");
                    const float H = 22f;
                    for (int sx = -1; sx <= 1; sx += 2)
                        for (int sz = -1; sz <= 1; sz += 2)
                        {
                            Vector3 a = pos + X * (2.4f * sx) + Z * (2.4f * sz);
                            Vector3 b = pos + X * (0.55f * sx) + Z * (0.55f * sz) + Vector3.up * H;
                            Strut(m, a, b, 0.22f, steel);
                        }
                    for (int lvl = 0; lvl < 4; lvl++)
                    {
                        float y0 = lvl * 5f, y1 = y0 + 5f;
                        float w0 = Mathf.Lerp(2.4f, 0.55f, y0 / H), w1 = Mathf.Lerp(2.4f, 0.55f, y1 / H);
                        for (int side = 0; side < 4; side++)
                        {
                            Vector3 dA = side switch { 0 => X, 1 => Z, 2 => -X, _ => -Z };
                            Vector3 dB = side switch { 0 => Z, 1 => -X, 2 => -Z, _ => X };
                            Strut(m, pos + dA * w0 + dB * w0 + Vector3.up * y0, pos + dA * w1 - dB * w1 + Vector3.up * y1, 0.09f, steel);
                        }
                    }
                    foreach (float yArm in new[] { 16f, 20f })
                    {
                        float half = yArm < 18f ? 5f : 3.8f;
                        m.Box("6b_lightly_weathered_metal", pos + Vector3.up * yArm, new Vector3(half * 2f, 0.35f, 0.4f), rot, steel);
                        for (int s = -1; s <= 1; s += 2)
                            m.Box("6a_painted_metal_panels", pos + X * (half * s * 0.95f) + Vector3.up * (yArm - 0.7f), new Vector3(0.18f, 1.1f, 0.18f), rot, V3Palette.C("chalk"));
                    }
                    return Box(colRoot, pos + Vector3.up * 3f, new Vector3(5f, 6f, 5f), rot);
                }
            }
            return 0;
        }

        private static void Strut(V3Mesh m, Vector3 a, Vector3 b, float w, Color c)
        {
            Vector3 d = b - a;
            float len = d.magnitude;
            if (len < 0.01f) return;
            m.Box("6b_lightly_weathered_metal", (a + b) / 2f, new Vector3(w, w, len), Quaternion.LookRotation(d / len, Mathf.Abs(d.y / len) > 0.95f ? Vector3.forward : Vector3.up), c);
        }

        // Three sagging wires between consecutive pylons (tips of the lower and upper arms), drawn in the pylon groups.
        private static void Wires(List<Vector3> pylons, Dictionary<string, Group> groups)
        {
            for (int i = 0; i + 1 < pylons.Count; i++)
            {
                Vector3 a = pylons[i], b = pylons[i + 1];
                if (Vector3.Distance(a, b) > 90f) continue;
                Vector3 dir = (b - a);
                dir.y = 0f;
                Vector3 side = Vector3.Cross(Vector3.up, dir.normalized);
                string gk = null;
                foreach (var kv in groups)
                    if (kv.Key.StartsWith("big_") && Vector3.Distance(new Vector3(kv.Value.Centre.x, 0f, kv.Value.Centre.z), new Vector3(a.x, 0f, a.z)) < BigCell) { gk = kv.Key; break; }
                if (gk == null) continue;
                V3Mesh m = groups[gk].Proc;
                foreach (var (off, y) in new[] { (-5f * 0.95f, 15.3f), (5f * 0.95f, 15.3f), (0f, 19.3f) })
                {
                    Vector3 p0 = a + side * off + Vector3.up * y, p3 = b + side * off + Vector3.up * y;
                    const int segs = 6;
                    Vector3 prev = p0;
                    for (int k = 1; k <= segs; k++)
                    {
                        float t = (float)k / segs;
                        Vector3 q = Vector3.Lerp(p0, p3, t) + Vector3.down * (4f * 1.6f * t * (1f - t));
                        Strut(m, prev, q, 0.035f, V3Palette.C("ink"));
                        prev = q;
                    }
                }
            }
        }

        private static int Box(Transform root, Vector3 centre, Vector3 size, Quaternion rot)
        {
            var go = new GameObject("Collider");
            go.transform.SetParent(root, false);
            go.transform.SetPositionAndRotation(centre, rot);
            go.AddComponent<BoxCollider>().size = size;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            return 1;
        }

        private static int Emit(Group g, Transform root, V3Store store, ref int subs)
        {
            var renderers = new List<Renderer>();
            if (g.Merge.Count > 0)
            {
                var parts = new List<CombineInstance>();
                var mats = new List<Material>();
                foreach (var kv in g.Merge)
                {
                    var part = new Mesh { indexFormat = IndexFormat.UInt32 };
                    part.CombineMeshes(kv.Value.ToArray(), true, true);
                    parts.Add(new CombineInstance { mesh = part, transform = Matrix4x4.identity });
                    mats.Add(kv.Key);
                }
                var mesh = new Mesh { name = g.Name, indexFormat = IndexFormat.UInt32 };
                mesh.CombineMeshes(parts.ToArray(), false, true);
                foreach (CombineInstance p in parts) Object.DestroyImmediate(p.mesh);
                mesh.RecalculateBounds();
                renderers.Add(Renderer(root, g.Name, store.AddMesh(mesh), mats.ToArray(), g.Cast));
                subs += mats.Count;
            }
            if (!g.Proc.IsEmpty)
            {
                Mesh pm = store.AddMesh(g.Proc.ToMesh(g.Name + "_proc", out string[] cats));
                renderers.Add(Renderer(root, g.Name + "_proc", pm, V3Ground.Mats(cats), g.Cast));
                subs += cats.Length;
            }
            if (renderers.Count == 0) return 0;
            // One LOD culled by screen height: transition = size * lodBias / (2 tan(fov/2) * cull distance), design fov 60.
            var lodGo = new GameObject(g.Name + "_LOD");
            lodGo.transform.SetParent(root, false);
            lodGo.transform.position = g.Centre;
            foreach (Renderer r in renderers) r.transform.SetParent(lodGo.transform, true);
            var lg = lodGo.AddComponent<LODGroup>();
            float size = g.Cell * 1.2f;
            float h = Mathf.Clamp(size * Mathf.Max(0.5f, QualitySettings.lodBias) / (2f * Mathf.Tan(30f * Mathf.Deg2Rad) * g.Cull), 0.002f, 0.95f);
            lg.SetLODs(new[] { new LOD(h, renderers.ToArray()) });
            lg.size = size;
            lg.localReferencePoint = Vector3.zero;
            return renderers.Count;
        }

        private static Renderer Renderer(Transform root, string name, Mesh mesh, Material[] mats, bool cast)
        {
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = mats;
            mr.shadowCastingMode = cast ? ShadowCastingMode.On : ShadowCastingMode.Off;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic |
                (V3Mesh.StaticBatchSafe(mesh) ? StaticEditorFlags.BatchingStatic : 0));
            return mr;
        }
    }
}
