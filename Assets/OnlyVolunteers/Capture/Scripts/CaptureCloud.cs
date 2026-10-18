using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>The cartoon undress cloud «пуф» (D12, CD-02): a cluster of soft white puffs pops up over the body in
    /// CoverSeconds, fully hiding it, holds, then bursts outward and shrinks away; a few small puffs fly off. Total
    /// about 0.55 s. Covered tells the caller when the swap under it may happen.</summary>
    public sealed class CaptureCloud : MonoBehaviour
    {
        public const float CoverSeconds = 0.12f;
        public const float HoldUntil = 0.3f;
        public const float TotalSeconds = 0.56f;
        private static Material material;

        private Transform[] puffs;
        private Vector3[] home, size, drift;
        private float started;
        public bool Covered => Time.time - started >= CoverSeconds;
        public bool Done => Time.time - started >= TotalSeconds;

        /// <summary>A cloud over a lying body: centre, its long axis (head-feet) and length.</summary>
        public static CaptureCloud Spawn(Vector3 center, Vector3 axis, float length = 1.9f)
        {
            var go = new GameObject("[Capture] Undress cloud");
            go.transform.position = center;
            go.transform.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(axis.sqrMagnitude > 1e-4f ? axis : Vector3.forward, Vector3.up).normalized, Vector3.up);
            var cloud = go.AddComponent<CaptureCloud>();
            cloud.Build(length);
            CaptureSounds.Puff(center);
            return cloud;
        }

        private static Material Mat
        {
            get
            {
                if (material != null) return material;
                var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
                material = new Material(shader) { name = "Capture_Cloud (runtime)", hideFlags = HideFlags.DontSave };
                Color c = new Color(0.97f, 0.97f, 0.99f);
                material.color = c;
                if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", c);
                if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", 0.05f);
                if (material.HasProperty("_EmissionColor"))
                {
                    material.EnableKeyword("_EMISSION");
                    material.SetColor("_EmissionColor", new Color(0.32f, 0.32f, 0.34f));
                }
                return material;
            }
        }

        private void Build(float length)
        {
            started = Time.time;
            var rnd = new System.Random(System.Environment.TickCount);
            int along = 6;
            int count = along * 3 + 6;
            puffs = new Transform[count];
            home = new Vector3[count];
            size = new Vector3[count];
            drift = new Vector3[count];
            int k = 0;
            for (int i = 0; i < along; i++)
            {
                float z = Mathf.Lerp(-length * 0.5f, length * 0.5f, (i + 0.5f) / along);
                for (int j = 0; j < 3; j++)
                {
                    float x = (j - 1) * 0.28f + (float)(rnd.NextDouble() - 0.5) * 0.1f;
                    float y = 0.18f + (j == 1 ? 0.22f : 0f) + (float)rnd.NextDouble() * 0.08f;
                    float r = 0.42f + (float)rnd.NextDouble() * 0.18f;
                    Add(k++, new Vector3(x, y, z), r, rnd);
                }
            }
            for (int i = 0; i < 6; i++)
            {
                float z = Mathf.Lerp(-length * 0.45f, length * 0.45f, i / 5f);
                Add(k++, new Vector3((float)(rnd.NextDouble() - 0.5) * 0.3f, 0.55f + (float)rnd.NextDouble() * 0.12f, z), 0.34f + (float)rnd.NextDouble() * 0.1f, rnd);
            }
        }

        private void Add(int i, Vector3 at, float diameter, System.Random rnd)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Destroy(go.GetComponent<Collider>());
            go.name = "Puff";
            go.transform.SetParent(transform, false);
            go.transform.localPosition = at;
            go.transform.localScale = Vector3.zero;
            var r = go.GetComponent<Renderer>();
            r.sharedMaterial = Mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            puffs[i] = go.transform;
            home[i] = at;
            size[i] = new Vector3(diameter, diameter * (0.85f + (float)rnd.NextDouble() * 0.2f), diameter);
            drift[i] = new Vector3(at.x * 2.2f, 0.6f + (float)rnd.NextDouble() * 0.6f, at.z * 0.5f) + Random.insideUnitSphere * 0.3f;
        }

        private void Update()
        {
            float t = Time.time - started;
            for (int i = 0; i < puffs.Length; i++)
            {
                if (puffs[i] == null) continue;
                float s;
                Vector3 p = home[i];
                if (t < CoverSeconds)
                {
                    float u = t / CoverSeconds;
                    s = 1.18f * Mathf.Sin(u * Mathf.PI * 0.5f); // pop with overshoot
                }
                else if (t < HoldUntil)
                {
                    float u = (t - CoverSeconds) / (HoldUntil - CoverSeconds);
                    s = Mathf.Lerp(1.18f, 1f, u) + Mathf.Sin(t * 40f + i) * 0.03f;
                }
                else
                {
                    float u = Mathf.Clamp01((t - HoldUntil) / (TotalSeconds - HoldUntil));
                    s = (1f - u * u) * (1f + u * 0.3f);
                    p += drift[i] * u * 0.6f;
                }
                puffs[i].localScale = size[i] * Mathf.Max(0f, s);
                puffs[i].localPosition = p;
            }
            if (t >= TotalSeconds) Destroy(gameObject);
        }
    }
}
