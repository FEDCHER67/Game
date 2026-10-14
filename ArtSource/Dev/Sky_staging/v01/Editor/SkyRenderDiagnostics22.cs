using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22.Editor
{
    public static class SkyRenderDiagnostics22
    {
        public static string Run(string revision="v01")
        {
            SkyReviewBuilder22.RequireLock();
            var shader=Shader.Find("OnlyVolunteers/Sky22/Painted Sky v01");
            if(!shader || !shader.isSupported || ShaderUtil.ShaderHasError(shader))throw new Exception("Sky shader unavailable or failed compilation.");
            var camera=Camera.main;var clock=Object.FindAnyObjectByType<SkyClock22>();var sky=Object.FindAnyObjectByType<SkyRenderer22>();
            if(!camera || !clock || !sky)throw new Exception("Open Sky_Test first.");
            var target=camera.targetTexture;var oldActive=RenderTexture.active;
            var beforeSky=RenderSettings.skybox;var beforeSun=RenderSettings.sun;
            var beforeFog=RenderSettings.fogColor;var beforeAmbient=RenderSettings.ambientSkyColor;
            var beforeMode=RenderSettings.ambientMode;float beforeEnd=RenderSettings.fogEndDistance;
            var lights=sky.GetComponentsInChildren<Light>(true);var rotations=new Quaternion[lights.Length];var intensities=new float[lights.Length];var enabled=new bool[lights.Length];
            for(int i=0;i<lights.Length;i++){rotations[i]=lights[i].transform.rotation;intensities[i]=lights[i].intensity;enabled[i]=lights[i].enabled;}
            var rt=new RenderTexture(960,540,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            float hour=clock.Hour;var mood=sky.Mood;var output=new StringBuilder();
            try
            {
                rt.Create();camera.targetTexture=rt;
                for(int phase=0;phase<4;phase++)
                {
                    clock.SetHour(phase==0?0:phase==1?6:phase==2?12:19);
                    sky.Mood=phase==2?SkyMood22.Rough:SkyMood22.Hamlet;
                    camera.Render();
                    if(RenderSettings.skybox!=beforeSky || RenderSettings.sun!=beforeSun || RenderSettings.fogColor!=beforeFog ||
                        RenderSettings.ambientSkyColor!=beforeAmbient || RenderSettings.ambientMode!=beforeMode || RenderSettings.fogEndDistance!=beforeEnd)
                        throw new Exception("Global atmosphere was not restored after camera "+phase);
                    for(int i=0;i<lights.Length;i++)if(Quaternion.Angle(rotations[i],lights[i].transform.rotation)>.001f ||
                        lights[i].intensity!=intensities[i] || lights[i].enabled!=enabled[i])throw new Exception("Light state leaked after rendering.");
                    output.AppendLine("PASS: camera restoration at hour "+clock.Hour);
                }
                if(ShaderUtil.ShaderHasError(shader))throw new Exception("Shader failed after first real render.");
                output.AppendLine("PASS: supported sky shader; no ShaderUtil errors after rendering");
                output.AppendLine("Unity="+Application.unityVersion+"; renderer="+SystemInfo.graphicsDeviceName+"; API="+SystemInfo.graphicsDeviceType);
                string file="Working/Reviews/Sky/render_diagnostics_"+revision+".txt";Directory.CreateDirectory(Path.GetDirectoryName(file));
                using(var w=new StreamWriter(new FileStream(file,FileMode.CreateNew)))w.Write(output.ToString());return file;
            }
            finally {camera.targetTexture=target;RenderTexture.active=oldActive;clock.SetHour(hour);sky.Mood=mood;rt.Release();Object.DestroyImmediate(rt);}
        }
    }
}
