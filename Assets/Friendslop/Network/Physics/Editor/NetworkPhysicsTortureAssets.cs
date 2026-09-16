using System;
using System.IO;
using FishNet.Component.Transforming;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using Friendslop.Network.Physics.Validation;
using Friendslop.Network.Validation;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Friendslop.Network.Physics.Editor
{
    public static class NetworkPhysicsTortureAssets
    {
        public const string ScenePath = "Assets/Friendslop/Network/Physics/Validation/NetworkPhysicsTorture.unity";
        private const string SourceScenePath = "Assets/Friendslop/Network/Validation/MultiplayerBootstrapValidation.unity";
        private const string PlayerPrefabPath = "Assets/Friendslop/Network/Physics/Validation/NetworkPhysicsPlayer.prefab";
        private const string BodyPrefabPath = "Assets/Friendslop/Network/Physics/Validation/SharedPhysicsBody.prefab";
        private const string PrefabCollectionPath = "Assets/Friendslop/Network/Physics/Validation/NetworkPhysicsSpawnablePrefabs.asset";
        private const string PlayerMaterialPath = "Assets/Friendslop/Network/Physics/Validation/NetworkPlayerGray.mat";
        private const string BodyMaterialPath = "Assets/Friendslop/Network/Physics/Validation/SharedBodyBlue.mat";

        [MenuItem("Friendslop/Stage 12.4/Rebuild Torture Test Assets")]
        public static void RebuildAssets()
        {
            EnsureFolders();
            Material playerMaterial = CreateOrReplaceMaterial(PlayerMaterialPath, new Color(0.55f, 0.55f, 0.58f));
            Material bodyMaterial = CreateOrReplaceMaterial(BodyMaterialPath, new Color(0.16f, 0.46f, 0.8f));
            NetworkObject playerPrefab = CreatePlayerPrefab(playerMaterial);
            NetworkObject bodyPrefab = CreateBodyPrefab(bodyMaterial);
            DefaultPrefabObjects prefabs = CreatePrefabCollection(playerPrefab, bodyPrefab);
            CreateScene(playerPrefab, bodyPrefab, prefabs);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            Debug.Log("[Stage12.4] Rebuilt validation scene and prefabs.");
        }

        [MenuItem("Friendslop/Stage 12.4/Build Windows Development Player")]
        public static void BuildWindowsDevelopmentPlayer()
        {
            RebuildAssets();
            string configuredDirectory = Environment.GetEnvironmentVariable("FRIENDSLOP_STAGE124_BUILD_DIR");
            string outputDirectory = string.IsNullOrWhiteSpace(configuredDirectory)
                ? Path.Combine(Path.GetDirectoryName(Application.dataPath)!, "Temp", "Stage12_4Build")
                : configuredDirectory;
            Directory.CreateDirectory(outputDirectory);
            string executablePath = Path.Combine(outputDirectory, "FriendslopNetworkPhysicsTorture.exe");

            BuildPlayerOptions options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = executablePath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.Development
            };

            BuildReport report = BuildPipeline.BuildPlayer(options);
            if (report.summary.result != BuildResult.Succeeded)
                throw new InvalidOperationException($"Stage 12.4 build failed: {report.summary.result} ({report.summary.totalErrors} errors).");

            Debug.Log($"[Stage12.4] Windows development build created at {executablePath}.");
        }

        private static void EnsureFolders()
        {
            EnsureFolder("Assets/Friendslop/Network", "Physics");
            EnsureFolder("Assets/Friendslop/Network/Physics", "Validation");
        }

        private static void EnsureFolder(string parent, string name)
        {
            string path = $"{parent}/{name}";
            if (!AssetDatabase.IsValidFolder(path))
                AssetDatabase.CreateFolder(parent, name);
        }

        private static Material CreateOrReplaceMaterial(string path, Color color)
        {
            AssetDatabase.DeleteAsset(path);
            Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            Material material = new Material(shader) { color = color };
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        private static NetworkObject CreatePlayerPrefab(Material material)
        {
            AssetDatabase.DeleteAsset(PlayerPrefabPath);
            GameObject root = new GameObject("NetworkPhysicsPlayer");
            CharacterController controller = root.AddComponent<CharacterController>();
            controller.height = 1.8f;
            controller.radius = 0.35f;
            controller.center = new Vector3(0f, 0.9f, 0f);

            NetworkObject networkObject = root.AddComponent<NetworkObject>();
            root.AddComponent<NeutralNetworkPlayer>();
            NetworkTransform networkTransform = root.AddComponent<NetworkTransform>();
            NetworkPhysicsPlayer player = root.AddComponent<NetworkPhysicsPlayer>();

            GameObject visual = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            visual.name = "Visual";
            UnityEngine.Object.DestroyImmediate(visual.GetComponent<Collider>());
            visual.transform.SetParent(root.transform, false);
            visual.transform.localPosition = new Vector3(0f, 0.9f, 0f);
            visual.transform.localScale = new Vector3(0.7f, 0.9f, 0.7f);
            visual.GetComponent<Renderer>().sharedMaterial = material;

            GameObject cameraObject = new GameObject("OwnerCamera");
            cameraObject.transform.SetParent(root.transform, false);
            cameraObject.transform.localPosition = new Vector3(0f, 1.55f, 0f);
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.nearClipPlane = 0.05f;
            cameraObject.AddComponent<AudioListener>();

            SetObjectReference(player, "ownerCamera", camera);
            SetObjectReference(player, "playerRenderer", visual.GetComponent<Renderer>());
            ConfigureNetworkTransform(networkTransform, 1);
            SetObjectReference(networkObject, "_networkTransform", networkTransform);
            networkObject.SetAssetPathHash(0x1240000000000001UL);

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(root, PlayerPrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            return prefab.GetComponent<NetworkObject>();
        }

        private static NetworkObject CreateBodyPrefab(Material material)
        {
            AssetDatabase.DeleteAsset(BodyPrefabPath);
            GameObject root = GameObject.CreatePrimitive(PrimitiveType.Cube);
            root.name = "SharedPhysicsBody";
            root.transform.localScale = new Vector3(1.1f, 1.1f, 1.1f);
            root.GetComponent<Renderer>().sharedMaterial = material;
            Rigidbody rigidbody = root.AddComponent<Rigidbody>();
            rigidbody.mass = 8f;
            rigidbody.interpolation = RigidbodyInterpolation.Interpolate;
            rigidbody.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;

            NetworkObject networkObject = root.AddComponent<NetworkObject>();
            NetworkTransform networkTransform = root.AddComponent<NetworkTransform>();
            root.AddComponent<NetworkPhysicsBody>();
            ConfigureNetworkTransform(networkTransform, 2);
            SetObjectReference(networkObject, "_networkTransform", networkTransform);
            networkObject.SetAssetPathHash(0x1240000000000002UL);

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(root, BodyPrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            return prefab.GetComponent<NetworkObject>();
        }

        private static DefaultPrefabObjects CreatePrefabCollection(NetworkObject player, NetworkObject body)
        {
            AssetDatabase.DeleteAsset(PrefabCollectionPath);
            DefaultPrefabObjects collection = ScriptableObject.CreateInstance<DefaultPrefabObjects>();
            collection.AddObject(player);
            collection.AddObject(body);
            AssetDatabase.CreateAsset(collection, PrefabCollectionPath);
            return collection;
        }

        private static void CreateScene(NetworkObject playerPrefab, NetworkObject bodyPrefab, DefaultPrefabObjects prefabs)
        {
            AssetDatabase.DeleteAsset(ScenePath);
            Scene source = EditorSceneManager.OpenScene(SourceScenePath, OpenSceneMode.Single);
            if (!EditorSceneManager.SaveScene(source, ScenePath, true))
                throw new InvalidOperationException("Could not save the Stage 12.4 validation scene copy.");

            Scene scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            MultiplayerBootstrapValidationRunner oldRunner = UnityEngine.Object.FindFirstObjectByType<MultiplayerBootstrapValidationRunner>();
            if (oldRunner != null)
                UnityEngine.Object.DestroyImmediate(oldRunner);

            FishNetSessionController session = UnityEngine.Object.FindFirstObjectByType<FishNetSessionController>();
            NetworkManager manager = UnityEngine.Object.FindFirstObjectByType<NetworkManager>();
            if (session == null || manager == null)
                throw new InvalidOperationException("Stage 12.2 validation scene no longer contains the expected network bootstrap.");

            session.gameObject.name = "Network Physics Bootstrap (Validation)";
            SetObjectReference(session, "neutralPlayerPrefab", playerPrefab);
            manager.SpawnablePrefabs = prefabs;
            EditorUtility.SetDirty(manager);

            NetworkPhysicsTortureRunner runner = session.gameObject.AddComponent<NetworkPhysicsTortureRunner>();
            SetObjectReference(runner, "sharedBodyPrefab", bodyPrefab);

            Camera existingCamera = UnityEngine.Object.FindFirstObjectByType<Camera>();
            if (existingCamera != null)
                UnityEngine.Object.DestroyImmediate(existingCamera.gameObject);

            CreateArenaObject("Floor", new Vector3(0f, -0.5f, 2f), new Vector3(20f, 1f, 20f));
            CreateArenaObject("NorthWall", new Vector3(0f, 2f, 12f), new Vector3(20f, 4f, 1f));
            CreateArenaObject("SouthWall", new Vector3(0f, 2f, -8f), new Vector3(20f, 4f, 1f));
            CreateArenaObject("EastWall", new Vector3(10f, 2f, 2f), new Vector3(1f, 4f, 20f));
            CreateArenaObject("WestWall", new Vector3(-10f, 2f, 2f), new Vector3(1f, 4f, 20f));
            CreateArenaObject("ContentionPlinth", new Vector3(0f, 0.25f, 5f), new Vector3(4f, 0.5f, 3f));

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene))
                throw new InvalidOperationException("Could not save the Stage 12.4 validation scene.");
        }

        private static void CreateArenaObject(string name, Vector3 position, Vector3 scale)
        {
            GameObject gameObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
            gameObject.name = name;
            gameObject.transform.SetPositionAndRotation(position, Quaternion.identity);
            gameObject.transform.localScale = scale;
        }

        private static void ConfigureNetworkTransform(NetworkTransform networkTransform, int configuration)
        {
            SerializedObject serialized = new SerializedObject(networkTransform);
            serialized.FindProperty("_clientAuthoritative").boolValue = false;
            serialized.FindProperty("_sendToOwner").boolValue = true;
            serialized.FindProperty("_componentConfiguration").enumValueIndex = configuration;
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void SetObjectReference(UnityEngine.Object target, string propertyName, UnityEngine.Object value)
        {
            SerializedObject serialized = new SerializedObject(target);
            SerializedProperty property = serialized.FindProperty(propertyName);
            if (property == null)
                throw new InvalidOperationException($"Serialized property '{propertyName}' was not found on {target.GetType().Name}.");
            property.objectReferenceValue = value;
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
