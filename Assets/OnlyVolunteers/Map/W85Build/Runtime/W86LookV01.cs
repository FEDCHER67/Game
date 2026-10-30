using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using OnlyVolunteers.Art;

namespace OnlyVolunteers.Map.W85
{
    // W86 look pass v01 (Fedya 25.10, brief §2): anti-aliasing on the game cameras, sky reflections, and material response.
    // Play only, nothing is written to assets: the map's shared materials (TextureTest kit, W86 props) stay as they are for the
    // other scenes; this scene swaps in tuned runtime copies.
    //  - AA: every game camera that renders to the screen gets SMAA (High). Cheap, no ghosting on the swaying foliage (TAA would).
    //  - Reflection: the scene had no probes and no baked sky, so every surface reflected Unity's grey default cubemap. One small
    //    cubemap of the live G22 sky plus the town around the camera (no players/NPCs, no shadows, no post) is set as the default
    //    reflection. Tiers 2-6 re-render 1-6 faces a frame and re-centre the cube on the camera at each full turn, so the
    //    reflections move continuously at a share of the frame rate (default high: 3 faces = the cube every 2nd frame); low
    //    resolution + mips keep it soft. Tier 1 = the old refresh-on-move; 0 = Unity default. No per-object probes.
    //  - Graphics options: PlayerPrefs (ov_gfx_*) read at start, for the future settings menu: MSAA, shadows, reflections, LOD.
    //  - Materials: rules by material name (and by renderer name for vehicles) set smoothness/metallic on runtime copies. Plaster,
    //    stone and brick get a restrained per-building variation (3 copies per material, picked by a hash of the building's
    //    position). Rough (district_rough) keeps its matte finish except glass. The player's van is never touched.
    [DisallowMultipleComponent]
    public sealed class W86LookV01 : MonoBehaviour
    {
        [Serializable]
        public struct Rule
        {
            [Tooltip("Material name must contain one of these ('|'-separated, case-insensitive).")] public string Material;
            [Tooltip("Optional: the renderer or its parent must contain one of these ('|'-separated).")] public string Renderer;
            [Tooltip("Smoothness; < 0 keeps the material's.")] public float Smoothness;
            [Tooltip("Metallic; < 0 keeps the material's.")] public float Metallic;
            [Tooltip("+/- smoothness spread across buildings (3 variants); 0 = one copy.")] public float Vary;
            [Tooltip("Apply inside district_rough too (glass only by default).")] public bool InRough;
        }

        public AntialiasingMode Antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
        public AntialiasingQuality AntialiasingQuality = AntialiasingQuality.High;

        [Header("Sky reflection")]
        public bool SkyReflection = true;
        public int ReflectionSize = 128;
        public float RefreshSeconds = 20f;
        public float SunTurnDegrees = 2f;
        public float MoveMetres = 20f;
        [Tooltip("Reflect the town too (else the sky only).")] public bool ReflectGeometry = true;
        public float ReflectFar = 180f;
        [Tooltip("LOD bias while the reflection renders (the scene runs 2): plain LOD1 houses in the soft reflection, ~4 renderers " +
                 "a house instead of ~50; the live cube costs a fraction of the CPU.")]
        public float ReflectLodBias = .3f;
        public Light Sun;

        [Header("Materials (first matching rule wins; the code table, not serialized)")]
        [NonSerialized] public Rule[] Rules = DefaultRules();
        [Tooltip("SUPERSEDED (Fedya 30.10: every model ~67 % less shiny, OvGlossV01): no longer applied. Was extra smoothness " +
                 "on masonry/render inside District_downtown (Fedya 25.10: Downtown still too matte). Kept so the scene's value loads.")]
        public float DowntownBoost = .14f;

        [Header("LOD (Fedya 25.10: visible switches, far shimmer of thin trims, CPU cost)")]
        [Tooltip("Buildings (LOD size >= 10 m): full facade (LOD0) down to this screen height, then the plain LOD1. Was 0.06 " +
                 "(~500 m: sub-pixel trims shimmered and every far house sent ~50 renderers). 0.16 = ~190 m for a 23 m house.")]
        public float BuildingLod0Height = .2f;
        [Tooltip("Small facade kit (fire escapes, roof tanks; size < 10 m): was 0.25 (~23 m, a visible pop while walking).")]
        public float KitLod0Height = .08f;
        public bool CrossFade = true;

