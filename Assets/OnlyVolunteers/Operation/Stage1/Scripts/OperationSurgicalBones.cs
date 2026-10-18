using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Bone colliders of the in-body ribcage (G38 v03d contract, "Контракт Unity / Claude"): every UCX_* mesh of the
    /// ribcage model becomes a convex MeshCollider under its target (RIB_* / STERNUM_*), local identity, its renderer off,
    /// on the layer SurgicalBone with the tag SurgicalRib / SurgicalSternum. The ribcage root gets a kinematic Rigidbody, so
    /// these colliders never join (or shift the mass of) the patient's ragdoll bodies; the SurgicalBone layer collides with
    /// nothing, so they never touch the body, organs, the table or the player. They exist for queries only: future
    /// mallet/osteotome sweeps use Mask (SurgicalBone only). Intercostal gaps stay open. The source meshes must be readable
    /// (the integration tool sets that on the FBX copy) or a player build has no collision data for them.</summary>
    public static class OperationSurgicalBones
    {
        public const string LayerName = "SurgicalBone", RibTag = "SurgicalRib", SternumTag = "SurgicalSternum";

        public static int Layer => LayerMask.NameToLayer(LayerName);
        /// <summary>The query mask of bone tools: SurgicalBone only (0 when the layer is missing).</summary>
        public static int Mask { get { int l = Layer; return l >= 0 ? 1 << l : 0; } }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void IsolateLayer()
        {
            int bone = Layer;
            if (bone < 0) return;
            for (int i = 0; i < 32; i++) Physics.IgnoreLayerCollision(bone, i, true);
        }

        /// <summary>Turns the UCX_* children of an instanced ribcage model into bone colliders. Returns their count.</summary>
        public static int Setup(GameObject ribcage)
        {
            if (ribcage == null) return 0;
            int layer = Layer, count = 0;
            foreach (var filter in ribcage.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!filter.name.StartsWith("UCX_")) continue;
                var renderer = filter.GetComponent<MeshRenderer>();
                if (renderer != null) renderer.enabled = false;
                if (filter.sharedMesh == null) continue;
                var collider = filter.GetComponent<MeshCollider>();
                if (collider == null) collider = filter.gameObject.AddComponent<MeshCollider>();
                collider.convex = true;
                collider.sharedMesh = filter.sharedMesh;
                if (layer >= 0) filter.gameObject.layer = layer;
                bool sternum = filter.name.StartsWith("UCX_STERNUM");
                try { filter.gameObject.tag = sternum ? SternumTag : RibTag; } catch (UnityException) { }
                count++;
            }
            if (count > 0 && !ribcage.TryGetComponent(out Rigidbody body))
            {
                body = ribcage.AddComponent<Rigidbody>();
                body.isKinematic = true; body.useGravity = false; body.interpolation = RigidbodyInterpolation.None;
            }
            return count;
        }
    }
}
