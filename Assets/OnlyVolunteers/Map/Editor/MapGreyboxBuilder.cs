using System;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map
{
    // Rough grey-box of the top-down map plan for driving tests: road strips, building boxes, water, labelled points,
    // boundary walls and the van. Input is the flattened plan from ArtSource/References/Map/Greybox/flatten_plan.py.
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
        private enum PawnKind { Kcc, Buddy }

        [Serializable] private sealed class Strip { public string cls; public float w; public float[] pts; }
        [Serializable] private sealed class Box { public float x, y, w, d, a, h; public int f; public string label; }
        [Serializable] private sealed class Tris { public float[] tris; }
        [Serializable] private sealed class Point { public string id, label, cat; public float x, y; }
        [Serializable] private sealed class Wall { public float[] pts; }
        [Serializable] private sealed class Barrier { public float x, y, w, d; }
        [Serializable]
        private sealed class Plan
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
            string flatPath = Path.Combine(Application.dataPath, "..", "ArtSource", "References", "Map", "Greybox", $"greybox_{Revision}_flat.json");
            Plan plan = JsonUtility.FromJson<Plan>(File.ReadAllText(flatPath));
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
            bool hasSea = plan.sea != null && plan.sea.Length > 0;
            if (hasSea)
            {
                AddMesh(roadsRoot, "Sea", TriMesh(plan.sea, 0.03f), Mat("Greybox_Sea", new Color(0.16f, 0.36f, 0.58f)));
                var corners = new List<Vector2>();
                foreach (Tris t in plan.sea)
                    for (int i = 0; i + 1 < t.tris.Length; i += 2)
                        corners.Add(new Vector2(t.tris[i], t.tris[i + 1]));
                new GameObject("SeaReturnZone").AddComponent<SeaReturnZone>().Triangles = corners.ToArray();
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

            var (spawn, spawnYaw) = NearestRoad(plan, PointPos(plan, "P02"));
            var van = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefab));
            van.transform.SetPositionAndRotation(spawn + Vector3.up * 0.3f, Quaternion.Euler(0f, spawnYaw, 0f));
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 3500f;
            cam.fieldOfView = 70f;
            var listener = camGo.AddComponent<AudioListener>();
            var rig = camGo.AddComponent<VanCameraRig>();
            rig.Van = van.transform;
            rig.DriverEye = FindDeep(van.transform, "SOCKET_DriverEye");
            if (vanMaxSpeedKmh > 0f)
                van.GetComponent<VanController>().MaxSpeedKmh = vanMaxSpeedKmh;
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
            // Driver rules (canon section 151): 3 opens/closes the sliding door, the rear doors open by hand only.
            input.GreyboxDoorRules = true;
            if (hasSea)
                van.AddComponent<SeaReturnTracker>();
            var meter = van.AddComponent<GreyboxTripMeter>();
            meter.Spots = new[]
            {
                Spot(plan, "P02", "P02 Двор деда"), Spot(plan, "B01", "B01 Вагон"), Spot(plan, "B02", "B02 Хижина"), Spot(plan, "P04", "P04 Приёмка"),
                Spot(plan, "B03", "B03 Гараж (спальник)"), Spot(plan, "CLOCK_SQUARE", "Площадь (старый город)"), Spot(plan, "P08", "P08 Больница"), Spot(plan, "B05", "B05 Промкомплекс"),
            };

            // Fedya: walk around on foot (Vadim's KCC player by default, or the Sausage Buddy), get into the van with E,
            // and meet crowd Buddies around town.
            GameObject[] buddies = GreyboxBuddySetup.EnsurePrefabs();
            Vector3 footSpawn = van.transform.TransformPoint(new Vector3(-2.6f, 0f, 1.5f));
            float footYaw = van.transform.eulerAngles.y - 90f;
            GreyboxPawn pawn = pawnKind == PawnKind.Kcc ? SpawnKccPlayer(footSpawn, footYaw) : null;
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

            var crowd = new GameObject("NPCs").transform;
            var loot = new GameObject("Pickups").transform;
            var rnd = new System.Random(7);
            int spawned = 0;
            foreach (string id in CrowdSpots)
            {
                if (!TryPointPos(plan, id, out Vector3 centre)) continue;
                for (int k = 0; k < 2; k++)
                {
                    if (!FreeSpot(plan, centre, rnd, out Vector3 p)) continue;
                    var npc = SpawnBuddy(buddies[spawned++ % buddies.Length], $"NPC_{id}_{k}", p, (float)rnd.NextDouble() * 360f);
                    npc.transform.SetParent(crowd, true);
                    // Layer NpcBody from the start: the Q ray, LMB and the cargo bay all look for it there.
                    SetLayerRecursively(npc.transform, OvLayers.NpcBody);
                    npc.AddComponent<GreyboxNpc>();
                    npc.AddComponent<GreyboxNpcBody>().GrabProfile = npcGrabProfile;
                    if (hasSea)
                        npc.AddComponent<SeaReturnTracker>();
                }
                if (database != null && database.Items.Count > 0 && database.Items[spawned % database.Items.Count] is ItemDefinition item &&
                    FreeSpot(plan, centre, rnd, out Vector3 itemSpot))
                    SpawnPickup(item, itemSpot, loot);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath);
            Debug.Log($"[Greybox] {Revision} (builder r{GreyboxVanSeat.CurrentBuildRevision}): {plan.roads.Length} roads, {plan.buildings.Length} buildings, {plan.points.Length} points -> {ScenePath}");
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

        private static GreyboxPawn SpawnKccPlayer(Vector3 position, float yaw)
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
            // reads its collision mask from the layer matrix in Awake; Player still collides with everything but
            // VehicleInterior.
            SetLayerRecursively(root.transform, OvLayers.Player);
            var pawn = root.AddComponent<GreyboxKccPawn>();
            // Scene override only: the map is ~2 km across, the prefab camera stops at 1 km.
            if (pawn.ViewCamera != null) pawn.ViewCamera.farClipPlane = 3500f;
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

        // Map/Data/NpcGrabProfile.asset: how one holder holds one grab point of an NPC body. Made once with the stage-1
        // numbers (350 N per holder: one drags with the heels on the ground, two lift); later tuning in the asset is kept.
        private static GrabPhysicsProfile EnsureNpcGrabProfile()
        {
            var profile = AssetDatabase.LoadAssetAtPath<GrabPhysicsProfile>(NpcGrabProfilePath);
            if (profile != null) return profile;
            EnsureDataDir();
            profile = ScriptableObject.CreateInstance<GrabPhysicsProfile>();
            AssetDatabase.CreateAsset(profile, NpcGrabProfilePath);
            var so = new SerializedObject(profile);
            so.FindProperty("acquireDistance").floatValue = 2.2f;
            so.FindProperty("holdDistance").floatValue = 1.2f;
            so.FindProperty("springStrength").floatValue = 600f;
            so.FindProperty("dampingRatio").floatValue = 1f;
            so.FindProperty("maxForce").floatValue = 350f;
            so.FindProperty("maxLinearSpeed").floatValue = 4.5f;
            so.FindProperty("maxAngularSpeed").floatValue = 8f;
            so.FindProperty("breakDistance").floatValue = 2.2f;
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

        private static bool FreeSpot(Plan plan, Vector3 centre, System.Random rnd, out Vector3 spot)
        {
            for (int attempt = 0; attempt < 12; attempt++)
            {
                float angle = (float)(rnd.NextDouble() * Math.PI * 2.0), radius = 5f + (float)rnd.NextDouble() * 7f;
                spot = centre + new Vector3(Mathf.Cos(angle) * radius, 0f, Mathf.Sin(angle) * radius);
                if (!InsideBuilding(plan, spot, 1.5f)) return true;
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

        private static GreyboxTripMeter.Spot Spot(Plan plan, string id, string name)
        {
            var (pos, yaw) = NearestRoad(plan, PointPos(plan, id));
            return new GreyboxTripMeter.Spot { Name = name, Position = pos, Yaw = yaw };
        }

        // Points of the plan sit inside buildings, so spawns and teleports snap to the nearest drivable road.
        private static (Vector3 pos, float yaw) NearestRoad(Plan plan, Vector3 target)
        {
            var t = new Vector2(target.x, target.z);
            float best = float.MaxValue;
            Vector2 bestPos = t, bestDir = Vector2.up;
            foreach (Strip s in plan.roads)
            {
                if (s.cls == "passage") continue;
                for (int i = 0; i + 1 < s.pts.Length / 2; i++)
                {
                    Vector2 a = P(s, i), b = P(s, i + 1), ab = b - a;
                    float len2 = ab.sqrMagnitude;
                    if (len2 < 0.01f) continue;
                    Vector2 q = a + ab * Mathf.Clamp01(Vector2.Dot(t - a, ab) / len2);
                    float d = (q - t).sqrMagnitude;
                    if (d < best) { best = d; bestPos = q; bestDir = ab.normalized; }
                }
            }
            return (new Vector3(bestPos.x, 0f, bestPos.y), Mathf.Atan2(bestDir.x, bestDir.y) * Mathf.Rad2Deg);
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
