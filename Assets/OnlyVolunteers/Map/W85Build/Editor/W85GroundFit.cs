using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 ground-fit check (lead brief 22.10, next to W85FloatCheck): every building footprint of the map data against the built terrain.
    // Ground range over the footprint (corners, edges every 1 m, interior grid 1 m) > 1.5 m = error (s03 rule "builder: plinth or move"),
    // > 1.0 m = warning. Run by the builder (validate step) and from the menu on the open map / play scene.
    public static class W85GroundFit
    {
        public const float Limit = 1.5f, Warn = 1.0f;

        [MenuItem("OnlyVolunteers/Map/W86 Ground-fit check (open map scene)")]
        static void Menu()
        {
            var scene = EditorSceneManager.GetActiveScene();
            var ter = Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None).FirstOrDefault(t => t.GetComponent<TerrainCollider>());
            string ver = scene.name.Contains("_v") ? scene.name.Substring(scene.name.LastIndexOf("_v") + 1) : "v02";
            string data = "Assets/OnlyVolunteers/Map/W85Build/Data/" + ver;
            if (!ter || !Directory.Exists(data)) { Debug.LogError($"[W86 ground fit] no terrain with a collider in {scene.name} or no {data}"); return; }
            string r = Run(data, ter, out int errors);
            Debug.Log("[W86 ground fit] " + r);
            if (errors > 0) Debug.LogWarning($"[W86 ground fit] {errors} building(s) over {Limit} m");
        }

        public static string Run(string dataDir, Terrain ter, out int errors)
        {
            errors = 0;
            var rows = new List<(string id, float range, float min, float max, string kind)>();
            int n = 0;
            foreach (string f in Directory.GetFiles(dataDir + "/districts", "*_v85.json").OrderBy(s => s))
            {
                var dj = MiniJson.Parse(File.ReadAllText(f)) as Dictionary<string, object>;
                string district = Path.GetFileNameWithoutExtension(f).Replace("_v85", "");
                if (dj == null || !(dj.TryGetValue("buildings", out var bo) && bo is List<object> list)) continue;
                foreach (var o in list.OfType<Dictionary<string, object>>())
                {
                    if (o.TryGetValue("disabled", out var dis) && dis is bool off && off) continue;
                    var fp = Pts(o.TryGetValue("footprint", out var fo) ? fo : null);
                    if (fp.Length < 3) continue;
                    n++;
                    float lo = float.MaxValue, hi = float.MinValue;
                    void Probe(Vector2 p) { float h = ter.SampleHeight(new Vector3(p.x, 0, p.y)) + ter.transform.position.y; lo = Mathf.Min(lo, h); hi = Mathf.Max(hi, h); }
                    for (int i = 0; i < fp.Length; i++)
                    {
                        Vector2 a = fp[i], b = fp[(i + 1) % fp.Length];
                        int k = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude));
                        for (int j = 0; j < k; j++) Probe(Vector2.Lerp(a, b, j / (float)k));
                    }
                    float x0 = fp.Min(q => q.x), x1 = fp.Max(q => q.x), z0 = fp.Min(q => q.y), z1 = fp.Max(q => q.y);
                    for (float z = z0 + .5f; z < z1; z += 1f) for (float x = x0 + .5f; x < x1; x += 1f) if (W76Atmosphere.Inside(fp, new Vector2(x, z))) Probe(new Vector2(x, z));
                    string id = o.TryGetValue("id", out var io) ? io as string : "?";
                    string kind = o.TryGetValue("kind", out var ko) ? ko as string : "";
                    if (hi - lo > Warn) rows.Add((district + "/" + id, hi - lo, lo, hi, kind));
                }
            }
            var err = rows.Where(r => r.range > Limit).OrderByDescending(r => r.range).ToList();
            var warn = rows.Where(r => r.range <= Limit).OrderByDescending(r => r.range).ToList();
            errors = err.Count;
            var sb = new StringBuilder($"ground fit: {n} building footprints of {dataDir}, {err.Count} errors (ground range > {Limit} m), {warn.Count} warnings (> {Warn} m)");
            foreach (var r in err) sb.Append($"\n  ERROR {r.id} ({r.kind}): ground {r.min:0.00}..{r.max:0.00} m, range {r.range:0.00} m");
            foreach (var r in warn.Take(12)) sb.Append($"\n  warn {r.id} ({r.kind}): range {r.range:0.00} m");
            return sb.ToString();
        }

        static Vector2[] Pts(object o)
        {
            var r = new List<Vector2>();
            if (o is List<object> l)
                foreach (var p in l)
                    if (p is List<object> xy && xy.Count >= 2) r.Add(new Vector2(System.Convert.ToSingle(xy[0], System.Globalization.CultureInfo.InvariantCulture), System.Convert.ToSingle(xy[1], System.Globalization.CultureInfo.InvariantCulture)));
            return r.ToArray();
        }
    }
}
