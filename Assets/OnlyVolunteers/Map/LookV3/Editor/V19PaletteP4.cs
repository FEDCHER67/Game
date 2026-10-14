using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19PaletteP4
    {
        public const string Output=V19PaletteTest.Root+"/Test_v04";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v04.unity";
        static string Review=>V19PilotTools.OutDir;
        public static string Build()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first");
            if(File.Exists(Scene)||Directory.Exists(Output))throw new IOException("v04 already exists");
            EditorSceneManager.OpenScene(V19PaletteP3.Scene,OpenSceneMode.Single);
            var old=Object.FindAnyObjectByType<DistrictWeather19V03>();
            var oldFog=old.visibleFog;old.enabled=false;oldFog.enabled=false;
            LookAssetStore.EnsureFolder(Output);
            var weather=old.gameObject.AddComponent<DistrictWeather19V04>();weather.enabled=false;
            weather.districts=old.districts;
            weather.weather=old.weather.Select(w=>JsonUtility.FromJson<DistrictWeather19V04.Weather>(JsonUtility.ToJson(w))).ToArray();
            weather.skyTemplate=old.skyTemplate;weather.sun=old.sun;weather.blendVolume=old.blendVolume;weather.blendMetres=old.blendMetres;
            var rough=weather.districts.First(d=>d.id=="residential");
            rough.fogStart=100;rough.fogEnd=450;
            rough.fogColour=new Color(.40f,.46f,.49f,1);
            rough.exposure=-.20f;rough.saturation=-35;rough.contrast=18;rough.temperature=-12;
            var local=GameObject.Find("V19_Light_residential");
            if(local)
            {
                var volume=local.GetComponent<Volume>();
                string path=Output+"/RoughGrade.asset";
                if(!AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(volume.sharedProfile),path))throw new IOException("Cannot copy Rough profile");
                volume.sharedProfile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
                if(volume.sharedProfile.TryGet<ColorAdjustments>(out var grade))
                {grade.postExposure.Override(rough.exposure);grade.saturation.Override(rough.saturation);grade.contrast.Override(rough.contrast);EditorUtility.SetDirty(grade);}
                if(volume.sharedProfile.TryGet<WhiteBalance>(out var balance))
                {balance.temperature.Override(rough.temperature);EditorUtility.SetDirty(balance);}
                EditorUtility.SetDirty(volume.sharedProfile);AssetDatabase.SaveAssetIfDirty(volume.sharedProfile);
            }
            var fog=old.gameObject.AddComponent<DistrictFog19V04>();fog.enabled=false;weather.visibleFog=fog;
            fog.baselinePipeline=oldFog.baselinePipeline;
            fog.forestDensity=oldFog.forestDensity;fog.groundExtinction=oldFog.groundExtinction;
            fog.groundHeights=oldFog.groundHeights;fog.terrainWorld=oldFog.terrainWorld;
            fog.mistTemplate=oldFog.mistTemplate;fog.haloTemplate=oldFog.haloTemplate;fog.vanHeadlights=oldFog.vanHeadlights;
            fog.halos=oldFog.halos.Select(h=>JsonUtility.FromJson<DistrictFog19V04.Halo>(JsonUtility.ToJson(h))).ToArray();
            var sampler=Object.FindAnyObjectByType<MapHeightSampler>();
            var banks=oldFog.banks.Where(b=>b.forest).Select(b=>JsonUtility.FromJson<DistrictFog19V04.Bank>(JsonUtility.ToJson(b))).ToList();
            var pockets=new[]{new Vector2(590,596),new Vector2(683,653),new Vector2(718,632)};
            for(int i=0;i<pockets.Length;i++)
            {
                var p=pockets[i];banks.Add(new DistrictFog19V04.Bank{position=new Vector3(p.x,sampler.Height(p.x,p.y)+.65f,p.y),size=new Vector2(9+i,1.1f),phase=2+i*1.74f,forest=false});
            }
            fog.banks=banks.ToArray();
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(fog.baselinePipeline),Output+"/PC_FogPipeline_v19.asset");
            fog.pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Output+"/PC_FogPipeline_v19.asset");
            var rp=new SerializedObject(fog.pipeline);var list=rp.FindProperty("m_RendererDataList");
            int index=rp.FindProperty("m_DefaultRendererIndex").intValue;
            var source=(ScriptableRendererData)list.GetArrayElementAtIndex(index).objectReferenceValue;
            AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(source),Output+"/PC_FogRenderer_v19.asset");
            var renderer=AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(Output+"/PC_FogRenderer_v19.asset");
            list.GetArrayElementAtIndex(index).objectReferenceValue=renderer;rp.ApplyModifiedPropertiesWithoutUndo();
            fog.fogTemplate=new Material(Shader.Find("OnlyVolunteers/StyleV3/DistrictFog19V04")){name="DepthHeightFog_v19_v04"};
            AssetDatabase.CreateAsset(fog.fogTemplate,Output+"/DepthHeightFog.mat");
            fog.feature=ScriptableObject.CreateInstance<FullScreenPassRendererFeature>();fog.feature.name="V19_DistrictHaze_PC_v04";
            fog.feature.injectionPoint=FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingTransparents;
            fog.feature.fetchColorBuffer=false;fog.feature.requirements=ScriptableRenderPassInput.Depth;fog.feature.passMaterial=fog.fogTemplate;
            AssetDatabase.AddObjectToAsset(fog.feature,renderer);renderer.rendererFeatures.Add(fog.feature);
            var rd=new SerializedObject(renderer);var map=rd.FindProperty("m_RendererFeatureMap");map.arraySize=renderer.rendererFeatures.Count;
            for(int i=0;i<map.arraySize;i++){AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rendererFeatures[i],out string guid,out long id);map.GetArrayElementAtIndex(i).longValue=id;}
            rd.ApplyModifiedPropertiesWithoutUndo();renderer.SetDirty();EditorUtility.SetDirty(renderer);EditorUtility.SetDirty(fog.feature);
            AssetDatabase.SaveAssetIfDirty(renderer);AssetDatabase.SaveAssetIfDirty(fog.pipeline);AssetDatabase.SaveAssetIfDirty(fog.feature);
            weather.enabled=true;fog.enabled=true;
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),Scene);
            return Scene+"; Forest settings retained; 3 thin Rough mist pockets; original trees and terrain retained";
        }
        public static string Capture(string label,string only="")
        {
            var sampler=Object.FindAnyObjectByType<MapHeightSampler>();var fog=Object.FindAnyObjectByType<DistrictFog19V04>();fog.reviewTime=12;
            int count=0;try
            {
                foreach(var p in V19PilotTools.LoadPoses("palette_fog_poses_v03.json"))
                {
                    if(!(p.Pilot=="rough" || p.Name.StartsWith("t") || p.Name=="o01_forest"))continue;
                    if(only!="" && p.Name!=only)continue;
                    string path=Review+"/"+label+p.Name+".png";if(File.Exists(path))continue;
                    float y=float.IsNaN(p.SurfaceY)?sampler.Height(p.X,p.Z)+p.Above:p.SurfaceY;
                    V19PilotTools.Render(path,new Vector3(p.X,y+V19PilotTools.WalkEye,p.Z),Quaternion.Euler(p.Pitch,p.Yaw,0),p.Fov>0?p.Fov:75,460,1920,1080,false,0,true);count++;
                }
            }
            finally{fog.reviewTime=-1;}
            return count+" captured: "+label;
        }
    }
}
