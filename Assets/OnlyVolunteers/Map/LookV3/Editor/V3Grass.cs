using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // v17 grass tufts (Fedya 2026-10-12: "small, noticeable grass tufts on the grass"; STYLE_OAR_NOTES section 6: low-poly
    // clump and tuft meshes, simple silhouettes, few colour groups, not realistic grass). Four tuft meshes (5-9 tapered
    // blades, 3 triangles each) and one rare flower clump, made here, drawn as instanced terrain detail meshes with the
    // flat style v3 surface material (vertex colours around the v07 grass mean #6F804D, lighter tips, a world-space macro
    // variation between neighbouring tufts; double-sided, up-facing normals so they light like the ground they stand on).
    // Placement = the grass splat weight (meadow 1, worn grass 0.7, park 0.45, lawn 0.3; none on sand, dry field, forest
    // floor) times a soft distance ramp from every hard surface (roads, junctions, sidewalks, plazas, parking, bridges,
    // building shells, water, retaining walls, big v17 props: their triangles are rasterised top-down at 0.5 m) times a
    // 23 m patch noise. Detail distance 75 m. No wind sway (would need a custom shader; the tufts are short and stiff).
    public static class V3Grass
    {
        public const float DetailDistance = 75f;
        public const int DetailRes = 1024, PerPatch = 32;
        // Expected tufts per detail cell (1.25 x 1 m on the 1280 x 1024 m terrain) in an open meadow.
        public const float MeadowDensity = 1.5f;
        private const float Fine = 0.5f, FlowerChance = 0.035f;
        private static readonly Dictionary<string, float> LayerWeight = new()
        {
            ["meadow"] = 1f, ["worn_grass"] = 0.7f, ["park_grass"] = 0.45f, ["lawn"] = 0.3f,
        };

        private struct Spec
        {
            public string Name;
            public int Blades, Seed;
            public float Height;
            public Color Base, Tip;
            public bool Flowers;
        }

        private static Color C(string hex) => ColorUtility.TryParseHtmlString(hex, out Color c) ? c : Color.magenta;

        private static Spec[] Specs => new[]
        {
            new Spec { Name = "Grass_Tuft_A", Blades = 7, Seed = 11, Height = 0.32f, Base = C("#56673A"), Tip = C("#98A85F") },
            new Spec { Name = "Grass_Tuft_B", Blades = 9, Seed = 23, Height = 0.25f, Base = C("#5C6B3C"), Tip = C("#A7AE67") },
            new Spec { Name = "Grass_Tuft_C", Blades = 6, Seed = 37, Height = 0.40f, Base = C("#4F6339"), Tip = C("#8DA65C") },
            new Spec { Name = "Grass_Tuft_D", Blades = 5, Seed = 41, Height = 0.48f, Base = C("#62703F"), Tip = C("#AFB16C") },
            new Spec { Name = "Grass_Flowers", Blades = 5, Seed = 53, Height = 0.30f, Base = C("#56673A"), Tip = C("#9CAA60"), Flowers = true },
        };

        public static void Build(Terrain terrain, float[,,] splat, string[] names, Transform envRoot, V3Store store, List<string> log)
        {
            if (terrain == null || splat == null || names == null) { log.Add("grass: no terrain splat, skipped"); return; }
            var sw = System.Diagnostics.Stopwatch.StartNew();
            TerrainData td = terrain.terrainData;
            Material mat = TuftMaterial();
            Spec[] specs = Specs;
            var protos = new DetailPrototype[specs.Length];
            var tris = new int[specs.Length];
            for (int i = 0; i < specs.Length; i++)
            {
                Mesh mesh = store.AddMesh(TuftMesh(specs[i]));
                tris[i] = (int)mesh.GetIndexCount(0) / 3;
                protos[i] = new DetailPrototype
                {
                    usePrototypeMesh = true,
                    prototype = Prefab(specs[i].Name, mesh, mat, store),
                    renderMode = DetailRenderMode.VertexLit,
                    useInstancing = true,
                    minWidth = 0.8f, maxWidth = 1.25f,
                    minHeight = 0.8f, maxHeight = 1.3f,
                    noiseSpread = 0.35f,
                    noiseSeed = specs[i].Seed,
                    healthyColor = Color.white, dryColor = Color.white,
                    alignToGround = 0.6f,
                    positionJitter = 1f,
                };
            }

            // Hard surfaces, top-down at 0.5 m.
            Vector3 origin = terrain.transform.position, size = td.size;
            int fx = Mathf.CeilToInt(size.x / Fine), fz = Mathf.CeilToInt(size.z / Fine);
            var hard = new bool[fx * fz];
            long rasterTris = 0;
            foreach (MeshFilter mf in HardSurfaces(envRoot))
                rasterTris += Rasterise(mf, terrain, origin, fx, fz, hard);

            // Detail cells: covered if any (0.5 m dilated) fine cell inside is hard.
            int res = DetailRes;
            float cw = size.x / res, ch = size.z / res;
            var dist = new float[res * res];
            const float Far = 50f;
            for (int i = 0; i < dist.Length; i++) dist[i] = Far;
            for (int z = 0; z < fz; z++)
                for (int x = 0; x < fx; x++)
                {
                    if (!hard[z * fx + x]) continue;
                    for (int dz = -1; dz <= 1; dz++)
                        for (int dx = -1; dx <= 1; dx++)
                        {
                            float wx = (x + dx + 0.5f) * Fine, wz = (z + dz + 0.5f) * Fine;
                            int cx = Mathf.FloorToInt(wx / cw), cz = Mathf.FloorToInt(wz / ch);
                            if (cx >= 0 && cz >= 0 && cx < res && cz < res) dist[cz * res + cx] = 0f;
                        }
                }
            Chamfer(dist, res, cw, ch);

            int ares = splat.GetLength(0), layers = splat.GetLength(2);
            var weight = new float[layers];
            int meadow = System.Array.IndexOf(names, "meadow");
            for (int l = 0; l < layers; l++) weight[l] = l < names.Length && LayerWeight.TryGetValue(names[l], out float w) ? w : 0f;
            var maps = new int[specs.Length][,];
            for (int i = 0; i < specs.Length; i++) maps[i] = new int[res, res];
            var counts = new long[specs.Length];
            for (int z = 0; z < res; z++)
                for (int x = 0; x < res; x++)
                {
                    float d = dist[z * res + x];
                    if (d <= 0f) continue;
                    int ax = Mathf.Min(ares - 1, (int)((x + 0.5f) / res * ares)), az = Mathf.Min(ares - 1, (int)((z + 0.5f) / res * ares));
                    float g = 0f;
                    for (int l = 0; l < layers; l++) g += splat[az, ax, l] * weight[l];
                    if (g < 0.05f) continue;
                    float wx = origin.x + (x + 0.5f) * cw, wz = origin.z + (z + 0.5f) * ch;
                    float near = 0.12f + 0.88f * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(1f, 10f, d));
                    float patch = 0.55f + 0.75f * Mathf.PerlinNoise(wx / 23f + 17.3f, wz / 23f + 5.1f);
                    float e = g * near * patch * MeadowDensity;
                    int n = Mathf.FloorToInt(e) + (Hash01(x, z, 1) < e - Mathf.Floor(e) ? 1 : 0);
                    for (int k = 0; k < n; k++)
                    {
                        int p = Mathf.Min(3, (int)(Hash01(x, z, 10 + k) * 4f));
                        maps[p][z, x]++;
                        counts[p]++;
                    }
                    if (meadow >= 0 && splat[az, ax, meadow] > 0.5f && d > 6f && Hash01(x, z, 99) < FlowerChance * patch)
                    {
                        maps[4][z, x]++;
                        counts[4]++;
                    }
                }

            td.SetDetailScatterMode(DetailScatterMode.InstanceCountMode);
            td.SetDetailResolution(res, PerPatch);
            td.detailPrototypes = protos;
            for (int i = 0; i < specs.Length; i++) td.SetDetailLayer(0, 0, i, maps[i]);
            terrain.detailObjectDistance = DetailDistance;
            terrain.detailObjectDensity = 1f;
            terrain.drawTreesAndFoliage = true;
            EditorUtility.SetDirty(td);

            long total = 0;
            foreach (long c in counts) total += c;
            float area = size.x * size.z;
            log.Add($"grass: {specs.Length} detail meshes ({string.Join("/", System.Array.ConvertAll(tris, t => t.ToString()))} tris), {total} tufts " +
                    $"({string.Join(", ", System.Array.ConvertAll(counts, c => c.ToString()))}; {total / area:0.00}/m2 map-wide, up to {MeadowDensity * 1.3f / (cw * ch):0.0}/m2 in open meadow), " +
                    $"detail res {res} ({cw:0.00} x {ch:0.00} m cells), distance {DetailDistance} m; {rasterTris} hard-surface tris rasterised in {sw.Elapsed.TotalSeconds:0.0} s");
        }

        // Roads (with junctions, sidewalks, plazas, parking, bridges), building shells, water, retaining walls, big v17 props.
        private static IEnumerable<MeshFilter> HardSurfaces(Transform envRoot)
        {
            foreach (string group in new[] { "Roads", "Buildings", "Water", "RetainingWalls", "Props_v17" })
            {
                Transform g = envRoot.Find(group);
                if (g == null) continue;
                foreach (MeshFilter mf in g.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (mf.sharedMesh == null) continue;
                    if (group == "Buildings" && mf.name != "Shell") continue;
                    if (group == "Props_v17" && !InBig(mf.transform, g)) continue;
                    yield return mf;
                }
            }
        }

        private static bool InBig(Transform t, Transform stop)
        {
            for (; t != null && t != stop; t = t.parent)
                if (t.name.Contains("_big_")) return true;
            return false;
        }

        // Triangles under the terrain (the sea plane runs below the whole land) are skipped.
        private static long Rasterise(MeshFilter mf, Terrain terrain, Vector3 origin, int fx, int fz, bool[] hard)
        {
            Matrix4x4 m = mf.transform.localToWorldMatrix;
            long count = 0;
            using (Mesh.MeshDataArray arr = Mesh.AcquireReadOnlyMeshData(mf.sharedMesh))
            {
                Mesh.MeshData md = arr[0];
                var verts = new Unity.Collections.NativeArray<Vector3>(md.vertexCount, Unity.Collections.Allocator.Temp);
                md.GetVertices(verts);
                var xz = new Vector2[verts.Length];
                var wy = new float[verts.Length];
                for (int i = 0; i < verts.Length; i++)
                {
                    Vector3 w = m.MultiplyPoint3x4(verts[i]);
                    xz[i] = new Vector2((w.x - origin.x) / Fine, (w.z - origin.z) / Fine);
                    wy[i] = w.y;
                }
                verts.Dispose();
                for (int s = 0; s < md.subMeshCount; s++)
                {
                    SubMeshDescriptor sd = md.GetSubMesh(s);
                    if (sd.topology != MeshTopology.Triangles) continue;
                    var idx = new Unity.Collections.NativeArray<int>(sd.indexCount, Unity.Collections.Allocator.Temp);
                    md.GetIndices(idx, s);
                    for (int t = 0; t + 2 < idx.Length; t += 3)
                    {
                        int a = idx[t], b = idx[t + 1], c = idx[t + 2];
                        Vector2 mid = (xz[a] + xz[b] + xz[c]) / 3f;
                        var centre = new Vector3(origin.x + mid.x * Fine, 0f, origin.z + mid.y * Fine);
                        float ground = terrain.SampleHeight(centre) + origin.y;
                        if (Mathf.Max(wy[a], Mathf.Max(wy[b], wy[c])) < ground - 0.4f) continue;
                        Triangle(xz[a], xz[b], xz[c], fx, fz, hard);
                        count++;
                    }
                    idx.Dispose();
                }
            }
            return count;
        }

        // Cell centres inside the triangle (grid units), either winding.
        private static void Triangle(Vector2 a, Vector2 b, Vector2 c, int fx, int fz, bool[] hard)
        {
            float area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
            if (Mathf.Abs(area) < 1e-6f) return;
            int x0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.x, Mathf.Min(b.x, c.x)))), x1 = Mathf.Min(fx - 1, Mathf.CeilToInt(Mathf.Max(a.x, Mathf.Max(b.x, c.x))));
            int z0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.y, Mathf.Min(b.y, c.y)))), z1 = Mathf.Min(fz - 1, Mathf.CeilToInt(Mathf.Max(a.y, Mathf.Max(b.y, c.y))));
            float sgn = Mathf.Sign(area);
            for (int z = z0; z <= z1; z++)
                for (int x = x0; x <= x1; x++)
                {
                    float px = x + 0.5f, pz = z + 0.5f;
                    float e0 = ((b.x - a.x) * (pz - a.y) - (b.y - a.y) * (px - a.x)) * sgn;
                    float e1 = ((c.x - b.x) * (pz - b.y) - (c.y - b.y) * (px - b.x)) * sgn;
                    float e2 = ((a.x - c.x) * (pz - c.y) - (a.y - c.y) * (px - c.x)) * sgn;
                    if (e0 >= 0f && e1 >= 0f && e2 >= 0f) hard[z * fx + x] = true;
                }
        }

        // Two-pass chamfer distance (metres) from the zero cells, capped by the initial value.
        private static void Chamfer(float[] d, int n, float cw, float ch)
        {
            float diag = Mathf.Sqrt(cw * cw + ch * ch);
            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                {
                    int i = z * n + x;
                    float v = d[i];
                    if (x > 0) v = Mathf.Min(v, d[i - 1] + cw);
                    if (z > 0)
                    {
                        v = Mathf.Min(v, d[i - n] + ch);
                        if (x > 0) v = Mathf.Min(v, d[i - n - 1] + diag);
                        if (x < n - 1) v = Mathf.Min(v, d[i - n + 1] + diag);
                    }
                    d[i] = v;
                }
            for (int z = n - 1; z >= 0; z--)
                for (int x = n - 1; x >= 0; x--)
                {
                    int i = z * n + x;
                    float v = d[i];
                    if (x < n - 1) v = Mathf.Min(v, d[i + 1] + cw);
                    if (z < n - 1)
                    {
                        v = Mathf.Min(v, d[i + n] + ch);
                        if (x < n - 1) v = Mathf.Min(v, d[i + n + 1] + diag);
                        if (x > 0) v = Mathf.Min(v, d[i + n - 1] + diag);
                    }
                    d[i] = v;
                }
        }

        private static float Hash01(int x, int z, int salt)
        {
            unchecked
            {
                uint h = (uint)(x * 73856093) ^ (uint)(z * 19349663) ^ (uint)(salt * 83492791);
                h ^= h >> 13;
                h *= 0x5bd1e995;
                h ^= h >> 15;
                return (h & 0xFFFFFF) / 16777216f;
            }
        }

        // 3 triangles a blade (base quad + tip), radial with outward lean; flowers: 3 stems with a two-diamond head.
        private static Mesh TuftMesh(Spec s)
        {
            var v = new List<Vector3>();
            var n = new List<Vector3>();
            var col = new List<Color32>();
            var uv = new List<Vector2>();
            var tri = new List<int>();
            var rnd = new System.Random(s.Seed);
            float R() => (float)rnd.NextDouble();
            for (int b = 0; b < s.Blades; b++)
            {
                float ang = (b + R() * 0.6f) / s.Blades * Mathf.PI * 2f;
                var outDir = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang));
                Vector3 root = outDir * (0.02f + R() * 0.06f);
                float h = s.Height * (0.65f + R() * 0.45f), lean = 0.15f + R() * 0.3f, w = 0.045f + R() * 0.03f;
                float face = ang + Mathf.PI * 0.5f + (R() - 0.5f) * 0.8f;
                Vector3 side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face)) * (w * 0.5f);
                Vector3 mid = root + outDir * (lean * h * 0.35f) + Vector3.up * (h * 0.55f);
                Vector3 tip = root + outDir * (lean * h) + Vector3.up * h;
                Color tipC = Color.Lerp(s.Tip, s.Tip * 1.08f, R());
                Color midC = Color.Lerp(s.Base, tipC, 0.55f);
                Vector3 bn = Vector3.Cross(side, tip - root).normalized;
                if (bn.y < 0f) bn = -bn;
                Vector3 nn = (Vector3.up * 0.75f + bn * 0.25f).normalized;
                int o = v.Count;
                Add(v, n, col, uv, root - side, nn, s.Base, 0f);
                Add(v, n, col, uv, root + side, nn, s.Base, 0f);
                Add(v, n, col, uv, mid - side * 0.7f, nn, midC, 0.55f);
                Add(v, n, col, uv, mid + side * 0.7f, nn, midC, 0.55f);
                Add(v, n, col, uv, tip, nn, tipC, 1f);
                tri.AddRange(new[] { o, o + 2, o + 1, o + 1, o + 2, o + 3, o + 2, o + 4, o + 3 });
            }
            if (s.Flowers)
            {
                Color[] heads = { C("#ECE8DA"), C("#E3C24B"), C("#ECE8DA") };
                for (int f = 0; f < 3; f++)
                {
                    float ang = f * 2.1f + R() * 0.5f;
                    var outDir = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang));
                    Vector3 root = outDir * (0.03f + R() * 0.05f);
                    float h = s.Height * (1.05f + R() * 0.35f);
                    Vector3 top = root + outDir * 0.05f + Vector3.up * h;
                    var side = new Vector3(-outDir.z, 0f, outDir.x) * 0.012f;
                    int o = v.Count;
                    Add(v, n, col, uv, root - side, Vector3.up, s.Base, 0f);
                    Add(v, n, col, uv, root + side, Vector3.up, s.Base, 0f);
                    Add(v, n, col, uv, top, Vector3.up, s.Tip, 1f);
                    tri.AddRange(new[] { o, o + 2, o + 1 });
                    float r = 0.035f + R() * 0.01f;
                    for (int d = 0; d < 2; d++)
                    {
                        float a0 = ang + d * Mathf.PI * 0.25f;
                        Vector3 ax = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)) * r, az = new Vector3(-ax.z, 0f, ax.x);
                        Vector3 cTop = top + Vector3.up * (0.004f * d);
                        int q = v.Count;
                        Add(v, n, col, uv, cTop + ax, Vector3.up, heads[f], 1f);
                        Add(v, n, col, uv, cTop + az, Vector3.up, heads[f], 1f);
                        Add(v, n, col, uv, cTop - ax, Vector3.up, heads[f], 1f);
                        Add(v, n, col, uv, cTop - az, Vector3.up, heads[f], 1f);
                        tri.AddRange(new[] { q, q + 1, q + 2, q, q + 2, q + 3 });
                    }
                }
            }
            var mesh = new Mesh { name = s.Name };
            mesh.SetVertices(v);
            mesh.SetNormals(n);
            mesh.SetColors(col);
            mesh.SetUVs(0, uv);
            mesh.SetTriangles(tri, 0);
            mesh.RecalculateBounds();
            mesh.RecalculateTangents();
            return mesh;
        }

        private static void Add(List<Vector3> v, List<Vector3> n, List<Color32> c, List<Vector2> uv, Vector3 p, Vector3 normal, Color colour, float t)
        {
            v.Add(p);
            n.Add(normal);
            c.Add(colour);
            uv.Add(new Vector2(0.5f, t));
        }

        private static GameObject Prefab(string name, Mesh mesh, Material mat, V3Store store)
        {
            var go = new GameObject(name);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(go, $"{store.GeneratedDir}/{name}.prefab");
            Object.DestroyImmediate(go);
            return prefab;
        }

        // The flat style v3 surface (white texture, tint reference 1: albedo = vertex colour), double-sided, matte, with a
        // stronger and finer macro variation than the buildings so neighbouring tufts differ a little.
        private static Material TuftMaterial()
        {
            string path = V3Materials.MaterialDir + "/V3S17_grass_tuft.mat";
            Shader shader = Shader.Find("OnlyVolunteers/StyleV3/Surface");
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool created = m == null;
            if (created) m = new Material(shader) { name = "V3S17_grass_tuft" };
            else if (m.shader != shader) m.shader = shader;
            m.SetTexture("_BaseMap", null);
            m.SetColor("_BaseColor", Color.white);
            m.SetVector("_TintRef", Vector4.one);
            m.SetFloat("_Cull", (float)CullMode.Off);
            m.SetFloat("_Smoothness", 0.12f);
            m.SetFloat("_Metallic", 0f);
            m.SetFloat("_MacroStrength", 0.16f);
            m.SetFloat("_MacroScale", 7f);
            m.SetFloat("_UseNormalMap", 0f);
            m.DisableKeyword("_NORMALMAP");
            m.SetFloat("_UseMaskMap", 0f);
            m.DisableKeyword("_V3_MASKMAP");
            m.SetFloat("_SpecularHighlightsOff", 1f);
            m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            m.SetFloat("_EnvironmentReflectionsOff", 1f);
            m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            m.enableInstancing = true;
            LookAssetStore.EnsureFolder(V3Materials.MaterialDir);
            if (created) AssetDatabase.CreateAsset(m, path);
            else EditorUtility.SetDirty(m);
            return m;
        }
    }
}
