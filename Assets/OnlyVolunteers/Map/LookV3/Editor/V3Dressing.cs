using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Plan structures the look json only names (world_v11_extensions.structures), dressed in style v3: Downtown park
    // lawns on the plaza with kerbs, round trees, benches and lamps; wooden and yacht piers; sun loungers and umbrellas;
    // haystacks; the village water tower. Registry prefabs are instantiated read-only and merged per material; procedural
    // parts are V3 meshes; colliders are boxes or convex prisms.
    public static class V3Dressing
    {
        // Park trees go into the terrain's tree instances, so they are added to the plan's trees before the terrain bakes.
        public static int AddParkTrees(LookData d)
        {
            if (V3LookData.Structures == null) return 0;
            var trees = new List<LookTree>(d.trees);
            int added = 0, k = 0;
            foreach (var s in V3LookData.Structures)
            {
                if (s.kind != "park_lawn" || s.poly == null || LookGeom.Count(s.poly) < 3) continue;
                float[] ring = LookGeom.OffsetPolygon(Ccw(s.poly), -2.2f);
                float[] cum = LookGeom.Cumulative(ring, true);
                float total = cum[cum.Length - 1];
                int n = Mathf.Max(2, Mathf.RoundToInt(total / 9f));
                for (int i = 0; i < n; i++)
                {
                    LookGeom.PointAt(ring, cum, total * i / n, true, out float x, out float y, out _, out _);
                    trees.Add(new LookTree { sp = (k++ % 3 == 0) ? "linden" : "oak", x = x, y = y, h = 7.5f + LookGeom.Hash01(k, 3, d.seed) * 2f });
                    added++;
                }
            }
            d.trees = trees.ToArray();
            return added;
        }

        public static float[] Ccw(float[] pts)
        {
            if (LookGeom.SignedArea(pts) >= 0f) return pts;
            int n = pts.Length / 2;
            var r = new float[pts.Length];
            for (int i = 0; i < n; i++)
            {
                r[2 * i] = pts[2 * (n - 1 - i)];
                r[2 * i + 1] = pts[2 * (n - 1 - i) + 1];
            }
            return r;
        }

        private const float Cell = 160f;
        private static Dictionary<string, V3Mesh> meshCells;
        private static Dictionary<string, Dictionary<Material, List<CombineInstance>>> propCells;

        private static string Key(Vector3 p) => Mathf.FloorToInt(p.x / Cell) + "_" + Mathf.FloorToInt(p.z / Cell);

        // Per 160 m cell, so the merged dressing is frustum-culled like the roads (one map-wide mesh would always draw).
        private static V3Mesh M(Vector3 p)
        {
            string k = Key(p);
            if (!meshCells.TryGetValue(k, out V3Mesh m)) meshCells[k] = m = new V3Mesh();
            return m;
        }

        private static Dictionary<Material, List<CombineInstance>> G(Vector3 p)
        {
            string k = Key(p);
            if (!propCells.TryGetValue(k, out var g)) propCells[k] = g = new Dictionary<Material, List<CombineInstance>>();
            return g;
        }

        public static void Build(LookData d, HeightModel hm, MapLookRegistry registry, V3Store store, Transform parent, List<string> log)
        {
            if (V3LookData.Structures == null) return;
            var root = new GameObject("Dressing").transform;
            root.SetParent(parent, false);
            meshCells = new Dictionary<string, V3Mesh>();
            propCells = new Dictionary<string, Dictionary<Material, List<CombineInstance>>>();
            int parks = 0, piers = 0, loungers = 0, stacks = 0;
            foreach (var s in V3LookData.Structures)
            {
                switch (s.kind)
                {
                    case "park_lawn":
                        if (s.poly != null) { Park(s.poly, hm, registry, root); parks++; }
                        break;
                    case "wooden_pier":
                    case "yacht_pier":
                        if (s.poly != null) { Pier(s.id, s.poly, d.sea.level, hm, root, store, s.kind == "yacht_pier"); piers++; }
                        break;
                    case "sun_lounger":
                        if (s.poly != null) { Loungers(s.id, s.poly, hm, registry, root, loungers); loungers++; }
                        break;
                    case "haystack":
                        Haystack(s.pos, Mathf.Max(1.5f, s.radius), hm, root);
                        stacks++;
                        break;
                    case "water_tower":
                        WaterTower(s.id, s.pos, Mathf.Max(3f, s.radius), hm, root);
                        break;
                }
            }
            int submeshes = 0;
            var keys = new List<string>(meshCells.Keys);
            keys.Sort(string.CompareOrdinal);
            foreach (string k in keys)
            {
                V3Mesh m = meshCells[k];
                if (m.IsEmpty) continue;
                var go = new GameObject("Dressing_Mesh_" + k);
                go.transform.SetParent(root, false);
                go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(m.ToMesh(go.name, out string[] cats));
                go.AddComponent<MeshRenderer>().sharedMaterials = V3Ground.Mats(cats);
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
                submeshes += cats.Length;
            }
            keys = new List<string>(propCells.Keys);
            keys.Sort(string.CompareOrdinal);
            foreach (string k in keys) submeshes += Emit(root, "Dressing_Props_" + k, propCells[k], store);
            meshCells = null;
            propCells = null;
            log.Add("dressing v3: " + parks + " park lawns, " + piers + " piers, " + loungers + " lounger rows, " + stacks + " haystacks; " + submeshes + " submeshes in 160 m cells");
        }

        private static void Place(MapLookRegistry registry, string key, Vector3 pos, Quaternion rot, Transform root, bool collider = true)
        {
            PrefabSlot slot = registry.ExactPrefabSlot(key);
            if (slot == null) return;
            Dictionary<Material, List<CombineInstance>> merge = G(pos);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, root);
            inst.transform.SetPositionAndRotation(pos, rot);
            inst.transform.localScale = slot.scale;
            foreach (MeshRenderer mr in inst.GetComponentsInChildren<MeshRenderer>())
            {
                var mf = mr.GetComponent<MeshFilter>();
                if (mf == null || mf.sharedMesh == null) continue;
                Material[] mats = mr.sharedMaterials;
                for (int i = 0; i < mf.sharedMesh.subMeshCount && i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    if (!merge.TryGetValue(mats[i], out var list)) merge[mats[i]] = list = new List<CombineInstance>();
                    list.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = i, transform = mf.transform.localToWorldMatrix });
                }
            }
            foreach (LODGroup lg in inst.GetComponentsInChildren<LODGroup>()) Object.DestroyImmediate(lg);
            foreach (MeshRenderer mr in inst.GetComponentsInChildren<MeshRenderer>())
            {
                MeshFilter mf = mr.GetComponent<MeshFilter>();
                Object.DestroyImmediate(mr);
                if (mf != null) Object.DestroyImmediate(mf);
            }
            if (!collider) foreach (Collider c in inst.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            foreach (Collider c in inst.GetComponentsInChildren<Collider>())
                if (c is MeshCollider mc && !mc.convex) mc.convex = true;
            if (inst.GetComponentInChildren<Collider>() == null) Object.DestroyImmediate(inst);
        }

        private static int Emit(Transform root, string name, Dictionary<Material, List<CombineInstance>> merge, V3Store store)
        {
            if (merge.Count == 0) return 0;
            var parts = new List<CombineInstance>();
            var mats = new List<Material>();
            foreach (var kv in merge)
            {
                var part = new Mesh { indexFormat = IndexFormat.UInt32 };
                part.CombineMeshes(kv.Value.ToArray(), true, true);
                parts.Add(new CombineInstance { mesh = part, transform = Matrix4x4.identity });
                mats.Add(kv.Key);
            }
            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.CombineMeshes(parts.ToArray(), false, true);
            foreach (CombineInstance p in parts) Object.DestroyImmediate(p.mesh);
            mesh.RecalculateBounds();
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(mesh);
            go.AddComponent<MeshRenderer>().sharedMaterials = mats.ToArray();
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            return mats.Count;
        }

        // A Downtown park on the plaza: lawn 6 cm above the paving, a chalk kerb, benches facing in, iron lamps at corners.
        private static void Park(float[] poly, HeightModel hm, MapLookRegistry registry, Transform root)
        {
            poly = Ccw(poly);
            LookGeom.Centroid(poly, out float cx, out float cy);
            float y = hm.Height(cx, cy) + RoadMeshBuilder.GroundLift + 0.06f;
            V3Mesh m = M(new Vector3(cx, 0f, cy));
            List<int> tris = MeshDraft.Triangulate(LookConvert.Poly(poly));
            Vector2[] p = LookConvert.Poly(poly);
            for (int i = 0; i + 2 < tris.Count; i += 3)
                m.TriFacing("1a_grass", new Vector3(p[tris[i]].x, y, p[tris[i]].y), new Vector3(p[tris[i + 1]].x, y, p[tris[i + 1]].y),
                    new Vector3(p[tris[i + 2]].x, y, p[tris[i + 2]].y), Vector3.up, V3Palette.C("lawn"));
            float[] outer = LookGeom.OffsetPolygon(poly, 0.25f);
            int n = p.Length;
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                var a = new Vector3(poly[2 * i], 0f, poly[2 * i + 1]);
                var b = new Vector3(poly[2 * j], 0f, poly[2 * j + 1]);
                var oa = new Vector3(outer[2 * i], 0f, outer[2 * i + 1]);
                var ob = new Vector3(outer[2 * j], 0f, outer[2 * j + 1]);
                float top = y + 0.08f, bot = y - 0.12f;
                m.QuadFacing("3c_concrete_panels", a + Vector3.up * top, oa + Vector3.up * top, ob + Vector3.up * top, b + Vector3.up * top, Vector3.up, V3Palette.C("chalk"));
                m.QuadFacing("3c_concrete_panels", oa + Vector3.up * bot, oa + Vector3.up * top, ob + Vector3.up * top, ob + Vector3.up * bot, oa - a + (ob - b), V3Palette.C("chalk"));
            }
            float[] ring = LookGeom.OffsetPolygon(poly, -1.0f);
            float[] cum = LookGeom.Cumulative(ring, true);
            float total = cum[cum.Length - 1];
            int benches = Mathf.Max(1, Mathf.RoundToInt(total / 14f));
            for (int i = 0; i < benches; i++)
            {
                LookGeom.PointAt(ring, cum, total * (i + 0.5f) / benches, true, out float x, out float z, out float tx, out float tz);
                var inward = new Vector3(-tz, 0f, tx);
                Place(registry, "prop/bench_park", new Vector3(x, y, z), Quaternion.LookRotation(inward), root);
            }
            for (int i = 0; i < n; i += Mathf.Max(1, n / 4))
                Place(registry, "prop/lamp_iron", new Vector3(outer[2 * i], y - 0.06f, outer[2 * i + 1]), Quaternion.identity, root);
        }

        // Timber pier on posts: deck 1.1 m over the sea, posts down to the bed, a low rail on the outer edges.
        private static void Pier(string id, float[] poly, float seaLevel, HeightModel hm, Transform root, V3Store store, bool concrete)
        {
            poly = Ccw(poly);
            Vector2[] p = LookConvert.Poly(poly);
            float deck = seaLevel + 1.1f;
            LookGeom.Centroid(poly, out float pcx, out float pcy);
            V3Mesh m = M(new Vector3(pcx, 0f, pcy));
            string cat = concrete ? "3c_concrete_panels" : "5a_wood_planks_fences";
            Color col = concrete ? V3Palette.C("paving") : V3Palette.C("wood.light");
            List<int> tris = MeshDraft.Triangulate(p);
            var colliderRoot = new GameObject("Pier_" + id);
            colliderRoot.transform.SetParent(root, false);
            for (int i = 0; i + 2 < tris.Count; i += 3)
            {
                Vector2 a = p[tris[i]], b = p[tris[i + 1]], c = p[tris[i + 2]];
                m.TriFacing(cat, new Vector3(a.x, deck, a.y), new Vector3(b.x, deck, b.y), new Vector3(c.x, deck, c.y), Vector3.up, col);
                m.TriFacing(cat, new Vector3(a.x, deck - 0.25f, a.y), new Vector3(b.x, deck - 0.25f, b.y), new Vector3(c.x, deck - 0.25f, c.y), Vector3.down, col * 0.85f);
                var draft = new MeshDraft();
                var tri = new[] { a, b, c };
                float area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
                if (area < 0f) System.Array.Reverse(tri);
                draft.Prism(draft.Slot("collision"), tri, deck - 0.25f, deck, true, true);
                var cgo = new GameObject("Collider");
                cgo.transform.SetParent(colliderRoot.transform, false);
                var mc = cgo.AddComponent<MeshCollider>();
                mc.sharedMesh = store.AddMesh(draft.ToMesh($"Pier_{id}_{i / 3}"));
                mc.convex = true;
            }
            int n = p.Length;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = p[i], b = p[(i + 1) % n];
                float len = Vector2.Distance(a, b);
                var A = new Vector3(a.x, 0f, a.y);
                var B = new Vector3(b.x, 0f, b.y);
                m.QuadFacing(cat, A + Vector3.up * (deck - 0.25f), A + Vector3.up * deck, B + Vector3.up * deck, B + Vector3.up * (deck - 0.25f),
                    new Vector3(b.y - a.y, 0f, a.x - b.x), col * 0.9f);
                int posts = Mathf.Max(1, Mathf.RoundToInt(len / 3f));
                for (int k = 0; k <= posts; k++)
                {
                    Vector2 q = Vector2.Lerp(a, b, (float)k / posts);
                    float bed = Mathf.Min(seaLevel - 0.5f, hm.Height(q.x, q.y));
                    m.Box("5a_wood_planks_fences", new Vector3(q.x, (bed + deck - 0.25f) / 2f, q.y), new Vector3(0.28f, deck - 0.25f - bed, 0.28f), Quaternion.identity, V3Palette.C("wood.dark"));
                    if (!concrete) m.Box("5a_wood_planks_fences", new Vector3(q.x, deck + 0.45f, q.y), new Vector3(0.12f, 0.9f, 0.12f), Quaternion.identity, V3Palette.C("wood"));
                }
                if (!concrete) m.Beam("5a_wood_planks_fences", A + Vector3.up * 0f, B, 0.1f, deck + 0.8f, deck + 0.9f, V3Palette.C("wood"));
            }
        }

        // A lounger row strip: two loungers facing along its long axis, an umbrella between them.
        private static void Loungers(string id, float[] poly, HeightModel hm, MapLookRegistry registry, Transform root, int k)
        {
            LookGeom.Centroid(poly, out float cx, out float cy);
            LookGeom.Bounds(poly, out float x0, out float y0, out float x1, out float y1);
            bool alongZ = y1 - y0 >= x1 - x0;
            Vector3 along = alongZ ? Vector3.forward : Vector3.right, across = alongZ ? Vector3.right : Vector3.forward;
            // Face the sea (south) where the strip runs north-south.
            Quaternion rot = Quaternion.LookRotation(alongZ ? Vector3.back : Vector3.right);
            var c = new Vector3(cx, hm.Height(cx, cy), cy);
            for (int s = -1; s <= 1; s += 2)
            {
                Vector3 p = c + across * (s * 0.55f);
                p.y = hm.Height(p.x, p.z);
                Place(registry, "prop/beach_sunlounger", p, rot, root);
            }
            Vector3 u = c + along * 1.6f;
            u.y = hm.Height(u.x, u.z) - 0.1f;
            Place(registry, k % 2 == 0 ? "prop/beach_umbrella_red" : "prop/beach_umbrella_teal", u, Quaternion.Euler(0f, k * 37f, 0f), root, false);
        }

        private static void Haystack(Vector2 p, float r, HeightModel hm, Transform root)
        {
            float y = hm.Height(p.x, p.y) - 0.1f;
            V3Mesh m = M(new Vector3(p.x, 0f, p.y));
            Color straw = V3Palette.C("field"), dark = V3Palette.C("field.dark");
            var c = new Vector3(p.x, y, p.y);
            m.Cylinder("1b_dirt_road", c, r * 0.8f, 1.6f, 10, straw, false);
            // Rounded top as two stacked cones.
            for (int s = 0; s < 10; s++)
            {
                float a0 = s * Mathf.PI * 2f / 10f, a1 = (s + 1) * Mathf.PI * 2f / 10f;
                Vector3 d0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)), d1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1));
                Vector3 b0 = c + d0 * r * 0.8f + Vector3.up * 1.6f, b1 = c + d1 * r * 0.8f + Vector3.up * 1.6f;
                Vector3 m0 = c + d0 * r * 0.5f + Vector3.up * 2.5f, m1 = c + d1 * r * 0.5f + Vector3.up * 2.5f;
                Vector3 top = c + Vector3.up * 3.0f;
                m.QuadFacing("1b_dirt_road", b0, m0, m1, b1, d0 + d1 + Vector3.up * 0.6f, straw);
                m.TriFacing("1b_dirt_road", m0, top, m1, d0 + d1 + Vector3.up * 1.5f, dark);
            }
            var go = new GameObject("Haystack_Collider");
            go.transform.SetParent(root, false);
            go.transform.position = c + Vector3.up * 1.4f;
            var cc = go.AddComponent<CapsuleCollider>();
            cc.radius = r * 0.75f;
            cc.height = 2.8f;
        }

        // The village landmark: brick shaft, steel tank with a railing, conical roof (the v12 generator's shape).
        private static void WaterTower(string id, Vector2 p, float r, HeightModel hm, Transform root)
        {
            float y = hm.Height(p.x, p.y);
            V3Mesh m = M(new Vector3(p.x, 0f, p.y));
            var c = new Vector3(p.x, y - 0.3f, p.y);
            float H = 18f, tankBase = H - 5.7f, tankTop = H - 1.7f;
            m.Cylinder("3a_brick", c, 2.3f, tankBase - 0.2f + 0.3f, 10, V3Palette.C("brick"), false);
            m.Cylinder("6b_lightly_weathered_metal", c + Vector3.up * (tankBase - 0.2f), 3.5f, 0.25f, 14, V3Palette.C("grey"));
            m.Cylinder("6a_painted_metal_panels", c + Vector3.up * tankBase, 3.0f, tankTop - tankBase, 14, V3Palette.C("teal"), false);
            for (int s = 0; s < 14; s++)
            {
                float a0 = s * Mathf.PI * 2f / 14f, a1 = (s + 1) * Mathf.PI * 2f / 14f;
                Vector3 d0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)), d1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1));
                m.TriFacing("4c_corrugated_metal", c + d0 * 3.3f + Vector3.up * tankTop, c + Vector3.up * H, c + d1 * 3.3f + Vector3.up * tankTop, d0 + d1 + Vector3.up, V3Palette.C("slate"));
                m.Box("6b_lightly_weathered_metal", c + (d0 * 3.45f) + Vector3.up * (tankBase + 0.55f), new Vector3(0.06f, 1.1f, 0.06f), Quaternion.identity, V3Palette.C("ink"));
            }
            m.Box("5a_wood_planks_fences", c + new Vector3(0f, 1.05f, 2.32f), new Vector3(1f, 2.1f, 0.1f), Quaternion.identity, V3Palette.C("wood.dark"));
            var go = new GameObject("WaterTower_" + id);
            go.transform.SetParent(root, false);
            go.transform.position = c + Vector3.up * (tankBase / 2f);
            var cc = go.AddComponent<CapsuleCollider>();
            cc.radius = 2.3f;
            cc.height = tankBase;
        }
    }
}
