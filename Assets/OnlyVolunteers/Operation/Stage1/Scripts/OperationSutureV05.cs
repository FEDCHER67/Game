using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Round 3 (Fedya: "every operation ends with suturing the incision"): the approved OperationSutured_v05 meshes in
    /// the opening's INC_ABDOMEN frame (the same recipe as OperationOpeningV02: the meshes are authored in that frame).
    /// SUTURE_SKIN closes exactly the stencilled hole (the opening's ABDOMEN_MASK and the skin stencil stay on) with the
    /// patient's ORIGINAL skin material in its Buddy_Skin slot; SUTURE_STITCH_01..N appear in their 'order' as the seam
    /// progresses; SUTURE_BLOOD is the dried blood along the seam. A body that left the table dead and unsewn shows the plain
    /// patch with blood and no stitches (never a see-through cavity off the table).</summary>
    public sealed class OperationSutureV05 : MonoBehaviour
    {
        private readonly List<Material> owned = new();
        private readonly List<GameObject> stitches = new();
        private GameObject skin, blood;
        public int StitchCount => stitches.Count;
        public int StitchesShown { get; private set; }
        public bool Shown => gameObject.activeSelf;

        public static OperationSutureV05 Create(OperationTuning tuning, Transform zone, Material originalSkin)
        {
            if (tuning == null || tuning.suturedModel == null) return null;
            var root = new GameObject("Sutured v05"); root.transform.SetParent(zone, false);
            var result = root.AddComponent<OperationSutureV05>();
            var byOrder = new SortedDictionary<int, GameObject>();
            foreach (var source in tuning.suturedModel.GetComponentsInChildren<MeshFilter>(true))
            {
                string name = source.name;
                if (!name.StartsWith("SUTURE_") || name == "SUTURE_THREAD_ALL") continue; // per-stitch objects instead of the UV1 clip
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = source.sharedMesh;
                var renderer = go.AddComponent<MeshRenderer>();
                var originals = source.GetComponent<Renderer>().sharedMaterials;
                var materials = new Material[originals.Length];
                for (int i = 0; i < materials.Length; i++)
                {
                    string m = originals[i] != null ? originals[i].name : "";
                    if (m.StartsWith("Buddy_Skin") && originalSkin != null) { materials[i] = originalSkin; continue; }
                    Color color = m.Contains("Thread") ? new Color(0.12f, 0.15f, 0.34f) : m.Contains("DriedBlood") ? new Color(0.40f, 0.07f, 0.07f)
                        : m.Contains("Cut") ? new Color(0.50f, 0.12f, 0.12f) : m.Contains("Seam") ? new Color(0.90f, 0.52f, 0.47f) : new Color(0.88f, 0.56f, 0.40f);
                    materials[i] = new Material(OperationVisuals.Lit(m + " suture v05", color, m.Contains("Thread") ? 0.35f : 0.5f));
                    result.owned.Add(materials[i]);
                }
                renderer.sharedMaterials = materials;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                if (name == "SUTURE_SKIN") result.skin = go;
                else if (name == "SUTURE_BLOOD") result.blood = go;
                else if (name.StartsWith("SUTURE_STITCH_") && int.TryParse(name.Substring("SUTURE_STITCH_".Length), out int order)) byOrder[order] = go;
            }
            foreach (var pair in byOrder) result.stitches.Add(pair.Value);
            root.SetActive(false);
            return result;
        }

        /// <summary>Patch on/off and the first 'stitchCount' stitches (in order); blood along the seam with the patch.</summary>
        public void Show(bool patch, int stitchCount)
        {
            if (gameObject.activeSelf != patch) gameObject.SetActive(patch);
            if (!patch) return;
            stitchCount = Mathf.Clamp(stitchCount, 0, stitches.Count);
            if (stitchCount == StitchesShown && skin != null && skin.activeSelf) return;
            for (int i = 0; i < stitches.Count; i++) if (stitches[i] != null) stitches[i].SetActive(i < stitchCount);
            if (skin != null) skin.SetActive(true);
            if (blood != null) blood.SetActive(true);
            StitchesShown = stitchCount;
        }

        private void OnDestroy() { foreach (var m in owned) if (m != null) Destroy(m); }
    }
}
