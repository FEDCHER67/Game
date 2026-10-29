using NUnit.Framework;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Story.Tests
{
    public sealed class PrologueStateTests
    {
        const string Target = PrologueState.TutorialTargetPersonId;
        const string Second = PrologueState.FallbackTargetPersonId;

        static PrologueState InTutorial(bool solo = false, int participants = 2)
        {
            var p = PrologueState.New();
            Assert.True(p.BeginIntro(solo, participants));
            Assert.True(p.BindTarget(Target));
            Assert.True(p.FinishIntro());
            return p;
        }

        static PrologueState Reload(PrologueState p) => PrologueState.FromSave(p.ToSave());

        [Test] public void IntroBeatsMoveForwardOnlyThenHandOff()
        {
            var p = PrologueState.New();
            Assert.AreEqual(PrologueStage.NotStarted, p.Stage);
            Assert.False(p.AdvanceIntro(IntroBeat.BrokeTalk), "no beats before the intro starts");
            Assert.True(p.BeginIntro(false, 3));
            Assert.False(p.BeginIntro(false, 3), "starts once");
            Assert.True(p.AdvanceIntro(IntroBeat.BloodNoticeMemory));
            Assert.False(p.AdvanceIntro(IntroBeat.BrokeTalk), "never backwards");
            Assert.True(p.FinishIntro());
            Assert.AreEqual(PrologueStage.Tutorial, p.Stage); Assert.False(p.IntroSkipped); Assert.AreEqual(IntroBeat.HandOff, p.Beat);
        }

        [Test] public void StagingUsesOnlyThePresentParticipants()
        {
            Assert.AreEqual(PrologueStaging.Solo, PrologueState.StagingFor(true, 3), "a solo world is solitary whatever happens");
            Assert.AreEqual(PrologueStaging.CoopSolitary, PrologueState.StagingFor(false, 1), "co-op world started alone: solitary staging");
            Assert.AreEqual(PrologueStaging.CoopGroup, PrologueState.StagingFor(false, 2));
            var p = PrologueState.New(); p.BeginIntro(true, 4);
            Assert.AreEqual(1, p.IntroParticipants); Assert.AreEqual(PrologueStaging.Solo, p.Staging);
            Assert.False(PrologueState.New().BeginIntro(false, 0));
        }

        [Test] public void SkipLeadsToTheSameTutorialWithoutRewardsAndOnlyOnce()
        {
            var p = PrologueState.New(); p.BeginIntro(false, 2); p.BindTarget(Target);
            Assert.True(p.SkipIntro());
            Assert.AreEqual(PrologueStage.Tutorial, p.Stage); Assert.True(p.IntroSkipped);
            Assert.False(p.SkipIntro()); Assert.False(p.FinishIntro());
            Assert.AreEqual(Target, p.TargetPersonId, "the same real target, nothing re-spawned");
        }

        [Test] public void ContinueNeverReplaysACompletedOpening()
        {
            var p = InTutorial();
            var loaded = Reload(p);
            Assert.AreEqual(PrologueStage.Tutorial, loaded.Stage);
            Assert.False(loaded.BeginIntro(false, 2), "a loaded world never restarts its intro");
        }

        [Test] public void OldWorldWithoutTheBlockNeverGetsTheOpening()
        {
            var p = PrologueState.FromSave(new PrologueSaveData()); // version 0
            Assert.AreEqual(PrologueStage.Completed, p.Stage);
            Assert.False(p.BeginIntro(false, 2));
            Assert.False(p.OnServerConfirmedDeath("anyone", false, 2).Fire);
            Assert.AreEqual(PrologueStage.Completed, PrologueState.FromSave(null).Stage);
        }

        [Test] public void TargetBindsOnceToOneRealPerson()
        {
            var p = PrologueState.New();
            Assert.False(p.BindTarget(""));
            Assert.True(p.BindTarget(Target)); Assert.AreEqual(TargetFate.Alive, p.Target);
            Assert.True(p.BindTarget(Target), "the same id again (load / duplicate) is fine");
            Assert.False(p.BindTarget("FOREST_WAGON_ADDICT_02"), "no replacement or cloned target");
            Assert.AreEqual(Target, Reload(p).TargetPersonId);
        }

        [Test] public void TutorialStepsCountInAnyOrderAndTheSaleCompletes()
        {
            var p = InTutorial();
            Assert.AreEqual(TutorialStep.MoveLook, p.NextHint());
            Assert.True(p.MarkStep(TutorialStep.PickUpSyringe)); Assert.False(p.MarkStep(TutorialStep.PickUpSyringe));
            Assert.True(p.MarkStep(TutorialStep.MoveLook));
            Assert.AreEqual(TutorialStep.ReadNotice, p.NextHint(), "a step done early is not asked again");
            p = Reload(p);
            Assert.True(p.IsDone(TutorialStep.PickUpSyringe));
            p.MarkStep(TutorialStep.SellBlood);
            Assert.AreEqual(PrologueStage.Completed, p.Stage); Assert.IsNull(p.NextHint());
        }

        [Test] public void CommittedFactsReconcileTheTutorial()
        {
            var p = InTutorial();
            p.ReconcileFromFacts(key => key == StoryFacts.TutorialSale);
            Assert.AreEqual(PrologueStage.Completed, p.Stage);
        }

        [Test] public void FirstDrawCinematicHasOneCommitAndNeverReplays()
        {
            var p = InTutorial();
            Assert.False(p.CanBeginFirstDrawCinematic("SOMEONE_ELSE"));
            Assert.True(p.BeginFirstDraw(Target, "host"));
            Assert.False(p.BeginFirstDraw(Target, "aaaaaaaa1111"), "a double interaction does not start a second one");
            Assert.True(p.MarkFirstDrawSkipped());
            Assert.True(p.CommitFirstDraw(Target, Target + "/blood/1"));
            Assert.False(p.CommitFirstDraw(Target, Target + "/blood/2"), "skip + normal completion or an animation event cannot commit twice");
            Assert.True(p.IsDone(TutorialStep.DrawBlood));
            Assert.True(p.FinishFirstDraw());
            var loaded = Reload(p);
            Assert.AreEqual(FirstDrawPhase.Done, loaded.FirstDraw); Assert.AreEqual(Target + "/blood/1", loaded.FirstDrawCommit);
            Assert.False(loaded.CanBeginFirstDrawCinematic(Target));
            Assert.False(loaded.CommitFirstDraw(Target, Target + "/blood/1"));
        }

        [Test] public void CancelledDrawGrantsNothingAndCanBeRetried()
        {
            var p = InTutorial();
            p.BeginFirstDraw(Target, "host");
            Assert.True(p.CancelFirstDraw());
            Assert.AreEqual(FirstDrawPhase.Idle, p.FirstDraw); Assert.AreEqual("", p.FirstDrawCommit);
            Assert.False(p.IsDone(TutorialStep.DrawBlood));
            Assert.True(p.BeginFirstDraw(Target, "aaaaaaaa1111"));
        }

        [Test] public void ActorDisconnectNeverLeavesALockedCutscene()
        {
            var p = InTutorial();
            p.BeginFirstDraw(Target, "aaaaaaaa1111");
            Assert.False(p.OnActorLost("bbbbbbbb2222"), "another player leaving changes nothing");
            Assert.True(p.OnActorLost("aaaaaaaa1111")); Assert.AreEqual(FirstDrawPhase.Idle, p.FirstDraw);
            p.BeginFirstDraw(Target, "host"); p.CommitFirstDraw(Target, "x/blood/1");
            Assert.True(p.OnActorLost("host")); Assert.AreEqual(FirstDrawPhase.Done, p.FirstDraw);
        }

        [Test] public void LoadMidCinematicResolvesToASafeState()
        {
            var p = InTutorial(); p.BeginFirstDraw(Target, "host");
            var a = Reload(p); a.AfterLoad(); Assert.AreEqual(FirstDrawPhase.Idle, a.FirstDraw);
            p.CommitFirstDraw(Target, "x/blood/1");
            var b = Reload(p); b.AfterLoad(); Assert.AreEqual(FirstDrawPhase.Done, b.FirstDraw);
        }

        [Test] public void DrawWithoutTheCinematicStillCommitsOnce()
        {
            var p = InTutorial();
            Assert.True(p.CommitFirstDraw(Target, "x/blood/1"));
            Assert.False(p.CanBeginFirstDrawCinematic(Target));
        }

        [Test] public void TramduroFiresOnlyAfterThatTargetsDeathAndOnlyOnce()
        {
            var p = InTutorial(false, 3);
            Assert.False(p.OnServerConfirmedDeath("FOREST_OD_JUNKIE_7", false, 3).Fire, "another person's death is not the beat");
            Assert.False(p.TramduroFired);
            Assert.True(p.CommitFirstDraw(Target, Target + "/blood/1")); // the one extraction, then (same server call) the death
            var beat = p.OnServerConfirmedDeath(Target, false, 2);
            Assert.True(beat.Fire); Assert.AreEqual(PrologueState.TramduroBeatId, beat.BeatId);
            Assert.AreEqual(PrologueStaging.CoopGroup, beat.Staging); Assert.AreEqual(2, beat.Participants, "staged for who is present now");
            Assert.AreEqual(TargetFate.Dead, p.Target);
            Assert.False(p.OnServerConfirmedDeath(Target, false, 2).Fire, "a duplicate death event does not replay it");
            var loaded = Reload(p);
            Assert.True(loaded.TramduroFired);
            Assert.False(loaded.OnServerConfirmedDeath(Target, false, 4).Fire, "load does not replay it");
            Assert.False(loaded.ReplayForLateJoin(PrologueState.TramduroBeatId), "late joiners do not get it");
        }

        [Test] public void DeathWithoutTheTutorialExtractionDoesNotTriggerIt()
        {
            var p = InTutorial(false, 2);
            Assert.False(p.OnServerConfirmedDeath(Target, false, 2).Fire, "TRAMDURO_ZETGRAM v01 §5: death alone is not the trigger");
            Assert.AreEqual(TargetFate.Dead, p.Target);
            Assert.False(p.CanBeginFirstDrawCinematic(Target), "no cinematic on a dead target");
            Assert.AreEqual(BeatPhase.None, p.Tramduro);
        }

        [Test] public void SecondWagonAddictTakesOverOnceWhenTheFirstDiedWithoutExtraction()
        {
            var p = InTutorial(false, 2);
            Assert.False(p.RebindAfterLossWithoutExtraction(Second), "not while the first target lives");
            p.OnServerConfirmedDeath(Target, false, 2);
            Assert.False(p.RebindAfterLossWithoutExtraction(Target), "never back to the dead id");
            Assert.True(p.RebindAfterLossWithoutExtraction(Second));
            Assert.AreEqual(Second, p.TargetPersonId); Assert.AreEqual(TargetFate.Alive, p.Target); Assert.True(p.TargetRebound);
            Assert.False(p.OnServerConfirmedDeath(Target, false, 2).Fire, "the old target is no longer the target");
            Assert.True(p.BeginFirstDraw(Second, "host"));
            Assert.True(p.CommitFirstDraw(Second, Second + "/blood/1"));
            Assert.True(p.OnServerConfirmedDeath(Second, false, 2).Fire, "Tramduro after the new target's draw and death");
            var loaded = Reload(p);
            Assert.AreEqual(Second, loaded.TargetPersonId); Assert.True(loaded.TargetRebound);
        }

        [Test] public void NoFallbackOnceTheExtractionHappenedOrTwice()
        {
            var p = InTutorial(false, 2);
            p.CommitFirstDraw(Target, Target + "/blood/1"); p.OnServerConfirmedDeath(Target, false, 2);
            Assert.False(p.RebindAfterLossWithoutExtraction(Second), "the normal tutorial death is not a loss");
            var q = InTutorial(false, 2);
            q.OnServerConfirmedDeath(Target, false, 2); q.RebindAfterLossWithoutExtraction(Second);
            q.OnServerConfirmedDeath(Second, false, 2);
            Assert.False(q.RebindAfterLossWithoutExtraction("FOREST_OD_JUNKIE_3"), "only one fallback");
        }

        [Test] public void BothWagonAddictsAreListed()
        {
            CollectionAssert.AreEqual(new[] { "FOREST_WAGON_ADDICT_01", "FOREST_WAGON_ADDICT_02" }, PrologueState.WagonAddictPersonIds);
        }

        [Test] public void CommitAndDeathInEitherOrderDecideItOnce()
        {
            var p = InTutorial(false, 2);
            Assert.False(p.OnServerConfirmedDeath(Target, false, 2).Fire);
            Assert.True(p.CommitFirstDraw(Target, Target + "/blood/1"));
            Assert.True(p.TryTramduro(false, 2).Fire);
            Assert.False(p.TryTramduro(false, 2).Fire);
        }

        [Test] public void PendingStartedDoneAcrossLoads()
        {
            var p = InTutorial(false, 2); p.CommitFirstDraw(Target, "x/blood/1"); p.OnServerConfirmedDeath(Target, false, 2);
            Assert.AreEqual(BeatPhase.Pending, p.Tramduro);
            var a = Reload(p); a.AfterLoad();
            var again = a.PendingTramduro(false, 1);
            Assert.True(again.Fire, "decided but never presented: offered once more after the load");
            Assert.AreEqual(PrologueStaging.CoopSolitary, again.Staging, "re-staged for who is present now");
            Assert.True(a.MarkTramduroStarted()); Assert.False(a.MarkTramduroStarted());
            var b = Reload(a); b.AfterLoad();
            Assert.AreEqual(BeatPhase.Done, b.Tramduro, "a started episode counts as given after a load");
            Assert.False(b.PendingTramduro(false, 2).Fire);
            Assert.False(b.MarkTramduroDone());
        }

        [Test] public void TramduroStagingSoloAndLoneCoopHost()
        {
            var solo = InTutorial(true, 1); solo.CommitFirstDraw(Target, "x/blood/1");
            Assert.AreEqual(PrologueStaging.Solo, solo.OnServerConfirmedDeath(Target, true, 1).Staging);
            var lone = InTutorial(false, 2); lone.CommitFirstDraw(Target, "x/blood/1");
            Assert.AreEqual(PrologueStaging.CoopSolitary, lone.OnServerConfirmedDeath(Target, false, 1).Staging,
                "the friend left before the death: solitary staging, the world stays co-op");
        }

        [Test] public void TramduroNeedsABoundTarget()
        {
            var p = PrologueState.New(); p.BeginIntro(false, 2);
            Assert.False(p.OnServerConfirmedDeath(Target, false, 2).Fire);
            Assert.False(p.OnServerConfirmedDeath("", false, 2).Fire);
        }
    }
}
