using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    public sealed class OperationAbdomenRulesTests
    {
        private OperationTuning tuning;
        private OperationState state;
        private OperationRules rules;
        [SetUp] public void Setup()
        {
            tuning = ScriptableObject.CreateInstance<OperationTuning>(); tuning.sharedAbdomen = true;
            state = OperationRules.Create("v04-zone", tuning); rules = new OperationRules(state, tuning);
            state.onTable = state.aligned = true; state.restraints[4] = true;
        }
        [TearDown] public void Teardown() => Object.DestroyImmediate(tuning);
        private void Open(float offset = 0f)
        { for (int i = 1; i <= 40; i++) rules.CutSharedGuide(3, i / 40f, offset, 0.04f); }

        /// <summary>Real loop samples: a point on (or radially off) the ellipse, measured the way the server measures it.</summary>
        private Vector2 LoopSample(float angle01, float radialOffset = 0f)
        {
            var p = OperationAbdomenGeometry.Point(tuning, 2, angle01);
            float r = Mathf.Min(tuning.liverLoopRadius.x, tuning.liverLoopRadius.y);
            p *= 1f + radialOffset / r;
            return OperationAbdomenGeometry.Coordinates(tuning, 2, p);
        }
        /// <summary>Goes round the liver from the seam in 'steps' samples (20 ms apart), +1 / -1 the two ways round.</summary>
        private void Loop(int direction = 1, float radialOffset = 0f, int steps = 60, float from = 0f, float to = 1f)
        {
            for (int i = 0; i <= steps; i++)
            {
                var g = LoopSample(direction * Mathf.Lerp(from, to, i / (float)steps), radialOffset);
                rules.CutSharedGuide(2, g.x, g.y, 0.02f);
            }
        }

        [Test] public void OneCutOpensAllThreeOrgansWithoutReleasingConnections()
        {
            int openings = 0; rules.Cue += cue => { if (cue == PatientCue.IncisionOpened) openings++; };
            Open(); Assert.True(state.zoneOpened); Assert.AreEqual(1, openings);
            foreach (var organ in state.organs) { Assert.True(organ.Opened); Assert.False(organ.Released); Assert.AreEqual(0, organ.damage); }
            Assert.False(rules.CanBeginSharedGuide(3, 0f, 0f));
            rules.CutSharedGuide(3, 1f, 0f, 1f); Assert.AreEqual(1, openings);
        }
        [Test] public void SharedSloppyOpeningCostsEachNearbyOrganExactlyOneGrade()
        {
            Open(0.035f); foreach (var organ in state.organs) Assert.AreEqual(1, organ.damage);
            rules.CutSharedGuide(3, 1f, 0.035f, 2f); foreach (var organ in state.organs) Assert.AreEqual(1, organ.damage);
            rules.DirectCut(1); Assert.AreEqual(3, state.organs[1].damage); Assert.AreEqual(1, state.organs[0].damage);
        }
        [Test] public void SharedGuideRejectsFarStartAndKeepsResumeProgress()
        {
            Assert.False(rules.CanBeginSharedGuide(3, 0.8f, 0f)); Assert.False(rules.CanBeginSharedGuide(3, 0f, 0.1f));
            Assert.True(rules.CanBeginSharedGuide(3, 0.02f, 0f));
            rules.CutSharedGuide(3, 0.5f, 0f, 1f);
            var loaded = JsonUtility.FromJson<OperationState>(JsonUtility.ToJson(state));
            var resumed = new OperationRules(loaded, tuning);
            Assert.AreEqual(0.5f, loaded.zoneCut); Assert.True(resumed.CanBeginSharedGuide(3, 0.52f, 0f));
            Assert.False(resumed.CanBeginSharedGuide(3, 0.95f, 0f));
            Assert.AreEqual(CutStep.Completed, resumed.CutSharedGuide(3, 1f, 0f, 1f)); Assert.True(loaded.zoneOpened);
        }
        [Test] public void SharedCutUsesTheExistingBladeSpeedAndOffLineRules()
        {
            rules.CutSharedGuide(3, 1f, 0f, 0.02f);
            Assert.AreEqual(0.02f * tuning.cutSpeed / tuning.abdomenCutLength, state.zoneCut, 0.00001f);
            float cut = state.zoneCut;
            Assert.AreEqual(CutStep.OffLine, rules.CutSharedGuide(3, 1f, 0.1f, 0.02f, 1.2f));
            Assert.AreEqual(cut, state.zoneCut); Open(); Assert.True(state.zoneSloppyApplied);
        }
        [Test] public void CordsAndPullCannotBypassTheSharedOpening()
        {
            bool latch = false;
            Assert.False(rules.SnipCord(0, 0, 1f)); Assert.False(rules.CanBeginSharedGuide(2, 0f, 0f));
            state.organs[0].cut = 1f; // even a stale per-organ save field must not grant access
            foreach (int i in new[] { 0, 1 }) state.organs[0].connections[i] = 1f;
            Assert.False(rules.Pull(0, 0.3f, 1, 1f, ref latch)); Assert.False(rules.Extract(0, 0.99f));
        }
        [Test] public void KidneyCordsAreBelowTheKidneyAndUseTheSameSnipTime()
        {
            tuning.organLift = 0.028f; Open();
            for (int i = 0; i < 2; i++) for (int c = 0; c < 2; c++)
            {
                OperationGeometry.Cord(tuning, i, c, out var attach, out var rim);
                Assert.Less(attach.z, tuning.organLift); Assert.Less(rim.z, tuning.organLift);
                Assert.Less(rim.y, -tuning.organHalfSize[i].y); Assert.Greater(attach.z, 0.009f);
                Assert.False(rules.SnipCord(i, c, 0.2f)); Assert.True(rules.SnipCord(i, c, 0.11f));
            }
        }
        [Test] public void LiverRequiresAGuidedLoopAndCannotUseTimedSnips()
        {
            Open(); Assert.False(rules.SnipCord(2, 0, 10f));
            Assert.True(rules.CanBeginSharedGuide(2, 0f, 0f));
            Loop(1, 0f, 60, 0f, 0.36f);
            Assert.AreEqual(1f, state.organs[2].connections[0]); Assert.False(state.organs[2].Released);
            Loop(1, 0f, 60, 0.36f, 0.7f); Assert.AreEqual(1f, state.organs[2].connections[1]);
            Loop(1, 0f, 60, 0.7f, 1.02f); Assert.True(state.organs[2].Released);
            Assert.False(state.organs[0].Released); Assert.AreEqual(0, state.organs[2].damage);
        }
        [Test] public void LiverSloppyLoopAndDirectCutRemainIndependentFromTheZone()
        {
            // 2.5 cm outside the loop: still on the forgiving band, but not neat.
            Open(); Loop(1, 0.025f, 80, 0f, 1.02f);
            Assert.True(state.organs[2].Released);
            Assert.AreEqual(1, state.organs[2].damage); rules.DirectCut(2); Assert.AreEqual(3, state.organs[2].damage);
            Assert.AreEqual(0, state.organs[0].damage);
        }
        [Test] public void LiverLoopCoordinatesCloseTheSeamInBothDirections()
        {
            foreach (float along in new[] { 0f, 0.2f, 0.5f, 0.8f, 0.99f })
            {
                var g = OperationAbdomenGeometry.Coordinates(tuning, 2, OperationAbdomenGeometry.Point(tuning, 2, along));
                Assert.AreEqual(along, g.x, 0.0001f); Assert.AreEqual(0f, g.y, 0.0001f);
            }
            var start = OperationAbdomenGeometry.Coordinates(tuning, 2, new Vector3(-0.0001f, tuning.liverLoopRadius.y, 0f));
            Assert.True(rules.CanBeginSharedGuide(3, 0f, 0f)); Open();
            Assert.True(rules.CanBeginSharedGuide(2, start.x, start.y), "a pixel left of the loop seam is still the start dot");
            Loop(1, 0f, 70, 0f, 0.97f); Assert.False(state.organs[2].Released, "not closed yet");
            Loop(1, 0f, 4, 0.97f, 1.03f); Assert.True(state.organs[2].Released, "crossing the seam closes the loop");
            Assert.AreEqual(1f, state.organs[2].connectionCut);
        }
        [Test] public void LiverLoopCanBeCutTheOtherWayRound()
        {
            Open(); Loop(-1, 0.008f, 70, 0f, 1.03f);
            Assert.AreEqual(-1, state.organs[2].connectionDirection);
            Assert.True(state.organs[2].Released); Assert.AreEqual(0, state.organs[2].damage);
        }
        [Test] public void AWiggleAtTheStartDotDoesNotLockTheWrongDirection()
        {
            Open();
            Loop(-1, 0f, 6, 0f, 0.05f); Loop(-1, 0f, 6, 0.05f, 0f);   // a little to the left and back
            Loop(1, 0f, 80, 0f, 1.03f);                                // then all the way round to the right
            Assert.AreEqual(1, state.organs[2].connectionDirection); Assert.True(state.organs[2].Released);
        }
        [Test] public void CuttingAcrossTheLiverIsNotGoingRoundIt()
        {
            Open(); Loop(1, 0f, 30, 0f, 0.3f);
            float progress = state.organs[2].connectionCut;
            var centre = OperationAbdomenGeometry.Coordinates(tuning, 2, new Vector3(0.002f, -0.003f, 0f));
            Assert.AreEqual(CutStep.OffLine, rules.CutSharedGuide(2, centre.x, centre.y, 0.02f, 0.3f));
            var far = LoopSample(0.75f);
            Assert.AreEqual(CutStep.None, rules.CutSharedGuide(2, far.x, far.y, 1f), "a leap to the far side is ignored");
            Assert.AreEqual(progress, state.organs[2].connectionCut);
            Assert.False(rules.CanBeginSharedGuide(2, far.x, far.y), "a new stroke cannot start on the far side");
            var here = LoopSample(progress + 0.03f);
            Assert.True(rules.CanBeginSharedGuide(2, here.x, here.y), "but it can resume where the last one stopped");
        }
        [Test] public void InvalidSharedGuideSamplesDoNotMutateState()
        {
            foreach (float invalid in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity })
            {
                Assert.AreEqual(CutStep.None, rules.CutSharedGuide(3, invalid, 0f, 1f));
                Assert.AreEqual(CutStep.None, rules.CutSharedGuide(3, 1f, invalid, 1f));
                Assert.AreEqual(CutStep.None, rules.CutSharedGuide(3, 1f, 0f, invalid));
            }
            Assert.AreEqual(CutStep.None, rules.CutSharedGuide(9, 1f, 0f, 1f)); Assert.AreEqual(0f, state.zoneCut);
        }
        [Test] public void MigratingAnOldOpenedSitePreservesGradesConnectionsAndRolls()
        {
            state.organs[1].cut = 1f; state.organs[0].damage = 2; state.organs[1].connections[0] = 1f;
            state.organs[1].rollCompleted = true; state.organs[1].rolled = 0.85f;
            rules.MigrateSharedOpening(); Assert.True(state.zoneOpened);
            foreach (var organ in state.organs) Assert.True(organ.Opened);
            Assert.AreEqual(2, state.organs[0].damage); Assert.AreEqual(1f, state.organs[1].connections[0]);
            Assert.True(state.organs[1].rollCompleted); Assert.AreEqual(0.85f, state.organs[1].rolled);
        }
        [Test] public void SharedOpeningDoesNotStartDecayOrAlterExtractionDeathChances()
        {
            Open(); Assert.AreEqual(0f, state.deathAge); Assert.True(state.alive);
            for (int i = 0; i < 3; i++)
            {
                foreach (int c in System.Linq.Enumerable.Range(0, state.organs[i].connections.Length)) state.organs[i].connections[c] = 1f;
                state.organs[i].pull = tuning.pullDistance; Assert.True(rules.Extract(i, 0.99f));
                Assert.AreEqual(new[] { 0.1f, 0.2f, 0.3f }[i], state.organs[i].deathChance, 0.0001f);
            }
        }
        [Test] public void LiverLoopReleaseThenHandsExtractExactlyOnce()
        {
            Open(); Loop(1, 0f, 70, 0f, 1.03f);
            bool latch = false; var liver = state.organs[2];
            for (int i = 0; i < 40 && !liver.removed; i++)
                if (rules.Pull(2, tuning.pullDistance * 1.2f, 1, 0.05f, ref latch)) rules.Extract(2, 0.99f);
            Assert.True(liver.removed); Assert.AreEqual(1, state.extracted);
            Assert.False(rules.Extract(2, 0.99f)); Assert.AreEqual(1, state.extracted);
            Assert.AreEqual(CutStep.None, rules.CutSharedGuide(2, 0.1f, 0f, 1f), "a removed liver has no loop any more");
        }
    }
}
