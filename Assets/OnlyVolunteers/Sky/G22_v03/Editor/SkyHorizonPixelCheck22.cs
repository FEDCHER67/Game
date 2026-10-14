using System;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22V03.Editor
{
    // A real URP Lit surface beyond fog end must match an adjacent unobstructed sky pixel.
    public static class SkyHorizonPixelCheck22
    {
        public static string Run(string revision="v03")
        {
            SkyReviewBuilder22.RequireLock();
            var sky=Object.FindAnyObjectByType<SkyRenderer22>();var clock=Object.FindAnyObjectByType<SkyClock22>();
            if(!sky || !clock)throw new Exception("Open Sky_Test first.");
            var oldMood=sky.Mood;float oldHour=clock.Hour;var active=RenderTexture.active;
            var cameraObject=new GameObject("G22 temporary horizon probe"){hideFlags=HideFlags.HideAndDontSave};
            var camera=cameraObject.AddComponent<Camera>();camera.enabled=false;
            camera.transform.position=new Vector3(0,1200,0);camera.transform.rotation=Quaternion.identity;
            camera.fieldOfView=60;camera.aspect=2;camera.farClipPlane=1500;camera.clearFlags=CameraClearFlags.Skybox;
            camera.allowHDR=true;camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            var surface=GameObject.CreatePrimitive(PrimitiveType.Cube);surface.name="G22 temporary distant Lit surface";surface.hideFlags=HideFlags.HideAndDontSave;
            surface.transform.position=new Vector3(-500,1200,900);surface.transform.localScale=new Vector3(900,900,1);
            var material=new Material(Shader.Find("Universal Render Pipeline/Lit")){hideFlags=HideFlags.HideAndDontSave};
            material.SetColor("_BaseColor",Color.red);surface.GetComponent<Renderer>().sharedMaterial=material;
            var rt=new RenderTexture(128,64,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            var pixels=new Texture2D(128,64,TextureFormat.RGB24,false);var result=new StringBuilder();
            try
            {
                rt.Create();camera.targetTexture=rt;
                foreach(float hour in SkyReviewCapture22.Hours)for(int overcast=0;overcast<2;overcast++)
                {
                    clock.SetHour(hour);sky.Mood=overcast==0?SkyMood22.Hamlet:SkyMood22.Rough;
                    camera.Render();camera.Render();RenderTexture.active=rt;
                    pixels.ReadPixels(new Rect(0,0,128,64),0,0);pixels.Apply();
                    Color terrain=pixels.GetPixel(32,31),horizon=pixels.GetPixel(96,31);
                    float delta=Mathf.Max(Mathf.Abs(terrain.r-horizon.r),Mathf.Abs(terrain.g-horizon.g),Mathf.Abs(terrain.b-horizon.b));
                    if(sky.LastState.horizon!=sky.LastState.fog)throw new Exception("Model horizon and fog diverged.");
                    if(delta>3f/255)throw new Exception("Rendered horizon seam: hour="+hour+", cover="+overcast+", delta="+delta+", surface="+terrain+", sky="+horizon);
                    result.AppendLine("PASS: hour="+hour+", overcast="+overcast+", maximum RGB difference="+delta.ToString("F6")+", sky="+horizon);
                }
                string path="Working/Reviews/Sky/horizon_pixels_"+revision+".txt";
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                using(var w=new StreamWriter(new FileStream(path,FileMode.CreateNew)))w.Write(result.ToString());
                return path;
            }
            finally
            {
                camera.targetTexture=null;RenderTexture.active=active;sky.Mood=oldMood;clock.SetHour(oldHour);
                rt.Release();Object.DestroyImmediate(rt);Object.DestroyImmediate(pixels);Object.DestroyImmediate(cameraObject);
                Object.DestroyImmediate(surface);Object.DestroyImmediate(material);
            }
        }
    }
}
