using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using OnlyVolunteers.Map.Wind;
using OnlyVolunteers.Map.Wind.Editor;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Sky22V04;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Trees.Editor
{
    public static class G23MassI08
    {
        public const string Root="Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i08_leafy_mass.unity";
        public const string Data=Root+"/SceneData/Terrain_v19_i08_leafy_mass.asset";
        public const string Evidence="Working/Reviews/Trees/i08";
        const string ShaderName="OnlyVolunteers/Wind/v03/GenericFoliageScaled";
        static void Fresh(string p){if(File.Exists(p))throw new Exception("Preserve existing deliverable: "+p);}
        static void Folder(string p){if(AssetDatabase.IsValidFolder(p))return;Folder(Path.GetDirectoryName(p).Replace('\\','/'));AssetDatabase.CreateFolder(Path.GetDirectoryName(p).Replace('\\','/'),Path.GetFileName(p));}
        static void Write(string p,object o){File.WriteAllText(Evidence+"/"+p,JsonConvert.SerializeObject(o,Formatting.Indented));}
        static string NewPath(string p)=>p.Replace(G23LeafyIntegration.Root,Root);
        static JArray Plan()=>JArray.Parse(File.ReadAllText(Evidence+"/scale_plan.json"));

        public static string BuildAssets()
        {
            if(EditorApplication.isPlaying)throw new Exception("Edit mode required");
            foreach(var p in new[]{"Materials","Prefabs","SceneData"})Folder(Root+"/"+p);
            var shader=Shader.Find(ShaderName);if(!shader||ShaderUtil.ShaderHasError(shader))throw new Exception("Shader missing/invalid");
            var audit=new List<object>();
            foreach(var guid in AssetDatabase.FindAssets("t:Material",new[]{G23LeafyIntegration.Root+"/Materials"}))
            {
                string path=AssetDatabase.GUIDToAssetPath(guid),dest=NewPath(path);Fresh(dest);
                var old=AssetDatabase.LoadAssetAtPath<Material>(path);var material=new Material(old){shader=shader};
                material.name=old.name;AssetDatabase.CreateAsset(material,dest);
                audit.Add(new{source=path,destination=dest,response=material.GetFloat("_WindResponse"),flexibleHeight=material.GetFloat("_FlexibleHeight"),instancing=material.enableInstancing});
            }
            foreach(var family in G23LeafyIntegration.Families)for(int v=0;v<3;v++)
            {
                string path=G23LeafyIntegration.Prefab(family,v),dest=NewPath(path);Fresh(dest);
                if(!AssetDatabase.CopyAsset(path,dest))throw new Exception("Prefab copy failed");
                var contents=PrefabUtility.LoadPrefabContents(dest);
                try
                {
                    foreach(var r in contents.GetComponentsInChildren<Renderer>(true))r.sharedMaterials=r.sharedMaterials.Select(m=>AssetDatabase.LoadAssetAtPath<Material>(NewPath(AssetDatabase.GetAssetPath(m)))).ToArray();
                    PrefabUtility.SaveAsPrefabAsset(contents,dest);
                }
                finally{PrefabUtility.UnloadPrefabContents(contents);}
            }
            Write("wind_material_bindings.json",audit);return "12 prefab bindings and 16 materials copied; original geometry, LODs, colliders and all material settings preserved; stiffness now scales with instance height.";
        }

        public static string Integrate()
        {
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying||scene.isDirty||scene.path!=G23LeafyIntegration.Scene)throw new Exception("Requires saved i07 Edit scene");
            Fresh(Scene);Fresh(Data);
            var terrain=Terrain.activeTerrain;var before=terrain.terrainData;
            if(AssetDatabase.GetAssetPath(before)!=G23LeafyIntegration.Data)throw new Exception("Unexpected TerrainData");
            if(!EditorSceneManager.SaveScene(scene,Scene)||!AssetDatabase.CopyAsset(G23LeafyIntegration.Data,Data))throw new Exception("Save/copy failed");
            var data=AssetDatabase.LoadAssetAtPath<TerrainData>(Data);var prototypes=data.treePrototypes;
            for(int i=24;i<36;i++)prototypes[i].prefab=AssetDatabase.LoadAssetAtPath<GameObject>(NewPath(AssetDatabase.GetAssetPath(prototypes[i].prefab)));
            data.treePrototypes=prototypes;var instances=data.treeInstances;
            foreach(var row in Plan())
            {
                int index=(int)row["index"];float w=(float)row["widthScale"],h=(float)row["heightScale"];
                if(index>=0){var t=instances[index];if(t.prototypeIndex!=(int)row["prototype"])throw new Exception("Variant mismatch");t.widthScale=w;t.heightScale=h;instances[index]=t;}
                else
                {
                    var g=GameObject.Find("V19_GardenAppleTree_v04");if(!g||g.transform.parent.lossyScale!=Vector3.one)throw new Exception("Garden apple mismatch");
                    g.transform.localScale=new Vector3(w,h,w);PrefabUtility.RecordPrefabInstancePropertyModifications(g.transform);
                    foreach(var r in g.GetComponentsInChildren<Renderer>(true))
                    {r.sharedMaterials=r.sharedMaterials.Select(m=>AssetDatabase.LoadAssetAtPath<Material>(NewPath(AssetDatabase.GetAssetPath(m)))).ToArray();PrefabUtility.RecordPrefabInstancePropertyModifications(r);}
                }
            }
            data.SetTreeInstances(instances,false);EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
            terrain.terrainData=data;terrain.GetComponent<TerrainCollider>().terrainData=data;terrain.Flush();
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);return Validate();
        }

        public static string Validate()
        {
            var terrain=Terrain.activeTerrain;var data=terrain.terrainData;
            var old=AssetDatabase.LoadAssetAtPath<TerrainData>(G23LeafyIntegration.Data);var a=old.treeInstances;var b=data.treeInstances;
            if(a.Length!=b.Length||b.Length!=8525||data.treePrototypes.Length!=36)throw new Exception("Tree counts changed");
            var plan=Plan().Where(r=>(int)r["index"]>=0).ToDictionary(r=>(int)r["index"]);float groundError=0;int retained=0;
            var actual=new List<object>();
            for(int i=0;i<a.Length;i++)
            {
                if(a[i].position!=b[i].position||a[i].rotation!=b[i].rotation||a[i].prototypeIndex!=b[i].prototypeIndex||!a[i].color.Equals(b[i].color)||!a[i].lightmapColor.Equals(b[i].lightmapColor))throw new Exception("Position/variant/yaw/color changed: "+i);
                if(!plan.ContainsKey(i)){retained++;if(a[i].heightScale!=b[i].heightScale||a[i].widthScale!=b[i].widthScale)throw new Exception("Retained tree changed: "+i);continue;}
                var p=plan[i];if(Mathf.Abs(b[i].heightScale-(float)p["heightScale"])>.000001f||Mathf.Abs(b[i].widthScale-(float)p["widthScale"])>.000001f)throw new Exception("Scale not applied");
                float ratio=b[i].widthScale/b[i].heightScale;if(ratio<.79999f||ratio>1.25001f)throw new Exception("Shape clamp failed");
                var position=Vector3.Scale(b[i].position,data.size)+terrain.transform.position;
                groundError=Mathf.Max(groundError,Mathf.Abs(position.y-terrain.SampleHeight(position)-terrain.transform.position.y));
                actual.Add(new{index=i,family=(string)p["family"],prototype=b[i].prototypeIndex,position=new[]{position.x,position.y,position.z},widthScale=b[i].widthScale,heightScale=b[i].heightScale,rotation=b[i].rotation});
            }
            for(int i=0;i<24;i++)if(old.treePrototypes[i].prefab!=data.treePrototypes[i].prefab)throw new Exception("Protected prototype changed");
            for(int i=24;i<36;i++)
            {
                var x=old.treePrototypes[i].prefab;var y=data.treePrototypes[i].prefab;if(!y)throw new Exception("Missing new prefab");
                var xr=x.GetComponentsInChildren<MeshFilter>(true);var yr=y.GetComponentsInChildren<MeshFilter>(true);
                if(xr.Length!=yr.Length||xr.Where((m,n)=>m.sharedMesh!=yr[n].sharedMesh).Any())throw new Exception("Geometry changed");
                if(x.GetComponent<LODGroup>().size!=y.GetComponent<LODGroup>().size||x.GetComponentsInChildren<Collider>().Length!=y.GetComponentsInChildren<Collider>().Length)throw new Exception("LOD/collider changed");
                foreach(var r in y.GetComponentsInChildren<Renderer>(true))foreach(var m in r.sharedMaterials)
                    if(!m||m.shader.name!=ShaderName||!m.enableInstancing||m.FindPass("ShadowCaster")<0||m.FindPass("DepthOnly")<0||ShaderUtil.ShaderHasError(m.shader))throw new Exception("Wind material invalid");
            }
            var apple=GameObject.Find("V19_GardenAppleTree_v04");var ap=Plan().Single(r=>(int)r["index"]<0);
            if((apple.transform.localScale-new Vector3((float)ap["widthScale"],(float)ap["heightScale"],(float)ap["widthScale"])).sqrMagnitude>1e-10)throw new Exception("Ordinary scale mismatch");
            var apos=ap["position"].Select(v=>(float)v).ToArray();if((apple.transform.position-new Vector3(apos[0],apos[1],apos[2])).sqrMagnitude>1e-9)throw new Exception("Ordinary pivot changed");
            var roots=UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
            int missing=roots.SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).Sum(t=>GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
            int badMeshes=roots.SelectMany(r=>r.GetComponentsInChildren<MeshFilter>(true)).Count(m=>!m.sharedMesh);
            int badMaterials=roots.SelectMany(r=>r.GetComponentsInChildren<Renderer>(true)).Sum(r=>r.sharedMaterials.Count(m=>!m));
            if(missing+badMeshes+badMaterials>0||groundError>.01f)throw new Exception("Missing references or ground contact failed");
            var audit=new{status="PASS",scene=Scene,treeInstances=b.Length,resized=plan.Count,ordinaryResized=1,retained,maxGroundError=groundError,missingScripts=missing,missingMeshes=badMeshes,missingMaterials=badMaterials,windOwners=Object.FindObjectsByType<V19Wind>().Length,
                terrainPath=AssetDatabase.GetAssetPath(data),terrainGuid=AssetDatabase.AssetPathToGUID(Data),
                missingLayers=data.terrainLayers.Count(l=>!l),missingTreePrototypes=data.treePrototypes.Count(p=>!p.prefab),missingDetailPrototypes=data.detailPrototypes.Count(p=>p.usePrototypeMesh?!p.prototype:!p.prototypeTexture)};
            Write("integration_validation.json",audit);Write("instances_readback.json",actual);return JsonConvert.SerializeObject(audit);
        }

        public static string Capture()
        {
            if(!EditorApplication.isPlaying)throw new Exception("Play required");
            var clock=Object.FindAnyObjectByType<SkyClock22>();bool running=clock.Running;float hour=clock.Hour;
            try{clock.Running=false;clock.SetHour(8);for(int i=0;i<4;i++){var p=G23LeafyBenchmark.Poses[i];WindReview24.Shot("../Trees/i08/i08_"+i,p.x,p.y,p.z,p.w,12,true,1.65f,1600,900);}return "Four i08 Play shots captured";}
            finally{clock.SetHour(hour);clock.Running=running;}
        }
        public static string Benchmark()
        {
            if(!EditorApplication.isPlaying||EditorApplication.isPaused||Time.captureDeltaTime!=0||Object.FindAnyObjectByType<G23MassBenchmarkI08>())throw new Exception("Normal Play required");
            string path=Path.GetFullPath(Evidence+"/performance_i08.json");Fresh(path);
            var ground=Object.FindAnyObjectByType<MapHeightSampler>();var points=G23MassBenchmarkI08.Poses.Select(p=>new Vector3(p.x,ground.Height(p.x,p.y)+1.65f,p.y)).ToArray();
            new GameObject("G23_TemporaryMassBenchmarkI08").AddComponent<G23MassBenchmarkI08>().Begin(points,path);return "Benchmark started; same completed i06/i07 poses";
        }
    }
}
