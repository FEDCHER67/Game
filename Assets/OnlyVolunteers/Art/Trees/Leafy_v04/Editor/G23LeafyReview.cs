using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Wind;
using OnlyVolunteers.Map.Wind.Editor;
using OnlyVolunteers.Sky22V04;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Trees.Editor
{
    public static class G23LeafyReview
    {
        public static string Capture(string revision)
        {
            if(!EditorApplication.isPlaying)throw new Exception("Play mode required for map captures");
            var clock=Object.FindAnyObjectByType<SkyClock22>();bool running=clock.Running;float hour=clock.Hour;
            try
            {
                clock.Running=false;clock.SetHour(8);
                for(int i=0;i<4;i++)
                {
                    var p=G23LeafyBenchmark.Poses[i];
                    WindReview24.Shot("../Trees/i07/"+revision+"_"+i,p.x,p.y,p.z,p.w,12,true,1.65f,1600,900);
                }
                return "Four actual Play captures saved: "+revision;
            }
            finally{clock.SetHour(hour);clock.Running=running;}
        }
        public static string Benchmark(string revision)
        {
            if(!EditorApplication.isPlaying||EditorApplication.isPaused||Time.captureDeltaTime!=0||Object.FindAnyObjectByType<G23LeafyBenchmark>())throw new Exception("Requires normal Play and no running benchmark");
            string path=Path.GetFullPath(G23LeafyIntegration.Evidence+"/performance_"+revision+".json");if(File.Exists(path))throw new Exception("Existing evidence");
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var positions=G23LeafyBenchmark.Poses.Select(p=>new Vector3(p.x,ground.Height(p.x,p.y)+1.65f,p.y)).ToArray();
            new GameObject("G23_TemporaryLeafyBenchmark").AddComponent<G23LeafyBenchmark>().Begin(positions,path);return "Started "+path;
        }
        public static string WindFrames()
        {
            if(!EditorApplication.isPlaying)throw new Exception("Play mode required");
            var clock=Object.FindAnyObjectByType<SkyClock22>();bool running=clock.Running;float hour=clock.Hour;
            try
            {
                clock.Running=false;clock.SetHour(8);var p=G23LeafyBenchmark.Poses[0];
                for(int frame=0;frame<32;frame++)WindReview24.Shot("../Trees/i07/wind_"+frame.ToString("00"),p.x,p.y,p.z,p.w,12+frame*.125f,true,1.65f,800,450);
                return "32 shared-wind frames saved";
            }
            finally{clock.SetHour(hour);clock.Running=running;}
        }
    }
}
