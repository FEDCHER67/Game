using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Crowd
{
    // One crowd NPC under CrowdDirector control (on the same object as GreyboxNpc). No NavMesh: it walks the crowd file's
    // polylines on the real ground with its CharacterController (gravity, steps), steering at the next vertex with a
    // small lane offset to the right, separating from every NPC around it and sidestepping right for oncoming ones.
    // Before a zebra (and a junction crossing) it stops at the kerb: a short look at a zebra, and it waits while the van
    // comes. Off its loop (joining it, running to report, heading for a despawn point) it follows A* paths over the crowd
    // graph (CrowdGraph).
    // Loop -> POI: passing a POI's access link it may (ActivityChance, a free slot) walk in, take a slot and do the
    // activity for the POI's dwell time (sit on the bench, queue, wait at the bus stop, smoke, lie on the beach, stand at
    // a door or on the church steps, hang around the playground), then walk back. No sit/lie clips yet: sitting sinks
    // the standing mesh, lying tips it over (placeholders).
    // GreyboxNpc keeps everything else: fleeing from the van or the pawn (the walker yields and rejoins after), going down,
    // the van. Stunned or captured -> Release: the pose is undone, the slot freed, the walker removed for good.
    [DisallowMultipleComponent]
    [RequireComponent(typeof(GreyboxNpc))]
    public sealed class CrowdWalker : MonoBehaviour
    {
        public enum Mode : byte { Route, Path, Activity, Pause, DespawnWait, Released }
        private enum Goal : byte { None, JoinRoute, ToPoi, FromPoi, Report, Leave }

        private const float ReachDistance = 0.8f, SlotReach = 0.35f, Gravity = 20f, TurnSpeed = 360f;
        private const float SeparationRadius = 1.0f, LookAhead = 2.5f, KerbAhead = 1.4f, MaxKerbWait = 12f;
        private const float StuckInterval = 2f, StuckDistance = 0.4f;

        public CrowdRole Role { get; private set; }
        public int District { get; private set; }
        public Mode State => _mode;
        public GreyboxNpc Npc { get; private set; }

        /// <summary>Counts toward its district's target: not on the way out, not reporting, not released.</summary>
        public bool Counts => _mode != Mode.Released && _mode != Mode.DespawnWait && _goal != Goal.Leave && _goal != Goal.Report && !_pendingReport;
        public bool CanLeave => _mode == Mode.Route && !_pendingReport;
        public bool CanWitness => _mode != Mode.Released && _goal != Goal.Report && !_pendingReport && Npc != null && Npc.State == NpcState.Free;
        public bool LyingDown => _mode == Mode.Activity && _activity == CrowdActivity.BeachLie;
        public Vector3 Eye => transform.position + Vector3.up * (LyingDown ? 0.4f : 1.55f);

        private CrowdDirector _director;
        private CharacterController _controller;
        private Transform _visual;
        private Vector3 _visualPosition;
        private Quaternion _visualRotation;
        private GameObject _label;
        private Mode _mode = Mode.Released;
        private Goal _goal;
        private CrowdProfile _profile;

        // Loop: a district route, or the police patrol (_route = -1).
        private int _route = -1, _index, _dir = 1;
        private float _speed, _lane, _vy;

        private readonly List<Vector2> _path = new();
        private int _pathIndex;

        private int _poi = -1, _slot = -1, _lastPoi = -1;
        private CrowdActivity _activity;
        private Vector2 _facing;
        private float _dwellUntil, _lastPoiTime;

        private bool _pendingReport;
        private float _reactAt;
        private NpcIncident _sawKind;
        private Vector3 _sawWhere;
        private CrowdWalker _officer;
        private string _reportVia;

        private int _despawn = -1;
        private float _leaveAt, _pauseUntil, _travelled, _nextPauseAt;
        private int _clearedCrossing = -1;
        private float _kerbSince = -1f, _kerbMin;
        private Vector3 _stuckFrom;
        private float _stuckCheck, _nextGroundCheck;
        private int _stuck;
        private bool _wasFleeing;

        private CrowdData Map => _director.Map;
        private Vector2[] Loop => _route >= 0 ? Map.Routes[_route].Points : Map.Patrol.Points;
        private Vector2 Pos2 => new(transform.position.x, transform.position.z);

        private void Awake()
        {
            Npc = GetComponent<GreyboxNpc>();
            _controller = GetComponent<CharacterController>();
            Animator animator = GetComponentInChildren<Animator>(true);
            if (animator != null && animator.transform != transform)
            {
                _visual = animator.transform;
                _visualPosition = _visual.localPosition;
                _visualRotation = _visual.localRotation;
            }
        }

        private void OnEnable() => GreyboxNpc.Incident += OnIncident;

        private void OnDisable() => GreyboxNpc.Incident -= OnIncident;

        private void OnIncident(GreyboxNpc npc, NpcIncident kind)
        {
            if (npc == Npc) Release();
        }

        // ---------- Starting ----------

        public void BeginAtSpawn(CrowdDirector director, CrowdRole role, int district, int spawn)
        {
            Init(director, role, district, role == CrowdRole.Police ? -1 : PickRoute(director, district));
            Vector2 at = Map.Spawns[spawn].Position;
            _index = NearestIndex(Loop, at);
            GoTo(Loop[_index], Goal.JoinRoute);
        }

        public void BeginOnRoute(CrowdDirector director, CrowdRole role, int district, int route, int index)
        {
            Init(director, role, district, role == CrowdRole.Police ? -1 : route);
            _index = index;
            _mode = Mode.Route;
        }

        private void Init(CrowdDirector director, CrowdRole role, int district, int route)
        {
            _director = director;
            Role = role;
            District = district;
            _route = route;
            CrowdPatrol patrol = director.Map.Patrol;
            Vector2 speed = route >= 0 ? director.Map.Routes[route].Speed : patrol != null ? patrol.Speed : new Vector2(1.1f, 1.4f);
            _speed = Random.Range(speed.x, speed.y);
            _profile = route >= 0 && director.Map.Routes[route].Profile == CrowdProfile.Beach ? CrowdProfile.All : CrowdProfile.Town;
            _lane = Random.Range(0.1f, 0.45f);
            _dir = Random.value < 0.5f ? 1 : -1;
            _goal = Goal.None;
            _path.Clear();
            _pathIndex = 0;
            _poi = _slot = _lastPoi = -1;
            _pendingReport = false;
            _officer = null;
            _despawn = -1;
            _clearedCrossing = -1;
            _kerbSince = -1f;
            _stuck = 0;
            _vy = 0f;
            _wasFleeing = false;
            _travelled = 0f;
            _nextPauseAt = Random.Range(60f, 140f);
            _leaveAt = Time.time + Random.Range(director.LifetimeMinutes.x, director.LifetimeMinutes.y) * 60f;
            _stuckFrom = transform.position;
            _stuckCheck = Time.time + StuckInterval;
            ResetPose();
            Npc.ExternalLocomotion = true;
            SetPoliceLabel(role == CrowdRole.Police);
        }

        private static int PickRoute(CrowdDirector director, int district)
        {
            List<int> routes = director.Map.Districts[district].Routes;
            if (routes.Count == 0) return 0;
            // Longer loops get more walkers.
            float total = 0f;
            foreach (int r in routes) total += director.Map.Routes[r].Length;
            float pick = Random.value * total;
            foreach (int r in routes)
            {
                pick -= director.Map.Routes[r].Length;
                if (pick <= 0f) return r;
            }
            return routes[routes.Count - 1];
        }

        // ---------- Update ----------

        private void Update()
        {
            if (_mode == Mode.Released || _director == null || _director.Map == null) return;
            if (Npc == null || Npc.State != NpcState.Free)
            {
                Release();
                return;
            }
            float now = Time.time;
            if (Npc.Fleeing)
            {
                // GreyboxNpc runs it away from the van or the pawn; the walker gives up its spot and waits.
                if (!_wasFleeing)
                {
                    _wasFleeing = true;
                    EndActivityNow();
                }
                return;
            }
            if (_wasFleeing)
            {
                _wasFleeing = false;
                Recover();
            }
            if (_pendingReport && now >= _reactAt) StartReport();

            Vector2 velocity = Vector2.zero;
            switch (_mode)
            {
                case Mode.Route:
                    if (Role == CrowdRole.Walker && now >= _leaveAt)
                    {
                        Leave();
                        break;
                    }
                    velocity = FollowLoop();
                    break;
                case Mode.Path:
                    velocity = FollowPath();
                    break;
                case Mode.Activity:
                    TickActivity(now);
                    break;
                case Mode.Pause:
                    if (now < _pauseUntil) break;
                    // Paused off the loop (an officer who saw something on his way in): path back first.
                    if ((Loop[_index] - Pos2).sqrMagnitude > 25f) Recover();
                    else _mode = Mode.Route;
                    break;
                case Mode.DespawnWait:
                    if (_despawn < 0 || _director.SpawnHidden(_despawn, now))
                    {
                        _director.Despawn(this);
                        return;
                    }
                    break;
            }
            if (_mode == Mode.Released) return;
            Move(velocity, now);
        }

        private void Move(Vector2 velocity, float now)
        {
            float dt = Time.deltaTime;
            var v = new Vector3(velocity.x, 0f, velocity.y);
            _vy = _controller.isGrounded ? -1f : _vy - Gravity * dt;
            if (_controller.enabled) _controller.Move((v + Vector3.up * _vy) * dt);
            float speed = v.magnitude;
            if (speed > 0.05f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(v), TurnSpeed * dt);
            if (_mode != Mode.Activity)
            {
                if (speed > 0.15f) Npc.Animate("Run", Mathf.Clamp(speed * _director.WalkAnimPerMps, 0.15f, 1.2f));
                else Npc.Animate("Idle", 1f);
            }
            if (now >= _nextGroundCheck)
            {
                _nextGroundCheck = now + 1f;
                // Fell through the ground (a seam, a deck edge): back onto it.
                float h = _director.SamplerHeight(transform.position.x, transform.position.z);
                if (transform.position.y < h - 2f) Teleport(Pos2);
            }
            CheckStuck(speed, now);
        }

        // ---------- Loop ----------

        private Vector2 FollowLoop()
        {
            Vector2[] loop = Loop;
            if (loop.Length < 2) return Vector2.zero;
            Vector2 pos = Pos2;
            Vector2 target = LaneTarget(loop, _index, _dir);
            for (int guard = 0; guard < 8 && (target - pos).sqrMagnitude < ReachDistance * ReachDistance; guard++)
            {
                if (!Advance()) return Vector2.zero; // turned off the loop (POI, pause)
                target = LaneTarget(loop, _index, _dir);
            }
            return Steer(target, _speed, true);
        }

        // Next vertex of the loop; false when that vertex sends it somewhere else (a POI, a police pause).
        private bool Advance()
        {
            Vector2[] loop = Loop;
            int next = Wrap(loop, _index + _dir);
            _travelled += Vector2.Distance(loop[_index], loop[next]);
            _index = next;
            if (Role == CrowdRole.Police && _travelled >= _nextPauseAt)
            {
                _travelled = 0f;
                _nextPauseAt = Random.Range(60f, 140f);
                Vector2 pause = Map.Patrol.Pause;
                _pauseUntil = Time.time + Random.Range(pause.x, pause.y);
                _mode = Mode.Pause;
                return false;
            }
            if (Role == CrowdRole.Walker && _route >= 0)
                foreach (int p in Map.Routes[_route].Pois)
                {
                    CrowdPoi poi = Map.Pois[p];
                    if (poi.RouteIndex != _index || (p == _lastPoi && Time.time - _lastPoiTime < 120f)) continue;
                    if (Random.value >= _director.ActivityChance) continue;
                    int slot = System.Array.IndexOf(poi.Slots, null);
                    if (slot < 0) continue;
                    GoToPoi(p, slot);
                    return false;
                }
            return true;
        }

        // Vertex i, moved _lane metres to the right of the direction of travel (keep right, no single file).
        private Vector2 LaneTarget(Vector2[] loop, int i, int dir)
        {
            Vector2 d = loop[i] - loop[Wrap(loop, i - dir)];
            if (d.sqrMagnitude < 1e-6f) return loop[i];
            d.Normalize();
            return loop[i] + new Vector2(d.y, -d.x) * _lane;
        }

        private static int Wrap(Vector2[] loop, int i) => ((i % loop.Length) + loop.Length) % loop.Length;

        private static int NearestIndex(Vector2[] loop, Vector2 p)
        {
            int best = 0;
            float bestSq = float.MaxValue;
            for (int i = 0; i < loop.Length; i++)
            {
                float d = (loop[i] - p).sqrMagnitude;
                if (d < bestSq)
                {
                    bestSq = d;
                    best = i;
                }
            }
            return best;
        }

        // ---------- Paths ----------

        // A* over the crowd graph from here to 'to' (exact end point appended); a straight line if there is no path.
        private void GoTo(Vector2 to, Goal goal)
        {
            CrowdGraph graph = Map.Graph;
            _path.Clear();
            _pathIndex = 0;
            int from = graph.Nearest(Pos2, _profile), end = graph.Nearest(to, _profile);
            if (from >= 0 && end >= 0 && graph.FindPath(from, end, _profile, _path))
            {
                _path.Insert(0, graph.Nodes[from]);
                if ((_path[_path.Count - 1] - to).sqrMagnitude > 0.01f) _path.Add(to);
            }
            else
            {
                _path.Clear();
                _path.Add(to);
            }
            _goal = goal;
            _mode = Mode.Path;
        }

        private Vector2 FollowPath()
        {
            if (_goal == Goal.Report && _officer != null && _pathIndex >= _path.Count - 1 && _path.Count > 0)
            {
                // Chasing a walking officer: the end of the path follows him.
                if (_officer.Npc == null || !_officer.isActiveAndEnabled || _officer.State == Mode.Released) _officer = null;
                else _path[_path.Count - 1] = _officer.Pos2;
            }
            Vector2 pos = Pos2;
            while (_pathIndex < _path.Count)
            {
                bool last = _pathIndex == _path.Count - 1;
                float reach = !last ? ReachDistance : _goal == Goal.ToPoi ? SlotReach : _goal == Goal.Report && _officer != null ? 2.5f : 1f;
                if ((_path[_pathIndex] - pos).sqrMagnitude > reach * reach) break;
                _pathIndex++;
            }
            if (_pathIndex >= _path.Count)
            {
                ArrivePath();
                return Vector2.zero;
            }
            bool running = _goal == Goal.Report;
            float speed = running ? _director.ReportRunSpeed : _speed;
            // Slow down into a slot.
            if (_goal == Goal.ToPoi && _pathIndex == _path.Count - 1)
                speed = Mathf.Min(speed, Mathf.Max(0.4f, Vector2.Distance(pos, _path[_pathIndex]) * 1.5f));
            return Steer(_path[_pathIndex], speed, !running);
        }

        private void ArrivePath()
        {
            switch (_goal)
            {
                case Goal.JoinRoute:
                case Goal.FromPoi:
                case Goal.None:
                    _goal = Goal.None;
                    _mode = Mode.Route;
                    break;
                case Goal.ToPoi:
                    StartActivity();
                    break;
                case Goal.Report:
                    _director.RaiseAlert(_director.DistrictAt(_sawWhere), this, _sawKind, _sawWhere, _officer != null ? _officer.name : _reportVia);
                    _officer = null;
                    Leave();
                    break;
                case Goal.Leave:
                    _mode = Mode.DespawnWait;
                    break;
            }
        }

        // After a flee: back to whatever it was doing, from where it ended up.
        private void Recover()
        {
            switch (_goal)
            {
                case Goal.Report:
                    StartReport();
                    break;
                case Goal.Leave:
                    Leave();
                    break;
                default:
                    _index = NearestIndex(Loop, Pos2);
                    GoTo(Loop[_index], Goal.JoinRoute);
                    break;
            }
        }

        /// <summary>Head for the nearest despawn point of its district and leave the map there once no camera sees it.</summary>
        public void Leave()
        {
            if (_mode == Mode.Released) return;
            EndActivityNow();
            _pendingReport = false;
            List<int> candidates = District >= 0 && District < Map.Districts.Count ? Map.Districts[District].Spawns : null;
            _despawn = -1;
            float best = float.MaxValue;
            Vector2 pos = Pos2;
            for (int k = 0; k < (candidates != null && candidates.Count > 0 ? candidates.Count : Map.Spawns.Count); k++)
            {
                int i = candidates != null && candidates.Count > 0 ? candidates[k] : k;
                float d = (Map.Spawns[i].Position - pos).sqrMagnitude;
                if (d < best)
                {
                    best = d;
                    _despawn = i;
                }
            }
            if (_despawn < 0)
            {
                _mode = Mode.DespawnWait;
                return;
            }
            GoTo(Map.Spawns[_despawn].Position, Goal.Leave);
        }

        // ---------- Steering ----------

        // Velocity (plan x, y) toward 'target': separation from nearby NPCs, a step right for oncoming ones, and a stop at
        // the kerb before a crossing when 'obeyKerb'.
        private Vector2 Steer(Vector2 target, float speed, bool obeyKerb)
        {
            Vector2 pos = Pos2;
            Vector2 to = target - pos;
            float distance = to.magnitude;
            Vector2 dir = distance > 1e-3f ? to / distance : new Vector2(transform.forward.x, transform.forward.z).normalized;
            if (obeyKerb && HoldAtKerb(pos, dir)) return Vector2.zero;
            Vector2 right = new(dir.y, -dir.x);
            Vector2 push = Vector2.zero;
            float y = transform.position.y;
            foreach (GreyboxNpc other in GreyboxNpc.All)
            {
                if (other == null || other == Npc) continue;
                Vector3 p = other.State == NpcState.Free ? other.transform.position : other.Center;
                if (Mathf.Abs(p.y - y) > 2f) continue;
                Vector2 rel = new(p.x - pos.x, p.z - pos.y);
                float d2 = rel.sqrMagnitude;
                if (d2 > LookAhead * LookAhead) continue;
                float d = Mathf.Sqrt(d2);
                if (d < SeparationRadius)
                    push -= (d > 1e-3f ? rel / d : right) * ((SeparationRadius - d) / SeparationRadius * 1.5f);
                float along = Vector2.Dot(rel, dir), across = Vector2.Dot(rel, right);
                if (along > 0f && Mathf.Abs(across) < 0.7f)
                    push += right * (0.6f * (1f - along / LookAhead)); // someone ahead: pass on the right
            }
            Vector2 velocity = dir * speed + push * speed;
            return Vector2.ClampMagnitude(velocity, speed * 1.2f);
        }

        // At the kerb of a zebra or junction crossing: a short look at a zebra, then wait while the van comes (12 s at most).
        private bool HoldAtKerb(Vector2 pos, Vector2 dir)
        {
            int here = Map.CrossingAt(pos);
            if (here >= 0)
            {
                _clearedCrossing = here; // already on it: keep going
                _kerbSince = -1f;
                return false;
            }
            int ahead = Map.CrossingAt(pos + dir * KerbAhead);
            if (ahead < 0)
            {
                _clearedCrossing = -1;
                _kerbSince = -1f;
                return false;
            }
            if (ahead == _clearedCrossing) return false;
            float now = Time.time;
            if (_kerbSince < 0f)
            {
                _kerbSince = now;
                _kerbMin = Map.Crossings[ahead].Zebra ? Random.Range(0.5f, 1.5f) : 0f;
            }
            float waited = now - _kerbSince;
            if (waited < MaxKerbWait && (waited < _kerbMin || VanComing(pos + dir * (KerbAhead + 2f))))
            {
                // Look along the road while waiting.
                return true;
            }
            _clearedCrossing = ahead;
            _kerbSince = -1f;
            return false;
        }

        private bool VanComing(Vector2 at)
        {
            var van = _director.Van;
            if (van == null) return false;
            Vector3 vp = van.transform.position;
            Vector2 rel = new(at.x - vp.x, at.y - vp.z);
            float kmh = Mathf.Abs(van.SpeedKmh);
            float d = rel.magnitude;
            if (d < 6f && kmh > 2f) return true;
            if (kmh < 5f || d > 35f) return false;
            Vector3 f = van.transform.forward * Mathf.Sign(van.SpeedKmh);
            return Vector2.Dot(new Vector2(f.x, f.z), rel) > 0f;
        }

        private void CheckStuck(float speed, float now)
        {
            if (now < _stuckCheck) return;
            _stuckCheck = now + StuckInterval;
            bool wants = (_mode == Mode.Route || _mode == Mode.Path) && _kerbSince < 0f;
            Vector3 p = transform.position;
            float moved = new Vector2(p.x - _stuckFrom.x, p.z - _stuckFrom.z).magnitude;
            _stuckFrom = p;
            if (!wants || moved >= StuckDistance)
            {
                _stuck = 0;
                return;
            }
            _stuck++;
            if (_mode == Mode.Path && _goal == Goal.ToPoi && _pathIndex >= _path.Count - 1)
            {
                StartActivity(); // the slot is inside a bench or a wall: do it here
                return;
            }
            if (_stuck == 1)
            {
                if (_mode == Mode.Path && _pathIndex < _path.Count - 1) _pathIndex++;
                else if (_mode == Mode.Route) Advance();
                return;
            }
            _lane = -_lane;
            if (_stuck >= 3)
            {
                Vector2 next = _mode == Mode.Path && _pathIndex < _path.Count ? _path[_pathIndex] : Loop[Wrap(Loop, _index + _dir)];
                if (!_director.Visible(transform.position, 0f) && !_director.Visible(_director.Ground(next), 0f))
                {
                    Teleport(next);
                    _stuck = 0;
                }
            }
        }

        private void Teleport(Vector2 p)
        {
            bool was = _controller.enabled;
            _controller.enabled = false;
            transform.position = _director.Ground(p) + Vector3.up * 0.05f;
            _controller.enabled = was;
            _vy = 0f;
            _stuckFrom = transform.position;
        }

        // ---------- POI activities ----------

        private void GoToPoi(int poiIndex, int slot)
        {
            CrowdPoi poi = Map.Pois[poiIndex];
            poi.Slots[slot] = this;
            _poi = poiIndex;
            _slot = slot;
            _activity = poi.Activity;
            SlotPose(poi, slot, out Vector2 spot, out _facing);
            // Over the graph (along the loop to where the access link meets it, then the link), then to the slot.
            GoTo(poi.Position, Goal.ToPoi);
            _path.Add(spot);
        }

        // Where slot k of a POI stands and which way it faces. Out points from the POI toward the path.
        private static void SlotPose(CrowdPoi poi, int slot, out Vector2 spot, out Vector2 facing)
        {
            Vector2 o = poi.Out, side = new(o.y, -o.x);
            float centred = slot - (poi.Capacity - 1) * 0.5f;
            switch (poi.Activity)
            {
                case CrowdActivity.BenchSit:
                    spot = poi.Position + side * (centred * 0.65f);
                    facing = o;
                    break;
                case CrowdActivity.ShopQueue:
                case CrowdActivity.Kiosk:
                    spot = poi.Position + o * (0.9f * slot); // a line out from the counter
                    facing = -o;
                    break;
                case CrowdActivity.BeachLie:
                    spot = poi.Position + side * (centred * 1.4f);
                    facing = o;
                    break;
                case CrowdActivity.BusWait:
                case CrowdActivity.BarDoor:
                case CrowdActivity.CasinoDoor:
                case CrowdActivity.ChurchSteps:
                    spot = poi.Position + side * (centred * 0.9f);
                    facing = o;
                    break;
                default:
                {
                    // Smoking corner, playground: a small circle, facing each other.
                    float angle = slot * Mathf.PI * 2f / Mathf.Max(1, poi.Capacity);
                    Vector2 ring = poi.Capacity > 1 ? new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * 0.7f : Vector2.zero;
                    spot = poi.Position + ring;
                    facing = ring.sqrMagnitude > 1e-4f ? -ring.normalized : o;
                    break;
                }
            }
        }

        private void StartActivity()
        {
            if (_poi < 0)
            {
                _mode = Mode.Route;
                return;
            }
            CrowdPoi poi = Map.Pois[_poi];
            _mode = Mode.Activity;
            _goal = Goal.None;
            _dwellUntil = Time.time + Random.Range(poi.Dwell.x, poi.Dwell.y);
            ApplyPose(_activity);
            Npc.Animate("Idle", _activity == CrowdActivity.SmokeCorner ? 0.6f : 1f);
        }

        private void TickActivity(float now)
        {
            Vector2 face = _facing;
            // Waiting for the bus or at a door: a look around now and then.
            if (_activity == CrowdActivity.BusWait || _activity == CrowdActivity.Playground || _activity == CrowdActivity.BarDoor)
            {
                float look = (Mathf.PerlinNoise(now * 0.15f, GetHashCode() * 0.01f) - 0.5f) * 140f;
                face = Rotate(face, look);
            }
            if (face.sqrMagnitude > 1e-4f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(new Vector3(face.x, 0f, face.y)), 120f * Time.deltaTime);
            if (now < _dwellUntil) return;
            CrowdPoi poi = Map.Pois[_poi];
            _lastPoi = _poi;
            _lastPoiTime = now;
            EndActivityNow();
            // Back out along the access link onto the loop, where it left.
            _index = poi.RouteIndex;
            GoTo(Loop[_index], Goal.FromPoi);
        }

        // Leaves the POI slot and undoes the pose (if any). Mode and goal are the caller's.
        private void EndActivityNow()
        {
            ResetPose();
            if (_poi >= 0 && _director != null && _director.Map != null)
            {
                CrowdPoi poi = Map.Pois[_poi];
                if (_slot >= 0 && _slot < poi.Slots.Length && poi.Slots[_slot] == this) poi.Slots[_slot] = null;
            }
            if (_mode == Mode.Activity || _goal == Goal.ToPoi)
            {
                _mode = Mode.Route;
                _goal = Goal.None;
            }
            _poi = _slot = -1;
        }

        // No sit/lie clips yet: placeholders on the mesh, undone by ResetPose.
        private void ApplyPose(CrowdActivity activity)
        {
            if (_visual == null) return;
            ResetPose();
            switch (activity)
            {
                case CrowdActivity.BenchSit:
                    _visual.localPosition = _visualPosition + Vector3.down * 0.35f;
                    break;
                case CrowdActivity.BeachLie:
                    _visual.localPosition = _visualPosition + Vector3.up * 0.25f;
                    _visual.localRotation = _visualRotation * Quaternion.Euler(-90f, 0f, 0f);
                    break;
            }
        }

        private void ResetPose()
        {
            if (_visual == null) return;
            _visual.localPosition = _visualPosition;
            _visual.localRotation = _visualRotation;
        }

        // ---------- Witness ----------

        /// <summary>Saw a stun or a capture at 'where'. A police officer raises the alert on the spot; a walker reacts after
        /// a moment and runs to report.</summary>
        public void Witness(NpcIncident kind, Vector3 where)
        {
            if (!CanWitness) return;
            _sawKind = kind;
            _sawWhere = where;
            if (Role == CrowdRole.Police)
            {
                _director.RaiseAlert(_director.DistrictAt(where), this, kind, where, "полицейский видел сам");
                EndActivityNow();
                _mode = Mode.Pause;
                _pauseUntil = Time.time + 4f;
                Vector3 look = where - transform.position;
                look.y = 0f;
                if (look.sqrMagnitude > 1e-4f) transform.rotation = Quaternion.LookRotation(look);
                return;
            }
            _pendingReport = true;
            _reactAt = Time.time + Random.Range(_director.ReactionDelay.x, _director.ReactionDelay.y);
        }

        // Run to the nearest witness hotspot or police officer (straight-line nearest), along the crowd graph.
        private void StartReport()
        {
            _pendingReport = false;
            EndActivityNow();
            Vector2 pos = Pos2;
            float best = float.MaxValue;
            Vector2 target = pos;
            _officer = null;
            _reportVia = "телефон";
            foreach (CrowdHotspot h in Map.Hotspots)
            {
                float d = (h.Position - pos).sqrMagnitude;
                if (d < best)
                {
                    best = d;
                    target = h.Position;
                    _reportVia = h.Id;
                }
            }
            foreach (CrowdWalker w in _director.Walkers)
            {
                if (w == this || w.Role != CrowdRole.Police || w._mode == Mode.Released) continue;
                float d = (w.Pos2 - pos).sqrMagnitude;
                if (d < best)
                {
                    best = d;
                    target = w.Pos2;
                    _officer = w;
                }
            }
            if (best == float.MaxValue)
            {
                // Nowhere to run: calls it in from here.
                _director.RaiseAlert(_director.DistrictAt(_sawWhere), this, _sawKind, _sawWhere, _reportVia);
                Leave();
                return;
            }
            GoTo(target, Goal.Report);
        }

        // ---------- Leaving crowd control ----------

        /// <summary>Stunned or captured: undo the pose, free the slot, hand the NPC back to GreyboxNpc for good.</summary>
        public void Release()
        {
            if (_mode == Mode.Released) return;
            EndActivityNow();
            _mode = Mode.Released;
            _pendingReport = false;
            if (Npc != null)
            {
                Npc.ExternalLocomotion = false;
                Npc.Animate("Idle", 1f);
            }
            SetPoliceLabel(false);
            if (_director != null) _director.Forget(this);
            Destroy(this);
        }

        private void SetPoliceLabel(bool on)
        {
            if (on && _label == null)
            {
                _label = new GameObject("Label_Police");
                _label.transform.SetParent(transform, false);
                _label.transform.localPosition = new Vector3(0f, 1.95f, 0f);
                var tm = _label.AddComponent<TextMesh>();
                tm.text = "ПОЛИЦИЯ";
                tm.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                _label.GetComponent<MeshRenderer>().sharedMaterial = tm.font.material;
                tm.fontSize = 48;
                tm.characterSize = 0.035f;
                tm.anchor = TextAnchor.MiddleCenter;
                tm.color = new Color(0.4f, 0.6f, 1f);
                _label.AddComponent<GreyboxBillboard>();
            }
            if (_label != null) _label.SetActive(on);
            if (!on && _label != null && _mode == Mode.Released) Destroy(_label);
        }

        private static Vector2 Rotate(Vector2 v, float degrees)
        {
            float r = degrees * Mathf.Deg2Rad, c = Mathf.Cos(r), s = Mathf.Sin(r);
            return new Vector2(v.x * c + v.y * s, -v.x * s + v.y * c);
        }
    }
}
