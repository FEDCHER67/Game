using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Audio
{
    /// <summary>
    /// Puts every AudioSource the game makes on a bus of OV_Main_v01 at run time (29.10), without touching the systems
    /// that own them: twice a second it looks for sources with no output group (or the library default, Effects) and
    /// assigns one by owner — the ambience player and the water bodies' amb_* loops → Ambience, the phone and the start menu → VoiceUI, everything else (van engine, operation table and
    /// its synth, kidney game, clinic, police siren, ...) → Effects. The one-shot pool (Sfx) picks its group itself per
    /// clip id. A source someone routed on purpose keeps its group. Also re-applies the saved bus volumes once a scene
    /// has loaded (AudioMixer.SetFloat is ignored before the mixer is live). No mixer asset → does nothing.
    /// </summary>
    public sealed class OvAudioRouterV01 : MonoBehaviour
    {
        public const float ScanSeconds = 0.5f;
        float nextScan, applyAt = -1f;
        int routed;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (FindAnyObjectByType<OvAudioRouterV01>() != null) return;
            var go = new GameObject("[Audio] Mixer router");
            DontDestroyOnLoad(go);
            go.AddComponent<OvAudioRouterV01>();
        }

        void OnEnable() => SceneManager.sceneLoaded += OnScene;
        void OnDisable() => SceneManager.sceneLoaded -= OnScene;
        void OnScene(Scene s, LoadSceneMode m) { applyAt = Time.unscaledTime + 0.1f; nextScan = 0f; }

        void Start()
        {
            OvAudioMixerV01.ApplySaved();
            applyAt = Time.unscaledTime + 0.1f;
        }

        void Update()
        {
            if (!OvAudioMixerV01.HasMixer) { enabled = false; return; }
            if (applyAt > 0f && Time.unscaledTime >= applyAt) { applyAt = -1f; OvAudioMixerV01.ApplySaved(); }
            if (Time.unscaledTime < nextScan) return;
            nextScan = Time.unscaledTime + ScanSeconds;
            var effects = OvAudioMixerV01.Group(OvAudioBus.Effects);
            foreach (AudioSource s in FindObjectsByType<AudioSource>(FindObjectsInactive.Include))
            {
                // unrouted, or on the library's default output (Effects: AmbiencePlayer, water and engine audio copy
                // SfxLibrary.Output when they make their sources) while the owner belongs to another bus
                if (s == null || s.outputAudioMixerGroup != null && s.outputAudioMixerGroup != effects) continue;
                var group = OvAudioMixerV01.Group(Classify(s));
                if (group == null || group == s.outputAudioMixerGroup) continue;
                s.outputAudioMixerGroup = group;
                routed++;
            }
        }

        public int Routed => routed;

        public static OvAudioBus Classify(AudioSource s)
        {
            if (s.GetComponentInParent<AmbiencePlayer>(true) != null) return OvAudioBus.Ambience;
            // the environment loops WaterLoop puts on water bodies (amb_* clips); wading / swimming loops on the van and
            // the NPCs (WaterBodyAudio on movers) are their own sounds: Effects
            string clip = s.clip != null ? s.clip.name : "";
            if (s.loop && clip.StartsWith("amb_", System.StringComparison.Ordinal)) return OvAudioBus.Ambience;
            if (s.GetComponentInParent<OnlyVolunteers.Phone.PhoneController>(true) != null) return OvAudioBus.VoiceUi;
            Transform t = s.transform;
            while (t != null)
            {
                if (t.name.StartsWith("[Menu]", System.StringComparison.Ordinal)) return OvAudioBus.VoiceUi;
                t = t.parent;
            }
            return OvAudioBus.Effects;
        }
    }
}
