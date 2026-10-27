using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Temporary: top-down and oblique shots of one district in an existing map scene (batch mode).</summary>
    static class VadimShots
    {
        public static void Rough()
        {
            var scene = EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity");
            var all = Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            var names = all.Where(t => t.childCount > 3 && System.Text.RegularExpressions.Regex.IsMatch(t.name, "(?i)rough|D04|district_04|неблаг"))
                           .Select(t => t.name + " path=" + Path(t) + " kids=" + t.childCount).Take(30);
            File.WriteAllLines(@"C:\Users\chern_0eqkb03\VolunteersBuilds\v19_rough_candidates.txt", names);
            var target = all.Where(t => t.childCount > 3 && System.Text.RegularExpressions.Regex.IsMatch(t.name, "(?i)rough|D04|district_04"))
                            .OrderByDescending(t => t.GetComponentsInChildren<Renderer>().Length).FirstOrDefault();
            var dump = new System.Collections.Generic.List<string>();
            var bl = GameObject.Find("MapLook_v19_StyleV3/Buildings").transform;
            foreach (Transform c in bl) dump.Add(c.name + " @" + c.position.ToString("F0"));
            File.AppendAllLines(@"C:\Users\chern_0eqkb03\VolunteersBuilds\v19_rough_candidates.txt", dump.Take(400));
            var rs = bl.Cast<Transform>().Where(c => c.name.StartsWith("B_04")).SelectMany(c => c.GetComponentsInChildren<Renderer>()).ToArray();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            File.AppendAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\v19_rough_candidates.txt", "\nTARGET B_04* renderers=" + rs.Length + " bounds " + b);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
                if (System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)fog|volume|haze|atmos|postfx|ambience")) mb.enabled = false;
            var go = new GameObject("ShotCam"); var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 5000; cam.clearFlags = CameraClearFlags.Skybox;
            float size = Mathf.Max(b.size.x, b.size.z) * 0.55f;
            cam.orthographic = true; cam.orthographicSize = size;
            go.transform.position = b.center + Vector3.up * 150; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 2048, 2048, @"C:\Users\chern_0eqkb03\Desktop\Неблагополучный_старая_сборка_v19_сверху.png");
            cam.orthographic = false; cam.fieldOfView = 50;
            go.transform.position = b.center + new Vector3(0, size * 0.55f, -size * 1.0f); go.transform.LookAt(b.center);
            Shot(cam, 2400, 1350, @"C:\Users\chern_0eqkb03\Desktop\Неблагополучный_старая_сборка_v19_сбоку.png");
        }

        public static void WholeW86()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var root = GameObject.Find("Map_W85_v02").transform;
            bool first = true; var b = new Bounds();
            foreach (Transform ch in root)
            {
                if (!ch.name.StartsWith("District_") && !ch.name.StartsWith("Roads")) continue;
                foreach (var r in ch.GetComponentsInChildren<Renderer>())
                {
                    if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
                }
            }
            b.Expand(new Vector3(80, 0, 80));
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
                if (System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)fog|volume|haze|atmos|postfx|ambience")) mb.enabled = false;
            var go = new GameObject("ShotCam"); var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 5000; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.55f, 0.75f, 0.85f);
            cam.orthographic = true; cam.orthographicSize = b.size.z * 0.5f; cam.aspect = b.size.x / b.size.z;
            float lodBias0 = QualitySettings.lodBias; QualitySettings.lodBias = 1000; QualitySettings.maximumLODLevel = 0; // restored below: Unity saves it into ProjectSettings and it leaked into game builds (low FPS)
            foreach (var lg in Object.FindObjectsByType<LODGroup>(FindObjectsSortMode.None)) lg.ForceLOD(0);
            go.transform.position = b.center + Vector3.up * 300; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            int w = 4096, h = Mathf.RoundToInt(4096 * b.size.z / b.size.x);
            Shot(cam, w, h, @"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_top.png");
            QualitySettings.lodBias = lodBias0;
        }

        public static void DowntownW85()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v01.unity");
            var d = GameObject.Find("Map_W85_v01/District_downtown").transform;
            var rs = d.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
                if (System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)fog|volume|haze|atmos|postfx|ambience")) mb.enabled = false;
            var go = new GameObject("ShotCam"); var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 5000; cam.clearFlags = CameraClearFlags.Skybox;
            float size = Mathf.Max(b.size.x, b.size.z) * 0.53f;
            cam.orthographic = true; cam.orthographicSize = size;
            go.transform.position = b.center + Vector3.up * 400; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 2400, 2400, @"C:\Users\chern_0eqkb03\Desktop\Даунтаун_сборка_Феди_W85_сверху.png");
            cam.orthographic = false; cam.fieldOfView = 50;
            go.transform.position = b.center + new Vector3(0, size * 0.55f, -size * 1.0f); go.transform.LookAt(b.center);
            Shot(cam, 2400, 1350, @"C:\Users\chern_0eqkb03\Desktop\Даунтаун_сборка_Феди_W85_сбоку.png");
        }

        /// <summary>W86 Rough district ground: terrain layer shares and flat ground meshes + top and eye-level shots.</summary>
        public static void RoughGroundW86()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var d = GameObject.Find("Map_W85_v02/District_rough").transform;
            var rs = d.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            var log = new System.Text.StringBuilder(); log.AppendLine("bounds " + b);
            foreach (var t in Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None))
            {
                var td = t.terrainData; var p = t.transform.position;
                if (p.x > b.max.x || p.z > b.max.z || p.x + td.size.x < b.min.x || p.z + td.size.z < b.min.z) continue;
                var w = new float[td.alphamapLayers];
                int res = td.alphamapResolution, n = 0;
                var all = td.GetAlphamaps(0, 0, res, res);
                for (int y = 0; y < res; y += 2) for (int x = 0; x < res; x += 2)
                {
                    float wx = p.x + (x + .5f) / res * td.size.x, wz = p.z + (y + .5f) / res * td.size.z;
                    if (wx < b.min.x || wx > b.max.x || wz < b.min.z || wz > b.max.z) continue;
                    n++; for (int l = 0; l < w.Length; l++) w[l] += all[y, x, l];
                }
                log.AppendLine("TERRAIN " + t.name + " samples " + n);
                for (int l = 0; l < w.Length; l++) if (n > 0 && w[l] / n > .01f)
                    log.AppendLine("  " + (100 * w[l] / n).ToString("0") + "%  " + td.terrainLayers[l].name + "  " + AssetDatabase.GetAssetPath(td.terrainLayers[l].diffuseTexture));
            }
            var area = new System.Collections.Generic.Dictionary<string, float>();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                var rb = r.bounds; if (!b.Contains(rb.center) || rb.size.y > 2f || rb.size.x * rb.size.z < 30f) continue;
                foreach (var m in r.sharedMaterials) if (m)
                {
                    var k = m.name + "  " + (m.mainTexture ? AssetDatabase.GetAssetPath(m.mainTexture) : "-") + "  (" + r.name + ")";
                    area.TryGetValue(k, out var a); area[k] = a + rb.size.x * rb.size.z;
                }
            }
            foreach (var kv in area.OrderByDescending(x => x.Value).Take(25)) log.AppendLine("MESH " + (int)kv.Value + " m2  " + kv.Key);
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\rough_ground.txt", log.ToString());
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            var go = new GameObject("ShotCam"); var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox;
            float size = Mathf.Max(b.size.x, b.size.z) * 0.53f;
            cam.orthographic = true; cam.orthographicSize = size;
            go.transform.position = b.center + Vector3.up * 400; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 2000, 2000, @"C:\Users\chern_0eqkb03\VolunteersBuilds\rough_ground_top.png");
            cam.orthographic = false; cam.fieldOfView = 60;
            var eyes = new[] { new Vector3(-0.15f, 0, -0.1f), new Vector3(0.2f, 0, 0.15f), new Vector3(0f, 0, -0.3f) };
            for (int i = 0; i < eyes.Length; i++)
            {
                var e = b.center + Vector3.Scale(eyes[i], b.size); e.y = 2000;
                e.y = Physics.Raycast(e, Vector3.down, out var hit, 4000) ? hit.point.y + 1.8f : b.center.y;
                go.transform.position = e; go.transform.rotation = Quaternion.Euler(14, 40 + 110 * i, 0);
                Shot(cam, 1600, 900, @"C:\Users\chern_0eqkb03\VolunteersBuilds\rough_ground_eye" + (i + 1) + ".png");
            }
        }

        static string Path(Transform t) => t.parent == null ? t.name : Path(t.parent) + "/" + t.name;

        static void Shot(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24); cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt; var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null; cam.targetTexture = null;
        }
    }
}
