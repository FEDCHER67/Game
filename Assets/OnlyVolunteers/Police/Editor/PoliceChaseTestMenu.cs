using OnlyVolunteers.Police.Dev;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // OnlyVolunteers/Map/Dev/Police Chase Test: runs Police/Scripts/Dev/PoliceChaseTest in the open play scene
    // (Map_Look_vNN_Play built with the police). Outside Play mode it enters Play, runs the test and leaves Play when done
    // (the request survives the domain reload in SessionState); in Play mode it just starts it. Results: [PoliceChaseTest]
    // lines in the console, DONE n/n PASS at the end. Prints the bake's timing report first (it needs no Play mode).
    public static class PoliceChaseTestMenu
    {
        private const string PendingKey = "ov.policeChaseTest";

        [MenuItem("OnlyVolunteers/Map/Dev/Police Chase Test")]
        private static void Run()
        {
            if (EditorApplication.isPlaying)
            {
                Spawn(false);
                return;
            }
            if (EditorUtility.scriptCompilationFailed)
            {
                Debug.LogWarning("[PoliceChaseTest] not started: the scripts have compile errors");
                return;
            }
            var director = Object.FindAnyObjectByType<PoliceDirector>();
            if (director == null || director.Data == null)
            {
                Debug.LogWarning("[PoliceChaseTest] not started: no PoliceDirector with data in the open scene (build it with Build Map Look + Gameplay)");
                return;
            }
            PoliceBaker.Bake(false, director.Data.Revision); // step 1: the predictions, printed (the test reads the baked police_vNN.asset)
            SessionState.SetFloat(PendingKey, (float)EditorApplication.timeSinceStartup);
            EditorApplication.isPlaying = true;
            EditorApplication.delayCall += () =>
            {
                if (!EditorApplication.isPlayingOrWillChangePlaymode) SessionState.EraseFloat(PendingKey);
            };
        }

        [InitializeOnLoadMethod]
        private static void Hook()
        {
            EditorApplication.playModeStateChanged -= OnPlayModeChanged;
            EditorApplication.playModeStateChanged += OnPlayModeChanged;
        }

        private static void OnPlayModeChanged(PlayModeStateChange change)
        {
            if (change != PlayModeStateChange.EnteredPlayMode) return;
            float requested = SessionState.GetFloat(PendingKey, -1f);
            if (requested < 0f) return;
            SessionState.EraseFloat(PendingKey);
            if (EditorApplication.timeSinceStartup - requested < 120.0) Spawn(true);
        }

        private static void Spawn(bool exitWhenDone)
        {
            var test = new GameObject("PoliceChaseTest").AddComponent<PoliceChaseTest>();
            test.ExitWhenDone = exitWhenDone;
        }
    }
}
