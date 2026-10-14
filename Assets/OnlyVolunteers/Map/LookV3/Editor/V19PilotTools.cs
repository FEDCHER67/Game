using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Player;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    // Review and access tooling of the map pilots (docs/specs/MAP_SPEC_2026-10-13_v01.md, stage 1: Hamlet + hamlet_rough_e,
    // Rough District). It runs unchanged on the v17 Play scene (the baseline) and on the v19 Play scene (after), so both
    // sides are measured from the same poses, routes and van settings. Files live in Working/Reviews/Map_v19_Pilots.
    //  - Poses (review_poses_v19.json): "walk" = the KCC player's camera (1.85 m above the feet, FOV 75), "raised" = the same
    //    camera on a raised standing surface, "van" = the VanCameraRig chase view (7.5 m back, 2.8 m up, aimed 1.2 m above
    //    the van root, FOV 70, pulled in by obstacles) behind a Van.prefab set on the ground, "top" = an orthographic plan
    //    view. Rendered off-screen in edit mode through the game's own pipeline asset (QualitySettings.renderPipeline, not
    //    the style capture asset), near 0.05 m, the revision's far clip, post on, stopNaN, 1920 x 1080.
    //  - Routes (routes_v19.json), Play mode: the scene's ordinary van (stock VanController, VanUpgrades all 0, empty) driven
    //    by a scripted pure-pursuit driver along a polyline, or the KCC player walked along one by scripted inputs. Crowd and
    //    police roots are switched off for repeatability. Results: routes_<label>.json and .txt. The state survives the
    //    domain reload of entering Play mode (SessionState + InitializeOnLoad). Application.runInBackground and
    //    PlayerSettings are never touched. Initial Play-mode frames need a visible editor; stepping begins only after
    //    EnteredPlayMode and the character's Awake, so no player loop is invoked during scene initialization.
    //  - Probes (edit mode, open look scene): terrain profiles, road grades on the built surface, slope/seam statistics of
    //    the pilot boxes and the ground under placed objects.
    [InitializeOnLoad]
    public static class V19PilotTools
    {
        public const string Dir = "Working/Reviews/Map_v19_Pilots";
        public const string PosesFile = "review_poses_v19.json", RoutesFile = "routes_v19.json";
        public const float WalkEye = 1.85f, WalkFov = 75f, VanFov = 70f, Near = 0.05f;
        public const float ChaseDistance = 7.5f, ChaseHeight = 2.8f, ChaseLook = 1.2f;
        private const string VanPrefab = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab";
        private const string Key = "OnlyVolunteers.V19PilotTools.";

        public static string ProjectDir => Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        public static string OutDir => Path.Combine(ProjectDir, Dir);

        // ------------------------------------------------------------------------------------------------ poses / capture

        public sealed class Pose
        {
            public string Name, Kind, Pilot, Note;
            public float X, Z, Yaw, Pitch, Above, SurfaceY = float.NaN, OrthoSize = 120f, Fov;
        }

        public static List<Pose> LoadPoses(string file = PosesFile)
        {
            var list = new List<Pose>();
            string path = Path.Combine(OutDir, file);
            if (!File.Exists(path)) return list;
            if (!(V3Json.Parse(File.ReadAllText(path)) is Dictionary<string, object> root) || !root.TryGetValue("poses", out object po) || !(po is List<object> poses))
                return list;
            foreach (object o in poses)
            {
                var d = (Dictionary<string, object>)o;
                list.Add(new Pose
                {
                    Name = V3Json.GetString(o, "name") ?? "pose",
                    Kind = V3Json.GetString(o, "kind") ?? "walk",
                    Pilot = V3Json.GetString(o, "pilot") ?? "",
                    Note = V3Json.GetString(o, "note") ?? "",
                    X = (float)V3Json.GetNumber(o, 0, "x"),
                    Z = (float)V3Json.GetNumber(o, 0, "z"),
                    Yaw = (float)V3Json.GetNumber(o, 0, "yaw"),
                    Pitch = (float)V3Json.GetNumber(o, 0, "pitch"),
                    Above = (float)V3Json.GetNumber(o, 0, "above"),
                    SurfaceY = d.ContainsKey("surface_y") ? (float)V3Json.GetNumber(o, 0, "surface_y") : float.NaN,
                    OrthoSize = (float)V3Json.GetNumber(o, 120, "ortho_size"),
                    Fov = (float)V3Json.GetNumber(o, 0, "fov"),
                });
            }
            return list;
        }

        // Renders every pose (or the ones whose name contains `only`) of the open look scene to <Dir>/<prefix><name>.png.
        public static string Shoot(string prefix, string revision, string only = null, int width = 1920, int height = 1080)
        {
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            if (sampler == null) return "no MapHeightSampler in the open scene";
            var done = new List<string>();
            float far = V3Lighting.FarClipFor(revision);
            foreach (Pose p in LoadPoses())
            {
                if (!string.IsNullOrEmpty(only) && p.Name.IndexOf(only, StringComparison.Ordinal) < 0) continue;
                string file = Path.Combine(OutDir, prefix + p.Name + ".png");
                try
                {
                    switch (p.Kind)
                    {
                        case "van":
                            done.Add(ShootVan(sampler, p, file, far, width, height));
                            break;
                        case "top":
                        {
                            var eye = new Vector3(p.X, 600f, p.Z);
                            Render(file, eye, Quaternion.Euler(90f, p.Yaw, 0f), 60f, 3000f, width, height, true, p.OrthoSize, false);
                            done.Add(file);
                            break;
                        }
                        default:
                        {
                            float ground = !float.IsNaN(p.SurfaceY) ? p.SurfaceY : sampler.Height(p.X, p.Z) + p.Above;
                            var eye = new Vector3(p.X, ground + WalkEye, p.Z);
                            Render(file, eye, Quaternion.Euler(p.Pitch, p.Yaw, 0f), p.Fov > 0f ? p.Fov : WalkFov, far, width, height, false, 0f, true);
                            done.Add(file);
                            break;
                        }
                    }
                }
                catch (Exception e)
                {
                    done.Add($"{p.Name}: FAILED {e.Message}");
                }
            }
            return $"{done.Count} captures\n" + string.Join("\n", done);
        }

        private static string ShootVan(MapHeightSampler sampler, Pose p, string file, float far, int width, int height)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefab);
            var van = prefab != null ? (GameObject)PrefabUtility.InstantiatePrefab(prefab) : null;
            // The review van is transient: use the same scene-scoped transparent variant as the saved v19 van.
            var aerial19 = Object.FindAnyObjectByType<DistrictAerial19V01>();
            if(van && aerial19 && aerial19.isActiveAndEnabled)
            {
                var glass=AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/LookV3/Palette19/Aerial_v01/Materials/VAN_Glass_8a71bad6_Aerial_v01.mat");
                if(glass)foreach(var renderer in van.GetComponentsInChildren<Renderer>(true))
                {
                    var materials=renderer.sharedMaterials;
                    for(int i=0;i<materials.Length;i++)if(materials[i]&&materials[i].name=="VAN_Glass")materials[i]=glass;
                    renderer.sharedMaterials=materials;
                }
            }
            try
            {
                Quaternion yaw = Quaternion.Euler(0f, p.Yaw, 0f);
                Vector3 fwd = yaw * Vector3.forward, right = yaw * Vector3.right;
                float hc = sampler.Height(p.X, p.Z);
                float hf = sampler.Height(p.X + fwd.x * 1.58f, p.Z + fwd.z * 1.58f), hr = sampler.Height(p.X - fwd.x * 1.58f, p.Z - fwd.z * 1.58f);
                float hl = sampler.Height(p.X - right.x * 0.8f, p.Z - right.z * 0.8f), hrr = sampler.Height(p.X + right.x * 0.8f, p.Z + right.z * 0.8f);
                float pitch = -Mathf.Atan2(hf - hr, 3.16f) * Mathf.Rad2Deg, roll = Mathf.Atan2(hl - hrr, 1.6f) * Mathf.Rad2Deg;
                Quaternion rot = Quaternion.Euler(pitch, p.Yaw, roll);
                var root = new Vector3(p.X, Mathf.Max(hc, (hf + hr) * 0.5f) + 0.05f, p.Z);
                if (van != null) van.transform.SetPositionAndRotation(root, rot);
                Physics.SyncTransforms();
                Vector3 target = root + Vector3.up * ChaseLook;
                Vector3 desired = target + yaw * new Vector3(0f, ChaseHeight - ChaseLook, -ChaseDistance);
                desired = PullIn(target, desired, van != null ? van.transform : null);
                Render(file, desired, Quaternion.LookRotation(target - desired, Vector3.up), p.Fov > 0f ? p.Fov : VanFov, far, width, height, false, 0f, true);
                return file;
            }
            finally
            {
                if (van != null) Object.DestroyImmediate(van);
            }
        }

        // VanCameraRig.Unobstructed: a 0.25 m sphere from the look point toward the camera stops 0.1 m short of the first
        // obstruction, never closer than 0.5 m. The van itself does not count.
        private static Vector3 PullIn(Vector3 target, Vector3 camera, Transform van)
        {
            Vector3 offset = camera - target;
            float distance = offset.magnitude;
            if (distance < 0.01f) return camera;
            Vector3 dir = offset / distance;
            float best = distance;
            bool hitAny = false;
            foreach (RaycastHit h in Physics.SphereCastAll(target, 0.25f, dir, distance, ~0, QueryTriggerInteraction.Ignore))
            {
                if (van != null && h.transform.IsChildOf(van)) continue;
                if (h.distance < best)
                {
                    best = h.distance;
                    hitAny = true;
                }
            }
            return hitAny ? target + dir * Mathf.Max(0.5f, best - 0.1f) : camera;
        }

        public static void Render(string file, Vector3 position, Quaternion rotation, float fov, float far, int width, int height, bool ortho, float orthoSize, bool fog)
        {
            // Plan sheets use the same fog-free orthographic view as the baseline. The district depth fog is perspective-only.
            var weather19=ortho?Object.FindAnyObjectByType<DistrictWeather19V05>():null;
            var fog19=ortho?Object.FindAnyObjectByType<DistrictFog19V05>():null;
            bool weatherEnabled=weather19&&weather19.enabled,fogEnabled=fog19&&fog19.enabled;
            if(weatherEnabled)weather19.enabled=false;if(fogEnabled)fog19.enabled=false;
            bool oldFog = RenderSettings.fog;
            var go = new GameObject("V19_CaptureCamera");
            try
            {
                RenderSettings.fog = fog && oldFog;
                var cam = go.AddComponent<Camera>();
                cam.fieldOfView = fov;
                cam.nearClipPlane = ortho ? 1f : Near;
                cam.farClipPlane = far;
                cam.orthographic = ortho;
                cam.orthographicSize = orthoSize;
                cam.clearFlags = CameraClearFlags.Skybox;
                go.transform.SetPositionAndRotation(position, rotation);
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = true;
                data.antialiasing = AntialiasingMode.None;
                data.stopNaN = true;
                data.requiresDepthOption = CameraOverrideOption.On;
                data.requiresColorOption = CameraOverrideOption.On;
                int msaa = QualitySettings.renderPipeline is UniversalRenderPipelineAsset urp ? Mathf.Max(1, urp.msaaSampleCount) : 1;
                var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = msaa };
                rt.Create();
                var resolved = new RenderTexture(width, height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
                resolved.Create();
                cam.targetTexture = rt;
                cam.Render();
                cam.Render();
                cam.targetTexture = null;
                Graphics.Blit(rt, resolved);
                RenderTexture prev = RenderTexture.active;
                RenderTexture.active = resolved;
                var tex = new Texture2D(width, height, TextureFormat.RGB24, false, false);
                tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                tex.Apply();
                RenderTexture.active = prev;
                Directory.CreateDirectory(Path.GetDirectoryName(file));
                File.WriteAllBytes(file, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                rt.Release();
                resolved.Release();
                Object.DestroyImmediate(rt);
                Object.DestroyImmediate(resolved);
            }
            finally
            {
                Object.DestroyImmediate(go);
                RenderSettings.fog = oldFog;
                if(weatherEnabled)weather19.enabled=true;if(fogEnabled)fog19.enabled=true;
            }
        }

        // ------------------------------------------------------------------------------------------------ routes (Play)

        public sealed class Route
        {
            public string Name, Mode, Pilot, Expect, Note, Plan;
            public float SpeedKmh = 40f, Timeout = 0f, PlannedLength;
            public List<Vector2> Pts = new();
            public string PlanInfo = "";
        }

        public static List<Route> LoadRoutes(string file = RoutesFile)
        {
            var list = new List<Route>();
            string path = Path.Combine(OutDir, file);
            if (!File.Exists(path)) return list;
            if (!(V3Json.Parse(File.ReadAllText(path)) is Dictionary<string, object> root) || !root.TryGetValue("routes", out object ro) || !(ro is List<object> routes))
                return list;
            foreach (object o in routes)
            {
                var d = (Dictionary<string, object>)o;
                var r = new Route
                {
                    Name = V3Json.GetString(o, "name") ?? "route",
                    Mode = V3Json.GetString(o, "mode") ?? "van",
                    Pilot = V3Json.GetString(o, "pilot") ?? "",
                    Expect = V3Json.GetString(o, "expect") ?? "pass",
                    Note = V3Json.GetString(o, "note") ?? "",
                    SpeedKmh = (float)V3Json.GetNumber(o, 40, "speed_kmh"),
                    Timeout = (float)V3Json.GetNumber(o, 0, "timeout_s"),
                    Plan = V3Json.GetString(o, "plan") ?? "",
                };
                if (d.TryGetValue("pts", out object pts) && pts is List<object> pl)
                    foreach (object q in pl)
                        if (q is List<object> xy && xy.Count >= 2 && xy[0] is double a && xy[1] is double b)
                            r.Pts.Add(new Vector2((float)a, (float)b));
                if (r.Pts.Count >= 2) list.Add(r);
            }
            return list;
        }

        static V19PilotTools()
        {
            EditorApplication.playModeStateChanged += PlayStateChanged;
            if (SessionState.GetBool(Key + "active", false)) EditorApplication.update += Tick;
        }

        private static void PlayStateChanged(PlayModeStateChange state)
        {
            if (state == PlayModeStateChange.EnteredPlayMode)
                SessionState.SetBool(Key + "initialized", true);
            else if (state == PlayModeStateChange.ExitingPlayMode && SessionState.GetBool(Key + "active", false))
                DetachInterrupted("interrupted: Play mode exited before the route run finished");
        }

        // Never resume an old baseline run on a different scene after a human/editor operation.
        private static void DetachInterrupted(string reason)
        {
            SessionState.SetBool(Key + "active", false);
            SessionState.SetString(Key + "status", reason);
            EditorApplication.update -= Tick;
            run = null;
            Time.captureDeltaTime = 0f;
            Debug.LogWarning("[V19Pilot] " + reason);
        }

        // Opens the scene, enters Play mode and runs every route (or those whose name contains `only`); the results land in
        // <Dir>/routes_<label>.json/.txt and Play mode stops by itself.
        public static string StartRoutes(string scenePath, string label, string only = null, string routeFile = RoutesFile)
        {
            if (EditorApplication.isPlaying) return "already playing";
            if (LoadRoutes(routeFile).Count == 0) return "no routes in " + Path.Combine(OutDir, routeFile);
            if (File.Exists(Path.Combine(OutDir, $"routes_{label}.json")) || File.Exists(Path.Combine(OutDir, $"routes_{label}.txt")))
                return "output already exists; choose a new numbered label: " + label;
            EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
            SessionState.SetBool(Key + "active", true);
            SessionState.SetBool(Key + "initialized", false);
            SessionState.SetString(Key + "label", label);
            SessionState.SetString(Key + "only", only ?? "");
            SessionState.SetString(Key + "scene", scenePath);
            SessionState.SetString(Key + "routeFile", routeFile);
            SessionState.SetString(Key + "status", "starting");
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
            EditorApplication.isPlaying = true;
            return "started routes " + label;
        }

        public static string Status() => SessionState.GetString(Key + "status", "idle");

        public static void Abort()
        {
            SessionState.SetBool(Key + "active", false);
            SessionState.SetString(Key + "status", "aborted");
            EditorApplication.update -= Tick;
            run = null;
            Time.captureDeltaTime = 0f;
            EditorApplication.isPaused = false;
            if (EditorApplication.isPlaying) EditorApplication.isPlaying = false;
        }

        private sealed class Run
        {
            public List<Route> Routes;
            public int Index = -1, Phase;
            public float PhaseStart, Start;
            public VanController Van;
            public Rigidbody Body;
            public GreyboxPawn Pawn;
            public KccFirstPersonInput Kcc;
            public readonly List<Behaviour> Disabled = new();
            public readonly List<GameObject> Hidden = new();
            public readonly StringBuilder Json = new(), Text = new();
            public bool FirstJson = true;
            // per route
            public float[] Cum;
            public int Seg;
            public float Travel, MaxLat, SumLat, MaxRoll, MaxPitch, MinClear = 9f, MaxClimb, SlowSince = -1f, MinSpeed = 999f, MaxSpeed, LastProgressT;
            public int Samples, Airborne, Grounded, Frames;
            public Vector3 Last, ProgressAt;
            public string Fail, Contact;
            public float VanBottom;
            public readonly List<string> Events = new();
            public readonly List<string> ContactTrace = new();
        }

        private static Run run;

        // The run steps the game itself: Play mode is paused and every editor update advances it frame by frame
        // (EditorApplication.Step) for up to ~120 ms of wall time, with a fixed 1/60 s per frame (Time.captureDeltaTime).
        // The result is the same whether the editor is focused, behind other windows or minimised (a minimised editor
        // stops the normal player loop when runInBackground is off, which must not be changed), and repeatable.
        public const float FrameDt = 1f / 60f;

        private static void Tick()
        {
            if (!SessionState.GetBool(Key + "active", false))
            {
                EditorApplication.update -= Tick;
                return;
            }
            if (!EditorApplication.isPlaying) return;
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().path != SessionState.GetString(Key + "scene", ""))
            {
                DetachInterrupted("interrupted: active scene changed; route results invalidated");
                return;
            }
            if (!SessionState.GetBool(Key + "initialized", false) || Time.frameCount < 2)
            {
                SessionState.SetString(Key + "status", "waiting for normal Play-mode initialization (keep Game view visible)");
                return;
            }
            if (run == null)
            {
                var motor = Object.FindAnyObjectByType<KinematicCharacterController.KinematicCharacterMotor>();
                if (motor != null && motor.CharacterController == null)
                {
                    SessionState.SetString(Key + "status", "waiting for KCC Awake before stepping");
                    return;
                }
            }
            if (!EditorApplication.isPaused)
            {
                EditorApplication.isPaused = true;
                Time.captureDeltaTime = FrameDt;
            }
            var wall = System.Diagnostics.Stopwatch.StartNew();
            while (wall.ElapsedMilliseconds < 120)
            {
                try
                {
                    Step();
                }
                catch (Exception e)
                {
                    Debug.LogError("[V19Pilot] route run failed: " + e);
                    SessionState.SetString(Key + "status", "error " + e.Message);
                    Finish();
                    return;
                }
                if (!SessionState.GetBool(Key + "active", false) || !EditorApplication.isPlaying) return;
                EditorApplication.Step();
            }
        }

        private static void Step()
        {
            float now = Time.time;
            if (run == null)
            {
                run = new Run { Routes = LoadRoutes(SessionState.GetString(Key + "routeFile", RoutesFile)), PhaseStart = now };
                string only = SessionState.GetString(Key + "only", "");
                if (!string.IsNullOrEmpty(only)) run.Routes = run.Routes.FindAll(r => r.Name.IndexOf(only, StringComparison.Ordinal) >= 0);
                SessionState.SetString(Key + "status", $"settling, {run.Routes.Count} routes");
                return;
            }
            if (run.Index < 0)
            {
                if (now - run.PhaseStart < 3f) return;
                Prepare();
                run.Index = 0;
                run.Phase = 0;
                run.PhaseStart = now;
                return;
            }
            if (run.Index >= run.Routes.Count)
            {
                Finish();
                return;
            }
            Route r = run.Routes[run.Index];
            SessionState.SetString(Key + "status", $"route {run.Index + 1}/{run.Routes.Count} {r.Name} phase {run.Phase}");
            if (r.Mode == "walk") StepWalk(r, now);
            else StepVan(r, now);
        }

        private static void Prepare()
        {
            run.Van = Object.FindAnyObjectByType<VanController>();
            run.Body = run.Van != null ? run.Van.GetComponent<Rigidbody>() : null;
            run.Pawn = Object.FindAnyObjectByType<GreyboxPawn>();
            run.Kcc = run.Pawn != null ? run.Pawn.GetComponent<KccFirstPersonInput>() : null;
            foreach (string n in new[] { "Crowd", "Police" })
            {
                GameObject g = GameObject.Find(n);
                if (g != null && g.activeSelf)
                {
                    g.SetActive(false);
                    run.Hidden.Add(g);
                }
            }
            if (run.Van != null)
                foreach (MonoBehaviour mb in run.Van.GetComponents<MonoBehaviour>())
                    if (mb.enabled && (mb.GetType().Name == "GreyboxVanAutopilot" || mb.GetType().Name == "VanDriveInput"))
                    {
                        mb.enabled = false;
                        run.Disabled.Add(mb);
                    }
            if (run.Van != null)
            {
                float low = float.MaxValue;
                int interior = LayerMask.NameToLayer("VehicleInterior");
                foreach (Collider c in run.Van.GetComponentsInChildren<Collider>())
                {
                    // The cargo-door step ramps (VanInteriorColliders) live on VehicleInterior, which PhysX ignores.
                    if (c is WheelCollider || c.isTrigger || c.gameObject.layer == interior) continue;
                    Bounds b = c.bounds;
                    for (int k = 0; k < 8; k++)
                    {
                        Vector3 corner = b.center + Vector3.Scale(b.extents, new Vector3((k & 1) == 0 ? -1 : 1, (k & 2) == 0 ? -1 : 1, (k & 4) == 0 ? -1 : 1));
                        low = Mathf.Min(low, run.Van.transform.InverseTransformPoint(corner).y);
                    }
                }
                run.VanBottom = low == float.MaxValue ? 0.2f : low;
                VanUpgrades up = run.Van.GetComponent<VanUpgrades>();
                run.Text.AppendLine($"van: mass {run.Body.mass:0} kg, motor {run.Van.MotorTorque:0} Nm, max {run.Van.MaxSpeedKmh:0} km/h, brake {run.Van.BrakeTorque:0}, " +
                                    $"steer {run.Van.MaxSteerAngle:0}/{run.Van.HighSpeedSteerAngle:0} deg, anti-roll {run.Van.AntiRoll:0}, upgrades " +
                                    (up != null ? $"E{up.GetLevel(VanUpgradeCategory.Engine)} B{up.GetLevel(VanUpgradeCategory.Brakes)} H{up.GetLevel(VanUpgradeCategory.Handling)}" : "none") +
                                    $", chassis bottom {run.VanBottom:0.00} m above the root; crowd/police roots off: {run.Hidden.Count}");
            }
            run.Json.Append("{\"label\":\"").Append(SessionState.GetString(Key + "label", "run")).Append("\",\"scene\":\"")
                .Append(SessionState.GetString(Key + "scene", "")).Append("\",\"routes\":[");
        }

        private static float H(float x, float z)
        {
            var s = Object.FindAnyObjectByType<MapHeightSampler>();
            return s != null ? s.Height(x, z) : 0f;
        }

        private static void BeginRoute(Route r, float now)
        {
            var pts = new float[r.Pts.Count * 2];
            for (int i = 0; i < r.Pts.Count; i++)
            {
                pts[2 * i] = r.Pts[i].x;
                pts[2 * i + 1] = r.Pts[i].y;
            }
            run.Cum = LookGeom.Cumulative(pts, false);
            run.Seg = 0;
            run.Travel = run.MaxLat = run.SumLat = run.MaxRoll = run.MaxPitch = run.MaxClimb = run.MaxSpeed = 0f;
            run.MinClear = 9f;
            run.MinSpeed = 999f;
            run.SlowSince = -1f;
            run.Samples = run.Airborne = run.Grounded = run.Frames = 0;
            run.Fail = null;
            run.Contact = null;
            run.Events.Clear();
            run.ContactTrace.Clear();
            if(r.Name.StartsWith("c_")&&r.Mode=="van"&&run.Van)
            {
                var witness=run.Van.GetComponent<G18RouteContactWitness>();
                if(!witness)witness=run.Van.gameObject.AddComponent<G18RouteContactWitness>();
                witness.Contacts.Clear();
            }
            run.Start = now;
            run.LastProgressT = now;
        }

        // Closest point of the route polyline to p (searching from the current segment on), its arc length and distance.
        private static void Project(Route r, Vector2 p, out float s, out float dist)
        {
            float best = float.MaxValue;
            s = 0f;
            int bestSeg = run.Seg;
            for (int i = Mathf.Max(0, run.Seg - 1); i < r.Pts.Count - 1; i++)
            {
                Vector2 a = r.Pts[i], b = r.Pts[i + 1];
                Vector2 ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                float d = Vector2.Distance(p, a + ab * t);
                if (d < best - 1e-3f)
                {
                    best = d;
                    s = run.Cum[i] + ab.magnitude * t;
                    bestSeg = i;
                }
                if (run.Cum[i] - run.Cum[Mathf.Min(run.Seg, run.Cum.Length - 1)] > 60f) break;
            }
            run.Seg = bestSeg;
            dist = best;
        }

        private static Vector2 PointAt(Route r, float s)
        {
            float total = run.Cum[run.Cum.Length - 1];
            s = Mathf.Clamp(s, 0f, total);
            for (int i = 0; i < r.Pts.Count - 1; i++)
                if (s <= run.Cum[i + 1] + 1e-4f)
                {
                    float L = run.Cum[i + 1] - run.Cum[i];
                    return Vector2.Lerp(r.Pts[i], r.Pts[i + 1], L > 1e-4f ? (s - run.Cum[i]) / L : 0f);
                }
            return r.Pts[r.Pts.Count - 1];
        }

        private static float TurnAhead(Route r, float s, float span)
        {
            Vector2 a = PointAt(r, s), b = PointAt(r, s + span * 0.5f), c = PointAt(r, s + span);
            Vector2 u = b - a, v = c - b;
            if (u.sqrMagnitude < 1e-3f || v.sqrMagnitude < 1e-3f) return 0f;
            return Vector2.Angle(u, v);
        }

        private static void StepVan(Route r, float now)
        {
            if (run.Van == null)
            {
                Record(r, "no van in the scene", now);
                return;
            }
            Transform t = run.Van.transform;
            if (run.Phase == 0)
            {
                Vector2 a = r.Pts[0], b = r.Pts[1];
                float yaw = Mathf.Atan2(b.x - a.x, b.y - a.y) * Mathf.Rad2Deg;
                run.Van.ResetUpright(new Vector3(a.x, H(a.x, a.y) + 0.6f, a.y), yaw);
                run.Van.Throttle = 0f;
                run.Van.Steer = 0f;
                run.Van.Handbrake = true;
                run.Phase = 1;
                run.PhaseStart = now;
                return;
            }
            if (run.Phase == 1)
            {
                if (now - run.PhaseStart < 2f) return;
                BeginRoute(r, now);
                run.Last = t.position;
                run.ProgressAt = t.position;
                run.Van.Handbrake = false;
                run.Phase = 2;
                return;
            }
            // Phase 2: drive.
            Vector3 pos = t.position;
            var p2 = new Vector2(pos.x, pos.z);
            Project(r, p2, out float s, out float lat);
            float total = run.Cum[run.Cum.Length - 1];
            float v = run.Van.SpeedKmh;
            float vms = Mathf.Abs(v) / 3.6f;
            float look = Mathf.Clamp(5f + 0.35f * vms, 6f, 14f);
            Vector2 target = PointAt(r, s + look);
            var fwd = new Vector2(t.forward.x, t.forward.z);
            Vector2 to = target - p2;
            float ang = Vector2.SignedAngle(to, fwd); // + = target to the right
            float steer = Mathf.Clamp(ang / 22f, -1f, 1f);
            float turn = TurnAhead(r, s, 24f);
            float vt = r.SpeedKmh * Mathf.Clamp(1f - turn / 110f, 0.35f, 1f);
            if (Mathf.Abs(ang) > 25f) vt = Mathf.Min(vt, 18f);
            run.Van.Steer = steer;
            run.Van.Throttle = Mathf.Clamp((vt - v) / 6f, -1f, 1f);
            run.Van.Handbrake = false;
            // metrics
            run.Frames++;
            run.Travel += Vector2.Distance(new Vector2(run.Last.x, run.Last.z), p2);
            run.Last = pos;
            run.MaxLat = Mathf.Max(run.MaxLat, lat);
            run.SumLat += lat;
            run.Samples++;
            Vector3 e = t.eulerAngles;
            float roll = Mathf.DeltaAngle(0f, e.z), pitch = Mathf.DeltaAngle(0f, e.x);
            run.MaxRoll = Mathf.Max(run.MaxRoll, Mathf.Abs(roll));
            run.MaxPitch = Mathf.Max(run.MaxPitch, Mathf.Abs(pitch));
            run.MaxSpeed = Mathf.Max(run.MaxSpeed, v);
            if (now - run.Start > 6f) run.MinSpeed = Mathf.Min(run.MinSpeed, v);
            int grounded = 0;
            foreach (WheelCollider w in run.Van.GetComponentsInChildren<WheelCollider>())
                if (w.isGrounded) grounded++;
            if (grounded <= 1) run.Airborne++;
            float clear = Clearance(t);
            run.MinClear = Mathf.Min(run.MinClear, clear);
            if (clear < 0.02f)
            {
                run.Grounded++;
                if (run.Events.Count < 12 && (run.Events.Count == 0 || !run.Events[run.Events.Count - 1].StartsWith("chassis")))
                    run.Events.Add($"chassis touches the ground at ({pos.x:0}, {pos.z:0})");
            }
            else if (run.Events.Count > 0 && run.Events[run.Events.Count - 1].StartsWith("chassis") && run.Events.Count < 12)
                run.Events.Add("clear");
            if (Vector3.Distance(pos, run.ProgressAt) > 1.0f)
            {
                run.ProgressAt = pos;
                run.LastProgressT = now;
            }
            float timeout = r.Timeout > 0f ? r.Timeout : 30f + total / Mathf.Max(1f, r.SpeedKmh / 3.6f) * 3f;
            bool arrived = s >= total - 4f && Vector2.Distance(p2, r.Pts[r.Pts.Count - 1]) < 6f;
            if (arrived) run.Fail = null;
            else if (Mathf.Abs(roll) > 55f || Vector3.Dot(t.up, Vector3.up) < 0.3f) run.Fail = $"tipped at ({pos.x:0}, {pos.z:0}), roll {roll:0} deg";
            else if (now - run.LastProgressT > 6f) run.Fail = $"stuck at ({pos.x:0}, {pos.z:0}) after {s:0} of {total:0} m: " + Blocking(t);
            else if (lat > 14f) run.Fail = $"left the line by {lat:0} m at ({pos.x:0}, {pos.z:0}) after {s:0} m: " + Blocking(t);
            else if (now - run.Start > timeout) run.Fail = $"timeout {timeout:0} s at ({pos.x:0}, {pos.z:0}) after {s:0} of {total:0} m";
            else return;
            run.Van.Throttle = 0f;
            run.Van.Steer = 0f;
            run.Van.Handbrake = true;
            Record(r, run.Fail, now, s, total);
        }

        // Chassis clearance: rays straight down (van frame) from six points of the underside, the van's own colliders skipped.
        private static float Clearance(Transform t)
        {
            float min = 9f;
            for (int i = 0; i < 6; i++)
            {
                float lx = (i % 2 == 0) ? -0.6f : 0.6f, lz = (i / 2 - 1) * 1.9f;
                Vector3 o = t.TransformPoint(new Vector3(lx, run.VanBottom + 0.4f, lz));
                foreach (RaycastHit h in Physics.RaycastAll(o, -t.up, 2f, ~0, QueryTriggerInteraction.Ignore))
                {
                    if (h.transform.IsChildOf(t)) continue;
                    if (h.collider.attachedRigidbody != null && !h.collider.attachedRigidbody.isKinematic) continue;
                    if (h.collider.gameObject.layer == LayerMask.NameToLayer("VehicleInterior")) continue;
                    min = Mathf.Min(min, h.distance - 0.4f);
                }
            }
            return min;
        }

        // What is right in front of the van or the pawn: collider names (parent/child), or the terrain slope ahead.
        private static string Blocking(Transform t)
        {
            var names = new List<string>();
            Vector3 c = t.position + t.forward * 3.2f + Vector3.up * 1.0f;
            foreach (Collider col in Physics.OverlapBox(c, new Vector3(1.3f, 0.8f, 1.2f), t.rotation, ~0, QueryTriggerInteraction.Ignore))
            {
                if (col.transform.IsChildOf(t)) continue;
                string n = col is TerrainCollider ? "terrain" : (col.transform.parent != null ? col.transform.parent.name + "/" : "") + col.name;
                if (!names.Contains(n) && names.Count < 4) names.Add(n);
            }
            Vector3 f = t.forward;
            float h0 = H(t.position.x, t.position.z), h1 = H(t.position.x + f.x * 4f, t.position.z + f.z * 4f);
            return (names.Count > 0 ? string.Join(", ", names) : "nothing solid ahead") + $"; ground ahead {((h1 - h0) / 4f) * 100f:0}% grade";
        }

        private static void StepWalk(Route r, float now)
        {
            if (run.Pawn == null || run.Kcc == null || run.Kcc.Character == null)
            {
                Record(r, "no KCC player in the scene", now);
                return;
            }
            ExampleCharacterController ch = run.Kcc.Character;
            Transform body = run.Pawn.Body;
            if (run.Phase == 0)
            {
                Vector2 a = r.Pts[0], b = r.Pts[1];
                float yaw = Mathf.Atan2(b.x - a.x, b.y - a.y) * Mathf.Rad2Deg;
                if (!run.Pawn.Controlled) run.Pawn.SetControlled(true);
                if (run.Kcc.enabled)
                {
                    run.Kcc.enabled = false;
                    run.Disabled.Add(run.Kcc);
                }
                run.Pawn.Teleport(new Vector3(a.x, H(a.x, a.y) + 0.3f, a.y), yaw);
                var stop = new PlayerCharacterInputs { CameraRotation = Quaternion.Euler(0f, yaw, 0f) };
                ch.SetInputs(ref stop);
                run.Phase = 1;
                run.PhaseStart = now;
                return;
            }
            if (run.Phase == 1)
            {
                if (now - run.PhaseStart < 1f) return;
                BeginRoute(r, now);
                run.Last = body.position;
                run.ProgressAt = body.position;
                run.Phase = 2;
                return;
            }
            Vector3 pos = body.position;
            if(r.Name.StartsWith("c_"))run.ContactTrace.Add(FormattableString.Invariant($"{now-run.Start:F4},{pos.x:F5},{pos.y:F5},{pos.z:F5}"));
            var p2 = new Vector2(pos.x, pos.z);
            Project(r, p2, out float s, out float lat);
            float total = run.Cum[run.Cum.Length - 1];
            Vector2 target = PointAt(r, s + 1.6f);
            Vector2 to = target - p2;
            float yawTo = Mathf.Atan2(to.x, to.y) * Mathf.Rad2Deg;
            ch.MaxStableMoveSpeed = 4.7025f;
            var inputs = new PlayerCharacterInputs { MoveAxisForward = 1f, CameraRotation = Quaternion.Euler(0f, yawTo, 0f) };
            ch.SetInputs(ref inputs);
            run.Frames++;
            run.Travel += Vector2.Distance(new Vector2(run.Last.x, run.Last.z), p2);
            run.MaxClimb = Mathf.Max(run.MaxClimb, pos.y - H(r.Pts[0].x, r.Pts[0].y));
            run.Last = pos;
            run.MaxLat = Mathf.Max(run.MaxLat, lat);
            run.SumLat += lat;
            run.Samples++;
            if (Vector3.Distance(pos, run.ProgressAt) > 0.6f)
            {
                run.ProgressAt = pos;
                run.LastProgressT = now;
            }
            float timeout = r.Timeout > 0f ? r.Timeout : 15f + total / 4.7f * 2.5f;
            bool arrived = s >= total - 1.2f && Vector2.Distance(p2, r.Pts[r.Pts.Count - 1]) < 1.6f;
            if (arrived) run.Fail = null;
            else if (now - run.LastProgressT > 4f) run.Fail = $"blocked at ({pos.x:0.0}, {pos.z:0.0}) after {s:0.0} of {total:0.0} m: " + Blocking(body);
            else if (lat > 6f) run.Fail = $"pushed off the line by {lat:0.0} m at ({pos.x:0.0}, {pos.z:0.0}) after {s:0.0} m: " + Blocking(body);
            else if (pos.y < H(pos.x, pos.z) - 2f) run.Fail = $"fell through the ground at ({pos.x:0.0}, {pos.z:0.0})";
            else if (now - run.Start > timeout) run.Fail = $"timeout {timeout:0} s at ({pos.x:0.0}, {pos.z:0.0}) after {s:0.0} of {total:0.0} m";
            else return;
            var stop2 = new PlayerCharacterInputs { CameraRotation = Quaternion.Euler(0f, yawTo, 0f) };
            ch.SetInputs(ref stop2);
            Record(r, run.Fail, now, s, total);
        }

        private static void Record(Route r, string fail, float now, float s = 0f, float total = 0f)
        {
            if(r.Name.StartsWith("c_")&&r.Mode=="van"&&run.Van)
            {
                var witness=run.Van.GetComponent<G18RouteContactWitness>();
                if(witness)run.Events.Add("PhysX body contacts: "+string.Join("; ",witness.Contacts));
            }
            if(run.ContactTrace.Count>0)File.WriteAllLines(Path.Combine(OutDir,"trace_"+SessionState.GetString(Key+"label", "run")+"_"+r.Name+".csv"),new[]{"time,x,y,z"}.Concat(run.ContactTrace));
            float time = now - run.Start;
            bool passed = fail == null;
            bool asExpected = r.Expect == "block" ? !passed : r.Expect == "either" || passed;
            float avg = run.Samples > 0 ? run.SumLat / run.Samples : 0f;
            string res = passed ? "ARRIVED" : "FAILED";
            string line = r.Mode == "walk"
                ? $"{r.Name} [{r.Pilot}, walk, expect {r.Expect}]: {res} in {time:0.0} s, line {total:0.0} m, walked {run.Travel:0.0} m, max off-line {run.MaxLat:0.0} m, max rise {run.MaxClimb:0.0} m" +
                  (passed ? "" : $"; {fail}") + (asExpected ? "" : "  << NOT AS EXPECTED")
                : $"{r.Name} [{r.Pilot}, van {r.SpeedKmh:0} km/h, expect {r.Expect}]: {res} in {time:0.0} s, line {total:0} m, driven {run.Travel:0} m, avg {(time > 0 ? run.Travel / time * 3.6f : 0f):0.0} km/h, " +
                  $"max {run.MaxSpeed:0} km/h, min after 6 s {(run.MinSpeed > 900f ? 0f : run.MinSpeed):0} km/h, off-line max {run.MaxLat:0.0} / avg {avg:0.0} m, roll max {run.MaxRoll:0} deg, pitch max {run.MaxPitch:0} deg, " +
                  $"chassis clearance min {run.MinClear:0.00} m, ground contact {run.Grounded} frames, <2 wheels {run.Airborne} frames" +
                  (passed ? "" : $"; {fail}") + (run.Events.Count > 0 ? $"; events: {string.Join(" | ", run.Events)}" : "") + (asExpected ? "" : "  << NOT AS EXPECTED");
            run.Text.AppendLine(line);
            Debug.Log("[V19Pilot] " + line);
            if (!run.FirstJson) run.Json.Append(',');
            run.FirstJson = false;
            run.Json.Append(string.Format(CultureInfo.InvariantCulture,
                "{{\"name\":\"{0}\",\"mode\":\"{1}\",\"pilot\":\"{2}\",\"expect\":\"{3}\",\"result\":\"{4}\",\"as_expected\":{5},\"time_s\":{6:0.0},\"line_m\":{7:0.0},\"travel_m\":{8:0.0},\"reached_m\":{9:0.0},\"max_offline_m\":{10:0.0},\"max_roll_deg\":{11:0.0},\"max_pitch_deg\":{12:0.0},\"min_clearance_m\":{13:0.00},\"ground_contact_frames\":{14},\"airborne_frames\":{15},\"max_speed_kmh\":{16:0.0},\"min_speed_kmh\":{17:0.0},\"fail\":\"{18}\",\"events\":\"{19}\"}}",
                r.Name, r.Mode, r.Pilot, r.Expect, passed ? "arrived" : "failed", asExpected ? "true" : "false", time, total, run.Travel, passed ? total : s, run.MaxLat,
                run.MaxRoll, run.MaxPitch, run.MinClear, run.Grounded, run.Airborne, run.MaxSpeed, run.MinSpeed > 900f ? 0f : run.MinSpeed, (fail ?? "").Replace("\"", "'"),
                string.Join(" | ", run.Events).Replace("\"", "'")));
            run.Index++;
            run.Phase = 0;
            run.PhaseStart = now;
        }

        private static void Finish()
        {
            string label = SessionState.GetString(Key + "label", "run");
            try
            {
                if (run != null)
                {
                    run.Json.Append("]}");
                    Directory.CreateDirectory(OutDir);
                    File.WriteAllText(Path.Combine(OutDir, $"routes_{label}.json"), run.Json.ToString());
                    File.WriteAllText(Path.Combine(OutDir, $"routes_{label}.txt"), run.Text.ToString());
                    Debug.Log("[V19Pilot] routes " + label + "\n" + run.Text);
                    if (run.Kcc != null && run.Kcc.Character != null)
                    {
                        var stop = new PlayerCharacterInputs { CameraRotation = run.Kcc.Character.transform.rotation };
                        run.Kcc.Character.SetInputs(ref stop);
                    }
                    foreach (Behaviour b in run.Disabled)
                        if (b != null) b.enabled = true;
                    foreach (GameObject g in run.Hidden)
                        if (g != null) g.SetActive(true);
                }
            }
            finally
            {
                run = null;
                SessionState.SetBool(Key + "active", false);
                SessionState.SetString(Key + "status", "done " + label);
                EditorApplication.update -= Tick;
                Time.captureDeltaTime = 0f;
                EditorApplication.isPaused = false;
                EditorApplication.isPlaying = false;
            }
        }

        // ------------------------------------------------------------------------------------------------ probes (edit)

        // Height profile of the built ground (terrain + bridge decks) between two plan points, every `step` metres.
        public static string Profile(float x0, float z0, float x1, float z1, float step = 2f)
        {
            var sb = new StringBuilder();
            float len = Vector2.Distance(new Vector2(x0, z0), new Vector2(x1, z1));
            int n = Mathf.Max(1, Mathf.CeilToInt(len / step));
            float maxGrade = 0f, prev = float.NaN;
            for (int i = 0; i <= n; i++)
            {
                float t = (float)i / n;
                float h = H(Mathf.Lerp(x0, x1, t), Mathf.Lerp(z0, z1, t));
                sb.Append(h.ToString("0.0", CultureInfo.InvariantCulture)).Append(' ');
                if (!float.IsNaN(prev)) maxGrade = Mathf.Max(maxGrade, Mathf.Abs(h - prev) / (len / n));
                prev = h;
            }
            return $"profile ({x0:0},{z0:0})->({x1:0},{z1:0}) {len:0} m, max grade {maxGrade * 100f:0}%: {sb}";
        }

        // Grades of the built road surface along the look json centrelines of the given roads: the steepest 6 m window and
        // the 95th percentile of 2 m steps, plus the cross slope 4 m to either side of the centreline.
        public static string RoadGrades(string revision, params string[] ids)
        {
            LookData d = MapLookBuilder.Load(revision);
            var sb = new StringBuilder();
            var want = new HashSet<string>(ids);
            foreach (LookRoad r in d.roads)
            {
                if (want.Count > 0 && !want.Contains(r.id)) continue;
                float[] xy = LookGeom.Resample(r.pts, 1f, out float[] arc);
                int n = arc.Length;
                if (n < 4) continue;
                var h = new float[n];
                for (int i = 0; i < n; i++) h[i] = H(xy[2 * i], xy[2 * i + 1]);
                float max6 = 0f, at = 0f, cross = 0f;
                var steps = new List<float>();
                for (int i = 0; i < n; i++)
                {
                    int j = i;
                    while (j < n - 1 && arc[j] - arc[i] < 6f) j++;
                    if (arc[j] - arc[i] >= 5.5f)
                    {
                        float g = Mathf.Abs(h[j] - h[i]) / (arc[j] - arc[i]);
                        if (g > max6) { max6 = g; at = arc[i]; }
                    }
                    if (i + 2 < n) steps.Add(Mathf.Abs(h[i + 2] - h[i]) / Mathf.Max(0.1f, arc[i + 2] - arc[i]));
                    if (i > 0)
                    {
                        float dx = xy[2 * i] - xy[2 * i - 2], dz = xy[2 * i + 1] - xy[2 * i - 1];
                        float L = Mathf.Sqrt(dx * dx + dz * dz);
                        if (L > 1e-3f)
                        {
                            float nx = -dz / L, nz = dx / L;
                            float hl = H(xy[2 * i] + nx * 2f, xy[2 * i + 1] + nz * 2f), hr = H(xy[2 * i] - nx * 2f, xy[2 * i + 1] - nz * 2f);
                            cross = Mathf.Max(cross, Mathf.Abs(hl - hr) / 4f);
                        }
                    }
                }
                steps.Sort();
                float p95 = steps.Count > 0 ? steps[(int)(steps.Count * 0.95f)] : 0f;
                sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "{0} ({1}, {2:0} m): max grade over 6 m {3:0.0}% at {4:0} m, 95th pct of 2 m steps {5:0.0}%, max cross slope +-2 m {6:0.0}%",
                    r.id, r.cls, arc[n - 1], max6 * 100f, at, p95 * 100f, cross * 100f));
            }
            return sb.ToString();
        }

        // Ground statistics of a plan box on a `step` grid: height range, standard deviation, the share of cells steeper than
        // 25 and 45 degrees, and the largest single-step height jump (a crack or seam shows as a jump the heightmap cannot
        // make smoothly).
        public static string GroundStats(string name, float x0, float z0, float x1, float z1, float step = 1f)
        {
            float mn = float.MaxValue, mx = float.MinValue, sum = 0f, sum2 = 0f, jump = 0f;
            int n = 0, s25 = 0, s45 = 0;
            Vector2 jumpAt = Vector2.zero;
            for (float x = x0; x <= x1; x += step)
                for (float z = z0; z <= z1; z += step)
                {
                    float h = H(x, z), hx = H(x + step, z), hz = H(x, z + step);
                    mn = Mathf.Min(mn, h);
                    mx = Mathf.Max(mx, h);
                    sum += h;
                    sum2 += h * h;
                    n++;
                    float g = Mathf.Sqrt((hx - h) * (hx - h) + (hz - h) * (hz - h)) / step;
                    float deg = Mathf.Atan(g) * Mathf.Rad2Deg;
                    if (deg > 25f) s25++;
                    if (deg > 45f) s45++;
                    float j = Mathf.Max(Mathf.Abs(hx - h), Mathf.Abs(hz - h));
                    if (j > jump)
                    {
                        jump = j;
                        jumpAt = new Vector2(x, z);
                    }
                }
            float mean = sum / Mathf.Max(1, n);
            float sd = Mathf.Sqrt(Mathf.Max(0f, sum2 / Mathf.Max(1, n) - mean * mean));
            return string.Format(CultureInfo.InvariantCulture, "{0}: {1} samples at {2} m, height {3:0.00}..{4:0.00} m (range {5:0.00}), sd {6:0.00} m, slope >25 deg {7:0.0}%, >45 deg {8:0.00}%, largest {2} m step {9:0.00} m at ({10:0}, {11:0})",
                name, n, step, mn, mx, mx - mn, sd, 100f * s25 / Mathf.Max(1, n), 100f * s45 / Mathf.Max(1, n), jump, jumpAt.x, jumpAt.y);
        }
    }
}
