using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Temporary: lists everything in the W86 play scene that has no texture (flat colour / default material) or is a
    /// primitive placeholder, grouped by district and object kind.</summary>
    static class VadimAudit
    {
        /// <summary>Per object kind: count, mean vertices, share of box-like meshes (&lt;= 24 verts), material names.</summary>
        public static void W86Boxes()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var rows = new Dictionary<string, (int n, long v, int box, HashSet<string> m)>();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var t = r.transform; string district = "(other)", obj = t.name;
                for (var p = t; p != null; p = p.parent)
                {
                    if (p.parent != null && p.parent.parent == null) { district = p.name; break; }
                    obj = p.name;
                }
                obj = Regex.Replace(obj, @"[\s_\-]*[\(\d][\d\)\s_\-]*$", "");
                obj = Regex.Replace(obj, @"^(B_|Zone_|T_|XT_|XC_)?\d\d[a-z]?-", "");
                string key = district + "\t" + obj;
                if (!rows.TryGetValue(key, out var a)) a = (0, 0, 0, new HashSet<string>());
                int vc = mf.sharedMesh.vertexCount;
                a.n++; a.v += vc; if (vc <= 24) a.box++;
                foreach (var m in r.sharedMaterials) if (m) a.m.Add(m.name);
                rows[key] = a;
            }
            File.WriteAllLines(@"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_boxes.tsv", rows.OrderBy(kv => kv.Key)
                .Select(kv => kv.Key + "\t" + kv.Value.n + "\t" + (kv.Value.v / kv.Value.n) + "\t" + kv.Value.box + "\t" + string.Join(",", kv.Value.m.Take(6))));
        }

        public static void W86()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var prim = new HashSet<string> { "Cube", "Cylinder", "Sphere", "Capsule", "Plane", "Quad" };
            var rows = new Dictionary<string, int[]>();          // key -> [renderers, noTexture, defaultMat, primitive]
            var mats = new Dictionary<string, int>();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var t = r.transform; string district = "(other)";
                for (var p = t; p != null; p = p.parent)
                    if (p.parent != null && p.parent.parent == null) { district = p.name; break; }
                string kind = Regex.Replace(t.name, @"[\s_\-]*[\(\d][\d\)\s_\-]*$", "");
                kind = Regex.Replace(kind, @"^(B_|Zone_)?\d\d-", "");
                if (t.parent != null && Regex.IsMatch(t.name, "^(LOD\\d|Mesh|Body|Roof|Wall|Part|Geo)", RegexOptions.IgnoreCase))
                    kind = Regex.Replace(t.parent.name, @"[\s_\-]*[\(\d][\d\)\s_\-]*$", "") + "/" + kind;
                var mf = r.GetComponent<MeshFilter>();
                bool isPrim = mf && mf.sharedMesh && prim.Contains(mf.sharedMesh.name) && AssetDatabase.GetAssetPath(mf.sharedMesh).Contains("unity default");
                bool noTex = true, defMat = false;
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null || m.name.StartsWith("Default-Material") || m.name == "Lit") { defMat = true; continue; }
                    foreach (var prop in m.GetTexturePropertyNames())
                        if (m.GetTexture(prop) != null && !prop.Contains("Light") ) { noTex = false; break; }
                    if (noTex) { mats.TryGetValue(m.name, out var c); mats[m.name] = c + 1; }
                }
                string key = district + "\t" + kind;
                if (!rows.TryGetValue(key, out var a)) rows[key] = a = new int[4];
                a[0]++; if (noTex) a[1]++; if (defMat) a[2]++; if (isPrim) a[3]++;
            }
            var lines = new List<string> { "district\tkind\trenderers\tno_texture\tdefault_mat\tprimitive" };
            lines.AddRange(rows.Where(kv => kv.Value[1] > 0 || kv.Value[2] > 0 || kv.Value[3] > 0)
                .OrderBy(kv => kv.Key).Select(kv => kv.Key + "\t" + string.Join("\t", kv.Value)));
            File.WriteAllLines(@"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_audit.tsv", lines);
            File.WriteAllLines(@"C:\Users\chern_0eqkb03\VolunteersBuilds\W86_audit_mats.tsv",
                mats.OrderByDescending(kv => kv.Value).Select(kv => kv.Value + "\t" + kv.Key));
        }
    }
}
