using System;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map
{
    // Rough grey-box of the top-down map plan for driving tests: road strips, building boxes, water, labelled points,
    // boundary walls and the van. Input is the flattened plan from ArtSource/References/Map/Greybox/flatten_plan.py.
    // The gameplay half (PlaceGameplay: van, cameras, pawn, NPC crowd, pickups, sea return) is shared with the look map's
    // play scene (Map/Look/Editor/MapLookGameplay.cs), which places it on the look's real ground instead of y = 0.
    public static class MapGreyboxBuilder
    {
        private static string Revision = "v05";
        private const string MaterialDir = "Assets/OnlyVolunteers/Map/Materials";
        private const string VanPrefab = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab";
        // Vadim's first-person KCC player (sprint, crouch, bunnyhop, long jump), instantiated as is; never edited from here.
        private const string KccPlayerPrefab = "Assets/OnlyVolunteers/Player/Prefabs/Player_KCC_Baseline.prefab";
        // NPC capture stage 1: Vadim's default grab profile (what LMB finds with), our NPC body profile and the fist.
        private const string DefaultGrabProfilePath = "Assets/OnlyVolunteers/Player/GrabPhysicsProfile.asset";
        private const string DataDir = "Assets/OnlyVolunteers/Map/Data";
        private const string NpcGrabProfilePath = DataDir + "/NpcGrabProfile.asset";
        private const string FistPath = DataDir + "/Fist.asset";

        // Who walks on foot: Vadim's real movement (default) or the third-person Sausage Buddy walker.
        internal enum PawnKind { Kcc, Buddy }

        // greybox_vNN_flat.json. Internal: the look map's gameplay scene (MapLookGameplay) places the same gameplay from it.
        [Serializable] internal sealed class Strip { public string cls; public float w; public float[] pts; }
        [Serializable] internal sealed class Box { public float x, y, w, d, a, h; public int f; public string label; }
        [Serializable] internal sealed class Tris { public float[] tris; }
        [Serializable] internal sealed class Point { public string id, label, cat; public float x, y; }
        [Serializable] internal sealed class Wall { public float[] pts; }
        [Serializable] internal sealed class Barrier { public float x, y, w, d; }
        [Serializable]
        internal sealed class Plan
        {
            public Strip[] roads, water_strips;
            public Box[] buildings;
            public Tris[] water, sea, beaches;
            public Point[] points;
            public float[] rail, bounds, tree_data, rock_data;
            public Wall[] walls;
            public Barrier[] barriers;
            public Box[] hedges;
        }

        private static readonly Dictionary<string, (float y, Color color)> RoadStyle = new()
        {
            ["dirt_shortcut"] = (0.03f, new Color(0.55f, 0.45f, 0.32f)),
            ["rural_road"] = (0.04f, new Color(0.42f, 0.42f, 0.40f)),
            ["passage"] = (0.045f, new Color(0.72f, 0.70f, 0.62f)),
            ["town_street"] = (0.05f, new Color(0.30f, 0.30f, 0.31f)),
            ["highway"] = (0.06f, new Color(0.22f, 0.22f, 0.24f)),
        };

        [MenuItem("OnlyVolunteers/Map/Build Rough Greybox v05")]
        public static void Build() => Build("v05", 0f, PawnKind.Kcc);

        // Layout x0.65, ~40% fewer generic buildings, groves/rocks filling the gaps (Fedya's first drive: too big, too empty between places).
        [MenuItem("OnlyVolunteers/Map/Build Rough Greybox v05 (scaled 0.65)")]
        public static void BuildScaled() => Build("v05_s065", 0f, PawnKind.Kcc);

        // v06: urban core redesign (3 housing complexes, townhouse old town, elite next door), ~1.6 km, groves between places.
        [MenuItem("OnlyVolunteers/Map/Build Rough Greybox v06")]
        public static void BuildV06() => Build("v06", 0f, PawnKind.Kcc);

        // Builds the newest greybox_vNN_flat.json (made by flatten_plan.py) without a code change per plan revision.
        [MenuItem("OnlyVolunteers/Map/Build Rough Greybox (latest plan)")]
        public static void BuildLatest() => BuildLatest(PawnKind.Kcc);

        // Same map, but on foot as the third-person Sausage Buddy (saved as Map_Greybox_vNN_Buddy, next to the KCC scene).
        [MenuItem("OnlyVolunteers/Map/Build Rough Greybox (latest plan, walk as Buddy)")]
        public static void BuildLatestBuddy() => BuildLatest(PawnKind.Buddy);

        private static void BuildLatest(PawnKind pawnKind)
        {
            string dir = Path.Combine(Application.dataPath, "..", "ArtSource", "References", "Map", "Greybox");
            string latest = null;
            foreach (string f in Directory.GetFiles(dir, "greybox_v*_flat.json"))
            {
                string rev = Path.GetFileName(f).Substring("greybox_".Length).Replace("_flat.json", "");
                if (rev.Contains("_")) continue;
                if (latest == null || string.CompareOrdinal(rev, latest) > 0) latest = rev;
            }
            if (latest != null) Build(latest, 0f, pawnKind);
        }

        private static void Build(string revision, float vanMaxSpeedKmh, PawnKind pawnKind)
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning("[Greybox] Exit Play mode first, then build again.");
                return;
            }
            Revision = revision;
            string ScenePath = $"Assets/OnlyVolunteers/Scenes/Map/Map_Greybox_{revision}{(pawnKind == PawnKind.Buddy ? "_Buddy" : "")}.unity";
            Plan plan = LoadPlan(Revision);
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Directory.CreateDirectory(MaterialDir);

            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.shadows = LightShadows.Soft;
            sun.intensity = 1.2f;
            sun.transform.rotation = Quaternion.Euler(50f, -35f, 0f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.57f, 0.60f);

            float x0 = plan.bounds[0], y0 = plan.bounds[1], x1 = plan.bounds[2], y1 = plan.bounds[3];
            var ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ground.name = "Ground";
            ground.transform.position = new Vector3((x0 + x1) / 2f, -0.5f, (y0 + y1) / 2f);
            ground.transform.localScale = new Vector3(x1 - x0 + 600f, 1f, y1 - y0 + 600f);
            ground.GetComponent<Renderer>().sharedMaterial = Mat("Greybox_Ground", new Color(0.47f, 0.55f, 0.40f));
            ground.isStatic = true;

            var roadsRoot = new GameObject("Roads").transform;
            foreach (var group in GroupBy(plan.roads))
            {
                (float y, Color c) style = RoadStyle.TryGetValue(group.Key, out var s) ? s : (0.05f, Color.gray);
                AddMesh(roadsRoot, $"Roads_{group.Key}", StripMesh(group.Value, style.y), Mat($"Greybox_Road_{group.Key}", style.c));
            }
            var waterMat = Mat("Greybox_Water", new Color(0.25f, 0.45f, 0.62f));
            AddMesh(roadsRoot, "Water_Rivers", StripMesh(new List<Strip>(plan.water_strips ?? new Strip[0]), 0.02f), waterMat);
            AddMesh(roadsRoot, "Water_Lake", TriMesh(plan.water, 0.02f), waterMat);
            // Beach and the out-of-bounds sea beyond it (v11+): no wall on the coast, the sea puts you back on land.
            AddMesh(roadsRoot, "Beach", TriMesh(plan.beaches, 0.015f), Mat("Greybox_Beach", new Color(0.86f, 0.79f, 0.58f)));
            SeaReturnZone seaZone = null;
            if (plan.sea != null && plan.sea.Length > 0)
            {
                AddMesh(roadsRoot, "Sea", TriMesh(plan.sea, 0.03f), Mat("Greybox_Sea", new Color(0.16f, 0.36f, 0.58f)));
                // Made here, next to the sea it belongs to, as the grey-box always did; PlaceGameplay then reuses it.
                seaZone = AddSeaReturnZone(plan.sea);
            }
            AddMesh(roadsRoot, "Railway", StripMesh(new List<Strip> { new() { w = 3f, pts = plan.rail } }, 0.07f), Mat("Greybox_Rail", new Color(0.30f, 0.24f, 0.22f)));

            var houseMat = Mat("Greybox_Building", new Color(0.78f, 0.78f, 0.76f));
            var funcMat = Mat("Greybox_Functional", new Color(0.93f, 0.62f, 0.25f));
            var buildings = new GameObject("Buildings").transform;
            foreach (Box b in plan.buildings)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = b.f == 1 ? $"F_{b.label}" : "Building";
                go.transform.SetParent(buildings, false);
                go.transform.position = new Vector3(b.x, b.h / 2f, b.y);
                go.transform.rotation = Quaternion.Euler(0f, -b.a, 0f);
                go.transform.localScale = new Vector3(Mathf.Max(1f, b.w), b.h, Mathf.Max(1f, b.d));
                go.GetComponent<Renderer>().sharedMaterial = b.f == 1 ? funcMat : houseMat;
                go.isStatic = true;
                if (b.f == 1 && !string.IsNullOrEmpty(b.label))
                    Label(go.transform.parent, b.label, new Vector3(b.x, b.h + 3f, b.y), 2.2f, Color.white);
            }

            var wallMat = Mat("Greybox_Boundary", new Color(0.20f, 0.33f, 0.20f));
            var walls = new GameObject("Boundary").transform;
            foreach (Wall w in plan.walls)
            {
                var a = new Vector3(w.pts[0], 0f, w.pts[1]);
                var c = new Vector3(w.pts[2], 0f, w.pts[3]);
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = "Wall";
                go.transform.SetParent(walls, false);
                go.transform.position = (a + c) / 2f + Vector3.up * 4f;
                go.transform.rotation = Quaternion.LookRotation(c - a);
                go.transform.localScale = new Vector3(3f, 8f, Vector3.Distance(a, c) + 3f);
                go.GetComponent<Renderer>().sharedMaterial = wallMat;
                go.isStatic = true;
            }
            var barrierMat = Mat("Greybox_DeadEnd", new Color(0.70f, 0.20f, 0.18f));
            foreach (Barrier br in plan.barriers)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = "DeadEnd";
                go.transform.SetParent(walls, false);
                go.transform.position = new Vector3(br.x, 2f, br.y);
                go.transform.localScale = new Vector3(br.w, 4f, br.d);
                go.GetComponent<Renderer>().sharedMaterial = barrierMat;
            }

            var nature = new GameObject("Vegetation").transform;
            var treeMat = Mat("Greybox_Tree", new Color(0.22f, 0.40f, 0.20f));
            var rockMat = Mat("Greybox_Rock", new Color(0.52f, 0.52f, 0.50f));
            float[] td = plan.tree_data ?? new float[0];
            for (int i = 0; i + 3 < td.Length; i += 4)
            {
                var tree = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                tree.name = "Tree";
                tree.transform.SetParent(nature, false);
                tree.transform.position = new Vector3(td[i], td[i + 3] / 2f, td[i + 1]);
                tree.transform.localScale = new Vector3(td[i + 2] * 2f, td[i + 3] / 2f, td[i + 2] * 2f);
                tree.GetComponent<Renderer>().sharedMaterial = treeMat;
                tree.isStatic = true;
            }
            float[] rd = plan.rock_data ?? new float[0];
            for (int i = 0; i + 5 < rd.Length; i += 6)
            {
                var rock = GameObject.CreatePrimitive(PrimitiveType.Cube);
                rock.name = "Rock";
                rock.transform.SetParent(nature, false);
                rock.transform.position = new Vector3(rd[i], rd[i + 3] / 2f - 0.2f, rd[i + 1]);
                rock.transform.rotation = Quaternion.Euler(0f, rd[i + 5], 0f);
                rock.transform.localScale = new Vector3(rd[i + 2], rd[i + 3], rd[i + 4]);
                rock.GetComponent<Renderer>().sharedMaterial = rockMat;
                rock.isStatic = true;
            }

            // Separators between districts as real fences (Fedya: no solid green walls); the canal needs only a railing.
            foreach (Box h in plan.hedges ?? new Box[0])
            {
                var (thickness, color) = FenceStyle(h.label);
                float height = h.h > 0f ? h.h : 2.4f;
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = $"Fence_{h.label}";
                go.transform.SetParent(nature, false);
                go.transform.position = new Vector3(h.x, height / 2f, h.y);
                go.transform.rotation = Quaternion.Euler(0f, -h.a, 0f);
                go.transform.localScale = h.w >= h.d
                    ? new Vector3(h.w, height, thickness)
                    : new Vector3(thickness, height, h.d);
                go.GetComponent<Renderer>().sharedMaterial = Mat($"Greybox_Fence_{h.label}", color);
                go.isStatic = true;
            }

            var points = new GameObject("Points").transform;
            var baseMat = Mat("Greybox_PointBase", new Color(0.80f, 0.15f, 0.15f));
            var pointMat = Mat("Greybox_PointPlace", new Color(0.15f, 0.55f, 0.60f));
            foreach (Point p in plan.points)
            {
                var pillar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                pillar.name = $"Point_{p.id}";
                pillar.transform.SetParent(points, false);
                pillar.transform.position = new Vector3(p.x, 5f, p.y);
                pillar.transform.localScale = new Vector3(1.2f, 5f, 1.2f);
                pillar.GetComponent<Renderer>().sharedMaterial = p.id.StartsWith("B") ? baseMat : pointMat;
                UnityEngine.Object.DestroyImmediate(pillar.GetComponent<Collider>());
                Label(points, $"{p.id} {p.label}", new Vector3(p.x, 12f, p.y), 3f, p.id.StartsWith("B") ? new Color(1f, 0.85f, 0.85f) : Color.white);
            }

            PlaceGameplay(new GameplaySetup
            {
                Plan = plan,
                Ground = GameplayGround.Flat,
                Pawn = pawnKind,
                Sea = plan.sea,
                SeaZone = seaZone,
                VanMaxSpeedKmh = vanMaxSpeedKmh,
            });

            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath);
            Debug.Log($"[Greybox] {Revision} (builder r{GreyboxVanSeat.CurrentBuildRevision}): {plan.roads.Length} roads, {plan.buildings.Length} buildings, {plan.points.Length} points -> {ScenePath}");
        }

        internal static string PlanPath(string revision) =>
            Path.Combine(Application.dataPath, "..", "ArtSource", "References", "Map", "Greybox", $"greybox_{revision}_flat.json");

        internal static Plan LoadPlan(string revision) => JsonUtility.FromJson<Plan>(File.ReadAllText(PlanPath(revision)));

        // Out-of-bounds sea (v11+) from the plan's sea triangles. The look map adds its surf (SeaReturnSurf) next to it.
        internal static SeaReturnZone AddSeaReturnZone(Tris[] sea)
        {
            var corners = new List<Vector2>();
            foreach (Tris t in sea)
                for (int i = 0; i + 1 < t.tris.Length; i += 2)
                    corners.Add(new Vector2(t.tris[i], t.tris[i + 1]));
            var zone = new GameObject("SeaReturnZone").AddComponent<SeaReturnZone>();
            zone.Triangles = corners.ToArray();
            return zone;
        }

        // What the gameplay stands on. This base class is the flat grey-box: y = 0 everywhere and nothing in the way but
        // the plan's building boxes (exactly what this builder always did). The look map's ground (MapLookGameplay) reads
        // its terrain, bridge decks and colliders instead and turns the checks on.
        internal class GameplayGround
        {
            public static readonly GameplayGround Flat = new();

            // On: spawn spots are tested against the scene (colliders, water), spots that fail are skipped, the van is
            // moved along its road to a free stretch and pitched with the road, the on-foot pawn steps out to a free side.
            public virtual bool Checks => false;

            // Height of what a body stands on at plan point (x, z).
            public virtual float Height(float x, float z) => 0f;

            // Height of the road surface at (x, z) for a van driving along 'dir' (plan x, z): where a road passes under a
            // bridge deck, the deck is not its surface.
            public virtual float RoadHeight(float x, float z, Vector2 dir) => Height(x, z);

            // A standing body (feet position, capsule radius and height) would overlap something or stand in water.
            public virtual bool Blocked(Vector3 feet, float radius, float height) => false;

            // An oriented box (the van's clearance) would overlap something or stand in water.
            public virtual bool Blocked(Vector3 centre, Vector3 halfExtents, Quaternion rotation) => false;
        }

        // Input of PlaceGameplay. Lighting and the environment are the caller's (the grey-box sun, MapLookLighting).
        internal sealed class GameplaySetup
        {
            public Plan Plan;
            public GameplayGround Ground = GameplayGround.Flat;
            public PawnKind Pawn = PawnKind.Kcc;
            // The plan's sea triangles (null or empty: no sea, no trackers).
            public Tris[] Sea;
            // Optional: a zone the caller already made from Sea; null = PlaceGameplay makes one.
            public SeaReturnZone SeaZone;
            public float VanMaxSpeedKmh;
            // Main Camera (van rig) and the KCC player's camera.
            public float FarClip = 3500f;
            public bool PostProcessing;
            // Static: two Buddies standing at each CrowdSpots point (the grey-box crowd, the fallback). Director: a
            // CrowdDirector with a pool of Buddies walking crowd_vNN.json instead (look map only, MapCrowdPlacer).
            public CrowdKind Crowd = CrowdKind.Static;
        }

        internal enum CrowdKind { Static, Director }

        internal sealed class GameplayResult
        {
            public GameObject Van;
            public GreyboxPawn Pawn;
            public int Npcs, Pickups, CrowdSlots;
            public CrowdDirector Director;
        }

        // NPC capsule for spawn checks (SpawnBuddy's CharacterController) and the KCC player's (prefab radius 0.5).
        private const float NpcRadius = 0.3f, NpcHeight = 1.5f, PawnRadius = 0.5f, PawnHeight = 1.8f;
        // The van's clearance in van-local space with the root on the road (render bounds 2.14 x 2.08 x 4.78 plus a
        // margin, and 1.5 m more ahead so it does not start nose to a wall), from 0.3 m above the road: kerbs and the
        // road's own camber do not count, bollards and walls do.
        private static readonly Vector3 VanClearCentre = new(0f, 1.3f, 0.75f), VanClearHalf = new(1.2f, 1.0f, 3.35f);
        private const float VanLift = 0.3f, VanAxle = 1.58f, VanSearch = 60f;

        // The gameplay half of a map scene, placed on setup.Ground: the van (driving, door rules, cargo bay, interior
        // colliders, sea tracker, trip meter F1-F8, seat, driver dummy, autopilot, cargo), Main Camera with the van rig,
        // the on-foot pawn (KCC player or Buddy walker) with sea tracker, cargo rider, inventory and the Q/LMB/E interactor,
        // the NPC grab profile, the Buddy crowd at CrowdSpots (layer NpcBody), pickups, and the sea return zone.
        internal static GameplayResult PlaceGameplay(GameplaySetup setup)
        {
            Plan plan = setup.Plan;
            GameplayGround ground = setup.Ground ?? GameplayGround.Flat;
            bool hasSea = setup.Sea != null && setup.Sea.Length > 0;
            if (hasSea && setup.SeaZone == null)
                setup.SeaZone = AddSeaReturnZone(setup.Sea);

            // Poses first, before the van exists, so the van never blocks its own spawn or the F1 spot on top of it.
            var (spawn, spawnRotation) = VanPose(plan, ground, PointPos(plan, "P02"));
            GreyboxTripMeter.Spot[] spots =
            {
                Spot(plan, ground, "P02", "P02 Двор деда"), Spot(plan, ground, "B01", "B01 Вагон"), Spot(plan, ground, "B02", "B02 Хижина"), Spot(plan, ground, "P04", "P04 Приёмка"),
                Spot(plan, ground, "B03", "B03 Гараж (спальник)"), Spot(plan, ground, "CLOCK_SQUARE", "Площадь (старый город)"), Spot(plan, ground, "P08", "P08 Больница"), Spot(plan, ground, "B05", "B05 Промкомплекс"),
            };
            // With ground checks, where F1-F8 put the pawn on foot: a free place next to the van's pose at each spot,
            // found before the van exists (it must not block the P02 spot under it).
            Vector3[] spotFeet = ground.Checks ? SpotFeet(ground, spots) : null;
            var van = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefab));
            van.transform.SetPositionAndRotation(spawn, spawnRotation);
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = setup.FarClip;
            cam.fieldOfView = 70f;
            var listener = camGo.AddComponent<AudioListener>();
            var rig = camGo.AddComponent<VanCameraRig>();
            rig.Van = van.transform;
            rig.DriverEye = FindDeep(van.transform, "SOCKET_DriverEye");
            if (setup.VanMaxSpeedKmh > 0f)
                van.GetComponent<VanController>().MaxSpeedKmh = setup.VanMaxSpeedKmh;
            if (!van.TryGetComponent(out VanDriveInput input))
                input = van.AddComponent<VanDriveInput>();
            // The cargo bay as a carrier (players ride in it, NPC bodies load into it), and the extra van colliders: steps
            // under the cargo doors, the cab partition, thicker walls, every van collider on layer Vehicle (built at runtime,
            // VanInteriorColliders.Awake). Newer Van.prefabs already have both.
            if (!van.TryGetComponent(out VanCargoSpace _))
                van.AddComponent<VanCargoSpace>();
            if (!van.TryGetComponent(out VanInteriorColliders _))
                van.AddComponent<VanInteriorColliders>();
            input.CameraRig = rig;
            // Driver door keys: 1 front left, 2 front right, 3 sliding, 4 rear pair, F all (Fedya, 2026-10-05: as before stage 1).
            input.GreyboxDoorRules = true;
            if (hasSea)
                van.AddComponent<SeaReturnTracker>();
            var meter = van.AddComponent<GreyboxTripMeter>();
            meter.Spots = spots;
            if (spotFeet != null)
                van.AddComponent<GreyboxTripFootSpots>().Positions = spotFeet;

            // Fedya: walk around on foot (Vadim's KCC player by default, or the Sausage Buddy), get into the van with E,
            // and meet crowd Buddies around town.
            GameObject[] buddies = GreyboxBuddySetup.EnsurePrefabs();
            Vector3 footSpawn = FootSpawn(ground, van.transform);
            float footYaw = van.transform.eulerAngles.y - 90f;
            GreyboxPawn pawn = setup.Pawn == PawnKind.Kcc ? SpawnKccPlayer(footSpawn, footYaw, setup.FarClip, setup.PostProcessing) : null;
            if (pawn == null)
            {
                var walker = SpawnBuddy(buddies[0], "Player_Buddy", footSpawn, footYaw).AddComponent<GreyboxWalker>();
                walker.CameraTransform = camGo.transform;
                walker.Follow = camGo.AddComponent<GreyboxFollowCamera>();
                walker.Follow.Target = walker.transform;
                pawn = walker;
            }
            else
            {
                // The KCC player brings its own camera and listener; Main Camera wakes up only in the van (GreyboxVanSeat).
                cam.enabled = false;
                listener.enabled = false;
            }
            // The look map's light post (bloom, vignette, warmth) needs it on every camera that renders the map.
            if (setup.PostProcessing)
                cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            // Tracker and inventory go on the part that moves (the KCC root stays where it was spawned).
            GameObject body = pawn.Body.gameObject;
            if (hasSea)
                body.AddComponent<SeaReturnTracker>();
            // Crouch into the van's cargo bay and ride along (attached to the van body, no jumping inside).
            if (pawn is GreyboxKccPawn)
                body.AddComponent<GreyboxCargoRider>();
            // Offline inventory (cloud module, LocalInventory) on the pawn: E picks up, G drops, 1-8 / wheel select.
            var database = AssetDatabase.LoadAssetAtPath<ItemDatabase>(ItemDatabasePath);
            InventoryInput inventoryInput = null;
            if (database != null)
            {
                body.AddComponent<LocalInventory>().Configure(database, 6, 12, 500);
                body.AddComponent<InventoryHud>();
                inventoryInput = body.AddComponent<InventoryInput>();
                var so = new SerializedObject(inventoryInput);
                if (pawn.ViewCamera != null)
                    so.FindProperty("viewCamera").objectReferenceValue = pawn.ViewCamera;
                // E is shared with the van and the cargo doors: GreyboxInteractor decides and calls PickupNow.
                so.FindProperty("externalPickup").boolValue = true;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            var seat = van.AddComponent<GreyboxVanSeat>();
            seat.Pawn = pawn;
            seat.VanCamera = rig;
            seat.BuildRevision = GreyboxVanSeat.CurrentBuildRevision; // older scenes warn "rebuild" at Play
            meter.Seat = seat;
            // The driver, visible in the cab while someone drives (offline stand-in for the seat socket, draft A7/B7).
            var driver = van.AddComponent<GreyboxDriverDummy>();
            driver.Seat = seat;
            driver.ViewCamera = rig;
            // P: the van drives itself (15/40 km/h, S-turns) while nobody is in the driver seat, to test riding in the
            // cargo bay alone (NPC capture stage 1).
            van.AddComponent<GreyboxVanAutopilot>();
            // NPC capture stage 1 (canon section 151): Q stuns (fist, zone by hit height), LMB drags the lying body by a
            // grab point, players push it into the cargo bay by hand; no carry, load key or slots. The cargo finds its
            // doors at Play (VanDriveInput looks them up by name in Awake) and handles loading, passengers and escapes.
            var cargo = van.AddComponent<GreyboxVanCargo>();
            var interactor = body.AddComponent<GreyboxInteractor>();
            interactor.Pawn = pawn;
            interactor.Seat = seat;
            interactor.Cargo = cargo;
            interactor.InventoryInput = inventoryInput;
            interactor.Weapon = EnsureFist();
            GrabPhysicsProfile npcGrabProfile = EnsureNpcGrabProfile();

            var result = new GameplayResult { Van = van, Pawn = pawn };
            var crowd = new GameObject("NPCs").transform;
            var loot = new GameObject("Pickups").transform;
            var rnd = new System.Random(7);
            int spawned = 0;
            foreach (string id in CrowdSpots)
            {
                if (!TryPointPos(plan, id, out Vector3 centre)) continue;
                for (int k = 0; k < 2; k++)
                {
                    result.CrowdSlots++;
                    if (!FreeSpot(plan, ground, centre, rnd, out Vector3 p)) continue;
                    // With the CrowdDirector the spots are still drawn (same random sequence, so the pickups stay put),
                    // but nobody stands there.
                    GameObject prefab = buddies[spawned++ % buddies.Length];
                    float yaw = (float)rnd.NextDouble() * 360f;
                    if (setup.Crowd != CrowdKind.Static) continue;
                    var npc = SpawnCrowdNpc(prefab, $"NPC_{id}_{k}", p, yaw, npcGrabProfile, hasSea);
                    npc.transform.SetParent(crowd, true);
                    result.Npcs++;
                }
                if (database != null && database.Items.Count > 0 && database.Items[spawned % database.Items.Count] is ItemDefinition item &&
                    FreeSpot(plan, ground, centre, rnd, out Vector3 itemSpot))
                {
                    SpawnPickup(item, itemSpot, loot);
                    result.Pickups++;
                }
            }
            if (setup.Crowd == CrowdKind.Director)
            {
                UnityEngine.Object.DestroyImmediate(crowd.gameObject);
                result.Director = MapCrowdPlacer.Place(buddies, npcGrabProfile, hasSea, out int pool);
                result.Npcs = pool;
            }
            return result;
        }

        // A grey-box crowd NPC: a Buddy with its CharacterController, GreyboxNpc, the grab body and a sea tracker, on
        // layer NpcBody from the start (the Q ray, LMB and the cargo bay all look for it there).
        internal static GameObject SpawnCrowdNpc(GameObject prefab, string name, Vector3 position, float yaw, GrabPhysicsProfile grabProfile, bool sea)
        {
            var npc = SpawnBuddy(prefab, name, position, yaw);
            SetLayerRecursively(npc.transform, OvLayers.NpcBody);
            npc.AddComponent<GreyboxNpc>();
            npc.AddComponent<GreyboxNpcBody>().GrabProfile = grabProfile;
            if (sea)
                npc.AddComponent<SeaReturnTracker>();
            return npc;
        }

        private static (float thickness, Color color) FenceStyle(string material) => material switch
        {
            "concrete_fence" or "frontage_fence" => (0.25f, new Color(0.62f, 0.62f, 0.60f)),
            "wooden_fence" or "fence_rock_grove" => (0.12f, new Color(0.45f, 0.33f, 0.22f)),
            "elite_fence" or "security_fence" => (0.15f, new Color(0.18f, 0.19f, 0.20f)),
            "canal_railing" or "canal_bank" => (0.08f, new Color(0.40f, 0.42f, 0.45f)),
            "rock_scarp" => (2.5f, new Color(0.52f, 0.52f, 0.50f)),
            _ => (0.2f, new Color(0.50f, 0.50f, 0.48f)),
        };

        // Where crowd Buddies stand (two near each): courtyards, bar, den, squares, the lake, the beach and the casino exit.
        private static readonly string[] CrowdSpots =
        {
            "BAD_BLOCK", "BAD_BLOCK_2", "BAD_BLOCK_3", "P06", "P07", "BAD_CENTER", "CLOCK_SQUARE", "P05", "P10", "B04",
            "P01", "P03", "B02", "P13", "P12", "P15", "BEACH_ENTRY", "BEACH_VALLEY_ENTRY",
        };

        private const string ItemDatabasePath = "Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset";

        // Organ props made for Fedya (ArtSource/Props/*-ASTRA-*), copied into Assets for the grey-box pickups.
        private static readonly Dictionary<string, string> PickupModels = new()
        {
            ["Heart"] = "Assets/OnlyVolunteers/Props/Organs/HEART-ASTRA-007.fbx",
            ["Kidney"] = "Assets/OnlyVolunteers/Props/Organs/KIDNEY-ASTRA-001.fbx",
            ["Liver"] = "Assets/OnlyVolunteers/Props/Organs/LIVER-ASTRA-001.fbx",
            ["Lungs"] = "Assets/OnlyVolunteers/Props/Organs/LUNGS-ASTRA-001.fbx",
            ["Brain"] = "Assets/OnlyVolunteers/Props/Organs/BRAIN-ASTRA-002.fbx",
            ["Scalpel"] = "Assets/OnlyVolunteers/Props/ScalpelAstra/Model/SCALPEL-ASTRA-001.fbx",
        };

        private static void SpawnPickup(ItemDefinition item, Vector3 position, Transform parent)
        {
            var root = new GameObject($"Pickup_{item.DisplayName}");
            root.transform.SetParent(parent, false);
            root.transform.position = position + Vector3.up * 0.15f;
            root.AddComponent<OfflineWorldItem>().Set(item, 1, 0);
            GameObject visual = PickupModels.TryGetValue(item.DisplayName, out string path) && AssetDatabase.LoadAssetAtPath<GameObject>(path) is GameObject model
                ? (GameObject)PrefabUtility.InstantiatePrefab(model, root.transform)
                : GameObject.CreatePrimitive(PrimitiveType.Sphere);
            visual.transform.SetParent(root.transform, false);
            // Props come at real size (10-30 cm); fit them to about 45 cm so they read from the street.
            var bounds = new Bounds(visual.transform.position, Vector3.zero);
            foreach (Renderer r in visual.GetComponentsInChildren<Renderer>()) bounds.Encapsulate(r.bounds);
            float size = Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z);
            if (size > 0.001f) visual.transform.localScale *= 0.45f / size;
            foreach (Collider c in visual.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
            Label(root.transform, $"{item.DisplayName} — E", position + Vector3.up * 1.1f, 0.6f, new Color(1f, 0.9f, 0.6f));
        }

        private static GreyboxPawn SpawnKccPlayer(Vector3 position, float yaw, float farClip, bool postProcessing)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(KccPlayerPrefab);
            if (prefab == null)
            {
                Debug.LogWarning($"[Greybox] {KccPlayerPrefab} not found, walking as the Sausage Buddy instead.");
                return null;
            }
            var root = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            root.name = "Player_KCC";
            root.transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            // Scene override only (the prefab stays on Default): our own capsule is skipped by OvLayers.ShootMask. The KCC
            // reads its collision mask from the layer matrix in Awake (Player x everything but VehicleInterior); then
            // GreyboxKccPawn adds VehicleInterior to its motor's CollidableLayers, so it walks on the van's step ramps.
            SetLayerRecursively(root.transform, OvLayers.Player);
            var pawn = root.AddComponent<GreyboxKccPawn>();
            // Scene override only: the map is ~2 km across, the prefab camera stops at 1 km.
            if (pawn.ViewCamera != null)
            {
                pawn.ViewCamera.farClipPlane = farClip;
                if (postProcessing) pawn.ViewCamera.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            }
            AddGrabber(root);
            return pawn;
        }

        // Vadim's LMB grabber, set up as on his Player.prefab (scene override only; Player_KCC_Baseline has none). It finds
        // things with his default profile; the NPC body then hands out a grab point with NpcGrabProfile. The van (layer
        // Vehicle) is never grabbed (PhysicsGrabber.TryAcquire) but still blocks the ray, so a closed bay stays closed.
        private static void AddGrabber(GameObject kccRoot)
        {
            var input = kccRoot.GetComponent<KccFirstPersonInput>();
            if (input == null) return;
            if (!kccRoot.TryGetComponent(out PhysicsGrabber grabber))
                grabber = kccRoot.AddComponent<PhysicsGrabber>();
            var so = new SerializedObject(grabber);
            so.FindProperty("character").objectReferenceValue = input.Character;
            so.FindProperty("viewCamera").objectReferenceValue = input.ViewCamera;
            so.FindProperty("profile").objectReferenceValue = AssetDatabase.LoadAssetAtPath<GrabPhysicsProfile>(DefaultGrabProfilePath);
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        // Map/Data/NpcGrabProfile.asset: how one holder holds a point anywhere on an NPC body. Made once with the stage-1
        // numbers (200 N up/down and 220 N sideways per holder; the stunned body weighs 275 N, so one hand lifts the head
        // or the feet with the other end pivoting on the ground, but not the pelvis; two hands can); later tuning in the
        // asset is kept.
        private static GrabPhysicsProfile EnsureNpcGrabProfile()
        {
            var profile = AssetDatabase.LoadAssetAtPath<GrabPhysicsProfile>(NpcGrabProfilePath);
            if (profile != null) return profile;
            EnsureDataDir();
            profile = ScriptableObject.CreateInstance<GrabPhysicsProfile>();
            AssetDatabase.CreateAsset(profile, NpcGrabProfilePath);
            var so = new SerializedObject(profile);
            so.FindProperty("acquireDistance").floatValue = 2.2f;
            so.FindProperty("holdDistance").floatValue = 2.5f;
            so.FindProperty("springStrength").floatValue = 1200f;
            so.FindProperty("dampingRatio").floatValue = 0.6f;
            so.FindProperty("maxForce").floatValue = 200f;
            so.FindProperty("maxLinearSpeed").floatValue = 4.5f;
            so.FindProperty("maxAngularSpeed").floatValue = 8f;
            so.FindProperty("breakDistance").floatValue = 2.2f;
            so.FindProperty("soloHorizontalMaxForce").floatValue = 220f;
            // NpcBody (lying) and NpcSeated (a passenger running for a door can be grabbed too).
            so.FindProperty("acquisitionLayers").intValue = OvLayers.NpcMask;
            so.ApplyModifiedPropertiesWithoutUndo();
            AssetDatabase.SaveAssets();
            return profile;
        }

        // Map/Data/Fist.asset: Q. The WeaponStun defaults are the fist; made once, later tuning in the asset is kept.
        private static WeaponStun EnsureFist()
        {
            var fist = AssetDatabase.LoadAssetAtPath<WeaponStun>(FistPath);
            if (fist != null) return fist;
            EnsureDataDir();
            fist = ScriptableObject.CreateInstance<WeaponStun>();
            AssetDatabase.CreateAsset(fist, FistPath);
            AssetDatabase.SaveAssets();
            return fist;
        }

        private static void EnsureDataDir()
        {
            if (!AssetDatabase.IsValidFolder(DataDir))
                AssetDatabase.CreateFolder(Path.GetDirectoryName(DataDir).Replace('\\', '/'), Path.GetFileName(DataDir));
        }

        private static void SetLayerRecursively(Transform t, int layer)
        {
            t.gameObject.layer = layer;
            foreach (Transform child in t)
                SetLayerRecursively(child, layer);
        }

        private static GameObject SpawnBuddy(GameObject prefab, string name, Vector3 position, float yaw)
        {
            var root = new GameObject(name);
            root.transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            var controller = root.AddComponent<CharacterController>();
            controller.height = 1.5f;
            controller.radius = 0.3f;
            controller.center = new Vector3(0f, 0.77f, 0f);
            var body = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root.transform);
            body.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            return root;
        }

        // A spot 5-12 m from a crowd point, outside the plan's building boxes. With ground checks it also stands on the real
        // ground, clear of every collider (look props, trees, furniture, fences, other NPCs) and out of the water; blocked
        // spots are skipped and the ring widens a little per try (40 tries), so the crowd stays about as big as on the
        // grey-box where the look puts buildings or props over a point. Draws from rnd in the grey-box's order.
        private static bool FreeSpot(Plan plan, GameplayGround ground, Vector3 centre, System.Random rnd, out Vector3 spot)
        {
            int attempts = ground.Checks ? 40 : 12;
            for (int attempt = 0; attempt < attempts; attempt++)
            {
                float reach = ground.Checks ? 7f + attempt * 0.35f : 7f;
                float angle = (float)(rnd.NextDouble() * Math.PI * 2.0), radius = 5f + (float)rnd.NextDouble() * reach;
                spot = centre + new Vector3(Mathf.Cos(angle) * radius, 0f, Mathf.Sin(angle) * radius);
                if (InsideBuilding(plan, spot, 1.5f)) continue;
                if (!ground.Checks) return true;
                spot.y = ground.Height(spot.x, spot.z);
                if (!ground.Blocked(spot, NpcRadius, NpcHeight)) return true;
            }
            spot = centre;
            return false;
        }

        // Buildings are rotated by Euler(0, -a, 0), so their local X runs along (cos a, sin a) in plan space.
        private static bool InsideBuilding(Plan plan, Vector3 p, float margin)
        {
            foreach (Box b in plan.buildings)
            {
                float rad = b.a * Mathf.Deg2Rad, dx = p.x - b.x, dz = p.z - b.y;
                float lx = dx * Mathf.Cos(rad) + dz * Mathf.Sin(rad);
                float lz = -dx * Mathf.Sin(rad) + dz * Mathf.Cos(rad);
                if (Mathf.Abs(lx) < b.w / 2f + margin && Mathf.Abs(lz) < b.d / 2f + margin) return true;
            }
            return false;
        }

        private static bool TryPointPos(Plan plan, string id, out Vector3 position)
        {
            foreach (Point p in plan.points)
                if (p.id == id)
                {
                    position = new Vector3(p.x, 0f, p.y);
                    return true;
                }
            position = Vector3.zero;
            return false;
        }

        private static GreyboxTripMeter.Spot Spot(Plan plan, GameplayGround ground, string id, string name)
        {
            var (pos, yaw) = RoadSpot(plan, ground, PointPos(plan, id), out _);
            return new GreyboxTripMeter.Spot { Name = name, Position = pos, Yaw = yaw };
        }

        // The van's pose at the road nearest to 'target', lifted to drop onto its wheels.
        private static (Vector3 pos, Quaternion rotation) VanPose(Plan plan, GameplayGround ground, Vector3 target)
        {
            var (pos, yaw) = RoadSpot(plan, ground, target, out Vector3 forward);
            return ground.Checks
                ? (pos + Vector3.up * VanLift, Quaternion.LookRotation(forward, Vector3.up))
                : (pos + Vector3.up * VanLift, Quaternion.Euler(0f, yaw, 0f));
        }

        // Where the van stands on the drivable road nearest to 'target' (the plan's points sit inside buildings): the
        // nearest road point itself on the flat grey-box. With ground checks: on the road surface (deck, asphalt) and
        // sloped with it (forward), at the nearest stretch of that road, searching both ways up to VanSearch metres, where
        // the van's clearance box overlaps nothing (no prop, tree, fence, gate or building); the nearest point if none is.
        // It faces the longer way along the road: the points sit at the ends of their access roads, so the van no longer
        // starts (or lands after F1-F8) with its nose against the building, as it did on the grey-box.
        private static (Vector3 pos, float yaw) RoadSpot(Plan plan, GameplayGround ground, Vector3 target, out Vector3 forward)
        {
            var (pos, yaw) = NearestRoad(plan, target, out Strip strip, out float along);
            forward = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward;
            if (!ground.Checks || strip == null) return (pos, yaw);
            bool haveFirst = false;
            Vector3 firstPos = pos, firstForward = forward;
            float firstYaw = yaw;
            int steps = Mathf.RoundToInt(VanSearch / 2f) * 2;
            float length = StripLength(strip);
            for (int step = 0; step <= steps; step++)
            {
                // 0, +2, -2, +4, -4, ... metres along the road from the nearest point.
                float offset = (step + 1) / 2 * 2f * (step % 2 == 1 ? 1f : -1f);
                if (!AlongStrip(strip, along + offset, out Vector2 p, out Vector2 dir)) continue;
                if (along + offset > length / 2f) dir = -dir; // more road behind than ahead: turn round
                var centre = new Vector3(p.x, ground.RoadHeight(p.x, p.y, dir), p.y);
                float front = ground.RoadHeight(p.x + dir.x * VanAxle, p.y + dir.y * VanAxle, dir);
                float rear = ground.RoadHeight(p.x - dir.x * VanAxle, p.y - dir.y * VanAxle, dir);
                Vector3 fwd = new Vector3(dir.x * 2f * VanAxle, front - rear, dir.y * 2f * VanAxle).normalized;
                // The higher of the centre and the axle midpoint, so a crest or a dip does not sink a wheel into the road.
                centre.y = Mathf.Max(centre.y, (front + rear) / 2f);
                float y = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
                if (!haveFirst)
                {
                    haveFirst = true;
                    firstPos = centre;
                    firstForward = fwd;
                    firstYaw = y;
                }
                Quaternion rotation = Quaternion.LookRotation(fwd, Vector3.up);
                if (ground.Blocked(centre + rotation * VanClearCentre, VanClearHalf, rotation)) continue;
                forward = fwd;
                return (centre, y);
            }
            Debug.LogWarning($"[Greybox] No free stretch of road within {VanSearch} m of ({target.x:0}, {target.z:0}); using the nearest point.");
            forward = firstForward;
            return (firstPos, firstYaw);
        }

        // Where the on-foot pawn starts next to the van: beside the driver door (the grey-box spot, at the van's height).
        // With ground checks: on the ground there, or at the first of a few other places around the van that is free.
        private static Vector3 FootSpawn(GameplayGround ground, Transform van)
        {
            Vector3 first = van.TransformPoint(new Vector3(-2.6f, 0f, 1.5f));
            if (!ground.Checks) return first;
            Vector3[] around =
            {
                new(-2.6f, 0f, 1.5f), new(2.6f, 0f, 1.5f), new(-2.6f, 0f, -1.2f), new(2.6f, 0f, -1.2f),
                new(0f, 0f, -4.6f), new(0f, 0f, 4.6f), new(-4f, 0f, 1.5f), new(4f, 0f, 1.5f),
            };
            foreach (Vector3 local in around)
            {
                Vector3 p = van.TransformPoint(local);
                p.y = ground.Height(p.x, p.z);
                if (!ground.Blocked(p, PawnRadius, PawnHeight)) return p + Vector3.up * 0.1f;
            }
            first.y = ground.Height(first.x, first.z) + 0.1f;
            return first;
        }

        // F1-F8 on foot with ground checks: the grey-box's place (4 m right of the spot) if it is free, else the first free one
        // of FootSpawn's places around a van standing at the spot (look buildings are hollow shells, walls stand by the road).
        private static Vector3[] SpotFeet(GameplayGround ground, GreyboxTripMeter.Spot[] spots)
        {
            Vector3[] around =
            {
                new(4f, 0f, 0f), new(-2.6f, 0f, 1.5f), new(2.6f, 0f, 1.5f), new(-2.6f, 0f, -1.2f), new(2.6f, 0f, -1.2f),
                new(0f, 0f, -4.6f), new(0f, 0f, 4.6f), new(-4f, 0f, 1.5f), new(4f, 0f, 1.5f),
            };
            var feet = new Vector3[spots.Length];
            for (int s = 0; s < spots.Length; s++)
            {
                Quaternion rotation = Quaternion.Euler(0f, spots[s].Yaw, 0f);
                Vector3 first = Vector3.zero;
                bool found = false;
                foreach (Vector3 local in around)
                {
                    Vector3 p = spots[s].Position + rotation * local;
                    p.y = ground.Height(p.x, p.z);
                    if (local == around[0]) first = p;
                    if (ground.Blocked(p, PawnRadius, PawnHeight)) continue;
                    feet[s] = p + Vector3.up * 0.1f;
                    found = true;
                    break;
                }
                if (found) continue;
                Debug.LogWarning($"[Greybox] F{s + 1} {spots[s].Name}: no free place on foot next to the spot; using 4 m to its right.");
                feet[s] = first + Vector3.up * 0.1f;
            }
            return feet;
        }

        // Points of the plan sit inside buildings, so spawns and teleports snap to the nearest drivable road.
        // Also returns the strip the point lies on and how far along it (metres from the strip's first point).
        private static (Vector3 pos, float yaw) NearestRoad(Plan plan, Vector3 target, out Strip strip, out float along)
        {
            var t = new Vector2(target.x, target.z);
            float best = float.MaxValue;
            Vector2 bestPos = t, bestDir = Vector2.up;
            strip = null;
            along = 0f;
            foreach (Strip s in plan.roads)
            {
                if (s.cls == "passage") continue;
                float run = 0f;
                for (int i = 0; i + 1 < s.pts.Length / 2; i++)
                {
                    Vector2 a = P(s, i), b = P(s, i + 1), ab = b - a;
                    float len2 = ab.sqrMagnitude;
                    if (len2 < 0.01f) continue;
                    Vector2 q = a + ab * Mathf.Clamp01(Vector2.Dot(t - a, ab) / len2);
                    float d = (q - t).sqrMagnitude;
                    if (d < best)
                    {
                        best = d;
                        bestPos = q;
                        bestDir = ab.normalized;
                        strip = s;
                        along = run + Vector2.Distance(a, q);
                    }
                    run += Mathf.Sqrt(len2);
                }
            }
            return (new Vector3(bestPos.x, 0f, bestPos.y), Mathf.Atan2(bestDir.x, bestDir.y) * Mathf.Rad2Deg);
        }

        // The point 'distance' metres along a strip and the strip's direction there; false past either end. Skips the
        // same degenerate segments as NearestRoad, so 'along' from there means the same place here.
        private static bool AlongStrip(Strip s, float distance, out Vector2 pos, out Vector2 dir)
        {
            pos = Vector2.zero;
            dir = Vector2.up;
            if (distance < 0f) return false;
            for (int i = 0; i + 1 < s.pts.Length / 2; i++)
            {
                Vector2 a = P(s, i), b = P(s, i + 1), ab = b - a;
                float len2 = ab.sqrMagnitude;
                if (len2 < 0.01f) continue;
                float len = Mathf.Sqrt(len2);
                if (distance <= len)
                {
                    dir = ab / len;
                    pos = a + dir * distance;
                    return true;
                }
                distance -= len;
            }
            return false;
        }

        private static float StripLength(Strip s)
        {
            float total = 0f;
            for (int i = 0; i + 1 < s.pts.Length / 2; i++)
            {
                float len2 = (P(s, i + 1) - P(s, i)).sqrMagnitude;
                if (len2 >= 0.01f) total += Mathf.Sqrt(len2);
            }
            return total;
        }

        private static Vector3 PointPos(Plan plan, string id)
        {
            foreach (Point p in plan.points)
                if (p.id == id)
                    return new Vector3(p.x, 0f, p.y);
            return new Vector3((plan.bounds[0] + plan.bounds[2]) / 2f, 0f, (plan.bounds[1] + plan.bounds[3]) / 2f);
        }

        private static Dictionary<string, List<Strip>> GroupBy(Strip[] strips)
        {
            var d = new Dictionary<string, List<Strip>>();
            foreach (Strip s in strips)
            {
                if (!d.TryGetValue(s.cls, out var list)) d[s.cls] = list = new List<Strip>();
                list.Add(s);
            }
            return d;
        }

        // One continuous ribbon per polyline; vertex normals are averaged at joints so turns do not leave gaps.
        private static Mesh StripMesh(List<Strip> strips, float y)
        {
            var verts = new List<Vector3>();
            var tris = new List<int>();
            foreach (Strip s in strips)
            {
                int n = s.pts.Length / 2;
                if (n < 2) continue;
                int start = verts.Count;
                for (int i = 0; i < n; i++)
                {
                    Vector2 prev = P(s, Mathf.Max(0, i - 1)), next = P(s, Mathf.Min(n - 1, i + 1));
                    Vector2 dir = (next - prev).normalized;
                    var side = new Vector3(-dir.y, 0f, dir.x) * (s.w / 2f);
                    Vector2 c = P(s, i);
                    verts.Add(new Vector3(c.x, y, c.y) + side);
                    verts.Add(new Vector3(c.x, y, c.y) - side);
                    if (i == 0) continue;
                    int a = start + (i - 1) * 2;
                    tris.AddRange(new[] { a, a + 2, a + 1, a + 1, a + 2, a + 3 });
                }
            }
            return Finish(verts, tris);
        }

        private static Mesh TriMesh(Tris[] water, float y)
        {
            var verts = new List<Vector3>();
            var tris = new List<int>();
            foreach (Tris t in water ?? new Tris[0])
                for (int i = 0; i + 1 < t.tris.Length; i += 2)
                {
                    tris.Add(verts.Count);
                    verts.Add(new Vector3(t.tris[i], y, t.tris[i + 1]));
                }
            // Ear clipping emits counter-clockwise triangles in plan space; flip so they face up in Unity.
            for (int i = 0; i + 2 < tris.Count; i += 3)
                (tris[i + 1], tris[i + 2]) = (tris[i + 2], tris[i + 1]);
            return Finish(verts, tris);
        }

        private static Vector2 P(Strip s, int i) => new(s.pts[2 * i], s.pts[2 * i + 1]);

        private static Mesh Finish(List<Vector3> verts, List<int> tris)
        {
            var mesh = new Mesh { indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(verts);
            mesh.SetTriangles(tris, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        private static void AddMesh(Transform parent, string name, Mesh mesh, Material mat)
        {
            if (mesh.vertexCount == 0) return;
            string path = $"{MaterialDir}/{name}_{Revision}.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            go.isStatic = true;
        }

        private static Material Mat(string name, Color color)
        {
            string path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.1f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static void Label(Transform parent, string text, Vector3 pos, float size, Color color)
        {
            var go = new GameObject($"Label_{text}");
            go.transform.SetParent(parent, false);
            go.transform.position = pos;
            var tm = go.AddComponent<TextMesh>();
            tm.text = text;
            tm.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            go.GetComponent<MeshRenderer>().sharedMaterial = tm.font.material;
            tm.fontSize = 48;
            tm.characterSize = size * 0.1f;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.color = color;
            go.AddComponent<GreyboxBillboard>();
        }

        private static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            foreach (Transform child in root)
            {
                Transform hit = FindDeep(child, name);
                if (hit != null) return hit;
            }
            return null;
        }
    }
}
