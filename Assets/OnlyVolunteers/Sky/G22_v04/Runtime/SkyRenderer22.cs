using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Sky22V04
{
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class SkyRenderer22 : MonoBehaviour
    {
        [SerializeField] SkyClock22 clock;
        [SerializeField] Material skyTemplate;
        [SerializeField] Light sun, moon;
        [SerializeField] SkyDistrictSource22 districtSource;
        [SerializeField] SkyMood22 mood=SkyMood22.Hamlet;
        [SerializeField,Range(0,360)] float sunAzimuth=25;
        [SerializeField,Range(0,2)] float windSpeed=.15f;
        [SerializeField,Range(.3f,3)] float cloudScale=1;
        [SerializeField,Range(24,80)] int cloudSteps=64;
        [SerializeField,Min(0)] float cloudTime;
        [Tooltip("W86: the light (and its shadows) turns in steps of this many degrees while the sky disc moves smoothly. " +
                 "A light that turns every frame re-rasterises the shadow map each frame: long shadows (the 130 m towers) " +
                 "crawl and shimmer and URP's texel snapping cannot hold them. 0 = follow every frame: the default since Fedya 25.10 (the steps moved all the lighting in jerks).")]
        [SerializeField,Range(0,2)] float shadowStepDegrees=0f;
        Vector3 sunShadowDir, moonShadowDir;
        Material sky;
        readonly Stack<Saved> saved=new Stack<Saved>();
        public SkyMood22 Mood { get=>mood;set=>mood=value; }
        public SkyState22 LastState { get; private set; }
        // G18g can consume this per-camera result once its horizon API exists. Colours are Unity gamma-space Color values.
        public event System.Action<Camera,Color> HorizonColourEvaluated;
        public float CloudTime { get=>cloudTime;set=>cloudTime=Mathf.Max(0,value); }
        public SkyDistrictSource22 DistrictSource { get=>districtSource;set=>districtSource=value; }
        static float smoothGloom=.1f;
        /// <summary>0 by day .. 1 at full night (19:30-04:30), smooth at dusk/dawn (clouds fade out with it).</summary>
        public static float NightAmount(float hour)
        {
            hour=Mathf.Repeat(hour,24f);
            if(hour>=19.5f || hour<4.5f)return 1f;
            if(hour>=18f)return Mathf.SmoothStep(0f,1f,(hour-18f)/1.5f);
            if(hour<6f)return Mathf.SmoothStep(1f,0f,(hour-4.5f)/1.5f);
            return 0f;
        }
        public void Configure(SkyClock22 c, Material template, Light s, Light m) { clock=c;skyTemplate=template;sun=s;moon=m;ReleaseSky(); }
        void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering+=BeginCamera;
            RenderPipelineManager.endCameraRendering+=EndCamera;
        }
        void Update() { if(Application.isPlaying)cloudTime+=Time.deltaTime; }
        void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering-=BeginCamera;
            RenderPipelineManager.endCameraRendering-=EndCamera;
            while(saved.Count>0)saved.Pop().Restore(sun,moon);
            ReleaseSky();
        }
        void ReleaseSky() { if(sky) { if(Application.isPlaying)Destroy(sky);else DestroyImmediate(sky); } sky=null; }
        void BeginCamera(ScriptableRenderContext context, Camera camera)
        {
            // Every begin has a corresponding stack entry, including ignored camera types.
            saved.Push(Saved.Read(camera,sun,moon));
            if(camera.cameraType==CameraType.Preview || !clock || !skyTemplate)return;
            if(districtSource && districtSource.isActiveAndEnabled && !districtSource.Ready)return;
            if(!sky)sky=new Material(skyTemplate){hideFlags=HideFlags.HideAndDontSave};
            SkyMood22 local=districtSource && districtSource.isActiveAndEnabled?districtSource.Sample(camera.transform.position):mood;
            SkyState22 state=SkyModel22.Evaluate(clock.Hour,local,sunAzimuth); LastState=state;HorizonColourEvaluated?.Invoke(camera,state.horizon);
            sky.SetColor("_Zenith",state.zenith);sky.SetColor("_Horizon",state.horizon);
            sky.SetColor("_CloudTop",state.cloudTop);sky.SetColor("_CloudBase",state.cloudBase);
            sky.SetColor("_SunColour",state.sunlight);sky.SetColor("_MoonColour",state.moonlight);
            sky.SetVector("_SunDirection",state.sunDirection);sky.SetVector("_MoonDirection",state.moonDirection);
            // Vadim 23.10: one cloud cover for the whole map (no clouds sliding in/out between districts), clouds fade out at night,
            // the district gloom drifts very slowly
            smoothGloom=Mathf.MoveTowards(smoothGloom,Mathf.Clamp01(local.gloom),Time.unscaledDeltaTime*.03f);
            sky.SetFloat("_Cover",Mathf.Lerp(.38f,0f,NightAmount(clock.Hour)));sky.SetFloat("_Gloom",smoothGloom);
            sky.SetFloat("_Stars",state.stars);sky.SetFloat("_Golden",state.golden);sky.SetFloat("_Daylight",state.daylight);
            sky.SetFloat("_CloudTime",cloudTime*windSpeed);sky.SetFloat("_CloudScale",cloudScale);sky.SetFloat("_Steps",cloudSteps);
            RenderSettings.skybox=sky;
            SetLight(sun,Stepped(ref sunShadowDir,state.sunDirection),state.sunlight,state.sunIntensity,state.shadowStrength,state.daylight>.35f);
            SetLight(moon,Stepped(ref moonShadowDir,state.moonDirection),state.moonlight,state.moonIntensity,.2f,state.daylight<=.35f); // W86: softer moon shadow
            RenderSettings.sun=state.daylight>.35f?sun:moon;
            RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientIntensity=1;
            RenderSettings.ambientSkyColor=state.ambient;RenderSettings.ambientEquatorColor=state.ambient*.85f;
            RenderSettings.ambientGroundColor=state.ambient*.55f;
            var probe=new SphericalHarmonicsL2();probe.AddAmbientLight(state.ambient.linear*.75f);RenderSettings.ambientProbe=probe;
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;RenderSettings.fogColor=state.fog;
            RenderSettings.fogStartDistance=Mathf.Max(0,local.fogStart);
            RenderSettings.fogEndDistance=Mathf.Max(local.fogStart+1,local.fogEnd);
            if(districtSource && districtSource.isActiveAndEnabled)districtSource.AfterAtmosphere(camera,state);
        }
        void EndCamera(ScriptableRenderContext context, Camera camera)
        {
            if(districtSource && districtSource.isActiveAndEnabled)districtSource.AfterCamera(camera);
            if(saved.Count>0 && saved.Peek().camera==camera)saved.Pop().Restore(sun,moon);
        }
        // The held light direction moves only once the sky's direction is shadowStepDegrees away (a jump after F12 or a
        // clock set is taken at once, being far beyond the step).
        Vector3 Stepped(ref Vector3 held, Vector3 direction)
        {
            if(held==Vector3.zero || shadowStepDegrees<=0 || Vector3.Angle(held,direction)>=shadowStepDegrees)held=direction;
            return held;
        }
        static void SetLight(Light light, Vector3 direction, Color colour, float intensity, float shadow, bool casts)
        {
            if(!light)return;
            light.transform.rotation=Quaternion.LookRotation(-direction,Mathf.Abs(direction.y)>.999f?Vector3.forward:Vector3.up);
            light.color=colour;light.intensity=intensity;light.enabled=intensity>.001f;
            light.shadowStrength=shadow;light.shadows=casts?LightShadows.Soft:LightShadows.None;
        }
        struct LightState
        {
            public bool enabled;public Color colour;public float intensity,shadow;public Quaternion rotation;public LightShadows shadows;
            public static LightState Read(Light l)=>!l?default:new LightState {enabled=l.enabled,colour=l.color,intensity=l.intensity,shadow=l.shadowStrength,rotation=l.transform.rotation,shadows=l.shadows};
            public void Restore(Light l) { if(!l)return;l.enabled=enabled;l.color=colour;l.intensity=intensity;l.shadowStrength=shadow;l.transform.rotation=rotation;l.shadows=shadows; }
        }
        struct Saved
        {
            public Camera camera;
            bool fog;FogMode mode;Color fogColour,ambientSky,equator,ground;float start,end,density,intensity;
            AmbientMode ambientMode;Material skybox;Light main;SphericalHarmonicsL2 probe;LightState sun,moon;
            public static Saved Read(Camera c,Light s,Light m)=>new Saved {camera=c,fog=RenderSettings.fog,mode=RenderSettings.fogMode,
                fogColour=RenderSettings.fogColor,start=RenderSettings.fogStartDistance,end=RenderSettings.fogEndDistance,density=RenderSettings.fogDensity,
                skybox=RenderSettings.skybox,main=RenderSettings.sun,ambientSky=RenderSettings.ambientSkyColor,equator=RenderSettings.ambientEquatorColor,
                ground=RenderSettings.ambientGroundColor,intensity=RenderSettings.ambientIntensity,ambientMode=RenderSettings.ambientMode,
                probe=RenderSettings.ambientProbe,sun=LightState.Read(s),moon=LightState.Read(m)};
            public void Restore(Light s,Light m)
            {
                RenderSettings.fog=fog;RenderSettings.fogMode=mode;RenderSettings.fogColor=fogColour;
                RenderSettings.fogStartDistance=start;RenderSettings.fogEndDistance=end;RenderSettings.fogDensity=density;
                RenderSettings.skybox=skybox;RenderSettings.sun=main;RenderSettings.ambientMode=ambientMode;
                RenderSettings.ambientSkyColor=ambientSky;RenderSettings.ambientEquatorColor=equator;RenderSettings.ambientGroundColor=ground;
                RenderSettings.ambientIntensity=intensity;RenderSettings.ambientProbe=probe;sun.Restore(s);moon.Restore(m);
            }
        }
    }
}
