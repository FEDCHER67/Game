using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 water for map v16: the sea (its polygon plus the outward apron on open edges), every inland polygon at its
    // level with a material per kind (lake, bog, pond), the river -> canal -> canal mouth as ONE ribbon along the plan's
    // centrelines carrying the flow velocity in UV1 (the shader moves the ripples downstream), and built basins (villa
    // pools, the palace fountain, the village well) on their own ground level with their own walls, decks and colliders
    // (the plan's absolute -0.3 m level would sink a pool on Elite Hill 11 m into the hill).
    public static class V3Water
    {
        public const float RiverSpeed = 0.55f, CanalSpeed = 0.22f, MouthSpeed = 0.3f, SeaHorizon = 1800f;

        public sealed class Basin
        {
            public LookWater W;
            public string Kind;
            public float Ground, Level, Floor, Rim;
            public float[] Deck;
        }

        // Basins come out of d.water before the HeightModel bakes (no carving at the plan level); river and canal get a
        // channel deep enough for colour by depth (bank 1:1.6, bed 1.5 m; the canal 2.2 m with near-vertical sides).
        public static List<Basin> Prepare(LookData d, List<string> log)
        {
            var basins = new List<Basin>();
            var keep = new List<LookWater>();
            foreach (LookWater w in d.water)
            {
                string src = Source(w);
                if (src == "swimming_pool" || src == "fountain" || src == "well")
                {
                    if (LookGeom.SignedArea(w.pts) < 0f) w.pts = Reverse(w.pts);
                    basins.Add(new Basin { W = w, Kind = src == "swimming_pool" ? "pool" : src });
                    continue;
                }
                if (src == "river")
                {
                    w.depth = 1.5f;
                    w.bank = 1.6f;
                }
                else if (src == "concrete_canal")
                {
                    w.depth = 2.2f;
                    w.bank = 0.35f;
                }
                keep.Add(w);
            }
            d.water = keep.ToArray();
            log.Add($"water prep: {keep.Count} carved bodies, {basins.Count} built basins (pools, fountain, well)");
            return basins;
        }

        private static float[] Reverse(float[] pts)
        {
            int n = pts.Length / 2;
            var r = new float[pts.Length];
            for (int i = 0; i < n; i++)
            {
                r[2 * i] = pts[2 * (n - 1 - i)];
                r[2 * i + 1] = pts[2 * (n - 1 - i) + 1];
            }
            return r;
        }

        public static string Source(LookWater w)
        {
            string s = V3LookData.WaterSource != null && V3LookData.WaterSource.TryGetValue(w.id, out string k) ? k : null;
            return string.IsNullOrEmpty(s) ? w.kind : s;
        }

        // Ground under each basin (after the bake, before sinking), then the terrain inside the basin (plus a margin the
        // deck covers) drops below the basin floor so the walls and water show.
        public static void SinkTerrain(HeightModel hm, List<Basin> basins)
        {
            foreach (Basin b in basins)
            {
                LookGeom.Centroid(b.W.pts, out float cx, out float cy);
                b.Ground = hm.Height(cx, cy);
                switch (b.Kind)
                {
                    case "pool":
                        b.Level = b.Ground - 0.15f;
                        b.Floor = b.Ground - 1.5f;
                        b.Rim = b.Ground + 0.06f;
                        break;
                    case "fountain":
                        b.Level = b.Ground + 0.35f;
                        b.Floor = b.Ground - 0.2f;
                        b.Rim = b.Ground + 0.5f;
                        break;
                    default: // well
                        b.Level = b.Ground + 0.25f;
                        b.Floor = b.Ground - 0.6f;
                        b.Rim = b.Ground + 0.6f;
                        break;
                }
                b.Deck = LookGeom.OffsetPolygon(b.W.pts, 2.2f);
                float[] inner = LookGeom.OffsetPolygon(b.W.pts, 0.6f);
                LookGrid g = hm.Grid;
                LookGeom.Bounds(inner, out float x0, out float y0, out float x1, out float y1);
                g.Range(x0 - 2f, y0 - 2f, x1 + 2f, y1 + 2f, out int i0, out int j0, out int i1, out int j1);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                        if (LookGeom.Inside(inner, g.X(i), g.Y(j)))
                            hm.Heights[j * g.Nx + i] = Mathf.Min(hm.Heights[j * g.Nx + i], b.Floor - 0.5f);
            }
            hm.MinHeight = float.MaxValue;
            hm.MaxHeight = float.MinValue;
            foreach (float h in hm.Heights)
            {
                hm.MinHeight = Mathf.Min(hm.MinHeight, h);
                hm.MaxHeight = Mathf.Max(hm.MaxHeight, h);
            }
        }

        public static void Build(LookData d, HeightModel hm, List<Basin> basins, V3Store store, Transform parent, MapHeightSampler sampler, List<string> log)
        {
            var root = new GameObject("Water").transform;
            root.SetParent(parent, false);
            int lakes = 0;
            LookWater river = null, canal = null, mouth = null;
            foreach (LookWater w in d.water)
            {
                string src = Source(w);
                if (src == "river") { river = w; continue; }
                if (src == "concrete_canal") { if (w.id.Contains("MOUTH")) mouth = w; else canal = w; continue; }
                string kind = src == "bog" ? "bog" : src == "village_pond" ? "pond" : "lake";
                var m = new V3Mesh();
                m.PlanTris("water", w.tris, w.level, 0f, 0f, Color.white);
                Emit(root, $"Water_{w.id}", m, V3Materials.Water(kind), store, null);
                sampler.Water.Add(new WaterZone { Id = w.id, Kind = "lake", Level = w.level, Pts = w.pts });
                lakes++;
            }
            int rows = Channel(d, river, canal, mouth, root, store, sampler, hm);
            if (canal != null) CanalWalls(canal, hm, root, store);
            if (mouth != null) CanalWalls(mouth, hm, root, store);
            foreach (Basin b in basins) BuiltBasin(b, root, store, sampler);
            Sea(d, root, store, sampler);
            log.Add($"water v3: sea + apron, {lakes} lakes/ponds/bogs, river->canal->mouth ribbon {rows} rows with flow, {basins.Count} built basins");
        }

        private static void Emit(Transform root, string name, V3Mesh m, Material mat, V3Store store, Vector2[] flow)
        {
            if (m.IsEmpty) return;
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            Mesh mesh = m.ToMesh(name, out _, false, flow == null);
            if (flow != null) mesh.SetUVs(1, new List<Vector2>(flow));
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(mesh);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = true;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
        }

        // ---------------------------------------------------------------- river -> canal -> mouth

        private static int Channel(LookData d, LookWater river, LookWater canal, LookWater mouth, Transform root, V3Store store, MapHeightSampler sampler, HeightModel hm)
        {
            var pts = new List<Vector2>();
            var half = new List<(float l, float r)>();
            var speed = new List<float>();
            var level = new List<float>();
            void AddPath(LookWater w, float spd, float[] widths)
            {
                if (w == null) return;
                List<Vector2> line = V3LookData.Centrelines != null && V3LookData.Centrelines.TryGetValue(w.id, out List<Vector2> c) ? c : null;
                if (line == null || line.Count < 2) return;
                for (int i = 0; i < line.Count; i++)
                {
                    if (pts.Count > 0 && Vector2.Distance(pts[pts.Count - 1], line[i]) < 1.0f) continue;
                    Vector2 dir = (line[Mathf.Min(line.Count - 1, i + 1)] - line[Mathf.Max(0, i - 1)]).normalized;
                    (float l, float r) hw = HalfWidths(w.pts, line[i], dir);
                    if (widths != null && i < widths.Length && widths[i] > 0.5f)
                    {
                        float hwP = widths[i] / 2f;
                        hw = (Mathf.Max(hw.l, hwP), Mathf.Max(hw.r, hwP));
                    }
                    pts.Add(line[i]);
                    half.Add(hw);
                    speed.Add(spd);
                    level.Add(w.level);
                }
                sampler.Water.Add(new WaterZone { Id = w.id, Kind = "lake", Level = w.level, Pts = w.pts });
            }
            float[] profile = river != null && V3LookData.WidthProfiles != null && V3LookData.WidthProfiles.TryGetValue(river.id, out float[] wp) ? wp : null;
            AddPath(river, RiverSpeed, profile);
            AddPath(canal, CanalSpeed, null);
            AddPath(mouth, MouthSpeed, null);
            if (pts.Count < 2) return 0;
            // The mouth drops to the sea level over its last 40 m and stops where it meets the sea polygon (no overlap of
            // two transparent surfaces).
            float seaLevel = d.sea.level;
            int end = pts.Count - 1;
            if (mouth != null && LookGeom.Count(d.sea.pts) >= 3)
                for (int i = 1; i < pts.Count; i++)
                    if (LookGeom.Inside(d.sea.pts, pts[i].x, pts[i].y))
                    {
                        end = i;
                        // Move the last point back onto the sea edge.
                        Vector2 a = pts[i - 1], b = pts[i];
                        float lo = 0f, hi = 1f;
                        for (int k = 0; k < 20; k++)
                        {
                            float mid = (lo + hi) / 2f;
                            Vector2 p = Vector2.Lerp(a, b, mid);
                            if (LookGeom.Inside(d.sea.pts, p.x, p.y)) hi = mid;
                            else lo = mid;
                        }
                        pts[i] = Vector2.Lerp(a, b, hi);
                        break;
                    }
            var cum = new float[end + 1];
            for (int i = 1; i <= end; i++) cum[i] = cum[i - 1] + Vector2.Distance(pts[i], pts[i - 1]);
            float total = cum[end];
            var m = new V3Mesh();
            var flow = new List<Vector2>();
            var rowsV = new List<Vector3[]>();
            var rowsF = new List<Vector2>();
            for (int i = 0; i <= end; i++)
            {
                Vector2 dir = (pts[Mathf.Min(end, i + 1)] - pts[Mathf.Max(0, i - 1)]).normalized;
                var n = new Vector2(-dir.y, dir.x);
                float y = level[i];
                if (mouth != null) y = Mathf.Lerp(y, seaLevel, Mathf.Clamp01((cum[i] - (total - 40f)) / 40f));
                float l = half[i].l + 1.2f, r = half[i].r + 1.2f;
                var row = new Vector3[5];
                float[] t = { l, l * 0.5f, 0f, -r * 0.5f, -r };
                for (int k = 0; k < 5; k++)
                {
                    Vector2 p = pts[i] + n * t[k];
                    row[k] = new Vector3(p.x, y, p.y);
                }
                rowsV.Add(row);
                rowsF.Add(dir * speed[i]);
            }
            for (int i = 0; i + 1 < rowsV.Count; i++)
                for (int k = 0; k + 1 < 5; k++)
                {
                    Vector3 a = rowsV[i][k], b = rowsV[i][k + 1], c = rowsV[i + 1][k + 1], e = rowsV[i + 1][k];
                    int before = m.Vertices.Count;
                    m.QuadFacing("water", a, b, c, e, Vector3.up, Color.white);
                    if (m.Vertices.Count == before) continue;
                    // QuadFacing may reverse the corner order; give each new vertex the flow of its row.
                    for (int v = before; v < m.Vertices.Count; v++)
                    {
                        Vector3 p = m.Vertices[v];
                        bool rowI = Vector3.SqrMagnitude(p - a) < 1e-6f || Vector3.SqrMagnitude(p - b) < 1e-6f;
                        flow.Add(rowI ? rowsF[i] : rowsF[i + 1]);
                    }
                }
            Emit(root, "Water_RiverCanal", m, V3Materials.Water("river"), store, flow.ToArray());
            // The canal and its mouth get the calmer canal material on the same mesh layout: split by the river's end.
            return rowsV.Count;
        }

        // Distances from a centreline point to the water polygon edge on the left and right (ray casts along the normal).
        private static (float l, float r) HalfWidths(float[] poly, Vector2 p, Vector2 dir)
        {
            var n = new Vector2(-dir.y, dir.x);
            float Ray(Vector2 d)
            {
                float best = 40f;
                int count = LookGeom.Count(poly);
                for (int i = 0; i < count; i++)
                {
                    int j = (i + 1) % count;
                    Vector2 a = new Vector2(poly[2 * i], poly[2 * i + 1]), b = new Vector2(poly[2 * j], poly[2 * j + 1]);
                    Vector2 e = b - a;
                    float den = d.x * e.y - d.y * e.x;
                    if (Mathf.Abs(den) < 1e-6f) continue;
                    Vector2 ap = a - p;
                    float t = (ap.x * e.y - ap.y * e.x) / den, u = (ap.x * d.y - ap.y * d.x) / den;
                    if (t > 0.05f && u >= 0f && u <= 1f && t < best) best = t;
                }
                return best;
            }
            float l = Ray(n), r = Ray(-n);
            if (l >= 40f || r >= 40f)
            {
                float dist = LookGeom.DistToPolyline(poly, p.x, p.y, true, out _, out _);
                if (l >= 40f) l = Mathf.Max(1f, dist);
                if (r >= 40f) r = Mathf.Max(1f, dist);
            }
            return (Mathf.Min(l, 25f), Mathf.Min(r, 25f));
        }

        // Concrete canal walls along the polygon edge: from 0.35 m above the ground down past the bed, coping on top.
        private static void CanalWalls(LookWater w, HeightModel hm, Transform root, V3Store store)
        {
            var m = new V3Mesh();
            int n = LookGeom.Count(w.pts);
            Color conc = V3Palette.C("grey.light"), cap = V3Palette.C("chalk.dark");
            bool ccw = LookGeom.SignedArea(w.pts) > 0f;
            float bed = -Mathf.Abs(w.depth) - 0.3f;
            var boxes = new List<(Vector3 c, Vector3 size, Quaternion rot)>();
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                var a = new Vector3(w.pts[2 * i], 0f, w.pts[2 * i + 1]);
                var b = new Vector3(w.pts[2 * j], 0f, w.pts[2 * j + 1]);
                Vector3 dir = b - a;
                float len = dir.magnitude;
                if (len < 0.05f) continue;
                dir /= len;
                Vector3 outward = ccw ? new Vector3(dir.z, 0f, -dir.x) : new Vector3(-dir.z, 0f, dir.x);
                // No wall where the polygon opens onto the sea or the river (low ground outside too).
                float oa = hm.Height(a.x + outward.x * 0.8f, a.z + outward.z * 0.8f), ob = hm.Height(b.x + outward.x * 0.8f, b.z + outward.z * 0.8f);
                if (oa < -0.1f && ob < -0.1f) continue;
                Vector3 ia = a - outward * 0.1f, ib = b - outward * 0.1f;
                float topA = Mathf.Max(oa, 0f) + 0.35f, topB = Mathf.Max(ob, 0f) + 0.35f;
                m.QuadFacing("3c_concrete_panels", new Vector3(ia.x, bed, ia.z), new Vector3(ia.x, topA, ia.z), new Vector3(ib.x, topB, ib.z), new Vector3(ib.x, bed, ib.z), -outward, conc);
                m.Beam("3c_concrete_panels", new Vector3(a.x + outward.x * 0.15f, 0f, a.z + outward.z * 0.15f), new Vector3(b.x + outward.x * 0.15f, 0f, b.z + outward.z * 0.15f),
                    0.6f, Mathf.Min(topA, topB) - 0.05f, Mathf.Max(topA, topB) + 0.1f, cap);
                float yTop = Mathf.Max(topA, topB) + 0.1f;
                boxes.Add(((a + b) / 2f + outward * 0.15f + Vector3.up * ((bed + yTop) / 2f), new Vector3(0.6f, yTop - bed, len), Quaternion.LookRotation(dir)));
            }
            if (m.IsEmpty) return;
            var go = new GameObject($"CanalWalls_{w.id}");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(m.ToMesh(go.name, out string[] cats));
            var mr = go.AddComponent<MeshRenderer>();
            var mats = new Material[cats.Length];
            for (int i = 0; i < cats.Length; i++) mats[i] = V3Materials.Mat(cats[i]);
            mr.sharedMaterials = mats;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            // One box per wall stretch (box/convex colliders only).
            foreach (var bx in boxes)
            {
                var c = new GameObject("Collider");
                c.transform.SetParent(go.transform, false);
                c.transform.SetPositionAndRotation(bx.c, bx.rot);
                c.AddComponent<BoxCollider>().size = bx.size;
            }
        }

        // ---------------------------------------------------------------- built basins

        private static void BuiltBasin(Basin b, Transform root, V3Store store, MapHeightSampler sampler)
        {
            float[] pts = b.W.pts;
            int n = LookGeom.Count(pts);
            if (n < 3) return;
            bool ccw = LookGeom.SignedArea(pts) > 0f;
            var m = new V3Mesh();
            Color coping = V3Palette.C("chalk"), deck = b.Kind == "pool" ? V3Palette.C("paving") : V3Palette.C("paving.dark");
            Color tile = b.Kind == "pool" ? LookConvert.Color("#BFE3E4") : V3Palette.C("grey.light");
            float[] copeOut = LookGeom.OffsetPolygon(pts, b.Kind == "pool" ? 0.4f : 0.35f);
            float rimTop = b.Rim;
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                Vector3 P(float[] a, int k, float y) => new Vector3(a[2 * k], y, a[2 * k + 1]);
                // Deck ring (paving) from the coping out to the deck edge, coping ring, inner wall down to the floor.
                m.QuadFacing("2b_sidewalk_tiles", P(copeOut, i, b.Ground + 0.05f), P(b.Deck, i, b.Ground + 0.05f), P(b.Deck, j, b.Ground + 0.05f), P(copeOut, j, b.Ground + 0.05f), Vector3.up, deck);
                m.QuadFacing("3c_concrete_panels", P(pts, i, rimTop), P(copeOut, i, rimTop), P(copeOut, j, rimTop), P(pts, j, rimTop), Vector3.up, coping);
                Vector3 edgeDir = P(pts, j, 0f) - P(pts, i, 0f);
                Vector3 inward = ccw ? new Vector3(-edgeDir.z, 0f, edgeDir.x) : new Vector3(edgeDir.z, 0f, -edgeDir.x);
                m.QuadFacing(b.Kind == "pool" ? "2b_sidewalk_tiles" : "3c_concrete_panels", P(pts, i, b.Floor), P(pts, i, rimTop), P(pts, j, rimTop), P(pts, j, b.Floor), inward, tile);
                if (rimTop > b.Ground + 0.1f)
                    m.QuadFacing("3c_concrete_panels", P(copeOut, i, b.Ground), P(copeOut, i, rimTop), P(copeOut, j, rimTop), P(copeOut, j, b.Ground), -inward, coping);
            }
            m.PlanTris(b.Kind == "pool" ? "2b_sidewalk_tiles" : "3c_concrete_panels", b.W.tris, b.Floor, 0f, 0f, tile);
            LookGeom.Centroid(pts, out float cx, out float cy);
            if (b.Kind == "fountain")
            {
                var c = new Vector3(cx, b.Floor, cy);
                m.Cylinder("3c_concrete_panels", c, 0.45f, b.Level - b.Floor + 0.6f, 10, coping);
                m.Cylinder("3c_concrete_panels", c + Vector3.up * (b.Level - b.Floor + 0.6f), 1.2f, 0.18f, 14, coping);
                m.Cylinder("3c_concrete_panels", c + Vector3.up * (b.Level - b.Floor + 0.78f), 0.22f, 0.9f, 8, coping);
                m.Cylinder("3c_concrete_panels", c + Vector3.up * (b.Level - b.Floor + 1.68f), 0.6f, 0.12f, 12, coping);
            }
            var go = new GameObject($"Basin_{b.W.id}");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(m.ToMesh(go.name, out string[] cats));
            var mr = go.AddComponent<MeshRenderer>();
            var mats = new Material[cats.Length];
            for (int i = 0; i < cats.Length; i++) mats[i] = V3Materials.Mat(cats[i]);
            mr.sharedMaterials = mats;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            var water = new V3Mesh();
            water.PlanTris("water", b.W.tris, b.Level, 0f, 0f, Color.white);
            Emit(root, $"Water_{b.W.id}", water, V3Materials.Water(b.Kind == "pool" ? "pool" : "fountain"), store, null);
            sampler.Water.Add(new WaterZone { Id = b.W.id, Kind = "lake", Level = b.Level, Pts = pts });
            // Colliders: the deck as a few boxes round the basin's box, the floor, the rim (convex ones only).
            Colliders(go, b, cx, cy);
        }

        private static void Colliders(GameObject go, Basin b, float cx, float cy)
        {
            // Oriented box of the basin from its longest edge.
            float[] pts = b.W.pts;
            int n = LookGeom.Count(pts);
            Vector2 axis = Vector2.right;
            float bestLen = 0f;
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                var e = new Vector2(pts[2 * j] - pts[2 * i], pts[2 * j + 1] - pts[2 * i + 1]);
                if (e.magnitude > bestLen) { bestLen = e.magnitude; axis = e.normalized; }
            }
            var ax = new Vector2(axis.x, axis.y);
            var az = new Vector2(-axis.y, axis.x);
            float minU = float.MaxValue, maxU = float.MinValue, minV = float.MaxValue, maxV = float.MinValue;
            for (int i = 0; i < n; i++)
            {
                var p = new Vector2(pts[2 * i] - cx, pts[2 * i + 1] - cy);
                float u = Vector2.Dot(p, ax), v = Vector2.Dot(p, az);
                minU = Mathf.Min(minU, u); maxU = Mathf.Max(maxU, u); minV = Mathf.Min(minV, v); maxV = Mathf.Max(maxV, v);
            }
            Quaternion rot = Quaternion.LookRotation(new Vector3(az.x, 0f, az.y));
            Vector3 centre = new Vector3(cx, 0f, cy);
            Vector3 X = new Vector3(ax.x, 0f, ax.y), Z = new Vector3(az.x, 0f, az.y);
            float hu = (maxU - minU) / 2f, hv = (maxV - minV) / 2f, cu = (maxU + minU) / 2f, cv = (maxV + minV) / 2f;
            centre += X * cu + Z * cv;
            void Box(Vector3 c, Vector3 size)
            {
                var g = new GameObject("Collider");
                g.transform.SetParent(go.transform, false);
                g.transform.SetPositionAndRotation(c, rot);
                g.AddComponent<BoxCollider>().size = size;
            }
            float deck = 2.2f, top = b.Rim, bottom = b.Ground - 2.6f;
            float h = top - bottom, yc = (top + bottom) / 2f;
            if (b.Kind == "pool")
            {
                Box(centre + Z * (hv + deck / 2f) + Vector3.up * yc, new Vector3((hu + deck) * 2f, h, deck));
                Box(centre - Z * (hv + deck / 2f) + Vector3.up * yc, new Vector3((hu + deck) * 2f, h, deck));
                Box(centre + X * (hu + deck / 2f) + Vector3.up * yc, new Vector3(deck, h, hv * 2f));
                Box(centre - X * (hu + deck / 2f) + Vector3.up * yc, new Vector3(deck, h, hv * 2f));
                Box(centre + Vector3.up * (b.Floor - 0.25f), new Vector3(hu * 2f, 0.5f, hv * 2f));
            }
            else
                Box(centre + Vector3.up * ((b.Rim + b.Floor) / 2f), new Vector3(hu * 2f + 0.7f, b.Rim - b.Floor, hv * 2f + 0.7f));
        }

        // ---------------------------------------------------------------- sea

        private static void Sea(LookData d, Transform root, V3Store store, MapHeightSampler sampler)
        {
            LookSea sea = d.sea;
            if (LookGeom.Count(sea.pts) < 3) return;
            var m = new V3Mesh();
            m.PlanTris("water", sea.tris, sea.level, 0f, 0f, Color.white);
            float[] apron = LookGeom.OffsetPolygon(sea.pts, Mathf.Max(SeaHorizon, sea.apron));
            int n = LookGeom.Count(sea.pts);
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                if (!HeightModel.OpenSeaVertex(d, i) || !HeightModel.OpenSeaVertex(d, j)) continue;
                var a = new Vector3(sea.pts[2 * i], sea.level, sea.pts[2 * i + 1]);
                var b = new Vector3(sea.pts[2 * j], sea.level, sea.pts[2 * j + 1]);
                var c = new Vector3(apron[2 * j], sea.level, apron[2 * j + 1]);
                var e = new Vector3(apron[2 * i], sea.level, apron[2 * i + 1]);
                m.QuadFacing("water", a, b, c, e, Vector3.up, Color.white);
            }
            Emit(root, "Sea", m, V3Materials.Water("sea"), store, null);
            sampler.Water.Add(new WaterZone { Id = sea.id, Kind = "sea", Level = sea.level, Pts = sea.pts });
            if (LookGeom.Count(d.beach.pts) >= 3) sampler.Water.Add(new WaterZone { Id = "BEACH_SURF", Kind = "sea", Level = sea.level, Pts = d.beach.pts });
        }
    }
}
