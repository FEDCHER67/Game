using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // v04 look ROLLOUT (Fedya 21.10 "раскатывай"): the approved texture-test v04 houses generated on every W85 footprint of their type.
    //  Hamlet   'house'                  -> H5 log house: HH_House_v03 model fitted to the footprint, trim colourways a / b / c and a dark
    //                                       roof tint per house (hash of the id), door side = data entrance; no street lamps in the Hamlet;
    //  Rough    'khrushchevka*'          -> R2c: KH2 panel, window atlas with varied G-R glass, 3D balconies / entrances / drainpipes, gas
    //                                       pipe, parapets (port of TextureTestHousesV04.Khrushchevka, any length / depth / floors, arches);
    //  Downtown 'house' / 'alley_plug'   -> D4: D1 composition (storefront ground floor, trim belt, cornice, recessed windows with sills),
    //                                       plaster + brick in the D4 range of hues, G-D glazing, rare awnings, fire escapes / AC on the
    //                                       alley and yard sides, blind party walls (port of TextureTestHousesV04.DtBuilding3, any rect).
    // Shared materials only: the test's own (Art/TextureTest_v01/Built_v04, never rebuilt from here), colour = vertex colour (Palette19
    // _TintRef) or one of the test's existing accent materials; new: 6 darker HH roof variants. Colliders: W85 bodies (+ roof test) for
    // R2c / D4, the house's own UCX hulls for H5. A failed house falls back to the generic W85 house (logged).
    public static partial class W85Builder
    {
        const string TTB = "Assets/OnlyVolunteers/Art/TextureTest_v01/Built_v04";
        const string V19Mat = "Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02/Materials/";
        static bool rollout;
        static int rolledH, rolledR, rolledD, hhMiss;
        sealed class RSurf { public Material M; public float TU = 1f, TV = 1f; public Color Own = Color.white; }
        static readonly Dictionary<string, RSurf> RS = new();
        static readonly Dictionary<string, GameObject> RKit = new();
        static readonly Dictionary<string, Material> RKitM = new();
        static readonly Dictionary<string, Material> HHM = new();
        static GameObject HHAsset;
        static Bounds HHWalls;                                                    // wall + plinth bounds of the house model (its own frame)
        static readonly List<(string id, Vector2[] fp)> DistrictFps = new();
        static readonly List<(Vector2[] line, float half)> DistrictStreets = new();
        static readonly List<string> RolloutIssues = new();

        static void RolloutInit()
        {
            rollout = false; RS.Clear(); RKit.Clear(); RKitM.Clear(); HHM.Clear(); HHAsset = null; RolloutIssues.Clear();
            rolledH = rolledR = rolledD = hhMiss = rolledO = 0; sepVariants.Clear();
            Folder(Gen + "/Materials/Rollout");
            void T(string key, string file, float tu, float tv) => RS[key] = RSurfOf(AssetDatabase.LoadAssetAtPath<Material>(TTB + "/Materials/" + file + ".mat"), tu, tv);
            T("KH2", "TT_KH2", 6.4f, 5.6f);
            T("atlas", "TT_KH_windows_atlas_clip", 10.24f, 1f);
            T("atlas_dusty", "TT_KH_windows_atlas_dusty", 1f, 1f);
            T("atlas_dirty", "TT_KH_windows_atlas_dirty", 1f, 1f);
            T("atlas_blend", "TT_KH_windows_atlas_streaks", 1f, 1f);
            T("flat", "TT_flat", 1f, 1f);
            T("acg_plaster", "TT_acg_plaster", 3f, 3f);
            T("brick_paint", "TT_brick_paint", 3f, 3f);
            T("trim", "TT_trim", 2f, .45f);
            T("glass_dt", "TT_Glass_Downtown", 1f, 1f);
            RS["concrete"] = RSurfOf(AssetDatabase.LoadAssetAtPath<Material>(V19Mat + "V19_V3S17_3c_concrete_panels_857C6E.mat"), 4f, 4f);
            RS["roof_flat"] = RSurfOf(AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/LookV3/Materials/V3S_4d_flat_bitumen_roof.mat"), 4f, 4f);
            RS["hh_plinth"] = RSurfOf(AssetDatabase.LoadAssetAtPath<Material>(TTB + "/Materials/House/TT_HH_Plinth.mat"), 3f, 3f);
            RS["sidewalk"] = RSurfOf(Mat("sidewalk_S1"), Tile("sidewalk_S1"), Tile("sidewalk_S1"));      // W86: paved strip in front of set-back facades
            if (Directory.Exists(TTB + "/Kit"))
                foreach (string f in Directory.GetFiles(TTB + "/Kit", "*.fbx"))
                {
                    var go = AssetDatabase.LoadAssetAtPath<GameObject>(f.Replace('\\', '/'));
                    if (go) RKit[Path.GetFileNameWithoutExtension(f)] = go;
                }
            if (Directory.Exists(TTB + "/Materials/Kit"))
                foreach (string f in Directory.GetFiles(TTB + "/Materials/Kit", "*.mat"))
                {
                    var m = AssetDatabase.LoadAssetAtPath<Material>(f.Replace('\\', '/'));
                    if (m && m.name.StartsWith("TT_")) RKitM[m.name.Substring(3)] = m;
                }
            if (Directory.Exists(TTB + "/Materials/House"))
                foreach (string f in Directory.GetFiles(TTB + "/Materials/House", "*.mat"))
                {
                    var m = AssetDatabase.LoadAssetAtPath<Material>(f.Replace('\\', '/'));
                    if (m) HHM[m.name] = m;
                }
            HHAsset = AssetDatabase.LoadAssetAtPath<GameObject>(TTB + "/House/HH_House_v03.fbx");
            if (HHAsset)
            {
                // dark roof tints per house (Fedya 21.10): per colourway the approved roof + two darker shared variants
                foreach (string cw in new[] { "a", "b", "c" })
                {
                    if (!HHM.TryGetValue($"TT_HH_Roof_{cw}_corrugated_weathered", out var r0)) continue;
                    for (int t = 1; t <= 2; t++)
                    {
                        var m = new Material(r0) { name = $"W85_HH_Roof_{cw}_dark{t}", enableInstancing = true };
                        Color c0 = r0.GetColor("_BaseColor");
                        float k = t == 1 ? .78f : .6f;
                        m.SetColor("_BaseColor", new Color(c0.r * k, c0.g * k, c0.b * k, c0.a));
                        AssetDatabase.CreateAsset(m, Gen + "/Materials/Rollout/" + m.name + ".mat");
                        HHM[m.name] = m;
                    }
                }
                // the model's wall + plinth extent (fits the plan footprint; roof overhang, porch and steps stay outside it)
                var probe = Object.Instantiate(HHAsset);
                var pts = new List<Vector3>();
                foreach (var r in probe.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = r.GetComponent<MeshFilter>();
                    if (!mf || !mf.sharedMesh || r.name.StartsWith("UCX_")) continue;
                    var mesh = mf.sharedMesh; var vs = mesh.vertices; var mats = r.sharedMaterials;
                    for (int s = 0; s < Mathf.Min(mesh.subMeshCount, mats.Length); s++)
                        if (mats[s] && (mats[s].name == "TT_HH_Wall" || mats[s].name == "TT_HH_Plinth"))
                            pts.AddRange(mesh.GetTriangles(s).Select(i => probe.transform.InverseTransformPoint(r.transform.TransformPoint(vs[i]))));
                }
                Object.DestroyImmediate(probe);
                if (pts.Count > 0)
                {
                    HHWalls = new Bounds(pts[0], Vector3.zero);
                    foreach (var p in pts) HHWalls.Encapsulate(p);
                }
                else HHAsset = null;
            }
            var missing = RS.Where(kv => !kv.Value.M).Select(kv => kv.Key).ToList();
            rollout = missing.Count == 0 && RKit.Count >= 20 && HHAsset != null;
            Note(rollout
                ? $"v04 rollout: on ({RS.Count} surfaces, {RKit.Count} kit pieces, {RKitM.Count} kit materials, HH house walls {HHWalls.size.x:0.00} x {HHWalls.size.z:0.00} m, eaves {HHWalls.max.y:0.00} m)"
                : "v04 rollout: OFF - missing " + string.Join(", ", missing) + (HHAsset ? "" : ", HH house (or its wall material)") + $", kit pieces {RKit.Count}");
        }

        static RSurf RSurfOf(Material m, float tu, float tv)
        {
            var s = new RSurf { M = m, TU = tu, TV = tv };
            if (!m) return s;
            if (m.HasProperty("_TintRef")) { Vector4 t = m.GetVector("_TintRef"); s.Own = new Color(t.x, t.y, t.z, 1f).gamma; }
            if (m.HasProperty("_DistrictMask") && m.GetTexture("_DistrictMask"))
            {   // V19 palette materials: W85 copy with the i10-space palette field off (as Mat())
                var cp = new Material(m) { name = "W85_" + m.name + "_nofield", enableInstancing = true };
                cp.SetTexture("_DistrictMask", null);
                AssetDatabase.CreateAsset(cp, Gen + "/Materials/Rollout/" + cp.name + ".mat");
                s.M = cp; paletteFixed++;
            }
            return s;
        }

        // district context for the Downtown face classification (party walls / streets); set by BuildDistrict before its buildings
        static void RolloutDistrict(Dictionary<string, object> dj)
        {
            DistrictFps.Clear(); DistrictStreets.Clear();
            foreach (var bo in Arr(Get(dj, "buildings")).Select(Obj))
            {
                if (bo == null || (Get(bo, "disabled") is bool off && off)) continue;
                var fp = V2s(Get(bo, "footprint"));
                if (fp.Length >= 3) DistrictFps.Add((S(Get(bo, "id"), ""), fp));
            }
            foreach (var z in Arr(Get(dj, "zones")).Select(Obj))
            {
                if (z == null || S(Get(z, "kind")) != "street") continue;
                var pl = V2s(Get(z, "poly_line"));
                if (pl.Length >= 2) DistrictStreets.Add((pl, F(Get(z, "carriageway_m"), 12f) * .5f));
            }
        }

        static void RolloutIssue(string s) { if (RolloutIssues.Count < 40 && !RolloutIssues.Contains(s)) RolloutIssues.Add(s); }

        static string RolloutSummary() =>
            $"v04 rollout: Hamlet H5 {rolledH} houses ({hhMiss} roof rays missed), Rough R2c {rolledR} khrushchevkas, Downtown D4 {rolledD} blocks" +
            (sepVariants.Count > 0 ? " (W86 separation, facade variants " + string.Join(" ", sepVariants.OrderBy(kv => kv.Key).Select(kv => kv.Key + " " + kv.Value)) + ")" : "") +
            (rolledO > 0 ? $", offices O {rolledO}" : "") +
            (RolloutIssues.Count > 0 ? "; issues: " + string.Join("; ", RolloutIssues) : "");

        // Building() hook: true = built here (the generic W85 house is skipped)
        static bool TryRollout(Transform parent, Dictionary<string, object> b, string district, string kind, List<Vector2> fp, string id)
        {
            if (!rollout) return false;
            string mode = district.Contains("hamlet") && (kind == "house" || kind == "hut_base2") ? "H5" :
                          district.Contains("rough") && kind.StartsWith("khrushchevka") ? "R2c" :
                          district.Contains("downtown") && (kind == "office" || S(Get(b, "facade_class")) == "office") ? "O" :
                          district.Contains("downtown") && (kind == "house" || kind == "alley_plug" || AccentKinds.Contains(kind)) ? "D4" : null;
            if (mode == null) return false;
            if (mode != "H5" && fp.Count != 4) { RolloutIssue($"{id}: {fp.Count}-point footprint, generic house kept"); return false; }
            var go = new GameObject("B_" + id); go.transform.SetParent(parent, false);
            bool ok;
            try
            {
                ok = mode == "H5" ? RolloutH5(go.transform, b, fp, id) : mode == "R2c" ? RolloutR2c(go.transform, b, fp, id, district) :
                     mode == "O" ? RolloutOfficeO1(go.transform, b, fp, id, district) : RolloutD4(go.transform, b, fp, id, district);
                if (ok && kind == "hut_base2") HutBase2Extras(go.transform, b, fp, id, district);
            }
            catch (Exception e) { ok = false; RolloutIssue($"{id} ({mode}) failed: {e.Message}"); }
            if (!ok) { Object.DestroyImmediate(go); return false; }
            if (mode == "H5") rolledH++; else if (mode == "R2c") rolledR++; else if (mode == "D4") rolledD++;
            return true;
        }

        // body (walls, glass, roof, balconies) stays to 1.2 % of the screen height; details (frames, sills, pipes, parapets, cornices) to 6 %
        static void RolloutLod(GameObject go, Transform details)
        {
            // kit pieces with their own LODGroup (balconies, fire escapes) keep it: a renderer may belong to one LODGroup only
            var nested = new HashSet<Renderer>(go.GetComponentsInChildren<LODGroup>(true).SelectMany(g => g.GetLODs().SelectMany(l => l.renderers)).Where(r => r));
            var all = go.GetComponentsInChildren<Renderer>().Where(r => !nested.Contains(r)).ToArray();
            var det = details.GetComponentsInChildren<Renderer>().Where(r => !nested.Contains(r)).ToArray();
            var lod = go.AddComponent<LODGroup>();
            lod.SetLODs(new[] { new LOD(.06f, all), new LOD(.012f, all.Except(det).ToArray()) });
            lod.RecalculateBounds();
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
        }

        // ================================================================== geometry (port of the texture-test helpers)
        sealed class RMesh
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> U = new(); public readonly List<Color> C = new(); public readonly List<int> T = new();
            public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); V.Add(d); U.Add(ua); U.Add(ub); U.Add(uc); U.Add(ud); C.Add(col); C.Add(col); C.Add(col); C.Add(col);
                T.Add(n); T.Add(n + 1); T.Add(n + 2); T.Add(n); T.Add(n + 2); T.Add(n + 3);
            }
        }

        sealed class RBatch
        {
            public readonly Dictionary<string, RMesh> By = new();
            public RMesh this[string k] { get { if (!By.TryGetValue(k, out var mb)) By[k] = mb = new RMesh(); return mb; } }
        }

        static void RFlush(RBatch b, Transform parent, string name)
        {
            foreach (var kv in b.By)
            {
                var mb = kv.Value;
                if (mb.V.Count == 0) continue;
                var mesh = new Mesh { name = name + "_" + kv.Key, indexFormat = mb.V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.SetVertices(mb.V); mesh.SetUVs(0, mb.U); mesh.SetColors(mb.C); mesh.SetTriangles(mb.T, 0);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + Safe(mesh.name) + ".asset");
                var go = new GameObject(mesh.name); go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = RS[kv.Key].M;
                if (kv.Key.StartsWith("atlas") || RNoShadow.Contains(kv.Key)) r.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            }
        }

        // frame: O + R x + up y + F z (proper rotation, the winding stays right); wall frame: x along the wall, z INTO the wall
        struct RFr
        {
            public Vector3 O, R, F;
            public Vector3 P(float x, float y, float z) => O + R * x + Vector3.up * y + F * z;
            public Vector3 P(Vector3 v) => P(v.x, v.y, v.z);
            public Vector3 D(Vector3 v) => R * v.x + Vector3.up * v.y + F * v.z;
            public static RFr Yaw(Vector3 o, float deg) { var q = Quaternion.Euler(0, deg, 0); return new RFr { O = o, R = q * Vector3.right, F = q * Vector3.forward }; }
            public RFr Wall(Vector2 p0, Vector2 p1)
            {
                Vector2 d = (p1 - p0).normalized; var dir = new Vector3(d.x, 0, d.y);
                return new RFr { O = P(p0.x, 0, p0.y), R = D(dir), F = D(-Vector3.Cross(Vector3.up, dir)) };
            }
            public Vector3 Out => -F;
        }

        static void REdge(float hx, float hz, int i, out Vector2 p0, out Vector2 p1)
        {
            switch (i)
            {
                case 0: p0 = new(-hx, -hz); p1 = new(hx, -hz); break;      // front (-Z)
                case 1: p0 = new(hx, -hz); p1 = new(hx, hz); break;        // +X
                case 2: p0 = new(hx, hz); p1 = new(-hx, hz); break;        // back (+Z)
                default: p0 = new(-hx, hz); p1 = new(-hx, -hz); break;     // -X
            }
        }

        static void RWall(RBatch b, string key, RFr w, float s0, float s1, float y0, float y1, Color col, float vOrigin = 0f, float tu = 0f)
        {
            var s = RS[key]; float TU = tu > 0f ? tu : s.TU;
            Vector2 Uv(float x, float y) => new(x / TU, (y - vOrigin) / s.TV);
            b[key].Quad(w.P(s0, y0, 0), w.P(s0, y1, 0), w.P(s1, y1, 0), w.P(s1, y0, 0), Uv(s0, y0), Uv(s0, y1), Uv(s1, y1), Uv(s1, y0), col);
        }

        static void RDecal(RBatch b, string key, RFr w, float s, float yb, Rect px, float o)
        {
            float wd = px.width / 200f, ht = px.height / 200f;                       // atlas: 200 px per metre, 2048 x 1024
            var uv = Rect.MinMaxRect(px.xMin / 2048f, 1f - px.yMax / 1024f, px.xMax / 2048f, 1f - px.yMin / 1024f);
            b[key].Quad(w.P(s - wd / 2, yb, -o), w.P(s - wd / 2, yb + ht, -o), w.P(s + wd / 2, yb + ht, -o), w.P(s + wd / 2, yb, -o),
                new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }

        const int RXP = 1, RXN = 2, RZP = 4, RZN = 8, RYP = 16, RYN = 32;
        const int RALL5 = RXP | RXN | RZP | RZN | RYP, RALL6 = RALL5 | RYN, ROUT = RXP | RXN | RZN | RYP | RYN;   // ROUT: no face into the wall
        static readonly (Vector3 n, int bit)[] RFaces = { (Vector3.right, RXP), (Vector3.left, RXN), (Vector3.forward, RZP), (Vector3.back, RZN), (Vector3.up, RYP), (Vector3.down, RYN) };
        static float RExt(Vector3 size, Vector3 a) => Mathf.Abs(a.x) * size.x + Mathf.Abs(a.y) * size.y + Mathf.Abs(a.z) * size.z;

        // axis-aligned box in frame f (centre c, size); faces by mask; flip = faces look inward (passages); UV = frame metres / tile
        static void RBox(RBatch b, string key, RFr f, Vector3 c, Vector3 size, Color col, int mask = RALL5, bool flip = false)
        {
            var s = RS[key];
            foreach (var (n, bit) in RFaces)
            {
                if ((mask & bit) == 0) continue;
                Vector3 ua = Mathf.Abs(n.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(n, ua);
                float hw = RExt(size, ra) / 2, hh = RExt(size, ua) / 2;
                Vector3 fc = c + n * RExt(size, n) / 2;
                Vector3 a = fc - ra * hw - ua * hh, bb = fc - ra * hw + ua * hh, cc = fc + ra * hw + ua * hh, d = fc + ra * hw - ua * hh;
                Vector2 Uv(Vector3 p) => new(Vector3.Dot(p, ra) / s.TU, Vector3.Dot(p, ua) / s.TV);
                if (flip) b[key].Quad(f.P(a), f.P(d), f.P(cc), f.P(bb), Uv(a), Uv(d), Uv(cc), Uv(bb), col);
                else b[key].Quad(f.P(a), f.P(bb), f.P(cc), f.P(d), Uv(a), Uv(bb), Uv(cc), Uv(d), col);
            }
        }

        static void RWallBox(RBatch b, string key, RFr w, float s0, float s1, float y0, float y1, float depth, Color col)
            => RBox(b, key, w, new Vector3((s0 + s1) / 2, (y0 + y1) / 2, (-depth + .01f) / 2), new Vector3(s1 - s0, y1 - y0, depth + .01f), col, ROUT);

        static void RPlane(RBatch b, string key, RFr f, float x0, float z0, float x1, float z1, float y, Color col)
        {
            var s = RS[key];
            b[key].Quad(f.P(x0, y, z0), f.P(x0, y, z1), f.P(x1, y, z1), f.P(x1, y, z0),
                new(x0 / s.TU, z0 / s.TV), new(x0 / s.TU, z1 / s.TV), new(x1 / s.TU, z1 / s.TV), new(x1 / s.TU, z0 / s.TV), col);
        }

        // the texture test's hash (with avalanche): the W85 Hash gives nearly equal values for ids that differ only in the last
        // character (bay / floor numbers), which made balconies and glass all-or-nothing per building
        static float RHash(string s, int salt = 0)
        {
            unchecked
            {
                int h = 17 + salt * 7919;
                foreach (char c in s) h = h * 31 + c;
                h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15;
                return (h & 0x7fffffff) / (float)int.MaxValue;
            }
        }

        static Color RX(string hex) { ColorUtility.TryParseHtmlString("#" + hex.TrimStart('#'), out Color c); return c; }
        static string RPick(string[] a, string id, int salt) => a[Mathf.Min(a.Length - 1, (int)(RHash(id, salt) * a.Length))];
        static Material RAcc(string kit, string hex) => RKitM.TryGetValue(kit + "_" + hex, out var m) ? m : RKitM.TryGetValue(kit, out var b) ? b : null;

        // kit piece (texture-test copies of FACADE_KIT_v01 with the TT materials): UCX hulls -> convex colliders on walkable / bumpable
        // pieces (balconies, canopies, steps, fire escapes, tanks, awnings), dropped on the rest (pipes, parapets, cornices, vents, AC)
        static readonly HashSet<string> RSolid = new()
        {
            "FK_R_Balcony_Glazed", "FK_R_Balcony_Open", "FK_R_Entrance_Canopy", "FK_R_Entrance_Steps2", "FK_R_Entrance_Steps3",
            "FK_D_FireEscape_Landing", "FK_D_FireEscape_Stair", "FK_D_RoofWaterTank", "FK_D_Storefront_Awning",
        };

        static GameObject RPiece(string name, Transform parent, Vector3 pos, Vector3 outward, params (string kit, Material with)[] swaps)
        {
            if (!RKit.TryGetValue(name, out var src)) { RolloutIssue("kit piece missing " + name); return null; }
            var go = Object.Instantiate(src, parent);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(outward, Vector3.up));
            bool solid = RSolid.Contains(name);
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true).Where(m => m.name.StartsWith("UCX_")).ToList())
            {
                var o = mf.gameObject; var mesh = mf.sharedMesh;
                Object.DestroyImmediate(o.GetComponent<MeshRenderer>()); Object.DestroyImmediate(mf);
                if (solid && o != go) { var mc = o.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true; }
                else if (o != go) Object.DestroyImmediate(o);
            }
            if (swaps.Length > 0)
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    var mats = r.sharedMaterials;
                    for (int i = 0; i < mats.Length; i++)
                        foreach (var s in swaps)
                            if (s.with && mats[i] && RKitM.TryGetValue(s.kit, out var km) && mats[i] == km) mats[i] = s.with;
                    r.sharedMaterials = mats;
                }
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            return go;
        }

        // ================================================================== Hamlet H5
        static bool RolloutH5(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object>();
            Frame(fp, roof, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            var e0 = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(e => e != null);
            Vector2 dir = -ay;
            if (e0 != null)
            {
                float a = F(Get(e0, "facing_deg")) * Mathf.Deg2Rad;
                dir = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                if (Get(e0, "facing_deg") == null) dir = (V2(Get(e0, "pos")) - c).normalized;
            }
            Vector2 front = new[] { ax, -ax, ay, -ay }.OrderByDescending(v => Vector2.Dot(v, dir)).First();
            bool frontAlongX = Mathf.Abs(Vector2.Dot(front, ax)) > .5f;
            float width = frontAlongX ? 2 * hy : 2 * hx, depth = frontAlongX ? 2 * hx : 2 * hy;
            float sx = Mathf.Clamp(width / Mathf.Max(.5f, HHWalls.size.x), .8f, 1.3f), sz = Mathf.Clamp(depth / Mathf.Max(.5f, HHWalls.size.z), .8f, 1.3f);
            if (Mathf.Abs(width / HHWalls.size.x - sx) > .02f || Mathf.Abs(depth / HHWalls.size.z - sz) > .02f)
                RolloutIssue($"{id}: footprint {width:0.0} x {depth:0.0} m, H5 scaled to its limit ({sx:0.00} / {sz:0.00})");
            float yaw = Mathf.Atan2(front.x, front.y) * Mathf.Rad2Deg;
            var q = Quaternion.Euler(0, yaw, 0);
            float gMin = fp.Min(p => Height(p.x, p.y)), gMax = fp.Max(p => Height(p.x, p.y)), gC = Height(c.x, c.y);
            float y = Mathf.Max(gC, Mathf.Lerp(gMin, gMax, .6f)) - .03f;                 // never buries the door side, the skirt closes the low side
            string cw = RPick(new[] { "a", "b", "c" }, id, 51);
            int tint = RHash(id, 52) < .3f ? 0 : RHash(id, 52) < .65f ? 1 : 2;
            var h = Object.Instantiate(HHAsset, go);
            h.name = "HH_House_v03_" + cw + (tint > 0 ? "_dark" + tint : "");
            h.transform.localScale = new Vector3(sx, 1f, sz);
            Vector3 off = q * new Vector3(HHWalls.center.x * sx, 0f, HHWalls.center.z * sz);
            h.transform.SetPositionAndRotation(new Vector3(c.x - off.x, y, c.y - off.z), q);
            foreach (var mf in h.GetComponentsInChildren<MeshFilter>(true).Where(m => m.name.StartsWith("UCX_")).ToList())
            {
                var o = mf.gameObject; var mesh = mf.sharedMesh;
                Object.DestroyImmediate(o.GetComponent<MeshRenderer>()); Object.DestroyImmediate(mf);
                var mc = o.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true;
            }
            foreach (var r in h.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (!mats[i]) continue;
                    string n = mats[i].name;
                    if (n.StartsWith("TT_HH_Roof_"))
                    {
                        string want = tint == 0 ? $"TT_HH_Roof_{cw}_corrugated_weathered" : $"W85_HH_Roof_{cw}_dark{tint}";
                        if (HHM.TryGetValue(want, out var rm)) mats[i] = rm;
                    }
                    else if (cw != "a" && n == "TT_HH_Wall" && HHM.TryGetValue("TT_HH_Wall_" + cw, out var wm)) mats[i] = wm;
                    else if (cw != "a" && n.EndsWith("_a") && HHM.TryGetValue(n.Substring(0, n.Length - 2) + "_" + cw, out var cm)) mats[i] = cm;
                }
                r.sharedMaterials = mats;
            }
            // plinth skirt down to the ground on the low side (sloped yards), inside the wall line
            if (y - gMin > .06f)
            {
                var sk = new RBatch();
                var fr = RFr.Yaw(new Vector3(c.x, y, c.y), yaw);
                float w2 = HHWalls.size.x * sx - .1f, d2 = HHWalls.size.z * sz - .1f, yb = gMin - .35f - y;
                RBox(sk, "hh_plinth", fr, new Vector3(0, (yb + .1f) / 2, 0), new Vector3(w2, .1f - yb, d2), Color.white, RALL5);
                RFlush(sk, go, "B_" + id + "_skirt");
            }
            foreach (Transform t in h.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            var lod = go.gameObject.AddComponent<LODGroup>();
            lod.SetLODs(new[] { new LOD(.01f, go.GetComponentsInChildren<Renderer>()) });
            lod.RecalculateBounds();
            // roof check (as the W85 roof test): rays straight down over the walls must hit the house's own hulls at eave height or above
            Physics.SyncTransforms();
            var cols = h.GetComponentsInChildren<Collider>();
            float eave = y + HHWalls.max.y - .15f;
            for (float u = -HHWalls.size.x * sx / 2 + .4f; u < HHWalls.size.x * sx / 2 - .3f; u += 1f)
                for (float v = -HHWalls.size.z * sz / 2 + .4f; v < HHWalls.size.z * sz / 2 - .3f; v += 1f)
                {
                    Vector3 p = new Vector3(c.x, y + 30f, c.y) + q * new Vector3(u, 0, v);
                    bool hit = false;
                    foreach (var rh in Physics.RaycastAll(p, Vector3.down, 40f)) if (cols.Contains(rh.collider) && rh.point.y >= eave) { hit = true; break; }
                    if (!hit) hhMiss++;
                }
            return true;
        }

        // ================================================================== Rough R2c (any length / depth / floors; arches)
        static readonly Rect WinWhite = Rect.MinMaxRect(60, 72, 388, 380), WinWood = Rect.MinMaxRect(460, 72, 788, 380), WinPlastic = Rect.MinMaxRect(860, 72, 1188, 380),
            WinStair = Rect.MinMaxRect(1284, 92, 1564, 330), WinKitchen = Rect.MinMaxRect(1690, 72, 1958, 380),
            Streak1 = Rect.MinMaxRect(914, 552, 1124, 872), Streak2 = Rect.MinMaxRect(1314, 532, 1494, 992), Streak3 = Rect.MinMaxRect(1664, 552, 1964, 832);
        static string RGlass(string id) { float h = RHash(id, 21); return h < .4f ? "atlas" : h < .75f ? "atlas_dusty" : "atlas_dirty"; }

        static bool RolloutR2c(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string district)
        {
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object> { ["type"] = "flat" };
            var plain = new Dictionary<string, object>();                            // frame along the longest edge
            Frame(fp, plain, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hz);
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null).ToList();
            var doors = ents.Where(e => { string k = S(Get(e, "kind"), "door"); return k == "podyezd" || k == "door"; }).ToList();
            var archs = ArchesOf(b, fp);                                               // W86: each arch's own clear width / height (6 x 4.5 m)
            float side = 0f;
            foreach (var e in doors)
            {
                float a = F(Get(e, "facing_deg")) * Mathf.Deg2Rad;
                side += Vector2.Dot(new Vector2(Mathf.Cos(a), Mathf.Sin(a)), ay) + .25f * Mathf.Sign(Vector2.Dot(V2(Get(e, "pos")) - c, ay));
            }
            Vector2 frontOut = side >= 0f ? ay : -ay, Fz = -frontOut;
            float yaw = Mathf.Atan2(Fz.x, Fz.y) * Mathf.Rad2Deg;
            float floor0 = Height(c.x, c.y), baseY = fp.Min(q => Height(q.x, q.y)) - .25f;
            int floors = Mathf.Max(1, (int)F(Get(b, "floors"), 5f));
            const float fl0 = .5f, fh = 2.8f;
            float top = floor0 + fl0 + floors * fh, yb = baseY - floor0, tl = top - floor0;
            var f = RFr.Yaw(new Vector3(c.x, floor0, c.y), yaw);
            Vector2 R2 = new(f.R.x, f.R.z);
            float LocalX(Vector2 p) => Vector2.Dot(p - c, R2);
            var details = new GameObject("details").transform; details.SetParent(go, false);
            var kit = new GameObject("kit").transform; kit.SetParent(go, false);
            var body = new RBatch(); var det = new RBatch();
            Color col = RS["KH2"].Own * (.95f + .08f * RHash(id, 31)); col.a = 1f;
            var archX = archs.Select(a => (x: LocalX(a.P), w: a.W, h: a.H)).ToList();
            int front0 = 0;
            for (int i = 0; i < 4; i++)
            {
                REdge(hx, hz, i, out var p0, out var p1);
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                bool front = i == 0, back = i == 2, longSide = front || back;
                int n = longSide ? Mathf.Max(1, Mathf.RoundToInt(L / 3.2f)) : 0;
                float bw = longSide ? L / n : 3.2f;
                float S2(float x) => front ? x + hx : hx - x;                           // local x -> s along this face
                var cuts = longSide ? archX.Select(a => (s: S2(a.x), a.w, a.h)).Where(a => a.s > 1f && a.s < L - 1f).OrderBy(a => a.s).ToList() : new List<(float s, float w, float h)>();
                float tu = longSide ? 2f * bw : 6.4f;                                     // one KH2 tile = two bays (panel seams on the bay grid)
                float cur = 0f;
                foreach (var ct in cuts)
                {
                    float a0 = Mathf.Max(cur, ct.s - ct.w * .5f), a1 = Mathf.Min(L, ct.s + ct.w * .5f);
                    if (a0 > cur) RWall(body, "KH2", w, cur, a0, yb, tl, col, fl0, tu);
                    RWall(body, "KH2", w, a0, a1, ct.h, tl, col, fl0, tu);
                    cur = a1;
                }
                if (cur < L) RWall(body, "KH2", w, cur, L, yb, tl, col, fl0, tu);
                if (longSide)
                {
                    var entBays = new HashSet<int>();
                    foreach (var e in doors)
                    {
                        float a = F(Get(e, "facing_deg")) * Mathf.Deg2Rad;
                        float face = Vector2.Dot(new Vector2(Mathf.Cos(a), Mathf.Sin(a)), frontOut);
                        if (front ? face < .3f : face > -.3f) continue;
                        entBays.Add(Mathf.Clamp(Mathf.FloorToInt(S2(LocalX(V2(Get(e, "pos")))) / bw), 0, n - 1));
                    }
                    if (front) front0 = entBays.Count;
                    for (int k = 0; k < n; k++)
                    {
                        float s = bw * (k + .5f);
                        var archAt = cuts.Where(ct => Mathf.Abs(ct.s - s) < ct.w * .5f + bw * .5f - .2f).ToList();
                        bool archBay = archAt.Count > 0;
                        float archTop = archBay ? archAt.Max(ct => ct.h) : 0f;
                        if (entBays.Contains(k) && !archBay)
                        {
                            RPiece("FK_R_Entrance_Steps3", details, w.P(s, 0, 0), w.Out, ("FK_Concrete", null));
                            RPiece("FK_R_IronDoor", details, w.P(s, .48f, 0), w.Out, ("FK_Metal_Paint", RAcc("FK_Metal_Paint", RHash(id + k, 3) < .5f ? "5E5048" : "4F6A5E")));
                            RPiece("FK_R_Entrance_Canopy", kit, w.P(s, 2.95f, 0), w.Out);
                            for (int fl = 1; fl < floors; fl++) RDecal(body, RGlass(id + i + k + "s" + fl), w, s, fl0 + fl * fh + 1.4f + .85f - .09f - fh / 2 + .5f, WinStair, .025f);
                            continue;
                        }
                        bool balconies = !archBay && (front ? RHash(id + "b" + k, 11) < .45f : RHash(id + "b" + k, 12) < .3f);
                        for (int fl = 0; fl < floors; fl++)
                        {
                            if (archBay && fl0 + fl * fh + .76f < archTop + .3f) continue;      // no window over the arch opening
                            string wid = id + i + "_" + k + "_" + fl;
                            float yf = fl0 + fl * fh, hsh = RHash(wid, 1);
                            Rect win = RHash(wid, 2) < .15f && !balconies ? WinKitchen : hsh < .45f ? WinWhite : hsh < .7f ? WinWood : WinPlastic;
                            RDecal(body, RGlass(wid), w, s, yf + .85f - .09f, win, .025f);
                            if (balconies && fl > 0)
                            {
                                if (RHash(wid, 3) > .45f)
                                    RPiece("FK_R_Balcony_Glazed", kit, w.P(s, yf, 0), w.Out,
                                        ("FK_Window_Frame", RAcc("FK_Window_Frame", RHash(wid, 4) < .5f ? "E6E2D8" : RHash(wid, 4) < .8f ? "8A6A4E" : "C9C2B2")));
                                else RPiece("FK_R_Balcony_Open", kit, w.P(s, yf, 0), w.Out,
                                        ("FK_Metal_Paint", RAcc("FK_Metal_Paint", RHash(wid, 5) < .4f ? "6A786F" : RHash(wid, 5) < .7f ? "7B5E4E" : "5E6E80")));
                            }
                            else if (front && fl > 0 && RHash(wid, 6) > .72f)
                                RDecal(det, "atlas_blend", w, s + (RHash(wid, 7) - .5f) * .4f, yf + .85f - .1f - 1.6f, RHash(wid, 8) > .5f ? Streak1 : Streak3, .018f);
                        }
                        if (front && balconies && RHash(id + k, 9) > .4f) RDecal(det, "atlas_blend", w, s + .9f, fl0 + fh - 2.3f, Streak2, .018f);
                    }
                    if (front)
                    {   // drainpipes (ends + every ~12.8 m, clear of the entrances), yellow gas pipe above the canopies
                        int np = Mathf.Max(2, Mathf.RoundToInt(L / 12.8f) + 1);
                        for (int j = 0; j < np; j++)
                        {
                            float s = Mathf.Lerp(.3f, L - .3f, j / (float)(np - 1));
                            foreach (int k in entBays) if (Mathf.Abs(s - bw * (k + .5f)) < 1.6f) s = bw * (k + .5f) + 1.7f * Mathf.Sign(s - bw * (k + .5f) + .01f);
                            if (cuts.Any(ct => Mathf.Abs(ct.s - s) < ct.w * .5f + .2f)) continue;
                            for (int fl = 0; fl < floors; fl++) RPiece("FK_R_Drainpipe_2m8", details, w.P(s, .3f + fl * fh, 0), w.Out);
                        }
                        if (L > 3f)
                        {
                            Color gas = RX("C4A23E");
                            RWallBox(det, "flat", w, .8f, L - .8f, 4.04f, 4.11f, .14f, gas);
                            RWallBox(det, "flat", w, .8f, .87f, .6f, 4.11f, .14f, gas);
                            RWallBox(det, "flat", w, L - .87f, L - .8f, .6f, 4.11f, .14f, gas);
                        }
                    }
                }
                // parapet along every edge on the bay grid (pieces stretched to the grid)
                int np2 = Mathf.Max(1, Mathf.RoundToInt(L / 3.2f)); float st = L / np2;
                for (int k = 0; k < np2; k++)
                {
                    var pp = RPiece("FK_R_Parapet_3m2", details, w.P(st * (k + .5f), tl, 0), w.Out);
                    if (pp) pp.transform.localScale = new Vector3(st / 3.2f, 1f, 1f);
                }
            }
            // arch passages: inner side walls + ceiling (concrete), the plinth stops at them
            foreach (var ar in archX)
                RBox(body, "concrete", f, new Vector3(ar.x, (yb + ar.h) / 2, 0), new Vector3(ar.w, ar.h - yb, 2 * hz + .02f), RS["concrete"].Own * .85f, RXP | RXN | RYP, true);
            float px0 = -hx - .04f;
            foreach (var ar in archX.OrderBy(a => a.x).Append((x: hx + 2.04f, w: 4f, h: 0f)))
            {
                float px1 = Mathf.Min(hx + .04f, ar.x - ar.w * .5f);
                if (px1 > px0 + .05f) RBox(body, "concrete", f, new Vector3((px0 + px1) / 2, (yb + .55f) / 2, 0), new Vector3(px1 - px0, .55f - yb, 2 * hz + .08f), RX("77756F"), RALL5);
                px0 = Mathf.Max(px0, ar.x + ar.w * .5f);
            }
            RPlane(body, "roof_flat", f, -hx, -hz, hx, hz, tl, RS["roof_flat"].Own);
            int nv = Mathf.Max(1, Mathf.RoundToInt(2 * hx / 12.8f));
            for (int j = 0; j < nv; j++) RPiece("FK_R_Roof_Vent", details, f.P(-hx + 2 * hx * (j + .5f) / nv, tl, 1.5f), f.F);
            if (doors.Count > 0 && front0 == 0) RolloutIssue($"{id}: entrances not on a long side");
            var bodyT = new GameObject("body").transform; bodyT.SetParent(go, false);
            RFlush(body, bodyT, "B_" + id + "_R2c");
            RFlush(det, details, "B_" + id + "_R2c_det");
            // collider arch tops at the visual ones (the arch height is measured from floor0, the collider base from baseY)
            Colliders(go, id, fp, baseY, top, "flat", roof, archs.Select(a => new Arch { P = a.P, Axis = a.Axis, W = a.W, H = a.H + floor0 - baseY }).ToList());
            Built.Add(new BInfo { Go = go.gameObject, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = "flat", Roof = roof });
            RolloutLod(go.gameObject, details);
            return true;
        }

        // ================================================================== Downtown D4 (any rect footprint; faces classified by the plan)
        static readonly string[] DtPlaster = { "C6BBA3", "A8AA9A", "B6A58F", "5F6C75", "7D8766", "B39562", "9C8F7A", "8E9A93", "C2A88A", "7A6F64", "A39A8C", "6E7B73" };
        static readonly string[] DtBrick = { "8A4E3F", "7A4437", "6A4034", "5E3B33", "94604A" };
        static readonly string[] DtGroundBrick = { "5E3B33", "7A4437", "6A4034", "6E4A3C" };
        static readonly string[] DtStone = { "BDB5A5", "CEC4B1", "CFC7B4", "D1C8B6" };            // existing TT_FK_Stone accents
        static readonly string[] DtSign = { "2F3A36", "4E3431", "34404F", "3F4F46", "5A3A36" };

        static Color RNearest(string[] pal, Color c)
        {
            Color best = RX(pal[0]); float bd = float.MaxValue;
            foreach (string h in pal) { Color p = RX(h); float d = (p.r - c.r) * (p.r - c.r) * .3f + (p.g - c.g) * (p.g - c.g) * .59f + (p.b - c.b) * (p.b - c.b) * .11f; if (d < bd) { bd = d; best = p; } }
            return best;
        }

        static Vector2 RNearestOn(Vector2[] pl, Vector2 p, out float dist)
        {
            Vector2 best = pl[0]; dist = float.MaxValue;
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                Vector2 a = pl[i], d = pl[i + 1] - a; float t = Mathf.Clamp01(Vector2.Dot(p - a, d) / Mathf.Max(1e-6f, d.sqrMagnitude));
                Vector2 q = a + d * t; float dd = (p - q).magnitude;
                if (dd < dist) { dist = dd; best = q; }
            }
            return best;
        }

        // faces of a rect footprint: 1 street (plan street in front, or a street door on it), 2 party wall (a neighbour against it),
        // 0 yard / alley; floor0 = sidewalk top in front of the street faces (else the ground at the centre)
        static int[] D4Faces(List<Vector2> fp, string id, List<Dictionary<string, object>> ents, out float floor0)
        {
            var kinds = new int[4]; floor0 = float.MinValue;
            for (int i = 0; i < 4; i++)
            {
                Vector2 p0 = fp[i], p1 = fp[(i + 1) % 4], d = (p1 - p0).normalized, n = new(d.y, -d.x);
                float L = (p1 - p0).magnitude;
                int party = 0;
                foreach (float t in new[] { .25f, .5f, .75f })
                {
                    Vector2 probe = Vector2.Lerp(p0, p1, t) + n * .8f;
                    if (DistrictFps.Any(o => o.id != id && W76Atmosphere.Inside(o.fp, probe))) party++;
                }
                bool streetDoor = ents.Any(e => S(Get(e, "street")) != null && Mathf.Abs(Cross(p0, p1, V2(Get(e, "pos")))) / Mathf.Max(.1f, L) < .8f);
                Vector2 mid = (p0 + p1) / 2; float sy = float.MinValue;
                bool street = streetDoor;
                foreach (var (line, half) in DistrictStreets)
                    foreach (float dd in new[] { 6f, 9f, 12f })
                    {
                        RNearestOn(line, mid + n * dd, out float dist);
                        if (dist < half + .5f) { street = true; break; }
                    }
                if (street)
                    foreach (var (line, half) in DistrictStreets)
                    {
                        Vector2 q = RNearestOn(line, mid + n * 8f, out float dist);
                        if (dist < half + 6f) sy = Mathf.Max(sy, Height(q.x, q.y) + .21f);   // sidewalk top (Streets: centreline + 0.06 + kerb 0.15)
                    }
                kinds[i] = party >= 2 && !streetDoor ? 2 : street ? 1 : 0;
                if (kinds[i] == 1) floor0 = Mathf.Max(floor0, sy > float.MinValue ? sy : Height(mid.x + n.x * 2f, mid.y + n.y * 2f) + .15f);
            }
            if (floor0 == float.MinValue) { Vector2 cc = fp.Aggregate(Vector2.zero, (s, q) => s + q) / 4; floor0 = Height(cc.x, cc.y) + .05f; }
            return kinds;
        }

        static bool RolloutD4(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string district)
        {
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object> { ["type"] = "flat" };
            int floors = Mathf.Max(1, (int)F(Get(b, "floors"), 5f));
            float Fh = F(Get(b, "floor_h_m"), 3.4f);
            var gfo = Obj(Get(b, "ground_floor"));
            float Gf = F(Get(gfo, "h_m"), 4.4f);
            float H = floors == 1 ? Mathf.Max(Gf, F(Get(b, "height_m"), Gf)) : Gf + (floors - 1) * Fh;
            string gk = (S(Get(gfo, "kind"), "") ?? "").ToLowerInvariant();
            var sk = Obj(Get(b, "sockets")) ?? new Dictionary<string, object>();
            bool shops = gk.Contains("store") || gk.Contains("shop") || gk.Contains("roll") || gk.Contains("cafe") || gk.Contains("bar") || gk.Contains("diner")
                         || (gk == "" && Get(sk, "storefront") is bool st && st);
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null && Get(e, "pos") != null).ToList();
            var kinds = D4Faces(fp, id, ents, out float floor0);
            // W86 separation (s04_downtown v37): window rhythm, ends, cornice, plinth, setback; none = the approved D4 face
            var sp = SepOf(Obj(Get(b, "separation")));
            if (S(Get(b, "kind")) == "house") ApplyDs(sp, id, floors);                    // W86 integration: Fedya's DS1 80 % / DS2 + DS3 20 %
            var acc = AccentOf(b);                                                     // W86 integration: T1 accent kinds (police, taxi, ...)
            AccentSep(acc, sp);
            var fpData = fp;
            if (sp.Setback > .01f) fp = SetbackFp(fp, kinds, sp.Setback);
            Vector2 cc = fp.Aggregate(Vector2.zero, (s, q) => s + q) / 4;
            float baseY = Mathf.Min(fp.Min(q => Height(q.x, q.y)) - .25f, floor0 - .4f);
            float top = floor0 + H, yb = baseY - floor0, tl = H;
            // palette (D4: a broader but restrained range; the plan colour picks the nearest approved hue)
            string slot = S(Get(b, "material_slot"), "") ?? "";
            bool brickUp = slot.Contains("brick") || (S(Get(b, "walls"), "") ?? "").Contains("brick");
            Color dataTint = RX(S(Get(b, "tint")) ?? "A8A090");
            string upKey = RolloutWallSurf(slot, id, brickUp ? "brick_paint" : "acg_plaster");
            Color up = brickUp ? RNearest(DtBrick, dataTint) : RNearest(DtPlaster, dataTint);
            string grKey; Color gr;
            if (shops && RHash(id, 41) < .7f) { grKey = "brick_paint"; gr = RX(RPick(DtGroundBrick, id, 42)); }
            else { grKey = upKey; gr = new Color(up.r * .9f, up.g * .9f, up.b * .9f, 1f); }
            if (sp.Rustic) { grKey = T7("ashlar"); gr = RX(sp.StringCol ?? "D9D0BD"); }
            if (acc != null) AccentColours(acc, id, ref upKey, ref up, ref grKey, ref gr, ref shops);
            bool lightFrame = RHash(id, 43) < .6f;
            Color frame = RX(lightFrame ? RPick(new[] { "E4DFD3", "E2DDD1" }, id, 44) : RPick(new[] { "2F3437", "33463D", "3B4144" }, id, 44));
            if (sp.FrameCol != null) { frame = RX(sp.FrameCol); lightFrame = sp.FrameCol.StartsWith("E"); }
            bool white = lightFrame && RHash(id, 45) < .55f;
            string stoneHex = RPick(DtStone, id, 46); Color stone = RX(stoneHex); var stoneM = RAcc("FK_Stone", stoneHex);
            Color sign = RX(RPick(DtSign, id, 47));
            Color plinth = sp.PlinthMat == "dark_paint" ? RX("3D3E3B") : stone;
            string fabric = Get(sk, "awning") is Dictionary<string, object> && RHash(id, 48) < .35f ? RPick(new[] { "green", "blue", "red" }, id, 49) : null;
            bool pil = !sp.On && grKey == "brick_paint" && RHash(id, 50) < .25f;
            var fe = Arr(Get(sk, "fire_escape")).Select(Obj).Where(o => o != null && Get(o, "from") != null).ToList();
            var details = new GameObject("details").transform; details.SetParent(go, false);
            var kit = new GameObject("kit").transform; kit.SetParent(go, false);
            var body = new RBatch(); var det = new RBatch();
            var f = RFr.Yaw(new Vector3(0, floor0, 0), 0);
            for (int i = 0; i < 4; i++)
            {
                Vector2 p0 = fp[i], p1 = fp[(i + 1) % 4];
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                bool partyStart = kinds[(i + 3) % 4] == 2, partyEnd = kinds[(i + 1) % 4] == 2;
                var pieceSwaps = new[] { ("FK_Stone", stoneM), ("FK_Brick", brickUp ? null : stoneM) };
                int np2 = Mathf.Max(1, Mathf.RoundToInt(L / 2f)); float pst = L / np2;
                void Parapets() { for (int k = 0; k < np2; k++) { var pp = RPiece("FK_D_Parapet_2m", details, w.P(pst * (k + .5f), tl, 0), w.Out, pieceSwaps); if (pp) pp.transform.localScale = new Vector3(pst / 2f, 1f, 1f); } }
                if (kinds[i] == 2 || L < 2.6f) { RWall(body, upKey, w, 0, L, yb, tl, up); Parapets(); continue; }
                bool street = kinds[i] == 1;
                if (street && sp.Setback > .01f)
                {   // the strip between the plan facade line and the set-back facade is paved like the sidewalk, flush with it
                    Vector2 q0 = fpData[i], q1 = fpData[(i + 1) % 4]; float tu = RS["sidewalk"].TU;
                    body["sidewalk"].Quad(f.P(p0.x, .005f, p0.y), f.P(q0.x, .005f, q0.y), f.P(q1.x, .005f, q1.y), f.P(p1.x, .005f, p1.y),
                        p0 / tu, q0 / tu, q1 / tu, p1 / tu, Color.white);
                }
                float e0 = SepEndClear(sp, partyStart), e1 = SepEndClear(sp, partyEnd);
                int bays = Mathf.Max(1, Mathf.RoundToInt(L / sp.Bay)); float bw = L / bays;
                float Bay(int k) => bw * (k + .5f);
                float hw = Mathf.Min(sp.Hw, bw / 2 - .45f);
                var upper = new List<Rect>();
                if (hw > .3f)
                    for (int fl = 1; fl < floors; fl++)
                    {
                        float yf = Gf + (fl - 1) * Fh, y0w = yf + sp.Sill, y1w = yf + Mathf.Min(sp.Head, Fh - .5f);
                        for (int k = 0; k < bays; k++)
                        {
                            if (!(street || k % 2 == 0)) continue;
                            float c = Bay(k), lim = Mathf.Min(c - e0, L - e1 - c);          // windows keep clear of the end pilasters / joints
                            if (sp.Paired && bw > 2.8f)
                            {
                                float pw = Mathf.Min(.42f, bw / 4 - .2f), off = pw + .12f;
                                if (lim < off + pw) continue;
                                upper.Add(Rect.MinMaxRect(c - off - pw, y0w, c - off + pw, y1w)); upper.Add(Rect.MinMaxRect(c + off - pw, y0w, c + off + pw, y1w));
                            }
                            else
                            {
                                float h2 = Mathf.Min(hw, lim);
                                if (h2 > .3f) upper.Add(Rect.MinMaxRect(c - h2, y0w, c + h2, y1w));
                            }
                        }
                    }
                ROpenings(body, upKey, w, L, Gf, tl, up, upper, .22f);
                foreach (var o in upper)
                {
                    RWindowUnit(body, det, w, o, .22f, white, frame, stone, brickUp || sp.Lintel);
                    if (sp.Hood) { RWallBox(det, "flat", w, o.xMin - .22f, o.xMax + .22f, o.yMax + .22f, o.yMax + .36f, .16f, stone); RWallBox(det, "flat", w, o.center.x - .35f, o.center.x + .35f, o.yMax + .36f, o.yMax + .5f, .1f, stone); }
                }
                // ground floor
                var edgeEnts = ents.Where(e => { var p = V2(Get(e, "pos")); float s = Vector2.Dot(p - p0, (p1 - p0) / L); return s > -.2f && s < L + .2f && Mathf.Abs(Cross(p0, p1, p)) / L < .8f + sp.Setback; })
                                   .Select(e => (s: Mathf.Clamp(Vector2.Dot(V2(Get(e, "pos")) - p0, (p1 - p0) / L), .9f + e0, Mathf.Max(.9f + e0, L - .9f - e1)), street: S(Get(e, "street")) != null)).ToList();
                var ground = new List<Rect>(); var gkind = new List<int>();                 // 0 shop, 1 shop door, 2 glazed door, 3 plain door, 4 window
                if (street && shops)
                {
                    var doorBays = new HashSet<int>(edgeEnts.Select(e => Mathf.Clamp(Mathf.FloorToInt(e.s / bw), 0, bays - 1)));
                    if (doorBays.Count == 0) doorBays.Add(bays - 1);
                    float hs = Mathf.Min(1.35f, bw / 2 - .3f);
                    for (int k = 0; k < bays; k++)
                    {
                        float h2 = Mathf.Min(hs, Mathf.Min(Bay(k) - e0, L - e1 - Bay(k)));
                        if (h2 < .5f) continue;
                        ground.Add(Rect.MinMaxRect(Bay(k) - h2, .5f, Bay(k) + h2, 3.0f)); gkind.Add(doorBays.Contains(k) ? 1 : 0);
                    }
                }
                else if (street)
                {
                    float sd = edgeEnts.Count > 0 ? edgeEnts[0].s : L / 2;
                    ground.Add(Rect.MinMaxRect(sd - .75f, 0f, sd + .75f, 2.7f)); gkind.Add(2);
                    foreach (float x in new[] { 1.5f + e0, L - 1.5f - e1 }) if (Mathf.Abs(x - sd) > 2.2f && L > 5f) { ground.Add(Rect.MinMaxRect(x - .65f, .9f, x + .65f, 2.6f)); gkind.Add(4); }
                }
                else
                {
                    foreach (var e in edgeEnts) { ground.Add(Rect.MinMaxRect(e.s - .6f, 0f, e.s + .6f, 2.2f)); gkind.Add(3); }
                    for (int k = 0; k < bays; k += 2)
                    {
                        float x = Bay(k);
                        if (hw > .3f && x - .6f > e0 && x + .6f < L - e1 && edgeEnts.All(e => Mathf.Abs(e.s - x) > 1.6f)) { ground.Add(Rect.MinMaxRect(x - .6f, 1.0f, x + .6f, 2.4f)); gkind.Add(4); }
                    }
                }
                ROpenings(body, grKey, w, L, yb, Gf, gr, ground, .25f);
                for (int j = 0; j < ground.Count; j++)
                {
                    var o = ground[j];
                    if (gkind[j] <= 1) RShopUnit(body, det, w, o, .25f, gkind[j] == 1);
                    else if (gkind[j] <= 3) RDoorUnit(body, det, w, o, .25f, gkind[j] == 2, frame, stone);
                    else RWindowUnit(body, det, w, o, .25f, white, frame, stone, false);
                }
                float br0 = sp.On && sp.Break && partyStart ? .25f : -.1f, br1 = sp.On && sp.Break && partyEnd ? .25f : -.1f;     // cornice / belt break at the party walls
                if (street)
                {   // plinth (split at doors), painted sign band, trim belt, pilasters, rare awnings, cornice
                    float ph = sp.On ? Mathf.Min(sp.PlinthH, shops ? .5f : .85f) : .5f;
                    float cur = 0f;
                    foreach (var o in ground.Where(o => o.yMin < ph - .05f).OrderBy(o => o.xMin))
                    {
                        if (o.xMin > cur + .05f) RWallBox(det, "flat", w, cur, o.xMin, yb, ph, .07f, plinth);
                        cur = Mathf.Max(cur, o.xMax);
                    }
                    if (cur < L - .05f) RWallBox(det, "flat", w, cur, L, yb, ph, .07f, plinth);
                    if (shops) RWallBox(det, "flat", w, .3f + e0, L - .3f - e1, 3.25f, Mathf.Min(3.95f, Gf - .5f), .07f, sign);
                    RBox(det, "trim", w, new Vector3((br0 + L - br1) / 2, Gf + .225f, -.05f), new Vector3(L - br0 - br1, .45f, .12f), RS["trim"].Own, ROUT);
                    if (sp.Belts) for (int fl = 2; fl < floors; fl++) RBox(det, "trim", w, new Vector3((br0 + L - br1) / 2, Gf + (fl - 1) * Fh - .08f, -.03f), new Vector3(L - br0 - br1, .16f, .07f), RS["trim"].Own, ROUT);
                    if (sp.StringFl > 0 && floors > sp.StringFl + 1) RWallBox(det, "flat", w, br0, L - br1, Gf + sp.StringFl * Fh - .1f, Gf + sp.StringFl * Fh + .1f, .08f, RX(sp.StringCol ?? "D9D0BD"));
                    if (acc != null && i == AccentFace(kinds)) AccentStreet(acc, det, kit, body, w, L, Gf, ground, gkind, id);
                    if (pil) { RWallBox(body, "brick_paint", w, 0, .6f, Gf + .45f, tl, .1f, gr); RWallBox(body, "brick_paint", w, L - .6f, L, Gf + .45f, tl, .1f, gr); }
                    if (fabric != null && shops)
                    {
                        RKitM.TryGetValue(fabric == "red" ? "FK_Fabric" : "FK_Fabric_" + fabric, out var fm);
                        for (int j = 0; j < ground.Count; j++) if (gkind[j] <= 1) RPiece("FK_D_Storefront_Awning", kit, w.P(ground[j].center.x, 3.02f, 0), w.Out, ("FK_Fabric", fm));
                    }
                    if (sp.On && sp.Cornice != null) SepCornice(det, w, L, tl, sp, Mathf.Max(0f, br0), Mathf.Max(0f, br1), up, stone);
                    else
                    {
                        int nc = Mathf.Max(1, Mathf.RoundToInt(L / 2f)); float cst = L / nc;
                        for (int k = 0; k < nc; k++) { var cp = RPiece("FK_D_Cornice_2m", details, w.P(cst * (k + .5f), tl, 0), w.Out, ("FK_Stone", stoneM)); if (cp) cp.transform.localScale = new Vector3(cst / 2f, 1f, 1f); }
                    }
                }
                else
                    for (int k = 0; k < bays; k += 2) if (floors > 1 && RHash(id + i + k, 13) > .55f) RPiece("FK_D_AC_Unit", details, w.P(Mathf.Min(Bay(k) + Mathf.Min(1.3f, bw * .45f), L - e1 - .5f), Gf + Fh * 1.2f, 0), w.Out);
                SepEnds(det, details, w, L, yb, tl, sp, partyStart, partyEnd, up, stone);
                // fire escapes (D4: on the alley / yard sides only): a plan fire escape on a street or party face moves to the
                // middle of the building's alley / yard face (the one nearest to it); none if the building has no such face
                foreach (var e in fe)
                {
                    Vector2 m = (V2(Get(e, "from")) + V2(Get(e, "to") ?? Get(e, "from"))) / 2;
                    int own = Enumerable.Range(0, 4).OrderBy(j => Mathf.Abs(Cross(fp[j], fp[(j + 1) % 4], m)) / Mathf.Max(.1f, (fp[(j + 1) % 4] - fp[j]).magnitude)).First();
                    int target = kinds[own] == 0 ? own : Enumerable.Range(0, 4).Where(j => kinds[j] == 0 && (fp[(j + 1) % 4] - fp[j]).magnitude > 5f)
                        .OrderBy(j => ((fp[j] + fp[(j + 1) % 4]) / 2 - m).magnitude).DefaultIfEmpty(-1).First();
                    if (target != i || floors < 2) continue;
                    if (L < 5f + e0 + e1) continue;
                    float s = target == own ? Vector2.Dot(m - p0, (p1 - p0) / L) : L / 2;
                    s = Mathf.Clamp(s, 2.3f + e0, L - 2.3f - e1);
                    for (int fl = 1; fl < floors; fl++)
                    {
                        float yy = Gf + (fl - 1) * Fh;
                        RPiece("FK_D_FireEscape_Landing", kit, w.P(s, yy, 0), w.Out);
                        if (fl < floors - 1) RPiece("FK_D_FireEscape_Stair", kit, w.P(s, yy, 0), w.Out);
                    }
                    RPiece("FK_D_FireEscape_Ladder", details, w.P(s + 1f, Gf - 3f, 0), w.Out);
                }
                Parapets();
            }
            Frame(fp, new Dictionary<string, object>(), out Vector2 rc, out Vector2 rax, out Vector2 ray, out float rhx, out float rhy);
            var rf = RFr.Yaw(new Vector3(rc.x, floor0, rc.y), Mathf.Atan2(ray.x, ray.y) * Mathf.Rad2Deg);
            RPlane(body, "roof_flat", rf, -rhx, -rhy, rhx, rhy, tl, RS["roof_flat"].Own);
            foreach (var t in Arr(Get(sk, "water_tank")).Select(V2).Where(v => v != Vector2.zero))
                RPiece("FK_D_RoofWaterTank", kit, new Vector3(t.x, top, t.y), Vector3.forward);
            if (Get(sk, "water_tank") is bool wt && wt) RPiece("FK_D_RoofWaterTank", kit, new Vector3(cc.x, top, cc.y), Vector3.forward);
            var bodyT = new GameObject("body").transform; bodyT.SetParent(go, false);
            RFlush(body, bodyT, "B_" + id + "_D4");
            RFlush(det, details, "B_" + id + "_D4_det");
            Colliders(go, id, fp, baseY, top, "flat", roof, new List<Arch>());
            Built.Add(new BInfo { Go = go.gameObject, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = "flat", Roof = roof });
            if (sp.On) sepVariants[sp.Variant] = sepVariants.TryGetValue(sp.Variant, out int nv) ? nv + 1 : 1;
            RolloutLod(go.gameObject, details);
            return true;
        }

        static readonly Dictionary<string, int> sepVariants = new();

        // wall s 0..L, y0..y1 with rectangular openings; reveals (recess metres deep) as single inward faces
        static void ROpenings(RBatch b, string key, RFr w, float L, float y0, float y1, Color col, List<Rect> holes, float recess)
        {
            var xs = new SortedSet<float> { 0, L }; var ys = new SortedSet<float> { y0, y1 };
            foreach (var h in holes) { xs.Add(Mathf.Clamp(h.xMin, 0, L)); xs.Add(Mathf.Clamp(h.xMax, 0, L)); ys.Add(Mathf.Clamp(h.yMin, y0, y1)); ys.Add(Mathf.Clamp(h.yMax, y0, y1)); }
            var xl = xs.ToList(); var yl = ys.ToList();
            for (int i = 0; i + 1 < xl.Count; i++)
                for (int j = 0; j + 1 < yl.Count; j++)
                {
                    var c = new Vector2((xl[i] + xl[i + 1]) / 2, (yl[j] + yl[j + 1]) / 2);
                    if (holes.Any(h => h.Contains(c))) continue;
                    RWall(b, key, w, xl[i], xl[i + 1], yl[j], yl[j + 1], col);
                }
            foreach (var h in holes)
            {
                RBox(b, key, w, new Vector3(h.xMin - .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col, RXP);
                RBox(b, key, w, new Vector3(h.xMax + .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col, RXN);
                RBox(b, key, w, new Vector3(h.center.x, h.yMax + .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col, RYN);
                if (h.yMin > y0 + .01f) RBox(b, key, w, new Vector3(h.center.x, h.yMin - .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col, RYP);
            }
        }

        const int RFM = RXP | RXN | RZN | RYP | RYN;                                   // frame members: no face against the glass

        static void RWindowUnit(RBatch body, RBatch det, RFr w, Rect o, float r, bool white, Color frame, Color stone, bool lintel)
        {
            RBox(body, "glass_dt", w, new Vector3(o.center.x, o.center.y, r + .005f), new Vector3(o.width, o.height, .01f), RX("3E4B55"), RZN);
            float t = .07f, zc = r - .03f;
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.center.x, o.center.y, zc), new Vector3(.05f, o.height, .05f), frame, RFM);
            if (white) RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + o.height * .64f, zc), new Vector3(o.width, .05f, .05f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMin - .04f, (r - .08f) / 2), new Vector3(o.width + .2f, .08f, r + .08f), stone, ROUT);   // sill
            if (lintel) RBox(det, "flat", w, new Vector3(o.center.x, o.yMax + .11f, -.015f), new Vector3(o.width + .24f, .22f, .05f), stone, ROUT);
            else
            {   // plaster: thin raised surround
                RBox(det, "flat", w, new Vector3(o.xMin - .06f, o.center.y + .06f, -.012f), new Vector3(.12f, o.height + .12f, .03f), stone, ROUT);
                RBox(det, "flat", w, new Vector3(o.xMax + .06f, o.center.y + .06f, -.012f), new Vector3(.12f, o.height + .12f, .03f), stone, ROUT);
                RBox(det, "flat", w, new Vector3(o.center.x, o.yMax + .06f, -.012f), new Vector3(o.width + .24f, .12f, .03f), stone, ROUT);
            }
        }

        static void RShopUnit(RBatch body, RBatch det, RFr w, Rect o, float r, bool door)
        {
            Color dark = RX("2F3538");
            RBox(body, "glass_dt", w, new Vector3(o.center.x, o.center.y, r + .005f), new Vector3(o.width, o.height, .01f), RX("3E4B55"), RZN);
            float zc = r - .04f;
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + .05f, zc), new Vector3(o.width, .1f, .08f), dark, RFM);
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMax - .05f, zc), new Vector3(o.width, .1f, .08f), dark, RFM);
            RBox(det, "flat", w, new Vector3(o.xMin + .05f, o.center.y, zc), new Vector3(.1f, o.height, .08f), dark, RFM);
            RBox(det, "flat", w, new Vector3(o.xMax - .05f, o.center.y, zc), new Vector3(.1f, o.height, .08f), dark, RFM);
            RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + 1.95f, zc), new Vector3(o.width, .06f, .06f), dark, RFM);
            if (door)
            {
                RBox(det, "flat", w, new Vector3(o.center.x + .2f, o.center.y - .2f, zc), new Vector3(.08f, o.height - .4f, .08f), dark, RFM);
                RBox(det, "flat", w, new Vector3(o.center.x + Mathf.Min(.75f, o.width / 2 - .2f), o.yMin + 1.05f, zc - .03f), new Vector3(.04f, .5f, .04f), RX("C9C2B0"), RFM);
            }
            else RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + .95f, zc), new Vector3(.05f, 1.9f, .05f), dark, RFM);
        }

        static void RDoorUnit(RBatch body, RBatch det, RFr w, Rect o, float r, bool glazed, Color frame, Color stone)
        {
            float ytop = o.yMax;
            RBox(body, glazed ? "glass_dt" : "flat", w, new Vector3(o.center.x, (o.yMin + ytop) / 2, r + .005f), new Vector3(o.width, ytop - o.yMin, .01f), glazed ? RX("3E4B55") : RX("4A4F50"), RZN);
            float zc = r - .03f;
            RBox(det, "flat", w, new Vector3(o.center.x, ytop - .05f, zc), new Vector3(o.width, .1f, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.xMin + .05f, o.center.y, zc), new Vector3(.1f, o.height, .06f), frame, RFM);
            RBox(det, "flat", w, new Vector3(o.xMax - .05f, o.center.y, zc), new Vector3(.1f, o.height, .06f), frame, RFM);
            if (glazed)
            {
                RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + 2.2f, zc), new Vector3(o.width, .07f, .06f), frame, RFM);
                RBox(det, "flat", w, new Vector3(o.center.x, o.center.y, zc), new Vector3(.06f, o.height, .06f), frame, RFM);
                RBox(det, "flat", w, new Vector3(o.center.x, ytop + .2f, -.02f), new Vector3(o.width + .6f, .3f, .06f), stone, ROUT);   // stone head
                RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + .08f, -.15f), new Vector3(o.width + .8f, .16f, .3f), stone, RALL6); // step
            }
        }

        // T09 a: base 2 through H5 - an invisible body box (the play scene finds the hut face by its box collider) + a roof-test entry
        static void HutBase2Extras(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string district)
        {
            Frame(fp, new Dictionary<string, object>(), out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            float baseY = fp.Min(q => Height(q.x, q.y)) - .25f, top = fp.Max(q => Height(q.x, q.y)) + Mathf.Max(2.4f, HHWalls.max.y - .4f);
            var cols = new GameObject("colliders").transform; cols.SetParent(go, false);
            AddBox(cols, c, baseY, top, 2 * hx - .1f, 2 * hy - .1f, -Mathf.Atan2(ax.y, ax.x) * Mathf.Rad2Deg);
            Built.Add(new BInfo { Go = go.gameObject, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = "none", Roof = new Dictionary<string, object>() });
            Done("T09 base-2 hut through H5");
        }

        // ================================================================== base 2: grandpa's yard (GRANDPA_YARD_v01 props)
        // As Fedya's i09 yard (handoff v10 §5.2 / 7.2): red rocking chair on the porch beside the door (away from the operating shed and
        // the paint table), the wooden barrel + paint cans / lid / brush by the wall at the far end of the door face, the blue rain drum
        // under a new downpipe at the hut corner on the next face; nothing on the van pad, the apron or the door steps.
        static void Base2Yard(Transform root)
        {
            if (!W85GrandpaYard.Prefab("GY_RockingChair_Red")) Note(W85GrandpaYard.Import().TrimEnd());
            var hut = Built.FirstOrDefault(x => x.Id.EndsWith("/02-A-BASE"));
            string file = Directory.GetFiles(Data + "/districts", "hamlet*_v85.json").FirstOrDefault();
            var dj = file != null ? Obj(Json.Parse(File.ReadAllText(file))) : null;
            var hb = Arr(Get(dj, "buildings")).Select(Obj).FirstOrDefault(o => o != null && S(Get(o, "kind")) == "hut_base2");
            var door = Arr(Get(hb, "entrances")).Select(Obj).FirstOrDefault(e => e != null);
            if (hut == null || door == null) { Note("base 2 yard: missing the hut 02-A-BASE or its door"); return; }
            Vector2 p = V2(Get(door, "pos")); float a = F(Get(door, "facing_deg")) * Mathf.Deg2Rad;
            Vector2 n = new(Mathf.Cos(a), Mathf.Sin(a)), tw = new(-n.y, n.x);
            float sMin = hut.Fp.Min(q => Vector2.Dot(q - p, tw)), sMax = hut.Fp.Max(q => Vector2.Dot(q - p, tw));
            var g = new GameObject("Base2_GrandpaYard").transform; g.SetParent(root, false);
            var log = new List<string>();
            void Put(string name, Vector2 at, Vector2 face, float lift = 0f)
            {
                var pf = W85GrandpaYard.Prefab(name);
                if (!pf) { log.Add("missing " + name); return; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, g);
                go.transform.SetPositionAndRotation(new Vector3(at.x, Height(at.x, at.y) + lift, at.y), Quaternion.Euler(0, Mathf.Atan2(face.x, face.y) * Mathf.Rad2Deg, 0));
                log.Add($"{name} ({at.x:0.0}, {at.y:0.0})");
            }
            Put("GY_RockingChair_Red", p + n * .62f + tw * 1.15f, (n - tw * .27f).normalized);                 // on the porch, beside the steps
            Put("GY_Barrel_Wood", p + n * .42f + tw * (sMax - .55f), n);                                      // by the wall, far end of the face
            Put("GY_PaintCan_Open_Green", p + n * 1.0f + tw * (sMax - .45f), n);
            Put("GY_PaintCan_Lid_Green", p + n * 1.28f + tw * (sMax - .78f), -n);
            Put("GY_PaintBrush_Green", p + n * .98f + tw * (sMax - 1.0f), (n + tw).normalized, .005f);
            Put("GY_PaintCan_Ochre", p + n * .62f + tw * (sMax - 1.1f), n);
            Put("GY_PaintCan_Small_Blue", p + n * 1.22f + tw * (sMax - 1.3f), -tw);
            // downpipe at the near corner of the next face (outward -tw) from the eave to the drum, drum under its outlet
            Vector2 c0 = p + tw * sMin, pipe = c0 - n * .35f;
            float ground = Height(pipe.x, pipe.y), eave = hut.Top - .45f, y0 = ground + .95f;
            var pc = Piece("FK_R_Drainpipe_2m8", g, new Vector3(pipe.x, y0, pipe.y), new Vector3(-tw.x, 0, -tw.y));
            if (pc && eave > y0 + .3f) pc.transform.localScale = new Vector3(1f, (eave - y0) / 2.8f, 1f);
            Put("GY_Drum_Rain", pipe - tw * .36f, -tw);
            foreach (Transform t in g.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            Note("base 2 yard (grandpa): " + string.Join(", ", log) + $"; downpipe {(pc ? "on" : "missing")} at ({pipe.x:0.0}, {pipe.y:0.0})");
        }

        // ================================================================== N-R3 night light on every urban street lamp
        // (Fedya 21.10: dimmer, shadowed, flickering; none in the Hamlet, which has no street lamps at all). Rural rects = W85Look rects.
        static bool RuralLamp(Vector2 p) =>
            (p.x > 185 && p.x < 470 && p.y > 365 && p.y < 625) || (p.x > 180 && p.x < 445 && p.y > 60 && p.y < 330) || (p.x > 520 && p.x < 665 && p.y > 60 && p.y < 300);
        static bool HamletLamp(Vector2 p) => p.x > 185 && p.x < 470 && p.y > 365 && p.y < 625;

        /// <summary>W86 (Fedya 25.10): the play scene built before "every lamp lights" gets the missing lamp lights (forest, valley,
        /// construction): the same flicker light + shadowed spot, added to the flicker list, the fog halos and the shadow budget.</summary>
        public static string LightAllLamps(UnityEngine.SceneManagement.Scene scene)
        {
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name.StartsWith("Map_W85_"));
            if (!root) return "lamps: no map root";
            var all = root.GetComponentsInChildren<Transform>(true).Where(x => (x.name.Contains("lamp") || x.name.Contains("Lamp")) && x.GetComponentInChildren<MeshRenderer>()).ToList();
            var set = new HashSet<Transform>(all);
            int added = 0, rebuilt = 0;
            foreach (var lamp in all)
            {
                bool nested = false;
                for (var p = lamp.parent; p != null; p = p.parent) if (set.Contains(p)) { nested = true; break; }
                if (nested || HamletLamp(new Vector2(lamp.position.x, lamp.position.z))) continue;
                var own = lamp.GetComponentsInChildren<Light>(true).Where(l => l.name == "Flicker").ToList();
                if (lamp.GetComponentInChildren<Light>(true) && own.Count == 0) continue; // a lamp with its own other light (not ours)
                // probe how many heads it has; a pole lit with fewer lights than heads (the old one-light-per-pole) is redone
                var probe = NightLamps(lamp.gameObject, false); int heads = probe.Count; foreach (var l in probe) Object.DestroyImmediate(l.gameObject);
                if (own.Count == heads && heads > 0) continue;
                foreach (var l in own) Object.DestroyImmediate(l.gameObject);
                NightLamps(lamp.gameObject, true);
                if (own.Count == 0) added++; else rebuilt++;
            }
            // every registration rebuilt from the lights that exist now: no destroyed entries, no duplicates
            var lights = root.GetComponentsInChildren<Light>(true).Where(l => l.name == "Flicker").ToList();
            var spots = lights.Select(l => l.GetComponentsInChildren<Light>(true).FirstOrDefault(x => x != l && x.name == "Flicker_Spot")).Where(x => x).ToList();
            var objs = scene.GetRootGameObjects();
            foreach (var life in objs.SelectMany(g => g.GetComponentsInChildren<OnlyVolunteers.Map.Look.V3.DistrictLife19V02>(true)))
                if (life.wornLamps != null && life.wornLamps.Length > 0) { life.wornLamps = lights.ToArray(); EditorUtility.SetDirty(life); }
            foreach (var fog in objs.SelectMany(g => g.GetComponentsInChildren<OnlyVolunteers.Map.Look.V3.DistrictFog19V05>(true)))
            {
                var keep = fog.halos.Where(h => h.light && h.light.name != "Flicker").ToList(); // van headlights etc.
                keep.AddRange(lights.Select(l => new OnlyVolunteers.Map.Look.V3.DistrictFog19V05.Halo { light = l, position = l.transform.position, size = 2.3f, colour = new Color(.78f, .86f, .91f, .36f) }));
                fog.halos = keep.ToArray(); EditorUtility.SetDirty(fog);
            }
            foreach (var mb in objs.SelectMany(g => g.GetComponentsInChildren<MonoBehaviour>(true)).Where(m => m && m.GetType().Name == "SkyMapNight22I03"))
            {
                var so = new SerializedObject(mb); var p = so.FindProperty("lamps"); if (p == null) continue;
                p.arraySize = lights.Count; for (int i = 0; i < lights.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = lights[i];
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            foreach (var budget in objs.SelectMany(g => g.GetComponentsInChildren<W85LampShadowBudget>(true)))
            { budget.Spots = spots.ToArray(); EditorUtility.SetDirty(budget); break; }
            return $"lamps: {added} newly lit, {rebuilt} multi-head lamps redone with one light per head; {lights.Count} head lights, {spots.Count} shadowed spots registered";
        }

        static void UrbanLamps(Transform root)
        {
            SampleLamps.Clear();
            var all = root.GetComponentsInChildren<Transform>(true).Where(x => (x.name.Contains("lamp") || x.name.Contains("Lamp")) && x.GetComponentInChildren<MeshRenderer>()).ToList();
            var set = new HashSet<Transform>(all);
            var spots = new List<Light>();
            int rural = 0;
            foreach (var lamp in all)
            {
                bool nested = false;
                for (var p = lamp.parent; p != null; p = p.parent) if (set.Contains(p)) { nested = true; break; }
                if (nested || lamp.GetComponentInChildren<Light>()) continue;
                Vector2 q = new(lamp.position.x, lamp.position.z);
                if (HamletLamp(q)) { rural++; continue; } // W86 (Fedya 25.10): every lamp on the map lights up; the Hamlet has none by design
                foreach (var l in NightLamps(lamp.gameObject, true)) // one light per head (double lanterns: two)
                {
                    SampleLamps.Add(l);
                    var sp = l.GetComponentsInChildren<Light>(true).FirstOrDefault(x => x != l);
                    if (sp) spots.Add(sp);
                }
            }
            if (spots.Count > 0)
            {
                var g = new GameObject("NightLamps_N-R3"); g.transform.SetParent(root, false);
                var budget = g.AddComponent<W85LampShadowBudget>();
                budget.Spots = spots.ToArray();
            }
            Note($"N-R3 night light: {SampleLamps.Count} urban street lamps (flicker point light in the head + shadowed spot; nearest {8} spots cast shadows), {rural} rural lamps unlit");
        }
    }
}
