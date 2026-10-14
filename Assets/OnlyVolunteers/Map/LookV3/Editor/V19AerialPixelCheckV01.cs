using System;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19AerialPixelCheckV01
    {
        public static string Run(string revision="v01", bool g22=false)
        {
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>();
            var previous=RenderTexture.active;
            var cameraObject=new GameObject("G18g transient pixel probe"){hideFlags=HideFlags.HideAndDontSave};
            var camera=cameraObject.AddComponent<Camera>();camera.enabled=false;camera.cullingMask=1<<31;
            camera.fieldOfView=60;camera.aspect=2;camera.nearClipPlane=.05f;camera.farClipPlane=1800;camera.clearFlags=CameraClearFlags.Skybox;
            camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            camera.GetUniversalAdditionalCameraData().requiresDepthOption=CameraOverrideOption.On;
            var surface=GameObject.CreatePrimitive(PrimitiveType.Cube);surface.hideFlags=HideFlags.HideAndDontSave;surface.layer=31;
            surface.transform.localScale=new Vector3(900,900,1);
            var material=new Material(Shader.Find("Universal Render Pipeline/Lit")){hideFlags=HideFlags.HideAndDontSave};
            material.SetColor("_BaseColor",Color.red);surface.GetComponent<Renderer>().sharedMaterial=material;
            var rt=new RenderTexture(128,64,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            var pixels=new Texture2D(128,64,TextureFormat.RGB24,false);var result=new StringBuilder();
            GameObject skyRig=null;Material skyTemplate=null;OnlyVolunteers.Sky22.SkyClock22 clock=null;
            bool oldWeather=weather.enabled;
            try
            {
                if(g22)
                {
                    weather.enabled=false;skyRig=new GameObject("G18g transient G22 integration probe"){hideFlags=HideFlags.HideAndDontSave};
                    clock=skyRig.AddComponent<OnlyVolunteers.Sky22.SkyClock22>();clock.Running=false;
                    skyTemplate=new Material(Shader.Find("OnlyVolunteers/Sky22/Painted Sky v02")){hideFlags=HideFlags.HideAndDontSave};
                    var bridge=skyRig.AddComponent<OnlyVolunteers.Sky22.SkyDistrictV19Bridge22>();bridge.Configure(weather);
                    var sky=skyRig.AddComponent<OnlyVolunteers.Sky22.SkyRenderer22>();sky.Configure(clock,skyTemplate,null,null);sky.DistrictSource=bridge;
                }
                rt.Create();camera.targetTexture=rt;
                foreach(float hour in g22?new[]{0f,6f,12f,18f}:new[]{12f})for(int i=0;i<weather.districts.Length;i++)
                {
                    if(clock)clock.SetHour(hour);
                    var b=weather.districts[i].bounds;var p=new Vector3((b.x+b.z)*.5f,1200,(b.y+b.w)*.5f);
                    camera.transform.SetPositionAndRotation(p,Quaternion.identity);surface.transform.position=p+new Vector3(-500,0,1600);
                    camera.Render();camera.Render();RenderTexture.active=rt;pixels.ReadPixels(new Rect(0,0,128,64),0,0);pixels.Apply();
                    var far=pixels.GetPixel(32,32);var skyColour=pixels.GetPixel(96,32);
                    float delta=Mathf.Max(Mathf.Abs(far.r-skyColour.r),Mathf.Abs(far.g-skyColour.g),Mathf.Abs(far.b-skyColour.b));
                    result.AppendLine(FormattableString.Invariant($"{(delta<=.03f?"PASS":"FAIL")} {weather.districts[i].id} hour={hour} maxRgbDelta={delta:F6} far={far} sky={skyColour}"));
                }
                string path="Working/Reviews/Map_v19_Pilots/aerial_horizon_pixels_"+(g22?"g22_":"")+revision+".txt";
                using(var writer=new StreamWriter(new FileStream(path,FileMode.CreateNew)))writer.Write(result);
                return result.ToString();
            }
            finally
            {
                camera.targetTexture=null;RenderTexture.active=previous;rt.Release();
                Object.DestroyImmediate(rt);Object.DestroyImmediate(pixels);Object.DestroyImmediate(cameraObject);Object.DestroyImmediate(surface);Object.DestroyImmediate(material);
                if(skyRig)Object.DestroyImmediate(skyRig);if(skyTemplate)Object.DestroyImmediate(skyTemplate);weather.enabled=oldWeather;
            }
        }
    }
}
