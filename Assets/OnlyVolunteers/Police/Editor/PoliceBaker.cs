using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // Bakes police_vNN.asset from the newest map plan, read-only (design 3.8; docs/drafts/POLICE_V1_DRAFT.md):
    //   ArtSource/References/Map/MAP_PLAN_R01_vNN.json  road_graph, points (bases = category "base"), the station building;
    //   Look/look_vNN_flat.json                         the station's parking lot and its spaces;
    //   Crowd/crowd_vNN.json                            districts and witness hotspots;
    //   Vehicles/Van/Prefabs/Van.prefab                 the van's pace model (torque, wheel radius, mass, damping);
    //   Police/Data/PoliceConfig.asset                  every tunable number.
    // Steps: the van graph (+ the lot), police edge times along each road (PoliceRoadModel; the police car of the model is
    // the reference van (PoliceConfig.Ref*Level upgrades) x the balance ratios, as at runtime), per base the van's reference
    // drive time from every
    // road node (only for the patrol loops, which keep off the default home's start area, and for table A), the station
    // and its spaces, the patrol loops (kept out of districts with a low PoliceConfig.Presence patrol weight: the plan's
    // district polygons), then the response model over patrol positions (table B, with each district's dispatch delay and
    // chance). Since 2026-10-07 there is
    // no home line any more (GTA-like evade rule at runtime): no T_home grid, no chase-length or turn-back tables.
    // "Report Police Timing" prints the tables and warnings only; "Bake Police Data" also writes the asset.
    public static class PoliceBaker
    {
        private const string PlanDir = "ArtSource/References/Map";
        private const string CrowdDir = "ArtSource/References/Map/Crowd";
        public const string DataDir = "Assets/OnlyVolunteers/Police/Data";
        public const string ConfigPath = DataDir + "/PoliceConfig.asset";
        private const string VanPrefabPath = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab";
        private const string Tag = "[PoliceBake]";

        [MenuItem("OnlyVolunteers/Map/Police/Bake Police Data (latest plan)", false, 230)]
        public static void BakeMenu() => Run(true);

        [MenuItem("OnlyVolunteers/Map/Police/Report Police Timing (latest plan)", false, 231)]
        public static void ReportMenu() => Run(false);

        private static void Run(bool write)
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning($"{Tag} exit Play mode first.");
                return;
            }
            Bake(write);
        }

        public static string DataPath(string revision) => $"{DataDir}/police_{revision}.asset";

        public static PoliceConfig EnsureConfig()
        {
            var config = AssetDatabase.LoadAssetAtPath<PoliceConfig>(ConfigPath);
            if (config != null) return config;
            Directory.CreateDirectory(Path.Combine(ProjectRoot, DataDir));
            config = ScriptableObject.CreateInstance<PoliceConfig>();
            AssetDatabase.CreateAsset(config, ConfigPath);
            AssetDatabase.SaveAssets();
            Debug.Log($"{Tag} created {ConfigPath} with the v1 defaults");
            return config;
        }

        private static string ProjectRoot => Path.GetDirectoryName(Application.dataPath);

        /// <summary>Highest MAP_PLAN_R01_vNN.json: its full path and revision ("v12").</summary>
        public static string LatestPlan(out string revision)
        {
            revision = null;
            string dir = Path.Combine(ProjectRoot, PlanDir);
            if (!Directory.Exists(dir)) return null;
            string best = null;
            int bestRev = -1;
            foreach (string f in Directory.GetFiles(dir, "MAP_PLAN_R01_v*.json"))
            {
                Match m = Regex.Match(Path.GetFileName(f), @"^MAP_PLAN_R01_v(\d+)\.json$");
                if (!m.Success) continue;
                int rev = int.Parse(m.Groups[1].Value);
                if (rev <= bestRev) continue;
                bestRev = rev;
                best = f;
            }
            if (best != null) revision = "v" + bestRev.ToString("00");
            return best;
        }

        public static string PlanPath(string revision) => Path.Combine(ProjectRoot, PlanDir, $"MAP_PLAN_R01_{revision}.json");

        public static string PlanHash(string path)
        {
            using var sha = SHA1.Create();
            string text = File.ReadAllText(path).Replace("\r\n", "\n");
            byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(text));
            return BitConverter.ToString(hash, 0, 6).Replace("-", "").ToLowerInvariant();
        }

        public static string LookPath(string rev) => Path.Combine(ProjectRoot, MapLookBuilder.LookJsonDir, $"look_{rev}_flat.json");

        /// <summary>The crowd file of this revision, else the newest other one (fallback = true: its hotspots and districts
        /// may not match this plan).</summary>
        public static string CrowdPath(string rev, out bool fallback)
        {
            fallback = false;
            string path = Path.Combine(ProjectRoot, CrowdDir, $"crowd_{rev}.json");
            if (File.Exists(path)) return path;
            fallback = true;
            string dir = Path.Combine(ProjectRoot, CrowdDir);
            path = Directory.Exists(dir) ? Directory.GetFiles(dir, "crowd_v*.json").OrderBy(f => f.Length).ThenBy(f => f, StringComparer.Ordinal).LastOrDefault() : null;
            return path != null && File.Exists(path) ? path : null;
        }

        /// <summary>Hash of every input of a bake of 'rev': the plan, the look file, the crowd file it resolves to, the whole
        /// PoliceConfig and the van prefab's pace numbers. A build re-bakes when the data's InputsHash differs.</summary>
        public static string InputsHash(string rev, string planPath, PoliceConfig config)
        {
            var sb = new StringBuilder();
            sb.Append("plan:").Append(File.ReadAllText(planPath).Replace("\r\n", "\n")).Append('\n');
            string look = LookPath(rev);
            sb.Append("look:").Append(File.Exists(look) ? File.ReadAllText(look).Replace("\r\n", "\n") : "none").Append('\n');
            string crowd = CrowdPath(rev, out _);
            sb.Append("crowd:").Append(crowd != null ? Path.GetFileName(crowd) + "\n" + File.ReadAllText(crowd).Replace("\r\n", "\n") : "none").Append('\n');
            sb.Append("config:").Append(config != null ? JsonUtility.ToJson(config) : "none").Append('\n');
            VanNumbers(out float torque, out float vmax, out float radius, out float mass, out float k);
            sb.Append(FormattableString.Invariant($"van:{torque},{vmax},{radius},{mass},{k}"));
            VanUpgradeConfig steps = VanSteps();
            sb.Append("\nupgrades:").Append(steps != null ? JsonUtility.ToJson(steps) : "defaults");
            using var sha = SHA1.Create();
            byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(sb.ToString()));
            return BitConverter.ToString(hash, 0, 8).Replace("-", "").ToLowerInvariant();
        }

        // ---------- The bake ----------

        private sealed class PlanPoint
        {
            public string Id, Name, District, Category, Node;
            public Vector2 Position;
        }

        private sealed class Ctx
        {
            public PoliceConfig C;
            public PoliceMapData D;
            public readonly Dictionary<string, PlanPoint> Points = new();
            public readonly Dictionary<string, int> NodeIndex = new();
            public readonly List<string> RoadOfEdge = new();
            public CrowdData Crowd;
            public CarModel VanRef, VanFast, Police, Patrol;
            public readonly List<string> ClassOfEdge = new();
            public string NoPoliceLine = "";
            public readonly List<string> Warnings = new();
            public readonly StringBuilder Md = new();
            public List<int>[] Adj;
            public float[][] BaseT;
            public string StationBuilding;
            // Plan district polygons (id, outline, bounds) and the district of every road edge (its midpoint; null = none).
            public readonly List<(string id, Vector2[] poly, Rect bounds)> Districts = new();
            public string[] EdgeDistrict;
            public PoliceBalance Balance;
        }

        /// <summary>Bakes (write = also saves police_vNN.asset) the plan of 'revision' ("v12"), or the newest plan.</summary>
        public static PoliceMapData Bake(bool write, string revision = null)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            Trees.Clear();
            PoliceTimes.Clear();
            VanRoutes.Clear();
            string rev = revision;
            string planPath = revision != null ? PlanPath(revision) : LatestPlan(out rev);
            if (planPath == null || !File.Exists(planPath))
            {
                Debug.LogError($"{Tag} no {PlanDir}/MAP_PLAN_R01_{revision ?? "vNN"}.json");
                return null;
            }
            var x = new Ctx { C = EnsureConfig(), D = ScriptableObject.CreateInstance<PoliceMapData>() };
            x.D.Revision = rev;
            x.D.PlanFile = Path.GetFileName(planPath);
            x.D.PlanHash = PlanHash(planPath);
            x.D.InputsHash = InputsHash(rev, planPath, x.C);
            x.D.BakedAt = DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);
            try
            {
                if (!(MiniJson.Parse(File.ReadAllText(planPath)) is Dictionary<string, object> plan))
                    throw new InvalidDataException("the plan is not a JSON object");
                if (!plan.ContainsKey("road_graph")) throw new InvalidDataException("the plan has no road_graph");
                ReadPoints(x, plan);
                ReadGraph(x, plan);
                ReadDistricts(x, plan);
                if (x.D.EdgeCount == 0) throw new InvalidDataException("the plan's road_graph has no van road edges");
                x.Crowd = LoadCrowd(x, rev);
                VanModel(x);
                x.Patrol = x.C.PatrolCar;
                ReadBases(x);
                Station(x, plan, rev);
                PoliceRoads(x);
                BuildAdjacency(x);
                EdgeTimes(x);
                BaseTimes(x);
                EdgeDistricts(x);
                Loops(x);
                Hotspots(x);
                Simulate(x);
            }
            catch (Exception e)
            {
                Debug.LogError($"{Tag} {rev}: bake failed ({e.GetType().Name}: {e.Message}); no police data written.\n{e.StackTrace}");
                UnityEngine.Object.DestroyImmediate(x.D);
                return null;
            }
            string report = x.Md.ToString();
            x.D.Report = report;
            Debug.Log($"{Tag} {rev} ({x.D.PlanFile}, hash {x.D.PlanHash}): {x.D.NodeCount} nodes, {x.D.EdgeCount} edges, {x.D.BaseCount} bases, " +
                      $"station {x.D.StationId} ({x.D.Stalls.Length} spaces), {x.D.Loops.Length} loops, {x.D.Hotspots.Length} hotspots; " +
                      $"{sw.Elapsed.TotalSeconds:0.0} s\n\n{report}");
            foreach (string w in x.Warnings) Debug.LogWarning($"{Tag} {w}");
            if (!write) return x.D;
            string path = DataPath(rev);
            Directory.CreateDirectory(Path.Combine(ProjectRoot, DataDir));
            var existing = AssetDatabase.LoadAssetAtPath<PoliceMapData>(path);
            if (existing != null)
            {
                EditorUtility.CopySerialized(x.D, existing);
                existing.name = Path.GetFileNameWithoutExtension(path);
                EditorUtility.SetDirty(existing);
                UnityEngine.Object.DestroyImmediate(x.D);
                x.D = existing;
            }
            else AssetDatabase.CreateAsset(x.D, path);
            AssetDatabase.SaveAssets();
            Debug.Log($"{Tag} wrote {path}");
            return x.D;
        }

        // ---------- Plan ----------

        private static void ReadPoints(Ctx x, Dictionary<string, object> plan)
        {
            foreach (Dictionary<string, object> p in List(plan, "points"))
            {
                if (!p.ContainsKey("position_m")) continue;
                var point = new PlanPoint
                {
                    Id = Str(p, "id"), Name = Str(p, "name_ru"), District = Str(p, "district_id"), Category = Str(p, "category"),
                    Node = Str(p, "road_node_id"), Position = Vec(p["position_m"]),
                };
                if (!string.IsNullOrEmpty(point.Id)) x.Points[point.Id] = point;
            }
        }

        private static void ReadGraph(Ctx x, Dictionary<string, object> plan)
        {
            var graph = (Dictionary<string, object>)plan["road_graph"];
            var nodes = new List<Vector2>();
            foreach (Dictionary<string, object> n in List(graph, "nodes"))
            {
                if (!n.ContainsKey("position_m") || Str(n, "id") == null) continue;
                x.NodeIndex[Str(n, "id")] = nodes.Count;
                nodes.Add(Vec(n["position_m"]));
            }
            var a = new List<int>();
            var b = new List<int>();
            var len = new List<float>();
            var width = new List<float>();
            foreach (Dictionary<string, object> e in List(graph, "edges"))
            {
                if (e.TryGetValue("van_access", out object van) && van is bool v && !v) continue;
                if (!x.NodeIndex.TryGetValue(Str(e, "from_node"), out int from) || !x.NodeIndex.TryGetValue(Str(e, "to_node"), out int to) || from == to) continue;
                a.Add(from);
                b.Add(to);
                len.Add(e.TryGetValue("length_m", out object l) ? (float)(double)l : Vector2.Distance(nodes[from], nodes[to]));
                width.Add(e.TryGetValue("width_m", out object w) ? (float)(double)w : 6f);
                x.RoadOfEdge.Add(Str(e, "road_id") ?? "");
                x.ClassOfEdge.Add(Str(e, "class") ?? "");
            }
            x.D.Nodes = nodes.ToArray();
            x.D.EdgeA = a.ToArray();
            x.D.EdgeB = b.ToArray();
            x.D.EdgeLength = len.ToArray();
            x.D.EdgeWidth = width.ToArray();
            x.D.EdgeKind = new byte[a.Count];
            x.D.EdgeTime = new float[a.Count];
        }

        private static void ReadDistricts(Ctx x, Dictionary<string, object> plan)
        {
            foreach (Dictionary<string, object> d in List(plan, "districts"))
            {
                string id = Str(d, "id");
                if (id == null || !d.TryGetValue("polygon_m", out object o) || !(o is List<object> list) || list.Count < 3) continue;
                Vector2[] poly = list.Select(Vec).ToArray();
                Vector2 min = poly[0], max = poly[0];
                foreach (Vector2 p in poly)
                {
                    min = Vector2.Min(min, p);
                    max = Vector2.Max(max, p);
                }
                x.Districts.Add((id, poly, Rect.MinMaxRect(min.x, min.y, max.x, max.y)));
            }
            if (x.Districts.Count == 0) x.Warnings.Add("the plan has no district polygons: patrol loops cannot keep out of low-presence districts");
        }

        /// <summary>District id at a plan point: the plan polygon holding it, else the crowd district of the nearest crowd
        /// route vertex (as CrowdDirector.DistrictAt at runtime) within 60 m, else null.</summary>
        private static string DistrictOf(Ctx x, Vector2 p)
        {
            foreach ((string id, Vector2[] poly, Rect bounds) in x.Districts)
                if (bounds.Contains(p) && InPolygon(poly, p)) return id;
            if (x.Crowd == null) return null;
            int best = -1;
            float bestSq = 3600f;
            foreach (CrowdRoute r in x.Crowd.Routes)
                foreach (Vector2 v in r.Points)
                {
                    float d = (v - p).sqrMagnitude;
                    if (d < bestSq)
                    {
                        bestSq = d;
                        best = r.District;
                    }
                }
            return best >= 0 && best < x.Crowd.Districts.Count ? x.Crowd.Districts[best].Id : null;
        }

        private static bool InPolygon(Vector2[] poly, Vector2 p)
        {
            bool inside = false;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            {
                Vector2 a = poly[i], b = poly[j];
                if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) inside = !inside;
            }
            return inside;
        }

        private static void EdgeDistricts(Ctx x)
        {
            PoliceMapData d = x.D;
            x.EdgeDistrict = new string[d.EdgeA.Length];
            for (int e = 0; e < d.EdgeA.Length; e++) x.EdgeDistrict[e] = DistrictOf(x, 0.5f * (d.Nodes[d.EdgeA[e]] + d.Nodes[d.EdgeB[e]]));
        }

        private static CrowdData LoadCrowd(Ctx x, string rev)
        {
            string path = CrowdPath(rev, out bool fallback);
            x.D.CrowdFile = path != null ? Path.GetFileName(path) : "";
            if (path == null)
            {
                x.Warnings.Add($"no crowd file: hotspots and loops only from plan points");
                return null;
            }
            if (fallback)
                x.Warnings.Add($"no crowd_{rev}.json: districts and witness hotspots taken from {Path.GetFileName(path)} (another revision; bake again when crowd_{rev}.json lands)");
            return CrowdData.Parse(File.ReadAllText(path));
        }

        // The van prefab's pace numbers (defaults when the prefab is missing).
        private static bool VanNumbers(out float torque, out float vmax, out float radius, out float mass, out float k)
        {
            torque = 1250f;
            vmax = 105f;
            radius = 0.37f;
            mass = 1800f;
            k = 0.02f;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefabPath);
            if (prefab == null) return false;
            if (prefab.TryGetComponent(out VanController van))
            {
                torque = van.MotorTorque;
                vmax = van.MaxSpeedKmh;
            }
            if (prefab.TryGetComponent(out Rigidbody rb))
            {
                mass = rb.mass;
                k = rb.linearDamping;
            }
            WheelCollider wheel = prefab.GetComponentInChildren<WheelCollider>(true);
            if (wheel != null) radius = wheel.radius;
            return true;
        }

        /// <summary>The van prefab's upgrade steps (VanUpgrades.Config; null = VanUpgradeConfig's built-in defaults).</summary>
        private static VanUpgradeConfig VanSteps()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefabPath);
            return prefab != null && prefab.TryGetComponent(out VanUpgrades upgrades) ? upgrades.Config : null;
        }

        // Van reference pace from the prefab (design 3.1): A = 0.9 * torque / (wheel radius * mass), k = linear damping.
        private static void VanModel(Ctx x)
        {
            if (!VanNumbers(out float torque, out float vmax, out float radius, out float mass, out float k))
                x.Warnings.Add($"no {VanPrefabPath}: van pace from defaults");
            float a = 0.9f * torque / (radius * mass);
            x.VanRef = new CarModel(vmax, a, k, x.C.VanRefLateral, x.C.VanRefBrake, 2.1f);
            x.VanFast = new CarModel(vmax, a, k, x.C.VanFastLateral, x.C.VanFastBrake, 2.1f);
            // The police car of the model: the reference van (PoliceConfig.Ref*Level upgrades of the prefab's VanUpgrades
            // steps) x the balance ratios, by the same PoliceConfig.Balance as PoliceDirector at runtime: edge times, dispatch
            // ETAs, the response table.
            PoliceBalance b = x.C.Balance(torque, vmax, radius, mass, k, VanSteps());
            x.Balance = b;
            x.Police = new CarModel(b.TopKmh, b.A, b.K, b.Lateral, b.Brake, 1.8f);
            x.D.VanA = a;
            x.D.VanK = k;
            x.D.VanVMaxKmh = vmax;
            x.D.VanPaceFactor = x.C.VanPaceFactor;
        }

        private static void ReadBases(Ctx x)
        {
            var bases = x.Points.Values.Where(p => p.Category == "base").OrderBy(p => p.Id, StringComparer.Ordinal).ToList();
            x.D.BaseIds = bases.Select(p => p.Id).ToArray();
            x.D.BaseNames = bases.Select(p => p.Name ?? p.Id).ToArray();
            x.D.BaseDoors = bases.Select(p => p.Position).ToArray();
            x.D.BaseNodes = bases.Select(p => NodeOf(x, p.Node, p.Position)).ToArray();
            x.D.SafeRadius = x.C.SafeRadius;
            if (x.D.BaseIds.Length == 0) x.Warnings.Add("no points of category \"base\" in the plan");
        }

        // Road node: the point's own road_node_id when it is a road node, else the nearest road node.
        private static int NodeOf(Ctx x, string nodeId, Vector2 p)
        {
            if (!string.IsNullOrEmpty(nodeId) && x.NodeIndex.TryGetValue(nodeId, out int n) && Touched(x, n)) return n;
            return NearestNode(x, p);
        }

        private static bool Touched(Ctx x, int n)
        {
            for (int e = 0; e < x.D.EdgeA.Length; e++)
                if ((x.D.EdgeA[e] == n || x.D.EdgeB[e] == n) && x.D.EdgeKind[e] == PoliceMapData.RoadEdge) return true;
            return false;
        }

        private static int NearestNode(Ctx x, Vector2 p)
        {
            int best = -1;
            float bestD = float.MaxValue;
            for (int e = 0; e < x.D.EdgeA.Length; e++)
            {
                if (x.D.EdgeKind[e] != PoliceMapData.RoadEdge) continue;
                foreach (int n in new[] { x.D.EdgeA[e], x.D.EdgeB[e] })
                {
                    float d = (x.D.Nodes[n] - p).sqrMagnitude;
                    if (d < bestD)
                    {
                        bestD = d;
                        best = n;
                    }
                }
            }
            return best;
        }

        // ---------- Station, its lot and spaces ----------

        private static void Station(Ctx x, Dictionary<string, object> plan, string rev)
        {
            PoliceConfig c = x.C;
            Dictionary<string, object> building = null;
            foreach (Dictionary<string, object> f in List(plan, "functional_buildings"))
                if ((!string.IsNullOrEmpty(c.StationPoint) && Str(f, "poi_id") == c.StationPoint) || (building == null && Str(f, "type") == c.StationBuildingType))
                {
                    building = f;
                    if (Str(f, "poi_id") == c.StationPoint) break;
                }
            x.Points.TryGetValue(c.StationPoint ?? "", out PlanPoint point);
            Vector2 center = building != null && building.ContainsKey("center_m") ? Vec(building["center_m"]) : point != null ? point.Position : Vector2.zero;
            Vector2 entrance = building != null && building.ContainsKey("entrance_m") ? Vec(building["entrance_m"]) : point != null ? point.Position : center;
            x.StationBuilding = building != null ? Str(building, "id") : null;
            x.D.StationId = point != null ? point.Id : x.StationBuilding ?? "?";
            if (building == null && point == null) x.Warnings.Add($"no station: neither point {c.StationPoint} nor a building of type {c.StationBuildingType}");
            x.D.StationCenter = center;
            x.D.Entrance = entrance;
            Vector2 outward = entrance - center;
            outward = outward.sqrMagnitude > 1e-4f ? outward.normalized : Vector2.left;
            x.D.Respawn = entrance + outward * 1f;
            x.D.RespawnYaw = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;

            // The lot of the station building in the look data: its spaces, aisle and access become lot edges.
            LookParking lot = null;
            try
            {
                LookData look = MapLookBuilder.Load(rev);
                if (look != null && look.parking != null)
                    lot = look.parking.FirstOrDefault(p => p.building == x.StationBuilding && p.stalls != null && p.stalls.Length >= 5 &&
                                                           p.access != null && p.access.Length >= 4);
            }
            catch (Exception e)
            {
                x.Warnings.Add($"look_{rev}_flat.json not read ({e.Message}): spaces are made up in front of the station");
            }
            var nodes = new List<Vector2>(x.D.Nodes);
            var a = new List<int>(x.D.EdgeA);
            var b = new List<int>(x.D.EdgeB);
            var len = new List<float>(x.D.EdgeLength);
            var width = new List<float>(x.D.EdgeWidth);
            var kind = new List<byte>(x.D.EdgeKind);
            void AddEdge(int from, int to, float w)
            {
                a.Add(from);
                b.Add(to);
                len.Add(Vector2.Distance(nodes[from], nodes[to]));
                width.Add(w);
                kind.Add(PoliceMapData.LotEdge);
                x.RoadOfEdge.Add("LOT");
                x.ClassOfEdge.Add("lot");
            }
            var stalls = new List<Vector3>();
            var stallNodes = new List<int>();
            if (lot != null)
            {
                Vector2 access0 = new(lot.access[0], lot.access[1]), access1 = new(lot.access[2], lot.access[3]);
                int road = NearestNode(x, access1);
                x.D.StationNode = road;
                int nAccess1 = nodes.Count;
                nodes.Add(access1);
                int nAccess0 = nodes.Count;
                nodes.Add(access0);
                AddEdge(road, nAccess1, 5f);
                AddEdge(nAccess1, nAccess0, 5f);
                // Aisle points in front of every space, chained from the one nearest the access.
                var aisle = new List<(int stall, Vector2 p)>();
                for (int i = 0; i + 4 < lot.stalls.Length; i += 5)
                {
                    var s = new Vector3(lot.stalls[i], lot.stalls[i + 1], lot.stalls[i + 4]);
                    float depth = lot.stalls[i + 3];
                    Vector2 fwd = new(Mathf.Sin(s.z * Mathf.Deg2Rad), Mathf.Cos(s.z * Mathf.Deg2Rad));
                    stalls.Add(s);
                    aisle.Add((stalls.Count - 1, new Vector2(s.x, s.y) + fwd * (depth * 0.5f + 1.5f)));
                }
                aisle.Sort((p, q) => Vector2.Distance(p.p, access0).CompareTo(Vector2.Distance(q.p, access0)));
                int prev = nAccess0;
                var aisleNode = new int[stalls.Count];
                foreach ((int stall, Vector2 p) in aisle)
                {
                    int n = nodes.Count;
                    nodes.Add(p);
                    AddEdge(prev, n, 5f);
                    aisleNode[stall] = n;
                    prev = n;
                }
                for (int i = 0; i < stalls.Count; i++)
                {
                    int n = nodes.Count;
                    nodes.Add(new Vector2(stalls[i].x, stalls[i].y));
                    AddEdge(aisleNode[i], n, 4f);
                    stallNodes.Add(n);
                }
            }
            else
            {
                // No lot in the look data: spaces in a row on the road side in front of the entrance, facing along the road.
                x.D.StationNode = NearestNode(x, entrance);
                Vector2 side = new(-outward.y, outward.x);
                for (int i = 0; i < Mathf.Max(1, c.Cars); i++)
                {
                    Vector2 p = entrance + outward * 4f + side * (i - (c.Cars - 1) * 0.5f) * 5.5f;
                    stalls.Add(new Vector3(p.x, p.y, Mathf.Atan2(side.x, side.y) * Mathf.Rad2Deg));
                    stallNodes.Add(-1);
                }
                x.Warnings.Add($"no parking lot of {x.StationBuilding} in look_{rev}_flat.json: {stalls.Count} roadside spaces at the entrance");
            }
            x.D.Nodes = nodes.ToArray();
            x.D.EdgeA = a.ToArray();
            x.D.EdgeB = b.ToArray();
            x.D.EdgeLength = len.ToArray();
            x.D.EdgeWidth = width.ToArray();
            x.D.EdgeKind = kind.ToArray();
            x.D.EdgeTime = new float[a.Count];
            x.D.Stalls = stalls.ToArray();
            x.D.StallNodes = stallNodes.ToArray();
            if (stalls.Count < c.Cars) x.Warnings.Add($"station {x.D.StationId}: {stalls.Count} parking spaces for {c.Cars} cars (the rest start on the road)");
        }

        // Which van roads are no police roads (config classes, or narrower than MinRoadWidth): the van escapes through them.
        private static void PoliceRoads(Ctx x)
        {
            PoliceMapData d = x.D;
            d.EdgeNoPolice = new bool[d.EdgeCount];
            var classes = new HashSet<string>(x.C.NoPoliceRoadClasses ?? new string[0], StringComparer.Ordinal);
            int blocked = 0;
            float metres = 0f;
            for (int e = 0; e < d.EdgeCount; e++)
            {
                if (d.EdgeKind[e] != PoliceMapData.RoadEdge) continue;
                string cls = e < x.ClassOfEdge.Count ? x.ClassOfEdge[e] : "";
                if (d.EdgeWidth[e] >= x.C.MinRoadWidth && !classes.Contains(cls)) continue;
                d.EdgeNoPolice[e] = true;
                blocked++;
                metres += d.EdgeLength[e];
            }
            x.NoPoliceLine = $"Не полицейские дороги (классы: {(classes.Count > 0 ? string.Join(", ", classes) : "нет")}; уже {x.C.MinRoadWidth:0.#} м): {blocked} рёбер, {metres:0} м.";
        }

        private static void BuildAdjacency(Ctx x)
        {
            x.Adj = new List<int>[x.D.NodeCount];
            for (int i = 0; i < x.Adj.Length; i++) x.Adj[i] = new List<int>();
            for (int e = 0; e < x.D.EdgeCount; e++)
            {
                x.Adj[x.D.EdgeA[e]].Add(e);
                x.Adj[x.D.EdgeB[e]].Add(e);
            }
        }

        // ---------- Edge times: the police car along each road, flying ----------

        private static void EdgeTimes(Ctx x)
        {
            PoliceMapData d = x.D;
            var byRoad = new Dictionary<string, List<int>>();
            for (int e = 0; e < d.EdgeCount; e++)
            {
                if (d.EdgeKind[e] == PoliceMapData.LotEdge)
                {
                    d.EdgeTime[e] = d.EdgeLength[e] / 4f; // walking pace in the lot
                    continue;
                }
                string road = x.RoadOfEdge[e];
                if (!byRoad.TryGetValue(road, out List<int> list)) byRoad[road] = list = new List<int>();
                list.Add(e);
            }
            var done = new bool[d.EdgeCount];
            foreach (List<int> edges in byRoad.Values)
            {
                var degree = new Dictionary<int, int>();
                foreach (int e in edges)
                {
                    degree[d.EdgeA[e]] = degree.TryGetValue(d.EdgeA[e], out int da) ? da + 1 : 1;
                    degree[d.EdgeB[e]] = degree.TryGetValue(d.EdgeB[e], out int db) ? db + 1 : 1;
                }
                var starts = degree.Where(kv => kv.Value != 2).Select(kv => kv.Key).Concat(degree.Keys).ToList();
                foreach (int start in starts)
                {
                    while (true)
                    {
                        int first = FreeEdgeAt(d, edges, done, start);
                        if (first < 0) break;
                        var pts = new List<Vector2> { d.Nodes[start] };
                        var widths = new List<float>();
                        var chain = new List<int>();
                        int node = start, edge = first;
                        while (edge >= 0)
                        {
                            done[edge] = true;
                            chain.Add(edge);
                            node = d.Other(edge, node);
                            pts.Add(d.Nodes[node]);
                            widths.Add(d.EdgeWidth[edge]);
                            if (degree[node] != 2) break;
                            edge = FreeEdgeAt(d, edges, done, node);
                        }
                        int n = pts.Count;
                        var s = new float[n];
                        var t = new float[n];
                        var v = new float[n];
                        var caps = new float[n];
                        PoliceRoadModel.Profile(pts, widths, x.Police, 0f, float.NaN, true, s, t, v, caps);
                        for (int i = 0; i < chain.Count; i++) d.EdgeTime[chain[i]] = Mathf.Max(0.01f, t[i + 1] - t[i]);
                    }
                }
            }
            for (int e = 0; e < d.EdgeCount; e++)
                if (d.EdgeTime[e] <= 0f) d.EdgeTime[e] = d.EdgeLength[e] / 15f;
        }

        private static int FreeEdgeAt(PoliceMapData d, List<int> edges, bool[] done, int node)
        {
            foreach (int e in edges)
                if (!done[e] && (d.EdgeA[e] == node || d.EdgeB[e] == node)) return e;
            return -1;
        }

        // ---------- Shortest paths by length (the model's route choice) ----------

        private sealed class Tree
        {
            public float[] Dist;
            public int[] PrevEdge;
            public int Root;
        }

        private static readonly Dictionary<(int, int), Tree> Trees = new();

        // mode 0: van roads (no lot); 1: police roads (no lot, no narrow edges).
        private static Tree LengthTree(Ctx x, int root, int mode)
        {
            if (Trees.TryGetValue((root, mode), out Tree cached)) return cached;
            PoliceMapData d = x.D;
            var dist = new float[d.NodeCount];
            var prev = new int[d.NodeCount];
            for (int i = 0; i < dist.Length; i++)
            {
                dist[i] = float.PositiveInfinity;
                prev[i] = -1;
            }
            var heap = new Heap();
            dist[root] = 0f;
            heap.Push(0f, root);
            while (heap.Count > 0)
            {
                heap.Pop(out float du, out int u);
                if (du > dist[u]) continue;
                foreach (int e in x.Adj[u])
                {
                    if (d.EdgeKind[e] != PoliceMapData.RoadEdge || (mode == 1 && d.EdgeNoPolice[e])) continue;
                    int v = d.Other(e, u);
                    float nd = du + d.EdgeLength[e];
                    if (nd >= dist[v]) continue;
                    dist[v] = nd;
                    prev[v] = e;
                    heap.Push(nd, v);
                }
            }
            var tree = new Tree { Dist = dist, PrevEdge = prev, Root = root };
            Trees[(root, mode)] = tree;
            return tree;
        }

        // Nodes from the tree's root to 'to' (empty when unreachable).
        private static List<int> PathFromRoot(Ctx x, Tree tree, int to)
        {
            var nodes = new List<int>();
            if (float.IsPositiveInfinity(tree.Dist[to])) return nodes;
            int n = to;
            nodes.Add(n);
            while (n != tree.Root)
            {
                int e = tree.PrevEdge[n];
                if (e < 0) return new List<int>();
                n = x.D.Other(e, n);
                nodes.Add(n);
            }
            nodes.Reverse();
            return nodes;
        }

        private static void Polyline(Ctx x, List<int> nodes, List<Vector2> pts, List<float> widths)
        {
            pts.Clear();
            widths.Clear();
            for (int i = 0; i < nodes.Count; i++)
            {
                Vector2 p = x.D.Nodes[nodes[i]];
                if (pts.Count > 0 && (pts[pts.Count - 1] - p).sqrMagnitude < 0.0025f) continue;
                if (pts.Count > 0) widths.Add(EdgeWidthBetween(x, nodes[i - 1], nodes[i]));
                pts.Add(p);
            }
        }

        private static float EdgeWidthBetween(Ctx x, int u, int v)
        {
            foreach (int e in x.Adj[u])
                if (x.D.Other(e, u) == v) return x.D.EdgeWidth[e];
            return 6f;
        }

        // ---------- Van drive time to every base ----------

        // Per base: seconds of reference van driving from every road node to the door (shortest path by length, flying
        // start, stop at the door). Only the patrol loops read it (they keep off the default home's start area).
        private static void BaseTimes(Ctx x)
        {
            PoliceMapData d = x.D;
            int bases = d.BaseCount;
            x.BaseT = new float[bases][];
            var pts = new List<Vector2>();
            var widths = new List<float>();
            for (int b = 0; b < bases; b++)
            {
                Tree tree = LengthTree(x, d.BaseNodes[b], 0);
                var t = new float[d.NodeCount];
                for (int n = 0; n < d.NodeCount; n++)
                {
                    t[n] = float.PositiveInfinity;
                    if (float.IsPositiveInfinity(tree.Dist[n])) continue;
                    List<int> path = PathFromRoot(x, tree, n);
                    path.Reverse(); // node -> base
                    Polyline(x, path, pts, widths);
                    t[n] = pts.Count < 2 ? 0f : PoliceRoadModel.Time(pts, widths, x.VanRef, 0f, 0f, true) * x.C.VanPaceFactor;
                }
                x.BaseT[b] = t;
            }
        }

        // ---------- Patrol loops ----------

        private static bool Resolve(Ctx x, string id, out Vector2 pos, out string district)
        {
            pos = Vector2.zero;
            district = null;
            if (string.IsNullOrEmpty(id)) return false;
            string[] xy = id.Split(',');
            if (xy.Length == 2 && float.TryParse(xy[0], NumberStyles.Float, CultureInfo.InvariantCulture, out float px) &&
                float.TryParse(xy[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float py))
            {
                pos = new Vector2(px, py);
                return true;
            }
            if (x.Points.TryGetValue(id, out PlanPoint p))
            {
                pos = p.Position;
                district = p.District;
                return true;
            }
            if (x.Crowd != null)
                foreach (CrowdHotspot h in x.Crowd.Hotspots)
                    if (h.Id == id)
                    {
                        pos = h.Position;
                        district = h.District >= 0 && h.District < x.Crowd.Districts.Count ? x.Crowd.Districts[h.District].Id : null;
                        return true;
                    }
            return false;
        }

        private static int ResolveNode(Ctx x, string id)
        {
            if (x.Points.TryGetValue(id, out PlanPoint p)) return NodeOf(x, p.Node, p.Position);
            return Resolve(x, id, out Vector2 pos, out _) ? NearestNode(x, pos) : -1;
        }

        private static void Loops(Ctx x)
        {
            PoliceMapData d = x.D;
            PoliceConfig c = x.C;
            int home = d.BaseIndex(c.DefaultHomeBase);
            float avoid = c.PatrolAvoidHome;
            var loops = new List<PoliceLoop>();
            foreach (PoliceLoopDef def in c.Loops)
            {
                // District presence: no patrol loop in a low-presence district (the alley district): its waypoints are
                // skipped, it is no loop district, and its roads cost LowPresenceDetour x their length below.
                string[] districts = (def.Districts ?? new string[0]).Where(id => !c.LowPresence(id)).ToArray();
                foreach (string id in def.Districts ?? new string[0])
                    if (c.LowPresence(id)) x.Warnings.Add($"loop {def.Name}: district {id} has a low police presence, dropped from the loop");
                var stops = new List<int> { d.StationNode };
                foreach (string w in def.Waypoints)
                {
                    int n = ResolveNode(x, w);
                    if (n < 0)
                    {
                        x.Warnings.Add($"loop {def.Name}: waypoint {w} not in this plan, skipped");
                        continue;
                    }
                    string wd = Resolve(x, w, out Vector2 wp, out string pd) ? pd ?? DistrictOf(x, wp) : null;
                    if (wd != null && c.LowPresence(wd))
                    {
                        x.Warnings.Add($"loop {def.Name}: waypoint {w} is in the low-presence district {wd}, skipped");
                        continue;
                    }
                    stops.Add(n);
                }
                if (stops.Count < 3)
                {
                    // Too few known waypoints: the group's hotspots in nearest-neighbour order from the station.
                    var left = new List<int>();
                    if (x.Crowd != null)
                        foreach (CrowdHotspot h in x.Crowd.Hotspots)
                            if (h.District >= 0 && h.District < x.Crowd.Districts.Count && districts.Contains(x.Crowd.Districts[h.District].Id))
                                left.Add(NearestNode(x, h.Position));
                    stops = new List<int> { d.StationNode };
                    while (left.Count > 0)
                    {
                        Vector2 at = d.Nodes[stops[stops.Count - 1]];
                        int k = 0;
                        for (int i = 1; i < left.Count; i++)
                            if ((d.Nodes[left[i]] - at).sqrMagnitude < (d.Nodes[left[k]] - at).sqrMagnitude) k = i;
                        stops.Add(left[k]);
                        left.RemoveAt(k);
                    }
                    x.Warnings.Add($"loop {def.Name}: built from its districts' hotspots ({stops.Count - 1} stops)");
                }
                if (stops.Count < 2) continue;
                stops.Add(d.StationNode);
                var signed = new List<int>();
                for (int i = 0; i + 1 < stops.Count; i++)
                {
                    List<int> path = LoopLeg(x, stops[i], stops[i + 1], home, avoid);
                    for (int k = 0; k + 1 < path.Count; k++)
                    {
                        int e = EdgeBetween(x, path[k], path[k + 1]);
                        if (e >= 0) signed.Add(d.EdgeA[e] == path[k] ? e + 1 : -(e + 1));
                    }
                }
                if (signed.Count < 2)
                {
                    x.Warnings.Add($"loop {def.Name}: no route between its stops");
                    continue;
                }
                var loop = new PoliceLoop { Name = def.Name, Districts = districts, Edges = signed.ToArray(), ScoreDay = def.ScoreDay, ScoreNight = def.ScoreNight };
                var route = new PoliceRoute();
                LoopPolyline(d, loop, route);
                loop.Length = route.Length();
                loop.Lap = PoliceRoadModel.Time(route.Points, route.Widths, x.Patrol, 0f, float.NaN, true);
                float low = LoopDistricts(x, loop).Where(kv => kv.Key != null && c.LowPresence(kv.Key)).Sum(kv => kv.Value);
                if (low > 1f) x.Warnings.Add($"loop {def.Name}: {low:0} m in low-presence districts (no way round)");
                loops.Add(loop);
            }
            d.Loops = loops.ToArray();
        }

        // Shortest by length, roads near the default home base (van time to it < PatrolAvoidHome) counted 20 % longer: a
        // patrol keeps off the start area when a route not much longer exists (design 4.3); roads in a low-presence district
        // count LowPresenceDetour x (a patrol goes round the alley district).
        private static List<int> LoopLeg(Ctx x, int from, int to, int home, float avoid)
        {
            PoliceMapData d = x.D;
            var dist = new float[d.NodeCount];
            var prev = new int[d.NodeCount];
            for (int i = 0; i < dist.Length; i++)
            {
                dist[i] = float.PositiveInfinity;
                prev[i] = -1;
            }
            var heap = new Heap();
            dist[from] = 0f;
            heap.Push(0f, from);
            while (heap.Count > 0)
            {
                heap.Pop(out float du, out int u);
                if (u == to) break;
                if (du > dist[u]) continue;
                foreach (int e in x.Adj[u])
                {
                    if (d.EdgeKind[e] != PoliceMapData.RoadEdge || d.EdgeNoPolice[e]) continue;
                    int v = d.Other(e, u);
                    float w = d.EdgeLength[e];
                    if (home >= 0 && (x.BaseT[home][u] < avoid || x.BaseT[home][v] < avoid)) w *= 1.2f;
                    if (x.EdgeDistrict[e] != null && x.C.LowPresence(x.EdgeDistrict[e])) w *= Mathf.Max(1f, x.C.LowPresenceDetour);
                    if (du + w >= dist[v]) continue;
                    dist[v] = du + w;
                    prev[v] = e;
                    heap.Push(dist[v], v);
                }
            }
            var nodes = new List<int>();
            if (float.IsPositiveInfinity(dist[to])) return nodes;
            for (int n = to; n != from; n = d.Other(prev[n], n)) nodes.Add(n);
            nodes.Add(from);
            nodes.Reverse();
            return nodes;
        }

        /// <summary>Metres of the loop per district id (null key = roads outside every district).</summary>
        private static Dictionary<string, float> LoopDistricts(Ctx x, PoliceLoop loop)
        {
            var metres = new Dictionary<string, float>();
            float none = 0f;
            foreach (int signed in loop.Edges)
            {
                int e = Mathf.Abs(signed) - 1;
                string id = x.EdgeDistrict[e];
                if (id == null) none += x.D.EdgeLength[e];
                else metres[id] = (metres.TryGetValue(id, out float m) ? m : 0f) + x.D.EdgeLength[e];
            }
            var result = metres.OrderByDescending(p => p.Value).ToDictionary(p => p.Key, p => p.Value);
            if (none > 0f) result[""] = none;
            return result;
        }

        private static int EdgeBetween(Ctx x, int u, int v)
        {
            foreach (int e in x.Adj[u])
                if (x.D.Other(e, u) == v) return e;
            return -1;
        }

        private static void LoopPolyline(PoliceMapData d, PoliceLoop loop, PoliceRoute route)
        {
            route.Clear();
            for (int i = 0; i < loop.Edges.Length; i++)
            {
                int e = Mathf.Abs(loop.Edges[i]) - 1;
                int a = loop.Edges[i] > 0 ? d.EdgeA[e] : d.EdgeB[e], b = loop.Edges[i] > 0 ? d.EdgeB[e] : d.EdgeA[e];
                if (i == 0) route.Add(d.Nodes[a], d.EdgeWidth[e]);
                route.Add(d.Nodes[b], d.EdgeWidth[e]);
            }
        }

        // ---------- Hotspots ----------

        private static void Hotspots(Ctx x)
        {
            var list = new List<PoliceHotspot>();
            foreach (PoliceHotspotDef def in x.C.Hotspots)
            {
                if (!Resolve(x, def.Id, out Vector2 pos, out string district))
                {
                    x.Warnings.Add($"hotspot {def.Id} not in this plan / crowd file, skipped");
                    continue;
                }
                list.Add(new PoliceHotspot { Id = def.Id, Name = string.IsNullOrEmpty(def.Name) ? def.Id : def.Name, District = district, Position = pos, Node = ResolveNode(x, def.Id) });
            }
            if (list.Count < 3 && x.Crowd != null)
            {
                list.Clear();
                foreach (CrowdHotspot h in x.Crowd.Hotspots)
                    list.Add(new PoliceHotspot
                    {
                        Id = h.Id, Name = h.Id.Replace("WITNESS_", ""), Position = h.Position, Node = NearestNode(x, h.Position),
                        District = h.District >= 0 && h.District < x.Crowd.Districts.Count ? x.Crowd.Districts[h.District].Id : null,
                    });
                x.Warnings.Add("hotspots: fewer than 3 of the config's found; using every crowd witness hotspot");
            }
            foreach (PoliceHotspot h in list) h.Core = h.District != null && x.C.CoreDistricts.Contains(h.District);
            x.D.Hotspots = list.ToArray();
        }

        // ---------- The timing model (design 3.1-3.4; port of roadsim.py): van drive times, response ----------

        private static readonly Dictionary<(int, int), float> PoliceTimes = new();

        // Police car from standstill along the shortest road path (the design's police_time).
        private static float PoliceTime(Ctx x, int from, int to)
        {
            if (from == to) return 0f;
            if (PoliceTimes.TryGetValue((from, to), out float cached)) return cached;
            Tree tree = LengthTree(x, from, 1);
            List<int> path = PathFromRoot(x, tree, to);
            float t = float.PositiveInfinity;
            if (path.Count >= 2)
            {
                var pts = new List<Vector2>();
                var widths = new List<float>();
                Polyline(x, path, pts, widths);
                t = PoliceRoadModel.Time(pts, widths, x.Police, 0f, float.NaN, false);
            }
            PoliceTimes[(from, to)] = t;
            return t;
        }

        private sealed class VanRoute
        {
            public float[] S, T, V;
            public List<(int node, float s, float t, float v)> Nodes = new();
            public float Total, Length;
            public List<Vector2> Pts = new();
            public List<float> Widths = new();
        }

        private static readonly Dictionary<(int, int, bool), VanRoute> VanRoutes = new();

        private static VanRoute Route(Ctx x, int from, int to, bool fast = false)
        {
            if (VanRoutes.TryGetValue((from, to, fast), out VanRoute cached)) return cached;
            var r = new VanRoute();
            List<int> nodes = PathFromRoot(x, LengthTree(x, from, 0), to);
            if (nodes.Count >= 2)
            {
                // All edges are single segments: vertex i is node i (duplicates aside).
                for (int i = 0; i < nodes.Count; i++)
                {
                    Vector2 p = x.D.Nodes[nodes[i]];
                    if (r.Pts.Count > 0 && (r.Pts[r.Pts.Count - 1] - p).sqrMagnitude < 0.0025f) continue;
                    if (r.Pts.Count > 0) r.Widths.Add(EdgeWidthBetween(x, nodes[i - 1], nodes[i]));
                    r.Pts.Add(p);
                    r.Nodes.Add((nodes[i], 0f, 0f, 0f));
                }
                int n = r.Pts.Count;
                r.S = new float[n];
                r.T = new float[n];
                r.V = new float[n];
                PoliceRoadModel.Profile(r.Pts, r.Widths, fast ? x.VanFast : x.VanRef, 0f, 0f, false, r.S, r.T, r.V, new float[n]);
                for (int i = 0; i < n; i++)
                {
                    r.T[i] *= x.C.VanPaceFactor;
                    r.Nodes[i] = (r.Nodes[i].node, r.S[i], r.T[i], r.V[i] / x.C.VanPaceFactor);
                }
                r.Total = r.T[n - 1];
                r.Length = r.S[n - 1];
            }
            VanRoutes[(from, to, fast)] = r;
            return r;
        }

        private static List<int> LoopSamples(Ctx x, PoliceLoop loop)
        {
            var samples = new List<int>();
            float acc = 0f;
            foreach (int signed in loop.Edges)
            {
                int e = Mathf.Abs(signed) - 1;
                acc += x.D.EdgeLength[e];
                if (acc < x.C.ModelSampleStep) continue;
                samples.Add(signed > 0 ? x.D.EdgeB[e] : x.D.EdgeA[e]);
                acc = 0f;
            }
            return samples;
        }

        private sealed class Mode
        {
            public string Name;
            public float Radio;
            public List<List<int>> Samples = new();
            public List<string> LoopNames = new();
        }

        private static Mode MakeMode(Ctx x, bool night)
        {
            PoliceConfig c = x.C;
            float a = night ? 1f : 0f;
            var m = new Mode
            {
                Name = night ? "ночь" : "день", Radio = c.RadioDelay.At(a),
            };
            int cars = night ? c.PatrolCarsNight : c.PatrolCarsDay;
            foreach (PoliceLoop loop in x.D.Loops.OrderByDescending(l => night ? l.ScoreNight : l.ScoreDay).Take(cars))
            {
                m.Samples.Add(LoopSamples(x, loop));
                m.LoopNames.Add(loop.Name);
            }
            return m;
        }

        private static float Percentile(List<float> values, float p)
        {
            if (values.Count == 0) return 0f;
            var sorted = values.OrderBy(v => v).ToList();
            return sorted[(int)(p * (sorted.Count - 1))];
        }

        private static float Median(List<float> values)
        {
            if (values.Count == 0) return 0f;
            var sorted = values.OrderBy(v => v).ToList();
            int n = sorted.Count;
            return n % 2 == 1 ? sorted[n / 2] : 0.5f * (sorted[n / 2 - 1] + sorted[n / 2]);
        }

        private static void Simulate(Ctx x)
        {
            PoliceMapData d = x.D;
            PoliceConfig c = x.C;
            StringBuilder md = x.Md;
            int nb = d.BaseCount;
            var day = MakeMode(x, false);
            var night = MakeMode(x, true);
            md.AppendLine($"## Полиция {d.Revision}: модель таймингов (бусик эталон: A {d.VanA:0.00} м/с², k {d.VanK:0.000}, {d.VanVMaxKmh:0} км/ч, поворот/тормоз {c.VanRefLateral:0}/{c.VanRefBrake:0}; темп ×{c.VanPaceFactor:0.00})");
            md.AppendLine();
            PoliceBalance bal = x.Balance;
            md.AppendLine($"Баланс: эталонный бусик прокачки двигатель/тормоза/управление {bal.Levels} — {bal.VanTopKmh:0} км/ч, A {bal.VanA:0.00} м/с², " +
                          $"поворот {bal.VanLateral:0.0}, тормоз {bal.VanBrake:0.0} м/с²; полиция × {c.TopSpeedRatio:0.00}/{c.AccelRatio:0.00}/{c.CornerGripRatio:0.00}/{c.BrakeRatio:0.00}.");
            md.AppendLine();
            md.AppendLine($"Полицейская машина модели (эталон × баланс): {x.Police.VMax * 3.6f:0} км/ч, A {x.Police.A:0.00} м/с², k {x.Police.K:0.000}, " +
                          $"сцепление {x.Police.ALat:0.0}, тормоз {x.Police.Brake:0.0} м/с². Черты дома нет: погоня кончается правилом «ушёл» или у базы.");
            md.AppendLine();
            md.AppendLine($"Участок {d.StationId} (узел {d.StationNode}), мест на стоянке {d.Stalls.Length}, возрождение ({d.Respawn.x:0}, {d.Respawn.y:0}).");
            md.AppendLine();
            md.AppendLine(x.NoPoliceLine);
            md.AppendLine();
            md.AppendLine("| Петля | Длина | Круг (≤35 км/ч) | Районы | По дорогам, м |");
            md.AppendLine("|---|---|---|---|---|");
            foreach (PoliceLoop l in d.Loops)
            {
                string roads = string.Join(", ", LoopDistricts(x, l).Select(kv => $"{(kv.Key == "" ? "вне районов" : kv.Key)} {kv.Value:0}"));
                md.AppendLine($"| {l.Name} | {l.Length:0} м | {l.Lap:0} с | {string.Join(", ", l.Districts)} | {roads} |");
                if (l.Lap < 120f || l.Lap > 200f) x.Warnings.Add($"loop {l.Name}: lap {l.Lap:0} s is outside 120-200 s");
            }
            md.AppendLine();
            md.AppendLine($"День: патруль {string.Join(" + ", day.LoopNames)} + резерв на стоянке; ночь: {string.Join(" + ", night.LoopNames)} + резерв.");
            md.AppendLine();

            // District presence.
            md.AppendLine("Присутствие полиции по районам (PoliceConfig.Presence; остальные районы — строка «*»):");
            md.AppendLine();
            md.AppendLine("| Район | Патруль | Шанс машины на вызов свидетеля | Задержка, с | Доп. машин |");
            md.AppendLine("|---|---|---|---|---|");
            foreach (PolicePresenceDef row in (c.Presence ?? new PolicePresenceDef[0]).Append(c.DefaultPresence).Where(r => r != null))
                md.AppendLine($"| {row.District} | {row.Patrol:0.##}{(row.Patrol < c.PatrolMinPresence ? " (без петель)" : "")} | {row.DispatchChance:0%} | {row.DispatchDelay:+0;-0;0} | {row.ExtraCars} |");
            md.AppendLine();

            // Table A: van drive hotspot -> base.
            md.AppendLine("### A. Бусик от точки до базы: длина · без торможений / быстрый / **эталон**, с");
            md.AppendLine();
            md.AppendLine("| Точка | " + string.Join(" | ", d.BaseIds.Select(b => "→ " + b)) + " |");
            md.AppendLine("|---|" + string.Concat(Enumerable.Repeat("---|", nb)));
            foreach (PoliceHotspot h in d.Hotspots)
            {
                h.VanTime = new float[nb];
                h.VanLength = new float[nb];
                var cells = new List<string>();
                for (int b = 0; b < nb; b++)
                {
                    VanRoute r = Route(x, h.Node, d.BaseNodes[b]);
                    VanRoute f = Route(x, h.Node, d.BaseNodes[b], true);
                    h.VanTime[b] = r.Total;
                    h.VanLength[b] = r.Length;
                    cells.Add(r.Pts.Count < 2 ? "—" : $"{r.Length:0} м · {r.Length / x.VanRef.VMax:0} / {f.Total:0} / **{r.Total:0}**");
                }
                md.AppendLine($"| {h.Name} | {string.Join(" | ", cells)} |");
            }
            md.AppendLine();

            // Table B: response.
            md.AppendLine("### B. Отклик (тревога → первая машина на месте, с задержкой района; если машину вообще шлют), с: медиана / p90");
            md.AppendLine();
            md.AppendLine($"| Точка | Район (шанс) | Только машина на стоянке | День ({string.Join("+", day.LoopNames)} + резерв) | Ночь ({string.Join("+", night.LoopNames)} + резерв) |");
            md.AppendLine("|---|---|---|---|---|");
            foreach (PoliceHotspot h in d.Hotspots)
            {
                PolicePresenceDef p = c.PresenceOf(h.District);
                h.RespParked = Mathf.Max(1f, day.Radio + p.DispatchDelay) + c.BoardingTime + PoliceTime(x, d.StationNode, h.Node);
                (h.RespDay, h.RespDayP90) = Response(x, day, h);
                (h.RespNight, h.RespNightP90) = Response(x, night, h);
                md.AppendLine($"| {h.Name} | {h.District ?? "—"} ({p.DispatchChance:0%}) | {h.RespParked:0} | {h.RespDay:0} / {h.RespDayP90:0} | {h.RespNight:0} / {h.RespNightP90:0} |");
                float limit = (h.Core ? 30f : 35f) + Mathf.Max(0f, p.DispatchDelay);
                if (h.RespDayP90 > limit) x.Warnings.Add($"response p90 at {h.Name} by day is {h.RespDayP90:0.0} s (> {limit:0} s)");
            }
            md.AppendLine();

            // Station check.
            for (int b = 0; b < nb; b++)
            {
                float t = PoliceTime(x, d.StationNode, d.BaseNodes[b]);
                if (t < 35f) x.Warnings.Add($"station {d.StationId} is {t:0.0} s of police driving from {d.BaseIds[b]} (< 35 s)");
            }
        }

        private static (float med, float p90) Response(Ctx x, Mode m, PoliceHotspot h)
        {
            int n = Mathf.Max(1, m.Samples.Count > 0 ? m.Samples.Max(s => s.Count) : 1);
            var resp = new List<float>();
            float radio = Mathf.Max(1f, m.Radio + x.C.PresenceOf(h.District).DispatchDelay);
            for (int k = 0; k < n; k++)
            {
                float best = radio + x.C.BoardingTime + PoliceTime(x, x.D.StationNode, h.Node);
                foreach (List<int> s in m.Samples)
                    if (s.Count > 0) best = Mathf.Min(best, radio + PoliceTime(x, s[k % s.Count], h.Node));
                resp.Add(best);
            }
            return (Median(resp), Percentile(resp, 0.9f));
        }

        // ---------- JSON helpers ----------

        private static IEnumerable<object> List(Dictionary<string, object> o, string key) =>
            o.TryGetValue(key, out object v) && v is List<object> list ? list : Enumerable.Empty<object>();

        private static string Str(Dictionary<string, object> o, string key) => o.TryGetValue(key, out object v) && v is string s ? s : null;

        private static Vector2 Vec(object o)
        {
            var list = (List<object>)o;
            return new Vector2((float)(double)list[0], (float)(double)list[1]);
        }

        private sealed class Heap
        {
            private readonly List<(float key, int value)> _items = new();
            public int Count => _items.Count;

            public void Push(float key, int value)
            {
                _items.Add((key, value));
                int i = _items.Count - 1;
                while (i > 0)
                {
                    int p = (i - 1) / 2;
                    if (_items[p].key <= key) break;
                    _items[i] = _items[p];
                    i = p;
                }
                _items[i] = (key, value);
            }

            public void Pop(out float key, out int value)
            {
                (key, value) = _items[0];
                var last = _items[_items.Count - 1];
                _items.RemoveAt(_items.Count - 1);
                if (_items.Count == 0) return;
                int i = 0;
                while (true)
                {
                    int c = 2 * i + 1;
                    if (c >= _items.Count) break;
                    if (c + 1 < _items.Count && _items[c + 1].key < _items[c].key) c++;
                    if (_items[c].key >= last.key) break;
                    _items[i] = _items[c];
                    i = c;
                }
                _items[i] = last;
            }
        }
    }
}
