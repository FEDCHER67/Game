using System.Collections.Generic;
using System.Text;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // The police of one map scene, offline (docs/drafts/POLICE_V1_DRAFT.md). Canon 72-82: police = movement and fun, not
    // the boss; as simple as possible: a cop who sees obvious crap aggroes, a witness report sends whoever gets there first.
    // - Suspects: the van and the player on foot, each with a wanted flag, the last known position and when it was seen.
    //   The flag clears WantedClearsAfter (60 s) after nobody is after it any more (canon 82: it passes quickly).
    // - Offenses: GreyboxNpc.Incident (a stun, a capture) seen by a car or an officer, hitting a cop, ramming a police car,
    //   dragging a body (checked every 0.5 s). Witness reports come as CrowdDirector.AlertRaised.
    // - Dispatch: one Dijkstra per alert over the baked edge times; ETA = radio delay + boarding (parked) + road time; the
    //   fastest free cars go (1, 2 at level 2+ or heat 60+, +1 at night, at most 2 by day / 3 at night). A capture or the
    //   van near the scene gives them the van's live position for TipWindow seconds. District presence (PoliceConfig.Presence,
    //   Fedya 2026-10-07): the alley district gets a car for a witness report only now and then and late, old town at once
    //   and one car more; patrol loops keep out of low-presence districts.
    // - Heat: hidden, per crowd district, 0-100, decays 1 point per 8 s; it moves patrols, speeds the radio, adds cars
    //   and foot officers, allows the rare shot. Night is one knob: CrowdDirector.Evening (F12).
    // - Pursuit (Fedya 2026-10-07, GTA-like): no give-up line near the base. Balance: once a second the cars get their top
    //   speed, acceleration, grip and brakes from a reference van (upgrade levels Engine 1 / Brakes 3 / Handling 3 by
    //   default) x the PoliceConfig ratios, a little above 1: a stock van needs upgrades and good driving to get away, Engine
    //   2-3 wins on the straights. Evade rule: a chased suspect nobody has seen for EvadeTime
    //   and more than EvadeDistance from every car and busy officer is lost: every car after it gives up (Evaded) and the
    //   wanted flag clears WantedClearsAfterEvade later.
    // - Home base: B01 until base ownership exists; Shift + backquote cycles it (tests). Its safe disc (canon 76): police
    //   never enter it; a car that followed the suspect there waits at the edge BaseWait s, then leaves.
    // - Dev HUD (editor / development builds): backquote.
    [DefaultExecutionOrder(-50)]
    public sealed class PoliceDirector : MonoBehaviour
    {
        public PoliceConfig Config;
        public PoliceMapData Data;
        [Tooltip("Arrest respawn (canon 80): in front of the station door, facing out.")]
        public Transform Respawn;
        [Tooltip("-1 = follow CrowdDirector.Evening; 0..1 = force (tests).")]
        public float NightOverride = -1f;
        public KeyCode HudKey = KeyCode.BackQuote;
        [Tooltip("Dev HUD (editor / development builds); backquote toggles it in Play.")]
        public bool ShowHud;
        [SerializeField, UnityEngine.Serialization.FormerlySerializedAs("Log")] private bool _log = true;

        /// <summary>[Police] console lines: editor and development builds only.</summary>
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public bool Log => _log;
#else
        public bool Log => false;
#endif

        public sealed class Suspect
        {
            public readonly string Name;
            public bool Wanted;
            /// <summary>A car had it in sight in a pursuit since it became wanted (the evade rule only ends a real chase).</summary>
            public bool Chased;
            public Vector3 LastKnown, Velocity;
            public float LastSeen = -999f, ClearAt;
            public Suspect(string name) => Name = name;
            public float SinceSeen => Time.time - LastSeen;
        }

        private struct Incident
        {
            public Vector3 Where;
            public float Time;
            public NpcIncident Kind;
            public Suspect Attacker;
            public bool Heated;
        }

        public static PoliceDirector Instance { get; private set; }
        // All police code per frame (director, cars, officers) under one profiler marker: tests read it with a ProfilerRecorder.
        public static readonly Unity.Profiling.ProfilerMarker Marker = new("Police");
        public readonly List<PoliceUnit> Units = new();
        public readonly List<PoliceOfficer> Officers = new();
        public readonly Suspect VanSuspect = new("бусик"), PawnSuspect = new("игрок");
        public int HomeBase { get; set; }
        public float[] Heat { get; private set; } = new float[1];
        public CrowdDirector Crowd { get; private set; }
        public VanController Van { get; private set; }
        public Rigidbody VanBody { get; private set; }
        public GreyboxPawn Pawn { get; private set; }
        public float TipUntil { get; private set; }
        public bool Tip => Time.time < TipUntil;
        public string LastGiveUp { get; private set; } = "";
        /// <summary>Chase top speed of the cars (m/s): the reference van's top speed (PoliceConfig.RefEngineLevel) x TopSpeedRatio.</summary>
        public float ChaseTopSpeed { get; private set; } = 27.8f;
        /// <summary>The van's top speed without upgrades (km/h); 0 without a van.</summary>
        public float StockVanTopSpeedKmh { get; private set; }
        /// <summary>The reference van (PoliceConfig.Ref*Level) and the police car balanced against it (valid with a van).</summary>
        public PoliceBalance Balance { get; private set; }
        /// <summary>The players' van at its current upgrade levels, by the same rule as the reference (valid with a van).</summary>
        public PoliceBalance CurrentVan { get; private set; }

        private GreyboxVanSeat _seat;
        private VanUpgrades _upgrades;
        private float _nextBalance;
        private GreyboxCargoRider _rider;
        private readonly List<Incident> _incidents = new();
        private static readonly List<(Vector3 where, float time)> PoliceKnocks = new();
        private readonly Dictionary<GreyboxNpc, float> _dragNoted = new();
        private float _nextDrag, _nextScan, _lastGiveUpUntil, _nextPawnLookup, _nextHud;
        private string _hudText = "";
        private readonly GUIContent _hudContent = new();
        private readonly List<(string text, float until)> _hints = new();
        private GUIStyle _hudStyle, _hintStyle;
        private readonly StringBuilder _sb = new();
        private readonly List<PoliceUnit> _candidates = new();

        public float Night => NightOverride >= 0f ? Mathf.Clamp01(NightOverride) : Crowd != null ? Crowd.Evening : 0f;
        public string HomeId => Data != null && HomeBase >= 0 && HomeBase < Data.BaseCount ? Data.BaseIds[HomeBase] : "?";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Instance = null;
            PoliceKnocks.Clear();
        }

        private void Awake()
        {
            Instance = this;
            if (Config == null || Data == null || Data.NodeCount == 0)
            {
                Debug.LogError("[Police] PoliceDirector needs a PoliceConfig and a baked PoliceMapData (OnlyVolunteers/Map/Police/Bake Police Data); police off.", this);
                enabled = false;
                return;
            }
            HomeBase = Mathf.Max(0, Data.BaseIndex(Config.DefaultHomeBase));
            ChaseTopSpeed = PoliceConfig.Kmh(Config.TopSpeedKmh);
        }

        private void OnEnable()
        {
            CrowdDirector.AlertRaised += OnAlert;
            GreyboxNpc.Incident += OnIncident;
            PoliceEvents.ArrestRequested += OnArrest;
            PoliceEvents.PursuitEnded += OnPursuitEnded;
        }

        private void OnDisable()
        {
            CrowdDirector.AlertRaised -= OnAlert;
            GreyboxNpc.Incident -= OnIncident;
            PoliceEvents.ArrestRequested -= OnArrest;
            PoliceEvents.PursuitEnded -= OnPursuitEnded;
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        private void Start()
        {
            Crowd = CrowdDirector.Instance != null ? CrowdDirector.Instance : FindAnyObjectByType<CrowdDirector>();
            Van = FindAnyObjectByType<VanController>();
            if (Van != null)
            {
                VanBody = Van.GetComponent<Rigidbody>();
                _seat = Van.GetComponent<GreyboxVanSeat>();
                _upgrades = Van.GetComponent<VanUpgrades>();
            }
            Pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            int districts = Crowd != null && Crowd.Map != null ? Crowd.Map.Districts.Count : 1;
            Heat = new float[districts];
            ApplyHeatFloors();
            UpdateBalance();
        }

        // ---------- Balance against the van ----------

        // The cars' chase numbers (Fedya 2026-10-07): a REFERENCE van at upgrade levels PoliceConfig.RefEngine/RefBrakes/
        // RefHandlingLevel (default 1/3/3) x the PoliceConfig ratios (a little above 1), whatever the players' van has: a stock
        // van cannot simply outrun the police, Engine 2-3 wins on the straights. Top speed, full throttle a(v) (the bake's van
        // model: A = 0.9 torque / (wheel radius x mass), k = its damping), lateral grip and braking (a clean, fast driver's
        // cornering / braking x the Handling / Brakes level's grip steps), all by PoliceConfig.VanAt with the van's own
        // VanUpgradeConfig. The stock torque / top speed are the van's current values with its engine level taken back out
        // (VanUpgrades applies stock x TorqueMultiplier and stock + MaxSpeedBonusKmh). Without a van the cars keep their own
        // numbers and TopSpeedKmh. Public: tests call it after changing the van's levels.
        public void UpdateBalance()
        {
            if (Van == null)
            {
                StockVanTopSpeedKmh = 0f;
                ChaseTopSpeed = PoliceConfig.Kmh(Config.TopSpeedKmh);
                return;
            }
            float torque = Van.MotorTorque, top = Van.MaxSpeedKmh;
            VanUpgradeConfig steps = _upgrades != null ? _upgrades.Config : null;
            int engineLevel = _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Engine) : 0;
            if (_upgrades != null)
            {
                VanEngineLevel engine = VanUpgradeConfig.EngineAt(steps, engineLevel);
                torque /= Mathf.Max(0.01f, engine.TorqueMultiplier);
                top -= engine.MaxSpeedBonusKmh;
            }
            StockVanTopSpeedKmh = top;
            float radius = Van.Front != null && Van.Front.Left != null ? Van.Front.Left.radius : 0.37f;
            float mass = VanBody != null ? VanBody.mass : 1800f;
            float damping = VanBody != null ? VanBody.linearDamping : 0.02f;
            PoliceBalance b = Config.Balance(torque, top, radius, mass, damping, steps);
            Balance = b;
            CurrentVan = Config.VanAt(torque, top, radius, mass, damping, steps, engineLevel,
                _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Brakes) : 0,
                _upgrades != null ? _upgrades.GetLevel(VanUpgradeCategory.Handling) : 0);
            ChaseTopSpeed = PoliceConfig.Kmh(b.TopKmh);
            foreach (PoliceUnit u in Units)
                if (u != null && u.Motor != null) u.Motor.SetPerformance(b.A, b.K, b.Lateral, b.Brake);
        }

        /// <summary>One line: the van at these levels vs the police (km/h, A m/s^2, cornering, braking m/s^2).</summary>
        public static string BalanceLine(PoliceBalance van, PoliceBalance police) =>
            $"van {van.Levels}: {van.VanTopKmh:0} km/h, A {van.VanA:0.00}, grip {van.VanLateral:0.0}, brake {van.VanBrake:0.0} | " +
            $"police (ref {police.Levels}): {police.TopKmh:0.0} km/h, A {police.A:0.00}, grip {police.Lateral:0.0}, brake {police.Brake:0.0}";

        // ---------- District presence ----------

        /// <summary>Crowd district id at a world point (null without a crowd map).</summary>
        public string DistrictId(Vector3 world)
        {
            if (Crowd == null || Crowd.Map == null) return null;
            int d = Crowd.DistrictAt(world);
            return d >= 0 && d < Crowd.Map.Districts.Count ? Crowd.Map.Districts[d].Id : null;
        }

        /// <summary>The PoliceConfig.Presence row of the district at a world point.</summary>
        public PolicePresenceDef PresenceAt(Vector3 world) => Config.PresenceOf(DistrictId(world));

        // ---------- Evade rule ----------

        /// <summary>Seconds since the police last knew where the suspect was: a sighting, or the van tip while it runs.</summary>
        public float Unseen(Suspect s, float now)
        {
            float known = s.LastSeen;
            if (s == VanSuspect) known = Mathf.Max(known, Mathf.Min(TipUntil, now));
            return now - known;
        }

        /// <summary>Where the suspect really is (the evade and base rules are game rules, not what the police know).</summary>
        public bool ActualPosition(Suspect s, out Vector3 position)
        {
            position = s.LastKnown;
            if (s == VanSuspect)
            {
                if (Van == null) return false;
                position = VanCenter;
                return true;
            }
            if (Pawn == null) return false;
            position = Pawn.Position;
            return true;
        }

        /// <summary>Metres from the suspect's real position to the nearest police car out of the station lot (or busy
        /// officer); +inf when none.</summary>
        public float NearestPolice(Suspect s)
        {
            if (!ActualPosition(s, out Vector3 p)) return float.PositiveInfinity;
            float best = float.PositiveInfinity;
            foreach (PoliceUnit u in Units)
                if (u.State != PoliceUnit.UnitState.Parked) best = Mathf.Min(best, Vector3.Distance(u.transform.position, p));
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.isActiveAndEnabled && o.IsAfter(s)) best = Mathf.Min(best, Vector3.Distance(o.transform.position, p));
            return best;
        }

        // A chased suspect nobody has seen for EvadeTime and more than EvadeDistance from every car (and busy officer) is
        // lost: every car after it gives up at once (siren off, back to patrol), the officers after it stand down, and the
        // wanted flag clears soon. Seeing it before that restarts the clock (a sighting updates LastSeen).
        private void CheckEvade(Suspect s, float now)
        {
            if (!s.Wanted || !s.Chased) return;
            bool after = false;
            foreach (PoliceUnit u in Units)
                if (u.IsAfter(s)) after = true;
            if (!after) return;
            if (Unseen(s, now) < Config.EvadeTime.At(Night) || NearestPolice(s) <= Config.EvadeDistance) return;
            float unseen = Unseen(s, now);
            foreach (PoliceUnit u in Units)
                if (u.IsAfter(s)) u.GiveUp(GiveUpCause.Evaded);
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.IsAfter(s)) o.StandDown();
            ReleaseSoon(s);
            if (Log) Debug.Log($"[Police] {s.Name} got away: unseen {unseen:0.0} s, nearest police {NearestPolice(s):0} m", this);
            Hint($"Полиция: {s.Name} ушёл");
        }

        /// <summary>The police lost the suspect or left it at its base: the wanted flag clears WantedClearsAfterEvade from
        /// now, unless someone is still after it (then the usual WantedClearsAfter after the last one stops).</summary>
        public void ReleaseSoon(Suspect s)
        {
            if (s == null || !s.Wanted) return;
            s.ClearAt = Mathf.Min(s.ClearAt, Time.time + Config.WantedClearsAfterEvade);
        }

        // ---------- Queries for units and officers ----------

        public static Vector2 Plan(Vector3 world) => new(world.x, world.z);

        public float DoorDistance(Vector3 world) => Data.DoorDistance(HomeBase, Plan(world));

        public bool InsideSafe(Vector3 world) => DoorDistance(world) < Data.SafeRadius;

        public Vector3 VanCenter => Van != null ? Van.transform.TransformPoint(0f, 1.0f, 0f) : Vector3.zero;
        public Vector3 VanVelocity => VanBody != null ? VanBody.linearVelocity : Vector3.zero;
        public float VanSpeedKmh => Van != null ? Mathf.Abs(Van.SpeedKmh) : 0f;

        /// <summary>The player sits in the van (drives or rides in the cargo bay).</summary>
        public bool PawnInVan
        {
            get
            {
                if (Pawn == null) return false;
                if (_seat != null && _seat.Driving) return true;
                if (_rider == null && Pawn.Body != null) Pawn.Body.TryGetComponent(out _rider);
                return _rider != null && _rider.Inside;
            }
        }

        public bool PawnOnFoot => Pawn != null && Pawn.Controlled && !PawnInVan;

        /// <summary>What police chase now: the player on foot when wanted, else the van when wanted (a wanted player in
        /// the van makes the van wanted).</summary>
        public bool Target(out Suspect suspect, out Vector3 position, out Vector3 velocity, out bool isVan)
        {
            if (PawnSuspect.Wanted && PawnOnFoot)
            {
                suspect = PawnSuspect;
                position = Pawn.Position + Vector3.up * 1.1f;
                velocity = Vector3.zero;
                isVan = false;
                return true;
            }
            if (Van != null && (VanSuspect.Wanted || (PawnSuspect.Wanted && PawnInVan)))
            {
                // A wanted player in the van makes the van wanted, for at least as long as the player is.
                if (!VanSuspect.Wanted) MarkWanted(VanSuspect, VanCenter);
                if (PawnSuspect.Wanted) VanSuspect.ClearAt = Mathf.Max(VanSuspect.ClearAt, PawnSuspect.ClearAt);
                suspect = VanSuspect;
                position = VanCenter;
                velocity = VanVelocity;
                isVan = true;
                return true;
            }
            suspect = null;
            position = velocity = Vector3.zero;
            isVan = false;
            return false;
        }

        /// <summary>A unit or officer sees the suspect right now: everyone after it gets the position (radio).</summary>
        public void Sighted(Suspect s, Vector3 position, Vector3 velocity)
        {
            s.LastKnown = position;
            s.Velocity = velocity;
            s.LastSeen = Time.time;
        }

        public void MarkWanted(Suspect s, Vector3 where)
        {
            if (s == null) return;
            if (!s.Wanted && Log) Debug.Log($"[Police] wanted: {s.Name} at ({where.x:0}, {where.z:0})", this);
            if (!s.Wanted) s.Chased = false;
            s.Wanted = true;
            s.LastKnown = where;
            s.ClearAt = Time.time + Config.WantedClearsAfter;
        }

        // ---------- Heat ----------

        public int DistrictAt(Vector3 world) => Crowd != null && Crowd.Map != null ? Mathf.Max(0, Crowd.DistrictAt(world)) : 0;

        public float HeatAt(Vector3 world) => Heat[Mathf.Clamp(DistrictAt(world), 0, Heat.Length - 1)];

        public void AddHeat(Vector3 where, float amount)
        {
            int d = Mathf.Clamp(DistrictAt(where), 0, Heat.Length - 1);
            Heat[d] = Mathf.Clamp(Heat[d] + amount, 0f, 100f);
        }

        public float DistrictHeat(string id)
        {
            if (Crowd == null || Crowd.Map == null) return Heat[0];
            int d = Crowd.Map.DistrictIndex(id);
            return d >= 0 && d < Heat.Length ? Heat[d] : 0f;
        }

        private void ApplyHeatFloors()
        {
            if (Crowd == null || Crowd.Map == null || Config.HeatFloorDistricts == null) return;
            for (int i = 0; i < Config.HeatFloorDistricts.Length && i < Config.HeatFloors.Length; i++)
            {
                int d = Crowd.Map.DistrictIndex(Config.HeatFloorDistricts[i]);
                if (d >= 0) Heat[d] = Mathf.Max(Heat[d], Config.HeatFloors[i]);
            }
        }

        /// <summary>Seconds before cars sent to 'where' leave: the radio delay + the district's PoliceConfig.Presence
        /// DispatchDelay (the alley district: long), 1 s quicker at high heat, at least 1 s.</summary>
        public float RadioDelay(Vector3 where)
        {
            float delay = Config.RadioDelay.At(Night) + PresenceAt(where).DispatchDelay;
            if (HeatAt(where) >= Config.HighHeat) delay -= 1f;
            return Mathf.Max(1f, delay);
        }

        /// <summary>The rare shot (canon 77): in a hot district (heat >= HighHeat), or at night when this chase's roll allowed it.</summary>
        public bool ShootingAllowed(Vector3 where, bool nightRoll) => HeatAt(where) >= Config.HighHeat || (Night > 0.5f && nightRoll);

        // ---------- Patrol roles ----------

        /// <summary>Cars that patrol now: PatrolCarsDay..PatrolCarsNight (one more at night).</summary>
        public int PatrolCount => Mathf.RoundToInt(Mathf.Lerp(Config.PatrolCarsDay, Config.PatrolCarsNight, Night));

        // Car index -> patrol rank: the first PatrolCarsDay cars patrol, the next one is the reserve (always parked
        // unless dispatched), the rest patrol at night.
        public bool ShouldPatrol(PoliceUnit unit)
        {
            int reserve = Config.PatrolCarsDay;
            int rank = unit.Index < reserve ? unit.Index : unit.Index == reserve ? int.MaxValue : unit.Index - 1;
            return rank < PatrolCount;
        }

        /// <summary>The free loop with the highest score (base score + heat of its districts / 25 x their PoliceConfig.Presence
        /// patrol weight + a nudge toward the last alert); two cars never share a loop.</summary>
        public int ChooseLoop(PoliceUnit unit, int preferred)
        {
            int best = -1;
            float bestScore = float.MinValue;
            for (int l = 0; l < Data.Loops.Length; l++)
            {
                bool taken = false;
                foreach (PoliceUnit u in Units)
                    if (u != unit && u.Loop == l && (u.State == PoliceUnit.UnitState.Patrol || u.State == PoliceUnit.UnitState.Return))
                        taken = true;
                if (taken) continue;
                PoliceLoop loop = Data.Loops[l];
                float score = Mathf.Lerp(loop.ScoreDay, loop.ScoreNight, Night);
                foreach (string d in loop.Districts) score += DistrictHeat(d) / 25f * Config.PresenceOf(d).Patrol;
                if (l == preferred) score += 2f;
                if (score > bestScore)
                {
                    bestScore = score;
                    best = l;
                }
            }
            return best;
        }

        // ---------- Update ----------

        private void Update()
        {
            using Unity.Profiling.ProfilerMarker.AutoScope scope = Marker.Auto();
            float now = Time.time;
            float dt = Time.deltaTime;
            // Heat cools; the richer districts never below their floor.
            float decay = dt / Mathf.Max(0.1f, Config.HeatDecaySeconds);
            for (int i = 0; i < Heat.Length; i++) Heat[i] = Mathf.Max(0f, Heat[i] - decay);
            ApplyHeatFloors();
            if (Pawn == null && now >= _nextPawnLookup)
            {
                _nextPawnLookup = now + 1f;
                Pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            }
            if (now >= _nextBalance)
            {
                _nextBalance = now + 1f;
                UpdateBalance();
            }
            CheckEvade(VanSuspect, now);
            CheckEvade(PawnSuspect, now);
            UpdateWanted(VanSuspect, now);
            UpdateWanted(PawnSuspect, now);
            if (now >= _nextDrag)
            {
                _nextDrag = now + 0.5f;
                CheckDragging(now);
            }
            if (now >= _nextScan)
            {
                if (_nextScan == 0f && Log)
                {
                    Debug.Log($"[Police] {Data.Revision}: {Units.Count} cars, station {Data.StationId}, home {HomeId}, {Data.Loops.Length} loops, " +
                              $"data {Data.name} (plan {Data.PlanHash})", this);
                    if (Van != null) Debug.Log($"[Police] balance: {BalanceLine(CurrentVan, Balance)}", this);
                }
                _nextScan = now + 0.5f;
                AdoptCrowdOfficers();
            }
            for (int i = PoliceKnocks.Count - 1; i >= 0; i--)
                if (now - PoliceKnocks[i].time > 60f) PoliceKnocks.RemoveAt(i);
            for (int i = _incidents.Count - 1; i >= 0; i--)
                if (now - _incidents[i].Time > 90f) _incidents.RemoveAt(i);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (Input.GetKeyDown(HudKey))
            {
                if (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift))
                {
                    HomeBase = (HomeBase + 1) % Mathf.Max(1, Data.BaseCount);
                    Hint($"Полиция: дом команды теперь {HomeId}");
                }
                else ShowHud = !ShowHud;
            }
