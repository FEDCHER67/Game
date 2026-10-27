using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Hill B (between Rough and Downtown) rework on the local W86 play scene.</summary>
    static class VadimHill
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        static readonly Rect Zone = new Rect(690, 430, 460, 260);

        public static void Dump()
        {
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var td = t.terrainData;
            sb.AppendLine("terrain pos " + t.transform.position + " size " + td.size + " hres " + td.heightmapResolution + " ares " + td.alphamapResolution + " holes " + td.holesResolution);
            sb.AppendLine("layers " + string.Join(", ", td.terrainLayers.Select((l, i) => i + ":" + l.name)));
            sb.AppendLine("trees(terrain) " + td.treeInstanceCount + " detailLayers " + td.detailPrototypes.Length);
            sb.Append("grid z\\x");
            for (float x = Zone.xMin; x <= Zone.xMax; x += 20) sb.Append(" " + x.ToString("0").PadLeft(4));
            sb.AppendLine();
            for (float z = Zone.yMax; z >= Zone.yMin; z -= 15)
            {
                sb.Append(z.ToString("0").PadLeft(6));
                for (float x = Zone.xMin; x <= Zone.xMax; x += 20) sb.Append(" " + t.SampleHeight(new Vector3(x, 0, z)).ToString("0").PadLeft(4));
                sb.AppendLine();
            }
            var groups = new System.Collections.Generic.Dictionary<string, int>();
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var p = tr.position; if (!Zone.Contains(new Vector2(p.x, p.z))) continue;
                string path = tr.name; var q = tr.parent; int depth = 0;
                while (q != null && depth < 6) { path = q.name + "/" + path; q = q.parent; depth++; }
                if (Regex(tr.name)) sb.AppendLine("OBJ " + path + " pos " + p.ToString("F1") + (tr.GetComponent<MeshFilter>() ? " verts " + tr.GetComponent<MeshFilter>().sharedMesh?.vertexCount : "") + " active " + tr.gameObject.activeInHierarchy);
                var parts = path.Split('/'); var key = string.Join("/", parts.Take(Mathf.Min(3, parts.Length - 1)));
                groups.TryGetValue(key, out var n); groups[key] = n + 1;
            }
            foreach (var kv in groups.OrderByDescending(k => k.Value).Take(40)) sb.AppendLine("GROUP " + kv.Value + "  " + kv.Key);
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\hill_dump.txt", sb.ToString());
        }

        static bool Regex(string n) => System.Text.RegularExpressions.Regex.IsMatch(n, "(?i)view|serp|spur|platform|tunnel|portal|lookout|smotr|overlook|berm|Road_|bench|parapet|rail");
    }
}
