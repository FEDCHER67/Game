using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    [System.Serializable]
    public sealed class PoliceLoop
    {
        public string Name;
        public string[] Districts = new string[0];
        // Signed edge sequence of the closed loop: e + 1 = along the edge (A -> B), -(e + 1) = against it.
        public int[] Edges = new int[0];
        public float Length, Lap, ScoreDay, ScoreNight;
    }

    [System.Serializable]
    public sealed class PoliceHotspot
    {
        public string Id, Name, District;
        public Vector2 Position;
        public int Node;
        public bool Core;
        // Per base (PoliceMapData.BaseIds order): the van's reference drive time to it (s, with VanPaceFactor) and its route
        // length (m) (the report's table A, the test's pace check).
        public float[] VanTime = new float[0], VanLength = new float[0];
        // Response (alert -> first unit there, s): one parked car only, day layout median / p90, night layout median / p90.
        public float RespParked, RespDay, RespDayP90, RespNight, RespNightP90;
    }

    // One route for a car to follow: plan points (x east, y north) and the road width of each segment.
    public sealed class PoliceRoute
    {
        public readonly List<Vector2> Points = new();
        public readonly List<float> Widths = new();
        public bool Loop;

        public void Clear()
        {
            Points.Clear();
            Widths.Clear();
            Loop = false;
        }

        public void Add(Vector2 p, float width)
        {
            if (Points.Count > 0 && (Points[Points.Count - 1] - p).sqrMagnitude < 0.01f) return;
            if (Points.Count > 0) Widths.Add(width);
            Points.Add(p);
        }

        public float Length()
        {
            float l = 0f;
            for (int i = 1; i < Points.Count; i++) l += Vector2.Distance(Points[i - 1], Points[i]);
            return l;
        }
    }

    // police_vNN.asset: the bake of one map plan (PoliceBaker, menu OnlyVolunteers/Map/Police/Bake Police Data). The van
    // road graph (+ the station lot), the bases (door, road node, safe radius), the station, its parking spaces and respawn
    // point, the patrol loops, the timing hotspots with the model's predictions, and a hash of the plan file (stale data
    // warns at build time). No drive-time-to-base fields any more (the home-line give-up is gone, 2026-10-07).
    // Runtime queries live here too: nearest edge, Dijkstra ETAs, A* routes for the cars.
    [CreateAssetMenu(menuName = "OnlyVolunteers/Police Map Data", fileName = "police_vNN")]
    public sealed class PoliceMapData : ScriptableObject
    {
        public const byte RoadEdge = 0, LotEdge = 1;

        [Header("Source")]
        public string Revision;
        public string PlanFile, PlanHash, BakedAt;
        [Tooltip("Hash of every bake input (plan, look file, crowd file, PoliceConfig, van numbers): a build re-bakes when it differs.")]
        public string InputsHash;
        [Tooltip("Crowd file the hotspots and districts came from (another revision's file = a fallback, warned at bake time).")]
        public string CrowdFile;

        [Header("Graph (plan metres)")]
        public Vector2[] Nodes = new Vector2[0];
        public int[] EdgeA = new int[0], EdgeB = new int[0];
        public float[] EdgeLength = new float[0], EdgeWidth = new float[0];
        [Tooltip("Police car seconds along the edge (flying, along its road; junction turns are added by the router).")]
        public float[] EdgeTime = new float[0];
        public byte[] EdgeKind = new byte[0];
        [Tooltip("Not a police road (PoliceConfig.NoPoliceRoadClasses or narrower than MinRoadWidth): police routes and " +
                 "dispatch never use it; the van can escape through it.")]
        public bool[] EdgeNoPolice = new bool[0];

        [Header("Bases")]
        public string[] BaseIds = new string[0];
        public string[] BaseNames = new string[0];
        public Vector2[] BaseDoors = new Vector2[0];
        public int[] BaseNodes = new int[0];
        public float SafeRadius = 60f;

        [Header("Station")]
        public string StationId;
        public Vector2 StationCenter, Entrance, Respawn;
        public float RespawnYaw;
        public int StationNode = -1;
        [Tooltip("Parking spaces: plan x, plan y, Unity yaw (the car faces the aisle).")]
        public Vector3[] Stalls = new Vector3[0];
        public int[] StallNodes = new int[0];

        [Header("Patrol and hotspots")]
        public PoliceLoop[] Loops = new PoliceLoop[0];
        public PoliceHotspot[] Hotspots = new PoliceHotspot[0];
        [TextArea(4, 30)] public string Report;

        [Header("Van pace model")]
        public float VanA, VanK, VanVMaxKmh, VanPaceFactor = 1f;

        // ---------- Runtime caches (built on first use) ----------
        [System.NonSerialized] private int[] _adjStart, _adjEdge;
        [System.NonSerialized] private Dictionary<int, List<int>> _grid;
        [System.NonSerialized] private bool[][] _inDisc;
        [System.NonSerialized] private float[] _g, _eta;
        [System.NonSerialized] private int[] _stamp, _prevEdge;
        [System.NonSerialized] private Vector2[] _inDir;
        [System.NonSerialized] private int _generation;
        [System.NonSerialized] private MinHeap _heap;
        [System.NonSerialized] private bool _byLength;
        [System.NonSerialized] private List<int> _pathNodes;
        private const float GridCellSize = 16f;
        private const float PoliceVMax = 32f; // A* heuristic: no police car is faster (m/s)

        public int NodeCount => Nodes.Length;
        public int EdgeCount => EdgeA.Length;
        public int BaseCount => BaseIds.Length;

        public int BaseIndex(string id) => System.Array.IndexOf(BaseIds, id);

        public Vector2 EdgePoint(int e, float t) => Vector2.Lerp(Nodes[EdgeA[e]], Nodes[EdgeB[e]], t);

        // ---------- Bases ----------

        public float DoorDistance(int b, Vector2 p) => b < 0 || b >= BaseCount ? float.PositiveInfinity : Vector2.Distance(BaseDoors[b], p);

        // ---------- Graph ----------

        private void EnsureGraph()
        {
            if (_adjStart != null && _adjStart.Length == NodeCount + 1) return;
            int n = NodeCount, m = EdgeCount;
            _adjStart = new int[n + 1];
            for (int e = 0; e < m; e++)
            {
                _adjStart[EdgeA[e] + 1]++;
                _adjStart[EdgeB[e] + 1]++;
            }
            for (int i = 0; i < n; i++) _adjStart[i + 1] += _adjStart[i];
            _adjEdge = new int[2 * m];
            var fill = new int[n];
            for (int e = 0; e < m; e++)
            {
                _adjEdge[_adjStart[EdgeA[e]] + fill[EdgeA[e]]++] = e;
                _adjEdge[_adjStart[EdgeB[e]] + fill[EdgeB[e]]++] = e;
            }
            _grid = new Dictionary<int, List<int>>();
            for (int e = 0; e < m; e++)
            {
                Vector2 a = Nodes[EdgeA[e]], b = Nodes[EdgeB[e]];
                int x0 = Cell(Mathf.Min(a.x, b.x)), x1 = Cell(Mathf.Max(a.x, b.x)), y0 = Cell(Mathf.Min(a.y, b.y)), y1 = Cell(Mathf.Max(a.y, b.y));
                for (int x = x0; x <= x1; x++)
                    for (int y = y0; y <= y1; y++)
                    {
                        int key = Key(x, y);
                        if (!_grid.TryGetValue(key, out List<int> list)) _grid[key] = list = new List<int>();
                        list.Add(e);
                    }
            }
            _g = new float[n];
            _eta = new float[n];
            _stamp = new int[n];
            _prevEdge = new int[n];
            _inDir = new Vector2[n];
            _heap = new MinHeap(256);
            _inDisc = new bool[BaseCount][];
        }

        private static int Cell(float v) => Mathf.FloorToInt(v / GridCellSize);
        private static int Key(int x, int y) => (x << 16) ^ (y & 0xFFFF);

        public int Other(int e, int node) => EdgeA[e] == node ? EdgeB[e] : EdgeA[e];

        /// <summary>Edges at a node (adjacency slice).</summary>
        public int Degree(int node)
        {
            EnsureGraph();
            return _adjStart[node + 1] - _adjStart[node];
        }

        public int EdgeAt(int node, int k) => _adjEdge[_adjStart[node] + k];

        /// <summary>Nearest edge to p within maxDistance: its index and the fraction t along it (A -> B).
        /// roadsOnly skips the station lot; police skips edges that are no police roads; avoidHome >= 0 skips the edges
        /// in that base's safe disc (a police goal is projected onto the nearest edge a police car may drive).</summary>
        public bool NearestEdge(Vector2 p, float maxDistance, bool roadsOnly, out int edge, out float t, out float distance,
            bool police = false, int avoidHome = -1)
        {
            EnsureGraph();
            edge = -1;
            t = 0f;
            distance = float.MaxValue;
            int cx = Cell(p.x), cy = Cell(p.y);
            int rings = Mathf.CeilToInt(maxDistance / GridCellSize);
            for (int r = 0; r <= rings; r++)
            {
                for (int dx = -r; dx <= r; dx++)
                    for (int dy = -r; dy <= r; dy++)
                    {
                        if (Mathf.Max(Mathf.Abs(dx), Mathf.Abs(dy)) != r) continue;
                        if (!_grid.TryGetValue(Key(cx + dx, cy + dy), out List<int> list)) continue;
                        foreach (int e in list)
                        {
                            if (roadsOnly && EdgeKind[e] != RoadEdge) continue;
                            if ((police || avoidHome >= 0) && Blocked(e, avoidHome, police)) continue;
                            float te = Project(e, p, out float d);
                            if (d < distance)
                            {
                                distance = d;
                                edge = e;
                                t = te;
                            }
                        }
                    }
                // Anything in a ring further out is at least (r * cell) away.
                if (edge >= 0 && distance <= r * GridCellSize) break;
            }
            return edge >= 0 && distance <= maxDistance;
        }

        public float Project(int e, Vector2 p, out float distance)
        {
            Vector2 a = Nodes[EdgeA[e]], ab = Nodes[EdgeB[e]] - a;
            float len2 = ab.sqrMagnitude;
            float t = len2 > 1e-6f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / len2) : 0f;
            distance = Vector2.Distance(a + ab * t, p);
            return t;
        }

        public bool InDisc(int b, int e)
        {
            EnsureGraph();
            if (b < 0 || b >= BaseCount) return false;
            if (_inDisc[b] == null)
            {
                var flags = new bool[EdgeCount];
                for (int k = 0; k < EdgeCount; k++)
                {
                    Project(k, BaseDoors[b], out float d);
                    flags[k] = d < SafeRadius;
                }
                _inDisc[b] = flags;
            }
            return _inDisc[b][e];
        }

        public bool NoPolice(int e) => e >= 0 && e < EdgeNoPolice.Length && EdgeNoPolice[e];

        private bool Blocked(int e, int homeBase, bool police) => (police && NoPolice(e)) || (homeBase >= 0 && InDisc(homeBase, e));

        // ---------- ETAs (one Dijkstra per alert) ----------

        /// <summary>Police seconds from plan point 'from' to every node over the edge times (no turn penalties), into an
        /// internal array read with EtaTo. Blocked: edges that are no police roads and the home base's safe disc.</summary>
        public void ComputeEtas(Vector2 from, int homeBase)
        {
            EnsureGraph();
            for (int i = 0; i < NodeCount; i++) _eta[i] = float.PositiveInfinity;
            if (!NearestEdge(from, 120f, false, out int e0, out float t0, out _, true, homeBase)) return;
            _heap.Clear();
            Relax(EdgeA[e0], EdgeTime[e0] * t0);
            Relax(EdgeB[e0], EdgeTime[e0] * (1f - t0));
            while (_heap.Count > 0)
            {
                _heap.Pop(out float d, out int u);
                if (d > _eta[u]) continue;
                for (int k = _adjStart[u]; k < _adjStart[u + 1]; k++)
                {
                    int e = _adjEdge[k];
                    if (Blocked(e, homeBase, true)) continue;
                    Relax(Other(e, u), d + EdgeTime[e]);
                }
            }
        }

        private void Relax(int node, float d)
        {
            if (d >= _eta[node]) return;
            _eta[node] = d;
            _heap.Push(d, node);
        }

        /// <summary>Seconds from the last ComputeEtas origin to plan point p (via its nearest edge).</summary>
        public float EtaTo(Vector2 p) => EtaTo(p, out _);

        /// <summary>As EtaTo, plus the direction the car drives in when it gets there (along the edge from the end it
        /// arrives by).</summary>
        public float EtaTo(Vector2 p, out Vector2 arriving)
        {
            arriving = Vector2.zero;
            if (!NearestEdge(p, 120f, false, out int e, out float t, out float off)) return float.PositiveInfinity;
            float viaA = _eta[EdgeA[e]] + EdgeTime[e] * t, viaB = _eta[EdgeB[e]] + EdgeTime[e] * (1f - t);
            Vector2 ab = (Nodes[EdgeB[e]] - Nodes[EdgeA[e]]).normalized;
            arriving = viaA <= viaB ? ab : -ab;
            return Mathf.Min(viaA, viaB) + off / 6f;
        }

        // ---------- Routes (A*) ----------

        /// <summary>Fastest route from 'from' (driving along 'heading') to 'to': edge times + turnPenalty * (turn /
        /// 90 deg)^2 at nodes + uTurnPenalty to start against the heading. Never through the home base's safe disc
        /// (homeBase -1 = none); police: never over edges that are no police roads. The goal is projected onto the nearest
        /// edge the route may use (a goal in the disc or an alley: its nearest open road). False (route cleared) when
        /// there is no way. byLength: the shortest route by metres over the roads only (no lot), as the bake's model drives the van.</summary>
        public bool FindRoute(Vector2 from, Vector2 heading, Vector2 to, int homeBase, bool police, float turnPenalty, float uTurnPenalty, PoliceRoute route,
            bool byLength = false)
        {
            route.Clear();
            EnsureGraph();
            _byLength = byLength;
            if (!NearestEdge(from, 150f, byLength, out int e0, out float t0, out _)) return false;
            if (!NearestEdge(to, 150f, byLength, out int eg, out float tg, out _, police, homeBase)) return false;
            Vector2 p0 = EdgePoint(e0, t0), pg = EdgePoint(eg, tg);
            Vector2 along0 = Nodes[EdgeB[e0]] - Nodes[EdgeA[e0]];
            float headingDot = heading.sqrMagnitude > 1e-4f ? Vector2.Dot(heading, along0) : 0f;
            float penaltyToA = headingDot > 0f ? uTurnPenalty : 0f, penaltyToB = headingDot < 0f ? uTurnPenalty : 0f;

            float best = float.PositiveInfinity;
            int bestNode = -1; // -1 + direct = same edge
            bool direct = false;
            if (e0 == eg)
            {
                float cost = Mathf.Abs(tg - t0) * Cost(e0) + (tg >= t0 ? penaltyToB : penaltyToA);
                best = cost;
                direct = true;
            }

            _generation++;
            _heap.Clear();
            Seed(EdgeA[e0], Cost(e0) * t0 + penaltyToA, e0, Nodes[EdgeA[e0]] - p0, to);
            Seed(EdgeB[e0], Cost(e0) * (1f - t0) + penaltyToB, e0, Nodes[EdgeB[e0]] - p0, to);
            int goalA = EdgeA[eg], goalB = EdgeB[eg];
            while (_heap.Count > 0)
            {
                _heap.Pop(out float f, out int u);
                if (f >= best) break;
                float gu = _g[u];
                if (f > gu + Heuristic(u, to) + 1e-3f) continue; // stale
                if (u == goalA || u == goalB)
                {
                    float extra = u == goalA ? Cost(eg) * tg : Cost(eg) * (1f - tg);
                    if (gu + extra < best)
                    {
                        best = gu + extra;
                        bestNode = u;
                        direct = false;
                    }
                }
                for (int k = _adjStart[u]; k < _adjStart[u + 1]; k++)
                {
                    int e = _adjEdge[k];
                    if (e == _prevEdge[u] || Blocked(e, homeBase, police) || (byLength && EdgeKind[e] != RoadEdge)) continue;
                    int v = Other(e, u);
                    Vector2 dir = Nodes[v] - Nodes[u];
                    float turn = Vector2.Angle(_inDir[u], dir) / 90f;
                    float g = gu + Cost(e) + turnPenalty * turn * turn;
                    if (_stamp[v] == _generation && g >= _g[v]) continue;
                    _stamp[v] = _generation;
                    _g[v] = g;
                    _prevEdge[v] = e;
                    _inDir[v] = dir;
                    _heap.Push(g + Heuristic(v, to), v);
                }
            }
            if (float.IsPositiveInfinity(best)) return false;
            route.Add(p0, EdgeWidth[e0]);
            if (!direct)
            {
                // Walk back from the goal node to the start edge.
                List<int> nodes = _pathNodes ??= new List<int>();
                nodes.Clear();
                int n = bestNode;
                for (int guard = 0; guard < NodeCount && n >= 0; guard++)
                {
                    nodes.Add(n);
                    int pe = _prevEdge[n];
                    if (pe == e0 && (n == EdgeA[e0] || n == EdgeB[e0])) break;
                    if (pe < 0) break;
                    n = Other(pe, n);
                }
                nodes.Reverse();
                for (int i = 0; i < nodes.Count; i++)
                {
                    int edge = i == 0 ? e0 : _prevEdge[nodes[i]];
                    route.Add(Nodes[nodes[i]], EdgeWidth[edge]);
                }
            }
            route.Add(pg, EdgeWidth[eg]);
            if (route.Points.Count < 2) route.Add(pg + (pg - p0).normalized * 0.5f, EdgeWidth[eg]);
            return route.Points.Count >= 2;
        }

        private void Seed(int node, float g, int viaEdge, Vector2 dir, Vector2 to)
        {
            if (_stamp[node] == _generation && g >= _g[node]) return;
            _stamp[node] = _generation;
            _g[node] = g;
            _prevEdge[node] = viaEdge;
            _inDir[node] = dir.sqrMagnitude > 1e-6f ? dir : Vector2.zero;
            _heap.Push(g + Heuristic(node, to), node);
        }

        private float Heuristic(int node, Vector2 to) => Vector2.Distance(Nodes[node], to) / (_byLength ? 1f : PoliceVMax);

        private float Cost(int e) => _byLength ? EdgeLength[e] : EdgeTime[e];

        /// <summary>The closed polyline of a patrol loop.</summary>
        public void LoopRoute(int loop, PoliceRoute route)
        {
            route.Clear();
            if (loop < 0 || loop >= Loops.Length) return;
            int[] edges = Loops[loop].Edges;
            for (int i = 0; i < edges.Length; i++)
            {
                int signed = edges[i];
                int e = Mathf.Abs(signed) - 1;
                int a = signed > 0 ? EdgeA[e] : EdgeB[e], b = signed > 0 ? EdgeB[e] : EdgeA[e];
                if (i == 0) route.Add(Nodes[a], EdgeWidth[e]);
                route.Add(Nodes[b], EdgeWidth[e]);
            }
            route.Loop = true;
        }

        // ---------- Heap ----------

        private sealed class MinHeap
        {
            private float[] _keys;
            private int[] _values;
            public int Count { get; private set; }

            public MinHeap(int capacity)
            {
                _keys = new float[capacity];
                _values = new int[capacity];
            }

            public void Clear() => Count = 0;

            public void Push(float key, int value)
            {
                if (Count == _keys.Length)
                {
                    System.Array.Resize(ref _keys, Count * 2);
                    System.Array.Resize(ref _values, Count * 2);
                }
                int i = Count++;
                while (i > 0)
                {
                    int parent = (i - 1) / 2;
                    if (_keys[parent] <= key) break;
                    _keys[i] = _keys[parent];
                    _values[i] = _values[parent];
                    i = parent;
                }
                _keys[i] = key;
                _values[i] = value;
            }

            public void Pop(out float key, out int value)
            {
                key = _keys[0];
                value = _values[0];
                Count--;
                if (Count == 0) return;
                float k = _keys[Count];
                int v = _values[Count];
                int i = 0;
                while (true)
                {
                    int c = 2 * i + 1;
                    if (c >= Count) break;
                    if (c + 1 < Count && _keys[c + 1] < _keys[c]) c++;
                    if (_keys[c] >= k) break;
                    _keys[i] = _keys[c];
                    _values[i] = _values[c];
                    i = c;
                }
                _keys[i] = k;
                _values[i] = v;
            }
        }
    }
}
