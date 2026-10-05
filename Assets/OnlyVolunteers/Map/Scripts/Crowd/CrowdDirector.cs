using System.Collections.Generic;
using System.Text;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map.Crowd
{
    // The living crowd of the final map, offline (draft docs/drafts/CROWD_AI_DRAFT.md). Reads crowd_vNN.json (a TextAsset
    // in Map/Data), keeps each district's walker count near its target for the time of day (Evening 0 = day counts,
    // 1 = evening counts, lerped; Density scales all), plus the police foot patrol. NPCs come from a pool of inactive
    // grey-box Buddies (GreyboxNpc + GreyboxNpcBody, built by the editor) and enter and leave the map only at the file's
    // hidden spawn/despawn points, and only while every enabled camera fails line of sight to the point for its grace
    // time (2 s) and every player is at least min_player_distance_m (25 m) away; otherwise the spawn or despawn waits.
    // The first fill at Start (Prewarm) is the one exception: it puts walkers straight onto their loops, but only at
    // spots that pass the same test.
    // A crowd NPC that is stunned or captured leaves crowd control for good (CrowdWalker.Release): it stays in the scene
    // as a plain GreyboxNpc, the district is one short and a replacement comes in at a hidden point.
    // Witnesses: GreyboxNpc.Incident -> CrowdWitness.Evaluate; a walker that saw it runs to the nearest witness hotspot
    // or police officer and RaiseAlert raises the district's alert (log + on-screen hint; police reaction is
    // CrowdPoliceHook, a placeholder).
    public sealed class CrowdDirector : MonoBehaviour
    {
        [Header("Data")]
        [Tooltip("crowd_vNN.json copied into Assets/OnlyVolunteers/Map/Data.")]
        public TextAsset Data;
        [Tooltip("Terrain + bridge deck height of the look map. Empty = found in the scene.")]
        public MapHeightSampler Sampler;
        [Tooltip("Inactive NPCs ready to spawn (children of this transform).")]
        public Transform PoolRoot;
        [Tooltip("Inactive NPCs cloned when the pool runs dry (never activated themselves).")]
        public GameObject[] Templates = new GameObject[0];

        [Header("Population")]
        [Tooltip("0 = day counts (walkers_day), 1 = evening counts (walkers_evening).")]
        [Range(0f, 1f)] public float Evening;
        [Tooltip("Scales every district target (1 = the file's counts).")]
        public float Density = 1f;
        public bool Police = true;
        [Tooltip("Fill the districts at Start straight onto their loops (at spots no camera sees).")]
        public bool Prewarm = true;
        [Tooltip("Seconds between spawns in one district.")]
        public float SpawnInterval = 1.5f;
        [Tooltip("Seconds a spawn point stays unused after a spawn there.")]
        public float SpawnPointCooldown = 4f;
        [Tooltip("Minutes a walker stays before heading for a despawn point (turnover).")]
        public Vector2 LifetimeMinutes = new(4f, 10f);

        [Header("Walking")]
        [Tooltip("Chance to stop at a POI when passing its access link.")]
        [Range(0f, 1f)] public float ActivityChance = 0.35f;
        [Tooltip("Animator speed of the Run clip per m/s of walking speed (the Buddy has no walk clip yet).")]
        public float WalkAnimPerMps = 0.24f;
        public float ReportRunSpeed = 3.6f;

        [Header("Witnesses")]
        public float ViewRangeDay = 32f;
        public float ViewRangeEvening = 20f;
        [Tooltip("Half angle of the view cone (degrees).")]
        public float ViewHalfAngle = 70f;
        [Tooltip("Seconds between seeing it and starting to run.")]
        public Vector2 ReactionDelay = new(0.3f, 0.9f);
        [Tooltip("Police see this much farther than walkers.")]
        public float PoliceRangeFactor = 1.3f;
        [Tooltip("Seconds per alert level to fade.")]
        public float AlertDecaySeconds = 90f;
        public int MaxAlert = 5;

        [Header("Debug")]
        public KeyCode OverlayKey = KeyCode.F11;
        public KeyCode TimeOfDayKey = KeyCode.F12;
        public bool ShowOverlay;
        public bool LogSpawns;

        // Layers that never hide anything from a camera or a witness: NPC bodies, the players, the van, water, Ignore Raycast.
        public const int OcclusionMask = ~((1 << 2) | (1 << 4) | (1 << OvLayers.Player) | (1 << OvLayers.RemotePlayer) |
                                           (1 << OvLayers.Vehicle) | (1 << OvLayers.VehicleInterior) | (1 << OvLayers.NpcBody) | (1 << OvLayers.NpcSeated));

        public static CrowdDirector Instance { get; private set; }
        public static event System.Action<CrowdAlert> AlertRaised;

        public CrowdData Map { get; private set; }
        public readonly List<CrowdWalker> Walkers = new();
        public float[] AlertLevel { get; private set; } = new float[0];
        public float ViewRange => Mathf.Lerp(ViewRangeDay, ViewRangeEvening, Evening);
        public VanController Van => _van;

        private readonly List<GameObject> _pool = new();
        private float[] _nextSpawn = new float[0];
        private float _nextPoliceSpawn;
        private float _nextVisibility, _nextBalance;
        private Camera[] _cameras = new Camera[8];
        private int _cameraCount;
        private GreyboxPawn _pawn;
        private VanController _van;
        private readonly RaycastHit[] _hits = new RaycastHit[16];
        private readonly List<(string text, float until)> _hints = new();
        private GUIStyle _hintStyle;
        private int _spawned;
        private TextAsset _gizmoData;
        private CrowdData _gizmoMap;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Instance = null;
            AlertRaised = null;
        }

        private void Awake()
        {
            Instance = this;
            if (Data == null)
            {
                Debug.LogError("[Crowd] no crowd data (TextAsset) on the CrowdDirector; crowd disabled.", this);
                enabled = false;
                return;
            }
            var sw = System.Diagnostics.Stopwatch.StartNew();
            Map = CrowdData.Parse(Data.text);
            if (Sampler == null) Sampler = FindAnyObjectByType<MapHeightSampler>();
            foreach (CrowdSpawn s in Map.Spawns) s.World = Ground(s.Position);
            AlertLevel = new float[Map.Districts.Count];
            _nextSpawn = new float[Map.Districts.Count];
            if (PoolRoot != null)
                foreach (Transform child in PoolRoot)
                    if (!child.gameObject.activeSelf && child.GetComponent<GreyboxNpc>() != null) _pool.Add(child.gameObject);
            Debug.Log($"[Crowd] {Map.Revision}: {Map.Districts.Count} districts, {Map.Routes.Count} loops, {Map.Pois.Count} POIs, " +
                      $"{Map.Spawns.Count} spawn points, {Map.Hotspots.Count} witness hotspots, graph {Map.Graph.Count} nodes, " +
                      $"pool {_pool.Count}; parsed in {sw.ElapsedMilliseconds} ms", this);
        }

        private void OnEnable() => GreyboxNpc.Incident += OnIncident;

        private void OnDisable() => GreyboxNpc.Incident -= OnIncident;

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        private void Start()
        {
            _pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            _van = FindAnyObjectByType<VanController>();
            RefreshCameras();
            if (Prewarm) PrewarmAll();
        }

        private void Update()
        {
            if (Input.GetKeyDown(OverlayKey)) ShowOverlay = !ShowOverlay;
            if (Input.GetKeyDown(TimeOfDayKey))
            {
                Evening = Evening < 0.5f ? 1f : 0f;
                Hint(Evening > 0.5f ? "Толпа: вечер" : "Толпа: день");
            }
            float now = Time.time;
            if (now >= _nextVisibility)
            {
                _nextVisibility = now + 0.25f;
                RefreshCameras();
                foreach (CrowdSpawn s in Map.Spawns)
                {
                    bool hidden = !Visible(s.World, s.MinPlayerDistance);
                    if (!hidden) s.HiddenSince = float.MaxValue;
                    else if (s.HiddenSince == float.MaxValue) s.HiddenSince = now;
                }
            }
            if (now >= _nextBalance)
            {
                _nextBalance = now + 0.5f;
                Balance(now);
            }
            for (int i = 0; i < AlertLevel.Length; i++)
                AlertLevel[i] = Mathf.Max(0f, AlertLevel[i] - Time.deltaTime / Mathf.Max(1f, AlertDecaySeconds));
        }

        // ---------- Population ----------

        public int Target(int district) => Mathf.RoundToInt(Map.Districts[district].Target(Evening) * Mathf.Max(0f, Density));

        /// <summary>Walkers that count for the district: on their way in, walking, at a POI; not leaving or reporting.</summary>
        public int Present(int district)
        {
            int n = 0;
            foreach (CrowdWalker w in Walkers)
                if (w.Role == CrowdRole.Walker && w.District == district && w.Counts) n++;
            return n;
        }

        private int PolicePresent()
        {
            int n = 0;
            foreach (CrowdWalker w in Walkers)
                if (w.Role == CrowdRole.Police) n++;
            return n;
        }

        private void Balance(float now)
        {
            for (int d = 0; d < Map.Districts.Count; d++)
            {
                int present = Present(d), target = Target(d);
                if (present < target && now >= _nextSpawn[d] && TryFreeSpawn(Map.Districts[d].Spawns, now, out int spawn))
                {
                    Spawn(CrowdRole.Walker, d, spawn);
                    _nextSpawn[d] = now + SpawnInterval;
                }
                else if (present > target)
                {
                    // One at a time: someone walking its loop (not at a POI, not reporting) heads home.
                    foreach (CrowdWalker w in Walkers)
                        if (w.Role == CrowdRole.Walker && w.District == d && w.CanLeave)
                        {
                            w.Leave();
                            break;
                        }
                }
            }
            if (Police && Map.Patrol != null && PolicePresent() < Map.Patrol.Officers && now >= _nextPoliceSpawn)
            {
                var spawns = new List<int>();
                foreach (int d in Map.Patrol.Districts) spawns.AddRange(Map.Districts[d].Spawns);
                if (TryFreeSpawn(spawns, now, out int spawn))
                {
                    Spawn(CrowdRole.Police, Map.Spawns[spawn].District, spawn);
                    _nextPoliceSpawn = now + SpawnInterval * 4f;
                }
            }
        }

        private bool TryFreeSpawn(List<int> candidates, float now, out int spawn)
        {
            spawn = -1;
            int offset = Random.Range(0, Mathf.Max(1, candidates.Count));
            for (int k = 0; k < candidates.Count; k++)
            {
                int i = candidates[(k + offset) % candidates.Count];
                if (SpawnHidden(i, now) && now - Map.Spawns[i].LastUsed >= SpawnPointCooldown)
                {
                    spawn = i;
                    return true;
                }
            }
            return false;
        }

        /// <summary>No camera has seen the spawn point for its grace time and nobody is within its minimum distance.</summary>
        public bool SpawnHidden(int spawn, float now)
        {
            CrowdSpawn s = Map.Spawns[spawn];
            return s.HiddenSince != float.MaxValue && now - s.HiddenSince >= s.Grace;
        }

        private CrowdWalker Spawn(CrowdRole role, int district, int spawn)
        {
            CrowdSpawn s = Map.Spawns[spawn];
            s.LastUsed = Time.time;
            CrowdWalker w = Take(s.World, Random.Range(0f, 360f), role);
            if (w == null) return null;
            w.BeginAtSpawn(this, role, district, spawn);
            if (LogSpawns) Debug.Log($"[Crowd] spawn {w.name} ({role}) at {s.Id} for {Map.Districts[district].Id}", w);
            return w;
        }

        private void PrewarmAll()
        {
            int placed = 0;
            for (int d = 0; d < Map.Districts.Count; d++)
            {
                CrowdDistrict district = Map.Districts[d];
                if (district.Routes.Count == 0) continue;
                for (int k = Target(d); k > 0; k--)
                {
                    int route = district.Routes[Random.Range(0, district.Routes.Count)];
                    if (HiddenRouteSpot(Map.Routes[route].Points, out int index, out Vector3 at) && Take(at, Random.Range(0f, 360f), CrowdRole.Walker) is CrowdWalker w)
                    {
                        w.BeginOnRoute(this, CrowdRole.Walker, d, route, index);
                        placed++;
                    }
                }
            }
            if (Police && Map.Patrol != null && Map.Patrol.Points.Length > 1)
                for (int k = 0; k < Map.Patrol.Officers; k++)
                    if (HiddenRouteSpot(Map.Patrol.Points, out int index, out Vector3 at) && Take(at, 0f, CrowdRole.Police) is CrowdWalker w)
                    {
                        w.BeginOnRoute(this, CrowdRole.Police, Map.Patrol.Districts.Count > 0 ? Map.Patrol.Districts[0] : 0, -1, index);
                        placed++;
                    }
            Debug.Log($"[Crowd] prewarm: {placed} NPCs placed on their loops ({(Evening > 0.5f ? "evening" : "day")}, density {Density:0.##})", this);
        }

        private bool HiddenRouteSpot(Vector2[] points, out int index, out Vector3 at)
        {
            for (int attempt = 0; attempt < 24; attempt++)
            {
                index = Random.Range(0, points.Length);
                at = Ground(points[index]);
                if (!Visible(at, 25f)) return true;
            }
            index = 0;
            at = Vector3.zero;
            return false;
        }

        // A pooled NPC (or a fresh clone of a template) placed at 'feet' and switched on, with its walker component.
        private CrowdWalker Take(Vector3 feet, float yaw, CrowdRole role)
        {
            GameObject go = null;
            while (_pool.Count > 0 && go == null)
            {
                go = _pool[_pool.Count - 1];
                _pool.RemoveAt(_pool.Count - 1);
            }
            if (go == null)
            {
                if (Templates == null || Templates.Length == 0 || Templates[_spawned % Templates.Length] == null)
                {
                    Debug.LogWarning("[Crowd] pool empty and no template to clone; spawn skipped.", this);
                    return null;
                }
                go = Instantiate(Templates[_spawned % Templates.Length], PoolRoot != null ? PoolRoot : transform);
            }
            _spawned++;
            go.name = (role == CrowdRole.Police ? "Police_" : "Crowd_") + _spawned.ToString("000");
            go.transform.SetPositionAndRotation(feet, Quaternion.Euler(0f, yaw, 0f));
            if (!go.TryGetComponent(out CrowdWalker walker)) walker = go.AddComponent<CrowdWalker>();
            go.SetActive(true);
            if (go.TryGetComponent(out SeaReturnTracker tracker)) tracker.Rebase();
            Walkers.Add(walker);
            return walker;
        }

        /// <summary>Back into the pool (the walker reached a hidden despawn point).</summary>
        public void Despawn(CrowdWalker walker)
        {
            if (LogSpawns) Debug.Log($"[Crowd] despawn {walker.name}", walker);
            Walkers.Remove(walker);
            walker.gameObject.SetActive(false);
            _pool.Add(walker.gameObject);
        }

        /// <summary>Out of crowd control for good (stunned or captured): the NPC stays, the district is one short.</summary>
        public void Forget(CrowdWalker walker) => Walkers.Remove(walker);

        // ---------- Visibility ----------

        private void RefreshCameras()
        {
            if (_cameras.Length < Camera.allCamerasCount) _cameras = new Camera[Camera.allCamerasCount + 4];
            _cameraCount = Camera.GetAllCameras(_cameras);
            if (_pawn == null) _pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
        }

        /// <summary>Some enabled camera has a clear line to the body standing at 'feet' (feet, waist or head inside its
        /// view), or a player (the pawn, a camera, the van) is closer than minDistance (flat).</summary>
        public bool Visible(Vector3 feet, float minDistance)
        {
            float minSq = minDistance * minDistance;
            if (_pawn != null && _pawn.Controlled && Flat(_pawn.Position - feet).sqrMagnitude < minSq) return true;
            if (_van != null && Flat(_van.transform.position - feet).sqrMagnitude < minSq) return true;
            for (int c = 0; c < _cameraCount; c++)
            {
                Camera cam = _cameras[c];
                if (cam == null || !cam.isActiveAndEnabled || cam.targetTexture != null) continue;
                Vector3 eye = cam.transform.position;
                if (Flat(eye - feet).sqrMagnitude < minSq) return true;
                for (int k = 0; k < 3; k++)
                {
                    Vector3 p = feet + Vector3.up * (0.2f + 0.7f * k);
                    Vector3 v = cam.WorldToViewportPoint(p);
                    if (v.z <= cam.nearClipPlane || v.z > cam.farClipPlane || v.x < -0.05f || v.x > 1.05f || v.y < -0.05f || v.y > 1.05f) continue;
                    if (!Physics.Linecast(eye, p, OcclusionMask, QueryTriggerInteraction.Ignore)) return true;
                }
            }
            return false;
        }

        // ---------- Ground ----------

        /// <summary>World feet position of plan point p: terrain or bridge deck (MapHeightSampler), raised to a flat
        /// collider surface just above it (sidewalk, kerb, deck), as the play scene builder places things.</summary>
        public Vector3 Ground(Vector2 p)
        {
            float h = Sampler != null ? Sampler.Height(p.x, p.y) : transform.position.y;
            int n = Physics.RaycastNonAlloc(new Vector3(p.x, h + 3f, p.y), Vector3.down, _hits, 6f, OcclusionMask, QueryTriggerInteraction.Ignore);
            float best = h;
            for (int i = 0; i < n; i++)
            {
                float y = _hits[i].point.y;
                if (y <= h + 0.3f && y > best && _hits[i].normal.y > 0.9f) best = y;
            }
            return new Vector3(p.x, best, p.y);
        }

        /// <summary>District of the loop vertex nearest to a world point (where an incident happened).</summary>
        public int DistrictAt(Vector3 world)
        {
            var p = new Vector2(world.x, world.z);
            int best = -1;
            float bestSq = float.MaxValue;
            foreach (CrowdRoute r in Map.Routes)
                foreach (Vector2 v in r.Points)
                {
                    float d = (v - p).sqrMagnitude;
                    if (d < bestSq)
                    {
                        bestSq = d;
                        best = r.District;
                    }
                }
            return best;
        }

        public float SamplerHeight(float x, float z) => Sampler != null ? Sampler.Height(x, z) : float.NegativeInfinity;

        // ---------- Witnesses and alerts ----------

        private void OnIncident(GreyboxNpc victim, NpcIncident kind) => CrowdWitness.Evaluate(this, victim, kind);

        /// <summary>A witness reached a hotspot or an officer (or an officer saw it): the district's alert goes up one level.</summary>
        public void RaiseAlert(int district, CrowdWalker reporter, NpcIncident kind, Vector3 where, string via)
        {
            if (district < 0 || district >= AlertLevel.Length) return;
            AlertLevel[district] = Mathf.Min(MaxAlert, Mathf.Floor(AlertLevel[district]) + 1f);
            var alert = new CrowdAlert
            {
                District = district, DistrictId = Map.Districts[district].Id, DistrictName = Map.Districts[district].Name,
                Level = Mathf.RoundToInt(AlertLevel[district]), Kind = kind, Position = where, Reporter = reporter, Via = via, Time = Time.time,
            };
            string what = kind == NpcIncident.Captured ? "похищение" : "нападение";
            Debug.Log($"[Crowd] ALERT {alert.DistrictId} level {alert.Level}: {what} at ({where.x:0}, {where.z:0}) reported by " +
                      $"{(reporter != null ? reporter.name : "?")} via {via}", reporter);
            Hint($"Тревога: {alert.DistrictName} — свидетель сообщил ({what}), уровень {alert.Level}");
            AlertRaised?.Invoke(alert);
        }

        public void Hint(string text) => _hints.Add((text, Time.time + 6f));

        private void OnGUI()
        {
            // OnGUI runs every frame (Layout + Repaint): nothing to draw = no work and no garbage.
            if (_hints.Count == 0 && !ShowOverlay) return;
            float now = Time.time;
            for (int i = _hints.Count - 1; i >= 0; i--)
                if (_hints[i].until < now) _hints.RemoveAt(i);
            _hintStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter, normal = { textColor = new Color(1f, 0.55f, 0.35f) } };
            for (int i = 0; i < _hints.Count; i++)
                GUI.Label(new Rect(0f, 70f + 24f * i, Screen.width, 24f), _hints[i].text, _hintStyle);
            if (!ShowOverlay || Map == null) return;
            var sb = new StringBuilder();
            sb.AppendLine($"Толпа ({OverlayKey}): {(Evening > 0.5f ? "вечер" : "день")} [{TimeOfDayKey}], плотность {Density:0.##}, пул {_pool.Count}");
            int total = 0;
            for (int d = 0; d < Map.Districts.Count; d++)
            {
                int present = Present(d);
                total += present;
                sb.AppendLine($"{Map.Districts[d].Name}: {present}/{Target(d)}  тревога {AlertLevel[d]:0.0}");
            }
            int hidden = 0;
            for (int i = 0; i < Map.Spawns.Count; i++)
                if (SpawnHidden(i, now)) hidden++;
            sb.AppendLine($"Всего {total}, полиция {PolicePresent()}, скрытых точек спавна {hidden}/{Map.Spawns.Count}");
            GUI.Box(new Rect(10f, Screen.height - 280f, 380f, 270f), GUIContent.none);
            GUI.Label(new Rect(18f, Screen.height - 276f, 370f, 266f), sb.ToString());
        }

        private void OnDrawGizmosSelected()
        {
            CrowdData map = Map;
            if (map == null)
            {
                if (Data == null) return;
                if (_gizmoData != Data)
                {
                    _gizmoMap = CrowdData.Parse(Data.text);
                    _gizmoData = Data;
                }
                map = _gizmoMap;
            }
            float y = 1f;
            Gizmos.color = new Color(0.3f, 0.8f, 1f);
            foreach (CrowdRoute r in map.Routes)
                for (int i = 0; i < r.Points.Length; i++)
                    Gizmos.DrawLine(P(r.Points[i], y), P(r.Points[(i + 1) % r.Points.Length], y));
            if (map.Patrol != null)
            {
                Gizmos.color = Color.blue;
                for (int i = 0; i < map.Patrol.Points.Length; i++)
                    Gizmos.DrawLine(P(map.Patrol.Points[i], y + 0.3f), P(map.Patrol.Points[(i + 1) % map.Patrol.Points.Length], y + 0.3f));
            }
            Gizmos.color = Color.magenta;
            foreach (CrowdSpawn s in map.Spawns) Gizmos.DrawWireSphere(P(s.Position, y), 1.5f);
            Gizmos.color = Color.red;
            foreach (CrowdHotspot h in map.Hotspots) Gizmos.DrawWireSphere(P(h.Position, y), h.Radius);
            Gizmos.color = Color.yellow;
            foreach (CrowdPoi p in map.Pois) Gizmos.DrawWireCube(P(p.Position, y), Vector3.one);
        }

        // Gizmo point: on the sampled ground when there is a sampler.
        private Vector3 P(Vector2 p, float lift) => new(p.x, (Sampler != null ? Sampler.Height(p.x, p.y) : transform.position.y) + lift, p.y);

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
