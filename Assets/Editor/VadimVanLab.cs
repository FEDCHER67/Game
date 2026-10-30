using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using OnlyVolunteers.Vehicles;
using OnlyVolunteers.Vehicles.EditorTools;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>VanLab (Vadim 30.10): a minimal test scene for the van and NPC handling. A copy of the W86 play scene with the
    /// whole map removed: a flat grey floor with a 1 m grid, the van, the player, the capture/network systems, the base-2 hut,
    /// grandpa's paint table and three standing NPC. The W86 scene itself is never changed. Re-run = rebuilt from scratch.
    /// VanOnly (Vadim 30.10, V2): the same floor with only the van, the player and the sky: no NPC, no hut, no paint table.
    /// Its van is the bigger v05 (Van_v05.prefab, rebuilt here): the scene's "Van" root keeps its network/capture/seat
    /// components, only the model, colliders and wheel colliders are swapped and every reference to them follows. The
    /// player starts 6 m off the van's front-right corner looking at it; the v1 status corner (base, caught, fund) is off.</summary>
    public static class VadimVanLab
    {
        const string Src = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        public const string Dst = "Assets/OnlyVolunteers/Scenes/Dev/VanLab_v01.unity";
        public const string VanOnlyDst = "Assets/OnlyVolunteers/Scenes/Dev/VanOnly_v01.unity";
        const string Dir = "Assets/VadimLocal/VanLab";
        const string Log = @"C:\Users\chern_0eqkb03\VolunteersBuilds\vanlab_build.txt";

        // children of the world root that stay: light, sky clock, post FX
        static readonly string[] KeepWorld = { "Sun", "PostFX_v17", "G22_DayNight_v04_Integration_i03" };
        static readonly string[] KeepRoots = { "Map_W85_v02", "[Capture] Network (solo host)", "[Capture] Stage A director", "Player_KCC", "Van",
            "Main Camera", "[Capture] Base B02 — operating shed", "G20 Grandpa's paint station — B02 hut", "G20 Map paint controls",
            "G20 Map painting HUD", "Crowd", "V3_FlyToggle", "W86_Look", "[Sale] First buyer crate (SALES SG-D27, W86)", "W86_Story_Anchors" };
        static readonly string[] KeepRootsVanOnly = { "Map_W85_v02", "[Capture] Network (solo host)", "[Capture] Stage A director", "Player_KCC", "Van",
            "Main Camera", "Crowd", "V3_FlyToggle", "W86_Look" };

        public static void Run() => Make(Dst, KeepRoots, 3, "vanlab");
        public static void RunVanOnly() => Make(VanOnlyDst, KeepRootsVanOnly, 0, "vanonly", VanOnlyV05);

        static void Make(string dst, string[] keepRoots, int npcCount, string tag, System.Action<Scene, GameObject, float, StringBuilder> extra = null)
        {
            var log = new StringBuilder();
            if (File.Exists(dst)) AssetDatabase.DeleteAsset(dst);
            if (!AssetDatabase.CopyAsset(Src, dst)) throw new IOException("copy failed");
            var scene = EditorSceneManager.OpenScene(dst);
            var roots = scene.GetRootGameObjects();
            var world = roots.First(r => r.name == "Map_W85_v02");
            var van = roots.First(r => r.name == "Van");

            // floor height = the ground under the van; the floor gets the road layer (the van and the walker know it as ground)
            float floorY = van.transform.position.y;
            var vanCols = new HashSet<Collider>(van.GetComponentsInChildren<Collider>(true));
            foreach (var h in Physics.RaycastAll(van.transform.position + Vector3.up * 6f, Vector3.down, 30f).OrderBy(h => h.distance))
                if (!vanCols.Contains(h.collider)) { floorY = h.point.y; log.AppendLine($"ground under the van: {h.collider.name} y {floorY:F3}"); break; }
            var road = world.transform.Find("Roads")?.GetComponentsInChildren<Collider>(true).FirstOrDefault();
            int layer = road ? road.gameObject.layer : 0;
            log.AppendLine($"floor layer {LayerMask.LayerToName(layer)} ({layer})");

            foreach (Transform c in world.transform.Cast<Transform>().ToList())
                if (!KeepWorld.Contains(c.name)) Object.DestroyImmediate(c.gameObject);
            foreach (var r in roots)
                if (r && !keepRoots.Contains(r.name)) { log.AppendLine("removed root " + r.name); Object.DestroyImmediate(r); }

            // crowd: no district spawning; npcCount NPC stand by the van to grab
            var crowd = roots.First(r => r && r.name == "Crowd");
            var cd = crowd.GetComponent<OnlyVolunteers.Map.Crowd.CrowdDirector>();
            var pool = crowd.transform.Find("Pool");
            if (pool) foreach (Transform c in pool.Cast<Transform>().ToList()) Object.DestroyImmediate(c.gameObject);
            var templates = cd.Templates.Where(t => t && !t.name.Contains("FOREST") && !t.name.Contains("VIP") && !t.name.Contains("POLICE")).ToList();
            log.AppendLine($"crowd templates usable {templates.Count}");
            cd.enabled = false;
            var npcRoot = new GameObject("VanLab_NPCs").transform;
            Vector3 side = -van.transform.right, fwd = van.transform.forward;
            for (int i = 0; i < npcCount && i < templates.Count; i++)
            {
                var t = templates[(i * 7) % templates.Count];
                var g = Object.Instantiate(t, npcRoot);
                g.name = "VanLab_NPC_" + i + "_" + t.name.Replace("CrowdTemplate_", "");
                var p = van.transform.position + side * 5f + fwd * (i - 1) * 2.5f; p.y = floorY;
                g.transform.SetPositionAndRotation(p, Quaternion.LookRotation(-side, Vector3.up));
                g.SetActive(true);
                log.AppendLine($"npc {g.name} at {p}");
            }

            // flat floor 1 km with a 1 m grid
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "VanLab_Floor (1 km, grid 1 m)";
            floor.transform.position = new Vector3(van.transform.position.x, floorY, van.transform.position.z);
            floor.transform.localScale = new Vector3(100f, 1f, 100f);
            floor.layer = layer;
            floor.GetComponent<MeshRenderer>().sharedMaterial = FloorMaterial();
            floor.isStatic = true;

            // own save file, so the W86 world save never moves the van off the floor
            var dir = roots.First(r => r && r.name == "[Capture] Stage A director");
            foreach (var mb in dir.GetComponents<MonoBehaviour>())
            {
                var so = new SerializedObject(mb);
                var p1 = so.FindProperty("SaveFileName"); if (p1 != null) { p1.stringValue = $"capture_{tag}_v01.json"; log.AppendLine($"save file -> capture_{tag}_v01.json"); }
                var p2 = so.FindProperty("EditorSlot"); if (p2 != null) p2.stringValue = $"capture_{tag}_editor_v01.json";
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            extra?.Invoke(scene, van, floorY, log);
            RenderSettings.fog = false;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            log.AppendLine("saved " + dst);
            File.WriteAllText(Log.Replace("vanlab", tag), log.ToString());
        }

        // ------------------------------------------------------------------ VanOnly: the v05 van
        static void VanOnlyV05(Scene scene, GameObject van, float floorY, StringBuilder log)
        {
            van.transform.position = new Vector3(van.transform.position.x, floorY + 0.05f, van.transform.position.z);
            SwapVanModel(van, VanSetupBuilder.BuildV05Prefab(), log);

            // geometry numbers that live on the van's scene components (v05, van-root space z = 0.2516 - Blender y; see
            // VanSetupBuilder.V05: the root sits at the wheelbase centre, which the longer cargo section moved 0.275 m back)
            var seat = van.GetComponent<OnlyVolunteers.Map.GreyboxVanSeat>();
            if (seat) seat.DoorPoint = new Vector3(-1.741f, 0f, 0.967f);
            var dummy = van.GetComponent<OnlyVolunteers.Map.GreyboxDriverDummy>();
            if (dummy)
            {
                dummy.SeatPoint = new Vector3(-0.552f, 1.201f, 1.165f);
                dummy.HeadPoint = new Vector3(-0.552f, 1.979f, 1.095f);
                dummy.WheelFallback = new Vector3(-0.552f, 1.385f, 1.775f);
            }
            // the two mist headlamps follow the headlights (v02 -0.61 / 0.86 / 2.30 -> v05 -0.70 / 0.97 / 2.97)
            foreach (Transform t in van.transform)
                if (t.name == "V19_MistHeadlamp")
                {
                    Vector3 p = t.localPosition;
                    t.localPosition = p + new Vector3(Mathf.Sign(p.x) * 0.092f, 0.111f, 0.664f);
                    log.AppendLine($"headlamp {p} -> {t.localPosition}");
                }
            // the bigger van: the chase camera further back and higher, so the road shows over the 2.6 m roof and 6.15 m length
            foreach (var rig in Object.FindObjectsByType<VanCameraRig>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                rig.ChaseDistance = 9.0f;
                rig.ChaseHeight = 3.4f;
                rig.ChaseLookHeight = 1.5f;
                log.AppendLine($"chase camera {rig.name}: 9.0 m back, 3.4 m high, looking at 1.5 m; driver eye {(rig.DriverEye ? rig.DriverEye.name : "none")}");
            }

            // capture director: no v1 status corner, no "catch someone in Khutor" objective, its own save file (the old one held
            // the v02 van and the old spawn)
            var dir = scene.GetRootGameObjects().First(r => r.name == "[Capture] Stage A director");
            foreach (var mb in dir.GetComponents<MonoBehaviour>())
            {
                var so = new SerializedObject(mb);
                var hud = so.FindProperty("ShowStatusCorner"); if (hud != null) { hud.boolValue = false; log.AppendLine("status corner off"); }
                var goal = so.FindProperty("NewGameObjective"); if (goal != null) { goal.stringValue = ""; log.AppendLine("new-game objective off"); }
                var p1 = so.FindProperty("SaveFileName"); if (p1 != null) p1.stringValue = "capture_vanonly_v05.json";
                var p2 = so.FindProperty("EditorSlot"); if (p2 != null) p2.stringValue = "capture_vanonly_editor_v05.json";
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            // trip meter: no F1-F8 teleports (they lead to W86 map spots, none of which exist here) and no list of them;
            // the trip readout and T stay
            var trip = van.GetComponent<OnlyVolunteers.Map.GreyboxTripMeter>();
            if (trip)
            {
                log.AppendLine($"trip meter: {trip.Spots.Length} teleport spots removed");
                trip.Spots = new OnlyVolunteers.Map.GreyboxTripMeter.Spot[0];
                EditorUtility.SetDirty(trip);
            }

            // the player: on the floor, 6 m from the van centre off its front-right corner, facing the van
            var player = scene.GetRootGameObjects().First(r => r.name == "Player_KCC");
            Transform feet = player.GetComponentsInChildren<Component>(true).FirstOrDefault(c => c && c.GetType().Name == "KinematicCharacterMotor")?.transform ?? player.transform;
            Vector3 fwd = Vector3.ProjectOnPlane(van.transform.forward, Vector3.up).normalized;
            Vector3 right = Vector3.ProjectOnPlane(van.transform.right, Vector3.up).normalized;
            Vector3 target = van.transform.position + (fwd + right).normalized * 6f;
            target.y = floorY + 0.05f;
            Vector3 look = van.transform.position - target; look.y = 0f;
            player.transform.RotateAround(feet.position, Vector3.up, Mathf.DeltaAngle(feet.eulerAngles.y, Quaternion.LookRotation(look).eulerAngles.y));
            player.transform.position += target - feet.position;
            log.AppendLine($"player feet {feet.position} yaw {feet.eulerAngles.y:F1} (van {van.transform.position}, yaw {van.transform.eulerAngles.y:F1})");

            // FPS (measured 30.10: the raymarched G22 sky is 13-30 ms of GPU at 4K, everything else ~2.5 ms): the scene's static
            // sky is rendered once into six faces at start and shown as a lookup (VanOnlySkyCache)
            string skyMatPath = Dir + "/VanOnlySkyCached_v01.mat";
            var skyMat = AssetDatabase.LoadAssetAtPath<Material>(skyMatPath);
            if (!skyMat)
            {
                skyMat = new Material(Shader.Find("VadimLocal/VanOnly Sky Cached"));
                AssetDatabase.CreateAsset(skyMat, skyMatPath);
            }
            var skyCache = new GameObject("VanOnly sky cache (the static sky baked into 6 faces at start)");
            SceneManager.MoveGameObjectToScene(skyCache, scene);
            skyCache.AddComponent<VanOnlySkyCache>().CachedSky = skyMat;
            log.AppendLine($"sky cache -> {skyMatPath} (shader {skyMat.shader.name})");
            // scripted tests from inside the build (-vanTest shots / fps / roof); idle without the argument
            var test = new GameObject("VanOnly test mode (idle unless started with -vanTest)");
            SceneManager.MoveGameObjectToScene(test, scene);
            test.AddComponent<VanOnlyTestMode>();

            // flicker check: nothing flat may lie in the floor's plane (z-fighting); such surfaces are switched off here
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (r.transform.IsChildOf(van.transform) || r.transform.IsChildOf(player.transform) || r.name.StartsWith("VanLab_Floor")) continue;
                Bounds b = r.bounds;
                if (b.size.y < 0.06f && Mathf.Abs(b.center.y - floorY) < 0.04f && b.size.x * b.size.z > 1f)
                {
                    log.AppendLine($"coplanar with the floor, switched off: {r.name} ({b.center}, {b.size})");
                    r.enabled = false;
                }
            }

            // headroom check: the 1.8 m player capsule (r 0.35) standing on the cargo floor touches no van collider (at
            // +-0.55 m off the centre line it touches the leaning upper walls; the 9 cm rear door sill is at z -2.79)
            Physics.SyncTransforms();
            int mask = ~0;
            foreach (string l in new[] { "VehicleInterior", "NpcSlide", "Player" })
            {
                int i = LayerMask.NameToLayer(l);
                if (i >= 0) mask &= ~(1 << i);
            }
            foreach (Vector3 local in new[] { new Vector3(0f, 0.5566f, -1.0f), new Vector3(0.45f, 0.5566f, -0.2f), new Vector3(-0.45f, 0.5566f, -0.2f), new Vector3(0f, 0.5566f, -2.4f) })
            {
                Vector3 foot = van.transform.TransformPoint(local + Vector3.up * 0.01f);
                bool blocked = Physics.CheckCapsule(foot + Vector3.up * 0.35f, foot + Vector3.up * (1.8f - 0.35f), 0.35f, mask, QueryTriggerInteraction.Ignore);
                string up = Physics.Raycast(foot + Vector3.up * 0.1f, Vector3.up, out RaycastHit h, 5f, mask, QueryTriggerInteraction.Ignore)
                    ? $"{h.point.y - foot.y:F3} m to {h.collider.name}" : "nothing above";
                string down = Physics.Raycast(foot + Vector3.up * 0.3f, Vector3.down, out RaycastHit g, 2f, mask, QueryTriggerInteraction.Ignore)
                    ? $"{g.collider.name} at {g.point.y - van.transform.position.y:F3}" : "nothing";
                log.AppendLine($"headroom: 1.8 m capsule on the cargo floor at {local}: {(blocked ? "BLOCKED" : "fits")}; clear above the floor {up}; floor {down}");
            }
        }

        /// <summary>Puts the model, colliders and wheel colliders of 'prefab' on the scene van in place of its own. The van
        /// root and every component on it stay (network, capture, seat, cargo, input); any reference anywhere in the scene to
        /// a replaced object or component is pointed at its counterpart (same path, same component type and index).</summary>
        static void SwapVanModel(GameObject van, GameObject prefab, StringBuilder log)
        {
            if (PrefabUtility.IsPartOfPrefabInstance(van))
                PrefabUtility.UnpackPrefabInstance(van, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            var fresh = (GameObject)PrefabUtility.InstantiatePrefab(prefab, van.scene);
            PrefabUtility.UnpackPrefabInstance(fresh, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            fresh.transform.SetPositionAndRotation(van.transform.position, van.transform.rotation);

            // v02 paint (grandpa's paint station is not in this scene; the v05 model has no paint layout)
            foreach (var mb in van.GetComponents<MonoBehaviour>().Where(m => m && (m.GetType().Name == "VanPaintSurface" || m.GetType().Name == "VanPaintMeshQuery")).ToList())
            {
                log.AppendLine("removed " + mb.GetType().Name);
                Object.DestroyImmediate(mb);
            }

            var partNames = new HashSet<string>(fresh.transform.Cast<Transform>().Select(t => t.name));
            var oldParts = van.transform.Cast<Transform>().Where(t => partNames.Contains(t.name)).ToList();
            var map = new Dictionary<Object, Object>();
            foreach (Transform part in oldParts)
                foreach (Transform o in part.GetComponentsInChildren<Transform>(true))
                {
                    Transform n = fresh.transform.Find(AnimationUtility.CalculateTransformPath(o, van.transform));
                    if (n == null) continue;
                    map[o.gameObject] = n.gameObject;
                    map[o] = n;
                    foreach (Component c in o.GetComponents<Component>())
                    {
                        if (c == null || c is Transform) continue;
                        Component[] mine = o.GetComponents(c.GetType()), theirs = n.GetComponents(c.GetType());
                        int i = System.Array.IndexOf(mine, c);
                        if (i >= 0 && i < theirs.Length) map[c] = theirs[i];
                    }
                }

            int changed = 0;
            foreach (GameObject root in van.scene.GetRootGameObjects())
                foreach (Component c in root.GetComponentsInChildren<Component>(true))
                {
                    if (c == null || c is Transform || c.transform.IsChildOf(fresh.transform) || oldParts.Any(p => c.transform.IsChildOf(p))) continue;
                    var so = new SerializedObject(c);
                    var it = so.GetIterator();
                    bool any = false;
                    while (it.Next(true))
                    {
                        if (it.propertyType != SerializedPropertyType.ObjectReference || it.name == "m_GameObject" || it.name == "m_Script") continue;
                        Object v = it.objectReferenceValue;
                        if (v != null && map.TryGetValue(v, out Object nv))
                        {
                            it.objectReferenceValue = nv;
                            any = true;
                            changed++;
                            log.AppendLine($"ref {c.GetType().Name}.{it.propertyPath} on {c.name} -> v05 {nv.name}");
                        }
                    }
                    if (any) so.ApplyModifiedPropertiesWithoutUndo();
                }

            foreach (Transform t in oldParts) Object.DestroyImmediate(t.gameObject);
            foreach (Transform t in fresh.transform.Cast<Transform>().ToList()) t.SetParent(van.transform, false);
            van.GetComponent<VanCargoSpace>().LocalBox = fresh.GetComponent<VanCargoSpace>().LocalBox;
            van.GetComponent<VanController>().CenterOfMass = fresh.GetComponent<VanController>().CenterOfMass;
            var interior = van.GetComponent<VanInteriorColliders>();
            interior.ModelRevision = fresh.GetComponent<VanInteriorColliders>().ModelRevision;
            interior.Build();
            Object.DestroyImmediate(fresh);
            log.AppendLine($"van model -> {AssetDatabase.GetAssetPath(prefab)}: {oldParts.Count} parts swapped, {changed} references moved");
        }

        static Material FloorMaterial()
        {
            if (!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets/VadimLocal", "VanLab");
            string texPath = Dir + "/VanLab_Grid_v01.png", matPath = Dir + "/VanLab_Floor_v01.mat";
            if (!File.Exists(texPath))
            {
                const int n = 256; // one tile = 4 m: a darker line every 4 m, a thin line every 1 m
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, true);
                var px = new Color32[n * n];
                for (int y = 0; y < n; y++)
                    for (int x = 0; x < n; x++)
                    {
                        bool major = x < 3 || y < 3, minor = x % 64 < 1 || y % 64 < 1;
                        byte v = major ? (byte)112 : minor ? (byte)128 : (byte)138;
                        px[y * n + x] = new Color32(v, v, v, 255);
                    }
                tex.SetPixels32(px); tex.Apply();
                File.WriteAllBytes(texPath, tex.EncodeToPNG());
                AssetDatabase.ImportAsset(texPath);
            }
            var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, matPath); }
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(texPath));
            m.SetTextureScale("_BaseMap", new Vector2(250f, 250f)); // plane 1000 m / 4 m tile
            m.SetColor("_BaseColor", Color.white);
            m.SetFloat("_Smoothness", 0.1f);
            EditorUtility.SetDirty(m);
            AssetDatabase.SaveAssets();
            return m;
        }
    }
}
