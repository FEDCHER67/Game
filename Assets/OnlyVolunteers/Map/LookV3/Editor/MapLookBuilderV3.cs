using System.Collections.Generic;
using System.Diagnostics;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Debug = UnityEngine.Debug;

namespace OnlyVolunteers.Map.Look.V3
{
    // The style v3 look of map v16 (Fedya 2026-10-11: One-Armed Robber direction, our bright palette): textured
    // categories by surface (G13 textures, V3Materials), terrain layers by surface, roads by type, buildings with the G12
    // detail kit through the facade grammar (V3Facade), merged per building and material with LODs (V3Buildings), the
    // plan's water with flow (V3Water; material = the manifest's "8a_water"), typed fences, the v2 daylight with the fog
    // pulled in for a 750 m far clip. A separate path: the v12 look (MapLookBuilder) and its assets are not touched;
    // everything v3 writes lives under Map/LookV3, Art/StyleKit_v3/BuildingDetails and the v16 scenes.
    public static class MapLookBuilderV3
    {
        public const string Revision = "v16";
        public const string SceneDir = "Assets/OnlyVolunteers/Scenes/Map";
        public static string LastLog = "";
        // The revision being built (lighting, terrain trees, props and fences switch on it); v16 stays exactly as before.
        public static string Current = Revision;

        // v17+ (phase A, 2026-10-11): game scale, density, occlusion, muted atmosphere. "v17", "v18"... but not "v16"/"v12".
        public static bool IsV17(string revision) => !string.IsNullOrEmpty(revision) && revision.Length == 3 && string.CompareOrdinal(revision, "v17") >= 0;

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v18 (style v3)")]
        public static void BuildMenuV18()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build("Map_Look_v18", "v18");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v19 (style v3)")]
        public static void BuildMenuV19()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build("Map_Look_v19", "v19");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v17 (style v3, phase A)")]
        public static void BuildMenuV17()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build("Map_Look_v17", "v17");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v16 (style v3)")]
        public static void BuildMenu()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build();
        }

