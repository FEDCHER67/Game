using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Shared E-key bookkeeping for the grey-box: getting into or out of the van swaps which scripts are live in the
    // middle of a frame, so the frame that used E is recorded and every other E handler skips it (one action per press).
    public static class GreyboxInput
    {
        public static int EUsedFrame = -1;

        public static bool EFree => EUsedFrame != Time.frameCount;

        public static void UseE() => EUsedFrame = Time.frameCount;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => EUsedFrame = -1;
    }
}
