using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Unity Terrain from the height model: 1025 heightmap over 1280 x 1024 m, 8 soft splat layers (registry layers or
    // generated flat-colour layers from the look bible), trees as TreeInstances of registry prefabs or placeholders.
    public static class TerrainBaker
    {
        // Ground colours of the look bible (meadow, forest floor, dry field, trampled grass, park grass, lawn, gravel, sand).
        internal static readonly Dictionary<string, string> LayerColours = new()
        {
            ["meadow"] = "#7D9A52", ["forest_floor"] = "#6E7A4B", ["dry_field"] = "#A89A72", ["worn_grass"] = "#8A8C5A",
            ["park_grass"] = "#6F9A4C", ["lawn"] = "#78A24E", ["gravel"] = "#9A907A", ["sand"] = "#E6D6A8",
        };

        public static Terrain Build(LookData d, HeightModel hm, MapLookRegistry registry, LookAssetStore store, Transform parent, List<string> log)
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
            float[,,] splat = GroundSplat.Bake(d, splatRes, out string[] layerNames);
            var layers = new TerrainLayer[layerNames.Length];
            for (int l = 0; l < layers.Length; l++)
                layers[l] = registry.Layer("layer/" + layerNames[l]) ?? GeneratedLayer(layerNames[l], registry);
            td.terrainLayers = layers;
            td.alphamapResolution = splatRes;
            td.baseMapResolution = Mathf.Min(1024, splatRes);
            td.SetAlphamaps(0, 0, splat);

            Trees(d, td, registry, store, log);
            store.AddAsset(td, $"Terrain_{store.Revision}.asset");
            lastSplat = splat;

            GameObject go = Terrain.CreateTerrainGameObject(td);
            go.name = "Terrain";
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(t.x0, minH, t.y0);
            var terrain = go.GetComponent<Terrain>();
            terrain.heightmapPixelError = t.pixel_error > 0f ? t.pixel_error : 3f;
            terrain.basemapDistance = 1500f;
            // Tree cost is bounded by the LODGroup on the registry tree prefabs (MapArtSetup.TreeLods: shadows only up
            // close, culled by screen size); treeDistance is the hard cap behind it. No billboards: mesh trees on URP
            // Lit (not Nature/Soft Occlusion) bake black imposters, so the billboard distance stays at the tree distance.
            terrain.treeDistance = 1000f;
            terrain.treeBillboardDistance = 1000f;
            terrain.treeCrossFadeLength = 30f;
            terrain.treeMaximumFullLODCount = 4000;
            terrain.drawInstanced = true;
            Material tm = TerrainMaterial();
            if (tm != null) terrain.materialTemplate = tm;
            DistrictCombiner.MarkStatic(go);
            log.Add($"terrain {t.sx}x{t.sy} m, heights {hm.MinHeight:0.0}..{hm.MaxHeight:0.0} m, splat {splatRes}, {td.treeInstanceCount} trees");
            return terrain;
        }

        private static float[,,] lastSplat;

        // CreateAsset re-creates the splat textures empty (Unity 6000.5) and later asset writes of the build blank them
        // again, so the splat is painted once more after the build has saved its assets, then saved itself. Without
        // this the whole map reads as the first layer (meadow: no beach sand, field or forest floor).
        public static void ReapplySplat(Terrain terrain, List<string> log)
        {
            if (terrain == null || lastSplat == null) return;
            TerrainData td = terrain.terrainData;
            td.SetAlphamaps(0, 0, lastSplat);
            EditorUtility.SetDirty(td);
            foreach (Texture2D tex in td.alphamapTextures) EditorUtility.SetDirty(tex);
            AssetDatabase.SaveAssets();
            log.Add($"splat re-applied after asset save: first layer {SplatShare(td, 0):P0} of the ground");
            lastSplat = null;
        }

        // Mean weight of one splat layer (sampled every 8 texels): a guard against the splat silently going blank.
        internal static float SplatShare(TerrainData td, int layer)
        {
            if (layer >= td.alphamapLayers) return -1f;
            int r = td.alphamapResolution;
            float[,,] a = td.GetAlphamaps(0, 0, r, r);
            double s = 0;
            for (int z = 0; z < r; z += 8)
                for (int x = 0; x < r; x += 8)
                    s += a[z, x, layer];
            return (float)(s / ((r / 8) * (r / 8)));
        }

        private static void Trees(LookData d, TerrainData td, MapLookRegistry registry, LookAssetStore store, List<string> log)
        {
            var index = new Dictionary<string, int>();
            var protos = new List<TreePrototype>();
            var heights = new List<float>();
            foreach (LookTree tree in d.trees)
            {
                string sp = string.IsNullOrEmpty(tree.sp) ? "oak" : tree.sp;
                if (index.ContainsKey(sp)) continue;
                // Second registry variant ("tree/birch_b"): exact key only, mixed in per instance below.
                GameObject variant = registry.ExactPrefabSlot("tree/" + sp + "_b")?.prefab;
                if (variant != null)
                {
                    index[sp + "_b"] = protos.Count;
                    protos.Add(new TreePrototype { prefab = variant, bendFactor = 0f });
                    heights.Add(PrefabHeight(variant));
                }
                GameObject prefab = registry.Prefab("tree/" + sp);
                float h = 1f;
                if (prefab != null) h = PrefabHeight(prefab);
                else
                {
                    MeshDraft draft = PlaceholderKit.Tree(sp, out float trunk);
                    prefab = store.PlaceholderPrefab("tree/" + sp, draft, registry, go =>
                    {
                        if (trunk <= 0f) return;
                        var cap = go.AddComponent<CapsuleCollider>();
                        cap.center = new Vector3(0f, 0.25f, 0f);
                        cap.radius = Mathf.Max(0.012f, trunk);
                        cap.height = 0.5f;
                    });
                }
                index[sp] = protos.Count;
                protos.Add(new TreePrototype { prefab = prefab, bendFactor = 0f });
                heights.Add(Mathf.Max(0.1f, h));
            }
            td.treePrototypes = protos.ToArray();
            var instances = new List<TreeInstance>(d.trees.Length);
            LookTerrain t = d.terrain;
            for (int k = 0; k < d.trees.Length; k++)
            {
                LookTree tree = d.trees[k];
                string sp = string.IsNullOrEmpty(tree.sp) ? "oak" : tree.sp;
                int p = index[sp];
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
            log.Add($"trees: {instances.Count} instances, {protos.Count} species");
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

        // Flat colour plus a little tiled noise, so the ground reads matte and organic until real layers arrive.
        private static TerrainLayer GeneratedLayer(string name, MapLookRegistry registry)
        {
            string dir = LookAssetStore.EnsureFolder(LookAssetStore.SharedDir + "/Layers");
            Color baseColour = LookConvert.Color(LayerColours.TryGetValue(name, out string hex) ? hex : "#7D9A52");
            // A slot colour overrides the look bible only when someone set it (not the LayerSlot field default).
            foreach (LayerSlot slot in registry.Layers)
                if (slot != null && slot.key == "layer/" + name && slot.layer == null && slot.fallback != LayerSlot.DefaultFallback)
                    baseColour = slot.fallback;
            const int size = 64;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, true) { name = $"Look_Layer_{name}", wrapMode = TextureWrapMode.Repeat };
            var px = new Color[size * size];
            int seed = LookGeom.StableHash(name);
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float n = LookGeom.Hash01(x, y, seed) * 0.5f + (LookGeom.Noise(x / 8f, y / 8f, seed) * 0.5f + 0.5f) * 0.5f;
                    px[y * size + x] = LookConvert.Shade(baseColour, 0.9f + n * 0.2f);
                }
            tex.SetPixels(px);
            tex.Apply(true);
            // Overwritten in place, so scenes built earlier keep their references (same GUIDs).
            tex = LookAssetStore.CreateOrReplace(tex, $"{dir}/Look_Layer_{name}_tex.asset");
            var layer = new TerrainLayer { diffuseTexture = tex, tileSize = new Vector2(3f, 3f), name = $"Look_Layer_{name}" };
            if (name == "sand" || name == "gravel") layer.tileSize = new Vector2(2f, 2f);
            return LookAssetStore.CreateOrReplace(layer, $"{dir}/Look_Layer_{name}.terrainlayer");
        }

        private static Material TerrainMaterial()
        {
            string path = LookAssetStore.MaterialDir + "/Look_Terrain.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null) return mat;
            Shader shader = Shader.Find("Universal Render Pipeline/Terrain/Lit");
            if (shader == null) return null;
            mat = new Material(shader) { name = "Look_Terrain" };
            LookAssetStore.EnsureFolder(LookAssetStore.MaterialDir);
            AssetDatabase.CreateAsset(mat, path);
            return mat;
        }
    }
}
