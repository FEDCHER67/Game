namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Hand pose library entries (FP_HANDS_SPEC_2026-10-18_v01 §3). Values are network-packed in 4 bits:
    /// keep them below 16 and never renumber an existing entry.</summary>
    public enum HandPoseId : byte
    {
        Empty = 0,         // relaxed hands low in view (nothing selected)
        GripCylinder = 1,  // syringe, scalpel, tools, zip-tie bundle
        Pinch = 2,         // small items: pills, a zip tie, a clue photo
        PalmUpCarry = 3,   // organ, blood bag on an open palm
        TwoHandCarry = 4,  // cooler, body bag, crate (both hands on handles)
        PhoneHold = 5,     // phone in the left hand, right thumb taps
        PushPull = 6,      // both hands reach a world handle (gurney, door, van)
        ThrowWindup = 7,   // charged throw, blended by charge 0..1
    }

    public enum HandSide : byte { Right = 0, Left = 1 }

    /// <summary>Short action state layered over a pose. Packed in 3 bits.</summary>
    public enum HandAction : byte
    {
        None = 0,
        Use = 1,      // one-shot poke / squeeze / cut (syringe press, scalpel stroke)
        Charge = 2,   // holding the throw button; charge01 says how far
        Throw = 3,    // release frame of a throw
        Reach = 4,    // hands IK to world targets (table tool, gurney, door)
        Equip = 5,    // item coming up into view
    }

    /// <summary>Finger groups of the 4-finger "sausage buddy" hand (thumb + index + middle + one merged ring/pinky).</summary>
    public enum FingerGroup : byte { Thumb = 0, Index = 1, Middle = 2, Rest = 3 }
}
