using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Characters.Npc
{
    /// <summary>Which body a free NPC gets when it goes down (stage 9 A/B switch, dev key F10): the stage-1 capsule
    /// (Map/Scripts/GreyboxNpcBody) or the 11-body ragdoll (NpcRagdoll).</summary>
    public enum NpcBodyMode : byte { Capsule, Ragdoll }

    public enum NpcSide : byte { Left, Right }

    /// <summary>Anatomical landmarks of a downed body (design doc §2.1): kicks start at an ankle and tear holds near it;
    /// the cargo bay tests the pelvis and the collar.</summary>
    public enum NpcLandmark : byte { Pelvis, Collar, Head, LeftAnkle, RightAnkle }

    // Stage 9 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §3.6): the physical body of a downed NPC, either the stage-1
    // capsule (GreyboxNpcBody) or the ragdoll (NpcRagdoll), so GreyboxNpc, GreyboxVanCargo and the police drive both the
    // same way. It holds only what those call on a downed body. The capsule stays the body of sitting and escaping NPCs
    // (GreyboxNpcBody.SetSeated, outside this interface).
    public interface INpcBody
    {
        bool Active { get; }
        /// <summary>Whether a hand may take hold now (set by GreyboxNpc).</summary>
        bool Grabbable { get; set; }
        int HolderCount { get; }
        /// <summary>Held, and only by the feet or shins (dragged by the ankles costs Condition when fast).</summary>
        bool OnlyLegsHeld { get; }
        Vector3 CenterOfMass { get; }
        /// <summary>Touching the ground or anything else right now (a crawl hop needs something to push off).</summary>
        bool Grounded { get; }
        /// <summary>The capsule's rigidbody; the ragdoll's pelvis.</summary>
        Rigidbody MainBody { get; }
        /// <summary>World position of a landmark (physics pose).</summary>
        Vector3 Landmark(NpcLandmark landmark);
        void Activate(Vector3 velocity, Vector3 angularVelocity);
        void Deactivate();
        /// <summary>An impulse at a world point, scaled with the body's mass like the stage-1 capsule (tuned at 40 kg).</summary>
        void Push(Vector3 impulse, Vector3 worldPoint);
        /// <summary>An impulse at that side's ankle.</summary>
        void Kick(NpcSide side, Vector3 impulse);
        /// <summary>One crawl step: a horizontal impulse plus a small hop (m/s up).</summary>
        void Scoot(Vector3 push, float hop);
        void IgnoreFor(IEnumerable<Collider> others, float seconds);
        /// <summary>A vehicle that just knocked it over (Fedya's playtest 2026-10-11): contacts with those of 'others' that
        /// overlap this body now are ignored, each pair until the two are apart again; everything else collides at once.
        /// The parts born inside the bumper pass out of it, and no pair comes back while overlapping (a body let back into
        /// contact inside the van's colliders stayed stuck in its windshield, roof or door).</summary>
        void IgnoreOverlapping(IEnumerable<Collider> others);
        void RevokeAll();
        /// <summary>Tears one hold loose, preferring holds near the landmark. False if nobody holds it.</summary>
        bool Tear(NpcLandmark preferred);
        /// <summary>(impact speed along the contact normal, the other collider); kinematic bodies (players) do not count.</summary>
        event Action<float, Collider> Impact;

        // ---- Cargo (GreyboxVanCargo) ----

        /// <summary>The fastest of its bodies relative to a moving frame (frameVelocity: the frame's velocity at a world
        /// point, e.g. the van's): the cargo bay's "at rest relative to the van" test.</summary>
        float MaxRelativeSpeed(Func<Vector3, Vector3> frameVelocity);
        /// <summary>Pulls each of its bodies toward the frame's velocity at its centre of mass (F = (frame - v) m perSecond),
        /// skipping bodies already within settledSpeed (so bodies in a parked van can sleep).</summary>
        void DampToward(Func<Vector3, Vector3> frameVelocity, float perSecond, float settledSpeed);
        /// <summary>The frame it lies in jumped (a van teleport): every body moved rigidly by the same move, given 'velocity'
        /// and no spin.</summary>
        void MoveRigid(Vector3 fromPos, Quaternion fromRot, Vector3 toPos, Quaternion toRot, Vector3 velocity);
        /// <summary>Laid on its back on the ground at 'ground' (a point on it, under the middle of the body), along
        /// 'flatForward' (the head that way), at rest: the cargo bay's ejection.</summary>
        void PlaceLying(Vector3 ground, Vector3 flatForward);
    }
}
