using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace OnlyVolunteers.Vehicles.Paint.Editor
{
    public static class VanPaintMapInstaller
    {
        public const string BaseScene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i03_sky.unity";
        public const string MapScene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity";
        public const string Generated=VanPaintTestBuilder.Root+"/Generated_i04";
        public static string Install()
        {
            VanPaintTestBuilder.RequireLock();
            var scene=SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying || scene.path!=BaseScene || scene.isDirty || File.Exists(MapScene) || Directory.Exists(Generated))
                throw new InvalidOperationException("Requires clean i03 in Edit mode and new i04 destinations.");
            var van=UnityEngine.Object.FindAnyObjectByType<VanController>();
            var pawn=UnityEngine.Object.FindAnyObjectByType<GreyboxKccPawn>();
            var hut=GameObject.Find("B_02_B02");
            if(van==null || pawn==null || hut==null) throw new InvalidOperationException("Expected van, player and B02 hut.");
            // Save a new scene before changing anything. The i03 source file is never saved again.
            if(!EditorSceneManager.SaveScene(scene,MapScene)) throw new IOException("New i04 scene save failed.");
            Directory.CreateDirectory(Generated); AssetDatabase.Refresh();
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab");
            var original=prefab.GetComponentsInChildren<MeshFilter>(true);
            var renderers=new List<Renderer>(); var parts=new List<VanPaintMeshQuery.Part>();
            var materialCopies=new Dictionary<Material,Material>();
            var size=new Bounds(Vector3.zero,Vector3.zero); bool first=true;
            var filters=van.GetComponentsInChildren<MeshFilter>(true);
            foreach(var f in filters)
            {
                foreach(var p in f.sharedMesh.vertices)
                {
                    var local=van.transform.InverseTransformPoint(f.transform.TransformPoint(p));
                    if(first){size=new Bounds(local,Vector3.zero);first=false;}else size.Encapsulate(local);
                }
            }
            foreach(var f in filters)
            {
                var renderer=f.GetComponent<MeshRenderer>(); var materials=renderer.sharedMaterials;
                bool Paint(Material m)=>m!=null && m.name.StartsWith("VAN_Body",StringComparison.Ordinal);
                var flags=new List<bool>();
                for(int i=0;i<f.sharedMesh.subMeshCount;i++)
                    flags.AddRange(Enumerable.Repeat(i<materials.Length && Paint(materials[i]),f.sharedMesh.GetTriangles(i).Length/3));
                if(materials.Any(Paint))
                {
                    int index=Array.FindIndex(original,x=>x.name==f.name);
                    Mesh baked=AssetDatabase.LoadAssetAtPath<Mesh>(VanPaintTestBuilder.Root+"/Generated/Mesh_"+index+".asset");
                    if(baked==null) throw new InvalidOperationException("Missing test atlas for "+f.name);
                    var mesh=UnityEngine.Object.Instantiate(baked); mesh.name=f.name+"_Paint_i04";
                    Matrix4x4 matrix=f.transform.worldToLocalMatrix*van.transform.localToWorldMatrix;
                    mesh.vertices=Array.ConvertAll(mesh.vertices,matrix.MultiplyPoint3x4);
                    Matrix4x4 normalMatrix=matrix.inverse.transpose;
                    mesh.normals=Array.ConvertAll(mesh.normals,n=>normalMatrix.MultiplyVector(n).normalized);
                    mesh.RecalculateBounds(); AssetDatabase.CreateAsset(mesh,Generated+"/"+mesh.name+".asset"); f.sharedMesh=mesh;
                    for(int i=0;i<materials.Length;i++)
                    {
                        if(!Paint(materials[i]))continue;
                        if(!materialCopies.TryGetValue(materials[i],out var material))
                        {
                            material=new Material(AssetDatabase.LoadAssetAtPath<Shader>(VanPaintTestBuilder.Root+"/Shaders/VanPaintBody.shader"));
                            material.name=materials[i].name+"_Paint_i04"; material.SetColor("_BaseColor",materials[i].GetColor("_BaseColor"));
                            AssetDatabase.CreateAsset(material,Generated+"/"+material.name+".mat");materialCopies.Add(materials[i],material);
                        }
                        materials[i]=material;
                    }
                    renderer.sharedMaterials=materials; renderers.Add(renderer);
                }
                parts.Add(new VanPaintMeshQuery.Part {filter=f,paintable=flags.ToArray()});
            }
            var surface=van.gameObject.AddComponent<VanPaintSurface>();
            surface.Configure(AssetDatabase.LoadAssetAtPath<Shader>(VanPaintTestBuilder.Root+"/Shaders/VanPaintBrush.shader"),renderers.ToArray(),size.size,"hamlet-player-van-g20");
            var query=van.gameObject.AddComponent<VanPaintMeshQuery>();query.Configure(parts.ToArray());
            var station=new GameObject("G20 Grandpa's paint station — B02 hut");
            Vector3 location=new(183.4f,0,523.3f);
            if(!Physics.Raycast(location+Vector3.up*10,Vector3.down,out var ground,30))throw new InvalidOperationException("Station ground missing");
            station.transform.position=ground.point;
            var test=EditorSceneManager.OpenScene(VanPaintTestBuilder.ScenePath,OpenSceneMode.Additive);
            foreach(var go in test.GetRootGameObjects())
            {
                if(go.GetComponent<VanPaintProp>()==null && go.name!="Grandpa's paint table" && go.name!="Table leg")continue;
                var copy=UnityEngine.Object.Instantiate(go);copy.name=go.name;
                SceneManager.MoveGameObjectToScene(copy,scene);copy.transform.SetParent(station.transform,false);
                copy.transform.localPosition=go.transform.position-new Vector3(-2.9f,0,.6f);
                copy.transform.localRotation=go.transform.rotation;
            }
            var uiSource=test.GetRootGameObjects().First(g=>g.name=="G20 Painting HUD");
            var ui=UnityEngine.Object.Instantiate(uiSource);ui.name="G20 Map painting HUD";SceneManager.MoveGameObjectToScene(ui,scene);
            EditorSceneManager.CloseScene(test,true);SceneManager.SetActiveScene(scene);
            Transform Hand(string name,Vector3 pos)
            {var t=new GameObject(name).transform;t.SetParent(pawn.ViewCamera.transform,false);t.localPosition=pos;t.localScale=Vector3.one*.65f;return t;}
            var left=Hand("G20 Held can",new Vector3(-.38f,-.38f,.85f));
            var right=Hand("G20 Held brush",new Vector3(.37f,-.36f,.85f));
            var controls=new GameObject("G20 Map paint controls");
            var painter=controls.AddComponent<VanPaintInteractor>();var hud=ui.GetComponent<VanPaintHud>();
            painter.Configure(pawn.ViewCamera,surface,hud,left,right);painter.ConfigureFirstPerson(query);painter.enabled=false;hud.Configure(painter,surface);
            var mode=controls.AddComponent<VanPaintMapMode>();mode.Painter=painter;mode.Hud=hud;mode.Pawn=pawn;mode.Station=station.transform;
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
            return "Installed on real van: "+renderers.Count+" paint renderers; station at "+station.transform.position+" beside B_02_B02; "+MapScene;
        }
    }
}
