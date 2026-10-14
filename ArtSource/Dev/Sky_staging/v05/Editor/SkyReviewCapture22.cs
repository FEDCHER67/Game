using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22V05.Editor
{
    public static class SkyReviewCapture22
    {
        const string PriorKey="G22V05.PreviousScene";
        public static readonly float[] Hours={5.65f,8,12,17.45f,19.1f,22,6.25f,18.25f};
        public static readonly string[] Labels={"dawn","morning","noon","golden_hour","dusk","night","sunrise_sunfacing","sunset_sunfacing"};
        public static void Open()
        {
            SkyReviewBuilder22.RequireLock();
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new Exception("Play must be stopped.");
            for(int i=0;i<SceneManager.sceneCount;i++)if(SceneManager.GetSceneAt(i).isDirty)throw new Exception("Unsaved scene: cannot start review.");
            if(SceneManager.sceneCount!=1)throw new Exception("Review requires one clean scene; preserve the current multi-scene setup.");
            string prior=SceneManager.GetActiveScene().path;if(prior!=SkyReviewBuilder22.ScenePath)SessionState.SetString(PriorKey,prior);
            EditorSceneManager.OpenScene(SkyReviewBuilder22.ScenePath,OpenSceneMode.Single);
        }
        public static void Restore()
        {
            SkyReviewBuilder22.RequireLock();if(EditorApplication.isPlayingOrWillChangePlaymode)throw new Exception("Stop Play before restoring.");
            string path=SessionState.GetString(PriorKey,"");if(!string.IsNullOrEmpty(path))EditorSceneManager.OpenScene(path,OpenSceneMode.Single);
        }
        // Capture one frame at a time so a long batch cannot monopolize the shared Editor.
        public static string Capture(int phase,bool overcast,string revision="v05")
        {
            SkyReviewBuilder22.RequireLock();
            if(SceneManager.GetActiveScene().path!=SkyReviewBuilder22.ScenePath)throw new Exception("Open Sky_Test first.");
            if(phase<0 || phase>=Hours.Length)throw new ArgumentOutOfRangeException(nameof(phase));
            if(revision.IndexOfAny(Path.GetInvalidFileNameChars())>=0 || revision.Contains(".."))throw new ArgumentException("Invalid capture revision.");
            string folder="Working/Reviews/Sky";Directory.CreateDirectory(folder);
            string file=folder+"/"+Labels[phase]+"_"+(overcast?"overcast":"clear")+"_"+revision+".png";
            if(File.Exists(file))throw new IOException("Capture exists: "+file);
            var clock=Object.FindAnyObjectByType<SkyClock22>();var sky=Object.FindAnyObjectByType<SkyRenderer22>();var camera=Camera.main;
            var oldMood=sky.Mood;float oldHour=clock.Hour,oldCloud=sky.CloudTime;var oldTarget=camera.targetTexture;
            var oldRotation=camera.transform.rotation;
            var previous=RenderTexture.active;var rt=new RenderTexture(1920,1080,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            var texture=new Texture2D(1920,1080,TextureFormat.RGB24,false);
            try
            {
                clock.SetHour(Hours[phase]);var mood=SkyMood22.Hamlet;mood.cloudCover=overcast?.97f:.28f;mood.gloom=overcast?.52f:0;
                sky.Mood=mood;sky.CloudTime=650;camera.targetTexture=rt;rt.Create();
                if(phase>=6){var direction=SkyModel22.Evaluate(clock.Hour,mood).sunDirection;camera.transform.rotation=Quaternion.Euler(-12,Mathf.Atan2(direction.x,direction.z)*Mathf.Rad2Deg,0);}
                camera.Render();camera.Render();RenderTexture.active=rt;texture.ReadPixels(new Rect(0,0,1920,1080),0,0);texture.Apply();
                using(var stream=new FileStream(file,FileMode.CreateNew)) {var bytes=texture.EncodeToPNG();stream.Write(bytes,0,bytes.Length);}
                var s=sky.LastState;
                string evidence=$"Unity={Application.unityVersion}\nScene={SceneManager.GetActiveScene().path}\nHour={clock.Hour}\nCloudCover={mood.cloudCover}\nSunIntensity={s.sunIntensity}\nMoonIntensity={s.moonIntensity}\nIsNight={clock.IsNight}\nResolution=1920x1080\nCamera={camera.transform.position}; {camera.transform.eulerAngles}; FOV={camera.fieldOfView}\n";
                using(var writer=new StreamWriter(new FileStream(file+".txt",FileMode.CreateNew)))writer.Write(evidence);
                return file;
            }
            finally
            {
                camera.targetTexture=oldTarget;camera.transform.rotation=oldRotation;RenderTexture.active=previous;sky.Mood=oldMood;sky.CloudTime=oldCloud;clock.SetHour(oldHour);
                rt.Release();Object.DestroyImmediate(rt);Object.DestroyImmediate(texture);
            }
        }
    }
}
