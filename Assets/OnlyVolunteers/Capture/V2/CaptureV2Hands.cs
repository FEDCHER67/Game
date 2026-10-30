using System.Collections.Generic;
using System.Reflection;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using Handle = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Handle;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture, the player's hands (on the KCC player; Q and E are taken from GreyboxInteractor through
    /// GreyboxInteractor.HandsOverride, the PhysicsGrabber is driven from here: its own LMB is off):
    /// - LMB is the slap (Vadim 31.10): hold to charge (up to ChargeMax 1 s: the view leans back further, he freezes in
    ///   shock), release to slap (the arms' punch, hit-stop 0.08 s .. 0.2 s, shake, he spins further and flies a little
    ///   when charged). Holding him: LMB slaps him again, out cold for less each time (2.5 / 1.5 / 0.7 s, longer when
    ///   charged); while he clings it is the slap on the hands and he lets go. Q does nothing here (the stock fist is off).
    /// - the hold: LMB on a lying body grabs it (the existing grab of any ragdoll bone) and keeps it without holding the
    ///   button; RMB lets go. Classified as head / collar / arm L/R / leg L/R (torso for the hips and belly); the player
    ///   walks at that grab's share of the walk speed.
    /// - E within ~2 m of an open van door while holding him: the throw (CaptureV2Npc: swing per grab, flight, a seat or
    ///   a bounce off a full van). No throwing anywhere else.
    /// - he clings (§4): the player stops dead, the mouse turns heavy and the view is pulled back toward what he holds;
    ///   only fast flicks along the arrow (away from the anchor) fill the bar; full: POP, both stumble back.
    /// The HUD (prompts, the escape meter, the arrow and the yank bar) is drawn here.</summary>
    [DefaultExecutionOrder(100)] // after KccFirstPersonInput (0): its mouse turn of this frame is in its yaw already
    [RequireComponent(typeof(GreyboxKccPawn))]
    public sealed class CaptureV2Hands : MonoBehaviour, GreyboxInteractor.IHandsOverride
    {
        private static readonly FieldInfo YawField = typeof(KccFirstPersonInput).GetField("_yaw", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly FieldInfo PitchField = typeof(KccFirstPersonInput).GetField("_pitch", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly RaycastHit[] Sweep = new RaycastHit[16];

        [System.NonSerialized] public CaptureV2Rig Rig;
        /// <summary>Test hook: no keyboard or mouse; the test calls ScriptSlap / ScriptThrow and sets ScriptMouse.</summary>
        [System.NonSerialized] public bool ScriptDriven;
        /// <summary>Test hook: mouse motion in degrees per second (x = turn right, y = look up), added to the real mouse.</summary>
        [System.NonSerialized] public Vector2 ScriptMouse;

        private GreyboxKccPawn _pawn;
        private KccFirstPersonInput _kcc;
        private PhysicsGrabber _grabber;
        private CaptureV2Npc _held;
        private GrabPointV2 _grab;
        private float _chargeStart = -1f, _strikeAt = -1f, _strikeLen, _charge, _cooldownUntil, _scriptReleaseAt;
        private Vector3 _lean;
        private CaptureV2Npc _slapTarget;
        private HitZone _slapZone;
        private bool _punchSent;
        private CaptureV2Npc _throwNpc;
        private int _throwDoor = -1, _throwOffer = -1;
        private float _prevYaw, _prevPitch;
        private bool _hasPrev;
        private int _seenPops;
        private float _popAt = -10f;
        private readonly List<Collider> _ignored = new();
        private Texture2D _arrowTex, _white;

        public CaptureV2Npc HeldNpc => _held;
        public GrabPointV2 HeldPoint => _grab;
        public bool ThrowOffered => _throwOffer >= 0;
        public bool Throwing => _throwNpc != null;
        public bool WindingUp => _chargeStart >= 0f || _strikeAt > 0f;
        public bool Charging => _chargeStart >= 0f;
        public float Charge => _charge;
        public Vector3 Feet => _pawn != null ? _pawn.Position : transform.position;
        public Vector2 Arrow { get; private set; } = Vector2.right;
        public float SpeedScale { get; private set; } = 1f;
        public Camera View => _pawn != null ? _pawn.ViewCamera : null;
        public KccFirstPersonInput Kcc => _kcc;
        public PhysicsGrabber Grabber => _grabber;
        private CaptureV2Tuning T => Rig != null ? Rig.Tuning : CaptureV2Rig.Instance != null ? CaptureV2Rig.Instance.Tuning : new CaptureV2Tuning();

        public bool OwnsQ => isActiveAndEnabled;
        public bool OwnsE => isActiveAndEnabled && (_throwOffer >= 0 || _throwNpc != null);

        private void Awake()
        {
            _pawn = GetComponent<GreyboxKccPawn>();
            _kcc = GetComponent<KccFirstPersonInput>();
            _grabber = GetComponentInChildren<PhysicsGrabber>(true);
        }

        private void OnEnable()
        {
            GreyboxInteractor.HandsOverride = this;
            if (_grabber != null) _grabber.ScriptDriven = true; // LMB is the slap; grab and let go are driven from here
            _hasPrev = false;
        }

        private void OnDisable()
        {
            if (ReferenceEquals(GreyboxInteractor.HandsOverride, this)) GreyboxInteractor.HandsOverride = null;
            if (_kcc != null) OperationPlayerSpeed.Clear(_kcc, this);
            if (_grabber != null) _grabber.ScriptDriven = false;
            _chargeStart = _strikeAt = -1f;
        }

        private void Update()
        {
            if (Rig == null) Rig = CaptureV2Rig.Instance;
            if (_pawn == null || Rig == null || _grabber == null) return;
            CaptureV2Juice.View = View;
            if (OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            UpdateHold();

            // speed: the grab's share of the walk, nothing while he clings or during the throw
            bool limit = _throwNpc != null || _held != null;
            SpeedScale = _throwNpc != null || (_held != null && _held.Current == CaptureV2Npc.Mode.Clinging) ? 0f
                : _held != null ? CaptureV2Rules.SpeedScale(T, _grab) : 1f;
            if (limit) OperationPlayerSpeed.RequestScale(_kcc, this, SpeedScale);

            if (!ScriptDriven)
            {
                bool locked = Cursor.lockState == CursorLockMode.Locked;
                if (locked && Input.GetMouseButtonDown(0)) PressLmb();
                if (_chargeStart >= 0f && !Input.GetMouseButton(0)) ReleaseSlap();
                if (locked && Input.GetMouseButtonDown(1) && _grabber.IsHolding && _throwNpc == null) _grabber.ScriptRelease();
                if (locked && Input.GetKeyDown(KeyCode.E) && _throwOffer >= 0) RequestThrow();
            }
            else if (_chargeStart >= 0f && Time.time >= _scriptReleaseAt) ReleaseSlap();
            TickWindup();
            TickThrow();
            if (_held != null && _held.Current == CaptureV2Npc.Mode.Clinging) ClingMouse();
            else _hasPrev = false;
            if (_held != null && _held.Pops != _seenPops)
            {
                _seenPops = _held.Pops;
                Popped(_held);
            }
            _throwOffer = _held != null && _throwNpc == null && _held.Npc.IsDown && !_held.Busy && Rig.Van != null ? Rig.Van.DoorNear(_pawn.Position) : -1;
            RestorePlayerPairs();
        }

        // ---------- the hold ----------

        private void UpdateHold()
        {
            CaptureV2Npc now = null;
            GrabPointV2 point = GrabPointV2.None;
            int part = -1;
            Rigidbody rb = _grabber.IsHolding ? _grabber.GrabbedBody : null;
            if (rb != null && rb.TryGetComponent(out NpcRagdollPart p) && p.Owner != null && p.Owner.TryGetComponent(out GreyboxNpc npc))
            {
                now = Rig.Ensure(npc);
                part = p.Index;
                NpcRagdollProfile prof = p.Owner.Profile;
                bool bad = false;
                foreach (NpcRagdoll.Claim c in p.Owner.Claims)
                    if (ReferenceEquals(c.Holder, _grabber)) bad = c.Handle == Handle.Bad;
                point = prof != null ? CaptureV2Rules.Classify(prof.Parts[part].Kind, prof.Parts[part].Side, bad) : GrabPointV2.Collar;
            }
            else if (rb != null && rb.TryGetComponent(out GreyboxNpcBody _) && rb.TryGetComponent(out GreyboxNpc capsuleNpc))
            {
                now = Rig.Ensure(capsuleNpc);
                point = GrabPointV2.Collar; // the stage-1 capsule: one handle
            }
            if (now == _held && (now == null || point == _grab)) return;
            if (_held != null && _held != now) CaptureV2Authority.Released(_held, _grabber);
            _held = now;
            _grab = point;
            if (now != null)
            {
                _seenPops = now.Pops;
                CaptureV2Authority.Grabbed(now, _grabber, point, part);
            }
        }

        // ---------- the slap ----------

        /// <summary>Test hook: LMB pressed now and released after 'charge' x ChargeMax s (0 = a quick click).</summary>
        public void ScriptSlap(float charge = 0f)
        {
            PressLmb();
            _scriptReleaseAt = Time.time + Mathf.Clamp01(charge) * T.ChargeMax;
        }

        /// <summary>Test hook: LMB pressed on what the crosshair finds; true when it grabbed (a slap it started is dropped).</summary>
        public bool ScriptLmbGrab()
        {
            bool was = _grabber.IsHolding;
            PressLmb();
            if (_chargeStart >= 0f)
            {
                _chargeStart = -1f;
                if (_slapTarget != null && _slapTarget.Current == CaptureV2Npc.Mode.Frozen) _slapTarget.HoldFrozen();
            }
            return !was && _grabber.IsHolding;
        }

        // LMB down: holding him: the slap (on the hands while he clings); a standing NPC in reach: the slap; a lying body
        // (or a loose prop): the grab, kept until RMB or the throw; nothing: a swing at the air.
        private void PressLmb()
        {
            if (_throwNpc != null || View == null || _chargeStart >= 0f || _strikeAt > 0f || Time.time < _cooldownUntil) return;
            if (_held != null)
            {
                BeginCharge(_held, HitZone.Head);
                return;
            }
            if (FindTarget(out GreyboxNpc npc, out _, out HitZone zone) && npc.State == NpcState.Free)
            {
                BeginCharge(Rig.Ensure(npc), zone);
                return;
            }
            if (!_grabber.IsHolding && _grabber.ScriptGrab()) return;
            BeginCharge(null, HitZone.Head);
        }

        private void BeginCharge(CaptureV2Npc target, HitZone zone)
        {
            _slapTarget = target;
            _slapZone = zone;
            _chargeStart = Time.time;
            _charge = 0f;
            _punchSent = false;
            if (target != null && target.Npc.State == NpcState.Free) CaptureV2Authority.Freeze(target, this);
        }

        // LMB up: the strike. A quick click still cocks the arm MinWindup s; the arms' punch reaches him ContactTime later.
        private void ReleaseSlap()
        {
            if (_chargeStart < 0f) return;
            float held = Time.time - _chargeStart;
            _charge = CaptureV2Rules.Charge(T, held);
            _chargeStart = -1f;
            _strikeLen = Mathf.Max(0f, T.MinWindup - held) + OnlyVolunteers.Player.Hands.ArmPunchV01.ContactTime;
            _strikeAt = Time.time + _strikeLen;
        }

        // What the crosshair finds within the slap reach: the exact ray first, then a fat sphere along it.
        private bool FindTarget(out GreyboxNpc npc, out Vector3 point, out HitZone zone)
        {
            npc = null;
            point = Vector3.zero;
            zone = HitZone.Torso;
            Camera view = View;
            if (view == null) return false;
            var ray = new Ray(view.transform.position, view.transform.forward);
            float reach = T.SlapReach;
            if (Physics.Raycast(ray, out RaycastHit hit, reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore) &&
                hit.collider.GetComponentInParent<GreyboxNpc>() is GreyboxNpc direct)
            {
                npc = direct;
                point = hit.point;
            }
            else
            {
                int n = Physics.SphereCastNonAlloc(ray, 0.35f, Sweep, reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore);
                float best = float.MaxValue;
                for (int i = 0; i < n; i++)
                {
                    RaycastHit h = Sweep[i];
                    Sweep[i] = default;
                    if (h.collider == null || h.distance <= 0f || h.distance >= best) continue;
                    GreyboxNpc c = h.collider.GetComponentInParent<GreyboxNpc>();
                    if (c == null) continue;
                    npc = c;
                    point = h.point;
                    best = h.distance;
                }
            }
            if (npc == null) return false;
            zone = npc.ZoneAlong(ray);
            return true;
        }

        private void TickWindup()
        {
            float now = Time.time;
            if (_chargeStart >= 0f)
            {
                // charging: the view leans back, turns and tilts further the longer LMB is held; full: a tense tremble
                _charge = CaptureV2Rules.Charge(T, now - _chargeStart);
                float cock = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((now - _chargeStart) / 0.18f));
                float shiver = _charge >= 1f ? Mathf.Sin(now * 70f) * 0.5f : 0f;
                _lean = new Vector3(-5f * cock - 5f * _charge, -8f * cock - 9f * _charge + shiver, 7f * cock + 6f * _charge);
                CaptureV2Juice.Lean(_lean);
                if (_slapTarget != null && _slapTarget.Current == CaptureV2Npc.Mode.Frozen) _slapTarget.HoldFrozen();
                if (now - _chargeStart >= T.ChargeAutoRelease) ReleaseSlap();
                return;
            }
            if (_strikeAt <= 0f) return;
            // the strike: the lean snaps back forward
            float k = Mathf.Clamp01((_strikeAt - now) / Mathf.Max(0.01f, _strikeLen));
            CaptureV2Juice.Lean(_lean * (k * k));
            if (_slapTarget != null && _slapTarget.Current == CaptureV2Npc.Mode.Frozen) _slapTarget.HoldFrozen();
            Vector3 point = SlapPoint();
            float p = _charge;
            if (!_punchSent && now >= _strikeAt - OnlyVolunteers.Player.Hands.ArmPunchV01.ContactTime)
            {
                _punchSent = true;
                OnlyVolunteers.Player.Hands.PlayerArmsV01.LocalPunch(_slapTarget != null, point, 0.6f + 0.4f * p);
                CaptureV2Sounds.Play(CaptureV2Sounds.Whoosh, View.transform.position + View.transform.forward * 0.6f, 0.5f + 0.4f * p, 1.35f - 0.35f * p);
            }
            if (now < _strikeAt) return;
            _strikeAt = -1f;
            _cooldownUntil = now + T.SlapCooldown;
            bool landed = false;
            if (_slapTarget != null && _slapTarget.isActiveAndEnabled)
            {
                Vector3 to = _slapTarget.Center - Feet;
                to.y = 0f;
                if (_slapTarget == _held || to.magnitude <= T.SlapLungeReach)
                    landed = CaptureV2Authority.Slap(_slapTarget, this, Feet, point, _slapZone, p);
            }
            if (!landed) return;
            CaptureV2Juice.HitStop(T.SlapHitStop * (1f + T.ChargeHitStopGain * p));
            CaptureV2Juice.Shake(T.SlapShake * (1f + T.ChargeShakeGain * p), 0.25f + 0.2f * p);
            CaptureV2Juice.Kick(1.5f + 2.5f * p, -2.5f - 3f * p, -4f - 4f * p);
            CaptureV2Sounds.Play(CaptureV2Sounds.Smack, point, 1f, 1f - 0.22f * p);
            Sfx.PlayAt(SfxIds.HitHead, point, 0.8f + 0.2f * p);
        }

        // Where the smack lands now: the clinging hand's anchor, a lying head, a standing face.
        private Vector3 SlapPoint()
        {
            CaptureV2Npc t = _slapTarget;
            if (t == null) return View != null ? View.transform.position + View.transform.forward * T.SlapReach : Feet;
            if (t.Current == CaptureV2Npc.Mode.Clinging) return t.ClingAnchor;
            if (t.Npc.IsDown && t.Npc.PhysicalBody != null && t.Npc.PhysicalBody.Active) return t.Npc.PhysicalBody.Landmark(NpcLandmark.Head);
            return t.transform.position + Vector3.up * 1.55f;
        }

        // ---------- the throw ----------

        /// <summary>Test hook: E at the door.</summary>
        public bool ScriptThrow()
        {
            RequestThrow();
            return _throwNpc != null;
        }

        private void RequestThrow()
        {
            if (_throwOffer < 0 || _held == null || _throwNpc != null || Rig.Van == null) return;
            CaptureV2Npc npc = _held;
            int door = _throwOffer;
            if (!CaptureV2Authority.Throw(npc, this, Rig.Van, door)) return;
            _throwNpc = npc;
            _throwDoor = door;
            IgnorePlayer(npc);
            _grabber.ScriptRelease(); // the swing carries him now
            CaptureV2Sounds.Play(CaptureV2Sounds.Whoosh, Feet + Vector3.up * 1.2f, 1f, 0.8f);
        }

        private void TickThrow()
        {
            if (_throwNpc == null) return;
            CaptureV2Npc b = _throwNpc;
            if (b.Current != CaptureV2Npc.Mode.Swing && b.Current != CaptureV2Npc.Mode.Flight)
            {
                _throwNpc = null;
                return;
            }
            // the view turns to the doorway, so he is seen going in
            Vector3 to = Rig.Van.DoorwayWorld(_throwDoor, 0.7f) - View.transform.position;
            float wantYaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            float wantPitch = -Mathf.Atan2(to.y, new Vector2(to.x, to.z).magnitude) * Mathf.Rad2Deg;
            float yaw = (float)YawField.GetValue(_kcc), pitch = (float)PitchField.GetValue(_kcc);
            YawField.SetValue(_kcc, Mathf.Repeat(Mathf.MoveTowardsAngle(yaw, wantYaw, 420f * Time.deltaTime), 360f));
            PitchField.SetValue(_kcc, Mathf.MoveTowards(pitch, Mathf.Clamp(wantPitch, -30f, 45f), 200f * Time.deltaTime));
            if (b.Current != CaptureV2Npc.Mode.Swing) return;
            float u = b.SwingProgress;
            switch (b.ThrowStyle)
            {
                case ThrowStyleV2.OverHead: // the sack goes over the head: look up with it, then slam down
                    CaptureV2Juice.Lean(new Vector3(u < 0.6f ? -18f * (u / 0.6f) : -18f + 30f * ((u - 0.6f) / 0.4f), 0f, 4f * b.ThrowMirror * u));
                    break;
                case ThrowStyleV2.Hammer:
                    CaptureV2Juice.Lean(new Vector3(-4f, -50f * b.ThrowMirror * Mathf.Sin(Mathf.PI * u), 9f * b.ThrowMirror * Mathf.Sin(Mathf.PI * u)));
                    break;
                default:
                    CaptureV2Juice.Lean(new Vector3(-3f, -65f * b.ThrowMirror * Mathf.Sin(Mathf.PI * u), 12f * b.ThrowMirror * Mathf.Sin(Mathf.PI * u)));
                    break;
            }
        }

        // The thrown body and the player's capsule ignore each other until they are apart again.
        private void IgnorePlayer(CaptureV2Npc npc)
        {
            Collider me = _kcc != null && _kcc.Character != null ? _kcc.Character.Motor.Capsule : null;
            NpcRagdoll r = npc != null ? npc.GetComponent<NpcRagdoll>() : null;
            if (me == null || r == null) return;
            foreach (Collider c in r.Colliders)
            {
                if (c == null || !c.enabled) continue;
                Physics.IgnoreCollision(c, me, true);
                if (!_kcc.Character.IgnoredColliders.Contains(c)) _kcc.Character.IgnoredColliders.Add(c);
                if (!_ignored.Contains(c)) _ignored.Add(c);
            }
        }

        private void RestorePlayerPairs()
        {
            if (_ignored.Count == 0 || _throwNpc != null) return;
            Collider me = _kcc.Character.Motor.Capsule;
            for (int i = _ignored.Count - 1; i >= 0; i--)
            {
                Collider c = _ignored[i];
                if (c != null && c.enabled && c.gameObject.activeInHierarchy && me != null && me.enabled)
                {
                    if (c.bounds.Intersects(me.bounds)) continue; // still inside: wait
                    Physics.IgnoreCollision(c, me, false);
                }
                _kcc.Character.IgnoredColliders.Remove(c);
                _ignored.RemoveAt(i);
            }
            _kcc.Character.IgnoredColliders.RemoveAll(c => c == null);
        }

        // ---------- cling: the heavy mouse, the pull back, the yank ----------

        private void ClingMouse()
        {
            CaptureV2Npc npc = _held;
            Camera view = View;
            float dt = Time.deltaTime;
            if (view == null || dt <= 0f || YawField == null || PitchField == null) return;
            float yaw = (float)YawField.GetValue(_kcc), pitch = (float)PitchField.GetValue(_kcc);
            if (!_hasPrev)
            {
                _prevYaw = yaw;
                _prevPitch = pitch;
                _hasPrev = true;
            }
            float dYaw = Mathf.DeltaAngle(_prevYaw, yaw) + ScriptMouse.x * dt;
            float dPitch = (pitch - _prevPitch) - ScriptMouse.y * dt;
            var mouse = new Vector2(dYaw, -dPitch); // x right, y forward (up)
            Vector3 away = npc.Center - npc.ClingAnchor;
            away.y = 0f;
            Vector3 f = view.transform.forward, r = view.transform.right;
            f.y = 0f;
            r.y = 0f;
            var arrow = new Vector2(Vector3.Dot(away, r.normalized), Vector3.Dot(away, f.normalized));
            Arrow = arrow.sqrMagnitude > 1e-4f ? arrow.normalized : Vector2.right;
            float along = Vector2.Dot(mouse, Arrow) / dt;
            CaptureV2Authority.Yank(npc, _grabber, along, dt);
            // heavy: the view gets only a share of the mouse; the anchor drags it back toward what he holds
            float newYaw = _prevYaw + dYaw * T.ClingHeavyMouse;
            float newPitch = Mathf.Clamp(_prevPitch + dPitch * T.ClingHeavyMouse, -85f, 85f);
            Vector3 to = npc.ClingAnchor - view.transform.position;
            float wantYaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            float wantPitch = -Mathf.Atan2(to.y, new Vector2(to.x, to.z).magnitude) * Mathf.Rad2Deg;
            newYaw = Mathf.MoveTowardsAngle(newYaw, wantYaw, T.ClingPullDegPerSec * dt);
            newPitch = Mathf.MoveTowards(newPitch, wantPitch, T.ClingPullDegPerSec * 0.5f * dt);
            // the yoke: the view never strays further than ClingMaxView from him (or than it already was), so the hold
            // (the hand's point in front of the view) is not torn out by the flicks
            float yawLimit = Mathf.Max(T.ClingMaxView, Mathf.Abs(Mathf.DeltaAngle(wantYaw, _prevYaw)));
            newYaw = wantYaw + Mathf.Clamp(Mathf.DeltaAngle(wantYaw, newYaw), -yawLimit, yawLimit);
            float pitchLimit = Mathf.Max(T.ClingMaxView, Mathf.Abs(_prevPitch - wantPitch));
            newPitch = Mathf.Clamp(newPitch, wantPitch - pitchLimit, wantPitch + pitchLimit);
            YawField.SetValue(_kcc, Mathf.Repeat(newYaw, 360f));
            PitchField.SetValue(_kcc, newPitch);
            _prevYaw = newYaw;
            _prevPitch = newPitch;
        }

        private void Popped(CaptureV2Npc npc)
        {
            Vector3 away = npc.Center - npc.ClingAnchor;
            away.y = 0f;
            away = away.sqrMagnitude > 1e-4f ? away.normalized : -transform.forward;
            _pawn.Knock(away * T.PopPlayerKnock + Vector3.up * 1.5f);
            CaptureV2Juice.HitStop(0.06f);
            CaptureV2Juice.Kick(-4f, 0f, 4f);
            CaptureV2Juice.Shake(1.6f, 0.35f);
            _popAt = Time.time;
            _hasPrev = false;
        }

        // ---------- test hooks ----------

        /// <summary>Test: look at a world point now (the camera too, so a ray this frame sees it).</summary>
        public void Aim(Vector3 world)
        {
            Camera view = View;
            if (view == null) return;
            Vector3 to = world - view.transform.position;
            float yaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            float pitch = -Mathf.Atan2(to.y, new Vector2(to.x, to.z).magnitude) * Mathf.Rad2Deg;
            SetView(yaw, pitch);
        }

        public void SetView(float yaw, float pitch)
        {
            YawField?.SetValue(_kcc, Mathf.Repeat(yaw, 360f));
            PitchField?.SetValue(_kcc, Mathf.Clamp(pitch, -85f, 85f));
            if (View != null) View.transform.rotation = Quaternion.Euler(Mathf.Clamp(pitch, -85f, 85f), yaw, 0f);
            _hasPrev = false;
        }

        public float ViewYaw => YawField != null ? (float)YawField.GetValue(_kcc) : 0f;
        public float ViewPitch => PitchField != null ? (float)PitchField.GetValue(_kcc) : 0f;

        // ---------- HUD ----------

        private void OnGUI()
        {
            if (OnlyVolunteers.UI.OvMenuGate.Blocking || _pawn == null || Rig == null) return;
            if (_white == null) { _white = new Texture2D(1, 1); _white.SetPixel(0, 0, Color.white); _white.Apply(); }
            var style = new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter };
            string hint = null;
            if (_held != null)
            {
                hint = $"держишь за {CaptureV2Rules.Name(_grab)}     ЛКМ — ещё шлепок     ПКМ — отпустить";
                if (_throwOffer >= 0)
                    hint = Rig.Van.FreeSeat(_throwOffer) >= 0 ? "E — закинуть в бусик     " + hint : "E — закинуть (мест нет, отскочит!)     " + hint;
            }
            else if (FindTarget(out GreyboxNpc npc, out _, out _) && npc.State == NpcState.Free) hint = "ЛКМ — шлёпнуть (зажми — сильнее)";
            else if (FindTarget(out GreyboxNpc down, out _, out _) && down.State == NpcState.Down) hint = "ЛКМ — схватить";
            if (_chargeStart >= 0f) hint = _charge >= 1f ? "ЗАМАХ НА ПОЛНУЮ!" : "замах...";
            if (Time.time - _popAt < 1.2f) hint = "ОТОРВАЛ!";
            if (_held == null && CaptureV2Rig.Instance != null)
                foreach (GreyboxNpc n in GreyboxNpc.All)
                    if (n != null && n.TryGetComponent(out CaptureV2Npc b) && b.LastBounced && Time.time - b.LastBounceTime < 1.5f) hint = "Мест нет — отскочил!";
            if (hint != null) GUI.Label(new Rect(0f, Screen.height - 110f, Screen.width - 340f, 30f), hint, style);
            if (_held == null) return;
            if (_held.Current == CaptureV2Npc.Mode.Awake || _held.Current == CaptureV2Npc.Mode.Clinging)
            {
                Bar(new Rect(Screen.width * 0.5f - 160f, 70f, 320f, 16f), _held.Meter, new Color(0.9f, 0.2f, 0.15f));
                GUI.Label(new Rect(0f, 44f, Screen.width, 24f), "вырывается!", style);
            }
            if (_held.Current != CaptureV2Npc.Mode.Clinging) return;
            // the arrow (pull this way) and the yank bar
            if (_arrowTex == null) _arrowTex = MakeArrow();
            Vector2 centre = new(Screen.width * 0.5f, Screen.height * 0.5f);
            float angle = Mathf.Atan2(-Arrow.y, Arrow.x) * Mathf.Rad2Deg;
            Matrix4x4 keep = GUI.matrix;
            GUIUtility.RotateAroundPivot(angle, centre);
            GUI.color = new Color(1f, 0.85f, 0.2f, 0.95f);
            GUI.DrawTexture(new Rect(centre.x + 40f, centre.y - 32f, 120f, 64f), _arrowTex);
            GUI.color = Color.white;
            GUI.matrix = keep;
            Bar(new Rect(centre.x - 120f, centre.y + 90f, 240f, 18f), _held.YankBar, new Color(1f, 0.85f, 0.2f));
            GUI.Label(new Rect(0f, centre.y + 112f, Screen.width, 26f), "вцепился!  рви мышью по стрелке!", style);
        }

        private void Bar(Rect r, float value, Color c)
        {
            GUI.color = new Color(0f, 0f, 0f, 0.6f);
            GUI.DrawTexture(r, _white);
            GUI.color = c;
            GUI.DrawTexture(new Rect(r.x + 2f, r.y + 2f, (r.width - 4f) * Mathf.Clamp01(value), r.height - 4f), _white);
            GUI.color = Color.white;
        }

        private static Texture2D MakeArrow()
        {
            const int w = 64, h = 32;
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false);
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    float cy = Mathf.Abs(y - h * 0.5f + 0.5f);
                    bool shaft = x < w * 0.6f && cy < h * 0.16f;
                    bool head = x >= w * 0.55f && cy < (w - x) * 0.55f;
                    t.SetPixel(x, y, shaft || head ? Color.white : Color.clear);
                }
            t.Apply();
            return t;
        }
    }
}
