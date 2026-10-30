// VanOnly (Vadim 30.10, FPS): the skybox as a lookup of six faces that VanOnlySkyCache rendered once from the G22 painted sky
// (the raymarched clouds cost 13-30 ms of GPU per frame at 4K; this lookup a fraction of a millisecond).
Shader "VadimLocal/VanOnly Sky Cached"
{
    Properties
    {
        _FlipV("Flip faces vertically", Float) = 0
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
            struct A { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 positionCS : SV_POSITION; float3 direction : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            TEXTURE2D_ARRAY(_Faces); SAMPLER(sampler_Faces);
            float4x4 _FaceVP[6];
            CBUFFER_START(UnityPerMaterial)
            float _FlipV;
            CBUFFER_END
            V vert(A i)
            {
                V o; UNITY_SETUP_INSTANCE_ID(i); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.direction = i.positionOS.xyz; return o;
            }
            float4 frag(V i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d = normalize(i.direction), a = abs(d);
                // the face whose axis the direction is closest to: +X -X +Y -Y +Z -Z (VanOnlySkyCache.Dirs)
                int face = a.x >= a.y && a.x >= a.z ? (d.x >= 0 ? 0 : 1) : (a.y >= a.z ? (d.y >= 0 ? 2 : 3) : (d.z >= 0 ? 4 : 5));
                float4 c = mul(_FaceVP[face], float4(d, 1));
                float2 uv = c.xy / c.w * 0.5 + 0.5;
                if (_FlipV > 0.5) uv.y = 1 - uv.y;
                return float4(SAMPLE_TEXTURE2D_ARRAY_LOD(_Faces, sampler_Faces, uv, face, 0).rgb, 1);
            }
            ENDHLSL
        }
    }
}
