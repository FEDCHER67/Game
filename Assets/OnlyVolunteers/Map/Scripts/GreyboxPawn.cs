using OnlyVolunteers.Player;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Whoever is on foot in the grey-box: Vadim's first-person KCC player (GreyboxKccPawn) or the Sausage Buddy walker.
    // The van seat, the NPCs, F1-F8 teleports and the sea return talk to this instead of to one concrete character.
    public abstract class GreyboxPawn : MonoBehaviour
    {
        // The transform that actually moves (the KCC prefab root stays put, its motor child walks).
        public abstract Transform Body { get; }
        public Vector3 Position => Body.position;
        // The pawn's own camera; null = it is seen through the scene's Main Camera.
        public virtual Camera ViewCamera => null;
        public virtual float Radius => 0.3f;
        public bool Controlled => isActiveAndEnabled;
        // Set by the van seat that drives with this pawn (GreyboxVanSeat.Awake).
        [System.NonSerialized] public GreyboxVanSeat Seat;
        // How the body is held (stage 1: plain data; a network SyncVar later). Seated while the van seat says it drives.
        public virtual Stance Stance => Driving ? Stance.Seated : Stance.Stand;
        protected bool Driving => Seat != null && Seat.Driving;

        public abstract void SetControlled(bool on);
        public abstract void Teleport(Vector3 position, float yawDegrees);
    }
}
