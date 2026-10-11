using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 terrain: the HeightModel heights, the look json's soft ground splat (GroundSplat, unchanged) plus v3 extras
    // (mud on bog and river banks, lawn-green floor under the forest zones, gravel in the canal), and eight v3 terrain
    // layers drawn with the G13 ground textures by surface: grass (meadow / worn / park / lawn tints), mud, dirt, gravel,
    // sand. Trees as TreeInstances of the registry tree prefabs (read only). Writes only under Map/LookV3.
    public static class V3Terrain
    {
        // Tree draw distance: 600 m for v16; the fog end (400 m) for v17 (MapLookBuilderV3 sets it per build).
        public static float TreeDistance = 600f;

        // Look-json layer name -> (category, palette colour, tile metres). Order and names stay the json's.
        private static readonly Dictionary<string, (string cat, string swatch, float tile)> Layers = new()
        {
            ["meadow"] = ("1a_grass", "meadow", 0f),
            ["forest_floor"] = ("1e_mud", "wood", 0f),
            ["dry_field"] = ("1b_dirt_road", "field.dark", 0f),
            ["worn_grass"] = ("1a_grass", "meadow.dark", 5.3f),
            ["park_grass"] = ("1a_grass", "lawn", 3.7f),
            ["lawn"] = ("1a_grass", "lawn.light", 2.6f),
            ["gravel"] = ("1d_gravel", "grey.light", 0f),
            ["sand"] = ("1c_beach_sand", "sand", 0f),
        };

        private static float[,,] lastSplat;

        private static Color V17Ground(string layer, string category)
        {
            Color r = V3Materials.Resolve(category).Reference;
            float k = layer switch { "park_grass" => 0.88f, "lawn" => 0.94f, "worn_grass" => 1.04f, "forest_floor" => 0.85f, _ => 1f };
            return new Color(Mathf.Clamp01(r.r * k), Mathf.Clamp01(r.g * k), Mathf.Clamp01(r.b * k), 1f);
        }

        // Rewrites the terrain layer assets of the current revision (MapLookBuilderV3.Current) from the manifest it uses.
        public static int RefreshLayers()
        {
            int n = 0;
            foreach (var kv in Layers)
            {
                V3Materials.Layer(kv.Key, kv.Value.cat, V3Palette.C(kv.Value.swatch), kv.Value.tile);
                n++;
            }
            return n;
        }

        public static Terrain Build(LookData d, HeightModel hm, MapLookRegistry registry, V3Store store, Transform parent, IEnumerable<float[]> mudPolys,
            IEnumerable<float[]> forestPolys, List<string> log)
        {
            LookTerrain t = d.terrain;
            int res = hm.Grid.Nx;
            float minH = Mathf.Floor(hm.MinHeight) - 1f, maxH = Mathf.Ceil(hm.MaxHeight) + 2f, sizeY = maxH - minH;
            var td = new TerrainData { heightmapResolution = res };
            td.size = new Vector3(t.sx, sizeY, t.sy);
            var heights = new float[res, res];
            for (int j = 0; j < res; j++)
                for (int i = 0; i < res; i++)
                    heights[j, i] = (hm.Heights[j * res + i] - minH) / sizeY;
            td.SetHeights(0, 0, heights);

            int splatRes = Mathf.ClosestPowerOfTwo(Mathf.Max(16, (int)t.splatmap));
            float[,,] splat = GroundSplat.Bake(d, splatRes, out string[] names);
            Extras(d, splat, names, splatRes, mudPolys, forestPolys);
            var layers = new TerrainLayer[names.Length];
            for (int l = 0; l < names.Length; l++)
            {
                (string cat, string swatch, float tile) spec = Layers.TryGetValue(names[l], out var s) ? s : ("1a_grass", "meadow", 0f);
                // v17: the ground shows the (muted) G13 texture colours instead of the bright palette swatches (Fedya: "lime
                // grass"); the grass layers differ by a small brightness step only.
                Color target = MapLookBuilderV3.IsV17(MapLookBuilderV3.Current) ? V17Ground(names[l], spec.cat) : V3Palette.C(spec.swatch);
                layers[l] = V3Materials.Layer(names[l], spec.cat, target, spec.tile);
            }
            td.terrainLayers = layers;
            td.alphamapResolution = splatRes;
            td.baseMapResolution = Mathf.Min(1024, splatRes);
            td.SetAlphamaps(0, 0, splat);
            Trees(d, td, registry, log);
            store.AddAsset(td, $"Terrain_{d.revision}.asset");
            lastSplat = splat;

            GameObject go = Terrain.CreateTerrainGameObject(td);
            go.name = "Terrain";
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(t.x0, minH, t.y0);
            var terrain = go.GetComponent<Terrain>();
            terrain.heightmapPixelError = t.pixel_error > 0f ? t.pixel_error : 3f;
            terrain.basemapDistance = 220f;
            // Trees were the biggest triangle cost in the v12 profile and in the first v16 run (1.1 M of 2.2 M at the
            // Downtown square): half the LOD bias for trees, none past 600 m (the fog is ~80 % there).
            terrain.treeDistance = TreeDistance;
            terrain.treeBillboardDistance = TreeDistance;
            terrain.treeLODBiasMultiplier = 0.5f;
            terrain.treeCrossFadeLength = 30f;
            terrain.treeMaximumFullLODCount = 4000;
            terrain.drawInstanced = true;
            terrain.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.TwoSided;
            Material tm = TerrainMaterial();
            if (tm != null) terrain.materialTemplate = tm;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.ReflectionProbeStatic);
            log.Add($"terrain {t.sx}x{t.sy} m, heights {hm.MinHeight:0.0}..{hm.MaxHeight:0.0} m, splat {splatRes} ({string.Join(", ", names)}), {td.treeInstanceCount} trees");
            return terrain;
        }

        // Unity re-creates the splat textures empty on CreateAsset and blanks them on later asset writes of the build
        // (TerrainBaker.ReapplySplat): paint once more after the build saved its assets.
        public static void ReapplySplat(Terrain terrain, List<string> log)
        {
            if (terrain == null || lastSplat == null) return;
            TerrainData td = terrain.terrainData;
            td.SetAlphamaps(0, 0, lastSplat);
            EditorUtility.SetDirty(td);
            foreach (Texture2D tex in td.alphamapTextures) EditorUtility.SetDirty(tex);
            AssetDatabase.SaveAssets();
            log.Add($"splat re-applied after the asset save: first layer {TerrainBaker.SplatShare(td, 0):P0} of the ground");
            lastSplat = null;
        }

        private static void Extras(LookData d, float[,,] w, string[] names, int res, IEnumerable<float[]> mudPolys, IEnumerable<float[]> forestPolys)
        {
            LookTerrain t = d.terrain;
            var grid = new LookGrid(res, res, t.x0 + t.sx / res * 0.5f, t.y0 + t.sy / res * 0.5f, t.sx / res, t.sy / res);
            int mud = Array.IndexOf(names, "forest_floor"), park = Array.IndexOf(names, "park_grass"), sand = Array.IndexOf(names, "sand");
            int seed = d.seed * 13 + 5;
            if (park >= 0 && forestPolys != null)
                foreach (float[] poly in forestPolys) Paint(grid, w, park, poly, 10f, 0.85f, seed + 1);
            if (mud >= 0 && mudPolys != null)
                foreach (float[] poly in mudPolys) Paint(grid, w, mud, poly, 4f, 1f, seed + 2);
            // The beach sand stays where GroundSplat painted it (sea and beach polygons).
            _ = sand;
        }

        // Blurred polygon mask with a noisy edge, blended over what is below (weight up to `strength`).
        private static void Paint(LookGrid grid, float[,,] w, int layer, float[] poly, float edge, float strength, int seed)
        {
            if (layer < 0 || LookGeom.Count(poly) < 3) return;
            float pad = edge + 2f;
            LookGeom.Bounds(poly, out float bx0, out float by0, out float bx1, out float by1);
            grid.Range(bx0 - pad, by0 - pad, bx1 + pad, by1 + pad, out int i0, out int j0, out int i1, out int j1);
            if (i1 < i0 || j1 < j0) return;
            int nx = i1 - i0 + 1, ny = j1 - j0 + 1;
            var mask = new float[nx * ny];
            var local = new LookGrid(nx, ny, grid.X(i0), grid.Y(j0), grid.Dx, grid.Dy);
            local.ScanFill(poly, (i, j) => mask[j * nx + i] = 1f);
            int rx = (int)(edge * 0.5f / grid.Dx), ry = (int)(edge * 0.5f / grid.Dy);
            if (rx > 0 || ry > 0) LookGrid.Blur(mask, nx, ny, rx, ry, 2);
            int nl = w.GetLength(2);
            for (int j = 0; j < ny; j++)
                for (int i = 0; i < nx; i++)
                {
                    float m = mask[j * nx + i];
                    if (m <= 0.001f) continue;
                    if (m < 0.999f)
                    {
                        float n = LookGeom.Fbm(local.X(i) / Mathf.Max(6f, edge), local.Y(j) / Mathf.Max(6f, edge), seed + layer * 97, 2);
                        m = LookGeom.Smooth01((m - 0.5f) * 1.6f + 0.5f + n * 0.35f);
                    }
                    m *= strength;
                    if (m <= 0.001f) continue;
                    int z = j0 + j, x = i0 + i;
                    float keep = 1f - m;
                    for (int l = 0; l < nl; l++) w[z, x, l] *= keep;
                    w[z, x, layer] += m;
                }
        }

        private static void Trees(LookData d, TerrainData td, MapLookRegistry registry, List<string> log)
        {
            var index = new Dictionary<string, int>();
            var protos = new List<TreePrototype>();
            var heights = new List<float>();
            foreach (LookTree tree in d.trees)
            {
                string sp = string.IsNullOrEmpty(tree.sp) ? "oak" : tree.sp;
                if (index.ContainsKey(sp)) continue;
                GameObject variant = registry.ExactPrefabSlot("tree/" + sp + "_b")?.prefab;
                if (variant != null)
                {
                    index[sp + "_b"] = protos.Count;
                    protos.Add(new TreePrototype { prefab = variant, bendFactor = 0f });
                    heights.Add(PrefabHeight(variant));
                }
                GameObject prefab = registry.Prefab("tree/" + sp);
                if (prefab == null)
                {
                    log.Add($"WARNING tree/{sp}: no registry prefab, species skipped (v3 writes no shared placeholders)");
                    index[sp] = -1;
                    continue;
                }
                index[sp] = protos.Count;
                protos.Add(new TreePrototype { prefab = prefab, bendFactor = 0f });
                heights.Add(Mathf.Max(0.1f, PrefabHeight(prefab)));
            }
            td.treePrototypes = protos.ToArray();
            var instances = new List<TreeInstance>(d.trees.Length);
            LookTerrain t = d.terrain;
            for (int k = 0; k < d.trees.Length; k++)
            {
                LookTree tree = d.trees[k];
                string sp = string.IsNullOrEmpty(tree.sp) ? "oak" : tree.sp;
                int p = index[sp];
                if (p < 0) continue;
                if (index.TryGetValue(sp + "_b", out int pb) && LookGeom.Hash01(k, 61, d.seed) < 0.45f) p = pb;
                float u = (tree.x - t.x0) / t.sx, v = (tree.y - t.y0) / t.sy;
                if (u < 0f || u > 1f || v < 0f || v > 1f) continue;
                float jitter = LookGeom.Hash01(k, 7, d.seed);
                float hs = Mathf.Max(0.5f, tree.h) / heights[p];
                byte tint = (byte)(225 + jitter * 30f);
                instances.Add(new TreeInstance
                {
                    position = new Vector3(u, 0f, v),
                    prototypeIndex = p,
                    heightScale = hs,
                    widthScale = hs * (0.85f + LookGeom.Hash01(k, 13, d.seed) * 0.3f),
                    rotation = LookGeom.Hash01(k, 29, d.seed) * Mathf.PI * 2f,
                    color = new Color32(tint, tint, tint, 255),
                    lightmapColor = new Color32(255, 255, 255, 255),
                });
            }
            td.SetTreeInstances(instances.ToArray(), true);
            log.Add($"trees: {instances.Count} instances, {protos.Count} prototypes");
        }

        private static float PrefabHeight(GameObject prefab)
        {
            float top = 0f, bottom = 0f;
            bool any = false;
            foreach (MeshFilter mf in prefab.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                Bounds b = mf.sharedMesh.bounds;
                float s = mf.transform.lossyScale.y;
                float y0 = mf.transform.position.y + b.min.y * s, y1 = mf.transform.position.y + b.max.y * s;
                top = any ? Mathf.Max(top, y1) : y1;
                bottom = any ? Mathf.Min(bottom, y0) : y0;
                any = true;
            }
            return any ? Mathf.Max(0.1f, top - Mathf.Min(0f, bottom)) : 1f;
        }

        private static Material TerrainMaterial()
        {
            string path = V3Materials.MaterialDir + "/V3_Terrain.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null) return mat;
            Shader shader = Shader.Find("Universal Render Pipeline/Terrain/Lit");
            if (shader == null) return null;
            mat = new Material(shader) { name = "V3_Terrain" };
            LookAssetStore.EnsureFolder(V3Materials.MaterialDir);
            AssetDatabase.CreateAsset(mat, path);
            return mat;
        }
    }
}
