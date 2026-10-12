using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // v17 corrections of the loaded look data before the environment is built (Fedya's playtest, 2026-10-12). The
    // look_v16 / look_v17 json (GPT's v16 converter, inherited unchanged by map_plan_v17.py) has:
    //  1. the Downtown ring's four 90-degree corners as road pieces meeting end to end with no junction patch, so the
    //     outer corner square shows grass; sharp polyline corners lose their vertex in the even 2 m resampling;
    //  2. every Downtown sidewalk as one run per street side straight through the crossing streets and junctions, so the
    //     paving and kerbs lie on the carriageway;
    //  3. kerb parking on both sides of every street (car centre inside the lane);
    //  4. street tree rows at a fixed 11 m, park rings and grids at metronome spacing.
    // Fixed here per revision v17 (v16 builds never call this). The plan generator still emits 1-4: a v18 plan should
    // split sidewalks at carriageways, add corner patches (or mitred joins), thin the car rows and scatter trees itself.
    public static class V3Fix17
    {
        private const float CornerTurnDeg = 20f;

        // ---------- 1 + 2: road corners and sidewalks ----------

        public static void Roads(LookData d, List<string> log)
        {
            int patches = CornerPatches(d);
            int before = d.sidewalks.Length;
            float lenBefore = 0f, lenAfter = 0f;
            foreach (LookSidewalk s in d.sidewalks) lenBefore += Length(s.pts);
            d.sidewalks = SplitSidewalks(d);
            foreach (LookSidewalk s in d.sidewalks) lenAfter += Length(s.pts);
            log.Add($"v17 road fix: {patches} corner patches where road pieces meet end to end without a junction; sidewalks " +
                    $"{before} runs -> {d.sidewalks.Length} (cut where they cross a carriageway or junction: {lenBefore - lenAfter:0} of {lenBefore:0} m removed); " +
                    "polyline corners > 20 deg kept in the road/sidewalk resampling (mitred)");
        }

        // Even resampling of about `step` metres that keeps every vertex turning more than `cornerDeg` (a mitred corner
        // instead of a cut one). Both ends kept.
        public static float[] ResampleKeepCorners(float[] pts, float step, float cornerDeg = CornerTurnDeg)
        {
            int n = LookGeom.Count(pts);
            if (n < 3) return LookGeom.Resample(pts, step, out _);
            float cosLim = Mathf.Cos(cornerDeg * Mathf.Deg2Rad);
            var outPts = new List<float>();
            int start = 0;
            for (int i = 1; i < n; i++)
            {
                bool corner = false;
                if (i < n - 1)
                {
                    LookGeom.Dir(pts, i - 1, i, out float ax, out float ay);
                    LookGeom.Dir(pts, i, i + 1, out float bx, out float by);
                    corner = ax * bx + ay * by < cosLim;
                }
                if (!corner && i < n - 1) continue;
                var piece = new float[(i - start + 1) * 2];
                Array.Copy(pts, start * 2, piece, 0, piece.Length);
                float[] rs = LookGeom.Resample(piece, step, out _);
                for (int k = outPts.Count == 0 ? 0 : 1; k < LookGeom.Count(rs); k++)
                {
                    outPts.Add(rs[2 * k]);
                    outPts.Add(rs[2 * k + 1]);
                }
                start = i;
            }
            return outPts.ToArray();
        }

        private struct End
        {
            public LookRoad Road;
            public Vector2 P, Into; // Into: travel direction along the road into the joint
            public float Hw;
        }

        private static int CornerPatches(LookData d)
        {
            var ends = new List<End>();
            foreach (LookRoad r in d.roads)
            {
                if (LookGeom.Count(r.pts) < 2) continue;
                float[] cum = LookGeom.Cumulative(r.pts);
                float total = cum[cum.Length - 1], s0 = Mathf.Max(0f, r.trim_start), s1 = total - Mathf.Max(0f, r.trim_end);
                if (s1 - s0 < 0.3f) continue;
                LookGeom.PointAt(r.pts, cum, s0, false, out float x0, out float y0, out float tx0, out float ty0);
                LookGeom.PointAt(r.pts, cum, s1, false, out float x1, out float y1, out float tx1, out float ty1);
                ends.Add(new End { Road = r, P = new Vector2(x0, y0), Into = -new Vector2(tx0, ty0).normalized, Hw = r.w / 2f });
                ends.Add(new End { Road = r, P = new Vector2(x1, y1), Into = new Vector2(tx1, ty1).normalized, Hw = r.w / 2f });
            }
            var free = new List<End>();
            foreach (End e in ends)
            {
                bool covered = false;
                foreach (LookJunction j in d.junctions)
                    if (LookGeom.Count(j.pts) >= 3 && (LookGeom.Inside(j.pts, e.P.x, e.P.y) || LookGeom.DistToPolyline(j.pts, e.P.x, e.P.y, true, out _, out _) < 1f))
                    {
                        covered = true;
                        break;
                    }
                if (!covered) free.Add(e);
            }
            var added = new List<LookJunction>(d.junctions);
            int count = 0;
            for (int i = 0; i < free.Count; i++)
                for (int k = i + 1; k < free.Count; k++)
                {
                    End a = free[i], b = free[k];
                    if (a.Road == b.Road || (a.P - b.P).magnitude > 1.5f) continue;
                    Vector2 tIn = a.Into, tOut = -b.Into;
                    if (Vector2.Angle(tIn, tOut) < 8f) continue;
                    Vector2 c = (a.P + b.P) * 0.5f, nIn = Perp(tIn), nOut = Perp(tOut), nb = (nIn + nOut).normalized;
                    float hm = Mathf.Max(a.Hw, b.Hw), m = 1f / Mathf.Max(0.35f, Vector2.Dot(nb, nIn));
                    var pts = new List<Vector2>
                    {
                        c + nIn * a.Hw, c - nIn * a.Hw, c - tIn * 0.4f + nIn * a.Hw, c - tIn * 0.4f - nIn * a.Hw,
                        c + nOut * b.Hw, c - nOut * b.Hw, c + tOut * 0.4f + nOut * b.Hw, c + tOut * 0.4f - nOut * b.Hw,
                        c + nb * (hm * m), c - nb * (hm * m),
                    };
                    List<Vector2> hull = Hull(pts);
                    if (hull.Count < 3) continue;
                    var flat = new float[hull.Count * 2];
                    for (int h = 0; h < hull.Count; h++)
                    {
                        flat[2 * h] = hull[h].x;
                        flat[2 * h + 1] = hull[h].y;
                    }
                    var tris = new List<float>();
                    for (int h = 1; h + 1 < hull.Count; h++)
                        tris.AddRange(new[] { hull[0].x, hull[0].y, hull[h].x, hull[h].y, hull[h + 1].x, hull[h + 1].y });
                    added.Add(new LookJunction
                    {
                        id = $"J17_corner_{a.Road.id}_{b.Road.id}", x = c.x, y = c.y, r = hm, arms = 2,
                        roads = new[] { a.Road.road, b.Road.road }, pts = flat, tris = tris.ToArray(),
                    });
                    count++;
                }
            d.junctions = added.ToArray();
            return count;
        }

        private static Vector2 Perp(Vector2 t) => new Vector2(-t.y, t.x);

        private static List<Vector2> Hull(List<Vector2> p)
        {
            p.Sort((a, b) => a.x != b.x ? a.x.CompareTo(b.x) : a.y.CompareTo(b.y));
            var h = new List<Vector2>();
            for (int pass = 0; pass < 2; pass++)
            {
                int start = h.Count;
                for (int i = 0; i < p.Count; i++)
                {
                    Vector2 q = pass == 0 ? p[i] : p[p.Count - 1 - i];
                    while (h.Count >= start + 2 && Cross(h[h.Count - 2], h[h.Count - 1], q) <= 1e-6f) h.RemoveAt(h.Count - 1);
                    h.Add(q);
                }
                h.RemoveAt(h.Count - 1);
            }
            return h;
        }

        private static float Cross(Vector2 o, Vector2 a, Vector2 b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);

        private sealed class RoadBox
        {
            public LookRoad Road;
            public float X0, Y0, X1, Y1;
        }

        private static List<RoadBox> Boxes(LookData d, float pad)
        {
            var list = new List<RoadBox>();
            foreach (LookRoad r in d.roads)
            {
                if (LookGeom.Count(r.pts) < 2) continue;
                LookGeom.Bounds(r.pts, out float x0, out float y0, out float x1, out float y1);
                float p = r.w / 2f + pad;
                list.Add(new RoadBox { Road = r, X0 = x0 - p, Y0 = y0 - p, X1 = x1 + p, Y1 = y1 + p });
            }
            return list;
        }

        private static LookSidewalk[] SplitSidewalks(LookData d)
        {
            List<RoadBox> boxes = Boxes(d, 1f);
            var result = new List<LookSidewalk>();
            foreach (LookSidewalk s in d.sidewalks)
            {
                if (LookGeom.Count(s.pts) < 2) continue;
                float[] line = ResampleKeepCorners(s.pts, 0.5f);
                int n = LookGeom.Count(line);
                float hw = s.w / 2f;
                float[] offs = { -hw - 0.1f, -hw * 0.5f, 0f, hw * 0.5f, hw + 0.12f };
                var blocked = new bool[n];
                for (int i = 0; i < n; i++)
                {
                    LookGeom.Normal(line, i, n, out float nx, out float ny, out _);
                    float x = line[2 * i], y = line[2 * i + 1];
                    foreach (float o in offs)
                    {
                        float qx = x + nx * o, qy = y + ny * o;
                        if (Blocked(d, boxes, s, qx, qy))
                        {
                            blocked[i] = true;
                            break;
                        }
                    }
                }
                var run = new List<float>();
                for (int i = 0; i <= n; i++)
                {
                    if (i < n && !blocked[i])
                    {
                        run.Add(line[2 * i]);
                        run.Add(line[2 * i + 1]);
                        continue;
                    }
                    if (run.Count >= 8 && Length(run.ToArray()) >= 2f)
                        result.Add(new LookSidewalk { road = s.road, side = s.side, w = s.w, verge = s.verge, curb = s.curb, district = s.district, pts = run.ToArray() });
                    run.Clear();
                }
            }
            return result.ToArray();
        }

        private static bool Blocked(LookData d, List<RoadBox> boxes, LookSidewalk s, float x, float y)
        {
            foreach (RoadBox b in boxes)
            {
                if (x < b.X0 || x > b.X1 || y < b.Y0 || y > b.Y1) continue;
                LookRoad r = b.Road;
                bool own = !string.IsNullOrEmpty(s.road) && r.road == s.road;
                float lim = own ? r.w / 2f - 0.25f : r.w / 2f + 0.3f;
                if (LookGeom.DistToPolyline(r.pts, x, y, false, out _, out _) < lim) return true;
            }
            foreach (LookJunction j in d.junctions)
            {
                if (LookGeom.Count(j.pts) < 3 || Mathf.Abs(x - j.x) > j.r + 30f || Mathf.Abs(y - j.y) > j.r + 30f) continue;
                if (LookGeom.Inside(j.pts, x, y)) return true;
            }
            return false;
        }

        private static float Length(float[] pts)
        {
            if (LookGeom.Count(pts) < 2) return 0f;
            float[] cum = LookGeom.Cumulative(pts);
            return cum[cum.Length - 1];
        }

        // A junction patch where every road through it is dirt: dirt, not the default asphalt (grey squares on the
        // hamlet's dirt crossings: RoadMeshBuilder only looks at roads that END at the junction).
        public static string JunctionMaterial(LookData d, LookJunction j)
        {
            bool any = false;
            foreach (LookRoad r in d.roads)
            {
                if (LookGeom.Count(r.pts) < 2 || LookGeom.DistToPolyline(r.pts, j.x, j.y, false, out _, out _) > j.r + 2f) continue;
                if (r.surface != "dirt") return null;
                any = true;
            }
            return any ? "mat/road/dirt" : null;
        }

        // ---------- fences across roads and paths ----------

        // Where a fence run crosses or runs inside a road or path (centre within the half width + 0.3 m), that stretch
        // becomes one gate opening (stretch + 1.2 m, piers just outside the carriageway).
        public static void Fences(LookData d, List<string> log)
        {
            if (V3LookData.Fences == null) return;
            List<RoadBox> boxes = Boxes(d, 1f);
            int gates = 0;
            foreach (V3LookData.Fence f in V3LookData.Fences)
            {
                var pts = new List<Vector2>(f.Line);
                if (f.Closed && pts.Count > 2) pts.Add(pts[0]);
                var hit = new List<(Vector2 p, float s)>();
                float arc = 0f;
                for (int i = 0; i + 1 < pts.Count; i++)
                {
                    Vector2 a = pts[i], b = pts[i + 1];
                    float len = Vector2.Distance(a, b);
                    int n = Mathf.Max(1, Mathf.CeilToInt(len / 0.5f));
                    for (int k = 0; k < n; k++)
                    {
                        Vector2 q = Vector2.Lerp(a, b, (k + 0.5f) / n);
                        if (OnCarriageway(boxes, q.x, q.y, 0.3f)) hit.Add((q, arc + len * (k + 0.5f) / n));
                    }
                    arc += len;
                }
                int r0 = 0;
                for (int i = 1; i <= hit.Count; i++)
                {
                    if (i < hit.Count && hit[i].s - hit[i - 1].s < 1.1f) continue;
                    var first = hit[r0];
                    var last = hit[i - 1];
                    Vector2 mid = hit[(r0 + i - 1) / 2].p;
                    float w = Mathf.Max(Vector2.Distance(first.p, last.p), last.s - first.s) + 1.2f;
                    bool covered = false;
                    foreach (var g in f.Gates)
                        if (Vector2.Distance(g.p, mid) + w / 2f <= g.w / 2f + 0.3f) covered = true;
                    if (!covered)
                    {
                        f.Gates.Add((mid, w));
                        gates++;
                    }
                    r0 = i;
                }
            }
            log.Add($"v17 fences: {gates} openings where a fence run crossed or ran inside a road or path");
        }

        private static bool OnCarriageway(List<RoadBox> boxes, float x, float y, float margin)
        {
            foreach (RoadBox b in boxes)
            {
                if (x < b.X0 || x > b.X1 || y < b.Y0 || y > b.Y1) continue;
                if (LookGeom.DistToPolyline(b.Road.pts, x, y, false, out _, out _) < b.Road.w / 2f + margin) return true;
            }
            return false;
        }

        // ---------- 3: parked cars ----------

        private static readonly HashSet<string> MainStreets = new() { "05_N", "05_W", "05_S", "05_E", "05_AX" };

        private static bool Main(LookRoad r) => r.cls == "highway" || r.cls == "rural_road" || MainStreets.Contains(r.road) || MainStreets.Contains(r.id);

        // None on main roads and boulevards; on side streets about a third in clusters (25 m kept out of every 75 m);
        // none on a sidewalk, in or near a junction or by a bridge / culvert. Yard cars away from the roads stay.
        public static void Cars(LookData d, List<string> log)
        {
            if (V3LookData.Props == null) return;
            List<RoadBox> boxes = Boxes(d, 6f);
            int total = 0, mainCut = 0, sideCut = 0, junctionCut = 0, walkCut = 0, sideKept = 0, yardKept = 0, pushed = 0;
            var kept = new List<V3LookData.Prop>(V3LookData.Props.Count);
            foreach (V3LookData.Prop p in V3LookData.Props)
            {
                bool car = p.Key.Contains("car_") || p.Key.Contains("van_");
                if (!car)
                {
                    // Signs and other street props standing inside a carriageway go to its edge + 0.6 m.
                    foreach (RoadBox b in boxes)
                    {
                        if (p.X < b.X0 || p.X > b.X1 || p.Y < b.Y0 || p.Y > b.Y1 || b.Road.cls == "passage") continue;
                        float dd = LookGeom.DistToPolyline(b.Road.pts, p.X, p.Y, false, out int seg, out float tt);
                        if (dd >= b.Road.w / 2f - 0.3f || dd < 0.5f) continue;
                        float cx = Mathf.Lerp(b.Road.pts[2 * seg], b.Road.pts[2 * seg + 2], tt), cy = Mathf.Lerp(b.Road.pts[2 * seg + 1], b.Road.pts[2 * seg + 3], tt);
                        float k = (b.Road.w / 2f + 0.6f) / dd;
                        p.X = cx + (p.X - cx) * k;
                        p.Y = cy + (p.Y - cy) * k;
                        pushed++;
                        break;
                    }
                    kept.Add(p);
                    continue;
                }
                total++;
                if (NearJunction(d, p.X, p.Y))
                {
                    junctionCut++;
                    continue;
                }
                if (OnSidewalk(d, p.X, p.Y))
                {
                    walkCut++;
                    continue;
                }
                LookRoad best = null;
                float bestD = float.MaxValue, bestS = 0f;
                foreach (RoadBox b in boxes)
                {
                    if (p.X < b.X0 || p.X > b.X1 || p.Y < b.Y0 || p.Y > b.Y1) continue;
                    float dd = LookGeom.DistToPolyline(b.Road.pts, p.X, p.Y, false, out int seg, out float t);
                    if (dd >= bestD) continue;
                    bestD = dd;
                    best = b.Road;
                    float[] cum = LookGeom.Cumulative(b.Road.pts);
                    bestS = Mathf.Lerp(cum[seg], cum[seg + 1], t);
                }
                if (best == null || bestD > best.w / 2f + 3.5f)
                {
                    yardKept++;
                    kept.Add(p);
                    continue;
                }
                if (Main(best))
                {
                    mainCut++;
                    continue;
                }
                float phase = (LookGeom.StableHash(best.id) & 0xFFFF) / 65535f * 75f;
                if (Mathf.Repeat(bestS + phase, 75f) < 25f)
                {
                    sideKept++;
                    kept.Add(p);
                }
                else sideCut++;
            }
            V3LookData.Props = kept;
            log.Add($"v17 cars: {total} -> {sideKept + yardKept} (main roads/boulevards {mainCut} removed, side streets {sideKept} kept in clusters / {sideCut} removed, " +
                    $"junctions/bridges {junctionCut} and sidewalks {walkCut} removed, {yardKept} yard cars kept); {pushed} street props moved off a carriageway");
        }

        private static bool NearJunction(LookData d, float x, float y)
        {
            foreach (LookJunction j in d.junctions)
            {
                if (LookGeom.Dist(x, y, j.x, j.y) < j.r + 9f) return true;
                if (LookGeom.Count(j.pts) >= 3 && Mathf.Abs(x - j.x) < j.r + 30f && Mathf.Abs(y - j.y) < j.r + 30f &&
                    (LookGeom.Inside(j.pts, x, y) || LookGeom.DistToPolyline(j.pts, x, y, true, out _, out _) < 4f)) return true;
            }
            foreach (LookCrossing c in d.crossings)
                if (LookGeom.Dist(x, y, c.x, c.y) < Mathf.Max(10f, c.len * 0.5f + 6f)) return true;
            return false;
        }

        private static bool OnSidewalk(LookData d, float x, float y)
        {
            foreach (LookSidewalk s in d.sidewalks)
            {
                LookGeom.Bounds(s.pts, out float x0, out float y0, out float x1, out float y1);
                float pad = s.w / 2f + 1f;
                if (x < x0 - pad || x > x1 + pad || y < y0 - pad || y > y1 + pad) continue;
                if (LookGeom.DistToPolyline(s.pts, x, y, false, out _, out _) < s.w / 2f + 0.9f) return true;
            }
            return false;
        }

        // ---------- 4: trees ----------

        private static readonly string[] ParkSpecies = { "oak", "linden", "birch", "poplar" };

        // Street rows re-spaced at 8-20 m with gaps; park, yard, orchard and forest trees jittered by a share of their
        // nearest-neighbour spacing, thinned through a 35 m cluster noise, with small 2-3 tree clusters added in parks;
        // heights +-20 %, some park species mixed. Nothing moves onto a road, a building or water (else it stays put).
        public static void Trees(LookData d, List<string> log)
        {
            int seed = d.seed * 31 + 17;
            List<RoadBox> boxes = Boxes(d, 8f);
            var blockers = new Blockers(d);
            var trees = d.trees;
            int n = trees.Length;
            var street = new Dictionary<string, List<int>>();
            var roadOf = new LookRoad[n];
            var kind = new int[n]; // 0 other, 1 street, 2 forest
            for (int i = 0; i < n; i++)
            {
                LookTree t = trees[i];
                if (InForest(t.x, t.y)) kind[i] = 2;
                if (t.sp == "bush") continue;
                LookRoad best = null;
                float bestD = float.MaxValue, side = 0f;
                foreach (RoadBox b in boxes)
                {
                    if (t.x < b.X0 || t.x > b.X1 || t.y < b.Y0 || t.y > b.Y1) continue;
                    float dd = LookGeom.DistToPolyline(b.Road.pts, t.x, t.y, false, out int seg, out float tt);
                    if (dd >= bestD) continue;
                    bestD = dd;
                    best = b.Road;
                    float ax = b.Road.pts[2 * seg], ay = b.Road.pts[2 * seg + 1], bx = b.Road.pts[2 * seg + 2], by = b.Road.pts[2 * seg + 3];
                    side = Mathf.Sign((bx - ax) * (t.y - ay) - (by - ay) * (t.x - ax));
                }
                if (best != null && bestD > best.w / 2f && bestD < best.w / 2f + 6.5f && kind[i] != 2)
                {
                    kind[i] = 1;
                    roadOf[i] = best;
                    string key = best.id + (side >= 0f ? "|L" : "|R");
                    if (!street.TryGetValue(key, out var list)) street[key] = list = new List<int>();
                    list.Add(i);
                }
            }

            var result = new List<LookTree>(n + 256);
            int streetIn = 0, streetOut = 0, moved = 0, dropped = 0, clusters = 0;
            var used = new bool[n];
            foreach (var kv in street)
            {
                List<int> idx = kv.Value;
                if (idx.Count < 3)
                {
                    foreach (int i in idx) kind[i] = 0;
                    continue;
                }
                LookRoad r = roadOf[idx[0]];
                float[] cum = LookGeom.Cumulative(r.pts);
                float sMin = float.MaxValue, sMax = float.MinValue, offSum = 0f, hSum = 0f;
                var species = new List<string>();
                foreach (int i in idx)
                {
                    LookTree t = trees[i];
                    float dd = LookGeom.DistToPolyline(r.pts, t.x, t.y, false, out int seg, out float tt);
                    float s = Mathf.Lerp(cum[seg], cum[seg + 1], tt);
                    sMin = Mathf.Min(sMin, s);
                    sMax = Mathf.Max(sMax, s);
                    offSum += dd;
                    hSum += t.h;
                    species.Add(t.sp);
                    used[i] = true;
                }
                streetIn += idx.Count;
                float off = offSum / idx.Count, hMean = hSum / idx.Count, sideSign = kv.Key.EndsWith("|L") ? 1f : -1f;
                int rs = LookGeom.StableHash(kv.Key) ^ seed;
                float sPos = sMin + LookGeom.Hash01(rs, 1, seed) * 5f;
                for (int k = 0; sPos <= sMax + 0.01f; k++)
                {
                    float gap = LookGeom.Hash01(rs, 100 + k, seed);
                    if (gap > 0.16f)
                    {
                        LookGeom.PointAt(r.pts, cum, sPos, false, out float x, out float y, out float tx, out float ty);
                        float o = Mathf.Max(r.w / 2f + 0.8f, off + (LookGeom.Hash01(rs, 200 + k, seed) - 0.5f) * 0.8f) * sideSign;
                        float px = x - ty * o, py = y + tx * o;
                        if (blockers.Free(px, py, boxes, 0.6f))
                        {
                            string sp = species[(int)(LookGeom.Hash01(rs, 300 + k, seed) * species.Count) % species.Count];
                            result.Add(new LookTree { sp = sp, x = px, y = py, h = hMean * (0.8f + 0.4f * LookGeom.Hash01(rs, 400 + k, seed)) });
                            streetOut++;
                        }
                    }
                    sPos += 8f + 12f * LookGeom.Hash01(rs, 500 + k, seed);
                }
            }

            // Nearest-neighbour spacing on a 6 m hash grid (all trees, before any move).
            var grid = new Dictionary<long, List<int>>();
            long Key(int gx, int gy) => ((long)gx << 32) ^ (uint)gy;
            for (int i = 0; i < n; i++)
            {
                long key = Key(Mathf.FloorToInt(trees[i].x / 6f), Mathf.FloorToInt(trees[i].y / 6f));
                if (!grid.TryGetValue(key, out var l)) grid[key] = l = new List<int>();
                l.Add(i);
            }
            for (int i = 0; i < n; i++)
            {
                if (used[i]) continue;
                LookTree t = trees[i];
                bool forest = kind[i] == 2, fruit = t.sp == "fruit", bush = t.sp == "bush";
                float nn = 12f;
                int gx = Mathf.FloorToInt(t.x / 6f), gy = Mathf.FloorToInt(t.y / 6f);
                for (int ox = -2; ox <= 2; ox++)
                    for (int oy = -2; oy <= 2; oy++)
                        if (grid.TryGetValue(Key(gx + ox, gy + oy), out var l))
                            foreach (int k in l)
                                if (k != i) nn = Mathf.Min(nn, LookGeom.Dist(t.x, t.y, trees[k].x, trees[k].y));
                float cluster = Mathf.PerlinNoise(t.x / 35f + 3.7f, t.y / 35f + 9.1f);
                float keep = forest ? 0.97f : fruit ? 0.85f : bush ? 0.95f : Mathf.Clamp01(0.62f + 0.5f * cluster);
                if (LookGeom.Hash01(i, 11, seed) > keep)
                {
                    dropped++;
                    continue;
                }
                float amp = nn * (forest ? 0.5f : fruit ? 0.22f : 0.38f);
                float ang = LookGeom.Hash01(i, 12, seed) * Mathf.PI * 2f, rad = amp * Mathf.Sqrt(LookGeom.Hash01(i, 13, seed));
                float x = t.x + Mathf.Cos(ang) * rad, y = t.y + Mathf.Sin(ang) * rad;
                if (rad > 0.2f && blockers.Free(x, y, boxes, 1.2f)) moved++;
                else
                {
                    x = t.x;
                    y = t.y;
                }
                string sp = t.sp;
                if (!forest && !fruit && !bush && Array.IndexOf(ParkSpecies, sp) >= 0 && LookGeom.Hash01(i, 14, seed) < 0.2f)
                    sp = ParkSpecies[(int)(LookGeom.Hash01(i, 15, seed) * ParkSpecies.Length) % ParkSpecies.Length];
                result.Add(new LookTree { sp = sp, x = x, y = y, h = t.h * (0.8f + 0.4f * LookGeom.Hash01(i, 16, seed)) });
                // Small clusters in parks and yards: a companion or two at 2.5-4.5 m where the cluster noise is high.
                if (!forest && !fruit && !bush && cluster > 0.55f && LookGeom.Hash01(i, 17, seed) < 0.22f)
                {
                    int extra = LookGeom.Hash01(i, 18, seed) < 0.6f ? 1 : 2;
                    for (int e = 0; e < extra; e++)
                    {
                        float a2 = ang + 2f + e * 2.2f + LookGeom.Hash01(i, 19 + e, seed), r2 = 2.5f + 2f * LookGeom.Hash01(i, 21 + e, seed);
                        float cx = x + Mathf.Cos(a2) * r2, cy = y + Mathf.Sin(a2) * r2;
                        if (!blockers.Free(cx, cy, boxes, 1.5f)) continue;
                        string csp = LookGeom.Hash01(i, 23 + e, seed) < 0.5f ? sp : "birch";
                        result.Add(new LookTree { sp = csp, x = cx, y = cy, h = t.h * (0.7f + 0.35f * LookGeom.Hash01(i, 25 + e, seed)) });
                        clusters++;
                    }
                }
            }
            d.trees = result.ToArray();
            log.Add($"v17 trees: {n} -> {d.trees.Length}; street rows {street.Count} sides, {streetIn} trees -> {streetOut} at 8-20 m with gaps; " +
                    $"{moved} jittered, {dropped} thinned by the cluster noise, {clusters} cluster companions; heights +-20 %");
        }

        private static bool InForest(float x, float y)
        {
            if (V3LookData.ForestZones == null) return false;
            foreach (var z in V3LookData.ForestZones)
                if (LookGeom.Count(z.poly) >= 3 && LookGeom.Inside(z.poly, x, y)) return true;
            return false;
        }

        // Building footprints (+1 m), water and the road carriageways (+margin) a moved or new tree may not stand on.
        private sealed class Blockers
        {
            private readonly List<(float[] poly, float x0, float y0, float x1, float y1)> polys = new();

            public Blockers(LookData d)
            {
                foreach (LookBuilding b in d.buildings)
                    if (LookGeom.Count(b.fp) >= 3) Add(LookGeom.OffsetPolygon(V3Dressing.Ccw(b.fp), 1f));
                foreach (LookWater w in d.water)
                    if (LookGeom.Count(w.pts) >= 3) Add(w.pts);
                foreach (LookJunction j in d.junctions)
                    if (LookGeom.Count(j.pts) >= 3) Add(j.pts);
                foreach (LookParking p in d.parking)
                    if (LookGeom.Count(p.pts) >= 3) Add(p.pts);
            }

            private void Add(float[] poly)
            {
                if (poly == null || LookGeom.Count(poly) < 3) return;
                LookGeom.Bounds(poly, out float x0, out float y0, out float x1, out float y1);
                polys.Add((poly, x0, y0, x1, y1));
            }

            public bool Free(float x, float y, List<RoadBox> roads, float roadMargin)
            {
                foreach (var p in polys)
                    if (x >= p.x0 && x <= p.x1 && y >= p.y0 && y <= p.y1 && LookGeom.Inside(p.poly, x, y)) return false;
                foreach (RoadBox b in roads)
                {
                    if (x < b.X0 || x > b.X1 || y < b.Y0 || y > b.Y1) continue;
                    if (LookGeom.DistToPolyline(b.Road.pts, x, y, false, out _, out _) < b.Road.w / 2f + roadMargin) return false;
                }
                return true;
            }
        }
    }
}
