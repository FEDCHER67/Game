using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>PlayMode acceptance with real input: the dev scene's scenario driver adds virtual Mouse/Keyboard devices
    /// and plays through the real OperationTableView / NetworkGrabber / HUD as a host. These tests only start a scenario
    /// and assert on its authoritative-state checks (the driver lives in Assembly-CSharp, reached through the Core hook).</summary>
    public sealed partial class OperationRealInputPlayTests
    {
        private const string ScenePath = "Assets/OnlyVolunteers/Scenes/Dev/Operation_Net_Stage1_v02.unity";
        private static bool loaded;

        private static IEnumerator EnsureScene()
        {
            if (loaded && OperationTestHooks.Runner != null) yield break;
#if UNITY_EDITOR
            var op = UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(ScenePath, new LoadSceneParameters(LoadSceneMode.Single));
            while (!op.isDone) yield return null;
#endif
            float end = Time.realtimeSinceStartup + 10f;
            while (OperationTestHooks.Runner == null && Time.realtimeSinceStartup < end) yield return null;
            loaded = OperationTestHooks.Runner != null;
        }

        private static IEnumerator Run(string scenario, float timeout)
        {
            yield return EnsureScene();
            Assert.NotNull(OperationTestHooks.Runner, "scenario driver present in " + ScenePath);
            var runner = OperationTestHooks.Runner;
            runner.Begin(scenario);
            float end = Time.realtimeSinceStartup + timeout;
            while (runner.Busy && Time.realtimeSinceStartup < end) yield return null;
            Assert.False(runner.Busy, scenario + " timed out");
            string log = string.Join("\n", runner.Log);
            Debug.Log("[OPS TEST] " + scenario + " -> " + runner.LastResult + "\n" + log);
            Assert.AreEqual("PASS", runner.LastResult, log);
        }

        [UnityTest, Order(1), Timeout(400000)] public IEnumerator HostFullLoop_CarryStrapsAnesthesiaBloodThreeOrgans() => Run("loop", 360f);
        [UnityTest, Order(2), Timeout(400000)] public IEnumerator EdgeCases_EscapePanicRescueYankDirectCutToolReturnOverdoseF10() => Run("edges", 380f);
        [UnityTest, Order(3), Timeout(300000)] public IEnumerator RotatedAndMovedTable_TableLocalValidation() => Run("rotated", 280f);
        [UnityTest, Order(4), Timeout(120000)] public IEnumerator Hud_1280x720_Capture() => Run("hud720", 100f);
        [UnityTest, Order(5), Timeout(400000)] public IEnumerator V04_RagdollCarrySharedBellyKidneysFromBelowLiverLoopAndTray() => Run("v04-loop", 360f);
        [UnityTest, Order(6), Timeout(180000)] public IEnumerator V04_SharedGuideWrongStartResumeAndReentry() => Run("v04-guide-edges", 150f);
        [UnityTest, Order(7), Timeout(120000)] public IEnumerator V04_ThrowLandAndRegrabRagdollWithRealInput() => Run("v04-throw", 100f);
    }
}
