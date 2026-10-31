using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>Builds that start with a main menu (the V2 build, and Vadim's Hangar / VanOnly builds since 31.10) still run
    /// their hidden scripted tests: started with -baseTest, -hangarTest or -vanTest, the first scene (the menu) is skipped
    /// and the build's game scene (index 1) loads at once. Without those arguments nothing happens.</summary>
    public static class MenuTestSkipV01
    {
        private static readonly string[] TestArgs = { "-baseTest", "-hangarTest", "-vanTest" };

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void SkipMenuForTests()
        {
            if (Application.isEditor) return;
            string[] args = System.Environment.GetCommandLineArgs();
            bool test = false;
            foreach (string a in TestArgs) if (System.Array.IndexOf(args, a) >= 0) test = true;
            if (!test) return;
            Scene s = SceneManager.GetActiveScene();
            if (s.buildIndex != 0 || !s.name.StartsWith("MainMenu") || SceneManager.sceneCountInBuildSettings < 2) return;
            Debug.Log("[OV] test run: skipping the start menu, loading build scene 1");
            SceneManager.LoadScene(1, LoadSceneMode.Single);
        }
    }
}
