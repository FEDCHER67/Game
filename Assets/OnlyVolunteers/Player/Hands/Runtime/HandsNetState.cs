using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Everything other clients need to draw someone's hands, in 16 bits (spec §7). The held item itself
    /// is NOT here: it comes from the inventory's replicated selection. Layout (LSB first): pose 4, action 3,
    /// action sequence 2 (re-triggers a repeated Use), charge 7 (0..127).</summary>
    public struct HandsNetState : System.IEquatable<HandsNetState>
    {
        public HandPoseId Pose;
        public HandAction Action;
        public byte ActionSequence; // 0..3, bumped on every one-shot action
        public float Charge01;

        public HandsNetState(HandPoseId pose, HandAction action, byte actionSequence, float charge01)
        {
            Pose = pose; Action = action; ActionSequence = actionSequence; Charge01 = charge01;
        }

        public ushort Pack()
        {
            int charge = Mathf.Clamp(Mathf.RoundToInt(Mathf.Clamp01(Charge01) * 127f), 0, 127);
            return (ushort)(((int)Pose & 0xF) | (((int)Action & 0x7) << 4) | ((ActionSequence & 0x3) << 7) | (charge << 9));
        }

        public static HandsNetState Unpack(ushort bits) => new HandsNetState(
            (HandPoseId)(bits & 0xF), (HandAction)((bits >> 4) & 0x7), (byte)((bits >> 7) & 0x3), ((bits >> 9) & 0x7F) / 127f);

        /// <summary>True when <paramref name="next"/> starts a new one-shot action compared with this state.</summary>
        public bool IsNewOneShot(HandsNetState next) =>
            (next.Action == HandAction.Use || next.Action == HandAction.Throw) &&
            (next.Action != Action || next.ActionSequence != ActionSequence);

        public bool Equals(HandsNetState other) => Pack() == other.Pack();
        public override bool Equals(object obj) => obj is HandsNetState other && Equals(other);
        public override int GetHashCode() => Pack();
    }
}
