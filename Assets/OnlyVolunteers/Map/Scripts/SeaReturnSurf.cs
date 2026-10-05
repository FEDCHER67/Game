using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The look map's surf: inside the beach polygon the sand runs under the sea's surface before the SeaReturnZone starts,
    // so a point there below the surface is not a dry place to put someone back on (SeaReturnZone.Dry). Only this
    // region: lake and river beds, and the dry hollows inland that lie below the sea level, stay dry places. Added next to
    // the zone by MapLookGameplay only; the flat grey-box has no surf (and its scene keeps its old serialized form).
    public sealed class SeaReturnSurf : MonoBehaviour
    {
        [Tooltip("Sea surface height.")]
        public float WaterLevel;

        [Tooltip("Surf region outline in world X/Z (the look's beach polygon, BEACH_SURF).")]
        public Vector2[] Polygon = new Vector2[0];

        // A point this far below the surface (feet or wheels in ankle-deep surf) still counts as dry.
        private const float WadeDepth = 0.1f;

        private static readonly List<SeaReturnSurf> Surfs = new();

        private void OnEnable() => Surfs.Add(this);
        private void OnDisable() => Surfs.Remove(this);

        public static bool Wet(Vector3 position)
        {
            foreach (SeaReturnSurf surf in Surfs)
                if (position.y < surf.WaterLevel - WadeDepth && surf.Inside(position.x, position.z))
                    return true;
            return false;
        }

        // Even-odd point in polygon.
        private bool Inside(float x, float z)
        {
            bool inside = false;
            for (int i = 0, j = Polygon.Length - 1; i < Polygon.Length; j = i++)
            {
                Vector2 a = Polygon[i], b = Polygon[j];
                if (a.y > z != b.y > z && x < (b.x - a.x) * (z - a.y) / (b.y - a.y) + a.x)
                    inside = !inside;
            }
            return inside;
        }
    }
}
