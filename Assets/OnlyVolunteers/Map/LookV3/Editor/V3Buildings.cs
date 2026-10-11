using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 buildings: per building one static mesh per sink, merged by material (category), under a LODGroup:
    // LOD0 = shell + big details (shadows) + small details (no shadows) up to ~70 m, LOD1 = shell + flat facade quads up
    // to ~220 m, LOD2 = shell + glass quads beyond. Colliders: boxes per footprint rectangle (or one convex prism for
    // convex non-rectangular footprints), boxes for porch steps. MapBuildingInfo as in the v12 look (doors for gameplay).
    public static class V3Buildings
    {
        public const float Lod0Distance = 60f, Lod1Distance = 200f, CullDistance = 900f, DesignFov = 65f;

        public sealed class Stats
        {
            public int Buildings, Renderers, Lod0Tris, Lod1Tris, Lod2Tris, Modules, Colliders, MaxTris;
            public string MaxId;
        }

        public static Stats Build(LookData d, HeightModel hm, V3Kit kit, V3Store store, Transform parent, List<string> log)
        {
            var stats = new Stats();
            var root = new GameObject("Buildings").transform;
            root.SetParent(parent, false);
            var list = new List<LookBuilding>(d.buildings);
            list.Sort((a, b) => string.CompareOrdinal(a.id, b.id));
            var done = new List<(V3Building b, string wall)>();
            var archetypes = new Dictionary<string, int>();
            foreach (LookBuilding b in list)
            {
                if (LookGeom.Count(b.fp) < 3) continue;
                float pad = hm.Pads.TryGetValue(b.id, out float p) ? p : hm.Height(b.x, b.y);
                var c = new V3Building(b, pad, hm.LowestUnder(b.fp));
                V3Grammar g = V3Facade.For(b);
                c.Arch = g.Arch;
                var neighbours = new List<(V3Building b, string wall)>();
                foreach (var other in done)
                    if (Near(other.b.B, b, 12f))
                        neighbours.Add(other);
                V3Facade.Colours(c, g, neighbours);
                switch (g.Special)
                {
                    case "container": Container(c); break;
                    case "tank": Tank(c, kit); break;
                    case "frame": Frame(c, false); break;
                    case "slab": Frame(c, true); break;
                    case "scaffold": Scaffold(c); break;
                    case "canopy": Canopy(c); break;
                    case "procedural": FromProcedural(c, hm); break;
                    default: V3Facade.Build(c, g, kit, d); break;
                }
                Emit(c, store, root, stats);
                done.Add((c, c.WallSwatch));
                archetypes[g.Arch] = archetypes.TryGetValue(g.Arch, out int n) ? n + 1 : 1;
            }
            var parts = new List<string>();
            foreach (var kv in archetypes) parts.Add($"{kv.Key} {kv.Value}");
            parts.Sort();
            log.Add($"buildings v3: {stats.Buildings} ({string.Join(", ", parts)}); {stats.Modules} kit modules; tris LOD0 {stats.Lod0Tris}, LOD1 {stats.Lod1Tris}, " +
                    $"LOD2 {stats.Lod2Tris}; heaviest {stats.MaxId} {stats.MaxTris}; {stats.Renderers} renderers, {stats.Colliders} colliders");
            return stats;
        }

        private static bool Near(LookBuilding a, LookBuilding b, float dist)
        {
            LookGeom.Bounds(a.fp, out float ax0, out float ay0, out float ax1, out float ay1);
            LookGeom.Bounds(b.fp, out float bx0, out float by0, out float bx1, out float by1);
            if (ax0 - dist > bx1 || bx0 - dist > ax1 || ay0 - dist > by1 || by0 - dist > ay1) return false;
            for (int i = 0; i + 1 < a.fp.Length; i += 2)
                if (LookGeom.DistToPolyline(b.fp, a.fp[i], a.fp[i + 1], true, out _, out _) < dist) return true;
            return false;
        }

        // ---------------------------------------------------------------- output

        private static void Emit(V3Building c, V3Store store, Transform root, Stats stats)
        {
            LookBuilding b = c.B;
            var go = new GameObject($"B_{b.id}");
            go.transform.SetParent(root, false);
            go.transform.position = new Vector3(b.x, c.Pad, b.y);
            var info = go.AddComponent<MapBuildingInfo>();
            info.Id = b.id;
            info.Kind = b.kind;
            info.Type = b.type;
            info.District = b.district;
            info.Label = b.label;
            info.Style = "v3/" + c.Arch;
            info.Floors = b.floors;
            info.Height = c.H;
            info.PadY = c.Pad;
            info.SignText = b.sign_text;
            info.Footprint = LookConvert.Poly(b.fp);
            var doors = new Vector3[c.Doors.Count];
            var facing = new Quaternion[c.Doors.Count];
            for (int i = 0; i < doors.Length; i++)
            {
                V3Building.Edge e = c.Edges[c.Doors[i].Edge];
                doors[i] = go.transform.position + V3Building.At(e, c.Doors[i].U, 0.45f, 0.4f);
                facing[i] = Quaternion.LookRotation(e.N);
            }
            info.Doors = doors;
            info.DoorFacing = facing;

            Renderer shell = Part(go, "Shell", c.Shell, store, ShadowCastingMode.On, true);
            Renderer big = Part(go, "DetailBig", c.Big, store, ShadowCastingMode.On, false);
            Renderer small = Part(go, "DetailSmall", c.Small, store, ShadowCastingMode.Off, false);
            Renderer lod1 = Part(go, "Lod1", c.Lod1, store, ShadowCastingMode.Off, false);
            Renderer lod2 = Part(go, "Lod2", c.Lod2, store, ShadowCastingMode.Off, false);
            var r0 = new List<Renderer>();
            foreach (Renderer r in new[] { shell, big, small }) if (r != null) r0.Add(r);
            var r1 = new List<Renderer>();
            foreach (Renderer r in new[] { shell, lod1 }) if (r != null) r1.Add(r);
            var r2 = new List<Renderer>();
            foreach (Renderer r in new[] { shell, lod2 }) if (r != null) r2.Add(r);
            foreach (Renderer r in new[] { shell, big, small, lod1, lod2 }) if (r != null) stats.Renderers++;
            if (shell != null)
            {
                var lg = go.AddComponent<LODGroup>();
                lg.fadeMode = LODFadeMode.CrossFade;
                lg.animateCrossFading = true;
                lg.RecalculateBounds();
                float size = Mathf.Max(1f, lg.size);
                float bias = Mathf.Max(0.1f, QualitySettings.lodBias), k = 2f * Mathf.Tan(DesignFov * 0.5f * Mathf.Deg2Rad);
                // v17 (denser game-scale streets, fog opaque at 400 m): detail to 45 m, facade quads to 160 m, cull at 460 m.
                bool v17 = MapLookBuilderV3.IsV17(MapLookBuilderV3.Current);
                float d0 = v17 ? 45f : Lod0Distance, d1 = v17 ? 160f : Lod1Distance, d2 = v17 ? V3Lighting.FarClipV17 : CullDistance;
                float h0 = Mathf.Clamp(size * bias / (k * d0), 0.02f, 0.95f);
                float h1 = Mathf.Clamp(size * bias / (k * d1), 0.004f, h0 * 0.8f);
                float h2 = Mathf.Clamp(size * bias / (k * d2), 0.0005f, h1 * 0.8f);
                lg.SetLODs(new[] { new LOD(h0, r0.ToArray()), new LOD(h1, r1.ToArray()), new LOD(h2, r2.ToArray()) });
            }
            stats.Lod0Tris += c.Shell.TriangleCount + c.Big.TriangleCount + c.Small.TriangleCount;
            stats.Lod1Tris += c.Shell.TriangleCount + c.Lod1.TriangleCount;
            stats.Lod2Tris += c.Shell.TriangleCount + c.Lod2.TriangleCount;
            stats.Modules += c.Modules;
            int t0 = c.Shell.TriangleCount + c.Big.TriangleCount + c.Small.TriangleCount;
            if (t0 > stats.MaxTris)
            {
                stats.MaxTris = t0;
                stats.MaxId = b.id + " " + c.Arch;
            }
            stats.Colliders += Colliders(go, c, store);
            stats.Buildings++;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
        }

        private static Renderer Part(GameObject owner, string name, V3Mesh mesh, V3Store store, ShadowCastingMode shadows, bool occluder)
        {
            if (mesh.IsEmpty) return null;
            var go = new GameObject(name);
            go.transform.SetParent(owner.transform, false);
            Mesh m = store.AddMesh(mesh.ToMesh($"{owner.name}_{name}", out string[] cats));
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            var mats = new Material[cats.Length];
            for (int i = 0; i < cats.Length; i++) mats[i] = V3Materials.Mat(cats[i]);
            mr.sharedMaterials = mats;
            mr.shadowCastingMode = shadows;
            mr.receiveShadows = true;
            var flags = StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic;
            if (occluder) flags |= StaticEditorFlags.OccluderStatic;
            GameObjectUtility.SetStaticEditorFlags(go, flags);
            return mr;
        }

        // Boxes per footprint rectangle when they cover the footprint, else one convex prism (convex footprints) or a
        // convex prism per plan triangle (concave ones). Never a concave mesh collider.
        private static int Colliders(GameObject go, V3Building c, V3Store store)
        {
            int count = 0;
            LookBuilding b = c.B;
            float top = Mathf.Max(c.H, 2.5f), low = c.Low;
            float fpArea = Mathf.Abs(LookGeom.SignedArea(b.fp)), rectArea = 0f;
            bool rectsInside = c.Rects.Count > 0;
            foreach (V3Building.Rect r in c.Rects)
            {
                rectArea += r.Hu * r.Hv * 4f;
                for (int su = -1; su <= 1; su += 2)
                    for (int sv = -1; sv <= 1; sv += 2)
                    {
                        Vector3 p = r.C + r.U * (su * r.Hu * 0.98f) + r.V * (sv * r.Hv * 0.98f);
                        if (!LookGeom.Inside(b.fp, p.x + b.x, p.z + b.y) && LookGeom.DistToPolyline(b.fp, p.x + b.x, p.z + b.y, true, out _, out _) > 0.3f) rectsInside = false;
                    }
            }
            bool special = c.Arch == "frame" || c.Arch == "scaffold" || c.Arch == "canopy" || c.Arch == "slab";
            if (special)
            {
                foreach (var box in c.Boxes) count += Box(go, box.centre, box.size, box.rot);
                return count;
            }
            if (rectsInside && rectArea > fpArea * 0.9f && rectArea < fpArea * 1.15f)
            {
                foreach (V3Building.Rect r in c.Rects)
                    count += Box(go, r.C + Vector3.up * ((low + top) / 2f), new Vector3(r.Hv * 2f, top - low, r.Hu * 2f), Quaternion.LookRotation(r.U));
            }
            else if (Convex(c.Fp))
                count += Prism(go, c.Fp, low, top, store, "Collider_Hull");
            else
                for (int i = 0; i + 5 < b.tris.Length; i += 6)
                {
                    var tri = new[] { new Vector2(b.tris[i] - b.x, b.tris[i + 1] - b.y), new Vector2(b.tris[i + 2] - b.x, b.tris[i + 3] - b.y), new Vector2(b.tris[i + 4] - b.x, b.tris[i + 5] - b.y) };
                    count += Prism(go, tri, low, top, store, $"Collider_Tri{i / 6}");
                }
            foreach (var box in c.Boxes) count += Box(go, box.centre, box.size, box.rot);
            return count;
        }

        private static bool Convex(Vector2[] p)
        {
            int n = p.Length, sign = 0;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = p[i], b = p[(i + 1) % n], c = p[(i + 2) % n];
                float cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
                if (Mathf.Abs(cross) < 1e-4f) continue;
                int s = cross > 0f ? 1 : -1;
                if (sign == 0) sign = s;
                else if (s != sign) return false;
            }
            return true;
        }

        private static int Box(GameObject owner, Vector3 centre, Vector3 size, Quaternion rot)
        {
            var go = new GameObject("Collider");
            go.transform.SetParent(owner.transform, false);
            go.transform.SetLocalPositionAndRotation(centre, rot);
            go.AddComponent<BoxCollider>().size = size;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            return 1;
        }

        private static int Prism(GameObject owner, Vector2[] poly, float y0, float y1, V3Store store, string name)
        {
            var draft = new MeshDraft();
            Vector2[] p = (Vector2[])poly.Clone();
            float area = 0f;
            for (int i = 0, j = p.Length - 1; i < p.Length; j = i++) area += p[j].x * p[i].y - p[i].x * p[j].y;
            if (area < 0f) System.Array.Reverse(p);
            draft.Prism(draft.Slot("collision"), p, y0, y1, true, true);
            var go = new GameObject(name);
            go.transform.SetParent(owner.transform, false);
            var mc = go.AddComponent<MeshCollider>();
            mc.sharedMesh = store.AddMesh(draft.ToMesh($"{owner.name}_{name}"));
            mc.convex = true;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            return 1;
        }

        // ---------------------------------------------------------------- special shapes

        // Shipping container: ribbed painted steel box (texture), double doors with lock bars on one short end, steel
        // corner posts. The whole stack reads from afar, so every LOD shares the shell.
        private static void Container(V3Building c)
        {
            c.WallCat = "6a_painted_metal_panels";
            c.RoofCat = "6a_painted_metal_panels";
            c.RoofColour = c.Wall;
            c.Plinth = c.Wall * 0.8f;
            c.Low = Mathf.Max(c.Low, -0.4f);
            c.H = Mathf.Min(c.H, 2.6f * Mathf.Max(1, c.Floors));
            c.BuildShell(0f, false, 0f, 0f);
            V3Building.Edge shortest = c.Edges[0];
            foreach (V3Building.Edge e in c.Edges) if (e.Len > 0.5f && e.Len < shortest.Len) shortest = e;
            Quaternion rot = Quaternion.LookRotation(-shortest.N);
            Color dark = c.Wall * 0.72f;
            float h = c.H;
            c.Big.Box("6a_painted_metal_panels", V3Building.At(shortest, shortest.Len / 2f, h / 2f, 0.03f), new Vector3(shortest.Len - 0.2f, h - 0.2f, 0.06f), rot, dark);
            for (int k = -1; k <= 1; k += 2)
                for (int bar = 0; bar < 2; bar++)
                {
                    float u = shortest.Len / 2f + k * (0.25f + bar * 0.55f);
                    c.Small.Box("6b_lightly_weathered_metal", V3Building.At(shortest, u, h / 2f, 0.09f), new Vector3(0.05f, h - 0.4f, 0.05f), rot, V3Palette.C("grey.light"));
                }
            foreach (V3Building.Edge e in c.Edges)
                c.Big.Box("6b_lightly_weathered_metal", e.A + Vector3.up * (h / 2f), new Vector3(0.16f, h, 0.16f), Quaternion.LookRotation(e.Dir), V3Palette.C("grey.dark"));
            c.Top = h;
        }

        // Storage tank: steel cylinder (the round footprint), two bands, a ladder up the front, a railing ring on top.
        private static void Tank(V3Building c, V3Kit kit)
        {
            c.WallCat = "6b_lightly_weathered_metal";
            c.Wall = V3Palette.C("chalk");
            c.RoofCat = "6b_lightly_weathered_metal";
            c.RoofColour = V3Palette.C("grey.light");
            c.BuildShell(0f, false, 0f, 0f);
            foreach (V3Building.Edge e in c.Edges)
            {
                foreach (float y in new[] { c.H * 0.33f, c.H * 0.66f })
                    V3Building.Band(c.Big, "6b_lightly_weathered_metal", e, y, y + 0.25f, 0.08f, V3Palette.C("grey"), 0.05f);
                c.Small.Box("6b_lightly_weathered_metal", e.A + Vector3.up * (c.H + 0.55f), new Vector3(0.06f, 1.1f, 0.06f), Quaternion.identity, V3Palette.C("grey.dark"));
            }
            V3Building.Edge f = c.Edges[c.Front];
            Quaternion rot = Quaternion.LookRotation(-f.N);
            for (int k = -1; k <= 1; k += 2)
                c.Small.Box("6b_lightly_weathered_metal", V3Building.At(f, f.Len / 2f + k * 0.25f, c.H / 2f, 0.25f), new Vector3(0.06f, c.H, 0.06f), rot, V3Palette.C("ink"));
            for (float y = 0.3f; y < c.H; y += 0.35f)
                c.Small.Box("6b_lightly_weathered_metal", V3Building.At(f, f.Len / 2f, y, 0.25f), new Vector3(0.5f, 0.04f, 0.04f), rot, V3Palette.C("ink"));
            c.Top = c.H + 1.1f;
        }

        // Concrete frame under construction (columns, slabs, rebar) or a foundation slab with column stubs.
        private static void Frame(V3Building c, bool slabOnly)
        {
            Color conc = V3Palette.C("panel"), rebar = V3Palette.C("brick.dark");
            int floors = slabOnly ? 0 : c.Floors;
            foreach (V3Building.Rect r in c.Rects)
            {
                Quaternion rot = Quaternion.LookRotation(r.U);
                c.Shell.Box("3c_concrete_panels", r.C + Vector3.up * (0.2f + c.Low / 2f), new Vector3(r.Hv * 2f + 0.4f, 0.4f - c.Low, r.Hu * 2f + 0.4f), rot, conc);
                c.Boxes.Add((r.C + Vector3.up * (0.2f + c.Low / 2f), new Vector3(r.Hv * 2f + 0.4f, 0.4f - c.Low, r.Hu * 2f + 0.4f), rot));
                int nu = Mathf.Max(1, Mathf.RoundToInt(r.Hu * 2f / 6f)), nv = Mathf.Max(1, Mathf.RoundToInt(r.Hv * 2f / 6f));
                float colTop = slabOnly ? 1.4f : floors * c.Fh;
                for (int i = 0; i <= nu; i++)
                    for (int j = 0; j <= nv; j++)
                    {
                        Vector3 p = r.C + r.U * (-r.Hu + 2f * r.Hu * i / nu) + r.V * (-r.Hv + 2f * r.Hv * j / nv);
                        c.Shell.Box("3c_concrete_panels", p + Vector3.up * (0.4f + colTop / 2f), new Vector3(0.45f, colTop, 0.45f), rot, conc);
                        c.Boxes.Add((p + Vector3.up * (0.4f + colTop / 2f), new Vector3(0.45f, colTop, 0.45f), rot));
                        for (int k = 0; k < 4; k++)
                            c.Small.Box("6b_lightly_weathered_metal", p + new Vector3((k % 2 - 0.5f) * 0.25f, 0.4f + colTop + 0.45f, (k / 2 - 0.5f) * 0.25f), new Vector3(0.04f, 0.9f, 0.04f), rot, rebar);
                    }
                for (int f = 1; f < floors; f++)
                {
                    float y = f * c.Fh;
                    c.Shell.Box("3c_concrete_panels", r.C + Vector3.up * (y + 0.12f + 0.4f), new Vector3(r.Hv * 2f + 0.3f, 0.25f, r.Hu * 2f + 0.3f), rot, conc, true);
                    c.Boxes.Add((r.C + Vector3.up * (y + 0.12f + 0.4f), new Vector3(r.Hv * 2f + 0.3f, 0.25f, r.Hu * 2f + 0.3f), rot));
                }
                c.Top = Mathf.Max(c.Top, colTop + 1.4f);
            }
        }

        // Steel tube scaffold around the footprint: standards every 2 m, ledgers every 2 m up, timber boards per lift.
        private static void Scaffold(V3Building c)
        {
            Color tube = V3Palette.C("grey.light"), board = V3Palette.C("wood.light");
            float h = c.H;
            foreach (V3Building.Edge e in c.Edges)
            {
                if (e.Len < 1f) continue;
                Quaternion rot = Quaternion.LookRotation(e.Dir);
                int n = Mathf.Max(1, Mathf.RoundToInt(e.Len / 2f));
                for (int k = 0; k <= n; k++)
                    for (int side = 0; side < 2; side++)
                        c.Shell.Box("6b_lightly_weathered_metal", V3Building.At(e, e.Len * k / n, h / 2f, side == 0 ? 0.3f : 1.3f), new Vector3(0.06f, h, 0.06f), rot, tube);
                for (float y = 2f; y <= h + 0.01f; y += 2f)
                {
                    for (int side = 0; side < 2; side++)
                        c.Shell.Box("6b_lightly_weathered_metal", V3Building.At(e, e.Len / 2f, y, side == 0 ? 0.3f : 1.3f), new Vector3(0.05f, 0.05f, e.Len), rot, tube);
                    c.Shell.Box("5a_wood_planks_fences", V3Building.At(e, e.Len / 2f, y - 0.05f, 0.8f), new Vector3(0.9f, 0.05f, e.Len), rot, board);
                }
                c.Boxes.Add((V3Building.At(e, e.Len / 2f, h / 2f, 0.8f), new Vector3(1.2f, h, e.Len), rot));
            }
            // The building inside: bare concrete walls behind the scaffold.
            c.WallCat = "3c_concrete_panels";
            c.Wall = V3Palette.C("panel");
            c.BuildShell(0.3f, false, 0f, 0f);
            c.Boxes.Add((Vector3.up * (h / 2f), new Vector3(1f, h, 1f), Quaternion.identity));
            c.Top = h + 0.5f;
        }

        // Fuel canopy: chalk roof slab with a mustard fascia on four columns (no walls).
        private static void Canopy(V3Building c)
        {
            Color white = V3Palette.C("chalk"), band = V3Palette.C("mustard");
            float h = Mathf.Max(4.5f, c.H + 1.2f);
            foreach (V3Building.Rect r in c.Rects)
            {
                Quaternion rot = Quaternion.LookRotation(r.U);
                c.Shell.Box("3b_plaster_stucco", r.C + Vector3.up * (h + 0.2f), new Vector3(r.Hv * 2f, 0.4f, r.Hu * 2f), rot, white, true);
                c.Big.Box("6a_painted_metal_panels", r.C + Vector3.up * (h - 0.1f), new Vector3(r.Hv * 2f + 0.05f, 0.3f, r.Hu * 2f + 0.05f), rot, band);
                for (int i = -1; i <= 1; i += 2)
                    for (int j = -1; j <= 1; j += 2)
                    {
                        Vector3 p = r.C + r.U * (i * r.Hu * 0.6f) + r.V * (j * r.Hv * 0.5f);
                        c.Shell.Box("3c_concrete_panels", p + Vector3.up * (h / 2f), new Vector3(0.45f, h, 0.45f), rot, white);
                        c.Boxes.Add((p + Vector3.up * (h / 2f), new Vector3(0.45f, h, 0.45f), rot));
                    }
                c.Shell.Box("3c_concrete_panels", r.C + Vector3.up * 0.08f, new Vector3(r.Hv * 1.2f, 0.16f, r.Hu * 1.2f), rot, V3Palette.C("paving"));
            }
            c.Top = h + 0.4f;
        }

        // The v12 generator's specials (wagon, church) converted to v3 categories and recipe colours.
        private static void FromProcedural(V3Building c, HeightModel hm)
        {
            LookBuilding b = c.B;
            BuildingResult res = ProceduralBuilding.Build(b, BuildingStyles.For(b), c.Pad, hm.LowestUnder(b.fp));
            Convert(res.Render, c.Shell, key => V3Convert.Slot(key, c));
            c.Top = Mathf.Max(c.H, res.Render.Vertices.Count > 0 ? MaxY(res.Render) : c.H);
        }

        private static float MaxY(MeshDraft d)
        {
            float y = 0f;
            foreach (Vector3 v in d.Vertices) y = Mathf.Max(y, v.y);
            return y;
        }

        // A v12 MeshDraft into a V3Mesh (slot keys -> category and palette colour).
        public static void Convert(MeshDraft draft, V3Mesh sink, System.Func<string, (string cat, Color colour)> map)
        {
            for (int s = 0; s < draft.Slots.Count; s++)
            {
                var (cat, col) = map(draft.Slots[s]);
                List<int> t = draft.Indices(s);
                for (int k = 0; k + 2 < t.Count; k += 3)
                {
                    int i0 = t[k], i1 = t[k + 1], i2 = t[k + 2];
                    sink.TriSmooth(cat, draft.Vertices[i0], draft.Vertices[i1], draft.Vertices[i2], draft.Normals[i0], draft.Normals[i1], draft.Normals[i2], col, col, col);
                }
            }
        }
    }

    // v12 slot keys ("mat/wall/oldtown|#C9A27E", "mat/road/asphalt", ...) -> style v3 category and palette colour.
    public static class V3Convert
    {
        public static (string cat, Color colour) Slot(string key, V3Building c = null)
        {
            string mat = key, hex = null;
            int bar = key.IndexOf('|');
            if (bar >= 0)
            {
                mat = key.Substring(0, bar);
                hex = key.Substring(bar + 1);
            }
            Color H(string swatch) => V3Palette.C(swatch);
            Color Hex(string fallback) => string.IsNullOrEmpty(hex) ? H(fallback) : LookConvert.Color(hex);
            if (mat.StartsWith("mat/wall/")) return c != null ? (c.WallCat, c.Wall) : ("3b_plaster_stucco", H("cream"));
            if (mat.StartsWith("mat/roof/"))
            {
                if (c != null) return (c.Roof == "flat" ? c.RoofCat : mat.EndsWith("tile") ? "4a_clay_roof_tiles" : c.RoofCat, c.RoofColour);
                return (mat.EndsWith("tile") ? "4a_clay_roof_tiles" : mat.EndsWith("flat") ? "4d_flat_bitumen_roof" : "4c_corrugated_metal", Hex("grey"));
            }
            switch (mat)
            {
                case "mat/trim": return ("3b_plaster_stucco", c != null ? c.Trim : H("chalk"));
                case "mat/plinth": return ("3c_concrete_panels", c != null ? c.Plinth : H("asphalt"));
                case "mat/glass": return ("glass", H("glass"));
                case "mat/glass_lit": return ("glass", H("glass.light"));
                case "mat/door": return ("5a_wood_planks_fences", c != null ? c.DoorColour : H("wood"));
                case "mat/door/metal": return ("6a_painted_metal_panels", H("grey"));
                case "mat/metal": return ("6b_lightly_weathered_metal", H("grey"));
                case "mat/iron": return ("6b_lightly_weathered_metal", H("ink"));
                case "mat/concrete": return ("3c_concrete_panels", H("panel"));
                case "mat/brick": return ("3a_brick", H("brick"));
                case "mat/stone": return ("3c_concrete_panels", H("paving"));
                case "mat/stucco": return ("3b_plaster_stucco", H("cream"));
                case "mat/wood": return ("5a_wood_planks_fences", H("wood"));
                case "mat/wood/dark": return ("5a_wood_planks_fences", H("wood.dark"));
                case "mat/dome": return ("4c_corrugated_metal", H("teal"));
                case "mat/gold": return ("6a_painted_metal_panels", H("mustard"));
                case "mat/rust": return ("6b_lightly_weathered_metal", H("brick.dark"));
                case "mat/white": return ("3b_plaster_stucco", H("chalk"));
                case "mat/red": return ("6a_painted_metal_panels", H("red"));
                case "mat/orange": return ("6a_painted_metal_panels", H("terracotta"));
                case "mat/canvas/red": return ("6a_painted_metal_panels", H("red"));
                case "mat/canvas/blue": return ("6a_painted_metal_panels", H("cobalt"));
                case "mat/sign": return ("6a_painted_metal_panels", Hex("chalk"));
                case "mat/road/asphalt":
                case "mat/road/junction": return ("2a_asphalt", H("asphalt"));
                case "mat/road/asphalt_worn": return ("2a_asphalt", H("asphalt.light"));
                case "mat/road/asphalt_elite": return ("2a_asphalt", H("asphalt.dark"));
                case "mat/road/dirt": return ("1b_dirt_road", H("wood.light"));
                case "mat/road/boardwalk": return ("5a_wood_planks_fences", H("wood.light"));
                case "mat/marking":
                case "mat/parking/line": return ("paint", H("chalk"));
                case "mat/marking/yellow": return ("paint", H("mustard"));
                case "mat/curb": return ("3c_concrete_panels", H("chalk.dark"));
                case "mat/curb/white": return ("3c_concrete_panels", H("chalk"));
                case "mat/ground/paving": return ("2b_sidewalk_tiles", H("paving"));
                case "mat/ground/cobble": return ("2c_cobblestone", H("paving.dark"));
                case "mat/ground/concrete": return ("3c_concrete_panels", H("grey.light"));
                case "mat/ground/asphalt": return ("2a_asphalt", H("asphalt"));
                case "mat/ground/rubber": return ("flat", H("coral"));
                case "mat/ground/gravel": return ("1d_gravel", H("grey.light"));
                case "mat/ground/sand": return ("1c_beach_sand", H("sand"));
                case "mat/bridge": return ("3c_concrete_panels", H("grey.light"));
                case "mat/ballast": return ("1d_gravel", H("grey"));
                case "mat/sleeper": return ("5a_wood_planks_fences", H("wood.dark"));
                case "mat/rail/steel": return ("6b_lightly_weathered_metal", H("grey.dark"));
                case "mat/elite/pier": return ("3c_concrete_panels", H("paving"));
                case "mat/hedge": return ("flat", H("leaf"));
            }
            if (mat.StartsWith("mat/sidewalk/")) return ("2b_sidewalk_tiles", mat.EndsWith("residential") || mat.EndsWith("industrial") ? H("grey.light") : H("paving"));
            if (mat.StartsWith("mat/neon/")) return ("flat", Hex("mustard"));
            if (mat.StartsWith("mat/fence/")) return ("5a_wood_planks_fences", H("wood"));
            return ("flat", Hex("grey"));
        }
    }
}
