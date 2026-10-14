#ifndef OV_AERIAL_19_V01_INCLUDED
#define OV_AERIAL_19_V01_INCLUDED
// Shared by the opaque depth overlay and every transparent v19 receiver.
// Persistent height texture plus numeric globals are scoped to a camera, restored at endCameraRendering.
TEXTURE2D(_G18AerialGround); SAMPLER(sampler_G18AerialGround);
float4 _G18AerialHorizon,_G18AerialClear,_G18AerialDense,_G18AerialHeight,_G18AerialWorld,_G18AerialState;
float4 _G18AerialEdge;
float G18Ground(float2 p)
{return SAMPLE_TEXTURE2D_LOD(_G18AerialGround,sampler_G18AerialGround,saturate((p-_G18AerialWorld.xy)/_G18AerialWorld.zw),0).r;}
float G18AerialOpacity(float3 world)
{
    if(_G18AerialState.x<.5)return 0;
    float3 delta=world-_WorldSpaceCameraPos;
    float distance=length(delta),clearDistance=max(0,distance-_G18AerialClear.x);
    float averageHeight=(world.y+_WorldSpaceCameraPos.y)*.5;
    float height=lerp(_G18AerialClear.z,_G18AerialClear.w,smoothstep(_G18AerialHeight.x,_G18AerialHeight.y,averageHeight));
    float optical=_G18AerialClear.y*clearDistance*clearDistance*height;
    float roughDistance=max(0,distance-_G18AerialDense.z);
    optical+=_G18AerialDense.x*roughDistance*roughDistance+_G18AerialDense.y*distance*distance;
    if(_G18AerialDense.w>.000001)
    {
        float span=min(distance,_G18AerialHeight.w),integral=0;
        float3 ray=delta/max(.001,distance);
        [unroll]for(int k=0;k<8;k++)
        {
            float3 p=_WorldSpaceCameraPos+ray*(span*(k+.5)/8);
            float h=max(0,p.y-G18Ground(p.xz));
            float bank=.86+.14*sin(p.x*.11+p.z*.078+_G18AerialState.y*.045);
            integral+=exp(-h/_G18AerialHeight.z)*bank*(1-smoothstep(4,7,h));
        }
        optical+=_G18AerialDense.w*integral*span/8;
    }
    // The outer 100 m skirt lies beyond all playable districts. It converges fully at the
    // finite terrain boundary, including transparent sea beyond it. Nearby play remains crisp.
    float2 edgeDistances=min(world.xz-_G18AerialWorld.xy,_G18AerialWorld.xy+_G18AerialWorld.zw-world.xz);
    float edge=(1-smoothstep(0,max(1,_G18AerialEdge.x),min(edgeDistances.x,edgeDistances.y)))*smoothstep(_G18AerialEdge.y,_G18AerialEdge.z,distance);
    return saturate(1-exp(-optical)*(1-edge));
}
half3 G18AerialColour(half3 colour,float3 world)
{return lerp(colour,_G18AerialHorizon.rgb,G18AerialOpacity(world));}
#endif
