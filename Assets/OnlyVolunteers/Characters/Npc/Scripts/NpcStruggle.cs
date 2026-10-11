using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using Part = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Part;

namespace OnlyVolunteers.Characters.Npc
{
    // Stage 9, step 4 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §4.3): a Groggy ragdoll moves on its joint drives, no
    // clips. GreyboxNpc adds it next to NpcRagdoll and ticks it every physics step while the NPC is down (Tick); Out, the
    // joints stay limp (only the A4 carry tone), and when it stops NpcRagdoll gets them back (DrivesTaken off).
    // - Lying (not held, not crawling: in a cargo bay, in the air): weak tone (GroggyTone), the head comes up (HeadLift)
    //   and looks around (LookAround), the arms paw about a reaching pose (on the back up at the sky, on the belly over
    //   the head; PawSpring/Amplitude/Frequency), the legs bicycle slowly.
    // - Crawling (not held, touching the ground, a direction from GreyboxNpc: away from the threat, or to an open cargo
    //   door): the arms reach over the head and pull down to the hips in turn, the legs push in step with the opposite
    //   arm, the head lifts. On the back the same cycle reads as a backstroke scoot with the heels. The trunk is dragged
    //   along in step with the pulls (a speed-limited force on the chest and the pelvis, CrawlSpeed / CrawlMaxForce):
    //   friction on 1 kg forearms cannot be trusted to move 28 kg reliably, so the propulsion is an assist synchronised
    //   with the limbs. It replaces the capsule-era crawl hops on the ragdoll. The pull goes head first, at most CrawlVeer
    //   off the head's direction toward the crawl direction, mostly at the chest: a body facing the wrong way curves round.
    // - Held (the carried struggle): the same pawing and leg swings HeldAmplitude wider and 1.3 times faster, the waist
    //   wriggles (Wriggle) inside the carry tone, whose springs it keeps (A4: the trunk, and a split pair's hammock hips),
    //   so the body stays carryable.
    // - Kick (GreyboxNpc picks the moment and rolls the tear): one leg chambers and lashes out for KickSeconds at
    //   KickSpring: on the back straight up, on the belly the heel up behind, held a forward kick. The motors' reaction
    //   jerks the holders' hands through the physics.
    // Joint targets: hinges in joint space (+X is flexion: NpcRagdoll.MakeJoint flips the hinge axis), clamped inside the
    // joint's limits; the shoulders from a wanted arm direction in the chest's frame (the character frame of the Idle
    // pose: +X right, +Y up, +Z front), turned into the joint target with the standard ConfigurableJoint formula
    // (target = W^-1 · rel^-1 · reference · W, W the joint frame; checked by NpcRagdollProfileTests).
    [DisallowMultipleComponent]
    public sealed class NpcStruggle : MonoBehaviour
    {
        public enum Mode : byte { Off, Lie, Crawl, Held }

        private const float DamperShare = 0.05f; // damper = spring x this: a lively, slightly bouncy flail
        private const float CrawlGain = 30f;     // the pull: N per kg of body per m/s short of its aim
        private const float PullShare = 0.55f;   // of an arm's crawl cycle: the pull (the rest is the reach)
        private const float GroundEvery = 0.1f;  // s between ground checks

        private NpcRagdoll _ragdoll;
        private Mode _mode;
        private float _start, _seed, _pawHz, _legHz, _mass, _nextGround;
        private bool _grounded;
        private readonly float[] _kickUntil = new float[2];
        private Quaternion[] _frame; // per part: its joint's frame (joint space -> the bone's local space)
        private int _pelvis = -1, _chest = -1, _head = -1;
        private readonly int[] _upper = { -1, -1 }, _fore = { -1, -1 }, _thigh = { -1, -1 }, _calf = { -1, -1 };

        /// <summary>What it does now (Off while Out, not a ragdoll, or the profile's Struggle is off).</summary>
        public Mode Current => _mode;
        /// <summary>Motor kicks started since the component was made (the smoke test, the notes).</summary>
        public int Kicks { get; private set; }
        /// <summary>N: the crawl's pull on the trunk in the last physics step (0 when not crawling).</summary>
        public float Pull { get; private set; }

        private void OnEnable()
        {
            if (_ragdoll == null) TryGetComponent(out _ragdoll);
        }

