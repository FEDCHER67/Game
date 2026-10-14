using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // v19 only. The same continuous district field drives the baked albedo mask and camera haze.
    // Work in world metres, inset each lookup rectangle by 15 m, then interpolate neighbouring cores.
    [ExecuteAlways]
    public sealed class DistrictAtmosphere19 : MonoBehaviour
    {
        [Serializable]
        public sealed class District
        {
            public string id, mood;
            public Vector4 bounds; // min x/z, max x/z, from the source plan
            [Range(0, 1)] public float palette;
            public float exposure, saturation, contrast, temperature;
            public float fogStart, fogEnd;
            public Color fogColour;
        }

        public District[] districts = Array.Empty<District>();
        public float coreInset = 15f;
        private float[] weights;
        private readonly Stack<FogState> saved = new();

        private struct FogState
        {
            public bool enabled;
            public FogMode mode;
            public Color colour;
            public float start, end, density;
            public static FogState Read() => new()
            {
                enabled = RenderSettings.fog, mode = RenderSettings.fogMode, colour = RenderSettings.fogColor,
                start = RenderSettings.fogStartDistance, end = RenderSettings.fogEndDistance, density = RenderSettings.fogDensity
            };
            public void Restore()
            {
                RenderSettings.fog = enabled; RenderSettings.fogMode = mode; RenderSettings.fogColor = colour;
                RenderSettings.fogStartDistance = start; RenderSettings.fogEndDistance = end; RenderSettings.fogDensity = density;
            }
        }

        public static void Weights(District[] regions, Vector2 p, float inset, float[] result)
        {
            float total = 0f;
            for (int i = 0; i < regions.Length; i++)
            {
                Vector4 b = regions[i].bounds;
                float dx = Mathf.Max(Mathf.Max(b.x + inset - p.x, 0f), p.x - b.z + inset);
                float dz = Mathf.Max(Mathf.Max(b.y + inset - p.y, 0f), p.y - b.w + inset);
                float distance2 = dx * dx + dz * dz;
                if (distance2 < 0.000001f)
                {
                    Array.Clear(result, 0, result.Length); result[i] = 1f; return;
                }
                result[i] = 1f / distance2;
                total += result[i];
            }
            for (int i = 0; i < regions.Length; i++) result[i] /= Mathf.Max(total, 0.000001f);
        }

        public float PaletteAt(Vector2 p)
        {
            EnsureWeights(); Weights(districts, p, coreInset, weights);
            float t = 0f;
            for (int i = 0; i < districts.Length; i++) t += weights[i] * districts[i].palette;
            return t;
        }

        public Vector3 HazeAt(Vector3 p, out Color colour)
        {
            EnsureWeights(); Weights(districts, new Vector2(p.x, p.z), coreInset, weights);
            float start = 0f, extinction = 0f;
            colour = Color.clear;
            for (int i = 0; i < districts.Length; i++)
            {
                District d = districts[i];
                start += weights[i] * d.fogStart;
                // Effective linear haze density; blending reciprocal range avoids sudden fog-mode changes.
                extinction += weights[i] / Mathf.Max(1f, d.fogEnd - d.fogStart);
                colour += weights[i] * d.fogColour;
            }
            return new Vector3(start, start + 1f / Mathf.Max(extinction, 0.0001f), extinction);
        }

        private void EnsureWeights()
        {
            if (weights == null || weights.Length != districts.Length) weights = new float[districts.Length];
        }

        private void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering += BeginCamera;
            RenderPipelineManager.endCameraRendering += EndCamera;
        }

        private void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= BeginCamera;
            RenderPipelineManager.endCameraRendering -= EndCamera;
            while (saved.Count > 0) saved.Pop().Restore();
        }

        private void BeginCamera(ScriptableRenderContext context, Camera camera)
        {
            saved.Push(FogState.Read());
            if (districts.Length == 0 || camera.cameraType == CameraType.Preview || camera.cameraType == CameraType.Reflection) return;
            Vector3 haze = HazeAt(camera.transform.position, out Color colour);
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = colour;
            RenderSettings.fogStartDistance = haze.x;
            RenderSettings.fogEndDistance = haze.y;
        }

        private void EndCamera(ScriptableRenderContext context, Camera camera)
        {
            if (saved.Count > 0) saved.Pop().Restore();
        }
    }
}
