using System;
using UnityEngine;

namespace OnlyVolunteers.Audio
{
    public enum WaterKind : byte { Sea, River, Canal, Lake, Pond, Bog, Pool, Puddle }

    // Surface triangles use the same plan coordinates and tessellation as WaterBuilder.
    public sealed class WaterData : ScriptableObject
    {
        [Serializable]
        public sealed class Area
        {
            public string Id;
            public WaterKind Kind;
            public float SurfaceY;
            public float[] Triangles = Array.Empty<float>(); // x,z pairs, three vertices per triangle
        }

        [Serializable]
        public struct Emitter
        {
            public Vector3 Position;
            public string SoundId;
        }

        public string PlanRevision;
        public Area[] Areas = Array.Empty<Area>();
        public Emitter[] Emitters = Array.Empty<Emitter>();
        // The map terrain, roads and other static ground are on Default. Never raycast actors/vehicles.
        public LayerMask GroundLayers = 1;
    }
}
