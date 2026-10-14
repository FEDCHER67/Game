using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Wind.Editor
{
    public static class WindIntegration24
    {
        public const string Root="Assets/OnlyVolunteers/Map/Wind/v01";
        public const string Base="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i05_wind_grass.unity";
        public static string Install()
        {
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying||scene.path!=Base||scene.isDirty||File.Exists(Scene))throw new Exception("Expected clean i04 and unused i05 path");
            if(Object.FindAnyObjectByType<V19Wind>())throw new Exception("Shared wind already exists");
            var grass=Object.FindAnyObjectByType<ChunkedGrassRenderer24>();if(!grass)throw new Exception("Grass missing");
            string materialRoot=Root+"/Materials";if(Directory.Exists(materialRoot))throw new Exception("Materials already exist");
            Directory.CreateDirectory(materialRoot);AssetDatabase.Refresh();
            var indirect=Shader.Find("OnlyVolunteers/Wind/v01/IndirectGrass");var generic=Shader.Find("OnlyVolunteers/Wind/v01/GenericFoliage");
            if(!indirect||!generic||ShaderUtil.ShaderHasError(indirect)||ShaderUtil.ShaderHasError(generic))throw new Exception("Wind shaders not ready");
            var material=new Material(grass.material){name="TallGrass_SharedWind_v01",shader=indirect,enableInstancing=true};
            material.SetFloat("_WindResponse",1);material.SetFloat("_FlexibleHeight",.4f);material.SetFloat("_TipFlash",.12f);
            AssetDatabase.CreateAsset(material,materialRoot+"/TallGrass_SharedWind_v01.mat");
            foreach(var preset in new[]{("Grass",1f,.4f),("Foliage",.10f,1f),("Bush",.22f,.5f)})
            {
                var mat=new Material(generic){name="Generic"+preset.Item1+"Wind_v01",enableInstancing=true};
                mat.SetFloat("_WindResponse",preset.Item2);mat.SetFloat("_FlexibleHeight",preset.Item3);
                AssetDatabase.CreateAsset(mat,materialRoot+"/"+mat.name+".mat");
            }
            grass.Release();grass.material=material;EditorUtility.SetDirty(grass);
            var wind=new GameObject("V19Wind").AddComponent<V19Wind>();wind.districts=Object.FindAnyObjectByType<DistrictWeather19V05>();
            var terrain=Object.FindAnyObjectByType<MapHeightSampler>().Terrain;var pos=terrain.transform.position;var size=terrain.terrainData.size;
            wind.fieldRectangle=new Vector4(pos.x,pos.z,size.x,size.z);wind.RebuildDistrictField();wind.ApplyPreset(V19Wind.Preset.Breezy);
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene,Scene);AssetDatabase.SaveAssets();
            return "Saved "+Scene+"; unchanged data="+AssetDatabase.GetAssetPath(grass.data)+"; instances="+grass.TotalInstances+"; one shared wind; generic materials ready";
        }
        public static string GpuProbe()
        {
            var compute=Object.Instantiate(AssetDatabase.LoadAssetAtPath<ComputeShader>(Root+"/Editor/WindProbe_v01.compute"));
            var source=new Vector4[]{new(0,0,0,1),new(0,1,0,1),new(0,8,0,.1f),new(2,7,0,.1f),new(.2f,0,0,1),new(0,1,0,1)};
            var input=source.SelectMany((p,i)=>new[]{p,new Vector4(0,1,0,i==5?0:1)}).ToArray();
            GraphicsBuffer src=null,dst=null;
            try
            {
                src=new GraphicsBuffer(GraphicsBuffer.Target.Structured,source.Length,32);src.SetData(input);
                dst=new GraphicsBuffer(GraphicsBuffer.Target.Structured,source.Length,16);
                int k=compute.FindKernel("Probe");compute.SetBuffer(k,"_Input",src);compute.SetBuffer(k,"_Output",dst);compute.SetInt("_Count",source.Length);
                compute.SetVector("_V19WindParameters",new Vector4(8*Mathf.Deg2Rad,32*Mathf.Deg2Rad,40,8));compute.SetVector("_V19WindDetail",new Vector4(0,45*Mathf.Deg2Rad,0,0));compute.SetTexture(k,"_V19WindField",Texture2D.whiteTexture);
                compute.SetVector("_V19WindDirectionTime",new Vector4(1,0,1.25f,1));compute.Dispatch(k,1,1,1);var rest=new Vector4[source.Length];dst.GetData(rest);
                compute.SetVector("_V19WindDirectionTime",new Vector4(1,0,3.75f,1));compute.Dispatch(k,1,1,1);var gust=new Vector4[source.Length];dst.GetData(gust);
                float restAngle=Vector3.Angle(Vector3.up,(Vector3)rest[1]),gustAngle=Vector3.Angle(Vector3.up,(Vector3)gust[1]);
                bool pass=((Vector3)gust[0]).sqrMagnitude<1e-8&&Vector3.Distance(gust[4],source[4])<.0001f&&Vector3.Distance(gust[5],source[5])<.0001f&&Mathf.Abs(restAngle-8)<.02f&&Mathf.Abs(gustAngle-40)<.02f&&Mathf.Abs(gust[2].x-.55805f)<.002f;
                string report=(pass?"PASS":"FAIL")+$" actual GPU shared HLSL: grass rest={restAngle:F3}deg; gust={gustAngle:F3}deg; 8m tree tip={gust[2].x:F3}m; pinned pivot, ground vertices and optional zero mask; no UVs/model bake required.\n"+string.Join("\n",gust.Select((p,i)=>i+": "+p));
                Directory.CreateDirectory("Working/Reviews/Wind");File.WriteAllText("Working/Reviews/Wind/generic_gpu_probe_v01.txt",report);if(!pass)throw new Exception(report);return report;
            }
            finally{src?.Dispose();dst?.Dispose();Object.DestroyImmediate(compute);}
        }
        public static string StartPerformance(string revision)
        {
            if(!EditorApplication.isPlaying||EditorApplication.isPaused||Time.captureDeltaTime!=0)throw new Exception("Requires ordinary unpaused Play");
            if(Time.frameCount<60||Object.FindAnyObjectByType<WindPerformance24>())throw new Exception("Wait for Play initialization; only one benchmark may run");
            var grass=Object.FindAnyObjectByType<ChunkedGrassRenderer24>();var ground=Object.FindAnyObjectByType<MapHeightSampler>();
            if(!grass||!grass.material||grass.material.shader.name!="OnlyVolunteers/Wind/v01/IndirectGrass")throw new Exception("Start comparison from the installed shared-wind material");
            string path=Path.GetFullPath("Working/Reviews/Wind/performance_"+revision+".json");if(File.Exists(path))throw new Exception("Evidence exists");
            var old=AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/Grass/Baked_v04/TallGrass_v04.mat");
            new GameObject("WindPerformance_Temporary").AddComponent<WindPerformance24>().Begin(old,grass,new Vector3(170,ground.Height(170,425)+1.65f,425),0,new Vector3(465,ground.Height(465,621)+1.65f,621),110,path);
            return "Started original/shared-wind comparison: "+path;
        }
    }
}
