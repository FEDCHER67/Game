using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Audio
{
    public static class WaterQuery
    {
        private const float GridSize = 32f;
        private const int CacheSize = 32768;
        private struct Triangle
        {
            public Vector2 A, B, C, Min, Max;
            public float Y;
            public WaterKind Kind;
        }
        private struct GroundCell
        {
            public int X, Z;
            public float Height;
            public bool Valid, Hit;
        }

        private static Triangle[] _triangles;
        private static Dictionary<long, int[]> _grid;
        private static readonly GroundCell[] Ground = new GroundCell[CacheSize];
        private static readonly RaycastHit[] Hits = new RaycastHit[64];
        private static int _groundLayers;
        private static WaterData _data;
        public static WaterData Data
        {
            get
            {
                // AmbiencePlayer may initialize before our AfterSceneLoad callback. Resolve once on that first read.
                if (_grid == null) LoadActiveScene();
                return _data;
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void Reset()
        {
            SceneManager.sceneLoaded -= SceneLoaded;
            SceneManager.activeSceneChanged -= ActiveSceneChanged;
            _data = null;
            _triangles = null;
            _grid = null;
            ClearGroundCache();
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void Subscribe()
        {
            SceneManager.sceneLoaded += SceneLoaded;
            SceneManager.activeSceneChanged += ActiveSceneChanged;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Load() => LoadActiveScene();

        private static void SceneLoaded(Scene scene, LoadSceneMode mode) => LoadActiveScene();
        private static void ActiveSceneChanged(Scene previous, Scene current) => LoadActiveScene();

        private static void LoadActiveScene()
        {
            string resourcePath = RevisionResourcePath(SceneManager.GetActiveScene().name);
            WaterData data = resourcePath != null ? Resources.Load<WaterData>(resourcePath) : null;
            var ambience = Object.FindAnyObjectByType<AmbiencePlayer>();
            if (ambience != null && ambience.SceneData != null && ambience.SceneData.WaterOverride != null)
                data = ambience.SceneData.WaterOverride;
            if (data == null) data = Resources.Load<WaterData>("Water_latest");
            if (_grid == null || data != _data) Initialize(data);
            else ClearGroundCache();
        }

        private static string RevisionResourcePath(string sceneName)
        {
            // Same scene-name rule as AmbiencePlayer.TryCreate (Map_Look_v12_Play / Map_Greybox_v16).
            System.Text.RegularExpressions.Match revision =
                System.Text.RegularExpressions.Regex.Match(sceneName, @"_(v\d+)(_|$)");
            return revision.Success ? "Water_" + revision.Groups[1].Value : null;
        }

        public static void Initialize(WaterData data)
        {
            _data = data;
            _groundLayers = data != null ? data.GroundLayers.value : 1;
            InitializeGeometry(data != null ? data.Areas : null);
            ClearGroundCache();
        }

        // Also used by the offline geometry check; all allocations belong to initialization.
        public static void InitializeGeometry(WaterData.Area[] areas)
        {
            int count = 0;
            if (areas != null)
                for (int i = 0; i < areas.Length; i++)
                    if (areas[i] != null && areas[i].Triangles != null) count += areas[i].Triangles.Length / 6;
            _triangles = new Triangle[count];
            var buckets = new Dictionary<long, List<int>>();
            int at = 0;
            if (areas != null)
            {
                for (int i = 0; i < areas.Length; i++)
                {
                    WaterData.Area area = areas[i];
                    if (area == null || area.Triangles == null) continue;
                    float[] t = area.Triangles;
                    for (int k = 0; k + 5 < t.Length; k += 6)
                    {
                        var triangle = new Triangle
                        {
                            A = new Vector2(t[k], t[k + 1]), B = new Vector2(t[k + 2], t[k + 3]),
                            C = new Vector2(t[k + 4], t[k + 5]), Y = area.SurfaceY, Kind = area.Kind,
                            Min = new Vector2(Mathf.Min(t[k], Mathf.Min(t[k + 2], t[k + 4])), Mathf.Min(t[k + 1], Mathf.Min(t[k + 3], t[k + 5]))),
                            Max = new Vector2(Mathf.Max(t[k], Mathf.Max(t[k + 2], t[k + 4])), Mathf.Max(t[k + 1], Mathf.Max(t[k + 3], t[k + 5])))
                        };
                        _triangles[at] = triangle;
                        for (int z = Cell(triangle.Min.y); z <= Cell(triangle.Max.y); z++)
                            for (int x = Cell(triangle.Min.x); x <= Cell(triangle.Max.x); x++)
                            {
                                long key = Key(x, z);
                                if (!buckets.TryGetValue(key, out List<int> bucket))
                                {
                                    bucket = new List<int>();
                                    buckets.Add(key, bucket);
                                }
                                bucket.Add(at);
                            }
                        at++;
                    }
                }
            }
            _grid = new Dictionary<long, int[]>(buckets.Count);
            foreach (KeyValuePair<long, List<int>> pair in buckets) _grid.Add(pair.Key, pair.Value.ToArray());
        }

        /// <summary>Water geometry at x,z, independent of the caller's height; false outside the built surfaces.</summary>
        public static bool SurfaceAt(Vector3 p, out float surfaceY, out WaterKind kind)
        {
            surfaceY = float.NegativeInfinity;
            kind = default;
            if (_grid == null || !_grid.TryGetValue(Key(Cell(p.x), Cell(p.z)), out int[] candidates))
            { surfaceY = 0f; return false; }
            Vector2 point = new Vector2(p.x, p.z);
            bool found = false;
            for (int i = 0; i < candidates.Length; i++)
            {
                Triangle t = _triangles[candidates[i]];
                if (point.x < t.Min.x || point.x > t.Max.x || point.y < t.Min.y || point.y > t.Max.y ||
                    (found && t.Y <= surfaceY) || !Contains(point, t.A, t.B, t.C)) continue;
                surfaceY = t.Y;
                kind = t.Kind;
                found = true;
            }
            if (!found) surfaceY = 0f;
            return found;
        }

        /// <summary>Nonnegative water-column depth. Static ground below the surface is cached in 0.5 m cells.
        /// No ground hit (e.g. beyond the terrain's sea apron) returns zero, never an invented bed.</summary>
        public static float Depth(Vector3 p)
        {
            if (!SurfaceAt(p, out float y, out _)) return 0f;
            int x = Mathf.FloorToInt(p.x * 2f), z = Mathf.FloorToInt(p.z * 2f);
            int index = unchecked((x * 73856093) ^ (z * 19349663)) & (CacheSize - 1);
            GroundCell cached = Ground[index];
            if (!cached.Valid || cached.X != x || cached.Z != z)
            {
                cached = new GroundCell { Valid = true, X = x, Z = z };
                // Start just above the water: bridges above it do not become the water's bed.
                int hits = Physics.RaycastNonAlloc(new Vector3((x + 0.5f) * 0.5f, y + 0.05f, (z + 0.5f) * 0.5f),
                    Vector3.down, Hits, 2000f, _groundLayers, QueryTriggerInteraction.Ignore);
                float nearest = float.PositiveInfinity;
                for (int i = 0; i < hits; i++)
                {
                    Collider collider = Hits[i].collider;
                    if (collider == null || collider.attachedRigidbody != null || collider is CharacterController || Hits[i].distance >= nearest) continue;
                    nearest = Hits[i].distance;
                    cached.Height = Hits[i].point.y;
                    cached.Hit = true;
                }
                Ground[index] = cached;
            }
            return cached.Hit ? Mathf.Max(0f, y - cached.Height) : 0f;
        }

        public static float FootDepth(Vector3 foot)
        {
            return SurfaceAt(foot, out float y, out _) && foot.y <= y + 0.015f ? Depth(foot) : 0f;
        }

        public static void ClearGroundCache() => System.Array.Clear(Ground, 0, Ground.Length);
        private static int Cell(float value) => Mathf.FloorToInt(value / GridSize);
        private static long Key(int x, int z) => ((long)x << 32) | (uint)z;
        private static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;
        private static bool Contains(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            if (Mathf.Abs(Cross(b - a, c - a)) < 0.000001f) return false;
            float ab = Cross(b - a, p - a), bc = Cross(c - b, p - b), ca = Cross(a - c, p - c);
            return (ab >= -0.0001f && bc >= -0.0001f && ca >= -0.0001f) ||
                   (ab <= 0.0001f && bc <= 0.0001f && ca <= 0.0001f);
        }
    }
}
