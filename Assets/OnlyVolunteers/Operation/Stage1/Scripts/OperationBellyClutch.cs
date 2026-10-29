using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>K10 (Fedya 29.10, variant В): the doomed patient's run pose, a procedural layer applied after the Animator
    /// (LateUpdate) on the existing clips, no new clip: hunched forward, both hands pressed to the belly, a cartoon
    /// side-to-side wobble, head up to see where he runs. Used by the table rig (swinging off / hopping off with the belly
    /// open) and by the field NPC (CaptureNpc) on his run, so the pose carries over the hand-off. Mixamo bones.</summary>
    public static class OperationBellyClutch
    {
        public const float HunchDegrees = 40f, WobbleDegrees = 6f, WobbleRate = 11f;
        /// <summary>Where the hands rest, in torso lengths (hips to Spine2) from the hips: up along the spine, forward of it
        /// (the Sausage Buddy belly is ~0.8 torso lengths deep), and apart.</summary>
        public const float BellyUp = 0.35f, BellyForward = 0.8f, HandsApart = 0.12f;

        /// <summary>upperArm / foreArm / hand: [0] left, [1] right. weight 0..1 (the caller blends it in and out).</summary>
        public static void Apply(Transform hips, Transform spine, Transform spine2, Transform head, Transform[] upperArm,
            Transform[] foreArm, Transform[] hand, float weight, float time)
        {
            if (weight <= 0.001f || hips == null || spine2 == null || upperArm == null || foreArm == null || hand == null) return;
            if (upperArm[0] == null || upperArm[1] == null || foreArm[0] == null || foreArm[1] == null || hand[0] == null || hand[1] == null) return;
            Vector3 up = spine2.position - hips.position;
            float torso = up.magnitude;
            if (torso < 1e-3f) return;
            up /= torso;
            Vector3 right = Vector3.ProjectOnPlane(upperArm[1].position - upperArm[0].position, up);
            if (right.sqrMagnitude < 1e-6f) return;
            right.Normalize();
            Vector3 forward = Vector3.Cross(right, up).normalized;

            // Hunch: AngleAxis(+a, right) tips the spine toward forward; split over the two spine bones.
            float hunch = HunchDegrees * weight;
            if (spine != null) spine.rotation = Quaternion.AngleAxis(hunch * 0.4f, right) * spine.rotation;
            spine2.rotation = Quaternion.AngleAxis(hunch * 0.6f, right) * spine2.rotation;
            float wobble = Mathf.Sin(time * WobbleRate) * WobbleDegrees * weight;
            spine2.rotation = Quaternion.AngleAxis(wobble, forward) * spine2.rotation;
            if (head != null) head.rotation = Quaternion.AngleAxis(-hunch * 0.7f, right) * head.rotation;

            // Arms after the bend: elbows in at the sides, both hands on the belly (a little apart).
            up = (spine2.position - hips.position).normalized;
            forward = Vector3.Cross(right, up).normalized;
            Vector3 belly = hips.position + up * torso * BellyUp + forward * torso * BellyForward;
            for (int side = 0; side < 2; side++)
            {
                float s = side == 0 ? -1f : 1f;
                float upperLength = Vector3.Distance(upperArm[side].position, foreArm[side].position);
                Vector3 elbow = upperArm[side].position + (-up * 0.75f + forward * 0.35f + right * s * 0.3f).normalized * upperLength;
                Aim(upperArm[side], foreArm[side].position - upperArm[side].position, elbow - upperArm[side].position, weight);
                Vector3 onBelly = belly + right * s * torso * HandsApart;
                Aim(foreArm[side], hand[side].position - foreArm[side].position, onBelly - foreArm[side].position, weight);
            }
        }

        private static void Aim(Transform bone, Vector3 current, Vector3 want, float weight)
        {
            if (current.sqrMagnitude < 1e-8f || want.sqrMagnitude < 1e-8f) return;
            Quaternion turn = Quaternion.FromToRotation(current.normalized, want.normalized);
            bone.rotation = Quaternion.Slerp(Quaternion.identity, turn, weight) * bone.rotation;
        }
    }
}
