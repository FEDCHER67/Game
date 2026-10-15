using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    public sealed class OperationRulesTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        [SetUp] public void Setup(){tuning=ScriptableObject.CreateInstance<OperationTuning>();state=OperationRules.Create("stable-fixture",tuning);rules=new OperationRules(state,tuning);}
        [TearDown] public void Teardown()=>Object.DestroyImmediate(tuning);
        private void Ready(int organ){state.aligned=state.onTable=true;var o=state.organs[organ];o.cut=1;for(int c=0;c<o.connections.Length;c++)o.connections[c]=1;o.pull=tuning.pullDistance;}
        private void OnTable(){state.onTable=state.aligned=true;state.knockedOut=false;state.dazedRemaining=0;}

        // ---------- v01 contract (values updated to the v02 tuning) ----------
        [Test] public void OP02_BloodPortionDurationWeakeningFatalAndRoundTrip()
        {
            Assert.False(rules.CollectBlood(4.49f));Assert.True(rules.CollectBlood(0.01f));Assert.AreEqual(1,state.bloodPortions);Assert.True(state.alive);
            Assert.True(rules.CollectBlood(4.5f));Assert.AreEqual(PatientCue.Weakened,state.lastCue);Assert.True(state.alive);
            var loaded=JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));var resumed=new OperationRules(loaded,tuning);
            Assert.AreEqual("stable-fixture",loaded.patientId);Assert.True(resumed.CollectBlood(4.5f));Assert.False(loaded.alive);Assert.AreEqual(DeathCause.Blood,loaded.deathCause);
            Assert.False(resumed.CollectBlood(4.5f));Assert.AreEqual(3,loaded.bloodPortions);
        }
        [Test] public void OP05_TorsoAlonePreventsEscapeAndLimbRestraintsRemainIndependent()
        {OnTable();Assert.True(rules.ToggleRestraint(4));rules.Tick(12,0,false);Assert.True(state.onTable);Assert.False(state.restraints[0]);rules.ToggleRestraint(0);rules.ToggleRestraint(0);Assert.True(state.Torso);}
        [Test] public void OP06_NoKitAllowsSleepingOrHeldOperation()
        {OnTable();Assert.False(rules.CanOperate(false));Assert.True(rules.CanOperate(true));rules.Tick(0.02f,0.9f,false);Assert.True(rules.CanOperate(false));}
        [Test] public void OP10_ReleasedConnectionsSurviveSpringAndOtherHolderContinues()
        {Ready(0);bool latch=false;state.organs[0].pull=0.15f;rules.Pull(0,0.2f,1,0.1f,ref latch);float previous=state.organs[0].pull;rules.Pull(0,0,0,0.1f,ref latch);Assert.Less(state.organs[0].pull,previous);Assert.True(state.organs[0].Released);rules.Pull(0,0.3f,1,0.1f,ref latch);Assert.Greater(state.organs[0].pull,previous-0.025f);}
        [Test] public void OP12_AbruptSharedPullDamagesOncePerContinuousGesture()
        {Ready(0);state.organs[0].pull=0;bool latch=false;rules.Pull(0,0.42f,2,0.02f,ref latch);Assert.AreEqual(1,state.organs[0].damage);rules.Pull(0,0.42f,2,0.02f,ref latch);Assert.AreEqual(1,state.organs[0].damage);Assert.AreEqual(1,state.organs[0].yanks);}
        [Test] public void OP13_IntrinsicGradesIndependentAndDamageCannotRaiseQuality()
        {Assert.AreNotEqual(state.organs[0].Grade,state.organs[1].Grade);rules.DirectCut(0);Assert.AreEqual(2,state.organs[0].Grade);Assert.AreEqual(3,state.organs[1].Grade);rules.DirectCut(0);rules.DirectCut(0);Assert.AreEqual(0,state.organs[0].Grade);}
        [Test] public void OP14_TooLittleSuitableAndExcessiveDose()
        {rules.Tick(0.02f,0.4f,false);Assert.That(state.sleepRemaining,Is.EqualTo(22.5f).Within(0.01));rules.Tick(0.02f,0.5f,false);Assert.AreEqual(90,state.sleepRemaining);rules.Tick(0.02f,1.5f,false);Assert.False(state.alive);Assert.AreEqual(DeathCause.Overdose,state.deathCause);}
        [Test] public void OP15_ResidualAndSimultaneousApplicationsAddRatherThanOverwrite()
        {rules.Tick(0.02f,1.1f+1.1f,false);Assert.True(state.alive);rules.Tick(0.02f,0.1f,false);Assert.False(state.alive);}
        [Test] public void OP16_RescueRequiresSuccessfulDoseAndCancelsPendingShock()
        {OnTable();state.restraints[4]=true;state.extracted=1;state.sleepRemaining=0.01f;rules.Tick(0.02f,0,false);Assert.That(state.panicRemaining,Is.InRange(7.97f,8f));rules.Tick(2,0.1f,false);Assert.Greater(state.panicRemaining,0);rules.Tick(1,0.8f,false);Assert.AreEqual(-1,state.panicRemaining);Assert.True(state.alive);rules.Tick(8,0,false);Assert.True(state.alive);}
        [Test] public void OP16_RestrainedAwakeningDiesAfterEightSecondsWithoutRescue()
        {OnTable();state.restraints[4]=true;state.extracted=1;state.sleepRemaining=0.01f;rules.Tick(0.02f,0,false);rules.Tick(7.9f,0,false);Assert.True(state.alive);rules.Tick(0.1f,0,false);Assert.AreEqual(DeathCause.Shock,state.deathCause);}
        [Test] public void OP17_UnrestrainedAwakeningFallsAndDiesButHoldingDoesNotGrantInvulnerability()
        {OnTable();state.extracted=1;state.sleepRemaining=0.01f;rules.Tick(0.02f,0,false);rules.Tick(8,0,false);Assert.AreEqual(DeathCause.FailedEscape,state.deathCause);}
        [Test] public void OP17_UntouchedAwakePatientEscapesWithoutPostExtractionShock()
        {OnTable();rules.Tick(tuning.escapeSeconds+0.1f,0,false);Assert.False(state.onTable);Assert.True(state.alive);Assert.AreEqual(1,state.escapes);Assert.True(state.knockedOut);}
        [TestCase(0,0.1f,0.2f,0.3f)] [TestCase(1,0.2f,0.3f,0.4f)] [TestCase(2,0.3f,0.4f,0.5f)]
        public void OP18_KidneyOrderAndBloodModifiersAndOnceOnlyOutcomes(int blood,float first,float second,float liver)
        {state.bloodPortions=blood;Ready(1);Assert.True(rules.Extract(1,0.99f));Assert.That(state.organs[1].deathChance,Is.EqualTo(first).Within(0.0001));Assert.False(rules.Extract(1,0));Assert.True(state.alive);Ready(0);rules.Extract(0,0.99f);Assert.That(state.organs[0].deathChance,Is.EqualTo(second).Within(0.0001));Ready(2);rules.Extract(2,0.99f);Assert.That(state.organs[2].deathChance,Is.EqualTo(liver).Within(0.0001));var loaded=JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));Assert.False(new OperationRules(loaded,tuning).Extract(2,0));Assert.AreEqual(0.99f,loaded.organs[2].rolled);}
        [Test] public void OP18_DeathSerializesSimultaneousExtractionsWithoutRerolls()
        {Ready(0);Ready(2);Assert.True(rules.Extract(0,0));Assert.False(state.alive);Assert.True(rules.Extract(2,0));Assert.False(state.organs[2].rollCompleted);Assert.AreEqual(2,state.extracted);}
        [Test] public void OP19_EarlyOverdoseCostsAllOrgansTwoAndOrdinaryDecayStillApplies()
        {rules.Tick(0.02f,2.4f,false);foreach(var o in state.organs)Assert.AreEqual(2,o.damage);rules.Tick(85,0,false);foreach(var o in state.organs)Assert.AreEqual(3,o.damage);}
        [Test] public void OP19_LaterOverdoseDoesNotApplyEarlyPenalty()
        {Ready(0);rules.Extract(0,0.99f);rules.Tick(0.02f,2.4f,false);Assert.False(state.alive);Assert.AreEqual(0,state.organs[1].damage);}
        [Test] public void OP20_GraceBoundaryIs85AndOpeningDoesNotRestartDeathClock()
        {rules.Die(DeathCause.Blood);rules.Tick(45,0,false);Assert.AreEqual(0,state.organs[0].damage);rules.Tick(39.99f,0,false);Assert.AreEqual(0,state.organs[0].damage);rules.Tick(0.02f,0,false);Assert.AreEqual(1,state.organs[0].damage);Ready(0);rules.Extract(0,0);int grade=state.organs[0].Grade;rules.Tick(40,0,false);Assert.AreEqual(2,state.organs[1].damage);Assert.AreEqual(grade,state.organs[0].Grade);}
        [Test] public void OP11_SloppyIncisionIsLocalAndDirectCutIndependent()
        {float t=0;while(state.organs[0].cut<1&&t<10){rules.Cut(0,Mathf.Min(1,state.organs[0].cut+0.1f),0.035f,0.05f);t+=0.05f;}Assert.AreEqual(1,state.organs[0].damage);Assert.AreEqual(0,state.organs[1].damage);rules.DirectCut(0);Assert.AreEqual(3,state.organs[0].damage);}
        [Test] public void PlacementRejectsRemotePatient()
        {Assert.False(rules.BeginAlignment(2));Assert.True(rules.BeginAlignment(0.2f));rules.Tick(tuning.alignmentSeconds,0,true);Assert.True(state.aligned);Assert.False(state.knockedOut);}

        // ---------- v02 feel and readability ----------
        private float Hold(float seconds){float dt=0.02f;for(float t=0;t<seconds-1e-4f;t+=dt){rules.Tick(dt,tuning.dosePerSecond*dt,false);if(!state.alive)return t;}return seconds;}
        [Test] public void V02_DoseWindowFeelsHuman_SleepAt1p6sDistressAfter2p5sOverdoseAt4p5s()
        {
            OnTable();
            Hold(1.5f);Assert.Less(state.residual,tuning.suitableMinimum,"1.5 s is just under the suitable minimum");
            Hold(0.2f);Assert.True(state.Sleeping);Assert.GreaterOrEqual(state.residual,tuning.suitableMinimum,"~1.7 s reaches the suitable range");
            Assert.AreEqual(tuning.sleepSeconds,state.sleepRemaining,0.5f);
            Hold(0.9f);Assert.Greater(state.residual,tuning.suitableMaximum,"past ~2.6 s the patient shows distress");Assert.True(state.alive);
            Hold(1.7f);Assert.True(state.alive,"4.3 s total still survives");
            Hold(0.4f);Assert.False(state.alive,"~4.7 s total is an overdose");Assert.AreEqual(DeathCause.Overdose,state.deathCause);
        }
        [Test] public void V02_OverdosingCueFiresOnceWhenCrossingTheSuitableMaximum()
        {
            int cues=0;rules.Cue+=c=>{if(c==PatientCue.Overdosing)cues++;};
            OnTable();Hold(3f);Hold(0.5f);Assert.AreEqual(1,cues);
        }
        [Test] public void V02_CutFollowsANormalDragWithoutStalling()
        {
            OnTable();state.restraints[4]=true;
            float length=tuning.IncisionLength(0);
            Assert.True(rules.CanBeginCut(0,0.02f,0.005f));
            // 20 Hz cursor samples, 50 FixedUpdate ticks/s, a 0.25 s drag along the whole guide (0.4 m/s).
            float along=0f;float time=0f;
            for(int tick=0;tick<40&&state.organs[0].cut<1f;tick++)
            {
                time+=0.02f;if(tick%3==0)along=Mathf.Min(1.05f,time/0.25f);
                rules.CutTowards(0,along,0.004f,0.02f);
            }
            Assert.AreEqual(1f,state.organs[0].cut,"completes");Assert.Less(time,0.42f,"finishes within ~0.4 s of the drag start");
            Assert.AreEqual(0,state.organs[0].damage,"a neat cut costs nothing");
        }
        [Test] public void V02_CutMustStartNearTheDotOrTheResumePoint()
        {
            Assert.False(rules.CanBeginCut(0,0.8f,0f),"cannot start at the far end");
            Assert.False(rules.CanBeginCut(0,0.1f,0.08f),"too far from the line");
            Assert.True(rules.CanBeginCut(0,-0.1f,0.02f),"a bit before the start dot is fine");
            state.organs[0].cut=0.5f;Assert.True(rules.CanBeginCut(0,0.6f,0f),"resume near the progress");
            Assert.AreEqual(CutStep.OffLine,rules.CutTowards(0,0.7f,0.08f,0.02f));Assert.AreEqual(0.5f,state.organs[0].cut,"off the line makes no progress");
        }
        [Test] public void V02_OffLineTravelCountsAsSloppy()
        {
            rules.AddOffLine(0,1.2f);
            for(int i=1;i<=20;i++)rules.CutTowards(0,i/20f,0.005f,0.05f);
            Assert.True(state.organs[0].sloppyApplied);Assert.AreEqual(1,state.organs[0].damage);
        }
        [Test] public void V02_CordSnipTakesAboutAThirdOfASecondAndNeedsTheOpening()
        {
            Assert.False(rules.SnipCord(0,0,1f),"no snip before the incision is open");
            state.organs[0].cut=1f;
            Assert.False(rules.SnipCord(0,0,0.2f));Assert.True(rules.SnipCord(0,0,0.11f));Assert.False(state.organs[0].Released);
            Assert.True(rules.SnipCord(0,1,0.31f));Assert.True(state.organs[0].Released);Assert.AreEqual(0,state.organs[0].damage);
        }
        [Test] public void V02_BloodNeedsSleepOrRestraintAndProgressIsKept()
        {
            OnTable();float fill=0f;
            Assert.False(rules.CanDrawBlood(0),"awake and loose: he squirms");
            state.restraints[1]=true;Assert.False(rules.CanDrawBlood(0),"the other arm strap does not help");Assert.True(rules.CanDrawBlood(1));
            Assert.False(rules.FillBlood(ref fill,2f));Assert.AreEqual(2f/tuning.bloodSeconds,fill,1e-4f,"released early: progress kept");
            Assert.True(rules.FillBlood(ref fill,2.6f));Assert.AreEqual(1f,fill);Assert.AreEqual(1,state.bloodPortions);
            Assert.False(rules.FillBlood(ref fill,1f),"a full syringe takes nothing more");
            state.restraints[1]=false;state.restraints[4]=true;Assert.True(rules.CanDrawBlood(0),"the torso strap allows both arms");
            rules.Die(DeathCause.Overdose);state.restraints[4]=false;Assert.True(rules.CanDrawBlood(0),"a corpse can give blood");
        }
        [Test] public void V02_DazedThenEscapeOnlyWithoutTorso()
        {
            Assert.True(rules.BeginAlignment(0.1f));rules.Tick(tuning.alignmentSeconds,0,false);Assert.True(state.Dazed);
            rules.Tick(tuning.dazedSeconds-0.1f,0,false);Assert.AreEqual(0,state.escapeProgress,"no escape while dazed");
            rules.Tick(0.2f,0,false);rules.Tick(tuning.escapeSeconds-0.5f,0,false);Assert.True(state.onTable,"still trying");
            rules.Tick(0.6f,0,false);Assert.False(state.onTable);Assert.True(state.alive);
        }
        [Test] public void V02_ForcePlaceAlignsAtOnce()
        {rules.ForcePlace();Assert.True(state.onTable&&state.aligned);Assert.False(state.knockedOut);Assert.True(state.Dazed);}
        [Test] public void V02_TableLocalGeometryIsRotationFree()
        {
            Assert.True(OperationGeometry.OverPad(new Vector3(0.1f,tuning.padTop+0.3f,-0.4f),tuning));
            Assert.False(OperationGeometry.OverPad(new Vector3(0.6f,tuning.padTop+0.3f,0f),tuning),"beside the pad");
            Assert.False(OperationGeometry.OverPad(new Vector3(0f,0.05f,0f),tuning),"under the table");
            Assert.True(OperationGeometry.InWorkVolume(new Vector3(0.6f,0.9f,0.3f)));Assert.False(OperationGeometry.InWorkVolume(new Vector3(0f,float.NaN,0f)));
            for(int i=0;i<3;i++)
            {
                var g=OperationGeometry.GuideCoordinates(tuning,i,OperationGeometry.GuidePoint(tuning,i,0.3f));
                Assert.AreEqual(0.3f,g.x,1e-4f);Assert.AreEqual(0f,g.y,1e-4f);
                OperationGeometry.Cord(tuning,i,0,out var a,out var r);Assert.Greater((r-a).magnitude,0.02f,"cords are long enough to aim at");
            }
        }
        [Test] public void V02_TargetCodesRoundTrip()
        {
            var t=new OpTarget(TargetKind.Cord,2,1);Assert.AreEqual(t,OpTarget.FromCode(t.Code));
            Assert.True(new OpTarget(TargetKind.Body,(int)BodyPart.Neck).IsInjectionSite);Assert.False(new OpTarget(TargetKind.Body,(int)BodyPart.Torso).IsInjectionSite);
            Assert.AreEqual(1,new OpTarget(TargetKind.Body,(int)BodyPart.ShoulderR).ArmSide);Assert.AreEqual(OpTarget.None,OpTarget.FromCode(0xFF0000));
        }
        [Test] public void V02_RussianTierLabels()
        {
            Assert.AreEqual(new[]{"Убитое","Сойдёт","Хорошее","Отличное","Идеальное"},OperationText.Tiers);
            Assert.AreEqual("Идеальное",OperationText.Tier(9));Assert.AreEqual("Убитое",OperationText.Tier(-3));
        }
    }
}
