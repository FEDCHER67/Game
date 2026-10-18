using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // GettingUp (stage 9): a ragdoll whose stun is over, settling and then playing its get-up clip (NpcGetUp); not
    // grabbable, not free yet (crowd walkers, police and the cargo bay leave it alone).
    public enum NpcState : byte { Free, Down, CargoSeated, Escaping, GettingUp }

    // How a downed NPC is doing. Out: the first 40% of the stun, eyes shut, limp. Groggy: the rest, scared, kicks and
    // crawls. Awake: conscious but caught (sitting in the van, escaping). None: free.
    public enum StunPhase : byte { None, Out, Groggy, Awake }

    // What a bystander can see happen to an NPC (GreyboxNpc.Incident): knocked down from its feet, or loaded into a van.
    public enum NpcIncident : byte { Stunned, Captured }

    // Grey-box crowd NPC (Sausage Buddy), NPC capture stage 1 (canon section 151, draft docs/drafts/NPC_CAPTURE_VAN_COOP_DRAFT.md).
    // Free: idles and blinks, runs away from the van or the on-foot pawn (CharacterController, ignores the van; a fast
    // van still knocks it over by script).
    // Down: a hit (Hit: weapon + zone) or a van knock (KnockOver) turns it into one physics body with grab points
    // (GreyboxNpcBody); players drag it with LMB and push it into the van by hand, there is no carry or load key.
    // The stun timer ALWAYS runs, also while held or carried (Fedya, 2026-10-04): a stunned, not killed, NPC comes round.
    // Out (first OutShare, 60%): limp. Groggy (the rest): kicks every 1.0-1.8 s (a kick can tear it out of someone's
    // hands: one in five with one holder, one in twenty with two, never with three) and crawls away from the pawn when
    // nobody holds it. (Third playtest, 2026-10-06: was 50%, 0.8-1.5 s, 0.35 / 0.15: a solo load lost its grip every
    // ~3 s of Groggy, which read as "heavy".)
    // At 0 it wakes: every hold is revoked; inside a cargo bay it sits up there (CargoSeated), elsewhere it stands up and
    // runs. A hard impact (>5.5 m/s, e.g. a drop from over 1.5 m; letting go of a chest-high carry is not one) wakes it
    // early and costs Condition, as does being dragged fast by the ankles only. Condition never kills (canon section 26),
    // it only goes down.
    // CargoSeated / Escaping: entered here, driven by GreyboxVanCargo (loading, van matching and escapes, chunk 3).
    // Stage 9 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md): a free NPC goes down either as the stage-1 capsule or, when
    // F10 says so and fewer than NpcRagdoll.Cap are simulated, as the 11-body ragdoll (Characters/Npc/NpcRagdoll, added
    // here at runtime). Both are driven through INpcBody (PhysicalBody; GreyboxVanCargo loads both the same way). Sitting
    // and escaping NPCs are the capsule; going down from there (a hit in the bay, the tumble out of a fast van) makes them
    // the ragdoll again: lying along the bay where they sat, or from their standing pose outside it.
    // Stage 9 step 3: a ragdoll that wakes outside a van gets up with a clip (GettingUp, Characters/Npc/NpcGetUp: settle,
    // GetUp_Back or GetUp_Belly, the CharacterController on at the clip's Stable point, then free and fleeing); one that
    // wakes in a cargo bay sits up there (SitUp_Cargo, then the controller loops Cargo_Sit_Idle) on the seated capsule.
    // Sitting NPCs play the sit clips (the visual turned SeatYaw and moved SeatOffset so the figure faces the capsule's
    // forward and sits on it) and knock on the wall now and then (Cargo_Knock) while the van is slow; escaping NPCs keep the
    // stage-1 look (the standing Run sunk by SeatedVisualDrop). Rigs without the clips keep the old visuals.
    // Stage 9 step 4 (design §4.3, §4.5, §4.6): a Groggy ragdoll struggles on its joint drives (Characters/Npc/NpcStruggle,
    // ticked from FixedDown): it paws and kicks lying, crawls away (or to an open cargo door) instead of the capsule's hops,
    // and wriggles while held; a kick starts the leg's motors and keeps the KickTearChance roll. A passenger leaving a
    // standing van (below EscapeTumbleKmh; faster it tumbles as before) hops out of the door onto the ground (JumpOut,
    // NpcGetUp) instead of appearing there, then runs; the clips Escape_Scramble / Cargo_JumpOut replace the sunk run and the
    // procedural hop as soon as clips.json installs them. Stumble: a trip through the ragdoll (the fat police officer's),
    // not stunned and not grabbable, then the get-up clip and on as before (Stumbling, no scream, no flight).
    // Stage 9 step 5 (design §5.4): the Animator is NpcAnimDriver's (added here at runtime): it reads this NPC's state each
    // frame and writes the contract's parameters; this script only tells it how fast it moves the NPC itself (fleeing, the
    // escape run) and asks for the knock on the van wall and, on a capsule (whose Animator stays on), a hit react.
    // State is public plain data (State, Phase, StunLeft, StunTotal, InCargo, Carrier, Condition) for a network version later.
    [RequireComponent(typeof(CharacterController))]
    public sealed class GreyboxNpc : MonoBehaviour
    {
        [Header("Crowd")]
        public float WalkerScareRadius = 7f;
        public float VanScareRadius = 14f;
        public float FleeSpeed = 4.5f;
        public float CalmAfter = 4f;
        public float KnockSpeedKmh = 15f;

        [Header("Down")]
        [Tooltip("N·s at the hit point: a standing NPC topples, a lying one jolts.")]
        public float HitImpulse = 60f;
        [Tooltip("Condition a hit costs when the NPC is already down, sitting in the van or escaping: re-stunning works " +
                 "but is not free (draft section 2, canon sections 24-25).")]
        public float ReStunConditionCost = 5f;
        [Tooltip("Share of the stun spent Out (eyes shut, limp); the rest is Groggy.")]
        [Range(0f, 1f)] public float OutShare = 0.6f;
        public Vector2 KickInterval = new(1.0f, 1.8f);
        [Tooltip("N·s at an ankle.")]
        public float KickImpulse = 25f;
        [Tooltip("Chance that a kick tears one hold loose, by the number of holders (0, 1, 2, 3).")]
        public float[] KickTearChance = { 0f, 0.2f, 0.05f, 0f };
        [Tooltip("Average crawl push in N while Groggy and nobody holds it, given as hops every CrawlPeriod seconds.")]
        public float CrawlForce = 80f;
        public float CrawlPeriod = 0.6f;
        [Tooltip("m/s up per crawl hop, so ground friction lets go for a moment.")]
        public float CrawlHop = 0.6f;
        [Tooltip("Average crawl push in N while crawling for an open cargo door (GreyboxVanCargo sets CrawlToward).")]
        public float EscapeCrawlForce = 120f;
        [Tooltip("Impact speed (m/s along the contact normal) that wakes it early and costs Condition: 5.5 is a drop from ~1.5 m.")]
        public float ImpactWakeSpeed = 5.5f;
        public float ImpactConditionCost = 5f;
        [Tooltip("Seconds of stun left after a hard impact (at most).")]
        public float EarlyWakeLeft = 1f;
        [Tooltip("Seconds after a hit or knock in which its own fall does not count as an impact.")]
        public float ImpactGrace = 1.5f;
        public float AnkleDragSpeed = 1.5f;
        [Tooltip("Condition per second while dragged by the ankles only, faster than AnkleDragSpeed.")]
        public float AnkleDragCost = 1f;
        [Tooltip("Before 2026-10-11 only (LegacyVanKnock): seconds the knocked body ignored all of the van's colliders.")]
        public float VanKnockIgnore = 0.5f;
        [Tooltip("A vehicle knocks it over (Fedya's playtest 2026-10-11): the body takes the vehicle's velocity at it times " +
                 "KnockAhead plus KnockLift m/s up. Over 1, the parts born inside the bumper leave it forward; at 0.9 the van " +
                 "drove into the thrown body and it ended up stuck in the windshield, the roof or a door.")]
        public float KnockAhead = 1.1f;
        public float KnockLift = 5f;
        /// <summary>Test hook (RagdollSmokeTest's before rows): the van's knock as before 2026-10-11: looked for once per
        /// rendered frame, 0.9 of the van's velocity plus 5 m/s up, all of the van ignored for VanKnockIgnore s.</summary>
        public static bool LegacyVanKnock;
        [Tooltip("A sitting or escaping NPC this far outside its cargo box with nothing else taking it out of the van " +
                 "(no GreyboxVanCargo, the van gone) gets up and runs.")]
        public float LostCarrierMargin = 1f;
        [Tooltip("The standing Buddy mesh is lowered this much while escaping in the cargo bay (and sitting there on rigs " +
                 "without the sit clips); hit zones of a sitter are counted as on the standing body this much higher.")]
        public float SeatedVisualDrop = 0.4f;

        [Header("Voice (optional, Sfx)")]
        [Tooltip("Seconds: the least time between two screams of this NPC (it screams when it starts running away).")]
        public float ScreamCooldown = 6f;
        [Tooltip("Seconds between gibberish mumbles while groggy.")]
        public Vector2 MumbleInterval = new(2.5f, 5f);
        [Tooltip("Seconds between whimpers while sitting in the cargo bay.")]
        public Vector2 WhimperInterval = new(4f, 9f);

        [Header("State (plain data)")]
        public NpcState State;
        public StunPhase Phase;
        public float StunLeft;
        public float StunTotal = 1f;
        public bool InCargo;
        [System.NonSerialized] public ICarrier Carrier;
        [Range(0f, 100f)] public float Condition = 100f;
        // Set by GreyboxVanCargo while a Groggy body crawls for an open cargo door: crawl toward CrawlGoal (world) with
        // EscapeCrawlForce instead of away from the pawn. Cleared on standing up or sitting up.
        [System.NonSerialized] public bool CrawlToward;
        [System.NonSerialized] public Vector3 CrawlGoal;
        // Capture -> delivery stage A (Capture/CaptureNpc): zip-tied hands. The hands' only action in this build is the
        // knock on the van wall, which stops; a future grip on the world (GripAnchor) must check this too.
        [System.NonSerialized] public bool HandsBound;
        // Set by a crowd walker (Crowd/CrowdWalker) that moves and animates this NPC while it is free and calm: UpdateFree
        // then only blinks. Fleeing, going down and everything after stay this script's.
        [System.NonSerialized] public bool ExternalLocomotion;
        // Stage 9 step 4: tripped (Stumble) and not up yet: GettingUp, but not knocked down (Police/PoliceOfficer is not
        // Down meanwhile and carries on after).
        [System.NonSerialized] public bool Stumbling;
        // Kicks while Groggy (both bodies) and holds they tore loose: plain counters for the smoke test and the notes.
        [System.NonSerialized] public int Kicks, Tears;

        public static readonly List<GreyboxNpc> All = new();
        // Raised when a free NPC goes down (before its body switches on) and when it becomes loaded in a cargo bay.
        public static event System.Action<GreyboxNpc, NpcIncident> Incident;

        private CharacterController _controller;
        private GreyboxNpcBody _body;
        private NpcRagdoll _ragdoll;
        private NpcGetUp _getUp;
        private NpcStruggle _struggle;
        private NpcAnimDriver _animDriver;
        // Hopping out of a standing van (JumpOut): flees from the van for twice CalmAfter once it lands; the landing thud
        // of the Cargo_JumpOut clip (its Land event) sounded.
        private bool _hopOut, _landed;
        private Animator _animator;
        private Transform _visual;
        // The visual's standing local pose, and the pose it is moving to (VisualPose; over _visualBlend seconds).
        private Vector3 _visualHome, _visualGoal;
        private Quaternion _visualHomeRotation = Quaternion.identity, _visualGoalRotation = Quaternion.identity;
        private float _visualBlend;
        // Sitting with the sit clips (stage 9) rather than the sunk standing Idle; the next knock, the strikes sounded.
        private bool _seatClips;
        private float _nextKnock, _knockAt;
        private float _wallScootAt = -1f; // when the visual moves onto the seat turned / slid by NpcGetUp.SitUp (SeatMoved)
        private int _knockHit = -1;
        private GreyboxFace _face;
        private VanController _van;
        private Rigidbody _vanBody;
        private GreyboxPawn _pawn;
        private SeaReturnTracker _tracker;
        private Vector3 _threat;
        private float _fleeUntil;
        private float _verticalSpeed;
        private float _flashUntil;
        private float _noiseSeed;
        private float _nextKick;
        private float _nextCrawl;
        private float _impactGraceUntil;
        private bool _wasInCargo;
        private float _nextScream;
        private float _nextVoice;
        private float _nextHurt;

        public GreyboxNpcBody Body => _body;
        /// <summary>Stage 9: the ragdoll component (its bodies exist only while this NPC lies down as one).</summary>
        public NpcRagdoll Ragdoll => _ragdoll;
        /// <summary>Stage 9 step 3: the get-up / sit-up clips' driver (busy while GettingUp).</summary>
        public NpcGetUp GetUp => _getUp;
        /// <summary>Stage 9 step 4: the Groggy ragdoll's struggle on its joint drives.</summary>
        public NpcStruggle Struggle => _struggle;
        /// <summary>Stage 9 step 5: the Animator's only writer (crowd walkers and police officers give it their speed, the
        /// activity, aiming and one-shots).</summary>
        public NpcAnimDriver Anim => _animDriver;
        /// <summary>Stage 9: the physical body in use, the ragdoll while it is built, otherwise the capsule (check Active:
        /// a free NPC has neither). The cargo bay and the police read downed bodies through it.</summary>
        public INpcBody PhysicalBody => Down;
        public bool IsDown => State == NpcState.Down;
        public bool Fleeing => State == NpcState.Free && Time.time < _fleeUntil;
        // The downed body in use: the ragdoll while it is built, otherwise the capsule.
        private INpcBody Down => _ragdoll != null && _ragdoll.Active ? _ragdoll : (INpcBody)_body;
        private bool Ragdolled => _ragdoll != null && _ragdoll.Active;
        // Middle of the body, upright or lying (the root is at the feet).
        public Vector3 Center
        {
            get
            {
                INpcBody down = Down;
                return down != null && down.Active ? down.CenterOfMass : transform.TransformPoint(0f, 0.75f, 0f);
            }
        }
        private bool CarrierAlive => Carrier is Object o ? o != null : Carrier != null;
        private GreyboxFace Face => _face ??= new GreyboxFace(gameObject);

        /// <summary>Hit zone of a swing along 'ray' (the view ray of a first-person hit), in NPC space: the height where
        /// the ray passes closest to the body's axis (feet to top), and how close it passes to the head centre
        /// (HitZones.Classify). Works for a near miss too (the sphere cast beside the head). Sitting in the van the capsule
        /// is only SeatedHeight (1 m) tall and the mesh is sunk by SeatedVisualDrop: heights are counted as on the standing
        /// body, so the top of a sitter (its head) is still a head hit.</summary>
        public HitZone ZoneAlong(Ray ray)
        {
            if (Ragdolled) return _ragdoll.ZoneAlong(ray); // stage 9: the part the swing passes closest to
            float bodyHeight = _body != null ? _body.Height : 1.5f;
            float drop = _body != null && _body.Seated ? SeatedVisualDrop : 0f;
            Vector3 origin = transform.InverseTransformPoint(ray.origin);
            Vector3 direction = transform.InverseTransformDirection(ray.direction).normalized;
            float top = Mathf.Max(0.1f, bodyHeight - drop);
            float height = ClosestAxisHeight(origin, direction, top) + drop;
            Vector3 head = new(0f, bodyHeight - HitZones.HeadCentreBelowTop - drop, 0f);
            Vector3 toHead = head - origin;
            float along = Mathf.Max(0f, Vector3.Dot(toHead, direction));
            float headDistance = (toHead - direction * along).magnitude;
            return HitZones.Classify(height, bodyHeight, headDistance);
        }

        /// <summary>Hit zone of a world point on this NPC (third person, no view ray): its height above the feet.</summary>
        public HitZone ZoneAt(Vector3 world)
        {
            if (Ragdolled) return _ragdoll.ZoneAt(world);
            float height = transform.InverseTransformPoint(world).y;
            if (_body != null && _body.Seated) height += SeatedVisualDrop;
            return HitZones.Classify(height, _body != null ? _body.Height : 1.5f);
        }

        // Height (0..top, local up) of the point on the body axis nearest to the ray origin + t * direction, t >= 0.
        private static float ClosestAxisHeight(Vector3 origin, Vector3 direction, float top)
        {
            float b = direction.y; // dot(axis, direction), axis = local up
            float denominator = 1f - b * b;
            float s;
            if (denominator < 1e-4f) s = origin.y; // looking along the axis (straight down on a standing NPC)
            else
            {
                // Closest points of the two lines (axis through the root, the ray), with w = axis origin - ray origin.
                Vector3 w = -origin;
                s = (b * Vector3.Dot(direction, w) - w.y) / denominator;
                if (Vector3.Dot(direction, w) + s * b < 0f) s = origin.y; // the closest point is behind the eye
            }
            return Mathf.Clamp(s, 0f, top);
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            All.Clear();
            Incident = null;
            LegacyVanKnock = false;
        }

        // In OnEnable rather than Awake: it also runs after a script reload in Play mode, which drops these references
        // and the event subscription.
        private void OnEnable()
        {
            if (!All.Contains(this)) All.Add(this);
            if (_controller == null) _controller = GetComponent<CharacterController>();
            // Scenes built before stage 1 have no body component yet.
            if (_body == null && !TryGetComponent(out _body)) _body = gameObject.AddComponent<GreyboxNpcBody>();
            _body.Impact -= OnImpact;
            _body.Impact += OnImpact;
            // Stage 9: the ragdoll sits on every NPC (no bodies until it goes down as one), so map builders need no edits.
            if (_ragdoll == null && !TryGetComponent(out _ragdoll)) _ragdoll = gameObject.AddComponent<NpcRagdoll>();
            _ragdoll.Impact -= OnImpact;
            _ragdoll.Impact += OnImpact;
            if (_getUp == null && !TryGetComponent(out _getUp)) _getUp = gameObject.AddComponent<NpcGetUp>();
            _getUp.Ground = GroundPoint;
            if (_struggle == null && !TryGetComponent(out _struggle)) _struggle = gameObject.AddComponent<NpcStruggle>();
            if (_animDriver == null && !TryGetComponent(out _animDriver)) _animDriver = gameObject.AddComponent<NpcAnimDriver>();
            // Scene references (looked up once; again after a reload if it dropped them) and the non-serialized grab
            // flag. Carrier is recovered in Update (RecoverCarrier), once every cargo bay has re-registered itself in
            // VanCargoSpace.All.
            if (_van == null) _van = FindAnyObjectByType<VanController>();
            if (_vanBody == null && _van != null) _vanBody = _van.GetComponent<Rigidbody>();
            if (_pawn == null) _pawn = FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include);
            if (_animator == null)
            {
                _animator = GetComponentInChildren<Animator>();
                if (_animator != null && _animator.transform != transform)
                {
                    _visual = _animator.transform;
                    // Its standing place. Sitting (after a script reload) it is moved for the seat: the builders put the
                    // visual at the root's origin.
                    bool seated = _body.Seated;
                    _visualHome = _visualGoal = seated ? Vector3.zero : _visual.localPosition;
                    _visualHomeRotation = _visualGoalRotation = seated ? Quaternion.identity : _visual.localRotation;
                }
            }
            _body.Grabbable = State == NpcState.Down || State == NpcState.Escaping;
            _ragdoll.Grabbable = State == NpcState.Down && _ragdoll.Active;
            // After a script reload: a sitter keeps its sit clips (the visual is still posed for them).
            if (State == NpcState.CargoSeated && _body.Seated) _seatClips = _getUp.CanSitUp;
            WaterBodyAudio.Ensure(gameObject);
        }

        private void OnDisable()
        {
            All.Remove(this);
            if (_body != null) _body.Impact -= OnImpact;
            if (_ragdoll != null) _ragdoll.Impact -= OnImpact;
        }

        private void Start()
        {
            _noiseSeed = Random.Range(0f, 100f);
            _face = new GreyboxFace(gameObject);
            _tracker = GetComponent<SeaReturnTracker>();
            // _van, _vanBody, _pawn, _animator and _visual come from OnEnable.
            if (State == NpcState.Free)
            {
                if (_controller.enabled) IgnoreVan(_controller);
                transform.Rotate(0f, Random.Range(0f, 360f), 0f);
            }
        }

        private void Update()
        {
            if (InCargo && Carrier == null) RecoverCarrier();
            if (InCargo != _wasInCargo)
            {
                _wasInCargo = InCargo;
                if (InCargo) Incident?.Invoke(this, NpcIncident.Captured);
            }
            switch (State)
            {
                case NpcState.Free: UpdateFree(); break;
                case NpcState.Down: UpdateDown(); break;
                case NpcState.CargoSeated: UpdateSeated(); break;
                case NpcState.Escaping: UpdateEscaping(); break;
                case NpcState.GettingUp: UpdateGettingUp(); break;
            }
        }

        private void FixedUpdate()
        {
            if (State == NpcState.Down)
            {
                FixedDown();
                return;
            }
            // Fedya's playtest 2026-10-11: a fast van is looked for every physics step too, not only every rendered frame,
            // so the body is never born more than one step's travel inside the bumper (0.32 m at 70 km/h).
            if (!LegacyVanKnock && (State == NpcState.Free ||
                                    (State == NpcState.GettingUp && _getUp != null && _getUp.Current != NpcGetUp.Step.Settling)) && VanHits())
            {
                KnockOver(_vanBody);
                return;
            }
            if (_struggle != null && _struggle.Current != NpcStruggle.Mode.Off) _struggle.Stop(); // up (or getting up): limp
            if (State == NpcState.GettingUp && _getUp != null) _getUp.FixedTick();
        }

        private void LateUpdate()
        {
            if (_visualBlend > 0f) BlendVisual();
            _face?.Apply();
        }

        // ---------- Free ----------

        private void UpdateFree()
        {
            if (VanHits())
            {
                if (LegacyVanKnock) KnockOver(VanPush());
                else KnockOver(_vanBody);
                return;
            }
            if (Scared(out Vector3 from))
            {
                if (Time.time >= _fleeUntil) Scream(); // calm -> running: one scream, not one per frame of fear
                _threat = from;
                _fleeUntil = Time.time + CalmAfter;
            }

            bool fleeing = Time.time < _fleeUntil;
            if (ExternalLocomotion && !fleeing)
            {
                Face.Set("Surprised", 0f);
                Face.Set("Worried", 0f);
                Face.TickBlink();
                return;
            }
            Vector3 move = Vector3.zero;
            if (fleeing)
            {
                Vector3 away = Flat(transform.position - _threat);
                if (away.sqrMagnitude < 0.01f) away = transform.forward;
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(away), 540f * Time.deltaTime);
                move = transform.forward * FleeSpeed;
            }
            _verticalSpeed = _controller.isGrounded ? -1f : _verticalSpeed - 20f * Time.deltaTime;
            _controller.Move((move + Vector3.up * _verticalSpeed) * Time.deltaTime);

            // Step 5: the driver picks the clip (fleeing: the panic run) and its playback from the speed.
            if (_animDriver != null) _animDriver.SetMove(Flat(_controller.velocity).magnitude);
            Face.Set("Surprised", fleeing ? 100f : 0f);
            Face.Set("Worried", fleeing ? 70f : 0f);
            if (!fleeing) Face.TickBlink();
        }

        // Level with the van too, not under it on a bridge or below a road embankment (the look map is not flat).
        private bool VanHits() => _van != null && Mathf.Abs(_van.SpeedKmh) > KnockSpeedKmh &&
                                  Flat(_van.transform.position - transform.position).magnitude < 2.6f &&
                                  Mathf.Abs(_van.transform.position.y - transform.position.y) < 2f;

        // Before 2026-10-11 (LegacyVanKnock): 0.9 of the van's velocity, so the van caught up with the thrown body.
        private Vector3 VanPush()
        {
            Vector3 push = _vanBody != null ? _vanBody.linearVelocity : _van.transform.forward * 10f;
            return push * 0.9f + Vector3.up * 5f;
        }

        private bool Scared(out Vector3 from)
        {
            from = Vector3.zero;
            if (_van != null && Mathf.Abs(_van.SpeedKmh) > 5f && Flat(_van.transform.position - transform.position).magnitude < VanScareRadius)
            {
                from = _van.transform.position;
                return true;
            }
            if (_pawn != null && _pawn.Controlled && Flat(_pawn.Position - transform.position).magnitude < WalkerScareRadius)
            {
                from = _pawn.Position;
                return true;
            }
            return false;
        }

        // ---------- Going down ----------

        /// <summary>A hit (Q now, other weapons later) from 'from' landing at 'point'. Stuns for the weapon's duration in
        /// that zone, never shortening what is left, and pushes 60 N·s at the point. Works free, lying or sitting.</summary>
        public void Hit(WeaponStun weapon, HitZone zone, Vector3 from, Vector3 point)
        {
            if (weapon == null) weapon = WeaponStun.Fist;
            bool alreadyOut = State == NpcState.Down && Phase == StunPhase.Out;
            // Re-stunning one that is already caught (lying, sitting, escaping) works but costs Condition (never kills);
            // one getting up is not caught any more.
            if (State != NpcState.Free && State != NpcState.GettingUp) Condition = Mathf.Max(0f, Condition - ReStunConditionCost);
            bool seated = State != NpcState.Free && _body.Active && _body.Seated;
            // A running NPC falls on in its run; a lying or sitting one keeps the velocity it has (e.g. the van's).
            if (Upright) GoDown(_controller.enabled ? _controller.velocity : Vector3.zero, Vector3.zero);
            else GoDown(null, null);
            ExtendStun(weapon.Duration(zone));
            Vector3 push = Flat(point - from);
            if (push.sqrMagnitude < 1e-4f) push = Flat(-transform.forward);
            if (push.sqrMagnitude < 1e-4f) push = Vector3.forward;
            // Stage 9: a sitter that became the ragdoll lies elsewhere in the bay now; the blow lands where the zone said
            // (the head, else the torso), not on whatever light limb is nearest to the old point.
            if (seated && Ragdolled)
                point = zone == HitZone.Head
                    ? _ragdoll.Landmark(NpcLandmark.Head)
                    : (_ragdoll.Landmark(NpcLandmark.Pelvis) + _ragdoll.Landmark(NpcLandmark.Collar)) * 0.5f;
            Down.Push(push.normalized * HitImpulse, point);
            // Step 5: the capsule keeps its Animator on (the ragdoll's is off): the mesh flinches, then lies (Down).
            if (!Ragdolled && _animDriver != null)
                _animDriver.Trigger(zone == HitZone.Head ? NpcAnimTrigger.HitHead
                    : Vector3.Dot(from - Center, transform.forward) >= 0f ? NpcAnimTrigger.HitFront : NpcAnimTrigger.HitBack);
            if (!alreadyOut && Time.time >= _nextHurt)
            {
                _nextHurt = Time.time + 0.35f;
                Sfx.PlayAt(SfxIds.NpcHurt, VoicePoint, Mathf.Lerp(0.8f, 1f, (weapon.Strength - 1) / 4f));
            }
        }

        /// <summary>Thrown out of the van (the tumble at speed) or by a script: down with that velocity, stunned like a fist
        /// to the torso; where the body is born inside the van it passes out of it (the van's knock grace below).</summary>
        public void KnockOver(Vector3 velocity) => KnockOver(velocity, _vanBody);

        /// <summary>Hit by a fast vehicle (the van, a police car): down with the vehicle's velocity at the NPC times
        /// KnockAhead plus KnockLift up, stunned like a fist to the torso. Fedya's playtest 2026-10-11 ("he gets stuck in
        /// the van's geometry"): born partly inside the vehicle, the body ignores it only until they are apart
        /// (IgnoreWhileOverlapping), and it leaves faster than the vehicle comes.</summary>
        public void KnockOver(Rigidbody vehicle)
        {
            Vector3 velocity = vehicle != null ? vehicle.GetPointVelocity(Center) * KnockAhead : Vector3.zero;
            KnockOver(velocity + Vector3.up * KnockLift, vehicle);
        }

        private void KnockOver(Vector3 velocity, Rigidbody vehicle)
        {
            GoDown(velocity, Random.onUnitSphere * 8f);
            ExtendStun(WeaponStun.Fist.Duration(HitZone.Torso));
            if (vehicle != null)
            {
                if (LegacyVanKnock) Down.IgnoreFor(vehicle.GetComponentsInChildren<Collider>(), VanKnockIgnore);
                else Down.IgnoreWhileOverlapping(vehicle);
            }
            Face.Set("Surprised", 100f, 10000f);
        }

        // On its feet, or rising on them in a get-up clip (no physical body): a hit or a van knocks it down from its pose.
        private bool Upright => State == NpcState.Free || (State == NpcState.GettingUp && !Ragdolled);

        // velocity / angularVelocity: set on the body; null keeps what an already active body has.
        private void GoDown(Vector3? velocity, Vector3? angularVelocity)
        {
            if (State == NpcState.GettingUp && _getUp != null) _getUp.Cancel();
            // On its feet, or only tripped (step 4: lying after a stumble is no knockdown yet): a new incident.
            if (Upright || Stumbling) Incident?.Invoke(this, NpcIncident.Stunned); // a crowd walker lets go here, before the body exists
            if (Upright)
            {
                _controller.enabled = false;
                SetTracker(false, false);
            }
            Stumbling = false;
            _hopOut = false;
            // Stage 9: a free NPC becomes the ragdoll when F10 says so and the cap allows (NpcRagdoll.CanActivate), and so
            // does one sitting in the van or escaping (the seated capsule); a lying body keeps its kind.
            if (Ragdolled) _ragdoll.SetVelocity(velocity, angularVelocity);
            else if (!_body.Active && _ragdoll.CanActivate)
                _ragdoll.Activate(velocity ?? Vector3.zero, angularVelocity ?? Vector3.zero);
            else if (!_body.Active) _body.Activate(velocity ?? Vector3.zero, angularVelocity ?? Vector3.zero);
            else if (_body.Seated && _ragdoll.CanActivate) SeatedToRagdoll(velocity, angularVelocity);
            else
            {
                if (_body.Seated) _body.SetSeated(false); // sitting in the van or escaping: down again where it is
                if (velocity.HasValue) _body.Rigidbody.linearVelocity = velocity.Value;
                if (angularVelocity.HasValue) _body.Rigidbody.angularVelocity = angularVelocity.Value;
            }
            if (!Ragdolled) VisualPose(_visualHome, _visualHomeRotation, 0f); // a ragdoll's bones hang under the visual: never move it then
            State = NpcState.Down;
            Down.Grabbable = true;
            _impactGraceUntil = Time.time + ImpactGrace; // its own fall is not a "drop"
        }

        // Stage 9: a sitter or an escaper (the seated capsule, its mesh sunk by SeatedVisualDrop) going down as the ragdoll.
        // Outside a cargo bay (the tumble out of a fast van) it is built from its standing pose where it is. In a bay the
        // ragdoll (1.85 m from the heels to the head top, longer than the stage-1 capsule) lies down on its back along the
        // van, head toward the roomier end, moved only as far as needed to fit between the rear doors and the partition and
        // between the wheel housings (BayLieHalfWidth); a body already lying there gets pushed aside by the solver.
        // velocity null keeps the capsule's (a sitter's: the van's).
        private void SeatedToRagdoll(Vector3? velocity, Vector3? angularVelocity)
        {
            Vector3 keep = _body.Rigidbody != null ? _body.Rigidbody.linearVelocity : Vector3.zero;
            Vector3 centre = _body.CenterOfMass;
            VanCargoSpace bay = CargoAt(centre);
            VisualPose(_visualHome, _visualHomeRotation, 0f); // the standing mesh on the root again, so its bones are where the body is
            _body.Deactivate();
            if (bay == null)
            {
                _ragdoll.Activate(velocity ?? keep, angularVelocity ?? Vector3.zero);
                return;
            }
            _ragdoll.Activate(Vector3.zero, Vector3.zero);
            _ragdoll.LyingExtent(out float headward, out float footward);
            Bounds box = bay.LocalBox;
            Vector3 local = bay.ToLocal(centre);
            const float margin = 0.05f;
            bool headFront = local.z < box.center.z; // more room toward the partition
            float zMin = box.min.z + margin + (headFront ? footward : headward);
            float zMax = box.max.z - margin - (headFront ? headward : footward);
            float z = zMin <= zMax ? Mathf.Clamp(local.z, zMin, zMax) : box.center.z;
            float x = Mathf.Clamp(local.x - box.center.x, -BayLieHalfWidth, BayLieHalfWidth) + box.center.x;
            Vector3 floor = bay.ToWorld(new Vector3(x, box.min.y, z));
            _ragdoll.PlaceLying(floor, bay.Rotation * (headFront ? Vector3.forward : Vector3.back), true);
            _ragdoll.SetVelocity(velocity ?? keep, angularVelocity);
        }

        // m from the bay's middle line a ragdoll laid down in it may lie: its arms stay clear of the rear wheel housings
        // (1.04 m apart).
        private const float BayLieHalfWidth = 0.15f;

        private void ExtendStun(float duration)
        {
            if (duration > StunLeft)
            {
                StunLeft = duration;
                StunTotal = duration;
            }
            Phase = PhaseNow();
        }

        private StunPhase PhaseNow() => 1f - StunLeft / Mathf.Max(0.01f, StunTotal) < OutShare ? StunPhase.Out : StunPhase.Groggy;

        // ---------- Down ----------

        private void UpdateDown()
        {
            if (!Down.Active)
            {
                Wake(); // the body was removed from outside
                return;
            }
            // Runs while held and while lying in a moving van too (one rule, Fedya 2026-10-04).
            StunLeft -= Time.deltaTime;
            if (StunLeft <= 0f)
            {
                Wake();
                return;
            }
            StunPhase previousPhase = Phase;
            Phase = PhaseNow();
            if (previousPhase == StunPhase.Out && Phase == StunPhase.Groggy)
                Sfx.PlayAt(SfxIds.NpcGasp, VoicePoint);
            if (Phase == StunPhase.Out)
            {
                _nextVoice = Time.time + Random.Range(0.3f, 1.2f); // the first mumble soon after it turns groggy
                Face.Set("Surprised", 0f);
                Face.Set("Worried", 0f);
                Face.Set("Blink", 100f, 1500f);
            }
            else
            {
                Face.Set("Surprised", Time.time < _flashUntil ? 100f : 0f, 900f);
                Face.Set("Worried", 70f);
                Face.TickBlink();
                VoiceEvery(SfxIds.NpcMumble, MumbleInterval);
            }
        }

        private void FixedDown()
        {
            INpcBody body = Down;
            if (!body.Active) return;
            float now = Time.time;
            bool groggy = Phase == StunPhase.Groggy;
            // In a cargo bay it crawls only for an open door (GreyboxVanCargo sets CrawlToward): crawling about inside
            // would keep it from ever resting long enough to count as loaded.
            bool crawl = groggy && body.HolderCount == 0 && (CrawlToward || CargoAt(Center) == null);
            bool ragdoll = Ragdolled;
            // Stage 9 step 4: the ragdoll struggles on its joint drives (crawling too); the capsule keeps its hops below.
            if (ragdoll && _struggle != null)
                _struggle.Tick(groggy, crawl ? CrawlDirection() : Vector3.zero,
                    CrawlToward ? EscapeCrawlForce / Mathf.Max(1f, CrawlForce) : 1f);
            if (groggy)
            {
                if (now >= _nextKick)
                {
                    Kick();
                    _nextKick = now + Random.Range(KickInterval.x, KickInterval.y);
                }
                if (!ragdoll && crawl && now >= _nextCrawl && body.Grounded)
                {
                    Crawl();
                    _nextCrawl = now + CrawlPeriod;
                }
            }
            else
            {
                // Out: the first kick and crawl come a moment after it turns Groggy.
                _nextKick = now + Random.Range(KickInterval.x, KickInterval.y);
                _nextCrawl = now + CrawlPeriod;
            }
            if (body.OnlyLegsHeld && RelativeVelocity().magnitude > AnkleDragSpeed)
                Condition = Mathf.Max(0f, Condition - AnkleDragCost * Time.fixedDeltaTime);
        }

        // A leg lashes out across the body (and a bit up). It jerks whoever holds that ankle and can tear a hold loose:
        // KickTearChance by holder count (one in five with one holder, one in twenty with two, never with three: the
        // draft says three hold it even when groggy).
        private void Kick()
        {
            NpcSide side = Random.value < 0.5f ? NpcSide.Left : NpcSide.Right;
            Vector3 across = transform.TransformDirection(new Vector3(Random.Range(-1f, 1f), 0f, Random.Range(-1f, 1f)));
            if (across.sqrMagnitude < 1e-4f) across = transform.right;
            INpcBody body = Down;
            body.Kick(side, (across.normalized + Vector3.up * 0.6f).normalized * KickImpulse);
            if (Ragdolled && _struggle != null) _struggle.Kick(side); // stage 9 step 4: the leg's motors lash out
            Kicks++;
            int holders = body.HolderCount;
            if (holders > 0 && KickTearChance.Length > 0 &&
                Random.value < KickTearChance[Mathf.Min(holders, KickTearChance.Length - 1)] &&
                body.Tear(side == NpcSide.Left ? NpcLandmark.LeftAnkle : NpcLandmark.RightAnkle))
                Tears++;
            _flashUntil = Time.time + 0.3f;
        }

        // The capsule's crawl: a hop and a push along the ground every CrawlPeriod (the ragdoll crawls on its drives).
        private void Crawl()
        {
            float force = CrawlToward ? EscapeCrawlForce : CrawlForce;
            Down.Scoot(CrawlDirection() * (force * CrawlPeriod), CrawlHop);
        }

        // Which way a Groggy body crawls (flat, unit): to an open cargo door (CrawlGoal), else away from the threat, else
        // head first.
        private Vector3 CrawlDirection()
        {
            Vector3 away = CrawlToward ? Flat(CrawlGoal - Center) : Flat(Center - ThreatPosition());
            if (away.sqrMagnitude < 0.01f)
                away = Ragdolled
                    ? Flat(_ragdoll.Landmark(NpcLandmark.Head) - _ragdoll.Landmark(NpcLandmark.Pelvis))
                    : Flat(transform.up); // head first
            if (away.sqrMagnitude < 0.01f) away = Vector3.forward;
            return away.normalized;
        }

        // Body velocity against what it lies on: the cargo bay when loaded, otherwise the world.
        private Vector3 RelativeVelocity()
        {
            Rigidbody rb = Down.MainBody;
            if (rb == null) return Vector3.zero;
            Vector3 frame = InCargo && CarrierAlive ? Carrier.PointVelocity(rb.worldCenterOfMass) : Vector3.zero;
            return rb.linearVelocity - frame;
        }

        private void OnImpact(float speed, Collider other)
        {
            if (State != NpcState.Down || speed < ImpactWakeSpeed || Time.time < _impactGraceUntil) return;
            Condition = Mathf.Max(0f, Condition - ImpactConditionCost);
            if (StunLeft > EarlyWakeLeft) StunLeft = EarlyWakeLeft; // jolted: comes round within a second
            _impactGraceUntil = Time.time + 0.3f; // one cost per landing, not one per bounce contact
            Debug.Log($"[NPC] {name}: impact {speed:0.0} m/s on {(other != null ? other.name : "?")} -> waking early, condition {Condition:0}");
        }

        // ---------- Waking ----------

        private void Wake()
        {
            INpcBody body = Down;
            body.RevokeAll();
            StunLeft = 0f;
            if (_struggle != null) _struggle.Stop(); // limp again before settling, sitting up or the quick stand-up
            // Lying in a cargo bay (loaded, or just dragged in): sits up there. Anywhere else: stands up and runs.
            if (!InCargo && body.Active && CargoAt(Center) is VanCargoSpace space)
            {
                InCargo = true;
                Carrier = space;
            }
            if (InCargo && CarrierAlive && body.Active)
            {
                // Stage 9: a ragdoll sits up with SitUp_Cargo; the capsule (or a rig without the clips) as before.
                if (Ragdolled && SitUpFromRagdoll()) return;
                if (Ragdolled) RagdollToCapsule();
                SitInCargo();
                return;
            }
            // Stage 9: a ragdoll gets up with a clip (GettingUp); the capsule (or a rig without the clips) at once.
            if (Ragdolled && _getUp != null && _getUp.CanGetUp)
            {
                BeginGetUp();
                return;
            }
            StandUp(ThreatPosition());
        }

        private static VanCargoSpace CargoAt(Vector3 world)
        {
            foreach (VanCargoSpace space in VanCargoSpace.All)
                if (space != null && space.isActiveAndEnabled && space.Upright && space.Contains(world))
                    return space;
            return null;
        }

        private void StandUp(Vector3 threat)
        {
            Vector3 centre = Center;
            Vector3 facing = Flat(transform.forward);
            if (facing.sqrMagnitude < 1e-4f) facing = Flat(transform.up);
            if (Ragdolled)
            {
                // Stage 9, no get-up clip yet: up where its hips lay, facing the way a get-up would end (feet side from
                // the back, head side from the belly); the pose blends from lying to the animation (NpcRagdoll).
                centre = _ragdoll.Landmark(NpcLandmark.Pelvis);
                Vector3 stand = _ragdoll.StandFacing();
                if (stand.sqrMagnitude > 1e-4f) facing = stand;
                _ragdoll.Deactivate();
            }
            float yaw = facing.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(facing).eulerAngles.y : transform.eulerAngles.y;
            _body.Deactivate();
            _body.Grabbable = false;
            VisualPose(_visualHome, _visualHomeRotation, 0f);
            Vector3 p = GroundPoint(centre, 1.5f);
            transform.SetPositionAndRotation(p, Quaternion.Euler(0f, yaw, 0f));
            ControllerOn();
            Stood(threat, p);
        }

        // The end of every stand-up (at once, or after a get-up clip): free, screaming, running from 'threat' (twice as long
        // after hopping out of a van, as LeaveCargo). Step 4: up from a trip (Stumbling) it carries on as it was: no scream,
        // no flight.
        private void Stood(Vector3 threat, Vector3 at)
        {
            bool tripped = Stumbling;
            Stumbling = false;
            if (!tripped)
            {
                _threat = threat;
                _fleeUntil = Time.time + CalmAfter * (_hopOut ? 2f : 1f);
                Scream(); // up and running
            }
            _hopOut = false;
            State = NpcState.Free;
            Phase = StunPhase.None;
            StunLeft = 0f;
            InCargo = false;
            Carrier = null;
            CrawlToward = false;
            // Dragged far while down (or into the van and out): forget the old dry points, unless it woke up in the sea.
            SetTracker(true, !SeaReturnZone.InSea(at));
        }

        private void ControllerOn()
        {
            if (_controller.enabled) return;
            _controller.enabled = true;
            IgnoreVan(_controller); // re-enabling recreates the shape, which drops ignore pairs
            _verticalSpeed = 0f;
        }

        // ---------- Getting up with a clip (stage 9 step 3) ----------

        // The stun is over and it lies as the ragdoll outside a van: NpcGetUp settles it, picks GetUp_Back or GetUp_Belly
        // and plays it from the lying pose; UpdateGettingUp switches the CharacterController on at the clip's Stable point
        // and frees it at the end.
        private void BeginGetUp()
        {
            State = NpcState.GettingUp;
            Phase = StunPhase.Awake;
            CrawlToward = false;
            _ragdoll.Grabbable = false;
            _body.Grabbable = false;
            _getUp.Begin();
        }

        private void UpdateGettingUp()
        {
            NpcGetUp.Step before = _getUp.Current;
            if (before == NpcGetUp.Step.None && Ragdolled)
            {
                StandUp(ThreatPosition()); // the get-up was lost while it still lay (never expected): up the old way
                return;
            }
            // Rising in the clip, a fast van knocks it over again (lying, the van hits the ragdoll itself).
            if (before != NpcGetUp.Step.Settling && VanHits())
            {
                if (LegacyVanKnock) KnockOver(VanPush());
                else KnockOver(_vanBody);
                return;
            }
            NpcGetUp.Step now = _getUp.Tick(Time.deltaTime);
            if (before == NpcGetUp.Step.Settling && now == NpcGetUp.Step.None)
            {
                StandUp(ThreatPosition()); // the ragdoll vanished while settling: up the old way
                return;
            }
            if (now == NpcGetUp.Step.Standing || now == NpcGetUp.Step.None) ControllerOn();
            bool hop = _getUp.Kind == GetUpKind.JumpOut; // out of a van: surprised (§4.7); a trip: surprised while it lies
            // Step 5: the Cargo_JumpOut clip's landing (its Land event): a thud where it lands.
            float land = hop ? _getUp.LandAt : -1f;
            if (land > 0f && !_landed && _getUp.ClipTime >= land)
            {
                _landed = true;
                Sfx.PlayAt(SfxIds.ThudGround, transform.position, 0.6f);
            }
            Face.Set("Surprised", hop || (Stumbling && now == NpcGetUp.Step.Settling) ? 100f : 0f);
            Face.Set("Worried", 70f);
            Face.TickBlink();
            if (now == NpcGetUp.Step.None)
                Stood(_hopOut && _van != null ? _van.transform.position : ThreatPosition(), transform.position);
        }

        // ---------- Step 4: the trip and the hop out of a van ----------

        /// <summary>Stage 9 step 4 (design §4.6): trips and goes flat as the ragdoll (NpcRagdoll.Stumble: from the running
        /// pose, pitched forward), not stunned, not grabbable, no incident; lies 'seconds', then gets up with the get-up
        /// clip (NpcGetUp) and is Free again as it was: no scream, no flight (the fat police officer's trip; PoliceOfficer is
        /// not Down meanwhile). A hit or a van while it lies makes it a real knockdown. False, nothing changed, when it
        /// cannot: not on its feet, or no ragdoll for it (NpcRagdoll.CanStumble: the cap, the rig) or no get-up clips.</summary>
        public bool Stumble(Vector3 velocity, float seconds)
        {
            if (State != NpcState.Free || _controller == null || !_controller.enabled || _body == null || _body.Active ||
                _ragdoll == null || !_ragdoll.CanStumble || _getUp == null || !_getUp.CanGetUp)
                return false;
            _controller.enabled = false;
            SetTracker(false, false);
            _ragdoll.Stumble(velocity);
            if (!_ragdoll.Active)
            {
                ControllerOn();
                SetTracker(true, false);
                return false;
            }
            State = NpcState.GettingUp;
            Phase = StunPhase.None;
            StunLeft = 0f;
            Stumbling = true;
            _ragdoll.Grabbable = false;
            _body.Grabbable = false;
            _getUp.Begin(seconds);
            return true;
        }

        /// <summary>Stage 9 step 4 (design §4.5): a passenger leaving a standing or slow van through a cargo door
        /// (GreyboxVanCargo.GetOut below EscapeTumbleKmh) hops down onto the ground outside along 'outward' (NpcGetUp.JumpOut:
        /// procedural, or the Cargo_JumpOut clip once installed) instead of appearing there, then is free and runs from the
        /// van like LeaveCargo(false). A lying body is not a passenger (it just falls out of the bay).</summary>
        public void JumpOut(Vector3 outward)
        {
            if (State == NpcState.Down || _getUp == null || _body == null || !_body.Active || Flat(outward).sqrMagnitude < 1e-4f)
            {
                LeaveCargo(false, Vector3.zero);
                return;
            }
            InCargo = false;
            Carrier = null;
            CrawlToward = false;
            Vector3 start = transform.position; // the seated capsule's root: its bottom, at the door sill
            _body.Deactivate();
            _body.Grabbable = false;
            State = NpcState.GettingUp;
            Phase = StunPhase.Awake;
            _hopOut = true;
            _landed = false;
            // The Cargo_JumpOut clip, else the run (NpcGetUp starts either through the driver: panicking at FleeSpeed).
            float seconds = _getUp.JumpOut(start, outward, FleeSpeed, out _);
            // Out of the escaper's sunk look: upright as it lands.
            VisualPose(_visualHome, _visualHomeRotation, Mathf.Max(0.05f, seconds));
        }

        // The Escape_Scramble clip's state when installed (clips.json), else null: the stage-1 sunk run plays.
        private string ScrambleState
        {
            get
            {
                NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
                return p != null && _getUp != null ? _getUp.Installed(p.Scramble) : null;
            }
        }

        /// <summary>Step 5: how far inside a cargo doorway a passenger running for it hands over to the Cargo_JumpOut clip
        /// (NpcGetUp.HopLead; 0 without the clip). GreyboxVanCargo lets it out there when the van is slow.</summary>
        public float HopLead => _getUp != null && State == NpcState.Escaping ? _getUp.HopLead : 0f;

        /// <summary>Step 5: seconds of the Escape_Scramble_Start clip a sitter plays in place before it runs for a door (0
        /// without it, or without the scramble clips).</summary>
        public float EscapeStartSeconds =>
            _animDriver != null && ScrambleState != null && _seatClips ? _animDriver.Seconds(NpcAnimContract.RoleScrambleStart) : 0f;

        // Stage 9 step 3: a ragdoll waking in a cargo bay sits up there with SitUp_Cargo (the controller then loops
        // Cargo_Sit_Idle): NpcGetUp picks the seat (the clip's first frame where the ragdoll lies, the seated figure inside
        // the bay), the seated capsule goes on there with the van's velocity, the visual turns for the sit clips and the
        // bones blend from the lying pose. False without the clips (RagdollToCapsule, the old way).
        private bool SitUpFromRagdoll()
        {
            if (!(Carrier is VanCargoSpace bay) || _getUp == null || !_getUp.CanSitUp) return false;
            Rigidbody pelvis = _ragdoll.MainBody;
            Vector3 velocity = bay.PointVelocity(pelvis != null ? pelvis.worldCenterOfMass : Center);
            SeatPose(out Vector3 position, out Quaternion rotation);
            if (!_getUp.SitUp(bay, position, rotation, _body.Radius, out Vector3 root, out Quaternion facing)) return false;
            // The seat turned square / slid back to the wall: the figure starts where the ragdoll lies and moves onto the
            // seat with the clip's scramble.
            if (_getUp.SeatMoved) VisualPose(_getUp.SeatStartPosition, _getUp.SeatStartRotation, 0f);
            else VisualPose(position, rotation, 0f);
            _body.ActivateSeated(root, facing, velocity);
            Seated(true);
            NpcRagdollProfile p = _ragdoll.Profile;
            if (_getUp.SeatMoved)
            {
                float seated = p.SitUp.Events != null && p.SitUp.Events.Length >= 2 ? p.SitUp.Events[1] : _getUp.ClipSeconds;
                _wallScootAt = Time.time + Mathf.Max(0f, seated - WallScootSeconds);
            }
            _nextKnock = Time.time + _getUp.ClipSeconds + Random.Range(p.KnockInterval.x, p.KnockInterval.y);
            return true;
        }

        // A ragdoll waking in a cargo bay on a rig without the sit clips hands over to the capsule where it lies: the
        // capsule's middle where the ragdoll's mass was, along it from the feet to the head; SitInCargo seats it facing
        // where the head was. The pose blends from lying to the seated mesh (NpcRagdoll).
        private void RagdollToCapsule()
        {
            Vector3 centre = _ragdoll.CenterOfMass;
            Vector3 axis = _ragdoll.Landmark(NpcLandmark.Head) - _ragdoll.Landmark(NpcLandmark.Pelvis);
            axis = axis.sqrMagnitude > 1e-4f ? axis.normalized : Vector3.up;
            Rigidbody pelvis = _ragdoll.MainBody;
            Vector3 velocity = pelvis != null ? pelvis.linearVelocity : Vector3.zero;
            _ragdoll.Deactivate();
            transform.SetPositionAndRotation(centre - axis * (_body.Height * 0.5f), Quaternion.FromToRotation(Vector3.up, axis));
            _body.Activate(velocity, Vector3.zero);
            if (_body.Rigidbody != null) _body.Rigidbody.ResetCenterOfMass(); // SetSeated reads it in this same frame
        }

        // ---------- In the van (driven by GreyboxVanCargo) ----------

        // The capsule waking in the bay (and the fallback above): seated where it lay. With the sit clips it sits up from
        // lying on its back too (SitUp_Cargo from its first frame, no blend: the capsule had the standing mesh), else the
        // stage-1 look: the standing Idle sunk by SeatedVisualDrop.
        private void SitInCargo()
        {
            _body.SetSeated(true);
            bool clips = _getUp != null && _getUp.CanSitUp;
            Seated(clips);
            if (!clips)
            {
                VisualPose(_visualHome + Vector3.down * SeatedVisualDrop, _visualHomeRotation, 0f);
                return;
            }
            SeatPose(out Vector3 position, out Quaternion rotation);
            VisualPose(position, rotation, 0f);
            NpcRagdollProfile p = _ragdoll.Profile;
            if (_animDriver != null) _animDriver.PlayGetUp(GetUpKind.SitUp, p.SitUp.State);
            _nextKnock = Time.time + p.SitUp.Seconds + Random.Range(p.KnockInterval.x, p.KnockInterval.y);
        }

        // Sitting in the bay now (CargoSeated, awake, not grabbable); clips: the sit clips play (else the sunk Idle).
        private void Seated(bool clips)
        {
            State = NpcState.CargoSeated;
            Phase = StunPhase.Awake;
            CrawlToward = false;
            _body.Grabbable = false;
            _seatClips = clips;
            _knockHit = -1;
            _wallScootAt = -1f;
            _nextVoice = Time.time + Random.Range(1f, 3f);
        }

        // The seated visual's local pose for the sit clips: turned SeatYaw (they face the clip's -X) and moved SeatOffset
        // (the figure over the seated capsule), from the profile (GreyboxBuddySetup.InstallClips measures them).
        private void SeatPose(out Vector3 position, out Quaternion rotation)
        {
            NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
            rotation = _visualHomeRotation * Quaternion.Euler(0f, p != null ? p.SeatYaw : 0f, 0f);
            position = _visualHome + (p != null ? p.SeatOffset : Vector3.zero);
        }

        // Sitting with the sit clips (the controller keeps it on the sit idle): now and then, while the van is slow or
        // parked, a knock on the wall (the KnockOnWall trigger from the sit idle; Cargo_Knock goes back to it by itself) with a
        // thud on each strike while the knock plays.
        private void TickSeatClips()
        {
            NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
            if (p == null || _animDriver == null) return;
            if (_knockHit >= 0 && Time.time - _knockAt > 0.4f && !_animDriver.InState(p.Knock.State)) _knockHit = -1; // cut short
            if (_knockHit >= 0 && _knockHit < p.Knock.Events.Length && Time.time - _knockAt >= p.Knock.Events[_knockHit])
            {
                _knockHit++;
                Sfx.PlayAt(SfxIds.ThudVan, KnockPoint, p.KnockVolume);
            }
            if (HandsBound) return; // tied hands cannot knock
            if (Time.time < _nextKnock) return;
            _nextKnock = Time.time + Random.Range(p.KnockInterval.x, p.KnockInterval.y);
            bool slow = !CarrierAlive || Carrier.PointVelocity(Center).magnitude < p.KnockVanSpeed;
            if (!slow || !p.Knock.Ready || !_animDriver.Trigger(NpcAnimTrigger.KnockOnWall, p.SitIdle.State)) return;
            _knockAt = Time.time;
            _knockHit = 0;
        }

        // About the right fist: the right forearm bone's end, else the voice point.
        private Vector3 KnockPoint
        {
            get
            {
                NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
                int forearm = p != null ? p.IndexOf(NpcRagdollProfile.Kind.ForeArm, NpcSide.Right) : -1;
                Transform bone = forearm >= 0 ? _ragdoll.BoneOf(forearm) : null;
                return bone != null ? bone.position : VoicePoint;
            }
        }

        private void UpdateSeated()
        {
            if (!_body.Active)
            {
                StandUp(ThreatPosition());
                return;
            }
            // Fallback only: the van is gone, or the NPC ended up far outside the bay. Leaving the bay normally (falling
            // out, the tumble at speed, escapes) is GreyboxVanCargo's, at a smaller margin, so it always comes first.
            if (LostCarrier())
            {
                LeaveCargo(false, Vector3.zero);
                return;
            }
            // Nervous: worried, with a startled flicker now and then.
            float flicker = Mathf.PerlinNoise(Time.time * 1.7f, _noiseSeed) > 0.68f ? 70f : 0f;
            Face.Set("Surprised", Time.time < _flashUntil ? 100f : flicker, 900f);
            Face.Set("Worried", 60f);
            Face.TickBlink();
            VoiceEvery(SfxIds.NpcWhimper, WhimperInterval);
            if (_seatClips) TickSeatClips();
            if (_wallScootAt >= 0f && Time.time >= _wallScootAt)
            {
                _wallScootAt = -1f;
                if (_seatClips)
                {
                    SeatPose(out Vector3 position, out Quaternion rotation);
                    VisualPose(position, rotation, WallScootSeconds);
                }
            }
        }

        // SitUp_Cargo's scramble to the wall: its last WallScootSeconds before the Seated event (v05: 2.14-2.90 s), the
        // visual moving from NpcGetUp.SeatStart onto the seat.
        private const float WallScootSeconds = 0.75f;

        private void UpdateEscaping()
        {
            if (!_body.Active)
            {
                StandUp(ThreatPosition());
                return;
            }
            if (LostCarrier())
            {
                LeaveCargo(false, Vector3.zero);
                return;
            }
            Face.Set("Surprised", 100f);
            Face.Set("Worried", 70f);
            // Step 5: the scramble (or the sunk run) plays at the run's speed relative to the van.
            Rigidbody rb = _body.Rigidbody;
            if (_animDriver != null && rb != null)
                _animDriver.SetMove(Flat(rb.linearVelocity - (CarrierAlive ? Carrier.PointVelocity(rb.worldCenterOfMass) : Vector3.zero)).magnitude);
        }

        private bool LostCarrier() => !InCargo || !CarrierAlive || !Carrier.Contains(Center, LostCarrierMargin);

        // A script reload in Play mode drops Carrier ([NonSerialized] interface) but keeps InCargo: find the bay it is in
        // again. In none (or no body), it is no longer loaded, and the usual rules take over (a sitter gets out and runs).
        private void RecoverCarrier()
        {
            // The body in use: the capsule, or a loaded ragdoll (GPT review 2026-10-07, finding 7: it read the capsule only,
            // so a loaded ragdoll lost its load after a reload until it rested long enough to count again).
            INpcBody body = PhysicalBody;
            if (body != null && body.Active)
                foreach (VanCargoSpace space in VanCargoSpace.All)
                    if (space != null && space.isActiveAndEnabled && space.Contains(Center, LostCarrierMargin))
                    {
                        Carrier = space;
                        return;
                    }
            InCargo = false;
        }

        /// <summary>Sitting in the van -> making a run for an open door (the cargo moves the body).</summary>
        public void BeginEscape()
        {
            if (State != NpcState.CargoSeated) return;
            State = NpcState.Escaping;
            // A runner can be grabbed (draft section 2: stop it by blocking the doorway, grabbing it or shutting the door);
            // GreyboxVanCargo stops the run as soon as someone holds it.
            _body.Grabbable = true;
            Scream();
            // The scramble: the Escape_Scramble clip once clips.json installs it (a stooped hurry that fits under the roof,
            // the figure at its standing height); until then the standing run sunk under the roof (stage 1). Either way it
            // turns in from the seat over the cross-fade (the driver's parameters pick the clip: in a van and panicking).
            string scramble = ScrambleState;
            // Step 5: Escape_Scramble_Start turns the sitter from the seat to the door inside the clip (it starts in the sit
            // pose): the visual leaves the seat layout over the whole clip, so the figure keeps facing where it looked.
            float start = scramble != null && _animDriver != null ? _animDriver.Seconds(NpcAnimContract.RoleScrambleStart) : 0f;
            VisualPose(scramble != null ? _visualHome : _visualHome + Vector3.down * SeatedVisualDrop, _visualHomeRotation,
                start > 0f && _seatClips ? start : SeatedSwitch);
        }

        /// <summary>The door shut in its face, it got stuck, or someone grabbed it: back to sitting, with a startled look.
        /// A sitter cannot be held, so any hold on it ends.</summary>
        public void CancelEscape()
        {
            if (State != NpcState.Escaping) return;
            State = NpcState.CargoSeated;
            _body.Grabbable = false;
            _body.RevokeAll();
            Flash();
            if (!_seatClips) return;
            SeatPose(out Vector3 position, out Quaternion rotation);
            VisualPose(position, rotation, SeatedSwitch); // the controller goes back to the sit idle (not panicking)
        }

        // Seconds the visual takes to turn between the seat and the run (the Animator's cross-fade is 0.15 s).
        private const float SeatedSwitch = 0.15f;

        /// <summary>Out of the van. tumble: jumped out of a fast van and rolls along the road, stunned again (the caller
        /// takes the Condition); otherwise lands on its feet and runs.</summary>
        public void LeaveCargo(bool tumble, Vector3 velocity)
        {
            InCargo = false;
            Carrier = null;
            if (tumble)
            {
                KnockOver(velocity);
                return;
            }
            Vector3 from = _van != null ? _van.transform.position : ThreatPosition();
            StandUp(from);
            _fleeUntil = Time.time + 2f * CalmAfter;
        }

        // ---------- Voice (Sfx; silent without a library) ----------

        private void Scream()
        {
            if (Time.time < _nextScream) return;
            _nextScream = Time.time + ScreamCooldown;
            Sfx.PlayAt(SfxIds.NpcScream, VoicePoint);
        }

        private void VoiceEvery(string id, Vector2 interval)
        {
            if (Time.time < _nextVoice) return;
            _nextVoice = Time.time + Random.Range(interval.x, interval.y);
            Sfx.PlayAt(id, VoicePoint);
        }

        // About the head: the top end of a lying body, head height of a standing or sitting one.
        private Vector3 VoicePoint =>
            Ragdolled ? _ragdoll.Landmark(NpcLandmark.Head) :
            _body != null && _body.Active ? Center + transform.up * 0.5f : transform.position + Vector3.up * 1.4f;

        /// <summary>A short startled look (an escape that failed).</summary>
        public void Flash() => _flashUntil = Time.time + 0.5f;

        /// <summary>Stop running away now (a police officer getting up goes for the attacker instead, Police/PoliceOfficer).</summary>
        public void Calm() => _fleeUntil = 0f;

        // The visual's local pose: at once (seconds 0), or eased over 'seconds' (BlendVisual, LateUpdate): standing, seated
        // for the sit clips, or sunk under the van roof (escaping; sitting on rigs without the sit clips). Never while the
        // ragdoll is built: its bodies hang under the visual (callers set it before Activate or after Deactivate).
        private void VisualPose(Vector3 position, Quaternion rotation, float seconds)
        {
            if (_visual == null) return;
            _visualGoal = position;
            _visualGoalRotation = rotation;
            if (seconds > 0f && !Ragdolled)
            {
                _visualBlend = seconds;
                return;
            }
            _visualBlend = 0f;
            _visual.SetLocalPositionAndRotation(position, rotation);
        }

        private void BlendVisual()
        {
            if (_visual == null || Ragdolled)
            {
                _visualBlend = 0f;
                return;
            }
            float k = Mathf.Clamp01(Time.deltaTime / _visualBlend);
            _visualBlend -= Time.deltaTime;
            if (_visualBlend <= 0f) k = 1f;
            _visual.GetLocalPositionAndRotation(out Vector3 position, out Quaternion rotation);
            _visual.SetLocalPositionAndRotation(Vector3.Lerp(position, _visualGoal, k), Quaternion.Slerp(rotation, _visualGoalRotation, k));
        }

        // ---------- Helpers ----------

        private Vector3 ThreatPosition() =>
            _pawn != null && _pawn.Controlled ? _pawn.Position :
            _van != null ? _van.transform.position : Center - transform.forward;

        // Highest ground under p (from 'above' metres up), ignoring the van, the pawn and every NPC (this one included),
        // so nobody ends up standing on someone's head or on the van's roof.
        private Vector3 GroundPoint(Vector3 p, float above)
        {
            float ground = float.NegativeInfinity;
            foreach (RaycastHit hit in Physics.RaycastAll(p + Vector3.up * above, Vector3.down, above + 20f, ~0, QueryTriggerInteraction.Ignore))
            {
                Transform t = hit.collider.transform;
                if (_van != null && t.IsChildOf(_van.transform)) continue;
                if (_pawn != null && (t.IsChildOf(_pawn.transform) || (_pawn.Body != null && t.IsChildOf(_pawn.Body)))) continue;
                if (hit.collider.GetComponentInParent<GreyboxNpc>() != null) continue;
                ground = Mathf.Max(ground, hit.point.y);
            }
            if (!float.IsNegativeInfinity(ground)) p.y = ground;
            return p;
        }

        // The sea tracker runs only while the NPC is free (on its own feet).
        private void SetTracker(bool on, bool rebase)
        {
            if (_tracker == null) _tracker = GetComponent<SeaReturnTracker>();
            if (_tracker == null) return;
            _tracker.enabled = on;
            if (on && rebase) _tracker.Rebase();
        }

        // The free NPC's CharacterController never touches the van (a fast van knocks it over by script instead). Only
        // active van colliders: IgnoreCollision with a disabled collider logs an error.
        private void IgnoreVan(Collider own)
        {
            if (_van == null || own == null || !own.enabled) return;
            foreach (Collider c in _van.GetComponentsInChildren<Collider>())
                if (c.enabled && c.gameObject.activeInHierarchy && c.GetComponentInParent<GreyboxNpc>() == null)
                    Physics.IgnoreCollision(c, own);
        }

        // SeaReturnTracker switched the controller off and on to move it, which dropped the ignore pairs.
        private void OnSeaReturned()
        {
            if (_controller.enabled) IgnoreVan(_controller);
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
