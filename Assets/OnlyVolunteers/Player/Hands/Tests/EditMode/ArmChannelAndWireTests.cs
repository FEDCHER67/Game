using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands.Tests
{
    public sealed class ArmChannelTests
    {
        private static readonly ArmSpringsV01 Springs = ArmSpringsV01.Default;
        private const float Dt = 1f / 60f;

        [Test]
        public void Release_SnapsBackWithOvershoot_ThenSettlesAtRest()
        {
            var ch = new ArmChannelV01();
            ch.Snap(Vector3.zero, 1f);
            for (int i = 0; i < 120; i++) { ch.TickWrist(Vector3.forward * 2f, true, Springs, Dt); ch.TickStretch(4f, 6f, Springs, Dt); }
            Assert.AreEqual(4f, ch.Stretch, 0.05f, "held far: the arm is long");
            Assert.AreEqual(1f, ch.Weight, 1e-4f);
            float min = 9f;
            for (int i = 0; i < 240; i++)
            {
                ch.TickWrist(Vector3.zero, false, Springs, Dt);
                ch.TickStretch(1f, 6f, Springs, Dt);
                min = Mathf.Min(min, ch.Stretch);
            }
            Assert.Less(min, 0.95f, "the snap back squashes the arm a little (overshoot)");
            Assert.GreaterOrEqual(min, Springs.MinStretch - 1e-5f, "never below the squash floor");
            Assert.AreEqual(1f, ch.Stretch, 0.02f);
            Assert.Less(ch.Wrist.magnitude, 0.01f);
            Assert.AreEqual(0f, ch.Weight, 1e-4f, "third person blends back to the clip once settled");
        }

        [Test]
        public void Stretch_NeverPassesTheMax()
        {
            var ch = new ArmChannelV01();
            ch.Snap(Vector3.zero, 1f);
            float max = 0f;
            for (int i = 0; i < 200; i++) { ch.TickStretch(6f, 6f, Springs, Dt); max = Mathf.Max(max, ch.Stretch); }
            Assert.LessOrEqual(max, 6f + 1e-5f, "an underdamped spring toward the limit must not overshoot past it");
        }

        [Test]
        public void Weight_KeepsTheHoldWhileTheReleasedHandFliesBack()
        {
            var ch = new ArmChannelV01();
            ch.Snap(Vector3.zero);
            for (int i = 0; i < 30; i++) ch.TickWrist(Vector3.one, true, Springs, Dt);
            ch.TickWrist(Vector3.zero, false, Springs, Dt);
            Assert.IsTrue(ch.Springy);
            Assert.AreEqual(1f, ch.Weight, 1e-4f);
            for (int i = 0; i < 120; i++) ch.TickWrist(Vector3.zero, false, Springs, Dt);
            Assert.IsFalse(ch.Springy);
            Assert.AreEqual(0f, ch.Weight, 1e-4f);
        }
    }

    public sealed class ArmsWireTests
    {
        private static ArmsStateV01 Holding() => new ArmsStateV01
        {
            Right = true, Left = true, TwoHanded = true, Pose = ArmsPoseV01.Grab, Heft = 0.83f,
            StretchRight = 3.4f, StretchLeft = 2.9f,
            RightOffset = new Vector3(0.31f, 1.12f, 2.05f), LeftOffset = new Vector3(-0.27f, 1.08f, -1.99f),
        };

        [Test]
        public void PackUnpack_RoundTripsWithinTheQuantisation()
        {
            var s = Holding();
            ArmsWireV01.Pack(s, out ulong a, out ulong b);
            var r = ArmsWireV01.Unpack(a, b);
            Assert.IsTrue(r.Right && r.Left && r.TwoHanded);
            Assert.AreEqual(ArmsPoseV01.Grab, r.Pose);
            Assert.AreEqual(s.Heft, r.Heft, 0.5f / 255f + 1e-5f);
            Assert.AreEqual(s.StretchRight, r.StretchRight, ArmsWireV01.StretchStep * 0.5f + 1e-5f);
            Assert.AreEqual(s.StretchLeft, r.StretchLeft, ArmsWireV01.StretchStep * 0.5f + 1e-5f);
            float step = ArmsWireV01.Range / 32767f;
            Assert.Less(Vector3.Distance(s.RightOffset, r.RightOffset), step * 1.5f);
            Assert.Less(Vector3.Distance(s.LeftOffset, r.LeftOffset), step * 1.5f);
            Assert.IsTrue(r.Equals(s), "equality is by wire form");
            Assert.IsTrue(r.Approximately(s));
        }

        [Test]
        public void Idle_UnpacksClean()
        {
            ArmsWireV01.Pack(ArmsStateV01.Idle, out ulong a, out ulong b);
            var r = ArmsWireV01.Unpack(a, b);
            Assert.IsFalse(r.AnyHand);
            Assert.AreEqual(ArmsPoseV01.Idle, r.Pose);
            Assert.AreEqual(Vector3.zero, r.RightOffset);
            Assert.AreEqual(1f, r.StretchRight, 1e-5f);
            // a pose without hands is still idle; an inactive hand's offset is dropped
            var odd = new ArmsStateV01 { Pose = ArmsPoseV01.Carry, TwoHanded = true, RightOffset = Vector3.one, StretchRight = 1f, StretchLeft = 1f };
            ArmsWireV01.Pack(odd, out a, out b);
            r = ArmsWireV01.Unpack(a, b);
            Assert.AreEqual(ArmsPoseV01.Idle, r.Pose);
            Assert.IsFalse(r.TwoHanded);
            Assert.AreEqual(Vector3.zero, r.RightOffset);
        }

        [Test]
        public void OutOfRange_ClampsInsteadOfWrapping()
        {
            var s = new ArmsStateV01
            {
                Right = true, Pose = ArmsPoseV01.PalmUp, Heft = 7f,
                StretchRight = 99f, StretchLeft = -3f,
                RightOffset = new Vector3(50f, -50f, float.NaN),
            };
            ArmsWireV01.Pack(s, out ulong a, out ulong b);
            var r = ArmsWireV01.Unpack(a, b);
            Assert.AreEqual(ArmsWireV01.Range, r.RightOffset.x, 1e-3f);
            Assert.AreEqual(-ArmsWireV01.Range, r.RightOffset.y, 1e-3f);
            Assert.AreEqual(0f, r.RightOffset.z, 1e-3f);
            Assert.AreEqual(1f, r.Heft, 1e-5f);
            Assert.AreEqual(ArmsWireV01.StretchMax, r.StretchRight, 1e-5f);
            Assert.AreEqual(ArmsWireV01.StretchMin, r.StretchLeft, 1e-5f);
        }

        [Test]
        public void Garbage_UnpacksToValidData_AndSanitizeClearsReservedBits()
        {
            ulong a = ulong.MaxValue, b = 0x0123456789ABCDEFUL;
            var r = ArmsWireV01.Unpack(a, b);
            Assert.That((int)r.Pose, Is.LessThan(ArmsWireV01.PoseCount));
            Assert.That(r.Heft, Is.InRange(0f, 1f));
            Assert.That(r.StretchRight, Is.InRange(ArmsWireV01.StretchMin, ArmsWireV01.StretchMax));
            Assert.That(Mathf.Abs(r.RightOffset.x), Is.LessThanOrEqualTo(ArmsWireV01.Range + 1e-3f));
            ArmsWireV01.Sanitize(ref a, ref b);
            Assert.AreEqual(0UL, a & 0x80UL, "reserved header bit cleared");
            var again = ArmsWireV01.Unpack(a, b);
            Assert.IsTrue(again.Equals(r));
        }

        [Test]
        public void ShapeAndThrottle()
        {
            var s = Holding();
            var moved = s; moved.RightOffset += new Vector3(0.002f, 0f, 0f);
            Assert.IsTrue(s.SameShape(moved));
            Assert.IsTrue(s.Approximately(moved), "2 mm is not worth a packet");
            moved.RightOffset += new Vector3(0.05f, 0f, 0f);
            Assert.IsFalse(s.Approximately(moved));
            var released = s; released.Left = false;
            Assert.IsFalse(s.SameShape(released), "a hand letting go is a shape change (sent reliably)");
            var other = s; other.Pose = ArmsPoseV01.Carry;
            Assert.IsFalse(s.SameShape(other));
        }

        [Test]
        public void PoseValues_AreNetworkData_NeverRenumbered()
        {
            Assert.AreEqual(0, (int)ArmsPoseV01.Idle);
            Assert.AreEqual(1, (int)ArmsPoseV01.Grab);
            Assert.AreEqual(2, (int)ArmsPoseV01.Carry);
            Assert.AreEqual(3, (int)ArmsPoseV01.PalmUp);
            Assert.AreEqual(4, (int)ArmsPoseV01.Tool);
            Assert.AreEqual(5, (int)ArmsPoseV01.Push);
            Assert.AreEqual(ArmsWireV01.PoseCount, System.Enum.GetValues(typeof(ArmsPoseV01)).Length);
            Assert.Less(ArmsWireV01.PoseCount, 16, "4 bits on the wire");
        }
    }
}