        [Header("Light balance (Fedya 25.10: flat forms). Applied per game camera after DistrictWeather/G22 set the light;")]
        [Header("scaled down to nothing under an overcast sun (Rough), so district moods stay.")]
        public bool LightBalance = true;
        [Tooltip("Sun intensity x this on a clear sun.")] public float SunBoost = 1.2f;
        [Tooltip("Ambient (the flat SH the weather writes) x this.")] public float AmbientScale = .78f;
        [Tooltip("Sky-from-above / ground-from-below split of the ambient (0 = flat as before).")] public float AmbientGradient = .45f;
        [Tooltip("Added to the sun's shadow strength (was 0.66-0.74 on clear districts).")] public float ShadowAdd = .14f;
        [Tooltip("Sun intensity at which the balance starts / is full (Rough runs ~0.2, Downtown ~1.1).")]
        public Vector2 ClearSunRange = new Vector2(.45f, .85f);

        // Smoothness = the 25.10 tuned value x OvGlossV01.Factor (Fedya 30.10: all models ~67 % less shiny); metallic unchanged.
        // Absolute values on fresh copies of the source materials: applying the rules again never compounds.
        const float G = OvGlossV01.Factor, GG = OvGlossV01.GlassFactor;
        public static Rule[] DefaultRules() => new[]
        {
            // vehicles first (renderer rules): painted bodies with a controlled sheen
            new Rule { Material = "SK_Palette|T1_SK_Palette", Renderer = "car_|-car|sedan|taxi|pickup", Smoothness = .62f * G, Metallic = .25f },
            new Rule { Material = "MW86_Machines|MW86_Military", Renderer = "", Smoothness = .45f * G, Metallic = .2f },
            // glass: reflections everywhere (also Rough)
            new Rule { Material = "glass", Smoothness = .95f * GG, Metallic = 0f, InRough = true },
            // metals
            new Rule { Material = "Metal_Galv|flat_metal|chrome", Smoothness = .55f * G, Metallic = .7f },
            new Rule { Material = "Metal_Dark", Smoothness = .42f * G, Metallic = .55f },
            new Rule { Material = "Metal_Paint|Window_Frame|trapez", Smoothness = .45f * G, Metallic = .15f },
            new Rule { Material = "flat_gloss", Smoothness = .7f * G, Metallic = 0f },
            // masonry and render: restrained variation per building
            new Rule { Material = "Stone", Smoothness = .24f * G, Metallic = 0f, Vary = .06f * G },
            new Rule { Material = "plaster|stucco|TT_flat|TT_trim", Smoothness = .2f * G, Metallic = 0f, Vary = .05f * G },
            new Rule { Material = "brick", Smoothness = .16f * G, Metallic = 0f, Vary = .04f * G },
            new Rule { Material = "Concrete", Smoothness = .18f * G, Metallic = 0f, Vary = .03f * G },
            new Rule { Material = "white_plastic|T2P_white|T2P_c_", Smoothness = .5f * G, Metallic = 0f },
        };

        readonly Dictionary<(Material, int, int), Material> copies = new();
        readonly HashSet<Camera> configured = new();
        Camera reflCam;
        RenderTexture cube;
        float nextRefresh;
        Vector3 lastSunFwd, lastPos;
        int face = 6; // 6 = idle, 0..5 = next face to render
        public int SwappedSlots { get; private set; }
        public int MaterialCopies => copies.Count;

