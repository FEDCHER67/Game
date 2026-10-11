// G13. Manual menu only; C# 9. Does not launch Unity or alter scene assignments.
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Art.Editor
{
    public static class StyleKitV3MaterialBuilder
    {
        private const string Kit = "Assets/OnlyVolunteers/Art/StyleKit_v3/";
        private const string Menu = "OnlyVolunteers/Art/Build Style Kit v3 Materials";

        [Serializable]
        private sealed class Manifest
        {
            public string schema;
            public int revision;
            public Entry[] entries;
        }

        [Serializable]
        private sealed class Metres
        {
            public float x;
            public float y;
        }

        [Serializable]
        private sealed class Entry
        {
            public string category;
            public string material_path;
            public Metres metres_per_tile;
            public string albedo;
            public string normal;
            public string mask;
            public bool environment_reflections;
        }

        [Serializable]
        private sealed class BuiltManifest
        {
            public string source_manifest;
            public int revision;
            public BuiltEntry[] entries;
        }

        [Serializable]
        private sealed class BuiltEntry
        {
            public string category;
            public string material_path;
            public string guid;
            public Metres metres_per_tile;
        }

        [MenuItem(Menu)]
        public static void Build()
        {
            // Select the greatest source revision, not the newest timestamp.
            var candidates = Directory.GetFiles(Kit, "materials_v3*.json")
                .Select(path => new { Path = path.Replace('\\', '/'),
                    Manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(path)) })
                .Where(x => x.Manifest != null && x.Manifest.schema == "OnlyVolunteers.StyleKitV3/1")
                .OrderByDescending(x => x.Manifest.revision).ToArray();
            if (candidates.Length == 0)
                throw new InvalidOperationException("No Style Kit v3 source manifest found.");
            var selected = candidates[0];
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
                throw new InvalidOperationException("URP Lit shader is unavailable.");

            var entries = selected.Manifest.entries;
            if (entries == null || entries.Length == 0)
                throw new InvalidOperationException("The manifest contains no texture sets.");
            var categories = new HashSet<string>(StringComparer.Ordinal);
            // Validate the entire manifest before creating any material.
            foreach (var entry in entries)
            {
                if (entry == null || string.IsNullOrWhiteSpace(entry.category) || !categories.Add(entry.category))
                    throw new InvalidOperationException("Empty or duplicate category in manifest.");
                ValidatePath(entry.material_path, "Materials/", ".mat");
                ValidatePath(entry.albedo, "Textures/", ".png");
                ValidatePath(entry.normal, "Textures/", ".png");
                ValidatePath(entry.mask, "Textures/", ".png");
                var metres = entry.metres_per_tile;
                if (metres == null || !PositiveFinite(metres.x) || !PositiveFinite(metres.y))
                    throw new InvalidOperationException("Invalid metres per tile: " + entry.category);
                foreach (var path in new[] { entry.albedo, entry.normal, entry.mask })
                    if (!File.Exists(path))
                        throw new FileNotFoundException("A manifest texture is missing.", path);
            }
            Directory.CreateDirectory(Kit + "Materials");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var built = new List<BuiltEntry>();
            foreach (var entry in entries)
            {
                var albedo = ImportTexture(entry.albedo, false, true);
                var normal = ImportTexture(entry.normal, true, false);
                var mask = ImportTexture(entry.mask, false, false);
                var materialPath = NextMaterialPath(entry.material_path);
                var material = new Material(shader) { name = Path.GetFileNameWithoutExtension(materialPath) };
                material.SetFloat("_WorkflowMode", 1f);
                material.SetTexture("_BaseMap", albedo);
                material.SetColor("_BaseColor", Color.white);
                material.SetTexture("_BumpMap", normal);
                // 50% strength is already baked into the pixels: do not halve twice.
                material.SetFloat("_BumpScale", 1f);
                material.EnableKeyword("_NORMALMAP");
                // URP Lit reads metallic from R and smoothness from A here.
                material.SetTexture("_MetallicGlossMap", mask);
                material.SetFloat("_Metallic", 1f);
                material.SetFloat("_Smoothness", 1f);
                material.SetFloat("_SmoothnessTextureChannel", 0f);
                material.EnableKeyword("_METALLICSPECGLOSSMAP");
                material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
                // The same texture supplies the occlusion G channel.
                material.SetTexture("_OcclusionMap", mask);
                material.SetFloat("_OcclusionStrength", 1f);
                material.EnableKeyword("_OCCLUSIONMAP");
                material.SetFloat("_EnvironmentReflections", entry.environment_reflections ? 1f : 0f);
                if (entry.environment_reflections)
                    material.DisableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                else
                    material.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                material.SetFloat("_SpecularHighlights", 1f);
                material.SetFloat("_Surface", 0f);
                material.SetFloat("_AlphaClip", 0f);
                material.SetFloat("_Cull", (float)CullMode.Back);
                material.SetFloat("_SrcBlend", (float)BlendMode.One);
                material.SetFloat("_DstBlend", (float)BlendMode.Zero);
                material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
                material.SetFloat("_DstBlendAlpha", (float)BlendMode.Zero);
                material.SetFloat("_ZWrite", 1f);
                material.SetFloat("_ReceiveShadows", 1f);
                material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                material.DisableKeyword("_ALPHATEST_ON");
                material.SetOverrideTag("RenderType", "Opaque");
                material.renderQueue = (int)RenderQueue.Geometry;
                var tiling = new Vector2(1f / entry.metres_per_tile.x, 1f / entry.metres_per_tile.y);
                foreach (var property in new[] { "_BaseMap", "_BumpMap", "_MetallicGlossMap", "_OcclusionMap" })
                {
                    material.SetTextureScale(property, tiling);
                    material.SetTextureOffset(property, Vector2.zero);
                }
                // NextMaterialPath checks both disk and AssetDatabase before this call.
                AssetDatabase.CreateAsset(material, materialPath);
                built.Add(new BuiltEntry { category = entry.category, material_path = materialPath,
                    guid = AssetDatabase.AssetPathToGUID(materialPath), metres_per_tile = entry.metres_per_tile });
            }
            AssetDatabase.SaveAssets();
            var receiptPath = NextReceiptPath();
            var receipt = new BuiltManifest { source_manifest = selected.Path,
                revision = selected.Manifest.revision, entries = built.ToArray() };
            // CreateNew protects an existing receipt even if the menu is invoked repeatedly.
            using (var stream = new FileStream(receiptPath, FileMode.CreateNew, FileAccess.Write))
            using (var writer = new StreamWriter(stream))
                writer.Write(JsonUtility.ToJson(receipt, true));
            AssetDatabase.Refresh();
            Debug.Log($"Style Kit v3: created {built.Count} URP Lit materials. Receipt: {receiptPath}. " +
                "Texture normals are OpenGL, mask is linear RGBA. Existing materials were preserved.");
        }

        private static bool PositiveFinite(float value) => value > 0f && !float.IsInfinity(value) && !float.IsNaN(value);

        private static void ValidatePath(string path, string subfolder, string extension)
        {
            if (string.IsNullOrEmpty(path) || !path.StartsWith(Kit + subfolder, StringComparison.Ordinal) ||
                path.Contains("..") || path.Contains('\\') || !path.EndsWith(extension, StringComparison.Ordinal))
                throw new InvalidOperationException("Path is outside the permitted Style Kit v3 folder: " + path);
        }

        private static Texture2D ImportTexture(string path, bool normal, bool srgb)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
                throw new InvalidOperationException("Missing TextureImporter: " + path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.convertToNormalmap = false;
            importer.flipGreenChannel = false;
            importer.alphaSource = normal ? TextureImporterAlphaSource.None : TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Trilinear;
            importer.anisoLevel = 4;
            importer.mipmapEnabled = true;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.maxTextureSize = 1024;
            importer.isReadable = false;
            // Preserve authored channels for the review kit. Platform compression
            // can be selected by the lead after in-game acceptance.
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.SaveAndReimport();
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null || texture.width != 1024 || texture.height != 1024)
                throw new InvalidOperationException("Expected a 1024 x 1024 texture: " + path);
            return texture;
        }

        private static string NextMaterialPath(string requested)
        {
            if (!Exists(requested))
                return requested;
            var folder = Path.GetDirectoryName(requested).Replace('\\', '/');
            var stem = Path.GetFileNameWithoutExtension(requested);
            // Keep an explicit source revision when adding a build revision.
            for (var version = 2; version < 10000; version++)
            {
                var candidate = $"{folder}/{stem}_v{version:00}.mat";
                if (!Exists(candidate))
                    return candidate;
            }
            throw new InvalidOperationException("Material revision limit reached.");
        }

        private static bool Exists(string path) => File.Exists(path) || File.Exists(path + ".meta") ||
            AssetDatabase.LoadMainAssetAtPath(path) != null;

        private static string NextReceiptPath()
        {
            for (var version = 1; version < 10000; version++)
            {
                var path = $"{Kit}materials_built_v{version:00}.json";
                if (!Exists(path))
                    return path;
            }
            throw new InvalidOperationException("Receipt revision limit reached.");
        }
    }
}
#endif
