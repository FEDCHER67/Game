// Vadim 28.10: copy of GenericFoliageScaled for the forest leaf cards. Near the camera the crown turns see-through
// (real alpha, no dither): the opaque passes skip what is closer than _NearFade.y, the pass "FoliageNearFade"
// (drawn after the transparents by the ForestNearFoliage renderer feature) blends it back in, fading to _NearAlpha.
Shader "OnlyVolunteers/Forest/FoliageNearFade_v01"
{
    Properties
    {
        _BaseMap("Albedo / cutout",2D)="white"{}
        _BaseColor("Tint",Color)=(.35,.55,.18,1)
        _UseVertexTint("Use vertex RGB as tint",Range(0,1))=0
        _UseVertexMask("Use vertex alpha as flexibility",Range(0,1))=0
        _Cutoff("Alpha clip (0 = opaque)",Range(0,1))=0
        _WindResponse("Wind response (grass 1, tree .1)",Range(0,2))=.12
        _FlexibleHeight("Root stiffness height (local metres)",Float)=1
        _WindPivotOS("Local base pivot offset",Vector)=(0,0,0,0)
        _TipFlash("Tip light change",Range(0,.3))=.08
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull",Float)=0
        _NearFade("Near fade: x see-through, y opaque (m)",Vector)=(2,6,0,0)
        _NearAlpha("Alpha when touching",Range(0,1))=.04
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "RenderPipeline"="UniversalPipeline" "Queue"="AlphaTest" "DisableBatching"="True" }
        Cull [_Cull] ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        #include "Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST,_BaseColor,_WindPivotOS;
        float4 _NearFade;
        float _UseVertexTint,_UseVertexMask,_Cutoff,_WindResponse,_FlexibleHeight,_TipFlash,_Cull,_NearAlpha;
        CBUFFER_END
        float3 _LightDirection,_LightPosition;
        struct Attributes { float4 positionOS:POSITION;float3 normalOS:NORMAL;float2 uv:TEXCOORD0;float4 color:COLOR;UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct Varyings {float4 positionCS:SV_POSITION;float3 positionWS:TEXCOORD0;float3 normalWS:TEXCOORD1;float2 uv:TEXCOORD2;float4 tint:TEXCOORD3;float2 fogFlash:TEXCOORD4;UNITY_VERTEX_OUTPUT_STEREO};
        Varyings Vert(Attributes input)
        {
            UNITY_SETUP_INSTANCE_ID(input);
            Varyings o=(Varyings)0;UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            o.positionWS=TransformObjectToWorld(input.positionOS.xyz);
            o.normalWS=TransformObjectToWorldNormal(input.normalOS);
            float3 pivot=TransformObjectToWorld(_WindPivotOS.xyz);
            // The per-instance matrix includes Terrain heightScale and ordinary prefab scale.
            // Keep the shared gust field and material response; scale only the stiffness height.
            float3 upVector=mul((float3x3)GetObjectToWorldMatrix(),float3(0,1,0));
            float heightScale=max(.0001,length(upVector));
            float3 up=upVector/heightScale;
            float flash;V19WindDeform(pivot,up,_WindResponse,_FlexibleHeight*heightScale,lerp(1,input.color.a,_UseVertexMask),o.positionWS,o.normalWS,flash);
            o.positionCS=TransformWorldToHClip(o.positionWS);
            o.uv=TRANSFORM_TEX(input.uv,_BaseMap);
            o.tint=_BaseColor*lerp(float4(1,1,1,1),float4(input.color.rgb,1),_UseVertexTint);
            o.fogFlash=float2(ComputeFogFactor(o.positionCS.z),flash);
            return o;
        }
        Varyings ShadowVert(Attributes input)
        {
            Varyings o=Vert(input);
            float3 lightDirection=_LightDirection;
            #if _CASTING_PUNCTUAL_LIGHT_SHADOW
            lightDirection=normalize(_LightPosition-o.positionWS);
            #endif
            o.positionCS=TransformWorldToHClip(ApplyShadowBias(o.positionWS,o.normalWS,lightDirection));
            #if UNITY_REVERSED_Z
            o.positionCS.z=min(o.positionCS.z,UNITY_NEAR_CLIP_VALUE*o.positionCS.w);
            #else
            o.positionCS.z=max(o.positionCS.z,UNITY_NEAR_CLIP_VALUE*o.positionCS.w);
            #endif
            return o;
        }
        half4 Surface(Varyings i){half4 c=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv)*i.tint;clip(c.a-max(.0001,_Cutoff));return c;}
        float CamDist(Varyings i){return distance(i.positionWS,_WorldSpaceCameraPos);}
        half3 Shade(Varyings i,half4 c)
        {
            float3 n=normalize(i.normalWS);
            Light sun=GetMainLight(TransformWorldToShadowCoord(i.positionWS));
            float3 lit=c.rgb*(max(SampleSH(n),.14)+sun.color*(.55+.45*saturate(dot(n,sun.direction)))*(.3+.7*sun.shadowAttenuation));
            lit*=1+_TipFlash*i.fogFlash.y;
            return MixFog(lit,i.fogFlash.x);
        }
        half4 Forward(Varyings i):SV_Target{clip(CamDist(i)-_NearFade.y);half4 c=Surface(i);return half4(Shade(i,c),1);}
        half4 NearFade(Varyings i):SV_Target
        {
            float d=CamDist(i);clip(_NearFade.y-d);half4 c=Surface(i);
            return half4(Shade(i,c),lerp(_NearAlpha,1,smoothstep(_NearFade.x,_NearFade.y,d)));
        }
        half4 Depth(Varyings i):SV_Target{Surface(i);return 0;}
        half4 DepthFar(Varyings i):SV_Target{clip(CamDist(i)-_NearFade.y);Surface(i);return 0;}
        half4 Normals(Varyings i):SV_Target{clip(CamDist(i)-_NearFade.y);Surface(i);return half4(normalize(i.normalWS),0);}
        ENDHLSL
        Pass { Name "Forward" Tags { "LightMode"="UniversalForwardOnly" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Forward
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            ENDHLSL
        }
        Pass { Name "FoliageNearFade" Tags { "LightMode"="FoliageNearFade" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment NearFade
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            ENDHLSL
        }
        Pass { Name "ShadowCaster" Tags { "LightMode"="ShadowCaster" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex ShadowVert
            #pragma fragment Depth
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            ENDHLSL
        }
        Pass { Name "DepthOnly" Tags { "LightMode"="DepthOnly" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment DepthFar
            #pragma multi_compile_instancing
            
            ENDHLSL
        }
        Pass { Name "DepthNormals" Tags { "LightMode"="DepthNormalsOnly" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Normals
            #pragma multi_compile_instancing
            
            ENDHLSL
        }
    }
}
