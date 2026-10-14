using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    // G18 additions consume the plan and original Blender collider contracts; no source kit is rewritten.
    public static class V19Infill
    {
        public const string Kit="Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01";
        public const string Source="ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01";
        public static Dictionary<string,object> Plan()=> (Dictionary<string,object>)V3Json.Parse(File.ReadAllText("ArtSource/References/Map/Look/look_v19_build_v07_flat.json"));
        public static Dictionary<string,object> Data()=> (Dictionary<string,object>)Plan()["v19"];
        public static List<object> List(Dictionary<string,object> d,string k)=>(List<object>)d[k];
        public static float F(object v)=>Convert.ToSingle(v);
        public static float N(Dictionary<string,object> d,string k)=>F(d[k]);
        public static Vector3 Vec(object v){var a=(List<object>)v;return new Vector3(F(a[0]),F(a[1]),F(a[2]));}
        static Vector3 Axes(Vector3 v)=>new(v.x,v.z,v.y);
        public static string Import()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            LookAssetStore.EnsureFolder(Kit);LookAssetStore.EnsureFolder(Kit+"/Prefabs");
            var doc=(Dictionary<string,object>)V3Json.Parse(File.ReadAllText(Source+"/validation_v01.json"));
            var assets=(Dictionary<string,object>)doc["assets"];int count=0;
            foreach(var pair in assets)
            {
                string target=Kit+"/"+pair.Key+"_v01.fbx";
                if(!File.Exists(target))File.Copy(Source+"/"+pair.Key+"_v01.fbx",target);
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            LookAssetStore.EnsureFolder(Kit+"/Decals");
            foreach(string id in new[]{"WORN_PATH_v01","WHEEL_TRACKS_DIRT_v01"})
            {
                string path=Kit+"/Decals/"+id+"_albedo.png";
                if(!File.Exists(path))File.Copy("ArtSource/Textures/StyleKit_v3/decals_v01/"+id+"_albedo.png",path);
                AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var ti=(TextureImporter)AssetImporter.GetAtPath(path);
                ti.alphaIsTransparency=true;ti.mipmapEnabled=true;ti.wrapMode=TextureWrapMode.Repeat;ti.SaveAndReimport();
                string mp=Kit+"/Decals/"+id+".mat";if(File.Exists(mp))continue;
                var mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=id+"_v19"};mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(path));
                mat.SetFloat("_AlphaClip",1);mat.SetFloat("_Cutoff",.12f);mat.EnableKeyword("_ALPHATEST_ON");mat.SetFloat("_Smoothness",.04f);mat.renderQueue=2450;AssetDatabase.CreateAsset(mat,mp);
            }
            var roles=((List<object>)doc["material_roles"]).Select(v=>(string)v).ToArray();
            var mats=roles.Select(r=>AssetDatabase.LoadAssetAtPath<Material>(V19PaletteP2.Kit+"/Materials/P19_"+r+".mat")).ToArray();
            if(mats.Any(m=>!m))throw new IOException("Missing approved kit palette");
            var audit=new List<string>();
            foreach(var pair in assets)
            {
                string prefab=Kit+"/Prefabs/"+pair.Key+"_v01.prefab";if(File.Exists(prefab))continue;
                string target=Kit+"/"+pair.Key+"_v01.fbx";var mi=(ModelImporter)AssetImporter.GetAtPath(target);
                mi.globalScale=1;mi.useFileScale=true;mi.bakeAxisConversion=true;mi.importAnimation=false;mi.animationType=ModelImporterAnimationType.None;
                mi.importCameras=false;mi.importLights=false;mi.importBlendShapes=false;mi.importVisibility=false;mi.addCollider=false;mi.isReadable=true;
                mi.meshCompression=ModelImporterMeshCompression.Off;mi.importNormals=ModelImporterNormals.Import;mi.importTangents=ModelImporterTangents.None;
                mi.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;mi.materialLocation=ModelImporterMaterialLocation.InPrefab;mi.SaveAndReimport();
                var root=new GameObject(pair.Key+"_v01");var model=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(target));
                model.transform.SetParent(root.transform,false);foreach(var r in model.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=mats;
                var a=(Dictionary<string,object>)pair.Value;var proxies=List(a,"colliders");
                Matrix4x4 basis=Matrix4x4.identity;basis.SetColumn(1,new Vector4(0,0,1,0));basis.SetColumn(2,new Vector4(0,1,0,0));
                if(pair.Key.Contains("WOODPILE") || pair.Key.Contains("TYRE"))
                {
                    // Log/tyre unions have many tiny facets. One fitted block is intentional for these solid piles.
                    Vector3 min=Axes(Vec(a["bounds_min"])),max=Axes(Vec(a["bounds_max"]));
                    var col=root.AddComponent<BoxCollider>();col.center=(min+max)*.5f;col.size=max-min;
                }
                else foreach(Dictionary<string,object> c in proxies)
                {
                    var go=new GameObject((string)c["id"]+"_"+c["name"]);go.transform.SetParent(root.transform,false);go.transform.localPosition=Axes(Vec(c["center_m"]));
                    var q=List(c,"rotation_quaternion_xyzw");var rot=basis*Matrix4x4.Rotate(new Quaternion(F(q[0]),F(q[1]),F(q[2]),F(q[3])))*basis.inverse;
                    go.transform.localRotation=Quaternion.LookRotation(rot.GetColumn(2),rot.GetColumn(1));go.AddComponent<BoxCollider>().size=Axes(Vec(c["size_m"]));
                }
                var rs=root.GetComponentsInChildren<MeshRenderer>();Bounds bb=rs[0].bounds;foreach(var r in rs.Skip(1))bb.Encapsulate(r.bounds);
                float error=(bb.size-Axes(Vec(a["size_m"]))).magnitude;
                if(error>.003f)throw new InvalidDataException(pair.Key+" import dimensions differ: "+error);
                PrefabUtility.SaveAsPrefabAsset(root,prefab);audit.Add(pair.Key+" PASS size_error="+error+" boxes="+root.GetComponentsInChildren<Collider>().Length);
                Object.DestroyImmediate(root);count++;
            }
            if(audit.Count>0){string report=V19PilotTools.OutDir+"/kit_v01_unity_import_g18_v01.txt";if(File.Exists(report))throw new IOException("Import audit revision already exists");File.WriteAllLines(report,audit);}return count+" modules imported; decals ready";
        }
        public static void Build(MapHeightSampler ground,Transform parent,V3Store store,List<string> log)
        {
            var data=Data();var root=new GameObject("V19_PurposefulPlaces").transform;root.SetParent(parent,false);
            foreach(Dictionary<string,object> p in List(data,"kit"))
            {
                string path=Kit+"/Prefabs/"+(string)p["module"]+"_v01.prefab";var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(!prefab)throw new IOException("Import required: "+path);
                var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name=(string)p["id"]+"_"+p["module"];go.transform.SetParent(root,false);
                float x=N(p,"x"),z=N(p,"z");go.transform.position=new Vector3(x,ground.Height(x,z),z);go.transform.rotation=Quaternion.Euler(0,N(p,"yaw"),0);
            }
            var registry=LookAssetStore.Registry();
            foreach(Dictionary<string,object> p in List(data,"natural"))
            {
                string kind=(string)p["kind"];Vector3 size=Vec(p["size"]);float x=N(p,"x"),z=N(p,"z");GameObject go;
                if(kind=="rock")
                {
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(V19Happykeys.Assets+"/Prefabs/ROCK_11_v19.prefab");if(!prefab)throw new IOException("Approved happykeys rock prefab missing");
                    go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.transform.SetParent(root,false);
                    var rs=go.GetComponentsInChildren<Renderer>();Bounds b=rs[0].bounds;foreach(var r in rs.Skip(1))b.Encapsulate(r.bounds);
                    go.transform.localScale=Vector3.Scale(go.transform.localScale,new Vector3(size.x/b.size.x,size.y/b.size.y,size.z/b.size.z));
                    // Preserve the approved manifest box proxy under the identical visible-model transform.
                }
                else
                {
                    go=GameObject.CreatePrimitive(PrimitiveType.Cylinder);go.transform.SetParent(root,false);go.transform.localScale=new Vector3(size.x,size.z*.5f,size.y);
                    go.GetComponent<MeshRenderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>(V19PaletteP2.Output+"/Materials/V19_WornWood.mat");
                    Object.DestroyImmediate(go.GetComponent<Collider>());go.AddComponent<MeshCollider>().sharedMesh=go.GetComponent<MeshFilter>().sharedMesh;
                }
                go.name=(string)p["id"];go.transform.position=new Vector3(x,ground.Height(x,z)+size.y*.4f,z);
                go.transform.rotation=Quaternion.Euler(kind=="log"?90:0,N(p,"yaw"),0);
                var renderers=go.GetComponentsInChildren<Renderer>();float bottom=renderers.Min(r=>r.bounds.min.y);
                go.transform.position+=Vector3.up*(ground.Height(x,z)-bottom-.08f);
            }
            log.Add("v19 infill: "+List(data,"kit").Count+" kit anchors, "+List(data,"natural").Count+" source-fitted solid rocks/logs");
            foreach(Dictionary<string,object> p in List(data,"decals"))
            {
                var points=List(p,"pts").Cast<List<object>>().Select(q=>new Vector2(F(q[0]),F(q[1]))).ToArray();float width=N(p,"width_m"),length=0;
                var verts=new List<Vector3>();var uv=new List<Vector2>();var triangles=new List<int>();
                for(int i=1;i<points.Length;i++)
                {
                    var a=points[i-1];var b=points[i];float len=Vector2.Distance(a,b);if(len<.01f)continue;var side=new Vector2(-(b-a).y,(b-a).x).normalized*width*.5f;
                    int steps=Mathf.CeilToInt(len/1.5f);
                    for(int j=0;j<steps;j++)
                    {
                        var start=Vector2.Lerp(a,b,j/(float)steps);var end=Vector2.Lerp(a,b,(j+1f)/steps);int v=verts.Count;
                        foreach(var q in new[]{start-side,start+side,end-side,end+side})verts.Add(new Vector3(q.x,ground.Height(q.x,q.y)+.035f,q.y));
                        float u0=(length+len*j/steps)/6,u1=(length+len*(j+1)/steps)/6;uv.AddRange(new[]{new Vector2(0,u0),new Vector2(1,u0),new Vector2(0,u1),new Vector2(1,u1)});
                        triangles.AddRange(new[]{v,v+2,v+1,v+1,v+2,v+3});
                    }
                    length+=len;
                }
                var mesh=new Mesh{name="V19_Track_"+p["id"]};mesh.SetVertices(verts);mesh.SetUVs(0,uv);mesh.SetTriangles(triangles,0);mesh.RecalculateNormals();mesh.RecalculateBounds();
                var go=new GameObject(mesh.name);go.transform.SetParent(root,false);go.AddComponent<MeshFilter>().sharedMesh=store.AddMesh(mesh);
                go.AddComponent<MeshRenderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>(Kit+"/Decals/"+p["texture"]+".mat");
            }
        }
    }
}
