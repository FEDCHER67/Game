using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Merges generated meshes per district x 160 m cell into one static mesh with a submesh per material slot
    // (UInt32 indices when large), so buildings, roads and fences cost a few draw calls per cell. A piece goes to the
    // cell of its centre, so a building is never split. Collider-only combiners emit MeshColliders without renderers.
    public sealed class DistrictCombiner
    {
        public readonly float Cell;
        private readonly Dictionary<(string district, int cx, int cz), MeshDraft> buckets = new();

        public DistrictCombiner(float cell = 160f)
        {
            Cell = cell;
        }

        public int Count => buckets.Count;

        public void Add(string district, Matrix4x4 localToWorld, MeshDraft draft, Vector3 worldCentre)
        {
            if (draft == null || draft.IsEmpty) return;
            var key = (string.IsNullOrEmpty(district) ? "common" : district, Mathf.FloorToInt(worldCentre.x / Cell), Mathf.FloorToInt(worldCentre.z / Cell));
            if (!buckets.TryGetValue(key, out MeshDraft bucket)) buckets[key] = bucket = new MeshDraft();
            bucket.Append(draft, localToWorld);
        }

        public void Add(LookPiece piece) => Add(piece.District, Matrix4x4.identity, piece.Draft, piece.Centre);

        // Emits one object per bucket under parent/District_<id>; returns (objects, triangles, submeshes).
        public (int objects, int triangles, int batches) Emit(Transform parent, string prefix, MapLookRegistry registry, LookAssetStore store,
            bool render, bool collide)
        {
            int objects = 0, tris = 0, batches = 0;
            var groups = new Dictionary<string, Transform>();
            var keys = new List<(string district, int cx, int cz)>(buckets.Keys);
            keys.Sort((a, b) => string.CompareOrdinal($"{a.district}_{a.cx:D4}_{a.cz:D4}", $"{b.district}_{b.cx:D4}_{b.cz:D4}"));
            foreach (var key in keys)
            {
                MeshDraft draft = buckets[key];
                if (draft.IsEmpty) continue;
                if (!groups.TryGetValue(key.district, out Transform group))
                {
                    group = new GameObject($"District_{key.district}").transform;
                    group.SetParent(parent, false);
                    groups[key.district] = group;
                }
                var go = new GameObject($"{prefix}_{key.district}_{key.cx}_{key.cz}");
                go.transform.SetParent(group, false);
                Mesh mesh = store.AddMesh(draft.ToMesh(go.name));
                if (render)
                {
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    go.AddComponent<MeshRenderer>().sharedMaterials = LookAssetStore.Materials(draft, registry);
                    batches += draft.Slots.Count;
                }
                if (collide) go.AddComponent<MeshCollider>().sharedMesh = mesh;
                MarkStatic(go, render);
                objects++;
                tris += draft.TriangleCount;
            }
            return (objects, tris, batches);
        }

        public static void MarkStatic(GameObject go, bool render = true)
        {
            // Already merged per cell, so no static batching (it would only duplicate the vertex data).
            StaticEditorFlags flags = StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic;
            if (render) flags |= StaticEditorFlags.OccluderStatic;
            GameObjectUtility.SetStaticEditorFlags(go, flags);
        }
    }
}
