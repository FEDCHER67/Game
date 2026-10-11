#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Vehicles;
using Unity.Profiling;
using UnityEngine;

namespace OnlyVolunteers.Police.Dev
{
    // Scripted police test (design section 6) in Map_Look_vNN_Play: OnlyVolunteers/Map/Dev/Police Chase Test enters Play,
    // runs everything at TimeScale 2 with a fixed seed and leaves Play (about 8-12 minutes). Lines: [PoliceChaseTest]
    // PASS / FAIL / INFO ..., then DONE n/n PASS. Statics Done / Passed / LastReport / Progress for MCP polling.
    //  1. Pace: RouteVanDriver drives 8 routes with nobody wanted; measured vs the bake's reference times (±20 %); the
    //     measured / model ratio is the VanPaceFactor to set (then bake again).
    //  2. Chases (16): day and night x 8 hotspot -> home pairs. Reset (heat 0, patrol cars at 0.25 of their loops, home
    //     base, night), van at the hotspot facing home, the alert at t = 0 (capture), the van drives at t = 8 s, until it
    //     is within 8 m of the door or 150 s. Dispatch, response, contact, pursuit length and how it ended (no home line
    //     since 2026-10-07: the van gets away, or the car waits at the base's safe disc), the closest any police came to
    //     the door (never inside the disc), stuck / flips.
    //  3. Lost sight (the van vanishes far away mid-chase): Search, then the evade rule within EvadeTime + 2 s.
    //  3b. Escape: the van waits for a car on its tail, then a clean, quick driver (EscapeLateral / EscapeBrake) drives to
    //     a far point: the police should fall behind and lose it (evade rule). 3c. Stop: the same start, the van brakes to
    //     a stop StopAfter s later: the police should catch up and get out (Dismount).
    //  4. Foot: an officer and a still player 20 m off: reached within 15 s, first hit <= 2 s later, three hits = one
    //     arrest event, the penalty, the player at the station. 4b: a passer-by stunned in front of a foot officer with
    //     the player next to the victim: the officer sees it himself and chases the player within 2 s.
    //  5. Performance: police code (profiler marker "Police") per frame, average over the chases.
    //  6. Witness runs (the measured table of POLICE_V1_DRAFT.md): a witness alert at bad-district and old-town hotspots,
    //     the van on autopilot (RouteVanDriver) to the nearest base and to the default team home, day and night. Every
    //     chase run (2 and 6) adds a row to Table: dispatch, response, contact, pursuit, give-up cause, seconds and metres
    //     of real driving still left to the base, closest police to the door, flips and stuck. Console errors are counted.
    public sealed class PoliceChaseTest : MonoBehaviour
    {
        public static bool Done, Passed;
        public static string LastReport = "", Progress = "", Table = "";

        public float TimeScale = 2f;
        public int Seed = 82;
        public bool ExitWhenDone;
        public bool RunPace = true, RunChases = true, RunNegative = true, RunEscape = true, RunStop = true, RunFoot = true, RunFootStun = true, RunWitness = true;
        [Tooltip("Escape / stop runs: start hotspot, how far the far point may be (straight-line m), the driver's cornering / " +
                 "braking (m/s^2; the reference driver is 5, PoliceConfig.VanFastLateral 8), and when the stop run brakes (s).")]
        public string EscapeHotspot = "BAD_CENTER";
        public float EscapeDistance = 800f, EscapeLateral = 7f, EscapeBrake = 7f, StopAfter = 12f;
        [Tooltip("Witness runs: these hotspots (bad district, old town), each to its nearest base and to the default home.")]
        public string[] WitnessHotspots = { "BAD_CENTER", "BAD_BLOCK_2", "CLOCK_SQUARE", "WITNESS_SUPERMARKET" };
        public bool WitnessDay = true, WitnessNight = true, WitnessNearest = true, WitnessHome = true;
        [Tooltip("Witness runs are repeated with the patrol cars starting at each of these fractions of their loops.")]
        public float[] WitnessLoopAlong = { 0.25f };
        [Tooltip("Patrol start (fraction of the loops) for the negative cases and the foot tests: they test the give-up rules, " +
                 "so a start where a car meets the van (0.75: the L1 car in the bad district).")]
        public float NegativeLoopAlong = 0.75f;
        [Tooltip("Log every busy car once per second of game time (state, speed, drive mode, route, gap to the van).")]
        public bool Trace;
        public float TraceInterval = 1f;
        [Tooltip("Where the player waits on foot during the van runs (plan metres): off every road (v12: the field south of B01).")]
        public Vector2 PawnWait = new(240f, 400f);
        [Tooltip("Optional: write every [Police...] line and error of the run to this file at the end.")]
        public string LogFile;

        private const string Tag = "[PoliceChaseTest]";
        private const float MaxRun = 150f, ArriveDistance = 8f;
        private static readonly (string hot, string home)[] Pairs =
        {
            ("BAD_CENTER", "B01"), ("BAD_BLOCK_2", "B01"), ("CLOCK_SQUARE", "B01"), ("WITNESS_SUPERMARKET", "B05"),
            ("WITNESS_CASINO", "B01"), ("BEACH_VALLEY_ENTRY", "B05"), ("BEACH_ENTRY", "B01"), ("P15", "B03"),
        };

        private PoliceDirector _d;
        private PoliceMapData _data;
        private PoliceConfig _c;
        private VanController _van;
        private RouteVanDriver _driver;
        private CrowdDirector _crowd;
        private readonly List<string> _lines = new();
        private int _checks, _passes;
        private ProfilerRecorder _recorder;
        private double _policeNs;
        private int _policeFrames;
        private readonly List<string> _rows = new();
        private float _nextTrace;
        private readonly List<string> _errors = new();
        private readonly StringBuilder _logAll = new();

