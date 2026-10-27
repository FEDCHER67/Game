using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Optional v19 camera-scoped aerial extension. Weather (or G22) remains the single sky/light owner.
    [ExecuteAlways]
    public sealed class DistrictAerial19V01 : MonoBehaviour
    {
        public float clearStart=35, clearHalf=175, portHalf=100, hazyHalf=150;
        public float outsideHalf=420;   // Vadim 23.10: far haze also between districts (hills), so the whole map is never visible at once
        public float lowHeightMultiplier=1.12f, highHeightMultiplier=.85f;
        public Vector2 heightRange=new Vector2(0,24);
        public float outerEdgeBlend=100;
        public Color LastHorizon {get;private set;}
        public Vector4 LastClear {get;private set;}
        static readonly string[] Names={"_G18AerialHorizon","_G18AerialClear","_G18AerialDense","_G18AerialHeight","_G18AerialWorld","_G18AerialState","_G18AerialEdge"};
        struct Saved {public Camera camera;public Vector4[] vectors;public Texture ground;}
        readonly Stack<Saved> saved=new();
        void OnEnable()=>RenderPipelineManager.endCameraRendering+=EndCamera;
        void OnDisable()
        {
            RenderPipelineManager.endCameraRendering-=EndCamera;
            while(saved.Count>0)Restore(saved.Pop());
        }
        public float HalfDistance(string id)=>id=="industrial"?portHalf:(id=="transition"||id=="tramduro"?hazyHalf:clearHalf);
        // Horizon is supplied by the active weather owner. G22 sets RenderSettings.fogColor=state.horizon first.
        public void ConfigureCamera(Camera camera,DistrictAtmosphere19.District[] districts,float[] weights,DistrictFog19V05 fog,Color horizon)
        {
            var previous=new Saved{camera=camera,vectors=new Vector4[Names.Length],ground=Shader.GetGlobalTexture("_G18AerialGround")};
            for(int i=0;i<Names.Length;i++)previous.vectors[i]=Shader.GetGlobalVector(Names[i]);
            saved.Push(previous);
            float rough=0,forest=0,coefficient=0,total=0;
            for(int i=0;i<districts.Length;i++)
            {
                string id=districts[i].id;float w=weights[i];total+=w;
                if(id=="residential")rough+=w;
                else if(id=="forest")forest+=w;
                else coefficient+=w*Mathf.Log(2)/Mathf.Pow(Mathf.Max(1,HalfDistance(id)-clearStart),2);
            }
            coefficient+=Mathf.Max(0,1-total)*Mathf.Log(2)/Mathf.Pow(Mathf.Max(1,outsideHalf-clearStart),2);
            LastHorizon=horizon;LastClear=new Vector4(clearStart,coefficient,lowHeightMultiplier,highHeightMultiplier);
            Shader.SetGlobalVector(Names[0],horizon.linear);
            Shader.SetGlobalVector(Names[1],LastClear);
            Shader.SetGlobalVector(Names[2],new Vector4(rough*fog.roughDensity*fog.roughDensity,forest*fog.forestDensity*fog.forestDensity,fog.roughHazeStart,fog.groundExtinction*(rough*fog.roughGroundWeight+forest*.72f)));
            Shader.SetGlobalVector(Names[3],new Vector4(heightRange.x,heightRange.y,2.3f,95));
            Shader.SetGlobalVector(Names[4],fog.terrainWorld);
            Shader.SetGlobalVector(Names[5],new Vector4(1,fog.reviewTime>=0?fog.reviewTime:Time.time,rough,forest));
            Shader.SetGlobalVector(Names[6],new Vector4(outerEdgeBlend,40,100,0));
            Shader.SetGlobalTexture("_G18AerialGround",fog.groundHeights);
            RenderSettings.fog=false;
        }
        void EndCamera(ScriptableRenderContext context,Camera camera)
        {if(saved.Count>0&&saved.Peek().camera==camera)Restore(saved.Pop());}
        static void Restore(Saved state)
        {
            for(int i=0;i<Names.Length;i++)Shader.SetGlobalVector(Names[i],state.vectors[i]);
            Shader.SetGlobalTexture("_G18AerialGround",state.ground);
        }
    }
}
