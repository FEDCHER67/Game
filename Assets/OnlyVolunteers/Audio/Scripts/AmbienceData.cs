using System;
using UnityEngine;

namespace OnlyVolunteers.Audio
{
    // Geometry and sound choices baked from the full map plan. Runtime never opens the plan JSON.
    public sealed class AmbienceData : ScriptableObject
    {
        [Serializable]
        public sealed class District
        {
            public string Id;
            public Vector2[] Polygon = Array.Empty<Vector2>();
        }

        [Serializable]
        public sealed class Coastline
        {
            public Vector2[] Points = Array.Empty<Vector2>();
        }

        [Serializable]
        public sealed class Mapping
        {
            public string DistrictId;
            public string AmbienceId;
            [Range(0f, 1f)] public float Volume;

            public Mapping() { }

            public Mapping(string districtId, string ambienceId, float volume)
            {
                DistrictId = districtId;
                AmbienceId = ambienceId;
                Volume = volume;
            }
        }

        public string PlanRevision;
        public District[] Districts = Array.Empty<District>();
        public Coastline[] Coastlines = Array.Empty<Coastline>();
        public Vector3[] Fountains = Array.Empty<Vector3>();
        public Vector3[] Offices = Array.Empty<Vector3>();

        // This table is preserved when the baker updates an existing asset. An unknown district is silent.
        public Mapping[] Mappings =
        {
            new Mapping("forest", "amb_birds", 0.5f),
            new Mapping("village", "amb_birds", 0.4f),
            new Mapping("hamlet", "amb_birds", 0.4f),
            new Mapping("old_town", "amb_city", 0.45f),
            new Mapping("downtown", "amb_city", 0.45f),
            new Mapping("residential", "amb_city", 0.35f),
            new Mapping("alley", "amb_city", 0.35f),
            new Mapping("rough", "amb_city", 0.35f),
            new Mapping("elite", "amb_birds", 0.3f),
            new Mapping("industrial", "amb_city", 0.3f),
            new Mapping("port", "amb_city", 0.3f),
            new Mapping("transition", "amb_birds", 0.35f),
            new Mapping("crossing", "amb_birds", 0.35f),
            new Mapping("fields", "amb_birds", 0.45f),
            new Mapping("valley", "amb_birds", 0.45f),
            new Mapping("beach", "amb_sea", 0.5f),
            new Mapping("beach_parking", "amb_sea", 0.5f),
        };

        public Mapping MappingFor(string districtId)
        {
            if (string.IsNullOrEmpty(districtId) || Mappings == null) return null;
            for (int i = 0; i < Mappings.Length; i++)
            {
                Mapping mapping = Mappings[i];
                if (mapping != null && string.Equals(mapping.DistrictId, districtId, StringComparison.OrdinalIgnoreCase))
                    return mapping;
            }
            return null;
        }
    }
}
