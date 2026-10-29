using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands.Tests
{
    /// <summary>PLAYER HANDS v02 (Fedya 30.10): the punch timeline and its single cue, the first-person hands rule (no idle
    /// hands) and the softer stretch clamp that keeps mid-distance grips in contact under the lower cap.</summary>
    public sealed class ArmPunchAndFramingTests
    {
        [Test]
        public void Punch_PhasesRunInOrder_AndTheSwingIsShorterThanAnyFistCooldown()
        {
            Assert.AreEqual(PunchPhaseV01.None, ArmPunchV01.Phase(-0.01f));
            Assert.AreEqual(PunchPhaseV01.Windup, ArmPunchV01.Phase(0f));
            Assert.AreEqual(PunchPhaseV01.Strike, ArmPunchV01.Phase(ArmPunchV01.Windup + 0.001f));
            Assert.AreEqual(PunchPhaseV01.Contact, ArmPunchV01.Phase(ArmPunchV01.ContactTime + 0.001f));
            Assert.AreEqual(PunchPhaseV01.Retract, ArmPunchV01.Phase(ArmPunchV01.ContactTime + ArmPunchV01.Contact + 0.001f));
            Assert.AreEqual(PunchPhaseV01.None, ArmPunchV01.Phase(ArmPunchV01.Duration));
            Assert.AreEqual(PunchPhaseV01.None, ArmPunchV01.Phase(float.NaN));
            Assert.Less(ArmPunchV01.Duration, 0.6f, "one swing is over before the next can be accepted (no overlapping swings)");
            Assert.Less(ArmPunchV01.ContactTime, 0.2f, "the fist arrives quickly after the key press (the hit is applied at the press)");
        }

        [Test]
        public void Punch_PathIsContinuous_ReachesTheStrike_AndEndsWhereItStarted()
        {
            Vector3 start = new Vector3(0.27f, -0.86f, 0.12f), cock = new Vector3(0.24f, -0.36f, 0.34f), strike = new Vector3(0.06f, -0.15f, 0.62f);
            Vector3 previous = ArmPunchV01.Blend(0f, start, cock, strike);
            Assert.Less(Vector3.Distance(previous, start), 1e-4f);
            float closest = float.MaxValue;
            const float step = 1f / 240f;
            for (float t = step; t < ArmPunchV01.Duration; t += step)
            {
                Vector3 p = ArmPunchV01.Blend(t, start, cock, strike);
                // the fastest part (the strike) covers well under 0.1 m per 1/240 s step: no teleports at phase changes
                Assert.Less(Vector3.Distance(p, previous), 0.1f, $"jump at t={t:0.000}");
                closest = Mathf.Min(closest, Vector3.Distance(p, strike));
                previous = p;
            }
            Assert.Less(closest, 0.03f, "the fist reaches the strike point");
            Vector3 end = ArmPunchV01.Blend(ArmPunchV01.Duration - 1e-4f, start, cock, strike);
            Assert.Less(Vector3.Distance(end, start), 0.01f, "and comes home");
            Vector3 atContact = ArmPunchV01.Blend(ArmPunchV01.ContactTime, start, cock, strike);
            Assert.Less(Vector3.Distance(atContact, strike), 0.05f, "the stars burst when the fist is out");
        }

        [Test]
        public void PunchLedger_OneCueOnce_RepeatsAndOldOnesDropped_WrapAccepted()
        {
            var ledger = new PunchLedgerV01();
            Assert.IsTrue(ledger.Accept(1));
            Assert.IsFalse(ledger.Accept(1), "a duplicate packet never bursts twice");
            Assert.IsTrue(ledger.Accept(2));
            Assert.IsFalse(ledger.Accept(1), "an older cue arriving late is dropped");
            Assert.IsTrue(ledger.Accept(ushort.MaxValue) == false, "far older (wrapped backwards) is dropped");
            var wrap = new PunchLedgerV01();
            Assert.IsTrue(wrap.Accept(65535));
            Assert.IsTrue(wrap.Accept(0), "the 16-bit counter wraps forward");
            wrap.Reset();
            Assert.IsTrue(wrap.Accept(0), "a rebuilt receiver starts fresh");
        }

        [Test]
        public void FirstPersonRule_NoIdleHands_OneHandItemRightOnly_TwoHandBoth()
        {
            void Check(bool rh, bool lh, bool two, int punch, bool wantR, bool wantL, string why)
            {
                FirstPersonHandsRuleV01.Engaged(rh, lh, two, punch, out bool r, out bool l);
                Assert.AreEqual(wantR, r, why + " (right)");
                Assert.AreEqual(wantL, l, why + " (left)");
            }
            Check(false, false, false, -1, false, false, "idle: no hands on screen");
            Check(true, false, false, -1, true, false, "a one-hand item: the right hand only");
            Check(false, true, false, -1, false, false, "the left hand never shows for a one-hand item");
            Check(true, true, false, -1, true, false, "two separate one-hand items: still no left hand");
            Check(true, true, true, -1, true, true, "a two-hand hold: both");
            Check(true, false, true, -1, true, false, "two-handed needs both hands active");
            Check(false, false, false, 0, true, false, "the punching arm shows for its swing");
            Check(true, false, false, 1, true, true, "item in the right hand: the left swings");
        }

        [Test]
        public void PunchSide_RightByDefault_LeftWhenTheRightHoldsAnItem()
        {
            Assert.AreEqual(0, FirstPersonHandsRuleV01.PunchSide(false, false, false));
            Assert.AreEqual(1, FirstPersonHandsRuleV01.PunchSide(true, false, false), "the syringe stays in the right hand");
            Assert.AreEqual(0, FirstPersonHandsRuleV01.PunchSide(true, true, true), "two-hand hold: the right lets go and comes back");
            Assert.AreEqual(0, FirstPersonHandsRuleV01.PunchSide(false, true, false));
        }

        [Test]
        public void SoftClamp_MidStretchPassesUnchanged_SoGripsUnderTheLowerCapStayInContact()
        {
            const float cap = 3.53f;
            float knee = 1f + (cap - 1f) * ArmStretchMath.SoftKnee;
            Assert.AreEqual(2.5f, ArmStretchMath.SoftClamp(2.5f, cap), 1e-5f, "a 2.5x hold is drawn at 2.5x");
            Assert.AreEqual(knee, ArmStretchMath.SoftClamp(knee, cap), 1e-5f);
            float justAbove = ArmStretchMath.SoftClamp(knee + 0.01f, cap);
            Assert.AreEqual(knee + 0.01f, justAbove, 2e-4f, "the bend-in starts with the same slope (no kink)");
            Assert.Less(ArmStretchMath.SoftClamp(20f, cap), cap + 1e-5f);
            Assert.Greater(ArmStretchMath.SoftClamp(20f, cap), cap - 0.01f);
        }

        [Test]
        public void Channel_Drive_IsAHold_ThenReleasesWithTheSnapBack()
        {
            var ch = new ArmChannelV01();
            ch.Snap(Vector3.zero, 1f);
            ch.Drive(new Vector3(0f, 0f, 0.6f), 1.3f, 1f);
            Assert.IsTrue(ch.Active);
            Assert.AreEqual(1.3f, ch.Stretch, 1e-5f);
            Assert.AreEqual(1f, ch.Weight, 1e-5f);
            ch.TickWrist(Vector3.zero, false, ArmSpringsV01.Default, 1f / 60f);
            Assert.IsTrue(ch.Springy, "the drive ending is a release: springy home");
        }
    }
}