#endif
        }

        private void UpdateWanted(Suspect s, float now)
        {
            if (!s.Wanted) return;
            bool hunted = false;
            foreach (PoliceUnit u in Units)
                if (u.IsAfter(s)) hunted = true;
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.IsAfter(s)) hunted = true;
            if (hunted) s.ClearAt = now + Config.WantedClearsAfter;
            else if (now >= s.ClearAt)
            {
                s.Wanted = false;
                s.Chased = false;
                if (Log) Debug.Log($"[Police] wanted cleared: {s.Name}", this);
                Hint("Полиция: розыск снят");
            }
        }

        // Crowd foot patrol officers (CrowdRole.Police walkers) become PoliceOfficers; extra ones come with heat.
        private void AdoptCrowdOfficers()
        {
            if (Crowd == null) return;
            foreach (CrowdWalker w in Crowd.Walkers)
                if (w != null && w.Role == CrowdRole.Police && !w.TryGetComponent(out PoliceOfficer _))
                {
                    var officer = w.gameObject.AddComponent<PoliceOfficer>();
                    officer.Fat = (w.GetInstanceIDSafe() & 1) == 1;
                }
            int hot = 0;
            if (Crowd.Map != null && Crowd.Map.Patrol != null)
                foreach (int d in Crowd.Map.Patrol.Districts)
                    if (d >= 0 && d < Heat.Length && Heat[d] >= Config.HighHeat) hot++;
            Crowd.ExtraOfficers = Mathf.Min(Config.MaxExtraOfficers, hot);
        }

        // A player holding a downed NPC, in sight of the police: an offense (once per body per 10 s). The body is the
        // capsule or the stage-9 ragdoll (GreyboxNpc.PhysicalBody).
        private void CheckDragging(float now)
        {
            if (Pawn == null || !Pawn.Controlled) return;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || npc.State != NpcState.Down) continue;
                OnlyVolunteers.Characters.Npc.INpcBody body = npc.PhysicalBody;
                if (body == null || !body.Active || body.HolderCount == 0) continue;
                if ((npc.Center - Pawn.Position).sqrMagnitude > 9f) continue;
                if (_dragNoted.TryGetValue(npc, out float at) && now - at < 10f) continue;
                if (!AnyPoliceSees(Pawn.Position + Vector3.up * 1.2f)) continue;
                _dragNoted[npc] = now;
                Offense(PawnSuspect, Pawn.Position, Config.HeatDrag, "тащит тело");
            }
        }

        // ---------- Offenses ----------

        public static void NotePoliceKnock(Vector3 where) => PoliceKnocks.Add((where, Time.time));

        private static bool KnockedByPolice(Vector3 where)
        {
            foreach ((Vector3 w, float t) in PoliceKnocks)
                if ((w - where).sqrMagnitude < 16f && Time.time - t < 60f) return true;
            return false;
        }

        private void OnIncident(GreyboxNpc victim, NpcIncident kind)
        {
            if (victim == null) return;
            Vector3 where = victim.Center;
            if (kind == NpcIncident.Stunned && KnockedByPolice(victim.transform.position)) return;
            Suspect attacker = Attacker(victim, kind);
            _incidents.Add(new Incident { Where = where, Time = Time.time, Kind = kind, Attacker = attacker });
            bool cop = victim.TryGetComponent(out PoliceOfficer hitCop);
            if (cop && attacker != null)
            {
                // Hitting a cop: every officer within 30 m goes after the attacker, the cop included once he is up.
                Offense(attacker, where, Config.HeatHitCop, "ударил полицейского");
                foreach (PoliceOfficer o in Officers)
                    if (o != null && o != hitCop && (o.transform.position - where).sqrMagnitude < 900f) o.Aggro(attacker, where);
                hitCop.Attacker = attacker;
                return;
            }
            if (attacker == null) return;
            if (!AnyPoliceSees(where)) return;
            float heat = kind == NpcIncident.Captured ? Config.HeatCapture : Config.HeatStun;
            Offense(attacker, where, heat, kind == NpcIncident.Captured ? "погрузка в бусик" : "оглушил человека");
            MarkHeated(where);
        }

        // Who did it: a capture is the van's; a stun is the player's when he is within 4 m, else the van's when it went by fast.
        private Suspect Attacker(GreyboxNpc victim, NpcIncident kind)
        {
            if (kind == NpcIncident.Captured) return VanSuspect;
            Vector3 p = victim.transform.position;
            if (Pawn != null && Pawn.Controlled && (Pawn.Position - p).sqrMagnitude < 16f) return PawnSuspect;
            if (Van != null && VanSpeedKmh > 10f && (Van.transform.position - p).sqrMagnitude < 36f) return VanSuspect;
            return null;
        }

        /// <summary>Police saw it: the suspect is wanted, heat goes up, every unit and officer that sees it aggroes, and
        /// the rest are dispatched as for a witness report (the police raise the alert themselves).</summary>
        public void Offense(Suspect s, Vector3 where, float heat, string what)
        {
            MarkWanted(s, where);
            AddHeat(where, heat);
            if (Log) Debug.Log($"[Police] offense seen: {what} by {s.Name} at ({where.x:0}, {where.z:0}), heat {HeatAt(where):0}", this);
            foreach (PoliceUnit u in Units)
                if (u.Sees(where)) u.SawOffense(s, where);
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.Sees(where)) o.Aggro(s, where);
            Dispatch(where, 1, s == VanSuspect, $"полиция видела: {what}");
        }

        public void Rammed(PoliceUnit unit)
        {
            Offense(VanSuspect, VanCenter, Config.HeatRam, "таран полицейской машины");
        }

        public bool AnyPoliceSees(Vector3 point)
        {
            foreach (PoliceUnit u in Units)
                if (u.Sees(point)) return true;
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.Sees(point)) return true;
            return false;
        }

        private void MarkHeated(Vector3 where)
        {
            for (int i = 0; i < _incidents.Count; i++)
                if ((_incidents[i].Where - where).sqrMagnitude < 25f)
                {
                    Incident inc = _incidents[i];
                    inc.Heated = true;
                    _incidents[i] = inc;
                }
        }

        /// <summary>Tests: a clean start. Heat 0, nothing wanted, every car parked, the patrol cars put at 'loopAlong'
        /// (0..1) of their loops, officers back in their cars or on patrol, this home base and night.</summary>
        public void ResetForTest(int home, float night, float loopAlong)
        {
            NightOverride = night;
            HomeBase = Mathf.Clamp(home, 0, Mathf.Max(0, Data.BaseCount - 1));
            for (int i = 0; i < Heat.Length; i++) Heat[i] = 0f;
            foreach (Suspect s in new[] { VanSuspect, PawnSuspect })
            {
                s.Wanted = false;
                s.Chased = false;
                s.LastSeen = -999f;
                s.Velocity = Vector3.zero;
            }
            TipUntil = 0f;
            LastGiveUp = "";
            _incidents.Clear();
            PoliceKnocks.Clear();
            foreach (PoliceOfficer o in Officers.ToArray())
                if (o != null)
                {
                    if (o.CrewOf != null) o.Board(true);
                    else o.StandDown();
                }
            foreach (PoliceUnit u in Units) u.ResetToStall();
            foreach (PoliceUnit u in Units)
                if (ShouldPatrol(u)) u.PlaceOnLoop(loopAlong);
        }

        // ---------- Witness reports and dispatch ----------

        private void OnAlert(CrowdAlert alert)
        {
            if (KnockedByPolice(alert.Position)) return; // the police car did it: not their problem
            // The incident behind the report: its attacker becomes wanted, its heat counts once.
            Suspect attacker = null;
            for (int i = _incidents.Count - 1; i >= 0; i--)
                if ((_incidents[i].Where - alert.Position).sqrMagnitude < 25f)
                {
                    Incident inc = _incidents[i];
                    attacker = inc.Attacker;
                    if (!inc.Heated)
                    {
                        AddHeat(alert.Position, inc.Kind == NpcIncident.Captured ? Config.HeatCapture : Config.HeatStun);
                        inc.Heated = true;
                        _incidents[i] = inc;
                    }
                    break;
                }
            if (attacker == null && alert.Kind == NpcIncident.Captured) attacker = VanSuspect;
            if (attacker != null) MarkWanted(attacker, alert.Position);
            // The officer the witness ran to (or who saw it) goes there himself.
            CrowdWalker officerWalker = alert.Officer != null ? alert.Officer : alert.Reporter != null && alert.Reporter.Role == CrowdRole.Police ? alert.Reporter : null;
            if (officerWalker != null && officerWalker.TryGetComponent(out PoliceOfficer officer)) officer.Respond(alert.Position, attacker);
            Dispatch(alert.Position, alert.Level, alert.Kind == NpcIncident.Captured, $"свидетель ({alert.Via})", true);
        }

        /// <summary>Send the fastest free cars (and nearby foot officers) to 'where'. District presence (PoliceConfig.Presence):
        /// a witness report gets cars only with the district's DispatchChance (always at heat >= HighHeat; an offense the
        /// police saw and test calls never roll), they leave after its DispatchDelay (RadioDelay), and it adds ExtraCars.</summary>
        public void Dispatch(Vector3 where, int level, bool capture, string why, bool witness = false)
        {
            float now = Time.time;
            float night = Night;
            float heat = HeatAt(where);
            PolicePresenceDef presence = PresenceAt(where);
            bool sendCars = !witness || heat >= Config.HighHeat || Random.value < presence.DispatchChance;
            if (sendCars && (capture || (Van != null && (Van.transform.position - where).sqrMagnitude < Config.VanNearIncident * Config.VanNearIncident)))
                TipUntil = Mathf.Max(TipUntil, now + Config.TipWindow.At(night));
            int wanted = level >= 2 || heat >= Config.HighHeat ? 2 : 1;
            if (night > 0.5f) wanted++;
            wanted += Mathf.Max(0, presence.ExtraCars);
            wanted = Mathf.Min(wanted, Mathf.RoundToInt(Config.MaxCarsPerAlert.At(night)));
            if (!sendCars) wanted = 0;
            int already = 0;
            foreach (PoliceUnit u in Units)
                if (u.IsBusy && (u.Incident - where).sqrMagnitude < 3600f) already++;
            float radio = RadioDelay(where);
            _sb.Clear();
            _candidates.Clear();
            if (already < wanted)
            {
                Data.ComputeEtas(Plan(where), HomeBase);
                foreach (PoliceUnit u in Units)
                    if (u.Dispatchable)
                    {
                        u.Eta = radio + (u.State == PoliceUnit.UnitState.Parked ? Config.BoardingTime : 0f) + Data.EtaTo(Plan(u.transform.position));
                        _candidates.Add(u);
                    }
                _candidates.Sort((a, b) => a.Eta.CompareTo(b.Eta));
                for (int i = 0; i < _candidates.Count && already < wanted; i++, already++)
                {
                    PoliceUnit u = _candidates[i];
                    u.Dispatch(where, radio);
                    _sb.Append($" #{u.Index + 1} (ETA {u.Eta:0} с)");
                }
            }
            // Patrol cars not sent move their next lap toward the trouble (not in a district patrols keep out of).
            int district = DistrictAt(where);
            if (presence.Patrol >= Config.PatrolMinPresence)
                foreach (PoliceUnit u in Units)
                    if (u.State == PoliceUnit.UnitState.Patrol) u.PreferDistrict(district);
            // Foot officers near enough run there.
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.CanRespond && (o.transform.position - where).sqrMagnitude < Config.FootRespondRadius * Config.FootRespondRadius * 0.6f)
                    o.Respond(where, capture ? VanSuspect : null);
            if (Log) Debug.Log($"[Police] alert at ({where.x:0}, {where.z:0}) {DistrictId(where) ?? "?"} level {level}, {why}: heat {heat:0}, night {night:0.0}, " +
                               $"cars{(_sb.Length > 0 ? _sb.ToString() : sendCars ? " none sent" : $" none sent (district roll {presence.DispatchChance:0%} failed)")}" +
                               $"{(radio > Config.RadioDelay.At(night) + 0.5f ? $", delay {radio:0} s" : "")}{(Tip ? ", van tip on" : "")}", this);
        }

        // ---------- Arrest (placeholder until the arrest scene, canon 78-80) ----------

        private void OnArrest(GreyboxPawn pawn, PoliceOfficer officer)
        {
            if (pawn == null) return;
            string loss = "";
            if (pawn.Body != null && pawn.Body.TryGetComponent(out LocalInventory inventory) && inventory.Model != null)
            {
                ArrestResult r = inventory.Model.ApplyArrestPenalty(Config.ArrestCashPercent);
                loss = $": −{r.CashTaken} наличных" + (r.Confiscated.IsEmpty ? "" : ", изъят самый дорогой предмет");
            }
            Vector3 at = Respawn != null ? Respawn.position : new Vector3(Data.Respawn.x, pawn.Position.y, Data.Respawn.y);
            float yaw = Respawn != null ? Respawn.eulerAngles.y : Data.RespawnYaw;
            if (Crowd != null) at = Crowd.Ground(Plan(at)) + Vector3.up * 0.1f;
            pawn.Teleport(at, yaw);
            PawnSuspect.Wanted = false;
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.IsAfter(PawnSuspect)) o.StandDown();
            Hint("АРЕСТ (заглушка): участок" + loss);
            Debug.Log($"[Police] ARREST by {(officer != null ? officer.name : "?")}{loss}; respawn at the station ({at.x:0}, {at.z:0})", this);
        }

        private void OnPursuitEnded(PoliceUnit unit, GiveUpCause cause, float metres)
        {
            string why = cause switch
            {
                GiveUpCause.Evaded => "ушёл",
                GiveUpCause.Base => "ждали у базы",
                GiveUpCause.Lost => "не нашли",
                GiveUpCause.CrewDown => "экипаж лежит",
                _ => "отозван",
            };
            LastGiveUp = $"#{unit.Index + 1} сдался: {why}" + (float.IsInfinity(metres) ? "" : $", {metres:0} м до {HomeId}");
            _lastGiveUpUntil = Time.time + 8f;
            if (Log) Debug.Log($"[Police] {LastGiveUp}", unit);
        }

        private string _lastHint;
        private float _lastHintAt = -99f;

        public void Hint(string text)
        {
            // The same line again within 3 s is dropped (the crowd's hint list keeps every line it gets).
            if (text == _lastHint && Time.time - _lastHintAt < 3f) return;
            _lastHint = text;
            _lastHintAt = Time.time;
            if (Crowd != null) Crowd.Hint(text);
            else _hints.Add((text, Time.time + 6f));
        }

        // ---------- Dev HUD ----------

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private void OnGUI()
        {
            if (Config == null || Data == null) return;
            float now = Time.time;
            if (_hints.Count > 0)
            {
                _hintStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter, normal = { textColor = new Color(0.5f, 0.7f, 1f) } };
                for (int i = _hints.Count - 1; i >= 0; i--)
                    if (_hints[i].until < now) _hints.RemoveAt(i);
                for (int i = 0; i < _hints.Count; i++)
                    GUI.Label(new Rect(0f, 120f + 24f * i, Screen.width, 24f), _hints[i].text, _hintStyle);
            }
            if (!ShowHud) return;
            _hudStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 13, wordWrap = true, normal = { textColor = Color.white } };
            if (now >= _nextHud && Event.current.type == EventType.Layout)
            {
                _nextHud = now + 0.25f;
                _hudText = HudString(now);
                _hudContent.text = _hudText;
            }
            float width = Mathf.Min(Screen.width - 28f, 890f);
            float height = Mathf.Max(44f, _hudStyle.CalcHeight(_hudContent, width));
            GUI.Box(new Rect(8f, 8f, width + 12f, height + 2f), GUIContent.none);
            GUI.Label(new Rect(14f, 10f, width, height), _hudText, _hudStyle);
        }

        // The HUD line, rebuilt 4 times a second (not on every OnGUI call).
        private string HudString(float now)
        {
            _sb.Clear();
            _sb.Append($"ПОЛИЦИЯ | дом {HomeId} | ");
            if (Van != null)
            {
                // Balance: the reference van (levels Д/Т/У = engine/brakes/handling) and the police car vs the players' van now.
                PoliceBalance b = Balance, v = CurrentVan;
                _sb.Append($"баланс: эталон Д{b.Engine}/Т{b.Brakes}/У{b.Handling} ≤{b.VanTopKmh:0} км/ч → полиция ≤{b.TopKmh:0}, " +
                           $"разгон {b.A:0.00}, поворот {b.Lateral:0.0}, тормоз {b.Brake:0.0} м/с²; бусик Д{v.Engine}/Т{v.Brakes}/У{v.Handling} " +
                           $"≤{Van.MaxSpeedKmh:0}, разгон {v.VanA:0.00}, поворот {v.VanLateral:0.0}, тормоз {v.VanBrake:0.0} | ");
            }
            Suspect chased = VanSuspect.Wanted && VanSuspect.Chased ? VanSuspect : PawnSuspect.Wanted && PawnSuspect.Chased ? PawnSuspect : null;
            if (chased != null)
            {
                float near = NearestPolice(chased);
                _sb.Append($"не видят {Mathf.Min(Unseen(chased, now), 99f):0}/{Config.EvadeTime.At(Night):0} с, до полиции " +
                           $"{(float.IsInfinity(near) ? "—" : near.ToString("0"))}/{Config.EvadeDistance:0} м | ");
            }
            foreach (PoliceUnit u in Units) _sb.Append(u.HudText()).Append(" | ");
            int foot = 0;
            foreach (PoliceOfficer o in Officers)
                if (o != null && o.isActiveAndEnabled) foot++;
            _sb.Append($"пешие {foot} | жар:");
            bool any = false;
            for (int d = 0; d < Heat.Length; d++)
            {
                if (Heat[d] < 1f) continue;
                string name = Crowd != null && Crowd.Map != null && d < Crowd.Map.Districts.Count ? Crowd.Map.Districts[d].Id : d.ToString();
                _sb.Append($" {name} {Heat[d]:0}");
                any = true;
            }
            if (!any) _sb.Append(" 0");
            _sb.Append($" | ночь {Night:0.0}");
            if (VanSuspect.Wanted) _sb.Append(" | РОЗЫСК: бусик");
            if (PawnSuspect.Wanted) _sb.Append(" | РОЗЫСК: игрок");
            if (now < _lastGiveUpUntil) _sb.Append("\n").Append(LastGiveUp);
            return _sb.ToString();
        }
