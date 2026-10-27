using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Map.W85
{
    // W86 look pass (Fedya 25.10, brief §2 "normals"): street props of the old Art/Map kit (hydrants, cars, umbrellas, bins...) and the
    // Downtown DC3 lamps/bollards are flat-shaded: every face has its own normals, so round shapes read as facets. Smoothed copies
    // are written next to the build (Generated/<ver>/SmoothNormals_v01, the source meshes stay as they are) and the play scene's
    // mesh filters point at them. A vertex normal averages the faces at its position that lie within MaxAngle of its own face, so
    // curves (8-35 degree steps) go smooth and boxes, corners and trims (90 degrees) stay hard. Rocks keep their facets (style).
    // Runs from W85PlayIntegrator (v02) and from the menu; idempotent.
    public static class W86SmoothNormalsV01
    {
        public const float MaxAngle = 35f;
        const string ArtMapMeshes = "Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/";

        [MenuItem("OnlyVolunteers/Map/W86 Smooth normals of street props (open play scene)")]
        static void Menu()
        {
            var scene = SceneManager.GetActiveScene();
            Debug.Log(Apply(scene, "v02"));
            EditorSceneManager.MarkSceneDirty(scene);
        }

        static bool Wanted(Mesh m, string path) =>
            m && m.isReadable && m.vertexCount >= 24 && m.vertexCount < 60000 &&
            (path.StartsWith(ArtMapMeshes) || (path.Contains("/Generated/") && m.name.StartsWith("DC3_") && (m.name.Contains("lamp") || m.name.Contains("bollard"))));

        public static string Apply(Scene scene, string ver)
        {
            string outDir = $"Assets/OnlyVolunteers/Map/W85Build/Generated/{ver}/SmoothNormals_v01";
            if (!AssetDatabase.IsValidFolder(outDir)) AssetDatabase.CreateFolder($"Assets/OnlyVolunteers/Map/W85Build/Generated/{ver}", "SmoothNormals_v01");
            var made = new Dictionary<Mesh, Mesh>();
            int swapped = 0, skipped = 0;
            foreach (var mf in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshFilter>(true)))
            {
                var src = mf.sharedMesh;
                if (!src) continue;
                string path = AssetDatabase.GetAssetPath(src);
                if (path.StartsWith(outDir)) continue; // already pointed at a smoothed copy
                if (!Wanted(src, path)) continue;
                if (!made.TryGetValue(src, out var dst))
                {
                    string dstPath = $"{outDir}/{src.name}_sn01.asset";
                    dst = Smooth(src, out int changedVerts);
                    if (changedVerts == 0) { made[src] = null; skipped++; continue; }
                    var old = AssetDatabase.LoadAssetAtPath<Mesh>(dstPath);
                    if (old) { EditorUtility.CopySerialized(dst, old); Object.DestroyImmediate(dst); dst = old; }
                    else AssetDatabase.CreateAsset(dst, dstPath);
                    made[src] = dst;
                }
                if (!dst) continue;
                Undo.RecordObject(mf, "smooth normals");
                mf.sharedMesh = dst;
                PrefabUtility.RecordPrefabInstancePropertyModifications(mf);
                swapped++;
            }
            AssetDatabase.SaveAssets();
            return $"smooth normals v01: {made.Values.Count(m => m)} meshes smoothed, {skipped} had no faceted curves, {swapped} mesh filters re-pointed";
        }

        static Mesh Smooth(Mesh src, out int changedVerts)
        {
            var dst = Object.Instantiate(src);
            dst.name = src.name + "_sn01";
            var v = dst.vertices; var n = dst.normals;
            var faceNormal = new Vector3[v.Length]; // each vertex's own face (flat meshes: one face per vertex)
            var faceArea = new Dictionary<int, (Vector3 n, float a)>();
            var atPos = new Dictionary<Vector3Int, List<(Vector3 n, float a)>>();
            Vector3Int Key(Vector3 p) => new(Mathf.RoundToInt(p.x * 1000f), Mathf.RoundToInt(p.y * 1000f), Mathf.RoundToInt(p.z * 1000f));
            for (int s = 0; s < dst.subMeshCount; s++)
            {
                var tri = dst.GetTriangles(s);
                for (int f = 0; f < tri.Length; f += 3)
                {
                    Vector3 c = Vector3.Cross(v[tri[f + 1]] - v[tri[f]], v[tri[f + 2]] - v[tri[f]]);
                    float a = c.magnitude; if (a < 1e-9f) continue;
                    Vector3 fnrm = c / a;
                    for (int k = 0; k < 3; k++)
                    {
                        int vi = tri[f + k];
                        faceNormal[vi] = fnrm;
                        var key = Key(v[vi]);
                        if (!atPos.TryGetValue(key, out var l)) atPos[key] = l = new List<(Vector3, float)>();
                        l.Add((fnrm, a));
                    }
                }
            }
            changedVerts = 0;
            float cos = Mathf.Cos(MaxAngle * Mathf.Deg2Rad);
            for (int i = 0; i < v.Length; i++)
            {
                if (faceNormal[i] == Vector3.zero || !atPos.TryGetValue(Key(v[i]), out var l)) continue;
                Vector3 sum = Vector3.zero;
                foreach (var (fn, a) in l) if (Vector3.Dot(fn, faceNormal[i]) >= cos) sum += fn * a;
                if (sum.sqrMagnitude < 1e-12f) continue;
                var nn = sum.normalized;
                if (Vector3.Angle(nn, n[i]) > 1f) changedVerts++;
                n[i] = nn;
            }
            dst.normals = n;
            dst.RecalculateTangents();
            return dst;
        }
    }
}
