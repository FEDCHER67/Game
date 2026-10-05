using UnityEngine;

namespace OnlyVolunteers.Audio
{
    // Fire-and-forget one-shot sounds at a world point, from a fixed pool of AudioSources (made on first use, kept across
    // scenes). No allocation per call: the library is looked up by id (string key), the pool is an array, the sources
    // only move. Every call is optional: no library, an unknown id or an entry without clips just returns false, so
    // gameplay code never has to check. Local presentation only (each machine plays what it sees); nothing networked.
    public static class Sfx
    {
        private const string ResourcePath = "SfxLibrary"; // Audio/Resources/SfxLibrary.asset

        private static SfxLibrary _library;
        private static bool _triedLoad;
        private static GameObject _root;
        private static AudioSource[] _voices;
        private static float[] _started;
        private static int _next;

        /// <summary>The library in use: Resources/SfxLibrary unless something set another one. Null = silent.</summary>
        public static SfxLibrary Library
        {
            get
            {
                if (_library == null && !_triedLoad)
                {
                    _triedLoad = true;
                    _library = Resources.Load<SfxLibrary>(ResourcePath);
                }
                return _library;
            }
            set
            {
                _library = value;
                _triedLoad = true;
            }
        }

        /// <summary>Whether 'id' has at least one clip (e.g. to skip work that only feeds a sound).</summary>
        public static bool Has(string id)
        {
            SfxLibrary.Entry entry = Library != null ? Library.Find(id) : null;
            return entry != null && entry.Clips != null && entry.Clips.Length > 0;
        }

        /// <summary>Plays a random clip of 'id' at 'position'. volumeScale/pitchScale multiply the entry's random
        /// ranges. False when nothing played (no library or clips, the id's cooldown, every voice busy with something
        /// more important).</summary>
        public static bool PlayAt(string id, Vector3 position, float volumeScale = 1f, float pitchScale = 1f)
        {
            SfxLibrary library = Library;
            if (library == null || volumeScale <= 0f) return false;
            SfxLibrary.Entry entry = library.Find(id);
            if (entry == null || entry.Clips == null || entry.Clips.Length == 0) return false;
            float now = Time.time;
            // LastPlayed outlives a Play session in the Editor (the asset stays loaded) while Time.time restarts at 0.
            if (now >= entry.LastPlayed && now - entry.LastPlayed < entry.Cooldown) return false;
            AudioClip clip = Pick(entry);
            if (clip == null) return false;
            int voice = Voice(library, entry.Priority);
            if (voice < 0) return false;

            entry.LastPlayed = now;
            AudioSource source = _voices[voice];
            source.Stop();
            source.transform.position = position;
            source.clip = clip;
            source.outputAudioMixerGroup = library.Output;
            source.volume = Mathf.Clamp01(Random.Range(entry.Volume.x, entry.Volume.y) * volumeScale);
            source.pitch = Mathf.Clamp(Random.Range(entry.Pitch.x, entry.Pitch.y) * pitchScale, 0.1f, 3f);
            source.spatialBlend = entry.SpatialBlend;
            source.minDistance = Mathf.Max(0.01f, entry.MinDistance);
            source.maxDistance = Mathf.Max(source.minDistance + 0.01f, entry.MaxDistance);
            source.priority = entry.Priority;
            source.Play();
            _started[voice] = now;
            return true;
        }

        // A random clip, not the one played last time when there is a choice.
        private static AudioClip Pick(SfxLibrary.Entry entry)
        {
            int count = entry.Clips.Length;
            int index = Random.Range(0, count);
            if (count > 1 && index == entry.LastClip) index = (index + 1 + Random.Range(0, count - 1)) % count;
            entry.LastClip = index;
            return entry.Clips[index];
        }

        // A free source (round robin), else the least important playing one that is not more important than this sound
        // (AudioSource priority: higher number = less important), the oldest on a tie. -1: all busy with better sounds.
        private static int Voice(SfxLibrary library, int priority)
        {
            if (_root == null) Build(library.Voices);
            int count = _voices.Length;
            for (int i = 0; i < count; i++)
            {
                int index = (_next + i) % count;
                if (_voices[index].isPlaying) continue;
                _next = (index + 1) % count;
                return index;
            }
            int steal = -1;
            for (int i = 0; i < count; i++)
            {
                int p = _voices[i].priority;
                if (p < priority) continue;
                if (steal < 0 || p > _voices[steal].priority || (p == _voices[steal].priority && _started[i] < _started[steal]))
                    steal = i;
            }
            return steal;
        }

        private static void Build(int count)
        {
            _root = new GameObject("Sfx (pool)");
            Object.DontDestroyOnLoad(_root);
            _voices = new AudioSource[Mathf.Max(1, count)];
            _started = new float[_voices.Length];
            for (int i = 0; i < _voices.Length; i++)
            {
                var child = new GameObject("Voice " + i);
                child.transform.SetParent(_root.transform, false);
                AudioSource source = child.AddComponent<AudioSource>();
                source.playOnAwake = false;
                source.loop = false;
                source.dopplerLevel = 0f; // pooled sources jump between points
                source.rolloffMode = AudioRolloffMode.Logarithmic;
                _voices[i] = source;
            }
            _next = 0;
        }

        // Enter Play mode without a domain reload keeps statics: start clean every time.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            _library = null;
            _triedLoad = false;
            _root = null;
            _voices = null;
            _started = null;
            _next = 0;
        }
    }
}