        // One run's observations.
        private sealed class Run
        {
            public float T0, Dispatch = -1f, Response = -1f, Contact = -1f, LastGiveUp = -1f, Arrival = -1f;
            public Vector3 Scene;
            public bool DispatchParked;
            public readonly Dictionary<PoliceUnit, PoliceUnit.UnitState> StartState = new();
            public GiveUpCause Cause;
            public bool GaveUp;
            public float GiveUpRemainingM = -1f;
            // Closest to the home door of a car on a call or in a chase (and of an officer at work or a crew member);
            // patrolling / parked cars and crowd officers walking their loop only count for ClosestPatrol (info).
            public float Closest = float.PositiveInfinity, ClosestPatrol = float.PositiveInfinity;
            public bool Rechase;
            // Stuck episodes and flips of the cars that took part (left patrol or parking at some point); patrol cars on
            // their loops only count for StuckPatrol (info).
            public int Stuck, Flips, StuckPatrol;
            public readonly Dictionary<PoliceUnit, (int stuck, int flips)> Start = new();
            public readonly HashSet<PoliceUnit> Busy = new();
            public bool Searched, Dismounted;
            public float DismountAt = -1f;
            public readonly HashSet<PoliceUnit> GaveUpUnits = new();
            public readonly HashSet<PoliceUnit> Pursued = new();
        }

        private Run _run;
        private float _loopAlong = 0.25f;

        private static PoliceChaseTest _running;

        private void Awake()
        {
            // One test at a time (a repeated start command must not run a second one alongside).
            if (_running != null && _running != this)
            {
                Destroy(gameObject);
                return;
            }
            _running = this;
        }

        private void OnDestroy()
        {
            if (_running == this) _running = null;
        }

        private IEnumerator Start()
        {
            if (_running != this) yield break;
            Done = Passed = false;
            Random.InitState(Seed);
            _d = PoliceDirector.Instance;
            _van = FindAnyObjectByType<VanController>();
            _crowd = CrowdDirector.Instance;
            if (_d == null || _van == null || _d.Data == null)
            {
                Finish("no PoliceDirector / van in the scene (open Map_Look_vNN_Play built with the police)");
                yield break;
            }
            _data = _d.Data;
            _c = _d.Config;
            if (!_van.TryGetComponent(out _driver)) _driver = _van.gameObject.AddComponent<RouteVanDriver>();
            float oldScale = Time.timeScale;
            Time.timeScale = TimeScale;
            _recorder = ProfilerRecorder.StartNew(ProfilerCategory.Scripts, "Police", 1);
            PoliceEvents.PursuitEnded += OnEnded;
            Application.logMessageReceived += OnLog;
            yield return new WaitForSeconds(1f);
            Log("INFO", $"{_data.Revision}: {_d.Units.Count} cars, {_d.Officers.Count} officers, home {_d.HomeId}, data {_data.name} (plan {_data.PlanHash})");

            if (RunPace) yield return Pace();
            if (RunChases)
                foreach (bool night in new[] { false, true })
                    foreach ((string hot, string home) in Pairs)
                        yield return Chase(hot, _data.BaseIndex(home), night, "pair");
            if (RunWitness)
                foreach (float along in WitnessLoopAlong) // each start position of the patrols, a full witness set
                foreach (bool night in new[] { false, true })
                    foreach (string hot in WitnessHotspots)
                    {
                        _loopAlong = along;
                        if ((night && !WitnessNight) || (!night && !WitnessDay)) continue;
                        PoliceHotspot h = Hot(hot);
                        if (h == null)
                        {
                            Log("INFO", $"witness {hot}: not in this plan");
                            continue;
                        }
                        int nearest = NearestBase(h);
                        int home = Mathf.Max(0, _data.BaseIndex(_c.DefaultHomeBase));
                        string tag = WitnessLoopAlong.Length > 1 ? $" (patrols at {along:0.##})" : "";
                        if (WitnessNearest) yield return Chase(hot, nearest, night, "witness, nearest base" + tag);
                        if (WitnessHome && home != nearest) yield return Chase(hot, home, night, "witness, team home" + tag);
                    }
            _loopAlong = NegativeLoopAlong;
            if (RunNegative) yield return LostSight();
            if (RunEscape) yield return Escape(false);
            if (RunStop) yield return Escape(true);
            if (RunFoot) yield return Foot();
            if (RunFootStun) yield return FootStun();
            if (_policeFrames > 0)
            {
                double ms = _policeNs / _policeFrames / 1e6;
                Check(ms <= 0.3, $"performance: police code {ms:0.000} ms per frame on average ({_d.Units.Count} cars, {_d.Officers.Count} officers)");
            }
            Check(_errors.Count == 0, $"console errors during the test: {_errors.Count}" + (_errors.Count > 0 ? " (first: " + _errors[0] + ")" : ""));
            PoliceEvents.PursuitEnded -= OnEnded;
            Application.logMessageReceived -= OnLog;
            _recorder.Dispose();
            Time.timeScale = oldScale;
            _driver.Stop();
            _d.NightOverride = -1f;
            Finish(null);
        }

