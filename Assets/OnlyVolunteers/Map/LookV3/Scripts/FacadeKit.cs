using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // One building-detail kit for the style v3 facade grammar: role id ("WIN_FRAME_M", "CORNICE_2M", ...) -> model.
    // Module contract (G12 README): metres, pivot on the wall plane at the bottom centre, Blender outward -Y (Unity -Z
    // after import), eight named role slots, colours as palette-cell UVs into PalettePath. A district theme swaps the whole
    // kit (the post-Soviet kit now; an American Downtown kit later) through FacadeKitSet without touching the grammar.
    [CreateAssetMenu(menuName = "OnlyVolunteers/Map/Facade Kit (style v3)", fileName = "FacadeKit")]
    public sealed class FacadeKit : ScriptableObject
    {
        public string KitId = "post_soviet_v01";
        [Tooltip("Palette image the module UVs point into (project-relative path; read at build time).")]
        public string PalettePath = "ArtSource/Props/STYLE_KIT_v2/_lib/Look_Palette_v2.png";
        public List<FacadeModule> Modules = new();

        public GameObject Model(string role)
        {
            foreach (FacadeModule m in Modules)
                if (m != null && m.Role == role && m.Model != null)
                    return m.Model;
            return null;
        }
    }

    [Serializable]
    public sealed class FacadeModule
    {
        public string Role;
        public GameObject Model;
    }
}
