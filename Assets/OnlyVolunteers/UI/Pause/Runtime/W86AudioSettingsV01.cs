using OnlyVolunteers.Audio;
using UnityEngine;

namespace OnlyVolunteers.UI.Pause
{
    /// <summary>
    /// Sound settings (PLAYER stage 29.10; mixer buses since the same day). The volumes live in OvAudioMixerV01: the
    /// AudioMixer OV_Main_v01 (Master / Effects / Ambience / VoiceUI with exposed volumes), local to this machine
    /// (PlayerPrefs), never in the game save. This class keeps the master-only entry points the pause menu and the
    /// phase-1 menu already call; without the mixer asset the master is AudioListener.volume as before.
    /// </summary>
    public static class W86AudioSettingsV01
    {
        public const string PrefMaster = OvAudioMixerV01.LegacyMasterPref;
        public const float DefaultMaster = 1f;
        /// <summary>Steps of the volume row (percent).</summary>
        public static readonly int[] Steps = { 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 };

        public static float LoadMaster() => OvAudioMixerV01.Load(OvAudioBus.Master);

        public static void ApplyMaster(float volume, bool save) => OvAudioMixerV01.Set(OvAudioBus.Master, volume, save);

        /// <summary>Every saved bus volume (the master and, with the mixer, Effects / Ambience / VoiceUI).</summary>
        public static void ApplySavedAtStartup() => OvAudioMixerV01.ApplySaved();

        public static int NearestStep(float volume)
        {
            int pct = Mathf.RoundToInt(Mathf.Clamp01(volume) * 100f), best = 0;
            for (int i = 0; i < Steps.Length; i++) if (Mathf.Abs(Steps[i] - pct) < Mathf.Abs(Steps[best] - pct)) best = i;
            return best;
        }
    }
}
