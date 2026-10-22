using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    // Geometry helpers (as TextureTestHousesV07: one mesh per surface per variant, colour per face in vertex colours, UV = metres / tile),
    // map materials (T2M_*), prop material sets (T2P_*) and the public generator entry point for the integrator.
    public static partial class TexW86T2
    {
        // ================================================================== mesh batch
        sealed class MB
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> U = new(); public readonly List<Color> C = new(); public readonly List<int> T = new();
            public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); V.Add(d); U.Add(ua); U.Add(ub); U.Add(uc); U.Add(ud); C.Add(col); C.Add(col); C.Add(col); C.Add(col);
                T.Add(n); T.Add(n + 1); T.Add(n + 2); T.Add(n); T.Add(n + 2); T.Add(n + 3);     // front = (b - a) x (c - a)
            }
            public void QuadUp(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color col)
            {
                if (Vector3.Cross(b - a, c - a).y >= 0) Quad(a, b, c, d, ua, ub, uc, ud, col); else Quad(d, c, b, a, ud, uc, ub, ua, col);
            }
            public void Tri(Vector3 a, Vector3 b, Vector3 c, Vector2 ua, Vector2 ub, Vector2 uc, Color col)
            {
                int n = V.Count;
                V.Add(a); V.Add(b); V.Add(c); U.Add(ua); U.Add(ub); U.Add(uc); C.Add(col); C.Add(col); C.Add(col);
                T.Add(n); T.Add(n + 1); T.Add(n + 2);
            }
        }

        sealed class Batch
        {
            public readonly Dictionary<string, MB> ByKey = new();
            public MB this[string k] { get { if (!ByKey.TryGetValue(k, out var mb)) ByKey[k] = mb = new MB(); return mb; } }
        }

        static int meshN;

        static void Flush(Batch b, Transform parent, string name, string folder = null)
        {
            folder ??= MeshDir;
            foreach (var kv in b.ByKey)
            {
                var mb = kv.Value;
                if (mb.V.Count == 0) continue;
                if (!S.TryGetValue(kv.Key, out var surf)) throw new Exception("surface missing: " + kv.Key);
                var mesh = new Mesh { name = name + "_" + kv.Key, indexFormat = mb.V.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.SetVertices(mb.V); mesh.SetUVs(0, mb.U); mesh.SetColors(mb.C); mesh.SetTriangles(mb.T, 0);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, folder + "/" + Safe(mesh.name) + ".asset"); meshN++;
                var go = new GameObject(mesh.name); go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = surf.M;
                if (surf.NoShadow) r.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            }
            b.ByKey.Clear();
        }

        // frame: O + R x + up y + F z (proper rotation, so the winding stays right)
        struct Fr
        {
            public Vector3 O, R, F;
            public Vector3 P(float x, float y, float z) => O + R * x + Vector3.up * y + F * z;
            public Vector3 P(Vector3 v) => P(v.x, v.y, v.z);
            public Vector3 D(Vector3 v) => R * v.x + Vector3.up * v.y + F * v.z;
            public static Fr Yaw(Vector3 o, float deg) { var q = Quaternion.Euler(0, deg, 0); return new Fr { O = o, R = q * Vector3.right, F = q * Vector3.forward }; }
            public Fr Sub(float x, float y, float z, float yawDeg = 0f)
            {
                var q = Quaternion.AngleAxis(yawDeg, Vector3.up);
                return new Fr { O = P(x, y, z), R = q * R, F = q * F };
            }
            // wall frame: x along the wall from p0, y up, z INTO the wall (outward = -F), origin at p0 (p in the frame's x / z)
            public Fr Wall(Vector2 p0, Vector2 p1)
            {
                Vector2 d = (p1 - p0).normalized; var dir = new Vector3(d.x, 0, d.y);
                return new Fr { O = P(p0.x, 0, p0.y), R = D(dir), F = D(-Vector3.Cross(Vector3.up, dir)) };
            }
        }

        static readonly Vector3[] Dirs = { Vector3.right, Vector3.left, Vector3.forward, Vector3.back, Vector3.up, Vector3.down };
        static float Ext(Vector3 size, Vector3 a) => Mathf.Abs(a.x) * size.x + Mathf.Abs(a.y) * size.y + Mathf.Abs(a.z) * size.z;

        static void Wall(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, Color col, float o = 0f)
        {
            var s = S[key];
            float Uu(float x) => x / s.TU; float Vv(float y) => y / s.TV;
            b[key].Quad(w.P(s0, y0, -o), w.P(s0, y1, -o), w.P(s1, y1, -o), w.P(s1, y0, -o),
                new(Uu(s0), Vv(y0)), new(Uu(s0), Vv(y1)), new(Uu(s1), Vv(y1)), new(Uu(s1), Vv(y0)), col);
        }

        // oriented box: centre c, axes X Y Z (X x Y = Z), size along them; UV = metres along the face axes / tile; mask skips faces
        static void OBox(Batch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, Vector3 size, Color col, bool bottom = true, bool top = true)
        {
            var s = S[key];
            foreach (var n in Dirs)
            {
                if (n == Vector3.down && !bottom) continue;
                if (n == Vector3.up && !top) continue;
                Vector3 ua = Mathf.Abs(n.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(n, ua);
                float hw = Ext(size, ra) / 2, hh = Ext(size, ua) / 2;
                Vector3 fc = n * Ext(size, n) / 2;
                Vector3 Lp(Vector3 p) => c + Xa * p.x + Ya * p.y + Za * p.z;
                Vector3 wa = Xa * ra.x + Ya * ra.y + Za * ra.z, wu = Xa * ua.x + Ya * ua.y + Za * ua.z;
                Vector3 a = Lp(fc - ra * hw - ua * hh), bb = Lp(fc - ra * hw + ua * hh), cc = Lp(fc + ra * hw + ua * hh), d = Lp(fc + ra * hw - ua * hh);
                Vector2 Uv(Vector3 p) => new(Vector3.Dot(p, wa) / s.TU, Vector3.Dot(p, wu) / s.TV);
                b[key].Quad(a, bb, cc, d, Uv(a), Uv(bb), Uv(cc), Uv(d), col);
            }
        }

        static void Box(Batch b, string key, Fr f, Vector3 c, Vector3 size, Color col, bool bottom = true, bool top = true) => OBox(b, key, f.P(c), f.R, Vector3.up, f.F, size, col, bottom, top);
        // box from min to max corner in the frame
        static void BoxF(Batch b, string key, Fr f, Vector3 min, Vector3 max, Color col, bool bottom = true) => Box(b, key, f, (min + max) / 2, max - min, col, bottom);

        // box on a wall: s0..s1 along, y0..y1, `depth` out of the wall (+1 cm into it)
        static void WallBox(Batch b, string key, Fr w, float s0, float s1, float y0, float y1, float depth, Color col)
            => Box(b, key, w, new Vector3((s0 + s1) / 2, (y0 + y1) / 2, (-depth + .01f) / 2), new Vector3(s1 - s0, y1 - y0, depth + .01f), col);

        // horizontal rectangle (facing up) in the frame
        static void Plane(Batch b, string key, Fr f, float x0, float z0, float x1, float z1, float y, Color col)
        {
            var s = S[key];
            Vector3 A = f.P(x0, y, z0), B = f.P(x0, y, z1), C = f.P(x1, y, z1), D = f.P(x1, y, z0);
            b[key].Quad(A, B, C, D, new(A.x / s.TU, A.z / s.TV), new(B.x / s.TU, B.z / s.TV), new(C.x / s.TU, C.z / s.TV), new(D.x / s.TU, D.z / s.TV), col);
        }

        // beam between two points, w x h section
        static void Beam(Batch b, string key, Vector3 p0, Vector3 p1, float w, float h, Color col)
        {
            Vector3 d = p1 - p0; float L = d.magnitude; if (L < 1e-4f) return;
            Vector3 Za = d / L, up = Mathf.Abs(Za.y) > .95f ? Vector3.forward : Vector3.up;
            Vector3 Xa = Vector3.Cross(up, Za).normalized, Ya = Vector3.Cross(Za, Xa);
            OBox(b, key, (p0 + p1) / 2, Xa, Ya, Za, new Vector3(w, h, L), col);
        }

        // cylinder along Ya from base c (Xa x Ya = Za), radius r (top r2), n facets
        static void CylF(Batch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, float r, float h, int n, Color col, bool top = true, bool bottom = false, float r2 = -1f)
        {
            if (r2 < 0) r2 = r;
            var s = S[key]; var mb = b[key];
            float circ = 2 * Mathf.PI * r;
            Vector3 D(float a) => Xa * Mathf.Sin(a) + Za * Mathf.Cos(a);
            Vector3 tc = c + Ya * h;
            for (int i = 0; i < n; i++)
            {
                float a0 = 2 * Mathf.PI * i / n, a1 = 2 * Mathf.PI * (i + 1) / n;
                Vector3 b0 = c + D(a0) * r, b1 = c + D(a1) * r, t0 = tc + D(a0) * r2, t1 = tc + D(a1) * r2;
                float u0 = circ * i / n / s.TU, u1 = circ * (i + 1) / n / s.TU, v1 = h / s.TV;
                mb.Quad(b1, t1, t0, b0, new(u1, 0), new(u1, v1), new(u0, v1), new(u0, 0), col);
                if (top && r2 > 0) mb.Tri(tc, t0, t1, new(.5f, .5f), new(.5f + Mathf.Sin(a0) * r2 / s.TU, .5f + Mathf.Cos(a0) * r2 / s.TV), new(.5f + Mathf.Sin(a1) * r2 / s.TU, .5f + Mathf.Cos(a1) * r2 / s.TV), col);
                if (bottom) mb.Tri(c, b1, b0, new(.5f, .5f), new(.5f + Mathf.Sin(a1) * r / s.TU, .5f + Mathf.Cos(a1) * r / s.TV), new(.5f + Mathf.Sin(a0) * r / s.TU, .5f + Mathf.Cos(a0) * r / s.TV), col);
            }
        }
        static void Cyl(Batch b, string key, Vector3 c, float r, float h, int n, Color col, bool top = true, float r2 = -1f) => CylF(b, key, c, Vector3.right, Vector3.up, Vector3.forward, r, h, n, col, top, false, r2);
        static void CylAx(Batch b, string key, Vector3 c, Vector3 axis, float r, float len, int n, Color col)
        {
            Vector3 Ya = axis.normalized, Xa = Vector3.Cross(Ya, Mathf.Abs(Ya.y) > .9f ? Vector3.right : Vector3.up).normalized, Za = Vector3.Cross(Xa, Ya);
            CylF(b, key, c - Ya * len / 2, Xa, Ya, Za, r, len, n, col, true, true);
        }

        // flat annulus facing up (world UV)
        static void Ring(Batch b, string key, Vector3 c, float r0, float r1, int n, Color col, float a0deg = 0f, float a1deg = 360f)
        {
            var s = S[key];
            for (int i = 0; i < n; i++)
            {
                float a0 = Mathf.Deg2Rad * Mathf.Lerp(a0deg, a1deg, i / (float)n), a1 = Mathf.Deg2Rad * Mathf.Lerp(a0deg, a1deg, (i + 1) / (float)n);
                Vector3 d0 = new(Mathf.Sin(a0), 0, Mathf.Cos(a0)), d1 = new(Mathf.Sin(a1), 0, Mathf.Cos(a1));
                Vector3 p0 = c + d0 * r0, p1 = c + d0 * r1, p2 = c + d1 * r1, p3 = c + d1 * r0;
                Vector2 Uv(Vector3 p) => new(p.x / s.TU, p.z / s.TV);
                b[key].Quad(p0, p1, p2, p3, Uv(p0), Uv(p1), Uv(p2), Uv(p3), col);
            }
        }

        // convex / star-shaped polygon (frame x / z points) as an up-facing fan at height y, world UV
        static void Poly(Batch b, string key, Fr f, IList<Vector2> pts, float y, Color col)
        {
            var s = S[key];
            Vector2 c = Vector2.zero; foreach (var p in pts) c += p; c /= pts.Count;
            Vector3 C = f.P(c.x, y, c.y);
            for (int i = 0; i < pts.Count; i++)
            {
                Vector3 A = f.P(pts[i].x, y, pts[i].y), B = f.P(pts[(i + 1) % pts.Count].x, y, pts[(i + 1) % pts.Count].y);
                if (Vector3.Cross(A - C, B - C).y >= 0) b[key].Tri(C, A, B, new(C.x / s.TU, C.z / s.TV), new(A.x / s.TU, A.z / s.TV), new(B.x / s.TU, B.z / s.TV), col);
                else b[key].Tri(C, B, A, new(C.x / s.TU, C.z / s.TV), new(B.x / s.TU, B.z / s.TV), new(A.x / s.TU, A.z / s.TV), col);
            }
        }

        // vertical skirt along a closed polygon (frame x / z, either winding), from y0 to y1, faces out (or in)
        static void Skirt(Batch b, string key, Fr f, IList<Vector2> pts, float y0, float y1, Color col, bool inward = false)
        {
            var s = S[key]; float u = 0;
            float area = 0; for (int i = 0; i < pts.Count; i++) { var p0 = pts[i]; var p1 = pts[(i + 1) % pts.Count]; area += p0.x * p1.y - p1.x * p0.y; }
            if (area < 0) inward = !inward;                                   // clockwise polygon: flip so the faces still point out (or in)
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 p = pts[i], q = pts[(i + 1) % pts.Count]; float L = (q - p).magnitude;
                Vector3 A = f.P(p.x, y0, p.y), B = f.P(p.x, y1, p.y), C = f.P(q.x, y1, q.y), D = f.P(q.x, y0, q.y);
                if (inward) b[key].Quad(D, C, B, A, new((u + L) / s.TU, y0 / s.TV), new((u + L) / s.TU, y1 / s.TV), new(u / s.TU, y1 / s.TV), new(u / s.TU, y0 / s.TV), col);
                else b[key].Quad(A, B, C, D, new(u / s.TU, y0 / s.TV), new(u / s.TU, y1 / s.TV), new((u + L) / s.TU, y1 / s.TV), new((u + L) / s.TU, y0 / s.TV), col);
                u += L;
            }
        }

        static List<Vector2> Ellipse(float rx, float rz, int n, float cx = 0, float cz = 0)
        {
            var l = new List<Vector2>();
            for (int i = 0; i < n; i++) { float a = -2 * Mathf.PI * i / n; l.Add(new Vector2(cx + Mathf.Cos(a) * rx, cz + Mathf.Sin(a) * rz)); }
            return l;
        }

        // window opening wall: wall s 0..L, y0..y1 with rectangular openings; reveals `recess` deep in the wall material
        static void OpeningsWall(Batch b, string key, Fr w, float L, float y0, float y1, Color col, List<Rect> holes, float recess)
        {
            var xs = new SortedSet<float> { 0, L }; var ys = new SortedSet<float> { y0, y1 };
            foreach (var h in holes) { xs.Add(Mathf.Clamp(h.xMin, 0, L)); xs.Add(Mathf.Clamp(h.xMax, 0, L)); ys.Add(Mathf.Clamp(h.yMin, y0, y1)); ys.Add(Mathf.Clamp(h.yMax, y0, y1)); }
            var xl = xs.ToList(); var yl = ys.ToList();
            for (int i = 0; i + 1 < xl.Count; i++)
                for (int j = 0; j + 1 < yl.Count; j++)
                {
                    var c = new Vector2((xl[i] + xl[i + 1]) / 2, (yl[j] + yl[j + 1]) / 2);
                    if (holes.Any(h => h.Contains(c))) continue;
                    Wall(b, key, w, xl[i], xl[i + 1], yl[j], yl[j + 1], col);
                }
            foreach (var h in holes)
            {
                Box(b, key, w, new Vector3(h.xMin - .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col);
                Box(b, key, w, new Vector3(h.xMax + .005f, h.center.y, recess / 2), new Vector3(.01f, h.height, recess), col);
                Box(b, key, w, new Vector3(h.center.x, h.yMax + .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col);
                if (h.yMin > y0 + .01f) Box(b, key, w, new Vector3(h.center.x, h.yMin - .005f, recess / 2), new Vector3(h.width + .02f, .01f, recess), col);
            }
        }

        // glass pane with one cell of the 4 x 4 office glass atlas (v07)
        static void Pane(Batch b, string key, Fr w, Rect o, float z, int cell)
        {
            int cx = cell % 4, cy = (cell / 4) % 4; const float e = .012f;
            var uv = Rect.MinMaxRect(cx / 4f + e, cy / 4f + e, (cx + 1) / 4f - e, (cy + 1) / 4f - e);
            b[key].Quad(w.P(o.xMin, o.yMin, z), w.P(o.xMin, o.yMax, z), w.P(o.xMax, o.yMax, z), w.P(o.xMax, o.yMin, z),
                new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }

        // framed window: glass, frame profile, mullion (+ transom), sill; surround (architrave) optional
        static void Window(Batch b, Fr w, Rect o, float r, Color frame, Color sill, bool transom, string glass = "glass_dark", float surround = 0f, Color? surroundCol = null, string id = "")
        {
            if (glass == "glass_atlas") Pane(b, glass, w, o, r + .005f, (int)(Hash(id, 5) * 16) % 16);
            else Box(b, glass, w, new Vector3(o.center.x, o.center.y, r + .005f), new Vector3(o.width, o.height, .01f), Color.white);
            float t = .07f, zc = r - .03f;
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .06f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .06f), frame);
            Box(b, "flat", w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame);
            Box(b, "flat", w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.center.y, zc), new Vector3(.05f, o.height, .05f), frame);
            if (transom) Box(b, "flat", w, new Vector3(o.center.x, o.yMin + o.height * .7f, zc), new Vector3(o.width, .05f, .05f), frame);
            Box(b, "flat", w, new Vector3(o.center.x, o.yMin - .04f, (r - .08f) / 2), new Vector3(o.width + .2f, .08f, r + .08f), sill);
            if (surround > 0)
            {
                var sc = surroundCol ?? sill;
                Box(b, "flat", w, new Vector3(o.xMin - surround / 2, o.center.y, -.02f), new Vector3(surround, o.height + surround, .04f), sc);
                Box(b, "flat", w, new Vector3(o.xMax + surround / 2, o.center.y, -.02f), new Vector3(surround, o.height + surround, .04f), sc);
                Box(b, "flat", w, new Vector3(o.center.x, o.yMax + surround / 2, -.02f), new Vector3(o.width + surround * 2, surround, .04f), sc);
            }
        }

        // triangular pediment on a wall (front face), base at y, width W, height H, depth d
        static void Pediment(Batch b, string key, Fr w, float cx, float y, float W, float H, float d, Color col)
        {
            var s = S[key]; var mb = b[key];
            Vector3 A = w.P(cx - W / 2, y, -d), B = w.P(cx, y + H, -d), C = w.P(cx + W / 2, y, -d);
            Vector3 A0 = w.P(cx - W / 2, y, 0), B0 = w.P(cx, y + H, 0), C0 = w.P(cx + W / 2, y, 0);
            Vector2 Uv(float x, float yy) => new(x / s.TU, yy / s.TV);
            mb.Tri(A, B, C, Uv(cx - W / 2, y), Uv(cx, y + H), Uv(cx + W / 2, y), col);
            mb.Quad(A0, B0, B, A, Uv(0, 0), Uv(0, H), Uv(d, H), Uv(d, 0), col);
            mb.Quad(B0, C0, C, B, Uv(0, H), Uv(0, 0), Uv(d, 0), Uv(d, H), col);
        }

        // faceted low-poly rock: subdivided cube pushed toward a sphere, noise displaced, flat bottom, box-projected UV (metres / tile)
        static void Rock(Batch b, string key, Fr f, Vector3 centre, Vector3 size, int seed, Color col, int n = 6)
        {
            var s = S[key]; var mb = b[key];
            var rnd = new System.Random(seed);
            float ph = (float)rnd.NextDouble() * 100f;
            Vector3 Pt(Vector3 cube)
            {
                Vector3 sp = cube.normalized;
                Vector3 p = Vector3.Lerp(cube * .9f, sp, .55f);
                float nz = Mathf.PerlinNoise(p.x * 1.7f + ph, p.z * 1.7f + p.y * .9f) - .5f + (Mathf.PerlinNoise(p.x * 4.1f + ph, p.y * 4.1f - p.z) - .5f) * .45f;
                p *= 1f + nz * .42f;
                p = Vector3.Scale(p, size * .5f);
                if (p.y < -size.y * .42f) p.y = -size.y * .42f;
                return p;
            }
            foreach (var nrm in Dirs)
            {
                Vector3 ua = Mathf.Abs(nrm.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(nrm, ua);
                for (int i = 0; i < n; i++)
                    for (int j = 0; j < n; j++)
                    {
                        Vector3 G(int a, int c) => nrm + ra * (2f * a / n - 1) + ua * (2f * c / n - 1);
                        Vector3 q0 = Pt(G(i, j)), q1 = Pt(G(i, j + 1)), q2 = Pt(G(i + 1, j + 1)), q3 = Pt(G(i + 1, j));
                        void T(Vector3 p0, Vector3 p1, Vector3 p2)
                        {
                            Vector3 w0 = f.P(centre + p0), w1 = f.P(centre + p1), w2 = f.P(centre + p2);
                            Vector3 fn = Vector3.Cross(w1 - w0, w2 - w0);
                            Vector2 Uv(Vector3 p) => Mathf.Abs(fn.y) > Mathf.Abs(fn.x) && Mathf.Abs(fn.y) > Mathf.Abs(fn.z) ? new(p.x / s.TU, p.z / s.TV)
                                : Mathf.Abs(fn.x) > Mathf.Abs(fn.z) ? new(p.z / s.TU, p.y / s.TV) : new(p.x / s.TU, p.y / s.TV);
                            float sh = .92f + .08f * Mathf.PerlinNoise(p0.x * .3f + ph, p0.z * .3f);
                            mb.Tri(w0, w1, w2, Uv(w0), Uv(w1), Uv(w2), col * sh);
                        }
                        T(q0, q1, q2); T(q0, q2, q3);
                    }
            }
        }

        // ---------------- props (prefab instances of the map library, read only)
        static readonly List<string> UsedProps = new();
        static GameObject Prop(string rel, Transform parent, Vector3 pos, float yaw, float scale = 1f)
        {
            string path = rel.StartsWith("Assets/") ? rel : MP + rel + ".prefab";
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!src) { Note("prop missing: " + path); return null; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            go.transform.localPosition = pos; go.transform.localRotation = Quaternion.Euler(0, yaw, 0); go.transform.localScale *= scale;
            if (!UsedProps.Contains(path)) UsedProps.Add(path);
            return go;
        }

        // ================================================================== map materials (T2M_*): onto existing W85 renderers
        // W85 meshes carry no vertex colour (reads as white) and UV = metres / tile_m of their material key (materials_v85.json), so a
        // map material keeps _TintRef = 1, puts the colour into _BaseColor (relative to the texture mean) and scales the texture to the
        // builder's tile: _BaseMap_ST = builderTile / texture metres. (Tinted renderers: the W85 builder's property-block _BaseColor would
        // override the colour; none of the T2M targets has a tint.)
        public static readonly Dictionary<string, (Material m, string note)> MapMats = new();

        static Material MapMat(string name, string key, string hex, float builderTileU, float builderTileV, string note, float smooth = -1f)
        {
            var src = S[key];
            var m = new Material(src.M) { name = "T2M_" + name, enableInstancing = true };
            m.SetVector("_TintRef", Vector4.one);
            Color own = src.Own, tgt = hex == null ? own : X(hex);
            var lin = new Color(tgt.linear.r / Mathf.Max(.02f, own.linear.r), tgt.linear.g / Mathf.Max(.02f, own.linear.g), tgt.linear.b / Mathf.Max(.02f, own.linear.b), 1f);
            m.SetColor("_BaseColor", lin.gamma);
            m.SetTextureScale("_BaseMap", new Vector2(builderTileU / src.TU, builderTileV / src.TV));
            if (smooth >= 0) m.SetFloat("_Smoothness", smooth);
            m = SaveOrLoad(m, MatDir + "/Map/T2M_" + name + ".mat");
            MapMats[name] = (m, note);
            return m;
        }

        // a map-style mesh (no vertex colour, builder UV convention) to prove a T2M material in the test scene
        static GameObject MapMesh(Transform parent, string name, List<Vector3> v, List<Vector2> uv, List<int> t, Material m)
        {
            var mesh = new Mesh { name = name };
            mesh.SetVertices(v); mesh.SetUVs(0, uv); mesh.SetTriangles(t, 0);
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, MeshDir + "/" + Safe(name) + ".asset"); meshN++;
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = m;
            return go;
        }

        // builder-style flat polygon (W85 Fill / Pier deck): UV = world x / z / tile
        static GameObject MapFlat(Transform parent, string name, Fr f, IList<Vector2> pts, float y, float tile, Material m)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            Vector2 c = Vector2.zero; foreach (var p in pts) c += p; c /= pts.Count;
            v.Add(f.P(c.x, y, c.y));
            foreach (var p in pts) v.Add(f.P(p.x, y, p.y));
            foreach (var q in v) uv.Add(new Vector2(q.x, q.z) / tile);
            for (int i = 0; i < pts.Count; i++) { t.Add(0); t.Add(1 + (i + 1) % pts.Count); t.Add(1 + i); }
            return MapMesh(parent, name, v, uv, t, m);
        }

        // builder-style vertical strip along a polyline: UV (along / tileU, height / tileV), double sided (Fence / PierSkirt)
        static GameObject MapStrip(Transform parent, string name, Fr f, IList<Vector2> line, float y0, float y1, float tileU, float tileV, Material m, bool closed = false)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            int n = line.Count + (closed ? 1 : 0); float u = 0;
            for (int i = 1; i < n; i++)
            {
                Vector2 a = line[i - 1], c = line[i % line.Count]; float L = (c - a).magnitude;
                int k = v.Count;
                v.Add(f.P(a.x, y0, a.y)); v.Add(f.P(a.x, y1, a.y)); v.Add(f.P(c.x, y1, c.y)); v.Add(f.P(c.x, y0, c.y));
                uv.Add(new(u / tileU, 0)); uv.Add(new(u / tileU, (y1 - y0) / tileV)); uv.Add(new((u + L) / tileU, (y1 - y0) / tileV)); uv.Add(new((u + L) / tileU, 0));
                t.AddRange(new[] { k, k + 1, k + 2, k, k + 2, k + 3, k + 3, k + 2, k + 1, k + 3, k + 1, k });
                u += L;
            }
            return MapMesh(parent, name, v, uv, t, m);
        }

        // ================================================================== prop material sets (T2P_*, URP Lit flat like the MP_* set)
        static readonly Dictionary<string, Material> PropMats = new();
        static Material PropMat(string name, string hex, float smooth = .2f, string texKey = null, float metal = 0f)
        {
            if (PropMats.TryGetValue(name, out var e)) return e;
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "T2P_" + name, enableInstancing = true };
            m.SetColor("_BaseColor", X(hex)); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (texKey != null && S.TryGetValue(texKey, out var s) && s.M.GetTexture("_BaseMap") is Texture t)
            {
                m.SetTexture("_BaseMap", t);
                var own = s.Own; var c = X(hex);
                m.SetColor("_BaseColor", new Color(c.r / Mathf.Max(.05f, own.r), c.g / Mathf.Max(.05f, own.g), c.b / Mathf.Max(.05f, own.b), 1f));
            }
            m = SaveOrLoad(m, MatDir + "/Props/T2P_" + name + ".mat");
            return PropMats[name] = m;
        }

        static Material MPm(string name) => AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Art/Map/Materials/" + name + ".mat");

        static void SetMats(GameObject go, Material[] mats)
        {
            if (!go) return;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                var cur = r.sharedMaterials;
                if (cur.Length == mats.Length) r.sharedMaterials = mats;
                else r.sharedMaterials = cur.Select((m, i) => i < mats.Length && mats[i] ? mats[i] : m).ToArray();
            }
        }

        // ================================================================== public generator (integrator): same code as the test scene
        // code + variant ('a' / 'b' / 'c'), world origin (footprint centre at ground level, or the line's frame), yaw (deg, front = -Z of
        // the frame = the side the data entrance faces), size (x length, y height, z depth; 0 = data default). Meshes go to meshFolder.
        // tint: wall colour of the data (beach bars / rental hut, e.g. "#F6C9C4"); the T98 pool is built without its water quad (keep the
        // W85 Water_Pool_<id> mesh + water area, moved to deck top - 0.12 m)
        static string genTint;
        public static GameObject Generate(string code, char variant, Transform parent, Vector3 origin, float yawDeg, Vector3 size, string meshFolder, string tint = null)
        {
            genTint = string.IsNullOrEmpty(tint) ? null : tint.TrimStart('#');
            if (S.Count == 0 || !S.ContainsKey("marble")) Surfaces(false);
            int v = Mathf.Clamp(variant - 'a', 0, 2);
            var go = new GameObject(code + variant); go.transform.SetParent(parent, false);
            var b = new Batch();
            var f = Fr.Yaw(origin, yawDeg);
            if (!Builders.TryGetValue(code, out var make)) throw new Exception("no generator for " + code);
            make(b, f, size, v, go.transform);
            Flush(b, go.transform, code + variant + "_" + Safe(parent ? parent.name : "x"), meshFolder);
            return go;
        }

        // line generators (fences, quay edges, hedges): points in world x / z, ground height function
        public static GameObject GenerateLine(string code, char variant, Transform parent, Vector2[] line, Func<Vector2, float> ground, string meshFolder, bool closed = false)
        {
            if (S.Count == 0 || !S.ContainsKey("marble")) Surfaces(false);
            int v = Mathf.Clamp(variant - 'a', 0, 2);
            var go = new GameObject(code + variant + "_line"); go.transform.SetParent(parent, false);
            var b = new Batch();
            if (!LineBuilders.TryGetValue(code, out var make)) throw new Exception("no line generator for " + code);
            var pts = line.ToList(); if (closed) pts.Add(line[0]);
            make(b, pts.Select(p => new Vector3(p.x, ground(p), p.y)).ToList(), v);
            Flush(b, go.transform, code + variant + "_line_" + Safe(parent ? parent.name : "x"), meshFolder);
            return go;
        }
    }
}
