using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Audio;

namespace OnlyVolunteers.Audio
{
    // Offline sound table: event id (SfxIds) -> clips plus how to play them. One asset,
    // Audio/Resources/SfxLibrary.asset, which Sfx loads on first use. The editor menu
    // "OnlyVolunteers/Audio/..." (SfxLibraryImporter) fills it by file-name prefix; hand-tuned volume, pitch and 3D
    // settings survive a refill, and Locked entries keep their clips too. Placeholders: ArtSource/Audio/SFX_GEN v01.
    [CreateAssetMenu(menuName = "VOLUNTEERS ONLY/Sfx Library")]
    public sealed class SfxLibrary : ScriptableObject
    {
        [Serializable]
        public sealed class Entry
        {
            public string Id;
            [Tooltip("Picked at random; the same clip never plays twice in a row when there are two or more.")]
            public AudioClip[] Clips = Array.Empty<AudioClip>();
            [Tooltip("Random volume (0..1), multiplied by the caller's scale.")]
            public Vector2 Volume = new(0.85f, 1f);
            [Tooltip("Random pitch, multiplied by the caller's scale.")]
            public Vector2 Pitch = new(0.95f, 1.05f);
            [Range(0f, 1f), Tooltip("0 = 2D (UI), 1 = fully 3D.")]
            public float SpatialBlend = 1f;
            public float MinDistance = 1.5f;
            public float MaxDistance = 35f;
            [Tooltip("Seconds: a second call for this id sooner than this is dropped (a body bouncing, a door rattling).")]
            public float Cooldown = 0.05f;
            [Range(0, 256), Tooltip("AudioSource priority: 0 most important. Voice stealing takes the least important.")]
            public int Priority = 128;
            [Tooltip("The refill menu leaves this entry's clips alone (hand-picked sounds).")]
            public bool Locked;

            [NonSerialized] public float LastPlayed = float.NegativeInfinity;
            [NonSerialized] public int LastClip = -1;
        }

        [Tooltip("AudioSources in the pool: the most sounds at once.")]
        [Range(4, 64)] public int Voices = 24;
        [Tooltip("Optional mixer group for every SFX.")]
        public AudioMixerGroup Output;
        public List<Entry> Entries = new();

        private Dictionary<string, Entry> _byId;

        /// <summary>The entry for 'id', or null. No allocation after the first call.</summary>
        public Entry Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            if (_byId == null) Rebuild();
            return _byId.TryGetValue(id, out Entry entry) ? entry : null;
        }

        /// <summary>After editing Entries from code (the importer does this).</summary>
        public void Rebuild()
        {
            _byId ??= new Dictionary<string, Entry>(StringComparer.Ordinal);
            _byId.Clear();
            foreach (Entry entry in Entries)
                if (entry != null && !string.IsNullOrEmpty(entry.Id))
                    _byId[entry.Id] = entry;
        }

        private void OnEnable() => _byId = null;
        private void OnValidate() => _byId = null;
    }
}
