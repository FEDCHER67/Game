using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.Grass;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W76
{
    // The look stack of the playtested map (Map_Look_v19_Play_i10_capture_delivery) on W76, with the same systems and assets:
    // G18g district weather/fog/aerial haze + district light volumes + PostFX_v17 + sun (copied from i10, re-pointed to W76
    // district rectangles), G22 day/night painted sky, V19Wind, i10 terrain material/settings, and the G24 tall grass baked
    // for the W76 terrain (fork of GrassPlacement24 without the v19-only inputs). i10 is opened additively, read, closed unsaved.
    public static class W76LookV01
    {
        const string I10 = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string Out = "Assets/OnlyVolunteers/Map/W76Build/Generated/v01_look";
        const float ChunkSize = 16f, Step = .5f;

        // i10 district ids (code keys: residential = Rough) on W76 rectangles (min x, min z, max x, max z)
        static readonly Dictionary<string, Vector4> Rects = new()
        {
            ["forest"] = new(185, 60, 470, 330), ["village"] = new(180, 360, 470, 625), ["transition"] = new(525, 345, 705, 495),
            ["residential"] = new(655, 668, 1006, 905), ["old_town"] = new(790, 228, 1268, 470), ["industrial"] = new(1172, 596, 1356, 684),
            ["elite"] = new(1340, 255, 1500, 390), ["fields"] = new(520, 60, 665, 300), ["beach"] = new(790, 100, 1520, 228),
            ["tramduro"] = new(1450, 690, 1650, 840),
        };

        public static string Apply(Transform root, Terrain ter)
        {
            var log = new List<string>();
            if (!Directory.Exists(Out)) { Directory.CreateDirectory(Out); AssetDatabase.Refresh(); }
            var scene = root.gameObject.scene;
            var i10 = EditorSceneManager.OpenScene(I10, OpenSceneMode.Additive);
            GameObject Copy(string path)
            {
                var src = i10.GetRootGameObjects().Select(g => path.Contains('/') ? g.transform.Find(path.Substring(path.IndexOf('/') + 1)) : (g.name == path ? g.transform : null))
                    .FirstOrDefault(t => t && (!path.Contains('/') || t.root.name == path.Substring(0, path.IndexOf('/'))));
                if (!src) { log.Add("i10 object missing: " + path); return null; }
                var c = Object.Instantiate(src.gameObject);
                c.name = src.name;
                EditorSceneManager.MoveGameObjectToScene(c, scene);
                return c;
            }
            var palette = Copy("V19_ApprovedPalette_Full_v01");
            var skyRig = Copy("G22_DayNight_v04_Integration_i03");
            var wind = Copy("V19Wind");
            var sun = Copy("MapLook_v19_StyleV3/Sun");
            var post = Copy("MapLook_v19_StyleV3/PostFX_v17");
            var camSrc = i10.GetRootGameObjects().FirstOrDefault(g => g.name == "Main Camera")?.GetComponent<Camera>();
            float camFar = camSrc ? camSrc.farClipPlane : 460f, camFov = camSrc ? camSrc.fieldOfView : 70f;
            var i10Terrain = i10.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).FirstOrDefault();
            Material terMat = i10Terrain ? i10Terrain.materialTemplate : null;
            float pe = i10Terrain ? i10Terrain.heightmapPixelError : 3, bd = i10Terrain ? i10Terrain.basemapDistance : 220;
            float tdist = i10Terrain ? i10Terrain.treeDistance : 400, bb = i10Terrain ? i10Terrain.treeBillboardDistance : 400, cf = i10Terrain ? i10Terrain.treeCrossFadeLength : 30;
            int mft = i10Terrain ? i10Terrain.treeMaximumFullLODCount : 4000;
            EditorSceneManager.CloseScene(i10, true);
            foreach (var g in new[] { palette, skyRig, wind, sun, post }) if (g) g.transform.SetParent(root, true);

            // our own simple look off (the i10 stack owns sun, fog and grading); W76Atmosphere keeps only the tunnel glare
            var ownSun = root.Find("Sun"); if (ownSun) Object.DestroyImmediate(ownSun.gameObject);
            var ownVol = root.Find("Volume_W76");
            if (ownVol) { ownVol.GetComponent<W76Atmosphere>().GlareOnly = true; }
            var sunLight = sun ? sun.GetComponent<Light>() : null;
            RenderSettings.sun = sunLight;

            // district weather (disabled data source, as in i10) -> W76 rectangles; light volumes on the same rectangles
            var weather = palette ? palette.GetComponent<DistrictWeather19V05>() : null;
            if (weather)
            {
                weather.sun = sunLight;
                foreach (var d in weather.districts) if (Rects.TryGetValue(d.id, out var r)) d.bounds = r;
                foreach (var v in palette.GetComponentsInChildren<Volume>(true))
                {
                    string id = v.name.Replace("V19_Light_", "");
                    var box = v.GetComponent<BoxCollider>();
                    if (box && Rects.TryGetValue(id, out var r)) { box.center = new Vector3((r.x + r.z) * .5f, 40f, (r.y + r.w) * .5f); box.size = new Vector3(r.z - r.x - 30f, 200f, r.w - r.y - 30f); }
                }
                var fog = weather.visibleFog;
                if (fog)
                {
                    var i10World = fog.terrainWorld;
                    fog.terrainWorld = new Vector4(0, 0, ter.terrainData.size.x, ter.terrainData.size.z);
                    fog.groundHeights = GroundHeights(ter);
                    fog.halos = Array.Empty<DistrictFog19V05.Halo>();
                    fog.vanHeadlights = Array.Empty<Light>();
                    // mist banks: same banks, moved from the i10 Rough / Forest rectangles to the W76 ones
                    var i10Rough = new Vector4(550, 554, 824.8f, 696.4f); var i10Forest = new Vector4(127.4f, 81, 346, 315.2f);
                    fog.banks = fog.banks.Select(b =>
                    {
                        Vector4 a = b.forest ? i10Forest : i10Rough, t = b.forest ? Rects["forest"] : Rects["residential"];
                        float u = Mathf.Clamp01((b.position.x - a.x) / (a.z - a.x)), w = Mathf.Clamp01((b.position.z - a.y) / (a.w - a.y));
                        float x = Mathf.Lerp(t.x + 20, t.z - 20, u), z = Mathf.Lerp(t.y + 20, t.w - 20, w);
                        b.position = new Vector3(x, ter.SampleHeight(new Vector3(x, 0, z)) + ter.transform.position.y + Mathf.Clamp(b.position.y, .8f, 2.5f), z);
                        return b;
                    }).ToArray();
                    log.Add($"fog: terrainWorld {i10World} -> {fog.terrainWorld}, {fog.banks.Length} mist banks moved to W76 Rough / Forest");
                }
            }
            if (skyRig)
            {
                var sky = skyRig.GetComponents<MonoBehaviour>();
                foreach (var mb in sky)
                {
                    var so = new SerializedObject(mb);
                    var p = so.FindProperty("sun"); if (p != null) p.objectReferenceValue = sunLight;
                    p = so.FindProperty("source"); if (p != null) p.objectReferenceValue = weather;
                    p = so.FindProperty("fog"); if (p != null && weather) p.objectReferenceValue = weather.visibleFog;
                    p = so.FindProperty("lamps"); if (p != null) p.arraySize = 0;
                    p = so.FindProperty("slots"); if (p != null) p.arraySize = 0;
                    so.ApplyModifiedPropertiesWithoutUndo();
                }
                var tpl = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Sky/G22_v04/Generated/PaintedSky_v04.mat");
                if (tpl) RenderSettings.skybox = tpl;
            }
            if (wind)
            {
                var so = new SerializedObject(wind.GetComponents<MonoBehaviour>().First());
                so.FindProperty("fieldRectangle").vector4Value = new Vector4(0, 0, ter.terrainData.size.x, ter.terrainData.size.z);
                var dp = so.FindProperty("districts"); if (dp != null) dp.objectReferenceValue = weather;
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            // terrain: i10 material and distances
            if (terMat) ter.materialTemplate = terMat;
            ter.heightmapPixelError = pe; ter.basemapDistance = bd; ter.treeDistance = tdist; ter.treeBillboardDistance = bb;
            ter.treeCrossFadeLength = cf; ter.treeMaximumFullLODCount = mft;

            // camera like i10's (FOV 70, far 460, depth + opaque textures, post) at the spawn
            var spawn = root.Find("Spawn_W76");
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            camGo.transform.SetParent(root, false);
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = camFov; cam.farClipPlane = camFar; cam.nearClipPlane = .2f;
            camGo.AddComponent<AudioListener>();
            var ad = camGo.AddComponent<UniversalAdditionalCameraData>(); ad.renderPostProcessing = true; ad.requiresDepthTexture = true; ad.requiresColorTexture = true;
            if (spawn) { camGo.transform.position = spawn.position + new Vector3(0, 2.5f, -6f); camGo.transform.rotation = spawn.rotation * Quaternion.Euler(8, 0, 0); }

            log.Add($"i10 look copied: palette/weather/fog/aerial + {palette?.GetComponentsInChildren<Volume>(true).Length ?? 0} light volumes, G22 sky, V19Wind, Sun, PostFX_v17; terrain material {(terMat ? terMat.name : "?")}, camera FOV {camFov} far {camFar}");
            log.Add(BakeGrass(ter, weather, root));
            return string.Join("\n", log);
        }

        static Texture2D GroundHeights(Terrain ter)
        {
            var td = ter.terrainData;
            var tex = new Texture2D(256, 256, TextureFormat.RFloat, false, true) { name = "W76_GroundHeights_v01", wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color[256 * 256];
            for (int z = 0; z < 256; z++) for (int x = 0; x < 256; x++) px[z * 256 + x] = new Color(td.GetInterpolatedHeight(x / 255f, z / 255f) + ter.transform.position.y, 0, 0, 1);
            tex.SetPixels(px); tex.Apply();
            string p = Out + "/W76_GroundHeights_v01.asset";
            AssetDatabase.DeleteAsset(p);
            AssetDatabase.CreateAsset(tex, p);
            return tex;
        }

        // ------------------------------------------------------------ G24 tall grass for W76 (GrassPlacement24 rules)
        static string BakeGrass(Terrain terrain, DistrictWeather19V05 weather, Transform root)
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            var td = terrain.terrainData; var origin = terrain.transform.position; var size = td.size;
            int w = Mathf.CeilToInt(size.x), h = Mathf.CeilToInt(size.z), fx = w * 2, fz = h * 2;
            var hard = new bool[fx * fz]; long tris = 0;
            // hard surfaces of the W76 build: roads, streets/sidewalks, zones and yards, piers, fences, roofs (= footprints), inland water
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>())
            {
                if (!mf.sharedMesh) continue;
                string n = mf.name;
                bool surface = n.StartsWith("Sea") ? false : n == "roof" || n.StartsWith("Road_") || n.StartsWith("Street_") || n.StartsWith("Sidewalk_") || n.StartsWith("Zone_")
                    || n.StartsWith("Alley_") || n.StartsWith("Yard_") || n.StartsWith("Pier") || n.StartsWith("Boardwalk_") || n.StartsWith("Ring_") || n.StartsWith("Water_")
                    || n.StartsWith("FenceMesh_") || n.StartsWith("Parapet_") || n.StartsWith("Tunnel") || n.StartsWith("Portal") || n.StartsWith("AlleyPlug") || n.StartsWith("Checkpoint");
                if (surface) tris += Raster(mf, origin, fx, fz, hard);
            }
            var clearance = new float[w * h]; for (int i = 0; i < clearance.Length; i++) clearance[i] = 50;
            for (int z = 0; z < fz; z++) for (int x = 0; x < fx; x++) if (hard[z * fx + x])
                for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++)
                { int xx = (x + dx) / 2, zz = (z + dz) / 2; if (xx >= 0 && zz >= 0 && xx < w && zz < h) clearance[zz * w + xx] = 0; }
            Chamfer(clearance, w, h);
            float Clear(float x, float z) { int ix = Mathf.FloorToInt(x - origin.x), iz = Mathf.FloorToInt(z - origin.z); return ix < 0 || iz < 0 || ix >= w || iz >= h ? 0 : clearance[iz * w + ix]; }

            var alpha = td.GetAlphamaps(0, 0, td.alphamapWidth, td.alphamapHeight);
            var names = td.terrainLayers.Select(t => t ? t.name.ToLowerInvariant() : "").ToArray();
            var bounds = weather.districts.Select(d => d.bounds).ToArray(); var weights = new float[bounds.Length];
            var canopy = new HashSet<long>();
            foreach (var tree in td.treeInstances)
            {
                var p = Vector3.Scale(tree.position, size) + origin; int tx = Mathf.FloorToInt(p.x / 2), tz = Mathf.FloorToInt(p.z / 2);
                for (int dz = -2; dz <= 2; dz++) for (int dx = -2; dx <= 2; dx++) canopy.Add(((long)(tx + dx) << 32) ^ (uint)(tz + dz));
            }
            int nx = Mathf.CeilToInt(size.x / ChunkSize), count = 0, rejected = 0;
            var byChunk = new SortedDictionary<int, List<ChunkedGrassRenderer24.Blade>>();
            var perDistrict = new SortedDictionary<string, int>();
            for (int iz = 0; iz < size.z / Step; iz++) for (int ix = 0; ix < size.x / Step; ix++)
            {
                float x = origin.x + (ix + .12f + .76f * H(ix, iz, 1)) * Step, z = origin.z + (iz + .12f + .76f * H(ix, iz, 2)) * Step;
                float clr = Clear(x, z);
                if (clr < .9f) { rejected++; continue; }
                int ax = Mathf.Clamp((int)((x - origin.x) / size.x * td.alphamapWidth), 0, td.alphamapWidth - 1), az = Mathf.Clamp((int)((z - origin.z) / size.z * td.alphamapHeight), 0, td.alphamapHeight - 1);
                float meadow = 0, lawn = 0, park = 0, dry = 0, sand = 0;
                for (int l = 0; l < names.Length; l++)
                {
                    string n = names[l]; float a = alpha[az, ax, l];
                    if (n.Contains("meadow") || n.Contains("worn_grass")) meadow += a; else if (n.Contains("park")) park += a; else if (n.Contains("lawn")) lawn += a;
                    else if (n.Contains("dry") || n.Contains("dirt")) dry += a; else if (n.Contains("sand")) sand += a;
                }
                string district = "between_districts"; float edge = 0;
                for (int d = 0; d < bounds.Length; d++)
                { var b = bounds[d]; if (x >= b.x && x <= b.z && z >= b.y && z <= b.w) { district = weather.districts[d].id; edge = Mathf.Min(Mathf.Min(x - b.x, b.z - x), Mathf.Min(z - b.y, b.w - z)); break; } }
                bool rough = district == "residential", beach = district == "beach", forest = district == "forest";
                float ground = meadow + lawn + park;
                if (district == "village") ground = Mathf.Max(ground, dry * .8f);
                if (beach) ground = Mathf.Max(ground, sand * .8f);
                if (rough) ground = Mathf.Max(ground, dry * .75f);
                if (ground < .55f) continue;
                if (forest && (meadow < .6f || canopy.Contains(((long)Mathf.FloorToInt(x / 2) << 32) ^ (uint)Mathf.FloorToInt(z / 2)))) continue;
                float patch = Mathf.PerlinNoise(x * .047f + 14.2f, z * .047f + 19.4f), pockets = Mathf.PerlinNoise(x * .18f + 5.7f, z * .18f + 28.1f);
                float density = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.43f, .64f, patch)) * ground;
                if (pockets < .31f) continue;
                bool roadside = clr < 4.5f;
                bool trim = district == "old_town" || ((district == "fields" || district == "elite") && (edge > 18 || lawn + park > .35f));
                if (roadside) density *= .24f; else if (trim) density *= .42f;
                if (rough) density *= .17f; else if (beach) density *= .13f; else if (forest) density *= .42f;
                else if (district == "industrial" || district == "tramduro" || district == "transition") density *= .24f;
                if (H(ix, iz, 3) > density) continue;
                float u = (x - origin.x) / size.x, v = (z - origin.z) / size.z;
                if (td.GetSteepness(u, v) > 34) continue;
                float y = td.GetInterpolatedHeight(u, v) + origin.y;
                if (y < .3f) continue;                                                       // sea / shore (sea level 0)
                DistrictBlend19.Weights(bounds, new Vector2(x, z), weather.blendMetres, weights);
                float pal = 0; for (int d = 0; d < weights.Length; d++) pal += weights[d] * weather.districts[d].palette;
                pal = Mathf.Min(.999f, pal) + (rough ? 2 : beach ? 4 : 0);
                int blades = rough || beach ? 3 : roadside || trim ? 2 : 4;
                for (int b = 0; b < blades; b++)
                {
                    float bx = x + (H(ix, iz, 10 + b * 3) - .5f) * .28f, bz = z + (H(ix, iz, 11 + b * 3) - .5f) * .28f;
                    if (Clear(bx, bz) < .75f) continue;
                    float by = td.GetInterpolatedHeight((bx - origin.x) / size.x, (bz - origin.z) / size.z) + origin.y;
                    float hh = roadside ? Mathf.Lerp(.1f, .25f, H(ix, iz, 30 + b)) : trim ? Mathf.Lerp(.12f, .24f, H(ix, iz, 30 + b)) :
                        rough ? Mathf.Lerp(.22f, .48f, H(ix, iz, 30 + b)) : beach ? Mathf.Lerp(.28f, .55f, H(ix, iz, 30 + b)) : Mathf.Lerp(.5f, .9f, H(ix, iz, 30 + b));
                    float yaw = H(ix, iz, 40 + b) * Mathf.PI * 2, wd = hh < .26f ? Mathf.Lerp(.035f, .06f, H(ix, iz, 50 + b)) : Mathf.Lerp(.085f, .15f, H(ix, iz, 50 + b));
                    int key = Mathf.FloorToInt((bx - origin.x) / ChunkSize) + nx * Mathf.FloorToInt((bz - origin.z) / ChunkSize);
                    if (!byChunk.TryGetValue(key, out var list)) byChunk[key] = list = new List<ChunkedGrassRenderer24.Blade>();
                    list.Add(new ChunkedGrassRenderer24.Blade { positionHeight = new Vector4(bx, by - .015f, bz, hh), shape = new Vector4(Mathf.Cos(yaw), Mathf.Sin(yaw), wd, pal) });
                    perDistrict[district] = perDistrict.TryGetValue(district, out int c) ? c + 1 : 1; count++;
                }
            }
            string bin = Out + "/GrassInstances_W76_v01.bytes";
            var chunks = new List<GrassPatchData24.Chunk>(); var world = new Bounds(); bool first = true; uint start = 0;
            using (var wr = new BinaryWriter(File.Create(bin)))
                foreach (var pair in byChunk)
                {
                    var bnd = new Bounds((Vector3)pair.Value[0].positionHeight, Vector3.zero);
                    foreach (var bl in pair.Value)
                    {
                        bnd.Encapsulate((Vector3)bl.positionHeight + Vector3.up * bl.positionHeight.w); bnd.Encapsulate((Vector3)bl.positionHeight);
                        foreach (var vv in new[] { bl.positionHeight, bl.shape }) { wr.Write(vv.x); wr.Write(vv.y); wr.Write(vv.z); wr.Write(vv.w); }
                    }
                    bnd.Expand(new Vector3(1.8f, .2f, 1.8f));
                    chunks.Add(new GrassPatchData24.Chunk { centre = bnd.center, extents = bnd.extents, start = start, count = (uint)pair.Value.Count }); start += (uint)pair.Value.Count;
                    if (first) { world = bnd; first = false; } else world.Encapsulate(bnd);
                }
            AssetDatabase.ImportAsset(bin, ImportAssetOptions.ForceSynchronousImport);
            var data = ScriptableObject.CreateInstance<GrassPatchData24>();
            data.instanceCount = count; data.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bin); data.chunks = chunks.ToArray(); data.worldBounds = world;
            data.sourceScene = "Map_W76_Build_v01";
            data.placementSummary = string.Join("; ", perDistrict.Select(p => p.Key + "=" + p.Value)) + $"; {tris} hard tris; rejectedHard={rejected}; seconds={watch.Elapsed.TotalSeconds:0.0}";
            string dp = Out + "/GrassData_W76_v01.asset"; AssetDatabase.DeleteAsset(dp); AssetDatabase.CreateAsset(data, dp);
            var go = new GameObject("G24_TallGrass_W76_v01"); go.transform.SetParent(root, false);
            var r = go.AddComponent<ChunkedGrassRenderer24>();
            r.data = data;
            r.bladeMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/OnlyVolunteers/Map/Grass/Baked_v04/Blade3Triangles_v04.asset");
            r.material = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/Wind/v01/Materials/TallGrass_SharedWind_v01.mat");
            r.visibility = AssetDatabase.LoadAssetAtPath<ComputeShader>("Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB/GrassVisibility24.compute");
            r.viewDistance = 150;
            return $"grass: {count} blades in {chunks.Count} chunks ({data.placementSummary}); blade mesh / shared-wind material / compute of i10: {(r.bladeMesh && r.material && r.visibility)}";
        }

        static float H(int x, int z, int salt) => GrassHash(x, z, salt);
        static float GrassHash(int x, int z, int salt)
        { unchecked { uint h = (uint)(x * 73856093) ^ (uint)(z * 19349663) ^ (uint)(salt * 83492791); h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15; return (h & 0xffffff) / 16777216f; } }

        static long Raster(MeshFilter mf, Vector3 origin, int fx, int fz, bool[] hard)
        {
            var m = mf.transform.localToWorldMatrix; var mesh = mf.sharedMesh;
            var v = mesh.vertices; var t = mesh.triangles; long n = 0;
            var p = v.Select(q => { var w = m.MultiplyPoint3x4(q); return new Vector2((w.x - origin.x) / .5f, (w.z - origin.z) / .5f); }).ToArray();
            for (int i = 0; i + 2 < t.Length; i += 3)
            {
                Vector2 a = p[t[i]], b = p[t[i + 1]], c = p[t[i + 2]];
                float area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
                if (Mathf.Abs(area) < 1e-6f) continue;
                float sg = Mathf.Sign(area); n++;
                int x0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.x, Mathf.Min(b.x, c.x)))), x1 = Mathf.Min(fx - 1, Mathf.CeilToInt(Mathf.Max(a.x, Mathf.Max(b.x, c.x))));
                int z0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.y, Mathf.Min(b.y, c.y)))), z1 = Mathf.Min(fz - 1, Mathf.CeilToInt(Mathf.Max(a.y, Mathf.Max(b.y, c.y))));
                for (int z = z0; z <= z1; z++) for (int x = x0; x <= x1; x++)
                {
                    float px = x + .5f, pz = z + .5f;
                    if (((b.x - a.x) * (pz - a.y) - (b.y - a.y) * (px - a.x)) * sg >= 0 && ((c.x - b.x) * (pz - b.y) - (c.y - b.y) * (px - b.x)) * sg >= 0 && ((a.x - c.x) * (pz - c.y) - (a.y - c.y) * (px - c.x)) * sg >= 0)
                        hard[z * fx + x] = true;
                }
            }
            return n;
        }

        static void Chamfer(float[] c, int w, int h)
        {
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
            { int i = z * w + x; float v = c[i]; if (x > 0) v = Mathf.Min(v, c[i - 1] + 1); if (z > 0) { v = Mathf.Min(v, c[i - w] + 1); if (x > 0) v = Mathf.Min(v, c[i - w - 1] + 1.414f); if (x < w - 1) v = Mathf.Min(v, c[i - w + 1] + 1.414f); } c[i] = v; }
            for (int z = h - 1; z >= 0; z--) for (int x = w - 1; x >= 0; x--)
            { int i = z * w + x; float v = c[i]; if (x < w - 1) v = Mathf.Min(v, c[i + 1] + 1); if (z < h - 1) { v = Mathf.Min(v, c[i + w] + 1); if (x > 0) v = Mathf.Min(v, c[i + w - 1] + 1.414f); if (x < w - 1) v = Mathf.Min(v, c[i + w + 1] + 1.414f); } c[i] = v; }
        }
    }
}
