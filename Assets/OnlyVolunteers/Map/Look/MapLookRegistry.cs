using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    [Serializable]
    public sealed class PrefabSlot
    {
        public string key;
        public GameObject prefab;
        public Vector3 scale = Vector3.one;
        public bool collider = true;
    }

    [Serializable]
    public sealed class MaterialSlot
    {
        public string key;
        public Material material;
        public Color fallback = new(0.6f, 0.6f, 0.6f);
        public float metresPerTile = 1f;
    }

    [Serializable]
    public sealed class LayerSlot
    {
        public string key;
        public TerrainLayer layer;
        public Color fallback = DefaultFallback;

        // The field default: a slot still at it was never coloured on purpose, so the look-bible colour wins.
        public static readonly Color DefaultFallback = new(0.5f, 0.6f, 0.4f);
    }

    // Where the look builder gets real art: prop/tree/material/terrain-layer keys ("prop/lamp_street", "tree/birch",
    // "mat/wall/panel", "layer/meadow") mapped to prefabs, materials and layers. Empty slots fall back to the family
    // default ("prop/_default"), then to generated placeholders, so the map builds today and upgrades as assets land.
    [CreateAssetMenu(menuName = "OnlyVolunteers/Map/Look Registry", fileName = "MapLookRegistry")]
    public sealed class MapLookRegistry : ScriptableObject
    {
        public string ArtRoot = "Assets/OnlyVolunteers/Art/Map";
        public List<PrefabSlot> Prefabs = new();
        public List<MaterialSlot> Materials = new();
        public List<LayerSlot> Layers = new();
        [Tooltip("Tinted variants per material key; further palette colours snap to the nearest existing tint. Each tint is a " +
                 "separate material (one more submesh per district cell), so keep it low for the draw-call budget.")]
        public int MaxTintsPerKey = 4;

        // Editor hook: turns a generated material into an asset (and may return an existing asset to reuse).
        public static Func<UnityEngine.Material, string, UnityEngine.Material> Persist;

        private readonly Dictionary<string, UnityEngine.Material> cache = new();
        private readonly Dictionary<string, List<Color>> tints = new();

        public void ResetCache()
        {
            cache.Clear();
            tints.Clear();
        }

        public GameObject Prefab(string key)
        {
            PrefabSlot slot = PrefabSlotFor(key);
            return slot != null ? slot.prefab : null;
        }

        // Exact key only, no family default: for buildings with a prop_key and for rocks, which must not turn into
        // whatever generic prefab fills "prop/_default".
        public PrefabSlot ExactPrefabSlot(string key)
        {
            foreach (PrefabSlot s in Prefabs)
                if (s != null && s.prefab != null && s.key == key)
                    return s;
            return null;
        }

        public PrefabSlot PrefabSlotFor(string key)
        {
            PrefabSlot exact = null, family = null;
            string fam = Family(key);
            foreach (PrefabSlot s in Prefabs)
            {
                if (s == null || s.prefab == null) continue;
                if (s.key == key) exact = s;
                else if (s.key == fam) family = s;
            }
            return exact ?? family;
        }

        public TerrainLayer Layer(string key)
        {
            foreach (LayerSlot s in Layers)
                if (s != null && s.key == key && s.layer != null)
                    return s.layer;
            return null;
        }

        public MaterialSlot MaterialSlotFor(string key)
        {
            MaterialSlot exact = null, family = null;
            string fam = Family(key);
            foreach (MaterialSlot s in Materials)
            {
                if (s == null) continue;
                if (s.key == key) exact = s;
                else if (s.key == fam && s.material != null) family = s;
            }
            if (exact != null && exact.material == null && family != null) return family;
            return exact ?? family;
        }

        // Slot key as written by MeshDraft: "mat/key" or "mat/key|#RRGGBB".
        public UnityEngine.Material Material(string slotKey)
        {
            int bar = slotKey.IndexOf('|');
            if (bar < 0)
            {
                MaterialSlot slot = MaterialSlotFor(slotKey);
                return Material(slotKey, slot != null && slot.key == slotKey ? slot.fallback : LookPalette.Default(slotKey), false);
            }
            return Material(slotKey.Substring(0, bar), LookConvert.Color(slotKey.Substring(bar + 1)), true);
        }

        public UnityEngine.Material Material(string key, Color tint) => Material(key, tint, true);

        // `tinted`: the colour comes from the plan palette (a "|#hex" slot). A real registry material keeps its own base
        // colour for untinted keys, and for tinted keys is scaled by tint / palette default, so a white-based texture
        // shows the palette colour and a key's default colour leaves the artist's material unchanged.
        public UnityEngine.Material Material(string key, Color tint, bool tinted)
        {
            tint = Snap(key, tint);
            tint.a = LookPalette.Alpha(key);
            string id = key + "|" + LookConvert.Hex(tint);
            if (cache.TryGetValue(id, out UnityEngine.Material cached) && cached != null) return cached;
            MaterialSlot slot = MaterialSlotFor(key);
            UnityEngine.Material mat;
            Color colour = tint;
            if (slot != null && slot.material != null)
            {
                mat = new UnityEngine.Material(slot.material);
                if (mat.HasProperty("_BaseMap") && mat.GetTexture("_BaseMap") != null)
                    mat.SetTextureScale("_BaseMap", Vector2.one / Mathf.Max(0.01f, slot.metresPerTile));
                Color own = mat.HasProperty("_BaseColor") ? mat.GetColor("_BaseColor") : mat.HasProperty("_Color") ? mat.color : Color.white;
                colour = tinted ? Relative(own, tint, LookPalette.Default(key)) : own;
                colour.a = own.a;
            }
            else
            {
                Shader lit = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
                mat = new UnityEngine.Material(lit);
                LookPalette.Configure(mat, key);
            }
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", colour);
            if (mat.HasProperty("_Color")) mat.color = colour;
            if (key.StartsWith("mat/neon") && mat.HasProperty("_EmissionColor"))
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", tint * 2.2f);
                // URP re-derives _EMISSION from these flags on import and validation; None would switch the glow off.
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            mat.enableInstancing = true;
            mat.name = Sanitize(id);
            if (Persist != null) mat = Persist(mat, mat.name) ?? mat;
            cache[id] = mat;
            return mat;
        }

        private static Color Relative(Color own, Color tint, Color reference)
        {
            // Up to 4x: a textured registry material's base colour is default / texture average, so it may exceed 1.
            static float Ch(float o, float t, float r) => Mathf.Clamp(o * t / Mathf.Max(0.05f, r), 0f, 4f);
            return new Color(Ch(own.r, tint.r, reference.r), Ch(own.g, tint.g, reference.g), Ch(own.b, tint.b, reference.b), own.a);
        }

        private Color Snap(string key, Color tint)
        {
            if (!tints.TryGetValue(key, out List<Color> list)) tints[key] = list = new List<Color>();
            foreach (Color c in list)
                if (Mathf.Abs(c.r - tint.r) + Mathf.Abs(c.g - tint.g) + Mathf.Abs(c.b - tint.b) < 0.025f)
                    return c;
            if (list.Count < Mathf.Max(1, MaxTintsPerKey))
            {
                list.Add(tint);
                return tint;
            }
            Color best = list[0];
            float bestD = float.MaxValue;
            foreach (Color c in list)
            {
                float d = Mathf.Abs(c.r - tint.r) + Mathf.Abs(c.g - tint.g) + Mathf.Abs(c.b - tint.b);
                if (d < bestD)
                {
                    bestD = d;
                    best = c;
                }
            }
            return best;
        }

        public static string Family(string key)
        {
            int slash = key.LastIndexOf('/');
            return slash < 0 ? key : key.Substring(0, slash) + "/_default";
        }

        public static string Sanitize(string id)
        {
            var chars = id.ToCharArray();
            for (int i = 0; i < chars.Length; i++)
                if (!char.IsLetterOrDigit(chars[i])) chars[i] = '_';
            return "Look_" + new string(chars).Trim('_');
        }

        // Every key the builder asks for, so the inspector can list empty slots for artists to fill.
        public static IEnumerable<string> KnownKeys()
        {
            foreach (string k in LookPalette.PropKeys) yield return "prop/" + k;
            foreach (string k in LookPalette.TreeKeys) yield return "tree/" + k;
            foreach (string k in LookPalette.MaterialKeys) yield return k;
        }
    }
}
