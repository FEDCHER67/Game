using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Sky22V04;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Wind.Editor
{
    public static class WindTreeReview23
    {
        [Serializable] public sealed class Pose {public string kind;public float x,z,yaw,pitch;public int prototype;public Vector3 tree;}
        [Serializable] public sealed class Poses {public Pose[] views;}
        static bool InsideBuilding(float x,float z,OnlyVolunteers.Map.Look.MapBuildingInfo[] buildings)
        {
            foreach(var b in buildings){if(b.Footprint==null||b.Footprint.Length<3)continue;var pts=new float[b.Footprint.Length*2];for(int i=0;i<b.Footprint.Length;i++){pts[i*2]=b.Footprint[i].x;pts[i*2+1]=b.Footprint[i].y;}if(LookGeom.Inside(pts,x,z))return true;}return false;
        }
        public static string FindPoses()
        {
            var terrain=Terrain.activeTerrain;var d=terrain.terrainData;var ground=Object.FindAnyObjectByType<MapHeightSampler>();
            var buildings=Object.FindObjectsByType<OnlyVolunteers.Map.Look.MapBuildingInfo>();
            string[] kinds={"Forest","Bare","Leafless"};
            Vector2[] anchors={new(214,190),new(650,650),new(700,615)};
            var result=new List<Pose>();
            for(int k=0;k<kinds.Length;k++)
            {
                var targets=d.treeInstances.Where(t=>kinds[k]=="Leafless"?t.prototypeIndex==16:WindTrees23.Kind(d.treePrototypes[t.prototypeIndex].prefab.name)==kinds[k]&&(kinds[k]!="Bare"||t.prototypeIndex>=17));
                var ranked=targets.OrderBy(t=>Vector2.Distance(new Vector2(t.position.x*d.size.x+terrain.transform.position.x,t.position.z*d.size.z+terrain.transform.position.z),anchors[k]));
                Pose chosen=null;
                foreach(var tr in ranked.Take(70))
                {
                    Vector3 at=Vector3.Scale(tr.position,d.size)+terrain.transform.position;var prefab=d.treePrototypes[tr.prototypeIndex].prefab;
                    float height=prefab.GetComponentsInChildren<MeshFilter>(true).Max(m=>m.sharedMesh.bounds.max.y)*tr.heightScale;
                    for(int turn=0;turn<8;turn++)
                    {
                        float angle=(145+turn*45)*Mathf.Deg2Rad;float distance=Mathf.Max(3.5f,height*1.35f);
                        var p=at+new Vector3(Mathf.Sin(angle),0,Mathf.Cos(angle))*distance;
                        if(InsideBuilding(p.x,p.z,buildings)||ground.InWater(p.x,p.z,out _))continue;
                        if(d.treeInstances.Any(other=>{var q=Vector3.Scale(other.position,d.size)+terrain.transform.position;return Vector2.Distance(new Vector2(p.x,p.z),new Vector2(q.x,q.z))<1.4f;}))continue;
                        p.y=ground.Height(p.x,p.z)+1.65f;Vector3 look=(at+Vector3.up*height*.45f)-p;var rot=Quaternion.LookRotation(look).eulerAngles;
                        chosen=new Pose{kind=kinds[k],x=p.x,z=p.z,yaw=rot.y,pitch=rot.x>180?rot.x-360:rot.x,prototype=tr.prototypeIndex,tree=at};break;
                    }
                    if(chosen!=null)break;
                }
                if(chosen==null)throw new Exception("No review pose for "+kinds[k]);result.Add(chosen);
            }
            File.WriteAllText(WindTrees23.Evidence+"/poses.json",JsonUtility.ToJson(new Poses{views=result.ToArray()},true));return string.Join("\n",result.Select(p=>p.kind+" "+p.x+","+p.z+" yaw="+p.yaw));
        }
        public static string Shot(int row,int frame,string prefix="sequence")
        {
            var poses=JsonUtility.FromJson<Poses>(File.ReadAllText(WindTrees23.Evidence+"/poses.json"));var p=poses.views[row];
            return WindReview24.Shot("trees_i06/"+prefix+"_"+p.kind+"_"+frame.ToString("00"),p.x,p.z,p.yaw,p.pitch,12+frame*.8f,true,1.65f,800,450);
        }
        public static string StartPerformance(string label)
        {
            if(!EditorApplication.isPlaying||EditorApplication.isPaused||Time.captureDeltaTime!=0||Time.frameCount<60||Object.FindAnyObjectByType<WindTreePerformance23>())throw new Exception("Requires initialized normal Play and no active benchmark");
            string path=Path.GetFullPath(WindTrees23.Evidence+"/performance_"+label+".json");if(File.Exists(path))throw new Exception("Evidence exists");
            var manifest=JsonUtility.FromJson<WindTrees23.Manifest>(File.ReadAllText(WindTrees23.Evidence+"/installation.json"));
            var lookup=manifest.materials.ToDictionary(m=>m.after,m=>AssetDatabase.LoadAssetAtPath<Material>(m.before));
            var bindings=new List<WindTreePerformance23.Binding>();
            foreach(var renderer in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include))if(WindTrees23.IsVegetation(renderer)&&renderer.sharedMaterials.Any(m=>m&&m.shader.name=="OnlyVolunteers/Wind/v02/GenericFoliage")){var after=renderer.sharedMaterials;bindings.Add(new WindTreePerformance23.Binding{renderer=renderer,after=after,before=after.Select(m=>lookup[AssetDatabase.GetAssetPath(m)]).ToArray()});}
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var positions=new[]{new Vector3(170,0,425),new Vector3(214,0,190),new Vector3(832,0,180),new Vector3(640,0,655)};
            for(int i=0;i<positions.Length;i++)positions[i].y=ground.Height(positions[i].x,positions[i].z)+1.65f;
            new GameObject("G23_TemporaryPerformance").AddComponent<WindTreePerformance23>().Begin(AssetDatabase.LoadAssetAtPath<TerrainData>(WindTrees23.OriginalData),bindings.ToArray(),positions,new float[]{0,320,165,90},path);
            return "Started "+path;
        }
    }
}
