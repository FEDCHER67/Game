Shader "OnlyVolunteers/Paint/Body"
{
    Properties { _BaseColor("Base colour",Color)=(.82,.76,.65,1) _PaintMask("Paint",2D)="black" {} _PaintEnabled("Runtime paint enabled",Float)=0 }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="Opaque" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            TEXTURE2D(_PaintMask); SAMPLER(sampler_PaintMask);
            CBUFFER_START(UnityPerMaterial)
            half4 _BaseColor;
            float _PaintEnabled;
            CBUFFER_END
            struct a { float4 positionOS:POSITION; float3 normalOS:NORMAL; float2 uv:TEXCOORD0; };
            struct v { float4 positionCS:SV_POSITION; float3 normalWS:TEXCOORD1; float2 uv:TEXCOORD0; };
            v vert(a i) { v o; o.positionCS=TransformObjectToHClip(i.positionOS.xyz); o.normalWS=TransformObjectToWorldNormal(i.normalOS); o.uv=i.uv; return o; }
            half4 frag(v i):SV_Target
            {
                half4 paint=SAMPLE_TEXTURE2D(_PaintMask,sampler_PaintMask,i.uv)*_PaintEnabled;
                half3 base=paint.rgb+_BaseColor.rgb*(1-paint.a);
                Light light=GetMainLight();
                half diffuse=saturate(dot(normalize(i.normalWS),light.direction));
                return half4(base*(half3(.42,.43,.46)+light.color*diffuse*.65),1);
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
    }
}
