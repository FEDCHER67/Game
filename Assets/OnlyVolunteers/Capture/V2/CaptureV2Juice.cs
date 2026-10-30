using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture juice: hit-stop (a short Time.timeScale dip in unscaled time), camera shake, kick and lean
    /// (render-only rotation offsets on the player's camera, applied after KccFirstPersonInput.LateUpdate, so the view
    /// direction the game reads is never changed by them) and the placeholder sounds (CaptureV2Sounds).</summary>
    [DefaultExecutionOrder(31000)]
    public sealed class CaptureV2Juice : MonoBehaviour
    {
        private static CaptureV2Juice _instance;
        /// <summary>The camera the offsets go on (the hands set it).</summary>
        public static Camera View;

        private bool _stopping;
        private float _stopUntil, _savedScale = 1f;
        private float _shakeAmp, _shakeUntil, _shakeLength = 0.2f;
        private Vector3 _kick;       // decaying offset, degrees (pitch, yaw, roll)
        private Vector3 _lean;       // eased toward _leanTarget
        private Vector3 _leanTarget;
        private float _leanUntil;

        private static CaptureV2Juice I
        {
            get
            {
                if (_instance == null)
                {
                    var go = new GameObject("[Capture V2] juice");
                    _instance = go.AddComponent<CaptureV2Juice>();
                }
                return _instance;
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            _instance = null;
            View = null;
        }

        /// <summary>Freeze-frame for 'seconds' of real time (time scale 0.05). Never while the game is paused.</summary>
        public static void HitStop(float seconds)
        {
            if (seconds <= 0f) return;
            CaptureV2Juice j = I;
            if (!j._stopping)
            {
                if (Time.timeScale < 0.5f) return; // paused or slowed by something else: leave it alone
                j._savedScale = Time.timeScale;
                j._stopping = true;
            }
            j._stopUntil = Mathf.Max(j._stopUntil, Time.unscaledTime + seconds);
            Time.timeScale = 0.05f;
        }

        public static void Shake(float degrees, float seconds)
        {
            CaptureV2Juice j = I;
            j._shakeAmp = Mathf.Max(j._shakeAmp * Mathf.Clamp01((j._shakeUntil - Time.unscaledTime) / j._shakeLength), degrees);
            j._shakeLength = Mathf.Max(0.05f, seconds);
            j._shakeUntil = Time.unscaledTime + j._shakeLength;
        }

        /// <summary>A sharp camera kick (degrees: pitch up is negative), decaying in ~0.15 s.</summary>
        public static void Kick(float pitch, float yaw, float roll) => I._kick += new Vector3(pitch, yaw, roll);

        /// <summary>A held lean (wind-up, throw swing): set every frame while it should last; eases in and back out.</summary>
        public static void Lean(Vector3 euler)
        {
            CaptureV2Juice j = I;
            j._leanTarget = euler;
            j._leanUntil = Time.unscaledTime + 0.05f;
        }

        private void Update()
        {
            if (_stopping && Time.unscaledTime >= _stopUntil)
            {
                _stopping = false;
                if (Time.timeScale <= 0.06f) Time.timeScale = _savedScale > 0.06f ? _savedScale : 1f;
            }
        }

        private void LateUpdate()
        {
            float dt = Time.unscaledDeltaTime;
            if (Time.unscaledTime > _leanUntil) _leanTarget = Vector3.zero;
            _lean = Vector3.Lerp(_lean, _leanTarget, 1f - Mathf.Exp(-dt * 18f));
            _kick *= Mathf.Exp(-dt * 14f);
            Vector3 shake = Vector3.zero;
            float left = _shakeUntil - Time.unscaledTime;
            if (left > 0f)
            {
                float a = _shakeAmp * (left / _shakeLength);
                float t = Time.unscaledTime * 47f;
                shake = new Vector3(Mathf.PerlinNoise(t, 0.3f) - 0.5f, Mathf.PerlinNoise(0.7f, t) - 0.5f, Mathf.PerlinNoise(t, t * 0.5f) - 0.5f) * (2f * a);
            }
            Vector3 total = _lean + _kick + shake;
            if (View == null || total.sqrMagnitude < 1e-6f) return;
            View.transform.rotation *= Quaternion.Euler(total);
        }

        private void OnDisable()
        {
            if (_stopping && Time.timeScale <= 0.06f) Time.timeScale = _savedScale > 0.06f ? _savedScale : 1f;
            _stopping = false;
        }
    }

    /// <summary>Placeholder sounds of V2 capture, synthesised at start (no files, no licences): smack, whoosh, boom, belt
    /// clack, pop, boing, bonk. Played 3D at a point from a small pool. Replace with recorded CC0 sounds later.</summary>
    public static class CaptureV2Sounds
    {
        public const string Smack = "smack", Whoosh = "whoosh", Boom = "boom", Clack = "clack", Pop = "pop", Boing = "boing", Bonk = "bonk";
        private const int Rate = 44100;
        private static readonly Dictionary<string, AudioClip> Clips = new();
        private static readonly List<AudioSource> Pool = new();
        private static GameObject _root;
        private static int _next;
        public static int Played { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Clips.Clear();
            Pool.Clear();
            _root = null;
            _next = 0;
            Played = 0;
        }

        public static void Play(string id, Vector3 at, float volume = 1f, float pitch = 1f)
        {
            AudioClip clip = Clip(id);
            if (clip == null) return;
            if (_root == null)
            {
                _root = new GameObject("[Capture V2] sounds");
                Object.DontDestroyOnLoad(_root);
                Pool.Clear();
            }
            if (Pool.Count < 10)
            {
                var go = new GameObject("v2 sfx");
                go.transform.SetParent(_root.transform, false);
                var s = go.AddComponent<AudioSource>();
                s.playOnAwake = false;
                s.spatialBlend = 1f;
                s.minDistance = 2.5f;
                s.maxDistance = 45f;
                s.rolloffMode = AudioRolloffMode.Linear;
                s.dopplerLevel = 0f;
                Pool.Add(s);
            }
            AudioSource src = Pool[_next % Pool.Count];
            _next++;
            src.transform.position = at;
            src.clip = clip;
            src.volume = Mathf.Clamp01(volume);
            src.pitch = pitch * Random.Range(0.94f, 1.06f);
            src.Play();
            Played++;
        }

        private static AudioClip Clip(string id)
        {
            if (Clips.TryGetValue(id, out AudioClip c)) return c;
            float[] d = id switch
            {
                Smack => Make(0.2f, (t, n) => n * Mathf.Exp(-t / 0.018f) * 0.9f + Mathf.Sin(2f * Mathf.PI * 190f * t) * Mathf.Exp(-t / 0.05f) * 0.6f),
                Whoosh => MakeFiltered(0.32f, t => Mathf.Sin(Mathf.PI * t / 0.32f) * 0.55f, t => 0.05f + 0.5f * t / 0.32f),
                Boom => Make(0.7f, (t, n) => (Mathf.Sin(2f * Mathf.PI * 52f * t) + 0.6f * Mathf.Sin(2f * Mathf.PI * 87f * t)) * Mathf.Exp(-t / 0.16f) * 0.75f + n * Mathf.Exp(-t / 0.03f) * 0.5f),
                Clack => Make(0.16f, (t, n) => Click(t, 0f) + Click(t, 0.065f)),
                Pop => Make(0.3f, (t, n) => Mathf.Sin(2f * Mathf.PI * Mathf.Lerp(900f, 110f, Mathf.Sqrt(t / 0.3f)) * t) * Mathf.Exp(-t / 0.07f) * 0.9f + n * Mathf.Exp(-t / 0.008f)),
                Boing => Make(0.45f, (t, n) => Mathf.Sin(2f * Mathf.PI * (260f * t + 14f * Mathf.Sin(2f * Mathf.PI * 9f * t) * Mathf.Exp(-t / 0.2f))) * Mathf.Exp(-t / 0.18f) * 0.8f),
                Bonk => Make(0.16f, (t, n) => (Mathf.Sin(2f * Mathf.PI * 820f * t) + 0.7f * Mathf.Sin(2f * Mathf.PI * 1310f * t)) * Mathf.Exp(-t / 0.035f) * 0.6f + n * Mathf.Exp(-t / 0.004f) * 0.5f),
                _ => null,
            };
            if (d == null) return null;
            c = AudioClip.Create("v2_" + id, d.Length, 1, Rate, false);
            c.SetData(d, 0);
            Clips[id] = c;
            return c;
        }

        private static float Click(float t, float at)
        {
            float u = t - at;
            if (u < 0f) return 0f;
            return (Mathf.Sin(2f * Mathf.PI * 2300f * u) * 0.7f + Mathf.Sin(2f * Mathf.PI * 3550f * u) * 0.4f) * Mathf.Exp(-u / 0.01f);
        }

        private static float[] Make(float seconds, System.Func<float, float, float> f)
        {
            var rnd = new System.Random(seconds.GetHashCode());
            var d = new float[Mathf.CeilToInt(seconds * Rate)];
            for (int i = 0; i < d.Length; i++)
            {
                float n = (float)(rnd.NextDouble() * 2.0 - 1.0);
                d[i] = Mathf.Clamp(f(i / (float)Rate, n), -1f, 1f);
            }
            return d;
        }

        // Noise through a one-pole low-pass whose cutoff (0..1 of the sample rate's share) moves over time: a whoosh.
        private static float[] MakeFiltered(float seconds, System.Func<float, float> envelope, System.Func<float, float> cutoff)
        {
            var rnd = new System.Random(7);
            var d = new float[Mathf.CeilToInt(seconds * Rate)];
            float y = 0f;
            for (int i = 0; i < d.Length; i++)
            {
                float t = i / (float)Rate;
                float n = (float)(rnd.NextDouble() * 2.0 - 1.0);
                y += Mathf.Clamp01(cutoff(t)) * (n - y);
                d[i] = Mathf.Clamp(y * envelope(t) * 2.5f, -1f, 1f);
            }
            return d;
        }
    }
}
