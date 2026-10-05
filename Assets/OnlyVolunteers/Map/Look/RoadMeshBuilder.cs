using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // One generated mesh chunk before district merging: what it is, where it belongs and whether it collides.
    public sealed class LookPiece
    {
        public string Name, District = "common", Category;
        public MeshDraft Draft;
        public bool Collide;
        public Vector3 Centre;
    }

    // Road surfaces draped on the baked terrain (+4 cm, no collider; the terrain carries the van): ribbons resampled
    // every 2 m with 4 vertices across and chipped edges on worn asphalt and dirt, junction patches, kerbed sidewalks
    // (colliders; kerbs only where the plan gives sidewalks: old town, bad district, elite), road paint, parking lots,
    // hard ground overlays, the railway, bridge decks and culvert mouths. Runtime-safe.
    public static class RoadMeshBuilder
    {
        public const float RoadLift = 0.04f, JunctionLift = 0.05f, PaintLift = 0.065f, GroundLift = 0.03f;

        public static List<LookPiece> Build(LookData d, Func<float, float, float> ground, List<BridgeDeck> decks)
        {
            float Surface(float x, float z) => MapHeightSampler.DeckHeight(decks, x, z, out float h) ? h : ground(x, z);
            var pieces = new List<LookPiece>();
            foreach (LookRoad r in d.roads) Road(pieces, r, Surface, d.seed);
            foreach (LookJunction j in d.junctions) Junction(pieces, d, j, Surface);
            foreach (LookSidewalk s in d.sidewalks) Sidewalk(pieces, d, s, ground);
            Markings(pieces, d, Surface);
            foreach (LookParking p in d.parking) Parking(pieces, p, ground);
            foreach (LookGround g in d.ground)
                if (!g.soft)
                    HardGround(pieces, g, ground);
            Rail(pieces, d, ground);
            foreach (BridgeDeck deck in decks) Bridge(pieces, deck, ground);
            foreach (LookCrossing c in d.crossings)
                if (c.kind == "culvert" || c.kind == "outlet")
                    Culvert(pieces, c, ground);
            return pieces;
        }

        // Bridge decks from the crossings: ends sit on the flattened road terrain just outside the channel. The deck
        // follows the road piece that crosses (the road curves over the bridge), so parapets stay outside the lane.
        public static List<BridgeDeck> Decks(LookData d, Func<float, float, float> ground)
        {
            var list = new List<BridgeDeck>();
            foreach (LookCrossing c in d.crossings)
            {
                if (c.kind != "bridge" || c.pts.Length < 4) continue;
                var a = new Vector2(c.pts[0], c.pts[1]);
                var b = new Vector2(c.pts[c.pts.Length - 2], c.pts[c.pts.Length - 1]);
                Vector2 dir = (b - a).normalized;
                a -= dir * 1.5f;
                b += dir * 1.5f;
                float half = c.w / 2f;
                float[] path = new float[0];
                LookRoad road = CrossingRoad(d, c, (a + b) / 2f);
                if (road != null)
                {
                    float[] cum = LookGeom.Cumulative(road.pts);
                    float sa = ArcAt(road.pts, cum, a), sb = ArcAt(road.pts, cum, b);
                    float s0 = Mathf.Max(0f, Mathf.Min(sa, sb)), s1 = Mathf.Min(cum[cum.Length - 1], Mathf.Max(sa, sb));
                    if (s1 - s0 > 2f)
                    {
                        path = LookGeom.SubPolyline(road.pts, cum, s0, s1);
                        if (sa > sb) path = Reverse(path);
                        a = new Vector2(path[0], path[1]);
                        b = new Vector2(path[path.Length - 2], path[path.Length - 1]);
                        half = Mathf.Max(half, road.w / 2f + 0.5f);
                    }
                }
                list.Add(new BridgeDeck { Id = c.id, A = a, B = b, HeightA = ground(a.x, a.y), HeightB = ground(b.x, b.y), HalfWidth = half, Path = path });
            }
            return list;
        }

        // The piece of the crossing's road that passes closest to the bridge centre (within 10 m).
        private static LookRoad CrossingRoad(LookData d, LookCrossing c, Vector2 mid)
        {
            LookRoad best = null;
            float bestDist = 10f;
            foreach (LookRoad r in d.roads)
            {
                if (r.road != c.road || LookGeom.Count(r.pts) < 2) continue;
                float dist = LookGeom.DistToPolyline(r.pts, mid.x, mid.y, false, out _, out _);
                if (dist >= bestDist) continue;
                bestDist = dist;
                best = r;
            }
            return best;
        }

        private static float ArcAt(float[] pts, float[] cum, Vector2 p)
        {
            LookGeom.DistToPolyline(pts, p.x, p.y, false, out int seg, out float t);
            return cum[seg] + (cum[seg + 1] - cum[seg]) * t;
        }

        private static float[] Reverse(float[] pts)
        {
            int n = pts.Length / 2;
            var r = new float[pts.Length];
            for (int i = 0; i < n; i++)
            {
                r[2 * i] = pts[2 * (n - 1 - i)];
                r[2 * i + 1] = pts[2 * (n - 1 - i) + 1];
            }
            return r;
        }

        private static string RoadMat(LookRoad r) => r.surface switch
        {
            "dirt" => "mat/road/dirt",
            "boardwalk" => "mat/road/boardwalk",
            "asphalt_worn" => r.district == "elite" ? "mat/road/asphalt_elite" : "mat/road/asphalt_worn",
            _ => r.district == "elite" ? "mat/road/asphalt_elite" : "mat/road/asphalt",
        };

        private static void Road(List<LookPiece> pieces, LookRoad r, Func<float, float, float> surface, int seed)
        {
            if (LookGeom.Count(r.pts) < 2) return;
            float[] cum = LookGeom.Cumulative(r.pts);
            float total = cum[cum.Length - 1], s0 = Mathf.Max(0f, r.trim_start), s1 = total - Mathf.Max(0f, r.trim_end);
            if (s1 - s0 < 0.3f) return;
            float[] line = LookGeom.Resample(LookGeom.SubPolyline(r.pts, cum, s0, s1), 2f, out _);
            int n = LookGeom.Count(line);
            float hw = r.w / 2f;
            bool chipped = r.surface == "asphalt_worn" || r.surface == "dirt";
            float chip = r.surface == "dirt" ? 0.35f : 0.15f;
            int rs = seed * 7919 + LookGeom.StableHash(r.id);
            var rows = new List<Vector3[]>(n);
            for (int i = 0; i < n; i++)
            {
                LookGeom.Normal(line, i, n, out float nx, out float ny, out float miter);
                float x = line[2 * i], z = line[2 * i + 1];
                float l = hw * miter, rr = hw * miter;
                if (chipped)
                {
                    l -= LookGeom.Clamp01(LookGeom.Noise(x * 0.7f, z * 0.7f, rs) * 0.5f + 0.5f) * chip;
                    rr -= LookGeom.Clamp01(LookGeom.Noise(x * 0.7f + 31f, z * 0.7f, rs) * 0.5f + 0.5f) * chip;
                }
                float[] offs = { l, l / 3f, -rr / 3f, -rr };
                var row = new Vector3[4];
                for (int k = 0; k < 4; k++)
                {
                    float px = x + nx * offs[k], pz = z + ny * offs[k];
                    row[k] = new Vector3(px, surface(px, pz) + RoadLift, pz);
                }
                rows.Add(row);
            }
            var draft = new MeshDraft();
            draft.Ribbon(draft.Slot(RoadMat(r)), rows);
            pieces.Add(new LookPiece { Name = r.id, District = r.district, Category = "road", Draft = draft, Centre = rows[n / 2][1] });
        }

        private static void Junction(List<LookPiece> pieces, LookData d, LookJunction j, Func<float, float, float> surface)
        {
            if (j.tris.Length < 6) return;
            string mat = "mat/road/asphalt";
            foreach (LookRoad r in d.roads)
                if (Array.IndexOf(j.roads, r.road) >= 0 && r.pts.Length >= 4 &&
                    (LookGeom.Dist(r.pts[0], r.pts[1], j.x, j.y) < 8f || LookGeom.Dist(r.pts[r.pts.Length - 2], r.pts[r.pts.Length - 1], j.x, j.y) < 8f))
                {
                    mat = RoadMat(r);
                    if (r.cls == "highway" || r.cls == "town_street") break;
                }
            var draft = new MeshDraft();
            Drape(draft, draft.Slot(mat), j.tris, surface, JunctionLift, 3f);
            pieces.Add(new LookPiece { Name = j.id, Category = "road", Draft = draft, Centre = new Vector3(j.x, surface(j.x, j.y), j.y) });
        }

        // Triangles subdivided until their edges are under maxEdge, then each vertex dropped onto the surface.
        public static void Drape(MeshDraft draft, int slot, float[] tris, Func<float, float, float> surface, float lift, float maxEdge)
        {
            for (int i = 0; i + 5 < tris.Length; i += 6)
                DrapeTri(draft, slot, new Vector2(tris[i], tris[i + 1]), new Vector2(tris[i + 2], tris[i + 3]), new Vector2(tris[i + 4], tris[i + 5]),
                    surface, lift, maxEdge, 0);
        }

        private static void DrapeTri(MeshDraft draft, int slot, Vector2 a, Vector2 b, Vector2 c, Func<float, float, float> surface, float lift, float maxEdge, int depth)
        {
            float longest = Mathf.Max((a - b).magnitude, Mathf.Max((b - c).magnitude, (c - a).magnitude));
            if (longest > maxEdge && depth < 5)
            {
                Vector2 ab = (a + b) / 2f, bc = (b + c) / 2f, ca = (c + a) / 2f;
                DrapeTri(draft, slot, a, ab, ca, surface, lift, maxEdge, depth + 1);
                DrapeTri(draft, slot, ab, b, bc, surface, lift, maxEdge, depth + 1);
                DrapeTri(draft, slot, ca, bc, c, surface, lift, maxEdge, depth + 1);
                DrapeTri(draft, slot, ab, bc, ca, surface, lift, maxEdge, depth + 1);
                return;
            }
            draft.TriFacing(slot, new Vector3(a.x, surface(a.x, a.y) + lift, a.y), new Vector3(b.x, surface(b.x, b.y) + lift, b.y),
                new Vector3(c.x, surface(c.x, c.y) + lift, c.y), Vector3.up);
        }

        // Sidewalk on its centreline: raised slab with a bevelled kerb (<= 12 cm) on the road side.
        private static void Sidewalk(List<LookPiece> pieces, LookData d, LookSidewalk s, Func<float, float, float> ground)
        {
            if (LookGeom.Count(s.pts) < 2) return;
            float[] line = LookGeom.Resample(s.pts, 2f, out _);
            int n = LookGeom.Count(line);
            float roadSide = RoadSide(d, s, line);
            float hw = s.w / 2f, curb = Mathf.Clamp(s.curb, 0.04f, 0.12f);
            var top = new List<Vector3[]>(n);
            var kerb = new List<Vector3[]>(n);
            for (int i = 0; i < n; i++)
            {
                LookGeom.Normal(line, i, n, out float nx, out float ny, out float miter);
                float x = line[2 * i], z = line[2 * i + 1];
                Vector3 P(float off, float lift)
                {
                    float o = off * roadSide * Mathf.Min(miter, 1.5f);
                    float px = x + nx * o, pz = z + ny * o;
                    return new Vector3(px, ground(px, pz) + lift, pz);
                }
                // Offsets measured towards the road: -hw is the far edge, +hw the kerb line.
                var t = new[] { P(-hw - 0.1f, 0.02f), P(-hw, curb), P(0f, curb), P(hw - 0.18f, curb) };
                var k = new[] { P(hw - 0.18f, curb), P(hw, curb), P(hw + 0.12f, RoadLift) };
                if (roadSide < 0f)
                {
                    Array.Reverse(t);
                    Array.Reverse(k);
                }
                top.Add(t);
                kerb.Add(k);
            }
            var draft = new MeshDraft();
            string district = string.IsNullOrEmpty(s.district) ? "common" : s.district;
            draft.Ribbon(draft.Slot("mat/sidewalk/" + district), top);
            draft.Ribbon(draft.Slot(district == "elite" ? "mat/curb/white" : "mat/curb"), kerb);
            pieces.Add(new LookPiece { Name = $"Sidewalk_{s.road}_{s.side}", District = district, Category = "sidewalk", Draft = draft, Collide = true, Centre = top[n / 2][1] });
        }

        // +1 when the road lies to the left of the sidewalk's direction (positive offsets point to the road).
        private static float RoadSide(LookData d, LookSidewalk s, float[] line)
        {
            int n = LookGeom.Count(line), mid = n / 2;
            float x = line[2 * mid], z = line[2 * mid + 1];
            float best = float.MaxValue, bx = x, bz = z;
            foreach (LookRoad r in d.roads)
            {
                if (!string.IsNullOrEmpty(s.road) && r.road != s.road) continue;
                float dd = LookGeom.DistToPolyline(r.pts, x, z, false, out int seg, out float t);
                if (dd >= best) continue;
                best = dd;
                bx = Mathf.Lerp(r.pts[2 * seg], r.pts[2 * seg + 2], t);
                bz = Mathf.Lerp(r.pts[2 * seg + 1], r.pts[2 * seg + 3], t);
            }
            if (best == float.MaxValue && !string.IsNullOrEmpty(s.road))
            {
                var any = new LookSidewalk { road = "", pts = s.pts };
                return RoadSide(d, any, line);
            }
            LookGeom.Normal(line, mid, n, out float nx, out float ny, out _);
            return (bx - x) * nx + (bz - z) * ny >= 0f ? 1f : -1f;
        }

        private static void Markings(List<LookPiece> pieces, LookData d, Func<float, float, float> surface)
        {
            foreach (LookMarking m in d.markings)
            {
                if (LookGeom.Count(m.pts) < 2) continue;
                var draft = new MeshDraft();
                int white = draft.Slot("mat/marking");
                if (m.kind == "zebra") Zebra(draft, white, m, surface);
                else Line(draft, white, m.pts, m.w, m.dash, m.gap, surface);
                if (!draft.IsEmpty)
                    pieces.Add(new LookPiece { Name = "Marking_" + m.road, Category = "paint", Draft = draft, Centre = new Vector3(m.pts[0], 0f, m.pts[1]) });
            }
        }

        // Painted line along a polyline; dash 0 means continuous.
        public static void Line(MeshDraft draft, int slot, float[] pts, float width, float dash, float gap, Func<float, float, float> surface, float lift = PaintLift)
        {
            float[] cum = LookGeom.Cumulative(pts);
            float total = cum[cum.Length - 1];
            bool solid = dash <= 0.01f;
            float step = solid ? 2f : dash + Mathf.Max(0.1f, gap);
            for (float s = 0f; s < total - 0.05f; s += step)
            {
                float e = Mathf.Min(total, s + (solid ? step : dash));
                LookGeom.PointAt(pts, cum, s, false, out float ax, out float az, out float tx, out float tz);
                LookGeom.PointAt(pts, cum, e, false, out float bx, out float bz, out float ux, out float uz);
                Vector3 na = new Vector3(-tz, 0f, tx) * (width / 2f), nb = new Vector3(-uz, 0f, ux) * (width / 2f);
                Vector3 a = new Vector3(ax, 0f, az), b = new Vector3(bx, 0f, bz);
                draft.QuadFacing(slot, Lift(a - na, surface, lift), Lift(a + na, surface, lift), Lift(b + nb, surface, lift), Lift(b - nb, surface, lift), Vector3.up);
            }
        }

        private static Vector3 Lift(Vector3 p, Func<float, float, float> surface, float lift) => new(p.x, surface(p.x, p.z) + lift, p.z);

        private static void Zebra(MeshDraft draft, int slot, LookMarking m, Func<float, float, float> surface)
        {
            var a = new Vector3(m.pts[0], 0f, m.pts[1]);
            var b = new Vector3(m.pts[2], 0f, m.pts[3]);
            Vector3 across = b - a;
            float len = across.magnitude;
            if (len < 0.5f) return;
            across /= len;
            Vector3 along = new Vector3(-across.z, 0f, across.x) * (Mathf.Max(1f, m.w) / 2f);
            float stripe = Mathf.Max(0.2f, m.dash), gap = Mathf.Max(0.2f, m.gap);
            for (float s = 0f; s + stripe <= len + 0.01f; s += stripe + gap)
            {
                Vector3 p0 = a + across * s, p1 = a + across * (s + stripe);
                draft.QuadFacing(slot, Lift(p0 - along, surface, PaintLift), Lift(p0 + along, surface, PaintLift), Lift(p1 + along, surface, PaintLift),
                    Lift(p1 - along, surface, PaintLift), Vector3.up);
            }
        }

        private static void Parking(List<LookPiece> pieces, LookParking p, Func<float, float, float> ground)
        {
            if (p.tris.Length < 6) return;
            var draft = new MeshDraft();
            Drape(draft, draft.Slot("mat/ground/" + (string.IsNullOrEmpty(p.mat) ? "asphalt" : p.mat)), p.tris, ground, GroundLift + 0.01f, 3f);
            int line = draft.Slot("mat/parking/line");
            for (int k = 0; k + 4 < p.stalls.Length; k += 5)
            {
                Quaternion q = LookConvert.Yaw(p.stalls[k + 4]);
                Vector3 c = new Vector3(p.stalls[k], 0f, p.stalls[k + 1]);
                Vector3 ax = q * Vector3.right * (p.stalls[k + 2] / 2f), az = q * Vector3.forward * (p.stalls[k + 3] / 2f);
                // Record is [cx, cy, width, depth, yaw of depth]; if an older json has them swapped, paint along the long axis.
                if (p.stalls[k + 2] > p.stalls[k + 3]) (ax, az) = (az, ax);
                for (int side = -1; side <= 1; side += 2)
                {
                    Vector3 o = c + ax * side;
                    Line(draft, line, new[] { o.x - az.x, o.z - az.z, o.x + az.x, o.z + az.z }, 0.1f, 0f, 0f, ground, GroundLift + 0.03f);
                }
            }
            LookGeom.Centroid(p.pts, out float cx, out float cz);
            pieces.Add(new LookPiece { Name = p.id, Category = "ground", Draft = draft, Centre = new Vector3(cx, ground(cx, cz), cz) });
        }

        private static void HardGround(List<LookPiece> pieces, LookGround g, Func<float, float, float> ground)
        {
            if (g.tris.Length < 6) return;
            string mat = g.mat == "paving" && g.ctx != null && g.ctx.Contains("square") ? "cobble" : g.mat;
            var draft = new MeshDraft();
            Drape(draft, draft.Slot("mat/ground/" + mat), g.tris, ground, GroundLift + g.prio * 0.0003f, 3f);
            LookGeom.Centroid(g.pts, out float cx, out float cz);
            pieces.Add(new LookPiece { Name = "Ground_" + g.ctx, Category = "ground", Draft = draft, Centre = new Vector3(cx, ground(cx, cz), cz) });
        }

        // Ballast bed, sleepers and two rails; at level crossings only the rails stay, flush with the road.
        private static void Rail(List<LookPiece> pieces, LookData d, Func<float, float, float> ground)
        {
            if (LookGeom.Count(d.rail.pts) < 2) return;
            float[] line = LookGeom.Resample(d.rail.pts, 2f, out float[] arc);
            int n = LookGeom.Count(line);
            var draft = new MeshDraft();
            int ballast = draft.Slot("mat/ballast"), sleeper = draft.Slot("mat/sleeper"), steel = draft.Slot("mat/rail/steel");
            bool NearCrossing(float x, float z)
            {
                foreach (LookRailCrossing c in d.rail.crossings)
                    if (LookGeom.Dist(x, z, c.x, c.y) < 5f) return true;
                return false;
            }
            var rows = new List<Vector3[]>();
            void Flush()
            {
                if (rows.Count >= 2) draft.Ribbon(ballast, rows);
                rows.Clear();
            }
            for (int i = 0; i < n; i++)
            {
                float x = line[2 * i], z = line[2 * i + 1];
                if (NearCrossing(x, z))
                {
                    Flush();
                    continue;
                }
                LookGeom.Normal(line, i, n, out float nx, out float nz, out _);
                float[] offs = { 1.8f, 1.25f, -1.25f, -1.8f };
                float[] lifts = { 0.02f, 0.28f, 0.28f, 0.02f };
                var row = new Vector3[4];
                for (int k = 0; k < 4; k++)
                {
                    float px = x + nx * offs[k], pz = z + nz * offs[k];
                    row[k] = new Vector3(px, ground(px, pz) + lifts[k], pz);
                }
                rows.Add(row);
            }
            Flush();
            float[] cum = LookGeom.Cumulative(line);
            float total = cum[cum.Length - 1];
            for (float s = 0.5f; s < total; s += 0.9f)
            {
                LookGeom.PointAt(line, cum, s, false, out float x, out float z, out float tx, out float tz);
                if (NearCrossing(x, z)) continue;
                float y = ground(x, z) + 0.28f;
                draft.Box(sleeper, new Vector3(x, y + 0.06f, z), new Vector3(2.4f, 0.12f, 0.24f), Quaternion.LookRotation(new Vector3(tx, 0f, tz)));
            }
            for (int i = 0; i + 1 < n; i++)
            {
                float ax = line[2 * i], az = line[2 * i + 1], bx = line[2 * i + 2], bz = line[2 * i + 3];
                bool crossing = NearCrossing(ax, az) || NearCrossing(bx, bz);
                LookGeom.Normal(line, i, n, out float nx, out float nz, out _);
                LookGeom.Normal(line, i + 1, n, out float mx, out float mz, out _);
                for (int side = -1; side <= 1; side += 2)
                {
                    var a = new Vector3(ax + nx * 0.72f * side, 0f, az + nz * 0.72f * side);
                    var b = new Vector3(bx + mx * 0.72f * side, 0f, bz + mz * 0.72f * side);
                    float y0 = crossing ? RoadLift : 0.4f;
                    a.y = ground(a.x, a.z) + y0;
                    b.y = ground(b.x, b.z) + y0;
                    Vector3 h = Vector3.up * 0.14f, w = Vector3.Cross(Vector3.up, (b - a).normalized) * 0.04f;
                    draft.QuadFacing(steel, a + h - w, b + h - w, b + h + w, a + h + w, Vector3.up);
                    draft.QuadFacing(steel, a - w, b - w, b + h - w, a + h - w, -w);
                    draft.QuadFacing(steel, a + w, b + w, b + h + w, a + h + w, w);
                }
            }
            pieces.Add(new LookPiece { Name = "Railway", Category = "rail", Draft = draft, Centre = new Vector3(line[2 * (n / 2)], 0f, line[2 * (n / 2) + 1]) });
        }

        // Concrete deck under the road ribbon, low parapets, abutments down into the channel; built along the deck
        // centreline (the road's curve), so the parapets keep their distance from the lane edge all the way across.
        private static void Bridge(List<LookPiece> pieces, BridgeDeck deck, Func<float, float, float> ground)
        {
            var draft = new MeshDraft();
            int conc = draft.Slot("mat/bridge"), surf = draft.Slot("mat/road/asphalt");
            float[] line = LookGeom.Resample(deck.Centreline(), 2f, out float[] arc);
            int n = LookGeom.Count(line);
            if (n < 2) return;
            float total = Mathf.Max(0.01f, arc[n - 1]);
            var centre = new Vector3[n];
            var side = new Vector3[n];
            for (int i = 0; i < n; i++)
            {
                LookGeom.Normal(line, i, n, out float nx, out float nz, out float miter);
                centre[i] = new Vector3(line[2 * i], Mathf.Lerp(deck.HeightA, deck.HeightB, arc[i] / total), line[2 * i + 1]);
                side[i] = new Vector3(nx, 0f, nz) * (deck.HalfWidth * Mathf.Min(miter, 1.5f));
            }
            Vector3 down = Vector3.up * -0.7f, up = Vector3.up * 0.7f;
            for (int i = 0; i + 1 < n; i++)
            {
                Vector3 a = centre[i], b = centre[i + 1];
                draft.QuadFacing(surf, a - side[i], a + side[i], b + side[i + 1], b - side[i + 1], Vector3.up);
                draft.QuadFacing(conc, a - side[i] + down, a + side[i] + down, b + side[i + 1] + down, b - side[i + 1] + down, Vector3.down);
                for (int s = -1; s <= 1; s += 2)
                {
                    Vector3 oa = side[i] * s, ob = side[i + 1] * s, facing = (oa + ob).normalized;
                    Vector3 ia = -oa.normalized * 0.3f, ib = -ob.normalized * 0.3f;
                    draft.QuadFacing(conc, a + oa, b + ob, b + ob + down, a + oa + down, facing);
                    draft.QuadFacing(conc, a + oa, b + ob, b + ob + up, a + oa + up, facing);
                    draft.QuadFacing(conc, a + oa + ia, b + ob + ib, b + ob + ib + up, a + oa + ia + up, -facing);
                    draft.QuadFacing(conc, a + oa + up, b + ob + up, b + ob + ib + up, a + oa + ia + up, Vector3.up);
                }
            }
            for (int e = 0; e < 2; e++)
            {
                int i = e == 0 ? 0 : n - 1, j = e == 0 ? 1 : n - 2;
                Vector3 end = centre[i], tangent = centre[i] - centre[j];
                tangent.y = 0f;
                if (tangent.sqrMagnitude < 1e-6f) tangent = Vector3.forward;
                float bed = ground(end.x, end.z) - 2.5f;
                draft.Box(conc, new Vector3(end.x, (end.y - 0.7f + bed) / 2f, end.z), new Vector3(deck.HalfWidth * 2f + 0.6f, end.y - 0.7f - bed, 1.2f),
                    Quaternion.LookRotation(tangent.normalized));
            }
            pieces.Add(new LookPiece { Name = "Bridge_" + deck.Id, Category = "bridge", Draft = draft, Collide = true, Centre = (centre[0] + centre[n - 1]) / 2f });
        }

        // Concrete headwalls with a dark pipe mouth where a river passes under a road embankment.
        private static void Culvert(List<LookPiece> pieces, LookCrossing c, Func<float, float, float> ground)
        {
            if (c.pts.Length < 4) return;
            var draft = new MeshDraft();
            int conc = draft.Slot("mat/concrete"), dark = draft.Slot("mat/iron");
            var mouths = new List<(Vector3 p, Vector3 n)>();
            if (c.kind == "outlet")
            {
                int n = LookGeom.Count(c.pts);
                var p0 = new Vector3(c.pts[0], 0f, c.pts[1]);
                var p1 = new Vector3(c.pts[2], 0f, c.pts[3]);
                var q0 = new Vector3(c.pts[2 * n - 2], 0f, c.pts[2 * n - 1]);
                var q1 = new Vector3(c.pts[2 * n - 4], 0f, c.pts[2 * n - 3]);
                mouths.Add((p0, (p0 - p1).normalized));
                mouths.Add((q0, (q0 - q1).normalized));
            }
            else
            {
                var a = new Vector3(c.pts[0], 0f, c.pts[1]);
                var b = new Vector3(c.pts[c.pts.Length - 2], 0f, c.pts[c.pts.Length - 1]);
                Vector3 along = (b - a).normalized, across = new Vector3(-along.z, 0f, along.x);
                Vector3 mid = new Vector3(c.x, 0f, c.y);
                mouths.Add((mid + across * (c.w / 2f + 2.5f), across));
                mouths.Add((mid - across * (c.w / 2f + 2.5f), -across));
            }
            foreach (var (p, n) in mouths)
            {
                float y = ground(p.x, p.z);
                Quaternion rot = Quaternion.LookRotation(n);
                draft.Box(conc, new Vector3(p.x, y + 0.2f, p.z), new Vector3(3.2f, 1.6f, 0.4f), rot);
                Vector3 face = new Vector3(p.x, y + 0.1f, p.z) + n * 0.21f, side = rot * Vector3.right;
                draft.QuadFacing(dark, face - side * 0.6f - Vector3.up * 0.5f, face - side * 0.6f + Vector3.up * 0.6f, face + side * 0.6f + Vector3.up * 0.6f, face + side * 0.6f - Vector3.up * 0.5f, n);
            }
            pieces.Add(new LookPiece { Name = "Culvert_" + c.id, Category = "prop", Draft = draft, Centre = new Vector3(c.x, 0f, c.y) });
        }
    }
}