        /// <summary>Physics step while the NPC is down (GreyboxNpc.FixedDown). groggy false: limp (Out). crawl: the flat
        /// direction to crawl in (zero: none: held, or lying in a cargo bay with no open door), speedScale on CrawlSpeed.</summary>
        public void Tick(bool groggy, Vector3 crawl, float speedScale)
        {
            if (_ragdoll == null) TryGetComponent(out _ragdoll);
            NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
            if (!groggy || p == null || !p.Struggle || !_ragdoll.Active)
            {
                Stop();
                return;
            }
            if (_mode == Mode.Off && !Begin(p)) return;
            float now = Time.fixedTime;
            int holders = _ragdoll.HolderCount;
            bool crawling = holders == 0 && crawl.sqrMagnitude > 1e-4f && Grounded(now);
            _mode = holders > 0 ? Mode.Held : crawling ? Mode.Crawl : Mode.Lie;
            float t = now - _start;
            bool back = _ragdoll.Front.y >= 0f;
            int tone = p.CarryTone ? _ragdoll.ToneFor(holders) : 0;
            Trunk(p, tone, back, t);
            for (int side = 0; side < 2; side++)
            {
                Arm(p, side, back, t);
                Leg(p, side, tone, back, t, now);
            }
            Pull = _mode == Mode.Crawl ? Drag(p, crawl.normalized, speedScale, t) : 0f;
        }

        /// <summary>One leg lashes out now (GreyboxNpc.Kick, which also rolls the tear). Only while it struggles.</summary>
        public void Kick(NpcSide side)
        {
            NpcRagdollProfile p = _ragdoll != null ? _ragdoll.Profile : null;
            if (_mode == Mode.Off || p == null) return;
            _kickUntil[(int)side] = Time.fixedTime + p.KickSeconds;
            Kicks++;
        }

        /// <summary>Back to limp (Out again, woken, the ragdoll gone): NpcRagdoll writes the carry tone again.</summary>
        public void Stop()
        {
            if (_mode == Mode.Off) return;
            _mode = Mode.Off;
            Pull = 0f;
            _kickUntil[0] = _kickUntil[1] = 0f;
            if (_ragdoll != null) _ragdoll.DrivesTaken = false;
        }

        private bool Begin(NpcRagdollProfile p)
        {
            int n = p.Parts.Length;
            if (_frame == null || _frame.Length != n) _frame = new Quaternion[n];
            for (int i = 0; i < n; i++)
            {
                ConfigurableJoint joint = _ragdoll.JointOf(i);
                _frame[i] = joint != null ? JointFrame(joint.axis, joint.secondaryAxis) : Quaternion.identity;
            }
            _pelvis = p.IndexOf(Kind.Pelvis);
            _chest = p.IndexOf(Kind.Chest);
            _head = p.IndexOf(Kind.Head);
            for (int s = 0; s < 2; s++)
            {
                var side = (NpcSide)s;
                _upper[s] = p.IndexOf(Kind.UpperArm, side);
                _fore[s] = p.IndexOf(Kind.ForeArm, side);
                _thigh[s] = p.IndexOf(Kind.Thigh, side);
                _calf[s] = p.IndexOf(Kind.Calf, side);
            }
            if (_pelvis < 0 || _chest < 0 || _head < 0) return false;
            _ragdoll.DrivesTaken = true;
            _start = Time.fixedTime;
            _seed = Random.Range(0f, 2f * Mathf.PI);
            _pawHz = Random.Range(Mathf.Min(p.PawFrequency.x, p.PawFrequency.y), Mathf.Max(p.PawFrequency.x, p.PawFrequency.y));
            _legHz = _pawHz * Random.Range(0.6f, 0.8f);
            _mass = Mathf.Max(1f, p.TotalMass);
            _kickUntil[0] = _kickUntil[1] = 0f;
            _nextGround = 0f;
            _mode = Mode.Lie;
            return true;
        }

        private bool Grounded(float now)
        {
            if (now >= _nextGround)
            {
                _nextGround = now + GroundEvery;
                _grounded = _ragdoll.Grounded;
            }
            return _grounded;
        }

        // ---------- The trunk: the waist (the chest's joint) and the neck (the head's) ----------

