using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    [ExecuteAlways]
    public sealed class DistrictWeather19V03 : MonoBehaviour
    {
        [Serializable]
        public sealed class Weather
        {
            public Color zenith, horizon, clouds, sunColour;
            public float cloudCover, cloudDensity, sunIntensity, ambientIntensity, shadowStrength;
        }
        public DistrictAtmosphere19.District[] districts;
        public Weather[] weather;
        public Material skyTemplate;
        public Light sun;
        public Volume blendVolume;
        public float blendMetres = 60;
        public DistrictFog19V03 visibleFog;
        private Material sky;
        private VolumeProfile grade;
        private ColorAdjustments colourAdjustments;
        private WhiteBalance whiteBalance;
        private Vector4[] bounds;
        private float[] weights;
        private readonly Stack<State> saved = new();
        public Vector3 LastHaze { get; private set; }
        public Color LastZenith { get; private set; }
        public float LastSun { get; private set; }
        private struct State
        {
            public bool fog;
            public FogMode mode;
            public Color fogColour, skyColour, equator, ground, sunColour;
            public float start, end, density, ambient, intensity, shadow;
            public Material skybox;
            public AmbientMode ambientMode;
            public SphericalHarmonicsL2 probe;
            public static State Read(Light light) => new() {
                fog=RenderSettings.fog, mode=RenderSettings.fogMode, fogColour=RenderSettings.fogColor,
                start=RenderSettings.fogStartDistance, end=RenderSettings.fogEndDistance, density=RenderSettings.fogDensity,
                skybox=RenderSettings.skybox, skyColour=RenderSettings.ambientSkyColor, equator=RenderSettings.ambientEquatorColor,
                ground=RenderSettings.ambientGroundColor, ambient=RenderSettings.ambientIntensity,
                ambientMode=RenderSettings.ambientMode, probe=RenderSettings.ambientProbe,
                intensity=light ? light.intensity : 0, sunColour=light ? light.color : Color.white, shadow=light ? light.shadowStrength : 0
            };
            public void Restore(Light light)
            {
                RenderSettings.fog=fog; RenderSettings.fogMode=mode; RenderSettings.fogColor=fogColour;
                RenderSettings.fogStartDistance=start; RenderSettings.fogEndDistance=end; RenderSettings.fogDensity=density;
                RenderSettings.skybox=skybox; RenderSettings.ambientMode=ambientMode;
                RenderSettings.ambientSkyColor=skyColour; RenderSettings.ambientEquatorColor=equator;
                RenderSettings.ambientGroundColor=ground; RenderSettings.ambientIntensity=ambient; RenderSettings.ambientProbe=probe;
                if (light) { light.intensity=intensity; light.color=sunColour; light.shadowStrength=shadow; }
            }
        }
        private void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering += BeginCamera;
            RenderPipelineManager.endCameraRendering += EndCamera;
        }
        private void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= BeginCamera;
            RenderPipelineManager.endCameraRendering -= EndCamera;
            while(saved.Count>0) saved.Pop().Restore(sun);
            if(sky) { if(Application.isPlaying) Destroy(sky); else DestroyImmediate(sky); }
            if(grade) { if(Application.isPlaying) Destroy(grade); else DestroyImmediate(grade); }
            sky=null; grade=null;
        }
        private bool Prepare()
        {
            if(districts==null || weather==null || districts.Length!=weather.Length || !skyTemplate) return false;
            if(weights==null || weights.Length!=districts.Length)
            {
                weights=new float[districts.Length]; bounds=new Vector4[districts.Length];
                for(int i=0;i<bounds.Length;i++) bounds[i]=districts[i].bounds;
            }
            if(!sky) sky=new Material(skyTemplate){hideFlags=HideFlags.HideAndDontSave};
            if(blendVolume && !grade)
            {
                grade=blendVolume.profile;
                grade.TryGet(out colourAdjustments); grade.TryGet(out whiteBalance);
            }
            return true;
        }
        public float[] Sample(Vector3 position)
        {
            if(!Prepare()) return Array.Empty<float>();
            DistrictBlend19.Weights(bounds, new Vector2(position.x,position.z),blendMetres,weights);
            return (float[])weights.Clone();
        }
        private void BeginCamera(ScriptableRenderContext context, Camera camera)
        {
            saved.Push(State.Read(sun));
            if(camera.cameraType==CameraType.Preview || camera.cameraType==CameraType.Reflection || !Prepare()) return;
            DistrictBlend19.Weights(bounds,new Vector2(camera.transform.position.x,camera.transform.position.z),blendMetres,weights);
            Color zenith=Color.clear,horizon=Color.clear,clouds=Color.clear,sunColour=Color.clear,fogColour=Color.clear;
            float cover=0,density=0,intensity=0,ambient=0,shadow=0,start=0,extinction=0,exposure=0,saturation=0,contrast=0,temperature=0;
            for(int i=0;i<districts.Length;i++)
            {
                float w=weights[i]; var d=districts[i];var a=weather[i];
                zenith+=a.zenith*w;horizon+=a.horizon*w;clouds+=a.clouds*w;sunColour+=a.sunColour*w;
                cover+=a.cloudCover*w;density+=a.cloudDensity*w;intensity+=a.sunIntensity*w;ambient+=a.ambientIntensity*w;shadow+=a.shadowStrength*w;
                fogColour+=d.fogColour*w;start+=d.fogStart*w;extinction+=w/Mathf.Max(1,d.fogEnd-d.fogStart);
                exposure+=d.exposure*w;saturation+=d.saturation*w;contrast+=d.contrast*w;temperature+=d.temperature*w;
            }
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;RenderSettings.fogColor=fogColour;
            RenderSettings.fogStartDistance=start;RenderSettings.fogEndDistance=start+1/Mathf.Max(extinction,.0001f);
            sky.SetColor("_Zenith",zenith);sky.SetColor("_Horizon",horizon);sky.SetColor("_CloudColour",clouds);
            sky.SetFloat("_CloudCover",cover);sky.SetFloat("_CloudDensity",density);
            sky.SetVector("_SunDirection",sun ? -sun.transform.forward : Vector3.up);sky.SetColor("_SunColour",sunColour);
            sky.SetFloat("_SunStrength",intensity*(1-cover*.92f));RenderSettings.skybox=sky;
            RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=Color.Lerp(horizon,zenith,.25f);
            RenderSettings.ambientEquatorColor=horizon;RenderSettings.ambientGroundColor=horizon*.55f;RenderSettings.ambientIntensity=ambient;
            var sh=new SphericalHarmonicsL2();sh.AddAmbientLight(horizon.linear*ambient*.8f);RenderSettings.ambientProbe=sh;
            if(sun) {sun.color=sunColour;sun.intensity=intensity;sun.shadowStrength=shadow;}
            if(colourAdjustments) {colourAdjustments.postExposure.value=exposure;colourAdjustments.saturation.value=saturation;colourAdjustments.contrast.value=contrast;}
            if(whiteBalance) whiteBalance.temperature.value=temperature;
            LastHaze=new Vector3(start,RenderSettings.fogEndDistance,extinction);LastZenith=zenith;LastSun=intensity;
            if(visibleFog && visibleFog.isActiveAndEnabled) visibleFog.ConfigureCamera(camera, districts, weights);
        }
        private void EndCamera(ScriptableRenderContext context, Camera camera)
        {
            if(saved.Count>0) saved.Pop().Restore(sun);
        }
    }
}
