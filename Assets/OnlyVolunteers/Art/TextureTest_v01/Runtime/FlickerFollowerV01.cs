using UnityEngine;

namespace OnlyVolunteers.Art.TextureTest
{
    // Functional street light that follows the existing i10 worn-lamp flicker: DistrictLife19V02 drives `source` (0.65 on /
    // 0.025 off) and SkyMapNight22I03 enables it at night; this copies the on/off state and the relative intensity to the
    // stronger, shadow-casting spot `target`, so the light pool and its shadows flicker together with the lamp.
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class FlickerFollowerV01 : MonoBehaviour
    {
        public Light source, target;
        public float sourceOn = .65f, targetOn = 60f;

        void LateUpdate() => Sync();

        public void Sync()
        {
            if (!source || !target) return;
            target.enabled = source.enabled && source.gameObject.activeInHierarchy;
            target.intensity = targetOn * Mathf.Clamp01(source.intensity / Mathf.Max(.001f, sourceOn));
        }
    }
}
