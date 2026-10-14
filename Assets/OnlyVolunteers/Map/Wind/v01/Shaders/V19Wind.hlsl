#ifndef ONLY_VOLUNTEERS_SHARED_WIND_V01
#define ONLY_VOLUNTEERS_SHARED_WIND_V01
// Geometry-independent world-space field. Ordinary foliage and indirect grass call this same code.
float4 _V19WindDirectionTime; // direction XZ, seconds, enabled
float4 _V19WindParameters; // base radians, gust radians, band wavelength metres, speed m/s
float4 _V19WindDetail; // turbulence metres, max radians, district field enabled, reserved
float4 _V19WindRectangle; // world minimum XZ, inverse size XZ
TEXTURE2D(_V19WindField); SAMPLER(sampler_V19WindField);

float3 V19WindRotate(float3 v,float3 axis,float s,float c)
{ return v*c+cross(axis,v)*s+axis*dot(axis,v)*(1-c); }

// response: 1 for grass, ~.1 for trees. flexibleHeight is metres, not a baked mesh attribute.
// Optional vertex mask defaults to 1. No UV layout, bone, vertex colour or model ID is required.
void V19WindDeform(float3 pivotWS,float3 upWS,float response,float flexibleHeight,float vertexMask,
                   inout float3 positionWS,inout float3 normalWS,out float flash)
{
    float3 relative=positionWS-pivotWS;
    float height=max(0,dot(relative,upWS));
    float radial=length(relative-upWS*dot(relative,upWS));
    float profile=smoothstep(0,max(.05,flexibleHeight),height)*saturate(vertexMask);
    float2 d=_V19WindDirectionTime.xy;
    float3 direction=normalize(float3(d.x,0,d.y)+float3(.00001,0,0));
    direction=direction-upWS*dot(direction,upWS);
    if(dot(direction,direction)<.00001)direction=cross(upWS,abs(upWS.z)<.9?float3(0,0,1):float3(1,0,0));
    direction=normalize(direction);
    float3 axis=normalize(cross(upWS,direction));
    float t=_V19WindDirectionTime.z;
    float phase=6.2831853*(dot(pivotWS.xz,d)-_V19WindParameters.w*t)/max(4,_V19WindParameters.z);
    float gust=pow(saturate(sin(phase)*.5+.5),3);
    float strength=1;
    if(_V19WindDetail.z>.5)strength=SAMPLE_TEXTURE2D_LOD(_V19WindField,sampler_V19WindField,(pivotWS.xz-_V19WindRectangle.xy)*_V19WindRectangle.zw,0).r;
    float angle=min(_V19WindDetail.y,(_V19WindParameters.x+gust*_V19WindParameters.y)*max(0,response)*strength)*profile*_V19WindDirectionTime.w;
    float s,c;sincos(angle,s,c);
    positionWS=pivotWS+V19WindRotate(relative,axis,s,c);
    normalWS=V19WindRotate(normalWS,axis,s,c);
    float flutter=sin(dot(positionWS,float3(.73,1.1,.49))*3.2-t*8.5);
    flutter*=_V19WindDetail.x*(radial/(radial+.35))*profile*min(1,response*3)*_V19WindDirectionTime.w;
    positionWS+=axis*flutter;
    flash=saturate(angle/.785398)*profile;
}
#endif
