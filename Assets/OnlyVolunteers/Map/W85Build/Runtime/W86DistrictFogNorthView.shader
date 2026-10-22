// W86 (lead 22.10, Vadim: from the Rough looking north the steppe framed by the ridges must read): a copy of
// LookV3/Palette19/DistrictFog19V05.shader (unchanged there) with one addition. Surfaces BEYOND the state fence (world z past the
// fence band) and the high ridges near it get a light distance haze instead of the dense Rough mist, so the steppe swells, ridges and
// far mountains stay soft silhouettes at 300 m - 3 km while everything inside the blocks keeps the approved Rough fog. Used by the W86
// map build as the DistrictFog19V05.fogTemplate shader (same properties, set by the same component).
Shader "OnlyVolunteers/W86/DistrictFogNorthView"
{
    Properties
    {
        _W86Mask("North view: z band (x,y), ridge height band (z,w)", Vector) = (880,946,22,34)
        _W86Haze("North view haze: start, end, max alpha", Vector) = (150,2600,0.82,0)
    }
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
            float4 _W86Mask;   // x,y: world z band where the far haze takes over; z,w: ridge height band (world y) north of z x-40
            float4 _W86Haze;   // x start m, y end m, z max alpha of the far haze
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
                // W86 north view: past the fence band (and on the high ridges framing it) a light distance haze replaces the mist
                float maskZ=smoothstep(_W86Mask.x,_W86Mask.y,world.z);
                float maskY=smoothstep(_W86Mask.z,_W86Mask.w,world.y)*smoothstep(_W86Mask.x-40,_W86Mask.y-45,world.z);
                float northMask=sky?0:saturate(max(maskZ,maskY))*step(.5,_W86Haze.y);
                float farHaze=saturate((distance-_W86Haze.x)/max(1,_W86Haze.y-_W86Haze.x))*_W86Haze.z;
                alpha=lerp(alpha,farHaze,northMask);
                float3 colour=lerp(_BaselineColour.rgb,_MilkColour.rgb,saturate(_FogDensity.z*1.7));
                // Low diffuse forward scattering; no hard shafts under the approved overcast sky.
                colour+=_ForwardScatter*pow(saturate(dot(ray,float3(.25,.35,.90))),4);
                return half4(colour,alpha);
            }
            ENDHLSL
        }
    }
}
