#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using System.Text;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Police;
using OnlyVolunteers.Vehicles;
using Unity.Profiling;
using Unity.Profiling.LowLevel.Unsafe;
using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using Handle = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Handle;

namespace OnlyVolunteers.Characters.Npc.Dev
{
    // T1 + T2 of stage 9 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §6), steps 1 to 3.
    // Step 1: r0 build (11 bodies, 10 joints, 13 colliders, 28 kg, Animator off; build time INFO), r1 knockdown (no NaN,
    // every body < 0.2 m/s within 4 s; asleep INFO), r5 grab any part (every part, the chest's collar/chest/belly and a
    // foot: the part, its handle and its hint; two hands on one part; a fourth holder refused), r3 one hand lifts the head
    // top +0.4 m within 1.5 s, r4 one hand on the pelvis lifts it <= 0.15 m (bad handle), r2 a hand pulls a wrist at the
    // cap for 2 s, every joint gap <= 3 cm, drag by the collar at walking speed (INFO), r7 a running NPC hit from behind
    // keeps its momentum, r9 with the cap at 2 the third knockdown gets the capsule, r10 F10's capsule mode gives the
    // stage-1 capsule.
    // Step 3: r8a / r8b waking on its back / belly gets up with GetUp_Back / GetUp_Belly (NpcGetUp: standing and free in
    // time, the clip seen, no pop, the CharacterController on at the clip's Stable point, up where its hips lay), r14 waking
    // loaded in the bay sits up there (SitUp_Cargo, then Cargo_Sit_Idle, under the roof, no pop); r6b (rear doors alone)
    // now runs over the van's NPC body slide.
    // Step 2 (assists A2-A4 on, the van loads ragdolls): r5b two hands (collar + ankle, standing) lift it on open ground
    // (the design's r5: the pelvis >= 0.3 m clear within 1.5 s, each hand's mean <= 160 N), r6 one hand loads it alone
    // through the sliding door in one go
    // (the h1 path of Map/Scripts/Dev/NpcLoadingTest: <= 12 s, mean hand force <= 195 N, grip kept), r6b the same through
    // the rear doors (loaded <= 12 s; force INFO, as the capsule's h2), r7 two hands, collar + ankle, through the rear
    // doors (whole body >= 0.3 m off the ground within 1.5 s, loaded <= 6 s, each hand's mean <= 160 N), r12 a ride with
    // two bodies (one on the other), doors shut, 40 km/h S-turns for 10 s (both stay loaded and in the bay, no body faster
    // than 6 m/s relative to the van; peak speeds and relative accelerations INFO), r11 a sitter in the bay hit with the
    // fist lies down there as the ragdoll and stays loaded, r13 a sitter tumbling out of the sliding door at 20 km/h
    // (GreyboxNpc.LeaveCargo(true), as GreyboxVanCargo.GetOut calls it) is a ragdoll that lands outside. T2 (INFO):
    // PerfAsleep copies of a crowd NPC lying asleep plus PerfAwake dropped awake (three times) for PerfFrames frames at
    // time scale 1: the physics simulation's ms per frame (ProfilerRecorder), the knockdown build time.
    // Step 4 (the Groggy struggle on the joint drives, the hop out of a standing van, the police trip; design §4.3-§4.6):
    // r17b the r5b pair lift with A Groggy (the carried struggle; kick tears off for the check), r15 kicks against one
    // holder (kicks every 0.45-0.55 s for 10 s, the hand taking hold again after each tear: no hold lost except to a tear,
    // the tear count plausible for KickTearChance by the binomial at 99 %), r16 a Groggy body nobody holds crawls away from
    // the threat (CrawlMin..CrawlMax m/s, within 45 degrees, joints whole), r16b a fist on the Groggy crawler stuns it again
    // (Out, limp, Condition - ReStunConditionCost), r19 a fat police officer (a copy of a crowd NPC) trips through the
    // ragdoll and gets up with the clip, not Down meanwhile, no incident, back in his state; r17a the r6 solo side-door
    // load with A Groggy (tears off): loaded <= 12 s, grip kept, mean force within 10 % of the same run's limp r6; r13 now
    // tumbles from the escape scramble (Escaping); r18 B sitting in the bay of the parked van gets out of the opened
    // sliding door with the hop (GreyboxNpc.JumpOut) and runs. Review fix (GPT review 2026-10-07, finding 8): r12 needs
    // both doors shut before the ride (after one re-lay of the bodies along the bay if a limb kept a door open) and shut
    // all through it.
    // Step 5 (NpcAnimDriver, the generated controller): r20 one writer: every tick of the run, for A, B, C and the r19
    // officer, the Animator stays off while the ragdoll is built, and while NpcGetUp owns it (a get-up, the officer's
    // get-up after the trip, the hop out of the van) the driver writes nothing and the contract's parameters stay as
    // NpcGetUp's start wrote them;
    // r21 the Animator shows each situation's state: fleeing after a get-up (the run), lying as the capsule (Down, or a
    // hit react), sitting in the van (the sit idle), escaping (the scramble or the run), the officer leaving (walking).
    // Hands are real PhysicsGrabbers (ScriptDriven, as in NpcLoadingTest); in the van checks a hand stands somewhere
    // (crouched in the bay: eye 0.85 m over the floor, or standing: 1.85 m), the hold distance follows its target no
    // faster than a mouse wheel (1 m/s) and within 0.6-2.5 m.
    // Sandbox: ground 300 m above the first test NPC, turned to the van's yaw (in quarter turns until the ride's path is
    // dry); three free NPCs (not police) are taken, their crowd walkers released, and at the end laid down where they
    // stood to wake up there; the van is parked 15 m to the side (kinematic, i.e. the handbrake), driven for the ride, and
    // put back with its doors and sea tracker; the T2 copies are destroyed.
    // Run: OnlyVolunteers/Characters/Npc/Dev/Ragdoll Smoke Test (enters Play, runs, leaves) in Map_Look_v12_Play (or
    // Map_Greybox_v12), or add this component in Play mode. Results: [RagdollSmokeTest] lines and the statics Done /
    // Passed / LastReport / Progress (MCP polls them). About 110 s of game time, ~45 s real at TimeScale 3.
    public sealed class RagdollSmokeTest : MonoBehaviour
    {
        public static bool Done;
        public static bool Passed;
        public static string LastReport = "";
        public static string Progress = "";

        [Tooltip("Time.timeScale while the test runs (T2 runs at 1). The physics step stays 1/60 s.")]
        public float TimeScale = 3f;
        public int Seed = 9;
        [Tooltip("Leave Play mode when done (the editor menu sets it when it entered Play mode itself).")]
        public bool ExitWhenDone;
        [Tooltip("T2: ragdolls lying asleep and ragdolls dropped awake while the physics time is recorded.")]
        public int PerfAsleep = 40;
        public int PerfAwake = 10;
        public int PerfFrames = 300;

        private const string Tag = "[RagdollSmokeTest]";
        private const float SandboxLift = 300f;
        private const float WalkSpeed = 4.7f; // KccFirstPersonInput.WalkSpeed

        // The van (van-local numbers from VanSetupBuilder / NpcLoadingTest: the floor 0.55, the floor edge at the sliding
        // door x 0.94, the rear bumper's outer top edge z -2.38, the bay x +-0.80, z -2.19..0.42).
        private const float VanSide = 15f;         // m: the van parks this far to the side of the sandbox centre
        private const float RidePath = 240f;       // m of dry ground the ride may need ahead of the van
        private const float StandEye = 1.85f, CrouchEye = 0.85f;
        private const float MinHold = 0.6f, MaxHold = 2.5f;
        private const float MaxWheelSpeed = 1.0f, WheelPlan = 0.95f;
        private const float SlideEdgeX = 0.94f, RearEdgeZ = -2.38f;
        private const float CarrySpeed = 1.2f, Carry = 1.12f, CarryInside = 0.40f, RideDrop = 0.30f;
        private const float RideSide = 0.90f, RideRear = 0.95f;
        private const float SoloLimit = 12f, PairLimit = 6f;        // s from the first grab to "loaded" (§3.5)
        private const float SoloForce = 195f, PairForce = 160f;     // N, mean per hand (§3.5)
        private const float PairClear = 0.3f, PairClearTime = 1.5f; // m off the ground within s (§3.5)
        private const float RideKmh = 40f, RideSeconds = 10f, RidePeriod = 4f, RideSteer = 0.3f;
        private const float ExplodeSpeed = 6f;      // m/s relative to the van: faster is an explosion, not a ride
        // m/s after a blow (r11, r13): the fist's own 42 N·s gives the struck torso part ~7.5 m/s before the joints share
        // it (the first run's 6 m/s limit here was the ride's, which has no blow); a light limb struck would reach ~30.
        private const float BlowSpeed = 10f;
        // Step 3 (get-up and sit-up clips): free within this many seconds of waking (settle <= 1 s + a 2.5-2.6 s clip),
        // no visible pop (m between two drawn frames: a broken snapshot jumps by the root move, 0.2-1 m), and sitting in the
        // van the head top stays this far under the bay's 1.43 m roof at most.
        private const float GetUpLimit = 4.5f, PopLimit = 0.3f, SitHeadLimit = 1.35f;
        // In the blend window (the clips hold their first pose ~0.2-0.45 s for it) the head may move this far at most: the
        // blend lifts the body to the clip's start (0.1-0.25 m); a wrong facing would swing it round, 1-2 m.
        private const float BlendWindow = 0.35f, TravelLimit = 0.5f;
        private const int FeetMask = 1 | OvLayers.VehicleMask | (1 << OvLayers.VehicleInterior);
        private const int GrabRayMask = ~(1 << OvLayers.VehicleInterior); // PhysicsGrabber.TryAcquire's
        // Step 4: r15's length (game s) and kick pace; r16's crawl speed range (m/s, design-free: "comic but readable", the
        // profile aims at 0.5) and window; r19 / r18: free again within these (s) of the trip / of the door opening; r17a:
        // the Groggy solo load's mean force may be this much above the same run's limp r6.
        private const float KickTearSeconds = 10f, CrawlMin = 0.2f, CrawlMax = 1.0f, CrawlWindow = 3f;
        private const float TripLimit = 6f, JumpOutLimit = 5f, GroggyForceMargin = 1.1f;
        private static readonly Vector2 TestKickPace = new(0.45f, 0.55f);

        private static readonly FieldInfo ViewCameraField =
            typeof(PhysicsGrabber).GetField("viewCamera", BindingFlags.NonPublic | BindingFlags.Instance);
        private static readonly FieldInfo ProfileField =
            typeof(PhysicsGrabber).GetField("profile", BindingFlags.NonPublic | BindingFlags.Instance);
        private static readonly WaitForFixedUpdate Fixed = new();

        private sealed class Hand
        {
            public GameObject Root;
            public Camera View;
            public PhysicsGrabber Grabber;
            public bool Expect; // a hold that must not be lost
            public bool Lost;
            public readonly List<float> Forces = new();
            // Van checks: where the hand stands, its eye height, what it holds.
            public Vector3 Stand, Target;
            public float Eye = StandEye;
            public NpcRagdoll Held;
            public int Slot = -1;
            public readonly List<float> Lags = new();
        }

        private struct Leg
        {
            public Hand Hand;
            public Vector3 FromTarget, ToTarget, FromStand, ToStand;
        }

        private sealed class Taken
        {
            public GreyboxNpc Npc;
            public Vector3 Home;
            public float Yaw;
        }

        private readonly List<Taken> _taken = new();
        private readonly List<Hand> _hands = new();
        private readonly HashSet<GreyboxNpc> _keepDown = new();
        // Step 4: kept Groggy (StunLeft 30 of 100) instead of Out; kick settings changed for a check (restored after).
        private readonly HashSet<GreyboxNpc> _keepGroggy = new();
        private readonly Dictionary<GreyboxNpc, (Vector2 interval, float[] tear)> _kicks0 = new();
        private float _soloLimpForce = -1f; // r6's mean force (limp), r17a's reference
        private Action<GreyboxNpc, NpcIncident> _incidentProbe;
        private GreyboxNpc _a, _b, _c;
        private Vector3 _o; // the sandbox's centre, on its ground
        private GameObject _ground;
        private GrabPhysicsProfile _finder;
        private NpcBodyMode _mode0;
        private int _cap0;
        private bool _trackAll0, _statics;
        private readonly StringBuilder _report = new();
        private int _checks, _passes, _logErrors, _lostGrips;
        private bool _nan;
        private string _abort;
        private bool _finished;
        private Action _observe; // per-tick bookkeeping of the running check

        // The van.
        private GreyboxVanCargo _cargo;
        private VanController _vanCtl;
        private GreyboxVanSeat _seat;
        private VanCargoSpace _space;
        private Rigidbody _van;
        private SeaReturnTracker _vanTracker;
        private bool _vanTrackerOn, _vanMoved, _vanKinematic0, _doorsTouched, _slideOpen0, _rearOpen0;
        private Vector3 _vanPos0;
        private Quaternion _vanRot0;
        private Vector3 _vo;        // the van root on the sandbox ground
        private Quaternion _yaw = Quaternion.identity;
        private string _vanSkip;    // why the van checks cannot run

        // T2.
        private readonly List<GameObject> _clones = new();
        private GameObject _cloneHolder;
        private int _fixedSteps;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Done = false;
            Passed = false;
            LastReport = "";
            Progress = "";
        }

        private void Awake()
        {
            Done = false;
            Passed = false;
            LastReport = "";
            Progress = "starting";
        }

        private void Start()
        {
            Application.logMessageReceived += OnLog;
            StartCoroutine(Drive());
        }

        private void FixedUpdate() => _fixedSteps++;

