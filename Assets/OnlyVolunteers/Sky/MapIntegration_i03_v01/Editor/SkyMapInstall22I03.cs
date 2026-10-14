using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.Sky22V04;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Sky22MapI03.Editor
{
    public static class SkyMapInstall22I03
    {
        public const string BaseScene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i02_grass.unity";
        public const string ScenePath="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i03_sky.unity";
        public const string Output="Working/Reviews/Sky";
        public static string Install()
        {
            OnlyVolunteers.Sky22V04.Editor.SkyReviewBuilder22.RequireLock();
            var scene=SceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode || scene.path!=BaseScene || scene.isDirty || File.Exists(ScenePath))
                throw new InvalidOperationException("Requires clean i02 in Edit mode and a new i03 destination.");
            var weather=Object.FindAnyObjectByType<DistrictWeather19V05>();
            if(!weather || !weather.sun || !weather.visibleFog || !weather.visibleFog.aerial || !weather.visibleFog.aerial.isActiveAndEnabled)
                throw new InvalidOperationException("Expected G18g atmosphere, sun and camera-scoped aerial path.");
            var template=AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Sky/G22_v04/Generated/PaintedSky_v04.mat");
            if(!template || ShaderUtil.ShaderHasError(template.shader))throw new InvalidOperationException("Complete v04 sky material required.");
            int before=Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).Count(t=>t.gameObject.scene==scene);
            weather.enabled=false;
            var rig=new GameObject("G22_DayNight_v04_Integration_i03");
            var clock=rig.AddComponent<SkyClock22>();clock.SetHour(8);clock.CycleMinutes=24;clock.Running=true;
            var moonObject=new GameObject("G22_Moon_i03");moonObject.transform.SetParent(rig.transform,false);
            var moon=moonObject.AddComponent<Light>();moon.type=LightType.Directional;moon.intensity=0;moon.enabled=false;
            var bridge=rig.AddComponent<SkyDistrictV19Bridge22>();bridge.Configure(weather);
            var sky=rig.AddComponent<SkyRenderer22>();sky.Configure(clock,template,weather.sun,moon);sky.DistrictSource=bridge;sky.CloudTime=650;
            var lamps=Object.FindObjectsByType<DistrictLife19V02>(FindObjectsInactive.Include).Where(x=>x.wornLamps!=null).SelectMany(x=>x.wornLamps).Where(x=>x).Distinct().ToArray();
            var slots=new List<SkyMapNight22I03.Slot>();
            foreach(var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include))
            {
                var mats=r.sharedMaterials;
                for(int i=0;i<mats.Length;i++)if(mats[i] && new[]{"MP_Lamp_Glow","Full19_WarmWindow","CoolGarageWindow"}.Contains(mats[i].name))
                    slots.Add(new SkyMapNight22I03.Slot{renderer=r,index=i});
            }
            var night=rig.AddComponent<SkyMapNight22I03>();night.Configure(clock,lamps,slots.ToArray(),weather.visibleFog);
            RenderSettings.skybox=template;
            if(!EditorSceneManager.SaveScene(scene,ScenePath))throw new IOException("Could not save i03 scene.");
            string text=$"Installed v04 in {ScenePath}\nBase={BaseScene}\nOriginal transforms={before}; added=2\nMorning=08:00; cycle=24 minutes\nLamps={lamps.Length}; emissive slots={slots.Count}\nG18g path: SkyRenderer22 -> state.fog/horizon -> SkyDistrictV19Bridge22.AfterAtmosphere -> DistrictFog19V05.ConfigureCamera -> DistrictAerial19V01.ConfigureCamera\nOld Weather19V05 disabled; district data retained.\n";
            WriteNew(Output+"/installation_i03_v01.txt",text);return text;
        }
        public static void WriteNew(string path,string text)
        {Directory.CreateDirectory(Path.GetDirectoryName(path));using(var writer=new StreamWriter(new FileStream(path,FileMode.CreateNew)))writer.Write(text);}
    }
}
