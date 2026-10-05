using System.Collections.Generic;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    public enum NpcState : byte { Free, Down, CargoSeated, Escaping }

    // How a downed NPC is doing. Out: the first 40% of the stun, eyes shut, limp. Groggy: the rest, scared, kicks and
    // crawls. Awake: conscious but caught (sitting in the van, escaping). None: free.
    public enum StunPhase : byte { None, Out, Groggy, Awake }

    // Grey-box crowd NPC (Sausage Buddy), NPC capture stage 1 (canon section 151, draft docs/drafts/NPC_CAPTURE_VAN_COOP_DRAFT.md).
    // Free: idles and blinks, runs away from the van or the on-foot pawn (CharacterController, ignores the van; a fast
    // van still knocks it over by script).
    // Down: a hit (Hit: weapon + zone) or a van knock (KnockOver) turns it into one physics body with grab points
    // (GreyboxNpcBody); players drag it with LMB and push it into the van by hand, there is no carry or load key.
    // The stun timer ALWAYS runs, also while held or carried (Fedya, 2026-10-04): a stunned, not killed, NPC comes round.
    // Out (first 40%): limp. Groggy (the rest): kicks every 0.8-1.5 s (a kick can tear it out of someone's hands, less
    // likely the more hands hold it; three hold it for sure) and crawls away from the pawn when nobody holds it.
    // At 0 it wakes: every hold is revoked; inside a cargo bay it sits up there (CargoSeated), elsewhere it stands up and
    // runs. A hard impact (>4.5 m/s, e.g. a drop from over a metre) wakes it early and costs Condition, as does being
    // dragged fast by the ankles only. Condition never kills (canon section 26), it only goes down.
    // CargoSeated / Escaping: entered here, driven by GreyboxVanCargo (loading, van matching and escapes, chunk 3).
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
        [Range(0f, 1f)] public float OutShare = 0.4f;
        public Vector2 KickInterval = new(0.8f, 1.5f);
        [Tooltip("N·s at an ankle.")]
        public float KickImpulse = 25f;
        [Tooltip("Chance that a kick tears one hold loose, by the number of holders (0, 1, 2, 3).")]
        public float[] KickTearChance = { 0f, 0.5f, 0.2f, 0f };
        [Tooltip("Average crawl push in N while Groggy and nobody holds it, given as hops every CrawlPeriod seconds.")]
        public float CrawlForce = 80f;
        public float CrawlPeriod = 0.6f;
        [Tooltip("m/s up per crawl hop, so ground friction lets go for a moment.")]
        public float CrawlHop = 0.6f;
        [Tooltip("Average crawl push in N while crawling for an open cargo door (GreyboxVanCargo sets CrawlToward).")]
        public float EscapeCrawlForce = 120f;
        [Tooltip("Impact speed (m/s along the contact normal) that wakes it early and costs Condition.")]
        public float ImpactWakeSpeed = 4.5f;
        public float ImpactConditionCost = 5f;
        [Tooltip("Seconds of stun left after a hard impact (at most).")]
        public float EarlyWakeLeft = 1f;
        [Tooltip("Seconds after a hit or knock in which its own fall does not count as an impact.")]
        public float ImpactGrace = 1.5f;
        public float AnkleDragSpeed = 1.5f;
        [Tooltip("Condition per second while dragged by the ankles only, faster than AnkleDragSpeed.")]
        public float AnkleDragCost = 1f;
        [Tooltip("Seconds the knocked body ignores the van's colliders.")]
        public float VanKnockIgnore = 0.5f;
        [Tooltip("A sitting or escaping NPC this far outside its cargo box with nothing else taking it out of the van " +
                 "(no GreyboxVanCargo, the van gone) gets up and runs.")]
        public float LostCarrierMargin = 1f;
        [Tooltip("The standing Buddy mesh is lowered this much while sitting in the cargo bay (no sitting clip yet).")]
        public float SeatedVisualDrop = 0.4f;

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

        public static readonly List<GreyboxNpc> All = new();

        private CharacterController _controller;
        private GreyboxNpcBody _body;
        private Animator _animator;
        private Transform _visual;
        private Vector3 _visualLocal;
        private GreyboxFace _face;
        private VanController _van;
        private Rigidbody _vanBody;
        private GreyboxPawn _pawn;
        private SeaReturnTracker _tracker;
        private Vector3 _threat;
        private float _fleeUntil;
        private float _verticalSpeed;
        private string _anim;
        private float _flashUntil;
        private float _noiseSeed;
        private float _nextKick;
        private float _nextCrawl;
        private float _impactGraceUntil;

        public GreyboxNpcBody Body => _body;
        public bool IsDown => State == NpcState.Down;
        // Middle of the body, upright or lying (the root is at the feet).
        public Vector3 Center => _body != null && _body.Active ? _body.CenterOfMass : transform.TransformPoint(0f, 0.75f, 0f);
        private bool CarrierAlive => Carrier is Object o ? o != null : Carrier != null;
        private GreyboxFace Face => _face ??= new GreyboxFace(gameObject);

        /// <summary>Hit zone of a world point on this NPC, from its height above the feet in NPC space. Sitting in the
        /// van the capsule is only SeatedHeight (1 m) tall and the mesh is sunk by SeatedVisualDrop: heights are counted
        /// as on the standing body, so the top of a sitter (its head) is still a head hit.</summary>
        public HitZone ZoneAt(Vector3 world)
        {
            float height = transform.InverseTransformPoint(world).y;
            if (_body != null && _body.Seated) height += SeatedVisualDrop;
            return HitZones.FromLocalHeight(height);
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();

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
                    // Sitting: the mesh is already sunk by SeatedVisualDrop; remember its standing place.
                    _visualLocal = _visual.localPosition + (_body.Seated ? Vector3.up * SeatedVisualDrop : Vector3.zero);
                }
            }
            _body.Grabbable = State == NpcState.Down || State == NpcState.Escaping;
        }

        private void OnDisable()
        {
            All.Remove(this);
            if (_body != null) _body.Impact -= OnImpact;
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
            switch (State)
            {
                case NpcState.Free: UpdateFree(); break;
                case NpcState.Down: UpdateDown(); break;
                case NpcState.CargoSeated: UpdateSeated(); break;
                case NpcState.Escaping: UpdateEscaping(); break;
            }
        }

        private void FixedUpdate()
        {
            if (State == NpcState.Down) FixedDown();
        }

        private void LateUpdate() => _face?.Apply();

        // ---------- Free ----------

        private void UpdateFree()
        {
            if (VanHits())
            {
                KnockOver(VanPush());
                return;
            }
            if (Scared(out Vector3 from))
            {
                _threat = from;
                _fleeUntil = Time.time + CalmAfter;
            }

            bool fleeing = Time.time < _fleeUntil;
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

            Play(fleeing ? "Run" : "Idle");
            Face.Set("Surprised", fleeing ? 100f : 0f);
            Face.Set("Worried", fleeing ? 70f : 0f);
            if (!fleeing) Face.TickBlink();
        }

        private bool VanHits() => _van != null && Mathf.Abs(_van.SpeedKmh) > KnockSpeedKmh &&
                                  Flat(_van.transform.position - transform.position).magnitude < 2.6f;

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
            // Re-stunning one that is already caught (lying, sitting, escaping) works but costs Condition (never kills).
            if (State != NpcState.Free) Condition = Mathf.Max(0f, Condition - ReStunConditionCost);
            // A running NPC falls on in its run; a lying or sitting one keeps the velocity it has (e.g. the van's).
            if (State == NpcState.Free) GoDown(_controller.enabled ? _controller.velocity : Vector3.zero, Vector3.zero);
            else GoDown(null, null);
            ExtendStun(weapon.Duration(zone));
            Vector3 push = Flat(point - from);
            if (push.sqrMagnitude < 1e-4f) push = Flat(-transform.forward);
            if (push.sqrMagnitude < 1e-4f) push = Vector3.forward;
            _body.Push(push.normalized * HitImpulse, point);
        }

        /// <summary>Thrown by a vehicle (the van at speed, or jumping out of one): down with that velocity, stunned like a
        /// fist to the torso, and the body ignores the van for a moment so it is not born inside the bumper.</summary>
        public void KnockOver(Vector3 velocity)
        {
            GoDown(velocity, Random.onUnitSphere * 8f);
            ExtendStun(WeaponStun.Fist.Duration(HitZone.Torso));
            if (_van != null) _body.IgnoreFor(_van.GetComponentsInChildren<Collider>(), VanKnockIgnore);
            Face.Set("Surprised", 100f, 10000f);
        }

        // velocity / angularVelocity: set on the body; null keeps what an already active body has.
        private void GoDown(Vector3? velocity, Vector3? angularVelocity)
        {
            if (State == NpcState.Free)
            {
                _controller.enabled = false;
                SetTracker(false, false);
            }
            if (!_body.Active) _body.Activate(velocity ?? Vector3.zero, angularVelocity ?? Vector3.zero);
            else
            {
                if (_body.Seated) _body.SetSeated(false); // sitting in the van or escaping: down again where it is
                if (velocity.HasValue) _body.Rigidbody.linearVelocity = velocity.Value;
                if (angularVelocity.HasValue) _body.Rigidbody.angularVelocity = angularVelocity.Value;
            }
            SetVisualDrop(false);
            State = NpcState.Down;
            _body.Grabbable = true;
            _impactGraceUntil = Time.time + ImpactGrace; // its own fall is not a "drop"
            Play("Idle");
        }

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
            if (!_body.Active)
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
            Phase = PhaseNow();
            if (Phase == StunPhase.Out)
            {
                Face.Set("Surprised", 0f);
                Face.Set("Worried", 0f);
                Face.Set("Blink", 100f, 1500f);
            }
            else
            {
                Face.Set("Surprised", Time.time < _flashUntil ? 100f : 0f, 900f);
                Face.Set("Worried", 70f);
                Face.TickBlink();
            }
            Play("Idle");
        }

        private void FixedDown()
        {
            if (!_body.Active) return;
            float now = Time.time;
            if (Phase == StunPhase.Groggy)
            {
                if (now >= _nextKick)
                {
                    Kick();
                    _nextKick = now + Random.Range(KickInterval.x, KickInterval.y);
                }
                // In a cargo bay it crawls only for an open door (GreyboxVanCargo sets CrawlToward): crawling about inside
                // would keep it from ever resting long enough to count as loaded.
                if (now >= _nextCrawl && _body.HolderCount == 0 && _body.Grounded && (CrawlToward || CargoAt(Center) == null))
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
            if (_body.OnlyAnklesHeld && RelativeVelocity().magnitude > AnkleDragSpeed)
                Condition = Mathf.Max(0f, Condition - AnkleDragCost * Time.fixedDeltaTime);
        }

        // A leg lashes out across the body (and a bit up). It jerks whoever holds that ankle and can tear a hold loose:
        // half the time with one holder, a fifth with two, never with three (the draft: three hold it even when groggy).
        private void Kick()
        {
            GreyboxNpcBody.Point ankle = Random.value < 0.5f ? GreyboxNpcBody.Point.LeftAnkle : GreyboxNpcBody.Point.RightAnkle;
            Vector3 across = transform.TransformDirection(new Vector3(Random.Range(-1f, 1f), 0f, Random.Range(-1f, 1f)));
            if (across.sqrMagnitude < 1e-4f) across = transform.right;
            _body.Kick(ankle, (across.normalized + Vector3.up * 0.6f).normalized * KickImpulse);
            int holders = _body.HolderCount;
            if (holders > 0 && KickTearChance.Length > 0 &&
                Random.value < KickTearChance[Mathf.Min(holders, KickTearChance.Length - 1)])
                _body.Tear(ankle);
            _flashUntil = Time.time + 0.3f;
        }

        private void Crawl()
        {
            Vector3 away = CrawlToward ? Flat(CrawlGoal - Center) : Flat(Center - ThreatPosition());
            if (away.sqrMagnitude < 0.01f) away = Flat(transform.up); // head first
            if (away.sqrMagnitude < 0.01f) away = Vector3.forward;
            float force = CrawlToward ? EscapeCrawlForce : CrawlForce;
            _body.Scoot(away.normalized * (force * CrawlPeriod), CrawlHop);
        }

        // Body velocity against what it lies on: the cargo bay when loaded, otherwise the world.
        private Vector3 RelativeVelocity()
        {
            Rigidbody rb = _body.Rigidbody;
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
            _body.RevokeAll();
            StunLeft = 0f;
            // Lying in a cargo bay (loaded, or just dragged in): sits up there. Anywhere else: stands up and runs.
            if (!InCargo && _body.Active && CargoAt(Center) is VanCargoSpace space)
            {
                InCargo = true;
                Carrier = space;
            }
            if (InCargo && CarrierAlive && _body.Active)
            {
                SitInCargo();
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
            float yaw = facing.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(facing).eulerAngles.y : transform.eulerAngles.y;
            _body.Deactivate();
            _body.Grabbable = false;
            SetVisualDrop(false);
            Vector3 p = GroundPoint(centre, 1.5f);
            transform.SetPositionAndRotation(p, Quaternion.Euler(0f, yaw, 0f));
            _controller.enabled = true;
            IgnoreVan(_controller); // re-enabling recreates the shape, which drops ignore pairs
            _verticalSpeed = 0f;
            _threat = threat;
            _fleeUntil = Time.time + CalmAfter;
            State = NpcState.Free;
            Phase = StunPhase.None;
            StunLeft = 0f;
            InCargo = false;
            Carrier = null;
            CrawlToward = false;
            // Dragged far while down (or into the van and out): forget the old dry points, unless it woke up in the sea.
            SetTracker(true, !SeaReturnZone.InSea(p));
        }

        // ---------- In the van (driven by GreyboxVanCargo) ----------

        private void SitInCargo()
        {
            State = NpcState.CargoSeated;
            Phase = StunPhase.Awake;
            CrawlToward = false;
            _body.Grabbable = false;
            _body.SetSeated(true);
            SetVisualDrop(true);
            Play("Idle");
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
            Play("Idle");
        }

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
            Play("Run");
        }

        private bool LostCarrier() => !InCargo || !CarrierAlive || !Carrier.Contains(Center, LostCarrierMargin);

        // A script reload in Play mode drops Carrier ([NonSerialized] interface) but keeps InCargo: find the bay it is in
        // again. In none (or no body), it is no longer loaded, and the usual rules take over (a sitter gets out and runs).
        private void RecoverCarrier()
        {
            if (_body != null && _body.Active)
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
            Play("Run");
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
        }

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

        /// <summary>A short startled look (an escape that failed).</summary>
        public void Flash() => _flashUntil = Time.time + 0.5f;

        // No sitting clip yet: the standing mesh sinks into the floor so its head stays under the van roof.
        private void SetVisualDrop(bool drop)
        {
            if (_visual != null) _visual.localPosition = _visualLocal + (drop ? Vector3.down * SeatedVisualDrop : Vector3.zero);
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

        private void Play(string state)
        {
            if (_animator == null || _anim == state) return;
            _animator.CrossFadeInFixedTime(state, 0.15f);
            _anim = state;
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