        // ---- graphics options: PlayerPrefs keys, written by the pause menu's graphics page (W86GraphicsSettingsV01) ----
        public const string PrefMsaa = "ov_gfx_msaa";             // 1 / 2 / 4 / 8 (default 4 = Low, 31.10)
        public const string PrefShadows = "ov_gfx_shadows";       // 0 off, 1 low (50 m, 2048), 2 high (120 m, 4096, faded edge) (default 2)
        // Reflection tiers (Fedya 25.10): the cube is re-rendered FacesPerTier[tier] faces a frame, so its update rate is a share of
        // the game's frame rate (at 120 FPS: ultra 120/s, very high ~80, high ~60, medium ~40, low ~20).
        // 0 Unity default, 1 refresh on move, 2 low (1 face), 3 medium (2), 4 high (3, default), 5 very high (4), 6 ultra (6 = 1:1,
        // "for the very best PCs"). ReflectionSize (128 px) below high, MaxReflectionSize (256 px) from high.
        // Costs: docs/reports/GRAPHICS_SETTINGS_NOTES_2026-10-25_RU.md
        public const string PrefReflections = "ov_gfx_reflections";
        public const int ReflectionsDefault = 1; // Vadim 27.10: defaults = the Low preset (W86GraphicsSettingsV01.Preset(0))
        static readonly int[] FacesPerTier = { 0, 0, 1, 2, 3, 4, 6 };
        public const string PrefLod = "ov_gfx_lod";               // 0 near (more FPS), 1 normal, 2 far (default 1)
        public const string PrefRenderScale = "ov_gfx_render_scale"; // percent, 50..100 (default 100 = Low, 31.10)
        public const string PrefTextures = "ov_gfx_textures";     // mip limit: 0 full, 1 half, 2 quarter (default 0)
        static readonly float[] LodScale = { 1.6f, 1f, .6f };      // x BuildingLod0Height: near switches to LOD1 sooner
        int reflTier = ReflectionsDefault;
        bool Live => reflTier >= 2;
        [Tooltip("Cube size from reflection tier 4 (high) up.")] public int MaxReflectionSize = 256;
        float baseBuildingLod0 = -1f;                               // BuildingLod0Height as set in the scene: multipliers never compound
        readonly Dictionary<LODGroup, LOD[]> originalLods = new();
#if UNITY_EDITOR
        int savedMsaa; float savedShadowDist, savedRenderScale, savedBorder; int savedShadowRes, savedMipLimit; bool savedRp;
#endif

        /// <summary>Reads the ov_gfx_* preferences and applies them to the running scene. Idempotent: safe to call again after
        /// any change (the graphics page's Apply). Reflections are created, resized or released as the tier needs.</summary>
        public void ApplyGraphics()
        {
            var rp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (rp)
            {
#if UNITY_EDITOR
                if (!savedRp)
                {
                    savedRp = true; savedMsaa = rp.msaaSampleCount; savedShadowDist = rp.shadowDistance;
                    savedShadowRes = rp.mainLightShadowmapResolution; savedRenderScale = rp.renderScale; savedMipLimit = QualitySettings.globalTextureMipmapLimit; savedBorder = rp.cascadeBorder;
                }
#endif
                int msaa = PlayerPrefs.GetInt(PrefMsaa, 4); // fallbacks = the Low preset (W86GraphicsSettingsV01.Preset(0), 31.10: no shimmer)
                rp.msaaSampleCount = msaa >= 8 ? 8 : msaa >= 4 ? 4 : msaa >= 2 ? 2 : 1;
                int sh = Mathf.Clamp(PlayerPrefs.GetInt(PrefShadows, 1), 0, 2);
                if (sh <= 0) rp.shadowDistance = 0f;
                else if (sh == 1) { rp.shadowDistance = 50f; rp.mainLightShadowmapResolution = 2048; }
                else { rp.shadowDistance = 120f; rp.mainLightShadowmapResolution = 4096; }
                // W86 (Fedya 25.10, video_02): at night the moon throws the towers' shadow across the plaza and its far edge was the hard
                // shadow-distance cut, a straight line riding with the camera. The last cascade now fades out over its last 35 %.
                rp.cascadeBorder = .35f;
                rp.renderScale = Mathf.Clamp(PlayerPrefs.GetInt(PrefRenderScale, 100), 50, 100) / 100f;
            }
            QualitySettings.globalTextureMipmapLimit = Mathf.Clamp(PlayerPrefs.GetInt(PrefTextures, 1), 0, 2);
            W85GrassRenderer.SetQuality((GrassQuality)Mathf.Clamp(PlayerPrefs.GetInt("ov_grass_quality", (int)GrassQuality.Low), 0, 3));

            if (baseBuildingLod0 < 0f) baseBuildingLod0 = BuildingLod0Height;
            BuildingLod0Height = baseBuildingLod0 * LodScale[Mathf.Clamp(PlayerPrefs.GetInt(PrefLod, 0), 0, 2)];
            TuneLods();

            reflTier = Mathf.Clamp(PlayerPrefs.GetInt(PrefReflections, ReflectionsDefault), 0, 6);
            if (reflTier <= 0 || !SkyReflection) ReleaseReflection();
            else
            {
                int size = reflTier >= 4 ? MaxReflectionSize : ReflectionSize;
                if (cube && cube.width != size) ReleaseReflection();
                if (!cube) SetupReflection(size);
            }
        }

