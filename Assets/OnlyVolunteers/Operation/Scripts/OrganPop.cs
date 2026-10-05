using System;
using UnityEngine;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// The extracted organ jumps up, spins, swells for a moment and then flies down toward the hotbar at the bottom of
    /// the view, where it "lands" in the inventory (the callback adds it). Pure presentation.
    /// </summary>
    public sealed class OrganPop : MonoBehaviour
    {
        private const float Seconds = 0.85f;

        private Camera view;
        private Vector3 from;
        private Vector3 baseScale;
        private Vector3 spin;
        private float time;
        private Action arrived;

        public static void Launch(Transform organ, Camera view, Action arrived)
        {
            var pop = organ.gameObject.AddComponent<OrganPop>();
            pop.view = view;
            pop.from = organ.position;
            pop.baseScale = organ.localScale;
            pop.spin = new Vector3(UnityEngine.Random.Range(300f, 600f), UnityEngine.Random.Range(-400f, 400f), 0f);
            pop.arrived = arrived;
        }

        private void Update()
        {
            time += Time.deltaTime;
            float t = Mathf.Clamp01(time / Seconds);
            // Target: just in front of the camera, low in the view (where the hotbar is).
            Vector3 to = view != null
                ? view.transform.position + view.transform.forward * 0.45f - view.transform.up * 0.22f
                : from + Vector3.up;
            Vector3 position = Vector3.Lerp(from, to, t * t);
            position += Vector3.up * Mathf.Sin(t * Mathf.PI) * 0.35f;
            transform.position = position;
            transform.Rotate(spin * Time.deltaTime, Space.Self);
            float swell = t < 0.35f ? Mathf.Lerp(1f, 1.6f, t / 0.35f) : Mathf.Lerp(1.6f, 0.15f, (t - 0.35f) / 0.65f);
            transform.localScale = baseScale * swell;
            if (t < 1f) return;
            arrived?.Invoke();
            arrived = null;
            Destroy(gameObject);
        }
    }
}
