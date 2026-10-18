using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Approved ORGANS_LAYOUT_v02 marker-local Unity metres (the source JSON's X sign is already converted).</summary>
    public static class OperationAnatomyV02
    {
        public static readonly Vector3 BellyStart = new(0f, 0.1223f, -0.008f);
        public static readonly Vector3 BellyEnd = new(0f, -0.1197f, -0.013f);
        public static readonly Vector3 LiverLoopCenter = new(-0.012f, -0.004f, 0.045f);
        private static readonly Vector3[] Starts =
        { new(0.0237f, 0.004f, 0.006f), new(0.0237f, -0.012f, 0.006f), new(-0.0236f, 0.004f, 0.006f), new(-0.0236f, -0.012f, 0.006f) };
        private static readonly Vector3[] Ends =
        { new(0.0594f, 0.0192f, -0.0055f), new(0.0648f, -0.0082f, -0.0065f), new(-0.0540f, 0.0178f, -0.0149f), new(-0.0590f, -0.0097f, -0.0154f) };
        public static void Cord(int organ, int cord, out Vector3 attach, out Vector3 end)
        { int index = Mathf.Clamp(organ * 2 + cord, 0, 3); attach = Starts[index]; end = Ends[index]; }
        /// <summary>v03 (tuning.anatomyV03) data where present, else the approved v02 values.</summary>
        public static void Cord(OperationTuning tuning, int organ, int cord, out Vector3 attach, out Vector3 end)
        {
            int index = Mathf.Clamp(organ * 2 + cord, 0, 3);
            if (tuning != null && tuning.anatomyV03 && tuning.cordStarts != null && tuning.cordEnds != null && tuning.cordStarts.Length == 4 && tuning.cordEnds.Length == 4)
            { attach = tuning.cordStarts[index]; end = tuning.cordEnds[index]; return; }
            Cord(organ, cord, out attach, out end);
        }
        public static Vector3 Start(OperationTuning tuning) => tuning != null && tuning.anatomyV03 && tuning.bellyStart != tuning.bellyEnd ? tuning.bellyStart : BellyStart;
        public static Vector3 End(OperationTuning tuning) => tuning != null && tuning.anatomyV03 && tuning.bellyStart != tuning.bellyEnd ? tuning.bellyEnd : BellyEnd;
    }
}
