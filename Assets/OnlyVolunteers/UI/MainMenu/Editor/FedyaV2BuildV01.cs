using System;
using System.IO;
using System.Linq;
using OnlyVolunteers.Session;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.UI.MainMenu.EditorTools
{
    /// <summary>
    /// Fedya's V2 build (31.10): the V2 start menu (MainMenu_V2_v01) + the V2 game scene (VanOnly_v01) as one Windows x64
    /// player in C:\Dev\GameBuilds\V2_Menu. MakeMenuScene copies MainMenu_v01 once (AssetDatabase.CopyAsset, never over an
    /// existing file) and sets the copy's menu to the V2 edition (VanOnly, no backdrop shot, no version label); MainMenu_v01
    /// itself is never opened for writing. Build applies the same player safeguards as VadimBuilds.Build (PC_RPAsset as the
    /// pipeline, the PC quality level, borderless fullscreen at native resolution) and only checks the scenes (missing
    /// scripts, cameras saved off): nothing is saved into VanOnly_v01.
    /// Batch: Unity.exe -batchmode -nographics -projectPath C:/Dev/Game -buildTarget Win64
    ///   -executeMethod OnlyVolunteers.UI.MainMenu.EditorTools.FedyaV2BuildV01.SetupBatch   (scene + Build Settings)
    ///   -executeMethod OnlyVolunteers.UI.MainMenu.EditorTools.FedyaV2BuildV01.BuildBatch   (the player)
    /// </summary>
    public static class FedyaV2BuildV01
    {
        public const string MenuV1 = WorldLaunchTargetV01.V1MenuScene;
        public const string MenuV2 = WorldLaunchTargetV01.V2MenuScene;
        public const string GameV2 = WorldLaunchTargetV01.V2GameScene;
        public const string ExePath = @"C:\Dev\GameBuilds\V2_Menu\VolunteersOnly_V2.exe";
        const string Pipeline = "Assets/Settings/PC_RPAsset.asset";
        const string Tag = "[FedyaV2Build] ";

        [MenuItem("OnlyVolunteers/Menu/V2 - make menu scene (MainMenu_V2_v01) + Build Settings")]
        public static void SetupMenuItem()
        {
            bool ok = MakeMenuScene() && AddToBuildSettings();
            EditorUtility.DisplayDialog("V2 menu", ok ? "MainMenu_V2_v01 is ready and in Build Settings." : "Failed: see the Console.", "OK");
        }

        [MenuItem("OnlyVolunteers/Build/Fedya V2 (menu V2 + VanOnly)")]
        public static void BuildMenuItem()
        {
            bool ok = Build(out string summary);
            EditorUtility.DisplayDialog("Fedya V2 build", summary, "OK");
            if (ok) EditorUtility.RevealInFinder(ExePath);
        }

        public static void SetupBatch()
        {
            bool ok = MakeMenuScene() && AddToBuildSettings();
            Debug.Log(Tag + "setup " + (ok ? "OK" : "FAILED"));
            if (Application.isBatchMode) EditorApplication.Exit(ok ? 0 : 1);
        }

        public static void BuildBatch()
        {
            bool ok = false;
            try { ok = Build(out string summary); Debug.Log(Tag + summary); }
            catch (Exception e) { Debug.LogException(e); }
            if (Application.isBatchMode) EditorApplication.Exit(ok ? 0 : 1);
        }

        /// <summary>MainMenu_V2_v01 = a copy of MainMenu_v01 with the menu set to V2. An existing copy is only re-checked
        /// (and its four menu fields set again if they differ); it is never replaced.</summary>
        public static bool MakeMenuScene()
        {
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(MenuV1) == null) { Debug.LogError(Tag + "missing " + MenuV1); return false; }
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(MenuV2) == null)
            {
                if (File.Exists(MenuV2)) { Debug.LogError(Tag + MenuV2 + " exists on disk but is not imported: not overwritten"); return false; }
                if (!AssetDatabase.CopyAsset(MenuV1, MenuV2)) { Debug.LogError(Tag + "CopyAsset failed: " + MenuV1 + " -> " + MenuV2); return false; }
                Debug.Log(Tag + "copied " + MenuV1 + " -> " + MenuV2);
            }
            var scene = EditorSceneManager.OpenScene(MenuV2, OpenSceneMode.Single);
            var menu = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<W86MainMenuV02>(true)).FirstOrDefault();
            if (menu == null) { Debug.LogError(Tag + "no W86MainMenuV02 in " + MenuV2); return false; }
            var so = new SerializedObject(menu);
            so.FindProperty(nameof(W86MainMenuV02.Edition)).intValue = (int)GameEditionV01.V2;
            so.FindProperty(nameof(W86MainMenuV02.GameScenePath)).stringValue = GameV2;
            so.FindProperty(nameof(W86MainMenuV02.Backdrop)).objectReferenceValue = null; // no forest-wagon shot: the V2 gradient
            so.FindProperty(nameof(W86MainMenuV02.VersionLabel)).stringValue = "";
            bool changed = so.ApplyModifiedPropertiesWithoutUndo();
            if (changed)
            {
                EditorSceneManager.MarkSceneDirty(scene);
                if (!EditorSceneManager.SaveScene(scene)) { Debug.LogError(Tag + "could not save " + MenuV2); return false; }
            }
            Debug.Log(Tag + MenuV2 + (changed ? " configured as V2" : " already V2") + ": game " + menu.GameScenePath + ", edition " + menu.Edition);
            return true;
        }

        /// <summary>Appends MainMenu_V2_v01 and VanOnly_v01 to Build Settings (existing entries kept as they are, in order).</summary>
        public static bool AddToBuildSettings()
        {
            var list = EditorBuildSettings.scenes.ToList();
            int before = list.Count;
            foreach (var path in new[] { MenuV2, GameV2 })
            {
                if (AssetDatabase.LoadAssetAtPath<SceneAsset>(path) == null) { Debug.LogError(Tag + "missing scene " + path); return false; }
                if (!list.Any(s => s.path == path)) list.Add(new EditorBuildSettingsScene(path, true));
            }
            if (list.Count != before)
            {
                EditorBuildSettings.scenes = list.ToArray();
                AssetDatabase.SaveAssets();
            }
            Debug.Log(Tag + "Build Settings: " + string.Join(", ", EditorBuildSettings.scenes.Select(s => Path.GetFileNameWithoutExtension(s.path) + (s.enabled ? "" : " (off)"))));
            return true;
        }

        /// <summary>The player: [MainMenu_V2_v01, VanOnly_v01], Windows x64, borderless fullscreen, PC_RPAsset.</summary>
        public static bool Build(out string summary)
        {
            summary = "";
            foreach (var path in new[] { MenuV2, GameV2 })
                if (AssetDatabase.LoadAssetAtPath<SceneAsset>(path) == null) { summary = "missing scene " + path + " (run the V2 menu setup first)"; Debug.LogError(Tag + summary); return false; }
            CheckScene(MenuV2);
            CheckScene(GameV2);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single); // nothing of the checks stays open (never saved)
            // the same player safeguards as VadimBuilds.Build: other sessions may leave the fog capture pipeline or a windowed
            // mode behind; the game always ships with PC_RPAsset and borderless fullscreen at native resolution
            var rp = AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.RenderPipelineAsset>(Pipeline);
            if (rp == null) { summary = "missing " + Pipeline; Debug.LogError(Tag + summary); return false; }
            UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline = rp;
            int pc = Array.IndexOf(QualitySettings.names, "PC");
            if (pc >= 0) { QualitySettings.SetQualityLevel(pc, false); QualitySettings.renderPipeline = rp; }
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.defaultIsNativeResolution = true;
            Debug.Log(Tag + "pipeline " + rp.name + ", quality " + QualitySettings.names[QualitySettings.GetQualityLevel()] + ", " + PlayerSettings.fullScreenMode);
            Directory.CreateDirectory(Path.GetDirectoryName(ExePath));
            var opt = new BuildPlayerOptions
            {
                scenes = new[] { MenuV2, GameV2 },
                locationPathName = ExePath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            };
            BuildReport r = BuildPipeline.BuildPlayer(opt);
            var s = r.summary;
            summary = $"{s.result}: {ExePath}, {s.totalSize / (1024.0 * 1024.0):0.0} MB (report), errors {s.totalErrors}, warnings {s.totalWarnings}, {s.totalTime.TotalMinutes:0.0} min";
            Debug.Log(Tag + summary);
            return s.result == BuildResult.Succeeded;
        }

        /// <summary>Read-only check of a scene before the build (VadimBuilds strips these in a copy; here nothing is saved):
        /// components with a missing script and prefab cameras saved off are reported.</summary>
        static void CheckScene(string path)
        {
            var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            int missing = 0, camerasOff = 0;
            foreach (var root in scene.GetRootGameObjects())
            {
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    missing += GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject);
                foreach (var cam in root.GetComponentsInChildren<Camera>(true))
                    if (!cam.enabled && PrefabUtility.IsPartOfPrefabInstance(cam)) { camerasOff++; Debug.LogWarning(Tag + path + ": prefab camera saved off: " + cam.name); }
            }
            if (missing > 0) Debug.LogWarning(Tag + path + ": " + missing + " component(s) with a missing script");
            Debug.Log(Tag + "checked " + Path.GetFileName(path) + ": missing scripts " + missing + ", prefab cameras off " + camerasOff);
        }
    }
}
