using System;
using System.IO;
using OnlyVolunteers.Map.Look.V3;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22V03.Editor
{
    // Contract test with isolated district data; does not open or modify the map scene.
    public static class SkyMapDiagnostics22
    {
        public static string Run()
        {
            SkyReviewBuilder22.RequireLock();
            var root=new GameObject("G22 isolated district verification"){hideFlags=HideFlags.HideAndDontSave};root.SetActive(false);
            VolumeProfile original=null;SkyDistrictV19Bridge22 bridge=null;
            try
            {
                var source=root.AddComponent<DistrictWeather19V05>();source.enabled=false;
                source.districts=new[]{
                    new DistrictAtmosphere19.District{id="village",bounds=new Vector4(0,0,100,100),fogStart=95,fogEnd=520,fogColour=new Color(.7f,.8f,.9f),exposure=.7f,saturation=4},
                    new DistrictAtmosphere19.District{id="residential",bounds=new Vector4(130,0,230,100),fogStart=45,fogEnd=240,fogColour=new Color(.48f,.54f,.6f),exposure=-.2f,saturation=-35}};
                source.weather=new[]{
                    new DistrictWeather19V05.Weather{zenith=new Color(.2f,.53f,.82f),horizon=new Color(.7f,.8f,.9f),clouds=Color.white,sunColour=Color.white,cloudCover=.46f,sunIntensity=1.1f,ambientIntensity=.95f},
                    new DistrictWeather19V05.Weather{zenith=new Color(.32f,.37f,.41f),horizon=new Color(.61f,.65f,.69f),clouds=new Color(.47f,.52f,.56f),sunColour=new Color(.8f,.85f,.9f),cloudCover=.96f,sunIntensity=.38f,ambientIntensity=.68f}};
                source.blendMetres=60;
                var volume=root.AddComponent<Volume>();source.blendVolume=volume;
                original=ScriptableObject.CreateInstance<VolumeProfile>();original.hideFlags=HideFlags.HideAndDontSave;
                var originalGrade=original.Add<ColorAdjustments>(true);originalGrade.postExposure.value=.123f;
                original.Add<WhiteBalance>(true);volume.profile=original;
                bridge=root.AddComponent<SkyDistrictV19Bridge22>();bridge.Configure(source);
                var hamlet=bridge.Sample(new Vector3(50,0,50));var rough=bridge.Sample(new Vector3(180,0,50));var middle=bridge.Sample(new Vector3(115,0,50));
                if(Mathf.Abs(hamlet.cloudCover-.46f)>.001f || Mathf.Abs(rough.cloudCover-.96f)>.001f || Mathf.Abs(middle.cloudCover-.71f)>.001f)
                    throw new Exception("District field or cloud-cover blending is incorrect.");
                if(SkyModel22.Evaluate(12,rough).sunIntensity>=SkyModel22.Evaluate(12,hamlet).sunIntensity*.4f)
                    throw new Exception("Rough lost noon gloom.");
                var night=SkyModel22.Evaluate(22,rough);
                if(night.moonIntensity<=0 || night.ambient.maxColorComponent<=0)throw new Exception("Rough night has no light.");
                var camera=root.AddComponent<Camera>();bridge.AfterAtmosphere(camera,SkyModel22.Evaluate(12,middle));
                if(volume.profile==original)throw new Exception("Adapter mutated the shared profile instead of cloning.");
                volume.profile.TryGet<ColorAdjustments>(out var runtimeGrade);
                if(Mathf.Abs(runtimeGrade.postExposure.value-.25f)>.001f || Mathf.Abs(originalGrade.postExposure.value-.123f)>.001f)
                    throw new Exception("District grading or source-profile preservation failed.");
                bridge.AfterCamera(camera);
                if(Mathf.Abs(runtimeGrade.postExposure.value-.123f)>.001f)throw new Exception("Camera grade was not restored.");
                bridge.Configure(null);if(volume.profile!=original)throw new Exception("Prior volume profile was not restored on unbind.");
                string path="Working/Reviews/Sky/district_contract_v03.txt";
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                using(var writer=new StreamWriter(new FileStream(path,FileMode.CreateNew)))writer.Write(
                    "PASS: existing DistrictBlend19 field and 50/50 transition\nPASS: noon Rough lighting remains darker\nPASS: nonzero Rough night lighting\nPASS: per-camera grade blend\nPASS: original profile unchanged\nPASS: camera grade and previous profile restored\nScope: isolated contract data using actual G18 types, not a full-map visual certification.\n");
                return path;
            }
            finally
            {
                if(bridge)bridge.Configure(null);
                if(original){foreach(var item in original.components)Object.DestroyImmediate(item);Object.DestroyImmediate(original);}
                Object.DestroyImmediate(root);
            }
        }
    }
}
