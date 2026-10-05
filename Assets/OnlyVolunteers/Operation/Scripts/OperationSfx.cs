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
    /// Placeholder cartoon sounds synthesised in code (no audio assets yet). Each cue name matches a row of the sound
    /// table in docs/drafts/OPERATION_PRESENTATION_DRAFT.md, so real recordings can replace them one by one.
    /// </summary>
    public static class OperationSfx
    {
        private const int Rate = 44100;
        private static AudioClip[] clips;

        public static void Play(AudioSource source, OperationCue cue, float volume = 0.6f)
        {
            if (source == null) return;
            if (clips == null) clips = Build();
            source.pitch = Random.Range(0.93f, 1.07f);
            source.PlayOneShot(clips[(int)cue], volume);
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
