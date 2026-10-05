using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Fence, wall and pipe geometry (runtime-safe; PropScatterer places the results). Plot fences: picket #A99773,
    // farmstead boards, hedges; the stylised elite ring: stucco plinth, stone piers, black bars, thuja hedge behind,
    // lamp piers at the gates. Fedya's rule: these only ever run around single plots or the elite hill, never along
    // district borders - the flattener drops every plan separator but the elite fence and the beach scarps.
    public static class FenceBuilder
    {
        // Render and collision drafts of one plot's fence (nulls when the plot is unfenced). Stretches that run along
        // a district border (onBorder) are left out, so a plot fence never doubles as a border fence.
        public static (MeshDraft render, MeshDraft collision) Yard(LookYard y, Func<float, float, float> ground, Func<float, float, bool> onBorder = null)
        {
            if (y.fence == "none" || string.IsNullOrEmpty(y.fence) || LookGeom.Count(y.pts) < 3) return (null, null);
            float[] cum = LookGeom.Cumulative(y.pts, true);
            float total = cum[cum.Length - 1];
            var draft = new MeshDraft();
            var col = new MeshDraft();
            int seed = LookGeom.StableHash(y.id);
            foreach (var (s0, s1) in YardRuns(y, cum, onBorder))
            {
                List<Vector2> run = RunPoints(y.pts, cum, true, s0, s1);
                switch (y.fence)
                {
                    case "picket": Picket(draft, run, ground, Mathf.Clamp(y.h, 0.7f, 1.3f), seed); break;
                    case "hedge": Hedge(draft, run, ground, Mathf.Clamp(y.h, 1f, 1.8f), "mat/hedge", 0.9f); break;
                    case "elite": EliteRun(draft, run, ground, Mathf.Clamp(y.h, 1.4f, 2.4f), Vector2.zero, false); break;
                    default: Wooden(draft, run, ground, Mathf.Clamp(y.h, 1f, 1.6f), seed); break;
                }
                Collider(col, run, ground, Mathf.Max(1f, y.h), y.fence == "hedge" ? 0.9f : 0.2f);
                GatePosts(draft, run, ground, y.fence);
            }
            return (draft, col);
        }

        // The elite perimeter: runs between the gate openings, hedge on the hill side.
        // `bars` false: the fence itself comes from kit prefabs (PropScatterer); only hedge, gate piers and collision here.
        public static (MeshDraft render, MeshDraft collision) Elite(LookEliteFence f, Func<float, float, float> ground, Vector2 inside, bool bars = true)
        {
            if (LookGeom.Count(f.pts) < 2) return (null, null);
            float[] cum = LookGeom.Cumulative(f.pts);
            float total = cum[cum.Length - 1];
            var draft = new MeshDraft();
            var col = new MeshDraft();
            float h = Mathf.Clamp(f.h, 1.6f, 2.6f);
            foreach (var (s0, s1) in Runs(total, f.gaps))
            {
                List<Vector2> run = RunPoints(f.pts, cum, false, s0, s1);
                EliteRun(draft, run, ground, h, inside, true, bars);
                GatePosts(draft, run, ground, "elite");
                Collider(col, run, ground, h, 0.5f);
            }
            return (draft, col);
        }

        // The elite fence runs between the gate openings (world XZ points).
        public static List<List<Vector2>> EliteRuns(LookEliteFence f)
        {
            var runs = new List<List<Vector2>>();
            if (LookGeom.Count(f.pts) < 2) return runs;
            float[] cum = LookGeom.Cumulative(f.pts);
            foreach (var (s0, s1) in Runs(cum[cum.Length - 1], f.gaps)) runs.Add(RunPoints(f.pts, cum, false, s0, s1));
            return runs;
        }

        // Fenced stretches of a plot perimeter (metres from pts[0]): the json gaps (gates >= 4.5 m) minus every
        // stretch of 3 m or more that lies within 1.2 m of a district border.
        public static List<(float s0, float s1)> YardRuns(LookYard y, float[] cum, Func<float, float, bool> onBorder)
        {
            float total = cum[cum.Length - 1];
            List<(float s0, float s1)> runs = Runs(total, y.gaps);
            if (onBorder == null) return runs;
            var result = new List<(float s0, float s1)>();
            foreach (var (s0, s1) in runs)
            {
                float start = s0, borderFrom = -1f;
                for (float s = s0; ; s += 0.5f)
                {
                    bool end = s >= s1;
                    float q = Mathf.Min(s, s1);
                    LookGeom.PointAt(y.pts, cum, q, true, out float x, out float z, out _, out _);
                    bool border = !end && onBorder(x, z);
                    if (border && borderFrom < 0f) borderFrom = q;
                    if ((!border || end) && borderFrom >= 0f)
                    {
                        if (q - borderFrom >= 3f)
                        {
                            if (borderFrom - 0.5f - start > 0.6f) result.Add((start, borderFrom - 0.5f));
                            start = q + 0.5f;
                        }
                        borderFrom = -1f;
                    }
                    if (end) break;
                }
                if (s1 - start > 0.6f) result.Add((start, s1));
            }
            return result;
        }

        // Fence run polylines sampled every 0.5 m (validation).
        public static List<float[]> YardLines(LookYard y, Func<float, float, bool> onBorder)
        {
            var lines = new List<float[]>();
            if (y.fence == "none" || string.IsNullOrEmpty(y.fence) || LookGeom.Count(y.pts) < 3) return lines;
            float[] cum = LookGeom.Cumulative(y.pts, true);
            foreach (var (s0, s1) in YardRuns(y, cum, onBorder))
            {
                var list = new List<float>();
                for (float q = s0; ; q += 0.5f)
                {
                    LookGeom.PointAt(y.pts, cum, Mathf.Min(q, s1), true, out float x, out float z, out _, out _);
                    list.Add(x);
                    list.Add(z);
                    if (q >= s1) break;
                }
                lines.Add(list.ToArray());
            }
            return lines;
        }

        // True near any district border line (the plan's district polygons).
        public static Func<float, float, bool> BorderTest(LookData d, float distance = 1.2f) => (x, z) =>
        {
            foreach (LookDistrict dist in d.districts)
                if (LookGeom.DistToPolyline(dist.pts, x, z, true, out _, out _) < distance)
                    return true;
            return false;
        };

        // Stone retaining wall along a pad ring, only where the step between inside and outside is real.
        public static (MeshDraft render, MeshDraft collision) RetainingWall(float[] ring, Func<float, float, float> ground, string material)
        {
            var draft = new MeshDraft();
            var col = new MeshDraft();
            int stone = draft.Slot(material), cs = col.Slot("collision");
            float[] cum = LookGeom.Cumulative(ring, true);
            float total = cum[cum.Length - 1];
            for (float s = 0f; s < total - 0.01f; s += 1f)
            {
                float e = Mathf.Min(total, s + 1f);
                LookGeom.PointAt(ring, cum, s, true, out float ax, out float ay, out float tx, out float ty);
                LookGeom.PointAt(ring, cum, e, true, out float bx, out float by, out _, out _);
                float mx = (ax + bx) / 2f, my = (ay + by) / 2f, nx = ty, ny = -tx;
                float hin = ground(mx - nx * 0.9f, my - ny * 0.9f), hout = ground(mx + nx * 0.9f, my + ny * 0.9f);
                float top = Mathf.Max(hin, hout) + 0.15f, bottom = Mathf.Min(hin, hout) - 0.3f;
                if (top - bottom < 0.75f) continue;
                var a = new Vector3(ax, 0f, ay);
                var c = new Vector3(bx, 0f, by);
                draft.Beam(stone, a, c, 0.45f, bottom, top);
                col.Beam(cs, a, c, 0.45f, bottom, top);
            }
            return (draft, col);
        }

        // Above-ground outfall pipe segments (buried sleeves are skipped).
        public static (MeshDraft render, MeshDraft collision) Pipe(LookPipe p, Func<float, float, float> ground)
        {
            if (p.mode == "buried_sleeve" || LookGeom.Count(p.pts) < 2) return (null, null);
            var draft = new MeshDraft();
            var col = new MeshDraft();
            int slot = draft.Slot("mat/pipe", string.IsNullOrEmpty(p.color) ? "#9B5C36" : p.color);
            float r = Mathf.Max(0.1f, p.d / 2f);
            for (int i = 0; i + 1 < LookGeom.Count(p.pts); i++)
            {
                var a = new Vector3(p.pts[2 * i], 0f, p.pts[2 * i + 1]);
                var b = new Vector3(p.pts[2 * i + 2], 0f, p.pts[2 * i + 3]);
                a.y = ground(a.x, a.z) + p.h;
                b.y = ground(b.x, b.z) + p.h;
                Tube(draft, slot, a, b, r, 10);
                if (p.collide) col.Beam(col.Slot("collision"), a, b, r * 2f, Mathf.Min(a.y, b.y) - r, Mathf.Max(a.y, b.y) + r);
            }
            return (draft, col);
        }

        // Dead fish on the sand, the sludge plume floating on the sea.
        public static MeshDraft Decal(LookDecal dc, Func<float, float, float> ground, float seaLevel)
        {
            var draft = new MeshDraft();
            if (dc.tris.Length >= 6)
            {
                int slot = draft.Slot("mat/decal/sludge", dc.color);
                draft.PlanTris(slot, dc.tris, (x, y) => Mathf.Max(seaLevel, ground(x, y)), 0.04f);
            }
            else
            {
                int slot = draft.Slot("mat/decal/fish", dc.color);
                Quaternion q = Quaternion.Euler(0f, dc.a, 0f);
                Vector3 c = new Vector3(dc.x, ground(dc.x, dc.y) + 0.03f, dc.y);
                Vector3 ax = q * Vector3.right * (Mathf.Max(0.1f, dc.sx) / 2f), az = q * Vector3.forward * (Mathf.Max(0.2f, dc.sy) / 2f);
                draft.QuadFacing(slot, c - ax - az, c - ax + az, c + ax + az, c + ax - az, Vector3.up);
            }
            return draft;
        }

        // ---------------------------------------------------------------- fences (plots and the elite ring only)
        // Runs of a closed perimeter (or open polyline) between gaps given as [start, end] metre pairs.
        private static List<(float s0, float s1)> Runs(float total, float[] gaps)
        {
            var g = new List<(float, float)>();
            for (int i = 0; i + 1 < gaps.Length; i += 2) g.Add((Mathf.Max(0f, gaps[i]), Mathf.Min(total, gaps[i + 1])));
            g.Sort((a, b) => a.Item1.CompareTo(b.Item1));
            var runs = new List<(float, float)>();
            float s = 0f;
            foreach (var (a, b) in g)
            {
                if (a - s > 0.3f) runs.Add((s, a));
                s = Mathf.Max(s, b);
            }
            if (total - s > 0.3f) runs.Add((s, total));
            return runs;
        }

        // Points of a run, including every corner inside it.
        private static List<Vector2> RunPoints(float[] pts, float[] cum, bool closed, float s0, float s1)
        {
            var list = new List<Vector2>();
            LookGeom.PointAt(pts, cum, s0, closed, out float x, out float y, out _, out _);
            list.Add(new Vector2(x, y));
            int n = LookGeom.Count(pts);
            for (int i = 1; i < cum.Length - 1; i++)
                if (cum[i] > s0 + 0.05f && cum[i] < s1 - 0.05f)
                {
                    int k = i % n;
                    list.Add(new Vector2(pts[2 * k], pts[2 * k + 1]));
                }
            LookGeom.PointAt(pts, cum, s1, closed, out x, out y, out _, out _);
            list.Add(new Vector2(x, y));
            return list;
        }

        private static Vector3 G(Func<float, float, float> ground, Vector2 p, float lift = 0f) => new(p.x, ground(p.x, p.y) + lift, p.y);

        // Picket fence #A99773: posts every ~2 m, two rails, pointed pickets with a little lean and height noise.
        private static void Picket(MeshDraft d, List<Vector2> run, Func<float, float, float> ground, float h, int seed)
        {
            int wood = d.Slot("mat/fence/picket");
            int k = 0;
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                float len = Vector2.Distance(a, b);
                if (len < 0.05f) continue;
                Vector2 dir = (b - a) / len;
                Vector3 n3 = new Vector3(dir.y, 0f, -dir.x);
                for (float s = 0f; s <= len; s += Mathf.Max(0.5f, len / Mathf.Max(1, Mathf.Round(len / 2f))))
                {
                    Vector2 p = a + dir * s;
                    d.Box(wood, G(ground, p, (h + 0.1f) / 2f - 0.05f), new Vector3(0.08f, h + 0.1f, 0.08f), Quaternion.LookRotation(n3));
                }
                for (int r = 0; r < 2; r++)
                {
                    float y = h * (r == 0 ? 0.3f : 0.75f);
                    Vector3 ga = G(ground, a, y), gb = G(ground, b, y);
                    d.QuadFacing(wood, ga - Vector3.up * 0.03f + n3 * 0.03f, ga + Vector3.up * 0.03f + n3 * 0.03f, gb + Vector3.up * 0.03f + n3 * 0.03f, gb - Vector3.up * 0.03f + n3 * 0.03f, n3);
                    d.QuadFacing(wood, ga - Vector3.up * 0.03f - n3 * 0.03f, ga + Vector3.up * 0.03f - n3 * 0.03f, gb + Vector3.up * 0.03f - n3 * 0.03f, gb - Vector3.up * 0.03f - n3 * 0.03f, -n3);
                }
                for (float s = 0.12f; s < len - 0.05f; s += 0.22f, k++)
                {
                    Vector2 p = a + dir * s;
                    float ph = h - 0.05f + (LookGeom.Hash01(k, 1, seed) - 0.5f) * 0.08f;
                    float lean = (LookGeom.Hash01(k, 2, seed) - 0.5f) * 0.06f;
                    Vector3 g = G(ground, p, 0.04f), side = new Vector3(dir.x, 0f, dir.y) * 0.045f, top = Vector3.up * ph + new Vector3(dir.x, 0f, dir.y) * lean;
                    Vector3 off = n3 * 0.05f;
                    Vector3 p0 = g - side + off, p1 = g - side + top - Vector3.up * 0.08f + off, p2 = g + side + top - Vector3.up * 0.08f + off, p3 = g + side + off;
                    d.QuadFacing(wood, p0, p1, p2, p3, n3);
                    d.QuadFacing(wood, p0, p1, p2, p3, -n3);
                    Vector3 tip = g + top + off;
                    d.TriFacing(wood, p1, tip, p2, n3);
                    d.TriFacing(wood, p1, tip, p2, -n3);
                }
            }
        }

        // Farmstead fence: grey-brown posts and three horizontal boards, slightly uneven.
        private static void Wooden(MeshDraft d, List<Vector2> run, Func<float, float, float> ground, float h, int seed)
        {
            int wood = d.Slot("mat/fence/wooden");
            int k = 0;
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                float len = Vector2.Distance(a, b);
                if (len < 0.05f) continue;
                Vector2 dir = (b - a) / len;
                int posts = Mathf.Max(1, Mathf.RoundToInt(len / 2.4f));
                for (int p = 0; p <= posts; p++, k++)
                {
                    Vector2 q = a + dir * (len * p / posts);
                    float ph = h + 0.1f + (LookGeom.Hash01(k, 4, seed) - 0.5f) * 0.15f;
                    d.Box(wood, G(ground, q, ph / 2f - 0.05f), new Vector3(0.12f, ph, 0.12f), Quaternion.Euler(0f, LookGeom.Hash01(k, 6, seed) * 20f, 0f));
                }
                for (int r = 0; r < 3; r++)
                {
                    float y = h * (0.25f + 0.32f * r);
                    Vector3 ga = G(ground, a, y), gb = G(ground, b, y + (LookGeom.Hash01(i, r, seed) - 0.5f) * 0.08f);
                    d.Beam(wood, ga, gb, 0.035f, ga.y - 0.07f, ga.y + 0.07f);
                }
            }
        }

        private static void Hedge(MeshDraft d, List<Vector2> run, Func<float, float, float> ground, float h, string mat, float width)
        {
            int slot = d.Slot(mat);
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                float len = Vector2.Distance(a, b);
                if (len < 0.05f) continue;
                // Pieces by length and by slope, each a prism whose bottom and top follow the ground at both ends, so
                // hedges on the steep elite gardens neither gap nor sink at their uphill ends.
                float rise = Mathf.Abs(ground(b.x, b.y) - ground(a.x, a.y));
                int parts = Mathf.Max(1, Mathf.Max(Mathf.CeilToInt(len / 3f), Mathf.CeilToInt(rise / 0.5f)));
                Vector3 dir = new Vector3(b.x - a.x, 0f, b.y - a.y) / len, side = new Vector3(dir.z, 0f, -dir.x) * (width / 2f);
                for (int p = 0; p < parts; p++)
                {
                    float fa = (float)p / parts, fb = (float)(p + 1) / parts;
                    Vector2 pa = Vector2.Lerp(a, b, fa), pb = Vector2.Lerp(a, b, fb);
                    float ga = ground(pa.x, pa.y), gb = ground(pb.x, pb.y);
                    float ta = ga + h + 0.12f * Mathf.Sin(fa * parts * 2.3f + i), tb = gb + h + 0.12f * Mathf.Sin(fb * parts * 2.3f + i);
                    var A = new Vector3(pa.x, 0f, pa.y);
                    var B = new Vector3(pb.x, 0f, pb.y);
                    Vector3 a0 = A + Vector3.up * (ga - 0.15f), a1 = A + Vector3.up * ta, b0 = B + Vector3.up * (gb - 0.15f), b1 = B + Vector3.up * tb;
                    d.QuadFacing(slot, a0 + side, b0 + side, b1 + side, a1 + side, side);
                    d.QuadFacing(slot, a0 - side, b0 - side, b1 - side, a1 - side, -side);
                    d.QuadFacing(slot, a1 - side, a1 + side, b1 + side, b1 - side, Vector3.up);
                    d.QuadFacing(slot, a0 - side, a0 + side, a1 + side, a1 - side, -dir);
                    d.QuadFacing(slot, b0 - side, b0 + side, b1 + side, b1 - side, dir);
                }
            }
        }

        // Stylised elite fence: stucco plinth, stone piers every 3 m, black bars, rail; optional hedge behind.
        private static void EliteRun(MeshDraft d, List<Vector2> run, Func<float, float, float> ground, float h, Vector2 inside, bool hedge, bool bars = true)
        {
            int plinth = bars ? d.Slot("mat/elite/plinth") : -1, pier = bars ? d.Slot("mat/elite/pier") : -1, iron = bars ? d.Slot("mat/iron") : -1;
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                float len = Vector2.Distance(a, b);
                if (len < 0.05f) continue;
                Vector2 dir = (b - a) / len;
                if (!bars)
                {
                    if (hedge) EliteHedge(d, a, b, dir, ground, h, inside);
                    continue;
                }
                Vector3 d3 = new Vector3(dir.x, 0f, dir.y), n3 = new Vector3(dir.y, 0f, -dir.x);
                int bays = Mathf.Max(1, Mathf.RoundToInt(len / 3f));
                for (int p = 0; p < bays; p++)
                {
                    Vector2 pa = Vector2.Lerp(a, b, (float)p / bays), pb = Vector2.Lerp(a, b, (float)(p + 1) / bays);
                    float ya = ground(pa.x, pa.y), yb = ground(pb.x, pb.y), y0 = Mathf.Min(ya, yb) - 0.2f;
                    d.Beam(plinth, new Vector3(pa.x, 0f, pa.y), new Vector3(pb.x, 0f, pb.y), 0.4f, y0, Mathf.Max(ya, yb) + 0.6f);
                    float bl = Vector2.Distance(pa, pb);
                    for (float s = 0.3f; s < bl - 0.25f; s += 0.16f)
                    {
                        Vector2 q = pa + dir * s;
                        float yq = Mathf.Lerp(ya, yb, s / bl);
                        Vector3 bottom = new Vector3(q.x, yq + 0.6f, q.y), top = new Vector3(q.x, yq + h - 0.1f, q.y);
                        Vector3 w = d3 * 0.018f;
                        d.QuadBoth(iron, bottom - w, top - w, top + w, bottom + w);
                    }
                    Vector3 ra = new Vector3(pa.x, ya + h - 0.15f, pa.y), rb = new Vector3(pb.x, yb + h - 0.15f, pb.y);
                    d.QuadFacing(iron, ra + n3 * 0.025f, ra + n3 * 0.025f + Vector3.up * 0.06f, rb + n3 * 0.025f + Vector3.up * 0.06f, rb + n3 * 0.025f, n3);
                    d.QuadFacing(iron, ra - n3 * 0.025f, ra - n3 * 0.025f + Vector3.up * 0.06f, rb - n3 * 0.025f + Vector3.up * 0.06f, rb - n3 * 0.025f, -n3);
                    d.QuadFacing(iron, ra + n3 * 0.025f + Vector3.up * 0.06f, ra - n3 * 0.025f + Vector3.up * 0.06f, rb - n3 * 0.025f + Vector3.up * 0.06f, rb + n3 * 0.025f + Vector3.up * 0.06f, Vector3.up);
                }
                for (int p = 0; p <= bays; p++)
                {
                    Vector2 q = Vector2.Lerp(a, b, (float)p / bays);
                    float yq = ground(q.x, q.y);
                    d.Box(pier, new Vector3(q.x, yq + h / 2f - 0.1f, q.y), new Vector3(0.5f, h + 0.2f, 0.5f), Quaternion.LookRotation(d3));
                    d.Box(pier, new Vector3(q.x, yq + h + 0.15f, q.y), new Vector3(0.62f, 0.1f, 0.62f), Quaternion.LookRotation(d3));
                }
                if (hedge) EliteHedge(d, a, b, dir, ground, h, inside);
            }
        }

        private static void EliteHedge(MeshDraft d, Vector2 a, Vector2 b, Vector2 dir, Func<float, float, float> ground, float h, Vector2 inside)
        {
            Vector2 mid = (a + b) / 2f;
            float side = Vector2.Dot(inside - mid, new Vector2(dir.y, -dir.x)) >= 0f ? 1f : -1f;
            Vector2 off = new Vector2(dir.y, -dir.x) * (0.9f * side);
            Hedge(d, new List<Vector2> { a + off, b + off }, ground, h - 0.3f, "mat/hedge/thuja", 0.8f);
        }

        // Taller piers with a lamp on each side of every opening.
        private static void GatePosts(MeshDraft d, List<Vector2> run, Func<float, float, float> ground, string fence)
        {
            if (run.Count < 2 || fence == "hedge") return;
            bool elite = fence == "elite";
            foreach (Vector2 p in new[] { run[0], run[run.Count - 1] })
            {
                float y = ground(p.x, p.y);
                float h = elite ? 2.8f : fence == "picket" ? 1.2f : 1.7f;
                int slot = d.Slot(elite ? "mat/elite/pier" : fence == "picket" ? "mat/fence/picket" : "mat/fence/wooden");
                float w = elite ? 0.8f : 0.16f;
                d.Box(slot, new Vector3(p.x, y + h / 2f - 0.1f, p.y), new Vector3(w, h + 0.2f, w), Quaternion.identity);
                if (elite) d.Box(d.Slot("mat/glass_lit"), new Vector3(p.x, y + h + 0.3f, p.y), new Vector3(0.35f, 0.45f, 0.35f), Quaternion.identity);
            }
        }

        private static void Collider(MeshDraft col, List<Vector2> run, Func<float, float, float> ground, float h, float width)
        {
            int slot = col.Slot("collision");
            for (int i = 0; i + 1 < run.Count; i++)
            {
                Vector2 a = run[i], b = run[i + 1];
                if (Vector2.Distance(a, b) < 0.05f) continue;
                float y0 = Mathf.Min(ground(a.x, a.y), ground(b.x, b.y)) - 0.5f;
                float y1 = Mathf.Max(ground(a.x, a.y), ground(b.x, b.y)) + h;
                col.Beam(slot, new Vector3(a.x, 0f, a.y), new Vector3(b.x, 0f, b.y), width, y0, y1);
            }
        }

        private static void Tube(MeshDraft d, int slot, Vector3 a, Vector3 b, float r, int sides)
        {
            Vector3 axis = (b - a).normalized;
            Vector3 u = Vector3.Cross(axis, Vector3.up);
            if (u.sqrMagnitude < 1e-4f) u = Vector3.right;
            u.Normalize();
            Vector3 v = Vector3.Cross(u, axis);
            for (int s = 0; s < sides; s++)
            {
                float a0 = s * Mathf.PI * 2f / sides, a1 = (s + 1) * Mathf.PI * 2f / sides;
                Vector3 o0 = (u * Mathf.Cos(a0) + v * Mathf.Sin(a0)) * r, o1 = (u * Mathf.Cos(a1) + v * Mathf.Sin(a1)) * r;
                d.QuadFacing(slot, a + o0, b + o0, b + o1, a + o1, o0 + o1);
            }
        }
    }
}
