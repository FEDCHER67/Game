using System.Collections.Generic;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The van's cargo bay in the grey-box, NPC capture stage 1 (canon section 151, draft sections 2-3): physical loading,
    // NPCs riding along, escapes through an opening door, ejection, the cargo doors for the on-foot pawn and the cargo HUD.
    // No slots, no load key: players drag and push the bodies in themselves (GreyboxNpcBody + PhysicsGrabber).
    // - Loading: a downed body counts as loaded when, for LoadHold seconds, its pelvis and collar are inside the cargo box
    //   (VanCargoSpace), nobody holds it and it is at rest RELATIVE TO THE VAN (|v - van point velocity| < LoadRestSpeed;
    //   in a moving van the world speed is never zero). Then InCargo + Carrier on the NPC and a thud: an impulse down on the
    //   van at that point, the suspension dips (no text). Pelvis or collar out of the box by more than UnloadMargin:
    //   unloaded. Loaded bodies nobody holds are damped toward the van's velocity (F = (vanVel - v) m LoadedDamping), so
    //   they settle and ride along; hard braking still throws them about.
    // - Passengers (CargoSeated, awake): GreyboxNpcBody.SetSeated makes them a 1 m upright capsule on layer NpcSeated;
    //   here they are kept moving with the van (F = (vanVel - v) m SeatedMatching) and turned with it (yaw relative to the
    //   van). One that ends up out of the bay anyway (braking with the door open) gets out like an escaper.
    // - Escapes: while a cargo door is more than EscapeOpenness open, every passenger and every loaded Groggy body nobody
    //   holds first turns to that door with a surprised face (the warning), and after EscapeDelay goes for it: a passenger
    //   runs (target velocity = van point velocity + EscapeSpeed toward the doorway, one EscapeHop up), a lying Groggy body
    //   crawls (GreyboxNpc.CrawlToward, EscapeCrawlForce). Out past the doorway: above EscapeTumbleKmh it is Down again on
    //   the road (fist to the torso, Condition - EscapeConditionCost); slower, a passenger is Free and flees, a Groggy body
    //   is simply out (it wakes up where it lies). No progress for EscapeGiveUp seconds or the door closing: back to sitting
    //   with a startled flash, and it tries again after EscapeRetry if the door stays open. Out (eyes shut) bodies stay put.
    // - Ejection: the van on its side or roof for EjectAfterFlip seconds, or in the sea: everyone in the bay is put outside
    //   (bodies placed, passengers stand up and run, a riding player via GreyboxPawn.Teleport). In the sea this waits for
    //   the van's SeaReturnTracker to put the van back on land, so they land next to it rather than in the water. Any other
    //   van teleport (F1-F8, R: VanController.ResetCount, or a jump over TeleportJump) carries the loaded NPCs and a
    //   riding player along.
    // - HUD: "Груз: n (оглушены m)" while driving or near the van; "тесно" above SoftLimit (a soft limit, nothing stops more).
    // Van-local coordinates follow VanSetupBuilder's Blender boxes, local = (-bx, bz, -by - 0.02): rear opening z -2.21,
    // sliding door on +X at z -0.92..0.42 (driver door on -X), van skin at x +-0.94, floor 0.55.
    // State on the NPCs is plain data (InCargo, Carrier, State); the per-NPC timers here are offline bookkeeping.
    [RequireComponent(typeof(VanController))]
    [DefaultExecutionOrder(-50)] // before SeaReturnTracker (0): sees the van in the sea before the tracker moves it out
    public sealed class GreyboxVanCargo : MonoBehaviour
    {
        private const float DoorReach = 2.2f;
        private const float SlideSideX = 0.8f;  // the pawn must be beyond this van-local x for the sliding door
        private const float RearSideZ = -2.0f;  // and behind this van-local z for the rear pair
        private const float HudRadius = 6f;
        private const float HandleReach = 1.2f;
        private const int SlideDoor = 0;
        private const int RearDoors = 1;

        public VanDoor Slide;
        public VanDoor RearLeft;
        public VanDoor RearRight;
        [Tooltip("Sliding door open/close time in the grey-box (the driver's 3, the handle, E outside).")]
        public float SlideDuration = 0.6f;

        [Header("Loading")]
        public float LoadHold = 0.5f;
        [Tooltip("m/s relative to the van.")]
        public float LoadRestSpeed = 0.25f;
        [Tooltip("N·s down on the van when a body counts as loaded.")]
        public float LoadThud = 400f;
        public float UnloadMargin = 0.15f;
        [Tooltip("1/s: loaded bodies nobody holds are pulled toward the van's velocity.")]
        public float LoadedDamping = 1.5f;
        [Tooltip("The HUD says it is cramped above this many NPCs (lying bodies stack physically, nothing stops more).")]
        public int SoftLimit = 4;

        [Header("Passengers")]
        [Tooltip("1/s: sitting NPCs are pulled toward the van's velocity.")]
        public float SeatedMatching = 4f;
        [Tooltip("Degrees per second a sitting NPC turns toward a door.")]
        public float SeatedTurnSpeed = 300f;

        [Header("Escapes")]
        [Range(0f, 1f)] public float EscapeOpenness = 0.3f;
        [Tooltip("Seconds from noticing an open door to the run (random in range).")]
        public Vector2 EscapeDelay = new(0.4f, 1.2f);
        [Tooltip("m/s toward the doorway, on top of the van's own velocity.")]
        public float EscapeSpeed = 2.5f;
        [Tooltip("m/s up when the run starts.")]
        public float EscapeHop = 2f;
        [Tooltip("1/s: how hard the runner chases its target velocity.")]
        public float EscapeAccel = 10f;
        public float EscapeGiveUp = 1.5f;
        public float EscapeRetry = 2f;
        [Tooltip("Metres past the doorway (the van's skin) at which the NPC is out.")]
        public float EscapePast = 0.25f;
        [Tooltip("Above this speed an escaping NPC tumbles onto the road instead of landing.")]
        public float EscapeTumbleKmh = 12f;
        public float EscapeConditionCost = 10f;

        [Header("Ejection")]
        public float EjectAfterFlip = 1f;
        [Tooltip("A van move longer than this in one physics tick is a teleport. Resets (R, F1-F8, the sea return: " +
                 "VanController.ResetCount) always count, however short.")]
        public float TeleportJump = 3f;

        // Below this relative speed (m/s, squared) no matching force is applied, so bodies in a parked van can sleep
        // (any non-zero AddForce wakes a body, and a body touching the van keeps the van's island awake too).
        private const float SettledSpeedSqr = 0.05f * 0.05f;

        // Door 0 = sliding door, 1 = rear pair. Van-local points outside: where the pawn stands to use the door, and where
        // ejected passengers land.
        private static readonly Vector3[] DoorOutside = { new(1.55f, 0f, -0.25f), new(0f, 0f, -3.0f) };
        // The doorway: a point on its plane at floor height (the van's skin x 0.94; the rear opening z -2.21) and the
        // plane's outward normal, van-local.
        private static readonly Vector3[] Doorway = { new(0.94f, 0.55f, -0.25f), new(0f, 0.55f, -2.21f) };
        private static readonly Vector3[] DoorwayNormal = { Vector3.right, Vector3.back };
        // Inside handle of the sliding door, van-local.
        private static readonly Vector3 HandlePoint = new(0.8f, 1.0f, -0.25f);
        private static readonly string[] DoorNames = { "сдвижную дверь", "задние двери" };

        private sealed class Tracked
        {
            public NpcState State;  // last seen; a change from outside (hit, woke up) drops the escape in progress
            public float RestFor;   // not loaded yet: how long the load conditions have held
            public float Yaw;       // sitting: facing relative to the van, degrees
            public float TargetYaw;
            public int Door = -1;   // escape: the door it goes for
            public float GoAt;      // escape: end of the warning
            public bool Running;
            public float Best;      // escape: nearest it got to the doorway (m)
            public float ProgressAt;
            public float RetryAt;
        }

        private VanController _van;
        private Rigidbody _vanBody;
        private GreyboxVanSeat _seat;
        private VanCargoSpace _space;
        private readonly Dictionary<GreyboxNpc, Tracked> _tracked = new();
        private readonly HashSet<GreyboxNpc> _seen = new();
        private readonly List<GreyboxNpc> _drop = new();
        private float _flippedFor;
        private bool _seaPending;
        private float _seaEjectAt;
        private bool _hasLastPose;
        private Vector3 _lastVanPos;
        private Quaternion _lastVanRot;
        private int _lastResetCount;

        public float SpeedKmh => _van != null ? _van.SpeedKmh : 0f;
        public Vector3 VanVelocity => _vanBody != null ? _vanBody.linearVelocity : Vector3.zero;
        public VanCargoSpace CargoSpace => _space;

        // In OnEnable rather than Awake (same moment at start): it also runs after a script reload in Play mode.
        private void OnEnable()
        {
            if (_van == null) _van = GetComponent<VanController>();
            if (_vanBody == null) _vanBody = GetComponent<Rigidbody>();
            if (_seat == null) _seat = GetComponent<GreyboxVanSeat>();
        }

        private void Start()
        {
            // VanDriveInput finds its doors by name in Awake; scenes that added it at build time have no references to copy.
            if (TryGetComponent(out VanDriveInput input))
            {
                if (Slide == null) Slide = input.Slide;
                if (RearLeft == null) RearLeft = input.RearLeft;
                if (RearRight == null) RearRight = input.RearRight;
            }
            if (Slide == null) Slide = FindDoor("VAN_Door_Slide");
            if (RearLeft == null) RearLeft = FindDoor("VAN_Door_Rear_Left");
            if (RearRight == null) RearRight = FindDoor("VAN_Door_Rear_Right");
            // Van.prefab built before stage 1 has a 1.1 s sliding door.
            if (Slide != null && SlideDuration > 0f) Slide.Duration = SlideDuration;
            TryGetComponent(out _space);
        }

        private VanDoor FindDoor(string doorName)
        {
            foreach (VanDoor door in GetComponentsInChildren<VanDoor>(true))
                if (door.name == doorName) return door;
            return null;
        }

        // ---------- Doors ----------

        /// <summary>Requested state (the door may still be moving or held by a foot).</summary>
        public bool DoorOpen(int door) => door == SlideDoor ? Requested(Slide) : Requested(RearLeft) || Requested(RearRight);

        public string DoorName(int door) => DoorNames[door];

        public void ToggleDoor(int door)
        {
            if (door == SlideDoor)
            {
                if (Slide != null) Slide.Request(!Slide.TargetOpen);
                return;
            }
            // The rear pair moves together: both shut if either is open.
            bool open = DoorOpen(RearDoors);
            if (RearLeft != null) RearLeft.Request(!open);
            if (RearRight != null) RearRight.Request(!open);
        }

        // Nearest cargo door whose outside point is within reach of 'position' (flat distance), or -1. Only from that
        // door's side: the rear reach overlaps the driver-door area along the back of the left side.
        public int NearestDoor(Vector3 position)
        {
            int best = -1;
            float bestDistance = DoorReach;
            Vector3 local = transform.InverseTransformPoint(position);
            for (int door = 0; door < DoorOutside.Length; door++)
            {
                if (door == SlideDoor ? Slide == null : RearLeft == null && RearRight == null) continue;
                if (door == SlideDoor ? local.x <= SlideSideX : local.z >= RearSideZ) continue;
                Vector3 d = transform.TransformPoint(DoorOutside[door]) - position;
                float distance = new Vector2(d.x, d.z).magnitude;
                if (distance <= bestDistance)
                {
                    best = door;
                    bestDistance = distance;
                }
            }
            return best;
        }

        /// <summary>Whether a pawn standing at 'feet' is in the cargo bay within reach of the sliding door's inside handle.</summary>
        public bool AtInsideHandle(Vector3 feet)
        {
            if (Slide == null || (_space == null && !TryGetComponent(out _space))) return false;
            // The pawn position is at its feet, on the floor: test the box half a metre higher.
            if (!_space.Contains(feet + transform.up * 0.5f)) return false;
            Vector3 d = transform.InverseTransformPoint(feet) - HandlePoint;
            return new Vector2(d.x, d.z).magnitude <= HandleReach;
        }

        private static bool Requested(VanDoor d) => d != null && d.TargetOpen;

        // How far open a door is (the rear pair: the wider of the two).
        private float Openness(int door)
        {
            if (door == SlideDoor) return Slide != null ? Slide.Openness : 0f;
            return Mathf.Max(RearLeft != null ? RearLeft.Openness : 0f, RearRight != null ? RearRight.Openness : 0f);
        }

        // Van-local middle of a doorway at floor height; with one rear door open, the middle of that half (left = -X).
        private Vector3 DoorwayLocal(int door)
        {
            Vector3 p = Doorway[door];
            if (door == RearDoors)
            {
                bool left = RearLeft != null && RearLeft.Openness > EscapeOpenness;
                bool right = RearRight != null && RearRight.Openness > EscapeOpenness;
                if (left != right) p.x = left ? -0.4f : 0.4f;
            }
            return p;
        }

        // Metres from a point to the doorway plane, positive while still inside.
        private float ToDoorway(int door, Vector3 world) =>
            -Vector3.Dot(_space.ToLocal(world) - Doorway[door], DoorwayNormal[door]);

        // World point a metre out through the doorway: runners and crawlers aim there, so they always head out.
        private Vector3 EscapeGoal(int door) => _space.ToWorld(DoorwayLocal(door) + DoorwayNormal[door]);

        // The open door (past EscapeOpenness) nearest to a point, or -1.
        private int OpenDoorNear(Vector3 world)
        {
            int best = -1;
            float bestDistance = float.MaxValue;
            for (int door = 0; door < Doorway.Length; door++)
            {
                if (Openness(door) <= EscapeOpenness) continue;
                float d = Vector3.Distance(world, _space.ToWorld(DoorwayLocal(door)));
                if (d < bestDistance)
                {
                    best = door;
                    bestDistance = d;
                }
            }
            return best;
        }

        // ---------- Physics tick ----------

        private void FixedUpdate()
        {
            if ((_space == null && !TryGetComponent(out _space)) || _vanBody == null) return;
            float dt = Time.fixedDeltaTime;
            float now = Time.time;
            if (CheckMovedOrEjected(dt, now)) return;

            _seen.Clear();
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !npc.isActiveAndEnabled) continue;
                GreyboxNpcBody body = npc.Body;
                if (body == null || !body.Active) continue;
                bool ours = Ours(npc);
                if (npc.InCargo && !ours) continue; // another van's
                switch (npc.State)
                {
                    case NpcState.Down:
                        TickDown(npc, body, ours, dt, now);
                        break;
                    case NpcState.CargoSeated:
                    case NpcState.Escaping:
                        if (ours) TickPassenger(npc, body, dt, now);
                        break;
                }
            }
            Prune();
        }

        private bool Ours(GreyboxNpc npc) => npc.InCargo && ReferenceEquals(npc.Carrier, _space);

        // A downed body: loading it, unloading it, damping it, and a Groggy one crawling for an open door.
        private void TickDown(GreyboxNpc npc, GreyboxNpcBody body, bool ours, float dt, float now)
        {
            Rigidbody rb = body.Rigidbody;
            Vector3 com = rb.worldCenterOfMass;
            Vector3 pelvis = body.PointWorld((int)GreyboxNpcBody.Point.Pelvis);
            Vector3 collar = body.PointWorld((int)GreyboxNpcBody.Point.Collar);
            Vector3 relative = rb.linearVelocity - _space.PointVelocity(com);
            if (!ours)
            {
                if (!_space.Contains(pelvis) || !_space.Contains(collar)) return; // not in the bay: not ours to track
                Tracked loading = Track(npc, rb);
                bool resting = _space.Upright && body.HolderCount == 0 && relative.magnitude < LoadRestSpeed;
                loading.RestFor = resting ? loading.RestFor + dt : 0f;
                if (loading.RestFor >= LoadHold) Load(npc, com, loading);
                return;
            }

            Tracked t = Track(npc, rb);
            if (!_space.Contains(pelvis, UnloadMargin) || !_space.Contains(collar, UnloadMargin))
            {
                // Out of the bay: a crawler on its way out gets the escape rules (the tumble at speed); a body that just
                // slid out (braking with the door open) is simply no longer loaded, physics does the rest.
                if (t.Running) GetOut(npc, rb, com);
                else Unload(npc);
                return;
            }
            if (npc.Phase == StunPhase.Groggy && body.HolderCount == 0)
            {
                if (TickEscape(npc, body, t, com, now) && t.Running && KeepGoing(npc, rb, t, com, now))
                    npc.CrawlGoal = EscapeGoal(t.Door);
            }
            else if (t.Door >= 0)
            {
                StopEscape(npc, t, now); // held, or knocked Out again
            }
            if (body.HolderCount == 0 && !t.Running && relative.sqrMagnitude > SettledSpeedSqr)
                rb.AddForce(-relative * (rb.mass * LoadedDamping));
        }

        private void Load(GreyboxNpc npc, Vector3 at, Tracked t)
        {
            npc.InCargo = true;
            npc.Carrier = _space;
            t.RestFor = 0f;
            _vanBody.AddForceAtPosition(Vector3.down * LoadThud, at, ForceMode.Impulse);
        }

        private void Unload(GreyboxNpc npc)
        {
            Forget(npc);
            npc.InCargo = false;
            npc.Carrier = null;
        }

        // A sitting or escaping NPC.
        private void TickPassenger(GreyboxNpc npc, GreyboxNpcBody body, float dt, float now)
        {
            Rigidbody rb = body.Rigidbody;
            Vector3 com = rb.worldCenterOfMass;
            Tracked t = Track(npc, rb);
            Vector3 vanVelocity = _space.PointVelocity(com);
            if (npc.State == NpcState.Escaping)
            {
                // Grabbed on the run (draft section 2: "схватить"): caught, it sits back down with a startled flash;
                // CancelEscape makes it ungrabbable again, so the hand slips off. It may try again after EscapeRetry.
                if (body.HolderCount > 0)
                {
                    StopEscape(npc, t, now);
                    Turn(rb, t, dt);
                    return;
                }
                Run(npc, rb, t, com, vanVelocity, now);
                // Run may have let it out: stood up (body gone) or tumbling on the road (not ours, lying).
                if (body.Active && Ours(npc) && npc.State != NpcState.Down) Turn(rb, t, dt);
                return;
            }
            // Thrown out of the bay while sitting (braking with the door open, a shove): out, by the same rules.
            if (!_space.Contains(com, 0.3f))
            {
                GetOut(npc, rb, com);
                return;
            }
            Vector3 lag = vanVelocity - rb.linearVelocity;
            if (lag.sqrMagnitude > SettledSpeedSqr) rb.AddForce(lag * (rb.mass * SeatedMatching));
            TickEscape(npc, body, t, com, now);
            Turn(rb, t, dt);
        }

        // Noticing an open door, the warning, and the start of the run. True while an escape is on (warning or running).
        private bool TickEscape(GreyboxNpc npc, GreyboxNpcBody body, Tracked t, Vector3 com, float now)
        {
            if (t.Door < 0)
            {
                if (now < t.RetryAt) return false;
                int door = OpenDoorNear(com);
                if (door < 0) return false;
                t.Door = door;
                t.GoAt = now + Random.Range(EscapeDelay.x, EscapeDelay.y);
                t.Running = false;
            }
            if (Openness(t.Door) <= EscapeOpenness)
            {
                StopEscape(npc, t, now); // shut before it got out
                return false;
            }
            Vector3 goal = EscapeGoal(t.Door);
            if (t.Running) return true;
            // The warning: it stares at the door, startled.
            npc.Flash();
            t.TargetYaw = VanYaw(goal - com);
            if (now < t.GoAt) return true;
            t.Running = true;
            t.Best = ToDoorway(t.Door, com);
            t.ProgressAt = now;
            if (npc.State == NpcState.CargoSeated)
            {
                npc.BeginEscape();
                t.State = npc.State;
                body.Rigidbody.AddForce(_space.Rotation * Vector3.up * EscapeHop, ForceMode.VelocityChange);
            }
            else
            {
                npc.CrawlToward = true;
                npc.CrawlGoal = goal;
            }
            return true;
        }

        // A running passenger: velocity toward the doorway on top of the van's own, facing where it runs.
        private void Run(GreyboxNpc npc, Rigidbody rb, Tracked t, Vector3 com, Vector3 vanVelocity, float now)
        {
            if (!t.Running || t.Door < 0 || Openness(t.Door) <= EscapeOpenness)
            {
                StopEscape(npc, t, now);
                return;
            }
            if (!KeepGoing(npc, rb, t, com, now)) return;
            Vector3 up = _space.Rotation * Vector3.up;
            Vector3 toward = Vector3.ProjectOnPlane(EscapeGoal(t.Door) - com, up);
            if (toward.sqrMagnitude < 1e-4f) toward = _space.Rotation * DoorwayNormal[t.Door];
            Vector3 desired = vanVelocity + toward.normalized * EscapeSpeed;
            rb.AddForce(Vector3.ProjectOnPlane(desired - rb.linearVelocity, up) * (rb.mass * EscapeAccel));
            t.TargetYaw = VanYaw(toward);
        }

        // While running or crawling: past the doorway -> out; no progress for EscapeGiveUp -> gives up. True = keep going.
        private bool KeepGoing(GreyboxNpc npc, Rigidbody rb, Tracked t, Vector3 com, float now)
        {
            float left = ToDoorway(t.Door, com);
            if (left < -EscapePast)
            {
                GetOut(npc, rb, com);
                return false;
            }
            if (left < t.Best - 0.05f)
            {
                t.Best = left;
                t.ProgressAt = now;
            }
            else if (now - t.ProgressAt > EscapeGiveUp)
            {
                StopEscape(npc, t, now);
                return false;
            }
            return true;
        }

        // Out of the van: tumbles at speed (stunned again, costs Condition); slower, a passenger lands and flees, a Groggy
        // body is just out of the bay.
        private void GetOut(GreyboxNpc npc, Rigidbody rb, Vector3 com)
        {
            Forget(npc);
            if (_space.PointVelocity(com).magnitude * 3.6f > EscapeTumbleKmh)
            {
                npc.Condition = Mathf.Max(0f, npc.Condition - EscapeConditionCost);
                npc.LeaveCargo(true, rb.linearVelocity);
                return;
            }
            if (npc.State == NpcState.Down)
            {
                npc.InCargo = false;
                npc.Carrier = null;
                return;
            }
            npc.LeaveCargo(false, Vector3.zero);
        }

        // Escape off (door shut, no way through, held): back to sitting with a flash; may try again after EscapeRetry.
        private void StopEscape(GreyboxNpc npc, Tracked t, float now)
        {
            if (npc.State == NpcState.Escaping) npc.CancelEscape(); // flashes too
            else if (t.Door >= 0) npc.Flash();
            t.State = npc.State;
            npc.CrawlToward = false;
            if (t.Door >= 0) t.RetryAt = now + EscapeRetry;
            t.Door = -1;
            t.Running = false;
        }

        // Sitting NPCs keep their facing relative to the van (rotation is frozen in physics), turning toward TargetYaw.
        private void Turn(Rigidbody rb, Tracked t, float dt)
        {
            t.Yaw = Mathf.MoveTowardsAngle(t.Yaw, t.TargetYaw, SeatedTurnSpeed * dt);
            Quaternion target = _space.Rotation * Quaternion.Euler(0f, t.Yaw, 0f);
            // Only when it actually turns: rotating every tick would keep a sitter in a parked van from sleeping.
            if (Quaternion.Angle(rb.rotation, target) > 0.05f) rb.MoveRotation(target);
        }

        private float VanYaw(Vector3 world)
        {
            Vector3 l = Quaternion.Inverse(_space.Rotation) * world;
            return l.x * l.x + l.z * l.z > 1e-6f ? Mathf.Atan2(l.x, l.z) * Mathf.Rad2Deg : 0f;
        }

        // ---------- Bookkeeping ----------

        private Tracked Track(GreyboxNpc npc, Rigidbody rb)
        {
            _seen.Add(npc);
            if (_tracked.TryGetValue(npc, out Tracked t) && t.State == npc.State) return t;
            if (t == null)
            {
                t = new Tracked();
                _tracked[npc] = t;
            }
            // New here, or its state changed from outside (hit, woke up, sat up): start over from its current facing.
            npc.CrawlToward = false;
            t.State = npc.State;
            t.RestFor = 0f;
            t.Door = -1;
            t.Running = false;
            t.Yaw = t.TargetYaw = VanYaw(rb.rotation * Vector3.forward);
            if (npc.State == NpcState.Escaping)
            {
                npc.CancelEscape(); // an escape nobody here started
                t.State = npc.State;
            }
            return t;
        }

        private void Forget(GreyboxNpc npc)
        {
            if (npc != null) npc.CrawlToward = false;
            _tracked.Remove(npc);
            _seen.Remove(npc);
        }

        private void Prune()
        {
            _drop.Clear();
            foreach (GreyboxNpc npc in _tracked.Keys)
                if (!_seen.Contains(npc)) _drop.Add(npc);
            foreach (GreyboxNpc npc in _drop)
                Forget(npc);
        }

        // ---------- Teleports, flips, the sea ----------

        // True = everyone was ejected this tick (nothing else to do).
        private bool CheckMovedOrEjected(float dt, float now)
        {
            Vector3 pos = _vanBody.position;
            Quaternion rot = _vanBody.rotation;
            // A reset (R lifts the van only 1.2 m and rights it) counts however short the jump; a long jump counts too.
            int resets = _van != null ? _van.ResetCount : 0;
            bool moved = _hasLastPose &&
                         (resets != _lastResetCount || (pos - _lastVanPos).sqrMagnitude > TeleportJump * TeleportJump);
            Vector3 lastPos = _lastVanPos;
            Quaternion lastRot = _lastVanRot;
            _lastVanPos = pos;
            _lastVanRot = rot;
            _lastResetCount = resets;
            _hasLastPose = true;

            if (moved)
            {
                // The sea return just put the van on land: everyone out, next to it. Any other teleport: they come along.
                if (_seaPending)
                {
                    _seaPending = false;
                    EjectAll(true);
                    return true;
                }
                CarryAlong(lastPos, lastRot, pos, rot);
            }

            if (SeaReturnZone.InSea(pos))
            {
                // Give the van's SeaReturnTracker a moment to move it out; without one, eject them here.
                if (!_seaPending)
                {
                    _seaPending = true;
                    _seaEjectAt = now + 0.25f;
                }
                else if (now >= _seaEjectAt)
                {
                    _seaPending = false;
                    EjectAll(true);
                    return true;
                }
            }
            else if (!moved)
            {
                _seaPending = false;
            }

            _flippedFor = _space.Upright ? 0f : _flippedFor + dt;
            if (_flippedFor >= EjectAfterFlip)
            {
                EjectAll(false);
                return true;
            }
            return false;
        }

        // The van jumped (teleport): move the loaded NPCs and a riding player by the same move.
        private void CarryAlong(Vector3 fromPos, Quaternion fromRot, Vector3 toPos, Quaternion toRot)
        {
            Quaternion turn = toRot * Quaternion.Inverse(fromRot);
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !Ours(npc) || npc.Body == null || !npc.Body.Active) continue;
                Rigidbody rb = npc.Body.Rigidbody;
                Vector3 p = toPos + turn * (rb.position - fromPos);
                Quaternion r = turn * rb.rotation;
                rb.position = p;
                rb.rotation = r;
                npc.transform.SetPositionAndRotation(p, r);
                rb.linearVelocity = _vanBody.linearVelocity;
                rb.angularVelocity = Vector3.zero;
            }
            if (RidingPawn() is GreyboxPawn pawn)
                pawn.Teleport(toPos + turn * (pawn.Position - fromPos), pawn.Body.eulerAngles.y + turn.eulerAngles.y);
        }

        // Everyone in the bay outside: next to the sliding door with the van upright, behind it when tipped over (the side
        // door may face the ground or the sky then).
        private void EjectAll(bool upright)
        {
            Vector3 basePoint = upright ? DoorOutside[SlideDoor] : DoorOutside[RearDoors];
            Vector3 along = upright ? Vector3.back : Vector3.right;
            Vector3 flatForward = Flat(_space.Rotation * Vector3.forward);
            if (flatForward.sqrMagnitude < 1e-4f) flatForward = Vector3.forward;
            flatForward.Normalize();
            int slot = 0;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || npc.Body == null || !npc.Body.Active) continue;
                bool inside = Ours(npc) || (!npc.InCargo && npc.State == NpcState.Down && _space.Contains(npc.Center));
                if (!inside) continue;
                Vector3 p = GroundBelow(_space.ToWorld(basePoint + along * (0.8f * Spread(slot++))));
                Place(npc, p, flatForward);
            }
            if (RidingPawn() is GreyboxPawn pawn)
            {
                Vector3 p = GroundBelow(_space.ToWorld(basePoint + along * (0.8f * Spread(slot))));
                pawn.Teleport(p + Vector3.up * 0.05f, Quaternion.LookRotation(flatForward).eulerAngles.y);
            }
        }

        // 0, +1, -1, +2, -2, ...
        private static float Spread(int i) => i == 0 ? 0f : ((i + 1) / 2) * (i % 2 == 1 ? 1f : -1f);

        private void Place(GreyboxNpc npc, Vector3 ground, Vector3 flatForward)
        {
            Forget(npc);
            GreyboxNpcBody body = npc.Body;
            Rigidbody rb = body.Rigidbody;
            if (npc.State == NpcState.Down)
            {
                // Lying along the van, centre one radius above the ground.
                Quaternion r = Quaternion.FromToRotation(Vector3.up, flatForward);
                Vector3 root = ground + Vector3.up * (body.Radius + 0.05f) - flatForward * (body.Height * 0.5f);
                rb.position = root;
                rb.rotation = r;
                npc.transform.SetPositionAndRotation(root, r);
                rb.linearVelocity = Vector3.zero;
                rb.angularVelocity = Vector3.zero;
                npc.InCargo = false;
                npc.Carrier = null;
                return;
            }
            // Sitting or escaping: put the body there, then it gets up (StandUp finds the ground under it) and runs.
            Vector3 seat = ground + Vector3.up * 0.05f;
            rb.position = seat;
            npc.transform.position = seat;
            npc.LeaveCargo(false, Vector3.zero);
        }

        // The on-foot pawn, if it rides in this bay (KCC player with GreyboxCargoRider).
        private GreyboxPawn RidingPawn()
        {
            GreyboxPawn pawn = _seat != null ? _seat.Pawn : null;
            if (pawn == null || !pawn.Controlled || !pawn.Body.TryGetComponent(out GreyboxCargoRider rider)) return null;
            return rider.Carrier == _space ? pawn : null;
        }

        // Highest ground under p, ignoring the van, the pawn and NPCs, and anything more than EjectStepUp above the van or
        // p (an awning, a bus-stop roof, a branch over the road on the look map).
        private const float EjectStepUp = 1.5f;

        private Vector3 GroundBelow(Vector3 p)
        {
            float top = Mathf.Max(p.y, transform.position.y) + 3f;
            float highest = top - 3f + EjectStepUp;
            float ground = float.NegativeInfinity;
            foreach (RaycastHit hit in Physics.RaycastAll(new Vector3(p.x, top, p.z), Vector3.down, top - p.y + 20f, ~0, QueryTriggerInteraction.Ignore))
            {
                Transform t = hit.collider.transform;
                if (hit.point.y > highest || t.IsChildOf(transform) || hit.collider.GetComponentInParent<GreyboxNpc>() != null) continue;
                if (_seat != null && _seat.Pawn != null && (t.IsChildOf(_seat.Pawn.transform) || t.IsChildOf(_seat.Pawn.Body))) continue;
                ground = Mathf.Max(ground, hit.point.y);
            }
            if (!float.IsNegativeInfinity(ground)) p.y = ground;
            return p;
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        // ---------- HUD ----------

        // NPCs loaded in this bay, and how many of them are stunned (lying).
        private void Count(out int total, out int stunned)
        {
            total = stunned = 0;
            if (_space == null && !TryGetComponent(out _space)) return;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !Ours(npc)) continue;
                total++;
                if (npc.State == NpcState.Down) stunned++;
            }
        }

        private void OnGUI()
        {
            GreyboxPawn pawn = _seat != null ? _seat.Pawn : null;
            bool near = pawn != null && pawn.Controlled && Vector3.Distance(pawn.Position, transform.position) <= HudRadius;
            if ((_seat == null || !_seat.Driving) && !near) return;
            Count(out int total, out int stunned);
            string text = $"Груз: {total} (оглушены {stunned})";
            if (total > SoftLimit) text += " — тесно";
            GUI.Label(new Rect(330f, 12f, 320f, 24f), text);
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.color = Color.cyan;
            foreach (Vector3 p in DoorOutside)
                Gizmos.DrawWireSphere(p, 0.15f);
            Gizmos.color = Color.magenta;
            for (int i = 0; i < Doorway.Length; i++)
                Gizmos.DrawLine(Doorway[i], Doorway[i] + DoorwayNormal[i] * 0.5f);
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(HandlePoint, 0.08f);
        }
    }
}