        private void Update()
        {
            if (_recorder.Valid && _run != null)
            {
                _policeNs += _recorder.LastValue;
                _policeFrames++;
            }
            if (_run == null || _d == null) return;
            float now = Time.time;
            if (Trace && now >= _nextTrace)
            {
                _nextTrace = now + TraceInterval;
                var sb = new StringBuilder();
                sb.Append($"{Tag} TRACE t={now - _run.T0:0} van ({_van.transform.position.x:0},{_van.transform.position.z:0}) {_van.SpeedKmh:0} km/h unseen {_d.Unseen(_d.VanSuspect, now):0.0} s");
                foreach (PoliceUnit u in _d.Units)
                {
                    if (u.State == PoliceUnit.UnitState.Parked || u.State == PoliceUnit.UnitState.Patrol) continue;
                    PoliceCarMotor m = u.Motor;
                    sb.Append($" | #{u.Index + 1} {u.State} ({m.Position2.x:0},{m.Position2.y:0}) {m.SpeedKmh:0} km/h {m.Mode} max {m.MaxSpeed * 3.6f:0} " +
                              $"route {m.Progress:0}/{m.RouteLength:0} gap {Vector3.Distance(u.transform.position, _van.transform.position):0} los {u.HasLineOfSight} stuck {m.StuckEpisodes} hops {m.Hops}{(m.Reversing ? " REV" : "")}" +
                              $"{(m.Grounded ? "" : " AIR")}{(m.PedestrianAhead ? " PED" : "")} hit [{m.LastHit}]");
                }
                Debug.Log(sb.ToString(), this);
            }
            foreach (PoliceUnit u in _d.Units)
            {
                if (_run.Dispatch < 0f && (u.State == PoliceUnit.UnitState.Respond || u.State == PoliceUnit.UnitState.Pursue))
                {
                    _run.Dispatch = now - _run.T0;
                    _run.DispatchParked = _run.StartState.TryGetValue(u, out PoliceUnit.UnitState was) && was == PoliceUnit.UnitState.Parked;
                }
                if (_run.Response < 0f && _run.Scene != Vector3.zero && Vector3.Distance(u.transform.position, _run.Scene) < 40f) _run.Response = now - _run.T0;
                if (u.State == PoliceUnit.UnitState.Pursue)
                {
                    if (_run.Contact < 0f) _run.Contact = now - _run.T0;
                    if (_run.GaveUpUnits.Contains(u)) _run.Rechase = true;
                    _run.Pursued.Add(u);
                }
                if (u.State == PoliceUnit.UnitState.Search && _run.Pursued.Contains(u)) _run.Searched = true;
                if (u.State == PoliceUnit.UnitState.Dismount)
                {
                    _run.Dismounted = true;
                    if (_run.DismountAt < 0f) _run.DismountAt = now - _run.T0;
                }
                if (u.State != PoliceUnit.UnitState.Patrol && u.State != PoliceUnit.UnitState.Parked) _run.Busy.Add(u);
                float door = _d.DoorDistance(u.transform.position);
                if (u.State == PoliceUnit.UnitState.Patrol || u.State == PoliceUnit.UnitState.Parked) _run.ClosestPatrol = Mathf.Min(_run.ClosestPatrol, door);
                else _run.Closest = Mathf.Min(_run.Closest, door);
            }
            foreach (PoliceOfficer o in _d.Officers)
            {
                if (o == null || !o.isActiveAndEnabled) continue;
                float door = _d.DoorDistance(o.transform.position);
                if (o.CrewOf != null || o.State != PoliceOfficer.OfficerState.Idle) _run.Closest = Mathf.Min(_run.Closest, door);
                else _run.ClosestPatrol = Mathf.Min(_run.ClosestPatrol, door);
            }
        }

        private void OnLog(string condition, string stackTrace, LogType type)
        {
            // Every police and test line (and every error) of the run, for LogFile: the shared console gets cleared.
            if (!string.IsNullOrEmpty(LogFile) && (type != LogType.Log || condition.StartsWith("[Police") || condition.StartsWith("[Crowd] ALERT")))
                _logAll.Append($"{Time.time:0.0} {condition}").Append('\n');
            if (type != LogType.Error && type != LogType.Exception && type != LogType.Assert) return;
            if (_errors.Count < 20) _errors.Add(condition.Length > 160 ? condition.Substring(0, 160) : condition);
            else _errors.Add("");
        }

        // The base the van reaches soonest from this hotspot (the bake's reference times).
        private int NearestBase(PoliceHotspot h)
        {
            int best = -1;
            for (int b = 0; b < _data.BaseCount && b < h.VanTime.Length; b++)
                if (h.VanTime[b] > 0f && (best < 0 || h.VanTime[b] < h.VanTime[best])) best = b;
            return Mathf.Max(0, best);
        }

        private void OnEnded(PoliceUnit unit, GiveUpCause cause, float metres)
        {
            if (_run == null) return;
            _run.GaveUp = true;
            _run.Cause = cause;
            _run.LastGiveUp = Time.time - _run.T0;
            _run.GiveUpRemainingM = _driver.Driving || _driver.Arrived ? _driver.Remaining : metres;
            _run.GaveUpUnits.Add(unit);
        }

        // ---------- Setup helpers ----------

        private PoliceHotspot Hot(string id) => _data.Hotspots.FirstOrDefault(h => h.Id == id);

        private Vector3 Ground(Vector2 p)
        {
            if (_crowd != null) return _crowd.Ground(p);
            return Physics.Raycast(new Vector3(p.x, 300f, p.y), Vector3.down, out RaycastHit hit, 600f, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore)
                ? hit.point : new Vector3(p.x, 0f, p.y);
        }

