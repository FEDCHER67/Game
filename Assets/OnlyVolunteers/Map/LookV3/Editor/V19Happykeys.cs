using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19Happykeys
    {
        public const string Source="ArtSource/ThirdParty/happykeys_rocks_dead_trees/v01";
        public const string Root="Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees";
        public const string Assets=Root+"/v01";
        static float F(object v)=>Convert.ToSingle(v);
        static Vector3 V(object v)=>V19Infill.Vec(v);
        static Vector3 Axes(Vector3 v,bool negative)=>new(v.x,v.z,negative?-v.y:v.y);
        static List<object> L(Dictionary<string,object> d,string k)=>(List<object>)d[k];
        public static string Import()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            LookAssetStore.EnsureFolder(Assets+"/fbx");LookAssetStore.EnsureFolder(Assets+"/Prefabs");LookAssetStore.EnsureFolder(Assets+"/Materials");
            foreach(string file in Directory.GetFiles(Source+"/fbx"))
            {string dst=Assets+"/fbx/"+Path.GetFileName(file);if(!File.Exists(dst))File.Copy(file,dst);}
            foreach(string name in new[]{"README.md","manifest_v01.json","validation_v01.json"})if(!File.Exists(Assets+"/"+name))File.Copy(Source+"/"+name,Assets+"/"+name);
            if(!File.Exists(Root+"/README.md"))File.WriteAllText(Root+"/README.md","# happykeys rocks and bare trees\n\nAuthor: Trekkerac / happykeys. Models and palette: CC0-1.0. Source: https://happykeys.itch.io/rocks-and-dead-trees. Provenance and source hashes: v01/README.md. Imported for G18 v19 only, with Fedya’s approval on 2026-10-14. Original FBX files are unchanged; generated prefabs use the supplied analytic proxies. R01 is decorative and has no collider.\n");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var manifest=(Dictionary<string,object>)V3Json.Parse(File.ReadAllText(Source+"/manifest_v01.json"));
            var recolour=(Dictionary<string,object>)manifest["recolour"];
            Material Material(string name,string key)
            {
                string path=Assets+"/Materials/"+name+".mat";var old=AssetDatabase.LoadAssetAtPath<Material>(path);if(old)return old;
                var c=V(recolour[key]);var mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=name};mat.SetColor("_BaseColor",new Color(c.x,c.y,c.z));mat.SetFloat("_Smoothness",.1f);
                AssetDatabase.CreateAsset(mat,path);return mat;
            }
            var bark=Material("HK_RoughBark_v19","bark_preview_srgb");var rock=Material("HK_Rock_v07","rock_preview_srgb");var audit=new List<string>();
            foreach(Dictionary<string,object> model in L(manifest,"models"))
            {
                string id=(string)model["id"],path=Assets+"/"+model["fbx"],prefab=Assets+"/Prefabs/"+id+"_v19.prefab";
                if(File.Exists(prefab))continue;
                var mi=(ModelImporter)AssetImporter.GetAtPath(path);mi.globalScale=1;mi.useFileScale=true;mi.bakeAxisConversion=true;mi.importAnimation=false;mi.animationType=ModelImporterAnimationType.None;
                mi.importCameras=false;mi.importLights=false;mi.importBlendShapes=false;mi.importVisibility=false;mi.addCollider=false;mi.isReadable=true;mi.meshCompression=ModelImporterMeshCompression.Off;
                mi.importNormals=ModelImporterNormals.Import;mi.importTangents=ModelImporterTangents.None;mi.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;mi.materialLocation=ModelImporterMaterialLocation.InPrefab;mi.SaveAndReimport();
                var asset=AssetDatabase.LoadAssetAtPath<GameObject>(path);var parts=asset.GetComponentsInChildren<MeshFilter>().Select(f=>new CombineInstance{mesh=f.sharedMesh,transform=f.transform.localToWorldMatrix}).ToArray();
                var mesh=new Mesh{name=id+"_UnityMetres_v19"};mesh.CombineMeshes(parts,true,true);mesh.RecalculateBounds();var bounds=(Dictionary<string,object>)model["bounding_box_m"];
                Vector3 expected=Axes(V(bounds["size"]),false);float error=(mesh.bounds.size-expected).magnitude;if(error>.003f)throw new InvalidDataException(id+" dimension mismatch "+error);
                Vector3 centre=(V(bounds["min"])+V(bounds["max"]))/2;
                bool negative=(mesh.bounds.center-Axes(centre,true)).sqrMagnitude<(mesh.bounds.center-Axes(centre,false)).sqrMagnitude;
                AssetDatabase.CreateAsset(mesh,Assets+"/Prefabs/"+id+"_Mesh_v19.asset");
                var go=new GameObject(id+"_v19");go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterial=(string)model["type"]=="tree_bare"?bark:rock;
                foreach(Dictionary<string,object> p in L(model,"collider_proxies"))
                {
                    var child=new GameObject((string)p["id"]);child.transform.SetParent(go.transform,false);child.transform.localPosition=Axes(V(p["center_blender_m"]),negative);
                    if((string)p["shape"]=="capsule")
                    {child.transform.localRotation=Quaternion.FromToRotation(Vector3.up,Axes(V(p["axis_blender"]),negative));var c=child.AddComponent<CapsuleCollider>();c.direction=1;c.radius=F(p["radius_m"]);c.height=F(p["height_m"]);}
                    else child.AddComponent<BoxCollider>().size=Axes(V(p["size_blender_m"]),false);
                }
                int count=go.GetComponentsInChildren<Collider>().Length;if(id=="ROCK_01"&&count!=0)throw new InvalidDataException("R01 must be decorative");
                PrefabUtility.SaveAsPrefabAsset(go,prefab);audit.Add(id+" PASS size_error="+error.ToString("F7")+" colliders="+count+" imported_axes=(x,z,"+(negative?"-y":"y")+")");Object.DestroyImmediate(go);
            }
            if(audit.Count>0){string report=V19PilotTools.OutDir+"/happykeys_import_g18_v01.txt";if(File.Exists(report))throw new IOException("Import audit revision already exists");File.WriteAllLines(report,audit);}return string.Join("\n",audit);
        }
        static GameObject Prefab(string id)=>AssetDatabase.LoadAssetAtPath<GameObject>(Assets+"/Prefabs/"+id+"_v19.prefab");
        static bool Rough(Vector2 p,Vector4 b)
        {float x=Mathf.Max(b.x-p.x,Mathf.Max(0,p.x-b.z)),z=Mathf.Max(b.y-p.y,Mathf.Max(0,p.y-b.w));return x*x+z*z<=60*60;}
        public static string Apply(MapHeightSampler ground,DistrictWeather19V05 weather)
        {
            var terrain=ground.Terrain;var td=terrain.terrainData;var prototypes=td.treePrototypes.ToList();var rough=weather.districts.First(d=>d.id=="residential").bounds;
            int first=prototypes.Count;for(int i=1;i<=3;i++){var prefab=Prefab("TREE_BARE_0"+i);if(!prefab)throw new IOException("Import happykeys first");prototypes.Add(new TreePrototype{prefab=prefab});}
            td.treePrototypes=prototypes.ToArray();var trees=td.treeInstances;var counts=new int[3];var rows=new List<string>();
            var random=new System.Random(19190);var plan=MapLookBuilder.Load("v19");
            bool Clear(Vector3 p)
            {
                foreach(var road in plan.roads)if(LookGeom.DistToPolyline(road.pts,p.x,p.z,false,out _,out _)<road.w*.5f+2.1f)return false;
                foreach(var b in plan.buildings)if(LookGeom.Inside(b.fp,p.x,p.z)||LookGeom.DistToPolyline(b.fp,p.x,p.z,true,out _,out _)<2.1f)return false;
                return true;
            }
            for(int i=0;i<trees.Length;i++)
            {
                var p=Vector3.Scale(trees[i].position,td.size)+terrain.transform.position;string name=prototypes[trees[i].prototypeIndex].prefab.name.ToLowerInvariant();
                if(!Rough(new Vector2(p.x,p.z),rough)||name.Contains("pine")||name.Contains("spruce")||name.Contains("bush")||name.Contains("hedge"))continue;
                int variant=random.Next(3);float scale=.85f+(float)random.NextDouble()*.30f;
                if(!Clear(p))
                {
                    bool found=false;float offset=(float)random.NextDouble()*Mathf.PI*2;
                    for(int ring=1;ring<=15&&!found;ring++)for(int step=0;step<20;step++)
                    {float angle=offset+step*Mathf.PI*.1f;var q=p+new Vector3(Mathf.Cos(angle)*ring,0,Mathf.Sin(angle)*ring);if(!Rough(new Vector2(q.x,q.z),rough)||!Clear(q))continue;p=q;p.y=ground.Height(p.x,p.z);found=true;break;}
                    if(!found)throw new InvalidDataException("No clear nearby position for Rough tree "+i);
                    trees[i].position=new Vector3((p.x-terrain.transform.position.x)/td.size.x,(p.y-terrain.transform.position.y)/td.size.y,(p.z-terrain.transform.position.z)/td.size.z);
                }
                trees[i].prototypeIndex=first+variant;trees[i].widthScale=scale;trees[i].heightScale=scale;trees[i].rotation=(float)random.NextDouble()*Mathf.PI*2;
                trees[i].color=Color.white;trees[i].lightmapColor=Color.white;counts[variant]++;
                rows.Add(FormattableString.Invariant($"{i},{p.x:F3},{p.z:F3},{name},T0{variant+1},{scale:F4}"));
            }
            td.SetTreeInstances(trees,false);EditorUtility.SetDirty(td);AssetDatabase.SaveAssetIfDirty(td);
            var root=new GameObject("V19_Happykeys_RockClusters").transform;var data=(Dictionary<string,object>)V19Infill.Data()["happykeys"];
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root.gameObject,ground.gameObject.scene);
            int rockCount=0,colliders=0;Physics.SyncTransforms();
            foreach(Dictionary<string,object> p in L(data,"rocks"))
            {
                var go=(GameObject)PrefabUtility.InstantiatePrefab(Prefab((string)p["model"]));go.name=(string)p["id"];go.transform.SetParent(root,false);
                float x=F(p["x"]),z=F(p["z"]);go.transform.position=new Vector3(x,ground.Height(x,z)-.04f,z);go.transform.rotation=Quaternion.Euler(0,F(p["yaw"]),0);go.transform.localScale=Vector3.one*F(p["scale"]);
                rockCount++;colliders+=go.GetComponentsInChildren<Collider>().Length;
            }
            File.WriteAllLines(V19PilotTools.OutDir+"/happykeys_tree_replacements_round1_v04.csv",new[]{"terrain_index,x,z,old_prototype,new_model,scale"}.Concat(rows));
            return "happykeys Rough/fade tree replacements "+string.Join("/",counts)+" (T01/T02/T03), rocks="+rockCount+", rock boxes="+colliders+"; R01 non-solid";
        }
    }
}