        void Start()
        {
            if (!Sun) { var s = GameObject.Find("Sun"); if (s) Sun = s.GetComponent<Light>(); }
            ApplyMaterials();
            TowerShadowCasters();
            ApplyGraphics();
            // registered after the weather/sky hooks (their OnEnable ran first), so this runs after they set the light;
            // their end-of-camera restore puts the stored light back, so nothing accumulates
            if (LightBalance) RenderPipelineManager.beginCameraRendering += BalanceLight;
            RenderPipelineManager.beginCameraRendering += ReflectionLodIn;
            RenderPipelineManager.endCameraRendering += ReflectionLodOut;
        }

        void Update()
        {
            foreach (var cam in Camera.allCameras)
                if (cam.cameraType == CameraType.Game && !cam.targetTexture && configured.Add(cam)) ConfigureCamera(cam);
            if (!cube) return;
            if (Live)
            {   // tiers 2-6: FacesPerTier faces a frame, the cube re-centred on the camera at each full turn
                // faces run on across the cube's end (4 a frame = 4, 2+2, 4...), so the average really is FacesPerTier
                int mask = 0;
                for (int i = 0; i < FacesPerTier[reflTier]; i++)
                {
                    if (face >= 6)
                    {
                        if (mask != 0) { reflCam.RenderToCubemap(cube, mask); mask = 0; }
                        var mc = Camera.main; reflCam.transform.position = mc ? mc.transform.position : lastPos; face = 0;
                    }
                    mask |= 1 << face++;
                }
                if (mask != 0) reflCam.RenderToCubemap(cube, mask);
                return;
            }
            if (face < 6) { reflCam.RenderToCubemap(cube, 1 << face); face++; return; } // tier 1: a refresh in progress
            Vector3 sf = Sun ? Sun.transform.forward : Vector3.down;
            var main = Camera.main;
            Vector3 cp = main ? main.transform.position : lastPos;
            if (Time.unscaledTime >= nextRefresh || Vector3.Angle(sf, lastSunFwd) >= SunTurnDegrees || (cp - lastPos).sqrMagnitude >= MoveMetres * MoveMetres)
                BeginRefresh(sf, cp);
        }

        void ConfigureCamera(Camera cam)
        {
            var data = cam.GetUniversalAdditionalCameraData();
            if (!data) return;
            data.antialiasing = Antialiasing;
            data.antialiasingQuality = AntialiasingQuality;
        }

        void ReleaseReflection()
        {
            if (RenderSettings.customReflectionTexture == cube && cube) RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            if (cube) { cube.Release(); Destroy(cube); cube = null; }
            if (reflCam) { Destroy(reflCam.gameObject); reflCam = null; }
            face = 6;
        }

