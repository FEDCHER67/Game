// W85 tall grass renderer: fork of ThirdParty/GrassInstancer_MB/ChunkedGrassRenderer24 (MangoButtermilch approach 3, MIT; the
// original stays untouched for i10). Same baked data (GrassPatchData24), blade mesh and shared-wind material (shadow receiving kept,
// several blade kinds kept). Changes for FPS (Fedya's grass decisions, 21.10):
//  - draw distance 40-60 m by quality preset, the shader's own fade over the last 20 m;
//  - density falloff with distance (a stable per-blade hash keeps 100 % near the camera -> ~25-45 % at the draw distance);
//  - chunk culling on the CPU per camera: frustum + distance + terrain-horizon occlusion (a chunk behind a hill is skipped),
//    the compute shader only expands the visible chunks;
//  - quality setting High / Medium / Low / Off (PlayerPrefs "ov_grass_quality"; W85GrassRenderer.SetQuality).
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using OnlyVolunteers.Map.Grass;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.W85
{
    public enum GrassQuality { Off = 0, Low = 1, Medium = 2, High = 3 }

    [ExecuteAlways]
    public sealed class W85GrassRenderer : MonoBehaviour
    {
        [StructLayout(LayoutKind.Sequential)]
        public struct Blade { public Vector4 positionHeight, shape; }

        public GrassPatchData24 data;
        public Mesh bladeMesh;
        public Material material;
        public ComputeShader visibility;
        [Tooltip("Terrain heights for the horizon occlusion test (RFloat, world heights).")] public Texture2D heightField;
        public Vector4 heightWorld = new(0, 0, 1744, 950);
        [Range(0, 1)] public float windStrength = .24f;
        public float windSpeed = 1.25f;
        [Header("Presets: draw distance (m), kept density at the far edge")]
        public Vector2 high = new(60, .45f), medium = new(50, .35f), low = new(40, .25f);
        public bool occlusion = true;
        [NonSerialized] public float reviewTime = -1;

        const string PrefKey = "ov_grass_quality";
        static GrassQuality quality = (GrassQuality)(-1);
        public static GrassQuality Quality
        {
            get { if ((int)quality < 0) quality = (GrassQuality)Mathf.Clamp(PlayerPrefs.GetInt(PrefKey, (int)GrassQuality.High), 0, 3); return quality; }
        }
        public static void SetQuality(GrassQuality q) { quality = q; PlayerPrefs.SetInt(PrefKey, (int)q); }

        public float ViewDistance => Quality switch { GrassQuality.High => high.x, GrassQuality.Medium => medium.x, GrassQuality.Low => low.x, _ => 0f };
        float FarKeep => Quality switch { GrassQuality.High => high.y, GrassQuality.Medium => medium.y, GrassQuality.Low => low.y, _ => 0f };
        public int TotalInstances => data ? data.instanceCount : 0;

        GraphicsBuffer source, chunks, mask;
        uint[] maskData;
        float[] heights; int hfW, hfH;
        ComputeShader compute;
        Material ownedMaterial;
        int kernel;
        readonly Plane[] planes = new Plane[6];
        readonly Vector4[] gpuPlanes = new Vector4[6];
        readonly Dictionary<Camera, CameraBuffers> cameras = new();
        readonly List<Camera> dead = new();

        sealed class CameraBuffers : IDisposable
        {
            public GraphicsBuffer visible, args;
            public MaterialPropertyBlock properties = new();
            public void Dispose() { visible?.Dispose(); args?.Dispose(); visible = args = null; }
        }

        void OnEnable() { RenderPipelineManager.beginCameraRendering += Render; }
        void OnDisable() { RenderPipelineManager.beginCameraRendering -= Render; Release(); }
        void OnDestroy() { Release(); }
        void Update()
        {
            dead.Clear();
            foreach (var pair in cameras) if (!pair.Key) dead.Add(pair.Key);
            foreach (var c in dead) { cameras[c].Dispose(); cameras.Remove(c); }
        }

        bool Prepare()
        {
            if (source != null) return true;
            if (!data || !data.instances || data.instanceCount <= 0 || !bladeMesh || !material || !visibility) return false;
            if (!SystemInfo.supportsComputeShaders || !SystemInfo.supportsInstancing) return false;
            byte[] bytes = data.instances.bytes;
            if (bytes.Length != data.instanceCount * 32) throw new InvalidDataException("W85 grass payload length mismatch");
            var blades = new Blade[data.instanceCount];
            using (var r = new BinaryReader(new MemoryStream(bytes, false)))
                for (int i = 0; i < blades.Length; i++)
                {
                    blades[i].positionHeight = new Vector4(r.ReadSingle(), r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                    blades[i].shape = new Vector4(r.ReadSingle(), r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                }
            try
            {
                source = new GraphicsBuffer(GraphicsBuffer.Target.Structured, blades.Length, 32); source.SetData(blades);
                chunks = new GraphicsBuffer(GraphicsBuffer.Target.Structured, data.chunks.Length, 32); chunks.SetData(data.chunks);
                compute = Instantiate(visibility); compute.hideFlags = HideFlags.HideAndDontSave;
                ownedMaterial = new Material(material) { enableInstancing = true, hideFlags = HideFlags.HideAndDontSave };
                kernel = compute.FindKernel("ChunkRender");
                compute.SetBuffer(kernel, "_Blades", source); compute.SetBuffer(kernel, "_Chunks", chunks);
                compute.SetInt("_ChunkCount", data.chunks.Length);
                mask = new GraphicsBuffer(GraphicsBuffer.Target.Structured, data.chunks.Length, 4);
                maskData = new uint[data.chunks.Length];
                compute.SetBuffer(kernel, "_ChunkMask", mask);
                heights = null;
                if (heightField && heightField.isReadable)
                {
                    hfW = heightField.width; hfH = heightField.height;
                    var px = heightField.GetPixels();
                    heights = new float[px.Length];
                    for (int i = 0; i < px.Length; i++) heights[i] = px[i].r;
                }
                return true;
            }
            catch { Release(); throw; }
        }

        void Render(ScriptableRenderContext context, Camera camera)
        {
            if (Quality == GrassQuality.Off || !camera || camera.cameraType == CameraType.Preview || camera.cameraType == CameraType.Reflection || !Prepare()) return;
            if ((camera.cullingMask & (1 << gameObject.layer)) == 0) return;
            if (!cameras.TryGetValue(camera, out var b))
            {
                b = new CameraBuffers
                {
                    visible = new GraphicsBuffer(GraphicsBuffer.Target.Append, data.instanceCount, 4),
                    args = new GraphicsBuffer(GraphicsBuffer.Target.IndirectArguments, 1, GraphicsBuffer.IndirectDrawIndexedArgs.size)
                };
                b.args.SetData(new[] { new GraphicsBuffer.IndirectDrawIndexedArgs {
                    indexCountPerInstance = bladeMesh.GetIndexCount(0), startIndex = bladeMesh.GetIndexStart(0), baseVertexIndex = bladeMesh.GetBaseVertex(0), instanceCount = 0, startInstance = 0 } });
                b.properties.SetBuffer("_Blades", source); b.properties.SetBuffer("_Visible", b.visible);
                cameras.Add(camera, b);
            }
            float vd = ViewDistance;
            GeometryUtility.CalculateFrustumPlanes(camera, planes);
            for (int i = 0; i < 6; i++) gpuPlanes[i] = new Vector4(planes[i].normal.x, planes[i].normal.y, planes[i].normal.z, planes[i].distance);
            compute.SetVectorArray("_Frustum", gpuPlanes);
            Vector3 cam = camera.transform.position;
            compute.SetVector("_CameraPosition", cam);
            compute.SetFloat("_ViewDistance", vd);
            compute.SetVector("_Falloff", new Vector4(vd * .35f, vd, FarKeep, 0f));
            // CPU chunk culling: distance, frustum, terrain horizon
            int nVis = 0;
            var ch = data.chunks;
            for (int i = 0; i < ch.Length; i++)
            {
                maskData[i] = 0;
                var bb = new Bounds(ch[i].centre, ch[i].extents * 2f);
                if (bb.SqrDistance(cam) > vd * vd || !GeometryUtility.TestPlanesAABB(planes, bb)) continue;
                if (occlusion && heights != null && Hidden(cam, ch[i].centre + new Vector3(0, ch[i].extents.y + .6f, 0))) continue;
                maskData[i] = 1; nVis++;
            }
            LastVisibleChunks = nVis;
            mask.SetData(maskData);
            b.visible.SetCounterValue(0);
            // re-bind every frame: a compute shader re-import (asset refresh in the editor) drops the instance's bindings
            compute.SetBuffer(kernel, "_Blades", source); compute.SetBuffer(kernel, "_Chunks", chunks); compute.SetBuffer(kernel, "_ChunkMask", mask);
            compute.SetInt("_ChunkCount", data.chunks.Length);
            compute.SetBuffer(kernel, "_Visible", b.visible);
            compute.Dispatch(kernel, data.chunks.Length, 1, 1);
            GraphicsBuffer.CopyCount(b.visible, b.args, 4);
            b.properties.SetFloat("_GrassTime", reviewTime >= 0 ? reviewTime : Time.realtimeSinceStartup);
            b.properties.SetVector("_GrassWind", new Vector4(windStrength, windSpeed, .84f, .54f));
            b.properties.SetFloat("_ViewDistance", vd);
            var rp = new RenderParams(ownedMaterial)
            {
                worldBounds = data.worldBounds, camera = camera, matProps = b.properties,
                shadowCastingMode = ShadowCastingMode.Off, receiveShadows = true, lightProbeUsage = LightProbeUsage.Off, layer = gameObject.layer
            };
            Graphics.RenderMeshIndirect(rp, bladeMesh, b.args);
        }

        public int LastVisibleChunks { get; private set; }

        float TerrainY(float x, float z)
        {
            float u = Mathf.Clamp01((x - heightWorld.x) / heightWorld.z) * (hfW - 1), v = Mathf.Clamp01((z - heightWorld.y) / heightWorld.w) * (hfH - 1);
            int x0 = (int)u, y0 = (int)v, x1 = Mathf.Min(x0 + 1, hfW - 1), y1 = Mathf.Min(y0 + 1, hfH - 1);
            float tx = u - x0, ty = v - y0;
            float a = Mathf.Lerp(heights[y0 * hfW + x0], heights[y0 * hfW + x1], tx), b = Mathf.Lerp(heights[y1 * hfW + x0], heights[y1 * hfW + x1], tx);
            return Mathf.Lerp(a, b, ty);
        }

        // a chunk is hidden when the terrain rises 0.8 m above the sight line from the camera to the chunk's top centre
        bool Hidden(Vector3 cam, Vector3 target)
        {
            Vector3 ray = target - cam;
            for (int s = 1; s < 10; s++)
            {
                Vector3 q = cam + ray * (s / 10f);
                if (TerrainY(q.x, q.z) > q.y + .8f) return true;
            }
            return false;
        }

        // review-only readback (never in a normal frame)
        public int ReadVisible(Camera camera)
        {
            if (!camera || !cameras.TryGetValue(camera, out var b)) return -1;
            var a = new GraphicsBuffer.IndirectDrawIndexedArgs[1]; b.args.GetData(a);
            return (int)a[0].instanceCount;
        }

        public void Release()
        {
            foreach (var pair in cameras) pair.Value.Dispose(); cameras.Clear();
            source?.Dispose(); source = null; chunks?.Dispose(); chunks = null; mask?.Dispose(); mask = null;
            Kill(compute); compute = null; Kill(ownedMaterial); ownedMaterial = null;
        }

        static void Kill(UnityEngine.Object o) { if (!o) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
