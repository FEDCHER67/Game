using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22.Editor
{
    public static class SkyVerification22
    {
        static void Check(bool condition,string name,StringBuilder result) {if(!condition)throw new Exception("FAIL: "+name);result.AppendLine("PASS: "+name);}
        public static string Run(string revision="v02")
        {
            SkyReviewBuilder22.RequireLock();var result=new StringBuilder();
            Check(Mathf.Abs(SkyModel22.Advance(9,1440,24)-9)<.0001f,"1440 seconds gives exactly one default cycle",result);
            Check(Mathf.Abs(SkyModel22.Advance(23.9f,6,24))<.0001f,"Midnight wraps",result);
            Check(SkyModel22.Wrap(-1)==23 && SkyModel22.Wrap(24)==0,"Negative and 24-hour scrub normalization",result);
            Check(SkyModel22.IsNight(23) && !SkyModel22.IsNight(12),"Night thresholds",result);
            var day=SkyModel22.Evaluate(12,SkyMood22.Hamlet);var night=SkyModel22.Evaluate(0,SkyMood22.Hamlet);var rough=SkyModel22.Evaluate(12,SkyMood22.Rough);
            Check(day.sunDirection.y>.8f && night.sunDirection.y<-.8f,"Sun rotation over 24 hours",result);
            Check(night.moonDirection.y>.8f && night.moonIntensity>.1f && night.ambient.maxColorComponent>.3f,"Readable lit night and moon",result);
            Check(rough.sunIntensity<day.sunIntensity*.4f && rough.zenith.grayscale<day.zenith.grayscale,"Rough remains gloomy at noon",result);
            Check(day.stars<.01f && night.stars>.9f,"Stars fade by day",result);
            Check(SkyModel22.Evaluate(17.45f,SkyMood22.Hamlet).golden>.4f,"Warm golden-hour interval",result);
            for(float h=0;h<24;h+=.1f) {var s=SkyModel22.Evaluate(h,SkyMood22.Hamlet);Check(!float.IsNaN(s.sunIntensity) && s.sunIntensity>=0 && s.moonIntensity>=0,"Finite light at hour "+h.ToString("F1"),result);}
            var a=SkyModel22.Evaluate(23.999f,SkyMood22.Hamlet);var b=SkyModel22.Evaluate(.001f,SkyMood22.Hamlet);
            Check(Vector3.Distance(a.sunDirection,b.sunDirection)<.001f && Mathf.Abs(a.zenith.r-b.zenith.r)<.001f,"Midnight continuity",result);
            GameObject g=new GameObject("G22 transient clock verification"){hideFlags=HideFlags.HideAndDontSave};
            try {var clock=g.AddComponent<SkyClock22>();int events=0;bool last=false;clock.NightChanged+=value=>{events++;last=value;};
                clock.SetHour(23);clock.SetHour(22);clock.SetHour(8);
                Check(events==2 && !last,"Night event exactly once per state change, including scrub",result);
                clock.Running=false;float h=clock.Hour;clock.Tick(100);Check(clock.Hour==h,"Paused clock stays fixed",result);
            } finally {Object.DestroyImmediate(g);}
            string file="Working/Reviews/Sky/verification_"+revision+".txt";Directory.CreateDirectory(Path.GetDirectoryName(file));
            using(var writer=new StreamWriter(new FileStream(file,FileMode.CreateNew)))writer.Write(result.ToString());return file;
        }
    }
}
