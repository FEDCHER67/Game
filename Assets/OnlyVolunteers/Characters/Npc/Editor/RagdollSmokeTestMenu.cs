using OnlyVolunteers.Characters.Npc.Dev;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Characters.Npc
{
    // OnlyVolunteers/Characters/Npc/Dev/Ragdoll Smoke Test: runs Dev/RagdollSmokeTest in the open map scene
    // (Map_Greybox_v12 or Map_Look_v12_Play). Outside Play mode it enters Play, runs the test and leaves Play when done
    // (the request survives the domain reload in SessionState); in Play mode it just starts the test. Results:
    // [RagdollSmokeTest] lines in the console. Same pattern as Map/Editor/NpcLoadingTestMenu.
    public static class RagdollSmokeTestMenu
    {
        private const string PendingKey = "ov.ragdollSmokeTest";

        [MenuItem("OnlyVolunteers/Characters/Npc/Dev/Ragdoll Smoke Test")]
        private static void Run()
        {
            if (EditorApplication.isPlaying)
            {
                Spawn(false);
                return;
            }
            if (EditorUtility.scriptCompilationFailed)
            {
                Debug.LogWarning("[RagdollSmokeTest] not started: the scripts have compile errors");
                return;
            }
            // A time stamp, not a flag: if entering Play fails, a later Play must not start the test.
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
            var test = new GameObject("RagdollSmokeTest").AddComponent<RagdollSmokeTest>();
            test.ExitWhenDone = exitWhenDone;
        }
    }
}
