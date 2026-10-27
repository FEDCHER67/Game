using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Sky22MapI03;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Vadim 23.10 (local W86): Downtown street lamps get their own model (DowntownLamp_v01 replaces the old-town lamp
    /// visuals in Downtown), the main roads get tall highway lamps (HighwayLamp_v01, every ~35 m on one side) with night lights
    /// registered in the night system.</summary>
    static class VadimLamps
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        const string Fbx = "Assets/VadimLocal/Lamps_v86/Lamps_v86.fbx";
        const string Dir = "Assets/VadimLocal/Lamps_v86";
        static readonly string[] MainRoads = { "main_hamlet_downtown", "hamlet_to_rough", "rough_to_port", "port_road", "cornice_view_c",
            "serpentine_view_b", "tunnel_south_approach", "tunnel_north_approach", "to_quiet_valley", "rough_west_link" };

        static Material Mat(string name, Color c, float smooth, float metal, Color? emit = null)
        {
            string p = Dir + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, p); }
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (emit.HasValue) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", emit.Value); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
            EditorUtility.SetDirty(m);
            return m;
        }

        static GameObject Model(string meshName, Dictionary<string, Material> mats)
        {
            var mesh = AssetDatabase.LoadAllAssetsAtPath(Fbx).OfType<Mesh>().First(m => m.name.StartsWith(meshName));
            var go = new GameObject(meshName);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            var src = AssetDatabase.LoadAllAssetsAtPath(Fbx).OfType<GameObject>().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>())
                .First(x => x.GetComponent<MeshFilter>().sharedMesh == mesh);
            r.sharedMaterials = src.sharedMaterials.Select(m => mats.TryGetValue(m.name, out var u) ? u : m).ToArray();
            r.shadowCastingMode = ShadowCastingMode.On;
            return go;
        }

        // the arm in the imported mesh points along local +X or -X: return the sign
        static float ArmSign(Mesh m) => m.bounds.center.x >= 0 ? 1f : -1f;

        // yaw only (never roll the pole upside down): turn the arm axis to the horizontal direction dir
        static Quaternion Yaw(Vector3 arm, Vector3 dir) => Quaternion.Euler(0, Vector3.SignedAngle(arm, new Vector3(dir.x, 0, dir.z), Vector3.up), 0);

        /// <summary>Vadim 23.10: a warm steady light on every Downtown lamp + the night-city driver (windows, flicker only in Rough).</summary>
        /// <summary>Hides the highway lamps (some float or lie sideways) until they are re-placed.</summary>
        public static void HighwayOff()
        {
            var s = EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var p = GameObject.Find("VadimHighwayLamps"); if (p) p.SetActive(false);
            Debug.Log("[VadimLamps] HighwayOff " + (p ? "done" : "not found"));
            EditorSceneManager.SaveScene(s);
        }

        public static void Night()
        {
            var scene = EditorSceneManager.OpenScene(Scene);
            var night = Object.FindFirstObjectByType<SkyMapNight22I03>(FindObjectsInactive.Include);
            var so = new SerializedObject(night); var lp = so.FindProperty("lamps");
            int n = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!mf.name.StartsWith("DowntownLamp_v01") || mf.transform.Find("VadimLampLight")) continue;
                float sign = ArmSign(mf.sharedMesh);
                var lg = new GameObject("VadimLampLight").AddComponent<Light>();
                lg.transform.SetParent(mf.transform, false);
                lg.transform.localPosition = Vector3.right * sign * 1.8f + Vector3.up * 5.6f;
                lg.transform.rotation = Quaternion.Euler(90, 0, 0);
                lg.type = LightType.Spot; lg.spotAngle = 125; lg.range = 16; lg.intensity = 7; lg.color = new Color(1f, .78f, .5f);
                lg.shadows = LightShadows.None; lg.enabled = false;
                lp.arraySize++; lp.GetArrayElementAtIndex(lp.arraySize - 1).objectReferenceValue = lg; n++;
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            if (!GameObject.Find("VadimNightCity")) new GameObject("VadimNightCity").AddComponent<OnlyVolunteers.VadimLocal.VadimNightCity>();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Debug.Log("[VadimLamps] downtown lamp lights " + n + ", night city driver added");
        }

        /// <summary>Adds the night-darkness full-screen pass (Hidden/VadimNightDark) to the URP renderer used by the play scene.</summary>
        public static void NightDark()
        {
            EditorSceneManager.OpenScene(Scene);
            var fog = Object.FindFirstObjectByType<OnlyVolunteers.Map.Look.V3.DistrictFog19V05>(FindObjectsInactive.Include);
            var assets = new List<UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset>();
            if (GraphicsSettings.defaultRenderPipeline is UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset a0) assets.Add(a0);
            for (int q = 0; q < QualitySettings.names.Length; q++) if (QualitySettings.GetRenderPipelineAssetAt(q) is UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset aq) assets.Add(aq);
            if (fog && fog.pipeline) assets.Add(fog.pipeline);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/VadimNightDark.mat");
            if (!mat) { mat = new Material(Shader.Find("Hidden/VadimNightDark")); AssetDatabase.CreateAsset(mat, Dir + "/VadimNightDark.mat"); }
            int added = 0;
            foreach (var asset in assets.Distinct())
            {
                var so = new SerializedObject(asset);
                var list = so.FindProperty("m_RendererDataList");
                for (int i = 0; i < list.arraySize; i++)
                {
                    var data = list.GetArrayElementAtIndex(i).objectReferenceValue as UnityEngine.Rendering.Universal.ScriptableRendererData;
                    if (!data || data.rendererFeatures.Any(f => f && f.name == "VadimNightDark")) continue;
                    var feat = ScriptableObject.CreateInstance<UnityEngine.Rendering.Universal.FullScreenPassRendererFeature>();
                    feat.name = "VadimNightDark";
                    feat.passMaterial = mat;
                    feat.injectionPoint = UnityEngine.Rendering.Universal.FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingPostProcessing;
                    feat.fetchColorBuffer = true;
                    feat.requirements = UnityEngine.Rendering.Universal.ScriptableRenderPassInput.Depth | UnityEngine.Rendering.Universal.ScriptableRenderPassInput.Color;
                    AssetDatabase.AddObjectToAsset(feat, data);
                    data.rendererFeatures.Add(feat);
                    var dso = new SerializedObject(data);
                    var map = dso.FindProperty("m_RendererFeatureMap");
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feat, out string _, out long lid);
                    map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = lid;
                    dso.ApplyModifiedPropertiesWithoutUndo();
                    data.SetDirty(); EditorUtility.SetDirty(data);
                    added++;
                    Debug.Log("[VadimLamps] night dark pass -> " + AssetDatabase.GetAssetPath(data));
                }
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[VadimLamps] night dark features added: " + added);
        }

        public static void Apply()
        {
            AssetDatabase.ImportAsset(Fbx, ImportAssetOptions.ForceUpdate);
            var mats = new Dictionary<string, Material>
            {
                ["Lamp_DarkPaint"] = Mat("Lamp_DarkPaint", new Color(.09f, .10f, .11f), .5f, .3f),
                ["Lamp_Galvanised"] = Mat("Lamp_Galvanised", new Color(.55f, .57f, .58f), .55f, .6f),
                ["Lamp_Concrete"] = Mat("Lamp_Concrete", new Color(.66f, .65f, .62f), .1f, 0f),
                ["Lamp_Glow"] = Mat("Lamp_Glow", new Color(1f, .86f, .6f), .5f, 0f, new Color(1f, .78f, .45f) * 2.2f),
            };
            var scene = EditorSceneManager.OpenScene(Scene);
            var root = GameObject.Find("Map_W85_v02").transform;
            var night = Object.FindFirstObjectByType<SkyMapNight22I03>(FindObjectsInactive.Include);
            var newLights = new List<Light>(); var newSlots = new List<SkyMapNight22I03.Slot>();

            // ---- Downtown: new visual on the old-town lamps inside the Downtown district
            var dtBox = new Rect(0, 0, 1270, 525);
            var oldLamps = root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("lamp_oldtown") && dtBox.Contains(new Vector2(t.position.x, t.position.z))).ToList();
            int dtn = 0;
            foreach (var t in oldLamps)
            {
                var done = t.Find("DowntownLamp_v01");
                if (done)
                {   // re-run: fix the orientation only
                    var f0 = Vector3.ProjectOnPlane(t.forward, Vector3.up); if (f0.sqrMagnitude < .01f) f0 = Vector3.forward;
                    done.rotation = Yaw(Vector3.right * ArmSign(done.GetComponent<MeshFilter>().sharedMesh), f0);
                    dtn++; continue;
                }
                var rs = t.GetComponentsInChildren<MeshRenderer>(true);
                if (rs.Length == 0) continue;
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                foreach (var r in rs) r.enabled = false;
                var m = Model("DowntownLamp_v01", mats);
                m.transform.SetParent(t, false);
                float s = Mathf.Clamp(b.size.y / 5.8f, .8f, 1.25f);
                m.transform.localScale = Vector3.one * s / Mathf.Max(.001f, t.lossyScale.y);
                // arm over the street: old lamps face the street with their forward axis
                float sign = ArmSign(m.GetComponent<MeshFilter>().sharedMesh);
                var fwd = Vector3.ProjectOnPlane(t.forward, Vector3.up).normalized;
                if (fwd.sqrMagnitude < .1f) fwd = Vector3.forward;
                m.transform.rotation = Yaw(Vector3.right * sign, fwd);
                newSlots.Add(new SkyMapNight22I03.Slot { renderer = m.GetComponent<MeshRenderer>(), index = System.Array.FindIndex(m.GetComponent<MeshRenderer>().sharedMaterials, x => x.name == "Lamp_Glow") });
                dtn++;
            }

            // ---- main roads: highway lamps every ~35 m on the right-hand side, arm over the road
            var json = File.ReadAllText("Assets/OnlyVolunteers/Map/W85Build/Data/v02/roads_v85.json");
            var data = MiniJson.Parse(json) as Dictionary<string, object>;
            var oldP = root.Find("VadimHighwayLamps"); if (oldP) Object.DestroyImmediate(oldP.gameObject);
            var parent = new GameObject("VadimHighwayLamps").transform; parent.SetParent(root, false);
            int hn = 0;
            var skip = new[] { new Rect(770, -10, 520, 550), new Rect(560, 650, 480, 310) };   // Downtown, Rough have their own lamps
            foreach (var ro in (List<object>)data["roads"])
            {
                var r = (Dictionary<string, object>)ro;
                if (!MainRoads.Contains((string)r["id"])) continue;
                float w = System.Convert.ToSingle(r["width_m"]);
                var pts = ((List<object>)r["points"]).Select(p => { var a = (List<object>)p; return new Vector2(System.Convert.ToSingle(a[0]), System.Convert.ToSingle(a[1])); }).ToList();
                float travelled = 0f, next = 17f;
                for (int i = 0; i + 1 < pts.Count; i++)
                {
                    var a = pts[i]; var bb = pts[i + 1]; float L = (bb - a).magnitude; if (L < .01f) continue;
                    var d = (bb - a) / L; var right = new Vector2(d.y, -d.x);
                    while (next <= travelled + L)
                    {
                        float u = next - travelled; next += 35f;
                        var c = a + d * u; var pos2 = c + right * (w / 2 + 1.6f);
                        if (skip.Any(k => k.Contains(pos2))) continue;
                        float y = Height(pos2);
                        if (float.IsNaN(y) || y < .5f) continue;
                        var m = Model("HighwayLamp_v01", mats);
                        m.name = "HighwayLamp_" + hn;
                        m.transform.SetParent(parent, false);
                        m.transform.position = new Vector3(pos2.x, y, pos2.y);
                        float sign = ArmSign(m.GetComponent<MeshFilter>().sharedMesh);
                        m.transform.rotation = Yaw(Vector3.right * sign, new Vector3(-right.x, 0, -right.y));
                        var lg = new GameObject("Light").AddComponent<Light>();
                        lg.transform.SetParent(m.transform, false);
                        lg.transform.localPosition = Vector3.right * sign * 2.6f + Vector3.up * 8.5f;
                        lg.transform.rotation = Quaternion.Euler(90, 0, 0);
                        lg.type = LightType.Spot; lg.spotAngle = 120; lg.range = 22; lg.intensity = 6; lg.color = new Color(1f, .82f, .58f);
                        lg.shadows = LightShadows.None; lg.enabled = false;
                        newLights.Add(lg);
                        newSlots.Add(new SkyMapNight22I03.Slot { renderer = m.GetComponent<MeshRenderer>(), index = System.Array.FindIndex(m.GetComponent<MeshRenderer>().sharedMaterials, x => x.name == "Lamp_Glow") });
                        hn++;
                    }
                    travelled += L;
                }
            }
            if (night)
            {
                var so = new SerializedObject(night);
                var lp = so.FindProperty("lamps"); var sp = so.FindProperty("slots");
                foreach (var l in newLights) { lp.arraySize++; lp.GetArrayElementAtIndex(lp.arraySize - 1).objectReferenceValue = l; }
                foreach (var sl in newSlots.Where(x => x.index >= 0))
                {
                    sp.arraySize++; var e = sp.GetArrayElementAtIndex(sp.arraySize - 1);
                    e.FindPropertyRelative("renderer").objectReferenceValue = sl.renderer; e.FindPropertyRelative("index").intValue = sl.index;
                }
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Debug.Log($"[VadimLamps] downtown {dtn} replaced, highway {hn} placed, night lights {newLights.Count}, night system {(night ? "yes" : "NO")}");
        }

        static float Height(Vector2 p)
        {
            var o = new Vector3(p.x, 400, p.y);
            var hits = Physics.RaycastAll(o, Vector3.down, 800);
            if (hits.Length == 0) { var t = Terrain.activeTerrain; return t ? t.SampleHeight(new Vector3(p.x, 0, p.y)) + t.transform.position.y : float.NaN; }
            return hits.Max(h => h.point.y);
        }
    }

    /// <summary>tiny JSON reader (objects, arrays, numbers, strings, bools, null) for the roads data.</summary>
    static class MiniJson
    {
        public static object Parse(string s) { int i = 0; return Val(s, ref i); }
        static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }
        static object Val(string s, ref int i)
        {
            Ws(s, ref i);
            char c = s[i];
            if (c == '{') { i++; var d = new Dictionary<string, object>(); Ws(s, ref i); if (s[i] == '}') { i++; return d; }
                while (true) { Ws(s, ref i); var k = (string)Val(s, ref i); Ws(s, ref i); i++; d[k] = Val(s, ref i); Ws(s, ref i); if (s[i] == ',') { i++; continue; } i++; return d; } }
            if (c == '[') { i++; var l = new List<object>(); Ws(s, ref i); if (s[i] == ']') { i++; return l; }
                while (true) { l.Add(Val(s, ref i)); Ws(s, ref i); if (s[i] == ',') { i++; continue; } i++; return l; } }
            if (c == '"') { i++; var sb = new System.Text.StringBuilder(); while (s[i] != '"') { if (s[i] == '\\') { i++; sb.Append(s[i] == 'n' ? '\n' : s[i] == 'u' ? (char)System.Convert.ToInt32(s.Substring(i + 1, 4), 16) : s[i]); if (s[i] == 'u') i += 4; } else sb.Append(s[i]); i++; } i++; return sb.ToString(); }
            if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
            if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
            if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
            int st = i; while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(st, i - st), System.Globalization.CultureInfo.InvariantCulture);
        }
    }
}
