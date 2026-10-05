using System.Collections.Generic;
using FishNet.Object;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Inventory.Editor
{
    /// <summary>
    /// Fills ItemDefinition world models from the imported organ props (the same FBX the map grey-box puts on its
    /// pickups) and makes the generic networked WorldItem prefab. Only empty references are filled, so a model or
    /// numbers chosen by hand are kept.
    /// </summary>
    internal static class ItemWorldModelMenu
    {
        private const string DatabasePath = "Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset";
        private const string GenericPrefabPath = "Assets/OnlyVolunteers/Inventory/Items/WorldItem_Generic.prefab";

        // Placeholder physics until playtest: mass kg, bounciness, squish. Size 0.45 m matches the grey-box pickups
        // (MapGreyboxBuilder.SpawnPickup), so an organ looks the same before and after it was carried.
        private readonly struct Entry
        {
            public readonly string[] Paths;
            public readonly float Size, Mass, Bounce, Squish;

            public Entry(float size, float mass, float bounce, float squish, params string[] paths)
            {
                Paths = paths;
                Size = size;
                Mass = mass;
                Bounce = bounce;
                Squish = squish;
            }
        }

        private static readonly Dictionary<string, Entry> Entries = new()
        {
            ["Heart"] = new Entry(0.45f, 0.35f, 0.35f, 0.2f, "Assets/OnlyVolunteers/Props/Organs/HEART-ASTRA-007.fbx"),
            ["Kidney"] = new Entry(0.45f, 0.2f, 0.35f, 0.2f, "Assets/OnlyVolunteers/Props/Organs/KIDNEY-ASTRA-001.fbx"),
            ["Liver"] = new Entry(0.45f, 0.6f, 0.25f, 0.25f, "Assets/OnlyVolunteers/Props/Organs/LIVER-ASTRA-001.fbx"),
            ["Lungs"] = new Entry(0.45f, 0.5f, 0.3f, 0.25f, "Assets/OnlyVolunteers/Props/Organs/LUNGS-ASTRA-001.fbx"),
            ["Brain"] = new Entry(0.45f, 0.45f, 0.3f, 0.3f, "Assets/OnlyVolunteers/Props/Organs/BRAIN-ASTRA-002.fbx"),
            // Not imported yet (ArtSource/Props/EYE-ASTRA-001); picked up once copied to one of these paths.
            ["Eye"] = new Entry(0.2f, 0.05f, 0.5f, 0.15f,
                "Assets/OnlyVolunteers/Props/Organs/EYE_ASTRA_001_v03.fbx",
                "Assets/OnlyVolunteers/Props/Organs/EYE-ASTRA-001.fbx"),
            ["Scalpel"] = new Entry(0.45f, 0.1f, 0.1f, 0f, "Assets/OnlyVolunteers/Props/ScalpelAstra/Model/SCALPEL-ASTRA-001.fbx"),
            // There is no cash item yet (cash is a number in the inventory); ready for one named Cash once
            // ArtSource/Props/CASH-ASTRA-001 is imported.
            ["Cash"] = new Entry(0.3f, 0.15f, 0.05f, 0f,
                "Assets/OnlyVolunteers/Props/Cash/CASH-ASTRA-001.fbx",
                "Assets/OnlyVolunteers/Props/CASH-ASTRA-001/CASH-ASTRA-001.fbx"),
        };

        [MenuItem("OnlyVolunteers/Inventory/Assign Item World Models")]
        private static void AssignWorldModels()
        {
            var database = AssetDatabase.LoadAssetAtPath<ItemDatabase>(DatabasePath);
            if (database == null)
            {
                Debug.LogError($"[Items] {DatabasePath} not found");
                return;
            }
            int assigned = 0;
            var report = new List<string>();
            foreach (ItemDefinition item in database.Items)
            {
                if (item == null) continue;
                if (item.WorldModel != null)
                {
                    report.Add($"{item.DisplayName}: kept {item.WorldModel.name}");
                    continue;
                }
                if (!Entries.TryGetValue(item.DisplayName, out Entry entry))
                {
                    report.Add($"{item.DisplayName}: no model known, drops as a grey box");
                    continue;
                }
                GameObject model = null;
                foreach (string path in entry.Paths)
                    if ((model = AssetDatabase.LoadAssetAtPath<GameObject>(path)) != null)
                        break;
                if (model == null)
                {
                    report.Add($"{item.DisplayName}: model not imported ({entry.Paths[0]}), drops as a grey box");
                    continue;
                }
                var so = new SerializedObject(item);
                so.FindProperty("worldModel").objectReferenceValue = model;
                so.FindProperty("worldModelSize").floatValue = entry.Size;
                so.FindProperty("dropMass").floatValue = entry.Mass;
                so.FindProperty("dropBounciness").floatValue = entry.Bounce;
                so.FindProperty("dropSquish").floatValue = entry.Squish;
                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(item);
                assigned++;
                report.Add($"{item.DisplayName}: {model.name}");
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"[Items] world models assigned: {assigned}\n" + string.Join("\n", report));
        }

        [MenuItem("OnlyVolunteers/Inventory/Create Generic WorldItem Prefab")]
        private static void CreateGenericPrefab()
        {
            var database = AssetDatabase.LoadAssetAtPath<ItemDatabase>(DatabasePath);
            if (database == null)
            {
                Debug.LogError($"[Items] {DatabasePath} not found");
                return;
            }
            var prefab = AssetDatabase.LoadAssetAtPath<NetworkObject>(GenericPrefabPath);
            if (prefab == null)
            {
                var go = new GameObject("WorldItem_Generic");
                go.AddComponent<NetworkObject>();
                var worldItem = go.AddComponent<WorldItem>();
                var item = new SerializedObject(worldItem);
                item.FindProperty("database").objectReferenceValue = database;
                item.ApplyModifiedPropertiesWithoutUndo();
                prefab = PrefabUtility.SaveAsPrefabAsset(go, GenericPrefabPath).GetComponent<NetworkObject>();
                Object.DestroyImmediate(go);
            }
            var so = new SerializedObject(database);
            so.FindProperty("genericWorldPrefab").objectReferenceValue = prefab;
            so.ApplyModifiedProperties();
            AssetDatabase.SaveAssets();
            Debug.Log($"[Items] generic WorldItem prefab: {GenericPrefabPath}. Check that it is listed in " +
                      "Assets/DefaultPrefabObjects.asset (FishNet adds new NetworkObject prefabs there on import).", prefab);
        }
    }
}
