using UnityEngine;
using UnityEngine.Audio;

namespace OnlyVolunteers.Audio
{
    /// <summary>Points the runtime at the game's AudioMixer (Audio/Mixer/OV_Main_v01.mixer, 29.10). One asset in
    /// Audio/Resources/OvAudioRouting_v01.asset, loaded by <see cref="OvAudioMixerV01"/>; the mixer itself stays outside
    /// Resources at the path the brief names.</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Audio routing v01", fileName = "OvAudioRouting_v01")]
    public sealed class OvAudioRoutingV01 : ScriptableObject
    {
        public const string ResourceName = "OvAudioRouting_v01";
        public AudioMixer Mixer;
    }
}
