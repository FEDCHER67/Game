using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using OnlyVolunteers.Economy;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    public static partial class W85PlayIntegrator
    {
        // ------------------------------------------------------------------ MECHANIC_W86 v01 (29.10)
        /// <summary>The route group under <see cref="WorkshopAnchorsName"/>.</summary>
        public const string MechanicRouteName = "MechanicRoute (MECHANIC_W86 v01)";
        private const float MechanicRadius = 0.3f;
        /// <summary>He stands this far in front of a bench / shelf top (clips_mechanic_v01.json: "0.45 m in front").</summary>
        private const float MechanicWorkReach = 0.45f;

        /// <summary>The mechanic step alone on the open play scene: model, route, brain on the existing workshop anchors
        /// (no building / ground / terrain work). The scene is marked dirty, not saved.</summary>
        public static string PlaceWorkshopMechanicInOpenScene()
        {
            Log.Clear();
            if (EditorApplication.isPlaying) return Fail("leave Play mode first");
            Scene scene = SceneManager.GetActiveScene();
            GameObject root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == WorkshopAnchorsName);
            if (root == null) return Fail($"no {WorkshopAnchorsName} in {scene.name}: run PlaceWorkshopZoneInOpenScene first");
            Note(PlaceWorkshopMechanic(root));
            EditorSceneManager.MarkSceneDirty(scene);
            AssetDatabase.SaveAssets();
            return Log.ToString();
        }

        /// <summary>
        /// MECHANIC_W86 v01 in the workshop (idempotent; also run by PlaceWorkshopLift): the dedicated model into
        /// WorkshopMechanicV01.ModelPrefab (identity WORKSHOP_MECHANIC kept), the route nodes under <see cref="MechanicRouteName"/>
        /// picked from the current geometry (workbench and parts shelf: their colliders' front + 0.45 m; the east lift post's
        /// outer face + 0.55 m; a via point behind the pit stairs; home = MechanicPoint, service = the lift control box
        /// point), the keep-out boxes (pit, lift, van path, loading area, the other bays, outside), the straight legs between
        /// nodes that are clear of them and of every collider (capsule cast) over solid floor, and the brain's tuning.
        /// </summary>
        static string PlaceWorkshopMechanic(GameObject root)
        {
            var sb = new StringBuilder();
            Transform frame = root.transform;
            var talk = root.GetComponent<WorkshopMechanicV01>();
            if (!talk) talk = root.AddComponent<WorkshopMechanicV01>();
            var brain = root.GetComponent<WorkshopMechanicBrainV01>();
            if (!brain) brain = root.AddComponent<WorkshopMechanicBrainV01>();
            var service = root.GetComponent<WorkshopServiceV01>();

            // the model (built once by the importer; re-run it by hand to rebuild)
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(OnlyVolunteers.Economy.EditorTools.MechanicW86ImportV01.PrefabPath);
            if (prefab == null)
            {
                sb.AppendLine(OnlyVolunteers.Economy.EditorTools.MechanicW86ImportV01.Build().TrimEnd());
                prefab = AssetDatabase.LoadAssetAtPath<GameObject>(OnlyVolunteers.Economy.EditorTools.MechanicW86ImportV01.PrefabPath);
            }
            talk.ModelPrefab = prefab;
            EditorUtility.SetDirty(talk);

            Transform home = talk.Spot != null ? talk.Spot : frame.Cast<Transform>().FirstOrDefault(t => t.name == "MechanicPoint");
            Transform control = service != null && service.ControlPoint != null ? service.ControlPoint : frame.Cast<Transform>().FirstOrDefault(t => t.name.StartsWith("MechanicControlPoint", StringComparison.Ordinal));
            if (home == null || control == null) return "mechanic: FAILED - no MechanicPoint / control box point under " + WorkshopAnchorsName;
            if (talk.Spot == null) talk.Spot = home;

            GameObject building = root.scene.GetRootGameObjects().FirstOrDefault(g => g.name == WorkshopBuildingName);
            Physics.SyncTransforms();
            // ---- stops from the current geometry (building-local)
            Vector3 bench = WorkFront(frame, building, "WS_P_Workbench_A", new Vector3(3.17f, 0f, 0.8f), 90f, out float benchYaw, sb);
            Vector3 shelf = WorkFront(frame, building, "WS_P_Shelving_Boxes_A", new Vector3(3.32f, 0f, -2.9f), 90f, out float shelfYaw, sb);
            Vector3 post = LiftPostSide(frame, building, out float postYaw, sb);
            Vector3 via = new Vector3(2.3f, 0f, -2.4f); // behind the pit stairs, east of the stair rails

            GameObject group = UniqueChild(frame, MechanicRouteName);
            group.transform.localPosition = Vector3.zero;
            group.transform.localRotation = Quaternion.identity;
            group.transform.localScale = Vector3.one;
            Transform Node(string name, Vector3 local, float yaw)
            {
                GameObject n = UniqueChild(group.transform, name);
                n.transform.localPosition = local;
                n.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
                n.transform.localScale = Vector3.one;
                EditorUtility.SetDirty(n);
                return n.transform;
            }
            Transform nBench = Node("Stop Workbench (InspectPart)", bench, benchYaw);
            Transform nPost = Node("Stop Lift post east (CheckBay)", post, postYaw);
            Transform nShelf = Node("Stop Parts shelf (WipeBench)", shelf, shelfYaw);
            Transform nVia = Node("Via Behind pit stairs", via, 90f);
            var nodes = new[] { home, nBench, nPost, nShelf, nVia, control };
            const int serviceIndex = 5;

            // ---- keep-out boxes (building-local; Workshop_W86_anchors_v01 / lift_v01 numbers + margins)
            var keep = new[]
            {
                new MechanicKeepOut { Name = "pit + stairs + rails", Center = new Vector3(0f, 0f, 0.9f), Size = new Vector3(1.5f, 4f, 5.2f) },
                new MechanicKeepOut { Name = "lift (posts, arms, control box, van on it)", Center = new Vector3(-0.025f, 0f, 2.4f), Size = new Vector3(4.05f, 4f, 2.8f) },
                new MechanicKeepOut { Name = "van path (door to pit stairs)", Center = new Vector3(0f, 0f, 3.2f), Size = new Vector3(2.6f, 4f, 7.6f) },
                new MechanicKeepOut { Name = "van loading / rear doors", Center = new Vector3(0f, 0f, 5.95f), Size = new Vector3(3.4f, 4f, 3.1f) },
                new MechanicKeepOut { Name = "west bay (rival hand-in)", Center = new Vector3(-8.2f, 0f, 0f), Size = new Vector3(7.6f, 4f, 12.4f) },
                new MechanicKeepOut { Name = "east bay", Center = new Vector3(8.2f, 0f, 0f), Size = new Vector3(7.6f, 4f, 12.4f) },
                new MechanicKeepOut { Name = "outside (apron, road)", Center = new Vector3(0f, 0f, 9.8f), Size = new Vector3(30f, 4f, 8.4f) },
            };

            // ---- legs: every pair whose straight line is clear
            var links = new List<Vector2Int>();
            var rejected = new List<string>();
            for (int i = 0; i < nodes.Length; i++)
                for (int j = i + 1; j < nodes.Length; j++)
                {
                    string why = LegBlocked(frame, keep, nodes[i].position, nodes[j].position);
                    if (why.Length == 0) links.Add(new Vector2Int(i, j));
                    else rejected.Add($"{Short(nodes[i])}-{Short(nodes[j])}: {why}");
                }

            brain.Frame = frame;
            brain.Nodes = nodes;
            brain.Links = links.ToArray();
            brain.ServiceNode = serviceIndex;
            brain.Stops = new[]
            {
                new MechanicStop { Node = 0, Work = MechanicAction.Idle },
                new MechanicStop { Node = 1, Work = MechanicAction.InspectPart },
                new MechanicStop { Node = 2, Work = MechanicAction.CheckBay },
                new MechanicStop { Node = 3, Work = MechanicAction.WipeBench },
            };
            brain.KeepOut = keep;
            brain.PuffMaterial = AssetDatabase.LoadAssetAtPath<Material>(OnlyVolunteers.Economy.EditorTools.MechanicW86ImportV01.PuffMaterialPath);
            EditorUtility.SetDirty(brain);
            EditorUtility.SetDirty(talk);

            // ---- checks: each stop on the floor, out of every keep-out box, its capsule clear; the round and the box reachable
            sb.AppendLine($"mechanic: model {(prefab ? AssetDatabase.GetAssetPath(prefab) : "MISSING (crowd placeholder stays)")}, id {WorkshopMechanicV01.MechanicId}, " +
                          $"brain on {WorkshopAnchorsName}, puff material {(brain.PuffMaterial ? brain.PuffMaterial.name : "fallback")}");
            for (int i = 0; i < nodes.Length; i++)
            {
                Vector3 w = nodes[i].position;
                Vector3 l = frame.InverseTransformPoint(w);
                string inBox = string.Join(", ", keep.Where(k => InBox(k, l, MechanicRadius - 0.001f)).Select(k => k.Name));
                string clear = CapsuleHits(w, MechanicRadius);
                float floor = FloorAt(w);
                sb.AppendLine($"  node {i} {nodes[i].name}: local ({l.x:0.00}, {l.z:0.00}) yaw {Mathf.DeltaAngle(0f, nodes[i].eulerAngles.y - frame.eulerAngles.y):0}; floor {(float.IsNaN(floor) ? "NONE" : (floor - w.y).ToString("+0.00;-0.00"))} m; " +
                              (inBox.Length > 0 ? "WARNING in keep-out: " + inBox : "outside every keep-out") + "; " + (clear.Length > 0 ? "WARNING capsule hits: " + clear : "capsule clear"));
            }
            sb.AppendLine($"  legs {links.Count}: {string.Join(", ", links.Select(k => Short(nodes[k.x]) + "-" + Short(nodes[k.y])))}");
            if (rejected.Count > 0) sb.AppendLine($"  not linked: {string.Join("; ", rejected)}");
            var reach = Reachable(nodes.Length, links, 0);
            string missing = string.Join(", ", Enumerable.Range(0, nodes.Length).Where(i => !reach.Contains(i)).Select(i => nodes[i].name));
            float round = RoundLength(nodes, links, new[] { 0, 1, 2, 3, 0 });
            sb.AppendLine(missing.Length == 0
                ? $"  every stop and the control box reachable from home; one round home > bench > post > shelf > home {round:0.0} m (~{round / Mathf.Max(0.1f, brain.WalkSpeed):0} s walking at {brain.WalkSpeed:0.0} m/s)"
                : "  WARNING unreachable: " + missing);
            Transform handIn = frame.Cast<Transform>().FirstOrDefault(t => t.name.StartsWith("RivalHandInZone", StringComparison.Ordinal));
            if (handIn) sb.AppendLine($"  nearest node to the rival hand-in zone: {nodes.Min(n => Vector3.Distance(n.position, handIn.position)):0.0} m (west bay, behind the partition)");
            sb.AppendLine($"  tuning: walk {brain.WalkSpeed:0.0} m/s, home dwell {brain.HomeDwellSeconds.x:0}-{brain.HomeDwellSeconds.y:0} s, gags every {brain.GagIntervalSeconds.x:0}-{brain.GagIntervalSeconds.y:0} active s, " +
                          $"attention {brain.AttentionStartRadius:0.0} m / release {brain.AttentionReleaseRadius:0.0} m after {brain.AttentionReleaseDelay:0.0} s, level +-{brain.AttentionMaxLevel:0.0} m");
            return sb.ToString().TrimEnd();
        }

        static string Short(Transform t)
        {
            string n = t.name;
            if (n.StartsWith("Stop ", StringComparison.Ordinal)) n = n.Substring(5);
            int p = n.IndexOf(" (", StringComparison.Ordinal);
            return p > 0 ? n.Substring(0, p) : n;
        }

        /// <summary>The floor point in front of a bench / shelf: its collider's front face (toward its yaw) + 0.45 m, at the
        /// collider's centre along the face; the yaw faces it. Fallback: the given point.</summary>
        static Vector3 WorkFront(Transform frame, GameObject building, string prop, Vector3 fallback, float fallbackYaw, out float yaw, StringBuilder sb)
        {
            yaw = fallbackYaw;
            Transform p = building ? building.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == prop) : null;
            BoxCollider box = p ? p.GetComponentsInChildren<BoxCollider>(true).FirstOrDefault() : null;
            if (!box) { sb.AppendLine($"  {prop}: not found, fallback point"); return fallback; }
            Bounds lb = LocalBounds(frame, box);
            float propYaw = Mathf.DeltaAngle(0f, p.eulerAngles.y - frame.eulerAngles.y);
            Vector3 front = Quaternion.Euler(0f, propYaw, 0f) * Vector3.forward; // the side it shows to the room
            Vector3 c = lb.center;
            float half = Mathf.Abs(front.x) > Mathf.Abs(front.z) ? lb.extents.x : lb.extents.z;
            Vector3 at = new Vector3(c.x, 0f, c.z) + new Vector3(Mathf.Round(front.x), 0f, Mathf.Round(front.z)) * (half + MechanicWorkReach);
            yaw = Mathf.Repeat(propYaw + 180f, 360f);
            sb.AppendLine($"  {prop}: collider local x {lb.min.x:0.00}..{lb.max.x:0.00} z {lb.min.z:0.00}..{lb.max.z:0.00} top {lb.max.y:0.00} -> stand at ({at.x:0.00}, {at.z:0.00}) facing {yaw:0}");
            return at;
        }

        /// <summary>Beside the east lift post (Lift_Static UCX_02, outer face) + 0.55 m, facing it: he knocks its base
        /// (Mech_Work_CheckBay) without entering the lift footprint.</summary>
        static Vector3 LiftPostSide(Transform frame, GameObject building, out float yaw, StringBuilder sb)
        {
            yaw = 270f;
            var fallback = new Vector3(2.4f, 0f, 2.4f);
            Transform lift = building ? building.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Lift_Static") : null;
            BoxCollider east = null;
            float best = float.MinValue;
            if (lift)
                foreach (BoxCollider b in lift.GetComponentsInChildren<BoxCollider>(true))
                {
                    Bounds lb = LocalBounds(frame, b);
                    if (lb.size.y > 3f && lb.center.x > best) { best = lb.center.x; east = b; }
                }
            if (!east) { sb.AppendLine("  lift post: not found, fallback point"); return fallback; }
            Bounds post = LocalBounds(frame, east);
            Vector3 at = new Vector3(post.max.x + 0.55f, 0f, post.center.z);
            sb.AppendLine($"  east lift post: collider local x {post.min.x:0.00}..{post.max.x:0.00} z {post.min.z:0.00}..{post.max.z:0.00} -> stand at ({at.x:0.00}, {at.z:0.00}) facing 270");
            return at;
        }

        static Bounds LocalBounds(Transform frame, BoxCollider b)
        {
            var lb = new Bounds();
            for (int i = 0; i < 8; i++)
            {
                Vector3 c = b.center + Vector3.Scale(b.size * 0.5f, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                Vector3 l = frame.InverseTransformPoint(b.transform.TransformPoint(c));
                if (i == 0) lb = new Bounds(l, Vector3.zero); else lb.Encapsulate(l);
            }
            return lb;
        }

        static bool InBox(MechanicKeepOut k, Vector3 local, float radius)
        {
            Vector3 e = k.Size * 0.5f + new Vector3(radius, 0f, radius);
            return Mathf.Abs(local.x - k.Center.x) < e.x && Mathf.Abs(local.z - k.Center.z) < e.z && Mathf.Abs(local.y - k.Center.y) < e.y;
        }

        /// <summary>Why a straight leg is not walkable ("" = clear): through a keep-out box (the control box point may stand
        /// at the lift's edge but its leg may not cross it), a collider in the way (capsule cast), or no floor under it.</summary>
        static string LegBlocked(Transform frame, MechanicKeepOut[] keep, Vector3 a, Vector3 b)
        {
            float len = Vector3.Distance(new Vector3(a.x, 0f, a.z), new Vector3(b.x, 0f, b.z));
            if (len > 9f) return "too long";
            int samples = Mathf.Max(4, Mathf.CeilToInt(len / 0.1f));
            for (int s = 0; s <= samples; s++)
            {
                Vector3 l = frame.InverseTransformPoint(Vector3.Lerp(a, b, s / (float)samples));
                foreach (MechanicKeepOut k in keep)
                    if (InBox(k, l, MechanicRadius - 0.001f)) return "keep-out " + k.Name;
            }
            Vector3 dir = b - a;
            dir.y = 0f;
            if (dir.sqrMagnitude > 1e-4f)
            {
                Vector3 p1 = a + Vector3.up * 0.4f, p2 = a + Vector3.up * 1.6f;
                foreach (RaycastHit h in Physics.CapsuleCastAll(p1, p2, MechanicRadius - 0.02f, dir.normalized, len, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
                    if (!(h.collider is TerrainCollider) && h.collider.gameObject.scene == frame.gameObject.scene && h.distance > 0f) return "collider " + h.collider.name;
            }
            for (int s = 1; s < samples; s += 3)
            {
                Vector3 p = Vector3.Lerp(a, b, s / (float)samples);
                float f = FloorAt(p);
                if (float.IsNaN(f) || Mathf.Abs(f - p.y) > 0.12f) return $"no floor at {Vector3.Distance(a, p):0.0} m";
            }
            return "";
        }

        /// <summary>The walkable surface under a point (a ray from 1 m above, colliders only, triggers ignored).</summary>
        static float FloorAt(Vector3 p)
        {
            foreach (RaycastHit h in Physics.RaycastAll(p + Vector3.up * 1.0f, Vector3.down, 2.5f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                return h.point.y;
            return float.NaN;
        }

        static string CapsuleHits(Vector3 at, float r)
        {
            var hits = Physics.OverlapCapsule(at + Vector3.up * (r + 0.12f), at + Vector3.up * 1.6f, r, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(c => !(c is TerrainCollider)).Select(c => c.name).Distinct().ToArray();
            return string.Join(", ", hits);
        }

        static HashSet<int> Reachable(int n, List<Vector2Int> links, int from)
        {
            var seen = new HashSet<int> { from };
            var todo = new Queue<int>();
            todo.Enqueue(from);
            while (todo.Count > 0)
            {
                int u = todo.Dequeue();
                foreach (Vector2Int l in links)
                {
                    int v = l.x == u ? l.y : l.y == u ? l.x : -1;
                    if (v >= 0 && seen.Add(v)) todo.Enqueue(v);
                }
            }
            return seen;
        }

        /// <summary>Shortest walking length of a round through the given stops (Dijkstra per leg).</summary>
        static float RoundLength(Transform[] nodes, List<Vector2Int> links, int[] order)
        {
            float total = 0f;
            for (int k = 0; k + 1 < order.Length; k++)
            {
                int n = nodes.Length;
                var d = Enumerable.Repeat(float.MaxValue, n).ToArray();
                var done = new bool[n];
                d[order[k]] = 0f;
                for (int it = 0; it < n; it++)
                {
                    int u = -1;
                    for (int i = 0; i < n; i++) if (!done[i] && d[i] < float.MaxValue && (u < 0 || d[i] < d[u])) u = i;
                    if (u < 0) break;
                    done[u] = true;
                    foreach (Vector2Int l in links)
                    {
                        int v = l.x == u ? l.y : l.y == u ? l.x : -1;
                        if (v < 0) continue;
                        float nd = d[u] + Vector3.Distance(nodes[u].position, nodes[v].position);
                        if (nd < d[v]) d[v] = nd;
                    }
                }
                total += d[order[k + 1]] == float.MaxValue ? float.NaN : d[order[k + 1]];
            }
            return total;
        }
    }
}
