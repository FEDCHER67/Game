using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // Style v3 light: the STYLE_BIBLE_v2 daylight (section 9.1: sun 45 deg from azimuth 225, #FFF4E4 x0.8, trilight
    // ambient, gradient sky, post without tonemapping) with the fog pulled in for the 750 m far clip (linear 160 -> 720 m
    // in the sky's horizon colour). Copies of the v2 trial sky and post profile live under LookV3/Lighting (the v2 files
    // stay untouched). PC_RPAsset_StyleV3 / PC_Renderer_StyleV3: copies of the trial pipeline with 2 shadow cascades,
    // 140 m shadows, MSAA 4x, depth + opaque textures (water) and SSAO; used for captures and the profile run.
    public static class V3Lighting
    {
        public const string Dir = V3Materials.Root + "/Lighting";
        public const string RpAsset = Dir + "/PC_RPAsset_StyleV3.asset";
        public const string RendererAsset = Dir + "/PC_Renderer_StyleV3.asset";
        public const float FarClip = 750f, FogStart = 160f, FogEnd = 720f, ShadowDistance = 140f;
        private const string V2 = "Assets/OnlyVolunteers/Art/StyleKit_v2/Lighting";
        // v17 (phase A, Fedya: "less bright, the earlier darker look was better"; One-Armed Robber gamut): warm low sun
        // (37 deg) with strong shadows, deeper desaturated zenith and a horizon haze the fog matches (separation from
        // 60 m, opaque by 400 m, far clip 460 m), ACES with less saturation, a touch more contrast and a warm balance.
        public const float FarClipV17 = 460f, FogStartV17 = 60f, FogEndV17 = 400f, ShadowDistanceV17 = 90f;
        public const string RpAssetV17 = Dir + "/PC_RPAsset_StyleV17.asset", SkyV17 = Dir + "/Look_Sky_v17.mat",
            SkyTexV17 = Dir + "/Look_Sky_v17_gradient.png", PostV17 = Dir + "/Look_PostFX_v17.asset";
        public static readonly Color FogV17 = new Color(0.705f, 0.737f, 0.753f);

        public static float FarClipFor(string revision) => MapLookBuilderV3.IsV17(revision) ? FarClipV17 : FarClip;

        public static Light Apply(Transform parent) => Apply(parent, MapLookBuilderV3.Revision);

        public static Light Apply(Transform parent, string revision)
        {
            if (MapLookBuilderV3.IsV17(revision)) return ApplyV17(parent);
            var sunGo = new GameObject("Sun");
            sunGo.transform.SetParent(parent, false);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = LookConvert.Color("#FFF4E4");
            sun.intensity = 0.8f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 1f;
            sunGo.transform.rotation = Quaternion.Euler(45f, 45f, 0f);
            sunGo.AddComponent<UniversalAdditionalLightData>();
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = LookConvert.Color("#ADC0E6");
            RenderSettings.ambientEquatorColor = LookConvert.Color("#CCD2DC");
            RenderSettings.ambientGroundColor = LookConvert.Color("#AAA294");
            RenderSettings.ambientIntensity = 1f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = LookConvert.Color("#D7E5F1");
            RenderSettings.fogStartDistance = FogStart;
            RenderSettings.fogEndDistance = FogEnd;
            Material sky = Copy<Material>(V2 + "/Look_Sky_v2.mat", Dir + "/Look_Sky_v3.mat");
            if (sky != null) RenderSettings.skybox = sky;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            RenderSettings.reflectionIntensity = 1f;
            var volumeGo = new GameObject("PostFX_v3");
            volumeGo.transform.SetParent(parent, false);
            var volume = volumeGo.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 1f;
            volume.sharedProfile = Copy<VolumeProfile>(V2 + "/Look_PostFX_v2.asset", Dir + "/Look_PostFX_v3.asset");
            return sun;
        }

        private static Light ApplyV17(Transform parent)
        {
            var sunGo = new GameObject("Sun");
            sunGo.transform.SetParent(parent, false);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = LookConvert.Color("#FFE3BE");
            sun.intensity = 1.05f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.85f;
            sunGo.transform.rotation = Quaternion.Euler(37f, 45f, 0f);
            sunGo.AddComponent<UniversalAdditionalLightData>();
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = LookConvert.Color("#8E9DB4");
            RenderSettings.ambientEquatorColor = LookConvert.Color("#9C9C95");
            RenderSettings.ambientGroundColor = LookConvert.Color("#6B6458");
            RenderSettings.ambientIntensity = 1f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = FogV17;
            RenderSettings.fogStartDistance = FogStartV17;
            RenderSettings.fogEndDistance = FogEndV17;
            RenderSettings.skybox = SkyMaterialV17();
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            RenderSettings.reflectionIntensity = 0.8f;
            var volumeGo = new GameObject("PostFX_v17");
            volumeGo.transform.SetParent(parent, false);
            var volume = volumeGo.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 1f;
            volume.sharedProfile = PostProfileV17();
            return sun;
        }

        // Equirect gradient (zenith -> horizon haze = fog colour -> ground haze), made once; Skybox/Panoramic like v3.
        public static Material SkyMaterialV17()
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(SkyV17);
            if (mat != null) return mat;
            LookAssetStore.EnsureFolder(Dir);
            if (AssetDatabase.LoadAssetAtPath<Texture2D>(SkyTexV17) == null)
            {
                const int w = 8, h = 512;
                var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                Color zen = LookConvert.Color("#4E6C93"), high = LookConvert.Color("#6F8BAD"), low = LookConvert.Color("#A3B3C1"),
                    hor = FogV17, below = LookConvert.Color("#A6ACAA"), ground = LookConvert.Color("#8F948C");
                for (int y = 0; y < h; y++)
                {
                    float v = (y + 0.5f) / h;              // 0 = nadir, 0.5 = horizon, 1 = zenith
                    float e = (v - 0.5f) * 2f;             // elevation -1..1
                    Color c;
                    if (e >= 0f)
                    {
                        if (e < 0.06f) c = Color.Lerp(hor, low, e / 0.06f);
                        else if (e < 0.35f) c = Color.Lerp(low, high, Mathf.SmoothStep(0f, 1f, (e - 0.06f) / 0.29f));
                        else c = Color.Lerp(high, zen, Mathf.SmoothStep(0f, 1f, (e - 0.35f) / 0.65f));
                    }
                    else c = Color.Lerp(hor, Color.Lerp(below, ground, Mathf.Clamp01(-e * 2f)), Mathf.Clamp01(-e * 6f));
                    for (int x = 0; x < w; x++) tex.SetPixel(x, y, c);
                }
                tex.Apply();
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(Application.dataPath, "..", SkyTexV17), tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(SkyTexV17);
                if (AssetImporter.GetAtPath(SkyTexV17) is TextureImporter ti)
                {
                    ti.wrapModeU = TextureWrapMode.Repeat;
                    ti.wrapModeV = TextureWrapMode.Clamp;
                    ti.mipmapEnabled = false;
                    ti.textureCompression = TextureImporterCompression.Uncompressed;
                    ti.SaveAndReimport();
                }
            }
            Material v3 = Copy<Material>(V2 + "/Look_Sky_v2.mat", Dir + "/Look_Sky_v3.mat");
            mat = v3 != null ? new Material(v3) : new Material(Shader.Find("Skybox/Panoramic"));
            mat.name = "Look_Sky_v17";
            mat.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(SkyTexV17));
            mat.SetColor("_Tint", new Color(0.5f, 0.5f, 0.5f, 0.5f));
            mat.SetFloat("_Exposure", 1f);
            AssetDatabase.CreateAsset(mat, SkyV17);
            return mat;
        }

        // Copy of the v3 post profile, then ACES, saturation -15, contrast +8, warm white balance, softer bloom.
        public static VolumeProfile PostProfileV17()
        {
            var prof = AssetDatabase.LoadAssetAtPath<VolumeProfile>(PostV17);
            if (prof != null) return prof;
            VolumeProfile v3 = Copy<VolumeProfile>(V2 + "/Look_PostFX_v2.asset", Dir + "/Look_PostFX_v3.asset");
            if (v3 != null) AssetDatabase.CopyAsset(Dir + "/Look_PostFX_v3.asset", PostV17);
            prof = AssetDatabase.LoadAssetAtPath<VolumeProfile>(PostV17);
            if (prof == null)
            {
                prof = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(prof, PostV17);
            }
            T Get<T>() where T : VolumeComponent
            {
                if (!prof.TryGet(out T c))
                {
                    c = prof.Add<T>(false);
                    c.name = typeof(T).Name;
                    AssetDatabase.AddObjectToAsset(c, prof);
                }
                c.active = true;
                return c;
            }
            var tm = Get<Tonemapping>();
            tm.mode.Override(TonemappingMode.ACES);
            var ca = Get<ColorAdjustments>();
            ca.postExposure.Override(0.15f);
            ca.contrast.Override(8f);
            ca.saturation.Override(-15f);
            var wb = Get<WhiteBalance>();
            wb.temperature.Override(8f);
            wb.tint.Override(0f);
            var bloom = Get<Bloom>();
            bloom.intensity.Override(0.15f);
            bloom.threshold.Override(1.2f);
            EditorUtility.SetDirty(prof);
            AssetDatabase.SaveAssets();
            return prof;
        }

        // The v17 capture pipeline: the v3 asset settings with 90 m shadows (2 cascades). The game's own PC_RPAsset is
        // project-wide (not per revision) and is not touched.
        public static UniversalRenderPipelineAsset PipelineV17()
        {
            UniversalRenderPipelineAsset v3 = Pipeline();
            var rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(RpAssetV17);
            if (rp == null)
            {
                AssetDatabase.CopyAsset(RpAsset, RpAssetV17);
                rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(RpAssetV17);
            }
            rp.shadowCascadeCount = 2;
            rp.cascade2Split = 0.25f;
            rp.shadowDistance = ShadowDistanceV17;
            rp.supportsCameraDepthTexture = true;
            rp.supportsCameraOpaqueTexture = true;
            rp.msaaSampleCount = 4;
            rp.supportsHDR = true;
            EditorUtility.SetDirty(rp);
            AssetDatabase.SaveAssetIfDirty(rp);
            return rp;
        }

        public static UniversalRenderPipelineAsset PipelineFor(string revision) => MapLookBuilderV3.IsV17(revision) ? PipelineV17() : Pipeline();

        private static T Copy<T>(string from, string to) where T : Object
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(to);
            if (existing != null) return existing;
            LookAssetStore.EnsureFolder(Dir);
            if (AssetDatabase.LoadAssetAtPath<T>(from) == null) return null;
            AssetDatabase.CopyAsset(from, to);
            return AssetDatabase.LoadAssetAtPath<T>(to);
        }

        // The v3 render pipeline asset (made once from the v2 trial copy; settings re-applied every call).
        public static UniversalRenderPipelineAsset Pipeline()
        {
            LookAssetStore.EnsureFolder(Dir);
            var rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererAsset);
            if (rendererData == null)
            {
                AssetDatabase.CopyAsset(V2 + "/PC_Renderer_StyleTrial_v2.asset", RendererAsset);
                rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererAsset);
            }
            var rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(RpAsset);
            if (rp == null)
            {
                AssetDatabase.CopyAsset(V2 + "/PC_RPAsset_StyleTrial_v2.asset", RpAsset);
                rp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(RpAsset);
                var so = new SerializedObject(rp);
                SerializedProperty list = so.FindProperty("m_RendererDataList");
                if (list != null && list.arraySize > 0) list.GetArrayElementAtIndex(0).objectReferenceValue = rendererData;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            rp.shadowCascadeCount = 2;
            rp.cascade2Split = 0.2f;
            rp.shadowDistance = ShadowDistance;
            rp.supportsCameraDepthTexture = true;
            rp.supportsCameraOpaqueTexture = true;
            rp.msaaSampleCount = 4;
            rp.supportsHDR = true;
            EditorUtility.SetDirty(rp);
            AssetDatabase.SaveAssetIfDirty(rp);
            return rp;
        }
    }
}
