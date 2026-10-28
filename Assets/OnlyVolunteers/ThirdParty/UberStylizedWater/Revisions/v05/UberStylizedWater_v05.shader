// MIT derivative of MatrixRex/Uber-Stylized-Water, commit 1fdd16c6312611fef7fb248dee86cdd3fd456a1e.
// OnlyVolunteers G14b/G14c v02, 2026-10-11; v03 2026-10-18 adds crest glow / trough shade (TASK-000811); v04 adds choppiness and waves 4-5 (TASK-000814); v05 adds the seabed tint (TASK-000818). See LICENSE here.
// The upstream Gerstner and two-way normal graph functions are retained in UberGraphPrimitives_v05.hlsl.
Shader "OnlyVolunteers/Uber Stylized Water v05"
{
    Properties
    {
        [KeywordEnum(Surface, Waterfall, FoamSplash)] _OV_Mode("Water mode", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Visible faces", Float) = 2
        [Header(Palette and depth in metres)]
        _Color_Shallow("Muted shallow colour", Color) = (0.435294,0.639216,0.627451,1)
        _Color_Deep("Muted deep colour", Color) = (0.184314,0.345098,0.407843,1)
        [ToggleUI] _OV_UseMidColor("Use separate mid depth colour", Float) = 1
        _OV_ColorMid("Mid depth colour", Color) = (0.290196,0.498039,0.549020,1)
        _OV_MidDepth("Mid colour depth (m)", Float) = 3.25
        _OV_ShoreColor("Light shoreline tint", Color) = (0.576471,0.713725,0.694118,1)
        _OV_ShallowDepth("End of shallows (m)", Float) = 1.5
        _OV_DeepDepth("Full deep colour (m)", Float) = 6
        _OV_ShoreTintDepth("Light band depth (m)", Float) = 0.65
        _OV_ShoreTintStrength("Light band amount", Range(0,1)) = 0.4
        [Header(Two layer shore and intersection foam)]
        _OV_FoamColor("Warm foam colour and opacity", Color) = (0.901961,0.890196,0.847059,0.62)
        [NoScaleOffset] _OV_FoamMap("Uber foam mask", 2D) = "white" {}
        [NoScaleOffset] _OV_NoiseMap("Uber breakup mask", 2D) = "gray" {}
        _OV_FoamScale("Foam texture repeats per metre", Float) = 0.65
        _OV_InnerWidth("Solid band depth (m)", Float) = 0.18
        _OV_FoamSoftness("Band edge softness (m)", Float) = 0.10
        _OV_OuterWidth("Outer band half width (m)", Float) = 0.13
        _OV_OuterTravel("Outer band travel in depth (m)", Float) = 0.75
        _OV_FoamPeriod("Arrival period (seconds)", Float) = 5.5
        _OV_OuterStrength("Broken outer band opacity", Range(0,1)) = 0.72
        _OV_IntersectionWidth("Obstacle contact distance (m)", Float) = 0.18
        [Header(Uber two way animated normals)]
        [Normal][NoScaleOffset] _Normal_Map("Normal map", 2D) = "bump" {}
        _Normal_Strength("Near ripple strength", Range(0,1)) = 0.22
        _Normal_DistanceStrength("Far ripple strength", Range(0,1)) = 0.045
        _Normal_Scale("Normal tile (10 divided by metres)", Float) = 3.333333
        _Normal_Pan("Uber cross ripple speed", Float) = 0.16
        _OV_DetailFade("Detail fade start and end (m)", Vector) = (35,130,0,0)
        [Header(River flow from converter)]
        [Toggle(_OV_FLOW)] _OV_MeshFlow("Use UV1.xy world XZ velocity", Float) = 0
        _OV_FlowSpeed("Mesh flow multiplier", Float) = 1
        _OV_FlowPeriod("Flow reset crossfade (seconds)", Float) = 4
        _OV_FlowFoam("Small flowing foam amount", Range(0,1)) = 0
        [Header(Upstream Gerstner waves)]
        [Toggle(_ENABLEWAVE)] _ENABLEWAVE("Vertex waves (subdivided mesh)", Float) = 1
        _1st_Wave_Length("Wave 1 wavelength (m)", Float) = 12
        _1st_Wave_Height("Wave 1 amplitude (m)", Float) = 0.09
        _1st_Wave_Speed("Wave 1 phase speed", Float) = 0.55
        _1st_Wave_Direction("Wave 1 direction XZ", Vector) = (1,0,0.25,0)
        _2nd_Wave_Length("Wave 2 wavelength (m)", Float) = 8
        _2nd_Wave_Height("Wave 2 amplitude (m)", Float) = 0.045
        _2nd_Wave_Speed("Wave 2 phase speed", Float) = 0.42
        _2nd_Wave_Direction("Wave 2 direction XZ", Vector) = (-0.3,0,1,0)
        _OV_Wave3("Wave 3 length amplitude speed", Vector) = (5.5,0.025,0.38,0)
        _OV_Wave3Direction("Wave 3 direction XZ", Vector) = (0.6,0,-0.8,0)
        _OV_CrestFoam("Soft white caps", Range(0,1)) = 0.22
        _OV_CrestThreshold("Crest threshold", Range(0,0.95)) = 0.42
        [Header(Soft light)]
        _OV_SkyTint("Fresnel sky tint", Color) = (0.623529,0.701961,0.749020,1)
        _OV_Fresnel("Fresnel amount and power", Vector) = (0.14,4,0,0)
        _OV_SunColor("Sun glint tint", Color) = (0.901961,0.890196,0.847059,1)
        _OV_Glints("Glint amount and exponent", Vector) = (0.18,360,0,0)
        _OV_GlintCoverage("Glint mask threshold (higher is fewer)", Range(0,0.95)) = 0.78
        _OV_ShadowStrength("Main light shadow tint amount", Range(0,1)) = 0.16
        [Header(v03 wave colour like Sea of Thieves)]
        _OV_CrestColor("Crest glow colour (alpha = amount, 0 = off)", Color) = (0.36,0.92,0.84,0)
        _OV_CrestRange("Crest glow from to (wave height -1..1)", Vector) = (0.1,0.85,0,0)
        _OV_CrestBacklight("Crest glow stronger against the sun", Range(0,1)) = 0.6
        _OV_TroughDarken("Trough darkening", Range(0,0.6)) = 0
        [Header(v04 choppy sea)]
        _OV_Choppiness("Wave sharpness (0 = smooth as v03)", Range(0,1)) = 0
        _OV_Wave4("Wave 4 length amplitude speed (amplitude 0 = off)", Vector) = (3,0,0.5,0)
        _OV_Wave4Direction("Wave 4 direction XZ", Vector) = (-0.8,0,-0.6,0)
        _OV_Wave5("Wave 5 length amplitude speed (amplitude 0 = off)", Vector) = (2,0,0.6,0)
        _OV_Wave5Direction("Wave 5 direction XZ", Vector) = (0.2,0,-1,0)
        _OV_Wobble("Shake: amplitude m, frequency 1/m, speed (amplitude 0 = off)", Vector) = (0.05,0.9,4,0)
        [Header(Under the surface)]
        [Toggle(_ENABLEREFRACTION)] _ENABLEREFRACTION("Opaque texture refraction", Float) = 1
        _OV_Refraction("Distortion (fraction of screen)", Range(0,0.02)) = 0.003
        _OV_Clarity("Shallow scene visibility", Range(0,0.5)) = 0.14
        _OV_ClarityTint("Seabed tint by the water colour (0 = as v04)", Range(0,1)) = 0
        [Toggle(_ENABLECAUSTICS)] _ENABLECAUSTICS("Procedural shallow caustics", Float) = 1
        _OV_Caustics("Caustics amount scale speed max depth", Vector) = (0.09,1.4,0.3,3.5)
        [Header(Waterfall uses UV0 with V upwards)]
        _OV_FallTiling("Fall repeats U V", Vector) = (5,1.4,0,0)
        _OV_FallSpeed("Fall UV repeats per second", Float) = 0.85
        _OV_FallFoam("Fall streak amount", Range(0,1)) = 0.7
        _OV_FallOpacity("Fall sheet opacity", Range(0,1)) = 0.86
        [Header(Splash uses radial UV0)]
        _OV_SplashSpeed("Splash ring arrivals per second", Float) = 0.45
        _OV_SplashOpacity("Splash opacity", Range(0,1)) = 0.75
        _OV_SoftContact("Splash soft contact distance (m)", Float) = 0.18
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="Transparent" "Queue"="Transparent" }
        Pass
        {
            Name "WaterForward"
            Tags { "LightMode"="UniversalForwardOnly" }
            Blend SrcAlpha OneMinusSrcAlpha, One OneMinusSrcAlpha
            ZWrite Off
            ZTest LEqual
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex WaterVertex
            #pragma fragment WaterFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma shader_feature_local _OV_MODE_SURFACE _OV_MODE_WATERFALL _OV_MODE_FOAMSPLASH
            #pragma shader_feature_local _ _ENABLEWAVE
            #pragma shader_feature_local_fragment _ _OV_FLOW
            #pragma shader_feature_local_fragment _ _ENABLEREFRACTION
            #pragma shader_feature_local_fragment _ _ENABLECAUSTICS
            #define _SURFACE_TYPE_TRANSPARENT 1
            #include "WaterStyle_v05.hlsl"
            ENDHLSL
        }
    }
    Fallback Off
}
