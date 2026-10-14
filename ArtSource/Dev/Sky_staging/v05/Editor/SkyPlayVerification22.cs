using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22V05.Editor
{
    [InitializeOnLoad]
    public static class SkyPlayVerification22
    {
        const string Key="G22V05.PlayVerification";
        static double started;
        static int frames;
        static bool hooked;
        static SkyPlayVerification22()
        {
            EditorApplication.playModeStateChanged+=State;
            if(SessionState.GetBool(Key,false))Hook();
        }
        public static void Start()
        {
            SkyReviewBuilder22.RequireLock();
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new Exception("Play is already active.");
            if(SceneManager.GetActiveScene().path!=SkyReviewBuilder22.ScenePath)throw new Exception("Open Sky_Test first.");
            if(File.Exists("Working/Reviews/Sky/play_verification_v05.txt"))throw new IOException("Evidence exists.");
            SessionState.SetBool(Key,true);started=EditorApplication.timeSinceStartup;frames=0;Hook();EditorApplication.isPlaying=true;
        }
        static void Hook() {if(hooked)return;hooked=true;EditorApplication.update+=Update;}
        static void Unhook() {EditorApplication.update-=Update;hooked=false;}
        static void State(PlayModeStateChange state)
        {
            if(!SessionState.GetBool(Key,false))return;
            if(state==PlayModeStateChange.EnteredPlayMode){started=EditorApplication.timeSinceStartup;frames=0;Hook();}
            if(state==PlayModeStateChange.EnteredEditMode){SessionState.SetBool(Key,false);Unhook();}
        }
        static void Update()
        {
            if(!SessionState.GetBool(Key,false)){Unhook();return;}
            if(!EditorApplication.isPlaying)return;
            if(Time.frameCount<3)
            {
                // The updated work protocol permits foregrounding Unity; never change background settings.
                if(EditorApplication.timeSinceStartup-started>30) {Unhook();Debug.LogWarning("G22 Play verification waiting for foreground initialization. Call Resume after normal frames advance.");}
                return;
            }
            if(++frames<8)return;
            Unhook();
            try
            {
                SkyReviewBuilder22.RequireLock();
                if(SceneManager.GetActiveScene().path!=SkyReviewBuilder22.ScenePath)throw new Exception("Scene changed during verification.");
                var clock=Object.FindAnyObjectByType<SkyClock22>();var renderer=Object.FindAnyObjectByType<SkyRenderer22>();
                float before=clock.Hour;clock.Running=true;clock.Tick(60);float after=clock.Hour;
                if(Mathf.Abs(SkyModel22.Wrap(after-before)-1)>.005f)throw new Exception("60-second tick did not advance one hour.");
                int events=0;Action<bool> listener=_=>events++;clock.NightChanged+=listener;
                clock.SetHour(12);events=0;clock.SetHour(22);clock.SetHour(21);clock.SetHour(8);clock.NightChanged-=listener;
                if(events!=2)throw new Exception("Runtime night event count: "+events);
                clock.SetHour(22);
                var windows=Array.Find(SceneManager.GetActiveScene().GetRootGameObjects(),g=>g.name=="G22 night windows");
                if(!windows || !windows.activeSelf)throw new Exception("Night objects did not activate.");
                clock.SetHour(12);if(windows.activeSelf)throw new Exception("Night objects stayed active by day.");
                string text="PASS: Play entered; normal frames="+Time.frameCount+"\nPASS: configured 24-minute clock\nPASS: runtime night transitions and lamp/window listener\nPASS: sky component active="+renderer.isActiveAndEnabled+"\nManual debug-key feel: NOT RUN\n";
                Directory.CreateDirectory("Working/Reviews/Sky");using(var w=new StreamWriter(new FileStream("Working/Reviews/Sky/play_verification_v05.txt",FileMode.CreateNew)))w.Write(text);
                SessionState.SetBool(Key,false);EditorApplication.isPlaying=false;
            }
            catch(Exception e){SessionState.SetBool(Key,false);EditorApplication.isPlaying=false;Debug.LogException(e);}
        }
        public static void Resume() {if(SessionState.GetBool(Key,false)){started=EditorApplication.timeSinceStartup;frames=0;Hook();}}
    }
}
