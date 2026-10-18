// OnlyVolunteers G14 v03 (2026-10-18, TASK-000811): v02 + Sea of Thieves-like wave colour — light turquoise crests
// (fake subsurface glow from the wave height, stronger against the sun) and darker troughs. MIT; derived from Uber Stylized Water.
// New metre-based depth/composition wraps its retained Gerstner and two-way normal functions.
#ifndef OV_UBER_WATER_STYLE_V03_INCLUDED
#define OV_UBER_WATER_STYLE_V03_INCLUDED
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Texture.hlsl"
#include "Packages/com.unity.shadergraph/ShaderGraphLibrary/Functions.hlsl"
#include "UberGraphPrimitives_v03.hlsl"

TEXTURE2D(_Normal_Map); SAMPLER(sampler_Normal_Map);
TEXTURE2D(_OV_FoamMap); SAMPLER(sampler_OV_FoamMap);
TEXTURE2D(_OV_NoiseMap); SAMPLER(sampler_OV_NoiseMap);
CBUFFER_START(UnityPerMaterial)
float4 _Normal_Map_TexelSize;
float4 _Color_Shallow, _Color_Deep, _OV_ShoreColor, _OV_FoamColor, _OV_ColorMid;
float4 _OV_DetailFade, _1st_Wave_Direction, _2nd_Wave_Direction;
float4 _OV_Wave3, _OV_Wave3Direction, _OV_SkyTint, _OV_Fresnel;
float4 _OV_SunColor, _OV_Glints, _OV_Caustics, _OV_FallTiling;
float4 _OV_CrestColor, _OV_CrestRange;
float _OV_TroughDarken, _OV_CrestBacklight;
float _OV_Mode, _Cull, _OV_ShallowDepth, _OV_DeepDepth;
float _OV_ShoreTintDepth, _OV_ShoreTintStrength, _OV_FoamScale, _OV_InnerWidth;
float _OV_FoamSoftness, _OV_OuterWidth, _OV_OuterTravel, _OV_FoamPeriod;
float _OV_OuterStrength, _OV_IntersectionWidth, _Normal_Strength, _Normal_DistanceStrength;
float _Normal_Scale, _Normal_Pan, _OV_MeshFlow, _OV_FlowSpeed;
float _OV_FlowPeriod, _OV_FlowFoam, _1st_Wave_Length;
float _1st_Wave_Height, _1st_Wave_Speed, _2nd_Wave_Length, _2nd_Wave_Height;
float _2nd_Wave_Speed, _OV_CrestFoam, _OV_CrestThreshold, _OV_ShadowStrength;
float _OV_Refraction, _OV_Clarity;
float _OV_FallSpeed, _OV_FallFoam, _OV_FallOpacity, _OV_SplashSpeed;
float _OV_SplashOpacity, _OV_SoftContact;
float _OV_UseMidColor, _OV_MidDepth, _OV_GlintCoverage;
CBUFFER_END

struct WaterAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
    float4 tangentOS : TANGENT;
    float2 uv : TEXCOORD0;
    float2 flow : TEXCOORD1; // V3Water / V3Mesh: signed world-XZ velocity in m/s, NOT encoded colour.
    float4 color : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};
