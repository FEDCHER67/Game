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
    // TextureTest_Houses_v01 (Fedya 20.10.2026, CL-TEXTEST): one cheap test piece per district to judge the house textures before
    // the whole map is textured. Hamlet: two neighbouring houses (H1, H2); Rough: one khrushchevka block, 8 bays x 5 floors on the
    // KH1b grid (R1 KH1b, R2 KH2); Downtown: a 43.5 m street segment, carriageway 12 m + 2 x 5 m sidewalks, 4 buildings 5-8 floors (D1, D2).
    // Each variant is a sibling group at the same place (only one active; toggle it in the hierarchy or use the menu).
    // Look: sky, sun, district weather / fog / aerial haze, district light volumes, PostFX_v17 and wind are copied from the
    // playtested i10 scene exactly as W76LookV01 does it, and the test pieces stand inside the W76 district rectangles, so the
    // district light of the map applies (Hamlet brightest, Rough grey and foggy, Downtown normal).
    // Materials: approved materials are reused untouched where the texture is the same (V19 boards / logs / brick / stucco v07 /
    // concrete, wavy slate roof sheet, flat bitumen roof) with UV = metres / tile (the W76 convention, material tiling 1).
    // New materials live only in Art/TextureTest_v01/Built: textures that had no Unity material yet (KH1b, KH2-KH4, KH window
    // atlas, the GPT facades, stucco v01, ground), the kit materials (FBX UV0 is 1 UV = 1 m, so the tiling sits in the material)
    // and flat painted colours. House colour = vertex colour on the palette shaders (tint = colour / texture mean _TintRef).
    // Texel density (px per metre) of every surface is written to Built/TextureTest_build_log.txt.
    public static class TextureTestHousesV01
    {
        const string Root = "Assets/OnlyVolunteers/Art/TextureTest_v01";
        const string Built = Root + "/Built";
        const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/TextureTest_Houses_v01.unity";
        const string I10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string KitSrc = "ArtSource/Props/FACADE_KIT_v01/FBX";
        const string Rev = "Working/Reviews/Textures_2026-10-17/";
        const string Gpt = Rev + "gpt_missing_v02_2026-10-18/Textures/";
        const string SK = "Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/";
        const string V19M = "Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02/Materials/";
        const string ShotDir = "Working/Reviews/TextureTest_v01/raw";
        const int ShotW = 1600, ShotH = 900;

        // W76 district rectangles (W76LookV01.Rects; i10 ids: village = Hamlet, residential = Rough, old_town = Downtown)
        static readonly Dictionary<string, Vector4> Rects = new()
        {
            ["forest"] = new(185, 60, 470, 330), ["village"] = new(180, 360, 470, 625), ["transition"] = new(525, 345, 705, 495),
            ["residential"] = new(655, 668, 1006, 905), ["old_town"] = new(790, 228, 1268, 470), ["industrial"] = new(1172, 596, 1356, 684),
            ["elite"] = new(1340, 255, 1500, 390), ["fields"] = new(520, 60, 665, 300), ["beach"] = new(790, 100, 1520, 228),
            ["tramduro"] = new(1450, 690, 1650, 840),
        };

        static readonly StringBuilder Log = new();
        static void Note(string s) { Log.AppendLine(s); }

        // ================================================================== menu / batch
        [MenuItem("OnlyVolunteers/Map/Texture Test v01/Build TextureTest_Houses_v01")]
        public static void BuildMenu() { if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) Build(); }

        [MenuItem("OnlyVolunteers/Map/Texture Test v01/Capture all variants")]
        public static void CaptureMenu() => Capture();

        [MenuItem("OnlyVolunteers/Map/Texture Test v01/Show H1 R1 D1 (defaults)")]
        public static void ShowDefaults() { foreach (string c in new[] { "H1", "R1", "D1" }) Show(c); }

        // batch: Unity.exe -batchmode -projectPath C:\Dev\Game -executeMethod OnlyVolunteers.Art.TextureTest.TextureTestHousesV01.BatchRun
        public static void BatchRun()
        {
            int code = 0;
            try { Build(); Capture(); }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        public static void BatchCaptureOnly()
        {
            int code = 0;
            try { EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); Capture(); }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        // ================================================================== build
        public static void Build()
        {
            Log.Clear(); Surfs.Clear(); KitM.Clear(); Kit.Clear(); Accents.Clear();
            var t0 = DateTime.Now;
            if (AssetDatabase.IsValidFolder(Built)) AssetDatabase.DeleteAsset(Built);
            foreach (string f in new[] { "Textures", "Materials", "Materials/Kit", "Meshes", "Kit", "Look" }) Folder(Built + "/" + f);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("TextureTest_Houses_v01").transform;
            Surfaces();
            KitMaterials();
            ImportKit();
            var cam = Look(root);
            Vector3 sun = ProbeSun(cam);
            Note($"sun direction (towards the sun) {sun}");
            var field = PaletteField();
            var hamlet = District(root, "TT_Hamlet", Place("village", new Vector2(325, 490), field), sun);
            var rough = District(root, "TT_Rough", Place("residential", new Vector2(830, 786), field), sun);
            var downtown = District(root, "TT_Downtown", Place("old_town", new Vector2(1030, 350), field), sun);
            Hamlet(hamlet); Rough(rough); Downtown(downtown);
            // capture points (district-local position, target): eye 1.7 m, van 2.3 m, 3/4 overview
            // (scope cut by Fedya 21.10: eye-height shot + 3/4 overview per variant, 2 variants per district)
            Shots(hamlet, ("eye", new Vector3(-12f, 1.7f, -12.5f), new Vector3(1f, 2.3f, 0f)), ("overview", new Vector3(-13f, 8.5f, -15f), new Vector3(.5f, 2.2f, .5f)));
            Shots(rough, ("eye", new Vector3(-1.5f, 1.7f, -16f), new Vector3(-4.8f, 4.2f, -6.4f)), ("overview", new Vector3(-22f, 13f, -25f), new Vector3(0f, 6f, -1f)));
            Shots(downtown, ("eye", new Vector3(-8f, 1.85f, -8.6f), new Vector3(4f, 7.5f, 11f)), ("overview", new Vector3(-28f, 20f, -21f), new Vector3(0f, 11f, 15f)));
            ShowDefaults();
            var eye = hamlet.Find("Shots/eye");
            if (eye) cam.transform.SetPositionAndRotation(eye.position, eye.rotation);
            Note("texel density (px per metre along U, texture width / tile): " + string.Join("; ", Surfs.Where(s => s.Value.Px > 0)
                .Select(s => $"{s.Key} {s.Value.Px / s.Value.TU:0} ({s.Value.Px} px / {s.Value.TU:0.##} m)")));
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Note($"built in {(DateTime.Now - t0).TotalSeconds:0} s");
            File.WriteAllText(Built + "/TextureTest_build_log.txt", Log.ToString());
            AssetDatabase.ImportAsset(Built + "/TextureTest_build_log.txt");
            Debug.Log("[TextureTest] build done\n" + Log);
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

        // ================================================================== look (W76LookV01 without terrain and grass)
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
                    // flat test ground at y = 0: ground heights 0 over the W76 world rectangle
                    var gh = new Texture2D(8, 8, TextureFormat.RFloat, false, true) { name = "TT_GroundHeights_v01", wrapMode = TextureWrapMode.Clamp };
                    gh.SetPixels(Enumerable.Repeat(new Color(0, 0, 0, 1), 64).ToArray()); gh.Apply();
                    AssetDatabase.CreateAsset(gh, Built + "/Look/TT_GroundHeights_v01.asset");
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
                    Note($"fog: {fog.banks.Length} mist banks on the W76 Rough / Forest rectangles, flat ground heights");
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
            camGo.transform.position = new Vector3(325, 2, 470);
            Note($"i10 look copied: palette/weather/fog + {palette?.GetComponentsInChildren<Volume>(true).Length ?? 0} light volumes, G22 sky, V19Wind, Sun, PostFX_v17; camera FOV {camFov} far {camFar}");
            return cam;
        }

        // The painted-sky rig turns the sun per camera from its clock and azimuth; one tiny render gives the real direction.
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

        // Reused V19 materials lerp to their own legacy colour where the i10-space palette field is set; pick a spot where it is 0
        // (so the per-house colour shows), as close as possible to the preferred centre and >= 75 m inside the district rectangle.
        static Func<Vector2, float> PaletteField()
        {
            var m = Surfs["brick"].M;
            var tex = m.HasProperty("_DistrictMask") ? m.GetTexture("_DistrictMask") as Texture2D : null;
            if (!tex) return p => 0f;
            Vector4 dw = m.GetVector("_DistrictWorld");
            var rt = RenderTexture.GetTemporary(tex.width, tex.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear);
            Graphics.Blit(tex, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var cpu = new Texture2D(tex.width, tex.height, TextureFormat.RGBA32, false, true);
            cpu.ReadPixels(new Rect(0, 0, tex.width, tex.height), 0, 0); cpu.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
            return p => cpu.GetPixelBilinear((p.x - dw.x) / dw.z, (p.y - dw.y) / dw.w).r;
        }

        static Vector2 Place(string district, Vector2 preferred, Func<Vector2, float> field)
        {
            float Max(Vector2 c) { float m = 0; for (int i = -4; i <= 4; i++) for (int j = -4; j <= 4; j++) m = Mathf.Max(m, field(c + new Vector2(i, j) * 9f)); return m; }
            var r = Rects[district];
            Vector2 best = preferred; float bestScore = Max(preferred) * 1000f;
            if (bestScore > 1f)
                for (float x = r.x + 75; x <= r.z - 75; x += 10) for (float z = r.y + 75; z <= r.w - 75; z += 10)
                {
                    var c = new Vector2(x, z); float s = Max(c) * 1000f + (c - preferred).magnitude * .01f;
                    if (s < bestScore) { bestScore = s; best = c; }
                }
            Note($"{district}: palette field max {Max(preferred):0.000} at preferred {preferred}; placed at {best} (field max {Max(best):0.000})");
            return best;
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
            foreach (Transform s in g.parent) if (s.name.Length == 2 && char.IsDigit(s.name[1])) s.gameObject.SetActive(s == g);
        }

        // ================================================================== capture
        public static void Capture()
        {
            var cam = Object.FindObjectsByType<Camera>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).FirstOrDefault(c => c.CompareTag("MainCamera"));
            if (!cam) throw new Exception("no main camera; build the scene first");
            Directory.CreateDirectory(ShotDir);
            var keep = (cam.transform.position, cam.transform.rotation);
            int n = 0;
            foreach (var d in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(t => t.name.StartsWith("TT_")).OrderBy(t => t.name))
            {
                var codes = d.Cast<Transform>().Where(s => s.name.Length == 2 && char.IsDigit(s.name[1])).Select(s => s.name).OrderBy(s => s).ToList();
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
            cam.transform.SetPositionAndRotation(keep.position, keep.rotation);
            Debug.Log($"[TextureTest] {n} shots -> {ShotDir}");
        }

        static void Render(Camera cam, string file)
        {
            var rt = new RenderTexture(ShotW, ShotH, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            rt.Create();
            var resolved = new RenderTexture(ShotW, ShotH, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            resolved.Create();
            cam.targetTexture = rt;
            cam.Render(); cam.Render();          // second frame: shadows / volumes / fog of a moved camera settle
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
        sealed class Surf { public Material M; public float TU = 1, TV = 1; public Color Own = Color.white; public bool Reused; public int Px; public Texture2D Tex; }
        static readonly Dictionary<string, Surf> Surfs = new();

        static void Surfaces()
        {
            // reused as they are (approved; texture identical)
            Reuse("boards", V19M + "V19_V3S17_5a_wood_planks_fences_8C6B4A.mat", 3, 3);
            Reuse("logs", V19M + "V19_V3S17_5b_logs_8F6E4E.mat", 3, 3);
            Reuse("brick", V19M + "V19_V3S17_3a_brick_B46A4F.mat", 3, 3);
            Reuse("stucco_v07", V19M + "V19_V3S17_3b_plaster_stucco_857C6E.mat", 4, 4);
            Reuse("concrete", V19M + "V19_V3S17_3c_concrete_panels_857C6E.mat", 4, 4);
            Reuse("roof_sheet", V19M + "V19_V3S17_4c_corrugated_metal_5F6260.mat", 3, 3);
            Reuse("roof_tile", V19M + "V19_V3S17_4a_clay_roof_tiles_5F6260.mat", 3, 3);
            Reuse("slate_wavy", "Assets/OnlyVolunteers/Map/Look/Materials/Look_mat_roof_sheet__5B6D6A.mat", 3, 3);
            Reuse("roof_flat", "Assets/OnlyVolunteers/Map/LookV3/Materials/V3S_4d_flat_bitumen_roof.mat", 4, 4);
            // new: textures without a Unity material so far
            // painted boards: same SK 5a texture as the reused V19 boards, but without the i10-space palette field, which at the W76
            // Hamlet spot pulls the reused material 80 % back to its own wood colour and would hide the house colour
            New("boards_paint", SK + "5a_wood_planks_fences/5a_wood_planks_fences_v07_albedo.png", 3, 3);
            New("stucco_v01", SK + "3b_plaster_stucco/3b_plaster_stucco_v01_albedo.png", 4, 4);
            New("KH1b", Rev + "candidates_rough_soviet_v02/KH1b_panel_grey_shabby_albedo.png", 12.8f, 11.2f);
            New("KH2", Rev + "candidates_rough_soviet_v01/KH2_panel_small_tiles_albedo.png", 6.4f, 5.6f);
            New("KH3", Rev + "candidates_rough_soviet_v01/KH3_silicate_brick_white_albedo.png", 1f, 1f);
            New("KH4", Rev + "candidates_rough_soviet_v01/KH4_red_brick_muted_albedo.png", 1f, 1f);
            New("dt_plaster", Gpt + "Facade_DT_plaster.png", 3.5f, 3.5f);
            New("dt_brick", Gpt + "Facade_DT_brick.png", 3.5f, 3.5f);
            New("dt_shop", Gpt + "Facade_DT_shop.png", 3.5f, 4f);
            New("hamlet_wood", Gpt + "Facade_Hamlet_wood.png", 3.5f, 3.5f);
            New("trim", Gpt + "FacadeTrim.png", 2f, .45f, clampV: true);
            New("meadow", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_meadow_albedo.png", 8, 8);
            New("worn_grass", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_worn_grass_albedo.png", 8, 8);
            New("dirt", SK + "1b_dirt_road/1b_dirt_road_v07_albedo.png", 6, 6);
            New("asphalt", Rev + "candidates_asphalt_v01/2a_asphalt_v07_A5d12_albedo.png", 6, 6);
            New("asphalt_old", SK + "2a_asphalt/2a_asphalt_v01_albedo.png", 6, 6);
            New("sidewalk", Rev + "candidates_paving_v01/S1_sidewalk_oar_1p5m_albedo.png", 3, 3);
            // flat painted colours (white texture, _TintRef 1: vertex colour = the colour)
            Flat("flat", .12f); Flat("glass", .86f);
            // KH window / door / streak atlas (200 px/m, transparent background)
            var atlas = Tex(Rev + "own_textures_v01/KH_windows_atlas_v01.png", TextureWrapMode.Clamp, TextureWrapMode.Clamp, true);
            Surfs["atlas"] = new Surf { M = Lit("TT_KH_windows_atlas_clip", Color.white, atlas, 1f, .35f, 0f, 1), Px = atlas ? atlas.width : 0, TU = 10.24f };
            Surfs["atlas_blend"] = new Surf { M = Lit("TT_KH_windows_atlas_streaks", new Color(1, 1, 1, .85f), atlas, 1f, .1f, 0f, 2) };
        }

        static Surf Reuse(string key, string path, float tu, float tv)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) throw new Exception("reuse target missing: " + path);
            Color own = Color.white;
            if (m.HasProperty("_TintRef")) { Vector4 t = m.GetVector("_TintRef"); own = new Color(t.x, t.y, t.z, 1f).gamma; }
            var tex = m.HasProperty("_BaseMap") ? m.GetTexture("_BaseMap") as Texture2D : null;
            return Surfs[key] = new Surf { M = m, TU = tu, TV = tv, Own = own, Reused = true, Tex = tex, Px = tex ? tex.width : 0 };
        }

        static Surf New(string key, string src, float tu, float tv, bool clampV = false, float smooth = .1f)
        {
            var tex = Tex(src, TextureWrapMode.Repeat, clampV ? TextureWrapMode.Clamp : TextureWrapMode.Repeat, false);
            var m = new Material(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "TT_" + key, enableInstancing = true };
            m.SetTexture("_BaseMap", tex);
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", 0f);
            m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            Color own = Median(src);
            m.SetVector("_TintRef", (Vector4)own.linear);
            AssetDatabase.CreateAsset(m, Built + "/Materials/TT_" + key + ".mat");
            return Surfs[key] = new Surf { M = m, TU = tu, TV = tv, Own = own, Tex = tex, Px = tex ? tex.width : 0 };
        }

        static void Flat(string key, float smooth)
        {
            var m = new Material(Shader.Find("OnlyVolunteers/StyleV3/Palette19")) { name = "TT_" + key, enableInstancing = true };
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", 0f); m.SetVector("_TintRef", Vector4.one); m.SetFloat("_MacroStrength", .02f);
            if (smooth < .5f) { m.SetFloat("_EnvironmentReflectionsOff", 1f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            AssetDatabase.CreateAsset(m, Built + "/Materials/TT_" + key + ".mat");
            Surfs[key] = new Surf { M = m };
        }

        static Texture2D Tex(string src, TextureWrapMode u, TextureWrapMode v, bool alpha)
        {
            string path = src;
            if (!src.StartsWith("Assets/"))
            {
                if (!File.Exists(src)) throw new Exception("texture missing: " + src);
                path = Built + "/Textures/" + Path.GetFileName(src);
                File.Copy(src, path, true);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = true;
                ti.wrapModeU = u; ti.wrapModeV = v; ti.alphaIsTransparency = alpha; ti.anisoLevel = 8; ti.maxTextureSize = 2048;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        // texture mean colour (sRGB) = per-channel median of a 200 x 200 sample grid (the GPT facades: wall colour, not the glass)
        static Color Median(string src)
        {
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            t.LoadImage(File.ReadAllBytes(src));
            var px = t.GetPixels32(); int w = t.width, h = t.height;
            var r = new List<byte>(); var g = new List<byte>(); var b = new List<byte>();
            for (int y = 0; y < 200; y++) for (int x = 0; x < 200; x++) { var c = px[(y * h / 200) * w + x * w / 200]; r.Add(c.r); g.Add(c.g); b.Add(c.b); }
            Object.DestroyImmediate(t);
            r.Sort(); g.Sort(); b.Sort(); int m = r.Count / 2;
            return new Color(r[m] / 255f, g[m] / 255f, b[m] / 255f, 1f);
        }

        static Material Lit(string name, Color col, Texture tex = null, float tile = 1f, float smooth = .15f, float metal = 0f, int mode = 0, string folder = "Materials")
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name, enableInstancing = true };
            m.SetColor("_BaseColor", col);
            if (tex) { m.SetTexture("_BaseMap", tex); m.SetTextureScale("_BaseMap", Vector2.one / tile); }
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
            AssetDatabase.CreateAsset(m, Built + "/" + folder + "/" + Safe(name) + ".mat");
            return m;
        }

        // ================================================================== facade kit
        static readonly Dictionary<string, Material> KitM = new();
        static readonly Dictionary<string, GameObject> Kit = new();
        static readonly Dictionary<string, Material> Accents = new();

        static void KitMaterials()
        {
            Material K(string name, Color c, Texture t = null, float tile = 1f, float smooth = .15f, float metal = 0f) => KitM[name] = Lit("TT_" + name, c, t, tile, smooth, metal, 0, "Materials/Kit");
            K("FK_Concrete", Color.white, Surfs["concrete"].Tex, 4f);
            K("FK_Concrete_Dark", new Color(.66f, .66f, .64f), Surfs["concrete"].Tex, 4f);
            K("FK_Brick", Color.white, Surfs["brick"].Tex, 3f);
            K("FK_Stone", X("D2C9B7"));
            K("FK_Wood", Color.white, Surfs["boards"].Tex, 3f);
            K("FK_Wood_Paint", X("E3DCCB"));
            K("FK_Metal_Dark", X("3E4446"), null, 1f, .35f, .3f);
            K("FK_Metal_Paint", X("6A786F"), null, 1f, .3f, .2f);
            K("FK_Metal_Galv", X("A3A8A6"), null, 1f, .45f, .45f);
            K("FK_Glass", X("3E4B55"), null, 1f, .88f);
            K("FK_Window_Frame", X("E6E2D8"), null, 1f, .3f);
            K("FK_Fabric", Color.white, Tex(Gpt + "Fabric_red.png", TextureWrapMode.Repeat, TextureWrapMode.Repeat, false), 1.2f);
            K("FK_Plastic", X("56705C"), null, 1f, .3f);
            K("FK_Roof_Metal", Color.white, Surfs["roof_sheet"].Tex, 3f, .25f, .2f);
            K("FK_Roof_Tile", Color.white, Surfs["roof_tile"].Tex, 3f);
            KitM["FK_Roof_Slate"] = Surfs["slate_wavy"].M;                                     // reuse: the wavy slate roof sheet itself
            foreach (string f in new[] { "blue", "green" })
                Accents["FK_Fabric_" + f] = Lit("TT_FK_Fabric_" + f, Color.white, Tex(Gpt + "Fabric_" + f + ".png", TextureWrapMode.Repeat, TextureWrapMode.Repeat, false), 1.2f, .15f, 0f, 0, "Materials/Kit");
            Accents["FK_Fabric_red"] = KitM["FK_Fabric"];
        }

        // per-instance colour of a flat kit material (shutters, frames, doors, railings, cornices): one cached material per colour
        static Material Accent(string kitKey, string hex)
        {
            string k = kitKey + "_" + hex;
            if (Accents.TryGetValue(k, out var m)) return m;
            var b = KitM[kitKey];
            return Accents[k] = Lit("TT_" + k, X(hex), b.GetTexture("_BaseMap"), b.GetTexture("_BaseMap") ? 1f / b.GetTextureScale("_BaseMap").x : 1f,
                b.GetFloat("_Smoothness"), b.GetFloat("_Metallic"), 0, "Materials/Kit");
        }

        static void ImportKit()
        {
            if (!Directory.Exists(KitSrc)) { Note("facade kit missing: " + KitSrc); return; }
            foreach (string f in Directory.GetFiles(KitSrc, "*.fbx"))
            {
                if (new FileInfo(f).Length < 1024) { Note("kit file is an LFS pointer: " + f); continue; }
                string dst = Built + "/Kit/" + Path.GetFileName(f);
                File.Copy(f, dst, true);
                AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceSynchronousImport);
                var mi = AssetImporter.GetAtPath(dst) as ModelImporter;
                if (mi)
                {
                    mi.globalScale = 1f; mi.importAnimation = false; mi.importCameras = false; mi.importLights = false;
                    mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                    foreach (var em in AssetDatabase.LoadAllAssetsAtPath(dst).OfType<Material>())
                        mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), em.name), KitFor(em.name));
                    mi.SaveAndReimport();
                }
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(dst);
                if (go) Kit[Path.GetFileNameWithoutExtension(f)] = go;
            }
            Note($"facade kit: {Kit.Count} pieces, {KitM.Count} kit materials");
        }

        static Material KitFor(string name) =>
            KitM.Where(kv => name.StartsWith(kv.Key)).OrderByDescending(kv => kv.Key.Length).Select(kv => kv.Value).FirstOrDefault() ?? KitM["FK_Concrete"];

        // kit piece: pivot = attach plane, +Z = out of the wall; UCX_ hulls dropped (view-only test scene); swaps = (kit material, replacement)
        static GameObject Piece(string name, Transform parent, Vector3 pos, Vector3 outward, params (string kit, Material with)[] swaps)
        {
            if (!Kit.TryGetValue(name, out var src)) { Note("kit piece missing: " + name); return null; }
            var go = Object.Instantiate(src, parent);
            go.name = name;
            go.transform.localPosition = pos;
            go.transform.localRotation = Quaternion.LookRotation(outward, Vector3.up);
            foreach (var t in go.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("UCX_")).ToList()) Object.DestroyImmediate(t.gameObject);
            if (swaps.Length > 0)
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    var mats = r.sharedMaterials;
                    for (int i = 0; i < mats.Length; i++) foreach (var s in swaps) if (s.with && mats[i] == KitM[s.kit]) mats[i] = s.with;
                    r.sharedMaterials = mats;
                }
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            return go;
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

        static void Flush(Batch b, Transform parent, string name)
        {
            foreach (var kv in b.ByKey)
            {
                var mb = kv.Value;
                if (mb.V.Count == 0) continue;
                var mesh = new Mesh { name = name + "_" + kv.Key, indexFormat = mb.V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.SetVertices(mb.V); mesh.SetUVs(0, mb.U); mesh.SetColors(mb.C); mesh.SetTriangles(mb.T, 0);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Built + "/Meshes/" + Safe(mesh.name) + ".asset");
                var go = new GameObject(mesh.name); go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = Surfs[kv.Key].M;
                if (kv.Key.StartsWith("atlas")) r.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            }
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

        static void Edge(float hx, float hz, int i, out Vector2 p0, out Vector2 p1)
        {
            switch (i)
            {
                case 0: p0 = new(-hx, -hz); p1 = new(hx, -hz); break;      // front (-Z)
                case 1: p0 = new(hx, -hz); p1 = new(hx, hz); break;        // +X
                case 2: p0 = new(hx, hz); p1 = new(-hx, hz); break;        // back (+Z)
                default: p0 = new(-hx, hz); p1 = new(-hx, -hz); break;     // -X
            }
        }

        // wall rectangle s0..s1 x y0..y1 in a wall frame, `o` metres out; UV = metres / tile from the wall start and vOrigin
        static void Wall(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, Color col, float vOrigin = 0f, float o = 0f, float uShift = 0f)
        {
            var s = Surfs[key];
            float Uu(float x) => (x + uShift) / s.TU; float Vv(float y) => (y - vOrigin) / s.TV;
            b[key].Quad(w.P(s0, y0, -o), w.P(s0, y1, -o), w.P(s1, y1, -o), w.P(s1, y0, -o),
                new(Uu(s0), Vv(y0)), new(Uu(s0), Vv(y1)), new(Uu(s1), Vv(y1)), new(Uu(s1), Vv(y0)), col);
        }

        static void Decal(Batch b, string key, Fr w, float s, float yb, Rect px, float o)
        {
            float wd = px.width / 200f, ht = px.height / 200f;           // atlas: 200 px per metre
            var uv = Rect.MinMaxRect(px.xMin / 2048f, 1f - px.yMax / 1024f, px.xMax / 2048f, 1f - px.yMin / 1024f);
            b[key].Quad(w.P(s - wd / 2, yb, -o), w.P(s - wd / 2, yb + ht, -o), w.P(s + wd / 2, yb + ht, -o), w.P(s + wd / 2, yb, -o),
                new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }

        static float Ext(Vector3 size, Vector3 a) => Mathf.Abs(a.x) * size.x + Mathf.Abs(a.y) * size.y + Mathf.Abs(a.z) * size.z;

        // axis-aligned box in frame f (centre c, size), UV = frame metres / tile (continuous across neighbouring boxes)
        static void Box(Batch b, string key, Fr f, Vector3 c, Vector3 size, Color col, bool bottom = false)
        {
            var s = Surfs[key];
            foreach (var n in new[] { Vector3.right, Vector3.left, Vector3.forward, Vector3.back, Vector3.up, Vector3.down })
            {
                if (n == Vector3.down && !bottom) continue;
                Vector3 ua = Mathf.Abs(n.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(n, ua);
                float hw = Ext(size, ra) / 2, hh = Ext(size, ua) / 2;
                Vector3 fc = c + n * Ext(size, n) / 2;
                Vector3 a = fc - ra * hw - ua * hh, bb = fc - ra * hw + ua * hh, cc = fc + ra * hw + ua * hh, d = fc + ra * hw - ua * hh;
                Vector2 Uv(Vector3 p) => new(Vector3.Dot(p, ra) / s.TU, Vector3.Dot(p, ua) / s.TV);
                b[key].Quad(f.P(a), f.P(bb), f.P(cc), f.P(d), Uv(a), Uv(bb), Uv(cc), Uv(d), col);
            }
        }

        // box on a wall: s0..s1 along, y0..y1, `depth` out of the wall (+1 cm into it)
        static void WallBox(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, float depth, Color col)
            => Box(b, key, w, new Vector3((s0 + s1) / 2, (y0 + y1) / 2, (-depth + .01f) / 2), new Vector3(s1 - s0, y1 - y0, depth + .01f), col, true);

        static void Plane(Batch b, string key, Fr f, float x0, float z0, float x1, float z1, float y, Color col)
        {
            var s = Surfs[key];
            b[key].Quad(f.P(x0, y, z0), f.P(x0, y, z1), f.P(x1, y, z1), f.P(x1, y, z0),
                new(x0 / s.TU, z0 / s.TV), new(x0 / s.TU, z1 / s.TV), new(x1 / s.TU, z1 / s.TV), new(x1 / s.TU, z0 / s.TV), col);
        }

        static Color Own(string key) => Surfs[key].Own;

        static Transform Group(Transform d, string name) { var g = new GameObject(name).transform; g.SetParent(d, false); return g; }

        // ================================================================== Hamlet (02): two houses, 7 x 6.5 m and 8 x 7 m
        sealed class HouseSpec
        {
            public Vector3 O; public float Yaw, W, D, Rh; public string Walls, Gables; public Color WallCol, GableCol;
            public string Shutter, Frame, Door; public bool KitWindows;
            public (int wall, float s)[] Windows; public (int wall, float s) DoorAt; public Vector2 Chimney; public float KitShift;
        }

        static void Hamlet(Transform d)
        {
            var f = Fr.Yaw(Vector3.zero, 0);
            var g = new Batch();
            Plane(g, "meadow", f, -50, -50, 50, 50, 0, Own("meadow"));
            Plane(g, "dirt", f, -50, -12.6f, 50, -9f, .02f, Own("dirt"));                    // street dirt road 3.6 m
            Plane(g, "dirt", f, -2.4f, -9f, 2.4f, 2.5f, .015f, Own("dirt"));                  // trodden yard path between the houses
            Flush(g, Group(d, "Ground"), "Hamlet_ground");
            // H1 approved StyleKit: house A painted boards SK 5a (house colour), house B natural logs SK 5b, 3D kit windows with shutters;
            // H2 GPT Facade_Hamlet_wood on both (windows in the texture), boards on the gables
            var variants = new (string code, string wallA, Color colA, string wallB, Color colB, string gableA, string gableB, string shA, string shB, bool kit)[]
            {
                ("H1", "boards_paint", X("8F9F76"), "logs", Own("logs"), "boards_paint", "boards", "EDE6D2", "6E8B5E", true),
                ("H2", "hamlet_wood", Own("hamlet_wood"), "hamlet_wood", Own("hamlet_wood"), "boards", "boards", "E6E1D6", "6E8B5E", false),
            };
            foreach (var v in variants)
            {
                var grp = Group(d, v.code);
                var b = new Batch();
                var gcolA = v.wallA == "boards_paint" ? v.colA : Own(v.gableA);
                var gcolB = v.wallB == "boards_paint" ? v.colB : Own(v.gableB);
                House(b, grp, new HouseSpec
                {
                    O = new Vector3(-6.5f, 0, 0), Yaw = 0, W = 7f, D = 6.5f, Rh = 2.4f, Walls = v.wallA, Gables = v.gableA, WallCol = v.colA, GableCol = gcolA,
                    Shutter = v.shA, Frame = "E8E4DA", Door = "6B4F3E", KitWindows = v.kit,
                    Windows = new[] { (0, 1.75f), (0, 5.25f), (2, 1.75f), (2, 5.25f), (3, 1.75f), (3, 5.25f) }, DoorAt = (1, 3.25f), Chimney = new Vector2(1.5f, .9f),
                });
                House(b, grp, new HouseSpec
                {
                    O = new Vector3(7f, 0, .5f), Yaw = 90, W = 8f, D = 7f, Rh = 2.6f, Walls = v.wallB, Gables = v.gableB, WallCol = v.colB, GableCol = gcolB,
                    Shutter = v.shB, Frame = "E8E4DA", Door = "5F7A6A", KitWindows = v.kit,
                    Windows = new[] { (1, 1.75f), (1, 5.25f), (0, 6.25f), (2, 1.75f), (2, 5.25f), (3, 1.75f), (3, 5.25f) }, DoorAt = (0, 3.5f), Chimney = new Vector2(-1.6f, -.8f),
                });
                Flush(b, grp, "Hamlet_" + v.code);
            }
        }

        static void House(Batch b, Transform parent, HouseSpec h)
        {
            var f = Fr.Yaw(h.O, h.Yaw);
            float hx = h.W / 2, hz = h.D / 2, E = 3.5f, R = E + h.Rh, ov = .4f;
            Fr[] walls = new Fr[4]; float[] len = new float[4];
            for (int i = 0; i < 4; i++)
            {
                Edge(hx, hz, i, out var p0, out var p1);
                walls[i] = f.Wall(p0, p1); len[i] = (p1 - p0).magnitude;
                Wall(b, h.Walls, walls[i], 0, len[i], 0, E, h.WallCol);
            }
            // gables on the +X / -X walls (ridge along local X), mapped like the wall below
            var gs = Surfs[h.Gables];
            foreach (int i in new[] { 1, 3 })
            {
                var w = walls[i]; float L = len[i];
                b[h.Gables].Tri(w.P(0, E, 0), w.P(L / 2, R, 0), w.P(L, E, 0), new(0, E / gs.TV), new(L / 2 / gs.TU, R / gs.TV), new(L / gs.TU, E / gs.TV), h.GableCol);
            }
            // plinth: concrete band 0.45 m, 4 cm proud
            Box(b, "concrete", f, new Vector3(0, .225f, 0), new Vector3(h.W + .08f, .45f, h.D + .08f), X("8C8984"));
            // roof: two slopes, wavy slate, double-sided (overhang seen from below), eave drops with the 0.4 m overhang
            var rs = Surfs["slate_wavy"];
            float e = E - ov * h.Rh / hz, HX = hx + ov, HZ = hz + ov, slope = Mathf.Sqrt(HZ * HZ + (R - e) * (R - e)) / rs.TV, along = 2 * HX / rs.TU;
            void Slope(Vector3 a, Vector3 bb, Vector3 c, Vector3 dd)
            {
                b["slate_wavy"].Quad(f.P(a), f.P(bb), f.P(c), f.P(dd), Vector2.zero, new(0, slope), new(along, slope), new(along, 0), Color.white);
                b["slate_wavy"].Quad(f.P(dd), f.P(c), f.P(bb), f.P(a), new(along, 0), new(along, slope), new(0, slope), Vector2.zero, Color.white);
            }
            Slope(new(-HX, e, -HZ), new(-HX, R, 0), new(HX, R, 0), new(HX, e, -HZ));
            Slope(new(HX, e, HZ), new(HX, R, 0), new(-HX, R, 0), new(-HX, e, HZ));
            // fascia boards along both eaves
            Box(b, "boards", f, new Vector3(0, e - .1f, -HZ + .02f), new Vector3(2 * HX, .2f, .04f), Own("boards"));
            Box(b, "boards", f, new Vector3(0, e - .1f, HZ - .02f), new Vector3(2 * HX, .2f, .04f), Own("boards"));
            // kit details
            var frameM = Accent("FK_Window_Frame", h.Frame);
            if (h.KitWindows)
                foreach (var (wi, s) in h.Windows)
                    Piece("FK_H_Window_Shutters", parent, walls[wi].P(s, 1.05f, 0), walls[wi].Out, ("FK_Wood_Paint", Accent("FK_Wood_Paint", h.Shutter)), ("FK_Window_Frame", frameM));
            {
                var (wi, s) = h.DoorAt; var w = walls[wi];
                WallBox(b, "flat", w, s - .58f, s + .58f, .5f, 2.68f, .05f, X(h.Frame));        // door frame
                WallBox(b, "flat", w, s - .48f, s + .48f, .56f, 2.6f, .08f, X(h.Door));         // door leaf
                Piece("FK_H_Steps", parent, w.P(s, 0, 0), w.Out, ("FK_Wood_Paint", Accent("FK_Wood_Paint", h.Door)));
                Piece("FK_H_PorchRoof", parent, w.P(s, 2.75f, 0), w.Out);
            }
            float yRoof = E + h.Rh * (1 - Mathf.Abs(h.Chimney.y) / hz);
            Piece("FK_H_Chimney", parent, f.P(h.Chimney.x, yRoof - .25f, h.Chimney.y), f.D(Vector3.forward));
            for (float x = -HX + 1f; x <= HX - .99f; x += 2f)
            {
                Piece("FK_G_RidgeCap_Slate_2m", parent, f.P(x, R, 0), f.D(Vector3.forward));
                Piece("FK_H_Gutter_2m", parent, f.P(x, e, -HZ), f.D(Vector3.back));
                Piece("FK_H_Gutter_2m", parent, f.P(-x, e, HZ), f.D(Vector3.forward));
            }
        }

        // ================================================================== Rough (04): khrushchevka block 8 bays x 3.2 m, 5 floors x 2.8 m
        // atlas rects (px, top-left origin) of KH_windows_atlas_v01 (gen_own_textures_v01.py: cells 400 x 500, 200 px/m)
        static readonly Rect WinWhite = Rect.MinMaxRect(60, 72, 388, 380), WinWood = Rect.MinMaxRect(460, 72, 788, 380), WinPlastic = Rect.MinMaxRect(860, 72, 1188, 380),
            WinStair = Rect.MinMaxRect(1284, 92, 1564, 330), WinKitchen = Rect.MinMaxRect(1690, 72, 1958, 380),
            Streak1 = Rect.MinMaxRect(914, 552, 1124, 872), Streak2 = Rect.MinMaxRect(1314, 532, 1494, 992), Streak3 = Rect.MinMaxRect(1664, 552, 1964, 832);

        static void Rough(Transform d)
        {
            var f = Fr.Yaw(Vector3.zero, 0);
            var g = new Batch();
            Plane(g, "worn_grass", f, -55, -55, 55, 55, 0, Own("worn_grass"));
            Plane(g, "dirt", f, -40, -11f, 40, -8.6f, .02f, Own("dirt"));                     // trodden track along the block
            foreach (float x in new[] { -4.8f, 4.8f }) Plane(g, "dirt", f, x - 1.3f, -8.6f, x + 1.3f, -6.4f, .015f, Own("dirt"));   // to the podyezds
            Flush(g, Group(d, "Ground"), "Rough_ground");
            foreach (var (code, wall) in new[] { ("R1", "KH1b"), ("R2", "KH2") })
            {
                var grp = Group(d, code);
                var b = new Batch();
                Khrushchevka(b, grp, wall, Own(wall));
                Flush(b, grp, "Rough_" + code);
            }
        }

        static void Khrushchevka(Batch b, Transform parent, string wall, Color col)
        {
            var f = Fr.Yaw(Vector3.zero, 0);
            const float hx = 12.8f, hz = 6.4f, fl0 = .5f, fh = 2.8f, top = fl0 + 5 * fh;   // 25.6 x 12.8 m, roof at 14.5 m
            var ent = new[] { 2, 5 };
            for (int i = 0; i < 4; i++)
            {
                Edge(hx, hz, i, out var p0, out var p1);
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                Wall(b, wall, w, 0, L, 0, top, col, fl0);                                   // panel seams on the floor lines (texture 4 floors x 2.8)
                bool front = i == 0, back = i == 2;
                if (front || back)
                {
                    for (int k = 0; k < 8; k++)
                    {
                        float s = 1.6f + 3.2f * k;
                        bool entrance = front && ent.Contains(k);
                        if (entrance)
                        {
                            Piece("FK_R_Entrance_Steps3", parent, w.P(s, 0, 0), w.Out, ("FK_Concrete", null));
                            Piece("FK_R_IronDoor", parent, w.P(s, .48f, 0), w.Out, ("FK_Metal_Paint", Accent("FK_Metal_Paint", k == 2 ? "5E5048" : "4F6A5E")));
                            Piece("FK_R_Entrance_Canopy", parent, w.P(s, 2.95f, 0), w.Out);
                            for (int fl = 1; fl <= 4; fl++) Decal(b, "atlas", w, s, fl0 + fl * fh + 1.4f + .85f - .09f - fh / 2 + .5f, WinStair, .025f);
                            continue;
                        }
                        bool balconies = front ? (k == 0 || k == 3 || k == 4 || k == 7) : (k == 1 || k == 6);
                        for (int fl = 0; fl < 5; fl++)
                        {
                            string id = wall + i + "_" + k + "_" + fl;
                            float yf = fl0 + fl * fh, hsh = Hash(id, 1);
                            Rect win = Hash(id, 2) < .15f && !balconies ? WinKitchen : hsh < .45f ? WinWhite : hsh < .7f ? WinWood : WinPlastic;
                            Decal(b, "atlas", w, s, yf + .85f - .09f, win, .025f);
                            if (balconies && fl > 0)
                            {
                                bool glazed = Hash(id, 3) > .45f;
                                if (glazed) Piece("FK_R_Balcony_Glazed", parent, w.P(s, yf, 0), w.Out,
                                    ("FK_Window_Frame", Accent("FK_Window_Frame", Hash(id, 4) < .5f ? "E6E2D8" : Hash(id, 4) < .8f ? "8A6A4E" : "C9C2B2")));
                                else Piece("FK_R_Balcony_Open", parent, w.P(s, yf, 0), w.Out,
                                    ("FK_Metal_Paint", Accent("FK_Metal_Paint", Hash(id, 5) < .4f ? "6A786F" : Hash(id, 5) < .7f ? "7B5E4E" : "5E6E80")));
                            }
                            else if (front && fl > 0 && Hash(id, 6) > .72f)
                                Decal(b, "atlas_blend", w, s + (Hash(id, 7) - .5f) * .4f, yf + .85f - .1f - 1.6f, Hash(id, 8) > .5f ? Streak1 : Streak3, .018f);
                        }
                        if (front && balconies && Hash(wall + k, 9) > .4f) Decal(b, "atlas_blend", w, s + .9f, fl0 + fh - 2.3f, Streak2, .018f);
                    }
                }
                // parapet along every edge (3.2 m pieces on the bay grid)
                for (float s = 1.6f; s < L; s += 3.2f) Piece("FK_R_Parapet_3m2", parent, w.P(s, top, 0), w.Out);
                if (front)
                {
                    foreach (float s in new[] { .3f, 12.8f, 25.3f })
                        for (int j = 0; j < 5; j++) Piece("FK_R_Drainpipe_2m8", parent, w.P(s, .3f + j * fh, 0), w.Out);
                    // yellow gas pipe along the facade above the canopies, with drops at both ends
                    WallBox(b, "flat", w, .8f, 24.8f, 4.04f, 4.11f, .14f, X("C4A23E"));
                    WallBox(b, "flat", w, .8f, .87f, .6f, 4.11f, .14f, X("C4A23E"));
                    WallBox(b, "flat", w, 24.73f, 24.8f, .6f, 4.11f, .14f, X("C4A23E"));
                }
            }
            Box(b, "concrete", f, new Vector3(0, .275f, 0), new Vector3(2 * hx + .08f, .55f, 2 * hz + .08f), X("77756F"));   // dark plinth
            Plane(b, "roof_flat", f, -hx, -hz, hx, hz, top, Own("roof_flat"));
            Piece("FK_R_Roof_Vent", parent, f.P(-6.4f, top, 1.5f), Vector3.forward);
            Piece("FK_R_Roof_Vent", parent, f.P(6.4f, top, 1.5f), Vector3.forward);
        }

        // ================================================================== Downtown (05): street 12 m + 2 x 5 m, 4 buildings 5-8 floors
        sealed class DtB { public string Id; public float X0, X1; public int Floors; public bool Brick, Lobby, CornerW, CornerE, AlleyW, AlleyE, Tank, FireW; public string Fabric; }

        static readonly DtB[] DtBuildings =
        {
            new() { Id = "B1", X0 = -21.75f, X1 = -11.25f, Floors = 8, CornerW = true, Fabric = "red" },
            new() { Id = "B2", X0 = -11.25f, X1 = -.75f, Floors = 6, Brick = true, Tank = true, Fabric = "green" },
            new() { Id = "B3", X0 = -.75f, X1 = 6.25f, Floors = 5, Lobby = true, AlleyE = true },
            new() { Id = "B4", X0 = 11.25f, X1 = 21.75f, Floors = 7, AlleyW = true, CornerE = true, FireW = true, Fabric = "blue" },
        };
        const float Z0 = 11f, Z1 = 25f, Gf = 4f, Fh = 3.5f, Kerb = .15f;

        sealed class DtPalette { public string[] Wall, Frame, Stone, Sign, Fabric; }

        static void Downtown(Transform d)
        {
            var f = Fr.Yaw(Vector3.zero, 0);
            var g = new Batch();
            Plane(g, "asphalt", f, -80, -6, 60, 6, 0, Own("asphalt"));                                     // main street, 12 m
            Plane(g, "asphalt", f, -38.75f, 6, -26.75f, 60, 0, Own("asphalt"));                            // cross street at the corner
            Plane(g, "asphalt", f, -38.75f, -60, -26.75f, -6, 0, Own("asphalt"));
            foreach (var (x0, z0, x1, z1) in new[] { (-26.75f, 6f, 60f, 60f), (-26.75f, -60f, 60f, -6f), (-80f, 6f, -38.75f, 60f), (-80f, -60f, -38.75f, -6f) })
                Box(g, "sidewalk", f, new Vector3((x0 + x1) / 2, Kerb / 2, (z0 + z1) / 2), new Vector3(x1 - x0, Kerb, z1 - z0), Own("sidewalk"));   // sidewalks 5 m + blocks
            Plane(g, "asphalt_old", f, 6.25f, Z0 + .3f, 11.25f, 40f, Kerb + .01f, Own("asphalt_old"));      // alley
            Flush(g, Group(d, "Ground"), "Downtown_ground");
            var calm = new DtPalette
            {
                Wall = new[] { "D8C8A4", "", "A4AF95", "C49478" }, Frame = new[] { "E7E2D6", "3F5B4C", "E7E2D6", "EDE8DC" },
                Stone = new[] { "D3CAB8", "CFC6B4", "D9D2C2", "D6CBB6" }, Sign = new[] { "3E5747", "6B3434", "", "3A4A63" }, Fabric = new[] { "red", "green", "", "blue" },
            };
            var bright = new DtPalette
            {
                Wall = new[] { "E3C47E", "A65A43", "7FAFA8", "D58F72" }, Frame = new[] { "F0ECE2", "EDE8DC", "F0ECE2", "F0ECE2" },
                Stone = new[] { "EAE2D0", "E2DACA", "E8E1D2", "EDE4D2" }, Sign = new[] { "2F6F6A", "9A3B32", "", "355C8C" }, Fabric = new[] { "green", "red", "", "blue" },
            };
            // D1 GPT facade PNGs (windows / storefront in the texture), calm palette; D2 plain stucco v01 / brick SK 3a + 3D kit
            // window frames + geometry storefronts, brighter "American" palette
            foreach (var (code, gpt, pal) in new[] { ("D1", true, calm), ("D2", false, bright) })
            {
                var grp = Group(d, code);
                var b = new Batch();
                for (int i = 0; i < DtBuildings.Length; i++) DtBuilding(b, grp, DtBuildings[i], i, gpt, pal, code);
                Flush(b, grp, "Downtown_" + code);
            }
        }

        static void DtBuilding(Batch b, Transform parent, DtB bd, int idx, bool gpt, DtPalette pal, string code)
        {
            float cx = (bd.X0 + bd.X1) / 2, cz = (Z0 + Z1) / 2, hx = (bd.X1 - bd.X0) / 2, hz = (Z1 - Z0) / 2;
            var f = Fr.Yaw(new Vector3(cx, Kerb, cz), 0);
            float top = Gf + (bd.Floors - 1) * Fh;
            Color wallCol = bd.Brick ? (pal.Wall[idx] == "" ? Own("brick") : X(pal.Wall[idx])) : X(pal.Wall[idx]);
            string plain = bd.Brick ? "brick" : "stucco_v01";
            string upperGpt = bd.Brick ? "dt_brick" : "dt_plaster";
            Color upperGptCol = bd.Brick ? Own("dt_brick") : wallCol;
            var frameM = Accent("FK_Window_Frame", pal.Frame[idx]);
            var stoneM = Accent("FK_Stone", pal.Stone[idx]);
            for (int i = 0; i < 4; i++)
            {
                Edge(hx, hz, i, out var p0, out var p1);
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                bool street = i == 0 || (i == 3 && bd.CornerW) || (i == 1 && bd.CornerE);
                bool alley = (i == 3 && bd.AlleyW) || (i == 1 && bd.AlleyE);
                int bays = Mathf.RoundToInt(L / Fh);
                float Bay(int k) => (L - bays * Fh) / 2 + Fh * (k + .5f);
                if (!street && !alley) { Wall(b, plain, w, 0, L, -Kerb, top, wallCol); continue; }   // party / back walls: plain
                // ---------------- facade surfaces
                if (gpt)
                {
                    if (street && !bd.Lobby) Wall(b, "dt_shop", w, 0, L, -Kerb, Gf, Own("dt_shop"), 0f, 0f, -(L - bays * Fh) / 2);
                    else Wall(b, street ? upperGpt : plain, w, 0, L, -Kerb, Gf, street ? upperGptCol : wallCol, Gf, 0f, -(L - bays * Fh) / 2);
                    Wall(b, upperGpt, w, 0, L, Gf, top, upperGptCol, Gf, 0f, -(L - bays * Fh) / 2);
                }
                else Wall(b, plain, w, 0, L, -Kerb, top, wallCol);
                // ---------------- upper windows (geometry variant: 3D frames; GPT variant: in the texture) + window AC units
                for (int fl = 1; fl < bd.Floors; fl++)
                {
                    float yf = Gf + (fl - 1) * Fh;
                    for (int k = 0; k < bays; k++)
                    {
                        string id = bd.Id + i + "_" + k + "_" + fl;
                        if (alley && !gpt && k % 2 == 1) continue;
                        if (!gpt) Piece("FK_D_Window_Frame", parent, w.P(Bay(k), yf + .75f, 0), w.Out, ("FK_Window_Frame", frameM), ("FK_Stone", stoneM));
                        if (Hash(id, 11) > (alley ? .62f : .82f) && !(bd.FireW && alley && Mathf.Abs(Bay(k) - (L - 4.5f)) < 2.2f))
                            Piece("FK_D_AC_Unit", parent, w.P(Bay(k), yf + .78f, 0), w.Out);
                    }
                }
                // ---------------- ground floor
                if (street)
                {
                    if (!gpt && !bd.Lobby) Storefront(b, parent, w, L, bays, bd, idx, pal);
                    if (bd.Lobby) Lobby(b, parent, w, L, gpt, pal.Frame[idx], wallCol, plain, frameM, stoneM);
                    if (bd.Fabric != null && !bd.Lobby)
                    {
                        string fab = pal.Fabric[idx] == "" ? bd.Fabric : pal.Fabric[idx];
                        for (int k = 0; k < bays; k++) Piece("FK_D_Storefront_Awning", parent, w.P(Bay(k), 3.02f, 0), w.Out, ("FK_Fabric", Accents["FK_Fabric_" + fab]));
                    }
                    // belt course (GPT FacadeTrim, 2 m repeat) between the ground floor and the upper floors
                    Box(b, "trim", w, new Vector3(L / 2, Gf + .225f, -.05f), new Vector3(L + .2f, .45f, .12f), Own("trim"));
                    for (float s = 1f; s < L - .5f; s += 2f) Piece("FK_D_Cornice_2m", parent, w.P(s, top, 0), w.Out, ("FK_Stone", stoneM));
                }
                else WallBox(b, "flat", w, L / 2 - .6f, L / 2 + .6f, -Kerb, 2.2f, .06f, X("4A4F50"));        // alley back door
                if (bd.FireW && alley) FireEscape(parent, w, L - 4.5f, bd.Floors);
                for (float s = 1f; s < L - .5f; s += 2f) Piece("FK_D_Parapet_2m", parent, w.P(s, top, 0), w.Out, ("FK_Stone", stoneM), ("FK_Brick", bd.Brick ? null : stoneM));
            }
            // parapets on the party / back walls too
            for (int i = 0; i < 4; i++)
            {
                bool street = i == 0 || (i == 3 && bd.CornerW) || (i == 1 && bd.CornerE), alley = (i == 3 && bd.AlleyW) || (i == 1 && bd.AlleyE);
                if (street || alley) continue;
                Edge(hx, hz, i, out var p0, out var p1); var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                for (float s = 1f; s < L - .5f; s += 2f) Piece("FK_D_Parapet_2m", parent, w.P(s, top, 0), w.Out, ("FK_Stone", stoneM), ("FK_Brick", bd.Brick ? null : stoneM));
            }
            Plane(b, "roof_flat", f, -hx, -hz, hx, hz, top, Own("roof_flat"));
            if (bd.Tank) Piece("FK_D_RoofWaterTank", parent, f.P(1f, top, 3.5f), Vector3.forward);
        }

        // geometry storefront: stone base, glass bays with dark frames and a mullion, a glass door in one bay, painted sign band
        static void Storefront(Batch b, Transform parent, Fr w, float L, int bays, DtB bd, int idx, DtPalette pal)
        {
            Color frame = X(idx == 1 ? "2F3A34" : "33383B"), sign = X(pal.Sign[idx]), stone = X(pal.Stone[idx]);
            WallBox(b, "stucco_v07", w, 0, L, -Kerb, .5f, .08f, stone);
            int door = bd.Id == "B4" ? 0 : bays - 1;
            for (int k = 0; k < bays; k++)
            {
                float s = (L - bays * Fh) / 2 + Fh * (k + .5f);
                WallBox(b, "glass", w, s - 1.45f, s + 1.45f, .5f, 3.0f, .03f, X("3E4B55"));
                WallBox(b, "flat", w, s - 1.55f, s - 1.43f, .5f, 3.08f, .08f, frame);
                WallBox(b, "flat", w, s + 1.43f, s + 1.55f, .5f, 3.08f, .08f, frame);
                WallBox(b, "flat", w, s - 1.55f, s + 1.55f, 2.98f, 3.08f, .08f, frame);
                WallBox(b, "flat", w, s - 1.55f, s + 1.55f, .5f, .58f, .08f, frame);
                if (k == door)
                {
                    WallBox(b, "flat", w, s - .1f, s - .04f, .5f, 3.0f, .08f, frame);              // door jamb
                    WallBox(b, "flat", w, s - .1f, s + 1.45f, 2.4f, 2.46f, .08f, frame);           // transom bar
                    WallBox(b, "flat", w, s + 1.1f, s + 1.16f, .58f, 2.4f, .1f, X("C9C2B0"));      // handle bar
                }
                else WallBox(b, "flat", w, s - .03f, s + .03f, .5f, 3.0f, .07f, frame);
            }
            WallBox(b, "flat", w, .15f, L - .15f, 3.22f, 3.86f, .1f, sign);
        }

        // residential lobby: GPT variant keeps the plaster texture (its windows) + a glass door; geometry variant: door + 2 framed windows
        static void Lobby(Batch b, Transform parent, Fr w, float L, bool gpt, string frameHex, Color wallCol, string plain, Material frameM, Material stoneM)
        {
            float s = L / 2;
            WallBox(b, "stucco_v07", w, s - .95f, s + .95f, -Kerb, 3.0f, .12f, X("CFC6B4"));        // stone surround
            WallBox(b, "glass", w, s - .62f, s + .62f, 0f, 2.55f, .14f, X("3E4B55"));
            WallBox(b, "flat", w, s - .7f, s + .7f, 2.55f, 2.65f, .16f, X(frameHex));
            WallBox(b, "flat", w, s - .04f, s + .04f, 0f, 2.55f, .16f, X(frameHex));
            if (!gpt) foreach (float x in new[] { 1.75f, L - 1.75f }) Piece("FK_D_Window_Frame", parent, w.P(x, .9f, 0), w.Out, ("FK_Window_Frame", frameM), ("FK_Stone", stoneM));
        }

        static void FireEscape(Transform parent, Fr w, float s, int floors)
        {
            for (int fl = 1; fl < floors; fl++)
            {
                float y = Gf + (fl - 1) * Fh;
                Piece("FK_D_FireEscape_Landing", parent, w.P(s, y, 0), w.Out);
                if (fl < floors - 1) Piece("FK_D_FireEscape_Stair", parent, w.P(s, y, 0), w.Out);
            }
            Piece("FK_D_FireEscape_Ladder", parent, w.P(s + 1f, Gf - 3f, 0), w.Out);
        }
    }
}
