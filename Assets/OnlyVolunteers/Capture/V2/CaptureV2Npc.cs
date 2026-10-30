using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture, one NPC (spec §1-§5, §7): the slap (frozen in shock; the head whips along the swipe first, the
    /// body follows half a turn, then the ragdoll drops like a sack; a red handprint stays on the struck cheek for the
    /// mission, in the van too; full charge: a few spit drops), out cold for the knock-out ladder (5 / 3 / 2 / 1 s, x1.4
    /// fully charged) with X eyes, the tongue out and stars round the head; getting up he can be slapped or grabbed down
    /// again (Redrop),
    /// "huh?" 0.5 s before waking, waking in the hands with the escape meter, clinging to things nearby (§4: the hands
    /// yank him off), the E throw into the van (swing per grab, flight, landing in a seat, belt) and bouncing back from a
    /// full van. Runs before GreyboxNpc (order -10), whose stun timer, ragdoll and seated capsule it drives through their
    /// public state: OutShare 1 keeps him Out while knocked out; awake in the hands the stun is kept topped up (Groggy:
    /// NpcStruggle wriggles, GreyboxNpc kicks; kick tears off), so only the meter or a let-go wakes him. The physics part
    /// (carry poses, resist, the swing) is CaptureV2NpcMotor.</summary>
    [DefaultExecutionOrder(-10)]
    [RequireComponent(typeof(GreyboxNpc))]
    public sealed class CaptureV2Npc : MonoBehaviour
    {
        public enum Mode : byte { Idle, Frozen, Spinning, KnockedOut, Awake, Clinging, Swing, Flight, Seated }
        private enum Face : byte { None, Shocked, Out, Huh, Awake, Cling, Nooo, Flight, Land, Smacked }

        [System.NonSerialized] public CaptureV2Rig Rig;
        public Mode Current { get; private set; }
        public GrabPointV2 Grab { get; private set; }
        public int GrabPart { get; private set; } = -1;
        public float Meter { get; private set; }
        public float YankBar { get; private set; }
        public int SlapCount { get; private set; }
        public float LastKnockOut { get; private set; }
        public int ReservedSeat { get; private set; } = -1;
        public bool Busy => Current == Mode.Swing || Current == Mode.Flight;
        public bool LastBounced { get; private set; }
        public float LastBounceTime { get; private set; } = -10f;
        public int LandingVariant { get; private set; }
        public string LastFace { get; private set; } = "";
        public Vector3 ClingAnchor { get; private set; }
        public Collider ClingCollider { get; private set; }
        // plain counters for the test and the notes
        public int Escapes, Pops, Seatings, Bounces, Clings, Slaps;
        /// <summary>Handprints on his cheeks (0..2; they stay for the mission).</summary>
        public int Handprints { get; private set; }
        /// <summary>The struck cheek's handprint (tests: close-up shots), null before the first.</summary>
        public Transform LastHandprint { get; private set; }
        /// <summary>When the last smack landed (Time.time; tests).</summary>
        public float LastSmackTime { get; private set; } = -10f;
        public float HeadSnapNow { get; private set; }
        public bool BeltOn => _belt != null;
        public float SwingProgress => Current == Mode.Swing ? Mathf.Clamp01((Time.fixedTime - _swingStart) / Mathf.Max(0.05f, T.SwingSeconds)) : 0f;
        public ThrowStyleV2 ThrowStyle => _style;
        public int ThrowMirror => _mirror;

        private GreyboxNpc _npc;
        private NpcRagdoll _ragdoll;
        private Transform _visual;
        private float _outShare0, _impact0, _hitImpulse0;
        private float[] _tear0;
        private object _holder;
        private bool _wasHeld;
        private float _heldSince, _dragged;
        private Vector3 _lastPelvis;
        private float _lastSlap = -100f, _frozenUntil;
        private float _spinStart, _spinYaw0, _spinDir, _charge;
        private Vector3 _swipe;
        private bool _snapping;
        private int _printSides;
        private readonly List<(Transform t, Vector3 v, float end)> _spit = new();
        private Vector3 _smackFrom, _smackPoint;
        private HitZone _smackZone;
        private Face _face;
        private float _faceUntil;
        private Face _faceAfter;
        private float _nextClingCheck, _clingCooldownUntil;
        private ConfigurableJoint _joint;
        private int _lastYankFrame = -1;
        // throw
        private CaptureV2Van _van;
        private int _door;
        private ThrowStyleV2 _style;
        private int _mirror = 1;
        private Vector3 _origin, _fwd, _p0;
        private float _swingStart, _flightStart, _landAt, _beltAt;
        private Vector3 _flightTarget;
        private Vector3 _visBasePos;
        private Quaternion _visBaseRot;
        private bool _landAnim;
        private GameObject _belt;
        // KO face props
        private bool _faceKnown;
        private Vector3 _eyeL, _eyeR, _mouth, _fNormal = Vector3.forward, _fUp = Vector3.up, _fRight = Vector3.right; // head-bone frame, metres
        private float _eyeSize = 0.025f, _mouthWidth = 0.05f;
        private Transform _headBone, _props, _tongue;
        private GameObject _xEyes;
        private Transform _starsRoot;
        private readonly List<Transform> _stars = new();
        private float _propsShown;
        private static readonly Collider[] Overlap = new Collider[24];

        public GreyboxNpc Npc => _npc != null ? _npc : _npc = GetComponent<GreyboxNpc>();
        private NpcRagdoll Ragdoll => _ragdoll != null ? _ragdoll : _ragdoll = GetComponent<NpcRagdoll>();
        private CaptureV2Tuning T => Rig != null ? Rig.Tuning : CaptureV2Rig.Instance != null ? CaptureV2Rig.Instance.Tuning : Fallback;
        private static readonly CaptureV2Tuning Fallback = new();
        public bool Held => Npc.IsDown && Npc.PhysicalBody != null && Npc.PhysicalBody.Active && Npc.PhysicalBody.HolderCount > 0;
        public Vector3 Center => Npc.Center;

        private void Awake()
        {
            _npc = GetComponent<GreyboxNpc>();
            _outShare0 = _npc.OutShare;
            _impact0 = _npc.ImpactWakeSpeed;
            _hitImpulse0 = _npc.HitImpulse;
            _tear0 = _npc.KickTearChance != null ? (float[])_npc.KickTearChance.Clone() : new float[4];
            foreach (Animator a in GetComponentsInChildren<Animator>(true))
                if (a.transform != transform) { _visual = a.transform; break; }
        }

        private void OnEnable()
        {
            if (_npc == null) _npc = GetComponent<GreyboxNpc>();
            _npc.FaceOverride = ApplyFace;
        }

        private void OnDisable()
        {
            if (_npc != null && _npc.FaceOverride == (System.Action<GreyboxFace>)ApplyFace) _npc.FaceOverride = null;
            if (_npc != null) _npc.HeldInPlace = false;
            EndCling();
            ShowProps(false);
        }

        private void OnDestroy()
        {
            if (_starsRoot != null) Destroy(_starsRoot.gameObject);
            StopSnap();
            foreach (var s in _spit) if (s.t != null) Destroy(s.t.gameObject);
            _spit.Clear();
        }

        // ---------- the slap ----------

        /// <summary>The wind-up started at him: a standing NPC freezes in shock until the smack.</summary>
        public void Freeze(object who)
        {
            if (Current != Mode.Idle || Npc.State != NpcState.Free) return;
            Npc.HeldInPlace = true;
            Current = Mode.Frozen;
            _frozenUntil = Time.time + 0.8f; // the hands keep it up while the slap charges (HoldFrozen)
            SetFace(Face.Shocked, 0f, Face.None);
            LearnFace();
        }

        /// <summary>The slap is still charging at him: stay frozen a little longer.</summary>
        public void HoldFrozen() => _frozenUntil = Mathf.Max(_frozenUntil, Time.time + 0.6f);

        /// <summary>The smack lands; charge 0 (a click) .. 1 (LMB held ChargeMax). Standing: half a turn (a whole one fully
        /// charged, then he flies a little), then down as the ragdoll. Lying (out cold, awake in the hands, clinging: the
        /// slap on the hands): out cold again for the next step of the ladder. Out a bit longer when charged. False:
        /// nothing to slap.</summary>
        public bool Smack(object who, Vector3 from, Vector3 point, HitZone zone, float charge, Vector3 swipe = default)
        {
            if (Busy || Current == Mode.Seated || Current == Mode.Spinning) return false;
            Slaps++;
            _charge = Mathf.Clamp01(charge);
            swipe.y = 0f;
            if (swipe.sqrMagnitude < 1e-4f) swipe = Vector3.Cross(Vector3.up, Flat(point - from)); // no swipe given: across the blow
            _swipe = swipe.sqrMagnitude > 1e-4f ? swipe.normalized : transform.right;
            LastSmackTime = Time.time;
            if (Npc.State == NpcState.Free)
            {
                LearnFace();
                Npc.HeldInPlace = true;
                Current = Mode.Spinning;
                _spinStart = Time.time;
                _spinYaw0 = transform.eulerAngles.y;
                // positive yaw turns his face toward up x forward: the head whips (and the body turns) along the swipe
                _spinDir = Vector3.Dot(Vector3.Cross(Vector3.up, transform.forward), _swipe) >= 0f ? 1f : -1f;
                _smackFrom = from;
                _smackPoint = point;
                _smackZone = zone;
                SetFace(Face.Smacked, 0f, Face.None);
                StartSnap();
                AddHandprint();
                if (_charge >= 0.98f) Spit();
                return true;
            }
            if (Npc.State == NpcState.GettingUp)
            {
                // rising is no hiding place (Vadim 31.10): down again, out cold for the next step of the ladder
                LearnFace();
                KnockOut(from, point, zone, true);
                AddHandprint();
                if (_charge >= 0.98f) Spit();
                return Npc.IsDown;
            }
            if (!Npc.IsDown) return false;
            if (Current == Mode.Clinging) EndCling();
            KnockOut(from, point, zone, true);
            AddHandprint();
            SnapLyingHead();
            if (_charge >= 0.98f) Spit();
            return true;
        }

        /// <summary>LMB on him while he gets up and is still low: down again as the ragdoll, out cold for the next step of
        /// the ladder, so the hands can take him at once. False when he is not getting up.</summary>
        public bool Redrop(object who, Vector3 from, Vector3 swipe)
        {
            if (Npc.State != NpcState.GettingUp || Busy || Current == Mode.Seated) return false;
            _charge = 0f;
            LearnFace();
            KnockOut(from, Npc.Center, HitZone.Torso, true);
            Debug.Log($"[CaptureV2] {name}: grabbed while getting up, down again");
            return Npc.IsDown;
        }

        // ---------- the head whip, the handprint, the spit ----------

        private void StartSnap()
        {
            HeadSnapNow = 0f;
            if (_snapping || _headBone == null) return;
            _snapping = true;
            CaptureV2Juice.LateTick += HeadSnapLate;
        }

        private void StopSnap()
        {
            if (!_snapping) return;
            _snapping = false;
            CaptureV2Juice.LateTick -= HeadSnapLate;
        }

        // After his animator and everything else (CaptureV2Juice's LateUpdate): the head whips along the swipe a bit over
        // the top (ease-out-back) and tilts, the neck takes a share; it lets go as the body catches up with the turn.
        private void HeadSnapLate()
        {
            if (this == null || _headBone == null || Current != Mode.Spinning)
            {
                HeadSnapNow = 0f;
                StopSnap();
                return;
            }
            float t = Time.time - _spinStart;
            float body = Mathf.Clamp01((t - T.SpinDelay) / Mathf.Max(0.05f, T.SpinSeconds + 0.06f * _charge));
            float u = Mathf.Clamp01(t / Mathf.Max(0.01f, T.HeadSnapSeconds)) - 1f;
            float whip = 1f + 2.70158f * u * u * u + 1.70158f * u * u; // ease-out-back: ~10 % past, then back
            float deg = T.HeadSnapDegrees * (1f + 0.25f * _charge) * whip * (1f - 0.7f * body) * _spinDir;
            HeadSnapNow = deg;
            Transform neck = _headBone.parent;
            if (neck != null) neck.rotation = Quaternion.AngleAxis(deg * 0.35f, Vector3.up) * neck.rotation;
            _headBone.rotation = Quaternion.AngleAxis(deg * 0.65f, Vector3.up) * Quaternion.AngleAxis(-deg * 0.2f, transform.forward) * _headBone.rotation;
        }

        // A lying head turns away along the swipe (the ragdoll's own joints limit it).
        private void SnapLyingHead()
        {
            if (Ragdoll == null || !Ragdoll.Active || Ragdoll.Profile == null || _headBone == null) return;
            Rigidbody rb = Ragdoll.BodyOf(Ragdoll.Profile.IndexOf(Kind.Head));
            if (rb == null) return;
            Vector3 axis = Vector3.Cross(_headBone.rotation * _fNormal, _swipe);
            if (axis.sqrMagnitude > 1e-4f) rb.AddTorque(axis.normalized * 12f, ForceMode.VelocityChange);
        }

        /// <summary>The red handprint on the cheek the palm arrived at (once per cheek; it stays for the mission: under the
        /// head bone, so it rides the ragdoll and the seated figure alike).</summary>
        private void AddHandprint()
        {
            if (Rig == null) return;
            if (_props == null) BuildProps();
            if (_headBone == null || _props == null) return;
            Vector3 rightW = _headBone.rotation * _fRight;
            float side = Vector3.Dot(rightW, -_swipe) >= 0f ? 1f : -1f; // his right cheek faces where the palm came from
            int bit = side > 0f ? 1 : 2;
            if ((_printSides & bit) != 0) return;
            _printSides |= bit;
            Vector3 mid = (_eyeL + _eyeR) * 0.5f;
            float r = HeadRadius();
            Vector3 centre = mid - _fNormal * (r * 0.8f);
            const float yaw = 58f * Mathf.Deg2Rad;
            Vector3 dir = (_fNormal * Mathf.Cos(yaw) + _fRight * (side * Mathf.Sin(yaw)) - _fUp * 0.5f).normalized;
            Vector3 at = centre + dir * (r * PrintRadius + 0.003f);
            Vector3 up = (_fUp - _fNormal * 0.25f).normalized;
            Quaternion rot = Quaternion.LookRotation(dir, up) * Quaternion.Euler(0f, 0f, side * 12f);
            float size = Mathf.Clamp(r * 1.25f, 0.085f, 0.15f) / 0.1f;
            // the thumb (the mesh's +x) toward his nose on either cheek
            Transform print = CaptureV2Rig.Prop("v2 handprint", _props, Rig.HandprintMesh, Rig.Handprint, at, rot,
                new Vector3(side > 0f ? -size : size, size, size)).transform;
            LastHandprint = print;
            Handprints++;
            Debug.Log($"[CaptureV2] {name}: handprint on the {(side > 0f ? "right" : "left")} cheek (head r {r:0.000} m)");
        }

        /// <summary>How far out from the head centre the print sits, x head radius (tuned on the render).</summary>
        public static float PrintRadius = 1f;

        private float HeadRadius()
        {
            NpcRagdollProfile p = Ragdoll != null ? Ragdoll.Profile : null;
            int head = p != null ? p.IndexOf(Kind.Head) : -1;
            float r = head >= 0 && _headBone != null ? p.Parts[head].Radius * Mathf.Abs(_headBone.lossyScale.x) : 0.1f;
            return Mathf.Clamp(r, 0.06f, 0.2f);
        }

        // Full charge only: a few small spit drops out of the mouth along the swipe.
        private void Spit()
        {
            if (Rig == null || _headBone == null) return;
            Vector3 mouth = _headBone.position + _headBone.rotation * _mouth;
            for (int i = 0; i < 4; i++)
            {
                GameObject go = CaptureV2Rig.Prop("v2 spit", null, Rig.Ball, Rig.Spit, mouth, Quaternion.identity, Vector3.one * Random.Range(0.012f, 0.02f));
                Vector3 v = _swipe * Random.Range(1.4f, 2.6f) + Vector3.up * Random.Range(0.5f, 1.3f) + Random.insideUnitSphere * 0.45f;
                _spit.Add((go.transform, v, Time.time + Random.Range(0.3f, 0.45f)));
            }
        }

        private void TickSpit()
        {
            if (_spit.Count == 0) return;
            float dt = Time.deltaTime;
            for (int i = _spit.Count - 1; i >= 0; i--)
            {
                var s = _spit[i];
                if (s.t == null || Time.time >= s.end)
                {
                    if (s.t != null) Destroy(s.t.gameObject);
                    _spit.RemoveAt(i);
                    continue;
                }
                s.v += Physics.gravity * dt;
                s.t.position += s.v * dt;
                _spit[i] = s;
            }
        }

        private void Spin()
        {
            float u = Mathf.Clamp01((Time.time - _spinStart - T.SpinDelay) / Mathf.Max(0.05f, T.SpinSeconds + 0.06f * _charge));
            float e = 1f - (1f - u) * (1f - u);
            transform.rotation = Quaternion.Euler(0f, _spinYaw0 + _spinDir * (T.SpinDegrees + T.ChargeSpinExtra * _charge) * e, 0f);
            if (u < 1f) return;
            // down like a sack: the stock hit with a small push, then a twisting slump
            Npc.HeldInPlace = false;
            Npc.HitImpulse = T.SackImpulse;
            Npc.Hit(WeaponStun.Fist, _smackZone, _smackFrom, _smackPoint);
            Npc.HitImpulse = _hitImpulse0;
            if (!Npc.IsDown)
            {
                Current = Mode.Idle;
                return;
            }
            KnockOut(_smackFrom, _smackPoint, _smackZone, false);
            if (Ragdoll != null && Ragdoll.Active)
            {
                // a click: a twisting slump; fully charged: he flies a little along the smack before he drops
                Vector3 push = Flat(_smackPoint - _smackFrom);
                Vector3 along = push.sqrMagnitude > 1e-4f ? push.normalized : Vector3.zero;
                Ragdoll.SetVelocity(Vector3.down * (0.8f * (1f - _charge)) + Vector3.up * (T.ChargeFlyUp * _charge) +
                                    along * (0.5f + T.ChargeFlySpeed * _charge), Vector3.up * (_spinDir * (4f + 6f * _charge)));
            }
        }

        private void KnockOut(Vector3 from, Vector3 point, HitZone zone, bool hit)
        {
            if (hit)
            {
                Npc.HitImpulse = T.SackImpulse;
                Npc.Hit(WeaponStun.Fist, zone, from, point);
                Npc.HitImpulse = _hitImpulse0;
            }
            float ko = CaptureV2Rules.KnockOut(T, SlapCount) * (1f + T.ChargeKnockOutGain * _charge);
            SlapCount++;
            _lastSlap = Time.time;
            LastKnockOut = ko;
            Npc.OutShare = 1f;
            Npc.StunTotal = ko;
            Npc.StunLeft = ko;
            Npc.Phase = StunPhase.Out;
            Npc.ImpactWakeSpeed = 1000f;
            Npc.KickTearChance = new float[4];
            Current = Mode.KnockedOut;
            SetFace(Face.Out, 0f, Face.None);
            ShowProps(true);
            Debug.Log($"[CaptureV2] {name}: out cold {ko:0.0} s (slap {SlapCount} of this catch, charge {_charge:0.00})");
        }

        // ---------- out cold, awake in the hands, free again ----------

        private void TickKnockOut()
        {
            if (!Npc.IsDown) { EndCatch(); return; }
            float left = Npc.StunLeft;
            bool huh = left <= T.HuhBefore;
            SetFace(huh ? Face.Huh : Face.Out, 0f, Face.None);
            ShowProps(!huh);
            if (left - Time.deltaTime > 0f) return;
            if (Held) EnterAwake();
            else EndCatch(); // GreyboxNpc wakes him this frame: up and running
        }

        private void EnterAwake()
        {
            Current = Mode.Awake;
            Npc.OutShare = 0f;
            Npc.StunTotal = 9999f;
            Npc.StunLeft = 9999f;
            Npc.Phase = StunPhase.Groggy;
            ShowProps(false);
            SetFace(Face.Awake, 0f, Face.None);
            _nextClingCheck = Time.time + 1f;
            Debug.Log($"[CaptureV2] {name}: woke up in the hands ({CaptureV2Rules.Name(Grab)}), meter {Meter:0.00}");
        }

        private void TickAwake()
        {
            if (!Npc.IsDown) { EndCatch(); return; }
            if (!Held)
            {
                WakeNow(); // let go: he gets up and runs
                return;
            }
            Npc.StunLeft = Mathf.Max(Npc.StunLeft, 100f);
            Meter = Mathf.Clamp01(Meter + CaptureV2Rules.MeterRate(T, Grab, Time.time - _heldSince, _dragged) * Time.deltaTime);
            if (Meter >= 1f)
            {
                Escapes++;
                Debug.Log($"[CaptureV2] {name}: broke free after {Time.time - _heldSince:0.0} s held, {_dragged:0.0} m dragged");
                Sfx.PlayAt(SfxIds.NpcScream, Center);
                WakeNow();
                return;
            }
            if (T.AutoCling && Time.time >= _nextClingCheck)
            {
                _nextClingCheck = Time.time + T.ClingCheckEvery;
                if (Time.time >= _clingCooldownUntil && Random.value < T.ClingChance) TryCling(null);
            }
        }

        private void WakeNow()
        {
            Npc.StunLeft = 0.0001f;
            EndCatch();
        }

        // Back to a plain NPC (woke up, escaped, or something else took over); GreyboxNpc's own values come back.
        private void EndCatch()
        {
            EndCling();
            ShowProps(false);
            Npc.OutShare = _outShare0;
            Npc.ImpactWakeSpeed = _impact0;
            Npc.KickTearChance = (float[])_tear0.Clone();
            Npc.HeldInPlace = false;
            if (Current != Mode.Seated) Current = Mode.Idle;
            Meter = 0f;
            YankBar = 0f;
            _face = Face.None;
        }

        private void TrackHold()
        {
            bool held = Held;
            if (held)
            {
                Vector3 pelvis = Npc.PhysicalBody.Landmark(NpcLandmark.Pelvis);
                if (!_wasHeld)
                {
                    _heldSince = Time.time;
                    _dragged = 0f;
                }
                else _dragged += Flat(pelvis - _lastPelvis).magnitude;
                _lastPelvis = pelvis;
            }
            _wasHeld = held;
        }

        public void OnGrabbed(object who, GrabPointV2 point, int part)
        {
            _holder = who;
            Grab = point;
            GrabPart = part;
            Debug.Log($"[CaptureV2] {name}: grabbed by the {CaptureV2Rules.Name(point)} (part {part})");
        }

        public void OnReleased(object who)
        {
            if (ReferenceEquals(_holder, who)) _holder = null;
        }

        // ---------- cling and yank (§4) ----------

        /// <summary>Test hook and the auto check: he grabs 'anchor' (null: whatever is in reach of a free hand).</summary>
        public bool TryCling(Collider anchor)
        {
            if (Current != Mode.Awake || Ragdoll == null || !Ragdoll.Active) return false;
            NpcRagdollProfile p = Ragdoll.Profile;
            Vector3 groundBelow = Npc.PhysicalBody.Landmark(NpcLandmark.Pelvis);
            Collider ground = Physics.Raycast(groundBelow + Vector3.up * 0.3f, Vector3.down, out RaycastHit g, 2f, ~OvLayers.NpcMask & OvLayers.ShootMask, QueryTriggerInteraction.Ignore) ? g.collider : null;
            float floorY = ground != null ? g.point.y : groundBelow.y - 0.2f;
            float best = float.MaxValue;
            int bestPart = -1;
            Collider bestCollider = null;
            Vector3 bestPoint = Vector3.zero;
            for (int s = 0; s < 2; s++)
            {
                int fore = p.IndexOf(Kind.ForeArm, (NpcSide)s);
                if (fore < 0 || PartHeld(fore) || PartHeld(p.Parts[fore].Parent)) continue;
                Vector3 hand = HandEnd(fore);
                if (anchor != null)
                {
                    Vector3 c = Closest(anchor, hand);
                    float d = Vector3.Distance(c, hand);
                    if (d < best) { best = d; bestPart = fore; bestCollider = anchor; bestPoint = c; }
                    continue;
                }
                int n = Physics.OverlapSphereNonAlloc(hand, T.ClingReach, Overlap, OvLayers.ShootMask & ~OvLayers.NpcMask, QueryTriggerInteraction.Ignore);
                for (int i = 0; i < n; i++)
                {
                    Collider c = Overlap[i];
                    Overlap[i] = null;
                    if (c == null || c == ground || c is TerrainCollider || c.transform.IsChildOf(transform)) continue;
                    if (c.bounds.size.y < 0.45f && !(c is CharacterController)) continue; // flat things: nothing to hold on to
                    Vector3 cp = Closest(c, hand);
                    if (cp.y < floorY + 0.15f) continue;
                    float d = Vector3.Distance(cp, hand);
                    if (d < best) { best = d; bestPart = fore; bestCollider = c; bestPoint = cp; }
                }
            }
            if (bestPart < 0) return false;
            StartCling(bestCollider, bestPoint, bestPart);
            return true;
        }

        private bool PartHeld(int part)
        {
            if (part < 0 || Ragdoll == null) return false;
            foreach (NpcRagdoll.Claim c in Ragdoll.Claims) if (c.Holder != null && c.Part == part) return true;
            return false;
        }

        private Vector3 HandEnd(int fore)
        {
            Ragdoll.CapsuleSegment(fore, out Vector3 a, out Vector3 b, out float r);
            Rigidbody parent = Ragdoll.BodyOf(Ragdoll.Profile.Parts[fore].Parent);
            Vector3 elbow = parent != null ? parent.position : a;
            return (Vector3.Distance(a, elbow) > Vector3.Distance(b, elbow) ? a : b);
        }

        private static Vector3 Closest(Collider c, Vector3 p) =>
            c is MeshCollider mc && !mc.convex ? c.ClosestPointOnBounds(p) : c is TerrainCollider ? p : c.ClosestPoint(p);

        private void StartCling(Collider anchor, Vector3 point, int part)
        {
            Rigidbody hand = Ragdoll.BodyOf(part);
            if (hand == null) return;
            Vector3 end = HandEnd(part);
            _joint = hand.gameObject.AddComponent<ConfigurableJoint>();
            _joint.autoConfigureConnectedAnchor = false;
            _joint.anchor = hand.transform.InverseTransformPoint(end);
            Rigidbody other = anchor != null ? anchor.attachedRigidbody : null;
            _joint.connectedBody = other;
            _joint.connectedAnchor = other != null ? other.transform.InverseTransformPoint(point) : point;
            _joint.xMotion = _joint.yMotion = _joint.zMotion = ConfigurableJointMotion.Free;
            var grip = new JointDrive { positionSpring = 4000f, positionDamper = 90f, maximumForce = 2600f };
            _joint.xDrive = _joint.yDrive = _joint.zDrive = grip;
            _joint.targetPosition = Vector3.zero;
            _joint.enableCollision = false;
            ClingAnchor = point;
            ClingCollider = anchor;
            YankBar = 0f;
            Clings++;
            Current = Mode.Clinging;
            SetFace(Face.Cling, 0f, Face.None);
            Sfx.PlayAt(SfxIds.NpcHurt, Center, 0.8f);
            Debug.Log($"[CaptureV2] {name}: clings to {(anchor != null ? anchor.name : "?")} at {point}");
        }

        private void EndCling()
        {
            if (_joint != null) Destroy(_joint);
            _joint = null;
            ClingCollider = null;
        }

        /// <summary>One holder's yank this frame: degrees per second of mouse along the arrow (away from the anchor). Phase 3:
        /// the holders' shares add up.</summary>
        public void AddYank(object who, float alongDegPerSecond, float dt)
        {
            if (Current != Mode.Clinging || dt <= 0f) return;
            YankBar = CaptureV2Rules.YankBar(T, YankBar, alongDegPerSecond, dt);
            _lastYankFrame = Time.frameCount;
        }

        private void TickCling()
        {
            if (!Npc.IsDown) { EndCatch(); return; }
            if (!Held || _joint == null)
            {
                EndCling();
                Current = Mode.Awake;
                return;
            }
            Npc.StunLeft = Mathf.Max(Npc.StunLeft, 100f);
            if (_lastYankFrame != Time.frameCount && _lastYankFrame != Time.frameCount - 1)
                YankBar = CaptureV2Rules.YankBar(T, YankBar, 0f, Time.deltaTime);
            if (YankBar >= 1f) TearOff();
        }

        private void TearOff()
        {
            Pops++;
            Vector3 away = Flat(Center - ClingAnchor);
            away = away.sqrMagnitude > 1e-4f ? away.normalized : -transform.forward;
            Transform hand = _joint != null ? _joint.transform : null;
            EndCling();
            if (Ragdoll != null && Ragdoll.Active)
                for (int i = 0; i < Ragdoll.PartCount; i++)
                {
                    Rigidbody rb = Ragdoll.BodyOf(i);
                    if (rb != null) rb.linearVelocity += away * T.PopNpcSpeed + Vector3.up * 1.2f;
                }
            CaptureV2Sounds.Play(CaptureV2Sounds.Pop, ClingAnchor, 1f);
            Sfx.PlayAt(SfxIds.NpcHurt, Center);
            SetFace(Face.Nooo, 1.3f, Face.Awake);
            Current = Mode.Awake;
            YankBar = 0f;
            _clingCooldownUntil = Time.time + T.ClingCooldown;
            // sometimes a piece of what he held stays in his hand
            if (hand != null && Rig != null && Random.value < 0.35f)
            {
                GameObject piece = CaptureV2Rig.Prop("v2 torn piece", hand, Rig.Box, Rig.Strap, Vector3.zero, Quaternion.Euler(20f, 0f, 70f), Vector3.one);
                piece.transform.localScale = Div(new Vector3(0.05f, 0.05f, 0.32f), hand.lossyScale);
                Destroy(piece, 4f);
            }
            Debug.Log($"[CaptureV2] {name}: POP, torn off");
        }

        // ---------- the throw (§5) ----------

        public bool BeginThrow(CaptureV2Hands hands, CaptureV2Van van, int door)
        {
            if (!Npc.IsDown || Busy || Current == Mode.Seated || Ragdoll == null || !Ragdoll.Active) return false;
            NpcRagdollProfile p = Ragdoll.Profile;
            if (GrabPart < 0 || Ragdoll.BodyOf(GrabPart) == null) GrabPart = p.IndexOf(Kind.Chest);
            if (Ragdoll.BodyOf(GrabPart) == null) return false;
            EndCling();
            _van = van;
            _door = door;
            ReservedSeat = van.FreeSeat(door);
            if (ReservedSeat >= 0 && !van.Reserve(ReservedSeat, Npc)) ReservedSeat = -1;
            _style = CaptureV2Rules.Style(Grab);
            _mirror = CaptureV2Rules.IsLeft(Grab) ? -1 : 1;
            _origin = hands.Feet;
            _fwd = Flat(van.DoorwayWorld(door, 0.7f) - _origin);
            _fwd = _fwd.sqrMagnitude > 1e-4f ? _fwd.normalized : Flat(hands.transform.forward).normalized;
            _p0 = ToThrow(Ragdoll.BodyOf(GrabPart).position);
            _swingStart = Time.fixedTime;
            Current = Mode.Swing;
            Npc.OutShare = 1f;
            Npc.StunTotal = 5f;
            Npc.StunLeft = 5f;
            Npc.Phase = StunPhase.Out;
            Npc.ImpactWakeSpeed = 1000f;
            ShowProps(false);
            SetFace(Face.Flight, 0f, Face.None);
            LastBounced = false;
            Debug.Log($"[CaptureV2] {name}: throw ({_style}{(_mirror < 0 ? ", left" : "")}) through door {door}, seat {ReservedSeat}");
            return true;
        }

        private Vector3 ToThrow(Vector3 world)
        {
            Vector3 d = world - _origin;
            Vector3 right = Vector3.Cross(Vector3.up, _fwd);
            return new Vector3(Vector3.Dot(d, right), d.y, Vector3.Dot(d, _fwd));
        }

        private Vector3 FromThrow(Vector3 local)
        {
            Vector3 right = Vector3.Cross(Vector3.up, _fwd);
            return _origin + right * local.x + Vector3.up * local.y + _fwd * local.z;
        }

        /// <summary>Where the hand carries the held part at swing progress u (0..1), world.</summary>
        public Vector3 SwingPoint(float u)
        {
            u = Mathf.Clamp01(u);
            Vector3 p0 = _p0;
            switch (_style)
            {
                case ThrowStyleV2.OverHead:
                {
                    // up over the shoulder behind the head, then over and forward, head first
                    var c = new Vector3(0.1f * _mirror, 2.75f, -0.85f);
                    var e = new Vector3(0f, 2.05f, 0.95f);
                    float w = u;
                    Vector3 a = Vector3.Lerp(p0, c, w), b = Vector3.Lerp(c, e, w);
                    return FromThrow(Vector3.Lerp(a, b, w));
                }
                default:
                {
                    // round the player: half a hammer-thrower turn (a leg) or a full spin (an arm), let go on the side
                    // moving toward the door
                    bool spin = _style == ThrowStyleV2.Spin;
                    float r = spin ? 1.0f : 1.25f, h = spin ? 1.15f : 1.0f;
                    Vector3 m = new(p0.x * _mirror, p0.y, p0.z); // mirrored: the left spin is the right one seen in a mirror
                    float a0 = Mathf.Atan2(m.z, m.x), a1 = 0f;
                    while (a1 - a0 < (spin ? 2f * Mathf.PI : Mathf.PI)) a1 += 2f * Mathf.PI;
                    float ease = Mathf.Pow(u, 1.5f);
                    float a = Mathf.Lerp(a0, a1, ease);
                    float rr = Mathf.Lerp(Mathf.Max(0.5f, new Vector2(m.x, m.z).magnitude), r, Mathf.Clamp01(u * 3f));
                    var local = new Vector3(Mathf.Cos(a) * rr * _mirror, Mathf.Lerp(p0.y, h, Mathf.Clamp01(u * 2f)), Mathf.Sin(a) * rr);
                    return FromThrow(local);
                }
            }
        }

        /// <summary>The swing is over (CaptureV2NpcMotor, physics step): let go toward the doorway. Seats free: into the bay
        /// (a straight, a flip or a ceiling landing); full: at the door frame, to bounce back.</summary>
        public void Release()
        {
            if (Current != Mode.Swing || Ragdoll == null || !Ragdoll.Active) return;
            Vector3 com = Ragdoll.CenterOfMass;
            Vector3 outward = _van.Outward(_door);
            Vector3 inside = _van.DoorwayWorld(_door, 0.65f) - outward * 0.45f;
            LandingVariant = Random.Range(0, 3);
            if (ReservedSeat >= 0)
            {
                Vector3 seat = _van.SeatWorld(ReservedSeat) + Vector3.up * 0.55f;
                _flightTarget = inside + (seat - inside) * 0.35f;
                if (LandingVariant == 2) _flightTarget.y = _van.DoorwayWorld(_door, 0f).y + _van.CeilingAbove(0f) - 0.35f;
            }
            else _flightTarget = _van.DoorwayWorld(_door, 0.8f) - outward * 0.1f;
            float time = Mathf.Max(0.12f, T.FlightSeconds);
            Vector3 v0 = (_flightTarget - com) / time - 0.5f * time * Physics.gravity;
            Vector3 roll = Vector3.Cross(Vector3.up, Flat(v0));
            roll = roll.sqrMagnitude > 1e-4f ? roll.normalized : Vector3.right;
            Vector3 w = roll * (LandingVariant == 1 ? 13f : 7f) + Vector3.up * Random.Range(-2f, 2f);
            for (int i = 0; i < Ragdoll.PartCount; i++)
            {
                Rigidbody rb = Ragdoll.BodyOf(i);
                if (rb == null) continue;
                rb.linearVelocity = v0 + Vector3.Cross(w, rb.worldCenterOfMass - com);
                rb.angularVelocity = w;
            }
            Ragdoll.IgnoreFor(_van.GetComponentsInChildren<Collider>(), time + 0.6f);
            Current = Mode.Flight;
            _flightStart = Time.time;
            CaptureV2Juice.HitStop(T.ThrowHitStop);
            CaptureV2Juice.Kick(-T.ThrowKick, 0f, _mirror * 1.5f);
            Sfx.PlayAt(SfxIds.NpcScream, com);
        }

        private void TickFlight()
        {
            if (Ragdoll == null || !Ragdoll.Active) { EndCatch(); return; }
            Vector3 com = Ragdoll.CenterOfMass;
            float t = Time.time - _flightStart;
            Vector3 outward = _van.Outward(_door);
            float depth = Vector3.Dot(com - _van.DoorwayWorld(_door, 0f), -outward);
            bool arrived = ReservedSeat >= 0 ? (depth >= 0.3f && t > 0.08f) || t >= T.FlightSeconds + 0.1f
                                             : depth >= -0.1f || Vector3.Distance(com, _flightTarget) < 0.35f || t >= T.FlightSeconds;
            if (!arrived) return;
            if (ReservedSeat >= 0) Land();
            else Bounce();
        }

        private void Land()
        {
            Vector3 seat = _van.SeatWorld(ReservedSeat);
            Quaternion rotation = _van.SeatRotation(ReservedSeat);
            if (LandingVariant == 2) CaptureV2Sounds.Play(CaptureV2Sounds.Bonk, _flightTarget, 1f);
            if (!Npc.SeatV2(_van.Space, seat, rotation))
            {
                _van.Free(Npc);
                ReservedSeat = -1;
                Bounce();
                return;
            }
            EndCatch();
            Npc.SeatBelted = true;
            Seatings++;
            Current = Mode.Seated;
            _landAt = Time.time;
            _beltAt = Time.time + T.BeltDelay;
            SlapCount = 0;
            if (_visual != null)
            {
                _visual.GetLocalPositionAndRotation(out _visBasePos, out _visBaseRot);
                _landAnim = true;
            }
            int face = Random.Range(0, LandFaces.Length);
            LastFace = LandFaces[face].name;
            _landFace = face;
            SetFace(Face.Land, 2.5f, Face.None);
            Vector3 side = -_van.Outward(_door);
            _van.Dip(seat + Vector3.up * 0.5f, side, T.VanDip, T.VanRock);
            CaptureV2Sounds.Play(CaptureV2Sounds.Boom, seat + Vector3.up * 0.5f, 1f);
            Sfx.PlayAt(SfxIds.VanHitMetalHeavy, seat + Vector3.up * 0.5f);
            Sfx.PlayAt(SfxIds.ThudVan, seat + Vector3.up * 0.3f);
            CaptureV2Juice.Shake(1.1f, 0.3f);
            Debug.Log($"[CaptureV2] {name}: landed in seat {ReservedSeat} ({(LandingVariant == 0 ? "straight" : LandingVariant == 1 ? "upside down, flips" : "ceiling, drops")}), face {LastFace}");
        }

        private void Bounce()
        {
            Bounces++;
            LastBounced = true;
            LastBounceTime = Time.time;
            ReservedSeat = -1;
            Vector3 outward = _van.Outward(_door);
            Vector3 side = Vector3.Cross(Vector3.up, outward) * Random.Range(-1f, 1f);
            if (Ragdoll != null && Ragdoll.Active)
            {
                for (int i = 0; i < Ragdoll.PartCount; i++)
                {
                    Rigidbody rb = Ragdoll.BodyOf(i);
                    if (rb == null) continue;
                    rb.linearVelocity = outward * 4.5f + Vector3.up * 2.8f + side;
                    rb.angularVelocity = Random.onUnitSphere * 6f;
                }
                Ragdoll.IgnoreFor(_van.GetComponentsInChildren<Collider>(), 0.45f);
            }
            CaptureV2Sounds.Play(CaptureV2Sounds.Boing, _flightTarget, 1f);
            _van.Dip(_flightTarget, outward, T.VanDip * 0.4f, T.VanRock * 0.5f);
            Npc.OutShare = 1f;
            Npc.StunTotal = 1.6f;
            Npc.StunLeft = 1.6f;
            Current = Mode.KnockedOut;
            SetFace(Face.Out, 0f, Face.None);
            ShowProps(true);
            Debug.Log($"[CaptureV2] {name}: no free seat, bounced back");
        }

        private void TickSeated()
        {
            if (Npc.State != NpcState.CargoSeated || !Npc.InCargo)
            {
                if (_belt != null) Destroy(_belt);
                _belt = null;
                if (_van != null) _van.Free(Npc);
                Npc.SeatBelted = false;
                ReservedSeat = -1;
                Current = Mode.Idle;
                _landAnim = false;
                return;
            }
            if (_belt == null && Time.time >= _beltAt)
            {
                MakeBelt();
                CaptureV2Sounds.Play(CaptureV2Sounds.Clack, Center, 1f);
            }
        }

        private void MakeBelt()
        {
            if (Rig == null) return;
            NpcRagdollProfile p = Ragdoll != null ? Ragdoll.Profile : null;
            Transform hips = p != null ? Ragdoll.BoneOf(p.IndexOf(Kind.Pelvis)) : null;
            Transform parent = hips != null ? hips : transform;
            var root = new GameObject("v2 seat belt").transform;
            root.SetParent(parent, false);
            root.localScale = Div(Vector3.one, parent.lossyScale);
            Vector3 lap = (hips != null ? hips.position : transform.position + Vector3.up * 0.3f) + transform.forward * 0.13f + Vector3.up * 0.04f;
            root.SetPositionAndRotation(lap, transform.rotation);
            CaptureV2Rig.Prop("strap", root, Rig.Box, Rig.Strap, Vector3.zero, Quaternion.identity, new Vector3(0.52f, 0.06f, 0.03f));
            CaptureV2Rig.Prop("buckle", root, Rig.Box, Rig.Buckle, new Vector3(0.02f, 0f, 0.012f), Quaternion.identity, new Vector3(0.075f, 0.055f, 0.03f));
            // the strap's ends run back to the floor behind him (fixed to the wall rail)
            CaptureV2Rig.Prop("strap L", root, Rig.Box, Rig.Strap, new Vector3(-0.27f, -0.12f, -0.12f), Quaternion.Euler(-55f, 0f, 0f), new Vector3(0.05f, 0.03f, 0.3f));
            CaptureV2Rig.Prop("strap R", root, Rig.Box, Rig.Strap, new Vector3(0.27f, -0.12f, -0.12f), Quaternion.Euler(-55f, 0f, 0f), new Vector3(0.05f, 0.03f, 0.3f));
            _belt = root.gameObject;
        }

        // ---------- faces (Blink, Surprised, Worried, Happy) ----------

        private static readonly (string name, float blink, float surprised, float worried, float happy)[] LandFaces =
        {
            ("WTF", 0f, 100f, 60f, 0f),
            ("panic", 0f, 70f, 100f, 0f),
            ("resigned", 55f, 0f, 90f, 0f),
            ("dumb grin", 0f, 50f, 0f, 100f),
            ("frozen stare", 0f, 100f, 0f, 0f),
            ("sob", 80f, 20f, 100f, 0f),
        };
        private int _landFace;

        private void SetFace(Face face, float seconds, Face after)
        {
            _face = face;
            _faceUntil = seconds > 0f ? Time.time + seconds : 0f;
            _faceAfter = after;
        }

        // GreyboxNpc.LateUpdate, after its own faces, before the weights are written.
        private void ApplyFace(GreyboxFace f)
        {
            Face m = _face;
            if (_faceUntil > 0f && Time.time > _faceUntil)
            {
                _face = m = _faceAfter;
                _faceUntil = 0f;
            }
            const float snap = 1e6f;
            switch (m)
            {
                case Face.Shocked: Set(f, 0f, 100f, 35f, 0f, snap); break;
                case Face.Smacked: Set(f, 75f, 100f, 45f, 0f, snap); break; // eyes squeezed, mouth popped open
                case Face.Out: Set(f, 100f, 55f, 0f, 0f, snap); break;
                case Face.Huh: Set(f, 30f, 45f, 55f, 0f, 400f); break;
                case Face.Awake: f.Set("Worried", 100f, 600f); break;
                case Face.Cling: Set(f, 35f, 0f, 100f, 0f, 800f); break;
                case Face.Nooo: Set(f, 0f, 100f, 100f, 0f, snap); break;
                case Face.Flight: Set(f, 0f, 100f, 80f, 0f, snap); break;
                case Face.Land:
                {
                    var l = LandFaces[Mathf.Clamp(_landFace, 0, LandFaces.Length - 1)];
                    Set(f, l.blink, l.surprised, l.worried, l.happy, snap);
                    break;
                }
            }
        }

        private static void Set(GreyboxFace f, float blink, float surprised, float worried, float happy, float speed)
        {
            f.Set("Blink", blink, speed);
            f.Set("Surprised", surprised, speed);
            f.Set("Worried", worried, speed);
            f.Set("Happy", happy, speed);
        }

        // ---------- the KO props: X eyes, the tongue out to the side, stars round the head ----------

        // Where the eyes and the mouth are, in the head bone's frame (metres): baked from the face mesh's Blink and Happy
        // shapes while he stands (SkinnedMeshRenderer.BakeMesh), else estimated from the ragdoll's head capsule.
        private void LearnFace()
        {
            if (_faceKnown || Ragdoll == null || Ragdoll.Profile == null) return;
            NpcRagdollProfile p = Ragdoll.Profile;
            int head = p.IndexOf(Kind.Head);
            _headBone = head >= 0 ? Ragdoll.BoneOf(head) : null;
            if (_headBone == null) return;
            _faceKnown = true;
            if (BakeFace()) return;
            // estimate: the head capsule, the character's front and up in the bone's frame (its Idle pose)
            NpcRagdollProfile.Part hp = p.Parts[head];
            Quaternion inv = Quaternion.Inverse(hp.PoseRotation);
            _fNormal = inv * Vector3.forward;
            _fUp = inv * Vector3.up;
            _fRight = inv * Vector3.right;
            Vector3 s = _headBone.lossyScale;
            Vector3 c = Vector3.Scale(hp.Center, s);
            float r = hp.Radius * Mathf.Abs(s.x);
            _eyeL = c + _fNormal * (r * 0.95f) + _fUp * (r * 0.2f) - _fRight * (r * 0.36f);
            _eyeR = c + _fNormal * (r * 0.95f) + _fUp * (r * 0.2f) + _fRight * (r * 0.36f);
            _mouth = c + _fNormal * (r * 0.9f) - _fUp * (r * 0.38f);
            _eyeSize = Mathf.Clamp(r * 0.2f, 0.015f, 0.04f);
            _mouthWidth = r * 0.5f;
            Debug.Log($"[CaptureV2] {name}: face props placed from the head capsule (no face mesh bake)");
        }

        private bool BakeFace()
        {
            SkinnedMeshRenderer face = null;
            foreach (SkinnedMeshRenderer r in GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (r.name == "Face" || r.name == "Face_LOD0") { face = r; break; }
            if (face == null || face.sharedMesh == null) return false;
            int blink = face.sharedMesh.GetBlendShapeIndex("Blink");
            int happy = face.sharedMesh.GetBlendShapeIndex("Happy");
            if (blink < 0) return false;
            var a = new Mesh();
            var b = new Mesh();
            var h = new Mesh();
            try
            {
                float wb = face.GetBlendShapeWeight(blink), wh = happy >= 0 ? face.GetBlendShapeWeight(happy) : 0f;
                face.SetBlendShapeWeight(blink, 0f);
                if (happy >= 0) face.SetBlendShapeWeight(happy, 0f);
                face.BakeMesh(a, true);
                face.SetBlendShapeWeight(blink, 100f);
                face.BakeMesh(b, true);
                face.SetBlendShapeWeight(blink, 0f);
                if (happy >= 0)
                {
                    face.SetBlendShapeWeight(happy, 100f);
                    face.BakeMesh(h, true);
                    face.SetBlendShapeWeight(happy, wh);
                }
                face.SetBlendShapeWeight(blink, wb);
                Vector3[] va = a.vertices, vb = b.vertices, vh = happy >= 0 ? h.vertices : null;
                if (va.Length == 0 || va.Length != vb.Length) return false;
                // two candidate spaces for the baked vertices; the right one puts the eyes next to the head bone
                Matrix4x4 m1 = Matrix4x4.TRS(face.transform.position, face.transform.rotation, Vector3.one);
                Matrix4x4 m2 = face.transform.localToWorldMatrix;
                List<Vector3> eyes = Changed(va, vb);
                if (eyes.Count < 4) return false;
                Vector3 c1 = m1.MultiplyPoint3x4(Mean(eyes)), c2 = m2.MultiplyPoint3x4(Mean(eyes));
                Matrix4x4 m = Vector3.Distance(c1, _headBone.position) <= Vector3.Distance(c2, _headBone.position) ? m1 : m2;
                Vector3 centre = m.MultiplyPoint3x4(Mean(eyes));
                if (Vector3.Distance(centre, _headBone.position) > 0.7f) return false;
                Vector3 right = transform.right, up = Vector3.up, fwd = transform.forward;
                var left = new List<Vector3>();
                var rightEye = new List<Vector3>();
                foreach (Vector3 v in eyes)
                {
                    Vector3 w = m.MultiplyPoint3x4(v);
                    (Vector3.Dot(w - centre, right) < 0f ? left : rightEye).Add(w);
                }
                Vector3 el = left.Count > 0 ? Mean(left) : centre - right * 0.03f;
                Vector3 er = rightEye.Count > 0 ? Mean(rightEye) : centre + right * 0.03f;
                float size = 0f;
                foreach (Vector3 v in left) size += Vector3.Distance(v, el);
                size = left.Count > 0 ? size / left.Count : 0.02f;
                Vector3 mouth = centre - up * 0.07f;
                float mouthWidth = 0.05f;
                if (vh != null && vh.Length == va.Length)
                {
                    List<Vector3> moved = Changed(va, vh);
                    var below = new List<Vector3>();
                    foreach (Vector3 v in moved)
                    {
                        Vector3 w = m.MultiplyPoint3x4(v);
                        if (Vector3.Dot(w - centre, up) < -0.015f) below.Add(w);
                    }
                    if (below.Count >= 3)
                    {
                        mouth = Mean(below);
                        float lo = float.MaxValue, hi = float.MinValue;
                        foreach (Vector3 w in below) { float x = Vector3.Dot(w - mouth, right); lo = Mathf.Min(lo, x); hi = Mathf.Max(hi, x); }
                        mouthWidth = Mathf.Clamp(hi - lo, 0.02f, 0.12f);
                    }
                }
                Quaternion toBone = Quaternion.Inverse(_headBone.rotation);
                _eyeL = toBone * (el - _headBone.position);
                _eyeR = toBone * (er - _headBone.position);
                _mouth = toBone * (mouth - _headBone.position);
                _fNormal = toBone * fwd;
                _fUp = toBone * up;
                _fRight = toBone * right;
                _eyeSize = Mathf.Clamp(size * 1.3f, 0.012f, 0.045f);
                _mouthWidth = mouthWidth;
                Debug.Log($"[CaptureV2] {name}: face baked (eyes {Vector3.Distance(el, er):0.000} m apart, eye {_eyeSize:0.000} m, mouth {mouthWidth:0.000} m wide)");
                return true;
            }
            catch (System.Exception e)
            {
                Debug.Log($"[CaptureV2] {name}: face bake failed ({e.GetType().Name}), estimating");
                return false;
            }
            finally
            {
                Destroy(a);
                Destroy(b);
                Destroy(h);
            }
        }

        private static List<Vector3> Changed(Vector3[] a, Vector3[] b)
        {
            float max = 0f;
            for (int i = 0; i < a.Length; i++) max = Mathf.Max(max, (b[i] - a[i]).sqrMagnitude);
            var list = new List<Vector3>();
            if (max < 1e-10f) return list;
            float limit = max * 0.12f; // (0.35 of the largest move)^2
            for (int i = 0; i < a.Length; i++) if ((b[i] - a[i]).sqrMagnitude >= limit) list.Add(a[i]);
            return list;
        }

        private static Vector3 Mean(List<Vector3> list)
        {
            Vector3 s = Vector3.zero;
            foreach (Vector3 v in list) s += v;
            return list.Count > 0 ? s / list.Count : s;
        }

        private static Vector3 Div(Vector3 a, Vector3 b) =>
            new(a.x / Mathf.Max(1e-4f, Mathf.Abs(b.x)), a.y / Mathf.Max(1e-4f, Mathf.Abs(b.y)), a.z / Mathf.Max(1e-4f, Mathf.Abs(b.z)));

        private void BuildProps()
        {
            if (_props != null || Rig == null) return;
            LearnFace();
            if (_headBone == null) return;
            _props = new GameObject("v2 KO face").transform;
            _props.SetParent(_headBone, false);
            _props.localScale = Div(Vector3.one, _headBone.lossyScale); // metres inside
            Quaternion face = Quaternion.LookRotation(_fNormal, _fUp);
            _xEyes = new GameObject("X eyes");
            _xEyes.transform.SetParent(_props, false);
            float bar = _eyeSize * 2.6f;
            foreach (Vector3 eye in new[] { _eyeL, _eyeR })
                for (int k = 0; k < 2; k++)
                    CaptureV2Rig.Prop("x", _xEyes.transform, Rig.Box, Rig.Dark, eye + _fNormal * 0.008f,
                        face * Quaternion.Euler(0f, 0f, k == 0 ? 45f : -45f), new Vector3(bar, bar * 0.2f, 0.008f));
            Vector3 corner = _mouth + _fNormal * 0.012f + _fRight * (_mouthWidth * 0.3f) - _fUp * 0.012f;
            _tongue = CaptureV2Rig.Prop("tongue", _props, Rig.Ball, Rig.Pink, corner, face * Quaternion.Euler(35f, 15f, -25f),
                new Vector3(0.042f, 0.018f, 0.075f)).transform;
            _starsRoot = new GameObject("v2 KO stars").transform;
            for (int i = 0; i < 4; i++)
                _stars.Add(CaptureV2Rig.Prop("star", _starsRoot, Rig.Star, Rig.Yellow, Vector3.zero, Quaternion.identity, Vector3.one * 0.085f).transform);
            ShowPropsNow(false);
        }

        private bool _propsOn;

        private void ShowProps(bool on)
        {
            if (on && _props == null) BuildProps();
            if (on == _propsOn) return;
            _propsOn = on;
            if (on) _propsShown = Time.time;
            ShowPropsNow(on);
        }

        private void ShowPropsNow(bool on)
        {
            if (_xEyes != null) _xEyes.SetActive(on);
            if (_tongue != null) _tongue.gameObject.SetActive(on);
            if (_starsRoot != null) _starsRoot.gameObject.SetActive(on);
        }

        private void AnimateProps()
        {
            if (!_propsOn || _headBone == null || _starsRoot == null) return;
            float t = Time.time - _propsShown;
            Vector3 eyes = _headBone.position + _headBone.rotation * ((_eyeL + _eyeR) * 0.5f);
            Vector3 headCentre = eyes - _headBone.rotation * _fNormal * 0.07f;
            Vector3 centre = headCentre + Vector3.up * 0.3f;
            Camera cam = Camera.main;
            float grow = Mathf.Clamp01(t / 0.15f);
            for (int i = 0; i < _stars.Count; i++)
            {
                float a = t * 2f * Mathf.PI * 1.1f + i * Mathf.PI * 0.5f;
                Vector3 p = centre + new Vector3(Mathf.Cos(a), 0.12f * Mathf.Sin(a * 2f + i), Mathf.Sin(a)) * 0.22f;
                Transform s = _stars[i];
                s.position = p;
                Vector3 look = cam != null ? cam.transform.position - p : Vector3.up;
                s.rotation = Quaternion.LookRotation(look.sqrMagnitude > 1e-4f ? look : Vector3.up) * Quaternion.Euler(0f, 0f, t * 400f + i * 40f);
                s.localScale = Vector3.one * (0.085f * grow * (1f + 0.15f * Mathf.Sin(t * 9f + i)));
            }
            if (_tongue != null)
            {
                Quaternion face = Quaternion.LookRotation(_fNormal, _fUp);
                _tongue.localRotation = face * Quaternion.Euler(35f + 12f * Mathf.Sin(t * 7f), 15f, -25f + 6f * Mathf.Sin(t * 5f));
            }
        }

        // ---------- per frame ----------

        private void Update()
        {
            switch (Current)
            {
                case Mode.Frozen:
                    Npc.Calm();
                    if (Time.time > _frozenUntil || Npc.State != NpcState.Free)
                    {
                        Npc.HeldInPlace = false;
                        Current = Mode.Idle;
                        _face = Face.None;
                    }
                    break;
                case Mode.Spinning: Spin(); break;
                case Mode.KnockedOut: TickKnockOut(); break;
                case Mode.Awake: TickAwake(); break;
                case Mode.Clinging: TickCling(); break;
                case Mode.Swing:
                    if (!Npc.IsDown || Ragdoll == null || !Ragdoll.Active) { if (_van != null) _van.Free(Npc); EndCatch(); }
                    else Npc.StunLeft = Mathf.Max(Npc.StunLeft, 2f);
                    break;
                case Mode.Flight:
                    Npc.StunLeft = Mathf.Max(Npc.StunLeft, 2f);
                    TickFlight();
                    break;
                case Mode.Seated: TickSeated(); break;
                default:
                    if (SlapCount > 0 && Npc.State == NpcState.Free && Time.time - _lastSlap > T.LadderReset) SlapCount = 0;
                    break;
            }
            TrackHold();
        }

        private void LateUpdate()
        {
            AnimateProps();
            TickSpit();
            if (_landAnim && _visual != null) LandingAnimation();
        }

        // The seated figure's landing (the visual's local pose; GreyboxNpc leaves it alone once seated): a bounce, upside
        // down and flipping over, or squashed against the ceiling and dropping.
        private void LandingAnimation()
        {
            float t = Time.time - _landAt;
            float length = LandingVariant == 2 ? 0.55f : 0.45f;
            if (t >= length || Current != Mode.Seated)
            {
                _visual.SetLocalPositionAndRotation(_visBasePos, _visBaseRot);
                _landAnim = false;
                return;
            }
            float u = t / length;
            Vector3 pos = _visBasePos;
            Quaternion rot = _visBaseRot;
            switch (LandingVariant)
            {
                case 0:
                    pos += Vector3.up * (0.22f * (1f - u) * Mathf.Abs(Mathf.Cos(u * Mathf.PI * 2.5f)));
                    break;
                case 1:
                {
                    float e = 1f - Mathf.Pow(1f - u, 3f);
                    Quaternion flip = Quaternion.AngleAxis(180f * (1f - e), Vector3.forward);
                    var pivot = new Vector3(0f, 0.55f, 0f);
                    pos = pivot + flip * (_visBasePos - pivot);
                    rot = flip * _visBaseRot;
                    break;
                }
                default:
                {
                    float high = _van != null ? Mathf.Max(0.3f, _van.CeilingAbove(0f) - 1.15f) : 0.8f;
                    float drop = t < 0.12f ? 0f : Mathf.Clamp01((t - 0.12f) / 0.28f);
                    float y = high * (1f - drop * drop);
                    if (t > 0.4f) y = 0.1f * Mathf.Abs(Mathf.Sin((t - 0.4f) / 0.15f * Mathf.PI)) * (1f - u);
                    pos += Vector3.up * y;
                    break;
                }
            }
            _visual.SetLocalPositionAndRotation(pos, rot);
        }

        // ---------- test hooks ----------

        /// <summary>Test: a free NPC standing at 'world' facing 'yaw', calm.</summary>
        public bool TestPlaceStanding(Vector3 world, float yaw)
        {
            if (Npc.State != NpcState.Free) return false;
            var cc = GetComponent<CharacterController>();
            bool was = cc != null && cc.enabled;
            if (cc != null) cc.enabled = false;
            transform.SetPositionAndRotation(world, Quaternion.Euler(0f, yaw, 0f));
            if (cc != null) cc.enabled = was;
            Npc.Calm();
            return true;
        }

        /// <summary>Test: hold him in place (no fleeing) until the slap.</summary>
        public void TestHold(bool on) => Npc.HeldInPlace = on;

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
