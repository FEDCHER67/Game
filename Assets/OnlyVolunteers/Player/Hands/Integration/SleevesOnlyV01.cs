using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// First-person sleeves (PLAYER HANDS v02): only the sleeves of the chosen top are drawn in first person, never its
    /// torso (with the viewmodel 25% lower and farther since 30.10 the chest and collar came into the bottom of the frame).
    /// Without touching the mesh (the player FBX is not readable and stays shared): the first-person top renderers'
    /// torso bone slots (hips, spine, neck, head) are re-pointed to one helper scaled to almost nothing at the middle of
    /// the shoulders, so every torso vertex collapses into that point behind and below the camera, while the sleeves,
    /// skinned to the shoulder / arm / forearm / hand bones and the stretch helpers, deform as before. Vertices blended
    /// between torso and arm (the shoulder cap) pull in toward the shoulders, out of view. Third person keeps the whole
    /// top. One helper per first-person body, set up once; nothing runs per frame.
    /// </summary>
    public static class SleevesOnlyV01
    {
        public const string HelperName = "FirstPerson_TorsoCollapse";

        /// <summary>Arm bones by name: the Mixamo shoulder/arm/forearm/hand chain (fingers included) and the
        /// StretchArmRigV01 helpers.</summary>
        public static bool IsArmBone(string name) =>
            !string.IsNullOrEmpty(name) && (name.Contains("Shoulder") || name.Contains("Arm") || name.Contains("Hand"));

        /// <summary>Re-points every non-arm bone of the renderer to the collapse helper (made under the rig root at
        /// <paramref name="shoulderMidWorld"/> on first use). Returns how many bone slots were re-pointed.</summary>
        public static int Apply(SkinnedMeshRenderer smr, Transform rigRoot, Vector3 shoulderMidWorld)
        {
            if (smr == null || rigRoot == null) return 0;
            Transform helper = rigRoot.Find(HelperName);
            if (helper == null)
            {
                helper = new GameObject(HelperName).transform;
                helper.SetParent(rigRoot, false);
                helper.position = shoulderMidWorld;
                helper.localRotation = Quaternion.identity;
                helper.localScale = Vector3.one * 1e-4f;
            }
            var bones = smr.bones;
            int n = 0;
            for (int i = 0; i < bones.Length; i++)
            {
                if (bones[i] == null || IsArmBone(bones[i].name) || bones[i] == helper) continue;
                bones[i] = helper;
                n++;
            }
            if (n > 0) smr.bones = bones;
            return n;
        }
    }
}
