using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.Sky22V04;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;

namespace OnlyVolunteers.Trees
{
    // Temporary measurement component, never saved into a scene or prefab.
    public sealed class G23MassBenchmarkI08 : MonoBehaviour
    {
        [Serializable] public sealed class Row { public string view; public int samples,visibleGrass; public float medianMs,p95Ms,cpuMedianMs,gpuMedianMs,fps; }
        [Serializable] public sealed class Result { public string scene,gpu,note; public int width=1280,height=720; public Row[] rows; }
        public static readonly string[] Views={"Hamlet orchard","Poplar road","Beach palms","Garden bushes"};
        public static readonly Vector4[] Poses={new(261,469,30,-3),new(316,332,27,-8),new(844,225,157,-7),new(294,512,328,4)};
        Camera camera;RenderTexture target;Camera[] otherCameras;bool[] enabledStates;SkyClock22 clock;bool oldRunning;float oldHour;
        Vector3[] positions;string path;int phase,frame;bool running;
        readonly float[] times=new float[240],cpus=new float[240],gpus=new float[240];
        readonly FrameTiming[] timings=new FrameTiming[1];readonly Row[] rows=new Row[4];
        public void Begin(Vector3[] points,string output)
        {
            positions=points;path=output;otherCameras=Camera.allCameras;enabledStates=otherCameras.Select(c=>c.enabled).ToArray();foreach(var c in otherCameras)c.enabled=false;
            clock=FindAnyObjectByType<SkyClock22>();if(clock){oldRunning=clock.Running;oldHour=clock.Hour;clock.Running=false;clock.SetHour(8);}
            camera=gameObject.AddComponent<Camera>();camera.fieldOfView=65;camera.nearClipPlane=.07f;camera.farClipPlane=650;
            target=new RenderTexture(1280,720,24,RenderTextureFormat.DefaultHDR);target.Create();camera.targetTexture=target;
            var data=gameObject.AddComponent<UniversalAdditionalCameraData>();data.renderPostProcessing=true;data.requiresDepthOption=CameraOverrideOption.On;data.requiresColorOption=CameraOverrideOption.On;
            running=true;SetPose();
        }
        void SetPose(){var p=Poses[phase];transform.SetPositionAndRotation(positions[phase],Quaternion.Euler(p.w,p.z,0));frame=-120;}
        void Update()
        {
            if(!running)return;FrameTimingManager.CaptureFrameTimings();
            if(frame>=0&&frame<times.Length){times[frame]=Time.unscaledDeltaTime*1000;bool got=FrameTimingManager.GetLatestTimings(1,timings)>0;cpus[frame]=got?(float)timings[0].cpuFrameTime:0;gpus[frame]=got?(float)timings[0].gpuFrameTime:0;}
            if(++frame<times.Length)return;
            var a=(float[])times.Clone();var b=(float[])cpus.Clone();var c=(float[])gpus.Clone();Array.Sort(a);Array.Sort(b);Array.Sort(c);
            var grass=FindAnyObjectByType<ChunkedGrassRenderer24>();if(grass)grass.ReadStats(camera);
            rows[phase]=new Row{view=Views[phase],samples=times.Length,visibleGrass=grass?grass.LastVisibleInstances:0,medianMs=a[120],p95Ms=a[228],cpuMedianMs=b[120],gpuMedianMs=c[120],fps=1000/a[120]};
            if(++phase<4){SetPose();return;}
            File.WriteAllText(path,JsonUtility.ToJson(new Result{scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,gpu=SystemInfo.graphicsDeviceName,
                note="Actual named Play scene; matched four camera poses, 1280x720 HDR, 08:00. 120 warmup + 240 normal frames per view. Whole-scene Editor frame times; GPU zero means unavailable. runInBackground and project settings untouched.",rows=rows},true));
            Debug.Log("G23_LEAFY_BENCHMARK_COMPLETE "+path);Restore();Destroy(gameObject);
        }
        void Restore()
        {
            if(!running)return;running=false;
            for(int i=0;i<otherCameras.Length;i++)if(otherCameras[i])otherCameras[i].enabled=enabledStates[i];
            if(clock){clock.SetHour(oldHour);clock.Running=oldRunning;}
            if(target){camera.targetTexture=null;target.Release();Destroy(target);}
        }
        void OnDisable(){Restore();}void OnDestroy(){Restore();}
    }
}
