using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>How other players see someone's held item (spec §6): a visual proxy of the selected item in the
    /// body's main hand, the off hand IK'd to its Grip_Off socket, two-handed loads carried at the chest with both
    /// arms IK'd, and the charged-throw windup. Runs after the body's Animator; owns nothing networked. Feed it the
    /// replicated selection (<see cref="Hold"/>) and <see cref="HandsNetState"/> (<see cref="ApplyNetState"/>).</summary>
    [DefaultExecutionOrder(1000)]
    [DisallowMultipleComponent]
    public sealed class ThirdPersonHeldItem : MonoBehaviour
    {
        [Tooltip("Body root; elbow poles are in its space.")]
        public Transform body;
        public TwoBoneArm rightArm = new TwoBoneArm { poleLocal = new Vector3(0.5f, 0.9f, -0.4f) };
        public TwoBoneArm leftArm = new TwoBoneArm { poleLocal = new Vector3(-0.5f, 0.9f, -0.4f) };
        [Tooltip("Where a two-handed load's main socket sits (child of the chest/spine bone).")]
        public Transform twoHandAnchor;
        [Tooltip("Main-hand grip target at full throw charge (child of the chest, behind the shoulder).")]
        public Transform windupAnchor;
        public float blendHalfLife = 0.1f;

        private readonly Dictionary<ItemGrip, ItemGrip> proxies = new Dictionary<ItemGrip, ItemGrip>();
        private ItemGrip heldPrefab, heldProxy;
        private HandsNetState state;
        private float twoHandWeight, twoHandVelocity, offWeight, offVelocity, charge, chargeVelocity;
        private float useElapsed = float.MaxValue;

        public ItemGrip HeldProxy => heldProxy;

        public void Hold(ItemGrip prefab)
        {
            if (prefab == heldPrefab) return;
            if (heldProxy != null) heldProxy.gameObject.SetActive(false);
            heldPrefab = prefab;
            heldProxy = null;
            if (prefab == null) return;
            if (!proxies.TryGetValue(prefab, out heldProxy) || heldProxy == null)
            {
                heldProxy = Instantiate(prefab, transform, false);
                heldProxy.name = prefab.name + "_TP";
                foreach (var c in heldProxy.GetComponentsInChildren<Collider>(true)) c.enabled = false;
                foreach (var rb in heldProxy.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
                proxies[prefab] = heldProxy;
            }
            heldProxy.gameObject.SetActive(true);
        }

        public void ApplyNetState(HandsNetState next)
        {
            if (state.IsNewOneShot(next)) useElapsed = 0f;
            state = next;
        }

        private void LateUpdate()
        {
            float dt = Time.deltaTime;
            if (useElapsed < float.MaxValue) useElapsed += dt;
            bool two = heldPrefab != null && heldPrefab.twoHanded && twoHandAnchor != null;
            twoHandWeight = Mathf.Clamp01(HandsMath.SpringStep(twoHandWeight, ref twoHandVelocity, two ? 1f : 0f, blendHalfLife, dt));
            bool off = heldProxy != null && heldProxy.HasOffSocket;
            offWeight = Mathf.Clamp01(HandsMath.SpringStep(offWeight, ref offVelocity, off ? 1f : 0f, blendHalfLife, dt));
            float chargeTarget = state.Action == HandAction.Charge ? state.Charge01 : 0f;
            charge = Mathf.Clamp01(HandsMath.SpringStep(charge, ref chargeVelocity, chargeTarget, blendHalfLife, dt));
            if (heldProxy == null) return;

            HandSide main = heldPrefab.mainHand;
            TwoBoneArm mainArm = main == HandSide.Right ? rightArm : leftArm;
            TwoBoneArm offArm = main == HandSide.Right ? leftArm : rightArm;
            if (!mainArm.IsValid) return;

            // The main hand follows the animation, or the windup / two-hand anchor when those are active.
            Pose mainGrip = mainArm.GripWorld;
            if (windupAnchor != null && charge > 0f)
                mainGrip = HandsMath.Lerp(mainGrip, new Pose(windupAnchor.position, windupAnchor.rotation), charge);
            if (twoHandWeight > 0f)
                mainGrip = HandsMath.Lerp(mainGrip, new Pose(twoHandAnchor.position, twoHandAnchor.rotation), twoHandWeight);
            float kick = HandsMath.UseKick(useElapsed, 0.25f);
            if (kick > 0f && body != null) mainGrip.position += body.forward * (0.08f * kick);

            if (charge > 0f || twoHandWeight > 0f || kick > 0f)
                mainArm.SolveGrip(mainGrip, body, 1f);
            heldProxy.PlaceByMainGrip(mainArm.GripWorld);

            if (offWeight > 0f && offArm.IsValid && heldProxy.TryGetSocketWorld(heldPrefab.OffHand, out Pose socket))
                offArm.SolveGrip(socket, body, offWeight);
        }
    }
}
