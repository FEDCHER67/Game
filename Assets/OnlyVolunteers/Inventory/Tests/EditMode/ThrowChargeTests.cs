using NUnit.Framework;

namespace OnlyVolunteers.Inventory.Tests
{
    /// <summary>The charged throw (WORK_INVENTORY_SPEC decision 6): tap = gentle toss, full charge ~1.1 s, heavier = lower top
    /// speed, the server clamps whatever the client sends.</summary>
    public sealed class ThrowChargeTests
    {
        [Test] public void TapIsAGentleToss_FullChargeAfterAboutASecond()
        {
            Assert.AreEqual(0f, ThrowCharge.FromHold(0f));
            Assert.AreEqual(ThrowCharge.TossSpeed, ThrowCharge.Speed(ThrowCharge.FromHold(0.03f), 0.3f), 0.25f, "a tap is ~2 m/s");
            Assert.Less(ThrowCharge.FromHold(0.9f), 1f);
            Assert.AreEqual(1f, ThrowCharge.FromHold(1.2f));
            Assert.That(ThrowCharge.FullChargeSeconds, Is.InRange(1f, 1.2f));
        }
        [Test] public void HeavierThingsReachALowerTopSpeed()
        {
            float light = ThrowCharge.Speed(1f, 0.3f), organ = ThrowCharge.Speed(1f, 5f), body = ThrowCharge.Speed(1f, 70f);
            Assert.AreEqual(ThrowCharge.MaxSpeedLight, light, 1e-4f);
            Assert.Greater(light, organ); Assert.Greater(organ, body);
            Assert.AreEqual(ThrowCharge.MaxSpeedHeavy, body, 1e-4f);
            Assert.AreEqual(ThrowCharge.TossSpeed, ThrowCharge.Speed(0f, 70f), 1e-4f, "a tap is the same toss for any mass");
        }
        [Test] public void ServerClampsTheClientCharge()
        {
            Assert.AreEqual(1f, ThrowCharge.Clamp(7f)); Assert.AreEqual(0f, ThrowCharge.Clamp(-3f));
            Assert.AreEqual(0f, ThrowCharge.Clamp(float.NaN)); Assert.AreEqual(0f, ThrowCharge.Clamp(float.PositiveInfinity));
            Assert.AreEqual(ThrowCharge.Speed(1f, 2f), ThrowCharge.Speed(50f, 2f));
        }
        [Test] public void VelocityFollowsTheViewWithASmallArc()
        {
            ThrowCharge.Velocity(0f, 0f, 2f, 1f, 1f, out float x, out float y, out float z);
            Assert.AreEqual(0f, x, 1e-5f); Assert.AreEqual(ThrowCharge.LiftFull, y, 1e-5f); Assert.AreEqual(ThrowCharge.MaxSpeedLight, z, 1e-4f);
            ThrowCharge.Velocity(0f, 0f, 0f, 0f, 1f, out x, out y, out z);
            Assert.False(float.IsNaN(x) || float.IsNaN(y) || float.IsNaN(z), "a zero direction never makes NaN");
        }
    }
}
