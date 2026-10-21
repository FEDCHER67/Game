using System.Collections.Generic;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // Distance culling for the W85 crowd (FPS, 21.10): the play scene runs ~50 walkers over 7 districts at once; measured in the editor
    // at a meadow spot 76 fps with the crowd vs 100 fps without it — all 50 animators were AlwaysAnimate and every skinned mesh
    // (NPC types up to 99 k triangles, no LODs) was skinned every frame, even 700 m away. Walkers beyond HideBeyond metres from the
    // camera get their renderers and animator switched off (they keep walking their routes); closer walkers animate with
    // CullUpdateTransforms. Only objects that still carry a CrowdWalker are touched: a stunned / captured NPC (CrowdWalker released)
    // is always shown again.
    public sealed class W85CrowdCull : MonoBehaviour
    {
        public float HideBeyond = 190f, ShowWithin = 170f, Interval = .25f;
        float next;
        readonly Dictionary<GameObject, (Renderer[] r, Animator a, bool shown)> seen = new();
        readonly List<GameObject> drop = new();

        void Update()
        {
            if (Time.unscaledTime < next) return;
            next = Time.unscaledTime + Interval;
            var cam = Camera.main;
            if (!cam) return;
            Vector3 cp = cam.transform.position;
            foreach (var w in FindObjectsByType<CrowdWalker>(FindObjectsInactive.Exclude))
            {
                var go = w.gameObject;
                if (!seen.TryGetValue(go, out var e))
                {
                    e = (go.GetComponentsInChildren<Renderer>(true), go.GetComponentInChildren<Animator>(true), true);
                    if (e.a) e.a.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
                }
                float d2 = (go.transform.position - cp).sqrMagnitude;
                bool show = e.shown ? d2 < HideBeyond * HideBeyond : d2 < ShowWithin * ShowWithin;
                if (show != e.shown) { Apply(e.r, e.a, show); e.shown = show; }
                seen[go] = e;
            }
            drop.Clear();
            foreach (var kv in seen)
                if (!kv.Key || !kv.Key.GetComponent<CrowdWalker>()) { if (kv.Key && !kv.Value.shown) Apply(kv.Value.r, kv.Value.a, true); drop.Add(kv.Key); }
            foreach (var k in drop) seen.Remove(k);
        }

        static void Apply(Renderer[] rs, Animator a, bool on)
        {
            foreach (var r in rs) if (r) r.enabled = on;
            if (a) a.enabled = on;
        }

        void OnDisable()
        {
            foreach (var kv in seen) if (kv.Key && !kv.Value.shown) Apply(kv.Value.r, kv.Value.a, true);
            seen.Clear();
        }
    }
}
