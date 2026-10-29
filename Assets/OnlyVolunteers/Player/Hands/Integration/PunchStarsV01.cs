using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// Cartoon impact stars of a landed punch (Fedya 30.10): a pop of flat yellow/white stars flying out of the hit point,
    /// spinning, facing the camera, gone in about half a second. Presentation only, one burst per punch cue (PlayerArmsV01
    /// schedules it at the fist's contact time; a miss never bursts). Pooled: a fixed set of star objects made once, one
    /// shared star mesh and one shared material (Resources/PunchStarV01.mat, URP Unlit), colours by MaterialPropertyBlock;
    /// no allocations per burst; the component sleeps (disabled) when nothing flies.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PunchStarsV01 : MonoBehaviour
    {
        public const string MaterialResource = "PunchStarV01";
        private const int Pool = 32;
        private static PunchStarsV01 instance;
        private static Mesh starMesh;
        private static Material material;
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        private static readonly Color[] Colours =
        {
            new Color(1f, 0.86f, 0.18f), new Color(1f, 0.95f, 0.55f), new Color(1f, 1f, 1f), new Color(1f, 0.68f, 0.12f),
        };

        private struct Star
        {
            public Transform T;
            public Renderer R;
            public Vector3 Velocity;
            public float Born, Life, Size, Spin, Angle;
            public bool Alive;
        }

        private struct Pending { public Vector3 At; public float Strength, When; public int Count; public float Size, Life; }

        private readonly Star[] stars = new Star[Pool];
        private readonly List<Pending> pending = new List<Pending>(4);
        private MaterialPropertyBlock block;
        private int next;

        /// <summary>The camera the stars face (PlayerArmsV01 sets the local player's view; else Camera.main).</summary>
        public static Camera View;

        private static Camera Facing => View != null && View.isActiveAndEnabled ? View : Camera.main;

        /// <summary>Stars currently flying (tests, the review notes).</summary>
        public static int Flying { get; private set; }
        /// <summary>Bursts started this session (tests: one per landed cue).</summary>
        public static int Bursts { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { instance = null; View = null; Flying = 0; Bursts = 0; }

        /// <summary>A burst at 'at' after 'delay' seconds of game time; strength 0..1 scales how many and how big.</summary>
        public static void Schedule(Vector3 at, float strength, float delay, int count, float size, float life)
        {
            var s = Ensure();
            if (s == null) return;
            s.pending.Add(new Pending { At = at, Strength = Mathf.Clamp01(strength), When = Time.time + Mathf.Max(0f, delay), Count = count, Size = size, Life = life });
            s.enabled = true;
        }

        private static PunchStarsV01 Ensure()
        {
            if (instance != null) return instance;
            if (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null) return null;
            // No DontSave flag: such objects outlive Play mode in the editor (frozen stars left in the scene).
            var go = new GameObject("[Hands] Punch stars");
            DontDestroyOnLoad(go);
            instance = go.AddComponent<PunchStarsV01>();
            return instance;
        }

        private void Awake()
        {
            block = new MaterialPropertyBlock();
            if (starMesh == null) starMesh = BuildStar(0.5f, 0.22f);
            if (material == null)
            {
                material = Resources.Load<Material>(MaterialResource);
                if (material == null)
                {
                    Shader sh = Shader.Find("Universal Render Pipeline/Unlit");
                    material = sh != null ? new Material(sh) { name = "PunchStar (code)", hideFlags = HideFlags.DontSave } : null;
                }
            }
            for (int i = 0; i < Pool; i++)
            {
                var go = new GameObject("Star");
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = starMesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = material;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off;
                go.SetActive(false);
                stars[i] = new Star { T = go.transform, R = r };
            }
        }

        private void OnEnable() => RenderPipelineManager.beginCameraRendering += FaceCamera;
        private void OnDisable() => RenderPipelineManager.beginCameraRendering -= FaceCamera;

        // Every camera sees the stars face-on (the player's view, a friend's, a review camera), spun by their own angle.
        private void FaceCamera(ScriptableRenderContext context, Camera cam)
        {
            if (cam == null) return;
            Quaternion face = cam.transform.rotation;
            for (int i = 0; i < Pool; i++)
                if (stars[i].Alive) stars[i].T.rotation = face * Quaternion.AngleAxis(stars[i].Angle, Vector3.forward);
        }

        private void Update()
        {
            float now = Time.time;
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                if (now < pending[i].When) continue;
                Burst(pending[i]);
                pending.RemoveAt(i);
            }
            int alive = 0;
            float dt = Time.deltaTime;
            for (int i = 0; i < Pool; i++)
            {
                ref Star s = ref stars[i];
                if (!s.Alive) continue;
                float age = (now - s.Born) / s.Life;
                if (age >= 1f)
                {
                    s.Alive = false;
                    s.T.gameObject.SetActive(false);
                    continue;
                }
                alive++;
                s.Velocity *= Mathf.Exp(-dt * 4f);
                s.Velocity += Vector3.down * (1.6f * dt);
                s.T.position += s.Velocity * dt;
                s.Angle += s.Spin * dt;
                // pop in (overshoot), hold, shrink away
                float pop = age < 0.15f ? Mathf.Lerp(0.2f, 1.25f, age / 0.15f) : age < 0.3f ? Mathf.Lerp(1.25f, 1f, (age - 0.15f) / 0.15f) : 1f;
                float fade = age > 0.6f ? 1f - (age - 0.6f) / 0.4f : 1f;
                s.T.localScale = Vector3.one * (s.Size * pop * fade);
            }
            Flying = alive;
            if (alive == 0 && pending.Count == 0) enabled = false;
        }

        private void Burst(in Pending p)
        {
            Bursts++;
            Camera cam = Facing;
            Vector3 right = cam != null ? cam.transform.right : Vector3.right;
            Vector3 up = cam != null ? cam.transform.up : Vector3.up;
            Vector3 back = cam != null ? -cam.transform.forward : Vector3.back;
            int count = Mathf.Clamp(Mathf.RoundToInt(p.Count * Mathf.Lerp(0.35f, 1f, p.Strength)), 1, 12);
            float size = p.Size * Mathf.Lerp(0.7f, 1f, p.Strength);
            float now = Time.time;
            // a big white flash star in the middle, the rest flying out in a ring (toward the viewer a little)
            for (int k = 0; k <= count; k++)
            {
                ref Star s = ref stars[next];
                next = (next + 1) % Pool;
                bool flash = k == 0;
                float a = (k / (float)count) * Mathf.PI * 2f + Random.Range(-0.3f, 0.3f);
                Vector3 dir = right * Mathf.Cos(a) + up * (Mathf.Sin(a) * 0.8f + 0.25f) + back * 0.35f;
                s.Velocity = flash ? Vector3.zero : dir.normalized * Random.Range(0.9f, 1.6f);
                s.Born = now;
                s.Life = flash ? p.Life * 0.35f : p.Life * Random.Range(0.8f, 1.1f);
                s.Size = flash ? size * 2.2f : size * Random.Range(0.8f, 1.2f);
                s.Spin = flash ? 0f : Random.Range(-540f, 540f);
                s.Angle = Random.Range(0f, 72f);
                s.Alive = true;
                s.T.position = p.At + back * 0.05f;
                s.T.localScale = Vector3.one * (s.Size * 0.2f);
                s.T.gameObject.SetActive(true);
                block.SetColor(BaseColor, flash ? Color.white : Colours[k % Colours.Length]);
                s.R.SetPropertyBlock(block);
            }
        }

        /// <summary>A flat five-point star in the XY plane, both sides (triangles wound both ways), radius outer / inner.</summary>
        private static Mesh BuildStar(float outer, float inner)
        {
            var v = new Vector3[11];
            v[0] = Vector3.zero;
            for (int i = 0; i < 10; i++)
            {
                float a = Mathf.PI * 0.5f + i * Mathf.PI / 5f;
                float r = i % 2 == 0 ? outer : inner;
                v[i + 1] = new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, 0f);
            }
            var t = new int[60];
            for (int i = 0; i < 10; i++)
            {
                int a = i + 1, b = (i + 1) % 10 + 1;
                t[i * 6 + 0] = 0; t[i * 6 + 1] = a; t[i * 6 + 2] = b;
                t[i * 6 + 3] = 0; t[i * 6 + 4] = b; t[i * 6 + 5] = a;
            }
            var m = new Mesh { name = "PunchStar", vertices = v, triangles = t, hideFlags = HideFlags.DontSave };
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }
    }
}
