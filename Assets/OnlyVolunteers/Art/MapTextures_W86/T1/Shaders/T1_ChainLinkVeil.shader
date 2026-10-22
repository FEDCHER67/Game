// Map W86 T1 (2026-10-22): chain-link that still reads as a fence at 30-60 m (no MSAA / TAA in the map, so alpha-to-coverage does
// nothing). Near: the wire alpha is sharpened around the cutoff with its screen derivative (crisp, anti-aliased wires). Far: the
// texel footprint (mip level) blends the wires into a soft veil = the mip-averaged coverage x _VeilBoost, so the net stays visible
// as a grey film instead of vanishing (the old alpha-clip FenceNet disappeared at 5-10 m). One alpha-blended pass, no shadows,
// no depth write (thin fences), URP lighting + fog. Wire colour = _BaseColor (texture RGB = wire shading only).
Shader "OnlyVolunteers/W86/T1_ChainLinkVeil"
{
    Properties
    {
        [MainTexture] _BaseMap("Wire mask (RGB shading, A wire)", 2D) = "white" {}
        [MainColor] _BaseColor("Wire colour", Color) = (0.62, 0.64, 0.64, 1)
        _Smoothness("Smoothness", Range(0, 1)) = 0.35
        _Metallic("Metallic", Range(0, 1)) = 0.3
        _Cutoff("Wire alpha cutoff (near)", Range(0, 1)) = 0.5
        _VeilBoost("Far veil: coverage multiplier", Range(0.5, 6)) = 2.4
        _VeilMax("Far veil: max opacity", Range(0, 1)) = 0.55
        _VeilStart("Veil starts at mip level", Range(0, 6)) = 0.6
        _VeilRange("Veil fade (mip levels)", Range(0.1, 6)) = 1.6
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "IgnoreProjector" = "True" }
        LOD 300

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST;
        float4 _BaseMap_TexelSize;
        half4 _BaseColor;
        half _Smoothness;
        half _Metallic;
        half _Cutoff;
        half _VeilBoost;
        half _VeilMax;
        half _VeilStart;
        half _VeilRange;
        CBUFFER_END
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha, One OneMinusSrcAlpha
            ZWrite Off
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ EVALUATE_SH_MIXED EVALUATE_SH_VERTEX
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 texcoord : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float3 normalWS : TEXCOORD2;
                half fogFactor : TEXCOORD3;
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs vp = GetVertexPositionInputs(input.positionOS.xyz);
                VertexNormalInputs vn = GetVertexNormalInputs(input.normalOS);
                o.uv = TRANSFORM_TEX(input.texcoord, _BaseMap);
                o.positionWS = vp.positionWS;
                o.normalWS = vn.normalWS;
                o.fogFactor = ComputeFogFactor(vp.positionCS.z);
                o.positionCS = vp.positionCS;
                return o;
            }

            half4 Frag(Varyings input, bool front : SV_IsFrontFace) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                half4 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                float2 tdx = ddx(input.uv * _BaseMap_TexelSize.zw), tdy = ddy(input.uv * _BaseMap_TexelSize.zw);
                float lod = 0.5 * log2(max(max(dot(tdx, tdx), dot(tdy, tdy)), 1e-8));
                half sharp = saturate((tex.a - _Cutoff) / max(fwidth(tex.a), 1e-3) + 0.5);
                half veil = min(tex.a * _VeilBoost, _VeilMax);
                half t = saturate((lod - _VeilStart) / _VeilRange);
                half alpha = lerp(sharp, max(veil, sharp * (1 - t)), t);
                clip(alpha - 0.004);

                SurfaceData s = (SurfaceData)0;
                s.albedo = _BaseColor.rgb * lerp(tex.rgb, 0.85, t);
                s.alpha = alpha;
                s.metallic = _Metallic;
                s.smoothness = _Smoothness;
                s.occlusion = 1;
                s.normalTS = half3(0, 0, 1);

                InputData d = (InputData)0;
                d.positionWS = input.positionWS;
                d.positionCS = input.positionCS;
                float3 n = normalize(input.normalWS) * (front ? 1 : -1);
                d.normalWS = n;
                d.viewDirectionWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
                #if defined(MAIN_LIGHT_CALCULATE_SHADOWS)
                d.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                #endif
                d.fogCoord = InitializeInputDataFog(float4(input.positionWS, 1.0), input.fogFactor);
                d.bakedGI = SampleSH(n);
                d.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
                half4 c = UniversalFragmentPBR(d, s);
                c.rgb = MixFog(c.rgb, d.fogCoord);
                c.a = alpha;
                return c;
            }
            ENDHLSL
        }
    }
    FallBack Off
}
