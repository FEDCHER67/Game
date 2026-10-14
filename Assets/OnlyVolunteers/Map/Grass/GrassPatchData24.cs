using System;
using UnityEngine;

namespace OnlyVolunteers.Map.Grass
{
    // Immutable, editor-baked world positions. Runtime never samples or edits the terrain.
    public sealed class GrassPatchData24 : ScriptableObject
    {
        [Serializable] public struct Chunk
        {
            public Vector3 centre;
            public uint start;
            public Vector3 extents;
            public uint count;
        }
        public TextAsset instances;
        public int instanceCount;
        public Bounds worldBounds;
        public Chunk[] chunks = Array.Empty<Chunk>();
        public string sourceScene, sourceCommit, placementSummary;
    }
}
