using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 integration (B2, 22.10): a named hook for the decal pass that follows (road markings T123, road wear T124, shore foam T134).
    // The builder leaves one empty object per decal group under Map_W85_v02/DecalHooks_W86 with the picked material and the targets;
    // the decal agent fills them. No behaviour at runtime.
    public sealed class W86DecalHook : MonoBehaviour
    {
        [TextArea] public string Note;
    }
}
