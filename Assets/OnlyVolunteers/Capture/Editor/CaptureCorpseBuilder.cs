using System;
using System.Linq;
using GameKit.Dependencies.Utilities;
using FishNet.Managing.Object;
using FishNet.Object;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player.Physics;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.Capture.Editor
{
    public static class CaptureCorpseBuilder
    {
        private const string Root = "Assets/OnlyVolunteers/Capture/";
        private const string PrefabPath = Root + "Art/BodyBag_Cargo_v02.prefab";
        private const string DefinitionPath = Root + "Art/BodyBag_Cargo_v02.asset";
        [MenuItem("OnlyVolunteers/Capture/Integrate corpse body bag v02")]
        public static string Apply()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "Art/BODYBAG_ASTRA_001_v02.fbx");
            if (source == null) throw new InvalidOperationException("Approved G34 v02 FBX is missing");
            var definition = AssetDatabase.LoadAssetAtPath<ItemDefinition>(DefinitionPath);
            if (definition == null)
            {
                definition = ScriptableObject.CreateInstance<ItemDefinition>();
                var ids = AssetDatabase.FindAssets("t:ItemDefinition").Select(g => AssetDatabase.LoadAssetAtPath<ItemDefinition>(AssetDatabase.GUIDToAssetPath(g)).Id).ToArray();
                var data = new SerializedObject(definition);
                data.FindProperty("id").intValue = ids.Length > 0 ? ids.Max() + 1 : 1;
                data.FindProperty("displayName").stringValue = "Мешок с телом"; data.FindProperty("shortLabel").stringValue = "ТЕЛО";
                data.FindProperty("size").intValue = 64; data.FindProperty("maxStack").intValue = 1;
                data.ApplyModifiedPropertiesWithoutUndo(); AssetDatabase.CreateAsset(definition, DefinitionPath);
            }
            var go = new GameObject("BodyBag_Cargo_v02");
            try
            {
                var network = go.AddComponent<NetworkObject>(); var body = go.AddComponent<Rigidbody>(); body.mass = 12f;
                body.interpolation = RigidbodyInterpolation.Interpolate; body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
                var handle = go.AddComponent<NetworkPhysicsBody>(); var hso = new SerializedObject(handle);
                hso.FindProperty("profile").objectReferenceValue = AssetDatabase.LoadAssetAtPath<GrabPhysicsProfile>("Assets/OnlyVolunteers/Player/GrabPhysicsProfile.asset"); hso.ApplyModifiedPropertiesWithoutUndo();
                var world = go.AddComponent<WorldItem>(); var wso = new SerializedObject(world); wso.FindProperty("definition").objectReferenceValue = definition; wso.ApplyModifiedPropertiesWithoutUndo();
                go.AddComponent<CaptureBodyBag>();
                var model = (GameObject)PrefabUtility.InstantiatePrefab(source, go.transform);
                var material = AssetDatabase.LoadAssetAtPath<Material>(Root + "Art/BodyBag_Cargo_v02.mat");
                if (material == null)
                {
                    material = new Material(Shader.Find("Universal Render Pipeline/Lit")); material.SetFloat("_Smoothness", 0.32f);
                    material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "Art/BODYBAG_ASTRA_001_v02_Atlas_00.png"));
                    AssetDatabase.CreateAsset(material, Root + "Art/BodyBag_Cargo_v02.mat");
                }
                int collisions = 0;
                foreach (var transform in model.GetComponentsInChildren<Transform>(true))
                    if (transform.name.Contains("OpenFlat")) transform.gameObject.SetActive(false);
                foreach (var mesh in model.GetComponentsInChildren<MeshFilter>(true))
                {
                    var renderer = mesh.GetComponent<Renderer>();
                    if (mesh.name.Contains("OpenFlat")) continue;
                    if (mesh.name.StartsWith("UCX_"))
                    {
                        renderer.enabled = false; var collider = mesh.gameObject.AddComponent<MeshCollider>(); collider.sharedMesh = mesh.sharedMesh; collider.convex = true; collisions++;
                    }
                    else renderer.sharedMaterial = material;
                }
                if (collisions == 0) throw new InvalidOperationException("v02 UCX collision proxy missing");
                network.SetAssetPathHash((PrefabPath + "BodyBagCargoV02").GetStableHashU64());
                var prefab = PrefabUtility.SaveAsPrefabAsset(go, PrefabPath).GetComponent<CaptureBodyBag>();
                var dso = new SerializedObject(definition); dso.FindProperty("worldPrefab").objectReferenceValue = prefab.GetComponent<NetworkObject>(); dso.ApplyModifiedPropertiesWithoutUndo(); AssetDatabase.SaveAssetIfDirty(definition);
                var spawnables = AssetDatabase.LoadAssetAtPath<SinglePrefabObjects>("Assets/OnlyVolunteers/Operation/Stage1/Data/OperationSpawnables_v02.asset");
                spawnables.AddObject(prefab.GetComponent<NetworkObject>(), true, false); EditorUtility.SetDirty(spawnables); AssetDatabase.SaveAssetIfDirty(spawnables);
                var scene = EditorSceneManager.OpenScene(CaptureStageABuilder.StageAScene);
                var director = UnityEngine.Object.FindAnyObjectByType<CaptureDirector>();
                var so = new SerializedObject(director); so.FindProperty("BodyBagPrefab").objectReferenceValue = prefab; so.ApplyModifiedPropertiesWithoutUndo();
                EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                return "Body bag v02: closed visual + " + collisions + " convex UCX, physical inventory item, spawnables and i10 director assigned";
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }
    }
}