        private void Trunk(NpcRagdollProfile p, int tone, bool back, float t)
        {
            const float tau = 2f * Mathf.PI;
            float look = Mathf.Sin(tau * 0.35f * t + _seed);
            float weak = p.GroggyTone, weakDamper = p.GroggyTone * DamperShare;
            switch (_mode)
            {
                case Mode.Held:
                {
                    // The carry tone's springs keep the trunk in line (A4); the wriggle rides on top, half as wide in a hammock.
                    float wriggle = p.Wriggle * (tone >= 2 ? 0.5f : 1f);
                    float a = tau * 1.3f * t + _seed;
                    float spring = tone == 2 ? p.CarryWaistSpring : tone == 1 ? p.HeldSpring : weak;
                    float damper = tone == 2 ? p.CarryDamper : tone == 1 ? p.HeldDamper : weakDamper;
                    float max = tone == 2 ? p.CarryMaxTorque : tone == 1 ? p.HeldMaxTorque : weak;
                    Hinge(p, _chest, 0f, 0.7f * wriggle * Mathf.Sin(a + 1.1f), wriggle * Mathf.Sin(a), spring, damper, max);
                    float neck = tone >= 1 ? Mathf.Max(p.HeldSpring, weak) : weak;
                    Hinge(p, _head, 0f, p.LookAround * look, 0f, neck, neck * DamperShare, tone >= 1 ? p.HeldMaxTorque : weak);
                    break;
                }
                case Mode.Crawl:
                {
                    float sway = Mathf.Sin(tau * t / Mathf.Max(0.2f, p.CrawlCycle));
                    float spring = 0.5f * p.CrawlSpring;
                    Hinge(p, _chest, back ? 8f : -5f, 0f, 10f * sway, spring, spring * DamperShare, spring);
                    Hinge(p, _head, back ? 0.8f * p.HeadLift : -p.HeadLift, 10f * look, 0f, weak, weakDamper, weak);
                    break;
                }
                default:
                {
                    // Curled a little on the back (trying to sit up), arched a little on the belly; the head up, looking round.
                    float wobble = Mathf.Sin(tau * 0.45f * t + 0.7f * _seed);
                    Hinge(p, _chest, back ? 12f : -8f, 0f, 6f * wobble, weak, weakDamper, weak);
                    float nod = 8f * Mathf.Sin(tau * 0.6f * t + _seed);
                    Hinge(p, _head, (back ? p.HeadLift : -0.8f * p.HeadLift) + nod, p.LookAround * look, 0f, weak, weakDamper, weak);
                    break;
                }
            }
        }

        // ---------- The arms ----------

        private void Arm(NpcRagdollProfile p, int side, bool back, float t)
        {
            int upper = _upper[side], fore = _fore[side];
            if (upper < 0) return;
            const float tau = 2f * Mathf.PI;
            float s = side == 0 ? -1f : 1f; // the character's left is -X (the Idle pose faces +Z)
            Vector3 dir;
            float elbow, spring;
            if (_mode == Mode.Crawl)
            {
                float phase = Mathf.Repeat(t / Mathf.Max(0.2f, p.CrawlCycle) + (side == 0 ? 0f : 0.5f), 1f);
                var reach = new Vector3(0.35f * s, 1f, 0f);    // over the head, along the ground
                var pulled = new Vector3(0.55f * s, -0.85f, 0f); // down beside the hip
                var lift = new Vector3(0f, 0f, back ? 1f : -1f); // away from the ground: the front on the back, the back on the belly
                if (phase < 1f - PullShare)
                {
                    float u = phase / (1f - PullShare); // the reach: the arm swings over, off the ground
                    dir = Vector3.Lerp(pulled, reach, u) + lift * (0.6f * Mathf.Sin(Mathf.PI * u));
                    elbow = 70f * Mathf.Sin(Mathf.PI * u);
                }
                else
                {
                    float u = (phase - (1f - PullShare)) / PullShare; // the pull: along the ground, pressing a little
                    dir = Vector3.Lerp(reach, pulled, u) - lift * 0.15f;
                    elbow = 55f * Mathf.Sin(Mathf.PI * u);
                }
                spring = p.CrawlSpring;
            }
            else
            {
                bool held = _mode == Mode.Held;
                float amp = p.PawAmplitude * (held ? p.HeldAmplitude : 1f);
                float a = tau * _pawHz * (held ? 1.3f : 1f) * t + _seed + 2.1f * side;
                // The pose it paws about: on the back reaching up at the sky (its front), on the belly over the head scraping
                // the ground; held, out in front of it.
                Vector3 basis = held ? new Vector3(0.4f * s, 0.1f, 0.9f)
                    : back ? new Vector3(0.45f * s, 0.25f, 0.85f)
                    : new Vector3(0.5f * s, 0.75f, 0.25f);
                dir = Quaternion.AngleAxis(amp * Mathf.Sin(a), Vector3.right) *
                      Quaternion.AngleAxis(0.6f * amp * Mathf.Sin(1.3f * a + 0.7f), Vector3.forward) * basis;
                elbow = 35f + 30f * (held ? p.HeldAmplitude : 1f) * Mathf.Sin(a + 1f);
                spring = p.PawSpring * (held ? 1.2f : 1f);
            }
            float max = 0.75f * spring;
            Part arm = p.Parts[upper];
            Part chest = p.Parts[arm.Parent];
            // The character-frame direction in the chest bone's frame (its Idle rotation in the character frame).
            Vector3 want = Quaternion.Inverse(chest.PoseRotation) * dir.normalized;
            _ragdoll.Drive(upper, ShoulderTarget(arm, _frame[upper], want), spring, spring * DamperShare, max);
            if (fore >= 0) Hinge(p, fore, elbow, 0f, 0f, spring, spring * DamperShare, max);
        }

