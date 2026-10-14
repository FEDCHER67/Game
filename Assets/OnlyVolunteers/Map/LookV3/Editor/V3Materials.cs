using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 surface categories and their materials. A category is one recoloured texture set (GPT's G13 output,
    // Assets/OnlyVolunteers/Art/StyleKit_v3: materials_v3.json -> Materials/M3_<category>.mat). Until those exist, a flat
    // temporary M3_<category>.mat (URP Lit, palette swatch) under LookV3/Materials/Temp stands in, so wiring the real
    // set is a data swap: "Refresh Style v3 Materials" (or any v3 build) rewrites the scene materials V3S_<category>.mat
    // in place (same GUIDs) from whichever source exists. The scene materials use the V3Surface shader: texture x
    // vertex colour, so every building of a category shares one material whatever its palette colour.
    public static class V3Materials
    {
        public const string Root = "Assets/OnlyVolunteers/Map/LookV3";
        // G18: later builds own their generated material/layer assets; v17 GUIDs and bytes stay intact.
        private static string RevisionFolder => MapLookBuilderV3.Current == "v18" || MapLookBuilderV3.Current == "v19"
            ? "/" + MapLookBuilderV3.Current : "";
        public static string MaterialDir => Root + "/Materials" + RevisionFolder;
        public static string TempDir => MaterialDir + "/Temp";
        public static string TextureDir => Root + "/Textures" + RevisionFolder;
        public static string LayerDir => Root + "/TerrainLayers" + RevisionFolder;
        public const string KitRoot = "Assets/OnlyVolunteers/Art/StyleKit_v3";
        public const string KitJson = KitRoot + "/materials_v3.json";
        public const string KitMaterialDir = KitRoot + "/Materials";

        public sealed class Category
        {
            public string Id, Swatch;
            public float Tile = 2f, Smoothness = 0.1f, Metallic, Bump = 0.5f;
            public bool Specular, Reflections;

            public Category(string id, string swatch, float tile, float smoothness = 0.1f)
            {
                Id = id;
                Swatch = swatch;
                Tile = tile;
                Smoothness = smoothness;
            }
        }

        // Ids = GPT's G13 category keys (picks_OAR.json), plus our own glass / paint / flat.
        public static readonly Category[] All =
        {
            new("1a_grass", "lawn", 4f), new("1b_dirt_road", "wood.light", 4f), new("1c_beach_sand", "sand", 4f),
            new("1d_gravel", "grey.light", 2f), new("1e_mud", "wood.dark", 4f, 0.25f),
            new("2a_asphalt", "asphalt", 6f, 0.12f), new("2b_sidewalk_tiles", "paving", 2f), new("2c_cobblestone", "paving.dark", 2f),
            new("3a_brick", "brick", 2f), new("3b_plaster_stucco", "cream", 3f), new("3c_concrete_panels", "panel", 4f),
            new("3d_cinder_blocks", "grey", 2f),
            new("4a_clay_roof_tiles", "terracotta", 2f, 0.15f), new("4b_slate_shingles", "slate", 2f, 0.2f),
            new("4c_corrugated_metal", "grey", 2f, 0.35f) { Metallic = 0.25f, Specular = true }, new("4d_flat_bitumen_roof", "grey.dark", 4f, 0.12f),
            new("5a_wood_planks_fences", "wood", 2f), new("5b_logs", "wood", 2f),
            new("6a_painted_metal_panels", "teal", 3f, 0.3f) { Specular = true }, new("6b_lightly_weathered_metal", "grey", 2f, 0.3f) { Metallic = 0.2f, Specular = true },
            new("7a_rock_cliff", "grey", 6f), new("7b_tree_bark", "wood", 2f),
            new("glass", "glass", 2f, 0.5f) { Specular = true, Reflections = true },
            new("paint", "chalk", 2f, 0.2f),
            new("flat", "chalk", 2f, 0.12f),
        };

        private static Dictionary<string, Category> byId;

        public static Category Get(string id)
        {
            if (byId == null)
            {
                byId = new Dictionary<string, Category>();
                foreach (Category c in All) byId[c.Id] = c;
            }
            return byId.TryGetValue(id, out Category cat) ? cat : byId["flat"];
        }

        // What the scene draws with, per category, and the colour the vertex tint is relative to.
        public sealed class Resolved
        {
            public Material Material;
            public Color Reference = Color.white;
            public string Source;
            public Texture Albedo, Normal, Mask;
            public float Tile;
        }

        private static readonly Dictionary<string, Resolved> cache = new();

        // One category of the G13 manifest (materials_v3*.json, the highest "revision" wins, as in GPT's builder).
        private sealed class KitEntry
        {
            public string Category, Material, Albedo, Normal, Mask, Palette;
            public float Tile;
        }

        private static Dictionary<string, KitEntry> kitTable;
        private static string kitManifest;

        // Per-revision scene materials and terrain layers: v16 and older keep V3S_/TL3_/T3_ and the G13 manifest of their
        // build (revision <= 5); v17+ (MapLookBuilderV3.Current) writes V3S17_/TL17_/T17_ from the newest manifest, so a
        // v17 texture revision never changes the v16 scenes.
        private static bool V17 => MapLookBuilderV3.IsV17(MapLookBuilderV3.Current);
        private const double V16ManifestRevision = 5;

        public static void ResetCache()
        {
            cache.Clear();
            kitTable = null;
            waterCache = null;
        }

        // Vertex colour (linear: the project is in linear space and vertex colours are not converted) that makes category
        // `id` show palette colour `target` (sRGB hex) over the category texture.
        public static Color Tint(string id, Color target)
        {
            Resolved r = Resolve(id);
            Color t = target.linear, re = r.Reference.linear;
            return new Color(Ratio(t.r, re.r), Ratio(t.g, re.g), Ratio(t.b, re.b), 1f);
        }

        private static float Ratio(float t, float r) => Mathf.Clamp(t / Mathf.Max(0.02f, r), 0f, 6f);

        public static Material Mat(string id) => Resolve(id).Material;

        public static Resolved Resolve(string id)
        {
            if (cache.TryGetValue(id, out Resolved r) && r.Material != null) return r;
            Category cat = Get(id);
            r = new Resolved { Tile = cat.Tile };
            Color baseColour = Color.white;
            KitEntry entry = Kit(cat.Id);
            if (entry != null)
            {
                Material source = string.IsNullOrEmpty(entry.Material) ? null : AssetDatabase.LoadAssetAtPath<Material>(entry.Material);
                r.Source = source != null ? entry.Material : entry.Albedo;
                r.Tile = entry.Tile > 0f ? entry.Tile : cat.Tile;
                r.Albedo = (source != null ? Tex(source, "_BaseMap", "_MainTex") : null) ?? AssetDatabase.LoadAssetAtPath<Texture2D>(entry.Albedo ?? "");
                r.Normal = (source != null ? Tex(source, "_BumpMap", "_NormalMap") : null) ?? AssetDatabase.LoadAssetAtPath<Texture2D>(entry.Normal ?? "");
                r.Mask = (source != null ? Tex(source, "_MaskMap", "_MetallicGlossMap") : null) ?? AssetDatabase.LoadAssetAtPath<Texture2D>(entry.Mask ?? "");
                if (source != null && source.HasProperty("_BaseColor")) baseColour = source.GetColor("_BaseColor");
            }
            if (r.Albedo == null)
            {
                Material temp = TempMaterial(cat);
                r.Source = AssetDatabase.GetAssetPath(temp);
                r.Normal = null;
                r.Mask = null;
                baseColour = Color.white; // untextured: the vertex colour is the palette colour itself
            }
            Color avg = r.Albedo is Texture2D t2 ? Average(t2) : Color.white;
            r.Reference = new Color(avg.r * baseColour.r, avg.g * baseColour.g, avg.b * baseColour.b, 1f);
            r.Material = SceneMaterial(cat, r, baseColour);
            cache[id] = r;
            return r;
        }

        private static KitEntry Kit(string id)
        {
            if (kitTable == null) kitTable = ReadKitTable();
            return kitTable.TryGetValue(id, out KitEntry e) ? e : null;
        }

        public static string KitManifest
        {
            get
            {
                if (kitTable == null) kitTable = ReadKitTable();
                return kitManifest;
            }
        }

        private static Dictionary<string, KitEntry> ReadKitTable()
        {
            var table = new Dictionary<string, KitEntry>();
            kitManifest = null;
            string dir = Path.Combine(Application.dataPath, "..", KitRoot);
            if (!Directory.Exists(dir)) return table;
            object best = null;
            double bestRev = double.MinValue;
            foreach (string f in Directory.GetFiles(dir, "materials_v3*.json"))
            {
                object root;
                try { root = V3Json.Parse(File.ReadAllText(f)); }
                catch { continue; }
                double rev = V3Json.GetNumber(root, 0, "revision");
                if (!(root is Dictionary<string, object>) || rev <= bestRev) continue;
                if (!V17 && rev > V16ManifestRevision) continue;
                best = root;
                bestRev = rev;
                kitManifest = KitRoot + "/" + Path.GetFileName(f);
            }
            if (!(best is Dictionary<string, object> dict)) return table;
            void Add(string key, object o)
            {
                if (!(o is Dictionary<string, object> e)) return;
                key = V3Json.GetString(o, "category") ?? key;
                if (string.IsNullOrEmpty(key)) return;
                float tile = (float)V3Json.GetNumber(o, 0, "metres_per_tile");
                if (e.TryGetValue("metres_per_tile", out object mpt) && mpt is Dictionary<string, object>) tile = (float)V3Json.GetNumber(mpt, 0, "x");
                var k = table.TryGetValue(key, out KitEntry old) ? old : new KitEntry { Category = key };
                k.Material = V3Json.GetString(o, "material_path", "material") ?? k.Material;
                k.Albedo = V3Json.GetString(o, "albedo") ?? k.Albedo;
                k.Normal = V3Json.GetString(o, "normal") ?? k.Normal;
                k.Mask = V3Json.GetString(o, "mask") ?? k.Mask;
                k.Palette = V3Json.GetString(o, "palette_hex") ?? k.Palette;
                if (tile > 0f) k.Tile = tile;
                table[key] = k;
            }
            if (dict.TryGetValue("categories", out object cats) && cats is Dictionary<string, object> cd)
                foreach (var kv in cd) Add(kv.Key, kv.Value);
            if (dict.TryGetValue("entries", out object ents) && ents is List<object> list)
                foreach (object o in list) Add(null, o);
            return table;
        }

        private static Texture Tex(Material m, params string[] names)
        {
            foreach (string n in names)
                if (m.HasProperty(n) && m.GetTexture(n) != null)
                    return m.GetTexture(n);
            return null;
        }

        // Mean colour of a texture (GPU downsample, so import settings do not matter).
        public static Color Average(Texture2D tex)
        {
            var rt = RenderTexture.GetTemporary(32, 32, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            Graphics.Blit(tex, rt);
            RenderTexture prev = RenderTexture.active;
            RenderTexture.active = rt;
            var read = new Texture2D(32, 32, TextureFormat.RGBA32, false, false);
            read.ReadPixels(new Rect(0, 0, 32, 32), 0, 0);
            read.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            Color sum = Color.black;
            foreach (Color c in read.GetPixels()) sum += c;
            Object.DestroyImmediate(read);
            sum /= 1024f;
            sum.a = 1f;
            return sum;
        }

        private static Material TempMaterial(Category cat)
        {
            LookAssetStore.EnsureFolder(TempDir);
            string path = $"{TempDir}/M3_{cat.Id}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "M3_" + cat.Id };
            m.SetColor("_BaseColor", V3Palette.C(cat.Swatch));
            m.SetFloat("_Smoothness", cat.Smoothness);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        private static Material SceneMaterial(Category cat, Resolved r, Color baseColour)
        {
            LookAssetStore.EnsureFolder(MaterialDir);
            string prefix = V17 ? "V3S17_" : "V3S_";
            string path = $"{MaterialDir}/{prefix}{cat.Id}.mat";
            Shader shader = Shader.Find("OnlyVolunteers/StyleV3/Surface");
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool created = m == null;
            if (created) m = new Material(shader) { name = prefix + cat.Id };
            else if (m.shader != shader) m.shader = shader;
            m.SetTexture("_BaseMap", r.Albedo);
            m.SetTextureScale("_BaseMap", Vector2.one / Mathf.Max(0.05f, r.Tile));
            m.SetTextureOffset("_BaseMap", Vector2.zero);
            m.SetColor("_BaseColor", baseColour);
            m.SetTexture("_BumpMap", r.Normal);
            m.SetTextureScale("_BumpMap", Vector2.one / Mathf.Max(0.05f, r.Tile));
            m.SetFloat("_BumpScale", r.Albedo != null ? 1f : cat.Bump); // G13 normals carry their 50 % strength baked in
            SetKeyword(m, "_NORMALMAP", "_UseNormalMap", r.Normal != null);
            m.SetTexture("_MaskMap", r.Mask);
            SetKeyword(m, "_V3_MASKMAP", "_UseMaskMap", r.Mask != null);
            // With a G13 mask the authored channels rule (R metallic, G AO, A smoothness), as in GPT's URP Lit materials.
            m.SetFloat("_Smoothness", r.Mask != null ? 1f : cat.Smoothness);
            m.SetFloat("_Metallic", r.Mask != null ? 1f : cat.Metallic);
            m.SetFloat("_OcclusionStrength", r.Mask != null ? 1f : 0.5f);
            m.SetFloat("_MacroStrength", cat.Id == "glass" || cat.Id == "paint" ? 0f : 0.05f);
            Color refLin = r.Reference.linear;
            m.SetVector("_TintRef", new Vector4(refLin.r, refLin.g, refLin.b, 1f));
            SetKeyword(m, "_SPECULARHIGHLIGHTS_OFF", "_SpecularHighlightsOff", !cat.Specular && r.Mask == null);
            SetKeyword(m, "_ENVIRONMENTREFLECTIONS_OFF", "_EnvironmentReflectionsOff", !cat.Reflections);
            m.enableInstancing = true;
            if (created) AssetDatabase.CreateAsset(m, path);
            else EditorUtility.SetDirty(m);
            return m;
        }

        private static void SetKeyword(Material m, string keyword, string toggle, bool on)
        {
            m.SetFloat(toggle, on ? 1f : 0f);
            if (on) m.EnableKeyword(keyword);
            else m.DisableKeyword(keyword);
        }

        [MenuItem("OnlyVolunteers/Map/Style v3/Refresh Style v3 Materials (data swap)")]
        public static void RefreshAll()
        {
            ResetCache();
            var sb = new System.Text.StringBuilder("[StyleV3] materials:\n");
            foreach (Category c in All)
            {
                Resolved r = Resolve(c.Id);
                sb.AppendLine($"  {c.Id}: {(r.Albedo != null ? "textured" : "flat temp")} <- {r.Source}, {r.Tile} m/tile, ref {LookConvert.Hex(r.Reference)}");
            }
            WaterMaterials(true);
            AssetDatabase.SaveAssets();
            Debug.Log(sb.ToString());
        }

        public static bool KitTexturesPresent()
        {
            ResetCache();
            int textured = 0;
            foreach (Category c in All)
                if (Kit(c.Id) != null) textured++;
            return textured > 0;
        }

        // ------------------------------------------------------------------ water

        public sealed class WaterKind
        {
            public string Id;
            public string Shallow, Deep;
            public float DepthRange, Clarity, FoamWidth, FoamStrength, Ripple1, Ripple2, RippleStrength, Swell, WaveSpeed, Refraction, Caustics, CausticsDepth, Reflection;
        }

        // Shallow turquoise -> deep palette blue for the sea; calmer, greener inland water; murky bog; bright pools.
        public static readonly WaterKind[] WaterKinds =
        {
            new() { Id = "sea", Shallow = "#5FD0CB", Deep = "#2A86C8", DepthRange = 2.6f, Clarity = 1.5f, FoamWidth = 0.9f, FoamStrength = 0.9f, Ripple1 = 9f, Ripple2 = 3.6f, RippleStrength = 0.65f, Swell = 0.45f, WaveSpeed = 0.45f, Refraction = 0.04f, Caustics = 0.8f, CausticsDepth = 2.2f, Reflection = 0.55f },
            new() { Id = "lake", Shallow = "#6CC8C0", Deep = "#2E7FB8", DepthRange = 1.0f, Clarity = 0.9f, FoamWidth = 0.35f, FoamStrength = 0.55f, Ripple1 = 6f, Ripple2 = 2.4f, RippleStrength = 0.45f, Swell = 0.15f, WaveSpeed = 0.2f, Refraction = 0.03f, Caustics = 0.6f, CausticsDepth = 1.2f, Reflection = 0.5f },
            new() { Id = "river", Shallow = "#78CFC6", Deep = "#3488BE", DepthRange = 0.8f, Clarity = 0.8f, FoamWidth = 0.35f, FoamStrength = 0.75f, Ripple1 = 4.5f, Ripple2 = 1.9f, RippleStrength = 0.6f, Swell = 0.1f, WaveSpeed = 0.12f, Refraction = 0.035f, Caustics = 0.7f, CausticsDepth = 1.0f, Reflection = 0.45f },
            new() { Id = "canal", Shallow = "#6FBFB6", Deep = "#2F78A8", DepthRange = 1.2f, Clarity = 0.8f, FoamWidth = 0.25f, FoamStrength = 0.5f, Ripple1 = 5.5f, Ripple2 = 2.2f, RippleStrength = 0.5f, Swell = 0.1f, WaveSpeed = 0.1f, Refraction = 0.03f, Caustics = 0.5f, CausticsDepth = 1.2f, Reflection = 0.5f },
            new() { Id = "pond", Shallow = "#86C9A8", Deep = "#3C8496", DepthRange = 0.7f, Clarity = 0.6f, FoamWidth = 0.25f, FoamStrength = 0.4f, Ripple1 = 5f, Ripple2 = 2f, RippleStrength = 0.35f, Swell = 0.1f, WaveSpeed = 0.12f, Refraction = 0.025f, Caustics = 0.35f, CausticsDepth = 0.8f, Reflection = 0.5f },
            new() { Id = "bog", Shallow = "#8FAE78", Deep = "#4C6E58", DepthRange = 0.5f, Clarity = 0.35f, FoamWidth = 0.2f, FoamStrength = 0.25f, Ripple1 = 6f, Ripple2 = 2.5f, RippleStrength = 0.2f, Swell = 0.05f, WaveSpeed = 0.05f, Refraction = 0.015f, Caustics = 0f, CausticsDepth = 0.5f, Reflection = 0.4f },
            new() { Id = "pool", Shallow = "#7FE3E6", Deep = "#33A9D6", DepthRange = 1.4f, Clarity = 3.5f, FoamWidth = 0.05f, FoamStrength = 0f, Ripple1 = 3f, Ripple2 = 1.3f, RippleStrength = 0.3f, Swell = 0f, WaveSpeed = 0.08f, Refraction = 0.03f, Caustics = 1.2f, CausticsDepth = 2.5f, Reflection = 0.35f },
            new() { Id = "fountain", Shallow = "#7FD6D8", Deep = "#3A9CC8", DepthRange = 0.5f, Clarity = 2f, FoamWidth = 0.08f, FoamStrength = 0.3f, Ripple1 = 2f, Ripple2 = 0.9f, RippleStrength = 0.45f, Swell = 0f, WaveSpeed = 0.15f, Refraction = 0.03f, Caustics = 0.9f, CausticsDepth = 1f, Reflection = 0.35f },
        };

        // Fedya 2026-10-11: the water shader is GPT's job. The water meshes take the material the G13 manifest maps for
        // water: a per-kind variant when one lands ("8a_water_sea", "..._lake", "..._river"; ponds, bogs, pools and the
        // canal fall back to lake / river), else "8a_water". Our own V3W_* (V3Water.shader) is only the fallback when the
        // manifest has no water at all.
        public static Material Water(string kind)
        {
            if (kitTable == null) kitTable = ReadKitTable();
            string group = kind == "sea" ? "sea" : kind == "river" || kind == "canal" ? "river" : kind == "pool" || kind == "fountain" ? "pool" : "lake";
            foreach (string want in new[] { kind, group, group == "pool" ? "lake" : null })
            {
                if (want == null) continue;
                foreach (var kv in kitTable)
                    if (kv.Key.Contains("water") && kv.Key.EndsWith("_" + want) && WaterMat(kv.Value) is Material m)
                        return m;
            }
            foreach (var kv in kitTable)
                if (kv.Key == "8a_water" && WaterMat(kv.Value) is Material m) return m;
            foreach (Material m in WaterMaterials(false))
                if (m != null && m.name == "V3W_" + kind) return m;
            return WaterMaterials(false)[0];
        }

        private static Material WaterMat(KitEntry e) => e == null || string.IsNullOrEmpty(e.Material) ? null : AssetDatabase.LoadAssetAtPath<Material>(e.Material);

        // Which water material is active (for the build log and the report).
        public static string WaterSource(string kind)
        {
            Material m = Water(kind);
            return m != null ? AssetDatabase.GetAssetPath(m) : "none";
        }

        private static Material[] waterCache;

        public static Material[] WaterMaterials(bool rewrite)
        {
            if (waterCache != null && !rewrite && System.Array.TrueForAll(waterCache, m => m != null)) return waterCache;
            LookAssetStore.EnsureFolder(MaterialDir);
            Texture2D normal = WaterNormalTexture(), aux = WaterAuxTexture();
            // A G13 water set (8a_water) brings its own ripple normal: a data swap like every other category.
            KitEntry water = Kit("8a_water");
            Material kit = water != null && !string.IsNullOrEmpty(water.Material) ? AssetDatabase.LoadAssetAtPath<Material>(water.Material) : null;
            Texture kitNormal = (kit != null ? Tex(kit, "_BumpMap", "_NormalMap") : null) ?? (water != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(water.Normal ?? "") : null);
            Shader shader = Shader.Find("OnlyVolunteers/StyleV3/Water");
            var list = new List<Material>();
            foreach (WaterKind k in WaterKinds)
            {
                string path = $"{MaterialDir}/V3W_{k.Id}.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                bool created = m == null;
                if (created) m = new Material(shader) { name = "V3W_" + k.Id };
                else if (m.shader != shader) m.shader = shader;
                m.SetColor("_ShallowColor", LookConvert.Color(k.Shallow));
                m.SetColor("_DeepColor", LookConvert.Color(k.Deep));
                m.SetFloat("_DepthRange", k.DepthRange);
                m.SetFloat("_Clarity", k.Clarity);
                m.SetFloat("_FoamWidth", k.FoamWidth);
                m.SetFloat("_FoamStrength", k.FoamStrength);
                m.SetFloat("_NormalTiling1", k.Ripple1);
                m.SetFloat("_NormalTiling2", k.Ripple2);
                m.SetFloat("_NormalStrength", k.RippleStrength);
                m.SetFloat("_SwellStrength", k.Swell);
                m.SetFloat("_WaveSpeed", k.WaveSpeed);
                m.SetFloat("_RefractionStrength", k.Refraction);
                m.SetFloat("_CausticsStrength", k.Caustics);
                m.SetFloat("_CausticsDepth", k.CausticsDepth);
                m.SetFloat("_ReflectionStrength", k.Reflection);
                m.SetTexture("_NormalMap", kitNormal != null ? kitNormal : normal);
                m.SetTexture("_AuxTex", aux);
                m.renderQueue = (int)RenderQueue.Transparent - 10;
                if (created) AssetDatabase.CreateAsset(m, path);
                else EditorUtility.SetDirty(m);
                list.Add(m);
            }
            waterCache = list.ToArray();
            return waterCache;
        }

        // Tileable ripple normal: a sum of sines with whole wave numbers on the unit square (so it wraps), broad and soft.
        private static Texture2D WaterNormalTexture()
        {
            string path = TextureDir + "/T_V3_WaterNormal.png";
            var existing = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (existing != null) return existing;
            LookAssetStore.EnsureFolder(TextureDir);
            const int size = 512;
            var rnd = new System.Random(1611);
            var waves = new List<(int kx, int ky, float amp, float phase)>();
            for (int k = 0; k < 28; k++)
            {
                int kx = rnd.Next(-7, 8), ky = rnd.Next(-7, 8);
                if (kx == 0 && ky == 0) continue;
                float len = Mathf.Sqrt(kx * kx + ky * ky);
                waves.Add((kx, ky, 1f / Mathf.Pow(len, 1.35f), (float)rnd.NextDouble() * Mathf.PI * 2f));
            }
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float u = x / (float)size, v = y / (float)size, dx = 0f, dy = 0f;
                    foreach (var w in waves)
                    {
                        float a = 2f * Mathf.PI * (w.kx * u + w.ky * v) + w.phase;
                        // Sharpened crest (1 - |sin|) gives the stylised, broad-trough ripple.
                        float c = Mathf.Cos(a) * w.amp;
                        dx += c * w.kx;
                        dy += c * w.ky;
                    }
                    var n = new Vector3(-dx * 0.09f, -dy * 0.09f, 1f).normalized;
                    px[y * size + x] = new Color32((byte)(n.x * 127.5f + 127.5f), (byte)(n.y * 127.5f + 127.5f), (byte)(n.z * 127.5f + 127.5f), 255);
                }
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(Application.dataPath, "..", path), tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(path);
            var ti = (TextureImporter)AssetImporter.GetAtPath(path);
            ti.textureType = TextureImporterType.NormalMap;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        // R: caustic web (tileable Voronoi edge distance F2 - F1), G: soft tileable value-noise for the foam mask.
        private static Texture2D WaterAuxTexture()
        {
            string path = TextureDir + "/T_V3_WaterAux.png";
            var existing = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (existing != null) return existing;
            LookAssetStore.EnsureFolder(TextureDir);
            const int size = 512, cells = 7;
            var rnd = new System.Random(4407);
            var pts = new Vector2[cells, cells];
            for (int j = 0; j < cells; j++)
                for (int i = 0; i < cells; i++)
                    pts[i, j] = new Vector2(i + 0.15f + (float)rnd.NextDouble() * 0.7f, j + 0.15f + (float)rnd.NextDouble() * 0.7f);
            const int grid = 8;
            var noise = new float[grid, grid];
            for (int j = 0; j < grid; j++)
                for (int i = 0; i < grid; i++)
                    noise[i, j] = (float)rnd.NextDouble();
            float Noise(float x, float y, int g, float[,] n)
            {
                int x0 = Mathf.FloorToInt(x), y0 = Mathf.FloorToInt(y);
                float fx = x - x0, fy = y - y0;
                fx = fx * fx * (3f - 2f * fx);
                fy = fy * fy * (3f - 2f * fy);
                float a = n[((x0 % g) + g) % g, ((y0 % g) + g) % g], b = n[((x0 + 1) % g + g) % g, ((y0 % g) + g) % g];
                float c = n[((x0 % g) + g) % g, ((y0 + 1) % g + g) % g], d = n[((x0 + 1) % g + g) % g, ((y0 + 1) % g + g) % g];
                return Mathf.Lerp(Mathf.Lerp(a, b, fx), Mathf.Lerp(c, d, fx), fy);
            }
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float u = x / (float)size * cells, v = y / (float)size * cells;
                    float f1 = 99f, f2 = 99f;
                    int cx = Mathf.FloorToInt(u), cy = Mathf.FloorToInt(v);
                    for (int dj = -1; dj <= 1; dj++)
                        for (int di = -1; di <= 1; di++)
                        {
                            int ii = cx + di, jj = cy + dj;
                            Vector2 p = pts[((ii % cells) + cells) % cells, ((jj % cells) + cells) % cells];
                            p += new Vector2(ii - ((ii % cells) + cells) % cells, jj - ((jj % cells) + cells) % cells);
                            float d = Vector2.Distance(p, new Vector2(u, v));
                            if (d < f1) { f2 = f1; f1 = d; }
                            else if (d < f2) f2 = d;
                        }
                    float edge = f2 - f1;
                    float caustic = Mathf.Pow(1f - Mathf.Clamp01(edge / 0.16f), 3f);
                    float fu = x / (float)size, fv = y / (float)size;
                    float n = Noise(fu * grid, fv * grid, grid, noise) * 0.65f + Noise(fu * grid * 2f + 3.1f, fv * grid * 2f + 1.7f, grid, noise) * 0.35f;
                    px[y * size + x] = new Color32((byte)(caustic * 255f), (byte)(Mathf.Clamp01(n) * 255f), 0, 255);
                }
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(Application.dataPath, "..", path), tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(path);
            var ti = (TextureImporter)AssetImporter.GetAtPath(path);
            ti.sRGBTexture = false;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.mipmapEnabled = true;
            ti.textureCompression = TextureImporterCompression.Uncompressed;
            ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        // ------------------------------------------------------------------ terrain layers

        // Terrain layer of a look-json ground name, drawn with a category texture (G13) tinted to a palette colour.
        public static TerrainLayer Layer(string name, string category, Color target, float tileOverride = 0f)
        {
            LookAssetStore.EnsureFolder(LayerDir);
            Resolved r = Resolve(category);
            string prefix = V17 ? "TL17_" : "TL3_";
            string path = $"{LayerDir}/{prefix}{name}.terrainlayer";
            var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
            bool created = layer == null;
            if (created) layer = new TerrainLayer { name = prefix + name };
            float tile = tileOverride > 0f ? tileOverride : r.Tile;
            layer.tileSize = new Vector2(tile, tile);
            if (r.Albedo is Texture2D albedo)
            {
                layer.diffuseTexture = albedo;
                Color ratio = Tint(category, target);
                layer.diffuseRemapMin = Vector4.zero;
                layer.diffuseRemapMax = new Vector4(ratio.r, ratio.g, ratio.b, 1f);
                layer.normalMapTexture = r.Normal as Texture2D;
                layer.normalScale = 0.5f;
                layer.maskMapTexture = r.Mask as Texture2D;
            }
            else
            {
                layer.diffuseTexture = FlatLayerTexture(name, target);
                layer.diffuseRemapMin = Vector4.zero;
                layer.diffuseRemapMax = Vector4.one;
                layer.normalMapTexture = null;
                layer.maskMapTexture = null;
            }
            layer.smoothness = 0.05f;
            layer.metallic = 0f;
            if (created) AssetDatabase.CreateAsset(layer, path);
            else EditorUtility.SetDirty(layer);
            return layer;
        }

        // Temporary ground texture: the palette colour with a quiet broad mottle (OAR: large quiet colour fields).
        private static Texture2D FlatLayerTexture(string name, Color colour)
        {
            string tp = V17 ? "T17_" : "T3_";
            string path = $"{LayerDir}/{tp}{name}_flat.asset";
            const int size = 64;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, true) { name = tp + name + "_flat", wrapMode = TextureWrapMode.Repeat };
            int seed = LookGeom.StableHash(name);
            var px = new Color[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float n = (LookGeom.Noise(x / 16f, y / 16f, seed) * 0.5f + 0.5f) * 0.7f + LookGeom.Hash01(x, y, seed) * 0.3f;
                    px[y * size + x] = LookConvert.Shade(colour, 0.95f + n * 0.1f);
                }
            tex.SetPixels(px);
            tex.Apply(true);
            return LookAssetStore.CreateOrReplace(tex, path);
        }
    }
}
