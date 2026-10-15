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
using Object=UnityEngine.Object;
namespace OnlyVolunteers.Trees.Editor {
public static class G23OaksPinesI09 {
public const string Root="Assets/OnlyVolunteers/Art/Trees/OaksPines_i09";
public const string Base=G23MassI08.Scene;
public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i09_oaks_pines.unity";
public const string Data=Root+"/SceneData/Terrain_v19_i09_oaks_pines.asset";
public const string Evidence="Working/Reviews/Trees/i09";
const string Staging="ArtSource/Dev/Trees_staging/i09_v01";
static readonly string[] Families={"Oak","Pine"};
static string Revision(string f)=>f=="Oak"?"v01_02":"v04";
static string Prefab(string f,int v)=>Root+"/Prefabs/"+f+"_"+(char)('A'+v)+"_"+Revision(f)+".prefab";
static string Kind(int i)=>i==0||i==1||i==2?"Oak":i==12||i==13||i==15?"Pine":null;
static void Fresh(string p){if(File.Exists(p))throw new Exception("Preserve existing: "+p);}
static void Folder(string p){if(AssetDatabase.IsValidFolder(p))return;var a=Path.GetDirectoryName(p).Replace('\\','/');Folder(a);AssetDatabase.CreateFolder(a,Path.GetFileName(p));}
static float[] XYZ(Vector3 p)=>new[]{p.x,p.y,p.z};
static void Write(string p,object o)=>File.WriteAllText(Evidence+"/"+p,JsonConvert.SerializeObject(o,Formatting.Indented));
        public static string BuildAssets()
        {
            if(EditorApplication.isPlaying)throw new Exception("Edit mode required");
            foreach(var folder in new[]{"Meshes","Prefabs","SceneData"})Folder(Root+"/"+folder);
            var shader=Shader.Find("OnlyVolunteers/Wind/v03/GenericFoliageScaled");
            foreach(var guid in AssetDatabase.FindAssets("t:Material",new[]{Root+"/Materials"})){
                var mat=AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));mat.shader=shader;mat.enableInstancing=true;EditorUtility.SetDirty(mat);
            }
            AssetDatabase.SaveAssets();
            var specs=JArray.Parse(File.ReadAllText(Staging+"/approved_specs.json"));
            var remaps=JObject.Parse(File.ReadAllText("ArtSource/Dev/Trees_staging/oaks_pines_v01/wind_bindings_v01.json"))["material_remaps"];
            var records=new List<object>();
            foreach(var family in Families)for(int variant=0;variant<3;variant++)
            {
                string id=family+"_"+(char)('A'+variant), revision=Revision(family), path=Root+"/Models/"+id+"_"+revision+".fbx";
                Fresh(Prefab(family,variant));
                var spec=specs.Single(s=>(string)s["id"]==id);float height=(float)spec["height"];
                var importer=(ModelImporter)AssetImporter.GetAtPath(path);
                importer.globalScale=1;importer.useFileUnits=true;importer.bakeAxisConversion=true;
                importer.isReadable=true;importer.importAnimation=false;importer.importCameras=false;importer.importLights=false;
                importer.meshCompression=ModelImporterMeshCompression.Off;importer.importNormals=ModelImporterNormals.Import;
                importer.SaveAndReimport();
                var source=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var root=new GameObject(id+"_"+revision);
                try
                {
                    var lods=new LOD[3];Bounds geometry=new Bounds();
                    for(int lod=0;lod<3;lod++)
                    {
                        var mf=source.GetComponentsInChildren<MeshFilter>(true).Single(m=>m.name.EndsWith("_LOD"+lod));
                        var mesh=Object.Instantiate(mf.sharedMesh);mesh.name=id+"_"+revision+"_LOD"+lod;
                        var transform=source.transform.worldToLocalMatrix*mf.transform.localToWorldMatrix;
                        mesh.vertices=mesh.vertices.Select(transform.MultiplyPoint3x4).ToArray();
                        var normals=transform.inverse.transpose;
                        mesh.normals=mesh.normals.Select(n=>normals.MultiplyVector(n).normalized).ToArray();
                        mesh.RecalculateTangents();mesh.RecalculateBounds();
                        if(Mathf.Abs(mesh.bounds.size.y-height)>.012f||Mathf.Abs(mesh.bounds.min.y)>.012f)throw new Exception("Import axes/units/base mismatch: "+mesh.name+mesh.bounds);
                        var trueBounds=mesh.bounds;if(lod==0)geometry=trueBounds;
                        // Generic wind bend bounds, baked into only the new derived mesh assets.
                        float response=family=="Oak"?.055f:.028f;
                        float maximumAngle=Mathf.Min(.7854f,.69814f*response*1.2f);
                        float pad=2*Mathf.Sin(maximumAngle/2)*(height+trueBounds.extents.magnitude)+.06f;
                        var padded=trueBounds;padded.Expand(Vector3.one*2*pad);mesh.bounds=padded;
                        string meshPath=Root+"/Meshes/"+mesh.name+".asset";Fresh(meshPath);AssetDatabase.CreateAsset(mesh,meshPath);
                        var child=new GameObject("LOD"+lod);child.transform.SetParent(root.transform,false);
                        child.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=child.AddComponent<MeshRenderer>();
                        renderer.sharedMaterials=mf.GetComponent<Renderer>().sharedMaterials.Select(m=>
                        {
                            string mapping=(string)remaps[family][m.name];if(mapping==null)throw new Exception("Missing material mapping "+m.name);
                            return AssetDatabase.LoadAssetAtPath<Material>(Root+"/Materials/"+Path.GetFileName(mapping.Replace('\\','/')));
                        }).ToArray();
                        if(renderer.sharedMaterials.Any(m=>!m||!m.enableInstancing||m.shader.name!="OnlyVolunteers/Wind/v03/GenericFoliageScaled"||ShaderUtil.ShaderHasError(m.shader)))throw new Exception("Shared wind binding invalid");
                        renderer.shadowCastingMode=ShadowCastingMode.On;renderer.receiveShadows=true;
                        lods[lod]=new LOD(new[]{.23f,.085f,.008f}[lod],new Renderer[]{renderer});
                        long tris=Enumerable.Range(0,mesh.subMeshCount).Sum(i=>(long)mesh.GetIndexCount(i)/3);
                        records.Add(new{id,lod,triangles=tris,height=height,geometryCenter=XYZ(trueBounds.center),geometrySize=XYZ(trueBounds.size),windPadding=pad,materials=renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray()});
                    }
                    var group=root.AddComponent<LODGroup>();group.fadeMode=LODFadeMode.None;group.SetLODs(lods);group.RecalculateBounds();
                    // Bounds padding must not inflate draw distances and delay the three LOD transitions.
                    float ratio=group.size/Mathf.Max(geometry.size.x,geometry.size.y,geometry.size.z);
                    for(int i=0;i<lods.Length;i++)lods[i].screenRelativeTransitionHeight*=ratio;
                    group.SetLODs(lods);
                    if(family!="Bush")foreach(var cap in spec["colliders"])
                    {
                        var holder=new GameObject("TrunkCapsule");holder.transform.SetParent(root.transform,false);
                        var center=cap["center_Unity"].Select(v=>(float)v).ToArray();var axis=cap["axis_Unity"].Select(v=>(float)v).ToArray();
                        // These approved capsule recipes already use Blender Y -> Unity +Z.
                        holder.transform.localPosition=new Vector3(center[0],center[1],center[2]);
                        holder.transform.localRotation=Quaternion.FromToRotation(Vector3.up,new Vector3(axis[0],axis[1],axis[2]));
                        var collider=holder.AddComponent<CapsuleCollider>();collider.direction=1;collider.radius=(float)cap["radius_m"];collider.height=(float)cap["height_m"];
                    }
                    PrefabUtility.SaveAsPrefabAsset(root,Prefab(family,variant));
                }
                finally{Object.DestroyImmediate(root);}
                importer.isReadable=false;importer.SaveAndReimport();
            }
            Write("asset_validation.json",records);return "Built 6 approved prefabs and 18 LODs; shared scaled wind; 12 trunk capsules.";
        }

