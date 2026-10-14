Shader "OnlyVolunteers/StyleV3/MistAerial19V01"
{
    Properties { _Glow("Glow",Float)=0 _DepthFade("Intersection softness",Float)=2 }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            ZWrite Off Cull Off Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vertex
            #pragma fragment Fragment
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Aerial19V01.hlsl"
            struct Attributes {float4 vertex:POSITION;float4 colour:COLOR;float2 uv:TEXCOORD0;};
            struct Varyings {float4 pos:SV_POSITION;float4 colour:COLOR;float2 uv:TEXCOORD0;float eye:TEXCOORD1;float3 world:TEXCOORD2;};
            float _MistTime,_Glow,_DepthFade;
            Varyings Vertex(Attributes v)
            {Varyings o;float3 w=TransformObjectToWorld(v.vertex.xyz);o.pos=TransformWorldToHClip(w);o.eye=-TransformWorldToView(w).z;o.world=w;o.uv=v.uv;o.colour=v.colour;return o;}
            half4 Fragment(Varyings i):SV_Target
            {
                float2 uv=i.uv*2-1;float radius=dot(uv,uv);
                float edge=pow(saturate(1-radius),3);
                float noise=.67+.20*sin(uv.x*8+uv.y*5+_MistTime*.08)+.13*sin(uv.x*19-uv.y*13-_MistTime*.06);
                float raw=SampleSceneDepth(i.pos.xy/_ScaledScreenParams.xy);
                float scene=LinearEyeDepth(raw,_ZBufferParams);
                float fade=saturate((scene-i.eye)/max(.1,_DepthFade))*saturate((i.eye-.25)/.8);
                float alpha=edge*lerp(noise,1,_Glow)*fade*i.colour.a;
                return half4(G18AerialColour(i.colour.rgb*(1+_Glow*.8),i.world),alpha);
            }
            ENDHLSL
        }
    }
}
