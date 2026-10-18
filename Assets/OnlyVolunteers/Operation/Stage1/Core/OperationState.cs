using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    // Append only: the numeric values travel over the network and into saves.
    public enum PatientCue
    {
        Placed, Aligning, Aligned, StrapChanged, LimbAdjusted, Struggling, Sleeping, Waking, Weakened, Panic, Rescue,
        ShockDeath, EscapeAttempt, FailedEscapeFall, Death, ConnectionReleased, Extracted,
        Escaped, KnockedOut, IncisionOpened, SloppyCut, DirectCut, Yank, BloodPortion, Overdosing, Dazed, BagSealed,
        // Round 3 (Claude): one stitch of the seam, the seam finished, a strap unbuckled by a free hand.
        Stitch, Sutured, Unbuckled
    }
    public enum DeathCause { None, Blood, Extraction, Overdose, Shock, FailedEscape }
    public enum CutStep { None, Advanced, OffLine, Completed }

    [Serializable]
    public sealed class OrganState
    {
        public int intrinsicGrade;
        public int damage;
        public float cut;
        public float neatCut;
        public float sloppyCut;
        public float offLine;
        public bool sloppyApplied;
        public float[] connections;
        public float pull;
        public bool removed;
        public bool rollCompleted;
        public float rolled = -1f;
        public float deathChance;
        public bool fatal;
        public int directCuts;
        public int yanks;
        /// <summary>v04: progress around the liver's attachment loop (individual organ state).</summary>
        public float connectionCut;
        public bool connectionSloppyApplied;
        /// <summary>v04: the way round the liver loop is cut (+1 counter-clockwise on the top camera, -1 clockwise, 0 not yet).</summary>
        public int connectionDirection;
        public string outputId = "";
        public int Grade => Mathf.Max(0, intrinsicGrade - damage);
        public bool Opened => cut >= 1f;
        public bool Released { get { foreach (float p in connections) if (p < 1f) return false; return true; } }
        public int CordsLeft { get { int n = 0; foreach (float p in connections) if (p < 1f) n++; return n; } }
    }

    [Serializable]
    public sealed class OperationState
    {
        public string patientId;
        public bool alive = true;
        public bool onTable;
        public bool aligned;
        public float alignment;
        /// <summary>Lying out cold off the table (fresh capture or after falling off). No escape, no interaction.</summary>
        public bool knockedOut = true;
        /// <summary>Groggy seconds right after being put on the table; the patient does not try to escape yet.</summary>
        public float dazedRemaining;
        public bool[] restraints = new bool[5];
        public float[] limbs = new float[4];
        public int bloodPortions;
        public float bloodProgress;
        public float residual;
        public float sleepRemaining;
        public float panicRemaining = -1f;
        public float escapeProgress;
        public int escapes;
        public float deathAge;
        public int corpseLoss;
        public DeathCause deathCause;
        public int extracted;
        public int kidneysExtracted;
        public OrganState[] organs;
        /// <summary>v04: one prepared abdomen opening shared by all three organ anchors.</summary>
        public bool zoneOpened;
        public float zoneCut;
        public float zoneNeatCut;
        public float zoneSloppyCut;
        public float zoneOffLine;
        public bool zoneSloppyApplied;
        public int cueSequence;
        public PatientCue lastCue;
        /// <summary>Capture → delivery (CAPTURE_DELIVERY_SPEC v01 D8): grades every organ loses when it is extracted, from
        /// the NPC's condition at the hand-over (0 for the dev patients). Applied once per organ in Extract.</summary>
        public int conditionLoss;
        /// <summary>Round 3: suturing progress along the incision line (0 head end .. 1 pubic end) and its completion.</summary>
        public float zoneSuture;
        public bool sutured;
        /// <summary>Round 3: a free hand working on the next strap (0..1 of unbuckleSeconds).</summary>
        public float unbuckleProgress;
        public bool Sleeping => alive && sleepRemaining > 0f;
        public bool Dazed => alive && onTable && dazedRemaining > 0f;
        public bool Torso => restraints.Length > 4 && restraints[4];
        public bool LimbsStrapped => restraints[0] && restraints[1] && restraints[2] && restraints[3];
        /// <summary>The belly is open and not sewn up yet: organs reachable, a living patient may not leave.</summary>
        public bool CavityOpen => zoneOpened && !sutured;
        public bool Panicking => alive && panicRemaining >= 0f;
    }

    [Serializable]
    public sealed class OperationItemState
    {
        public string id;
        public int kind; // 0 kidney, 1 liver, 2 sealed blood, 3 filled syringe (legacy v01).
        public int grade;
        public int organIndex = -1;
        public Vector3 position;
        public Quaternion rotation = Quaternion.identity;
        public float freshness;
        public bool sealedBlood;
        public bool expired;
    }

    [Serializable]
    public sealed class OperationWorldState
    {
        public OperationState patient;
        public Vector3 patientPosition;
        public Quaternion patientRotation = Quaternion.identity;
        public List<OperationItemState> items = new();
        public float[] syringeStocks = { 10f, 10f }; // v01 field, kept so old saves load.
        public Vector3[] toolPositions;               // v01 field, unused in v02 (tools always load docked).
        public bool v02;
        public float anesthesiaStock;
        public float anesthesiaBarrel;
        public float bloodFill;
        public int bagsUsedMask;
        public int bloodBagged;
        /// <summary>Round 2: where the (now movable) gurney stood; its outputs are saved in world space, so it is put back
        /// there first. Absent in older saves (the gurney then stays at its spawn).</summary>
        public bool hasTablePose;
        public Vector3 tablePosition;
        public Quaternion tableRotation = Quaternion.identity;
    }

    /// <summary>Server-owned rules. No input, network, physics or file IO; the registered PatientRecord owns State.</summary>
    public sealed partial class OperationRules
    {
        public OperationState State { get; }
        private readonly OperationTuning tuning;
        private bool struggling;
        private bool overdosing;
        public event Action<PatientCue> Cue;
        public OperationRules(OperationState state, OperationTuning config)
        {
            State = state; tuning = config;
            // Round 3: without the torso strap an old save's closed torso strap simply is not there any more.
            if (State != null && State.restraints != null && State.restraints.Length > 4 && tuning != null && !tuning.torsoStrap) State.restraints[4] = false;
        }
        public OperationTuning Tuning => tuning;
        public static OperationState Create(string id, OperationTuning config)
        {
            var state = new OperationState { patientId = id, organs = new OrganState[3] };
            for (int i = 0; i < 3; i++) state.organs[i] = new OrganState
            { intrinsicGrade = config.intrinsicGrades[i], connections = new float[config.connections[i]] };
            return state;
        }
        private void Emit(PatientCue cue) { State.lastCue = cue; State.cueSequence++; Cue?.Invoke(cue); }

        // ---------- placement / restraints ----------
        public bool BeginAlignment(float distance)
        {
            if (State.onTable || distance > tuning.placementRadius || !Finite(distance)) return false;
            State.onTable = true; State.aligned = false; State.alignment = tuning.alignmentSeconds;
            Emit(PatientCue.Placed); Emit(PatientCue.Aligning); return true;
        }
        /// <summary>Dev shortcut: the patient lies aligned on the table at once.</summary>
        public void ForcePlace()
        {
            bool was = State.onTable && State.aligned;
            State.onTable = true; State.alignment = 0f;
            if (!was) FinishAlignment();
        }
        private void FinishAlignment()
        {
            State.aligned = true; State.knockedOut = false; State.escapeProgress = 0f;
            if (State.alive) { State.dazedRemaining = tuning.dazedSeconds; Emit(PatientCue.Dazed); }
            Emit(PatientCue.Aligned);
        }
        public bool ToggleRestraint(int index)
        {
            if (!State.aligned || index < 0 || index >= 5 || !OperationStraps.Active(tuning, index)) return false;
            if (State.restraints[index] && MustSutureBeforeRelease) return false; // sew him up first
            State.unbuckleProgress = 0f;
            State.restraints[index] = !State.restraints[index]; Emit(PatientCue.StrapChanged); return true;
        }
        public void AdjustLimb(int index, float position)
        {
            if (!State.aligned || index < 0 || index >= 4 || State.restraints[index] || !Finite(position)) return;
            State.limbs[index] = Mathf.Clamp(position, -1, 1); Emit(PatientCue.LimbAdjusted);
        }
        /// <summary>Held down on the table: the torso strap (when it exists) or, round 3, all four limb straps.</summary>
        public bool Held => OperationStraps.Held(State, tuning);
        /// <summary>Round 3 (lead rule): a living patient with an open, unsutured belly is not released: no strap opens, no escape.</summary>
        public bool MustSutureBeforeRelease => State.alive && State.CavityOpen;
        public bool CanOperate(bool held) => State.onTable && State.aligned && (!State.alive || State.Sleeping || Held || held);
        public bool CanInject => State.alive && State.onTable && State.aligned;

        // ---------- time ----------
        public void Tick(float seconds, float administered, bool held)
        {
            if (seconds <= 0 || !Finite(seconds)) return;
            if (State.dazedRemaining > 0f) State.dazedRemaining = Mathf.Max(0f, State.dazedRemaining - seconds);
            if (State.onTable && !State.aligned)
            {
                State.alignment = Mathf.Max(0, State.alignment - seconds);
                if (State.alignment == 0) FinishAlignment();
            }
            if (!State.alive) { Decay(seconds); return; }
            State.residual = Mathf.Max(0, State.residual - seconds * tuning.residualPerSecond);
            bool wasSleeping = State.Sleeping;
            State.sleepRemaining = Mathf.Max(0, State.sleepRemaining - seconds);
            if (administered > 0 && Finite(administered))
            {
                State.residual += administered;
                if (State.residual > tuning.overdoseAbove) { Die(DeathCause.Overdose); return; }
                float ratio = Mathf.Clamp01(State.residual / tuning.suitableMinimum);
                State.sleepRemaining = Mathf.Max(State.sleepRemaining, tuning.sleepSeconds * ratio * ratio);
                if (State.panicRemaining >= 0 && State.residual >= tuning.suitableMinimum)
                { State.panicRemaining = -1; State.escapeProgress = 0; Emit(PatientCue.Rescue); }
            }
            bool nowOverdosing = State.residual > tuning.suitableMaximum;
            if (nowOverdosing && !overdosing) Emit(PatientCue.Overdosing);
            overdosing = nowOverdosing;
            if (!wasSleeping && State.Sleeping && State.panicRemaining < 0) Emit(PatientCue.Sleeping);
            if (wasSleeping && !State.Sleeping)
            {
                Emit(PatientCue.Waking);
                if (State.extracted > 0 && State.panicRemaining < 0)
                { State.panicRemaining = tuning.rescueSeconds; Emit(PatientCue.Panic); }
            }
            bool restrained = Held || (!tuning.torsoStrap && AnyStrapClosed);
            bool nowStruggling = State.onTable && State.aligned && !State.Sleeping && !State.Dazed && (restrained || held);
            if (nowStruggling && !struggling) Emit(PatientCue.Struggling);
            struggling = nowStruggling;
            bool awakeOnTable = State.onTable && State.aligned && !State.Sleeping && !State.Dazed && !held;
            // Round 3: a free hand unbuckles the other straps one by one (the per-strap escape steps; clips hook Unbuckled).
            if (awakeOnTable && !tuning.torsoStrap && !MustSutureBeforeRelease && NextUnbuckle(out int strap, out int hand))
            {
                State.unbuckleProgress += seconds / Mathf.Max(0.1f, tuning.unbuckleSeconds);
                if (State.unbuckleProgress >= 1f)
                {
                    State.unbuckleProgress = 0f; State.restraints[strap] = false;
                    LastUnbuckledStrap = strap; LastUnbuckledHand = hand;
                    Emit(PatientCue.Unbuckled); Emit(PatientCue.StrapChanged);
                }
            }
            else State.unbuckleProgress = 0f;
            if (State.panicRemaining >= 0)
            {
                if (!Held && !held && State.escapeProgress == 0) Emit(PatientCue.EscapeAttempt);
                if (!Held && !held) State.escapeProgress += seconds;
                State.panicRemaining = Mathf.Max(0, State.panicRemaining - seconds);
                if (State.panicRemaining <= 0) Die(!Held && !held ? DeathCause.FailedEscape : DeathCause.Shock);
            }
            else if (awakeOnTable && CanEscape)
            {
                if (State.escapeProgress == 0) Emit(PatientCue.EscapeAttempt);
                State.escapeProgress += seconds;
                if (State.escapeProgress >= tuning.escapeSeconds) Escape();
            }
            else State.escapeProgress = 0;
        }

        /// <summary>Escape-step hooks (server): the strap the free hand just opened and that hand (0 left, 1 right), valid
        /// when PatientCue.Unbuckled fires; -1 before the first. The step in progress is NextUnbuckle + State.unbuckleProgress.</summary>
        public int LastUnbuckledStrap { get; private set; } = -1;
        public int LastUnbuckledHand { get; private set; } = -1;

        private bool AnyStrapClosed { get { for (int i = 0; i < OperationStraps.Count(tuning); i++) if (State.restraints[i]) return true; return false; } }

        /// <summary>Free to slide off: with the torso strap, it open; without it, every limb strap open. Never with an
        /// open, unsutured belly (round 3 lead rule).</summary>
        public bool CanEscape => !MustSutureBeforeRelease && (tuning.torsoStrap ? !State.Torso : !AnyStrapClosed);

        /// <summary>The escape steps (hook for strap-combination clips): the next strap a FREE hand unbuckles and which hand
        /// (0 left, 1 right). Order: the other arm first, then the left leg, the right leg. None while both arms are strapped.</summary>
        public bool NextUnbuckle(out int strap, out int hand)
        {
            strap = -1; hand = -1;
            bool left = !State.restraints[0], right = !State.restraints[1];
            if (!left && !right) return false;
            hand = left ? 0 : 1;
            foreach (int i in new[] { 0, 1, 2, 3 }) if (State.restraints[i]) { strap = i; return true; }
            return false;
        }
        private void Escape()
        {
            State.onTable = State.aligned = false; State.knockedOut = true; State.escapeProgress = 0f; State.escapes++; State.unbuckleProgress = 0f;
            Array.Clear(State.restraints, 0, 5);
            Emit(PatientCue.FailedEscapeFall); Emit(PatientCue.Escaped);
        }
        public void Die(DeathCause cause)
        {
            if (!State.alive) return;
            State.alive = false; State.deathCause = cause; State.deathAge = 0;
            State.sleepRemaining = 0; State.panicRemaining = -1; State.dazedRemaining = 0;
            if (cause == DeathCause.Overdose && State.extracted == 0)
                foreach (var organ in State.organs) if (!organ.removed) organ.damage += tuning.earlyOverdoseLoss;
            if (cause == DeathCause.FailedEscape) Emit(PatientCue.FailedEscapeFall);
            if (cause == DeathCause.Shock) Emit(PatientCue.ShockDeath);
            Emit(PatientCue.Death);
        }
        private void Decay(float seconds)
        {
            State.deathAge += seconds;
            int loss = Mathf.Max(0, Mathf.FloorToInt((State.deathAge - tuning.corpseGraceSeconds) / tuning.corpseGradeSeconds));
            int delta = loss - State.corpseLoss;
            if (delta <= 0) return;
            foreach (var organ in State.organs) if (!organ.removed) organ.damage += delta;
            State.corpseLoss = loss;
        }

        // ---------- blood ----------
        /// <summary>Asleep, torso or that arm strapped, or dead; and the body still has a portion to give.</summary>
        public bool CanDrawBlood(int arm) => State.onTable && State.aligned && State.bloodPortions < tuning.fatalPortion &&
            (!State.alive || State.Sleeping || Held || (arm >= 0 && arm < 2 && State.restraints[arm]));
        /// <summary>Fills one syringe; when it is full one portion counts (2nd weakens, 3rd kills a living patient).</summary>
        public bool FillBlood(ref float fill, float seconds)
        {
            if (fill >= 1f || seconds <= 0f || !Finite(seconds) || State.bloodPortions >= tuning.fatalPortion) return false;
            fill = Mathf.Min(1f, fill + seconds / tuning.bloodSeconds);
            if (fill < 1f - 0.00001f) return false;
            fill = 1f; State.bloodPortions++;
            Emit(PatientCue.BloodPortion);
            if (State.alive)
            {
                if (State.bloodPortions == tuning.weakenedPortion) Emit(PatientCue.Weakened);
                if (State.bloodPortions >= tuning.fatalPortion) Die(DeathCause.Blood);
            }
            return true;
        }
        /// <summary>v01 API: progress stored on the patient.</summary>
        public bool CollectBlood(float seconds)
        {
            if (!State.alive || State.bloodPortions >= tuning.fatalPortion || seconds <= 0) return false;
            float fill = State.bloodProgress;
            bool done = FillBlood(ref fill, seconds);
            State.bloodProgress = done ? 0f : fill;
            return done;
        }

        // ---------- incisions ----------
        /// <summary>A stroke starts near the line, from the start point up to a little past the current progress.</summary>
        public bool CanBeginCut(int index, float along, float offset)
        {
            if (index < 0 || index >= State.organs.Length || !Finite(along) || !Finite(offset)) return false;
            var organ = State.organs[index];
            if (organ.removed || organ.cut >= 1f) return false;
            return Mathf.Abs(offset) <= tuning.cutTolerance && along >= -tuning.cutStartSlack && along <= organ.cut + tuning.cutResumeWindow;
        }
        /// <summary>Progress follows the cursor's projection on the guide, limited only by a generous speed cap.</summary>
        public CutStep CutTowards(int index, float along, float offset, float seconds)
        {
            if (index < 0 || index >= State.organs.Length || !Finite(along) || !Finite(offset) || !Finite(seconds) || seconds <= 0) return CutStep.None;
            var organ = State.organs[index];
            if (organ.removed || organ.cut >= 1f) return CutStep.None;
            float distance = Mathf.Abs(offset);
            if (distance > tuning.cutTolerance) return CutStep.OffLine;
            float target = Mathf.Clamp01(along);
            if (target <= organ.cut) return CutStep.None;
            float delta = Mathf.Min(target - organ.cut, seconds * tuning.cutSpeed / tuning.IncisionLength(index));
            organ.cut += delta;
            if (distance <= tuning.neatTolerance) organ.neatCut += delta; else organ.sloppyCut += delta;
            if (organ.cut < 0.995f) return CutStep.Advanced;
            organ.cut = 1f;
            if (!organ.sloppyApplied && organ.sloppyCut + organ.offLine * tuning.offLineWeight > tuning.sloppyFraction)
            { organ.damage += tuning.sloppyLoss; organ.sloppyApplied = true; Emit(PatientCue.SloppyCut); }
            Emit(PatientCue.IncisionOpened);
            return CutStep.Completed;
        }
        /// <summary>Cursor travel off the line during a stroke, in incision lengths.</summary>
        public void AddOffLine(int index, float lengths)
        {
            if (index < 0 || index >= State.organs.Length || !Finite(lengths) || lengths <= 0) return;
            var organ = State.organs[index];
            if (organ.removed || organ.cut >= 1f) return;
            organ.offLine = Mathf.Min(2f, organ.offLine + lengths);
        }
        /// <summary>v01 API kept for the rule tests.</summary>
        public bool Cut(int index, float along, float distance, float seconds)
        {
            var step = CutTowards(index, along, distance, seconds);
            return step == CutStep.Advanced || step == CutStep.Completed;
        }
        public void DirectCut(int index)
        {
            var organ = State.organs[index];
            if (organ.removed) return;
            organ.damage += tuning.directCutLoss; organ.directCuts++;
            Emit(PatientCue.DirectCut);
        }

        // ---------- cords ----------
        public bool SnipCord(int organIndex, int cord, float seconds)
        {
            if (organIndex < 0 || organIndex >= State.organs.Length || !Finite(seconds) || seconds <= 0) return false;
            if (tuning.sharedAbdomen && (!State.CavityOpen || organIndex == 2)) return false;
            var organ = State.organs[organIndex];
            if (organ.removed || organ.cut < 1 || cord < 0 || cord >= organ.connections.Length || organ.connections[cord] >= 1) return false;
            organ.connections[cord] = Mathf.Min(1, organ.connections[cord] + seconds / tuning.connectionSeconds);
            if (organ.connections[cord] < 1) return false;
            Emit(PatientCue.ConnectionReleased);
            return true;
        }
        public void ReleaseConnection(int organIndex, int connection, float seconds) => SnipCord(organIndex, connection, seconds);

        // ---------- pull / extraction ----------
        public bool Pull(int index, float sharedTarget, int holders, float seconds, ref bool damageLatched)
        {
            if (tuning.sharedAbdomen && !State.CavityOpen) return false;
            var organ = State.organs[index];
            if (organ.removed || !organ.Released || organ.cut < 1 || seconds <= 0 || !Finite(sharedTarget)) return false;
            if (holders == 0) { organ.pull = Mathf.MoveTowards(organ.pull, 0, seconds * tuning.springSpeed); damageLatched = false; return false; }
            float next = Mathf.MoveTowards(organ.pull, Mathf.Clamp(sharedTarget, 0, tuning.pullDistance * 1.5f),
                seconds * tuning.pullResponse * Mathf.Abs(sharedTarget - organ.pull) * Mathf.Sqrt(holders));
            if (!damageLatched && (next - organ.pull) / seconds > tuning.abruptSpeed)
            { organ.damage += tuning.abruptLoss; organ.yanks++; damageLatched = true; Emit(PatientCue.Yank); }
            organ.pull = next;
            return organ.pull >= tuning.pullDistance;
        }
        public bool Extract(int index, float random)
        {
            if (tuning.sharedAbdomen && !State.CavityOpen) return false;
            var organ = State.organs[index];
            if (organ.removed || organ.cut < 1 || !organ.Released || organ.pull < tuning.pullDistance) return false;
            organ.removed = true; organ.outputId = State.patientId + "/organ/" + index;
            if (State.conditionLoss > 0) organ.damage += State.conditionLoss; // D8: condition loss lands at extraction
            State.extracted++;
            if (index < 2) State.kidneysExtracted++;
            if (State.alive)
            {
                // Lead decision 2026-10-18: the liver, or the second kidney, is a vital removal: death at once, no roll.
                bool vital = tuning.liverOrBothKidneysFatal && (index == 2 || State.kidneysExtracted >= 2);
                organ.deathChance = vital ? 1f : Mathf.Clamp01((index == 2 ? tuning.liverChance : State.kidneysExtracted == 1 ? tuning.firstKidneyChance : tuning.secondKidneyChance)
                    + State.bloodPortions * tuning.bloodChancePerPortion);
                organ.rolled = Mathf.Clamp01(random); organ.rollCompleted = true;
                organ.fatal = vital || organ.rolled < organ.deathChance;
                if (organ.fatal) Die(DeathCause.Extraction);
                else if (!State.Sleeping && State.panicRemaining < 0)
                { State.panicRemaining = tuning.rescueSeconds; Emit(PatientCue.Panic); }
            }
            Emit(PatientCue.Extracted); return true;
        }
        public static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    }

    /// <summary>Pure table-local geometry shared by the server and the tests.</summary>
    public static class OperationGeometry
    {
        /// <summary>A released patient whose centre is above the pad (table-local) gets aligned onto the table.</summary>
        public static bool OverPad(Vector3 tableLocal, OperationTuning tuning) =>
            Mathf.Abs(tableLocal.x) <= tuning.padHalfExtents.x && Mathf.Abs(tableLocal.z) <= tuning.padHalfExtents.z &&
            tableLocal.y >= tuning.padTop - 0.15f && tableLocal.y <= tuning.padTop + 1.2f;
        /// <summary>Client points are accepted only inside the table's working volume.</summary>
        public static bool InWorkVolume(Vector3 tableLocal) =>
            OperationRules.Finite(tableLocal.x) && OperationRules.Finite(tableLocal.y) && OperationRules.Finite(tableLocal.z) &&
            Mathf.Abs(tableLocal.x) <= 1.8f && tableLocal.y >= -0.5f && tableLocal.y <= 2.4f && Mathf.Abs(tableLocal.z) <= 1.8f;
        /// <summary>Guide point in marker-local metres; along 0 is the start (pulsing dot), 1 the end.</summary>
        public static Vector3 GuidePoint(OperationTuning tuning, int organ, float along)
        {
            float l = tuning.IncisionLength(organ);
            float s = (0.5f - along) * l;
            return tuning.guideAcross[organ] ? new Vector3(-s, 0f, 0f) : new Vector3(0f, s, 0f);
        }
        /// <summary>Marker-local metres to (along, signed offset from the line).</summary>
        public static Vector2 GuideCoordinates(OperationTuning tuning, int organ, Vector3 markerLocal)
        {
            float l = tuning.IncisionLength(organ);
            if (tuning.guideAcross[organ]) return new Vector2(markerLocal.x / l + 0.5f, markerLocal.y);
            return new Vector2(0.5f - markerLocal.y / l, markerLocal.x);
        }
        /// <summary>Cord c of an organ: from its attachment on the organ to the rim of the opening (marker-local metres).</summary>
        public static void Cord(OperationTuning tuning, int organ, int cord, out Vector3 attach, out Vector3 rim)
        {
            if (tuning.anatomicalLayout && organ < 2)
            { OperationAnatomyV02.Cord(tuning, organ, cord, out attach, out rim); return; }
            if (tuning.sharedAbdomen && organ < 2)
            {
                // The cords leave the underside of the kidney and hang below its lower end, inside the shared opening
                // and above its floor, so the top camera reaches them without clicking through the kidney.
                float side = cord == 0 ? -1f : 1f;
                attach = new Vector3(side * 0.009f, -tuning.organHalfSize[organ].y * 0.5f, tuning.organLift - 0.006f);
                rim = new Vector3(side * 0.019f, -tuning.organHalfSize[organ].y - 0.026f, tuning.organLift - 0.003f);
                return;
            }
            int count = Mathf.Max(1, tuning.connections[organ]);
            float angle = (cord + 0.5f) / count * Mathf.PI * 2f + tuning.cordPhase[organ] * Mathf.Deg2Rad;
            var dir = new Vector3(Mathf.Cos(angle), Mathf.Sin(angle), 0f);
            Vector2 organHalf = tuning.organHalfSize[organ], hole = tuning.openingHalfSize[organ];
            attach = new Vector3(dir.x * organHalf.x * 0.85f, dir.y * organHalf.y * 0.85f, tuning.organLift * 0.6f);
            rim = new Vector3(dir.x * (hole.x + tuning.cordOverhang), dir.y * (hole.y + tuning.cordOverhang), -0.003f);
        }
        public static float DistanceToSegment(Vector3 p, Vector3 a, Vector3 b)
        {
            Vector3 ab = b - a; float t = ab.sqrMagnitude > 1e-8f ? Mathf.Clamp01(Vector3.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
            return Vector3.Distance(p, a + ab * t);
        }
    }

    /// <summary>Russian display names and tier colours (BUYERS_SPEC v02 labels).</summary>
    public static class OperationText
    {
        public static readonly string[] Tiers = { "Убитое", "Сойдёт", "Хорошее", "Отличное", "Идеальное" };
        public static readonly string[] TierHex = { "#8C7B6B", "#C2B23A", "#4DC25A", "#3E8DFF", "#A75CFF" };
        public static readonly string[] Straps = { "левая рука", "правая рука", "левая нога", "правая нога", "торс" };
        public static readonly string[] Organs = { "Почка (левая)", "Почка (правая)", "Печень" };
        public static readonly string[] OrganShort = { "Л. почка", "П. почка", "Печень" };
        public static string Tier(int grade) => Tiers[Mathf.Clamp(grade, 0, Tiers.Length - 1)];
        public static Color TierColor(int grade)
        {
            ColorUtility.TryParseHtmlString(TierHex[Mathf.Clamp(grade, 0, TierHex.Length - 1)], out var c); return c;
        }
        public static string Death(DeathCause cause) => cause switch
        {
            DeathCause.Blood => "кровь кончилась",
            DeathCause.Extraction => "не пережил изъятия",
            DeathCause.Overdose => "передоз наркоза",
            DeathCause.Shock => "болевой шок",
            DeathCause.FailedEscape => "неудачный побег",
            _ => ""
        };
    }
}