        void SetupReflection(int size)
        {
            var go = new GameObject("W86_SkyReflectionCamera") { hideFlags = HideFlags.DontSave };
            go.transform.SetParent(transform, false);
            reflCam = go.AddComponent<Camera>();
            reflCam.enabled = false;
            reflCam.cameraType = CameraType.Reflection; // the grass (its own compute pass), fogs and weather skip reflection cameras; G22 still draws the sky
            reflCam.cullingMask = ReflectGeometry ? ~((1 << OvLayers.Player) | (1 << OvLayers.RemotePlayer) | (1 << OvLayers.VehicleInterior) |
                                                      OvLayers.NpcMask | (1 << OvLayers.NpcSlide) | (1 << 5)) : 0; // 5 = UI
            reflCam.clearFlags = CameraClearFlags.Skybox;
            reflCam.nearClipPlane = .5f; reflCam.farClipPlane = ReflectFar;
            var data = reflCam.GetUniversalAdditionalCameraData();
            if (data) { data.renderPostProcessing = false; data.renderShadows = false; }
            cube = new RenderTexture(size, size, 16, RenderTextureFormat.ARGBHalf)
            {
                dimension = TextureDimension.Cube, useMipMap = true, autoGenerateMips = true, name = "W86_SkyReflection"
            };
            cube.Create();
            var main = Camera.main;
            BeginRefresh(Sun ? Sun.transform.forward : Vector3.down, main ? main.transform.position : transform.position);
            reflCam.RenderToCubemap(cube, 63); face = 6; // the first one whole, at load
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
            RenderSettings.customReflectionTexture = cube;
        }

        void BeginRefresh(Vector3 sunFwd, Vector3 at)
        {
            nextRefresh = Time.unscaledTime + RefreshSeconds;
            lastSunFwd = sunFwd; lastPos = at;
            reflCam.transform.position = at; // the district sky mood and the reflected street follow the camera
            face = 0;
        }

        void ApplyMaterials()
        {
            var vans = new HashSet<Transform>();
            foreach (var mb in FindObjectsByType<MonoBehaviour>())
                if (mb.GetType().Name == "VanController") vans.Add(mb.transform);
            var lowered = new string[Rules.Length][]; var lowRend = new string[Rules.Length][];
            for (int i = 0; i < Rules.Length; i++)
            {
                lowered[i] = Split(Rules[i].Material);
                lowRend[i] = Split(Rules[i].Renderer);
            }
            foreach (var r in FindObjectsByType<MeshRenderer>())
            {
                if (InAny(r.transform, vans)) continue;
                // a few W86 props carry more material slots than submeshes: re-assigning them only logs a warning per prop
                var mf = r.GetComponent<MeshFilter>();
                if (mf && mf.sharedMesh && r.sharedMaterials.Length > mf.sharedMesh.subMeshCount) continue;
                string district = District(r.transform);
                bool inRough = district == "district_rough";
                const float boost = 0f; // the Downtown sheen boost is superseded (OvGlossV01, Fedya 30.10)
                string rn = (r.name + " " + (r.transform.parent ? r.transform.parent.name : "")).ToLowerInvariant();
                var mats = r.sharedMaterials; bool changed = false;
                for (int k = 0; k < mats.Length; k++)
                {
                    var m = mats[k];
                    // URP Lit only: the StyleV3 Palette19 materials use smoothness/metallic as mask multipliers
                    if (!m || m.shader.name != "Universal Render Pipeline/Lit") continue;
                    string mn = m.name.ToLowerInvariant();
                    for (int i = 0; i < Rules.Length; i++)
                    {
                        if (!Contains(mn, lowered[i])) continue;
                        if (lowRend[i].Length > 0 && !Contains(rn, lowRend[i])) continue;
                        if (inRough && !Rules[i].InRough) break;
                        int variant = Rules[i].Vary > 0f ? Variant(r.transform) : 1;
                        mats[k] = Copy(m, i, variant, Rules[i].Vary > 0f ? boost : 0f); changed = true;
                        break;
                    }
                }
                if (changed) { r.sharedMaterials = mats; SwappedSlots++; }
            }
        }

