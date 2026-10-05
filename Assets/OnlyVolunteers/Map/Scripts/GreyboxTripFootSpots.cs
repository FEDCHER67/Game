using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Where F1-F8 (GreyboxTripMeter) put the pawn when it is on foot, one per spot, checked at build time against the
    // scene (MapGreyboxBuilder.SpotFeet: free of colliders, outside building footprints, out of the water). Added by the
    // look map's play scene only; without it, or for a zero entry, the meter keeps the grey-box's 4 m to the spot's right.
    public sealed class GreyboxTripFootSpots : MonoBehaviour
    {
        [Tooltip("Pawn feet position per trip-meter spot, same order as GreyboxTripMeter.Spots; zero = not set.")]
        public Vector3[] Positions = new Vector3[0];

        public bool TryGet(int index, out Vector3 feet)
        {
            feet = index >= 0 && index < Positions.Length ? Positions[index] : Vector3.zero;
            return feet != Vector3.zero;
        }
    }
}
