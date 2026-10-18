using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Query-only, triangle-accurate targets for each visible strap; never fills the space inside a belt.</summary>
    public sealed class OperationStrapTargets : MonoBehaviour
    {
        private readonly List<MeshCollider>[] targets = new List<MeshCollider>[5];

        public static OperationStrapTargets Install(NetworkOperationTable table)
        {
            var result = table.GetComponent<OperationStrapTargets>();
            if (result == null) result = table.gameObject.AddComponent<OperationStrapTargets>();
            if (result.targets[0] != null) return result;
            for (int i = 0; i < 5; i++)
            {
                result.targets[i] = new List<MeshCollider>();
                if (!OperationStraps.Active(table.Tuning, i)) continue; // round 3: no torso strap, no target for it
                result.Build(table.StrapTransform(i), i, table.Tuning);
                if (i == 4) result.Build(table.Slot("STRAP_TORSO_SecondHalf"), i, table.Tuning);
            }
            return result;
        }

        private void Build(Transform root, int index, OperationTuning tuning)
        {
            if (root == null) return;
            foreach (var old in root.GetComponentsInChildren<OperationTargetTag>(true))
                if (old.kind == TargetKind.Strap)
                    foreach (var collider in old.GetComponents<Collider>()) collider.enabled = false;
            foreach (var mesh in root.GetComponentsInChildren<MeshFilter>(true))
            {
                var renderer = mesh.GetComponent<Renderer>();
                if (mesh.sharedMesh == null || renderer == null || !renderer.enabled) continue;
                // Player-safe copy: the FBX strap meshes are not readable, so a collider on them is empty in a build.
                var query = OperationQueryMeshes.Resolve(mesh.sharedMesh, tuning);
                if (query == null) continue;
                var go = new GameObject("Hit_Strap_" + index + "_mesh");
                // Ignore Raycast: out of default-mask rays (pickup, aim); the table view casts every layer. PlayerPushPolicy
                // keeps it out of the player's motor (an open strap swings over the edge, review G35 M3).
                go.layer = 2;
                go.transform.SetParent(mesh.transform, false);
                // A separate kinematic query body supports the concave mesh while the gurney itself remains dynamic.
                var body = go.AddComponent<Rigidbody>(); body.isKinematic = true; body.useGravity = false;
                var hit = go.AddComponent<MeshCollider>(); hit.sharedMesh = query; hit.convex = false;
                hit.excludeLayers = ~0; // no physical contacts; raycasts still use the exact visible triangles
                var tag = go.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.Strap; tag.index = index;
                tag.highlight = new[] { renderer };
                targets[index].Add(hit);
            }
        }

        public IReadOnlyList<MeshCollider> Targets(int index) => index >= 0 && index < targets.Length && targets[index] != null ? targets[index] : (IReadOnlyList<MeshCollider>)new MeshCollider[0];

        public bool Contains(int index, Vector3 world)
        {
            if (index < 0 || index >= targets.Length || targets[index] == null) return false;
            foreach (var collider in targets[index])
                foreach (var axis in new[] { Vector3.up, Vector3.right, Vector3.forward, Vector3.down, Vector3.left, Vector3.back })
                    if (collider != null && collider.Raycast(new Ray(world + axis * 0.012f, -axis), out var hit, 0.024f)) return true;
            return false;
        }
    }
}
