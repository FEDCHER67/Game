using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.EditorTools
{
    /// <summary>Bakes readable copies of the meshes the operation table uses for query-only MeshColliders (the five strap
    /// bands/buckles of TABLE-ASTRA-001 v02 and the approved v02 ABDOMEN_MASK) and lists them in the stage-1 tuning.
    /// Why: the source FBX meshes are not readable; a MeshCollider created at runtime on them works in the Editor but has
    /// no collision data in a player, so in Fedya's 2026-10-18 build no strap could be hovered or clicked. The source
    /// FBX and its import settings stay untouched.</summary>
    public static class OperationQueryMeshBaker
    {
        public const string Folder = "Assets/OnlyVolunteers/Operation/Stage1/Art/QueryMeshes_v01";
        private static readonly string[] TablePrefabs =
        {
            "Assets/OnlyVolunteers/Operation/Stage1/Prefabs/OperatingTableAstra_v02.prefab",
            "Assets/OnlyVolunteers/Operation/Stage1/Prefabs/Stage1_Table_Placeholder_v02.prefab",
        };
        private const string TuningPath = "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationStage1_v02.asset";

        [MenuItem("OnlyVolunteers/Operation/Bake Player-Safe Query Meshes (v01)")]
        public static void BakeMenu() => Debug.Log("[OPS] " + Bake());

        public static string Bake()
        {
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(TuningPath);
            if (tuning == null) return "tuning not found: " + TuningPath;
            var sources = new List<Mesh>();
            foreach (var path in TablePrefabs)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null) continue;
                foreach (var filter in prefab.GetComponentsInChildren<MeshFilter>(true))
                    if (UnderStrap(filter.transform) && filter.sharedMesh != null && !filter.sharedMesh.isReadable && !sources.Contains(filter.sharedMesh))
                        sources.Add(filter.sharedMesh);
            }
            if (tuning.abdomenModel != null)
                foreach (var filter in tuning.abdomenModel.GetComponentsInChildren<MeshFilter>(true))
                    if (filter.name == "ABDOMEN_MASK" && filter.sharedMesh != null && !filter.sharedMesh.isReadable && !sources.Contains(filter.sharedMesh))
                        sources.Add(filter.sharedMesh);
            // Round 4: readable render copies (all UVs, sub-meshes) of the seam's skin and blood, for the stitch-by-stitch closing.
            var render = new List<Mesh>();
            if (tuning.suturedModel != null)
                foreach (var filter in tuning.suturedModel.GetComponentsInChildren<MeshFilter>(true))
                    if ((filter.name == "SUTURE_SKIN" || filter.name == "SUTURE_BLOOD") && filter.sharedMesh != null && !filter.sharedMesh.isReadable && !sources.Contains(filter.sharedMesh))
                    { sources.Add(filter.sharedMesh); render.Add(filter.sharedMesh); }
            if (!AssetDatabase.IsValidFolder(Folder)) AssetDatabase.CreateFolder(Path.GetDirectoryName(Folder).Replace('\\', '/'), Path.GetFileName(Folder));
            var copies = new List<Mesh>();
            if (tuning.queryMeshes != null) foreach (var m in tuning.queryMeshes) if (m != null && !copies.Contains(m)) copies.Add(m);
            int created = 0;
            foreach (var source in sources)
            {
                string assetPath = Folder + "/" + source.name + OperationQueryMeshes.Suffix + ".asset";
                var existing = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
                // A newer source with the same mesh name (e.g. ABDOMEN_MASK of OperationAbdomen_v03) gets its own file.
                if (existing != null && existing.vertexCount != source.vertexCount)
                    assetPath = Folder + "/" + Path.GetFileNameWithoutExtension(AssetDatabase.GetAssetPath(source)) + "__" + source.name + OperationQueryMeshes.Suffix + ".asset";
                var copy = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
                if (copy == null || copy.vertexCount != source.vertexCount || !copy.isReadable)
                {
                    if (copy != null) return "existing copy differs, not overwritten: " + assetPath;
                    copy = render.Contains(source) ? CopyFull(source) : Copy(source);
                    AssetDatabase.CreateAsset(copy, assetPath);
                    created++;
                }
                if (!copies.Contains(copy)) copies.Add(copy);
            }
            tuning.queryMeshes = copies.ToArray();
            EditorUtility.SetDirty(tuning);
            AssetDatabase.SaveAssets();
            return "query meshes: " + sources.Count + " sources, " + created + " new copies, tuning lists " + copies.Count;
        }

        private static bool UnderStrap(Transform t)
        {
            for (; t != null; t = t.parent) if (t.name.StartsWith("STRAP")) return true;
            return false;
        }

        /// <summary>Round 4: a render-ready readable copy (positions, normals, tangents, UV0/UV1, colours, sub-meshes).</summary>
        private static Mesh CopyFull(Mesh source)
        {
            var copy = new Mesh { name = source.name + OperationQueryMeshes.Suffix };
            copy.indexFormat = source.indexFormat;
            copy.vertices = source.vertices;
            copy.normals = source.normals;
            if (source.tangents != null && source.tangents.Length == source.vertexCount) copy.tangents = source.tangents;
            if (source.uv != null && source.uv.Length == source.vertexCount) copy.uv = source.uv;
            if (source.uv2 != null && source.uv2.Length == source.vertexCount) copy.uv2 = source.uv2;
            if (source.colors != null && source.colors.Length == source.vertexCount) copy.colors = source.colors;
            copy.subMeshCount = source.subMeshCount;
            for (int i = 0; i < source.subMeshCount; i++) copy.SetTriangles(source.GetTriangles(i), i);
            copy.RecalculateBounds();
            return copy;
        }

        private static Mesh Copy(Mesh source)
        {
            // Editor-only read of the non-readable source; the copy stays readable (no UploadMeshData(true)).
            var copy = new Mesh { name = source.name + OperationQueryMeshes.Suffix };
            copy.indexFormat = source.indexFormat;
            copy.vertices = source.vertices;
            copy.normals = source.normals;
            var triangles = new List<int>();
            for (int i = 0; i < source.subMeshCount; i++) triangles.AddRange(source.GetTriangles(i));
            copy.SetTriangles(triangles, 0);
            copy.RecalculateBounds();
            return copy;
        }
    }
}
