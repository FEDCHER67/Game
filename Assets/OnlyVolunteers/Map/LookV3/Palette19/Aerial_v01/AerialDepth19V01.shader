Shader "OnlyVolunteers/StyleV3/AerialDepth19V01"
{
    SubShader
    {
        Tags {"RenderPipeline"="UniversalPipeline"}
        Pass
        {
            Name "AerialDepthOverlay"
            ZWrite Off ZTest Always Cull Off Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Aerial19V01.hlsl"
            half4 Frag(Varyings i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float raw=SampleSceneDepth(i.texcoord);
                #if UNITY_REVERSED_Z
                if(raw<=.0000001)return 0;
                #else
                if(raw>=.9999999)return 0;
                raw=lerp(UNITY_NEAR_CLIP_VALUE,1,raw);
                #endif
                float3 world=ComputeWorldSpacePosition(i.texcoord,raw,UNITY_MATRIX_I_VP);
                return half4(_G18AerialHorizon.rgb,G18AerialOpacity(world));
            }
            ENDHLSL
        }
    }
}
