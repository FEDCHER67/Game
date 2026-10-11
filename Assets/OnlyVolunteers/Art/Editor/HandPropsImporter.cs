using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Art.Editor
{
    public static class HandPropsImporter
    {
        private const string SourceDirectory = "ArtSource/Props/STYLE_KIT_v2/HAND_PROPS";
        private const string TargetDirectory = "Assets/OnlyVolunteers/Art/StyleKit_v2/HandProps";
        private const string PalettePath = "Assets/OnlyVolunteers/Art/StyleKit_v2/Materials/Look_Palette_v2b.mat";

        private static readonly string[] PropIds =
        {
            "PROP_CIGARETTE", "PROP_LIGHTER", "PROP_PHONE", "PROP_COFFEE_CUP",
            "PROP_SHOPPING_BAG", "PROP_BEACH_TOWEL",
        };

        [MenuItem("OnlyVolunteers/Art/Import Hand Props (STYLE_KIT_v2)")]
        public static void ImportHandProps()
        {
            Material palette = AssetDatabase.LoadAssetAtPath<Material>(PalettePath);
            if (palette == null)
            {
                Debug.LogError("[HandProps] Missing material: " + PalettePath);
                return;
            }

            if (!AssetDatabase.IsValidFolder(TargetDirectory))
                AssetDatabase.CreateFolder("Assets/OnlyVolunteers/Art/StyleKit_v2", "HandProps");

            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            foreach (string id in PropIds)
            {
                string fileName = id + "_v01.fbx";
                string source = Path.Combine(projectRoot, SourceDirectory, fileName);
                string assetPath = TargetDirectory + "/" + fileName;
                string target = Path.Combine(projectRoot, assetPath);

                if (!File.Exists(source))
                {
                    Debug.LogError("[HandProps] Missing source: " + source);
                    continue;
                }
                if (File.Exists(target))
                {
                    Debug.Log("[HandProps] Skipped existing file: " + assetPath);
                    continue;
                }

                try
                {
                    File.Copy(source, target, false);
                    AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
                    ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
                    if (importer == null)
                        throw new InvalidOperationException("Copied FBX has no ModelImporter: " + assetPath);

                    // Match the existing StyleKit_v2 model importer: metric scale 1,
                    // baked axis conversion, imported normals and palette remapping.
                    importer.animationType = ModelImporterAnimationType.None;
                    importer.importAnimation = false;
                    importer.importCameras = false;
                    importer.importLights = false;
                    importer.addCollider = false;
                    importer.globalScale = 1f;
                    importer.useFileScale = true;
                    importer.bakeAxisConversion = true;
                    importer.importNormals = ModelImporterNormals.Import;
                    importer.importTangents = ModelImporterTangents.None;
                    importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                    importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
                    importer.SaveAndReimport();

                    var names = new HashSet<string>(StringComparer.Ordinal);
                    foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(assetPath))
                        if (asset is Material material) names.Add(material.name);
                    foreach (var pair in importer.GetExternalObjectMap())
                        if (pair.Key.type == typeof(Material)) names.Add(pair.Key.name);
                    // Every hand prop was exported with exactly this one atlas material.
                    names.Add("Look_Palette_v2");
                    foreach (string name in names)
                        importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), name), palette);
                    importer.SaveAndReimport();
                    Debug.Log("[HandProps] Imported " + assetPath + " with " + names.Count + " palette material remap(s).");
                }
                catch (Exception exception)
                {
                    Debug.LogError("[HandProps] Failed to import " + assetPath + ": " + exception);
                }
            }
        }
    }
}
