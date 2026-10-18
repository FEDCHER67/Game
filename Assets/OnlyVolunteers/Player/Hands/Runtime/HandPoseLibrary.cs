using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>The project's set of <see cref="HandPose"/> assets (one per id). Missing ids fall back to
    /// <see cref="HandPose.Defaults"/>, so an empty library still gives working greybox hands.</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Hands/Hand Pose Library", fileName = "HandPoseLibrary")]
    public sealed class HandPoseLibrary : ScriptableObject
    {
        public HandPose[] poses = new HandPose[0];

        public HandPose Find(HandPoseId id)
        {
            if (poses == null) return null;
            foreach (var p in poses) if (p != null && p.id == id) return p;
            return null;
        }
    }
}
