using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Wind
{
    // Culling only. V19Wind remains the single wind owner. No per-model component or mesh bake.
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class FoliageBounds23 : MonoBehaviour
    {
        readonly Dictionary<Renderer,Bounds> originals=new();
        readonly List<Material> materials=new();
        readonly List<Renderer> remove=new();
        float nextScan;
        void OnEnable(){Refresh();}
        void Update(){if(Time.realtimeSinceStartup>=nextScan){nextScan=Time.realtimeSinceStartup+5;Refresh();}}
        public void Refresh()
        {
            remove.Clear();foreach(var pair in originals)if(!pair.Key)remove.Add(pair.Key);
            foreach(var renderer in remove)originals.Remove(renderer);
            foreach(var renderer in FindObjectsByType<MeshRenderer>())
            {
                renderer.GetSharedMaterials(materials);bool wind=false;float radius=0;
                if(!originals.TryGetValue(renderer,out var bounds))bounds=renderer.localBounds;
                foreach(var mat in materials)if(mat&&mat.shader&&mat.shader.name=="OnlyVolunteers/Wind/v02/GenericFoliage")
                {
                    wind=true;Vector3 pivot=renderer.localToWorldMatrix.MultiplyPoint3x4(mat.GetVector("_WindPivotOS"));
                    for(int i=0;i<8;i++)
                    {
                        var offset=Vector3.Scale(bounds.extents,new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1));
                        radius=Mathf.Max(radius,Vector3.Distance(pivot,renderer.localToWorldMatrix.MultiplyPoint3x4(bounds.center+offset)));
                    }
                }
                if(!wind){if(originals.TryGetValue(renderer,out var old)){renderer.localBounds=old;originals.Remove(renderer);}continue;}
                if(!originals.ContainsKey(renderer))originals.Add(renderer,bounds);
                float displacement=radius*.77f+.1f;var inv=renderer.worldToLocalMatrix;
                var padding=new Vector3(((Vector3)inv.GetRow(0)).magnitude,((Vector3)inv.GetRow(1)).magnitude,((Vector3)inv.GetRow(2)).magnitude)*displacement;
                bounds.Expand(padding*2);renderer.localBounds=bounds;
            }
        }
        void OnDisable(){foreach(var pair in originals)if(pair.Key)pair.Key.localBounds=pair.Value;originals.Clear();}
    }
}
