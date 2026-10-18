using System.Collections.Generic;
using OnlyVolunteers.Inventory;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>One size for an organ everywhere (Fedya 2026-10-18: the organ on the tray was smaller than in the body).
    /// The physical organ item (tray, hand, dropped) is fitted at runtime so its largest side equals its ItemDefinition's
    /// WorldModelSize (kidney 0.15 m, liver 0.22 m), which is also the inventory/drop size and matches the approved v02
    /// organ in the open belly (measured 0.147 / 0.221 m). The item prefabs' own model scale (organItemScale 0.7) made it
    /// 0.13 / 0.20 m.</summary>
    public static class OperationOrganSize
    {
        /// <summary>Largest side (world metres, along the first renderer's own axes) of the enabled mesh renderers under root.</summary>
        public static float LargestSide(Transform root)
        {
            var renderers = new List<Renderer>();
            foreach (var r in root.GetComponentsInChildren<Renderer>()) if (r.enabled && (r is MeshRenderer || r is SkinnedMeshRenderer)) renderers.Add(r);
            if (renderers.Count == 0) return 0f;
            Transform reference = renderers[0].transform;
            Vector3[] axes = { reference.right, reference.up, reference.forward };
            var min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue); var max = -min;
            foreach (var r in renderers)
            {
                Bounds b = r is SkinnedMeshRenderer s && s.sharedMesh != null ? s.sharedMesh.bounds : r.TryGetComponent(out MeshFilter f) && f.sharedMesh != null ? f.sharedMesh.bounds : r.localBounds;
                for (int c = 0; c < 8; c++)
                {
                    var corner = new Vector3((c & 1) == 0 ? b.min.x : b.max.x, (c & 2) == 0 ? b.min.y : b.max.y, (c & 4) == 0 ? b.min.z : b.max.z);
                    Vector3 w = r.transform.TransformPoint(corner);
                    for (int a = 0; a < 3; a++) { float d = Vector3.Dot(w, axes[a]); min[a] = Mathf.Min(min[a], d); max[a] = Mathf.Max(max[a], d); }
                }
            }
            return Mathf.Max(max.x - min.x, Mathf.Max(max.y - min.y, max.z - min.z));
        }

        /// <summary>Scales the item's model child (with its collider) so its largest side is 'size'. True when fitted.</summary>
        public static bool Fit(Transform item, float size)
        {
            if (item == null || size <= 0f) return false;
            Transform model = item.Find(ItemWorldModel.ChildName);
            if (model == null) return false;
            float current = LargestSide(model);
            if (current < 1e-4f) return false;
            float k = size / current;
            if (Mathf.Abs(k - 1f) > 0.005f) model.localScale *= k;
            return true;
        }
    }
}
