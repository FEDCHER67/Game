using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Something bodies ride inside (the van's cargo bay): players are attached to its Rigidbody, NPC bodies count as
    // loaded when they rest inside it. "At rest" is always measured against PointVelocity, never against the world:
    // in a moving van the world speed is never zero.
    public interface ICarrier
    {
        Rigidbody Body { get; }
        // The frame the volume is defined in (the van root).
        Transform Space { get; }
        // False when tipped over (up vector less than ~73 degrees from vertical is still upright).
        bool Upright { get; }
        bool Contains(Vector3 world, float margin = 0f);
        Vector3 PointVelocity(Vector3 world);
    }
}
