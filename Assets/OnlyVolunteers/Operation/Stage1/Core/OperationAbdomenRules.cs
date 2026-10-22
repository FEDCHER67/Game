using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>v04: the one shared belly incision and the liver loop extend the existing rules; extraction, damage and
    /// mortality stay in OperationState.cs. Guide 3 is the belly line; guide 2 is the loop around the liver.
    /// The liver loop may be cut either way round: the first few centimetres pick the direction, then progress follows
    /// the cursor's angle round the loop (unwrapped against the progress so the seam closes cleanly).</summary>
    public sealed partial class OperationRules
    {
        public float GuideProgress(int guide) => guide == OperationAbdomenGeometry.ZoneGuide ? (State.BellyClosed ? State.zoneReopen : State.zoneCut)
            : guide == 2 ? State.organs[2].connectionCut : 0f;
        /// <summary>+1 or -1 once the liver loop has a direction; the belly line always runs one way.</summary>
        public int GuideDirection(int guide) => guide == 2 ? State.organs[2].connectionDirection : 1;

        private bool SharedGuideOpen(int guide)
        {
            if (!tuning.sharedAbdomen) return false;
            // Round 4 (decision 4): a closed belly (seam, begun seam or the dead-body patch) opens again along the same line.
            if (guide == OperationAbdomenGeometry.ZoneGuide) return !State.zoneOpened || State.BellyClosed;
            if (guide != 2 || !State.zoneOpened) return false;
            var liver = State.organs[2];
            return !liver.removed && !liver.Released;
        }

        /// <summary>Guide coordinate -> progress units. Belly: the projection on the line. Liver loop: 'raw' is the angle
        /// (0..1 round from the seam toward the marker's +X); before the direction is settled it is the distance from the seam either way.</summary>
        private float SharedAlong(int guide, float raw, out int sign)
        {
            sign = 1;
            if (guide == OperationAbdomenGeometry.ZoneGuide) return raw;
            var liver = State.organs[2];
            float progress = liver.connectionCut;
            float a = Mathf.Repeat(raw, 1f);
            if (liver.connectionDirection == 0 || progress < OperationAbdomenGeometry.LoopLockAt)
            {
                float sigma = a > 0.5f ? a - 1f : a;
                sign = sigma < 0f ? -1 : 1;
                return Mathf.Abs(sigma);
            }
            sign = liver.connectionDirection;
            float s = sign > 0 ? a : Mathf.Repeat(1f - a, 1f);
            float best = s;
            if (Mathf.Abs(s - 1f - progress) < Mathf.Abs(best - progress)) best = s - 1f;
            if (Mathf.Abs(s + 1f - progress) < Mathf.Abs(best - progress)) best = s + 1f;
            return best;
        }

        /// <summary>A stroke starts on the guide band near the start dot, or near where the last stroke stopped.</summary>
        public bool CanBeginSharedGuide(int guide, float along, float offset)
        {
            if (!Finite(along) || !Finite(offset) || !SharedGuideOpen(guide)) return false;
            if (Mathf.Abs(offset) > OperationAbdomenGeometry.Tolerance(tuning, guide)) return false;
            float progress = GuideProgress(guide);
            float at = SharedAlong(guide, along, out _);
            if (guide == OperationAbdomenGeometry.ZoneGuide)
                return at >= -tuning.cutStartSlack && at <= progress + tuning.cutResumeWindow;
            return at >= progress - OperationAbdomenGeometry.LoopBackSlack && at <= progress + OperationAbdomenGeometry.LoopResumeWindow;
        }

        public CutStep CutSharedGuide(int guide, float along, float offset, float seconds, float offLineTravel = 0f)
        {
            if (!Finite(along) || !Finite(offset) || !Finite(seconds) || seconds <= 0f ||
                !Finite(offLineTravel) || offLineTravel < 0f || !SharedGuideOpen(guide)) return CutStep.None;
            lastSeconds = seconds;
            bool zone = guide == OperationAbdomenGeometry.ZoneGuide;
            var liver = State.organs[2];
            if (Mathf.Abs(offset) > OperationAbdomenGeometry.Tolerance(tuning, guide))
            {
                if (zone) State.zoneOffLine = Mathf.Min(2f, State.zoneOffLine + offLineTravel);
                else liver.offLine = Mathf.Min(2f, liver.offLine + offLineTravel);
                return CutStep.OffLine;
            }
            float previous = GuideProgress(guide);
            float target = SharedAlong(guide, along, out int sign);
            // A leap round the loop between two samples (a flick across the liver) is not a cut.
            if (!zone && target - previous > OperationAbdomenGeometry.LoopJumpLimit) return CutStep.None;
            float delta = Mathf.Min(Mathf.Clamp01(target) - previous,
                seconds * tuning.cutSpeed / OperationAbdomenGeometry.GuideLength(tuning, guide));
            if (delta <= 0f) return CutStep.None;
            float next = Mathf.Min(1f, previous + delta);
            bool neat = Mathf.Abs(offset) <= tuning.neatTolerance;
            if (zone && State.BellyClosed) return Reopen(previous, target);
            if (zone)
            {
                State.zoneCut = next;
                if (neat) State.zoneNeatCut += delta; else State.zoneSloppyCut += delta;
                // Keep the existing organ view/save fields coherent for the unchanged HUD and extraction rules.
                foreach (var organ in State.organs) organ.cut = next;
                if (next < 0.995f) return CutStep.Advanced;
                State.zoneOpened = true; State.zoneCut = 1f;
                foreach (var organ in State.organs) organ.cut = 1f;
                if (!State.zoneSloppyApplied && State.zoneSloppyCut + State.zoneOffLine * tuning.offLineWeight > tuning.sloppyFraction)
                {
                    State.zoneSloppyApplied = true;
                    foreach (var organ in State.organs)
                        if (!organ.removed) { organ.damage += tuning.sloppyLoss; organ.sloppyApplied = true; }
                    Emit(PatientCue.SloppyCut);
                }
                Emit(PatientCue.IncisionOpened);
                return CutStep.Completed;
            }
            // The direction stays open for the first few centimetres (a wiggle either way is harmless), then locks.
            if (liver.connectionDirection == 0 || previous < OperationAbdomenGeometry.LoopLockAt) liver.connectionDirection = sign;
            liver.connectionCut = next;
            if (neat) liver.neatCut += delta; else liver.sloppyCut += delta;
            // Each third of the loop releases one of the liver's three connections; no timed snip can bypass the loop.
            for (int c = 0; c < liver.connections.Length; c++)
                if (liver.connections[c] < 1f && next + 0.005f >= (c + 1f) / liver.connections.Length)
                { liver.connections[c] = 1f; Emit(PatientCue.ConnectionReleased); }
            if (next < 0.995f) return CutStep.Advanced;
            liver.connectionCut = 1f;
            for (int c = 0; c < liver.connections.Length; c++) liver.connections[c] = 1f;
            if (!liver.connectionSloppyApplied && liver.sloppyCut + liver.offLine * tuning.offLineWeight > tuning.sloppyFraction)
            { liver.connectionSloppyApplied = true; liver.damage += tuning.sloppyLoss; Emit(PatientCue.SloppyCut); }
            return CutStep.Completed;
        }

        /// <summary>Round 4 (decision 4): one scalpel stroke along the line (reopenSpeedFactor x the cut speed) reopens a sutured,
        /// partly sewn or patched belly. The insides stay as they were (no new sloppy loss, released connections and removed
        /// organs unchanged), spoilage simply continues; the belly can be sewn up again.</summary>
        private CutStep Reopen(float previous, float target)
        {
            float delta = Mathf.Min(Mathf.Clamp01(target) - previous, Mathf.Max(1f, tuning.reopenSpeedFactor) *
                tuning.cutSpeed / OperationAbdomenGeometry.GuideLength(tuning, OperationAbdomenGeometry.ZoneGuide) * lastSeconds);
            if (delta <= 0f) return CutStep.None;
            State.zoneReopen = Mathf.Min(1f, previous + delta);
            if (State.zoneReopen < 0.995f) return CutStep.Advanced;
            State.sutured = false; State.skinPatched = false; State.zoneSuture = 0f; State.zoneReopen = 0f;
            Emit(PatientCue.Reopened);
            return CutStep.Completed;
        }
        private float lastSeconds;

        /// <summary>Round 4: a dead body leaving the table opened and unsewn gets the plain skin patch (no stitches).</summary>
        public void PatchIfOpen()
        {
            if (!State.zoneOpened || State.sutured) return;
            State.skinPatched = true; State.zoneSuture = 0f; State.zoneReopen = 0f;
        }

        // ---------- suturing (round 3: every operation ends with sewing the incision up) ----------
        /// <summary>Stitches done (0..tuning.sutureStitches), from the seam progress.</summary>
        public int Stitches => State.sutured ? Mathf.Max(1, tuning.sutureStitches) : Mathf.FloorToInt(State.zoneSuture * Mathf.Max(1, tuning.sutureStitches) + 0.0001f);

        /// <summary>A suturing stroke starts on the incision line at the top (head) end, or near where the seam stopped. Only
        /// after the opening was made, never twice.</summary>
        public bool CanBeginSuture(float along, float offset)
        {
            if (!Finite(along) || !Finite(offset) || !State.zoneOpened || State.sutured || State.skinPatched) return false;
            if (Mathf.Abs(offset) > OperationAbdomenGeometry.Tolerance(tuning, OperationAbdomenGeometry.ZoneGuide)) return false;
            return along >= State.zoneSuture - tuning.cutStartSlack && along <= State.zoneSuture + tuning.cutResumeWindow;
        }

        /// <summary>Sews along the line like the cut (same coordinates: 0 head end .. 1 pubic end), at most sutureSpeed.
        /// Each finished stitch emits Stitch, the last one Sutured; the belly is closed from then on (no organ access).</summary>
        public CutStep Suture(float along, float offset, float seconds)
        {
            if (!Finite(along) || !Finite(offset) || !Finite(seconds) || seconds <= 0f || !State.zoneOpened || State.sutured || State.skinPatched) return CutStep.None;
            if (Mathf.Abs(offset) > OperationAbdomenGeometry.Tolerance(tuning, OperationAbdomenGeometry.ZoneGuide)) return CutStep.OffLine;
            float previous = State.zoneSuture;
            float delta = Mathf.Min(Mathf.Clamp01(along) - previous,
                seconds * tuning.sutureSpeed / OperationAbdomenGeometry.GuideLength(tuning, OperationAbdomenGeometry.ZoneGuide));
            if (delta <= 0f) return CutStep.None;
            int before = Stitches;
            State.zoneSuture = Mathf.Min(1f, previous + delta);
            if (State.zoneSuture >= 0.995f) State.zoneSuture = 1f;
            int after = Mathf.FloorToInt(State.zoneSuture * Mathf.Max(1, tuning.sutureStitches) + 0.0001f);
            for (int k = before; k < after; k++) Emit(PatientCue.Stitch);
            if (State.zoneSuture < 1f) return CutStep.Advanced;
            State.sutured = true; State.unbuckleProgress = 0f;
            Emit(PatientCue.Sutured);
            return CutStep.Completed;
        }

        /// <summary>Old saves keep already released connections, grades and rolled outcomes. A partial old per-organ
        /// incision becomes shared progress; one completed old opening provides access to the shared zone.</summary>
        public void MigrateSharedOpening()
        {
            if (!tuning.sharedAbdomen || State.zoneOpened) return;
            float progress = State.zoneCut;
            foreach (var organ in State.organs) progress = Mathf.Max(progress, organ.cut);
            State.zoneCut = progress;
            State.zoneOpened = progress >= 1f;
            foreach (var organ in State.organs) organ.cut = progress;
        }
    }

    /// <summary>Pure geometry of the v04 guides. Belly line: zone-local metres (OperationAbdomen.ZonePose). Liver loop:
    /// liver-marker-local metres, an ellipse round the marker with its seam (start dot) at the top (+Y, toward the head).</summary>
    public static class OperationAbdomenGeometry
    {
        public const int ZoneGuide = 3;
        /// <summary>Loop fraction after which the direction round the liver is fixed.</summary>
        public const float LoopLockAt = 0.08f;
        /// <summary>A loop stroke may start this far behind / ahead of the current progress (loop fractions).</summary>
        public const float LoopBackSlack = 0.1f, LoopResumeWindow = 0.2f;
        /// <summary>Largest step round the loop one sample may advance (loop fractions); larger leaps are ignored.</summary>
        public const float LoopJumpLimit = 0.25f;

        /// <summary>Half-width of the band that counts as "on the guide". The loop band stops well short of its centre,
        /// so cutting across the liver never counts as going round it.</summary>
        public static float Tolerance(OperationTuning tuning, int guide) => guide == ZoneGuide ? tuning.cutTolerance
            : Mathf.Min(tuning.cutTolerance, 0.6f * Mathf.Min(tuning.liverLoopRadius.x, tuning.liverLoopRadius.y));

        public static float GuideLength(OperationTuning tuning, int guide) => guide == ZoneGuide ? tuning.abdomenCutLength :
            Mathf.PI * (3f * (tuning.liverLoopRadius.x + tuning.liverLoopRadius.y) -
                Mathf.Sqrt((3f * tuning.liverLoopRadius.x + tuning.liverLoopRadius.y) *
                    (tuning.liverLoopRadius.x + 3f * tuning.liverLoopRadius.y)));

        /// <summary>Point at 'along' (0 = start dot); direction &gt;= 0 runs from the seam toward the marker's +X (counter-clockwise on the top camera, whose right is the marker's -X), negative the other way.</summary>
        public static Vector3 Point(OperationTuning tuning, int guide, float along, int direction = 1)
        {
            if (guide == ZoneGuide) return tuning.anatomicalLayout
                ? Vector3.LerpUnclamped(OperationAnatomyV02.Start(tuning), OperationAnatomyV02.End(tuning), along)
                : new Vector3(0f, (0.5f - along) * tuning.abdomenCutLength, 0f);
            float angle = along * Mathf.PI * 2f * (direction < 0 ? -1f : 1f);
            return new Vector3(Mathf.Sin(angle) * tuning.liverLoopRadius.x, Mathf.Cos(angle) * tuning.liverLoopRadius.y, tuning.anatomicalLayout ? 0f : LoopHeight)
                + (tuning.anatomicalLayout ? OperationAnatomyV02.LiverLoopCenter : Vector3.zero);
        }
        /// <summary>Loop plane above the liver marker: high enough that the whole (tilted) loop clears the opening's floor.</summary>
        public const float LoopHeight = 0.03f;

        /// <summary>(along, signed offset in metres). Belly: projection on the line. Loop: the raw angle 0..1 in the positive direction
        /// from the seam (the rules unwrap it) and the radial distance from the loop.</summary>
        public static Vector2 Coordinates(OperationTuning tuning, int guide, Vector3 local)
        {
            if (guide == ZoneGuide) return tuning.anatomicalLayout
                ? new Vector2((OperationAnatomyV02.Start(tuning).y - local.y) / (OperationAnatomyV02.Start(tuning).y - OperationAnatomyV02.End(tuning).y), local.x)
                : new Vector2(0.5f - local.y / tuning.abdomenCutLength, local.x);
            if (tuning.anatomicalLayout) local -= OperationAnatomyV02.LiverLoopCenter;
            float x = local.x / tuning.liverLoopRadius.x, y = local.y / tuning.liverLoopRadius.y;
            float along = Mathf.Repeat(Mathf.Atan2(x, y) / (Mathf.PI * 2f), 1f);
            float radius = Mathf.Sqrt(x * x + y * y);
            return new Vector2(along, (radius - 1f) * Mathf.Min(tuning.liverLoopRadius.x, tuning.liverLoopRadius.y));
        }
    }
}