        // Builds and saves Scenes/Map/Map_Look_v16.unity. Returns the build log.
        public static string Build(string sceneName = "Map_Look_v16", string revision = Revision)
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning("[StyleV3] Exit Play mode first, then build again.");
                return "playing";
            }
            var sw = Stopwatch.StartNew();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Current = revision;
            var root = new GameObject($"MapLook_{revision}_StyleV3").transform;
            var log = new List<string>();
            MapHeightSampler sampler = BuildEnvironment(revision, root, sceneName, log);
            V3Lighting.Apply(root, revision);
            FlyCamera(MapLookBuilder.Load(revision), sampler, revision);
            LookAssetStore.EnsureFolder(SceneDir);
            string path = $"{SceneDir}/{sceneName}.unity";
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), path);
            log.Add($"scene saved to {path} in {sw.Elapsed.TotalSeconds:0.0} s");
            LastLog = "[StyleV3] " + revision + "\n  " + string.Join("\n  ", log);
            Current = Revision;
            Debug.Log(LastLog);
            return LastLog;
        }

        // Environment only (terrain, roads, buildings, water, fences, blockers) under `parent`; meshes and the terrain go
        // to Map/LookV3/Generated/<owner>.
        public static MapHeightSampler BuildEnvironment(string revision, Transform parent, string owner, List<string> log)
        {
            var sw = Stopwatch.StartNew();
            Current = revision;
            bool v17 = IsV17(revision);
            V3Terrain.TreeDistance = v17 ? V3Lighting.FogEndV17 : 600f;
            V3Materials.ResetCache();
            V3Building.ResetCaches();
            log.Add($"materials: G13 manifest {V3Materials.KitManifest ?? "none (flat temporary palette materials)"}; water material {V3Materials.WaterSource("sea")}");
            LookData d = MapLookBuilder.Load(revision);
            V3LookData.Load(revision);
            var store = new V3Store(owner);
            store.Reset();
            List<V3Water.Basin> basins = V3Water.Prepare(d, log);
            // Typed fences come from world_v11_extensions (V3Ground.Fences); the look_v1 elite ring entries are the same runs.
            d.elite_fence = new LookEliteFence[0];
            var hm = new HeightModel(d);
            hm.CalmV19Pilots = revision == "v19";
            // v17: drivable grade <= 8 % through the new relief (embankments/cuttings come from the side blends).
            if (v17) hm.RoadGrade = 0.08f;
            hm.Bake();
            V3Water.SinkTerrain(hm, basins);
            log.Add($"heights baked in {sw.Elapsed.TotalSeconds:0.0} s ({hm.MinHeight:0.0}..{hm.MaxHeight:0.0} m)");
            foreach (string w in hm.Warnings) log.Add("height: " + w);
            if (v17)
            {
                var steep = new List<string>();
                foreach (HeightModel.RoadProfile r in hm.Roads)
                    if (r.MaxGrade > 0.09f) steep.Add($"{r.Id} {r.MaxGrade * 100f:0}%");
                log.Add("roads over 9 % grade: " + (steep.Count == 0 ? "none" : string.Join(", ", steep)));
            }

            var mud = new List<float[]>();
            foreach (LookWater w in d.water)
            {
                string src = V3Water.Source(w);
                if (src == "bog") mud.Add(LookGeom.OffsetPolygon(V3Dressing.Ccw(w.pts), 3f));
                else if (src == "river" || src == "village_pond" || src == "pond_under_waterfall") mud.Add(LookGeom.OffsetPolygon(V3Dressing.Ccw(w.pts), 1.2f));
            }
            var forest = new List<float[]>();
            foreach (var z in V3LookData.ForestZones) forest.Add(z.poly);
            MapLookRegistry registry = LookAssetStore.Registry();
            log.Add($"park trees added: {V3Dressing.AddParkTrees(d)}");
            // v17 playtest fixes (2026-10-12): natural tree scatter; corner patches, mitred corners and sidewalks cut at
            // carriageways; parked cars thinned (V3Fix17 says what in the plan data causes each).
            if (v17) V3Fix17.Trees(d, log);
            Terrain terrain = V3Terrain.Build(d, hm, registry, store, parent, mud, forest, log);
            var samplerGo = new GameObject("MapHeightSampler");
            samplerGo.transform.SetParent(parent, false);
            var sampler = samplerGo.AddComponent<MapHeightSampler>();
            sampler.Terrain = terrain;
            sampler.Decks = RoadMeshBuilder.Decks(d, hm.Height);

            if (v17)
            {
                V3Fix17.Roads(d, log);
                RoadMeshBuilder.LineResampler = (pts, step) => V3Fix17.ResampleKeepCorners(pts, step);
                RoadMeshBuilder.JunctionMaterial = V3Fix17.JunctionMaterial;
                V3Fix17.Fences(d, log);
            }
            try
            {
                V3Ground.Roads(d, hm, sampler, store, parent, log);
            }
            finally
            {
                RoadMeshBuilder.LineResampler = null;
                RoadMeshBuilder.JunctionMaterial = null;
            }
            if (v17) V3Fix17.Cars(d, log);
            V3Kit kit = V3Kit.Load();
            V3Buildings.Build(d, hm, kit, store, parent, log);
            V3Dressing.Build(d, hm, registry, store, parent, log);
            if (v17) V3Props17.Build(d, hm, registry, store, parent, log);
            V3Water.Build(d, hm, basins, store, parent, sampler, log);
            if (v17) V3WaterAudio17.Bake(parent.Find("Water"), revision, log);
            V3Ground.Fences(hm, store, parent, log);
            V3Ground.RetainingWalls(d, hm, store, parent, log);
            V3Ground.Blockers(d, hm, parent);
            if (v17) V3Grass.Build(terrain, V3Terrain.PendingSplat, V3Terrain.PendingNames, parent, store, log);
            if (revision == "v19") V19Infill.Build(sampler, parent, store, log);
            AssetDatabase.SaveAssets();
            V3Terrain.ReapplySplat(terrain, log);
            log.Add($"assets: {store.MeshCount} meshes in {store.GeneratedDir}; environment built in {sw.Elapsed.TotalSeconds:0.0} s");
            return sampler;
        }

        private static void FlyCamera(LookData d, MapHeightSampler sampler, string revision)
        {
            Vector2 spawn = MapLookValidator.Spawn(d);
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.3f;
            cam.farClipPlane = V3Lighting.FarClipFor(revision);
            cam.fieldOfView = 60f;
            camGo.AddComponent<AudioListener>();
            camGo.AddComponent<LookFlyCamera>();
            UniversalAdditionalCameraData data = cam.GetUniversalAdditionalCameraData();
            data.renderPostProcessing = true;
            // The stylized water (G14, Uber Stylized Water) reads the depth and opaque textures: on per camera, whatever
            // the active pipeline asset says (PC_RPAsset has both on as well).
            data.requiresDepthOption = CameraOverrideOption.On;
            data.requiresColorOption = CameraOverrideOption.On;
            Vector3 eye = sampler.Snap(new Vector3(spawn.x, 0f, spawn.y), 30f) + new Vector3(-40f, 0f, -40f);
            Vector3 target = new Vector3(d.terrain.x0 + d.terrain.sx * 0.45f, 0f, d.terrain.y0 + d.terrain.sy * 0.55f);
            camGo.transform.SetPositionAndRotation(eye, Quaternion.LookRotation((target - eye).normalized + Vector3.down * 0.25f));
        }
    }
}
