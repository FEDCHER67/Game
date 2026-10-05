using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look
{
    // Colours and surface settings from the map look bible (R01 v12): matte faceted surfaces, one hero hue per district,
    // full chroma only on signage, neon and road paint. Used whenever the registry has no material for a key.
    public static class LookPalette
    {
        private static readonly Dictionary<string, string> Defaults = new()
        {
            ["mat/glass"] = "#3E4C55", ["mat/glass_lit"] = "#3A4650", ["mat/door"] = "#5A4636", ["mat/door/metal"] = "#4A5458",
            ["mat/metal"] = "#5B6266", ["mat/iron"] = "#232426", ["mat/concrete"] = "#A8A69E", ["mat/plinth"] = "#6B6660",
            ["mat/brick"] = "#B46A4F", ["mat/gold"] = "#C9A24A", ["mat/dome"] = "#2F6F8F", ["mat/stone"] = "#CFC6B4",
            ["mat/stucco"] = "#E6DFD0", ["mat/rock"] = "#7D7A70", ["mat/wood"] = "#8C6B4A", ["mat/wood/dark"] = "#6B5241",
            ["mat/sign"] = "#F2EDE0", ["mat/neon/pink"] = "#FF5C8A", ["mat/neon/yellow"] = "#FFD166", ["mat/neon/cyan"] = "#4DD9F0",
            ["mat/neon/blue"] = "#3D7BFF", ["mat/red"] = "#D23B32", ["mat/white"] = "#F2F0EA", ["mat/orange"] = "#E8732A",
            ["mat/rubber"] = "#B5553F", ["mat/rust"] = "#8C5A3C", ["mat/canvas/red"] = "#C9503F", ["mat/canvas/blue"] = "#4C7FB0",
            ["mat/road/asphalt"] = "#4F5254", ["mat/road/asphalt_worn"] = "#5A5C5E", ["mat/road/asphalt_elite"] = "#5E6064",
            ["mat/road/dirt"] = "#8F8064", ["mat/road/boardwalk"] = "#9C7A55", ["mat/road/junction"] = "#55585A",
            ["mat/marking"] = "#ECE8DC", ["mat/marking/yellow"] = "#E3B341", ["mat/curb"] = "#B8B4AA", ["mat/curb/white"] = "#E9E7E0",
            ["mat/sidewalk/old_town"] = "#BEB8A8", ["mat/sidewalk/residential"] = "#9A9A92", ["mat/sidewalk/elite"] = "#CFC9BC",
            ["mat/sidewalk/industrial"] = "#8C8C86", ["mat/sidewalk/transition"] = "#A8A290", ["mat/sidewalk/_default"] = "#A9A59A",
            ["mat/ground/paving"] = "#BEB8A8", ["mat/ground/concrete"] = "#9A9A92", ["mat/ground/asphalt"] = "#56595B",
            ["mat/ground/rubber"] = "#AE6A55", ["mat/ground/cobble"] = "#8B8378", ["mat/ground/gravel"] = "#9A907A",
            ["mat/parking/line"] = "#E8E4D6", ["mat/rail"] = "#6A6058", ["mat/rail/steel"] = "#77706A", ["mat/ballast"] = "#7D776E",
            ["mat/sleeper"] = "#5B4A3C", ["mat/bridge"] = "#A7A49B", ["mat/fence/picket"] = "#A99773", ["mat/fence/wooden"] = "#8C7356",
            ["mat/fence/chainlink"] = "#7E8486", ["mat/hedge"] = "#4F7A3E", ["mat/hedge/thuja"] = "#3F6633", ["mat/elite/pier"] = "#D9D4C8",
            ["mat/elite/plinth"] = "#CFC9BC", ["mat/water/lake"] = "#4F9BB5", ["mat/water/river"] = "#5A9DAF", ["mat/water/canal"] = "#5F8E8C",
            ["mat/water/sea"] = "#3F86A3", ["mat/water/foam"] = "#F2F6F4", ["mat/decal/sludge"] = "#777F49", ["mat/decal/fish"] = "#B0B29A",
            ["mat/pipe"] = "#9B5C36", ["mat/trunk"] = "#6B5241", ["mat/trunk/birch"] = "#E8E4DA", ["mat/trunk/palm"] = "#8A7356",
            ["mat/leaves/pine"] = "#3F6633", ["mat/leaves/spruce"] = "#35593A", ["mat/leaves/birch"] = "#7FA05A",
            ["mat/leaves/oak"] = "#4F7A3E", ["mat/leaves/linden"] = "#5E8A48", ["mat/leaves/poplar"] = "#5E8A48",
            ["mat/leaves/fruit"] = "#6F9A4C", ["mat/leaves/willow"] = "#7F9F5A", ["mat/leaves/palm"] = "#5E8A48",
            ["mat/leaves/cypress"] = "#3F5F3A", ["mat/leaves/bush"] = "#557F44", ["mat/leaves/_default"] = "#5E8A48",
            ["mat/wall/_default"] = "#C8C3B5", ["mat/trim"] = "#F4EEE2", ["mat/roof/_default"] = "#6E7478",
        };

        public static readonly string[] PropKeys =
        {
            "lamp_street", "lamp_iron", "lamp_bollard", "power_pole", "bench", "bin", "garbage_container", "bus_stop",
            "bus_stop_sign", "sign_crossing", "sign_no_swimming", "swings", "slide", "sandbox", "carpet_rack", "pipe_support",
            "kiosk", "atm", "ad_pole", "rock", "camera", "_default",
        };

        public static readonly string[] TreeKeys = { "pine", "spruce", "birch", "oak", "linden", "poplar", "fruit", "willow", "palm", "cypress", "bush" };

        public static readonly string[] MaterialKeys =
        {
            "mat/wall/panel", "mat/wall/oldtown", "mat/wall/rural_wood", "mat/wall/shed", "mat/wall/civic", "mat/wall/commercial",
            "mat/wall/neon", "mat/wall/villa", "mat/wall/industrial", "mat/trim", "mat/plinth", "mat/glass", "mat/glass_lit",
            "mat/door", "mat/roof/flat", "mat/roof/sheet", "mat/roof/tile", "mat/roof/corrugated", "mat/brick", "mat/concrete",
            "mat/metal", "mat/road/asphalt", "mat/road/asphalt_worn", "mat/road/dirt", "mat/marking", "mat/curb",
            "mat/sidewalk/old_town", "mat/sidewalk/residential", "mat/sidewalk/elite", "mat/ground/paving", "mat/ground/concrete",
            "mat/ground/cobble", "mat/water/lake", "mat/water/sea", "mat/fence/picket", "mat/fence/wooden", "mat/hedge",
            "mat/elite/pier", "mat/iron", "mat/rock",
        };

        // District hero colours (rule 3), used for sidewalks, lamps and kerbs.
        public static readonly Dictionary<string, string> DistrictHue = new()
        {
            ["forest"] = "#4F7A3E", ["village"] = "#C9A24A", ["transition"] = "#EDE6D2", ["residential"] = "#5B86A8",
            ["old_town"] = "#B46A4F", ["elite"] = "#F4F1EA", ["industrial"] = "#8C3B2E", ["fields"] = "#C9B98B", ["valley"] = "#C94C6A",
        };

        public static Color Default(string key)
        {
            if (Defaults.TryGetValue(key, out string hex)) return LookConvert.Color(hex);
            string fam = MapLookRegistry.Family(key);
            if (Defaults.TryGetValue(fam, out hex)) return LookConvert.Color(hex);
            return new Color(0.6f, 0.6f, 0.6f);
        }

        public static string DefaultHex(string key) => LookConvert.Hex(Default(key));

        // Matte by default; glass, water and metal get their own response; water and decals are transparent.
        public static void Configure(Material mat, string key)
        {
            float smooth = 0.08f, metal = 0f;
            if (key.StartsWith("mat/glass")) smooth = 0.82f;
            else if (key.StartsWith("mat/water")) smooth = 0.9f;
            else if (key == "mat/metal" || key == "mat/iron" || key == "mat/rail/steel" || key == "mat/gold") { smooth = 0.45f; metal = 0.35f; }
            else if (key.StartsWith("mat/marking") || key.StartsWith("mat/neon")) smooth = 0.2f;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smooth);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metal);
            if (mat.HasProperty("_SpecularHighlights") && smooth < 0.1f) mat.SetFloat("_SpecularHighlights", 0f);
            if (mat.HasProperty("_EnvironmentReflections") && smooth < 0.1f) mat.SetFloat("_EnvironmentReflections", 0f);
            if (smooth < 0.1f)
            {
                mat.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                mat.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            }
            if (key == "mat/glass_lit" && mat.HasProperty("_EmissionColor"))
            {
                // Lit windows: emission is wired but black until night lighting is designed.
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", Color.black);
            }
            if (key.StartsWith("mat/water") || key.StartsWith("mat/decal")) SetTransparent(mat);
            if (key.StartsWith("mat/leaves") || key.StartsWith("mat/fence") || key == "mat/iron") SetDoubleSided(mat);
        }

        public static void SetTransparent(Material mat)
        {
            if (mat.HasProperty("_Surface")) mat.SetFloat("_Surface", 1f);
            if (mat.HasProperty("_Blend")) mat.SetFloat("_Blend", 0f);
            if (mat.HasProperty("_SrcBlend")) mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            if (mat.HasProperty("_DstBlend")) mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            if (mat.HasProperty("_ZWrite")) mat.SetFloat("_ZWrite", 0f);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            mat.renderQueue = (int)RenderQueue.Transparent;
        }

        public static void SetDoubleSided(Material mat)
        {
            if (mat.HasProperty("_Cull")) mat.SetFloat("_Cull", (float)CullMode.Off);
        }

        // Alpha of the transparent keys (applied by the builder through the tint).
        public static float Alpha(string key) => key switch
        {
            "mat/water/sea" => 0.86f,
            "mat/water/lake" => 0.8f,
            "mat/water/river" => 0.78f,
            "mat/water/canal" => 0.82f,
            "mat/water/foam" => 0.7f,
            "mat/decal/sludge" => 0.65f,
            _ => 1f,
        };
    }
}