        private bool VanRoute(Vector2 from, Vector2 to, PoliceRoute route) =>
            _data.FindRoute(from, Vector2.zero, to, -1, false, 0f, 0f, route, true);

        private void PutVan(PoliceRoute route)
        {
            Vector2 a = route.Points[0], b = route.Points[Mathf.Min(1, route.Points.Count - 1)];
            float yaw = Mathf.Atan2(b.x - a.x, b.y - a.y) * Mathf.Rad2Deg;
            _driver.Stop();
            _van.ResetUpright(Ground(a) + Vector3.up * 0.6f, yaw);
        }

        private IEnumerator Reset(int home, bool night)
        {
            _run = null;
            _driver.Stop();
            _d.ResetForTest(home, night ? 1f : 0f, _loopAlong);
            if (_crowd != null) _crowd.Evening = night ? 1f : 0f;
            // The player waits on foot off every road (no stun near a van route can be blamed on him).
            GreyboxPawn pawn = _d.Pawn;
            if (pawn != null && pawn.Controlled && !_d.PawnInVan) pawn.Teleport(Ground(PawnWait) + Vector3.up * 0.1f, 0f);
            yield return new WaitForSeconds(1f);
        }

        // Every car back in its parking space and switched off (or on again; the next Reset puts the patrols out).
        private void PoliceOff(bool off)
        {
            foreach (PoliceUnit u in _d.Units)
            {
                if (off) u.ResetToStall();
                u.enabled = !off;
                if (off) u.Motor.Mode = PoliceCarMotor.DriveMode.Stop;
            }
        }

        private Run Begin(Vector3 scene = default)
        {
            var run = new Run { T0 = Time.time, Scene = scene };
            foreach (PoliceUnit u in _d.Units)
            {
                run.StartState[u] = u.State;
                run.Start[u] = (u.Motor.StuckEpisodes, u.Motor.Flips);
            }
            _run = run;
            return run;
        }

        private void End(Run run)
        {
            foreach (PoliceUnit u in _d.Units)
            {
                if (!run.Start.TryGetValue(u, out (int stuck, int flips) at)) continue;
                int stuck = u.Motor.StuckEpisodes - at.stuck, flips = u.Motor.Flips - at.flips;
                if (run.Busy.Contains(u))
                {
                    run.Stuck += stuck;
                    run.Flips += flips;
                }
                else
                {
                    run.StuckPatrol += stuck;
                    run.Flips += flips; // a flip is a flip, patrol or not
                }
            }
            _run = null;
        }

        private void Alert(Vector3 where)
        {
            if (_crowd != null && _crowd.Map != null) _crowd.RaiseAlert(Mathf.Max(0, _crowd.DistrictAt(where)), null, NpcIncident.Captured, where, "test");
            else
            {
                _d.MarkWanted(_d.VanSuspect, where);
                _d.Dispatch(where, 1, true, "test");
            }
        }

        // Drives the prepared route from t = 8 s; ends on arrival, when all is over, or after maxTime.
        private IEnumerator DriveRun(Run run, PoliceRoute route, float maxTime, System.Func<Run, bool> stop = null)
        {
            bool started = false;
            while (Time.time - run.T0 < maxTime)
            {
                float t = Time.time - run.T0;
                if (!started && t >= _c.ModelVanLeavesAt - _c.ModelAlertAt)
                {
                    started = true;
                    _driver.Drive(route.Points, route.Widths);
                }
                if (started && _driver.Arrived && run.Arrival < 0f) run.Arrival = _driver.ArrivedAt - run.T0;
                if (run.Arrival >= 0f && t > run.Arrival + 3f) break;
                if (stop != null && stop(run)) break;
                yield return null;
            }
        }

        // ---------- 1. Pace ----------

        private IEnumerator Pace()
        {
            var ratios = new List<float>();
            var route = new PoliceRoute();
            foreach ((string hot, string home) in Pairs)
            {
                PoliceHotspot h = Hot(hot);
                int b = _data.BaseIndex(home);
                if (h == null || b < 0 || !VanRoute(_data.Nodes[h.Node], _data.BaseDoors[b], route))
                {
                    Log("INFO", $"pace {hot}->{home}: not in this plan");
                    continue;
                }
                Progress = $"pace {hot}->{home}";
                yield return Reset(b, false);
                PoliceOff(true); // design 6.2: the pace without police (a blind test van would ram the patrol cars)
                PutVan(route);
                yield return new WaitForSeconds(1f);
                Run run = Begin();
                run.T0 = Time.time - (_c.ModelVanLeavesAt - _c.ModelAlertAt); // drive at once
                yield return DriveRun(run, route, MaxRun);
                End(run);
                float driven = run.Arrival >= 0f ? run.Arrival - (_c.ModelVanLeavesAt - _c.ModelAlertAt) : float.NaN;
                float model = h.VanTime[b];
                float ratio = driven / Mathf.Max(1f, model);
                if (!float.IsNaN(driven)) ratios.Add(ratio);
                Check(!float.IsNaN(driven) && Mathf.Abs(ratio - 1f) <= 0.2f, $"pace {h.Name}->{home}: driven {driven:0.0} s, model {model:0.0} s (x{ratio:0.00})");
            }
            PoliceOff(false);
            if (ratios.Count > 0)
            {
                ratios.Sort();
                float median = ratios[ratios.Count / 2];
                Log("INFO", $"pace: median measured / model {median:0.00}; set PoliceConfig.VanPaceFactor = {_data.VanPaceFactor * median:0.00} and bake again if it is off by more than 0.1");
            }
        }

        // ---------- 2. Chases ----------

