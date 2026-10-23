using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands.Tests
{
    public sealed class HandsMathTests
    {
        private const float Tol = 1e-3f;

        private static void Near(Vector3 expected, Vector3 actual, float tol = Tol) =>
            Assert.That(Vector3.Distance(expected, actual), Is.LessThan(tol), $"expected {expected} got {actual}");

        [Test]
        public void TwoBone_ReachableTarget_KeepsBoneLengthsAndHitsTarget()
        {
            var root = new Vector3(0.2f, -0.4f, 0f);
            var target = new Vector3(0.15f, -0.2f, 0.4f);
            bool ok = HandsMath.SolveTwoBone(root, 0.3f, 0.28f, target, root + new Vector3(1f, -1f, 0f), out var elbow, out var end);
            Assert.IsTrue(ok);
            Near(target, end);
            Assert.AreEqual(0.3f, Vector3.Distance(root, elbow), Tol);
            Assert.AreEqual(0.28f, Vector3.Distance(elbow, end), Tol);
        }

        [Test]
        public void TwoBone_ElbowBendsTowardsPole()
        {
            var root = Vector3.zero;
            var target = new Vector3(0f, 0f, 0.4f);
            HandsMath.SolveTwoBone(root, 0.3f, 0.3f, target, new Vector3(0f, -1f, 0.2f), out var down, out _);
            HandsMath.SolveTwoBone(root, 0.3f, 0.3f, target, new Vector3(1f, 0f, 0.2f), out var right, out _);
            Assert.Less(down.y, -0.1f);
            Assert.Greater(right.x, 0.1f);
        }

        [Test]
        public void TwoBone_UnreachableTarget_ClampsAlongTheLine()
        {
            var target = new Vector3(0f, 0f, 2f);
            bool ok = HandsMath.SolveTwoBone(Vector3.zero, 0.3f, 0.3f, target, Vector3.down, out var elbow, out var end);
            Assert.IsFalse(ok);
            Assert.AreEqual(0.6f * 0.999f, end.z, Tol);
            Assert.AreEqual(0f, end.x, Tol);
            Assert.AreEqual(0.3f, elbow.magnitude, Tol);
            Assert.LessOrEqual(elbow.y, 0f);
        }

        [Test]
        public void TwoBone_PoleOnTheAxis_StillGivesAValidElbow()
        {
            HandsMath.SolveTwoBone(Vector3.zero, 0.3f, 0.3f, new Vector3(0f, 0f, 0.4f), new Vector3(0f, 0f, 5f), out var elbow, out _);
            Assert.IsFalse(float.IsNaN(elbow.x) || float.IsNaN(elbow.y) || float.IsNaN(elbow.z));
            Assert.AreEqual(0.3f, elbow.magnitude, Tol);
        }

        [Test]
        public void Spring_HalfLifeIsExactFromRest()
        {
            float v = 0f;
            float x = HandsMath.SpringStep(1f, ref v, 0f, 0.2f, 0.2f);
            Assert.AreEqual(0.5f, x, Tol);
        }

        [Test]
        public void Spring_FromRestNeverOvershoots_AndIsFrameRateIndependent()
        {
            float v1 = 0f, x1 = 1f;
            for (int i = 0; i < 600; i++) { x1 = HandsMath.SpringStep(x1, ref v1, 0f, 0.1f, 1f / 600f); Assert.GreaterOrEqual(x1, -1e-6f); }
            float v2 = 0f, x2 = 1f;
            for (int i = 0; i < 30; i++) x2 = HandsMath.SpringStep(x2, ref v2, 0f, 0.1f, 1f / 30f);
            Assert.AreEqual(x1, x2, Tol);
        }

        [Test]
        public void Spring_ZeroDtKeepsValue_ZeroHalfLifeSnaps()
        {
            float v = 3f;
            Assert.AreEqual(1f, HandsMath.SpringStep(1f, ref v, 0f, 0.1f, 0f));
            Assert.AreEqual(5f, HandsMath.SpringStep(1f, ref v, 5f, 0f, 0.016f));
            Assert.AreEqual(0f, v);
        }

        [Test]
        public void Sway_OpposesLookAndIsClamped()
        {
            Vector3 s = HandsMath.SwayAngles(new Vector2(100f, 0f), 0.02f, 6f, 0f);
            Assert.AreEqual(-2f, s.y, Tol);
            Vector3 big = HandsMath.SwayAngles(new Vector2(10000f, -10000f), 0.02f, 6f, 0.02f);
            Assert.AreEqual(-6f, big.y, Tol);
            Assert.AreEqual(6f, big.x, Tol);
            Assert.AreEqual(-6f, big.z, Tol);
        }

        [Test]
        public void Bob_ZeroWhenStillAndBoundedByAmplitude()
        {
            var amp = new Vector2(0.012f, 0.008f);
            Near(Vector3.zero, HandsMath.BobOffset(1.3f, 0f, amp), 1e-6f);
            for (float p = 0f; p < 6.3f; p += 0.1f)
            {
                Vector3 o = HandsMath.BobOffset(p, 1f, amp);
                Assert.LessOrEqual(Mathf.Abs(o.x), amp.x + 1e-6f);
                Assert.LessOrEqual(o.y, 1e-6f);
                Assert.GreaterOrEqual(o.y, -amp.y - 1e-6f);
            }
            float phase = HandsMath.AdvanceBobPhase(0f, 2f, 0.5f, 0.25f); // 0.5 m walked at 0.5 cycles/m → quarter cycle
            Assert.AreEqual(Mathf.PI * 0.5f, phase, Tol);
            Assert.AreEqual(0f, HandsMath.AdvanceBobPhase(0f, 0f, 0.5f, 1f));
        }

        [Test]
        public void Fov_SameFovIsIdentity_AndScreenPositionIsKept()
        {
            Assert.AreEqual(1f, HandsMath.FovCompensation(70f, 70f), 1e-5f);
            var world = new Vector3(0.3f, -0.2f, 1f);
            Vector3 vm = HandsMath.WorldToViewModelSpace(world, 75f, 55f);
            float tw = Mathf.Tan(37.5f * Mathf.Deg2Rad), tv = Mathf.Tan(27.5f * Mathf.Deg2Rad);
            Assert.AreEqual(world.x / world.z / tw, vm.x / vm.z / tv, 1e-4f); // same normalised screen x
            Assert.AreEqual(world.y / world.z / tw, vm.y / vm.z / tv, 1e-4f);
            Assert.AreEqual(world.z, vm.z);
        }

        [Test]
        public void WallRetract_Range()
        {
            Assert.AreEqual(0f, HandsMath.WallRetract(1f, 0.5f));
            Assert.AreEqual(1f, HandsMath.WallRetract(0f, 0.5f));
            Assert.AreEqual(0.5f, HandsMath.WallRetract(0.25f, 0.5f), Tol);
            Assert.AreEqual(0f, HandsMath.WallRetract(0.1f, 0f));
        }

        [Test]
        public void UseKick_StartsAndEndsAtZero_PeaksAtAttack()
        {
            Assert.AreEqual(0f, HandsMath.UseKick(0f, 0.25f));
            Assert.AreEqual(0f, HandsMath.UseKick(0.25f, 0.25f));
            Assert.AreEqual(1f, HandsMath.UseKick(0.075f, 0.25f, 0.3f), Tol);
            Assert.AreEqual(0f, HandsMath.UseKick(float.MaxValue, 0.25f));
        }

        [Test]
        public void Pose_InverseAndMultiplyRoundTrip()
        {
            var a = new Pose(new Vector3(1f, 2f, 3f), Quaternion.Euler(10f, 40f, -20f));
            var b = new Pose(new Vector3(-0.3f, 0.1f, 0.5f), Quaternion.Euler(-30f, 5f, 60f));
            Pose id = HandsMath.Multiply(a, HandsMath.Inverse(a));
            Near(Vector3.zero, id.position);
            Assert.AreEqual(1f, Mathf.Abs(Quaternion.Dot(Quaternion.identity, id.rotation)), Tol);
            Pose back = HandsMath.Multiply(HandsMath.Inverse(a), HandsMath.Multiply(a, b));
            Near(b.position, back.position);
            Assert.AreEqual(1f, Mathf.Abs(Quaternion.Dot(b.rotation, back.rotation)), Tol);
        }

        [Test]
        public void ItemPoseFromGrip_PutsTheSocketOnTheHand()
        {
            var hand = new Pose(new Vector3(0.2f, 1.4f, 0.5f), Quaternion.Euler(0f, 30f, 15f));
            var socketInItem = new Pose(new Vector3(0f, 0.05f, -0.02f), Quaternion.Euler(90f, 0f, 0f));
            Pose item = HandsMath.ItemPoseFromGrip(hand, socketInItem);
            Pose socketWorld = HandsMath.Multiply(item, socketInItem);
            Near(hand.position, socketWorld.position);
            Assert.AreEqual(1f, Mathf.Abs(Quaternion.Dot(hand.rotation, socketWorld.rotation)), Tol);
        }

        [Test]
        public void HandPoseFromSocket_PutsTheGripOnTheSocket()
        {
            var socket = new Pose(new Vector3(1f, 1f, 1f), Quaternion.Euler(0f, -45f, 0f));
            var gripInHand = new Pose(new Vector3(0f, 0f, 0.05f), Quaternion.Euler(0f, 0f, 10f));
            Pose hand = HandsMath.HandPoseFromSocket(socket, gripInHand);
            Pose grip = HandsMath.Multiply(hand, gripInHand);
            Near(socket.position, grip.position);
            Assert.AreEqual(1f, Mathf.Abs(Quaternion.Dot(socket.rotation, grip.rotation)), Tol);
        }

        [Test]
        public void BlendRotations_SingleWeightIsThatRotation_HalfIsBetween()
        {
            var r = new[] { Quaternion.identity, Quaternion.Euler(0f, 90f, 0f) };
            Assert.AreEqual(1f, Mathf.Abs(Quaternion.Dot(r[1], HandsMath.BlendRotations(r, new[] { 0f, 1f }, 2))), Tol);
            Quaternion half = HandsMath.BlendRotations(r, new[] { 0.5f, 0.5f }, 2);
            Assert.AreEqual(45f, Quaternion.Angle(Quaternion.identity, half), 0.1f);
            // Opposite hemisphere quaternion of the same rotation must not cancel out.
            var q = Quaternion.Euler(0f, 90f, 0f);
            var neg = new Quaternion(-q.x, -q.y, -q.z, -q.w);
            Quaternion same = HandsMath.BlendRotations(new[] { q, neg }, new[] { 0.5f, 0.5f }, 2);
            Assert.AreEqual(0f, Quaternion.Angle(q, same), 0.1f);
        }
    }
}
