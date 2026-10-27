using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Look.V3;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Vadim's district look tweaks on the W86 play scene (dump / apply).</summary>
    static class VadimLook
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        const string Out = @"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_look.txt";

        static void Bright(DistrictWeather19V05 w, string id, float exp = 0.62f, float temp = 0f)
        {
            int i = System.Array.FindIndex(w.districts, d => d.id == id); if (i < 0) return;
            var d = w.districts[i];
            d.exposure = exp; d.saturation = 6; d.contrast = 3; d.temperature = temp; d.fogStart = 95; d.fogEnd = 480;
            d.fogColour = new Color(0.765f, 0.831f, 0.863f, 1);
            if (w.weather != null && i < w.weather.Length)
            {
                var x = w.weather[i];
                x.zenith = new Color(0.22f, 0.50f, 0.82f, 1); x.horizon = new Color(0.71f, 0.80f, 0.86f, 1);
                x.sunColour = new Color(1f, 0.95f, 0.86f, 1); x.sunIntensity = 1.05f; x.ambientIntensity = 0.9f; x.cloudCover = 0.3f;
            }
        }

        /// <summary>Vadim 22.10: no forest fog; Rough aura only right at the district; Construction, Downtown, Elite, Port, fields,
        /// beach bright and sunny; Hamlet sunny with a light warm Breaking Bad / Mexico tint.</summary>
        public static void Apply()
        {
            var scene = EditorSceneManager.OpenScene(Scene);
            var w = Object.FindFirstObjectByType<DistrictWeather19V05>(FindObjectsInactive.Include);
            var f = w.visibleFog;
            f.forestDensity = 0f;
            f.banks = f.banks.Where(b => !b.forest).ToArray();
            EditorUtility.SetDirty(f);
            foreach (var id in new[] { "transition", "old_town", "elite", "industrial", "fields", "beach" }) Bright(w, id);
            Bright(w, "forest", 0.55f, 0f);
            int v = System.Array.FindIndex(w.districts, d => d.id == "village");
            if (v >= 0)
            {
                var d = w.districts[v];
                d.exposure = 0.72f; d.saturation = 12; d.contrast = 5; d.temperature = 16; d.fogStart = 95; d.fogEnd = 480;
                d.fogColour = new Color(0.86f, 0.80f, 0.68f, 1);
                var x = w.weather[v];
                x.zenith = new Color(0.25f, 0.52f, 0.80f, 1); x.horizon = new Color(0.88f, 0.80f, 0.64f, 1);
                x.sunColour = new Color(1f, 0.86f, 0.66f, 1); x.sunIntensity = 1.12f; x.ambientIntensity = 0.95f; x.cloudCover = 0.2f;
            }
            int r = System.Array.FindIndex(w.districts, d => d.id == "residential");
            if (r >= 0) w.districts[r].bounds = new Vector4(700, 715, 990, 905);   // blend 60 m starts the aura right at the district edge
            EditorUtility.SetDirty(w);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Debug.Log("[VadimLook] applied");
        }

        /// <summary>Vadim 23.10: the static sea shore-foam decals (T134, incl. the outer line 5-7 m out) off; the moving shore foam
        /// comes from the water shader itself (inner band + travelling outer band in the sea material).</summary>
        public static void ShoreFoamOff()
        {
            var scene = EditorSceneManager.OpenScene(Scene);
            int n = 0;
            foreach (var t in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (t.name.StartsWith("T134_shore") && t.gameObject.activeSelf) { t.gameObject.SetActive(false); n++; }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Debug.Log("[VadimLook] shore foam groups off: " + n);
        }

        /// <summary>Lamps by district (name, source prefab/mesh, count, sample position) + day/night components.</summary>
        public static void DumpLamps()
        {
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            var groups = new System.Collections.Generic.Dictionary<string, (int n, Vector3 p, string src)>();
            foreach (var t in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!System.Text.RegularExpressions.Regex.IsMatch(t.name, "(?i)lamp|light_pole|streetlight|fonar")) continue;
                if (t.parent != null && System.Text.RegularExpressions.Regex.IsMatch(t.parent.name, "(?i)lamp")) continue;
                string root = t.root.name, dist = root;
                for (var p = t; p != null; p = p.parent) if (p.parent != null && p.parent.parent == null) { dist = root + "/" + p.name; break; }
                string kind = System.Text.RegularExpressions.Regex.Replace(t.name, @"\d+", "#");
                var src = PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject);
                var mf = t.GetComponentInChildren<MeshFilter>();
                string s = src ? AssetDatabase.GetAssetPath(src) : (mf && mf.sharedMesh ? "mesh:" + mf.sharedMesh.name + " v" + mf.sharedMesh.vertexCount : "-");
                string key = dist + " | " + kind + " | " + s;
                groups[key] = groups.TryGetValue(key, out var g) ? (g.n + 1, g.p, g.src) : (1, t.position, s);
            }
            foreach (var kv in groups.OrderBy(k => k.Key)) sb.AppendLine(kv.Value.n + "  " + kv.Key + "  @" + kv.Value.p.ToString("F0"));
            sb.AppendLine("--- day/night components");
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (mb && System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)day|night|time|sky|cycle"))
                    sb.AppendLine(mb.GetType().FullName + " on " + mb.gameObject.name + " (" + AssetDatabase.GetAssetPath(MonoScript.FromMonoBehaviour(mb)) + ")");
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_lamps.txt", sb.ToString());
        }

        public static void DumpNight()
        {
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            var nl = GameObject.Find("Map_W85_v02/NightLamps_N-R3");
            if (nl)
            {
                var types = new System.Collections.Generic.Dictionary<string, int>();
                foreach (var c in nl.GetComponentsInChildren<Component>(true)) { var k = c.GetType().Name; types[k] = types.TryGetValue(k, out var v) ? v + 1 : 1; }
                sb.AppendLine("NightLamps types: " + string.Join(", ", types.Select(kv => kv.Key + "=" + kv.Value)));
                foreach (Transform t in nl.transform) { sb.AppendLine("  child " + t.name + " @" + t.position.ToString("F0") + " comps " + string.Join(",", t.GetComponents<Component>().Select(c => c.GetType().Name))); if (sb.Length > 3000) break; }
            }
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (mb && System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)flick|lamp|night|glow|window"))
                    sb.AppendLine(mb.GetType().FullName + " on " + mb.gameObject.name);
            var night = Object.FindFirstObjectByType<OnlyVolunteers.Sky22MapI03.SkyMapNight22I03>(FindObjectsInactive.Include);
            if (night) { var so = new SerializedObject(night); sb.AppendLine("night lamps " + so.FindProperty("lamps").arraySize + " slots " + so.FindProperty("slots").arraySize);
                var sp = so.FindProperty("slots"); var names = new System.Collections.Generic.Dictionary<string, int>();
                for (int i = 0; i < sp.arraySize; i++) { var r = sp.GetArrayElementAtIndex(i).FindPropertyRelative("renderer").objectReferenceValue as Renderer; var k = r ? System.Text.RegularExpressions.Regex.Replace(r.name, @"\d+", "#") : "null"; names[k] = names.TryGetValue(k, out var v) ? v + 1 : 1; }
                sb.AppendLine("slot renderers: " + string.Join(", ", names.OrderByDescending(kv => kv.Value).Take(20).Select(kv => kv.Key + "=" + kv.Value)));
                var lp = so.FindProperty("lamps"); var ln = new System.Collections.Generic.Dictionary<string, int>();
                for (int i = 0; i < lp.arraySize; i++) { var l = lp.GetArrayElementAtIndex(i).objectReferenceValue as Light; var k = l ? (l.transform.parent ? l.transform.parent.name : "") + "/" + System.Text.RegularExpressions.Regex.Replace(l.name, @"\d+", "#") : "null"; ln[k] = ln.TryGetValue(k, out var v) ? v + 1 : 1; }
                sb.AppendLine("lamp lights: " + string.Join(", ", ln.OrderByDescending(kv => kv.Value).Take(20).Select(kv => kv.Key + "=" + kv.Value))); }
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_night.txt", sb.ToString());
        }

        public static void Dump()
        {
            EditorSceneManager.OpenScene(Scene);
            var w = Object.FindFirstObjectByType<DistrictWeather19V05>(FindObjectsInactive.Include);
            var sb = new StringBuilder();
            sb.AppendLine("weather on " + (w ? w.name : "NONE") + " blend " + (w ? w.blendMetres : 0));
            if (w)
            {
                for (int i = 0; i < w.districts.Length; i++)
                {
                    var d = w.districts[i];
                    sb.AppendLine($"{i} {d.id} mood={d.mood} b={d.bounds} pal={d.palette} exp={d.exposure} sat={d.saturation} con={d.contrast} temp={d.temperature} fog={d.fogStart}-{d.fogEnd} col={d.fogColour}");
                    if (w.weather != null && i < w.weather.Length)
                    {
                        var x = w.weather[i];
                        sb.AppendLine($"   sky zen={x.zenith} hor={x.horizon} sunCol={x.sunColour} sun={x.sunIntensity} amb={x.ambientIntensity} cloud={x.cloudCover}");
                    }
                }
                var f = w.visibleFog;
                if (f) sb.AppendLine($"fog rough={f.roughDensity} start={f.roughHazeStart} forest={f.forestDensity} ground={f.groundExtinction} banks={f.banks.Length} forestBanks={f.banks.Count(b => b.forest)}");
            }
            var root = GameObject.Find("Map_W85_v02");
            if (root) foreach (Transform c in root.transform) if (c.name.StartsWith("District_"))
            {
                var rs = c.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) continue;
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                sb.AppendLine($"{c.name} x {b.min.x:0}..{b.max.x:0} z {b.min.z:0}..{b.max.z:0}");
            }
            File.WriteAllText(Out, sb.ToString());
        }
    }
}
