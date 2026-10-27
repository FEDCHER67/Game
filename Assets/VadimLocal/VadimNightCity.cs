using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Art.TextureTest;
using OnlyVolunteers.Sky22V04;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.VadimLocal
{
    /// <summary>Vadim 23.10 (local W86): the night city. Downtown glows like New York at night — warm steady street lights and
    /// ~70 % of the windows lit warm; lamp flicker only in the Rough District and only as a rare, slow, unsettling fade-out; all
    /// other city lights steady and warm.</summary>
    [DefaultExecutionOrder(10000)]
    public sealed class VadimNightCity : MonoBehaviour
    {
        public Rect downtown = new Rect(770, -10, 520, 550);
        public Rect rough = new Rect(560, 650, 480, 310);
        public Color warm = new Color(1f, 0.78f, 0.5f);
        public float windowsLit = 0.6f;

        SkyClock22 clock;
        public float hazeStart = 110f, hazeHalf = 380f, hazeMax = 0.92f;
        public Color hazeDay = new Color(0.68f, 0.79f, 0.90f, 1f), hazeNight = new Color(0.05f, 0.07f, 0.12f, 1f);
        struct L { public Light light; public float baseI; public bool scary; public float seed; }
        readonly List<L> lights = new();
        readonly List<FlickerFollowerV01> followers = new();
        readonly List<(Renderer r, Material[] day, Material[] night)> windows = new();
        public float lightRadius = 90f;
        public int maxLights = 24;
        Camera cam;
        MaterialPropertyBlock block;
        bool lastNight, first = true;
        Volume glow;

        void Start()
        {
            clock = FindAnyObjectByType<SkyClock22>();
            // night bloom: lamps, windows and headlights get a soft halo (weight follows the night)
            glow = new GameObject("VadimNightBloom").AddComponent<Volume>();
            glow.isGlobal = true; glow.priority = 50; glow.weight = 0;
            var prof = ScriptableObject.CreateInstance<VolumeProfile>();
            var bloom = prof.Add<Bloom>(true); bloom.threshold.Override(1.0f); bloom.intensity.Override(0.4f); bloom.scatter.Override(0.6f);
            glow.sharedProfile = prof;
            block = new MaterialPropertyBlock();
            var rnd = new System.Random(86);
            foreach (var f in FindObjectsByType<FlickerFollowerV01>(FindObjectsInactive.Include))
            {   // followers copy the old flicker; we drive the lights ourselves
                f.enabled = false; followers.Add(f);
            }
            foreach (var l in FindObjectsByType<Light>(FindObjectsInactive.Include))
            {
                if (l.type == LightType.Directional) continue;
                bool lamp = l.name.Contains("Flicker") || (l.transform.parent && l.transform.parent.name.StartsWith("DowntownLamp")) || l.name.StartsWith("VadimLampLight");
                if (!lamp) continue;
                var p = new Vector2(l.transform.position.x, l.transform.position.z);
                bool scary = rough.Contains(p);
                if (!scary) l.color = warm;
                lights.Add(new L { light = l, baseI = Mathf.Max(l.intensity, 0.01f) * (downtown.Contains(p) ? 1.35f : 1f), scary = scary, seed = (float)rnd.NextDouble() * 100f });
            }
            // windows: each Downtown glass material gets 3 shared warm lit variants (no property blocks -> SRP batching stays)
            var lit = new Dictionary<Material, Material[]>();
            Color[] tints = { new Color(1f, 0.62f, 0.26f) * 1.0f, new Color(1f, 0.7f, 0.34f) * 1.4f, new Color(1f, 0.78f, 0.45f) * 1.8f };
            foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude))
            {
                var p = new Vector2(r.bounds.center.x, r.bounds.center.z);
                if (!downtown.Contains(p)) continue;
                var day = r.sharedMaterials; Material[] night = null;
                bool on = rnd.NextDouble() < windowsLit; int v = rnd.Next(3);
                for (int i = 0; i < day.Length; i++)
                {
                    var m = day[i];
                    if (!m || !(m.name.Contains("Glass") || m.name.Contains("glass") || m.name.Contains("Window") || m.name.Contains("glazing"))) continue;
                    if (!on) continue;
                    if (!lit.TryGetValue(m, out var vars))
                    {
                        vars = new Material[3];
                        for (int k = 0; k < 3; k++)
                        {
                            vars[k] = new Material(m) { name = m.name + " (night lit " + k + ")" };
                            vars[k].EnableKeyword("_EMISSION"); vars[k].SetColor("_EmissionColor", tints[k]);
                            vars[k].globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                        }
                        lit.Add(m, vars);
                    }
                    night ??= (Material[])day.Clone();
                    night[i] = vars[v];
                }
                if (night != null) windows.Add((r, day, night));
            }
        }

        // the Rough lamp: steady, but now and then it slowly dies, hangs dark for a moment, stutters once and comes back
        static float Scary(float t, float seed)
        {
            float period = 9f + Mathf.Repeat(seed * 7.3f, 14f);
            float ph = Mathf.Repeat(t + seed * 3.1f, period);
            if (ph < 1.4f) return Mathf.Lerp(1f, 0.08f, Mathf.SmoothStep(0, 1, ph / 1.4f));          // slow fade out
            if (ph < 2.4f) return 0.06f;                                                              // dark
            if (ph < 2.55f) return 0.7f;                                                              // one stutter
            if (ph < 2.75f) return 0.1f;
            if (ph < 3.6f) return Mathf.Lerp(0.1f, 1f, Mathf.SmoothStep(0, 1, (ph - 2.75f) / 0.85f));
            return 0.95f + 0.05f * Mathf.PerlinNoise(t * 0.7f, seed);                                 // faint hum
        }

        void LateUpdate()
        {
            // map-wide distance haze (Hidden/VadimHaze pass): clear near, far things sink into a soft blue; dark at night
            float nightAmt = clock ? SkyRenderer22.NightAmount(clock.Hour) : 0f;
            Shader.SetGlobalVector("_VadimHaze", new Vector4(hazeStart, hazeHalf, hazeMax, 1f));
            Shader.SetGlobalColor("_VadimHazeColor", Color.Lerp(hazeDay, hazeNight, nightAmt));
            bool night = clock ? clock.IsNight : false;
            if (glow) glow.weight = Mathf.MoveTowards(glow.weight, night ? 1f : 0f, Time.deltaTime * 0.5f);
            float t = Time.time;
            if (!cam || !cam.isActiveAndEnabled) cam = Camera.main;
            if (night && cam)
            {
                var cp = cam.transform.position; float r2 = lightRadius * lightRadius;
                lights.Sort((a, b) => ((a.light ? a.light.transform.position : Vector3.positiveInfinity) - cp).sqrMagnitude
                    .CompareTo(((b.light ? b.light.transform.position : Vector3.positiveInfinity) - cp).sqrMagnitude));
                for (int i = 0; i < lights.Count; i++)
                {
                    var l = lights[i]; if (!l.light) continue;
                    bool on = i < maxLights && (l.light.transform.position - cp).sqrMagnitude < r2;
                    l.light.enabled = on;
                    if (on) l.light.intensity = l.scary ? l.baseI * Scary(t, l.seed) : l.baseI;
                }
            }
            foreach (var f in followers)
                if (f && f.target && f.source) f.target.intensity = f.targetOn * Mathf.Clamp01(f.source.intensity / Mathf.Max(0.001f, f.sourceOn));
            if (first || night != lastNight)
            {
                first = false; lastNight = night;
                foreach (var (r, day, nightMats) in windows)
                    if (r) r.sharedMaterials = night ? nightMats : day;
            }
        }
    }
}
