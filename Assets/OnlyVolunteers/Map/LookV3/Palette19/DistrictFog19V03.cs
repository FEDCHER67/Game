using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // PC checkpoint-P fog. The weather controller remains the sole owner of camera atmosphere.
    // This module owns the scoped renderer and VFX, and is called once per camera by that controller.
    [ExecuteAlways]
    public sealed class DistrictFog19V03 : MonoBehaviour
    {
        [Serializable] public struct Bank { public Vector3 position; public Vector2 size; public float phase; public bool forest; }
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
        public float roughDensity=.031f, forestDensity=.026f, groundExtinction=.055f;
        [NonSerialized] public float reviewTime=-1;
        public Vector4 LastDensity { get; private set; }
        public int DropletCount { get; private set; }
        RenderPipelineAsset previousPipeline;
        Material fog, mist, glow, previousPassMaterial;
        GameObject rig;
        ParticleSystem droplets, patches, lights;
        readonly ParticleSystem.Particle[] dropBuffer=new ParticleSystem.Particle[140];
        readonly ParticleSystem.Particle[] bankBuffer=new ParticleSystem.Particle[32];
        readonly ParticleSystem.Particle[] lightBuffer=new ParticleSystem.Particle[32];

        void OnEnable() { Prepare(); }
        bool Prepare()
        {
            if(!pipeline || !feature || !fogTemplate || !mistTemplate || !haloTemplate) return false;
            if(!fog)
            {
                previousPipeline=QualitySettings.renderPipeline==pipeline && baselinePipeline ? baselinePipeline : QualitySettings.renderPipeline;
                fog=new Material(fogTemplate){hideFlags=HideFlags.HideAndDontSave};
                mist=new Material(mistTemplate){hideFlags=HideFlags.HideAndDontSave};
                glow=new Material(haloTemplate){hideFlags=HideFlags.HideAndDontSave};
                previousPassMaterial=feature.passMaterial;feature.passMaterial=fog;
                QualitySettings.renderPipeline=pipeline;
                rig=new GameObject("V19_Fog_RuntimeOnly"){hideFlags=HideFlags.HideAndDontSave};
                droplets=MakeParticles("CameraAttached_MistDroplets",140,mist);
                patches=MakeParticles("World_MistBanks",32,mist);
                lights=MakeParticles("Lamp_Window_Headlight_Scatter",32,glow);
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
            foreach(var headlight in vanHeadlights)if(headlight)headlight.intensity=1.6f*amount;
            var milk=new Color(.77f,.81f,.83f,1);
            float density2=rough*roughDensity*roughDensity+forest*forestDensity*forestDensity;
            LastDensity=new Vector4(rough,forest,Mathf.Sqrt(density2),groundExtinction*(rough+forest*.72f));
            fog.SetVector("_FogDensity",new Vector4(density2,LastDensity.w,amount,2.3f));
            fog.SetVector("_Baseline",new Vector4(RenderSettings.fogStartDistance,RenderSettings.fogEndDistance,0,0));
            fog.SetColor("_BaselineColour",RenderSettings.fogColor.linear);
            fog.SetColor("_MilkColour",milk.linear);fog.SetTexture("_GroundHeights",groundHeights);fog.SetVector("_TerrainWorld",terrainWorld);
            fog.SetFloat("_MistTime",now);
            // The fullscreen pass replaces surface fog only while dense district fog has nonzero weight.
            // At zero weight the original surface fog and approved other-district look are untouched.
            if(amount>0.00001f) RenderSettings.fog=false;
            mist.SetFloat("_MistTime",now);glow.SetFloat("_MistTime",now);
            int n=0;
            for(int i=0;i<dropBuffer.Length && amount>.001f;i++)
            {
                float depth=.8f+Hash(i+27)*6.5f;
                var local=new Vector3((Hash(i+104)-.5f)*11+Mathf.Sin(now*.10f+i)*.3f,
                    Mathf.Repeat(Hash(i+201)*5+now*.017f,5)-2.5f,depth);
                float size=.006f+Hash(i+321)*.015f;
                dropBuffer[n++]=Particle(camera.transform.TransformPoint(local),new Vector3(size,size,1),new Color(.85f,.91f,.93f,.13f*amount));
            }
            DropletCount=n;droplets.SetParticles(dropBuffer,n);
            n=0;
            foreach(var bank in banks)
            {
                if(n>=bankBuffer.Length)break;
                float fade=bank.forest?forest:rough;if(fade<.001f)continue;
                var p=bank.position+new Vector3(Mathf.Sin(now*.045f+bank.phase)*1.7f,Mathf.Sin(now*.07f+bank.phase)*.2f,Mathf.Cos(now*.035f+bank.phase)*1.2f);
                bankBuffer[n++]=Particle(p,new Vector3(bank.size.x,bank.size.y,1),new Color(.70f,.76f,.79f,(bank.forest?.14f:.22f)*fade));
            }
            patches.SetParticles(bankBuffer,n);n=0;
            foreach(var h in halos)
            {
                if(n>=lightBuffer.Length)break;
                if(h.light && (!h.light.enabled || !h.light.gameObject.activeInHierarchy))continue;
                Vector3 p=h.light?h.light.transform.position:h.position;
                float strength=h.light?Mathf.Clamp01(h.light.intensity*1.3f+.12f):1;
                float distance=Vector3.Distance(camera.transform.position,p);
                float atten=Mathf.Exp(-density2*distance*distance*.6f);
                var col=h.colour;col.a*=amount*strength*atten;
                lightBuffer[n++]=Particle(p,new Vector3(h.size,h.size,1),col);
            }
            lights.SetParticles(lightBuffer,n);
        }
        void OnDisable()
        {
            if(!fog)return;
            if(QualitySettings.renderPipeline==pipeline) QualitySettings.renderPipeline=previousPipeline;
            if(feature && feature.passMaterial==fog)feature.passMaterial=previousPassMaterial;
            Release(rig);Release(fog);Release(mist);Release(glow);fog=null;mist=null;glow=null;rig=null;
            #if UNITY_EDITOR
            // Unity's scene save persists this temporary quality override, while SaveAssetIfDirty
            // does not save ProjectSettings. Restore only our exact serialized reference; all other
            // settings, line endings and existing edits remain byte-for-byte untouched.
            if(!Application.isPlaying && previousPipeline && QualitySettings.renderPipeline==previousPipeline)
            {
                string own=UnityEditor.AssetDatabase.AssetPathToGUID(UnityEditor.AssetDatabase.GetAssetPath(pipeline));
                string prior=UnityEditor.AssetDatabase.AssetPathToGUID(UnityEditor.AssetDatabase.GetAssetPath(previousPipeline));
                string path=System.IO.Path.GetFullPath(System.IO.Path.Combine(Application.dataPath,"../ProjectSettings/QualitySettings.asset"));
                if(own.Length>0 && prior.Length>0 && own!=prior && System.IO.File.Exists(path))
                {
                    string text=System.IO.File.ReadAllText(path);
                    string needle="customRenderPipeline: {fileID: 11400000, guid: "+own+", type: 2}";
                    if(text.Contains(needle))System.IO.File.WriteAllText(path,text.Replace(needle,
                        "customRenderPipeline: {fileID: 11400000, guid: "+prior+", type: 2}"),new System.Text.UTF8Encoding(false));
                }
            }
            #endif
        }
        static void Release(UnityEngine.Object o){if(!o)return;if(Application.isPlaying)Destroy(o);else DestroyImmediate(o);}
    }
}
