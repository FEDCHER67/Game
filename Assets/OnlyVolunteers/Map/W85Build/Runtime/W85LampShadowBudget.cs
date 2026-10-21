using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // N-R3 street light on every urban lamp (Fedya 21.10: dimmer, shadowed, flickering): each lamp has a functional spot under its head
    // (FlickerFollowerV01 switches it with the flicker). Soft shadows from all of them at night would cost one shadow-map pass per lit
    // spot, so only the MaxShadowed lit spots nearest to the camera cast shadows (re-sorted 4 times a second); the others keep their
    // light without shadows. By day all spots are off and this only walks the array.
    [DisallowMultipleComponent]
    public sealed class W85LampShadowBudget : MonoBehaviour
    {
        public Light[] Spots = new Light[0];
        public int MaxShadowed = 8;
        public float Interval = .25f;
        float next;
        readonly List<(float d, Light l)> lit = new();

        void Update()
        {
            if (Time.unscaledTime < next) return;
            next = Time.unscaledTime + Interval;
            var cam = Camera.main;
            if (!cam) return;
            Vector3 cp = cam.transform.position;
            lit.Clear();
            foreach (var l in Spots)
            {
                if (!l) continue;
                if (l.enabled) lit.Add(((l.transform.position - cp).sqrMagnitude, l));
                else if (l.shadows != LightShadows.None) l.shadows = LightShadows.None;
            }
            lit.Sort((a, b) => a.d.CompareTo(b.d));
            for (int i = 0; i < lit.Count; i++)
            {
                var want = i < MaxShadowed ? LightShadows.Soft : LightShadows.None;
                if (lit[i].l.shadows != want) lit[i].l.shadows = want;
            }
        }
    }
}