#endif

        private void OnDrawGizmosSelected()
        {
            if (Data == null || Data.NodeCount == 0) return;
            float y = 2f;
            Color[] colors = { new(0.2f, 0.4f, 1f), new(0.1f, 0.8f, 0.9f), new(0.7f, 0.3f, 1f), Color.white };
            for (int l = 0; l < Data.Loops.Length; l++)
            {
                Gizmos.color = colors[l % colors.Length];
                foreach (int signed in Data.Loops[l].Edges)
                {
                    int e = Mathf.Abs(signed) - 1;
                    Vector2 a = Data.Nodes[Data.EdgeA[e]], b = Data.Nodes[Data.EdgeB[e]];
                    Gizmos.DrawLine(new Vector3(a.x, y + l * 0.3f, a.y), new Vector3(b.x, y + l * 0.3f, b.y));
                }
            }
            // The home base's safe disc.
            int home = Application.isPlaying ? HomeBase : Mathf.Max(0, Config != null ? Data.BaseIndex(Config.DefaultHomeBase) : 0);
            if (home < 0 || home >= Data.BaseCount) return;
            Vector2 door = Data.BaseDoors[home];
            Gizmos.color = Color.green;
            for (int k = 0; k < 48; k++)
            {
                float a0 = k * Mathf.PI * 2f / 48f, a1 = (k + 1) * Mathf.PI * 2f / 48f;
                Gizmos.DrawLine(new Vector3(door.x + Mathf.Cos(a0) * Data.SafeRadius, y, door.y + Mathf.Sin(a0) * Data.SafeRadius),
                                new Vector3(door.x + Mathf.Cos(a1) * Data.SafeRadius, y, door.y + Mathf.Sin(a1) * Data.SafeRadius));
            }
        }
    }

    internal static class PoliceObjectExtensions
    {
        // GetInstanceID is obsolete-as-error in this Unity: a stable-enough per-object number from the name instead.
        public static int GetInstanceIDSafe(this Object o) => o != null ? o.name.GetHashCode() : 0;
    }
}
