using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Map.Look
{
    // Terrain heights of the look build, in metres, on the heightmap grid (plan space, ground level 0). Pure C#.
    // Base field: elite hill, beach/sea profile, lake/river/canal channels, +-0.5 m rural noise, boundary berm.
    // Constraints on top, in priority yard < building < road: roads get smoothed, grade-limited centreline profiles
    // pinned to junction heights, buildings a flat pad at their entrance height, yards a soft terrace to their pad.
    // Blends widen with the height difference so side slopes stay under ~20 degrees (van parity: slopes <= 22).
    public sealed class HeightModel
    {
        public sealed class RoadProfile
        {
            public string Id, Road, Cls;
            public float W;
            public float[] Xy, S, H;
            public float MaxGrade;
        }

        // Pads that sit more than WallDrop off the natural ground get a retaining wall instead of a long bank.
        public sealed class RetainingWall
        {
            public string BuildingId;
            public float[] Ring;
        }

        public readonly LookData Data;
        public readonly LookGrid Grid;
        public float[] Heights;
        public float MinHeight, MaxHeight;
        public RoadProfile[] Roads = new RoadProfile[0];
        public RoadProfile Rail;
        public readonly Dictionary<string, float> JunctionHeights = new();
        public readonly Dictionary<string, float> Pads = new();
        public readonly Dictionary<string, float> YardPads = new();
        public readonly List<RetainingWall> Walls = new();
        public readonly List<string> Warnings = new();
        public float MaxRoadGrade;

        public float RuralNoise = 0.5f;
        public float RoadShoulder = 1f, RoadBlend = 8f, RoadBlendMax = 24f, RoadGrade = 0.12f, RoadSigma = 8f;
        public float BuildingMargin = 1.5f, BuildingBlend = 5f, BuildingBlendMax = 8f, WallDrop = 1.2f, WallOffset = 1.2f;
        public float YardBlend = 4f, YardBlendMax = 12f, YardTerrace = 0.6f;
        public float SideSlopeDeg = 20f;

        private float[] smooth;
        private bool[] insideBoundary;
        private readonly List<(float x0, float y0, float x1, float y1, float ax, float ay, float bx, float by, float hw)> bridges = new();

        private static readonly HashSet<string> RuralDistricts = new() { "forest", "village", "transition", "fields" };

        public HeightModel(LookData data, int resolution = 0)
        {
            Data = data;
            LookTerrain t = data.terrain;
            int res = resolution > 0 ? resolution : Math.Max(33, (int)t.heightmap);
            Grid = new LookGrid(res, res, t.x0, t.y0, t.sx / (res - 1), t.sy / (res - 1));
        }

        public float Height(float x, float y) => Grid.Sample(Heights, x, y);

        // Hill and coast only: what roads follow before they are smoothed.
        public float SmoothHeight(float x, float y) => Grid.Sample(smooth, x, y);

        public void Bake()
        {
            int n = Grid.Length;
            smooth = new float[n];
            BakeHills(smooth);
            BakeCoast(smooth);
            var baseField = new float[n];
            for (int k = 0; k < n; k++) baseField[k] = smooth[k];
            BakeNoise(baseField);
            BakeBerm(baseField);
            BakeWater(baseField);
            CollectBridges();

            BakeRoadProfiles();
            var roadW = new float[n];
            var roadH = new float[n];
            StampRoads(baseField, roadW, roadH);

            var first = new float[n];
            for (int k = 0; k < n; k++) first[k] = LookGeom.Lerp(baseField[k], roadH[k], roadW[k]);
            ComputePads(first);

            var field = (float[])baseField.Clone();
            ApplyYards(baseField, field);
            var core = new bool[n];
            ApplyBuildings(baseField, field, core);
            // Pad cores (footprint + margin, or inside a retaining wall) stay flat at the pad: the road blend is already
            // in the pad height, so applying it again would tilt floors and bury doors near roads.
            for (int k = 0; k < n; k++)
                if (!core[k] || roadW[k] >= 0.999f)
                    field[k] = LookGeom.Lerp(field[k], roadH[k], roadW[k]);
            Heights = field;
            MinHeight = float.MaxValue;
            MaxHeight = float.MinValue;
            foreach (float h in Heights)
            {
                MinHeight = MathF.Min(MinHeight, h);
                MaxHeight = MathF.Max(MaxHeight, h);
            }
        }

        private void BakeHills(float[] f)
        {
            foreach (LookHill hill in Data.hills)
            {
                if (hill.rx <= 0f || hill.ry <= 0f) continue;
                Grid.Range(hill.x - hill.rx, hill.y - hill.ry, hill.x + hill.rx, hill.y + hill.ry, out int i0, out int j0, out int i1, out int j1);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        float dx = (Grid.X(i) - hill.x) / hill.rx, dy = (Grid.Y(j) - hill.y) / hill.ry;
                        float r = MathF.Sqrt(dx * dx + dy * dy);
                        if (r >= 1f) continue;
                        f[j * Grid.Nx + i] += hill.h * 0.5f * (1f + MathF.Cos(MathF.PI * r));
                    }
            }
        }

        // Beach: -1.5 t^3 from the land edge (t = 0) to the sea edge (t = 1); sea bed drops to `bed`; shores outside fade.
        private void BakeCoast(float[] f)
        {
            int n = Grid.Length;
            insideBoundary = new bool[n];
            Grid.ScanFill(Data.boundary.pts, (i, j) => insideBoundary[j * Grid.Nx + i] = true);
            LookBeach beach = Data.beach;
            LookSea sea = Data.sea;
            if (LookGeom.Count(sea.pts) < 3 && LookGeom.Count(beach.pts) < 3) return;
            var inBeach = new bool[n];
            var inSea = new bool[n];
            Grid.ScanFill(beach.pts, (i, j) => inBeach[j * Grid.Nx + i] = true);
            Grid.ScanFill(sea.pts, (i, j) => inSea[j * Grid.Nx + i] = true);
            var dLand = Filled(n, 999f);
            var dSea = Filled(n, 999f);
            var dOutline = Filled(n, 999f);
            const float reach = 90f;
            Grid.Stamp(beach.land, false, reach, (i, j, d, s, t) => Min(dLand, j * Grid.Nx + i, d));
            Grid.Stamp(beach.sea, false, reach, (i, j, d, s, t) => Min(dSea, j * Grid.Nx + i, d));
            Grid.Stamp(sea.pts, true, 70f, (i, j, d, s, t) => Min(dOutline, j * Grid.Nx + i, d));
            float bed = sea.bed < 0f ? sea.bed : -4f;
            // Open sea: outside the map, the side of the sea polygon that faces away from the coast (its open edges,
            // see OpenSeaVertex) sinks to the sea bed all the way to the terrain edge, so the water meets the sky
            // instead of a band of land on the far side. Depth there grows with the distance from the closed (coast)
            // edges only, so no shallow ridge runs along the open edges.
            var dOpen = Filled(n, 999f);
            var dClosed = Filled(n, 999f);
            int ns = LookGeom.Count(sea.pts);
            for (int e = 0; e < ns; e++)
            {
                int a = e, c = (e + 1) % ns;
                float[] target = OpenSeaVertex(Data, a) && OpenSeaVertex(Data, c) ? dOpen : dClosed;
                Grid.StampSegment(sea.pts[2 * a], sea.pts[2 * a + 1], sea.pts[2 * c], sea.pts[2 * c + 1], e, OpenSeaReach,
                    (i, j, d, s, t) => Min(target, j * Grid.Nx + i, d));
            }
            for (int k = 0; k < n; k++)
            {
                if (inBeach[k])
                {
                    float t = dLand[k] / MathF.Max(0.01f, dLand[k] + dSea[k]);
                    f[k] += -1.5f * t * t * t;
                }
                else if (inSea[k] || dSea[k] < 2f)
                {
                    // Also the thin gaps between the beach and sea polygons (they do not share an exact edge).
                    float d = MathF.Min(dSea[k], dClosed[k]);
                    f[k] += LookGeom.Lerp(-1.5f, bed, LookGeom.Smooth01(d / 40f));
                }
                else if (!insideBoundary[k] && dOpen[k] < dClosed[k])
                {
                    f[k] += LookGeom.Lerp(-1.5f, bed, LookGeom.Smooth01(dClosed[k] / 40f));
                }
                else if (!insideBoundary[k] && dOutline[k] < 70f)
                {
                    f[k] += LookGeom.Lerp(-1.5f, 0f, LookGeom.Smooth01(dOutline[k] / 30f));
                }
            }
        }

        public const float OpenSeaReach = 400f;

        // A sea polygon vertex on the open-water side: outside the map, away from the beach and the map boundary.
        // WaterBuilder extends the sea surface outward from edges between two such vertices.
        public static bool OpenSeaVertex(LookData d, int i)
        {
            float x = d.sea.pts[2 * i], y = d.sea.pts[2 * i + 1];
            if (LookGeom.Inside(d.boundary.pts, x, y)) return false;
            if (LookGeom.Count(d.beach.sea) >= 2 && LookGeom.DistToPolyline(d.beach.sea, x, y, false, out _, out _) < 15f) return false;
            if (LookGeom.Count(d.beach.pts) >= 3 && LookGeom.DistToPolyline(d.beach.pts, x, y, true, out _, out _) < 15f) return false;
            return LookGeom.DistToPolyline(d.boundary.pts, x, y, true, out _, out _) > 15f;
        }

        private void BakeNoise(float[] f)
        {
            if (RuralNoise <= 0f) return;
            int n = Grid.Length;
            var mask = new float[n];
            foreach (LookDistrict d in Data.districts)
                if (RuralDistricts.Contains(d.id))
                    Grid.ScanFill(d.pts, (i, j) => mask[j * Grid.Nx + i] = 1f);
            LookGrid.Blur(mask, Grid.Nx, Grid.Ny, (int)(8f / Grid.Dx), (int)(8f / Grid.Dy), 2);
            int seed = Data.seed * 31 + 7;
            for (int j = 0; j < Grid.Ny; j++)
                for (int i = 0; i < Grid.Nx; i++)
                {
                    int k = j * Grid.Nx + i;
                    if (mask[k] <= 0f) continue;
                    f[k] += LookGeom.Fbm(Grid.X(i) / 45f, Grid.Y(j) / 45f, seed) * RuralNoise * mask[k];
                }
        }

        // Inland edges rise into a berm; everything outside the boundary (but not the coast) sits on it.
        private void BakeBerm(float[] f)
        {
            LookBoundary b = Data.boundary;
            int count = LookGeom.Count(b.pts);
            if (count < 3) return;
            int n = Grid.Length;
            float bermH = b.berm_h > 0f ? b.berm_h : 2.5f, ramp = MathF.Max(12f, b.band * 3f);
            var dInland = Filled(n, 999f);
            var dAll = Filled(n, 999f);
            for (int e = 0; e < count; e++)
            {
                int a = e, c = (e + 1) % count;
                bool coast = e < b.coast.Length && b.coast[e] == 1;
                float ax = b.pts[2 * a], ay = b.pts[2 * a + 1], cx = b.pts[2 * c], cy = b.pts[2 * c + 1];
                Grid.StampSegment(ax, ay, cx, cy, e, 70f, (i, j, d, s, t) => Min(dAll, j * Grid.Nx + i, d));
                if (!coast) Grid.StampSegment(ax, ay, cx, cy, e, ramp, (i, j, d, s, t) => Min(dInland, j * Grid.Nx + i, d));
            }
            LookBeach beach = Data.beach;
            var inCoast = new bool[n];
            Grid.ScanFill(beach.pts, (i, j) => inCoast[j * Grid.Nx + i] = true);
            Grid.ScanFill(Data.sea.pts, (i, j) => inCoast[j * Grid.Nx + i] = true);
            for (int k = 0; k < n; k++)
            {
                if (inCoast[k]) continue;
                if (insideBoundary[k])
                {
                    if (dInland[k] < ramp) f[k] += bermH * (1f - LookGeom.Smooth01(dInland[k] / ramp));
                }
                else if (f[k] > -0.5f)
                {
                    f[k] += bermH + MathF.Min(dAll[k], 70f) * 0.04f;
                }
            }
        }

        private void BakeWater(float[] f)
        {
            foreach (LookWater w in Data.water)
            {
                if (w.kind == "lake")
                {
                    float bed = -MathF.Abs(w.depth), ratio = w.bank > 0f ? w.bank : 4f;
                    var inside = new bool[Grid.Length];
                    Grid.ScanFill(w.pts, (i, j) => inside[j * Grid.Nx + i] = true);
                    var dEdge = Filled(Grid.Length, 999f);
                    float reach = -bed * ratio + 2f;
                    Grid.Stamp(w.pts, true, reach, (i, j, d, s, t) => Min(dEdge, j * Grid.Nx + i, d));
                    for (int k = 0; k < f.Length; k++)
                        if (inside[k])
                            f[k] = MathF.Min(f[k], MathF.Max(bed, -dEdge[k] / ratio));
                }
                else
                {
                    Channel(w, out float top, out float bottom, out float bed);
                    bool linear = w.kind == "canal";
                    Grid.Stamp(w.pts, false, top, (i, j, d, s, t) =>
                    {
                        int k = j * Grid.Nx + i;
                        float u = (d - bottom) / MathF.Max(0.1f, top - bottom);
                        float h = d <= bottom ? bed : LookGeom.Lerp(bed, 0f, linear ? LookGeom.Clamp01(u) : LookGeom.Smooth01(u));
                        f[k] = MathF.Min(f[k], h);
                    });
                }
            }
        }

        // River/canal cross-section: ground (0) beyond `top`, flat bed inside `bottom`; natural banks are S-shaped,
        // concrete canal banks straight. `depth` is the bed depth below ground (water depth = level + depth).
        public static void Channel(LookWater w, out float top, out float bottom, out float bed)
        {
            bed = -MathF.Abs(w.depth);
            bool canal = w.kind == "canal";
            float width = MathF.Max(w.w, w.wet_w);
            top = canal ? width / 2f : width / 2f + w.bank / 2f;
            bottom = MathF.Max(0.5f, top - (-bed) * (canal ? 2.8f : 4.5f));
        }

        // Half width of the water surface of a river/canal (for the water ribbon), plus a little overlap into the banks.
        public static float WaterHalfWidth(LookWater w)
        {
            Channel(w, out float top, out float bottom, out float bed);
            if (w.level <= bed) return bottom;
            float frac = (w.level - bed) / (0f - bed);
            float u = w.kind == "canal" ? frac : InverseSmooth(frac);
            return bottom + u * (top - bottom) + 0.4f;
        }

        private static float InverseSmooth(float y)
        {
            float lo = 0f, hi = 1f;
            for (int k = 0; k < 20; k++)
            {
                float m = (lo + hi) / 2f;
                if (LookGeom.Smooth01(m) < y) lo = m;
                else hi = m;
            }
            return (lo + hi) / 2f;
        }

        private void CollectBridges()
        {
            bridges.Clear();
            foreach (LookCrossing c in Data.crossings)
            {
                if (c.kind != "bridge" || LookGeom.Count(c.pts) < 2) continue;
                float ax = c.pts[0], ay = c.pts[1], bx = c.pts[c.pts.Length - 2], by = c.pts[c.pts.Length - 1];
                float hw = c.w / 2f + 3f;
                bridges.Add((MathF.Min(ax, bx) - hw, MathF.Min(ay, by) - hw, MathF.Max(ax, bx) + hw, MathF.Max(ay, by) + hw, ax, ay, bx, by, hw));
            }
        }

        // True inside a bridge span: the channel under it is left alone and the deck carries the road.
        public bool InBridge(float x, float y, float extraAcross = 0f)
        {
            foreach (var b in bridges)
            {
                if (x < b.x0 - extraAcross || x > b.x1 + extraAcross || y < b.y0 - extraAcross || y > b.y1 + extraAcross) continue;
                float dx = b.bx - b.ax, dy = b.by - b.ay, len = MathF.Sqrt(dx * dx + dy * dy);
                if (len < 0.1f) continue;
                float along = ((x - b.ax) * dx + (y - b.ay) * dy) / len, across = MathF.Abs((x - b.ax) * dy - (y - b.ay) * dx) / len;
                if (along > 0.5f && along < len - 0.5f && across < b.hw + extraAcross) return true;
            }
            return false;
        }

        private void BakeRoadProfiles()
        {
            JunctionHeights.Clear();
            foreach (LookJunction j in Data.junctions)
            {
                float h = 0f;
                for (int k = 0; k < 5; k++)
                {
                    float a = k * MathF.PI * 2f / 4f;
                    float r = k == 4 ? 0f : 4f;
                    h += SmoothHeight(j.x + MathF.Cos(a) * r, j.y + MathF.Sin(a) * r);
                }
                JunctionHeights[j.id] = h / 5f;
            }
            CollectJoins();
            var list = new List<RoadProfile>();
            MaxRoadGrade = 0f;
            foreach (LookRoad r in Data.roads)
            {
                if (LookGeom.Count(r.pts) < 2) continue;
                RoadProfile p = Profile(r.id, r.road, r.cls, r.w, r.pts, RoadSigma, RoadGrade, true);
                list.Add(p);
                MaxRoadGrade = MathF.Max(MaxRoadGrade, p.MaxGrade);
                if (p.MaxGrade > 0.36f) Warnings.Add($"road {r.id}: grade {p.MaxGrade * 100f:0}% (over 20 degrees)");
            }
            Roads = list.ToArray();
            Rail = LookGeom.Count(Data.rail.pts) >= 2 ? Profile("RAIL", "RAIL", "rail", Data.rail.w, Data.rail.pts, 15f, 0.03f, false) : null;
            if (MaxRoadGrade > RoadGrade + 0.01f)
                Warnings.Add($"roads: steepest grade {MaxRoadGrade * 100f:0}% (target {RoadGrade * 100f:0}%) where the hill or a junction forces it");
        }

        private RoadProfile Profile(string id, string road, string cls, float w, float[] pts, float sigma, float grade, bool pin)
        {
            float[] xy = LookGeom.Resample(pts, 2f, out float[] arc);
            int n = arc.Length;
            var raw = new float[n];
            for (int i = 0; i < n; i++) raw[i] = SmoothHeight(xy[2 * i], xy[2 * i + 1]);
            var h = new float[n];
            for (int i = 0; i < n; i++)
            {
                float sum = 0f, wsum = 0f;
                for (int k = 0; k < n; k++)
                {
                    float ds = arc[k] - arc[i];
                    if (MathF.Abs(ds) > sigma * 3f) continue;
                    float g = MathF.Exp(-ds * ds / (2f * sigma * sigma));
                    sum += raw[k] * g;
                    wsum += g;
                }
                h[i] = sum / wsum;
            }
            bool pin0 = false, pin1 = false;
            if (pin)
            {
                float total = arc[n - 1];
                pin0 = PinHeight(road, xy[0], xy[1], out float h0);
                pin1 = PinHeight(road, xy[2 * (n - 1)], xy[2 * (n - 1) + 1], out float h1);
                float d0 = pin0 ? h0 - h[0] : 0f, d1 = pin1 ? h1 - h[n - 1] : 0f;
                if (pin0 && !pin1) d1 = d0 * MathF.Max(0f, 1f - total / 60f);
                if (pin1 && !pin0) d0 = d1 * MathF.Max(0f, 1f - total / 60f);
                for (int i = 0; i < n; i++) h[i] += LookGeom.Lerp(d0, d1, total > 0f ? arc[i] / total : 0f);
            }
            for (int pass = 0; pass < 40; pass++)
            {
                bool changed = false;
                for (int i = 0; i + 1 < n; i++)
                {
                    float lim = grade * (arc[i + 1] - arc[i]), diff = h[i + 1] - h[i];
                    if (MathF.Abs(diff) <= lim + 1e-4f) continue;
                    float excess = (MathF.Abs(diff) - lim) * MathF.Sign(diff);
                    bool lockA = pin0 && i == 0, lockB = pin1 && i + 1 == n - 1;
                    if (lockA && lockB) continue;
                    if (lockA) h[i + 1] -= excess;
                    else if (lockB) h[i] += excess;
                    else
                    {
                        h[i] += excess * 0.5f;
                        h[i + 1] -= excess * 0.5f;
                    }
                    changed = true;
                }
                if (!changed) break;
            }
            float maxGrade = 0f;
            for (int i = 0; i + 1 < n; i++)
                maxGrade = MathF.Max(maxGrade, MathF.Abs(h[i + 1] - h[i]) / MathF.Max(0.01f, arc[i + 1] - arc[i]));
            return new RoadProfile { Id = id, Road = road, Cls = cls, W = w, Xy = xy, S = arc, H = h, MaxGrade = maxGrade };
        }

        private bool PinHeight(string road, float x, float y, out float h)
        {
            if (JunctionPin(road, x, y, out h)) return true;
            bool found = false;
            float best = JoinRadius;
            foreach (var jn in joins)
            {
                float d = LookGeom.Dist(x, y, jn.x, jn.y);
                if (d >= best) continue;
                best = d;
                h = jn.h;
                found = true;
            }
            return found;
        }

        private bool JunctionPin(string road, float x, float y, out float h)
        {
            h = 0f;
            float best = 8f;
            bool found = false;
            foreach (LookJunction j in Data.junctions)
            {
                float d = LookGeom.Dist(x, y, j.x, j.y);
                if (d >= best || Array.IndexOf(j.roads, road) < 0) continue;
                best = d;
                h = JunctionHeights[j.id];
                found = true;
            }
            return found;
        }

        // Road pieces that meet end to end with no junction (one road running on as another) share one height at the
        // join, so their profiles cannot step apart there. A join that touches a pinned end takes the junction height.
        private const float JoinRadius = 1.5f;
        private readonly List<(float x, float y, float h)> joins = new();

        private void CollectJoins()
        {
            joins.Clear();
            var ends = new List<(string road, float x, float y)>();
            foreach (LookRoad r in Data.roads)
            {
                int c = LookGeom.Count(r.pts);
                if (c < 2) continue;
                ends.Add((r.road, r.pts[0], r.pts[1]));
                ends.Add((r.road, r.pts[2 * c - 2], r.pts[2 * c - 1]));
            }
            var used = new bool[ends.Count];
            for (int a = 0; a < ends.Count; a++)
            {
                if (used[a]) continue;
                var cluster = new List<int> { a };
                used[a] = true;
                for (int q = 0; q < cluster.Count; q++)
                    for (int b = 0; b < ends.Count; b++)
                        if (!used[b] && LookGeom.Dist(ends[cluster[q]].x, ends[cluster[q]].y, ends[b].x, ends[b].y) < JoinRadius)
                        {
                            used[b] = true;
                            cluster.Add(b);
                        }
                if (cluster.Count < 2) continue;
                float sx = 0f, sy = 0f, sh = 0f, pinH = 0f;
                bool anyPinned = false, allPinned = true;
                foreach (int e in cluster)
                {
                    sx += ends[e].x;
                    sy += ends[e].y;
                    sh += SmoothHeight(ends[e].x, ends[e].y);
                    bool pinned = JunctionPin(ends[e].road, ends[e].x, ends[e].y, out float ph);
                    if (pinned && !anyPinned) pinH = ph;
                    anyPinned |= pinned;
                    allPinned &= pinned;
                }
                if (allPinned) continue;
                joins.Add((sx / cluster.Count, sy / cluster.Count, anyPinned ? pinH : sh / cluster.Count));
            }
        }

        // Height of a road piece's profile at arc length s (for draping and bridge decks).
        public static float ProfileHeight(RoadProfile p, float s)
        {
            int n = p.S.Length;
            if (n == 1 || s <= 0f) return p.H[0];
            if (s >= p.S[n - 1]) return p.H[n - 1];
            int lo = 0, hi = n - 1;
            while (hi - lo > 1)
            {
                int m = (lo + hi) / 2;
                if (p.S[m] <= s) lo = m;
                else hi = m;
            }
            float t = (s - p.S[lo]) / MathF.Max(1e-4f, p.S[hi] - p.S[lo]);
            return LookGeom.Lerp(p.H[lo], p.H[hi], t);
        }

        private void StampRoads(float[] under, float[] weight, float[] height)
        {
            int n = Grid.Length;
            var sumW = new float[n];
            var sumWH = new float[n];
            float k = 1.5f / MathF.Tan(SideSlopeDeg * MathF.PI / 180f);
            void Add(int i, int j, float d, float core, float target)
            {
                int idx = j * Grid.Nx + i;
                float bw = Math.Clamp(MathF.Abs(target - under[idx]) * k, RoadBlend, RoadBlendMax);
                float w = d <= core ? 1f : 1f - LookGeom.Smooth01((d - core) / bw);
                if (w <= 0f) return;
                // Inside a span the channel is left alone: the deck carries the road, and channel cells beside the deck
                // must not be filled by the road blend either.
                if (bridges.Count > 0 && InBridge(Grid.X(i), Grid.Y(j), under[idx] < 0f ? RoadBlendMax : 0f)) return;
                float w4 = w * w * w * w;
                sumW[idx] += w4;
                sumWH[idx] += w4 * target;
                if (w > weight[idx]) weight[idx] = w;
            }
            var all = new List<RoadProfile>(Roads);
            if (Rail != null) all.Add(Rail);
            foreach (RoadProfile p in all)
            {
                float core = p.W / 2f + RoadShoulder;
                int count = p.S.Length;
                for (int s = 0; s + 1 < count; s++)
                {
                    float h0 = p.H[s], h1 = p.H[s + 1];
                    Grid.StampSegment(p.Xy[2 * s], p.Xy[2 * s + 1], p.Xy[2 * s + 2], p.Xy[2 * s + 3], s, core + RoadBlendMax,
                        (i, j, d, seg, t) => Add(i, j, d, core, LookGeom.Lerp(h0, h1, t)));
                }
            }
            foreach (LookJunction jn in Data.junctions)
            {
                float rad = 0f;
                for (int q = 0; q + 1 < jn.pts.Length; q += 2) rad = MathF.Max(rad, LookGeom.Dist(jn.x, jn.y, jn.pts[q], jn.pts[q + 1]));
                float core = rad + RoadShoulder, hj = JunctionHeights[jn.id];
                Grid.StampSegment(jn.x, jn.y, jn.x, jn.y, 0, core + RoadBlendMax, (i, j, d, seg, t) => Add(i, j, d, core, hj));
            }
            for (int idx = 0; idx < n; idx++)
                height[idx] = sumW[idx] > 0f ? sumWH[idx] / sumW[idx] : under[idx];
        }

        private void ComputePads(float[] first)
        {
            Pads.Clear();
            YardPads.Clear();
            foreach (LookBuilding b in Data.buildings)
            {
                float x = b.x, y = b.y;
                if (b.ent.Length >= 2)
                {
                    x = b.ent[0];
                    y = b.ent[1];
                }
                Pads[b.id] = Grid.Sample(first, x, y);
            }
            foreach (LookYard yard in Data.yards)
            {
                float pad = float.NaN;
                foreach (LookBuilding b in Data.buildings)
                    if (LookGeom.Inside(yard.pts, b.x, b.y))
                    {
                        pad = Pads[b.id];
                        break;
                    }
                if (float.IsNaN(pad))
                {
                    LookGeom.Centroid(yard.pts, out float cx, out float cy);
                    pad = Grid.Sample(first, cx, cy);
                }
                YardPads[yard.id] = pad;
            }
        }

        private void ApplyYards(float[] under, float[] field)
        {
            float slopeK = 1.5f / MathF.Tan(SideSlopeDeg * MathF.PI / 180f);
            foreach (LookYard yard in Data.yards)
            {
                if (LookGeom.Count(yard.pts) < 3) continue;
                float pad = YardPads[yard.id];
                LookGeom.Bounds(yard.pts, out float x0, out float y0, out float x1, out float y1);
                Grid.Range(x0 - YardBlendMax, y0 - YardBlendMax, x1 + YardBlendMax, y1 + YardBlendMax, out int i0, out int j0, out int i1, out int j1);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        float x = Grid.X(i), y = Grid.Y(j);
                        int k = j * Grid.Nx + i;
                        float target = under[k] - Math.Clamp(under[k] - pad, -YardTerrace, YardTerrace);
                        float w = 1f;
                        if (!LookGeom.Inside(yard.pts, x, y))
                        {
                            float d = LookGeom.DistToPolyline(yard.pts, x, y, true, out _, out _);
                            float bw = Math.Clamp(MathF.Abs(target - under[k]) * slopeK, YardBlend, YardBlendMax);
                            if (d >= bw) continue;
                            w = 1f - LookGeom.Smooth01(d / bw);
                        }
                        field[k] = LookGeom.Lerp(field[k], target, w);
                    }
            }
        }

        private void ApplyBuildings(float[] under, float[] field, bool[] core)
        {
            int n = Grid.Length;
            var sumW = new float[n];
            var sumWH = new float[n];
            var maxW = new float[n];
            float k = 1.5f / MathF.Tan(SideSlopeDeg * MathF.PI / 180f);
            Walls.Clear();
            foreach (LookBuilding b in Data.buildings)
            {
                if (LookGeom.Count(b.fp) < 3) continue;
                float pad = Pads[b.id];
                float[] ring = LookGeom.OffsetPolygon(b.fp, BuildingMargin + WallOffset);
                float drop = 0f;
                float[] cum = LookGeom.Cumulative(ring, true);
                for (float s = 0f; s < cum[cum.Length - 1]; s += 1f)
                {
                    LookGeom.PointAt(ring, cum, s, true, out float rx, out float ry, out _, out _);
                    drop = MathF.Max(drop, MathF.Abs(pad - Grid.Sample(under, rx, ry)));
                }
                bool walled = drop > WallDrop && string.IsNullOrEmpty(b.prop_key);
                // Fedya's rule: nothing fence- or wall-like on district borders (only the elite ring). A ring that hugs
                // a border gets the ordinary bank blend instead of a stone wall.
                if (walled && HugsBorder(ring))
                {
                    walled = false;
                    Warnings.Add($"{b.id}: pad {drop:0.0} m off the ground next to a district border - banked, no retaining wall");
                }
                if (walled) Walls.Add(new RetainingWall { BuildingId = b.id, Ring = ring });
                float reach = BuildingMargin + BuildingBlendMax;
                LookGeom.Bounds(b.fp, out float x0, out float y0, out float x1, out float y1);
                Grid.Range(x0 - reach, y0 - reach, x1 + reach, y1 + reach, out int i0, out int j0, out int i1, out int j1);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        float x = Grid.X(i), y = Grid.Y(j);
                        int idx = j * Grid.Nx + i;
                        float w = 1f;
                        if (walled)
                        {
                            // Weight by the wall ring itself (mitred corners included), so the pad reaches the wall all
                            // the way round and the corners stay closed: full inside, linear over +-0.7 m of the ring.
                            float dr = LookGeom.DistToPolyline(ring, x, y, true, out _, out _);
                            float signed = LookGeom.Inside(ring, x, y) ? -dr : dr;
                            if (signed >= 0.7f) continue;
                            if (signed > -0.7f) w = 1f - (signed + 0.7f) / 1.4f;
                        }
                        else if (!LookGeom.Inside(b.fp, x, y))
                        {
                            float d = LookGeom.DistToPolyline(b.fp, x, y, true, out _, out _);
                            if (d > BuildingMargin)
                            {
                                float bw = Math.Clamp(MathF.Abs(pad - under[idx]) * k, BuildingBlend, BuildingBlendMax);
                                if (d >= BuildingMargin + bw) continue;
                                w = 1f - LookGeom.Smooth01((d - BuildingMargin) / bw);
                            }
                        }
                        float w4 = w * w * w * w;
                        sumW[idx] += w4;
                        sumWH[idx] += w4 * pad;
                        if (w > maxW[idx]) maxW[idx] = w;
                    }
            }
            for (int idx = 0; idx < n; idx++)
                if (maxW[idx] > 0f)
                {
                    field[idx] = LookGeom.Lerp(field[idx], sumWH[idx] / sumW[idx], maxW[idx]);
                    core[idx] = maxW[idx] >= 1f;
                }
        }

        // Same test as MapLookValidator.BorderFences: within BorderBand of a district outline for BorderHug metres in a row.
        public float BorderBand = 3f, BorderHug = 6f;

        private bool HugsBorder(float[] ring)
        {
            float[] cum = LookGeom.Cumulative(ring, true);
            float total = cum[cum.Length - 1], hug = 0f;
            for (float s = 0f; s < total + BorderHug; s += 1f)
            {
                LookGeom.PointAt(ring, cum, s % total, true, out float x, out float y, out _, out _);
                bool near = false;
                foreach (LookDistrict d in Data.districts)
                    if (LookGeom.Count(d.pts) >= 3 && LookGeom.DistToPolyline(d.pts, x, y, true, out _, out _) < BorderBand)
                    {
                        near = true;
                        break;
                    }
                hug = near ? hug + 1f : 0f;
                if (hug >= BorderHug) return true;
            }
            return false;
        }

        // Lowest terrain point under a footprint (the plinth goes down to it).
        public float LowestUnder(float[] fp)
        {
            int n = LookGeom.Count(fp);
            float low = float.MaxValue;
            for (int i = 0; i < n; i++)
            {
                int b = (i + 1) % n;
                low = MathF.Min(low, Height(fp[2 * i], fp[2 * i + 1]));
                low = MathF.Min(low, Height((fp[2 * i] + fp[2 * b]) / 2f, (fp[2 * i + 1] + fp[2 * b + 1]) / 2f));
            }
            LookGeom.Centroid(fp, out float cx, out float cy);
            return MathF.Min(low, Height(cx, cy));
        }

        // Water surface over the terrain at (x, y): lake, river/canal channel or the sea.
        public bool InWater(float x, float y, out float level)
        {
            float h = Height(x, y);
            foreach (LookWater w in Data.water)
            {
                if (h >= w.level) continue;
                if (w.kind == "lake")
                {
                    if (LookGeom.Inside(w.pts, x, y)) { level = w.level; return true; }
                }
                else if (LookGeom.DistToPolyline(w.pts, x, y, false, out _, out _) < WaterHalfWidth(w))
                {
                    level = w.level;
                    return true;
                }
            }
            if (h < Data.sea.level && (LookGeom.Inside(Data.sea.pts, x, y) || LookGeom.Inside(Data.beach.pts, x, y)))
            {
                level = Data.sea.level;
                return true;
            }
            level = 0f;
            return false;
        }

        private static float[] Filled(int n, float v)
        {
            var a = new float[n];
            for (int i = 0; i < n; i++) a[i] = v;
            return a;
        }

        private static void Min(float[] a, int k, float v)
        {
            if (v < a[k]) a[k] = v;
        }
    }
}
