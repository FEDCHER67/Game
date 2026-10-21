using OnlyVolunteers.Capture;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // In the Unity editor CaptureDirector saves to the shared slot capture_stageA_editor.json (also used by the i10 play scene), so a
    // W85 session would load i10 positions (van / player teleported) and overwrite i10's editor save. This sets the existing
    // CaptureTestHooks.SaveSlot override to a W85-only slot before CaptureDirector starts. Editor only; builds use SaveFileName.
    [DefaultExecutionOrder(-10000)]
    public sealed class W85EditorSaveSlot : MonoBehaviour
    {
        public string EditorSlot = "capture_stageA_editor_W85.json";

        void Awake()
        {
#if UNITY_EDITOR
            if (string.IsNullOrEmpty(CaptureTestHooks.SaveSlot)) CaptureTestHooks.SaveSlot = EditorSlot;
#endif
        }
    }
}
