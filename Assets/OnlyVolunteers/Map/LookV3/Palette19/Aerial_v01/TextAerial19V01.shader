Shader "OnlyVolunteers/StyleV3/TextAerial19V01"
{
 Properties {_MainTex("Font",2D)="white"{} _Color("Colour",Color)=(1,1,1,1)}
 SubShader
 {
  Tags {"Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline"}
  Pass
  {
   ZWrite Off Cull Off Blend SrcAlpha OneMinusSrcAlpha
   HLSLPROGRAM
   #pragma target 3.5
   #pragma vertex vert
   #pragma fragment frag
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   #include "Aerial19V01.hlsl"
   TEXTURE2D(_MainTex);SAMPLER(sampler_MainTex);
   CBUFFER_START(UnityPerMaterial)
   float4 _Color;
   CBUFFER_END
   struct A {float4 positionOS:POSITION;float2 uv:TEXCOORD0;float4 colour:COLOR;};
   struct V {float4 positionCS:SV_POSITION;float2 uv:TEXCOORD0;float4 colour:COLOR;float3 world:TEXCOORD1;};
   V vert(A i){V o;o.world=TransformObjectToWorld(i.positionOS.xyz);o.positionCS=TransformWorldToHClip(o.world);o.uv=i.uv;o.colour=i.colour*_Color;return o;}
   half4 frag(V i):SV_Target{return half4(G18AerialColour(i.colour.rgb,i.world),i.colour.a*SAMPLE_TEXTURE2D(_MainTex,sampler_MainTex,i.uv).a);}
   ENDHLSL
  }
 }
}
