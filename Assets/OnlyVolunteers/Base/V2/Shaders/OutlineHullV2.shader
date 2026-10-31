// V2 base shop hover outline (Fedya 31.10, plan P1): an inverted hull drawn only on the hovered display item.
// The mesh (a smoothed-normal copy of the item, ShopDisplayItemV2.SmoothNormals) is pushed out along its normals by
// _Width metres and drawn with front faces culled, so only a rim shows around the item. Flat unlit colour from the
// renderer's property block (_OutlineColor); two materials: a solid thin line (opaque) and a faint wider halo
// (alpha blended, no depth write). No screen-space pass, no HDR (nothing for bloom to catch), no noise.
Shader "OnlyVolunteers/BaseV2/OutlineHullV2"
{
    Properties
    {
        _OutlineColor ("Colour", Color) = (1, 0.74, 0.25, 1)
        _Width ("Width (m)", Float) = 0.008
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 0
        [Toggle] _ZWrite ("Z Write", Float) = 1
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry+20" }
        Pass
        {
            Name "OutlineHull"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            ZTest LEqual
            ZWrite [_ZWrite]
            Blend [_SrcBlend] [_DstBlend]

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _OutlineColor;
                float _Width;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes i)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 n = normalize(TransformObjectToWorldNormal(i.normalOS));
                float3 w = TransformObjectToWorld(i.positionOS.xyz) + n * _Width;
                o.positionCS = TransformWorldToHClip(w);
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                return _OutlineColor;
            }
            ENDHLSL
        }
    }
    FallBack Off
}
