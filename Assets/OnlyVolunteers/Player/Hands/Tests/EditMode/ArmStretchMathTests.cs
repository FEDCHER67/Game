using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands.Tests
{
    public sealed class ArmStretchMathTests
    {
        private const float Reach = 0.44f; // the sausage's shoulder-to-wrist rest length

        [Test]
        public void NeededStretch_IsOneWithinEasyReach_AtAnyHeft()
        {
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(0.1f, Reach, 0f, 0.35f));
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(Reach * ArmStretchMath.DefaultComfort, Reach, 1f, 0.35f));
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(Reach * 0.5f, Reach, 1f, 0.35f));
        }

        [Test]
        public void NeededStretch_FartherIsLonger_AndContinuousAtTheEdge()
        {
            float edge = Reach * ArmStretchMath.DefaultComfort;
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(edge + 1e-4f, Reach, 0f, 0.35f), 1e-3f);
            float previous = 1f;
            for (float d = edge; d < 3f; d += 0.05f)
            {
                float s = ArmStretchMath.NeededStretch(d, Reach, 0.5f, 0.35f);
                Assert.GreaterOrEqual(s, previous - 1e-5f, $"stretch must not shrink as the target goes farther (d={d})");
                previous = s;
            }
            Assert.Greater(previous, 5f, "a 3 m reach needs a very long arm");
        }

        [Test]
        public void NeededStretch_ChainIsLongerThanTheDistance_SoTheElbowStaysBent()
        {
            float d = 1.2f;
            float s = ArmStretchMath.NeededStretch(d, Reach, 0f, 0.35f);
            Assert.Greater(s * Reach, d);
            Assert.AreEqual(d / (Reach * ArmStretchMath.DefaultComfort), s, 1e-4f);
        }

        [Test]
        public void NeededStretch_HeavierIsLonger_OnlyOnceStretched()
        {
            float far = 1.5f;
            float light = ArmStretchMath.NeededStretch(far, Reach, 0f, 0.35f);
            float heavy = ArmStretchMath.NeededStretch(far, Reach, 1f, 0.35f);
            Assert.Greater(heavy, light * 1.3f, "heft 1 adds most of SagPerHeft once well stretched");
            Assert.LessOrEqual(heavy, light * 1.35f + 1e-4f);
            // just past the edge the sag has barely faded in
            float near = Reach * 0.95f;
            Assert.AreEqual(ArmStretchMath.NeededStretch(near, Reach, 0f, 0.35f), ArmStretchMath.NeededStretch(near, Reach, 1f, 0.35f), 0.01f);
        }

        [Test]
        public void NeededStretch_GarbageIsSafe()
        {
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(float.NaN, Reach, 1f, 0.35f));
            Assert.AreEqual(1f, ArmStretchMath.NeededStretch(2f, 0f, 1f, 0.35f));
            Assert.GreaterOrEqual(ArmStretchMath.NeededStretch(2f, Reach, -5f, -1f), 1f);
        }

        [Test]
        public void SoftClamp_IdentityBelowOne_MonotonicAndNeverPastMax()
        {
            Assert.AreEqual(0.8f, ArmStretchMath.SoftClamp(0.8f, 6f));
            Assert.AreEqual(1f, ArmStretchMath.SoftClamp(1f, 6f));
            float previous = 1f;
            for (float s = 1f; s < 50f; s += 0.25f)
            {
                float c = ArmStretchMath.SoftClamp(s, 6f);
                Assert.LessOrEqual(c, 6f);
                Assert.GreaterOrEqual(c, previous - 1e-5f);
                previous = c;
            }
            Assert.Greater(ArmStretchMath.SoftClamp(50f, 6f), 5.95f, "far targets end at the limit");
            Assert.AreEqual(1.5f, ArmStretchMath.SoftClamp(1.5f, 6f), 0.05f, "a mild stretch is nearly unclamped");
            Assert.AreEqual(1f, ArmStretchMath.SoftClamp(3f, 1f), "max 1 = no stretch at all");
            Assert.AreEqual(1f, ArmStretchMath.SoftClamp(float.NaN, 6f));
        }

        [Test]
        public void Thickness_StretchedThinner_SquashedFatter_Clamped()
        {
            Assert.AreEqual(1f, ArmStretchMath.Thickness(1f), 1e-5f);
            Assert.AreEqual(Mathf.Pow(4f, -ArmStretchMath.ThinExponent), ArmStretchMath.Thickness(4f, 0.3f), 1e-4f);
            Assert.Less(ArmStretchMath.Thickness(4f, 0.3f), ArmStretchMath.Thickness(2f, 0.3f), "longer = thinner");
            Assert.AreEqual(0.6f, ArmStretchMath.Thickness(200f, 0.6f), 1e-5f);
            Assert.Greater(ArmStretchMath.Thickness(0.8f), 1f);
            Assert.LessOrEqual(ArmStretchMath.Thickness(0.1f, 0.45f, 1.3f), 1.3f);
            Assert.AreEqual(1f, ArmStretchMath.Thickness(0f));
        }

        [Test]
        public void Spring_Underdamped_OvershootsThenSettles()
        {
            float x = 3f, v = 0f, min = 3f;
            for (int i = 0; i < 240; i++)
            {
                x = ArmStretchMath.Spring(x, ref v, 1f, 6.5f, 0.26f, 1f / 60f);
                min = Mathf.Min(min, x);
            }
            Assert.Less(min, 0.9f, "the snap back overshoots below the target (squash)");
            Assert.AreEqual(1f, x, 0.01f, "and settles");
        }

        [Test]
        public void Spring_Damped_DoesNotOvershoot_AndIsStableForHitches()
        {
            float x = 3f, v = 0f;
            for (int i = 0; i < 300; i++)
            {
                x = ArmStretchMath.Spring(x, ref v, 1f, 4f, 1.2f, 1f / 60f);
                Assert.GreaterOrEqual(x, 1f - 1e-4f);
            }
            float y = 3f, w = 0f;
            for (int i = 0; i < 20; i++) y = ArmStretchMath.Spring(y, ref w, 1f, 12f, 0.3f, 0.25f); // 4 fps hitch frames
            Assert.IsFalse(float.IsNaN(y) || float.IsInfinity(y));
            Assert.AreEqual(1f, y, 0.05f);
            float z = 2f, u = 0f;
            Assert.AreEqual(2f, ArmStretchMath.Spring(z, ref u, 1f, 5f, 0.3f, 0f), "dt 0 (pause) keeps the value");
        }

        [Test]
        public void SolveTwoBone_Reachable_HitsTargetWithBoneLengths()
        {
            Vector3 root = new Vector3(0.2f, 1.17f, 0f), target = new Vector3(0.25f, 1.1f, 0.35f);
            bool ok = ArmStretchMath.SolveTwoBone(root, 0.23f, 0.21f, target, root + new Vector3(0.5f, -1f, 0f), out var elbow, out var end);
            Assert.IsTrue(ok);
            Assert.Less(Vector3.Distance(end, target), 1e-4f);
            Assert.AreEqual(0.23f, Vector3.Distance(root, elbow), 1e-4f);
            Assert.AreEqual(0.21f, Vector3.Distance(elbow, end), 1e-4f);
            Vector3 mid = (root + target) * 0.5f;
            Assert.Less(elbow.y, mid.y, "the elbow bends toward the pole (down)");
        }

        [Test]
        public void SolveTwoBone_Unreachable_ClampsOntoTheReachSphere()
        {
            Vector3 root = Vector3.zero, target = new Vector3(0f, 0f, 3f);
            bool ok = ArmStretchMath.SolveTwoBone(root, 0.5f, 0.5f, target, Vector3.down, out var elbow, out var end);
            Assert.IsFalse(ok);
            Assert.AreEqual(1f, end.z, 1e-3f);
            Assert.AreEqual(0f, end.x, 1e-4f);
            Assert.AreEqual(0.5f, Vector3.Distance(root, elbow), 1e-3f);
        }

        [Test]
        public void HandRotation_FingersAlongY_PalmAlongZ()
        {
            Vector3 fingers = new Vector3(0.1f, -0.2f, 1f).normalized, palm = Vector3.up;
            Quaternion q = ArmStretchMath.HandRotation(fingers, palm);
            Assert.Greater(Vector3.Dot(q * Vector3.up, fingers), 0.9999f);
            Assert.AreEqual(0f, Vector3.Dot(q * Vector3.forward, fingers), 1e-4f);
            Assert.Greater(Vector3.Dot(q * Vector3.forward, palm), 0.9f);
            Quaternion degenerate = ArmStretchMath.HandRotation(Vector3.up, Vector3.up);
            Assert.Greater(Vector3.Dot(degenerate * Vector3.up, Vector3.up), 0.9999f);
        }

        [Test]
        public void SwayBobAndWall_StayInTheirLimits()
        {
            Vector3 sway = ArmStretchMath.SwayAngles(new Vector2(5000f, -5000f), 0.012f, 4.5f, 0.006f);
            Assert.LessOrEqual(Mathf.Abs(sway.x), 4.5f);
            Assert.LessOrEqual(Mathf.Abs(sway.y), 4.5f);
            Assert.LessOrEqual(Mathf.Abs(sway.z), 4.5f);
            Assert.Less(sway.y, 0f, "turning right makes the arms lag left");
            var amp = new Vector2(0.011f, 0.016f);
            for (float p = 0f; p < 7f; p += 0.1f)
            {
                Vector3 bob = ArmStretchMath.BobOffset(p, 1f, amp);
                Assert.LessOrEqual(Mathf.Abs(bob.x), amp.x + 1e-6f);
                Assert.LessOrEqual(bob.y, 0f);
                Assert.GreaterOrEqual(bob.y, -amp.y - 1e-6f);
            }
            Assert.AreEqual(Vector3.zero, ArmStretchMath.BobOffset(1f, 0f, amp));
            float phase = ArmStretchMath.AdvanceBobPhase(6f, 100f, 0.36f, 1f);
            Assert.That(phase, Is.InRange(0f, 2f * Mathf.PI));
            Assert.AreEqual(0f, ArmStretchMath.WallRetract(1f, 0.55f));
            Assert.AreEqual(1f, ArmStretchMath.WallRetract(0f, 0.55f));
            Assert.That(ArmStretchMath.WallRetract(0.3f, 0.55f), Is.InRange(0.4f, 0.5f));
        }
    }
}