        private IEnumerator Chase(string hot, int b, bool night, string kind)
        {
            PoliceHotspot h = Hot(hot);
            string home = b >= 0 && b < _data.BaseCount ? _data.BaseIds[b] : "?";
            var route = new PoliceRoute();
            string name = $"{kind}: {(night ? "night" : "day")} {hot}->{home}";
            if (h == null || b < 0 || !VanRoute(_data.Nodes[h.Node], _data.BaseDoors[b], route))
            {
                Log("INFO", $"{name}: not in this plan");
                yield break;
            }
            Progress = name;
            yield return Reset(b, night);
            PutVan(route);
            yield return new WaitForSeconds(1f);
            Vector3 scene = Ground(_data.Nodes[h.Node]) + Vector3.up;
            Run run = Begin(scene);
            Alert(scene);
            yield return DriveRun(run, route, MaxRun);
            End(run);

            float predResp = night ? h.RespNightP90 : h.RespDayP90;
            // Dispatch: radio (+ boarding for the parked reserve).
            float dispatchLimit = run.DispatchParked ? (night ? 5f : 6.5f) : (night ? 2f : 3.5f);
            Check(run.Dispatch >= 0f && run.Dispatch <= dispatchLimit,
                  $"{name}: dispatch {run.Dispatch:0.0} s ({(run.DispatchParked ? "parked reserve" : "patrol car")}, <= {dispatchLimit} s)");
            // Response: first car at the scene or in contact.
            float resp = run.Contact >= 0f ? run.Contact : run.Response;
            float respLimit = h.Core ? 30f : night ? 30f : 35f;
            Check(resp >= 0f && resp <= Mathf.Max(respLimit, 1.3f * predResp), $"{name}: response {resp:0.0} s (limit {respLimit:0}, predicted p90 {predResp:0})");
            float pursuit = run.Contact >= 0f && run.LastGiveUp >= 0f ? run.LastGiveUp - run.Contact : 0f;
            // No home line any more: a chase toward home ends by the evade rule, at the base (the car waits at the safe
            // disc's edge: Base), or the car is still on the van's tail at the door. All fine; recorded, not judged.
            Log("INFO", $"{name}: contact {F(run.Contact)} s, pursuit {(run.Contact >= 0f ? F(pursuit, "0") : "-")} s, ended " +
                        $"{(run.GaveUp ? run.Cause.ToString() : "-")}, dismounted {run.Dismounted}, van arrival {F(run.Arrival, "0")} s");
            Check(run.Closest >= _data.SafeRadius && !run.Rechase && run.Flips == 0 && run.Stuck <= 1,
                  $"{name}: safety: closest to the door {run.Closest:0} m (patrol, info: {run.ClosestPatrol:0} m), re-chase {run.Rechase}, flips {run.Flips}, stuck {run.Stuck} (patrol cars, info: {run.StuckPatrol})");
            float leftS = run.Arrival >= 0f && run.LastGiveUp >= 0f ? run.Arrival - run.LastGiveUp : float.NaN;
            _rows.Add($"| {kind} | {(night ? "night" : "day")} | {h.Name} -> {home} | {F(h.VanTime[b], "0")} | {F(run.Dispatch)} | {F(resp)} | {F(run.Contact)} | " +
                      $"{(run.Contact >= 0f ? F(pursuit, "0") : "no chase")} | {(run.GaveUp ? run.Cause.ToString() : "-")} | {F(leftS)} | {(run.GaveUp ? F(run.GiveUpRemainingM, "0") : "-")} | " +
                      $"{F(run.Arrival, "0")} | {F(run.Closest, "0")} | {run.Flips} | {run.Stuck} |");
        }

        private static string F(float v, string fmt = "0.0") =>
            v >= 0f && !float.IsNaN(v) && !float.IsInfinity(v) ? v.ToString(fmt, System.Globalization.CultureInfo.InvariantCulture) : "-";

        // ---------- 3. Negative cases ----------

        private IEnumerator LostSight()
        {
            PoliceHotspot h = Hot("BAD_CENTER");
            int b = _data.BaseIndex("B01");
            var route = new PoliceRoute();
            if (h == null || b < 0 || !VanRoute(_data.Nodes[h.Node], _data.BaseDoors[b], route)) yield break;
            Progress = "lost sight";
            yield return Reset(b, false);
            PutVan(route);
            yield return new WaitForSeconds(1f);
            Run run = Begin();
            Alert(Ground(_data.Nodes[h.Node]) + Vector3.up);
            float vanished = -1f;
            yield return DriveRun(run, route, MaxRun, r =>
            {
                if (vanished < 0f && r.Contact >= 0f && Time.time - r.T0 > r.Contact + 3f)
                {
                    // The van is gone: far from every patrol loop and every police car, away from home.
                    Vector2 hide = HidingPlace(b);
                    _driver.Stop();
                    _van.ResetUpright(Ground(hide) + Vector3.up * 0.6f, 0f);
                    vanished = Time.time - r.T0;
                }
                return vanished >= 0f && (Time.time - r.T0 > vanished + 45f || _d.Units.All(u => !u.IsBusy));
            });
            End(run);
            float limit = _c.EvadeTime.Day + 2f;
            float took = run.LastGiveUp - vanished;
            Check(vanished >= 0f && run.GaveUp && run.Cause == GiveUpCause.Evaded && took <= limit,
                  $"lost sight: searched {run.Searched}, gave up ({run.Cause}) {took:0.0} s after the van vanished (<= {limit:0})");
        }

