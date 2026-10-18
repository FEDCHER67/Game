using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.W76
{
    // Map v76 per-district look (handoff v02 §6): fog, ambient, saturation/brightness by district, blended over 40–80 m
    // at the borders, plus the tunnel-exit glare ("тёмный тоннель -> яркий город": short post-exposure flash, eyes adapt
    // in 1–2 s). Cheap: one global Volume with ColorAdjustments, RenderSettings fog; no extra passes.
    public sealed class W76Atmosphere : MonoBehaviour
    {
        [Serializable]
        public sealed class Zone
        {
            public string Id;
            public Vector2[] Polygon = new Vector2[0];     // world X/Z
            public float Blend = 60f;                      // m, soft edge outside the polygon
            public Color FogColor = new(0.72f, 0.78f, 0.82f);
            public float FogStart = 60f, FogEnd = 400f;    // linear fog (v17: 60 -> 400 m)
            public float Exposure;                         // post exposure, EV
            public float Saturation;                       // -100..100
            public Color Filter = Color.white;
            public float Priority;                         // higher wins where zones overlap
        }

        public Zone Default = new() { Id = "default" };
        public List<Zone> Zones = new();
        public Volume Volume;
        [Header("Tunnel exit glare")]
        public Vector2[] TunnelAxis = new Vector2[0];      // world X/Z, portal to portal
        public float TunnelHalfWidth = 5f;
        public float GlareEv = 2.6f, GlareSeconds = 1.6f;
        public Transform Viewer;                           // defaults to Camera.main

        ColorAdjustments grade;
        bool inTunnel;
        float glareT = 99f;
        int exitDir;

        void OnEnable()
        {
            if (Volume && Volume.profile && !Volume.profile.TryGet(out grade))
                grade = Volume.profile.Add<ColorAdjustments>(true);
            if (grade)
            {
                grade.postExposure.overrideState = true;
                grade.saturation.overrideState = true;
                grade.colorFilter.overrideState = true;
            }
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
        }

        void LateUpdate()
        {
            Transform v = Viewer ? Viewer : (Camera.main ? Camera.main.transform : null);
            if (!v) return;
            Vector2 p = new(v.position.x, v.position.z);
            // weighted blend of zones
            float wSum = 1e-4f;
            Color fog = Default.FogColor * 1e-4f, filter = Default.Filter * 1e-4f;
            float fs = Default.FogStart * 1e-4f, fe = Default.FogEnd * 1e-4f, ev = 0f, sat = 0f;
            float best = -1f;
            foreach (Zone z in Zones)
            {
                float d = Inside(z.Polygon, p) ? 0f : Distance(z.Polygon, p);
                float w = Mathf.Clamp01(1f - d / Mathf.Max(1f, z.Blend));
                w = w * w * (3f - 2f * w);
                if (w <= 0f) continue;
                w *= 1f + z.Priority;
                best = Mathf.Max(best, w);
                wSum += w; fog += z.FogColor * w; filter += z.Filter * w;
                fs += z.FogStart * w; fe += z.FogEnd * w; ev += z.Exposure * w; sat += z.Saturation * w;
            }
            float rest = Mathf.Clamp01(1f - best);
            wSum += rest; fog += Default.FogColor * rest; filter += Default.Filter * rest;
            fs += Default.FogStart * rest; fe += Default.FogEnd * rest; ev += Default.Exposure * rest; sat += Default.Saturation * rest;
            RenderSettings.fogColor = fog / wSum;
            RenderSettings.fogStartDistance = fs / wSum;
            RenderSettings.fogEndDistance = fe / wSum;
            float glare = Glare(p, v.position.y);
            if (grade)
            {
                grade.postExposure.value = ev / wSum + glare;
                grade.saturation.value = sat / wSum;
                grade.colorFilter.value = filter / wSum;
            }
        }

        // Inside the tunnel the picture darkens a little; leaving it the exposure jumps by GlareEv and settles in GlareSeconds
        // (stronger towards Downtown: exiting at the last portal).
        float Glare(Vector2 p, float y)
        {
            if (TunnelAxis == null || TunnelAxis.Length < 2) return 0f;
            float d = Distance(TunnelAxis, p, out float along, out float total);
            bool now = d < TunnelHalfWidth && along > 2f && along < total - 2f;
            if (inTunnel && !now)
            {
                glareT = 0f;
                exitDir = along > total * .5f ? 1 : 0;
            }
            inTunnel = now;
            glareT += Time.deltaTime;
            if (inTunnel) return -0.6f;
            if (glareT > GlareSeconds) return 0f;
            float k = 1f - glareT / GlareSeconds;
            return GlareEv * (exitDir == 1 ? 1f : .75f) * k * k;
        }

        public static bool Inside(Vector2[] poly, Vector2 p)
        {
            bool c = false;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
                if ((poly[i].y > p.y) != (poly[j].y > p.y) &&
                    p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)
                    c = !c;
            return c;
        }

        public static float Distance(Vector2[] pl, Vector2 p) => Distance(pl, p, out _, out _);

        public static float Distance(Vector2[] pl, Vector2 p, out float along, out float total)
        {
            float best = float.MaxValue, acc = 0f;
            along = 0f;
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                Vector2 a = pl[i], b = pl[i + 1], ab = b - a;
                float L = ab.magnitude;
                float t = L > 1e-4f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / (L * L)) : 0f;
                float d = (a + ab * t - p).magnitude;
                if (d < best) { best = d; along = acc + t * L; }
                acc += L;
            }
            total = acc;
            return best;
        }
    }
}
