using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using OnlyVolunteers.Map.Wind;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Trees.Editor
{
    // Explicit approved-revision integration; never runs automatically or rebuilds the map.
    public static class G23LeafyIntegration
    {
        public const string Root="Assets/OnlyVolunteers/Art/Trees/Leafy_v04";
        public const string Base="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i06_wind_trees.unity";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i07_leafy_v04.unity";
        public const string BeforeData="Assets/OnlyVolunteers/Map/Wind/Trees_v01/Terrain_v19_i06_wind.asset";
        public const string Data=Root+"/SceneData/Terrain_v19_i07_leafy.asset";
        public const string Evidence="Working/Reviews/Trees/i07";
        const string Staging="ArtSource/Dev/Trees_staging/v04";
        public static readonly string[] Families={"Apple","Poplar","Palm","Bush"};
        public static string Revision(string family)=>family=="Poplar"?"v04_04":"v04_03";
        public static string Prefab(string family,int variant)=>Root+"/Prefabs/"+family+"_"+(char)('A'+variant)+"_"+Revision(family)+".prefab";
        static void Fresh(string path){if(File.Exists(path))throw new IOException("Preserve earlier deliverable: "+path);}
        static void Folder(string path){if(AssetDatabase.IsValidFolder(path))return;var parent=Path.GetDirectoryName(path).Replace('\\','/');Folder(parent);AssetDatabase.CreateFolder(parent,Path.GetFileName(path));}
        static float[] XYZ(Vector3 p)=>new[]{p.x,p.y,p.z};
        public static string Kind(int prototype)=>prototype==3||prototype==4||prototype==9?"Poplar":prototype==7||prototype==8?"Apple":prototype==10||prototype==11?"Palm":prototype==14?"Bush":null;
        static void Write(string file,object value)=>File.WriteAllText(Evidence+"/"+file,Newtonsoft.Json.JsonConvert.SerializeObject(value,Newtonsoft.Json.Formatting.Indented));

        public static string BuildAssets()
        {
            if(EditorApplication.isPlaying)throw new Exception("Edit mode required");
            foreach(var folder in new[]{"Meshes","Prefabs","SceneData"})Folder(Root+"/"+folder);
            var specs=(JArray)JObject.Parse(File.ReadAllText(Staging+"/validation_v04_03.json"))["variants"];
            var remaps=JObject.Parse(File.ReadAllText(Staging+"/wind_bindings_v04_03.json"))["material_remaps"];
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
                        float response=family=="Apple"?.13f:family=="Poplar"?.075f:family=="Palm"?.18f:.22f;
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
                        if(renderer.sharedMaterials.Any(m=>!m||!m.enableInstancing||m.shader.name!="OnlyVolunteers/Wind/v02/GenericFoliage"||ShaderUtil.ShaderHasError(m.shader)))throw new Exception("Shared wind binding invalid");
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
                    if(family!="Bush")foreach(var cap in spec["collider"])
                    {
                        var holder=new GameObject("TrunkCapsule");holder.transform.SetParent(root.transform,false);
                        var center=cap["center_Unity"].Select(v=>(float)v).ToArray();var axis=cap["axis_Unity"].Select(v=>(float)v).ToArray();
                        // Imported FBX handedness maps Blender Y to Unity +Z;
                        // staged capsule recipes used -Z, so convert that axis here.
                        holder.transform.localPosition=new Vector3(center[0],center[1],-center[2]);
                        holder.transform.localRotation=Quaternion.FromToRotation(Vector3.up,new Vector3(axis[0],axis[1],-axis[2]));
                        var collider=holder.AddComponent<CapsuleCollider>();collider.direction=1;collider.radius=(float)cap["radius_m"];collider.height=(float)cap["height_m"];
                    }
                    PrefabUtility.SaveAsPrefabAsset(root,Prefab(family,variant));
                }
                finally{Object.DestroyImmediate(root);}
                importer.isReadable=false;importer.SaveAndReimport();
            }
            Write("asset_validation.json",records);return "Built 12 approved prefabs and 36 LODs; shared wind materials; 18 trunk capsules; bushes have no collider.";
        }

        public static string AuditTerrain(string label)
        {
            var rows=Object.FindObjectsByType<Terrain>().Select(t=>
            {
                var d=t.terrainData;string path=AssetDatabase.GetAssetPath(d);
                return new{terrain=t.name,path,guid=AssetDatabase.AssetPathToGUID(path),
                    layers=d.terrainLayers.Select((v,i)=>new{slot=i,path=AssetDatabase.GetAssetPath(v),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(v)),missing=!v}).ToArray(),
                    trees=d.treePrototypes.Select((p,i)=>new{slot=i,path=AssetDatabase.GetAssetPath(p.prefab),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(p.prefab)),missing=!p.prefab,count=d.treeInstances.Count(v=>v.prototypeIndex==i)}).ToArray(),
                    details=d.detailPrototypes.Select((p,i)=>new{slot=i,useMesh=p.usePrototypeMesh,path=AssetDatabase.GetAssetPath(p.usePrototypeMesh?(Object)p.prototype:p.prototypeTexture),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(p.usePrototypeMesh?(Object)p.prototype:p.prototypeTexture)),missing=p.usePrototypeMesh?!p.prototype:!p.prototypeTexture,textureOptional=p.usePrototypeMesh}).ToArray()};
            }).ToArray();
            Write("terrain_audit_"+label+".json",rows);return "Recorded TerrainData and every layer/tree/detail path/GUID without repairing anything.";
        }

        public static string Integrate()
        {
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying||scene.path!=Base||scene.isDirty)throw new Exception("Requires clean i06 Edit scene");
            Fresh(Scene);Fresh(Data);
            var terrain=Terrain.activeTerrain;var old=terrain.terrainData;
            if(AssetDatabase.GetAssetPath(old)!=BeforeData)throw new Exception("Unexpected base TerrainData");
            if(Object.FindObjectsByType<V19Wind>().Length!=1)throw new Exception("Expected one shared wind");
            if(!EditorSceneManager.SaveScene(scene,Scene))throw new Exception("SaveAs failed");
            if(!AssetDatabase.CopyAsset(BeforeData,Data))throw new Exception("TerrainData copy failed");
            var data=AssetDatabase.LoadAssetAtPath<TerrainData>(Data);var protos=data.treePrototypes.ToList();int first=protos.Count;
            foreach(var family in Families)for(int variant=0;variant<3;variant++)protos.Add(new TreePrototype{prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family,variant)),bendFactor=0});
            if(protos.Any(p=>!p.prefab))throw new Exception("Unresolved prototype");data.treePrototypes=protos.ToArray();
            var instances=old.treeInstances;var rng=new System.Random(230407);var replacements=new List<object>();
            for(int i=0;i<instances.Length;i++)
            {
                var tree=instances[i];string family=Kind(tree.prototypeIndex);if(family==null)continue;
                int variant=rng.Next(3);float scale=.9f+.2f*(float)rng.NextDouble();float yaw=(float)rng.NextDouble()*Mathf.PI*2;
                replacements.Add(new{index=i,family,variant=((char)('A'+variant)).ToString(),oldPrototype=tree.prototypeIndex,newPrototype=first+Array.IndexOf(Families,family)*3+variant,position=XYZ(Vector3.Scale(tree.position,data.size)+terrain.transform.position),scale,yaw});
                tree.prototypeIndex=first+Array.IndexOf(Families,family)*3+variant;tree.rotation=yaw;tree.widthScale=tree.heightScale=scale;instances[i]=tree;
            }
            data.SetTreeInstances(instances,false);EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
            terrain.terrainData=data;terrain.GetComponent<TerrainCollider>().terrainData=data;terrain.Flush();
            var originals=Object.FindObjectsByType<LODGroup>(FindObjectsInactive.Include).Where(g=>g.name=="V19_GardenAppleTree").ToArray();
            var ordinary=new List<object>();
            foreach(var previous in originals)
            {
                int variant=rng.Next(3);float scale=.9f+.2f*(float)rng.NextDouble();float yaw=(float)rng.NextDouble()*360;
                var obj=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Prefab("Apple",variant)),previous.transform.parent);
                obj.name="V19_GardenAppleTree_v04";obj.transform.position=previous.transform.position;
                obj.transform.rotation=Quaternion.Euler(0,yaw,0);obj.transform.localScale=Vector3.one*scale;
                ordinary.Add(new{name=obj.name,variant=((char)('A'+variant)).ToString(),position=XYZ(obj.transform.position),scale,yaw});
                Object.DestroyImmediate(previous.gameObject);
            }
            Write("replacements.json",new{seed=230407,scaleRule="Native approved metre sizes, uniform 0.9–1.1; every original world pivot retained",terrain=replacements,ordinary});
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AuditTerrain("i07");
            return "Saved i07: "+replacements.Count+" terrain instances and "+ordinary.Count+" garden apple replaced. All other tree records/prefabs preserved.";
        }

        public static string Validate()
        {
            var old=AssetDatabase.LoadAssetAtPath<TerrainData>(BeforeData);var terrain=Terrain.activeTerrain;var data=terrain.terrainData;
            var a=old.treeInstances;var b=data.treeInstances;if(a.Length!=b.Length)throw new Exception("Tree count changed");
            int retained=0,replaced=0;float maxGroundError=0;var counts=new Dictionary<string,int>();
            for(int i=0;i<a.Length;i++)
            {
                if(a[i].position!=b[i].position||!a[i].color.Equals(b[i].color)||!a[i].lightmapColor.Equals(b[i].lightmapColor))throw new Exception("Original position/colour changed: "+i);
                var family=Kind(a[i].prototypeIndex);
                if(family==null)
                {
                    retained++;if(a[i].prototypeIndex!=b[i].prototypeIndex||a[i].widthScale!=b[i].widthScale||a[i].heightScale!=b[i].heightScale||a[i].rotation!=b[i].rotation)throw new Exception("Retained instance changed: "+i);
                }
                else
                {
                    replaced++;if(!counts.ContainsKey(family))counts[family]=0;counts[family]++;
                    string path=AssetDatabase.GetAssetPath(data.treePrototypes[b[i].prototypeIndex].prefab);
                    if(!path.StartsWith(Root+"/Prefabs/"+family+"_")||!path.EndsWith(Revision(family)+".prefab"))throw new Exception("Wrong approved revision: "+path);
                    if(b[i].widthScale!=b[i].heightScale||b[i].widthScale<.9f||b[i].widthScale>1.1f||b[i].rotation<0||b[i].rotation>=Mathf.PI*2)throw new Exception("Invalid seeded variation");
                    var point=Vector3.Scale(b[i].position,data.size)+terrain.transform.position;
                    maxGroundError=Mathf.Max(maxGroundError,Mathf.Abs(point.y-(terrain.SampleHeight(point)+terrain.transform.position.y)));
                }
            }
            for(int i=0;i<old.treePrototypes.Length;i++)if(data.treePrototypes[i].prefab!=old.treePrototypes[i].prefab)throw new Exception("Old prototype changed");
            if(maxGroundError>.01f)throw new Exception("Ground contact mismatch");
            int missing=0,badMaterials=0;foreach(var root in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())foreach(var tr in root.GetComponentsInChildren<Transform>(true))missing+=GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(tr.gameObject);
            foreach(var family in Families)for(int variant=0;variant<3;variant++)
            {
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family,variant));var group=prefab.GetComponent<LODGroup>();
                if(!group||group.lodCount!=3)throw new Exception("LODGroup invalid");
                if(prefab.GetComponentsInChildren<CapsuleCollider>().Length!=(family=="Bush"?0:2))throw new Exception("Collider count invalid");
                foreach(var r in prefab.GetComponentsInChildren<Renderer>(true))
                {
                    if(r.shadowCastingMode!=ShadowCastingMode.On||!r.receiveShadows)throw new Exception("Shadow flags invalid");
                    foreach(var m in r.sharedMaterials)if(!m||m.shader.name!="OnlyVolunteers/Wind/v02/GenericFoliage"||!m.enableInstancing||m.FindPass("ShadowCaster")<0||m.FindPass("DepthOnly")<0)badMaterials++;
                }
            }
            if(missing!=0||badMaterials!=0)throw new Exception("Missing scripts/materials");
            var result=new{status="PASS",total=b.Length,replaced,retained,counts,maxGroundError,missingScripts=missing,badMaterials,windOwners=Object.FindObjectsByType<V19Wind>().Length,shaderErrors=ShaderUtil.ShaderHasError(Shader.Find("OnlyVolunteers/Wind/v02/GenericFoliage"))};
            Write("integration_validation.json",result);return Newtonsoft.Json.JsonConvert.SerializeObject(result);
        }
    }
}
