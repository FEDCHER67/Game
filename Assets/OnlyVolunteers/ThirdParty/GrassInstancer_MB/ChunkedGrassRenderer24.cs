// Adapted from Unity Grass Instancer, approach 3, by MangoButtermilch (2022).
// MIT; full notice in LICENSE.txt. Pinned source and modification map: PORT_NOTES.md.
using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;
using OnlyVolunteers.Map.Grass;

namespace OnlyVolunteers.ThirdParty.GrassInstancerMB
{
    [ExecuteAlways]
    public sealed class ChunkedGrassRenderer24 : MonoBehaviour
    {
        [StructLayout(LayoutKind.Sequential)]
        public struct Blade { public Vector4 positionHeight, shape; }
        public GrassPatchData24 data;
        public Mesh bladeMesh;
        public Material material;
        public ComputeShader visibility;
        [Range(30, 300)] public float viewDistance = 150;
        [Range(0, 1)] public float windStrength = .24f;
        public float windSpeed = 1.25f;
        [NonSerialized] public float reviewTime = -1;
        [NonSerialized] public bool suppressDrawing;
        public int TotalInstances => data ? data.instanceCount : 0;
        public int TotalChunks => data && data.chunks != null ? data.chunks.Length : 0;
        public int LastCandidateChunks { get; private set; }
        public int LastVisibleInstances { get; private set; }
        public string LastCamera { get; private set; }
        public int LiveCameraBuffers => cameras.Count;
        public bool IsReady => source != null;

        GraphicsBuffer source, chunks;
        ComputeShader compute;
        Material ownedMaterial;
        int kernel;
        readonly Plane[] planes = new Plane[6];
        readonly Vector4[] gpuPlanes = new Vector4[6];
        readonly Dictionary<Camera, CameraBuffers> cameras = new();
        readonly List<Camera> deadCameras = new();

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
            // Capture cameras are short-lived. Do not retain their GPU resources indefinitely.
            deadCameras.Clear();
            foreach (var pair in cameras) if (!pair.Key) deadCameras.Add(pair.Key);
            foreach (var camera in deadCameras) { cameras[camera].Dispose(); cameras.Remove(camera); }
        }

