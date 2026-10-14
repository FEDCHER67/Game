Shader "OnlyVolunteers/Paint/Brush"
{
    SubShader
    {
        Tags { "RenderType"="Transparent" }
        Pass
        {
            ZTest Always ZWrite Off Cull Off
            Blend One OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            float4x4 _PaintMatrix;
            struct a { float4 vertex:POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; float4 clip:TEXCOORD1; };
            struct v { float4 pos:SV_POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; float4 clip:TEXCOORD1; float2 maskUv:TEXCOORD2; };
            v vert(a i) { v o; o.pos=mul(_PaintMatrix,i.vertex); o.uv=i.uv; o.color=i.color; o.clip=i.clip; o.maskUv=i.vertex.xy; return o; }
            float4 frag(v i):SV_Target
            {
                clip(min(min(i.maskUv.x-i.clip.x,i.maskUv.y-i.clip.y),min(i.clip.z-i.maskUv.x,i.clip.w-i.maskUv.y)));
                float2 p=i.uv*2-1;
                float grain=frac(sin(dot(i.maskUv,float2(12345.6,78901.2)))*43758.5453);
                float edge=1-smoothstep(.76+grain*.10,1.0,length(p));
                float alpha=edge*(.90+.10*grain)*i.color.a;
                return float4(i.color.rgb*alpha,alpha);
            }
            ENDHLSL
        }
    }
}
