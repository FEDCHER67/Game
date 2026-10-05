using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look
{
    // Fixed late-afternoon light of the look bible: warm sun #FFE3B8 x1.6 at 32 degrees elevation from the south-west
    // (azimuth 235), soft shadows at 0.85, gradient ambient, linear haze, procedural sky, light post (bloom 0.15,
    // vignette 0.2, +5 warmth). Shadow distance lives in the URP asset (project-wide), so it is not touched here.
    public static class MapLookLighting
    {
        public const float SunElevation = 32f, SunAzimuth = 235f, FogStart = 250f, FogEnd = 1100f;

        public static Light Apply(Transform parent)
        {
            var sunGo = new GameObject("Sun");
            sunGo.transform.SetParent(parent, false);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = LookConvert.Color("#FFE3B8");
            sun.intensity = 1.6f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.85f;
            // The light travels away from the sun: azimuth of travel = sun azimuth - 180 (from north, clockwise).
            sunGo.transform.rotation = Quaternion.Euler(SunElevation, SunAzimuth - 180f, 0f);

            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = Color.Lerp(LookConvert.Color("#6FA7D6"), LookConvert.Color("#BFC9D6"), 0.5f);
            RenderSettings.ambientEquatorColor = LookConvert.Color("#D9E6EC") * 0.85f;
            RenderSettings.ambientGroundColor = LookConvert.Color("#8E9A7C") * 0.7f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = LookConvert.Color("#D7DFE3");
            RenderSettings.fogStartDistance = FogStart;
            RenderSettings.fogEndDistance = FogEnd;
            Material sky = Sky();
            if (sky != null) RenderSettings.skybox = sky;

            var volumeGo = new GameObject("PostFX");
            volumeGo.transform.SetParent(parent, false);
            var volume = volumeGo.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 1f;
            volume.sharedProfile = Profile();
            return sun;
        }

        private static Material Sky()
        {
            string path = LookAssetStore.MaterialDir + "/Look_Sky.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                Shader shader = Shader.Find("Skybox/Procedural");
                if (shader == null) return null;
                mat = new Material(shader) { name = "Look_Sky" };
                LookAssetStore.EnsureFolder(LookAssetStore.MaterialDir);
                AssetDatabase.CreateAsset(mat, path);
            }
            if (mat.HasProperty("_SkyTint")) mat.SetColor("_SkyTint", LookConvert.Color("#6FA7D6"));
            if (mat.HasProperty("_GroundColor")) mat.SetColor("_GroundColor", LookConvert.Color("#D9E6EC"));
            if (mat.HasProperty("_AtmosphereThickness")) mat.SetFloat("_AtmosphereThickness", 0.75f);
            if (mat.HasProperty("_Exposure")) mat.SetFloat("_Exposure", 1.15f);
            if (mat.HasProperty("_SunSize")) mat.SetFloat("_SunSize", 0.035f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static VolumeProfile Profile()
        {
            string path = LookAssetStore.MaterialDir + "/Look_PostFX.asset";
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
            if (profile == null)
            {
                LookAssetStore.EnsureFolder(LookAssetStore.MaterialDir);
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, path);
            }
            Get<Bloom>(profile).intensity.Override(0.15f);
            Vignette vignette = Get<Vignette>(profile);
            vignette.intensity.Override(0.2f);
            vignette.smoothness.Override(0.4f);
            Get<WhiteBalance>(profile).temperature.Override(5f);
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            return profile;
        }

        // Existing override or a new one saved inside the profile asset (otherwise it would not survive a reload).
        private static T Get<T>(VolumeProfile profile) where T : VolumeComponent
        {
            if (profile.TryGet(out T existing)) return existing;
            T added = profile.Add<T>(true);
            added.name = typeof(T).Name;
            AssetDatabase.AddObjectToAsset(added, profile);
            return added;
        }
    }
}