        bool Prepare()
        {
            if (source != null) return true;
            if (!data || !data.instances || data.instanceCount <= 0 || !bladeMesh || !material || !visibility) return false;
            if (!SystemInfo.supportsComputeShaders || !SystemInfo.supportsInstancing) return false;
            byte[] bytes = data.instances.bytes;
            if (bytes.Length != data.instanceCount * 32) throw new InvalidDataException("G24 instance payload length mismatch");
            var blades = new Blade[data.instanceCount];
            using (var reader = new BinaryReader(new MemoryStream(bytes, false)))
                for (int i = 0; i < blades.Length; i++)
                {
                    blades[i].positionHeight = new Vector4(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                    blades[i].shape = new Vector4(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                }
            try
            {
                source = new GraphicsBuffer(GraphicsBuffer.Target.Structured, blades.Length, 32); source.SetData(blades);
                chunks = new GraphicsBuffer(GraphicsBuffer.Target.Structured, data.chunks.Length, 32); chunks.SetData(data.chunks);
                compute = Instantiate(visibility); compute.hideFlags = HideFlags.HideAndDontSave;
                ownedMaterial = new Material(material) { enableInstancing = true, hideFlags = HideFlags.HideAndDontSave };
                kernel = compute.FindKernel("ChunkRender");
                compute.SetBuffer(kernel,"_Blades",source); compute.SetBuffer(kernel,"_Chunks",chunks);
                compute.SetInt("_ChunkCount",data.chunks.Length);
                return true;
            }
            catch { Release(); throw; }
        }

        void Render(ScriptableRenderContext context, Camera camera)
        {
            if (suppressDrawing || !camera || camera.cameraType == CameraType.Preview || camera.cameraType == CameraType.Reflection || !Prepare()) return;
            if ((camera.cullingMask & (1 << gameObject.layer)) == 0) return;
            if (!cameras.TryGetValue(camera, out var buffers))
            {
                buffers = new CameraBuffers();
                buffers.visible = new GraphicsBuffer(GraphicsBuffer.Target.Append, data.instanceCount, 4);
                buffers.args = new GraphicsBuffer(GraphicsBuffer.Target.IndirectArguments, 1, GraphicsBuffer.IndirectDrawIndexedArgs.size);
                buffers.args.SetData(new[] { new GraphicsBuffer.IndirectDrawIndexedArgs {
                    indexCountPerInstance=bladeMesh.GetIndexCount(0), startIndex=bladeMesh.GetIndexStart(0),
                    baseVertexIndex=bladeMesh.GetBaseVertex(0), instanceCount=0, startInstance=0 } });
                buffers.properties.SetBuffer("_Blades",source); buffers.properties.SetBuffer("_Visible",buffers.visible);
                cameras.Add(camera,buffers);
            }
            GeometryUtility.CalculateFrustumPlanes(camera,planes);
            for (int i=0;i<6;i++) gpuPlanes[i]=new Vector4(planes[i].normal.x,planes[i].normal.y,planes[i].normal.z,planes[i].distance);
            compute.SetVectorArray("_Frustum",gpuPlanes);
            compute.SetVector("_CameraPosition",camera.transform.position);
            compute.SetFloat("_ViewDistance",viewDistance);
            buffers.visible.SetCounterValue(0);
            compute.SetBuffer(kernel,"_Visible",buffers.visible);
            compute.Dispatch(kernel,data.chunks.Length,1,1);
            GraphicsBuffer.CopyCount(buffers.visible,buffers.args,4);
            buffers.properties.SetFloat("_GrassTime",reviewTime >= 0 ? reviewTime : Time.realtimeSinceStartup);
            buffers.properties.SetVector("_GrassWind",new Vector4(windStrength,windSpeed,.84f,.54f));
            buffers.properties.SetFloat("_ViewDistance",viewDistance);
            var render = new RenderParams(ownedMaterial) {
                worldBounds=data.worldBounds, camera=camera, matProps=buffers.properties,
                shadowCastingMode=ShadowCastingMode.Off, receiveShadows=true,
                lightProbeUsage=LightProbeUsage.Off, layer=gameObject.layer };
            Graphics.RenderMeshIndirect(render,bladeMesh,buffers.args);
            LastCamera=camera.name;
        }

        // Explicit review-only readback. Never blocks a normal gameplay frame.
        public string ReadStats(Camera camera)
        {
            if (!camera || !cameras.TryGetValue(camera,out var buffers)) return "No rendered camera buffer";
            var args = new GraphicsBuffer.IndirectDrawIndexedArgs[1]; buffers.args.GetData(args);
            LastVisibleInstances=(int)args[0].instanceCount;
            GeometryUtility.CalculateFrustumPlanes(camera,planes); LastCandidateChunks=0;
            foreach(var chunk in data.chunks)
            {
                var b=new Bounds(chunk.centre,chunk.extents*2);
                if (b.SqrDistance(camera.transform.position)<=viewDistance*viewDistance && GeometryUtility.TestPlanesAABB(planes,b)) LastCandidateChunks++;
            }
            return $"total={TotalInstances}; visible={LastVisibleInstances}; chunks={LastCandidateChunks}/{TotalChunks}; culled={TotalInstances-LastVisibleInstances}; distance={viewDistance}; occlusion=disabled";
        }
        public void Release()
        {
            foreach(var pair in cameras) pair.Value.Dispose(); cameras.Clear();
            source?.Dispose(); source=null; chunks?.Dispose(); chunks=null;
            DisposeObject(compute); compute=null; DisposeObject(ownedMaterial); ownedMaterial=null;
        }
        static void DisposeObject(UnityEngine.Object obj)
        { if(!obj)return; if(Application.isPlaying) Destroy(obj); else DestroyImmediate(obj); }
    }
}
