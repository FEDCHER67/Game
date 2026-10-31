using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.BaseV2.EditorTools
{
    /// <summary>
    /// V2 base P1 (Fedya 31.10) placed into Vadim's hangar scene. Called by VadimHangarLab.Run (one hook line) after it
    /// built the hangar, so every regeneration of HangarLab_v01 keeps these pieces; nothing of Vadim's geometry, rooms or
    /// materials is changed (the room prefab instances only get the moving lift parts' static flags cleared in the scene).
    /// Everything goes under one root "Base_V2_P1 (Fedya)":
    ///  - BaseV2DirectorV01 (V2 workshop open, the shop purchase channel, the baton, F8 test money) + the in-build test mode;
    ///  - GEAR: the rubber baton on a display stand on the hall counter (ShopDisplayItemV2 + its outline materials), a
    ///    placeholder seller (a crowd NPC's look, all behaviour stripped: he only stands) at Anchor_Clerk;
    ///  - workshop: the dock zone over Vadim's lift, WorkshopServiceV01 driving his lift parts (travel fitted under the
    ///    beam for van v05), mechanic B (Mechanic_W86_v02, route home <-> control point, v1 talk off), the speech bubble,
    ///    WorkshopDockV2 with free exit spots; review-camera markers;
    ///  - the scene van: StartAtMax off (V2 canon: the junk van).
    /// Generated assets: Assets/OnlyVolunteers/Base/V2/Art (meshes, materials). Log: Logs/BaseV2Builder_v01.txt.
    /// Batch (regenerates the whole hangar scene through Vadim's builder):
    ///   -executeMethod OnlyVolunteers.BaseV2.EditorTools.BaseV2BuilderV01.RegenerateHangarBatch
    /// </summary>
    public static class BaseV2BuilderV01
    {
        const string Dir = "Assets/OnlyVolunteers/Base/V2";
        const string ArtDir = Dir + "/Art";
        const string MeshAsset = ArtDir + "/BaseV2_P1_Meshes_v01.asset";
        const string Shader = Dir + "/Shaders/OutlineHullV2.shader";
        const string MechanicPrefab = "Assets/OnlyVolunteers/Characters/Mechanic_W86/Mechanic_W86_v02.prefab";
        const string PuffMaterial = "Assets/OnlyVolunteers/Characters/Mechanic_W86/Fx/MechanicPuff_v01.mat";
        const string GearMatDir = "Assets/VadimLocal/Hangar/Rooms/Gear/Materials/";
        const string LiftJson = "Assets/OnlyVolunteers/Art/Buildings/Workshop_W86/Workshop_W86_lift_v01.json";
        const string LogPath = "Logs/BaseV2Builder_v01.txt";
        const uint L0 = 1u, Hall = 1u << 1, Room = 1u << 2;
        static readonly string[] Moving = { "Lift_Carriage_L_Wide", "Lift_Carriage_R_Wide", "Lift_Arms_FL_Wide", "Lift_Arms_FR_Wide", "Lift_Arms_RL_Wide", "Lift_Arms_RR_Wide" };

        static StringBuilder _log;

        static void L(string s)
        {
            _log.AppendLine(s);
            Debug.Log("[BaseV2Builder] " + s);
        }

        /// <summary>Batch: Vadim's VadimHangarLab.Run (which calls <see cref="Apply"/>); his log path is on his PC, so a
        /// failure to write it after the scene is saved is reported, not fatal.</summary>
        public static void RegenerateHangarBatch()
        {
            int code = 0;
            try { OnlyVolunteers.EditorTools.VadimHangarLab.Run(); }
            catch (Exception e)
            {
                bool afterSave = e is IOException || e is UnauthorizedAccessException;
                Debug.LogWarning("[BaseV2Builder] VadimHangarLab.Run threw " + e.GetType().Name + ": " + e.Message + (afterSave ? " (his log file on his PC; the scene was saved before)" : ""));
                if (!afterSave) { Debug.LogException(e); code = 1; }
            }
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        /// <summary>Places the V2 base P1 pieces into the open hangar scene (idempotent: the old root is replaced).</summary>
        public static void Apply(Scene scene, Transform hangar, GameObject van)
        {
            _log = new StringBuilder();
            L($"apply into {scene.path}: hangar {hangar.name} at {hangar.position}, van {(van ? van.name : "none")}");
            foreach (GameObject old in scene.GetRootGameObjects().Where(g => g.name == BaseV2Names.Root).ToList()) Object.DestroyImmediate(old);
            var root = new GameObject(BaseV2Names.Root);
            SceneManager.MoveGameObjectToScene(root, scene);
            root.transform.SetPositionAndRotation(hangar.position, hangar.rotation);
            Directory.CreateDirectory(ArtDir);
            AssetDatabase.Refresh();

            var mats = Materials();
            Mesh baton, stand;
            Meshes(out baton, out stand);
            var director = root.AddComponent<BaseV2DirectorV01>();
            director.BatonMesh = baton;
            director.BatonMaterial = mats.rubber;
            var test = new GameObject("BaseV2 test mode (idle unless started with -baseTest)");
            test.transform.SetParent(root.transform, false);
            test.AddComponent<BaseV2TestModeV01>();

            Physics.SyncTransforms();
            try { Shop(hangar, root.transform, mats, baton, stand); } catch (Exception e) { L("GEAR shop FAILED: " + e); }
            try { Workshop(hangar, root.transform, van, mats); } catch (Exception e) { L("workshop FAILED: " + e); }

            if (van != null && van.TryGetComponent(out VanUpgrades up))
            {
                up.StartAtMax = false;
                EditorUtility.SetDirty(up);
                L("scene van: StartAtMax off (V2 canon: the junk van; the paid tiers drive it)");
            }
            EditorSceneManager.MarkSceneDirty(scene);
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath));
            File.WriteAllText(LogPath, _log.ToString());
        }

        // ================================================================== assets

        struct Mats { public Material rubber, steel, standBoard, outline, halo, bubble, bubbleText; }

        static Material LitMat(string name, Color c, float smooth, float metal)
        {
            string path = $"{ArtDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(UnityEngine.Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Smoothness", smooth);
            m.SetFloat("_Metallic", metal);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Mats Materials()
        {
            var m = new Mats
            {
                rubber = LitMat("BaseV2_BatonRubber_v01", new Color(0.075f, 0.075f, 0.08f), 0.22f, 0f),
                steel = LitMat("BaseV2_BatonSteel_v01", new Color(0.42f, 0.42f, 0.4f), 0.3f, 0.6f),
            };
            m.standBoard = AssetDatabase.LoadAssetAtPath<Material>(GearMatDir + "GEAR_DarkTan_v01.mat") ?? LitMat("BaseV2_Stand_v01", new Color(0.55f, 0.48f, 0.34f), 0.15f, 0f);
            var sh = AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(Shader);
            if (sh == null) throw new FileNotFoundException("outline shader missing: " + Shader);
            m.outline = OutlineMat("BaseV2_OutlineLine_v01", sh, 0.007f, false);
            m.halo = OutlineMat("BaseV2_OutlineHalo_v01", sh, 0.02f, true);
            string bp = $"{ArtDir}/BaseV2_Bubble_v01.mat";
            m.bubble = AssetDatabase.LoadAssetAtPath<Material>(bp);
            if (!m.bubble) { m.bubble = new Material(UnityEngine.Shader.Find("Universal Render Pipeline/Unlit")); AssetDatabase.CreateAsset(m.bubble, bp); }
            m.bubble.SetColor("_BaseColor", new Color(0.93f, 0.9f, 0.82f));
            EditorUtility.SetDirty(m.bubble);
            string tp = $"{ArtDir}/BaseV2_BubbleText_v01.mat";
            var tsh = AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(Dir + "/Shaders/BubbleTextV2.shader");
            if (tsh == null) throw new FileNotFoundException("bubble text shader missing");
            m.bubbleText = AssetDatabase.LoadAssetAtPath<Material>(tp);
            if (!m.bubbleText) { m.bubbleText = new Material(tsh); AssetDatabase.CreateAsset(m.bubbleText, tp); }
            m.bubbleText.shader = tsh;
            EditorUtility.SetDirty(m.bubbleText);
            AssetDatabase.SaveAssets();
            return m;
        }

        static Material OutlineMat(string name, UnityEngine.Shader sh, float width, bool halo)
        {
            string path = $"{ArtDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            m.shader = sh;
            m.SetFloat("_Width", width);
            m.SetColor("_OutlineColor", new Color(1f, 0.74f, 0.25f, halo ? 0.22f : 1f));
            m.SetFloat("_SrcBlend", (float)(halo ? BlendMode.SrcAlpha : BlendMode.One));
            m.SetFloat("_DstBlend", (float)(halo ? BlendMode.OneMinusSrcAlpha : BlendMode.Zero));
            m.SetFloat("_ZWrite", halo ? 0f : 1f);
            m.renderQueue = halo ? (int)RenderQueue.Transparent + 10 : (int)RenderQueue.Geometry + 20;
            EditorUtility.SetDirty(m);
            return m;
        }

        static void Meshes(out Mesh baton, out Mesh stand)
        {
            if (File.Exists(MeshAsset)) AssetDatabase.DeleteAsset(MeshAsset);
            baton = BaseV2MeshesV01.Baton();
            stand = BaseV2MeshesV01.Stand();
            AssetDatabase.CreateAsset(baton, MeshAsset);
            AssetDatabase.AddObjectToAsset(stand, baton);
            AssetDatabase.SaveAssets();
            L($"meshes: baton {baton.vertexCount} v / {baton.triangles.Length / 3} tris (bounds {baton.bounds.size.x:0.000} x {baton.bounds.size.y:0.000} x {baton.bounds.size.z:0.000} m), stand {stand.triangles.Length / 3} tris");
        }

        static GameObject Child(Transform parent, string name, Vector3 pos, Quaternion rot)
        {
            var g = new GameObject(name);
            g.transform.SetParent(parent, false);
            g.transform.SetPositionAndRotation(pos, rot);
            return g;
        }

        static MeshRenderer Visual(GameObject g, Mesh mesh, Material[] mats, bool shadows = true)
        {
            g.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = g.AddComponent<MeshRenderer>();
            r.sharedMaterials = mats;
            r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            r.receiveShadows = false; // no shadow crawl on small props (CLAUDE.md no shimmer)
            r.renderingLayerMask = L0 | Hall | Room;
            return r;
        }

        static Transform Find(Transform root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name);

        static int Mask => ~((1 << OnlyVolunteers.Map.OvLayers.Player) | (1 << OnlyVolunteers.Map.OvLayers.RemotePlayer) | (1 << OnlyVolunteers.Map.OvLayers.VehicleInterior));

        // ================================================================== GEAR: the baton display + seller

        static void Shop(Transform hangar, Transform root, Mats mats, Mesh baton, Mesh stand)
        {
            Transform gear = hangar.Find("Room_Gear");
            if (gear == null) { L("GEAR: Room_Gear not found: no shop"); return; }
            Transform counter = Find(gear, "counter_out");
            Transform hallSpot = Find(gear, "Anchor_CounterHall"), clerk = Find(gear, "Anchor_Clerk");
            var cc = counter ? counter.GetComponent<Collider>() : null;
            if (cc == null || hallSpot == null || clerk == null) { L("GEAR: counter_out / anchors missing"); return; }
            Bounds cb = cc.bounds;
            // the counter runs along its longer horizontal side; the hall is toward the customer spot
            Vector3 along = cb.size.x >= cb.size.z ? Vector3.right : Vector3.forward;
            Vector3 toHall = Vector3.ProjectOnPlane(hallSpot.position - cb.center, Vector3.up);
            toHall = Vector3.Project(toHall, Vector3.Cross(Vector3.up, along)).normalized;
            float slide = Vector3.Dot(hallSpot.position - cb.center, along);
            slide = Mathf.Clamp(slide, -(Vector3.Dot(cb.extents, new Vector3(Mathf.Abs(along.x), 0, Mathf.Abs(along.z))) - 0.4f), Vector3.Dot(cb.extents, new Vector3(Mathf.Abs(along.x), 0, Mathf.Abs(along.z))) - 0.4f);
            Vector3 standPos = new Vector3(cb.center.x, cb.max.y + 0.002f, cb.center.z) + along * slide;
            Quaternion standRot = Quaternion.LookRotation(Vector3.Cross(along, Vector3.up), Vector3.up); // the stand's local X along the counter
            var shop = Child(root, "BaseV2 GEAR shop", standPos, standRot);
            var standGo = Child(shop.transform, "Baton display stand", standPos, standRot);
            Visual(standGo, stand, new[] { mats.standBoard }, false);
            // the item: the baton across the cradles (its +Y along the stand's X)
            var item = Child(shop.transform, "Display baton_rubber", standGo.transform.TransformPoint(BaseV2MeshesV01.StandRest), standRot * Quaternion.Euler(0f, 0f, -90f));
            item.transform.position -= item.transform.up * (BaseV2MeshesV01.BatonLength * 0.5f);
            var vis = Child(item.transform, "Baton (rubber, placeholder)", item.transform.position, item.transform.rotation);
            Visual(vis, baton, new[] { mats.rubber, mats.steel }, false);
            var box = item.AddComponent<BoxCollider>();
            box.center = new Vector3(0f, BaseV2MeshesV01.BatonLength * 0.5f - 0.02f, 0f);
            box.size = new Vector3(0.075f, BaseV2MeshesV01.BatonLength + 0.1f, 0.075f);
            var display = item.AddComponent<ShopDisplayItemV2>();
            display.ItemId = GearCatalogV2.Baton;
            display.OutlineMeshes = new[] { vis.GetComponent<MeshFilter>() };
            display.OutlineMaterial = mats.outline;
            display.HaloMaterial = mats.halo;
            display.Reach = 2.6f;
            L($"GEAR: counter_out {cb.min:F2}..{cb.max:F2}; stand on it at {standPos:F2} (slid {slide:+0.00;-0.00} m toward the customer spot), item collider {box.size}");

            // customer spot (tests) and a review camera in the hall
            var spot = Child(root, BaseV2Names.ShopCustomerSpot, new Vector3(hallSpot.position.x, hallSpot.position.y, hallSpot.position.z), Quaternion.LookRotation(Flat(standPos - hallSpot.position)));
            Vector3 aim = item.transform.position + item.transform.up * (BaseV2MeshesV01.BatonLength * 0.5f);
            float reachFlat = Flat(aim - spot.transform.position).magnitude;
            L($"GEAR: customer spot {spot.transform.position:F2}, {reachFlat:0.00} m (flat) to the baton; display reach {display.Reach:0.0} m {(reachFlat <= display.Reach ? "OK" : "TOO FAR")}");
            Vector3 camPos = hallSpot.position + toHall * 1.0f + along * 1.1f + Vector3.up * 1.55f;
            Child(root, BaseV2Names.ShopReviewCam, camPos, Quaternion.LookRotation(aim + Vector3.up * 0.25f - camPos));

            Seller(hangar, root, clerk, hallSpot);
        }

        static void Seller(Transform hangar, Transform root, Transform clerk, Transform hallSpot)
        {
            var crowd = hangar.gameObject.scene.GetRootGameObjects().FirstOrDefault(r => r.name == "Crowd");
            var cd = crowd ? crowd.GetComponent<OnlyVolunteers.Map.Crowd.CrowdDirector>() : null;
            var templates = cd != null && cd.Templates != null ? cd.Templates.Where(t => t).ToList() : new List<GameObject>();
            GameObject pick = null;
            foreach (string want in new[] { "PROM_FOREMAN", "HAMLET_MUZHIK", "OLD_OFFICE", "OLD_BUSINESSMAN" })
            {
                pick = templates.FirstOrDefault(t => t.name.Contains(want));
                if (pick) break;
            }
            pick ??= templates.FirstOrDefault(t => !t.name.Contains("FOREST") && !t.name.Contains("VIP") && !t.name.Contains("POLICE") && !t.name.Contains("BEACH"));
            if (pick == null) { L("GEAR seller: no crowd template in the scene: no seller"); return; }
            var go = Object.Instantiate(pick, root);
            go.name = "GEAR seller (placeholder, " + pick.name.Replace("CrowdTemplate_", "") + ")";
            go.transform.SetPositionAndRotation(clerk.position, Quaternion.LookRotation(Flat(hallSpot.position - clerk.position)));
            int removed = Strip(go);
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 0;
            if (!go.TryGetComponent(out OnlyVolunteers.Characters.Npc.NpcAnimDriver _) && go.GetComponentInChildren<Animator>(true) != null)
                go.AddComponent<OnlyVolunteers.Characters.Npc.NpcAnimDriver>();
            var cap = go.AddComponent<CapsuleCollider>();
            cap.center = new Vector3(0f, 0.9f, 0f);
            cap.height = 1.8f;
            cap.radius = 0.28f;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask = L0 | Hall | Room;
            go.SetActive(true);
            L($"GEAR seller: {go.name} at {clerk.position:F2} facing the hall; behaviour stripped ({removed} components: no NPC brain, no capture, no physics), idle only");
        }

        /// <summary>Removes everything but the look (transform, animator, renderers, mesh filters, LOD groups, the anim
        /// driver), dependents first so no RequireComponent blocks a removal.</summary>
        static int Strip(GameObject go)
        {
            bool Keep(Component c) => c is Transform || c is Animator || c is Renderer || c is MeshFilter || c is LODGroup ||
                                      c is OnlyVolunteers.Characters.Npc.NpcAnimDriver;
            int removed = 0;
            for (int pass = 0; pass < 12; pass++)
            {
                var all = go.GetComponentsInChildren<Component>(true).Where(c => c != null).ToList();
                var required = new HashSet<Type>();
                foreach (Component c in all)
                    foreach (RequireComponent rc in c.GetType().GetCustomAttributes(typeof(RequireComponent), true))
                        foreach (Type t in new[] { rc.m_Type0, rc.m_Type1, rc.m_Type2 }) if (t != null) required.Add(t);
                var drop = all.Where(c => !Keep(c) && !required.Any(t => t.IsInstanceOfType(c) && all.Any(o => o != c && o.gameObject == c.gameObject && !Keep(o) && Requires(o, c)))).ToList();
                // joints before bodies, then the rest
                drop = drop.OrderBy(c => c is Joint ? 0 : c is Rigidbody ? 2 : 1).ToList();
                if (drop.Count == 0) break;
                foreach (Component c in drop)
                {
                    if (c == null) continue;
                    if (all.Any(o => o != null && o != c && o.gameObject == c.gameObject && Requires(o, c))) continue;
                    Object.DestroyImmediate(c);
                    removed++;
                }
            }
            return removed;
        }

        static bool Requires(Component o, Component c)
        {
            foreach (RequireComponent rc in o.GetType().GetCustomAttributes(typeof(RequireComponent), true))
                foreach (Type t in new[] { rc.m_Type0, rc.m_Type1, rc.m_Type2 })
                    if (t != null && t.IsInstanceOfType(c)) return true;
            return false;
        }

        // ================================================================== workshop: dock, lift, mechanic

        static void Workshop(Transform hangar, Transform root, GameObject vanGo, Mats mats)
        {
            Transform room = hangar.Find("Room_Workshop");
            if (room == null) { L("workshop: Room_Workshop not found"); return; }
            Transform anchor = Find(room, "Anchor_VanOnLift");
            var beam = Find(room, "C_lift_beam")?.GetComponent<Collider>();
            var posts = room.GetComponentsInChildren<Collider>(true).Where(c => c.name == "C_lift_post").ToList();
            var parts = Moving.Select(n => Find(room, n)).ToArray();
            if (anchor == null || beam == null || posts.Count != 2 || parts.Any(p => p == null)) { L($"workshop: lift pieces missing (anchor {anchor != null}, beam {beam != null}, posts {posts.Count}, parts {parts.Count(p => p != null)}/6)"); return; }
            var van = vanGo ? vanGo.GetComponent<VanController>() : null;
            if (van == null) { L("workshop: no VanController on the scene van"); return; }
            float floorY = anchor.position.y;
            Quaternion parkRot = Quaternion.Euler(0f, anchor.eulerAngles.y, 0f);
            Vector3 fwd = parkRot * Vector3.forward, right = parkRot * Vector3.right;

            // the lift parts move in play: never static-batched
            foreach (Transform p in parts) GameObjectUtility.SetStaticEditorFlags(p.gameObject, 0);
            // the van over the lift: its body centre on the anchor (as VadimHangarRooms.PlaceVan)
            Bounds body = WorkshopServiceV01.VanBodyBoundsOf(van);
            Vector3 park = anchor.position - parkRot * new Vector3(body.center.x, 0f, body.center.z);
            park.y = floorY;
            float restTop = (vanGo.transform.position.y - floorY) + body.max.y;
            float beamUnder = beam.bounds.min.y - floorY;
            float travel = Mathf.Min(LiftSession.DefaultTravel, beamUnder - restTop - 0.3f);
            L($"workshop: van v05 body {body.size.x:0.00} x {body.size.y:0.00} x {body.size.z:0.00} m (renderer bounds, mirrors included), root {body.center.z:+0.00;-0.00} m off the body centre; rest top {restTop:0.00} m");
            L($"workshop: lift beam underside {beamUnder:0.00} m; v1 travel {LiftSession.DefaultTravel:0.00} m would put the roof at {restTop + LiftSession.DefaultTravel:0.00} m; travel used {travel:0.00} m -> raised roof {restTop + travel:0.00} m, clearance {beamUnder - restTop - travel:0.00} m");
            foreach (Collider post in posts)
            {
                Bounds pb = post.bounds;
                float across = Vector3.Dot(pb.center - anchor.position, right);
                float inner = Mathf.Abs(across) - Mathf.Abs(Vector3.Dot(pb.extents, new Vector3(Mathf.Abs(right.x), 0f, Mathf.Abs(right.z))));
                L($"workshop: post {(across > 0 ? "right" : "left")} inner face {inner:0.00} m from the lift axis: gap to the van body+mirrors {inner - body.size.x * 0.5f:0.00} m per side");
            }
            foreach (Transform p in parts.Where(t => t.name.StartsWith("Lift_Carriage")))
            {
                var rb = p.GetComponentInChildren<Renderer>();
                if (rb == null) continue;
                float across = Vector3.Dot(rb.bounds.center - anchor.position, right);
                float inner = Mathf.Abs(across) - Mathf.Abs(Vector3.Dot(rb.bounds.extents, new Vector3(Mathf.Abs(right.x), 0f, Mathf.Abs(right.z))));
                L($"workshop: {p.name} inner edge {inner:0.00} m from the axis: gap to the van {inner - body.size.x * 0.5f:0.00} m");
            }
            // what the raised van would touch (room colliders other than the lift posts / floor)
            Vector3 raisedC = anchor.position + Vector3.up * (restTop + travel - body.size.y * 0.5f);
            var hits = Physics.OverlapBox(raisedC, new Vector3(body.size.x * 0.5f, body.size.y * 0.5f, body.size.z * 0.5f), parkRot, ~0, QueryTriggerInteraction.Ignore)
                .Where(c => c.transform.IsChildOf(room) && c.name != "C_floor").Select(c => c.name).Distinct().ToList();
            L("workshop: raised van box vs room colliders: " + (hits.Count == 0 ? "clear" : "TOUCHES " + string.Join(", ", hits)));

            var svcGo = Child(root, "BaseV2 workshop service (lift, dock)", park, parkRot);
            var parkT = Child(svcGo.transform, "VanPark (lift centre, root of van v05)", park, parkRot).transform;
            var zoneGo = Child(svcGo.transform, "Dock zone (van centre in the box)", new Vector3(anchor.position.x, floorY, anchor.position.z), parkRot);
            var zone = zoneGo.AddComponent<WorkshopZone>();
            zone.Size = new Vector3(2.2f, 4f, 3.4f);
            zone.LiftOnly = true;
            zone.ShowMarkers = false;
            zone.Title = "Мастерская — подъёмник";

            // the control box point: outside the post with free floor (the mechanic stands there and works the lift)
            Transform control = null;
            float bestFree = -1f;
            foreach (Collider post in posts)
            {
                Vector3 side = Vector3.Dot(post.bounds.center - anchor.position, right) > 0f ? right : -right;
                Vector3 p = new Vector3(post.bounds.center.x, floorY, post.bounds.center.z) + side * 0.75f;
                float free = Free(p, 0.35f) ? 1f + (Free(p + side * 0.8f, 0.35f) ? 1f : 0f) : 0f;
                if (free <= bestFree) continue;
                bestFree = free;
                if (control != null) Object.DestroyImmediate(control.gameObject);
                control = Child(svcGo.transform, "Mechanic control point (beside the lift post)", p, Quaternion.LookRotation(-side)).transform;
            }
            Vector3 mechSide = Flat(control.position - anchor.position).normalized;
            // exit spots: both sides, front and rear of the axles, 2.7 m off the axis (outside the van + 0.9 m keep-out),
            // the side away from the mechanic first
            var spots = new List<Transform>();
            foreach (float s in new[] { -1f, 1f })
                foreach (float a in new[] { 1.7f, -1.7f, 3.2f })
                {
                    Vector3 sideDir = right * s;
                    Vector3 p = anchor.position + sideDir * 2.75f + fwd * a;
                    p.y = floorY;
                    bool free = Free(p, 0.4f);
                    if (!free) { L($"workshop: exit spot {s:+0;-0}/{a:+0.0;-0.0} blocked"); continue; }
                    var t = Child(svcGo.transform, $"Exit spot {(Vector3.Dot(sideDir, mechSide) > 0f ? "mechanic side" : "far side")} {a:+0.0;-0.0}", p, Quaternion.LookRotation(Flat(anchor.position - p))).transform;
                    spots.Add(t);
                }
            // the mechanic's side first: the customer steps out beside him and sees him and his bubble (the far side is
            // behind the raised van)
            spots = spots.OrderBy(t => Vector3.Dot(t.position - anchor.position, mechSide) > 0f ? 0 : 1).ToList();
            L($"workshop: control point {control.position:F2}; exit spots {spots.Count}: " + string.Join("; ", spots.Select(t => t.name)));

            var service = svcGo.AddComponent<WorkshopServiceV01>();
            service.Zone = zone;
            service.VanPark = parkT;
            service.LiftParts = parts;
            service.LiftArms = parts.Where(p => p.name.StartsWith("Lift_Arms")).ToArray();
            service.ArmEngagedYaw = service.LiftArms.Select(a => EngagedYaw(a, anchor.position, right)).ToArray();
            service.LiftTravel = travel;
            service.LiftSeconds = LiftSession.DefaultSeconds;
            service.ArmSwingSeconds = LiftSession.DefaultSwingSeconds;
            service.ControlPoint = control;
            service.Mechanic = Child(svcGo.transform, "Customer area (lift start reach)", anchor.position, parkRot).transform;
            service.MechanicReach = 4.5f;
            service.OwnerLeash = 14f;
            service.PadTolerance = new Vector3(0.6f, 1.2f, 15f);
            L("workshop: arms engaged yaw " + string.Join(", ", service.LiftArms.Select((a, i) => a.name + " " + service.ArmEngagedYaw[i].ToString("+0.0;-0.0"))));

            // mechanic B: home a little further out from the control point, a straight clear leg between them
            Vector3 home = control.position + mechSide * 1.2f + fwd * 1.4f;
            if (!Free(home, 0.35f)) home = control.position + fwd * 1.6f;
            if (!Free(home, 0.35f)) home = control.position - fwd * 1.6f;
            var mechGo = Child(root, "BaseV2 mechanic B (Mechanic_W86_v02)", home, Quaternion.LookRotation(Flat(anchor.position - home)));
            var homeT = Child(mechGo.transform, "Route home", home, Quaternion.LookRotation(Flat(anchor.position - home))).transform;
            var talk = mechGo.AddComponent<WorkshopMechanicV01>();
            talk.Spot = homeT;
            talk.ModelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(MechanicPrefab);
            talk.TalkEnabled = false;
            var brain = mechGo.GetComponent<WorkshopMechanicBrainV01>() ?? mechGo.AddComponent<WorkshopMechanicBrainV01>();
            brain.Frame = room;
            brain.Nodes = new[] { homeT, control };
            brain.Links = new[] { new Vector2Int(0, 1) };
            brain.Stops = new[] { new MechanicStop { Node = 0, Work = MechanicAction.Idle } };
            brain.ServiceNode = 1;
            brain.KeepOut = new MechanicKeepOut[0];
            brain.PuffMaterial = AssetDatabase.LoadAssetAtPath<Material>(PuffMaterial);
            bool leg = !Physics.CapsuleCast(home + Vector3.up * 0.4f, home + Vector3.up * 1.5f, 0.3f, Flat(control.position - home).normalized,
                out RaycastHit legHit, Flat(control.position - home).magnitude, Mask, QueryTriggerInteraction.Ignore);
            L($"workshop: mechanic {(talk.ModelPrefab ? talk.ModelPrefab.name : "MISSING model (crowd placeholder)")} home {home:F2} (free {Free(home, 0.35f)}), leg home->control {(leg ? "clear" : "BLOCKED by " + legHit.collider.name)}");

            var bubbleGo = Child(root, "BaseV2 mechanic speech bubble", control.position, Quaternion.identity);
            var bubble = bubbleGo.AddComponent<SpeechBubbleV2>();
            bubble.PanelMaterial = mats.bubble;
            bubble.TextMaterial = mats.bubbleText;
            bubble.LineHeight = 0.15f;
            bubble.Padding = 0.2f;
            bubble.Above = 2.1f;
            var dock = svcGo.AddComponent<WorkshopDockV2>();
            dock.Service = service;
            dock.Mechanic = talk;
            dock.Bubble = bubble;
            dock.ExitSpots = spots.ToArray();

            // review markers: ground level from the door side diagonal, and straight down from above the roof
            Vector3 cam = anchor.position - fwd * 4.4f + mechSide * 3.3f + Vector3.up * 1.65f;
            if (!Free(cam - Vector3.up * 1.6f, 0.3f)) cam = anchor.position - fwd * 4.2f + Vector3.up * 1.65f;
            Child(root, BaseV2Names.WorkshopReviewCam, cam, Quaternion.LookRotation(anchor.position + Vector3.up * 2.1f + mechSide * 1.4f - cam));
            Vector3 top = anchor.position + Vector3.up * 32f;
            Child(root, BaseV2Names.WorkshopTopCam, top, Quaternion.LookRotation(Vector3.down, fwd));
            L($"workshop: dock zone {zone.Size} at {zoneGo.transform.position:F2}, tolerance {service.PadTolerance}, travel {travel:0.00} m in {service.LiftSeconds:0.#} s");
        }

        static bool Free(Vector3 feet, float r) =>
            !Physics.CheckCapsule(feet + Vector3.up * (r + 0.15f), feet + Vector3.up * 1.6f, r, Mask, QueryTriggerInteraction.Ignore);

        /// <summary>The v1 lift's engaged arm yaw (Workshop_W86_lift_v01.json, 40.6 deg) with the sign that swings this arm
        /// toward the lift axis in Vadim's rebuilt lift (his copy is turned and stretched): tried both ways on the arm's
        /// renderer bounds, the one that brings it nearer the axis wins.</summary>
        static float EngagedYaw(Transform arm, Vector3 axisPoint, Vector3 right)
        {
            float mag = 40.6f;
            try
            {
                var json = File.ReadAllText(LiftJson);
                string key = arm.name.Replace("_Wide", "");
                int i = json.IndexOf("\"" + key + "\"", StringComparison.Ordinal);
                int k = i >= 0 ? json.IndexOf("\"engaged_local_yaw\"", i, StringComparison.Ordinal) : -1;
                if (k > 0)
                {
                    string tail = json.Substring(k + 19).TrimStart(' ', ':');
                    string num = new string(tail.TakeWhile(ch => char.IsDigit(ch) || ch == '-' || ch == '.').ToArray());
                    if (float.TryParse(num, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v)) mag = Mathf.Abs(v);
                }
            }
            catch (Exception) { }
            var r = arm.GetComponentInChildren<Renderer>();
            if (r == null) return mag;
            Quaternion baseRot = arm.localRotation;
            float Lateral(float yaw)
            {
                arm.localRotation = baseRot * Quaternion.Euler(0f, yaw, 0f);
                float d = 0f;
                // the far end of the arm: the bounds corner farthest from the arm pivot, measured across the lift
                Bounds b = r.bounds;
                for (int c = 0; c < 8; c++)
                {
                    Vector3 p = new Vector3((c & 1) == 0 ? b.min.x : b.max.x, b.center.y, (c & 4) == 0 ? b.min.z : b.max.z);
                    d += Mathf.Abs(Vector3.Dot(p - axisPoint, right));
                }
                return d;
            }
            float plus = Lateral(mag), minus = Lateral(-mag);
            arm.localRotation = baseRot;
            return plus <= minus ? mag : -mag;
        }

        static Vector3 Flat(Vector3 v)
        {
            v.y = 0f;
            return v.sqrMagnitude > 1e-6f ? v : Vector3.forward;
        }
    }
}
