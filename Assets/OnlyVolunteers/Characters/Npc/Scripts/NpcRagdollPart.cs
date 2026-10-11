using System.Collections.Generic;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Characters.Npc
{
    // One simulated bone of an NPC ragdoll (added and removed with its Rigidbody by NpcRagdoll). PhysicsGrabber finds it as
    // the hit body's IGrabPointTarget, so any part can be grabbed; everything is forwarded to the owner with this part's
    // index (holds, at most three per NPC, live in the owner). IGrabPointBodyGroup lets the hold damp with the owner's
    // hold mass and ignore the whole NPC, not only this bone. Contacts are reported to the owner (impacts, thuds).
    // IDoorPushTarget (step 3): a van door pushing this bone hands the push to the owner, which spreads it over the body.
    [DisallowMultipleComponent]
    public sealed class NpcRagdollPart : MonoBehaviour, IGrabPointTarget, IGrabPointBodyGroup, IDoorPushTarget
    {
        // Serialized so a script reload in Play mode keeps them (the components themselves survive it).
        [SerializeField, HideInInspector] private NpcRagdoll _owner;
        [SerializeField, HideInInspector] private int _index;

        public NpcRagdoll Owner => _owner;
        public int Index => _index;

        internal void Bind(NpcRagdoll owner, int index)
        {
            _owner = owner;
            _index = index;
        }

        public bool TryClaim(object holder, Vector3 hit, out int point, out Vector3 local, out GrabPhysicsProfile profile)
        {
            if (_owner != null) return _owner.TryClaim(holder, _index, hit, out point, out local, out profile);
            point = -1;
            local = Vector3.zero;
            profile = null;
            return false;
        }

        public bool IsClaimValid(object holder, int point) => _owner != null && _owner.IsClaimValid(holder, point, _index);

        public void Release(object holder, int point)
        {
            if (_owner != null) _owner.Release(holder, point);
        }

        public float HoldMass(int point) => _owner != null ? _owner.HoldMassOf(_index) : 1f;

        public IReadOnlyList<Collider> HeldColliders(int point) =>
            _owner != null ? _owner.Colliders : (IReadOnlyList<Collider>)GetComponentsInChildren<Collider>();

        public void ApplyHoldForce(int point, Vector3 worldPoint, Vector3 force)
        {
            if (_owner != null) _owner.ApplyHoldForce(_index, worldPoint, force);
        }

        public void DoorPush(Vector3 amount, Vector3 worldPoint, ForceMode mode)
        {
            if (_owner != null) _owner.DoorPush(_index, amount, worldPoint, mode);
            else if (TryGetComponent(out Rigidbody rb)) rb.AddForceAtPosition(amount, worldPoint, mode);
        }

        /// <summary>Every part of one ragdoll is one group for a van door (one push per step, not one per part).</summary>
        public object DoorPushGroup => _owner != null ? _owner : this;

        private void OnCollisionEnter(Collision collision)
        {
            if (_owner != null) _owner.OnPartCollision(_index, collision);
        }
    }
}
