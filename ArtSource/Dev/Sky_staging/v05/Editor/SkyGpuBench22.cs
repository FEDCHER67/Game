using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22V05.Editor
{
    // Unique GPU markers surround the real sky shader draw only. No global pipeline settings change.
    // Eight full-screen cube draws amplify sub-ms timings; reported time is divided by eight.
    public static class SkyGpuBench22
    {
        const int Draws=8;
        static readonly int[] Steps={64,48,32,64,48,32};
        static Material[] materials;static CommandBuffer[] commands;static Recorder[] recorders;
        static List<double>[] measurements;static RenderTexture target;
        static int frames,lastFrame;static double deadline;
        public static bool Finished {get;private set;}
        public static string Failure {get;private set;}
        public static void Start()
        {
            SkyReviewBuilder22.RequireLock();
            if(!EditorApplication.isPlaying)throw new Exception("GPU benchmark requires normal Play frames.");
            if(!SystemInfo.supportsGpuRecorder)throw new Exception("GPU recorder unsupported; do not substitute CPU timings.");
            if(File.Exists("Working/Reviews/Sky/gpu_sky_v05.csv"))throw new IOException("GPU evidence already exists.");
            Finished=false;Failure=null;frames=0;lastFrame=-1;deadline=EditorApplication.timeSinceStartup+120;
            var primitive=GameObject.CreatePrimitive(PrimitiveType.Cube);primitive.SetActive(false);
            Mesh cube=primitive.GetComponent<MeshFilter>().sharedMesh;Object.DestroyImmediate(primitive);
            target=new RenderTexture(1920,1080,24,RenderTextureFormat.RGB111110Float){name="G22 temporary sky GPU target"};target.Create();
            materials=new Material[6];commands=new CommandBuffer[6];recorders=new Recorder[6];measurements=new List<double>[6];
            Matrix4x4 view=Camera.main.worldToCameraMatrix;view.m03=view.m13=view.m23=0;
            Matrix4x4 projection=GL.GetGPUProjectionMatrix(Matrix4x4.Perspective(70,1920f/1080f,.1f,1500),true);
            for(int i=0;i<6;i++)
            {
                var mood=SkyMood22.Hamlet;if(i>=3){mood.cloudCover=.97f;mood.gloom=.52f;}
                var state=SkyModel22.Evaluate(12,mood);
                var material=new Material(Shader.Find("OnlyVolunteers/Sky22V05/Painted Sky v05")){hideFlags=HideFlags.HideAndDontSave};materials[i]=material;
                material.SetColor("_Zenith",state.zenith);material.SetColor("_Horizon",state.horizon);material.SetColor("_CloudTop",state.cloudTop);material.SetColor("_CloudBase",state.cloudBase);
                material.SetColor("_SunColour",state.sunlight);material.SetColor("_MoonColour",state.moonlight);material.SetVector("_SunDirection",state.sunDirection);material.SetVector("_MoonDirection",state.moonDirection);
                material.SetFloat("_Cover",mood.cloudCover);material.SetFloat("_Gloom",mood.gloom);material.SetFloat("_Stars",state.stars);material.SetFloat("_Golden",state.golden);material.SetFloat("_Daylight",state.daylight);
                material.SetFloat("_CloudTime",650*.15f);material.SetFloat("_CloudScale",1);material.SetFloat("_Steps",Steps[i]);
                string label="G22 sky GPU "+(i<3?"fair ":"overcast ")+Steps[i];
                var sampler=CustomSampler.Create(label,true);var recorder=sampler.GetRecorder();recorder.enabled=true;recorders[i]=recorder;measurements[i]=new List<double>();
                var cmd=new CommandBuffer{name=label};commands[i]=cmd;cmd.SetRenderTarget(target);cmd.SetViewport(new Rect(0,0,1920,1080));cmd.ClearRenderTarget(true,true,Color.black);
                cmd.SetViewProjectionMatrices(view,projection);cmd.BeginSample(sampler);
                for(int draw=0;draw<Draws;draw++)cmd.DrawMesh(cube,Matrix4x4.identity,material,0,0);
                cmd.EndSample(sampler);
            }
            EditorApplication.update+=Update;
        }
        static void Update()
        {
            try
            {
                SkyReviewBuilder22.RequireLock();
                if(!EditorApplication.isPlaying)throw new Exception("Play stopped before GPU timing completed.");
                if(EditorApplication.timeSinceStartup>deadline)throw new Exception("GPU measurement timed out.");
                if(Time.frameCount==lastFrame)return;lastFrame=Time.frameCount;frames++;
                for(int i=0;i<6;i++)
                {
                    if(frames>24 && recorders[i].gpuSampleBlockCount>0 && recorders[i].gpuElapsedNanoseconds>0)
                        measurements[i].Add(recorders[i].gpuElapsedNanoseconds/1000000.0/recorders[i].gpuSampleBlockCount/Draws);
                    Graphics.ExecuteCommandBuffer(commands[i]);
                }
                if(frames>=104)
                {
                    var previous=RenderTexture.active;var probe=new Texture2D(1920,1080,TextureFormat.RGB24,false);
                    try
                    {
                        RenderTexture.active=target;probe.ReadPixels(new Rect(0,0,1920,1080),0,0);probe.Apply();
                        if(probe.GetPixel(960,540).maxColorComponent<.01f)throw new Exception("GPU benchmark target was black; timings invalid.");
                        using(var f=new FileStream("Working/Reviews/Sky/gpu_shader_target_v05.png",FileMode.CreateNew)){var bytes=probe.EncodeToPNG();f.Write(bytes,0,bytes.Length);}
                    }
                    finally {RenderTexture.active=previous;Object.DestroyImmediate(probe);}
                    var csv=new StringBuilder("weather,steps,samples,mean_gpu_ms,median_gpu_ms,p95_gpu_ms\n");
                    for(int i=0;i<6;i++)
                    {
                        var values=measurements[i];if(values.Count<30)throw new Exception("Insufficient valid GPU samples for case "+i);
                        values.Sort();double sum=0;foreach(double value in values)sum+=value;
                        csv.AppendLine((i<3?"fair":"overcast")+","+Steps[i]+","+values.Count+","+(sum/values.Count).ToString("F6",CultureInfo.InvariantCulture)+","+values[values.Count/2].ToString("F6",CultureInfo.InvariantCulture)+","+values[(int)((values.Count-1)*.95)].ToString("F6",CultureInfo.InvariantCulture));
                    }
                    using(var w=new StreamWriter(new FileStream("Working/Reviews/Sky/gpu_sky_v05.csv",FileMode.CreateNew)))w.Write(csv.ToString());
                    using(var w=new StreamWriter(new FileStream("Working/Reviews/Sky/gpu_method_v05.txt",FileMode.CreateNew)))w.Write("GPU="+SystemInfo.graphicsDeviceName+"; API="+SystemInfo.graphicsDeviceType+"\n1920x1080 RGB111110Float + depth24, full-screen sky shader only, cube geometry, no terrain/post-processing; no CPU time substitution.\nUnique CustomSampler GPU markers, 8 repeated draws per sample divided by 8; 24 warmup frames, then 80 measured normal Play frames; three-frame GPU readback delay excluded by warmup.\nClock and mood frozen at noon; fair .28 / overcast .97; same view, wind phase and shader as captures. This measures isolated full-screen sky shader cost, not whole-game frame time.\n");
                    Cleanup();Finished=true;
                }
            }
            catch(Exception e){Failure=e.ToString();Cleanup();Finished=true;Debug.LogException(e);}
        }
        static void Cleanup()
        {
            EditorApplication.update-=Update;
            if(recorders!=null)foreach(var r in recorders)if(r!=null)r.enabled=false;
            if(commands!=null)foreach(var c in commands)c?.Release();
            if(materials!=null)foreach(var m in materials)if(m)Object.DestroyImmediate(m);
            if(target){target.Release();Object.DestroyImmediate(target);}target=null;
        }
    }
}
