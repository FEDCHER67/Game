using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Debug = UnityEngine.Debug;

namespace OnlyVolunteers.Map.Look
{
    // Builds the stylised map look from look_vNN_flat.json (ArtSource/References/Map/Look/flatten_look.py):
    // terrain + splat + trees, draped roads and sidewalks, procedural buildings merged per district cell, water,
    // fences (plots and the elite ring only), props, blockers, lighting and a fly camera, saved as Map_Look_vNN.
    // BuildEnvironment is the environment alone, for the greybox gameplay builder to place on later.
    public static class MapLookBuilder
    {
        public const string LookJsonDir = "ArtSource/References/Map/Look";
        private const string SceneDir = "Assets/OnlyVolunteers/Scenes/Map";

        [MenuItem("OnlyVolunteers/Map/Build Map Look (latest plan)")]
        public static void BuildLatest()
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning("[MapLook] Exit Play mode first, then build again.");
                return;
            }
            string rev = LatestRevision();
            if (rev == null)
            {
                Debug.LogError($"[MapLook] No look_vNN_flat.json in {LookJsonDir}; run flatten_look.py first.");
                return;
            }
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var sw = Stopwatch.StartNew();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject($"MapLook_{rev}").transform;
            MapHeightSampler sampler = BuildEnvironment(rev, root, $"Map_Look_{rev}");
            if (sampler == null) return;
            MapLookLighting.Apply(root);
            FlyCamera(lastData ?? Load(rev), sampler);
            LookAssetStore.EnsureFolder(SceneDir);
            string scenePath = $"{SceneDir}/Map_Look_{rev}.unity";
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scenePath);
            Debug.Log($"[MapLook] {rev}: scene saved to {scenePath} in {sw.Elapsed.TotalSeconds:0.0} s");
            if (lastData != null && lastModel != null) Debug.Log(MapLookValidator.Validate(lastData, lastModel, rev, root));
        }

        public static string LatestRevision()
        {
            string dir = Path.Combine(Application.dataPath, "..", LookJsonDir);
            if (!Directory.Exists(dir)) return null;
            string latest = null;
            foreach (string f in Directory.GetFiles(dir, "look_v*_flat.json"))
            {
                string rev = Path.GetFileName(f).Substring("look_".Length).Replace("_flat.json", "");
                if (rev.Contains("_")) continue;
                if (latest == null || rev.Length > latest.Length || rev.Length == latest.Length && string.CompareOrdinal(rev, latest) > 0) latest = rev;
            }
            return latest;
        }

        public static LookData Load(string revision)
        {
            string path = Path.Combine(Application.dataPath, "..", LookJsonDir, $"look_{revision}_flat.json");
            LookData d = JsonUtility.FromJson<LookData>(File.ReadAllText(path));
            d.Normalise();
            return d;
        }

        private static LookData lastData;
        private static HeightModel lastModel;

        // Environment only: terrain, roads, buildings, water, props, colliders. Returns the height sampler.
        // `owner` should name the scene being built (e.g. the greybox scene): its generated meshes and terrain go to
        // Generated/<owner>_<rev>, which only a rebuild of that same owner replaces, so other scenes keep theirs.
        // Defaults to the active scene's name ("Unsaved" for a new, unsaved scene).
        public static MapHeightSampler BuildEnvironment(string revision, Transform parent, string owner = null)
        {
            var sw = Stopwatch.StartNew();
            var log = new List<string>();
            LookData d = Load(revision);
            lastData = d;
            if (d.schema != "look_v1") Debug.LogWarning($"[MapLook] look json schema '{d.schema}', expected look_v1");
            MapLookRegistry registry = LookAssetStore.Registry();
            registry.ResetCache();
            if (string.IsNullOrEmpty(owner)) owner = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
            if (string.IsNullOrEmpty(owner)) owner = "Unsaved";
            var store = new LookAssetStore(revision, owner);
            store.Reset();
            MapLookRegistry.Persist = LookAssetStore.PersistMaterial;
            try
            {
                var hm = new HeightModel(d);
                hm.Bake();
                lastModel = hm;
                log.Add($"heights baked in {sw.Elapsed.TotalSeconds:0.0} s");

                Terrain terrain = TerrainBaker.Build(d, hm, registry, store, parent, log);
                var samplerGo = new GameObject("MapHeightSampler");
                samplerGo.transform.SetParent(parent, false);
                var sampler = samplerGo.AddComponent<MapHeightSampler>();
                sampler.Terrain = terrain;
                sampler.Decks = RoadMeshBuilder.Decks(d, hm.Height);

                var render = new DistrictCombiner();
                var colliders = new DistrictCombiner();
                List<LookPiece> pieces = RoadMeshBuilder.Build(d, hm.Height, sampler.Decks);
                var roadRender = new DistrictCombiner();
                foreach (LookPiece p in pieces)
                {
                    roadRender.Add(p);
                    if (p.Collide) colliders.Add(p);
                }
                log.Add($"roads: {pieces.Count} pieces, {sampler.Decks.Count} bridge decks");

                int buildingTris = Buildings(d, hm, registry, store, parent, render, log);
                WaterBuilder.Build(d, hm, registry, store, parent, sampler, log);
                PropScatterer.Build(d, hm, registry, store, parent, render, colliders, log);

                var merged = new GameObject("Merged").transform;
                merged.SetParent(parent, false);
                var b = render.Emit(merged, "Look", registry, store, true, false);
                var r = roadRender.Emit(merged, "Road", registry, store, true, false);
                var c = colliders.Emit(merged, "Collider", registry, store, false, true);
                log.Add($"merged: buildings/fences {b.objects} objects {b.triangles} tris {b.batches} submeshes (buildings alone {buildingTris} tris); " +
                        $"roads {r.objects} objects {r.triangles} tris {r.batches} submeshes; {c.objects} collider chunks");
                if (buildingTris > 350000) log.Add($"WARNING building triangles {buildingTris} over the 350k budget");
                int drawn = b.batches + r.batches + PropScatterer.LastInstanceRenderers;
                if (drawn > 150) log.Add($"note: {drawn} batches before culling ({b.batches} merged, {r.batches} roads, {PropScatterer.LastInstanceRenderers} prop prefab renderers; target 150)");
                foreach (string w in hm.Warnings) log.Add("height: " + w);
                foreach (string w in d.warnings) log.Add("flattener: " + w);
                store.Save();
                TerrainBaker.ReapplySplat(terrain, log);
                log.Add($"assets: {store.MeshCount} meshes in {store.GeneratedDir}; environment built in {sw.Elapsed.TotalSeconds:0.0} s");
                Debug.Log("[MapLook] " + revision + "\n  " + string.Join("\n  ", log));
                return sampler;
            }
            finally
            {
                MapLookRegistry.Persist = null;
            }
        }

        private static int Buildings(LookData d, HeightModel hm, MapLookRegistry registry, LookAssetStore store, Transform parent, DistrictCombiner render, List<string> log)
        {
            var root = new GameObject("Buildings").transform;
            root.SetParent(parent, false);
            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            Material signMaterial = SignMaterial(font);
            int tris = 0, prefabs = 0, over = 0, nudgedBuildings = 0;
            foreach (LookBuilding b in d.buildings)
            {
                if (LookGeom.Count(b.fp) < 3) continue;
                float pad = hm.Pads.TryGetValue(b.id, out float p) ? p : hm.Height(b.x, b.y);
                var go = new GameObject($"B_{b.id}");
                go.transform.SetParent(root, false);
                go.transform.position = new Vector3(b.x, pad, b.y);
                var info = go.AddComponent<MapBuildingInfo>();
                info.Id = b.id;
                info.Kind = b.kind;
                info.Type = b.type;
                info.District = b.district;
                info.Label = b.label;
                info.Style = b.style;
                info.Floors = b.floors;
                info.Height = b.h;
                info.PadY = pad;
                info.SignText = b.sign_text;
                info.Footprint = LookConvert.Poly(b.fp);

                // Exact key only: a "prop/_default" family prefab must not replace kiosks, ATMs or bus shelters.
                PrefabSlot slot = string.IsNullOrEmpty(b.prop_key) ? null : registry.ExactPrefabSlot(b.prop_key);
                if (slot != null)
                {
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, go.transform);
                    inst.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.Euler(0f, b.front_deg, 0f));
                    inst.transform.localScale = slot.scale;
                    // Same rule as street furniture: kit art bigger than the plan footprint slides out of the carriageway.
                    if (slot.collider && PropScatterer.KeepOffRoads(d, inst)) nudgedBuildings++;
                    info.Doors = new[] { inst.transform.position };
                    info.DoorFacing = new[] { Quaternion.Euler(0f, b.front_deg, 0f) };
                    prefabs++;
                    continue;
                }

                BuildingStyle style = BuildingStyles.For(b);
                BuildingResult res = ProceduralBuilding.Build(b, style, pad, hm.LowestUnder(b.fp));
                tris += res.Triangles;
                if (res.Triangles > style.TriangleBudget)
                {
                    over++;
                    log.Add($"note: {b.id} ({b.kind}/{b.type}) {res.Triangles} tris over its {style.TriangleBudget} budget");
                }
                Vector3 origin = go.transform.position;
                render.Add(b.district, Matrix4x4.Translate(origin), res.Render, origin);
                if (res.Collision != null) go.AddComponent<MeshCollider>().sharedMesh = store.AddMesh(res.Collision);
                foreach (ExtraCollider ec in res.Colliders)
                {
                    Vector3 world = origin + ec.Centre;
                    if (ec.Optional && OnRoad(d, world.x, world.z, Mathf.Max(ec.Size.x, ec.Size.z) / 2f + 0.5f)) continue;
                    var cgo = new GameObject("Collider");
                    cgo.transform.SetParent(go.transform, false);
                    cgo.transform.SetLocalPositionAndRotation(ec.Centre, ec.Rotation);
                    cgo.AddComponent<BoxCollider>().size = ec.Size;
                    DistrictCombiner.MarkStatic(cgo, false);
                }
                var doors = new Vector3[res.Doors.Length];
                var facing = new Quaternion[res.Doors.Length];
                for (int i = 0; i < doors.Length; i++)
                {
                    doors[i] = origin + res.Doors[i].position;
                    facing[i] = res.Doors[i].rotation;
                }
                info.Doors = doors;
                info.DoorFacing = facing;
                if (res.HasSign) Sign(go.transform, res, font, signMaterial);
                DistrictCombiner.MarkStatic(go, false);
            }
            log.Add($"buildings: {d.buildings.Length} ({prefabs} from registry prefabs, {nudgedBuildings} nudged off van roads), {tris} triangles, {over} over budget");
            return tris;
        }

        internal static bool OnRoad(LookData d, float x, float z, float margin)
        {
            foreach (LookRoad r in d.roads)
                if (r.van && LookGeom.DistToPolyline(r.pts, x, z, false, out _, out _) < r.w / 2f + margin)
                    return true;
            return false;
        }

        // Depth-tested, fogged text material on the font's atlas (font.material is GUI/Text Shader, which draws through
        // buildings and hills). Persisted so the saved scene keeps it; falls back to the font material without the shader.
        private static Material SignMaterial(Font font)
        {
            Shader shader = Shader.Find("OnlyVolunteers/Map/LookSignText");
            if (shader == null) return font.material;
            var mat = new Material(shader) { name = "Look_SignText", mainTexture = font.material.mainTexture, renderQueue = 3000 };
            return LookAssetStore.PersistMaterial(mat, mat.name);
        }

        // Sign text as a TextMesh (LegacyRuntime has Cyrillic), sized to fit the board.
        private static void Sign(Transform parent, BuildingResult res, Font font, Material material)
        {
            var go = new GameObject("Sign");
            go.transform.SetParent(parent, false);
            go.transform.SetLocalPositionAndRotation(res.Sign.position, res.Sign.rotation);
            var tm = go.AddComponent<TextMesh>();
            tm.text = res.SignText;
            tm.font = font;
            tm.fontSize = 64;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.alignment = TextAlignment.Center;
            tm.color = res.SignTextColor;
            float byHeight = res.SignHeight * 0.62f * 10f / tm.fontSize;
            float byWidth = (res.SignWidth - 0.3f) * 10f / (tm.fontSize * 0.62f * Mathf.Max(1, res.SignText.Length));
            tm.characterSize = Mathf.Max(0.005f, Mathf.Min(byHeight, byWidth));
            go.GetComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static void FlyCamera(LookData d, MapHeightSampler sampler)
        {
            Vector2 spawn = MapLookValidator.Spawn(d);
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.3f;
            cam.farClipPlane = 3000f;
            cam.fieldOfView = 60f;
            camGo.AddComponent<AudioListener>();
            camGo.AddComponent<LookFlyCamera>();
            cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            Vector3 eye = sampler.Snap(new Vector3(spawn.x, 0f, spawn.y), 30f) + new Vector3(-40f, 0f, -40f);
            Vector3 target = new Vector3(d.terrain.x0 + d.terrain.sx * 0.45f, 0f, d.terrain.y0 + d.terrain.sy * 0.55f);
            camGo.transform.SetPositionAndRotation(eye, Quaternion.LookRotation((target - eye).normalized + Vector3.down * 0.25f));
        }
    }
}
