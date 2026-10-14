Shader "OnlyVolunteers/StyleV3/DistrictFog19V04"
{
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "DepthHeightMist_PC"
            ZWrite Off ZTest Always Cull Off Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            TEXTURE2D(_GroundHeights); SAMPLER(sampler_GroundHeights);
            float4 _FogDensity,_TerrainWorld,_Baseline;
            float4 _MilkColour,_BaselineColour;
            float _MistTime,_ForwardScatter;
            float4 _DistrictDistance;
            float Height(float2 p)
            {return SAMPLE_TEXTURE2D_LOD(_GroundHeights,sampler_GroundHeights,saturate((p-_TerrainWorld.xy)/_TerrainWorld.zw),0).r;}
            half4 Frag(Varyings input):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                if(_FogDensity.z<.00001) return 0;
                float raw=SampleSceneDepth(input.texcoord);
                #if UNITY_REVERSED_Z
                bool sky=raw<.00001;
                #else
                bool sky=raw>.99999;
                raw=lerp(UNITY_NEAR_CLIP_VALUE,1,raw);
                #endif
                float3 world=ComputeWorldSpacePosition(input.texcoord,raw,UNITY_MATRIX_I_VP);
                float3 ray=world-_WorldSpaceCameraPos;
                float distance=length(ray);ray/=max(.001,distance);
                float span=min(distance,95),heightIntegral=0;
                [unroll] for(int i=0;i<8;i++)
                {
                    float3 p=_WorldSpaceCameraPos+ray*(span*(i+.5)/8);
                    float h=max(0,p.y-Height(p.xz));
                    float bank=.86+.14*sin(p.x*.11+p.z*.078+_MistTime*.045);
                    heightIntegral+=exp(-h/_FogDensity.w)*bank*(1-smoothstep(4,7,h));
                }
                heightIntegral*=span/8;
                // Exp-squared extinction in distance, plus an integrated ground layer (0-6m).
                // The horizon must converge to the same mist colour as distant geometry;
                // otherwise fully fogged trees become pale cutouts against an unfogged dark sky.
                float skyOptical=_DistrictDistance.w*(1-smoothstep(.08,.60,max(0,ray.y)));
                // The Forest keeps the approved v03 extinction. Rough haze starts beyond walking range.
                float roughDistance=max(0,distance-_DistrictDistance.z);
                float distanceOptical=_DistrictDistance.x*roughDistance*roughDistance+_DistrictDistance.y*distance*distance;
                float optical=(sky?skyOptical:distanceOptical)+_FogDensity.y*heightIntegral;
                float dense=1-exp(-optical);
                float baseline=sky?0:saturate((distance-_Baseline.x)/max(1,_Baseline.y-_Baseline.x))*(1-_FogDensity.z);
                float alpha=1-(1-baseline)*(1-dense);
                float3 colour=lerp(_BaselineColour.rgb,_MilkColour.rgb,saturate(_FogDensity.z*1.7));
                // Low diffuse forward scattering; no hard shafts under the approved overcast sky.
                colour+=_ForwardScatter*pow(saturate(dot(ray,float3(.25,.35,.90))),4);
                return half4(colour,alpha);
            }
            ENDHLSL
        }
    }
}
