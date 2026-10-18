using System;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>One finger chain of a hand rig: its bones curl around <see cref="curlAxis"/> (bone-local).</summary>
    [Serializable]
    public sealed class FingerChain
    {
        public FingerGroup group;
        public Transform[] bones = new Transform[0];
        public Vector3 curlAxis = Vector3.right;
        [Tooltip("Degrees per joint at curl 1.")] public float maxCurl = 75f;
        public Vector3 spreadAxis = Vector3.up;
        [Tooltip("Degrees of the first joint at spread 1 (sign per finger: index -, rest +).")] public float maxSpread = 0f;
        [NonSerialized] public Quaternion[] rest;
    }

    /// <summary>Transform-based arm: upper → lower → hand, with a grip point child on the hand. Works on any rig
    /// (view-model arms and the third-person body), no Animator/humanoid needed (spec §5, §6).</summary>
    [Serializable]
    public sealed class TwoBoneArm
    {
        public Transform upper;
        public Transform lower;
        public Transform hand;
        [Tooltip("Child of the hand where held items attach (Hand_R_Grip / Hand_L_Grip). Falls back to the hand.")]
        public Transform grip;
        [Tooltip("Elbow pole, in the space of the arm's reference transform (view root or body root).")]
        public Vector3 poleLocal = new Vector3(0.6f, -0.8f, 0f);
        public FingerChain[] fingers = new FingerChain[0];

        public bool IsValid => upper != null && lower != null && hand != null;
        public Transform GripOrHand => grip != null ? grip : hand;

        public void CacheRest()
        {
            if (fingers == null) return;
            foreach (var f in fingers)
            {
                if (f == null || f.bones == null) continue;
                f.rest = new Quaternion[f.bones.Length];
                for (int i = 0; i < f.bones.Length; i++) if (f.bones[i] != null) f.rest[i] = f.bones[i].localRotation;
            }
        }

        /// <summary>Grip point relative to the hand bone.</summary>
        public Pose GripInHand
        {
            get
            {
                if (grip == null || hand == null) return new Pose(Vector3.zero, Quaternion.identity);
                Quaternion inv = Quaternion.Inverse(hand.rotation);
                return new Pose(inv * (grip.position - hand.position), inv * grip.rotation);
            }
        }

        public Pose GripWorld
        {
            get { Transform g = GripOrHand; return g != null ? new Pose(g.position, g.rotation) : default; }
        }

        /// <summary>Moves the arm so its grip point reaches <paramref name="gripTarget"/> (world).
        /// <paramref name="weight"/> 0 keeps the current (animated) pose.</summary>
        public void SolveGrip(Pose gripTarget, Transform reference, float weight)
        {
            if (!IsValid || weight <= 0f) return;
            Pose handTarget = HandsMath.HandPoseFromSocket(gripTarget, GripInHand);
            if (weight < 1f) handTarget = HandsMath.Lerp(new Pose(hand.position, hand.rotation), handTarget, weight);
            Vector3 pole = reference != null ? reference.TransformPoint(poleLocal) : upper.position + poleLocal;

            Vector3 a = upper.position, b = lower.position, c = hand.position;
            float l1 = Vector3.Distance(a, b), l2 = Vector3.Distance(b, c);
            if (l1 < 1e-4f || l2 < 1e-4f) return;
            HandsMath.SolveTwoBone(a, l1, l2, handTarget.position, pole, out Vector3 elbow, out Vector3 end);

            upper.rotation = Quaternion.FromToRotation(b - a, elbow - a) * upper.rotation;
            b = lower.position; c = hand.position;
            lower.rotation = Quaternion.FromToRotation(c - b, end - b) * lower.rotation;
            hand.rotation = handTarget.rotation;
        }

        /// <summary>Applies finger curls (x thumb, y index, z middle, w rest) and spread (-1..1) over the rest pose.</summary>
        public void ApplyFingers(Vector4 curl, float spread)
        {
            if (fingers == null) return;
            foreach (var f in fingers)
            {
                if (f == null || f.bones == null || f.rest == null) continue;
                float c = curl[(int)f.group];
                for (int i = 0; i < f.bones.Length && i < f.rest.Length; i++)
                {
                    if (f.bones[i] == null) continue;
                    Quaternion q = f.rest[i] * Quaternion.AngleAxis(c * f.maxCurl, f.curlAxis);
                    if (i == 0 && f.maxSpread != 0f) q = Quaternion.AngleAxis(spread * f.maxSpread, f.spreadAxis) * q;
                    f.bones[i].localRotation = q;
                }
            }
        }
    }
}
