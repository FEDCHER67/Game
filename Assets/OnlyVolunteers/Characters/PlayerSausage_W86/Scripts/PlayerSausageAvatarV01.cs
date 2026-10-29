using System;
using System.Collections.Generic;
using OnlyVolunteers.Session;
using UnityEngine;

namespace OnlyVolunteers.Characters.Player
{
    // ---- PLAYER_SAUSAGE_W86_v01_manifest.json (JsonUtility shape; unknown fields are ignored) ----
    [Serializable] public sealed class SausageOptionV01
    {
        public string id = "", name_ru = "", mesh = "", mesh_under_hat = "";
        public List<string> lods = new List<string>(), lods_under_hat = new List<string>(), hides_body_regions = new List<string>();
        public bool hair_under_hat;
    }
    [Serializable] public sealed class SausageAspectV01 { public string name_ru = "", @default = ""; public List<SausageOptionV01> options = new List<SausageOptionV01>(); }
    [Serializable] public sealed class SausageAspectsV01 { public SausageAspectV01 hair, beard, top, bottom, head; }
    [Serializable] public sealed class SausageSkinV01 { public string id = "", name_ru = "", skin = "", nose = "", inner = "", rim = ""; }
    [Serializable] public sealed class SausageSkinMaterialsV01 { public string skin = "Buddy_Skin", nose = "Buddy_Skin_Nose", inner = "Buddy_Skin_Inner", rim = "Buddy_Eye_Rim"; }
    [Serializable] public sealed class SausageSkinTonesV01 { public string @default = ""; public SausageSkinMaterialsV01 materials = new SausageSkinMaterialsV01(); public List<SausageSkinV01> options = new List<SausageSkinV01>(); }
    [Serializable] public sealed class SausageSwatchV01 { public string id = "", name_ru = "", main = "", trim = "", accent = ""; }
    [Serializable] public sealed class SausageSwatchesV01 { public List<SausageSwatchV01> options = new List<SausageSwatchV01>(); }
    [Serializable] public sealed class SausageBaseV01 { public List<string> meshes = new List<string>(), always_on = new List<string>(); }
    [Serializable] public sealed class SausageManifestV01
    {
        public string asset = "", revision = "";
        public SausageBaseV01 @base = new SausageBaseV01();
        public SausageAspectsV01 aspects = new SausageAspectsV01();
        public SausageSkinTonesV01 skin_tones = new SausageSkinTonesV01();
        public SausageSwatchesV01 clothing_swatches = new SausageSwatchesV01();

        public const string ResourceName = "PLAYER_SAUSAGE_W86_v01_manifest";

        public static SausageManifestV01 Parse(string json)
        {
            try
            {
                var m = JsonUtility.FromJson<SausageManifestV01>(json);
                return m != null && m.aspects != null && m.aspects.top != null && m.aspects.top.options.Count > 0 ? m : null;
            }
            catch (Exception e) { Debug.LogWarning("[OV Avatar] player sausage manifest unreadable: " + e.Message); return null; }
        }

        public SausageAspectV01 Aspect(AppearanceSlot slot)
        {
            switch (slot)
            {
                case AppearanceSlot.Hair: return aspects.hair;
                case AppearanceSlot.FacialHair: return aspects.beard;
                case AppearanceSlot.Top: return aspects.top;
                case AppearanceSlot.Bottom: return aspects.bottom;
                case AppearanceSlot.Accessory: return aspects.head;
                default: return null;
            }
        }

        public SausageOptionV01 Option(AppearanceSlot slot, string id)
        {
            var a = Aspect(slot);
            if (a == null || a.options == null) return null;
            foreach (var o in a.options) if (o != null && o.id == id) return o;
            return null;
        }

        /// <summary>Is this a part the model really has? Colour slots: the manifest's palette (skin, swatches) or any hair colour.</summary>
        public bool Has(AppearanceSlot slot, string id)
        {
            switch (slot)
            {
                case AppearanceSlot.Skin: return skin_tones.options.Exists(o => o.id == id);
                case AppearanceSlot.TopColour:
                case AppearanceSlot.BottomColour: return clothing_swatches.options.Exists(o => o.id == id);
                case AppearanceSlot.HairColour: return AppearanceCatalogV01.IsValid(slot, id);
                default: return Option(slot, id) != null;
            }
        }
    }

