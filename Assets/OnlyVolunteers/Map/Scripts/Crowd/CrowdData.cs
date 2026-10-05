using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace OnlyVolunteers.Map.Crowd
{
    public enum CrowdActivity : byte
    {
        BenchSit, BeachLie, ShopQueue, SmokeCorner, Playground, BusWait, Kiosk, BarDoor, ChurchSteps, CasinoDoor, Other,
    }

    // Edge/node profile bits: who may walk there. Beach routes are for beach walkers only (town walkers and police keep
    // off the sand, crowd_v12 runtime_contract.profile_policy); everything else is open to everyone.
    [Flags]
    public enum CrowdProfile : byte { Town = 1, Beach = 2, All = Town | Beach }

    public sealed class CrowdDistrict
    {
        public string Id, Name;
        public int Day, Evening;
        public readonly List<int> Routes = new();
        public readonly List<int> Spawns = new();

        public float Target(float evening) => Mathf.Lerp(Day, Evening, Mathf.Clamp01(evening));
    }

    public sealed class CrowdRoute
    {
        public string Id;
        public int District;
        public CrowdProfile Profile;
        public Vector2 Speed;
        // Plan points (x east, y north) without the closing duplicate; the loop wraps from the last back to the first.
        public Vector2[] Points;
        public float Length;
        public readonly List<int> Pois = new();

        public int Wrap(int i) => ((i % Points.Length) + Points.Length) % Points.Length;

        /// <summary>The loop vertex where a point on the loop is reached: the nearer end of the loop segment closest to p.</summary>
        public int NearestOnSegment(Vector2 p)
        {
            int best = 0;
            float bestSq = float.MaxValue;
            for (int i = 0; i < Points.Length; i++)
            {
                Vector2 a = Points[i], ab = Points[(i + 1) % Points.Length] - a;
                float len2 = ab.sqrMagnitude;
                float t = len2 > 1e-6f ? Mathf.Clamp01(((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / len2) : 0f;
                float d = (a + ab * t - p).sqrMagnitude;
                if (d < bestSq)
                {
                    bestSq = d;
                    best = t < 0.5f ? i : (i + 1) % Points.Length;
                }
            }
            return best;
        }

        public int Nearest(Vector2 p)
        {
            int best = 0;
            float bestSq = float.MaxValue;
            for (int i = 0; i < Points.Length; i++)
            {
                float d = (Points[i] - p).sqrMagnitude;
                if (d < bestSq)
                {
                    bestSq = d;
                    best = i;
                }
            }
            return best;
        }
    }

    public sealed class CrowdPoi
    {
        public string Id;
        public int District, Route;
        public CrowdActivity Activity;
        public Vector2 Position;
        public int Capacity;
        public Vector2 Dwell;
        // Access link from the POI to its route (first point at the POI, last on the route) and the route vertex it meets.
        public Vector2[] Access;
        public int RouteIndex;
        // Unit plan direction from the POI out along its access link (towards the path).
        public Vector2 Out;
        // Walker in each slot (null = free).
        public CrowdWalker[] Slots;
    }

    public sealed class CrowdSpawn
    {
        public string Id;
        public int District;
        public Vector2 Position;
        public float MinPlayerDistance, Grace;
        // Runtime: world feet position, time it last became hidden (float.MaxValue = visible now), last spawn time.
        public Vector3 World;
        public float HiddenSince = float.MaxValue, LastUsed = -999f;
    }

    public sealed class CrowdHotspot
    {
        public string Id;
        public int District;
        public Vector2 Position;
        public float Radius;
        public int EyesDay, EyesEvening;
    }

    public sealed class CrowdCrossing
    {
        public string Id;
        public bool Zebra;
        public Vector2[] Polygon;
        public Rect Bounds;

        public bool Contains(Vector2 p)
        {
            if (!Bounds.Contains(p)) return false;
            bool inside = false;
            for (int i = 0, j = Polygon.Length - 1; i < Polygon.Length; j = i++)
            {
                Vector2 a = Polygon[i], b = Polygon[j];
                if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) inside = !inside;
            }
            return inside;
        }
    }

    public sealed class CrowdPatrol
    {
        public string Id;
        public Vector2[] Points;
        public int Officers;
        public Vector2 Speed, Pause;
        public readonly List<int> Districts = new();
    }

    // crowd_vNN.json (ArtSource/References/Map/Crowd, copied to Map/Data as a TextAsset) as runtime data: districts with
    // day/evening walker counts, looping routes, POIs with activities, hidden spawn/despawn points, witness hotspots, the
    // police loop, zebras/junctions, and one walk graph built from every polyline (routes, links, patrol) for paths off
    // the loops (joining a route, running to report, walking to a despawn point). Plan (x, y) -> Unity (x, ground, y).
    public sealed class CrowdData
    {
        public string Revision;
        public readonly List<CrowdDistrict> Districts = new();
        public readonly List<CrowdRoute> Routes = new();
        public readonly List<CrowdPoi> Pois = new();
        public readonly List<CrowdSpawn> Spawns = new();
        public readonly List<CrowdHotspot> Hotspots = new();
        public readonly List<CrowdCrossing> Crossings = new();
        public CrowdPatrol Patrol;
        public readonly CrowdGraph Graph = new();

        private const float CrossingCell = 16f;
        private readonly Dictionary<(int, int), List<int>> _crossingGrid = new();

        public int DistrictIndex(string id)
        {
            for (int i = 0; i < Districts.Count; i++)
                if (Districts[i].Id == id) return i;
            return -1;
        }

        public static CrowdData Parse(string json)
        {
            var root = (Dictionary<string, object>)MiniJson.Parse(json);
            var data = new CrowdData { Revision = Str(root, "revision") };
            var routeIndex = new Dictionary<string, int>();
            var poiIndex = new Dictionary<string, int>();
            var spawnIndex = new Dictionary<string, int>();

            foreach (Dictionary<string, object> d in Objects(root, "districts"))
                data.Districts.Add(new CrowdDistrict
                {
                    Id = Str(d, "id"), Name = Str(d, "name_ru"), Day = (int)Num(d, "walkers_day"), Evening = (int)Num(d, "walkers_evening"),
                });

            foreach (Dictionary<string, object> r in Objects(root, "routes"))
            {
                var route = new CrowdRoute
                {
                    Id = Str(r, "id"), District = data.DistrictIndex(Str(r, "district_id")),
                    Profile = Str(r, "profile") == "beach_walker" ? CrowdProfile.Beach : CrowdProfile.Town,
                    Speed = Pair(r, "speed_mps", new Vector2(1.1f, 1.4f)), Points = Loop(Polyline(r, "polyline_m")),
                };
                route.Length = LoopLength(route.Points);
                routeIndex[route.Id] = data.Routes.Count;
                if (route.District >= 0) data.Districts[route.District].Routes.Add(data.Routes.Count);
                data.Routes.Add(route);
                data.Graph.AddPolyline(Polyline(r, "polyline_m"), route.Profile);
            }

            foreach (Dictionary<string, object> p in Objects(root, "points_of_interest"))
            {
                var poi = new CrowdPoi
                {
                    Id = Str(p, "id"), District = data.DistrictIndex(Str(p, "district_id")), Activity = ParseActivity(Str(p, "activity")),
                    Position = Vec(p, "position_m"), Capacity = Mathf.Max(1, (int)Num(p, "capacity", 1)), Dwell = Pair(p, "dwell_s", new Vector2(10f, 40f)),
                    Route = routeIndex.TryGetValue(Str(p, "route_id"), out int ri) ? ri : -1,
                };
                poi.Slots = new CrowdWalker[poi.Capacity];
                poiIndex[poi.Id] = data.Pois.Count;
                data.Pois.Add(poi);
            }

            foreach (Dictionary<string, object> s in Objects(root, "spawn_despawn_points"))
            {
                var spawn = new CrowdSpawn
                {
                    Id = Str(s, "id"), District = data.DistrictIndex(Str(s, "district_id")), Position = Vec(s, "position_m"),
                    MinPlayerDistance = Num(s, "min_player_distance_m", 25f), Grace = Num(s, "visibility_grace_s", 2f),
                };
                spawnIndex[spawn.Id] = data.Spawns.Count;
                if (spawn.District >= 0) data.Districts[spawn.District].Spawns.Add(data.Spawns.Count);
                data.Spawns.Add(spawn);
            }

            foreach (Dictionary<string, object> h in Objects(root, "witness_hotspots"))
                data.Hotspots.Add(new CrowdHotspot
                {
                    Id = Str(h, "id"), District = data.DistrictIndex(Str(h, "district_id")), Position = Vec(h, "position_m"),
                    Radius = Num(h, "radius_m", 15f), EyesDay = (int)Num(h, "expected_eyes_day"), EyesEvening = (int)Num(h, "expected_eyes_evening"),
                });

            if (root.TryGetValue("police_patrol", out object patrolObj) && patrolObj is Dictionary<string, object> patrol)
            {
                data.Patrol = new CrowdPatrol
                {
                    Id = Str(patrol, "id"), Points = Loop(Polyline(patrol, "polyline_m")), Officers = (int)Num(patrol, "officers", 2f),
                    Speed = Pair(patrol, "speed_mps", new Vector2(1.15f, 1.45f)), Pause = Pair(patrol, "pause_at_anchors_s", new Vector2(5f, 15f)),
                };
                if (patrol.TryGetValue("district_ids", out object ids) && ids is List<object> idList)
                    foreach (object id in idList)
                    {
                        int di = data.DistrictIndex(id as string);
                        if (di >= 0) data.Patrol.Districts.Add(di);
                    }
                data.Graph.AddPolyline(Polyline(patrol, "polyline_m"), CrowdProfile.Town);
            }

            foreach (Dictionary<string, object> c in Objects(root, "connections"))
            {
                Vector2[] line = Polyline(c, "polyline_m");
                CrowdProfile profile = Str(c, "profile") == "beach_walker" ? CrowdProfile.Beach : CrowdProfile.Town;
                data.Graph.AddPolyline(line, profile);
                if (line.Length < 2) continue;
                data.Graph.AttachLater(line[0]);
                data.Graph.AttachLater(line[line.Length - 1]);
                if (Str(c, "purpose") == "activity_access" && poiIndex.TryGetValue(Str(c, "point_id"), out int pi))
                {
                    CrowdPoi poi = data.Pois[pi];
                    poi.Access = line;
                    if (poi.Route >= 0) poi.RouteIndex = data.Routes[poi.Route].NearestOnSegment(line[line.Length - 1]);
                    Vector2 outward = line[1] - line[0];
                    poi.Out = outward.sqrMagnitude > 1e-6f ? outward.normalized : Vector2.up;
                }
            }

            foreach (CrowdPoi poi in data.Pois)
            {
                if (poi.Access == null)
                {
                    // No access link: walk straight from the nearest route vertex.
                    if (poi.Route < 0) continue;
                    CrowdRoute route = data.Routes[poi.Route];
                    poi.RouteIndex = route.Nearest(poi.Position);
                    poi.Access = new[] { poi.Position, route.Points[poi.RouteIndex] };
                    Vector2 outward = route.Points[poi.RouteIndex] - poi.Position;
                    poi.Out = outward.sqrMagnitude > 1e-6f ? outward.normalized : Vector2.up;
                }
                if (poi.Route >= 0) data.Routes[poi.Route].Pois.Add(data.Pois.IndexOf(poi));
            }

            foreach (Dictionary<string, object> c in Objects(root, "allowed_crossings"))
            {
                Vector2[] polygon = Polyline(c, "polygon_m");
                if (polygon.Length < 3) continue;
                Vector2 min = polygon[0], max = polygon[0];
                foreach (Vector2 v in polygon)
                {
                    min = Vector2.Min(min, v);
                    max = Vector2.Max(max, v);
                }
                int index = data.Crossings.Count;
                data.Crossings.Add(new CrowdCrossing { Id = Str(c, "id"), Zebra = Str(c, "kind") == "zebra", Polygon = polygon, Bounds = Rect.MinMaxRect(min.x, min.y, max.x, max.y) });
                for (int x = Mathf.FloorToInt(min.x / CrossingCell); x <= Mathf.FloorToInt(max.x / CrossingCell); x++)
                    for (int y = Mathf.FloorToInt(min.y / CrossingCell); y <= Mathf.FloorToInt(max.y / CrossingCell); y++)
                    {
                        if (!data._crossingGrid.TryGetValue((x, y), out List<int> list)) data._crossingGrid[(x, y)] = list = new List<int>();
                        list.Add(index);
                    }
            }

            data.Graph.Finish();
            return data;
        }

        /// <summary>Index of the zebra or junction polygon containing plan point p, or -1.</summary>
        public int CrossingAt(Vector2 p)
        {
            if (!_crossingGrid.TryGetValue((Mathf.FloorToInt(p.x / CrossingCell), Mathf.FloorToInt(p.y / CrossingCell)), out List<int> list)) return -1;
            foreach (int i in list)
                if (Crossings[i].Contains(p)) return i;
            return -1;
        }

        public static CrowdActivity ParseActivity(string tag) => tag switch
        {
            "bench_sit" => CrowdActivity.BenchSit,
            "beach_lie" => CrowdActivity.BeachLie,
            "shop_queue" => CrowdActivity.ShopQueue,
            "smoke_corner" => CrowdActivity.SmokeCorner,
            "playground" => CrowdActivity.Playground,
            "bus_wait" => CrowdActivity.BusWait,
            "kiosk" => CrowdActivity.Kiosk,
            "bar_door" => CrowdActivity.BarDoor,
            "church_steps" => CrowdActivity.ChurchSteps,
            "casino_door" => CrowdActivity.CasinoDoor,
            _ => CrowdActivity.Other,
        };

        public static float LoopLength(Vector2[] points)
        {
            float length = 0f;
            for (int i = 0; i < points.Length; i++) length += Vector2.Distance(points[i], points[(i + 1) % points.Length]);
            return length;
        }

        // ---------- JSON helpers ----------

        private static IEnumerable<object> Objects(Dictionary<string, object> o, string key) =>
            o.TryGetValue(key, out object v) && v is List<object> list ? list : (IEnumerable<object>)Array.Empty<object>();

        private static string Str(Dictionary<string, object> o, string key) => o.TryGetValue(key, out object v) ? v as string : null;

        private static float Num(Dictionary<string, object> o, string key, float fallback = 0f) =>
            o.TryGetValue(key, out object v) && v is double d ? (float)d : fallback;

        private static Vector2 Vec(Dictionary<string, object> o, string key) =>
            o.TryGetValue(key, out object v) && v is List<object> l && l.Count >= 2 ? new Vector2(F(l[0]), F(l[1])) : Vector2.zero;

        private static Vector2 Pair(Dictionary<string, object> o, string key, Vector2 fallback) =>
            o.TryGetValue(key, out object v) && v is List<object> l && l.Count >= 2 ? new Vector2(F(l[0]), F(l[1])) : fallback;

        private static Vector2[] Polyline(Dictionary<string, object> o, string key)
        {
            if (!o.TryGetValue(key, out object v) || !(v is List<object> list)) return Array.Empty<Vector2>();
            var points = new List<Vector2>(list.Count);
            foreach (object item in list)
                if (item is List<object> xy && xy.Count >= 2) points.Add(new Vector2(F(xy[0]), F(xy[1])));
            return points.ToArray();
        }

        // A closed polyline without its closing duplicate (the last point repeats the first).
        private static Vector2[] Loop(Vector2[] points)
        {
            if (points.Length > 2 && (points[0] - points[points.Length - 1]).sqrMagnitude < 0.01f)
            {
                var trimmed = new Vector2[points.Length - 1];
                Array.Copy(points, trimmed, trimmed.Length);
                return trimmed;
            }
            return points;
        }

        private static float F(object o) => o is double d ? (float)d : 0f;
    }

    // Undirected walk graph over every polyline of the crowd file. Vertices closer than MergeDistance share one node;
    // a link end that lies on another polyline's segment rather than on a vertex (crowd_v12: 12 POI links meet their
    // route mid-segment) is spliced into that segment (AttachLater, done in Finish). Each edge keeps the profile of the
    // polyline it came from; A* only uses edges open to the walker's profile.
    public sealed class CrowdGraph
    {
        private const float MergeDistance = 0.05f, Cell = 10f, AttachDistance = 0.3f;

        public readonly List<Vector2> Nodes = new();
        private readonly List<List<(int to, float cost, CrowdProfile profile)>> _edges = new();
        private readonly List<CrowdProfile> _nodeProfile = new();
        private readonly Dictionary<(int, int), int> _keys = new();
        private readonly Dictionary<(int, int), List<int>> _grid = new();
        private readonly List<Vector2> _attach = new();

        // A* scratch (reused, the graph is static after Finish).
        private float[] _g;
        private int[] _from, _stamp;
        private bool[] _closed;
        private int _search;
        private readonly List<(float f, int node)> _heap = new();

        public int Count => Nodes.Count;

        public void AddPolyline(Vector2[] points, CrowdProfile profile)
        {
            int previous = -1;
            foreach (Vector2 p in points)
            {
                int node = Node(p);
                if (previous >= 0 && previous != node) Link(previous, node, profile);
                previous = node;
            }
        }

        /// <summary>Splice this polyline end into whatever segment it lies on, once every polyline is in (Finish).</summary>
        public void AttachLater(Vector2 p) => _attach.Add(p);

        public void Finish()
        {
            foreach (Vector2 p in _attach) Splice(Node(p));
            _attach.Clear();
            for (int i = 0; i < Nodes.Count; i++)
            {
                var key = (Mathf.FloorToInt(Nodes[i].x / Cell), Mathf.FloorToInt(Nodes[i].y / Cell));
                if (!_grid.TryGetValue(key, out List<int> list)) _grid[key] = list = new List<int>();
                list.Add(i);
            }
            _g = new float[Nodes.Count];
            _from = new int[Nodes.Count];
            _stamp = new int[Nodes.Count];
            _closed = new bool[Nodes.Count];
        }

        private int Node(Vector2 p)
        {
            var key = (Mathf.RoundToInt(p.x / MergeDistance), Mathf.RoundToInt(p.y / MergeDistance));
            if (_keys.TryGetValue(key, out int node)) return node;
            node = Nodes.Count;
            _keys[key] = node;
            Nodes.Add(p);
            _edges.Add(new List<(int, float, CrowdProfile)>(2));
            _nodeProfile.Add(0);
            return node;
        }

        // Node n lies on edge (u, v) (closer than AttachDistance, strictly between its ends): split it into (u, n), (n, v).
        private void Splice(int n)
        {
            Vector2 p = Nodes[n];
            int bestU = -1, bestK = -1;
            float bestDist = AttachDistance;
            for (int u = 0; u < Nodes.Count; u++)
            {
                if (u == n) continue;
                List<(int to, float cost, CrowdProfile profile)> edges = _edges[u];
                for (int k = 0; k < edges.Count; k++)
                {
                    int v = edges[k].to;
                    if (v <= u || v == n) continue; // each undirected edge once
                    Vector2 a = Nodes[u], ab = Nodes[v] - a;
                    float len2 = ab.sqrMagnitude;
                    if (len2 < 1e-6f) continue;
                    float t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / len2;
                    if (t <= 0.01f || t >= 0.99f) continue;
                    float dist = (a + ab * t - p).magnitude;
                    if (dist < bestDist)
                    {
                        bestDist = dist;
                        bestU = u;
                        bestK = k;
                    }
                }
            }
            if (bestU < 0) return;
            (int to, float _, CrowdProfile profile) edge = _edges[bestU][bestK];
            int w = edge.to;
            _edges[bestU].RemoveAt(bestK);
            _edges[w].RemoveAll(e => e.to == bestU && e.profile == edge.profile);
            Link(bestU, n, edge.profile);
            Link(n, w, edge.profile);
        }

        private void Link(int a, int b, CrowdProfile profile)
        {
            float cost = Vector2.Distance(Nodes[a], Nodes[b]);
            _edges[a].Add((b, cost, profile));
            _edges[b].Add((a, cost, profile));
            _nodeProfile[a] |= profile;
            _nodeProfile[b] |= profile;
        }

        /// <summary>Nearest node open to 'profile' within maxDistance (plan metres), or -1.</summary>
        public int Nearest(Vector2 p, CrowdProfile profile, float maxDistance = 80f)
        {
            int cx = Mathf.FloorToInt(p.x / Cell), cy = Mathf.FloorToInt(p.y / Cell);
            int rings = Mathf.CeilToInt(maxDistance / Cell);
            int best = -1;
            float bestSq = maxDistance * maxDistance;
            for (int r = 0; r <= rings; r++)
            {
                for (int x = cx - r; x <= cx + r; x++)
                    for (int y = cy - r; y <= cy + r; y++)
                    {
                        if (Mathf.Abs(x - cx) != r && Mathf.Abs(y - cy) != r) continue; // ring r only
                        if (!_grid.TryGetValue((x, y), out List<int> list)) continue;
                        foreach (int n in list)
                        {
                            if ((_nodeProfile[n] & profile) == 0) continue;
                            float d = (Nodes[n] - p).sqrMagnitude;
                            if (d < bestSq)
                            {
                                bestSq = d;
                                best = n;
                            }
                        }
                    }
                // Anything in a later ring is at least r * Cell away.
                if (best >= 0 && bestSq <= (r * Cell) * (r * Cell)) break;
            }
            return best;
        }

        /// <summary>A* from node 'start' to node 'goal' over edges open to 'profile'. Appends the node positions (start
        /// excluded, goal included) to 'path'. False when there is no path.</summary>
        public bool FindPath(int start, int goal, CrowdProfile profile, List<Vector2> path)
        {
            if (start < 0 || goal < 0) return false;
            if (start == goal)
            {
                path.Add(Nodes[goal]);
                return true;
            }
            _search++;
            _heap.Clear();
            Visit(start, 0f, -1);
            Push(Heuristic(start, goal), start);
            while (_heap.Count > 0)
            {
                int node = Pop();
                if (_closed[node]) continue;
                _closed[node] = true;
                if (node == goal)
                {
                    int count = path.Count;
                    for (int n = goal; n != start; n = _from[n]) path.Add(Nodes[n]);
                    path.Reverse(count, path.Count - count);
                    return true;
                }
                foreach ((int to, float cost, CrowdProfile edgeProfile) in _edges[node])
                {
                    if ((edgeProfile & profile) == 0) continue;
                    float g = _g[node] + cost;
                    if (_stamp[to] == _search && (_closed[to] || g >= _g[to])) continue;
                    Visit(to, g, node);
                    Push(g + Heuristic(to, goal), to);
                }
            }
            return false;
        }

        private float Heuristic(int a, int b) => Vector2.Distance(Nodes[a], Nodes[b]);

        private void Visit(int node, float g, int from)
        {
            if (_stamp[node] != _search)
            {
                _stamp[node] = _search;
                _closed[node] = false;
            }
            _g[node] = g;
            _from[node] = from;
        }

        private void Push(float f, int node)
        {
            _heap.Add((f, node));
            int i = _heap.Count - 1;
            while (i > 0)
            {
                int parent = (i - 1) / 2;
                if (_heap[parent].f <= _heap[i].f) break;
                (_heap[parent], _heap[i]) = (_heap[i], _heap[parent]);
                i = parent;
            }
        }

        private int Pop()
        {
            int top = _heap[0].node;
            int last = _heap.Count - 1;
            _heap[0] = _heap[last];
            _heap.RemoveAt(last);
            int i = 0;
            while (true)
            {
                int l = 2 * i + 1, r = l + 1, smallest = i;
                if (l < _heap.Count && _heap[l].f < _heap[smallest].f) smallest = l;
                if (r < _heap.Count && _heap[r].f < _heap[smallest].f) smallest = r;
                if (smallest == i) break;
                (_heap[smallest], _heap[i]) = (_heap[i], _heap[smallest]);
                i = smallest;
            }
            return top;
        }
    }

    // Minimal JSON reader for the crowd file: objects -> Dictionary<string, object>, arrays -> List<object>, numbers ->
    // double, strings, bools, null. JsonUtility cannot read the nested [x, y] arrays of the polylines.
    public static class MiniJson
    {
        public static object Parse(string json)
        {
            int i = 0;
            object value = Value(json, ref i);
            return value;
        }

        private static object Value(string s, ref int i)
        {
            Skip(s, ref i);
            if (i >= s.Length) throw new FormatException("Unexpected end of JSON");
            char c = s[i];
            switch (c)
            {
                case '{': return Obj(s, ref i);
                case '[': return Arr(s, ref i);
                case '"': return Str(s, ref i);
                case 't': i += 4; return true;
                case 'f': i += 5; return false;
                case 'n': i += 4; return null;
                default: return Number(s, ref i);
            }
        }

        private static Dictionary<string, object> Obj(string s, ref int i)
        {
            var o = new Dictionary<string, object>();
            i++; // {
            while (true)
            {
                Skip(s, ref i);
                if (s[i] == '}')
                {
                    i++;
                    return o;
                }
                string key = Str(s, ref i);
                Skip(s, ref i);
                i++; // :
                o[key] = Value(s, ref i);
                Skip(s, ref i);
                if (s[i] == ',') i++;
            }
        }

        private static List<object> Arr(string s, ref int i)
        {
            var list = new List<object>();
            i++; // [
            while (true)
            {
                Skip(s, ref i);
                if (s[i] == ']')
                {
                    i++;
                    return list;
                }
                list.Add(Value(s, ref i));
                Skip(s, ref i);
                if (s[i] == ',') i++;
            }
        }

        private static string Str(string s, ref int i)
        {
            var sb = new StringBuilder();
            i++; // opening quote
            while (s[i] != '"')
            {
                char c = s[i++];
                if (c != '\\')
                {
                    sb.Append(c);
                    continue;
                }
                char e = s[i++];
                switch (e)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u':
                        sb.Append((char)int.Parse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                        i += 4;
                        break;
                    default: sb.Append(e); break;
                }
            }
            i++; // closing quote
            return sb.ToString();
        }

        private static double Number(string s, ref int i)
        {
            int start = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(start, i - start), NumberStyles.Float, CultureInfo.InvariantCulture);
        }

        private static void Skip(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }
    }
}
