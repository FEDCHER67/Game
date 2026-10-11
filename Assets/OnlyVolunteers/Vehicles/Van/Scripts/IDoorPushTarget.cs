using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Stage 9 (NPC ragdoll, docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md): a body made of several rigidbodies that takes a
    // van door's push itself. VanDoor tunes its push (up to 300 N) and its shove (15 N·s) on the 28-40 kg stage-1 capsule;
    // put on a 1 kg forearm of the ragdoll they flung the limb away. The ragdoll's parts implement this and spread the push
    // over the whole body (Characters/Npc/NpcRagdollPart -> NpcRagdoll.DoorPush). Every other body is pushed as before.
    public interface IDoorPushTarget
    {
        /// <summary>The door pushes this body at 'worldPoint': 'amount' is a force (ForceMode.Force) or an impulse
        /// (ForceMode.Impulse). The van takes the same reaction as for any other body.</summary>
        void DoorPush(Vector3 amount, Vector3 worldPoint, ForceMode mode);

        /// <summary>The whole body this part belongs to (the ragdoll): a door shares one push and one shove per physics
        /// step among all the parts of one group it meets (GPT review 2026-10-07, finding 1).</summary>
        object DoorPushGroup { get; }
    }
}
