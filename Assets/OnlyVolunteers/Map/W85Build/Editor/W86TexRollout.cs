using System;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // W86 integration (B2, 22.10): the T1 / T2 texture picks rolled out on the map (MapW86_TexturesAll_2026-10-22/T1/PICKS_T1.md,
    // ROLLOUT_MAP_T1.json, T2/PICKS_T2.md, ROLLOUT_MAP_T2.json). Picks are constants here (switch a code = change its letter / path):
    //  - slot materials (materials_v85.json "texture_test" / "texture_test_roof", split slots rough_kiosk / rough_transformer / rough_kpp /
    //    hamlet_hay_shelter by kind, data tints cleared on retextured slots);
    //  - builder geometry asked for by T1 (D4 accent profiles for police / taxi / van shop / diner / gas shop / classical / base garage /
    //    loft, base-2 hut through H5, open hay shelter, Rough garage doors, transformer door + danger plate, KPP band + canopy, shop "24"
    //    light box, tunnel lamps + kerbs + ceiling UVs, railway dead end, chain-link veil on every chain-link fence, foam rings);
    //  - T2 generators (TexW86T2.Generate / GenerateLine) on their buildings / lines, T2 map materials on the W85 renderers;
    //  - one post pass that swaps materials by W85 object name (zones, piers, bridges, portals, tunnel, walls, prop tints).
    // Decals (road markings, wear, shore foam: T123 / T124 / T134) are the next agent's: W86DecalHooks() lists their targets only.
    public static partial class W85Builder
    {
        const string T1Mat = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Materials/";
        const string T1Pref = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Prefabs/";
        const string T1Layers = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1/TerrainLayers/";
        const string T2Mats = "Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/";
        static readonly Dictionary<string, Material> LoadedMats = new();
        static readonly List<string> W86Missing = new();
        static readonly Dictionary<string, int> W86Done = new();
        static void Done(string what, int n = 1) => W86Done[what] = W86Done.TryGetValue(what, out int k) ? k + n : n;

        static Material LoadMat(string path)
        {
            if (LoadedMats.TryGetValue(path, out var m) && m) return m;
            m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m && !W86Missing.Contains(path)) W86Missing.Add(path);
            return LoadedMats[path] = m;
        }
        static Material T1M(string n) => LoadMat(T1Mat + n + ".mat");
        static Material T2M(string n) => LoadMat(T2Mats + "Map/" + n + ".mat");
        static Material T2P(string n) => LoadMat(T2Mats + "Props/" + n + ".mat");

        static void W86RolloutInit()
        {
            LoadedMats.Clear(); W86Missing.Clear(); W86Done.Clear(); V07Log.Clear(); DsCount.Clear(); MapReadyCache.Clear(); RNoShadow.Clear();
            dcPaving = null; t2Ok = null; railTop = .55f; PoolHoles.Clear(); MetreBoxCache.Clear();
            Folder(Gen + "/Meshes/T2");
            // M2 atlas: one URP Lit material, mipmaps OFF on the 16 px swatch atlas (MODELS_M2.json "material")
            ModelsInit();
        }

        // ================================================================== slots: split by kind, tint cleared on retextured slots
        static string SlotFor(string district, string kind, string slot)
        {
            if (district.Contains("rough"))
            {
                if (kind == "kiosk") return "rough_kiosk";
                if (kind == "transformer_booth") return "rough_transformer";
                if (kind == "border_control") return "rough_kpp";
            }
            if (district.Contains("hamlet") && kind == "hay_shelter") return "hamlet_hay_shelter";
            return slot;
        }
        static bool ClearTint(string slot) => Get(Obj(Get(Slots, slot ?? "")), "clear_tint") is bool ct && ct;

        // ================================================================== T1 D4 accent profiles (T43 b, T44 a, T45 a, T46 a)
        sealed class Acc { public string Kind; }
        static readonly HashSet<string> AccentKinds = new() { "police", "police_rotunda", "taxi_depot", "podium_annex", "arch_house", "van_shop", "gas_shop", "diner", "classical", "base_garage", "loft" };
        static Acc AccentOf(Dictionary<string, object> b) { string k = S(Get(b, "kind"), ""); return AccentKinds.Contains(k) ? new Acc { Kind = k } : null; }
        static int AccentFace(int[] kinds) { int i = Array.IndexOf(kinds, 1); return i >= 0 ? i : 0; }

        static void AccentColours(Acc a, string id, ref string upKey, ref Color up, ref string grKey, ref Color gr, ref bool shops)
        {
            switch (a.Kind)
            {
                case "police": case "police_rotunda": case "taxi_depot": case "podium_annex": case "arch_house":       // T43 b: D4 brick, stone trims
                    upKey = "brick_paint"; up = RX("7A4437"); grKey = "brick_paint"; gr = RX("6A4034"); shops = false; break;
                case "van_shop": case "gas_shop": case "diner":                                                         // T45 a: cream plaster storefronts
                    upKey = "acg_plaster"; up = RX("C6BBA3"); grKey = "acg_plaster"; gr = RX("B6A58F"); shops = true; break;
                case "classical":                                                                                       // T46 a: plaster over rusticated ashlar
                    upKey = "acg_plaster"; up = RX("D9D2C2"); grKey = T7("ashlar"); gr = RX("C9C1AF"); shops = false; break;
                case "base_garage": case "loft":                                                                        // T44 a: D4 brick
                    upKey = "brick_paint"; up = RX("6A4034"); grKey = "brick_paint"; gr = RX("5E3B33"); shops = false; break;
            }
            Done("T1 accent " + a.Kind);
        }

        // letters from T1_sign_words (row 0 POLICE, 1 TAXI, 2 GAS, 3 DINER, 4 VANS) centred at s on a street face, height letterH
        static readonly float[] SignFracT1 = { .147f, .092f, .083f, .126f, .109f, .168f, .175f, .086f };
        static void SignWord(RBatch det, RFr w, int row, float s, float y, float letterH, float proud)
        {
            var m = T1M("T1_sign_words"); if (!m) return;
            string k = RSurfKey("t1:sign_words", m, 1f, true);
            float fw = SignFracT1[row] * 1.1f, hgt = letterH * 128f / 86f, width = hgt * 16f * fw;
            var uv = Rect.MinMaxRect(.5f - fw / 2, 1f - (row + 1) / 8f, .5f + fw / 2, 1f - row / 8f);
            float s0 = s - width / 2, s1 = s + width / 2, y0 = y - hgt / 2, y1 = y + hgt / 2;
            det[k].Quad(w.P(s0, y0, -proud), w.P(s0, y1, -proud), w.P(s1, y1, -proud), w.P(s1, y0, -proud), new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }

        static void AccentStreet(Acc a, RBatch det, Transform kit, RBatch body, RFr w, float L, float Gf, List<Rect> ground, List<int> gkind, string id)
        {
            float door = ground.Count > 0 ? ground[Mathf.Max(0, gkind.FindIndex(k => k == 1 || k == 2 || k == 3))].center.x : L / 2;
            Color dark = RX("2F3437");
            switch (a.Kind)
            {
                case "police": case "police_rotunda":
                {
                    RWallBox(det, "flat", w, .2f, L - .2f, Gf + .35f, Gf + 1.05f, .1f, RX("2E4A7A"));
                    SignWord(det, w, 0, L / 2, Gf + .7f, .42f, .13f);
                    RWallBox(det, "flat", w, door - 2f, door + 2f, 3.2f, 3.38f, 1.6f, dark);                  // entrance canopy
                    var bl = T1M("T1_blue_lamp");
                    if (bl) { string k = RSurfKey("t1:blue_lamp", bl, 1f, true); foreach (float x in new[] { door - 2.3f, door + 2.3f }) RBox(det, k, w, new Vector3(x, 2.4f, -.07f), new Vector3(.25f, .4f, .14f), Color.white, RALL6); }
                    RCyl(det, T7("flat_metal"), w.P(Mathf.Min(L - .8f, door + 5f), 0, -1.4f), .06f, 9f, 8, RX("C9C6C0"));
                    RBox(det, T7("flat"), w, new Vector3(Mathf.Min(L - .8f, door + 5f) + .9f, 8.4f, -1.4f), new Vector3(1.7f, 1.1f, .02f), RX("2F4E8C"), RALL6);
                    break;
                }
                case "taxi_depot":
                {
                    RWallBox(det, "flat", w, .2f, L - .2f, Gf - .05f, Gf + .45f, .1f, RX("E1B53A"));
                    SignWord(det, w, 1, L / 2, Gf + .2f, .36f, .13f);
                    float span = Mathf.Min(14.4f, L - 2f), x0 = (L - span) / 2;
                    for (int i = 0; i < 3; i++) RWallBox(det, T7("shutter"), w, x0 + i * span / 3 + .3f, x0 + (i + 1) * span / 3 - .3f, .02f, Mathf.Min(3.6f, Gf - .6f), .03f, RX("7E8284"));
                    break;
                }
                case "van_shop": case "diner": case "gas_shop":
                {
                    Color band = RX("A33A33");
                    int row = a.Kind == "van_shop" ? 4 : a.Kind == "diner" ? 3 : 2;
                    RWallBox(det, "flat", w, .2f, L - .2f, Gf - .95f, Gf - .3f, .12f, band);
                    SignWord(det, w, row, L / 2, Gf - .62f, a.Kind == "diner" ? .5f : .38f, .15f);
                    if (a.Kind == "gas_shop")
                    {   // fuel canopy 16 x 10 m at 5 m on 4 columns in front of the shop, white with a red fascia band
                        float cw = Mathf.Min(16f, L + 4f), cx = L / 2;
                        RBox(det, "flat", w, new Vector3(cx, 5.12f, -6.5f), new Vector3(cw, .25f, 10f), RX("E9E6DF"), RALL6);
                        RBox(det, "flat", w, new Vector3(cx, 4.85f, -6.5f), new Vector3(cw + .2f, .9f, 10.2f), RX("E9E6DF"), RXP | RXN | RZP | RZN);
                        RBox(det, "flat", w, new Vector3(cx, 4.72f, -11.62f), new Vector3(cw + .2f, .25f, .05f), band, RALL6);
                        foreach (float x in new[] { cx - cw / 2 + 2f, cx + cw / 2 - 2f }) foreach (float z in new[] { -3f, -10f }) RBox(det, "flat", w, new Vector3(x, 2.5f, z), new Vector3(.4f, 5f, .4f), RX("C9C6C0"), RALL5);
                    }
                    break;
                }
                case "base_garage":
                {   // three recessed roller-shutter bays with stone lintels
                    float span = Mathf.Min(15.6f, L - 1.5f), x0 = (L - span) / 2;
                    for (int i = 0; i < 3; i++)
                    {
                        float a0 = x0 + i * span / 3 + .35f, a1 = x0 + (i + 1) * span / 3 - .35f;
                        RWallBox(det, T7("shutter"), w, a0, a1, .02f, Mathf.Min(3.9f, Gf - .4f), .03f, RX("8C8F90"));
                        RWallBox(det, "flat", w, a0 - .25f, a1 + .25f, Mathf.Min(3.9f, Gf - .4f), Mathf.Min(3.9f, Gf - .4f) + .35f, .08f, RX("D1C8B6"));
                    }
                    break;
                }
                case "classical":
                {   // pilasters every bay, entablature + cornice
                    int n = Mathf.Max(2, Mathf.RoundToInt(L / 4f)); float st = L / n;
                    for (int i = 0; i <= n; i++) RWallBox(det, "trim", w, Mathf.Max(0, i * st - .3f), Mathf.Min(L, i * st + .3f), Gf, Gf + 9f, .24f, RX("E6E0D2"));
                    break;
                }
            }
        }

        // loft (T44 a): big steel windows, dark frames
        static void AccentSep(Acc a, SepP sp)
        {
            if (a == null) return;
            if (a.Kind == "loft") { sp.On = true; sp.Bay = 3.4f; sp.Hw = 1.3f; sp.Sill = .5f; sp.Head = 2.9f; sp.FrameCol = "2F3437"; }
            if (a.Kind == "classical") { sp.On = true; sp.Hood = true; sp.Lintel = true; sp.Bay = 4f; sp.Hw = .75f; sp.Sill = .6f; sp.Head = 3.2f; sp.FrameCol = "E4DFD3"; sp.Cornice = "stepped"; sp.CorniceH = .9f; sp.CorniceP = .6f; sp.CorCol = "E6E0D2"; }
        }

        // ================================================================== building hooks
        // before the generic house: models / prefabs / open structures that have no W85 body
        static bool W86BeforeBuilding(Transform parent, Dictionary<string, object> b, string district, string kind, List<Vector2> fp, string id)
        {
            try
            {
                if (kind == "rail_wagon_base1") return WagonModel(parent, b, fp, id);
                if (district.Contains("hamlet") && kind == "bus_stop") return BusStopT12(parent, b, fp, id);
                if (district.Contains("hamlet") && kind == "hay_shelter") return HayShelterT10(parent, b, fp, id);
            }
            catch (Exception e) { RolloutIssue($"{id} ({kind}) W86 pre-hook failed: {e.Message}"); }
            return false;
        }

        // after the generic house (colliders + roof test entry kept): new look
        static void W86AfterBuilding(Transform go, Dictionary<string, object> b, string district, string kind, List<Vector2> fp, string id)
        {
            try
            {
                if (district.Contains("port"))
                {
                    if (kind == "storage_tank") { T2Tank(go, b, fp, id); return; }
                    if (new[] { "warehouse", "checkpoint_booth", "service_post", "site_cabin", "pump_house" }.Contains(kind))
                    {
                        bool pitched = (S(Get(Obj(Get(b, "roof")), "type"), "flat") ?? "flat") != "flat";
                        StripVisuals(go, pitched ? new[] { "roof", "gables" } : new string[0]);
                        if (pitched) ReMaterial(go, "roof", MapReadyT7("trapez", Tile(S(Get(Obj(Get(b, "roof")), "material")) ?? "roof_tile_SK4a")), "gables", MapReadyT7("wave", Tile(S(Get(b, "walls")) ?? "brick_SK3a")));
                        PortP3(go, b, fp, id, kind);
                        return;
                    }
                }
                if (district.Contains("elite"))
                {
                    if (kind == "villa" || kind == "garage") { StripVisuals(go); EliteVilla(go, b, fp, id, kind == "garage"); return; }
                    if (kind == "fbi_post" || kind == "guard_booth") { StripVisuals(go); EliteFbi(go, b, fp, id, kind == "guard_booth"); return; }
                }
                if (district.Contains("construction"))
                {
                    if (kind == "old_dormitory") { T2Building(go, b, fp, id, "T69", 'a'); return; }
                    if (kind == "transformer_booth") { T2Building(go, b, fp, id, "T79", 'a', 270f); return; }
                    if (new[] { "concrete_frame", "stair_lift_core", "scaffold", "cargo_hoist", "foundation_slab", "site_cabin", "canteen", "shower", "foreman_office", "guard_booth", "van_workshop" }.Contains(kind))
                    { StripVisuals(go); C2Building(go, b, fp, id, kind); return; }
                }
                if (district.Contains("valley"))
                {
                    if (kind.Contains("lab")) { StripVisuals(go); ValleyLabQ3(go, b, fp, id); return; }
                    if (kind == "casino") { StripVisuals(go); CasinoQ3(go, b, fp, id); return; }
                }
                if (district.Contains("beach"))
                {
                    if (kind == "beach_bar") { T2Building(go, b, fp, id, id.Contains("cabana") ? "T107cabana" : "T107bar", 'a', null, S(Get(b, "tint"))); return; }
                    if (kind == "rental_hut") { T2Building(go, b, fp, id, "T107hut", 'a', null, S(Get(b, "tint"))); return; }
                }
                if (district.Contains("tramduro"))
                {
                    if (kind.Contains("palace")) { T2Building(go, b, fp, id, "T115", 'a'); return; }
                    if (kind.Contains("hangar")) { T2Building(go, b, fp, id, "T116", 'a'); HangarColliders(go, b, fp, id); return; }
                    if (kind == "guard_booth") { T2Building(go, b, fp, id, "T117", 'a'); return; }
                }
                if (district.Contains("downtown") && kind == "pavilion") { StripVisuals(go); DcPavilion(go, b, fp, id); return; }
                if (district.Contains("downtown") && AccentKinds.Contains(kind) && fp.Count != 4) { StripVisuals(go); PolyD4(go, b, fp, id, kind); return; }
                if (district.Contains("rough"))
                {
                    if (kind == "garage") { GarageDoor(go, b, fp, id); return; }
                    if (kind == "transformer_booth") { TransformerT28(go, b, fp, id); return; }
                    if (kind == "border_control") { KppT29(go, b, fp, id); return; }
                    if (kind == "shop") { Shop24T27(go, b, fp, id); return; }
                }
            }
            catch (Exception e) { RolloutIssue($"{id} ({kind}) W86 reskin failed: {e.Message}"); }
        }

        static void ReMaterial(Transform go, params object[] pairs)
        {
            for (int i = 0; i + 1 < pairs.Length; i += 2)
            {
                var t = go.Find((string)pairs[i]); var m = pairs[i + 1] as Material;
                if (t && m) foreach (var r in t.GetComponentsInChildren<MeshRenderer>(true)) r.sharedMaterial = m;
            }
        }

        // ================================================================== T2 generators
        static bool? t2Ok;
        static GameObject T2Gen(string code, char v, Transform parent, Vector3 origin, float yaw, Vector3 size, string tint = null)
        {
            try
            {
                var go = OnlyVolunteers.Art.MapTexturesW86.TexW86T2.Generate(code, v, parent, origin, yaw, size, Gen + "/Meshes/T2", tint);
                if (go) { foreach (var t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic); t2Ok = true; Done("T2 " + code); }
                return go;
            }
            catch (Exception e) { RolloutIssue($"T2 {code} failed: {e.Message}"); t2Ok = false; return null; }
        }

        static void T2Building(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string code, char v, float? facing = null, string tint = null)
        {
            var bf = BFrameOf(b, fp, facing);
            float yaw = Mathf.Atan2(bf.F.F.x, bf.F.F.z) * Mathf.Rad2Deg;                 // the frame yaw (front = -Z = entrance side)
            StripVisuals(go);
            var g = T2Gen(code, v, go, new Vector3(bf.C.x, bf.Y0, bf.C.y), yaw, new Vector3(bf.W, bf.H, bf.D), tint);
            if (!g) return;
            var lod = go.gameObject.AddComponent<LODGroup>();
            lod.SetLODs(new[] { new LOD(.012f, go.GetComponentsInChildren<Renderer>()) }); lod.RecalculateBounds();
        }

        static void T2Tank(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            Vector2 c = fp.Aggregate(Vector2.zero, (s, q) => s + q) / fp.Count;
            float r = fp.Max(q => (q - c).magnitude);
            StripVisuals(go);
            T2Gen("T81", 'a', go, new Vector3(c.x, fp.Min(q => Height(q.x, q.y)), c.y), 0f, new Vector3(2 * r, F(Get(b, "height_m"), 10f), 2 * r));
        }

        // hangar (T116): open front / sides -> colliders = back wall + the arch in 16 segments (the generic box would fill the hangar)
        static void HangarColliders(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var bf = BFrameOf(b, fp);
            var gen = go.Find("colliders"); if (gen) Object.DestroyImmediate(gen.gameObject);
            var cols = new GameObject("colliders").transform; cols.SetParent(go, false);
            float W = bf.W, H = bf.H, D = bf.D, post = 3f, half = W / 2, sag = H - post, R = (half * half + sag * sag) / (2 * sag), cy = H - R;
            Vector2 Arc(int i) { float x = -half + W * i / 16; return new Vector2(x, cy + Mathf.Sqrt(R * R - x * x)); }
            for (int i = 0; i < 16; i++)
            {
                Vector2 a = Arc(i), c = Arc(i + 1);
                var pts = new List<Vector3>();
                foreach (float z in new[] { -D / 2, D / 2 }) foreach (float dy in new[] { 0f, -.35f }) { pts.Add(bf.F.P(a.x, a.y + dy, z) - bf.F.O); pts.Add(bf.F.P(c.x, c.y + dy, z) - bf.F.O); }
                var g = new GameObject("arch_" + i); g.transform.SetParent(cols, false); g.transform.position = bf.F.O;
                var m = new Mesh { name = "B_" + id + "_arch_" + i }; m.SetVertices(pts); m.SetTriangles(Enumerable.Range(1, pts.Count - 2).SelectMany(k => new[] { 0, k, k + 1 }).ToArray(), 0);
                AssetDatabase.CreateAsset(m, Gen + "/Meshes/" + Safe(m.name) + ".asset");
                var mc = g.AddComponent<MeshCollider>(); mc.sharedMesh = m; mc.convex = true;
            }
            var back = new List<Vector3>();
            for (int i = 0; i <= 16; i++) { var a = Arc(i); foreach (float z in new[] { D / 2, D / 2 - .3f }) { back.Add(bf.F.P(a.x, a.y, z) - bf.F.O); back.Add(bf.F.P(a.x, -.3f, z) - bf.F.O); } }
            var bg = new GameObject("back"); bg.transform.SetParent(cols, false); bg.transform.position = bf.F.O;
            var bm = new Mesh { name = "B_" + id + "_back" }; bm.SetVertices(back); bm.SetTriangles(Enumerable.Range(1, back.Count - 2).SelectMany(k => new[] { 0, k, k + 1 }).ToArray(), 0);
            AssetDatabase.CreateAsset(bm, Gen + "/Meshes/" + Safe(bm.name) + ".asset");
            var bc = bg.AddComponent<MeshCollider>(); bc.sharedMesh = bm; bc.convex = true;
            foreach (float z in new[] { -D / 2, -D / 4, 0f, D / 4, D / 2 }) foreach (int sg in new[] { -1, 1 }) AddBoxLocal(cols, bf.F, new Vector3(sg * (half - .2f), post / 2, z), new Vector3(.4f, post, .4f));
            Built.RemoveAll(x => x.Go == go.gameObject);                                   // open arch: no flat-roof test
        }

        // ================================================================== Forest: base-1 wagon (M1 model), X01 railway dead end
        static float railTop = .55f;
        static bool WagonModel(Transform parent, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var m = M1Model("MW86_RailWagon_Base1"); if (!m) return false;
            Vector2 c = fp.Aggregate(Vector2.zero, (s, q) => s + q) / fp.Count;
            float ridge = F(Get(Obj(Get(b, "roof")), "ridge_axis_deg"), 32.5f), yaw = 90f - ridge;
            var e0 = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(e => e != null);
            if (e0 != null)
            {   // the sliding doorway is on the model's local +X: flip if the data door faces the other track side
                float fa = F(Get(e0, "facing_deg")) * Mathf.Deg2Rad; Vector3 want = new(Mathf.Cos(fa), 0, Mathf.Sin(fa));
                if (Vector3.Dot(Quaternion.Euler(0, yaw, 0) * Vector3.right, want) < 0) yaw += 180f;
            }
            float y = Height(c.x, c.y) + railTop;
            var go = PlaceModel(parent, "B_" + id, m, new Vector3(c.x, y, c.y), yaw, 1f, M1Mat("Machines", 'A'), M1Colliders("MW86_RailWagon_Base1"), true);
            // invisible ramp to the door (steps of 0.42-0.45 m on the model; the floor is 1.3 m over the rail, the KCC has no stairs)
            var right = Quaternion.Euler(0, yaw, 0) * Vector3.right;
            Vector3 sill = go.transform.TransformPoint(new Vector3(1.6f, 1.3f, 0f));
            float ground = Height(sill.x + right.x * 2f, sill.z + right.z * 2f), rise = sill.y - ground, len = Mathf.Max(2.5f, rise / Mathf.Tan(28f * Mathf.Deg2Rad));
            var ramp = new GameObject("DoorRamp_invisible").AddComponent<BoxCollider>();
            ramp.transform.SetParent(go.transform, true);
            Vector3 foot = sill + right * len; foot.y = ground;
            Vector3 dirV = (foot - sill).normalized, sideV = Vector3.Cross(Vector3.up, dirV).normalized, upV = Vector3.Cross(dirV, sideV);
            if (upV.y < 0) upV = -upV;
            ramp.transform.rotation = Quaternion.LookRotation(dirV, upV);
            ramp.transform.position = (sill + foot) * .5f - upV * .1f;
            ramp.size = new Vector3(1.6f, .2f, (foot - sill).magnitude + .3f);
            Done("M1 wagon (base 1) + door ramp");
            return true;
        }

        // X01 b: ballast bed 3 m + slopes, wooden sleepers every 0.62 m, rusty rails at +-0.76 m, buffer stop at the dead end
        static void RailwayX01(Transform parent, Dictionary<string, object> z, string id)
        {
            var line = V2s(Get(z, "line")); if (line.Length < 2) return;
            var b = new RBatch();
            string ballast = RSurfKey("t1:X01_ballast", T1M("T1_X01_ballast_brown") ?? RS["concrete"].M, 2f);
            string sleeper = RSurfKey("t1:boards_tar", T1M("T1_k_boards_tar") ?? RS["flat"].M, 1f);
            string rail = T7("flat_metal");
            var pts = Resample(line, 1f);
            float acc = 0f, total = 0f; for (int i = 1; i < pts.Count; i++) total += (pts[i] - pts[i - 1]).magnitude;
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], c = pts[i], d = (c - a).normalized, n = new(-d.y, d.x);
                float ya = Height(a.x, a.y), yc = Height(c.x, c.y), L = (c - a).magnitude;
                Vector3 A(float o, float y) => new Vector3(a.x + n.x * o, ya + y, a.y + n.y * o);
                Vector3 C(float o, float y) => new Vector3(c.x + n.x * o, yc + y, c.y + n.y * o);
                b[ballast].Quad(A(1.5f, .25f), C(1.5f, .25f), C(-1.5f, .25f), A(-1.5f, .25f), new(acc / 2f, 0), new((acc + L) / 2f, 0), new((acc + L) / 2f, 1.5f), new(acc / 2f, 1.5f), RS[ballast].Own);
                b[ballast].Quad(A(2.4f, -.05f), C(2.4f, -.05f), C(1.5f, .25f), A(1.5f, .25f), new(acc / 2f, -.5f), new((acc + L) / 2f, -.5f), new((acc + L) / 2f, 0), new(acc / 2f, 0), RS[ballast].Own);
                b[ballast].Quad(A(-1.5f, .25f), C(-1.5f, .25f), C(-2.4f, -.05f), A(-2.4f, -.05f), new(acc / 2f, 1.5f), new((acc + L) / 2f, 1.5f), new((acc + L) / 2f, 2f), new(acc / 2f, 2f), RS[ballast].Own);
                acc += L;
            }
            var g0 = RFr.Yaw(Vector3.zero, 0);
            for (float s = .3f; s < total; s += .62f)
            {
                Vector2 q = PointAt(pts, s), q2 = PointAt(pts, Mathf.Min(total, s + .1f)), d = (q2 - q).normalized;
                var f = RFr.Yaw(new Vector3(q.x, Height(q.x, q.y) + .25f, q.y), Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg);
                RBox(b, sleeper, f, new Vector3(0, .08f, 0), new Vector3(2.6f, .16f, .25f), RS[sleeper].Own, RALL5);
            }
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], c = pts[i], d = (c - a).normalized, n = new(-d.y, d.x);
                foreach (float o in new[] { -.76f, .76f })
                {
                    Vector3 p0 = new(a.x + n.x * o, Height(a.x, a.y) + .48f, a.y + n.y * o), p1 = new(c.x + n.x * o, Height(c.x, c.y) + .48f, c.y + n.y * o);
                    RBeam(b, rail, p0, p1, .07f, .14f, RX("6B4A3A"));
                }
            }
            // buffer stop at the east (dead) end
            Vector2 e = line[line.Length - 1], ed = (line[line.Length - 1] - line[line.Length - 2]).normalized;
            var bfr = RFr.Yaw(new Vector3(e.x + ed.x * .4f, Height(e.x, e.y) + .25f, e.y + ed.y * .4f), Mathf.Atan2(ed.x, ed.y) * Mathf.Rad2Deg);
            RBox(b, T7("flat_metal"), bfr, new Vector3(0, .6f, 0), new Vector3(2.2f, .35f, .3f), RX("8A3A2E"), RALL6);
            foreach (float x in new[] { -.76f, .76f }) RBeam(b, rail, bfr.P(x, .55f, 0), bfr.P(x, -.05f, 1.4f), .12f, .12f, RX("5A4034"));
            var holder = new GameObject("Railway_" + id).transform; holder.SetParent(parent, false);
            RFlush(b, holder, "Railway_" + id);
            foreach (Transform t in holder) if (t.name.Contains("ballast")) { var mc = t.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = t.GetComponent<MeshFilter>().sharedMesh; }
            Done("X01 railway dead end");
        }

        // ================================================================== Hamlet: T12 bus stop prefab, T10 open hay shelter
        static bool BusStopT12(Transform parent, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var pf = AssetDatabase.LoadAssetAtPath<GameObject>(T1Pref + "T1_BusStop_a.prefab"); if (!pf) return false;
            Frame(fp, Obj(Get(b, "roof")) ?? new Dictionary<string, object>(), out Vector2 c, out Vector2 ax, out Vector2 ay, out _, out _);
            // open side (-Z) towards the nearest world road
            Vector2 best = ay; float bd = float.MaxValue;
            foreach (var v in new[] { ay, -ay })
                foreach (var (_, pl, _, kind) in WorldRoads) { if (kind == "tunnel") continue; float d = W76Atmosphere.Distance(pl, c + v * 3f); if (d < bd) { bd = d; best = v; } }
            float yaw = Mathf.Atan2(-best.x, -best.y) * Mathf.Rad2Deg;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
            go.name = "B_" + id; go.transform.SetPositionAndRotation(new Vector3(c.x, fp.Min(q => Height(q.x, q.y)), c.y), Quaternion.Euler(0, yaw, 0));
            if (go.GetComponentsInChildren<Collider>(true).Length == 0)
            {
                var f = RFr.Yaw(go.transform.position, yaw); var cols = new GameObject("colliders").transform; cols.SetParent(go.transform, true);
                AddBoxLocal(cols, f, new Vector3(0, 1.35f, .85f), new Vector3(4.4f, 2.7f, .2f));
                foreach (int s in new[] { -1, 1 }) AddBoxLocal(cols, f, new Vector3(s * 2.15f, 1.35f, 0), new Vector3(.2f, 2.7f, 1.8f));
                AddBoxLocal(cols, f, new Vector3(0, 2.65f, 0), new Vector3(4.6f, .15f, 2f));
            }
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            Done("T12 bus stop");
            return true;
        }

        static bool HayShelterT10(Transform parent, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var roofM = T1M("T1_T07a_roof"); var postM = T1M("T1_k_boards_dark"); if (!roofM || !postM) return false;
            var roofD = Obj(Get(b, "roof")) ?? new Dictionary<string, object>();
            Frame(fp, roofD, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            float g0 = fp.Min(q => Height(q.x, q.y)), H = F(Get(b, "height_m"), 4f), rh = F(Get(roofD, "ridge_h_m"), 1.5f), ov = .4f;
            var go = new GameObject("B_" + id); go.transform.SetParent(parent, false);
            var f = RFr.Yaw(new Vector3(c.x, g0, c.y), Mathf.Atan2(ay.x, ay.y) * Mathf.Rad2Deg);       // local x = ridge axis (ax)
            var b2 = new RBatch();
            string post = RSurfKey("t1:k_boards_dark", postM, 1f), roof = RSurfKey("t1:T07a_sheet", roofM, 3f);   // (no "roof" in the name: the float check skips the shelter's own roof)
            var cols = new GameObject("colliders").transform; cols.SetParent(go.transform, false);
            foreach (float x in new[] { -hx + .15f, 0f, hx - .15f }) foreach (float z in new[] { -hy + .15f, hy - .15f })
                { RBox(b2, post, f, new Vector3(x, (H - .3f) / 2, z), new Vector3(.2f, H + .3f, .2f), RS[post].Own, RALL5); AddBoxLocal(cols, f, new Vector3(x, H / 2, z), new Vector3(.2f, H, .2f)); }
            foreach (float z in new[] { -hy + .15f, hy - .15f }) RBox(b2, post, f, new Vector3(0, H - .1f, z), new Vector3(2 * hx, .2f, .22f), RS[post].Own, RALL6);
            RBox(b2, post, f, new Vector3(0, H + rh - .1f, 0), new Vector3(2 * hx, .2f, .2f), RS[post].Own, RALL6);
            foreach (int s in new[] { -1, 1 })
            {
                Vector3 e0 = f.P(-hx - ov, H - ov * rh / hy, s * (hy + ov)), e1 = f.P(hx + ov, H - ov * rh / hy, s * (hy + ov)), r0 = f.P(-hx - ov, H + rh, 0), r1 = f.P(hx + ov, H + rh, 0);
                float sl = Mathf.Sqrt((hy + ov) * (hy + ov) + rh * rh) / 3f, al = (2 * hx + 2 * ov) / 3f;
                if (s < 0) { b2[roof].Quad(e0, r0, r1, e1, Vector2.zero, new(0, sl), new(al, sl), new(al, 0), Color.white); b2[roof].Quad(e1, r1, r0, e0, Vector2.zero, new(0, sl), new(al, sl), new(al, 0), Color.white); }
                else { b2[roof].Quad(e1, r1, r0, e0, Vector2.zero, new(0, sl), new(al, sl), new(al, 0), Color.white); b2[roof].Quad(e0, r0, r1, e1, Vector2.zero, new(0, sl), new(al, sl), new(al, 0), Color.white); }
            }
            RFlush(b2, go.transform, "B_" + id + "_T10");
            var hull = new List<Vector3> { f.P(-hx - ov, H - .05f, -hy - ov), f.P(hx + ov, H - .05f, -hy - ov), f.P(hx + ov, H - .05f, hy + ov), f.P(-hx - ov, H - .05f, hy + ov), f.P(-hx - ov, H + rh + .05f, 0), f.P(hx + ov, H + rh + .05f, 0) };
            Hull(cols, "roof", hull, id);
            // hay bales inside (T14 prefab)
            var bale = AssetDatabase.LoadAssetAtPath<GameObject>(T1Pref + "T1_HayBale_a.prefab");
            if (bale)
                for (int i = 0; i < 4; i++)
                {
                    var bg = (GameObject)PrefabUtility.InstantiatePrefab(bale, go.transform);
                    Vector3 p = f.P(-hx + 1.2f + i * (2 * hx - 2.4f) / 3f, .75f, (i % 2 == 0 ? -.6f : .6f));
                    p.y = Height(p.x, p.z) + .72f;
                    bg.transform.SetPositionAndRotation(p, Quaternion.LookRotation(f.F, Vector3.up));
                }
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            Done("T10 open hay shelter");
            return true;
        }

        // ================================================================== Rough: T26 garage doors, T28 transformer, T29 KPP, T27 shop 24
        static void GarageDoor(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var e = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(x => x != null && Get(x, "pos") != null);
            if (e == null) return;
            int nn = (int)(RHash(id, 91) * 16) % 16;
            var pf = AssetDatabase.LoadAssetAtPath<GameObject>(T1Pref + $"T1_GarageDoor_{nn:00}.prefab"); if (!pf) return;
            Vector2 p = V2(Get(e, "pos")); float a = F(Get(e, "facing_deg")) * Mathf.Deg2Rad; Vector3 outN = new(Mathf.Cos(a), 0, Mathf.Sin(a));
            float baseY = fp.Min(q => Height(q.x, q.y)) - .25f;
            var d = (GameObject)PrefabUtility.InstantiatePrefab(pf, go);
            d.name = "GarageDoor_" + nn.ToString("00");
            d.transform.SetPositionAndRotation(new Vector3(p.x, Mathf.Max(baseY + .25f, Height(p.x, p.y)), p.y) + outN * .02f, Quaternion.LookRotation(-outN, Vector3.up));
            foreach (Transform t in d.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            var lod = go.GetComponent<LODGroup>(); if (lod) { var l = lod.GetLODs(); l[0].renderers = l[0].renderers.Concat(d.GetComponentsInChildren<Renderer>()).ToArray(); lod.SetLODs(l); }
            Done("T26 garage doors");
        }

        static (Vector2 p, Vector3 n, Vector2 d)? FaceDoor(Dictionary<string, object> b, List<Vector2> fp)
        {
            var e = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(x => x != null && Get(x, "pos") != null);
            if (e != null) { float a = F(Get(e, "facing_deg")) * Mathf.Deg2Rad; var n = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)); return (V2(Get(e, "pos")), n, new Vector2(-n.z, n.x)); }
            // no entrance: the south face (lowest z edge), middle
            int best = 0; float bz = float.MaxValue;
            for (int i = 0; i < fp.Count; i++) { float z = (fp[i].y + fp[(i + 1) % fp.Count].y) / 2; if (z < bz) { bz = z; best = i; } }
            Vector2 a0 = fp[best], a1 = fp[(best + 1) % fp.Count], dd = (a1 - a0).normalized;
            return ((a0 + a1) / 2, new Vector3(dd.y, 0, -dd.x), dd);
        }

        static void TransformerT28(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var fd = FaceDoor(b, fp); if (fd == null) return;
            var (p, n, d) = fd.Value;
            var det = new RBatch();
            float g = Height(p.x, p.y);
            var f = RFr.Yaw(new Vector3(p.x, g, p.y), Mathf.Atan2(-n.x, -n.z) * Mathf.Rad2Deg);
            string met = RSurfKey("t1:k_metal", T1M("T1_k_metal") ?? RS["flat"].M, 1f);
            RBox(det, met, f, new Vector3(0, 1.1f, -.03f), new Vector3(1.3f, 2.2f, .06f), RX("6C7073"), RALL6);
            var dm = T1M("T1_danger");
            if (dm) RBox(det, RSurfKey("t1:danger", dm, 1f, true), f, new Vector3(0, 1.55f, -.065f), new Vector3(.4f, .4f, .005f), Color.white, RZN);
            var details = go.Find("details") ?? new GameObject("details").transform; details.SetParent(go, false);
            RFlush(det, details, "B_" + id + "_T28");
            Done("T28 transformer door + plate");
        }

        static void KppT29(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var fd = FaceDoor(b, fp); if (fd == null) return;
            var (p, n, d) = fd.Value;
            var det = new RBatch();
            float g = Height(p.x, p.y), H = F(Get(b, "height_m"), 3.8f);
            var f = RFr.Yaw(new Vector3(p.x, g, p.y), Mathf.Atan2(-n.x, -n.z) * Mathf.Rad2Deg);
            // blue band, duty window ribbon, door, canopy; barrier arm (T1_stripes) beside it
            RBox(det, T7("flat"), f, new Vector3(0, H - .7f, -.04f), new Vector3(9.6f, .35f, .06f), RX("2E5E9E"), RALL6);
            RBox(det, T7("glass_d"), f, new Vector3(-2.6f, 1.75f, -.03f), new Vector3(3.6f, 1.1f, .04f), Color.white, RALL6);
            RBox(det, T7("flat_metal"), f, new Vector3(-2.6f, 1.75f, -.04f), new Vector3(3.8f, 1.3f, .02f), RX("D9DBDC"), RALL6);
            RBox(det, T7("flat_metal"), f, new Vector3(0, 1.05f, -.03f), new Vector3(1.1f, 2.1f, .06f), RX("5C6266"), RALL6);
            RBox(det, T7("flat"), f, new Vector3(0, 2.55f, -.8f), new Vector3(2.4f, .15f, 1.6f), RX("C9C6BF"), RALL6);
            var st = T1M("T1_stripes");
            if (st)
            {
                string k = RSurfKey("t1:stripes", st, 1f);
                RBox(det, T7("flat_metal"), f, new Vector3(3.4f, .55f, -2.2f), new Vector3(.3f, 1.1f, .3f), RX("D9DBDC"), RALL5);
                RBox(det, k, f, new Vector3(3.4f + 3f, 1f, -2.2f), new Vector3(6f, .12f, .12f), Color.white, RALL6);
            }
            var details = go.Find("details") ?? new GameObject("details").transform; details.SetParent(go, false);
            RFlush(det, details, "B_" + id + "_T29");
            Done("T29 KPP band / window / canopy / barrier");
        }

        static void Shop24T27(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var fd = FaceDoor(b, fp); if (fd == null) return;
            var (p, n, d) = fd.Value;
            var det = new RBatch();
            float g = Height(p.x, p.y);
            var f = RFr.Yaw(new Vector3(p.x, g, p.y), Mathf.Atan2(-n.x, -n.z) * Mathf.Rad2Deg);
            // storefront glass + grilles either side of the door, "24" light box over it, canopy
            string glass = T7("glass_d"), grille = RSurfKey("t1:grille", T1M("T1_grille") ?? RS["flat"].M, 1f, true);
            foreach (int s in new[] { -1, 1 })
            {
                RBox(det, glass, f, new Vector3(s * 4.2f, 1.5f, -.03f), new Vector3(5f, 1.8f, .04f), Color.white, RALL6);
                RBox(det, grille, f, new Vector3(s * 4.2f, 1.5f, -.07f), new Vector3(5f, 1.8f, .01f), Color.white, RZN);
                RBox(det, T7("flat"), f, new Vector3(s * 4.2f, .55f, -.15f), new Vector3(5.2f, .08f, .3f), RX("C9C6BF"), RALL6);
            }
            RBox(det, T7("flat_metal"), f, new Vector3(0, 1.1f, -.03f), new Vector3(1.4f, 2.2f, .06f), RX("4F5A60"), RALL6);
            RBox(det, T7("flat"), f, new Vector3(0, 2.75f, -.9f), new Vector3(4f, .15f, 1.8f), RX("8E9294"), RALL6);
            var s24 = T1M("T1_sign24");
            if (s24) RBox(det, RSurfKey("t1:sign24", s24, 1f, true), f, new Vector3(0, 3.25f, -.1f), new Vector3(2.8f, .7f, .2f), Color.white, RALL6);
            var details = go.Find("details") ?? new GameObject("details").transform; details.SetParent(go, false);
            RFlush(det, details, "B_" + id + "_T27");
            Done("T27 shop 24 front + light box");
        }

        // ================================================================== Extras hooks
        // fences: styled geometry by district (visuals), the W85 Fence() box colliders stay; T31 veil net on every chain-link
        static string FenceStyle(string district, string id, string mat)
        {
            if (district.Contains("elite") && id.Contains("fence")) return "e2";
            if (district.Contains("construction")) return "c2";
            if (district.Contains("valley")) return "q3";
            if (district.Contains("port")) return "p3";
            return null;
        }

        static void AfterFence(Transform parent, string id, Vector2[] pl, bool closed, float h, List<(Vector2 c, float w)> gaps, string district, string mat)
        {
            var holder = parent.Find("Fence_" + id); if (!holder) return;
            var mesh = holder.Find("FenceMesh_" + id);
            string style = FenceStyle(district, id, mat);
            if (district.Contains("tramduro") && id.Contains("perimeter"))
            {   // T122 a: concrete wall + barbed strands on outriggers (line as given, the gap = the gate)
                if (T2Gen("T122", 'a', holder, pl, closed) != null && mesh) { Object.DestroyImmediate(mesh.GetComponent<MeshRenderer>()); }
                return;
            }
            if (style != null)
            {
                StyledFence(holder, id, pl, closed, h, gaps, style);
                if (mesh) Object.DestroyImmediate(mesh.gameObject);
                return;
            }
            if (!mesh) return;
            var mr = mesh.GetComponent<MeshRenderer>();
            if (mat == "fence_net" && T1M("T1_T31b_net")) { mr.sharedMaterial = T1M("T1_T31b_net"); mr.shadowCastingMode = ShadowCastingMode.Off; Done("T31 chain-link veil"); }
            else if (district.Contains("rough") && id.Contains("football") && id.EndsWith("_board") && T1M("T1_T34a_boards")) { mr.sharedMaterial = T1M("T1_T34a_boards"); Done("T34 football boards"); }
            else if (district.Contains("rough") && mat == "concrete_panel_SK3c" && T1M("T1_T33b_panel")) { mr.sharedMaterial = T1M("T1_T33b_panel"); Done("T33 PO-2 panels"); }
        }

        static GameObject T2Gen(string code, char v, Transform parent, Vector2[] line, bool closed)
        {
            try
            {
                var go = OnlyVolunteers.Art.MapTexturesW86.TexW86T2.GenerateLine(code, v, parent, line, q => Height(q.x, q.y), Gen + "/Meshes/T2", closed);
                if (go) { foreach (var t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic); Done("T2 " + code + " line"); }
                return go;
            }
            catch (Exception e) { RolloutIssue($"T2 line {code} failed: {e.Message}"); return null; }
        }

        // T97 a: Elite plot hedges as T2 hedge lines (the W85 cube renderers off, their colliders kept)
        static void HedgeT97(Transform parent, Dictionary<string, object> z, string id)
        {
            var hd = Obj(Get(z, "hedge")); var hl = V2s(Get(hd, "line")); if (hl.Length < 2) return;
            var gp = Obj(Get(z, "gate"));
            var runs = new List<List<Vector2>> { new() };
            var pts = Resample(hl, .5f);
            foreach (var q in pts)
            {
                bool gap = gp != null && (V2(Get(gp, "pos")) - q).magnitude < F(Get(gp, "w_m"), 5f) * .5f + .3f;
                if (gap) { if (runs[runs.Count - 1].Count > 0) runs.Add(new List<Vector2>()); continue; }
                runs[runs.Count - 1].Add(q);
            }
            int n = 0;
            foreach (var r in runs.Where(r => r.Count >= 2))
            {   // one holder per run: the T2 mesh asset is named after the parent (same parent = the meshes overwrite each other)
                var holder = new GameObject($"Hedge_T97_{id}_{n}").transform; holder.SetParent(parent, false);
                if (T2Gen("T97", 'a', holder, r.ToArray(), false) != null) n++;
            }
            if (n > 0)
                foreach (Transform t in parent.Cast<Transform>().Where(t => t.name == "Hedge_" + id).ToList())
                { var mr = t.GetComponent<MeshRenderer>(); if (mr) Object.DestroyImmediate(mr); var mf = t.GetComponent<MeshFilter>(); if (mf) Object.DestroyImmediate(mf); }
        }

        // T98 a: Elite pools on a raised teak deck: terrain holes under the basin, the generated basin, water at deck top - 0.12 m
        static readonly List<Vector2[]> PoolHoles = new();
        static float ElitePoolLevel(Dictionary<string, object> z, List<Dictionary<string, object>> zones, out bool ok)
        {
            ok = false;
            string id = S(Get(z, "id"), "");
            var deck = zones.FirstOrDefault(o => S(Get(o, "kind")) == "pool_deck" && S(Get(o, "id"), "") == id.Replace("-pool", "-deck"));
            var poly = V2s(Get(z, "poly")); if (poly.Length != 4 || deck == null) return 0f;
            float terrace = F(Get(z, "abs_height_m"), poly.Average(q => Height(q.x, q.y)));
            Vector2 c = poly.Aggregate(Vector2.zero, (s, q) => s + q) / 4;
            Vector2 e0 = poly[1] - poly[0], e1 = poly[2] - poly[1];
            Vector2 ax = (e0.magnitude >= e1.magnitude ? e0 : e1).normalized;
            float yaw = -Mathf.Atan2(ax.y, ax.x) * Mathf.Rad2Deg;                        // frame x = the long edge
            var dpoly = V2s(Get(deck, "poly"));
            float dl = dpoly.Length == 4 ? Mathf.Max((dpoly[1] - dpoly[0]).magnitude, (dpoly[2] - dpoly[1]).magnitude) : 21f;
            float dd = dpoly.Length == 4 ? Mathf.Min((dpoly[1] - dpoly[0]).magnitude, (dpoly[2] - dpoly[1]).magnitude) : 9.5f;
            var f = RFr.Yaw(new Vector3(c.x, terrace, c.y), yaw);
            Vector3 origin = f.O + f.F * .2f;                                            // the T2 basin sits 0.2 m towards -Z of its frame
            var holder = new GameObject("Pool_" + id + "_T98").transform; holder.SetParent(poolParent, false);
            var g = T2Gen("T98", 'a', holder, origin, yaw, new Vector3(dl, .3f, dd));
            if (!g) return 0f;
            // walkable deck + basin colliders (terrain is cut under the basin)
            var fo = RFr.Yaw(origin, yaw);
            float pl = Mathf.Min(14f, dl - 4f), pd = Mathf.Min(5.4f, dd - 2.5f), pz = -.2f, cw = .35f;
            var cols = new GameObject("colliders").transform; cols.SetParent(holder, false);
            AddBoxLocal(cols, fo, new Vector3(0, .15f - .25f, (-dd / 2 + (pz - pd / 2 - cw)) / 2), new Vector3(dl, .5f, (pz - pd / 2 - cw) + dd / 2));
            AddBoxLocal(cols, fo, new Vector3(0, .15f - .25f, (dd / 2 + (pz + pd / 2 + cw)) / 2), new Vector3(dl, .5f, dd / 2 - (pz + pd / 2 + cw)));
            AddBoxLocal(cols, fo, new Vector3((-dl / 2 - pl / 2 - cw) / 2, .15f - .25f, pz), new Vector3(dl / 2 - pl / 2 - cw, .5f, pd + 2 * cw));
            AddBoxLocal(cols, fo, new Vector3((dl / 2 + pl / 2 + cw) / 2, .15f - .25f, pz), new Vector3(dl / 2 - pl / 2 - cw, .5f, pd + 2 * cw));
            AddBoxLocal(cols, fo, new Vector3(0, .3f - 1.5f - .1f, pz), new Vector3(pl, .2f, pd));
            foreach (int s in new[] { -1, 1 }) { AddBoxLocal(cols, fo, new Vector3(s * (pl / 2 + .1f), .3f - .75f, pz), new Vector3(.2f, 1.5f, pd)); AddBoxLocal(cols, fo, new Vector3(0, .3f - .75f, pz + s * (pd / 2 + .1f)), new Vector3(pl + .4f, 1.5f, .2f)); }
            // terrain holes under the basin (+ 0.3 m under the coping)
            Vector2 R2 = new(fo.R.x, fo.R.z), F2 = new(fo.F.x, fo.F.z), o2 = new Vector2(origin.x, origin.z) + F2 * pz;
            PoolHoles.Add(new[] { o2 - R2 * (pl / 2 + .3f) - F2 * (pd / 2 + .3f), o2 + R2 * (pl / 2 + .3f) - F2 * (pd / 2 + .3f), o2 + R2 * (pl / 2 + .3f) + F2 * (pd / 2 + .3f), o2 - R2 * (pl / 2 + .3f) + F2 * (pd / 2 + .3f) });
            ok = true;
            Done("T98 pool (basin + deck + terrain hole)");
            return origin.y + .3f - .12f;
        }
        static Transform poolParent;

        static void CutPoolHoles()
        {
            if (PoolHoles.Count == 0 || !Ter || lastHoles == null) return;
            var td = Ter.terrainData; int R = lastHoles.GetLength(0); int n = 0;
            foreach (var poly in PoolHoles)
            {
                float x0 = poly.Min(q => q.x), x1 = poly.Max(q => q.x), z0 = poly.Min(q => q.y), z1 = poly.Max(q => q.y);
                int i0 = Mathf.FloorToInt(x0 / W * R), i1 = Mathf.CeilToInt(x1 / W * R), j0 = Mathf.FloorToInt(z0 / Hh * R), j1 = Mathf.CeilToInt(z1 / Hh * R);
                for (int j = Mathf.Max(0, j0); j <= Mathf.Min(R - 1, j1); j++)
                    for (int i = Mathf.Max(0, i0); i <= Mathf.Min(R - 1, i1); i++)
                    {
                        Vector2 cc = new((i + .5f) * W / R, (j + .5f) * Hh / R);
                        if (W76Atmosphere.Inside(poly, cc) && lastHoles[j, i]) { lastHoles[j, i] = false; n++; }
                    }
            }
            td.SetHoles(0, 0, lastHoles);
            Note($"T98 pools: {PoolHoles.Count} basins, {n} terrain hole cells cut");
        }

        // ================================================================== post pass: T1 / T2 materials by W85 object name
        static void W86PostPass(Transform root)
        {
            int n = 0;
            void Set(Transform t, Material m, string what, bool noShadow = false)
            {
                if (!t || !m) return;
                var mr = t.GetComponent<MeshRenderer>(); if (!mr) return;
                mr.sharedMaterial = m; if (noShadow) mr.shadowCastingMode = ShadowCastingMode.Off;
                n++; Done(what);
            }
            var all = root.GetComponentsInChildren<Transform>(true).ToList();
            Transform Named(string name) => all.FirstOrDefault(t => t.name == name);
            IEnumerable<Transform> Prefix(string p) => all.Where(t => t.name.StartsWith(p));
            // --- world: bridges (T125 Tramduro = T2 a, T126 valley = T1 b), tunnel (T127 b portals, T128 a shell), retaining walls (X02 a)
            foreach (var part in new[] { "kerbs", "slab", "parapets" }) Set(Named("Bridge_bridge_tramduro_" + part), T2M("T2M_T125a_" + part), "T125 Tramduro bridge (T2 a)");
            foreach (var t in Prefix("Pier_bridge_tramduro_")) Set(t, T2M("T2M_T125a_piers"), "T125 Tramduro bridge (T2 a)");
            foreach (var t in Prefix("BridgeSpan_")) Set(t, T1M("T1_T125b_concrete"), "T126 bridge to the valley (T1 b)");
            foreach (var t in Prefix("Portal_")) { MetreUV(t, 4f); Set(t, T1M("T1_P_b"), "T127 portals (T1 b)"); }
            Set(Named("Tunnel_shell"), T1M("T1_T128a_shell"), "T128 tunnel shell (T1 a)");
            var rw = Named("RetainingWalls");
            if (rw) foreach (Transform t in rw)
                {
                    bool villa = t.name.Contains("07-V");
                    Set(t, MapReadyT7("rubble_grey", t.name.Contains("_inner") || villa ? Tile("cobble_SK2c") : Tile("concrete_SK3c")), villa || t.name.Contains("elite") ? "E2 rubble walls" : "X02 retaining walls (rubble)");
                }
            // --- forest / hamlet water: T05 b bog without the rim + duckweed plane, T19 b jetty
            foreach (var t in Prefix("Water_Bog_"))
            {
                Set(t, T1M("T1_T05b_water"), "T05 bog water");
                var dw = T1M("T1_T05b_duckweed");
                if (dw) { var c = Object.Instantiate(t.gameObject, t.parent); c.name = t.name + "_duckweed"; c.transform.position += Vector3.up * .02f; var mr = c.GetComponent<MeshRenderer>(); mr.sharedMaterial = dw; mr.shadowCastingMode = ShadowCastingMode.Off; }
            }
            foreach (var t in Prefix("Zone_02-FISH-DOCK")) { Set(t, T1M("T1_T19b_deck"), "T19 jetty deck"); JettyPiles(t); }
            // --- Downtown yards (T66 c), port yard / pier (T89 b, T90 b), Elite piers (T100 b), beach (T112 b, T113 b), Tramduro concrete (XT1 a)
            foreach (var t in all.Where(t => t.name.StartsWith("Zone_05-") && (t.name.Contains("yard") || t.name.Contains("forecourt") || t.name.Contains("parking")))) Set(t, T1M("T1_T66c_slabs"), "T66 Downtown yards (slabs)");
            foreach (var nm in new[] { "Zone_06-yard", "Zone_06-09-loading-apron" }) Set(Named(nm), T2M("T2M_T89b_yard"), "T89 port yard");
            foreach (var t in Prefix("Pier_06-")) Set(t, T2M("T2M_T90b_pier"), "T90 port pier");
            foreach (var t in Prefix("PierSkirt_06-")) Set(t, T2M("T2M_T90b_skirt"), "T90 port pier");
            foreach (var t in all.Where(t => t.name.StartsWith("Pier_07-pier") || t.name.StartsWith("PierSkirt_07-pier"))) Set(t, T2M("T2M_T100b_deck"), "T100 Elite piers");
            foreach (var t in all.Where(t => t.name.StartsWith("Pier_09-") || t.name.StartsWith("PierSkirt_09-") || t.name.StartsWith("Boardwalk_09-"))) Set(t, T2M("T2M_T112b_deck"), "T112 beach boards");
            Set(Named("Zone_09-pier-square"), T2M("T2M_T113b_plaza"), "T113 pier square");
            foreach (var t in all.Where(t => t.name.StartsWith("Zone_10-") && (t.name.Contains("concrete") || t.name.Contains("helipad") || t.name.Contains("apron")))) Set(t, T2M("T2M_XT1a_concrete"), "XT1 Tramduro concrete");
            // --- XT1 a: Tramduro helipad on its +3 m platform (data 10-helipad_hill: the terrain has no raised cap) + the T2 pad markings
            HelipadXT1(Named("Zone_10-helipad"), Named("District_tramduro"));
            // --- DC3 square paving (cool grey slabs)
            Set(Named("Zone_05-04-plaza"), DcPaving(), "DC3 square paving");
            // --- Elite stone road (E2: sandstone setts, rubble parapet)
            Set(Named("Road_elite_stone_road"), MapReadyT7("setts_sand", Tile("cobble_SK2c")), "E2 stone road (setts)");
            Set(Named("Parapet_elite_stone_road"), MapReadyT7("rubble_grey", 2f), "E2 stone road parapet");
            // --- Rough: masts (T36 b), prop tints (T37 b / T38 b / T40 b / T41 b), Downtown umbrellas T57 c
            foreach (var t in Prefix("04-box-floodlight")) Set(t, T1M("T1_T36b_mast"), "T36 floodlight masts");
            int tinted = 0;
            var rough = Named("District_rough");
            if (rough)
                foreach (Transform t in rough)
                {
                    string code = t.name.StartsWith("04-yard") || t.name.StartsWith("04-turnik") || t.name.StartsWith("04-play") ? "T37b" : t.name.StartsWith("04-trash") || t.name.Contains("bin") ? "T38b" : t.name.StartsWith("04-car") ? "T40b" : null;
                    if (code != null) tinted += PropTint(t, code);
                }
            var det = Named("Details_by_rules");
            if (det) foreach (Transform t in det) if (t.name.StartsWith("bench_soviet") || t.name.StartsWith("trashbin_concrete")) tinted += PropTint(t, "T41b");
            foreach (var t in Prefix("05-pav-umbrella")) tinted += PropTint(t, "T57c");
            if (tinted > 0) Done("T37 / T38 / T40 / T41 / T57 prop tints (renderers)", tinted);
            // --- beach props: T108 b lifeguard towers, T109 a umbrellas, T110 b loungers, T102 b Elite loungers / umbrellas
            BeachProps(Named("District_beach"), Named("District_elite"));
            Note($"W86 post pass: {n} renderers re-materialled");
        }

        static void HelipadXT1(Transform pad, Transform district)
        {
            if (!pad || !district) return;
            var r = pad.GetComponent<MeshRenderer>(); if (!r) return;
            var bb = r.bounds; float g = bb.center.y - .04f, top = g + 3f;
            Vector2 c = new(bb.center.x, bb.center.z); float h = Mathf.Max(bb.size.x, bb.size.z) / 2f, H2 = h + 4f;
            var mb = new MB();
            Vector3 T(float x, float z) => new(c.x + x, top, c.y + z);
            Vector3 Bm(float x, float z) => new(c.x + x, g - .3f, c.y + z);
            // sloped sides (4) of the frustum, a west access ramp 8 m wide
            mb.QuadBoth(Bm(-H2, -H2), T(-h, -h), T(h, -h), Bm(H2, -H2), Vector2.zero, new(0, 1), new(1, 1), new(1, 0));
            mb.QuadBoth(Bm(H2, -H2), T(h, -h), T(h, h), Bm(H2, H2), Vector2.zero, new(0, 1), new(1, 1), new(1, 0));
            mb.QuadBoth(Bm(H2, H2), T(h, h), T(-h, h), Bm(-H2, H2), Vector2.zero, new(0, 1), new(1, 1), new(1, 0));
            mb.QuadBoth(Bm(-H2, H2), T(-h, h), T(-h, -h), Bm(-H2, -H2), Vector2.zero, new(0, 1), new(1, 1), new(1, 0));
            mb.QuadBoth(new Vector3(c.x - h - 16f, g - .05f, c.y - 4f), new Vector3(c.x - h - 16f, g - .05f, c.y + 4f), T(-h, 4f), T(-h, -4f), Vector2.zero, new(0, 2), new(4, 2), new(4, 0));
            for (int i = 0; i < mb.UV.Count; i++) mb.UV[i] = new Vector2(mb.V[i].x, mb.V[i].z) / 4f;
            var m = mb.Build("Helipad_platform_XT1");
            var go = MeshGo("Helipad_platform_XT1", district, m, T2M("T2M_XT1a_concrete") ?? Mat("concrete_SK3c"), true);
            pad.position += Vector3.up * 3f;                                               // the pad surface on the cap
            Physics.SyncTransforms();
            T2Gen("XT1heli", 'a', district, new Vector3(c.x, top + .045f, c.y), 0f, new Vector3(24f, 0f, 24f));
            Done("XT1 helipad platform (+3 m) + markings");
        }

        // a primitive cube scaled to its box: UVs re-made in metres / tile (the primitive stretches 0..1 over each face)
        static readonly Dictionary<string, Mesh> MetreBoxCache = new();
        static void MetreUV(Transform t, float tile)
        {
            var mf = t.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || mf.sharedMesh.name != "Cube") return;
            Vector3 s = t.localScale;
            string key = $"{s.x:0.00}_{s.y:0.00}_{s.z:0.00}_{tile}";
            if (!MetreBoxCache.TryGetValue(key, out var m) || !m)
            {
                m = Object.Instantiate(mf.sharedMesh); m.name = "W86_box_" + key;
                var v = m.vertices; var n = m.normals; var uv = new Vector2[v.Length];
                for (int i = 0; i < v.Length; i++)
                {
                    Vector3 p = Vector3.Scale(v[i], s), a = n[i];
                    uv[i] = Mathf.Abs(a.y) > .5f ? new Vector2(p.x, p.z) / tile : Mathf.Abs(a.x) > .5f ? new Vector2(p.z, p.y) / tile : new Vector2(p.x, p.y) / tile;
                }
                m.uv = uv;
                AssetDatabase.CreateAsset(m, Gen + "/Meshes/" + Safe(m.name) + ".asset");
                MetreBoxCache[key] = m;
            }
            mf.sharedMesh = m;
        }

        static int PropTint(Transform t, string code)
        {
            int k = 0;
            foreach (var r in t.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mats = r.sharedMaterials; bool ch = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (!mats[i]) continue;
                    var tm = AssetDatabase.LoadAssetAtPath<Material>(T1Mat + "PropTint/T1_" + mats[i].name + "_" + code + ".mat");
                    if (tm) { mats[i] = tm; ch = true; }
                }
                if (ch) { r.sharedMaterials = mats; k++; }
            }
            return k;
        }

        static void JettyPiles(Transform deck)
        {
            var mf = deck.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) return;
            var bark = T1M("T1_k_bark"); if (!bark) return;
            var b = new RBatch(); string k = RSurfKey("t1:k_bark", bark, 1f);
            var v = mf.sharedMesh.vertices; float top = v.Max(q => q.y);
            var hull = v.Select(q => new Vector2(q.x, q.z)).ToList();
            Vector2 c = hull.Aggregate(Vector2.zero, (s, q) => s + q) / hull.Count;
            foreach (var q in hull.Distinct()) { Vector2 p = Vector2.Lerp(q, c, .08f); RCyl(b, k, new Vector3(p.x, Mathf.Min(Height(p.x, p.y), top - 1f) - .5f, p.y), .11f, top - (Mathf.Min(Height(p.x, p.y), top - 1f) - .5f), 8, RS[k].Own); }
            RFlush(b, deck.parent, deck.name + "_piles");
        }

        static void SetMatsAll(Transform t, Material[] want)
        {
            foreach (var r in t.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < Mathf.Min(mats.Length, want.Length); i++) if (want[i]) mats[i] = want[i];
                r.sharedMaterials = mats;
            }
        }

        static void BeachProps(Transform beach, Transform elite)
        {
            int n = 0;
            var white = T2P("T2P_white"); var chrome = T2P("T2P_chrome"); var whiteP = T2P("T2P_white_plastic"); var teal = T2P("T2P_c_2FA3A8");
            string[] canopy = { "E8735E", "2FA3A8", "F2C14E", "8FD3B8", "EE8FA8" };
            if (beach)
                foreach (Transform t in beach)
                {
                    string nm = t.name;
                    var r = t.GetComponentInChildren<MeshRenderer>(); if (!r) continue;
                    var mats = r.sharedMaterials;
                    if (nm.StartsWith("09-lifeguard"))
                    {   // T108 b: Miami pastel towers (slots MP_Concrete, MP_White, MP_Wood, MP_Wood_Dark, MP_Red)
                        var col = T2P(nm.EndsWith("0") ? "T2P_c_F4D35E" : "T2P_c_9BD08A"); var red = T2P("T2P_c_E8735E");
                        SetMatsAll(t, new[] { null, col, white, white, red }); n++; continue;
                    }
                    if (PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject) is GameObject src)
                    {
                        if (src.name.StartsWith("beach_umbrella"))
                        {   // T109 a: Miami pastel canopy colours per instance
                            var c = T2P("T2P_c_" + canopy[(int)(RHash(nm, 3) * canopy.Length) % canopy.Length]);
                            SetMatsAll(t, new[] { null, white, chrome, c, white }); n++;
                        }
                        else if (src.name.StartsWith("beach_sunlounger"))
                        {   // T110 b: white frames, white plastic beds, every third teal
                            SetMatsAll(t, new[] { white, RHash(nm, 4) < .34f ? teal : whiteP }); n++;
                        }
                    }
                }
            if (elite)
                foreach (Transform t in elite)
                {
                    if (!(PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject) is GameObject src)) continue;
                    var r = t.GetComponentInChildren<MeshRenderer>(); if (!r) continue;
                    var mats = r.sharedMaterials;
                    if (src.name.StartsWith("beach_sunlounger")) { SetMatsAll(t, new[] { T2P("T2P_T102b_frame"), T2P("T2P_T102b_bed") }); n++; }
                    else if (src.name.StartsWith("beach_umbrella")) { SetMatsAll(t, new[] { null, T2P("T2P_T102b_pole"), T2P("T2P_T102b_pole"), T2P("T2P_T102b_canopy"), T2P("T2P_T102b_canopy2") }); n++; }
                }
            if (n > 0) Done("T102 / T108 / T109 / T110 beach + Elite prop colours", n);
        }

        // ================================================================== T130 b: foam ring at the foot of each waterfall
        static void FoamRingT130(Transform parent, string id, Vector2 foot, Vector2 dir, float level)
        {
            var m = T1M("T1_foam_ring"); if (!m) return;
            var mb = new MB(); Vector2 r = new(dir.y, -dir.x);
            Vector2 a = foot - r * 4.5f - dir * 3.5f, b = foot + r * 4.5f - dir * 3.5f, c = foot + r * 4.5f + dir * 3.5f, d = foot - r * 4.5f + dir * 3.5f;
            float y = level + .03f;
            mb.Quad(new Vector3(a.x, y, a.y), new Vector3(d.x, y, d.y), new Vector3(c.x, y, c.y), new Vector3(b.x, y, b.y), new(0, 0), new(0, 1), new(1, 1), new(1, 0));
            var go = MeshGo("FoamRing_" + id, parent, mb.Build("FoamRing_" + id), m);
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            Done("T130 foam rings");
        }

        // ================================================================== decal hooks for the next agent (T123 / T124 / T134): targets only
        static void W86DecalHooks(Transform root)
        {
            var hooks = new GameObject("DecalHooks_W86").transform; hooks.SetParent(root, false);
            void H(string name, string note) { var g = new GameObject(name); g.transform.SetParent(hooks, false); g.AddComponent<W86DecalHook>().Note = note; }
            H("T123_road_markings", "T1 pick b: T1_dec_marks_b (worn T1_dec_marks_c on the Rough ring); targets Roads/Road_* (A5 asphalt), District_downtown/Streets/Street_*");
            H("T124_road_wear", "T1 pick b: T1_dec_wear_b (row 3 Rough extras on Road_rough_ring); targets Roads/Road_*, District_rough/Road_*");
            H("T134_shore_foam", "T1 pick b: T1_dec_foam_b strip along the sea shoreline (3.2 m wide, 1.2 m into the water, sea level + 4 cm)");
        }
    }
}
