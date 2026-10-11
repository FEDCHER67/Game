using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // A car for the drive-time model: top speed (m/s), full-throttle acceleration a(v) = A - K * v, the sideways
    // acceleration it takes bends at (ALat), its braking (Brake) and its body width (eats into the road width a bend
    // can be cut through).
    [System.Serializable]
    public struct CarModel
    {
        public float VMax, A, K, ALat, Brake, Width;

        public CarModel(float vmaxKmh, float a, float k, float aLat, float brake, float width)
        {
            VMax = vmaxKmh / 3.6f;
            A = a;
            K = k;
            ALat = aLat;
            Brake = brake;
            Width = width;
        }

        public float Accel(float v) => Mathf.Max(0.05f, A - K * v);
    }

    // The corner-speed model shared by the bake (PoliceBaker: drive times, the T_home fields, the timing report) and the
    // police car (PoliceCarMotor: how fast to take the next bend), so predictions and behaviour match. Port of the
    // design's Python model (roadsim.py, bend_caps / profile_series):
    // - a bend = consecutive polyline vertices turning the same way; its speed cap is v = sqrt(ALat * R_eff) with
    //   R_eff = R_centreline + w_eff / (1 - cos(theta / 2)), w_eff = road width - car width, theta = its total turn;
    // - forward pass at full throttle (1 m sub-steps), backward pass braking at Brake ahead of every cap.
    public static class PoliceRoadModel
    {
        private const float StraightDeg = 0.3f;

        /// <summary>Speed cap (m/s) at every vertex of the polyline. widths: one per segment (pts.Count - 1).</summary>
        public static void BendCaps(IReadOnlyList<Vector2> pts, IReadOnlyList<float> widths, CarModel car, float[] caps)
        {
            int n = pts.Count;
            for (int i = 0; i < n; i++) caps[i] = car.VMax;
            if (n < 3) return;
            float straight = StraightDeg * Mathf.Deg2Rad;
            int k = 1;
            while (k < n - 1)
            {
                float a = TurnAt(pts, k);
                if (Mathf.Abs(a) < straight)
                {
                    k++;
                    continue;
                }
                float sign = Mathf.Sign(a);
                int j = k;
                float total = 0f;
                while (j < n - 1)
                {
                    float aj = TurnAt(pts, j);
                    if (aj * sign <= straight) break;
                    total += Mathf.Abs(aj);
                    j++;
                }
                // Bend vertices k .. j-1; the arc between them; the narrowest road it touches.
                float arc = 0f;
                for (int s = k; s < j - 1; s++) arc += Vector2.Distance(pts[s], pts[s + 1]);
                float w = float.MaxValue;
                for (int s = Mathf.Max(0, k - 1); s < Mathf.Min(widths.Count, j); s++) w = Mathf.Min(w, widths[s]);
                if (w == float.MaxValue) w = 6f;
                float wEff = Mathf.Max(0.6f, w - car.Width);
                float r = total > 1e-6f ? arc / total : 1e9f;
                if (total > 1e-4f) r += wEff / Mathf.Max(1e-6f, 1f - Mathf.Cos(Mathf.Min(total, Mathf.PI * 0.98f) * 0.5f));
                float v = Mathf.Sqrt(car.ALat * r);
                for (int t = k; t < j; t++) caps[t] = Mathf.Min(caps[t], v);
                k = j;
            }
        }

        // Signed turn (radians, + = left) at vertex i.
        private static float TurnAt(IReadOnlyList<Vector2> pts, int i)
        {
            Vector2 a = pts[i] - pts[i - 1], b = pts[i + 1] - pts[i];
            return Mathf.Atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y);
        }

        /// <summary>Speed (V), distance (S) and time (T) at every vertex: full throttle from v0 (or, flying, from the first
        /// cap), every bend at its cap, braking ahead of caps, ending at vEnd (NaN = free). Arrays at least pts.Count long.
        /// Returns the total time.</summary>
        public static float Profile(IReadOnlyList<Vector2> pts, IReadOnlyList<float> widths, CarModel car, float v0, float vEnd, bool flying,
            float[] s, float[] t, float[] v, float[] caps)
        {
            int n = pts.Count;
            if (n == 0) return 0f;
            s[0] = 0f;
            t[0] = 0f;
            if (n < 2)
            {
                v[0] = v0;
                return 0f;
            }
            BendCaps(pts, widths, car, caps);
            v[0] = flying ? Mathf.Min(caps[0], car.VMax) : v0;
            for (int i = 0; i < n - 1; i++)
            {
                float cur = v[i];
                float seg = Vector2.Distance(pts[i], pts[i + 1]);
                int steps = Mathf.Max(1, (int)(seg / 1f));
                float ds = seg / steps;
                for (int k = 0; k < steps; k++) cur = Mathf.Sqrt(cur * cur + 2f * car.Accel(cur) * ds);
                v[i + 1] = Mathf.Min(cur, Mathf.Min(caps[i + 1], car.VMax));
            }
            if (!float.IsNaN(vEnd)) v[n - 1] = Mathf.Min(v[n - 1], vEnd);
            for (int i = n - 2; i >= 0; i--)
            {
                float seg = Vector2.Distance(pts[i], pts[i + 1]);
                v[i] = Mathf.Min(v[i], Mathf.Sqrt(v[i + 1] * v[i + 1] + 2f * car.Brake * seg));
            }
            for (int i = 0; i < n - 1; i++)
            {
                float seg = Vector2.Distance(pts[i], pts[i + 1]);
                float avg = Mathf.Max(0.3f, 0.5f * (v[i] + v[i + 1]));
                s[i + 1] = s[i] + seg;
                t[i + 1] = t[i] + seg / avg;
            }
            return t[n - 1];
        }

        /// <summary>Profile with its own scratch arrays (bake and tests; not per frame).</summary>
        public static float Time(IReadOnlyList<Vector2> pts, IReadOnlyList<float> widths, CarModel car, float v0, float vEnd, bool flying)
        {
            int n = pts.Count;
            if (n < 2) return 0f;
            var s = new float[n];
            var t = new float[n];
            var v = new float[n];
            var caps = new float[n];
            return Profile(pts, widths, car, v0, vEnd, flying, s, t, v, caps);
        }
    }
}
