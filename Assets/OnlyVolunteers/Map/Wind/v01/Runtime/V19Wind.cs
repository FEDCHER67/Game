using System;
using System.Collections.Generic;
using UnityEngine;
using OnlyVolunteers.Map.Look.V3;

namespace OnlyVolunteers.Map.Wind
{
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class V19Wind : MonoBehaviour
    {
        public enum Preset { Calm, Breezy, Stormy }
        [Tooltip("One shared direction in world X/Z, independent of model rotation.")]
        public Vector2 direction = new(.84f,.54f);
        [Tooltip("Rest lean, in degrees, before material response and district strength.")]
        [Range(0,20)] public float baseDegrees=8;
        [Tooltip("Additional lean at the crest of a travelling gust.")]
        [Range(0,45)] public float gustDegrees=32;
        [Min(4)] public float gustSize=40;
        [Min(0)] public float gustSpeed=8;
        [Range(0,.1f)] public float turbulence=.018f;
        [Range(0,60)] public float maximumDegrees=45;
        [Tooltip("Optional v19 district source. Without it the material works with uniform wind.")]
        public DistrictWeather19V05 districts;
        public Vector4 fieldRectangle=new(-120,-120,1728,1024);
        public float openStrength=1.12f,hamletStrength=.95f,forestStrength=.55f,roughStrength=1.2f,beachStrength=1.15f;
        [NonSerialized] public float reviewTime=-1;
        Texture2D field;
        bool fieldDirty;
        float nextBoundsScan;
        readonly Dictionary<Renderer,Bounds> originalBounds=new();
        readonly List<Material> materials=new();
        readonly List<Renderer> deadRenderers=new();
        static V19Wind owner;
        static readonly int Direction=Shader.PropertyToID("_V19WindDirectionTime"),Parameters=Shader.PropertyToID("_V19WindParameters"),Detail=Shader.PropertyToID("_V19WindDetail"),Field=Shader.PropertyToID("_V19WindField"),Rectangle=Shader.PropertyToID("_V19WindRectangle");
        public bool IsOwner=>owner==this;

        void OnEnable()
        {
            if(owner&&owner!=this){Debug.LogError("Only one V19Wind may own the shared shader wind.",this);enabled=false;return;}
            owner=this;RebuildDistrictField();Publish();
        }
        void Update()
        {
            if(!IsOwner)return;
            if(fieldDirty){fieldDirty=false;RebuildDistrictField();}
            Publish();
            if(Time.realtimeSinceStartup>=nextBoundsScan){nextBoundsScan=Time.realtimeSinceStartup+5;RefreshModelBounds();}
        }
        void OnValidate(){fieldDirty=true;}
        void OnDisable()
        {
            if(IsOwner){Shader.SetGlobalVector(Direction,Vector4.zero);Shader.SetGlobalTexture(Field,Texture2D.whiteTexture);owner=null;}
            ReleaseField();
            foreach(var item in originalBounds)if(item.Key)item.Key.localBounds=item.Value;
            originalBounds.Clear();
        }
        // Shader displacement cannot update CPU culling bounds. One scene owner pads ordinary
        // renderers automatically; no mesh rewrite, per-model bake or helper component is needed.
        public void RefreshModelBounds()
        {
            deadRenderers.Clear();
            foreach(var item in originalBounds)if(!item.Key)deadRenderers.Add(item.Key);
            foreach(var item in deadRenderers)originalBounds.Remove(item);
            foreach(var renderer in FindObjectsByType<Renderer>())
            {
                renderer.GetSharedMaterials(materials);bool usesWind=false;
                if(!originalBounds.TryGetValue(renderer,out var bounds))bounds=renderer.localBounds;
                float radiusWorld=0;
                foreach(var mat in materials)if(mat&&mat.shader&&mat.shader.name=="OnlyVolunteers/Wind/v01/GenericFoliage")
                {
                    usesWind=true;Vector3 pivot=mat.GetVector("_WindPivotOS");
                    var worldPivot=renderer.localToWorldMatrix.MultiplyPoint3x4(pivot);
                    // World-space wind must also be safe with nonuniform import/parent scales.
                    for(int corner=0;corner<8;corner++)
                    {
                        var offset=Vector3.Scale(bounds.extents,new Vector3((corner&1)==0?-1:1,(corner&2)==0?-1:1,(corner&4)==0?-1:1));
                        radiusWorld=Mathf.Max(radiusWorld,Vector3.Distance(worldPivot,renderer.localToWorldMatrix.MultiplyPoint3x4(bounds.center+offset)));
                    }
                }
                if(!usesWind){if(originalBounds.TryGetValue(renderer,out var previous)){renderer.localBounds=previous;originalBounds.Remove(renderer);}continue;}
                if(!originalBounds.ContainsKey(renderer))originalBounds.Add(renderer,bounds);
                // 2*sin(45 degrees/2) bounds any capped rotation; .1 m covers maximum flutter.
                float displacement=radiusWorld*.77f+.1f;
                var inverse=renderer.worldToLocalMatrix;
                var padding=new Vector3(((Vector3)inverse.GetRow(0)).magnitude,((Vector3)inverse.GetRow(1)).magnitude,((Vector3)inverse.GetRow(2)).magnitude)*displacement;
                var padded=bounds;padded.Expand(padding*2);renderer.localBounds=padded;
            }
        }
        void ReleaseField(){if(!field)return;if(Application.isPlaying)Destroy(field);else DestroyImmediate(field);field=null;}
        public void ApplyPreset(Preset preset)
        {
            baseDegrees=preset==Preset.Calm?4:preset==Preset.Stormy?12:8;
            gustDegrees=preset==Preset.Calm?12:preset==Preset.Stormy?36:32;
            gustSize=preset==Preset.Calm?55:preset==Preset.Stormy?30:40;
            gustSpeed=preset==Preset.Calm?3:preset==Preset.Stormy?13:8;
            turbulence=preset==Preset.Calm?.007f:preset==Preset.Stormy?.035f:.018f;
            Publish();
        }
        [ContextMenu("Preset/Calm")] void Calm()=>ApplyPreset(Preset.Calm);
        [ContextMenu("Preset/Breezy")] void Breezy()=>ApplyPreset(Preset.Breezy);
        [ContextMenu("Preset/Stormy")] void Stormy()=>ApplyPreset(Preset.Stormy);
        public void Publish()
        {
            if(!IsOwner)return;
            var d=direction.sqrMagnitude>.0001f?direction.normalized:Vector2.right;
            Shader.SetGlobalVector(Direction,new Vector4(d.x,d.y,reviewTime>=0?reviewTime:Time.time,1));
            Shader.SetGlobalVector(Parameters,new Vector4(baseDegrees*Mathf.Deg2Rad,gustDegrees*Mathf.Deg2Rad,Mathf.Max(4,gustSize),Mathf.Max(0,gustSpeed)));
            Shader.SetGlobalVector(Detail,new Vector4(turbulence,Mathf.Min(45,maximumDegrees)*Mathf.Deg2Rad,field?1:0,0));
            Shader.SetGlobalVector(Rectangle,new Vector4(fieldRectangle.x,fieldRectangle.y,1/Mathf.Max(1,fieldRectangle.z),1/Mathf.Max(1,fieldRectangle.w)));
            Shader.SetGlobalTexture(Field,field?field:Texture2D.whiteTexture);
        }
        public void RebuildDistrictField()
        {
            ReleaseField();if(!districts||districts.districts==null||districts.districts.Length==0)return;
            int n=districts.districts.Length;var bounds=new Vector4[n];var weights=new float[n];var strengths=new float[n];
            for(int i=0;i<n;i++)
            {
                var d=districts.districts[i];bounds[i]=d.bounds;
                strengths[i]=d.id=="forest"?forestStrength:d.id=="village"?hamletStrength:d.id=="residential"?roughStrength:d.id=="beach"?beachStrength:d.id=="old_town"?.75f:d.id=="elite"?.85f:1;
            }
            const int size=256;var pixels=new float[size*size];
            for(int z=0;z<size;z++)for(int x=0;x<size;x++)
            {
                var p=new Vector2(fieldRectangle.x+(x+.5f)/size*fieldRectangle.z,fieldRectangle.y+(z+.5f)/size*fieldRectangle.w);
                DistrictBlend19.Weights(bounds,p,districts.blendMetres,weights);
                float strength=0,nearest=float.PositiveInfinity;
                for(int i=0;i<n;i++){strength+=strengths[i]*weights[i];var b=bounds[i];float dx=Mathf.Max(b.x-p.x,0,p.x-b.z),dz=Mathf.Max(b.y-p.y,0,p.y-b.w);nearest=Mathf.Min(nearest,Mathf.Sqrt(dx*dx+dz*dz));}
                strength=Mathf.Lerp(strength,openStrength,Mathf.SmoothStep(0,1,nearest/60));pixels[z*size+x]=strength;
            }
            field=new Texture2D(size,size,TextureFormat.RFloat,false,true){name="V19Wind district strengths (runtime)",hideFlags=HideFlags.HideAndDontSave,wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
            field.SetPixelData(pixels,0);field.Apply(false,true);
        }
    }
}
