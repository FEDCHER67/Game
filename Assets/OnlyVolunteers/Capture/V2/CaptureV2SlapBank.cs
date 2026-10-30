using UnityEngine;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>The slap's hit sounds as serialized references, so they reach the build. Vadim 31.10: only his sound,
    /// in three strength tiers baked from it (Audio/Slap/Slap_Vadim_Light/Medium/Heavy_01..03; the original
    /// Slap_Vadim_01 is the fallback; the other Slap_*.wav and Candidates/ stay unused). The loud peak comes ~0.125 s
    /// after the file start (Light, pitched up: ~0.114 s), so a hit starts that long before the contact (CaptureV2Hands).
    /// Resources/CaptureV2SlapBank, filled by CaptureV2SlapBankBuilder (editor; also before every player build).</summary>
    public sealed class CaptureV2SlapBank : ScriptableObject
    {
        public const string ResourceName = "CaptureV2SlapBank";
        public AudioClip[] Light = new AudioClip[0], Medium = new AudioClip[0], Heavy = new AudioClip[0];
        public AudioClip Hit;
        public float LightPeak = 0.114f, HitPeak = 0.125f;
        public float LightUpTo = 0.35f, MediumUpTo = 0.85f; // charge bands: light .. 0.35 .. medium .. 0.85 .. heavy
    }
}
