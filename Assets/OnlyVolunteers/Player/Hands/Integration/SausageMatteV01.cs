using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// Fedya 30.10: the player's sausage (the first-person arms, his shadow body and how friends see him) is fully matte:
    /// every skin and clothing material is swapped for a runtime copy with smoothness 0, metallic 0, specular highlights
    /// off and environment reflections off (so neither the reflection probes nor W86LookV01's live sky cube shine on it).
    /// The eyes keep their shine. One copy per source material for the whole session (shared by every body), named as
    /// the source so PlayerSausageAvatarV01's tints (MaterialPropertyBlock by material name) still find their slots.
    /// Resources/PlayerMatteVariantV01.mat carries the same keyword set, so a player build compiles that shader variant.
    /// </summary>
    public static class SausageMatteV01
    {
        public const string VariantResource = "PlayerMatteVariantV01";
        private static readonly string[] KeepShine = { "Eye_White", "Pupil", "Eye_Shine", "Glasses" };
        private static readonly Dictionary<Material, Material> copies = new Dictionary<Material, Material>();
        private static readonly int Smoothness = Shader.PropertyToID("_Smoothness"), Metallic = Shader.PropertyToID("_Metallic"),
            Specular = Shader.PropertyToID("_SpecularHighlights"), Environment = Shader.PropertyToID("_EnvironmentReflections"),
            Glossy = Shader.PropertyToID("_GlossyReflections");

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => copies.Clear();

        /// <summary>Swaps every renderer's materials below root for their matte copies (once per body, at its creation).</summary>
        public static int Apply(GameObject root)
        {
            if (root == null) return 0;
            int swapped = 0;
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    Material m = Matte(mats[i]);
                    if (m == mats[i]) continue;
                    mats[i] = m;
                    changed = true;
                    swapped++;
                }
                if (changed) r.sharedMaterials = mats;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }
            return swapped;
        }

        /// <summary>The matte copy of a material (the material itself for the eyes, non-Lit shaders and null).</summary>
        public static Material Matte(Material source)
        {
            if (source == null || !source.HasProperty(Smoothness)) return source;
            foreach (string keep in KeepShine) if (source.name.Contains(keep)) return source;
            if (copies.TryGetValue(source, out Material copy) && copy != null) return copy;
            copy = new Material(source) { name = source.name, hideFlags = HideFlags.DontSave };
            copy.SetFloat(Smoothness, 0f);
            if (copy.HasProperty(Metallic)) copy.SetFloat(Metallic, 0f);
            if (copy.HasProperty(Specular)) copy.SetFloat(Specular, 0f);
            if (copy.HasProperty(Environment)) copy.SetFloat(Environment, 0f);
            if (copy.HasProperty(Glossy)) copy.SetFloat(Glossy, 0f);
            copy.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            copy.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            copies[source] = copy;
            return copy;
        }

        /// <summary>True when the material is fully matte (tests, the review notes).</summary>
        public static bool IsMatte(Material m) =>
            m != null && (!m.HasProperty(Smoothness) || m.GetFloat(Smoothness) <= 0f) &&
            m.IsKeywordEnabled("_SPECULARHIGHLIGHTS_OFF") && m.IsKeywordEnabled("_ENVIRONMENTREFLECTIONS_OFF");
    }
}
