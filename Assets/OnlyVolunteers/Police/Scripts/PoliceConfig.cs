using UnityEngine;

namespace OnlyVolunteers.Police
{
    // A number that blends from day (night = 0) to night (1): CrowdDirector.Evening is the one night-aggression knob.
    [System.Serializable]
    public struct DayNight
    {
        public float Day, Night;

        public DayNight(float day, float night)
        {
            Day = day;
            Night = night;
        }

        public float At(float night) => Mathf.Lerp(Day, Night, Mathf.Clamp01(night));
    }

    // A patrol loop to bake: one per district group (design 4.2-4.3). Waypoints are plan point ids (P10, CLOCK_SQUARE),
    // crowd witness hotspot ids (WITNESS_CASINO) or "x,y" plan metres; ids a newer plan no longer has are skipped, and with
    // none left the group's own hotspots are used in nearest-neighbour order. The loop starts and ends at the station.
    [System.Serializable]
    public sealed class PoliceLoopDef
    {
        public string Name = "L1";
        [Tooltip("Crowd/plan district ids this loop covers (its heat raises the loop's score).")]
        public string[] Districts = new string[0];
        public string[] Waypoints = new string[0];
        public float ScoreDay = 1f, ScoreNight = 1f;
    }

    // A hotspot of the timing report (where captures happen): id as for waypoints, plus a short name for the tables.
    [System.Serializable]
    public sealed class PoliceHotspotDef
    {
        public string Id;
        public string Name;
    }

    // Police presence of one district (Fedya 2026-10-07): the alley district (bad district) has almost no police, so a
    // stock van can grind there; old town is full of them, the problem that pushes the next upgrades. Keyed by the crowd /
    // plan district id, so a new map with other ids only needs new rows (unknown ids get PoliceConfig.DefaultPresence).
    [System.Serializable]
    public sealed class PolicePresenceDef
    {
        public string District = "";
        [Tooltip("Patrol weight: a district's heat raises a patrol loop's score x this, and an alert there moves the next " +
                 "lap of a patrol only when it is at least PatrolMinPresence. Below PatrolMinPresence the bake keeps the patrol " +
                 "loops out of the district (its waypoints are skipped, its roads cost LowPresenceDetour x their length).")]
        public float Patrol = 1f;
        [Tooltip("Share of witness reports from here that get a car at all (one roll per report; heat >= HighHeat there or an " +
                 "offense the police saw themselves: always).")]
        [Range(0f, 1f)] public float DispatchChance = 1f;
        [Tooltip("Seconds added to the radio delay before cars sent here leave (negative = quicker; the delay is at least 1 s).")]
        public float DispatchDelay;
        [Tooltip("Cars added to each alert here (MaxCarsPerAlert still caps them).")]
        public int ExtraCars;
    }