struct WaterVaryings
{
    float4 positionCS : SV_POSITION;
    float3 positionWS : TEXCOORD0;
    float3 normalWS : TEXCOORD1;
    float4 tangentWS : TEXCOORD2;
    float4 uvFlow : TEXCOORD3;
    float3 waveFog : TEXCOORD4; // crest height / summed amplitude, fog, undeformed water Y
    half4 color : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

// Upstream equation, with guarded inputs; all displacement stays in world metres.
void OV_UberWave(float3 p, float lengthM, float amplitude, float speed, float3 direction,
                 out float3 displacement, out float3 normal)
{
    Bindings_GersterWaveGenerator_aac6f1504e8ae554dac04c1d18eb799b_float b;
    b.WorldSpacePosition = p;
    b.TimeParameters = _TimeParameters.xyz;
    direction.y = 0;
    direction = dot(direction, direction) > 0.0001 ? normalize(direction) : float3(1,0,0);
    // Keep the source function's divisions finite even if an artist sets amplitude to zero.
    float enabled = step(0.00001, amplitude);
    float safeHeight = max(amplitude, 0.00001);
    SG_GersterWaveGenerator_aac6f1504e8ae554dac04c1d18eb799b_float(
        max(lengthM, 0.25), min(0.025, safeHeight * 0.2), safeHeight, speed, direction,
        b, displacement, normal);
    displacement *= enabled;
    normal = lerp(float3(0,1,0), normal, enabled);
}

WaterVaryings WaterVertex(WaterAttributes input)
{
    WaterVaryings o = (WaterVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, o);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    float3 p = TransformObjectToWorld(input.positionOS.xyz);
    float baseY = p.y;
    float3 n = TransformObjectToWorldNormal(input.normalOS);
    float crest = 0;
#if defined(_ENABLEWAVE) && !defined(_OV_MODE_WATERFALL) && !defined(_OV_MODE_FOAMSPLASH)
    float3 d1, d2, d3, n1, n2, n3;
    OV_UberWave(p, _1st_Wave_Length, _1st_Wave_Height, _1st_Wave_Speed, _1st_Wave_Direction.xyz, d1, n1);
    OV_UberWave(p, _2nd_Wave_Length, _2nd_Wave_Height, _2nd_Wave_Speed, _2nd_Wave_Direction.xyz, d2, n2);
    OV_UberWave(p, _OV_Wave3.x, _OV_Wave3.y, _OV_Wave3.z, _OV_Wave3Direction.xyz, d3, n3);
    float waveFade = 1 - smoothstep(100, 220, distance(GetCameraPositionWS(), p));
    // Apply only to upward-facing water meshes, never turn a vertical sheet into an ocean.
    waveFade *= saturate(n.y);
    float3 delta = (d1 + d2 + d3) * waveFade;
    crest = delta.y / max(_1st_Wave_Height + _2nd_Wave_Height + _OV_Wave3.y, 0.0001);
    p += delta;
    n = normalize(lerp(n, normalize(n1 + n2 + n3 - float3(0,2,0)), waveFade));
#endif
    o.positionWS = p;
    o.normalWS = n;
    o.tangentWS = float4(TransformObjectToWorldDir(input.tangentOS.xyz), input.tangentOS.w * GetOddNegativeScale());
    o.positionCS = TransformWorldToHClip(p);
    o.uvFlow = float4(input.uv, input.flow);
    o.waveFog = float3(crest, ComputeFogFactor(o.positionCS.z), baseY);
    o.color = input.color;
    return o;
}

float3 OV_UberNormal(float2 xz, float detailFade)
{
    Bindings_var2WayNormalBlend_0731d7b977697114da66cb4d58f833a0_float b;
    b.AbsoluteWorldSpacePosition = float3(xz.x, 0, xz.y);
    b.TimeParameters = _TimeParameters.xyz;
    UnityTexture2D normalMap = UnityBuildTexture2DStructInternal(
        _Normal_Map, sampler_Normal_Map, _Normal_Map_TexelSize, float4(1,1,0,0), float4(0,0,0,0));
    float3 rawNormal, detail;
    SG_var2WayNormalBlend_0731d7b977697114da66cb4d58f833a0_float(
        detailFade, _Normal_Strength, _Normal_DistanceStrength, normalMap,
        _Normal_Pan, _Normal_Scale, b, rawNormal, detail);
    return normalize(detail);
}

// Two half-period-offset phases: preserve converter velocity without unbounded bending/stretching.
void OV_FlowCoordinates(float2 p, float2 velocity, out float2 a, out float2 b, out float blend)
{
    float period = max(_OV_FlowPeriod, 0.25);
    float phase = frac(_Time.y / period);
    a = p - velocity * (phase * period);
    b = p - velocity * (frac(phase + 0.5) * period);
    blend = abs(phase * 2 - 1); // the resetting phase has exactly zero weight
}

float OV_DepthAt(float2 uv, out float3 world)
{
    float raw = SampleSceneDepth(uv);
#if UNITY_REVERSED_Z
    float valid = step(0.000001, raw);
#else
    float valid = 1 - step(0.999999, raw);
    raw = lerp(UNITY_NEAR_CLIP_VALUE, 1, raw);
#endif
    world = ComputeWorldSpacePosition(uv, raw, UNITY_MATRIX_I_VP);
    return valid;
}

// Cheap analytic caustic network; no extra texture, projector, camera or render pass.
float OV_Caustic(float2 bedXZ, float time)
{
    float2 p = bedXZ * max(_OV_Caustics.y, 0.01);
    p += 0.38 * sin(p.yx * 1.31 + float2(time, -time * 0.7));
    float a = sin(p.x + p.y * 0.61 + time * 0.35);
    float b = sin(p.y - p.x * 0.49 - time * 0.28);
    float field = abs(a * b);
    float aa = max(fwidth(field), 0.015);
    return 1 - smoothstep(0.055, 0.11 + aa, field);
}

half4 WaterFragment(WaterVaryings i) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    float2 screenUV = GetNormalizedScreenSpaceUV(i.positionCS);
    float3 sceneWS;
    float sceneValid = OV_DepthAt(screenUV, sceneWS);
    float waterEye = -TransformWorldToView(i.positionWS).z;
    float eyeGap = max(0, -TransformWorldToView(sceneWS).z - waterEye);
    eyeGap = lerp(1000, eyeGap, sceneValid);
    float detailFade = smoothstep(_OV_DetailFade.x, max(_OV_DetailFade.y, _OV_DetailFade.x + 1),
                                 distance(GetCameraPositionWS(), i.positionWS));
    float time = _Time.y;

#if defined(_OV_MODE_FOAMSPLASH)
    float2 uv = i.uvFlow.xy;
    float radius = length((uv - 0.5) * 2);
    float mask = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap, uv * 2 + float2(time * 0.03, -time * 0.045)).r;
    float phase = frac(time * _OV_SplashSpeed);
    float ring = 1 - smoothstep(0.06, 0.16, abs(radius - lerp(0.15, 0.9, phase)));
    ring *= sin(phase * PI);
    float patch = (1 - smoothstep(0.1, 0.72, radius)) * smoothstep(0.1, 0.6, mask);
    float alpha = saturate(patch * 0.65 + ring * lerp(0.2, 1, mask));
    alpha *= (1 - smoothstep(0.82, 1, radius)) * _OV_SplashOpacity * i.color.a;
    alpha *= saturate(eyeGap / max(_OV_SoftContact, 0.001)) * _OV_FoamColor.a;
    return half4(MixFog(_OV_FoamColor.rgb, i.waveFog.y), alpha);
