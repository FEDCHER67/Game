using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22.Editor
{
    [InitializeOnLoad]
    public static class SkyInputCheck22
    {
        const string Key="G22.InputCheck";
        static Keyboard virtualKeyboard,priorKeyboard;
        static SkyClock22 clock;
        static int phase,frame;
        static float forwardHour,reverseHour;
        static double deadline;
        static bool subscribed;
        static SkyInputCheck22()
        {
            EditorApplication.playModeStateChanged+=Changed;
            if(SessionState.GetBool(Key,false))Subscribe();
        }
        public static void Start()
        {
            SkyReviewBuilder22.RequireLock();
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new Exception("Stop other Play checks first.");
            if(SceneManager.GetActiveScene().path!=SkyReviewBuilder22.ScenePath)throw new Exception("Open Sky_Test first.");
            if(File.Exists("Working/Reviews/Sky/input_check_v01.txt"))throw new IOException("Input evidence already exists.");
            SessionState.SetBool(Key,true);phase=0;deadline=EditorApplication.timeSinceStartup+90;Subscribe();EditorApplication.isPlaying=true;
        }
        static void Subscribe(){if(subscribed)return;subscribed=true;EditorApplication.update+=Update;}
        static void Changed(PlayModeStateChange state)
        {
            if(!SessionState.GetBool(Key,false))return;
            if(state==PlayModeStateChange.EnteredPlayMode){phase=0;deadline=EditorApplication.timeSinceStartup+90;Subscribe();}
            if(state==PlayModeStateChange.EnteredEditMode)Cleanup();
        }
        static void Cleanup()
        {
            if(virtualKeyboard!=null && virtualKeyboard.added)InputSystem.RemoveDevice(virtualKeyboard);
            if(priorKeyboard!=null && priorKeyboard.added)priorKeyboard.MakeCurrent();
            virtualKeyboard=null;priorKeyboard=null;EditorApplication.update-=Update;subscribed=false;SessionState.SetBool(Key,false);
        }
        static void Queue(params UnityEngine.InputSystem.Key[] keys)
        {InputSystem.QueueStateEvent(virtualKeyboard,new KeyboardState(keys));frame=Time.frameCount;}
        static void Update()
        {
            if(!SessionState.GetBool(Key,false)){Cleanup();return;}
            if(!EditorApplication.isPlaying || Time.frameCount<3)return;
            try
            {
                SkyReviewBuilder22.RequireLock();
                if(EditorApplication.timeSinceStartup>deadline)throw new Exception("Input probe timed out; normal Play frames must advance.");
                if(phase==0)
                {
                    clock=Object.FindAnyObjectByType<SkyClock22>();priorKeyboard=Keyboard.current;
                    virtualKeyboard=InputSystem.AddDevice<Keyboard>("G22 verification keyboard");virtualKeyboard.MakeCurrent();
                    clock.Running=false;clock.SetHour(10);Queue(UnityEngine.InputSystem.Key.Backslash);phase=1;return;
                }
                if(Time.frameCount-frame<10)return;
                if(phase==1)
                {
                    if(!clock.Running)throw new Exception("Backslash did not resume the clock through Update.");
                    Queue();phase=2;return;
                }
                if(phase==2)
                {
                    clock.Running=false;clock.SetHour(10);Queue(UnityEngine.InputSystem.Key.RightBracket);phase=3;return;
                }
                if(phase==3)
                {
                    forwardHour=clock.Hour;if(forwardHour<=10.0001f)throw new Exception("Right bracket did not scrub forward through Update.");
                    Queue(UnityEngine.InputSystem.Key.LeftShift,UnityEngine.InputSystem.Key.LeftBracket);phase=4;return;
                }
                if(phase==4)
                {
                    reverseHour=clock.Hour;if(reverseHour>=forwardHour-.0001f)throw new Exception("Shift + left bracket did not scrub backward.");
                    Queue();phase=5;return;
                }
                if(phase==5)
                {
                    float afterRelease=clock.Hour;
                    string text="PASS: backslash toggles clock via Input System and normal Update\nPASS: right bracket scrubs forward; hour="+forwardHour+
                        "\nPASS: Shift + left bracket scrubs backward; hour="+reverseHour+"\nReleased input hour="+afterRelease+
                        "\nVirtual keyboard isolated to this Unity Play run; no OS keys injected.\n";
                    Directory.CreateDirectory("Working/Reviews/Sky");using(var w=new StreamWriter(new FileStream("Working/Reviews/Sky/input_check_v01.txt",FileMode.CreateNew)))w.Write(text);
                    Cleanup();EditorApplication.isPlaying=false;
                }
            }
            catch(Exception e){Cleanup();EditorApplication.isPlaying=false;Debug.LogException(e);}
        }
    }
}