    // Every tunable number of police v1 (docs/drafts/POLICE_V1_DRAFT.md). One asset: Police/Data/PoliceConfig.asset.
    // Pursuit model (Fedya 2026-10-07, GTA-like): no give-up line near the base; the police car is a little stronger than a
    // reference van at upgrade levels Engine 1 / Brakes 3 / Handling 3 (balance ratios), so a stock van needs upgrades and
    // good driving; the chase ends when the van stays unseen and far away (evade rule), or at the base's safe disc.
    // District presence (same day): almost no police in the alley district, many in old town (Presence table).
    // The bake (PoliceBaker) reads the model and placement part; the runtime (PoliceDirector, PoliceUnit, PoliceCarMotor,
    // PoliceOfficer) reads the rest. Changing a bake number needs "Bake Police Data" again; runtime numbers act at once.
    [CreateAssetMenu(menuName = "OnlyVolunteers/Police Config", fileName = "PoliceConfig")]
    public sealed class PoliceConfig : ScriptableObject
    {
        [Header("Bake: placement (data-driven, recomputed per plan)")]
        [Tooltip("Plan point of the station; empty or missing = the building of type StationBuildingType.")]
        public string StationPoint = "P10";
        public string StationBuildingType = "police_station";
        [Tooltip("Home base until base ownership exists (Shift + backquote cycles it in Play).")]
        public string DefaultHomeBase = "B01";
        [Tooltip("Districts where the bake's response target is the tighter one (old town; the alley district has almost no " +
                 "police since 2026-10-07, see Presence).")]
        public string[] CoreDistricts = { "old_town" };
        public PoliceHotspotDef[] Hotspots =
        {
            new() { Id = "BAD_CENTER", Name = "BAD_CENTER" }, new() { Id = "BAD_BLOCK_2", Name = "Двор 2" }, new() { Id = "P07", Name = "P07 притон" },
            new() { Id = "CLOCK_SQUARE", Name = "CLOCK_SQUARE" }, new() { Id = "WITNESS_SUPERMARKET", Name = "Супермаркет" },
            new() { Id = "WITNESS_CASINO", Name = "Казино" }, new() { Id = "BEACH_VALLEY_ENTRY", Name = "Пляж (долина)" },
            new() { Id = "BEACH_ENTRY", Name = "Пляж (элитка)" }, new() { Id = "P15", Name = "Элитка P15" },
        };
        public PoliceLoopDef[] Loops =
        {
            new()
            {
                // Old town (2026-10-07: no patrol loop in the alley district any more).
                Name = "L1", Districts = new[] { "old_town" }, ScoreDay = 3f, ScoreNight = 3f,
                Waypoints = new[] { "P05", "P09", "WITNESS_SUPERMARKET", "P13-5", "P13-3", "CLOCK_SQUARE", "P11" },
            },
            new()
            {
                Name = "L2", Districts = new[] { "fields", "beach", "transition" }, ScoreDay = 1.5f, ScoreNight = 3f,
                Waypoints = new[] { "CLOCK_SQUARE", "394,600", "WITNESS_CASINO", "BEACH_VALLEY_ENTRY", "WITNESS_CASINO", "394,600", "CLOCK_SQUARE" },
            },
            new()
            {
                Name = "L3", Districts = new[] { "elite", "old_town", "beach" }, ScoreDay = 1f, ScoreNight = 2f,
                Waypoints = new[] { "ELITE_GATE", "P15", "BEACH_ENTRY", "ELITE_GATE", "CLOCK_SQUARE", "P11" },
            },
        };
        [Tooltip("Patrolling cars by day / at night (the rest wait in the station lot; one of them is the reserve).")]
        public int PatrolCarsDay = 2, PatrolCarsNight = 3;
        [Tooltip("Cars placed at the station (one per parking space at most).")]
        public int Cars = 4;
        [Tooltip("Edges narrower than this are not police roads (the van can escape through them). The narrowest plan roads " +
                 "are 3.8 m (rural) and 4.5 m (v13 alleys), so this only catches a future footpath-wide road.")]
        public float MinRoadWidth = 3f;
        [Tooltip("Road classes (road_graph edge \"class\") that are no police roads: police routes and dispatch avoid them, " +
                 "the van escapes through them (a close chase with sight may still follow it in). Fedya's call; empty = all roads.")]
        public string[] NoPoliceRoadClasses = { "alley" };
        [Tooltip("Safe disc round the home base door (canon 76): police never drive, chase or search inside it.")]
        public float SafeRadius = 60f;
        [Tooltip("Patrol loops count roads within this many seconds of reference van driving from the default home base 20 % " +
                 "longer: a patrol keeps off the start area when a route not much longer exists (design 4.3).")]
        public float PatrolAvoidHome = 25f;

        [Header("District presence (data-driven by district id: patrol loops, dispatch, the bake)")]
        [Tooltip("Per district: patrol weight, share of witness reports that get a car, extra delay, extra cars. The alley " +
                 "district (residential, the bad district) has almost no police; old town has many (Fedya 2026-10-07).")]
        public PolicePresenceDef[] Presence =
        {
            new() { District = "residential", Patrol = 0.1f, DispatchChance = 0.3f, DispatchDelay = 25f, ExtraCars = 0 },
            new() { District = "old_town", Patrol = 2f, DispatchChance = 1f, DispatchDelay = -1f, ExtraCars = 1 },
        };
        [Tooltip("Every district without a row in Presence (moderate police).")]
        public PolicePresenceDef DefaultPresence = new() { District = "*", Patrol = 1f, DispatchChance = 0.8f, DispatchDelay = 4f, ExtraCars = 0 };
        [Tooltip("Districts with a lower Patrol weight get no patrol loops (bake) and do not pull patrols toward an alert.")]
        public float PatrolMinPresence = 0.5f;
        [Tooltip("Bake: a road in a district below PatrolMinPresence counts this many times its length for the patrol loop " +
                 "legs, so a loop goes round the district whenever a way round exists.")]
        public float LowPresenceDetour = 8f;

