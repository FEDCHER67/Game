using OnlyVolunteers.Map.Dev;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // OnlyVolunteers/Map/Dev/NPC Loading Test: runs Map/Scripts/Dev/NpcLoadingTest in the open map scene (Map_Greybox_v12
    // or Map_Look_v12_Play). Outside Play mode it enters Play, runs the test and leaves Play when done (the request
    // survives the domain reload in SessionState); in Play mode it just starts the test. Results: [NpcLoadingTest] lines
    // in the console.
    public static class NpcLoadingTestMenu
    {
        private const string PendingKey = "ov.npcLoadingTest";

        [MenuItem("OnlyVolunteers/Map/Dev/NPC Loading Test")]
        private static void Run()
        {
            if (EditorApplication.isPlaying)
            {
                Spawn(false);
                return;
            }
            if (EditorUtility.scriptCompilationFailed)
            {
                Debug.LogWarning("[NpcLoadingTest] not started: the scripts have compile errors");
                return;
            }
            // A time stamp, not a flag: if entering Play fails, a later Play must not start the test.
            SessionState.SetFloat(PendingKey, (float)EditorApplication.timeSinceStartup);
            EditorApplication.isPlaying = true;
            // Play refused (nothing is entering it on the next editor tick): drop the request at once, so whoever presses
            // Play next does not get the test (it moves the van and ends their Play session).
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
            var test = new GameObject("NpcLoadingTest").AddComponent<NpcLoadingTest>();
            test.ExitWhenDone = exitWhenDone;
        }
    }
}
