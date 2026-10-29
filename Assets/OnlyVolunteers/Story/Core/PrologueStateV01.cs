using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Story
{
    // Append only: the numeric values are saved.
    public enum PrologueStage { NotStarted = 0, Intro = 1, Tutorial = 2, Completed = 3 }
    /// <summary>The opening's beats in order (PLAYER stage brief §3): drinking by the wagons, broke talk, the remembered
    /// blood notice ("nobody said it had to be our blood"), the addict noticed, the decision, hand-off to the player.</summary>
    public enum IntroBeat { Drinking = 0, BrokeTalk = 1, BloodNoticeMemory = 2, AddictNoticed = 3, Decision = 4, HandOff = 5 }
    /// <summary>How a scene is staged: a solo world is genuinely solitary (inner thoughts); a co-op world with one
    /// participant present uses the same solitary staging without changing the saved mode; two or more = banter.</summary>
    public enum PrologueStaging { Solo = 0, CoopSolitary = 1, CoopGroup = 2 }
    public enum TargetFate { Unbound = 0, Alive = 1, Dead = 2 }
    /// <summary>The introductory first blood draw: Idle (not started) → Cinematic (the valid draw started, presentation
    /// running) → Committed (the ONE authoritative extraction commit happened) → Done (cameras/input restored).</summary>
    public enum FirstDrawPhase { Idle = 0, Cinematic = 1, Committed = 2, Done = 3 }
    /// <summary>Tutorial hints in teaching order. Any order of real world actions counts (nothing is reset to force it).</summary>
    public enum TutorialStep { MoveLook = 0, ReadNotice = 1, PickUpSyringe = 2, KnockOut = 3, DrawBlood = 4, CallBuyer = 5, SellBlood = 6 }
    /// <summary>The post-death Tramduro episode: decided (Pending, waiting for a safe moment after the fall) → its
    /// presentation Started → Done. A load turns Started into Done (never replayed to everyone).</summary>
    public enum BeatPhase { None = 0, Pending = 1, Started = 2, Done = 3 }

    /// <summary>The opening/tutorial block of one world (saved with the world, host-owned). version 0 = absent: a world
    /// made before this block (it never gets an intro replayed; see PrologueState.FromSave).</summary>
    [Serializable]
    public sealed class PrologueSaveData
    {
        public int version;
        public int stage;
        public int introBeat;
        public bool introSkipped;
        public int staging;
        public int introParticipants;
        public string targetPersonId = "";
        public int targetFate;
        public int firstDraw;
        public bool firstDrawSkipped;
        public string firstDrawActor = "";
        public string firstDrawCommit = "";
        public List<string> tutorialDone = new List<string>();
        public bool tramduroFired;
        public int tramduroPhase;
        public int tramduroStaging;
        public int tramduroParticipants;
        /// <summary>The first target died without the tutorial extraction and the second wagon addict took over (once).</summary>
        public bool targetRebound;
        public string lostTargetPersonId = "";

        public PrologueSaveData Copy()
        {
            var c = (PrologueSaveData)MemberwiseClone();
            c.tutorialDone = tutorialDone != null ? new List<string>(tutorialDone) : new List<string>();
            return c;
        }
    }

    /// <summary>A one-shot story beat the server tells the PRESENT participants to play. Fire false = nothing to play.</summary>
    public readonly struct PrologueBeat
    {
        public readonly string BeatId;
        public readonly PrologueStaging Staging;
        public readonly int Participants;
        public PrologueBeat(string beatId, PrologueStaging staging, int participants) { BeatId = beatId; Staging = staging; Participants = participants; }
        public bool Fire => !string.IsNullOrEmpty(BeatId);
        public static readonly PrologueBeat None = default;
    }

    /// <summary>
    /// Server-side rules of the opening and the tutorial (pure C#; the world save stores <see cref="ToSave"/>). The scene
    /// director (stage 2) calls these at the real events; nothing here grants items, money or XP:
    /// - New world only: <see cref="BeginIntro"/> → beats → <see cref="FinishIntro"/> or <see cref="SkipIntro"/>; both lead to
    ///   the same Tutorial (skip gives no reward and spawns nothing extra). Loading never replays a finished intro.
    /// - The tutorial target is ONE real authored person (<see cref="BindTarget"/>, once): rebinding to another id is refused
    ///   (no cloned/replacement addict).
    /// - First draw: the cinematic may start only for that living target while the commit has not happened; the commit
    ///   (portion + death by the donor rule) happens once in gameplay code and is recorded here once, skipped or not.
    /// - Tramduro: after the server-confirmed death of THAT target, with its tutorial extraction committed, the post-death
    ///   episode is decided exactly once per world (Pending → Started → Done), staged for the participants present at that
    ///   moment; duplicates, late joins and loads never replay it to everyone (TRAMDURO_ZETGRAM_NARRATIVE_SPEC v01 §5, §12.3).
    /// </summary>
    public sealed class PrologueState
    {
        public const int Version = 1;
        /// <summary>The once-only post-death beat (Tramduro resentment + "we should get him too, eventually").</summary>
        public const string TramduroBeatId = "PROLOGUE.TRAMDURO_AFTER_TARGET_DEATH.v01";
        /// <summary>Authored PersonId of the intoxicated adult addict at the wagon, the tutorial target (default 29.10).</summary>
        public const string TutorialTargetPersonId = "FOREST_WAGON_ADDICT_01";
        /// <summary>The second wagon addict (same one-extraction condition): the fallback target (default 29.10).</summary>
        public const string FallbackTargetPersonId = "FOREST_WAGON_ADDICT_02";
        /// <summary>Both wagon addicts carry the authored severe drug-intoxication condition (one blood portion OR one organ).</summary>
        public static readonly string[] WagonAddictPersonIds = { TutorialTargetPersonId, FallbackTargetPersonId };

        PrologueSaveData d;
        readonly HashSet<string> done = new HashSet<string>(StringComparer.Ordinal);

        PrologueState(PrologueSaveData data)
        {
            d = data;
            d.tutorialDone ??= new List<string>();
            foreach (string s in d.tutorialDone) done.Add(s);
        }

        /// <summary>A fresh world's prologue (not started).</summary>
        public static PrologueState New() => new PrologueState(new PrologueSaveData { version = Version });

        /// <summary>From a save. version 0 (a world made before this block, or a block that is missing) = Completed and
        /// skipped: an old world never gets the opening, the tutorial target or the Tramduro beat retro-fitted.</summary>
        public static PrologueState FromSave(PrologueSaveData data)
        {
            if (data == null || data.version <= 0)
                return new PrologueState(new PrologueSaveData { version = Version, stage = (int)PrologueStage.Completed, introSkipped = true,
                    tramduroFired = true, tramduroPhase = (int)BeatPhase.Done });
            var copy = Clone(data);
            return new PrologueState(copy);
        }

        public PrologueSaveData ToSave()
        {
            d.tutorialDone = new List<string>(done);
            d.tutorialDone.Sort(StringComparer.Ordinal);
            return Clone(d);
        }

        static PrologueSaveData Clone(PrologueSaveData s) => s.Copy();

        public PrologueStage Stage => (PrologueStage)d.stage;
        public IntroBeat Beat => (IntroBeat)d.introBeat;
        public bool IntroSkipped => d.introSkipped;
        public PrologueStaging Staging => (PrologueStaging)d.staging;
        public int IntroParticipants => d.introParticipants;
        public string TargetPersonId => d.targetPersonId ?? "";
        public TargetFate Target => (TargetFate)d.targetFate;
        public FirstDrawPhase FirstDraw => (FirstDrawPhase)d.firstDraw;
        public bool FirstDrawSkipped => d.firstDrawSkipped;
        public string FirstDrawActor => d.firstDrawActor ?? "";
        public string FirstDrawCommit => d.firstDrawCommit ?? "";
        public bool TramduroFired => d.tramduroFired;
        public BeatPhase Tramduro => (BeatPhase)d.tramduroPhase;

        public static PrologueStaging StagingFor(bool soloWorld, int participants) =>
            soloWorld ? PrologueStaging.Solo : participants >= 2 ? PrologueStaging.CoopGroup : PrologueStaging.CoopSolitary;

        // ---------- intro ----------

        /// <summary>A new world starts its opening with the participants actually present (ready) at that moment.</summary>
        public bool BeginIntro(bool soloWorld, int participants)
        {
            if (Stage != PrologueStage.NotStarted || participants < 1) return false;
            if (soloWorld) participants = 1;
            d.stage = (int)PrologueStage.Intro; d.introBeat = (int)IntroBeat.Drinking;
            d.introParticipants = participants; d.staging = (int)StagingFor(soloWorld, participants);
            return true;
        }

        /// <summary>Beats only move forward (a repeated or older beat from a late message is ignored).</summary>
        public bool AdvanceIntro(IntroBeat beat)
        {
            if (Stage != PrologueStage.Intro || (int)beat <= d.introBeat) return false;
            d.introBeat = (int)beat;
            return true;
        }

        public bool FinishIntro() => EnterTutorial(false);
        /// <summary>Skip = the same tutorial start, no reward and nothing spawned twice.</summary>
        public bool SkipIntro() => EnterTutorial(true);

        bool EnterTutorial(bool skipped)
        {
            if (Stage != PrologueStage.Intro) return false;
            d.introBeat = (int)IntroBeat.HandOff; d.introSkipped = skipped;
            d.stage = (int)PrologueStage.Tutorial;
            if (done.Contains(TutorialStep.SellBlood.ToString())) d.stage = (int)PrologueStage.Completed;
            return true;
        }

        // ---------- target ----------

        /// <summary>Binds the one real tutorial target once. The same id again = true (load, duplicate); another id = false.</summary>
        public bool BindTarget(string personId)
        {
            if (string.IsNullOrEmpty(personId)) return false;
            if (!string.IsNullOrEmpty(d.targetPersonId)) return d.targetPersonId == personId;
            d.targetPersonId = personId; d.targetFate = (int)TargetFate.Alive;
            return true;
        }

        public bool IsTarget(string personId) => !string.IsNullOrEmpty(personId) && personId == d.targetPersonId;

        public bool TargetRebound => d.targetRebound;

        /// <summary>Default 29.10: the target died WITHOUT the tutorial extraction (no commit, no Tramduro yet) → another real,
        /// living authored person (the second wagon addict) becomes the target. Once per world; never after a commit, never back
        /// to a dead id. The caller checks that the new person is alive.</summary>
        public bool RebindAfterLossWithoutExtraction(string newPersonId)
        {
            if (Target != TargetFate.Dead || d.targetRebound || d.tramduroFired || !string.IsNullOrEmpty(d.firstDrawCommit)) return false;
            if (string.IsNullOrEmpty(newPersonId) || newPersonId == d.targetPersonId) return false;
            d.lostTargetPersonId = d.targetPersonId; d.targetPersonId = newPersonId;
            d.targetFate = (int)TargetFate.Alive; d.targetRebound = true;
            d.firstDraw = (int)FirstDrawPhase.Idle; d.firstDrawActor = ""; d.firstDrawSkipped = false;
            return true;
        }

        // ---------- tutorial hints ----------

        public bool IsDone(TutorialStep step) => done.Contains(step.ToString());

        /// <summary>A real world action happened (in any order, also before the hint asked for it). Idempotent. The first
        /// sale completes the tutorial.</summary>
        public bool MarkStep(TutorialStep step)
        {
            if (!done.Add(step.ToString())) return false;
            if (step == TutorialStep.SellBlood && Stage == PrologueStage.Tutorial) d.stage = (int)PrologueStage.Completed;
            return true;
        }

        /// <summary>Already committed story facts count (a loaded or migrated world). StoryFacts.TutorialSale = sold.</summary>
        public void ReconcileFromFacts(Func<string, bool> hasFact)
        {
            if (hasFact != null && hasFact(StoryFacts.TutorialSale)) MarkStep(TutorialStep.SellBlood);
        }

        /// <summary>The hint to show now: the first step in teaching order not done yet; null outside the tutorial.</summary>
        public TutorialStep? NextHint()
        {
            if (Stage != PrologueStage.Tutorial) return null;
            foreach (TutorialStep s in Enum.GetValues(typeof(TutorialStep))) if (!IsDone(s)) return s;
            return null;
        }

        // ---------- first draw (introductory cinematic) ----------

        public bool CanBeginFirstDrawCinematic(string personId) =>
            Stage == PrologueStage.Tutorial && IsTarget(personId) && Target == TargetFate.Alive && FirstDraw == FirstDrawPhase.Idle;

        /// <summary>The valid draw passed the existing authority/ownership checks: the cinematic starts for this actor.</summary>
        public bool BeginFirstDraw(string personId, string actorId)
        {
            if (!CanBeginFirstDrawCinematic(personId) || string.IsNullOrEmpty(actorId)) return false;
            d.firstDraw = (int)FirstDrawPhase.Cinematic; d.firstDrawActor = actorId; d.firstDrawSkipped = false;
            return true;
        }

        /// <summary>Skip only changes presentation: the same gameplay action still ends through its own completion or
        /// cancellation boundary; nothing is granted here.</summary>
        public bool MarkFirstDrawSkipped()
        {
            if (FirstDraw != FirstDrawPhase.Cinematic) return false;
            d.firstDrawSkipped = true;
            return true;
        }

        /// <summary>Cancelled/failed before the commit: back to Idle, no portion, no death, the allowance is not used.</summary>
        public bool CancelFirstDraw()
        {
            if (FirstDraw != FirstDrawPhase.Cinematic) return false;
            d.firstDraw = (int)FirstDrawPhase.Idle; d.firstDrawActor = ""; d.firstDrawSkipped = false;
            return true;
        }

        /// <summary>The ONE authoritative extraction commit on the target (called by gameplay code with the minted portion id;
        /// also when the draw ran without the cinematic). A second call — another syringe, an animation event, a reload —
        /// returns false and changes nothing.</summary>
        public bool CommitFirstDraw(string personId, string portionId)
        {
            if (!IsTarget(personId) || string.IsNullOrEmpty(portionId)) return false;
            if (FirstDraw == FirstDrawPhase.Committed || FirstDraw == FirstDrawPhase.Done) return false;
            d.firstDraw = (int)FirstDrawPhase.Committed; d.firstDrawCommit = portionId;
            MarkStep(TutorialStep.DrawBlood);
            return true;
        }

        /// <summary>Cameras and input are restored: the cinematic is over for good.</summary>
        public bool FinishFirstDraw()
        {
            if (FirstDraw != FirstDrawPhase.Committed) return false;
            d.firstDraw = (int)FirstDrawPhase.Done;
            return true;
        }

        /// <summary>The acting player disconnected: before the commit the draw is cancelled (nothing granted); after it the
        /// cinematic just ends. Never an endless locked cutscene.</summary>
        public bool OnActorLost(string actorId)
        {
            if (string.IsNullOrEmpty(actorId) || actorId != d.firstDrawActor) return false;
            if (FirstDraw == FirstDrawPhase.Cinematic) return CancelFirstDraw();
            if (FirstDraw == FirstDrawPhase.Committed) return FinishFirstDraw();
            return false;
        }

        /// <summary>A load mid-cinematic: an uncommitted draw is back to Idle (its syringe follows the existing pending/cancel
        /// rules), a committed one is Done. Nothing replays.</summary>
        public void AfterLoad()
        {
            if (FirstDraw == FirstDrawPhase.Cinematic) CancelFirstDraw();
            else if (FirstDraw == FirstDrawPhase.Committed) FinishFirstDraw();
            if (Tramduro == BeatPhase.Started) d.tramduroPhase = (int)BeatPhase.Done; // its presentation counts as given
        }

        // ---------- death → Tramduro ----------

        /// <summary>The server confirmed a person's authoritative death. For the tutorial target it records the fate and, when
        /// the tutorial extraction is committed too, decides the Tramduro episode (see <see cref="TryTramduro"/>). Any other
        /// person, a duplicate event or a load = None.</summary>
        public PrologueBeat OnServerConfirmedDeath(string personId, bool soloWorld, int participantsPresent)
        {
            if (!IsTarget(personId)) return PrologueBeat.None;
            d.targetFate = (int)TargetFate.Dead;
            return TryTramduro(soloWorld, participantsPresent);
        }

        /// <summary>The episode is decided ONCE per world when both are true: the target's authoritative death and the committed
        /// tutorial extraction (TRAMDURO_ZETGRAM v01 §5: a death without that extraction does not trigger it). Call it after
        /// OnServerConfirmedDeath and after CommitFirstDraw (either order). Staged for the participants present now.</summary>
        public PrologueBeat TryTramduro(bool soloWorld, int participantsPresent)
        {
            if (d.tramduroFired || Target != TargetFate.Dead || string.IsNullOrEmpty(d.firstDrawCommit)) return PrologueBeat.None;
            int n = soloWorld ? 1 : Math.Max(1, participantsPresent);
            d.tramduroFired = true; d.tramduroPhase = (int)BeatPhase.Pending;
            d.tramduroParticipants = n; d.tramduroStaging = (int)StagingFor(soloWorld, n);
            return new PrologueBeat(TramduroBeatId, (PrologueStaging)d.tramduroStaging, n);
        }

        /// <summary>A decided episode not yet presented (e.g. the save was written between the decision and the safe moment):
        /// offered once more, re-staged for who is present now. None otherwise.</summary>
        public PrologueBeat PendingTramduro(bool soloWorld, int participantsPresent)
        {
            if (Tramduro != BeatPhase.Pending) return PrologueBeat.None;
            int n = soloWorld ? 1 : Math.Max(1, participantsPresent);
            d.tramduroParticipants = n; d.tramduroStaging = (int)StagingFor(soloWorld, n);
            return new PrologueBeat(TramduroBeatId, (PrologueStaging)d.tramduroStaging, n);
        }

        public bool MarkTramduroStarted()
        {
            if (Tramduro != BeatPhase.Pending) return false;
            d.tramduroPhase = (int)BeatPhase.Started;
            return true;
        }

        public bool MarkTramduroDone()
        {
            if (Tramduro != BeatPhase.Pending && Tramduro != BeatPhase.Started) return false;
            d.tramduroPhase = (int)BeatPhase.Done;
            return true;
        }

        /// <summary>Late joiners never get a fired beat replayed (it was a moment, not a status).</summary>
        public bool ReplayForLateJoin(string beatId) => false;
    }
}
