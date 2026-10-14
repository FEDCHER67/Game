Shader "OnlyVolunteers/Sky22V03/Painted Sky v03"
{
    Properties
    {
        _Zenith("Zenith",Color)=(.24,.60,.79,1)
        _Horizon("Horizon",Color)=(.74,.88,.89,1)
        _CloudTop("Cloud light",Color)=(1,.98,.91,1)
        _CloudBase("Cloud shade",Color)=(.52,.64,.73,1)
        _SunColour("Sun",Color)=(1,.9,.7,1)
        _MoonColour("Moon",Color)=(.51,.68,1,1)
        _SunDirection("Sun direction",Vector)=(0,1,0,0)
        _MoonDirection("Moon direction",Vector)=(0,-1,0,0)
        _Cover("Cover",Range(0,1))=.38
        _Gloom("Gloom",Range(0,1))=0
        _Stars("Stars",Range(0,1))=0
        _Golden("Golden hour",Range(0,1))=0
        _Daylight("Daylight",Range(0,1))=1
        _CloudTime("Wind time",Float)=0
        _CloudScale("Cloud scale",Float)=1
        _Steps("Cloud steps",Float)=64
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct A {float4 positionOS:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID};
            struct V {float4 positionCS:SV_POSITION;float3 direction:TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO};
            CBUFFER_START(UnityPerMaterial)
            float4 _Zenith,_Horizon,_CloudTop,_CloudBase,_SunColour,_MoonColour,_SunDirection,_MoonDirection;
            float _Cover,_Gloom,_Stars,_Golden,_Daylight,_CloudTime,_CloudScale,_Steps;
            CBUFFER_END
            V vert(A i) { V o;UNITY_SETUP_INSTANCE_ID(i);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.positionCS=TransformObjectToHClip(i.positionOS.xyz);o.direction=i.positionOS.xyz;return o; }
            float hash31(float3 p) {p=frac(p*.1031);p+=dot(p,p.yzx+33.33);return frac((p.x+p.y)*p.z);}
            float noise3(float3 p)
            {
                float3 a=floor(p),f=frac(p);f=f*f*(3-2*f);
                return lerp(lerp(lerp(hash31(a),hash31(a+float3(1,0,0)),f.x),lerp(hash31(a+float3(0,1,0)),hash31(a+float3(1,1,0)),f.x),f.y),
                    lerp(lerp(hash31(a+float3(0,0,1)),hash31(a+float3(1,0,1)),f.x),lerp(hash31(a+float3(0,1,1)),hash31(a+1),f.x),f.y),f.z);
            }
            float density(float3 p)
            {
                float height=p.y;
                p.xz=p.xz*_CloudScale+float2(_CloudTime*.028,_CloudTime*.012);
                float n=noise3(p*1.35)*.72+noise3(p*3.2+13.1)*.23+noise3(p*6.4+31.4)*.05;
                float cap=smoothstep(1,1.18,height)*(1-smoothstep(1.48,2.18,height));
                float threshold=lerp(.86,.25,saturate(_Cover));
                return saturate((n-threshold)*5.0)*cap;
            }
            float stars(float3 d,float scale)
            {
                // 3-D directional cells avoid a longitude seam and polar UV stretching.
                float3 p=d*scale,a=floor(p),f=frac(p)-.5;
                float h=hash31(a);float r=length(f);
                float width=max(length(fwidth(p)),.015);
                float star=1-smoothstep(.025,.025+width,r);
                return star*step(.975,h)*(.45+hash31(a+8)*1.8);
            }
            float4 frag(V i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d=normalize(i.direction),sun=normalize(_SunDirection.xyz),moon=normalize(_MoonDirection.xyz);
                float elevation=saturate(d.y);
                float horizonMask=smoothstep(.035,.12,d.y);
                float3 sky=lerp(_Horizon.rgb,_Zenith.rgb,pow(smoothstep(.035,1,elevation),.55));
                float towardsSun=saturate(dot(d,sun));
                sky+=_SunColour.rgb*pow(towardsSun,7)*exp(-abs(d.y)*5)*_Golden*.22*(1-_Gloom*.75)*horizonMask;
                float sunDisc=1-smoothstep(.012,.016,length(d-sun));
                sky+=_SunColour.rgb*(sunDisc*2.1+pow(towardsSun,180)*.3+pow(towardsSun,12)*.04)*_Daylight*horizonMask;
                sky+=(stars(d,165)+stars(d,310)*.5)*_Stars*smoothstep(0,.18,d.y)*float3(.72,.83,1)*horizonMask;
                float md=length(d-moon);
                float moonDisc=1-smoothstep(.025,.028,md);
                float crater=.78+.22*noise3(d*190);
                sky+=_MoonColour.rgb*(moonDisc*crater*1.65+exp(-md*24)*.045)*_Stars*horizonMask;
                float horizonFade=smoothstep(.09,.23,d.y);
                if(horizonFade>0 && _Cover>.001)
                {
                    float dy=max(d.y,.055),entry=1/dy,exit=min(2.18/dy,35.0);
                    int count=(int)clamp(_Steps,24,80);
                    float stepSize=(exit-entry)/count;
                    float transmittance=1;float3 cloud=0;
                    float jitter=.25+.5*hash31(float3(i.positionCS.xy,17.3));
                    float3 lightDir=lerp(moon,sun,smoothstep(.1,.7,_Daylight));
                    lightDir.y=max(lightDir.y,.22);lightDir=normalize(lightDir);
                    [loop] for(int k=0;k<count;k++)
                    {
                        float3 p=d*(entry+(k+jitter)*stepSize);
                        float den=density(p);
                        if(den>.002)
                        {
                            float occlusion=density(p+lightDir*.20)*.65+density(p+lightDir*.52)*.35;
                            float lighting=exp(-occlusion*2.2);
                            float top=smoothstep(1.15,1.95,p.y);
                            float shade=saturate(.34+lighting*.62+top*.20);
                            shade=smoothstep(0,1,shade);
                            float3 colour=lerp(_CloudBase.rgb,_CloudTop.rgb,shade);
                            colour+=_SunColour.rgb*pow(towardsSun,5)*lighting*.18*_Golden*(1-_Gloom);
                            colour*=lerp(1,.62,smoothstep(.7,1,_Cover));
                            float alpha=1-exp(-den*stepSize*11);
                            cloud+=colour*alpha*transmittance;
                            transmittance*=1-alpha;
                            if(transmittance<.012)break;
                        }
                    }
                    float3 cloudSky=cloud+sky*transmittance;
                    // Aerial perspective merges distant cloud banks into the atmospheric horizon.
                    cloudSky=lerp(cloudSky,_Horizon.rgb,exp(-max(d.y,0)*22)*.45);
                    sky=lerp(sky,cloudSky,horizonFade);
                }
                return float4(max(sky,0),1);
            }
            ENDHLSL
        }
    }
}
