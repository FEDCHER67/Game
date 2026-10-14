using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // Camera-enqueued equivalent of the original v19 alpha fog overlay.
    // Does not create, modify or select a pipeline asset or renderer feature.
    public sealed class DistrictFogPass19V01 : ScriptableRenderPass
    {
        Material material;
        sealed class PassData
        {
            public Material material;
            public TextureHandle depth;
        }
        public DistrictFogPass19V01()
        {
            renderPassEvent = RenderPassEvent.BeforeRenderingTransparents;
            ConfigureInput(ScriptableRenderPassInput.Depth);
            profilingSampler = new ProfilingSampler("V19 camera depth-height fog");
        }
        public void SetMaterial(Material value) { material = value; }
        public override void RecordRenderGraph(RenderGraph graph, ContextContainer frameData)
        {
            if (!material) return;
            var resources = frameData.Get<UniversalResourceData>();
            if (!resources.cameraDepthTexture.IsValid()) return;
            using (var builder = graph.AddRasterRenderPass<PassData>("V19 camera depth-height fog", out var data, profilingSampler))
            {
                data.material = material;
                data.depth = resources.cameraDepthTexture;
                builder.UseTexture(data.depth, AccessFlags.Read);
                // Destination colour is read by fixed-function alpha blending, not sampled.
                builder.SetRenderAttachment(resources.activeColorTexture, 0, AccessFlags.ReadWrite);
                builder.SetRenderFunc(static (PassData pass, RasterGraphContext context) =>
                {
                    var properties = new MaterialPropertyBlock();
                    properties.SetVector("_BlitScaleBias", new Vector4(1, 1, 0, 0));
                    properties.SetTexture("_CameraDepthTexture", (Texture)pass.depth);
                    context.cmd.DrawProcedural(Matrix4x4.identity, pass.material, 0, MeshTopology.Triangles, 3, 1, properties);
                });
            }
        }
    }
}