        [Header("Bake: drive-time models")]
        [Tooltip("Van pace: measured / modelled time (1 = the model is right). Set after the Unity calibration, then bake again.")]
        public float VanPaceFactor = 1f;
        [Tooltip("Reference driver of the van (the pace model and the test autopilot): cornering and braking m/s^2.")]
        public float VanRefLateral = 5f, VanRefBrake = 5f;
        [Tooltip("The police car of the bake's model (edge times, ETAs, response table) is the stock van x the balance ratios " +
                 "below, as at runtime; the patrol car is its own model (35 km/h, for the lap times).")]
        public CarModel PatrolCar = new(35f, 2.0f, 0.03f, 4f, 4f, 1.8f);
        [Tooltip("Timeline of the response model and the test runs: alert after the stun, van leaves after the stun (s).")]
        public float ModelAlertAt = 4f, ModelVanLeavesAt = 12f;
        [Tooltip("Patrol positions sampled every this many metres along a loop.")]
        public float ModelSampleStep = 25f;

        [Header("Day / night (blended by CrowdDirector.Evening)")]
        public DayNight RadioDelay = new(3f, 1.5f);
        public DayNight TipWindow = new(20f, 30f);
        [Tooltip("Evade rule (GTA-like): nobody has seen the suspect for this many seconds AND it is more than EvadeDistance " +
                 "from every police car and busy officer: the police lose it (siren off, back to patrol, wanted clears quickly). " +
                 "Seeing it again before that restarts the chase.")]
        public DayNight EvadeTime = new(10f, 15f);
        [Tooltip("Pursuit -> search: nobody has seen it for this long (s) and it is more than LostSightDistance away (until " +
                 "then the car drives on along its last direction).")]
        public DayNight LostSightTime = new(6f, 9f);
        [Tooltip("A car searches at most this long (s), then gives up on its own (the evade rule usually ends it first).")]
        public DayNight SearchTime = new(20f, 30f);
        [Tooltip("Canon 76: the suspect went inside the base's safe disc: a pursuing car stops at the disc's edge, waits this " +
                 "long (s) watching, then leaves. It comes out again before that: the chase goes on.")]
        public DayNight BaseWait = new(8f, 12f);
        public DayNight RamCooldown = new(6f, 4f);
        public DayNight FootChaseCap = new(25f, 35f);
        public DayNight MaxCarsPerAlert = new(2f, 3f);

        [Header("Dispatch and pursuit")]
        public float BoardingTime = 3f;
        [Tooltip("Evade rule: metres from every police car (and busy officer) the unseen suspect must be.")]
        public float EvadeDistance = 80f;
        [Tooltip("A car within this many metres outside the safe disc (or standing) counts as at the edge: its BaseWait runs.")]
        public float BaseEdgeBand = 20f;
        public float GiveUpShakeTime = 2f, IgnoreAfterGiveUp = 30f;
        [Tooltip("The wanted flag clears this long (s) after nobody is after the suspect any more (canon 82: it passes quickly).")]
        public float WantedClearsAfter = 60f;
        [Tooltip("...and only this long after the police lost it (evade rule, a search that ran out after contact) or left it " +
                 "at its base.")]
        public float WantedClearsAfterEvade = 5f;
        public float CarSightRange = 45f, CarSightHalfAngle = 75f, CarAllRound = 15f, RoofHeight = 1.6f;
        [Tooltip("Sight range of a car already in a pursuit (it watches the van only): a van 50-60 m ahead on a straight is not lost.")]
        public float PursuitSightRange = 70f;
        public float LostSightDistance = 50f;
        [Tooltip("Responding with the tip: the van's assumed pace (m/s, at least) along its likely way home when the car looks " +
                 "for a point to meet it (about the bake's reference driver on town roads).")]
        public float InterceptVanSpeed = 14f;
        [Tooltip("Meeting point: the car must get there this many seconds before the van; within InterceptWait m of it, it stops and waits.")]
        public float InterceptMargin = 3f, InterceptWait = 15f;
        [Tooltip("A meeting point is only worth it with at least this much chase (s of van driving at InterceptVanSpeed, straight " +
                 "line) left before the home base's safe disc; else the car goes for the van itself, from behind.")]
        public float InterceptMinChase = 8f;
        [Tooltip("After the tip runs out, a car keeps its meeting point (a stake-out) until this long (s) after the van was due there.")]
        public float InterceptHold = 15f;
        [Tooltip("A pursuing crew that saw the suspect within this many seconds sees all round to the full sight range (the van " +
                 "that just passed head-on is not lost at once).")]
        public float TrackAllRound = 1f;
        [Tooltip("Route cost of a turn on the spot in a chase, as a share of UTurnPenalty (a handbrake turn after the van).")]
        public float ChaseUTurnScale = 0.35f;
        public float FootRespondRadius = 150f;
        [Tooltip("Close chase straight at the van: after a stuck episode, follow the roads again for this long (s).")]
        public float DirectBlockAfterStuck = 4f;
        public float VanNearIncident = 40f;

