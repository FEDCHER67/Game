using UnityEditor;

namespace OnlyVolunteers.Capture.Editor
{
    /// <summary>Dev aid: SessionState "capture.autorun" = scenario name starts that scenario of the capture driver as soon
    /// as Play has the runner (used from automation; one-shot).</summary>
    [InitializeOnLoad]
    public static class CaptureDevAutorun
    {
        public const string Key = "capture.autorun";

        static CaptureDevAutorun()
        {
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            if (!EditorApplication.isPlaying) return;
            string name = SessionState.GetString(Key, "");
            if (string.IsNullOrEmpty(name)) return;
            var runner = CaptureTestHooks.Runner;
            if (runner == null || runner.Busy) return;
            SessionState.EraseString(Key);
            runner.Begin(name);
        }
    }
}
