using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look
{
    // Mesh under construction, one submesh per material slot ("mat/key|#RRGGBB", resolved by MapLookRegistry).
    // Faceted on purpose: every face gets its own vertices and a flat normal; UVs are box-mapped in metres so tiled
    // detail textures (brick, panel seams, plaster) line up on any face once the registry supplies them.
    public sealed class MeshDraft
    {
        public readonly List<Vector3> Vertices = new();
        public readonly List<Vector3> Normals = new();
        public readonly List<Vector2> Uvs = new();
        private readonly List<List<int>> triangles = new();
        private readonly List<string> slots = new();
        private readonly Dictionary<string, int> slotIndex = new();

        public IReadOnlyList<string> Slots => slots;
        public bool IsEmpty => Vertices.Count == 0;

        public int TriangleCount
        {
            get
            {
                int n = 0;
                foreach (List<int> t in triangles) n += t.Count / 3;
                return n;
            }
        }

        public static string Key(string material, string hex) => string.IsNullOrEmpty(hex) ? material : material + "|" + hex.ToUpperInvariant();

        public int Slot(string key)
        {
            if (slotIndex.TryGetValue(key, out int i)) return i;
            i = slots.Count;
            slots.Add(key);
            slotIndex[key] = i;
            triangles.Add(new List<int>());
            return i;
        }

        public int Slot(string material, string hex) => Slot(Key(material, hex));

        public List<int> Indices(int slot) => triangles[slot];

        // Triangle a-b-c, clockwise seen from the side it faces (Unity's front face).
        public void Tri(int slot, Vector3 a, Vector3 b, Vector3 c)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            if (n.sqrMagnitude < 1e-12f) return;
            n.Normalize();
            int i = Vertices.Count;
            Add(a, n);
            Add(b, n);
            Add(c, n);
            List<int> t = triangles[slot];
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
        }

        // Quad a-b-c-d, clockwise seen from the side it faces.
        public void Quad(int slot, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            if (n.sqrMagnitude < 1e-12f) n = Vector3.Cross(c - a, d - a);
            if (n.sqrMagnitude < 1e-12f) return;
            n.Normalize();
            int i = Vertices.Count;
            Add(a, n);
            Add(b, n);
            Add(c, n);
            Add(d, n);
            List<int> t = triangles[slot];
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
            t.Add(i);
            t.Add(i + 2);
            t.Add(i + 3);
        }

        // Same quad, turned so it faces `facing` whatever order the corners came in.
        public void QuadFacing(int slot, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 facing)
        {
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), facing) < 0f) Quad(slot, d, c, b, a);
            else Quad(slot, a, b, c, d);
        }

        public void TriFacing(int slot, Vector3 a, Vector3 b, Vector3 c, Vector3 facing)
        {
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), facing) < 0f) Tri(slot, a, c, b);
            else Tri(slot, a, b, c);
        }

        public void QuadBoth(int slot, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
        {
            Quad(slot, a, b, c, d);
            Quad(slot, d, c, b, a);
        }

        // Vertical wall quad standing on the segment a->b (outward normal on the right of a->b, plan CCW footprints).
        public void Wall(int slot, Vector3 a, Vector3 b, float y0, float y1)
        {
            if (y1 - y0 < 1e-4f) return;
            Quad(slot, new Vector3(a.x, y0, a.z), new Vector3(a.x, y1, a.z), new Vector3(b.x, y1, b.z), new Vector3(b.x, y0, b.z));
        }

        // Oriented box: centre, size (x, y, z) and yaw; `bottom` adds the bottom face.
        public void Box(int slot, Vector3 centre, Vector3 size, Quaternion rot, bool bottom = false)
        {
            Vector3 hx = rot * new Vector3(size.x / 2f, 0f, 0f), hy = new Vector3(0f, size.y / 2f, 0f), hz = rot * new Vector3(0f, 0f, size.z / 2f);
            hy = rot * hy;
            Vector3 c = centre;
            Vector3 p000 = c - hx - hy - hz, p100 = c + hx - hy - hz, p010 = c - hx + hy - hz, p110 = c + hx + hy - hz;
            Vector3 p001 = c - hx - hy + hz, p101 = c + hx - hy + hz, p011 = c - hx + hy + hz, p111 = c + hx + hy + hz;
            Quad(slot, p000, p010, p110, p100);
            Quad(slot, p101, p111, p011, p001);
            Quad(slot, p001, p011, p010, p000);
            Quad(slot, p100, p110, p111, p101);
            Quad(slot, p010, p011, p111, p110);
            if (bottom) Quad(slot, p000, p100, p101, p001);
        }

        // Box between two points on the ground plan (a beam, a rail, a fence plank): width across, height up from y0.
        public void Beam(int slot, Vector3 a, Vector3 b, float width, float y0, float y1, bool bottom = false)
        {
            Vector3 d = b - a;
            d.y = 0f;
            float len = d.magnitude;
            if (len < 1e-4f) return;
            Quaternion rot = Quaternion.LookRotation(d / len, Vector3.up);
            Vector3 mid = (a + b) / 2f;
            Box(slot, new Vector3(mid.x, (y0 + y1) / 2f, mid.z), new Vector3(width, y1 - y0, len), rot, bottom);
        }

        // Straight prism over a plan-CCW footprint (x, z pairs), from y0 to y1, with optional top and bottom caps.
        public void Prism(int slot, Vector2[] poly, float y0, float y1, bool top, bool bottom, int topSlot = -1)
        {
            int n = poly.Length;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = poly[i], b = poly[(i + 1) % n];
                Wall(slot, new Vector3(a.x, 0f, a.y), new Vector3(b.x, 0f, b.y), y0, y1);
            }
            if (top) Cap(topSlot >= 0 ? topSlot : slot, poly, y1, true);
            if (bottom) Cap(slot, poly, y0, false);
        }

        // Fan/ear-clipped polygon cap facing up (or down).
        public void Cap(int slot, Vector2[] poly, float y, bool up)
        {
            List<int> tris = Triangulate(poly);
            for (int i = 0; i + 2 < tris.Count; i += 3)
            {
                Vector2 a = poly[tris[i]], b = poly[tris[i + 1]], c = poly[tris[i + 2]];
                TriFacing(slot, new Vector3(a.x, y, a.y), new Vector3(b.x, y, b.y), new Vector3(c.x, y, c.y), up ? Vector3.up : Vector3.down);
            }
        }

        // Plan-CCW triangles from the look json (flat x,y list), lifted to height y (or by a height function) and
        // turned to face up.
        public void PlanTris(int slot, float[] tris, Func<float, float, float> height, float lift, float ox = 0f, float oz = 0f)
        {
            for (int i = 0; i + 5 < tris.Length; i += 6)
            {
                var a = new Vector3(tris[i] - ox, 0f, tris[i + 1] - oz);
                var b = new Vector3(tris[i + 2] - ox, 0f, tris[i + 3] - oz);
                var c = new Vector3(tris[i + 4] - ox, 0f, tris[i + 5] - oz);
                a.y = height(tris[i], tris[i + 1]) + lift;
                b.y = height(tris[i + 2], tris[i + 3]) + lift;
                c.y = height(tris[i + 4], tris[i + 5]) + lift;
                TriFacing(slot, a, b, c, Vector3.up);
            }
        }

        // Surface of revolution around the vertical axis at `centre`: radii[i] at heights[i]; a zero radius closes it.
        public void Lathe(int slot, Vector3 centre, float[] radii, float[] heights, int sides, float phase = 0f)
        {
            for (int k = 0; k + 1 < radii.Length; k++)
                for (int s = 0; s < sides; s++)
                {
                    float a0 = phase + s * Mathf.PI * 2f / sides, a1 = phase + (s + 1) * Mathf.PI * 2f / sides;
                    Vector3 d0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)), d1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1));
                    Vector3 p00 = centre + d0 * radii[k] + Vector3.up * heights[k];
                    Vector3 p01 = centre + d1 * radii[k] + Vector3.up * heights[k];
                    Vector3 p10 = centre + d0 * radii[k + 1] + Vector3.up * heights[k + 1];
                    Vector3 p11 = centre + d1 * radii[k + 1] + Vector3.up * heights[k + 1];
                    Vector3 outward = (d0 + d1).normalized;
                    Vector3 slope = Vector3.up * (radii[k] - radii[k + 1]) + outward * Mathf.Max(0.0001f, heights[k + 1] - heights[k]);
                    if (radii[k] < 1e-4f) TriFacing(slot, p00, p10, p11, slope);
                    else if (radii[k + 1] < 1e-4f) TriFacing(slot, p00, p10, p01, slope);
                    else QuadFacing(slot, p00, p10, p11, p01, slope);
                }
        }

        public void Cylinder(int slot, Vector3 baseCentre, float radius, float height, int sides, bool top = true)
        {
            Lathe(slot, baseCentre, new[] { radius, radius }, new[] { 0f, height }, sides);
            if (!top) return;
            var poly = new Vector2[sides];
            for (int s = 0; s < sides; s++)
            {
                float a = s * Mathf.PI * 2f / sides;
                poly[s] = new Vector2(baseCentre.x + Mathf.Cos(a) * radius, baseCentre.z + Mathf.Sin(a) * radius);
            }
            Cap(slot, poly, baseCentre.y + height, true);
        }

        // Ribbon of shared vertices: rows[i] is one cross-section (left to right looking along the ribbon).
        // Normals are smoothed along and across; UV u = metres across, v = metres along.
        public void Ribbon(int slot, List<Vector3[]> rows, bool doubleSided = false)
        {
            if (rows.Count < 2) return;
            int cols = rows[0].Length;
            int start = Vertices.Count;
            float along = 0f;
            for (int r = 0; r < rows.Count; r++)
            {
                if (r > 0) along += Vector3.Distance(Mid(rows[r]), Mid(rows[r - 1]));
                float across = 0f;
                for (int c = 0; c < cols; c++)
                {
                    if (c > 0) across += Vector3.Distance(rows[r][c], rows[r][c - 1]);
                    Vector3 fwd = rows[Mathf.Min(rows.Count - 1, r + 1)][c] - rows[Mathf.Max(0, r - 1)][c];
                    Vector3 side = rows[r][Mathf.Min(cols - 1, c + 1)] - rows[r][Mathf.Max(0, c - 1)];
                    Vector3 n = Vector3.Cross(fwd, side);
                    if (n.y < 0f) n = -n;
                    Vertices.Add(rows[r][c]);
                    Normals.Add(n.sqrMagnitude > 1e-10f ? n.normalized : Vector3.up);
                    Uvs.Add(new Vector2(across, along));
                }
            }
            List<int> t = triangles[slot];
            for (int r = 0; r + 1 < rows.Count; r++)
                for (int c = 0; c + 1 < cols; c++)
                {
                    int i00 = start + r * cols + c, i01 = i00 + 1, i10 = i00 + cols, i11 = i10 + 1;
                    Vector3 a = Vertices[i00], b = Vertices[i10], d = Vertices[i01];
                    bool up = Vector3.Cross(b - a, d - a).y >= 0f;
                    if (up)
                    {
                        t.Add(i00); t.Add(i10); t.Add(i11);
                        t.Add(i00); t.Add(i11); t.Add(i01);
                    }
                    else
                    {
                        t.Add(i00); t.Add(i11); t.Add(i10);
                        t.Add(i00); t.Add(i01); t.Add(i11);
                    }
                    if (doubleSided)
                    {
                        t.Add(i00); t.Add(i11); t.Add(i10);
                        t.Add(i00); t.Add(i01); t.Add(i11);
                    }
                }
        }

        public void Append(MeshDraft other, Matrix4x4 m)
        {
            Matrix4x4 nm = m.inverse.transpose;
            int offset = Vertices.Count;
            for (int i = 0; i < other.Vertices.Count; i++)
            {
                Vertices.Add(m.MultiplyPoint3x4(other.Vertices[i]));
                Normals.Add(nm.MultiplyVector(other.Normals[i]).normalized);
                Uvs.Add(other.Uvs[i]);
            }
            for (int s = 0; s < other.slots.Count; s++)
            {
                if (other.triangles[s].Count == 0) continue;
                List<int> dst = triangles[Slot(other.slots[s])];
                foreach (int idx in other.triangles[s]) dst.Add(idx + offset);
            }
        }

        // Only the triangles of one slot (used to split a draft by material).
        public void AppendSlot(MeshDraft other, int otherSlot, Matrix4x4 m, string asKey)
        {
            Matrix4x4 nm = m.inverse.transpose;
            List<int> dst = triangles[Slot(asKey)];
            var remap = new Dictionary<int, int>();
            foreach (int idx in other.triangles[otherSlot])
            {
                if (!remap.TryGetValue(idx, out int ni))
                {
                    ni = Vertices.Count;
                    Vertices.Add(m.MultiplyPoint3x4(other.Vertices[idx]));
                    Normals.Add(nm.MultiplyVector(other.Normals[idx]).normalized);
                    Uvs.Add(other.Uvs[idx]);
                    remap[idx] = ni;
                }
                dst.Add(ni);
            }
        }

        public Mesh ToMesh(string name)
        {
            var mesh = new Mesh { name = name, indexFormat = Vertices.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            mesh.SetVertices(Vertices);
            mesh.SetNormals(Normals);
            mesh.SetUVs(0, Uvs);
            mesh.subMeshCount = Mathf.Max(1, triangles.Count);
            for (int s = 0; s < triangles.Count; s++) mesh.SetTriangles(triangles[s], s, false);
            mesh.RecalculateBounds();
            // Tangents for normal-mapped registry materials (URP Lit _NORMALMAP); UVs are box-projected above.
            if (Vertices.Count > 0) mesh.RecalculateTangents();
            return mesh;
        }

        private void Add(Vector3 p, Vector3 n)
        {
            Vertices.Add(p);
            Normals.Add(n);
            Uvs.Add(BoxUv(p, n));
        }

        private static Vector2 BoxUv(Vector3 p, Vector3 n)
        {
            float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
            if (ay >= ax && ay >= az) return new Vector2(p.x, p.z);
            return ax > az ? new Vector2(p.z, p.y) : new Vector2(p.x, p.y);
        }

        private static Vector3 Mid(Vector3[] row) => (row[0] + row[row.Length - 1]) / 2f;

        // Ear clipping for a CCW (x, z) polygon; a fan is the fallback when clipping gets stuck.
        public static List<int> Triangulate(Vector2[] poly)
        {
            var result = new List<int>();
            int n = poly.Length;
            if (n < 3) return result;
            var idx = new List<int>(n);
            float area = 0f;
            for (int i = 0, j = n - 1; i < n; j = i++) area += poly[j].x * poly[i].y - poly[i].x * poly[j].y;
            for (int i = 0; i < n; i++) idx.Add(area >= 0f ? i : n - 1 - i);
            int guard = 0;
            while (idx.Count > 3 && guard++ < n * n)
            {
                bool clipped = false;
                for (int k = 0; k < idx.Count; k++)
                {
                    int ia = idx[(k + idx.Count - 1) % idx.Count], ib = idx[k], ic = idx[(k + 1) % idx.Count];
                    Vector2 a = poly[ia], b = poly[ib], c = poly[ic];
                    if ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) <= 1e-7f) continue;
                    bool inside = false;
                    foreach (int o in idx)
                    {
                        if (o == ia || o == ib || o == ic) continue;
                        if (InTri(poly[o], a, b, c)) { inside = true; break; }
                    }
                    if (inside) continue;
                    result.Add(ia);
                    result.Add(ib);
                    result.Add(ic);
                    idx.RemoveAt(k);
                    clipped = true;
                    break;
                }
                if (!clipped) break;
            }
            if (idx.Count == 3)
            {
                result.Add(idx[0]);
                result.Add(idx[1]);
                result.Add(idx[2]);
            }
            else if (idx.Count > 3)
            {
                for (int k = 1; k + 1 < idx.Count; k++)
                {
                    result.Add(idx[0]);
                    result.Add(idx[k]);
                    result.Add(idx[k + 1]);
                }
            }
            return result;
        }

        private static bool InTri(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d1 = (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y);
            float d2 = (p.x - c.x) * (b.y - c.y) - (b.x - c.x) * (p.y - c.y);
            float d3 = (p.x - a.x) * (c.y - a.y) - (c.x - a.x) * (p.y - a.y);
            bool neg = d1 < 0f || d2 < 0f || d3 < 0f, pos = d1 > 0f || d2 > 0f || d3 > 0f;
            return !(neg && pos);
        }
    }

    // Small conversions between the json's flat arrays / hex colours and Unity types.
    public static class LookConvert
    {
        public static Color Color(string hex, float alpha = 1f)
        {
            LookGeom.Hex(hex, out float r, out float g, out float b);
            return new Color(r, g, b, alpha);
        }

        public static string Hex(Color c) => "#" + ColorUtility.ToHtmlStringRGB(c);

        public static Color Shade(Color c, float k) => new Color(Mathf.Clamp01(c.r * k), Mathf.Clamp01(c.g * k), Mathf.Clamp01(c.b * k), c.a);

        public static string ShadeHex(string hex, float k) => Hex(Shade(Color(hex), k));

        public static Vector2[] Poly(float[] pts, float ox = 0f, float oz = 0f)
        {
            int n = LookGeom.Count(pts);
            var p = new Vector2[n];
            for (int i = 0; i < n; i++) p[i] = new Vector2(pts[2 * i] - ox, pts[2 * i + 1] - oz);
            return p;
        }

        public static Quaternion Yaw(float deg) => Quaternion.Euler(0f, deg, 0f);

        // Plan direction (x, y) -> Unity yaw in degrees.
        public static float YawOf(float dx, float dy) => Mathf.Atan2(dx, dy) * Mathf.Rad2Deg;
    }
}
