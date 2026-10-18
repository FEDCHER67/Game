using System.Collections.Generic;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>One captured crowd NPC (capture → delivery stage A). Added the first time he is knocked down and kept
    /// until he is laid on the operating table. It owns nothing of the NPC's movement: GreyboxNpc, its ragdoll and the
    /// van keep doing that. It adds what travels with the body (spec §3):
    /// - his OperationState, ticked here by the unchanged OperationRules (anesthesia residual / sleep, overdose death,
    ///   blood portions, corpse decay; D1, D7, D10), and handed over to the table as the same object;
    /// - zip ties (§5.2): feet keep him down crawling, hands + feet stop him crawling out of the van and make him 30 %
    ///   easier to carry, hands stop the wall knock; small dark bands on the wrists/ankles and a soft spring that keeps a
    ///   lying body's wrists / ankles together.
    /// While he sleeps or is dead the stun timer is pinned so he stays limp (eyes shut) and never gets up.</summary>
    [DefaultExecutionOrder(-40)] // after GreyboxVanCargo (-50) sets CrawlToward, before GreyboxNpc (0) reads it and ticks the stun
    public sealed class CaptureNpc : MonoBehaviour
    {
        public static readonly List<CaptureNpc> All = new List<CaptureNpc>();
        /// <summary>Stun seconds he still lies limp after the anesthesia wears off, before the usual Groggy part.</summary>
        public const float WakeTail = 5f;
        /// <summary>Sleep (s) at which a sitting / escaping / rising NPC slumps down.</summary>
        public const float SlumpSleep = 1.5f;
        private const float TieSpringRest = 0.09f, TieSpring = 900f, TieDamper = 40f, TieMaxForce = 260f;

        public GreyboxNpc Npc { get; private set; }
        public CaptureFacts Facts { get; private set; }
        public OperationState State { get; private set; }
        public OperationRules Rules { get; private set; }
        public string PatientId => Facts != null ? Facts.patientId : "";
        public bool Alive => State != null && State.alive;
        public bool Asleep => State != null && State.Sleeping;
        public Restraints Ties => Facts != null ? Facts.restraints : default;
        /// <summary>Lying limp in the first part of a stun (or asleep): not fighting.</summary>
        public bool KnockedOutCold => Npc != null && Npc.State == NpcState.Down && Npc.Phase == StunPhase.Out;
        public bool Admitted { get; set; }
        public float LastDoseAt { get; private set; } = -10f;
        public float LastBloodAt { get; private set; } = -10f;

        private float pendingDose;
        private float[] kickTear;
        private float kickImpulse;
        private bool scaledKicks;
        private bool wasAlive = true;
        private static WeaponStun slumpWeapon;
        private readonly Transform[] wrist = new Transform[2], ankle = new Transform[2];
        private readonly Transform[] upperArm = new Transform[2], foreArm = new Transform[2];
        private Transform hips, spine2;
        private GameObject[] bands;
        private LineRenderer handLink, footLink;
        private float behindBack;

        public static CaptureNpc Of(GreyboxNpc npc) => npc != null && npc.TryGetComponent(out CaptureNpc c) ? c : null;

        public void Bind(CaptureFacts facts, OperationState state, OperationTuning tuning)
        {
            Npc = GetComponent<GreyboxNpc>();
            Facts = facts;
            State = state;
            Rules = new OperationRules(state, tuning);
            wasAlive = state.alive;
            FindBones();
            if (!All.Contains(this)) All.Add(this);
            ApplyTies(true);
        }

        private void OnEnable() { if (Facts != null && !All.Contains(this)) All.Add(this); }
        private void OnDisable() => All.Remove(this);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { All.Clear(); slumpWeapon = null; }

        // ---------- what the field kit calls ----------

        /// <summary>Anesthesia pushed this frame (consumed by the next rules tick, the table's dose model).</summary>
        public void QueueDose(float amount)
        {
            if (amount <= 0f || !Alive) return;
            pendingDose += amount;
            LastDoseAt = Time.time;
        }

        /// <summary>Fills the field blood syringe; true when a portion completed (OperationRules.FillBlood).</summary>
        public bool DrawBlood(ref float fill, float seconds)
        {
            LastBloodAt = Time.time;
            bool done = Rules.FillBlood(ref fill, seconds);
            if (done) Debug.Log($"[CAPTURE] blood portion {State.bloodPortions} from {PatientId} alive={State.alive}");
            return done;
        }

        public FieldRefusal CanDrawBlood() =>
            CaptureRules.CanDrawBlood(State, KnockedOutCold, Ties, Rules.Tuning.fatalPortion);

        public bool CanBeTied => Npc != null && Npc.State == NpcState.Down;

        public void Tie(TieTarget target)
        {
            if (target == TieTarget.None) return;
            Facts.restraints = CaptureRules.Apply(Facts.restraints, target);
            Debug.Log($"[CAPTURE] tie {target} on {PatientId}: {Facts.restraints}");
            ApplyTies(true);
        }

        public void SetTies(Restraints r)
        {
            Facts.restraints = r;
            ApplyTies(true);
        }

        // ---------- tick ----------

        private void FixedUpdate()
        {
            if (Npc == null || State == null || Admitted) return;
            float dose = pendingDose;
            pendingDose = 0f;
            Rules.Tick(Time.fixedDeltaTime, dose, false);
            Facts.condition = Npc.Condition;
            if (wasAlive && !State.alive)
            {
                Debug.Log($"[CAPTURE] {PatientId} died in the field: {State.deathCause}");
                CaptureDirector.Instance?.Toast("Он больше не дышит… передоз", CaptureHud.Bad);
            }
            wasAlive = State.alive;
            Restraints r = Facts.restraints;
            // Hands + feet: no crawling for a cargo door (the van's escape sets CrawlToward earlier in this physics step).
            if (!CaptureRules.CanLeaveVanAlone(r) && Npc.InCargo) Npc.CrawlToward = false;
            TieSprings(r);
        }

        private void Update()
        {
            if (Npc == null || State == null || Admitted) return;
            Pin();
            ApplyTies(false);
        }

        // Asleep or dead: pinned limp (the stun timer never runs out). Feet tied: never stands up, crawls (Groggy).
        private void Pin()
        {
            bool dead = !State.alive;
            bool sleeping = State.Sleeping;
            if ((dead || sleeping) && Npc.State != NpcState.Down && Npc.State != NpcState.Free && (dead || State.sleepRemaining >= SlumpSleep))
                Slump();
            if (Npc.State != NpcState.Down) return;
            if (dead)
            {
                Npc.StunLeft = Npc.StunTotal = 9999f;
                Npc.Phase = StunPhase.Out;
                return;
            }
            if (sleeping)
            {
                float left = State.sleepRemaining + WakeTail;
                Npc.StunLeft = Npc.StunTotal = Mathf.Max(left, Npc.StunLeft);
                Npc.Phase = StunPhase.Out;
                return;
            }
            if (CaptureRules.StaysDown(Facts.restraints) && Npc.StunLeft < 1.5f)
            {
                // Groggy share of a 10 s stun: crawls and kicks, never wakes to his feet.
                Npc.StunTotal = 10f;
                Npc.StunLeft = 3f;
            }
        }

        /// <summary>After a load: a free copy of his crowd template goes down (no push, no cost) and is laid where he lay,
        /// head that way, with the saved stun.</summary>
        public void PutDownAt(Vector3 ground, Vector3 headDirection, bool faceUp, float stunLeft, float stunTotal)
        {
            if (Npc.State != NpcState.Down) Slump();
            transform.position = ground;
            Physics.SyncTransforms();
            if (Npc.Ragdoll != null && Npc.Ragdoll.Active) Npc.Ragdoll.PlaceLying(ground, headDirection, faceUp);
            else if (Npc.PhysicalBody != null && Npc.PhysicalBody.Active) Npc.PhysicalBody.PlaceLying(ground, headDirection);
            Npc.StunLeft = Mathf.Max(0.5f, stunLeft);
            Npc.StunTotal = Mathf.Max(Npc.StunLeft, stunTotal);
            Pin();
        }

        /// <summary>Sitting in the van, running for a door or rising from a get-up when the anesthesia takes: down where he
        /// is, through GreyboxNpc.Hit with no push and no condition cost (a sitter lies down along the bay).</summary>
        private void Slump()
        {
            if (slumpWeapon == null)
            {
                slumpWeapon = ScriptableObject.CreateInstance<WeaponStun>();
                slumpWeapon.name = "Anesthesia slump (code)";
                slumpWeapon.hideFlags = HideFlags.DontSave;
                slumpWeapon.BaseSeconds = 6f;
                slumpWeapon.Spread = 0f;
            }
            float impulse = Npc.HitImpulse, cost = Npc.ReStunConditionCost;
            Npc.HitImpulse = 0f;
            Npc.ReStunConditionCost = 0f;
            Vector3 at = Npc.Center;
            Npc.Hit(slumpWeapon, HitZone.Torso, at, at);
            Npc.HitImpulse = impulse;
            Npc.ReStunConditionCost = cost;
            Debug.Log($"[CAPTURE] {PatientId} slumps ({(State.alive ? "asleep" : "dead")})");
        }

        // ---------- ties ----------

        private void FindBones()
        {
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
            {
                switch (t.name)
                {
                    case "mixamorig:LeftHand": wrist[0] = t; break;
                    case "mixamorig:RightHand": wrist[1] = t; break;
                    case "mixamorig:LeftFoot": ankle[0] = t; break;
                    case "mixamorig:RightFoot": ankle[1] = t; break;
                    case "mixamorig:LeftArm": upperArm[0] = t; break;
                    case "mixamorig:RightArm": upperArm[1] = t; break;
                    case "mixamorig:LeftForeArm": foreArm[0] = t; break;
                    case "mixamorig:RightForeArm": foreArm[1] = t; break;
                    case "mixamorig:Hips": hips = t; break;
                    case "mixamorig:Spine2": spine2 = t; break;
                }
            }
        }

        private void ApplyTies(bool changed)
        {
            Restraints r = Facts.restraints;
            Npc.HandsBound = r.hands;
            bool both = r.Both;
            if (both != scaledKicks)
            {
                if (both)
                {
                    kickTear = (float[])Npc.KickTearChance.Clone();
                    kickImpulse = Npc.KickImpulse;
                    for (int i = 0; i < Npc.KickTearChance.Length; i++) Npc.KickTearChance[i] *= CaptureRules.BothTiedResistance;
                    Npc.KickImpulse *= CaptureRules.BothTiedResistance;
                }
                else if (kickTear != null)
                {
                    Npc.KickTearChance = kickTear;
                    Npc.KickImpulse = kickImpulse;
                }
                scaledKicks = both;
            }
            if (changed) CaptureTieVisuals.Ensure(ref bands, ref handLink, ref footLink, wrist, ankle, r, transform);
            CaptureTieVisuals.UpdateLinks(handLink, footLink, wrist, ankle, r);
        }

        // A lying ragdoll with tied wrists / ankles: a soft spring between the two forearms / calves at the hands / feet.
        private void TieSprings(Restraints r)
        {
            NpcRagdoll rag = Npc.Ragdoll;
            if (rag == null || !rag.Active || rag.Profile == null) return;
            if (r.hands) Spring(rag, NpcRagdollProfile.Kind.ForeArm, wrist);
            if (r.feet) Spring(rag, NpcRagdollProfile.Kind.Calf, ankle);
        }

        private static void Spring(NpcRagdoll rag, NpcRagdollProfile.Kind kind, Transform[] ends)
        {
            if (ends[0] == null || ends[1] == null) return;
            Rigidbody a = rag.BodyOf(rag.Profile.IndexOf(kind, NpcSide.Left));
            Rigidbody b = rag.BodyOf(rag.Profile.IndexOf(kind, NpcSide.Right));
            if (a == null || b == null) return;
            Vector3 pa = ends[0].position, pb = ends[1].position;
            Vector3 d = pb - pa;
            float dist = d.magnitude;
            if (dist <= TieSpringRest || dist < 1e-4f) return;
            Vector3 n = d / dist;
            float closing = Vector3.Dot(b.GetPointVelocity(pb) - a.GetPointVelocity(pa), n);
            float f = Mathf.Clamp((dist - TieSpringRest) * TieSpring + closing * TieDamper, 0f, TieMaxForce);
            a.AddForceAtPosition(n * f, pa);
            b.AddForceAtPosition(-n * f, pb);
        }

        // Hands tied and on his feet / sitting (the Animator drives the arms): the arms go behind his back after the
        // animation, so the wrists meet at the lower back.
        private void LateUpdate()
        {
            if (Npc == null || Facts == null || Admitted) return;
            bool animated = Npc.Ragdoll == null || !Npc.Ragdoll.Active;
            float want = Facts.restraints.hands && State.alive && animated ? 1f : 0f;
            behindBack = Mathf.MoveTowards(behindBack, want, Time.deltaTime / 0.25f);
            if (behindBack > 0.001f && hips != null) CaptureTieVisuals.ArmsBehindBack(hips, spine2, upperArm, foreArm, wrist, behindBack);
            CaptureTieVisuals.UpdateLinks(handLink, footLink, wrist, ankle, Facts.restraints);
        }

        private void OnDestroy()
        {
            All.Remove(this);
        }
    }
}
