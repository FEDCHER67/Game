using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Smoothed blend shapes of the Sausage Buddy face (Blink, Surprised, Worried, Happy) plus random blinking.
    // The FBX carries the shapes but not the face track, so scripts drive the expressions. The body clips also key
    // the shapes (at zero), so the weights live here and Apply() writes them after the Animator, from LateUpdate.
    public sealed class GreyboxFace
    {
        private readonly SkinnedMeshRenderer _face;
        private readonly Dictionary<string, int> _index = new();
        private readonly float[] _weights;
        private float _nextBlink;
        private float _blinkEnd;

        public GreyboxFace(GameObject root)
        {
            foreach (SkinnedMeshRenderer r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (r.name == "Face") _face = r;
            if (_face == null) return;
            _weights = new float[_face.sharedMesh.blendShapeCount];
            for (int i = 0; i < _face.sharedMesh.blendShapeCount; i++)
                _index[_face.sharedMesh.GetBlendShapeName(i)] = i;
            _nextBlink = Time.time + Random.Range(1f, 4f);
        }

        public void Set(string shape, float target, float speedPerSecond = 500f)
        {
            if (_face == null || !_index.TryGetValue(shape, out int i)) return;
            _weights[i] = Mathf.MoveTowards(_weights[i], target, speedPerSecond * Time.deltaTime);
        }

        public void Apply()
        {
            if (_face == null) return;
            for (int i = 0; i < _weights.Length; i++)
                _face.SetBlendShapeWeight(i, _weights[i]);
        }

        public void TickBlink()
        {
            if (Time.time >= _nextBlink)
            {
                _blinkEnd = Time.time + 0.12f;
                _nextBlink = Time.time + Random.Range(2f, 5f);
            }
            Set("Blink", Time.time < _blinkEnd ? 100f : 0f, 1500f);
        }
    }
}