        [Header("Balance against a REFERENCE van (its upgrade levels below; read from the van at runtime; acts at once)")]
        [Tooltip("Upgrade levels of the reference van the police are balanced against (Fedya 2026-10-07: Engine 1, Brakes 3, " +
                 "Handling 3; the police are a little stronger than that van). The player's own levels do not change the police: " +
                 "a stock van cannot simply outrun them, Engine 2-3 wins on the straights, corners are near even at Handling/Brakes 3.")]
        [Range(0, 3)] public int RefEngineLevel = 1;
        [Range(0, 3)] public int RefBrakesLevel = 3, RefHandlingLevel = 3;
        [Tooltip("Police top speed in a chase / the reference van's MaxSpeedKmh (stock + the engine level's bonus).")]
        [Range(0.5f, 1.5f)] public float TopSpeedRatio = 1.03f;
        [Tooltip("Police full-throttle acceleration a(v) / the reference van's (A = 0.9 torque / (wheel radius x mass), torque " +
                 "= stock x the engine level's TorqueMultiplier, minus its damping x v; the measured van drives at 0.97 of that model).")]
        [Range(0.5f, 1.5f)] public float AccelRatio = 1.03f;
        [Tooltip("A clean, fast driver in the STOCK van: cornering and braking m/s^2. The reference van's are these x its " +
                 "Handling level's SidewaysGripMultiplier (cornering) and x the lower of its Brakes level's BrakeTorque / " +
                 "ForwardGrip multipliers (braking); the bake's 'fast' van column uses the stock numbers.")]
        public float VanFastLateral = 8f, VanFastBrake = 8f;
        [Tooltip("Police lateral grip / the reference van's cornering (the car plans bends at PoliceCarMotor.CornerPlanFactor " +
                 "of its grip).")]
        [Range(0.5f, 1.5f)] public float CornerGripRatio = 1.02f;
        [Tooltip("Police braking / the reference van's braking (also how early it brakes for bends).")]
        [Range(0.5f, 1.5f)] public float BrakeRatio = 1.02f;

        [Header("Driving")]
        [Tooltip("Police top speed only when there is no van in the scene (else TopSpeedRatio x the stock van's).")]
        public float TopSpeedKmh = 100f;
        public float PatrolKmh = 35f;
        [Tooltip("Route costs (s): per junction turn (x (angle / 90)^2), and for starting against the car's heading (a K-turn " +
                 "on a street costs braking, the turn and the run-up again).")]
        public float TurnPenalty = 0.5f, UTurnPenalty = 8f;
        public float ReplanInterval = 0.5f;
        public float RamDistance = 8f, RamAngle = 20f, RamMinVanKmh = 20f, RamExtra = 3f;
        [Tooltip("No bump above this van speed (km/h): a push at speed wrecks the van against the next wall.")]
        public float RamMaxVanKmh = 50f;
        public float BoxInVanKmh = 10f;
        public float DismountVanKmh = 8f, DismountDelay = 1.5f, DismountRange = 25f, CrewReturnDistance = 20f;

        [Header("Heat (hidden, per crowd district)")]
        public float HeatStun = 8f, HeatCapture = 15f, HeatDrag = 8f, HeatHitCop = 20f, HeatRam = 10f;
        [Tooltip("Seconds per heat point of decay (100 -> 0 in about 13 minutes).")]
        public float HeatDecaySeconds = 8f;
        public float HighHeat = 60f;
        [Tooltip("Optional: heat never cools below this in these districts (richer districts, more police: try old town 10, elite " +
                 "15). Off (0) by default: a floor also raises those districts' patrol loop scores and moves the day patrol.")]
        public string[] HeatFloorDistricts = { "old_town", "elite" };
        public float[] HeatFloors = { 0f, 0f };
        public int MaxExtraOfficers = 2;

        [Header("Officers on foot")]
        public float ThinSpeed = 7.4f, FatSpeed = 5.6f, FatAnimFactor = 1.35f, FatTripPerSecond = 0.04f, TripTime = 1.2f;
        public float OfficerRangeFactor = 1.3f;
        public float ChaseStartRange = 40f, ChaseDirectRange = 20f, ChaseLoseDistance = 25f, ChaseLoseTime = 5f;
        public float BeatWindup = 0.45f, BeatReach = 1.6f, BeatStart = 1.4f, BeatCooldown = 1.2f, BeatSide = 5f, BeatUp = 2.5f;
        public int HitsToArrest = 3;
        public float ArrestWindow = 12f;
        public int ArrestCashPercent = 10;
        public float WakeChaseRange = 30f, LookAroundTime = 10f;

