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
                    if (t != null && System.Array.Exists(t.GetComponents<Component>(), c => c == null))
                    { Debug.Log("[VadimBuilds] drop object " + t.name); Object.DestroyImmediate(t.gameObject); removed++; }
                }
            }
            var copy = "Assets/VadimLocal/Build_" + name + ".unity";
            EditorSceneManager.SaveScene(scene, copy, true);
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