#else
    float2 p = i.positionWS.xz;
    float2 velocity = 0;
    float2 flowA = p, flowB = p;
    float flowBlend = 0;
#if defined(_OV_MODE_WATERFALL)
    // UV0 V=0 bottom, V=1 top. Increasing sampled V moves features down the sheet.
    p = i.uvFlow.xy * _OV_FallTiling.xy + float2(0, time * _OV_FallSpeed);
    flowA = flowB = p * 10 / max(_Normal_Scale, 0.01);
#elif defined(_OV_FLOW)
    velocity = i.uvFlow.zw * _OV_FlowSpeed;
    OV_FlowCoordinates(p, velocity, flowA, flowB, flowBlend);
#endif
    float3 detail = OV_UberNormal(flowA, detailFade);
#if defined(_OV_FLOW) && !defined(_OV_MODE_WATERFALL)
    detail = normalize(lerp(detail, OV_UberNormal(flowB, detailFade), flowBlend));
#endif
    float3 n = normalize(i.normalWS);
#if defined(_OV_MODE_WATERFALL)
    float3 tangent = normalize(i.tangentWS.xyz);
    float3 bitangent = cross(n, tangent) * i.tangentWS.w;
#else
    // Projected normals use the same fixed world XZ axes as the inherited sampler.
    float3 tangent = normalize(float3(1, -n.x / max(n.y, 0.05), 0));
    float3 bitangent = normalize(cross(tangent, n));
#endif
    n = normalize(n * detail.z + tangent * detail.x + bitangent * detail.y);
    float3 view = GetWorldSpaceNormalizeViewDir(i.positionWS);
    Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
    float lit = lerp(1 - _OV_ShadowStrength, 1, sun.shadowAttenuation);
    float fresnel = pow(saturate(1 - abs(dot(n, view))), max(_OV_Fresnel.y, 0.1)) * _OV_Fresnel.x;