        // A road node far from every loop and car, 300 m and more from the home door: the van "hides" there.
        private Vector2 HidingPlace(int home)
        {
            var loopPoints = new List<Vector2>();
            var r = new PoliceRoute();
            for (int l = 0; l < _data.Loops.Length; l++)
            {
                _data.LoopRoute(l, r);
                loopPoints.AddRange(r.Points);
            }
            Vector2 best = _data.Nodes[0];
            float bestScore = float.MinValue;
            for (int n = 0; n < _data.NodeCount; n += 3)
            {
                Vector2 p = _data.Nodes[n];
                if (_data.DoorDistance(home, p) < 300f) continue;
                float score = float.MaxValue;
                foreach (Vector2 q in loopPoints) score = Mathf.Min(score, (q - p).sqrMagnitude);
                foreach (PoliceUnit u in _d.Units) score = Mathf.Min(score, (u.Motor.Position2 - p).sqrMagnitude);
                if (score > bestScore)
                {
                    bestScore = score;
                    best = p;
                }
            }
            return best;
        }

        // ---------- 3b / 3c. Escape and stop ----------

        // A far point for the van from 'from': at most EscapeDistance away (straight line), the farthest such road node whose
        // van route keeps 30 m off the home base's safe disc (the base rule must not end the run) and away from every base.
        private bool FarRoute(Vector2 from, int home, PoliceRoute route)
        {
            var candidates = new List<(float d, int n)>();
            for (int n = 0; n < _data.NodeCount; n++)
            {
                Vector2 p = _data.Nodes[n];
                float d = Vector2.Distance(p, from);
                if (d > EscapeDistance || d < EscapeDistance * 0.4f) continue;
                bool nearBase = false;
                for (int b = 0; b < _data.BaseCount; b++)
                    if (_data.DoorDistance(b, p) < _data.SafeRadius + 100f) nearBase = true;
                if (!nearBase) candidates.Add((d, n));
            }
            candidates.Sort((a, b) => b.d.CompareTo(a.d));
            for (int k = 0; k < candidates.Count && k < 40; k++)
            {
                if (!VanRoute(from, _data.Nodes[candidates[k].n], route)) continue;
                bool clear = true;
                foreach (Vector2 q in route.Points)
                    if (_data.DoorDistance(home, q) < _data.SafeRadius + 30f) clear = false;
                if (clear) return true;
            }
            return false;
        }

        // Distance from the van to the nearest car on the job (responding, chasing, searching, out); +inf when none.
        private float NearestBusyGap()
        {
            float best = float.PositiveInfinity;
            foreach (PoliceUnit u in _d.Units)
                if (u.IsBusy) best = Mathf.Min(best, Vector3.Distance(u.transform.position, _van.transform.position));
            return best;
        }

        // 3b (stop = false): the van waits at the hotspot until a car is on its tail (pursuit) or 40 s, then drives cleanly
        // and quickly (EscapeLateral / EscapeBrake) to a far point: expect the police to fall behind and lose it (Evaded).
        // 3c (stop = true): the same, but StopAfter s after leaving the van brakes hard to a stop and stands: expect the
        // police to catch up and get out (Dismount). Gaps to the nearest busy car every 5 s are logged.
        private IEnumerator Escape(bool stop)
        {
            string name = stop ? "stop" : "escape";
            PoliceHotspot h = Hot(EscapeHotspot);
            int home = Mathf.Max(0, _data.BaseIndex(_c.DefaultHomeBase));
            var route = new PoliceRoute();
            if (h == null || !FarRoute(_data.Nodes[h.Node], home, route))
            {
                Log("INFO", $"{name}: no hotspot {EscapeHotspot} / far route in this plan");
                yield break;
            }
            Progress = name;
            yield return Reset(home, false);
            PutVan(route);
            yield return new WaitForSeconds(1f);
            Vector3 scene = Ground(route.Points[0]) + Vector3.up;
            Run run = Begin(scene);
            Alert(scene);
            float lateral = _driver.LateralAccel, brake = _driver.Brake;
            _driver.LateralAccel = EscapeLateral;
            _driver.Brake = EscapeBrake;
            float left = -1f, evaded = -1f, stoppedAt = -1f, maxGap = 0f, minGapAfterStop = float.PositiveInfinity, nextGap = 0f;
            var gaps = new StringBuilder();
            while (Time.time - run.T0 < 160f)
            {
                float t = Time.time - run.T0;
                if (left < 0f && (run.Contact >= 0f || t > 40f))
                {
                    left = t;
                    _driver.Drive(route.Points, route.Widths);
                }
                if (left >= 0f)
                {
                    float gap = NearestBusyGap();
                    if (!float.IsInfinity(gap)) maxGap = Mathf.Max(maxGap, gap);
                    if (t >= nextGap)
                    {
                        nextGap = t + 5f;
                        gaps.Append($" {t - left:0}s:{(float.IsInfinity(gap) ? "-" : gap.ToString("0"))}");
                    }
                    if (stop && t - left >= StopAfter)
                    {
                        // Brake hard to a stop, then stand with the handbrake (the driver is off).
                        if (stoppedAt < 0f)
                        {
                            stoppedAt = t;
                            _driver.Stop();
                        }
                        float v = _van.SpeedKmh;
                        _van.Steer = 0f;
                        _van.Throttle = v > 3f ? -1f : 0f;
                        _van.Handbrake = v <= 3f;
                        if (!float.IsInfinity(gap)) minGapAfterStop = Mathf.Min(minGapAfterStop, gap);
                    }
                }
                if (evaded < 0f && run.GaveUp && run.Cause == GiveUpCause.Evaded) evaded = t;
                if (!stop && evaded >= 0f && t > evaded + 3f) break;
                if (!stop && _driver.Arrived && t > _driver.ArrivedAt - run.T0 + 25f) break;
                if (stop && run.DismountAt >= 0f && t > run.DismountAt + 5f) break;
                if (stop && stoppedAt >= 0f && t > stoppedAt + 45f) break;
                yield return null;
            }
            End(run);
            _driver.Stop();
            _driver.LateralAccel = lateral;
            _driver.Brake = brake;
            string common = $"contact {F(run.Contact)} s, van left {F(left)} s, route {route.Length():0} m, gap to the nearest busy car every 5 s after leaving:{gaps}";
            if (!stop)
                Check(left >= 0f && evaded >= 0f && run.Flips == 0,
                      $"escape (driver {EscapeLateral:0.#}/{EscapeBrake:0.#} m/s^2, police top {_d.ChaseTopSpeed * 3.6f:0} km/h vs van {_van.MaxSpeedKmh:0}): " +
                      $"lost it {(evaded >= 0f ? F(evaded - left) + " s after the van left" : "never")}, max gap {maxGap:0} m, van arrival {F(run.Arrival, "0")} s, " +
                      $"dismounted {run.Dismounted}, flips {run.Flips}, stuck {run.Stuck}; {common}");
            else
                Check(stoppedAt >= 0f && run.DismountAt >= stoppedAt && run.Flips == 0,
                      $"stop (after {StopAfter:0} s): crew out {(run.DismountAt >= 0f ? F(run.DismountAt - stoppedAt) + " s after the van braked" : "never")}, " +
                      $"closest car after the stop {(float.IsInfinity(minGapAfterStop) ? "-" : minGapAfterStop.ToString("0"))} m, ended {(run.GaveUp ? run.Cause.ToString() : "-")}, " +
                      $"flips {run.Flips}; {common}");
        }

