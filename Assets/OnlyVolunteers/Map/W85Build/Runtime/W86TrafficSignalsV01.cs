using System;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 traffic signal cycle (Fedya 25.10, screenshot 06): each head has three lens renderers; per junction the two road axes take
    // turns (green 9 s, amber 2.5 s, all red 1.5 s), junctions offset by a hash so the district does not switch in step. Swaps shared
    // on/off materials only (no per-frame allocations, batching kept); game time, so the pause menu stops it too.
    [DisallowMultipleComponent]
    public sealed class W86TrafficSignalsV01 : MonoBehaviour
    {
        [Serializable]
        public struct Head
        {
            public Renderer red, amber, green;
            public int junction;   // stable id per junction
            public int axis;       // 0 / 1: which road the head faces
        }

        public Head[] heads = Array.Empty<Head>();
        public Material redOn, redOff, amberOn, amberOff, greenOn, greenOff;
        public float green = 9f, amber = 2.5f, allRed = 1.5f;
        readonly System.Collections.Generic.Dictionary<int, int> lastState = new();

        void Update()
        {
            float half = green + amber + allRed, cycle = half * 2f;
            for (int i = 0; i < heads.Length; i++)
            {
                var h = heads[i];
                if (!h.red) continue;
                float t = Mathf.Repeat(Time.time + Hash(h.junction) * cycle + (h.axis == 1 ? half : 0f), cycle);
                int state = t < green ? 2 : t < green + amber ? 1 : 0; // 2 green, 1 amber, 0 red
                if (lastState.TryGetValue(i, out int was) && was == state) continue;
                lastState[i] = state;
                h.red.sharedMaterial = state == 0 ? redOn : redOff;
                h.amber.sharedMaterial = state == 1 ? amberOn : amberOff;
                h.green.sharedMaterial = state == 2 ? greenOn : greenOff;
            }
        }

        static float Hash(int n) => Mathf.Repeat(Mathf.Sin(n * 12.9898f + 4.1414f) * 43758.5453f, 1f);
    }
}