#if defined(_OV_MODE_WATERFALL)
    float2 fallUV = float2(p.x, p.y * 0.22);
    float streak = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap, fallUV).r;
    float breakup = SAMPLE_TEXTURE2D(_OV_NoiseMap, sampler_OV_NoiseMap, p * float2(0.7, 0.45)).r;
    float foam = smoothstep(0.2, 0.6, streak + breakup * 0.22) * _OV_FallFoam;
    foam = max(foam, (1 - smoothstep(0, 0.2, i.uvFlow.y)) * 0.8);
    foam *= _OV_FoamColor.a;
    float3 colour = lerp(_Color_Shallow.rgb, _OV_FoamColor.rgb, foam);
    colour = lerp(colour * lit, _OV_SkyTint.rgb, fresnel);
    float side = smoothstep(0, 0.06, i.uvFlow.x) * (1 - smoothstep(0.94, 1, i.uvFlow.x));
    float alpha = side * lerp(_OV_FallOpacity, 1, foam) * i.color.a;
    return half4(MixFog(colour, i.waveFog.y), alpha);
#else
    float depth = max(0, i.positionWS.y - sceneWS.y);
    depth = lerp(1000, depth, sceneValid);
    float deep = smoothstep(_OV_ShallowDepth, max(_OV_DeepDepth, _OV_ShallowDepth + 0.01), depth);
    float3 colour = lerp(_Color_Shallow.rgb, _Color_Deep.rgb, deep);
    float midDepth = clamp(_OV_MidDepth, _OV_ShallowDepth + 0.01, max(_OV_DeepDepth - 0.01, _OV_ShallowDepth + 0.01));
    float3 threeTone = lerp(_Color_Shallow.rgb, _OV_ColorMid.rgb, smoothstep(_OV_ShallowDepth, midDepth, depth));
    threeTone = lerp(threeTone, _Color_Deep.rgb, smoothstep(midDepth, max(_OV_DeepDepth, midDepth + 0.01), depth));
    colour = lerp(colour, threeTone, saturate(_OV_UseMidColor));
    float shoreTint = (1 - smoothstep(0, max(_OV_ShoreTintDepth, 0.01), depth)) * _OV_ShoreTintStrength;
    colour = lerp(colour, _OV_ShoreColor.rgb, shoreTint);
    // v03: Sea of Thieves-like crest glow and trough shade from the summed wave height (-1 trough .. +1 crest).
    float waveH = i.waveFog.x;
    float3 v3view = SafeNormalize(GetWorldSpaceViewDir(i.positionWS));
    Light v3sun = GetMainLight();
    float backlit = saturate(dot(-v3view, v3sun.direction) * 0.5 + 0.5);
    float crestGlow = smoothstep(_OV_CrestRange.x, _OV_CrestRange.y, waveH) * _OV_CrestColor.a;
    crestGlow *= lerp(1.0, 0.55 + 0.9 * backlit, saturate(_OV_CrestBacklight)) * smoothstep(0.6, 2.5, depth);
    colour = lerp(colour, _OV_CrestColor.rgb, saturate(crestGlow));
    colour *= 1 - _OV_TroughDarken * smoothstep(0.0, 0.85, -waveH) * smoothstep(0.6, 2.5, depth);

    float2 foamUV = flowA * _OV_FoamScale + float2(time * 0.012, -time * 0.009);
    float foamTexture = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap, foamUV).r;
#if defined(_OV_FLOW)
    float f2 = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap,
                              flowB * _OV_FoamScale + float2(time * 0.012, -time * 0.009)).r;
    foamTexture = lerp(foamTexture, f2, flowBlend);
