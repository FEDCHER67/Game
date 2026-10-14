Shader "OnlyVolunteers/StyleV3/DistrictSkyAerial19V01"
{
    Properties
    {
        _Zenith("Zenith",Color)=(.15,.42,.75,1)
        _Horizon("Horizon",Color)=(.68,.78,.86,1)
        _CloudColour("Cloud colour",Color)=(.95,.97,1,1)
        _CloudCover("Cloud cover",Range(0,1))=.45
        _CloudDensity("Cloud density",Range(0,2))=1
        _SunDirection("Sun direction",Vector)=(0,1,0,0)
        _SunColour("Sun colour",Color)=(1,.97,.87,1)
        _SunStrength("Sun strength",Float)=1
        _HorizonBand("Clear horizon band",Float)=.035
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct A {float4 vertex:POSITION;};
            struct V {float4 position:SV_POSITION;float3 direction:TEXCOORD0;};
            CBUFFER_START(UnityPerMaterial)
            float4 _Zenith,_Horizon,_CloudColour,_SunDirection,_SunColour;
            float _CloudCover,_CloudDensity,_SunStrength,_HorizonBand;
            CBUFFER_END
            V vert(A i) {V o;o.position=TransformObjectToHClip(i.vertex.xyz);o.direction=i.vertex.xyz;return o;}
            float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p)
            {
                float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
                return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
            }
            float4 frag(V i):SV_Target
            {
                float3 d=normalize(i.direction);
                float3 colour=lerp(_Horizon.rgb,_Zenith.rgb,pow(smoothstep(_HorizonBand,1,d.y),.55));
                float2 p=d.xz/(max(d.y,0)+.24)*2.6;
                float n=noise(p)*.56+noise(p*2.07+9)*.28+noise(p*4.21-3)*.12+noise(p*8.2)*.04;
                float cloud=smoothstep(1-_CloudCover-.12,1-_CloudCover+.13,n)*_CloudDensity;
                cloud=saturate(cloud)*smoothstep(_HorizonBand,_HorizonBand+.15,d.y);
                float3 litCloud=_CloudColour.rgb*lerp(.65,1.12,smoothstep(.25,.82,n));
                colour=lerp(colour,litCloud,cloud);
                float s=saturate(dot(d,normalize(_SunDirection.xyz)));
                colour+=_SunColour.rgb*_SunStrength*(pow(s,6000)*2+pow(s,24)*.13)*(1-cloud)*smoothstep(_HorizonBand,_HorizonBand+.12,d.y);
                return float4(colour,1);
            }
            ENDHLSL
        }
    }
}
