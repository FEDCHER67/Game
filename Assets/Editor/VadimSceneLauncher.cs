using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Vadim's desktop shortcuts: open a scene and press Play. A running editor picks the request up from
    /// Library/ov_open_scene.txt; a fresh editor gets it from the -ovScene command-line argument.</summary>
    [InitializeOnLoad]
    static class VadimSceneLauncher
    {
        const string RequestFile = "Library/ov_open_scene.txt";
        static double _next;
        static string _pending;

        static VadimSceneLauncher()
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == "-ovScene" && !SessionState.GetBool("ovSceneDone", false))
                {
                    SessionState.SetBool("ovSceneDone", true);
                    _pending = args[i + 1];
                }
            EditorApplication.update += Tick;
        }

        static void Tick()
        {
            if (EditorApplication.timeSinceStartup < _next) return;
            _next = EditorApplication.timeSinceStartup + 1.0;
            if (_pending == null && File.Exists(RequestFile))
            {
                _pending = File.ReadAllText(RequestFile).Trim();
                File.Delete(RequestFile);
            }
            if (_pending == null || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            if (EditorApplication.isPlaying) { EditorApplication.isPlaying = false; return; }
            var scene = _pending;
            _pending = null;
            EditorSceneManager.OpenScene(scene);
            EditorApplication.isPlaying = true;
            Debug.Log("[VadimSceneLauncher] " + scene);
        }
    }
}
