using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Box collider that is not part of the footprint prism (canopy columns, poles). Optional ones are dropped by the
    // builder when they would stand on a road (van parity).
    public struct ExtraCollider
    {
        public Vector3 Centre, Size;
        public Quaternion Rotation;
        public bool Optional;
    }

    // Output of ProceduralBuilding, in the building's local space (origin = footprint centroid at pad height).
    public sealed class BuildingResult
    {
        public MeshDraft Render;
        public Mesh Collision;
        public string[] Slots;
        public Pose Sign;
        public bool HasSign;
        public float SignWidth, SignHeight;
        public string SignText = "";
        public Color SignTextColor = Color.black;
        public Pose[] Doors = new Pose[0];
        public readonly List<ExtraCollider> Colliders = new();
        public int Triangles;
    }

    // Low-poly procedural building from a look json record and a BuildingStyle: per-edge walls (safe for concave
    // footprints) with plinth, window bays (inset up to 4 floors, flat quads above), floor bands, doors, canopies,
    // panel balconies and stair strips; flat roofs with parapet or gable/hip/shed roofs per footprint rectangle; plus
    // the landmark generators (water tower, chimney, church domes, casino crown, bowling pin). Runtime-safe.
    public static class ProceduralBuilding
    {
        private struct Edge
        {
            public int Index;
            public Vector3 A, B, Dir, N;
            public float Len;
        }

        private struct Door
        {
            public int Edge;
            public float U;
        }

        private struct Rect
        {
            public Vector3 C, U, V;
            public float Hu, Hv;
        }

        private sealed class Ctx
        {
            public LookBuilding B;
            public BuildingStyle S;
            public MeshDraft D;
            public BuildingResult R;
            public System.Random Rnd;
            public Edge[] Edges;
            public Vector2[] Fp;
            public List<Door> Doors = new();
            public List<Rect> Rects = new();
            public int Front, Floors;
            public float Fh, H, Low, Top, DoorLift;
            public int Wall, Trim, Roof, Plinth, Glass, GlassLit, DoorS, Metal, Concrete, Brick;
        }

        public static BuildingResult Build(LookBuilding b, BuildingStyle s, float padY, float lowestY)
        {
            Ctx c = Setup(b, s, padY, lowestY);
            switch (s.Special)
            {
                case "water_tower": WaterTower(c); break;
                case "chimney": Chimney(c); break;
                case "bus_stop": BusStop(c); break;
                case "ad_pole": AdPole(c); break;
                case "wagon": Wagon(c); break;
                default: Generic(c); break;
            }
            BuildingResult r = c.R;
            r.Render = c.D;
            r.Slots = new string[c.D.Slots.Count];
            for (int i = 0; i < r.Slots.Length; i++) r.Slots[i] = c.D.Slots[i];
            r.Triangles = c.D.TriangleCount;
            var doors = new List<Pose>();
            foreach (Door d in c.Doors)
            {
                Edge e = c.Edges[d.Edge];
                doors.Add(new Pose(At(e, d.U, c.DoorLift, 0.4f), Quaternion.LookRotation(e.N)));
            }
            r.Doors = doors.ToArray();
            if (r.Collision == null && s.Special != "bus_stop" && s.Special != "ad_pole")
            {
                var col = new MeshDraft();
                col.Prism(col.Slot("collision"), c.Fp, c.Low, Mathf.Max(c.Top, 2.5f), true, false);
                r.Collision = col.ToMesh($"{b.id}_collision");
            }
            return r;
        }

        private static Ctx Setup(LookBuilding b, BuildingStyle s, float padY, float lowestY)
        {
            var c = new Ctx { B = b, S = s, D = new MeshDraft(), R = new BuildingResult(), Rnd = new System.Random(b.seed) };
            c.Floors = Mathf.Max(1, b.floors);
            c.Fh = b.floor_h > 0.5f ? b.floor_h : 3f;
            c.H = b.h > 0.5f ? b.h : c.Floors * c.Fh;
            if (string.IsNullOrEmpty(s.Special) || s.Special == "church" || s.Special == "ruin") c.H = c.Floors * c.Fh;
            c.Low = Mathf.Min(-0.3f, lowestY - padY - 0.3f);
            c.Top = c.H;
            c.Fp = LookConvert.Poly(b.fp, b.x, b.y);
            int n = c.Fp.Length;
            var edges = new List<Edge>();
            for (int i = 0; i < n; i++)
            {
                Vector2 a = c.Fp[i], q = c.Fp[(i + 1) % n];
                var A = new Vector3(a.x, 0f, a.y);
                var B = new Vector3(q.x, 0f, q.y);
                float len = Vector3.Distance(A, B);
                Vector3 dir = len > 1e-4f ? (B - A) / len : Vector3.right;
                edges.Add(new Edge { Index = i, A = A, B = B, Dir = dir, N = new Vector3(dir.z, 0f, -dir.x), Len = len });
            }
            c.Edges = edges.ToArray();
            for (int k = 0; k + 4 < b.rects.Length; k += 5)
            {
                Quaternion q = LookConvert.Yaw(b.rects[k + 4]);
                Vector3 ax = q * Vector3.right, az = q * Vector3.forward;
                float sx = b.rects[k + 2], sz = b.rects[k + 3];
                bool zLong = sz >= sx;
                c.Rects.Add(new Rect
                {
                    C = new Vector3(b.rects[k] - b.x, 0f, b.rects[k + 1] - b.y),
                    U = zLong ? az : ax,
                    V = zLong ? ax : az,
                    Hu = (zLong ? sz : sx) / 2f,
                    Hv = (zLong ? sx : sz) / 2f,
                });
            }
            for (int k = 0; k + 2 < b.ent.Length; k += 3)
            {
                var p = new Vector3(b.ent[k] - b.x, 0f, b.ent[k + 1] - b.y);
                int best = 0;
                float bestD = float.MaxValue, bestU = 0f;
                foreach (Edge e in c.Edges)
                {
                    if (e.Len < 0.5f) continue;
                    float u = Mathf.Clamp(Vector3.Dot(p - e.A, e.Dir), 0f, e.Len);
                    float d = Vector3.Distance(e.A + e.Dir * u, p);
                    if (d < bestD)
                    {
                        bestD = d;
                        best = e.Index;
                        bestU = u;
                    }
                }
                float margin = Mathf.Min(s.DoorW / 2f + 0.3f, c.Edges[best].Len / 2f);
                c.Doors.Add(new Door { Edge = best, U = Mathf.Clamp(bestU, margin, c.Edges[best].Len - margin) });
            }
            if (c.Doors.Count > 0) c.Front = c.Doors[0].Edge;
            else
            {
                float bestDot = float.MinValue;
                Vector3 want = LookConvert.Yaw(b.front_deg) * Vector3.forward;
                foreach (Edge e in c.Edges)
                {
                    float d = Vector3.Dot(e.N, want) + e.Len * 0.001f;
                    if (d > bestDot)
                    {
                        bestDot = d;
                        c.Front = e.Index;
                    }
                }
                c.Doors.Add(new Door { Edge = c.Front, U = c.Edges[c.Front].Len / 2f });
            }
            Slots(c);
            c.DoorLift = s.Steps * 0.15f + (s.Porch ? 0.3f : 0f);
            return c;
        }

        // Material slots with the building palette (wall mid, trim light, roof dark - rule 2).
        private static void Slots(Ctx c)
        {
            LookBuilding b = c.B;
            BuildingStyle s = c.S;
            MeshDraft d = c.D;
            c.Wall = d.Slot(s.WallMat, b.wall);
            c.Trim = d.Slot(s.TrimMat, b.trim);
            c.Roof = d.Slot(s.RoofMat, b.roof_col);
            c.Plinth = d.Slot("mat/plinth", s.PlinthHex);
            c.Glass = d.Slot("mat/glass");
            c.GlassLit = d.Slot("mat/glass_lit");
            c.DoorS = d.Slot("mat/door");
            c.Metal = d.Slot("mat/metal");
            c.Concrete = d.Slot("mat/concrete");
            c.Brick = d.Slot("mat/brick");
        }

        private static Vector3 At(Edge e, float u, float y, float off) => e.A + e.Dir * u + e.N * off + Vector3.up * y;

        private static void WallQuad(Ctx c, int slot, Edge e, float u0, float u1, float y0, float y1, float off)
        {
            if (u1 - u0 < 1e-3f || y1 - y0 < 1e-3f) return;
            c.D.Quad(slot, At(e, u0, y0, off), At(e, u0, y1, off), At(e, u1, y1, off), At(e, u1, y0, off));
        }

        private static void Ledge(Ctx c, int slot, Edge e, float u0, float u1, float y, float off0, float off1, bool up)
        {
            c.D.QuadFacing(slot, At(e, u0, y, off0), At(e, u1, y, off0), At(e, u1, y, off1), At(e, u0, y, off1), up ? Vector3.up : Vector3.down);
        }

        // Proud band along an edge: front face plus top and bottom ledges.
        private static void Band(Ctx c, int slot, Edge e, float y0, float y1, float off)
        {
            WallQuad(c, slot, e, -off, e.Len + off, y0, y1, off);
            Ledge(c, slot, e, -off, e.Len + off, y1, 0f, off, true);
            Ledge(c, slot, e, -off, e.Len + off, y0, 0f, off, false);
        }

        // ---------------------------------------------------------------- generic buildings
        private static void Generic(Ctx c)
        {
            BuildingStyle s = c.S;
            bool ruin = s.Special == "ruin";
            foreach (Edge e in c.Edges)
                if (e.Len >= 0.3f)
                    EdgeWalls(c, e, ruin);
            if (ruin) RuinTops(c);
            else Roof(c);
            Doors(c);
            Sign(c);
            Extras(c);
        }

        private static void EdgeWalls(Ctx c, Edge e, bool ruin)
        {
            BuildingStyle s = c.S;
            if (s.PlinthH > 0.05f)
            {
                WallQuad(c, c.Plinth, e, -0.04f, e.Len + 0.04f, c.Low, s.PlinthH, 0.04f);
                Ledge(c, c.Plinth, e, -0.04f, e.Len + 0.04f, s.PlinthH, 0f, 0.04f, true);
            }
            bool inset = c.Floors <= s.InsetMaxFloors && !s.ArchedWindows;
            List<float> cols = Columns(c, e, s.WinW, s.Pitch);
            bool modernSea = s.Modern && e.N.z < -0.2f;
            for (int f = 0; f < c.Floors; f++)
            {
                float y0 = f == 0 ? c.Low : f * c.Fh, y1 = f == c.Floors - 1 ? c.H : (f + 1) * c.Fh;
                if (y1 - y0 < 0.2f) continue;
                float w = s.WinW, wy0 = f * c.Fh + (f == 0 ? Mathf.Max(s.Sill, s.PlinthH + 0.35f) : s.Sill), wy1;
                List<float> row = cols;
                if (s.RibbonWindows && cols.Count > 0) w = Mathf.Max(s.WinW, Spacing(e, cols) - 0.4f);
                if (s.HighBandWindows)
                {
                    if (f != c.Floors - 1) row = Empty;
                    wy0 = Mathf.Max(f * c.Fh + 2.2f, y1 - 1.6f);
                }
                wy1 = Mathf.Min(wy0 + s.WinH, y1 - 0.3f);
                bool shop = f == 0 && (e.Index == c.Front || s.GlassFront && e.Len > 8f) && (s.Shopfront || s.GlassFront);
                if (shop)
                {
                    row = Columns(c, e, 2.6f, s.GlassFront ? 3.0f : 3.4f);
                    w = Mathf.Max(1.6f, Spacing(e, row) - (s.GlassFront ? 0.35f : 0.8f));
                    wy0 = 0.45f + c.DoorLift;
                    wy1 = Mathf.Max(wy0 + 1.4f, Mathf.Min(c.Fh, c.H) - (e.Index == SignEdge(c) ? s.SignH + 0.5f : 0.6f));
                }
                if (modernSea)
                {
                    row = Columns(c, e, 2.4f, 2.8f);
                    w = Mathf.Max(1.6f, Spacing(e, row) - 0.3f);
                    wy0 = f * c.Fh + (f == 0 ? 0.3f : 0.15f);
                    wy1 = Mathf.Min(f * c.Fh + c.Fh - 0.35f, y1 - 0.2f);
                }
                var wins = new List<Vector2>();
                foreach (float uc in row)
                {
                    float u0 = uc - w / 2f, u1 = uc + w / 2f;
                    if (u0 < 0.3f || u1 > e.Len - 0.3f) continue;
                    if (f == 0 && HitsDoor(c, e, uc, w)) continue;
                    if (f > 0 && s.StairStrips && HitsStrip(c, e, uc, w)) continue;
                    wins.Add(new Vector2(u0, u1));
                }
                if (wy1 - wy0 < 0.3f) wins.Clear();
                if (ruin) RuinRow(c, e, y0, y1, wy0, wy1, wins);
                else if (inset && wins.Count > 0 && !shop && !modernSea) InsetRow(c, e, y0, y1, wy0, wy1, wins);
                else FlatRow(c, e, y0, y1, wy0, wy1, wins, shop || modernSea);
                if (s.Balconies && f >= 1 && e.Len >= 14f) Balconies(c, e, f, row);
            }
            if (s.FloorBands)
                for (int f = 1; f < c.Floors; f++)
                    Band(c, c.Trim, e, f * c.Fh - 0.12f, f * c.Fh + 0.08f, 0.06f);
            if (s.Cornice && s.ParapetH <= 0f && c.B.roof == "flat") Band(c, c.Trim, e, c.H - 0.3f, c.H, 0.14f);
            if (s.StairStrips) StairStrips(c, e);
            if (s.NeonStrips)
            {
                int neon = c.D.Slot("mat/neon/strip", c.B.trim);
                float top = c.H + Mathf.Max(0f, s.ParapetH) - 0.3f;
                WallQuad(c, neon, e, 0f, e.Len, top - 0.14f, top, 0.05f);
                if (e.Index == c.Front && c.Floors > 1) WallQuad(c, neon, e, 0f, e.Len, c.Fh - 0.1f, c.Fh + 0.04f, 0.05f);
            }
        }

        private static readonly List<float> Empty = new();

        private static List<float> Columns(Ctx c, Edge e, float winW, float pitch)
        {
            var list = new List<float>();
            float usable = e.Len - 2f * c.S.EdgeMargin;
            if (usable < winW + 0.2f) return list;
            int count = Mathf.Max(1, Mathf.FloorToInt(usable / Mathf.Max(0.5f, pitch)));
            float spacing = usable / count;
            for (int k = 0; k < count; k++) list.Add(c.S.EdgeMargin + spacing * (k + 0.5f));
            return list;
        }

        private static float Spacing(Edge e, List<float> cols) => cols.Count > 1 ? cols[1] - cols[0] : e.Len * 0.6f;

        private static bool HitsDoor(Ctx c, Edge e, float uc, float w)
        {
            foreach (Door d in c.Doors)
                if (d.Edge == e.Index && Mathf.Abs(uc - d.U) < (w + DoorWidth(c)) / 2f + 0.25f)
                    return true;
            return false;
        }

        private static bool HitsStrip(Ctx c, Edge e, float uc, float w)
        {
            foreach (Door d in c.Doors)
                if (d.Edge == e.Index && Mathf.Abs(uc - d.U) < (w + 1.6f) / 2f + 0.1f)
                    return true;
            return false;
        }

        private static float DoorWidth(Ctx c) => c.S.RollerDoor ? 4f : c.S.DoorW;

        private static int GlassSlot(Ctx c) => c.Rnd.NextDouble() < c.S.GlassLit ? c.GlassLit : c.Glass;

        private static void FlatRow(Ctx c, Edge e, float y0, float y1, float wy0, float wy1, List<Vector2> wins, bool bigGlass)
        {
            BuildingStyle s = c.S;
            WallQuad(c, c.Wall, e, 0f, e.Len, y0, y1, 0f);
            float fw = bigGlass ? 0.1f : s.FrameW;
            foreach (Vector2 w in wins)
            {
                WallQuad(c, c.Trim, e, w.x - fw, w.y + fw, wy0 - fw, wy1 + fw, 0.02f);
                int glass = GlassSlot(c);
                WallQuad(c, glass, e, w.x, w.y, wy0, wy1, 0.035f);
                if (s.ArchedWindows) Arch(c, glass, c.Trim, e, (w.x + w.y) / 2f, (w.y - w.x) / 2f, wy1, 0.035f, fw);
                if (s.Bars)
                    for (int k = 1; k <= 3; k++)
                    {
                        float u = Mathf.Lerp(w.x, w.y, k / 4f);
                        WallQuad(c, c.D.Slot("mat/iron"), e, u - 0.025f, u + 0.025f, wy0, wy1, 0.06f);
                    }
                if (!bigGlass) Ledge(c, c.Trim, e, w.x - fw - 0.04f, w.y + fw + 0.04f, wy0 - fw, 0.02f, 0.08f, true);
            }
        }

        // Window holes with reveals: piers between bays, glass set back by the inset depth.
        private static void InsetRow(Ctx c, Edge e, float y0, float y1, float wy0, float wy1, List<Vector2> wins)
        {
            float d = c.S.InsetDepth, fw = c.S.FrameW;
            WallQuad(c, c.Wall, e, 0f, e.Len, y0, wy0, 0f);
            WallQuad(c, c.Wall, e, 0f, e.Len, wy1, y1, 0f);
            float u = 0f;
            foreach (Vector2 w in wins)
            {
                WallQuad(c, c.Wall, e, u, w.x, wy0, wy1, 0f);
                u = w.y;
                int glass = GlassSlot(c);
                Vector3 back = -e.N * d;
                c.D.QuadFacing(c.Trim, At(e, w.x, wy0, 0f), At(e, w.x, wy1, 0f), At(e, w.x, wy1, 0f) + back, At(e, w.x, wy0, 0f) + back, e.Dir);
                c.D.QuadFacing(c.Trim, At(e, w.y, wy0, 0f), At(e, w.y, wy1, 0f), At(e, w.y, wy1, 0f) + back, At(e, w.y, wy0, 0f) + back, -e.Dir);
                c.D.QuadFacing(c.Trim, At(e, w.x, wy1, 0f), At(e, w.y, wy1, 0f), At(e, w.y, wy1, 0f) + back, At(e, w.x, wy1, 0f) + back, Vector3.down);
                c.D.QuadFacing(c.Trim, At(e, w.x, wy0, 0f), At(e, w.y, wy0, 0f), At(e, w.y, wy0, 0f) + back, At(e, w.x, wy0, 0f) + back, Vector3.up);
                WallQuad(c, glass, e, w.x, w.y, wy0, wy1, -d);
                // Mullion and sill ledge in the trim colour.
                WallQuad(c, c.Trim, e, (w.x + w.y) / 2f - fw / 2f, (w.x + w.y) / 2f + fw / 2f, wy0, wy1, -d + 0.01f);
                WallQuad(c, c.Trim, e, w.x - 0.06f, w.y + 0.06f, wy0 - 0.07f, wy0, 0.06f);
                Ledge(c, c.Trim, e, w.x - 0.06f, w.y + 0.06f, wy0, 0f, 0.06f, true);
            }
            WallQuad(c, c.Wall, e, u, e.Len, wy0, wy1, 0f);
        }

        // Roofless ruin: walls seen from both sides, dark window holes, ragged tops added later.
        private static void RuinRow(Ctx c, Edge e, float y0, float y1, float wy0, float wy1, List<Vector2> wins)
        {
            int hole = c.D.Slot("mat/iron");
            WallQuad(c, c.Wall, e, 0f, e.Len, y0, y1, 0f);
            Vector3 inA = -e.N * 0.35f;
            c.D.QuadFacing(c.Wall, e.A + inA + Vector3.up * y0, e.A + inA + Vector3.up * y1, e.B + inA + Vector3.up * y1, e.B + inA + Vector3.up * y0, -e.N);
            foreach (Vector2 w in wins)
            {
                WallQuad(c, hole, e, w.x, w.y, wy0, wy1, 0.02f);
                c.D.QuadFacing(hole, At(e, w.x, wy0, -0.37f), At(e, w.x, wy1, -0.37f), At(e, w.y, wy1, -0.37f), At(e, w.y, wy0, -0.37f), -e.N);
            }
        }

        private static void RuinTops(Ctx c)
        {
            foreach (Edge e in c.Edges)
            {
                if (e.Len < 0.3f) continue;
                int pieces = Mathf.Max(1, Mathf.RoundToInt(e.Len / 3f));
                for (int k = 0; k < pieces; k++)
                {
                    float u0 = e.Len * k / pieces, u1 = e.Len * (k + 1) / pieces;
                    float drop = (float)c.Rnd.NextDouble() * Mathf.Min(1.8f, c.H * 0.4f);
                    float top = c.H - drop;
                    c.D.QuadFacing(c.Wall, At(e, u0, top, 0f), At(e, u1, top, 0f), At(e, u1, top, -0.35f), At(e, u0, top, -0.35f), Vector3.up);
                    WallQuad(c, c.D.Slot("mat/plinth", c.S.PlinthHex), e, u0, u1, top, c.H + 0.01f, 0.005f);
                }
            }
            c.Top = c.H;
        }

        private static void Arch(Ctx c, int fill, int frame, Edge e, float uc, float r, float y, float off, float fw)
        {
            const int segs = 8;
            Vector3 centre = At(e, uc, y, off), centreF = At(e, uc, y, off - 0.015f);
            for (int k = 0; k < segs; k++)
            {
                float a0 = Mathf.PI * k / segs, a1 = Mathf.PI * (k + 1) / segs;
                c.D.TriFacing(fill, centre, At(e, uc + Mathf.Cos(a0) * r, y + Mathf.Sin(a0) * r, off), At(e, uc + Mathf.Cos(a1) * r, y + Mathf.Sin(a1) * r, off), e.N);
                float rf = r + fw;
                c.D.TriFacing(frame, centreF, At(e, uc + Mathf.Cos(a0) * rf, y + Mathf.Sin(a0) * rf, off - 0.015f),
                    At(e, uc + Mathf.Cos(a1) * rf, y + Mathf.Sin(a1) * rf, off - 0.015f), e.N);
            }
        }

        // Panel balconies: every second bay from the second floor, some glazed (seeded).
        private static void Balconies(Ctx c, Edge e, int f, List<float> cols)
        {
            float y = f * c.Fh;
            Quaternion rot = Quaternion.LookRotation(e.N);
            for (int k = 0; k < cols.Count; k++)
            {
                if (k % 2 != (e.Index % 2)) continue;
                if (HitsStrip(c, e, cols[k], 3f)) continue;
                float w = Mathf.Min(3f, Spacing(e, cols) * 0.9f);
                Vector3 baseP = At(e, cols[k], y, 0.6f);
                c.D.Box(c.Concrete, baseP + Vector3.down * 0.075f, new Vector3(w, 0.15f, 1.2f), rot, true);
                var hr = new System.Random(c.B.seed ^ (f * 131 + k * 17 + e.Index * 7));
                bool glazed = hr.NextDouble() < 0.4;
                int front = glazed ? c.Glass : hr.NextDouble() < 0.5 ? c.Trim : c.Wall;
                c.D.Box(front, At(e, cols[k], y + 0.5f, 1.17f), new Vector3(w, 1.0f, 0.06f), rot);
                if (glazed)
                {
                    c.D.Box(c.Concrete, At(e, cols[k] - w / 2f + 0.03f, y + 0.5f, 0.6f), new Vector3(0.06f, 1.0f, 1.2f), rot);
                    c.D.Box(c.Concrete, At(e, cols[k] + w / 2f - 0.03f, y + 0.5f, 0.6f), new Vector3(0.06f, 1.0f, 1.2f), rot);
                    WallQuad(c, c.Glass, e, cols[k] - w / 2f, cols[k] + w / 2f, y + 1.0f, y + c.Fh - 0.25f, 1.2f);
                    c.D.Box(c.Concrete, At(e, cols[k], y + c.Fh - 0.2f, 0.6f), new Vector3(w, 0.1f, 1.25f), rot, true);
                }
            }
        }

        // Glazed stair strip above each panel entrance, painted in the courtyard stripe colour (trim).
        private static void StairStrips(Ctx c, Edge e)
        {
            foreach (Door d in c.Doors)
            {
                if (d.Edge != e.Index) continue;
                WallQuad(c, c.Trim, e, d.U - 0.8f, d.U + 0.8f, c.Fh, c.H - 0.3f, 0.03f);
                for (int f = 1; f < c.Floors; f++)
                    WallQuad(c, GlassSlot(c), e, d.U - 0.45f, d.U + 0.45f, f * c.Fh + 1.4f, f * c.Fh + 2.3f, 0.045f);
            }
        }

        // ---------------------------------------------------------------- roofs
        private static void Roof(Ctx c)
        {
            string roof = c.B.roof;
            if (roof == "flat" || c.Rects.Count == 0) FlatRoof(c);
            else
                foreach (Rect r in c.Rects)
                {
                    if (roof == "hip") Hip(c, r);
                    else if (roof == "shed") Shed(c, r);
                    else Gable(c, r);
                }
        }

        private static void FlatRoof(Ctx c)
        {
            float p = c.S.ParapetH;
            c.D.PlanTris(c.Roof, c.B.tris, (x, y) => c.H, 0f, c.B.x, c.B.y);
            if (p > 0f)
                foreach (Edge e in c.Edges)
                {
                    if (e.Len < 0.2f) continue;
                    WallQuad(c, c.Wall, e, 0f, e.Len, c.H, c.H + p, 0f);
                    c.D.QuadFacing(c.Wall, At(e, 0f, c.H, -0.25f), At(e, 0f, c.H + p, -0.25f), At(e, e.Len, c.H + p, -0.25f), At(e, e.Len, c.H, -0.25f), -e.N);
                    Ledge(c, c.Trim, e, -0.05f, e.Len + 0.05f, c.H + p, -0.27f, 0.05f, true);
                    WallQuad(c, c.Trim, e, -0.05f, e.Len + 0.05f, c.H + p - 0.12f, c.H + p, 0.05f);
                }
            c.Top = c.H + Mathf.Max(0f, p);
            if (c.S.Modern)
            {
                // Modern villa: thin white roof slab overhanging every side (the cantilever read).
                foreach (Rect r in c.Rects)
                    c.D.Box(c.Trim, r.C + Vector3.up * (c.H + p + 0.12f), new Vector3(r.Hv * 2f + 1.6f, 0.24f, r.Hu * 2f + 1.6f), Quaternion.LookRotation(r.U), true);
            }
        }

        private static void Gable(Ctx c, Rect r)
        {
            float t = Mathf.Tan(c.S.RoofPitch * Mathf.Deg2Rad), e = c.S.Eaves, th = 0.14f;
            float rise = r.Hv * t, eaveY = c.H - e * t, ridgeY = c.H + rise;
            Vector3 up = Vector3.up;
            for (int side = -1; side <= 1; side += 2)
            {
                Vector3 vs = r.V * side;
                Vector3 e0 = r.C - r.U * (r.Hu + e) + vs * (r.Hv + e) + up * eaveY;
                Vector3 e1 = r.C + r.U * (r.Hu + e) + vs * (r.Hv + e) + up * eaveY;
                Vector3 r0 = r.C - r.U * (r.Hu + e) + up * ridgeY;
                Vector3 r1 = r.C + r.U * (r.Hu + e) + up * ridgeY;
                Vector3 facing = up + vs * t;
                c.D.QuadFacing(c.Roof, e0, r0, r1, e1, facing);
                Vector3 dn = up * -th;
                c.D.QuadFacing(c.Trim, e0 + dn, r0 + dn, r1 + dn, e1 + dn, -facing);
                c.D.QuadFacing(c.Trim, e0, e1, e1 + dn, e0 + dn, vs);
                c.D.QuadFacing(c.Trim, e0, r0, r0 + dn, e0 + dn, -r.U);
                c.D.QuadFacing(c.Trim, e1, r1, r1 + dn, e1 + dn, r.U);
            }
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 uo = r.U * (su * r.Hu);
                c.D.TriFacing(c.Wall, r.C + uo - r.V * r.Hv + up * c.H, r.C + uo + r.V * r.Hv + up * c.H, r.C + uo + up * ridgeY, r.U * su);
            }
            c.Top = Mathf.Max(c.Top, ridgeY);
            if (c.S.Chimney) ChimneyStack(c, r, ridgeY);
        }

        private static void Hip(Ctx c, Rect r)
        {
            float t = Mathf.Tan(c.S.RoofPitch * Mathf.Deg2Rad), e = c.S.Eaves, th = 0.14f;
            float rise = r.Hv * t, eaveY = c.H - e * t, ridgeY = c.H + rise, rh = Mathf.Max(0f, r.Hu - r.Hv);
            Vector3 up = Vector3.up, dn = up * -th;
            Vector3 E(int su, int sv) => r.C + r.U * (su * (r.Hu + e)) + r.V * (sv * (r.Hv + e)) + up * eaveY;
            Vector3 R(int su) => r.C + r.U * (su * rh) + up * ridgeY;
            for (int sv = -1; sv <= 1; sv += 2)
            {
                Vector3 facing = up + r.V * (sv * t);
                if (rh > 0.01f) c.D.QuadFacing(c.Roof, E(-1, sv), R(-1), R(1), E(1, sv), facing);
                else c.D.TriFacing(c.Roof, E(-1, sv), R(0), E(1, sv), facing);
                c.D.QuadFacing(c.Trim, E(-1, sv) + dn, R(-1) + dn, R(1) + dn, E(1, sv) + dn, -facing);
                c.D.QuadFacing(c.Trim, E(-1, sv), E(1, sv), E(1, sv) + dn, E(-1, sv) + dn, r.V * sv);
            }
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 facing = up + r.U * (su * t);
                c.D.TriFacing(c.Roof, E(su, -1), R(su), E(su, 1), facing);
                c.D.TriFacing(c.Trim, E(su, -1) + dn, R(su) + dn, E(su, 1) + dn, -facing);
                c.D.QuadFacing(c.Trim, E(su, -1), E(su, 1), E(su, 1) + dn, E(su, -1) + dn, r.U * su);
            }
            c.Top = Mathf.Max(c.Top, ridgeY);
            if (c.S.Chimney) ChimneyStack(c, r, ridgeY);
        }

        private static void Shed(Ctx c, Rect r)
        {
            float t = Mathf.Tan(Mathf.Min(c.S.RoofPitch, 18f) * Mathf.Deg2Rad), e = c.S.Eaves, th = 0.12f;
            Vector3 front = c.Edges[c.Front].N;
            float sh = Vector3.Dot(r.V, front) >= 0f ? 1f : -1f;
            float rise = 2f * r.Hv * t;
            Vector3 up = Vector3.up, dn = up * -th, vs = r.V * sh;
            Vector3 l0 = r.C - r.U * (r.Hu + e) - vs * (r.Hv + e) + up * (c.H - e * t);
            Vector3 l1 = r.C + r.U * (r.Hu + e) - vs * (r.Hv + e) + up * (c.H - e * t);
            Vector3 h0 = r.C - r.U * (r.Hu + e) + vs * (r.Hv + e) + up * (c.H + rise + e * t);
            Vector3 h1 = r.C + r.U * (r.Hu + e) + vs * (r.Hv + e) + up * (c.H + rise + e * t);
            Vector3 facing = up - vs * t;
            c.D.QuadFacing(c.Roof, l0, h0, h1, l1, facing);
            c.D.QuadFacing(c.Trim, l0 + dn, h0 + dn, h1 + dn, l1 + dn, -facing);
            c.D.QuadFacing(c.Trim, l0, l1, l1 + dn, l0 + dn, -vs);
            c.D.QuadFacing(c.Trim, h0, h1, h1 + dn, h0 + dn, vs);
            c.D.QuadFacing(c.Trim, l0, h0, h0 + dn, l0 + dn, -r.U);
            c.D.QuadFacing(c.Trim, l1, h1, h1 + dn, l1 + dn, r.U);
            Vector3 hiA = r.C - r.U * r.Hu + vs * r.Hv, hiB = r.C + r.U * r.Hu + vs * r.Hv;
            c.D.QuadFacing(c.Wall, hiA + up * c.H, hiA + up * (c.H + rise), hiB + up * (c.H + rise), hiB + up * c.H, vs);
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 uo = r.U * (su * r.Hu);
                c.D.TriFacing(c.Wall, r.C + uo - vs * r.Hv + up * c.H, r.C + uo + vs * r.Hv + up * c.H, r.C + uo + vs * r.Hv + up * (c.H + rise), r.U * su);
            }
            c.Top = Mathf.Max(c.Top, c.H + rise);
        }

        private static void ChimneyStack(Ctx c, Rect r, float ridgeY)
        {
            float side = c.Rnd.NextDouble() < 0.5 ? -1f : 1f;
            Vector3 p = r.C + r.U * (side * r.Hu * 0.35f) + r.V * (r.Hv * 0.25f);
            float y0 = c.H, y1 = ridgeY + 0.8f;
            c.D.Box(c.Brick, p + Vector3.up * ((y0 + y1) / 2f), new Vector3(0.6f, y1 - y0, 0.6f), Quaternion.LookRotation(r.U));
            c.D.Box(c.Concrete, p + Vector3.up * (y1 + 0.05f), new Vector3(0.75f, 0.1f, 0.75f), Quaternion.LookRotation(r.U));
        }

        // ---------------------------------------------------------------- doors, signs, extras
        private static void Doors(Ctx c)
        {
            BuildingStyle s = c.S;
            bool first = true;
            foreach (Door d in c.Doors)
            {
                Edge e = c.Edges[d.Edge];
                float lift = c.DoorLift;
                bool roller = s.RollerDoor && first && e.Len > 6f;
                float w = roller ? 4f : s.DoorW, h = roller ? Mathf.Min(4f, c.H - 0.6f) : s.DoorH;
                first = false;
                WallQuad(c, c.Trim, e, d.U - w / 2f - 0.12f, d.U + w / 2f + 0.12f, lift, lift + h + 0.12f, 0.02f);
                int leaf = roller ? c.D.Slot("mat/door/metal") : s.GlassFront || s.Modern || s.Name == "commercial" ? c.Glass : c.DoorS;
                WallQuad(c, leaf, e, d.U - w / 2f, d.U + w / 2f, lift, lift + h, 0.035f);
                if (roller)
                    for (float y = lift + 0.5f; y < lift + h; y += 0.5f)
                        WallQuad(c, c.Trim, e, d.U - w / 2f, d.U + w / 2f, y - 0.03f, y, 0.045f);
                if (s.ArchedDoor && !roller) Arch(c, leaf, c.Trim, e, d.U, w / 2f, lift + h, 0.035f, 0.12f);
                Quaternion rot = Quaternion.LookRotation(e.N);
                float top = lift + h + (s.ArchedDoor ? w / 2f : 0f);
                if (s.CanopyW > 0f && !roller)
                {
                    float cw = Mathf.Min(s.CanopyW, e.Len), cd = s.CanopyD;
                    int slot = s.Name == "oldtown" ? c.Roof : c.Concrete;
                    c.D.Box(slot, At(e, d.U, top + 0.3f, cd / 2f), new Vector3(cw, 0.15f, cd), rot, true);
                    if (s.Special == "casino")
                        c.D.Box(c.D.Slot("mat/neon/yellow"), At(e, d.U, top + 0.3f, cd + 0.03f), new Vector3(cw, 0.2f, 0.06f), rot);
                    if (s.Special == "hospital")
                        for (int k = -1; k <= 1; k += 2)
                            c.D.Cylinder(c.Metal, At(e, d.U + k * (cw / 2f - 0.3f), 0f, cd - 0.3f), 0.1f, top + 0.3f, 6, false);
                }
                for (int k = 0; k < s.Steps; k++)
                {
                    float depth = 0.3f * (s.Steps - k);
                    c.D.Box(c.Concrete, At(e, d.U, 0.15f * (k + 1) / 2f, depth / 2f), new Vector3(w + 0.8f, 0.15f * (k + 1), depth), rot);
                }
                if (s.Porch)
                {
                    c.D.Box(c.D.Slot("mat/wood"), At(e, d.U, 0.15f, 0.75f), new Vector3(2.2f, 0.3f, 1.5f), rot, false);
                    for (int k = -1; k <= 1; k += 2)
                        c.D.Box(c.D.Slot("mat/wood"), At(e, d.U + k * 1.0f, 1.35f, 1.4f), new Vector3(0.14f, 2.1f, 0.14f), rot);
                    c.D.Box(c.Roof, At(e, d.U, 2.5f, 0.9f), new Vector3(2.5f, 0.12f, 1.9f), rot, true);
                }
                if (s.Special == "police")
                    c.D.Box(c.D.Slot("mat/neon/blue"), At(e, d.U, top + 0.75f, 0.12f), new Vector3(0.45f, 0.3f, 0.25f), rot);
                if (s.Special == "bank") Columns4(c, e, d.U, Mathf.Min(c.H, c.Fh * 2f) - 0.4f);
            }
        }

        private static void Portico(Ctx c)
        {
            if (c.Doors.Count == 0) return;
            Door d = c.Doors[0];
            Columns4(c, c.Edges[d.Edge], d.U, Mathf.Min(c.H - 0.3f, 6.4f));
        }

        // Four-column portico with a slab on top (bank, classic mansion).
        private static void Columns4(Ctx c, Edge e, float u, float height)
        {
            int stone = c.D.Slot("mat/stone");
            for (int k = 0; k < 4; k++)
            {
                float du = (k - 1.5f) * 1.9f;
                if (u + du < 0.2f || u + du > e.Len - 0.2f) continue;
                c.D.Cylinder(stone, At(e, u + du, 0f, 2.2f), 0.28f, height, 8, false);
            }
            c.D.Box(c.Trim, At(e, u, height + 0.25f, 1.3f), new Vector3(Mathf.Min(6.6f, e.Len), 0.5f, 2.6f), Quaternion.LookRotation(e.N), true);
            if (c.S.Name == "villa")
            {
                int rail = c.Trim;
                for (int k = -6; k <= 6; k++)
                    c.D.Box(rail, At(e, u + k * 0.25f, height + 0.85f, 2.5f), new Vector3(0.08f, 0.7f, 0.08f), Quaternion.LookRotation(e.N));
                c.D.Box(rail, At(e, u, height + 1.25f, 2.5f), new Vector3(3.3f, 0.1f, 0.14f), Quaternion.LookRotation(e.N));
                c.D.Box(c.D.Slot("mat/gold"), At(e, u, height + 0.05f, 2.62f), new Vector3(Mathf.Min(6.6f, e.Len), 0.08f, 0.04f), Quaternion.LookRotation(e.N));
            }
        }

        private static int SignEdge(Ctx c)
        {
            int side = c.B.sign_side;
            if (side >= 0 && side < c.Edges.Length && c.Edges[side].Len >= 1.5f) return side;
            return c.Front;
        }

        private static void Sign(Ctx c)
        {
            string text = c.B.sign_text;
            if (string.IsNullOrEmpty(text) || c.B.sign_side < 0 && c.S.Special != "casino") return;
            BuildingStyle s = c.S;
            if (s.Special == "casino")
            {
                CasinoCrown(c, text);
                return;
            }
            Edge e = c.Edges[SignEdge(c)];
            float u = e.Len / 2f;
            foreach (Door d in c.Doors)
                if (d.Edge == e.Index)
                    u = d.U;
            float hgt = s.SignH;
            float width = Mathf.Min(e.Len - 0.6f, Mathf.Max(2.4f, text.Length * hgt * 0.62f + 0.8f));
            if (s.Special == "supermarket") width = e.Len * 0.85f;
            u = Mathf.Clamp(u, width / 2f + 0.3f, e.Len - width / 2f - 0.3f);
            float y = c.Floors == 1 ? c.H - hgt / 2f - 0.25f : c.Fh + 0.1f;
            if (c.Floors == 1 && s.ParapetH > 0f) y = c.H + Mathf.Min(s.ParapetH, hgt) - hgt / 2f;
            string boardHex = s.SignMat == "mat/sign" ? (s.Name == "commercial" ? c.B.trim : "#F2EDE0") : "";
            int board = s.SignMat == "mat/sign" ? c.D.Slot("mat/sign", boardHex) : c.D.Slot(s.SignMat);
            if (s.Name == "neon") board = c.D.Slot("mat/sign", "#1E2A44");
            Quaternion rot = Quaternion.LookRotation(e.N);
            c.D.Box(board, At(e, u, y, 0.09f), new Vector3(width, hgt, 0.12f), rot);
            if (s.NeonStrips)
            {
                int neon = c.D.Slot("mat/neon/strip", c.B.trim);
                c.D.Box(neon, At(e, u, y + hgt / 2f + 0.04f, 0.1f), new Vector3(width + 0.1f, 0.08f, 0.14f), rot);
                c.D.Box(neon, At(e, u, y - hgt / 2f - 0.04f, 0.1f), new Vector3(width + 0.1f, 0.08f, 0.14f), rot);
            }
            Color bg = s.Name == "neon" ? LookConvert.Color("#1E2A44") : s.SignMat == "mat/red" ? LookConvert.Color("#E53935") : LookConvert.Color(string.IsNullOrEmpty(boardHex) ? "#F2EDE0" : boardHex);
            SetSign(c, text, At(e, u, y, 0.16f), Quaternion.LookRotation(-e.N), width, hgt, bg);
        }

        private static void SetSign(Ctx c, string text, Vector3 pos, Quaternion rot, float width, float height, Color background)
        {
            BuildingResult r = c.R;
            r.HasSign = true;
            r.Sign = new Pose(pos, rot);
            r.SignWidth = width;
            r.SignHeight = height;
            r.SignText = text;
            float lum = background.r * 0.3f + background.g * 0.59f + background.b * 0.11f;
            r.SignTextColor = c.S.Name == "neon" ? LookConvert.Color(c.B.trim) : lum > 0.55f ? LookConvert.Color("#2E2E2E") : LookConvert.Color("#F7F3EA");
        }

        private static void CasinoCrown(Ctx c, string text)
        {
            Edge e = c.Edges[SignEdge(c)];
            float y = c.H + Mathf.Max(0f, c.S.ParapetH) + 1.4f, w = Mathf.Min(e.Len * 0.7f, 16f);
            Quaternion rot = Quaternion.LookRotation(e.N);
            int board = c.D.Slot("mat/sign", "#3C2F4B");
            c.D.Box(board, At(e, e.Len / 2f, y, -0.6f), new Vector3(w, 2.0f, 0.3f), rot);
            int neon = c.D.Slot("mat/neon/yellow");
            c.D.Box(neon, At(e, e.Len / 2f, y + 1.1f, -0.6f), new Vector3(w + 0.3f, 0.2f, 0.36f), rot);
            c.D.Box(neon, At(e, e.Len / 2f, y - 1.1f, -0.6f), new Vector3(w + 0.3f, 0.2f, 0.36f), rot);
            for (int k = 0; k < 5; k++)
            {
                float u = e.Len / 2f + (k - 2) * w / 4.2f;
                c.D.Box(neon, At(e, u, y + 1.6f, -0.6f), new Vector3(0.5f, 0.8f, 0.3f), rot * Quaternion.Euler(0f, 0f, 45f));
            }
            for (int k = -1; k <= 1; k += 2)
                c.D.Box(c.Metal, At(e, e.Len / 2f + k * w * 0.35f, (c.H + y) / 2f, -0.8f), new Vector3(0.2f, y - c.H, 0.2f), rot);
            SetSign(c, text, At(e, e.Len / 2f, y, -0.43f), Quaternion.LookRotation(-e.N), w, 2.0f, LookConvert.Color("#3C2F4B"));
            c.R.SignTextColor = LookConvert.Color("#FFD166");
            c.Top = Mathf.Max(c.Top, y + 2f);
        }

        private static void Extras(Ctx c)
        {
            BuildingStyle s = c.S;
            float roofY = c.H + Mathf.Max(0f, s.ParapetH);
            bool flat = c.B.roof == "flat" || c.Rects.Count == 0;
            if (s.MachineRoom && flat)
            {
                bool tower = c.B.kind == "tower";
                var seen = new List<Vector3>();
                foreach (Door d in c.Doors)
                {
                    Edge e = c.Edges[d.Edge];
                    Vector3 p = At(e, d.U, c.H, -Mathf.Min(5f, 3.5f));
                    if (seen.Exists(q => Vector3.Distance(q, p) < 6f)) continue;
                    seen.Add(p);
                    float mh = tower ? 6f : 2.5f;
                    c.D.Box(c.Wall, p + Vector3.up * (mh / 2f), new Vector3(3.2f, mh, 3.6f), Quaternion.LookRotation(e.N));
                    c.D.Box(c.Roof, p + Vector3.up * (mh + 0.05f), new Vector3(3.4f, 0.1f, 3.8f), Quaternion.LookRotation(e.N));
                    if (tower) c.D.Cylinder(c.Metal, p + Vector3.up * mh, 0.08f, 5f, 5, false);
                    c.Top = Mathf.Max(c.Top, c.H + mh);
                }
            }
            if (s.Hvac && flat && c.Rects.Count > 0)
            {
                Rect r = c.Rects[0];
                int count = 2 + c.Rnd.Next(2);
                for (int k = 0; k < count; k++)
                {
                    Vector3 p = r.C + r.U * ((k - (count - 1) / 2f) * Mathf.Min(4f, r.Hu * 0.5f)) + r.V * (r.Hv * 0.2f);
                    c.D.Box(c.Metal, p + Vector3.up * (c.H + 0.6f), new Vector3(1.6f, 1.2f, 1.1f), Quaternion.LookRotation(r.U));
                }
            }
            if (s.Name == "villa" && !s.Modern && s.Special != "bank") Portico(c);
            switch (s.Special)
            {
                case "church": Church(c); break;
                case "gas_station": GasCanopy(c); break;
                case "bowling": BowlingPin(c, roofY); break;
                case "hospital": RedCross(c); break;
                case "police": Flag(c, roofY); break;
                case "kiosk": KioskAwning(c); break;
            }
        }

        private static void RedCross(Ctx c)
        {
            Edge e = c.Edges[c.Front];
            float u = c.Doors.Count > 0 ? c.Doors[0].U : e.Len / 2f;
            float y = c.H - 1.8f;
            int red = c.D.Slot("mat/red");
            WallQuad(c, c.D.Slot("mat/white"), e, u - 1.6f, u + 1.6f, y - 1.6f, y + 1.6f, 0.04f);
            WallQuad(c, red, e, u - 0.4f, u + 0.4f, y - 1.3f, y + 1.3f, 0.06f);
            WallQuad(c, red, e, u - 1.3f, u + 1.3f, y - 0.4f, y + 0.4f, 0.06f);
        }

        private static void Flag(Ctx c, float roofY)
        {
            if (c.Rects.Count == 0) return;
            Rect r = c.Rects[0];
            Vector3 p = r.C + r.U * (r.Hu * 0.6f) + r.V * (r.Hv * 0.5f);
            float top = c.Top + 5f;
            c.D.Cylinder(c.Metal, new Vector3(p.x, c.H, p.z), 0.06f, top - c.H, 6, true);
            Vector3 a = new Vector3(p.x, top - 0.2f, p.z), dir = r.U;
            c.D.QuadBoth(c.D.Slot("mat/canvas/blue"), a, a + dir * 1.6f, a + dir * 1.6f + Vector3.down * 1.0f, a + Vector3.down * 1.0f);
            c.Top = top;
        }

        private static void KioskAwning(Ctx c)
        {
            Edge e = c.Edges[c.Front];
            float u = e.Len / 2f, y = Mathf.Min(c.H - 0.4f, 2.2f);
            WallQuad(c, c.Glass, e, u - 0.6f, u + 0.6f, y - 1.0f, y - 0.2f, 0.04f);
            int canvas = c.D.Slot(c.Rnd.NextDouble() < 0.5 ? "mat/canvas/red" : "mat/canvas/blue");
            Vector3 a0 = At(e, u - 1.0f, y + 0.1f, 0f), a1 = At(e, u + 1.0f, y + 0.1f, 0f);
            Vector3 b0 = At(e, u - 1.0f, y - 0.3f, 0.7f), b1 = At(e, u + 1.0f, y - 0.3f, 0.7f);
            c.D.QuadBoth(canvas, a0, b0, b1, a1);
        }

        private static void GasCanopy(Ctx c)
        {
            Edge e = c.Edges[c.Front];
            float u = c.Doors.Count > 0 ? c.Doors[0].U : e.Len / 2f;
            Quaternion rot = Quaternion.LookRotation(e.N);
            Vector3 centre = At(e, u, 0f, 1.5f + 5f);
            int white = c.D.Slot("mat/white"), orange = c.D.Slot("mat/orange");
            c.D.Box(white, centre + Vector3.up * 5.475f, new Vector3(16f, 0.25f, 10f), rot, true);
            c.D.Box(orange, centre + Vector3.up * 5.175f, new Vector3(16.1f, 0.35f, 10.1f), rot, true);
            Vector3 across = rot * Vector3.right, outward = rot * Vector3.forward;
            for (int i = -1; i <= 1; i += 2)
                for (int j = -1; j <= 1; j += 2)
                {
                    Vector3 p = centre + across * (i * 5f) + outward * (j * 3f);
                    c.D.Box(white, p + Vector3.up * 2.5f, new Vector3(0.5f, 5f, 0.5f), rot);
                    c.R.Colliders.Add(new ExtraCollider { Centre = p + Vector3.up * 2.5f, Size = new Vector3(0.5f, 5f, 0.5f), Rotation = rot, Optional = true });
                }
            for (int i = -1; i <= 1; i += 2)
            {
                Vector3 p = centre + across * (i * 2.6f);
                c.D.Box(orange, p + Vector3.up * 0.8f, new Vector3(0.7f, 1.6f, 1.1f), rot);
                c.D.Box(white, p + Vector3.up * 1.65f, new Vector3(0.75f, 0.1f, 1.15f), rot);
                c.R.Colliders.Add(new ExtraCollider { Centre = p + Vector3.up * 0.8f, Size = new Vector3(0.7f, 1.6f, 1.1f), Rotation = rot, Optional = true });
            }
            c.Top = Mathf.Max(c.Top, 5.6f);
        }

        private static void BowlingPin(Ctx c, float roofY)
        {
            Vector3 p = c.Rects.Count > 0 ? c.Rects[0].C : Vector3.zero;
            p.y = roofY;
            float[] r = { 0.55f, 0.75f, 0.85f, 0.62f, 0.4f, 0.44f, 0.5f, 0.44f, 0.26f, 0f };
            float[] h = { 0f, 0.8f, 1.8f, 2.9f, 3.6f, 4.1f, 4.7f, 5.3f, 5.8f, 6.0f };
            c.D.Lathe(c.D.Slot("mat/white"), p, r, h, 12);
            int red = c.D.Slot("mat/red");
            c.D.Lathe(red, p, new[] { 0.42f, 0.42f }, new[] { 3.45f, 3.6f }, 12);
            c.D.Lathe(red, p, new[] { 0.41f, 0.41f }, new[] { 3.75f, 3.9f }, 12);
            c.Top = Mathf.Max(c.Top, roofY + 6f);
        }

        // Church: bell tower at the entrance with a tent roof, onion dome (4 m) and four small domes over the nave.
        private static void Church(Ctx c)
        {
            if (c.Rects.Count == 0) return;
            Rect nave = c.Rects[0];
            Edge e = c.Edges[c.Front];
            Quaternion rot = Quaternion.LookRotation(e.N);
            float u = c.Doors.Count > 0 ? c.Doors[0].U : e.Len / 2f;
            Vector3 towerC = At(e, u, 0f, -2.9f);
            float towerTop = 18f;
            c.D.Box(c.Wall, towerC + Vector3.up * ((towerTop + c.Low) / 2f), new Vector3(5.4f, towerTop - c.Low, 5.4f), rot);
            for (int k = 0; k < 4; k++)
            {
                Quaternion face = rot * Quaternion.Euler(0f, 90f * k, 0f);
                Vector3 n = face * Vector3.forward, side = face * Vector3.right;
                Vector3 o = towerC + n * 2.72f + Vector3.up * 14.2f;
                c.D.QuadFacing(c.D.Slot("mat/iron"), o - side * 0.6f, o - side * 0.6f + Vector3.up * 2.2f, o + side * 0.6f + Vector3.up * 2.2f, o + side * 0.6f, n);
            }
            int dome = c.D.Slot("mat/dome", "#2F6F8F"), gold = c.D.Slot("mat/gold");
            c.D.Lathe(c.Roof, towerC + Vector3.up * towerTop, new[] { 3.9f, 0f }, new[] { 0f, 2.2f }, 4, Mathf.Atan2(e.N.z, e.N.x) + Mathf.PI / 4f);
            c.D.Cylinder(c.Wall, towerC + Vector3.up * (towerTop + 1.2f), 0.9f, 1.4f, 10, false);
            Onion(c, dome, gold, towerC + Vector3.up * (towerTop + 2.6f), 1.1f);
            float t = Mathf.Tan(c.S.RoofPitch * Mathf.Deg2Rad), ridge = c.H + nave.Hv * t;
            Vector3 mid = nave.C;
            c.D.Cylinder(c.Wall, mid + Vector3.up * (c.H + nave.Hv * t * 0.5f), 2.0f, nave.Hv * t * 0.5f + 2.2f, 12, false);
            Onion(c, dome, gold, mid + Vector3.up * (ridge + 2.2f), 2.0f);
            for (int i = -1; i <= 1; i += 2)
                for (int j = -1; j <= 1; j += 2)
                {
                    Vector3 p = mid + nave.U * (i * Mathf.Min(4.5f, nave.Hu * 0.45f)) + nave.V * (j * nave.Hv * 0.45f);
                    c.D.Cylinder(c.Wall, p + Vector3.up * (c.H + nave.Hv * t * 0.4f), 0.75f, ridge - c.H - nave.Hv * t * 0.4f + 1.2f, 8, false);
                    Onion(c, dome, gold, p + Vector3.up * (ridge + 1.2f), 0.9f);
                }
            c.Top = Mathf.Max(c.Top, towerTop + 7f);
            c.R.Colliders.Add(new ExtraCollider { Centre = towerC + Vector3.up * (towerTop / 2f), Size = new Vector3(5.4f, towerTop, 5.4f), Rotation = rot });
        }

        private static void Onion(Ctx c, int dome, int gold, Vector3 baseP, float radius)
        {
            float hgt = radius * 2.3f;
            float[] r = { 0.8f, 1.0f, 0.86f, 0.45f, 0.12f, 0f };
            float[] h = { 0f, 0.25f, 0.5f, 0.75f, 0.92f, 1f };
            for (int i = 0; i < r.Length; i++)
            {
                r[i] *= radius;
                h[i] *= hgt;
            }
            c.D.Lathe(dome, baseP, r, h, 12);
            Vector3 top = baseP + Vector3.up * hgt;
            float s = Mathf.Max(0.5f, radius * 0.8f);
            c.D.Box(gold, top + Vector3.up * (s * 0.6f), new Vector3(0.08f * s * 1.5f, s * 1.2f, 0.08f * s * 1.5f), Quaternion.identity);
            c.D.Box(gold, top + Vector3.up * (s * 0.8f), new Vector3(s * 0.7f, 0.08f * s * 1.5f, 0.08f * s * 1.5f), Quaternion.identity);
        }

        // ---------------------------------------------------------------- special shapes
        private static void WaterTower(Ctx c)
        {
            Vector3 o = Vector3.zero;
            float H = c.H > 6f ? c.H : 18f;
            float tankBase = H - 5.7f, tankTop = H - 1.7f;
            c.D.Box(c.Concrete, o + Vector3.up * ((c.Low + 0.3f) / 2f), new Vector3(5.6f, 0.3f - c.Low, 5.6f), Quaternion.identity);
            Edge e = c.Edges[c.Front];
            Vector3 n = e.N;
            // Brick shaft: straight 2.4 m skirt up past the door, then the taper to 2.1 m; one flat facet faces the door.
            float straight = Mathf.Max(c.Low + 0.1f, Mathf.Min(2.5f, tankBase - 1.0f)), taper = Mathf.Max(straight + 0.1f, Mathf.Min(straight + 1.2f, tankBase - 0.3f));
            float facing = Mathf.Atan2(n.z, n.x) - Mathf.PI / 10f;
            c.D.Lathe(c.Brick, o, new[] { 2.4f, 2.4f, 2.1f, 2.1f }, new[] { c.Low, straight, taper, Mathf.Max(taper + 0.1f, tankBase - 0.2f) }, 10, facing);
            Vector3 dp = o + n * (2.4f * Mathf.Cos(Mathf.PI / 10f) + 0.03f);
            c.D.QuadFacing(c.DoorS, dp + Vector3.Cross(Vector3.up, n) * 0.5f, dp + Vector3.Cross(Vector3.up, n) * 0.5f + Vector3.up * 2.1f,
                dp - Vector3.Cross(Vector3.up, n) * 0.5f + Vector3.up * 2.1f, dp - Vector3.Cross(Vector3.up, n) * 0.5f, n);
            c.D.Cylinder(c.Metal, o + Vector3.up * (tankBase - 0.2f), 3.6f, 0.2f, 12, true);
            c.D.Lathe(c.Wall, o, new[] { 0f, 3.0f, 3.0f }, new[] { tankBase - 0.6f, tankBase, tankTop }, 12);
            c.D.Lathe(c.Roof, o, new[] { 3.3f, 0f }, new[] { tankTop, H }, 12);
            for (int k = 0; k < 12; k++)
            {
                float a = k * Mathf.PI * 2f / 12f;
                Vector3 p = o + new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * 3.5f;
                c.D.Box(c.Metal, p + Vector3.up * (tankBase + 0.5f), new Vector3(0.05f, 1.0f, 0.05f), Quaternion.identity);
            }
            c.Top = H;
            c.R.Collision = PrismMesh(c, c.Low, H);
        }

        // Industrial chimney: tapered brick stack with white and red bands near the top (district 7 landmark).
        private static void Chimney(Ctx c)
        {
            float H = c.H > 10f ? c.H : 60f;
            float r0 = 0.0f;
            foreach (Edge e in c.Edges) r0 = Mathf.Max(r0, e.Len);
            r0 = Mathf.Clamp(r0 * 0.38f, 2.2f, 4f);
            float r1 = r0 * 0.5f;
            c.D.Box(c.Concrete, Vector3.up * ((c.Low + 1.2f) / 2f), new Vector3(r0 * 2.5f, 1.2f - c.Low, r0 * 2.5f), Quaternion.identity);
            c.D.Lathe(c.Brick, Vector3.zero, new[] { r0, r1 }, new[] { 1.2f, H }, 14);
            int white = c.D.Slot("mat/white"), red = c.D.Slot("mat/red");
            float[] bands = { H - 14f, H - 9f, H - 4f };
            for (int k = 0; k < bands.Length; k++)
            {
                float y0 = bands[k], y1 = y0 + 2.5f;
                float ra = Mathf.Lerp(r0, r1, (y0 - 1.2f) / (H - 1.2f)) + 0.04f, rb = Mathf.Lerp(r0, r1, (y1 - 1.2f) / (H - 1.2f)) + 0.04f;
                c.D.Lathe(k % 2 == 0 ? red : white, Vector3.zero, new[] { ra, rb }, new[] { y0, y1 }, 14);
            }
            c.D.Lathe(c.Concrete, Vector3.zero, new[] { r1 + 0.25f, r1 + 0.25f, r1 - 0.2f }, new[] { H - 0.6f, H, H }, 14);
            c.Top = H;
            c.R.Collision = PrismMesh(c, c.Low, Mathf.Min(H, 12f));
        }

        // Open bus shelter: back panel, side panels, roof and bench (the prefab replaces it when the registry has one).
        private static void BusStop(Ctx c)
        {
            if (c.Rects.Count == 0)
            {
                Generic(c);
                return;
            }
            Rect r = c.Rects[0];
            Vector3 front = c.Edges[c.Front].N;
            Vector3 back = Vector3.Dot(r.V, front) > 0f ? -r.V : r.V;
            Quaternion rot = Quaternion.LookRotation(-back);
            float len = r.Hu * 2f, depth = r.Hv * 2f, h = 2.5f;
            c.D.Box(c.Glass, r.C + back * (r.Hv - 0.05f) + Vector3.up * (h / 2f + 0.1f), new Vector3(len, h - 0.2f, 0.06f), rot);
            for (int k = -1; k <= 1; k += 2)
                c.D.Box(c.Glass, r.C + r.U * (k * (r.Hu - 0.05f)) + Vector3.up * (h / 2f + 0.1f), new Vector3(0.06f, h - 0.2f, depth * 0.6f), rot);
            c.D.Box(c.Roof, r.C + Vector3.up * (h + 0.08f), new Vector3(len + 0.4f, 0.16f, depth + 0.4f), rot, true);
            for (int k = -1; k <= 1; k += 2)
                c.D.Box(c.Metal, r.C + r.U * (k * (r.Hu - 0.1f)) + back * (r.Hv - 0.1f) + Vector3.up * (h / 2f), new Vector3(0.1f, h, 0.1f), rot);
            c.D.Box(c.D.Slot("mat/wood"), r.C + back * (r.Hv - 0.45f) + Vector3.up * 0.45f, new Vector3(len * 0.7f, 0.08f, 0.4f), rot, true);
            c.Top = h;
            c.R.Colliders.Add(new ExtraCollider { Centre = r.C + back * (r.Hv - 0.05f) + Vector3.up * (h / 2f), Size = new Vector3(len, h, 0.12f), Rotation = rot });
        }

        private static void AdPole(Ctx c)
        {
            Edge e = c.Edges[c.Front];
            Quaternion rot = Quaternion.LookRotation(e.N);
            float H = Mathf.Max(3f, c.H);
            c.D.Cylinder(c.Metal, new Vector3(0f, c.Low, 0f), 0.2f, H - c.Low + 0.2f, 8, false);
            Vector3 boardC = new Vector3(0f, H + 0.9f, 0f);
            c.D.Box(c.D.Slot("mat/sign", c.B.trim), boardC, new Vector3(3.6f, 1.8f, 0.2f), rot, true);
            string text = string.IsNullOrEmpty(c.B.sign_text) ? c.B.label : c.B.sign_text;
            if (!string.IsNullOrEmpty(text)) SetSign(c, text, boardC + e.N * 0.12f, Quaternion.LookRotation(-e.N), 3.4f, 1.6f, LookConvert.Color(c.B.trim));
            c.Top = H + 1.8f;
            c.R.Colliders.Add(new ExtraCollider { Centre = new Vector3(0f, H / 2f, 0f), Size = new Vector3(0.4f, H, 0.4f), Rotation = Quaternion.identity });
        }

        // Start wagon: an old goods wagon off its rails, rounded roof, sliding door, rust.
        private static void Wagon(Ctx c)
        {
            if (c.Rects.Count == 0)
            {
                Generic(c);
                return;
            }
            Rect r = c.Rects[0];
            Quaternion rot = Quaternion.LookRotation(r.U);
            float body0 = 0.9f, body1 = Mathf.Max(3.0f, c.H) - 0.3f;
            int rust = c.D.Slot("mat/rust");
            c.D.Box(c.Wall, r.C + Vector3.up * ((body0 + body1) / 2f), new Vector3(r.Hv * 2f, body1 - body0, r.Hu * 2f), rot, true);
            for (int k = -1; k <= 1; k += 2)
            {
                c.D.Box(rust, r.C + r.U * (k * r.Hu * 0.65f) + Vector3.up * ((c.Low + body0) / 2f), new Vector3(r.Hv * 1.4f, body0 - c.Low, 2.4f), rot, false);
                Vector3 side = r.V * (k * (r.Hv + 0.01f));
                c.D.QuadFacing(c.DoorS, r.C + side - r.U * 1.2f + Vector3.up * (body0 + 0.1f), r.C + side - r.U * 1.2f + Vector3.up * (body1 - 0.2f),
                    r.C + side + r.U * 1.2f + Vector3.up * (body1 - 0.2f), r.C + side + r.U * 1.2f + Vector3.up * (body0 + 0.1f), r.V * k);
            }
            const int segs = 5;
            for (int s = 0; s < segs; s++)
            {
                float a0 = Mathf.PI * s / segs, a1 = Mathf.PI * (s + 1) / segs;
                Vector3 p0 = r.V * (Mathf.Cos(a0) * (r.Hv + 0.1f)) + Vector3.up * (body1 + Mathf.Sin(a0) * 0.6f);
                Vector3 p1 = r.V * (Mathf.Cos(a1) * (r.Hv + 0.1f)) + Vector3.up * (body1 + Mathf.Sin(a1) * 0.6f);
                Vector3 mid = (p0 + p1) / 2f;
                mid.y -= body1;
                c.D.QuadFacing(c.Roof, r.C + p0 - r.U * (r.Hu + 0.1f), r.C + p0 + r.U * (r.Hu + 0.1f), r.C + p1 + r.U * (r.Hu + 0.1f), r.C + p1 - r.U * (r.Hu + 0.1f), mid + Vector3.up * 0.01f);
            }
            for (int k = -1; k <= 1; k += 2)
                c.D.Box(c.Wall, r.C + r.U * (k * r.Hu) + Vector3.up * (body1 + 0.25f), new Vector3(r.Hv * 2f, 0.5f, 0.05f), rot);
            c.Top = body1 + 0.6f;
        }

        private static Mesh PrismMesh(Ctx c, float y0, float y1)
        {
            var col = new MeshDraft();
            col.Prism(col.Slot("collision"), c.Fp, y0, y1, true, false);
            return col.ToMesh($"{c.B.id}_collision");
        }
    }
}
