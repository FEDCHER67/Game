using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19AerialBuildV01
    {
        public const string Folder="Assets/OnlyVolunteers/Map/LookV3/Palette19/Aerial_v01";
        static Material CopyMaterial(Material source,string file,string shader)
        {
            string path=Folder+"/Materials/"+file+".mat";
            var existing=AssetDatabase.LoadAssetAtPath<Material>(path);if(existing)return existing;
            var s=Shader.Find(shader);if(!s)throw new Exception("Missing shader "+shader);
            var material=new Material(source){name=file};material.shader=s;
            AssetDatabase.CreateAsset(material,path);return material;
        }
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new Exception("Stop Play before aerial integration");
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(scene.name!="Map_Look_v19"&&scene.name!="Map_Look_v19_Play")throw new Exception("Final v19 scene required");
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>();var fog=weather.visibleFog;
            LookAssetStore.EnsureFolder(Folder+"/Materials");
            // Disable/re-enable disposes only scene-owned transient materials; no pipeline changes.
            weather.enabled=false;fog.enabled=false;
            var aerial=weather.GetComponent<DistrictAerial19V01>();if(!aerial)aerial=weather.gameObject.AddComponent<DistrictAerial19V01>();
            fog.aerial=aerial;
            weather.skyTemplate=CopyMaterial(weather.skyTemplate,"Sky_Aerial19_v01","OnlyVolunteers/StyleV3/DistrictSkyAerial19V01");
            fog.fogTemplate=CopyMaterial(fog.fogTemplate,"Depth_Aerial19_v01","OnlyVolunteers/StyleV3/AerialDepth19V01");
            fog.mistTemplate=CopyMaterial(fog.mistTemplate,"Mist_Aerial19_v01","OnlyVolunteers/StyleV3/MistAerial19V01");
            fog.haloTemplate=CopyMaterial(fog.haloTemplate,"Halo_Aerial19_v01","OnlyVolunteers/StyleV3/MistAerial19V01");
            var mappings=new Dictionary<Material,Material>();var lines=new List<string>();
            foreach(var renderer in scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Renderer>(true)))
            {
                var mats=renderer.sharedMaterials;bool changed=false;
                for(int i=0;i<mats.Length;i++)
                {
                    var mat=mats[i];if(!mat || !mat.shader || mat.renderQueue<2501)continue;
                    string shader=null;
                    switch(mat.shader.name)
                    {
                        case "UberStylizedWater":shader="WaterAerial19V01";break;
                        case "Universal Render Pipeline/Lit":shader="GlassAerial19V01";break;
                        case "Universal Render Pipeline/Particles/Unlit":shader="SmokeAerial19V01";break;
                        case "GUI/Text Shader":shader="TextAerial19V01";break;
                        default:if(mat.shader.name.StartsWith("OnlyVolunteers/StyleV3/")&&mat.shader.name.Contains("Aerial"))continue;throw new Exception("Unhandled transparent receiver "+mat.shader.name+" on "+renderer.name);
                    }
                    if(!mappings.TryGetValue(mat,out var replacement))
                    {
                        string guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(mat));
                        if(string.IsNullOrEmpty(guid))guid="builtin";
                        replacement=CopyMaterial(mat,mat.name.Replace('/','_')+"_"+guid.Substring(0,Math.Min(8,guid.Length))+"_Aerial_v01","OnlyVolunteers/StyleV3/"+shader);
                        mappings.Add(mat,replacement);lines.Add(AssetDatabase.GetAssetPath(mat)+" -> "+AssetDatabase.GetAssetPath(replacement));
                    }
                    mats[i]=replacement;changed=true;
                }
                if(changed)renderer.sharedMaterials=mats;
            }
            fog.enabled=true;weather.enabled=true;
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
            return string.Join("\n",lines)+"\nApplied to "+scene.path+"; material variants="+mappings.Count;
        }
        public static string CapturePoses(string prefix,string file="review_poses_v19_final_v02.json",string only="")
        {
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var fog=Object.FindAnyObjectByType<DistrictFog19V05>();
            fog.reviewTime=12;int count=0;
            try{foreach(var p in V19PilotTools.LoadPoses(file))
            {
                if(only!=""&&!p.Name.StartsWith(only))continue;
                string path=V19PilotTools.OutDir+"/"+prefix+p.Name+".png";if(File.Exists(path))continue;
                if(p.Kind=="van")
                {
                    typeof(V19PilotTools).GetMethod("ShootVan",System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic).Invoke(null,new object[]{ground,p,path,1200f,1920,1080});
                }
                else if(p.Kind=="top")V19PilotTools.Render(path,new Vector3(p.X,600,p.Z),Quaternion.Euler(90,p.Yaw,0),60,3000,1920,1080,true,p.OrthoSize,false);
                else
                {
                    float y=float.IsNaN(p.SurfaceY)?ground.Height(p.X,p.Z)+p.Above:p.SurfaceY;
                    V19PilotTools.Render(path,new Vector3(p.X,y+V19PilotTools.WalkEye,p.Z),Quaternion.Euler(p.Pitch,p.Yaw,0),p.Fov>0?p.Fov:75,1200,1920,1080,false,0,true);
                }
                count++;
            }}finally{fog.reviewTime=-1;}
            return count+" aerial review captures";
        }
    }
}
