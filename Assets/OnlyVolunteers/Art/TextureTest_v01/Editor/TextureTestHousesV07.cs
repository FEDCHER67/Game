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

namespace OnlyVolunteers.Art.TextureTest
{
    // TextureTest_Houses_v07 (Map W86, agent A4, 22.10.2026): texture variants with codes for the parts of the W85 map that have no
    // approved textures yet, one sample (one house / one street) per district, day light, the playtested i10 look exactly as in
    // v01-v06 / W85Look (sky, sun, district weather and fog +8 %, light volumes, PostFX_v17) on the W85 district rectangles, so
    // the district light of the map applies. Variants are sibling groups (one active), shots per district (eye 1.7 m, wide, close).
    //   O1-O3   Downtown offices (05-05 / 05-06, 32 x 14 m, 6 floors): own facade type, windows better than D4, worse than T4.
    //   DS1-DS3 Downtown street of 3-6 floor houses: visible separation (pilasters / cornice breaks / setbacks / gaps / trim).
    //   DC1-DC3 Downtown centre (plaza "Water axis"): 1 x 1 m slabs, dark 0.5 m band, mirror pool edging, kiosk / bench / lamp.
    //   P1-P3   Port: warehouse, containers, quay edge, reach stacker, yard, chain-link fence.
    //   E1-E3   Elite: villa, FBI building, stone road + parapet, trap gate in the solid fence, guard booth.
    //   C1-C3   Construction: concrete frame, scaffolding, site cabins, workshop, blue profiled-sheet fence + gate, tower crane.
    //   Q1-Q3   Quiet Valley: final lab (base 5), casino, low wooden fence.
    // Textures: Source_v07 (made by Working/Reviews/MapW86_Textures_2026-10-22/tools/gen_textures_v07.py from ambientCG CC0 sets,
    // see Source_v07/SOURCES.md) + existing project textures referenced read-only. Materials, meshes and look assets only in
    // Built_v07; nothing of Built_v04 (used by the map) or any other existing asset is written. Colour = vertex colour on the
    // Palette19 shader (one material per surface category, SRP-batched), glass / mesh / net = URP Lit.
    public static class TextureTestHousesV07
    {
        const string Root = "Assets/OnlyVolunteers/Art/TextureTest_v01";
        const string Built = Root + "/Built_v07";
        const string Src = Root + "/Source_v07";
        const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/TextureTest_Houses_v07.unity";
        const string I10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string SK = "Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/";
        const string TTB4 = Root + "/Built_v04/Textures/";                 // read only (textures of the approved v04 look)
        const string MP = "Assets/OnlyVolunteers/Art/Map/Prefabs/";
        const string ShotDir = "Working/Reviews/MapW86_Textures_2026-10-22/raw";
        const int ShotW = 1600, ShotH = 900;
        const float FogBoost = 1.08f;                                      // W85Look: fog +8 % (Fedya 21.10)
        const float Kerb = .15f;

        static readonly Dictionary<string, Vector4> Rects = new()
        {
            ["forest"] = new(180, 60, 445, 330), ["village"] = new(185, 365, 470, 625), ["transition"] = new(525, 345, 705, 500),
            ["residential"] = new(655, 668, 1006, 905), ["old_town"] = new(790, 215, 1272, 472), ["industrial"] = new(1165, 595, 1360, 690),
            ["elite"] = new(1342, 258, 1496, 388), ["fields"] = new(520, 60, 665, 300), ["beach"] = new(790, 100, 1520, 228),
            ["tramduro"] = new(1440, 680, 1660, 860),
        };

        static readonly string[] Codes = { "O1", "O2", "O3", "DS1", "DS2", "DS3", "DC1", "DC2", "DC3", "P1", "P2", "P3", "E1", "E2", "E3", "C1", "C2", "C3", "Q1", "Q2", "Q3" };
        static bool IsCode(string n) => Codes.Contains(n);

        static readonly StringBuilder Log = new();
        static void Note(string s) { Log.AppendLine(s); }

        // ================================================================== menu / batch
        [MenuItem("OnlyVolunteers/Map/Texture Test v07/Build TextureTest_Houses_v07")]
        public static void BuildMenu() { if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) Build(); }

        [MenuItem("OnlyVolunteers/Map/Texture Test v07/Capture all variants")]
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
            Log.Clear(); S.Clear(); MeanCache.Clear(); UsedProps.Clear(); meshN = 0;
            var t0 = DateTime.Now;
            if (AssetDatabase.IsValidFolder(Built)) AssetDatabase.DeleteAsset(Built);
            foreach (string f in new[] { "Materials", "Meshes", "Look" }) Folder(Built + "/" + f);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("TextureTest_Houses_v07").transform;
            Surfaces();
            var cam = Look(root);
            Vector3 sun = ProbeSun(cam);
            Note($"sun direction (towards the sun) {sun}");
            var off = District(root, "TT_Offices", new Vector2(880, 300), sun);
            var st = District(root, "TT_Street", new Vector2(1035, 300), sun);
            var sq = District(root, "TT_Square", new Vector2(1190, 330), sun);
            var po = District(root, "TT_Port", new Vector2(1262, 642), sun);
            var el = District(root, "TT_Elite", new Vector2(1419, 323), sun);
            var co = District(root, "TT_Construction", new Vector2(615, 422), sun);
            var va = District(root, "TT_Valley", new Vector2(592, 180), sun);
            Offices(off); Street(st); Square(sq); Port(po); Elite(el); Construction(co); Valley(va);
            Shots(off, ("eye", new Vector3(-8f, 1.7f, -8.5f), new Vector3(2f, 9.5f, 18f)), ("wide", new Vector3(-30f, 14f, -24f), new Vector3(0f, 10f, 16f)),
                ("close", new Vector3(-4f, 6f, -3f), new Vector3(2f, 9.5f, 11f)));
            Shots(st, ("eye", new Vector3(-20f, 1.7f, -9f), new Vector3(-2f, 8f, 16f)), ("wide", new Vector3(-32f, 15f, -26f), new Vector3(0f, 8f, 15f)),
                ("along", new Vector3(-26f, 10f, 2f), new Vector3(14f, 9f, 12f)));
            Shots(sq, ("eye", new Vector3(-11f, 1.7f, 12.5f), new Vector3(-1f, 1.2f, 46f)), ("wide", new Vector3(-38f, 17f, -16f), new Vector3(0f, 0f, 26f)),
                ("close", new Vector3(-14f, 1.7f, 7.5f), new Vector3(-17f, .9f, 14f)));
            Shots(po, ("eye", new Vector3(-6f, 1.7f, -17f), new Vector3(0f, 5f, 20f)), ("wide", new Vector3(68f, 14f, -26f), new Vector3(8f, 2f, 8f)),
                ("close", new Vector3(-28f, 1.7f, -13f), new Vector3(-41f, 3f, -1f)));
            Shots(el, ("eye", new Vector3(.6f, 1.7f, -24f), new Vector3(0f, 4.5f, 10f)), ("wide", new Vector3(24f, 15f, -28f), new Vector3(-12f, 2f, 16f)),
                ("villa", new Vector3(-16f, 1.7f, 5f), new Vector3(-30f, 3.6f, 20f)));
            Shots(co, ("eye", new Vector3(-5f, 1.7f, -13f), new Vector3(0f, 7f, 12f)), ("wide", new Vector3(-46f, 20f, -46f), new Vector3(-4f, 5f, 8f)),
                ("close", new Vector3(-15f, 1.7f, -33f), new Vector3(-3f, 2.2f, -20f)));
            Shots(va, ("eye", new Vector3(-3f, 1.7f, -16f), new Vector3(1f, 4.5f, 15f)), ("wide", new Vector3(-30f, 16f, -28f), new Vector3(14f, 2f, 16f)),
                ("casino", new Vector3(40f, 1.7f, -5f), new Vector3(50f, 4f, 18f)));
            foreach (var d in new[] { off, st, sq, po, el, co, va }) Show(d.Cast<Transform>().First(t => IsCode(t.name)).name);
            // baked reflection probe per district (as v06): glass / water / gloss reflect the painted sky, not black
            foreach (var (d, c, sz) in new[] { (off, new Vector3(0, 12, 12), new Vector3(110, 40, 70)), (st, new Vector3(0, 10, 12), new Vector3(110, 40, 70)),
                (sq, new Vector3(0, 6, 24), new Vector3(120, 40, 110)), (po, new Vector3(0, 8, 8), new Vector3(130, 40, 110)), (el, new Vector3(-10, 6, 10), new Vector3(120, 30, 100)),
                (co, new Vector3(0, 10, 15), new Vector3(130, 50, 110)), (va, new Vector3(25, 6, 10), new Vector3(130, 30, 90)) }) Probe(d, c, sz);
            var eye = off.Find("Shots/eye");
            if (eye) cam.transform.SetPositionAndRotation(eye.position, eye.rotation);
            Note("texel density (px per metre along U): " + string.Join("; ", S.Where(s => s.Value.Px > 0).Select(s => $"{s.Key} {s.Value.Px / s.Value.TU:0}")));
            Note("props used: " + string.Join(", ", UsedProps.Select(Path.GetFileNameWithoutExtension)));
            Note($"meshes {meshN}, materials {S.Values.Select(s => s.M).Distinct().Count()} (+ reused water)");
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Note($"built in {(DateTime.Now - t0).TotalSeconds:0} s");
            File.WriteAllText(Built + "/TextureTest_v07_build_log.txt", Log.ToString());
            AssetDatabase.ImportAsset(Built + "/TextureTest_v07_build_log.txt");
            Debug.Log("[TextureTest v07] build done\n" + Log);
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

        static Color X(string hex) { ColorUtility.TryParseHtmlString("#" + hex, out Color c); return c; }
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_').ToArray());

        // ================================================================== look (copy of TextureTestHousesV06.Look / W85Look, no terrain)
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
                    var gh = new Texture2D(8, 8, TextureFormat.RFloat, false, true) { name = "TT7_GroundHeights", wrapMode = TextureWrapMode.Clamp };
                    gh.SetPixels(Enumerable.Repeat(new Color(0, 0, 0, 1), 64).ToArray()); gh.Apply();
                    AssetDatabase.CreateAsset(gh, Built + "/Look/TT7_GroundHeights.asset");
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
                    Note($"fog x{FogBoost} (W85Look), {fog.banks.Length} mist banks on the Rough / Forest rectangles, flat ground heights");
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

