using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    // Checkpoint P: a palette-only branch of the saved style-v3 v18 scene. No layout builder or bakes run here.
    public static class V19PaletteTest
    {
        public const string SourceScene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v18_Play.unity";
        public const string Root = "Assets/OnlyVolunteers/Map/LookV3/Palette19";
        public const string Poses = "palette_poses_v01.json";
        private static string output;
        private static Texture2D field;
        private static Vector4 world;
        private static readonly Dictionary<string, Material> materials = new();

        private static Color C(string hex) => LookConvert.Color(hex);
        private static DistrictAtmosphere19.District D(string id, Vector4 bounds, float t, string mood,
            float exposure, float saturation, float contrast, float temperature, float start, float end, string fog) => new()
        {
            id = id, bounds = bounds, palette = t, mood = mood, exposure = exposure,
            saturation = saturation, contrast = contrast, temperature = temperature,
            fogStart = start, fogEnd = end, fogColour = C(fog)
        };

        public static DistrictAtmosphere19.District[] Districts() => new[]
        {
            D("forest", new(127.4f,81,346,315.2f), .50f, "dark, mysterious forest haze", .22f,-7,-12,-3,22,245,"#ABB7B5"),
            D("village", new(132.6f,373.6f,374,599.8f), .80f, "brightest, clean sunny village", .70f,6,3,4,95,520,"#C3D4DC"),
            D("transition", new(424.8f,321.6f,568,479.6f), .60f, "neutral daylight, light dust", .43f,0,0,2,55,370,"#BDB9AE"),
            D("residential", new(550,554,824.8f,696.4f), .50f, "darkest, subdued soft haze", .22f,-7,-12,-3,22,245,"#B6C0C3"),
            D("old_town", new(646,250,1090,478), .60f, "colourful lively sunshine", .55f,10,5,3,90,480,"#C1D0D9"),
            D("industrial", new(938,528,1118,648), .55f, "cooler subdued sea mist", .32f,-4,-5,-6,40,310,"#B2BEC6"),
            D("elite", new(1160,228,1382,408), .75f, "clean sunny gardens", .64f,5,3,3,90,490,"#C3D1D9"),
            D("fields", new(430,128,545.6f,292), .75f, "bright pastoral sunshine", .64f,4,2,5,90,490,"#C8D3D6"),
            D("beach", new(739.4f,71.6f,991.4f,216), .75f, "warm high sun, lifted exposure", .68f,4,2,7,95,510,"#CED9DA"),
            D("tramduro", new(1204,506,1410,670), .60f, "neutral muted daylight, sea haze", .43f,-2,-2,0,60,385,"#B8C6CE")
        };

        public static string Capture(string label)
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Capture edit-mode poses only.");
            var poses = V19PilotTools.LoadPoses(Poses);
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            int count = 0;
            foreach (var p in poses)
            {
                string file = Path.Combine(V19PilotTools.OutDir, label + p.Name + ".png");
                if (File.Exists(file)) throw new IOException("Capture exists: " + file);
                float y = float.IsNaN(p.SurfaceY) ? sampler.Height(p.X, p.Z) + p.Above : p.SurfaceY;
                V19PilotTools.Render(file, new Vector3(p.X, y + V19PilotTools.WalkEye, p.Z),
                    Quaternion.Euler(p.Pitch, p.Yaw, 0), p.Fov > 0 ? p.Fov : 75,
                    V3Lighting.FarClipV17, 1920, 1080, false, 0, true);
                count++;
            }
            return count + " matching-pose captures: " + label;
        }

        public static string Build(int revision = 1)
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play mode before building.");
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (scene.path != SourceScene || scene.isDirty) throw new InvalidOperationException("Open the saved v18 style-v3 source without pending scene edits.");
            string version = "v" + revision.ToString("00");
            output = Root + "/Test_" + version;
            string destination = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_" + version + ".unity";
            if (Directory.Exists(output) || File.Exists(destination)) throw new IOException("Choose a fresh numbered palette revision.");
            LookAssetStore.EnsureFolder(output);
            LookAssetStore.EnsureFolder(output + "/Materials");
            LookAssetStore.EnsureFolder(output + "/Vegetation");
            materials.Clear();
            // Change the scene identity before any edits; saving later cannot write back to v18.
            if (!EditorSceneManager.SaveScene(scene, destination)) throw new IOException("Could not create palette scene.");
            var root = new GameObject("V19_Palette_" + version);
            var atmosphere = root.AddComponent<DistrictAtmosphere19>();
            atmosphere.districts = Districts();
            var terrain = Terrain.activeTerrain;
            var sourceData = terrain.terrainData;
            world = new Vector4(terrain.transform.position.x, terrain.transform.position.z, sourceData.size.x, sourceData.size.z);
            BuildField(atmosphere);
            BuildTerrain(terrain, atmosphere);
            var look = MapLookBuilder.Load("v18");
            var buildings = look.buildings.ToDictionary(b => b.id);
            int renderers = 0;
            foreach (var renderer in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                var info = renderer.GetComponentInParent<MapBuildingInfo>();
                LookBuilding building = info != null && buildings.TryGetValue(info.Id, out var b) ? b : null;
                var source = renderer.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < source.Length; i++)
                {
                    Material original = source[i];
                    if (original == null || original.shader.name != "OnlyVolunteers/StyleV3/Surface") continue;
                    string target = Bright(original.name, building);
                    if (target == null) continue;
                    source[i] = Surface(original, target, false);
                    changed = true;
                }
                if (changed) { renderer.sharedMaterials = source; renderers++; }
            }
            BuildVegetation(terrain);
            BuildVolumes(root.transform, atmosphere.districts);
            AssetDatabase.SaveAssets();
            // Terrain serialization can reset a new splat in this project; re-apply after saving, as in v18.
            terrain.terrainData.SetAlphamaps(0, 0, paletteSplat);
            EditorUtility.SetDirty(terrain.terrainData);
            AssetDatabase.SaveAssetIfDirty(terrain.terrainData);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return destination + "; 10 district volumes + transition volume; " + renderers + " recoloured renderers; " + materials.Count + " surface variants";
        }

        private static void BuildField(DistrictAtmosphere19 atmosphere)
        {
            const int res = 1024;
            field = new Texture2D(res, res, TextureFormat.RFloat, false, true)
            { name = "Palette_Field_v19", wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var pixels = new Color[res * res];
            for (int z = 0; z < res; z++)
                for (int x = 0; x < res; x++)
                    pixels[z * res + x] = new Color(atmosphere.PaletteAt(new Vector2(world.x + (x + .5f) / res * world.z,
                        world.y + (z + .5f) / res * world.w)), 0, 0, 1);
            field.SetPixels(pixels); field.Apply(false, false);
            AssetDatabase.CreateAsset(field, output + "/Palette_Field_v19.asset");
        }

        private static float[,,] paletteSplat;
        private static void BuildTerrain(Terrain terrain, DistrictAtmosphere19 atmosphere)
        {
            TerrainData original = terrain.terrainData;
            int w = original.alphamapWidth, h = original.alphamapHeight, n = original.terrainLayers.Length;
            float[,,] old = original.GetAlphamaps(0, 0, w, h);
            string path = output + "/Terrain_palette.asset";
            if (!AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(original), path)) throw new IOException("Terrain copy failed");
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(path);
            var layers = new TerrainLayer[n * 2];
            var registry = AssetDatabase.LoadAssetAtPath<MapLookRegistry>("Assets/OnlyVolunteers/Map/Look/MapLookRegistry.asset");
            for (int i = 0; i < n; i++)
            {
                layers[i] = original.terrainLayers[i];
                string key = layers[i].name.Replace("TL17_", "");
                var legacy = registry.Layer("layer/" + key);
                if (legacy == null) throw new InvalidOperationException("Missing legacy layer: " + key);
                layers[n + i] = Object.Instantiate(legacy);
                layers[n + i].name = "V19_LegacyEndpoint_" + key;
                AssetDatabase.CreateAsset(layers[n + i], output + "/" + layers[n+i].name + ".terrainlayer");
            }
            data.terrainLayers = layers;
            paletteSplat = new float[h,w,n*2];
            for (int z = 0; z < h; z++)
                for (int x = 0; x < w; x++)
                {
                    float t = atmosphere.PaletteAt(new Vector2(world.x + (float)x/(w-1)*world.z, world.y + (float)z/(h-1)*world.w));
                    for (int i = 0; i < n; i++)
                    { paletteSplat[z,x,i] = old[z,x,i]*(1-t); paletteSplat[z,x,n+i] = old[z,x,i]*t; }
                }
            data.SetAlphamaps(0, 0, paletteSplat);
            terrain.terrainData = data;
            terrain.GetComponent<TerrainCollider>().terrainData = data;
            EditorUtility.SetDirty(data);
        }

        private static string Bright(string name, LookBuilding b)
        {
            if (name.Contains("3a_brick")) return LookPalette.DefaultHex("mat/brick");
            if (name.Contains("3b_plaster") || name.Contains("3c_concrete") || name.Contains("3d_cinder"))
                return b != null ? b.wall : LookPalette.DefaultHex("mat/concrete");
            if (name.Contains("4a_") || name.Contains("4b_") || name.Contains("4c_") || name.Contains("4d_"))
                return b != null ? b.roof_col : LookPalette.DefaultHex("mat/roof/_default");
            if (name.Contains("5a_") || name.Contains("5b_")) return b != null && b.style == "rural_wood" ? b.wall : LookPalette.DefaultHex("mat/wood");
            if (name.Contains("1a_grass")) return "#7D9A52";
            if (name.Contains("1b_dirt")) return LookPalette.DefaultHex("mat/road/dirt");
            if (name.Contains("1c_beach")) return "#E6D6A8";
            if (name.Contains("1d_gravel")) return "#9A907A";
            if (name.Contains("1e_mud")) return "#6E7A4B";
            if (name.Contains("2b_sidewalk")) return LookPalette.DefaultHex("mat/sidewalk/" + (b != null ? b.district : "_default"));
            if (name.Contains("2c_cobble")) return LookPalette.DefaultHex("mat/ground/cobble");
            return null; // road markings, glass, signs and gameplay props keep their own colours
        }

        private static Material Surface(Material original, string hex, bool grass)
        {
            string key = original.name + "_" + hex.TrimStart('#') + (grass ? "_grass" : "");
            if (materials.TryGetValue(key, out var existing)) return existing;
            var mat = new Material(original) { name = "V19_" + key, shader = Shader.Find("OnlyVolunteers/StyleV3/Palette19") };
            mat.SetTexture("_DistrictMask", field);
            mat.SetVector("_DistrictWorld", world);
            mat.SetColor("_BrightColor", C(hex));
            mat.SetFloat("_PaletteGrass", grass ? 1 : 0);
            AssetDatabase.CreateAsset(mat, output + "/Materials/" + mat.name + ".mat");
            materials[key] = mat;
            return mat;
        }

        private static void BuildVegetation(Terrain terrain)
        {
            var data = terrain.terrainData;
            var details = data.detailPrototypes;
            for (int i = 0; i < details.Length; i++)
            {
                var go = Object.Instantiate(details[i].prototype);
                go.name = "V19_" + details[i].prototype.name;
                foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                    renderer.sharedMaterials = renderer.sharedMaterials.Select(m => Surface(m,"#7D9A52",true)).ToArray();
                details[i].prototype = PrefabUtility.SaveAsPrefabAsset(go, output + "/Vegetation/" + go.name + ".prefab");
                Object.DestroyImmediate(go);
            }
            data.detailPrototypes = details;
            // v18 already references the exact legacy MP tree/fruit meshes and materials. Their two albedo endpoints
            // are identical. Preserve their positions, silhouettes, red apples and colours; create owned material copies.
            var protoCopies = new Dictionary<GameObject,GameObject>();
            var materialCopies = new Dictionary<Material,Material>();
            var trees = data.treePrototypes;
            foreach (var p in trees)
            {
                if (!protoCopies.TryGetValue(p.prefab, out var copy))
                {
                    var go = Object.Instantiate(p.prefab); go.name = "V19_" + p.prefab.name;
                    foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                    {
                        var mats = renderer.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++)
                        {
                            var m = mats[i];
                            if (!materialCopies.TryGetValue(m, out var own))
                            {
                                own = new Material(m) { name = "V19_" + m.name };
                                AssetDatabase.CreateAsset(own, output + "/Vegetation/" + own.name + ".mat");
                                materialCopies[m] = own;
                            }
                            mats[i] = own;
                        }
                        renderer.sharedMaterials = mats;
                    }
                    copy = PrefabUtility.SaveAsPrefabAsset(go, output + "/Vegetation/" + go.name + ".prefab");
                    Object.DestroyImmediate(go);
                    protoCopies[p.prefab] = copy;
                }
                p.prefab = copy;
            }
            data.treePrototypes = trees;
            data.RefreshPrototypes();
            EditorUtility.SetDirty(data);
        }

        private static void BuildVolumes(Transform parent, DistrictAtmosphere19.District[] districts)
        {
            var baseline = D("between_districts", Vector4.zero, .65f, "blended daylight", .43f,0,0,2,60,390,"#BBC9D0");
            AddVolume(parent, baseline, true);
            foreach (var d in districts) AddVolume(parent, d, false);
        }

        private static void AddVolume(Transform parent, DistrictAtmosphere19.District district, bool global)
        {
            var go = new GameObject("V19_Light_" + district.id); go.transform.SetParent(parent, false);
            if (!global)
            {
                Vector4 b = district.bounds;
                var box = go.AddComponent<BoxCollider>(); box.isTrigger = true;
                box.center = new Vector3((b.x+b.z)*.5f, 40, (b.y+b.w)*.5f);
                box.size = new Vector3(b.z-b.x-30, 200, b.w-b.y-30);
            }
            var profile = ScriptableObject.CreateInstance<VolumeProfile>(); profile.name = go.name;
            AssetDatabase.CreateAsset(profile, output + "/" + go.name + ".asset");
            var ca = profile.Add<ColorAdjustments>(false);
            ca.postExposure.Override(district.exposure); ca.saturation.Override(district.saturation); ca.contrast.Override(district.contrast);
            AssetDatabase.AddObjectToAsset(ca, profile);
            var wb = profile.Add<WhiteBalance>(false); wb.temperature.Override(district.temperature); wb.tint.Override(0);
            AssetDatabase.AddObjectToAsset(wb, profile);
            var volume = go.AddComponent<Volume>(); volume.isGlobal = global; volume.priority = global ? 2 : 20;
            volume.blendDistance = 60; volume.weight = 1; volume.sharedProfile = profile;
            volume.UpdateColliders();
            EditorUtility.SetDirty(profile);
        }
    }
}
