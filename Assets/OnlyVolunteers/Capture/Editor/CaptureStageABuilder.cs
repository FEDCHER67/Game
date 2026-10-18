using System.IO;
using FishNet.Managing;
using FishNet.Managing.Transporting;
using FishNet.Object;
using FishNet.Transporting.Tugboat;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.Capture.Editor
{
    /// <summary>Builds the stage A prototype scene from the latest map play scene (never edits i09 itself) and the
    /// Windows player. Re-running it rebuilds only the "[Capture]" parts of the i10 scene.</summary>
    public static class CaptureStageABuilder
    {
        public const string SourceScene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i09_oaks_pines.unity";
        public const string StageAScene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        private const string ArtFolder = "Assets/OnlyVolunteers/Capture/Art";
        private const string TablePrefab = "Assets/OnlyVolunteers/Operation/Stage1/Prefabs/OperatingTableAstra_v02.prefab";
        private const string Spawnables = "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationSpawnables_v02.asset";
        private const string Tuning = "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationStage1_v02.asset";
        private const string GrabProfile = "Assets/OnlyVolunteers/Player/GrabPhysicsProfile.asset";
        private const string NetworkPlayerPrefab = "Assets/OnlyVolunteers/Network/Prefabs/NetworkPlayer.prefab";
        public const string BuildPath = "Working/Reviews/Capture/stageA/build/CaptureDelivery_StageA.exe";

        // The operating shed in grandpa's yard (B02, the hut itself is a solid block): plan metres, open toward the yard (north).
        public static readonly Vector3 ShedCenter = new Vector3(185.5f, 0f, 508.6f);
        public const float ShedWidth = 6f, ShedDepth = 5f, ShedHeight = 3.7f;
        public static readonly Vector3 TablePosition = new Vector3(185.5f, 0.07f, 508.75f);
        public const float TableYaw = 90f;

        [MenuItem("OnlyVolunteers/Capture/Build Stage A scene (i10)")]
        public static string BuildScene()
        {
            if (!File.Exists(StageAScene))
            {
                if (!AssetDatabase.CopyAsset(SourceScene, StageAScene)) throw new IOException("copy failed: " + SourceScene);
                AssetDatabase.Refresh();
            }
            var scene = EditorSceneManager.OpenScene(StageAScene);
            foreach (var root in scene.GetRootGameObjects())
                if (root.name.StartsWith("[Capture]")) Object.DestroyImmediate(root);

            // The old receiving pad loop (B01, ClinicDropOff) is off in this scene (D3: no pad).
            var clinic = GameObject.Find("FC_ClinicLoop");
            if (clinic != null) clinic.SetActive(false);

            var van = Object.FindAnyObjectByType<GreyboxVanCargo>(FindObjectsInactive.Include);
            if (van != null) { van.SoftLimit = 3; EditorUtility.SetDirty(van); }

            // Network: a solo FishNet host.
            var net = new GameObject("[Capture] Network (solo host)");
            var manager = net.AddComponent<NetworkManager>();
            var transportManager = net.AddComponent<TransportManager>();
            var tugboat = net.AddComponent<Tugboat>();
            var session = net.AddComponent<NetworkSession>();
            session.enabled = false; // only the grab allow-list (NetworkGrabber asks it); no menu, no player spawns
            var mso = new SerializedObject(manager);
            mso.FindProperty("_spawnablePrefabs").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Object>(Spawnables);
            mso.FindProperty("_dontDestroyOnLoad").boolValue = false;
            mso.FindProperty("_refreshDefaultPrefabs").boolValue = false;
            mso.ApplyModifiedPropertiesWithoutUndo();
            var tso = new SerializedObject(transportManager);
            var tp = tso.FindProperty("Transport") ?? tso.FindProperty("_transport");
            if (tp != null) { tp.objectReferenceValue = tugboat; tso.ApplyModifiedPropertiesWithoutUndo(); }

            // The map pawn becomes the host's NetworkPlayer (externalControl) with the operation's hands.
            var pawn = Object.FindAnyObjectByType<GreyboxKccPawn>(FindObjectsInactive.Include);
            if (pawn == null) throw new System.InvalidOperationException("no GreyboxKccPawn in " + StageAScene);
            var pawnGo = pawn.gameObject;
            var nob = pawnGo.GetComponent<NetworkObject>() ?? pawnGo.AddComponent<NetworkObject>();
            var player = pawnGo.GetComponent<NetworkPlayer>() ?? pawnGo.AddComponent<NetworkPlayer>();
            var pso = new SerializedObject(player);
            pso.FindProperty("externalControl").boolValue = true;
            pso.ApplyModifiedPropertiesWithoutUndo();
            var inventory = pawnGo.GetComponent<NetworkInventory>() ?? pawnGo.AddComponent<NetworkInventory>();
            var refInv = AssetDatabase.LoadAssetAtPath<GameObject>(NetworkPlayerPrefab).GetComponent<NetworkInventory>();
            var iso = new SerializedObject(inventory);
            iso.FindProperty("database").objectReferenceValue = new SerializedObject(refInv).FindProperty("database").objectReferenceValue;
            iso.FindProperty("reachOrigin").objectReferenceValue = pawn.Body;
            iso.ApplyModifiedPropertiesWithoutUndo();
            var grabber = pawnGo.GetComponent<NetworkGrabber>() ?? pawnGo.AddComponent<NetworkGrabber>();
            var gso = new SerializedObject(grabber);
            gso.FindProperty("profile").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Object>(GrabProfile);
            gso.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(pawnGo);

            // The operating shed and where the table spawns.
            var baseRoot = BuildShed();
            var spawn = new GameObject("Table spawn").transform;
            spawn.SetParent(baseRoot.transform, false);
            spawn.SetPositionAndRotation(TablePosition, Quaternion.Euler(0f, TableYaw, 0f));

            var directorGo = new GameObject("[Capture] Stage A director");
            var director = directorGo.AddComponent<CaptureDirector>();
            director.TablePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(TablePrefab).GetComponent<NetworkOperationTable>();
            director.TableSpawn = spawn;
            director.PawnNetworkObject = nob;
            director.Tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Tuning);

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var sceneIdProp = typeof(NetworkObject).GetProperty("SceneId", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
            string report = $"built {StageAScene}: pawn NetworkObject sceneId={(sceneIdProp != null ? sceneIdProp.GetValue(nob) : "?")}, table spawn {TablePosition}, clinic loop off, van soft limit 3";
            Debug.Log("[CAPTURE] " + report);
            return report;
        }

        private static Material Mat(string name, Color color, float smooth)
        {
            if (!AssetDatabase.IsValidFolder(ArtFolder)) AssetDatabase.CreateFolder("Assets/OnlyVolunteers/Capture", "Art");
            string path = ArtFolder + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name };
            m.SetColor("_BaseColor", color);
            m.SetFloat("_Smoothness", smooth);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        private static GameObject Box(Transform parent, string name, Vector3 center, Vector3 size, Material m, float yaw = 0f)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(center, Quaternion.Euler(0f, yaw, 0f));
            go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = m;
            go.isStatic = true;
            return go;
        }

        private static GameObject BuildShed()
        {
            var root = new GameObject("[Capture] Base B02 — operating shed").transform;
            var wood = Mat("Capture_Shed_Wood_v01", new Color(0.46f, 0.32f, 0.2f), 0.15f);
            var plank = Mat("Capture_Shed_Plank_v01", new Color(0.55f, 0.4f, 0.26f), 0.12f);
            var floor = Mat("Capture_Shed_Concrete_v01", new Color(0.56f, 0.55f, 0.52f), 0.1f);
            var roof = Mat("Capture_Shed_Roof_v01", new Color(0.24f, 0.29f, 0.33f), 0.35f);
            var tile = Mat("Capture_Shed_Tile_v01", new Color(0.78f, 0.84f, 0.82f), 0.5f);
            Vector3 c = ShedCenter;
            float w = ShedWidth, d = ShedDepth, h = ShedHeight;
            Box(root, "Floor", c + new Vector3(0f, 0.03f, 0f), new Vector3(w, 0.08f, d), floor);
            Box(root, "Floor tiles (operating corner)", c + new Vector3(0f, 0.071f, 0.15f), new Vector3(3.6f, 0.005f, 2.8f), tile);
            Box(root, "Back wall", c + new Vector3(0f, h * 0.5f, -d * 0.5f + 0.06f), new Vector3(w, h, 0.12f), plank);
            Box(root, "West wall", c + new Vector3(-w * 0.5f + 0.06f, h * 0.5f, 0f), new Vector3(0.12f, h, d), plank);
            Box(root, "East wall", c + new Vector3(w * 0.5f - 0.06f, h * 0.5f, -d * 0.18f), new Vector3(0.12f, h, d * 0.64f), plank);
            for (int i = 0; i < 2; i++)
                Box(root, "Front post " + i, c + new Vector3((i == 0 ? -1f : 1f) * (w * 0.5f - 0.1f), h * 0.5f, d * 0.5f - 0.1f), new Vector3(0.16f, h, 0.16f), wood);
            Box(root, "Front beam", c + new Vector3(0f, h - 0.12f, d * 0.5f - 0.1f), new Vector3(w, 0.2f, 0.18f), wood);
            var r = Box(root, "Roof", c + new Vector3(0f, h + 0.08f, 0.1f), new Vector3(w + 0.5f, 0.1f, d + 0.6f), roof);
            r.transform.rotation = Quaternion.Euler(-4f, 0f, 0f);
            // a shelf with jars and a bucket: it reads as grandpa's shed, not an operating theatre
            Box(root, "Shelf", c + new Vector3(-w * 0.5f + 0.35f, 1.3f, -0.6f), new Vector3(0.45f, 0.05f, 1.6f), wood);
            Box(root, "Shelf box", c + new Vector3(-w * 0.5f + 0.35f, 1.45f, -1.0f), new Vector3(0.3f, 0.25f, 0.35f), plank);
            var lampGo = new GameObject("Lamp");
            lampGo.transform.SetParent(root, false);
            lampGo.transform.position = c + new Vector3(0f, h - 0.35f, 0.15f);
            var lamp = lampGo.AddComponent<Light>();
            lamp.type = LightType.Point;
            lamp.color = new Color(1f, 0.92f, 0.78f);
            lamp.intensity = 4f;
            lamp.range = 9f;
            lamp.shadows = LightShadows.None;
            var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Object.DestroyImmediate(bulb.GetComponent<Collider>());
            bulb.name = "Bulb";
            bulb.transform.SetParent(lampGo.transform, false);
            bulb.transform.localScale = Vector3.one * 0.14f;
            var bulbMat = Mat("Capture_Shed_Bulb_v01", new Color(1f, 0.95f, 0.8f), 0.6f);
            bulbMat.EnableKeyword("_EMISSION");
            bulbMat.SetColor("_EmissionColor", new Color(2.5f, 2.2f, 1.6f));
            bulb.GetComponent<Renderer>().sharedMaterial = bulbMat;
            var sign = new GameObject("Sign");
            sign.transform.SetParent(root, false);
            sign.transform.position = c + new Vector3(0f, h - 0.12f, d * 0.5f + 0.02f);
            sign.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            var text = sign.AddComponent<TextMesh>();
            text.text = "ОПЕРАЦИОННАЯ ДЕДА";
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.GetComponent<MeshRenderer>().sharedMaterial = text.font.material;
            text.characterSize = 0.06f;
            text.fontSize = 64;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = new Color(0.95f, 0.9f, 0.75f);
            return root.gameObject;
        }

        [MenuItem("OnlyVolunteers/Capture/Build Stage A player (Windows)")]
        public static string BuildPlayer() => BuildPlayerAt(BuildPath);

        public static string BuildPlayerAt(string path)
        {
            string full = Path.GetFullPath(path);
            Directory.CreateDirectory(Path.GetDirectoryName(full));
            var options = new BuildPlayerOptions
            {
                scenes = new[] { StageAScene },
                locationPathName = full,
                target = BuildTarget.StandaloneWindows64,
                targetGroup = BuildTargetGroup.Standalone,
                options = BuildOptions.None,
            };
            var report = BuildPipeline.BuildPlayer(options);
            string text = $"result={report.summary.result} errors={report.summary.totalErrors} warnings={report.summary.totalWarnings} size={report.summary.totalSize / (1024 * 1024)} MB time={report.summary.totalTime}";
            Debug.Log("[CAPTURE] player build " + text + " -> " + full);
            return text;
        }
    }
}
