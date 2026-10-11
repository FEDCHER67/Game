using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Everything the style v3 builder knows about one building while it is generated (local frame: origin at the
    // footprint centre b.x, b.y at pad height; plan-CCW footprint, so every edge's outward normal is on its right).
    // Output goes to five sinks: Shell (walls, plinth band, roof, parapet; every LOD, casts shadows), Big (cornices,
    // balconies, canopies, awnings, roof kit: LOD0, casts shadows), Small (windows, pipes, bars, AC units, signs: LOD0,
    // no shadows), Lod1 (flat window and band quads: 60-220 m) and Lod2 (glass quads only, beyond).
    public sealed class V3Building
    {
        public struct Edge
        {
            public int Index;
            public Vector3 A, B, Dir, N;
            public float Len;
            public bool ConvexStart, ConvexEnd, SquareStart, SquareEnd;
        }

        public struct Door
        {
            public int Edge;
            public float U;
        }

        public struct Rect
        {
            public Vector3 C, U, V;
            public float Hu, Hv;
        }

        public LookBuilding B;
        public string District, Arch;
        public Vector2[] Fp;
        public Edge[] Edges;
        public readonly List<Door> Doors = new();
        public readonly List<Rect> Rects = new();
        public int Front, Floors;
        public float Fh, H, Low, Pad, Top;
        // v17 game scale (LookBuilding.ground_h > 0): a taller ground storey G, parapet <= 0.6 m, 1.1 x 2.3 m doors.
        public float G;
        public bool GameScale;
        public string Roof;
        public System.Random Rnd;

        public string WallCat = "3b_plaster_stucco", RoofCat = "4d_flat_bitumen_roof";
        public string WallSwatch = "cream", RoofSwatch = "grey";
        public Color Wall, RoofColour, Trim, Frame, Plinth, DoorColour, Accent, Glass, GlassLight;

        public readonly V3Mesh Shell = new(), Big = new(), Small = new(), Lod1 = new(), Lod2 = new();
        public readonly List<(Vector3 centre, Vector3 size, Quaternion rot)> Boxes = new();
        public int Modules;

        public V3Building(LookBuilding b, float pad, float lowestY)
        {
            B = b;
            District = string.IsNullOrEmpty(b.district) ? "common" : b.district;
            Pad = pad;
            Rnd = new System.Random(b.seed != 0 ? b.seed : LookGeom.StableHash(b.id));
            Floors = Mathf.Max(1, b.floors);
            Fh = b.floor_h > 0.5f ? b.floor_h : 3.2f;
            GameScale = b.ground_h > 0.5f;
            G = GameScale ? b.ground_h : Fh;
            H = GameScale ? G + (Floors - 1) * Fh : Floors * Fh;
            Top = H;
            Low = Mathf.Min(-0.3f, lowestY - pad - 0.3f);
            Roof = string.IsNullOrEmpty(b.roof) ? "flat" : b.roof;
            Fp = LookConvert.Poly(b.fp, b.x, b.y);
            if (LookGeom.SignedArea(b.fp) < 0f) System.Array.Reverse(Fp);
            int n = Fp.Length;
            var edges = new Edge[n];
            for (int i = 0; i < n; i++)
            {
                Vector2 a = Fp[i], q = Fp[(i + 1) % n];
                var A = new Vector3(a.x, 0f, a.y);
                var B2 = new Vector3(q.x, 0f, q.y);
                float len = Vector3.Distance(A, B2);
                Vector3 dir = len > 1e-4f ? (B2 - A) / len : Vector3.right;
                edges[i] = new Edge { Index = i, A = A, B = B2, Dir = dir, N = new Vector3(dir.z, 0f, -dir.x), Len = len };
            }
            for (int i = 0; i < n; i++)
            {
                Edge prev = edges[(i + n - 1) % n];
                Edge cur = edges[i];
                float cross = prev.Dir.x * cur.Dir.z - prev.Dir.z * cur.Dir.x;
                // Plan CCW in (x, z): a left turn seen from above is cross > 0 in (x, y_plan); Unity z = plan y.
                bool convex = cross > 1e-3f;
                bool square = Mathf.Abs(Vector3.Dot(prev.Dir, cur.Dir)) < 0.15f;
                edges[i].ConvexStart = convex;
                edges[i].SquareStart = square;
                edges[(i + n - 1) % n].ConvexEnd = convex;
                edges[(i + n - 1) % n].SquareEnd = square;
            }
            Edges = edges;
            for (int k = 0; k + 4 < b.rects.Length; k += 5)
            {
                Quaternion q = LookConvert.Yaw(b.rects[k + 4]);
                Vector3 ax = q * Vector3.right, az = q * Vector3.forward;
                float sx = b.rects[k + 2], sz = b.rects[k + 3];
                bool zLong = sz >= sx;
                Rects.Add(new Rect
                {
                    C = new Vector3(b.rects[k] - b.x, 0f, b.rects[k + 1] - b.y),
                    U = zLong ? az : ax,
                    V = zLong ? ax : az,
                    Hu = (zLong ? sz : sx) / 2f,
                    Hv = (zLong ? sx : sz) / 2f,
                });
            }
            FindDoors();
        }

        private void FindDoors()
        {
            LookBuilding b = B;
            for (int k = 0; k + 2 < b.ent.Length; k += 3)
            {
                var p = new Vector3(b.ent[k] - b.x, 0f, b.ent[k + 1] - b.y);
                int best = 0;
                float bestD = float.MaxValue, bestU = 0f;
                foreach (Edge e in Edges)
                {
                    if (e.Len < 1.8f) continue;
                    float u = Mathf.Clamp(Vector3.Dot(p - e.A, e.Dir), 0f, e.Len);
                    float d = Vector3.Distance(e.A + e.Dir * u, p);
                    if (d < bestD)
                    {
                        bestD = d;
                        best = e.Index;
                        bestU = u;
                    }
                }
                float margin = Mathf.Min(1.3f, Edges[best].Len / 2f);
                Doors.Add(new Door { Edge = best, U = Mathf.Clamp(bestU, margin, Edges[best].Len - margin) });
            }
            if (Doors.Count > 0) Front = Doors[0].Edge;
            else
            {
                float bestDot = float.MinValue;
                Vector3 want = LookConvert.Yaw(b.front_deg) * Vector3.forward;
                foreach (Edge e in Edges)
                {
                    float d = Vector3.Dot(e.N, want) + e.Len * 0.001f;
                    if (d > bestDot)
                    {
                        bestDot = d;
                        Front = e.Index;
                    }
                }
                Doors.Add(new Door { Edge = Front, U = Edges[Front].Len / 2f });
            }
        }

        public float Rand() => (float)Rnd.NextDouble();

        // Height of the floor of storey f (0 = ground). Older plans: f * Fh exactly.
        public float FloorY(int f) => GameScale ? (f <= 0 ? 0f : G + (f - 1) * Fh) : f * Fh;

        public static Vector3 At(Edge e, float u, float y, float off) => e.A + e.Dir * u + e.N * off + Vector3.up * y;

        // Module frame on a wall: module X -> along the edge, module -Z -> outward, Y up (G12 contract).
        public static Matrix4x4 OnWall(Edge e, float u, float y, float off, Vector3 scale) =>
            Matrix4x4.TRS(At(e, u, y, off), Quaternion.LookRotation(-e.N, Vector3.up), scale);

        public bool NearDoor(Edge e, float u, float halfWidth)
        {
            foreach (Door d in Doors)
                if (d.Edge == e.Index && Mathf.Abs(u - d.U) < halfWidth + 0.95f)
                    return true;
            return false;
        }

        // ---------------------------------------------------------------- module placement

        // Appends a kit module (frame contract above) with matrix m into sink, recolouring slots through `recolour`
        // (null keeps the kit palette) and filing each slot under its surface category.
        public void Place(V3Module mod, V3Mesh sink, Matrix4x4 m, System.Func<string, Color, Color> recolour = null)
        {
            if (mod == null) return;
            Modules++;
            Matrix4x4 nm = m.inverse.transpose;
            bool flip = m.determinant < 0f;
            foreach (var part in mod.Parts)
            {
                string slotCat = V3Kit.SlotCategory(part.slot, WallCat, RoofCat);
                int[] t = part.tris;
                for (int k = 0; k + 2 < t.Length; k += 3)
                {
                    int i0 = t[k], i1 = flip ? t[k + 2] : t[k + 1], i2 = flip ? t[k + 1] : t[k + 2];
                    Color c0 = mod.C[i0], c1 = mod.C[i1], c2 = mod.C[i2];
                    if (recolour != null)
                    {
                        c0 = recolour(part.slot, c0);
                        c1 = recolour(part.slot, c1);
                        c2 = recolour(part.slot, c2);
                    }
                    // A colour far from the texture's own (chalk mullions on the wood set, ink rails on grey metal) would
                    // need a huge tint: such faces go to the flat palette material instead.
                    string cat = Fits(slotCat, c0) ? slotCat : "flat";
                    sink.TriSmooth(cat, m.MultiplyPoint3x4(mod.V[i0]), m.MultiplyPoint3x4(mod.V[i1]), m.MultiplyPoint3x4(mod.V[i2]),
                        nm.MultiplyVector(mod.N[i0]).normalized, nm.MultiplyVector(mod.N[i1]).normalized, nm.MultiplyVector(mod.N[i2]).normalized, c0, c1, c2);
                }
            }
        }

        private static readonly Dictionary<string, float> refLum = new();

        public static void ResetCaches() => refLum.Clear();

        private static float Lum(Color c)
        {
            Color l = c.linear;
            return 0.2126f * l.r + 0.7152f * l.g + 0.0722f * l.b;
        }

        public static bool Fits(string cat, Color target)
        {
            if (cat == "glass" || cat == "flat" || cat == "paint") return true;
            if (!refLum.TryGetValue(cat, out float r)) refLum[cat] = r = Lum(V3Materials.Resolve(cat).Reference);
            float ratio = Lum(target) / Mathf.Max(0.005f, r);
            return ratio > 0.4f && ratio < 2.4f;
        }

        // Is the kit colour near a palette swatch (the kit's chalk trims, the glass, the mustard gas pipe...).
        public static bool Near(Color c, Color swatch, float tol = 0.06f) =>
            Mathf.Abs(c.r - swatch.r) + Mathf.Abs(c.g - swatch.g) + Mathf.Abs(c.b - swatch.b) < tol * 3f;

        // ---------------------------------------------------------------- shell

        // Walls from the lowest ground to the top (+ parapet), the band below the pad in the plinth colour, flat roof or
        // pitched roofs per footprint rectangle. Fascia and parapet caps in the trim colour.
        public void BuildShell(float parapet, bool pitched, float roofPitch, float eaves)
        {
            float wallTop = H + (pitched ? 0f : parapet);
            foreach (Edge e in Edges)
            {
                if (e.Len < 0.05f) continue;
                WallQuad(Shell, e, Low, 0f, Plinth, WallCat == "3b_plaster_stucco" ? "3c_concrete_panels" : WallCat);
                WallQuad(Shell, e, 0f, wallTop, Wall, WallCat);
                if (!pitched && parapet > 0.05f)
                {
                    // Inner face and a chalk cap 0.40 wide, 0.10 proud outside (bible 7.2).
                    Vector3 inA = e.A - e.N * 0.25f, inB = e.B - e.N * 0.25f;
                    Shell.QuadFacing(WallCat, inA + Vector3.up * H, inA + Vector3.up * wallTop, inB + Vector3.up * wallTop, inB + Vector3.up * H, -e.N, Wall);
                    Shell.Box("3c_concrete_panels", At(e, e.Len / 2f, wallTop + 0.075f, -0.1f), new Vector3(e.Len + 0.2f, 0.15f, 0.42f),
                        Quaternion.LookRotation(-e.N), Trim);
                }
            }
            if (!pitched || Rects.Count == 0)
            {
                Shell.PlanTris(RoofCat, B.tris, H, B.x, B.y, RoofColour);
                Top = Mathf.Max(Top, wallTop);
                Lod2.PlanTris(RoofCat, B.tris, H, B.x, B.y, RoofColour);
            }
            else
                foreach (Rect r in Rects)
                {
                    if (Roof == "hip") Hip(r, roofPitch, eaves);
                    else if (Roof == "shed") Shed(r, roofPitch, eaves);
                    else Gable(r, roofPitch, eaves);
                }
        }

        private static void WallQuad(V3Mesh m, Edge e, float y0, float y1, Color c, string cat)
        {
            if (y1 - y0 < 1e-3f) return;
            m.Quad(cat, e.A + Vector3.up * y0, e.A + Vector3.up * y1, e.B + Vector3.up * y1, e.B + Vector3.up * y0, c);
        }

        private void Gable(Rect r, float pitch, float e)
        {
            float t = Mathf.Tan(pitch * Mathf.Deg2Rad), th = 0.18f;
            float rise = r.Hv * t, eaveY = H - e * t, ridgeY = H + rise;
            Vector3 up = Vector3.up;
            for (int side = -1; side <= 1; side += 2)
            {
                Vector3 vs = r.V * side;
                Vector3 e0 = r.C - r.U * (r.Hu + e) + vs * (r.Hv + e) + up * eaveY;
                Vector3 e1 = r.C + r.U * (r.Hu + e) + vs * (r.Hv + e) + up * eaveY;
                Vector3 r0 = r.C - r.U * (r.Hu + e) + up * ridgeY;
                Vector3 r1 = r.C + r.U * (r.Hu + e) + up * ridgeY;
                Vector3 facing = up + vs * t;
                Shell.QuadFacing(RoofCat, e0, r0, r1, e1, facing, RoofColour);
                Vector3 dn = up * -th;
                Shell.QuadFacing("3c_concrete_panels", e0 + dn, r0 + dn, r1 + dn, e1 + dn, -facing, Trim);
                Shell.QuadFacing("3c_concrete_panels", e0, e1, e1 + dn, e0 + dn, vs, Trim);
                Shell.QuadFacing("3c_concrete_panels", e0, r0, r0 + dn, e0 + dn, -r.U, Trim);
                Shell.QuadFacing("3c_concrete_panels", e1, r1, r1 + dn, e1 + dn, r.U, Trim);
            }
            // Ridge cap in the roof's dark tone.
            Shell.Box(RoofCat, r.C + Vector3.up * (ridgeY + 0.05f), new Vector3(0.22f, 0.12f, r.Hu * 2f + e * 2f), Quaternion.LookRotation(r.U), RoofColour * 0.82f);
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 uo = r.U * (su * r.Hu);
                Shell.TriFacing(WallCat, r.C + uo - r.V * r.Hv + up * H, r.C + uo + r.V * r.Hv + up * H, r.C + uo + up * ridgeY, r.U * su, Wall);
            }
            Top = Mathf.Max(Top, ridgeY + 0.1f);
        }

        private void Hip(Rect r, float pitch, float e)
        {
            float t = Mathf.Tan(pitch * Mathf.Deg2Rad), th = 0.18f;
            float rise = r.Hv * t, eaveY = H - e * t, ridgeY = H + rise, rh = Mathf.Max(0f, r.Hu - r.Hv);
            Vector3 up = Vector3.up, dn = up * -th;
            Vector3 E(int su, int sv) => r.C + r.U * (su * (r.Hu + e)) + r.V * (sv * (r.Hv + e)) + up * eaveY;
            Vector3 R(int su) => r.C + r.U * (su * rh) + up * ridgeY;
            for (int sv = -1; sv <= 1; sv += 2)
            {
                Vector3 facing = up + r.V * (sv * t);
                if (rh > 0.01f) Shell.QuadFacing(RoofCat, E(-1, sv), R(-1), R(1), E(1, sv), facing, RoofColour);
                else Shell.TriFacing(RoofCat, E(-1, sv), R(0), E(1, sv), facing, RoofColour);
                Shell.QuadFacing("3c_concrete_panels", E(-1, sv) + dn, R(-1) + dn, R(1) + dn, E(1, sv) + dn, -facing, Trim);
                Shell.QuadFacing("3c_concrete_panels", E(-1, sv), E(1, sv), E(1, sv) + dn, E(-1, sv) + dn, r.V * sv, Trim);
            }
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 facing = up + r.U * (su * t);
                Shell.TriFacing(RoofCat, E(su, -1), R(su), E(su, 1), facing, RoofColour);
                Shell.TriFacing("3c_concrete_panels", E(su, -1) + dn, R(su) + dn, E(su, 1) + dn, -facing, Trim);
                Shell.QuadFacing("3c_concrete_panels", E(su, -1), E(su, 1), E(su, 1) + dn, E(su, -1) + dn, r.U * su, Trim);
            }
            Top = Mathf.Max(Top, ridgeY);
        }

        private void Shed(Rect r, float pitch, float e)
        {
            float t = Mathf.Tan(Mathf.Min(pitch, 18f) * Mathf.Deg2Rad), th = 0.15f;
            Vector3 front = Edges[Front].N;
            float sh = Vector3.Dot(r.V, front) >= 0f ? 1f : -1f;
            float rise = 2f * r.Hv * t;
            Vector3 up = Vector3.up, dn = up * -th, vs = r.V * sh;
            Vector3 l0 = r.C - r.U * (r.Hu + e) - vs * (r.Hv + e) + up * (H - e * t);
            Vector3 l1 = r.C + r.U * (r.Hu + e) - vs * (r.Hv + e) + up * (H - e * t);
            Vector3 h0 = r.C - r.U * (r.Hu + e) + vs * (r.Hv + e) + up * (H + rise + e * t);
            Vector3 h1 = r.C + r.U * (r.Hu + e) + vs * (r.Hv + e) + up * (H + rise + e * t);
            Vector3 facing = up - vs * t;
            Shell.QuadFacing(RoofCat, l0, h0, h1, l1, facing, RoofColour);
            Shell.QuadFacing("3c_concrete_panels", l0 + dn, h0 + dn, h1 + dn, l1 + dn, -facing, Trim);
            Shell.QuadFacing("3c_concrete_panels", l0, l1, l1 + dn, l0 + dn, -vs, Trim);
            Shell.QuadFacing("3c_concrete_panels", h0, h1, h1 + dn, h0 + dn, vs, Trim);
            Shell.QuadFacing("3c_concrete_panels", l0, h0, h0 + dn, l0 + dn, -r.U, Trim);
            Shell.QuadFacing("3c_concrete_panels", l1, h1, h1 + dn, l1 + dn, r.U, Trim);
            Vector3 hiA = r.C - r.U * r.Hu + vs * r.Hv, hiB = r.C + r.U * r.Hu + vs * r.Hv;
            Shell.QuadFacing(WallCat, hiA + up * H, hiA + up * (H + rise), hiB + up * (H + rise), hiB + up * H, vs, Wall);
            for (int su = -1; su <= 1; su += 2)
            {
                Vector3 uo = r.U * (su * r.Hu);
                Shell.TriFacing(WallCat, r.C + uo - vs * r.Hv + up * H, r.C + uo + vs * r.Hv + up * H, r.C + uo + vs * r.Hv + up * (H + rise), r.U * su, Wall);
            }
            Top = Mathf.Max(Top, H + rise);
        }

        // Height of the roof surface over local (x, z) (pitched roofs: the highest rect slope there; flat: H).
        public float RoofY(Vector3 p, float pitch)
        {
            if (Roof == "flat" || Rects.Count == 0) return H;
            float t = Mathf.Tan(pitch * Mathf.Deg2Rad), best = H;
            foreach (Rect r in Rects)
            {
                Vector3 d = p - r.C;
                float u = Vector3.Dot(d, r.U), v = Vector3.Dot(d, r.V);
                if (Mathf.Abs(u) > r.Hu || Mathf.Abs(v) > r.Hv) continue;
                float y = Roof == "shed" ? H + (v * (Vector3.Dot(r.V, Edges[Front].N) >= 0f ? 1f : -1f) + r.Hv) * Mathf.Tan(Mathf.Min(pitch, 18f) * Mathf.Deg2Rad)
                    : H + (r.Hv - Mathf.Abs(v)) * t;
                best = Mathf.Max(best, y);
            }
            return best;
        }

        // ---------------------------------------------------------------- LOD stand-ins

        // A window seen from 60-220 m: frame quad, glass quad and a sill; beyond 220 m the glass alone.
        public void FlatWindow(Edge e, float u, float y0, float w, float h, Color glass, bool sill = true)
        {
            Quaternion rot = Quaternion.LookRotation(-e.N);
            Vector3 c = At(e, u, y0 + h / 2f, 0.03f);
            Vector3 r = e.Dir * (w / 2f), up = Vector3.up * (h / 2f);
            Lod1.Quad("3b_plaster_stucco", c - r - up, c - r + up, c + r + up, c + r - up, Frame);
            float fw = Mathf.Min(0.13f, w * 0.15f);
            Vector3 cg = At(e, u, y0 + h / 2f, 0.045f);
            Vector3 rg = e.Dir * (w / 2f - fw), ug = Vector3.up * (h / 2f - fw);
            Lod1.Quad("glass", cg - rg - ug, cg - rg + ug, cg + rg + ug, cg + rg - ug, glass);
            if (sill) Lod1.Box("3c_concrete_panels", At(e, u, y0 + 0.03f, 0.06f), new Vector3(w + 0.16f, 0.07f, 0.13f), rot, Frame);
            Vector3 c2 = At(e, u, y0 + h / 2f, 0.03f);
            Lod2.Quad("glass", c2 - rg - ug, c2 - rg + ug, c2 + rg + ug, c2 + rg - ug, glass);
        }

        // A proud horizontal band along an edge (belts, cornice stand-ins, slabs), into the given sink.
        public static void Band(V3Mesh m, string cat, Edge e, float y0, float y1, float off, Color c, float extend = 0f)
        {
            Quaternion rot = Quaternion.LookRotation(-e.N);
            m.Box(cat, At(e, e.Len / 2f, (y0 + y1) / 2f, off / 2f), new Vector3(e.Len + extend * 2f, y1 - y0, off), rot, c, true);
        }
    }
}
