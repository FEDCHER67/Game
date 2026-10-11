using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    // OV stage9: optional extras for a point target made of several bodies (the NPC ragdoll: eleven rigidbodies joined by
    // joints, Characters/Npc/NpcRagdollPart). PhysicsGrabber uses each member only when its IGrabPointTarget also
    // implements this interface; every other target (the gurney, the scalpel, the stage-1 NPC capsule) is held exactly as
    // before. point is the handle TryClaim gave.
    public interface IGrabPointBodyGroup
    {
        /// <summary>Mass the hold damps with (instead of the grabbed body's own mass: a 1 kg forearm on a 28 kg chain).</summary>
        float HoldMass(int point);

        /// <summary>Every collider the holder must ignore while holding (the whole NPC, not only the grabbed bone).</summary>
        IReadOnlyList<Collider> HeldColliders(int point);

        /// <summary>Applies the hold's force at worldPoint; the target may spread it over its bodies.</summary>
        void ApplyHoldForce(int point, Vector3 worldPoint, Vector3 force);
    }
}
