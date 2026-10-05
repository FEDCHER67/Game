using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Map.Look
{
    // Plan-space geometry on flat x,y float arrays (the look json layout). System types only, shared by the height model,
    // the splat painter and the mesh builders.
    public static class LookGeom
    {
        public static int Count(float[] pts) => pts == null ? 0 : pts.Length / 2;

        public static float SegDist(float px, float py, float ax, float ay, float bx, float by, out float t)
        {
            float dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
            t = l2 < 1e-9f ? 0f : Clamp01(((px - ax) * dx + (py - ay) * dy) / l2);
            float qx = ax + dx * t - px, qy = ay + dy * t - py;
            return MathF.Sqrt(qx * qx + qy * qy);
        }

        // Even-odd rule, so polygons with a hole bridge still work.
        public static bool Inside(float[] poly, float x, float y)
        {
            int n = Count(poly);
            bool inside = false;
            for (int i = 0, j = n - 1; i < n; j = i++)
            {
                float yi = poly[2 * i + 1], yj = poly[2 * j + 1];
                if ((yi > y) == (yj > y)) continue;
                float xi = poly[2 * i], xj = poly[2 * j];
                if (x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
            }
            return inside;
        }

        public static void Bounds(float[] pts, out float x0, out float y0, out float x1, out float y1)
        {
            x0 = y0 = float.MaxValue;
            x1 = y1 = float.MinValue;
            for (int i = 0; i + 1 < pts.Length; i += 2)
            {
                x0 = MathF.Min(x0, pts[i]);
                x1 = MathF.Max(x1, pts[i]);
                y0 = MathF.Min(y0, pts[i + 1]);
                y1 = MathF.Max(y1, pts[i + 1]);
            }
        }

        public static float SignedArea(float[] poly)
        {
            int n = Count(poly);
            float a = 0f;
            for (int i = 0, j = n - 1; i < n; j = i++)
                a += poly[2 * j] * poly[2 * i + 1] - poly[2 * i] * poly[2 * j + 1];
            return a * 0.5f;
        }

        public static void Centroid(float[] pts, out float cx, out float cy)
        {
            int n = Count(pts);
            cx = cy = 0f;
            if (n == 0) return;
            for (int i = 0; i < n; i++)
            {
                cx += pts[2 * i];
                cy += pts[2 * i + 1];
            }
            cx /= n;
            cy /= n;
        }

        public static float[] Cumulative(float[] pts, bool closed = false)
        {
            int n = Count(pts);
            var cum = new float[closed ? n + 1 : Math.Max(1, n)];
            for (int i = 1; i < cum.Length; i++)
            {
                int a = i - 1, b = i % n;
                cum[i] = cum[i - 1] + Dist(pts[2 * a], pts[2 * a + 1], pts[2 * b], pts[2 * b + 1]);
            }
            return cum;
        }

        public static float Dist(float ax, float ay, float bx, float by)
        {
            float dx = bx - ax, dy = by - ay;
            return MathF.Sqrt(dx * dx + dy * dy);
        }

        // Point and unit tangent at arc length s (closed polylines wrap through the closing edge).
        public static void PointAt(float[] pts, float[] cum, float s, bool closed, out float x, out float y, out float tx, out float ty)
        {
            int n = Count(pts);
            int segs = closed ? n : n - 1;
            x = n > 0 ? pts[0] : 0f;
            y = n > 0 ? pts[1] : 0f;
            tx = 1f;
            ty = 0f;
            if (segs <= 0) return;
            float total = cum[segs];
            s = Math.Clamp(s, 0f, total);
            int k = 0;
            while (k < segs - 1 && cum[k + 1] < s) k++;
            int a = k, b = (k + 1) % n;
            float len = cum[k + 1] - cum[k];
            float t = len > 1e-6f ? (s - cum[k]) / len : 0f;
            float ax = pts[2 * a], ay = pts[2 * a + 1], bx = pts[2 * b], by = pts[2 * b + 1];
            x = ax + (bx - ax) * t;
            y = ay + (by - ay) * t;
            if (len > 1e-6f)
            {
                tx = (bx - ax) / len;
                ty = (by - ay) / len;
            }
        }

        // Even spacing of about `step` metres; both ends kept.
        public static float[] Resample(float[] pts, float step, out float[] arc)
        {
            float[] cum = Cumulative(pts);
            float total = cum[cum.Length - 1];
            int n = Math.Max(1, (int)MathF.Ceiling(total / step));
            var outPts = new float[(n + 1) * 2];
            arc = new float[n + 1];
            for (int i = 0; i <= n; i++)
            {
                float s = total * i / n;
                PointAt(pts, cum, s, false, out float x, out float y, out _, out _);
                outPts[2 * i] = x;
                outPts[2 * i + 1] = y;
                arc[i] = s;
            }
            return outPts;
        }

        public static float[] SubPolyline(float[] pts, float[] cum, float s0, float s1)
        {
            var list = new List<float>();
            PointAt(pts, cum, s0, false, out float x, out float y, out _, out _);
            list.Add(x);
            list.Add(y);
            for (int i = 1; i < cum.Length - 1; i++)
                if (cum[i] > s0 + 1e-3f && cum[i] < s1 - 1e-3f)
                {
                    list.Add(pts[2 * i]);
                    list.Add(pts[2 * i + 1]);
                }
            PointAt(pts, cum, s1, false, out x, out y, out _, out _);
            list.Add(x);
            list.Add(y);
            return list.ToArray();
        }

        public static float DistToPolyline(float[] pts, float x, float y, bool closed, out int seg, out float t)
        {
            int n = Count(pts);
            int segs = closed ? n : n - 1;
            float best = float.MaxValue;
            seg = 0;
            t = 0f;
            for (int i = 0; i < segs; i++)
            {
                int b = (i + 1) % n;
                float d = SegDist(x, y, pts[2 * i], pts[2 * i + 1], pts[2 * b], pts[2 * b + 1], out float tt);
                if (d < best)
                {
                    best = d;
                    seg = i;
                    t = tt;
                }
            }
            return n == 1 ? Dist(x, y, pts[0], pts[1]) : best;
        }

        // Left offset (positive d) of an open polyline with mitred joints, limited so sharp bends do not spike.
        public static float[] Offset(float[] pts, float d)
        {
            int n = Count(pts);
            var o = new float[n * 2];
            for (int i = 0; i < n; i++)
            {
                Normal(pts, i, n, out float nx, out float ny, out float miter);
                o[2 * i] = pts[2 * i] + nx * d * miter;
                o[2 * i + 1] = pts[2 * i + 1] + ny * d * miter;
            }
            return o;
        }

        // Outward offset of a plan-CCW polygon (negative d shrinks it), mitred and limited at sharp corners.
        public static float[] OffsetPolygon(float[] poly, float d)
        {
            int n = Count(poly);
            var o = new float[n * 2];
            for (int i = 0; i < n; i++)
            {
                int a = (i + n - 1) % n, b = (i + 1) % n;
                Dir(poly, a, i, out float t0x, out float t0y);
                Dir(poly, i, b, out float t1x, out float t1y);
                float nx = t0y + t1y, ny = -t0x - t1x, l = MathF.Sqrt(nx * nx + ny * ny);
                if (l < 1e-5f) { nx = t1y; ny = -t1x; l = 1f; }
                nx /= l;
                ny /= l;
                float c = nx * t1y - ny * t1x;
                float m = c > 0.4f ? 1f / c : 2.5f;
                o[2 * i] = poly[2 * i] + nx * d * m;
                o[2 * i + 1] = poly[2 * i + 1] + ny * d * m;
            }
            return o;
        }

        // Left normal at vertex i (averaged over the two adjacent segments) and the miter scale (<= 2.5).
        public static void Normal(float[] pts, int i, int n, out float nx, out float ny, out float miter)
        {
            int a = Math.Max(0, i - 1), b = Math.Min(n - 1, i + 1);
            float t0x = 0f, t0y = 0f, t1x = 0f, t1y = 0f;
            if (i > 0) Dir(pts, a, i, out t0x, out t0y);
            if (i < n - 1) Dir(pts, i, b, out t1x, out t1y);
            if (i == 0) { t0x = t1x; t0y = t1y; }
            if (i == n - 1) { t1x = t0x; t1y = t0y; }
            float tx = t0x + t1x, ty = t0y + t1y, l = MathF.Sqrt(tx * tx + ty * ty);
            if (l < 1e-5f) { tx = t1x; ty = t1y; l = 1f; }
            tx /= l;
            ty /= l;
            nx = -ty;
            ny = tx;
            float c = nx * -t1y + ny * t1x;
            miter = c > 0.4f ? 1f / c : 2.5f;
        }

        public static void Dir(float[] pts, int a, int b, out float dx, out float dy)
        {
            dx = pts[2 * b] - pts[2 * a];
            dy = pts[2 * b + 1] - pts[2 * a + 1];
            float l = MathF.Sqrt(dx * dx + dy * dy);
            if (l < 1e-6f) { dx = 1f; dy = 0f; return; }
            dx /= l;
            dy /= l;
        }

        public static float Clamp01(float v) => v < 0f ? 0f : v > 1f ? 1f : v;

        public static float Smooth01(float t)
        {
            t = Clamp01(t);
            return t * t * (3f - 2f * t);
        }

        public static float Lerp(float a, float b, float t) => a + (b - a) * t;

        // Stable 32-bit hash for seeds and per-object jitter.
        public static uint Hash(uint x)
        {
            x ^= x >> 16;
            x *= 0x7feb352dU;
            x ^= x >> 15;
            x *= 0x846ca68bU;
            x ^= x >> 16;
            return x;
        }

        // FNV-1a over the characters: stable across runtimes (string.GetHashCode is not).
        public static int StableHash(string s)
        {
            uint h = 2166136261U;
            if (s != null)
                foreach (char ch in s)
                {
                    h ^= ch;
                    h *= 16777619U;
                }
            return (int)(h & 0x7FFFFFFF);
        }

        public static float Hash01(int a, int b, int seed)
        {
            uint h = Hash((uint)a * 73856093U ^ Hash((uint)b * 19349663U ^ (uint)seed * 83492791U));
            return (h & 0xFFFFFF) / 16777216f;
        }

        // Value noise in [-1, 1], smooth, deterministic; fbm adds octaves.
        public static float Noise(float x, float y, int seed)
        {
            int ix = (int)MathF.Floor(x), iy = (int)MathF.Floor(y);
            float fx = x - ix, fy = y - iy;
            float a = Hash01(ix, iy, seed), b = Hash01(ix + 1, iy, seed);
            float c = Hash01(ix, iy + 1, seed), d = Hash01(ix + 1, iy + 1, seed);
            float u = fx * fx * (3f - 2f * fx), v = fy * fy * (3f - 2f * fy);
            return Lerp(Lerp(a, b, u), Lerp(c, d, u), v) * 2f - 1f;
        }

        public static float Fbm(float x, float y, int seed, int octaves = 3)
        {
            float sum = 0f, amp = 1f, norm = 0f;
            for (int o = 0; o < octaves; o++)
            {
                sum += Noise(x, y, seed + o * 1013) * amp;
                norm += amp;
                x *= 2.03f;
                y *= 2.03f;
                amp *= 0.5f;
            }
            return sum / norm;
        }

        // Hex "#RRGGBB" -> 0..1 components; bad input gives mid grey.
        public static void Hex(string hex, out float r, out float g, out float b)
        {
            r = g = b = 0.5f;
            if (string.IsNullOrEmpty(hex)) return;
            string s = hex.TrimStart('#');
            if (s.Length < 6) return;
            try
            {
                r = Convert.ToInt32(s.Substring(0, 2), 16) / 255f;
                g = Convert.ToInt32(s.Substring(2, 2), 16) / 255f;
                b = Convert.ToInt32(s.Substring(4, 2), 16) / 255f;
            }
            catch (FormatException)
            {
            }
        }
    }

    public delegate void StampCell(int i, int j, float dist, int seg, float t);

    // Regular sample grid over plan space: sample (i, j) sits at (X0 + i*Dx, Y0 + j*Dy); index = j*Nx + i.
    public sealed class LookGrid
    {
        public readonly int Nx, Ny;
        public readonly float X0, Y0, Dx, Dy;

        public LookGrid(int nx, int ny, float x0, float y0, float dx, float dy)
        {
            Nx = nx;
            Ny = ny;
            X0 = x0;
            Y0 = y0;
            Dx = dx;
            Dy = dy;
        }

        public int Length => Nx * Ny;
        public float X(int i) => X0 + i * Dx;
        public float Y(int j) => Y0 + j * Dy;

        public void Range(float x0, float y0, float x1, float y1, out int i0, out int j0, out int i1, out int j1)
        {
            i0 = Math.Max(0, (int)MathF.Ceiling((x0 - X0) / Dx));
            j0 = Math.Max(0, (int)MathF.Ceiling((y0 - Y0) / Dy));
            i1 = Math.Min(Nx - 1, (int)MathF.Floor((x1 - X0) / Dx));
            j1 = Math.Min(Ny - 1, (int)MathF.Floor((y1 - Y0) / Dy));
        }

        // Calls cell(i, j) for every sample inside the polygon (even-odd scanline fill).
        public void ScanFill(float[] poly, Action<int, int> cell)
        {
            int n = LookGeom.Count(poly);
            if (n < 3) return;
            LookGeom.Bounds(poly, out float bx0, out float by0, out float bx1, out float by1);
            Range(bx0, by0, bx1, by1, out int i0, out int j0, out int i1, out int j1);
            var xs = new List<float>(16);
            for (int j = j0; j <= j1; j++)
            {
                float y = Y(j);
                xs.Clear();
                for (int a = 0, b = n - 1; a < n; b = a++)
                {
                    float ya = poly[2 * a + 1], yb = poly[2 * b + 1];
                    if ((ya > y) == (yb > y)) continue;
                    float xa = poly[2 * a], xb = poly[2 * b];
                    xs.Add(xa + (y - ya) * (xb - xa) / (yb - ya));
                }
                if (xs.Count < 2) continue;
                xs.Sort();
                for (int k = 0; k + 1 < xs.Count; k += 2)
                {
                    int ia = Math.Max(i0, (int)MathF.Ceiling((xs[k] - X0) / Dx));
                    int ib = Math.Min(i1, (int)MathF.Floor((xs[k + 1] - X0) / Dx));
                    for (int i = ia; i <= ib; i++) cell(i, j);
                }
            }
        }

        // Visits every sample within `radius` of each segment; a sample near several segments is visited once per segment.
        public void Stamp(float[] pts, bool closed, float radius, StampCell cell)
        {
            int n = LookGeom.Count(pts);
            if (n == 1)
            {
                StampSegment(pts[0], pts[1], pts[0], pts[1], 0, radius, cell);
                return;
            }
            int segs = closed ? n : n - 1;
            for (int s = 0; s < segs; s++)
            {
                int b = (s + 1) % n;
                StampSegment(pts[2 * s], pts[2 * s + 1], pts[2 * b], pts[2 * b + 1], s, radius, cell);
            }
        }

        public void StampSegment(float ax, float ay, float bx, float by, int seg, float radius, StampCell cell)
        {
            Range(MathF.Min(ax, bx) - radius, MathF.Min(ay, by) - radius, MathF.Max(ax, bx) + radius, MathF.Max(ay, by) + radius,
                out int i0, out int j0, out int i1, out int j1);
            for (int j = j0; j <= j1; j++)
            {
                float y = Y(j);
                for (int i = i0; i <= i1; i++)
                {
                    float d = LookGeom.SegDist(X(i), y, ax, ay, bx, by, out float t);
                    if (d <= radius) cell(i, j, d, seg, t);
                }
            }
        }

        // Bilinear sample of a field laid out on this grid; outside the grid the edge value is used.
        public float Sample(float[] field, float x, float y)
        {
            float gx = Math.Clamp((x - X0) / Dx, 0f, Nx - 1.001f), gy = Math.Clamp((y - Y0) / Dy, 0f, Ny - 1.001f);
            int i = (int)gx, j = (int)gy;
            float fx = gx - i, fy = gy - j;
            int k = j * Nx + i;
            float a = field[k], b = field[k + 1], c = field[k + Nx], d = field[k + Nx + 1];
            return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
        }

        // Separable box blur (radius in samples per axis), run `passes` times; values outside the grid repeat the edge.
        public static void Blur(float[] f, int nx, int ny, int rx, int ry, int passes)
        {
            var tmp = new float[Math.Max(nx, ny)];
            for (int p = 0; p < passes; p++)
            {
                if (rx > 0)
                    for (int j = 0; j < ny; j++)
                    {
                        int row = j * nx;
                        float sum = 0f;
                        for (int k = -rx; k <= rx; k++) sum += f[row + Math.Clamp(k, 0, nx - 1)];
                        for (int i = 0; i < nx; i++)
                        {
                            tmp[i] = sum / (2 * rx + 1);
                            sum += f[row + Math.Min(nx - 1, i + rx + 1)] - f[row + Math.Max(0, i - rx)];
                        }
                        Array.Copy(tmp, 0, f, row, nx);
                    }
                if (ry > 0)
                    for (int i = 0; i < nx; i++)
                    {
                        float sum = 0f;
                        for (int k = -ry; k <= ry; k++) sum += f[Math.Clamp(k, 0, ny - 1) * nx + i];
                        for (int j = 0; j < ny; j++)
                        {
                            tmp[j] = sum / (2 * ry + 1);
                            sum += f[Math.Min(ny - 1, j + ry + 1) * nx + i] - f[Math.Max(0, j - ry) * nx + i];
                        }
                        for (int j = 0; j < ny; j++) f[j * nx + i] = tmp[j];
                    }
            }
        }
    }
}
