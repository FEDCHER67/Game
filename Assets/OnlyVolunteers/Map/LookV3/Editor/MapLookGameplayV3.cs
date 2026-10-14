using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace OnlyVolunteers.Map.Look.V3
{
    // Map_Look_v16_Play in style v3: Map_Look_v16 (MapLookBuilderV3, built first when asked or missing) with the grey-box
    // gameplay placed on it exactly as MapLookGameplay does for the v12 look (van, cameras, KCC player, CrowdDirector with
    // crowd_v16, police_v16, pickups, sea return), saved under the Play name. Both scenes share one generated environment
    // (Map/LookV3/Generated/Map_Look_v16, ~1/2 the disk of two builds): rebuilding the look means rebuilding Play too.
    public static class MapLookGameplayV3
    {
        public const string LookScene = "Map_Look_v16", PlayScene = "Map_Look_v16_Play";

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v18 + Gameplay")]
        public static void BuildMenuV18()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build(true, "v18");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v19 + Gameplay")]
        public static void BuildMenuV19()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build(true, "v19");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v17 + Gameplay (style v3, phase A)")]
        public static void BuildMenuV17()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build(true, "v17");
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Build Map Look v16 + Gameplay (style v3)")]
        public static void BuildMenu()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Build(true);
        }

        public static string Build(bool rebuildLook) => Build(rebuildLook, MapLookBuilderV3.Revision);

        public static string Build(bool rebuildLook, string rev)
        {
            if (EditorApplication.isPlaying) return "playing";
            string LookScene = $"Map_Look_{rev}", PlayScene = $"Map_Look_{rev}_Play";
            string planPath = Path.GetFullPath(MapGreyboxBuilder.PlanPath(rev));
            if (!File.Exists(planPath)) return "no grey-box plan " + planPath;
            var sw = Stopwatch.StartNew();
            var log = new List<string>();
            string lookPath = $"{MapLookBuilderV3.SceneDir}/{LookScene}.unity";
            if (rebuildLook || !File.Exists(Path.Combine(Application.dataPath, "..", lookPath)))
                log.Add(MapLookBuilderV3.Build(LookScene, rev));
            EditorSceneManager.OpenScene(lookPath, OpenSceneMode.Single);
            GameObject envRoot = GameObject.Find($"MapLook_{rev}_StyleV3");
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            if (envRoot == null || sampler == null) return LookScene + " has no v3 environment root or height sampler";
            // The look scene's fly camera goes: the gameplay brings the van rig and the player's camera.
            foreach (LookFlyCamera fly in Object.FindObjectsByType<LookFlyCamera>(FindObjectsInactive.Include))
                Object.DestroyImmediate(fly.gameObject);
            MapGreyboxBuilder.Plan plan = MapGreyboxBuilder.LoadPlan(rev);
            bool police = MapCrowdPlacer.UseDirector && Police.MapPolicePlacer.Enabled && Police.MapPolicePlacer.EnsureData(rev, out _) != null;
            LookData data = MapLookBuilder.Load(rev);
            Physics.SyncTransforms();
            var setup = new MapGreyboxBuilder.GameplaySetup
            {
                Plan = plan,
                Ground = new LookPlayGround(sampler, data, envRoot.transform),
                Pawn = MapGreyboxBuilder.PawnKind.Kcc,
                Sea = plan.sea,
                FarClip = V3Lighting.FarClipFor(rev),
                PostProcessing = true,
                Crowd = MapCrowdPlacer.UseDirector ? MapGreyboxBuilder.CrowdKind.Director : MapGreyboxBuilder.CrowdKind.Static,
                Revision = rev,
            };
            MapGreyboxBuilder.GameplayResult result = MapGreyboxBuilder.PlaceGameplay(setup);
            AddSurf(setup.SeaZone, data);
            // Depth + opaque textures for the stylized water on every camera of the scene (scene overrides only).
            foreach (Camera cam in Object.FindObjectsByType<Camera>(FindObjectsInactive.Include))
            {
                var camData = cam.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>() ?? cam.gameObject.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
                camData.requiresDepthOption = UnityEngine.Rendering.Universal.CameraOverrideOption.On;
                camData.requiresColorOption = UnityEngine.Rendering.Universal.CameraOverrideOption.On;
                // v17: safety net against any NaN/Inf pixel that bloom would blow up into a glare blob.
                if (MapLookBuilderV3.IsV17(rev)) camData.stopNaN = true;
                EditorUtility.SetDirty(camData);
            }
            // v17: Backslash toggles a free fly camera over the map (player and van input suspended meanwhile).
            if (MapLookBuilderV3.IsV17(rev)) new GameObject("V3_FlyToggle").AddComponent<V3FlyToggle>();
            int moved = 0;
            foreach (Collider c in envRoot.GetComponentsInChildren<Collider>(true))
                if (!c.isTrigger && c.gameObject.layer != 0)
                {
                    c.gameObject.layer = 0;
                    moved++;
                }
            string scenePath = $"{MapLookBuilderV3.SceneDir}/{PlayScene}.unity";
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scenePath);
            // An earlier separate Play build of this session left its own generated folder: unused now.
            string old = V3Store.GeneratedRoot + "/" + PlayScene;
            if (rev != "v18" && rev != "v19" && AssetDatabase.IsValidFolder(old)) AssetDatabase.DeleteAsset(old);
            Vector3 van = result.Van.transform.position;
            log.Add($"gameplay: van at ({van.x:0.0}, {van.y:0.00}, {van.z:0.0}), " +
                    (result.Director != null ? $"CrowdDirector with {result.Npcs} pooled NPCs ({(result.Director.Data != null ? result.Director.Data.name : "no data")}), " : $"{result.Npcs} crowd NPCs, ") +
                    $"{result.Pickups} pickups, police {(result.Police != null ? "placed" : police ? "failed" : "off")}; {moved} environment colliders moved to Default -> {scenePath} in {sw.Elapsed.TotalSeconds:0.0} s");
            string text = "[StyleV3+Play] " + rev + "\n  " + string.Join("\n  ", log);
            Debug.Log(text);
            return text;
        }

        // As MapLookGameplay.AddSurf: the beach below the sea level is no dry place to put someone back on.
        private static void AddSurf(SeaReturnZone zone, LookData data)
        {
            if (zone == null || LookGeom.Count(data.sea.pts) < 3 || LookGeom.Count(data.beach.pts) < 3) return;
            float[] pts = data.beach.pts;
            var polygon = new Vector2[pts.Length / 2];
            for (int i = 0; i < polygon.Length; i++) polygon[i] = new Vector2(pts[2 * i], pts[2 * i + 1]);
            var surf = zone.gameObject.AddComponent<SeaReturnSurf>();
            surf.WaterLevel = data.sea.level;
            surf.Polygon = polygon;
        }
    }
}
