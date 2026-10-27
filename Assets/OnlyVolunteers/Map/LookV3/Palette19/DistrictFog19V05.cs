using System.Collections.Generic;
using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // Defaults describe the original v05; final v19 scenes serialize the approved v06
    // halfway blend from v04 toward v03, including droplets. G45 evaluates forest fog at 85% of the reviewed density once.
    // PC district fog. The weather controller remains the sole owner of camera atmosphere.
    // This module owns the scoped renderer and VFX, and is called once per camera by that controller.
    [ExecuteAlways]
    public sealed class DistrictFog19V05 : MonoBehaviour
    {
        [Serializable] public struct Bank { public Vector3 position; public Vector2 size; public float phase; public bool forest; public float opacity; }
        [Serializable] public struct Halo { public Vector3 position; public Color colour; public float size; public Light light; }
        public UniversalRenderPipelineAsset pipeline;
        public RenderPipelineAsset baselinePipeline;
        public FullScreenPassRendererFeature feature;
        public Material fogTemplate, mistTemplate, haloTemplate;
        public Texture2D groundHeights;
        public Vector4 terrainWorld;
        public Bank[] banks = Array.Empty<Bank>();
        public Halo[] halos = Array.Empty<Halo>();
        public Light[] vanHeadlights=Array.Empty<Light>();
        public float roughDensity=.01135f, roughHazeStart=33.75f, forestDensity=.026f, groundExtinction=.055f;
        [NonSerialized] public float reviewTime=-1;
        public Vector4 LastDensity { get; private set; }
        public int DropletCount { get; private set; }
        public float roughGroundWeight=.25f;
        public int roughDropletLimit=24;
        public float roughDropletOpacity=.018f;
        public Material RuntimeFogMaterial => fog;
        public DistrictAerial19V01 aerial;
        DistrictFogPass19V01 cameraPass;
        Material fog, mist, glow;
        GameObject rig;
        ParticleSystem droplets, patches, lights;
        readonly ParticleSystem.Particle[] dropBuffer=new ParticleSystem.Particle[140];
        readonly ParticleSystem.Particle[] bankBuffer=new ParticleSystem.Particle[32];
        readonly ParticleSystem.Particle[] lightBuffer=new ParticleSystem.Particle[96]; // W86: the nearest 96 lit halos (every lamp on the map has one)
        readonly List<(float d,int i)> haloOrder=new();

        void OnEnable() { Prepare(); }
        bool Prepare()
        {
            if(!fogTemplate || !mistTemplate || !haloTemplate) return false;
            if(!fog)
            {
                fog=new Material(fogTemplate){hideFlags=HideFlags.HideAndDontSave};
                mist=new Material(mistTemplate){hideFlags=HideFlags.HideAndDontSave};
                glow=new Material(haloTemplate){hideFlags=HideFlags.HideAndDontSave};
                cameraPass=new DistrictFogPass19V01();
                cameraPass.SetMaterial(fog);
                rig=new GameObject("V19_Fog_RuntimeOnly"){hideFlags=HideFlags.HideAndDontSave};
                droplets=MakeParticles("CameraAttached_MistDroplets",140,mist);
                patches=MakeParticles("World_MistBanks",32,mist);
                lights=MakeParticles("Lamp_Window_Headlight_Scatter",96,glow);
            }
            return true;
        }
        ParticleSystem MakeParticles(string name,int count,Material material)
        {
            var go=new GameObject(name){hideFlags=HideFlags.HideAndDontSave};go.transform.SetParent(rig.transform,false);
            var ps=go.AddComponent<ParticleSystem>();ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var m=ps.main;m.maxParticles=count;m.loop=false;m.playOnAwake=false;m.startSpeed=0;m.startLifetime=100000;
            m.simulationSpace=ParticleSystemSimulationSpace.World;m.startSize3D=true;m.cullingMode=ParticleSystemCullingMode.AlwaysSimulate;
            var emission=ps.emission;emission.enabled=false;var shape=ps.shape;shape.enabled=false;
            var r=go.GetComponent<ParticleSystemRenderer>();r.sharedMaterial=material;r.renderMode=ParticleSystemRenderMode.Billboard;
            r.alignment=ParticleSystemRenderSpace.View;r.maxParticleSize=1;r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=false;
            // SetParticles on a stopped system is discarded by Unity. Pause an initialized system;
            // the weather callback supplies stable particles before each camera's cull/render.
            ps.Play();ps.Pause();return ps;
        }
        static float Hash(int n)=>Mathf.Repeat(Mathf.Sin(n*127.1f+311.7f)*43758.5453f,1);
        static ParticleSystem.Particle Particle(Vector3 p,Vector3 size,Color c)=>new()
        {position=p,startSize3D=size,startColor=c,startLifetime=100000,remainingLifetime=100000,randomSeed=1};

        public void ConfigureCamera(Camera camera,DistrictAtmosphere19.District[] districts,float[] weights)
        {
            if(!Prepare()) return;
            float rough=0,forest=0;
            for(int i=0;i<districts.Length;i++)
            {if(districts[i].id=="residential")rough=weights[i];if(districts[i].id=="forest")forest=weights[i];}
            float amount=rough+forest, now=reviewTime>=0?reviewTime:Time.time;
            foreach(var headlight in vanHeadlights)if(headlight)headlight.intensity=1.6f*(forest+rough*.25f);
            var milk=Color.Lerp(new Color(.40f,.46f,.49f,1),new Color(.77f,.81f,.83f,1),amount>0?forest/amount:0);
            // G45: forest-only 15% reduction after the existing global boost. Pure evaluation is rebuild-idempotent.
            const float forestFogScale=.85f;
            float forestDistanceDensity=forestDensity*forestFogScale;
            float density2=rough*roughDensity*roughDensity+forest*forestDistanceDensity*forestDistanceDensity;
            LastDensity=new Vector4(rough,forest,Mathf.Sqrt(density2),groundExtinction*(rough*roughGroundWeight+forest*.72f*forestFogScale));
            fog.SetVector("_FogDensity",new Vector4(density2,LastDensity.w,amount,2.3f));
            fog.SetVector("_DistrictDistance",new Vector4(rough*roughDensity*roughDensity,forest*forestDistanceDensity*forestDistanceDensity,roughHazeStart,rough*.28f+forest*6));
            fog.SetFloat("_ForwardScatter",rough*.003f+forest*.012f*forestFogScale);
            fog.SetVector("_Baseline",new Vector4(RenderSettings.fogStartDistance,RenderSettings.fogEndDistance,0,0));
            fog.SetColor("_BaselineColour",RenderSettings.fogColor.linear);
            fog.SetColor("_MilkColour",milk.linear);fog.SetTexture("_GroundHeights",groundHeights);fog.SetVector("_TerrainWorld",terrainWorld);
            fog.SetFloat("_MistTime",now);
            // The fullscreen pass replaces surface fog only while dense district fog has nonzero weight.
            // At zero weight the original surface fog and approved other-district look are untouched.
            if(amount>0.00001f) RenderSettings.fog=false;
            mist.SetFloat("_MistTime",now);glow.SetFloat("_MistTime",now);
            int n=0;
            // Forest retains all v03 droplets; Rough has only a few nearly invisible motes.
            int dropLimit=forest>.001f?dropBuffer.Length:Mathf.Clamp(roughDropletLimit,0,dropBuffer.Length);
            for(int i=0;i<dropLimit && amount>.001f;i++)
            {
                float depth=.8f+Hash(i+27)*6.5f;
                var local=new Vector3((Hash(i+104)-.5f)*11+Mathf.Sin(now*.10f+i)*.3f,
                    Mathf.Repeat(Hash(i+201)*5+now*.017f,5)-2.5f,depth);
                float size=.006f+Hash(i+321)*.015f;
                dropBuffer[n++]=Particle(camera.transform.TransformPoint(local),new Vector3(size,size,1),new Color(.85f,.91f,.93f,(.13f*forest*forestFogScale+roughDropletOpacity*rough)));
            }
            DropletCount=n;droplets.SetParticles(dropBuffer,n);
            n=0;
            foreach(var bank in banks)
            {
                if(n>=bankBuffer.Length)break;
                float fade=bank.forest?forest:rough;if(fade<.001f)continue;
                var p=bank.position+new Vector3(Mathf.Sin(now*.045f+bank.phase)*1.7f,Mathf.Sin(now*.07f+bank.phase)*.2f,Mathf.Cos(now*.035f+bank.phase)*1.2f);
                bankBuffer[n++]=Particle(p,new Vector3(bank.size.x,bank.size.y,1),new Color(.70f,.76f,.79f,(bank.forest?.14f*forestFogScale:bank.opacity)*fade));
            }
            patches.SetParticles(bankBuffer,n);n=0;
            haloOrder.Clear();
            for(int k=0;k<halos.Length;k++)
            {
                var hk=halos[k];
                if(hk.light && (!hk.light.enabled || !hk.light.gameObject.activeInHierarchy))continue;
                Vector3 pk=hk.light?hk.light.transform.position:hk.position;
                haloOrder.Add(((pk-camera.transform.position).sqrMagnitude,k));
            }
            haloOrder.Sort((a,b)=>a.d.CompareTo(b.d));
            foreach(var (_,hi) in haloOrder)
            {
                if(n>=lightBuffer.Length)break;
                var h=halos[hi];
                Vector3 p=h.light?h.light.transform.position:h.position;
                float strength=h.light?Mathf.Clamp01(h.light.intensity*1.3f+.12f):1;
                float distance=Vector3.Distance(camera.transform.position,p);
                float atten=Mathf.Exp(-density2*distance*distance*.6f);
                // W86 (Fedya 25.10): a halo round every lamp, its size and glow growing with the fog here: the district banks (forest,
                // rough) plus the plain haze (a nearer fog end = denser air); clear streets keep a small faint glow
                float haze=Mathf.Clamp01((650f-RenderSettings.fogEndDistance)/450f);
                float fogK=Mathf.Clamp01(forest+rough*.6f+haze*.6f);
                var col=h.colour;col.a*=(.22f+.78f*fogK)*strength*atten;
                float sz=h.size*(.55f+.95f*fogK);
                lightBuffer[n++]=Particle(p,new Vector3(sz,sz,1),col);
            }
            lights.SetParticles(lightBuffer,n);
            // The scene owns the pass; no renderer or pipeline asset is changed.
            if(aerial && aerial.isActiveAndEnabled) aerial.ConfigureCamera(camera,districts,weights,this,RenderSettings.fogColor);
            if((amount>0.00001f || (aerial && aerial.isActiveAndEnabled)) && cameraPass!=null)
                camera.GetUniversalAdditionalCameraData().scriptableRenderer.EnqueuePass(cameraPass);
        }
        void OnDisable()
        {
            if(!fog)return;
            Release(rig);Release(fog);Release(mist);Release(glow);
            fog=null;mist=null;glow=null;rig=null;cameraPass=null;
        }
        static void Release(UnityEngine.Object o){if(!o)return;if(Application.isPlaying)Destroy(o);else DestroyImmediate(o);}
    }
}