        Material Copy(Material src, int rule, int variant, float boost)
        {
            if (boost > 0f) variant += 10; // Downtown copies apart
            if (copies.TryGetValue((src, rule, variant), out var c)) return c;
            var rr = Rules[rule];
            c = new Material(src) { name = src.name + "_W86L" + variant, hideFlags = HideFlags.DontSave };
            if (rr.Smoothness >= 0f) c.SetFloat("_Smoothness", Mathf.Clamp01(rr.Smoothness + boost + (variant % 10 - 1) * rr.Vary));
            if (rr.Metallic >= 0f) c.SetFloat("_Metallic", rr.Metallic);
            if (c.HasProperty("_EnvironmentReflections")) { c.SetFloat("_EnvironmentReflections", 1f); c.DisableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            if (c.HasProperty("_SpecularHighlights")) { c.SetFloat("_SpecularHighlights", 1f); c.DisableKeyword("_SPECULARHIGHLIGHTS_OFF"); }
            // a gloss map would override the scalar: keep the map's pattern only on the glass/metal it was painted for
            if (c.IsKeywordEnabled("_METALLICSPECGLOSSMAP") && rr.Vary > 0f) c.DisableKeyword("_METALLICSPECGLOSSMAP");
            copies[(src, rule, variant)] = c;
            return c;
        }

        // one stable variant per building: the topmost transform under the district root
        static int Variant(Transform t)
        {
            Transform b = t;
            while (b.parent && b.parent.parent && !b.parent.name.StartsWith("district_")) b = b.parent;
            Vector3 p = b.position;
            uint h = (uint)Mathf.RoundToInt(p.x * 7.13f) * 73856093u ^ (uint)Mathf.RoundToInt(p.z * 5.71f) * 19349663u;
            return (int)(h % 3u);
        }

        // the District_* / district_* root above (lower case), or ""
        static string District(Transform t)
        {
            for (var p = t; p; p = p.parent) { string n = p.name.ToLowerInvariant(); if (n.StartsWith("district_")) return n; }
            return "";
        }

        void TuneLods()
        {
            int b = 0, k = 0;
            float kitWant = KitLod0Height * (BuildingLod0Height / Mathf.Max(.0001f, baseBuildingLod0 > 0f ? baseBuildingLod0 : BuildingLod0Height));
            foreach (var lg in FindObjectsByType<LODGroup>())
            {
                if (lockedTowers.Contains(lg)) continue;
                if (!originalLods.TryGetValue(lg, out var orig))
                {
                    if (lg.GetComponentInChildren<SkinnedMeshRenderer>(true)) continue; // NPC crowd LODs (opt_v02) stay as tuned
                    orig = lg.GetLODs();
                    if (orig.Length < 2) continue;
                    originalLods[lg] = orig;
                }
                var lods = (LOD[])orig.Clone(); // from the scene's own heights every time: repeated Apply never compounds
                bool building = lg.size >= 10f;
                float want = building ? BuildingLod0Height : kitWant;
                if (building && lods[0].screenRelativeTransitionHeight < want) { lods[0].screenRelativeTransitionHeight = want; b++; }
                else if (!building && lods[0].screenRelativeTransitionHeight > want) { lods[0].screenRelativeTransitionHeight = want; k++; }
                for (int i = 1; i < lods.Length; i++)
                    lods[i].screenRelativeTransitionHeight = Mathf.Min(lods[i].screenRelativeTransitionHeight, lods[i - 1].screenRelativeTransitionHeight * .5f);
                if (CrossFade) { lg.fadeMode = LODFadeMode.CrossFade; lg.animateCrossFading = true; }
                lg.SetLODs(lods);
            }
            TunedBuildings = b; TunedKits = k;
        }
        public int TunedBuildings { get; private set; }
        public int TunedKits { get; private set; }

        static string[] Split(string s) => string.IsNullOrEmpty(s) ? Array.Empty<string>() : s.ToLowerInvariant().Split('|');
        static bool Contains(string s, string[] keys) { foreach (var k in keys) if (k.Length > 0 && s.Contains(k)) return true; return false; }
        static bool InAny(Transform t, HashSet<Transform> roots) { for (var p = t; p; p = p.parent) if (roots.Contains(p)) return true; return false; }

        float lodBiasBefore = -1f;
        void ReflectionLodIn(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam != reflCam || lodBiasBefore >= 0f) return;
            lodBiasBefore = QualitySettings.lodBias; QualitySettings.lodBias = ReflectLodBias;
        }
        void ReflectionLodOut(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam != reflCam || lodBiasBefore < 0f) return;
            QualitySettings.lodBias = lodBiasBefore; lodBiasBefore = -1f;
        }

