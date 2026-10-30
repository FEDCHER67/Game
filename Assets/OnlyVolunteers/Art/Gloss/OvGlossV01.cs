namespace OnlyVolunteers.Art
{
    /// <summary>
    /// Global gloss reduction v01 (Fedya 30.10: "all models about 67 % less shiny"). One factor for the whole game:
    /// the perceptual smoothness of every model surface is its previous baseline x <see cref="Factor"/>.
    /// Where it is applied (each applies it once, from a known baseline, as an absolute value, so nothing compounds):
    ///  - .mat assets of the live scenes: Art/Gloss/gloss_manifest_v01.json (baseline + target per material), written by
    ///    GlossReductionV01 and re-asserted by its .mat import guard after any builder rewrites a listed material;
    ///  - FBX-embedded materials (crowd NPCs, mechanic, W86 props, cars...): GlossFbxPostprocessorV01 scales the importer's
    ///    smoothness on every import (the FBX is the baseline, so reimports never compound);
    ///  - runtime rules/copies: W86LookV01 rule table, W86VehiclesV01 gloss scale, OperationVisuals.Lit, van cargo fit-out,
    ///    NPC fallback prop, capture zip tie.
    /// Smoothness is the gloss control of URP Lit and of the project's V19/V3/T1 surface shaders; with a metallic/gloss map
    /// the scalar scales the map's A channel, so the map itself is never edited. Metallic, specular highlights, environment
    /// reflections, emission and transparency are left as they were. The player's sausage and hands are excluded (their own
    /// matte pass, SausageMatteV01); the eyes (eye white, pupil, shine dot) keep their wet highlight as on the player.
    /// Report: docs/reports/GLOSS_REDUCTION_2026-10-30_RU.md.
    /// </summary>
    public static class OvGlossV01
    {
        /// <summary>New smoothness = baseline x Factor (about 67 % less gloss).</summary>
        public const float Factor = 0.33f;

        /// <summary>Glass (material names with glass / window / windshield / lens) keeps a little more of its gloss so it still
        /// reads as glass: the Downtown towers' 0.95 at x0.33 (0.31) turned into satin blue cladding with no sky in it; x0.55
        /// (0.52) keeps a soft sky reflection and is still clearly less mirror-like (comparison in the report). Exception:
        /// the W86 cars' glass lives in one packed surface map under one scalar, so it takes Factor like their paint.</summary>
        public const float GlassFactor = 0.55f;

        public static float Scale(float baseline) => baseline * Factor;
    }
}
