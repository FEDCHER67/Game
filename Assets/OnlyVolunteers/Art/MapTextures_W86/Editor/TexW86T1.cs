using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Look.V3;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    // Map W86 texture agent T1 (22.10.2026): three texture variants (a / b / c) for every W85 material group of Forest, Hamlet, Rough,
    // Downtown specials and the World (roads, decals, bridges, tunnel, fences, banks, steppe...) with the verdict NO TEXTURE / BAD /
    // OK-NOT-AGREED in Working/Reviews/MapW86_TextureInventory_2026-10-22/INVENTORY.md, on representative geometry, in the playtested
    // i10 / W85 look (sky, sun, district weather, fog +8 %, PostFX_v17) placed on the W85 district rectangles (copy of the v07 look code).
    // One station per inventory code (only that station active while it is captured), variants a / b / c = sibling groups.
    // Textures: MapTextures_W86/T1/Textures (made by ArtSource/Textures/W86_T1/tools/gen_textures_t1.py from ambientCG CC0 sets + own),
    // materials / meshes / prefabs only in MapTextures_W86/T1; existing materials (approved v04 / v07 / W85) are referenced read-only.
    // Map-ready ("slot") materials: Palette19 with _TintRef 1 (the colour is in the texture / _BaseColor, white vertex colour as the
    // generic W85 boxes have) and _BaseMap_ST precompensated for the W85 box UVs (metres / tile of the building's data wall key).
    public static partial class TexW86T1
    {
        const string Root = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1";
        const string Tex = Root + "/Textures";
        const string MatDir = Root + "/Materials";
        const string MeshDir = Root + "/Meshes";
        const string PrefabDir = Root + "/Prefabs";
        const string LookDir = Root + "/Look";
        const string LayerDir = Root + "/TerrainLayers";
        const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/TextureTest_W86_T1.unity";
        const string I10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string ShotDir = "Working/Reviews/MapW86_TexturesAll_2026-10-22/T1/raw";
        const int ShotW = 1280, ShotH = 720;
        const float FogBoost = 1.08f;

        static readonly Dictionary<string, Vector4> Rects = new()
        {
            ["forest"] = new(180, 60, 445, 330), ["village"] = new(185, 365, 470, 625), ["transition"] = new(525, 345, 705, 500),
            ["residential"] = new(655, 668, 1006, 905), ["old_town"] = new(790, 215, 1272, 472), ["industrial"] = new(1165, 595, 1360, 690),
            ["elite"] = new(1342, 258, 1496, 388), ["fields"] = new(520, 60, 665, 300), ["beach"] = new(790, 100, 1520, 228),
            ["tramduro"] = new(1440, 680, 1660, 860),
        };
        // station anchor per district (inside the rect, so the district light / weather / fog applies)
        static readonly Dictionary<string, Vector2> Anchor = new()
        {
            ["forest"] = new(300, 200), ["hamlet"] = new(330, 490), ["rough"] = new(830, 790), ["downtown"] = new(1030, 340),
            ["world"] = new(615, 420), ["valley"] = new(592, 180), ["beach"] = new(1150, 165), ["tramduro"] = new(1550, 770),
        };

        static readonly StringBuilder Log = new();
        static void Note(string s) { Log.AppendLine(s); }

        [MenuItem("OnlyVolunteers/Map/Texture W86 T1/Build TextureTest_W86_T1")]
        public static void BuildMenu() { if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) Build(); }

        [MenuItem("OnlyVolunteers/Map/Texture W86 T1/Capture all")]
        public static void CaptureMenu() => Capture(null);

        // ================================================================== build
        public static void Build() => BuildScene(false);

        // shared editor: build + capture with every other loaded scene's roots hidden (nothing saved there), then restore them
        public static string RunIsolated(string onlyCodes, bool build)
        {
            var hidden = new List<GameObject>();
            var prevActive = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            for (int i = 0; i < EditorSceneManager.sceneCount; i++)
            {
                var sc = EditorSceneManager.GetSceneAt(i);
                if (!sc.isLoaded || sc.path == ScenePath) continue;
                foreach (var g in sc.GetRootGameObjects()) if (g.activeSelf) { g.SetActive(false); hidden.Add(g); }
            }
            UnityEngine.SceneManagement.Scene mine = default;
            var t0 = DateTime.Now;
            try
            {
                if (build) mine = BuildScene(true);
                else { mine = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Additive); EditorSceneManager.SetActiveScene(mine); }
                if (onlyCodes != "none") Capture(onlyCodes == "all" ? null : onlyCodes);
            }
            finally
            {
                if (mine.IsValid() && mine.isLoaded) EditorSceneManager.CloseScene(mine, true);
                foreach (var g in hidden) if (g) g.SetActive(true);
                if (prevActive.IsValid() && prevActive.isLoaded) EditorSceneManager.SetActiveScene(prevActive);
            }
            return $"done in {(DateTime.Now - t0).TotalSeconds:0} s, restored {hidden.Count} roots";
        }

        static UnityEngine.SceneManagement.Scene BuildScene(bool additive)
        {
            Log.Clear(); S.Clear(); MeanCache.Clear(); Stations.Clear(); Manifest.Clear(); TintCache.Clear(); meshN = 0;
            var t0 = DateTime.Now;
            foreach (string f in new[] { MatDir, MeshDir, PrefabDir, LookDir, LayerDir })
                if (AssetDatabase.IsValidFolder(f)) AssetDatabase.DeleteAsset(f);
            foreach (string f in new[] { MatDir, MatDir + "/PropTint", MeshDir, PrefabDir, LookDir, LayerDir }) Folder(f);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, additive ? NewSceneMode.Additive : NewSceneMode.Single);
            if (additive) EditorSceneManager.SetActiveScene(scene);
            var root = new GameObject("TextureTest_W86_T1").transform;
            Surfaces();
            TerrainLayers();
            var cam = Look(root);
            Vector3 sun = ProbeSun(cam);
            Note($"sun direction (towards the sun) {sun}");
            sunDir = sun;
            BuildStations(root);
            // one baked reflection probe per district anchor (sky + ground only)
            foreach (var st in Stations) st.T.gameObject.SetActive(false);
            var probes = new GameObject("Probes").transform; probes.SetParent(root, false);
            foreach (var kv in Anchor)
            {
                if (!Stations.Any(s => s.District == kv.Key)) continue;
                var g = Stations.First(s => s.District == kv.Key);
                g.T.gameObject.SetActive(true); foreach (Transform v in g.T) if (v.name.Length == 1) v.gameObject.SetActive(false);
                Probe(probes, kv.Key, new Vector3(kv.Value.x, 8f, kv.Value.y), new Vector3(160, 60, 160));
                g.T.gameObject.SetActive(false);
            }
            foreach (var st in Stations) { st.T.gameObject.SetActive(true); Show(st, "a"); }
            var first = Stations[0];
            if (first.Shots.Count > 0) cam.transform.SetPositionAndRotation(first.Shots[0].T.position, first.Shots[0].T.rotation);
            Note($"stations {Stations.Count}, meshes {meshN}, materials {S.Values.Select(s => s.M).Distinct().Count()}");
            EditorSceneManager.SaveScene(scene, ScenePath);
            WriteManifest();
            AssetDatabase.SaveAssets();
            Note($"built in {(DateTime.Now - t0).TotalSeconds:0} s");
            File.WriteAllText(Root + "/TexW86T1_build_log.txt", Log.ToString());
            AssetDatabase.ImportAsset(Root + "/TexW86T1_build_log.txt");
            Debug.Log("[TexW86T1] build done\n" + Log);
            return scene;
        }

        static Vector3 sunDir;

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

        static float Hash(string s, int salt = 0)
        {
            unchecked
            {
                int h = 17 + salt * 7919;
                foreach (char c in s) h = h * 31 + c;
                h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15;
                return (h & 0x7fffffff) / (float)int.MaxValue;
            }
        }

        static Color X(string hex) { ColorUtility.TryParseHtmlString("#" + hex.TrimStart('#'), out Color c); return c; }
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_').ToArray());

        // ================================================================== look (copy of TextureTestHousesV07.Look / W85Look, no terrain)
        static Light sunLight;

        static Camera Look(Transform root)
        {
            var look = new GameObject("Look_i10").transform; look.SetParent(root, false);
            var scene = root.gameObject.scene;
            var i10 = EditorSceneManager.OpenScene(I10, OpenSceneMode.Additive);
            GameObject Copy(string path)
            {
                var src = i10.GetRootGameObjects().Select(g => path.Contains('/') ? g.transform.Find(path.Substring(path.IndexOf('/') + 1)) : (g.name == path ? g.transform : null))
                    .FirstOrDefault(t => t && (!path.Contains('/') || t.root.name == path.Substring(0, path.IndexOf('/'))));
                if (!src) { Note("i10 object missing: " + path); return null; }
                var c = Object.Instantiate(src.gameObject);
                c.name = src.name;
                EditorSceneManager.MoveGameObjectToScene(c, scene);
                return c;
            }
            var palette = Copy("V19_ApprovedPalette_Full_v01");
            var skyRig = Copy("G22_DayNight_v04_Integration_i03");
            var wind = Copy("V19Wind");
            var sun = Copy("MapLook_v19_StyleV3/Sun");
            var post = Copy("MapLook_v19_StyleV3/PostFX_v17");
            var camSrc = i10.GetRootGameObjects().FirstOrDefault(g => g.name == "Main Camera")?.GetComponent<Camera>();
            float camFar = camSrc ? camSrc.farClipPlane : 460f, camFov = camSrc ? camSrc.fieldOfView : 70f;
            EditorSceneManager.CloseScene(i10, true);
            foreach (var g in new[] { palette, skyRig, wind, sun, post }) if (g) g.transform.SetParent(look, true);
            sunLight = sun ? sun.GetComponent<Light>() : null;
            RenderSettings.sun = sunLight;
            var world = new Vector4(0, 0, 1744, 950);
            var weather = palette ? palette.GetComponent<DistrictWeather19V05>() : null;
            if (weather)
            {
                weather.sun = sunLight;
                foreach (var d in weather.districts) if (Rects.TryGetValue(d.id, out var r)) d.bounds = r;
                foreach (var v in palette.GetComponentsInChildren<Volume>(true))
                {
                    string id = v.name.Replace("V19_Light_", "");
                    var box = v.GetComponent<BoxCollider>();
                    if (box && Rects.TryGetValue(id, out var r)) { box.center = new Vector3((r.x + r.z) * .5f, 40f, (r.y + r.w) * .5f); box.size = new Vector3(r.z - r.x - 30f, 200f, r.w - r.y - 30f); }
                }
                var fog = weather.visibleFog;
                if (fog)
                {
                    var gh = new Texture2D(8, 8, TextureFormat.RFloat, false, true) { name = "T1_GroundHeights", wrapMode = TextureWrapMode.Clamp };
                    gh.SetPixels(Enumerable.Repeat(new Color(0, 0, 0, 1), 64).ToArray()); gh.Apply();
                    AssetDatabase.CreateAsset(gh, LookDir + "/T1_GroundHeights.asset");
                    fog.terrainWorld = world;
                    fog.groundHeights = gh;
                    fog.halos = Array.Empty<DistrictFog19V05.Halo>();
                    fog.vanHeadlights = Array.Empty<Light>();
                    var i10Rough = new Vector4(550, 554, 824.8f, 696.4f); var i10Forest = new Vector4(127.4f, 81, 346, 315.2f);
                    fog.banks = fog.banks.Select(b =>
                    {
                        Vector4 a = b.forest ? i10Forest : i10Rough, t = b.forest ? Rects["forest"] : Rects["residential"];
                        float u = Mathf.Clamp01((b.position.x - a.x) / (a.z - a.x)), w = Mathf.Clamp01((b.position.z - a.y) / (a.w - a.y));
                        b.position = new Vector3(Mathf.Lerp(t.x + 20, t.z - 20, u), Mathf.Clamp(b.position.y, .8f, 2.5f), Mathf.Lerp(t.y + 20, t.w - 20, w));
                        return b;
                    }).ToArray();
                    fog.roughDensity *= FogBoost; fog.forestDensity *= FogBoost; fog.groundExtinction *= FogBoost;
                    foreach (var dd in weather.districts) dd.fogEnd = dd.fogStart + (dd.fogEnd - dd.fogStart) / FogBoost;
                    Note($"fog x{FogBoost} (W85Look), {fog.banks.Length} mist banks, flat ground heights");
                }
            }
            else Note("district weather missing in i10 copy");
            if (skyRig)
            {
                foreach (var mb in skyRig.GetComponents<MonoBehaviour>())
                {
                    var so = new SerializedObject(mb);
                    var p = so.FindProperty("sun"); if (p != null) p.objectReferenceValue = sunLight;
                    p = so.FindProperty("source"); if (p != null) p.objectReferenceValue = weather;
                    p = so.FindProperty("fog"); if (p != null && weather) p.objectReferenceValue = weather.visibleFog;
                    p = so.FindProperty("lamps"); if (p != null) p.arraySize = 0;
                    p = so.FindProperty("slots"); if (p != null) p.arraySize = 0;
                    so.ApplyModifiedPropertiesWithoutUndo();
                }
                var tpl = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Sky/G22_v04/Generated/PaintedSky_v04.mat");
                if (tpl) RenderSettings.skybox = tpl;
            }
            if (wind)
            {
                var so = new SerializedObject(wind.GetComponents<MonoBehaviour>().First());
                var fr = so.FindProperty("fieldRectangle"); if (fr != null) fr.vector4Value = world;
                var dp = so.FindProperty("districts"); if (dp != null) dp.objectReferenceValue = weather;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            camGo.transform.SetParent(root, false);
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = camFov; cam.farClipPlane = Mathf.Max(camFar, 900f); cam.nearClipPlane = .15f;
            camGo.AddComponent<AudioListener>();
            var ad = camGo.AddComponent<UniversalAdditionalCameraData>(); ad.renderPostProcessing = true; ad.requiresDepthTexture = true; ad.requiresColorTexture = true;
            Note($"i10 look copied; camera FOV {camFov} far {cam.farClipPlane}");
            return cam;
        }

        static Vector3 ProbeSun(Camera cam)
        {
            var rt = new RenderTexture(64, 36, 24);
            cam.targetTexture = rt; cam.Render(); cam.targetTexture = null;
            rt.Release(); Object.DestroyImmediate(rt);
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (mb.GetType().Name != "SkyRenderer22") continue;
                object st = mb.GetType().GetProperty("LastState")?.GetValue(mb);
                object v = st?.GetType().GetField("sunDirection")?.GetValue(st);
                if (v is Vector3 v3 && v3.sqrMagnitude > .01f) return v3.normalized;
                if (v is Vector4 v4 && ((Vector3)v4).sqrMagnitude > .01f) return ((Vector3)v4).normalized;
            }
            return sunLight ? -sunLight.transform.forward : new Vector3(.4f, .7f, -.5f).normalized;
        }

        // station root: the front (local -Z) faces the sun side with the sun ~30 deg to the left (as v07), so front + left end are lit
        static float SunYaw()
        {
            var sh = new Vector3(sunDir.x, 0, sunDir.z); if (sh.sqrMagnitude < 1e-4f) sh = Vector3.back; sh.Normalize();
            var local = new Vector3(-Mathf.Sin(30 * Mathf.Deg2Rad), 0, -Mathf.Cos(30 * Mathf.Deg2Rad));
            return Mathf.Atan2(sh.x, sh.z) * Mathf.Rad2Deg - Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg;
        }

        static void Probe(Transform parent, string name, Vector3 pos, Vector3 size)
        {
            var go = new GameObject("ReflectionProbe_" + name); go.transform.SetParent(parent, false); go.transform.position = pos;
            var p = go.AddComponent<ReflectionProbe>();
            p.size = size; p.resolution = 128; p.hdr = true; p.mode = ReflectionProbeMode.Baked; p.boxProjection = false;
            string path = LookDir + "/T1_Probe_" + name + ".exr";
            if (Lightmapping.BakeReflectionProbe(p, path))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                p.mode = ReflectionProbeMode.Custom; p.customBakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path);
            }
            else Note("reflection probe bake failed: " + name);
        }

        // ================================================================== stations
        sealed class Shot { public string Name; public Transform T; }
        sealed class Station
        {
            public string Code, District, Title; public Transform T; public readonly List<Shot> Shots = new();
            public readonly Dictionary<string, Transform> V = new();
        }
        static readonly List<Station> Stations = new();

        static Station NewStation(Transform root, string code, string district, string title)
        {
            var st = new Station { Code = code, District = district, Title = title };
            var t = new GameObject("ST_" + code).transform; t.SetParent(root, false);
            var a = Anchor[district];
            t.SetPositionAndRotation(new Vector3(a.x, 0, a.y), Quaternion.Euler(0, SunYaw(), 0));
            st.T = t;
            foreach (string v in new[] { "a", "b", "c" }) { var g = new GameObject(v).transform; g.SetParent(t, false); st.V[v] = g; }
            Stations.Add(st);
            return st;
        }

        static void AddShot(Station st, string name, Vector3 pos, Vector3 target)
        {
            var parent = st.T.Find("Shots");
            if (!parent) { parent = new GameObject("Shots").transform; parent.SetParent(st.T, false); }
            var g = new GameObject(name).transform; g.SetParent(parent, false);
            g.localPosition = pos; g.localRotation = Quaternion.LookRotation(target - pos, Vector3.up);
            st.Shots.Add(new Shot { Name = name, T = g });
        }

        static void Show(Station st, string v) { foreach (var kv in st.V) kv.Value.gameObject.SetActive(kv.Key == v); }

        // ================================================================== capture: one station at a time, each variant x shot
        public static void Capture(string onlyCode)
        {
            var cam = Object.FindObjectsByType<Camera>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).FirstOrDefault(c => c.CompareTag("MainCamera"));
            if (!cam) throw new Exception("no main camera; build the scene first");
            Directory.CreateDirectory(ShotDir);
            var keep = (cam.transform.position, cam.transform.rotation);
            var all = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(t => t.name.StartsWith("ST_") && t.parent && t.parent.parent == null).OrderBy(t => t.name).ToList();
            int n = 0;
            foreach (var s in all)
            {
                string code = s.name.Substring(3);
                if (onlyCode != null && !onlyCode.Split(',').Contains(code)) continue;
                foreach (var o in all) o.gameObject.SetActive(o == s);
                var shots = s.Find("Shots");
                foreach (string v in new[] { "a", "b", "c" })
                {
                    foreach (Transform c in s) if (c.name.Length == 1) c.gameObject.SetActive(c.name == v);
                    foreach (Transform sh in shots)
                    {
                        cam.transform.SetPositionAndRotation(sh.position, sh.rotation);
                        Render(cam, Path.Combine(ShotDir, $"{code}_{v}_{sh.name}.png"));
                        n++;
                    }
                }
                foreach (Transform c in s) if (c.name.Length == 1) c.gameObject.SetActive(c.name == "a");
            }
            foreach (var o in all) o.gameObject.SetActive(true);
            cam.transform.SetPositionAndRotation(keep.position, keep.rotation);
            Debug.Log($"[TexW86T1] {n} shots -> {ShotDir}");
        }

        static void Render(Camera cam, string file)
        {
            var rt = new RenderTexture(ShotW, ShotH, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 1 };
            rt.Create();
            cam.targetTexture = rt;
            cam.Render(); cam.Render();
            cam.targetTexture = null;
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var tex = new Texture2D(ShotW, ShotH, TextureFormat.RGB24, false, false);
            tex.ReadPixels(new Rect(0, 0, ShotW, ShotH), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(file, tex.EncodeToPNG());
            Object.DestroyImmediate(tex); rt.Release(); Object.DestroyImmediate(rt);
        }

        // ================================================================== manifest (code -> variant -> role -> material asset path)
        static readonly Dictionary<string, SortedDictionary<string, SortedDictionary<string, string>>> Manifest = new();

        static void Use(string code, string v, string role, string key)
        {
            if (!S.TryGetValue(key, out var s) || !s.M) { Note($"manifest: missing surface {key} ({code}{v} {role})"); return; }
            if (!Manifest.TryGetValue(code, out var cv)) Manifest[code] = cv = new SortedDictionary<string, SortedDictionary<string, string>>();
            if (!cv.TryGetValue(v, out var roles)) cv[v] = roles = new SortedDictionary<string, string>();
            roles[role] = AssetDatabase.GetAssetPath(s.M);
        }

        static void UseAsset(string code, string v, string role, string assetPath)
        {
            if (!Manifest.TryGetValue(code, out var cv)) Manifest[code] = cv = new SortedDictionary<string, SortedDictionary<string, string>>();
            if (!cv.TryGetValue(v, out var roles)) cv[v] = roles = new SortedDictionary<string, string>();
            roles[role] = assetPath;
        }

        static string J(string s) => "\"" + (s ?? "").Replace("\\", "/").Replace("\"", "'") + "\"";

        static void WriteManifest()
        {
            var sb = new StringBuilder("{\n");
            int i = 0;
            foreach (var kv in Manifest.OrderBy(k => k.Key))
            {
                sb.Append($"  {J(kv.Key)}: {{\n");
                int j = 0;
                foreach (var v in kv.Value)
                {
                    sb.Append($"    {J(v.Key)}: {{ ");
                    sb.Append(string.Join(", ", v.Value.Select(r => $"{J(r.Key)}: {J(r.Value)}")));
                    sb.Append(" }" + (++j < kv.Value.Count ? "," : "") + "\n");
                }
                sb.Append("  }" + (++i < Manifest.Count ? "," : "") + "\n");
            }
            sb.Append("}\n");
            File.WriteAllText(Root + "/T1_manifest.json", sb.ToString());
            AssetDatabase.ImportAsset(Root + "/T1_manifest.json");
        }

        // ================================================================== surfaces
        sealed class Surf { public Material M; public float TU = 1, TV = 1; public Color Own = Color.white; public bool NoShadow; }
        static readonly Dictionary<string, Surf> S = new();
        static readonly Dictionary<string, Color> MeanCache = new();

        static string PathOf(string file) => file.StartsWith("Assets/") ? file : Tex + "/" + file;

        // own textures (T1/Textures): importer set here; any other texture is only referenced
        static Texture2D T(string file, bool normal = false, bool alpha = false, int max = 1024, bool coverage = false)
        {
            string p = PathOf(file);
            if (p.StartsWith(Tex + "/"))
            {
                AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceSynchronousImport);
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti)
                {
                    var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    if (ti.textureType != type || ti.sRGBTexture == normal || ti.wrapMode != TextureWrapMode.Repeat || ti.anisoLevel != 8 || ti.maxTextureSize != max
                        || ti.alphaIsTransparency != alpha || !ti.mipmapEnabled || ti.mipMapsPreserveCoverage != coverage)
                    {
                        ti.textureType = type; ti.sRGBTexture = !normal; ti.wrapMode = TextureWrapMode.Repeat; ti.anisoLevel = 8; ti.maxTextureSize = max;
                        ti.mipmapEnabled = true; ti.alphaIsTransparency = alpha; ti.textureCompression = TextureImporterCompression.CompressedHQ;
                        ti.mipMapsPreserveCoverage = coverage; if (coverage) ti.alphaTestReferenceValue = .5f;
                        if (alpha) ti.alphaSource = TextureImporterAlphaSource.FromInput;
                        ti.SaveAndReimport();
                    }
                }
            }
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(p);
            if (!t) throw new Exception("texture missing: " + p);
            return t;
        }

        static Color MeanOf(string p)
        {
            if (MeanCache.TryGetValue(p, out var c)) return c;
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            t.LoadImage(File.ReadAllBytes(p));
            var px = t.GetPixels32();
            double r = 0, g = 0, b = 0; int n = 0;
            for (int i = 0; i < px.Length; i += 29) { r += px[i].r; g += px[i].g; b += px[i].b; n++; }
            Object.DestroyImmediate(t);
            return MeanCache[p] = new Color((float)(r / n / 255), (float)(g / n / 255), (float)(b / n / 255), 1f);
        }

        static Material NewP(string key) => new(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "T1_" + key, enableInstancing = true };

        static Surf Save(string key, Surf s)
        {
            AssetDatabase.CreateAsset(s.M, MatDir + "/T1_" + key + ".mat");
            return S[key] = s;
        }

        static void PalCommon(Material m, Texture2D tex, string normal, float bump, float smooth, float metal, int max)
        {
            m.SetTexture("_BaseMap", tex); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            if (normal != null)
            {
                var nt = T(normal, true, false, max);
                if (nt) { m.SetTexture("_BumpMap", nt); m.SetFloat("_UseNormalMap", 1f); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", bump); }
            }
        }

        // vertex-colour driven kit material (as v07): colour per face = vertex colour relative to the texture mean; ST 1, UV = metres / tile
        static Surf Kit(string key, string albedo, float tile, string normal = null, float bump = .5f, float smooth = .12f, float metal = 0f, int max = 1024)
        {
            if (S.ContainsKey(key)) return S[key];
            var tex = T(albedo, false, false, max);
            var m = NewP(key);
            PalCommon(m, tex, normal, bump, smooth, metal, max);
            Color own = MeanOf(PathOf(albedo));
            m.SetVector("_TintRef", (Vector4)own.linear);
            return Save(key, new Surf { M = m, TU = tile, TV = tile, Own = own });
        }

        // map-ready material: colour in the texture (or _BaseColor), _TintRef 1 (white vertex colour), ST = t0 / tile for UV = metres / t0
        static Surf MapM(string key, string albedo, float tile, float t0, string normal = null, float bump = .5f, float smooth = .12f, float metal = 0f, string hex = null, int max = 1024, float tileV = 0f)
        {
            if (S.ContainsKey(key)) return S[key];
            var tex = T(albedo, false, false, max);
            var m = NewP(key);
            PalCommon(m, tex, normal, bump, smooth, metal, max);
            m.SetVector("_TintRef", Vector4.one);
            if (tileV <= 0f) tileV = tile;
            m.SetTextureScale("_BaseMap", new Vector2(t0 / tile, t0 / tileV));
            if (hex != null)
            {
                Color mean = MeanOf(PathOf(albedo)).linear, want = X(hex).linear;
                var bl = new Color(want.r / Mathf.Max(mean.r, .02f), want.g / Mathf.Max(mean.g, .02f), want.b / Mathf.Max(mean.b, .02f), 1f);
                m.SetColor("_BaseColor", bl.gamma);
            }
            return Save(key, new Surf { M = m, TU = t0, TV = t0, Own = Color.white });
        }

        static Surf Flat(string key, float smooth, float metal = 0f)
        {
            if (S.ContainsKey(key)) return S[key];
            var m = NewP(key);
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal); m.SetVector("_TintRef", Vector4.one); m.SetFloat("_MacroStrength", .02f);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            return Save(key, new Surf { M = m });
        }

        // existing approved material, referenced read-only: Own = its texture mean (gamma of _TintRef) so white-equivalent colour is its own
        static Surf Ref(string key, string matPath, float tu, float tv)
        {
            if (S.ContainsKey(key)) return S[key];
            var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (!m) throw new Exception("material missing: " + matPath);
            Color own = Color.white;
            if (m.HasProperty("_TintRef")) { var v = m.GetVector("_TintRef"); own = new Color(v.x, v.y, v.z, 1f).gamma; }
            return S[key] = new Surf { M = m, TU = tu, TV = tv, Own = own };
        }

        // URP Lit: mode 0 opaque, 1 alpha clip, 2 transparent
        static Surf Lit(string key, Color col, Texture tex, float tu, float tv, float smooth, float metal, int mode, bool twoSided = false, bool noShadow = false, Texture normal = null)
        {
            if (S.ContainsKey(key)) return S[key];
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "T1_" + key, enableInstancing = true };
            m.SetColor("_BaseColor", col);
            if (tex) m.SetTexture("_BaseMap", tex);
            if (normal) { m.SetTexture("_BumpMap", normal); m.EnableKeyword("_NORMALMAP"); }
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (mode == 1) { m.SetFloat("_AlphaClip", 1f); m.SetFloat("_Cutoff", .5f); m.EnableKeyword("_ALPHATEST_ON"); m.renderQueue = (int)RenderQueue.AlphaTest; }
            if (mode == 2)
            {
                m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f); m.SetOverrideTag("RenderType", "Transparent");
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f); m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.renderQueue = (int)RenderQueue.Transparent;
                m.SetShaderPassEnabled("ShadowCaster", false);
            }
            if (twoSided) { m.SetFloat("_Cull", 0f); m.doubleSidedGI = true; }
            return Save(key, new Surf { M = m, TU = tu, TV = tv, Own = Color.white, NoShadow = noShadow || mode == 2 });
        }

        static Surf Emit(string key, Color col, float intensity, Texture tex = null, int mode = 0)
        {
            if (S.ContainsKey(key)) return S[key];
            var s = Lit(key, col, tex, 1, 1, .3f, 0, mode, mode != 0, true);
            s.M.EnableKeyword("_EMISSION"); s.M.SetColor("_EmissionColor", col * intensity);
            if (tex) s.M.SetTexture("_EmissionMap", tex);
            s.M.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            EditorUtility.SetDirty(s.M);
            return s;
        }

        // copy of an existing material with edits (water variants etc.)
        static Surf CopyOf(string key, string srcPath, Action<Material> edit, float tu = 1f, float tv = 1f, bool noShadow = true)
        {
            if (S.ContainsKey(key)) return S[key];
            var src = AssetDatabase.LoadAssetAtPath<Material>(srcPath);
            if (!src) throw new Exception("material missing: " + srcPath);
            var m = new Material(src) { name = "T1_" + key };
            edit?.Invoke(m);
            return Save(key, new Surf { M = m, TU = tu, TV = tv, NoShadow = noShadow });
        }

        // PropTint: prefab instance with every material swapped for a tinted copy (b / c variants of the palette props)
        static readonly Dictionary<string, Material> TintCache = new();

        static GameObject Prop(string path, Transform parent, Vector3 pos, float yaw, float scale = 1f, Color? tint = null, string tag = null)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!asset) { Note("prop missing: " + path); return null; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent);
            go.transform.localPosition = pos; go.transform.localRotation = Quaternion.Euler(0, yaw, 0); go.transform.localScale = Vector3.one * scale;
            if (tint is Color t)
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    var mats = r.sharedMaterials;
                    for (int i = 0; i < mats.Length; i++)
                    {
                        if (!mats[i]) continue;
                        string k = mats[i].name + "_" + tag;
                        if (!TintCache.TryGetValue(k, out var tm))
                        {
                            tm = new Material(mats[i]) { name = "T1_" + Safe(k) };
                            string prop = tm.HasProperty("_BaseColor") ? "_BaseColor" : tm.HasProperty("_Color") ? "_Color" : null;
                            if (prop != null) { var c0 = tm.GetColor(prop); tm.SetColor(prop, new Color(c0.r * t.r, c0.g * t.g, c0.b * t.b, c0.a)); }
                            AssetDatabase.CreateAsset(tm, MatDir + "/PropTint/T1_" + Safe(k) + ".mat");
                            TintCache[k] = tm;
                        }
                        mats[i] = tm;
                    }
                    r.sharedMaterials = mats;
                }
            return go;
        }

        // terrain layers for the integrator (banks, fields, steppe backdrop, ballast): diffuse + normal + tile size
        static void TerrainLayers()
        {
            foreach (var (name, alb, nrm, tile, code, v, role) in new[]
            {
                ("T1_L_bank_mud", "T1_bank_mud_albedo.png", "T1_bank_mud_normal.png", 4f, "T06", "b", "terrain layer (bank band)"),
                ("T1_L_bank_pebbles", "T1_bank_pebbles_albedo.png", "T1_bank_pebbles_normal.png", 3f, "T06", "c", "terrain layer (bank band)"),
                ("T1_L09b_field_plowed", "T1_field_plowed_b_albedo.png", "T1_field_plowed_b_normal.png", 4f, "T21", "b", "terrain layer L09"),
                ("T1_L10b_field_stubble", "T1_field_stubble_b_albedo.png", "T1_field_stubble_normal.png", 4f, "T21", "b", "terrain layer L10"),
                ("T1_L09c_field_plowed", "T1_field_plowed_c_albedo.png", "T1_field_plowed_b_normal.png", 4f, "T21", "c", "terrain layer L09"),
                ("T1_L10c_field_stubble", "T1_field_stubble_c_albedo.png", "T1_field_stubble_normal.png", 4f, "T21", "c", "terrain layer L10"),
                ("T1_L_steppe_b", "T1_steppe_macro_albedo.png", null, 64f, "T132", "b", "terrain layer (steppe backdrop)"),
                ("T1_L_steppe_c", "T1_steppe_macro_warm_albedo.png", null, 64f, "T132", "c", "terrain layer (steppe backdrop)"),
                ("T1_L_ballast_brown", "T1_ballast_brown_albedo.png", "T1_ballast_normal.png", 2f, "X01", "b", "terrain layer (track bed, optional)"),
            })
            {
                var l = new TerrainLayer { diffuseTexture = T(alb), tileSize = new Vector2(tile, tile) };
                if (nrm != null) { l.normalMapTexture = T(nrm, true); l.normalScale = .6f; }
                l.smoothness = 0f; l.metallic = 0f;
                string p = LayerDir + "/" + name + ".terrainlayer";
                AssetDatabase.CreateAsset(l, p);
                UseAsset(code, v, role, p);
                foreach (string c2 in code == "T06" ? new[] { "T22", "T129" } : new string[0]) UseAsset(c2, v, role, p);
            }
        }

        // ================================================================== geometry (one mesh per variant group, a submesh per surface)
        sealed class MB
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> U = new(); public readonly List<Color> C = new(); public readonly List<int> Tr = new();
            public void Tri(Vector3 a, Vector3 b, Vector3 c, Vector2 ua, Vector2 ub, Vector2 uc, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); U.Add(ua); U.Add(ub); U.Add(uc); C.Add(col); C.Add(col); C.Add(col);
                Tr.Add(n); Tr.Add(n + 1); Tr.Add(n + 2);
            }
        }

        sealed class Batch
        {
            public readonly Dictionary<string, MB> ByKey = new();
            public MB this[string k] { get { if (!ByKey.TryGetValue(k, out var mb)) ByKey[k] = mb = new MB(); return mb; } }
        }

        static int meshN;

        static GameObject Flush(Batch b, Transform parent, string name)
        {
            var keys = b.ByKey.Where(kv => kv.Value.V.Count > 0).Select(kv => kv.Key).ToList();
            if (keys.Count == 0) return null;
            var shadowKeys = keys.Where(k => !S[k].NoShadow).ToList();
            var noShadowKeys = keys.Where(k => S[k].NoShadow).ToList();
            GameObject first = null;
            foreach (var (set, suffix, cast) in new[] { (shadowKeys, "", true), (noShadowKeys, "_ns", false) })
            {
                if (set.Count == 0) continue;
                var mesh = new Mesh { name = name + suffix };
                var V = new List<Vector3>(); var U = new List<Vector2>(); var C = new List<Color>();
                var subs = new List<List<int>>();
                foreach (var k in set)
                {
                    if (!S.ContainsKey(k)) throw new Exception("surface missing: " + k);
                    var mb = b.ByKey[k]; int o = V.Count;
                    V.AddRange(mb.V); U.AddRange(mb.U); C.AddRange(mb.C);
                    subs.Add(mb.Tr.Select(i => i + o).ToList());
                }
                mesh.indexFormat = V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
                mesh.SetVertices(V); mesh.SetUVs(0, U); mesh.SetColors(C);
                mesh.subMeshCount = subs.Count;
                for (int i = 0; i < subs.Count; i++) mesh.SetTriangles(subs[i], i);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, MeshDir + "/" + Safe(mesh.name) + ".asset"); meshN++;
                var go = new GameObject(mesh.name); go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterials = set.Select(k => S[k].M).ToArray();
                if (!cast) r.shadowCastingMode = ShadowCastingMode.Off;
                first ??= go;
            }
            b.ByKey.Clear();
            return first;
        }

        // quad with an explicit outward normal (winding fixed to face it); uv per corner
        static void Q(Batch b, string key, Vector3 a, Vector3 c1, Vector3 c2, Vector3 d, Vector3 n, Vector2 ua, Vector2 u1, Vector2 u2, Vector2 ud, Color col)
        {
            var mb = b[key];
            if (Vector3.Dot(Vector3.Cross(c1 - a, c2 - a), n) >= 0) { mb.Tri(a, c1, c2, ua, u1, u2, col); mb.Tri(a, c2, d, ua, u2, ud, col); }
            else { mb.Tri(a, c2, c1, ua, u2, u1, col); mb.Tri(a, d, c2, ua, ud, u2, col); }
        }

        static void TriN(Batch b, string key, Vector3 a, Vector3 c1, Vector3 c2, Vector3 n, Vector2 ua, Vector2 u1, Vector2 u2, Color col)
        {
            var mb = b[key];
            if (Vector3.Dot(Vector3.Cross(c1 - a, c2 - a), n) >= 0) mb.Tri(a, c1, c2, ua, u1, u2, col); else mb.Tri(a, c2, c1, ua, u2, u1, col);
        }

        // planar face: origin o, axes ex (u) and ey (v) with lengths, outward normal = n; uv = metres / tile (+ offsets)
        static void Face(Batch b, string key, Vector3 o, Vector3 ex, float lx, Vector3 ey, float ly, Vector3 n, Color col, float u0 = 0f, float v0 = 0f)
        {
            var s = S[key];
            Vector3 a = o, c1 = o + ex * lx, c2 = o + ex * lx + ey * ly, d = o + ey * ly;
            Q(b, key, a, c1, c2, d, n, new Vector2(u0 / s.TU, v0 / s.TV), new Vector2((u0 + lx) / s.TU, v0 / s.TV), new Vector2((u0 + lx) / s.TU, (v0 + ly) / s.TV), new Vector2(u0 / s.TU, (v0 + ly) / s.TV), col);
        }

        // oriented box: centre c, unit axes X / Y / Z, size along them; side faces v = world height
        static void OBox(Batch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, Vector3 size, Color col, bool bottom = false)
        {
            Vector3 hx = Xa * size.x * .5f, hy = Ya * size.y * .5f, hz = Za * size.z * .5f;
            float y0 = (c - hy).y;
            // +Z / -Z faces (u along X)
            Face(b, key, c - hx - hy + hz, Xa, size.x, Ya, size.y, Za, col, 0, y0);
            Face(b, key, c - hx - hy - hz, Xa, size.x, Ya, size.y, -Za, col, 0, y0);
            Face(b, key, c + hx - hy - hz, Za, size.z, Ya, size.y, Xa, col, 0, y0);
            Face(b, key, c - hx - hy - hz, Za, size.z, Ya, size.y, -Xa, col, 0, y0);
            Face(b, key, c - hx + hy - hz, Xa, size.x, Za, size.z, Ya, col, (c - hx).x, (c - hz).z);
            if (bottom) Face(b, key, c - hx - hy - hz, Xa, size.x, Za, size.z, -Ya, col);
        }

        static void Box(Batch b, string key, Vector3 c, Vector3 size, Color col, float yaw = 0f, bool bottom = false)
        {
            var q = Quaternion.Euler(0, yaw, 0);
            OBox(b, key, c, q * Vector3.right, Vector3.up, q * Vector3.forward, size, col, bottom);
        }

        static void BoxMM(Batch b, string key, Vector3 min, Vector3 max, Color col) => Box(b, key, (min + max) * .5f, max - min, col);

        // cylinder between p0 and p1 (radius r, n sides); uv side = arc metres / TU x length / TV, or into an atlas rect (side / cap)
        static void Cyl(Batch b, string key, Vector3 p0, Vector3 p1, float r, int n, Color col, bool caps = true, float r1 = -1f, Rect? sideUV = null, Rect? capUV = null, string capKey = null)
        {
            if (r1 < 0) r1 = r;
            var s = S[key];
            Vector3 ax = (p1 - p0); float L = ax.magnitude; ax /= L;
            Vector3 e1 = Vector3.Cross(ax, Mathf.Abs(ax.y) < .9f ? Vector3.up : Vector3.right).normalized, e2 = Vector3.Cross(ax, e1);
            for (int i = 0; i < n; i++)
            {
                float a0 = i * Mathf.PI * 2 / n, a1 = (i + 1) * Mathf.PI * 2 / n;
                Vector3 d0 = e1 * Mathf.Cos(a0) + e2 * Mathf.Sin(a0), d1 = e1 * Mathf.Cos(a1) + e2 * Mathf.Sin(a1);
                Vector2 ua, ub, uc, ud;
                if (sideUV is Rect su)
                {
                    float f0 = (float)i / n, f1 = (float)(i + 1) / n;
                    ua = new Vector2(su.x + su.width * f0, su.y); ub = new Vector2(su.x + su.width * f1, su.y);
                    uc = new Vector2(su.x + su.width * f1, su.yMax); ud = new Vector2(su.x + su.width * f0, su.yMax);
                }
                else
                {
                    float c0 = a0 * r, c1 = a1 * r;
                    ua = new Vector2(c0 / s.TU, 0); ub = new Vector2(c1 / s.TU, 0); uc = new Vector2(c1 / s.TU, L / s.TV); ud = new Vector2(c0 / s.TU, L / s.TV);
                }
                Vector3 nn = (d0 + d1).normalized;
                Q(b, key, p0 + d0 * r, p0 + d1 * r, p1 + d1 * r1, p1 + d0 * r1, nn, ua, ub, uc, ud, col);
            }
            if (!caps) return;
            string ck = capKey ?? key; var cs = S[ck];
            foreach (var (pc, rr, nrm) in new[] { (p1, r1, ax), (p0, r, -ax) })
            {
                for (int i = 0; i < n; i++)
                {
                    float a0 = i * Mathf.PI * 2 / n, a1 = (i + 1) * Mathf.PI * 2 / n;
                    Vector3 d0 = e1 * Mathf.Cos(a0) + e2 * Mathf.Sin(a0), d1 = e1 * Mathf.Cos(a1) + e2 * Mathf.Sin(a1);
                    Vector2 Uc(Vector3 d, float k)
                    {
                        if (capUV is Rect cu) return new Vector2(cu.center.x + Vector3.Dot(d, e1) * k * cu.width * .5f, cu.center.y + Vector3.Dot(d, e2) * k * cu.height * .5f);
                        return new Vector2(Vector3.Dot(d, e1) * rr * k / cs.TU, Vector3.Dot(d, e2) * rr * k / cs.TV);
                    }
                    TriN(b, ck, pc, pc + d0 * rr, pc + d1 * rr, nrm, Uc(Vector3.zero, 0), Uc(d0, 1), Uc(d1, 1), col);
                }
            }
        }

        // wall with rectangular openings (face frame: origin o = outer bottom-left, ex along the wall, F = inward); holes in (x, y) wall
        // coordinates (y absolute); reveals of depth `recess`
        static void HoleWall(Batch b, string key, Vector3 o, Vector3 ex, Vector3 F, float L, float y0, float y1, List<Rect> holes, float recess, Color col, float u0 = 0f)
        {
            var xs = new List<float> { 0, L }; var ys = new List<float> { y0, y1 };
            foreach (var h in holes) { xs.Add(h.xMin); xs.Add(h.xMax); ys.Add(h.yMin); ys.Add(h.yMax); }
            xs = xs.Where(x => x >= 0 && x <= L).Distinct().OrderBy(x => x).ToList(); ys = ys.Where(y => y >= y0 && y <= y1).Distinct().OrderBy(y => y).ToList();
            Vector3 n = -F;
            for (int i = 0; i + 1 < xs.Count; i++)
                for (int j = 0; j + 1 < ys.Count; j++)
                {
                    var c = new Vector2((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2);
                    if (holes.Any(h => h.Contains(c))) continue;
                    Face(b, key, o + ex * xs[i] + Vector3.up * (ys[j] - o.y), ex, xs[i + 1] - xs[i], Vector3.up, ys[j + 1] - ys[j], n, col, u0 + xs[i], ys[j]);
                }
            foreach (var h in holes)
            {
                Vector3 bl = o + ex * h.xMin + Vector3.up * (h.yMin - o.y), br = o + ex * h.xMax + Vector3.up * (h.yMin - o.y);
                Face(b, key, bl, F, recess, Vector3.up, h.height, ex, col);                       // left reveal (faces +ex)
                Face(b, key, br, F, recess, Vector3.up, h.height, -ex, col);                      // right reveal
                Face(b, key, bl + Vector3.up * h.height, ex, h.width, F, recess, -Vector3.up, col); // head
                Face(b, key, bl, ex, h.width, F, recess, Vector3.up, col);                         // sill reveal
            }
        }

        static Vector3 FP(Vector3 o, Vector3 ex, Vector3 F, float x, float y, float z) => o + ex * x + Vector3.up * (y - o.y) + F * z;

        // box in a face frame (x along the wall, y absolute height, z inward; size x / y / z)
        static void FBox(Batch b, string key, Vector3 o, Vector3 ex, Vector3 F, float x, float y, float z, Vector3 size, Color col)
            => OBox(b, key, FP(o, ex, F, x, y, z), ex, Vector3.up, F, size, col);

        // gable roof over x0..x1 / z0..z1 with the ridge along X (alongX) or Z; gable triangles in wallKey (null = none)
        static void Gable(Batch b, string key, string wallKey, float x0, float x1, float z0, float z1, float eave, float ridge, float over, bool alongX, Color col, Color wallCol)
        {
            if (!alongX)
            {   // swap axes by building in a rotated frame: reuse the alongX code with x <-> z
                GableZ(b, key, wallKey, x0, x1, z0, z1, eave, ridge, over, col, wallCol); return;
            }
            float zm = (z0 + z1) / 2, half = (z1 - z0) / 2 + over, drop = over * (ridge - eave) / ((z1 - z0) / 2);
            Vector3 r0 = new(x0 - over, ridge, zm), r1 = new(x1 + over, ridge, zm);
            foreach (int sgn in new[] { -1, 1 })
            {
                Vector3 e0 = new(x0 - over, eave - drop, zm + sgn * half), e1 = new(x1 + over, eave - drop, zm + sgn * half);
                Vector3 n = Vector3.Cross(r1 - r0, e0 - r0).normalized; if (n.y < 0) n = -n;
                float slope = Vector3.Distance(r0, e0); var s = S[key];
                Q(b, key, e0, e1, r1, r0, n, new Vector2(0, 0), new Vector2((x1 - x0 + 2 * over) / s.TU, 0), new Vector2((x1 - x0 + 2 * over) / s.TU, slope / s.TV), new Vector2(0, slope / s.TV), col);
                Q(b, key, e0 + Vector3.down * .06f, e1 + Vector3.down * .06f, r1 + Vector3.down * .06f, r0 + Vector3.down * .06f, -n, Vector2.zero, Vector2.right, Vector2.one, Vector2.up, col * .7f);
            }
            if (wallKey == null) return;
            var ws = S[wallKey];
            foreach (float x in new[] { x0, x1 })
            {
                Vector3 a = new(x, eave, z0), c = new(x, eave, z1), t = new(x, ridge, zm);
                Vector3 n = x == x0 ? Vector3.left : Vector3.right;
                TriN(b, wallKey, a, c, t, n, new Vector2(z0 / ws.TU, eave / ws.TV), new Vector2(z1 / ws.TU, eave / ws.TV), new Vector2(zm / ws.TU, ridge / ws.TV), wallCol);
            }
        }

        static void GableZ(Batch b, string key, string wallKey, float x0, float x1, float z0, float z1, float eave, float ridge, float over, Color col, Color wallCol)
        {
            float xm = (x0 + x1) / 2, half = (x1 - x0) / 2 + over, drop = over * (ridge - eave) / ((x1 - x0) / 2);
            Vector3 r0 = new(xm, ridge, z0 - over), r1 = new(xm, ridge, z1 + over);
            var s = S[key];
            foreach (int sgn in new[] { -1, 1 })
            {
                Vector3 e0 = new(xm + sgn * half, eave - drop, z0 - over), e1 = new(xm + sgn * half, eave - drop, z1 + over);
                Vector3 n = Vector3.Cross(r1 - r0, e0 - r0).normalized; if (n.y < 0) n = -n;
                float slope = Vector3.Distance(r0, e0);
                Q(b, key, e0, e1, r1, r0, n, new Vector2(0, 0), new Vector2((z1 - z0 + 2 * over) / s.TU, 0), new Vector2((z1 - z0 + 2 * over) / s.TU, slope / s.TV), new Vector2(0, slope / s.TV), col);
                Q(b, key, e0 + Vector3.down * .06f, e1 + Vector3.down * .06f, r1 + Vector3.down * .06f, r0 + Vector3.down * .06f, -n, Vector2.zero, Vector2.right, Vector2.one, Vector2.up, col * .7f);
            }
            if (wallKey == null) return;
            var ws = S[wallKey];
            foreach (float z in new[] { z0, z1 })
            {
                Vector3 a = new(x0, eave, z), c = new(x1, eave, z), t = new(xm, ridge, z);
                Vector3 n = z == z0 ? Vector3.back : Vector3.forward;
                TriN(b, wallKey, a, c, t, n, new Vector2(x0 / ws.TU, eave / ws.TV), new Vector2(x1 / ws.TU, eave / ws.TV), new Vector2(xm / ws.TU, ridge / ws.TV), wallCol);
            }
        }

        // mono-pitch roof slab (high side at z0 or z1)
        static void ShedRoof(Batch b, string key, float x0, float x1, float z0, float z1, float yLow, float yHigh, float over, bool highAtZ0, Color col)
        {
            float za = z0 - over, zb = z1 + over;
            float ya = highAtZ0 ? yHigh : yLow, yb2 = highAtZ0 ? yLow : yHigh;
            float k = (yb2 - ya) / (z1 - z0);
            ya -= k * over; yb2 += k * over;
            Vector3 a = new(x0 - over, ya, za), c1 = new(x1 + over, ya, za), c2 = new(x1 + over, yb2, zb), d = new(x0 - over, yb2, zb);
            var s = S[key]; float L = Vector3.Distance(a, d);
            Q(b, key, a, c1, c2, d, Vector3.up, Vector2.zero, new Vector2((x1 - x0 + 2 * over) / s.TU, 0), new Vector2((x1 - x0 + 2 * over) / s.TU, L / s.TV), new Vector2(0, L / s.TV), col);
            Q(b, key, a + Vector3.down * .08f, c1 + Vector3.down * .08f, c2 + Vector3.down * .08f, d + Vector3.down * .08f, Vector3.down, Vector2.zero, Vector2.right, Vector2.one, Vector2.up, col * .7f);
        }

        // ground plane (station-local), metres UV
        static void Ground(Batch b, string key, float x0, float z0, float x1, float z1, float y, Color col)
            => Face(b, key, new Vector3(x0, y, z0), Vector3.right, x1 - x0, Vector3.forward, z1 - z0, Vector3.up, col, x0, z0);

        // prefab from a built group (meshes are assets)
        static string MakePrefab(GameObject go, string name)
        {
            string p = PrefabDir + "/" + name + ".prefab";
            var clone = Object.Instantiate(go); clone.name = name;
            clone.transform.position = Vector3.zero; clone.transform.rotation = Quaternion.identity;
            PrefabUtility.SaveAsPrefabAsset(clone, p);
            Object.DestroyImmediate(clone);
            return p;
        }
    }
}
