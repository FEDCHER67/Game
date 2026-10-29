using OnlyVolunteers.Capture;
using OnlyVolunteers.Network;
using OnlyVolunteers.Session;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// PLAYER HANDS v01 (Fedya 30.10): visible, stretchy sausage arms. Added by NetworkPlayer.Awake to every player
    /// (the map pawn and the network prefab); presentation only.
    ///
    /// Local player: his own first-person arms (camera-relative: sway, walk bob, breathing; skin tone and the chosen top's
    /// sleeves) plus a shadows-only copy of his full sausage, so he never sees inside his own head. Fedya 30.10: no idle
    /// hands in first person: the right hand shows only while it holds a one-hand item, both only for a two-hand hold, the
    /// swinging arm for a Q punch (FirstPersonHandsRuleV01); an arm with nothing to do parks out of view and the arms are
    /// not drawn at all once both are parked. The viewmodel sits 25% farther and lower than v01. Remote player (a friend's view): the full dressed sausage on that player's motor, walking/idle clips, the
    /// same arm IK on top. Both rigs reach for the same world grip points (PlayerArmsIntentV01 reads what is held) and
    /// stretch, wobble, sag with heft and snap back with overshoot (ArmStretchMath, ArmChannelV01, StretchArmRigV01).
    ///
    /// Network: the owner sends ArmsStateV01 through NetworkPlayer.SubmitArms (reliable on a change of hands/pose and as
    /// a keyframe, unreliable stream in between, at most SendRate per second); remote copies draw NetworkPlayer.RemoteArms.
    ///
    /// Punch (Q, Fedya 30.10): the existing hit path (GreyboxInteractor) calls <see cref="LocalPunch"/> once per accepted
    /// swing with the authoritative result (landed or not, where, how strong). That one call plays the swing on the
    /// first-person arm and the shadow body, schedules the cartoon stars at the fist's contact (landed only) and sends one
    /// PunchCueV01 through NetworkPlayer.SubmitPunch; friends play the same swing on the remote body and burst their own
    /// stars once per cue sequence (PunchLedgerV01). Nothing here hits, stuns or decides anything.
    ///
    /// Never touched: reach, hold points, capsule, carry physics, authority. No colliders: nothing here pushes anyone.
    /// </summary>
    [DefaultExecutionOrder(250)] // after the KCC camera (KccFirstPersonInput.LateUpdate) and the body clips
    [DisallowMultipleComponent]
    public sealed class PlayerArmsV01 : MonoBehaviour
    {
        // ---- dev switches (editor/dev checks, screenshots) ----
        /// <summary>Hides the first-person arms (for an outside screenshot).</summary>
        public static bool DebugHideFirstPerson;
        /// <summary>Local player: also draws a "friend's view" sausage fed through the wire round trip (Pack → Unpack →
        /// the remote code path), at the motor + DebugEchoOffset, and hides the own shadow body meanwhile.</summary>
        public static bool DebugEcho;
        public static Vector3 DebugEchoOffset;

        public enum Role { None, Local, Remote }

        /// <summary>The local player's arms (null when there is none).</summary>
        public static PlayerArmsV01 Local { get; private set; }

        public Role Current { get; private set; }
        public ArmsIntentV01 Intent { get; private set; } = ArmsIntentV01.Idle;
        /// <summary>Local: the state built (and sent) this frame. Remote: the state drawn.</summary>
        public ArmsStateV01 State { get; private set; } = ArmsStateV01.Idle;
        public SausageArmsBodyV01 FirstPerson => view;
        public SausageArmsBodyV01 Body => body;
        public SausageArmsBodyV01 Echo => echo;
        public int SentReliable { get; private set; }
        public int SentStream { get; private set; }

        private NetworkPlayer player;
        private PlayerArmsTuningV01 tuning;
        private PlayerArmsIntentV01 intentReader;
        private SausageArmsBodyV01 body, view, echo;
        private Transform anchor, motor;
        private Camera viewCamera;
        private PlayerAppearance look;
        private bool warned;

        // first-person motion
        private Vector3 sway, swayVelocity;
        private Vector2 lastLook;
        private bool hasLook;
        private float bobPhase, bobWeight, retract;
        private Vector3 lastCameraPosition;

        // network
        private ArmsStateV01 lastSent = ArmsStateV01.Idle;
        private bool sentAny;
        private float nextStream, lastKey = -999f;

        // punch (Q): the local cue being played (Time.time it began) and the last remote cue
        private PunchCueV01 punch, remotePunch;
        private float punchStart = -999f, remotePunchStart = -999f;
        private ushort punchSequence;
        private readonly PunchLedgerV01 punchLedger = new PunchLedgerV01();
        private float fpVisibleUntil = -999f;

        // hidden stand-ins (restored on teardown)
        private Renderer[] hiddenPlaceholders;
        private Renderer hiddenCapsule;

        private static readonly int WallMask = ~((1 << 2) | (1 << 5) | (1 << 8) | (1 << 9) | (1 << 11) | (1 << 12) | (1 << 13) | (1 << 14));

        private void Awake() => player = GetComponent<NetworkPlayer>();

        private void OnDestroy()
        {
            Teardown();
        }

        private Role Decide()
        {
            if (player == null || SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null) return Role.None;
            if (player.IsClientInitialized) return player.IsOwner ? Role.Local : Role.Remote;
            return player.ExternalControl ? Role.Local : Role.None; // the map pawn, before (or without) the solo host
        }

        private void LateUpdate()
        {
            Role want = Decide();
            if (want != Current)
            {
                Teardown();
                Current = want;
                if (want != Role.None) Build();
            }
            if (Current == Role.Local) TickLocal(Time.deltaTime);
            else if (Current == Role.Remote) TickRemote(Time.deltaTime);
        }

        // ---------------- build / teardown ----------------

        private void Build()
        {
            tuning = PlayerArmsTuningV01.Load();
            if (tuning.BodyPrefab == null)
            {
                if (!warned) Debug.LogWarning("[OV Hands] Resources/PlayerArmsTuningV01 has no body prefab: no visible arms");
                warned = true;
                return;
            }
            motor = player.PlayerCollider != null ? player.PlayerCollider.transform : transform;
            int layer = motor.gameObject.layer;
            if (Current == Role.Local)
            {
                intentReader = new PlayerArmsIntentV01(player);
                body = SausageArmsBodyV01.Create(tuning.BodyPrefab, motor, SausageArmsBodyV01.Kind.ThirdPersonShadow, "[Hands] Body (shadow only)", layer, tuning.Matte);
                viewCamera = player.ViewCamera;
                if (viewCamera != null)
                {
                    anchor = new GameObject("[Hands] First-person anchor").transform;
                    anchor.SetParent(viewCamera.transform, false);
                    view = SausageArmsBodyV01.Create(tuning.BodyPrefab, anchor, SausageArmsBodyV01.Kind.FirstPerson, "[Hands] First-person arms", layer, tuning.Matte);
                    if (view != null)
                    {
                        view.Transform.localScale = Vector3.one * tuning.FpScale;
                        view.Transform.localPosition = tuning.FpShoulders - view.ShoulderMid * tuning.FpScale;
                    }
                }
                // The KCC prefab's shadows-only capsule: the sausage's shadow replaces it.
                var capsule = motor.Find("Root/Meshes/Capsule");
                if (body != null && capsule != null && capsule.TryGetComponent(out Renderer r) && r.enabled &&
                    r.shadowCastingMode == ShadowCastingMode.ShadowsOnly)
                { r.enabled = false; hiddenCapsule = r; }
                look = AppearanceProfileV01.Load();
                AppearanceProfileV01.Changed += OnLocalLook;
                Local = this;
            }
            else
            {
                body = SausageArmsBodyV01.Create(tuning.BodyPrefab, motor, SausageArmsBodyV01.Kind.ThirdPersonVisible, "[Hands] Body", layer, tuning.Matte);
                if (body != null && player.RemoteVisualRoot != null)
                {
                    hiddenPlaceholders = player.RemoteVisualRoot.GetComponentsInChildren<Renderer>(true);
                    foreach (var p in hiddenPlaceholders) if (p != null) p.enabled = false;
                }
                look = player.Appearance;
                player.AppearanceChanged += OnRemoteLook;
                player.PunchReceived += OnRemotePunch;
            }
            Dress();
            Debug.Log($"[OV Hands] {Current} arms for player {player.OwnerId}: body={(body != null)}, firstPerson={(view != null)}, " +
                      $"stretch renderers={(body != null ? body.Rig.PatchedRenderers : 0)}");
        }

        private void Teardown()
        {
            AppearanceProfileV01.Changed -= OnLocalLook;
            if (player != null) { player.AppearanceChanged -= OnRemoteLook; player.PunchReceived -= OnRemotePunch; }
            body?.Destroy(); view?.Destroy(); echo?.Destroy();
            body = view = echo = null;
            if (anchor != null) Destroy(anchor.gameObject);
            anchor = null;
            if (hiddenCapsule != null) hiddenCapsule.enabled = true;
            hiddenCapsule = null;
            if (hiddenPlaceholders != null) foreach (var p in hiddenPlaceholders) if (p != null) p.enabled = true;
            hiddenPlaceholders = null;
            if (Local == this) Local = null;
            sentAny = false;
            hasLook = false;
            punchStart = remotePunchStart = -999f;
            punchLedger.Reset();
        }

        private void OnLocalLook(PlayerAppearance a) { look = a; Dress(); }
        private void OnRemoteLook(NetworkPlayer p) { look = p.Appearance; Dress(); }

        private void Dress()
        {
            if (look == null) return;
            body?.Dress(look); view?.Dress(look); echo?.Dress(look);
        }

        // ---------------- local ----------------

        private void TickLocal(float dt)
        {
            if (body == null && view == null) return;
            if (viewCamera == null) viewCamera = player.ViewCamera;
            var intent = intentReader != null ? intentReader.Read(viewCamera) : ArmsIntentV01.Idle;
            Intent = intent;
            if (viewCamera != null) PunchStarsV01.View = viewCamera;
            float punchT = DebugPunchFreeze >= 0f && Time.time - punchStart < 30f ? DebugPunchFreeze : Time.time - punchStart;
            if (!ArmPunchV01.Active(punchT)) punchT = -1f;
            if (view != null) TickFirstPerson(view, intent, punchT, dt);
            Vector3 feet = motor.position;
            float yaw = viewCamera != null ? viewCamera.transform.eulerAngles.y : motor.eulerAngles.y;
            float pitch = viewCamera != null ? Mathf.DeltaAngle(0f, viewCamera.transform.eulerAngles.x) : 0f;
            Quaternion facing = Quaternion.Euler(0f, yaw, 0f);
            if (body != null) TickBody(body, feet, facing, pitch, intent, punchT, punch, dt);
            var state = BuildState(intent, feet, body);
            State = state;
            Send(state);
            TickEcho(state, feet, facing, pitch, punchT, dt);
        }

        private ArmsStateV01 BuildState(in ArmsIntentV01 intent, Vector3 feet, SausageArmsBodyV01 b)
        {
            var s = new ArmsStateV01
            {
                Right = intent.Right.Active,
                Left = intent.Left.Active,
                TwoHanded = intent.TwoHanded && intent.Right.Active && intent.Left.Active,
                Pose = intent.Any ? intent.Pose : ArmsPoseV01.Idle,
                Heft = intent.Any ? intent.Heft : 0f,
                StretchRight = b != null ? b.StretchShown[0] : 1f,
                StretchLeft = b != null ? b.StretchShown[1] : 1f,
                RightOffset = intent.Right.Active ? intent.Right.Grip - feet : Vector3.zero,
                LeftOffset = intent.Left.Active ? intent.Left.Grip - feet : Vector3.zero,
            };
            return s;
        }

        private void Send(in ArmsStateV01 state)
        {
            if (!player.IsSpawned || !player.IsOwner) return;
            float now = Time.unscaledTime;
            bool shape = !sentAny || !state.SameShape(lastSent);
            if (shape || (state.AnyHand && now - lastKey >= Mathf.Max(0.2f, tuning.KeyframeInterval)))
            {
                player.SubmitArms(state, true);
                SentReliable++;
                lastSent = state; sentAny = true; lastKey = now;
                nextStream = now + 1f / Mathf.Max(1f, tuning.SendRate);
                return;
            }
            if (state.AnyHand && now >= nextStream && !state.Approximately(lastSent))
            {
                player.SubmitArms(state, false);
                SentStream++;
                lastSent = state;
                nextStream = now + 1f / Mathf.Max(1f, tuning.SendRate);
            }
        }

        private void TickEcho(in ArmsStateV01 state, Vector3 feet, Quaternion facing, float pitch, float punchT, float dt)
        {
            if (!DebugEcho)
            {
                if (echo != null)
                {
                    echo.Destroy(); echo = null;
                    body?.SetVisible(true);
                }
                return;
            }
            if (echo == null)
            {
                echo = SausageArmsBodyV01.Create(tuning.BodyPrefab, motor, SausageArmsBodyV01.Kind.ThirdPersonVisible, "[Hands] Echo (friend's view)", motor.gameObject.layer, tuning.Matte);
                if (echo == null) return;
                if (look != null) echo.Dress(look);
                body?.SetVisible(false); // one shadow, one body: the echo stands where the own (shadow) body is
            }
            ArmsWireV01.Pack(state, out ulong a, out ulong b);
            var received = ArmsWireV01.Unpack(a, b);
            Vector3 at = feet + DebugEchoOffset;
            // the echo plays the local punch as a friend gets it (the cue's offset from the feet); no second stars
            TickBody(echo, at, facing, pitch, FromState(received, at), punchT, punch, dt);
        }

        // ---------------- remote ----------------

        private void TickRemote(float dt)
        {
            if (body == null) return;
            var state = player.RemoteArms;
            State = state;
            Vector3 feet = motor.position;
            Quaternion facing = player.RemoteVisualRoot != null ? player.RemoteVisualRoot.rotation
                : Quaternion.Euler(0f, motor.eulerAngles.y, 0f);
            var intent = FromState(state, feet);
            Intent = intent;
            float punchT = Time.time - remotePunchStart;
            if (!ArmPunchV01.Active(punchT)) punchT = -1f;
            TickBody(body, feet, facing, player.RemotePitch, intent, punchT, remotePunch, dt);
        }

        // ---------------- punch (Q) ----------------

        /// <summary>The existing Q hit path, once per swing it accepted (after its cooldown): plays the swing on the local
        /// player's arms, bursts the stars at the contact when the hit <paramref name="landed"/> (never for a miss) and
        /// sends the one cue to friends. <paramref name="target"/>: the hit point, or where the swing ends for a miss.
        /// <paramref name="strength"/> 0..1: the share of a full stun the contact gave (fewer, smaller stars when weak).
        /// Presentation only; returns the cue's sequence (0 when there is no local player).</summary>
        public static ushort LocalPunch(bool landed, Vector3 target, float strength)
        {
            var arms = Local;
            var t = arms != null && arms.tuning != null ? arms.tuning : PlayerArmsTuningV01.Load();
            if (landed) PunchStarsV01.Schedule(target, strength, ArmPunchV01.ContactTime, t.StarCount, t.StarSize, t.StarLife);
            return arms != null ? arms.StartLocalPunch(landed, target, strength) : (ushort)0;
        }

        /// <summary>The last local punch cue (review notes, tests).</summary>
        public PunchCueV01 LastPunch => punch;
        /// <summary>Dev (review shots): the local punch is drawn frozen this many seconds after its start; negative = off.</summary>
        public static float DebugPunchFreeze = -1f;

        private ushort StartLocalPunch(bool landed, Vector3 target, float strength)
        {
            int side = FirstPersonHandsRuleV01.PunchSide(Intent.Right.Active, Intent.Left.Active, Intent.TwoHanded);
            punchSequence++;
            if (punchSequence == 0) punchSequence = 1;
            Vector3 feet = motor != null ? motor.position : transform.position;
            punch = new PunchCueV01
            {
                Sequence = punchSequence, Side = (byte)side, Landed = landed, Strength = Mathf.Clamp01(strength),
                Offset = Vector3.ClampMagnitude(target - feet, ArmsWireV01.Range),
            };
            punchStart = Time.time;
            if (view != null) view.PunchKey = -1;
            if (body != null) body.PunchKey = -1;
            if (echo != null) echo.PunchKey = -1;
            if (player != null && player.IsSpawned && player.IsOwner) player.SubmitPunch(punch);
            return punchSequence;
        }

        private void OnRemotePunch(NetworkPlayer from, PunchCueV01 cue)
        {
            if (from != player || Current != Role.Remote || !punchLedger.Accept(cue.Sequence)) return;
            remotePunch = cue;
            remotePunchStart = Time.time;
            if (body != null) body.PunchKey = -1;
            if (cue.Landed && motor != null && tuning != null)
                PunchStarsV01.Schedule(motor.position + cue.Offset, cue.Strength, ArmPunchV01.ContactTime, tuning.StarCount, tuning.StarSize, tuning.StarLife);
        }

        /// <summary>A received arm state as hand goals around this copy's feet.</summary>
        public static ArmsIntentV01 FromState(in ArmsStateV01 s, Vector3 feet) => new ArmsIntentV01
        {
            Right = new HandGoalV01 { Active = s.Right, Grip = feet + s.RightOffset },
            Left = new HandGoalV01 { Active = s.Left, Grip = feet + s.LeftOffset },
            Pose = s.Pose, Heft = s.Heft, TwoHanded = s.TwoHanded, Source = "wire",
        };

        // ---------------- shared solving ----------------

        /// <summary>Finger direction, palm direction and finger curl of a pose. side +1 right, -1 left.</summary>
        public static void PoseFrame(ArmsPoseV01 pose, float side, Vector3 right, Vector3 up, Vector3 forward, Vector3 reach,
            out Vector3 fingers, out Vector3 palm, out float curl)
        {
            switch (pose)
            {
                case ArmsPoseV01.Grab:
                    fingers = Vector3.Lerp(reach, forward, 0.35f); palm = -right * side * 0.85f - up * 0.3f + forward * 0.1f; curl = 0.85f; break;
                case ArmsPoseV01.Carry:
                    fingers = forward * 0.7f - right * side * 0.55f; palm = up; curl = 0.4f; break;
                case ArmsPoseV01.PalmUp:
                    fingers = forward * 0.9f - right * side * 0.2f; palm = up; curl = 0.3f; break;
                case ArmsPoseV01.Tool:
                    fingers = Vector3.Lerp(reach, forward + up * 0.35f, 0.5f); palm = -right * side; curl = 0.95f; break;
                case ArmsPoseV01.Push:
                    fingers = forward; palm = -up + forward * 0.25f; curl = 0.65f; break;
                default:
                    fingers = forward * 0.8f - up * 0.35f - right * side * 0.15f; palm = -right * side * 0.75f - up * 0.45f + forward * 0.2f; curl = 0.25f; break;
            }
        }

        private static Vector3 Mirror(Vector3 v, float side) => new Vector3(v.x * side, v.y, v.z);

        private void TickFirstPerson(SausageArmsBodyV01 fp, in ArmsIntentV01 intent, float punchT, float dt)
        {
            var director = CaptureDirector.Instance;
            bool tableView = director != null && director.Bridge != null && director.Bridge.InTableMode;
            bool allowed = viewCamera != null && viewCamera.isActiveAndEnabled && !DebugHideFirstPerson && !tableView && anchor != null;
            // Fedya 30.10: no idle hands. Right: a one-hand item (or a two-hand hold); left: a two-hand hold only; the
            // swinging arm for its punch. Once nothing is engaged the arms drop out of view and are no longer drawn.
            int punchSide = punchT >= 0f ? punch.Side : -1;
            FirstPersonHandsRuleV01.Engaged(intent.Right.Active, intent.Left.Active, intent.TwoHanded, punchSide,
                out bool engageRight, out bool engageLeft);
            bool engaged = allowed && (engageRight || engageLeft);
            float now = Time.time;
            if (engaged) fpVisibleUntil = now + Mathf.Max(0f, tuning.FpHideAfter);
            bool show = allowed && (engaged || now < fpVisibleUntil);
            fp.SetVisible(show);
            if (!show)
            {
                hasLook = false;
                if (!fp.Parked) Park(fp);
                return;
            }
            fp.Parked = false;
            Transform cam = viewCamera.transform;

            // sway (lag behind the look), bob (walking), breathing
            Vector3 e = cam.eulerAngles;
            var lookNow = new Vector2(e.y, e.x);
            Vector2 lookVelocity = hasLook && dt > 0f
                ? new Vector2(Mathf.DeltaAngle(lastLook.x, lookNow.x), Mathf.DeltaAngle(lastLook.y, lookNow.y)) / dt : Vector2.zero;
            Vector3 moved = hasLook ? cam.position - lastCameraPosition : Vector3.zero;
            moved.y = 0f;
            lastLook = lookNow; lastCameraPosition = cam.position; hasLook = true;
            Vector3 swayGoal = ArmStretchMath.SwayAngles(lookVelocity, tuning.SwayGain, tuning.SwayMax, tuning.SwayRoll);
            Vector3 sv = swayVelocity;
            sway = ArmStretchMath.Spring(sway, ref sv, swayGoal, tuning.SwayHz, tuning.SwayDamping, dt);
            swayVelocity = sv;
            float planar = dt > 0f && moved.magnitude < 2f ? moved.magnitude / dt : 0f;
            bobWeight = Mathf.MoveTowards(bobWeight, Mathf.Clamp01(planar / Mathf.Max(0.1f, tuning.BobReferenceSpeed)), dt * 4f);
            bobPhase = ArmStretchMath.AdvanceBobPhase(bobPhase, planar, tuning.BobCyclesPerMeter, dt);
            Vector3 bob = ArmStretchMath.BobOffset(bobPhase, bobWeight, tuning.BobAmplitude) +
                          Vector3.up * (Mathf.Sin(Time.time * 2f * Mathf.PI * tuning.BreathHz) * tuning.BreathAmplitude);
            anchor.localPosition = bob;
            anchor.localRotation = Quaternion.Euler(sway);

            // a punch reaches less far into a wall right in front
            float retractGoal = UnityEngine.Physics.Raycast(cam.position, cam.forward, out RaycastHit hit, tuning.WallProbe, WallMask, QueryTriggerInteraction.Ignore)
                ? ArmStretchMath.WallRetract(hit.distance, tuning.WallProbe) : 0f;
            retract = Mathf.MoveTowards(retract, retractGoal, dt * 5f);

            var rig = fp.Rig;
            rig.ResetToRest();
            Vector3 right = anchor.right, up = anchor.up, forward = anchor.forward;
            float blend = 1f - Mathf.Exp(-dt * (punchSide >= 0 ? 40f : 16f));
            for (int i = 0; i < 2; i++)
            {
                var side = (StretchArmRigV01.Side)i;
                float sign = i == 0 ? 1f : -1f;
                var goal = intent[i];
                var ch = fp.Channels[i];
                bool holds = (i == 0 ? engageRight : engageLeft) && goal.Active && punchSide != i;
                Vector3 shoulder = rig.ShoulderPosition(side);
                Vector3 grip = holds ? goal.Grip : anchor.TransformPoint(Mirror(tuning.FpPark, sign));
                Vector3 pole = shoulder + anchor.rotation * Mirror(tuning.FpPole, sign);
                if (i == punchSide)
                {
                    PunchFirstPerson(fp, ch, rig, side, sign, shoulder, pole, grip, punchT, blend);
                    continue;
                }
                Vector3 reach = (grip - shoulder).sqrMagnitude > 1e-6f ? (grip - shoulder).normalized : forward;
                PoseFrame(holds ? intent.Pose : ArmsPoseV01.Idle, sign, right, up, forward, reach, out Vector3 fingers, out Vector3 palm, out float curl);
                if (!holds) { fingers = -up * 0.9f + forward * 0.2f; palm = -right * sign; curl = 0.35f; } // hanging, relaxed (out of view)
                Quaternion handGoal = Quaternion.Inverse(anchor.rotation) * ArmStretchMath.HandRotation(fingers, palm);
                fp.HandShown[i] = fp.HandShownSet[i] ? Quaternion.Slerp(fp.HandShown[i], handGoal, blend) : handGoal;
                fp.HandShownSet[i] = true;
                Quaternion hand = anchor.rotation * fp.HandShown[i];
                Vector3 wristGoal = rig.WristForGrip(side, grip, hand);
                ch.TickWrist(anchor.InverseTransformPoint(wristGoal), holds, tuning.Springs, dt);
                Vector3 wrist = anchor.TransformPoint(ch.Wrist);
                StretchFor(ch, rig, side, wrist, holds, intent.Heft, dt);
                rig.Solve(side, wrist, hand, pole, ch.Stretch, 1f);
                rig.Curl(side, curl, 1f);
                fp.StretchShown[i] = ch.Stretch;
            }
            SyncHelpers(fp);
        }

        /// <summary>First person, nothing to do: both wrists snapped to their park points out of the view, so the next use
        /// raises the arm into the frame from below.</summary>
        private void Park(SausageArmsBodyV01 fp)
        {
            for (int i = 0; i < 2; i++)
            {
                fp.Channels[i].Snap(Mirror(tuning.FpPark, i == 0 ? 1f : -1f), 1f);
                fp.StretchShown[i] = 1f;
            }
            fp.Parked = true;
        }

        /// <summary>First-person swing of one arm: from where the wrist was, cocked low at the side, out along the crosshair
        /// (a compact jab, a little rubber stretch at most), a short hold, back home (the parked spot or the grip it holds).</summary>
        private void PunchFirstPerson(SausageArmsBodyV01 fp, ArmChannelV01 ch, StretchArmRigV01 rig, StretchArmRigV01.Side side,
            float sign, Vector3 shoulder, Vector3 pole, Vector3 homeGrip, float punchT, float blend)
        {
            int i = (int)side;
            if (fp.PunchKey != punch.Sequence) { fp.PunchKey = punch.Sequence; fp.PunchFrom = ch.Wrist; }
            Vector3 right = anchor.right, up = anchor.up, forward = anchor.forward;
            // a fist: knuckles forward, palm down and a little inward
            Quaternion handGoal = Quaternion.Inverse(anchor.rotation) *
                                  ArmStretchMath.HandRotation(forward - up * 0.1f, -up * 0.85f - right * sign * 0.45f);
            fp.HandShown[i] = fp.HandShownSet[i] ? Quaternion.Slerp(fp.HandShown[i], handGoal, blend) : handGoal;
            fp.HandShownSet[i] = true;
            Quaternion hand = anchor.rotation * fp.HandShown[i];
            Vector3 strikeLocal = Mirror(tuning.FpPunchStrike, sign);
            strikeLocal.z *= 1f - 0.45f * retract;
            Vector3 cockW = anchor.InverseTransformPoint(rig.WristForGrip(side, anchor.TransformPoint(Mirror(tuning.FpPunchCock, sign)), hand));
            Vector3 strikeW = anchor.InverseTransformPoint(rig.WristForGrip(side, anchor.TransformPoint(strikeLocal), hand));
            Vector3 homeW = anchor.InverseTransformPoint(rig.WristForGrip(side, homeGrip, hand));
            Vector3 start = ArmPunchV01.Phase(punchT) == PunchPhaseV01.Retract ? homeW : fp.PunchFrom;
            Vector3 wristLocal = ArmPunchV01.Blend(punchT, start, cockW, strikeW);
            Vector3 wrist = anchor.TransformPoint(wristLocal);
            float stretch = ArmStretchMath.SoftClamp(
                ArmStretchMath.NeededStretch(Vector3.Distance(wrist, shoulder), rig.RestReach(side), 0f, 0f), tuning.MaxStretch);
            ch.Drive(wristLocal, stretch, 1f);
            rig.Solve(side, wrist, hand, pole, stretch, 1f);
            rig.Curl(side, ArmPunchV01.Curl(punchT), 1f);
            fp.StretchShown[i] = stretch;
        }

        private void TickBody(SausageArmsBodyV01 b, Vector3 feet, Quaternion facing, float pitch, in ArmsIntentV01 intent,
            float punchT, in PunchCueV01 cue, float dt)
        {
            b.Transform.SetPositionAndRotation(feet, facing);
            b.Transform.localScale = Vector3.one * tuning.BodyScale;
            b.TickAnimation(feet, dt, tuning);
            Vector3 right = facing * Vector3.right, up = Vector3.up, forward = facing * Vector3.forward;
            b.Nod(pitch * tuning.HeadPitchShare, right);
            var rig = b.Rig;
            int punchSide = punchT >= 0f ? cue.Side : -1;
            for (int i = 0; i < 2; i++)
            {
                var side = (StretchArmRigV01.Side)i;
                float sign = i == 0 ? 1f : -1f;
                var goal = intent[i];
                var ch = b.Channels[i];
                rig.RestoreLengths(side);
                var arm = rig[side];
                Vector3 shoulder = rig.ShoulderPosition(side);
                Vector3 animatedWrist = arm.Hand.position;
                Quaternion animatedHand = arm.Hand.rotation;
                Quaternion hand = animatedHand;
                Vector3 wristGoal = animatedWrist;
                float curl = 0.25f;
                if (goal.Active)
                {
                    Vector3 reach = (goal.Grip - shoulder).sqrMagnitude > 1e-6f ? (goal.Grip - shoulder).normalized : forward;
                    PoseFrame(intent.Pose, sign, right, up, forward, reach, out Vector3 fingers, out Vector3 palm, out curl);
                    hand = ArmStretchMath.HandRotation(fingers, palm);
                    wristGoal = rig.WristForGrip(side, goal.Grip, hand);
                }
                Vector3 pole = shoulder + facing * Mirror(tuning.TpPole, sign);
                if (i == punchSide)
                {
                    PunchBody(b, ch, rig, side, sign, feet + cue.Offset, cue.Sequence, wristGoal, hand, facing, pole, punchT);
                    continue;
                }
                ch.TickWrist(b.Transform.InverseTransformPoint(wristGoal), goal.Active, tuning.Springs, dt);
                Vector3 wrist = b.Transform.TransformPoint(ch.Wrist);
                StretchFor(ch, rig, side, wrist, goal.Active, intent.Heft, dt);
                float w = ch.Weight;
                float s = Mathf.Lerp(1f, ch.Stretch, w);
                rig.Solve(side, wrist, goal.Active ? hand : animatedHand, pole, s, w);
                if (goal.Active || w > 0f) rig.Curl(side, curl, w);
                b.StretchShown[i] = s;
            }
            SyncHelpers(b);
        }

        /// <summary>Third person (the shadow body, a friend's view): the same swing as an outward jab toward the cue's target,
        /// the arm rubber-stretching up to TpPunchReach of the stretch cap, then back to the clip pose or the grip it holds;
        /// once the swing is over the channel springs back from there (the usual release).</summary>
        private void PunchBody(SausageArmsBodyV01 b, ArmChannelV01 ch, StretchArmRigV01 rig, StretchArmRigV01.Side side, float sign,
            Vector3 target, ushort sequence, Vector3 homeWrist, Quaternion homeHand, Quaternion facing, Vector3 pole, float punchT)
        {
            int i = (int)side;
            Vector3 right = facing * Vector3.right, forward = facing * Vector3.forward, up = Vector3.up;
            Vector3 shoulder = rig.ShoulderPosition(side);
            if (b.PunchKey != sequence) { b.PunchKey = sequence; b.PunchFrom = ch.Initialised ? ch.Wrist : b.Transform.InverseTransformPoint(homeWrist); }
            Vector3 toTarget = target - shoulder;
            float distance = toTarget.magnitude;
            Vector3 dir = distance > 1e-4f ? toTarget / distance : forward;
            float reach = rig.RestReach(side);
            float strikeLength = Mathf.Clamp(distance, reach * 0.8f, reach * Mathf.Max(1f, tuning.MaxStretch * tuning.TpPunchReach));
            Quaternion fist = ArmStretchMath.HandRotation(dir, -up * 0.85f - right * sign * 0.45f);
            Vector3 strikeW = rig.WristForGrip(side, shoulder + dir * strikeLength, fist);
            Vector3 cockW = rig.WristForGrip(side, shoulder + forward * 0.1f - up * 0.16f + right * (sign * 0.06f), fist);
            Vector3 start = ArmPunchV01.Phase(punchT) == PunchPhaseV01.Retract ? b.Transform.InverseTransformPoint(homeWrist) : b.PunchFrom;
            Vector3 wristLocal = ArmPunchV01.Blend(punchT, start, b.Transform.InverseTransformPoint(cockW), b.Transform.InverseTransformPoint(strikeW));
            Vector3 wrist = b.Transform.TransformPoint(wristLocal);
            float stretch = Mathf.Clamp(Vector3.Distance(wrist, shoulder) / (reach * 0.97f), 1f, Mathf.Max(1f, tuning.MaxStretch));
            ch.Drive(wristLocal, stretch, 1f);
            float home = Mathf.Clamp01((punchT - ArmPunchV01.ContactTime - ArmPunchV01.Contact) / ArmPunchV01.Retract);
            rig.Solve(side, wrist, Quaternion.Slerp(fist, homeHand, home), pole, stretch, 1f);
            rig.Curl(side, ArmPunchV01.Curl(punchT), 1f);
            b.StretchShown[i] = stretch;
        }

        /// <summary>Holding: the arm grows to the reach it needs (heft makes it sag). Let go: it springs straight back to its
        /// own length, faster than the hand flies home, so the hand rides the retracting arm and the arm squashes a little
        /// past rest (the comic snap-back) before it settles.</summary>
        private void StretchFor(ArmChannelV01 ch, StretchArmRigV01 rig, StretchArmRigV01.Side side, Vector3 wrist, bool holding, float heft, float dt)
        {
            float need = 1f, cap = tuning.MaxStretch;
            if (holding)
            {
                float reach = rig.RestReach(side);
                float distance = Vector3.Distance(wrist, rig.ShoulderPosition(side));
                need = ArmStretchMath.SoftClamp(ArmStretchMath.NeededStretch(distance, reach, heft, tuning.SagPerHeft, tuning.Comfort), tuning.MaxStretch);
                if (tuning.KeepGripBeyondCap && reach > 1e-4f)
                {
                    // the opt-in contact mode: straight to the grip, never longer than the wire can carry
                    float touch = Mathf.Min(distance / (reach * 0.995f), ArmsWireV01.StretchMax);
                    need = Mathf.Max(need, touch);
                    cap = Mathf.Max(cap, touch);
                }
            }
            ch.TickStretch(need, cap, tuning.Springs, dt);
        }

        private void SyncHelpers(SausageArmsBodyV01 b)
        {
            float r = b.StretchShown[0], l = b.StretchShown[1];
            b.Rig.SyncHelpers(r, ArmStretchMath.Thickness(r, tuning.MinThickness), l, ArmStretchMath.Thickness(l, tuning.MinThickness));
        }
    }
}