        // District root: the front facades (local -Z) face the sun side with the sun ~30 deg to the left, so front and left end are lit.
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
            var go = new GameObject("ReflectionProbe_TT7"); go.transform.SetParent(d, false); go.transform.localPosition = local;
            var p = go.AddComponent<ReflectionProbe>();
            p.size = size; p.resolution = 256; p.hdr = true; p.mode = ReflectionProbeMode.Baked; p.boxProjection = false;
            string path = Built + "/Look/TT7_Probe_" + d.name + ".exr";
            if (Lightmapping.BakeReflectionProbe(p, path))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                p.mode = ReflectionProbeMode.Custom; p.customBakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path);
            }
            else Note("reflection probe bake failed: " + d.name);
        }

        static void Shots(Transform d, params (string name, Vector3 pos, Vector3 target)[] shots)
        {
            var parent = new GameObject("Shots").transform; parent.SetParent(d, false);
            foreach (var s in shots)
            {
                var g = new GameObject(s.name).transform; g.SetParent(parent, false);
                g.localPosition = s.pos; g.localRotation = Quaternion.LookRotation(s.target - s.pos, Vector3.up);
            }
        }

        static void Show(string code)
        {
            var g = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(t => t.name == code && t.parent && t.parent.name.StartsWith("TT_"));
            if (!g) return;
            foreach (Transform s in g.parent) if (IsCode(s.name)) s.gameObject.SetActive(s == g);
        }

        // ================================================================== capture: one district active at a time, every variant x shot
        public static void Capture(string only)
        {
            var cam = Object.FindObjectsByType<Camera>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).FirstOrDefault(c => c.CompareTag("MainCamera"));
            if (!cam) throw new Exception("no main camera; build the scene first");
            Directory.CreateDirectory(ShotDir);
            var keep = (cam.transform.position, cam.transform.rotation);
            var districts = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(t => t.name.StartsWith("TT_") && t.parent && t.parent.parent == null).OrderBy(t => t.name).ToList();
            int n = 0;
            foreach (var d in districts)
            {
                if (only != null && d.name != only) continue;
                foreach (var o in districts) o.gameObject.SetActive(o == d);
                var codes = d.Cast<Transform>().Where(s => IsCode(s.name)).Select(s => s.name).ToList();
                var shots = d.Find("Shots");
                foreach (string code in codes)
                {
                    Show(code);
                    foreach (Transform s in shots)
                    {
                        cam.transform.SetPositionAndRotation(s.position, s.rotation);
                        Render(cam, Path.Combine(ShotDir, code + "_" + s.name + ".png"));
                        n++;
                    }
                }
                Show(codes.First());
            }
            foreach (var o in districts) o.gameObject.SetActive(true);
            cam.transform.SetPositionAndRotation(keep.position, keep.rotation);
            Debug.Log($"[TextureTest v07] {n} shots -> {ShotDir}");
        }

        public static void CaptureOne(string district) => Capture(district);

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

        // ================================================================== surfaces
        sealed class Surf { public Material M; public float TU = 1, TV = 1; public Color Own = Color.white; public int Px; public bool NoShadow; }
        static readonly Dictionary<string, Surf> S = new();
        static readonly Dictionary<string, Color> MeanCache = new();

        static string PathOf(string file) => file.StartsWith("Assets/") ? file : Src + "/" + file;

        // Source_v07 textures are ours: importer set here. Every other texture is only referenced (importer untouched).
        static Texture2D SrcTex(string file, bool normal, bool alpha = false, int max = 1024)
        {
            string p = PathOf(file);
            if (p.StartsWith(Src + "/"))
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

        static Material NewPalette(string key)
        {
            var m = new Material(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "TT7_" + key, enableInstancing = true };
            return m;
        }

        static Surf Pal(string key, string albedo, float tu, float tv, string normal = null, float bump = .5f, float smooth = .12f, float metal = 0f, int max = 1024)
        {
            var tex = SrcTex(albedo, false, false, max);
            var m = NewPalette(key);
            m.SetTexture("_BaseMap", tex); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            if (normal != null)
            {
                var nt = SrcTex(normal, true, false, max);
                if (nt) { m.SetTexture("_BumpMap", nt); m.SetFloat("_UseNormalMap", 1f); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", bump); }
            }
            Color own = MeanOf(PathOf(albedo));
            m.SetVector("_TintRef", (Vector4)own.linear);
            AssetDatabase.CreateAsset(m, Built + "/Materials/TT7_" + key + ".mat");
            return S[key] = new Surf { M = m, TU = tu, TV = tv, Own = own, Px = tex.width };
        }

        static Surf FlatS(string key, float smooth, float metal = 0f)
        {
            var m = NewPalette(key);
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal); m.SetVector("_TintRef", Vector4.one); m.SetFloat("_MacroStrength", .02f);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            AssetDatabase.CreateAsset(m, Built + "/Materials/TT7_" + key + ".mat");
            return S[key] = new Surf { M = m };
        }

        // URP Lit: mode 0 opaque, 1 alpha clip, 2 transparent; mesh UVs are already metres / TU (texture scale 1)
        static Surf LitS(string key, Color col, Texture tex, float tu, float tv, float smooth, float metal, int mode, bool twoSided = false, bool noShadow = false)
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "TT7_" + key, enableInstancing = true };
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
            AssetDatabase.CreateAsset(m, Built + "/Materials/TT7_" + key + ".mat");
            return S[key] = new Surf { M = m, TU = tu, TV = tv, Own = col, Px = tex ? tex.width : 0, NoShadow = noShadow || mode == 2 };
        }

        static Surf RefS(string key, string matPath)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (!m) throw new Exception("material missing: " + matPath);
            return S[key] = new Surf { M = m, TU = 1, TV = 1, NoShadow = true };
        }

        static Texture2D glassAtlas, chainTex, meshTex, netTex;

        static void Surfaces()
        {
            // existing project textures, referenced read-only (new materials here)
            Pal("meadow", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_meadow_albedo.png", 8, 8);
            Pal("asphalt", TTB4 + "2a_asphalt_v07_A5d12_albedo.png", 6, 6);
            Pal("sidewalk", TTB4 + "S1_sidewalk_oar_1p5m_albedo.png", 3, 3);
            Pal("dirt", SK + "1b_dirt_road/1b_dirt_road_v07_albedo.png", 6, 6, SK + "1b_dirt_road/1b_dirt_road_v07_normal.png", .5f);
            Pal("plaster", Root + "/Source_v03/TT_acg_Plaster001_neutral_albedo.png", 3, 3, Root + "/Source_v03/TT_acg_Plaster001_normal.png", .35f);
            Pal("brick_d4", SK + "3a_brick/3a_brick_v07_albedo.png", 3, 3, SK + "3a_brick/3a_brick_v07_normal.png", .6f);
            Pal("cinder", SK + "3d_cinder_blocks/3d_cinder_blocks_v07_albedo.png", 3, 3, SK + "3d_cinder_blocks/3d_cinder_blocks_v07_normal.png", .6f);
            Pal("roof_flat", SK + "4d_flat_bitumen_roof/4d_flat_bitumen_roof_v03_albedo.png", 4, 4);
            FlatS("flat", .12f); FlatS("flat_metal", .4f, .45f); FlatS("flat_gloss", .82f, .1f);
            S["glass_d"] = new Surf { M = LitS("glass_d", X("2F3B43"), null, 1, 1, .9f, .25f, 0).M };     // D4 glazing (G-D)
            // Source_v07 (ambientCG CC0 adapted + own)
            Pal("travertine", "T7_travertine_panels_albedo.png", 2.4f, 2.4f, "T7_travertine_panels_normal.png", .45f, .2f);
            Pal("conc", "T7_concrete_smooth_albedo.png", 2.4f, 2.4f, "T7_concrete_smooth_normal.png", .3f);
            Pal("panel", "T7_panel_smooth_albedo.png", 2.4f, 2.4f, "T7_panel_smooth_normal.png", .6f, .18f);
            Pal("board", "T7_concrete_boardformed_albedo.png", 2f, 2f, "T7_concrete_boardformed_normal.png", .6f);
            Pal("formwork", "T7_concrete_formwork_albedo.png", 2.4f, 2.4f, "T7_concrete_formwork_normal.png", .5f);
            Pal("aggregate", "T7_concrete_aggregate_albedo.png", 1.4f, 1.4f);
            Pal("slab_warm", "T7_slab_granite_warm_albedo.png", 2f, 2f, "T7_slab_normal.png", .5f, .16f);
            Pal("slab_grey", "T7_slab_granite_grey_albedo.png", 2f, 2f, "T7_slab_normal.png", .5f, .16f);
            Pal("slab_lime", "T7_slab_limestone_albedo.png", 2f, 2f, "T7_slab_normal.png", .5f, .16f);
            Pal("stone", "T7_stone_grain_albedo.png", 1f, 1f, null, .5f, .22f);
            Pal("mosaic", "T7_pool_mosaic_albedo.png", 1.5f, 1.5f, "T7_pool_mosaic_normal.png", .4f, .45f);
            Pal("setts", "T7_setts_granite_albedo.png", 1.15f, 1.15f, "T7_setts_granite_normal.png", .8f);
            Pal("setts_sand", "T7_setts_sandstone_albedo.png", 1.2f, 1.2f, "T7_setts_sandstone_normal.png", .8f);
            Pal("rubble_grey", "T7_rubble_grey_albedo.png", 2.2f, 2.2f, "T7_rubble_grey_normal.png", .8f);
            Pal("rubble_warm", "T7_rubble_warm_albedo.png", 2.2f, 2.2f, "T7_rubble_warm_normal.png", .8f);
            Pal("asph_light", "T7_asphalt_light_albedo.png", 3f, 3f);
            Pal("ashlar", "T7_rustic_ashlar_albedo.png", 2.4f, 2.4f, "T7_rustic_ashlar_normal.png", .8f);
            Pal("trapez", "T7_metal_trapez_albedo.png", 1.5f, 1.5f, "T7_metal_trapez_normal.png", .9f, .3f, .2f);
            Pal("wave", "T7_metal_wave_albedo.png", 1.2f, 1.2f, "T7_metal_wave_normal.png", .9f, .35f, .3f);
            Pal("shutter", "T7_shutter_albedo.png", 2f, 2f, "T7_shutter_normal.png", .7f, .3f, .2f);
            Pal("planks", "T7_planks_scaffold_albedo.png", 1.4f, 1.4f, "T7_planks_scaffold_normal.png", .5f);
            Pal("planks_w", "T7_planks_weathered_albedo.png", 1.6f, 1.6f, "T7_planks_weathered_normal.png", .6f);
            Pal("teak", "T7_wood_teak_albedo.png", 1.2f, 1.2f, null, .5f, .2f);
            Pal("larch", "T7_wood_larch_albedo.png", 1.2f, 1.2f, null, .5f, .18f);
            Pal("osb", "T7_osb_albedo.png", 1.22f, 1.22f);
            Pal("brick_roman", "T7_brick_roman_albedo.png", 1.2f, 1.2f, "T7_brick_roman_normal.png", .7f);
            Pal("container", "T7_container_atlas_albedo.png", 1f, 1f, "T7_container_atlas_normal.png", .8f, .3f, .15f, 2048);
            glassAtlas = SrcTex("T7_office_glass_atlas_albedo.png", false);
            chainTex = SrcTex("T7_chainlink_rgba.png", false, true);
            meshTex = SrcTex("T7_mesh_weld_rgba.png", false, true);
            netTex = SrcTex("T7_net_rgba.png", false, true, 512);
            // own simple water (the W85 flow / sea shaders need the map's depth and mesh data): clear pool water over the tiles, sea
            LitS("water_pool", new Color(.32f, .62f, .78f, .5f), null, 1, 1, .82f, 0f, 2, false, true);
            LitS("water_puddle", new Color(.30f, .36f, .38f, .6f), null, 1, 1, .95f, 0f, 2, false, true);
            LitS("sea", X("4C8CA6"), null, 1, 1, .9f, 0f, 0, false, true);
            Note($"surfaces: {S.Count} (Source_v07 + read-only project textures)");
        }

        // per-variant URP Lit surfaces (no vertex colour): office glass atlas, chain-link / weld mesh, safety net, emissive
        static string Glass(string key, string hex)
        {
            if (!S.ContainsKey(key)) LitS(key, X(hex), glassAtlas, 1, 1, .9f, .3f, 0, false, true);
            return key;
        }
        static string Chain(string key, string hex, bool weld = false)
        {
            if (!S.ContainsKey(key)) LitS(key, X(hex), weld ? meshTex : chainTex, weld ? 2.4f : .8f, weld ? 2.4f : .8f, .35f, .3f, 1, true);
            return key;
        }
        static string Net(string key, string hex)
        {
            if (!S.ContainsKey(key)) LitS(key, X(hex), netTex, 1f, 1f, .1f, 0f, 2, true, true);
            return key;
        }
        static string Emit(string key, string hex, float intensity)
        {
            if (S.ContainsKey(key)) return key;
            var s = LitS(key, X(hex), null, 1, 1, .3f, 0, 0);
            s.M.EnableKeyword("_EMISSION"); s.M.SetColor("_EmissionColor", X(hex) * intensity); s.M.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            EditorUtility.SetDirty(s.M);
            return key;
        }

        // ================================================================== geometry
        sealed class MB
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> U = new(); public readonly List<Color> C = new(); public readonly List<int> T = new();
            public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); V.Add(d); U.Add(ua); U.Add(ub); U.Add(uc); U.Add(ud); C.Add(col); C.Add(col); C.Add(col); C.Add(col);
                T.Add(n); T.Add(n + 1); T.Add(n + 2); T.Add(n); T.Add(n + 2); T.Add(n + 3);     // front = (b - a) x (c - a)
            }
            public void Tri(Vector3 a, Vector3 b, Vector3 c, Vector2 ua, Vector2 ub, Vector2 uc, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); U.Add(ua); U.Add(ub); U.Add(uc); C.Add(col); C.Add(col); C.Add(col);
                T.Add(n); T.Add(n + 1); T.Add(n + 2);
            }
        }

        sealed class Batch
        {
            public readonly Dictionary<string, MB> ByKey = new();
            public MB this[string k] { get { if (!ByKey.TryGetValue(k, out var mb)) ByKey[k] = mb = new MB(); return mb; } }
        }

        static int meshN;

        static void Flush(Batch b, Transform parent, string name)
        {
            foreach (var kv in b.ByKey)
            {
                var mb = kv.Value;
                if (mb.V.Count == 0) continue;
                if (!S.TryGetValue(kv.Key, out var surf)) throw new Exception("surface missing: " + kv.Key);
                var mesh = new Mesh { name = name + "_" + kv.Key, indexFormat = mb.V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.SetVertices(mb.V); mesh.SetUVs(0, mb.U); mesh.SetColors(mb.C); mesh.SetTriangles(mb.T, 0);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Built + "/Meshes/" + Safe(mesh.name) + ".asset"); meshN++;
                var go = new GameObject(mesh.name); go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = surf.M;
                if (surf.NoShadow) r.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            }
            b.ByKey.Clear();
        }

        // frame: O + R x + up y + F z (proper rotation, so the winding stays right)
        struct Fr
        {
            public Vector3 O, R, F;
            public Vector3 P(float x, float y, float z) => O + R * x + Vector3.up * y + F * z;
            public Vector3 P(Vector3 v) => P(v.x, v.y, v.z);
            public Vector3 D(Vector3 v) => R * v.x + Vector3.up * v.y + F * v.z;
            public static Fr Yaw(Vector3 o, float deg) { var q = Quaternion.Euler(0, deg, 0); return new Fr { O = o, R = q * Vector3.right, F = q * Vector3.forward }; }
            // wall frame: x along the wall from p0, y up, z INTO the wall (outward = -F), origin at p0
            public Fr Wall(Vector2 p0, Vector2 p1)
            {
                Vector2 d = (p1 - p0).normalized; var dir = new Vector3(d.x, 0, d.y);
                return new Fr { O = P(p0.x, 0, p0.y), R = D(dir), F = D(-Vector3.Cross(Vector3.up, dir)) };
            }
            public Vector3 Out => -F;
        }

        static readonly Fr G0 = Fr.Yaw(Vector3.zero, 0);
        static readonly Vector3[] Dirs = { Vector3.right, Vector3.left, Vector3.forward, Vector3.back, Vector3.up, Vector3.down };
        static float Ext(Vector3 size, Vector3 a) => Mathf.Abs(a.x) * size.x + Mathf.Abs(a.y) * size.y + Mathf.Abs(a.z) * size.z;

        static void Wall(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, Color col, float o = 0f)
        {
            var s = S[key];
            float Uu(float x) => x / s.TU; float Vv(float y) => y / s.TV;
            b[key].Quad(w.P(s0, y0, -o), w.P(s0, y1, -o), w.P(s1, y1, -o), w.P(s1, y0, -o),
                new(Uu(s0), Vv(y0)), new(Uu(s0), Vv(y1)), new(Uu(s1), Vv(y1)), new(Uu(s1), Vv(y0)), col);
        }

        // oriented box: centre c, axes X Y Z (X x Y = Z), size along them; UV = metres along the face axes / tile
        static void OBox(Batch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, Vector3 size, Color col, bool bottom = true)
        {
            var s = S[key];
            foreach (var n in Dirs)
            {
                if (n == Vector3.down && !bottom) continue;
                Vector3 ua = Mathf.Abs(n.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(n, ua);
                float hw = Ext(size, ra) / 2, hh = Ext(size, ua) / 2;
                Vector3 fc = n * Ext(size, n) / 2;
                Vector3 Lp(Vector3 p) => c + Xa * p.x + Ya * p.y + Za * p.z;
                Vector3 wa = Xa * ra.x + Ya * ra.y + Za * ra.z, wu = Xa * ua.x + Ya * ua.y + Za * ua.z;
                Vector3 a = Lp(fc - ra * hw - ua * hh), bb = Lp(fc - ra * hw + ua * hh), cc = Lp(fc + ra * hw + ua * hh), d = Lp(fc + ra * hw - ua * hh);
                Vector2 Uv(Vector3 p) => new(Vector3.Dot(p, wa) / s.TU, Vector3.Dot(p, wu) / s.TV);
                b[key].Quad(a, bb, cc, d, Uv(a), Uv(bb), Uv(cc), Uv(d), col);
            }
        }

        static void Box(Batch b, string key, Fr f, Vector3 c, Vector3 size, Color col, bool bottom = true) => OBox(b, key, f.P(c), f.R, Vector3.up, f.F, size, col, bottom);
        // world (district-local) axis-aligned box from min to max corner
        static void BoxMM(Batch b, string key, Vector3 min, Vector3 max, Color col, bool bottom = true) => OBox(b, key, (min + max) / 2, Vector3.right, Vector3.up, Vector3.forward, max - min, col, bottom);

        // box on a wall: s0..s1 along, y0..y1, `depth` out of the wall (+1 cm into it)
        static void WallBox(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, float depth, Color col)
            => Box(b, key, w, new Vector3((s0 + s1) / 2, (y0 + y1) / 2, (-depth + .01f) / 2), new Vector3(s1 - s0, y1 - y0, depth + .01f), col);

        static void Plane(Batch b, string key, float x0, float z0, float x1, float z1, float y, Color col)
        {
            var s = S[key];
            b[key].Quad(new(x0, y, z0), new(x0, y, z1), new(x1, y, z1), new(x1, y, z0),
                new(x0 / s.TU, z0 / s.TV), new(x0 / s.TU, z1 / s.TV), new(x1 / s.TU, z1 / s.TV), new(x1 / s.TU, z0 / s.TV), col);
        }

        // beam between two points, w x h section
        static void Beam(Batch b, string key, Vector3 p0, Vector3 p1, float w, float h, Color col)
        {
            Vector3 d = p1 - p0; float L = d.magnitude; if (L < 1e-4f) return;
            Vector3 Za = d / L, up = Mathf.Abs(Za.y) > .95f ? Vector3.forward : Vector3.up;
            Vector3 Xa = Vector3.Cross(up, Za).normalized, Ya = Vector3.Cross(Za, Xa);
            OBox(b, key, (p0 + p1) / 2, Xa, Ya, Za, new Vector3(w, h, L), col);
        }

        // cylinder along Ya from base c (Xa x Ya = Za), radius r (top r2), n facets
        static void CylF(Batch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, float r, float h, int n, Color col, bool top = true, bool bottom = false, float r2 = -1f)
        {
            if (r2 < 0) r2 = r;
            var s = S[key]; var mb = b[key];
            float circ = 2 * Mathf.PI * r;
            Vector3 D(float a) => Xa * Mathf.Sin(a) + Za * Mathf.Cos(a);
            Vector3 tc = c + Ya * h;
            for (int i = 0; i < n; i++)
            {
                float a0 = 2 * Mathf.PI * i / n, a1 = 2 * Mathf.PI * (i + 1) / n;
                Vector3 b0 = c + D(a0) * r, b1 = c + D(a1) * r, t0 = tc + D(a0) * r2, t1 = tc + D(a1) * r2;
                float u0 = circ * i / n / s.TU, u1 = circ * (i + 1) / n / s.TU, v1 = h / s.TV;
                mb.Quad(b1, t1, t0, b0, new(u1, 0), new(u1, v1), new(u0, v1), new(u0, 0), col);
                if (top) mb.Tri(tc, t0, t1, new(.5f, .5f), new(.5f + Mathf.Sin(a0) * r2 / s.TU, .5f + Mathf.Cos(a0) * r2 / s.TV), new(.5f + Mathf.Sin(a1) * r2 / s.TU, .5f + Mathf.Cos(a1) * r2 / s.TV), col);
                if (bottom) mb.Tri(c, b1, b0, new(.5f, .5f), new(.5f + Mathf.Sin(a1) * r / s.TU, .5f + Mathf.Cos(a1) * r / s.TV), new(.5f + Mathf.Sin(a0) * r / s.TU, .5f + Mathf.Cos(a0) * r / s.TV), col);
            }
        }
        static void Cyl(Batch b, string key, Vector3 c, float r, float h, int n, Color col, bool top = true, float r2 = -1f) => CylF(b, key, c, Vector3.right, Vector3.up, Vector3.forward, r, h, n, col, top, false, r2);
        // horizontal cylinder (wheels, pipes) along axis
        static void CylAx(Batch b, string key, Vector3 c, Vector3 axis, float r, float len, int n, Color col)
        {
            Vector3 Ya = axis.normalized, Xa = Vector3.Cross(Ya, Mathf.Abs(Ya.y) > .9f ? Vector3.right : Vector3.up).normalized, Za = Vector3.Cross(Xa, Ya);
            CylF(b, key, c - Ya * len / 2, Xa, Ya, Za, r, len, n, col, true, true);
        }

        // flat annulus facing up
        static void Ring(Batch b, string key, Vector3 c, float r0, float r1, int n, Color col)
        {
            var s = S[key];
            for (int i = 0; i < n; i++)
            {
                float a0 = 2 * Mathf.PI * i / n, a1 = 2 * Mathf.PI * (i + 1) / n;
                Vector3 d0 = new(Mathf.Sin(a0), 0, Mathf.Cos(a0)), d1 = new(Mathf.Sin(a1), 0, Mathf.Cos(a1));
                Vector3 p0 = c + d0 * r0, p1 = c + d0 * r1, p2 = c + d1 * r1, p3 = c + d1 * r0;
                Vector2 Uv(Vector3 p) => new(p.x / s.TU, p.z / s.TV);
                b[key].Quad(p0, p1, p2, p3, Uv(p0), Uv(p1), Uv(p2), Uv(p3), col);
            }
        }

        static Transform Group(Transform d, string name) { var g = new GameObject(name).transform; g.SetParent(d, false); return g; }

        // window opening wall (from v06): wall s 0..L, y0..y1 with rectangular openings; reveals `recess` deep in the wall material
        static void OpeningsWall(Batch b, string key, Fr w, float L, float y0, float y1, Color col, List<Rect> holes, float recess)
        {
            var xs = new SortedSet<float> { 0, L }; var ys = new SortedSet<float> { y0, y1 };
            foreach (var h in holes) { xs.Add(Mathf.Clamp(h.xMin, 0, L)); xs.Add(Mathf.Clamp(h.xMax, 0, L)); ys.Add(Mathf.Clamp(h.yMin, y0, y1)); ys.Add(Mathf.Clamp(h.yMax, y0, y1)); }
            var xl = xs.ToList(); var yl = ys.ToList();
            for (int i = 0; i + 1 < xl.Count; i++)
                for (int j = 0; j + 1 < yl.Count; j++)
                {
                    var c = new Vector2((xl[i] + xl[i + 1]) / 2, (yl[j] + yl[j + 1]) / 2);
                    if (holes.Any(h => h.Contains(c))) continue;
                    Wall(b, key, w, xl[i], xl[i + 1], yl[j], yl[j + 1], col);
                }
            foreach (var h in holes)
            {
                Box(b, key, w, new Vector3(h.xMin - .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col);
                Box(b, key, w, new Vector3(h.xMax + .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col);
                Box(b, key, w, new Vector3(h.center.x, h.yMax + .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col);
                if (h.yMin > y0 + .01f) Box(b, key, w, new Vector3(h.center.x, h.yMin - .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col);
            }
        }

        // glass pane with one cell of the 4 x 4 office glass atlas
        static void Pane(Batch b, string key, Fr w, Rect o, float z, int cell)
        {
            int cx = cell % 4, cy = (cell / 4) % 4; const float e = .012f;
            var uv = Rect.MinMaxRect(cx / 4f + e, cy / 4f + e, (cx + 1) / 4f - e, (cy + 1) / 4f - e);
            b[key].Quad(w.P(o.xMin, o.yMin, z), w.P(o.xMin, o.yMax, z), w.P(o.xMax, o.yMax, z), w.P(o.xMax, o.yMin, z),
                new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }

        static int Cell(string id) => (int)(Hash(id, 5) * 16) % 16;

        // office window: atlas glass, frame profile t, `mull` vertical mullions, optional transom (fraction of height), sill
        static void OfficeWindow(Batch b, Fr w, Rect o, float r, string glass, Color frame, string id, int mull, float transom, Color? sill, float t = .06f)
        {
            Pane(b, glass, w, o, r + .005f, Cell(id));
            float zc = r - .03f;
            Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .07f), frame);
            Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .07f), frame);
            Box(b, "flat_metal", w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .07f), frame);
            Box(b, "flat_metal", w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .07f), frame);
            for (int k = 1; k <= mull; k++) Box(b, "flat_metal", w, new Vector3(o.xMin + o.width * k / (mull + 1), o.center.y, zc), new Vector3(t * .9f, o.height, .08f), frame);
            if (transom > 0) Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMin + o.height * transom, zc), new Vector3(o.width, t * .9f, .08f), frame);
            if (sill.HasValue) Box(b, "flat", w, new Vector3(o.center.x, o.yMin - .03f, (r - .07f) / 2), new Vector3(o.width + .12f, .06f, r + .07f), sill.Value);
        }

        // D4 window (from v06 WindowUnit), glass G-D
        static void WindowUnit(Batch b, Fr w, Rect o, float r, bool white, Color frame, Color stone, bool lintel)
        {
            Box(b, "glass_d", w, new Vector3(o.center.x, o.center.y, r + .005f), new Vector3(o.width, o.height, .01f), Color.white);
            float t = .07f, zc = r - .03f;
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .06f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .06f), frame);
            Box(b, "flat", w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame);
            Box(b, "flat", w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.center.y, zc), new Vector3(.05f, o.height, .05f), frame);
            if (white) Box(b, "flat", w, new Vector3(o.center.x, o.yMin + o.height * .64f, zc), new Vector3(o.width, .05f, .05f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin - .04f, (r - .08f) / 2), new Vector3(o.width + .2f, .08f, r + .08f), stone);
            if (lintel) Box(b, "flat", w, new Vector3(o.center.x, o.yMax + .11f, -.015f), new Vector3(o.width + .24f, .22f, .05f), stone);
            else
            {
                Box(b, "flat", w, new Vector3(o.xMin - .06f, o.center.y + .06f, -.012f), new Vector3(.12f, o.height + .12f, .03f), stone);
                Box(b, "flat", w, new Vector3(o.xMax + .06f, o.center.y + .06f, -.012f), new Vector3(.12f, o.height + .12f, .03f), stone);
                Box(b, "flat", w, new Vector3(o.center.x, o.yMax + .06f, -.012f), new Vector3(o.width + .24f, .12f, .03f), stone);
            }
        }

        static void ShopUnit(Batch b, Fr w, Rect o, float r, bool door, Color dark)
        {
            Box(b, "glass_d", w, new Vector3(o.center.x, o.center.y, r + .005f), new Vector3(o.width, o.height, .01f), Color.white);
            float zc = r - .04f;
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin + .05f, zc), new Vector3(o.width, .1f, .08f), dark);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMax - .05f, zc), new Vector3(o.width, .1f, .08f), dark);
            Box(b, "flat", w, new Vector3(o.xMin + .05f, o.center.y, zc), new Vector3(.1f, o.height, .08f), dark);
            Box(b, "flat", w, new Vector3(o.xMax - .05f, o.center.y, zc), new Vector3(.1f, o.height, .08f), dark);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin + 1.95f, zc), new Vector3(o.width, .06f, .06f), dark);
            if (door) Box(b, "flat", w, new Vector3(o.center.x + .2f, o.center.y - .2f, zc), new Vector3(.08f, o.height - .4f, .08f), dark);
            else Box(b, "flat", w, new Vector3(o.center.x, o.yMin + .95f, zc), new Vector3(.05f, 1.9f, .05f), dark);
        }

        // ---------------- props (prefab instances of the map library, read only)
        static readonly List<string> UsedProps = new();
        static GameObject Prop(string rel, Transform parent, Vector3 pos, float yaw, float scale = 1f)
        {
            string path = rel.StartsWith("Assets/") ? rel : MP + rel + ".prefab";
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!src) { Note("prop missing: " + path); return null; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            go.transform.localPosition = pos; go.transform.localRotation = Quaternion.Euler(0, yaw, 0); go.transform.localScale *= scale;
            if (!UsedProps.Contains(path)) UsedProps.Add(path);
            return go;
        }

        // ================================================================== Downtown street context (v06 D4 street profile)
        static void DtStreet(Batch g, float x0, float x1)
        {
            Plane(g, "asphalt", x0, -6, x1, 6, 0, Own("asphalt"));
            foreach (var (z0, z1) in new[] { (6f, 11f), (-11f, -6f) })
                Box(g, "sidewalk", G0, new Vector3((x0 + x1) / 2, Kerb / 2, (z0 + z1) / 2), new Vector3(x1 - x0, Kerb, z1 - z0), Own("sidewalk"));
            Plane(g, "sidewalk", x0, -16, x1, -11, Kerb, Own("sidewalk"));
            Plane(g, "conc", x0, 11, x1, 70, Kerb - .02f, X("BDB8AE"));
            Plane(g, "meadow", x0 - 200, -240, x1 + 200, 240, -.05f, Own("meadow"));
        }
        static Color Own(string key) => S[key].Own;

        // ================================================================== Downtown house (D4 composition + separation options)
        sealed class DH
        {
            public string Id; public float X0, X1, Front = 11f, Back = 25f, Gf = 4f, Fh = 3.3f; public int Floors;
            public string Wall = "plaster", WallCol = "B39562", Base = "brick_d4", BaseCol = "6A4034", Frame = "E4DFD3", Stone = "CFC6B3", Sign;
            public bool Shop = true, WhiteWin, Pilasters, Quoins, GapW, GapE, Penthouse, Downpipe, Rustic, Lintel;
            public string PilKey = "flat", PilCol = "D2CBBE", CorCol = "D8D1C3", StringCol = "D8D1C3", SideCol;
            public int Cornice = 1, WinType; public float StringY = -1f, Setback;
        }

        static void DHouse(Batch b, DH h)
        {
            float zf = h.Front + h.Setback, zb = h.Back;
            float top = h.Gf + (h.Floors - 1) * h.Fh, topMain = h.Penthouse ? top - h.Fh : top;
            Color wc = X(h.WallCol), bc = h.BaseCol == null ? Own(h.Base) : X(h.BaseCol), frame = X(h.Frame), stone = X(h.Stone), side = h.SideCol != null ? X(h.SideCol) : wc;
            const float gw = .6f, gd = 1.5f;                                      // shadow gap: 1.2 m wide (two halves), 1.5 m deep
            float x0 = h.X0 + (h.GapW ? gw : 0), x1 = h.X1 - (h.GapE ? gw : 0), L = x1 - x0;
            var f = Fr.Yaw(new Vector3(0, Kerb, 0), 0);
            var w = f.Wall(new Vector2(x0, zf), new Vector2(x1, zf));
            int bays = Mathf.Max(1, Mathf.RoundToInt(L / 3.1f));
            float bw = L / bays;
            float Bay(int k) => bw * (k + .5f);
            float cw = h.Pilasters || h.Quoins ? .6f : 0f;                       // keep windows off the pilasters
            // upper floors
            var holes = new List<(Rect r, int type)>();
            for (int fl = 1; fl < h.Floors - (h.Penthouse ? 1 : 0); fl++)
            {
                float yf = h.Gf + (fl - 1) * h.Fh;
                for (int k = 0; k < bays; k++)
                {
                    float c = Bay(k);
                    if (c - .9f < cw || c + .9f > L - cw) c = Mathf.Clamp(c, cw + .95f, L - cw - .95f);
                    switch (h.WinType)
                    {
                        case 1: holes.Add((Rect.MinMaxRect(c - .85f, yf + .8f, c - .1f, yf + 2.75f), 1)); holes.Add((Rect.MinMaxRect(c + .1f, yf + .8f, c + .85f, yf + 2.75f), 1)); break;
                        case 2: if (k % 2 == 0) { holes.Add((Rect.MinMaxRect(c - 1.05f, yf + .8f, c - .4f, yf + 2.7f), 2)); holes.Add((Rect.MinMaxRect(c - .32f, yf + .8f, c + .32f, yf + 2.7f), 2)); holes.Add((Rect.MinMaxRect(c + .4f, yf + .8f, c + 1.05f, yf + 2.7f), 2)); }
                            else holes.Add((Rect.MinMaxRect(c - .6f, yf + .8f, c + .6f, yf + 2.7f), 0)); break;
                        default: holes.Add((Rect.MinMaxRect(c - .75f, yf + .8f, c + .75f, yf + 2.75f), h.WinType)); break;
                    }
                }
            }
            OpeningsWall(b, h.Wall, w, L, h.Gf, topMain, wc, holes.Select(q => q.r).ToList(), .22f);
            foreach (var (o, type) in holes)
            {
                WindowUnit(b, w, o, .22f, h.WhiteWin && type != 1, frame, stone, h.Lintel);
                if (type == 3)
                {   // pediment-like hood: projecting cap + small raised centre block
                    WallBox(b, "flat", w, o.xMin - .22f, o.xMax + .22f, o.yMax + .22f, o.yMax + .36f, .16f, stone);
                    WallBox(b, "flat", w, o.center.x - .35f, o.center.x + .35f, o.yMax + .36f, o.yMax + .5f, .1f, stone);
                }
            }
            // ground floor
            string gk = h.Rustic ? "ashlar" : h.Base; Color gc = h.Rustic ? X(h.StringCol) : bc;
            var ground = new List<Rect>();
            if (h.Shop) for (int k = 0; k < bays; k++) { float c = Mathf.Clamp(Bay(k), cw + 1.4f, L - cw - 1.4f); ground.Add(Rect.MinMaxRect(c - 1.3f, .45f, c + 1.3f, 3.0f)); }
            else { ground.Add(Rect.MinMaxRect(L / 2 - .75f, -Kerb, L / 2 + .75f, 2.6f)); foreach (float c in new[] { Mathf.Max(cw + 1f, 1.4f), Mathf.Min(L - cw - 1f, L - 1.4f) }) ground.Add(Rect.MinMaxRect(c - .65f, .9f, c + .65f, 2.6f)); }
            OpeningsWall(b, gk, w, L, -Kerb, h.Gf, gc, ground, .25f);
            for (int j = 0; j < ground.Count; j++)
            {
                var o = ground[j];
                if (h.Shop) ShopUnit(b, w, o, .25f, j == ground.Count - 1, X("2F3538"));
                else if (o.yMin < 0) { Box(b, "flat", w, new Vector3(o.center.x, o.center.y, .255f), new Vector3(o.width, o.height, .01f), X("4A3A30")); }
                else WindowUnit(b, w, o, .25f, false, frame, stone, false);
            }
            if (!h.Rustic) WallBox(b, "flat", w, 0, L, -Kerb, .45f, .07f, stone);                                  // plinth
            if (h.Sign != null) WallBox(b, "flat", w, cw + .3f, L - cw - .3f, 3.15f, 3.8f, .07f, X(h.Sign));
            WallBox(b, "flat", w, 0, L, h.Gf, h.Gf + .35f, .1f, X(h.StringCol));                                      // belt course over the shops
            if (h.StringY > 0) WallBox(b, "flat", w, 0, L, h.StringY, h.StringY + .2f, .08f, X(h.StringCol));
            // pilasters / quoins at both ends
            if (h.Pilasters) foreach (var (a, c) in new[] { (0f, .55f), (L - .55f, L) }) WallBox(b, h.PilKey, w, a, c, h.Gf + .35f, topMain, .12f, X(h.PilCol));
            if (h.Quoins)
                for (float y = h.Gf + .35f; y < topMain - .3f; y += .6f)
                {
                    bool wide = Mathf.RoundToInt((y - h.Gf) / .6f) % 2 == 0;
                    float qw = wide ? .75f : .45f;
                    WallBox(b, h.PilKey, w, 0, qw, y, Mathf.Min(y + .55f, topMain), .1f, X(h.PilCol));
                    WallBox(b, h.PilKey, w, L - qw, L, y, Mathf.Min(y + .55f, topMain), .1f, X(h.PilCol));
                }
            // cornice (own height and profile per house) + parapet
            Color cc = X(h.CorCol);
            switch (h.Cornice)
            {
                case 1: WallBox(b, "flat", w, -.02f, L + .02f, topMain - .4f, topMain, .35f, cc); break;
                case 2:
                    WallBox(b, "flat", w, 0, L, topMain - .75f, topMain - .5f, .12f, cc);
                    WallBox(b, "flat", w, 0, L, topMain - .5f, topMain - .28f, .26f, cc);
                    WallBox(b, "flat", w, -.05f, L + .05f, topMain - .28f, topMain, .5f, cc); break;
                case 3:
                    WallBox(b, "flat", w, -.02f, L + .02f, topMain - .35f, topMain, .45f, cc);
                    for (float s = .5f; s < L - .2f; s += 1f) WallBox(b, "flat", w, s - .08f, s + .08f, topMain - .7f, topMain - .35f, .32f, cc);
                    break;
            }
            Wall(b, h.Wall, w, 0, L, topMain, topMain + (h.Cornice > 0 ? .55f : .9f), wc);
            WallBox(b, "flat", w, -.02f, L + .02f, topMain + (h.Cornice > 0 ? .55f : .9f), topMain + (h.Cornice > 0 ? .67f : 1.02f), .06f, X("8E8A84"));
            // sides, back, gaps, roof
            float zs = h.GapW ? zf + gd : zf;
            Wall(b, h.Wall, f.Wall(new Vector2(h.X0, zb), new Vector2(h.X0, zs)), 0, zb - zs, -Kerb, topMain + .6f, side);
            zs = h.GapE ? zf + gd : zf;
            Wall(b, h.Wall, f.Wall(new Vector2(h.X1, zs), new Vector2(h.X1, zb)), 0, zb - zs, -Kerb, topMain + .6f, side);
            Wall(b, h.Wall, f.Wall(new Vector2(h.X1, zb), new Vector2(h.X0, zb)), 0, h.X1 - h.X0, -Kerb, topMain, side);
            Color gapDark = X("3A3634");
            if (h.GapW)
            {
                Wall(b, h.Wall, f.Wall(new Vector2(x0, zf + gd), new Vector2(x0, zf)), 0, gd, -Kerb, topMain + .55f, wc * .9f);
                Wall(b, h.Wall, f.Wall(new Vector2(h.X0, zf + gd), new Vector2(x0, zf + gd)), 0, gw, -Kerb, topMain, gapDark);
            }
            if (h.GapE)
            {
                Wall(b, h.Wall, f.Wall(new Vector2(x1, zf), new Vector2(x1, zf + gd)), 0, gd, -Kerb, topMain + .55f, wc * .9f);
                Wall(b, h.Wall, f.Wall(new Vector2(x1, zf + gd), new Vector2(h.X1, zf + gd)), 0, gw, -Kerb, topMain, gapDark);
            }
            Plane(b, "roof_flat", x0, zf, x1, zb, Kerb + topMain + .02f, Own("roof_flat"));
            if (h.GapW || h.GapE) Plane(b, "roof_flat", h.X0, zf + gd, h.X1, zb, Kerb + topMain + .01f, Own("roof_flat"));
            if (h.Penthouse)
            {   // top floor set back 1.8 m behind a railing
                float pz = zf + 1.8f;
                var pw = f.Wall(new Vector2(x0 + .3f, pz), new Vector2(x1 - .3f, pz)); float PL = L - .6f;
                var ph = new List<Rect>();
                for (float s = 1.2f; s < PL - 1f; s += 2.4f) ph.Add(Rect.MinMaxRect(s - .8f, topMain + .3f, s + .8f, topMain + 2.7f));
                OpeningsWall(b, h.Wall, pw, PL, topMain, top, wc, ph, .12f);
                foreach (var o in ph) WindowUnit(b, pw, o, .12f, false, frame, stone, false);
                Wall(b, h.Wall, f.Wall(new Vector2(x0 + .3f, zb), new Vector2(x0 + .3f, pz)), 0, zb - pz, topMain, top, side);
                Wall(b, h.Wall, f.Wall(new Vector2(x1 - .3f, pz), new Vector2(x1 - .3f, zb)), 0, zb - pz, topMain, top, side);
                WallBox(b, "flat", pw, -.05f, PL + .05f, top, top + .3f, .25f, cc);
                Plane(b, "roof_flat", x0 + .3f, pz, x1 - .3f, zb, Kerb + top + .02f, Own("roof_flat"));
                for (float s = .1f; s <= L; s += 1.2f) Box(b, "flat_metal", w, new Vector3(Mathf.Min(s, L - .05f), topMain + .67f + .5f, .25f), new Vector3(.05f, 1f, .05f), X("2F3437"));
                Box(b, "flat_metal", w, new Vector3(L / 2, topMain + 1.7f, .25f), new Vector3(L, .06f, .08f), X("2F3437"));
            }
            if (h.Downpipe) Cyl(b, "flat_metal", f.P(x1 - .14f, -Kerb, zf - .1f), .055f, topMain + Kerb, 8, X("6E7376"), false);
        }

        // ================================================================== 1. Downtown offices O1-O3
        static void Offices(Transform d)
        {
            var g = new Batch();
            DtStreet(g, -70, 60);
            var ctx = Group(d, "Context");
            DHouse(g, new DH { Id = "N1", X0 = -30, X1 = -16, Floors = 5, Wall = "plaster", WallCol = "5F6C75", Base = "brick_d4", BaseCol = "5E3B33", Sign = "2F3A36", Stone = "BDB5A5" });
            DHouse(g, new DH { Id = "N2", X0 = 16, X1 = 28, Floors = 4, Wall = "brick_d4", WallCol = "8A4E3F", Base = "brick_d4", BaseCol = "7A4437", Lintel = true, WhiteWin = true, Sign = "4E3431", Stone = "D1C8B6" });
            DHouse(g, new DH { Id = "N0", X0 = -44, X1 = -30, Floors = 6, Wall = "plaster", WallCol = "B39562", Base = "plaster", BaseCol = "A49C8B", Shop = false, Stone = "CEC4B1", Frame = "33463D" });
            DHouse(g, new DH { Id = "N3", X0 = 28, X1 = 40, Floors = 5, Wall = "plaster", WallCol = "7D8766", Stone = "CFC7B4", Frame = "2F3437", Sign = "34404F" });
            Flush(g, ctx, "Off_ctx");
            foreach (float x in new[] { -22f, -4f, 14f }) Prop("LAMPS/lamp_oldtown_single", ctx, new Vector3(x, Kerb, 6.7f), 90);
            Prop("CARS/car_sedan_beige", ctx, new Vector3(-12f, 0, 4.6f), 90);
            Prop("CARS/car_sedan_blue", ctx, new Vector3(22f, 0, -4.6f), -90);
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "O" + v);
                var b = new Batch();
                Office(b, v);
                Flush(b, grp, "Off_O" + v);
            }
        }

        static void Office(Batch b, int v)
        {
            const float L = 32f, x0 = -16f, zf = 11f, zb = 25f, Gf = 4.5f, Fh = 3.6f;
            const int floors = 6, bays = 10; const float bw = L / bays;
            float top = Gf + (floors - 1) * Fh;                                  // 22.5 m
            var f = Fr.Yaw(new Vector3(0, Kerb, 0), 0);
            var w = f.Wall(new Vector2(x0, zf), new Vector2(x0 + L, zf));
            float Bay(int k) => bw * (k + .5f);
            string id = "O" + v;
            string clad; Color cl; string glass; Color frame;
            switch (v)
            {
                case 1:
                {   // O1 stone grid: travertine panels, projecting piers, punched 2.3 x 2.3 windows with bronze frames, dark granite base
                    clad = "travertine"; cl = X("E2D8C6"); glass = Glass("glass_o1", "C6D2DC"); frame = X("4B4239");
                    var holes = new List<Rect>();
                    for (int fl = 1; fl < floors; fl++) { float yf = Gf + (fl - 1) * Fh; for (int k = 0; k < bays; k++) holes.Add(Rect.MinMaxRect(Bay(k) - 1.15f, yf + .85f, Bay(k) + 1.15f, yf + 3.15f)); }
                    OpeningsWall(b, clad, w, L, Gf, top, cl, holes, .32f);
                    int i = 0; foreach (var o in holes) OfficeWindow(b, w, o, .32f, glass, frame, id + i++, 1, .72f, X("D6CDBD"));
                    for (int k = 0; k <= bays; k++) { float s = k * bw; WallBox(b, clad, w, Mathf.Max(0, s - .33f), Mathf.Min(L, s + .33f), Gf, top + .9f, .14f, cl); }
                    for (int fl = 1; fl < floors; fl++) WallBox(b, clad, w, 0, L, Gf + (fl - 1) * Fh - .12f, Gf + (fl - 1) * Fh + .12f, .06f, cl);
                    // base: dark granite, tall glazing, recessed entrance with canopy
                    Color dk = X("4A4B4E");
                    var gh = new List<Rect>();
                    for (int k = 0; k < bays; k++) if (k != 4 && k != 5) gh.Add(Rect.MinMaxRect(Bay(k) - 1.3f, .35f, Bay(k) + 1.3f, 3.95f));
                    gh.Add(Rect.MinMaxRect(L / 2 - 2.9f, -Kerb, L / 2 + 2.9f, 3.95f));
                    OpeningsWall(b, "stone", w, L, -Kerb, Gf, dk, gh, .3f);
                    i = 0; foreach (var o in gh) OfficeWindow(b, w, o, o.yMin < 0 ? 1.2f : .3f, glass, frame, id + "g" + i++, o.yMin < 0 ? 3 : 1, o.yMin < 0 ? .7f : .75f, null, .08f);
                    if (true) { var o = gh.Last(); foreach (float s in new[] { o.xMin, o.xMax }) Box(b, "stone", w, new Vector3(s, Gf / 2, .6f), new Vector3(.02f, Gf, 1.2f), dk); Box(b, "flat", w, new Vector3(o.center.x, o.yMax + .005f, .6f), new Vector3(o.width, .01f, 1.2f), X("D9D4CA")); }
                    WallBox(b, "flat_metal", w, L / 2 - 4f, L / 2 + 4f, Gf - .3f, Gf - .05f, 2.4f, X("3A3C3F"));       // canopy
                    WallBox(b, "flat_metal", w, -.02f, L + .02f, top + .9f, top + 1.05f, .2f, X("8C8478"));             // coping
                    WallBox(b, "flat_metal", w, 1.5f, 9f, 2.8f, 3.4f, .08f, X("3A3C3F"));                               // name plate band
                    break;
                }
                case 2:
                {   // O2 brick + ribbon windows: long-format brick, continuous ribbons with slim dark mullions every 1.6 m, light concrete ledges
                    clad = "brick_roman"; cl = Own("brick_roman"); glass = Glass("glass_o2", "C6D6CC"); frame = X("33383C");
                    var holes = new List<Rect>();
                    for (int fl = 1; fl < floors; fl++) { float yf = Gf + (fl - 1) * Fh; holes.Add(Rect.MinMaxRect(1.2f, yf + .9f, L - 1.2f, yf + 2.9f)); }
                    OpeningsWall(b, clad, w, L, Gf, top + .8f, cl, holes, .2f);
                    int i = 0;
                    foreach (var o in holes)
                    {
                        int n = Mathf.RoundToInt(o.width / 1.6f); float pw = o.width / n;
                        for (int k = 0; k < n; k++) Pane(b, glass, w, Rect.MinMaxRect(o.xMin + k * pw, o.yMin, o.xMin + (k + 1) * pw, o.yMax), .205f, Cell(id + i++));
                        for (int k = 0; k <= n; k++) Box(b, "flat_metal", w, new Vector3(o.xMin + k * pw, o.center.y, .15f), new Vector3(k == 0 || k == n ? .1f : .07f, o.height, .12f), frame);
                        Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMax - .04f, .15f), new Vector3(o.width, .08f, .12f), frame);
                        Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMin + .04f, .15f), new Vector3(o.width, .08f, .12f), frame);
                        WallBox(b, "conc", w, o.xMin - .3f, o.xMax + .3f, o.yMin - .2f, o.yMin, .24f, X("D3CEC4"));        // ledge
                    }
                    // ground: brick piers every 6.4 m, black steel shopfronts, door in the middle
                    var gh = new List<Rect>();
                    for (int k = 0; k < 5; k++) gh.Add(Rect.MinMaxRect(k * 6.4f + .45f, k == 2 ? -Kerb : .25f, (k + 1) * 6.4f - .45f, 3.9f));
                    OpeningsWall(b, clad, w, L, -Kerb, Gf, cl, gh, .3f);
                    i = 0; foreach (var o in gh) OfficeWindow(b, w, o, .3f, glass, X("232527"), id + "g" + i++, 2, .78f, null, .09f);
                    WallBox(b, "conc", w, 0, L, Gf - .25f, Gf + .1f, .14f, X("D3CEC4"));
                    WallBox(b, "conc", w, -.02f, L + .02f, top + .8f, top + .98f, .1f, X("D3CEC4"));                 // coping
                    WallBox(b, "flat_metal", w, L / 2 - 3.6f, L / 2 + 3.6f, 3.95f, 4.15f, 1.6f, X("232527"));        // entrance canopy
                    break;
                }
                default:
                {   // O3 precast concrete frame: deep projecting window boxes (egg-crate), white frames, blue-green glass, recessed arcade
                    clad = "panel"; cl = X("CFCBC2"); glass = Glass("glass_o3", "BCD8E2"); frame = X("E6E8E6");
                    var holes = new List<Rect>();
                    for (int fl = 1; fl < floors; fl++) { float yf = Gf + (fl - 1) * Fh; for (int k = 0; k < bays; k++) holes.Add(Rect.MinMaxRect(Bay(k) - 1.25f, yf + .75f, Bay(k) + 1.25f, yf + 3.05f)); }
                    OpeningsWall(b, clad, w, L, Gf, top + 1f, cl, holes, .15f);
                    int i = 0;
                    foreach (var o in holes)
                    {
                        OfficeWindow(b, w, o, .15f, glass, frame, id + i++, 2, 0f, null, .05f);
                        WallBox(b, clad, w, o.xMin - .2f, o.xMax + .2f, o.yMax, o.yMax + .2f, .42f, cl);
                        WallBox(b, clad, w, o.xMin - .2f, o.xMax + .2f, o.yMin - .2f, o.yMin, .42f, cl);
                        WallBox(b, clad, w, o.xMin - .2f, o.xMin, o.yMin - .2f, o.yMax + .2f, .42f, cl);
                        WallBox(b, clad, w, o.xMax, o.xMax + .2f, o.yMin - .2f, o.yMax + .2f, .42f, cl);
                    }
                    WallBox(b, clad, w, -.02f, L + .02f, top + .1f, top + 1.1f, .5f, cl);                              // deep fascia
                    // arcade: glazing 2 m back, columns, soffit
                    var w2 = f.Wall(new Vector2(x0, zf + 2f), new Vector2(x0 + L, zf + 2f));
                    var gh = new List<Rect>();
                    for (int k = 0; k < bays; k++) gh.Add(Rect.MinMaxRect(Bay(k) - 1.4f, k == 5 ? -Kerb : .1f, Bay(k) + 1.4f, 4.1f));
                    OpeningsWall(b, "conc", w2, L, -Kerb, Gf, X("D8D5CE"), gh, .1f);
                    i = 0; foreach (var o in gh) OfficeWindow(b, w2, o, .1f, glass, X("3A3D40"), id + "g" + i++, 1, .8f, null, .07f);
                    for (int k = 0; k <= bays; k++) Box(b, "conc", f, new Vector3(x0 + Mathf.Clamp(k * bw, .28f, L - .28f), Gf / 2 - Kerb / 2, zf + .28f), new Vector3(.55f, Gf + Kerb, .55f), cl);
                    Box(b, "conc", f, new Vector3(0, Gf - .1f, zf + 1f), new Vector3(L, .2f, 2f), X("DCD8D0"));
                    Wall(b, clad, f.Wall(new Vector2(x0, zf + 2f), new Vector2(x0, zf)), 0, 2f, -Kerb, Gf, cl);
                    Wall(b, clad, f.Wall(new Vector2(x0 + L, zf), new Vector2(x0 + L, zf + 2f)), 0, 2f, -Kerb, Gf, cl);
                    Plane(b, "stone", x0, zf, x0 + L, zf + 2f, Kerb + .005f, X("BEB9B0"));
                    break;
                }
            }
            // party walls (exposed above the neighbours), back, roof, plant room
            Wall(b, clad, f.Wall(new Vector2(x0, zb), new Vector2(x0, zf)), 0, zb - zf, -Kerb, top + 1f, cl);
            Wall(b, clad, f.Wall(new Vector2(x0 + L, zf), new Vector2(x0 + L, zb)), 0, zb - zf, -Kerb, top + 1f, cl);
            Wall(b, clad, f.Wall(new Vector2(x0 + L, zb), new Vector2(x0, zb)), 0, L, -Kerb, top + 1f, cl);
            Plane(b, "roof_flat", x0, zf, x0 + L, zb, Kerb + top + .02f, Own("roof_flat"));
            Box(b, "trapez", f, new Vector3(2f, top + 1.6f, 19f), new Vector3(10f, 3.2f, 6f), X("A8ADB0"));
        }

        // ================================================================== 2. Downtown street separation DS1-DS3
        static void Street(Transform d)
        {
            var g = new Batch();
            DtStreet(g, -60, 60);
            var ctx = Group(d, "Context");
            Flush(g, ctx, "St_ctx");
            foreach (float x in new[] { -28f, -10f, 8f, 26f }) Prop("LAMPS/lamp_oldtown_single", ctx, new Vector3(x, Kerb, 6.7f), 90);
            Prop("CARS/car_sedan_green", ctx, new Vector3(-2f, 0, 4.6f), 90);
            Prop("CARS/car_hatchback", ctx, new Vector3(16f, 0, -4.6f), -90);
            // the same 7 houses (3-6 floors, Fedya 22.10) in three separation treatments
            (float x0, float x1, int fl, string wall, string col, string bas, string bcol)[] row =
            {
                (-36, -24, 4, "plaster", "B39562", "brick_d4", "6A4034"), (-24, -14, 6, "brick_d4", "8A4E3F", "brick_d4", "7A4437"),
                (-14, -5, 3, "plaster", "7D8766", "plaster", "A49C8B"), (-5, 8, 5, "plaster", "5F6C75", "brick_d4", "5E3B33"),
                (8, 17, 4, "plaster", "C6BBA3", "plaster", "A8A08F"), (17, 30, 6, "brick_d4", "9A5A46", "brick_d4", "6A4034"),
                (30, 38, 3, "plaster", "A8AA9A", "plaster", "9A9C8C"),
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "DS" + v);
                var b = new Batch();
                for (int i = 0; i < row.Length; i++)
                {
                    var r = row[i];
                    var h = new DH { Id = $"DS{v}_{i}", X0 = r.x0, X1 = r.x1, Floors = r.fl, Wall = r.wall, WallCol = r.col, Base = r.bas, BaseCol = r.bcol, Shop = i % 3 != 2,
                        Sign = i % 3 == 0 ? "2F3A36" : i % 3 == 1 ? "4E3431" : null, Lintel = r.wall == "brick_d4", WhiteWin = i % 2 == 1, Cornice = 1, Stone = "CFC6B3" };
                    if (v == 1)
                    {   // DS1: own corner pilasters (stone or brick quoins) + own cornice height / profile = a visible break at every party wall
                        h.Pilasters = i % 2 == 0; h.Quoins = i % 2 == 1; h.PilKey = i % 2 == 0 ? "stone" : "flat";
                        h.PilCol = new[] { "D8D0C0", "D9D2C4", "CBC3B2", "DAD3C6", "B9B2A3", "E0D9CB", "C9C1B0" }[i];
                        h.Cornice = new[] { 2, 3, 1, 2, 3, 2, 1 }[i];
                        h.CorCol = new[] { "DCD4C4", "E2DBCD", "CFC7B6", "D8D1C3", "BDB5A5", "E4DDD0", "D2CBBB" }[i];
                        h.SideCol = Shade(r.col, .92f);
                    }
                    else if (v == 2)
                    {   // DS2: alternating building line (0.6 m setbacks), 1 m recessed shadow gaps, penthouse setback on the tall houses, downpipes
                        h.Setback = i % 2 == 0 ? 1f : 0f;
                        h.GapE = i == 1 || i == 3 || i == 5; h.GapW = i == 2 || i == 4 || i == 6;
                        h.Penthouse = r.fl >= 6; h.Downpipe = !h.GapE; h.Cornice = i % 2 == 0 ? 1 : 0;
                        h.CorCol = "D3CCBE";
                    }
                    else
                    {   // DS3: different base (rusticated / brick / plaster), string courses at different heights, window types, trim colours
                        h.Rustic = i == 1 || i == 3 || i == 5; h.StringCol = new[] { "E4DCCB", "CFC6B3", "D9D0BD", "C7BFAE", "E9E2D3", "BFB6A4", "DED6C6" }[i];
                        h.StringY = h.Gf + h.Fh * (i % 2 == 0 ? 1 : 2) - .1f; h.WinType = new[] { 3, 1, 0, 2, 3, 1, 0 }[i];
                        h.Cornice = new[] { 2, 1, 3, 0, 2, 3, 1 }[i]; h.CorCol = h.StringCol; h.Frame = new[] { "E4DFD3", "2F3437", "E9E4D8", "33463D", "E4DFD3", "4A3A30", "2F3437" }[i];
                        h.Downpipe = true;
                    }
                    DHouse(b, h);
                }
                Flush(b, grp, "St_DS" + v);
            }
        }

        static string Shade(string hex, float k) { var c = X(hex) * k; return ColorUtility.ToHtmlStringRGB(c); }

        // ================================================================== 3. Downtown centre (plaza "Water axis") DC1-DC3
        sealed class DCPal { public string Slab, SlabCol, Band, BandCol, Coping, CopCol, PoolCol, KioskCol, KioskTrim, KioskRoof, BenchWood, BenchMetal, LampCol, BollCol, Banner1, Banner2; }

        static void Square(Transform d)
        {
            var g = new Batch();
            Plane(g, "asphalt", -80, -17, 80, -5.2f, 0, Own("asphalt"));
            Box(g, "stone", G0, new Vector3(0, Kerb / 2, -5.1f), new Vector3(160, Kerb, .25f), X("B9B4AA"));
            foreach (var (a0, a1, c0, c1) in new[] { (-260f, 260f, -260f, 15.5f), (-260f, -8.5f, 15.5f, 50.5f), (8.5f, 260f, 15.5f, 50.5f), (-260f, 260f, 50.5f, 260f) })
                Plane(g, "meadow", a0, c0, a1, c1, -.05f, Own("meadow"));        // no ground under the pool basin
            Plane(g, "sidewalk", -80, -40, 80, -17, Kerb, Own("sidewalk"));
            // twin-tower podium context (glass), stairs come per variant
            Box(g, "flat", G0, new Vector3(0, 3f, 69f), new Vector3(60f, 6f, 14f), X("B9B4AA"));
            // city around the square: house rows on both sides and behind the podium (D4 look, context only)
            foreach (var (x0, x1, fl, wall, col, z) in new[] { (-100f, -82f, 5, "plaster", "B39562", 0f), (-82f, -64f, 6, "brick_d4", "8A4E3F", 0f), (-64f, -46f, 4, "plaster", "5F6C75", 0f),
                (46f, 64f, 4, "plaster", "7D8766", 0f), (64f, 82f, 6, "plaster", "C6BBA3", 0f), (82f, 100f, 5, "brick_d4", "9A5A46", 0f),
                (-56f, -36f, 6, "plaster", "A8AA9A", 82f), (-36f, -14f, 5, "brick_d4", "8A4E3F", 82f), (14f, 36f, 6, "plaster", "B39562", 82f), (36f, 56f, 5, "plaster", "5F6C75", 82f) })
                DHouse(g, new DH { Id = "SQ" + x0, X0 = x0, X1 = x1, Front = z, Back = z + 14f, Floors = fl, Wall = wall, WallCol = col, Lintel = wall == "brick_d4", Sign = "2F3A36" });
            Plane(g, "sidewalk", -100f, -5f, -40f, 0f, .01f, Own("sidewalk"));
            Plane(g, "sidewalk", 40f, -5f, 100f, 0f, .01f, Own("sidewalk"));
            var ctx = Group(d, "Context");
            Flush(g, ctx, "Sq_ctx");
            var gl = new Batch();
            var pw = G0.Wall(new Vector2(-30, 62.2f), new Vector2(30, 62.2f));
            for (float s = 0; s < 60f; s += 3f) Pane(gl, Glass("glass_dc_podium", "6E8FB8"), pw, Rect.MinMaxRect(s + .06f, 2.4f, s + 2.94f, 5.7f), -.02f, Cell("pod" + s));
            Flush(gl, ctx, "Sq_podium");
            Prop("BUS_STOP/busstop_shelter", ctx, new Vector3(24f, Kerb, -19f), 180);
            Prop("CARS/car_sedan_red", ctx, new Vector3(-14f, 0, -8.5f), 90);
            var pals = new[]
            {
                new DCPal { Slab = "slab_warm", SlabCol = "CFC5B4", Band = "stone", BandCol = "4C4B4C", Coping = "slab_grey", CopCol = "D9D4CB", PoolCol = "3E93B8",
                    KioskCol = "E9E6DF", KioskTrim = "3C4045", KioskRoof = "3C4045", BenchWood = "teak", BenchMetal = "3C4045", LampCol = "34404F", BollCol = "3C4045", Banner1 = "E2B437", Banner2 = "2F5FA0" },
                new DCPal { Slab = "slab_lime", SlabCol = "DCD0BA", Band = "stone", BandCol = "3E3B37", Coping = "travertine", CopCol = "E2D6C0", PoolCol = "2F4C5A",
                    KioskCol = "2F4A3E", KioskTrim = "B08D57", KioskRoof = "2F4A3E", BenchWood = "larch", BenchMetal = "2F4A3E", LampCol = "2F4A3E", BollCol = "2F4A3E", Banner1 = "B08D57", Banner2 = "8A3A34" },
                new DCPal { Slab = "slab_grey", SlabCol = "CACAC5", Band = "stone", BandCol = "3A3D42", Coping = "conc", CopCol = "D3D2CD", PoolCol = "47B4C6",
                    KioskCol = "383C40", KioskTrim = "D6D4CE", KioskRoof = "383C40", BenchWood = "larch", BenchMetal = "B8BABB", LampCol = "E6E6E2", BollCol = "383C40", Banner1 = "E07A2E", Banner2 = "3A3D42" },
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "DC" + v);
                var b = new Batch();
                SquareVariant(b, grp, pals[v - 1], "DC" + v);
                Flush(b, grp, "Sq_DC" + v);
            }
        }

        static void SquareVariant(Batch b, Transform grp, DCPal p, string code)
        {
            Color slab = X(p.SlabCol), band = X(p.BandCol), cop = X(p.CopCol);
            const float PX = 36f, Z0 = -4.8f, Z1 = 52f;
            // paving 1 x 1 m (one tone), dark 0.5 m band along the edge
            foreach (var (a0, a1, c0, c1) in new[] { (-PX, PX, Z0, 15f), (-PX, -9f, 15f, 51f), (9f, PX, 15f, 51f), (-PX, PX, 51f, Z1) })
                Plane(b, p.Slab, a0, c0, a1, c1, .01f, slab);                  // paving round the pool (pool + band cut out)
            Plane(b, p.Slab, -9f, 15f, 9f, 15.5f, .01f, slab); Plane(b, p.Slab, -9f, 50.5f, 9f, 51f, .01f, slab);
            Plane(b, p.Slab, -9f, 15.5f, -8.5f, 50.5f, .01f, slab); Plane(b, p.Slab, 8.5f, 15.5f, 9f, 50.5f, .01f, slab);
            foreach (var (a0, a1, c0, c1) in new[] { (-PX, PX, Z0, Z0 + .5f), (-PX, -PX + .5f, Z0, Z1), (PX - .5f, PX, Z0, Z1) })
                Plane(b, p.Band, a0, c0, a1, c1, .015f, band);
            // mirror pool 16 x 36 m, ~30 cm: coping, inner walls and bottom in mosaic, water just under the coping
            const float px = 8f, pz0 = 16f, pz1 = 50f;
            foreach (var (a0, a1, c0, c1) in new[] { (-px - 1f, px + 1f, pz0 - 1f, pz0 - .5f), (-px - 1f, px + 1f, pz1 + .5f, pz1 + 1f), (-px - 1f, -px - .5f, pz0 - .5f, pz1 + .5f), (px + .5f, px + 1f, pz0 - .5f, pz1 + .5f) })
                Plane(b, p.Band, a0, c0, a1, c1, .016f, band);                // dark 0.5 m band round the pool coping
            Plane(b, "mosaic", -px, pz0, px, pz1, -.32f, X(p.PoolCol));
            foreach (var (a, c) in new[] { (new Vector2(-px, pz0), new Vector2(px, pz0)), (new Vector2(px, pz0), new Vector2(px, pz1)), (new Vector2(px, pz1), new Vector2(-px, pz1)), (new Vector2(-px, pz1), new Vector2(-px, pz0)) })
            {
                var w = G0.Wall(c, a);                                  // inner faces look into the pool
                Wall(b, "mosaic", w, 0, (c - a).magnitude, -.32f, .02f, X(p.PoolCol));
            }
            foreach (var (mn, mx) in new[] { (new Vector3(-px - .5f, 0, pz0 - .5f), new Vector3(px + .5f, .14f, pz0)), (new Vector3(-px - .5f, 0, pz1), new Vector3(px + .5f, .14f, pz1 + .5f)),
                (new Vector3(-px - .5f, 0, pz0), new Vector3(-px, .14f, pz1)), (new Vector3(px, 0, pz0), new Vector3(px + .5f, .14f, pz1)) })
                BoxMM(b, p.Coping, mn, mx, cop);
            string wk = "water_" + code;                                          // pool water per variant (DC2 = dark mirror)
            if (!S.ContainsKey(wk)) LitS(wk, code == "DC2" ? new Color(.16f, .27f, .33f, .72f) : code == "DC3" ? new Color(.38f, .74f, .82f, .45f) : new Color(.30f, .60f, .78f, .5f), null, 1, 1, .85f, 0f, 2, false, true);
            Plane(b, wk, -px, pz0, px, pz1, -.06f, Color.white);
            // monument ring (dark band R 7 m) + podium, dry fountain jets as small grates
            Ring(b, p.Band, new Vector3(0, .017f, 7f), 6.5f, 7f, 64, band);
            Cyl(b, p.Band, new Vector3(0, 0, 7f), 2.2f, .5f, 32, band);
            Cyl(b, p.Coping, new Vector3(0, .5f, 7f), 1.7f, .6f, 32, cop);
            for (int i = 0; i < 16; i++) { float a = i * Mathf.PI / 8; Cyl(b, "flat_metal", new Vector3(Mathf.Sin(a) * 4.5f, .012f, 7f + Mathf.Cos(a) * 4.5f), .12f, .01f, 8, X("6E7174")); }
            // tribune stairs with the water cascade in the middle (2.25 m up to the podium terrace)
            for (int s = 0; s < 5; s++)
            {
                float y = (s + 1) * .45f, z = 52f + s * 1.2f;
                BoxMM(b, p.Slab, new Vector3(-26f, 0, z), new Vector3(-3.2f, y, 62.2f), slab);
                BoxMM(b, p.Slab, new Vector3(3.2f, 0, z), new Vector3(26f, y, 62.2f), slab);
                BoxMM(b, "mosaic", new Vector3(-3.2f, 0, z), new Vector3(3.2f, y - .08f, 62.2f), X(p.PoolCol));
                Plane(b, "water_pool", -3.2f, z, 3.2f, z + 1.2f, y - .1f, Color.white);
            }
            BoxMM(b, p.Coping, new Vector3(-3.6f, 0, 52f), new Vector3(-3.2f, 2.45f, 62.2f), cop);
            BoxMM(b, p.Coping, new Vector3(3.2f, 0, 52f), new Vector3(3.6f, 2.45f, 62.2f), cop);
            Plane(b, p.Slab, -30f, 58f, 30f, 62.2f, 2.26f, slab);
            // bollards along the boulevard (gaps for the van ramps), tall lamps with banners, round bench planters, pavilion, kiosk
            for (float x = -33f; x <= 33f; x += 3f) if (Mathf.Abs(x) > 4f) { Cyl(b, "flat_metal", new Vector3(x, 0, -4.1f), .11f, .9f, 12, X(p.BollCol)); Cyl(b, "flat_metal", new Vector3(x, .9f, -4.1f), .13f, .06f, 12, X(p.BollCol)); }
            int li = 0;
            foreach (var q in new[] { new Vector2(-12f, 2f), new Vector2(12f, 2f), new Vector2(-12f, 24f), new Vector2(12f, 24f), new Vector2(-12f, 44f), new Vector2(12f, 44f) })
                TallLamp(b, new Vector3(q.x, 0, q.y), X(p.LampCol), li++ % 2 == 0 ? X(p.Banner1) : X(p.Banner2), q.x > 0);
            foreach (var q in new[] { new Vector3(-17f, 0, 14f), new Vector3(17f, 0, 30f), new Vector3(-17f, 0, 38f) }) RoundBench(b, q, p);
            Pavilion(b, new Vector3(-24f, 0, 26f), p);
            Kiosk(b, new Vector3(20f, 0, 8f), p);
        }

        static void TallLamp(Batch b, Vector3 at, Color col, Color banner, bool east)
        {
            Cyl(b, "flat_metal", at, .14f, .5f, 12, col);
            Cyl(b, "flat_metal", at, .09f, 6.2f, 12, col);
            float sx = east ? -1 : 1;
            Beam(b, "flat_metal", at + new Vector3(0, 5.9f, 0), at + new Vector3(sx * 1.1f, 6.15f, 0), .07f, .07f, col);
            Box(b, "flat_metal", G0, at + new Vector3(sx * 1.15f, 6.05f, 0), new Vector3(.55f, .16f, .3f), col);
            Box(b, "flat_gloss", G0, at + new Vector3(sx * 1.15f, 5.95f, 0), new Vector3(.45f, .04f, .22f), X("F3EFE2"));
            Box(b, "flat", G0, at + new Vector3(-sx * .32f, 4.2f, 0), new Vector3(.5f, 1.8f, .03f), banner);
            Box(b, "flat_metal", G0, at + new Vector3(-sx * .32f, 5.13f, 0), new Vector3(.62f, .04f, .04f), col);
        }

        static void RoundBench(Batch b, Vector3 c, DCPal p)
        {
            Cyl(b, p.Coping, c, 1.45f, .5f, 28, X(p.CopCol));
            Cyl(b, "flat", c + Vector3.up * .5f, 1.3f, .05f, 28, X("5E4A3A"));
            Cyl(b, "meadow", c + Vector3.up * .55f, 1.1f, .25f, 20, X("6D8B4A"), true, .7f);
            for (int i = 0; i < 9; i++) { float a = i * 2 * Mathf.PI / 9 + .3f; Cyl(b, "flat", c + new Vector3(Mathf.Sin(a) * .6f, .7f, Mathf.Cos(a) * .6f), .16f, .18f, 8, X(new[] { "C8463A", "E2B437", "8E5BA8", "E8E4DA" }[i % 4]), true, .05f); }
            int n = 24;
            for (int i = 0; i < n; i++)
            {
                float a0 = i * 2 * Mathf.PI / n, a1 = (i + 1) * 2 * Mathf.PI / n, r = 1.75f;
                Vector3 p0 = c + new Vector3(Mathf.Sin(a0) * r, .45f, Mathf.Cos(a0) * r), p1 = c + new Vector3(Mathf.Sin(a1) * r, .45f, Mathf.Cos(a1) * r);
                Beam(b, p.BenchWood, p0, p1, .55f, .06f, Own(p.BenchWood));
                if (i % 3 == 0) Cyl(b, "flat_metal", c + new Vector3(Mathf.Sin(a0) * r, 0, Mathf.Cos(a0) * r), .05f, .42f, 6, X(p.BenchMetal));
            }
        }

        static void Pavilion(Batch b, Vector3 c, DCPal p)
        {
            const float W = 12f, D = 7f, H = 3.8f;
            var f = Fr.Yaw(c, 0);
            Box(b, "flat", f, new Vector3(0, .1f, 0), new Vector3(W + .4f, .2f, D + .4f), X(p.CopCol));
            string gk = Glass("glass_dc_" + p.KioskTrim, "B3C3C9");
            for (int i = 0; i < 4; i++)
            {
                float hx = W / 2, hz = D / 2; Vector2 a, e;
                switch (i) { case 0: a = new(-hx, -hz); e = new(hx, -hz); break; case 1: a = new(hx, -hz); e = new(hx, hz); break; case 2: a = new(hx, hz); e = new(-hx, hz); break; default: a = new(-hx, hz); e = new(-hx, -hz); break; }
                var w = f.Wall(a, e); float L = (e - a).magnitude; int n = Mathf.RoundToInt(L / 1.5f); float pw = L / n;
                for (int k = 0; k < n; k++) Pane(b, gk, w, Rect.MinMaxRect(k * pw, .2f, (k + 1) * pw, H), .02f, Cell("pav" + i + k));
                for (int k = 0; k <= n; k++) Box(b, "flat_metal", w, new Vector3(k * pw, H / 2 + .1f, 0), new Vector3(.08f, H - .2f, .1f), X(p.KioskCol));
                Box(b, "flat_metal", w, new Vector3(L / 2, 1f, 0), new Vector3(L, .06f, .08f), X(p.KioskCol));
            }
            Box(b, "flat_metal", f, new Vector3(0, H + .25f, 0), new Vector3(W + 1.4f, .5f, D + 1.4f), X(p.KioskRoof));
            Box(b, "flat_metal", f, new Vector3(0, H + .02f, 0), new Vector3(W + 1.5f, .06f, D + 1.5f), X(p.KioskTrim));
            // terrace umbrellas (yellow per plan) as simple cones
            foreach (float x in new[] { -4f, 0f, 4f })
            {
                Cyl(b, "flat_metal", c + new Vector3(x, 0, -6f), .04f, 2.4f, 6, X("D6D4CE"));
                Cyl(b, "flat", c + new Vector3(x, 2.1f, -6f), 1.4f, .45f, 12, X("E8C23A"), true, .05f);
            }
        }

        static void Kiosk(Batch b, Vector3 c, DCPal p)
        {
            const float W = 3.2f, D = 2.4f, H = 2.7f;
            var f = Fr.Yaw(c, 0);
            Box(b, "flat", f, new Vector3(0, .55f, 0), new Vector3(W, 1.1f, D), X(p.KioskCol));
            Box(b, "flat_gloss", f, new Vector3(0, 1.1f + (H - 1.1f) / 2, 0), new Vector3(W - .3f, H - 1.1f, D - .3f), X("6B7F8E"));
            foreach (var (x, z) in new[] { (-1f, -1f), (1f, -1f), (1f, 1f), (-1f, 1f) }) Box(b, "flat_metal", f, new Vector3(x * (W / 2 - .06f), H / 2, z * (D / 2 - .06f)), new Vector3(.12f, H, .12f), X(p.KioskCol));
            Box(b, "flat_metal", f, new Vector3(0, H + .2f, 0), new Vector3(W + .7f, .25f, D + .7f), X(p.KioskRoof));
            Box(b, "flat", f, new Vector3(0, H - .2f, -D / 2 - .02f), new Vector3(W - .2f, .35f, .04f), X(p.KioskTrim));
            Box(b, "flat_metal", f, new Vector3(0, 1.12f, -D / 2 - .15f), new Vector3(W - .4f, .05f, .35f), X(p.KioskTrim));
        }

        // ================================================================== 4. Port P1-P3
        sealed class PPal { public string Wall, WallCol, Upper, UpperCol, Trim, Shutter, PlinthKey, PlinthCol; public float PlinthH; public string[] Cont; public string Stacker, Yard, YardCol, Joint, Edge, EdgeCol, Fence, FenceKey, Mast; public bool Hatch, YardLines; }

        static void Port(Transform d)
        {
            var g = new Batch();
            Plane(g, "meadow", -260, -260, 45, 260, -.06f, Own("meadow"));
            Plane(g, "sea", 45f, -200f, 300f, 220f, -1.6f, Color.white);
            Plane(g, "asphalt", -120, -23, 45, -14, .012f, Own("asphalt"));
            var ctx = Group(d, "Context");
            Flush(g, ctx, "Port_ctx");
            var pals = new[]
            {
                new PPal { Wall = "trapez", WallCol = "8FA5B5", Trim = "E8E8E4", Shutter = "B9BDBF", PlinthKey = "conc", PlinthCol = "BDB8AE", PlinthH = .6f,
                    Cont = new[] { "A8473A", "3E6A9A", "4E7A52", "C8743A", "D9D7D0", "3E6A9A", "A8473A", "8A6A4A" }, Stacker = "E0B030", Yard = "conc", YardCol = "C9C5BD", Joint = "8E8A82",
                    Edge = "aggregate", EdgeCol = "C6C1B6", Fence = "B5BAB8", Mast = "B5BAB8" },
                new PPal { Wall = "trapez", WallCol = "9A4A3A", Trim = "E6DCC4", Shutter = "E2D8C2", PlinthKey = "board", PlinthCol = "B9B2A6", PlinthH = 2.4f,
                    Cont = new[] { "6F8FA6", "8A5A44", "5E7F7A", "B89A5A", "6F8FA6", "9A7B62", "4F6670", "B0A48E" }, Stacker = "C8463A", Yard = "formwork", YardCol = "BDB7AC", Joint = "8A847A",
                    Edge = "rubble_grey", EdgeCol = "B8B4AC", Fence = "4E6E4E", Mast = "8A8E8E" },
                new PPal { Wall = "wave", WallCol = "B9BEC0", Upper = "trapez", UpperCol = "5E8E86", Trim = "F0F0EC", Shutter = "EEEEEA", PlinthKey = "conc", PlinthCol = "C4C0B8", PlinthH = .6f,
                    Cont = new[] { "E3B23C", "2F8F9D", "E8E6E0", "B23A3A", "2F8F9D", "E3B23C", "4C6F9E", "E8E6E0" }, Stacker = "2E5E9E", Yard = "asph_light", YardCol = "9C9C9A", Joint = null,
                    Edge = "conc", EdgeCol = "C9C6BF", Fence = "3A3F3F", Mast = "D9DBDC", Hatch = true, YardLines = true },
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "P" + v);
                var b = new Batch();
                PortVariant(b, grp, pals[v - 1], "P" + v);
                Flush(b, grp, "Port_P" + v);
            }
        }

        static void PortVariant(Batch b, Transform grp, PPal p, string code)
        {
            // yard (concrete slabs 6 x 6 m with dark joints, or light asphalt with painted lines)
            Plane(b, p.Yard, -60, -14, 45, 46, .01f, X(p.YardCol));
            Plane(b, p.Yard, -60, -40, 45, -23, .01f, X(p.YardCol));
            if (p.Joint != null)
            {
                for (float x = -60; x <= 45; x += 6) Plane(b, "flat", x - .03f, -14, x + .03f, 46, .016f, X(p.Joint));
                for (float z = -14; z <= 46; z += 6) Plane(b, "flat", -60, z - .03f, 45, z + .03f, .016f, X(p.Joint));
            }
            if (p.YardLines)
            {
                for (float x = -54; x < -28; x += 3.2f) Plane(b, "flat", x - .06f, -12f, x + .06f, 8f, .017f, X("E8E4D6"));
                Plane(b, "flat", -58f, -10f, 40f, -9.85f, .017f, X("E2B22E"));
            }
            // warehouse 50 x 24 x 9.6 m, three roller shutters onto the apron
            const float wx0 = -25f, wx1 = 25f, wz0 = 12f, wz1 = 36f, H = 9.6f;
            Plane(b, "conc", -18f, 4f, 18f, 12f, .02f, X("D5D1C8"));
            for (int i = 0; i < 4; i++)
            {
                Vector2 a, e;
                switch (i) { case 0: a = new(wx0, wz0); e = new(wx1, wz0); break; case 1: a = new(wx1, wz0); e = new(wx1, wz1); break; case 2: a = new(wx1, wz1); e = new(wx0, wz1); break; default: a = new(wx0, wz1); e = new(wx0, wz0); break; }
                var w = G0.Wall(a, e); float L = (e - a).magnitude;
                var holes = new List<Rect>();
                if (i == 0) { foreach (float s in new[] { 10f, 25f, 40f }) { holes.Add(Rect.MinMaxRect(s - 2.5f, 0, s + 2.5f, 5.2f)); holes.Add(Rect.MinMaxRect(s + 3.4f, 0, s + 4.4f, 2.2f)); } }
                if (i == 1) holes.Add(Rect.MinMaxRect(L / 2 - 2.5f, 0, L / 2 + 2.5f, 5.2f));
                float ph = p.PlinthH;
                var plinthHoles = holes.Where(h => h.yMin < ph).Select(h => Rect.MinMaxRect(h.xMin, 0, h.xMax, Mathf.Min(h.yMax, ph))).ToList();
                OpeningsWall(b, p.PlinthKey, w, L, 0, ph, X(p.PlinthCol), plinthHoles, .1f);
                if (p.Upper != null)
                {
                    OpeningsWall(b, p.Wall, w, L, ph, 4.8f, X(p.WallCol), holes, .1f);
                    OpeningsWall(b, p.Upper, w, L, 4.8f, H, X(p.UpperCol), holes, .1f);
                    WallBox(b, "flat_metal", w, 0, L, 4.7f, 5.05f, .08f, X(p.Trim));
                }
                else OpeningsWall(b, p.Wall, w, L, ph, H, X(p.WallCol), holes, .1f);
                if (ph > 1f) WallBox(b, "flat_metal", w, 0, L, ph - .05f, ph + .1f, .1f, X(p.Trim));
                // high window band (polycarbonate) on the long sides
                if (i == 0 || i == 2) for (float s = 3f; s < L - 3f; s += 6f) { Box(b, "flat_gloss", w, new Vector3(s + 1.5f, 7.6f, -.02f), new Vector3(3.6f, .9f, .04f), X("C9D3D6")); Box(b, "flat_metal", w, new Vector3(s + 1.5f, 7.6f, -.03f), new Vector3(3.8f, 1.1f, .02f), X(p.Trim)); }
                foreach (var h in holes)
                {
                    bool big = h.width > 3f;
                    Box(b, big ? "shutter" : "flat_metal", w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .02f), big ? X(p.Shutter) : X("5C6266"));
                    WallBox(b, "flat_metal", w, h.xMin - .2f, h.xMin, 0, h.yMax + .2f, .1f, X(p.Trim));
                    WallBox(b, "flat_metal", w, h.xMax, h.xMax + .2f, 0, h.yMax + .2f, .1f, X(p.Trim));
                    WallBox(b, "flat_metal", w, h.xMin - .2f, h.xMax + .2f, h.yMax, h.yMax + .2f, .1f, X(p.Trim));
                    if (big) WallBox(b, "flat_metal", w, h.xMin - .3f, h.xMax + .3f, h.yMax + .2f, h.yMax + .7f, .45f, X(p.Trim));
                }
                WallBox(b, "flat_metal", w, -.15f, .15f, 0, H + .3f, .15f, X(p.Trim));           // corner trims
                WallBox(b, "flat_metal", w, -.1f, L + .1f, H, H + .35f, .12f, X(p.Trim));       // top flashing
            }
            Plane(b, "wave", wx0, wz0, wx1, wz1, H + .3f, X("A9AEB0"));
            // containers: two small stacks (1-3 tiers) + singles
            var cs = new (float x, float z, bool forty, int tier, float yaw)[]
            {
                (-42f, -4f, true, 0, 0), (-42f, -4f, true, 1, 0), (-45f, -4f, false, 2, 0), (-42f, -1.4f, true, 0, 0), (-39f, -1.4f, false, 1, 0),
                (-45f, 1.2f, false, 0, 0), (-38.5f, 1.2f, false, 0, 0), (-20f, -6.5f, false, 0, 18f),
            };
            for (int i = 0; i < cs.Length; i++) Container(b, new Vector3(cs[i].x, cs[i].tier * 2.59f, cs[i].z), cs[i].forty, cs[i].yaw, X(p.Cont[i % p.Cont.Length]));
            ReachStacker(b, new Vector3(-24f, 0, -11.5f), X(p.Stacker));
            // light mast
            Cyl(b, "flat_metal", new Vector3(12f, 0, -10f), .28f, 20f, 12, X(p.Mast), true, .18f);
            Box(b, "flat_metal", G0, new Vector3(12f, 20.3f, -10f), new Vector3(2.6f, .5f, .5f), X(p.Mast));
            for (int k = -1; k <= 1; k++) Box(b, "flat_gloss", G0, new Vector3(12f + k * .8f, 19.9f, -10.2f), new Vector3(.6f, .4f, .2f), X("EDEBE2"));
            // quay edge on the east: kerb, safety edge, bollards, fenders, quay wall down to the water
            Box(b, p.Edge, G0, new Vector3(44.6f, .1f, 10f), new Vector3(.8f, .2f, 100f), X(p.EdgeCol));
            if (p.Hatch) for (float z = -40f; z < 60f; z += 1.2f) Box(b, "flat", G0, new Vector3(44.6f, .205f, z + .3f), new Vector3(.8f, .01f, .6f), (Mathf.RoundToInt(z / 1.2f) % 2 == 0) ? X("E2B22E") : X("26282A"));
            else Box(b, "flat", G0, new Vector3(44.6f, .205f, 10f), new Vector3(.8f, .01f, 100f), X(p.Edge == "rubble_grey" ? "B8B4AC" : "E2B22E"));
            Wall(b, p.Edge == "rubble_grey" ? "rubble_grey" : "conc", G0.Wall(new Vector2(45f, -40f), new Vector2(45f, 60f)), 0, 100f, -2.2f, .2f, X(p.EdgeCol));
            for (float z = -36f; z < 60f; z += 12f) { Cyl(b, "flat_metal", new Vector3(44.2f, .2f, z), .22f, .55f, 12, X("3A3D40")); Cyl(b, "flat_metal", new Vector3(44.2f, .75f, z), .32f, .12f, 12, X("3A3D40")); }
            for (float z = -39f; z < 60f; z += 6f) Box(b, "flat", G0, new Vector3(45.22f, -.7f, z), new Vector3(.4f, 1.3f, .45f), X("232425"));
            // chain-link fence on concrete posts (west and north)
            string ck = Chain("chain_" + code, p.Fence);
            foreach (var (a, e) in new[] { (new Vector2(-60f, -40f), new Vector2(-60f, 46f)), (new Vector2(-60f, 46f), new Vector2(44f, 46f)) })
            {
                var w = G0.Wall(a, e); float L = (e - a).magnitude;
                Wall(b, ck, w, 0, L, .05f, 2.4f, Color.white);
                for (float s = 0; s <= L; s += 3f) Box(b, "conc", w, new Vector3(s, 1.3f, 0), new Vector3(.2f, 2.6f, .2f), X("C2BEB6"));
            }
        }

        // ISO container 20 / 40 ft: one atlas material, vertex tint; sides split into atlas repeats, door end +X, blind end -X
        static void Container(Batch b, Vector3 at, bool forty, float yaw, Color col)
        {
            float L = forty ? 12.19f : 6.06f, W = 2.44f, H = 2.59f;
            var f = Fr.Yaw(at, yaw);
            var mb = b["container"];
            int reps = forty ? 4 : 2; float seg = L / reps;
            void Face(Vector3 a, Vector3 bb, Vector3 c, Vector3 d, float u0, float u1) => mb.Quad(f.P(a), f.P(bb), f.P(c), f.P(d), new(u0, 0), new(u0, 1), new(u1, 1), new(u1, 0), col);
            for (int k = 0; k < reps; k++)
            {
                float x0 = -L / 2 + k * seg, x1 = x0 + seg;
                Face(new(x0, 0, -W / 2), new(x0, H, -W / 2), new(x1, H, -W / 2), new(x1, 0, -W / 2), 0f, .5f);       // front side (-Z)
                Face(new(x1, 0, W / 2), new(x1, H, W / 2), new(x0, H, W / 2), new(x0, 0, W / 2), 0f, .5f);           // back side (+Z)
                mb.Quad(f.P(x0, H, -W / 2), f.P(x0, H, W / 2), f.P(x1, H, W / 2), f.P(x1, H, -W / 2), new(0, .1f), new(0, .9f), new(.5f, .9f), new(.5f, .1f), col);   // roof
            }
            Face(new(L / 2, 0, -W / 2), new(L / 2, H, -W / 2), new(L / 2, H, W / 2), new(L / 2, 0, W / 2), .5f, .75f);       // door end (+X)
            Face(new(-L / 2, 0, W / 2), new(-L / 2, H, W / 2), new(-L / 2, H, -W / 2), new(-L / 2, 0, -W / 2), .75f, 1f);    // blind end (-X)
            Color dk = col * .55f; dk.a = 1;
            foreach (float x in new[] { -L / 2 + .09f, L / 2 - .09f }) foreach (float z in new[] { -W / 2 + .09f, W / 2 - .09f }) foreach (float y in new[] { .06f, H - .06f })
                Box(b, "flat_metal", f, new Vector3(x, y, z), new Vector3(.19f, .13f, .19f), dk);
        }

        static void ReachStacker(Batch b, Vector3 at, Color paint)
        {
            var f = Fr.Yaw(at, 0);
            Color dark = X("2B2E31"), glass = X("4F6470");
            Box(b, "flat_metal", f, new Vector3(0, 1.6f, 0), new Vector3(7.5f, 1.5f, 3.6f), paint);
            Box(b, "flat_metal", f, new Vector3(-3.4f, 2.3f, 0), new Vector3(1.4f, 1.8f, 3.4f), paint);                  // counterweight
            Box(b, "flat_metal", f, new Vector3(.4f, 3.3f, -1.1f), new Vector3(1.6f, 2.0f, 1.4f), paint);                // cab
            Box(b, "flat_gloss", f, new Vector3(.4f, 3.55f, -1.81f), new Vector3(1.3f, 1.2f, .02f), glass);
            Box(b, "flat_gloss", f, new Vector3(1.21f, 3.55f, -1.1f), new Vector3(.02f, 1.2f, 1.1f), glass);
            foreach (float x in new[] { -2.4f, 2.5f }) foreach (float z in new[] { -1.55f, 1.55f }) CylAx(b, "flat", f.P(x, .85f, z), Vector3.forward, .85f, .6f, 14, dark);
            Vector3 p0 = f.P(-2.5f, 2.6f, .6f), p1 = f.P(5.5f, 8.2f, .6f);
            Beam(b, "flat_metal", p0, p1, .8f, .9f, paint);
            Box(b, "flat_metal", f, new Vector3(6.1f, 8.0f, .6f), new Vector3(.6f, .5f, 6.0f), dark);                    // spreader
            Beam(b, "flat_metal", f.P(1f, 2.4f, .6f), f.P(2f, 4.9f, .6f), .35f, .35f, dark);                             // lift cylinder
        }

        // ================================================================== 5. Elite E1-E3
        sealed class EPal { public string Villa, VillaCol, Upper, UpperCol, Feature, FeatureCol, Louvre, Frame, Fascia, Road, RoadCol, Parapet, ParCol, Cap, CapCol, FenceKey, FenceCol, PostKey, PostCol, Gate, Fbi, FbiCol, FbiFrame; }

        static void Elite(Transform d)
        {
            var g = new Batch();
            Plane(g, "meadow", -260, 0, 260, 260, -.03f, Own("meadow"));
            Plane(g, "meadow", -260, -260, 2.25f, 0, -.03f, Own("meadow"));
            // downhill slope on the outer side of the stone road
            var mb = g["meadow"]; var sm = S["meadow"];
            Vector3 q0 = new(3f, -.4f, -260f), q1 = new(3f, -.4f, -8f), q2 = new(12f, -4.5f, -8f), q3 = new(12f, -4.5f, -260f);
            mb.Quad(q0, q1, q2, q3, new(q0.x / sm.TU, q0.z / sm.TV), new(q1.x / sm.TU, q1.z / sm.TV), new(q2.x / sm.TU, q2.z / sm.TV), new(q3.x / sm.TU, q3.z / sm.TV), Own("meadow"));
            Plane(g, "meadow", 12f, -260, 260, -8f, -4.5f, Own("meadow"));
            Plane(g, "meadow", 2.9f, -8f, 260, 0, -.03f, Own("meadow"));                  // terrace in front of the fence, retaining wall per variant
            Plane(g, "asphalt", -3.2f, 0, 3.2f, 60, .01f, Own("asphalt"));
            Plane(g, "asphalt", -16f, 18f, -3.2f, 30f, .01f, Own("asphalt"));
            var ctx = Group(d, "Context");
            Flush(g, ctx, "El_ctx");
            foreach (var q in new[] { new Vector3(-8f, 0, 12f), new Vector3(10f, 0, 14f), new Vector3(-48f, 0, 14f), new Vector3(16f, 0, 40f), new Vector3(-10f, 0, -15f), new Vector3(-14f, 0, -26f) })
                Prop("TREES/tree_palm_a", ctx, q, Hash(q.ToString()) * 360f);
            Prop("CARS/car_sedan_blue", ctx, new Vector3(9f, 0, 22f), 0);
            Prop("CARS/car_sedan_blue", ctx, new Vector3(12f, 0, 22f), 0);
            var pals = new[]
            {
                new EPal { Villa = "plaster", VillaCol = "F2F0EA", Upper = "travertine", UpperCol = "E8DECD", Feature = "rubble_warm", FeatureCol = null, Louvre = "teak", Frame = "222426", Fascia = "F4F2EC",
                    Road = "setts", RoadCol = "B8B0A4", Parapet = "rubble_warm", ParCol = null, Cap = "travertine", CapCol = "E6DCCB", FenceKey = "plaster", FenceCol = "EDEBE4", PostKey = "travertine", PostCol = "E6DCCB", Gate = "1E2022",
                    Fbi = "board", FbiCol = "485462", FbiFrame = "1E2022" },
                new EPal { Villa = "plaster", VillaCol = "EFE6D6", Upper = "plaster", UpperCol = "E9DCC6", Feature = "rubble_grey", FeatureCol = null, Louvre = "teak", Frame = "3B3128", Fascia = "EFE6D6",
                    Road = "setts_sand", RoadCol = null, Parapet = "rubble_grey", ParCol = null, Cap = "stone", CapCol = "C9C4BA", FenceKey = "rubble_grey", FenceCol = null, PostKey = "stone", PostCol = "C9C4BA", Gate = "4A3A2C",
                    Fbi = "panel", FbiCol = "4A5563", FbiFrame = "2A2E33" },
                new EPal { Villa = "plaster", VillaCol = "F4F4F2", Upper = "panel", UpperCol = "3A3D42", Feature = "larch", FeatureCol = null, Louvre = "larch", Frame = "2B2D30", Fascia = "F4F4F2",
                    Road = "setts", RoadCol = "7E7F80", Parapet = "conc", ParCol = "C2BFB8", Cap = "conc", CapCol = "D2CFC8", FenceKey = "panel", FenceCol = "3A3D42", PostKey = "conc", PostCol = "C2BFB8", Gate = "2B2D30",
                    Fbi = "conc", FbiCol = "3F4954", FbiFrame = "16181A" },
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "E" + v);
                var b = new Batch();
                EliteVariant(b, pals[v - 1], "E" + v);
                Flush(b, grp, "El_E" + v);
            }
        }

        static Color C(string key, string hex) => hex == null ? Own(key) : X(hex);

        static void EliteVariant(Batch b, EPal p, string code)
        {
            // stone road 4.5 m, no markings; stone parapet on the outer (downhill) side, lamps
            Plane(b, p.Road, -2.25f, -60f, 2.25f, 0f, .02f, C(p.Road, p.RoadCol));
            Box(b, "stone", G0, new Vector3(-2.4f, .06f, -30f), new Vector3(.3f, .12f, 60f), X("BDB8AE"));
            Box(b, p.Parapet, G0, new Vector3(2.65f, (-4.5f + .85f) / 2, -30.5f), new Vector3(.5f, 4.5f + .85f, 59f), C(p.Parapet, p.ParCol));
            Box(b, p.Cap, G0, new Vector3(2.65f, .91f, -30.5f), new Vector3(.66f, .12f, 59f), C(p.Cap, p.CapCol));
            Wall(b, p.Parapet, G0.Wall(new Vector2(2.9f, -8f), new Vector2(260f, -8f)), 0, 257.1f, -4.6f, 0f, C(p.Parapet, p.ParCol));
            Box(b, p.Cap, G0, new Vector3(131.45f, .06f, -8.15f), new Vector3(257.1f, .12f, .4f), C(p.Cap, p.CapCol));
            for (float z = -55f; z < -2f; z += 14f)
            {
                Cyl(b, "flat_metal", new Vector3(2.65f, .97f, z), .07f, 3.4f, 8, X(p.Gate));
                Box(b, "flat_metal", G0, new Vector3(2.65f, 4.55f, z), new Vector3(.36f, .5f, .36f), X(p.Gate));
                Box(b, "flat_gloss", G0, new Vector3(2.65f, 4.5f, z), new Vector3(.3f, .34f, .38f), X("F1EBD8"));
            }
            // high solid fence of the gated village with posts, floodlights and wire; the trap gate (closed) with lamp posts
            var w = G0.Wall(new Vector2(-60f, 0f), new Vector2(60f, 0f));
            Wall(b, p.FenceKey, w, 0, 60f - 3.4f, 0, 3.2f, C(p.FenceKey, p.FenceCol));
            Wall(b, p.FenceKey, w, 60f + 3.4f, 120f, 0, 3.2f, C(p.FenceKey, p.FenceCol));
            Wall(b, p.FenceKey, G0.Wall(new Vector2(60f, .3f), new Vector2(-60f, .3f)), 0, 120f, 0, 3.2f, C(p.FenceKey, p.FenceCol));
            WallBox(b, p.Cap, w, 0, 60f - 3.4f, 3.2f, 3.32f, .08f, C(p.Cap, p.CapCol));
            WallBox(b, p.Cap, w, 60f + 3.4f, 120f, 3.2f, 3.32f, .08f, C(p.Cap, p.CapCol));
            for (float s = 0f; s <= 120f; s += 6f)
            {
                if (Mathf.Abs(s - 60f) < 4f) continue;
                Box(b, p.PostKey, w, new Vector3(s, 1.75f, .15f), new Vector3(.6f, 3.5f, .7f), C(p.PostKey, p.PostCol));
                Box(b, "flat_metal", w, new Vector3(s, 3.55f, -.1f), new Vector3(.3f, .2f, .3f), X("2A2C2E"));
                Box(b, "flat_gloss", w, new Vector3(s, 3.45f, -.26f), new Vector3(.22f, .14f, .04f), X("EDEAE0"));
                Beam(b, "flat_metal", w.P(s, 3.3f, .15f), w.P(s, 3.9f, -.15f), .04f, .04f, X("2A2C2E"));
            }
            foreach (float y in new[] { 3.55f, 3.75f }) Box(b, "flat_metal", w, new Vector3(60f, y, -.05f), new Vector3(120f, .02f, .02f), X("4A4C4E"));
            foreach (float s in new[] { 60f - 3.6f, 60f + 3.6f })
            {
                Box(b, p.PostKey, w, new Vector3(s, 2f, .15f), new Vector3(.9f, 4f, .9f), C(p.PostKey, p.PostCol));
                Box(b, p.Cap, w, new Vector3(s, 4.06f, .15f), new Vector3(1.05f, .12f, 1.05f), C(p.Cap, p.CapCol));
                Box(b, "flat_metal", w, new Vector3(s, 4.4f, .15f), new Vector3(.4f, .55f, .4f), X(p.Gate));
                Box(b, "flat_gloss", w, new Vector3(s, 4.4f, .15f), new Vector3(.32f, .4f, .44f), X("F1EBD8"));
            }
            for (int leaf = 0; leaf < 2; leaf++)
            {
                float s0 = 60f - 3.15f + leaf * 3.15f;
                foreach (float y in new[] { .15f, 1.5f, 2.95f }) Box(b, "flat_metal", w, new Vector3(s0 + 1.575f, y, .1f), new Vector3(3.1f, .1f, .08f), X(p.Gate));
                for (float s = s0 + .05f; s < s0 + 3.15f; s += .14f) Box(b, "flat_metal", w, new Vector3(s, 1.55f, .1f), new Vector3(.035f, 2.95f, .035f), X(p.Gate));
            }
            // guard booth outside the gate
            Booth(b, new Vector3(-7.5f, 0, -5f), p);
            // FBI building 24 x 12 m, 2 floors: ribbon windows, recessed entrance with canopy, flag
            FbiBuilding(b, new Vector3(0, 0, 32f), p);
            Cyl(b, "flat_metal", new Vector3(9f, 0, 24f), .08f, 10f, 8, X("D6D6D2"));
            Box(b, "flat", G0, new Vector3(9.9f, 9.2f, 24f), new Vector3(1.7f, 1.1f, .02f), X("2F4E8C"));
            // villa (type L), its garage
            Villa(b, p);
        }

        static void Booth(Batch b, Vector3 at, EPal p)
        {
            var f = Fr.Yaw(at, 0);
            Box(b, p.Fbi, f, new Vector3(0, 1.4f, 0), new Vector3(6f, 2.8f, 5.7f), C(p.Fbi, p.FbiCol));
            Box(b, "flat_gloss", f, new Vector3(0, 1.75f, -2.86f), new Vector3(4.6f, 1.1f, .02f), X("3A4652"));
            Box(b, "flat_gloss", f, new Vector3(3.01f, 1.75f, 0), new Vector3(.02f, 1.1f, 4f), X("3A4652"));
            Box(b, "flat_metal", f, new Vector3(0, 2.95f, 0), new Vector3(7f, .3f, 6.7f), X(p.FbiFrame));
        }

        static void FbiBuilding(Batch b, Vector3 c, EPal p)
        {
            const float W = 24f, D = 12f, H = 7f;
            var f = Fr.Yaw(c, 0);
            Color col = C(p.Fbi, p.FbiCol), fr = X(p.FbiFrame);
            string gk = Glass("glass_fbi", "6D7B88");
            for (int i = 0; i < 4; i++)
            {
                Vector2 a, e; float hx = W / 2, hz = D / 2;
                switch (i) { case 0: a = new(-hx, -hz); e = new(hx, -hz); break; case 1: a = new(hx, -hz); e = new(hx, hz); break; case 2: a = new(hx, hz); e = new(-hx, hz); break; default: a = new(-hx, hz); e = new(-hx, -hz); break; }
                var w = f.Wall(a, e); float L = (e - a).magnitude;
                var holes = new List<Rect>();
                foreach (float y in new[] { .9f, 4.4f }) holes.Add(Rect.MinMaxRect(1.2f, y, L - 1.2f, y + 1.5f));
                if (i == 0) holes[0] = Rect.MinMaxRect(1.2f, .9f, L / 2 - 2.2f, 2.4f);
                if (i == 0) holes.Add(Rect.MinMaxRect(L / 2 + 2.2f, .9f, L - 1.2f, 2.4f));
                if (i == 0) holes.Add(Rect.MinMaxRect(L / 2 - 1.6f, 0, L / 2 + 1.6f, 3f));
                OpeningsWall(b, p.Fbi, w, L, 0, H + .6f, col, holes, .2f);
                int k = 0;
                foreach (var o in holes)
                {
                    int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.5f)); float pw = o.width / n;
                    for (int j = 0; j < n; j++) Pane(b, gk, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), .205f, Cell("fbi" + i + k + j));
                    for (int j = 0; j <= n; j++) Box(b, "flat_metal", w, new Vector3(o.xMin + j * pw, o.center.y, .16f), new Vector3(.08f, o.height, .1f), fr);
                    k++;
                }
                WallBox(b, "flat_metal", w, -.05f, L + .05f, H + .6f, H + .75f, .1f, fr);
            }
            var fw = f.Wall(new Vector2(-W / 2, -D / 2), new Vector2(W / 2, -D / 2));
            WallBox(b, "flat_metal", fw, W / 2 - 3f, W / 2 + 3f, 3.1f, 3.4f, 2.2f, fr);
            Plane(b, "roof_flat", c.x - W / 2, c.z - D / 2, c.x + W / 2, c.z + D / 2, H + .02f, Own("roof_flat"));
            Box(b, "flat_metal", f, new Vector3(-W / 2 + .3f, 5.2f, -D / 2 - .3f), new Vector3(.25f, .2f, .35f), X("2A2C2E"));   // cameras
            Box(b, "flat_metal", f, new Vector3(W / 2 - .3f, 5.2f, -D / 2 - .3f), new Vector3(.25f, .2f, .35f), X("2A2C2E"));
        }

        static void Villa(Batch b, EPal p)
        {
            Color vc = C(p.Villa, p.VillaCol), uc = C(p.Upper, p.UpperCol), fr = X(p.Frame), fa = X(p.Fascia);
            string gk = Glass("glass_villa", "8DA2AE");
            // A: ground volume 18 x 9.4 x 3.4, big glazing; B: upper 12 x 8 cantilevered 2 m; C: wing with stone feature wall; garage
            VBox(b, p.Villa, vc, -42f, -24f, 18f, 27.4f, 0f, 3.4f, gk, fr, front: (3.0f, .25f, 3.0f), id: "A");
            VBox(b, p.Upper, uc, -40f, -28f, 16f, 24f, 3.4f, 6.8f, gk, fr, front: (2.2f, .55f, 2.5f), id: "B");
            VBox(b, p.Villa, vc, -24f, -16f, 18f, 30f, 0f, 3.4f, gk, fr, front: (0f, 0f, 0f), id: "C");
            VBox(b, p.Villa, vc, -14f, -6f, 20f, 28f, 0f, 3.2f, gk, fr, front: (0f, 0f, 0f), id: "G");
            // roof slabs with thin projecting fascias
            foreach (var (x0, x1, z0, z1, y) in new[] { (-42f, -24f, 18f, 27.4f, 3.4f), (-40f, -28f, 16f, 24f, 6.8f), (-24f, -16f, 18f, 30f, 3.4f), (-14f, -6f, 20f, 28f, 3.2f) })
                BoxMM(b, "flat", new Vector3(x0 - .4f, y, z0 - .4f), new Vector3(x1 + .4f, y + .3f, z1 + .4f), fa);
            // louvres over the right half of B's glazing
            for (float x = -33.8f; x < -28.4f; x += .38f) BoxMM(b, p.Louvre, new Vector3(x, 3.7f, 15.62f), new Vector3(x + .07f, 6.6f, 15.92f), Own(p.Louvre));
            // stone feature wall + entrance door on C, glass railing on A's roof terrace
            BoxMM(b, p.Feature, new Vector3(-23.6f, 0, 17.6f), new Vector3(-19.4f, 3.4f, 18.02f), C(p.Feature, p.FeatureCol));
            BoxMM(b, "teak", new Vector3(-18.8f, 0, 17.94f), new Vector3(-17.2f, 2.5f, 18.0f), X("FFFFFF") * Own("teak"));
            BoxMM(b, "flat_gloss", new Vector3(-28f, 3.7f, 17.7f), new Vector3(-24.4f, 4.75f, 17.76f), X("A9C3CC"));
            // garage door
            BoxMM(b, "shutter", new Vector3(-12.6f, 0, 19.94f), new Vector3(-7.4f, 2.5f, 20f), X(p.Frame == "222426" ? "D8D6D0" : "7A7C7E"));
            Plane(b, "stone", -42f, 12f, -16f, 18f, .02f, X("E4E0D6"));
        }

        // villa volume: walls with optional front glazing (pane width, sill, height) on the -Z face
        static void VBox(Batch b, string key, Color col, float x0, float x1, float z0, float z1, float y0, float y1, string glass, Color fr, (float pane, float sill, float h) front, string id)
        {
            for (int i = 0; i < 4; i++)
            {
                Vector2 a, e;
                switch (i) { case 0: a = new(x0, z0); e = new(x1, z0); break; case 1: a = new(x1, z0); e = new(x1, z1); break; case 2: a = new(x1, z1); e = new(x0, z1); break; default: a = new(x0, z1); e = new(x0, z0); break; }
                var w = Fr.Yaw(new Vector3(0, y0, 0), 0).Wall(a, e); float L = (e - a).magnitude, H = y1 - y0;
                var holes = new List<Rect>();
                if (i == 0 && front.pane > 0) { int n = Mathf.FloorToInt((L - 1.6f) / front.pane); float st = (L - n * front.pane) / 2; holes.Add(Rect.MinMaxRect(st, front.sill, st + n * front.pane, front.sill + front.h)); }
                if (i == 1 && id == "A") holes.Add(Rect.MinMaxRect(1f, .25f, 4f, 2.9f));
                if (i == 3 && (id == "B" || id == "C")) holes.Add(Rect.MinMaxRect(1.5f, .6f, 3.5f, 2.6f));
                OpeningsWall(b, key, w, L, 0, H, col, holes, .15f);
                foreach (var o in holes)
                {
                    int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 3f)); float pw = o.width / n;
                    for (int j = 0; j < n; j++) Pane(b, glass, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), .155f, Cell(id + i + j));
                    for (int j = 0; j <= n; j++) Box(b, "flat_metal", w, new Vector3(o.xMin + j * pw, o.center.y, .1f), new Vector3(.07f, o.height, .1f), fr);
                    Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMin + .035f, .1f), new Vector3(o.width, .07f, .1f), fr);
                    Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMax - .035f, .1f), new Vector3(o.width, .07f, .1f), fr);
                }
            }
            if (y0 > 0) Plane(b, key, x0, z0, x1, z1, y0 - .01f, col);         // cantilever underside visible from below is acceptable; floor plate
        }

        // ================================================================== 6. Construction C1-C3
        sealed class CPal { public string Frame, FrameCol, Tube, Plank, Net, NetCol, Rail, Rail2, Infill, InfillCol; public string[] Cabins; public string CabTrim, Shop, ShopCol, ShopUpper, ShopUpperCol, ShopDoor, Fence, FenceTrim, GateInfill, Crane, Crane2; }

        static void Construction(Transform d)
        {
            var g = new Batch();
            Plane(g, "meadow", -260, -260, 260, -22.5f, -.03f, Own("meadow"));
            Plane(g, "meadow", -260, -22.5f, -58f, 260, -.03f, Own("meadow"));
            Plane(g, "meadow", 58f, -22.5f, 260, 260, -.03f, Own("meadow"));
            Plane(g, "meadow", -58f, 62f, 58f, 260, -.03f, Own("meadow"));
            Plane(g, "dirt", -58f, -22.5f, 58f, 62f, .0f, Own("dirt"));
            Plane(g, "dirt", -9.5f, -60f, 9.5f, -22.5f, .005f, Own("dirt"));
            // ruts with puddles from the gate
            foreach (float x in new[] { -1.1f, 1.1f }) Plane(g, "dirt", x - .35f, -60f, x + .35f, 6f, .01f, X("6E5A44"));
            Plane(g, "water_puddle", -1.5f, -12f, -.7f, -9.5f, .02f, Color.white);
            Plane(g, "water_puddle", .7f, -6f, 1.5f, -2.8f, .02f, Color.white);
            var ctx = Group(d, "Context");
            Flush(g, ctx, "Co_ctx");
            Prop("BINS/garbage_container_open", ctx, new Vector3(18f, 0, -6f), 90);
            var pals = new[]
            {
                new CPal { Frame = "formwork", FrameCol = "BDB9B1", Tube = "A9AEB0", Plank = "planks", Net = "net_green", NetCol = "3E7A4A", Rail = "C8463A", Rail2 = "EDEBE4", Infill = "cinder", InfillCol = null,
                    Cabins = new[] { "E8E6DF", "8FA9B8", "E8E6DF", "A9C0CC" }, CabTrim = "3C6EA8", Shop = "cinder", ShopCol = null, ShopDoor = "B9BDBF", Fence = "2F5FA0", FenceTrim = "E8E8E4", GateInfill = "trapez",
                    Crane = "E2B32E", Crane2 = "3A3C3E" },
                new CPal { Frame = "board", FrameCol = "CBC2B2", Tube = "C8463A", Plank = "planks", Net = "net_orange", NetCol = "E07A2E", Rail = "E2B32E", Rail2 = "2A2C2E", Infill = "brick_roman", InfillCol = null,
                    Cabins = new[] { "8FA9B8", "A47E62", "C8BFA8", "A9C0CC" }, CabTrim = "E8E6DF", Shop = "brick_roman", ShopCol = null, ShopUpper = "wave", ShopUpperCol = "B9BEC0", ShopDoor = "C8463A", Fence = "6F9AC8", FenceTrim = "F2F2EE", GateInfill = "trapez",
                    Crane = "C8463A", Crane2 = "EDEBE4" },
                new CPal { Frame = "conc", FrameCol = "AAA8A2", Tube = "2E5E9E", Plank = "larch", Net = "net_blue", NetCol = "5A7FA8", Rail = "E8E6E0", Rail2 = "2E5E9E", Infill = "cinder", InfillCol = "B4B0A8",
                    Cabins = new[] { "5E8A5E", "D9D7D0", "5E8A5E", "D9D7D0" }, CabTrim = "2B2D30", Shop = "wave", ShopCol = "B9BEC0", ShopDoor = "E07A2E", Fence = "22437A", FenceTrim = "B5BAB8", GateInfill = "mesh",
                    Crane = "E07A2E", Crane2 = "2B2D30" },
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "C" + v);
                var b = new Batch();
                ConstructionVariant(b, pals[v - 1], "C" + v);
                Flush(b, grp, "Co_C" + v);
            }
        }

        static void ConstructionVariant(Batch b, CPal p, string code)
        {
            Color fc = C(p.Frame, p.FrameCol), tube = X(p.Tube);
            // building A: monolithic frame 24 x 14 m, 5 floors x 3 m, 18 columns, slab edges with railings, top floor open
            float[] cx = { -12f, -7.2f, -2.4f, 2.4f, 7.2f, 12f }, cz = { 8f, 15f, 22f };
            BoxMM(b, p.Frame, new Vector3(-12.4f, 0, 7.6f), new Vector3(12.4f, .3f, 22.4f), fc);
            for (int fl = 1; fl <= 5; fl++)
            {
                float y = fl * 3f;
                BoxMM(b, p.Frame, new Vector3(-12.4f, y - .25f, 7.6f), new Vector3(12.4f, y, 22.4f), fc);
                foreach (float x in cx) foreach (float z in cz) BoxMM(b, p.Frame, new Vector3(x - .2f, y - 3f + (fl == 1 ? .3f : 0), z - .2f), new Vector3(x + .2f, y - .25f, z + .2f), fc);
                if (fl <= 4)
                    for (float x = -12f; x <= 12.01f; x += 2f) Box(b, "flat_metal", G0, new Vector3(x, y + .55f, 7.75f), new Vector3(.05f, 1.1f, .05f), X(p.Rail2));
                if (fl <= 4) foreach (float yy in new[] { .5f, 1.05f }) Box(b, "flat", G0, new Vector3(0, y + yy, 7.75f), new Vector3(24f, .08f, .03f), yy > 1f ? X(p.Rail) : X(p.Rail2));
            }
            // masonry infill in progress on floors 1-2 (east bays)
            foreach (var (y0, x0, x1) in new[] { (.3f, 2.6f, 11.8f), (3f, 7.4f, 11.8f) })
            {
                var w = G0.Wall(new Vector2(x0, 22.2f), new Vector2(x1, 22.2f));
                Wall(b, p.Infill, w, 0, x1 - x0, y0, y0 + 2.75f, C(p.Infill, p.InfillCol));
                Wall(b, p.Infill, G0.Wall(new Vector2(x1, 22.2f), new Vector2(x0, 22.2f)), 0, x1 - x0, y0, y0 + 2.75f, C(p.Infill, p.InfillCol));
            }
            // stair / lift core
            var core = new[] { (new Vector2(-2f, 16.4f), new Vector2(2f, 16.4f)), (new Vector2(2f, 16.4f), new Vector2(2f, 22f)), (new Vector2(2f, 22f), new Vector2(-2f, 22f)), (new Vector2(-2f, 22f), new Vector2(-2f, 16.4f)) };
            foreach (var (a, e) in core)
            {
                var w = G0.Wall(a, e); float L = (e - a).magnitude;
                var holes = new List<Rect>();
                if (a.y < 17f && e.y < 17f) for (int fl = 0; fl < 5; fl++) holes.Add(Rect.MinMaxRect(L / 2 - .5f, fl * 3f + .3f, L / 2 + .5f, fl * 3f + 2.4f));
                OpeningsWall(b, p.Frame, w, L, 0, 16f, fc, holes, .2f);
            }
            // scaffold along the west two thirds of the south face (the east bays show the bare frame): standards / ledgers / transoms,
            // diagonal braces, plank decks, toe boards, safety net on the middle bays
            const float sz0 = 5.4f, sz1 = 7.3f, sx1 = 4.8f, sxc = (-12f + sx1) / 2, sxl = sx1 + 12f;
            for (float x = -12f; x <= sx1 + .01f; x += 2.4f) foreach (float z in new[] { sz0, sz1 }) Box(b, "flat_metal", G0, new Vector3(x, 8.1f, z), new Vector3(.05f, 16.2f, .05f), tube);
            for (float y = 2f; y <= 16f; y += 2f)
            {
                foreach (float z in new[] { sz0, sz1 }) { Box(b, "flat_metal", G0, new Vector3(sxc, y, z), new Vector3(sxl, .05f, .05f), tube); Box(b, "flat_metal", G0, new Vector3(sxc, y + 1f, z), new Vector3(sxl, .045f, .045f), tube); }
                for (float x = -12f; x <= sx1 + .01f; x += 2.4f) Box(b, "flat_metal", G0, new Vector3(x, y, (sz0 + sz1) / 2), new Vector3(.05f, .05f, sz1 - sz0), tube);
                BoxMM(b, p.Plank, new Vector3(-12f, y + .03f, sz0 + .05f), new Vector3(sx1, y + .08f, sz1 - .05f), Own(p.Plank));
                BoxMM(b, p.Plank, new Vector3(-12f, y + .08f, sz0 - .02f), new Vector3(sx1, y + .26f, sz0 + .02f), Own(p.Plank));
            }
            for (float x = -12f; x < sx1 - .1f; x += 4.8f) for (float y = 0f; y < 16f; y += 4f) Beam(b, "flat_metal", new Vector3(x, y, sz0 - .06f), new Vector3(x + 4.8f, y + 4f, sz0 - .06f), .045f, .045f, tube);
            string nk = Net(p.Net, p.NetCol);
            Wall(b, nk, G0.Wall(new Vector2(-4.8f, sz0 - .15f), new Vector2(sx1 + .1f, sz0 - .15f)), 0, 9.7f, 2f, 16.2f, Color.white);
            // cargo hoist mast at the east face
            for (int k = 0; k < 4; k++) Box(b, "flat_metal", G0, new Vector3(13.2f + (k % 2) * 1.1f, 8.5f, 12f + (k / 2) * 1.1f), new Vector3(.08f, 17f, .08f), X(p.Crane));
            for (float y = 1f; y < 17f; y += 1.5f) BoxMM(b, "flat_metal", new Vector3(13.15f, y, 11.95f), new Vector3(14.35f, y + .06f, 13.15f), X(p.Crane));
            BoxMM(b, "trapez", new Vector3(12.8f, 0, 11.4f), new Vector3(14.8f, 2.4f, 13.8f), X(p.Crane));
            // tower crane: lattice mast, cab, jib, counter-jib with weights, hook
            TowerCrane(b, new Vector3(-24f, 0, 30f), X(p.Crane), X(p.Crane2));
            // site cabins (block containers 6 x 2.4 m, ~1 m apart): trapezoid sheet, trims, door, window, step
            for (int i = 0; i < 4; i++) Cabin(b, new Vector3(-46f + i * 3.4f, 0, -7f), X(p.Cabins[i]), X(p.CabTrim), "cab" + code + i);
            // workshop 24 x 12 m with three 5.6 m roller doors
            var ws = new (Vector2 a, Vector2 e)[] { (new(24f, 6f), new(48f, 6f)), (new(48f, 6f), new(48f, 18f)), (new(48f, 18f), new(24f, 18f)), (new(24f, 18f), new(24f, 6f)) };
            for (int i = 0; i < 4; i++)
            {
                var w = G0.Wall(ws[i].a, ws[i].e); float L = (ws[i].e - ws[i].a).magnitude;
                var holes = new List<Rect>();
                if (i == 0) foreach (float s in new[] { 4.2f, 12f, 19.8f }) holes.Add(Rect.MinMaxRect(s - 2.8f, 0, s + 2.8f, 4f));
                if (p.ShopUpper != null) { OpeningsWall(b, p.Shop, w, L, 0, 2.4f, C(p.Shop, p.ShopCol), holes.Select(h => Rect.MinMaxRect(h.xMin, 0, h.xMax, 2.4f)).ToList(), .1f); OpeningsWall(b, p.ShopUpper, w, L, 2.4f, 4.8f, X(p.ShopUpperCol), holes, .1f); }
                else OpeningsWall(b, p.Shop, w, L, 0, 4.8f, C(p.Shop, p.ShopCol), holes, .1f);
                foreach (var h in holes) { Box(b, "shutter", w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .02f), X(p.ShopDoor)); WallBox(b, "flat_metal", w, h.xMin - .15f, h.xMax + .15f, h.yMax, h.yMax + .4f, .3f, X("5C6266")); }
                WallBox(b, "flat_metal", w, -.05f, L + .05f, 4.8f, 5.0f, .12f, X("8E9294"));
            }
            Plane(b, "wave", 24f, 6f, 48f, 18f, 5f, X("A9AEB0"));
            // material store: pallets of bricks / blocks, formwork stack
            for (int i = 0; i < 3; i++)
            {
                Vector3 q = new(-30f + i * 2.2f, 0, 18f);
                BoxMM(b, "planks", q, q + new Vector3(1.2f, .15f, 1.0f), Own("planks"));
                BoxMM(b, i == 1 ? "cinder" : "brick_roman", q + new Vector3(.05f, .15f, .05f), q + new Vector3(1.15f, 1.05f, .95f), i == 1 ? Own("cinder") : Own("brick_roman"));
            }
            BoxMM(b, "osb", new Vector3(-30f, 0, 21.5f), new Vector3(-27.5f, .9f, 22.8f), Own("osb"));
            // site fence: blue profiled sheet ~2 m, posts inside, top trim; main gate 19 m open, leaves swung in
            string infill = p.GateInfill == "mesh" ? Chain("mesh_" + code, "B5BAB8", true) : "trapez";
            foreach (var (a, e) in new[] { (new Vector2(-58f, -22f), new Vector2(-9.5f, -22f)), (new Vector2(9.5f, -22f), new Vector2(58f, -22f)), (new Vector2(58f, -22f), new Vector2(58f, 62f)), (new Vector2(-58f, 62f), new Vector2(-58f, -22f)) })
            {
                var w = G0.Wall(a, e); float L = (e - a).magnitude;
                Wall(b, "trapez", w, 0, L, 0, 2f, X(p.Fence));
                Wall(b, "trapez", G0.Wall(e, a), 0, L, 0, 2f, X(p.Fence) * .92f);
                WallBox(b, "flat_metal", w, 0, L, 1.92f, 2.04f, .05f, X(p.FenceTrim));
                for (float s = 0; s <= L; s += 3f) Box(b, "flat_metal", w, new Vector3(s, 1.05f, .1f), new Vector3(.08f, 2.1f, .08f), X("8E9294"));
            }
            for (int leaf = 0; leaf < 2; leaf++)
            {
                float sx = leaf == 0 ? -9.5f : 9.5f, dir = leaf == 0 ? 1 : -1;
                Vector3 hinge = new(sx, 0, -22f), end = hinge + Quaternion.Euler(0, dir * -35f, 0) * new Vector3(dir * 4.75f, 0, 0);
                var w = G0.Wall(new Vector2(hinge.x, hinge.z), new Vector2(end.x, end.z));
                if (infill == "trapez") { Wall(b, "trapez", w, .05f, 4.7f, .1f, 1.95f, X(p.Fence)); Wall(b, "trapez", G0.Wall(new Vector2(end.x, end.z), new Vector2(hinge.x, hinge.z)), .05f, 4.7f, .1f, 1.95f, X(p.Fence) * .92f); }
                else Wall(b, infill, w, .05f, 4.7f, .1f, 1.95f, Color.white);
                foreach (float y in new[] { .08f, 1.97f }) Box(b, "flat_metal", w, new Vector3(2.375f, y, 0), new Vector3(4.75f, .07f, .06f), X("8E9294"));
                foreach (float s in new[] { .03f, 4.72f }) Box(b, "flat_metal", w, new Vector3(s, 1.02f, 0), new Vector3(.07f, 2f, .06f), X("8E9294"));
                Box(b, "flat_metal", G0, hinge + new Vector3(0, 1.2f, 0), new Vector3(.16f, 2.4f, .16f), X("6E7376"));
            }
            // guard booth at the gate
            BoxMM(b, "trapez", new Vector3(11f, 0, -20f), new Vector3(15.8f, 2.6f, -15.6f), X(p.Cabins[0]));
            BoxMM(b, "flat_gloss", new Vector3(11.5f, 1.1f, -20.03f), new Vector3(15.3f, 2.1f, -20f), X("4F6470"));
            BoxMM(b, "flat_metal", new Vector3(10.8f, 2.6f, -20.2f), new Vector3(16f, 2.8f, -15.4f), X(p.CabTrim));
        }

        static void Cabin(Batch b, Vector3 at, Color col, Color trim, string id)
        {
            const float W = 2.4f, D = 6f, H = 2.6f;
            BoxMM(b, "trapez", at + new Vector3(-W / 2, .2f, -D / 2), at + new Vector3(W / 2, H, D / 2), col);
            foreach (float x in new[] { -W / 2, W / 2 }) foreach (float z in new[] { -D / 2, D / 2 }) BoxMM(b, "flat_metal", at + new Vector3(x - .07f, 0, z - .07f), at + new Vector3(x + .07f, H + .05f, z + .07f), trim);
            BoxMM(b, "flat_metal", at + new Vector3(-W / 2 - .07f, H - .1f, -D / 2 - .07f), at + new Vector3(W / 2 + .07f, H + .1f, D / 2 + .07f), trim);
            BoxMM(b, "flat", at + new Vector3(-.95f, .25f, -D / 2 - .04f), at + new Vector3(-.05f, 2.2f, -D / 2 + .01f), X("5A5F63"));
            BoxMM(b, "flat_gloss", at + new Vector3(.25f, 1.0f, -D / 2 - .03f), at + new Vector3(1.0f, 1.9f, -D / 2 + .01f), X("4F6470"));
            BoxMM(b, "flat", at + new Vector3(.2f, .95f, -D / 2 - .05f), at + new Vector3(1.05f, 1.0f, -D / 2 + .01f), trim);
            BoxMM(b, "flat_metal", at + new Vector3(-1.1f, 0, -D / 2 - .7f), at + new Vector3(.1f, .22f, -D / 2), X("6E7376"));
            BoxMM(b, "flat_gloss", at + new Vector3(W / 2 - .01f, 1.1f, -1f), at + new Vector3(W / 2 + .03f, 1.9f, .4f), X("4F6470"));
        }

        static void TowerCrane(Batch b, Vector3 at, Color paint, Color dark)
        {
            const float H = 36f, m = 1.6f;
            BoxMM(b, "conc", at + new Vector3(-2.5f, 0, -2.5f), at + new Vector3(2.5f, .8f, 2.5f), X("B9B5AD"));
            for (int k = 0; k < 4; k++) Box(b, "flat_metal", G0, at + new Vector3((k % 2 - .5f) * m, H / 2 + .8f, (k / 2 - .5f) * m), new Vector3(.14f, H, .14f), paint);
            for (float y = .8f; y < H; y += 2f)
            {
                foreach (var (a, e) in new[] { (new Vector3(-m / 2, 0, -m / 2), new Vector3(m / 2, 0, -m / 2)), (new Vector3(m / 2, 0, -m / 2), new Vector3(m / 2, 0, m / 2)), (new Vector3(m / 2, 0, m / 2), new Vector3(-m / 2, 0, m / 2)), (new Vector3(-m / 2, 0, m / 2), new Vector3(-m / 2, 0, -m / 2)) })
                {
                    Beam(b, "flat_metal", at + a + Vector3.up * y, at + e + Vector3.up * y, .08f, .08f, paint);
                    Beam(b, "flat_metal", at + a + Vector3.up * y, at + e + Vector3.up * (y + 2f), .06f, .06f, paint);
                }
            }
            float top = H + .8f;
            BoxMM(b, "flat_metal", at + new Vector3(-1.2f, top, -1.2f), at + new Vector3(1.2f, top + 1.2f, 1.2f), dark);
            BoxMM(b, "flat_metal", at + new Vector3(.9f, top - .2f, -2.2f), at + new Vector3(2.5f, top + 1.6f, -.6f), paint);           // cab
            BoxMM(b, "flat_gloss", at + new Vector3(2.5f, top + .4f, -2.1f), at + new Vector3(2.53f, top + 1.4f, -.7f), X("4F6470"));
            // jib (+X, 40 m): two bottom chords + top chord + diagonals
            float L = 40f;
            Vector3 j0 = at + new Vector3(1.2f, top + 1.2f, 0);
            for (float s = 0; s < L; s += 2f)
            {
                Vector3 a = j0 + new Vector3(s, 0, 0), e = j0 + new Vector3(s + 2f, 0, 0);
                foreach (float z in new[] { -.6f, .6f }) Beam(b, "flat_metal", a + new Vector3(0, 0, z), e + new Vector3(0, 0, z), .1f, .1f, paint);
                Beam(b, "flat_metal", a + new Vector3(0, 1.4f, 0), e + new Vector3(0, 1.4f, 0), .1f, .1f, paint);
                foreach (float z in new[] { -.6f, .6f }) Beam(b, "flat_metal", a + new Vector3(0, 0, z), e + new Vector3(-1f, 1.4f, 0), .06f, .06f, paint);
            }
            // counter-jib (-X, 12 m) with concrete weights, tower head and ties
            for (float s = 0; s < 12f; s += 2f) foreach (float z in new[] { -.8f, .8f }) Beam(b, "flat_metal", at + new Vector3(-1.2f - s, top + 1.2f, z), at + new Vector3(-3.2f - s, top + 1.2f, z), .12f, .12f, paint);
            for (int k = 0; k < 3; k++) BoxMM(b, "conc", at + new Vector3(-12.6f + k * 1.1f, top - .8f, -.9f), at + new Vector3(-11.6f + k * 1.1f, top + 1.2f, .9f), X("BDB9B1"));
            Beam(b, "flat_metal", at + new Vector3(0, top + 1.2f, 0), at + new Vector3(0, top + 7f, 0), .4f, .4f, paint);
            Beam(b, "flat_metal", at + new Vector3(0, top + 7f, 0), j0 + new Vector3(22f, 1.4f, 0), .05f, .05f, dark);
            Beam(b, "flat_metal", at + new Vector3(0, top + 7f, 0), at + new Vector3(-12f, top + 1.3f, 0), .05f, .05f, dark);
            // trolley + hook
            BoxMM(b, "flat_metal", j0 + new Vector3(18f, -.4f, -.7f), j0 + new Vector3(19.4f, 0, .7f), dark);
            Beam(b, "flat_metal", j0 + new Vector3(18.7f, -.4f, 0), j0 + new Vector3(18.7f, -18f, 0), .03f, .03f, dark);
            BoxMM(b, "flat_metal", j0 + new Vector3(18.3f, -18.8f, -.3f), j0 + new Vector3(19.1f, -18f, .3f), X("E2B32E"));
        }

        // ================================================================== 7. Quiet Valley Q1-Q3
        sealed class QPal { public string Lab, LabCol, Upper, UpperCol, Fin, FinCol, Frame, Door, Soffit, Glass, Casino, CasinoCol, Trim, Canopy, Fence; public int FenceType; }

        static void Valley(Transform d)
        {
            var g = new Batch();
            Plane(g, "meadow", -260, -260, 260, 260, -.03f, Own("meadow"));
            Plane(g, "asphalt", -3f, -60f, 3f, 0f, .01f, Own("asphalt"));
            Plane(g, "asphalt", -3f, -6f, 80f, 0f, .011f, Own("asphalt"));
            Plane(g, "asphalt", 34f, 0f, 66f, 6f, .011f, Own("asphalt"));
            var ctx = Group(d, "Context");
            Flush(g, ctx, "Va_ctx");
            foreach (var q in new[] { new Vector3(-26f, 0, 4f), new Vector3(24f, 0, 2f), new Vector3(-30f, 0, 34f), new Vector3(76f, 0, 10f), new Vector3(28f, 0, 32f) })
                Prop(q.x > 60 || q.x < -28 ? "TREES/tree_oak_a" : "TREES/tree_palm_b", ctx, q, Hash(q.ToString()) * 360f);
            var pals = new[]
            {
                new QPal { Lab = "panel", LabCol = "ECEDEA", Upper = "panel", UpperCol = "F2F2EF", Fin = "flat", FinCol = "F4F4F2", Frame = "C8CCCE", Door = "D6D8D8", Soffit = "larch", Glass = "9FC6CF",
                    Casino = "plaster", CasinoCol = "DDB9A0", Trim = "C9A44C", Canopy = "A8323A", Fence = "F2F0EA", FenceType = 0 },
                new QPal { Lab = "board", LabCol = "D6D0C4", Upper = "larch", UpperCol = null, Fin = "flat", FinCol = "5A4A3A", Frame = "5A4A3A", Door = "8A7660", Soffit = "larch", Glass = "A9BDB8",
                    Casino = "travertine", CasinoCol = "E6D6BC", Trim = "8C6A3E", Canopy = "2F5A46", Fence = "9C8A70", FenceType = 1 },
                new QPal { Lab = "panel", LabCol = "3C4045", Upper = "conc", UpperCol = "E2E0DA", Fin = "flat", FinCol = "2B2D30", Frame = "1E2022", Door = "3C4045", Soffit = "teak", Glass = "8FA6B4",
                    Casino = "plaster", CasinoCol = "7A2E36", Trim = "C9A44C", Canopy = "1E2022", Fence = "4A4038", FenceType = 2 },
            };
            for (int v = 1; v <= 3; v++)
            {
                var grp = Group(d, "Q" + v);
                var b = new Batch();
                ValleyVariant(b, grp, pals[v - 1], "Q" + v);
                Flush(b, grp, "Va_Q" + v);
            }
        }

        static void ValleyVariant(Batch b, Transform grp, QPal p, string code)
        {
            string gk = Glass("glass_" + code, p.Glass);
            Color lc = C(p.Lab, p.LabCol), uc = C(p.Upper, p.UpperCol), fr = X(p.Frame);
            Plane(b, "conc", -19.2f, 0f, 19.2f, 10f, .015f, X("D4D0C6"));
            // ground floor 38.4 x 18.8 x 4: garage (2 doors), recessed glazed lobby, OR wing with high band windows
            var gw = new (Vector2 a, Vector2 e)[] { (new(-19.2f, 10f), new(19.2f, 10f)), (new(19.2f, 10f), new(19.2f, 28.8f)), (new(19.2f, 28.8f), new(-19.2f, 28.8f)), (new(-19.2f, 28.8f), new(-19.2f, 10f)) };
            for (int i = 0; i < 4; i++)
            {
                var w = G0.Wall(gw[i].a, gw[i].e); float L = (gw[i].e - gw[i].a).magnitude;
                var holes = new List<Rect>();
                if (i == 0) { holes.Add(Rect.MinMaxRect(.8f, 0, 5.6f, 3.8f)); holes.Add(Rect.MinMaxRect(6.6f, 0, 11.4f, 3.8f)); holes.Add(Rect.MinMaxRect(13.2f, 0, 25.2f, 3.9f)); holes.Add(Rect.MinMaxRect(26.8f, 2.4f, 37.6f, 3.5f)); }
                if (i == 1 || i == 3) holes.Add(Rect.MinMaxRect(3f, 2.4f, L - 3f, 3.5f));
                OpeningsWall(b, p.Lab, w, L, 0, 4f, lc, holes, i == 0 ? .2f : .15f);
                int k = 0;
                foreach (var o in holes)
                {
                    if (o.width < 6f && o.yMin == 0) { Box(b, "shutter", w, new Vector3(o.center.x, o.center.y, .22f), new Vector3(o.width, o.height, .02f), X(p.Door)); WallBox(b, "flat_metal", w, o.xMin - .1f, o.xMax + .1f, o.yMax, o.yMax + .15f, .1f, fr); continue; }
                    int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.6f)); float pw = o.width / n;
                    float z = i == 0 && o.yMin == 0 ? 2.2f : .16f;                                   // lobby glass 2 m back
                    for (int j = 0; j < n; j++) Pane(b, gk, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), z, Cell(code + i + k + j));
                    for (int j = 0; j <= n; j++) Box(b, "flat_metal", w, new Vector3(o.xMin + j * pw, o.center.y, z - .05f), new Vector3(.07f, o.height, .1f), fr);
                    Box(b, "flat_metal", w, new Vector3(o.center.x, o.yMax - .04f, z - .05f), new Vector3(o.width, .08f, .1f), fr);
                    if (z > 1f)
                    {
                        Box(b, p.Lab, w, new Vector3(o.xMin + .01f, o.center.y, z / 2), new Vector3(.02f, o.height, z), lc);
                        Box(b, p.Lab, w, new Vector3(o.xMax - .01f, o.center.y, z / 2), new Vector3(.02f, o.height, z), lc);
                        Box(b, p.Soffit, w, new Vector3(o.center.x, o.yMax + .01f, z / 2), new Vector3(o.width, .02f, z), Own(p.Soffit));
                    }
                    k++;
                }
            }
            // upper floor 33.2 x 18 x 3.6, cantilevered 2 m over the forecourt: ribbon glazing with vertical fins, solid end panels
            var uw = new (Vector2 a, Vector2 e)[] { (new(-14f, 8f), new(19.2f, 8f)), (new(19.2f, 8f), new(19.2f, 26f)), (new(19.2f, 26f), new(-14f, 26f)), (new(-14f, 26f), new(-14f, 8f)) };
            for (int i = 0; i < 4; i++)
            {
                var w = Fr.Yaw(new Vector3(0, 4f, 0), 0).Wall(uw[i].a, uw[i].e); float L = (uw[i].e - uw[i].a).magnitude;
                var holes = new List<Rect>();
                if (i == 0) holes.Add(Rect.MinMaxRect(3f, .7f, L - 2f, 3.0f));
                if (i == 2) holes.Add(Rect.MinMaxRect(2f, .9f, L - 2f, 2.6f));
                if (i == 1 || i == 3) holes.Add(Rect.MinMaxRect(4f, .7f, L - 4f, 3.0f));
                OpeningsWall(b, p.Upper, w, L, 0, 4.2f, uc, holes, .2f);
                foreach (var o in holes)
                {
                    int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.6f)); float pw = o.width / n;
                    for (int j = 0; j < n; j++) Pane(b, gk, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), .205f, Cell(code + "u" + i + j));
                    for (int j = 0; j <= n; j++) { Box(b, "flat_metal", w, new Vector3(o.xMin + j * pw, o.center.y, .15f), new Vector3(.06f, o.height, .1f), fr); if (i == 0) WallBox(b, p.Fin, w, o.xMin + j * pw - .06f, o.xMin + j * pw + .06f, o.yMin - .3f, o.yMax + .3f, .55f, X(p.FinCol)); }
                }
                WallBox(b, "flat_metal", w, -.05f, L + .05f, 4.2f, 4.35f, .1f, fr);
            }
            Box(b, p.Soffit, G0, new Vector3(2.6f, 3.995f, 9f), new Vector3(33.2f, .01f, 2f), Own(p.Soffit));
            Plane(b, "roof_flat", -19.2f, 10f, -14f, 28.8f, 4.02f, Own("roof_flat"));
            Plane(b, "roof_flat", -14f, 8f, 19.2f, 26f, 8.22f, Own("roof_flat"));
            for (int k = 0; k < 3; k++) { BoxMM(b, "flat_gloss", new Vector3(-8f + k * 9f, 8.2f, 13f), new Vector3(-4.6f + k * 9f, 8.9f, 18f), X(p.Glass) * .8f); BoxMM(b, "flat_metal", new Vector3(-8.1f + k * 9f, 8.2f, 12.9f), new Vector3(-4.5f + k * 9f, 8.3f, 18.1f), fr); }
            // entrance canopy on two slim columns
            BoxMM(b, "flat", new Vector3(-6.5f, 3.7f, 3.5f), new Vector3(6.5f, 4f, 10f), X(p.FinCol));
            foreach (float x in new[] { -5.5f, 5.5f }) Cyl(b, "flat_metal", new Vector3(x, 0, 4.4f), .12f, 3.7f, 10, fr);
            // casino 40 x 17.2 m: stucco, plinth, tall windows with trims, portico on 4 columns, cornice band, roof sign + neon
            const float cx0 = 30f, cx1 = 70f, cz0 = 12f, cz1 = 29.2f, CH = 6.4f;
            Color cc = C(p.Casino, p.CasinoCol), trim = X(p.Trim);
            var cw = new (Vector2 a, Vector2 e)[] { (new(cx0, cz0), new(cx1, cz0)), (new(cx1, cz0), new(cx1, cz1)), (new(cx1, cz1), new(cx0, cz1)), (new(cx0, cz1), new(cx0, cz0)) };
            for (int i = 0; i < 4; i++)
            {
                var w = G0.Wall(cw[i].a, cw[i].e); float L = (cw[i].e - cw[i].a).magnitude;
                var holes = new List<Rect>();
                if (i == 0) { for (float s = 3f; s < L - 2f; s += 4f) if (Mathf.Abs(s + 1f - L / 2) > 4f) holes.Add(Rect.MinMaxRect(s, .9f, s + 2f, 4.9f)); holes.Add(Rect.MinMaxRect(L / 2 - 2.2f, 0, L / 2 + 2.2f, 3.6f)); }
                if (i == 1 || i == 3) for (float s = 3f; s < L - 2f; s += 4.5f) holes.Add(Rect.MinMaxRect(s, .9f, s + 2f, 4.9f));
                OpeningsWall(b, p.Casino, w, L, 0, CH + .8f, cc, holes, .25f);
                int k = 0;
                foreach (var o in holes)
                {
                    OfficeWindow(b, w, o, .25f, Glass("glass_casino", "6A7C88"), trim, code + "c" + i + k++, 1, .75f, trim, .07f);
                    WallBox(b, "flat_metal", w, o.xMin - .18f, o.xMax + .18f, o.yMax, o.yMax + .22f, .1f, trim);
                }
                WallBox(b, "stone", w, 0, L, 0, .6f, .06f, X("D9D2C4"));
                WallBox(b, "flat_metal", w, -.05f, L + .05f, CH - .2f, CH + .15f, .25f, trim);
                WallBox(b, "flat", w, -.05f, L + .05f, CH + .8f, CH + .95f, .12f, X(Shade(p.CasinoCol ?? "E6D6BC", 1.08f)));
            }
            Plane(b, "roof_flat", cx0, cz0, cx1, cz1, CH + .02f, Own("roof_flat"));
            BoxMM(b, "flat_metal", new Vector3(43f, 3.9f, 6.5f), new Vector3(57f, 4.4f, 12f), X(p.Canopy));
            BoxMM(b, "flat_metal", new Vector3(42.9f, 4.3f, 6.4f), new Vector3(57.1f, 4.45f, 12.1f), trim);
            foreach (float x in new[] { 43.6f, 47.5f, 52.5f, 56.4f }) Cyl(b, "flat_metal", new Vector3(x, 0, 7.1f), .22f, 3.9f, 12, trim);
            Plane(b, "conc", 40f, 6f, 60f, 12f, .015f, X("D4D0C6"));
            var sign = Prop("VALLEY/casino_crown_sign", grp, new Vector3(50f, CH + .9f, 12.4f), 180);
            Prop("VALLEY/neon_star", grp, new Vector3(41.5f, 4.8f, 11.7f), 180); Prop("VALLEY/neon_star", grp, new Vector3(58.5f, 4.8f, 11.7f), 180);
            // low wooden fence ~1 m with the opening for the drive
            Color fcol = X(p.Fence);
            foreach (var (x0, x1) in new[] { (-60f, -4f), (4f, 85f) })
            {
                float z = -12f;
                if (p.FenceType == 0)
                {   // white picket
                    for (float x = x0; x <= x1; x += 2f) BoxMM(b, "flat", new Vector3(x - .05f, 0, z - .05f), new Vector3(x + .05f, 1.1f, z + .05f), fcol);
                    foreach (float y in new[] { .3f, .8f }) BoxMM(b, "flat", new Vector3(x0, y, z + .05f), new Vector3(x1, y + .08f, z + .09f), fcol);
                    for (float x = x0 + .08f; x < x1; x += .16f) BoxMM(b, "flat", new Vector3(x - .04f, .06f, z - .06f), new Vector3(x + .04f, .98f, z - .04f), fcol);
                }
                else if (p.FenceType == 1)
                {   // natural ranch rails
                    for (float x = x0; x <= x1; x += 2.5f) BoxMM(b, "planks_w", new Vector3(x - .07f, 0, z - .07f), new Vector3(x + .07f, 1.15f, z + .07f), fcol);
                    foreach (float y in new[] { .45f, .9f }) BoxMM(b, "planks_w", new Vector3(x0, y, z - .14f), new Vector3(x1, y + .14f, z - .07f), fcol);
                }
                else
                {   // dark stained closed board fence with a cap rail
                    var w = G0.Wall(new Vector2(x0, z), new Vector2(x1, z));
                    Wall(b, "planks_w", w, 0, x1 - x0, 0, 1f, fcol);
                    Wall(b, "planks_w", G0.Wall(new Vector2(x1, z + .04f), new Vector2(x0, z + .04f)), 0, x1 - x0, 0, 1f, fcol);
                    BoxMM(b, "planks_w", new Vector3(x0, 1f, z - .05f), new Vector3(x1, 1.06f, z + .09f), fcol * 1.1f);
                    for (float x = x0; x <= x1; x += 2.4f) BoxMM(b, "planks_w", new Vector3(x - .06f, 0, z + .04f), new Vector3(x + .06f, 1.04f, z + .14f), fcol);
                }
            }
        }
    }
}