static Vector2 Dimensions(GameObject prefab) {
    var mf=prefab.GetComponent<LODGroup>().GetLODs()[0].renderers[0].GetComponent<MeshFilter>();
    var matrix=prefab.transform.worldToLocalMatrix*mf.transform.localToWorldMatrix;
    var verts=mf.sharedMesh.vertices.Select(matrix.MultiplyPoint3x4).ToArray();
    var mats=mf.GetComponent<Renderer>().sharedMaterials;var leaves=new List<Vector3>();
    for(int s=0;s<mf.sharedMesh.subMeshCount;s++)if(mats[s].name.IndexOf("Leaf",StringComparison.OrdinalIgnoreCase)>=0)
        leaves.AddRange(mf.sharedMesh.GetTriangles(s).Distinct().Select(i=>verts[i]));
    if(leaves.Count==0)throw new Exception("No leaf geometry: "+prefab.name);
    return new Vector2(verts.Max(p=>p.y)-verts.Min(p=>p.y),Mathf.Max(leaves.Max(p=>p.x)-leaves.Min(p=>p.x),leaves.Max(p=>p.z)-leaves.Min(p=>p.z)));
}
public static string Integrate() {
    var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
    if(EditorApplication.isPlaying||scene.isDirty||scene.path!=Base)throw new Exception("Requires clean i08 Edit scene");
    Fresh(Scene);Fresh(Data);var terrain=Terrain.activeTerrain;var old=terrain.terrainData;
    if(AssetDatabase.GetAssetPath(old)!=G23MassI08.Data)throw new Exception("Unexpected source TerrainData");
    var protos=old.treePrototypes.ToList();var dims=protos.Select((p,i)=>Kind(i)==null?Vector2.zero:Dimensions(p.prefab)).ToList();
    foreach(var f in Families)for(int v=0;v<3;v++){var p=AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(f,v));protos.Add(new TreePrototype{prefab=p,bendFactor=0});dims.Add(Dimensions(p));}
    if(!EditorSceneManager.SaveScene(scene,Scene)||!AssetDatabase.CopyAsset(G23MassI08.Data,Data))throw new Exception("Save/copy failed");
    var data=AssetDatabase.LoadAssetAtPath<TerrainData>(Data);data.treePrototypes=protos.ToArray();var instances=old.treeInstances;
    var rng=new System.Random(230409);var rows=new List<object>();
    for(int i=0;i<instances.Length;i++){
        var t=instances[i];var f=Kind(t.prototypeIndex);if(f==null)continue;
        int v=rng.Next(3),slot=36+Array.IndexOf(Families,f)*3+v;float jitter=.9f+.2f*(float)rng.NextDouble(),yaw=(float)rng.NextDouble()*Mathf.PI*2;
        var a=dims[t.prototypeIndex];var b=dims[slot];float h=a.x*t.heightScale/b.x*jitter,w=a.y*t.widthScale/b.y*jitter,ratio=w/h;
        float newH=w/Mathf.Clamp(ratio,.8f,1.25f);
        rows.Add(new{index=i,family=f,variant=((char)('A'+v)).ToString(),oldPrototype=t.prototypeIndex,newPrototype=slot,jitter,yaw,
            oldNativeHeight=a.x,oldNativeWidth=a.y,newNativeHeight=b.x,newNativeWidth=b.y,
            i08Height=a.x*t.heightScale,i08Width=a.y*t.widthScale,i09Height=b.x*newH,i09Width=b.y*w,
            widthScale=w,heightScale=newH,requestedRatio=ratio,clamped=ratio<.8f||ratio>1.25f,position=XYZ(Vector3.Scale(t.position,data.size)+terrain.transform.position)});
        t.prototypeIndex=slot;t.rotation=yaw;t.widthScale=w;t.heightScale=newH;instances[i]=t;
    }
    if(rows.Count!=2778)throw new Exception("Expected 2778 replacements, found "+rows.Count);
    data.SetTreeInstances(instances,false);EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
    terrain.terrainData=data;terrain.GetComponent<TerrainCollider>().terrainData=data;terrain.Flush();
    Write("replacements.json",rows);Write("native_dimensions.json",dims.Select((p,i)=>new{slot=i,height=p.x,width=p.y}).ToArray());
    EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);return Validate();
}
public static string Validate() {
    var old=AssetDatabase.LoadAssetAtPath<TerrainData>(G23MassI08.Data);var terrain=Terrain.activeTerrain;var data=terrain.terrainData;
    var a=old.treeInstances;var b=data.treeInstances;var plan=JArray.Parse(File.ReadAllText(Evidence+"/replacements.json")).ToDictionary(p=>(int)p["index"]);
    if(a.Length!=b.Length||b.Length!=8525||data.treePrototypes.Length!=42)throw new Exception("Tree count mismatch");
    float ground=0;int kept=0;var actual=new List<object>();
    for(int i=0;i<a.Length;i++){
        if(a[i].position!=b[i].position||!a[i].color.Equals(b[i].color)||!a[i].lightmapColor.Equals(b[i].lightmapColor))throw new Exception("Pivot/color changed "+i);
        if(!plan.ContainsKey(i)){kept++;if(a[i].prototypeIndex!=b[i].prototypeIndex||a[i].heightScale!=b[i].heightScale||a[i].widthScale!=b[i].widthScale||a[i].rotation!=b[i].rotation)throw new Exception("Protected tree changed "+i);continue;}
        var p=plan[i];if(b[i].prototypeIndex!=(int)p["newPrototype"]||Mathf.Abs(b[i].heightScale-(float)p["heightScale"])>1e-6f||Mathf.Abs(b[i].widthScale-(float)p["widthScale"])>1e-6f||Mathf.Abs(b[i].rotation-(float)p["yaw"])>1e-6f)throw new Exception("Plan mismatch "+i);
        float ratio=b[i].widthScale/b[i].heightScale;if(ratio<.79999f||ratio>1.25001f)throw new Exception("Shape clamp failed");
        var pos=Vector3.Scale(b[i].position,data.size)+terrain.transform.position;ground=Mathf.Max(ground,Mathf.Abs(pos.y-terrain.SampleHeight(pos)-terrain.transform.position.y));
        actual.Add(new{index=i,prototype=b[i].prototypeIndex,widthScale=b[i].widthScale,heightScale=b[i].heightScale,rotation=b[i].rotation,position=XYZ(pos)});
    }
    for(int i=0;i<36;i++)if(old.treePrototypes[i].prefab!=data.treePrototypes[i].prefab)throw new Exception("Original prototype modified");
    foreach(var f in Families)for(int v=0;v<3;v++){
        var p=AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(f,v));
        if(p.GetComponent<LODGroup>().lodCount!=3||p.GetComponentsInChildren<CapsuleCollider>().Length!=2)throw new Exception("LOD/capsule invalid");
        foreach(var ren in p.GetComponentsInChildren<Renderer>(true)){
            if(ren.shadowCastingMode!=ShadowCastingMode.On||!ren.receiveShadows)throw new Exception("Shadows disabled");
            foreach(var m in ren.sharedMaterials)if(!m||!m.enableInstancing||m.shader.name!="OnlyVolunteers/Wind/v03/GenericFoliageScaled"||m.FindPass("ShadowCaster")<0||m.FindPass("DepthOnly")<0||ShaderUtil.ShaderHasError(m.shader))throw new Exception("Material invalid");
        }
    }
    var roots=UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
    int scripts=roots.SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).Sum(t=>GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
    int meshes=roots.SelectMany(r=>r.GetComponentsInChildren<MeshFilter>(true)).Count(m=>!m.sharedMesh);
    int materials=roots.SelectMany(r=>r.GetComponentsInChildren<Renderer>(true)).Sum(m=>m.sharedMaterials.Count(v=>!v));
    if(scripts+meshes+materials>0||ground>.01f)throw new Exception("Missing references or ground mismatch");
    var result=new{status="PASS",total=b.Length,replaced=plan.Count,retained=kept,maxGroundError=ground,missingScripts=scripts,missingMeshes=meshes,missingMaterials=materials,
        counts=plan.Values.GroupBy(p=>(string)p["family"]).ToDictionary(g=>g.Key,g=>g.Count()),windOwners=Object.FindObjectsByType<V19Wind>().Length,
        terrainPath=AssetDatabase.GetAssetPath(data),terrainGuid=AssetDatabase.AssetPathToGUID(Data),
        layers=data.terrainLayers.Select((v,i)=>new{slot=i,path=AssetDatabase.GetAssetPath(v),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(v)),missing=!v}).ToArray(),
        trees=data.treePrototypes.Select((v,i)=>new{slot=i,path=AssetDatabase.GetAssetPath(v.prefab),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(v.prefab)),missing=!v.prefab}).ToArray(),
        details=data.detailPrototypes.Select((v,i)=>new{slot=i,path=AssetDatabase.GetAssetPath(v.usePrototypeMesh?(Object)v.prototype:v.prototypeTexture),missing=v.usePrototypeMesh?!v.prototype:!v.prototypeTexture}).ToArray()};
    Write("integration_validation.json",result);Write("instances_readback.json",actual);return "PASS 2778 replaced, "+kept+" retained; max ground error "+ground;
}
public static string Benchmark(string label){
    if(!EditorApplication.isPlaying||EditorApplication.isPaused||Time.captureDeltaTime!=0)throw new Exception("Normal Play required");
    var motor=Object.FindAnyObjectByType<KinematicCharacterController.KinematicCharacterMotor>();if(motor.CharacterController==null)throw new Exception("KCC not initialized");
    string path=Path.GetFullPath(Evidence+"/performance_"+label+".json");Fresh(path);
    var ground=Object.FindAnyObjectByType<OnlyVolunteers.Map.Look.MapHeightSampler>();
    var points=G23MassBenchmarkI08.Poses.Select(p=>new Vector3(p.x,ground.Height(p.x,p.y)+1.65f,p.y)).ToArray();
    new GameObject("G23_TemporaryI09Benchmark").AddComponent<G23MassBenchmarkI08>().Begin(points,path);return "Started matched benchmark "+label;
}
public static string Capture(string label){
    if(!EditorApplication.isPlaying)throw new Exception("Play required");
    var clock=Object.FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();bool run=clock.Running;float hour=clock.Hour;
    try{clock.Running=false;clock.SetHour(8);var cameras=JArray.Parse(File.ReadAllText(Evidence+"/cameras.json"));
        foreach(var p in cameras)OnlyVolunteers.Map.Wind.Editor.WindReview24.Shot("../Trees/i09/"+label+"_"+(string)p["id"],(float)p["x"],(float)p["z"],(float)p["yaw"],(float)p["pitch"],12,true,(float)p["eye"],1600,900);
        return "Four matched Play shots "+label;
    }finally{clock.SetHour(hour);clock.Running=run;}
}
}}

