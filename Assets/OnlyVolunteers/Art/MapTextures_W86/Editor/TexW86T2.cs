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
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    // Map W86 texture pass, agent T2 (22.10.2026): Construction, Port, Elite, Quiet Valley, Beach, Tramduro. Every material group of
    // Working/Reviews/MapW86_TextureInventory_2026-10-22/INVENTORY.md in these districts with the verdict NO TEXTURE / BAD / OK-NOT-AGREED
    // (minus the v07 sets Fedya already chose: P1/P3, E2, C2, Q3) gets three variants a / b / c, one picked by Fedya's taste guide.
    // Scene TextureTest_W86_T2: one stage per group on its district's W85 rectangle (the playtested i10 look: district light / fog +8 %),
    // the three variants are sibling groups (one active); Capture renders every group x variant x shot into the T2 review folder.
    // Materials: shared Palette19 surfaces coloured per face by vertex colour (as the approved v04 / v07 sets) for the geometry that
    // the generators below build (public Generate(...) for the integrator: same code, any footprint), plus "map" materials (T2M_*,
    // _TintRef 1, colour in _BaseColor, tiling matched to the W85 builder UVs) that can be put straight onto existing W85 renderers
    // (piers, yards, pools, decks, bridge, fences). Prefab props (umbrellas, loungers, lifeguard towers, palms) get material sets.
    // Textures: MapTextures_W86/T2/Textures (gen_textures_t2.py from CC0 ambientCG / Poly Haven + own) and existing project textures
    // referenced read-only (TextureTest v03 / v04 / v07, StyleKit, map detail textures). Nothing outside MapTextures_W86/T2 and the
    // own scene is written.
    public static partial class TexW86T2
    {
        public const string Root = "Assets/OnlyVolunteers/Art/MapTextures_W86/T2";
        const string Tex = Root + "/Textures";
        const string MatDir = Root + "/Materials";
        const string MeshDir = Root + "/Meshes";
        const string LookDir = Root + "/Look";
        const string PrefabDir = Root + "/Prefabs";
        const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/TextureTest_W86_T2.unity";
        const string I10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string SK = "Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/";
        const string TT = "Assets/OnlyVolunteers/Art/TextureTest_v01/";
        const string V07 = TT + "Source_v07/";
        const string MP = "Assets/OnlyVolunteers/Art/Map/Prefabs/";
        const string ShotDir = "Working/Reviews/MapW86_TexturesAll_2026-10-22/T2/raw";
        const int ShotW = 1280, ShotH = 720;
        const float FogBoost = 1.08f;

        static readonly Dictionary<string, Vector4> Rects = new()
        {
            ["forest"] = new(180, 60, 445, 330), ["village"] = new(185, 365, 470, 625), ["transition"] = new(525, 345, 705, 500),
            ["residential"] = new(655, 668, 1006, 905), ["old_town"] = new(790, 215, 1272, 472), ["industrial"] = new(1165, 595, 1360, 690),
            ["elite"] = new(1342, 258, 1496, 388), ["fields"] = new(520, 60, 665, 300), ["beach"] = new(790, 100, 1520, 228),
            ["tramduro"] = new(1440, 680, 1660, 860),
        };
        // district stages (W85 world x / z inside the district rectangle, so the district light / fog of the look applies)
        static readonly (string name, Vector2 at)[] Districts =
        {
            ("Construction", new(615, 422)), ("Port", new(1262, 642)), ("Elite", new(1419, 323)), ("Valley", new(592, 180)),
            ("Beach", new(1000, 165)), ("Tramduro", new(1550, 770)),
        };
        static readonly string[] Vars = { "a", "b", "c" };

        static readonly StringBuilder Log = new();
        static void Note(string s) { Log.AppendLine(s); }

        // ================================================================== menu / batch
        [MenuItem("OnlyVolunteers/Map/W86 Textures T2/Build TextureTest_W86_T2")]
        public static void BuildMenu() { if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) Build(); }

        [MenuItem("OnlyVolunteers/Map/W86 Textures T2/Capture all")]
        public static void CaptureMenu() => Capture(null);

        public static void BatchRun()
        {
            int code = 0;
            try { Build(); Capture(null); }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        // ================================================================== build
        public static void Build()
        {
            Log.Clear(); S.Clear(); MeanCache.Clear(); meshN = 0; UsedProps.Clear(); PropMats.Clear();
            var t0 = DateTime.Now;
            foreach (string f in new[] { MatDir, MeshDir, LookDir, PrefabDir }) if (AssetDatabase.IsValidFolder(f)) AssetDatabase.DeleteAsset(f);
            foreach (string f in new[] { MatDir, MatDir + "/Map", MatDir + "/Props", MeshDir, LookDir, PrefabDir }) Folder(f);
            // shared editor: never close / discard somebody else's scene. The test scene is opened ADDITIVELY and made active; the other
            // loaded scenes' roots are switched off (states saved to Temp, restored by Finish()) so they do not show in the shots.
            // NEVER NewSceneMode.Single while another real scene is loaded (it would discard its unsaved changes without asking)
            var others = new List<Scene>();
            for (int i = 0; i < SceneManager.sceneCount; i++) { var sc = SceneManager.GetSceneAt(i); if (sc.path != ScenePath) others.Add(sc); }
            var act = SceneManager.GetActiveScene();
            var prev = act.path != ScenePath ? act : others.FirstOrDefault();
            var openTest = SceneManager.GetSceneByPath(ScenePath);
            if (openTest.IsValid() && openTest.isLoaded)
            {
                if (others.Count == 0) EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);   // only the test scene: replace by an empty one
                else EditorSceneManager.CloseScene(openTest, true);
            }
            bool single = others.Count == 0 || others.All(sc => string.IsNullOrEmpty(sc.path) && !sc.isDirty);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, single ? NewSceneMode.Single : NewSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            HideOthers(scene, prev);
            var root = new GameObject("TextureTest_W86_T2").transform;
            Surfaces(true);
            MapMaterials();
            PropMaterials();
            var cam = Look(root);
            Vector3 sun = ProbeSun(cam);
            Note($"sun direction (towards the sun) {sun}");
            var dRoots = new Dictionary<string, Transform>();
            foreach (var (name, at) in Districts) dRoots[name] = District(root, "TT_" + name, at, sun);
            foreach (var g in Groups)
            {
                var gr = Group(dRoots[g.District], "G_" + g.Code);
                curGroup = g.Code;
                g.Make(gr);
                var shots = Group(gr, "Shots");
                foreach (var s in g.Shots)
                {
                    var t = new GameObject(s.name).transform; t.SetParent(shots, false);
                    t.localPosition = s.pos; t.localRotation = Quaternion.LookRotation(s.target - s.pos, Vector3.up);
                }
                ShowVariant(gr, "a");
            }
            // one baked reflection probe per district (sky + ground only, all groups off), so glass / water / gloss do not reflect black
            foreach (var (name, _) in Districts)
            {
                var d = dRoots[name];
                foreach (Transform g in d) if (g.name.StartsWith("G_")) g.gameObject.SetActive(false);
                Probe(d, new Vector3(0, 8, 10), new Vector3(160, 50, 140));
                foreach (Transform g in d) if (g.name.StartsWith("G_")) g.gameObject.SetActive(true);
            }
            Note("texel density (px per metre along U): " + string.Join("; ", S.Where(s => s.Value.Px > 0 && s.Value.TU > 0).Select(s => $"{s.Key} {s.Value.Px / s.Value.TU:0}")));
            Note("props used: " + string.Join(", ", UsedProps.Select(Path.GetFileNameWithoutExtension)));
            Note($"meshes {meshN}, surface materials {S.Values.Select(s => s.M).Distinct().Count()}, map materials {MapMats.Count}, prop materials {PropMats.Count}");
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Note($"built in {(DateTime.Now - t0).TotalSeconds:0} s");
            File.WriteAllText(Root + "/TexW86T2_build_log.txt", Log.ToString());
            AssetDatabase.ImportAsset(Root + "/TexW86T2_build_log.txt");
            Debug.Log("[TexW86T2] build done\n" + Log);
        }

        static string curGroup;
        const string HiddenFile = "Temp/TexW86T2_hidden_roots.txt";

        // switch off the roots of every other loaded scene (shared editor), remember their states in Temp (survives a domain reload)
        static void HideOthers(Scene mine, Scene prevActive)
        {
            var lines = new List<string> { "ACTIVE	" + prevActive.path };
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var sc = SceneManager.GetSceneAt(i);
                if (sc == mine || !sc.isLoaded) continue;
                foreach (var r in sc.GetRootGameObjects()) { lines.Add(sc.path + "	" + r.name + "	" + (r.activeSelf ? 1 : 0)); r.SetActive(false); }
            }
            if (File.Exists(HiddenFile)) lines = File.ReadAllLines(HiddenFile).ToList();     // an earlier run did not restore yet: keep the ORIGINAL states
            File.WriteAllLines(HiddenFile, lines);
        }

        // restore the other scenes (root active states, active scene) and close the test scene (it is saved on disk)
        [MenuItem("OnlyVolunteers/Map/W86 Textures T2/Finish (restore other scenes)")]
        public static void Finish()
        {
            if (!File.Exists(HiddenFile)) return;
            var lines = File.ReadAllLines(HiddenFile);
            string active = lines.FirstOrDefault(l => l.StartsWith("ACTIVE	"))?.Substring(7);
            foreach (var l in lines.Where(l => !l.StartsWith("ACTIVE	")))
            {
                var p = l.Split('	'); if (p.Length < 3) continue;
                var sc = SceneManager.GetSceneByPath(p[0]);
                if (!sc.IsValid() || !sc.isLoaded) continue;
                foreach (var r in sc.GetRootGameObjects().Where(r => r.name == p[1])) r.SetActive(p[2] == "1");
            }
            var a = string.IsNullOrEmpty(active) ? default : SceneManager.GetSceneByPath(active);
            if (a.IsValid() && a.isLoaded) SceneManager.SetActiveScene(a);
            var test = SceneManager.GetSceneByPath(ScenePath);
            if (test.IsValid() && test.isLoaded && SceneManager.sceneCount > 1) EditorSceneManager.CloseScene(test, true);
            File.Delete(HiddenFile);
            Debug.Log("[TexW86T2] other scenes restored");
        }

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

        public static Color X(string hex) { ColorUtility.TryParseHtmlString("#" + hex.TrimStart('#'), out Color c); return c; }
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_').ToArray());
        static Transform Group(Transform d, string name) { var g = new GameObject(name).transform; g.SetParent(d, false); return g; }

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
                    var gh = new Texture2D(8, 8, TextureFormat.RFloat, false, true) { name = "T2_GroundHeights", wrapMode = TextureWrapMode.Clamp };
                    gh.SetPixels(Enumerable.Repeat(new Color(0, 0, 0, 1), 64).ToArray()); gh.Apply();
                    AssetDatabase.CreateAsset(gh, LookDir + "/T2_GroundHeights.asset");
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
                    Note($"fog x{FogBoost} (W85Look), {fog.banks.Length} mist banks moved to the Rough / Forest rectangles, flat ground heights");
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
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = camFov; cam.farClipPlane = camFar; cam.nearClipPlane = .2f;
            camGo.AddComponent<AudioListener>();
            var ad = camGo.AddComponent<UniversalAdditionalCameraData>(); ad.renderPostProcessing = true; ad.requiresDepthTexture = true; ad.requiresColorTexture = true;
            Note($"i10 look copied: palette/weather/fog + {palette?.GetComponentsInChildren<Volume>(true).Length ?? 0} light volumes, G22 sky, V19Wind, Sun, PostFX_v17; camera FOV {camFov} far {camFar}");
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

        // District root: front facades (local -Z) face the sun side with the sun ~30 deg to the left (as v07), so front + left end are lit.
        static Transform District(Transform root, string name, Vector2 at, Vector3 sun)
        {
            var t = new GameObject(name).transform; t.SetParent(root, false);
            var sh = new Vector3(sun.x, 0, sun.z); if (sh.sqrMagnitude < 1e-4f) sh = Vector3.back; sh.Normalize();
            var local = new Vector3(-Mathf.Sin(30 * Mathf.Deg2Rad), 0, -Mathf.Cos(30 * Mathf.Deg2Rad));
            float yaw = Mathf.Atan2(sh.x, sh.z) * Mathf.Rad2Deg - Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg;
            t.SetPositionAndRotation(new Vector3(at.x, 0, at.y), Quaternion.Euler(0, yaw, 0));
            Note($"{name}: at {at}, yaw {yaw:0}");
            return t;
        }

        static void Probe(Transform d, Vector3 local, Vector3 size)
        {
            var go = new GameObject("ReflectionProbe_T2"); go.transform.SetParent(d, false); go.transform.localPosition = local;
            var p = go.AddComponent<ReflectionProbe>();
            p.size = size; p.resolution = 256; p.hdr = true; p.mode = ReflectionProbeMode.Baked; p.boxProjection = false;
            string path = LookDir + "/T2_Probe_" + d.name + ".exr";
            if (Lightmapping.BakeReflectionProbe(p, path))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                p.mode = ReflectionProbeMode.Custom; p.customBakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path);
            }
            else Note("reflection probe bake failed: " + d.name);
        }

        static void ShowVariant(Transform g, string v)
        {
            foreach (Transform s in g) if (Vars.Contains(s.name)) s.gameObject.SetActive(s.name == v);
        }

        // ================================================================== capture: one group active at a time, every variant x shot
        public static void Capture(string onlyCode)
        {
            var cam = Object.FindObjectsByType<Camera>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).FirstOrDefault(c => c.CompareTag("MainCamera"));
            if (!cam) throw new Exception("no main camera; build the scene first");
            Directory.CreateDirectory(ShotDir);
            var keep = (cam.transform.position, cam.transform.rotation);
            var groups = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(t => t.name.StartsWith("G_") && t.parent && t.parent.name.StartsWith("TT_")).OrderBy(t => t.name).ToList();
            int n = 0;
            var t0 = DateTime.Now;
            foreach (var g in groups)
            {
                string code = g.name.Substring(2);
                if (onlyCode != null && !onlyCode.Split(',').Contains(code)) continue;
                foreach (var o in groups) o.gameObject.SetActive(o == g);
                var shots = g.Find("Shots");
                foreach (string v in Vars)
                {
                    if (!g.Find(v)) continue;
                    ShowVariant(g, v);
                    foreach (Transform s in shots)
                    {
                        cam.transform.SetPositionAndRotation(s.position, s.rotation);
                        Render(cam, Path.Combine(ShotDir, code + v + "_" + s.name + ".png"));
                        n++;
                    }
                }
                ShowVariant(g, "a");
            }
            foreach (var o in groups) o.gameObject.SetActive(true);
            cam.transform.SetPositionAndRotation(keep.position, keep.rotation);
            Debug.Log($"[TexW86T2] {n} shots -> {ShotDir} in {(DateTime.Now - t0).TotalSeconds:0} s");
        }

        static void Render(Camera cam, string file)
        {
            var rt = new RenderTexture(ShotW, ShotH, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            rt.Create();
            var resolved = new RenderTexture(ShotW, ShotH, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            resolved.Create();
            cam.targetTexture = rt;
            cam.Render(); cam.Render();
            cam.targetTexture = null;
            Graphics.Blit(rt, resolved);
            var prev = RenderTexture.active; RenderTexture.active = resolved;
            var tex = new Texture2D(ShotW, ShotH, TextureFormat.RGB24, false, false);
            tex.ReadPixels(new Rect(0, 0, ShotW, ShotH), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(file, tex.EncodeToPNG());
            Object.DestroyImmediate(tex); rt.Release(); resolved.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(resolved);
        }

        // ================================================================== surfaces (shared, Palette19 + vertex colour)
        sealed class Surf { public Material M; public float TU = 1, TV = 1; public Color Own = Color.white; public int Px; public bool NoShadow; }
        static readonly Dictionary<string, Surf> S = new();
        static readonly Dictionary<string, Color> MeanCache = new();
        static bool creating = true;

        static string PathOf(string file) => file.StartsWith("Assets/") ? file : Tex + "/" + file;

        // T2 textures are ours: importer set here. Every other texture is only referenced (importer untouched).
        static Texture2D SrcTex(string file, bool normal, bool alpha = false, int max = 1024)
        {
            string p = PathOf(file);
            if (p.StartsWith(Tex + "/") && creating)
            {
                AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceSynchronousImport);
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti)
                {
                    var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    if (ti.textureType != type || ti.sRGBTexture == normal || ti.wrapMode != TextureWrapMode.Repeat || ti.anisoLevel != 8 || ti.maxTextureSize != max
                        || ti.alphaIsTransparency != alpha || !ti.mipmapEnabled)
                    {
                        ti.textureType = type; ti.sRGBTexture = !normal; ti.wrapMode = TextureWrapMode.Repeat; ti.anisoLevel = 8; ti.maxTextureSize = max;
                        ti.mipmapEnabled = true; ti.alphaIsTransparency = alpha; ti.textureCompression = TextureImporterCompression.CompressedHQ;
                        if (alpha) ti.alphaSource = TextureImporterAlphaSource.FromInput;
                        ti.SaveAndReimport();
                    }
                }
            }
            else if (normal && AssetImporter.GetAtPath(p) is TextureImporter oi && oi.textureType != TextureImporterType.NormalMap)
            {
                Note("normal map not imported as normal map (skipped, importer not touched): " + p);
                return null;
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

        static Material SaveOrLoad(Material m, string path)
        {
            if (creating) { AssetDatabase.CreateAsset(m, path); return m; }
            var e = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!e) throw new Exception("material missing (run Build first): " + path);
            return e;
        }

        static Surf Pal(string key, string albedo, float tu, float tv, string normal = null, float bump = .5f, float smooth = .12f, float metal = 0f, int max = 1024)
        {
            var tex = SrcTex(albedo, false, false, max);
            var m = new Material(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "T2_" + key, enableInstancing = true };
            m.SetTexture("_BaseMap", tex); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            if (normal != null)
            {
                var nt = SrcTex(normal, true, false, max);
                if (nt) { m.SetTexture("_BumpMap", nt); m.SetFloat("_UseNormalMap", 1f); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", bump); }
            }
            Color own = MeanOf(PathOf(albedo));
            m.SetVector("_TintRef", (Vector4)own.linear);
            m = SaveOrLoad(m, MatDir + "/T2_" + key + ".mat");
            return S[key] = new Surf { M = m, TU = tu, TV = tv, Own = own, Px = tex.width };
        }

        static Surf FlatS(string key, float smooth, float metal = 0f)
        {
            var m = new Material(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "T2_" + key, enableInstancing = true };
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal); m.SetVector("_TintRef", Vector4.one); m.SetFloat("_MacroStrength", .02f);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            m = SaveOrLoad(m, MatDir + "/T2_" + key + ".mat");
            return S[key] = new Surf { M = m };
        }

        // URP Lit: mode 0 opaque, 1 alpha clip, 2 transparent; mesh UVs are already metres / TU (texture scale 1)
        static Surf LitS(string key, Color col, Texture tex, float tu, float tv, float smooth, float metal, int mode, bool twoSided = false, bool noShadow = false, string dir = MatDir)
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "T2_" + key, enableInstancing = true };
            m.SetColor("_BaseColor", col);
            if (tex) m.SetTexture("_BaseMap", tex);
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
            m = SaveOrLoad(m, dir + "/T2_" + key + ".mat");
            return S[key] = new Surf { M = m, TU = tu, TV = tv, Own = col, Px = tex ? tex.width : 0, NoShadow = noShadow || mode == 2 };
        }

        static string Emit(string key, string hex, float intensity)
        {
            if (S.ContainsKey(key)) return key;
            var s = LitS(key, X(hex), null, 1, 1, .3f, 0, 0);
            if (creating)
            {
                s.M.EnableKeyword("_EMISSION"); s.M.SetColor("_EmissionColor", X(hex) * intensity); s.M.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                EditorUtility.SetDirty(s.M);
            }
            return key;
        }

        static Texture2D glassAtlas, chainTex;

        static void Surfaces(bool create)
        {
            creating = create; S.Clear();
            // existing project textures (read only)
            Pal("lawn", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_park_grass_albedo.png", 8, 8);
            Pal("meadow", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_meadow_albedo.png", 8, 8);
            Pal("sand", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_sand_albedo.png", 8, 8);
            Pal("dirt", SK + "1b_dirt_road/1b_dirt_road_v07_albedo.png", 6, 6, SK + "1b_dirt_road/1b_dirt_road_v07_normal.png", .5f);
            Pal("roof_flat", SK + "4d_flat_bitumen_roof/4d_flat_bitumen_roof_v03_albedo.png", 4, 4);
            Pal("asphalt", TT + "Built_v04/Textures/2a_asphalt_v07_A5d12_albedo.png", 6, 6);
            Pal("plaster", TT + "Source_v03/TT_acg_Plaster001_neutral_albedo.png", 3, 3, TT + "Source_v03/TT_acg_Plaster001_normal.png", .35f);
            Pal("kh3", TT + "Built_v04/Textures/KH3_silicate_brick_white_albedo.png", 1, 1);
            Pal("rockmacro", "Assets/OnlyVolunteers/Map/W85Build/Generated/v01/Textures/Rock_Macro.png", 6, 6);
            Pal("travertine", V07 + "T7_travertine_panels_albedo.png", 2.4f, 2.4f, V07 + "T7_travertine_panels_normal.png", .45f, .2f);
            Pal("conc", V07 + "T7_concrete_smooth_albedo.png", 2.4f, 2.4f, V07 + "T7_concrete_smooth_normal.png", .3f);
            Pal("panel", V07 + "T7_panel_smooth_albedo.png", 2.4f, 2.4f, V07 + "T7_panel_smooth_normal.png", .6f, .18f);
            Pal("board", V07 + "T7_concrete_boardformed_albedo.png", 2f, 2f, V07 + "T7_concrete_boardformed_normal.png", .6f);
            Pal("formwork", V07 + "T7_concrete_formwork_albedo.png", 2.4f, 2.4f, V07 + "T7_concrete_formwork_normal.png", .5f);
            Pal("aggregate", V07 + "T7_concrete_aggregate_albedo.png", 1.4f, 1.4f);
            Pal("slab_grey", V07 + "T7_slab_granite_grey_albedo.png", 2f, 2f, V07 + "T7_slab_normal.png", .5f, .16f);
            Pal("slab_lime", V07 + "T7_slab_limestone_albedo.png", 2f, 2f, V07 + "T7_slab_normal.png", .5f, .16f);
            Pal("stone", V07 + "T7_stone_grain_albedo.png", 1f, 1f, null, .5f, .22f);
            Pal("mosaic", V07 + "T7_pool_mosaic_albedo.png", 1.5f, 1.5f, V07 + "T7_pool_mosaic_normal.png", .4f, .45f);
            Pal("setts_sand", V07 + "T7_setts_sandstone_albedo.png", 1.2f, 1.2f, V07 + "T7_setts_sandstone_normal.png", .8f);
            Pal("rubble_grey", V07 + "T7_rubble_grey_albedo.png", 2.2f, 2.2f, V07 + "T7_rubble_grey_normal.png", .8f);
            Pal("asph_light", V07 + "T7_asphalt_light_albedo.png", 3f, 3f);
            Pal("ashlar", V07 + "T7_rustic_ashlar_albedo.png", 2.4f, 2.4f, V07 + "T7_rustic_ashlar_normal.png", .8f);
            Pal("trapez", V07 + "T7_metal_trapez_albedo.png", 1.5f, 1.5f, V07 + "T7_metal_trapez_normal.png", .9f, .3f, .2f);
            Pal("wave", V07 + "T7_metal_wave_albedo.png", 1.2f, 1.2f, V07 + "T7_metal_wave_normal.png", .9f, .35f, .3f);
            Pal("planks_w", V07 + "T7_planks_weathered_albedo.png", 1.6f, 1.6f, V07 + "T7_planks_weathered_normal.png", .6f);
            Pal("teak", V07 + "T7_wood_teak_albedo.png", 1.2f, 1.2f, null, .5f, .2f);
            Pal("brick_roman", V07 + "T7_brick_roman_albedo.png", 1.2f, 1.2f, V07 + "T7_brick_roman_normal.png", .7f);
            // T2 own (gen_textures_t2.py)
            Pal("marble", "T2_marble_albedo.png", 2f, 2f, "T2_marble_normal.png", .3f, .35f);
            Pal("wallpanel", "T2_wallpanel_albedo.png", 3f, 3f, "T2_wallpanel_normal.png", .7f);
            Pal("slabs6", "T2_slabs6_albedo.png", 6f, 6f, "T2_slabs6_normal.png", .6f);
            Pal("patched", "T2_concrete_patched_albedo.png", 8f, 8f);
            Pal("canvas", "T2_canvas_albedo.png", .6f, .6f, "T2_canvas_normal.png", .4f);
            Pal("terrazzo", "T2_terrazzo_albedo.png", 1.2f, 1.2f, null, .5f, .3f);
            Pal("rock_grey", "T2_rock_grey_albedo.png", 4f, 4f, "T2_rock_grey_normal.png", .9f);
            Pal("rock_warm", "T2_rock_warm_albedo.png", 4f, 4f, "T2_rock_warm_normal.png", .9f);
            Pal("thatch", "T2_thatch_albedo.png", 2f, 2f, "T2_thatch_normal.png", .8f);
            Pal("deck_teak", "T2_deck_teak_albedo.png", 1.8f, 1.8f, "T2_deck_teak_normal.png", .6f, .18f);
            Pal("deck_bleached", "T2_deck_bleached_albedo.png", 1.4f, 1.4f, "T2_deck_bleached_normal.png", .6f);
            Pal("roof_barrel", "T2_roof_barrel_albedo.png", 3.2f, 3.2f, "T2_roof_barrel_normal.png", .8f);
            Pal("camo", "T2_camo_albedo.png", 4f, 4f);
            Pal("hedge_box", "T2_hedge_box_albedo.png", 2f, 2f, "T2_hedge_box_normal.png", .8f);
            Pal("hedge_laurel", "T2_hedge_laurel_albedo.png", 2f, 2f, "T2_hedge_laurel_normal.png", .8f, .22f);
            Pal("hedge_bougain", "T2_hedge_bougain_albedo.png", 2f, 2f, "T2_hedge_bougain_normal.png", .8f);
            Pal("stripes", "T2_stripes_atlas_albedo.png", 4f, 1f);
            Pal("hazard", "T2_hazard_atlas_albedo.png", 4f, 1f);
            Pal("green_fine", "T2_green_fine_albedo.png", 2f, 2f);
            Pal("flowerbed", "T2_flowerbed_albedo.png", 1.5f, 1.5f);
            FlatS("flat", .12f); FlatS("flat_metal", .4f, .45f); FlatS("flat_gloss", .82f, .1f); FlatS("flat_gold", .55f, .75f);
            glassAtlas = SrcTex(V07 + "T7_office_glass_atlas_albedo.png", false);
            chainTex = SrcTex(V07 + "T7_chainlink_rgba.png", false, true);
            LitS("glass_dark", X("34424A"), null, 1, 1, .9f, .25f, 0);
            LitS("glass_atlas", X("8FA2AE"), glassAtlas, 1, 1, .9f, .3f, 0, false, true);
            LitS("chain", X("5A5E5C"), chainTex, .8f, .8f, .35f, .3f, 1, true);
            LitS("water_pool", new Color(.36f, .74f, .82f, .5f), null, 1, 1, .85f, 0f, 2, false, true);
            LitS("sea", X("4C8CA6"), null, 1, 1, .9f, 0f, 0, false, true);
            LitS("waterfall", new Color(.86f, .93f, .96f, .62f), null, 1, 1, .7f, 0f, 2, true, true);
            Emit("bulb", "FFE3A0", 2.2f); Emit("neon_red", "FF3B3B", 3.0f); Emit("neon_white", "FFF6E8", 1.6f); Emit("lamp_warm", "FFE8C0", 1.4f);
            Note($"surfaces: {S.Count}");
        }

        static Color Own(string key) => S[key].Own;
    }
}
