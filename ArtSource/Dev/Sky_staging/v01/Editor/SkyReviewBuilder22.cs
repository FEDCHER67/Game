using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22.Editor
{
    public static class SkyReviewBuilder22
    {
        public const string Root="Assets/OnlyVolunteers/Sky/G22_v01";
        public const string ScenePath="Assets/OnlyVolunteers/Scenes/Dev/Sky_Test.unity";
        const string LockPath=@"C:\Users\Zeyo-ne\AppData\Local\Temp\claude\C--Dev\ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f\scratchpad\unity.lock";
        static Material grass,bark,leaf,wall,roof,trim,stone,window;
        static int meshCount;
        public static void RequireLock()
        {
            if(!File.Exists(LockPath) || !File.ReadAllText(LockPath).StartsWith("gpt-g22 ",StringComparison.Ordinal))
                throw new InvalidOperationException("G22 must hold the shared Unity lock.");
            if(EditorApplication.isCompiling || EditorApplication.isUpdating)throw new InvalidOperationException("Editor is busy.");
        }
        [MenuItem("OnlyVolunteers/Sky G22/Build NEW Sky Test v01")]
        public static void Build()
        {
            RequireLock();if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("Stop Play before building.");
            if(File.Exists(ScenePath) || Directory.Exists(Root+"/Generated"))throw new IOException("Deliverable exists. Use a new numbered revision; never overwrite.");
            for(int i=0;i<SceneManager.sceneCount;i++)if(SceneManager.GetSceneAt(i).isDirty)throw new InvalidOperationException("An existing scene has unsaved work.");
            Scene prior=SceneManager.GetActiveScene();
            Scene scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            try
            {
                Directory.CreateDirectory(Root+"/Generated");Directory.CreateDirectory("Assets/OnlyVolunteers/Scenes/Dev");AssetDatabase.Refresh();
                grass=Mat("Meadow","#809968");bark=Mat("Bark","#675950");leaf=Mat("Leaf","#768D51");wall=Mat("Plaster","#DED0B1");
                roof=Mat("Roof","#796E6B");trim=Mat("Timber","#7C644C");stone=Mat("Stone","#959E93");window=Mat("Window","#FFDA8E");
                window.EnableKeyword("_EMISSION");window.SetColor("_EmissionColor",new Color(1,.56f,.18f)*2);AssetDatabase.SaveAssetIfDirty(window);
                TerrainMesh();
                var path=Primitive("Winding path",PrimitiveType.Cube,new Vector3(0,-.045f,18),new Vector3(3,.1f,56),stone);
                path.transform.rotation=Quaternion.Euler(0,-12,0);
                for(int i=0;i<8;i++) { var hill=Primitive("Distant hill "+i,PrimitiveType.Sphere,new Vector3(-130+i*38,-7,120+(i%3)*18),new Vector3(65,26+i%3*9,55),grass); }
                House(new Vector3(8,0,21));
                var rand=new System.Random(2201);
                for(int i=0;i<28;i++)
                {
                    float x=(float)rand.NextDouble()*130-65,z=(float)rand.NextDouble()*95+7;
                    if(Mathf.Abs(x)<13 && z<38)continue;
                    Tree(new Vector3(x,Height(x,z),z),4+(float)rand.NextDouble()*5,i%3==0);
                }
                for(int i=0;i<20;i++) {float x=(float)rand.NextDouble()*80-40,z=(float)rand.NextDouble()*80;
                    Primitive("Meadow rock "+i,PrimitiveType.Sphere,new Vector3(x,Height(x,z),z),new Vector3(1.1f,.55f,.7f),stone);}
                var rig=new GameObject("G22 • Original painted sky");var clock=rig.AddComponent<SkyClock22>();
                var sun=Light("Sun",rig.transform);var moon=Light("Moon",rig.transform);
                Shader shader=Shader.Find("OnlyVolunteers/Sky22/Painted Sky v01");if(!shader)throw new Exception("Sky shader missing.");
                var sky=new Material(shader){name="PaintedSky_v01"};AssetDatabase.CreateAsset(sky,Root+"/Generated/PaintedSky_v01.mat");
                var renderer=rig.AddComponent<SkyRenderer22>();renderer.Configure(clock,sky,sun,moon);
                var camera=new GameObject("Sky Review Camera").AddComponent<Camera>();camera.tag="MainCamera";
                camera.transform.position=new Vector3(-16,4,-20);camera.transform.rotation=Quaternion.Euler(-22,40,0);
                camera.fieldOfView=66;camera.nearClipPlane=.1f;camera.farClipPlane=1500;camera.clearFlags=CameraClearFlags.Skybox;camera.allowHDR=true;
                camera.gameObject.AddComponent<AudioListener>();camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
                var volume=new GameObject("Review grading").AddComponent<Volume>();volume.isGlobal=true;volume.priority=1;
                var profile=ScriptableObject.CreateInstance<VolumeProfile>();
                var tone=profile.Add<Tonemapping>(true);tone.mode.value=TonemappingMode.ACES;
                AssetDatabase.CreateAsset(profile,Root+"/Generated/ReviewGrade_v01.asset");
                foreach(var component in profile.components)AssetDatabase.AddObjectToAsset(component,profile);
                AssetDatabase.SaveAssetIfDirty(profile);volume.sharedProfile=profile;
                var night=GameObject.Find("G22 night windows");var nightDriver=rig.AddComponent<SkyNightObjects22>();nightDriver.Configure(clock,new[]{night});
                RenderSettings.skybox=sky;RenderSettings.sun=sun;RenderSettings.ambientMode=AmbientMode.Trilight;
                RenderSettings.ambientSkyColor=new Color(.55f,.65f,.72f);RenderSettings.ambientEquatorColor=new Color(.45f,.5f,.5f);RenderSettings.ambientGroundColor=new Color(.25f,.28f,.25f);
                RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;RenderSettings.fogStartDistance=95;RenderSettings.fogEndDistance=650;
                if(!EditorSceneManager.SaveScene(scene,ScenePath))throw new IOException("Scene save failed.");
                Debug.Log("G22 BUILD PASS: "+ScenePath);
            }
            finally {EditorSceneManager.CloseScene(scene,true);if(prior.IsValid())SceneManager.SetActiveScene(prior);}
        }
        static Material Mat(string name,string hex)
        {
            var m=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="G22_"+name};ColorUtility.TryParseHtmlString(hex,out var c);
            m.SetColor("_BaseColor",c);m.SetFloat("_Smoothness",.05f);AssetDatabase.CreateAsset(m,Root+"/Generated/"+name+"_v01.mat");return m;
        }
        static GameObject Primitive(string name,PrimitiveType type,Vector3 p,Vector3 scale,Material m)
        {
            var g=GameObject.CreatePrimitive(type);g.name=name;g.transform.position=p;g.transform.localScale=scale;g.GetComponent<Renderer>().sharedMaterial=m;return g;
        }
        static Light Light(string name,Transform parent) {var l=new GameObject(name).AddComponent<Light>();l.transform.SetParent(parent);l.type=LightType.Directional;l.shadows=LightShadows.Soft;l.intensity=name=="Sun"?1.1f:0;return l;}
        static float Height(float x,float z)=>Mathf.Sin(x*.038f)*Mathf.Sin(z*.034f)*1.5f;
        static void TerrainMesh()
        {
            const int n=65;var v=new Vector3[n*n];var uv=new Vector2[v.Length];var tris=new int[(n-1)*(n-1)*6];int ti=0;
            for(int z=0;z<n;z++)for(int x=0;x<n;x++) {float px=(x-32)*4,pz=(z-12)*4;int a=z*n+x;v[a]=new Vector3(px,Height(px,pz)-.15f,pz);uv[a]=new Vector2(x/64f,z/64f);
                if(x<n-1 && z<n-1){tris[ti++]=a;tris[ti++]=a+n;tris[ti++]=a+1;tris[ti++]=a+1;tris[ti++]=a+n;tris[ti++]=a+n+1;}}
            var mesh=new Mesh{name="Sky test terrain"};mesh.vertices=v;mesh.uv=uv;mesh.triangles=tris;mesh.RecalculateNormals();mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh,Root+"/Generated/Terrain_v01.asset");var g=new GameObject("Small rolling terrain",typeof(MeshFilter),typeof(MeshRenderer),typeof(MeshCollider));
            g.GetComponent<MeshFilter>().sharedMesh=mesh;g.GetComponent<MeshCollider>().sharedMesh=mesh;g.GetComponent<MeshRenderer>().sharedMaterial=grass;
        }
        static void Tree(Vector3 p,float height,bool broad)
        {
            Primitive("Tree trunk",PrimitiveType.Cylinder,p+Vector3.up*height*.35f,new Vector3(.35f,height*.35f,.35f),bark);
            if(broad)for(int j=0;j<3;j++)Primitive("Rounded canopy",PrimitiveType.Sphere,p+new Vector3((j-1)*height*.18f,height*.76f+(j==1?.6f:0),0),new Vector3(height*.58f,height*.53f,height*.55f),leaf);
            else for(int j=0;j<4;j++)Cone(p+Vector3.up*(height*.25f+j*height*.16f),height*(.33f-j*.05f),height*.40f,leaf);
        }
        static void Cone(Vector3 p,float radius,float height,Material material)
        {
            const int sides=9;var vertices=new Vector3[sides*3];var indices=new int[vertices.Length];
            for(int j=0;j<sides;j++){float a=j*Mathf.PI*2/sides,b=(j+1)*Mathf.PI*2/sides;vertices[j*3]=new Vector3(Mathf.Cos(a)*radius,0,Mathf.Sin(a)*radius);vertices[j*3+1]=Vector3.up*height;vertices[j*3+2]=new Vector3(Mathf.Cos(b)*radius,0,Mathf.Sin(b)*radius);indices[j*3]=j*3;indices[j*3+1]=j*3+1;indices[j*3+2]=j*3+2;}
            var mesh=new Mesh();mesh.vertices=vertices;mesh.triangles=indices;mesh.RecalculateNormals();AssetDatabase.CreateAsset(mesh,Root+"/Generated/Pine_"+(meshCount++)+"_v01.asset");
            var g=new GameObject("Pine crown",typeof(MeshFilter),typeof(MeshRenderer));g.transform.position=p;g.GetComponent<MeshFilter>().sharedMesh=mesh;g.GetComponent<MeshRenderer>().sharedMaterial=material;
        }
        static void House(Vector3 p)
        {
            p.y=Height(p.x,p.z);Primitive("Cottage walls",PrimitiveType.Cube,p+new Vector3(0,2,0),new Vector3(7,4,6),wall);
            for(int s=-1;s<=1;s+=2){var r=Primitive("Pitched roof",PrimitiveType.Cube,p+new Vector3(s*1.9f,4.6f,0),new Vector3(4.4f,.28f,7.2f),roof);r.transform.rotation=Quaternion.Euler(0,0,-s*24);}
            Primitive("Chimney",PrimitiveType.Cube,p+new Vector3(2,5.3f,1),new Vector3(.75f,2,.8f),stone);
            Primitive("Door",PrimitiveType.Cube,p+new Vector3(0,1.2f,-3.04f),new Vector3(1.25f,2.4f,.15f),trim);
            var windows=new GameObject("G22 night windows");
            for(int s=-1;s<=1;s+=2){Primitive("Window frame",PrimitiveType.Cube,p+new Vector3(s*2.2f,2.2f,-3.10f),new Vector3(1.5f,1.6f,.12f),trim);
                var pane=Primitive("Warm window",PrimitiveType.Cube,p+new Vector3(s*2.2f,2.2f,-3.19f),new Vector3(1.24f,1.33f,.08f),window);pane.transform.SetParent(windows.transform);
                Primitive("Window mullion",PrimitiveType.Cube,p+new Vector3(s*2.2f,2.2f,-3.25f),new Vector3(.08f,1.4f,.1f),trim);
                Primitive("Window crossbar",PrimitiveType.Cube,p+new Vector3(s*2.2f,2.2f,-3.25f),new Vector3(1.3f,.08f,.1f),trim);}
            Primitive("Lamp post",PrimitiveType.Cylinder,p+new Vector3(-6,1.8f,-5),new Vector3(.13f,1.8f,.13f),trim);
            var lamp=new GameObject("Night street lamp").AddComponent<Light>();lamp.transform.position=p+new Vector3(-6,3.4f,-5);lamp.type=LightType.Point;lamp.color=new Color(1,.65f,.29f);lamp.intensity=2.5f;lamp.range=13;lamp.transform.SetParent(windows.transform);
        }
    }
}
