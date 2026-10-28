using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Vadim's local Windows player builds of Fedya's map scenes (one exe per scene). Each scene is first copied to
    /// Assets/VadimLocal with missing-script components stripped; an object whose component still reads as null (04-KPP-button in W85: its
    /// W76LeaveCountryButton class lives in W76MapMarkers.cs) is dropped, as it corrupts level0 in the player.</summary>
    static class VadimBuilds
    {
        const string Root = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";

        public static void BuildAll()
        {
            var only = System.Environment.GetEnvironmentVariable("OV_BUILD_ONLY");
            if (only == null || only == "Map_W85") Build("Map_W85", "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v01.unity");
            if (only == "Map_W86") Build("Map_W86", "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity");
            if (only == null || only == "Map_v19") Build("Map_v19", "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity");
        }

        static void Build(string name, string scenePath)
        {
            var scene = EditorSceneManager.OpenScene(scenePath);
            int removed = 0;
            foreach (var root in scene.GetRootGameObjects())
            {
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                { if (t == null) continue;
                    removed += GameObjectUtility.RemoveMonoBehavioursWithMissingScript(t.gameObject);
                    // a component that still reads as null (script stored inside the scene) cannot be stripped: drop its object
                    if (t != null && (System.Array.Exists(t.GetComponents<Component>(), c => c == null) || t.name == "04-KPP-button" || t.name == "Trigger_10-missile-strike-trigger"))
                    { Debug.Log("[VadimBuilds] drop object " + t.name); Object.DestroyImmediate(t.gameObject); removed++; }
                }
            }
            // render scripts switch the game cameras off; a prefab camera saved off (Player_KCC_Baseline) gives a grey game
            foreach (var cam in Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (!cam.enabled && PrefabUtility.IsPartOfPrefabInstance(cam)) { cam.enabled = true; Debug.Log("[VadimBuilds] camera on: " + cam.name); }
            var copy = "Assets/VadimLocal/Build_" + name + ".unity";
            EditorSceneManager.SaveScene(scene, copy, true);
            // other sessions build previews/renders from this project and may leave the fog capture pipeline or a windowed mode behind:
            // the game always ships with PC_RPAsset and borderless fullscreen at native resolution
            var rp = AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.RenderPipelineAsset>("Assets/Settings/PC_RPAsset.asset");
            UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline = rp;
            int pc = System.Array.IndexOf(QualitySettings.names, "PC"); if (pc >= 0) { QualitySettings.SetQualityLevel(pc, false); QualitySettings.renderPipeline = rp; }
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow; PlayerSettings.defaultIsNativeResolution = true;
            Debug.Log("[VadimBuilds] pipeline " + (rp ? rp.name : "null") + ", quality " + QualitySettings.names[QualitySettings.GetQualityLevel()] + ", " + PlayerSettings.fullScreenMode);
            var opt = new BuildPlayerOptions
            {
                scenes = new[] { copy },
                locationPathName = Root + name + @"\VolunteersOnly_" + name + ".exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None
            };
            var r = BuildPipeline.BuildPlayer(opt);
            Debug.Log("[VadimBuilds] " + name + ": " + r.summary.result + " errors=" + r.summary.totalErrors + " missingScriptsRemoved=" + removed);
        }
    }
}
