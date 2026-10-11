// Style v3 water (map v16): colour by depth (shallow turquoise -> deep palette blue), depth-based shore foam broken up
// by a noise mask, two ripple normal layers carried by a two-phase flow (UV1 = flow velocity in m/s along world xz for
// rivers and the canal, otherwise a wind drift), a large slow swell, refraction of the opaque scene, caustics on the
// bottom in shallow sunlit water, sun glint and a fresnel sky reflection. Transparent, no depth write; needs the URP
// depth and opaque textures (on in PC_RPAsset and PC_RPAsset_StyleV3).
Shader "OnlyVolunteers/StyleV3/Water"
{
    Properties
    {
        _ShallowColor("Shallow colour", Color) = (0.38, 0.80, 0.80, 1)
        _DeepColor("Deep colour", Color) = (0.13, 0.47, 0.72, 1)
        _DepthRange("Depth to the deep colour (m)", Float) = 3
        _Clarity("Bottom visibility (m of water)", Float) = 1.6
        _BottomTint("Bottom tint", Range(0, 1)) = 0.45
        _FoamColor("Foam colour", Color) = (0.97, 0.99, 1, 1)
        _FoamWidth("Shore foam width (m)", Float) = 0.7
        _FoamStrength("Foam strength", Range(0, 1)) = 0.85
        _FoamNoiseSize("Foam pattern size (m)", Float) = 2.6
        [NoScaleOffset][Normal] _NormalMap("Ripple normal", 2D) = "bump" {}
        _NormalTiling1("Ripple A size (m)", Float) = 7
        _NormalTiling2("Ripple B size (m)", Float) = 2.9
        _SwellTiling("Swell size (m)", Float) = 38
        _NormalStrength("Ripple strength", Range(0, 2)) = 0.6
        _SwellStrength("Swell strength", Range(0, 2)) = 0.35
        _WaveSpeed("Wind drift (m/s)", Float) = 0.3
        _WindDir("Wind direction (x, z)", Vector) = (0.8, 0.6, 0, 0)
        _FlowSpeed("Flow speed scale", Float) = 1
        _Smoothness("Smoothness", Range(0, 1)) = 0.93
        _SpecularStrength("Sun glint", Range(0, 4)) = 1.1
        _FresnelPower("Fresnel power", Float) = 4.5
        _ReflectionStrength("Sky reflection", Range(0, 1)) = 0.5
        _RefractionStrength("Refraction", Range(0, 0.2)) = 0.035
        [NoScaleOffset] _AuxTex("Caustics (R) + foam noise (G)", 2D) = "black" {}
        _CausticsSize("Caustics size (m)", Float) = 3.4
        _CausticsStrength("Caustics strength", Range(0, 3)) = 0.7
        _CausticsDepth("Caustics fade depth (m)", Float) = 1.8
        _EdgeSoftness("Shore edge softness (m)", Float) = 0.06
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent-10" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        LOD 300

        Pass
        {
            Name "ForwardWater"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex WaterVertex
            #pragma fragment WaterFragment
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
            half4 _ShallowColor;
            half4 _DeepColor;
            half4 _FoamColor;
            float4 _WindDir;
            float _DepthRange;
            float _Clarity;
            float _BottomTint;
            float _FoamWidth;
            float _FoamStrength;
            float _FoamNoiseSize;
            float _NormalTiling1;
            float _NormalTiling2;
            float _SwellTiling;
            float _NormalStrength;
            float _SwellStrength;
            float _WaveSpeed;
            float _FlowSpeed;
            float _Smoothness;
            float _SpecularStrength;
            float _FresnelPower;
            float _ReflectionStrength;
            float _RefractionStrength;
            float _CausticsSize;
            float _CausticsStrength;
            float _CausticsDepth;
            float _EdgeSoftness;
            CBUFFER_END

            TEXTURE2D(_NormalMap); SAMPLER(sampler_NormalMap);
            TEXTURE2D(_AuxTex); SAMPLER(sampler_AuxTex);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 flow : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float2 flow : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings WaterVertex(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                VertexPositionInputs p = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = p.positionCS;
                output.positionWS = p.positionWS;
                output.flow = input.flow;
                output.fogFactor = ComputeFogFactor(p.positionCS.z);
                return output;
            }

            half3 Ripple(float2 uv)
            {
                return UnpackNormal(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, uv));
            }

            // Two phases half a cycle apart, each reset while its weight is zero: a flow that varies from place to place
            // never shears the pattern, and a uniform drift looks like a plain scroll.
            half3 FlowRipple(float2 xz, float2 velocity, float size, float t, float2 jump)
            {
                const float cycle = 5.0;
                float c0 = t / cycle, c1 = t / cycle + 0.5;
                float p0 = frac(c0), p1 = frac(c1);
                float w = abs(1.0 - 2.0 * p0);
                float2 uv0 = (xz - velocity * p0 * cycle) / size + jump * floor(c0);
                float2 uv1 = (xz - velocity * p1 * cycle) / size + jump * floor(c1) + 0.5;
                return normalize(lerp(Ripple(uv0), Ripple(uv1), w));
            }

            float EyeDepth(float rawDepth)
            {
                if (unity_OrthoParams.w > 0.5)
                {
                    #if UNITY_REVERSED_Z
                    rawDepth = 1.0 - rawDepth;
                    #endif
                    return lerp(_ProjectionParams.y, _ProjectionParams.z, rawDepth);
                }
                return LinearEyeDepth(rawDepth, _ZBufferParams);
            }

            half4 WaterFragment(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

                float3 posWS = input.positionWS;
                float t = _Time.y;
                float2 wind = normalize(_WindDir.xy + float2(1e-4, 0));
                float2 side = float2(-wind.y, wind.x);
                float2 flow = input.flow * _FlowSpeed;
                float surfEye = -TransformWorldToView(posWS).z;

                // Ripples: two layers carried by the flow (or the wind) plus a slow swell; fade with distance (no shimmer).
                float detail = lerp(1.0, 0.35, saturate(surfEye / 350.0));
                half3 nA = FlowRipple(posWS.xz, flow + wind * _WaveSpeed, _NormalTiling1, t, float2(0.31, 0.17));
                half3 nB = FlowRipple(posWS.xz, flow * 0.85 + (side * 0.55 + wind * 0.6) * _WaveSpeed, _NormalTiling2, t * 1.07, float2(0.13, 0.41));
                half3 nS = Ripple(posWS.xz / _SwellTiling + wind * t * 0.006);
                half3 n = half3(nA.xy * _NormalStrength + nB.xy * _NormalStrength * 0.7, 1.0);
                n.xy = n.xy * detail + nS.xy * _SwellStrength;
                half3 N = normalize(half3(n.x, n.z, n.y));
                half3 V = normalize(_WorldSpaceCameraPos - posWS);

                // Water depth below this pixel: the scene depth along the view ray.
                float2 suv = GetNormalizedScreenSpaceUV(input.positionCS);
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                bool ortho = unity_OrthoParams.w > 0.5;
                float3 rayPerEye = ortho ? camFwd : (posWS - _WorldSpaceCameraPos) / max(1e-3, surfEye);
                float sceneEye = EyeDepth(SampleSceneDepth(suv));
                float3 bottomWS = posWS + rayPerEye * max(0.0, sceneEye - surfEye);
                float depth = max(0.0, posWS.y - bottomWS.y);

                // Refraction: bend the view of the bottom with the ripples, never onto something in front of the water.
                float2 ruv = suv + N.xz * _RefractionStrength * saturate(depth * 1.5) * detail;
                float refrEye = EyeDepth(SampleSceneDepth(ruv));
                if (refrEye < surfEye) { ruv = suv; refrEye = sceneEye; }
                float3 bottomR = posWS + rayPerEye * max(0.0, refrEye - surfEye);
                float depthR = max(0.0, posWS.y - bottomR.y);
                float path = max(0.0, refrEye - surfEye) * length(rayPerEye);
                half3 sceneColor = SampleSceneColor(ruv);

                Light mainLight = GetMainLight(TransformWorldToShadowCoord(posWS));
                half shadow = mainLight.shadowAttenuation;
                half ndl = saturate(dot(N, mainLight.direction));
                half3 ambient = SampleSH(N);

                // Body colour by depth, lit softly (water in shade stays bright, as in the palette).
                float deepT = 1.0 - exp(-depth / max(0.05, _DepthRange));
                half3 waterColor = lerp(_ShallowColor.rgb, _DeepColor.rgb, deepT);
                half3 body = waterColor * (ambient * 0.75 + mainLight.color * (0.35 + 0.45 * ndl) * lerp(0.55, 1.0, shadow));

                // The bottom seen through the water: tinted, with caustics where the bottom is sunlit and shallow.
                float2 cuv = bottomR.xz / max(0.1, _CausticsSize);
                half c1 = SAMPLE_TEXTURE2D(_AuxTex, sampler_AuxTex, cuv + t * float2(0.021, 0.013)).r;
                half c2 = SAMPLE_TEXTURE2D(_AuxTex, sampler_AuxTex, cuv * 1.37 + float2(0.37, 0.71) - t * float2(0.017, -0.019)).r;
                half caustics = min(c1, c2) * _CausticsStrength * (1.0 - smoothstep(0.0, max(0.05, _CausticsDepth), depthR));
                caustics *= MainLightRealtimeShadow(TransformWorldToShadowCoord(bottomR));
                half3 bottom = sceneColor * lerp(half3(1, 1, 1), _ShallowColor.rgb * 1.35, _BottomTint) + caustics * mainLight.color;
                float transmit = exp(-path / max(0.05, _Clarity));
                half3 color = lerp(body, bottom, transmit);

                // Sky reflection (fresnel) and sun glint.
                half3 R = reflect(-V, N);
                half3 sky = GlossyEnvironmentReflection(R, 1.0 - _Smoothness, 1.0);
                half fresnel = lerp(0.03, 1.0, pow(1.0 - saturate(dot(N, V)), _FresnelPower));
                color = lerp(color, sky, saturate(fresnel * _ReflectionStrength));
                half3 H = normalize(mainLight.direction + V);
                half nh = saturate(dot(N, H));
                color += (pow(nh, 420.0) * 3.0 + pow(nh, 48.0) * 0.08) * _SpecularStrength * mainLight.color * shadow;

                // Shore foam: a solid line at the contact, broken up further out by the noise mask.
                half shore = 1.0 - saturate(depth / max(0.02, _FoamWidth));
                half noise = SAMPLE_TEXTURE2D(_AuxTex, sampler_AuxTex, posWS.xz / max(0.1, _FoamNoiseSize) + wind * t * 0.035 + flow * t * 0.08).g;
                half foam = smoothstep(noise - 0.07, noise + 0.07, shore * shore * 1.1);
                foam = max(foam, smoothstep(0.82, 0.97, shore)) * _FoamStrength;
                half3 foamLit = _FoamColor.rgb * (ambient * 0.6 + mainLight.color * (0.5 + 0.4 * ndl) * lerp(0.7, 1.0, shadow));
                color = lerp(color, foamLit, foam);

                half alpha = saturate(depth / max(0.005, _EdgeSoftness) + foam);
                color = MixFog(color, InitializeInputDataFog(float4(posWS, 1.0), input.fogFactor));
                return half4(color, alpha);
            }
            ENDHLSL
        }
    }

    FallBack Off
}