        private void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            if (_finished) return;
            _finished = true;
            Teardown();
            Line($"{Tag} ABORTED: the runner was destroyed before the end");
            LastReport = _report.ToString();
            Progress = "aborted";
            Passed = false;
            Done = true;
        }

        private void OnLog(string message, string stack, LogType type)
        {
            if (message != null && message.StartsWith(Tag, StringComparison.Ordinal)) return;
            if ((type == LogType.Error || type == LogType.Exception || type == LogType.Assert) && stack != null &&
                stack.Contains("OnlyVolunteers.") && !stack.Contains("UnityEditor."))
                _logErrors++;
        }

        // Runs Main with nested IEnumerators inline; every yield is a WaitForFixedUpdate (or null: one frame, T2). An
        // exception ends the run with a FAIL instead of leaving NPCs in the sky.
        private IEnumerator Drive()
        {
            var stack = new Stack<IEnumerator>();
            stack.Push(Main());
            while (stack.Count > 0)
            {
                IEnumerator top = stack.Peek();
                bool more;
                try
                {
                    more = top.MoveNext();
                }
                catch (Exception e)
                {
                    Debug.LogException(e);
                    _abort = $"exception in '{Progress}': {e.GetType().Name}: {e.Message}";
                    break;
                }
                if (!more)
                {
                    stack.Pop();
                    continue;
                }
                if (top.Current is IEnumerator child)
                {
                    stack.Push(child);
                    continue;
                }
                yield return top.Current;
            }
            Finish();
        }

        private IEnumerator Main()
        {
            for (int i = 0; i < 5; i++) yield return Fixed;
            if (!Setup()) yield break;
            yield return Build();
            yield return Settle();
            yield return GrabAny();
            yield return HeadLift();
            yield return PelvisLift();
            yield return Stretch();
            yield return Punch();
            yield return Drag();
            yield return PairLift(false);
            yield return PairLift(true);
            yield return KickTear();
            yield return CrawlCheck();
            yield return Restun();
            yield return GetUp(true);
            yield return GetUp(false);
            yield return Momentum();
            yield return CapCheck();
            yield return CapsuleMode();
            yield return TripCheck();
            yield return Van();
            AnimContract();
            yield return Perf();
        }

        // ---------- Setup and teardown ----------

        private bool Setup()
        {
            Progress = "setup";
            if (ViewCameraField == null || ProfileField == null) return Abort("PhysicsGrabber has no viewCamera/profile fields");
            var picks = new List<GreyboxNpc>();
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !npc.isActiveAndEnabled || npc.State != NpcState.Free || npc.InCargo || PoliceOfficer.IsOfficer(npc)) continue;
                if (npc.Ragdoll == null || !npc.Ragdoll.Ready || npc.Body == null) continue;
                picks.Add(npc);
                if (picks.Count == 3) break;
            }
            if (picks.Count < 3)
            {
                string why = GreyboxNpc.All.Count > 0 && GreyboxNpc.All[0] != null && GreyboxNpc.All[0].Ragdoll != null
                    ? GreyboxNpc.All[0].Ragdoll.Problem : "no NPCs";
                return Abort($"need 3 free NPCs with a ready ragdoll, found {picks.Count} ({why})");
            }
            _a = picks[0];
            _b = picks[1];
            _c = picks[2];
            _o = _a.transform.position + Vector3.up * SandboxLift;
            GreyboxPawn pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            if (pawn != null && Flat(pawn.Position - _o).magnitude < 40f)
            {
                Vector3 away = Flat(_o - pawn.Position);
                _o += (away.sqrMagnitude > 1e-4f ? away.normalized : Vector3.forward) * 80f;
            }
            if (SeaReturnZone.InSea(_o)) return Abort("the sandbox would be over the sea");

            // The frame: the van's yaw, turned in quarter turns until the van's place, the ride ahead of it and the NPC
            // area are all dry (SeaReturnZone is flat: it would eject the cargo or move free NPCs back to land).
            _cargo = FindAnyObjectByType<GreyboxVanCargo>();
            Quaternion yaw = Quaternion.identity;
            if (_cargo != null)
            {
                Vector3 f = Flat(_cargo.transform.forward);
                if (f.sqrMagnitude > 1e-4f) yaw = Quaternion.LookRotation(f.normalized);
            }
            bool dry = false;
            for (int turn = 0; turn < 4 && !dry; turn++)
            {
                Quaternion y = Quaternion.Euler(0f, 90f * turn, 0f) * yaw;
                if (!PathDry(y)) continue;
                _yaw = y;
                dry = true;
            }
            if (_cargo == null) _vanSkip = "no GreyboxVanCargo in the scene";
            else if (!dry) _vanSkip = "no dry ground for the van ride around this sandbox";
            _vo = _o + _yaw * new Vector3(VanSide, 0f, 0f);

            foreach (GreyboxNpc npc in picks)
            {
                _taken.Add(new Taken { Npc = npc, Home = npc.transform.position, Yaw = npc.transform.eulerAngles.y });
                if (npc.TryGetComponent(out CrowdWalker walker)) walker.Release();
            }
            // One box of ground: the NPC area (+-30 m), the van's place and the ride ahead of it.
            _ground = new GameObject("RagdollSmokeTest_Ground") { layer = 0 };
            _ground.transform.SetPositionAndRotation(_o + _yaw * new Vector3(VanSide * 0.5f, -0.5f, RidePath * 0.5f - 20f), _yaw);
            _ground.AddComponent<BoxCollider>().size = new Vector3(140f, 1f, RidePath + 120f);
            Physics.SyncTransforms();

            PhysicsGrabber player = FindAnyObjectByType<PhysicsGrabber>(FindObjectsInactive.Include);
            _finder = player != null ? ProfileField.GetValue(player) as GrabPhysicsProfile : null;
            if (_finder == null) _finder = _a.Body.Profile;
            for (int i = 0; i < 2; i++) _hands.Add(NewHand(i));

            _mode0 = NpcRagdoll.Mode;
            _cap0 = NpcRagdoll.Cap;
            _trackAll0 = NpcRagdoll.TrackAll;
            _statics = true;
            NpcRagdoll.Mode = NpcBodyMode.Ragdoll;
            NpcRagdoll.TrackAll = true; // the sandbox is far from the player
            UnityEngine.Random.InitState(Seed);
            Time.timeScale = Mathf.Max(0.1f, TimeScale);
            NpcRagdollProfile p = _a.Ragdoll.Profile;
            Line(Inv($"{Tag} start: {_a.name}, {_b.name}, {_c.name}; profile '{p.name}' {p.TotalMass:0.0} kg; hand finder '{_finder.name}'; ") +
                 Inv($"handles {p.GoodForce.x:0}/{p.MediumForce.x:0}/{p.BadForce.x:0} N, hold mass {(p.UseHoldMass ? p.HoldMass : 0f):0} kg; ") +
                 Inv($"assists A2 {(p.SpreadForce ? p.SpreadShare : 0f):0.##} A3 {p.ReliefFor(1):0.##}/{p.ReliefFor(2):0.##}/{p.ReliefFor(3):0.##} ") +
                 Inv($"A4 {(p.CarryTone ? "on" : "off")}; F10 default {_mode0}; timeScale {Time.timeScale:0.#}") +
                 (_vanSkip != null ? $"; van checks skipped: {_vanSkip}" : ""));
            return true;
        }

        private bool PathDry(Quaternion yaw)
        {
            Vector3 vo = _o + yaw * new Vector3(VanSide, 0f, 0f);
            for (float z = -10f; z <= RidePath; z += 15f)
                for (float x = -20f; x <= 20f; x += 20f)
                    if (SeaReturnZone.InSea(vo + yaw * new Vector3(x, 0f, z))) return false;
            for (float x = -50f; x <= 10f; x += 10f)
                for (float z = -50f; z <= 10f; z += 10f)
                    if (SeaReturnZone.InSea(_o + yaw * new Vector3(x, 0f, z))) return false;
            return true;
        }

        private bool Abort(string why)
        {
            _abort = why;
            return false;
        }

        private Hand NewHand(int n)
        {
            var root = new GameObject($"RagdollTestHand_{n}");
            root.SetActive(false); // Awake needs the profile set first
            var eye = new GameObject("Eye");
            eye.transform.SetParent(root.transform, false);
            var view = eye.AddComponent<Camera>();
            view.enabled = false;
            var grabber = root.AddComponent<PhysicsGrabber>();
            ViewCameraField.SetValue(grabber, view);
            ProfileField.SetValue(grabber, _finder);
            root.SetActive(true);
            grabber.ScriptDriven = true;
            return new Hand { Root = root, View = view, Grabber = grabber };
        }

        private void Teardown()
        {
            Time.timeScale = 1f;
            _observe = null;
            foreach (Hand h in _hands)
            {
                if (h.Grabber != null) h.Grabber.ScriptRelease();
                if (h.Root != null) Destroy(h.Root);
            }
            _hands.Clear();
            _keepDown.Clear();
            _keepGroggy.Clear();
            foreach (KeyValuePair<GreyboxNpc, (Vector2 interval, float[] tear)> kv in _kicks0)
                if (kv.Key != null)
                {
                    kv.Key.KickInterval = kv.Value.interval;
                    kv.Key.KickTearChance = kv.Value.tear;
                }
            _kicks0.Clear();
            if (_incidentProbe != null) GreyboxNpc.Incident -= _incidentProbe;
            _incidentProbe = null;
            foreach (GameObject clone in _clones)
                if (clone != null) Destroy(clone);
            _clones.Clear();
            if (_cloneHolder != null) Destroy(_cloneHolder);
            // Back where they stood: lying there, waking a second later (a free one is simply put back). Unloaded first,
            // so the van's teleport back below does not carry them along.
            foreach (Taken t in _taken)
            {
                GreyboxNpc npc = t.Npc;
                if (npc == null) continue;
                npc.InCargo = false;
                npc.Carrier = null;
                Vector3 facing = Quaternion.Euler(0f, t.Yaw, 0f) * Vector3.forward;
                if (npc.Ragdoll != null && npc.Ragdoll.Active)
                {
                    npc.Ragdoll.UnpinAll();
                    npc.Ragdoll.PlaceLying(t.Home, facing, true);
                }
                else if (npc.Body != null && npc.Body.Active && npc.Body.Rigidbody != null)
                {
                    if (npc.State != NpcState.Down)
                        npc.Hit(WeaponStun.Fist, HitZone.Torso, npc.Center + Vector3.up, npc.Center); // a sitter lies down first
                    if (npc.Ragdoll != null && npc.Ragdoll.Active) npc.Ragdoll.PlaceLying(t.Home, facing, true);
                    else
                    {
                        npc.Body.UnpinAll();
                        Rigidbody rb = npc.Body.Rigidbody;
                        Vector3 p = t.Home + Vector3.up * (npc.Body.Radius + 0.05f);
                        Quaternion r = Quaternion.LookRotation(Vector3.up, facing);
                        rb.position = p;
                        rb.rotation = r;
                        rb.linearVelocity = Vector3.zero;
                        rb.angularVelocity = Vector3.zero;
                        npc.transform.SetPositionAndRotation(p, r);
                    }
                }
                else PutAt(npc, t.Home, t.Yaw);
                npc.InCargo = false;
                npc.Carrier = null;
                if (npc.State == NpcState.Down) npc.StunLeft = Mathf.Min(npc.StunLeft, 1f);
            }
            _taken.Clear();
            if (_vanMoved && _van != null)
            {
                if (_vanCtl != null)
                {
                    _vanCtl.Throttle = 0f;
                    _vanCtl.Steer = 0f;
                    _vanCtl.Handbrake = true;
                }
                if (!_van.isKinematic)
                {
                    _van.linearVelocity = Vector3.zero;
                    _van.angularVelocity = Vector3.zero;
                }
                _van.position = _vanPos0;
                _van.rotation = _vanRot0;
                _van.transform.SetPositionAndRotation(_vanPos0, _vanRot0);
                _van.isKinematic = _vanKinematic0;
                if (!_vanKinematic0)
                {
                    _van.linearVelocity = Vector3.zero;
                    _van.angularVelocity = Vector3.zero;
                }
            }
            _vanMoved = false;
            if (_vanTracker != null) _vanTracker.enabled = _vanTrackerOn;
            if (_doorsTouched && _cargo != null)
            {
                if (_cargo.DoorOpen(0) != _slideOpen0) _cargo.ToggleDoor(0);
                if (_cargo.DoorOpen(1) != _rearOpen0) _cargo.ToggleDoor(1);
                _doorsTouched = false;
            }
            if (_statics)
            {
                NpcRagdoll.Mode = _mode0;
                NpcRagdoll.Cap = _cap0;
                NpcRagdoll.TrackAll = _trackAll0;
                _statics = false;
            }
            if (_ground != null) Destroy(_ground);
            Physics.SyncTransforms();
        }

        private void Finish()
        {
            if (_finished) return;
            _finished = true;
            if (_abort != null) Line($"{Tag} FAIL run aborted: {_abort}");
            Check("global", _abort == null && _logErrors == 0 && !_nan && _lostGrips == 0,
                Inv($"errors={_logErrors} nan={(_nan ? 1 : 0)} lostGrips={_lostGrips}"));
            Teardown();
            int failed = _checks - _passes;
            Passed = failed == 0;
            Line(Passed ? $"{Tag} DONE {_passes}/{_checks} PASS" : $"{Tag} DONE {_passes}/{_checks} FAIL {failed}");
            LastReport = _report.ToString();
            Progress = "done";
            Done = true;
#if UNITY_EDITOR
            if (ExitWhenDone) UnityEditor.EditorApplication.isPlaying = false;
#endif
            Destroy(gameObject);
        }

        // ---------- r0, r1: going down ----------

        private IEnumerator Build()
        {
            Progress = "r0 build";
            PutAt(_a, _o, 0f);
            yield return Idle(0.4f); // standing a moment: the bone motion tracker has samples
            _a.Hit(WeaponStun.Fist, HitZone.Torso, _a.transform.position + _a.transform.forward, _a.Center);
            _keepDown.Add(_a);
            KeepStunned();
            NpcRagdoll r = _a.Ragdoll;
            double ms = NpcRagdoll.LastBuildMilliseconds;
            int bodies = 0, joints = 0, colliders = 0, wrongLayer = 0;
            float mass = 0f;
            foreach (Rigidbody rb in _a.GetComponentsInChildren<Rigidbody>())
            {
                bodies++;
                mass += rb.mass;
            }
            joints = _a.GetComponentsInChildren<ConfigurableJoint>().Length;
            foreach (Collider c in _a.GetComponentsInChildren<Collider>())
            {
                if (!c.enabled) continue; // the CharacterController, off while down
                colliders++;
                if (c.gameObject.layer != OvLayers.NpcBody) wrongLayer++;
            }
            Animator animator = _a.GetComponentInChildren<Animator>();
            bool ok = r.Active && !_a.Body.Active && _a.State == NpcState.Down && bodies == 11 && joints == 10 &&
                      colliders == 13 && r.Colliders.Count == 13 && Mathf.Abs(mass - 28f) <= 0.05f && wrongLayer == 0 &&
                      animator != null && !animator.enabled && NpcRagdoll.ActiveCount == 1;
            Check("r0 build", ok, Inv($"bodies={bodies} joints={joints} colliders={colliders} mass={mass:0.00} kg wrongLayer={wrongLayer} ") +
                                  Inv($"animatorOff={(animator != null && !animator.enabled ? 1 : 0)} live={NpcRagdoll.ActiveCount} build={ms:0.00} ms (INFO, budget 0.5)"));
        }

        private IEnumerator Settle()
        {
            Progress = "r1 knockdown";
            NpcRagdoll r = _a.Ragdoll;
            float t0 = Time.fixedTime, settled = -1f, asleep = -1f, fall = 0f;
            Vector3 start = r.Landmark(NpcLandmark.Pelvis);
            for (int k = 0; k < Ticks(6f) && (settled < 0f || asleep < 0f); k++)
            {
                yield return Fixed;
                AfterTick();
                float fastest = 0f;
                bool sleeping = true;
                for (int i = 0; i < r.PartCount; i++)
                {
                    Rigidbody rb = r.BodyOf(i);
                    fastest = Mathf.Max(fastest, rb.linearVelocity.magnitude);
                    sleeping &= rb.IsSleeping();
                }
                if (settled < 0f && fastest < 0.2f) settled = Time.fixedTime - t0;
                if (asleep < 0f && sleeping) asleep = Time.fixedTime - t0;
                fall = Mathf.Max(fall, start.y - r.Landmark(NpcLandmark.Pelvis).y);
            }
            Check("r1 knockdown", !_nan && settled >= 0f && settled <= 4f,
                Inv($"every body < 0.2 m/s after {Seconds(settled)} (limit 4 s); asleep after {Seconds(asleep)} (INFO, aim 6 s); pelvis fell {fall:0.00} m"));
        }

        // ---------- r5: any part ----------

        private IEnumerator GrabAny()
        {
            Progress = "r5 grab any part";
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            var misses = new List<string>();
            int tried = 0;
            Hand h = _hands[0];
            // Every part from above at its capsule's middle; the chest at its collar, chest and belly; the left foot box.
            var points = new List<(string label, int part, Vector3 point, Handle handle, string hint)>();
            for (int i = 0; i < r.PartCount; i++)
            {
                NpcRagdollProfile.Part part = p.Parts[i];
                if (part.Kind == Kind.Chest) continue;
                string hint = part.Handle == Handle.Bad ? part.Hint + " — тяжело" : part.Hint;
                points.Add((part.Name, i, r.PartCenter(i), part.Handle, hint));
            }
            // The chest's collar band beside the neck (the head capsule covers the middle of it), and the belly.
            int chest = p.IndexOf(Kind.Chest);
            Vector3 chestUp = ChestUp(r, chest), lateral = ChestLateral(r, chest);
            float cr = p.Parts[chest].Radius;
            Vector3 cc = r.PartCenter(chest);
            points.Add(("Chest front", chest, cc + lateral * 0.15f + chestUp * (0.4f * cr), Handle.Good, "грудь"));
            points.Add(("Chest belly", chest, cc - chestUp * (0.5f * cr), Handle.Bad, "живот — тяжело"));
            int calf = p.IndexOf(Kind.Calf, NpcSide.Left);
            points.Add(("Foot_L", calf, FootBoxCentre(r, calf), Handle.Good, "ступню"));
            points.Add(("Collar (back)", chest, Vector3.zero, Handle.Good, "ворот")); // last: turns the body over
            foreach ((string label, int part, Vector3 probe, Handle handle, string hint) in points)
            {
                Vector3 point = probe;
                if (label == "Collar (back)")
                {
                    // The collar from behind: the body turned onto its belly.
                    r.PlaceLying(_o, Vector3.right, false);
                    yield return Idle(0.6f);
                    cc = r.PartCenter(chest);
                    point = cc + ChestLateral(r, chest) * 0.15f + ChestUp(r, chest) * (0.4f * cr);
                }
                tried++;
                if (!Above(point, out RaycastHit hit, out Vector3 eye))
                {
                    misses.Add(label + ": nothing above");
                    continue;
                }
                string seen = r.GrabHintName(hit.collider, hit.point);
                Aim(h, eye, hit.point);
                bool held = h.Grabber.ScriptGrab();
                int slot = SlotOf(r, h.Grabber);
                NpcRagdollPart got = held && h.Grabber.GrabbedBody != null ? h.Grabber.GrabbedBody.GetComponent<NpcRagdollPart>() : null;
                if (got == null || slot < 0) misses.Add($"{label}: no hold");
                else
                {
                    if (got.Index != part) misses.Add($"{label}: took {p.Parts[got.Index].Name}");
                    if (r.Claims[slot].Handle != handle) misses.Add($"{label}: handle {r.Claims[slot].Handle}, not {handle}");
                    if (r.Claims[slot].Part != got.Index) misses.Add($"{label}: claim on another part");
                }
                if (seen != hint) misses.Add($"{label}: hint '{seen}', not '{hint}'");
                h.Grabber.ScriptRelease();
                yield return Fixed;
            }
            // Two hands on the same part, then a third holder (an F9 pin) and a fourth, refused.
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            int head = p.IndexOf(Kind.Head);
            bool two = Above(r.PartCenter(head), out RaycastHit headHit, out Vector3 headEye);
            if (two)
            {
                Aim(_hands[0], headEye, headHit.point);
                Aim(_hands[1], headEye + Vector3.forward * 0.3f, headHit.point);
                two = _hands[0].Grabber.ScriptGrab() && _hands[1].Grabber.ScriptGrab() && r.HolderCount == 2;
            }
            if (!two) misses.Add("two hands on the head: refused");
            int thigh = p.IndexOf(Kind.Thigh, NpcSide.Right);
            bool pinned = Above(r.PartCenter(thigh), out RaycastHit thighHit, out _) && r.TogglePin(thighHit.collider, thighHit.point, 0f) &&
                          r.HolderCount == 3;
            if (!pinned) misses.Add("a third holder (F9 pin) refused");
            r.UnpinAll();
            foreach (Hand hand in _hands) hand.Grabber.ScriptRelease();
            yield return Fixed;
            // Three pins far apart (a pin within 0.25 m of another removes it instead).
            int[] pinParts = { p.IndexOf(Kind.Calf, NpcSide.Right), p.IndexOf(Kind.ForeArm, NpcSide.Right), p.IndexOf(Kind.Thigh, NpcSide.Left) };
            foreach (int part in pinParts)
                if (Above(r.PartCenter(part), out RaycastHit pinHit, out _)) r.TogglePin(pinHit.collider, pinHit.point, 0f);
            bool full = r.HolderCount == 3;
            Aim(_hands[0], headEye, headHit.point);
            bool fourth = _hands[0].Grabber.ScriptGrab();
            if (!full || fourth) misses.Add($"holder limit: {r.HolderCount} pins, fourth {(fourth ? "taken" : "refused")}");
            _hands[0].Grabber.ScriptRelease();
            r.UnpinAll();
            yield return Fixed;
            Check("r5 grab any part", misses.Count == 0 && r.HolderCount == 0,
                $"{tried} points, two hands on one part, three holders max" + (misses.Count > 0 ? " [" + string.Join("; ", misses) + "]" : ""));
        }

        // ---------- r3, r4: one hand lifts ----------

        private IEnumerator HeadLift()
        {
            Progress = "r3 head lift";
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            int head = p.IndexOf(Kind.Head);
            r.CapsuleSegment(head, out _, out Vector3 top, out _);
            yield return Lift("r3 head lift", r, top, 0.5f, 1.5f, rise => rise >= 0.4f, "head top", "(limit +0.40 m within 1.5 s)");
        }

        private IEnumerator PelvisLift()
        {
            Progress = "r4 pelvis";
            NpcRagdoll r = _a.Ragdoll;
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            yield return Lift("r4 pelvis one hand", r, r.Landmark(NpcLandmark.Pelvis), 0.6f, 2f, rise => rise <= 0.15f, "pelvis",
                "(bad handle: at most +0.15 m)");
        }

        // One hand grabs at 'point' from above and raises its target by 'raise' over 0.5 s, holding 'seconds' in all; the
        // check looks at how far the grabbed point rose (max) and how soon it rose 0.4 m.
        private IEnumerator Lift(string name, NpcRagdoll r, Vector3 point, float raise, float seconds, Func<float, bool> pass, string what, string limit)
        {
            Hand h = _hands[0];
            if (!Above(point, out RaycastHit hit, out Vector3 eye) || !Grab(h, eye, hit.point, r, out int slot))
            {
                Check(name, false, $"could not grab the {what}");
                yield break;
            }
            Vector3 claim0 = r.ClaimWorld(slot);
            Vector3 from = eye + Vector3.up * 0.5f; // the hold distance stays above the 0.6 m minimum at the top
            float t0 = Time.fixedTime, rise = 0f, reach = -1f;
            h.Expect = true;
            h.Forces.Clear();
            int ticks = Ticks(seconds);
            for (int k = 1; k <= ticks; k++)
            {
                float u = Mathf.Clamp01(k * Time.fixedDeltaTime / 0.5f);
                Aim(h, Vector3.Lerp(eye, from, u), claim0 + Vector3.up * (raise * u));
                yield return Fixed;
                AfterTick();
                if (h.Grabber.IsHolding)
                {
                    float y = r.ClaimWorld(slot).y - claim0.y;
                    rise = Mathf.Max(rise, y);
                    if (reach < 0f && y >= 0.4f) reach = Time.fixedTime - t0;
                }
            }
            h.Expect = false;
            float force = Mean(h.Forces);
            Release(h);
            yield return Idle(0.3f);
            bool head = name == "r3 head lift";
            Check(name, pass(rise) && (!head || (reach >= 0f && reach <= 1.5f)),
                Inv($"{what} rose {rise:0.00} m{(head ? ", +0.4 m after " + Seconds(reach) : "")}, mean hand force {force:0} N {limit}"));
        }

        // ---------- r2: stretch ----------

        private IEnumerator Stretch()
        {
            Progress = "r2 stretch";
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            int forearm = p.IndexOf(Kind.ForeArm, NpcSide.Left);
            r.CapsuleSegment(forearm, out _, out Vector3 wrist, out _);
            Hand h = _hands[0];
            if (!Above(wrist, out RaycastHit hit, out Vector3 eye) || !Grab(h, eye, hit.point, r, out int slot))
            {
                Check("r2 stretch", false, "could not grab the wrist");
                yield break;
            }
            Vector3 claim0 = r.ClaimWorld(slot);
            Vector3 outward = Flat(claim0 - r.PartCenter(p.IndexOf(Kind.Chest)));
            outward = outward.sqrMagnitude > 1e-4f ? outward.normalized : Vector3.forward;
            Vector3 target = claim0 + outward * 0.9f + Vector3.up * 0.4f;
            Vector3 stand = claim0 + outward * 1.7f + Vector3.up * 1.4f;
            float gap = 0f;
            int saturated = 0;
            h.Expect = true;
            h.Forces.Clear();
            int ticks = Ticks(2.2f);
            for (int k = 1; k <= ticks; k++)
            {
                float u = Mathf.Clamp01(k * Time.fixedDeltaTime / 0.2f);
                Aim(h, Vector3.Lerp(eye, stand, u), Vector3.Lerp(claim0, target, u));
                yield return Fixed;
                AfterTick();
                gap = Mathf.Max(gap, MaxJointGap(r));
                if (h.Grabber.LastPointForce.magnitude >= p.GoodForce.x - 1f) saturated++;
            }
            h.Expect = false;
            float force = Mean(h.Forces);
            Release(h);
            yield return Idle(0.3f);
            Check("r2 stretch", gap <= 0.03f,
                Inv($"worst joint gap {gap * 100f:0.0} cm (limit 3), mean hand force {force:0} N, at the cap {saturated * 100 / Mathf.Max(1, ticks)}% of ticks"));
        }

        // ---------- Punch on a limb (INFO, step 3) ----------

        // A fist on the forearm of a body lying on its back (the step-3 fix of the whipped limb): the struck forearm takes at
        // most HitPartSpeed of the blow, the rest moves the whole body. Printed: the forearm's and the pelvis's peak speed.
        private IEnumerator Punch()
        {
            Progress = "punch on a lying forearm (INFO)";
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            r.PlaceLying(_o, Vector3.right, true);
            yield return Idle(0.6f);
            int forearm = p.IndexOf(Kind.ForeArm, NpcSide.Left);
            Vector3 at = r.PartCenter(forearm);
            float condition = _a.Condition;
            _a.Hit(WeaponStun.Fist, HitZone.Limb, at + new Vector3(0f, 1.2f, 0.6f), at);
            _a.Condition = condition; // the test's blow costs nothing
            KeepStunned();
            float arm = 0f, pelvis = 0f;
            for (int k = 0; k < Ticks(0.6f); k++)
            {
                yield return Fixed;
                AfterTick();
                arm = Mathf.Max(arm, r.BodyOf(forearm).linearVelocity.magnitude);
                pelvis = Mathf.Max(pelvis, r.MainBody.linearVelocity.magnitude);
            }
            yield return Idle(0.6f);
            Line(Inv($"{Tag} INFO punch on a lying forearm (fist, 42 N·s): forearm peak {arm:0.0} m/s (its share capped at {p.HitPartSpeed:0} m/s; ") +
                 Inv($"the whole blow on it was ~40 m/s before step 3), pelvis peak {pelvis:0.0} m/s"));
        }

        // ---------- Drag (INFO) ----------

        private IEnumerator Drag()
        {
            Progress = "drag (INFO)";
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            r.PlaceLying(_o - Vector3.right * 8f, Vector3.right, true);
            yield return Idle(0.6f);
            int chest = p.IndexOf(Kind.Chest);
            Vector3 collar = r.PartCenter(chest) + ChestLateral(r, chest) * 0.12f + ChestUp(r, chest) * (0.75f * p.Parts[chest].Radius);
            Hand h = _hands[0];
            if (!Above(collar, out RaycastHit hit, out Vector3 eye) || !Grab(h, eye, hit.point, r, out int slot))
            {
                Line($"{Tag} INFO drag: could not grab the collar");
                yield break;
            }
            // The player backs away head first at walking speed, holding the collar at knee height.
            Vector3 hold = r.ClaimWorld(slot) + Vector3.up * 0.35f;
            Vector3 back = Vector3.right;
            var lags = new List<float>();
            var speeds = new List<float>();
            h.Expect = true;
            h.Forces.Clear();
            int ticks = Ticks(2.4f);
            for (int k = 1; k <= ticks; k++)
            {
                float t = k * Time.fixedDeltaTime;
                float speed = Mathf.Min(WalkSpeed, WalkSpeed * t / 0.4f);
                hold += back * (speed * Time.fixedDeltaTime);
                Aim(h, hold + back * 0.9f + Vector3.up * 1.2f, hold);
                yield return Fixed;
                AfterTick();
                if (t < 1.4f || !h.Grabber.IsHolding) continue;
                lags.Add(Vector3.Distance(h.Grabber.PointHoldTarget, r.ClaimWorld(slot)));
                speeds.Add(Vector3.Dot(r.MainBody.linearVelocity, back));
            }
            h.Expect = false;
            Release(h);
            yield return Idle(0.3f);
            Line(Inv($"{Tag} INFO drag by the collar at {WalkSpeed:0.0} m/s: pelvis {Mean(speeds):0.0} m/s ({Mean(speeds) / WalkSpeed * 100f:0}%), ") +
                 Inv($"lag {Mean(lags):0.00} m (design target >= 70%, <= 0.6 m), mean force {Mean(h.Forces):0} N"));
        }

        // ---------- r5b: two hands on open ground ----------

        // The design's T1 r5 (§6): collar + ankle, both hands standing (the collar hand beside the chest, the ankle hand
        // behind the feet), lifting to the carry height in 0.5 s and holding it for a second. The pelvis must clear the
        // ground by PairClear within PairClearTime of the grab, each hand's mean force at most PairForce. INFO: the whole
        // body's clearance (the arms hang), the carry tone the joints got (2: the split-pair hammock of A4).
        // Step 4 (r17b, groggy): the same with A Groggy once both hands hold it (the carried struggle: pawing, wriggling,
        // kicking on the drives; kick tears off, r15 measures those): it must stay carryable by the same numbers.
        private IEnumerator PairLift(bool groggy)
        {
            string name = groggy ? "r17b pair lift, groggy (carried struggle)" : "r5b pair lift (open ground)";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            Vector3 headDir = Vector3.right;
            r.PlaceLying(_o + new Vector3(0f, 0f, -6f), headDir, true);
            KeepStunned();
            yield return Idle(0.6f);
            Hand a = _hands[0], b = _hands[1];
            Crouch(a, false);
            Crouch(b, false);
            a.Stand = Flat(r.Landmark(NpcLandmark.Collar)) + Vector3.forward * 0.55f + headDir * 0.15f;
            b.Stand = Flat(LowFootTip(r)) - headDir * 0.8f;
            bool collar = GrabCollar(a, r);
            string collarMiss = string.Join("; ", _grabMiss);
            bool ankle = GrabCalf(b, r, NpcSide.Left);
            if (!collar || !ankle)
            {
                Check(name, false, Inv($"could not take hold: collar={(collar ? 1 : 0)} ankle={(ankle ? 1 : 0)}") +
                                   (collar ? "" : " [collar: " + collarMiss + "]") + (ankle ? "" : " [ankle: " + string.Join("; ", _grabMiss) + "]"));
                ReleaseHand(a);
                ReleaseHand(b);
                yield break;
            }
            int pelvis = p.IndexOf(Kind.Pelvis);
            float grabbed = Time.fixedTime, clearAt = -1f, clear = float.NegativeInfinity, whole = float.NegativeInfinity;
            int tone = 0, kicks0 = _a.Kicks, heldTicks = 0, ticks = 0;
            if (groggy)
            {
                OverrideKicks(_a, null, new float[4]);
                SetGroggy(_a, true);
            }
            _observe = () =>
            {
                r.CapsuleSegment(pelvis, out Vector3 pa, out Vector3 pb, out float pr);
                float up = Mathf.Min(pa.y, pb.y) - pr - _o.y;
                clear = Mathf.Max(clear, up);
                if (clearAt < 0f && up >= PairClear) clearAt = Time.fixedTime - grabbed;
                whole = Mathf.Max(whole, LowestPoint(r) - _o.y);
                tone = Mathf.Max(tone, r.Tone);
                ticks++;
                if (_a.Struggle != null && _a.Struggle.Current == NpcStruggle.Mode.Held) heldTicks++;
            };
            Vector3 ta = a.Target, tb = b.Target;
            yield return Move(0.5f, To(a, new Vector3(ta.x, _o.y + Carry, ta.z)), To(b, new Vector3(tb.x, _o.y + Carry, tb.z)));
            yield return Move(1.0f, To(a, a.Target), To(b, b.Target));
            _observe = null;
            bool kept = !a.Lost && !b.Lost;
            float forceA = Mean(a.Forces), forceB = Mean(b.Forces);
            var lags = new List<float>(a.Lags);
            lags.AddRange(b.Lags);
            ReleaseHand(a);
            ReleaseHand(b);
            if (groggy)
            {
                SetGroggy(_a, false);
                RestoreKicks(_a);
            }
            yield return Idle(0.8f);
            bool struggled = !groggy || heldTicks >= ticks / 2;
            Check(name, kept && clearAt >= 0f && clearAt <= PairClearTime && forceA <= PairForce && forceB <= PairForce && struggled,
                Inv($"pelvis clear {clear:0.00} m, {PairClear:0.0} m after {Seconds(clearAt)} (limit {PairClearTime:0.0} s); whole body {whole:0.00} m (INFO); ") +
                Inv($"force collar={forceA:0}N ankle={forceB:0}N (limit {PairForce:0} each) grip={(kept ? "kept" : "LOST")} tone {tone} ") +
                Inv($"lag={Mean(lags):0.00}m (p95 {Percentile(lags, 0.95f):0.00})") +
                (groggy ? Inv($"; struggling held {heldTicks}/{ticks} ticks, kicks {_a.Kicks - kicks0}") : ""));
        }

        // ---------- Step 4: r15 kicks against a holder, r16 crawl, r16b re-stun ----------

        // r15: A lies on its back, one hand standing beside it holds the collar up at 0.7 m while A is Groggy, kicking every
        // TestKickPace s (the game's KickInterval is 1.0-1.8 s) with the scene's KickTearChance, for KickTearSeconds. After
        // every tear the hand takes hold again, like a player. Pass: at least 10 kicks while held; no hold lost but to a
        // tear (the motors must not rip holds); the tears plausible for KickTearChance[1] (binomial, 99 %). INFO: the hand's
        // force, the shins' peak speed.
        private IEnumerator KickTear()
        {
            const string name = "r15 groggy kicks against a holder";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            Vector3 headDir = Vector3.right;
            r.PlaceLying(_o + new Vector3(0f, 0f, 6f), headDir, true);
            KeepStunned();
            yield return Idle(0.6f);
            Hand h = _hands[0];
            Crouch(h, false);
            h.Stand = Flat(r.Landmark(NpcLandmark.Collar)) + Vector3.forward * 0.55f + headDir * 0.15f;
            if (!GrabCollar(h, r))
            {
                Check(name, false, "could not take the collar [" + string.Join("; ", _grabMiss) + "]");
                yield break;
            }
            h.Expect = false; // tears are expected here; a hold lost without one is counted below
            float chance = _a.KickTearChance.Length > 1 ? _a.KickTearChance[1] : 0f;
            OverrideKicks(_a, TestKickPace, null);
            SetGroggy(_a, true);
            float height = _o.y + 0.7f;
            h.Target = new Vector3(h.Target.x, height, h.Target.z);
            int heldKicks = 0, tears = 0, ripped = 0, regrabs = 0, missed = 0, lastTear = -100;
            float calfPeak = 0f;
            var forces = new List<float>();
            int calfL = p.IndexOf(Kind.Calf, NpcSide.Left), calfR = p.IndexOf(Kind.Calf, NpcSide.Right);
            int ticks = Ticks(KickTearSeconds);
            for (int k = 0; k < ticks; k++)
            {
                bool holding = h.Grabber.IsHolding;
                int kicks = _a.Kicks, torn = _a.Tears;
                if (holding) AimHand(h);
                yield return Fixed;
                AfterTick();
                if (holding) heldKicks += _a.Kicks - kicks;
                if (_a.Tears > torn)
                {
                    tears += _a.Tears - torn;
                    lastTear = k;
                }
                if (holding && !h.Grabber.IsHolding && k - lastTear > 2) ripped++;
                if (!h.Grabber.IsHolding && k - lastTear >= 3 && (k & 3) == 0)
                {
                    // Take hold again (a player would): the collar from where the hand stands, then up to the hold height.
                    ReleaseHand(h);
                    h.Stand = Flat(r.Landmark(NpcLandmark.Collar)) + Vector3.forward * 0.55f + headDir * 0.15f;
                    if (GrabCollar(h, r))
                    {
                        regrabs++;
                        h.Expect = false;
                        h.Target = new Vector3(h.Target.x, height, h.Target.z);
                    }
                    else missed++;
                }
                if (h.Grabber.IsHolding) forces.Add(h.Grabber.LastPointForce.magnitude);
                if (calfL >= 0) calfPeak = Mathf.Max(calfPeak, r.BodyOf(calfL).linearVelocity.magnitude);
                if (calfR >= 0) calfPeak = Mathf.Max(calfPeak, r.BodyOf(calfR).linearVelocity.magnitude);
            }
            ReleaseHand(h);
            SetGroggy(_a, false);
            RestoreKicks(_a);
            yield return Idle(0.6f);
            bool plausible = BinomialPlausible(heldKicks, tears, chance, out double atMost, out double atLeast);
            Check(name, heldKicks >= 10 && ripped == 0 && plausible,
                Inv($"{heldKicks} kicks while held, {tears} tore the hold ({(heldKicks > 0 ? 100f * tears / heldKicks : 0f):0}%, KickTearChance {chance * 100f:0}%: ") +
                Inv($"P(<= {tears}) {atMost:0.000}, P(>= {tears}) {atLeast:0.000}, limit 0.005 each); holds lost without a tear {ripped} (limit 0); ") +
                Inv($"taken again {regrabs} (missed tries {missed}); INFO hand force mean {Mean(forces):0} N p95 {Percentile(forces, 0.95f):0} N, shin peak {calfPeak:0.0} m/s"));
        }

        // r16: A lies on its back on open ground, Groggy, nobody holds it: it crawls on its drives away from the threat (the
        // player, else the van, far off). After 1 s to get going the pelvis is followed for CrawlWindow s. Pass: CrawlMin ..
        // CrawlMax m/s, within 45 degrees of straight away from the threat, the struggle crawling at least 60 % of the
        // ticks, no body faster than 4 m/s, every joint gap <= 3 cm. INFO: the path's straightness, the pull, kicks.
        private IEnumerator CrawlCheck()
        {
            const string name = "r16 groggy crawl";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            Vector3 spot = _o + new Vector3(-6f, 0f, -6f);
            bool threat = Threat(out Vector3 from);
            // Its head 30 degrees off straight away from the threat: it crawls head first and has to turn a little.
            Vector3 headAway = Flat(spot - from);
            headAway = Quaternion.Euler(0f, 30f, 0f) * (headAway.sqrMagnitude > 1e-4f ? headAway.normalized : Vector3.right);
            r.PlaceLying(spot, headAway, true);
            KeepStunned();
            yield return Idle(0.6f);
            SetGroggy(_a, true);
            yield return Idle(1f);
            Vector3 start = Flat(r.Landmark(NpcLandmark.Pelvis)), last = start;
            float path = 0f, fastest = 0f, gap = 0f, pull = 0f;
            int crawling = 0, ticks = 0, kicks0 = _a.Kicks;
            for (int k = 0; k < Ticks(CrawlWindow); k++)
            {
                yield return Fixed;
                AfterTick();
                Vector3 now = Flat(r.Landmark(NpcLandmark.Pelvis));
                path += Vector3.Distance(now, last);
                last = now;
                ticks++;
                if (_a.Struggle != null && _a.Struggle.Current == NpcStruggle.Mode.Crawl)
                {
                    crawling++;
                    pull += _a.Struggle.Pull;
                }
                for (int i = 0; i < r.PartCount; i++) fastest = Mathf.Max(fastest, r.BodyOf(i).linearVelocity.magnitude);
                gap = Mathf.Max(gap, MaxJointGap(r));
            }
            Vector3 moved = last - start;
            float speed = moved.magnitude / CrawlWindow;
            Vector3 away = Flat(start - from);
            float angle = threat && away.sqrMagnitude > 1e-4f && moved.sqrMagnitude > 1e-6f ? Vector3.Angle(moved, away) : 180f;
            Check(name, speed >= CrawlMin && speed <= CrawlMax && angle <= 45f && crawling >= 0.6f * ticks && fastest <= 4f && gap <= 0.03f,
                Inv($"{speed:0.00} m/s over {CrawlWindow:0} s (limits {CrawlMin:0.0}..{CrawlMax:0.0}), {angle:0} deg off straight away from the threat (limit 45), ") +
                Inv($"crawling {crawling}/{ticks} ticks, fastest body {fastest:0.0} m/s (limit 4), worst joint gap {gap * 100f:0.0} cm (limit 3); ") +
                Inv($"INFO straightness {(path > 1e-3f ? moved.magnitude / path : 0f):0.00}, mean pull {(crawling > 0 ? pull / crawling : 0f):0} N, kicks {_a.Kicks - kicks0}"));
        }

        // r16b (hits on lying bodies): the Groggy crawler with little stun left (2 of 8 s) is hit with the fist: stunned
        // again (Out at once, the struggle off by the next step: limp), Condition - ReStunConditionCost, the blow spread as
        // in step 3 (no body faster than BlowSpeed).
        private IEnumerator Restun()
        {
            const string name = "r16b fist on a groggy body";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            _keepGroggy.Remove(_a);
            _keepDown.Remove(_a);
            _a.StunTotal = 8f;
            _a.StunLeft = 2f; // Groggy (75 % gone)
            yield return Fixed;
            yield return Fixed;
            float condition = _a.Condition;
            bool wasStruggling = _a.Struggle != null && _a.Struggle.Current != NpcStruggle.Mode.Off;
            Vector3 at = r.Landmark(NpcLandmark.Pelvis);
            _a.Hit(WeaponStun.Fist, HitZone.Torso, at + new Vector3(0.6f, 1.2f, 0f), at);
            bool outAgain = _a.Phase == StunPhase.Out && _a.StunLeft > 2f;
            float cost = condition - _a.Condition;
            _a.Condition = condition; // the test's blow costs nothing afterwards
            _keepDown.Add(_a);
            float peak = 0f;
            bool limp = false;
            for (int k = 0; k < Ticks(0.6f); k++)
            {
                yield return Fixed;
                AfterTick();
                peak = Mathf.Max(peak, r.MaxRelativeSpeed(null));
                if (k == 1) limp = _a.Struggle == null || _a.Struggle.Current == NpcStruggle.Mode.Off;
            }
            RestoreKicks(_a);
            Check(name, wasStruggling && outAgain && limp && Mathf.Abs(cost - _a.ReStunConditionCost) < 0.01f && peak <= BlowSpeed,
                Inv($"struggling before={(wasStruggling ? 1 : 0)}; after the fist: Out={(outAgain ? 1 : 0)} limp={(limp ? 1 : 0)}, ") +
                Inv($"Condition -{cost:0.#} (rule {_a.ReStunConditionCost:0.#}), peak body speed {peak:0.0} m/s (limit {BlowSpeed:0})"));
        }

        // ---------- r8a/r8b get up with the clips (step 3), r7 momentum ----------

        // The design's T1 r8 with the step-3 clips (§4.4): A lies on its back (r8a) or its belly (r8b) on open ground and
        // wakes. It must end up standing (free, the CharacterController and the Animator on, nothing of the ragdoll left,
        // the head well above the hips) within GetUpLimit; the expected clip must play; nothing may pop (the Hips or the
        // head moving more than PopLimit between two drawn frames); the CharacterController must come on at the clip's
        // Stable point (not at its start); it must stand within 0.35 m of where its hips lay, the hips never more than 5 cm
        // under the ground. INFO: the settle, the lying Hips against the clip's first frame, crawls, the root's shift.
        private IEnumerator GetUp(bool faceUp)
        {
            string name = faceUp ? "r8a get-up from the back" : "r8b get-up from the belly";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            NpcGetUp up = _a.GetUp;
            if (!r.Active && _a.State == NpcState.Free)
            {
                // r8a stood it up: down again as the ragdoll.
                _a.Hit(WeaponStun.Fist, HitZone.Torso, _a.transform.position + _a.transform.forward, _a.Center);
                _keepDown.Add(_a);
                KeepStunned();
                yield return Idle(0.3f);
            }
            if (!r.Active || up == null || !up.CanGetUp)
            {
                Check(name, false, Inv($"cannot start: ragdoll={(r.Active ? 1 : 0)} state={_a.State} clips={(up != null && up.CanGetUp ? 1 : 0)}"));
                yield break;
            }
            NpcRagdollProfile p = r.Profile;
            NpcRagdollProfile.ClipInfo clip = faceUp ? p.GetUpBack : p.GetUpBelly;
            r.PlaceLying(_o, Vector3.right, faceUp);
            yield return Idle(0.8f);
            Transform hips = r.Hips, head = r.BoneOf(p.IndexOf(Kind.Head));
            Animator animator = r.Animator;
            var controller = _a.GetComponent<CharacterController>();
            Vector3 hips0 = hips.position, lastHips = hips.position, lastHead = head.position;
            // Real time from here: a drawn frame then covers 1/60-1/30 s of the clip (a few cm), whatever the frame rate,
            // so a pop (a jump by the root move, 0.2-1 m) stands out.
            Time.timeScale = 1f;
            _keepDown.Remove(_a);
            _a.StunTotal = 8f;
            _a.StunLeft = 0.05f;
            float t0 = Time.fixedTime, startAt = -1f, clipAt = -1f, onAt = -1f, onShare = -1f, pop = 0f, firstPop = 0f, sunk = -1f;
            float travel = 0f; // how far the head goes in the blend window: a wrong facing swings the body round smoothly
            Vector3 headAtStart = head.position;
            int frame = Time.frameCount, frames = 0;
            for (int k = 0; k < Ticks(GetUpLimit + 1.5f) && _a.State != NpcState.Free; k++)
            {
                yield return Fixed;
                AfterTick();
                float t = Time.fixedTime - t0;
                if (Time.frameCount != frame)
                {
                    frame = Time.frameCount;
                    frames++;
                    float jump = Mathf.Max(Vector3.Distance(hips.position, lastHips), Vector3.Distance(head.position, lastHead));
                    pop = Mathf.Max(pop, jump);
                    if (startAt >= 0f && t - startAt <= 0.6f) firstPop = Mathf.Max(firstPop, jump);
                    lastHips = hips.position;
                    lastHead = head.position;
                }
                sunk = Mathf.Max(sunk, _o.y - hips.position.y);
                if (startAt < 0f && !r.Active && up.Current != NpcGetUp.Step.Settling)
                {
                    startAt = t;
                    headAtStart = head.position;
                }
                if (startAt >= 0f && t - startAt <= BlendWindow) travel = Mathf.Max(travel, Vector3.Distance(head.position, headAtStart));
                if (clipAt < 0f && animator != null && animator.enabled && animator.GetCurrentAnimatorStateInfo(0).IsName(clip.State)) clipAt = t;
                if (onAt < 0f && controller.enabled)
                {
                    onAt = t;
                    onShare = up.ClipSeconds > 0f ? up.ClipTime / up.ClipSeconds : -1f;
                }
            }
            Time.timeScale = Mathf.Max(0.1f, TimeScale);
            float freeAt = _a.State == NpcState.Free ? Time.fixedTime - t0 : -1f;
            int left = _a.GetComponentsInChildren<Rigidbody>().Length + _a.GetComponentsInChildren<Joint>().Length +
                       _a.GetComponentsInChildren<NpcRagdollPart>().Length;
            foreach (Collider c in _a.GetComponentsInChildren<Collider>())
                if (!(c is CharacterController)) left++;
            // Standing, the Head bone (the neck's top) is ~0.43 m over the Hips; lying, about level with them.
            float upright = head.position.y - hips.position.y;
            float off = Flat(_a.transform.position - hips0).magnitude;
            bool stood = freeAt >= 0f && freeAt <= GetUpLimit && !r.Active && left == 0 && animator != null && animator.enabled &&
                         controller.enabled && upright >= 0.3f && NpcRagdoll.ActiveCount == 0;
            bool stable = onAt >= 0f && onAt <= 3.5f && onShare >= clip.Stable - 0.05f && onShare <= clip.Stable + 0.15f;
            Check(name, stood && clipAt >= 0f && pop <= PopLimit && travel <= TravelLimit && stable && off <= 0.35f && sunk <= 0.05f,
                Inv($"free after {Seconds(freeAt)} (limit {GetUpLimit:0.0} s), {clip.State} {(clipAt >= 0f ? "played" : "NOT SEEN")}, head {upright:0.00} m over the hips, leftovers {left}; ") +
                Inv($"CharacterController on at {Seconds(onAt)} = {onShare * 100f:0}% of the clip (Stable {clip.Stable * 100f:0}%); ") +
                Inv($"largest move of hips/head between drawn frames {pop:0.00} m (limit {PopLimit:0.0}), {firstPop:0.00} m in the first 0.6 s of the clip; ") +
                Inv($"the head travelled {travel:0.00} m in the first {BlendWindow:0.00} s of the clip (limit {TravelLimit:0.0}: the lying pose and the clip's start agree); ") +
                Inv($"stood {off:0.00} m from where its hips lay (limit 0.35), hips at most {Mathf.Max(0f, sunk) * 100f:0} cm under the ground (limit 5); ") +
                Inv($"INFO settled {up.SettledAfter:0.00} s, lying Hips {up.LyingHips:0.00} m vs the clip's {clip.HipsStart.y:0.00} m, crawls {up.Crawls}, shift {up.Shift:0.00} m{(up.Squeezed ? " SQUEEZED" : "")}, {frames} frames"));
        }

        private IEnumerator Momentum()
        {
            Progress = "r7 momentum";
            var controller = _a.GetComponent<CharacterController>();
            yield return Idle(0.6f); // woke up screaming and running away
            Saw("fleeing after the get-up (A)", _a, NpcAnimContract.RunState);
            Vector3 v = Flat(controller.velocity);
            if (v.magnitude < 2f)
            {
                Check("r7 momentum", false, Inv($"the woken NPC is not running ({v.magnitude:0.0} m/s)"));
                yield break;
            }
            Vector3 dir = v.normalized;
            _a.Hit(WeaponStun.Fist, HitZone.Torso, _a.transform.position - dir, _a.Center);
            _keepDown.Add(_a);
            KeepStunned();
            NpcRagdoll r = _a.Ragdoll;
            yield return Fixed;
            AfterTick();
            float along = 0f, mass = 0f;
            for (int i = 0; i < r.PartCount; i++)
            {
                Rigidbody rb = r.BodyOf(i);
                along += Vector3.Dot(rb.linearVelocity, dir) * rb.mass;
                mass += rb.mass;
            }
            along /= Mathf.Max(0.01f, mass);
            Check("r7 momentum", r.Active && along >= 0.7f * v.magnitude,
                Inv($"ran {v.magnitude:0.0} m/s, hit from behind (+1.5 m/s): body {along:0.0} m/s along the run one tick later (limit {0.7f * v.magnitude:0.0})"));
            yield return Idle(1.5f);
        }

        // ---------- r9 cap, r10 capsule mode ----------

        private IEnumerator CapCheck()
        {
            Progress = "r9 cap";
            NpcRagdoll.Cap = 2;
            PutAt(_b, _o + new Vector3(5f, 0f, 5f), 0f);
            PutAt(_c, _o + new Vector3(-5f, 0f, 5f), 0f);
            yield return Idle(0.3f);
            _b.Hit(WeaponStun.Fist, HitZone.Torso, _b.transform.position + _b.transform.forward, _b.Center);
            _keepDown.Add(_b);
            double msB = NpcRagdoll.LastBuildMilliseconds;
            _c.Hit(WeaponStun.Fist, HitZone.Torso, _c.transform.position + _c.transform.forward, _c.Center);
            _keepDown.Add(_c);
            KeepStunned();
            bool ok = _a.Ragdoll.Active && _b.Ragdoll.Active && !_c.Ragdoll.Active && _c.Body.Active && NpcRagdoll.ActiveCount == 2;
            NpcRagdoll.Cap = _cap0;
            yield return Idle(0.5f);
            Check("r9 cap", ok, Inv($"cap 2: A ragdoll={(_a.Ragdoll.Active ? 1 : 0)} B ragdoll={(_b.Ragdoll.Active ? 1 : 0)} ") +
                                Inv($"C capsule={(_c.Body.Active ? 1 : 0)} live={NpcRagdoll.ActiveCount}; B built in {msB:0.00} ms"));
        }

        private IEnumerator CapsuleMode()
        {
            Progress = "r10 capsule mode";
            _keepDown.Remove(_a);
            _a.StunTotal = 8f;
            _a.StunLeft = 0.05f;
            yield return WaitFor(() => _a.State == NpcState.Free, GetUpLimit + 1.5f); // the get-up clip (step 3)
            yield return Idle(0.2f);
            NpcRagdoll.Mode = NpcBodyMode.Capsule;
            _a.Hit(WeaponStun.Fist, HitZone.Torso, _a.transform.position + _a.transform.forward, _a.Center);
            _keepDown.Add(_a);
            KeepStunned();
            bool ok = _a.State == NpcState.Down && _a.Body.Active && !_a.Ragdoll.Active;
            yield return Idle(0.3f);
            Saw("lying as the capsule (A)", _a, With(RoleStates(_a, NpcAnimContract.RoleHitFront, NpcAnimContract.RoleHitBack, NpcAnimContract.RoleHitHead),
                NpcAnimContract.DownState));
            Check("r10 capsule mode", ok, $"F10 = capsule: stage-1 body={(_a.Body.Active ? 1 : 0)} ragdoll={(_a.Ragdoll.Active ? 1 : 0)}");
            NpcRagdoll.Mode = NpcBodyMode.Ragdoll;
        }

        // ---------- r19: the fat police officer's trip (step 4) ----------

        // A copy of a free crowd NPC (made under an inactive parent, its crowd walker, police role and sea tracker removed, as
        // in T2) becomes a fat PoliceOfficer in the sandbox; with no crowd walker and no car he walks off (Leave). Then
        // PoliceOfficer.Trip (what Move rolls for the fat one while he runs). Pass: he goes down as the ragdoll (Stumbling,
        // not grabbable), is never Down for the police, gets up with the get-up clip and is Free again within TripLimit, in
        // the state he was in, his CharacterController on and no ragdoll left, and no incident is raised for him.
        private IEnumerator TripCheck()
        {
            const string name = "r19 fat police officer trips";
            Progress = name;
            GreyboxNpc template = null;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && npc.isActiveAndEnabled && npc.State == NpcState.Free && !npc.InCargo && !PoliceOfficer.IsOfficer(npc) &&
                    npc.Ragdoll != null && npc.Ragdoll.Ready && !IsTaken(npc))
                {
                    template = npc;
                    break;
                }
            if (template == null)
            {
                Check(name, false, "no free crowd NPC to make an officer of");
                yield break;
            }
            var holder = new GameObject("RagdollTrip_Holder");
            holder.SetActive(false);
            GameObject go = Instantiate(template.gameObject, holder.transform);
            go.name = "RagdollTrip_Officer";
            foreach (CrowdWalker w in go.GetComponents<CrowdWalker>()) DestroyImmediate(w);
            foreach (PoliceOfficer o in go.GetComponents<PoliceOfficer>()) DestroyImmediate(o);
            foreach (SeaReturnTracker s in go.GetComponents<SeaReturnTracker>()) DestroyImmediate(s);
            go.transform.SetPositionAndRotation(_o + new Vector3(10f, 0f, -10f), Quaternion.identity);
            go.transform.SetParent(null, true); // active now: Awake and OnEnable run
            Destroy(holder);
            _clones.Add(go);
            var cop = go.AddComponent<PoliceOfficer>();
            cop.Fat = true;
            GreyboxNpc npcCop = go.GetComponent<GreyboxNpc>();
            yield return null; // Start
            yield return Idle(0.8f);
            Saw("an officer leaving on foot (r19)", npcCop, NpcAnimContract.WalkState, NpcAnimContract.IdleState);
            PoliceOfficer.OfficerState before = cop.State;
            int incidents = 0;
            _incidentProbe = (victim, kind) =>
            {
                if (victim == npcCop) incidents++;
            };
            GreyboxNpc.Incident += _incidentProbe;
            if (!go.activeSelf) go.SetActive(true); // his Leave may have sent him off the map already (PoliceOfficer.Vanish)
            bool tripped = cop.Trip();
            bool ragdoll = npcCop.Ragdoll != null && npcCop.Ragdoll.Active, stumbling = npcCop.Stumbling, down = false, grabbable = false;
            float t0 = Time.fixedTime, freeAt = -1f;
            for (int k = 0; k < Ticks(TripLimit + 1f) && freeAt < 0f; k++)
            {
                yield return Fixed;
                AfterTick();
                WatchAnim(npcCop);
                down |= cop.Down;
                ragdoll |= npcCop.Ragdoll.Active;
                grabbable |= npcCop.Ragdoll.Active && npcCop.Ragdoll.Grabbable;
                if (npcCop.State == NpcState.Free && !npcCop.Stumbling) freeAt = Time.fixedTime - t0;
            }
            GreyboxNpc.Incident -= _incidentProbe;
            _incidentProbe = null;
            var controller = go.GetComponent<CharacterController>();
            bool up = freeAt >= 0f && freeAt <= TripLimit && !npcCop.Ragdoll.Active && controller.enabled && cop.State == before;
            Check(name, tripped && ragdoll && stumbling && !down && !grabbable && up && incidents == 0,
                Inv($"tripped={(tripped ? 1 : 0)} ragdoll={(ragdoll ? 1 : 0)} stumbling={(stumbling ? 1 : 0)} grabbable={(grabbable ? 1 : 0)} ") +
                Inv($"Down for the police={(down ? 1 : 0)}; free after {Seconds(freeAt)} (limit {TripLimit:0} s: lies {PoliceTripTime():0.0} s, settles, the get-up clip) ") +
                Inv($"state {before} -> {cop.State}, controller on={(controller.enabled ? 1 : 0)}, incidents {incidents} (limit 0)"));
            _clones.Remove(go);
            Destroy(go);
            yield return Fixed;
        }

        private static float PoliceTripTime() => PoliceDirector.Instance != null ? PoliceDirector.Instance.Config.TripTime : 1.2f;

        // ---------- The van: r6, r6b, r7, r12, r11, r13 ----------

        private IEnumerator Van()
        {
            Progress = "van setup";
            if (!VanSetup(out string why))
            {
                Check("van", false, "van checks not run: " + why);
                yield break;
            }
            // A is the stage-1 capsule since r10: up, and down again as the ragdoll.
            _keepDown.Remove(_a);
            _a.StunTotal = 8f;
            _a.StunLeft = 0.05f;
            yield return WaitFor(() => _a.State == NpcState.Free, 1.5f);
            if (_a.State == NpcState.Free)
            {
                _a.Hit(WeaponStun.Fist, HitZone.Torso, _a.transform.position + _a.transform.forward, _a.Center);
                _keepDown.Add(_a);
                KeepStunned();
            }
            if (!_a.Ragdoll.Active || !_b.Ragdoll.Active)
            {
                Check("van", false, Inv($"van checks not run: A ragdoll={(_a.Ragdoll.Active ? 1 : 0)} B ragdoll={(_b.Ragdoll.Active ? 1 : 0)}"));
                yield break;
            }
            yield return SoloLoad(0, false);
            yield return SoloLoad(0, true);
            yield return SoloLoad(1, false);
            yield return PairLoad();
            yield return Ride();
            yield return SeatedHit();
            yield return Tumble();
            yield return JumpOutCheck();
        }

        private bool VanSetup(out string why)
        {
            why = _vanSkip;
            if (why != null) return false;
            _van = _cargo.GetComponent<Rigidbody>();
            _vanCtl = _cargo.GetComponent<VanController>();
            _seat = _cargo.GetComponent<GreyboxVanSeat>();
            _space = _cargo.CargoSpace != null ? _cargo.CargoSpace : _cargo.GetComponent<VanCargoSpace>();
            if (_van == null || _vanCtl == null || _space == null || _cargo.Slide == null || (_cargo.RearLeft == null && _cargo.RearRight == null))
            {
                why = "the van has no body, controller, cargo space or cargo doors";
                return false;
            }
            if (_seat != null && _seat.Driving)
            {
                why = "van occupied: someone is in the driver seat";
                return false;
            }
            GreyboxPawn pawn = _seat != null ? _seat.Pawn : null;
            if (pawn != null && pawn.Controlled && _space.Contains(pawn.Position + Vector3.up * 0.5f))
            {
                why = "van occupied: the player is in the cargo bay";
                return false;
            }
            foreach (GreyboxNpc other in GreyboxNpc.All)
                if (other != null && other.InCargo && ReferenceEquals(other.Carrier, _space))
                {
                    why = "the van has cargo: unload it first";
                    return false;
                }
            _vanPos0 = _van.position;
            _vanRot0 = _van.rotation;
            _vanKinematic0 = _van.isKinematic;
            if (!_van.isKinematic)
            {
                _van.linearVelocity = Vector3.zero;
                _van.angularVelocity = Vector3.zero;
            }
            _van.isKinematic = true;
            _vanMoved = true;
            _van.position = _vo;
            _van.rotation = _yaw;
            _van.transform.SetPositionAndRotation(_vo, _yaw);
            if (_van.TryGetComponent(out _vanTracker))
            {
                _vanTrackerOn = _vanTracker.enabled;
                _vanTracker.enabled = false;
            }
            _doorsTouched = true;
            _slideOpen0 = _cargo.DoorOpen(0);
            _rearOpen0 = _cargo.DoorOpen(1);
            Physics.SyncTransforms();
            return true;
        }

        // Back to the handbrake after the ride: kinematic, level, on the sandbox ground; the frame follows the van.
        private void ParkVan()
        {
            Vector3 forward = Flat(_van.rotation * Vector3.forward);
            _yaw = forward.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(forward.normalized) : _yaw;
            _vo = new Vector3(_van.position.x, _o.y, _van.position.z);
            _van.linearVelocity = Vector3.zero;
            _van.angularVelocity = Vector3.zero;
            _van.isKinematic = true;
            _van.position = _vo;
            _van.rotation = _yaw;
            _van.transform.SetPositionAndRotation(_vo, _yaw);
            Physics.SyncTransforms();
        }

        // r6 / r6b: one player alone, in one go (NpcLoadingTest's h1/h2 path, retold for the ragdoll). It lies on its back
        // outside the door, head toward the van; the player crouches in the bay at the door and takes the collar through
        // the doorway: A lifts it to the carry height (the trunk comes up, the legs stay down), B backs in at CarrySpeed
        // until the collar is CarryInside past the edge, C lowers it to the ride height over RideDrop and pulls it in level
        // (the body slides over the edge like a plank: the spine and the hips bend backward only a little), D lowers it and
        // lets go. Through the sliding door the bay is 1.74 m deep (far wall to floor edge) and the Buddy 1.81 m long from
        // the heels to the head top, so it cannot lie straight across (first run: the feet stayed out over the step): the
        // whole path runs on a diagonal toward the front-left corner (SideLine), the body ending with its head 5 cm from the
        // left wall and 12 cm from the partition and its heels just inside the door, the player stepping aside to the rear.
        // Step 4 (r17a, groggy): the side door again with A Groggy once the hand holds it (the carried struggle; kick tears
        // off, r15 measures those): loaded in time, grip kept, mean force at most GroggyForceMargin x this run's limp r6.
        private IEnumerator SoloLoad(int door, bool groggy)
        {
            string name = groggy ? "r17a solo side door, groggy (carried struggle)" : door == 0 ? "r6 solo side door" : "r6b solo rear doors";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            // Van-local, on the floor plane: d runs from the head toward the feet; the collar's last target and the head
            // top's place outside lie on one line along d.
            Vector3 d = door == 0 ? SideLine : Vector3.back;
            Vector3 collarEnd = door == 0 ? SideHeadEnd + d * HeadToClaim : new Vector3(0f, 0f, -0.55f);
            Vector3 headOut = door == 0 ? SideHeadEnd + d * ((1.40f - SideHeadEnd.x) / d.x) : new Vector3(0f, 0f, -2.90f);
            Vector3 headDir = _yaw * -d;
            yield return PlaceFor(_a, W(headOut.x, 0f, headOut.z), headDir);
            yield return EnsureOpen(door);
            Hand h = _hands[0];
            Crouch(h, true);
            h.Stand = door == 0 ? W(0.75f, 0f, -0.35f) : W(0.15f, 0f, -1.75f);
            if (!GrabCollar(h, r))
            {
                Check(name, false, "could not take the collar from the bay [" + string.Join("; ", _grabMiss) + "]");
                yield break;
            }
            float grabbed = Time.fixedTime, loaded = -1f;
            int kicks0 = _a.Kicks, heldTicks = 0, ticks = 0;
            if (groggy)
            {
                OverrideKicks(_a, null, new float[4]);
                SetGroggy(_a, true);
            }
            _observe = () =>
            {
                if (loaded < 0f && Loaded(_a)) loaded = Time.fixedTime - grabbed;
                if (!h.Grabber.IsHolding) return;
                ticks++;
                if (_a.Struggle != null && _a.Struggle.Current == NpcStruggle.Mode.Held) heldTicks++;
            };
            var marks = new List<int>();
            // A
            Vector3 claim = r.ClaimWorld(h.Slot);
            yield return Move(0.5f, To(h, new Vector3(claim.x, _vo.y + Carry, claim.z) + headDir * 0.15f));
            marks.Add(h.Forces.Count);
            // B: the collar CarryInside past the edge, on the line.
            Vector3 over = door == 0 ? OnLine(collarEnd, d, SlideEdgeX - CarryInside) : new Vector3(0f, 0f, RearEdgeZ + CarryInside);
            Vector3 standOver = door == 0 ? W(0f, 0f, -0.80f) : W(0.15f, 0f, RearEdgeZ + CarryInside + 0.70f);
            Vector3 overW = W(over.x, Carry, over.z);
            yield return Move(Flat(overW - h.Target).magnitude / CarrySpeed, To(h, overW, standOver));
            marks.Add(h.Forces.Count);
            // C
            float ride = door == 0 ? RideSide : RideRear;
            Vector3 drop = over - d * RideDrop;
            Vector3 standDrop = door == 0 ? W(-0.05f, 0f, -0.80f) : W(0.15f, 0f, RearEdgeZ + CarryInside + RideDrop + 0.70f);
            yield return Move(RideDrop / CarrySpeed, To(h, W(drop.x, ride, drop.z), standDrop));
            Vector3 collarIn = W(collarEnd.x, ride, collarEnd.z);
            Vector3 standIn = door == 0 ? W(-0.10f, 0f, -0.80f) : W(0.15f, 0f, 0.05f);
            yield return Move(Flat(collarIn - h.Target).magnitude / CarrySpeed, To(h, collarIn, standIn));
            marks.Add(h.Forces.Count);
            // D
            yield return Move(0.4f, To(h, collarIn - Vector3.up * (ride - 0.85f)));
            marks.Add(h.Forces.Count);
            bool kept = !h.Lost;
            var forces = new List<float>(h.Forces);
            var lags = new List<float>(h.Lags);
            ReleaseHand(h);
            yield return WaitFor(() => loaded >= 0f || Time.fixedTime - grabbed > SoloLimit + 1f, 4f);
            _observe = null;
            if (groggy)
            {
                SetGroggy(_a, false); // Out again before it notices the open door
                RestoreKicks(_a);
            }
            float force = Mean(forces);
            if (door == 0 && !groggy) _soloLimpForce = force;
            // Groggy: within GroggyForceMargin of this run's limp r6 (the struggle must not make it heavier), at least SoloForce.
            float limit = groggy && _soloLimpForce > 0f ? Mathf.Max(SoloForce, _soloLimpForce * GroggyForceMargin) : SoloForce;
            Vector3 head = L(HeadTop(r)), feet = L(LowFootTip(r));
            bool struggled = !groggy || heldTicks >= ticks / 2;
            bool ok = kept && loaded >= 0f && loaded <= SoloLimit && (door == 1 || force <= limit) && struggled;
            Check(name, ok, Inv($"loaded={LoadedText(loaded)} (limit {SoloLimit:0} s) grip={(kept ? "kept" : "LOST")} ") +
                            Inv($"force{(door == 1 ? "(info)" : "")}={force:0}N{(door == 0 ? Inv($" (limit {limit:0})") : "")} ") +
                            $"phases[{Phases(forces, marks, "lift", "carry", "ride", "lower")}] " +
                            Inv($"lag={Mean(lags):0.00}m (p95 {Percentile(lags, 0.95f):0.00}) head=({head.x:0.00},{head.z:0.00}) feet=({feet.x:0.00},{feet.z:0.00})") +
                            (groggy ? Inv($"; limp r6 {_soloLimpForce:0} N, struggling held {heldTicks}/{ticks} ticks, kicks {_a.Kicks - kicks0}") : "") +
                            (loaded < 0f ? " " + Why(_a) : ""));
        }

        // The side door's diagonal (van-local, floor plane): from the head toward the feet, and the head top's last place.
        private static readonly Vector3 SideLine = new Vector3(0.894f, 0f, -0.447f);
        private static readonly Vector3 SideHeadEnd = new Vector3(-0.75f, 0f, 0.30f);
        private const float HeadToClaim = 0.55f; // m from the head top to a collar hold along the body (Buddy)

        // The point of the line (through 'p' along 'd', floor plane) at van-local x.
        private static Vector3 OnLine(Vector3 p, Vector3 d, float x) => p + d * ((x - p.x) / d.x);

        private static string LoadedText(float loaded) =>
            loaded < 0f ? "no" : loaded.ToString("0.0", CultureInfo.InvariantCulture) + " s";

        // Why a body does not count as loaded: where its pelvis and collar are (van-local), whether the bay contains them,
        // how fast its fastest body is, and its holders.
        private string Why(GreyboxNpc npc)
        {
            NpcRagdoll r = npc.Ragdoll;
            if (r == null || !r.Active) return $"[not a ragdoll: {npc.State}]";
            Vector3 pelvis = r.Landmark(NpcLandmark.Pelvis), collar = r.Landmark(NpcLandmark.Collar);
            Vector3 lp = L(pelvis), lc = L(collar);
            return Inv($"[pelvis ({lp.x:0.00},{lp.y:0.00},{lp.z:0.00}) in={(_space.Contains(pelvis) ? 1 : 0)} ") +
                   Inv($"collar ({lc.x:0.00},{lc.y:0.00},{lc.z:0.00}) in={(_space.Contains(collar) ? 1 : 0)} ") +
                   Inv($"fastest {r.MaxRelativeSpeed(_space.PointVelocity):0.00} m/s holders {r.HolderCount} state {npc.State}/{npc.Phase}]");
        }

        // Known blocker (2026-10-07, runs 1-3): crouched in the bay, hand A does not see the collar band past the 0.57 m
        // sausage head (every ray hits the head), so this check fails before the carry; next try: A standing outside
        // between the open rear leaves, then climbing in crouched. r5b measures the same pair on open ground meanwhile.
        // r7: two players, "one takes the arms, the other the legs" (design §3.5): A crouched in the bay at the rear doors
        // holds the collar, B behind the feet holds the left shin by the ankle. Both lift to the carry height (whole body
        // off the ground: A4 makes the trunk a hammock), walk it in at CarrySpeed (A backs toward the cab, B up to the
        // ground behind the rear step), lower it and let go.
        private IEnumerator PairLoad()
        {
            const string name = "r7 pair rear doors";
            Progress = name;
            NpcRagdoll r = _a.Ragdoll;
            Vector3 headDir = _yaw * Vector3.forward;
            yield return PlaceFor(_a, W(0f, 0f, -2.90f), headDir);
            yield return EnsureOpen(1);
            Hand a = _hands[0], b = _hands[1];
            Crouch(a, true);
            Crouch(b, false);
            a.Stand = W(0.15f, 0f, -1.90f);
            b.Stand = Flat(LowFootTip(r)) - headDir * 0.8f;
            bool collar = GrabCollar(a, r);
            string collarMiss = string.Join("; ", _grabMiss);
            bool ankle = GrabCalf(b, r, NpcSide.Left);
            if (!collar || !ankle)
            {
                Check(name, false, Inv($"could not take hold: collar={(collar ? 1 : 0)} ankle={(ankle ? 1 : 0)}") +
                                   (collar ? "" : " [collar: " + collarMiss + "]") + (ankle ? "" : " [ankle: " + string.Join("; ", _grabMiss) + "]"));
                ReleaseHand(a);
                ReleaseHand(b);
                yield break;
            }
            float grabbed = Time.fixedTime, loaded = -1f, clear = float.NegativeInfinity, clearAt = -1f;
            int tone = 0;
            _observe = () =>
            {
                float low = LowestPoint(r) - _vo.y;
                clear = Mathf.Max(clear, low);
                if (clearAt < 0f && low >= PairClear) clearAt = Time.fixedTime - grabbed;
                tone = Mathf.Max(tone, r.Tone);
                if (loaded < 0f && Loaded(_a)) loaded = Time.fixedTime - grabbed;
            };
            Vector3 ta = a.Target, tb = b.Target;
            yield return Move(0.5f, To(a, new Vector3(ta.x, _vo.y + Carry, ta.z)), To(b, new Vector3(tb.x, _vo.y + Carry, tb.z)));
            yield return Move(1.0f, To(a, a.Target), To(b, b.Target));
            float pelvisUp = r.Landmark(NpcLandmark.Pelvis).y - _vo.y;
            // In: the collar to z -0.55 (the head short of the partition, the feet inside the rear doors).
            Vector3 shift = _yaw * new Vector3(0f, 0f, -0.55f - L(a.Target).z);
            yield return Move(shift.magnitude / CarrySpeed, To(a, a.Target + shift, W(0.15f, 0f, 0.05f)), To(b, b.Target + shift, W(0f, 0f, -3.00f)));
            Vector3 down = Vector3.down * (Carry - 0.85f);
            yield return Move(0.4f, To(a, a.Target + down), To(b, b.Target + down));
            bool kept = !a.Lost && !b.Lost;
            var fa = new List<float>(a.Forces);
            var fb = new List<float>(b.Forces);
            var lags = new List<float>(a.Lags);
            lags.AddRange(b.Lags);
            ReleaseHand(a);
            ReleaseHand(b);
            yield return WaitFor(() => loaded >= 0f || Time.fixedTime - grabbed > PairLimit + 1f, 3f);
            _observe = null;
            float forceA = Mean(fa), forceB = Mean(fb);
            bool ok = kept && clearAt >= 0f && clearAt <= PairClearTime && loaded >= 0f && loaded <= PairLimit &&
                      forceA <= PairForce && forceB <= PairForce;
            Check(name, ok, Inv($"clear={clear:0.00}m, {PairClear:0.0} m at {Seconds(clearAt)} (limit {PairClearTime:0.0}) ") +
                            Inv($"loaded={LoadedText(loaded)} (limit {PairLimit:0} s) ") +
                            Inv($"force collar={forceA:0}N ankle={forceB:0}N (limit {PairForce:0} each) grip={(kept ? "kept" : "LOST")} ") +
                            Inv($"pelvis {pelvisUp:0.00} m up while carried, tone {tone} lag={Mean(lags):0.00}m (p95 {Percentile(lags, 0.95f):0.00})") +
                            (loaded < 0f ? " " + Why(_a) : ""));
        }

        // r12: two bodies in the bay (A, and B tossed on top of it), doors shut, the van driven: up to RideKmh, S-turns
        // (steer +-RideSteer, period RidePeriod) for RideSeconds, then braking to a stop. Both must stay loaded and in the
        // bay (pelvis and collar within 0.15 m of the box), no NaN, no body faster than ExplodeSpeed relative to the van.
        // INFO: speeds, the bodies' relative accelerations against the van's own (jitter would show as body accelerations
        // well above the van's), when and where a body left.
        private IEnumerator Ride()
        {
            const string name = "r12 van ride";
            Progress = name;
            NpcRagdoll ra = _a.Ragdoll, rb = _b.Ragdoll;
            Vector3 along = _yaw * Vector3.forward;
            bool aIn = Loaded(_a);
            if (!aIn)
            {
                // r7 did not load it: lay it in the bay so the ride is still tested.
                _a.InCargo = false;
                _a.Carrier = null;
                ra.PlaceLying(W(0f, 0.55f, -0.80f), along, true); // the feet well inside the rear doors
                yield return WaitFor(() => Loaded(_a), 3f);
            }
            _b.InCargo = false;
            _b.Carrier = null;
            Vector3 onA = ra.Landmark(NpcLandmark.Pelvis);
            onA.y = Highest(ra) + 0.05f;
            rb.PlaceLying(onA, along, true);
            // Setup, not a check: B dropped on A may slide off it for a while (step 3, run 1: still 0.37 m/s after 3 s
            // once r7 left A lying across the bay).
            yield return WaitFor(() => Loaded(_a) && Loaded(_b), 6f);
            if (_cargo.DoorOpen(0)) _cargo.ToggleDoor(0);
            if (_cargo.DoorOpen(1)) _cargo.ToggleDoor(1);
            yield return WaitFor(DoorsShut, 3f);
            bool relaid = false;
            if (!DoorsShut())
            {
                // A limb kept a door open (step 3, run 3: the slide stayed 0.18 open): both laid along the middle of the bay
                // (A as when r7 did not load it, B on A) and the doors given their time again. The ride must start shut
                // (GPT review 2026-10-07, finding 8: it used to start whatever the doors did).
                relaid = true;
                _a.InCargo = false;
                _a.Carrier = null;
                ra.PlaceLying(W(0f, 0.55f, -0.80f), along, true);
                _b.InCargo = false;
                _b.Carrier = null;
                Vector3 onA2 = ra.Landmark(NpcLandmark.Pelvis);
                onA2.y = Highest(ra) + 0.05f;
                rb.PlaceLying(onA2, along, true);
                yield return WaitFor(() => Loaded(_a) && Loaded(_b) && DoorsShut(), 6f);
            }
            bool both = Loaded(_a) && Loaded(_b);
            string notLoaded = (Loaded(_a) ? "" : " A " + Why(_a)) + (Loaded(_b) ? "" : " B " + Why(_b));
            float slideOpen = _cargo.Slide.Openness, rearOpen = RearOpenness(false);
            bool shut = DoorsShut();
            float doorsMax = 0f;

            _van.isKinematic = false;
            _van.linearVelocity = Vector3.zero;
            _van.angularVelocity = Vector3.zero;
            _vanCtl.Handbrake = false;
            _vanCtl.Steer = 0f;
            _vanCtl.Throttle = 0f;
            var npcs = new[] { _a, _b };
            var last = new Dictionary<Rigidbody, Vector3>();
            var jerks = new List<float>();
            var speeds = new List<float>(); // per tick of the turns: the fastest body relative to the van
            var vanAccels = new List<float>(); // per tick of the turns: the van's own horizontal acceleration
            float peak = 0f, topKmh = 0f, vanAccel = 0f, settledLate = 0f;
            string peakAt = "-";
            bool stayed = true, inside = true;
            string left = "";
            float t0 = Time.fixedTime, sStart = -1f;
            Vector3 vanV = _van.linearVelocity;
            int maxTicks = Ticks(6f + RideSeconds + 8f);
            for (int k = 0; k < maxTicks; k++)
            {
                float t = Time.fixedTime - t0;
                float kmh = _vanCtl.SpeedKmh;
                if (sStart < 0f && (kmh >= RideKmh - 2f || t >= 6f)) sStart = t;
                bool turning = sStart >= 0f && t < sStart + RideSeconds;
                bool braking = sStart >= 0f && t >= sStart + RideSeconds;
                if (braking && kmh < 1.5f) break;
                _vanCtl.Throttle = braking ? -0.5f : Mathf.Clamp((RideKmh - kmh) * 0.2f, -1f, 1f);
                _vanCtl.Steer = turning ? RideSteer * Mathf.Sin(2f * Mathf.PI * (t - sStart) / RidePeriod) : 0f;
                yield return Fixed;
                AfterTick();
                doorsMax = Mathf.Max(doorsMax, Mathf.Max(_cargo.Slide.Openness, RearOpenness(false)));
                topKmh = Mathf.Max(topKmh, _vanCtl.SpeedKmh);
                Vector3 v = _van.linearVelocity;
                float vanNow = Flat(v - vanV).magnitude / Time.fixedDeltaTime;
                if (t > 0.5f) vanAccel = Mathf.Max(vanAccel, vanNow); // not while it settles on its wheels
                if (turning) vanAccels.Add(vanNow);
                vanV = v;
                float worstJerk = 0f, fastest = 0f;
                foreach (GreyboxNpc npc in npcs)
                {
                    NpcRagdoll r = npc.Ragdoll;
                    if (!r.Active)
                    {
                        if (stayed) left += Inv($" {npc.name} not a ragdoll at {t:0.0}s ({npc.State});");
                        stayed = false;
                        continue;
                    }
                    if (!Loaded(npc) && stayed)
                    {
                        stayed = false;
                        left += Inv($" {npc.name} unloaded at {t:0.0}s {Why(npc)};");
                    }
                    if (inside && (!_space.Contains(r.Landmark(NpcLandmark.Pelvis), 0.15f) || !_space.Contains(r.Landmark(NpcLandmark.Collar), 0.15f)))
                    {
                        inside = false;
                        left += Inv($" {npc.name} out of the bay at {t:0.0}s {Why(npc)};");
                    }
                    for (int i = 0; i < r.PartCount; i++)
                    {
                        Rigidbody body = r.BodyOf(i);
                        Vector3 rel = body.linearVelocity - _space.PointVelocity(body.worldCenterOfMass);
                        float speed = rel.magnitude;
                        fastest = Mathf.Max(fastest, speed);
                        if (speed > peak)
                        {
                            peak = speed;
                            peakAt = Inv($"{npc.name}/{r.Profile.Parts[i].Name} at {t:0.0}s");
                        }
                        if (last.TryGetValue(body, out Vector3 before)) worstJerk = Mathf.Max(worstJerk, (rel - before).magnitude / Time.fixedDeltaTime);
                        last[body] = rel;
                    }
                }
                if (turning)
                {
                    jerks.Add(worstJerk);
                    speeds.Add(fastest);
                }
                if (turning && t > sStart + RideSeconds - 3f) settledLate = Mathf.Max(settledLate, fastest);
            }
            _vanCtl.Throttle = 0f;
            _vanCtl.Steer = 0f;
            _vanCtl.Handbrake = true;
            yield return Idle(1f);
            float travelled = Flat(_van.position - _vo).magnitude;
            ParkVan();
            yield return Idle(0.3f);
            bool ok = both && shut && doorsMax <= 0.05f && stayed && inside && peak <= ExplodeSpeed && !_nan && sStart >= 0f;
            Check(name, ok, Inv($"loaded before={(both ? "both" : "NOT both" + notLoaded)}{(aIn ? "" : " (A laid in: r7 did not load it)")} ") +
                            Inv($"doors open slide {slideOpen:0.00} rear {rearOpen:0.00} before the ride (limit 0.01{(relaid ? "; bodies re-laid along the bay to free a door" : "")}), at most {doorsMax:0.00} during it (limit 0.05); ") +
                            Inv($"top {topKmh:0} km/h, {travelled:0} m; stayed loaded={(stayed ? 1 : 0)} in the bay={(inside ? 1 : 0)}{left}; ") +
                            Inv($"peak relative speed {peak:0.00} m/s ({peakAt}; limit {ExplodeSpeed:0}); in the turns the fastest body p50 {Percentile(speeds, 0.5f):0.00} p95 {Percentile(speeds, 0.95f):0.00} m/s, last 3 s <= {settledLate:0.00} m/s (INFO); ") +
                            Inv($"in the turns the bodies' worst relative acceleration p50 {Percentile(jerks, 0.5f):0.0} p95 {Percentile(jerks, 0.95f):0.0} max {Max(jerks):0.0} m/s2 vs the van's own p50 {Percentile(vanAccels, 0.5f):0.0} p95 {Percentile(vanAccels, 0.95f):0.0} m/s2 (INFO); van peak {vanAccel:0.0} m/s2"));
        }

        // r11: a passenger hit in the bay lies down there as the ragdoll. A is taken out first; B (lying in the bay) wakes and
        // sits up (the ragdoll hands over to the seated capsule), then the fist from beside it.
        private IEnumerator SeatedHit()
        {
            const string name = "r11 hit in the van";
            Progress = name;
            NpcRagdoll ra = _a.Ragdoll, rb = _b.Ragdoll;
            if (ra.Active)
            {
                _a.InCargo = false;
                _a.Carrier = null;
                ra.PlaceLying(W(-4f, 0f, -1f), _yaw * Vector3.forward, true);
            }
            if (!rb.Active || !Loaded(_b))
            {
                Check(name, false, Inv($"B is not lying loaded in the bay (ragdoll={(rb.Active ? 1 : 0)} loaded={(Loaded(_b) ? 1 : 0)})"));
                yield break;
            }
            yield return Idle(0.5f);
            yield return WakeInVan();
            bool sat = _b.State == NpcState.CargoSeated && !rb.Active && _b.Body.Seated && Loaded(_b);
            yield return Idle(0.4f);
            Vector3 at = _b.Center + Vector3.up * 0.3f;
            _b.Hit(WeaponStun.Fist, HitZone.Torso, at + _yaw * Vector3.right, at);
            _keepDown.Add(_b);
            KeepStunned();
            bool down = _b.State == NpcState.Down && rb.Active && !_b.Body.Active;
            float peak = 0f;
            _observe = () =>
            {
                if (rb.Active) peak = Mathf.Max(peak, rb.MaxRelativeSpeed(null));
            };
            yield return Idle(1.5f);
            _observe = null;
            bool inBay = rb.Active && _space.Contains(rb.Landmark(NpcLandmark.Pelvis)) && _space.Contains(rb.Landmark(NpcLandmark.Collar));
            float still = rb.Active ? rb.MaxRelativeSpeed(null) : -1f;
            Check(name, sat && down && inBay && Loaded(_b) && peak <= BlowSpeed,
                Inv($"sat up in the bay={(sat ? 1 : 0)}; after the fist: ragdoll={(down ? 1 : 0)} in the bay={(inBay ? 1 : 0)} loaded={(Loaded(_b) ? 1 : 0)} ") +
                Inv($"peak body speed {peak:0.00} m/s (limit {BlowSpeed:0}), {still:0.00} m/s after 1.5 s"));
        }

        // r14 (step 3, §4.5): B lying loaded in the bay wakes and sits up there: SitUp_Cargo on the seated capsule, then the
        // controller's Cargo_Sit_Idle. It must be seated (CargoSeated, the seated capsule on, the ragdoll gone) and still
        // loaded; both clips must be seen; nothing may pop (PopLimit between two drawn frames); the head top stays under
        // SitHeadLimit over the bay floor; the hips stay in the bay. INFO: where it sits, the seat's shift, the lying Hips.
        private IEnumerator WakeInVan()
        {
            const string name = "r14 wake in the van";
            Progress = name;
            NpcRagdoll r = _b.Ragdoll;
            NpcRagdollProfile p = r.Profile;
            NpcGetUp up = _b.GetUp;
            if (!r.Active || up == null || !up.CanSitUp)
            {
                Check(name, false, Inv($"cannot start: ragdoll={(r.Active ? 1 : 0)} clips={(up != null && up.CanSitUp ? 1 : 0)}"));
                yield return SitUp(_b);
                yield break;
            }
            Transform hips = r.Hips, head = r.BoneOf(p.IndexOf(Kind.Head)), top = head;
            foreach (Transform t in _b.GetComponentsInChildren<Transform>(true))
                if (t.name == "mixamorig:HeadTop_End") top = t;
            Animator animator = r.Animator;
            Vector3 lastHips = hips.position, lastHead = head.position;
            float floor = _space.LocalBox.min.y;
            Time.timeScale = 1f; // as in r8: drawn frames close together, so a pop stands out
            _keepDown.Remove(_b);
            _b.StunTotal = 8f;
            _b.StunLeft = 0.05f;
            bool sitUp = false, idle = false, inBay = true;
            float pop = 0f, height = float.MinValue, travel = 0f, seatedAt = -1f;
            Vector3 headAtStart = head.position;
            int frame = Time.frameCount;
            for (int k = 0; k < Ticks(3.2f); k++)
            {
                yield return Fixed;
                AfterTick();
                if (Time.frameCount != frame)
                {
                    frame = Time.frameCount;
                    pop = Mathf.Max(pop, Mathf.Max(Vector3.Distance(hips.position, lastHips), Vector3.Distance(head.position, lastHead)));
                    lastHips = hips.position;
                    lastHead = head.position;
                }
                if (_b.State != NpcState.CargoSeated) continue;
                if (seatedAt < 0f)
                {
                    seatedAt = Time.fixedTime;
                    headAtStart = head.position;
                }
                if (Time.fixedTime - seatedAt <= BlendWindow) travel = Mathf.Max(travel, Vector3.Distance(head.position, headAtStart));
                height = Mathf.Max(height, _space.ToLocal(top.position).y - floor);
                inBay &= _space.Contains(hips.position, 0.05f);
                if (animator == null || !animator.enabled) continue;
                AnimatorStateInfo state = animator.GetCurrentAnimatorStateInfo(0);
                sitUp |= state.IsName(p.SitUp.State);
                idle |= state.IsName(p.SitIdle.State);
            }
            Time.timeScale = Mathf.Max(0.1f, TimeScale);
            bool seated = _b.State == NpcState.CargoSeated && !r.Active && _b.Body.Active && _b.Body.Seated &&
                          _b.Body.gameObject.layer == OvLayers.NpcSeated && Loaded(_b);
            Record("sitting in the van (B, r14)", idle, idle ? p.SitIdle.State : "not seen", p.SitIdle.State);
            Vector3 at = L(_b.transform.position);
            Check(name, seated && sitUp && idle && pop <= PopLimit && travel <= TravelLimit && height <= SitHeadLimit && inBay,
                Inv($"seated={(seated ? 1 : 0)} (loaded={(Loaded(_b) ? 1 : 0)}), {p.SitUp.State} {(sitUp ? "seen" : "NOT SEEN")}, {p.SitIdle.State} {(idle ? "seen" : "NOT SEEN")}; ") +
                Inv($"largest move of hips/head between drawn frames {pop:0.00} m (limit {PopLimit:0.0}); the head travelled {travel:0.00} m in the first {BlendWindow:0.00} s (limit {TravelLimit:0.0}); ") +
                Inv($"head top at most {height:0.00} m over the floor (limit {SitHeadLimit:0.00}); hips in the bay={(inBay ? 1 : 0)}; ") +
                Inv($"INFO sits at ({at.x:0.00}, {at.z:0.00}) van-local, seat shift {up.Shift:0.00} m, lying Hips {up.LyingHips:0.00} m vs the clip's {p.SitUp.HipsStart.y:0.00} m"));
        }

        // r13: the tumble out of a fast van as the ragdoll. B sits up in the bay again, is put just outside the sliding
        // doorway at floor height facing out, and leaves the cargo the way GreyboxVanCargo.GetOut lets a passenger out
        // above EscapeTumbleKmh: LeaveCargo(true) with its velocity (the van's 20 km/h plus 2.5 m/s out of the door).
        private IEnumerator Tumble()
        {
            const string name = "r13 tumble out of the van";
            Progress = name;
            NpcRagdoll rb = _b.Ragdoll;
            yield return SitUp(_b);
            if (_b.State != NpcState.CargoSeated || _b.Body.Rigidbody == null)
            {
                Check(name, false, $"B did not sit up in the bay ({_b.State})");
                yield break;
            }
            // Step 4: from the escape scramble (Escaping: the run for the door), as GreyboxVanCargo lets a runner out.
            _b.BeginEscape();
            bool escaping = _b.State == NpcState.Escaping;
            Rigidbody seat = _b.Body.Rigidbody;
            Vector3 outside = W(SlideEdgeX + 0.35f, 0.57f, -0.25f);
            Quaternion facing = _yaw * Quaternion.LookRotation(Vector3.right);
            seat.position = outside;
            seat.rotation = facing;
            seat.linearVelocity = Vector3.zero;
            _b.transform.SetPositionAndRotation(outside, facing);
            Physics.SyncTransforms();
            Vector3 velocity = _yaw * new Vector3(2.5f, 0.3f, 5.6f);
            _b.LeaveCargo(true, velocity);
            _keepDown.Add(_b);
            KeepStunned();
            bool rag = rb.Active && _b.State == NpcState.Down && !_b.InCargo && !_b.Body.Active;
            float peak = 0f;
            _observe = () =>
            {
                if (rb.Active) peak = Mathf.Max(peak, rb.MaxRelativeSpeed(null));
            };
            yield return Idle(3f);
            _observe = null;
            float pelvisUp = rb.Active ? rb.Landmark(NpcLandmark.Pelvis).y - _o.y : -1f;
            bool outOfBay = rb.Active && !_space.Contains(rb.Landmark(NpcLandmark.Pelvis), 0.15f);
            float still = rb.Active ? rb.MaxRelativeSpeed(null) : -1f;
            float travelled = rb.Active ? Flat(rb.Landmark(NpcLandmark.Pelvis) - outside).magnitude : -1f;
            Check(name, escaping && rag && outOfBay && pelvisUp >= 0f && pelvisUp <= 0.35f && peak <= BlowSpeed && !_nan,
                Inv($"from the escape={(escaping ? 1 : 0)} ragdoll={(rag ? 1 : 0)} out of the bay={(outOfBay ? 1 : 0)}; after 3 s the pelvis {pelvisUp:0.00} m above the ground (limit 0.35), ") +
                Inv($"{travelled:0.0} m from the door, {still:0.00} m/s; peak body speed {peak:0.0} m/s (start {velocity.magnitude:0.0}, limit {BlowSpeed:0})"));
        }

        // r18 (step 4, design §4.5): out of a parked van. B (lying outside after r13) is laid in the bay along it and loads;
        // the sliding door opens all the way with the van standing (the handbrake); B wakes, sits up, notices the door, runs
        // for it and hops down out of it (GreyboxNpc.JumpOut: NpcGetUp's procedural hop, the Cargo_JumpOut clip once
        // installed) and runs off. Real time from the wake, so a pop stands out. Pass: free within JumpOutLimit of waking,
        // the sit-up, the escape run and the hop seen, landed at least 0.3 m out from the doorway on the ground (not in the
        // bay), nothing popping between drawn frames during the hop (PopLimit), the hips never under the ground. INFO: the
        // hop's length and landing.
        private IEnumerator JumpOutCheck()
        {
            const string name = "r18 out of a standing van (hop)";
            Progress = name;
            NpcRagdoll rb = _b.Ragdoll;
            if (!rb.Active)
            {
                _b.Hit(WeaponStun.Fist, HitZone.Torso, _b.Center + Vector3.up, _b.Center);
                _keepDown.Add(_b);
                KeepStunned();
            }
            if (!rb.Active)
            {
                Check(name, false, Inv($"B is not a ragdoll ({_b.State})"));
                yield break;
            }
            _b.InCargo = false;
            _b.Carrier = null;
            rb.PlaceLying(W(0f, 0.55f, -0.80f), _yaw * Vector3.forward, true);
            KeepStunned();
            yield return WaitFor(() => Loaded(_b), 3f);
            // The sliding door all the way open first, while B is still out cold (an Out body stays put): in run 2 the door
            // opened in front of the sitter, who ran for it at 30 % open (the stage-1 rule) and was still 0.37 m inside the
            // doorway 6 s later (the panel still moving across, it gives up and tries again 2 s later): the escape rule,
            // not the hop this check is about.
            yield return EnsureOpen(0);
            _doorsTouched = true;
            Transform hips = rb.Hips, head = rb.BoneOf(rb.Profile.IndexOf(Kind.Head));
            Time.timeScale = 1f;
            // Wakes: sits up (SitUp_Cargo), sees the open door, runs for it, hops out.
            _keepDown.Remove(_b);
            _b.StunTotal = 8f;
            _b.StunLeft = 0.05f;
            float t0 = Time.fixedTime, freeAt = -1f, hopAt = -1f, pop = 0f, sunk = -1f, hopSeconds = 0f;
            bool escaped = false, seated = false, escapeShown = false;
            string[] escapeStates = With(RoleStates(_b, NpcAnimContract.RoleScrambleStart, NpcAnimContract.RoleScramble), NpcAnimContract.EscapeFallbackState);
            Vector3 lastHips = hips.position, lastHead = head.position;
            int frame = Time.frameCount;
            for (int k = 0; k < Ticks(JumpOutLimit + 1f) && freeAt < 0f; k++)
            {
                yield return Fixed;
                AfterTick();
                seated |= _b.State == NpcState.CargoSeated;
                escaped |= _b.State == NpcState.Escaping;
                if (_b.State == NpcState.Escaping && !escapeShown) escapeShown = PlaysAny(_b, escapeStates);
                bool hopping = _b.State == NpcState.GettingUp && _b.GetUp.Kind == GetUpKind.JumpOut;
                if (hopping && hopAt < 0f)
                {
                    hopAt = Time.fixedTime - t0;
                    hopSeconds = _b.GetUp.ClipSeconds;
                    lastHips = hips.position;
                    lastHead = head.position;
                }
                if (Time.frameCount != frame)
                {
                    frame = Time.frameCount;
                    if (hopping) pop = Mathf.Max(pop, Mathf.Max(Vector3.Distance(hips.position, lastHips), Vector3.Distance(head.position, lastHead)));
                    lastHips = hips.position;
                    lastHead = head.position;
                }
                if (hopAt >= 0f) sunk = Mathf.Max(sunk, _vo.y - hips.position.y);
                if (_b.State == NpcState.Free) freeAt = Time.fixedTime - t0;
            }
            Time.timeScale = Mathf.Max(0.1f, TimeScale);
            Record("escaping (B, r18)", escapeShown, escapeShown ? "seen" : escaped ? "not seen while escaping" : "never escaped", escapeStates);
            Vector3 at = _b.transform.position;
            float outward = L(at).x - SlideEdgeX;
            bool onGround = Mathf.Abs(at.y - _vo.y) <= 0.1f && !_space.Contains(at + Vector3.up * 0.5f);
            var controller = _b.GetComponent<CharacterController>();
            Check(name, freeAt >= 0f && freeAt <= JumpOutLimit && seated && escaped && hopAt >= 0f && outward >= 0.3f && onGround &&
                        pop <= PopLimit && sunk <= 0.05f && controller.enabled,
                Inv($"free after {Seconds(freeAt)} of waking (limit {JumpOutLimit:0} s), sat up={(seated ? 1 : 0)} ran for it={(escaped ? 1 : 0)}, hop at {Seconds(hopAt)} ") +
                Inv($"({hopSeconds:0.00} s{(_b.GetUp.State != null ? ", clip " + _b.GetUp.State : ", procedural")}); landed {outward:0.00} m out from the doorway (limit 0.3) ") +
                Inv($"on the ground={(onGround ? 1 : 0)}; largest move of hips/head between drawn frames in the hop {pop:0.00} m (limit {PopLimit:0.0}), ") +
                Inv($"hips at most {Mathf.Max(0f, sunk) * 100f:0} cm under the ground (limit 5); controller on={(controller.enabled ? 1 : 0)}"));
        }

        // Wakes a body lying in the bay: it sits up there (CargoSeated), the doors stay as they are (shut: no escape).
        private IEnumerator SitUp(GreyboxNpc npc)
        {
            _keepDown.Remove(npc);
            npc.StunTotal = 8f;
            npc.StunLeft = 0.05f;
            yield return WaitFor(() => npc.State == NpcState.CargoSeated || npc.State == NpcState.Free, 1.5f);
        }

        // ---------- r20, r21: the Animator contract (step 5) ----------

        // Per NPC: ticks it lay as the ragdoll (and of those, with its Animator on), ticks NpcGetUp owned the Animator (and
        // of those, with a driver write or a parameter changed since that get-up's first tick).
        private sealed class AnimWatch
        {
            public int Ragdoll, AnimatorOn, Owned, Writes, Changed;
            public int OwnerWrites = -1, WritesAt;
            public string Parameters, First;
        }

        private readonly Dictionary<GreyboxNpc, AnimWatch> _animWatch = new();
        private readonly List<string> _states = new(); // r21: "situation: state" lines
        private int _statesOk, _statesSeen;

        private void WatchAnim(GreyboxNpc npc)
        {
            NpcAnimDriver driver = npc != null ? npc.Anim : null;
            Animator animator = driver != null ? driver.Animator : null;
            if (animator == null) return;
            if (!_animWatch.TryGetValue(npc, out AnimWatch w)) _animWatch[npc] = w = new AnimWatch();
            if (npc.Ragdoll != null && npc.Ragdoll.Active)
            {
                w.Ragdoll++;
                if (animator.enabled)
                {
                    w.AnimatorOn++;
                    w.First ??= $"{npc.name}: Animator on while a ragdoll ({Progress})";
                }
                w.Parameters = null;
                return;
            }
            if (npc.GetUp == null || !npc.GetUp.Owns || !animator.isActiveAndEnabled)
            {
                w.Parameters = null;
                return;
            }
            w.Owned++;
            string now = AnimParameters(animator);
            if (w.Parameters == null || driver.OwnerWrites != w.OwnerWrites)
            {
                // A get-up's first tick (or a new one): what NpcGetUp's start wrote.
                w.Parameters = now;
                w.OwnerWrites = driver.OwnerWrites;
                w.WritesAt = driver.Writes;
                return;
            }
            if (driver.Writes != w.WritesAt)
            {
                w.Writes++;
                w.WritesAt = driver.Writes;
                w.First ??= $"{npc.name}: a driver write during {npc.GetUp.Kind} ({Progress})";
            }
            if (now != w.Parameters)
            {
                w.Changed++;
                w.First ??= $"{npc.name}: parameters changed during {npc.GetUp.Kind} ({Progress}): {w.Parameters} -> {now}";
                w.Parameters = now;
            }
        }

        private static string AnimParameters(Animator a) =>
            Inv($"stun {a.GetInteger(NpcAnimContract.StunPhase)} cargo {a.GetBool(NpcAnimContract.InCargo)} panic {a.GetBool(NpcAnimContract.Panic)} ") +
            Inv($"activity {a.GetInteger(NpcAnimContract.Activity)} getUp {a.GetInteger(NpcAnimContract.GetUp)} speed {a.GetFloat(NpcAnimContract.Speed):0.00} ") +
            Inv($"mul {a.GetFloat(NpcAnimContract.SpeedMul):0.00} driven {a.GetBool(NpcAnimContract.Driven)} ragdoll {a.GetBool(NpcAnimContract.Ragdoll)}");

        // r21: a situation's result worked out by the caller.
        private void Record(string situation, bool ok, string now, params string[] expected)
        {
            _statesSeen++;
            if (ok) _statesOk++;
            _states.Add($"{situation}: {now}{(ok ? "" : " (expected " + string.Join(" or ", expected) + ")")}");
        }

        // The state names of these roles' clips where the NPC's controller has them.
        private static string[] RoleStates(GreyboxNpc npc, params string[] roles)
        {
            var states = new List<string>();
            NpcAnimDriver d = npc != null ? npc.Anim : null;
            foreach (string role in roles)
                if (d != null && d.Has(role)) states.Add(d.Clip(role).State);
            return states.ToArray();
        }

        private static string[] With(string[] list, params string[] more)
        {
            var all = new List<string>(list);
            all.AddRange(more);
            return all.ToArray();
        }

        // The NPC's base layer is in (or going into) one of 'states'.
        private static bool PlaysAny(GreyboxNpc npc, string[] states)
        {
            Animator a = npc != null && npc.Anim != null ? npc.Anim.Animator : null;
            if (a == null || !a.isActiveAndEnabled) return false;
            AnimatorStateInfo current = a.GetCurrentAnimatorStateInfo(0), next = a.GetNextAnimatorStateInfo(0);
            foreach (string s in states)
                if (current.IsName(s) || (a.IsInTransition(0) && next.IsName(s))) return true;
            return false;
        }

        // r21: a crowd NPC walking its route (not one of the test's) plays Walk.
        private void SawCrowdWalker()
        {
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || IsTaken(npc) || npc.State != NpcState.Free || npc.Fleeing || !npc.TryGetComponent(out CrowdWalker walker) ||
                    walker.State != CrowdWalker.Mode.Route || !npc.TryGetComponent(out CharacterController controller) || !controller.enabled)
                    continue;
                float speed = Flat(controller.velocity).magnitude;
                if (speed < 0.6f || speed > 2f) continue;
                Saw(Inv($"a crowd walker at {speed:0.0} m/s ({npc.name})"), npc, NpcAnimContract.WalkState);
                return;
            }
        }

        // r21: records whether 'npc' plays one of 'states' now (the base layer, a transition into one counts).
        private void Saw(string situation, GreyboxNpc npc, params string[] states)
        {
            Animator a = npc != null && npc.Anim != null ? npc.Anim.Animator : null;
            string now = "Animator off";
            bool ok = false;
            if (a != null && a.isActiveAndEnabled)
            {
                ok = PlaysAny(npc, states);
                now = StateName(a, a.GetCurrentAnimatorStateInfo(0)) + (a.IsInTransition(0) ? " -> " + StateName(a, a.GetNextAnimatorStateInfo(0)) : "");
            }
            Record(situation, ok, now, states);
        }

        // The base-layer state's name among the controller's clips (by name hash), for the report.
        private static string StateName(Animator a, AnimatorStateInfo info)
        {
            foreach (string s in new[] { NpcAnimContract.IdleState, NpcAnimContract.WalkState, NpcAnimContract.RunState, NpcAnimContract.DownState,
                         NpcAnimContract.RagdollState, NpcAnimContract.EscapeFallbackState, NpcAnimContract.CargoFallbackState })
                if (info.IsName(s)) return s;
            foreach (AnimationClip clip in a.runtimeAnimatorController.animationClips)
                if (clip != null && info.IsName(clip.name)) return clip.name;
            return "#" + info.shortNameHash;
        }

        private void AnimContract()
        {
            Progress = "r20 r21 animator";
            SawCrowdWalker();
            int ragdoll = 0, owned = 0, on = 0, writes = 0, changed = 0;
            string first = null;
            foreach (AnimWatch w in _animWatch.Values)
            {
                ragdoll += w.Ragdoll;
                owned += w.Owned;
                on += w.AnimatorOn;
                writes += w.Writes;
                changed += w.Changed;
                first ??= w.First;
            }
            Check("r20 one writer (NpcAnimDriver)", ragdoll > 0 && owned > 0 && on == 0 && writes == 0 && changed == 0,
                Inv($"{_animWatch.Count} NPCs: {ragdoll} ticks as a ragdoll, Animator on in {on} (limit 0); {owned} ticks NpcGetUp owned the Animator, ") +
                Inv($"driver writes in {writes}, parameters changed in {changed} (limit 0 each){(first != null ? "; first: " + first : "")}"));
            Check("r21 animator states by situation", _statesSeen > 0 && _statesOk == _statesSeen,
                Inv($"{_statesOk}/{_statesSeen}: ") + string.Join("; ", _states));
        }

        // ---------- T2: performance probe (INFO) ----------

        private IEnumerator Perf()
        {
            Progress = "T2 perf";
            GreyboxNpc template = null;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && npc.isActiveAndEnabled && npc.State == NpcState.Free && !npc.InCargo && !PoliceOfficer.IsOfficer(npc) &&
                    npc.Ragdoll != null && npc.Ragdoll.Ready && !IsTaken(npc))
                {
                    template = npc;
                    break;
                }
            if (template == null)
            {
                Line($"{Tag} INFO T2 perf: skipped (no free NPC to copy)");
                yield break;
            }
            int asleepN = Mathf.Max(0, PerfAsleep), awakeN = Mathf.Max(0, PerfAwake), total = asleepN + awakeN;
            NpcRagdoll.Cap = Mathf.Max(_cap0, NpcRagdoll.ActiveCount + total + 1);
            // Copies of a free crowd NPC, made under an inactive parent so their crowd walker, police role and sea tracker
            // are gone before they wake (the crowd and the scene are not touched).
            _cloneHolder = new GameObject("RagdollProbe_Holder");
            _cloneHolder.SetActive(false);
            var probes = new List<GreyboxNpc>();
            for (int i = 0; i < total; i++)
            {
                GameObject go = Instantiate(template.gameObject, _cloneHolder.transform);
                go.name = $"RagdollProbe_{i:00}";
                foreach (CrowdWalker w in go.GetComponents<CrowdWalker>()) DestroyImmediate(w);
                foreach (PoliceOfficer o in go.GetComponents<PoliceOfficer>()) DestroyImmediate(o);
                foreach (SeaReturnTracker s in go.GetComponents<SeaReturnTracker>()) DestroyImmediate(s);
                go.transform.SetPositionAndRotation(PerfSpot(i, asleepN), _yaw);
                go.transform.SetParent(null, true); // active now: Awake and OnEnable run
                _clones.Add(go);
                probes.Add(go.GetComponent<GreyboxNpc>());
            }
            yield return null; // Start
            var builds = new List<float>();
            foreach (GreyboxNpc npc in probes)
            {
                if (npc == null) continue;
                npc.Hit(WeaponStun.Fist, HitZone.Torso, npc.transform.position + npc.transform.forward, npc.Center);
                _keepDown.Add(npc);
                if (npc.Ragdoll.Active) builds.Add((float)NpcRagdoll.LastBuildMilliseconds);
            }
            KeepStunned();
            int ragdolls = 0;
            foreach (GreyboxNpc npc in probes)
                if (npc != null && npc.Ragdoll.Active) ragdolls++;
            Vector3 along = _yaw * Vector3.forward;
            for (int i = 0; i < probes.Count; i++)
                if (probes[i] != null && probes[i].Ragdoll.Active) probes[i].Ragdoll.PlaceLying(PerfSpot(i, asleepN), along, true);
            // Until the lying ones sleep (at most 8 s).
            int asleep = 0;
            for (int k = 0; k < Ticks(8f); k++)
            {
                yield return Fixed;
                AfterTick();
                asleep = Sleeping(probes, 0, asleepN);
                if (asleep >= asleepN) break;
            }
            float waited = 0f;
            Time.timeScale = 1f;
            yield return null;
            var handles = new List<ProfilerRecorderHandle>();
            ProfilerRecorderHandle.GetAvailable(handles);
            string marker = null;
            ProfilerRecorder recorder = default;
            foreach (string wanted in new[] { "Physics.Simulate", "FixedUpdate.PhysicsFixedUpdate", "Physics.Processing" })
            {
                foreach (ProfilerRecorderHandle handle in handles)
                {
                    if (ProfilerRecorderHandle.GetDescription(handle).Name != wanted) continue;
                    recorder = new ProfilerRecorder(handle, 1, ProfilerRecorderOptions.Default);
                    recorder.Start();
                    marker = wanted;
                    break;
                }
                if (marker != null) break;
            }
            var baseline = new List<float>();
            var loaded = new List<float>();
            var steps = new List<float>();
            int stepsAt = _fixedSteps;
            for (int f = 0; f < 60 + PerfFrames; f++)
            {
                if (f >= 60 && (f - 60) % 100 == 0)
                    for (int i = asleepN; i < probes.Count; i++)
                        if (probes[i] != null && probes[i].Ragdoll.Active)
                            probes[i].Ragdoll.PlaceLying(PerfSpot(i, asleepN) + Vector3.up * 1.2f, along, true);
                yield return null;
                KeepStunned();
                waited += Time.unscaledDeltaTime;
                float ms = recorder.Valid ? recorder.LastValue * 1e-6f : 0f;
                if (f < 60) baseline.Add(ms);
                else
                {
                    loaded.Add(ms);
                    steps.Add(_fixedSteps - stepsAt);
                }
                stepsAt = _fixedSteps;
            }
            if (recorder.Valid) recorder.Dispose();
            int awakeEnd = probes.Count - asleepN - Sleeping(probes, asleepN, probes.Count);
            Time.timeScale = Mathf.Max(0.1f, TimeScale);
            float perStep = Mean(steps) > 0f ? Mean(loaded) / Mean(steps) : 0f;
            Line(Inv($"{Tag} INFO T2 perf: {ragdolls} ragdolls of {total} copies ({asleep}/{asleepN} asleep before, {awakeN} dropped awake from 1.2 m every 100 frames), ") +
                 Inv($"marker '{marker ?? "none"}': 40 asleep {Mean(baseline):0.00} ms/frame; with the drops mean {Mean(loaded):0.00} p95 {Percentile(loaded, 0.95f):0.00} ") +
                 Inv($"max {Max(loaded):0.00} ms/frame, {Mean(steps):0.00} physics steps/frame -> {perStep:0.00} ms/step ({PerfFrames} frames in {waited:0.0} s real); ") +
                 Inv($"awake at the end {awakeEnd}; knockdown build mean {Mean(builds):0.00} max {Max(builds):0.00} ms (budget 0.5)"));
            foreach (GreyboxNpc npc in probes) _keepDown.Remove(npc);
            foreach (GameObject clone in _clones)
                if (clone != null) Destroy(clone);
            _clones.Clear();
            if (_cloneHolder != null) Destroy(_cloneHolder);
            _cloneHolder = null;
            NpcRagdoll.Cap = _cap0;
            yield return Fixed;
        }

        // A grid of asleepN lying places (5 across, 2.5 m apart) on the far side of the sandbox, then a row for the rest.
        private Vector3 PerfSpot(int i, int asleepN)
        {
            if (i < asleepN) return _o + _yaw * new Vector3(-45f + 2.5f * (i % 5), 0f, -45f + 2.5f * (i / 5));
            int j = i - asleepN;
            return _o + _yaw * new Vector3(-30f, 0f, -45f + 2.5f * j);
        }

        private static int Sleeping(List<GreyboxNpc> npcs, int from, int to)
        {
            int n = 0;
            for (int i = from; i < to && i < npcs.Count; i++)
            {
                NpcRagdoll r = npcs[i] != null ? npcs[i].Ragdoll : null;
                if (r == null || !r.Active) continue;
                bool all = true;
                for (int p = 0; p < r.PartCount && all; p++) all = r.BodyOf(p).IsSleeping();
                if (all) n++;
            }
            return n;
        }

        private bool IsTaken(GreyboxNpc npc)
        {
            foreach (Taken t in _taken)
                if (t.Npc == npc) return true;
            return false;
        }

        // ---------- Helpers: the van ----------

        private Vector3 W(float x, float y, float z) => _vo + _yaw * new Vector3(x, y, z);
        private Vector3 L(Vector3 world) => Quaternion.Inverse(_yaw) * (world - _vo);
        private bool Loaded(GreyboxNpc npc) => npc.InCargo && ReferenceEquals(npc.Carrier, _space);

        private IEnumerator EnsureOpen(int door)
        {
            if (!_cargo.DoorOpen(door)) _cargo.ToggleDoor(door);
            yield return WaitFor(() => door == 0 ? _cargo.Slide.Openness >= 0.99f : RearOpenness(true) >= 0.99f, 3f);
        }

        private bool DoorsShut() => _cargo.Slide.Openness <= 0.01f && RearOpenness(false) <= 0.01f;

        // min: the less open of the two rear leaves; otherwise the wider.
        private float RearOpenness(bool min)
        {
            float l = _cargo.RearLeft != null ? _cargo.RearLeft.Openness : min ? 1f : 0f;
            float r = _cargo.RearRight != null ? _cargo.RearRight.Openness : min ? 1f : 0f;
            return min ? Mathf.Min(l, r) : Mathf.Max(l, r);
        }

        // Lays the NPC's ragdoll on its back with its head top at 'headTop' (flat), head along 'headDir', not loaded, at
        // rest, then lets it settle.
        private IEnumerator PlaceFor(GreyboxNpc npc, Vector3 headTop, Vector3 headDir)
        {
            foreach (Hand h in _hands) ReleaseHand(h);
            _observe = null;
            NpcRagdoll r = npc.Ragdoll;
            npc.InCargo = false;
            npc.Carrier = null;
            Vector3 dir = Flat(headDir).normalized;
            Vector3 spot = new Vector3(headTop.x, _vo.y, headTop.z) - dir * 0.95f;
            r.PlaceLying(spot, dir, true);
            Vector3 miss = Flat(headTop - HeadTop(r));
            r.PlaceLying(spot + miss, dir, true);
            npc.InCargo = false;
            npc.Carrier = null;
            KeepStunned();
            yield return Idle(0.6f);
        }

        private static Vector3 HeadTop(NpcRagdoll r)
        {
            int head = r.Profile.IndexOf(Kind.Head);
            NpcRagdollProfile.Part part = r.Profile.Parts[head];
            return r.PartCenter(head) + (r.BodyOf(head).rotation * part.Up).normalized * (part.Height * 0.5f);
        }

        // The end of the feet farthest from the head (heels or toes, whichever sticks out).
        private static Vector3 LowFootTip(NpcRagdoll r)
        {
            Vector3 head = HeadTop(r);
            Vector3 best = r.Landmark(NpcLandmark.LeftAnkle);
            float far = -1f;
            foreach (Collider c in r.Colliders)
            {
                if (!(c is BoxCollider box)) continue;
                Bounds b = box.bounds;
                for (int corner = 0; corner < 8; corner++)
                {
                    var p = new Vector3((corner & 1) == 0 ? b.min.x : b.max.x, (corner & 2) == 0 ? b.min.y : b.max.y, (corner & 4) == 0 ? b.min.z : b.max.z);
                    float d = Flat(p - head).sqrMagnitude;
                    if (d <= far) continue;
                    far = d;
                    best = p;
                }
            }
            return best;
        }

        private static float LowestPoint(NpcRagdoll r)
        {
            float low = float.MaxValue;
            for (int i = 0; i < r.PartCount; i++)
            {
                r.CapsuleSegment(i, out Vector3 a, out Vector3 b, out float radius);
                low = Mathf.Min(low, Mathf.Min(a.y, b.y) - radius);
            }
            foreach (Collider c in r.Colliders)
                if (c is BoxCollider) low = Mathf.Min(low, c.bounds.min.y);
            return low;
        }

        private static float Highest(NpcRagdoll r)
        {
            float high = float.MinValue;
            for (int i = 0; i < r.PartCount; i++)
            {
                r.CapsuleSegment(i, out Vector3 a, out Vector3 b, out float radius);
                high = Mathf.Max(high, Mathf.Max(a.y, b.y) + radius);
            }
            return high;
        }

        // ---------- Helpers: hands that stand somewhere ----------

        private static Leg To(Hand h, Vector3 target) => To(h, target, h.Stand);

        private static Leg To(Hand h, Vector3 target, Vector3 stand) =>
            new() { Hand = h, FromTarget = h.Target, ToTarget = target, FromStand = h.Stand, ToStand = stand };

        private static void Crouch(Hand h, bool crouch) => h.Eye = crouch ? CrouchEye : StandEye;

        // Where the hand's feet are: the ground, the van's floor or step (or one of its invisible ramps).
        private Vector3 Feet(Vector3 stand)
        {
            var from = new Vector3(stand.x, _vo.y + 1.5f, stand.z);
            return Physics.Raycast(from, Vector3.down, out RaycastHit hit, 3f, FeetMask, QueryTriggerInteraction.Ignore)
                ? hit.point
                : new Vector3(stand.x, _vo.y, stand.z);
        }

        private Vector3 EyeOf(Hand h) => Feet(h.Stand) + Vector3.up * h.Eye;

        private void AimHand(Hand h) => Aim(h, EyeOf(h), h.Target);

        // Takes the chest's collar band from where the hand stands, the way a player aims at whatever of it shows: the
        // first of a grid of points on the top half of the chest whose view ray reaches the chest first (the head capsule
        // covers the middle of the collar, the upper arms its sides). Good handle only. _grabMiss says why not.
        private bool GrabCollar(Hand h, NpcRagdoll r)
        {
            NpcRagdollProfile p = r.Profile;
            int chest = p.IndexOf(Kind.Chest);
            float cr = p.Parts[chest].Radius;
            Vector3 c = r.PartCenter(chest), up = ChestUp(r, chest), lateral = ChestLateral(r, chest);
            _grabMiss.Clear();
            foreach (float s in new[] { 0.85f, 0.65f, 0.45f, 0.25f })
                foreach (float side in new[] { 0f, 0.05f, -0.05f, 0.10f, -0.10f, 0.14f, -0.14f })
                    if (TryGrabPart(h, r, chest, c + up * (s * cr) + lateral * side, Handle.Good))
                        return true;
            return false;
        }

        // Takes a shin near its ankle (from 90 % to 40 % of the way from its middle to the foot end, on its top or sides).
        private bool GrabCalf(Hand h, NpcRagdoll r, NpcSide side)
        {
            int calf = r.Profile.IndexOf(Kind.Calf, side);
            r.CapsuleSegment(calf, out Vector3 knee, out Vector3 ankle, out float radius);
            Vector3 mid = (knee + ankle) * 0.5f;
            Vector3 across = Vector3.Cross(Vector3.up, ankle - knee);
            across = across.sqrMagnitude > 1e-6f ? across.normalized : Vector3.right;
            _grabMiss.Clear();
            foreach (float u in new[] { 0.7f, 0.9f, 0.5f, 0.4f })
                foreach (float s in new[] { 0f, 0.6f, -0.6f })
                    if (TryGrabPart(h, r, calf, Vector3.Lerp(mid, ankle, u) + Vector3.up * (radius * 0.5f) + across * (s * radius), Handle.Good))
                        return true;
            return false;
        }

        private readonly List<string> _grabMiss = new();

        private void Miss(string why)
        {
            if (_grabMiss.Count < 4 && !_grabMiss.Contains(why)) _grabMiss.Add(why);
        }

        private bool TryGrabPart(Hand h, NpcRagdoll r, int part, Vector3 point, Handle handle)
        {
            Vector3 eye = EyeOf(h);
            Vector3 to = point - eye;
            if (!Physics.Raycast(eye, to.normalized, out RaycastHit hit, to.magnitude + 0.3f, GrabRayMask, QueryTriggerInteraction.Ignore))
            {
                Miss("no hit");
                return false;
            }
            if (r.PartOf(hit.collider) != part)
            {
                int other = r.PartOf(hit.collider);
                Miss(other >= 0 ? "ray hits " + r.Profile.Parts[other].Name : "ray hits " + hit.collider.name);
                return false;
            }
            if (hit.distance > r.GrabReach)
            {
                Miss(Inv($"too far {hit.distance:0.00} m"));
                return false;
            }
            h.Target = hit.point;
            Aim(h, eye, hit.point);
            if (!h.Grabber.ScriptGrab())
            {
                Miss("grabber refused");
                return false;
            }
            int slot = SlotOf(r, h.Grabber);
            if (slot < 0 || r.Claims[slot].Part != part || r.Claims[slot].Handle != handle)
            {
                Miss(slot < 0 ? "no claim" : $"claim {r.Profile.Parts[r.Claims[slot].Part].Name}/{r.Claims[slot].Handle}");
                h.Grabber.ScriptRelease();
                return false;
            }
            h.Held = r;
            h.Slot = slot;
            h.Lost = false;
            h.Forces.Clear();
            h.Lags.Clear();
            h.Target = r.ClaimWorld(slot);
            AimHand(h);
            h.Expect = true;
            return true;
        }

        private static void ReleaseHand(Hand h)
        {
            h.Expect = false;
            h.Grabber.ScriptRelease();
            h.Held = null;
            h.Slot = -1;
        }

        // Moves the hands' targets and stands linearly over at least 'nominal' seconds, slower if a hold distance would
        // change faster than the wheel (WheelPlan of MaxWheelSpeed). Each tick: aim, one physics step, the bookkeeping.
        private IEnumerator Move(float nominal, params Leg[] legs)
        {
            int ticks = Ticks(Stretch(nominal, legs));
            for (int k = 1; k <= ticks; k++)
            {
                float u = (float)k / ticks;
                foreach (Leg leg in legs)
                {
                    leg.Hand.Target = Vector3.Lerp(leg.FromTarget, leg.ToTarget, u);
                    leg.Hand.Stand = Vector3.Lerp(leg.FromStand, leg.ToStand, u);
                    AimHand(leg.Hand);
                }
                yield return Fixed;
                AfterTick();
            }
        }

        private float Stretch(float nominal, Leg[] legs)
        {
            const int samples = 40;
            float worst = 0f;
            foreach (Leg leg in legs)
            {
                float previous = HoldAt(leg, 0f);
                for (int i = 1; i <= samples; i++)
                {
                    float d = HoldAt(leg, (float)i / samples);
                    worst = Mathf.Max(worst, Mathf.Abs(d - previous) * samples);
                    previous = d;
                }
            }
            return Mathf.Max(nominal, worst / (MaxWheelSpeed * WheelPlan), Time.fixedDeltaTime);
        }

        private float HoldAt(Leg leg, float u)
        {
            Vector3 eye = Feet(Vector3.Lerp(leg.FromStand, leg.ToStand, u)) + Vector3.up * leg.Hand.Eye;
            return Mathf.Clamp(Vector3.Distance(Vector3.Lerp(leg.FromTarget, leg.ToTarget, u), eye), MinHold, MaxHold);
        }

        // ---------- Helpers ----------

        private void KeepStunned()
        {
            foreach (GreyboxNpc npc in _keepDown)
                if (npc != null && npc.State == NpcState.Down)
                {
                    npc.StunTotal = 100f;
                    // Out: no kicks, no crawling. Step 4 checks keep some Groggy (70 % of the stun gone): the struggle.
                    npc.StunLeft = _keepGroggy.Contains(npc) ? 30f : 100f;
                }
        }

        // Step 4: kept Groggy (and down) or back to Out.
        private void SetGroggy(GreyboxNpc npc, bool groggy)
        {
            if (groggy)
            {
                _keepDown.Add(npc);
                _keepGroggy.Add(npc);
            }
            else _keepGroggy.Remove(npc);
            KeepStunned();
        }

        // Step 4: a check's own kick pace and tear chances (null keeps the scene's), restored by RestoreKicks or Teardown.
        private void OverrideKicks(GreyboxNpc npc, Vector2? interval, float[] tear)
        {
            if (!_kicks0.ContainsKey(npc)) _kicks0[npc] = (npc.KickInterval, npc.KickTearChance);
            if (interval.HasValue) npc.KickInterval = interval.Value;
            if (tear != null) npc.KickTearChance = tear;
        }

        private void RestoreKicks(GreyboxNpc npc)
        {
            if (!_kicks0.TryGetValue(npc, out (Vector2 interval, float[] tear) kick)) return;
            npc.KickInterval = kick.interval;
            npc.KickTearChance = kick.tear;
            _kicks0.Remove(npc);
        }

        // Where a downed NPC crawls away from (GreyboxNpc.ThreatPosition): the controlled pawn, else the van.
        private static bool Threat(out Vector3 threat)
        {
            GreyboxPawn pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            if (pawn != null && pawn.Controlled)
            {
                threat = pawn.Position;
                return true;
            }
            VanController van = FindAnyObjectByType<VanController>();
            threat = van != null ? van.transform.position : Vector3.zero;
            return van != null;
        }

        // Whether x tears in n kicks are plausible for a chance p a kick: neither P(X <= x) nor P(X >= x) under 0.5 %.
        private static bool BinomialPlausible(int n, int x, float p, out double atMost, out double atLeast)
        {
            double below = 0.0, exactly = 0.0;
            for (int k = 0; k <= n; k++)
            {
                double c = 1.0;
                for (int i = 1; i <= k; i++) c = c * (n - k + i) / i;
                double pk = c * Math.Pow(p, k) * Math.Pow(1.0 - p, n - k);
                if (k < x) below += pk;
                else if (k == x) exactly = pk;
            }
            atMost = below + exactly;
            atLeast = 1.0 - below;
            return atMost >= 0.005 && atLeast >= 0.005;
        }

        private void AfterTick()
        {
            KeepStunned();
            foreach (Taken t in _taken)
            {
                WatchAnim(t.Npc);
                NpcRagdoll r = t.Npc != null ? t.Npc.Ragdoll : null;
                if (r == null || !r.Active) continue;
                for (int i = 0; i < r.PartCount; i++)
                    if (!GrabPhysicsSolver.IsFinite(r.BodyOf(i).position)) _nan = true;
            }
            foreach (Hand h in _hands)
            {
                if (!h.Expect) continue;
                if (!h.Grabber.IsHolding)
                {
                    _lostGrips++;
                    h.Lost = true;
                    h.Expect = false;
                    continue;
                }
                h.Forces.Add(h.Grabber.LastPointForce.magnitude);
                if (h.Held != null && h.Slot >= 0 && h.Held.Active)
                    h.Lags.Add(Vector3.Distance(h.Grabber.PointHoldTarget, h.Held.ClaimWorld(h.Slot)));
            }
            _observe?.Invoke();
        }

        // A point of the body seen from above: the ray down onto it (the hit on the body) and an eye 1.2 m up, a little
        // to the side (a player looking down at the body).
        private static bool Above(Vector3 point, out RaycastHit hit, out Vector3 eye)
        {
            eye = point + Vector3.up * 1.2f + Vector3.forward * 0.05f; // nearly straight down: no limb in between
            Vector3 to = point - eye;
            return Physics.Raycast(eye, to.normalized, out hit, to.magnitude + 0.5f, OvLayers.NpcMask, QueryTriggerInteraction.Ignore);
        }

        private bool Grab(Hand h, Vector3 eye, Vector3 point, NpcRagdoll r, out int slot)
        {
            Aim(h, eye, point);
            slot = -1;
            if (!h.Grabber.ScriptGrab()) return false;
            slot = SlotOf(r, h.Grabber);
            if (slot < 0)
            {
                h.Grabber.ScriptRelease();
                return false;
            }
            Aim(h, eye, point);
            return true;
        }

        private static void Release(Hand h)
        {
            h.Expect = false;
            h.Grabber.ScriptRelease();
        }

        private static int SlotOf(NpcRagdoll r, object holder)
        {
            for (int i = 0; i < r.Claims.Length; i++)
                if (ReferenceEquals(r.Claims[i].Holder, holder)) return i;
            return -1;
        }

        // The eye where the hand stands, looking at its target; while holding, the hold distance follows it.
        private static void Aim(Hand h, Vector3 eye, Vector3 target)
        {
            Vector3 to = target - eye;
            if (to.sqrMagnitude > 1e-6f) h.View.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(to));
            if (h.Grabber.IsHolding) h.Grabber.PointHoldDistance = to.magnitude;
        }

        private static Vector3 ChestUp(NpcRagdoll r, int chest)
        {
            Rigidbody rb = r.BodyOf(chest);
            return (rb.rotation * r.Profile.Parts[chest].Up).normalized;
        }

        private static Vector3 ChestLateral(NpcRagdoll r, int chest)
        {
            r.CapsuleSegment(chest, out Vector3 a, out Vector3 b, out _);
            Vector3 d = b - a;
            return d.sqrMagnitude > 1e-6f ? d.normalized : r.BodyOf(chest).rotation * Vector3.right;
        }

        private static Vector3 FootBoxCentre(NpcRagdoll r, int calf)
        {
            foreach (Collider c in r.Colliders)
                if (c is BoxCollider box && c.attachedRigidbody == r.BodyOf(calf))
                    return box.transform.TransformPoint(box.center);
            return r.Landmark(NpcLandmark.LeftAnkle);
        }

        private static float MaxJointGap(NpcRagdoll r)
        {
            float worst = 0f;
            for (int i = 0; i < r.PartCount; i++)
            {
                ConfigurableJoint j = r.JointOf(i);
                if (j == null || j.connectedBody == null) continue;
                Rigidbody child = r.BodyOf(i), parent = j.connectedBody;
                Vector3 a = child.position + child.rotation * Vector3.Scale(j.anchor, child.transform.lossyScale);
                Vector3 c = parent.position + parent.rotation * Vector3.Scale(j.connectedAnchor, parent.transform.lossyScale);
                worst = Mathf.Max(worst, Vector3.Distance(a, c));
            }
            return worst;
        }

        private static void PutAt(GreyboxNpc npc, Vector3 feet, float yaw)
        {
            var controller = npc.GetComponent<CharacterController>();
            bool on = controller != null && controller.enabled;
            if (on) controller.enabled = false;
            npc.transform.SetPositionAndRotation(feet, Quaternion.Euler(0f, yaw, 0f));
            if (on) controller.enabled = true;
            Physics.SyncTransforms();
            // Re-enabling the controller dropped its ignore pairs with the van; the NPC restores them on this message.
            npc.SendMessage("OnSeaReturned", SendMessageOptions.DontRequireReceiver);
            if (npc.TryGetComponent(out SeaReturnTracker tracker)) tracker.Rebase();
        }

        private IEnumerator Idle(float seconds)
        {
            int ticks = Ticks(seconds);
            for (int k = 0; k < ticks; k++)
            {
                yield return Fixed;
                AfterTick();
            }
        }

        private IEnumerator WaitFor(Func<bool> done, float timeout)
        {
            int ticks = Ticks(timeout);
            for (int k = 0; k < ticks && !done(); k++)
            {
                yield return Fixed;
                AfterTick();
            }
        }

        private static int Ticks(float seconds) => Mathf.Max(1, Mathf.CeilToInt(seconds / Time.fixedDeltaTime - 1e-3f));

        private static float Mean(List<float> values)
        {
            if (values.Count == 0) return 0f;
            float sum = 0f;
            foreach (float v in values) sum += v;
            return sum / values.Count;
        }

        private static float Max(List<float> values)
        {
            float m = 0f;
            foreach (float v in values) m = Mathf.Max(m, v);
            return m;
        }

        private static float Percentile(List<float> values, float p)
        {
            if (values.Count == 0) return 0f;
            var sorted = new List<float>(values);
            sorted.Sort();
            return sorted[Mathf.Clamp(Mathf.CeilToInt(p * sorted.Count) - 1, 0, sorted.Count - 1)];
        }

        // Mean force per phase: marks are the force counts at the end of each phase but the last.
        private static string Phases(List<float> forces, List<int> marks, params string[] names)
        {
            var sb = new StringBuilder();
            int from = 0;
            for (int i = 0; i < names.Length; i++)
            {
                int to = i < marks.Count ? Mathf.Min(marks[i], forces.Count) : forces.Count;
                float sum = 0f;
                for (int k = from; k < to; k++) sum += forces[k];
                if (sb.Length > 0) sb.Append(' ');
                sb.Append(names[i]).Append(' ').Append((to > from ? sum / (to - from) : 0f).ToString("0", CultureInfo.InvariantCulture));
                from = to;
            }
            return sb.ToString();
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        private static string Seconds(float s) => s < 0f ? "never" : s.ToString("0.00", CultureInfo.InvariantCulture) + " s";

        private static string Inv(FormattableString s) => FormattableString.Invariant(s);

        private void Check(string name, bool ok, string details)
        {
            _checks++;
            if (ok) _passes++;
            Line($"{Tag} {(ok ? "PASS" : "FAIL")} {name}: {details}");
        }

        private void Line(string text)
        {
            _report.AppendLine(text);
            Debug.Log(text);
        }
    }
}
#endif
