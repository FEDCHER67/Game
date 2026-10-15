using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Placeholder for the props agent's OperatingTableStraps until OperatingTableAstra_v02 exists. Same API:
    /// SetOpen(index, open01), order L arm, R arm, L leg, R leg, torso. Each strap is a hinge that flips its band up
    /// and outward when open.</summary>
    public sealed class OperationStrapsPlaceholder : MonoBehaviour
    {
        [SerializeField] private Transform[] hinges = new Transform[5];
        [Tooltip("Optional second half of the torso belt (hinged on the other side), moves with index 4.")]
        [SerializeField] private Transform torsoSecond;
        [SerializeField] private float openDegrees = 100f;
        private Quaternion[] closed;
        private Quaternion secondClosed;

        private void Awake()
        {
            closed = new Quaternion[hinges.Length];
            for (int i = 0; i < hinges.Length; i++) if (hinges[i] != null) closed[i] = hinges[i].localRotation;
            if (torsoSecond != null) secondClosed = torsoSecond.localRotation;
        }
        public void SetOpen(int index, float open01)
        {
            if (closed == null) Awake();
            if (index < 0 || index >= hinges.Length || hinges[index] == null) return;
            var open = Quaternion.Euler(Mathf.Clamp01(open01) * openDegrees, 0f, 0f);
            hinges[index].localRotation = closed[index] * open;
            if (index == 4 && torsoSecond != null) torsoSecond.localRotation = secondClosed * open;
        }
    }
}
