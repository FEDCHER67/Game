using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Import settings for the map art under Art/Map (cloud-built Blender FBX and generated textures):
    // FBX baked to Unity axes in metres, no animation/cameras/lights/colliders; textures repeat-wrapped with mipmaps,
    // normal maps as Normal, masks linear, the STREET_KIT palette point-filtered and uncompressed.
    public sealed class MapArtPostprocessor : AssetPostprocessor
    {
        public const string ArtRoot = "Assets/OnlyVolunteers/Art/Map/";

        private static bool Ours(string path) => path.Replace('\\', '/').StartsWith(ArtRoot);

        private void OnPreprocessModel()
        {
            if (!Ours(assetPath)) return;
            var mi = (ModelImporter)assetImporter;
            mi.bakeAxisConversion = false; // baked axes flip the Blender front (-Y) to -Z; the prefab builder bakes the root -90 X / x100 into the mesh instead
            mi.useFileScale = true;
            mi.globalScale = 1f;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.addCollider = false;
            mi.isReadable = false;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
        }

        private void OnPreprocessTexture()
        {
            if (!Ours(assetPath)) return;
            var ti = (TextureImporter)assetImporter;
            string name = System.IO.Path.GetFileNameWithoutExtension(assetPath).ToLowerInvariant();
            ti.textureType = name.Contains("_normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = !(name.Contains("_normal") || name.Contains("_mask") || name.Contains("_roughness"));
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.mipmapEnabled = true;
            ti.filterMode = FilterMode.Bilinear;
            ti.anisoLevel = 4;
            ti.maxTextureSize = 2048;
            ti.textureCompression = TextureImporterCompression.Compressed;
            ti.isReadable = false;
            if (name == "sk_palette")
            {
                ti.filterMode = FilterMode.Point;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.anisoLevel = 0;
            }
        }
    }
}