        // ---------- The legs ----------

        private void Leg(NpcRagdollProfile p, int side, int tone, bool back, float t, float now)
        {
            int thigh = _thigh[side], calf = _calf[side];
            if (thigh < 0) return;
            const float tau = 2f * Mathf.PI;
            float hip, knee, spring, damper, max;
            float hipSpring = -1f, hipDamper = 0f, hipMax = 0f; // the hips' own drive (a split pair's hammock)
            float left = _kickUntil[side] - now;
            if (left > 0f)
            {
                // The kick: chamber, then lash out.
                bool chamber = 1f - left / Mathf.Max(0.05f, p.KickSeconds) < 0.35f;
                if (_mode == Mode.Held)
                {
                    hip = chamber ? 70f : 15f;
                    knee = chamber ? 110f : 0f;
                }
                else if (back)
                {
                    hip = chamber ? 60f : 85f;
                    knee = chamber ? 110f : 5f;
                }
                else
                {
                    hip = chamber ? 0f : -18f;
                    knee = chamber ? 120f : 10f;
                }
                spring = p.KickSpring;
                damper = 0.02f * p.KickSpring;
                max = p.KickMaxTorque;
            }
            else if (_mode == Mode.Crawl)
            {
                // With the opposite arm: drawn up while it reaches, pushing while it pulls.
                float phase = Mathf.Repeat(t / Mathf.Max(0.2f, p.CrawlCycle) + (side == 0 ? 0.5f : 0f), 1f);
                float u = phase < 1f - PullShare ? phase / (1f - PullShare) : 1f - (phase - (1f - PullShare)) / PullShare;
                hip = Mathf.Lerp(5f, 45f, u);
                knee = Mathf.Lerp(5f, 80f, u);
                spring = p.CrawlSpring;
                damper = spring * DamperShare;
                max = 0.75f * spring;
            }
            else
            {
                bool held = _mode == Mode.Held;
                float amp = p.LegAmplitude * (held ? p.HeldAmplitude : 1f);
                float a = tau * (held ? 1.4f : _legHz) * t + _seed + Mathf.PI * side;
                if (back || held)
                {
                    hip = 25f + amp * Mathf.Sin(a);
                    knee = 40f + 1.3f * amp * Mathf.Sin(a + 1.2f);
                }
                else
                {
                    hip = 5f + 0.4f * amp * Mathf.Sin(a);
                    knee = 50f + 1.4f * amp * Mathf.Sin(a + 1.2f);
                }
                spring = p.LegSpring * (held ? 1.7f : 1f);
                damper = spring * DamperShare;
                max = 0.8f * spring;
                if (held && tone == 2)
                {
                    // Carried by a split pair as a hammock (A4): the hips stay firm at the carry flexion, the knees kick about.
                    hipSpring = p.CarryHipSpring;
                    hipDamper = p.CarryDamper;
                    hipMax = p.CarryMaxTorque;
                    hip = p.CarryHipFlexion + 0.3f * amp * Mathf.Sin(a);
                }
            }
            if (hipSpring >= 0f) Hinge(p, thigh, hip, 0f, 0f, hipSpring, hipDamper, hipMax);
            else Hinge(p, thigh, hip, 0f, 0f, spring, damper, max);
            if (calf >= 0) Hinge(p, calf, knee, 0f, 0f, spring, damper, max);
        }

        // ---------- The crawl's pull ----------

