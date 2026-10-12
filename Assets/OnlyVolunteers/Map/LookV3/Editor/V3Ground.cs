using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 ground pieces: roads, junctions, sidewalks, plazas, parking, bridges from the shared RoadMeshBuilder
    // (geometry unchanged) re-filed by surface type (asphalt, sidewalk tiles, cobblestone, dirt...) and merged per
    // district x 160 m cell; the plan's typed fences (blue sheet, concrete, high fence with barbed wire, low rail,
    // military, palace railing) with gate gaps and one box collider per bay; retaining walls (box colliders); the
    // invisible boundary blockers.
    public static class V3Ground
    {
        private const float Cell = 160f;

        public static void Roads(LookData d, HeightModel hm, MapHeightSampler sampler, V3Store store, Transform parent, List<string> log)
        {
            List<LookPiece> pieces = RoadMeshBuilder.Build(d, hm.Height, sampler.Decks);
            var surfaces = new Dictionary<string, string>();
            foreach (LookRoad r in d.roads) surfaces[r.id] = r.surface;
            var render = new SortedDictionary<string, V3Mesh>();
            int tris = 0;
            foreach (LookPiece p in pieces)
            {
                string key = $"{(string.IsNullOrEmpty(p.District) ? "common" : p.District)}_{Mathf.FloorToInt(p.Centre.x / Cell)}_{Mathf.FloorToInt(p.Centre.z / Cell)}";
                if (!render.TryGetValue(key, out V3Mesh m)) render[key] = m = new V3Mesh();
                string name = p.Name ?? "";
                bool paving = surfaces.TryGetValue(name, out string surf) && surf == "paving";
                bool plaza = name.StartsWith("Ground_") && name.Contains("plaza");
                MeshDraft draft = p.Draft;
                for (int s = 0; s < draft.Slots.Count; s++)
                {
                    var (cat, col) = V3Convert.Slot(draft.Slots[s]);
                    if (paving && cat == "2a_asphalt") { cat = "2b_sidewalk_tiles"; col = V3Palette.C("paving"); }
                    if (plaza && cat == "2b_sidewalk_tiles") { cat = "2c_cobblestone"; col = V3Palette.C("paving.dark"); }
                    List<int> t = draft.Indices(s);
                    for (int k = 0; k + 2 < t.Count; k += 3)
                    {
                        int a = t[k], b = t[k + 1], c = t[k + 2];
                        m.TriUv(cat, draft.Vertices[a], draft.Vertices[b], draft.Vertices[c], draft.Normals[a], draft.Normals[b], draft.Normals[c],
                            draft.Uvs[a], draft.Uvs[b], draft.Uvs[c], col);
                    }
                }
            }
            var root = new GameObject("Roads").transform;
            root.SetParent(parent, false);
            foreach (var kv in render)
            {
                if (kv.Value.IsEmpty) continue;
                var go = new GameObject("Road_" + kv.Key);
                go.transform.SetParent(root, false);
                tris += kv.Value.TriangleCount;
                go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(kv.Value.ToMesh(go.name, out string[] cats));
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterials = Mats(cats);
                mr.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            }
            int boxes = WalkableBoxes(d, hm, sampler, root);
            log.Add($"roads v3: {pieces.Count} pieces in {render.Count} cells, {tris} tris; {boxes} box colliders (sidewalks, bridge decks and parapets)");
        }

        // Box colliders instead of the v12 look's per-cell mesh colliders (Fedya's perf rule: box/convex colliders only):
        // a sidewalk slab per 2 m stretch, pitched along the ground, top at the kerb height; per bridge deck stretch the
        // deck slab and both parapets. Sidewalk slabs stay off the carriageway like the v12 kerb (road side +-0).
        private static int WalkableBoxes(LookData d, HeightModel hm, MapHeightSampler sampler, Transform parent)
        {
            var root = new GameObject("WalkableColliders").transform;
            root.SetParent(parent, false);
            int count = 0;
            void Box(Vector3 a, Vector3 b, float width, float top, float depth)
            {
                Vector3 dir = b - a;
                float len = dir.magnitude;
                if (len < 0.05f) return;
                var go = new GameObject("Collider");
                go.transform.SetParent(root, false);
                Vector3 up = Vector3.Cross(dir / len, Vector3.Cross(Vector3.up, dir / len)).normalized;
                if (up.y < 0f) up = -up;
                Vector3 centre = (a + b) / 2f + Vector3.up * (top - depth / 2f);
                go.transform.SetPositionAndRotation(centre, Quaternion.LookRotation(dir / len, up));
                go.AddComponent<BoxCollider>().size = new Vector3(width, depth, len + 0.08f);
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
                count++;
            }
            foreach (LookSidewalk sw in d.sidewalks)
            {
                if (LookGeom.Count(sw.pts) < 2) continue;
                float[] line = LookGeom.Resample(sw.pts, 2f, out _);
                int n = LookGeom.Count(line);
                float curb = Mathf.Clamp(sw.curb, 0.04f, 0.12f);
                for (int i = 0; i + 1 < n; i++)
                {
                    var a = new Vector3(line[2 * i], 0f, line[2 * i + 1]);
                    var b = new Vector3(line[2 * i + 2], 0f, line[2 * i + 3]);
                    a.y = hm.Height(a.x, a.z);
                    b.y = hm.Height(b.x, b.z);
                    Box(a, b, sw.w + 0.1f, curb, 0.5f);
                }
            }
            foreach (BridgeDeck deck in sampler.Decks)
            {
                float[] line = LookGeom.Resample(deck.Centreline(), 2f, out float[] arc);
                int n = LookGeom.Count(line);
                if (n < 2) continue;
                float total = Mathf.Max(0.01f, arc[n - 1]);
                for (int i = 0; i + 1 < n; i++)
                {
                    var a = new Vector3(line[2 * i], Mathf.Lerp(deck.HeightA, deck.HeightB, arc[i] / total), line[2 * i + 1]);
                    var b = new Vector3(line[2 * i + 2], Mathf.Lerp(deck.HeightA, deck.HeightB, arc[i + 1] / total), line[2 * i + 3]);
                    Box(a, b, deck.HalfWidth * 2f + 0.6f, 0f, 0.7f);
                    Vector3 side = Vector3.Cross(Vector3.up, (b - a).normalized) * deck.HalfWidth;
                    for (int s = -1; s <= 1; s += 2)
                        Box(a + side * s, b + side * s, 0.3f, 0.7f, 0.7f);
                }
            }
            return count;
        }

        public static Material[] Mats(string[] cats)
        {
            var mats = new Material[cats.Length];
            for (int i = 0; i < cats.Length; i++) mats[i] = V3Materials.Mat(cats[i]);
            return mats;
        }

        // ---------------------------------------------------------------- fences

        private sealed class FenceStyle
        {
            public float H, Bay = 2.6f, Post = 0.12f, Panel = 0.05f;
            public string PanelCat, PostCat;
            public Color PanelColour, PostColour;
            public bool Bars, Rails, Barbed, Solid, Plinth;
        }

        private static FenceStyle Style(string kind)
        {
            switch (kind)
            {
                case "fence_profiled_sheet_blue":
                    return new FenceStyle { H = 2.0f, PanelCat = "4c_corrugated_metal", PanelColour = V3Palette.C("cobalt"), PostCat = "6b_lightly_weathered_metal", PostColour = V3Palette.C("grey.dark"), Solid = true };
                case "concrete_port_yard_with_fence":
                    return new FenceStyle { H = 2.4f, Bay = 3f, Post = 0.25f, Panel = 0.15f, PanelCat = "3c_concrete_panels", PanelColour = V3Palette.C("grey.light"), PostCat = "3c_concrete_panels", PostColour = V3Palette.C("grey"), Solid = true, Barbed = true };
                case "military_fence":
                    return new FenceStyle { H = 2.4f, Bay = 3f, Post = 0.25f, Panel = 0.15f, PanelCat = "3c_concrete_panels", PanelColour = V3Palette.C("panel"), PostCat = "3c_concrete_panels", PostColour = V3Palette.C("grey"), Solid = true, Barbed = true };
                case "high_fence_with_barbed_wire":
                    return new FenceStyle { H = 2.4f, Bay = 2.8f, Post = 0.14f, PanelCat = "6b_lightly_weathered_metal", PanelColour = V3Palette.C("ink"), PostCat = "6b_lightly_weathered_metal", PostColour = V3Palette.C("ink"), Bars = true, Barbed = true, Plinth = true };
                case "palace_lawn_with_fence":
                    return new FenceStyle { H = 1.1f, Bay = 2.4f, Post = 0.12f, PanelCat = "6b_lightly_weathered_metal", PanelColour = V3Palette.C("ink"), PostCat = "3c_concrete_panels", PostColour = V3Palette.C("chalk"), Bars = true, Plinth = true };
                // v17 yard fences (inside districts / common-land properties; never on district borders).
                case "fence_wood_yard":
                    return new FenceStyle { H = 1.8f, Bay = 2.4f, Post = 0.12f, Panel = 0.06f, PanelCat = "5a_wood_planks_fences", PanelColour = V3Palette.C("wood"), PostCat = "5a_wood_planks_fences", PostColour = V3Palette.C("wood.dark"), Solid = true };
                case "fence_low_garden":
                    return new FenceStyle { H = 0.9f, Bay = 2.2f, Post = 0.06f, PanelCat = "6a_painted_metal_panels", PanelColour = V3Palette.C("teal"), PostCat = "6a_painted_metal_panels", PostColour = V3Palette.C("teal"), Bars = true };
                case "fence_kindergarten":
                    return new FenceStyle { H = 1.5f, Bay = 2.5f, Post = 0.08f, PanelCat = "6a_painted_metal_panels", PanelColour = V3Palette.C("mint"), PostCat = "6a_painted_metal_panels", PostColour = V3Palette.C("grey.dark"), Bars = true, Plinth = true };
                case "fence_chainlink":
                    return new FenceStyle { H = 2.2f, Bay = 3.0f, Post = 0.08f, PanelCat = "6b_lightly_weathered_metal", PanelColour = V3Palette.C("grey"), PostCat = "6b_lightly_weathered_metal", PostColour = V3Palette.C("grey.dark"), Bars = true };
                case "fence_dacha":
                    return new FenceStyle { H = 1.3f, Bay = 2.4f, Post = 0.1f, PanelCat = "5a_wood_planks_fences", PanelColour = V3Palette.C("wood.light"), PostCat = "5a_wood_planks_fences", PostColour = V3Palette.C("wood"), Rails = true };
                default: // low_perimeter_fence_open_gates
                    return new FenceStyle { H = 1.0f, Bay = 2.4f, Post = 0.12f, PanelCat = "5a_wood_planks_fences", PanelColour = V3Palette.C("wood.light"), PostCat = "5a_wood_planks_fences", PostColour = V3Palette.C("wood"), Rails = true };
            }
        }

        public static void Fences(HeightModel hm, V3Store store, Transform parent, List<string> log)
        {
            if (V3LookData.Fences == null || V3LookData.Fences.Count == 0) return;
            var root = new GameObject("Fences").transform;
            root.SetParent(parent, false);
            int bays = 0, colliders = 0;
            // v17 fences (ids with "_v17_", hundreds of short runs) merge per 80 m cell and shadow mode; the v16 runs stay one
            // object each as before.
            var cells = new Dictionary<string, (V3Mesh m, Transform t, bool solid)>();
            foreach (V3LookData.Fence f in V3LookData.Fences)
            {
                FenceStyle st = Style(f.Kind);
                bool merged = f.Id.Contains("_v17_");
                V3Mesh m;
                GameObject go;
                if (merged)
                {
                    string ck = $"{Mathf.FloorToInt(f.Line[0].x / 80f)}_{Mathf.FloorToInt(f.Line[0].y / 80f)}_{(st.Solid ? 1 : 0)}";
                    if (!cells.TryGetValue(ck, out var cell))
                    {
                        var cgo = new GameObject("Fences_v17_" + ck);
                        cgo.transform.SetParent(root, false);
                        cells[ck] = cell = (new V3Mesh(), cgo.transform, st.Solid);
                    }
                    m = cell.m;
                    go = new GameObject("Fence_" + f.Id);
                    go.transform.SetParent(cell.t, false);
                }
                else
                {
                    m = new V3Mesh();
                    go = new GameObject("Fence_" + f.Id);
                    go.transform.SetParent(root, false);
                }
                var line = new List<Vector2>(f.Line);
                if (f.Closed || Vector2.Distance(line[0], line[line.Count - 1]) > 0.5f && f.Closed) line.Add(line[0]);
                for (int i = 0; i + 1 < line.Count; i++)
                {
                    Vector2 a = line[i], b = line[i + 1];
                    float len = Vector2.Distance(a, b);
                    if (len < 0.2f) continue;
                    int n = Mathf.Max(1, Mathf.RoundToInt(len / st.Bay));
                    for (int k = 0; k < n; k++)
                    {
                        Vector2 p0 = Vector2.Lerp(a, b, (float)k / n), p1 = Vector2.Lerp(a, b, (float)(k + 1) / n);
                        if (InGate(f, (p0 + p1) / 2f)) continue;
                        float y0 = Mathf.Min(hm.Height(p0.x, p0.y), hm.Height(p1.x, p1.y)) - 0.1f;
                        Bay(m, st, p0, p1, y0, hm);
                        bays++;
                        Vector2 mid = (p0 + p1) / 2f, dir = (p1 - p0).normalized;
                        var c = new GameObject("Collider");
                        c.transform.SetParent(go.transform, false);
                        float ym = hm.Height(mid.x, mid.y);
                        c.transform.SetPositionAndRotation(new Vector3(mid.x, ym + st.H / 2f, mid.y), Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.y)));
                        c.AddComponent<BoxCollider>().size = new Vector3(Mathf.Max(0.2f, st.Panel + 0.1f), st.H + 0.4f, Vector2.Distance(p0, p1) + 0.05f);
                        colliders++;
                    }
                }
                foreach (var g in f.Gates)
                    for (int s = -1; s <= 1; s += 2)
                    {
                        // Gate piers either side of the opening.
                        Vector2 dir = GateDir(f, g.p);
                        Vector2 p = g.p + dir * (s * g.w / 2f);
                        float y = hm.Height(p.x, p.y);
                        m.Box(st.PostCat, new Vector3(p.x, y + (st.H + 0.3f) / 2f, p.y), new Vector3(0.45f, st.H + 0.3f, 0.45f), Quaternion.identity, st.PostColour);
                    }
                if (merged || m.IsEmpty) continue;
                go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(m.ToMesh(go.name, out string[] cats));
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterials = Mats(cats);
                mr.shadowCastingMode = st.Solid ? ShadowCastingMode.On : ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            }
            var cellKeys = new List<string>(cells.Keys);
            cellKeys.Sort(string.CompareOrdinal);
            foreach (string ck in cellKeys)
            {
                var cell = cells[ck];
                if (cell.m.IsEmpty) continue;
                GameObject go = cell.t.gameObject;
                Mesh cellMesh = store.AddMesh(cell.m.ToMesh(go.name, out string[] cats));
                go.AddComponent<MeshFilter>().sharedMesh = cellMesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterials = Mats(cats);
                mr.shadowCastingMode = cell.solid ? ShadowCastingMode.On : ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic |
                    (V3Mesh.StaticBatchSafe(cellMesh) ? StaticEditorFlags.BatchingStatic : 0));
            }
            log.Add($"fences v3: {V3LookData.Fences.Count} runs, {bays} bays, {colliders} box colliders");
        }

        private static bool InGate(V3LookData.Fence f, Vector2 p)
        {
            foreach (var g in f.Gates)
                if (Vector2.Distance(g.p, p) < g.w / 2f) return true;
            return false;
        }

        private static Vector2 GateDir(V3LookData.Fence f, Vector2 p)
        {
            float best = float.MaxValue;
            Vector2 dir = Vector2.right;
            for (int i = 0; i + 1 < f.Line.Count; i++)
            {
                Vector2 a = f.Line[i], b = f.Line[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                float d = Vector2.Distance(a + ab * t, p);
                if (d < best) { best = d; dir = ab.normalized; }
            }
            return dir;
        }

        private static void Bay(V3Mesh m, FenceStyle st, Vector2 p0, Vector2 p1, float y0, HeightModel hm)
        {
            Vector3 a = new Vector3(p0.x, 0f, p0.y), b = new Vector3(p1.x, 0f, p1.y);
            float ya = hm.Height(p0.x, p0.y), yb = hm.Height(p1.x, p1.y);
            m.Box(st.PostCat, new Vector3(a.x, ya + st.H / 2f - 0.05f, a.z), new Vector3(st.Post, st.H + 0.1f, st.Post), Quaternion.LookRotation(b - a), st.PostColour);
            float len = Vector3.Distance(a, b);
            Vector3 dir = (b - a) / len;
            float bottom = Mathf.Min(ya, yb) - 0.05f;
            if (st.Plinth) m.Beam("3c_concrete_panels", a, b, 0.3f, bottom - 0.2f, Mathf.Max(ya, yb) + 0.35f, V3Palette.C("grey.light"));
            float lo = st.Plinth ? Mathf.Max(ya, yb) + 0.35f : bottom + (st.Solid ? 0f : 0.1f);
            float hi = Mathf.Max(ya, yb) + st.H;
            if (st.Solid) m.Beam(st.PanelCat, a + dir * st.Post / 2f, b - dir * st.Post / 2f, st.Panel, lo, hi, st.PanelColour);
            if (st.Rails)
                foreach (float h in new[] { 0.35f, 0.8f })
                    m.Beam(st.PanelCat, a, b, 0.06f, Mathf.Lerp(ya, yb, 0.5f) + h - 0.05f, Mathf.Lerp(ya, yb, 0.5f) + h + 0.05f, st.PanelColour);
            if (st.Bars)
            {
                m.Beam(st.PanelCat, a, b, 0.05f, hi - 0.12f, hi - 0.05f, st.PanelColour);
                m.Beam(st.PanelCat, a, b, 0.05f, lo + 0.08f, lo + 0.15f, st.PanelColour);
                int bars = Mathf.Max(2, Mathf.RoundToInt(len / 0.28f));
                for (int k = 1; k < bars; k++)
                {
                    Vector3 p = Vector3.Lerp(a, b, (float)k / bars);
                    m.Box(st.PanelCat, new Vector3(p.x, (lo + hi) / 2f, p.z), new Vector3(0.035f, hi - lo, 0.035f), Quaternion.LookRotation(dir), st.PanelColour);
                }
            }
            if (st.Barbed)
                for (int w = 0; w < 3; w++)
                {
                    float y = hi + 0.12f + w * 0.12f;
                    Vector3 off = Vector3.Cross(Vector3.up, dir) * (0.08f * w);
                    m.Beam("6b_lightly_weathered_metal", a + off, b + off, 0.02f, y, y + 0.02f, V3Palette.C("grey.dark"));
                }
        }

        // ---------------------------------------------------------------- retaining walls, blockers

        public static void RetainingWalls(LookData d, HeightModel hm, V3Store store, Transform parent, List<string> log)
        {
            if (hm.Walls.Count == 0) return;
            var root = new GameObject("RetainingWalls").transform;
            root.SetParent(parent, false);
            var m = new V3Mesh();
            int boxes = 0;
            foreach (HeightModel.RetainingWall w in hm.Walls)
            {
                int n = LookGeom.Count(w.Ring);
                for (int i = 0; i < n; i++)
                {
                    int j = (i + 1) % n;
                    Vector2 a = new Vector2(w.Ring[2 * i], w.Ring[2 * i + 1]), b = new Vector2(w.Ring[2 * j], w.Ring[2 * j + 1]);
                    float len = Vector2.Distance(a, b);
                    if (len < 0.3f) continue;
                    Vector2 dir = (b - a) / len, nrm = new Vector2(dir.y, -dir.x);
                    float top = float.MinValue, bottom = float.MaxValue;
                    bool any = false;
                    for (float s = 0f; s <= len; s += 1f)
                    {
                        Vector2 p = a + dir * Mathf.Min(s, len);
                        float hin = hm.Height(p.x - nrm.x * 0.9f, p.y - nrm.y * 0.9f), hout = hm.Height(p.x + nrm.x * 0.9f, p.y + nrm.y * 0.9f);
                        float t = Mathf.Max(hin, hout) + 0.15f, bo = Mathf.Min(hin, hout) - 0.3f;
                        if (t - bo < 0.75f) continue;
                        any = true;
                        top = Mathf.Max(top, t);
                        bottom = Mathf.Min(bottom, bo);
                    }
                    if (!any) continue;
                    var A = new Vector3(a.x, 0f, a.y);
                    var B = new Vector3(b.x, 0f, b.y);
                    m.Beam("3c_concrete_panels", A, B, 0.45f, bottom, top, V3Palette.C("paving"));
                    var c = new GameObject("Collider");
                    c.transform.SetParent(root, false);
                    c.transform.SetPositionAndRotation(new Vector3((a.x + b.x) / 2f, (top + bottom) / 2f, (a.y + b.y) / 2f), Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.y)));
                    c.AddComponent<BoxCollider>().size = new Vector3(0.45f, top - bottom, len);
                    boxes++;
                }
            }
            if (m.IsEmpty) return;
            var go = new GameObject("RetainingWalls_Mesh");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(m.ToMesh(go.name, out string[] cats));
            go.AddComponent<MeshRenderer>().sharedMaterials = Mats(cats);
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            log.Add($"retaining walls v3: {hm.Walls.Count} pads, {boxes} box colliders");
        }

        // Invisible walls on the inland map edge (coast edges stay open), as PropScatterer.Blockers: one box per edge.
        public static void Blockers(LookData d, HeightModel hm, Transform parent)
        {
            var group = new GameObject("Blockers").transform;
            group.SetParent(parent, false);
            LookBoundary bnd = d.boundary;
            int n = LookGeom.Count(bnd.pts);
            float bh = bnd.blocker_h > 0f ? bnd.blocker_h : 6f;
            for (int e = 0; e < n; e++)
            {
                if (e < bnd.coast.Length && bnd.coast[e] == 1) continue;
                int f = (e + 1) % n;
                var a = new Vector3(bnd.pts[2 * e], 0f, bnd.pts[2 * e + 1]);
                var b = new Vector3(bnd.pts[2 * f], 0f, bnd.pts[2 * f + 1]);
                float len = Vector3.Distance(a, b);
                if (len < 0.1f) continue;
                float y0 = Mathf.Min(hm.Height(a.x, a.z), hm.Height(b.x, b.z)) - 2f, y1 = Mathf.Max(hm.Height(a.x, a.z), hm.Height(b.x, b.z)) + bh;
                var go = new GameObject("Boundary_" + e);
                go.transform.SetParent(group, false);
                go.transform.SetPositionAndRotation(new Vector3((a.x + b.x) / 2f, (y0 + y1) / 2f, (a.z + b.z) / 2f), Quaternion.LookRotation((b - a) / len));
                go.AddComponent<BoxCollider>().size = new Vector3(1f, y1 - y0, len + 1f);
            }
        }
    }
}
