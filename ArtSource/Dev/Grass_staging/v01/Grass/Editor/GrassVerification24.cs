using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEditor;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Grass.Editor
{
    public static class GrassVerification24
    {
        public static string ShaderStatus(string revision="v01")
        {
            var shader=Shader.Find("OnlyVolunteers/Grass/MB_TallGrass24");if(!shader)throw new Exception("Grass shader missing");
            var flags=System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Public;
            var codeMethod=typeof(ShaderUtil).GetMethod("GetSRPBatcherCompatibilityCode",flags);
            var reasonMethod=typeof(ShaderUtil).GetMethod("GetSRPBatcherCompatibilityIssueReason",flags);
            int code=codeMethod!=null?(int)codeMethod.Invoke(null,new object[]{shader,0}):-999;
            string reason=code>0&&reasonMethod!=null?(string)reasonMethod.Invoke(null,new object[]{shader,0,code}):"Unavailable or compatible";
            var errors=ShaderUtil.GetShaderMessages(shader).Where(m=>m.severity.ToString()=="Error").Select(m=>m.message).ToArray();
            string report=$"supported={shader.isSupported}; SRPBatcherCompatibilityCode={code}; reason={reason}; globalSRPBatcher={UnityEngine.Rendering.GraphicsSettings.useScriptableRenderPipelineBatching}; shaderErrors={errors.Length}\n"+string.Join("\n",errors);
            string path=GrassReview24.Output+"/shader_status_"+revision+".txt";if(File.Exists(path))throw new IOException("Shader status revision exists");File.WriteAllText(path,report);
            if(!shader.isSupported||errors.Length>0||code==0||!UnityEngine.Rendering.GraphicsSettings.useScriptableRenderPipelineBatching)throw new Exception(report);
            return report;
        }
        public static string GpuCulling()
        {
            var asset=AssetDatabase.LoadAssetAtPath<ComputeShader>(GrassPlacement24.Vendor+"/GrassVisibility24.compute");
            var shader=Object.Instantiate(asset);var go=new GameObject("G24_CullTestRuntimeOnly"){hideFlags=HideFlags.HideAndDontSave};
            GraphicsBuffer source=null,chunks=null,visible=null,count=null;
            try
            {
                var camera=go.AddComponent<Camera>();camera.enabled=false;camera.nearClipPlane=.1f;camera.farClipPlane=40;camera.aspect=1;camera.fieldOfView=60;
                camera.transform.position=new Vector3(0,.5f,0);
                var blades=new[]{B(0,0,2),B(1,0,8),B(30,0,8),B(0,0,-20),B(0,0,55),B(0,0,20),B(-1,0,9)};
                // A giant chunk encloses the complete frustum (no corners inside): upstream's test rejected it.
                var cells=new[]{new GrassPatchData24.Chunk{centre=new Vector3(0,0,10),extents=Vector3.one*80,start=0,count=5},
                    new GrassPatchData24.Chunk{centre=new Vector3(0,0,15),extents=new Vector3(3,2,7),start=5,count=2}};
                source=new GraphicsBuffer(GraphicsBuffer.Target.Structured,blades.Length,32);source.SetData(blades);
                chunks=new GraphicsBuffer(GraphicsBuffer.Target.Structured,cells.Length,32);chunks.SetData(cells);
                visible=new GraphicsBuffer(GraphicsBuffer.Target.Append,blades.Length,4);count=new GraphicsBuffer(GraphicsBuffer.Target.Raw,1,4);
                int kernel=shader.FindKernel("ChunkRender");shader.SetBuffer(kernel,"_Blades",source);shader.SetBuffer(kernel,"_Chunks",chunks);shader.SetBuffer(kernel,"_Visible",visible);
                var planes=GeometryUtility.CalculateFrustumPlanes(camera);shader.SetVectorArray("_Frustum",planes.Select(p=>new Vector4(p.normal.x,p.normal.y,p.normal.z,p.distance)).ToArray());
                shader.SetVector("_CameraPosition",camera.transform.position);shader.SetFloat("_ViewDistance",40);shader.SetInt("_ChunkCount",cells.Length);
                visible.SetCounterValue(0);shader.Dispatch(kernel,cells.Length,1,1);GraphicsBuffer.CopyCount(visible,count,0);
                var n=new uint[1];count.GetData(n);var actual=new uint[n[0]];if(actual.Length>0)visible.GetData(actual,0,0,actual.Length);
                var expected=new uint[]{0,1,5,6};Array.Sort(actual);
                if(!actual.SequenceEqual(expected))throw new Exception("GPU culling mismatch: "+string.Join(",",actual));
                return "PASS: camera-inside-chunk intersection; frustum + distance rejection; exact chunk tails (5 + 2); no duplicate IDs; visible=0,1,5,6";
            }
            finally{source?.Dispose();chunks?.Dispose();visible?.Dispose();count?.Dispose();Object.DestroyImmediate(shader);Object.DestroyImmediate(go);}
        }
        static ChunkedGrassRenderer24.Blade B(float x,float y,float z)=>new(){positionHeight=new Vector4(x,y,z,.8f),shape=new Vector4(1,0,.1f,.8f)};
        public static string Placement(string revision="v01")
        {
            var grass=Object.FindAnyObjectByType<ChunkedGrassRenderer24>();var ground=Object.FindAnyObjectByType<MapHeightSampler>();
            if(!grass||!ground)throw new InvalidOperationException("Need installed G24 scene");
            var data=grass.data;var bytes=data.instances.bytes;
            if(bytes.Length!=data.instanceCount*32)throw new Exception("Invalid payload length");
            uint next=0;foreach(var chunk in data.chunks){if(chunk.start!=next||chunk.count==0)throw new Exception("Invalid chunk ranges");next+=chunk.count;}
            if(next!=data.instanceCount)throw new Exception("Chunk counts do not cover data");
            var mask=GrassExclusion24.Build(ground.Terrain);int hard=0,water=0,outside=0,invalidHeight=0;float maxGroundError=0,minHeight=10,maxHeight=0;
            var td=ground.Terrain.terrainData;var origin=ground.Terrain.transform.position;int sampled=0;
            using(var r=new BinaryReader(new MemoryStream(bytes,false)))for(int i=0;i<data.instanceCount;i++)
            {
                float x=r.ReadSingle(),y=r.ReadSingle(),z=r.ReadSingle(),h=r.ReadSingle();r.BaseStream.Position+=16;
                minHeight=Mathf.Min(minHeight,h);maxHeight=Mathf.Max(maxHeight,h);
                if(h<.099f||h>.901f)invalidHeight++;
                if(!data.worldBounds.Contains(new Vector3(x,y,z)))outside++;
                // Every blade must pass the hard surface mask, not just the sampled centres.
                if(mask.Distance(x,z)<.75f)hard++;
                if(i%19!=0)continue;sampled++;
                float actual=td.GetInterpolatedHeight((x-origin.x)/td.size.x,(z-origin.z)/td.size.z)+origin.y-.015f;
                maxGroundError=Mathf.Max(maxGroundError,Mathf.Abs(actual-y));if(ground.InWater(x,z,out _))water++;
            }
            string result=$"instances={data.instanceCount}; chunks={data.chunks.Length}; heights={minHeight:F3}..{maxHeight:F3}; hardSurfaceViolations={hard}; outsideBounds={outside}; badHeight={invalidHeight}; sampledWaterViolations={water}/{sampled}; maxGroundError={maxGroundError:F5}m; terrainLowDetails={td.detailPrototypes.Length}; bladeTriangles={grass.bladeMesh.GetIndexCount(0)/3}";
            bool pass=hard==0&&outside==0&&water==0&&invalidHeight==0&&maxGroundError<.01f&&td.detailPrototypes.Length>0;
            string path=GrassReview24.Output+"/placement_audit_"+revision+".txt";if(File.Exists(path))throw new IOException("Audit revision exists");File.WriteAllText(path,(pass?"PASS ":"FAIL ")+result);
            if(!pass)throw new Exception(result);return "PASS "+result;
        }
    }
}
