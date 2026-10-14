using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Wind.Editor
{
    public static class WindReview24
    {
        public const string Output="Working/Reviews/Wind";
        public static string Shot(string name,float x,float z,float yaw,float pitch=4,float time=12,bool after=true,float eye=1.65f,int width=1600,int height=900)
        {
            string path=Output+"/"+name+".png";
            if(File.Exists(path))throw new IOException("Capture exists: "+path);
            var grass=Object.FindAnyObjectByType<ChunkedGrassRenderer24>();var ground=Object.FindAnyObjectByType<MapHeightSampler>();
            if(!grass||!ground)throw new InvalidOperationException("Grass and ground required");
            foreach(var building in Object.FindObjectsByType<MapBuildingInfo>())
            {
                if(building.Footprint==null||building.Footprint.Length<3)continue;
                var polygon=new float[building.Footprint.Length*2];
                for(int i=0;i<building.Footprint.Length;i++){polygon[i*2]=building.Footprint[i].x;polygon[i*2+1]=building.Footprint[i].y;}
                if(LookGeom.Inside(polygon,x,z))throw new InvalidOperationException("Review camera is inside building "+building.Id+"; choose an exterior viewpoint");
            }
            var fog=Object.FindAnyObjectByType<DistrictFog19V05>();float oldFogTime=fog?fog.reviewTime:-1;
            var wind=Object.FindAnyObjectByType<V19Wind>();if(!wind)throw new InvalidOperationException("Shared wind missing");float oldWindTime=wind.reviewTime;wind.reviewTime=time;wind.Publish();
            float oldTime=grass.reviewTime;bool oldSuppress=grass.suppressDrawing;
            var go=new GameObject("G24_ReviewCamera"){hideFlags=HideFlags.HideAndDontSave};
            RenderTexture rt=null,resolved=null;Texture2D tex=null;var previous=RenderTexture.active;
            try
            {
                grass.reviewTime=time;grass.suppressDrawing=!after;if(fog)fog.reviewTime=12;
                var camera=go.AddComponent<Camera>();camera.fieldOfView=65;camera.nearClipPlane=.07f;camera.farClipPlane=650;camera.clearFlags=CameraClearFlags.Skybox;
                go.transform.SetPositionAndRotation(new Vector3(x,ground.Height(x,z)+eye,z),Quaternion.Euler(pitch,yaw,0));
                var data=go.AddComponent<UniversalAdditionalCameraData>();data.renderPostProcessing=true;data.requiresDepthOption=CameraOverrideOption.On;data.requiresColorOption=CameraOverrideOption.On;
                int msaa=QualitySettings.renderPipeline is UniversalRenderPipelineAsset urp?Mathf.Max(1,urp.msaaSampleCount):1;
                rt=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB){antiAliasing=msaa};rt.Create();
                resolved=new RenderTexture(width,height,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);resolved.Create();camera.targetTexture=rt;
                camera.Render();camera.Render();
                string stats=after?grass.ReadStats(camera):"Tall layer suppressed; low grass unchanged";
                Graphics.Blit(rt,resolved);RenderTexture.active=resolved;tex=new Texture2D(width,height,TextureFormat.RGB24,false,false);tex.ReadPixels(new Rect(0,0,width,height),0,0);tex.Apply();
                Directory.CreateDirectory(Output);File.WriteAllBytes(path,tex.EncodeToPNG());
                string meta=$"scene={UnityEngine.SceneManagement.SceneManager.GetActiveScene().path}\ncamera={go.transform.position}; yaw={yaw}; pitch={pitch}; fov=65; time={time}; after={after}\n{stats}\nSRP Batcher={GraphicsSettings.useScriptableRenderPipelineBatching}; GPU={SystemInfo.graphicsDeviceName}";
                File.WriteAllText(Output+"/"+name+".txt",meta);return path+"\n"+meta;
            }
            finally
            {
                wind.reviewTime=oldWindTime;wind.Publish();RenderTexture.active=previous;grass.reviewTime=oldTime;grass.suppressDrawing=oldSuppress;if(fog)fog.reviewTime=oldFogTime;
                Object.DestroyImmediate(go);if(tex)Object.DestroyImmediate(tex);if(rt){rt.Release();Object.DestroyImmediate(rt);}if(resolved){resolved.Release();Object.DestroyImmediate(resolved);}
            }
        }
    }
}
