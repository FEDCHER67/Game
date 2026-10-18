using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Weights of every <see cref="HandPoseId"/>, moved linearly towards one target pose so a switch in the
    /// middle of a blend continues from where it is. Weights always sum to 1. Pure C#; EditMode-tested.</summary>
    public sealed class PoseBlender
    {
        public const int Count = 16; // HandPoseId is packed in 4 bits

        private readonly float[] weights = new float[Count];
        public HandPoseId Target { get; private set; }
        public float[] Weights => weights;

        public PoseBlender(HandPoseId initial = HandPoseId.Empty)
        {
            Target = initial;
            weights[(int)initial] = 1f;
        }

        public float WeightOf(HandPoseId id) => weights[(int)id];

        public void SetTarget(HandPoseId id) => Target = id;

        public void Snap(HandPoseId id)
        {
            for (int i = 0; i < Count; i++) weights[i] = 0f;
            weights[(int)id] = 1f;
            Target = id;
        }

        /// <summary>Advance by <paramref name="dt"/>; a full blend from another pose takes <paramref name="blendTime"/>.
        /// <paramref name="cap"/> &lt; 1 holds the target at a partial weight (the charged throw: cap = charge01);
        /// a lower cap than the current weight pulls it back at the same speed.</summary>
        public void Step(float dt, float blendTime, float cap = 1f)
        {
            int t = (int)Target;
            cap = Mathf.Clamp01(cap);
            if (blendTime <= 1e-4f && cap >= 1f) { Snap(Target); return; }
            float rate = blendTime <= 1e-4f ? float.MaxValue : dt / blendTime;
            float current = weights[t];
            float targetWeight = current < cap ? Mathf.Min(cap, current + rate) : Mathf.Max(cap, current - rate);
            float others = 1f - weights[t];
            float newOthers = 1f - targetWeight;
            if (others > 1e-6f)
            {
                float scale = newOthers / others;
                for (int i = 0; i < Count; i++) if (i != t) weights[i] *= scale;
            }
            else if (newOthers > 0f)
            {
                // Pulled back from a full target with nothing else left: hand the rest to Empty.
                int fallback = t == (int)HandPoseId.Empty ? (int)HandPoseId.GripCylinder : (int)HandPoseId.Empty;
                weights[fallback] = newOthers;
            }
            weights[t] = targetWeight;
        }

        public bool Settled => weights[(int)Target] >= 1f;
    }
}