        // ---------- 4. Foot ----------
        // ---------- 4. Foot ----------

        private IEnumerator Foot()
        {
            Progress = "foot";
            yield return Reset(Mathf.Max(0, _data.BaseIndex(_c.DefaultHomeBase)), false);
            PoliceOfficer officer = null;
            float wait = 0f;
            while (officer == null && wait < 20f)
            {
                officer = _d.Officers.FirstOrDefault(o => o != null && o.isActiveAndEnabled && o.CrewOf == null && !o.Down);
                wait += 0.5f;
                yield return new WaitForSeconds(0.5f);
            }
            GreyboxPawn pawn = _d.Pawn;
            if (officer == null || pawn == null || !pawn.Controlled)
            {
                Check(false, "foot: no free crowd officer or no player on foot");
                yield break;
            }
            // The player 20 m from him along the walk graph.
            Vector3 op = officer.transform.position;
            Vector2 spot = PoliceDirector.Plan(op + officer.transform.forward * 20f);
            if (_crowd != null && _crowd.Map != null)
            {
                int node = _crowd.Map.Graph.Nearest(spot, CrowdProfile.Town);
                if (node >= 0) spot = _crowd.Map.Graph.Nodes[node];
            }
            pawn.Teleport(Ground(spot) + Vector3.up * 0.1f, 0f);
            yield return new WaitForSeconds(0.5f);
            int cashBefore = Cash(pawn);
            int arrests = 0;
            void OnArrest(GreyboxPawn p, PoliceOfficer o) => arrests++;
            PoliceEvents.ArrestRequested += OnArrest;
            _d.MarkWanted(_d.PawnSuspect, pawn.Position);
            officer.Aggro(_d.PawnSuspect, pawn.Position);
            float t0 = Time.time, reached = -1f, firstHit = -1f;
            int hits0 = officer.Hits;
            float nextNote = t0 + 3f;
            while (Time.time - t0 < 45f && arrests == 0)
            {
                if (reached < 0f && Vector3.Distance(officer.transform.position, pawn.Position) <= _c.BeatReach + 0.2f) reached = Time.time - t0;
                if (firstHit < 0f && officer.Hits > hits0) firstHit = Time.time - t0;
                if (Trace && Time.time >= nextNote)
                {
                    nextNote = Time.time + 3f;
                    Debug.Log($"{Tag} TRACE foot t={Time.time - t0:0} {officer.name} {officer.State} at ({officer.transform.position.x:0},{officer.transform.position.z:0}) " +
                              $"player ({pawn.Position.x:0},{pawn.Position.z:0}) gap {Vector3.Distance(officer.transform.position, pawn.Position):0.0} wanted {_d.PawnSuspect.Wanted} hits {officer.Hits - hits0}", this);
                }
                yield return null;
            }
            yield return new WaitForSeconds(2f);
            PoliceEvents.ArrestRequested -= OnArrest;
            int cashAfter = Cash(pawn);
            float atStation = Vector2.Distance(PoliceDirector.Plan(pawn.Position), _data.Respawn);
            Check(reached >= 0f && reached <= 15f, $"foot: officer reached the player in {reached:0.0} s (<= 15)");
            Check(firstHit >= 0f && reached >= 0f && firstHit - reached <= 2f + 1e-3f, $"foot: first hit {firstHit - reached:0.0} s after reaching (<= 2)");
            Check(arrests == 1, $"foot: arrest events {arrests} (exactly 1)");
            int expected = cashBefore - cashBefore * _c.ArrestCashPercent / 100;
            Check(cashAfter <= expected, $"foot: cash {cashBefore} -> {cashAfter} (-{_c.ArrestCashPercent} %)");
            Check(atStation < 8f, $"foot: player {atStation:0.0} m from the station respawn");
        }

