using OnlyVolunteers.Characters.Npc;
using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using Part = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Part;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture, the physics of one NPC (after GreyboxNpc and NpcStruggle in the physics step, order 50):
    /// - out cold and held: a carry pose per grab on soft joint drives (physics still wins): by the head the arms hang,
    ///   by the collar they flop up over the head, by an arm the free arm hangs and the knees bend (shuffling), by a leg
    ///   the arms trail over the head and the free leg bends;
    /// - awake and held (NpcStruggle wriggles underneath): the resist per grab: by the head or the collar he reaches for
    ///   your wrist and digs his heels in, by an arm he yanks it back and the other hand reaches for it, by a leg he claws
    ///   the ground (arms forward, a drag against you) and kicks with the other leg;
    /// - the throw swing: the held part follows the hand's path (CaptureV2Npc.SwingPoint) on a stiff spring, the trunk
    ///   trails it on a soft one, gravity mostly relieved; at the end CaptureV2Npc.Release lets go.</summary>
    [DefaultExecutionOrder(50)]
    public sealed class CaptureV2NpcMotor : MonoBehaviour
    {
        private const float PoseSpring = 35f, PoseDamper = 1.5f, PoseMax = 25f;
        private CaptureV2Npc _brain;
        private NpcRagdoll _ragdoll;
        private bool _posing;
        private int _pelvis = -1, _chest = -1, _head = -1;
        private readonly int[] _upper = { -1, -1 }, _fore = { -1, -1 }, _thigh = { -1, -1 }, _calf = { -1, -1 };
        private Quaternion[] _frame;
        private float _nextJerk;

        private void FixedUpdate()
        {
            if (_brain == null) TryGetComponent(out _brain);
            if (_ragdoll == null) TryGetComponent(out _ragdoll);
            if (_brain == null || _ragdoll == null || !_ragdoll.Active || _ragdoll.Profile == null)
            {
                _posing = false;
                return;
            }
            if (!Resolve()) return;
            bool held = _brain.Held;
            switch (_brain.Current)
            {
                case CaptureV2Npc.Mode.KnockedOut when held:
                    CarryPose();
                    break;
                case CaptureV2Npc.Mode.Awake when held:
                case CaptureV2Npc.Mode.Clinging when held:
                    StopPosing();
                    Resist();
                    break;
                case CaptureV2Npc.Mode.Swing:
                    StopPosing();
                    Swing();
                    break;
                default:
                    StopPosing();
                    break;
            }
        }

        private bool Resolve()
        {
            NpcRagdollProfile p = _ragdoll.Profile;
            int n = p.Parts.Length;
            if (_frame != null && _frame.Length == n && _pelvis >= 0) return true;
            _pelvis = p.IndexOf(Kind.Pelvis);
            _chest = p.IndexOf(Kind.Chest);
            _head = p.IndexOf(Kind.Head);
            for (int s = 0; s < 2; s++)
            {
                _upper[s] = p.IndexOf(Kind.UpperArm, (NpcSide)s);
                _fore[s] = p.IndexOf(Kind.ForeArm, (NpcSide)s);
                _thigh[s] = p.IndexOf(Kind.Thigh, (NpcSide)s);
                _calf[s] = p.IndexOf(Kind.Calf, (NpcSide)s);
            }
            _frame = new Quaternion[n];
            for (int i = 0; i < n; i++)
            {
                ConfigurableJoint j = _ragdoll.JointOf(i);
                _frame[i] = j != null ? NpcStruggle.JointFrame(j.axis, j.secondaryAxis) : Quaternion.identity;
            }
            return _pelvis >= 0 && _chest >= 0;
        }

        private void StopPosing()
        {
            if (!_posing) return;
            _posing = false;
            // give the joints back (limp + the carry tone) unless the struggle drives them now
            if (!TryGetComponent(out NpcStruggle s) || s.Current == NpcStruggle.Mode.Off) _ragdoll.DrivesTaken = false;
        }

        // ---------- out cold: the carry pose ----------

        private void CarryPose()
        {
            if (!_ragdoll.DrivesTaken) _ragdoll.DrivesTaken = true;
            _posing = true;
            NpcRagdollProfile p = _ragdoll.Profile;
            GrabPointV2 g = _brain.Grab;
            int heldSide = CaptureV2Rules.IsLeft(g) ? 0 : 1;
            for (int s = 0; s < 2; s++)
            {
                float x = s == 0 ? -1f : 1f;
                bool heldArm = CaptureV2Rules.IsArm(g) && s == heldSide;
                bool heldLeg = CaptureV2Rules.IsLeg(g) && s == heldSide;
                Vector3 arm;
                float elbow, hip, knee;
                switch (g)
                {
                    case GrabPointV2.Head: arm = new Vector3(0.25f * x, -0.95f, 0.15f); elbow = 15f; hip = 5f; knee = 8f; break;
                    case GrabPointV2.ArmLeft:
                    case GrabPointV2.ArmRight: arm = new Vector3(0.3f * x, -0.9f, 0.2f); elbow = 30f; hip = 35f; knee = 55f; break;
                    case GrabPointV2.LegLeft:
                    case GrabPointV2.LegRight: arm = new Vector3(0.35f * x, 0.95f, 0f); elbow = 10f; hip = heldLeg ? 0f : 25f; knee = heldLeg ? 0f : 45f; break;
                    default: arm = new Vector3(0.55f * x, 0.8f, -0.1f); elbow = 35f; hip = 0f; knee = 4f; break; // collar, torso
                }
                if (!heldArm)
                {
                    Shoulder(p, s, arm, PoseSpring);
                    Hinge(p, _fore[s], elbow, 0f, 0f, PoseSpring);
                }
                if (!heldLeg)
                {
                    Hinge(p, _thigh[s], hip, 0f, 0f, PoseSpring);
                    Hinge(p, _calf[s], knee, 0f, 0f, PoseSpring);
                }
            }
        }

        // ---------- awake in the hands: the resist per grab ----------

        private void Resist()
        {
            NpcRagdollProfile p = _ragdoll.Profile;
            GrabPointV2 g = _brain.Grab;
            Vector3 hand = HoldPoint(out int heldPart);
            Rigidbody pelvis = _ragdoll.BodyOf(_pelvis), chest = _ragdoll.BodyOf(_chest);
            if (pelvis == null || chest == null) return;
            Vector3 toHolder = Flat(hand - pelvis.position);
            toHolder = toHolder.sqrMagnitude > 1e-4f ? toHolder.normalized : Vector3.forward;
            Vector3 drag = Flat(pelvis.linearVelocity);
            float now = Time.fixedTime;
            int heldSide = CaptureV2Rules.IsLeft(g) ? 0 : 1;
            switch (g)
            {
                case GrabPointV2.Head:
                case GrabPointV2.Collar:
                case GrabPointV2.Torso:
                    // grabs your wrist (the right hand, or the left now and then) and digs his heels in
                    Reach(p, Mathf.Sin(now * 1.3f) > 0f ? 1 : 0, hand, 70f);
                    for (int s = 0; s < 2; s++)
                    {
                        Rigidbody calf = _ragdoll.BodyOf(_calf[s]);
                        if (calf != null) calf.AddForce(-drag * 9f, ForceMode.Acceleration);
                    }
                    break;
                case GrabPointV2.ArmLeft:
                case GrabPointV2.ArmRight:
                {
                    // yanks the arm back now and then; the other hand clings to it
                    Rigidbody fore = _ragdoll.BodyOf(_fore[heldSide]);
                    if (fore != null && now >= _nextJerk)
                    {
                        _nextJerk = now + Random.Range(0.6f, 1.0f);
                        fore.AddForce(-toHolder * 5f + Vector3.down * 1.5f, ForceMode.Impulse);
                        chest.AddForce(-toHolder * 6f, ForceMode.Impulse);
                    }
                    Reach(p, 1 - heldSide, _ragdoll.PartCenter(_fore[heldSide] >= 0 ? _fore[heldSide] : _chest), 70f);
                    break;
                }
                case GrabPointV2.LegLeft:
                case GrabPointV2.LegRight:
                {
                    // claws the ground: arms forward over the head and a drag against the pull; kicks with the other leg
                    for (int s = 0; s < 2; s++) Shoulder(p, s, new Vector3(0.4f * (s == 0 ? -1f : 1f), 0.9f, 0.25f), 60f);
                    chest.AddForce(-toHolder * 55f + Vector3.down * 20f, ForceMode.Force);
                    int free = 1 - heldSide;
                    Rigidbody calf = _ragdoll.BodyOf(_calf[free]);
                    if (calf != null && now >= _nextJerk)
                    {
                        _nextJerk = now + Random.Range(0.8f, 1.3f);
                        calf.AddForce((toHolder + Vector3.up * 0.4f).normalized * 6f, ForceMode.Impulse);
                    }
                    break;
                }
            }
            _ = heldPart;
        }

        // The hold's world point (the first claim), the holder's hand.
        private Vector3 HoldPoint(out int part)
        {
            part = -1;
            for (int i = 0; i < _ragdoll.Claims.Length; i++)
            {
                if (_ragdoll.Claims[i].Holder == null) continue;
                part = _ragdoll.Claims[i].Part;
                return _ragdoll.ClaimWorld(i);
            }
            return _ragdoll.CenterOfMass;
        }

        // An arm reaches for a world point (shoulder drive toward it in the character frame).
        private void Reach(NpcRagdollProfile p, int side, Vector3 target, float spring)
        {
            int upper = _upper[side];
            if (upper < 0) return;
            Rigidbody chest = _ragdoll.BodyOf(p.Parts[upper].Parent);
            Rigidbody arm = _ragdoll.BodyOf(upper);
            if (chest == null || arm == null) return;
            // the character frame from the chest body: chest bone = character * PoseRotation
            Quaternion character = chest.rotation * Quaternion.Inverse(p.Parts[p.Parts[upper].Parent].PoseRotation);
            Vector3 dir = Quaternion.Inverse(character) * (target - arm.position);
            if (dir.sqrMagnitude < 1e-4f) return;
            Shoulder(p, side, dir.normalized, spring);
            Hinge(p, _fore[side], 20f, 0f, 0f, spring);
        }

        // ---------- the throw swing ----------

        private void Swing()
        {
            float u = _brain.SwingProgress;
            if (u >= 1f)
            {
                _brain.Release();
                return;
            }
            Rigidbody held = _ragdoll.BodyOf(_brain.GrabPart);
            if (held == null) return;
            float seconds = Mathf.Max(0.1f, (CaptureV2Rig.Instance != null ? CaptureV2Rig.Instance.Tuning : new CaptureV2Tuning()).SwingSeconds);
            Vector3 h = _brain.SwingPoint(u);
            Vector3 hv = (_brain.SwingPoint(Mathf.Min(1f, u + 0.03f)) - h) / (0.03f * seconds);
            Vector3 relief = -Physics.gravity * 0.75f;
            for (int i = 0; i < _ragdoll.PartCount; i++)
            {
                Rigidbody rb = _ragdoll.BodyOf(i);
                if (rb != null) rb.AddForce(relief, ForceMode.Acceleration);
            }
            Vector3 a = 900f * (h - held.position) + 60f * (hv - held.linearVelocity);
            held.AddForce(Vector3.ClampMagnitude(a, 450f), ForceMode.Acceleration);
            Vector3 trail = hv.sqrMagnitude > 1e-3f ? hv.normalized : Vector3.up;
            Vector3 c = h - trail * 0.5f - Vector3.up * 0.3f;
            foreach (int k in new[] { _pelvis, _chest })
            {
                Rigidbody rb = _ragdoll.BodyOf(k);
                if (rb == null || rb == held) continue;
                Vector3 at = 90f * (c - rb.position) + 18f * (hv - rb.linearVelocity);
                rb.AddForce(Vector3.ClampMagnitude(at, 200f), ForceMode.Acceleration);
            }
        }

        // ---------- joint targets (as NpcStruggle: hinges flex about +X, shoulders from a character-frame direction) ----------

        private void Hinge(NpcRagdollProfile p, int part, float flex, float twist, float side, float spring)
        {
            if (part < 0) return;
            Part pp = p.Parts[part];
            flex = Mathf.Clamp(flex, pp.LowX, pp.HighX);
            twist = Mathf.Clamp(twist, -pp.LimitY, pp.LimitY);
            side = Mathf.Clamp(side, -pp.LimitZ, pp.LimitZ);
            Quaternion target = Quaternion.AngleAxis(flex, Vector3.right) * Quaternion.AngleAxis(twist, Vector3.up) * Quaternion.AngleAxis(side, Vector3.forward);
            _ragdoll.Drive(part, target, spring, spring * 0.05f + PoseDamper, Mathf.Max(PoseMax, spring * 0.75f));
        }

        private void Shoulder(NpcRagdollProfile p, int side, Vector3 dirCharacter, float spring)
        {
            int upper = _upper[side];
            if (upper < 0) return;
            Part arm = p.Parts[upper];
            Part chest = p.Parts[arm.Parent];
            Vector3 want = Quaternion.Inverse(chest.PoseRotation) * dirCharacter.normalized;
            _ragdoll.Drive(upper, NpcStruggle.ShoulderTarget(arm, _frame[upper], want), spring, spring * 0.05f + PoseDamper, Mathf.Max(PoseMax, spring * 0.75f));
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
