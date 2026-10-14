// STAGED ONLY. Preserve fog, depth, shadow and instancing passes.
// G23. Shared deformation for colour, shadow, depth and depth-normal passes.
// URP 17.5 includes provide lighting. No wind texture, scripts or material clones per tree.
#ifndef OV_FOREST_FROND_SWAY_V03
#define OV_FOREST_FROND_SWAY_V03
UNITY_INSTANCING_BUFFER_START(TreeWind)
    UNITY_DEFINE_INSTANCED_PROP(float4, _TreeShape)
    UNITY_DEFINE_INSTANCED_PROP(float4, _WindSettings)
UNITY_INSTANCING_BUFFER_END(TreeWind)
// Test captures only: x = seconds, w = override enabled. Zero uses Unity's clock.
float4 _TreesPreviewClock;

float3 TreeSwayPosition(float3 p, float frondTip)
{
    float4 shape = UNITY_ACCESS_INSTANCED_PROP(TreeWind, _TreeShape);
    float4 wind = UNITY_ACCESS_INSTANCED_PROP(TreeWind, _WindSettings);
    float h = saturate((p.y - shape.x) * shape.y);
    // Bottom 4% is exactly fixed; outer branch tips get more movement than the stem.
    float heightWeight = saturate((h - 0.04) / 0.96);
    float tip = saturate(length(p.xz) * shape.z);
    float tipWeight = saturate(frondTip);
    tipWeight *= tipWeight;
    float mask = heightWeight * heightWeight * lerp(0.35, 1.0, tip);
    // UV0.x is authored separately for every disconnected slab: roots stay stiff.
    mask += heightWeight * 0.8 * tipWeight;
    float3 origin = TransformObjectToWorld(float3(0, 0, 0));
    float phase = frac(dot(origin.xz, float2(0.1031, 0.11369))) * 6.2831853;
    float t = lerp(_Time.y, _TreesPreviewClock.x, saturate(_TreesPreviewClock.w));
    float gust = 0.72 + 0.28 * sin(t * 0.17 + phase * 0.37);
    float wave = sin(t * wind.x + phase) + wind.y * tip * sin(t * 1.31 + phase * 1.7);
    float2 delta = normalize(wind.zw) * (shape.w * mask * gust * wave);
    // World-space wind remains coherent across rotations, while phase is per instance.
    return p + mul((float3x3)GetWorldToObjectMatrix(), float3(delta.x, 0, delta.y));
}
#endif
