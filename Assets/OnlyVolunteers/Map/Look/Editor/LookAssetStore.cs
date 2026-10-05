using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Where the look build writes: per build meshes and terrain under Map/Look/Generated/<owner>_vNN, one folder per
    // target scene and revision (wiped only when that same scene is rebuilt), shared placeholders and terrain layers
    // under Generated/Shared (overwritten in place, so their GUIDs and every scene's references survive), tinted
    // materials under Map/Look/Materials (reused across builds by name), the registry at Map/Look/MapLookRegistry.asset.
    // Never Map/Materials.
    public sealed class LookAssetStore
    {
        public const string LookRoot = "Assets/OnlyVolunteers/Map/Look";
        public const string MaterialDir = LookRoot + "/Materials";
        public const string RegistryPath = LookRoot + "/MapLookRegistry.asset";
        public const string SharedDir = LookRoot + "/Generated/Shared";

        public readonly string Revision, GeneratedDir;
        private readonly string meshContainer, sharedContainer;
        private bool meshContainerMade, sharedContainerMade;
        private readonly Dictionary<string, Mesh> sharedMeshes = new();
        private readonly Dictionary<string, GameObject> prefabs = new();
        public int MeshCount;

        // `owner` names the scene the build is for (Map_Look_v12, a greybox scene...): each owner gets its own folder.
        public LookAssetStore(string revision, string owner = null)
        {
            Revision = revision;
            string folder = string.IsNullOrEmpty(owner) ? revision : owner.Contains(revision) ? Safe(owner) : $"{Safe(owner)}_{revision}";
            GeneratedDir = $"{LookRoot}/Generated/{folder}";
            meshContainer = $"{GeneratedDir}/Meshes_{folder}.asset";
            sharedContainer = $"{SharedDir}/Placeholders.asset";
            sharedContainerMade = AssetDatabase.LoadMainAssetAtPath(sharedContainer) != null;
        }

        private static string Safe(string s)
        {
            var chars = s.ToCharArray();
            for (int i = 0; i < chars.Length; i++)
                if (!char.IsLetterOrDigit(chars[i]) && chars[i] != '_' && chars[i] != '-') chars[i] = '_';
            return new string(chars);
        }

        // Wipes this owner's generated folder only. Shared placeholders, layers and materials are overwritten in place.
        public void Reset()
        {
            if (AssetDatabase.IsValidFolder(GeneratedDir)) AssetDatabase.DeleteAsset(GeneratedDir);
            EnsureFolder(GeneratedDir);
            EnsureFolder(SharedDir);
            EnsureFolder(MaterialDir);
        }

        // Writes `asset` to `path`; when an asset of that type is already there, copies into it (same GUID) and returns it.
        public static T CreateOrReplace<T>(T asset, string path) where T : Object
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing == null)
            {
                AssetDatabase.CreateAsset(asset, path);
                return asset;
            }
            string name = existing.name;
            EditorUtility.CopySerialized(asset, existing);
            existing.name = name;
            EditorUtility.SetDirty(existing);
            if (!AssetDatabase.Contains(asset)) Object.DestroyImmediate(asset);
            return existing;
        }

        public static string EnsureFolder(string path)
        {
            path = path.Replace('\\', '/').TrimEnd('/');
            if (AssetDatabase.IsValidFolder(path)) return path;
            string parent = Path.GetDirectoryName(path)?.Replace('\\', '/');
            if (!string.IsNullOrEmpty(parent)) EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
            return path;
        }

        // Per-revision mesh (render chunk, collision) packed into one container asset.
        public Mesh AddMesh(Mesh mesh)
        {
            if (mesh == null) return null;
            if (!meshContainerMade)
            {
                AssetDatabase.CreateAsset(mesh, meshContainer);
                meshContainerMade = true;
            }
            else AssetDatabase.AddObjectToAsset(mesh, meshContainer);
            MeshCount++;
            return mesh;
        }

        // Shared placeholder mesh, stored as a sub-asset of Placeholders.asset and reused by name (same object, so
        // prefabs and scenes that point at it keep working after a rebuild).
        public Mesh SharedMesh(string key, MeshDraft draft)
        {
            if (sharedMeshes.TryGetValue(key, out Mesh m) && m != null) return m;
            m = draft.ToMesh("Placeholder_" + key.Replace('/', '_'));
            Mesh existing = null;
            if (sharedContainerMade)
                foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(sharedContainer))
                    if (o is Mesh mesh && mesh.name == m.name)
                    {
                        existing = mesh;
                        break;
                    }
            if (existing != null)
            {
                EditorUtility.CopySerialized(m, existing);
                existing.name = m.name;
                EditorUtility.SetDirty(existing);
                Object.DestroyImmediate(m);
                m = existing;
            }
            else if (!sharedContainerMade)
            {
                AssetDatabase.CreateAsset(m, sharedContainer);
                sharedContainerMade = true;
            }
            else AssetDatabase.AddObjectToAsset(m, sharedContainer);
            sharedMeshes[key] = m;
            return m;
        }

        public T AddAsset<T>(T asset, string fileName) where T : Object
        {
            string path = $"{GeneratedDir}/{fileName}";
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        // Placeholder prefab (shared): one mesh with its slot materials, plus an optional collider.
        public GameObject PlaceholderPrefab(string key, MeshDraft draft, MapLookRegistry registry, System.Action<GameObject> addCollider)
        {
            if (prefabs.TryGetValue(key, out GameObject p) && p != null) return p;
            Mesh mesh = SharedMesh(key, draft);
            var go = new GameObject("Placeholder_" + key.Replace('/', '_'));
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = Materials(draft, registry);
            addCollider?.Invoke(go);
            string path = $"{SharedDir}/{go.name}.prefab";
            p = PrefabUtility.SaveAsPrefabAsset(go, path); // an existing prefab at path keeps its GUID
            Object.DestroyImmediate(go);
            prefabs[key] = p;
            return p;
        }

        public static Material[] Materials(MeshDraft draft, MapLookRegistry registry)
        {
            var mats = new Material[draft.Slots.Count];
            for (int i = 0; i < mats.Length; i++) mats[i] = registry.Material(draft.Slots[i]);
            return mats;
        }

        // Registry hook: reuse the material asset of the same name (so scenes of other revisions keep theirs).
        public static Material PersistMaterial(Material generated, string name)
        {
            EnsureFolder(MaterialDir);
            string path = $"{MaterialDir}/{name}.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing == null)
            {
                AssetDatabase.CreateAsset(generated, path);
                return generated;
            }
            existing.shader = generated.shader;
            existing.CopyPropertiesFromMaterial(generated);
            existing.renderQueue = generated.renderQueue;
            existing.enableInstancing = generated.enableInstancing;
            EditorUtility.SetDirty(existing);
            Object.DestroyImmediate(generated);
            return existing;
        }

        public static MapLookRegistry Registry()
        {
            var reg = AssetDatabase.LoadAssetAtPath<MapLookRegistry>(RegistryPath);
            if (reg != null) return reg;
            EnsureFolder(LookRoot);
            reg = ScriptableObject.CreateInstance<MapLookRegistry>();
            MapLookRegistryEditor.AddMissingKeys(reg);
            AssetDatabase.CreateAsset(reg, RegistryPath);
            AssetDatabase.SaveAssets();
            return reg;
        }

        public void Save() => AssetDatabase.SaveAssets();
    }
}