        private static int Cash(GreyboxPawn pawn) =>
            pawn != null && pawn.Body != null && pawn.Body.TryGetComponent(out LocalInventory inv) && inv.Model != null ? inv.Model.Cash : 0;

        // ---------- 4b. Foot: a stun in an officer's view ----------

        // A passer-by is knocked down 8 m in front of a crowd foot officer with the player standing next to the victim:
        // the officer must see it himself (no witness needed), go after the player (Alerted, then Chase) and the player
        // must be wanted. The player then stands still; the officer reaching him is enough here (Foot() checks the hits).
        private IEnumerator FootStun()
        {
            Progress = "foot stun";
            yield return Reset(Mathf.Max(0, _data.BaseIndex(_c.DefaultHomeBase)), false);
            PoliceOfficer officer = null;
            float wait = 0f;
            while (officer == null && wait < 20f)
            {
                officer = _d.Officers.FirstOrDefault(o => o != null && o.isActiveAndEnabled && o.CrewOf == null && !o.Down &&
                                                          o.State == PoliceOfficer.OfficerState.Idle);
                wait += 0.5f;
                yield return new WaitForSeconds(0.5f);
            }
            GreyboxPawn pawn = _d.Pawn;
            GreyboxNpc victim = GreyboxNpc.All.FirstOrDefault(n => n != null && n.State == NpcState.Free && !PoliceOfficer.IsOfficer(n) &&
                                                                   n.isActiveAndEnabled && n.GetComponent<CrowdWalker>() != null);
            if (officer == null || pawn == null || !pawn.Controlled || victim == null)
            {
                Check(false, "foot stun: no free crowd officer, passer-by or player on foot");
                yield break;
            }
            Transform ot = officer.transform;
            Vector3 fwd = Vector3.ProjectOnPlane(ot.forward, Vector3.up).normalized;
            Vector3 spot = Ground(PoliceDirector.Plan(ot.position + fwd * 8f));
            var cc = victim.GetComponent<CharacterController>();
            if (cc != null) cc.enabled = false;
            victim.transform.position = spot + Vector3.up * 0.05f;
            if (cc != null) cc.enabled = true;
            Vector3 side = Vector3.Cross(Vector3.up, fwd);
            pawn.Teleport(Ground(PoliceDirector.Plan(spot + side * 1.5f)) + Vector3.up * 0.1f, Quaternion.LookRotation(-side).eulerAngles.y);
            yield return null;
            bool saw = officer.Sees(victim.Center);
            float t0 = Time.time;
            victim.KnockOver(fwd * 3f + Vector3.up * 2f);
            float chasing = -1f, reached = -1f;
            while (Time.time - t0 < 15f)
            {
                if (chasing < 0f && officer.IsAfter(_d.PawnSuspect) &&
                    (officer.State == PoliceOfficer.OfficerState.Chase || officer.State == PoliceOfficer.OfficerState.Beat))
                    chasing = Time.time - t0;
                if (reached < 0f && Vector3.Distance(officer.transform.position, pawn.Position) <= _c.BeatReach + 0.2f) reached = Time.time - t0;
                if (reached >= 0f) break;
                yield return null;
            }
            Check(saw && _d.PawnSuspect.Wanted && chasing >= 0f && chasing <= 2f,
                  $"foot stun: officer saw it {saw}, player wanted {_d.PawnSuspect.Wanted}, chasing after {chasing:0.0} s (<= 2), reached after {reached:0.0} s");
            _d.ResetForTest(Mathf.Max(0, _data.BaseIndex(_c.DefaultHomeBase)), 0f, 0.25f);
            yield return new WaitForSeconds(1f);
        }

        // ---------- Reporting ----------

        private void Check(bool ok, string what)
        {
            _checks++;
            if (ok) _passes++;
            Log(ok ? "PASS" : "FAIL", what);
        }

        private void Log(string kind, string what)
        {
            string line = $"{Tag} {kind} {what}";
            _lines.Add(line);
            if (kind == "FAIL") Debug.LogWarning(line, this);
            else Debug.Log(line, this);
        }

        private void Finish(string error)
        {
            if (error != null) Log("FAIL", error);
            Passed = error == null && _passes == _checks;
            string done = $"{Tag} DONE {_passes}/{_checks} PASS";
            var table = new StringBuilder();
            if (_rows.Count > 0)
            {
                table.AppendLine("| Run | Time | Hotspot -> base | Van model s | Dispatch s | Response s | Contact s | Pursuit s | Gave up | Left s | Left m | Arrival s | Closest m | Flips | Stuck |");
                table.AppendLine("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
                foreach (string row in _rows) table.AppendLine(row);
                Debug.Log($"{Tag} TABLE\n{table}", this);
            }
            Table = table.ToString();
            Debug.Log(done, this);
            var sb = new StringBuilder();
            foreach (string l in _lines) sb.AppendLine(l);
            sb.AppendLine(done);
            LastReport = sb.ToString();
            Progress = "done";
            if (!string.IsNullOrEmpty(LogFile))
            {
                try { System.IO.File.WriteAllText(LogFile, _logAll.Append('\n').Append(LastReport).Append('\n').Append(Table).ToString()); }
                catch (System.Exception e) { Debug.LogWarning($"{Tag} could not write {LogFile}: {e.Message}"); }
            }
            Done = true;
#if UNITY_EDITOR
            if (ExitWhenDone) UnityEditor.EditorApplication.isPlaying = false;
#endif
        }
    }
}
#endif
