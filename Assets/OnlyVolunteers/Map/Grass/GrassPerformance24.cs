using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;

namespace OnlyVolunteers.Map.Grass
{
    // Explicitly started review harness. Never saved in a scene or enabled during ordinary play.
    public sealed class GrassPerformance24 : MonoBehaviour
    {
        [Serializable] public sealed class Row
        {
            public string location;public bool tallGrass;public int samples,width,height;
            public float medianMs,p95Ms,meanMs,cpuMedianMs,gpuMedianMs;
            public int visibleInstances,candidateChunks,totalInstances,totalChunks;
            public string culling;
        }
        [Serializable] public sealed class Result
        { public string scene,gpu,unity,note;public Row[] rows; }
        ChunkedGrassRenderer24 grass;
        Camera camera;Camera[] others;bool[] enabledStates;
        Vector3[] positions;float[] yaws;
        string output;int phase,frames;bool running,oldSuppress;
        readonly float[] times=new float[180],cpu=new float[180],gpu=new float[180];
        readonly FrameTiming[] timing=new FrameTiming[1];
        readonly Row[] rows=new Row[4];
        public void Begin(ChunkedGrassRenderer24 renderer,Vector3 hamlet,float hamletYaw,Vector3 hill,float hillYaw,string path)
        {
            grass=renderer;oldSuppress=grass.suppressDrawing;positions=new[]{hamlet,hill};yaws=new[]{hamletYaw,hillYaw};output=path;
            others=Camera.allCameras;enabledStates=others.Select(c=>c.enabled).ToArray();foreach(var c in others)c.enabled=false;
            gameObject.tag="MainCamera";
            camera=gameObject.AddComponent<Camera>();camera.fieldOfView=65;camera.nearClipPlane=.07f;camera.farClipPlane=650;
            var data=gameObject.AddComponent<UniversalAdditionalCameraData>();data.renderPostProcessing=true;data.requiresDepthOption=CameraOverrideOption.On;data.requiresColorOption=CameraOverrideOption.On;
            running=true;SetPhase();
        }
        void SetPhase()
        {frames=-60;grass.suppressDrawing=phase%2==0;transform.SetPositionAndRotation(positions[phase/2],Quaternion.Euler(4,yaws[phase/2],0));}
        void Update()
        {
            if(!running)return;
            FrameTimingManager.CaptureFrameTimings();
            if(frames>=0&&frames<times.Length)
            {
                times[frames]=Time.unscaledDeltaTime*1000;
                bool available=FrameTimingManager.GetLatestTimings(1,timing)>0;
                cpu[frames]=available?(float)timing[0].cpuFrameTime:0;gpu[frames]=available?(float)timing[0].gpuFrameTime:0;
            }
            frames++;if(frames<times.Length)return;
            var sorted=(float[])times.Clone();Array.Sort(sorted);var sc=(float[])cpu.Clone();Array.Sort(sc);var sg=(float[])gpu.Clone();Array.Sort(sg);
            bool after=phase%2==1;string stats=after?grass.ReadStats(camera):"suppressed";
            rows[phase]=new Row{location=phase<2?"Hamlet":"Between districts",tallGrass=after,samples=times.Length,width=camera.pixelWidth,height=camera.pixelHeight,
                medianMs=sorted[sorted.Length/2],p95Ms=sorted[(int)(sorted.Length*.95f)],meanMs=times.Average(),cpuMedianMs=sc[sc.Length/2],gpuMedianMs=sg[sg.Length/2],
                visibleInstances=after?grass.LastVisibleInstances:0,candidateChunks=after?grass.LastCandidateChunks:0,totalInstances=grass.TotalInstances,totalChunks=grass.TotalChunks,culling=stats};
            phase++;if(phase<4){SetPhase();return;}
            var result=new Result{scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,gpu=SystemInfo.graphicsDeviceName,unity=Application.unityVersion,
                note="Live Play frames; 60 warm-up + 180 samples per cell. Editor workload and existing gameplay are included. CPU/GPU zero means FrameTimingManager unavailable. No background or quality settings changed.",rows=rows};
            File.WriteAllText(output,JsonUtility.ToJson(result,true));Debug.Log("G24_PERFORMANCE_COMPLETE "+output);Restore();Destroy(gameObject);
        }
        void Restore(){if(!running)return;running=false;if(grass)grass.suppressDrawing=oldSuppress;for(int i=0;i<others.Length;i++)if(others[i])others[i].enabled=enabledStates[i];}
        void OnDisable(){Restore();}
        void OnDestroy(){Restore();}
    }
}
