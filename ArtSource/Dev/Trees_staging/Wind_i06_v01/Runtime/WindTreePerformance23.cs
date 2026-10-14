using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using OnlyVolunteers.Sky22V04;

namespace OnlyVolunteers.Map.Wind
{
    // Temporary review harness; never saved in the map.
    public sealed class WindTreePerformance23 : MonoBehaviour
    {
        [Serializable] public sealed class Row { public string view;public bool after;public int samples,width,height,visibleGrass;public float medianMs,p95Ms,cpuMedianMs,gpuMedianMs; }
        [Serializable] public sealed class Result { public string scene,gpu,note;public Row[] rows; }
        public sealed class Binding {public Renderer renderer;public Material[] before,after;}
        Terrain terrain;TerrainData beforeData,afterData;TerrainCollider collider;
        Camera camera;RenderTexture target;Camera[] otherCameras;bool[] enabledStates;Binding[] bindings;
        Vector3[] poses;float[] yaws;string path;int phase,frame;bool running;
        readonly float[] times=new float[240],cpus=new float[240],gpus=new float[240];
        readonly FrameTiming[] timing=new FrameTiming[1];readonly Row[] rows=new Row[8];
        SkyClock22 clock;bool clockRunning;float oldHour;
        public void Begin(TerrainData original,Binding[] pairs,Vector3[] positions,float[] angles,string output)
        {
            terrain=Terrain.activeTerrain;collider=terrain.GetComponent<TerrainCollider>();beforeData=original;afterData=terrain.terrainData;bindings=pairs;poses=positions;yaws=angles;path=output;
            otherCameras=Camera.allCameras;enabledStates=otherCameras.Select(c=>c.enabled).ToArray();foreach(var c in otherCameras)c.enabled=false;
            clock=FindAnyObjectByType<SkyClock22>();if(clock){clockRunning=clock.Running;oldHour=clock.Hour;clock.Running=false;clock.SetHour(8);}
            camera=gameObject.AddComponent<Camera>();camera.fieldOfView=65;camera.nearClipPlane=.07f;camera.farClipPlane=650;
            target=new RenderTexture(1280,720,24,RenderTextureFormat.DefaultHDR);target.Create();camera.targetTexture=target;
            var data=gameObject.AddComponent<UniversalAdditionalCameraData>();data.renderPostProcessing=true;data.requiresDepthOption=CameraOverrideOption.On;data.requiresColorOption=CameraOverrideOption.On;
            running=true;SetPhase();
        }
        void SetPhase()
        {
            bool after=phase%2==1;var data=after?afterData:beforeData;terrain.terrainData=data;collider.terrainData=data;terrain.Flush();
            foreach(var b in bindings)if(b.renderer)b.renderer.sharedMaterials=after?b.after:b.before;
            var bounds=FindAnyObjectByType<FoliageBounds23>();if(bounds)bounds.Refresh();
            transform.SetPositionAndRotation(poses[phase/2],Quaternion.Euler(phase/2==1?-8:0,yaws[phase/2],0));frame=-120;
        }
        void Update()
        {
            if(!running)return;FrameTimingManager.CaptureFrameTimings();
            if(frame>=0&&frame<times.Length){times[frame]=Time.unscaledDeltaTime*1000;bool got=FrameTimingManager.GetLatestTimings(1,timing)>0;cpus[frame]=got?(float)timing[0].cpuFrameTime:0;gpus[frame]=got?(float)timing[0].gpuFrameTime:0;}
            if(++frame<times.Length)return;
            var st=(float[])times.Clone();var sc=(float[])cpus.Clone();var sg=(float[])gpus.Clone();Array.Sort(st);Array.Sort(sc);Array.Sort(sg);
            var grass=FindAnyObjectByType<ChunkedGrassRenderer24>();if(grass)grass.ReadStats(camera);
            rows[phase]=new Row{view=new[]{"Hamlet","Forest","Beach","Rough"}[phase/2],after=phase%2==1,samples=times.Length,width=camera.pixelWidth,height=camera.pixelHeight,medianMs=st[120],p95Ms=st[228],cpuMedianMs=sc[120],gpuMedianMs=sg[120],visibleGrass=grass?grass.LastVisibleInstances:0};
            if(++phase<rows.Length){SetPhase();return;}
            File.WriteAllText(path,JsonUtility.ToJson(new Result{scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,gpu=SystemInfo.graphicsDeviceName,note="i05 tree bindings vs i06 shared wind bindings, same i06 scene and grass. 120 warm-up + 240 ordinary Play frames per cell; 08:00 fixed. Includes Editor/gameplay and shared bounds helper overhead in both cases. CPU/GPU zero = unavailable.",rows=rows},true));
            Debug.Log("G23_WIND_PERFORMANCE_COMPLETE "+path);Restore();Destroy(gameObject);
        }
        void Restore()
        {
            if(!running)return;running=false;if(terrain){terrain.terrainData=afterData;collider.terrainData=afterData;terrain.Flush();}
            foreach(var b in bindings)if(b.renderer)b.renderer.sharedMaterials=b.after;
            for(int i=0;i<otherCameras.Length;i++)if(otherCameras[i])otherCameras[i].enabled=enabledStates[i];
            if(clock){clock.SetHour(oldHour);clock.Running=clockRunning;}
            if(target){camera.targetTexture=null;target.Release();Destroy(target);}
        }
        void OnDisable(){Restore();}void OnDestroy(){Restore();}
    }
}