    /// <summary>
    /// The player's customisable Sausage Buddy (PLAYER_SAUSAGE_W86 v01, Fedya 29.10) on its prefab: applies a
    /// <see cref="PlayerAppearance"/> by the parts manifest — the chosen option mesh of each aspect on (all three LODs), the
    /// others off; the Body_* regions the chosen top and bottom cover off; the hair's under-the-hat variant while a cap,
    /// beanie or bandana is worn; skin tone on Buddy_Skin / _Nose / _Inner / Buddy_Eye_Rim, the clothing swatch (main, trim,
    /// accent) on PLAYER_Top_* / PLAYER_Bottom_*, the hair colour on PLAYER_Hair / _Hair_Part / _Stubble — all as
    /// MaterialPropertyBlock tints (no material instances). Presentation only: the look itself belongs to the player's
    /// profile (AppearanceProfileV01) and the network wire; this never changes size, speed or anything else.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PlayerSausageAvatarV01 : MonoBehaviour
    {
        [Tooltip("PLAYER_SAUSAGE_W86_v01_manifest.json (the importer sets it).")]
        public TextAsset Manifest;

        SausageManifestV01 manifest;
        readonly Dictionary<string, List<GameObject>> objects = new Dictionary<string, List<GameObject>>(StringComparer.Ordinal);
        readonly Dictionary<string, List<(Renderer r, int index)>> slotsByMaterial = new Dictionary<string, List<(Renderer, int)>>(StringComparer.Ordinal);
        MaterialPropertyBlock block;
        bool indexed;
        static readonly int BaseColor = Shader.PropertyToID("_BaseColor"), ColorId = Shader.PropertyToID("_Color");

        public SausageManifestV01 Parsed
        {
            get
            {
                if (manifest == null)
                {
                    TextAsset t = Manifest != null ? Manifest : Resources.Load<TextAsset>(SausageManifestV01.ResourceName);
                    if (t != null) manifest = SausageManifestV01.Parse(t.text);
                }
                return manifest;
            }
        }

        public bool HasPart(AppearanceSlot slot, string id) => Parsed != null ? Parsed.Has(slot, id) : AppearanceCatalogV01.IsValid(slot, id);

        void Index()
        {
            if (indexed) return;
            indexed = true;
            objects.Clear(); slotsByMaterial.Clear();
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
            {
                if (!objects.TryGetValue(t.name, out var list)) objects[t.name] = list = new List<GameObject>();
                list.Add(t.gameObject);
            }
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    string n = mats[i].name.Replace(" (Instance)", "");
                    if (!slotsByMaterial.TryGetValue(n, out var list)) slotsByMaterial[n] = list = new List<(Renderer, int)>();
                    list.Add((r, i));
                }
            }
        }

        void SetObject(string name, bool on)
        {
            if (string.IsNullOrEmpty(name) || !objects.TryGetValue(name, out var list)) return;
            foreach (var go in list) if (go != null && go.activeSelf != on) go.SetActive(on);
        }

        void SetLods(SausageOptionV01 o, bool on, bool underHat)
        {
            if (o == null) return;
            foreach (string n in o.lods) SetObject(n, on && !underHat);
            foreach (string n in o.lods_under_hat) SetObject(n, on && underHat);
            if (!string.IsNullOrEmpty(o.mesh)) SetObject(o.mesh, on && !underHat);
            if (!string.IsNullOrEmpty(o.mesh_under_hat)) SetObject(o.mesh_under_hat, on && underHat);
        }

        void Tint(string material, Color c)
        {
            if (string.IsNullOrEmpty(material) || !slotsByMaterial.TryGetValue(material, out var list)) return;
            block ??= new MaterialPropertyBlock();
            c.a = 1f;
            foreach (var (r, index) in list)
            {
                if (r == null) continue;
                r.GetPropertyBlock(block, index);
                block.SetColor(BaseColor, c);
                block.SetColor(ColorId, c);
                r.SetPropertyBlock(block, index);
            }
        }

        static Color Hex(string hex, Color fallback) => !string.IsNullOrEmpty(hex) && ColorUtility.TryParseHtmlString(hex, out Color c) ? c : fallback;

        public void Apply(PlayerAppearance look)
        {
            var m = Parsed;
            if (m == null) { Debug.LogWarning("[OV Avatar] no parts manifest: the player sausage cannot be dressed", this); return; }
            Index();
            var a = AppearanceRules.Sanitize(look);
            var head = m.Option(AppearanceSlot.Accessory, a.Get(AppearanceSlot.Accessory));
            bool hat = head != null && head.hair_under_hat;
            var hidden = new HashSet<string>(StringComparer.Ordinal);
            foreach (AppearanceSlot slot in new[] { AppearanceSlot.Hair, AppearanceSlot.FacialHair, AppearanceSlot.Top, AppearanceSlot.Bottom, AppearanceSlot.Accessory })
            {
                var aspect = m.Aspect(slot);
                if (aspect == null) continue;
                string chosen = a.Get(slot);
                foreach (var o in aspect.options)
                {
                    bool on = o.id == chosen;
                    SetLods(o, on, slot == AppearanceSlot.Hair && hat);
                    if (on && o.hides_body_regions != null) foreach (string r in o.hides_body_regions) hidden.Add(r);
                }
            }
            foreach (string region in m.@base.meshes)
            {
                if (m.@base.always_on.Contains(region)) { SetRegion(region, true); continue; }
                SetRegion(region, !hidden.Contains(region));
            }
            // tints
            var skin = m.skin_tones.options.Find(o => o.id == a.skin) ?? (m.skin_tones.options.Count > 0 ? m.skin_tones.options[0] : null);
            if (skin != null)
            {
                var mats = m.skin_tones.materials ?? new SausageSkinMaterialsV01();
                Tint(mats.skin, Hex(skin.skin, Color.white)); Tint(mats.nose, Hex(skin.nose, Color.white));
                Tint(mats.inner, Hex(skin.inner, Color.white)); Tint(mats.rim, Hex(skin.rim, Color.white));
            }
            Swatch("PLAYER_Top", m.clothing_swatches.options.Find(o => o.id == a.topColour));
            Swatch("PLAYER_Bottom", m.clothing_swatches.options.Find(o => o.id == a.bottomColour));
            Color hair = AppearanceProfileV01.Swatch(a, AppearanceSlot.HairColour, Hex("#5C402E", Color.black));
            Tint("PLAYER_Hair", hair);
            Tint("PLAYER_Hair_Part", hair * 0.76f);
            Tint("PLAYER_Stubble", Color.Lerp(hair, Hex("#6E5242", hair), 0.35f));
        }

        void SetRegion(string region, bool on)
        {
            SetObject(region, on);
            for (int l = 0; l < 3; l++) SetObject(region + "_LOD" + l, on);
        }

        void Swatch(string prefix, SausageSwatchV01 s)
        {
            if (s == null) return;
            Tint(prefix + "_Main", Hex(s.main, Color.white));
            Tint(prefix + "_Trim", Hex(s.trim, Color.white));
            Tint(prefix + "_Accent", Hex(s.accent, Color.white));
        }
    }
}
