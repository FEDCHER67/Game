using NUnit.Framework;

namespace OnlyVolunteers.Player.Hands.Tests
{
    public sealed class PoseBlenderAndNetStateTests
    {
        private static float Sum(PoseBlender b)
        {
            float s = 0f;
            foreach (float w in b.Weights) s += w;
            return s;
        }

        [Test]
        public void Blender_ReachesTargetInBlendTime_AndWeightsSumToOne()
        {
            var b = new PoseBlender(HandPoseId.Empty);
            b.SetTarget(HandPoseId.GripCylinder);
            for (int i = 0; i < 9; i++) { b.Step(0.0166f, 0.15f); Assert.AreEqual(1f, Sum(b), 1e-4f); }
            Assert.IsFalse(b.Settled);
            b.Step(0.0166f, 0.15f);
            Assert.IsTrue(b.Settled);
            Assert.AreEqual(0f, b.WeightOf(HandPoseId.Empty), 1e-5f);
        }

        [Test]
        public void Blender_SwitchMidBlendIsContinuous()
        {
            var b = new PoseBlender(HandPoseId.Empty);
            b.SetTarget(HandPoseId.GripCylinder);
            b.Step(0.075f, 0.15f); // half way
            float grip = b.WeightOf(HandPoseId.GripCylinder);
            b.SetTarget(HandPoseId.PalmUpCarry);
            Assert.AreEqual(grip, b.WeightOf(HandPoseId.GripCylinder), 1e-6f); // nothing jumps on the switch
            b.Step(0.03f, 0.15f);
            Assert.AreEqual(1f, Sum(b), 1e-4f);
            Assert.AreEqual(0.2f, b.WeightOf(HandPoseId.PalmUpCarry), 1e-4f);
            Assert.Less(b.WeightOf(HandPoseId.GripCylinder), grip);
        }

        [Test]
        public void Blender_CapHoldsPartialWeight_AndPullsBack()
        {
            var b = new PoseBlender(HandPoseId.GripCylinder);
            b.SetTarget(HandPoseId.ThrowWindup);
            for (int i = 0; i < 30; i++) b.Step(0.0166f, 0.15f, 0.4f);
            Assert.AreEqual(0.4f, b.WeightOf(HandPoseId.ThrowWindup), 1e-4f);
            Assert.AreEqual(0.6f, b.WeightOf(HandPoseId.GripCylinder), 1e-4f);
            for (int i = 0; i < 30; i++) b.Step(0.0166f, 0.15f, 0.1f);
            Assert.AreEqual(0.1f, b.WeightOf(HandPoseId.ThrowWindup), 1e-4f);
            Assert.AreEqual(1f, Sum(b), 1e-4f);
        }

        [Test]
        public void Blender_ZeroBlendTimeSnaps()
        {
            var b = new PoseBlender(HandPoseId.Empty);
            b.SetTarget(HandPoseId.TwoHandCarry);
            b.Step(0.01f, 0f);
            Assert.AreEqual(1f, b.WeightOf(HandPoseId.TwoHandCarry));
            Assert.AreEqual(1f, Sum(b), 1e-6f);
        }

        [Test]
        public void NetState_RoundTripsEveryField()
        {
            var s = new HandsNetState(HandPoseId.ThrowWindup, HandAction.Charge, 3, 0.5f);
            HandsNetState r = HandsNetState.Unpack(s.Pack());
            Assert.AreEqual(HandPoseId.ThrowWindup, r.Pose);
            Assert.AreEqual(HandAction.Charge, r.Action);
            Assert.AreEqual(3, (int)r.ActionSequence);
            Assert.AreEqual(0.5f, r.Charge01, 1f / 127f);
            Assert.AreEqual(1f, HandsNetState.Unpack(new HandsNetState(HandPoseId.Empty, HandAction.None, 0, 5f).Pack()).Charge01);
            Assert.AreEqual(ushort.MaxValue, new HandsNetState((HandPoseId)15, (HandAction)7, 3, 1f).Pack());
        }

        [Test]
        public void NetState_RepeatedUseIsANewOneShot()
        {
            var a = new HandsNetState(HandPoseId.GripCylinder, HandAction.Use, 1, 0f);
            var same = a;
            var again = new HandsNetState(HandPoseId.GripCylinder, HandAction.Use, 2, 0f);
            Assert.IsFalse(a.IsNewOneShot(same));
            Assert.IsTrue(a.IsNewOneShot(again));
            Assert.IsFalse(a.IsNewOneShot(new HandsNetState(HandPoseId.GripCylinder, HandAction.None, 2, 0f)));
        }

        [Test]
        public void PoseIds_FitInFourBits()
        {
            foreach (HandPoseId id in System.Enum.GetValues(typeof(HandPoseId))) Assert.Less((int)id, PoseBlender.Count);
            foreach (HandAction a in System.Enum.GetValues(typeof(HandAction))) Assert.Less((int)a, 8);
        }
    }
}
