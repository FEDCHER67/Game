using System;
using System.Collections.Generic;
using UnityEngine;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.Sky22V04;

namespace OnlyVolunteers.Sky22MapI03
{
    // Scene-local presentation only. Shared material assets and vehicle lighting stay untouched.
    [DisallowMultipleComponent]
    public sealed class SkyMapNight22I03 : MonoBehaviour
    {
        [Serializable] public struct Slot { public Renderer renderer; public int index; }
        [SerializeField] SkyClock22 clock;
        [SerializeField] Light[] lamps=Array.Empty<Light>();
        [SerializeField] Slot[] slots=Array.Empty<Slot>();
        [SerializeField] DistrictFog19V05 fog;
        readonly Dictionary<Renderer,Material[]> originals=new();
        readonly Dictionary<Material,Material> clones=new();
        bool[] priorLights;
        DistrictFog19V05.Halo[] priorHalos, ownedHalos;
        bool bound;
        public bool NightApplied { get; private set; }
        public int LampCount=>lamps.Length;
        public int EmissiveSlotCount=>slots.Length;
        public void Configure(SkyClock22 value,Light[] lights,Slot[] surfaces,DistrictFog19V05 haze)
        { Release();clock=value;lamps=lights;slots=surfaces;fog=haze;if(Application.isPlaying && isActiveAndEnabled)Bind(); }
        void OnEnable(){if(Application.isPlaying)Bind();}
        void OnDisable()=>Release();
        void Bind()
        {
            if(bound || !clock)return;
            priorLights=new bool[lamps.Length];
            for(int i=0;i<lamps.Length;i++)if(lamps[i])priorLights[i]=lamps[i].enabled;
            foreach(var slot in slots)
            {
                if(!slot.renderer)continue;
                if(!originals.ContainsKey(slot.renderer))originals.Add(slot.renderer,slot.renderer.sharedMaterials);
                var materials=slot.renderer.sharedMaterials;
                if(slot.index<0 || slot.index>=materials.Length || !materials[slot.index])continue;
                var original=originals[slot.renderer][slot.index];
                if(!clones.TryGetValue(original,out var clone))
                {clone=new Material(original){name=original.name+" (G22 night instance)",hideFlags=HideFlags.HideAndDontSave};clones.Add(original,clone);}
                materials[slot.index]=clone;slot.renderer.sharedMaterials=materials;
            }
            if(fog){priorHalos=fog.halos;ownedHalos=(DistrictFog19V05.Halo[])priorHalos.Clone();fog.halos=ownedHalos;}
            bound=true;clock.NightChanged+=Apply;Apply(clock.IsNight);
        }
        void Apply(bool night)
        {
            NightApplied=night;
            foreach(var lamp in lamps)if(lamp)lamp.enabled=night;
            foreach(var pair in clones)
            {
                if(pair.Key.HasProperty("_EmissionColor"))pair.Value.SetColor("_EmissionColor",night?pair.Key.GetColor("_EmissionColor"):Color.black);
                if(pair.Key.HasProperty("_BaseColor"))
                {var c=pair.Key.GetColor("_BaseColor");var dim=c*.22f;dim.a=c.a;pair.Value.SetColor("_BaseColor",night?c:dim);}
            }
            if(ownedHalos!=null)for(int i=0;i<ownedHalos.Length;i++)
            {
                // Only stationary, unowned halo cues. Headlight halos retain their gameplay light reference.
                if(priorHalos[i].light)continue;
                var halo=priorHalos[i];if(!night)halo.colour.a=0;ownedHalos[i]=halo;
            }
        }
        void Release()
        {
            if(!bound)return;
            if(clock)clock.NightChanged-=Apply;
            foreach(var pair in originals)if(pair.Key)pair.Key.sharedMaterials=pair.Value;
            for(int i=0;i<lamps.Length;i++)if(lamps[i])lamps[i].enabled=priorLights[i];
            if(fog && ReferenceEquals(fog.halos,ownedHalos))fog.halos=priorHalos;
            foreach(var clone in clones.Values)if(clone){if(Application.isPlaying)Destroy(clone);else DestroyImmediate(clone);}
            originals.Clear();clones.Clear();priorLights=null;priorHalos=null;ownedHalos=null;bound=false;
        }
        public bool CheckApplied()
        {
            foreach(var lamp in lamps)if(lamp && lamp.enabled!=NightApplied)return false;
            foreach(var pair in clones)if(pair.Key.HasProperty("_EmissionColor"))
            {var expected=NightApplied?pair.Key.GetColor("_EmissionColor"):Color.black;if(pair.Value.GetColor("_EmissionColor")!=expected)return false;}
            if(ownedHalos!=null)for(int i=0;i<ownedHalos.Length;i++)if(!priorHalos[i].light && !NightApplied && ownedHalos[i].colour.a!=0)return false;
            return bound && clones.Count>0;
        }
    }
}