#endif
    float noise = SAMPLE_TEXTURE2D(_OV_NoiseMap, sampler_OV_NoiseMap, p * 0.17 + time * float2(0.007,-0.011)).r;
    float soft = max(_OV_FoamSoftness, min(fwidth(depth) * 0.6, 0.15) + 0.001);
    float inner = 1 - smoothstep(max(0, _OV_InnerWidth - soft), _OV_InnerWidth + soft, depth);
    // Camera depth catches opaque vertical posts/rocks/vehicles as well as the terrain slope.
    float contact = 1 - smoothstep(0, max(_OV_IntersectionWidth, 0.001), eyeGap);
    inner = max(inner, contact);
    float arrival = 0.5 + 0.5 * sin(time * TWO_PI / max(_OV_FoamPeriod, 0.1) + noise * 0.7);
    float centre = _OV_InnerWidth + _OV_OuterTravel * (0.25 + 0.75 * arrival);
    float outer = 1 - smoothstep(_OV_OuterWidth, _OV_OuterWidth + soft, abs(depth - centre));
    // The upstream animated depth-contour/dissolve idea, rescaled to metres and softened.
    outer *= smoothstep(0.16, 0.62, foamTexture + noise * 0.28) * _OV_OuterStrength;
    float crest = smoothstep(_OV_CrestThreshold, min(1, _OV_CrestThreshold + 0.28), i.waveFog.x);
    float caps = crest * smoothstep(0.12, 0.65, foamTexture) * _OV_CrestFoam * (1 - detailFade);
    float flowFoam = 0;
#if defined(_OV_FLOW)
    // Two displaced samples join mask fragments into short streaks along the local velocity.
    float2 stretch = velocity / max(length(velocity), 0.001) * 0.55;
    float tailA = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap, foamUV - stretch * _OV_FoamScale).r;
    float tailB = SAMPLE_TEXTURE2D(_OV_FoamMap, sampler_OV_FoamMap,
        (flowB - stretch) * _OV_FoamScale + float2(time * 0.012, -time * 0.009)).r;
    float streak = lerp(tailA, tailB, flowBlend) * foamTexture;
    flowFoam = smoothstep(0.10, 0.38, streak) * _OV_FlowFoam * saturate(length(velocity) * 3);
    flowFoam *= (1 - detailFade) * lerp(0.4, 1, 1 - smoothstep(0, 2.5, depth));
#endif
    float foam = saturate(max(inner, outer) + caps + flowFoam);

#if defined(_ENABLEREFRACTION)
    float2 offset = TransformWorldToViewDir(n, false).xy * _OV_Refraction;
    offset *= saturate(depth * 2) * (1 - detailFade) * (1 - foam);
    float2 refractUV = clamp(screenUV + offset, 0.001, 0.999);
    float3 refractWS;
    float refractValid = OV_DepthAt(refractUV, refractWS);
    // Reject foreground objects pulled into the water by the screen-space offset.
    float behind = step(waterEye + 0.02, -TransformWorldToView(refractWS).z) * refractValid;
    refractUV = lerp(screenUV, refractUV, behind);
    float clarity = _OV_Clarity * (1 - deep) * (1 - foam) * (1 - fresnel) * sceneValid;
    colour = lerp(colour, SampleSceneColor(refractUV) * lerp(1.0.xxx, _Color_Shallow.rgb, 0.12), clarity);
#endif
#if defined(_ENABLECAUSTICS)
    float shallow = (1 - smoothstep(0.5, max(_OV_Caustics.w, 0.51), depth)) * smoothstep(0.03,0.25,depth);
    float caustic = OV_Caustic(sceneWS.xz, time * _OV_Caustics.z);
    colour += _OV_ShoreColor.rgb * caustic * shallow * _OV_Caustics.x * sceneValid * (1 - foam) * (1 - detailFade) * sun.shadowAttenuation;
#endif
    colour = lerp(colour * lit, _OV_SkyTint.rgb, fresnel);
    float3 halfDir = SafeNormalize(view + sun.direction);
    float highlight = pow(saturate(dot(n, halfDir)), max(_OV_Glints.y, 8));
    // Broad soft sun shape with sparse crest glints, attenuated before they become distant shimmer.
    float sparseGlint = smoothstep(_OV_GlintCoverage, min(1, _OV_GlintCoverage + 0.14), foamTexture);
    float glint = highlight * lerp(0.10, 1, crest) * sparseGlint;
    glint *= _OV_Glints.x * (1 - detailFade) * sun.shadowAttenuation * (1 - foam);
    colour += _OV_SunColor.rgb * sun.color * glint;
    colour = lerp(colour, _OV_FoamColor.rgb * lerp(0.92, 1, sun.shadowAttenuation), foam * _OV_FoamColor.a);
    // Surface alpha stays opaque: OpaqueTexture transmission is composited once, never double-blended.
    return half4(MixFog(colour, i.waveFog.y), 1);
#endif
#endif
}
#endif
