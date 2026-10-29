using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Round 4 (Fedya): a patient who got off the table is still undressed. The crowd template he is re-created from
    /// (CaptureSave.Respawn) wears the Outfit mesh; here the Outfit goes off, his Body renderer takes the patient model's
    /// body mesh and the patient trunks ("Shorts") are added, both skinned to his own bones by name (the same
    /// Buddy_Rig_Mixamo65 skeleton). His skin and face materials stay his (CaptureTableBridge.Match keeps every slot whose
    /// name he has). If any bone is missing nothing changes (he stays dressed rather than broken).</summary>
    public static class CaptureUndress
    {
        public static bool Apply(GameObject npc, GameObject patientModel)
        {
            if (npc == null || patientModel == null) return false;
            SkinnedMeshRenderer body = null, shorts = null, sourceBody = null, sourceShorts = null;
            var bodyLods = new List<SkinnedMeshRenderer>();
            foreach (var smr in npc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.name == "Body") body = smr;
                else if (smr.name == "Shorts") shorts = smr;
                else if (smr.name.StartsWith("Body_LOD")) bodyLods.Add(smr);
            }
            foreach (var smr in patientModel.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.name == "Body") sourceBody = smr;
                else if (smr.name == "Shorts") sourceShorts = smr;
            }
            if (body == null || sourceBody == null || sourceBody.sharedMesh == null) return false;
            var bones = new Dictionary<string, Transform>();
            foreach (var t in npc.GetComponentsInChildren<Transform>(true)) if (!bones.ContainsKey(t.name)) bones[t.name] = t;
            if (!Map(sourceBody, bones, out var bodyBones, out var bodyRoot)) return false;
            Transform[] shortsBones = null; Transform shortsRoot = null;
            bool addShorts = shorts == null && sourceShorts != null && sourceShorts.sharedMesh != null &&
                Map(sourceShorts, bones, out shortsBones, out shortsRoot);

            var own = body.sharedMaterials;
            body.sharedMesh = sourceBody.sharedMesh;
            body.bones = bodyBones;
            body.rootBone = bodyRoot;
            body.localBounds = sourceBody.localBounds;
            body.sharedMaterials = CaptureTableBridge.Match(sourceBody.sharedMaterials, own);
            // TASK-000900: the types' crowd LODs Body_LOD1 / _LOD2 are cut under the outfit too: they show the same full body.
            foreach (var level in bodyLods)
            {
                level.sharedMesh = body.sharedMesh;
                level.bones = bodyBones;
                level.rootBone = bodyRoot;
                level.localBounds = body.localBounds;
                level.sharedMaterials = body.sharedMaterials;
            }
            if (addShorts)
            {
                var go = new GameObject("Shorts");
                go.transform.SetParent(body.transform.parent, false);
                go.transform.localPosition = body.transform.localPosition;
                go.transform.localRotation = body.transform.localRotation;
                go.transform.localScale = body.transform.localScale;
                go.layer = body.gameObject.layer;
                var renderer = go.AddComponent<SkinnedMeshRenderer>();
                renderer.sharedMesh = sourceShorts.sharedMesh;
                renderer.bones = shortsBones;
                renderer.rootBone = shortsRoot;
                renderer.localBounds = sourceShorts.localBounds;
                renderer.sharedMaterials = sourceShorts.sharedMaterials;
                renderer.updateWhenOffscreen = body.updateWhenOffscreen;
                // ... and in every level of the type's LODGroup, so it is culled with the body.
                var group = body.GetComponentInParent<LODGroup>();
                if (group != null)
                {
                    var lods = group.GetLODs();
                    for (int i = 0; i < lods.Length; i++)
                    {
                        var list = new List<Renderer>(lods[i].renderers) { renderer };
                        lods[i].renderers = list.ToArray();
                    }
                    group.SetLODs(lods);
                }
            }
            foreach (var smr in npc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.name == "Outfit" || smr.name.StartsWith("Outfit")) smr.enabled = false;
            // K10 (Fedya 29.10): he stays the table patient: nothing of the type's props either (hats, backpacks, things in
            // hand: Props_Head / Props_Spine2 / Props_*Hand and their LODs), and no held-props drop when he runs.
            foreach (var r in npc.GetComponentsInChildren<Renderer>(true))
                if (r.name.StartsWith("Props_")) r.enabled = false;
            foreach (var held in npc.GetComponentsInChildren<OnlyVolunteers.Characters.NpcHeldProps>(true))
            {
                if (Application.isPlaying) Object.Destroy(held); else Object.DestroyImmediate(held);
            }
            return true;
        }

        private static bool Map(SkinnedMeshRenderer source, Dictionary<string, Transform> bones, out Transform[] mapped, out Transform root)
        {
            var from = source.bones;
            mapped = new Transform[from.Length];
            root = null;
            for (int i = 0; i < from.Length; i++)
            {
                if (from[i] == null) continue;
                if (!bones.TryGetValue(from[i].name, out mapped[i]))
                {
                    Debug.LogWarning("[CAPTURE] undress: bone " + from[i].name + " missing on the field NPC; he stays dressed");
                    return false;
                }
            }
            if (source.rootBone != null && !bones.TryGetValue(source.rootBone.name, out root)) return false;
            return true;
        }
    }
}
