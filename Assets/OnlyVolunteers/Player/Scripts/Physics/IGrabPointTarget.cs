using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    // OV stage1: a rigidbody that is held at points the target chooses (the NPC body: any point, on its axis, where the
    // ray hit) instead of exactly where the ray hit. Put it on the GameObject of the Rigidbody. PhysicsGrabber asks for a
    // point when it grabs, holds that point with the profile it gets back, checks the claim every physics tick and hands
    // it back on release. The target decides who may hold what (e.g. a holder limit) and can take a claim away at any
    // time (IsClaimValid turns false: the NPC kicked free, woke up, ...). Holders are compared by reference.
    public interface IGrabPointTarget
    {
        /// <summary>Claims a point for a world hit point. point is an opaque handle (the NPC body: a holder slot). False =
        /// refused (not grabbable now, too many holders). local is the point in the Rigidbody transform's space; profile
        /// is how to hold it.</summary>
        bool TryClaim(object holder, Vector3 hit, out int point, out Vector3 local, out GrabPhysicsProfile profile);

        /// <summary>Whether holder still holds point.</summary>
        bool IsClaimValid(object holder, int point);

        /// <summary>Hands the point back (no-op if holder no longer holds it).</summary>
        void Release(object holder, int point);
    }
}
