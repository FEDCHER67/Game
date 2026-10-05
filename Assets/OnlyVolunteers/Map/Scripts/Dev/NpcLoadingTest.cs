#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map.Dev
{
    // Scripted, repeatable loading test for NPC capture stage 1 (Fedya's second playtest, 2026-10-05: "the body still cannot
    // be got into the van"). Hands are real PhysicsGrabbers (ScriptDriven: this script aims their camera, grabs and lets
    // go; the force goes through HoldPoint -> GrabPhysicsSolver -> AddForceAtPosition exactly like a player's) with no
    // KCC: no capsule, no speed scaling, zero frame velocity. They lift a stunned NPC by the head, the feet and the pelvis on
    // open ground, then load it through the sliding door and the rear doors (three start poses each), and finally once
    // more through the rear doors with the fist's real head stun (g: Groggy kicks and crawling, INFO only).
    // Sandbox: the van is parked 300 m above where it stands (kinematic, i.e. the handbrake; yaw only), on a 30 x 30 m box of
    // default ground. Scenario setup teleports the body; the loading itself never does. Afterwards the van, its doors and
    // its sea tracker are put back, and the NPC lies down where it stood and wakes a second later.
    // A hand is limited like a player: the hold distance (the mouse wheel) may change by at most 1 m/s, a move that would
    // need more is slowed down to that; it must stay within the hold range (0.6 .. the profile's HoldDistance), and the
    // place the hand stands must be free (a KCC capsule ignores only the body it holds; before a grab the body too, so a
    // hand grabs from beside the body, never from inside it).
    // Loading is two steps (first real run, 2026-10-05): the head end is pushed onto the floor edge (or the bumper) and
    // leans there with the feet on the ground (a rigid body cannot get its head down onto the floor while its feet are
    // down: the edge contact stays near s 1.25, see the INFO release lines), then the feet are lifted and pushed in after
    // it. A d/e failure: read the release line and the blocker names first; retune the hand only after the poses are right.
    // Run: OnlyVolunteers/Map/Dev/NPC Loading Test (enters Play mode, runs, leaves), or add this component in Play mode.
    // Results: [NpcLoadingTest] lines in the console and the statics Done / Passed / LastReport / Progress (MCP polls them).
    // Unity MCP: check EditorApplication.isPlaying first (someone else may be testing), enter Play in Map_Greybox_v12 or
    // Map_Look_v12_Play, then: new GameObject("NpcLoadingTest").AddComponent<OnlyVolunteers.Map.Dev.NpcLoadingTest>();
    // poll NpcLoadingTest.Done every 10 s (about 35-60 s real time at TimeScale 3); stop Play when done.
    public sealed class NpcLoadingTest : MonoBehaviour
    {
        public static bool Done;
        public static bool Passed;
        public static string LastReport = "";
        public static string Progress = "";

        [Tooltip("Time.timeScale while the test runs. The physics step stays 1/60 s, so results do not depend on it.")]
        public float TimeScale = 3f;
        [Tooltip("c3: lift one point at 15 places along the body.")]
        public bool RunSweep = true;
        public int Seed = 151;
        [Tooltip("Leave Play mode when done (the editor menu sets it when it entered Play mode itself).")]
        public bool ExitWhenDone;

        private const string Tag = "[NpcLoadingTest]";
        private const float SandboxLift = 300f;
        private const float StandEye = 1.85f;               // standing eye height (stooped 1.20, crouched 0.85)
        private const float StandHeight = 2.0f, StandRadius = 0.33f;
        private const float MinHold = 0.6f;                 // PhysicsGrabber.MinPointHold
        private const float MaxWheelSpeed = 1.0f;           // m/s of hold distance: 10 wheel notches a second
        private const float WheelPlan = 0.95f;              // moves are planned a little under it
        private const float ReachSlack = 0.05f;
        private const float SettleTime = 0.6f;
        private const int StandMask = 1 | OvLayers.VehicleMask; // Default | Vehicle
        private const int FeetMask = StandMask | (1 << OvLayers.VehicleInterior);
        private const float SlideEdgeX = 0.94f, RearEdgeZ = -2.38f; // the floor edge, the bumper's outer top edge
        private const float EdgeLean = 0.12f; // D1/E1: the head cap's centre at most this far outside the edge (leaning on it)
        // The body touches a housing at |x| 0.24 (1.04 m between the arches, radius 0.28); a few cm more is solver slop
        // while sliding along it, which only warns (housingTicks).
        private const float HousingZMin = -2.04f, HousingZMax = -1.12f, HousingTop = 0.85f, HousingHalfGap = 0.27f;
        private const float WalkSpeed = 3f; // m/s, the player walking from the head to the feet in (g)

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
            public int Slot = -1;
            public Vector3 Stand;     // where the feet are (XZ; the height comes from the ground under it)
            public Vector3 Target;    // where the hand is told to hold, world
            public float Hold = -1f;  // hold distance last set (-1: not holding)
        }

        private struct Leg
        {
            public Hand Hand;
            public Vector3 FromTarget, ToTarget, FromStand, ToStand;
        }

        // One check: its failures and lag samples.
        private sealed class Run
        {
            public readonly string Name;
            public readonly List<string> Fails = new();
            public readonly List<float> Lags = new();
            public Run(string name) => Name = name;
            public void Fail(string why)
            {
                if (!Fails.Contains(why)) Fails.Add(why);
            }
        }

        private GreyboxVanCargo _cargo;
        private GreyboxVanSeat _seat;
        private VanCargoSpace _space;
        private Rigidbody _van;
        private SeaReturnTracker _vanTracker;
        private bool _vanTrackerOn;
        private Vector3 _vanPos0;
        private Quaternion _vanRot0;
        private bool _vanKinematic0;
        private bool _vanMoved;
        private bool _doorsTouched, _slideOpen0, _rearOpen0;
        private Vector3 _o;         // sandbox origin: the van root, on the sandbox ground
        private Quaternion _yaw;    // the van's yaw
        private GameObject _ground;
        private readonly List<Collider> _housings = new();

        private GreyboxNpc _npc;
        private GreyboxNpcBody _body;
        private Vector3 _npcHome;
        private float _npcHomeYaw;
        private bool _npcTaken;

        private GrabPhysicsProfile _handProfile;
        private readonly List<Hand> _hands = new();
        private Run _run;
        private bool _recordLag;
        private Action _observe;
        private bool _waitOk;
        private readonly StringBuilder _report = new();
        private int _checks, _passes, _warnings;
        private int _logErrors, _earlyWakes;
        private bool _infoRun;      // (g): lost grips are counted as tears, early wakes reported, nothing fails
        private int _tears, _infoEarlyWakes;
        private bool _nan;
        private string _abort;
        private bool _finished;

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
            if (message == null) message = "";
            if (message.StartsWith(Tag, StringComparison.Ordinal)) return;
            // Only our runtime code counts: not the editor (other builders, MCP calls) and not other packages.
            if ((type == LogType.Error || type == LogType.Exception || type == LogType.Assert) && stack != null &&
                stack.Contains("OnlyVolunteers.") && !stack.Contains("UnityEditor."))
                _logErrors++;
            // Only the test's own NPC ("[NPC] <name>: impact ... -> waking early").
            if (_npc != null && message.Contains("[NPC]") && message.Contains("waking early") && message.Contains(_npc.name))
            {
                if (_infoRun) _infoEarlyWakes++;
                else _earlyWakes++;
            }
        }

        // Runs Main with nested IEnumerators inline (every yield is a WaitForFixedUpdate, so the script always runs right
        // after a physics step and the cameras it sets are read by the next step's PhysicsGrabber.FixedUpdate). An
        // exception ends the run with a FAIL instead of leaving the van in the sky.
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
                    _abort = $"exception in {(_run != null ? _run.Name : "setup")}: {e.GetType().Name}: {e.Message}";
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
            for (int i = 0; i < 5; i++) yield return Fixed; // every Start has run (doors, cargo space, colliders)
            if (!Setup()) yield break;
            yield return OpenDoors();
            if (_abort != null) yield break;
            // a2: the collar (s 1.30) can reach 1.30 m at most with the feet down; 1.15 leaves room for the hold's sag.
            yield return EndLift("a1", "a2", 1.30f, true, 1.70f, 1.15f);
            yield return EndLift("b1", "b2", 0.08f, false, 1.80f, 1.30f);
            yield return PelvisOne();
            yield return PelvisTwo();
            if (RunSweep) yield return Sweep();
            for (int v = 0; v < 3; v++) yield return SideDoor(v);
            for (int v = 0; v < 3; v++) yield return RearDoors(v);
            yield return Drag();
            yield return RealStun();
        }

        // ---------- Setup and teardown ----------

        private bool Setup()
        {
            Progress = "setup";
            _cargo = FindAnyObjectByType<GreyboxVanCargo>();
            if (_cargo == null) return Abort("no GreyboxVanCargo in the scene: open Map_Greybox_v12 (or Map_Look_v12_Play)");
            _van = _cargo.GetComponent<Rigidbody>();
            _seat = _cargo.GetComponent<GreyboxVanSeat>();
            _space = _cargo.CargoSpace != null ? _cargo.CargoSpace : _cargo.GetComponent<VanCargoSpace>();
            if (_van == null || _space == null || _cargo.Slide == null || (_cargo.RearLeft == null && _cargo.RearRight == null))
                return Abort("the van has no body, cargo space or cargo doors");
            if (_seat != null && _seat.Driving) return Abort("van occupied: someone is in the driver seat");
            GreyboxPawn pawn = _seat != null ? _seat.Pawn : null;
            if (pawn != null && pawn.Controlled && _space.Contains(pawn.Position + Vector3.up * 0.5f))
                return Abort("van occupied: the player is in the cargo bay");
            foreach (GreyboxNpc other in GreyboxNpc.All)
                if (other != null && other.InCargo && ReferenceEquals(other.Carrier, _space))
                    return Abort("the van has cargo: unload it first");
            foreach (GreyboxNpc candidate in GreyboxNpc.All)
                if (candidate != null && candidate.isActiveAndEnabled && candidate.State == NpcState.Free && candidate.Body != null)
                {
                    _npc = candidate;
                    break;
                }
            if (_npc == null) return Abort("no free NPC");
            if (ViewCameraField == null || ProfileField == null) return Abort("PhysicsGrabber has no viewCamera/profile fields");

            // The hands find bodies with the player's default profile (Player/GrabPhysicsProfile: reach 2.8, all layers);
            // the NPC then hands out NpcGrabProfile, as in the game.
            PhysicsGrabber player = FindAnyObjectByType<PhysicsGrabber>(FindObjectsInactive.Include);
            _handProfile = player != null ? ProfileField.GetValue(player) as GrabPhysicsProfile : null;
            if (_handProfile == null) _handProfile = _npc.Body.Profile;

            // The sandbox: the van 300 m up, kinematic, upright, on a box of ground.
            _vanPos0 = _van.position;
            _vanRot0 = _van.rotation;
            _vanKinematic0 = _van.isKinematic;
            Vector3 forward = Flat(_vanRot0 * Vector3.forward);
            _yaw = forward.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(forward.normalized) : Quaternion.identity;
            _o = _vanPos0 + Vector3.up * SandboxLift;
            if (SeaReturnZone.InSea(_o)) return Abort("the sandbox would be over the sea");
            if (!_van.isKinematic)
            {
                _van.linearVelocity = Vector3.zero;
                _van.angularVelocity = Vector3.zero;
            }
            _van.isKinematic = true;
            _vanMoved = true;
            _van.position = _o;
            _van.rotation = _yaw;
            _van.transform.SetPositionAndRotation(_o, _yaw);
            // Its sea tracker would remember the sandbox as dry ground to return to.
            if (_van.TryGetComponent(out _vanTracker))
            {
                _vanTrackerOn = _vanTracker.enabled;
                _vanTracker.enabled = false;
            }
            _ground = new GameObject("NpcLoadingTest_Ground") { layer = 0 };
            _ground.transform.SetPositionAndRotation(_o - Vector3.up * 0.5f, _yaw);
            _ground.AddComponent<BoxCollider>().size = new Vector3(30f, 1f, 30f);
            foreach (BoxCollider c in _cargo.GetComponentsInChildren<BoxCollider>(true))
                if (c.name == "HousingRearLeft" || c.name == "HousingRearRight")
                    _housings.Add(c);
            Physics.SyncTransforms();

            // The NPC: stunned the real way (GreyboxNpc.Hit: the body activates at DownedMass).
            _npcHome = _npc.transform.position;
            _npcHomeYaw = _npc.transform.eulerAngles.y;
            _npcTaken = true;
            _npc.Hit(WeaponStun.Fist, HitZone.Torso, _npc.transform.position + _npc.transform.forward, _npc.Center);
            UnityEngine.Random.InitState(Seed);
            _body = _npc.Body;
            if (_body.Rigidbody == null) return Abort("the hit did not activate the NPC body");

            for (int i = 0; i < 3; i++) _hands.Add(NewHand(i));
            Time.timeScale = Mathf.Max(0.1f, TimeScale);

            GrabPhysicsProfile p = _body.Profile;
            Line(Inv($"{Tag} start: {_npc.name} {_body.Rigidbody.mass:0.#} kg (DownedMass {_body.DownedMass:0.#}, awake {_body.Mass:0.#}); ") +
                 Inv($"hand '{p.name}': up {p.MaxForce:0} N, side {p.SoloHorizontalMaxForce:0} N, spring {p.SpringStrength:0}, ") +
                 Inv($"damping {p.DampingRatio:0.##}, hold {MinHold:0.0}..{p.HoldDistance:0.0} m; finder '{_handProfile.name}'; ") +
                 Inv($"timeScale {Time.timeScale:0.#}, seed {Seed}"));
            return true;
        }

        private bool Abort(string why)
        {
            _abort = why;
            return false;
        }

        private Hand NewHand(int n)
        {
            var root = new GameObject($"TestHand_{n}");
            root.SetActive(false); // Awake needs the profile set first
            var eye = new GameObject("Eye");
            eye.transform.SetParent(root.transform, false);
            var view = eye.AddComponent<Camera>();
            view.enabled = false;
            var grabber = root.AddComponent<PhysicsGrabber>();
            ViewCameraField.SetValue(grabber, view);
            ProfileField.SetValue(grabber, _handProfile);
            root.SetActive(true);
            grabber.ScriptDriven = true;
            return new Hand { Root = root, View = view, Grabber = grabber };
        }

        private IEnumerator OpenDoors()
        {
            Progress = "opening the doors";
            _doorsTouched = true;
            _slideOpen0 = _cargo.DoorOpen(0);
            _rearOpen0 = _cargo.DoorOpen(1);
            if (!_cargo.DoorOpen(0)) _cargo.ToggleDoor(0);
            yield return WaitFor(() => _cargo.Slide.Openness >= 0.99f, 3f);
            if (!_waitOk) _abort = "the sliding door did not open";
            if (!_cargo.DoorOpen(1)) _cargo.ToggleDoor(1);
            yield return WaitFor(() => RearOpenness(true) >= 0.99f, 3f);
            if (!_waitOk) _abort = "the rear doors did not open";
        }

        // max = false: the less open of the two leaves.
        private float RearOpenness(bool min)
        {
            float l = _cargo.RearLeft != null ? _cargo.RearLeft.Openness : min ? 1f : 0f;
            float r = _cargo.RearRight != null ? _cargo.RearRight.Openness : min ? 1f : 0f;
            return min ? Mathf.Min(l, r) : Mathf.Max(l, r);
        }

        private void Teardown()
        {
            Time.timeScale = 1f;
            foreach (Hand h in _hands)
            {
                if (h.Grabber != null) h.Grabber.ScriptRelease();
                if (h.Root != null) Destroy(h.Root);
            }
            _hands.Clear();
            if (_npcTaken && _npc != null)
            {
                // Back where it stood, not loaded, lying down; it wakes a second later and runs.
                _npc.InCargo = false;
                _npc.Carrier = null;
                Rigidbody rb = _body != null ? _body.Rigidbody : null;
                if (rb != null)
                {
                    _body.UnpinAll();
                    Vector3 p = _npcHome + Vector3.up * (_body.Radius + 0.05f);
                    Quaternion r = Quaternion.LookRotation(Vector3.up, Quaternion.Euler(0f, _npcHomeYaw, 0f) * Vector3.forward);
                    rb.position = p;
                    rb.rotation = r;
                    rb.linearVelocity = Vector3.zero;
                    rb.angularVelocity = Vector3.zero;
                    _npc.transform.SetPositionAndRotation(p, r);
                }
                if (_npc.State == NpcState.Down) _npc.StunLeft = Mathf.Min(_npc.StunLeft, 1f);
                _npcTaken = false;
            }
            if (_ground != null) Destroy(_ground);
            if (_vanMoved && _van != null)
            {
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
            Physics.SyncTransforms();
        }

        private void Finish()
        {
            if (_finished) return;
            _finished = true;
            if (_abort != null) Line($"{Tag} FAIL run aborted: {_abort}");
            bool global = _abort == null && _logErrors == 0 && _earlyWakes == 0 && !_nan;
            Check("global", global, Inv($"errors={_logErrors} earlyWakes={_earlyWakes} nan={(_nan ? 1 : 0)}"), null);
            Teardown();
            int failed = _checks - _passes; // an abort fails "global"
            Passed = failed == 0;
            Line(Passed
                ? $"{Tag} DONE {_passes}/{_checks} PASS" + (_warnings > 0 ? $" ({_warnings} warnings)" : "")
                : $"{Tag} DONE {_passes}/{_checks} FAIL {failed}");
            LastReport = _report.ToString();
            Progress = "done";
            Done = true;
#if UNITY_EDITOR
            if (ExitWhenDone) UnityEditor.EditorApplication.isPlaying = false;
#endif
            Destroy(gameObject);
        }

        // ---------- (a), (b): one hand lifts an end ----------

        // first: lift the claim at 's' to 1.10 m on its arc (the far cap stays down); second: pull it toward the far cap's
        // vertical and up to 'high' (it stops at the geometric limit). head: the far cap is the foot cap, else the head cap.
        private IEnumerator EndLift(string first, string second, float s, bool head, float high, float pass2)
        {
            Progress = first;
            _run = new Run(first);
            Vector3 axis = Vector3.right;
            yield return Place(AreaRoot(W(-7f, 0f, 0f), axis), axis);
            float farS = head ? _body.Radius : _body.Height - _body.Radius;
            Hand h = _hands[0];
            h.Stand = Flat(AxisPoint(s)) + Side(axis) * 0.8f;
            if (!Grab(h, s))
            {
                Check(first, false, "", _run);
                Check(second, false, "skipped (no grab)", null);
                yield break;
            }
            float claimS = _body.Claims[h.Slot].Local.y;
            Vector3 far0 = AxisPoint(farS);
            // Physics, not the script's own timing: how long the hold trails the target through 0.90 m, and how soon after
            // the lift it is within 0.20 m of the target (the static sag under the end's ~120 N is ~0.15 m).
            float tTarget = -1f, tHold = -1f, tEnd = -1f, settle = -1f, farMax = 0f, slip = 0f, top = 0f;
            _observe = () =>
            {
                if (h.Slot < 0) return;
                Vector3 claimNow = _body.ClaimWorld(h.Slot);
                float y = Height(claimNow);
                if (tTarget < 0f && Height(h.Target) >= 0.90f) tTarget = Time.fixedTime;
                if (tHold < 0f && y >= 0.90f) tHold = Time.fixedTime;
                if (tEnd >= 0f && settle < 0f && Vector3.Distance(h.Grabber.PointHoldTarget, claimNow) <= 0.20f)
                    settle = Time.fixedTime - tEnd;
                top = Mathf.Max(top, y);
                Vector3 far = AxisPoint(farS);
                farMax = Mathf.Max(farMax, Height(far));
                slip = Mathf.Max(slip, Flat(far - far0).magnitude);
            };
            yield return Move(0.4f, To(h, Arc(far0, _body.ClaimWorld(h.Slot), 1.10f)));
            tEnd = Time.fixedTime;
            _run.Lags.Clear();
            _recordLag = true;
            yield return Move(1.6f, To(h, h.Target));
            _recordLag = false;
            float lag = MeanTail(_run.Lags, Ticks(1.0f));
            float delay = tTarget >= 0f && tHold >= 0f ? tHold - tTarget : float.PositiveInfinity;
            // Calibrated on the first real run (2026-10-05): mean lag (static sag) ~0.15 m, the far end drifts 0.18-0.20 m
            // while mostly pivoting.
            bool ok = delay <= 0.40f && settle >= 0f && settle <= 0.3f && lag <= 0.20f && slip <= 0.25f && farMax <= 0.33f;
            string cap = head ? "footCap" : "headCap";
            Check(first, ok, Inv($"s={claimS:0.00} delay90={(float.IsPositiveInfinity(delay) ? "never" : delay.ToString("0.00", Inv0))}s ") +
                             Inv($"settle={(settle < 0f ? "never" : settle.ToString("0.00", Inv0))}s lag={lag:0.00}m slip={slip:0.00}m {cap}={farMax:0.00}m"), _run);

            Progress = second;
            _run = new Run(second);
            top = 0f;
            farMax = 0f;
            Vector3 claim = _body.ClaimWorld(h.Slot);
            Vector3 farNow = AxisPoint(farS);
            Vector3 toward = Flat(claim - farNow).normalized;
            Vector3 over = new(farNow.x, _o.y + high, farNow.z);
            yield return Move(0.5f, To(h, over + toward * 0.35f));
            yield return Move(1.5f, To(h, h.Target));
            _observe = null;
            string what = head ? "collar" : "ankle";
            Check(second, top >= pass2 && farMax <= 0.33f, Inv($"max {what}={top:0.00}m {cap}={farMax:0.00}m"), _run);
            ReleaseAll();
        }

        // ---------- (c) the pelvis ----------

        private IEnumerator PelvisOne()
        {
            Progress = "c1";
            _run = new Run("c1");
            Vector3 axis = Vector3.right;
            yield return Place(AreaRoot(W(-7f, 0f, 0f), axis), axis);
            Hand h = _hands[0];
            h.Stand = Flat(AxisPoint(0.80f)) + Side(axis) * 0.8f;
            if (!Grab(h, 0.80f))
            {
                Check("c1", false, "", _run);
                yield break;
            }
            float pelvisMax = 0f, capMax = 0f;
            _observe = () =>
            {
                pelvisMax = Mathf.Max(pelvisMax, Height(AxisPoint(0.80f)));
                capMax = Mathf.Max(capMax, Mathf.Max(Height(AxisPoint(_body.Radius)), Height(AxisPoint(_body.Height - _body.Radius))));
            };
            float start = Height(AxisPoint(0.80f));
            float t0 = Time.fixedTime;
            yield return Move(0f, To(h, h.Target + Vector3.up));
            yield return Move(Mathf.Max(0f, 2.5f - (Time.fixedTime - t0)), To(h, h.Target));
            _observe = null;
            Check("c1", pelvisMax <= 0.40f && capMax <= 0.33f,
                Inv($"pelvis max={pelvisMax:0.00}m rise={pelvisMax - start:0.00}m caps={capMax:0.00}m"), _run);
            ReleaseAll();
        }

        private IEnumerator PelvisTwo()
        {
            Progress = "c2";
            _run = new Run("c2");
            Vector3 axis = Vector3.right;
            yield return Place(AreaRoot(W(-7f, 0f, 0f), axis), axis);
            Hand left = _hands[0], right = _hands[1];
            left.Stand = Flat(AxisPoint(0.72f)) - Side(axis) * 0.8f;
            right.Stand = Flat(AxisPoint(0.80f)) + Side(axis) * 0.8f;
            if (!Grab(left, 0.72f) || !Grab(right, 0.80f))
            {
                Check("c2", false, "", _run);
                ReleaseAll();
                yield break;
            }
            float start = Height(AxisPoint(0.80f));
            float t0 = Time.fixedTime, t45 = -1f, rise = 0f;
            _observe = () =>
            {
                float r = Height(AxisPoint(0.80f)) - start;
                rise = Mathf.Max(rise, r);
                if (t45 < 0f && r >= 0.45f) t45 = Time.fixedTime - t0;
            };
            yield return Move(0f, To(left, left.Target + Vector3.up), To(right, right.Target + Vector3.up));
            yield return Move(Mathf.Max(0f, 2.0f - (Time.fixedTime - t0)), To(left, left.Target), To(right, right.Target));
            _observe = null;
            Check("c2", t45 >= 0f && t45 <= 1.5f,
                Inv($"rise={rise:0.00}m t45={(t45 < 0f ? "never" : t45.ToString("0.00", Inv0))}s"), _run);
            ReleaseAll();
        }

        // One hand lifts one point 1 m, at 15 places along the body: the ends go up, the middle stays down.
        private IEnumerator Sweep()
        {
            Progress = "c3";
            var run = new Run("c3");
            var pairs = new StringBuilder();
            bool ok = true;
            Vector3 axis = Vector3.right;
            Hand h = _hands[0];
            for (int i = 0; i < 15; i++)
            {
                float s = 0.05f + 0.10f * i;
                Progress = Inv($"c3 s={s:0.00}");
                _run = run;
                yield return Place(AreaRoot(W(-7f, 0f, 0f), axis), axis);
                h.Stand = Flat(AxisPoint(s)) + Side(axis) * 0.8f;
                if (!Grab(h, s))
                {
                    ok = false;
                    pairs.Append(Inv($" {s:0.00}:nograb"));
                    continue;
                }
                float start = Height(_body.ClaimWorld(h.Slot)), rise = 0f;
                _observe = () =>
                {
                    if (h.Slot >= 0) rise = Mathf.Max(rise, Height(_body.ClaimWorld(h.Slot)) - start);
                };
                float t0 = Time.fixedTime;
                yield return Move(0f, To(h, h.Target + Vector3.up));
                yield return Move(Mathf.Max(0f, 1.5f - (Time.fixedTime - t0)), To(h, h.Target));
                _observe = null;
                ReleaseAll();
                pairs.Append(Inv($" {s:0.00}:{rise:0.00}"));
                int k = Mathf.RoundToInt(s * 100f);
                if ((k == 5 || k == 15 || k == 25 || k == 125 || k == 135 || k == 145) && rise < 0.60f) ok = false;
                if ((k == 65 || k == 75 || k == 85) && rise > 0.10f) ok = false;
            }
            Check("c3", ok, "s:rise" + pairs, run);
        }

        // ---------- (d) the sliding door ----------

        // Van-local frame: x+ = the sliding-door side, z+ = forward, y up from the wheels' contact (the sandbox ground).
        private IEnumerator SideDoor(int variant)
        {
            string name = $"d{variant + 1}";
            Progress = name;
            _run = new Run(name);
            float dz = variant == 0 ? 0f : variant == 1 ? 0.15f : -0.15f;
            float yawDeg = variant == 0 ? 0f : variant == 1 ? 8f : -8f;
            // Head toward the van (-x), the feet tip 2.85 m out, centred on the clear opening (z -0.626 .. 0.42).
            Vector3 axisLocal = Quaternion.Euler(0f, yawDeg, 0f) * Vector3.left;
            Vector3 centre = W(2.85f - 0.75f, 0f, -0.10f + dz);
            Vector3 axis = _yaw * axisLocal;
            // Placed first (the last variant's body may still hang in a hand or lie in the shut bay), then the door.
            yield return Place(AreaRoot(centre, axis), axis);
            yield return EnsureOpen(0);

            Hand h = _hands[0];
            var lags = new List<float>();
            float firstGrab, lastRelease;
            // D1: from beside the body (a player cannot stand in a body it does not hold) the head end up; then onto the
            // body's line, pushing the collar in as far as it goes (the target is out of reach on purpose: the hand pushes
            // at its full side force), lowered a little, let go: the head end leans on the floor edge, the feet on the
            // ground. Only the lift is timed (lag).
            h.Stand = HeadStand(axis);
            if (!Grab(h, 1.30f))
            {
                Check(name, false, "D1", _run);
                yield break;
            }
            firstGrab = Time.fixedTime;
            _run.Lags.Clear();
            _recordLag = true;
            yield return Move(0.5f, To(h, Arc(AxisPoint(_body.Radius), _body.ClaimWorld(h.Slot), 1.05f)));
            _recordLag = false;
            yield return Move(1.5f, To(h, W(0.25f, 1.00f, -0.10f), W(1.60f, 0f, -0.10f)));
            yield return Move(0.4f, To(h, W(0.25f, 0.92f, -0.10f)));
            _recordLag = false;
            lags.AddRange(_run.Lags);
            ReleaseInfo(name, "D1", EdgeS(0, SlideEdgeX), "floor edge");
            ReleaseHand(h);
            yield return Idle(0.7f);
            Vector3 head = L(AxisPoint(_body.Height - _body.Radius));
            float speed = _body.Rigidbody.linearVelocity.magnitude;
            bool d1 = head.x <= SlideEdgeX + EdgeLean && head.y >= 0.75f && speed < 0.2f;

            // D2: the feet up and pushed in after it.
            Vector3 ankle = L(AxisPoint(0.08f));
            h.Stand = W(ankle.x + 0.6f, 0f, -0.10f);
            if (!Grab(h, 0.08f))
            {
                Check(name, false, Inv($"D1 head=({head.x:0.00},{head.y:0.00}) D2"), _run);
                yield break;
            }
            Vector3 c = _body.ClaimWorld(h.Slot);
            _run.Lags.Clear();
            _recordLag = true;
            yield return Move(0.5f, To(h, new Vector3(c.x, _o.y + 1.00f, c.z)));
            // Pushed until the head end meets the far wall (x -0.94; the body is 1.5 m, the bay 1.88 m wide), so the feet
            // clear the sliding door's path (tip x <= 0.77) and the door shuts.
            yield return Move(1.5f, To(h, W(0.55f, 0.95f, -0.10f), W(1.55f, 0f, -0.10f)));
            yield return Move(0.4f, To(h, W(0.55f, 0.85f, -0.10f)));
            _recordLag = false;
            lags.AddRange(_run.Lags);
            ReleaseHand(h);
            lastRelease = Time.fixedTime;
            float loaded = -1f;
            _observe = () =>
            {
                if (loaded < 0f && _npc.InCargo && ReferenceEquals(_npc.Carrier, _cargo.CargoSpace))
                    loaded = Time.fixedTime - lastRelease;
            };
            yield return Idle(1.5f);
            _observe = null;
            float feetX = L(AxisPoint(0f)).x;
            // time: the script's own move durations, for information (the real stun is in g).
            float time = lastRelease - firstGrab, p95 = Percentile(lags, 0.95f);
            bool ok = d1 && loaded >= 0f && p95 <= 0.35f;
            Check(name, ok, Inv($"D1 head=({head.x:0.00},{head.y:0.00}) v={speed:0.00} loaded={(loaded < 0f ? "no" : loaded.ToString("0.00", Inv0))}s ") +
                            Inv($"time(info)={time:0.0}s lagP95={p95:0.00}m feetX={feetX:0.00}"), _run);

            // Soft: the door shuts on a loaded body; the feet are in.
            if (feetX > 0.77f) Warn(name, Inv($"feet tip x={feetX:0.00} > 0.77"));
            _cargo.ToggleDoor(0);
            yield return WaitFor(() => _cargo.Slide.Openness <= 0.01f, 2.5f);
            if (!_waitOk) Warn(name, Inv($"sliding door did not close (openness {_cargo.Slide.Openness:0.00}, stalled {_cargo.Slide.IsStalled})"));
        }

        // ---------- (e) the rear doors ----------

        private IEnumerator RearDoors(int variant)
        {
            string name = $"e{variant + 1}";
            Progress = name;
            _run = new Run(name);
            float dx = variant == 0 ? 0f : variant == 1 ? 0.10f : -0.10f;
            float yawDeg = variant == 0 ? 0f : variant == 1 ? 6f : -6f;
            // Head toward the van (+z), the feet tip at z -4.60 (collar -3.30, head tip -3.10).
            Vector3 axisLocal = Quaternion.Euler(0f, yawDeg, 0f) * Vector3.forward;
            Vector3 centre = W(dx, 0f, -4.60f + 0.75f);
            Vector3 axis = _yaw * axisLocal;
            yield return Place(AreaRoot(centre, axis), axis);
            yield return EnsureOpen(1);

            // Logged all through: how far off the middle the body passes the wheel housings, and contacts with them.
            float housingX = 0f;
            int housingTicks = 0;
            float headOverBumper = float.PositiveInfinity;
            Action watchHousings = () =>
            {
                for (float s = 0f; s <= _body.Height + 1e-3f; s += 0.05f)
                {
                    Vector3 p = L(AxisPoint(s));
                    if (p.z >= HousingZMin && p.z <= HousingZMax && p.y - _body.Radius < HousingTop)
                        housingX = Mathf.Max(housingX, Mathf.Abs(p.x));
                }
                Vector3 headCap = L(AxisPoint(_body.Height - _body.Radius));
                if (headCap.z >= -2.38f && headCap.z <= -2.15f) headOverBumper = Mathf.Min(headOverBumper, headCap.y);
                if (TouchesHousing()) housingTicks++;
            };

            Hand h = _hands[0];
            var lags = new List<float>();
            float firstGrab, lastRelease;
            // E1: from beside the body the head end up, then onto the bumper (RearHeadMoves).
            h.Stand = HeadStand(axis);
            if (!Grab(h, 1.30f))
            {
                Check(name, false, "E1", _run);
                yield break;
            }
            firstGrab = Time.fixedTime;
            _observe = watchHousings;
            _run.Lags.Clear();
            _recordLag = true;
            yield return RearHeadMoves(h);
            _recordLag = false;
            lags.AddRange(_run.Lags);
            ReleaseInfo(name, "E1", EdgeS(2, RearEdgeZ), "bumper edge");
            ReleaseHand(h);
            yield return Idle(0.7f);
            Vector3 head = L(AxisPoint(_body.Height - _body.Radius));
            float speed = _body.Rigidbody.linearVelocity.magnitude;
            bool e1 = head.z >= RearEdgeZ - EdgeLean && head.y >= 0.75f && speed < 0.2f;

            // E2: the feet up and pushed in after it, between the wheel housings.
            Vector3 ankle = L(AxisPoint(0.08f));
            h.Stand = W(0f, 0f, ankle.z - 0.8f);
            if (!Grab(h, 0.08f))
            {
                _observe = null;
                Check(name, false, Inv($"E1 head=({head.z:0.00},{head.y:0.00}) E2"), _run);
                yield break;
            }
            _run.Lags.Clear();
            _recordLag = true;
            yield return RearFeetMoves(h);
            _recordLag = false;
            lags.AddRange(_run.Lags);
            ReleaseHand(h);
            lastRelease = Time.fixedTime;
            float loaded = -1f;
            _observe = () =>
            {
                watchHousings();
                if (loaded < 0f && _npc.InCargo && ReferenceEquals(_npc.Carrier, _cargo.CargoSpace))
                    loaded = Time.fixedTime - lastRelease;
            };
            yield return Idle(1.5f);
            _observe = null;
            float feetZ = L(AxisPoint(0f)).z;
            float time = lastRelease - firstGrab, p95 = Percentile(lags, 0.95f); // time: for information, as in d
            bool ok = e1 && loaded >= 0f && p95 <= 0.35f && housingX <= HousingHalfGap;
            string bumper = float.IsPositiveInfinity(headOverBumper) ? "-" : headOverBumper.ToString("0.00", Inv0);
            Check(name, ok, Inv($"E1 head=({head.z:0.00},{head.y:0.00}) v={speed:0.00} overBumper={bumper}m ") +
                            Inv($"loaded={(loaded < 0f ? "no" : loaded.ToString("0.00", Inv0))}s time(info)={time:0.0}s lagP95={p95:0.00}m ") +
                            Inv($"housingX={housingX:0.00}m housingTicks={housingTicks} feetZ={feetZ:0.00}"), _run);

            if (housingTicks > 0) Warn(name, $"{housingTicks} ticks touching the wheel housings");
            if (feetZ < -2.12f) Warn(name, Inv($"feet tip z={feetZ:0.00} < -2.12"));
            _cargo.ToggleDoor(1);
            yield return WaitFor(() => RearOpenness(false) <= 0.01f, 2.5f);
            if (!_waitOk) Warn(name, Inv($"rear doors did not close (openness {RearOpenness(false):0.00})"));
        }

        // E1 moves, holding the head end: lift it (timed), walk onto the body's line pushing the collar in as far as it
        // goes (out of reach on purpose: full side force), lower it a little. The head end then leans on the bumper.
        private IEnumerator RearHeadMoves(Hand h)
        {
            if (h.Slot < 0) yield break;
            yield return Move(0.5f, To(h, Arc(AxisPoint(_body.Radius), _body.ClaimWorld(h.Slot), 1.10f)));
            _recordLag = false;
            yield return Move(1.8f, To(h, W(0f, 1.00f, -1.60f), W(0f, 0f, -3.00f)));
            yield return Move(0.4f, To(h, W(0f, 0.92f, -1.60f)));
        }

        // E2 moves, holding an ankle: up, pushed in between the wheel housings, lowered.
        private IEnumerator RearFeetMoves(Hand h)
        {
            if (h.Slot < 0) yield break;
            Vector3 c = _body.ClaimWorld(h.Slot);
            yield return Move(0.5f, To(h, new Vector3(c.x, _o.y + 1.00f, c.z)));
            yield return Move(1.6f, To(h, W(0f, 0.95f, -2.00f), W(0f, 0f, -3.05f)));
            yield return Move(0.4f, To(h, W(0f, 0.88f, -2.00f)));
        }

        // Where the body passes over the van edge when let go (s from the feet; the head end leaning on it: about 1.1-1.3).
        private void ReleaseInfo(string name, string step, float edgeS, string edge)
        {
            Line(Inv($"{Tag} INFO {name} {step} release: {edge} under the body at s={edgeS:0.00} m from the feet, ") +
                 Inv($"centre of mass at s={ComS():0.00}"));
        }

        private bool TouchesHousing()
        {
            Collider capsule = _body.GetComponent<CapsuleCollider>();
            if (capsule == null) return false;
            Rigidbody rb = _body.Rigidbody;
            foreach (Collider housing in _housings)
                if (housing != null && Physics.ComputePenetration(capsule, rb.position, rb.rotation, housing,
                        housing.transform.position, housing.transform.rotation, out _, out _))
                    return true;
            return false;
        }

        // ---------- (f) dragging, informative ----------

        private IEnumerator Drag()
        {
            Progress = "f";
            _run = new Run("f");
            Vector3 axis = _yaw * Vector3.left; // head away from the van
            yield return Place(AreaRoot(W(-5.5f, 0f, 0f), axis), axis);
            Hand h = _hands[0];
            h.Stand = Flat(AxisPoint(1.30f)) + axis * 0.9f;
            if (!Grab(h, 1.30f))
            {
                Line($"{Tag} INFO f no grab");
                yield break;
            }
            yield return Move(0.4f, To(h, Arc(AxisPoint(_body.Radius), _body.ClaimWorld(h.Slot), 0.90f)));
            Vector3 centre0 = _body.Rigidbody.worldCenterOfMass;
            _run.Lags.Clear();
            _recordLag = true;
            yield return Move(3f / 1.2f, To(h, h.Target + axis * 3f, h.Stand + axis * 3f));
            _recordLag = false;
            float moved = Flat(_body.Rigidbody.worldCenterOfMass - centre0).magnitude;
            float lag = MeanTail(_run.Lags, _run.Lags.Count);
            string fails = _run.Fails.Count > 0 ? " [" + string.Join("; ", _run.Fails) + "]" : "";
            Line(Inv($"{Tag} INFO f lag={lag:0.00}m moved={moved:0.00}m of 3.00m") + fails);
            ReleaseAll();
        }

        // ---------- (g) the real stun, informative ----------

        // The rear-door load once more, with the fist's real head stun instead of the endless Out of the checks above:
        // Out (eyes shut, limp) for OutShare of it, then Groggy: a kick every 0.8-1.5 s, half of them tear a single hand
        // loose (KickTearChance[1]), and it crawls away whenever nobody holds it (between the head and the feet). The hand
        // walks from the head to the feet and may grab again once after a tear. INFO only: loaded or not, when, against
        // the Out window, and the tears.
        private IEnumerator RealStun()
        {
            const string name = "g";
            Progress = name;
            _run = new Run(name);
            Vector3 axis = _yaw * Vector3.forward;
            Vector3 root = AreaRoot(W(0f, 0f, -4.60f + 0.75f), axis);
            yield return Place(root, axis);
            yield return EnsureOpen(1);
            _infoRun = true;
            _tears = 0;
            _infoEarlyWakes = 0;
            // The hit (Hit only lengthens a stun, so the endless one goes first). Its push is undone: the body is put back
            // where it lay after the step that applies the impulse; the player then needs a moment to grab.
            _npc.StunLeft = 0f;
            Vector3 headTop = AxisPoint(_body.Height - _body.Radius);
            _npc.Hit(WeaponStun.Fist, HitZone.Head, headTop + Side(axis) * 0.8f, headTop);
            float hitAt = Time.fixedTime, stun = _npc.StunTotal, outWindow = stun * _npc.OutShare;
            yield return Idle(Time.fixedDeltaTime);
            Repose(root, axis);
            yield return Idle(0.4f);

            Hand h = _hands[0];
            int regrabs = 1;
            float loadedAt = -1f;
            _observe = () =>
            {
                if (loadedAt < 0f && _npc.InCargo && ReferenceEquals(_npc.Carrier, _cargo.CargoSpace))
                    loadedAt = Time.fixedTime - hitAt;
            };
            // E1: the head end onto the bumper.
            h.Stand = HeadStand(axis);
            if (Grab(h, 1.30f))
            {
                yield return RearHeadMoves(h);
                if (h.Slot < 0 && regrabs > 0 && _npc.State == NpcState.Down)
                {
                    regrabs--;
                    if (Grab(h, 1.30f, false)) yield return RearHeadMoves(h);
                }
            }
            ReleaseHand(h);
            // The walk to the feet (a moment to react, then walking), the feet grabbed from behind them.
            yield return Idle(0.3f);
            if (_npc.State == NpcState.Down && _body.Rigidbody != null)
            {
                Vector3 feetStand = FeetStand();
                yield return Move(Flat(feetStand - h.Stand).magnitude / WalkSpeed, To(h, AxisPoint(0.08f), feetStand));
            }
            if (_npc.State == NpcState.Down && _body.Rigidbody != null)
            {
                h.Stand = FeetStand(); // where the feet are now: it may have crawled meanwhile
                if (Grab(h, 0.08f))
                {
                    yield return RearFeetMoves(h);
                    if (h.Slot < 0 && regrabs > 0 && _npc.State == NpcState.Down)
                    {
                        regrabs--;
                        if (Grab(h, 0.08f, false)) yield return RearFeetMoves(h);
                    }
                }
                ReleaseHand(h);
                yield return Idle(1.5f);
            }
            _observe = null;
            bool inCargo = _npc.InCargo && ReferenceEquals(_npc.Carrier, _cargo.CargoSpace);
            string loaded = loadedAt < 0f
                ? "no"
                : Inv($"{loadedAt:0.0}s after the hit ({(loadedAt <= outWindow ? "within Out" : "Groggy")})");
            string fails = _run.Fails.Count > 0 ? " [" + string.Join("; ", _run.Fails) + "]" : "";
            Line(Inv($"{Tag} INFO g real head stun {stun:0.#}s, Out {outWindow:0.#}s: loaded={loaded} inCargoAtEnd={(inCargo ? 1 : 0)} ") +
                 Inv($"tears={_tears} regrabs={1 - regrabs} earlyWakes={_infoEarlyWakes} state={_npc.State}/{_npc.Phase}") + fails);
            _infoRun = false;
            ReleaseAll();
            // Down again for the teardown (it may have woken, sat up in the bay or run).
            if (_npc.State != NpcState.Down || _body.Rigidbody == null || _body.Seated)
                _npc.Hit(WeaponStun.Fist, HitZone.Torso, _npc.transform.position + _npc.transform.forward, _npc.Center);
            KeepStunned();
        }

        // Beside the head end, a little toward the feet: clear of the body, the step and the open rear leaves.
        private Vector3 HeadStand(Vector3 axis) =>
            Flat(AxisPoint(1.30f)) + Side(axis) * 0.7f - Flat(axis).normalized * 0.6f;

        // Behind the feet tip, on the body's line.
        private Vector3 FeetStand()
        {
            Vector3 back = Flat(AxisPoint(0f) - AxisPoint(1f));
            back = back.sqrMagnitude > 1e-4f ? back.normalized : -(_yaw * Vector3.forward);
            return Flat(AxisPoint(0.08f)) + back * 0.8f;
        }

        // ---------- Hands ----------

        private static Leg To(Hand h, Vector3 target) => To(h, target, h.Stand);

        private static Leg To(Hand h, Vector3 target, Vector3 stand) =>
            new() { Hand = h, FromTarget = h.Target, ToTarget = target, FromStand = h.Stand, ToStand = stand };

        // Aims at the top of the body at 's' (straight out from the axis, so a leaning body is aimed at right) and grabs.
        // False (and a "grab blocked" failure) when the grabber got nothing or not this body; a failure too when the hold
        // landed more than 0.10 m from 's'. freeSpot: the hand must not stand in the body (a KCC capsule only passes
        // through the body it holds); false for a re-grab where the hand already is.
        private bool Grab(Hand h, float s, bool freeSpot = true)
        {
            h.Slot = -1;
            h.Hold = -1f;
            if (freeSpot && StandBlocked(h, StandMask | (1 << OvLayers.NpcBody), out string blocker))
                _run?.Fail(Inv($"grabbing at s={s:0.00} from inside {blocker}"));
            Vector3 axis = _body.Rigidbody.rotation * Vector3.up;
            Vector3 up = Vector3.ProjectOnPlane(Vector3.up, axis);
            if (up.sqrMagnitude < 1e-6f) up = Vector3.ProjectOnPlane(Vector3.forward, axis);
            h.Target = AxisPoint(s) + up.normalized * (SurfaceAbove(s) - 0.01f);
            Aim(h);
            if (h.Grabber.ScriptGrab())
                for (int i = 0; i < _body.Claims.Length; i++)
                    if (ReferenceEquals(_body.Claims[i].Holder, h.Grabber))
                        h.Slot = i;
            if (h.Slot < 0)
            {
                h.Grabber.ScriptRelease();
                _run?.Fail(Inv($"grab blocked at s={s:0.00}"));
                return false;
            }
            float got = _body.Claims[h.Slot].Local.y;
            if (Mathf.Abs(got - s) > 0.10f) _run?.Fail(Inv($"grabbed at s={got:0.00}, not {s:0.00}"));
            h.Target = _body.ClaimWorld(h.Slot);
            h.Hold = h.Grabber.PointHoldDistance;
            Aim(h); // now holding: hold distance, reach and stand checks
            return true;
        }

        private static void ReleaseHand(Hand h)
        {
            h.Grabber.ScriptRelease();
            h.Slot = -1;
            h.Hold = -1f;
        }

        private void ReleaseAll()
        {
            foreach (Hand h in _hands) ReleaseHand(h);
        }

        // The eye where the hand stands, looking at its target; while holding, the hold distance (the wheel) follows the
        // target, within reach and no faster than a wheel turns, and the place it stands must be free.
        private void Aim(Hand h)
        {
            Vector3 eye = Feet(h.Stand) + Vector3.up * StandEye;
            Vector3 to = h.Target - eye;
            if (to.sqrMagnitude > 1e-6f) h.View.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(to));
            else h.View.transform.position = eye;
            if (!h.Grabber.IsHolding || h.Slot < 0) return;
            float want = to.magnitude;
            float longest = Mathf.Max(MinHold, _body.Profile.HoldDistance);
            if (want < MinHold - ReachSlack || want > longest + ReachSlack) _run?.Fail(Inv($"out of reach ({want:0.00} m)"));
            if (h.Hold >= 0f && Mathf.Abs(want - h.Hold) > MaxWheelSpeed * Time.fixedDeltaTime + 1e-4f)
                _run?.Fail(Inv($"unrealistic wheel ({Mathf.Abs(want - h.Hold) / Time.fixedDeltaTime:0.0} m/s)"));
            h.Grabber.PointHoldDistance = want;
            h.Hold = want;
            if (StandBlocked(h, StandMask, out string blocker)) _run?.Fail($"stand blocked by {blocker}");
        }

        // A standing KCC capsule at the hand's place would overlap 'mask' (while holding: the world and the van, not the
        // body it holds, which the KCC ignores).
        private bool StandBlocked(Hand h, int mask, out string blocker)
        {
            Vector3 feet = Feet(h.Stand);
            Collider[] hits = Physics.OverlapCapsule(feet + Vector3.up * 0.37f, feet + Vector3.up * (StandHeight - 0.35f),
                StandRadius, mask, QueryTriggerInteraction.Ignore);
            blocker = hits.Length > 0 ? hits[0].name : null;
            return hits.Length > 0;
        }

        private Vector3 Feet(Vector3 stand)
        {
            var from = new Vector3(stand.x, _o.y + 1.5f, stand.z);
            return Physics.Raycast(from, Vector3.down, out RaycastHit hit, 3f, FeetMask, QueryTriggerInteraction.Ignore)
                ? hit.point
                : new Vector3(stand.x, _o.y, stand.z);
        }

        private static Vector3 HandPoint(Hand h) => h.Grabber.PointHoldTarget;

        // Moves the hands' targets and stands linearly over at least 'nominal' seconds, slower if a hold distance would
        // change faster than the wheel (WheelPlan). Each tick: aim, one physics step, then the per-tick bookkeeping.
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
                    Aim(leg.Hand);
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
            return Mathf.Max(nominal, worst / WheelPlan, Time.fixedDeltaTime);
        }

        private float HoldAt(Leg leg, float u)
        {
            Vector3 eye = Feet(Vector3.Lerp(leg.FromStand, leg.ToStand, u)) + Vector3.up * StandEye;
            return Vector3.Distance(Vector3.Lerp(leg.FromTarget, leg.ToTarget, u), eye);
        }

        // Physics ticks with nobody moving.
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
            _waitOk = done();
            int ticks = Ticks(timeout);
            for (int k = 0; k < ticks && !_waitOk; k++)
            {
                yield return Fixed;
                AfterTick();
                _waitOk = done();
            }
        }

        private IEnumerator EnsureOpen(int door)
        {
            if (!_cargo.DoorOpen(door)) _cargo.ToggleDoor(door);
            yield return WaitFor(() => door == 0 ? _cargo.Slide.Openness >= 0.99f : RearOpenness(true) >= 0.99f, 3f);
            if (!_waitOk) _run?.Fail(door == 0 ? "sliding door did not open" : "rear doors did not open");
        }

        private void AfterTick()
        {
            Rigidbody rb = _body != null ? _body.Rigidbody : null;
            if (rb != null && !GrabPhysicsSolver.IsFinite(rb.position)) _nan = true;
            if (_run != null && _npc != null && _npc.State != NpcState.Down) _run.Fail($"NPC woke up ({_npc.State})");
            foreach (Hand h in _hands)
            {
                if (h.Slot < 0) continue;
                if (!h.Grabber.IsHolding || !_body.IsClaimValid(h.Grabber, h.Slot))
                {
                    if (_infoRun) _tears++;
                    else _run?.Fail("lost grip");
                    h.Grabber.ScriptRelease();
                    h.Slot = -1;
                    h.Hold = -1f;
                    continue;
                }
                if (_recordLag && _run != null) _run.Lags.Add(Vector3.Distance(HandPoint(h), _body.ClaimWorld(h.Slot)));
            }
            _observe?.Invoke();
        }

        // ---------- The body ----------

        // Lays the body flat with its feet tip at 'root', head along 'axis', stunned for long (Out: no kicks, no crawl),
        // not loaded; then lets it settle. A body that woke up is knocked down again first.
        private IEnumerator Place(Vector3 root, Vector3 axis)
        {
            ReleaseAll();
            _observe = null;
            _recordLag = false;
            if (_npc.State != NpcState.Down || _body.Rigidbody == null || _body.Seated)
                _npc.Hit(WeaponStun.Fist, HitZone.Torso, _npc.transform.position + _npc.transform.forward, _npc.Center);
            _body.UnpinAll();
            Repose(root, axis);
            KeepStunned();
            yield return Idle(SettleTime);
            KeepStunned();
        }

        // Teleports the body flat with its feet tip at 'root', head along 'axis', at rest.
        private void Repose(Vector3 root, Vector3 axis)
        {
            Rigidbody rb = _body.Rigidbody;
            Quaternion rotation = Quaternion.LookRotation(Vector3.up, axis);
            rb.position = root;
            rb.rotation = rotation;
            rb.linearVelocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
            _npc.transform.SetPositionAndRotation(root, rotation);
            Physics.SyncTransforms();
        }

        private void KeepStunned()
        {
            _npc.StunTotal = 600f;
            _npc.StunLeft = 600f;
            _npc.Phase = StunPhase.Out;
            _npc.Condition = 100f;
            _npc.InCargo = false;
            _npc.Carrier = null;
        }

        // Feet tip of a flat body centred at 'centre' (ground level) with its head along 'axis'.
        private Vector3 AreaRoot(Vector3 centre, Vector3 axis)
        {
            Vector3 root = centre - axis.normalized * (_body.Height * 0.5f);
            root.y = _o.y + _body.Radius + 0.01f;
            return root;
        }

        private Vector3 AxisPoint(float s)
        {
            Rigidbody rb = _body.Rigidbody;
            return rb.position + rb.rotation * new Vector3(0f, s, 0f);
        }

        // s of the centre of mass along the axis.
        private float ComS()
        {
            Rigidbody rb = _body.Rigidbody;
            return Vector3.Dot(rb.worldCenterOfMass - rb.position, rb.rotation * Vector3.up);
        }

        // s where the axis crosses van-local x (component 0) or z (2) = 'at'; NaN when it runs along it.
        private float EdgeS(int component, float at)
        {
            Vector3 a = L(AxisPoint(0f)), b = L(AxisPoint(1f));
            float d = b[component] - a[component];
            return Mathf.Abs(d) < 1e-4f ? float.NaN : (at - a[component]) / d;
        }

        // Height of the capsule's top above its axis at 's' (lower over the rounded end caps).
        private float SurfaceAbove(float s)
        {
            float r = _body.Radius;
            float intoCap = Mathf.Max(r - s, s - (_body.Height - r));
            return intoCap > 0f ? Mathf.Sqrt(Mathf.Max(0f, r * r - intoCap * intoCap)) : r;
        }

        // Where the claim is when lifted to 'height' with the body turning about 'farCap': same distance from the cap, in
        // the vertical plane through the cap and the claim.
        private Vector3 Arc(Vector3 farCap, Vector3 claim, float height)
        {
            float length = Vector3.Distance(farCap, claim);
            Vector3 toward = Flat(claim - farCap);
            toward = toward.sqrMagnitude > 1e-6f ? toward.normalized : Vector3.forward;
            float y = _o.y + height;
            float dy = y - farCap.y;
            return new Vector3(farCap.x, y, farCap.z) + toward * Mathf.Sqrt(Mathf.Max(0f, length * length - dy * dy));
        }

        private static Vector3 Side(Vector3 axis) => Vector3.Cross(Vector3.up, axis).normalized;

        // ---------- Frames, numbers, report ----------

        private Vector3 W(float x, float y, float z) => _o + _yaw * new Vector3(x, y, z);
        private Vector3 L(Vector3 world) => Quaternion.Inverse(_yaw) * (world - _o);
        private float Height(Vector3 world) => world.y - _o.y;
        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
        private static int Ticks(float seconds) => Mathf.Max(1, Mathf.CeilToInt(seconds / Time.fixedDeltaTime - 1e-3f));

        private static float MeanTail(List<float> values, int count)
        {
            if (values.Count == 0) return float.PositiveInfinity;
            int from = Mathf.Max(0, values.Count - count);
            float sum = 0f;
            for (int i = from; i < values.Count; i++) sum += values[i];
            return sum / (values.Count - from);
        }

        private static float Percentile(List<float> values, float p)
        {
            if (values.Count == 0) return float.PositiveInfinity;
            var sorted = new List<float>(values);
            sorted.Sort();
            return sorted[Mathf.Clamp(Mathf.CeilToInt(p * sorted.Count) - 1, 0, sorted.Count - 1)];
        }

        private static readonly IFormatProvider Inv0 = System.Globalization.CultureInfo.InvariantCulture;
        private static string Inv(FormattableString s) => FormattableString.Invariant(s);

        private void Check(string name, bool ok, string details, Run run)
        {
            if (run != null && run.Fails.Count > 0) ok = false;
            _checks++;
            if (ok) _passes++;
            string reasons = run != null && run.Fails.Count > 0 ? " [" + string.Join("; ", run.Fails) + "]" : "";
            Line($"{Tag} {(ok ? "PASS" : "FAIL")} {name} {details}{reasons}");
        }

        private void Warn(string name, string what)
        {
            _warnings++;
            Line($"{Tag} WARN {name} {what}");
        }

        private void Line(string text)
        {
            _report.AppendLine(text);
            Progress = text;
            if (text.Contains(" FAIL ") || text.Contains(" WARN ") || text.Contains("ABORTED")) Debug.LogWarning(text);
            else Debug.Log(text);
        }
    }
}
#endif
