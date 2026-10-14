using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19AerialReceiverCheckV01
    {
        public static string Run(string revision="v01")
        {
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>();
            var previous=RenderTexture.active;var go=new GameObject("G18g transient receiver camera"){hideFlags=HideFlags.HideAndDontSave};
            var camera=go.AddComponent<Camera>();camera.enabled=false;camera.cullingMask=1<<31;camera.fieldOfView=60;camera.aspect=2;camera.farClipPlane=1500;
            camera.clearFlags=CameraClearFlags.Skybox;camera.GetUniversalAdditionalCameraData().requiresDepthOption=CameraOverrideOption.On;
            camera.GetUniversalAdditionalCameraData().requiresColorOption=CameraOverrideOption.On;
            camera.GetUniversalAdditionalCameraData().renderPostProcessing=false;
            var plane=GameObject.CreatePrimitive(PrimitiveType.Quad);plane.hideFlags=HideFlags.HideAndDontSave;plane.layer=31;
            var rt=new RenderTexture(128,64,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);var pixels=new Texture2D(128,64,TextureFormat.RGB24,false);
            var log=new StringBuilder("Real GPU probes; no post grade. RGB deltas in sRGB; transparent source shape is an isolated quad with its actual shader.\n");
            var owned=new System.Collections.Generic.List<Material>();
            try
            {
                rt.Create();camera.targetTexture=rt;camera.transform.position=new Vector3(250,1200,480);camera.transform.rotation=Quaternion.Euler(0,90,0);plane.transform.rotation=camera.transform.rotation;
                var ray=camera.ViewportPointToRay(new Vector3(64.5f/128,32.5f/64,0)).direction;
                var black=new Material(Shader.Find("Universal Render Pipeline/Unlit")){hideFlags=HideFlags.HideAndDontSave};black.SetColor("_BaseColor",Color.black);owned.Add(black);
                foreach(string district in new[]{"village","industrial"})
                {
                    var d=weather.districts.First(x=>x.id==district);camera.transform.position=new Vector3((d.bounds.x+d.bounds.z)*.5f,1200,(d.bounds.y+d.bounds.w)*.5f);
                    plane.GetComponent<Renderer>().sharedMaterial=black;
                    foreach(float distance in new[]{20f,35f,40f,100f,175f,200f,350f,400f,450f})
                    {
                        plane.transform.position=camera.transform.position+ray*distance;plane.transform.localScale=Vector3.one*distance*.3f;
                        camera.Render();camera.Render();RenderTexture.active=rt;pixels.ReadPixels(new Rect(0,0,128,64),0,0);pixels.Apply();
                        Color pixel=pixels.GetPixel(64,32).linear,horizon=pixels.GetPixel(100,32).linear;
                        float alpha=(pixel.r/horizon.r+pixel.g/horizon.g+pixel.b/horizon.b)/3;
                        log.AppendLine(FormattableString.Invariant($"CURVE {district} distance={distance} height=1200 measuredOpacity={alpha:F5}"));
                    }
                }
                camera.transform.position=new Vector3(250,1200,480);
                string folder=V19AerialBuildV01.Folder+"/Materials/";
                string[] materials={"M3_Water_River_9a4c189d_Aerial_v01","VAN_Glass_8a71bad6_Aerial_v01","V19_SoftSmoke_f895cf32_Aerial_v01","Font Material_00000000_Aerial_v01","Mist_Aerial19_v01","Halo_Aerial19_v01"};
                foreach(var name in materials)
                {
                    var source=UnityEditor.AssetDatabase.LoadAssetAtPath<Material>(folder+name+".mat");
                    var mat=new Material(source){hideFlags=HideFlags.HideAndDontSave};owned.Add(mat);
                    // A white atlas/vertex colour makes text and particle quads measurable; real shader alpha rules remain.
                    if(mat.HasProperty("_MainTex"))mat.SetTexture("_MainTex",Texture2D.whiteTexture);
                    if(mat.HasProperty("_BaseMap"))mat.SetTexture("_BaseMap",Texture2D.whiteTexture);
                    if(mat.HasProperty("_BaseColor"))mat.SetColor("_BaseColor",new Color(.1f,.2f,.1f,1));
                    plane.GetComponent<Renderer>().sharedMaterial=mat;
                    Color near=Color.black,far=Color.black,sky=Color.black;
                    foreach(float distance in new[]{20f,900f})
                    {
                        plane.transform.position=camera.transform.position+ray*distance;plane.transform.localScale=Vector3.one*distance*.3f;
                        camera.Render();camera.Render();RenderTexture.active=rt;pixels.ReadPixels(new Rect(0,0,128,64),0,0);pixels.Apply();
                        if(distance<100)near=pixels.GetPixel(64,32);else {far=pixels.GetPixel(64,32);sky=pixels.GetPixel(100,32);}
                    }
                    float delta=Mathf.Max(Mathf.Abs(far.r-sky.r),Mathf.Abs(far.g-sky.g),Mathf.Abs(far.b-sky.b));
                    log.AppendLine(FormattableString.Invariant($"RECEIVER {(delta<=.03f?"PASS":"FAIL")} {name} near={near} far={far} horizon={sky} delta={delta:F6}"));
                }
                string path="Working/Reviews/Map_v19_Pilots/aerial_receiver_pixels_"+revision+".txt";
                using(var writer=new StreamWriter(new FileStream(path,FileMode.CreateNew)))writer.Write(log);
                return log.ToString();
            }
            finally
            {
                camera.targetTexture=null;RenderTexture.active=previous;rt.Release();Object.DestroyImmediate(rt);Object.DestroyImmediate(pixels);
                Object.DestroyImmediate(go);Object.DestroyImmediate(plane);foreach(var mat in owned)Object.DestroyImmediate(mat);
            }
        }
    }
}
