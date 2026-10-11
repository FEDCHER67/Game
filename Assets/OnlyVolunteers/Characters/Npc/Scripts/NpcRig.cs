using UnityEngine;

namespace OnlyVolunteers.Characters.Npc
{
    // On a character prefab's root, next to its Animator (SausageBuddy_A/B; put there by GreyboxBuddySetup.EnsurePrefabs
    // through NpcRagdollBuilder.EnsureRig): which ragdoll profile fits this rig. NpcRagdoll, which GreyboxNpc adds at
    // runtime to every NPC root, finds it among its children, so map builders and placers need no edits.
    [DisallowMultipleComponent]
    public sealed class NpcRig : MonoBehaviour
    {
        public NpcRagdollProfile Ragdoll;
        public Animator Animator;
    }
}
