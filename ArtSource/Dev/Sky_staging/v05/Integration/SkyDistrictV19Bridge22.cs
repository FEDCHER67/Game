using OnlyVolunteers.Map.Look.V3;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Sky22V05
{
    // Put outside the Sky22 asmdef: the existing map types live in Assembly-CSharp.
    // Read-only adapter. The map owner selects one weather owner on a NEW scene revision.
    [ExecuteAlways]
    public sealed class SkyDistrictV19Bridge22 : SkyDistrictSource22
    {
        [SerializeField] DistrictWeather19V05 source;
        Vector4[] bounds;
        float[] weights;
        Volume volume;
        VolumeProfile ownedProfile,priorProfile;
        ColorAdjustments grade;
        WhiteBalance balance;
        readonly Stack<GradeState> saved=new Stack<GradeState>();
        struct GradeState { public Camera camera;public Vector4 values; }
        public override bool Ready => source && !source.isActiveAndEnabled && source.districts!=null && source.weather!=null && source.districts.Length>0 && source.districts.Length==source.weather.Length;
        public void Configure(DistrictWeather19V05 value) { Release();source=value;bounds=null;weights=null; }
        public override SkyMood22 Sample(Vector3 position)
        {
            if(!Ready)return SkyMood22.Hamlet;
            if(weights==null || weights.Length!=source.districts.Length)
            {weights=new float[source.districts.Length];bounds=new Vector4[weights.Length];}
            for(int i=0;i<bounds.Length;i++)bounds[i]=source.districts[i].bounds;
            DistrictBlend19.Weights(bounds,new Vector2(position.x,position.z),source.blendMetres,weights);
            var result=new SkyMood22 {tint=Color.clear,districtPaletteWeight=1};float extinction=0;
            for(int i=0;i<weights.Length;i++)
            {
                var d=source.districts[i];var w=source.weather[i];float k=weights[i];
                result.cloudCover+=w.cloudCover*k;
                result.gloom+=(d.id=="residential"?.82f:d.id=="forest"?.64f:d.id=="industrial"?.25f:d.id=="transition"?.18f:.02f)*k;
                result.lightMultiplier+=w.sunIntensity/1.1f*k;result.ambientMultiplier+=w.ambientIntensity/.95f*k;
                result.tint+=Color.Lerp(Color.white,w.sunColour,.35f)*k;
                result.daytimeZenith+=w.zenith*k;result.daytimeHorizon+=w.horizon*k;result.daytimeCloud+=w.clouds*k;
                result.fogStart+=d.fogStart*k;extinction+=k/Mathf.Max(1,d.fogEnd-d.fogStart);
            }
            result.fogEnd=result.fogStart+1/Mathf.Max(.0001f,extinction);
            return result;
        }
        void PrepareGrade()
        {
            if(ownedProfile || !source.blendVolume)return;
            volume=source.blendVolume;
            priorProfile=volume.HasInstantiatedProfile()?volume.profile:null;
            var template=priorProfile?priorProfile:volume.sharedProfile;
            ownedProfile=ScriptableObject.CreateInstance<VolumeProfile>();ownedProfile.hideFlags=HideFlags.HideAndDontSave;
            if(template)foreach(var item in template.components) {var copy=Instantiate(item);copy.hideFlags=HideFlags.HideAndDontSave;ownedProfile.components.Add(copy);}
            if(!ownedProfile.TryGet(out grade))grade=ownedProfile.Add<ColorAdjustments>(true);
            if(!ownedProfile.TryGet(out balance))balance=ownedProfile.Add<WhiteBalance>(true);
            volume.profile=ownedProfile;
        }
        public override void AfterAtmosphere(Camera camera,SkyState22 state)
        {
            if(!Ready || weights==null)return;
            PrepareGrade();
            if(grade && balance)
            {
                saved.Push(new GradeState{camera=camera,values=new Vector4(grade.postExposure.value,grade.saturation.value,grade.contrast.value,balance.temperature.value)});
                Vector4 v=Vector4.zero;
                for(int i=0;i<weights.Length;i++){var d=source.districts[i];v+=new Vector4(d.exposure,d.saturation,d.contrast,d.temperature)*weights[i];}
                SetGrade(v);
            }
            if(source.visibleFog && source.visibleFog.isActiveAndEnabled)
            {
                source.visibleFog.ConfigureCamera(camera,source.districts,weights);
                // G18 creates this material as a transient clone. Never change the fogTemplate asset.
                var feature=source.visibleFog.feature;var material=feature?feature.passMaterial:null;
                if(material && (material.hideFlags & HideFlags.DontSave)!=0)
                    material.SetColor("_MilkColour",state.fog.linear);
            }
        }
        void SetGrade(Vector4 v) {grade.postExposure.value=v.x;grade.saturation.value=v.y;grade.contrast.value=v.z;balance.temperature.value=v.w;}
        public override void AfterCamera(Camera camera)
        {if(saved.Count>0 && saved.Peek().camera==camera)SetGrade(saved.Pop().values);}
        void OnDisable()=>Release();
        void Release()
        {
            saved.Clear();
            if(volume && ownedProfile && volume.HasInstantiatedProfile() && volume.profile==ownedProfile)volume.profile=priorProfile;
            if(ownedProfile){foreach(var item in ownedProfile.components)Dispose(item);Dispose(ownedProfile);}
            ownedProfile=null;priorProfile=null;volume=null;grade=null;balance=null;
        }
        static void Dispose(Object item) {if(!item)return;if(Application.isPlaying)Destroy(item);else DestroyImmediate(item);}
        public bool HasExclusiveOwnership => source && !source.isActiveAndEnabled;
    }
}
