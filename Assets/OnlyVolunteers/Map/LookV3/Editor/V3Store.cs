using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Where a style v3 build writes: Map/LookV3/Generated/<scene name> (meshes in one container, the terrain data), wiped
    // only when that same scene is rebuilt. Nothing under Map/Look (the v12 look keeps its materials, placeholders and
    // layers byte-identical).
    public sealed class V3Store
    {
        public const string GeneratedRoot = V3Materials.Root + "/Generated";
        public readonly string Owner, GeneratedDir;
        private readonly string container;
        private bool containerMade;
        public int MeshCount;

        public V3Store(string owner)
        {
            Owner = owner;
            GeneratedDir = $"{GeneratedRoot}/{owner}";
            container = $"{GeneratedDir}/Meshes_{owner}.asset";
        }

        public void Reset()
        {
            if (AssetDatabase.IsValidFolder(GeneratedDir)) AssetDatabase.DeleteAsset(GeneratedDir);
            LookAssetStore.EnsureFolder(GeneratedDir);
        }

        public Mesh AddMesh(Mesh mesh)
        {
            if (mesh == null) return null;
            if (!containerMade)
            {
                AssetDatabase.CreateAsset(mesh, container);
                containerMade = true;
            }
            else AssetDatabase.AddObjectToAsset(mesh, container);
            MeshCount++;
            return mesh;
        }

        public T AddAsset<T>(T asset, string fileName) where T : Object
        {
            AssetDatabase.CreateAsset(asset, $"{GeneratedDir}/{fileName}");
            return asset;
        }
    }
}
