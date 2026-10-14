// Original URP style adapter around MangoButtermilch's indirect instance pipeline (MIT).
Shader "OnlyVolunteers/Grass/MB_TallGrass24"
{
    Properties
    {
        _RootMuted("Muted roots",Color)=(.26,.32,.15,1)
        _TipMuted("Muted tips",Color)=(.52,.59,.30,1)
        _RootBright("Hamlet roots",Color)=(.27,.39,.13,1)
        _TipBright("Hamlet tips",Color)=(.63,.77,.33,1)
        _GrassSRPOptOut("Grass-only instancing path",Float)=1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Cull Off ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        #define UNITY_INDIRECT_DRAW_ARGS IndirectDrawIndexedArgs
        #include "UnityIndirect.cginc"
        struct Blade { float4 positionHeight; float4 shape; };
        StructuredBuffer<Blade> _Blades;
        StructuredBuffer<uint> _Visible;
        // Deliberately outside UnityPerMaterial: ONLY this shader bypasses the SRP Batcher.
        // Explicit indirect draws + per-camera property blocks; no global pipeline changes.
        float4 _RootMuted,_TipMuted,_RootBright,_TipBright;
        float _GrassSRPOptOut,_GrassTime,_ViewDistance;
        float4 _GrassWind;
        struct Attributes { float3 positionOS:POSITION; float2 uv:TEXCOORD0; uint instanceID:SV_InstanceID; };
        struct Varyings { float4 positionCS:SV_POSITION; float3 positionWS:TEXCOORD0; float3 colour:TEXCOORD1; float fog:TEXCOORD2; float3 normalWS:TEXCOORD3; };
        Varyings GrassVertex(Attributes input)
        {
            InitIndirectDrawArgs(0);
            uint id=_Visible[GetIndirectInstanceID(input.instanceID)];
            Blade blade=_Blades[id];
            float3 root=blade.positionHeight.xyz;
            float height=blade.positionHeight.w;
            float y=input.uv.y;
            float2 direction=_GrassWind.zw;
            float wave=sin(dot(root.xz,direction)*.115-_GrassTime*_GrassWind.y);
            float gust=pow(saturate(wave*.5+.5),3);
            float ripple=sin(dot(root.xz,float2(.67,-.74))*.82-_GrassTime*2.8);
            float bend=(_GrassWind.x*(.35+.9*gust)+ripple*.035)*y*y*height*_GrassSRPOptOut;
            float3 p=float3(input.positionOS.x*blade.shape.z,input.positionOS.y*height,input.positionOS.z*height);
            p.xz=float2(p.x*blade.shape.x-p.z*blade.shape.y,p.x*blade.shape.y+p.z*blade.shape.x);
            p.xz+=direction*bend;
            // Collapse the final 20 metres smoothly into the preserved low layer.
            float fade=1-smoothstep(_ViewDistance-20,_ViewDistance,distance(root,_WorldSpaceCameraPos));
            p*=fade;
            Varyings output;
            output.positionWS=root+p;
            output.positionCS=TransformWorldToHClip(output.positionWS);
            float code=blade.shape.w;
            float palette=frac(code);
            float3 low=lerp(_RootMuted.rgb,_RootBright.rgb,palette);
            float3 high=lerp(_TipMuted.rgb,_TipBright.rgb,palette);
            if(code>1.5) { low=SRGBToLinear(float3(.35,.34,.22)); high=SRGBToLinear(float3(.62,.59,.37)); }
            if(code>3.5) { low=SRGBToLinear(float3(.39,.39,.23)); high=SRGBToLinear(float3(.69,.68,.42)); }
            float patch=.93+.07*sin(root.x*.047+sin(root.z*.061)*1.6)+.035*sin(root.z*.16);
            output.colour=lerp(low,high,smoothstep(0,1,y))*patch;
            output.normalWS=normalize(float3(-blade.shape.y*.24,.96,blade.shape.x*.24));
            output.fog=ComputeFogFactor(output.positionCS.z);
            return output;
        }
        ENDHLSL
        Pass
        {
            Name "GrassForward" Tags { "LightMode"="UniversalForwardOnly" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex GrassVertex
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            half4 Frag(Varyings input):SV_Target
            {
                Light sun=GetMainLight(TransformWorldToShadowCoord(input.positionWS));
                float3 ambient=max(SampleSH(input.normalWS),float3(.14,.14,.14));
                float diffuse=.55+.45*saturate(dot(input.normalWS,sun.direction));
                float shadow=.30+.70*sun.shadowAttenuation;
                float3 colour=input.colour*(ambient+sun.color*diffuse*shadow);
                return half4(MixFog(colour,input.fog),1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags { "LightMode"="DepthOnly" } ColorMask R
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex GrassVertex
            #pragma fragment Depth
            half4 Depth(Varyings input):SV_Target { return input.positionCS.z; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals" Tags { "LightMode"="DepthNormalsOnly" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex GrassVertex
            #pragma fragment Normals
            half4 Normals(Varyings input):SV_Target { return half4(normalize(input.normalWS),0); }
            ENDHLSL
        }
    }
}
