using OnlyVolunteers.Audio;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // Brain of one police car with its crew of two (design 1.2 and 2.3-2.6). One small state machine, no suspicion levels:
    //   Parked / Patrol -> Alerted (dispatch: siren, radio delay, +3 s boarding when parked) -> Respond (to the van's live
    //   position while the tip lasts, else to the scene) -> Pursue <-> Search, Dismount when the van stops,
    //   GiveUp (siren off, brake, 2 s of fist shaking, ignores the van 30 s) -> Return (patrol loop or parking space).
    // Seeing a wanted suspect within 45 m (cone +-75 deg, all round within 15 m, from the roof) starts a pursuit, unless it
    // is inside its base's safe disc. Pursuit model (Fedya 2026-10-07, GTA-like): no give-up line near the base and no
    // stamina; the car is a little slower than the van (PoliceDirector sets it from the van, PoliceConfig balance), so a
    // clean driver pulls away on his own. A chase ends by
    //   evade: nobody (any car or officer, shared by radio) has seen the suspect for EvadeTime (10 s day / 15 s night) and
    //   it is more than EvadeDistance (80 m) from every police car (PoliceDirector checks it for all cars at once);
    //   base (canon 76): the suspect is inside its base's safe disc: the car stops at the disc's edge, waits BaseWait
    //   (8 / 12 s) watching, then leaves; never inside the disc, never a crew out there;
    //   or a search that runs out (SearchTime), the crew down, the suspect no longer wanted.
    [RequireComponent(typeof(PoliceCarMotor))]
    public sealed class PoliceUnit : MonoBehaviour
    {
        public enum UnitState : byte { Parked, Patrol, Alerted, Respond, Pursue, Dismount, Search, GiveUp, Return }

        public int Index;
        [Tooltip("Parking space index in the station lot (PoliceMapData.Stalls).")]
        public int Stall;
        public PoliceOfficer[] Crew = new PoliceOfficer[0];
        public AudioSource Siren;
        public Renderer[] Lights = new Renderer[0];
        public TextMesh Label;

        public UnitState State { get; private set; } = UnitState.Parked;
        public int Loop { get; private set; } = -1;
        public Vector3 Incident { get; private set; }
        [System.NonSerialized] public float Eta;
        public PoliceCarMotor Motor { get; private set; }
        public bool HasLineOfSight => _los;
        public float PursuitStartedAt { get; private set; } = -1f;
        public GiveUpCause LastCause { get; private set; }

        public bool IsBusy => State == UnitState.Alerted || State == UnitState.Respond || State == UnitState.Pursue ||
                              State == UnitState.Dismount || State == UnitState.Search;
        public bool Dispatchable => State == UnitState.Parked || State == UnitState.Patrol || State == UnitState.Return;

        private PoliceDirector _d;
        private PoliceConfig C => _d.Config;
        private float _stateSince, _alertedUntil, _nextSight, _nextPlan, _ignoreUntil;
        private bool _los, _contact, _wasParked, _joining;
        private PoliceDirector.Suspect _target;
        private int _preferredLoop = -1;
        private Vector2 _planTarget;
        private float _ramReadyAt, _ramUntil, _backoffUntil, _touchSince = -1f, _slowSince = -1f;
        private bool _touching;
        private int _searchStep;
        private Vector2 _searchGoal;
        private float _searchUntil;
        private float _crewBackAt;
        private bool _crewOut;
        private float _baseSince = -1f;
        private float _blink;
        private readonly PoliceRoute _plan = new(), _vanWay = new();
        private bool _planOk, _hasIntercept;
        private float _planAt, _nextIntercept, _interceptUntil, _interceptWidth, _seenAt = -99f;
        private Vector3 _intercept;
        private Vector2 _interceptDir;
        private int _stuckSeen;
        private float _noDirectUntil, _clearCheckAt;
        private Vector3 _clearTarget;
        private bool _clear;

        public string StateName => State switch
        {
            UnitState.Parked => "СТОЯНКА",
            UnitState.Patrol => "ПАТРУЛЬ",
            UnitState.Alerted => "ВЫЗОВ",
            UnitState.Respond => "ЕДЕТ",
            UnitState.Pursue => "ПОГОНЯ",
            UnitState.Dismount => "ВЫШЛИ",
            UnitState.Search => "ПОИСК",
            UnitState.GiveUp => "СДАЛСЯ",
            _ => "ВОЗВРАТ",
        };

        private void Awake()
        {
            Motor = GetComponent<PoliceCarMotor>();
        }

        private void Start()
        {
            _d = PoliceDirector.Instance;
            if (_d == null || !_d.isActiveAndEnabled)
            {
                enabled = false;
                return;
            }
            _d.Units.Add(this);
            _d.Units.Sort((a, b) => a.Index.CompareTo(b.Index));
            foreach (PoliceOfficer o in Crew)
                if (o != null) o.CrewOf = this;
            _nextSight = Time.time + Index * 0.05f;
            SetSiren(false);
            Enter(UnitState.Parked);
            // Patrol cars start somewhere on their loop that no camera sees (design 4.1).
            if (_d.ShouldPatrol(this)) PlaceOnLoop(-1f);
        }

        private void OnDestroy()
        {
            if (_d != null) _d.Units.Remove(this);
        }

        // ---------- Queries ----------

        public bool IsAfter(PoliceDirector.Suspect s) => _target == s && IsBusy;

        /// <summary>From the roof: within 45 m in a +-75 deg cone, or within 15 m all round, and nothing solid between.</summary>
        public bool Sees(Vector3 point)
        {
            Vector3 eye = transform.position + Vector3.up * C.RoofHeight;
            Vector3 to = point - eye;
            float d = to.magnitude;
            // In a pursuit the crew watches the van and nothing else: it is seen farther (a straight avenue).
            if (d > (State == UnitState.Pursue ? Mathf.Max(C.CarSightRange, C.PursuitSightRange) : C.CarSightRange)) return false;
            // A car standing still (lying in wait, at the scene) has its crew looking all round; so does a crew that had the
            // suspect in sight a moment ago (heads turn, mirrors: the van that just passed head-on is not lost at once).
            bool tracking = (State == UnitState.Pursue || State == UnitState.Dismount) && Time.time - _seenAt < C.TrackAllRound;
            if (d > C.CarAllRound && Mathf.Abs(Motor.Speed) > 2f && !tracking)
            {
                Vector3 flat = new(to.x, 0f, to.z);
                if (Vector3.Angle(transform.forward, flat) > C.CarSightHalfAngle) return false;
            }
            return !Physics.Linecast(eye, point, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore);
        }

        private bool SeesVan(Vector3 center) => Sees(center) || Sees(center + Vector3.up * 0.9f);

        public string HudText()
        {
            string text = $"#{Index + 1} {StateName}";
            if (State == UnitState.Patrol && Loop >= 0) text += " " + _d.Data.Loops[Loop].Name;
            if ((State == UnitState.Pursue || State == UnitState.Search || State == UnitState.Dismount) && _target != null)
            {
                float gap = Vector3.Distance(transform.position, _target.LastKnown);
                text += $" {gap:0} м{(_los ? " LOS" : "")}";
                if (_baseSince >= 0f) text += $", у базы {Time.time - _baseSince:0}/{C.BaseWait.At(_d.Night):0} с";
            }
            return text;
        }

        // ---------- Orders ----------

        public void Dispatch(Vector3 where, float radioDelay)
        {
            Incident = where;
            _wasParked = State == UnitState.Parked;
            _alertedUntil = Time.time + radioDelay + (_wasParked ? C.BoardingTime : 0f);
            _hasIntercept = false;
            _nextIntercept = 0f;
            _d.Target(out _target, out _, out _, out _);
            Enter(UnitState.Alerted);
        }

        public void PreferDistrict(int district)
        {
            if (_d.Crowd == null || _d.Crowd.Map == null || district < 0 || district >= _d.Crowd.Map.Districts.Count) return;
            string id = _d.Crowd.Map.Districts[district].Id;
            for (int l = 0; l < _d.Data.Loops.Length; l++)
                if (System.Array.IndexOf(_d.Data.Loops[l].Districts, id) >= 0)
                {
                    _preferredLoop = l;
                    return;
                }
        }

        /// <summary>Saw an offense with its own eyes: pursue that suspect (already after it: the sighting is enough).</summary>
        public void SawOffense(PoliceDirector.Suspect s, Vector3 where)
        {
            Incident = where;
            _ignoreUntil = 0f;
            if (State == UnitState.Pursue || State == UnitState.Search || State == UnitState.Dismount) return;
            _target = s;
            _wasParked = State == UnitState.Parked;
            _alertedUntil = Time.time + (_wasParked ? C.BoardingTime : 0.3f);
            Enter(UnitState.Alerted);
        }

        // ---------- Update ----------

        private void Update()
        {
            if (_d == null) return;
            using Unity.Profiling.ProfilerMarker.AutoScope scope = PoliceDirector.Marker.Auto();
            float now = Time.time;
            if (_target == _d.PawnSuspect && _d.Van != null && _d.PawnInVan) FollowIntoVan(now);
            if (now >= _nextSight)
            {
                _nextSight = now + 0.2f;
                Look();
            }
            switch (State)
            {
                case UnitState.Parked: TickParked(); break;
                case UnitState.Patrol: TickPatrol(now); break;
                case UnitState.Alerted: TickAlerted(now); break;
                case UnitState.Respond: TickRespond(now); break;
                case UnitState.Pursue: TickPursue(now); break;
                case UnitState.Dismount: TickDismount(now); break;
                case UnitState.Search: TickSearch(now); break;
                case UnitState.GiveUp: TickGiveUp(now); break;
                case UnitState.Return: TickReturn(now); break;
            }
            Blink(now);
        }

        // The suspect on foot got into the van (a wanted player in the van makes the van wanted): from now on the car is
        // after the van, from where the player was last seen; a crew out on foot is called back first.
        private void FollowIntoVan(float now)
        {
            PoliceDirector.Suspect van = _d.VanSuspect, pawn = _d.PawnSuspect;
            if (!van.Wanted) _d.MarkWanted(van, pawn.LastKnown);
            if (pawn.LastSeen > van.LastSeen)
            {
                van.LastKnown = pawn.LastKnown;
                van.LastSeen = pawn.LastSeen;
            }
            van.ClearAt = Mathf.Max(van.ClearAt, pawn.ClearAt);
            van.Chased |= pawn.Chased;
            _target = van;
            if (State == UnitState.Dismount && _crewOut && _crewBackAt < 0f)
            {
                _crewBackAt = now;
                foreach (PoliceOfficer o in Crew)
                    if (o != null) o.CallBack();
            }
        }

        // Every 0.2 s: can it see what the police are after? A sighting is shared with everyone (radio).
        private void Look()
        {
            _los = false;
            if (!_d.Target(out PoliceDirector.Suspect s, out Vector3 pos, out Vector3 vel, out bool isVan)) return;
            bool seen = isVan ? SeesVan(pos) : Sees(pos);
            if (!seen) return;
            if (_target == null || _target == s)
            {
                _los = true;
                _seenAt = Time.time;
            }
            _d.Sighted(s, pos, vel);
            if (Time.time < _ignoreUntil) return;
            if (State == UnitState.Patrol || State == UnitState.Respond || State == UnitState.Search || State == UnitState.Return ||
                (State == UnitState.Alerted && !_wasParked))
                TryPursue(s, pos);
        }

        private void TryPursue(PoliceDirector.Suspect s, Vector3 pos)
        {
            if (State == UnitState.Search && s == _target && _contact)
            {
                Enter(UnitState.Pursue);
                return;
            }
            if (_d.InsideSafe(pos)) return; // at its base: never a chase from there (canon 76)
            _target = s;
            s.Chased = true;
            if (!_contact)
            {
                _contact = true;
                PursuitStartedAt = Time.time;
            }
            Enter(UnitState.Pursue);
            PoliceEvents.RaisePursuitStarted(this);
            if (_d.Log) Debug.Log($"[Police] #{Index + 1} PURSUIT of {s.Name} at {Vector3.Distance(transform.position, pos):0} m", this);
        }

        private void Enter(UnitState state)
        {
            State = state;
            _stateSince = Time.time;
            _nextPlan = 0f;
            _baseSince = -1f;
            switch (state)
            {
                case UnitState.Parked:
                    Motor.Mode = PoliceCarMotor.DriveMode.Stop;
                    Motor.Handbrake = true;
                    SetSiren(false);
                    _contact = false;
                    break;
                case UnitState.Alerted:
                case UnitState.Respond:
                case UnitState.Pursue:
                case UnitState.Search:
                    Motor.Handbrake = false;
                    SetSiren(true);
                    break;
                case UnitState.Dismount:
                    SetSiren(true);
                    break;
                case UnitState.GiveUp:
                case UnitState.Patrol:
                case UnitState.Return:
                    Motor.Handbrake = false;
                    SetSiren(false);
                    break;
            }
            if (state == UnitState.Search)
            {
                _searchStep = 0;
                _searchUntil = Time.time + C.SearchTime.At(_d.Night);
            }
        }

        // ---------- States ----------

        private void TickParked()
        {
            Motor.Mode = PoliceCarMotor.DriveMode.Stop;
            Motor.Handbrake = true;
            ReclaimCrew();
            if (_d.ShouldPatrol(this)) StartPatrol();
        }

        // Crew left behind earlier and gone off the map since: back in the car (at the station or at the end of a lap).
        private void ReclaimCrew()
        {
            foreach (PoliceOfficer o in Crew)
                if (o != null && o.Orphaned && !o.gameObject.activeSelf) o.Board(true);
        }

        private void StartPatrol()
        {
            int loop = _d.ChooseLoop(this, _preferredLoop);
            _preferredLoop = -1;
            if (loop < 0)
            {
                Enter(UnitState.Parked);
                return;
            }
            Loop = loop;
            Enter(UnitState.Patrol);
            JoinLoop();
        }

        // Drive (A*) to the nearest point of the loop, then follow it.
        private void JoinLoop()
        {
            _d.Data.LoopRoute(Loop, Motor.Route);
            Vector2 here = Motor.Position2, best = here;
            float bestD = float.MaxValue;
            foreach (Vector2 p in Motor.Route.Points)
            {
                float d = (p - here).sqrMagnitude;
                if (d < bestD)
                {
                    bestD = d;
                    best = p;
                }
            }
            if (bestD < 100f)
            {
                Motor.StartLoopNearest();
                _joining = false;
                return;
            }
            _joining = PlanTo(best);
            if (!_joining) Motor.StartLoopNearest();
        }

        private void TickPatrol(float now)
        {
            Motor.Mode = PoliceCarMotor.DriveMode.Route;
            Motor.MaxSpeed = PoliceConfig.Kmh(C.PatrolKmh);
            Motor.KeepRight = true;
            Motor.CutCorners = false;
            Motor.StopAtEnd = 4f;
            if (_joining)
            {
                if (Motor.AtRouteEnd)
                {
                    _joining = false;
                    _d.Data.LoopRoute(Loop, Motor.Route);
                    Motor.StartLoopNearest();
                }
                return;
            }
            if (Motor.Laps > 0)
            {
                ReclaimCrew();
                // End of a lap: keep patrolling (maybe another loop) or go home to park.
                if (!_d.ShouldPatrol(this))
                {
                    Loop = -1;
                    Enter(UnitState.Return);
                    return;
                }
                int next = _d.ChooseLoop(this, _preferredLoop);
                _preferredLoop = -1;
                if (next >= 0 && next != Loop)
                {
                    Loop = next;
                    JoinLoop();
                }
                else Motor.StartLoopNearest();
            }
        }

        private void TickAlerted(float now)
        {
            if (!_wasParked && Motor.Mode == PoliceCarMotor.DriveMode.Route) Motor.MaxSpeed = PoliceConfig.Kmh(C.PatrolKmh); // still on patrol till the radio
            else
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Stop;
                Motor.Handbrake = false;
            }
            if (now >= _alertedUntil) Enter(UnitState.Respond);
        }

        private void TickRespond(float now)
        {
            Vector3 goal = Incident;
            // The van's live position (the tip) only while it is outside its base's safe disc: a tip never leads a car to the
            // base. When the tip runs out, a car that already picked a meeting point on the van's way home keeps it (a
            // stake-out) until the van should long have passed there; it only knows where it expects the van, not where it is.
            bool toVan = false;
            if (_d.Van != null && (_d.Tip || (_hasIntercept && now < _interceptUntil)))
            {
                Vector3 van = _d.VanCenter;
                if (!_d.InsideSafe(van))
                {
                    goal = _d.Tip ? Intercept(van, now) : _intercept;
                    toVan = true;
                }
            }
            // At the meeting point ahead of the van: wait there for it at the roadside, facing the van's way home, so it can
            // pull out right behind the van when it passes (it sees all round while standing).
            if (toVan && _hasIntercept && Vector2.Distance(Motor.Position2, PoliceDirector.Plan(goal)) < C.InterceptWait)
            {
                WaitForVan(now);
                if (now - _stateSince > 120f) GiveUp(GiveUpCause.Lost);
                return;
            }
            DriveTo(goal, _d.ChaseTopSpeed, true, now, 0f);
            if (Vector3.Distance(transform.position, Incident) < 15f && !toVan)
            {
                _searchGoal = PoliceDirector.Plan(Incident);
                Enter(UnitState.Search);
                return;
            }
            if (now - _stateSince > 120f) GiveUp(GiveUpCause.Lost);
        }

        // Where to meet the van while the tip lasts: the first point of its likely way home (the shortest road route to the
        // home base, as the bake's timing model drives it) that this car reaches before the van does, with some chase left
        // before the base's safe disc; none: a little ahead of the van itself. Re-planned once a second.
        private Vector3 Intercept(Vector3 van, float now)
        {
            if (now >= _nextIntercept)
            {
                _nextIntercept = now + 1f;
                // At its meeting point it stays, unless the van's way home no longer passes near it (the van turned off):
                // re-planning from the roadside always finds a point a few metres on, which is not a reason to move.
                bool there = _hasIntercept && Vector2.Distance(Motor.Position2, PoliceDirector.Plan(_intercept)) < C.InterceptWait;
                bool found = FindIntercept(van, out Vector3 point, out Vector2 dir, out float width, out float tVan);
                if (!there || (found && Vector2.Distance(PoliceDirector.Plan(point), PoliceDirector.Plan(_intercept)) > 40f))
                {
                    _hasIntercept = found;
                    _intercept = point;
                    _interceptDir = dir;
                    _interceptWidth = width;
                    if (found) _interceptUntil = now + tVan + C.InterceptHold;
                }
            }
            if (_hasIntercept) return _intercept;
            // No meeting point: go for the van itself. Ahead of it when it drives away from the car; straight at it when it
            // comes toward the car (a point "ahead" would then swing round behind the car with every replan, and the car
            // would turn in circles where the van is about to come through).
            Vector3 vanVel = Vector3.ProjectOnPlane(_d.VanVelocity, Vector3.up);
            if (Vector3.Dot(vanVel, transform.position - van) > 0f) return van;
            float lead = Mathf.Clamp(Vector3.Distance(transform.position, van) / Mathf.Max(5f, _d.ChaseTopSpeed), 0f, 4f);
            Vector3 ahead = van + vanVel * lead;
            return !_d.InsideSafe(ahead) ? ahead : van;
        }

        /// <summary>Responding at a meeting point on the van's way home (other cars pick another one).</summary>
        public bool HasIntercept(out Vector3 point)
        {
            point = _intercept;
            return State == UnitState.Respond && _hasIntercept;
        }

        // The first point of the van's likely way home this car reaches InterceptMargin s before the van, still worth it:
        // the van has at least InterceptMinChase s of driving (straight line) left there before the base's safe disc (else
        // the car goes for the van itself, from behind), and no other responding car waits within 40 m (two cars racing to
        // one junction from opposite sides meet head-on). Also the van's direction and the road width there.
        private bool FindIntercept(Vector3 van, out Vector3 point, out Vector2 dir, out float width, out float tVan)
        {
            point = van;
            dir = Vector2.zero;
            width = 6f;
            tVan = 0f;
            PoliceMapData data = _d.Data;
            int home = _d.HomeBase;
            if (home < 0 || home >= data.BaseCount) return false;
            if (!data.FindRoute(PoliceDirector.Plan(van), Vector2.zero, data.BaseDoors[home], -1, false, 0f, 0f, _vanWay, true)) return false;
            data.ComputeEtas(Motor.Position2, home); // police seconds from this car to every node
            float vanSpeed = Mathf.Max(C.InterceptVanSpeed, _d.VanVelocity.magnitude);
            float line = data.SafeRadius + C.InterceptMinChase * vanSpeed;
            float along = 0f;
            var pts = _vanWay.Points;
            for (int i = 1; i < pts.Count; i++)
            {
                float len = Vector2.Distance(pts[i - 1], pts[i]);
                for (float s = Mathf.Min(10f, len); s <= len; s += 10f)
                {
                    Vector2 p = Vector2.Lerp(pts[i - 1], pts[i], len > 1e-3f ? s / len : 1f);
                    float t = (along + s) / vanSpeed;
                    if (data.DoorDistance(home, p) <= line) return false; // too close to the base: a chase from there is not worth it
                    Vector2 way = len > 1e-3f ? (pts[i] - pts[i - 1]) / len : Vector2.zero;
                    // In time, and getting there going the van's way (from a side street or from behind, never head-on:
                    // a car met head-on has to turn round after the van and loses it).
                    if (data.EtaTo(p, out Vector2 arriving) + C.InterceptMargin > t || Vector2.Dot(arriving, way) < 0.3f || TakenByOther(p)) continue;
                    point = new Vector3(p.x, van.y, p.y);
                    dir = way;
                    width = _vanWay.Widths.Count >= i ? _vanWay.Widths[i - 1] : 6f;
                    tVan = t;
                    return true;
                }
                along += len;
            }
            return false;
        }

        private bool TakenByOther(Vector2 p)
        {
            foreach (PoliceUnit u in _d.Units)
                if (u != this && u.HasIntercept(out Vector3 q) && (PoliceDirector.Plan(q) - p).sqrMagnitude < 1600f) return true;
            return false;
        }

        // At the meeting point: to the right-hand roadside a little on along the van's way, nose toward its way home (a
        // K-turn first when it came the other way), then stand. The van passes on its left; the car pulls out behind it.
        private void WaitForVan(float now)
        {
            Vector2 dir = _interceptDir.sqrMagnitude > 0.5f ? _interceptDir : Motor.Forward2;
            var right = new Vector2(dir.y, -dir.x);
            float side = Mathf.Clamp(_interceptWidth * 0.5f - 0.9f, 1.2f, 2.4f);
            Vector2 spot = PoliceDirector.Plan(_intercept) + dir * 8f + right * side;
            Vector2 here = Motor.Position2;
            bool facing = Vector2.Dot(Motor.Forward2, dir) > 0.8f;
            bool near = Vector2.Distance(here, spot) < 8f;
            if (facing && near)
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Stop;
                Motor.Handbrake = false;
                return;
            }
            // Near the spot with a clear way, nose the wrong way: aim on along the van's way, so it turns (or K-turns)
            // round on the spot. Otherwise there along the roads (never straight across a block).
            Vector3 aim = Ground(near ? spot + dir * 12f : spot) + Vector3.up;
            if (near && ClearTo(aim, now))
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = PoliceDirector.Plan(aim);
                Motor.Handbrake = false;
                Motor.MaxSpeed = Mathf.Min(PoliceConfig.Kmh(15f), SafeSpeed());
                return;
            }
            DriveTo(Ground(spot), PoliceConfig.Kmh(30f), false, now, 0f, 1f, 0f);
        }

        private void TickPursue(float now)
        {
            PoliceDirector.Suspect s = _target;
            if (s == null || !s.Wanted)
            {
                GiveUp(GiveUpCause.Ordered);
                return;
            }
            bool targetIsVan = s == _d.VanSuspect;
            Vector3 pos, vel;
            if (targetIsVan && (_los || s.SinceSeen < 0.5f))
            {
                pos = _d.VanCenter; // in sight (its own or someone's on the radio)
                vel = _d.VanVelocity;
            }
            else if (targetIsVan)
            {
                // Out of sight a moment: on along the way it was going (dead reckoning from the last sighting), so the car
                // keeps driving after it instead of braking to a stop where it was last seen.
                vel = s.Velocity;
                pos = s.LastKnown + Vector3.ProjectOnPlane(vel, Vector3.up) * Mathf.Min(s.SinceSeen, C.LostSightTime.At(_d.Night));
            }
            else
            {
                pos = s.LastKnown;
                vel = Vector3.zero;
            }
            float gap = Vector3.Distance(transform.position, pos);
            // The base rule is a game rule on where the suspect really is (the car may only know an old position).
            Vector3 actual = targetIsVan ? _d.VanCenter : _d.Pawn != null ? _d.Pawn.Position : pos;
            if (AtBase(actual, now)) return;
            // Out of sight: nobody has seen it for N s and it is more than 50 m away (or the car stands where it was last
            // seen): search. The evade rule (PoliceDirector) ends the whole chase when it stays unseen and far.
            if (s.SinceSeen > C.LostSightTime.At(_d.Night) && (Vector3.Distance(transform.position, actual) > C.LostSightDistance || gap < 12f))
            {
                _searchGoal = PoliceDirector.Plan(s.LastKnown);
                Enter(UnitState.Search);
                return;
            }
            // Stopped van (or a suspect on foot close by): the crew gets out.
            float vanKmh = targetIsVan ? _d.VanSpeedKmh : 0f;
            if (targetIsVan)
            {
                if (vanKmh < C.DismountVanKmh && gap < C.DismountRange)
                {
                    if (_slowSince < 0f) _slowSince = now;
                    if (now - _slowSince >= C.DismountDelay)
                    {
                        StartDismount();
                        return;
                    }
                }
                else _slowSince = -1f;
            }
            else if (gap < 15f)
            {
                StartDismount();
                return;
            }
            Chase(pos, vel, gap, vanKmh, now);
        }

        // Canon 76: the police never storm a base. The suspect is inside its base's safe disc: on toward it up to the
        // disc's edge (routes never enter the disc, SafeSpeed stops the car 5 m before it), wait there BaseWait s watching,
        // then leave. No crew out, no bump. It comes out of the disc before that: the chase goes on (false).
        private bool AtBase(Vector3 actual, float now)
        {
            if (!_d.InsideSafe(actual))
            {
                _baseSince = -1f;
                return false;
            }
            _slowSince = -1f;
            bool atEdge = _d.DoorDistance(transform.position) < _d.Data.SafeRadius + C.BaseEdgeBand || Mathf.Abs(Motor.Speed) < 1f;
            if (atEdge && _baseSince < 0f) _baseSince = now;
            if (_baseSince >= 0f && now - _baseSince >= C.BaseWait.At(_d.Night))
            {
                GiveUp(GiveUpCause.Base);
                return true;
            }
            DriveTo(actual, _d.ChaseTopSpeed, true, now, 5f, C.ChaseUTurnScale, 0f);
            return true;
        }

        // Speeds by gap (design 2.3), never over the chase top speed (a little under the van's), and the light bump. No
        // catch-up out of sight: a van that drives cleanly gets away.
        private void Chase(Vector3 pos, Vector3 vel, float gap, float vanKmh, float now)
        {
            // Stuck while driving straight at the van (a low wall, a fence, a facade): the roads for a while.
            if (Motor.StuckEpisodes != _stuckSeen)
            {
                _stuckSeen = Motor.StuckEpisodes;
                if (Motor.Mode == PoliceCarMotor.DriveMode.Direct) _noDirectUntil = now + C.DirectBlockAfterStuck;
            }
            bool directOk = now >= _noDirectUntil;
            float closing = Mathf.Max(1f, Motor.Speed - Vector3.Dot(vel, (pos - transform.position).normalized));
            float lead = Mathf.Clamp(gap / closing, 0f, 1.5f);
            Vector3 predicted = pos + vel * lead;
            float vanSpeed = vanKmh / 3.6f;
            float top = _d.ChaseTopSpeed;
            float speed;
            if (gap > 15f) speed = top;
            else if (gap > C.RamDistance) speed = vanSpeed + 1.5f;
            else speed = Mathf.Max(0f, vanSpeed - 1f); // close behind: a little slower, the van's next braking is not a crash
            // Never faster than it can still brake down to the van's speed before reaching it (the van slows hard for a
            // sharp corner; at 100 km/h 25 m behind, the police car otherwise rear-ends it and pins it in the corner).
            if (gap < 60f) speed = Mathf.Min(speed, Mathf.Sqrt(vanSpeed * vanSpeed + 2f * Motor.Brake * 0.7f * Mathf.Max(0f, gap - C.RamDistance)));
            // Touching too long: back off. Close behind, lined up, ram ready: a light bump.
            if (_touching)
            {
                if (_touchSince < 0f) _touchSince = now;
                if (now - _touchSince > 1.5f) _backoffUntil = now + 2f;
            }
            else _touchSince = -1f;
            Vector3 toVan = pos - transform.position;
            bool lined = Vector3.Angle(transform.forward, new Vector3(toVan.x, 0f, toVan.z)) < C.RamAngle;
            // The light bump only at town speeds: at 80 km/h a "light" push sends the van into the next wall, and the joke is over.
            if (gap < C.RamDistance && lined && vanKmh > C.RamMinVanKmh && vanKmh < C.RamMaxVanKmh && now >= _ramReadyAt && now >= _backoffUntil)
            {
                _ramUntil = now + 1f;
                _ramReadyAt = now + C.RamCooldown.At(_d.Night);
            }
            if (now < _ramUntil) speed = vanSpeed + C.RamExtra;
            if (now < _backoffUntil) speed = Mathf.Max(0f, vanSpeed - 3f);
            speed = Mathf.Min(speed, top, SafeSpeed());
            // The van comes head-on (it met the car at the meeting point, or turned round): pull over to the right and let it
            // pass, then turn after it (the target behind: full lock or a K-turn). Never a head-on crash.
            Vector3 fromVan = transform.position - pos;
            fromVan.y = 0f;
            Vector3 vanFlat = new(vel.x, 0f, vel.z);
            if (gap < 45f && vanFlat.magnitude > 4f && Vector3.Dot(vanFlat.normalized, fromVan.normalized) > 0.6f &&
                Vector3.Dot(transform.forward, -fromVan.normalized) > 0.3f)
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = PoliceDirector.Plan(transform.position + transform.forward * 6f + transform.right * 2.5f);
                Motor.MaxSpeed = Mathf.Min(PoliceConfig.Kmh(10f), SafeSpeed());
                return;
            }
            // The van comes up from behind, going the car's way (it waited at the roadside for it): roll on slowly in its own
            // lane and let it come by, then follow. Never backing into it.
            if (gap < 40f && vanFlat.magnitude > 4f && Vector3.Dot(transform.forward, -fromVan.normalized) < -0.2f &&
                Vector3.Dot(vanFlat.normalized, transform.forward) > 0.5f)
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = PoliceDirector.Plan(transform.position + transform.forward * 12f);
                Motor.MaxSpeed = Mathf.Min(Mathf.Clamp(vanSpeed * 0.5f, 2f, 10f), SafeSpeed());
                return;
            }
            // Slow van: box it in (stop 4.5 m ahead of its nose, 1.5 m to the side, angled across).
            if (_d.Van != null && vanKmh < C.BoxInVanKmh && gap < 30f && directOk)
            {
                Transform v = _d.Van.transform;
                Vector3 box = v.position + v.forward * 4.5f + v.right * 1.5f;
                if (ClearTo(box + Vector3.up, now))
                {
                    Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                    Motor.DirectPoint = PoliceDirector.Plan(box);
                    Motor.MaxSpeed = Mathf.Min(Mathf.Clamp(Vector3.Distance(transform.position, box) * 0.8f, 0f, PoliceConfig.Kmh(30f)), SafeSpeed());
                    return;
                }
            }
            if (gap <= 30f && _los && directOk && ClearTo(predicted, now))
            {
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = PoliceDirector.Plan(predicted);
                Motor.MaxSpeed = Mathf.Max(0f, speed); // already capped by SafeSpeed
                Motor.CutCorners = true;
                Motor.KeepRight = false;
                return;
            }
            // In a chase a turn on the spot is cheap (a handbrake turn): the van that just went by is followed, not
            // driven round the block for.
            DriveTo(predicted, speed, true, now, 5f, C.ChaseUTurnScale, Mathf.Max(3f, vanSpeed));
        }

        // Nothing low and solid on the straight line to 'target' (a car-wide sweep 0.3-1.7 m above the road): kerbs pass,
        // low walls, fences and facades do not. Checked at most every 0.2 s per target.
        private bool ClearTo(Vector3 target, float now)
        {
            if (now < _clearCheckAt && (target - _clearTarget).sqrMagnitude < 4f) return _clear;
            _clearCheckAt = now + 0.2f;
            _clearTarget = target;
            Vector3 from = transform.position + transform.up * 1.0f;
            Vector3 to = target - from;
            float dist = to.magnitude - 0.5f;
            _clear = dist <= 0.5f || !Physics.SphereCast(from, 0.7f, to.normalized, out _, dist, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore);
            return _clear;
        }

        private void StartDismount()
        {
            _slowSince = -1f;
            Enter(UnitState.Dismount);
            _crewOut = false;
            _crewBackAt = -1f;
        }

        // Doors open: the crew appears at the left and right doors (+-1.3 m) and goes for the suspect.
        private void CrewOut()
        {
            _crewOut = true;
            int i = 0;
            foreach (PoliceOfficer o in Crew)
            {
                if (o == null || !o.Inside) continue;
                bool left = i++ % 2 == 0;
                Vector3 door = transform.TransformPoint(new Vector3(left ? -1.3f : 1.3f, 0.1f, 0.2f));
                o.GetOut(door, transform.eulerAngles.y + (left ? -90f : 90f), _target);
            }
        }

        private void TickDismount(float now)
        {
            PoliceDirector.Suspect s = _target;
            bool targetIsVan = s == _d.VanSuspect;
            Vector3 pos = targetIsVan ? _d.VanCenter : s != null ? s.LastKnown : transform.position;
            // The last metres first: stop about 6 m from the van, then open the doors.
            float gap = Vector3.Distance(transform.position, pos);
            if (!_crewOut)
            {
                // It rolled into its base's safe disc meanwhile: no doors open there (canon 76), the chase rules take over.
                if (_d.InsideSafe(pos))
                {
                    Enter(UnitState.Pursue);
                    return;
                }
                if (gap > 7.5f && now - _stateSince < 4f)
                {
                    Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                    Motor.DirectPoint = PoliceDirector.Plan(pos);
                    Motor.Handbrake = false;
                    Motor.MaxSpeed = Mathf.Min(Mathf.Clamp((gap - 6f) * 0.8f, 1f, 8f), SafeSpeed());
                    return;
                }
                Motor.Mode = PoliceCarMotor.DriveMode.Stop;
                Motor.Handbrake = true;
                if (Mathf.Abs(Motor.Speed) > 1f) return;
                CrewOut();
            }
            Motor.Mode = PoliceCarMotor.DriveMode.Stop;
            Motor.Handbrake = true;
            bool allDown = true, allIn = true;
            foreach (PoliceOfficer o in Crew)
            {
                if (o == null) continue;
                if (!o.Down) allDown = false;
                if (!o.Inside && !o.Down && !o.Orphaned) allIn = false;
            }
            if (allDown && Crew.Length > 0)
            {
                GiveUp(GiveUpCause.CrewDown);
                return;
            }
            bool done = s == null || !s.Wanted;
            bool gone = (targetIsVan && gap > C.CrewReturnDistance + 6f) || _d.InsideSafe(pos);
            if ((done || gone) && _crewBackAt < 0f)
            {
                _crewBackAt = now;
                foreach (PoliceOfficer o in Crew)
                    if (o != null) o.CallBack();
            }
            if (_crewBackAt >= 0f && (allIn || now - _crewBackAt > 15f))
            {
                foreach (PoliceOfficer o in Crew)
                    if (o != null && !o.Inside && !o.Down) o.Orphan(); // left behind: walks off on his own
                if (done) GiveUp(GiveUpCause.Ordered);
                else Enter(UnitState.Pursue);
            }
        }

        private void TickSearch(float now)
        {
            if (_target != null && !_target.Wanted)
            {
                GiveUp(GiveUpCause.Ordered);
                return;
            }
            if (now >= _searchUntil)
            {
                GiveUp(GiveUpCause.Lost);
                return;
            }
            // Last known position, then on along the van's last direction, then random branches (routes never enter the
            // base's safe disc: a search never goes into it).
            if (Vector2.Distance(Motor.Position2, _searchGoal) < 12f || (Motor.AtRouteEnd && now - _stateSince > 2f))
            {
                _searchStep++;
                Vector2 from = Motor.Position2;
                if (_searchStep == 1 && _target != null && _target.Velocity.sqrMagnitude > 1f)
                    _searchGoal = PoliceDirector.Plan(_target.LastKnown) + new Vector2(_target.Velocity.x, _target.Velocity.z).normalized * 80f;
                else
                {
                    PoliceMapData data = _d.Data;
                    int node = Random.Range(0, data.NodeCount);
                    for (int k = 0; k < 20; k++)
                    {
                        float dist = Vector2.Distance(data.Nodes[node], from);
                        if (dist > 50f && dist < 130f && data.Degree(node) >= 3) break;
                        node = Random.Range(0, data.NodeCount);
                    }
                    _searchGoal = data.Nodes[node];
                }
                _nextPlan = 0f;
            }
            DriveTo(new Vector3(_searchGoal.x, transform.position.y, _searchGoal.y), PoliceConfig.Kmh(60f), true, now, 4f);
        }

        public void GiveUp(GiveUpCause cause)
        {
            if (State == UnitState.GiveUp) return;
            bool wasChasing = State == UnitState.Pursue || State == UnitState.Search || State == UnitState.Dismount || State == UnitState.Respond;
            LastCause = cause;
            PoliceDirector.Suspect target = _target;
            Enter(UnitState.GiveUp);
            Motor.Mode = PoliceCarMotor.DriveMode.Stop;
            Motor.Handbrake = true;
            // Only a car that had the van (or the player) in sight sulks and ignores it for a while; a responder that never
            // saw anyone just turns back, and it was no pursuit.
            if (_contact) _ignoreUntil = Time.time + C.IgnoreAfterGiveUp;
            foreach (PoliceOfficer o in Crew)
                if (o != null && !o.Inside && !o.Down) o.Orphan();
            // Lost it, or left it at its base: the wanted flag passes quickly once nobody else is after it (canon 82).
            if (target != null && (cause == GiveUpCause.Evaded || cause == GiveUpCause.Base || (cause == GiveUpCause.Lost && _contact)))
                _d.ReleaseSoon(target);
            if (wasChasing && _contact)
            {
                // Information for the HUD and tests: metres along the roads the suspect still was from the team's home.
                float metres = float.PositiveInfinity;
                if (target != null && _d.Data.BaseCount > 0)
                {
                    Vector3 at = target == _d.VanSuspect && _d.Van != null ? _d.VanCenter : target.LastKnown;
                    var route = new PoliceRoute();
                    if (_d.Data.FindRoute(PoliceDirector.Plan(at), Vector2.zero, _d.Data.BaseDoors[_d.HomeBase], -1, false, 0f, 0f, route))
                        metres = route.Length();
                }
                PoliceEvents.RaisePursuitEnded(this, cause, metres);
            }
            if (Label != null) Label.text = "Тьфу!";
        }

        private void TickGiveUp(float now)
        {
            Motor.Mode = PoliceCarMotor.DriveMode.Stop;
            if (now - _stateSince < C.GiveUpShakeTime) return;
            if (Label != null) Label.text = "";
            _contact = false;
            _target = null;
            Enter(UnitState.Return);
        }

        private void TickReturn(float now)
        {
            if (_d.ShouldPatrol(this))
            {
                StartPatrol();
                return;
            }
            // Back to its own parking space, nose in.
            Vector3 stall = _d.Data.Stalls.Length > Stall ? _d.Data.Stalls[Stall] : Vector3.zero;
            var stall2 = new Vector2(stall.x, stall.y);
            if (now >= _nextPlan)
            {
                _nextPlan = now + 5f;
                // A car that somehow ended up at the home base's door may leave through the safe disc.
                _planOk = PlanTo(stall2, _d.DoorDistance(transform.position) > _d.Data.SafeRadius + 10f);
                if (!_planOk) _nextPlan = now + 1f;
                Motor.StopAtEnd = 0f;
            }
            if (!_planOk)
            {
                // No road within reach: slowly straight toward the station until a plan works.
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = stall2;
                Motor.MaxSpeed = Mathf.Min(PoliceConfig.Kmh(20f), SafeSpeed());
                return;
            }
            Motor.Mode = PoliceCarMotor.DriveMode.Route;
            Motor.MaxSpeed = PoliceConfig.Kmh(Motor.RouteLength - Motor.Progress < 30f ? 12f : C.PatrolKmh + 10f);
            Motor.KeepRight = Motor.RouteLength - Motor.Progress > 30f;
            Motor.CutCorners = false;
            if (Motor.AtRouteEnd && Mathf.Abs(Motor.Speed) < 1f) Enter(UnitState.Parked);
        }

        // ---------- Driving helpers ----------

        // Route mode to a world point, re-planned every ReplanInterval or when the goal moved more than 'replanMove' m.
        // endSpeed: m/s at the end of the route (a chase does not brake for a goal that moves on).
        private void DriveTo(Vector3 goal, float maxSpeed, bool cut, float now, float replanMove, float uTurnScale = 1f, float endSpeed = 3f)
        {
            Vector2 g = PoliceDirector.Plan(goal);
            // Mid K-turn the route stays (a new one could want the other way round and the car would see-saw), for up to 4 s.
            bool frozen = _planOk && Motor.Manoeuvring && now - _planAt < 4f;
            if (!frozen && (now >= _nextPlan || (replanMove > 0f && Vector2.Distance(g, _planTarget) > Mathf.Max(replanMove, 15f))))
            {
                _nextPlan = now + C.ReplanInterval;
                _planOk = PlanTo(g, true, uTurnScale);
            }
            if (!_planOk)
            {
                // No police route (the car or the goal far from any road): straight at it, never into the safe disc.
                Motor.Mode = PoliceCarMotor.DriveMode.Direct;
                Motor.DirectPoint = g;
                Motor.MaxSpeed = Mathf.Min(maxSpeed, SafeSpeed());
                Motor.CutCorners = true;
                Motor.KeepRight = false;
                return;
            }
            Motor.Mode = PoliceCarMotor.DriveMode.Route;
            Motor.MaxSpeed = Mathf.Min(maxSpeed, SafeSpeed());
            Motor.CutCorners = cut;
            Motor.KeepRight = !cut;
            Motor.StopAtEnd = endSpeed;
        }

        // Never into the home base's safe disc: no faster than it can still stop 5 m before its edge (straight-line metres).
        private float SafeSpeed()
        {
            float room = _d.DoorDistance(transform.position) - _d.Data.SafeRadius - 5f;
            if (room > 0f) return Mathf.Sqrt(2f * Motor.Brake * room);
            // Already inside (a patrol loop passes the door, then the call came): out again slowly, never on toward the door
            // (its routes avoid the disc, so they lead out).
            Vector2 toDoor = _d.Data.BaseDoors[_d.HomeBase] - Motor.Position2;
            Vector3 v = Motor.Body.linearVelocity;
            return Vector2.Dot(new Vector2(v.x, v.z), toDoor) > 0.5f ? 0f : PoliceConfig.Kmh(20f);
        }

        // Plans into a scratch route and hands it to the motor only when it worked: a failed plan never leaves the motor
        // with an empty or half-changed route.
        private bool PlanTo(Vector2 goal, bool avoidHome = true, float uTurnScale = 1f)
        {
            _planTarget = goal;
            Vector2 heading = Mathf.Abs(Motor.Speed) > 2f ? Motor.Forward2 * Mathf.Sign(Motor.Speed) : Motor.Forward2;
            // Turning round costs more the faster the car goes (braking, the K-turn, the run-up): a moving car keeps its way
            // round the block instead of see-sawing after a goal that moves.
            float uTurn = C.UTurnPenalty * uTurnScale * (1f + Mathf.Max(0f, Motor.Speed) / 10f);
            if (!_d.Data.FindRoute(Motor.Position2, heading, goal, avoidHome ? _d.HomeBase : -1, true, C.TurnPenalty, uTurn, _plan))
                return false;
            PoliceRoute route = Motor.Route;
            route.Points.Clear();
            route.Widths.Clear();
            route.Points.AddRange(_plan.Points);
            route.Widths.AddRange(_plan.Widths);
            route.Loop = false;
            Motor.RouteChanged();
            _planAt = Time.time;
            return true;
        }

        /// <summary>Puts the car on its patrol loop (at fraction 'along' 0..1, or a random place no camera sees when < 0).</summary>
        public void PlaceOnLoop(float along)
        {
            int loop = _d.ChooseLoop(this, -1);
            if (loop < 0) return;
            Loop = loop;
            _d.Data.LoopRoute(loop, Motor.Route);
            var pts = Motor.Route.Points;
            if (pts.Count < 2) return;
            int index = 0;
            if (along >= 0f) index = Mathf.Clamp(Mathf.RoundToInt(along * (pts.Count - 1)), 0, pts.Count - 2);
            else
                for (int attempt = 0; attempt < 30; attempt++)
                {
                    index = Random.Range(0, pts.Count - 1);
                    if (_d.Crowd == null || !_d.Crowd.Visible(Ground(pts[index]), 30f)) break;
                }
            Vector2 p = pts[index], dir = pts[index + 1] - pts[index];
            float yaw = dir.sqrMagnitude > 1e-4f ? Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg : 0f;
            Motor.Teleport(Ground(p) + Vector3.up * 0.4f, yaw);
            Motor.StartLoopNearest();
            _joining = false;
            Enter(UnitState.Patrol);
        }

        /// <summary>Back into its parking space, parked (tests).</summary>
        public void ResetToStall()
        {
            Vector3 stall = _d.Data.Stalls.Length > Stall ? _d.Data.Stalls[Stall] : Vector3.zero;
            Vector2 p = new Vector2(stall.x, stall.y) - new Vector2(Mathf.Sin(stall.z * Mathf.Deg2Rad), Mathf.Cos(stall.z * Mathf.Deg2Rad)) * 0.85f;
            Motor.Teleport(Ground(p) + Vector3.up * 0.4f, stall.z);
            _target = null;
            _contact = false;
            _hasIntercept = false;
            _ignoreUntil = 0f;
            foreach (PoliceOfficer o in Crew)
                if (o != null) o.Board(true);
            Loop = -1;
            Enter(UnitState.Parked);
        }

        private Vector3 Ground(Vector2 p)
        {
            if (_d.Crowd != null) return _d.Crowd.Ground(p);
            return Physics.Raycast(new Vector3(p.x, 200f, p.y), Vector3.down, out RaycastHit hit, 400f, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore)
                ? hit.point : new Vector3(p.x, transform.position.y, p.y);
        }

        // ---------- Siren, lights ----------

        private void SetSiren(bool on)
        {
            if (Siren != null)
            {
                if (Siren.clip == null && Sfx.Library != null && Sfx.Library.Find(SfxIds.PoliceSiren) is SfxLibrary.Entry e && e.Clips != null && e.Clips.Length > 0)
                    Siren.clip = e.Clips[0];
                if (on && !Siren.isPlaying && Siren.clip != null) Siren.Play();
                else if (!on && Siren.isPlaying) Siren.Stop();
            }
            if (!on)
                foreach (Renderer r in Lights)
                    if (r != null) r.enabled = false;
        }

        private void Blink(float now)
        {
            bool on = Siren != null ? Siren.isPlaying || State == UnitState.Alerted || State == UnitState.Respond || State == UnitState.Pursue || State == UnitState.Dismount || State == UnitState.Search
                                    : IsBusy;
            if (!on) return;
            _blink += Time.deltaTime;
            bool phase = Mathf.Repeat(_blink * 3f, 1f) < 0.5f;
            for (int i = 0; i < Lights.Length; i++)
                if (Lights[i] != null) Lights[i].enabled = (i % 2 == 0) == phase;
        }

        // ---------- Collisions ----------

        private void OnCollisionEnter(Collision collision)
        {
            if (_d == null || _d.VanBody == null || collision.rigidbody != _d.VanBody) return;
            float rel = collision.relativeVelocity.magnitude;
            Vector3 where = collision.contactCount > 0 ? collision.GetContact(0).point : transform.position;
            if (rel > 3f)
            {
                PoliceEvents.RaiseSlapstick(this, where, rel);
                Sfx.PlayAt(SfxIds.ThudVan, where, Mathf.Clamp01(rel / 10f));
            }
            if (rel > 8f) Motor.SpinOut();
            // The van rammed us (it was the faster one): that is an offense in itself.
            float vanSpeed = _d.VanBody.linearVelocity.magnitude, mine = Motor.Body.linearVelocity.magnitude;
            // One crash is one offense: its bounces and scrapes (more contacts within a few seconds) add nothing.
            if (rel > 5f && vanSpeed > mine && State != UnitState.Pursue && Time.time >= _ignoreUntil && Time.time >= _nextRamOffense)
            {
                _nextRamOffense = Time.time + 3f;
                _d.Rammed(this);
            }
        }

        private float _nextRamOffense;

        private void OnCollisionStay(Collision collision)
        {
            if (_d != null && _d.VanBody != null && collision.rigidbody == _d.VanBody) _touching = true;
        }

        private void FixedUpdate() => _touching = false;
    }
}
