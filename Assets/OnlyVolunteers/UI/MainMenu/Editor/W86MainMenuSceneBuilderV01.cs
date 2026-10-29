using System.Collections.Generic;
using System.Linq;
using FishNet.Managing;
using FishNet.Managing.Transporting;
using OnlyVolunteers.Session;
using OnlyVolunteers.UI.Pause;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.UI.MainMenu.EditorTools
{
    /// <summary>
    /// Builds the start-menu scene Scenes/Menu/MainMenu_v01.unity (29.10) additively, so the scene open in the editor stays
    /// open: a camera, a dim light, the menu (W86MainMenuV02 + the avatar preview + the lobby), the pause menu (its graphics
    /// page is the menu's Графика), a FishNet NetworkManager for the lobby (Tugboat, not DontDestroyOnLoad) and an
    /// EventSystem; then puts the menu FIRST in the Build Settings, before the play scene (nothing else removed).
    /// Re-running rebuilds the same scene file (its GUID stays).
    /// </summary>
    public static class W86MainMenuSceneBuilderV01
    {
        public const string ScenePath = WorldLaunchV01.MenuScenePath;
        const string BackdropPath = "Assets/OnlyVolunteers/UI/MainMenu/Art/MenuBackdrop_Wagon_v01.jpg";
        const string BodyPath = "Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_A.prefab";
        const string ClickPath = "Assets/OnlyVolunteers/Audio/Library_v1/ui/ui_pickup_01.wav";
        const string SpawnablesPath = "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationSpawnables_v02.asset";

        [MenuItem("OnlyVolunteers/Menu/Build start menu scene (v01)")]
        public static void BuildMenu() => Debug.Log(Build());

        public static string Build()
        {
            if (EditorApplication.isPlaying) return "leave Play mode first";
            var log = new System.Text.StringBuilder();
            Scene previous = SceneManager.GetActiveScene();
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(ScenePath));
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            SceneManager.SetActiveScene(scene);

            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.55f, 0.6f, 0.55f);
            RenderSettings.ambientEquatorColor = new Color(0.38f, 0.4f, 0.34f);
            RenderSettings.ambientGroundColor = new Color(0.2f, 0.2f, 0.17f);
            RenderSettings.fog = false;
            RenderSettings.skybox = null;

            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.07f, 0.08f, 0.06f);
            cam.cullingMask = 0; // the menu is UI; the avatar preview renders with its own camera
            camGo.AddComponent<AudioListener>();
            var urp = camGo.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            urp.renderPostProcessing = false;

            var lightGo = new GameObject("Directional Light");
            lightGo.transform.rotation = Quaternion.Euler(40f, 160f, 0f);
            var light = lightGo.AddComponent<Light>(); light.type = LightType.Directional; light.intensity = 0.4f;

            var netGo = new GameObject("[Menu] Network (lobby)");
            var tug = netGo.AddComponent<FishNet.Transporting.Tugboat.Tugboat>();
            var tm = netGo.AddComponent<TransportManager>();
            var nm = netGo.AddComponent<NetworkManager>();
            var tmSo = new SerializedObject(tm); tmSo.FindProperty("Transport").objectReferenceValue = tug; tmSo.ApplyModifiedPropertiesWithoutUndo();
            var nmSo = new SerializedObject(nm);
            var spawnables = AssetDatabase.LoadAssetAtPath<ScriptableObject>(SpawnablesPath);
            nmSo.FindProperty("_spawnablePrefabs").objectReferenceValue = spawnables;
            nmSo.FindProperty("_dontDestroyOnLoad").boolValue = false;
            nmSo.FindProperty("_runInBackground").boolValue = true;
            nmSo.ApplyModifiedPropertiesWithoutUndo();
            log.AppendLine("network: NetworkManager + Tugboat, spawnables " + (spawnables != null ? spawnables.name : "MISSING"));

            var pauseGo = new GameObject("[Menu] Pause (graphics page)");
            pauseGo.AddComponent<W86PauseMenuV01>();

            var menuGo = new GameObject("[Menu] Start");
            var lobby = menuGo.AddComponent<W86MenuLobbyV01>();
            lobby.Manager = nm;
            var preview = menuGo.AddComponent<W86AvatarPreviewV01>();
            preview.CrowdBodyPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(BodyPath);
            preview.ModularPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(OnlyVolunteers.Characters.Player.EditorTools.PlayerSausageImportV01.PrefabPath);
            var menu = menuGo.AddComponent<W86MainMenuV02>();
            menu.Lobby = lobby; menu.Preview = preview;
            menu.Backdrop = AssetDatabase.LoadAssetAtPath<Texture2D>(BackdropPath);
            menu.ClickClip = AssetDatabase.LoadAssetAtPath<AudioClip>(ClickPath);
            log.AppendLine($"menu: backdrop {(menu.Backdrop != null ? "ok" : "MISSING")}, player sausage {(preview.ModularPrefab != null ? "ok" : "MISSING (crowd stand-in)")}, preview body {(preview.CrowdBodyPrefab != null ? "ok" : "MISSING")}, click {(menu.ClickClip != null ? "ok" : "procedural")}");

            var esGo = new GameObject("[Menu] EventSystem", typeof(EventSystem), typeof(UnityEngine.InputSystem.UI.InputSystemUIInputModule));
            esGo.transform.SetAsLastSibling();

            bool saved = EditorSceneManager.SaveScene(scene, ScenePath);
            log.AppendLine("saved " + ScenePath + ": " + saved);
            if (previous.IsValid()) SceneManager.SetActiveScene(previous);
            EditorSceneManager.CloseScene(scene, true);

            // Build Settings: the menu first, everything else kept in order
            var list = EditorBuildSettings.scenes.ToList();
            list.RemoveAll(s => s.path == ScenePath);
            list.Insert(0, new EditorBuildSettingsScene(ScenePath, true));
            if (!list.Any(s => s.path == WorldLaunchV01.MapScenePath)) list.Insert(1, new EditorBuildSettingsScene(WorldLaunchV01.MapScenePath, true));
            EditorBuildSettings.scenes = list.ToArray();
            log.AppendLine("build settings: " + string.Join(", ", list.Select((s, i) => i + ":" + System.IO.Path.GetFileNameWithoutExtension(s.path))));
            AssetDatabase.SaveAssets();
            return log.ToString();
        }
    }
}
