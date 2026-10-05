using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Everything that stands on the ground besides buildings and trees: street furniture and rocks (registry prefabs or
    // placeholders, yaw jittered 3-12 degrees - nothing on a grid), plot fences, the elite perimeter fence, retaining
    // walls, the outfall pipe and decals, plus invisible blockers (map edge, beach scarps, exit barriers).
    // Fedya's rule: NO fences or walls on district borders. Fences come only from yards (around single plots, with
    // their >= 4.5 m gates) and the elite ring; the map edge is a berm, rocks and an invisible blocker.
    public static class PropScatterer
    {
        public static void Build(LookData d, HeightModel hm, MapLookRegistry registry, LookAssetStore store, Transform parent,
            DistrictCombiner render, DistrictCombiner colliders, List<string> log)
        {
            var root = new GameObject("Props").transform;
            root.SetParent(parent, false);
            LastInstanceRenderers = 0;
            merger = new PrefabMerger();
            nudged = 0;
            int placed = Furniture(d, hm, registry, root, render, colliders);
            int rocks = Rocks(d, hm, registry, root, render, colliders);
            int fences = Yards(d, hm, render, colliders);
            int panels = Elite(d, hm, registry, root, render, colliders);
            int walls = RetainingWalls(d, hm, render, colliders);
            Pipes(d, hm, render, colliders);
            Decals(d, hm, render);
            Blockers(d, hm, store, root);
            int instances = merger.Instances;
            LastInstanceRenderers = merger.Emit(root, store);
            merger = null;
            log.Add($"props: {placed} furniture, {rocks} rocks ({instances} prefab instances merged into {LastInstanceRenderers} submeshes, {nudged} nudged off van roads, placeholders merged), {fences} fenced plots, " +
                    $"{d.elite_fence.Length} elite fence runs ({panels} prefab panels), {walls} retaining walls");
        }

        // ---------------------------------------------------------------- furniture and rocks
        private static string District(LookData d, float x, float y)
        {
            foreach (LookDistrict dist in d.districts)
                if (LookGeom.Inside(dist.pts, x, y))
                    return dist.id;
            return "common";
        }

        // Street lamps follow the district: iron lanterns in the old town, bollards on the elite hill.
        private static string Variant(string type, string district) => type switch
        {
            "lamp_street" when district == "old_town" => "lamp_iron",
            "lamp_street" when district == "elite" => "lamp_bollard",
            "bench" when district == "forest" => "log_bench",
            _ => type,
        };

        // Registry-art variants of a furniture type (placeholder shape and collider footprint stay the base type's):
        // run-down kit in the panel blocks and industry, park furniture in the old town and on the hill, wooden poles
        // in the countryside. Picked by hash, so a rebuild places the same variant.
        public static string ArtVariant(string type, string district, int k, int seed)
        {
            float h = LookGeom.Hash01(k, 47, seed);
            bool rough = district == "residential" || district == "industrial";
            bool rural = district == "village" || district == "forest" || district == "fields" || district == "transition";
            bool posh = district == "old_town" || district == "elite";
            return type switch
            {
                "lamp_street" when rough && h < 0.18f => "lamp_street_broken",
                "lamp_iron" when h < 0.3f => "lamp_iron_double",
                "power_pole" when rural => "power_pole_wood",
                "power_pole" when h < 0.3f => "power_pole_strut",
                "bench" when posh => "bench_park",
                "bench" when rough && h < 0.25f => "bench_broken",
                "bin" when posh => "bin_tipping",
                "garbage_container" when h < 0.4f => "garbage_container_open",
                "bus_stop" when rough => "bus_stop_vandalised",
                _ => type,
            };
        }

        private static float Jitter(int k, int seed)
        {
            float a = 3f + LookGeom.Hash01(k, 3, seed) * 9f;
            return LookGeom.Hash01(k, 5, seed) < 0.5f ? -a : a;
        }

        // Submeshes of the merged registry-art prefabs of the last build, for the batch count in the log.
        public static int LastInstanceRenderers { get; private set; }

        private static PrefabMerger merger;

        // Registry prefabs are instantiated for their transforms and colliders, then their meshes are merged per
        // district x 160 m cell (one submesh per material, like DistrictCombiner), leaving collider-only instances.
        // Hundreds of benches, lamps and fence panels then cost a few draw calls per cell instead of one per piece.
        private sealed class PrefabMerger
        {
            private readonly Dictionary<(string district, int cx, int cz), Dictionary<Material, List<CombineInstance>>> cells = new();
            public int Instances;

            public void Absorb(GameObject inst, string district)
            {
                Instances++;
                Vector3 p = inst.transform.position;
                var key = (string.IsNullOrEmpty(district) ? "common" : district, Mathf.FloorToInt(p.x / 160f), Mathf.FloorToInt(p.z / 160f));
                if (!cells.TryGetValue(key, out var byMaterial)) cells[key] = byMaterial = new Dictionary<Material, List<CombineInstance>>();
                foreach (MeshRenderer mr in inst.GetComponentsInChildren<MeshRenderer>())
                {
                    var mf = mr.GetComponent<MeshFilter>();
                    if (mf == null || mf.sharedMesh == null) continue;
                    Material[] mats = mr.sharedMaterials;
                    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
                    {
                        Material m = s < mats.Length ? mats[s] : null;
                        if (m == null) continue;
                        if (!byMaterial.TryGetValue(m, out var list)) byMaterial[m] = list = new List<CombineInstance>();
                        list.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = s, transform = mf.transform.localToWorldMatrix });
                    }
                }
                // Keep the instance (prefab link, colliders) but drop its renderers: the merged cell draws it.
                foreach (MeshRenderer mr in inst.GetComponentsInChildren<MeshRenderer>())
                {
                    MeshFilter mf = mr.GetComponent<MeshFilter>();
                    UnityEngine.Object.DestroyImmediate(mr);
                    if (mf != null) UnityEngine.Object.DestroyImmediate(mf);
                }
                if (inst.GetComponentInChildren<Collider>() == null) UnityEngine.Object.DestroyImmediate(inst);
                else DistrictCombiner.MarkStatic(inst, false);
            }

            public int Emit(Transform root, LookAssetStore store)
            {
                var group = new GameObject("MergedArt").transform;
                group.SetParent(root, false);
                int submeshes = 0;
                var keys = new List<(string district, int cx, int cz)>(cells.Keys);
                keys.Sort((a, b) => string.CompareOrdinal($"{a.district}_{a.cx:D4}_{a.cz:D4}", $"{b.district}_{b.cx:D4}_{b.cz:D4}"));
                foreach (var key in keys)
                {
                    var byMaterial = cells[key];
                    var parts = new List<CombineInstance>();
                    var materials = new List<Material>();
                    int verts = 0;
                    foreach (var kv in byMaterial)
                    {
                        var part = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
                        part.CombineMeshes(kv.Value.ToArray(), true, true);
                        parts.Add(new CombineInstance { mesh = part, transform = Matrix4x4.identity });
                        materials.Add(kv.Key);
                        verts += part.vertexCount;
                    }
                    string name = $"Art_{key.district}_{key.cx}_{key.cz}";
                    // Index format before combining: changing it afterwards collapses the submeshes.
                    var mesh = new Mesh
                    {
                        name = name,
                        indexFormat = verts < 65000 ? UnityEngine.Rendering.IndexFormat.UInt16 : UnityEngine.Rendering.IndexFormat.UInt32,
                    };
                    mesh.CombineMeshes(parts.ToArray(), false, true);
                    foreach (CombineInstance p in parts) UnityEngine.Object.DestroyImmediate(p.mesh);
                    mesh.RecalculateBounds();
                    var go = new GameObject(name);
                    go.transform.SetParent(group, false);
                    go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(mesh);
                    go.AddComponent<MeshRenderer>().sharedMaterials = materials.ToArray();
                    DistrictCombiner.MarkStatic(go);
                    submeshes += materials.Count;
                }
                return submeshes;
            }
        }

        private static int Furniture(LookData d, HeightModel hm, MapLookRegistry registry, Transform root, DistrictCombiner render, DistrictCombiner colliders)
        {
            var group = new GameObject("Furniture").transform;
            group.SetParent(root, false);
            for (int k = 0; k < d.furniture.Length; k++)
            {
                LookFurniture f = d.furniture[k];
                string district = District(d, f.x, f.y);
                string type = Variant(f.type, district);
                float yaw = f.a + Jitter(k, d.seed);
                var pos = new Vector3(f.x, hm.Height(f.x, f.y), f.y);
                // Family fallback is fine for street furniture ("prop/_default" stands in for any missing kit piece).
                // Art variants (broken lamps, park benches, wooden poles...) only where the registry has them.
                PrefabSlot slot = FurnitureSlot(d, registry, k);
                Place(d, group, slot, district, () => PlaceholderKit.Prop(type, out _), PropCollide(type), 2.2f,
                    pos, Quaternion.Euler(0f, yaw, 0f), Vector3.one, render, colliders);
            }
            return d.furniture.Length;
        }

        // The registry slot furniture item k is built from (art variant first, then the type or its family fallback);
        // null or an empty slot means the PlaceholderKit shape. Shared with MapLookValidator.
        public static PrefabSlot FurnitureSlot(LookData d, MapLookRegistry registry, int k)
        {
            LookFurniture f = d.furniture[k];
            string district = District(d, f.x, f.y);
            string type = Variant(f.type, district);
            string art = ArtVariant(type, district, k, d.seed);
            return (art != type ? registry.ExactPrefabSlot("prop/" + art) : null) ?? registry.PrefabSlotFor("prop/" + type);
        }

        private static bool PropCollide(string type)
        {
            PlaceholderKit.Prop(type, out bool collide);
            return collide;
        }

        private static int Rocks(LookData d, HeightModel hm, MapLookRegistry registry, Transform root, DistrictCombiner render, DistrictCombiner colliders)
        {
            var group = new GameObject("Rocks").transform;
            group.SetParent(root, false);
            PrefabSlot rockSlot = registry.ExactPrefabSlot("prop/rock"); // never the "prop/_default" family prefab
            for (int k = 0; k < d.rocks.Length; k++)
            {
                LookRock r = d.rocks[k];
                int variant = (int)(LookGeom.Hash01(k, 41, d.seed) * 4f) % 4;
                var scale = new Vector3(Mathf.Max(0.3f, r.sx), Mathf.Max(0.3f, r.sy), Mathf.Max(0.3f, r.sz));
                var pos = new Vector3(r.x, hm.Height(r.x, r.y) - 0.15f * scale.y, r.y);
                Place(null, group, rockSlot, District(d, r.x, r.y), () => PlaceholderKit.Rock(variant), true, float.MaxValue, pos, Quaternion.Euler(0f, r.a, 0f), scale,
                    render, colliders);
            }
            return d.rocks.Length;
        }

        // One prop: a registry prefab stays an instance; a placeholder is merged into the district cell meshes (render
        // and collider), so the hundreds of stand-ins cost no draw calls of their own.
        private static void Place(LookData d, Transform parent, PrefabSlot slot, string district, Func<MeshDraft> placeholder, bool collide, float footprintBelow,
            Vector3 pos, Quaternion rot, Vector3 scale, DistrictCombiner render, DistrictCombiner colliders)
        {
            if (slot?.prefab == null)
            {
                MeshDraft draft = placeholder();
                Matrix4x4 m = Matrix4x4.TRS(pos, rot, scale);
                render.Add(district, m, draft, pos);
                if (collide && ColliderBox(draft, footprintBelow, out Vector3 centre, out Vector3 size))
                {
                    var col = new MeshDraft();
                    col.Box(col.Slot("collision"), centre, size, Quaternion.identity, true);
                    colliders.Add(district, m, col, pos);
                }
                return;
            }
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, parent);
            inst.transform.SetPositionAndRotation(pos, rot);
            inst.transform.localScale = Vector3.Scale(slot.scale, scale);
            if (!slot.collider)
                foreach (Collider c in inst.GetComponentsInChildren<Collider>())
                    UnityEngine.Object.DestroyImmediate(c);
            if (d != null) KeepOffRoads(d, inst);
            merger.Absorb(inst, district);
        }

        // Registry art is bigger than the placeholder footprints the plan was checked with (a 5.6 m bus shelter, a
        // braced wooden pole): when a collider corner reaches into a van road, slide the piece out along the road
        // normal by the overlap plus 10 cm, so the van keeps its full road width.
        private static int nudged;

        // Returns true when the piece was moved. Also used for registry-prefab buildings (kiosks, ATM, bus shelter).
        internal static bool KeepOffRoads(LookData d, GameObject inst)
        {
            bool moved = false;
            for (int pass = 0; pass < 3; pass++)
            {
                float worst = 0f;
                Vector2 push = Vector2.zero;
                foreach (Collider c in inst.GetComponentsInChildren<Collider>())
                    foreach (Vector3 corner in Footprint(c))
                        foreach (LookRoad r in d.roads)
                        {
                            if (!r.van || LookGeom.Count(r.pts) < 2) continue;
                            float into = r.w / 2f - LookGeom.DistToPolyline(r.pts, corner.x, corner.z, false, out int seg, out float t);
                            if (into <= worst) continue;
                            float ax = r.pts[2 * seg], ay = r.pts[2 * seg + 1], bx = r.pts[2 * seg + 2], by = r.pts[2 * seg + 3];
                            var onLine = new Vector2(Mathf.Lerp(ax, bx, t), Mathf.Lerp(ay, by, t));
                            var centre = new Vector2(inst.transform.position.x, inst.transform.position.z);
                            Vector2 away = centre - onLine;
                            if (away.sqrMagnitude < 1e-4f) away = new Vector2(by - ay, ax - bx); // centre on the axis: any side
                            worst = into;
                            push = away.normalized;
                        }
                if (worst <= 0f) return moved;
                if (pass == 0) nudged++;
                moved = true;
                inst.transform.position += new Vector3(push.x, 0f, push.y) * (worst + 0.1f);
            }
            return moved;
        }

        internal static IEnumerable<Vector3> Footprint(Collider c)
        {
            Vector3 centre, ext;
            switch (c)
            {
                case BoxCollider b:
                    centre = b.center;
                    ext = b.size / 2f;
                    break;
                case CapsuleCollider cap:
                    centre = cap.center;
                    ext = new Vector3(cap.radius, 0f, cap.radius);
                    break;
                default:
                    yield return c.bounds.center;
                    yield break;
            }
            for (int sx = -1; sx <= 1; sx++)
                for (int sz = -1; sz <= 1; sz++)
                    yield return c.transform.TransformPoint(centre + new Vector3(sx * ext.x, 0f, sz * ext.z));
        }

        // Placeholder collider box (local space): full height, but the footprint only of what stands below
        // `footprintBelow` metres, so a lamp arm or a pole crossarm over the road is not a wall down to the ground.
        public static bool ColliderBox(MeshDraft draft, float footprintBelow, out Vector3 centre, out Vector3 size)
        {
            centre = size = Vector3.zero;
            if (draft == null || draft.Vertices.Count == 0) return false;
            Vector3 min = Vector3.positiveInfinity, max = Vector3.negativeInfinity, lowMin = Vector3.positiveInfinity, lowMax = Vector3.negativeInfinity;
            bool low = false;
            foreach (Vector3 v in draft.Vertices)
            {
                min = Vector3.Min(min, v);
                max = Vector3.Max(max, v);
                if (v.y > footprintBelow) continue;
                lowMin = Vector3.Min(lowMin, v);
                lowMax = Vector3.Max(lowMax, v);
                low = true;
            }
            if (low)
            {
                min.x = lowMin.x;
                min.z = lowMin.z;
                max.x = lowMax.x;
                max.z = lowMax.z;
            }
            size = Vector3.Max(max - min, new Vector3(0.15f, 0.15f, 0.15f));
            centre = (min + max) / 2f;
            return true;
        }

        // The collider footprint a furniture item gets in the build (placeholder shape; registry art is assumed to match).
        public static bool FurnitureCollider(LookData d, LookFurniture f, int k, out Vector3 centre, out Vector3 size, out float yaw)
        {
            string type = Variant(f.type, District(d, f.x, f.y));
            yaw = f.a + Jitter(k, d.seed);
            MeshDraft draft = PlaceholderKit.Prop(type, out bool collide);
            centre = size = Vector3.zero;
            return collide && ColliderBox(draft, 2.2f, out centre, out size);
        }

        private static int Yards(LookData d, HeightModel hm, DistrictCombiner render, DistrictCombiner colliders)
        {
            int count = 0;
            Func<float, float, bool> border = FenceBuilder.BorderTest(d);
            foreach (LookYard y in d.yards)
            {
                var (draft, col) = FenceBuilder.Yard(y, hm.Height, border);
                if (draft == null) continue;
                LookGeom.Centroid(y.pts, out float cx, out float cz);
                var centre = new Vector3(cx, 0f, cz);
                render.Add(y.district, Matrix4x4.identity, draft, centre);
                colliders.Add(y.district, Matrix4x4.identity, col, centre);
                count++;
            }
            return count;
        }

        // The elite ring: kit panels and posts (registry "prop/fence_elite_panel" / "_post") when present, else the
        // procedural bars. Hedge, gate piers and the continuous collision beam always come from FenceBuilder.
        private static int Elite(LookData d, HeightModel hm, MapLookRegistry registry, Transform root, DistrictCombiner render, DistrictCombiner colliders)
        {
            Vector2 inside = d.hills.Length > 0 ? new Vector2(d.hills[0].x, d.hills[0].y) : Vector2.zero;
            PrefabSlot panel = registry.ExactPrefabSlot("prop/fence_elite_panel"), post = registry.ExactPrefabSlot("prop/fence_elite_post");
            bool kit = panel != null && post != null;
            Transform group = null;
            int count = 0;
            foreach (LookEliteFence f in d.elite_fence)
            {
                var (draft, col) = FenceBuilder.Elite(f, hm.Height, inside, !kit);
                if (draft == null) continue;
                var centre = new Vector3(f.pts[0], 0f, f.pts[1]);
                render.Add("elite", Matrix4x4.identity, draft, centre);
                colliders.Add("elite", Matrix4x4.identity, col, centre);
                if (!kit) continue;
                if (group == null)
                {
                    group = new GameObject("EliteFence").transform;
                    group.SetParent(root, false);
                }
                foreach (List<Vector2> run in FenceBuilder.EliteRuns(f))
                    count += EliteKit(group, run, hm, panel, post);
            }
            return count;
        }

        // Panels between posts at a ~3 m pitch along each run (panel stretched to the bay), sunk 5 cm; colliders off
        // (the beam from FenceBuilder is gap-free).
        private static int EliteKit(Transform group, List<Vector2> run, HeightModel hm, PrefabSlot panel, PrefabSlot post)
        {
            const float panelLength = 2.5f, postWidth = 0.66f;
            int count = 0;
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                float len = Vector2.Distance(a, b);
                if (len < 0.3f) continue;
                Vector2 dir = (b - a) / len;
                Quaternion rot = Quaternion.LookRotation(new Vector3(-dir.y, 0f, dir.x));
                // Panels stay level (vertical bars), so on a slope the uphill end sinks by the rise over the bay: halve
                // the bays until no bay rises more than MaxRise (down to MinBay), which keeps at most ~0.3 m of the
                // 2.39 m panel underground even on the 30% stretches of the ring.
                int bays = Mathf.Max(1, Mathf.RoundToInt(len / 3f));
                while (len / bays >= 2f * MinBay && MaxBayRise(a, b, bays, hm) > MaxRise) bays *= 2;
                float bay = len / bays;
                for (int p = 0; p <= bays; p++)
                {
                    if (p == 0 && i > 0) continue; // shared corner post
                    Vector2 q = Vector2.Lerp(a, b, (float)p / bays);
                    Instance(group, post, new Vector3(q.x, hm.Height(q.x, q.y) - 0.05f, q.y), rot, Vector3.one);
                }
                if (bay <= postWidth + 0.2f) continue;
                for (int p = 0; p < bays; p++)
                {
                    Vector2 q0 = Vector2.Lerp(a, b, (float)p / bays), q1 = Vector2.Lerp(a, b, (float)(p + 1) / bays), m = (q0 + q1) / 2f;
                    float y = Mathf.Min(hm.Height(q0.x, q0.y), hm.Height(q1.x, q1.y)) - 0.05f;
                    Instance(group, panel, new Vector3(m.x, y, m.y), rot, new Vector3((bay - postWidth + 0.1f) / panelLength, 1f, 1f));
                    count++;
                }
            }
            return count;
        }

        private const float MaxRise = 0.3f, MinBay = 1.2f;

        private static float MaxBayRise(Vector2 a, Vector2 b, int bays, HeightModel hm)
        {
            float worst = 0f;
            for (int p = 0; p < bays; p++)
            {
                Vector2 q0 = Vector2.Lerp(a, b, (float)p / bays), q1 = Vector2.Lerp(a, b, (float)(p + 1) / bays);
                worst = Mathf.Max(worst, Mathf.Abs(hm.Height(q0.x, q0.y) - hm.Height(q1.x, q1.y)));
            }
            return worst;
        }

        private static void Instance(Transform parent, PrefabSlot slot, Vector3 pos, Quaternion rot, Vector3 scale)
        {
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, parent);
            inst.transform.SetPositionAndRotation(pos, rot);
            inst.transform.localScale = Vector3.Scale(slot.scale, scale);
            foreach (Collider c in inst.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
            merger.Absorb(inst, "elite");
        }

        // Stone retaining walls around pads that sit more than 1.2 m off the natural ground (elite hill mansions).
        private static int RetainingWalls(LookData d, HeightModel hm, DistrictCombiner render, DistrictCombiner colliders)
        {
            int count = 0;
            foreach (HeightModel.RetainingWall w in hm.Walls)
            {
                LookBuilding b = System.Array.Find(d.buildings, x => x.id == w.BuildingId);
                string district = b != null ? b.district : "common";
                var (draft, col) = FenceBuilder.RetainingWall(w.Ring, hm.Height, district == "elite" ? "mat/elite/pier" : "mat/stone");
                if (draft.IsEmpty) continue;
                LookGeom.Centroid(w.Ring, out float cx, out float cz);
                render.Add(district, Matrix4x4.identity, draft, new Vector3(cx, 0f, cz));
                colliders.Add(district, Matrix4x4.identity, col, new Vector3(cx, 0f, cz));
                count++;
            }
            return count;
        }

        private static void Pipes(LookData d, HeightModel hm, DistrictCombiner render, DistrictCombiner colliders)
        {
            foreach (LookPipe p in d.pipes)
            {
                var (draft, col) = FenceBuilder.Pipe(p, hm.Height);
                if (draft == null) continue;
                var centre = new Vector3(p.pts[0], 0f, p.pts[1]);
                render.Add("industrial", Matrix4x4.identity, draft, centre);
                colliders.Add("industrial", Matrix4x4.identity, col, centre);
            }
        }

        private static void Decals(LookData d, HeightModel hm, DistrictCombiner render)
        {
            foreach (LookDecal dc in d.decals)
                render.Add("common", Matrix4x4.identity, FenceBuilder.Decal(dc, hm.Height, d.sea.level), new Vector3(dc.x, 0f, dc.y));
        }

        // Invisible walls: inland map edge (coast edges stay open to the beach), beach-end scarps, exit barriers.
        private static void Blockers(LookData d, HeightModel hm, LookAssetStore store, Transform root)
        {
            var group = new GameObject("Blockers").transform;
            group.SetParent(root, false);
            LookBoundary bnd = d.boundary;
            int n = LookGeom.Count(bnd.pts);
            var edge = new MeshDraft();
            int slot = edge.Slot("collision");
            float bh = bnd.blocker_h > 0f ? bnd.blocker_h : 6f;
            for (int e = 0; e < n; e++)
            {
                if (e < bnd.coast.Length && bnd.coast[e] == 1) continue;
                int f = (e + 1) % n;
                var a = new Vector3(bnd.pts[2 * e], 0f, bnd.pts[2 * e + 1]);
                var b = new Vector3(bnd.pts[2 * f], 0f, bnd.pts[2 * f + 1]);
                float y0 = Mathf.Min(hm.Height(a.x, a.z), hm.Height(b.x, b.z)) - 2f, y1 = Mathf.Max(hm.Height(a.x, a.z), hm.Height(b.x, b.z)) + bh;
                edge.Beam(slot, a, b, 1f, y0, y1, true);
            }
            Collider(group, "Boundary", edge, store);
            foreach (LookBlocker bl in d.blockers) Prism(group, bl.id, bl.pts, Mathf.Max(3f, bl.h), hm, store);
            foreach (LookExit ex in d.exits)
                for (int k = 0; k < ex.barriers.Length; k++)
                {
                    Prism(group, $"Exit_{ex.id}_{k}", ex.barriers[k].pts, Mathf.Max(3f, ex.h), hm, store);
                    if (ex.type == "destroyed_bridge") BrokenDeck(root, ex.barriers[k].pts, hm, store);
                }
        }

        private static void Prism(Transform group, string name, float[] pts, float h, HeightModel hm, LookAssetStore store)
        {
            if (LookGeom.Count(pts) < 3) return;
            float low = float.MaxValue, high = float.MinValue;
            for (int i = 0; i + 1 < pts.Length; i += 2)
            {
                float y = hm.Height(pts[i], pts[i + 1]);
                low = Mathf.Min(low, y);
                high = Mathf.Max(high, y);
            }
            var draft = new MeshDraft();
            Vector2[] poly = LookConvert.Poly(pts);
            if (LookGeom.SignedArea(pts) < 0f) System.Array.Reverse(poly);
            draft.Prism(draft.Slot("collision"), poly, low - 1f, high + h, true, true);
            Collider(group, name, draft, store);
        }

        private static void Collider(Transform group, string name, MeshDraft draft, LookAssetStore store)
        {
            if (draft.IsEmpty) return;
            var go = new GameObject(name);
            go.transform.SetParent(group, false);
            go.AddComponent<MeshCollider>().sharedMesh = store.AddMesh(draft.ToMesh(name));
            DistrictCombiner.MarkStatic(go, false);
        }

        // The NE exit: a collapsed concrete span tilted into the gap behind the barrier rocks.
        private static void BrokenDeck(Transform root, float[] pts, HeightModel hm, LookAssetStore store)
        {
            LookGeom.Centroid(pts, out float cx, out float cz);
            var draft = new MeshDraft();
            float y = hm.Height(cx, cz);
            draft.Box(draft.Slot("mat/bridge"), new Vector3(cx, y + 1.2f, cz), new Vector3(7f, 0.7f, 12f), Quaternion.Euler(14f, 35f, 6f), true);
            var go = new GameObject("Exit_BrokenBridge");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(draft.ToMesh(go.name));
            go.AddComponent<MeshRenderer>().sharedMaterials = LookAssetStore.Materials(draft, LookAssetStore.Registry());
            DistrictCombiner.MarkStatic(go);
        }
    }
}
