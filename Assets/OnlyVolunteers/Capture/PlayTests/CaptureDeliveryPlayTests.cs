using System.Collections;
using NUnit.Framework;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>Capture → delivery stage A in the real map scene (i10) as a solo FishNet host. The scenario driver
    /// (Assembly-CSharp, reached through CaptureTestHooks) plays like a person: virtual Mouse/Keyboard into everything the
    /// game reads through the Input System (the field kit, the table view, the NetworkGrabber, K); the legacy-input map
    /// keys (Q, LMB carry, E, W/A/S/D) go through the same entry points their handlers call. These tests start a
    /// scenario and assert on its authoritative-state checks; evidence goes to Working/Reviews/Capture/stageA/run_*.</summary>
    public sealed partial class CaptureDeliveryPlayTests
    {
        private const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";

        private static IEnumerator LoadScene()
        {
            LogAssert.ignoreFailingMessages = true;
#if UNITY_EDITOR
            var op = UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(ScenePath, new LoadSceneParameters(LoadSceneMode.Single));
            while (!op.isDone) yield return null;
#endif
            float end = Time.realtimeSinceStartup + 30f;
            while (CaptureTestHooks.Runner == null && Time.realtimeSinceStartup < end) yield return null;
        }

        private static IEnumerator EnsureScene()
        {
            if (CaptureTestHooks.Runner != null) yield break;
            yield return LoadScene();
        }

        private static IEnumerator Run(string scenario, float timeout)
        {
            // The map logs its own warnings/errors (assets, crowd); the scenario's checks are the assertions here.
            LogAssert.ignoreFailingMessages = true;
            var runner = CaptureTestHooks.Runner;
            Assert.NotNull(runner, "capture scenario driver present in " + ScenePath);
            runner.Begin(scenario);
            float end = Time.realtimeSinceStartup + timeout;
            while (runner.Busy && Time.realtimeSinceStartup < end) yield return null;
            Assert.False(runner.Busy, scenario + " timed out");
            string log = string.Join("\n", runner.Log);
            Debug.Log("[CAPTURE TEST] " + scenario + " -> " + runner.LastResult + "\n" + log);
            Assert.AreEqual("PASS", runner.LastResult, log);
        }

        [UnityTest, Order(1), Timeout(420000)]
        public IEnumerator FullLoop_HamletKnockout_TiesAnesthesiaBlood_Van3_DriveToBase_TableCloud_Kidney()
        {
            // A fresh game: the automated runs have their own save slot, emptied before the scene comes up.
            CaptureTestHooks.SaveSlot = "capture_stageA_test.json";
            string path = System.IO.Path.Combine(Application.persistentDataPath, "OnlyVolunteers", CaptureTestHooks.SaveSlot);
            if (System.IO.File.Exists(path)) System.IO.File.Delete(path);
            yield return LoadScene();
            yield return Run("loop", 400f);
        }

        [UnityTest, Order(2), Timeout(240000)]
        public IEnumerator SaveAndQuit_ReloadKeepsPositionsSleepBloodTies()
        {
            yield return EnsureScene();
            yield return Run("save-a", 90f);
            yield return LoadScene(); // "quit and start again": the scene comes up fresh and loads the save
            yield return Run("save-b", 90f);
        }

        [UnityTest, Order(3), Timeout(240000)]
        public IEnumerator PushPolicy_HeldOrganRagdollsCarriedNpcNeverMoveThePlayer_VanStillDoes()
        {
            yield return EnsureScene();
            yield return Run("push", 200f);
        }

        [UnityTest, Order(4), Timeout(240000)]
        public IEnumerator FieldRules_OverdoseKills_BloodRefusals_TieRows()
        {
            yield return EnsureScene();
            yield return Run("rules", 200f);
        }
    }
}
