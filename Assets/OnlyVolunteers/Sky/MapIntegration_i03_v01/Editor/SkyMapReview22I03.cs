using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.Sky22V04;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22MapI03.Editor
{
    public static class SkyMapReview22I03
    {
        static readonly string[] Globals={"_G18AerialHorizon","_G18AerialClear","_G18AerialDense","_G18AerialHeight","_G18AerialWorld","_G18AerialState","_G18AerialEdge"};
        public static string Shot(string district,float x,float z,float yaw,float hour,string label)
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Capture the installed map in Play.");
            string path=SkyMapInstall22I03.Output+"/map_i03_"+district+"_"+label+"_v01.png";
            if(File.Exists(path))throw new IOException(path+" already exists");
            var clock=Object.FindAnyObjectByType<SkyClock22>();var sky=Object.FindAnyObjectByType<SkyRenderer22>();
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var fog=Object.FindAnyObjectByType<DistrictFog19V05>();
            var grass=Object.FindAnyObjectByType<ChunkedGrassRenderer24>();
            var go=new GameObject("G22 i03 review camera"){hideFlags=HideFlags.HideAndDontSave};
            var camera=go.AddComponent<Camera>();camera.enabled=false;camera.fieldOfView=70;camera.nearClipPlane=.05f;camera.farClipPlane=650;
            camera.clearFlags=CameraClearFlags.Skybox;camera.transform.SetPositionAndRotation(new Vector3(x,ground.Height(x,z)+1.85f,z),Quaternion.Euler(-6,yaw,0));
            camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;camera.GetUniversalAdditionalCameraData().requiresDepthOption=CameraOverrideOption.On;
            var previous=RenderTexture.active;var rt=new RenderTexture(1920,1080,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);rt.Create();
            var pixels=new Texture2D(1920,1080,TextureFormat.RGB24,false,false);
            float oldHour=clock.Hour,oldCloud=sky.CloudTime,oldFog=fog.reviewTime,oldGrass=grass.reviewTime;bool running=clock.Running;
            try
            {
                clock.Running=false;clock.SetHour(hour);sky.CloudTime=650;fog.reviewTime=12;grass.reviewTime=12;camera.targetTexture=rt;
                camera.Render();camera.Render();RenderTexture.active=rt;pixels.ReadPixels(new Rect(0,0,1920,1080),0,0);pixels.Apply();
                if(sky.LastState.horizon!=fog.aerial.LastHorizon)throw new Exception("Sky and aerial horizons differ.");
                using(var file=new FileStream(path,FileMode.CreateNew)){var bytes=pixels.EncodeToPNG();file.Write(bytes,0,bytes.Length);}
                SkyMapInstall22I03.WriteNew(Path.ChangeExtension(path,".txt"),$"Scene={UnityEngine.SceneManagement.SceneManager.GetActiveScene().path}\nPlay={Application.isPlaying}; frame={Time.frameCount}; hour={hour}\nPosition={camera.transform.position}; yaw={yaw}; pitch=-6; FOV=70; 1920x1080\nSky horizon={sky.LastState.horizon}; G18g horizon={fog.aerial.LastHorizon}\nCover={sky.DistrictSource.Sample(camera.transform.position).cloudCover}; Night={clock.IsNight}\n{grass.ReadStats(camera)}\n");return path;
            }
            finally
            {clock.SetHour(oldHour);clock.Running=running;sky.CloudTime=oldCloud;fog.reviewTime=oldFog;grass.reviewTime=oldGrass;camera.targetTexture=null;RenderTexture.active=previous;rt.Release();Object.DestroyImmediate(pixels);Object.DestroyImmediate(rt);Object.DestroyImmediate(go);}
        }
        public static string HorizonAndNightCheck()
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Check the installed map in Play.");
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>(FindObjectsInactive.Include);
            var clock=Object.FindAnyObjectByType<SkyClock22>();var sky=Object.FindAnyObjectByType<SkyRenderer22>();var night=Object.FindAnyObjectByType<SkyMapNight22I03>();
            var aerial=weather.visibleFog.aerial;float oldHour=clock.Hour;bool running=clock.Running;
            var go=new GameObject("G22 installed map horizon probe"){hideFlags=HideFlags.HideAndDontSave};var camera=go.AddComponent<Camera>();camera.enabled=false;camera.cullingMask=1<<31;
            camera.fieldOfView=60;camera.aspect=2;camera.nearClipPlane=.05f;camera.farClipPlane=1800;camera.clearFlags=CameraClearFlags.Skybox;
            camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;camera.GetUniversalAdditionalCameraData().requiresDepthOption=CameraOverrideOption.On;
            var cube=GameObject.CreatePrimitive(PrimitiveType.Cube);cube.hideFlags=HideFlags.HideAndDontSave;cube.layer=31;cube.transform.localScale=new Vector3(900,900,1);
            var material=new Material(Shader.Find("Universal Render Pipeline/Lit")){hideFlags=HideFlags.HideAndDontSave};material.SetColor("_BaseColor",Color.red);cube.GetComponent<Renderer>().sharedMaterial=material;
            var rt=new RenderTexture(128,64,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);rt.Create();var pixels=new Texture2D(128,64,TextureFormat.RGB24,false);
            var active=RenderTexture.active;var pipeline=QualitySettings.renderPipeline;var graphicsPipeline=GraphicsSettings.defaultRenderPipeline;
            var text=new StringBuilder();int failures=0;float maximum=0;int transitions=0;Action<bool> listener=n=>transitions++;clock.NightChanged+=listener;
            try
            {
                clock.Running=false;camera.targetTexture=rt;
                foreach(float hour in new[]{0f,6f,12f,17.45f,22f})foreach(var district in weather.districts)
                {
                    clock.SetHour(hour);var b=district.bounds;var position=new Vector3((b.x+b.z)*.5f,1200,(b.y+b.w)*.5f);
                    camera.transform.SetPositionAndRotation(position,Quaternion.identity);cube.transform.position=position+new Vector3(-500,0,1600);
                    var saved=Globals.Select(Shader.GetGlobalVector).ToArray();var fogColour=RenderSettings.fogColor;var skybox=RenderSettings.skybox;
                    camera.Render();camera.Render();RenderTexture.active=rt;pixels.ReadPixels(new Rect(0,0,128,64),0,0);pixels.Apply();
                    var far=pixels.GetPixel(32,32);var adjacent=pixels.GetPixel(96,32);float delta=Mathf.Max(Mathf.Abs(far.r-adjacent.r),Mathf.Abs(far.g-adjacent.g),Mathf.Abs(far.b-adjacent.b));maximum=Mathf.Max(maximum,delta);
                    bool restore=Globals.Select((n,i)=>Shader.GetGlobalVector(n)==saved[i]).All(x=>x) && fogColour==RenderSettings.fogColor && skybox==RenderSettings.skybox;
                    bool pass=delta<=2f/255 && sky.LastState.horizon==aerial.LastHorizon && restore && night.CheckApplied();if(!pass)failures++;
                    text.AppendLine($"{(pass?"PASS":"FAIL")} {district.id} hour={hour} farSkyRGBDelta={delta:F6} exactHorizon={sky.LastState.horizon==aerial.LastHorizon} globalRestore={restore} nightBindings={night.CheckApplied()}");
                }
                bool owners=!weather.enabled && sky.DistrictSource.Ready && Object.FindObjectsByType<SkyClock22>().Length==1 && Object.FindObjectsByType<SkyRenderer22>().Length==1;
                bool pipelines=pipeline==QualitySettings.renderPipeline && graphicsPipeline==GraphicsSettings.defaultRenderPipeline;
                int missing=UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).Sum(t=>GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
                bool summary=owners && pipelines && missing==0 && transitions>=2 && failures==0;
                text.AppendLine($"{(summary?"PASS":"FAIL")} summary: 50 renders; failures={failures}; maxRGBDelta={maximum}; oneOwner={owners}; pipelinesUnchanged={pipelines}; missingScripts={missing}; nightTransitions={transitions}; lamps={night.LampCount}; emissiveSlots={night.EmissiveSlotCount}; frame={Time.frameCount}");
                SkyMapInstall22I03.WriteNew(SkyMapInstall22I03.Output+"/horizon_night_play_i03_v01.txt",text.ToString());return text.ToString();
            }
            finally
            {clock.NightChanged-=listener;clock.SetHour(oldHour);clock.Running=running;camera.targetTexture=null;RenderTexture.active=active;rt.Release();Object.DestroyImmediate(rt);Object.DestroyImmediate(pixels);Object.DestroyImmediate(cube);Object.DestroyImmediate(material);Object.DestroyImmediate(go);}
        }
    }
}
