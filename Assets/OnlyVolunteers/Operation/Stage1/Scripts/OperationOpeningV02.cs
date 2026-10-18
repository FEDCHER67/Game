using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Approved v02 meshes and the URP skin stencil, attached in the INC_ABDOMEN frame.</summary>
    public sealed class OperationOpeningV02 : MonoBehaviour
    {
        private readonly List<Material> owned = new();
        private MeshCollider mask;
        public bool Contains(Ray ray) => mask != null && mask.sharedMesh != null && mask.Raycast(ray, out _, 8f);
        public MeshCollider Mask => mask;
        /// <summary>The patient's original (un-stencilled) skin material: the sutured patch wears it (round 3).</summary>
        public Material OriginalSkin { get; private set; }
        private readonly List<GameObject> cavity = new();
        /// <summary>Round 3: everything of the opening but ABDOMEN_MASK (the stencil writer stays on under the sutured patch).</summary>
        public void SetCavityVisible(bool visible) { foreach (var go in cavity) if (go != null && go.activeSelf != visible) go.SetActive(visible); }

        public static OperationOpeningV02 Create(OperationTuning tuning, Transform parent, Transform patient)
        {
            var root = new GameObject("Approved opening v02"); root.transform.SetParent(parent, false);
            var result = root.AddComponent<OperationOpeningV02>();
            Material skin = null;
            foreach (var renderer in patient.GetComponentsInChildren<SkinnedMeshRenderer>())
                if (renderer.name == "Body")
                {
                    var materials = renderer.sharedMaterials;
                    for (int i = 0; i < materials.Length; i++)
                    {
                        if (materials[i] == null || !materials[i].name.StartsWith("Buddy_Skin")) continue;
                        skin = materials[i]; result.OriginalSkin = skin;
                        var masked = new Material(skin) { name = skin.name + " stencil v02", shader = tuning.skinStencilShader };
                        result.owned.Add(masked); materials[i] = masked;
                    }
                    renderer.sharedMaterials = materials;
                }
            foreach (var source in tuning.abdomenModel.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!source.name.StartsWith("ABDOMEN_")) continue; // interactive kidney cords use the authoritative geometry
                var go = new GameObject(source.name); go.transform.SetParent(root.transform, false);
                if (source.name != "ABDOMEN_MASK") result.cavity.Add(go);
                go.AddComponent<MeshFilter>().sharedMesh = source.sharedMesh;
                var renderer = go.AddComponent<MeshRenderer>();
                var originals = source.GetComponent<Renderer>().sharedMaterials;
                var materials = new Material[originals.Length];
                for (int i = 0; i < materials.Length; i++)
                {
                    string name = originals[i] != null ? originals[i].name : "";
                    if (name.StartsWith("Buddy_Skin") && skin != null) { materials[i] = skin; continue; }
                    if (source.name == "ABDOMEN_MASK")
                    { materials[i] = new Material(tuning.maskStencilShader) { name = "Abdomen stencil writer v02", renderQueue = 1999 }; }
                    else
                    {
                        Color color = name.Contains("Artery") ? new Color(0.8f, 0.16f, 0.20f) : name.Contains("Vein") ? new Color(0.52f, 0.36f, 0.66f)
                            : name.Contains("Bowel") ? new Color(0.9f, 0.56f, 0.52f) : Color.white;
                        materials[i] = new Material(OperationVisuals.Lit(name + " v02", color, 0.7f));
                        if (name.Contains("Interior") && tuning.abdomenGradient != null) materials[i].SetTexture("_BaseMap", tuning.abdomenGradient);
                    }
                    result.owned.Add(materials[i]);
                }
                renderer.sharedMaterials = materials;
                if (source.name == "ABDOMEN_MASK")
                {
                    // The query collider lives on its own child: AddComponent<MeshCollider> next to a MeshFilter would first
                    // cook the FBX's non-readable mesh (an error in a player build) before the readable copy is assigned.
                    var query = new GameObject("ABDOMEN_MASK query"); query.transform.SetParent(go.transform, false); query.layer = 2;
                    var body = query.AddComponent<Rigidbody>(); body.isKinematic = true; body.useGravity = false;
                    result.mask = query.AddComponent<MeshCollider>(); result.mask.sharedMesh = OperationQueryMeshes.Resolve(source.sharedMesh, tuning); result.mask.excludeLayers = ~0;
                }
            }
            return result;
        }
        private void OnDestroy() { foreach (var material in owned) if (material != null) Destroy(material); }
    }
}
