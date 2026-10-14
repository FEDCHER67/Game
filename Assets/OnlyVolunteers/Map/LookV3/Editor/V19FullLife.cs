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
    // Extends the approved small storytelling kit. DistrictLife remains the single lightweight flyer behaviour.
    public static class V19FullLife
    {
        static Transform root;static MapHeightSampler ground;static readonly List<DistrictLife19V02.Flyer> flyers=new();
        static readonly List<string> log=new();const string Output=V19FullPalette.Output+"/Life";
        static GameObject Kit(string id,float x,float z,float yaw=0,float height=0)
        {
            // Review round 1 moves the extra household story clusters with their plots.
            // Curtains already derive their positions from the current building footprints.
            if(id!="CURTAIN_PAIR")
            {
                if(x>=285 && x<=311 && z>=497 && z<=517){x-=7;z+=1;}
                else if(x>=324 && x<=348 && z>=488 && z<=506)x-=20;
                else if(x>=170 && x<=182 && z>=555 && z<=570){x-=1;z-=8;}
            }
            var asset=AssetDatabase.LoadAssetAtPath<GameObject>(V19PaletteP2.Kit+"/Prefabs/"+id+"_v02.prefab");
            if(!asset)throw new IOException("Missing kit "+id);var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);go.name="Full19_"+id;go.transform.SetParent(root,false);
            go.transform.position=new Vector3(x,ground.Height(x,z)+height,z);go.transform.rotation=Quaternion.Euler(0,yaw,0);return go;
        }
        static Material Mat(string name,string hex)
        {var mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=name};mat.SetColor("_BaseColor",V19PaletteP2.C(hex));mat.SetFloat("_Smoothness",.05f);AssetDatabase.CreateAsset(mat,Output+"/"+name+".mat");return mat;}
        static Transform Wing(Transform body,float side,Material mat,float scale)
        {
            var mesh=new Mesh{name="Full19_BirdWing"};mesh.vertices=new[]{Vector3.zero,new Vector3(side*.6f*scale,0,-.06f),new Vector3(side*.3f*scale,0,-.26f)};mesh.triangles=new[]{0,1,2,2,1,0};mesh.RecalculateNormals();mesh.RecalculateBounds();
            string path=AssetDatabase.GenerateUniqueAssetPath(Output+"/Wing.asset");AssetDatabase.CreateAsset(mesh,path);
            var go=new GameObject("FlappingWing");go.transform.SetParent(body,false);go.transform.localPosition=Vector3.up*.2f;go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterial=mat;return go.transform;
        }
        static void Birds(string name,float x,float z,int count,Material mat,float scale,float height,float radius)
        {
            for(int i=0;i<count;i++)
            {
                var go=Kit("CROW",x,z,0,height+i*.35f);go.name="Full19_"+name+"_"+i;
                foreach(var r in go.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=Enumerable.Repeat(mat,r.sharedMaterials.Length).ToArray();
                foreach(var c in go.GetComponentsInChildren<Collider>())Object.DestroyImmediate(c);
                go.transform.localScale=Vector3.one*scale;
                if(i<2){var roof=MapLookBuilder.Load("v19").buildings.OrderBy(b=>(b.x-x)*(b.x-x)+(b.y-z)*(b.y-z)).First();go.transform.position=new Vector3(roof.x+i*1.1f,ground.Height(roof.x,roof.y)+roof.h+.45f,roof.y+i*.35f);continue;}
                var f=new DistrictLife19V02.Flyer{body=go.transform,leftWing=Wing(go.transform,-1,mat,1),rightWing=Wing(go.transform,1,mat,1),centre=go.transform.position,radius=radius+i*.7f,speed=.18f+i*.009f,phase=i*1.31f,flap=6.5f};
                go.transform.position+=new Vector3(Mathf.Cos(f.phase)*f.radius,0,Mathf.Sin(f.phase)*f.radius*.64f);flyers.Add(f);
            }
            log.Add(name+": "+count+" birds at "+x+","+z+"; 2 perched, remainder circling");
        }
        static void Smoke(Vector3 p)
        {
            var source=GameObject.Find("V19_Life_CheckpointP_v02_Full_v01").GetComponentsInChildren<ParticleSystem>().First();
            var go=Object.Instantiate(source.gameObject,root);go.name="Full19_OccupiedChimney";go.transform.position=p;
        }
        public static string Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");if(GameObject.Find("V19_Life_Full_v01"))throw new IOException("Life already placed");
            ground=Object.FindAnyObjectByType<MapHeightSampler>();root=new GameObject("V19_Life_Full_v01").transform;LookAssetStore.EnsureFolder(Output);flyers.Clear();log.Clear();
            // Three additional households: a gardener, a bicycle owner's gate, and an inhabited northern house.
            Kit("FLOWER_BED",294,509.4f,0);Kit("BUCKET_WATERING",296.2f,510,45);Kit("BICYCLE",302.7f,504.2f,12);
            Kit("APPLE_BASKET",301.6f,508.8f,15);Kit("LAUNDRY_CLOTHES",298,511,0);
            Kit("FLOWER_BED",332.1f,500.1f,0);Kit("DOGHOUSE",339.1f,500.5f,180);Kit("AXE_STUMP_LOGS",340.5f,495.4f,55);
            Kit("FLOWER_BED",174.4f,564.9f,0);Kit("BUCKET_WATERING",178.8f,565.2f,25);
            // Curtains sit just behind existing windows; warm panes use a small emissive quad, not a new house material.
            var warm=Mat("Full19_WarmWindow","#DDA666");warm.EnableKeyword("_EMISSION");warm.SetColor("_EmissionColor",new Color(.55f,.24f,.06f));EditorUtility.SetDirty(warm);
            foreach(var b in MapLookBuilder.Load("v19").buildings.Where(b=>new[]{"02_B05","02_house_18","02_house_20"}.Contains(b.id)))
            {
                float z=b.fp.Where((v,i)=>i%2==1).Min(),y=ground.Height(b.x,b.y);
                var curtain=Kit("CURTAIN_PAIR",b.x-1.7f,z+.06f,0,1.1f);curtain.transform.position=new Vector3(b.x-1.7f,y+1.1f,z+.06f);
                var window=GameObject.CreatePrimitive(PrimitiveType.Quad);window.name="Full19_WarmPane";window.transform.SetParent(root,false);window.transform.position=new Vector3(b.x-1.7f,y+1.55f,z-.012f);window.transform.localScale=new Vector3(.76f,.68f,1);Object.DestroyImmediate(window.GetComponent<Collider>());window.GetComponent<MeshRenderer>().sharedMaterial=warm;
                Smoke(new Vector3(b.x+1.8f,y+b.h+1.1f,b.y));
            }
            Material pigeon=Mat("Full19_PigeonSlate","#656A76"),gull=Mat("Full19_GullIvory","#DEDCD3"),song=Mat("Full19_SongbirdBrown","#736149"),crow=AssetDatabase.LoadAssetAtPath<Material>(V19PaletteP2.Output+"/Materials/V19_CrowBlack.mat");
            Birds("DowntownPigeons",936,476,7,pigeon,.85f,9,10);Birds("BeachGulls",938,218,6,gull,1.12f,5,16);
            Birds("PortGulls",946,661,6,gull,1.12f,9,17);Birds("TramduroGulls",1308,627,5,gull,1.12f,8,18);
            Birds("EliteSongbirds",1217,419,4,song,.5f,4,6);Birds("ValleyLarks",558,255,4,song,.5f,5,9);
            Birds("HamletSongbirds",298,511,4,song,.5f,4,7);Birds("ForestEdgeCrows",322,301,4,crow,1,7,10);
            for(int i=0;i<5;i++){var go=Kit("BUTTERFLY",294+i*.35f,509.4f,0,.9f);flyers.Add(new(){body=go.transform,centre=go.transform.position,radius=.5f,speed=.8f+i*.1f,phase=i*1.6f,flap=18});}
            root.gameObject.AddComponent<DistrictLife19V02>().flyers=flyers.ToArray();
            log.Add("Three household clusters, 3 curtain/warm pane pairs, 3 additional chimney emitters, 5 butterflies. Existing Rough crows/black palette preserved. No new audio downloads.");
            AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(root.gameObject.scene);EditorSceneManager.SaveScene(root.gameObject.scene);
            string text=string.Join("\n",log);File.WriteAllText(V19PilotTools.OutDir+"/life_full_v07.txt",text);return text;
        }
    }
}
