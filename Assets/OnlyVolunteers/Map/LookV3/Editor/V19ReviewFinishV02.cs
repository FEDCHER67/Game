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
    // Additive round-1 finish. Original kits, terrain and previous review assets stay intact.
    public static class V19ReviewFinishV02
    {
        public const string Folder="Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v07/ReviewFinish_v02";
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(!scene.name.StartsWith("Map_Look_v19"))throw new InvalidOperationException("v19 scene required");
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();
            var fog=Object.FindAnyObjectByType<DistrictFog19V05>();
            if(!ground || !fog)throw new InvalidOperationException("Prepared v19 Look required");
            LookAssetStore.EnsureFolder(Folder);
            fog.roughDensity=Mathf.Lerp(.0048f,.031f,.5f);
            fog.roughHazeStart=Mathf.Lerp(45,0,.5f);
            fog.roughGroundWeight=.5f;
            fog.roughDropletLimit=82;
            fog.roughDropletOpacity=Mathf.Lerp(.018f,.13f,.5f);
            // Match each surviving pocket to its original v03 bank index. For banks absent
            // in v04, interpolate opacity from zero while expanding the low layer halfway.
            int[] originalIndex={1,6,8,0,2,3,4,5,7,9,10,11,12,13};
            int j=0;
            for(int i=0;i<fog.banks.Length;i++)
            {
                var b=fog.banks[i];if(b.forest)continue;
                int original=originalIndex[j];
                var targetSize=new Vector2(12+(original%4)*3,3+(original%3)*.7f);
                float targetHeight=1.7f+(original%3)*.45f;
                if(j<3)
                {
                    b.size=Vector2.Lerp(new Vector2(9+j,1.1f),targetSize,.5f);
                    b.position.y=ground.Height(b.position.x,b.position.z)+Mathf.Lerp(.65f,targetHeight,.5f);
                    b.opacity=Mathf.Lerp(.065f,.22f,.5f);
                }
                else
                {
                    b.size=new Vector2(targetSize.x,targetSize.y*.5f);
                    b.position.y=ground.Height(b.position.x,b.position.z)+targetHeight*.5f;
                    b.opacity=.11f;
                }
                fog.banks[i]=b;j++;
            }
            string materialPath=Folder+"/DepthHeightFog_v06.mat";
            var mat=AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if(!mat){mat=new Material(fog.fogTemplate){name="DepthHeightFog_v06_RoughHalf"};AssetDatabase.CreateAsset(mat,materialPath);}
            fog.fogTemplate=mat;
            if(!GameObject.Find("V19_R1_CourtyardFinish_v02"))
            {
                var parent=new GameObject("V19_R1_CourtyardFinish_v02").transform;
                Add("SHED_RUINED",684,586,0,parent,ground);
                Add("SHED_RUINED",696,586,8,parent,ground);
                foreach(float x in new[]{681f,684f,687f})foreach(float z in new[]{590f,593f})
                    Add("GARDEN_BED_2M",x,z,0,parent,ground);
                foreach(float x in new[]{680f,682f,686f,688f})Add("FENCE_PICKET_2M",x,588,0,parent,ground);
                foreach(float z in new[]{590f,592f})Add("FENCE_PICKET_2M",679,z,90,parent,ground);
                Add("BENCH_SOVIET",689,598,180,parent,ground);
                Strip("CourtyardWalk",new[]{new Vector2(676,596),new Vector2(690,596),new Vector2(703,596)},2.1f,parent,ground);
                Strip("GardenWorkSoil",new[]{new Vector2(680,591.5f),new Vector2(688,591.5f)},7,parent,ground);
                Strip("ShedAccess",new[]{new Vector2(684,586),new Vector2(691,590),new Vector2(691,596)},1.4f,parent,ground);
            }
            Physics.SyncTransforms();
            EditorUtility.SetDirty(fog);EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            return "Rough v06: density="+fog.roughDensity+", start="+fog.roughHazeStart+", ground="+(fog.groundExtinction*fog.roughGroundWeight)+", droplets="+fog.roughDropletLimit+" alpha="+fog.roughDropletOpacity+"; 14 Rough banks halfway, 4 Forest banks untouched; courtyard work garden and two source-sized sheds added";
        }
        static void Add(string module,float x,float z,float yaw,Transform parent,MapHeightSampler ground)
        {
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(V19Infill.Kit+"/Prefabs/"+module+"_v01.prefab");
            if(!prefab)throw new IOException(module+" missing");
            var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name="R1_"+module+"_"+x+"_"+z;
            go.transform.SetParent(parent,false);go.transform.position=new Vector3(x,ground.Height(x,z),z);go.transform.rotation=Quaternion.Euler(0,yaw,0);
        }
        static void Strip(string name,Vector2[] points,float width,Transform parent,MapHeightSampler ground)
        {
            string path=Folder+"/"+name+"_v02.asset";var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(!mesh)
            {
                var verts=new List<Vector3>();var uv=new List<Vector2>();var triangles=new List<int>();float travelled=0;
                for(int i=1;i<points.Length;i++)
                {
                    Vector2 a=points[i-1],b=points[i],delta=b-a,side=new Vector2(-delta.y,delta.x).normalized*width*.5f;
                    float len=delta.magnitude;int steps=Mathf.Max(1,Mathf.CeilToInt(len));
                    for(int n=0;n<steps;n++)
                    {
                        var start=Vector2.Lerp(a,b,n/(float)steps);var end=Vector2.Lerp(a,b,(n+1f)/steps);int v=verts.Count;
                        foreach(var p in new[]{start-side,start+side,end-side,end+side})verts.Add(new Vector3(p.x,ground.Height(p.x,p.y)+.035f,p.y));
                        float t0=(travelled+len*n/steps)/6,t1=(travelled+len*(n+1)/steps)/6;
                        uv.AddRange(new[]{new Vector2(0,t0),new Vector2(width/2,t0),new Vector2(0,t1),new Vector2(width/2,t1)});
                        triangles.AddRange(new[]{v,v+2,v+1,v+1,v+2,v+3});
                    }
                    travelled+=len;
                }
                mesh=new Mesh{name=name+"_v02"};mesh.SetVertices(verts);mesh.SetUVs(0,uv);mesh.SetTriangles(triangles,0);mesh.RecalculateNormals();mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,path);
            }
            var go=new GameObject(name);go.transform.SetParent(parent,false);go.AddComponent<MeshFilter>().sharedMesh=mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>(V19Infill.Kit+"/Decals/WORN_PATH_v01.mat");
        }
    }
}