        [Header("Shooting (rare)")]
        public float ShootMin = 6f, ShootMax = 15f, ShootAim = 1f, ShootHitChance = 0.5f, ShootCooldown = 12f;
        [Tooltip("At night (heat below HighHeat) an officer may shoot at all in this share of his foot chases (one roll per " +
                 "chase); by day only at HighHeat (canon 77: mostly they beat, rarely shoot).")]
        [Range(0f, 1f)] public float NightShootChance = 0.25f;

        /// <summary>The presence row of a district id (DefaultPresence when it has none).</summary>
        public PolicePresenceDef PresenceOf(string district)
        {
            if (!string.IsNullOrEmpty(district) && Presence != null)
                foreach (PolicePresenceDef p in Presence)
                    if (p != null && p.District == district) return p;
            return DefaultPresence ?? new PolicePresenceDef();
        }

        /// <summary>A district patrol loops keep out of (Patrol weight below PatrolMinPresence).</summary>
        public bool LowPresence(string district) => PresenceOf(district).Patrol < PatrolMinPresence;

        /// <summary>The police car's chase numbers from the STOCK van's pace numbers (torque N m, top speed km/h, wheel radius
        /// m, mass kg, damping) and the van's upgrade steps (null = VanUpgradeConfig's built-in defaults): the reference van at
        /// RefEngine/RefBrakes/RefHandlingLevel x the ratios. PoliceDirector (runtime) and PoliceBaker use this one rule.</summary>
        public PoliceBalance Balance(float stockTorque, float stockTopKmh, float wheelRadius, float mass, float damping,
                                     OnlyVolunteers.Vehicles.VanUpgradeConfig upgrades) =>
            VanAt(stockTorque, stockTopKmh, wheelRadius, mass, damping, upgrades, RefEngineLevel, RefBrakesLevel, RefHandlingLevel);

        /// <summary>The van at these upgrade levels (the same steps VanUpgrades applies: torque x TorqueMultiplier, top speed +
        /// MaxSpeedBonusKmh; a clean, fast driver's cornering VanFastLateral x SidewaysGripMultiplier and braking VanFastBrake x
        /// the lower of BrakeTorque / ForwardGrip multipliers), and that van x the balance ratios.</summary>
        public PoliceBalance VanAt(float stockTorque, float stockTopKmh, float wheelRadius, float mass, float damping,
                                   OnlyVolunteers.Vehicles.VanUpgradeConfig upgrades, int engineLevel, int brakesLevel, int handlingLevel)
        {
            var engine = OnlyVolunteers.Vehicles.VanUpgradeConfig.EngineAt(upgrades, engineLevel);
            var brakes = OnlyVolunteers.Vehicles.VanUpgradeConfig.BrakesAt(upgrades, brakesLevel);
            var handling = OnlyVolunteers.Vehicles.VanUpgradeConfig.HandlingAt(upgrades, handlingLevel);
            var b = new PoliceBalance
            {
                Engine = engineLevel, Brakes = brakesLevel, Handling = handlingLevel,
                VanTopKmh = stockTopKmh + engine.MaxSpeedBonusKmh,
                VanA = 0.9f * stockTorque * engine.TorqueMultiplier / (Mathf.Max(0.1f, wheelRadius) * Mathf.Max(1f, mass)),
                VanK = damping,
                VanLateral = VanFastLateral * handling.SidewaysGripMultiplier,
                VanBrake = VanFastBrake * Mathf.Min(brakes.BrakeTorqueMultiplier, brakes.ForwardGripMultiplier),
            };
            b.TopKmh = b.VanTopKmh * TopSpeedRatio;
            b.A = b.VanA * AccelRatio;
            b.K = b.VanK * AccelRatio;
            b.Lateral = b.VanLateral * CornerGripRatio;
            b.Brake = b.VanBrake * BrakeRatio;
            return b;
        }

        public static float Kmh(float kmh) => kmh / 3.6f;
    }

    /// <summary>A van at upgrade levels Engine / Brakes / Handling (Van*) and the police car balanced against it (the rest;
    /// PoliceConfig.Balance = the reference van): top speed km/h, full-throttle a(v) = A - K v (m/s^2), cornering and
    /// braking m/s^2.</summary>
    public struct PoliceBalance
    {
        public int Engine, Brakes, Handling;
        public float VanTopKmh, VanA, VanK, VanLateral, VanBrake;
        public float TopKmh, A, K, Lateral, Brake;

        public string Levels => $"{Engine}/{Brakes}/{Handling}";
    }
}
