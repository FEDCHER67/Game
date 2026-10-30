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
        private Vector3 _kickFast;   // the slap's tiny snap (pitch, yaw), gone in ~0.1 s
        private float _fovHold, _fovHoldTarget, _fovHoldUntil, _fovPop, _fovApplied;
        private float _fovWritten = float.NaN;
        private Camera _fovCam;
        /// <summary>Runs in this LateUpdate (order 31000, after the animators and the arms): the V2 head snap.</summary>
        public static event System.Action LateTick;
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

        /// <summary>The slap's kick (Vadim 31.10): a tiny, sharp pitch/yaw snap, never a roll, gone in about 0.1 s.</summary>
        public static void KickFast(float pitch, float yaw) => I._kickFast += new Vector3(pitch, yaw, 0f);

        /// <summary>A held field-of-view offset in degrees (negative = push in), set every frame while it should last;
        /// eases in at 'rate' per s and back out fast when no longer set.</summary>
        public static void Fov(float degrees, float rate = 9f)
        {
            CaptureV2Juice j = I;
            j._fovHoldTarget = degrees;
            j._fovHoldUntil = Time.unscaledTime + 0.05f;
            j._fovRate = rate;
        }

        /// <summary>The field of view snaps back from any push-in at once and pops this many degrees wider, settling fast.</summary>
        public static void FovPop(float degrees)
        {
            CaptureV2Juice j = I;
            j._fovHold = 0f;
            j._fovHoldTarget = 0f;
            j._fovPop += degrees;
        }

        private float _fovRate = 9f;

        /// <summary>The current field-of-view offset (tests).</summary>
        public static float FovOffset => _instance != null ? _instance._fovApplied : 0f;

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
            LateTick?.Invoke();
            if (Time.unscaledTime > _leanUntil) _leanTarget = Vector3.zero;
            _lean = Vector3.Lerp(_lean, _leanTarget, 1f - Mathf.Exp(-dt * 18f));
            _kick *= Mathf.Exp(-dt * 14f);
            _kickFast *= Mathf.Exp(-dt * 32f);
            ApplyFov(dt);
            Vector3 shake = Vector3.zero;
            float left = _shakeUntil - Time.unscaledTime;
            if (left > 0f)
            {
                float a = _shakeAmp * (left / _shakeLength);
                float t = Time.unscaledTime * 47f;
                shake = new Vector3(Mathf.PerlinNoise(t, 0.3f) - 0.5f, Mathf.PerlinNoise(0.7f, t) - 0.5f, 0f) * (2f * a); // no roll
            }
            Vector3 total = _lean + _kick + _kickFast + shake;
            if (View == null || total.sqrMagnitude < 1e-6f) return;
            View.transform.rotation *= Quaternion.Euler(total);
        }

        // The offset rides on whatever field of view the game sets: if nobody changed it since our last write, the base is
        // that minus our offset, else the new value is the base.
        private void ApplyFov(float dt)
        {
            if (Time.unscaledTime > _fovHoldUntil) _fovHoldTarget = 0f;
            float rate = _fovHoldTarget == 0f ? 22f : _fovRate;
            _fovHold = Mathf.Lerp(_fovHold, _fovHoldTarget, 1f - Mathf.Exp(-dt * rate));
            _fovPop *= Mathf.Exp(-dt * 16f);
            if (Mathf.Abs(_fovHold) < 0.01f && _fovHoldTarget == 0f) _fovHold = 0f;
            if (Mathf.Abs(_fovPop) < 0.01f) _fovPop = 0f;
            float off = _fovHold + _fovPop;
            if (View != _fovCam)
            {
                if (_fovCam != null && !float.IsNaN(_fovWritten) && Mathf.Abs(_fovCam.fieldOfView - _fovWritten) < 1e-3f)
                    _fovCam.fieldOfView -= _fovApplied;
                _fovCam = View;
                _fovApplied = 0f;
                _fovWritten = float.NaN;
            }
            if (_fovCam == null || (off == 0f && _fovApplied == 0f)) return;
            float cur = _fovCam.fieldOfView;
            float baseFov = !float.IsNaN(_fovWritten) && Mathf.Abs(cur - _fovWritten) < 1e-3f ? cur - _fovApplied : cur;
            _fovCam.fieldOfView = baseFov + off;
            _fovWritten = _fovCam.fieldOfView;
            _fovApplied = off;
        }

        private void OnDisable()
        {
            if (_stopping && Time.timeScale <= 0.06f) Time.timeScale = _savedScale > 0.06f ? _savedScale : 1f;
            _stopping = false;
            if (_fovCam != null && !float.IsNaN(_fovWritten) && Mathf.Abs(_fovCam.fieldOfView - _fovWritten) < 1e-3f) _fovCam.fieldOfView -= _fovApplied;
            _fovApplied = 0f;
            _fovWritten = float.NaN;
        }
    }

    /// <summary>Sounds of V2 capture. The slap's hit is Vadim's recorded slap in three strength tiers (Resources/
    /// CaptureV2SlapBank; PlaySlapHit: the tier by the charge, a random variant never the same twice in a row, pitch
    /// +-3 %, started so its peak lands on the contact); everything else (and the slap while the bank
    /// is empty) is synthesised at start: smack, whoosh, boom, belt clack, pop, boing, bonk. Played 3D at a point from a
    /// small pool.</summary>
    public static class CaptureV2Sounds
    {
        public const string Smack = "smack", Whoosh = "whoosh", Boom = "boom", Clack = "clack", Pop = "pop", Boing = "boing", Bonk = "bonk";
        private const int Rate = 44100;
        private static readonly Dictionary<string, AudioClip> Clips = new();
        private static readonly List<AudioSource> Pool = new();
        private static GameObject _root;
        private static int _next;
        public static int Played { get; private set; }
        public static int PlayedRecorded { get; private set; }
        private static CaptureV2SlapBank _bank;
        private static bool _bankLoaded;
        private static readonly int[] LastPick = { -1, -1, -1 };

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Clips.Clear();
            Pool.Clear();
            _root = null;
            _next = 0;
            Played = 0;
            PlayedRecorded = 0;
            _bank = null;
            _bankLoaded = false;
            LastPick[0] = LastPick[1] = LastPick[2] = -1;
        }

        /// <summary>The recorded slap clips (null or empty sets when the bank is missing).</summary>
        public static CaptureV2SlapBank Bank
        {
            get
            {
                if (!_bankLoaded)
                {
                    _bankLoaded = true;
                    _bank = Resources.Load<CaptureV2SlapBank>(CaptureV2SlapBank.ResourceName);
                }
                return _bank;
            }
        }

        /// <summary>Vadim's slap hit is there (else the caller uses the synthesised smack at the contact).</summary>
        public static bool HasSlapHit => Bank != null && (Bank.Hit != null || Bank.Light.Length + Bank.Medium.Length + Bank.Heavy.Length > 0);
        /// <summary>The tier for a charge 0..1: 0 light, 1 medium, 2 heavy.</summary>
        public static int SlapTier(float charge) => Bank == null ? 1 : charge <= Bank.LightUpTo ? 0 : charge <= Bank.MediumUpTo ? 1 : 2;
        /// <summary>Seconds from the hit sound's start to its peak for that charge (0 without a sound).</summary>
        public static float SlapHitPeak(float charge) => !HasSlapHit ? 0f : SlapTier(charge) == 0 && Bank.Light.Length > 0 ? Bank.LightPeak : Bank.HitPeak;
        /// <summary>The name of the last slap hit played (tests).</summary>
        public static string LastSlapHit { get; private set; } = "";

        /// <summary>Vadim's slap hit for this charge (a random variant of its tier, never the same twice in a row; the
        /// original when the tier is empty), 'skip' seconds into the clip so its peak lands on the contact, pitch +-3 %.</summary>
        public static bool PlaySlapHit(float charge, Vector3 at, float volume, float skip)
        {
            if (!HasSlapHit) return false;
            int tier = SlapTier(charge);
            AudioClip[] set = tier == 0 ? Bank.Light : tier == 1 ? Bank.Medium : Bank.Heavy;
            AudioClip clip = Bank.Hit;
            if (set != null && set.Length > 0)
            {
                int n = set.Length, last = LastPick[tier];
                int i = n == 1 ? 0 : Random.Range(0, n - 1);
                if (n > 1 && last >= 0 && i >= last) i++;
                LastPick[tier] = i;
                if (set[i] != null) clip = set[i];
            }
            if (clip == null) return false;
            PlayClip(clip, at, volume, 1f, 0.03f, skip);
            LastSlapHit = clip.name;
            PlayedRecorded++;
            return true;
        }

        public static void Play(string id, Vector3 at, float volume = 1f, float pitch = 1f)
        {
            AudioClip clip = Clip(id);
            if (clip == null) return;
            PlayClip(clip, at, volume, pitch, 0.06f, 0f);
        }

        private static void PlayClip(AudioClip clip, Vector3 at, float volume, float pitch, float variance, float skip)
        {
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
            src.pitch = pitch * Random.Range(1f - variance, 1f + variance);
            src.Play();
            if (skip > 0f) src.time = Mathf.Min(skip, clip.length - 0.01f);
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
