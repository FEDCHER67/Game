using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 (map data v02): the north steppe backdrop and the far sea are drawn up to the haze end (~4 km) while everything else keeps the
    // camera's own far clip (i10: 460 m) - per-layer cull distances on every game camera (the pawn / van cameras appear at runtime, so
    // cameras are re-checked once a second). Camera.layerCullDistances is not serialized, hence this component. The scene fog fades the
    // far land into the haze.
    [DisallowMultipleComponent]
    public sealed class W85FarView : MonoBehaviour
    {
        [Tooltip("Far plane for the far layer (steppe backdrop, far sea), m")] public float Far = 4000f;
        [Tooltip("Layer drawn to Far (TransparentFX = 1)")] public int FarLayer = 1;
        [Tooltip("Cull distance of all other layers; 0 = each camera's own far clip as found")] public float Others = 0f;
        readonly Dictionary<Camera, float> own = new();
        float next;

        void OnEnable() => next = 0f;

        void OnDisable()
        {
            foreach (var kv in own)
                if (kv.Key) { kv.Key.farClipPlane = kv.Value; kv.Key.layerCullDistances = new float[32]; }
            own.Clear();
        }

        void LateUpdate()
        {
            if (Time.unscaledTime < next) return;
            next = Time.unscaledTime + 1f;
            foreach (var cam in Camera.allCameras) Apply(cam);
        }

        void Apply(Camera cam)
        {
            if (!cam || cam.targetTexture != null || cam.cameraType != CameraType.Game || own.ContainsKey(cam)) return;
            float keep = Others > 0f ? Others : cam.farClipPlane;
            if (keep >= Far) return;
            own[cam] = cam.farClipPlane;
            var d = new float[32];
            for (int i = 0; i < 32; i++) d[i] = keep;
            d[Mathf.Clamp(FarLayer, 0, 31)] = 0f;                 // 0 = the far plane
            cam.farClipPlane = Far;
            cam.layerCullDistances = d;
        }
    }
}
