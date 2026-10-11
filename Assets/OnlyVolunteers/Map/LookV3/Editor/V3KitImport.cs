using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Import settings for the style v3 building-detail kit (ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS, G12): FBX in
    // metres with the axis conversion baked (README "Bake Axis Conversion enabled"), imported normals, no animation,
    // cameras, lights or colliders, readable meshes (the facade builder merges them per building), embedded materials
    // only so the eight role slots (plaster, brick, concrete, metal_painted, metal_dark, wood, glass, roof) keep their names.
    public sealed class V3KitPostprocessor : AssetPostprocessor
    {
        public const string KitDir = "Assets/OnlyVolunteers/Art/StyleKit_v3/BuildingDetails";

        private void OnPreprocessModel()
        {
            if (!assetPath.Replace('\\', '/').StartsWith(KitDir + "/")) return;
            var mi = (ModelImporter)assetImporter;
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.bakeAxisConversion = true;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.addCollider = false;
            mi.isReadable = true;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.None;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
        }
    }

    public static class V3KitImport
    {
        public const string Source = "ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS";

        // Copies every module FBX (never over an existing file) into the kit folder and imports it.
        [MenuItem("OnlyVolunteers/Map/Style v3/Import Building Details Kit (G12)")]
        public static int Import()
        {
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string src = Path.Combine(project, Source);
            LookAssetStore.EnsureFolder(V3KitPostprocessor.KitDir);
            int copied = 0;
            foreach (string f in Directory.GetFiles(src, "*_v01.fbx"))
            {
                string dst = Path.Combine(project, V3KitPostprocessor.KitDir, Path.GetFileName(f));
                if (File.Exists(dst)) continue;
                File.Copy(f, dst);
                copied++;
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log($"[StyleV3] building details kit: {copied} FBX copied into {V3KitPostprocessor.KitDir}");
            return copied;
        }
    }
}
