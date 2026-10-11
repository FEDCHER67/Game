using OnlyVolunteers.Audio;
using UnityEngine;

namespace OnlyVolunteers.Operation
{
    public enum OperationCue
    {
        Strap,
        Tick,
        Slit,
        Yelp,
        Boing,
        Pop,
        Rip,
        Tape,
    }

    /// <summary>
    /// Cartoon sounds of the operation table. A cue plays a recorded clip of its SfxLibrary entry (operation_strap,
    /// operation_tick, ...; Audio/Library_v1) with that entry's volume and pitch range; a cue without clips falls back to
    /// the placeholder synthesised in code. Each cue name matches a row of the sound table in
    /// docs/drafts/OPERATION_PRESENTATION_DRAFT.md.
    /// </summary>
    public static class OperationSfx
    {
        private const int Rate = 44100;
        private static AudioClip[] clips;

        // Library id per cue, in OperationCue order.
        private static readonly string[] Ids =
        {
            SfxIds.OperationStrap, SfxIds.OperationTick, SfxIds.OperationSlit, SfxIds.OperationYelp,
            SfxIds.OperationBoing, SfxIds.OperationPop, SfxIds.OperationRip, SfxIds.OperationTape,
        };

        public static void Play(AudioSource source, OperationCue cue, float volume = 0.6f)
        {
            if (source == null) return;
            if (PlayRecorded(source, cue, volume)) return;
            if (clips == null) clips = Build();
            source.pitch = Random.Range(0.93f, 1.07f);
            source.PlayOneShot(clips[(int)cue], volume);
        }

        // A random clip of the cue's library entry (not the one played last time; empty slots, e.g. local-only files
        // missing on this machine, are skipped), false when the entry has none.
        private static bool PlayRecorded(AudioSource source, OperationCue cue, float volume)
        {
            int index = (int)cue;
            SfxLibrary library = Sfx.Library;
            SfxLibrary.Entry entry = library != null && index < Ids.Length ? library.Find(Ids[index]) : null;
            if (entry == null || entry.Clips == null || entry.Clips.Length == 0) return false;
            int count = entry.Clips.Length;
            int pick = Random.Range(0, count);
            if (count > 1 && pick == entry.LastClip) pick = (pick + 1 + Random.Range(0, count - 1)) % count;
            for (int i = 0; i < count; i++)
            {
                int at = (pick + i) % count;
                AudioClip clip = entry.Clips[at];
                if (clip == null) continue;
                entry.LastClip = at;
                source.pitch = Random.Range(entry.Pitch.x, entry.Pitch.y);
                source.PlayOneShot(clip, volume * Random.Range(entry.Volume.x, entry.Volume.y));
                return true;
            }
            return false;
        }

        private static AudioClip[] Build()
        {
            var result = new AudioClip[8];
            result[(int)OperationCue.Strap] = Make("Strap", 0.16f, t => Click(t, 0f) + Click(t, 0.09f));
            result[(int)OperationCue.Tick] = Make("Tick", 0.03f, t => Mathf.Sin(t * 2800f * 6.2832f) * (1f - t / 0.03f) * 0.5f);
            result[(int)OperationCue.Slit] = Make("Slit", 0.22f, t => Noise() * Envelope(t, 0.22f) * (0.6f + 0.4f * Mathf.Sin(t * 90f * 6.2832f)));
            result[(int)OperationCue.Yelp] = Make("Yelp", 0.35f, t => Sweep(t, 0.35f, 600f, 1250f, 480f) * Envelope(t, 0.35f));
            result[(int)OperationCue.Boing] = Make("Boing", 0.45f, t =>
                Mathf.Sin(6.2832f * (180f * t + 6f * Mathf.Sin(t * 38f))) * Mathf.Exp(-t * 7f));
            result[(int)OperationCue.Pop] = Make("Pop", 0.14f, t => Sweep(t, 0.14f, 260f, 980f, 980f) * Mathf.Exp(-t * 18f));
            result[(int)OperationCue.Rip] = Make("Rip", 0.3f, t => Noise() * Envelope(t, 0.3f) * (Mathf.Sin(t * 55f * 6.2832f) > 0f ? 1f : 0.35f));
            result[(int)OperationCue.Tape] = Make("Tape", 0.32f, t => Noise() * (t / 0.32f) * (Mathf.Sin(t * 40f * 6.2832f) > -0.2f ? 1f : 0.2f) * 0.6f);
            return result;
        }

        private static AudioClip Make(string name, float seconds, System.Func<float, float> wave)
        {
            int count = Mathf.CeilToInt(seconds * Rate);
            var data = new float[count];
            for (int i = 0; i < count; i++) data[i] = Mathf.Clamp(wave((float)i / Rate), -1f, 1f) * 0.8f;
            AudioClip clip = AudioClip.Create($"Operation_{name}", count, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private static float Noise() => Random.value * 2f - 1f;

        private static float Envelope(float t, float length) => Mathf.Min(1f, t / 0.01f) * (1f - t / length);

        private static float Click(float t, float at) =>
            t < at || t > at + 0.04f ? 0f : Noise() * (1f - (t - at) / 0.04f);

        // Frequency glides start -> peak (first half) -> end (second half); phase is integrated per half.
        private static float Sweep(float t, float length, float start, float peak, float end)
        {
            float half = length * 0.5f;
            float phase = t < half
                ? start * t + (peak - start) * t * t / (2f * half)
                : (start + peak) * half * 0.5f + peak * (t - half) + (end - peak) * (t - half) * (t - half) / (2f * half);
            return Mathf.Sin(6.2832f * phase);
        }
    }
}
