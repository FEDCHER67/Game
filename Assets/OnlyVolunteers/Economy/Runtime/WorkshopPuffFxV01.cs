using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// The mechanic's cartoon "poof" on the van at the moment an upgrade is committed (MECHANIC_W86 v01): a compact cluster
    /// of soft cream balls that pop out, swell and shrink away in ~0.7 s, plus a few tiny sparks. Purely visual and local:
    /// no collider, no rigidbody, no light, nothing left behind (the object destroys itself), never any force or damage.
    /// The server spawns it on its own view and broadcasts the cue; clients spawn the same here. No packages, no particle
    /// system: a handful of shared-mesh renderers animated in Update.
    /// </summary>
    public sealed class WorkshopPuffFxV01 : MonoBehaviour
    {
        public const float Lifetime = 0.75f;
        private const int Balls = 8, Sparks = 5;

        private static Mesh sphere;
        private static Material fallback;

        private const float Drag = 4.5f;

        private Transform[] parts;
        private Vector3[] start, velocity;
        private float[] size, delay;
        private float age;

        /// <summary>A puff at 'at' (world) bulging along 'outward' (away from the van body). material: the puff material
        /// asset (Fx/MechanicPuff_v01.mat); null = a plain white fallback.</summary>
        public static WorkshopPuffFxV01 Spawn(Vector3 at, Vector3 outward, Material material, int seed = 0)
        {
            EnsureMesh();
            var go = new GameObject("MechanicPuff_v01 (fx)");
            go.transform.position = at;
            var fx = go.AddComponent<WorkshopPuffFxV01>();
            fx.Build(outward.sqrMagnitude > 1e-4f ? outward.normalized : Vector3.up, material != null ? material : fallback, seed != 0 ? seed : Time.frameCount);
            return fx;
        }

        private static void EnsureMesh()
        {
            if (sphere != null) return;
            GameObject probe = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere = probe.GetComponent<MeshFilter>().sharedMesh;
            fallback = new Material(probe.GetComponent<MeshRenderer>().sharedMaterial) { name = "MechanicPuff_fallback", color = new Color(0.97f, 0.95f, 0.9f) };
            if (Application.isPlaying) Object.Destroy(probe); else Object.DestroyImmediate(probe); // edit-mode previews too
        }

        private void Build(Vector3 outward, Material material, int seed)
        {
            var random = new System.Random(seed);
            float R() => (float)random.NextDouble();
            int n = Balls + Sparks;
            parts = new Transform[n];
            start = new Vector3[n];
            velocity = new Vector3[n];
            size = new float[n];
            delay = new float[n];
            Vector3 side = Vector3.Cross(outward, Vector3.up);
            if (side.sqrMagnitude < 1e-3f) side = Vector3.right;
            side.Normalize();
            Vector3 up = Vector3.Cross(side, outward).normalized;
            for (int i = 0; i < n; i++)
            {
                bool spark = i >= Balls;
                var p = new GameObject(spark ? "spark" : "ball");
                p.transform.SetParent(transform, false);
                p.AddComponent<MeshFilter>().sharedMesh = sphere;
                var mr = p.AddComponent<MeshRenderer>();
                mr.sharedMaterial = material;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
                float a = (i / (float)(spark ? Sparks : Balls) + R() * 0.15f) * Mathf.PI * 2f;
                Vector3 ring = side * Mathf.Cos(a) + up * Mathf.Sin(a);
                Vector3 dir = (ring * (spark ? 1f : 0.85f) + outward * (spark ? 0.6f : 0.45f + R() * 0.3f)).normalized;
                velocity[i] = dir * (spark ? 2.6f + R() * 0.8f : 1.1f + R() * 0.5f);
                size[i] = spark ? 0.05f + R() * 0.03f : 0.26f + R() * 0.16f;
                delay[i] = spark ? 0.02f : R() * 0.06f;
                start[i] = ring * 0.08f;
                p.transform.localPosition = start[i];
                p.transform.localScale = Vector3.zero;
                parts[i] = p.transform;
            }
        }

        private void Update()
        {
            age += Time.deltaTime;
            if (age >= Lifetime || parts == null) { Destroy(gameObject); return; }
            Pose(age);
        }

        /// <summary>The puff 'seconds' after it started (deterministic: also for edit-mode previews).</summary>
        public void Pose(float seconds)
        {
            if (parts == null) return;
            for (int i = 0; i < parts.Length; i++)
            {
                if (parts[i] == null) continue;
                float local = seconds - delay[i];
                float t = local / (Lifetime - delay[i]);
                if (t <= 0f) { parts[i].localScale = Vector3.zero; continue; }
                // soft drag: it billows out and stops, never flies off
                parts[i].localPosition = start[i] + velocity[i] * ((1f - Mathf.Exp(-Drag * local)) / Drag);
                // pop up fast (0..0.2), hold, shrink to nothing (cartoon puff)
                float s = t < 0.2f ? Mathf.SmoothStep(0f, 1.15f, t / 0.2f) : Mathf.Lerp(1.15f, 0f, Mathf.SmoothStep(0f, 1f, (t - 0.2f) / 0.8f));
                parts[i].localScale = Vector3.one * (size[i] * Mathf.Max(0f, s));
            }
        }
    }
}
