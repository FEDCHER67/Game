using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Marks a collider as an operation target for the table cursor raycast.</summary>
    public sealed class OperationTargetTag : MonoBehaviour
    {
        public TargetKind kind;
        public int index;
        public int sub;
        /// <summary>Optional renderers to tint while hovered.</summary>
        public Renderer[] highlight;
        public OpTarget Target => new OpTarget(kind, index, sub);
    }
}
