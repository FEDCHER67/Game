using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Map.Look
{
    // Terrain splat weights from the look json's soft ground polygons (district bases, fields, yards, sites, shoulders),
    // painted in priority order. Edges are blurred over the polygon's `edge` metres and broken up with noise, so district
    // borders read as organic blends of grass, dirt and gravel rather than lines (no fences, no hard seams).
    // Also paints sand under the sea and lake and gravel in river/canal channels. Pure C#; result is [z, x, layer].
    public static class GroundSplat
    {
        public static float[,,] Bake(LookData data, int res, out string[] layers)
        {
            LookTerrain t = data.terrain;
            layers = t.layers.Length > 0 ? t.layers : data.soft_layers;
            int nl = layers.Length;
            var grid = new LookGrid(res, res, t.x0 + t.sx / res * 0.5f, t.y0 + t.sy / res * 0.5f, t.sx / res, t.sy / res);
            var w = new float[res, res, nl];
            int def = Math.Max(0, Array.IndexOf(layers, string.IsNullOrEmpty(t.@default) ? data.ground_default : t.@default));
            for (int z = 0; z < res; z++)
                for (int x = 0; x < res; x++)
                    w[z, x, def] = 1f;
            int seed = data.seed * 17 + 3;
            var items = new List<LookGround>();
            foreach (LookGround g in data.ground)
                if (g.soft && Array.IndexOf(layers, g.mat) >= 0)
                    items.Add(g);
            items.Sort((a, b) => a.prio.CompareTo(b.prio));
            foreach (LookGround g in items)
                Paint(grid, w, Array.IndexOf(layers, g.mat), g.pts, MathF.Max(0.5f, g.edge), seed);
            // Macro variation: large soft patches of a sister layer that shares the texture at a different tile size
            // (meadow 3 m -> worn grass 5.3 m, park grass 3.7 m -> lawn 2.5 m), so the tile grid of a big field never
            // lines up over more than a few repeats and the ground does not read as one stamped pattern.
            Macro(grid, w, Array.IndexOf(layers, "meadow"), Array.IndexOf(layers, "worn_grass"), 0.4f, 60f, seed + 11);
            Macro(grid, w, Array.IndexOf(layers, "park_grass"), Array.IndexOf(layers, "lawn"), 0.35f, 35f, seed + 12);
            int sand = Array.IndexOf(layers, "sand"), gravel = Array.IndexOf(layers, "gravel");
            if (sand >= 0)
            {
                Paint(grid, w, sand, data.sea.pts, 3f, seed + 1);
                foreach (LookWater lake in data.water)
                    if (lake.kind == "lake")
                        Paint(grid, w, sand, lake.pts, 2f, seed + 2);
            }
            if (gravel >= 0)
                foreach (LookWater river in data.water)
                    if (river.kind != "lake")
                    {
                        HeightModel.Channel(river, out float top, out _, out _);
                        PaintBand(grid, w, gravel, river.pts, top + 0.5f, 1.5f, seed + 3);
                    }
            return w;
        }

        // Moves up to `amount` of layer `from` to layer `to` in low-frequency noise patches of about `scale` metres.
        private static void Macro(LookGrid grid, float[,,] w, int from, int to, float amount, float scale, int seed)
        {
            if (from < 0 || to < 0) return;
            int nz = w.GetLength(0), nx = w.GetLength(1);
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    float have = w[z, x, from];
                    if (have <= 0.001f) continue;
                    float n = LookGeom.Fbm(grid.X(x) / scale, grid.Y(z) / scale, seed, 3);
                    float m = LookGeom.Smooth01((n + 0.1f) * 2.2f) * amount * have;
                    w[z, x, from] -= m;
                    w[z, x, to] += m;
                }
        }

        // Blurred polygon mask with a noisy threshold, painted over whatever is below.
        private static void Paint(LookGrid grid, float[,,] w, int layer, float[] poly, float edge, int seed)
        {
            if (layer < 0 || LookGeom.Count(poly) < 3) return;
            float pad = edge + 2f;
            LookGeom.Bounds(poly, out float bx0, out float by0, out float bx1, out float by1);
            grid.Range(bx0 - pad, by0 - pad, bx1 + pad, by1 + pad, out int i0, out int j0, out int i1, out int j1);
            if (i1 < i0 || j1 < j0) return;
            int nx = i1 - i0 + 1, ny = j1 - j0 + 1;
            var mask = new float[nx * ny];
            var local = new LookGrid(nx, ny, grid.X(i0), grid.Y(j0), grid.Dx, grid.Dy);
            local.ScanFill(poly, (i, j) => mask[j * nx + i] = 1f);
            int rx = (int)(edge * 0.5f / grid.Dx), ry = (int)(edge * 0.5f / grid.Dy);
            if (rx > 0 || ry > 0) LookGrid.Blur(mask, nx, ny, rx, ry, 2);
            float amp = edge >= 8f ? 0.45f : edge >= 2f ? 0.25f : 0.1f;
            float scale = MathF.Max(6f, edge);
            for (int j = 0; j < ny; j++)
                for (int i = 0; i < nx; i++)
                {
                    float m = mask[j * nx + i];
                    if (m <= 0.001f) continue;
                    float x = local.X(i), y = local.Y(j);
                    if (m < 0.999f)
                    {
                        float n = LookGeom.Fbm(x / scale, y / scale, seed + layer * 97, 2);
                        m = LookGeom.Smooth01((m - 0.5f) * 1.6f + 0.5f + n * amp);
                    }
                    if (m <= 0.001f) continue;
                    Blend(w, j0 + j, i0 + i, layer, m);
                }
        }

        // Band along a polyline: full inside `half`, soft outside over `soft` metres.
        private static void PaintBand(LookGrid grid, float[,,] w, int layer, float[] line, float half, float soft, int seed)
        {
            var best = new Dictionary<int, float>();
            grid.Stamp(line, false, half + soft, (i, j, d, s, t) =>
            {
                int k = j * grid.Nx + i;
                float m = d <= half ? 1f : 1f - LookGeom.Smooth01((d - half) / soft);
                if (!best.TryGetValue(k, out float old) || m > old) best[k] = m;
            });
            foreach (var kv in best)
            {
                int i = kv.Key % grid.Nx, j = kv.Key / grid.Nx;
                float n = LookGeom.Noise(grid.X(i) / 4f, grid.Y(j) / 4f, seed) * 0.2f;
                Blend(w, j, i, layer, LookGeom.Clamp01(kv.Value + n));
            }
        }

        private static void Blend(float[,,] w, int z, int x, int layer, float m)
        {
            int nl = w.GetLength(2);
            float keep = 1f - m;
            for (int l = 0; l < nl; l++) w[z, x, l] *= keep;
            w[z, x, layer] += m;
        }
    }
}
