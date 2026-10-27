// Vadim 23.10 (local W86): distance haze everywhere on the map, like Schedule I. Clear near the camera, half-hazed at
// _VadimHaze.y metres, far objects sink into the haze colour. Full-screen pass, works on every material (the per-material
// fog / aerial receivers do not). Driven by the globals _VadimHaze (start, half distance, max amount, on) and _VadimHazeColor.
// Vadim 25.10: plus the steppe dust beyond the northern border — a thick orange fog in a box past the KPP fence. Each pixel's
// view ray is clipped to the box; the metres it runs inside (thinner with height, soft at the box's sides) turn into fog, so
// the dust is impenetrable after ~50 m and nothing beyond the border can be seen, from the KPP or from anywhere else.
Shader "Hidden/VadimHaze"
{
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" }
        ZWrite Off ZTest Always Cull Off
        Pass
        {
            Name "VadimHaze"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            float4 _VadimHaze;
            float4 _VadimHazeColor;

            // the dust box (world): x, y, z from / to; density per metre; height falloff
            static const float3 DustMin = float3(560.0, -30.0, 944.0);
            static const float3 DustMax = float3(1140.0, 45.0, 2400.0);
            static const float DustDensity = 0.022;
            static const float DustFalloff = 10.0;

            half3 Dust(half3 c, float3 cam, float3 wp, half3 hazeCol)
            {
                float3 rd = wp - cam; float len = length(rd); rd /= max(len, 1e-4);
                float3 inv = 1.0 / (abs(rd) < 1e-5 ? (rd >= 0 ? 1e-5 : -1e-5) : rd);
                float3 t0 = (DustMin - cam) * inv, t1 = (DustMax - cam) * inv;
                float3 tmin = min(t0, t1), tmax = max(t0, t1);
                float tin = max(max(tmin.x, tmin.y), max(tmin.z, 0.0)), tout = min(min(tmax.x, tmax.y), min(tmax.z, len));
                if (tout <= tin) return c;
                float3 mid = cam + rd * (tin + tout) * 0.5;
                float side = smoothstep(0.0, 140.0, min(mid.x - DustMin.x, DustMax.x - mid.x)) * smoothstep(DustMin.z, DustMin.z + 70.0, mid.z);   // soft near edge too
                float height = exp(-max(0.0, mid.y - 12.0) / DustFalloff);
                float3 outside = max(DustMin - cam, cam - DustMax); float camDist = length(max(outside, 0.0));
                float near = 1.0 - smoothstep(120.0, 260.0, camDist);                 // only seen near the KPP, not across the map (Vadim 25.10)
                float a = (1.0 - exp(-DustDensity * (tout - tin) * height * side)) * near;
                // warm orange by day, dimmer at night (the haze colour tells day from night)
                half lum = dot(hazeCol, half3(0.3, 0.59, 0.11));
                half3 dust = half3(0.86, 0.54, 0.27) * saturate(lum / 0.72 + 0.12);
                return lerp(c, dust, saturate(a));
            }

            half4 Frag(Varyings input) : SV_Target
            {
                float2 uv = input.texcoord;
                half4 c = SAMPLE_TEXTURE2D_X(_BlitTexture, sampler_LinearClamp, uv);
                float4 p = _VadimHaze.w > 0.5 ? _VadimHaze : float4(110, 380, 0.92, 1);
                half3 col = _VadimHazeColor.a > 0.5 ? _VadimHazeColor.rgb : half3(0.68, 0.79, 0.90);
                float raw = SampleSceneDepth(uv);
                #if UNITY_REVERSED_Z
                    bool sky = raw <= 0.000001;
                #else
                    bool sky = raw >= 0.999999;
                #endif
                float3 wp = ComputeWorldSpacePosition(uv, raw, UNITY_MATRIX_I_VP);
                if (sky)
                {   // the sky near the horizon meets the haze, no hard line where the land ends
                    float h = saturate(1.0 - abs(uv.y - 0.5) * 3.0);
                    c.rgb = lerp(c.rgb, col, h * h * p.z * 0.6);
                    float3 dir = normalize(wp - _WorldSpaceCameraPos);
                    c.rgb = Dust(c.rgb, _WorldSpaceCameraPos, _WorldSpaceCameraPos + dir * 4000.0, col);
                    return c;
                }
                float d = LinearEyeDepth(raw, _ZBufferParams);
                float t = max(0.0, d - p.x);
                float k = 0.6931 / max(1.0, (p.y - p.x) * (p.y - p.x));
                float f = (1.0 - exp(-k * t * t)) * p.z;
                c.rgb = lerp(c.rgb, col, f);
                c.rgb = Dust(c.rgb, _WorldSpaceCameraPos, wp, col);
                return c;
            }
            ENDHLSL
        }
    }
}
