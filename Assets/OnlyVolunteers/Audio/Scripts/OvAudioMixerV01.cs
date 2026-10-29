using System;
using UnityEngine;
using UnityEngine.Audio;

namespace OnlyVolunteers.Audio
{
    /// <summary>The mixer buses that exist for the game's actual sounds (29.10). There is no music in the game yet, so there
    /// is no Music bus (one is added with the first music track).</summary>
    public enum OvAudioBus { Master = 0, Effects = 1, Ambience = 2, VoiceUi = 3 }

    /// <summary>
    /// The game's AudioMixer OV_Main_v01 (Master → Effects / Ambience / VoiceUI) and its volume settings. Each bus has an
    /// exposed volume parameter (OV_Vol_*); the settings page sets them in linear 0..1 (stored per machine in PlayerPrefs,
    /// never in the world save) and they are applied on start. Routing: <see cref="SfxGroup"/> for the one-shot library
    /// (NPC voices, UI and phone sounds → VoiceUI, everything else → Effects), <see cref="OvAudioRouterV01"/> for the
    /// AudioSources other systems create (ambience and water → Ambience, the phone → VoiceUI, the rest → Effects). Without
    /// the mixer asset everything falls back to the old master-only volume (AudioListener.volume).
    /// </summary>
    public static class OvAudioMixerV01
    {
        public static readonly OvAudioBus[] Buses = { OvAudioBus.Master, OvAudioBus.Effects, OvAudioBus.Ambience, OvAudioBus.VoiceUi };
        public const string LegacyMasterPref = "ov_audio_master";

        static AudioMixer mixer;
        static bool tried;
        static readonly AudioMixerGroup[] groups = new AudioMixerGroup[4];

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { mixer = null; tried = false; Array.Clear(groups, 0, groups.Length); }

        public static AudioMixer Mixer
        {
            get
            {
                if (mixer == null && !tried)
                {
                    tried = true;
                    var routing = Resources.Load<OvAudioRoutingV01>(OvAudioRoutingV01.ResourceName);
                    mixer = routing != null ? routing.Mixer : null;
                    if (mixer == null) Debug.LogWarning("[OV Audio] no mixer (Resources/" + OvAudioRoutingV01.ResourceName + "): master volume only");
                }
                return mixer;
            }
        }

        public static bool HasMixer => Mixer != null;

        public static string GroupName(OvAudioBus bus) =>
            bus == OvAudioBus.Master ? "Master" : bus == OvAudioBus.Effects ? "Effects" : bus == OvAudioBus.Ambience ? "Ambience" : "VoiceUI";

        public static string Parameter(OvAudioBus bus) => "OV_Vol_" + GroupName(bus);

        public static string Label(OvAudioBus bus) =>
            bus == OvAudioBus.Master ? "Общая громкость" : bus == OvAudioBus.Effects ? "Эффекты" : bus == OvAudioBus.Ambience ? "Окружение" : "Голоса и интерфейс";

        public static string Hint(OvAudioBus bus) =>
            bus == OvAudioBus.Master ? "Все звуки игры" : bus == OvAudioBus.Effects ? "Бусик, удары, операция, предметы, сирена" :
            bus == OvAudioBus.Ambience ? "Лес, море, город, вода" : "Крики и бормотание NPC, телефон, кнопки меню";

        static string Pref(OvAudioBus bus) => "ov_audio_bus_" + GroupName(bus).ToLowerInvariant();

        public static AudioMixerGroup Group(OvAudioBus bus)
        {
            int i = (int)bus;
            if (groups[i] != null) return groups[i];
            AudioMixer m = Mixer;
            if (m == null) return null;
            AudioMixerGroup[] found = m.FindMatchingGroups(bus == OvAudioBus.Master ? "Master" : "Master/" + GroupName(bus));
            if (found == null || found.Length == 0) found = m.FindMatchingGroups(GroupName(bus));
            groups[i] = found != null && found.Length > 0 ? found[0] : null;
            return groups[i];
        }

        /// <summary>The group for a one-shot library id (NPC voices, UI and the phone → VoiceUI; the rest → Effects).</summary>
        public static AudioMixerGroup SfxGroup(string id, AudioMixerGroup fallback)
        {
            if (!HasMixer) return fallback;
            id ??= "";
            bool voiceUi = id.StartsWith("npc_", StringComparison.Ordinal) || id.StartsWith("ui_", StringComparison.Ordinal) ||
                           id.StartsWith("phone_", StringComparison.Ordinal) || id.StartsWith("cash_", StringComparison.Ordinal);
            return Group(voiceUi ? OvAudioBus.VoiceUi : OvAudioBus.Effects) ?? fallback;
        }

        /// <summary>Saved linear volume 0..1 (the master migrates the PLAYER-stage master-only value once).</summary>
        public static float Load(OvAudioBus bus)
        {
            float fallback = bus == OvAudioBus.Master ? PlayerPrefs.GetFloat(LegacyMasterPref, 1f) : 1f;
            float v = PlayerPrefs.GetFloat(Pref(bus), fallback);
            return float.IsNaN(v) ? 1f : Mathf.Clamp01(v);
        }

        public static float ToDecibels(float linear) => linear <= 0.0001f ? -80f : Mathf.Clamp(20f * Mathf.Log10(linear), -80f, 0f);

        /// <summary>Applies one bus now; save = write it to PlayerPrefs (the settings page's Apply).</summary>
        public static void Set(OvAudioBus bus, float linear, bool save)
        {
            linear = Mathf.Clamp01(float.IsNaN(linear) ? 1f : linear);
            AudioMixer m = Mixer;
            if (m != null)
            {
                m.SetFloat(Parameter(bus), ToDecibels(linear));
                if (bus == OvAudioBus.Master) AudioListener.volume = 1f; // the mixer's master does it now (no double attenuation)
            }
            else if (bus == OvAudioBus.Master) AudioListener.volume = linear;
            if (!save) return;
            PlayerPrefs.SetFloat(Pref(bus), linear);
            if (bus == OvAudioBus.Master) PlayerPrefs.SetFloat(LegacyMasterPref, linear);
            PlayerPrefs.Save();
        }

        /// <summary>Every bus from its saved value (start of any scene with a menu, and the router on first use).</summary>
        public static void ApplySaved()
        {
            foreach (OvAudioBus b in Buses)
                if (b == OvAudioBus.Master || HasMixer) Set(b, Load(b), false);
        }
    }
}