        // The trunk dragged in step with the arms' pulls: toward CrawlSpeed x scale x (0.3 .. 1.4 with the pull), at most
        // CrawlMaxForce, 70 % on the chest and 30 % on the pelvis, head first: along the head's direction turned at most
        // CrawlVeer toward 'dir', so a body facing away from where it wants to go curves round instead of folding; the
        // chest lifted a little while an arm pulls (the arms push it up).
        private float Drag(NpcRagdollProfile p, Vector3 dir, float scale, float t)
        {
            Rigidbody chest = _ragdoll.BodyOf(_chest), pelvis = _ragdoll.BodyOf(_pelvis), head = _ragdoll.BodyOf(_head);
            if (chest == null || pelvis == null) return 0f;
            Vector3 along = _ragdoll.Landmark(NpcLandmark.Head) - _ragdoll.Landmark(NpcLandmark.Pelvis);
            along.y = 0f;
            if (along.sqrMagnitude > 1e-4f)
            {
                float off = Vector3.SignedAngle(along, dir, Vector3.up);
                if (Mathf.Abs(off) > 179f) off = 179f; // straight behind it: turn one way, not through the ground
                dir = Quaternion.AngleAxis(Mathf.Clamp(off, -p.CrawlVeer, p.CrawlVeer), Vector3.up) * along.normalized;
            }
            float cycle = Mathf.Max(0.2f, p.CrawlCycle);
            float surge = 0f;
            for (int side = 0; side < 2; side++)
            {
                float phase = Mathf.Repeat(t / cycle + (side == 0 ? 0f : 0.5f), 1f);
                if (phase >= 1f - PullShare)
                    surge = Mathf.Max(surge, Mathf.Sin(Mathf.PI * (phase - (1f - PullShare)) / PullShare));
            }
            float trunk = chest.mass + pelvis.mass;
            Vector3 velocity = (chest.linearVelocity * chest.mass + pelvis.linearVelocity * pelvis.mass) / trunk;
            float aim = p.CrawlSpeed * Mathf.Max(0f, scale) * (0.3f + 1.1f * surge);
            float force = Mathf.Clamp((aim - Vector3.Dot(velocity, dir)) * CrawlGain * _mass, 0f, p.CrawlMaxForce);
            chest.AddForce(dir * (0.7f * force), ForceMode.Force);
            pelvis.AddForce(dir * (0.3f * force), ForceMode.Force);
            float lifted = chest.mass + (head != null ? head.mass : 0f);
            chest.AddForce(Vector3.up * (0.3f * lifted * -Physics.gravity.y * surge), ForceMode.Force);
            return force;
        }

        // ---------- Joint targets ----------

        // A hinge (waist, neck, elbow, hip, knee) in joint space: flexion about +X, twist about Y, side bend about Z, each
        // kept inside the joint's limits (a drive pushing into a limit only makes the solver fight).
        private void Hinge(NpcRagdollProfile p, int part, float flex, float twist, float side, float spring, float damper, float max)
        {
            if (part < 0) return;
            Part pp = p.Parts[part];
            flex = Mathf.Clamp(flex, pp.LowX, pp.HighX);
            twist = Mathf.Clamp(twist, -pp.LimitY, pp.LimitY);
            side = Mathf.Clamp(side, -pp.LimitZ, pp.LimitZ);
            Quaternion target = Quaternion.AngleAxis(flex, Vector3.right) * Quaternion.AngleAxis(twist, Vector3.up) *
                                Quaternion.AngleAxis(side, Vector3.forward);
            _ragdoll.Drive(part, target, spring, damper, max);
        }

        /// <summary>The joint-space target that points a ball joint's bone (along part.Axis) along 'want' (a direction in the
        /// parent part's bone frame), swung from its reference without extra twist: target = W^-1 · rel^-1 · reference · W
        /// with rel = the wanted rotation relative to the parent and W = frame (JointFrame of the joint's axes).</summary>
        public static Quaternion ShoulderTarget(Part part, Quaternion frame, Vector3 want)
        {
            Vector3 from = part.Reference * part.Axis.normalized;
            Quaternion rel = Quaternion.FromToRotation(from, want.normalized) * part.Reference;
            return Quaternion.Inverse(frame) * Quaternion.Inverse(rel) * part.Reference * frame;
        }

        /// <summary>A ConfigurableJoint's frame: joint space (X = axis, Y = secondary axis) into the body's local space.</summary>
        public static Quaternion JointFrame(Vector3 axis, Vector3 secondary)
        {
            Vector3 right = axis.normalized;
            Vector3 forward = Vector3.Cross(axis, secondary).normalized;
            Vector3 up = Vector3.Cross(forward, right).normalized;
            return Quaternion.LookRotation(forward, up);
        }
    }
}
