using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Player-safe meshes for the query-only MeshColliders (strap bands/buckles, the v02 opening mask).
    /// A runtime MeshCollider needs CPU-readable mesh data in a player build; the table and abdomen FBX meshes are not
    /// readable, so their colliders came out empty in Fedya's build ("CollisionMeshData couldn't be created because the
    /// mesh has been marked as non-accessible") while every Editor run worked. The readable copies are baked once in the
    /// Editor (OperationQueryMeshBaker) and listed in OperationTuning.queryMeshes; they carry the same triangles.</summary>
    public static class OperationQueryMeshes
    {
        public const string Suffix = "_query";

        /// <summary>The mesh a query collider may use for <paramref name="source"/>: itself when readable, else its baked
        /// readable copy (same name + "_query", same vertex count); null when neither exists.</summary>
        public static Mesh Resolve(Mesh source, OperationTuning tuning)
        {
            if (source == null) return null;
            if (source.isReadable) return source;
            if (tuning != null && tuning.queryMeshes != null)
                foreach (var copy in tuning.queryMeshes)
                    if (copy != null && copy.isReadable && copy.vertexCount == source.vertexCount &&
                        (copy.name == source.name + Suffix || copy.name.EndsWith("__" + source.name + Suffix))) return copy;
            Debug.LogError("[OPS] no readable query mesh for '" + source.name + "': its MeshCollider would be empty in a player build. " +
                           "Run OnlyVolunteers/Operation/Bake Player-Safe Query Meshes.");
            return null;
        }

        /// <summary>True when the collider would work in a player build too (a readable mesh, so PhysX can cook it).</summary>
        public static bool PlayerSafe(MeshCollider collider) => collider != null && collider.sharedMesh != null && collider.sharedMesh.isReadable;
    }
}
