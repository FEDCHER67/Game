namespace OnlyVolunteers.Player
{
    // OV stage1: how a player's body is held, for gameplay checks now and for a SyncVar later (other players see a bent
    // back/neck when someone is stooped inside the van's cargo bay). Byte-sized on purpose: it is meant to go over the wire.
    // Stand 2.0 m, Crouch 1.0 m, Stoop 1.35 m (cargo bay, roof at 1.43 m), Seated = driving (set by the seat, not the KCC).
    public enum Stance : byte { Stand, Crouch, Stoop, Seated }
}
