using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Top views and an object list along the foot of hill B (Downtown and Rough edges) for the wall / sidewalk rework.</summary>
    static class VadimWallProbe
    {
        const string Out = "C:/Users/chern_0eqkb03/VolunteersBuilds/";

        public static void Heights()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = t.transform.position; var td = t.terrainData;
            var sb = new StringBuilder();
            var mt = t.materialTemplate;
            sb.AppendLine($"terrain material {(mt ? mt.name : "null")} shader {(mt ? mt.shader.name : "-")} drawInstanced {t.drawInstanced} layers: " + string.Join("; ", td.terrainLayers.Select((l, i) => $"{i} {l.name} {(l.diffuseTexture ? l.diffuseTexture.name : "-")} tile {l.tileSize} off {l.tileOffset} spec {l.specular} metal {l.metallic} smooth {l.smoothness}")));
            if (mt) { var sh = mt.shader; for (int i = 0; i < sh.GetPropertyCount(); i++) sb.Append(sh.GetPropertyName(i) + " "); sb.AppendLine(); sb.AppendLine("keywords " + string.Join(",", mt.shaderKeywords)); }
            float H(float x, float z) => t.SampleHeight(new Vector3(x, 0, z)) + tp.y;
            sb.AppendLine("rough ring south side (z 666 / 662 / 656 / 648):");
            for (float x = 680; x <= 1000; x += 10) sb.AppendLine($"x {x}: {H(x, 666):0.0} {H(x, 662):0.0} {H(x, 656):0.0} {H(x, 648):0.0}");
            sb.AppendLine("rough_to_port, 6 / 12 m to the south-west side:");
            var rp = new[] { new Vector2(999, 674), new Vector2(1007, 675), new Vector2(1035, 674), new Vector2(1048, 673), new Vector2(1062, 672), new Vector2(1076, 670), new Vector2(1091, 668), new Vector2(1106, 659), new Vector2(1121, 645), new Vector2(1136, 640), new Vector2(1149, 638), new Vector2(1168, 635), new Vector2(1186, 633) };
            for (int i = 0; i + 1 < rp.Length; i++)
            {
                var d = (rp[i + 1] - rp[i]).normalized; var r = new Vector2(d.y, -d.x);   // right of travel = south side for an eastward road
                var m = (rp[i] + rp[i + 1]) * .5f; var a6 = m + r * 6f; var a12 = m + r * 12f;
                sb.AppendLine($"{m.x:0},{m.y:0} right {r.x:0.00},{r.y:0.00}: road {H(m.x, m.y):0.0} 6m {H(a6.x, a6.y):0.0} 12m {H(a12.x, a12.y):0.0}");
            }
            sb.AppendLine("downtown edge, 1 / 4 / 10 m behind the sidewalk edge:");
            foreach (var (x, z) in new[] { (790f, 513f), (800f, 513f), (810f, 513f), (830f, 513f), (850f, 513f), (866f, 513f), (880f, 521f), (920f, 521f), (960f, 521f), (1000f, 521f), (1040f, 521f), (1080f, 521f), (1110f, 521f), (1130f, 505f), (1160f, 505f), (1190f, 505f), (1215f, 505f), (1230f, 505f) })
                sb.AppendLine($"{x},{z}: {H(x, z + 1):0.0} {H(x, z + 4):0.0} {H(x, z + 10):0.0}");
            File.WriteAllText(Out + "probe_heights.txt", sb.ToString());
        }

        /// <summary>ASCII cover map (0.5 m) of the Downtown north band: which mesh tops cover each cell.</summary>
        public static void Cover()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            const float X0 = 798f, X1 = 1240f, Z0 = 496f, Z1 = 525f, C = .5f;
            int nx = Mathf.CeilToInt((X1 - X0) / C), nz = Mathf.CeilToInt((Z1 - Z0) / C);
            var map = new char[nz, nx]; var hy = new float[nz, nx];
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++) { map[j, i] = '.'; hy[j, i] = -99f; }
            var band = new Rect(X0, Z0, X1 - X0, Z1 - Z0); var info = new StringBuilder();
            foreach (var mr in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                string n = mr.name; char ch;
                if (n.StartsWith("Sidewalk_corners")) ch = 'C'; else if (n.StartsWith("Sidewalk")) ch = 'S'; else if (n.StartsWith("Street")) ch = 'R';
                else if (n.StartsWith("Road_")) ch = 'r'; else if (n.StartsWith("Wall_")) ch = 'W'; else continue;
                var b = mr.bounds; if (!band.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                var mf = mr.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || !mf.sharedMesh.isReadable) { info.AppendLine($"unreadable {n}"); continue; }
                var m = mf.sharedMesh; var v = m.vertices; var t = m.triangles; var tr = mr.transform;
                for (int k = 0; k < v.Length; k++) v[k] = tr.TransformPoint(v[k]);
                int cnt = 0;
                for (int k = 0; k < t.Length; k += 3)
                {
                    Vector3 a0 = v[t[k]], a1 = v[t[k + 1]], a2 = v[t[k + 2]];
                    var nrm = Vector3.Cross(a1 - a0, a2 - a0); if (nrm.sqrMagnitude < 1e-8f || Mathf.Abs(nrm.normalized.y) < .6f) continue;
                    float mnx = Mathf.Min(a0.x, Mathf.Min(a1.x, a2.x)), mxx = Mathf.Max(a0.x, Mathf.Max(a1.x, a2.x)), mnz = Mathf.Min(a0.z, Mathf.Min(a1.z, a2.z)), mxz = Mathf.Max(a0.z, Mathf.Max(a1.z, a2.z));
                    if (mxx < X0 || mnx > X1 || mxz < Z0 || mnz > Z1) continue;
                    for (int j = Mathf.Max(0, (int)((mnz - Z0) / C)); j <= Mathf.Min(nz - 1, (int)((mxz - Z0) / C)); j++)
                        for (int i = Mathf.Max(0, (int)((mnx - X0) / C)); i <= Mathf.Min(nx - 1, (int)((mxx - X0) / C)); i++)
                        {
                            var q = new Vector2(X0 + (i + .5f) * C, Z0 + (j + .5f) * C);
                            if (!InTri(q, new Vector2(a0.x, a0.z), new Vector2(a1.x, a1.z), new Vector2(a2.x, a2.z))) continue;
                            float y = Mathf.Max(a0.y, Mathf.Max(a1.y, a2.y));
                            if (y > hy[j, i]) { hy[j, i] = y; map[j, i] = ch; cnt++; }
                        }
                }
                info.AppendLine($"{n} cells {cnt} mat {(mr.sharedMaterial ? mr.sharedMaterial.name : "-")}");
            }
            var sb = new StringBuilder(); sb.Append(info);
            for (float xs = X0; xs < X1; xs += 75f)
            {
                int i0 = (int)((xs - X0) / C), i1 = Mathf.Min(nx, (int)((xs + 75f - X0) / C));
                sb.AppendLine($"--- x {xs} .. {xs + 75f} (left to right, 0.5 m per char), north on top");
                for (int j = nz - 1; j >= 0; j--)
                {
                    sb.Append($"{Z0 + j * C,6:0.0} ");
                    for (int i = i0; i < i1; i++) sb.Append(map[j, i]);
                    sb.AppendLine();
                }
            }
            File.WriteAllText(Out + "probe_cover.txt", sb.ToString());
        }

        static bool InTri(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d1 = (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y), d2 = (p.x - c.x) * (b.y - c.y) - (b.x - c.x) * (p.y - c.y), d3 = (p.x - a.x) * (c.y - a.y) - (c.x - a.x) * (p.y - a.y);
            bool neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0; return !(neg && pos);
        }

        public static void Spots()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = t.transform.position;
            var sb = new StringBuilder();
            sb.AppendLine("terrain z rows 700..640 step 4, x 712..788 step 4:");
            for (float z = 700; z >= 640; z -= 4) { sb.Append($"{z}:"); for (float x = 712; x <= 788; x += 4) sb.Append($" {t.SampleHeight(new Vector3(x, 0, z)) + tp.y,4:0}"); sb.AppendLine(); }
            var rects = new[] { new Rect(1028, 500, 32, 26), new Rect(712, 640, 76, 60) };
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; var c = new Vector2(b.center.x, b.center.z);
                if (!rects.Any(q => q.Contains(c)) || b.size.x > 60 || b.size.z > 60) continue;
                string n = r.name; var tr = r.transform.parent; for (int k = 0; k < 2 && tr; k++, tr = tr.parent) n = tr.name + "/" + n;
                if (n.Contains("Lamp") || n.Contains("lamp") || n.Contains("Decal") || n.Contains("B_04")) continue;
                sb.AppendLine($"{n} c={b.center.x:0},{b.center.y:0},{b.center.z:0} s={b.size.x:0.0},{b.size.y:0.0},{b.size.z:0.0}");
            }
            File.WriteAllText(Out + "probe_spots.txt", sb.ToString());
        }

        public static void Border()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder();
            foreach (var t in Object.FindObjectsByType<Terrain>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                sb.AppendLine($"TERRAIN {t.name} active {t.gameObject.activeInHierarchy} pos {t.transform.position} size {t.terrainData.size} res {t.terrainData.heightmapResolution}");
            var rx = new System.Text.RegularExpressions.Regex("(?i)kpp|checkpoint|border|steppe|leave|barrier|booth|boom|fence_04|04-gate|guard|step|haze|backdrop|edge|horizon");
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!rx.IsMatch(tr.name)) continue;
                if (tr.parent && rx.IsMatch(tr.parent.name)) continue;
                var rs = tr.GetComponentsInChildren<Renderer>(true); Bounds bb = rs.Length > 0 ? rs[0].bounds : new Bounds(tr.position, Vector3.zero); foreach (var r in rs) bb.Encapsulate(r.bounds);
                string path = tr.name; var q = tr.parent; for (int k = 0; k < 2 && q; k++, q = q.parent) path = q.name + "/" + path;
                sb.AppendLine($"{path} active {tr.gameObject.activeInHierarchy} pos {tr.position.x:0},{tr.position.y:0},{tr.position.z:0} bounds {bb.min.x:0},{bb.min.z:0}..{bb.max.x:0},{bb.max.z:0} y{bb.min.y:0}..{bb.max.y:0} rend {rs.Length}");
            }
            var main = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = main.transform.position;
            sb.AppendLine("main terrain heights, rows z 1000..760 step 20, x 560..1100 step 30:");
            for (float z = 1000; z >= 760; z -= 20) { sb.Append($"{z}:"); for (float x = 560; x <= 1100; x += 30) sb.Append($" {main.SampleHeight(new Vector3(x, 0, z)) + tp.y,4:0}"); sb.AppendLine(); }
            var rj = File.ReadAllText("Assets/OnlyVolunteers/Map/W85Build/Data/v02/roads_v85.json");
            File.WriteAllText(Out + "probe_border.txt", sb.ToString());
        }

        public static void Tramduro()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder();
            var d = GameObject.Find("District_tramduro");
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = t.transform.position;
            if (!d) { sb.AppendLine("no District_tramduro"); }
            else foreach (Transform c in d.transform)
            {
                var rs = c.GetComponentsInChildren<Renderer>(true); Bounds b = rs.Length > 0 ? rs[0].bounds : new Bounds(c.position, Vector3.zero); foreach (var r in rs) b.Encapsulate(r.bounds);
                float g = t.SampleHeight(new Vector3(b.center.x, 0, b.center.z)) + tp.y;
                var comps = string.Join(",", c.GetComponentsInChildren<MonoBehaviour>(true).Select(m => m ? m.GetType().Name : "MISSING").Distinct());
                int missing = c.GetComponentsInChildren<Transform>(true).Sum(x => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(x.gameObject));
                sb.AppendLine($"{c.name} active {c.gameObject.activeSelf} pos {c.position.x:0.0},{c.position.y:0.0},{c.position.z:0.0} rot {c.eulerAngles.y:0} b {b.min.x:0},{b.min.z:0}..{b.max.x:0},{b.max.z:0} y {b.min.y:0.0}..{b.max.y:0.0} ground {g:0.0} rend {rs.Length} mb [{comps}] missing {missing}");
            }
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (System.Text.RegularExpressions.Regex.IsMatch(tr.name, "(?i)strike|missile|rocket|alarm|bridge") && !(tr.parent && tr.parent.name == "District_tramduro") && tr.parent && !System.Text.RegularExpressions.Regex.IsMatch(tr.parent.name, "(?i)strike|missile|rocket|alarm|bridge"))
                    sb.AppendLine($"OTHER {tr.parent.name}/{tr.name} pos {tr.position.x:0},{tr.position.y:0},{tr.position.z:0}");
            File.WriteAllText(Out + "probe_tramduro.txt", sb.ToString());
        }

        public static void Trump()
        {
            var pf = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Characters/SausageBuddy/Types_v01/Prefabs/SausageBuddy_TRAMDURO.prefab");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pf); var sb = new StringBuilder();
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) if (System.Text.RegularExpressions.Regex.IsMatch(t.name, "(?i)head|jaw|mouth|neck|right(arm|forearm|hand$|shoulder)|spine2|hips")) sb.AppendLine($"{t.name} pos {t.position} fwd {t.forward} up {t.up}");
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) { var sm = r as SkinnedMeshRenderer; sb.AppendLine($"R {r.name} {r.GetType().Name} b {r.bounds.min}..{r.bounds.max} shapes {(sm && sm.sharedMesh ? sm.sharedMesh.blendShapeCount : 0)} {(sm && sm.sharedMesh && sm.sharedMesh.blendShapeCount > 0 ? string.Join(",", Enumerable.Range(0, sm.sharedMesh.blendShapeCount).Select(i => sm.sharedMesh.GetBlendShapeName(i))) : "")}"); }
            sb.AppendLine("components: " + string.Join(",", go.GetComponentsInChildren<Component>(true).Select(c => c.GetType().Name).Distinct()));
            sb.AppendLine("root fwd " + go.transform.forward);
            File.WriteAllText(Out + "probe_trump.txt", sb.ToString());
        }

        public static void Tram2()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder(); var rx = new System.Text.RegularExpressions.Regex("(?i)statue|monument|flag|tank|helipad|XT1|speech|lectern|palace");
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!rx.IsMatch(tr.name) || tr.parent && rx.IsMatch(tr.parent.name) && !tr.name.StartsWith("10-tank")) continue;
                var rs = tr.GetComponentsInChildren<Renderer>(true); if (rs.Length == 0) continue; Bounds b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                sb.AppendLine($"{(tr.parent ? tr.parent.name : "-")}/{tr.name} act {tr.gameObject.activeInHierarchy} pos {tr.position.x:0.0},{tr.position.y:0.0},{tr.position.z:0.0} rot {tr.eulerAngles} sc {tr.lossyScale.x:0.00} b {b.min.x:0.0},{b.min.y:0.0},{b.min.z:0.0}..{b.max.x:0.0},{b.max.y:0.0},{b.max.z:0.0}");
                if (tr.name.StartsWith("10-tank1") || tr.name.Contains("flag") || tr.name.Contains("Flag"))
                    foreach (var r in rs) sb.AppendLine($"    R {r.name} parent {r.transform.parent.name} lpos {r.transform.localPosition} lrot {r.transform.localEulerAngles} b {r.bounds.min}..{r.bounds.max} mesh {(r.GetComponent<MeshFilter>()?.sharedMesh?.name)}");
            }
            File.WriteAllText(Out + "probe_tram2.txt", sb.ToString());
        }

        public static void Tank()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder();
            var tk = GameObject.Find("10-tank1");
            foreach (var mf in tk.GetComponentsInChildren<MeshFilter>(true))
            {
                var m = mf.sharedMesh; sb.AppendLine($"{mf.name} mesh {m.name} readable {m.isReadable} verts {m.vertexCount} subs {m.subMeshCount} bounds {m.bounds.min}..{m.bounds.max} local {mf.transform.localPosition} {mf.transform.localEulerAngles} {mf.transform.localScale} mats {string.Join(",", mf.GetComponent<MeshRenderer>().sharedMaterials.Select(x => x ? x.name : "-"))}");
                if (!m.isReadable) continue;
                var v = m.vertices; var up = new int[v.Length]; for (int i = 0; i < v.Length; i++) up[i] = i;
                int F(int x) { while (up[x] != x) x = up[x] = up[up[x]]; return x; }
                var w = new Dictionary<Vector3Int, int>(); for (int i = 0; i < v.Length; i++) { var k = Vector3Int.RoundToInt(v[i] * 1000f); if (w.TryGetValue(k, out int o)) up[F(i)] = F(o); else w[k] = i; }
                var t = m.triangles; for (int k = 0; k < t.Length; k += 3) { up[F(t[k + 1])] = F(t[k]); up[F(t[k + 2])] = F(t[k]); }
                var comps = new Dictionary<int, Bounds>(); for (int i = 0; i < v.Length; i++) { int r = F(i); if (comps.TryGetValue(r, out var bb)) { bb.Encapsulate(v[i]); comps[r] = bb; } else comps[r] = new Bounds(v[i], Vector3.zero); }
                foreach (var c in comps.Values.OrderByDescending(c => c.size.magnitude).Take(14)) sb.AppendLine($"   comp {c.min.x:0.00},{c.min.y:0.00},{c.min.z:0.00} .. {c.max.x:0.00},{c.max.y:0.00},{c.max.z:0.00}");
                if (mf.name.Contains("LOD0")) break;
            }
            File.WriteAllText(Out + "probe_tank.txt", sb.ToString());
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            var go = new GameObject("Cam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 2000; cam.fieldOfView = 55;
            go.transform.position = new Vector3(1570, 16, 765); go.transform.LookAt(new Vector3(1572, 7, 800));
            var rt = new RenderTexture(1000, 600, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(1000, 600, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1000, 600), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "tram_palace.png", tex.EncodeToPNG());
            go.transform.position = new Vector3(1514, 9, 742); go.transform.LookAt(new Vector3(1502, 6, 752)); cam.Render(); tex.ReadPixels(new Rect(0, 0, 1000, 600), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "tram_tank.png", tex.EncodeToPNG());
        }

        public static void TramAndDowntown()
        {
            VadimHillApply.TramduroOnly();
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("TopCam"); var cam = go.AddComponent<Camera>(); cam.orthographic = true; cam.farClipPlane = 800; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black;
            cam.orthographicSize = 215; cam.aspect = 640f / 430f; go.transform.position = new Vector3(1010, 400, 335); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            var rt = new RenderTexture(1920, 1290, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(1920, 1290, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1920, 1290), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "dt_top.png", tex.EncodeToPNG());
        }

        public static void ForestTop()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("TopCam"); var cam = go.AddComponent<Camera>(); cam.orthographic = true; cam.farClipPlane = 800; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black;
            cam.orthographicSize = 180; cam.aspect = 480f / 360f; go.transform.position = new Vector3(370, 400, 250); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            var rt = new RenderTexture(1920, 1440, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(1920, 1440, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1920, 1440), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "forest_top.png", tex.EncodeToPNG());
        }

        public static void Walls()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder();
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; string mats = string.Join(",", r.sharedMaterials.Select(m => m ? m.name + "(" + m.shader.name + ")" : "-"));
                bool far = b.max.z > 880f && b.min.x < 1150f && b.max.x > 600f;
                bool tall = b.size.y > 12f && (b.size.x > 80f || b.size.z > 80f);
                bool netty = System.Text.RegularExpressions.Regex.IsMatch(mats + r.name, "(?i)net|chain|invis|bound|wall|beam|cone|light|glass|veil|aura|fog");
                if (!(far && (tall || netty)) && !(tall && netty)) continue;
                string n = r.name; var t = r.transform.parent; for (int k = 0; k < 3 && t; k++, t = t.parent) n = t.name + "/" + n;
                sb.AppendLine($"{n} | {b.min.x:0},{b.min.y:0},{b.min.z:0}..{b.max.x:0},{b.max.y:0},{b.max.z:0} | {mats}");
            }
            File.WriteAllText(Out + "probe_walls.txt", sb.ToString());
        }

        public static void ValleyTop()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("TopCam"); var cam = go.AddComponent<Camera>(); cam.orthographic = true; cam.farClipPlane = 800; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black;
            cam.orthographicSize = 140; cam.aspect = 300f / 280f; go.transform.position = new Vector3(580, 400, 210); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            var rt = new RenderTexture(1500, 1400, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(1500, 1400, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1500, 1400), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "valley_top.png", tex.EncodeToPNG());
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var sb = new StringBuilder();
            for (float z = 300; z >= 80; z -= 20) { sb.Append($"{z}:"); for (float x = 480; x <= 720; x += 15) sb.Append($" {t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y,4:0}"); sb.AppendLine(); }
            File.WriteAllText(Out + "valley_heights.txt", sb.ToString());
        }

        public static void Valley2()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder(); var area = Rect.MinMaxRect(480, 70, 720, 330);
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; if (!area.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                string n = r.name; var t = r.transform.parent; for (int k = 0; k < 2 && t; k++, t = t.parent) n = t.name + "/" + n;
                if (n.Contains("Balcony") || n.Contains("LOD1") || n.Contains("LOD2")) continue;
                sb.AppendLine($"{n} | {b.min.x:0},{b.min.y:0},{b.min.z:0}..{b.max.x:0},{b.max.y:0},{b.max.z:0} | {(r.GetComponent<MeshFilter>()?.sharedMesh ? (r.GetComponent<MeshFilter>().sharedMesh.isReadable ? "R" : "nr") : "-")} {r.sharedMaterial?.name}");
            }
            foreach (var ps in Object.FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None)) { var p = ps.transform.position; if (area.Contains(new Vector2(p.x, p.z))) sb.AppendLine($"PS {ps.name} {p}"); }
            File.WriteAllText(Out + "probe_valley2.txt", sb.ToString());
        }

        public static void GroundCheck()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("Cam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 60; cam.clearFlags = CameraClearFlags.Skybox;
            var sb = new StringBuilder();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Road_to_quiet_valley" || r.name == "Street_05-street-N0c") sb.AppendLine($"{r.name} mat {r.sharedMaterial?.name} shader {r.sharedMaterial?.shader.name} col {(r.sharedMaterial && r.sharedMaterial.HasProperty("_BaseColor") ? r.sharedMaterial.GetColor("_BaseColor").ToString() : "-")}");
            File.WriteAllText(Out + "ground_check.txt", sb.ToString());
            go.transform.position = new Vector3(543, 10, 330); go.transform.LookAt(new Vector3(560, 4, 250)); 
            var rt = new RenderTexture(1000, 600, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(1000, 600, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1000, 600), 0, 0); tex.Apply(); File.WriteAllBytes(Out + "ground_valley.png", tex.EncodeToPNG());
        }

        public static void ValleyViews()
        {
            ValleyTop();
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("VCam2"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 60; cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(1000, 600, 24); var tex = new Texture2D(1000, 600, TextureFormat.RGB24, false);
            void Shot(string f) { cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1000, 600), 0, 0); tex.Apply(); File.WriteAllBytes(Out + f, tex.EncodeToPNG()); }
            go.transform.position = new Vector3(640, 55, 300); go.transform.LookAt(new Vector3(645, 8, 160)); Shot("valley_mountain.png");
            go.transform.position = new Vector3(770, 35, 330); go.transform.LookAt(new Vector3(720, 5, 210)); Shot("valley_plain.png");
            go.transform.position = new Vector3(720, 14, 112); go.transform.LookAt(new Vector3(630, 6, 190)); Shot("valley_beach.png");
            go.transform.position = new Vector3(520, 30, 330); go.transform.LookAt(new Vector3(545, 5, 190)); Shot("valley_floor.png");
        }


        public static void Elite()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("ECam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(1000, 700, 24); var tex = new Texture2D(1000, 700, TextureFormat.RGB24, false);
            void Shot(string f) { cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1000, 700), 0, 0); tex.Apply(); File.WriteAllBytes(Out + f, tex.EncodeToPNG()); }
            cam.orthographic = true; cam.orthographicSize = 70; cam.aspect = 1000f / 700f; go.transform.position = new Vector3(1540, 300, 280); go.transform.rotation = Quaternion.Euler(90, 0, 0); Shot("elite_top.png");
            cam.orthographic = false; cam.fieldOfView = 60; go.transform.position = new Vector3(1600, 32, 262); go.transform.LookAt(new Vector3(1525, 2, 280)); Shot("elite_view.png");
            go.transform.position = new Vector3(1527, 3.5f, 222); go.transform.LookAt(new Vector3(1530, 2, 300)); Shot("elite_ground.png");
            go.transform.position = new Vector3(1565, 18, 205); go.transform.LookAt(new Vector3(1505, 3, 240)); Shot("elite_corner.png");
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var sb = new StringBuilder();
            for (float z = 340; z >= 220; z -= 6) { sb.Append($"{z}:"); for (float x = 1480; x <= 1600; x += 6) sb.Append($" {t.SampleHeight(new Vector3(x, 0, z)) + t.transform.position.y,5:0.0}"); sb.AppendLine(); }
            var area = Rect.MinMaxRect(1480, 220, 1610, 340);
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; if (b.size.x > 300 || !area.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                string n = r.name; var tr = r.transform.parent; for (int k = 0; k < 2 && tr; k++, tr = tr.parent) n = tr.name + "/" + n;
                if (n.Contains("LOD1") || n.Contains("LOD2")) continue;
                sb.AppendLine($"{n} | {b.min.x:0.0},{b.min.y:0.0},{b.min.z:0.0}..{b.max.x:0.0},{b.max.y:0.0},{b.max.z:0.0} | {r.sharedMaterial?.name}");
            }
            File.WriteAllText(Out + "elite_probe.txt", sb.ToString());
        }

        public static void AllViews()
        {
            Elite();
            ValleyViews();
            VadimHillApply.BorderShots();
        }


        public static void EliteJunk()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            var sb = new StringBuilder(); var area = Rect.MinMaxRect(1440, 190, 1540, 330);
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; if (b.size.x > 60 || b.min.y > 8f || !area.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                string n = r.name; var tr = r.transform.parent; for (int k = 0; k < 3 && tr; k++, tr = tr.parent) n = tr.name + "/" + n;
                if (n.Contains("LOD1") || n.Contains("LOD2") || n.Contains("Pier") || n.Contains("cove-")) continue;
                sb.AppendLine($"{n} | {b.min.x:0.0},{b.min.y:0.0},{b.min.z:0.0}..{b.max.x:0.0},{b.max.y:0.0},{b.max.z:0.0} | {r.sharedMaterial?.name}");
            }
            var de = GameObject.Find("District_elite");
            var l = de ? de.transform.Find("07-cove-lounger00") : null;
            if (l) foreach (var mf in l.GetComponentsInChildren<MeshFilter>())
            {
                var m = mf.sharedMesh; if (!m || !m.isReadable) { sb.AppendLine($"lounger mesh {mf.name} not readable"); continue; }
                var v = m.vertices; var bb = m.bounds; bool alongX = bb.size.x >= bb.size.z; float lo = alongX ? bb.min.x : bb.min.z, len = alongX ? bb.size.x : bb.size.z;
                float hA = -9, hB = -9; foreach (var q in v) { float t = ((alongX ? q.x : q.z) - lo) / len; if (t < .25f) hA = Mathf.Max(hA, q.y); if (t > .75f) hB = Mathf.Max(hB, q.y); }
                sb.AppendLine($"lounger mesh {mf.name}: bounds {bb}, long axis {(alongX ? "x" : "z")}, max y low end {hA:0.00}, high end {hB:0.00}, local rot {mf.transform.localRotation.eulerAngles}, root rot {l.rotation.eulerAngles}");
            }
            foreach (var t in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))
                if (t.name.ToLower().Contains("palm") && t.parent && !t.parent.name.ToLower().Contains("palm")) sb.AppendLine($"palm obj {t.name} parent {t.parent.name} at {t.position}");
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>();
            for (int k = 0; k < ter.terrainData.treePrototypes.Length; k++) sb.AppendLine($"tree proto {k} {ter.terrainData.treePrototypes[k].prefab?.name}");
            File.WriteAllText(Out + "elite_junk.txt", sb.ToString());
        }


        /// <summary>Mountain texture options (Vadim 25.10: no chessboard look): the rock skins get each candidate, two views each.</summary>
        public static void RockOptions()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var skins = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).Where(r => r.sharedMaterial && r.sharedMaterial.name.StartsWith("W86_rock_face")).ToArray();
            var flat = skins.Select(r => r.GetComponent<MeshFilter>().sharedMesh).ToArray();
            var smooth = flat.Select(m =>
            {   // same triangles and UVs, normals averaged over every corner at the same spot: no faceted checker
                if (!m || !m.isReadable) return m; var v = m.vertices; var t = m.triangles; var acc = new Dictionary<Vector3Int, Vector3>();
                Vector3Int K(Vector3 q) => new Vector3Int(Mathf.RoundToInt(q.x * 50), Mathf.RoundToInt(q.y * 50), Mathf.RoundToInt(q.z * 50));
                for (int k = 0; k < t.Length; k += 3) { var n = Vector3.Cross(v[t[k + 1]] - v[t[k]], v[t[k + 2]] - v[t[k]]); for (int q = 0; q < 3; q++) { var key = K(v[t[k + q]]); acc[key] = (acc.TryGetValue(key, out var a) ? a : Vector3.zero) + n; } }
                var nm = Object.Instantiate(m); nm.normals = v.Select(q => acc.TryGetValue(K(q), out var a2) ? a2.normalized : Vector3.up).ToArray(); return nm;
            }).ToArray();
            Material Lit(string tex, Color col)
            {
                var m = new Material(Shader.Find("Universal Render Pipeline/Lit")); var tx = AssetDatabase.LoadAssetAtPath<Texture2D>(tex);
                if (tx) m.SetTexture("_BaseMap", tx); m.SetColor("_BaseColor", col); m.SetFloat("_Smoothness", .08f); return m;
            }
            var orig = skins.Length > 0 ? skins[0].sharedMaterial : null;
            var opts = new (string n, Material m, bool sm)[]
            {
                ("A", orig, false),
                ("B", orig, true),
                ("C", Lit("Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Textures/T2_rock_grey_albedo.png", Color.white), true),
                ("D", Lit("Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Textures/T2_rock_warm_albedo.png", Color.white), true),
                ("E", Lit("Assets/OnlyVolunteers/Map/W19Greybox/Generated/v07/W19_rock.png", Color.white), true),
                ("F", Lit("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Textures/Rock_Macro.png", new Color(.62f, .58f, .54f)), true),
            };
            var go = new GameObject("OptCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 55; cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(800, 500, 24); var tex2 = new Texture2D(800, 500, TextureFormat.RGB24, false);
            void Shot(string f) { cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex2.ReadPixels(new Rect(0, 0, 800, 500), 0, 0); tex2.Apply(); File.WriteAllBytes(Out + f, tex2.EncodeToPNG()); }
            foreach (var o in opts)
            {
                for (int k = 0; k < skins.Length; k++) { skins[k].sharedMaterial = o.m; skins[k].GetComponent<MeshFilter>().sharedMesh = o.sm ? smooth[k] : flat[k]; }
                go.transform.position = new Vector3(1585, 22, 245); go.transform.LookAt(new Vector3(1505, 12, 268)); Shot($"rockopt_{o.n}_elite.png");
                go.transform.position = new Vector3(700, 26, 175); go.transform.LookAt(new Vector3(625, 14, 215)); Shot($"rockopt_{o.n}_valley.png");
            }
        }


        /// <summary>The plain stone on the real cliffs: smooth shading, then flat facets (the low-poly look).</summary>
        public static void StoneLook()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("SLCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 55; cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(900, 560, 24); var tex = new Texture2D(900, 560, TextureFormat.RGB24, false);
            void Shot(string f) { cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 900, 560), 0, 0); tex.Apply(); File.WriteAllBytes(Out + f, tex.EncodeToPNG()); }
            void Both(string tag)
            {
                go.transform.position = new Vector3(1585, 22, 245); go.transform.LookAt(new Vector3(1505, 12, 268)); Shot($"stonelook_{tag}_elite.png");
                go.transform.position = new Vector3(700, 26, 175); go.transform.LookAt(new Vector3(625, 14, 215)); Shot($"stonelook_{tag}_valley.png");
            }
            Both("smooth"); Both("smooth");   // the first render after loading can come out dark
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.sharedMaterial || !r.sharedMaterial.name.StartsWith("W86_rock_stone")) continue;
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue;
                var m = Object.Instantiate(mf.sharedMesh); m.RecalculateNormals(); mf.sharedMesh = m;   // triangle soup: face normals = flat facets
            }
            Both("flat");
        }


        /// <summary>Several dark tints of Fedya's rock on the real cliffs (rock skins + terrain rock layer), no rebuild.</summary>
        public static void StoneTints()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var mats = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).Where(r => r.sharedMaterial && r.sharedMaterial.name.StartsWith("W86_rock_stone")).Select(r => r.sharedMaterial).Distinct().ToArray();
            var td = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>().terrainData; var tl = td.terrainLayers[7];
            var go = new GameObject("STCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 55; cam.clearFlags = CameraClearFlags.Skybox;
            var rt = new RenderTexture(800, 500, 24); var tex = new Texture2D(800, 500, TextureFormat.RGB24, false);
            void Shot(string f) { cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 800, 500), 0, 0); tex.Apply(); File.WriteAllBytes(Out + f, tex.EncodeToPNG()); }
            var tints = new (string n, Color c)[] { ("1", new Color(.92f, .94f, .98f)), ("2", new Color(.8f, .83f, .88f)), ("3", new Color(.68f, .71f, .76f)) };
            go.transform.position = new Vector3(1585, 22, 245); go.transform.LookAt(new Vector3(1505, 12, 268)); Shot("tint_warmup.png");
            foreach (var (n, c) in tints)
            {
                foreach (var m in mats) m.SetColor("_BaseColor", c);
                tl.diffuseRemapMax = new Vector4(c.r, c.g, c.b, 1f); td.terrainLayers = td.terrainLayers;
                go.transform.position = new Vector3(1585, 22, 245); go.transform.LookAt(new Vector3(1505, 12, 268)); Shot($"tint_{n}_elite.png");
                go.transform.position = new Vector3(700, 26, 175); go.transform.LookAt(new Vector3(625, 14, 215)); Shot($"tint_{n}_valley.png");
                go.transform.position = new Vector3(1556, 7, 262); go.transform.LookAt(new Vector3(1514, 5, 282)); Shot($"tint_{n}_foot.png");
            }
        }


        /// <summary>The whole map: a top view (2 px per metre) and two oblique overviews, no fog, for the "how it will look" brief.</summary>
        public static void MapOverview()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("OvCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 5000; cam.clearFlags = CameraClearFlags.Skybox;
            void Shot(int w, int h, string f) { var rt = new RenderTexture(w, h, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; var tx = new Texture2D(w, h, TextureFormat.RGB24, false); tx.ReadPixels(new Rect(0, 0, w, h), 0, 0); tx.Apply(); File.WriteAllBytes(Out + f, tx.EncodeToPNG()); }
            cam.orthographic = true; cam.orthographicSize = 475; cam.aspect = 1744f / 950f; go.transform.position = new Vector3(872, 500, 475); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(3488, 1900, "map_top_full.png"); Shot(3488, 1900, "map_top_full.png");
            cam.orthographic = false; cam.fieldOfView = 50;
            go.transform.position = new Vector3(872, 520, -420); go.transform.LookAt(new Vector3(872, 0, 520)); Shot(2400, 1350, "map_oblique_south.png");
            go.transform.position = new Vector3(1900, 480, 200); go.transform.LookAt(new Vector3(820, 0, 520)); Shot(2400, 1350, "map_oblique_east.png");
        }

        public static void Run()
        {
            EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            RenderSettings.fog = false;
            var hidden = new StringBuilder();
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (r.bounds.size.x > 300f || r.bounds.size.z > 300f || System.Text.RegularExpressions.Regex.IsMatch(r.name, "Aura|Haze|Fog|Aerial|Dome|Veil", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                { hidden.AppendLine($"{r.name} {r.bounds.size}"); r.enabled = false; }
            File.WriteAllText(Out + "probe_hidden.txt", hidden.ToString());
            var cam = new GameObject("ProbeCam").AddComponent<Camera>();
            cam.orthographic = true; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black; cam.farClipPlane = 600f; cam.nearClipPlane = .3f;
            var sun = Object.FindObjectsByType<Light>(FindObjectsSortMode.None).FirstOrDefault(l => l.type == LightType.Directional);
            if (sun) { sun.transform.rotation = Quaternion.Euler(70, 20, 0); sun.intensity = Mathf.Max(sun.intensity, 1.1f); }
            // (name, xMin, zMin, xMax, zMax) at 4 px per metre
            var views = new (string n, float x0, float z0, float x1, float z1)[]
            {
                ("dt_west", 780, 480, 960, 560), ("dt_mid", 940, 480, 1120, 560), ("dt_east", 1100, 470, 1280, 550),
                ("rough_west", 700, 640, 880, 700), ("rough_mid", 860, 640, 1040, 700), ("rough_east", 1020, 620, 1200, 700),
            };
            foreach (var v in views)
            {
                float w = v.x1 - v.x0, d = v.z1 - v.z0;
                cam.orthographicSize = d * .5f; cam.aspect = w / d;
                cam.transform.position = new Vector3((v.x0 + v.x1) * .5f, 90f, (v.z0 + v.z1) * .5f); cam.transform.rotation = Quaternion.Euler(90, 0, 0);
                int pw = Mathf.RoundToInt(w * 4), ph = Mathf.RoundToInt(d * 4);
                var rt = new RenderTexture(pw, ph, 24); cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
                var tex = new Texture2D(pw, ph, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, pw, ph), 0, 0); tex.Apply();
                File.WriteAllBytes(Out + $"probe_{v.n}.png", tex.EncodeToPNG()); RenderTexture.active = null; cam.targetTexture = null;
            }
            var sb = new StringBuilder();
            var bands = new[] { new Rect(780, 488, 480, 50), new Rect(700, 655, 500, 40) };
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var b = r.bounds; var fr = Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z);
                if (!bands.Any(bb => bb.Overlaps(fr))) continue;
                if (b.size.x > 400 || b.size.z > 400) continue;
                string path = r.name; var t = r.transform.parent; for (int k = 0; k < 3 && t; k++, t = t.parent) path = t.name + "/" + path;
                sb.AppendLine($"{path} | {b.min.x:0.0},{b.min.y:0.0},{b.min.z:0.0} .. {b.max.x:0.0},{b.max.y:0.0},{b.max.z:0.0} | col={(r.GetComponent<Collider>() ? 1 : 0)}");
            }
            File.WriteAllText(Out + "probe_foot_objects.txt", sb.ToString());
        }
    }
}
