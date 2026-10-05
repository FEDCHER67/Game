using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    [Serializable]
    public sealed class BridgeDeck
    {
        public string Id;
        public Vector2 A, B;
        public float HeightA, HeightB, HalfWidth;
        // Deck centreline in plan (x, z pairs) following the road from A to B; empty means the straight chord A-B.
        public float[] Path = new float[0];

        public float[] Centreline() => Path != null && Path.Length >= 4 ? Path : new[] { A.x, A.y, B.x, B.y };
    }

    [Serializable]
    public sealed class WaterZone
    {
        public string Id, Kind;
        public float Level, HalfWidth;
        public float[] Pts = new float[0];
    }

    // Ground height of the look map for spawning and snapping (terrain plus bridge decks) and the water test.
    // The play scene (MapLookGameplay) places the grey-box gameplay with Height(), raised to the colliders there.
    public sealed class MapHeightSampler : MonoBehaviour
    {
        public Terrain Terrain;
        public List<BridgeDeck> Decks = new();
        public List<WaterZone> Water = new();

        public float Height(float x, float z)
        {
            float h = 0f;
            if (Terrain != null) h = Terrain.SampleHeight(new Vector3(x, 0f, z)) + Terrain.transform.position.y;
            if (DeckHeight(Decks, x, z, out float deck)) h = Mathf.Max(h, deck);
            return h;
        }

        public Vector3 Snap(Vector3 p, float lift = 0f) => new(p.x, Height(p.x, p.z) + lift, p.z);

        public bool InWater(float x, float z, out float level)
        {
            float h = Height(x, z);
            foreach (WaterZone w in Water)
            {
                if (h >= w.Level) continue;
                bool inside = w.Kind == "lake" || w.Kind == "sea"
                    ? LookGeom.Inside(w.Pts, x, z)
                    : LookGeom.DistToPolyline(w.Pts, x, z, false, out _, out _) < w.HalfWidth;
                if (!inside) continue;
                level = w.Level;
                return true;
            }
            level = 0f;
            return false;
        }

        // Deck surface height where (x, z) lies on a bridge deck (within HalfWidth of its centreline, between its ends).
        public static bool DeckHeight(List<BridgeDeck> decks, float x, float z, out float h) => DeckAt(decks, x, z, out h, out _);

        // As DeckHeight, plus the deck's direction there (unit plan x, z of its centreline segment nearest to the point).
        public static bool DeckAt(List<BridgeDeck> decks, float x, float z, out float h, out Vector2 dir)
        {
            h = 0f;
            dir = Vector2.zero;
            if (decks == null) return false;
            foreach (BridgeDeck d in decks)
            {
                float[] path = d.Centreline();
                int n = path.Length / 2;
                float total = 0f, bestDist = float.MaxValue, bestS = 0f, bestRaw = 0f;
                int bestSeg = -1;
                for (int i = 0; i + 1 < n; i++)
                {
                    float ax = path[2 * i], az = path[2 * i + 1], bx = path[2 * i + 2], bz = path[2 * i + 3];
                    float dx = bx - ax, dz = bz - az, len2 = dx * dx + dz * dz, len = Mathf.Sqrt(len2);
                    float raw = len2 > 1e-8f ? ((x - ax) * dx + (z - az) * dz) / len2 : 0f, t = Mathf.Clamp01(raw);
                    float px = ax + dx * t - x, pz = az + dz * t - z, dist = Mathf.Sqrt(px * px + pz * pz);
                    if (dist < bestDist)
                    {
                        bestDist = dist;
                        bestSeg = i;
                        bestRaw = raw;
                        bestS = total + len * t;
                    }
                    total += len;
                }
                if (bestSeg < 0 || total < 0.1f || bestDist > d.HalfWidth) continue;
                if (bestSeg == 0 && bestRaw < 0f || bestSeg == n - 2 && bestRaw > 1f) continue;
                h = Mathf.Lerp(d.HeightA, d.HeightB, bestS / total);
                dir = new Vector2(path[2 * bestSeg + 2] - path[2 * bestSeg], path[2 * bestSeg + 3] - path[2 * bestSeg + 1]).normalized;
                return true;
            }
            return false;
        }
    }
}
