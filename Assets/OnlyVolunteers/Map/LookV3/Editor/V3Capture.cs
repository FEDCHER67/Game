using System.IO;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // Off-screen captures of the open scene for review: a temporary camera at a pose renders through the v3 pipeline
    // asset (2 cascades, MSAA 4x, depth + opaque textures for the water), restored afterwards (as the v2 trial renders).
    public static class V3Capture
    {
        // Revision of the open scene's look (pipeline asset and far clip follow it); MapLookBuilderV3.Revision = v16.
        public static string Revision = MapLookBuilderV3.Revision;

        public static string Shot(string file, Vector3 position, Vector3 target, float fov = 60f, int width = 1920, int height = 1080, bool ortho = false, float orthoSize = 100f, bool fog = true)
        {
            RenderPipelineAsset old = QualitySettings.renderPipeline;
            bool oldFog = RenderSettings.fog;
            var go = new GameObject("V3_CaptureCamera");
            try
            {
                RenderSettings.fog = fog && oldFog;
                QualitySettings.renderPipeline = V3Lighting.PipelineFor(Revision);
                var cam = go.AddComponent<Camera>();
                cam.fieldOfView = fov;
                cam.nearClipPlane = ortho ? 1f : 0.1f;
                cam.farClipPlane = ortho ? 3000f : V3Lighting.FarClipFor(Revision);
                cam.orthographic = ortho;
                cam.orthographicSize = orthoSize;
                cam.clearFlags = CameraClearFlags.Skybox;
                go.transform.position = position;
                Vector3 dir = target - position;
                go.transform.rotation = Quaternion.LookRotation(dir.sqrMagnitude > 1e-6f ? dir.normalized : Vector3.forward,
                    Mathf.Abs(Vector3.Dot(dir.normalized, Vector3.up)) > 0.99f ? Vector3.forward : Vector3.up);
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = true;
                data.antialiasing = AntialiasingMode.None;
                var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
                rt.Create();
                var resolved = new RenderTexture(width, height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
                resolved.Create();
                cam.targetTexture = rt;
                cam.Render();
                // A second frame: shadows and SSAO of a fresh camera settle, and the opaque texture the water reads exists.
                cam.Render();
                cam.targetTexture = null;
                Graphics.Blit(rt, resolved);
                RenderTexture prev = RenderTexture.active;
                RenderTexture.active = resolved;
                var tex = new Texture2D(width, height, TextureFormat.RGB24, false, false);
                tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                tex.Apply();
                RenderTexture.active = prev;
                Directory.CreateDirectory(Path.GetDirectoryName(file));
                File.WriteAllBytes(file, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                rt.Release();
                resolved.Release();
                Object.DestroyImmediate(rt);
                Object.DestroyImmediate(resolved);
                return file;
            }
            finally
            {
                Object.DestroyImmediate(go);
                QualitySettings.renderPipeline = old;
                RenderSettings.fog = oldFog;
            }
        }
    }
}
