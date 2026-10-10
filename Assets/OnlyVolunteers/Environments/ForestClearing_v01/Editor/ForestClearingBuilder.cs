using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.ForestStudy.Editor
{
    public static class ForestClearingBuilder
    {
        public const string Root = "Assets/OnlyVolunteers/Environments/ForestClearing_v01";
        public const string ScenePath = Root + "/ForestClearing_v01.unity";
        [Serializable] public class Entry { public string model,group; public float x,y,z,scale,yaw; }
        [Serializable] public class MatEntry { public string name,texture; public bool cutout; public float[] color; }
        [Serializable] public class Layout { public Entry[] instances; public MatEntry[] materials; public float[] spawn; }

        [MenuItem("Tools/Volunteers Only/Forest/Create ForestClearing v01")]
        public static void Build()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play Mode first.");
            if (File.Exists(ScenePath) && !SessionState.GetBool("VO_ForestDraftRebuild",false)) throw new InvalidOperationException("v01 already exists. Open it or author a new numbered revision.");
            var layout=JsonUtility.FromJson<Layout>(File.ReadAllText(Root+"/Layout.json"));
            Directory.CreateDirectory(Root+"/Materials");Directory.CreateDirectory(Root+"/Prefabs");
            var shader=Shader.Find("Universal Render Pipeline/Lit");
            if(shader==null) throw new InvalidOperationException("URP/Lit unavailable.");
            var materials=new Dictionary<string,Material>();
            foreach(var e in layout.materials)
            {
                var path=Root+"/Materials/"+e.name+".mat";
                var m=AssetDatabase.LoadAssetAtPath<Material>(path);
                if(m==null) {m=new Material(shader);AssetDatabase.CreateAsset(m,path);}
                m.SetFloat("_Smoothness",.05f);m.SetFloat("_Metallic",0);
                m.SetFloat("_SpecularHighlights",0);m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                m.SetColor("_BaseColor",new Color(e.color[0],e.color[1],e.color[2],e.color[3]));
                if(!string.IsNullOrEmpty(e.texture))
                {
                    var texPath=Root+"/Textures/"+e.texture;
                    var importer=AssetImporter.GetAtPath(texPath) as TextureImporter;
                    if(importer!=null) {importer.sRGBTexture=true;importer.alphaIsTransparency=e.cutout;importer.mipmapEnabled=true;importer.maxTextureSize=1024;importer.SaveAndReimport();}
                    m.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(texPath));
                }
                if(e.cutout)
                {
                    // Blender preview illumination differs from Unity's linear URP daylight.
                    m.SetColor("_BaseColor",new Color(.68f,.76f,.72f,1));
                    m.SetFloat("_AlphaClip",1);m.SetFloat("_Cutoff",.45f);m.SetFloat("_Cull",0);
                    m.EnableKeyword("_ALPHATEST_ON");m.SetOverrideTag("RenderType","TransparentCutout");m.renderQueue=2450;
                    m.SetTexture("_EmissionMap",m.GetTexture("_BaseMap"));m.SetColor("_EmissionColor",new Color(.02f,.02f,.02f));m.EnableKeyword("_EMISSION");
                }
                m.enableInstancing=true;EditorUtility.SetDirty(m);materials[e.name]=m;
            }
            var gm=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Materials/Forest_Ground.mat");
            if(gm==null) {gm=new Material(shader);AssetDatabase.CreateAsset(gm,Root+"/Materials/Forest_Ground.mat");}
            gm.name="Forest_Ground";gm.SetFloat("_Smoothness",0);
            gm.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"/Textures/Ground_Albedo.png"));
            materials[gm.name]=gm;
            var previous=SceneManager.GetActiveScene();
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
            try
            {
                SceneManager.SetActiveScene(scene);
                var root=new GameObject("Forest clearing · 70 m");
                var groups=new Dictionary<string,Transform>();
                var prefabs=new Dictionary<string,GameObject>();
                foreach(var model in layout.instances.Select(e=>e.model).Distinct().Concat(new[]{"Ground_70m"}))
                {
                    string modelPath=Root+"/Models/"+model+".fbx";
                    var importer=AssetImporter.GetAtPath(modelPath) as ModelImporter;
                    importer.importCameras=false;importer.importLights=false;importer.importAnimation=false;
                    importer.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;importer.SaveAndReimport();
                    var obj=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(modelPath),scene);
                    obj.name="Mesh";
                    var wrapper=new GameObject(model);obj.transform.SetParent(wrapper.transform,false);obj=wrapper;
                    foreach(var renderer in obj.GetComponentsInChildren<MeshRenderer>())
                    {
                        renderer.sharedMaterials=renderer.sharedMaterials.Select(m=>materials[m.name]).ToArray();
                        renderer.shadowCastingMode=ShadowCastingMode.TwoSided;renderer.receiveShadows=true;
                    }
                    if(model.StartsWith("tree_"))
                    {
                        var bounds=BoundsOf(obj);var collider=obj.AddComponent<CapsuleCollider>();collider.radius=.34f;
                        collider.height=Mathf.Min(bounds.size.y*.47f,3.5f);collider.center=new Vector3(0,collider.height*.5f,0);
                    }
                    else if(model=="Ground_70m" || model.StartsWith("stone_") || model=="log" || model=="stump_roundDetailed")
                    {
                        foreach(var mesh in obj.GetComponentsInChildren<MeshFilter>())mesh.gameObject.AddComponent<MeshCollider>().sharedMesh=mesh.sharedMesh;
                    }
                    foreach(var t in obj.GetComponentsInChildren<Transform>())GameObjectUtility.SetStaticEditorFlags(t.gameObject,StaticEditorFlags.BatchingStatic|StaticEditorFlags.OccluderStatic|StaticEditorFlags.OccludeeStatic);
                    prefabs[model]=PrefabUtility.SaveAsPrefabAsset(obj,Root+"/Prefabs/"+model+".prefab");
                    UnityEngine.Object.DestroyImmediate(obj);
                }
                var ground=(GameObject)PrefabUtility.InstantiatePrefab(prefabs["Ground_70m"],scene);ground.transform.SetParent(root.transform);
                foreach(var e in layout.instances)
                {
                    if(!groups.ContainsKey(e.group)) {var g=new GameObject(e.group);g.transform.SetParent(root.transform);groups[e.group]=g.transform;}
                    var obj=(GameObject)PrefabUtility.InstantiatePrefab(prefabs[e.model],scene);
                    obj.transform.SetParent(groups[e.group]);obj.transform.SetPositionAndRotation(new Vector3(e.x,e.y,e.z),Quaternion.Euler(0,e.yaw,0));obj.transform.localScale=Vector3.one*e.scale;
                }
                var sun=new GameObject("Soft afternoon sun").AddComponent<Light>();sun.type=LightType.Directional;
                sun.color=new Color(1,.95f,.85f);sun.intensity=1.35f;sun.shadows=LightShadows.Soft;sun.shadowStrength=.8f;sun.transform.rotation=Quaternion.Euler(48,-32,0);
                RenderSettings.sun=sun;RenderSettings.ambientMode=AmbientMode.Trilight;
                RenderSettings.ambientSkyColor=new Color(.55f,.64f,.72f);RenderSettings.ambientEquatorColor=new Color(.4f,.45f,.39f);RenderSettings.ambientGroundColor=new Color(.25f,.28f,.2f);
                var sh=new SphericalHarmonicsL2();sh.AddAmbientLight(new Color(.35f,.4f,.35f));RenderSettings.ambientProbe=sh;
                var sky=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Materials/Forest_Sky.mat");
                if(sky==null) {sky=new Material(Shader.Find("Skybox/Procedural"));AssetDatabase.CreateAsset(sky,Root+"/Materials/Forest_Sky.mat");}
                sky.SetFloat("_SunSize",.025f);sky.SetFloat("_AtmosphereThickness",.85f);
                sky.SetColor("_SkyTint",new Color(.52f,.6f,.65f));sky.SetColor("_GroundColor",new Color(.4f,.46f,.3f));sky.SetFloat("_Exposure",1.05f);
                RenderSettings.skybox=sky;
                RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;RenderSettings.fogStartDistance=42;RenderSettings.fogEndDistance=95;RenderSettings.fogColor=new Color(.66f,.76f,.74f);
                var player=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Player/Prefabs/Player_KCC_Baseline.prefab"),scene);
                player.name="Player · existing KCC movement";player.transform.position=new Vector3(layout.spawn[0],layout.spawn[1],layout.spawn[2]);
                var cam=player.GetComponentInChildren<Camera>();cam.farClipPlane=130;cam.fieldOfView=70;
                var cd=cam.GetComponent<UniversalAdditionalCameraData>() ?? cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
                cd.antialiasing=AntialiasingMode.SubpixelMorphologicalAntiAliasing;cd.antialiasingQuality=AntialiasingQuality.High;
                cd.renderShadows=true;
                var boundaries=new GameObject("Study boundary colliders");
                for(int i=0;i<4;i++)
                {
                    var wall=new GameObject("Boundary "+i);wall.transform.SetParent(boundaries.transform);var box=wall.AddComponent<BoxCollider>();
                    bool x=i<2;box.size=x?new Vector3(1,20,70):new Vector3(70,20,1);wall.transform.position=x?new Vector3(i==0?-34:34,8,0):new Vector3(0,8,i==2?-34:34);
                }
                var overview=new GameObject("Preview camera (disabled)").AddComponent<Camera>();overview.enabled=false;overview.fieldOfView=58;overview.farClipPlane=140;
                overview.transform.position=new Vector3(-4.2f,2.6f,-15.5f);overview.transform.LookAt(new Vector3(1,2.2f,9));
                var pd=overview.gameObject.AddComponent<UniversalAdditionalCameraData>();pd.antialiasing=AntialiasingMode.SubpixelMorphologicalAntiAliasing;pd.antialiasingQuality=AntialiasingQuality.High;
                AssetDatabase.SaveAssets();
                if(!EditorSceneManager.SaveScene(scene,ScenePath))throw new Exception("Forest scene save failed.");
                var report=new {scene=ScenePath,instances=layout.instances.Length,prefabs=prefabs.Count,materials=materials.Count,
                    missingScripts=scene.GetRootGameObjects().Sum(g=>g.GetComponentsInChildren<Transform>(true).Sum(t=>GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject))),
                    groundBounds=BoundsOf(ground).size.ToString(),playerScale=player.transform.lossyScale.ToString()};
                File.WriteAllText("ArtSource/Environments/ForestClearing_v01/unity_validation.json",JsonUtility.ToJson(new Report {instances=layout.instances.Length,prefabs=prefabs.Count,missingScripts=report.missingScripts,groundBounds=report.groundBounds},true));
                Debug.Log("FOREST_V01_READY "+ScenePath+" instances="+layout.instances.Length+" missingScripts="+report.missingScripts);
            }
            finally {SceneManager.SetActiveScene(previous);EditorSceneManager.CloseScene(scene,true);}
        }
        [Serializable] class Report {public int instances,prefabs,missingScripts;public string groundBounds;}
        [MenuItem("Tools/Volunteers Only/Forest/Render loaded forest previews")]
        public static void RenderPreviews()
        {
            var scene=SceneManager.GetActiveScene();
            if(scene.path!=ScenePath || SceneManager.sceneCount!=1 || EditorApplication.isPlaying)throw new InvalidOperationException("Load only ForestClearing_v01 in Edit Mode.");
            var camera=GameObject.Find("Preview camera (disabled)").GetComponent<Camera>();
            var pos=camera.transform.position;var rot=camera.transform.rotation;var fov=camera.fieldOfView;
            try {
                Capture(camera,scene,"Unity_Forest_View.png");
                camera.transform.position=new Vector3(31,38,-37);camera.transform.LookAt(Vector3.zero);camera.fieldOfView=53;
                Capture(camera,scene,"Unity_Forest_Overview.png");
            } finally {camera.transform.SetPositionAndRotation(pos,rot);camera.fieldOfView=fov;}
        }
        static Bounds BoundsOf(GameObject obj) {var r=obj.GetComponentsInChildren<Renderer>();var b=r[0].bounds;foreach(var item in r.Skip(1))b.Encapsulate(item.bounds);return b;}
        static void Capture(Camera camera,Scene scene,string name)
        {
            camera.overrideSceneCullingMask=EditorSceneManager.GetSceneCullingMask(scene);
            var rt=new RenderTexture(1440,900,24,RenderTextureFormat.ARGB32);rt.antiAliasing=2;rt.Create();
            var old=RenderTexture.active;camera.targetTexture=rt;
            try {camera.Render();RenderTexture.active=rt;var image=new Texture2D(1440,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1440,900),0,0);image.Apply();File.WriteAllBytes("ArtSource/Environments/ForestClearing_v01/Previews/"+name,image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally {camera.targetTexture=null;camera.overrideSceneCullingMask=0;RenderTexture.active=old;rt.Release();UnityEngine.Object.DestroyImmediate(rt);}
        }
    }
}
