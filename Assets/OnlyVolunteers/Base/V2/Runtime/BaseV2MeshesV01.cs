using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// Placeholder geometry of the V2 base P1 (Fedya 31.10), chunky low-poly with modelled details (CLAUDE.md "details are
    /// 3D"): the rubber baton (a police-style straight stick: a ribbed grip with seven raised rings, a steel collar and
    /// butt cap, a rounded tip, a wrist strap loop; submesh 0 rubber, 1 steel) and its counter display stand (a bevelled
    /// base board with two U-cradles). Metres; the baton lies along +Y from its butt (y 0) to its tip (y 0.62).
    /// Placeholders until the reference -> texture -> model workflow gives the final look.
    /// </summary>
    public static class BaseV2MeshesV01
    {
        public const float BatonLength = 0.62f;

        private sealed class Builder
        {
            public readonly List<Vector3> V = new List<Vector3>();
            public readonly List<Vector3> N = new List<Vector3>();
            public readonly List<Vector2> U = new List<Vector2>();
            public readonly List<List<int>> T = new List<List<int>>();

            public Builder(int submeshes) { for (int i = 0; i < submeshes; i++) T.Add(new List<int>()); }

            /// <summary>A convex polygon facing 'normal' (winding fixed from it), flat shaded.</summary>
            public void Poly(int sub, Vector3 normal, params Vector3[] p)
            {
                int b = V.Count;
                for (int i = 0; i < p.Length; i++) { V.Add(p[i]); N.Add(normal); U.Add(new Vector2(p[i].x + p[i].z, p[i].y)); }
                bool flip = Vector3.Dot(Vector3.Cross(p[1] - p[0], p[2] - p[0]), normal) < 0f;
                for (int i = 1; i + 1 < p.Length; i++)
                {
                    T[sub].Add(b);
                    if (flip) { T[sub].Add(b + i + 1); T[sub].Add(b + i); }
                    else { T[sub].Add(b + i); T[sub].Add(b + i + 1); }
                }
            }

            /// <summary>A lathe along +Y through 'profile' (radius, y) pairs: every segment its own ring band (hard edges
            /// between segments, smooth around), flat caps where the profile starts / ends at a radius.</summary>
            public void Lathe(int sub, Vector3 origin, IList<Vector2> profile, int sides, bool capStart, bool capEnd)
            {
                for (int s = 0; s + 1 < profile.Count; s++)
                {
                    Vector2 a = profile[s], c = profile[s + 1];
                    Vector2 d = c - a;
                    Vector2 pn = new Vector2(d.y, -d.x).normalized; // outward in (r, y)
                    if (pn.x < 0f && Mathf.Abs(d.y) > 1e-5f) pn = -pn;
                    int b = V.Count;
                    for (int i = 0; i <= sides; i++)
                    {
                        float ang = i * Mathf.PI * 2f / sides;
                        Vector3 dir = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang));
                        Vector3 nn = (dir * pn.x + Vector3.up * pn.y).normalized;
                        V.Add(origin + dir * a.x + Vector3.up * a.y); N.Add(nn); U.Add(new Vector2((float)i / sides, a.y));
                        V.Add(origin + dir * c.x + Vector3.up * c.y); N.Add(nn); U.Add(new Vector2((float)i / sides, c.y));
                    }
                    for (int i = 0; i < sides; i++)
                    {
                        int p0 = b + i * 2, p1 = p0 + 1, q0 = p0 + 2, q1 = p0 + 3;
                        // outward: (q0 - p0) x (p1 - p0) points out for this ordering
                        T[sub].Add(p0); T[sub].Add(p1); T[sub].Add(q0);
                        T[sub].Add(q0); T[sub].Add(p1); T[sub].Add(q1);
                    }
                }
                if (capStart && profile[0].x > 1e-4f) Cap(sub, origin, profile[0], sides, Vector3.down);
                if (capEnd && profile[profile.Count - 1].x > 1e-4f) Cap(sub, origin, profile[profile.Count - 1], sides, Vector3.up);
            }

            private void Cap(int sub, Vector3 origin, Vector2 ring, int sides, Vector3 normal)
            {
                var pts = new Vector3[sides];
                for (int i = 0; i < sides; i++)
                {
                    float ang = i * Mathf.PI * 2f / sides;
                    pts[i] = origin + new Vector3(Mathf.Cos(ang) * ring.x, ring.y, Mathf.Sin(ang) * ring.x);
                }
                Poly(sub, normal, pts);
            }

            /// <summary>An axis-aligned box (centre, half extents) with every edge chamfered by b: 6 faces, 12 edge strips, 8
            /// corner triangles.</summary>
            public void BevelBox(int sub, Vector3 c, Vector3 h, float b)
            {
                Vector3 P(int ax, float sa, int ay, float sb, int az, float sc)
                {
                    var v = new Vector3();
                    v[ax] = sa; v[ay] = sb; v[az] = sc;
                    return c + v;
                }
                for (int a = 0; a < 3; a++)
                {
                    int u = (a + 1) % 3, w = (a + 2) % 3;
                    for (int s = -1; s <= 1; s += 2)
                    {
                        Vector3 n = Vector3.zero; n[a] = s;
                        float hu = h[u] - b, hw = h[w] - b;
                        Poly(sub, n, P(a, s * h[a], u, hu, w, hw), P(a, s * h[a], u, hu, w, -hw), P(a, s * h[a], u, -hu, w, -hw), P(a, s * h[a], u, -hu, w, hw));
                    }
                }
                for (int a1 = 0; a1 < 3; a1++)
                    for (int a2 = a1 + 1; a2 < 3; a2++)
                    {
                        int a3 = 3 - a1 - a2;
                        for (int s1 = -1; s1 <= 1; s1 += 2)
                            for (int s2 = -1; s2 <= 1; s2 += 2)
                            {
                                Vector3 n = Vector3.zero; n[a1] = s1; n[a2] = s2; n.Normalize();
                                float l = h[a3] - b;
                                Poly(sub, n, P(a1, s1 * h[a1], a2, s2 * (h[a2] - b), a3, l), P(a1, s1 * (h[a1] - b), a2, s2 * h[a2], a3, l),
                                    P(a1, s1 * (h[a1] - b), a2, s2 * h[a2], a3, -l), P(a1, s1 * h[a1], a2, s2 * (h[a2] - b), a3, -l));
                            }
                    }
                for (int sx = -1; sx <= 1; sx += 2)
                    for (int sy = -1; sy <= 1; sy += 2)
                        for (int sz = -1; sz <= 1; sz += 2)
                        {
                            var n = new Vector3(sx, sy, sz).normalized;
                            Poly(sub, n, c + new Vector3(sx * h.x, sy * (h.y - b), sz * (h.z - b)), c + new Vector3(sx * (h.x - b), sy * h.y, sz * (h.z - b)),
                                c + new Vector3(sx * (h.x - b), sy * (h.y - b), sz * h.z));
                        }
            }

            /// <summary>A torus in the plane spanned by axis1/axis2 (the strap loop).</summary>
            public void Torus(int sub, Vector3 centre, Vector3 axis1, Vector3 axis2, float major, float minor, int segs, int sides)
            {
                Vector3 normal = Vector3.Cross(axis1, axis2).normalized;
                int b = V.Count;
                for (int i = 0; i <= segs; i++)
                {
                    float a = i * Mathf.PI * 2f / segs;
                    Vector3 radial = axis1 * Mathf.Cos(a) + axis2 * Mathf.Sin(a);
                    for (int j = 0; j <= sides; j++)
                    {
                        float t = j * Mathf.PI * 2f / sides;
                        Vector3 n = radial * Mathf.Cos(t) + normal * Mathf.Sin(t);
                        V.Add(centre + radial * major + n * minor); N.Add(n); U.Add(new Vector2((float)i / segs, (float)j / sides));
                    }
                }
                for (int i = 0; i < segs; i++)
                    for (int j = 0; j < sides; j++)
                    {
                        int p = b + i * (sides + 1) + j, q = p + sides + 1;
                        Vector3 n = N[p];
                        bool flip = Vector3.Dot(Vector3.Cross(V[q] - V[p], V[p + 1] - V[p]), n) < 0f;
                        if (!flip) { T[sub].Add(p); T[sub].Add(q); T[sub].Add(p + 1); T[sub].Add(p + 1); T[sub].Add(q); T[sub].Add(q + 1); }
                        else { T[sub].Add(p); T[sub].Add(p + 1); T[sub].Add(q); T[sub].Add(p + 1); T[sub].Add(q + 1); T[sub].Add(q); }
                    }
            }

            public Mesh Make(string name)
            {
                var m = new Mesh { name = name };
                m.SetVertices(V);
                m.SetNormals(N);
                m.SetUVs(0, U);
                m.subMeshCount = T.Count;
                for (int i = 0; i < T.Count; i++) m.SetTriangles(T[i], i);
                m.RecalculateBounds();
                m.RecalculateTangents();
                return m;
            }
        }

        /// <summary>The rubber baton: submesh 0 rubber (grip with rings, shaft, tip, strap), 1 steel (butt cap, collar).</summary>
        public static Mesh Baton()
        {
            var b = new Builder(2);
            const int sides = 14;
            float rGrip = 0.0175f, rRing = 0.0205f, rShaft = 0.0165f;
            // steel butt cap: a chamfered disc
            b.Lathe(1, Vector3.zero, new[] { new Vector2(0.021f, 0f), new Vector2(0.026f, 0.004f), new Vector2(0.026f, 0.015f), new Vector2(0.022f, 0.02f) }, sides, true, true);
            // ribbed rubber grip: seven raised rings
            var grip = new List<Vector2> { new Vector2(rGrip, 0.02f) };
            float y = 0.03f;
            for (int i = 0; i < 7; i++)
            {
                grip.Add(new Vector2(rGrip, y));
                grip.Add(new Vector2(rRing, y + 0.003f));
                grip.Add(new Vector2(rRing, y + 0.009f));
                grip.Add(new Vector2(rGrip, y + 0.012f));
                y += 0.02f;
            }
            grip.Add(new Vector2(rGrip, 0.172f));
            b.Lathe(0, Vector3.zero, grip, sides, false, false);
            // steel collar between grip and shaft
            b.Lathe(1, Vector3.zero, new[] { new Vector2(0.021f, 0.172f), new Vector2(0.025f, 0.176f), new Vector2(0.025f, 0.188f), new Vector2(0.021f, 0.192f) }, sides, true, true);
            // shaft and a rounded tip
            var shaft = new List<Vector2> { new Vector2(rShaft, 0.192f), new Vector2(rShaft + 0.0008f, 0.45f), new Vector2(rShaft + 0.0012f, 0.595f) };
            for (int i = 1; i <= 4; i++)
            {
                float a = i / 4f * Mathf.PI * 0.5f;
                shaft.Add(new Vector2((rShaft + 0.0012f) * Mathf.Cos(a), 0.595f + 0.025f * Mathf.Sin(a)));
            }
            b.Lathe(0, Vector3.zero, shaft, sides, true, false);
            // the wrist strap: a loop hanging off the butt cap
            b.Torus(0, new Vector3(0f, -0.036f, 0f), Vector3.up, Vector3.forward, 0.034f, 0.0055f, 16, 6);
            return b.Make("BaseV2_Baton_v01");
        }

        /// <summary>The counter display stand: a bevelled board 0.62 x 0.04 x 0.17 m and two U-cradles 0.42 m apart that
        /// hold the baton 0.075 m above the board (its axis along local X). Origin = the board's bottom centre.</summary>
        public static Mesh Stand()
        {
            var b = new Builder(1);
            b.BevelBox(0, new Vector3(0f, 0.02f, 0f), new Vector3(0.31f, 0.02f, 0.085f), 0.008f);
            foreach (float x in new[] { -0.21f, 0.21f })
            {
                b.BevelBox(0, new Vector3(x, 0.046f, 0f), new Vector3(0.022f, 0.006f, 0.04f), 0.003f);       // the cradle's foot
                b.BevelBox(0, new Vector3(x, 0.07f, 0.03f), new Vector3(0.02f, 0.024f, 0.009f), 0.003f);     // back post
                b.BevelBox(0, new Vector3(x, 0.07f, -0.03f), new Vector3(0.02f, 0.024f, 0.009f), 0.003f);    // front post
                b.BevelBox(0, new Vector3(x, 0.0545f, 0f), new Vector3(0.02f, 0.0025f, 0.022f), 0.0015f);    // the U's floor
            }
            return b.Make("BaseV2_BatonStand_v01");
        }

        /// <summary>Where the baton rests on the stand (local to the stand): centre of the baton's length, axis along X.</summary>
        public static readonly Vector3 StandRest = new Vector3(0f, 0.075f, 0f);
    }
}
