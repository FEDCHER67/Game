using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 mesh under construction: one submesh per surface category (V3Materials ids), a palette colour per vertex
    // (relative to the category texture, see V3Materials.Tint), flat-faceted faces whose UV0 is a planar projection in
    // METRES in the face's own frame (u along the face horizontally, v up the face; roofs: u along the eave, v up the
    // slope; floors: x, z), so every tiled texture shows at true scale on any wall angle. Unwelded triangles.
    public sealed class V3Mesh
    {
        public readonly List<Vector3> Vertices = new();
        public readonly List<Vector3> Normals = new();
        public readonly List<Vector2> Uvs = new();
        public readonly List<Color> Colors = new();
        private readonly Dictionary<string, List<int>> triangles = new();
        private readonly List<string> order = new();

        public bool IsEmpty => Vertices.Count == 0;
        public IReadOnlyList<string> Categories => order;

        public int TriangleCount
        {
            get
            {
                int n = 0;
                foreach (List<int> t in triangles.Values) n += t.Count / 3;
                return n;
            }
        }

        public List<int> Indices(string category)
        {
            if (!triangles.TryGetValue(category, out List<int> list))
            {
                triangles[category] = list = new List<int>();
                order.Add(category);
            }
            return list;
        }

        public static Vector2 PlanarUv(Vector3 p, Vector3 n)
        {
            Vector3 u = Vector3.Cross(Vector3.up, n);
            if (u.sqrMagnitude < 1e-4f) return new Vector2(p.x, p.z);
            u.Normalize();
            Vector3 v = Vector3.Cross(n, u).normalized;
            return new Vector2(Vector3.Dot(p, u), Vector3.Dot(p, v));
        }

        // Triangle a-b-c, clockwise seen from the side it faces; flat normal unless normals are given.
        public void Tri(string cat, Vector3 a, Vector3 b, Vector3 c, Color col)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            if (n.sqrMagnitude < 1e-12f) return;
            n.Normalize();
            List<int> t = Indices(cat);
            int i = Vertices.Count;
            Add(a, n, PlanarUv(a, n), col);
            Add(b, n, PlanarUv(b, n), col);
            Add(c, n, PlanarUv(c, n), col);
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
        }

        public void Quad(string cat, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Color col)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            if (n.sqrMagnitude < 1e-12f) n = Vector3.Cross(c - a, d - a);
            if (n.sqrMagnitude < 1e-12f) return;
            n.Normalize();
            List<int> t = Indices(cat);
            int i = Vertices.Count;
            Add(a, n, PlanarUv(a, n), col);
            Add(b, n, PlanarUv(b, n), col);
            Add(c, n, PlanarUv(c, n), col);
            Add(d, n, PlanarUv(d, n), col);
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
            t.Add(i);
            t.Add(i + 2);
            t.Add(i + 3);
        }

        public void QuadFacing(string cat, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 facing, Color col)
        {
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), facing) < 0f) Quad(cat, d, c, b, a, col);
            else Quad(cat, a, b, c, d, col);
        }

        public void TriFacing(string cat, Vector3 a, Vector3 b, Vector3 c, Vector3 facing, Color col)
        {
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), facing) < 0f) Tri(cat, a, c, b, col);
            else Tri(cat, a, b, c, col);
        }

        // Oriented box (centre, full size, rotation); `bottom` adds the underside.
        public void Box(string cat, Vector3 centre, Vector3 size, Quaternion rot, Color col, bool bottom = false)
        {
            Vector3 hx = rot * new Vector3(size.x / 2f, 0f, 0f), hy = rot * new Vector3(0f, size.y / 2f, 0f), hz = rot * new Vector3(0f, 0f, size.z / 2f);
            Vector3 c = centre;
            Vector3 p000 = c - hx - hy - hz, p100 = c + hx - hy - hz, p010 = c - hx + hy - hz, p110 = c + hx + hy - hz;
            Vector3 p001 = c - hx - hy + hz, p101 = c + hx - hy + hz, p011 = c - hx + hy + hz, p111 = c + hx + hy + hz;
            Quad(cat, p000, p010, p110, p100, col);
            Quad(cat, p101, p111, p011, p001, col);
            Quad(cat, p001, p011, p010, p000, col);
            Quad(cat, p100, p110, p111, p101, col);
            Quad(cat, p010, p011, p111, p110, col);
            if (bottom) Quad(cat, p000, p100, p101, p001, col);
        }

        // Box between two plan points (beam, slab edge): width across, from y0 to y1.
        public void Beam(string cat, Vector3 a, Vector3 b, float width, float y0, float y1, Color col, bool bottom = false)
        {
            Vector3 d = b - a;
            d.y = 0f;
            float len = d.magnitude;
            if (len < 1e-4f) return;
            Box(cat, new Vector3((a.x + b.x) / 2f, (y0 + y1) / 2f, (a.z + b.z) / 2f), new Vector3(width, y1 - y0, len), Quaternion.LookRotation(d / len), col, bottom);
        }

        public void Cylinder(string cat, Vector3 baseCentre, float radius, float height, int sides, Color col, bool top = true)
        {
            for (int s = 0; s < sides; s++)
            {
                float a0 = s * Mathf.PI * 2f / sides, a1 = (s + 1) * Mathf.PI * 2f / sides;
                Vector3 d0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)) * radius, d1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1)) * radius;
                Vector3 b0 = baseCentre + d0, b1 = baseCentre + d1, t0 = b0 + Vector3.up * height, t1 = b1 + Vector3.up * height;
                QuadFacing(cat, b0, t0, t1, b1, d0 + d1, col);
                if (top) TriFacing(cat, baseCentre + Vector3.up * height, t0, t1, Vector3.up, col);
            }
        }

        // Plan-CCW triangles (flat x,y list) at height h (local to origin ox, oz), facing up.
        public void PlanTris(string cat, float[] tris, float h, float ox, float oz, Color col)
        {
            for (int i = 0; i + 5 < tris.Length; i += 6)
                TriFacing(cat, new Vector3(tris[i] - ox, h, tris[i + 1] - oz), new Vector3(tris[i + 2] - ox, h, tris[i + 3] - oz),
                    new Vector3(tris[i + 4] - ox, h, tris[i + 5] - oz), Vector3.up, col);
        }

        // A triangle with its own vertex normals (kit modules keep their weighted normals); UV planar by the face normal.
        public void TriSmooth(string cat, Vector3 a, Vector3 b, Vector3 c, Vector3 na, Vector3 nb, Vector3 nc, Color ca, Color cb, Color cc)
        {
            Vector3 n = Vector3.Cross(b - a, c - a);
            if (n.sqrMagnitude < 1e-14f) return;
            n.Normalize();
            List<int> t = Indices(cat);
            int i = Vertices.Count;
            Add(a, na, PlanarUv(a, n), ca);
            Add(b, nb, PlanarUv(b, n), cb);
            Add(c, nc, PlanarUv(c, n), cc);
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
        }

        // A triangle with explicit UVs (road ribbons keep their across/along metres so tiles follow the street).
        public void TriUv(string cat, Vector3 a, Vector3 b, Vector3 c, Vector3 na, Vector3 nb, Vector3 nc, Vector2 ua, Vector2 ub, Vector2 uc, Color col)
        {
            if (Vector3.Cross(b - a, c - a).sqrMagnitude < 1e-14f) return;
            List<int> t = Indices(cat);
            int i = Vertices.Count;
            Add(a, na, ua, col);
            Add(b, nb, ub, col);
            Add(c, nc, uc, col);
            t.Add(i);
            t.Add(i + 1);
            t.Add(i + 2);
        }

        // Another V3Mesh, transformed (its UVs are recomputed in the new frame so textures keep their metre scale).
        public void Append(V3Mesh other, Matrix4x4 m)
        {
            Matrix4x4 nm = m.inverse.transpose;
            foreach (string cat in other.order)
            {
                List<int> src = other.triangles[cat];
                List<int> dst = Indices(cat);
                for (int k = 0; k + 2 < src.Count; k += 3)
                {
                    int i0 = src[k], i1 = src[k + 1], i2 = src[k + 2];
                    Vector3 a = m.MultiplyPoint3x4(other.Vertices[i0]), b = m.MultiplyPoint3x4(other.Vertices[i1]), c = m.MultiplyPoint3x4(other.Vertices[i2]);
                    Vector3 n = Vector3.Cross(b - a, c - a);
                    if (n.sqrMagnitude < 1e-14f) continue;
                    n.Normalize();
                    int i = Vertices.Count;
                    Add(a, nm.MultiplyVector(other.Normals[i0]).normalized, PlanarUv(a, n), other.Colors[i0]);
                    Add(b, nm.MultiplyVector(other.Normals[i1]).normalized, PlanarUv(b, n), other.Colors[i1]);
                    Add(c, nm.MultiplyVector(other.Normals[i2]).normalized, PlanarUv(c, n), other.Colors[i2]);
                    dst.Add(i);
                    dst.Add(i + 1);
                    dst.Add(i + 2);
                }
            }
        }

        // Every category's triangles of `other` moved as they are (already in this frame), keeping UVs.
        public void AppendRaw(V3Mesh other)
        {
            int offset = Vertices.Count;
            Vertices.AddRange(other.Vertices);
            Normals.AddRange(other.Normals);
            Uvs.AddRange(other.Uvs);
            Colors.AddRange(other.Colors);
            foreach (string cat in other.order)
            {
                List<int> dst = Indices(cat);
                foreach (int idx in other.triangles[cat]) dst.Add(idx + offset);
            }
        }

        // Welded on the way out (equal position, normal, UV and colour share one vertex, also across submeshes) with the
        // colour as 8-bit palette sRGB: the V3Surface shader tints the category texture by it relative to _TintRef, so
        // no per-category conversion is baked into the mesh. `tint` is kept for callers (water meshes pass false).
        public Mesh ToMesh(string name, out string[] categories, bool tint = true, bool weld = true)
        {
            categories = order.ToArray();
            var map = new Dictionary<(int, int, int, int, int, int, int, int, uint), int>();
            var pos = new List<Vector3>();
            var nrm = new List<Vector3>();
            var uvs = new List<Vector2>();
            var col = new List<Color32>();
            var remap = new int[Vertices.Count];
            for (int i = 0; i < Vertices.Count; i++)
            {
                Vector3 p = Vertices[i], n = Normals[i];
                Vector2 u = Uvs[i];
                Color32 c = Colors[i];
                var key = (Mathf.RoundToInt(p.x * 2000f), Mathf.RoundToInt(p.y * 2000f), Mathf.RoundToInt(p.z * 2000f),
                    Mathf.RoundToInt(n.x * 500f), Mathf.RoundToInt(n.y * 500f), Mathf.RoundToInt(n.z * 500f),
                    Mathf.RoundToInt(u.x * 1000f), Mathf.RoundToInt(u.y * 1000f), (uint)(c.r | c.g << 8 | c.b << 16));
                if (!weld || !map.TryGetValue(key, out int idx))
                {
                    idx = pos.Count;
                    map[key] = idx;
                    pos.Add(p);
                    nrm.Add(n);
                    uvs.Add(u);
                    col.Add(c);
                }
                remap[i] = idx;
            }
            var mesh = new Mesh { name = name, indexFormat = pos.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            mesh.SetVertices(pos);
            mesh.SetNormals(nrm);
            mesh.SetUVs(0, uvs);
            mesh.SetColors(col);
            mesh.subMeshCount = Mathf.Max(1, order.Count);
            for (int s = 0; s < order.Count; s++)
            {
                List<int> src = triangles[order[s]];
                var dst = new int[src.Count];
                for (int k = 0; k < dst.Length; k++) dst[k] = remap[src[k]];
                mesh.SetTriangles(dst, s, false);
            }
            mesh.RecalculateBounds();
            if (pos.Count > 0) mesh.RecalculateTangents();
            return tint && pos.Count > 0 ? Compact(mesh) : mesh;
        }

        // Unity's static batching cannot take these compact meshes: the combined mesh it builds on entering Play has every
        // SNorm8 normal zeroed, the lighting turns NaN and bloom blows the pixels up into big white blobs (v17 glare bug,
        // 2026-10-12). Only meshes with float normals may be flagged BatchingStatic; the SRP Batcher handles the rest.
        public static bool StaticBatchSafe(Mesh m) =>
            m != null && (!m.HasVertexAttribute(VertexAttribute.Normal) || m.GetVertexAttributeFormat(VertexAttribute.Normal) == VertexAttributeFormat.Float32);

        // 28-32 bytes a vertex instead of 52: position float x3, normal and tangent snorm8 x4, colour unorm8 x4, UV half x2
        // when every UV fits half precision well (building meshes are local, |uv| < 48 m), else float x2 (world-space roads).
        private static Mesh Compact(Mesh src)
        {
            Vector3[] p = src.vertices, n = src.normals;
            Vector4[] t = src.tangents;
            Color32[] c = src.colors32;
            Vector2[] uv = src.uv;
            int count = p.Length;
            bool half = true;
            foreach (Vector2 u in uv)
                if (Mathf.Abs(u.x) > 48f || Mathf.Abs(u.y) > 48f) { half = false; break; }
            int stride = half ? 28 : 32;
            var attrs = new[]
            {
                new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3),
                new VertexAttributeDescriptor(VertexAttribute.Normal, VertexAttributeFormat.SNorm8, 4),
                new VertexAttributeDescriptor(VertexAttribute.Tangent, VertexAttributeFormat.SNorm8, 4),
                new VertexAttributeDescriptor(VertexAttribute.Color, VertexAttributeFormat.UNorm8, 4),
                new VertexAttributeDescriptor(VertexAttribute.TexCoord0, half ? VertexAttributeFormat.Float16 : VertexAttributeFormat.Float32, 2),
            };
            var data = new Unity.Collections.NativeArray<byte>(count * stride, Unity.Collections.Allocator.Temp);
            void F(int o, float v)
            {
                int b = System.BitConverter.SingleToInt32Bits(v);
                data[o] = (byte)b;
                data[o + 1] = (byte)(b >> 8);
                data[o + 2] = (byte)(b >> 16);
                data[o + 3] = (byte)(b >> 24);
            }
            byte S(float v) => (byte)(sbyte)Mathf.RoundToInt(Mathf.Clamp(v, -1f, 1f) * 127f);
            void H(int o, float v)
            {
                ushort h = Mathf.FloatToHalf(v);
                data[o] = (byte)h;
                data[o + 1] = (byte)(h >> 8);
            }
            for (int i = 0; i < count; i++)
            {
                int o = i * stride;
                F(o, p[i].x);
                F(o + 4, p[i].y);
                F(o + 8, p[i].z);
                data[o + 12] = S(n[i].x);
                data[o + 13] = S(n[i].y);
                data[o + 14] = S(n[i].z);
                data[o + 15] = 0;
                Vector4 tg = t != null && t.Length == count ? t[i] : new Vector4(1f, 0f, 0f, 1f);
                data[o + 16] = S(tg.x);
                data[o + 17] = S(tg.y);
                data[o + 18] = S(tg.z);
                data[o + 19] = S(tg.w < 0f ? -1f : 1f);
                data[o + 20] = c[i].r;
                data[o + 21] = c[i].g;
                data[o + 22] = c[i].b;
                data[o + 23] = 255;
                if (half)
                {
                    H(o + 24, uv[i].x);
                    H(o + 26, uv[i].y);
                }
                else
                {
                    F(o + 24, uv[i].x);
                    F(o + 28, uv[i].y);
                }
            }
            var mesh = new Mesh { name = src.name, indexFormat = src.indexFormat };
            mesh.SetVertexBufferParams(count, attrs);
            mesh.SetVertexBufferData(data, 0, 0, data.Length);
            data.Dispose();
            mesh.subMeshCount = src.subMeshCount;
            for (int s = 0; s < src.subMeshCount; s++) mesh.SetTriangles(src.GetTriangles(s), s, false);
            mesh.bounds = src.bounds;
            Object.DestroyImmediate(src);
            // Render-only meshes: no CPU copy in the player (half the memory); colliders use their own readable meshes.
            var so = new UnityEditor.SerializedObject(mesh);
            SerializedProperty readable = so.FindProperty("m_IsReadable");
            if (readable != null)
            {
                readable.boolValue = false;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            return mesh;
        }

        private void Add(Vector3 p, Vector3 n, Vector2 uv, Color c)
        {
            Vertices.Add(p);
            Normals.Add(n);
            Uvs.Add(uv);
            Colors.Add(c);
        }
    }
}
