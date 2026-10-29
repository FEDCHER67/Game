using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.W85
{
    /// <summary>
    /// Removes from a mesh every part that lies inside a set of world-space boxes: triangles crossing a box face are split
    /// exactly along it (position, normal, tangent, uv0 / uv1, colour interpolated), the pieces inside are dropped, the rest
    /// is kept with its submesh. Used to open the ground-floor west section of 04-H3 for the pharmacy unit (and the front
    /// garden fence for its path) without touching the rest of the house. Pure geometry, no assets written here.
    /// </summary>
    public static class W86MeshCutV01
    {
        struct PV
        {
            public Vector3 p, w, n; public Vector4 t; public Vector2 uv, uv2; public Color c;
            public static PV Lerp(PV a, PV b, float k) => new PV
            {
                p = Vector3.LerpUnclamped(a.p, b.p, k), w = Vector3.LerpUnclamped(a.w, b.w, k),
                n = Vector3.LerpUnclamped(a.n, b.n, k).normalized,
                t = new Vector4(Mathf.LerpUnclamped(a.t.x, b.t.x, k), Mathf.LerpUnclamped(a.t.y, b.t.y, k), Mathf.LerpUnclamped(a.t.z, b.t.z, k), a.t.w),
                uv = Vector2.LerpUnclamped(a.uv, b.uv, k), uv2 = Vector2.LerpUnclamped(a.uv2, b.uv2, k), c = Color.LerpUnclamped(a.c, b.c, k),
            };
        }

        public struct Result { public Mesh Mesh; public int Kept, Dropped, Split; public bool Changed => Dropped > 0 || Split > 0; }

        /// <summary>True when the world bounds of a renderer / mesh touch any box.</summary>
        public static bool Touches(Bounds world, IList<Bounds> boxes)
        {
            foreach (Bounds b in boxes) if (b.Intersects(world)) return true;
            return false;
        }

        public static Result Cut(Mesh src, Matrix4x4 localToWorld, IList<Bounds> boxes)
        {
            var res = new Result();
            Vector3[] v = src.vertices;
            Vector3[] n = src.normals; bool hasN = n != null && n.Length == v.Length;
            Vector4[] t = src.tangents; bool hasT = t != null && t.Length == v.Length;
            var uv = new List<Vector2>(); src.GetUVs(0, uv); bool hasUv = uv.Count == v.Length;
            var uv2 = new List<Vector2>(); src.GetUVs(1, uv2); bool hasUv2 = uv2.Count == v.Length;
            Color[] col = src.colors; bool hasC = col != null && col.Length == v.Length;
            var w = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++) w[i] = localToWorld.MultiplyPoint3x4(v[i]);

            var ov = new List<Vector3>(v); var on = hasN ? new List<Vector3>(n) : null; var ot = hasT ? new List<Vector4>(t) : null;
            var ouv = hasUv ? new List<Vector2>(uv) : null; var ouv2 = hasUv2 ? new List<Vector2>(uv2) : null; var oc = hasC ? new List<Color>(col) : null;
            var subs = new List<int>[src.subMeshCount];
            PV Get(int i) => new PV { p = v[i], w = w[i], n = hasN ? n[i] : Vector3.up, t = hasT ? t[i] : Vector4.zero, uv = hasUv ? uv[i] : Vector2.zero, uv2 = hasUv2 ? uv2[i] : Vector2.zero, c = hasC ? col[i] : Color.white };
            int Add(PV p)
            {
                ov.Add(p.p); on?.Add(p.n); ot?.Add(p.t); ouv?.Add(p.uv); ouv2?.Add(p.uv2); oc?.Add(p.c);
                return ov.Count - 1;
            }

            for (int s = 0; s < src.subMeshCount; s++)
            {
                if (src.GetTopology(s) != MeshTopology.Triangles) { subs[s] = new List<int>(src.GetIndices(s)); continue; }
                int[] tri = src.GetTriangles(s);
                var outTri = new List<int>(tri.Length);
                for (int k = 0; k + 2 < tri.Length; k += 3)
                {
                    int a = tri[k], b = tri[k + 1], c = tri[k + 2];
                    var tb = new Bounds(w[a], Vector3.zero); tb.Encapsulate(w[b]); tb.Encapsulate(w[c]);
                    bool touch = false;
                    foreach (Bounds box in boxes) if (Overlap(box, tb)) { touch = true; break; }
                    if (!touch) { outTri.Add(a); outTri.Add(b); outTri.Add(c); res.Kept++; continue; }
                    var pieces = new List<List<PV>> { new List<PV> { Get(a), Get(b), Get(c) } };
                    foreach (Bounds box in boxes)
                    {
                        var next = new List<List<PV>>();
                        foreach (var poly in pieces) Subtract(poly, box, next);
                        pieces = next;
                    }
                    if (pieces.Count == 1 && pieces[0].Count == 3 && Same(pieces[0], w[a], w[b], w[c]))
                    { outTri.Add(a); outTri.Add(b); outTri.Add(c); res.Kept++; continue; }
                    if (pieces.Count == 0) { res.Dropped++; continue; }
                    res.Split++;
                    foreach (var poly in pieces)
                    {
                        int i0 = Add(poly[0]);
                        for (int q = 1; q + 1 < poly.Count; q++)
                        {
                            int i1 = Add(poly[q]), i2 = Add(poly[q + 1]);
                            outTri.Add(i0); outTri.Add(i1); outTri.Add(i2);
                        }
                    }
                }
                subs[s] = outTri;
            }

            var m = new Mesh { name = src.name + "_cut" };
            m.indexFormat = ov.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
            m.SetVertices(ov);
            if (on != null) m.SetNormals(on);
            if (ot != null) m.SetTangents(ot);
            if (ouv != null) m.SetUVs(0, ouv);
            if (ouv2 != null) m.SetUVs(1, ouv2);
            if (oc != null) m.SetColors(oc);
            m.subMeshCount = subs.Length;
            for (int s = 0; s < subs.Length; s++)
            {
                if (src.GetTopology(s) == MeshTopology.Triangles) m.SetTriangles(subs[s], s, false);
                else m.SetIndices(subs[s].ToArray(), src.GetTopology(s), s, false);
            }
            m.RecalculateBounds();
            res.Mesh = m;
            return res;
        }

        static bool Overlap(Bounds box, Bounds tri) =>
            tri.max.x > box.min.x + 1e-5f && tri.min.x < box.max.x - 1e-5f &&
            tri.max.y > box.min.y + 1e-5f && tri.min.y < box.max.y - 1e-5f &&
            tri.max.z > box.min.z + 1e-5f && tri.min.z < box.max.z - 1e-5f;

        static bool Same(List<PV> p, Vector3 a, Vector3 b, Vector3 c) =>
            (p[0].w - a).sqrMagnitude < 1e-10f && (p[1].w - b).sqrMagnitude < 1e-10f && (p[2].w - c).sqrMagnitude < 1e-10f;

        /// <summary>poly minus box: the parts outside go to 'outside' (convex pieces), the part inside is dropped.</summary>
        static void Subtract(List<PV> poly, Bounds box, List<List<PV>> outside)
        {
            var bb = new Bounds(poly[0].w, Vector3.zero);
            foreach (var p in poly) bb.Encapsulate(p.w);
            if (!Overlap(box, bb)) { outside.Add(poly); return; }
            List<PV> cur = poly;
            for (int k = 0; k < 6; k++)
            {
                int axis = k >> 1;
                float sign = (k & 1) == 0 ? 1f : -1f;                      // inside: sign * (x - v) >= 0
                float val = (k & 1) == 0 ? box.min[axis] : box.max[axis];
                Split(cur, axis, val, sign, out List<PV> inPart, out List<PV> outPart);
                if (outPart.Count >= 3 && Area(outPart) > 1e-7f) outside.Add(outPart);
                cur = inPart;
                if (cur.Count < 3 || Area(cur) <= 1e-7f) return;
            }
            // what is left lies inside the box: dropped
        }

        static void Split(List<PV> poly, int axis, float val, float sign, out List<PV> inPart, out List<PV> outPart)
        {
            inPart = new List<PV>(poly.Count + 2); outPart = new List<PV>(poly.Count + 2);
            for (int i = 0; i < poly.Count; i++)
            {
                PV a = poly[i], b = poly[(i + 1) % poly.Count];
                float da = sign * (a.w[axis] - val), db = sign * (b.w[axis] - val);
                if (da >= 0f) inPart.Add(a);
                if (da <= 0f) outPart.Add(a);
                if ((da > 0f && db < 0f) || (da < 0f && db > 0f))
                {
                    PV x = PV.Lerp(a, b, da / (da - db));
                    inPart.Add(x); outPart.Add(x);
                }
            }
        }

        static float Area(List<PV> poly)
        {
            Vector3 s = Vector3.zero;
            for (int i = 1; i + 1 < poly.Count; i++) s += Vector3.Cross(poly[i].w - poly[0].w, poly[i + 1].w - poly[0].w);
            return s.magnitude * .5f;
        }
    }
}
