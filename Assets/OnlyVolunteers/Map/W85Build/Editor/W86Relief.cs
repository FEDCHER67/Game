using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // W86 pass (data v02, lead brief 22.10): relief / water / backdrop parts of the builder. Every member falls back to the v01
    // behaviour when the v01 data lacks the new fields.
    //  - river: the water ribbon at the per-point surface of s03 (water_v85.json river.surface_m), none in the underground spans
    //    (land bridges: rock portals at both ends), none inside the lakes it runs through, white water at the cascades;
    //  - waterfalls from their geometry (lip / base edges, drop, own material with the WaterFX_waterfall_v02_tileY texture), white
    //    water (foam splash) at the foot, two framing rocks at the lip;
    //  - the north steppe backdrop: a second terrain (no collider, no shadows) replacing the flat Steppe_far plane, exact seam with the
    //    main terrain, drawn to the far plane by W85FarView (layer TransparentFX) and faded by the scene fog;
    //  - retaining walls: Elite stone road (inner cut), tunnel portal approaches (both sides), villa terraces (data line);
    //  - rock faces: terrain faces steeper than 35 deg get a rock skin with box-projected UVs (no stretched texture) and sparse rock
    //    outcrops on the steepest ones.
    public static partial class W85Builder
    {
        const int FarLayer = 1;                                   // TransparentFX: drawn to the far plane by W85FarView
        const string RockPrefabs = "Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01/Prefabs";
        static bool BackdropOn;
        static float[,] backdropH; static Vector3 backdropPos, backdropSize; static int backdropRes;
        static float[,,] backdropAlpha; static Terrain backdropTer;
        static float backdropHazeEnd = 3800f;
        static readonly List<GameObject> RockKit = new();
        static int rocksPlaced;

        static void W86Init()
        {
            BackdropOn = IsV2 && File.Exists(Data + "/steppe_backdrop_v02.json");
            backdropH = null; backdropAlpha = null; backdropTer = null; rocksPlaced = 0; RiverPts.Clear();
            RockKit.Clear();
            if (Directory.Exists(RockPrefabs))
                foreach (string f in Directory.GetFiles(RockPrefabs, "ROCK_*_v19.prefab").OrderBy(s => s))
                {
                    var g = AssetDatabase.LoadAssetAtPath<GameObject>(f.Replace('\\', '/'));
                    if (g) RockKit.Add(g);
                }
        }

        // ------------------------------------------------------------------ ground fit (s03 rule: footprint range > 1.5 m = error)
        // A building footprint whose ground range is over W85GroundFit.Limit gets its ground compressed towards the footprint mean to
        // ~1.25 m (inside the footprint fully, fading out over 3 m around it) in the built heightmap only; logged per building.
        internal static void GradeFootprints(float[,] h, int R, float sizeY, float posY)
        {
            float cell = W / (R - 1), cellZ = Hh / (R - 1);
            float At(float x, float z)
            {
                float u = Mathf.Clamp(x / cell, 0, R - 1.001f), v = Mathf.Clamp(z / cellZ, 0, R - 1.001f);
                int i = (int)u, j = (int)v; float fu = u - i, fv = v - j;
                return posY + sizeY * Mathf.Lerp(Mathf.Lerp(h[j, i], h[j, i + 1], fu), Mathf.Lerp(h[j + 1, i], h[j + 1, i + 1], fu), fv);
            }
            var log = new List<string>();
            foreach (string f in Directory.GetFiles(Data + "/districts", "*_v85.json"))
                foreach (var b in Arr(Get(Obj(Json.Parse(File.ReadAllText(f))), "buildings")).Select(Obj))
                {
                    if (b == null || (Get(b, "disabled") is bool off && off)) continue;
                    var fp = V2s(Get(b, "footprint"));
                    if (fp.Length < 3) continue;
                    float x0 = fp.Min(q => q.x), x1 = fp.Max(q => q.x), z0 = fp.Min(q => q.y), z1 = fp.Max(q => q.y);
                    var samples = new List<float>();
                    for (int k = 0; k < fp.Length; k++) { Vector2 a = fp[k], c = fp[(k + 1) % fp.Length]; int n = Mathf.Max(1, Mathf.CeilToInt((c - a).magnitude)); for (int t = 0; t < n; t++) { var q = Vector2.Lerp(a, c, t / (float)n); samples.Add(At(q.x, q.y)); } }
                    for (float z = z0 + .5f; z < z1; z += 1f) for (float x = x0 + .5f; x < x1; x += 1f) if (W76.W76Atmosphere.Inside(fp, new Vector2(x, z))) samples.Add(At(x, z));
                    float lo = samples.Min(), hi = samples.Max();
                    if (hi - lo <= W85GroundFit.Limit - .05f) continue;
                    float mean = samples.Average(), k2 = 1.2f / (hi - lo);
                    const float Fade = 3f;
                    int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - Fade) / cell)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 + Fade) / cell));
                    int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - Fade) / cellZ)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 + Fade) / cellZ));
                    var ring = fp.Append(fp[0]).ToArray();
                    for (int j = j0; j <= j1; j++)
                        for (int i = i0; i <= i1; i++)
                        {
                            var p = new Vector2(i * cell, j * cellZ);
                            float w = W76.W76Atmosphere.Inside(fp, p) ? 1f : Mathf.Clamp01(1f - W76.W76Atmosphere.Distance(ring, p) / Fade);
                            if (w <= 0f) continue;
                            float y = posY + sizeY * h[j, i];
                            float y2 = mean + (y - mean) * Mathf.Lerp(1f, k2, w * w * (3f - 2f * w));
                            h[j, i] = Mathf.Clamp01((y2 - posY) / sizeY);
                        }
                    log.Add($"{S(Get(b, "id"))} {hi - lo:0.00} -> ~1.2 m");
                }
            Note(log.Count == 0 ? "ground fit grading: no footprint over the limit" : $"ground fit grading: {log.Count} footprint(s) levelled in the built terrain: " + string.Join(", ", log));
        }

        // ------------------------------------------------------------------ steppe backdrop (second terrain beyond the border)
        static float BackdropHeight(float x, float z)
        {
            if (backdropH == null) return -10f;
            float u = (x - backdropPos.x) / backdropSize.x * (backdropRes - 1), v = (z - backdropPos.z) / backdropSize.z * (backdropRes - 1);
            if (u < 0 || v < 0 || u > backdropRes - 1 || v > backdropRes - 1) return -10f;
            int i = Mathf.Min((int)u, backdropRes - 2), j = Mathf.Min((int)v, backdropRes - 2);
            float fu = u - i, fv = v - j;
            float h = Mathf.Lerp(Mathf.Lerp(backdropH[j, i], backdropH[j, i + 1], fu), Mathf.Lerp(backdropH[j + 1, i], backdropH[j + 1, i + 1], fu), fv);
            return backdropPos.y + h * backdropSize.y;
        }

        static void BuildBackdrop(Transform root)
        {
            if (!BackdropOn) { Note("steppe backdrop: none in " + Data + " (flat Steppe_far plane)"); return; }
            var bj = Obj(Json.Parse(File.ReadAllText(Data + "/steppe_backdrop_v02.json")));
            var pos = Arr(Get(bj, "position_m")); var size = Arr(Get(bj, "size_m"));
            backdropPos = new Vector3(F(pos[0]), F(pos[1]), F(pos[2])); backdropSize = new Vector3(F(size[0]), F(size[1]), F(size[2]));
            backdropHazeEnd = F(Get(Obj(Get(bj, "haze")), "end_m"), 3800f);
            byte[] raw = File.ReadAllBytes(Data + "/" + S(Get(bj, "heightmap")));
            int R = Mathf.RoundToInt(Mathf.Sqrt(raw.Length / 2f));
            if (R * R * 2 != raw.Length) { Note($"steppe backdrop: heightmap size {raw.Length} B is not square r16 - skipped"); BackdropOn = false; return; }
            var h = new float[R, R];
            for (int j = 0; j < R; j++) for (int i = 0; i < R; i++) { int k = (j * R + i) * 2; h[j, i] = (raw[k] | raw[k + 1] << 8) / 65535f; }
            backdropH = h; backdropRes = R;
            // layers: R dry steppe grass, G rock, B greener swales, A coast sand-gravel (s07); own copies with long tiles (seen from afar)
            var keys = new[] { "L02_worn_grass", "L07_rock_macro", "L01_meadow", "L06_gravel_SK1d" };
            var i10 = I10Layers();
            var layers = keys.Select(k => BackdropLayer(k, i10)).ToArray();
            const int AR = 512;
            var td = new TerrainData { heightmapResolution = R, alphamapResolution = AR };
            td.size = backdropSize;
            AssetDatabase.CreateAsset(td, Gen + "/Terrain/TerrainData_SteppeBackdrop_" + Ver + ".asset");
            td.SetHeights(0, 0, h);
            td.terrainLayers = layers;
            string splat = (S(Get(bj, "splat")) ?? "").Split(' ')[0];
            var a = new float[AR, AR, 4];
            if (splat.Length > 0 && File.Exists(Data + "/" + splat))
            {
                var png = LoadPng(Data + "/" + splat);                // row 0 of the PNG (north) ends up at y = height - 1: y 0 = south
                var px = png.GetPixels32(); int w = png.width, ht = png.height;
                for (int j = 0; j < AR; j++)
                    for (int i = 0; i < AR; i++)
                    {
                        var c = px[Mathf.Min(ht - 1, (int)((j + .5f) / AR * ht)) * w + Mathf.Min(w - 1, (int)((i + .5f) / AR * w))];
                        float r = c.r, g = c.g, b = c.b, al = c.a, sum = r + g + b + al;
                        if (sum <= 0f) { a[j, i, 0] = 1f; continue; }
                        a[j, i, 0] = r / sum; a[j, i, 1] = g / sum; a[j, i, 2] = b / sum; a[j, i, 3] = al / sum;
                    }
                Object.DestroyImmediate(png);
            }
            else for (int j = 0; j < AR; j++) for (int i = 0; i < AR; i++) a[j, i, 0] = 1f;
            td.SetAlphamaps(0, 0, a);
            backdropAlpha = a;
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
            var go = Terrain.CreateTerrainGameObject(td);
            go.name = "SteppeBackdrop_" + Ver;
            Object.DestroyImmediate(go.GetComponent<TerrainCollider>());          // seen only: the invisible wall stands on the border fence
            go.transform.SetParent(root, false);
            go.transform.position = backdropPos;
            go.layer = FarLayer;
            backdropTer = go.GetComponent<Terrain>();
            var tm = AssetDatabase.LoadAssetAtPath<Material>(TerrainMaterial);
            if (tm) backdropTer.materialTemplate = tm;
            var u = Obj(Get(bj, "unity"));
            backdropTer.heightmapPixelError = F(Get(u, "pixel_error"), 8f); backdropTer.basemapDistance = F(Get(u, "basemap_distance"), 300f);
            backdropTer.drawTreesAndFoliage = false; backdropTer.drawInstanced = true;
            backdropTer.shadowCastingMode = ShadowCastingMode.Off;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            var seam = Obj(Get(bj, "seam"));
            float seamZ = F(Get(seam, "z_m"), Hh), worst = 0f;
            for (float x = 1f; x < W - 1f; x += 13f) worst = Mathf.Max(worst, Mathf.Abs(BackdropHeight(x, seamZ) - Height(x, seamZ - .01f)));
            Note($"steppe backdrop: terrain {R} x {R}, {backdropSize.x:0} x {backdropSize.z:0} m at ({backdropPos.x:0.0}, {backdropPos.z:0.0}), heights {backdropPos.y:0}..{backdropPos.y + backdropSize.y:0} m, " +
                 $"layer {LayerMask.LayerToName(FarLayer)}, no collider / shadows; seam z {seamZ:0} max |dh| {worst:0.00} m; haze end {backdropHazeEnd:0} m");
        }

        static TerrainLayer BackdropLayer(string key, Dictionary<string, TerrainLayer> i10)
        {
            var steppe = SteppeLayerT132(key);                                   // W86 integration: T132 b steppe (64 m macro tile)
            if (steppe) return steppe;
            var src = Layer(key, i10);
            if (!src) return null;
            var l = new TerrainLayer { diffuseTexture = src.diffuseTexture, normalMapTexture = src.normalMapTexture, tileSize = src.tileSize * 3f, smoothness = 0f, metallic = 0f };
            AssetDatabase.CreateAsset(l, Gen + "/Terrain/W86_backdrop_" + key + ".terrainlayer");
            created++;
            return l;
        }

        static void ReapplyBackdrop()
        {
            if (!backdropTer || backdropH == null) return;
            var td = backdropTer.terrainData;
            td.SetHeights(0, 0, backdropH);
            if (backdropAlpha != null) td.SetAlphamaps(0, 0, backdropAlpha);
            EditorUtility.SetDirty(td);
            foreach (Texture2D tex in td.alphamapTextures) EditorUtility.SetDirty(tex);
            AssetDatabase.SaveAssets();
            Note($"steppe backdrop re-applied after the asset save: probe {td.GetHeight(td.heightmapResolution / 2, td.heightmapResolution / 2):0.0} m");
        }

        // far view: cameras draw the backdrop + far sea to the haze end, everything else keeps its old cull distance
        static void FarView(Transform root)
        {
            if (!BackdropOn) return;
            if (backdropTer && Ter) backdropTer.materialTemplate = Ter.materialTemplate;      // the i10 terrain material of the look
            var fv = root.gameObject.AddComponent<W85FarView>();
            fv.Far = Mathf.Max(1000f, backdropHazeEnd + 200f); fv.FarLayer = FarLayer;
            Note($"far view: W85FarView on {root.name}: camera far {fv.Far:0} m for layer {LayerMask.LayerToName(FarLayer)} (steppe backdrop, far sea), other layers keep each camera's own far clip");
            NorthViewFog(root);
        }

        // Rough north view (lead 22.10): the district fog pass of the look gets the W86 copy of its shader (Runtime/
        // W86DistrictFogNorthView.shader): surfaces past the state fence band and the high ridges near it get a light distance haze
        // instead of the dense Rough mist; inside the blocks the approved Rough fog stays. Band from the border fence line of the data.
        static void NorthViewFog(Transform root)
        {
            var fog = root.GetComponentsInChildren<OnlyVolunteers.Map.Look.V3.DistrictFog19V05>(true).FirstOrDefault();
            var sh = Shader.Find("OnlyVolunteers/W86/DistrictFogNorthView");
            if (!fog || !fog.fogTemplate || !sh) { Note($"north view fog: skipped (fog {(fog ? "ok" : "missing")}, shader {(sh ? "ok" : "missing")})"); return; }
            var fence = V2s(Get(Obj(Json.Parse(File.ReadAllText(Data + "/border_v85.json"))), "fence_line"));
            float z0 = fence.Length > 0 ? fence.Min(q => q.y) : 920f, z1 = fence.Length > 0 ? fence.Max(q => q.y) : 944f;
            var m = new Material(sh) { name = "W86_DistrictFog_NorthView" };
            m.CopyPropertiesFromMaterial(fog.fogTemplate);
            var mask = new Vector4(z0 - 40f, z1 + 2f, 22f, 34f); var haze = new Vector4(150f, 2600f, .82f, 0f);
            m.SetVector("_W86Mask", mask); m.SetVector("_W86Haze", haze);
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W86_DistrictFog_NorthView.mat"); created++;
            fog.fogTemplate = m;
            EditorUtility.SetDirty(fog);
            if (fog.isActiveAndEnabled) { fog.enabled = false; fog.enabled = true; }          // re-create its runtime material from the new template
            Note($"north view fog: Rough fog pass -> {sh.name}: light haze ({haze.x:0}-{haze.y:0} m, max {haze.z:0.00}) past z {mask.x:0}-{mask.y:0} (fence band) and on ridges over {mask.z:0}-{mask.w:0} m near it");
        }

        // ------------------------------------------------------------------ river (W86: per-point surface)
        static void RiverV2(Transform parent, Dictionary<string, object> b, Material flow, Dictionary<string, object> wj)
        {
            string id = S(Get(b, "id"), "river");
            var axis = V2s(Get(b, "axis"));
            float[] Fl(string k) => Arr(Get(b, k)).Select(x => F(x)).ToArray();
            var wid = Fl("width_m"); var surf = Fl("surface_m");
            var reach = Arr(Get(b, "reach")).Select(x => S(x, "")).ToArray();
            int N = axis.Length;
            var spans = Arr(Get(b, "underground_spans")).Select(o => { var s = Arr(o); return (a: (int)F(s[0]), b: (int)F(s[1])); }).ToList();
            var fallSpans = new List<(int a, int b)>();
            var lakes = new List<Vector2[]>();
            foreach (var o in Arr(Get(wj, "bodies")).Select(Obj))
            {
                string k = S(Get(o, "kind"));
                if (k == "waterfall" && Get(o, "axis_index") != null) { var ai = Arr(Get(o, "axis_index")); fallSpans.Add(((int)F(ai[0]), (int)F(ai[1]))); }
                if (k == "lake" || k == "pond" || k == "swamp") { var ol = V2s(Get(o, "outline")); if (ol.Length >= 3) lakes.Add(ol); }
            }
            float Wd(int i) => i < wid.Length ? wid[i] : 6f;
            float Lv(int i) => i < surf.Length ? surf[i] : RiverBed(axis[i].y) + 1.2f;
            string Rc(int i) => i < reach.Length ? reach[i] : "river";
            bool Skip(int i)                                                       // segment i -> i + 1
            {
                if (spans.Any(s => i >= s.a && i < s.b)) return true;
                if (fallSpans.Any(s => i >= s.a && i < s.b)) return true;
                if (Rc(i) == "waterfall" && Rc(i + 1) == "waterfall") return true;
                Vector2 m = (axis[i] + axis[i + 1]) * .5f;
                return lakes.Any(l => W76.W76Atmosphere.Inside(l, m));
            }
            var rm = new MB(); int runs = 0, segs = 0; bool open = false;
            for (int i = 0; i + 1 < N; i++)
            {
                if (Skip(i)) { open = false; continue; }
                foreach (int k in open ? new[] { i + 1 } : new[] { i, i + 1 })
                {
                    Vector2 d = (axis[Mathf.Min(k + 1, N - 1)] - axis[Mathf.Max(k - 1, 0)]).normalized, nrm = new(-d.y, d.x);
                    float hw = Wd(k) * .5f + .8f, y = Lv(k) - (lakes.Any(l => W76.W76Atmosphere.Inside(l, axis[k])) ? .03f : 0f);   // no z-fight with a lake fill
                    string r = Rc(k);
                    float speed = r == "brook" ? 1.5f : r == "stream" ? 1.25f : r == "gorge_rocks" ? 1f : .8f;
                    foreach (var q in new[] { axis[k] + nrm * hw, axis[k] - nrm * hw }) { rm.V.Add(new Vector3(q.x, y, q.y)); rm.UV.Add(q / 10f); rm.UV1.Add(d * speed); }
                }
                if (!open) runs++;
                int v = rm.V.Count - 4; rm.T.AddRange(new[] { v, v + 2, v + 3, v, v + 3, v + 1 });
                open = true; segs++;
            }
            RiverPts.Clear();
            for (int i = 0; i < N; i++) RiverPts.Add((axis[i], Lv(i)));
            var mesh = rm.Build("Water_River_" + id);
            var go = MeshGo("Water_River_" + id, parent, mesh, flow);
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            AddWaterArea(id, Audio.WaterKind.River, mesh, true);
            // white water at the cascades (s03 cascades_axis_index)
            var splash = SplashMaterial(Mat(SeaMaterialKey));
            int nc = 0;
            foreach (var ci in Arr(Get(b, "cascades_axis_index")).Select(x => (int)F(x)).Where(x => x >= 0 && x < N))
            {
                Vector2 d = (axis[Mathf.Min(ci + 1, N - 1)] - axis[Mathf.Max(ci - 1, 0)]).normalized;
                Splash(parent, $"Cascade_{id}_{ci}", axis[ci] + d * .5f, Lv(Mathf.Min(ci + 1, N - 1)) + .03f, Mathf.Max(2.2f, Wd(ci) * .8f), splash);
                nc++;
            }
            // rock portals at both ends of each underground span (the river goes under a natural land bridge)
            int nr = 0;
            foreach (var s in spans)
                foreach (int k in new[] { Mathf.Clamp(s.a, 0, N - 1), Mathf.Clamp(s.b, 0, N - 1) })
                {
                    Vector2 d = (axis[Mathf.Min(k + 1, N - 1)] - axis[Mathf.Max(k - 1, 0)]).normalized, nrm = new(-d.y, d.x);
                    foreach (int sg in new[] { -1, 1 })
                        if (Rock(parent, axis[k] + nrm * sg * (Wd(k) * .5f + 1.6f), 3.6f + 1.4f * Hash(id + k + sg), 1.4f)) nr++;
                }
            Note($"river {id}: {segs} segments in {runs} runs at the s03 surface ({surf.Min():0.0}..{surf.Max():0.0} m), skipped: underground spans " +
                 string.Join(" ", spans.Select(s => $"[{s.a}..{s.b}]")) + ", falls " + string.Join(" ", fallSpans.Select(s => $"[{s.a}..{s.b}]")) + $", lakes; {nc} cascade foam splashes, {nr} portal rocks");
        }

        static readonly List<(Vector2 p, float y)> RiverPts = new();
        // water level of the river nearest to a polygon (within `range` m), else -inf
        static float RiverLevelNear(Vector2[] poly, float range)
        {
            float best = float.MaxValue, y = float.NegativeInfinity;
            Vector2 c = poly.Aggregate(Vector2.zero, (s, q) => s + q) / poly.Length;
            foreach (var (p, ly) in RiverPts) { float d = (p - c).magnitude; if (d < best) { best = d; y = ly; } }
            return best <= range + poly.Max(q => (q - c).magnitude) ? y : float.NegativeInfinity;
        }

        // ------------------------------------------------------------------ waterfalls (W86: geometry from water_v85.json)
        static void WaterfallV2(Transform parent, Dictionary<string, object> b, Material sea)
        {
            string id = S(Get(b, "id"), "waterfall");
            Vector3 W3(object o) { var a = Arr(o); return new Vector3(F(a[0]), F(a[2]), F(a[1])); }
            var lip = Arr(Get(b, "lip_edge")).Select(W3).ToArray(); var bas = Arr(Get(b, "base_edge")).Select(W3).ToArray();
            if (lip.Length < 2 || bas.Length < 2) { Note($"waterfall {id}: no lip / base edge"); return; }
            // keep the left / right order of the lip on the base (closest pairing)
            if ((lip[0] - bas[0]).sqrMagnitude + (lip[1] - bas[1]).sqrMagnitude > (lip[0] - bas[1]).sqrMagnitude + (lip[1] - bas[0]).sqrMagnitude) (bas[0], bas[1]) = (bas[1], bas[0]);
            float drop = F(Get(b, "drop_m"), lip[0].y - bas[0].y), width = F(Get(b, "width_top_m"), (lip[1] - lip[0]).magnitude);
            Vector3 lipC = (lip[0] + lip[1]) * .5f, basC = (bas[0] + bas[1]) * .5f;
            Vector3 fdir = new Vector3(basC.x - lipC.x, 0, basC.z - lipC.z);
            if (fdir.sqrMagnitude < .01f) { float a = F(Get(b, "flow_dir_deg")) * Mathf.Deg2Rad; fdir = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)); }
            fdir.Normalize();
            var mat = WaterfallMaterialFor(id, sea, S(Get(b, "material_texture")), width, drop);
            int rows = Mathf.Max(4, Mathf.CeilToInt(drop / 1.2f)), pushed = 0;
            var m = new MB(); var cols = new List<Color>();
            for (int r = 0; r <= rows; r++)
            {
                float t = r / (float)rows, hz = Mathf.Sqrt(t);                     // falling water: out fast at the lip, then mostly down
                for (int s = 0; s < 2; s++)
                {
                    Vector3 p = new(Mathf.Lerp(lip[s].x, bas[s].x, hz), Mathf.Lerp(lip[s].y, bas[s].y, t), Mathf.Lerp(lip[s].z, bas[s].z, hz));
                    // never inside the rock face: push the sheet out along the flow until the ground is .3 m below it
                    for (int k = 0; k < 24 && r > 0 && r < rows && Height(p.x, p.z) > p.y - .3f; k++) { p += fdir * .25f; pushed++; }
                    m.V.Add(p); m.UV.Add(new Vector2(s, 1f - t)); cols.Add(Color.white);
                }
                if (r > 0) { int v = m.V.Count - 4; m.T.AddRange(new[] { v, v + 2, v + 3, v, v + 3, v + 1 }); }
            }
            var mesh = new Mesh { name = "Waterfall_" + id };
            mesh.SetVertices(m.V); mesh.SetUVs(0, m.UV); mesh.SetColors(cols); mesh.SetTriangles(m.T, 0);
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + Safe(mesh.name) + ".asset");
            var go = MeshGo("Waterfall_" + id, parent, mesh, mat);
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            // white water at the foot (foam splash on the pool / sea surface) and a second, wider, fainter ring of spray
            float rad = F(Get(b, "spray_radius_m"), 5f);
            var splash = SplashMaterial(sea);
            if (!(Get(b, "foam_at_base") is bool fb) || fb)
            {
                Vector2 foot = new Vector2(basC.x, basC.z) + new Vector2(fdir.x, fdir.z) * .8f;
                float level = Mathf.Max(basC.y, 0f) + .04f;
                Splash(parent, "Foam_" + id, foot, level, rad, splash);
                Splash(parent, "Foam_" + id + "_outer", foot + new Vector2(fdir.x, fdir.z) * rad * .4f, level + .01f, rad * 1.6f, splash);
                FoamRingT130(parent, id, foot, new Vector2(fdir.x, fdir.z), level);    // W86 integration: T130 b foam ring
            }
            // two rocks framing the lip ("between two rocks")
            Vector3 side = (lip[1] - lip[0]).normalized;
            int nr = 0;
            foreach (int sg in new[] { -1, 1 })
            {
                Vector3 q = lipC + side * sg * (width * .5f + 1.6f) - fdir * .6f;
                if (Rock(parent, new Vector2(q.x, q.z), Mathf.Clamp(drop * .22f, 2.5f, 4.5f), .9f)) nr++;
            }
            Note($"waterfall {id}: lip {lipC.y:0.0} -> base {basC.y:0.0} m (drop {drop:0.0} m, {width:0.0} m wide), {rows} rows, {pushed} sheet pushes off the rock face, foam r {rad:0} m, {nr} framing rocks");
        }

        static Material WaterfallMaterialFor(string id, Material sea, string texPath, float width, float drop)
        {
            var m = new Material(sea) { name = "W85_waterfall_" + id };
            m.SetFloat("_OV_Mode", 1f); m.DisableKeyword("_OV_MODE_SURFACE"); m.DisableKeyword("_OV_MODE_FOAMSPLASH"); m.EnableKeyword("_OV_MODE_WATERFALL");
            m.SetFloat("_ENABLEWAVE", 0f); m.DisableKeyword("_ENABLEWAVE");
            var tex = ImportTexture(texPath ?? S(Get(Obj(Get(MatMap, "waterfall")), "texture")));
            if (tex) m.SetTexture("_OV_FoamMap", tex);
            if (m.HasProperty("_OV_FallTiling")) m.SetVector("_OV_FallTiling", new Vector4(Mathf.Max(1f, width / 2.2f), Mathf.Max(1f, drop / 5f), 0, 0));
            if (m.HasProperty("_Cull")) m.SetFloat("_Cull", 0f);                     // seen from both sides
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W85_waterfall_" + Safe(id) + ".mat"); created++;
            return m;
        }

        static Material splashMat;
        static Material SplashMaterial(Material sea)
        {
            string p = Gen + "/Materials/W85_water_foam_splash.mat";
            if (splashMat && AssetDatabase.GetAssetPath(splashMat) == p) return splashMat;
            var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m)
            {
                m = new Material(sea) { name = "W85_water_foam_splash" };
                m.SetFloat("_OV_Mode", 2f); m.DisableKeyword("_OV_MODE_SURFACE"); m.DisableKeyword("_OV_MODE_WATERFALL"); m.EnableKeyword("_OV_MODE_FOAMSPLASH");
                m.SetFloat("_ENABLEWAVE", 0f); m.DisableKeyword("_ENABLEWAVE");
                var tex = ImportTexture(S(Get(Obj(Get(MatMap, "shore_foam")), "texture"))) ?? ImportTexture(S(Get(Obj(Get(MatMap, "waterfall")), "texture")));
                if (tex) m.SetTexture("_OV_FoamMap", tex);
                AssetDatabase.CreateAsset(m, p); created++;
            }
            return splashMat = m;
        }

        // radial-UV quad (the v05 shader's FoamSplash mode: UV0 0..1, centre 0.5)
        static void Splash(Transform parent, string name, Vector2 c, float y, float r, Material mat)
        {
            var mb = new MB();
            mb.Quad(new Vector3(c.x - r, y, c.y - r), new Vector3(c.x - r, y, c.y + r), new Vector3(c.x + r, y, c.y + r), new Vector3(c.x + r, y, c.y - r),
                new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0));
            var mesh = mb.Build(name, false);
            mesh.SetColors(Enumerable.Repeat(Color.white, mesh.vertexCount).ToList());
            AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + Safe(name) + ".asset");
            var go = MeshGo(name, parent, mesh, mat);
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
        }

        // A rock of the v19 kit (happykeys, CC0), scaled to `size` metres across, sunk by `sink` metres, random yaw / tilt by position.
        static bool Rock(Transform parent, Vector2 at, float size, float sink, Vector3? up = null)
        {
            if (RockKit.Count == 0) return false;
            float hsh = Hash($"{at.x:0.0}_{at.y:0.0}", 7);
            var src = RockKit[Mathf.Min(RockKit.Count - 1, (int)(hsh * RockKit.Count))];
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            go.name = "Rock_" + src.name;
            go.transform.rotation = Quaternion.FromToRotation(Vector3.up, up ?? Vector3.up) * Quaternion.Euler(0, hsh * 360f, 0);
            var rs = go.GetComponentsInChildren<Renderer>();
            if (rs.Length > 0)
            {
                var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                float ext = Mathf.Max(bb.size.x, bb.size.z, .1f);
                go.transform.localScale = go.transform.localScale * (size / ext);
            }
            go.transform.position = new Vector3(at.x, Height(at.x, at.y) - sink, at.y);
            if (IsV2) W85FloatCheck.SeatRock(go.transform);                       // G46: validate actual tilted mesh support, not just its pivot
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            rocksPlaced++;
            return true;
        }

        // ------------------------------------------------------------------ retaining walls
        static void RetainingWalls(Transform root)
        {
            if (!IsV2) return;
            var parent = new GameObject("RetainingWalls").transform; parent.SetParent(root, false);
            var rj = Obj(Json.Parse(File.ReadAllText(Data + "/roads_v85.json")));
            Vector2 elite = V2(Get(Obj(Get(Obj(Json.Parse(File.ReadAllText(Data + "/features_v85.json"))), "elite")), "centre"));
            var portals = TunnelAxis.Length >= 2 ? new[] { TunnelAxis[0], TunnelAxis[TunnelAxis.Length - 1] } : new Vector2[0];
            int runs = 0; float metres = 0f;
            foreach (var r in Arr(Get(rj, "roads")).Select(Obj))
            {
                string kind = S(Get(r, "kind")), id = S(Get(r, "id"));
                var pl = V2s(Get(r, "points"));
                if (pl.Length < 2 || kind == "tunnel" || kind == "bridge" || kind == "dirt" || kind == "sand_track") continue;
                var pts = ResamplePy(pl, 2f);
                var hs = Arr(Get(r, "heights")).Select(x => F(x)).ToArray();
                Func<int, float> hAt = hs.Length == pts.Count ? i => hs[i] : (Func<int, float>)(i => Height(pts[i].x, pts[i].y));
                float w = F(Get(r, "width_m"), 6.4f);
                if (kind == "stone_serpentine")
                {   // Elite stone road: the inner side (to the plateau) is cut into the hill -> stone wall; the outer side has the parapet
                    // s03 grades a 6+ m shoulder beside the road: the wall stands at the toe of the steep rise to the plateau
                    var (n, m) = ToeWall(parent, "Wall_retaining_" + id + "_inner", pts, hAt, w, i => Vector2.Dot(Normal(pts, i), elite - pts[i]) > 0 ? 1 : -1, "cobble_SK2c");
                    runs += n; metres += m;
                }
                if (portals.Length > 0)
                {   // tunnel portal approaches: concrete wing walls on both sides where the cut rises above the road (within 70 m of a portal)
                    Func<int, bool> near = i => portals.Any(p => (pts[i] - p).magnitude < 70f);
                    if (!portals.Any(p => (pl[0] - p).magnitude < 3f || (pl[pl.Length - 1] - p).magnitude < 3f)) continue;   // approach roads only (they end at a portal)
                    foreach (int sg in new[] { -1, 1 })
                    {
                        var (n, m) = CutWall(parent, "Wall_retaining_" + id + (sg > 0 ? "_L" : "_R"), pts, hAt, w, i => sg, "concrete_SK3c", near);
                        runs += n; metres += m;
                    }
                }
            }
            // villa terraces (Elite data: retaining_wall line on the downhill side of the plot, terrace_abs_m)
            int villas = 0;
            foreach (string f in Directory.GetFiles(Data + "/districts", "*_v85.json"))
                foreach (var z in Arr(Get(Obj(Json.Parse(File.ReadAllText(f))), "zones")).Select(Obj))
                {
                    var line = V2s(Get(z, "retaining_wall"));
                    if (line.Length < 2) continue;
                    float terrace = F(Get(z, "terrace_abs_m"), float.NaN);
                    var mb = new MB(); float acc = 0f;
                    foreach (var q in Resample(line, 1.5f).Zip(Resample(line, 1.5f).Skip(1), (a, c) => (a, c)))
                    {
                        float top = float.IsNaN(terrace) ? Mathf.Max(Height(q.a.x, q.a.y), Height(q.c.x, q.c.y)) + .3f : terrace + .35f;
                        float ya = Height(q.a.x, q.a.y) - .4f, yc = Height(q.c.x, q.c.y) - .4f, L = (q.c - q.a).magnitude;
                        if (top - Mathf.Min(ya, yc) < .5f) { acc += L; continue; }
                        Vector2 d = (q.c - q.a) / L, nrm = new(-d.y, d.x);
                        WallSlab(mb, q.a, q.c, nrm, .45f, ya, yc, top, top, acc, Tile("cobble_SK2c"));
                        acc += L;
                    }
                    if (mb.V.Count == 0) continue;
                    string nm = "Wall_retaining_" + S(Get(z, "id"), "plot");
                    MeshGo(nm, parent, mb.Build(nm), Mat("cobble_SK2c"), true);
                    villas++; metres += acc;
                }
            Note($"retaining walls: {runs} road cut runs (Elite stone road inner side, tunnel portal approaches) + {villas} villa terraces, {metres:0} m in all");
        }

        static Vector2 Normal(List<Vector2> pts, int i)
        {
            Vector2 d = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[Mathf.Max(i - 1, 0)]).normalized;
            return new Vector2(-d.y, d.x);
        }

        // Wall along one road edge where the ground beside the road stands > 0.7 m above it: from 0.3 m under the road to 0.25 m over the
        // ground behind; each run of consecutive samples = one mesh (front, top, back) with a static mesh collider.
        static (int runs, float metres) CutWall(Transform parent, string name, List<Vector2> pts, Func<int, float> hAt, float w, Func<int, int> side, string mat, Func<int, bool> filter)
        {
            var mb = new MB(); int runs = 0; float metres = 0f, tile = Tile(mat); bool open = false; float acc = 0f;
            float off = w * .5f + .35f, thick = .5f;
            for (int i = 1; i < pts.Count; i++)
            {
                bool Cut(int k, out float bottom, out float top)
                {
                    Vector2 n = Normal(pts, k) * side(k);
                    float road = hAt(k), behind = Mathf.Max(Height(pts[k].x + n.x * (off + 1.3f), pts[k].y + n.y * (off + 1.3f)), Height(pts[k].x + n.x * (off + .4f), pts[k].y + n.y * (off + .4f)));
                    bottom = road - .3f; top = behind + .25f;
                    return (filter == null || filter(k)) && behind - road > .7f;
                }
                if (!Cut(i - 1, out float b0, out float t0) || !Cut(i, out float b1, out float t1)) { open = false; continue; }
                if (!open) runs++;
                open = true;
                Vector2 n0 = Normal(pts, i - 1) * side(i - 1), n1 = Normal(pts, i) * side(i);
                Vector2 a = pts[i - 1] + n0 * off, c = pts[i] + n1 * off;
                float L = (c - a).magnitude;
                if (L < .05f) continue;
                Vector2 face = -(n0 + n1).normalized;                               // the wall's front looks back at the road
                WallSlab(mb, a, c, face, thick, b0, b1, t0, t1, acc, tile);
                acc += L; metres += L;
            }
            if (mb.V.Count > 0) MeshGo(name, parent, mb.Build(name), Mat(mat), true);
            return (runs, metres);
        }

        // Wall at the toe of a cut slope beside a road: scanning out from the road edge (up to 14 m) for the first metre that rises > 0.6 m
        // (31 deg); where the next 2.5 m rise > 1.2 m, a 2.5 m deep stone block stands there: its face at the toe, its top level with the
        // ground 2.5 m behind it (wall + backfill), so the steep ledge reads as a retaining wall, not a stretched slope.
        static (int runs, float metres) ToeWall(Transform parent, string name, List<Vector2> pts, Func<int, float> hAt, float w, Func<int, int> side, string mat)
        {
            var mb = new MB(); int runs = 0; float metres = 0f, tile = Tile(mat), acc = 0f; bool open = false;
            const float Deep = 2.5f;
            bool Toe(int k, out Vector2 at, out float bottom, out float top)
            {
                Vector2 n = Normal(pts, k) * side(k); at = default; bottom = top = 0f;
                float H(float d) => Height(pts[k].x + n.x * d, pts[k].y + n.y * d);
                for (float d = w * .5f + .4f; d < w * .5f + 14f; d += .5f)
                {
                    if (H(d + 1f) - H(d) < .6f) continue;
                    float rise = H(d + Deep) - H(d);
                    if (rise < 1.2f) return false;
                    at = pts[k] + n * d; bottom = H(d) - .35f; top = H(d + Deep) + .12f;
                    return true;
                }
                return false;
            }
            Vector2 prev = default; float pb = 0f, pt = 0f;
            for (int i = 0; i < pts.Count; i++)
            {
                if (!Toe(i, out Vector2 at, out float b0, out float t0)) { open = false; continue; }
                if (open)
                {
                    float L = (at - prev).magnitude;
                    if (L > .05f && L < 6f)
                    {
                        Vector2 face = -(Normal(pts, i - 1) * side(i - 1) + Normal(pts, i) * side(i)).normalized;
                        WallSlab(mb, prev, at, face, Deep, pb, b0, pt, t0, acc, tile);
                        acc += L; metres += L;
                    }
                }
                else runs++;
                open = true; prev = at; pb = b0; pt = t0;
            }
            if (mb.V.Count > 0) MeshGo(name, parent, mb.Build(name), Mat(mat), true);
            return (runs, metres);
        }

        // vertical slab a -> c: face on the `face` side, top, back face (thickness), y from bottom to top at both ends
        static void WallSlab(MB mb, Vector2 a, Vector2 c, Vector2 face, float thick, float ya, float yc, float ta, float tc, float u0, float tile)
        {
            float L = (c - a).magnitude, u1 = u0 + L;
            Vector2 ab = a - face * thick, cb = c - face * thick;
            Vector3 A0 = new(a.x, ya, a.y), A1 = new(a.x, ta, a.y), C0 = new(c.x, yc, c.y), C1 = new(c.x, tc, c.y);
            Vector3 B0 = new(ab.x, ya, ab.y), B1 = new(ab.x, ta, ab.y), D0 = new(cb.x, yc, cb.y), D1 = new(cb.x, tc, cb.y);
            // pick the winding so that the front face looks along `face`
            bool flip = Vector3.Dot(Vector3.Cross(A1 - A0, C0 - A0), new Vector3(face.x, 0, face.y)) < 0;
            void Q(Vector3 p, Vector3 q, Vector3 r, Vector3 s, Vector2 up, Vector2 uq, Vector2 ur, Vector2 us)
            { if (flip) mb.Quad(s, r, q, p, us, ur, uq, up); else mb.Quad(p, q, r, s, up, uq, ur, us); }
            Q(A0, A1, C1, C0, new Vector2(u0 / tile, ya / tile), new Vector2(u0 / tile, ta / tile), new Vector2(u1 / tile, tc / tile), new Vector2(u1 / tile, yc / tile));   // front
            Q(A1, B1, D1, C1, new Vector2(u0 / tile, 0), new Vector2(u0 / tile, thick / tile), new Vector2(u1 / tile, thick / tile), new Vector2(u1 / tile, 0));            // top
            Q(D0, D1, B1, B0, new Vector2(u1 / tile, yc / tile), new Vector2(u1 / tile, tc / tile), new Vector2(u0 / tile, ta / tile), new Vector2(u0 / tile, ya / tile));   // back
        }

        // ------------------------------------------------------------------ rock faces (> 35 deg: no stretched terrain texture)
        static void RockFaces(Transform root)
        {
            if (!IsV2 || !Ter) return;
            var parent = new GameObject("RockFaces").transform; parent.SetParent(root, false);
            var td = Ter.terrainData; var o = Ter.transform.position;
            int nx = Mathf.FloorToInt(W), nz = Mathf.FloorToInt(Hh);
            const float Steep = 35f, Out = .12f, Sink = -.25f, Chunk = 64f;
            // keep-out: buildings, roads (+1 m), tunnel portals, the river surface
            var block = new bool[nx * nz];
            void Mark(Vector2 c, float r) { for (int z = Mathf.Max(0, (int)(c.y - r)); z <= Mathf.Min(nz - 1, (int)(c.y + r)); z++) for (int x = Mathf.Max(0, (int)(c.x - r)); x <= Mathf.Min(nx - 1, (int)(c.x + r)); x++) if ((new Vector2(x + .5f, z + .5f) - c).magnitude <= r) block[z * nx + x] = true; }
            foreach (var (id, pl, w, kind) in WorldRoads)
                if (kind != "tunnel") foreach (var q in Resample(pl, 1f)) Mark(q, w * .5f + 1.2f);
            foreach (var p in TunnelAxis.Length >= 2 ? new[] { TunnelAxis[0], TunnelAxis[TunnelAxis.Length - 1] } : new Vector2[0]) Mark(p, 16f);
            foreach (var bi in Built)
            {
                float x0 = bi.Fp.Min(q => q.x) - 1, x1 = bi.Fp.Max(q => q.x) + 1, z0 = bi.Fp.Min(q => q.y) - 1, z1 = bi.Fp.Max(q => q.y) + 1;
                for (int z = Mathf.Max(0, (int)z0); z <= Mathf.Min(nz - 1, (int)z1); z++) for (int x = Mathf.Max(0, (int)x0); x <= Mathf.Min(nx - 1, (int)x1); x++) block[z * nx + x] = true;
            }
            var steep = new bool[nx * nz]; int nSteep = 0;
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    int k = z * nx + x;
                    if (block[k]) continue;
                    float u = (x + .5f) / W, v = (z + .5f) / Hh;
                    if (td.GetSteepness(u, v) < Steep) continue;
                    if (td.GetInterpolatedHeight(u, v) + o.y < .5f) continue;           // sea cliffs under the water line
                    steep[k] = true; nSteep++;
                }
            bool IsSteep(int x, int z) => x >= 0 && z >= 0 && x < nx && z < nz && steep[z * nx + x];
            var mat = RockFaceMaterial();
            int chunks = 0; long tris = 0;
            for (int cz = 0; cz < nz; cz += (int)Chunk)
                for (int cx = 0; cx < nx; cx += (int)Chunk)
                {
                    var mb = new MB();
                    for (int z = cz; z < Mathf.Min(nz, cz + (int)Chunk); z++)
                        for (int x = cx; x < Mathf.Min(nx, cx + (int)Chunk); x++)
                        {
                            if (!IsSteep(x, z)) continue;
                            Vector3 Vt(int vx, int vz)
                            {   // inner vertices (all 4 cells around steep) float 12 cm over the ground, edge vertices sink into it
                                bool inner = IsSteep(vx - 1, vz - 1) && IsSteep(vx, vz - 1) && IsSteep(vx - 1, vz) && IsSteep(vx, vz);
                                float u = vx / W, v = vz / Hh;
                                Vector3 n = td.GetInterpolatedNormal(u, v);
                                return new Vector3(vx, td.GetInterpolatedHeight(u, v) + o.y, vz) + n * (inner ? Out : Sink);
                            }
                            Vector3 p00 = Vt(x, z), p10 = Vt(x + 1, z), p01 = Vt(x, z + 1), p11 = Vt(x + 1, z + 1);
                            RockTri(mb, p00, p01, p11); RockTri(mb, p00, p11, p10);
                            tris += 2;
                        }
                    if (mb.V.Count == 0) continue;
                    string nm = $"RockFace_{cx}_{cz}";
                    var go = MeshGo(nm, parent, mb.Build(nm), mat);
                    go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
                    chunks++;
                }
            // outcrops: one rock per 26 m cell on the steepest (> 50 deg) free spot
            int rocks0 = rocksPlaced; const float Cell = 26f;
            var outcrops = new GameObject("RockOutcrops").transform; outcrops.SetParent(parent, false);
            for (float cz = 0; cz < Hh; cz += Cell)
                for (float cx = 0; cx < W; cx += Cell)
                {
                    float best = 50f; Vector2 at = default; bool found = false;
                    for (float z = cz + 2; z < Mathf.Min(Hh, cz + Cell) - 2; z += 3f)
                        for (float x = cx + 2; x < Mathf.Min(W, cx + Cell) - 2; x += 3f)
                        {
                            int k = (int)z * nx + (int)x;
                            if (k < 0 || k >= block.Length || block[k] || !steep[k]) continue;
                            float s = td.GetSteepness(x / W, z / Hh);
                            if (s > best) { best = s; at = new Vector2(x, z); found = true; }
                        }
                    if (!found) continue;
                    Vector3 n = td.GetInterpolatedNormal(at.x / W, at.y / Hh);
                    Rock(outcrops, at, 2.8f + 2.4f * Hash($"{at.x}_{at.y}", 3), .9f, Vector3.Slerp(Vector3.up, n, .5f));
                }
            Note($"rock faces: {nSteep} m2 steeper than {Steep} deg -> {chunks} rock skin chunks ({tris} tris, box-projected UVs, edges sunk into the ground), {rocksPlaced - rocks0} outcrops on faces > 50 deg");
        }

        // one triangle with its own UVs projected on the plane its normal faces most (no stretching on steep faces)
        static void RockTri(MB mb, Vector3 a, Vector3 b, Vector3 c)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
            const float T = 7f;
            Vector2 Uv(Vector3 p) => ay >= ax && ay >= az ? new Vector2(p.x, p.z) / T : ax >= az ? new Vector2(p.z, p.y) / T : new Vector2(p.x, p.y) / T;
            if (n.y < 0) mb.Tri(a, c, b, Uv(a), Uv(c), Uv(b)); else mb.Tri(a, b, c, Uv(a), Uv(b), Uv(c));
        }

        static Material RockFaceMaterial()
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W86_rock_face", enableInstancing = true };
            var tex = ImportTexture(S(Get(Obj(Get(MatMap, "L07_rock_macro")), "texture")));
            if (tex) m.SetTexture("_BaseMap", tex);
            m.SetColor("_BaseColor", new Color(.93f, .92f, .9f));
            m.SetFloat("_Smoothness", .06f);
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W86_rock_face.mat"); created++;
            return m;
        }

        // ------------------------------------------------------------------ look rectangles that moved with the data
        static Dictionary<string, Vector4> LookRects()
        {
            if (!IsV2) return null;
            var d = new Dictionary<string, Vector4>();
            Vector4? Box(string district)
            {
                string f = Directory.GetFiles(Data + "/districts", district + "_v85.json").FirstOrDefault();
                if (f == null) return null;
                var dj = Obj(Json.Parse(File.ReadAllText(f)));
                var pts = new List<Vector2>();
                foreach (var b in Arr(Get(dj, "buildings")).Select(Obj)) pts.AddRange(V2s(Get(b, "footprint")));
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj)) foreach (string k in new[] { "poly", "line", "poly_line" }) pts.AddRange(V2s(Get(z, k)).Where(q => q != Vector2.zero));
                if (pts.Count == 0) return null;
                return new Vector4(pts.Min(q => q.x), pts.Min(q => q.y), pts.Max(q => q.x), pts.Max(q => q.y));
            }
            var dt = Box("downtown");
            if (dt.HasValue) d["old_town"] = new Vector4(dt.Value.x - 5f, dt.Value.y - 3f, dt.Value.z + 1f, dt.Value.w + 5f);
            string bf = Directory.GetFiles(Data + "/districts", "beach_v85.json").FirstOrDefault();
            float dy = bf != null ? F(Get(Obj(Get(Obj(Json.Parse(File.ReadAllText(bf))), "shift_v37")), "dy_m"), 0f) : 0f;
            d["beach"] = new Vector4(790, 100 + dy, 1520, 228 + dy);
            Note("look rectangles (data " + Ver + "): " + string.Join(", ", d.Select(kv => $"{kv.Key} ({kv.Value.x:0}, {kv.Value.y:0})-({kv.Value.z:0}, {kv.Value.w:0})")));
            return d;
        }
    }
}
