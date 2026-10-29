using System;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>What the hands do (4 bits on the wire). Never renumber: the values are network data.</summary>
    public enum ArmsPoseV01 : byte
    {
        /// <summary>Nothing held: first person shows the arms low in view, third person plays the body clip.</summary>
        Idle = 0,
        /// <summary>Fists on a held point (an NPC limb, a prop's side).</summary>
        Grab = 1,
        /// <summary>Both arms under a load (the body bag, a crate carried in the arms).</summary>
        Carry = 2,
        /// <summary>A small item held in an open palm (an organ, a blood bag).</summary>
        PalmUp = 3,
        /// <summary>A tool in the fist (syringe, zip tie, brush, paint can).</summary>
        Tool = 4,
        /// <summary>Hands on a bar, knuckles up (the gurney).</summary>
        Push = 5,
    }

    /// <summary>
    /// PLAYER HANDS v01 sync contract (NetworkPlayer.SubmitArms → server → every other client): the arm state of one player
    /// as plain data. Grip targets are world offsets from the player's own motor position (the feet), so a friend rebuilds
    /// the same world points around his copy of that player; stretch is what the owner's third-person body needed (the
    /// remote body recomputes its own from the same geometry and only falls back to this value). Visual only: nothing in
    /// gameplay reads it.
    /// </summary>
    [Serializable]
    public struct ArmsStateV01 : IEquatable<ArmsStateV01>
    {
        public bool Right;
        public bool Left;
        public bool TwoHanded;
        public ArmsPoseV01 Pose;
        /// <summary>0 light .. 1 heavy (a knocked-out NPC, the body bag): longer, sagging arms.</summary>
        public float Heft;
        public float StretchRight;
        public float StretchLeft;
        /// <summary>Right grip point minus the motor position, world metres.</summary>
        public Vector3 RightOffset;
        public Vector3 LeftOffset;

        public bool AnyHand => Right || Left;

        public static ArmsStateV01 Idle => new ArmsStateV01 { Pose = ArmsPoseV01.Idle, StretchRight = 1f, StretchLeft = 1f };

        /// <summary>Same hands, pose and two-handedness (a change of these is sent reliably).</summary>
        public bool SameShape(in ArmsStateV01 other) =>
            Right == other.Right && Left == other.Left && TwoHanded == other.TwoHanded && Pose == other.Pose;

        /// <summary>Close enough that a new packet would not show (send throttle).</summary>
        public bool Approximately(in ArmsStateV01 other, float positionTolerance = 0.01f, float stretchTolerance = 0.03f,
            float heftTolerance = 0.02f)
        {
            if (!SameShape(other)) return false;
            if (Mathf.Abs(Heft - other.Heft) > heftTolerance) return false;
            if (Right && ((RightOffset - other.RightOffset).sqrMagnitude > positionTolerance * positionTolerance ||
                          Mathf.Abs(StretchRight - other.StretchRight) > stretchTolerance)) return false;
            if (Left && ((LeftOffset - other.LeftOffset).sqrMagnitude > positionTolerance * positionTolerance ||
                         Mathf.Abs(StretchLeft - other.StretchLeft) > stretchTolerance)) return false;
            return true;
        }

        public bool Equals(ArmsStateV01 other)
        {
            ArmsWireV01.Pack(this, out ulong a1, out ulong b1);
            ArmsWireV01.Pack(other, out ulong a2, out ulong b2);
            return a1 == a2 && b1 == b2;
        }

        public override bool Equals(object obj) => obj is ArmsStateV01 other && Equals(other);

        public override int GetHashCode()
        {
            ArmsWireV01.Pack(this, out ulong a, out ulong b);
            return (a ^ (b * 31UL)).GetHashCode();
        }

        public override string ToString() =>
            $"arms[{Pose} R={(Right ? RightOffset.ToString("F2") : "-")} L={(Left ? LeftOffset.ToString("F2") : "-")} " +
            $"two={TwoHanded} heft={Heft:F2} s={StretchRight:F2}/{StretchLeft:F2}]";
    }

    /// <summary>
    /// 16-byte wire form of <see cref="ArmsStateV01"/>: two ulongs, so the RPCs need no custom serializer.
    /// A: bits 0-7 header (0 right, 1 left, 2 two-handed, 3-6 pose, 7 reserved = 0), 8-15 heft, 16-23 right stretch,
    /// 24-31 left stretch, 32-47 right x, 48-63 right y. B: 0-15 right z, 16-31 left x, 32-47 left y, 48-63 left z.
    /// Offsets: ±<see cref="Range"/> m in 16 bits (0.12 mm). Stretch: <see cref="StretchMin"/>..<see cref="StretchMax"/>
    /// in 1/32 steps. Heft: 0..1 in 1/255 steps. Unpack(Pack(x)) == x within those steps; garbage unpacks to valid data.
    /// </summary>
    public static class ArmsWireV01
    {
        public const float Range = 4f;
        public const float StretchMin = 0.5f;
        public const float StretchStep = 1f / 32f;
        public const float StretchMax = StretchMin + 255f * StretchStep; // 8.46875
        public const int PoseCount = 6;

        public static void Pack(in ArmsStateV01 s, out ulong a, out ulong b)
        {
            uint header = 0;
            if (s.Right) header |= 1u;
            if (s.Left) header |= 2u;
            if (s.TwoHanded) header |= 4u;
            header |= ((uint)Mathf.Clamp((int)s.Pose, 0, 15) & 15u) << 3;
            a = header
                | (ulong)QuantizeUnit(s.Heft) << 8
                | (ulong)QuantizeStretch(s.StretchRight) << 16
                | (ulong)QuantizeStretch(s.StretchLeft) << 24
                | (ulong)QuantizeOffset(s.RightOffset.x) << 32
                | (ulong)QuantizeOffset(s.RightOffset.y) << 48;
            b = QuantizeOffset(s.RightOffset.z)
                | (ulong)QuantizeOffset(s.LeftOffset.x) << 16
                | (ulong)QuantizeOffset(s.LeftOffset.y) << 32
                | (ulong)QuantizeOffset(s.LeftOffset.z) << 48;
        }

        public static ArmsStateV01 Unpack(ulong a, ulong b)
        {
            uint header = (uint)(a & 0xFF);
            int pose = (int)((header >> 3) & 15u);
            var s = new ArmsStateV01
            {
                Right = (header & 1u) != 0,
                Left = (header & 2u) != 0,
                TwoHanded = (header & 4u) != 0,
                Pose = pose < PoseCount ? (ArmsPoseV01)pose : ArmsPoseV01.Grab,
                Heft = ((a >> 8) & 0xFF) / 255f,
                StretchRight = StretchMin + ((a >> 16) & 0xFF) * StretchStep,
                StretchLeft = StretchMin + ((a >> 24) & 0xFF) * StretchStep,
                RightOffset = new Vector3(Offset((ushort)(a >> 32)), Offset((ushort)(a >> 48)), Offset((ushort)b)),
                LeftOffset = new Vector3(Offset((ushort)(b >> 16)), Offset((ushort)(b >> 32)), Offset((ushort)(b >> 48))),
            };
            if (!s.AnyHand) { s.Pose = ArmsPoseV01.Idle; s.TwoHanded = false; }
            if (!s.Right) { s.RightOffset = Vector3.zero; }
            if (!s.Left) { s.LeftOffset = Vector3.zero; }
            return s;
        }

        /// <summary>Server side: re-encodes whatever a client sent (reserved bits cleared, unknown pose mapped).</summary>
        public static void Sanitize(ref ulong a, ref ulong b)
        {
            var s = Unpack(a, b);
            Pack(s, out a, out b);
        }

        public static ushort QuantizeOffset(float metres)
        {
            if (float.IsNaN(metres)) metres = 0f;
            float n = Mathf.Clamp(metres, -Range, Range) / Range;
            return unchecked((ushort)(short)Mathf.RoundToInt(n * 32767f));
        }

        public static float Offset(ushort raw) => unchecked((short)raw) / 32767f * Range;

        public static byte QuantizeStretch(float stretch)
        {
            if (float.IsNaN(stretch)) stretch = 1f;
            return (byte)Mathf.Clamp(Mathf.RoundToInt((stretch - StretchMin) / StretchStep), 0, 255);
        }

        public static byte QuantizeUnit(float value)
        {
            if (float.IsNaN(value)) value = 0f;
            return (byte)Mathf.Clamp(Mathf.RoundToInt(Mathf.Clamp01(value) * 255f), 0, 255);
        }
    }
}
