using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Out-of-bounds sea beyond the beach (Fedya, 2026-10-04): whoever gets into it is put back on land
    // by their SeaReturnTracker. The area is a set of map-plan triangles (x, z), so no trigger colliders are needed.
    public sealed class SeaReturnZone : MonoBehaviour
    {
        [Tooltip("Triangle corners in world X/Z, three per triangle.")]
        public Vector2[] Triangles = new Vector2[0];

        private static readonly List<SeaReturnZone> Zones = new();

        private void OnEnable() => Zones.Add(this);
        private void OnDisable() => Zones.Remove(this);

        public static bool InSea(Vector3 position)
        {
            var p = new Vector2(position.x, position.z);
            foreach (SeaReturnZone zone in Zones)
                for (int i = 0; i + 2 < zone.Triangles.Length; i += 3)
                    if (InTriangle(p, zone.Triangles[i], zone.Triangles[i + 1], zone.Triangles[i + 2]))
                        return true;
            return false;
        }

        /// <summary>A place to put someone back on: outside every zone and not in the surf under the sea's surface (the
        /// look map's SeaReturnSurf regions; the flat grey-box has none, so there every point outside the zone is dry).
        /// </summary>
        public static bool Dry(Vector3 position) => !InSea(position) && !SeaReturnSurf.Wet(position);

        private static bool InTriangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d1 = Cross(p, a, b), d2 = Cross(p, b, c), d3 = Cross(p, c, a);
            bool hasNeg = d1 < 0f || d2 < 0f || d3 < 0f;
            bool hasPos = d1 > 0f || d2 > 0f || d3 > 0f;
            return !(hasNeg && hasPos);
        }

        private static float Cross(Vector2 p, Vector2 a, Vector2 b) => (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y);
    }
}
