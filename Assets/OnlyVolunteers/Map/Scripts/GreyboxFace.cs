using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Smoothed blend shapes of the Sausage Buddy face (Blink, Surprised, Worried, Happy) plus random blinking.
    // The FBX carries the shapes but not the face track, so scripts drive the expressions. The body clips also key
    // the shapes (at zero), so the weights live here and Apply() writes them after the Animator, from LateUpdate.
    // TASK-000900: the NPC types have crowd LODs (Face = LOD0, also accepted as "Face_LOD0"; Face_LOD1 / Face_LOD2 keep the
    // shape keys): the weights are written to every level, matched by shape name (a level without a shape is skipped).
    public sealed class GreyboxFace
    {
        private readonly SkinnedMeshRenderer _face;
        private readonly Dictionary<string, int> _index = new();
        private readonly float[] _weights;
        private readonly List<(SkinnedMeshRenderer renderer, int[] shape)> _levels = new();
        private float _nextBlink;
        private float _blinkEnd;

        public GreyboxFace(GameObject root)
        {
            var levels = new List<SkinnedMeshRenderer>();
            foreach (SkinnedMeshRenderer r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = FaceLod(r.name);
                if (lod == 0) _face = r;
                else if (lod > 0) levels.Add(r);
            }
            if (_face == null) return;
            _weights = new float[_face.sharedMesh.blendShapeCount];
            for (int i = 0; i < _face.sharedMesh.blendShapeCount; i++)
                _index[_face.sharedMesh.GetBlendShapeName(i)] = i;
            foreach (SkinnedMeshRenderer r in levels)
            {
                if (r.sharedMesh == null) continue;
                var shape = new int[_weights.Length];
                bool any = false;
                for (int i = 0; i < shape.Length; i++)
                {
                    shape[i] = r.sharedMesh.GetBlendShapeIndex(_face.sharedMesh.GetBlendShapeName(i));
                    any |= shape[i] >= 0;
                }
                if (any) _levels.Add((r, shape));
            }
            _nextBlink = Time.time + Random.Range(1f, 4f);
        }

        // 0 = "Face" / "Face_LOD0", n = "Face_LODn", -1 = not the face.
        private static int FaceLod(string name)
        {
            if (name == "Face") return 0;
            if (name.Length > 8 && name.StartsWith("Face_LOD") && int.TryParse(name.Substring(8), out int lod)) return lod;
            return -1;
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
            foreach ((SkinnedMeshRenderer renderer, int[] shape) in _levels)
            {
                if (renderer == null) continue;
                for (int i = 0; i < shape.Length; i++)
                    if (shape[i] >= 0) renderer.SetBlendShapeWeight(shape[i], _weights[i]);
            }
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