        // W86 (Fedya 25.10: the skyscraper shadow still shimmers in motion): the T4 twin towers are nested shells (glass body, spandrel
        // bands, mullion frame, crown) whose faces lie a few cm apart; all of them cast, so the shells shadow each other and the
        // acne crawls as the cascades follow the moving camera. Only the solid glass body (and the podium) casts now; the thin
        // shells still receive. The silhouette on the ground is the body's, unchanged.
        // Fedya's recording (25.10): the tower shadow pops in/out as the camera moves forward/back: the towers' LODGroup (LOD0 full,
        // LOD1 reduced) switches / cross-fades by distance, and its fade state is shared by every camera (the reflection camera runs
        // another LOD bias), so the casting set changes with the player's distance. The two towers are locked to LOD0: no LODGroup,
        // the LOD1-only pieces off. Two objects: negligible cost.
        void TowerShadowCasters()
        {
            foreach (var r in FindObjectsByType<MeshRenderer>())
                if (r.name == "Towers_T4_tower_spandrel" || r.name == "Towers_T4_tower_frame" || r.name == "Towers_T4_tower_crown")
                    r.shadowCastingMode = ShadowCastingMode.Off;
            foreach (var lg in FindObjectsByType<LODGroup>())
            {
                if (!lg.name.StartsWith("Sample_T4")) continue;
                var lods = lg.GetLODs(); if (lods.Length == 0) continue;
                var keep = new HashSet<Renderer>(lods[0].renderers.Where(r => r));
                for (int i = 1; i < lods.Length; i++) foreach (var r in lods[i].renderers) if (r && !keep.Contains(r)) r.enabled = false;
                lg.enabled = false;
                lockedTowers.Add(lg);
            }
        }
        readonly HashSet<LODGroup> lockedTowers = new();

        void BalanceLight(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam.cameraType != CameraType.Game || !Sun) return;
            float k = Mathf.InverseLerp(ClearSunRange.x, ClearSunRange.y, Sun.intensity);
            if (k <= 0f) return;
            Sun.intensity *= Mathf.Lerp(1f, SunBoost, k);
            Sun.shadowStrength = Mathf.Min(1f, Sun.shadowStrength + ShadowAdd * k);
            // the weather writes a flat SH (one colour from every side): keep its average, tilt it sky-above / ground-below
            var sh = RenderSettings.ambientProbe;
            var c = new Color(sh[0, 0], sh[1, 0], sh[2, 0]); // Unity keeps the L0 band as the flat colour itself
            float scale = Mathf.Lerp(1f, AmbientScale, k), grad = AmbientGradient * k;
            var outSh = new SphericalHarmonicsL2();
            outSh.AddAmbientLight(c * scale * (1f - grad * .35f));
            outSh.AddDirectionalLight(Vector3.up, c * scale * grad, 1f);
            RenderSettings.ambientProbe = outSh;
        }

        void OnDestroy()
        {
#if UNITY_EDITOR
            // the pipeline asset is a project file: in the editor put back what was there, so a low setting never lands in git
            if (savedRp && GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset rp)
            {
                rp.msaaSampleCount = savedMsaa; rp.shadowDistance = savedShadowDist; rp.mainLightShadowmapResolution = savedShadowRes;
                rp.renderScale = savedRenderScale; QualitySettings.globalTextureMipmapLimit = savedMipLimit; rp.cascadeBorder = savedBorder;
            }
#endif
            RenderPipelineManager.beginCameraRendering -= BalanceLight;
            RenderPipelineManager.beginCameraRendering -= ReflectionLodIn;
            RenderPipelineManager.endCameraRendering -= ReflectionLodOut;
            if (lodBiasBefore >= 0f) { QualitySettings.lodBias = lodBiasBefore; lodBiasBefore = -1f; }
            if (RenderSettings.customReflectionTexture == cube) RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            if (cube) { cube.Release(); Destroy(cube); }
            foreach (var c in copies.Values) if (c) Destroy(c);
        }
    }
}
