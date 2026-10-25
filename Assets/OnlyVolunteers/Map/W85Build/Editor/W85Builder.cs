using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // Map v85 one-click builder (lead brief "Map W85 build", 2026-10-21; forked from W76Builder, which stays untouched).
    // Everything comes from Data/v01 (Tools/MapV85/*.py: Vadim's 2D map v85, district plans v31/v52/v07/v11/v12/v06/v03, handoff v10):
    // terrain heightmap + holes + splat, world roads (own heights, bridges, tunnel), water (River/Lake/Pond/Bog for corpse disposal),
    // northern border, districts (buildings with material slots, zones, fences, props), vegetation by logic, small details by rules.
    // Output: Generated/v01 (own folder, rebuilt on every click) and scene Scenes/Map/Map_W85_Build_v01.unity.
    // Nothing approved is modified: reused materials / layers / prefabs are only referenced (V19 palette-field materials -> W85 copy, field off).
    public static partial class W85Builder
    {
        const string Root = "Assets/OnlyVolunteers/Map/W85Build";
        // Data version (W86, 22.10): v01 = the W85 build as playtested; v02 = Tools/MapV85 re-run of the W86 pass (relief, waterfalls,
        // steppe backdrop, Rough replanning, Downtown v37, fuel station ...). Set by the menu entry; every output is per version.
        static string Ver = "v01";
        static string Data = Root + "/Data/v01";            // Tools/MapV85 (2D map v85 + handoff v10)
        static string Gen = Root + "/Generated/v01";
        static string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Build_v01.unity";
        static bool IsV2 => Ver != "v01";
        public static string ScenePathOf(string ver) => $"Assets/OnlyVolunteers/Scenes/Map/Map_W85_Build_{ver}.unity";
        static void SetVersion(string ver)
        {
            Ver = ver; Data = Root + "/Data/" + ver; Gen = Root + "/Generated/" + ver; ScenePath = ScenePathOf(ver);
        }
        const string SceneI10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string KitSrc = "ArtSource/Props/FACADE_KIT_v01/FBX";
        const string TerrainMaterial = "Assets/OnlyVolunteers/Map/LookV3/Materials/V3_Terrain.mat";
        // ---- decisions (Fedya 18.10 + handoff v10 §12); change here and rebuild
        const float DowntownCarriageway = 12f;           // v10 §6: 12 m carriageway (replaces Q1 8.5 m)
        const float DowntownSidewalk = 5f;               // v10 §6: 5 m sidewalks (replaces Q1 4.5 m)
        const string SeaMaterialKey = "water_sea";       // Q2: "water_sea" = Sea_trial_calm_v09 (variant 1), "water_sea_alt_v10" = v10
        const float EliteGateSeconds = 4f;               // Q3: gate open after the van passes, s
        const float EliteGuardSeconds = 2f;              // Q3: + guards come out, s
        const int LifeguardTowers = 2;                   // Q4 answered (Fedya 18.10): 2 of the 6 on the map, one per van entry (x 895, x 1142)
        // Q5 answered: port as on the approved v76 picture (latest shift; data as is, checked by overlay).
        // Q6 answered: no fuel station for now: canopy + kiosk carry "disabled": true in the data and are skipped (set false to restore).
        // Q7 answered: VIEW B serpentine 12 %; v10: low 1-1.5 m berm and an open view (terrain makes a pass, Tools/MapV85/s03_terrain.py).
        const string PrefabLib = "Assets/OnlyVolunteers/Art/Map/Prefabs/";
        const string PK1Door = "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/DOOR_FRAME_RURAL_v01.prefab";
        static readonly StringBuilder Log = new();
        static Dictionary<string, object> MatMap;
        static readonly Dictionary<string, Material> Mats = new();
        static readonly Dictionary<string, float> MatTile = new();
        static Terrain Ter;
        static float W = 1744f, Hh = 950f;
        static int created, reused;

        [MenuItem("OnlyVolunteers/Map/W85 Build/Build Map_W85_Build_v01 (2D map v85)")]
        public static void Build() => Build("v01", true);

        // Same build without dialogs (automation: agents / batch mode). The output is only our own Generated/v01 + scene.
        public static void BuildSilent() => Build("v01", false);

        // W86 pass (lead brief 22.10): the same builder on Data/v02 -> Generated/v02 + Scenes/Map/Map_W85_Build_v02.unity (v01 untouched).
        [MenuItem("OnlyVolunteers/Map/W86 Build (data v02)")]
        public static void BuildV02() => Build("v02", false); // no confirm dialog (Fedya 25.10: never ask to click Rebuild)
        public static void BuildV02Silent() => Build("v02", false);

        static void Build(string ver, bool interactive)
        {
            SetVersion(ver);
            if (!File.Exists(Data + "/terrain_v85.json"))
            {
                if (interactive) EditorUtility.DisplayDialog("W85", "No data in " + Data + ". Run Tools/MapV85 (s01 ... s07).", "OK");
                else Debug.LogError("[W85] no data in " + Data);
                return;
            }
            if (interactive && File.Exists(ScenePath) && !EditorUtility.DisplayDialog("W85", "Rebuild " + ScenePath + " and " + Gen + " (own generated output, nothing approved is touched)?", "Rebuild", "Cancel"))
                return;
            if (interactive && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var t0 = DateTime.Now;
            Log.Clear(); Mats.Clear(); MatTile.Clear(); Built.Clear(); SlotMats.Clear(); PrefabCache.Clear(); LayerCache.Clear(); created = reused = paletteFixed = 0; poolWater = null;
            // (not inside Start/StopAssetEditing: a delete + re-create of the same folder in one batch left no folder on a rebuild)
            if (AssetDatabase.IsValidFolder(Gen)) AssetDatabase.DeleteAsset(Gen);
            foreach (string f in new[] { "Meshes", "Materials", "Textures", "FacadeKit", "Terrain" }) Folder(Gen + "/" + f);
            ImportKit();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Map_W85_" + Ver).transform;
            Note($"[W85] data {Data} -> {Gen} + {ScenePath}");
            var mj = Obj(Json.Parse(File.ReadAllText(Data + "/materials_v85.json")));
            MatMap = mj["materials"] as Dictionary<string, object>;
            Slots = Obj(Get(mj, "slots")) ?? new Dictionary<string, object>();
            Sample = LoadSample();
            LoadSampleRules();
            RolloutInit();
            W86Init();
            W86RolloutInit();                                                     // W86 integration (v07 / T1 / T2 / M1 / M2)
            Step("terrain", () => BuildTerrain(root));
            Step("steppe backdrop", () => BuildBackdrop(root));
            Step("roads", () => BuildRoads(root));
            Step("tunnel", () => BuildTunnel(root));
            Step("water", () => BuildWater(root));
            Step("border", () => BuildBorder(root));
            foreach (string f in Directory.GetFiles(Data + "/districts", "*_v85.json").OrderBy(s => s))
                Step("district " + Path.GetFileNameWithoutExtension(f), () => BuildDistrict(root, f));
            Step("retaining walls", () => RetainingWalls(root));
            Step("view pocket", () => ViewPocket(root));
            Step("rock faces", () => RockFaces(root));
            Step("details", () => BuildDetails(root));
            Step("texture sample", () => BuildSample(root));
            Step("night lamps", () => UrbanLamps(root));
            Step("base 2 yard", () => Base2Yard(root));
            Step("light", () => BuildLight(root));
            Step("W86 rollout post pass", () => { W86PostPass(root); EliteRoadLamps(root); CutPoolHoles(); W86DecalHooks(root); });
            if (IsV2) Step("W86 decals", () => W86Decals(root));                 // W86 decals (B3): markings, wear, oil, foam into DecalHooks_W86
            if (IsV2) Step("G46 road surfaces", () => Note(W86RoadRepair.Meshes(root)));
            Step("validate", () => Validate(root));
            Note(RolloutSummary());
            Step("i10 look", () => Note(W85Look.Apply(root, Ter, Ver, LookRects())));
            Step("far view", () => FarView(root));
            Step("texture sample night", () => SampleNight(root));
            Note(W86Summary());
            Note(ModelSummary());
            Note(GreyBoxReport(root));
            Note($"materials: {reused} reused, {created} created, {paletteFixed} V19 palette-field copies (field off), {SlotMats.Count} slot materials");
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            ReapplyTerrain();
            ReapplyBackdrop();
            Note($"built in {(DateTime.Now - t0).TotalSeconds:0} s");
            File.WriteAllText(Gen + "/W85_build_log.txt", Log.ToString());
            AssetDatabase.ImportAsset(Gen + "/W85_build_log.txt");
            Debug.Log("[W85] done\n" + Log);
        }

        // Texture sample (T4 twin towers): the data file of the version, else the builder's own default (W86: Data/v02 has none; the
        // replaced tower / podium ids are found by kind near the sample, so a pipeline re-run that renames them does not break it).
        const string SampleDefault = Root + "/Editor/W86_texture_sample_default.json";
        static Dictionary<string, object> LoadSample()
        {
            string f = Data + "/texture_sample_v85.json";
            if (File.Exists(f)) return Obj(Json.Parse(File.ReadAllText(f)));
            if (IsV2 && File.Exists(SampleDefault)) { Note("texture sample: " + SampleDefault + " (no texture_sample_v85.json in " + Data + ")"); return Obj(Json.Parse(File.ReadAllText(SampleDefault))); }
            return new Dictionary<string, object>();
        }

        // ------------------------------------------------------------------ helpers
        static void Step(string name, Action a)
        {
            EditorUtility.DisplayProgressBar("W85 build", name, 0.5f);
            try { a(); Note("ok: " + name); }
            catch (Exception e) { Note("FAILED " + name + ": " + e); Debug.LogException(e); }
            finally { EditorUtility.ClearProgressBar(); }
        }

        static void Note(string s) => Log.AppendLine(s);

        static void Folder(string path)
        {
            string[] parts = path.Split('/');
            string cur = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = cur + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(cur, parts[i]);
                cur = next;
            }
        }

        static Dictionary<string, object> Obj(object o) => o as Dictionary<string, object>;
        static List<object> Arr(object o) => o as List<object> ?? new List<object>();
        static float F(object o, float d = 0f) => o is double v ? (float)v : o is long l ? l : d;
        static string S(object o, string d = null) => o as string ?? d;
        static object Get(Dictionary<string, object> d, string k) => d != null && d.TryGetValue(k, out object v) ? v : null;
        static Vector2 V2(object o) { var a = Arr(o); return a.Count >= 2 ? new Vector2(F(a[0]), F(a[1])) : Vector2.zero; }
        static Vector2[] V2s(object o) => Arr(o).Select(V2).ToArray();
        static float Height(float x, float z) => Ter ? Ter.SampleHeight(new Vector3(x, 0f, z)) + Ter.transform.position.y : 0f;
        static Vector3 P(Vector2 p, float dy = 0f) => new(p.x, Height(p.x, p.y) + dy, p.y);
        static float Hash(string s, int salt = 0) { unchecked { int h = 17 + salt; foreach (char c in s) h = h * 31 + c; return (h & 0x7fffffff) / (float)int.MaxValue; } }

        // ------------------------------------------------------------------ materials (addendum 01: reuse by texture GUID)
        static Material Mat(string key)
        {
            if (string.IsNullOrEmpty(key)) key = "concrete_SK3c";
            if (Mats.TryGetValue(key, out Material m)) return m;
            if (key == "lawn_hedge")
            {   // clipped hedge of the Elite plots (no hedge texture in the approved set yet): plain green URP Lit, one shared material
                var hm = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W85_hedge", enableInstancing = true };
                hm.SetColor("_BaseColor", new Color(.24f, .38f, .2f)); hm.SetFloat("_Smoothness", .05f);
                AssetDatabase.CreateAsset(hm, Gen + "/Materials/W85_hedge.mat"); created++;
                MatTile[key] = 2f;
                return Mats[key] = hm;
            }
            var rec = Obj(Get(MatMap, key));
            if (rec == null) { Note("unknown material key " + key + " -> concrete_SK3c"); return Mats[key] = Mat("concrete_SK3c"); }
            MatTile[key] = F(Get(rec, "tile_m"), 4f);
            string action = S(Get(rec, "action")), asset = S(Get(rec, "asset"));
            if (action == "reuse" && asset != null && asset.EndsWith(".mat"))
            {
                m = AssetDatabase.LoadAssetAtPath<Material>(asset);
                if (m && m.HasProperty("_DistrictMask") && m.GetTexture("_DistrictMask"))
                {   // V19 palette materials carry the i10-space palette field: on W85 it pulled house colours back to the legacy colour
                    // (texture test 21.10). W85 gets its own copy with the field off; the approved material is not touched.
                    var cp = new Material(m) { name = "W85_" + key + "_nofield", enableInstancing = true };
                    cp.SetTexture("_DistrictMask", null);
                    AssetDatabase.CreateAsset(cp, Gen + "/Materials/W85_" + key + "_nofield.mat");
                    created++; paletteFixed++;
                    return Mats[key] = cp;
                }
                if (m) { reused++; return Mats[key] = m; }
                Note("reuse target missing " + asset);
            }
            Texture2D tex = ImportTexture(S(Get(rec, "texture")));
            m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W85_" + key, enableInstancing = true };
            if (tex) m.SetTexture("_BaseMap", tex);
            m.SetFloat("_Smoothness", key.Contains("glass") ? .85f : .12f);
            if (key == "fence_net")
            {
                m.SetFloat("_AlphaClip", 1f); m.SetFloat("_Cutoff", .5f); m.EnableKeyword("_ALPHATEST_ON");
                m.SetFloat("_Cull", 0f);
            }
            if (key == "tower_glass") m.SetFloat("_Metallic", .35f);
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W85_" + key + ".mat");
            created++;
            return Mats[key] = m;
        }

        static float Tile(string key) { Mat(key); return MatTile.TryGetValue(key, out float t) && t > 0f ? t : 4f; }

        static int paletteFixed;
        static Dictionary<string, object> Slots;
        static readonly Dictionary<string, Material> SlotMats = new();

        // One material per building type ("slot", materials_v85.json "slots"): a copy of today's approved material for that type, so a
        // texture swap for e.g. all Downtown stucco houses is ONE change (the slot line in the data, or this one material). Texture sample:
        // a slot entry "texture_test": "<material asset path>" makes that slot use the test material instead.
        static Material SlotMat(string slot, string part, string fallbackKey)
        {
            if (string.IsNullOrEmpty(slot)) return Mat(fallbackKey);
            string id = slot + "_" + part;
            if (SlotMats.TryGetValue(id, out var sm) && sm) return sm;
            var rec = Obj(Get(Slots, slot));
            string key = S(Get(rec, part)) ?? fallbackKey;
            string test = S(Get(rec, part == "walls" ? "texture_test" : "texture_test_roof"));
            if (!string.IsNullOrEmpty(test) && AssetDatabase.LoadAssetAtPath<Material>(test) is Material tm) return SlotMats[id] = tm;
            var baseM = Mat(key);
            MatTile[id] = Tile(key);
            var m = new Material(baseM) { name = "W85_slot_" + id, enableInstancing = true };
            Folder(Gen + "/Materials/Slots");
            AssetDatabase.CreateAsset(m, Gen + "/Materials/Slots/W85_slot_" + id + ".mat");
            created++;
            return SlotMats[id] = m;
        }

        static Texture2D ImportTexture(string repoPath)
        {
            if (string.IsNullOrEmpty(repoPath)) return null;
            if (repoPath.StartsWith("Assets/")) return AssetDatabase.LoadAssetAtPath<Texture2D>(repoPath);
            string dst = Gen + "/Textures/" + Path.GetFileName(repoPath);
            if (!File.Exists(dst))
            {
                if (!File.Exists(repoPath)) { Note("texture missing " + repoPath); return null; }
                File.Copy(repoPath, dst);
                AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceSynchronousImport);
                var ti = AssetImporter.GetAtPath(dst) as TextureImporter;
                if (ti)
                {
                    ti.wrapMode = repoPath.Contains("Facade") || repoPath.Contains("atlas") ? TextureWrapMode.Repeat : TextureWrapMode.Repeat;
                    ti.alphaIsTransparency = repoPath.Contains("atlas") || repoPath.Contains("FenceNet") || repoPath.Contains("Marks") || repoPath.Contains("WaterFX");
                    ti.mipmapEnabled = true;
                    ti.SaveAndReimport();
                }
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
        }

        static readonly Dictionary<string, TerrainLayer> LayerCache = new();
        static TerrainLayer Layer(string key, Dictionary<string, TerrainLayer> fromI10)
        {
            if (LayerCache.TryGetValue(key, out var cached) && cached) return cached;        // W86: the steppe backdrop asks for the same layers
            var swapped = SwappedLayer(key);                                                  // W86 integration: T21 b field layers
            if (swapped) return LayerCache[key] = swapped;
            return LayerCache[key] = LayerNew(key, fromI10);
        }

        static TerrainLayer LayerNew(string key, Dictionary<string, TerrainLayer> fromI10)
        {
            var rec = Obj(Get(MatMap, key));
            string tex = S(Get(rec, "texture")), asset = S(Get(rec, "asset"));
            string guid = tex != null && tex.StartsWith("Assets/") ? AssetDatabase.AssetPathToGUID(tex) : null;
            if (guid != null && fromI10.TryGetValue(guid, out TerrainLayer li)) { reused++; return li; }        // the layer the i10 scene uses
            if (S(Get(rec, "action")) == "reuse" && asset != null && asset.EndsWith(".terrainlayer"))
            {
                var l = AssetDatabase.LoadAssetAtPath<TerrainLayer>(asset);
                if (l) { reused++; return l; }
            }
            var layer = new TerrainLayer { diffuseTexture = ImportTexture(tex), tileSize = Vector2.one * F(Get(rec, "tile_m"), 8f), smoothness = 0f, metallic = 0f };
            AssetDatabase.CreateAsset(layer, Gen + "/Terrain/W85_" + key + ".terrainlayer");
            created++;
            return layer;
        }

        static Dictionary<string, TerrainLayer> I10Layers()
        {
            var d = new Dictionary<string, TerrainLayer>();
            if (!File.Exists(SceneI10)) return d;
            foreach (string dep in AssetDatabase.GetDependencies(SceneI10, true))
            {
                if (!dep.EndsWith(".terrainlayer")) continue;
                var l = AssetDatabase.LoadAssetAtPath<TerrainLayer>(dep);
                if (l && l.diffuseTexture) d[AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(l.diffuseTexture))] = l;
            }
            return d;
        }

        // ------------------------------------------------------------------ terrain
        static void BuildTerrain(Transform root)
        {
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/terrain_v85.json")));
            var size = Arr(Get(tj, "size_m")); var pos = Arr(Get(tj, "position_m"));
            W = F(size[0]); Hh = F(size[2]);
            const int R = 2049, AR = 2048;
            byte[] raw = File.ReadAllBytes(Data + "/" + S(Get(tj, "heightmap")));
            var heights = new float[R, R];
            for (int j = 0; j < R; j++)
                for (int i = 0; i < R; i++)
                {
                    int k = (j * R + i) * 2;
                    heights[j, i] = (raw[k] | raw[k + 1] << 8) / 65535f;
                }
            if (IsV2) GradeFootprints(heights, R, F(size[1]), F(pos[1]));               // W86 ground fit: level the rare footprint > 1.5 m
            if (IsV2) W86RoadRepair.Grade(heights, F(size[1]), F(pos[1]));             // G46 shared road profiles, approach cuts, reviewed sea artifacts
            // layers first: they import textures, and an import during the build reverted the fresh TerrainData to its saved (flat) state
            var splat = Obj(Get(tj, "splat"));
            var keys = Arr(Get(splat, "layers")).Select(o => (string)o).ToList();
            var i10 = I10Layers();
            var layerArr = keys.Select(k => Layer(k, i10)).ToArray();
            var td = new TerrainData { heightmapResolution = R, alphamapResolution = AR };
            td.size = new Vector3(W, F(size[1]), Hh);
            AssetDatabase.CreateAsset(td, Gen + "/Terrain/TerrainData_W85_" + Ver + ".asset");
            td.SetHeights(0, 0, heights);
            byte[] bits = File.ReadAllBytes(Data + "/Holes_v85_2048_bits.bytes");
            var holes = new bool[R - 1, R - 1];
            for (int j = 0; j < R - 1; j++)
                for (int i = 0; i < R - 1; i++)
                {
                    int b = j * (R - 1) + i;
                    holes[j, i] = (bits[b >> 3] >> (7 - (b & 7)) & 1) == 1;           // 1 = solid
                }
            if (IsV2) W86RoadRepair.TunnelHoles(holes, heights, F(size[1]), F(pos[1]));
            td.SetHoles(0, 0, holes);
            td.terrainLayers = layerArr;
            var masks = Arr(Get(splat, "files")).Select(f => LoadPng(Data + "/" + (string)f)).ToArray();
            var px32 = masks.Select(m => m.GetPixels32()).ToArray();
            int mw = masks[0].width, mh = masks[0].height;
            var a = new float[AR, AR, keys.Count];
            for (int j = 0; j < AR; j++)
                for (int i = 0; i < AR; i++)
                {
                    int px = Mathf.Min(mw - 1, (int)((i + .5f) / AR * W)), py = Mathf.Min(mh - 1, (int)((j + .5f) / AR * Hh));
                    float sum = 0f;
                    for (int l = 0; l < keys.Count; l++)
                    {
                        Color32 c = px32[l / 4][py * mw + px];
                        float v = ((l % 4) switch { 0 => c.r, 1 => c.g, 2 => c.b, _ => c.a }) / 255f;
                        a[j, i, l] = v; sum += v;
                    }
                    if (sum <= 0f) a[j, i, 0] = 1f;
                    else for (int l = 0; l < keys.Count; l++) a[j, i, l] /= sum;
                }
            if (IsV2) { a = W86BankBands(a, keys, ref layerArr); td.terrainLayers = layerArr; }   // W86 integration: bank bands
            td.SetAlphamaps(0, 0, a);
            foreach (var m in masks) Object.DestroyImmediate(m);
            Trees(td);
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
            lastHeights = heights; lastHoles = holes; lastAlpha = a;
            var go = Terrain.CreateTerrainGameObject(td);
            go.name = "Terrain_W85_" + Ver;
            go.transform.SetParent(root, false);
            go.transform.position = new Vector3(F(pos[0]), F(pos[1]), F(pos[2]));
            Ter = go.GetComponent<Terrain>();
            var tm = AssetDatabase.LoadAssetAtPath<Material>(TerrainMaterial);
            if (tm) Ter.materialTemplate = tm;
            Ter.heightmapPixelError = 4f; Ter.basemapDistance = 900f; Ter.treeDistance = 650f; Ter.treeBillboardDistance = 220f;
            Ter.drawInstanced = true; Ter.shadowCastingMode = ShadowCastingMode.On;
            go.AddComponent<MapHeightSampler>().Terrain = Ter;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            Note($"terrain {W}x{F(size[1])}x{Hh} m, heightmap {R}, splat {AR} x {keys.Count} layers, {td.treeInstanceCount} trees, height probe {td.GetHeight(1024, 1024):0.00} m (expected {heights[1024, 1024] * td.size.y:0.00})");
        }

        // Local check: on a rebuild the TerrainData heights (and splat) came out blank after the later asset writes of the build
        // (same Unity quirk as V3Terrain.ReapplySplat / W19 "data set before this is lost"): write them again once all is saved.
        static float[,] lastHeights; static bool[,] lastHoles; static float[,,] lastAlpha;

        static void ReapplyTerrain()
        {
            if (!Ter || lastHeights == null) return;
            var td = Ter.terrainData;
            td.SetHeights(0, 0, lastHeights);
            td.SetHoles(0, 0, lastHoles);
            td.SetAlphamaps(0, 0, lastAlpha);
            if (IsV2) W86RoadRepair.PaintAccessRuts(td);
            EditorUtility.SetDirty(td);
            foreach (Texture2D tex in td.alphamapTextures) EditorUtility.SetDirty(tex);
            AssetDatabase.SaveAssets();
            float probe = td.GetHeight(1024, 1024), expect = lastHeights[1024, 1024] * td.size.y;
            Note($"terrain re-applied after the asset save: height probe {probe:0.00} m (expected {expect:0.00} m)");
            lastHeights = null; lastHoles = null; lastAlpha = null;
        }

        static Texture2D LoadPng(string path)
        {
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            t.LoadImage(File.ReadAllBytes(path));              // row 0 of the PNG (north) ends up at y = height - 1
            return t;
        }

        static readonly Dictionary<string, string[]> TreeKit = new()
        {
            ["pine"] = new[] { "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_A_v04.prefab", "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_B_v04.prefab", "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_C_v04.prefab" },
            // i10 set: forest conifers and bare Rough trees = the V19Wind versions (Map/Wind/Trees_v01), the rest = COZY kit (Leafy_v04_i08, OaksPines_i09)
            ["spruce"] = new[] { "Assets/OnlyVolunteers/Art/Trees/Conifers_v04_03/Prefabs/Forest_Spruce_A_v04_03_Wind.prefab", "Assets/OnlyVolunteers/Art/Trees/Conifers_v04_03/Prefabs/Forest_Spruce_B_v04_03_Wind.prefab", "Assets/OnlyVolunteers/Art/Trees/Conifers_v04_03/Prefabs/Forest_Fir_v04_03_Wind.prefab", "Assets/OnlyVolunteers/Art/Trees/Conifers_v04_03/Prefabs/Forest_Young_v04_03_Wind.prefab" },
            ["birch"] = new[] { "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_A_v04_04.prefab", "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_B_v04_04.prefab" },
            ["oak"] = new[] { "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_A_v01_02.prefab", "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_B_v01_02.prefab", "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_C_v01_02.prefab" },
            ["leafy"] = new[] { "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Apple_A_v04_03.prefab", "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Apple_B_v04_03.prefab", "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_C_v04_04.prefab" },
            // T114 b (W86 integration): the same palms with brighter leaves / bark (material copies only)
            ["palm"] = new[] { "Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Prefabs/Palm_A_v04_03_T114b.prefab", "Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Prefabs/Palm_B_v04_03_T114b.prefab", "Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Prefabs/Palm_C_v04_03_T114b.prefab" },
            ["bush"] = new[] { "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Bush_A_v04_03.prefab", "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Bush_B_v04_03.prefab" },
            ["bare"] = new[] { "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_01_v19_Wind_v01.prefab", "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_02_v19_Wind_v01.prefab", "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_03_v19_Wind_v01.prefab" },
        };

        // Tree-like prop kinds by whole word ("street_lamp" contains "tree" as a substring: v01 turned the 59 Rough lamps into trees).
        static readonly HashSet<string> TreeWords = new() { "tree", "trees", "palm", "bush", "shrub", "oak", "apple", "pine", "birch", "poplar", "spruce" };
        static bool IsTree(string kind) => kind.Split('_', ' ', '-').Any(w => TreeWords.Contains(w));

        static readonly List<TreePrototype> Protos = new();
        static readonly Dictionary<string, List<int>> ProtoIdx = new();
        static readonly List<TreeInstance> TreeList = new();

        static int Proto(string kind, float h)
        {
            if (!ProtoIdx.TryGetValue(kind, out var idx)) kind = kind.Contains("palm") ? "palm" : kind.Contains("bare") ? "bare" : kind.Contains("bush") ? "bush" : "leafy";
            idx = ProtoIdx.TryGetValue(kind, out var i2) ? i2 : null;
            if (idx == null || idx.Count == 0) return -1;
            return idx[(int)(h * idx.Count) % idx.Count];
        }

        // G45: coordinate-derived hashes never consume a shared RNG or depend on iteration order.
        static Vector2[][] ForestTreePolygons = Array.Empty<Vector2[]>();
        static readonly HashSet<long> ForestTreeRemoved = new();
        static bool ForestTreeAt(float x, float z) => ForestTreePolygons.Any(p => W76Atmosphere.Inside(p, new Vector2(x, z)));
        static long TreePositionKey(float x, float z) => ((long)Mathf.RoundToInt(x * 10f) << 32) | (uint)Mathf.RoundToInt(z * 10f);
        static uint TreeSeed(float x, float z, uint salt)
        {
            unchecked
            {
                uint h = (uint)Mathf.RoundToInt(x * 10f) * 0x9e3779b9u ^ (uint)Mathf.RoundToInt(z * 10f) * 0x85ebca6bu ^ salt;
                h ^= h >> 16; h *= 0x7feb352du; h ^= h >> 15; h *= 0x846ca68bu; return h ^ (h >> 16);
            }
        }
        static float TreeRandom(float x, float z, uint salt) => (TreeSeed(x, z, salt) & 0xffffffu) / 16777216f;
        static void AddTree(string kind, float x, float z, float scale, float rotDeg, bool designed = false)
        {
            bool forest = IsV2 && ForestTreeAt(x, z);
            if (forest && ForestTreeRemoved.Contains(TreePositionKey(x, z))) return;
            if (IsV2 && !designed && kind != "bare" && kind != "bush" && kind != "palm")
            {
                float mix = TreeRandom(x, z, 4502u);
                if (forest) kind = mix < .22f ? "oak" : mix < .55f ? "spruce" : "pine";
                else if (mix < .14f) kind = "spruce";
                else if (mix < .30f) kind = "pine";
            }
            int p = Proto(kind, IsV2 ? TreeRandom(x, z, 4503u) : Mathf.Repeat(x * .37f + z * .71f, 1f));
            if (p < 0) return;
            float height = scale;
            if (IsV2 && !designed && kind != "bare" && kind != "bush" && kind != "palm")
            {
                height *= Mathf.Lerp(forest ? .82f : .94f, forest ? 1.18f : 1.06f, TreeRandom(x, z, 4504u));
                // New lowest crown is 2.1 m: preserve >=1.89 m of clear trunk, above the 1.8 m player.
                if (kind == "spruce") height = Mathf.Clamp(height, .90f, 1.18f);
            }
            TreeList.Add(new TreeInstance
            {
                prototypeIndex = p,
                position = new Vector3(x / W, 0f, z / Hh),
                widthScale = scale, heightScale = height, rotation = rotDeg * Mathf.Deg2Rad,
                color = Color.white, lightmapColor = Color.white
            });
        }

        static void Trees(TerrainData td)
        {
            Protos.Clear(); ProtoIdx.Clear(); TreeList.Clear();
            foreach (var kv in TreeKit)
            {
                ProtoIdx[kv.Key] = new List<int>();
                foreach (string p in kv.Value)
                {
                    var treePath = !IsV2 ? p.Replace("Art/Trees/Conifers_v04_03/Prefabs/Forest_", "Map/Wind/Trees_v01/Prefabs/Forest_").Replace("_v04_03_Wind.prefab", "_v03_04_Wind_v01.prefab") : p;
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(treePath);
                    if (!prefab) { Note("missing tree prefab " + p); continue; }
                    int at = Protos.FindIndex(t => t.prefab == prefab);
                    if (at < 0) { Protos.Add(new TreePrototype { prefab = prefab }); at = Protos.Count - 1; }
                    ProtoIdx[kv.Key].Add(at);
                }
            }
            td.treePrototypes = Protos.ToArray();
            var vj = Obj(Json.Parse(File.ReadAllText(Data + "/vegetation_v85.json")));
            ForestTreePolygons = IsV2 ? Arr(Get(Obj(Json.Parse(File.ReadAllText(Data + "/districts/forest_v85.json"))), "zones"))
                .Select(Obj).Where(z => S(Get(z, "kind")) == "veg_zone").Select(z => V2s(Get(z, "poly"))).Where(p => p.Length >= 3).ToArray() : Array.Empty<Vector2[]>();
            ForestTreeRemoved.Clear();
            if (IsV2)
            {
                var forest = Arr(Get(vj, "trees")).Select(Arr).Where(t => ForestTreeAt(F(t[0]), F(t[1]))).ToArray();
                foreach (var t in forest.OrderBy(t => TreeSeed(F(t[0]), F(t[1]), 4501u)).ThenBy(t => TreePositionKey(F(t[0]), F(t[1]))).Take(Mathf.RoundToInt(forest.Length * .15f)))
                    ForestTreeRemoved.Add(TreePositionKey(F(t[0]), F(t[1])));
                Note($"G45 forest: {forest.Length} -> {forest.Length - ForestTreeRemoved.Count}; removed {ForestTreeRemoved.Count} stable placements");
            }
            foreach (object o in Arr(Get(vj, "trees")))
            {
                var t = Arr(o);
                AddTree((string)t[2], F(t[0]), F(t[1]), F(t[3], 1f), F(t[4]));
            }
            // designed trees of the districts (Hamlet orchard + square tree, beach / Elite palm rows): only those s05 kept (same hard rules,
            // duplicates between districts removed)
            var keep = new HashSet<string>(Arr(Get(vj, "designed_from_districts")).Select(o => S(Get(Obj(o), "id"))));
            foreach (string f in Directory.GetFiles(Data + "/districts", "*_v85.json").OrderBy(f => f, StringComparer.Ordinal))
                foreach (object o in Arr(Get(Obj(Json.Parse(File.ReadAllText(f))), "props")))
                {
                    var p = Obj(o);
                    string kind = (S(Get(p, "kind"), "") ?? "").ToLowerInvariant();
                    if (!IsTree(kind) || !keep.Contains(S(Get(p, "id"), ""))) continue;
                    Vector2 q = V2(Get(p, "pos"));
                    string k = kind.Contains("palm") ? "palm" : kind.Contains("bush") || kind.Contains("shrub") ? "bush" : f.Contains("rough") ? "bare" : kind.Contains("pine") ? "pine" : kind.Contains("birch") ? "birch" : kind.Contains("oak") ? "oak" : "leafy";
                    AddTree(k, q.x, q.y, 1f, F(Get(p, "rot_deg")), true);
                }
            // A partial vegetation rebuild keeps the exact reviewed XYZ, including terrain-snap rounding.
            var prior = td.treeInstances.GroupBy(t => TreePositionKey(t.position.x * W, t.position.z * Hh)).ToDictionary(g => g.Key, g => g.First().position);
            td.SetTreeInstances(TreeList.ToArray(), true);
            if (prior.Count > 0)
            {
                var trees = td.treeInstances;
                for (int i = 0; i < trees.Length; i++)
                    if (prior.TryGetValue(TreePositionKey(trees[i].position.x * W, trees[i].position.z * Hh), out var position)) trees[i].position = position;
                td.SetTreeInstances(trees, false);
            }
        }

        // ------------------------------------------------------------------ meshes
        sealed class MB
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> UV = new(); public readonly List<Vector2> UV1 = new(); public readonly List<int> T = new();
            public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); V.Add(d); UV.Add(ua); UV.Add(ub); UV.Add(uc); UV.Add(ud);
                T.Add(n); T.Add(n + 1); T.Add(n + 2); T.Add(n); T.Add(n + 2); T.Add(n + 3);     // front = (b - a) x (c - a): roads up, walls out
            }
            public void Tri(Vector3 a, Vector3 b, Vector3 c, Vector2 ua, Vector2 ub, Vector2 uc)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); UV.Add(ua); UV.Add(ub); UV.Add(uc);
                T.Add(n); T.Add(n + 1); T.Add(n + 2);
            }
            public void QuadBoth(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
            {
                Quad(a, b, c, d, ua, ub, uc, ud); Quad(d, c, b, a, ud, uc, ub, ua);
            }
            public Mesh Build(string name, bool save = true)
            {
                var m = new Mesh { name = name, indexFormat = V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                m.SetVertices(V); m.SetUVs(0, UV); if (UV1.Count == V.Count) m.SetUVs(1, UV1); m.SetTriangles(T, 0);
                m.RecalculateNormals(); m.RecalculateBounds();
                if (save) AssetDatabase.CreateAsset(m, Gen + "/Meshes/" + Safe(name) + ".asset");
                return m;
            }
        }

        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_').ToArray());

        static GameObject MeshGo(string name, Transform parent, Mesh mesh, Material mat, bool collider = false, bool convex = false)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            if (collider) { var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = convex; }
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            return go;
        }

        static List<Vector2> Resample(Vector2[] pl, float step)
        {
            var o = new List<Vector2>();
            if (pl.Length == 0) return o;
            o.Add(pl[0]);
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                float L = (pl[i + 1] - pl[i]).magnitude;
                int n = Mathf.Max(1, Mathf.CeilToInt(L / step));
                for (int k = 1; k <= n; k++) o.Add(Vector2.Lerp(pl[i], pl[i + 1], k / (float)n));
            }
            return o;
        }

        // Ribbon along a polyline at terrain height (+lift); u across (m / tile), v along (m / tile).
        static Mesh Ribbon(string name, Vector2[] pl, float width, float tile, float lift, Func<int, float> heightAt = null, float step = 2f)
        {
            var pts = Resample(pl, step);
            var mb = new MB();
            float acc = 0f;
            Vector3 pl0 = default, pr0 = default;
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 dir = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[Mathf.Max(i - 1, 0)]).normalized;
                Vector2 n = new(-dir.y, dir.x);
                Vector2 l = pts[i] + n * width * .5f, r = pts[i] - n * width * .5f;
                float hc = heightAt != null ? heightAt(i) : float.NaN;
                Vector3 pl1 = new(l.x, (float.IsNaN(hc) ? Height(l.x, l.y) : hc) + lift, l.y);
                Vector3 pr1 = new(r.x, (float.IsNaN(hc) ? Height(r.x, r.y) : hc) + lift, r.y);
                if (i > 0)
                {
                    float a2 = acc + (pts[i] - pts[i - 1]).magnitude;
                    mb.Quad(pl0, pl1, pr1, pr0, new Vector2(0, acc / tile), new Vector2(0, a2 / tile), new Vector2(width / tile, a2 / tile), new Vector2(width / tile, acc / tile));
                    acc = a2;
                }
                pl0 = pl1; pr0 = pr1;
            }
            return mb.Build(name);
        }

        // ------------------------------------------------------------------ roads
        static void BuildRoads(Transform root)
        {
            var parent = new GameObject("Roads").transform; parent.SetParent(root, false);
            var rj = Obj(Json.Parse(File.ReadAllText(Data + "/roads_v85.json")));
            int n = 0, nb = 0;
            WorldRoads.Clear();
            foreach (object o in Arr(Get(rj, "roads")))
            {
                var r = Obj(o);
                string kind = S(Get(r, "kind")), id = S(Get(r, "id"));
                var pl = V2s(Get(r, "points"));
                if (pl.Length < 2) continue;
                float w = F(Get(r, "width_m"), 6.4f);
                WorldRoads.Add((id, pl, w, kind));
                if (kind == "tunnel" || kind == "sand_track" || kind == "dirt") continue;      // tunnel mesh / splat ruts only
                var hs = Arr(Get(r, "heights")).Select(x => F(x)).ToArray();
                if (kind == "bridge") { BuildBridge(parent, id, pl, hs, w, F(Get(r, "carriageway_m"), 6.4f), F(Get(r, "pier_step_m"), 21f)); nb++; continue; }
                string surf = S(Get(r, "surface"), "asphalt_A5d12");
                var pts = ResamplePy(pl, 2f);
                Func<int, float> hAt = hs.Length == pts.Count ? i => hs[i] : (Func<int, float>)null;
                if (hAt == null) Note($"road {id}: {hs.Length} heights for {pts.Count} points -> terrain heights");
                var mesh = RibbonPts("Road_" + id, pts, w, Tile(surf), .05f + .004f * (n % 9), hAt);
                MeshGo("Road_" + id, parent, mesh, Mat(surf), true);
                if (kind == "stone_serpentine") Parapet(parent, id, pl, w);
                var br = Obj(Get(r, "bridge"));
                if (br != null) { BridgeSpan(parent, id, pts, hAt, w, V2(Get(br, "from")), V2(Get(br, "to"))); nb++; }
                n++;
            }
            Note($"roads: {n} meshes (own grade-limited heights, mesh colliders), {nb} bridges; dirt roads / sand ruts = splat");
        }

        // world roads (centre line, width) for sidewalk curb drops, grass and details
        static readonly List<(string id, Vector2[] pl, float w, string kind)> WorldRoads = new();

        // Same as Tools/MapV85/common.resample (n = max(1, int(L / step)) per segment) so the road heights of s03 line up 1:1.
        static List<Vector2> ResamplePy(Vector2[] pl, float step)
        {
            var o = new List<Vector2> { pl[0] };
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                float L = (pl[i + 1] - pl[i]).magnitude;
                int k = Mathf.Max(1, (int)(L / step));
                for (int j = 1; j <= k; j++) o.Add(Vector2.Lerp(pl[i], pl[i + 1], j / (float)k));
            }
            return o;
        }

        static Mesh RibbonPts(string name, List<Vector2> pts, float width, float tile, float lift, Func<int, float> heightAt)
        {
            var mb = new MB();
            float acc = 0f;
            Vector3 pl0 = default, pr0 = default;
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 dir = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[Mathf.Max(i - 1, 0)]).normalized;
                Vector2 nrm = new(-dir.y, dir.x);
                Vector2 l = pts[i] + nrm * width * .5f, r = pts[i] - nrm * width * .5f;
                float hc = heightAt != null ? heightAt(i) : float.NaN;
                Vector3 pl1 = new(l.x, (float.IsNaN(hc) ? Height(l.x, l.y) : hc) + lift, l.y);
                Vector3 pr1 = new(r.x, (float.IsNaN(hc) ? Height(r.x, r.y) : hc) + lift, r.y);
                if (i > 0)
                {
                    float a2 = acc + (pts[i] - pts[i - 1]).magnitude;
                    mb.Quad(pl0, pl1, pr1, pr0, new Vector2(0, acc / tile), new Vector2(0, a2 / tile), new Vector2(width / tile, a2 / tile), new Vector2(width / tile, acc / tile));
                    acc = a2;
                }
                pl0 = pl1; pr0 = pr1;
            }
            return mb.Build(name);
        }

        // Real bridge (v10 §5, v02 §5): deck 8.8 m (carriageway 6.4 + kerbs), parapets 1.1 m both sides, piers every ~21 m to the
        // sea floor, abutments where the shores end. Deck heights = the road profile (level with both ends, crest mid-span).
        static void BuildBridge(Transform parent, string id, Vector2[] pl, float[] hs, float deck, float carriage, float pierStep)
        {
            var pts = ResamplePy(pl, 2f);
            Func<int, float> hAt = hs.Length == pts.Count ? i => hs[i] : (Func<int, float>)(i => Mathf.Max(3f, Height(pts[i].x, pts[i].y)));
            MeshGo("Bridge_" + id + "_deck", parent, RibbonPts("Bridge_" + id + "_deck", pts, carriage, Tile("asphalt_A5d12"), .02f, hAt), Mat("asphalt_A5d12"), true);
            var kerb = new MB(); var slab = new MB(); var rail = new MB();
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], b = pts[i], d = (b - a).normalized, nrm = new(-d.y, d.x);
                float ya = hAt(i - 1), yb = hAt(i), L = (b - a).magnitude;
                foreach (int sg in new[] { -1, 1 })
                {
                    Vector2 i0 = a + nrm * sg * carriage * .5f, i1 = b + nrm * sg * carriage * .5f, o0 = a + nrm * sg * deck * .5f, o1 = b + nrm * sg * deck * .5f;
                    Vector3 I0 = new(i0.x, ya + .17f, i0.y), I1 = new(i1.x, yb + .17f, i1.y), O0 = new(o0.x, ya + .17f, o0.y), O1 = new(o1.x, yb + .17f, o1.y);
                    if (sg > 0) kerb.Quad(I0, I1, O1, O0, Vector2.zero, new Vector2(0, L), new Vector2(1, L), new Vector2(1, 0));
                    else kerb.Quad(O0, O1, I1, I0, Vector2.zero, new Vector2(0, L), new Vector2(1, L), new Vector2(1, 0));
                    kerb.QuadBoth(new Vector3(i0.x, ya - .02f, i0.y), new Vector3(i1.x, yb - .02f, i1.y), I1, I0, Vector2.zero, new Vector2(L, 0), new Vector2(L, .2f), new Vector2(0, .2f));
                    rail.QuadBoth(O0, O1, O1 + Vector3.up * 1.1f, O0 + Vector3.up * 1.1f, Vector2.zero, new Vector2(L / 3f, 0), new Vector2(L / 3f, .37f), new Vector2(0, .37f));
                }
                Vector2 la = a + nrm * deck * .5f, ra = a - nrm * deck * .5f, lb = b + nrm * deck * .5f, rb = b - nrm * deck * .5f;
                slab.Quad(new Vector3(ra.x, ya - .9f, ra.y), new Vector3(rb.x, yb - .9f, rb.y), new Vector3(lb.x, yb - .9f, lb.y), new Vector3(la.x, ya - .9f, la.y), Vector2.zero, new Vector2(0, L), new Vector2(1, L), new Vector2(1, 0));
                foreach (int sg in new[] { -1, 1 })
                {
                    Vector2 e0 = a + nrm * sg * deck * .5f, e1 = b + nrm * sg * deck * .5f;
                    slab.QuadBoth(new Vector3(e0.x, ya - .9f, e0.y), new Vector3(e1.x, yb - .9f, e1.y), new Vector3(e1.x, yb + .17f, e1.y), new Vector3(e0.x, ya + .17f, e0.y), Vector2.zero, new Vector2(L, 0), new Vector2(L, 1), new Vector2(0, 1));
                }
            }
            MeshGo("Bridge_" + id + "_kerbs", parent, kerb.Build("Bridge_" + id + "_kerbs"), Mat("concrete_SK3c"), true);
            MeshGo("Bridge_" + id + "_slab", parent, slab.Build("Bridge_" + id + "_slab"), Mat("concrete_SK3c"));
            MeshGo("Bridge_" + id + "_parapets", parent, rail.Build("Bridge_" + id + "_parapets"), Mat("concrete_SK3c"), true);
            float total = 0f; for (int i = 1; i < pts.Count; i++) total += (pts[i] - pts[i - 1]).magnitude;
            int np = 0;
            for (float s0 = pierStep; s0 < total - pierStep * .5f; s0 += pierStep)
            {
                Vector2 q = PointAt(pts, s0);
                int idx = Mathf.Clamp(Mathf.RoundToInt(s0 / Mathf.Max(.01f, total) * (pts.Count - 1)), 0, pts.Count - 1);
                float top = hAt(idx) - .9f, bottom = Mathf.Min(Height(q.x, q.y), -1f) - 1f;
                Vector2 d = (pts[Mathf.Min(idx + 1, pts.Count - 1)] - pts[Mathf.Max(idx - 1, 0)]).normalized;
                Box(parent, "Pier_" + id + "_" + np++, new Vector3(q.x, (top + bottom) * .5f, q.y), new Vector3(deck - 1.5f, top - bottom, 1.6f), -Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg + 90f, "concrete_SK3c", true);
            }
            Note($"bridge {id}: {total:0} m, deck {deck} m, {np} piers");
        }

        // Short span inside a road (valley road over the river): concrete slab under the road ribbon, parapets on both sides.
        static void BridgeSpan(Transform parent, string id, List<Vector2> pts, Func<int, float> hAt, float w, Vector2 from, Vector2 to)
        {
            var rail = new MB(); var slab = new MB();
            float deck = w + 2.4f;
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], b = pts[i], mid = (a + b) * .5f;
                if (DistSeg(mid, from, to) > 2.5f) continue;
                Vector2 d = (b - a).normalized, nrm = new(-d.y, d.x);
                float ya = hAt != null ? hAt(i - 1) : Height(a.x, a.y), yb = hAt != null ? hAt(i) : Height(b.x, b.y), L = (b - a).magnitude;
                foreach (int sg in new[] { -1, 1 })
                {
                    Vector2 o0 = a + nrm * sg * deck * .5f, o1 = b + nrm * sg * deck * .5f;
                    rail.QuadBoth(new Vector3(o0.x, ya, o0.y), new Vector3(o1.x, yb, o1.y), new Vector3(o1.x, yb + 1.1f, o1.y), new Vector3(o0.x, ya + 1.1f, o0.y), Vector2.zero, new Vector2(L / 3f, 0), new Vector2(L / 3f, .37f), new Vector2(0, .37f));
                }
                Vector2 la = a + nrm * deck * .5f, ra = a - nrm * deck * .5f, lb = b + nrm * deck * .5f, rb = b - nrm * deck * .5f;
                slab.Quad(new Vector3(ra.x, ya - .8f, ra.y), new Vector3(rb.x, yb - .8f, rb.y), new Vector3(lb.x, yb - .8f, lb.y), new Vector3(la.x, ya - .8f, la.y), Vector2.zero, new Vector2(0, L), new Vector2(1, L), new Vector2(1, 0));
                slab.Quad(new Vector3(la.x, ya + .04f, la.y), new Vector3(lb.x, yb + .04f, lb.y), new Vector3(rb.x, yb + .04f, rb.y), new Vector3(ra.x, ya + .04f, ra.y), Vector2.zero, new Vector2(0, L), new Vector2(1, L), new Vector2(1, 0));
            }
            if (rail.V.Count == 0) return;
            MeshGo("BridgeSpan_" + id + "_parapets", parent, rail.Build("BridgeSpan_" + id + "_parapets"), Mat("concrete_SK3c"), true);
            MeshGo("BridgeSpan_" + id + "_slab", parent, slab.Build("BridgeSpan_" + id + "_slab"), Mat("concrete_SK3c"), true);
        }

        static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
        {
            Vector2 v = b - a; float t = Mathf.Clamp01(Vector2.Dot(p - a, v) / Mathf.Max(1e-6f, v.sqrMagnitude));
            return (p - (a + v * t)).magnitude;
        }

        // Elite stone road: stone parapet outside (centre of the Elite = inside), lamps every 18 m (GripAnchor).
        static void Parapet(Transform parent, string id, Vector2[] pl, float w)
        {
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/features_v85.json")));
            Vector2 c = V2(Get(Obj(Get(tj, "elite")), "centre"));
            var pts = Resample(pl, 3f);
            var mb = new MB();
            var lamps = new GameObject("Lamps_" + id).transform; lamps.SetParent(parent, false);
            float acc = 0f;
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], b = pts[i], d = (b - a).normalized, nrm = new(-d.y, d.x);
                if (Vector2.Dot(nrm, (a + b) * .5f - c) < 0) nrm = -nrm;
                Vector2 a2 = a + nrm * (w * .5f + .3f), b2 = b + nrm * (w * .5f + .3f);
                Vector3 A = P(a2), B = P(b2);
                mb.QuadBoth(A, B, B + Vector3.up * .8f, A + Vector3.up * .8f, Vector2.zero, new Vector2(3f / 2f, 0), new Vector2(1.5f, .4f), new Vector2(0, .4f));
                acc += (b - a).magnitude;
                if (acc > 18f) { acc = 0f; Lamp(lamps, a2 + nrm * .3f); }
            }
            var m = mb.Build("Parapet_" + id);
            MeshGo("Parapet_" + id, parent, m, Mat("cobble_SK2c"), true);
        }

        static void Lamp(Transform parent, Vector2 q)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = "Lamp"; go.transform.SetParent(parent, false);
            go.transform.position = P(q, 2.5f); go.transform.localScale = new Vector3(.16f, 2.5f, .16f);
            go.GetComponent<MeshRenderer>().sharedMaterial = Mat("metal_painted_SK6a");
            go.AddComponent<W76GripAnchor>();
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        }

        // ------------------------------------------------------------------ tunnel (box section, concrete, glare zone)
        static Vector2[] TunnelAxis = new Vector2[0];

        static void BuildTunnel(Transform root)
        {
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/terrain_v85.json")));
            var t = Obj(Get(tj, "tunnel"));
            TunnelAxis = V2s(Get(t, "axis"));
            var ph = Arr(Get(t, "portal_heights_m"));
            float h0 = F(ph[0]), h1 = F(ph[1]), width = F(Get(t, "width_m"), 9f), clear = F(Get(t, "clear_height_m"), 5.5f);
            var pts = Resample(TunnelAxis, 2f);
            float total = 0f; for (int i = 1; i < pts.Count; i++) total += (pts[i] - pts[i - 1]).magnitude;
            var shell = new MB(); var road = new MB();
            float acc = 0f, tile = Tile("concrete_SK3c");
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], b = pts[i], d = (b - a).normalized, n = new(-d.y, d.x);
                float L = (b - a).magnitude, ya = Mathf.Lerp(h0, h1, acc / total), yb = Mathf.Lerp(h0, h1, (acc + L) / total);
                Vector2 al = a + n * width * .5f, ar = a - n * width * .5f, bl = b + n * width * .5f, br = b - n * width * .5f;
                Vector3 A0 = new(al.x, ya, al.y), A1 = new(ar.x, ya, ar.y), B0 = new(bl.x, yb, bl.y), B1 = new(br.x, yb, br.y), up = Vector3.up * clear;
                float u0 = acc / tile, u1 = (acc + L) / tile;
                road.Quad(A0, B0, B1, A1, new Vector2(0, u0), new Vector2(0, u1), new Vector2(1, u1), new Vector2(1, u0));
                shell.Quad(A0 + up, B0 + up, B0, A0, new Vector2(u0, 1), new Vector2(u1, 1), new Vector2(u1, 0), new Vector2(u0, 0));    // left wall
                shell.Quad(A1, B1, B1 + up, A1 + up, new Vector2(u0, 0), new Vector2(u1, 0), new Vector2(u1, 1), new Vector2(u0, 1));    // right wall
                shell.Quad(A1 + up, B1 + up, B0 + up, A0 + up, new Vector2(u0, .6f), new Vector2(u1, .6f), new Vector2(u1, 1), new Vector2(u0, 1));  // ceiling (T128: the concrete part of the shell texture)
                acc += L;
            }
            var parent = new GameObject("Tunnel").transform; parent.SetParent(root, false);
            MeshGo("Tunnel_shell", parent, shell.Build("Tunnel_shell"), Mat("concrete_SK3c"), true);
            MeshGo("Tunnel_road", parent, road.Build("Tunnel_road"), Mat("asphalt_A5d12"), true);
            TunnelExtrasT128(parent, pts, total, h0, h1, width, clear);
            for (int e = 0; e < 2; e++)
            {
                Vector2 p0 = e == 0 ? pts[0] : pts[pts.Count - 1], p1 = e == 0 ? pts[1] : pts[pts.Count - 2];
                Vector2 dIn = (p1 - p0).normalized, nrm = new(-dIn.y, dIn.x);
                float y0 = e == 0 ? h0 : h1, yaw = Mathf.Atan2(dIn.x, dIn.y) * Mathf.Rad2Deg;
                Vector2 face = p0 - dIn * .6f;
                foreach (int sgn in new[] { -1, 1 })
                {
                    Vector2 c = face + nrm * sgn * (width * .5f + 3f);
                    Box(parent, "Portal_" + e + (sgn < 0 ? "_L" : "_R"), new Vector3(c.x, y0 + 4f, c.y), new Vector3(6f, clear + 9f, 1.2f), yaw, "concrete_SK3c", true);
                }
                Box(parent, "Portal_" + e + "_lintel", new Vector3(face.x, y0 + clear + 3f, face.y), new Vector3(width + 12f, 6f, 1.2f), yaw, "concrete_SK3c", true);
            }
            var lights = new GameObject("Tunnel_lights").transform; lights.SetParent(parent, false);
            for (float s = 10f; s < total; s += 24f)
            {
                Vector2 q = PointAt(pts, s);
                var l = new GameObject("Light").AddComponent<Light>();
                l.transform.SetParent(lights, false);
                l.transform.position = new Vector3(q.x, Mathf.Lerp(h0, h1, s / total) + clear - .3f, q.y);
                l.type = LightType.Point; l.range = 14f; l.intensity = 2f; l.color = new Color(1f, .82f, .6f); l.shadows = LightShadows.None;
            }
            Note($"tunnel: {total:0} m, portals {h0:0.0} / {h1:0.0} m, cover min {F(Get(t, "min_cover_m")):0.0} m");
        }

        static Vector2 PointAt(List<Vector2> pts, float s)
        {
            for (int i = 1; i < pts.Count; i++)
            {
                float L = (pts[i] - pts[i - 1]).magnitude;
                if (s <= L) return Vector2.Lerp(pts[i - 1], pts[i], s / Mathf.Max(L, 1e-4f));
                s -= L;
            }
            return pts[pts.Count - 1];
        }

        // ------------------------------------------------------------------ water
        static void BuildWater(Transform root)
        {
            var parent = new GameObject("Water").transform; parent.SetParent(root, false);
            var sea = Mat(SeaMaterialKey);
            if (!sea || !sea.shader || !sea.shader.name.Contains("Water")) Note("WARNING: Sea_trial_calm_v09 not found or not the v05 water shader");
            // sea: dense grid over the map (vertex waves need vertices), coarse skirt to the horizon
            var mb = new MB();
            const float step = 4f;
            for (float z = -200f; z < Hh + 200f; z += step)
                for (float x = -200f; x < W + 200f; x += step)
                {
                    float hc = x >= 0 && x <= W && z >= 0 && z <= Hh ? Height(x + 2f, z + 2f) : BackdropHeight(x + 2f, z + 2f);
                    if (hc > 3f) continue;                                    // under land (map or steppe backdrop): no water quads
                    mb.Quad(new Vector3(x, 0, z), new Vector3(x, 0, z + step), new Vector3(x + step, 0, z + step), new Vector3(x + step, 0, z),
                        new Vector2(x, z) / 10f, new Vector2(x, z + step) / 10f, new Vector2(x + step, z + step) / 10f, new Vector2(x + step, z) / 10f);
                }
            MeshGo("Sea_dense_0m", parent, mb.Build("Sea_dense"), sea).GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            // far sea all round outside the dense grid (south, west, east; north only east of the steppe, x > 1100: v67 harbour is sea)
            var ring = new MB();
            void FarQuad(float x0, float z0, float x1, float z1) => ring.Quad(new Vector3(x0, -.05f, z0), new Vector3(x0, -.05f, z1), new Vector3(x1, -.05f, z1), new Vector3(x1, -.05f, z0),
                new Vector2(x0, z0) / 10f, new Vector2(x0, z1) / 10f, new Vector2(x1, z1) / 10f, new Vector2(x1, z0) / 10f);
            const float far = 6000f, g = 200f;
            FarQuad(-far, -far, W + far, -g);                    // south
            FarQuad(-far, -g, -g, Hh + g);                       // west
            FarQuad(W + g, -g, W + far, Hh + g);                 // east
            FarQuad(1100f, Hh + g, W + far, Hh + far);           // north-east (sea north of the harbour and Tramduro)
            if (BackdropOn) FarQuad(-far, Hh + g, 1100f, Hh + far);   // W86: north-west too; the steppe backdrop terrain covers it where it is land
            var farSea = MeshGo("Sea_far_ring", parent, ring.Build("Sea_far_ring"), sea);
            farSea.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            if (BackdropOn) farSea.layer = FarLayer;                 // drawn to the far plane (W85FarView), like the backdrop
            // inland water (v85 vectors): the river as one ribbon along its axis (flow mode, surface = bed + 1.2 m, bed of s03), lakes /
            // plunge pool / Hamlet pond / swamp as flat fills at their s03 surface. Disposal kinds for WaterQuery: River, Lake; Pond, Bog not.
            var flow = FlowMaterial(sea);
            var wj = Obj(Json.Parse(File.ReadAllText(Data + "/water_v85.json")));
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/terrain_v85.json")));
            var lakeLevel = Arr(Get(tj, "lakes")).Select(Obj).Where(l => l != null).ToDictionary(l => S(Get(l, "id")), l => F(Get(l, "surface_m"), 5f));
            int n = 0;
            WaterAreas.Clear();
            foreach (object o in Arr(Get(wj, "bodies")))
            {
                var b = Obj(o);
                string kind = S(Get(b, "kind")), id = S(Get(b, "id"));
                if (kind == "river" && Get(b, "surface_m") != null)
                {   // W86 (data v02): the water ribbon at the per-point surface of s03, no water in the underground spans
                    RiverV2(parent, b, flow, wj);
                    n++;
                    continue;
                }
                if (kind == "river")
                {
                    var axis = V2s(Get(b, "axis"));
                    var wid = Arr(Get(b, "width_m")).Select(x => F(x)).ToArray();
                    var rm = new MB();
                    for (int i = 0; i < axis.Length; i++)
                    {
                        Vector2 d = (axis[Mathf.Min(i + 1, axis.Length - 1)] - axis[Mathf.Max(i - 1, 0)]).normalized, nrm = new(-d.y, d.x);
                        float hw = (i < wid.Length ? wid[i] : 6f) * .5f + .8f, y = RiverBed(axis[i].y) + 1.2f;
                        foreach (var q in new[] { axis[i] + nrm * hw, axis[i] - nrm * hw }) { rm.V.Add(new Vector3(q.x, y, q.y)); rm.UV.Add(q / 10f); rm.UV1.Add(d * .8f); }
                        if (i > 0) { int k = rm.V.Count - 4; rm.T.AddRange(new[] { k, k + 2, k + 3, k, k + 3, k + 1 }); }
                    }
                    var rmesh = rm.Build("Water_River_" + id);
                    var rgo = MeshGo("Water_River_" + id, parent, rmesh, flow);
                    rgo.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
                    AddWaterArea(id, Audio.WaterKind.River, rmesh, true);
                    n++;
                    continue;
                }
                var outline = V2s(Get(b, "outline"));
                if (outline.Length < 3 || !(kind == "lake" || kind == "swamp" || kind == "pond")) continue;
                float lv = Get(b, "surface_m") != null ? F(Get(b, "surface_m")) : lakeLevel.TryGetValue(id, out float l0) ? l0 : outline.Average(q => Height(q.x, q.y)) + .2f;
                var mesh = Fill(id, outline, q => lv, Vector2.zero);
                var wk = kind == "swamp" ? Audio.WaterKind.Bog : kind == "pond" ? Audio.WaterKind.Pond : Audio.WaterKind.Lake;
                var go = MeshGo("Water_" + wk + "_" + id, parent, mesh, kind == "swamp" ? SwampMaterial(flow) : flow);
                go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
                AddWaterArea(id, wk, mesh, false);
                n++;
            }
            // waterfalls (mountain lake -> gorge; river -> sea at the Quiet Valley)
            foreach (object o in Arr(Get(wj, "bodies")))
            {
                var b = Obj(o);
                if (S(Get(b, "kind")) != "waterfall") continue;
                if (Get(b, "lip_edge") != null) { WaterfallV2(parent, b, sea); continue; }      // W86: geometry from the data
                Vector2 q = V2(Get(b, "at"));
                float top = F(Get(b, "top_m"), 9f), bottom = S(Get(b, "id")) == "waterfall_sea" ? 0f : RiverBed(q.y) + 1.2f;
                if (S(Get(b, "id")) == "waterfall_sea") top = RiverBed(q.y) + 1.2f;
                else top = bottom + top;
                var wf = WaterfallMaterial(sea);
                var m2 = new MB();
                m2.QuadBoth(new Vector3(q.x - 5f, top, q.y + 1f), new Vector3(q.x + 5f, top, q.y + 1f), new Vector3(q.x + 5f, bottom, q.y - 1f), new Vector3(q.x - 5f, bottom, q.y - 1f),
                    new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(0, 0));
                MeshGo("Waterfall_" + S(Get(b, "id")), parent, m2.Build("Waterfall_" + S(Get(b, "id"))), wf);
            }
            // sea return zone (out-of-bounds sea) all round the island: deep-sea cells (terrain < -1.2 m, i.e. past the ~8 m
            // shallow band at the beaches) merged into row runs + the outside of the map; the van is put back on the last dry point
            var zone = new GameObject("SeaReturnZone").AddComponent<SeaReturnZone>();
            zone.transform.SetParent(parent, false);
            var tris = new List<Vector2>();
            void Rect(float x0, float z0, float x1, float z1) { tris.AddRange(new[] { new Vector2(x0, z0), new Vector2(x1, z0), new Vector2(x1, z1), new Vector2(x0, z0), new Vector2(x1, z1), new Vector2(x0, z1) }); }
            Rect(-1500, -1500, W + 1500, 0); Rect(-1500, 0, 0, Hh); Rect(W, 0, W + 1500, Hh);       // south, west, east outside the terrain
            if (BackdropOn) Rect(1100, Hh, W + 1500, Hh + 1500);        // W86: the sea north of the harbour / Tramduro (outside the terrain)
            const float cell = 8f;
            for (float z = 0; z < Hh; z += cell)
            {
                float run = -1f;
                for (float x = 0; x <= W; x += cell)
                {
                    bool deep = x < W && new[] { Height(x, z), Height(x + cell, z), Height(x, z + cell), Height(x + cell, z + cell) }.All(hh => hh < -1.2f);
                    if (deep && run < 0) run = x;
                    if (!deep && run >= 0) { Rect(run, z, x, z + cell); run = -1f; }
                }
            }
            zone.Triangles = tris.ToArray();
            WaterAreas.Add(new Audio.WaterData.Area { Id = "sea", Kind = Audio.WaterKind.Sea, SurfaceY = 0f, Triangles = tris.SelectMany(t => new[] { t.x, t.y }).ToArray() });
            var wd = ScriptableObject.CreateInstance<Audio.WaterData>();
            wd.PlanRevision = $"W85_{Ver} (data {Ver})"; wd.Areas = WaterAreas.ToArray();
            AssetDatabase.CreateAsset(wd, Gen + $"/W85_WaterData_{Ver}.asset");
            Note($"water: dense sea grid {mb.V.Count / 4} quads + far plane, {n} inland bodies (flow mode), sea return zone {tris.Count / 3} triangles all round; " +
                 $"WaterData {Gen}/W85_WaterData_{Ver}.asset: " + string.Join(", ", WaterAreas.GroupBy(a => a.Kind).Select(g => g.Key + " " + g.Count())));
        }

        // WaterQuery data for this map (disposal: River / Lake / Canal only; Pond, Bog, Pool, Sea not). Rivers slope, so each
        // river triangle is its own area at its mean level; lakes / ponds / bog are one flat area.
        static readonly List<Audio.WaterData.Area> WaterAreas = new();

        static void AddWaterArea(string id, Audio.WaterKind kind, Mesh m, bool perTriangle)
        {
            var v = m.vertices; var t = m.triangles;
            if (!perTriangle)
            {
                WaterAreas.Add(new Audio.WaterData.Area { Id = id, Kind = kind, SurfaceY = v.Average(q => q.y), Triangles = t.SelectMany(i => new[] { v[i].x, v[i].z }).ToArray() });
                return;
            }
            for (int i = 0; i + 2 < t.Length; i += 3)
                WaterAreas.Add(new Audio.WaterData.Area { Id = id + "_" + i / 3, Kind = kind, SurfaceY = (v[t[i]].y + v[t[i + 1]].y + v[t[i + 2]].y) / 3f,
                    Triangles = new[] { v[t[i]].x, v[t[i]].z, v[t[i + 1]].x, v[t[i + 1]].z, v[t[i + 2]].x, v[t[i + 2]].z } });
        }

        // River bed of the v85 terrain (lower bed: the gorge is cut into the ground).
        static float RiverBed(float y) => 0.9f + 1.4f * Sm((y - 96f) / 220f) + 10f * Sm((y - 600f) / 160f);   // Tools/MapV85/s03_terrain.py bed_line
        static float Sm(float t) { t = Mathf.Clamp01(t); return t * t * (3f - 2f * t); }

        static Material FlowMaterial(Material sea)
        {
            string p = Gen + "/Materials/W85_water_flow.mat";
            var m = new Material(sea) { name = "W85_water_flow" };
            m.SetFloat("_ENABLEWAVE", 0f); m.DisableKeyword("_ENABLEWAVE");
            m.SetFloat("_OV_MeshFlow", 1f); m.EnableKeyword("_OV_FLOW");
            AssetDatabase.CreateAsset(m, p); created++;
            return m;
        }

        static Material SwampMaterial(Material flow)
        {
            string p = Gen + "/Materials/W85_water_swamp.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (existing) return existing;
            var m = new Material(flow) { name = "W85_water_swamp" };
            m.SetColor("_Color_Shallow", new Color(.20f, .26f, .18f)); m.SetColor("_Color_Deep", new Color(.10f, .14f, .10f));
            m.SetColor("_OV_ColorMid", new Color(.14f, .19f, .13f));
            AssetDatabase.CreateAsset(m, p); created++;
            return m;
        }

        static Material WaterfallMaterial(Material sea)
        {
            string p = Gen + "/Materials/W85_waterfall.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (existing) return existing;
            var m = new Material(sea) { name = "W85_waterfall" };
            m.SetFloat("_OV_Mode", 1f); m.DisableKeyword("_OV_MODE_SURFACE"); m.EnableKeyword("_OV_MODE_WATERFALL");
            var tex = ImportTexture(S(Get(Obj(Get(MatMap, "waterfall")), "texture")));
            if (tex) m.SetTexture("_OV_FoamMap", tex);
            AssetDatabase.CreateAsset(m, p); created++;
            return m;
        }

        // Ear-clipping fill of a simple polygon; per-vertex level; UV1 = flow velocity XZ for the v05 flow mode.
        static Mesh Fill(string name, Vector2[] poly, Func<Vector2, float> level, Vector2 flow, bool save = true)
        {
            var pts = poly.ToList();
            if (Area(pts) < 0) pts.Reverse();
            var mb = new MB();
            foreach (var q in pts) { mb.V.Add(new Vector3(q.x, level(q), q.y)); mb.UV.Add(q / 10f); mb.UV1.Add(flow); }
            var idx = Enumerable.Range(0, pts.Count).ToList();
            int guard = 0;
            while (idx.Count > 3 && guard++ < 20000)
            {
                bool cut = false;
                for (int i = 0; i < idx.Count; i++)
                {
                    int a = idx[(i + idx.Count - 1) % idx.Count], b = idx[i], c = idx[(i + 1) % idx.Count];
                    if (Cross(pts[a], pts[b], pts[c]) <= 0) continue;
                    bool inside = false;
                    for (int k = 0; k < idx.Count && !inside; k++)
                    {
                        int q = idx[k];
                        if (q == a || q == b || q == c) continue;
                        inside = InTri(pts[q], pts[a], pts[b], pts[c]);
                    }
                    if (inside) continue;
                    mb.T.Add(a); mb.T.Add(c); mb.T.Add(b);
                    idx.RemoveAt(i); cut = true; break;
                }
                if (!cut) break;
            }
            if (idx.Count == 3) { mb.T.Add(idx[0]); mb.T.Add(idx[2]); mb.T.Add(idx[1]); }
            return mb.Build(name, save);
        }

        static float Area(List<Vector2> p) { float a = 0; for (int i = 0; i < p.Count; i++) { var u = p[i]; var v = p[(i + 1) % p.Count]; a += u.x * v.y - v.x * u.y; } return a * .5f; }
        static float Cross(Vector2 a, Vector2 b, Vector2 c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
        static bool InTri(Vector2 p, Vector2 a, Vector2 b, Vector2 c) => Cross(a, b, p) >= 0 && Cross(b, c, p) >= 0 && Cross(c, a, p) >= 0;

        // ------------------------------------------------------------------ northern border
        static void BuildBorder(Transform root)
        {
            // v85: the fence-netting, towers, KPP building, sliding gate and the "Leave the country" button are Rough district data
            // (scope north_border) and are built with the district. Here: the invisible wall along the border (+ past both ends) and the
            // far steppe plane (only seen).
            var bj = Obj(Json.Parse(File.ReadAllText(Data + "/border_v85.json")));
            var parent = new GameObject("Border_North").transform; parent.SetParent(root, false);
            var pl = V2s(Get(bj, "fence_line"));
            float wall = F(Get(bj, "invisible_wall_height_m"), 60f);
            var walls = new GameObject("InvisibleWall").transform; walls.SetParent(parent, false);
            var east = new List<Vector2> { pl[pl.Length - 1] };
            east.AddRange(V2s(Get(bj, "right_ridge_crest")));
            east.Add(east[east.Count - 1] + (east[east.Count - 1] - east[east.Count - 2]).normalized * 20f);
            var west = new List<Vector2> { pl[0], new Vector2(pl[0].x, Hh - 3f), new Vector2(-20f, Hh - 3f) };
            int nw = 0;
            foreach (var line in new[] { pl.ToList(), east, west })
                for (int i = 1; i < line.Count; i++)
                {
                    Vector2 a = line[i - 1], b = line[i];
                    var c = new GameObject("Wall_" + nw++).AddComponent<BoxCollider>();
                    c.transform.SetParent(walls, false);
                    float y0 = Mathf.Min(Height(a.x, a.y), Height(b.x, b.y)) - 5f;
                    c.transform.position = new Vector3((a.x + b.x) * .5f, y0 + (wall + 60f) * .5f, (a.y + b.y) * .5f);
                    c.transform.rotation = Quaternion.LookRotation(new Vector3(b.x - a.x, 0, b.y - a.y));
                    c.size = new Vector3(.5f, wall + 60f, (b - a).magnitude + .2f);
                }
            if (BackdropOn)
            {   // W86: the steppe backdrop terrain (BuildBackdrop) replaces the flat far plane
                Note($"border: invisible wall {wall} m along the border fence line ({pl.Length} pts) + {east.Count + west.Count - 2} segments past the ends; steppe = backdrop terrain; fence / KPP / towers built with the Rough district (scope north_border)");
                return;
            }
            var st = Obj(Get(bj, "steppe"));
            var steppe = GameObject.CreatePrimitive(PrimitiveType.Plane);
            steppe.name = "Steppe_far"; Object.DestroyImmediate(steppe.GetComponent<Collider>());
            steppe.transform.SetParent(parent, false);
            steppe.transform.position = new Vector3((-3000f + 1100f) * .5f, F(Get(st, "rises_to_horizon_m"), 18f) + 4f, Hh + 1500f);
            steppe.transform.localScale = new Vector3((1100f + 3000f) / 10f, 1f, 300f);
            steppe.GetComponent<MeshRenderer>().sharedMaterial = SteppeMaterial();
            Note($"border: invisible wall {wall} m along the border fence line ({pl.Length} pts) + {east.Count + west.Count - 2} segments past the ends; fence / KPP / towers built with the Rough district (scope north_border)");
        }

        static Material SteppeMaterial()
        {
            var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(S(Get(Obj(Get(MatMap, "L02_worn_grass")), "asset")) ?? "");
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W85_steppe_far", enableInstancing = true };
            if (layer && layer.diffuseTexture) { m.SetTexture("_BaseMap", layer.diffuseTexture); m.SetTextureScale("_BaseMap", new Vector2(600f, 300f)); }
            m.SetFloat("_Smoothness", 0f);
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W85_steppe_far.mat"); created++;
            return m;
        }

        static GameObject Box(Transform parent, string name, Vector3 centre, Vector3 size, float yawDeg, string mat, bool collider)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name; go.transform.SetParent(parent, false);
            go.transform.position = centre; go.transform.rotation = Quaternion.Euler(0, yawDeg, 0); go.transform.localScale = size;
            go.GetComponent<MeshRenderer>().sharedMaterial = Mat(mat);
            if (!collider) Object.DestroyImmediate(go.GetComponent<Collider>());
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            return go;
        }

        // ------------------------------------------------------------------ facade kit (FACADE_KIT_v01, merged from claude/facade-kit-v01)
        static readonly Dictionary<string, GameObject> Kit = new();

        static void ImportKit()
        {
            Kit.Clear(); KitMats.Clear();
            if (!Directory.Exists(KitSrc)) { Note("facade kit missing: " + KitSrc); return; }
            foreach (string f in Directory.GetFiles(KitSrc, "*.fbx"))
            {
                string dst = Gen + "/FacadeKit/" + Path.GetFileName(f);
                if (new FileInfo(f).Length < 1024) { Note("kit file is an LFS pointer (run git lfs pull): " + f); continue; }
                File.Copy(f, dst, true);
                AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceSynchronousImport);
                var mi = AssetImporter.GetAtPath(dst) as ModelImporter;
                if (mi)
                {
                    mi.globalScale = 1f; mi.importAnimation = false; mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                    // one shared material per kit material name (FK_Concrete, FK_Metal_Dark, ...) instead of a copy per FBX
                    foreach (var em in AssetDatabase.LoadAllAssetsAtPath(dst).OfType<Material>())
                        mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), em.name), KitMaterial(em));
                    mi.SaveAndReimport();
                }
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(dst);
                if (go) Kit[Path.GetFileNameWithoutExtension(f)] = go;
            }
            Note($"facade kit: {Kit.Count} pieces imported, {KitMats.Count} shared kit materials");
        }

        static readonly Dictionary<string, Material> KitMats = new();

        // Kit placeholder material (FACADE_KIT_v01 README: one placeholder per kind, real textures later): URP Lit, kit colour.
        static Material KitMaterial(Material embedded)
        {
            if (KitMats.TryGetValue(embedded.name, out Material m) && m) return m;
            string path = Gen + "/FacadeKit/Materials/" + Safe(embedded.name) + ".mat";
            Folder(Gen + "/FacadeKit/Materials");
            m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m)
            {
                Color c = embedded.HasProperty("_BaseColor") ? embedded.GetColor("_BaseColor") : embedded.HasProperty("_Color") ? embedded.color : Color.grey;
                m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = embedded.name, enableInstancing = true };
                m.SetColor("_BaseColor", c);
                m.SetFloat("_Smoothness", embedded.name.Contains("Glass") ? .8f : .15f);
                if (embedded.name.Contains("Metal")) m.SetFloat("_Metallic", .4f);
                AssetDatabase.CreateAsset(m, path);
                created++;
            }
            return KitMats[embedded.name] = m;
        }

        // Instance a kit piece; UCX_ children -> convex MeshCollider on the piece, UCX renderer removed (ROOF_COLLISION_NOTE).
        static GameObject Piece(string name, Transform parent, Vector3 pos, Vector3 outward)
        {
            if (!Kit.TryGetValue(name, out GameObject src)) return null;
            // plain copy (no prefab link): children of a prefab instance cannot be destroyed / stripped
            var go = Object.Instantiate(src, parent);
            go.name = name;
            go.transform.position = pos;
            go.transform.rotation = Quaternion.LookRotation(outward, Vector3.up);
            // UCX_ child keeps its own transform (FBX axis conversion): collider on the child, its renderer removed
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true).Where(m => m.name.StartsWith("UCX_")).ToList())
            {
                var ucx = mf.gameObject;
                var mesh = mf.sharedMesh;
                Object.DestroyImmediate(ucx.GetComponent<MeshRenderer>());
                Object.DestroyImmediate(mf);
                var mc = ucx.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true;
            }
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            return go;
        }

        // ------------------------------------------------------------------ districts
        static void BuildDistrict(Transform root, string file)
        {
            var dj = Obj(Json.Parse(File.ReadAllText(file)));
            string district = S(Get(dj, "district"), Path.GetFileNameWithoutExtension(file));
            var parent = new GameObject("District_" + district).transform; parent.SetParent(root, false);
            poolParent = parent;
            int nb = 0, np = 0, nz = 0;
            foreach (object o in Arr(Get(dj, "zones"))) if (Zone(parent, Obj(o))) nz++;
            RolloutDistrict(dj);
            foreach (object o in Arr(Get(dj, "buildings")))
            {
                var bo = Obj(o);
                if (Get(bo, "disabled") is bool off && off) continue;
                string bid = S(Get(bo, "id"), "");
                if (SampleSkip.Contains(bid)) continue;                                 // replaced by the texture sample
                if (SampleCutX.TryGetValue(bid, out var keep))
                {   // the texture sample takes one section of this house: keep the rest (footprint clamped, doors of the kept part only)
                    bo = new Dictionary<string, object>(bo);
                    bo["footprint"] = CutFootprint(bid, V2s(Get(bo, "footprint")).ToList()).Select(q => (object)new List<object> { (double)q.x, (double)q.y }).ToList();
                    bo["entrances"] = Arr(Get(bo, "entrances")).Where(e => { var q = V2(Get(Obj(e), "pos")); return q.x >= keep.x - .1f && q.x <= keep.y + .1f; }).ToList();
                }
                if (Building(parent, bo, district)) nb++;
            }
            var props = Arr(Get(dj, "props")).Select(Obj).Where(o => o != null && !(Get(o, "disabled") is bool off && off)).ToList();
            var towers = props.Where(o => S(Get(o, "kind")) == "lifeguard_tower").ToList();
            if (towers.Count > LifeguardTowers)
            {   // Q4: keep the tower nearest to each van entry and to the pier (handoff v02 §8.9: <= 2; map v45: 6)
                var keep = new List<Dictionary<string, object>>();
                foreach (float x in new[] { 895f, 1142f, 1032f, 960f, 1090f, 1200f })
                {
                    if (keep.Count >= LifeguardTowers) break;
                    var t = towers.Where(o => !keep.Contains(o)).OrderBy(o => Mathf.Abs(V2(Get(o, "pos")).x - x)).FirstOrDefault();
                    if (t != null) keep.Add(t);
                }
                props.RemoveAll(o => towers.Contains(o) && !keep.Contains(o));
            }
            foreach (var o in props) { if (Prop(parent, o)) np++; }
            string extras = Extras(parent, dj, district);
            FlushPropBatches(parent);
            Note($"{district}: {nb} buildings, {np} props, {nz} zone surfaces{extras}");
        }

        // ------------------------------------------------------------------ district extras (v85 data)
        // Downtown streets 12 + 2 x 5 m with kerbs, junction corners and curb drops at entries; fences / border fences with gates as gaps;
        // walls; district roads (internal legs, Elite inner ring / gate road with absolute heights); piers, boardwalks, pools, alley
        // plugs, gate trap / missile markers, football box fence, bollards, Elite hedges. Data only; nothing new is invented.
        static string Extras(Transform parent, Dictionary<string, object> dj, string district)
        {
            var zones = Arr(Get(dj, "zones")).Select(Obj).Where(z => z != null).ToList();
            var sb = new StringBuilder();
            var streets = zones.Where(z => S(Get(z, "kind")) == "street" && Get(z, "carriageway_m") != null && Arr(Get(z, "poly_line")).Count >= 2).ToList();
            if (streets.Count > 0)
            {
                var drops = zones.Where(z => S(Get(z, "kind")) == "curb_drop").Select(z => V2s(Get(z, "poly"))).Where(p => p.Length >= 3).ToList();
                var junctions = zones.Where(z => S(Get(z, "kind")) == "junction").ToList();
                sb.Append($", {Streets(parent, streets, drops, junctions)} street meshes (carriageway + 5 m sidewalks, kerbs, corners, {drops.Count} curb drops)");
            }
            // gates of this district (gaps in its fences)
            var gates = new List<(Vector2 c, float w)>();
            foreach (var z in zones)
            {
                string k = S(Get(z, "kind"), "");
                if (k == "gate" || k == "gate_trap")
                {
                    if (Get(z, "pos") != null) gates.Add((V2(Get(z, "pos")), F(Get(z, "w_m"), 6f) + .4f));
                    else { var pp = V2s(Get(z, "poly")); if (pp.Length >= 3) gates.Add((pp.Aggregate(Vector2.zero, (a, b) => a + b) / pp.Length, F(Get(z, "w_m"), 6f) + .4f)); }
                }
                if (k == "gates") foreach (var g in Arr(Get(z, "items")).Select(Obj))
                    {
                        var c0 = Get(g, "centre") ?? Get(g, "pos") ?? Get(g, "centre_world");
                        if (c0 != null) gates.Add((V2(c0), F(Get(g, "w_m") ?? Get(g, "width_m"), 6f) + .4f));
                    }
            }
            int fences = 0, piers = 0, plugs = 0, roads = 0, walls = 0, hedges = 0;
            foreach (var z in zones)
            {
                string kind = S(Get(z, "kind"), ""), id = S(Get(z, "id"), kind);
                var line = V2s(Get(z, "line") ?? Get(z, "poly_line") ?? Get(z, "polyline"));
                if (W86Zone(parent, z, kind, id, line, district, zones)) continue;       // W86: side gaps, patrol loops, planter strips
                if (kind == "fence" || kind == "border_fence")
                {
                    var pl = line.Length >= 2 ? line : V2s(Get(z, "poly"));
                    bool closed = Get(z, "closed") is bool cl && cl || (line.Length < 2 && pl.Length >= 3);
                    var g = new List<(Vector2 c, float w)>(gates);
                    foreach (var gg in Arr(Get(z, "gates")).Select(Obj)) g.Add((V2(Get(gg, "centre")), F(Get(gg, "width_m"), 6f) + .4f));
                    var bt = Obj(Get(z, "gate"));
                    if (bt != null) { var bw = V2s(Get(bt, "between")); if (bw.Length == 2) g.Add(((bw[0] + bw[1]) * .5f, (bw[0] - bw[1]).magnitude + .4f)); }
                    string mat = S(Get(z, "surface")) ?? S(Get(z, "material"));
                    if (mat == null || Get(MatMap, mat) == null) mat = district.Contains("elite") || district.Contains("rough") ? "concrete_panel_SK3c" : district.Contains("valley") ? "boards_SK5a" : "metal_painted_SK6a";
                    bool net = mat == "fence_net";
                    Fence(parent, id, pl, closed, F(Get(z, "height_m"), 2f), mat, g, net, S(Get(z, "tint")));
                    AfterFence(parent, id, pl, closed, F(Get(z, "height_m"), 2f), g, district, mat);
                    fences++;
                }
                else if (kind == "wall" && line.Length >= 2)
                {
                    for (int i = 1; i < line.Length; i++)
                    {
                        Vector2 a = line[i - 1], b = line[i], m = (a + b) * .5f;
                        float h = F(Get(z, "h_m"), 3f), y0 = Mathf.Min(Height(a.x, a.y), Height(b.x, b.y)) - .2f;
                        Box(parent, "Wall_" + id + "_" + i, new Vector3(m.x, y0 + h * .5f, m.y), new Vector3((b - a).magnitude, h, F(Get(z, "w_m"), .4f)), -Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg, S(Get(z, "material"), "brick_SK3a"), true);
                    }
                    walls++;
                }
                else if ((kind == "road" || kind == "ring_road") && line.Length >= 2 && !(Get(z, "world_road") is bool wr && wr))
                {
                    if (OnWorldRoad(line)) continue;                               // already built from roads_v85.json
                    var pts = ResamplePy(line, 2f);
                    var habs = Arr(Get(z, "h_abs")).Select(x => F(x)).ToArray();
                    Func<int, float> hAt = null;
                    if (habs.Length >= 2) hAt = i => habs[Mathf.Clamp(Mathf.RoundToInt(i / (float)Mathf.Max(1, pts.Count - 1) * (habs.Length - 1)), 0, habs.Length - 1)];
                    string surf = S(Get(z, "surface"), "asphalt_A5d12");
                    if (Get(MatMap, surf) == null) surf = "asphalt_A5d12";
                    float w = F(Get(z, "width_m"), 6.4f);
                    MeshGo("Road_" + id, parent, RibbonPts("Road_" + id, pts, w, Tile(surf), .07f, hAt), Mat(surf), true);
                    roads++;
                }
                else if (kind == "dead_end_alley_pair" || kind == "dead_end_alley")
                {
                    var pw = V2s(Get(z, "plug_wall"));
                    if (pw.Length >= 3)
                    {
                        Frame(pw.ToList(), new Dictionary<string, object>(), out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
                        float baseY = pw.Min(q => Height(q.x, q.y)) - .2f;
                        var plugGo = Box(parent, "AlleyPlug_" + id, new Vector3(c.x, baseY + 4.5f, c.y), new Vector3(2 * hx, 9f, 2 * hy), -Mathf.Atan2(ax.y, ax.x) * Mathf.Rad2Deg, "brick_SK3a", true);
                        AlleyPlugT67(plugGo, pw.ToList(), id, V2s(Get(z, "poly")));
                        plugs++;
                    }
                    var poly = V2s(Get(z, "poly"));
                    if (poly.Length >= 3) FlatPatch(parent, "Alley_" + id, poly, "asphalt_old_SK2a", .05f);
                }
                else if (kind == "pier") { Pier(parent, id, V2s(Get(z, "poly")), S(Get(z, "surface"), "boards_pier_SK5a_v02")); piers++; }
                else if (kind == "gate_trap" || kind == "trigger")
                {
                    var tm = new GameObject((kind == "gate_trap" ? "EliteGateTrap_" : "Trigger_") + id).AddComponent<W76TrapMarker>();
                    tm.transform.SetParent(parent, false);
                    var pos = Get(z, "pos") != null ? V2(Get(z, "pos")) : V2s(Get(z, "poly")).Aggregate(Vector2.zero, (a, b) => a + b) / Mathf.Max(1, V2s(Get(z, "poly")).Length);
                    tm.transform.position = P(pos, .5f);
                    tm.Kind = kind == "gate_trap" ? "elite_gate_latch" : "tramduro_missiles"; tm.Seconds = EliteGateSeconds; tm.GuardSeconds = EliteGuardSeconds;
                }
                else if (kind == "boardwalk" && line.Length >= 2)
                    MeshGo("Boardwalk_" + id, parent, Ribbon("Boardwalk_" + id, line, F(Get(z, "width_m"), 3f), Tile("boards_pier_SK5a_v02"), .12f), Mat("boards_pier_SK5a_v02"));
                else if (kind == "football_box")
                {
                    var poly = V2s(Get(z, "poly"));
                    var fz = Obj(Get(z, "fence"));
                    var wk = Obj(Get(z, "wicket"));
                    var gaps = wk != null ? new List<(Vector2 c, float w)> { (V2(Get(wk, "pos")), F(Get(wk, "w_m"), 6f)) } : null;
                    Fence(parent, id + "_board", poly, true, F(Get(fz, "board_h_m"), 1f), "boards_SK5a", gaps, false, null);
                    Fence(parent, id + "_net", poly, true, F(Get(fz, "net_h_m"), 4.5f), "fence_net", gaps, true, null);
                    AfterFence(parent, id + "_board", poly, true, F(Get(fz, "board_h_m"), 1f), gaps, district, "boards_SK5a");
                    AfterFence(parent, id + "_net", poly, true, F(Get(fz, "net_h_m"), 4.5f), gaps, district, "fence_net");
                    fences++;
                }
                else if (kind == "villa_plot")
                {
                    var hd = Obj(Get(z, "hedge"));
                    var hl = V2s(Get(hd, "line"));
                    var gp = Obj(Get(z, "gate"));
                    for (int i = 1; i < hl.Length; i++)
                    {
                        Vector2 a = hl[i - 1], b = hl[i];
                        int k2 = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 3f));
                        for (int j = 0; j < k2; j++)
                        {
                            Vector2 p0 = Vector2.Lerp(a, b, j / (float)k2), p1 = Vector2.Lerp(a, b, (j + 1) / (float)k2), m = (p0 + p1) * .5f;
                            if (gp != null && (V2(Get(gp, "pos")) - m).magnitude < F(Get(gp, "w_m"), 5f) * .5f + .3f) continue;
                            float hh = F(Get(hd, "h_m"), 1.8f);
                            var hb = Box(parent, "Hedge_" + id, new Vector3(m.x, Height(m.x, m.y) + hh * .5f - .1f, m.y), new Vector3((p1 - p0).magnitude + .05f, hh, F(Get(hd, "w_m"), .9f)), -Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg, "lawn_hedge", true);
                        }
                    }
                    HedgeT97(parent, z, id);
                    hedges++;
                }
                else if (kind == "bollard_row" && line.Length >= 2)
                {
                    if (district.Contains("downtown")) DcBollards(parent, id, line, !(Get(z, "grip_anchor") is bool gb && !gb));
                    else foreach (var q in Resample(line, 1.6f)) Box(parent, "Bollard", P(q, .45f), new Vector3(.22f, .9f, .22f), 0f, "metal_painted_SK6a", true);
                }
                else if (kind == "pool")
                {
                    var poly = V2s(Get(z, "poly"));
                    if (poly.Length < 3) continue;
                    float baseH = poly.Average(q => Height(q.x, q.y));
                    bool basin = district.Contains("elite");                         // Elite: tiled basin; Downtown: 0.3 m mirror pool the van drives into
                    float lv = basin ? baseH - .08f : baseH + .3f;
                    if (basin) { float pl = ElitePoolLevel(z, zones, out bool pok); if (pok) lv = pl; }
                    var wm = Fill("Pool_" + id, poly, q => lv, Vector2.zero);
                    var go = MeshGo("Water_Pool_" + id, parent, wm, PoolWater());
                    go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
                    AddWaterArea(id, Audio.WaterKind.Pool, wm, false);
                    if (!basin)
                    {
                        var rim = new MB();
                        for (int i = 0; i < poly.Length; i++)
                        {
                            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
                            rim.QuadBoth(new Vector3(a.x, baseH, a.y), new Vector3(a.x, baseH + .34f, a.y), new Vector3(b.x, baseH + .34f, b.y), new Vector3(b.x, baseH, b.y),
                                Vector2.zero, new Vector2(0, .34f), new Vector2((b - a).magnitude, .34f), new Vector2((b - a).magnitude, 0));
                        }
                        MeshGo("PoolRim_" + id, parent, rim.Build("PoolRim_" + id), Mat("plaza_M3"));
                        if (district.Contains("downtown")) DcPool(parent, id, poly, V2s(Get(z, "edge_poly")), baseH);
                    }
                }
            }
            if (district.Contains("downtown"))
                foreach (var z in zones.Where(z => S(Get(z, "kind")) == "plaza" && (S(Get(z, "id"), "") ?? "").Contains("05-04")))
                    DcPlazaBand(parent, V2s(Get(z, "poly")));
            sb.Append($", {fences} fences, {walls} walls, {roads} district roads, {piers} piers, {plugs} alley plugs, {hedges} hedged plots");
            sb.Append(W86ExtrasNote());
            return sb.ToString();
        }

        static bool OnWorldRoad(Vector2[] line)
        {
            foreach (var (id, pl, w, kind) in WorldRoads)
            {
                if (kind == "tunnel") continue;
                var arr = pl;
                bool a = W76Atmosphere.Distance(arr, line[0]) < 3f, b = W76Atmosphere.Distance(arr, line[line.Length - 1]) < 3f;
                bool m = W76Atmosphere.Distance(arr, line[line.Length / 2]) < 3f;
                if (a && b && m) return true;
            }
            return false;
        }

        static Material poolWater;
        static Material PoolWater()
        {
            if (poolWater) return poolWater;
            var flow = AssetDatabase.LoadAssetAtPath<Material>(Gen + "/Materials/W85_water_flow.mat");
            poolWater = flow ? flow : Mat("water_sea");
            return poolWater;
        }

        static void FlatPatch(Transform parent, string name, Vector2[] poly, string surf, float lift)
        {
            float baseH = poly.Average(q => Height(q.x, q.y));
            var mesh = Fill(name, poly, q => baseH + lift, Vector2.zero);
            float t = Tile(surf);
            mesh.uv = mesh.vertices.Select(v => new Vector2(v.x, v.z) / t).ToArray();
            EditorUtility.SetDirty(mesh);
            MeshGo(name, parent, mesh, Mat(surf));
        }

        // Downtown streets (v10 §6: 12 m carriageway + 5 m sidewalks = 22 m between facades): asphalt carriageway + raised sidewalks with
        // a 15 cm kerb; sidewalks stop where they would cross another street's carriageway, at curb drops (entries, van gates) and where a
        // world road enters (the road continues as carriageway); junction corners get a sidewalk square so the walkway is continuous.
        static int Streets(Transform parent, List<Dictionary<string, object>> streets, List<Vector2[]> drops, List<Dictionary<string, object>> junctions)
        {
            var root = new GameObject("Streets").transform; root.SetParent(parent, false);
            var lines = streets.Select(z => (z, pl: Extend(V2s(Get(z, "poly_line")), CarriagewayOf(z) * .5f))).ToList();
            float sw = DowntownSidewalk, curb = .15f;
            string side = "sidewalk_S1";
            float st = Tile(side);
            bool Blocked(Dictionary<string, object> self, Vector2 q)
            {
                if (lines.Any(o => !ReferenceEquals(o.z, self) && W76Atmosphere.Distance(o.pl, q) < CarriagewayOf(o.z) * .5f + .3f)) return true;
                // W86 (Fedya 25.10, screenshots 08/09): curb drops (vehicle crossings) no longer cut the walk: paving runs on, the kerb is lowered
                foreach (var (id, pl, w, kind) in WorldRoads)
                    if (kind != "tunnel" && kind != "dirt" && kind != "sand_track" && W76Atmosphere.Distance(pl, q) < w * .5f + .4f) return true;
                return false;
            }
            int n = 0, li = 0;
            foreach (var (z, pl) in lines)
            {
                string id = S(Get(z, "id"), "street");
                float cw = CarriagewayOf(z);
                string surf = S(Get(z, "surface"), "asphalt_A5d12");
                MeshGo("Street_" + id, root, Ribbon("Street_" + id, pl, cw, Tile(surf), .06f + .003f * (li++ % 6)), Mat(surf), true);
                var pts = Resample(pl, 1f);
                foreach (int sgn in new[] { 1, -1 })
                {
                    var mb = new MB();
                    Vector2? prevIn = null, prevOut = null; float acc = 0f;
                    for (int i = 0; i < pts.Count; i++)
                    {
                        Vector2 dir = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[Mathf.Max(i - 1, 0)]).normalized, nrm = new Vector2(-dir.y, dir.x) * sgn;
                        Vector2 pin = pts[i] + nrm * cw * .5f, pout = pts[i] + nrm * (cw * .5f + sw), mid = (pin + pout) * .5f;
                        bool blocked = Blocked(z, mid) || Blocked(z, pin + nrm * .4f);
                        if (blocked || prevIn == null) { prevIn = blocked ? (Vector2?)null : pin; prevOut = blocked ? (Vector2?)null : pout; continue; }
                        bool lowered = drops.Any(d => W76Atmosphere.Inside(d, mid) || W76Atmosphere.Distance(d.Append(d[0]).ToArray(), mid) < .6f);
                        float y = Height(pts[i].x, pts[i].y) + .06f + (lowered ? .025f : curb); // dropped kerb at a crossing
                        Vector3 a0 = new(prevIn.Value.x, y, prevIn.Value.y), a1 = new(prevOut.Value.x, y, prevOut.Value.y), b0 = new(pin.x, y, pin.y), b1 = new(pout.x, y, pout.y);
                        float u0 = acc / st, u1 = (acc + 1f) / st; acc += 1f;
                        if (sgn > 0) mb.Quad(a1, b1, b0, a0, new Vector2(sw / st, u0), new Vector2(sw / st, u1), new Vector2(0, u1), new Vector2(0, u0));
                        else mb.Quad(a0, b0, b1, a1, new Vector2(0, u0), new Vector2(0, u1), new Vector2(sw / st, u1), new Vector2(sw / st, u0));
                        Vector3 down = Vector3.down * (curb + .1f);
                        mb.QuadBoth(a0 + down, b0 + down, b0, a0, Vector2.zero, new Vector2(1f / st, 0), new Vector2(1f / st, .1f), new Vector2(0, .1f));
                        prevIn = pin; prevOut = pout;
                    }
                    if (mb.V.Count == 0) continue;
                    string nm = "Sidewalk_" + id + (sgn > 0 ? "_L" : "_R");
                    MeshGo(nm, root, mb.Build(nm), Mat(side), true);
                    n++;
                }
                n++;
            }
            // junction corners: sidewalk squares in every quadrant that is not carriageway (continuous walkway around the block corner)
            var corner = new MB();
            foreach (var j in junctions)
            {
                Vector2 c = V2(Get(j, "pos"));
                // W86: the corner square starts at the real kerb line (the widest carriageway meeting here), not a fixed 6 m: wide
                // streets left a grass strip between the two walks at every corner
                float h = 6f;
                foreach (var o in lines) if (W76Atmosphere.Distance(o.pl, c) < CarriagewayOf(o.z) * .5f + 1f) h = Mathf.Max(h, CarriagewayOf(o.z) * .5f);
                foreach (var sx in new[] { -1f, 1f })
                    foreach (var sy in new[] { -1f, 1f })
                    {
                        Vector2 q0 = c + new Vector2(sx * h, sy * h), q1 = c + new Vector2(sx * (h + sw), sy * (h + sw)), m = (q0 + q1) * .5f;
                        if (lines.Any(o => W76Atmosphere.Distance(o.pl, m) < CarriagewayOf(o.z) * .5f + .2f)) continue;
                        if (drops.Any(d => W76Atmosphere.Inside(d, m))) continue;
                        float y = Height(m.x, m.y) + .06f + curb;
                        Vector2 lo = Vector2.Min(q0, q1), hi = Vector2.Max(q0, q1);
                        corner.Quad(new Vector3(lo.x, y, lo.y), new Vector3(lo.x, y, hi.y), new Vector3(hi.x, y, hi.y), new Vector3(hi.x, y, lo.y),
                            new Vector2(lo.x, lo.y) / st, new Vector2(lo.x, hi.y) / st, new Vector2(hi.x, hi.y) / st, new Vector2(hi.x, lo.y) / st);
                    }
            }
            if (corner.V.Count > 0) { MeshGo("Sidewalk_corners", root, corner.Build("Sidewalk_corners"), Mat(side), true); n++; }
            return n;
        }

        static float CarriagewayOf(Dictionary<string, object> z) => DowntownCarriageway > 0f ? DowntownCarriageway : F(Get(z, "carriageway_m"), 12f);

        static Vector2[] Extend(Vector2[] pl, float by)
        {
            if (pl.Length < 2) return pl;
            var o = pl.ToArray();
            o[0] = pl[0] + (pl[0] - pl[1]).normalized * by;
            o[o.Length - 1] = pl[pl.Length - 1] + (pl[pl.Length - 1] - pl[pl.Length - 2]).normalized * by;
            return o;
        }

        // Fence: 2 m panels on the ground, double-sided, a thin box collider per panel; gates = gaps (centre, width); optional tint.
        static void Fence(Transform parent, string id, Vector2[] line, bool closed, float h, string mat, List<(Vector2 c, float w)> gaps, bool net, string tint)
        {
            if (line.Length < 2) return;
            var pts = line.ToList(); if (closed) pts.Add(line[0]);
            var mb = new MB();
            var col = new GameObject("Fence_" + id).transform; col.SetParent(parent, false);
            float t = net ? 1f : Tile(mat);
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], b = pts[i];
                int k = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 2f));
                for (int j = 0; j < k; j++)
                {
                    Vector2 p0 = Vector2.Lerp(a, b, j / (float)k), p1 = Vector2.Lerp(a, b, (j + 1) / (float)k), m = (p0 + p1) * .5f;
                    if (gaps != null && gaps.Any(g => (g.c - m).magnitude < g.w * .5f)) continue;
                    float y0 = Height(p0.x, p0.y) - .3f, y1 = Height(p1.x, p1.y) - .3f, L = (p1 - p0).magnitude;
                    mb.QuadBoth(new Vector3(p0.x, y0, p0.y), new Vector3(p0.x, y0 + h + .3f, p0.y), new Vector3(p1.x, y1 + h + .3f, p1.y), new Vector3(p1.x, y1, p1.y),
                        Vector2.zero, new Vector2(0, (h + .3f) / t), new Vector2(L / t, (h + .3f) / t), new Vector2(L / t, 0));
                    var bc = new GameObject("p").AddComponent<BoxCollider>();
                    bc.transform.SetParent(col, false);
                    bc.transform.position = new Vector3(m.x, (y0 + y1) * .5f + (h + .3f) * .5f, m.y);
                    bc.transform.rotation = Quaternion.LookRotation(new Vector3(p1.x - p0.x, 0, p1.y - p0.y));
                    bc.size = new Vector3(.2f, h + .3f, L + .05f);
                }
            }
            if (mb.V.Count == 0) return;
            var go = MeshGo("FenceMesh_" + id, col, mb.Build("Fence_" + id), Mat(mat));
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.TwoSided;
            if (!string.IsNullOrEmpty(tint) && ColorUtility.TryParseHtmlString(tint, out Color tc))
            {
                var mpb = new MaterialPropertyBlock(); mpb.SetColor("_BaseColor", tc);
                go.GetComponent<MeshRenderer>().SetPropertyBlock(mpb);
            }
        }

        // Pier / jetty deck: boards 1.2 m over the sea (follows the sand where it starts on the beach), 0.4 m skirt, walkable.
        static void Pier(Transform parent, string id, Vector2[] poly, string mat)
        {
            if (poly.Length < 3) return;
            Func<Vector2, float> lv = q => Mathf.Max(1.2f, Height(q.x, q.y) + .15f);
            var deck = Fill("Pier_" + id, poly, lv, Vector2.zero);
            float t = Tile(mat);
            deck.uv = deck.vertices.Select(v => new Vector2(v.x, v.z) / t).ToArray();
            EditorUtility.SetDirty(deck);
            MeshGo("Pier_" + id, parent, deck, Mat(mat), true);
            var sk = new MB();
            for (int i = 0; i < poly.Length; i++)
            {
                Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
                float ya = lv(a), yb = lv(b);
                sk.QuadBoth(new Vector3(a.x, ya - .4f, a.y), new Vector3(a.x, ya, a.y), new Vector3(b.x, yb, b.y), new Vector3(b.x, yb - .4f, b.y), Vector2.zero, new Vector2(0, .4f), new Vector2(1, .4f), new Vector2(1, 0));
            }
            MeshGo("PierSkirt_" + id, parent, sk.Build("PierSkirt_" + id), Mat(mat));
        }

        static readonly HashSet<string> FlatZones = new() { "plaza", "pool", "playground", "parking", "yard", "sidewalk", "pitch", "court", "deck", "helipad", "terrace", "lot", "trash", "base_yard", "courtyard", "loading_pad", "apron", "taxi_stand", "gas_station", "fuel_pad", "fishing_platform", "materials_store", "driveway" };

        static bool Zone(Transform parent, Dictionary<string, object> z)
        {
            string kind = (S(Get(z, "kind"), "") ?? "").ToLowerInvariant(), surf = S(Get(z, "surface"));
            var poly = V2s(Get(z, "poly"));
            if (poly.Length < 3 || surf == null || Get(MatMap, surf) == null) return false;
            if (!FlatZones.Any(k => kind.Contains(k))) return false;
            if (parent.name.Contains("elite") && (kind == "pool" || kind == "pool_deck") && T2Available()) return false;   // T98: generated basin + deck
            float lift = kind.Contains("pool") ? -.25f : .04f;
            float baseH = poly.Average(q => Height(q.x, q.y));
            if (kind.Contains("fishing") || kind.Contains("dock")) baseH = Mathf.Max(baseH, RiverLevelNear(poly, 8f) + F(Get(z, "deck_h_m"), .4f) - lift);   // W86: over the water, never under it
            var mesh = Fill("Zone_" + S(Get(z, "id"), kind), poly, q => baseH + lift, Vector2.zero);
            float zt = Tile(surf);
            mesh.uv = mesh.vertices.Select(v => new Vector2(v.x, v.z) / zt).ToArray();
            EditorUtility.SetDirty(mesh);
            MeshGo("Zone_" + S(Get(z, "id"), kind), parent, mesh, Mat(surf), true);
            return true;
        }

        static string DefaultWalls(string kind, string district) =>
            district.Contains("rough") && (kind.Contains("khrush") || kind.Contains("panel")) ? "KH1b" :
            district.Contains("downtown") ? (kind.Contains("tower") || kind.Contains("glass") || kind.Contains("pavilion") ? "tower_glass" : "facade_downtown_stucco") :
            district.Contains("hamlet") ? "facade_hamlet" : district.Contains("elite") ? "facade_elite_villa" :
            district.Contains("port") ? "facade_warehouse" : district.Contains("tramduro") || district.Contains("construction") ? "concrete_panel_SK3c" : "stucco_SK3b";

        // material per building type (slot) + the isolated texture sample (Data/v01/texture_sample_v85.json: building id -> test material)
        static string curSlot, curId;
        static Dictionary<string, object> Sample;
        static Material SampleMat(string part)
        {
            var rec = Obj(Get(Obj(Get(Sample, "buildings")), curId ?? ""));
            string path = S(Get(rec, part));
            return path != null ? AssetDatabase.LoadAssetAtPath<Material>(path) : null;
        }
        static Material WallMat(string key) => SampleMat("walls") ?? (curSlot != null ? SlotMat(curSlot, "walls", key) : Mat(key));
        static Material RoofMat(string key) => SampleMat("roof") ?? (curSlot != null ? SlotMat(curSlot, "roof", key) : Mat(key));

        static bool Building(Transform parent, Dictionary<string, object> b, string district)
        {
            var fp = V2s(Get(b, "footprint")).ToList();
            if (fp.Count < 3) return false;
            if (Area(fp) < 0) fp.Reverse();
            string id = S(Get(b, "id"), "b"), kind = (S(Get(b, "kind"), "") ?? "").ToLowerInvariant();
            if (W86BeforeBuilding(parent, b, district, kind, fp, id)) return true;     // W86 integration: wagon model, bus stop, hay shelter
            if (W86Building(parent, b, district, kind, fp, id)) return true;            // W86: fuel canopy (columns, no walls)
            if (TryRollout(parent, b, district, kind, fp, id)) return true;
            float height = F(Get(b, "height_m"), 0f);
            int floors = (int)F(Get(b, "floors"), 1f);
            float floorH = F(Get(b, "floor_h_m"), district.Contains("downtown") ? 3.5f : 2.8f);
            if (height <= 0f) height = Mathf.Max(2.5f, floors * floorH);
            string walls = S(Get(b, "walls")) ?? DefaultWalls(kind, district);
            curSlot = SlotFor(district, kind, S(Get(b, "material_slot"))); curId = id;
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object>();
            string roofType = S(Get(roof, "type"), "flat"), roofMat = S(Get(roof, "material")) ?? (roofType == "flat" ? "roof_flat_SK4d" : "roof_tile_SK4a");
            float baseY = fp.Min(q => Height(q.x, q.y)) - .25f;                   // foundations sink, nothing floats
            var go = new GameObject("B_" + id); go.transform.SetParent(parent, false);
            var details = new GameObject("details").transform; details.SetParent(go.transform, false);
            // tint: one material per texture; colour per house via property block (handoff: colour = material parameter)
            string tint = ClearTint(curSlot) ? null : S(Get(b, "tint"));                 // W86: the retextured slots carry their colour in the texture
            // arches: rectangular footprints only — passage across the depth, opening = the data's clear width / height (W86: 6 x 4.5 m)
            var arches = ArchesOf(b, fp);
            float wallTile = Tile(walls);
            var body = new MB();
            float top = baseY + height;
            for (int i = 0; i < fp.Count; i++)
            {
                Vector2 a = fp[i], c = fp[(i + 1) % fp.Count];
                float L = (c - a).magnitude;
                if (L < .05f) continue;
                Vector2 d = (c - a) / L;
                var cuts = new List<(float s, float w, float h)>();
                foreach (var ar in arches)
                {
                    if (Mathf.Abs(Vector2.Dot(d, ar.Axis)) > .5f) continue;            // a wall along the passage is not cut
                    float s = Vector2.Dot(ar.P - a, d), off = Mathf.Abs(Cross(a, c, ar.P)) / L;
                    if (s > .3f && s < L - .3f && off < 30f) cuts.Add((s, ar.W, ar.H));
                }
                float u = 0f;
                foreach (var seg in Segments(L, cuts))
                {
                    Vector2 p0 = a + d * seg.s0, p1 = a + d * seg.s1;
                    float y0 = seg.h > 0f ? baseY + seg.h : baseY;
                    body.Quad(new Vector3(p0.x, y0, p0.y), new Vector3(p0.x, top, p0.y), new Vector3(p1.x, top, p1.y), new Vector3(p1.x, y0, p1.y),
                        new Vector2((u + seg.s0) / wallTile, (y0 - baseY) / wallTile), new Vector2((u + seg.s0) / wallTile, height / wallTile),
                        new Vector2((u + seg.s1) / wallTile, height / wallTile), new Vector2((u + seg.s1) / wallTile, (y0 - baseY) / wallTile));
                }
            }
            var bodyMesh = body.Build("B_" + id + "_walls");
            var wallGo = MeshGo("walls", go.transform, bodyMesh, WallMat(walls));
            if (!string.IsNullOrEmpty(tint) && ColorUtility.TryParseHtmlString(tint, out Color col))
            {
                var mpb = new MaterialPropertyBlock(); mpb.SetColor("_BaseColor", col);
                wallGo.GetComponent<MeshRenderer>().SetPropertyBlock(mpb);
            }
            Roof(go.transform, id, fp, top, roofType, roof, roofMat, walls);
            Colliders(go.transform, id, fp, baseY, top, roofType, roof, arches);
            Built.Add(new BInfo { Go = go, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = roofType, Roof = roof });
            Sockets(details, b, fp, baseY, top, floors, floorH, district);
            // LOD: details off at distance (kit pieces), body + roof always
            // kit pieces with their own LODGroup (window shutters) keep it: a renderer may belong to one LODGroup only (console warnings)
            var nestedR = new HashSet<Renderer>(go.GetComponentsInChildren<LODGroup>(true).SelectMany(g => g.GetLODs().SelectMany(l => l.renderers)).Where(r => r));
            var lod = go.AddComponent<LODGroup>();
            var all = go.GetComponentsInChildren<Renderer>().Where(r => !nestedR.Contains(r)).ToArray();
            var detailR = details.GetComponentsInChildren<Renderer>();
            lod.SetLODs(new[] { new LOD(.06f, all), new LOD(.01f, all.Except(detailR).ToArray()) });
            lod.RecalculateBounds();
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            W86AfterBuilding(go.transform, b, district, kind, fp, id);                  // W86 integration: v07 / T2 reskins, T1 extras
            return true;
        }

        sealed class BInfo { public GameObject Go; public string Id, Type; public List<Vector2> Fp; public float Base, Top; public Dictionary<string, object> Roof; }
        static readonly List<BInfo> Built = new();

        static IEnumerable<(float s0, float s1, float h)> Segments(float L, List<(float s, float w, float h)> cuts)
        {
            float cur = 0f;
            foreach (var c in cuts.OrderBy(c => c.s))
            {
                float a = Mathf.Max(cur, c.s - c.w * .5f), b = Mathf.Min(L, c.s + c.w * .5f);
                if (b <= a) continue;
                if (a > cur) yield return (cur, a, 0f);
                yield return (a, b, c.h);
                cur = b;
            }
            if (cur < L) yield return (cur, L, 0f);
        }

        // Drive-through arches of a building: entrances[kind=arch] (pos, w_m, clear_h_m, through) and arches[] (rect, clear_w_m, clear_h_m,
        // through), merged (the Rough lists each arch in both). Defaults 4 x 4.5 m (W85 v01). Axis = passage direction (N-S / W-E), else the
        // footprint's short axis (the passage goes through the depth).
        struct Arch { public Vector2 P, Axis; public float W, H; }
        static List<Arch> ArchesOf(Dictionary<string, object> b, List<Vector2> fp)
        {
            var list = new List<Arch>();
            Frame(fp, new Dictionary<string, object>(), out _, out _, out Vector2 shortAx, out _, out _);
            Vector2 AxisOf(string through) => through == "N-S" ? Vector2.up : through == "W-E" || through == "E-W" ? Vector2.right : shortAx;
            void Add(Vector2 p, float w, float h, string through)
            {
                if (list.Any(a => (a.P - p).magnitude < 2f)) return;
                list.Add(new Arch { P = p, W = w > .5f ? w : 4f, H = h > .5f ? h : 4.5f, Axis = AxisOf(through) });
            }
            foreach (var e in Arr(Get(b, "entrances")).Select(Obj))
                if (e != null && S(Get(e, "kind")) == "arch") Add(V2(Get(e, "pos")), F(Get(e, "w_m") ?? Get(e, "clear_w_m"), 4f), F(Get(e, "clear_h_m"), 4.5f), S(Get(e, "through")));
            foreach (var a in Arr(Get(b, "arches")).Select(Obj))
            {
                var r = V2s(Get(a, "rect"));
                if (a == null || r.Length < 3) continue;
                Add(r.Aggregate(Vector2.zero, (s, q) => s + q) / r.Length, F(Get(a, "clear_w_m") ?? Get(a, "w_m"), 4f), F(Get(a, "clear_h_m"), 4.5f), S(Get(a, "through")));
            }
            return list;
        }

        // Oriented frame of a footprint: ridge along ridge_axis_deg or the longest edge.
        static void Frame(List<Vector2> fp, Dictionary<string, object> roof, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy)
        {
            float ang;
            if (Get(roof, "ridge_axis_deg") != null) ang = F(Get(roof, "ridge_axis_deg")) * Mathf.Deg2Rad;
            else
            {
                int best = 0; float bl = 0;
                for (int i = 0; i < fp.Count; i++) { float l = (fp[(i + 1) % fp.Count] - fp[i]).magnitude; if (l > bl) { bl = l; best = i; } }
                Vector2 e = fp[(best + 1) % fp.Count] - fp[best]; ang = Mathf.Atan2(e.y, e.x);
            }
            ax = new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)); ay = new Vector2(-ax.y, ax.x);
            float x0 = float.MaxValue, x1 = float.MinValue, y0 = float.MaxValue, y1 = float.MinValue;
            foreach (var q in fp) { float u = Vector2.Dot(q, ax), v = Vector2.Dot(q, ay); x0 = Mathf.Min(x0, u); x1 = Mathf.Max(x1, u); y0 = Mathf.Min(y0, v); y1 = Mathf.Max(y1, v); }
            c = ax * (x0 + x1) * .5f + ay * (y0 + y1) * .5f; hx = (x1 - x0) * .5f; hy = (y1 - y0) * .5f;
        }

        static void Roof(Transform parent, string id, List<Vector2> fp, float top, string type, Dictionary<string, object> roof, string roofMat, string walls)
        {
            float tile = Tile(roofMat);
            if (type == "none") return;
            if (type == "flat")
            {
                var capMesh = Fill("B_" + id + "_roof", fp.ToArray(), q => top, Vector2.zero);
                capMesh.uv = capMesh.vertices.Select(v => new Vector2(v.x, v.z) / tile).ToArray();
                EditorUtility.SetDirty(capMesh);
                MeshGo("roof", parent, capMesh, RoofMat(roofMat));
                float ph = F(Get(roof, "parapet_h_m"), 0f);
                if (ph > 0f)
                {
                    var mb = new MB();
                    for (int i = 0; i < fp.Count; i++)
                    {
                        Vector2 a = fp[i], b = fp[(i + 1) % fp.Count];
                        mb.Quad(new Vector3(a.x, top, a.y), new Vector3(a.x, top + ph, a.y), new Vector3(b.x, top + ph, b.y), new Vector3(b.x, top, b.y),
                            Vector2.zero, new Vector2(0, ph / 4f), new Vector2((b - a).magnitude / 4f, ph / 4f), new Vector2((b - a).magnitude / 4f, 0));
                        mb.Quad(new Vector3(b.x, top, b.y), new Vector3(b.x, top + ph, b.y), new Vector3(a.x, top + ph, a.y), new Vector3(a.x, top, a.y),
                            Vector2.zero, new Vector2(0, ph / 4f), new Vector2((b - a).magnitude / 4f, ph / 4f), new Vector2((b - a).magnitude / 4f, 0));
                    }
                    MeshGo("parapet", parent, mb.Build("B_" + id + "_parapet"), WallMat(walls));
                }
                return;
            }
            Frame(fp, roof, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            float ov = F(Get(roof, "overhang_m"), .4f), rh = F(Get(roof, "ridge_h_m"), Mathf.Max(1.5f, hy * .7f));
            hx += ov; hy += ov;
            Vector3 Q(float u, float v, float y) { Vector2 p = c + ax * u + ay * v; return new Vector3(p.x, y, p.y); }
            var r = new MB(); var g = new MB();
            float slopeLen = Mathf.Sqrt(hy * hy + rh * rh) / tile, along = 2f * hx / tile;
            float e = top - ov * rh / Mathf.Max(hy - ov, .5f);                         // eave drops with the overhang
            if (type == "shed")
            {
                r.Quad(Q(-hx, -hy, e), Q(-hx, hy, top + rh), Q(hx, hy, top + rh), Q(hx, -hy, e), Vector2.zero, new Vector2(0, slopeLen), new Vector2(along, slopeLen), new Vector2(along, 0));
            }
            else
            {
                float rx = type == "hip" ? Mathf.Max(0f, hx - hy) : type == "pyramid" ? 0f : hx;
                r.Quad(Q(-hx, -hy, e), Q(-rx, 0, top + rh), Q(rx, 0, top + rh), Q(hx, -hy, e), Vector2.zero, new Vector2(0, slopeLen), new Vector2(along, slopeLen), new Vector2(along, 0));
                r.Quad(Q(hx, hy, e), Q(rx, 0, top + rh), Q(-rx, 0, top + rh), Q(-hx, hy, e), Vector2.zero, new Vector2(0, slopeLen), new Vector2(along, slopeLen), new Vector2(along, 0));
                if (type == "gable")
                {
                    float gt = Tile(walls);
                    g.Tri(Q(-hx + ov, -hy + ov, top), Q(-hx + ov, hy - ov, top), Q(-hx + ov, 0, top + rh), Vector2.zero, new Vector2(2 * (hy - ov) / gt, 0), new Vector2((hy - ov) / gt, rh / gt));
                    g.Tri(Q(hx - ov, hy - ov, top), Q(hx - ov, -hy + ov, top), Q(hx - ov, 0, top + rh), Vector2.zero, new Vector2(2 * (hy - ov) / gt, 0), new Vector2((hy - ov) / gt, rh / gt));
                }
                else
                {
                    r.Tri(Q(-hx, hy, e), Q(-rx, 0, top + rh), Q(-hx, -hy, e), Vector2.zero, new Vector2(hy / tile, slopeLen), new Vector2(2 * hy / tile, 0));
                    r.Tri(Q(hx, -hy, e), Q(rx, 0, top + rh), Q(hx, hy, e), Vector2.zero, new Vector2(hy / tile, slopeLen), new Vector2(2 * hy / tile, 0));
                }
            }
            var rm = r.Build("B_" + id + "_roof");
            // double-sided roof underside for overhangs
            MeshGo("roof", parent, rm, RoofMat(roofMat)).GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.TwoSided;
            if (g.V.Count > 0) MeshGo("gables", parent, g.Build("B_" + id + "_gables"), WallMat(walls));
            // ridge caps from the kit (plug the seam; carry their own UCX)
            string cap = S(Get(roof, "ridge_cap"));
            if (type != "shed" && type != "pyramid" && cap != null)
            {
                string piece = cap.Contains("slate") ? "FK_G_RidgeCap_Slate_2m" : cap.Contains("metal") ? "FK_G_RidgeCap_Metal_2m" : "FK_G_RidgeCap_Tile_2m";
                float rx = type == "hip" ? Mathf.Max(0f, hx - hy) : hx;
                for (float s = -rx + 1f; s <= rx - 1f + 1e-3f; s += 2f)
                    Piece(piece, parent.Find("details") ?? parent, Q(s, 0, top + rh), new Vector3(ay.x, 0, ay.y));
            }
        }

        // ROOF_COLLISION_NOTE recipe 1: body box (convex prism) + ONE convex hull of the whole roof incl. the ridge (no gap).
        static void Colliders(Transform parent, string id, List<Vector2> fp, float baseY, float top, string type, Dictionary<string, object> roof, List<Arch> arches)
        {
            var col = new GameObject("colliders"); col.transform.SetParent(parent, false);
            Frame(fp, roof, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            bool rect = fp.Count == 4;
            float yaw = -Mathf.Atan2(ax.y, ax.x) * Mathf.Rad2Deg;
            if (rect && arches.Count > 0)
            {
                // body split around each arch (the arch's clear width below its clear height, a box above it up to the roof); the split runs
                // along the walls the passage cuts through (normally the long axis)
                bool alongX = Mathf.Abs(Vector2.Dot(arches[0].Axis, ax)) < .5f;
                Vector2 u = alongX ? ax : ay; float hu = alongX ? hx : hy, hv = alongX ? hy : hx;
                float uyaw = -Mathf.Atan2(u.y, u.x) * Mathf.Rad2Deg;
                var cuts = arches.Select(a => (s: Vector2.Dot(a.P - c, u), a.W, a.H)).OrderBy(t => t.s).ToList();
                float cur = -hu;
                foreach (var ct in cuts)
                {
                    float a0 = Mathf.Clamp(ct.s - ct.W * .5f, -hu, hu), a1 = Mathf.Clamp(ct.s + ct.W * .5f, -hu, hu);
                    if (a0 > cur + .1f) AddBox(col.transform, c + u * (cur + a0) * .5f, baseY, top, a0 - cur, 2 * hv, uyaw);
                    if (a1 > a0 + .05f) AddBox(col.transform, c + u * (a0 + a1) * .5f, baseY + ct.H, top, a1 - a0, 2 * hv, uyaw);
                    cur = Mathf.Max(cur, a1);
                }
                if (hu > cur + .1f) AddBox(col.transform, c + u * (cur + hu) * .5f, baseY, top, hu - cur, 2 * hv, uyaw);
            }
            else if (rect) AddBox(col.transform, c, baseY, top, 2 * hx, 2 * hy, yaw);
            else if (IsConvex(fp))
            {
                var pts = new List<Vector3>();
                foreach (var q in fp) { pts.Add(new Vector3(q.x, baseY, q.y)); pts.Add(new Vector3(q.x, top, q.y)); }
                Hull(col.transform, "body", pts, id);
            }
            else Prism(col.transform, fp, baseY, top, id);     // v02: concave (L / U / T) bodies -> closed non-convex prism, no filled corners
            if (type == "flat" || type == "none") { float ph = F(Get(roof, "parapet_h_m"), 0f); if (ph > 0) ParapetBoxes(col.transform, fp, top, ph); return; }
            float ov = F(Get(roof, "overhang_m"), .4f), rh = F(Get(roof, "ridge_h_m"), Mathf.Max(1.5f, hy * .7f));
            float HX = hx + ov, HY = hy + ov, e = top - ov * rh / Mathf.Max(hy, .5f);
            Vector3 Q(float u, float v, float y) { Vector2 p = c + ax * u + ay * v; return new Vector3(p.x, y, p.y); }
            float rx = type == "hip" ? Mathf.Max(0f, HX - HY) : type == "pyramid" ? 0f : HX;
            var roofPts = new List<Vector3> { Q(-HX, -HY, e - .02f), Q(HX, -HY, e - .02f), Q(HX, HY, e - .02f), Q(-HX, HY, e - .02f), Q(-rx, 0, top + rh + .05f), Q(rx, 0, top + rh + .05f) };
            if (type == "shed") roofPts = new List<Vector3> { Q(-HX, -HY, e), Q(HX, -HY, e), Q(HX, HY, top + rh), Q(-HX, HY, top + rh), Q(-HX, -HY, top - .05f), Q(HX, HY, top - .05f) };
            roofPts.Add(Q(0, 0, top - .02f));                                           // overlap the body (no gap > 0.02 m)
            Hull(col.transform, "roof", roofPts, id);
        }

        static bool IsConvex(List<Vector2> fp)
        {
            int sign = 0;
            for (int i = 0; i < fp.Count; i++)
            {
                float c = Cross(fp[i], fp[(i + 1) % fp.Count], fp[(i + 2) % fp.Count]);
                if (Mathf.Abs(c) < 1e-4f) continue;
                int sg = c > 0 ? 1 : -1;
                if (sign != 0 && sg != sign) return false;
                sign = sg;
            }
            return true;
        }

        // Closed prism (walls out, cap up, floor down) as a static non-convex MeshCollider for concave footprints.
        static void Prism(Transform parent, List<Vector2> fp, float y0, float y1, string id)
        {
            var mb = new MB();
            for (int i = 0; i < fp.Count; i++)
            {
                Vector2 a = fp[i], b = fp[(i + 1) % fp.Count];
                mb.Quad(new Vector3(a.x, y0, a.y), new Vector3(a.x, y1, a.y), new Vector3(b.x, y1, b.y), new Vector3(b.x, y0, b.y), Vector2.zero, Vector2.up, Vector2.one, Vector2.right);
            }
            var cap = Fill("tmp", fp.ToArray(), q => y1, Vector2.zero, false);
            int o = mb.V.Count;
            mb.V.AddRange(cap.vertices); mb.UV.AddRange(cap.vertices.Select(v => Vector2.zero)); mb.T.AddRange(cap.triangles.Select(t => t + o));
            o = mb.V.Count;
            mb.V.AddRange(cap.vertices.Select(v => new Vector3(v.x, y0, v.z))); mb.UV.AddRange(cap.vertices.Select(v => Vector2.zero));
            var tt = cap.triangles;
            for (int i = 0; i + 2 < tt.Length; i += 3) { mb.T.Add(tt[i] + o); mb.T.Add(tt[i + 2] + o); mb.T.Add(tt[i + 1] + o); }
            Object.DestroyImmediate(cap);
            var m = mb.Build("B_" + id + "_body_prism");
            var g = new GameObject("body"); g.transform.SetParent(parent, false);
            g.AddComponent<MeshCollider>().sharedMesh = m;
        }

        static void AddBox(Transform parent, Vector2 c, float y0, float y1, float sx, float sz, float yaw)
        {
            var g = new GameObject("box"); g.transform.SetParent(parent, false);
            g.transform.position = new Vector3(c.x, (y0 + y1) * .5f, c.y); g.transform.rotation = Quaternion.Euler(0, yaw, 0);
            g.AddComponent<BoxCollider>().size = new Vector3(sx, y1 - y0, sz);
        }

        static void ParapetBoxes(Transform parent, List<Vector2> fp, float top, float ph)
        {
            for (int i = 0; i < fp.Count; i++)
            {
                Vector2 a = fp[i], b = fp[(i + 1) % fp.Count], d = b - a;
                AddBox(parent, (a + b) * .5f, top, top + ph, d.magnitude, .25f, -Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
            }
        }

        static void Hull(Transform parent, string name, List<Vector3> pts, string id)
        {
            // convex MeshCollider: Unity builds the hull from the vertices; triangles only need to be valid
            var m = new Mesh { name = "B_" + id + "_" + name + "_hull" };
            m.SetVertices(pts);
            var tri = new List<int>();
            for (int i = 1; i + 1 < pts.Count; i++) { tri.Add(0); tri.Add(i); tri.Add(i + 1); }
            m.SetTriangles(tri, 0);
            AssetDatabase.CreateAsset(m, Gen + "/Meshes/" + Safe(m.name) + ".asset");
            var g = new GameObject(name); g.transform.SetParent(parent, false);
            var mc = g.AddComponent<MeshCollider>(); mc.sharedMesh = m; mc.convex = true;
        }

        // Facade sockets: Rough balconies/podyezds, Downtown fire escapes/AC/water tanks/awnings, Hamlet porch/chimney/shutters.
        static void Sockets(Transform details, Dictionary<string, object> b, List<Vector2> fp, float baseY, float top, int floors, float floorH, string district)
        {
            string id = S(Get(b, "id"), "b"), kit = S(Get(b, "facade_kit"), "none");
            var sk = Obj(Get(b, "sockets")) ?? new Dictionary<string, object>();
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null).ToList();
            Vector2 centre = fp.Aggregate(Vector2.zero, (s, q) => s + q) / fp.Count;
            Vector3 Out(Vector2 a, Vector2 c2) { Vector2 d = (c2 - a).normalized; var n = new Vector3(d.y, 0, -d.x); return n; }   // CCW footprint: right normal = outward
            foreach (var e in ents)
            {
                string k = S(Get(e, "kind"), "door");
                Vector2 p = V2(Get(e, "pos"));
                float f = F(Get(e, "facing_deg")) * Mathf.Deg2Rad;
                var outward = new Vector3(Mathf.Cos(f), 0, Mathf.Sin(f));
                if (outward.sqrMagnitude < .5f) outward = new Vector3(p.x - centre.x, 0, p.y - centre.y).normalized;
                var at = new Vector3(p.x, baseY + .25f, p.y);
                if (kit == "rough" && k == "podyezd")
                {
                    Piece("FK_R_IronDoor", details, at, outward);
                    Piece("FK_R_Entrance_Canopy", details, at + Vector3.up * 2.4f, outward);
                    Piece(Hash(id + p) > .5f ? "FK_R_Entrance_Steps3" : "FK_R_Entrance_Steps2", details, at, outward);
                }
                else if (kit == "hamlet" && k == "door")
                {
                    Piece("FK_H_Steps", details, at, outward);
                    // the kit porch roof stands on its own posts from the ground (pivot on the ground, 3.05 m): it was placed 2.3 m up and
                    // hung in the air at every Hamlet door (Fedya 21.10, "roofs in the air" near base 2)
                    Piece("FK_H_PorchRoof", details, at, outward);
                    var df = AssetDatabase.LoadAssetAtPath<GameObject>(PK1Door);
                    if (df)
                    {   // the door itself (pilot kit rural door frame + leaf) in the wall, threshold at the top step
                        var dg = (GameObject)PrefabUtility.InstantiatePrefab(df, details);
                        dg.transform.SetPositionAndRotation(at + Vector3.up * .5f, Quaternion.LookRotation(outward, Vector3.up));
                        foreach (Transform t in dg.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                    }
                }
            }
            for (int i = 0; i < fp.Count; i++)
            {
                Vector2 a = fp[i], c2 = fp[(i + 1) % fp.Count];
                float L = (c2 - a).magnitude;
                if (L < 6f) continue;
                Vector3 n = Out(a, c2);
                Vector2 d = (c2 - a) / L;
                bool entranceSide = ents.Any(e => Mathf.Abs(Cross(a, c2, V2(Get(e, "pos")))) / L < 3f);
                if (kit == "rough")
                {
                    string bal = S(Get(sk, "balconies"), "mixed");
                    int bays = Mathf.FloorToInt(L / 3.2f);
                    for (int bay = 0; bay < bays; bay++)
                    {
                        Vector2 q = a + d * (L - bays * 3.2f) * .5f + d * (bay + .5f) * 3.2f;
                        for (int fl = 0; fl < floors; fl++)
                        {
                            var wpos = new Vector3(q.x, baseY + .25f + fl * floorH + .85f, q.y);
                            Piece("FK_R_Window_Frame", details, wpos, n);
                            if (bal != "none" && !entranceSide && fl > 0 && bay % 2 == 1 && Hash(id + bay + "_" + fl) > .3f)
                                Piece(bal == "open" || (bal == "mixed" && Hash(id + bay + fl, 3) > .5f) ? "FK_R_Balcony_Open" : "FK_R_Balcony_Glazed", details, new Vector3(q.x, baseY + .25f + fl * floorH, q.y), n);
                        }
                    }
                    for (float s = 1f; s < L; s += 2.8f * 4f) Piece("FK_R_Drainpipe_2m8", details, new Vector3(a.x + d.x * s, baseY + .25f, a.y + d.y * s), n);
                }
                else if (kit == "downtown")
                {
                    if (F(Get(sk, "ac_units")) > 0 || Hash(id + i) > .6f) Piece("FK_D_AC_Unit", details, new Vector3(a.x + d.x * L * .3f, baseY + floorH * 1.6f, a.y + d.y * L * .3f), n);
                    if (Get(sk, "fire_escape") is bool fe && fe && !entranceSide && i == 0)
                        for (int fl = 1; fl < floors; fl++)
                        {
                            Piece("FK_D_FireEscape_Landing", details, new Vector3(a.x + d.x * L * .5f, baseY + fl * floorH, a.y + d.y * L * .5f), n);
                            Piece("FK_D_FireEscape_Stair", details, new Vector3(a.x + d.x * L * .5f, baseY + fl * floorH, a.y + d.y * L * .5f), n);
                        }
                    if (Get(sk, "awning") is bool aw && aw && entranceSide) Piece("FK_D_Storefront_Awning", details, new Vector3(a.x + d.x * L * .5f, baseY + 3.0f, a.y + d.y * L * .5f), n);
                    for (float s = 1f; s < L - 1f; s += 2f) Piece("FK_D_Parapet_2m", details, new Vector3(a.x + d.x * s, top, a.y + d.y * s), n);
                }
                else if (kit == "hamlet")
                {
                    if (Get(sk, "windows") is bool w && w)
                        for (float s = 2f; s < L - 1.5f; s += 3f)
                        {
                            Vector2 wq = a + d * s;
                            if (ents.Any(e => (V2(Get(e, "pos")) - wq).magnitude < 1.5f)) continue;     // no window over the door
                            Piece("FK_H_Window_Shutters", details, new Vector3(wq.x, baseY + 1.1f, wq.y), n);
                        }
                }
            }
            if (kit == "downtown" && Get(sk, "water_tank") is bool wt && wt) Piece("FK_D_RoofWaterTank", details, new Vector3(centre.x, top, centre.y), Vector3.forward);
            if (kit == "hamlet") Piece("FK_H_Chimney", details, new Vector3(centre.x, top, centre.y), Vector3.forward);
            if (kit == "rough") Piece("FK_R_Roof_Vent", details, new Vector3(centre.x, top, centre.y), Vector3.forward);
        }

        // Prop kinds of the district data / details -> existing prefabs of Art/Map/Prefabs (shared meshes + materials, static batching);
        // markers (spawn / gathering / legend / triggers) -> empty named objects; everything else -> a sized box (as W76).
        static readonly Dictionary<string, string> PrefabOf = new()
        {
            ["street_lamp"] = "LAMPS/lamp_soviet", ["pole_lamp"] = "LAMPS/lamp_soviet", ["lamp_soviet"] = "LAMPS/lamp_soviet", ["lamp_oldtown_single"] = "LAMPS/lamp_oldtown_single",
            ["lamp_oldtown_double"] = "LAMPS/lamp_oldtown_double", ["lamp_tall"] = "LAMPS/lamp_oldtown_double",
            ["bench"] = "BENCHES/bench_park", ["bench_soviet"] = "BENCHES/bench_soviet", ["bench_soviet_broken"] = "BENCHES/bench_soviet_broken", ["spectator_bench"] = "BENCHES/bench_soviet",
            ["green_bin"] = "BINS/trashbin_tipping", ["bin_green"] = "BINS/trashbin_tipping", ["bin_blue"] = "BINS/trashbin_tipping", ["shared_bin"] = "BINS/trashbin_tipping",
            ["trashbin_concrete"] = "BINS/trashbin_concrete", ["skip_bin"] = "BINS/garbage_container_open", ["dumpster"] = "BINS/garbage_container_closed",
            ["garbage_container_closed"] = "BINS/garbage_container_closed", ["garbage_container_open"] = "BINS/garbage_container_open",
            ["old_soviet_car"] = "CARS/car_hatchback", ["car_hatchback"] = "CARS/car_hatchback", ["car_sedan_beige"] = "CARS/car_sedan_beige", ["car_sedan_blue"] = "CARS/car_sedan_blue",
            ["car_sedan_green"] = "CARS/car_sedan_green", ["car_sedan_red"] = "CARS/car_sedan_red", ["black_suv"] = "CARS/car_sedan_blue", ["rusted_car"] = "WRECKS/car_wrecked",
            ["rusty_car_body"] = "WRECKS/car_wrecked", ["fire_hydrant"] = "TRAFFIC/fire_hydrant", ["sign_stop"] = "TRAFFIC/sign_stop", ["sign_giveway"] = "TRAFFIC/sign_giveway",
            ["swing_set"] = "PLAYGROUND/play_swings", ["slide"] = "PLAYGROUND/play_slide", ["sandbox"] = "PLAYGROUND/play_sandbox", ["roundabout"] = "PLAYGROUND/play_carousel",
            ["pull_up_bar"] = "PLAYGROUND/play_horizontal_bar", ["lifeguard_tower"] = "BEACH/beach_lifeguard_tower", ["bus_stop_shelter"] = "BUS_STOP/busstop_shelter",
            ["lounger_1"] = "BEACH/beach_sunlounger", ["loungers_2"] = "BEACH/beach_sunlounger", ["sun_lounger"] = "BEACH/beach_sunlounger", ["lounger_umbrella_elite"] = "BEACH/beach_sunlounger",
            ["umbrella_towel"] = "BEACH/beach_umbrella_teal", ["umbrella_1_lounger"] = "BEACH/beach_umbrella_red", ["umbrella_2_loungers"] = "BEACH/beach_umbrella_teal",
            ["umbrella_3_loungers"] = "BEACH/beach_umbrella_red", ["beach_umbrella"] = "BEACH/beach_umbrella_red", ["umbrella_yellow"] = "BEACH/beach_umbrella_red",
            ["parked_tractor"] = "HEAVY/tractor_small", ["paz_bus"] = "HEAVY/bus_city", ["security_camera_pole"] = "SMALL/cctv_pole", ["wooden_crate"] = "SMALL/default_crate",
            ["rounded_rock"] = "SMALL/rock_02", ["bin"] = "BINS/trashbin_tipping",
            // Hamlet yard dressing -> the approved pilot kits (i09/i10 props, as in the texture test)
            ["woodpile"] = PK1 + "WOODPILE_v01", ["round_hay_bale"] = PK1 + "HAY_BALE_ROUND_v01", ["old_well"] = PK1 + "WELL_RURAL_v01",
            ["farm_trailer"] = PK1 + "CART_WOODEN_v01", ["handcart"] = PK1 + "CART_WOODEN_v01", ["clothesline"] = PK1 + "LAUNDRY_POLE_PAIR_v01",
            ["watering_can"] = PK2 + "BUCKET_WATERING_v02", ["bucket"] = PK2 + "BUCKET_WATERING_v02", ["outdoor_table"] = PK2 + "PICNIC_TABLE_v02",
            ["gathering_table"] = PK2 + "PICNIC_TABLE_v02", ["flower_pot"] = PK2 + "FLOWER_BED_v02", ["stump"] = PK2 + "AXE_STUMP_LOGS_v02",
        };
        const string PK1 = "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/", PK2 = "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/";
        static readonly HashSet<string> Grip = new() { "street_lamp", "pole_lamp", "lamp_soviet", "lamp_oldtown_single", "lamp_oldtown_double", "lamp_tall", "bench", "bench_soviet",
            "bench_soviet_broken", "spectator_bench", "fire_hydrant", "sign_stop", "sign_giveway", "traffic_light", "flagpole", "pull_up_bar", "light_mast", "floodlight_mast", "bollard" };
        static readonly Dictionary<string, GameObject> PrefabCache = new();

        static GameObject Prefab(string kind)
        {
            if (!PrefabOf.TryGetValue(kind, out string rel)) return null;
            if (PrefabCache.TryGetValue(rel, out var p)) return p;
            return PrefabCache[rel] = AssetDatabase.LoadAssetAtPath<GameObject>((rel.StartsWith("Assets/") ? rel : PrefabLib + rel) + ".prefab");
        }

        static bool Prop(Transform parent, Dictionary<string, object> p)
        {
            string kind = (S(Get(p, "kind"), "") ?? "").ToLowerInvariant();
            if (IsTree(kind) && !kind.Contains("lamp")) return false;               // terrain trees (s05)
            if (Arr(Get(p, "pos")).Count < 2) return false;                         // "count only, place by logic" props have no position
            string id = S(Get(p, "id"), kind);
            Vector2 q = V2(Get(p, "pos"));
            if (kind.Contains("lamp") && HamletLamp(q)) return false;                // H5 (Fedya 21.10): no street lamps in the Hamlet
            if (W86Model(parent, p, kind, id, q)) return true;                       // W86 integration: M1 / M2 models, containers, masts, lamps
            if (W86Prop(parent, p, kind, id, q)) return true;                         // W86: NPC spots, iron gates, piers, hedges, pumps, cars
            if (kind == "legend_object" || kind.Contains("marker") || kind.Contains("spawn") || kind == "trigger_marker")
            {   // numbered legend circle / spawn or gathering point: a named marker, not a cube
                var mk = new GameObject("Marker_" + id + "_" + Safe(S(Get(p, "label"), kind) ?? kind));
                mk.transform.SetParent(parent, false);
                mk.transform.position = P(q);
                return true;
            }
            float rot = F(Get(p, "rot_deg"));
            bool grip = (Get(p, "grip_anchor") is bool g && g) || Grip.Contains(kind);
            var pf = Prefab(kind);
            if (pf)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
                go.name = id;
                go.transform.position = P(q);
                go.transform.rotation = Quaternion.Euler(0, 90f - rot, 0);
                if (grip) go.AddComponent<W76GripAnchor>();
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                if (kind == "leave_country_button") go.AddComponent<W76LeaveCountryButton>();
                return true;
            }
            if (Get(p, "dressing") is bool dr && dr) return false;                    // small yard clutter without a finished asset: no grey boxes
            var sz = Arr(Get(p, "size"));
            Vector3 size = sz.Count >= 3 ? new Vector3(F(sz[0]), F(sz[2]), F(sz[1])) : sz.Count == 2 ? new Vector3(F(sz[0]), 1f, F(sz[1])) : DefaultSize(kind);
            if (size.y <= 0f) size.y = DefaultSize(kind).y;
            float yaw = -rot;
            if (kind.Contains("lamp") || kind.Contains("light") || kind.Contains("pole") || kind.Contains("mast") || kind == "flagpole")
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                go.name = id; go.transform.SetParent(parent, false);
                float h = kind.Contains("mast") ? 16f : kind == "flagpole" ? 12f : kind == "traffic_light" ? 4.2f : 5f;
                go.transform.position = P(q, h * .5f); go.transform.localScale = new Vector3(.16f, h * .5f, .16f);
                go.GetComponent<MeshRenderer>().sharedMaterial = Mat("metal_painted_SK6a");
                if (kind == "traffic_light") Box(go.transform.parent, id + "_head", P(q, h - .4f), new Vector3(.35f, .9f, .35f), yaw, "metal_painted_SK6a", false);
                go.AddComponent<W76GripAnchor>();
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                return true;
            }
            string mat = kind.Contains("container") || kind.Contains("garage") || kind.Contains("kiosk") || kind.Contains("booth") || kind.Contains("gate") || kind.Contains("rail") ? "metal_painted_SK6a" :
                kind.Contains("bench") || kind.Contains("pier") || kind.Contains("lounger") || kind.Contains("hay") || kind.Contains("crate") || kind.Contains("pallet") || kind.Contains("tower") ? "boards_SK5a" :
                "concrete_SK3c";
            var b = Box(parent, id, P(q, size.y * .5f), size, yaw, mat, size.x * size.z > .2f && !(Get(p, "solid") is bool so && !so));
            if (grip || kind.Contains("hydrant") || kind.Contains("sign") || kind.Contains("rail")) b.AddComponent<W76GripAnchor>();
            if (kind == "leave_country_button") b.AddComponent<W76LeaveCountryButton>();
            return true;
        }

        static Vector3 DefaultSize(string kind) =>
            kind.Contains("container") ? new Vector3(6.06f, 2.6f, 2.44f) : kind.Contains("car") ? new Vector3(4.2f, 1.45f, 1.8f) :
            kind.Contains("bench") ? new Vector3(1.8f, .45f, .5f) : kind.Contains("garage") ? new Vector3(3.2f, 2.5f, 6f) :
            kind.Contains("lounger") ? new Vector3(2f, .4f, .7f) : kind.Contains("tower") ? new Vector3(3f, 4f, 3f) : new Vector3(1f, 1f, 1f);

        // small details by rules (Tools/MapV85/s06b_details.py: Downtown lamps / hydrants / traffic lights / signs / parked cars / alley bins,
        // Rough podyezd benches + bins, give-way signs at rural T-joins)
        static void BuildDetails(Transform root)
        {
            var dj = Obj(Json.Parse(File.ReadAllText(Data + "/details_v85.json")));
            var parent = new GameObject("Details_by_rules").transform; parent.SetParent(root, false);
            int n = 0, k = 0;
            foreach (object o in Arr(Get(dj, "props")))
            {
                var p = Obj(o);
                if (!p.ContainsKey("id")) p["id"] = S(Get(p, "kind"), "d") + "_" + k++;
                string door = S(Get(p, "door"));
                if (door != null && (SampleSkip.Contains(door) || (SampleCutX.TryGetValue(door, out var kx) && (V2(Get(p, "pos")).x < kx.x || V2(Get(p, "pos")).x > kx.y)))) continue;
                if (Prop(parent, p)) n++;
            }
            FlushPropBatches(parent);
            Note($"details by rules: {n} placed ({string.Join(", ", Obj(Get(dj, "counts")).Select(kv => kv.Key + " " + kv.Value))})");
        }

        // ------------------------------------------------------------------ texture SAMPLE (Fedya 21.10: texture test v04 approved)
        // Data/v01/texture_sample_v85.json: groups of the texture-test scene (H5 house scheme a, R2c khrushchevka section, D4 street face
        // with G-D glazing) are copied onto chosen W85 spots, replacing (or cutting) the W85 buildings there. They keep the test's own
        // isolated materials (Art/TextureTest_v01/Built_v04) — nothing shared with the rest of the map changes. The urban lamps around the
        // spots get the N-R3 night light (i10 worn lamp light in the head + functional spot in the Rough, flicker, fog halo) and only
        // those lamps are registered with the night sky rig. Remove the json line (or the file) and rebuild to take a sample out.
        static readonly HashSet<string> SampleSkip = new();
        static readonly Dictionary<string, Vector2> SampleCutX = new();
        static readonly List<Light> SampleLamps = new();
        static readonly List<(Vector2 c, float r)> SampleSpots = new();

        static void LoadSampleRules()
        {
            SampleSkip.Clear(); SampleCutX.Clear(); SampleLamps.Clear(); SampleSpots.Clear();
            foreach (var it in Arr(Get(Sample, "items")).Select(Obj))
            {
                var near = Obj(Get(it, "replace_near"));
                if (near != null && !it.ContainsKey("replace"))
                {   // W86: replaced buildings found by kind near the sample (ids change with the pipeline)
                    var kinds = new HashSet<string>(Arr(Get(near, "kinds")).Select(o => S(o)));
                    Vector2 at = V2(Get(it, "pos")); float rad = F(Get(near, "radius_m"), 60f);
                    var ids = new List<object>();
                    foreach (string f in Directory.GetFiles(Data + "/districts", (S(Get(near, "district")) ?? "*") + "_v85.json"))
                        foreach (var bo in Arr(Get(Obj(Json.Parse(File.ReadAllText(f))), "buildings")).Select(Obj))
                        {
                            var fp = V2s(Get(bo, "footprint"));
                            if (fp.Length < 3 || !kinds.Contains(S(Get(bo, "kind"), ""))) continue;
                            if ((fp.Aggregate(Vector2.zero, (s2, q) => s2 + q) / fp.Length - at).magnitude <= rad) ids.Add(S(Get(bo, "id")));
                        }
                    it["replace"] = ids;
                }
                foreach (var r in Arr(Get(it, "replace"))) SampleSkip.Add(S(r));
                var cut = Obj(Get(it, "cut"));
                if (cut != null) SampleCutX[S(Get(cut, "building"))] = V2(Get(cut, "keep_x"));
            }
        }

        static List<Vector2> CutFootprint(string id, List<Vector2> fp)
        {
            if (!SampleCutX.TryGetValue(id, out var k)) return fp;
            return fp.Select(q => new Vector2(Mathf.Clamp(q.x, k.x, k.y), q.y)).ToList();
        }

        static void BuildSample(Transform root)
        {
            var items = Arr(Get(Sample, "items")).Select(Obj).Where(o => o != null).ToList();
            if (items.Count == 0) { Note("texture sample: none"); return; }
            var parent = new GameObject("TextureSample_v04").transform; parent.SetParent(root, false);
            var scenes = new Dictionary<string, Scene>();
            var log = new List<string>();
            try
            {
                foreach (var it in items)
                {
                    string id = S(Get(it, "id")), path = S(Get(it, "source"));
                    Vector2 at = V2(Get(it, "pos"));
                    float y = Get(it, "y") != null ? F(Get(it, "y")) : Height(at.x, at.y);
                    GameObject copy;
                    {
                        string src = S(Get(it, "source_scene")) ?? S(Get(Sample, "source_scene"));
                        if (!scenes.TryGetValue(src, out var sc)) scenes[src] = sc = EditorSceneManager.OpenScene(src, OpenSceneMode.Additive);
                        Transform t = null;
                        foreach (var r in sc.GetRootGameObjects()) { t = r.transform.Find(path); if (t) break; }
                        if (!t) { log.Add("missing source " + path); continue; }
                        copy = Object.Instantiate(t.gameObject);
                        copy.name = "Sample_" + id + "_" + t.name;
                        SceneManager.MoveGameObjectToScene(copy, root.gameObject.scene);
                        copy.transform.SetParent(parent, false);
                        foreach (var ex in Arr(Get(it, "exclude")).Select(e => S(e)))
                        { var c = copy.transform.Find(ex); if (c) Object.DestroyImmediate(c.gameObject); }
                    }
                    var fit = Obj(Get(it, "fit_depth"));
                    if (fit != null) FitDepth(copy, id, fit);
                    copy.transform.SetPositionAndRotation(new Vector3(at.x, y, at.y), Quaternion.Euler(0, F(Get(it, "yaw_deg")), 0));
                    // colliders (the texture test is visual only): boxes given in the data (local frame), "mesh" = exact static mesh
                    // colliders on the main surfaces, else convex hulls per mesh
                    var boxes = Arr(Get(it, "boxes")).Select(Obj).Where(b => b != null).ToList();
                    string colMode = S(Get(it, "colliders"), "");
                    if (boxes.Count > 0)
                        foreach (var bx in boxes)
                        {
                            var g = new GameObject("collider"); g.transform.SetParent(copy.transform, false);
                            var bc = g.AddComponent<BoxCollider>();
                            var cc = Arr(Get(bx, "centre")); var ss = Arr(Get(bx, "size"));
                            bc.center = new Vector3(F(cc[0]), F(cc[1]), F(cc[2])); bc.size = new Vector3(F(ss[0]), F(ss[1]), F(ss[2]));
                        }
                    else
                        foreach (var mf in copy.GetComponentsInChildren<MeshFilter>(true))
                        {
                            if (!mf.sharedMesh || mf.name.Contains("atlas") || mf.GetComponent<Collider>()) continue;
                            if (colMode == "mesh") { if (mf.name.Contains("frame") || mf.name.Contains("Mullion")) continue; mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh; }
                            else { var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; mc.convex = true; }
                        }
                    if (Get(it, "lod") is bool lodOn && lodOn)
                    {   // LOD1 drops the thin mullion / fin meshes, culled below 0.4 % of the screen height
                        var all = copy.GetComponentsInChildren<Renderer>();
                        var thin = all.Where(r => r.name.Contains("frame") || r.name.Contains("Mullion") || r.name.Contains("crown")).ToArray();
                        var lod = copy.AddComponent<LODGroup>();
                        lod.SetLODs(new[] { new LOD(.25f, all), new LOD(.004f, all.Except(thin).ToArray()) });
                        lod.RecalculateBounds();
                    }
                    foreach (var tr in copy.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(tr.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                    SampleSpots.Add((at, F(Get(it, "night_radius_m"), 0f)));
                    foreach (var mv in Arr(Get(it, "move_objects")).Select(Obj).Where(o => o != null))
                    {
                        var go = root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == S(Get(mv, "name")));
                        if (!go) { log.Add("move: missing " + S(Get(mv, "name"))); continue; }
                        Vector2 q = V2(Get(mv, "pos")); var sz = Arr(Get(mv, "size"));
                        go.position = new Vector3(q.x, y + F(Get(mv, "lift_m")), q.y);
                        if (sz.Count == 3 && go.TryGetComponent(out MeshFilter mfm) && mfm.sharedMesh && mfm.sharedMesh.name == "Cube") go.localScale = new Vector3(F(sz[0]), F(sz[1]), F(sz[2]));
                        log.Add($"moved {go.name} to ({q.x:0.0}, {q.y:0.0}) +{F(Get(mv, "lift_m")):0.0} m");
                    }
                    log.Add($"{id}: {path} at ({at.x:0.0}, {at.y:0.0}) y {y:0.00} yaw {F(Get(it, "yaw_deg")):0}" + (Arr(Get(it, "replace")).Count > 0 ? " replaces " + string.Join(", ", Arr(Get(it, "replace")).Select(o => S(o))) : "") + (Get(it, "cut") != null ? " cuts " + S(Get(Obj(Get(it, "cut")), "building")) : ""));
                }
            }
            finally { foreach (var sc in scenes.Values) EditorSceneManager.CloseScene(sc, true); }
            // no terrain tree inside a sample or within 2.5 m of it (the samples are a little larger than the W85 houses they replace)
            var rects = parent.Cast<Transform>().Select(c => { var rs = c.GetComponentsInChildren<Renderer>(); var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return Rect.MinMaxRect(b.min.x - 2.5f, b.min.z - 2.5f, b.max.x + 2.5f, b.max.z + 2.5f); }).ToList();
            var td = Ter.terrainData;
            var trees = td.treeInstances;
            var kept = trees.Where(ti => { var w = new Vector2(ti.position.x * td.size.x, ti.position.z * td.size.z); return !rects.Any(r => r.Contains(w)); }).ToArray();
            if (kept.Length != trees.Length) { td.SetTreeInstances(kept, true); EditorUtility.SetDirty(td); }
            log.Add($"{trees.Length - kept.Length} terrain trees removed at the samples");
            Note("texture sample: " + string.Join("; ", log));
        }

        // T4 podium fitted to the plaza (Fedya 21.10: adapt the podium to the plaza, not the plaza to the podium): the 26 m deep podium and
        // the connector are squeezed in depth (local z) to the free depth between the plaza stair and the street; the towers are not touched.
        // Meshes are copied into Generated (the test assets stay as they are).
        static void FitDepth(GameObject copy, string id, Dictionary<string, object> fit)
        {
            float k = F(Get(fit, "k"), 1f), podY = F(Get(fit, "podium_y"), 8.6f), cx = F(Get(fit, "connector_half_x"), 6.4f), cy = F(Get(fit, "connector_y"), 16.6f);
            float tx = F(Get(fit, "tower_x"), 16f), tr = F(Get(fit, "tower_r"), 12f);
            int moved = 0;
            foreach (var mf in copy.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh) continue;
                var m = Object.Instantiate(mf.sharedMesh); m.name = "Sample_" + id + "_" + mf.sharedMesh.name;
                var root = copy.transform; var toLocal = root.worldToLocalMatrix * mf.transform.localToWorldMatrix; var toMesh = toLocal.inverse;
                var v = m.vertices;
                for (int i = 0; i < v.Length; i++)
                {
                    var p = toLocal.MultiplyPoint3x4(v[i]);
                    bool tower = Mathf.Abs(p.x) > cx && new Vector2(Mathf.Abs(p.x) - tx, p.z).magnitude < tr && p.y > -.5f;
                    bool podium = p.y <= podY && !tower, conn = Mathf.Abs(p.x) <= cx && p.y <= cy;
                    if (!(podium || conn)) continue;
                    p.z *= k; v[i] = toMesh.MultiplyPoint3x4(p); moved++;
                }
                m.vertices = v; m.RecalculateBounds(); m.RecalculateNormals(); m.RecalculateTangents();
                AssetDatabase.CreateAsset(m, Gen + "/Meshes/" + Safe(m.name) + ".asset");
                mf.sharedMesh = m;
            }
            Note($"texture sample {id}: podium + connector depth x{k:0.000} ({moved} vertices), towers unchanged");
        }

        // texture test v04 FlickerLamp (N-R3): point light in the lamp head (MP_Glass centroid), #BAC8D2, range 7, 0.4, off by day;
        // in the Rough + a spot under the head (range 15, 95 deg, soft shadows) that follows the flicker (FlickerFollowerV01, on 140).
        static Light NightLamp(GameObject pole, bool strong) => NightLamps(pole, strong)[0];

        // W86 (Fedya 25.10, recheck 01): one light PER HEAD. The MP_Glass vertices of the pole are clustered (heads > 0.5 m apart);
        // a single-head lamp is unchanged, a double lantern gets two lights, each at its own glass, dimmed so the pair reads as one
        // fixture (x .62 each) instead of a doubled one.
        static List<Light> NightLamps(GameObject pole, bool strong)
        {
            var pts = new List<Vector3>();
            foreach (var r in pole.GetComponentsInChildren<MeshRenderer>())
            {
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var mesh = mf.sharedMesh; var vs = mesh.vertices; var mats = r.sharedMaterials;
                for (int s = 0; s < Mathf.Min(mesh.subMeshCount, mats.Length); s++)
                    if (mats[s] && (mats[s].name == "MP_Glass" || mats[s].name == "MP_Lamp_Glow")) pts.AddRange(mesh.GetTriangles(s).Select(i => r.transform.TransformPoint(vs[i])));
            }
            // connected glass = one head: a point joins (and merges) every cluster that has a point within 0.35 m
            var heads = new List<List<Vector3>>();
            foreach (var p in pts.Distinct())
            {
                var near = heads.Where(c => c.Any(q => (q - p).sqrMagnitude < .1225f)).ToList();
                if (near.Count == 0) { heads.Add(new List<Vector3> { p }); continue; }
                var first = near[0]; first.Add(p);
                for (int k = 1; k < near.Count; k++) { first.AddRange(near[k]); heads.Remove(near[k]); }
            }
            // glass panes and the glowing bulb of ONE lantern can sit apart: clusters whose centres are within 0.7 m are one head
            // (the two heads of the Old Town double lantern are 1.24 m apart)
            for (bool merged = true; merged;)
            {
                merged = false;
                for (int i = 0; i < heads.Count && !merged; i++)
                    for (int k = i + 1; k < heads.Count && !merged; k++)
                    {
                        Vector3 ci = heads[i].Aggregate(Vector3.zero, (x, y) => x + y) / heads[i].Count, ck = heads[k].Aggregate(Vector3.zero, (x, y) => x + y) / heads[k].Count;
                        if ((ci - ck).sqrMagnitude < .49f) { heads[i].AddRange(heads[k]); heads.RemoveAt(k); merged = true; }
                    }
            }
            heads = heads.Where(h => h.Count >= 3).ToList();
            var centres = heads.Count > 0 ? heads.Select(h => h.Aggregate(Vector3.zero, (a, c) => a + c) / h.Count - Vector3.up * .07f).ToList() : null;
            if (centres == null)
            {
                var rs = pole.GetComponentsInChildren<Renderer>(); var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                centres = new List<Vector3> { new(bb.center.x, bb.max.y - .3f, bb.center.z) };
            }
            float share = centres.Count > 1 ? .62f : 1f;
            ColorUtility.TryParseHtmlString("#BAC8D2", out Color col);
            var lights = new List<Light>();
            foreach (var c in centres)
            {
                var light = new GameObject("Flicker").AddComponent<Light>();
                light.transform.SetParent(pole.transform, false); light.transform.position = c;
                light.type = LightType.Point; light.color = col; light.range = 7f; light.intensity = .4f; light.shadows = LightShadows.None; light.enabled = false;
                lights.Add(light);
                if (!strong) continue;
                var spot = new GameObject("Flicker_Spot").AddComponent<Light>();
                spot.transform.SetParent(light.transform, false); spot.transform.SetPositionAndRotation(light.transform.position - Vector3.up * .6f, Quaternion.Euler(90f, 0, 0));
                spot.type = LightType.Spot; spot.color = col; spot.range = 15f; spot.spotAngle = 95f; spot.innerSpotAngle = 50f;
                spot.shadows = LightShadows.Soft; spot.shadowStrength = .9f; spot.shadowNearPlane = .1f; spot.enabled = false;
                var ad = new SerializedObject(spot.gameObject.AddComponent<UniversalAdditionalLightData>()); var tier = ad.FindProperty("m_AdditionalLightsShadowResolutionTier"); if (tier != null) { tier.intValue = 1; ad.ApplyModifiedPropertiesWithoutUndo(); }
                var fol = spot.gameObject.AddComponent<OnlyVolunteers.Art.TextureTest.FlickerFollowerV01>(); fol.source = light; fol.target = spot; fol.sourceOn = .65f; fol.targetOn = 140f * share;
            }
            return lights;
        }

        // after the i10 look (which empties the sky rig's lamp list): only the sample lamps turn on at night, flicker and get fog halos
        public static readonly Rect DowntownCalmRect = new(960f, 120f, 460f, 540f); // world XZ around Downtown (the Rough lies west of x 960)
        static void SampleNight(Transform root)
        {
            if (SampleLamps.Count == 0) return;
            var life = (root.Find("NightLamps_N-R3") ?? root).gameObject.AddComponent<OnlyVolunteers.Map.Look.V3.DistrictLife19V02>();
            life.flyers = Array.Empty<OnlyVolunteers.Map.Look.V3.DistrictLife19V02.Flyer>(); life.wornLamps = SampleLamps.ToArray();
            life.calmAreas = new[] { DowntownCalmRect }; // W86 (Fedya 25.10): Downtown lamps steady, rare short drop-outs; the Rough keeps the worn flicker
            int rigs = 0;
            foreach (var mb in root.GetComponentsInChildren<MonoBehaviour>(true).Where(m => m && m.GetType().Name == "SkyMapNight22I03"))
            {
                var so = new SerializedObject(mb);
                var p = so.FindProperty("lamps");
                if (p != null) { p.arraySize = SampleLamps.Count; for (int i = 0; i < SampleLamps.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = SampleLamps[i]; }
                so.ApplyModifiedPropertiesWithoutUndo(); rigs++;
            }
            var fog = root.GetComponentsInChildren<OnlyVolunteers.Map.Look.V3.DistrictFog19V05>(true).FirstOrDefault();
            if (fog) fog.halos = SampleLamps.Select(l => new OnlyVolunteers.Map.Look.V3.DistrictFog19V05.Halo { light = l, position = l.transform.position, size = 2.3f, colour = new Color(.78f, .86f, .91f, .36f) }).ToArray();
            Note($"texture sample night: {SampleLamps.Count} N-R3 lamps on {rigs} night rig(s), fog halos {(fog ? "on" : "no fog")}");
        }

        // ------------------------------------------------------------------ light, atmosphere, tunnel glare (v02 §6)
        static void BuildLight(Transform root)
        {
            var sunGo = new GameObject("Sun"); sunGo.transform.SetParent(root, false);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.25f; sun.color = new Color(1f, .95f, .86f);
            sun.shadows = LightShadows.Soft; sun.shadowStrength = .85f;
            sunGo.transform.rotation = Quaternion.Euler(37f, -35f, 0f);
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.62f, .70f, .78f); RenderSettings.ambientEquatorColor = new Color(.56f, .58f, .54f); RenderSettings.ambientGroundColor = new Color(.36f, .34f, .30f);
            var volGo = new GameObject("Volume_W85"); volGo.transform.SetParent(root, false);
            var vol = volGo.AddComponent<Volume>(); vol.isGlobal = true; vol.priority = 5f;
            var prof = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(prof, Gen + "/W85_VolumeProfile.asset");
            var tm = prof.Add<Tonemapping>(true); tm.mode.overrideState = true; tm.mode.value = TonemappingMode.ACES;
            var ca = prof.Add<ColorAdjustments>(true); ca.saturation.overrideState = true; ca.saturation.value = -15f; ca.contrast.overrideState = true; ca.contrast.value = 8f;
            var bloom = prof.Add<Bloom>(true); bloom.intensity.overrideState = true; bloom.intensity.value = .25f;
            EditorUtility.SetDirty(prof);
            vol.sharedProfile = prof;
            var atm = volGo.AddComponent<W76Atmosphere>();
            atm.Volume = vol; atm.TunnelAxis = TunnelAxis;
            atm.Default = new W76Atmosphere.Zone { Id = "default", FogColor = new Color(.74f, .80f, .84f), FogStart = 60f, FogEnd = 400f, Saturation = -15f };
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/terrain_v85.json")));
            var pads = Obj(Get(tj, "pads"));
            Vector2[] Pad(string k) => V2s(Get(Obj(Get(pads, k)), "poly"));
            Vector2[] Rect(float x0, float y0, float x1, float y1) => new[] { new Vector2(x0, y0), new Vector2(x1, y0), new Vector2(x1, y1), new Vector2(x0, y1) };
            // gamma column of v02 §6 -> exposure (0.80 = +0.25 EV ... 0.50 = -0.55 EV); Rough: low grey sky, fog 120–150 m
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "rough", Polygon = Pad("rough"), Blend = 50f, FogColor = new Color(.58f, .60f, .62f), FogStart = 15f, FogEnd = 140f, Exposure = -.55f, Saturation = -35f, Filter = new Color(.92f, .95f, 1f), Priority = 1f });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "construction", Polygon = Rect(530, 350, 700, 495), Blend = 60f, FogColor = new Color(.86f, .84f, .78f), FogStart = 150f, FogEnd = 700f, Exposure = .35f, Saturation = 0f, Filter = new Color(1f, .97f, .9f), Priority = 1f });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "downtown", Polygon = Pad("downtown"), Blend = 60f, FogColor = new Color(.74f, .82f, .90f), FogStart = 80f, FogEnd = 450f, Exposure = -.1f, Saturation = -10f });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "port", Polygon = Pad("port"), Blend = 60f, FogColor = new Color(.70f, .76f, .80f), FogStart = 40f, FogEnd = 300f, Exposure = -.2f, Saturation = -20f, Filter = new Color(.93f, .97f, 1f) });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "hamlet", Polygon = Rect(200, 370, 450, 610), Blend = 70f, FogColor = new Color(.78f, .86f, .92f), FogStart = 90f, FogEnd = 500f, Exposure = .25f, Saturation = 0f });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "forest", Polygon = Rect(190, 70, 420, 320), Blend = 60f, FogColor = new Color(.66f, .72f, .66f), FogStart = 30f, FogEnd = 260f, Exposure = -.45f, Saturation = -18f });
            atm.Zones.Add(new W76Atmosphere.Zone { Id = "beach", Polygon = Rect(790, 120, 1500, 240), Blend = 50f, FogColor = new Color(.80f, .86f, .92f), FogStart = 120f, FogEnd = 600f, Exposure = .1f, Saturation = 0f });
            // spawn: main road east of the Hamlet, Construction on the left (as W19)
            var spawn = new GameObject("Spawn_W85"); spawn.transform.SetParent(root, false);
            spawn.transform.position = P(new Vector2(520f, 348f), 1.2f);
            spawn.transform.rotation = Quaternion.Euler(0, 90f, 0);
            Note("light: sun 37°, trilight, ACES, sat -15 / contrast +8, district zones (Rough overcast fog, Construction bright), tunnel exit glare");
        }

        // ------------------------------------------------------------------ checks
        static void Validate(Transform root)
        {
            int miss = 0, holes = 0;
            foreach (var mr in root.GetComponentsInChildren<MeshRenderer>(true)) if (!mr.sharedMaterial) miss++;
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == "colliders" && t.GetComponentsInChildren<Collider>().Length == 0) holes++;
            RoofTest(out int rays, out int missed);
            Note(W85FloatCheck.Run(root.gameObject.scene, true).TrimEnd());
            string gf = W85GroundFit.Run(Data, Ter, out int gfErrors);                // W86: footprint ground range > 1.5 m = error
            File.WriteAllText(Gen + "/W85_groundfit.txt", gf);
            Note(gf);
            Note($"validate: renderers without material {miss}, buildings without colliders {holes}, roof rays {rays} (missed {missed}) - details {Gen}/W85_roof_test.txt");
        }

        // ROOF_COLLISION_NOTE check over ALL buildings: (1) a ray straight down every 0.5 m over the footprint must hit this
        // building's colliders at roof level (flat: >= roof - 5 cm; pitched: >= eave - 5 cm); (2) ridge penetration: rays every
        // 0.25 m along the ridge at 0 / +-5 cm across must hit >= ridge - 20 cm, and a 0.3 m sphere (a player's capsule) swept
        // down onto the ridge must stop >= ridge - 50 cm. Hits on other objects (trees, neighbours) are ignored.
        static void RoofTest(out int rays, out int missed)
        {
            Physics.SyncTransforms();
            rays = missed = 0;
            int ridgeRays = 0, ridgeMiss = 0, sweeps = 0, sweepMiss = 0, bad = 0;
            var rep = new StringBuilder("W76 roof collision test (all buildings)\n");
            foreach (var b in Built)
            {
                int r0 = rays, m0 = missed, rr0 = ridgeMiss, s0 = sweepMiss;
                bool pitched = b.Type != "flat" && b.Type != "none";
                float minY = b.Top - .05f, ridge = b.Top;
                Frame(b.Fp, b.Roof, out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
                float ov = F(Get(b.Roof, "overhang_m"), .4f), rh = F(Get(b.Roof, "ridge_h_m"), Mathf.Max(1.5f, hy * .7f));
                if (pitched) { minY = b.Top - ov * rh / Mathf.Max(hy, .5f) - .05f; ridge = b.Top + rh; }
                float x0 = b.Fp.Min(q => q.x), x1 = b.Fp.Max(q => q.x), z0 = b.Fp.Min(q => q.y), z1 = b.Fp.Max(q => q.y);
                for (float x = x0 + .25f; x < x1; x += .5f)
                    for (float z = z0 + .25f; z < z1; z += .5f)
                    {
                        var p = new Vector2(x, z);
                        if (!W76Atmosphere.Inside(b.Fp.ToArray(), p) || W76Atmosphere.Distance(b.Fp.Append(b.Fp[0]).ToArray(), p) < .15f) continue;
                        rays++;
                        if (!HitOwn(b.Go, new Vector3(x, ridge + 30f, z), out float y) || y < minY) missed++;
                    }
                if (pitched)
                {
                    float rx = b.Type == "hip" ? Mathf.Max(0f, hx + ov - (hy + ov)) : b.Type == "pyramid" ? 0f : hx + ov;
                    // along the whole ridge except the last 10 cm at the gable faces (a ray exactly on the hull's end face is a tangent)
                    float r0x = rx > .2f ? -rx + .1f : 0f, r1x = rx > .2f ? rx - .1f : 0f;
                    for (float sAx = r0x; sAx <= r1x + 1e-3f; sAx += .25f)
                        foreach (float v in b.Type == "shed" ? new[] { hy + ov - .3f } : new[] { -.05f, 0f, .05f })
                        {
                            Vector2 q = c + ax * sAx + ay * v;
                            float eav = b.Top - ov * rh / Mathf.Max(hy, .5f), target = b.Type == "shed" ? eav + (b.Top + rh - eav) * (2f * (hy + ov) - .3f) / (2f * (hy + ov)) : ridge;
                            ridgeRays++;
                            if (!HitOwn(b.Go, new Vector3(q.x, target + 10f, q.y), out float y) || y < target - .2f)
                            {
                                ridgeMiss++;
                                rep.AppendLine($"  ridge miss {b.Id} at ({q.x:0.00}, {q.y:0.00}) along {sAx:0.00} across {v:0.00}: hit {(y > float.MinValue ? y.ToString("0.00") : "none")} < ridge {target:0.00}");
                            }
                            if (v != 0f) continue;
                            sweeps++;
                            var hits = Physics.SphereCastAll(new Vector3(q.x, target + 10f, q.y), .3f, Vector3.down, 30f);
                            float best = float.MinValue;
                            foreach (var h in hits) if (h.collider.transform.IsChildOf(b.Go.transform) && h.distance > 0f) best = Mathf.Max(best, target + 10f - h.distance);
                            if (best < target - .5f) sweepMiss++;
                        }
                }
                if (missed > m0 || ridgeMiss > rr0 || sweepMiss > s0)
                {
                    bad++;
                    rep.AppendLine($"FAIL {b.Id} ({b.Type}): grid {missed - m0}/{rays - r0} missed, ridge {ridgeMiss - rr0}, sweep {sweepMiss - s0}");
                }
            }
            rep.Insert(0, $"buildings {Built.Count}, failing {bad}; grid rays {rays} missed {missed}; ridge rays {ridgeRays} missed {ridgeMiss}; ridge sphere sweeps {sweeps} missed {sweepMiss}\n");
            File.WriteAllText(Gen + "/W85_roof_test.txt", rep.ToString());
            Note($"roof test: {Built.Count} buildings, failing {bad}; ridge rays {ridgeRays} (missed {ridgeMiss}), sweeps {sweeps} (missed {sweepMiss})");
        }

        // Highest hit on this building's own colliders straight below `from`.
        static bool HitOwn(GameObject b, Vector3 from, out float y)
        {
            y = float.MinValue;
            foreach (var h in Physics.RaycastAll(from, Vector3.down, 200f))
                if (h.collider.transform.IsChildOf(b.transform)) y = Mathf.Max(y, h.point.y);
            return y > float.MinValue;
        }

        // ------------------------------------------------------------------ minimal JSON (objects, arrays, numbers, strings, bools, null)
        static class Json
        {
            public static object Parse(string s) { int i = 0; return Value(s, ref i); }

            static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

            static object Value(string s, ref int i)
            {
                Ws(s, ref i);
                char c = s[i];
                if (c == '{')
                {
                    var d = new Dictionary<string, object>(); i++;
                    Ws(s, ref i);
                    if (s[i] == '}') { i++; return d; }
                    while (true)
                    {
                        Ws(s, ref i); string k = Str(s, ref i); Ws(s, ref i); i++;      // ':'
                        d[k] = Value(s, ref i); Ws(s, ref i);
                        if (s[i] == ',') { i++; continue; }
                        i++; return d;
                    }
                }
                if (c == '[')
                {
                    var a = new List<object>(); i++;
                    Ws(s, ref i);
                    if (s[i] == ']') { i++; return a; }
                    while (true)
                    {
                        a.Add(Value(s, ref i)); Ws(s, ref i);
                        if (s[i] == ',') { i++; continue; }
                        i++; return a;
                    }
                }
                if (c == '"') return Str(s, ref i);
                if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
                if (s.Length - i >= 5 && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
                if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
                if (s.Length - i >= 3 && string.CompareOrdinal(s, i, "NaN", 0, 3) == 0) { i += 3; return double.NaN; }
                int st = i;
                while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
                return double.Parse(s.Substring(st, i - st), CultureInfo.InvariantCulture);
            }

            static string Str(string s, ref int i)
            {
                var sb = new StringBuilder(); i++;
                while (s[i] != '"')
                {
                    if (s[i] == '\\')
                    {
                        i++;
                        switch (s[i])
                        {
                            case 'n': sb.Append('\n'); break;
                            case 't': sb.Append('\t'); break;
                            case 'r': sb.Append('\r'); break;
                            case 'b': sb.Append('\b'); break;
                            case 'f': sb.Append('\f'); break;
                            case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; break;
                            default: sb.Append(s[i]); break;
                        }
                    }
                    else sb.Append(s[i]);
                    i++;
                }
                i++;
                return sb.ToString();
            }
        }
    }
}
