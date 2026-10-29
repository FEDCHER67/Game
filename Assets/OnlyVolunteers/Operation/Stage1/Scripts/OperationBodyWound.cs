using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>K10 (Fedya 29.10): the belly of a patient who left the table, on the field NPC that carries him on (a crowd
    /// template wearing the patient body and trunks, CaptureUndress): the same approved opening as on the table
    /// (OperationOpeningV02: skin stencil hole, cavity, wound lip) and the same seam / patch (OperationSutureV05), no new art.
    /// They hang on a copy of the patient model's INC_ABDOMEN frame under his own mixamorig bone, so they run, fall and lie
    /// with him (runner, then corpse). Opened and not sewn: the gaping wound (cavity on). Sewn, partly sewn or patched: the
    /// seam or the patch over it, as the table shows a body that leaves it. The table-only query collider is removed.</summary>
    public sealed class OperationBodyWound : MonoBehaviour
    {
        public const string FrameName = "INC_ABDOMEN (patient wound)";
        /// <summary>His Body materials before the opening stencilled the skin slots (the table re-admission keeps his skin
        /// colour from these: CaptureTableBridge.KeepAppearance).</summary>
        public Material[] OriginalBodyMaterials { get; private set; }
        public bool Open { get; private set; }

        /// <summary>Builds the wound for this state on 'body' (its Body renderer must already wear the patient body). Returns
        /// null when the belly was never opened, or the patient model / tuning / bones are missing (he then shows no wound).</summary>
        public static OperationBodyWound Attach(GameObject body, OperationTuning tuning, OperationState state, GameObject patientModel)
        {
            if (body == null || tuning == null || state == null || !state.zoneOpened || patientModel == null) return null;
            if (!tuning.anatomicalLayout || tuning.abdomenModel == null) return null;
            var anchors = patientModel.GetComponentInChildren<OperationPatientAnchors>(true);
            Transform source = anchors != null ? anchors.Abdomen : null;
            if (source == null || source.parent == null) return null;
            Transform bone = null;
            foreach (var t in body.GetComponentsInChildren<Transform>(true))
            {
                if (t == null) continue;
                if (t.name == FrameName) { Kill(t.gameObject); continue; } // rebuilt (a second Attach)
                if (bone == null && t.name == source.parent.name) bone = t;
            }
            if (bone == null) return null;
            SkinnedMeshRenderer skin = null;
            foreach (var smr in body.GetComponentsInChildren<SkinnedMeshRenderer>(true)) if (smr.name == "Body") { skin = smr; break; }
            if (skin == null) return null;

            var frame = new GameObject(FrameName).transform;
            frame.SetParent(bone, false);
            frame.localPosition = source.localPosition; frame.localRotation = source.localRotation; frame.localScale = source.localScale;
            var wound = frame.gameObject.AddComponent<OperationBodyWound>();
            wound.OriginalBodyMaterials = skin.sharedMaterials;
            var zone = new GameObject("SharedAbdomen (field)").transform;
            zone.SetParent(frame, false);
            zone.localScale = Vector3.one / Mathf.Max(0.0001f, frame.lossyScale.x); // metres, as on the table

            var opening = OperationOpeningV02.Create(tuning, zone, body.transform);
            if (opening.Mask != null) Kill(opening.Mask.gameObject); // the table's click query: no kinematic body on a ragdoll bone
            wound.Open = state.CavityOpen;
            if (!wound.Open)
            {
                opening.SetCavityVisible(false);
                var suture = OperationSutureV05.Create(tuning, zone, opening.OriginalSkin);
                if (suture != null)
                {
                    suture.Show(true, state.sutured ? suture.StitchCount : 0);
                    suture.SetClosure(1f, true);
                }
            }
            return wound;
        }

        private static void Kill(GameObject go)
        {
            if (Application.isPlaying) Destroy(go); else DestroyImmediate(go);
        }
    }
}
