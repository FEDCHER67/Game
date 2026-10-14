using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Shared by v19 albedo, weather and ambience. A pair of boundaries blends across 60 world metres.
    public static class DistrictBlend19
    {
        public static void Weights(Vector4[] bounds, Vector2 p, float width, float[] result)
        {
            float nearest = float.PositiveInfinity;
            for (int i = 0; i < bounds.Length; i++)
            {
                Vector4 b = bounds[i];
                float x = Mathf.Max(b.x + 15 - p.x, Mathf.Max(0, p.x - b.z + 15));
                float z = Mathf.Max(b.y + 15 - p.y, Mathf.Max(0, p.y - b.w + 15));
                result[i] = Mathf.Sqrt(x*x + z*z);
                nearest = Mathf.Min(nearest, result[i]);
            }
            float sum = 0;
            for (int i = 0; i < bounds.Length; i++)
            {
                float t = Mathf.Clamp01(1 - (result[i] - nearest) / Mathf.Max(width, 1));
                result[i] = t*t*(3-2*t); sum += result[i];
            }
            for (int i = 0; i < bounds.Length; i++) result[i] /= Mathf.Max(sum, .00001f);
        }
    }
}
