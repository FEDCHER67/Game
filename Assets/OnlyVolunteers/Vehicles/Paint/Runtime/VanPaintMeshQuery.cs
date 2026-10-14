using System;
using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    // Query the rendered triangles directly. No extra colliders or forces on the driving van.
    // Local-space vertices follow their original moving door transforms.
    public sealed class VanPaintMeshQuery : MonoBehaviour
    {
        [Serializable] public sealed class Part
        {
            public MeshFilter filter;
            public bool[] paintable;
            [NonSerialized] public Vector3[] vertices;
            [NonSerialized] public Vector2[] uv;
            [NonSerialized] public int[] triangles;
        }
        [SerializeField] Part[] parts;
        public void Configure(Part[] value) { parts = value; }
        public bool TryHit(Ray ray, float reach, out Vector2 uv)
        {
            uv = default; float best = reach; bool found = false;
            foreach (var part in parts)
            {
                if (part.filter == null || !part.filter.gameObject.activeInHierarchy) continue;
                Mesh mesh = part.filter.sharedMesh;
                // Meshes imported without Read/Write (the wheels) cannot be queried and are not paintable.
                if (mesh == null || !mesh.isReadable) continue;
                if (part.vertices == null) { part.vertices = mesh.vertices; part.uv = mesh.uv; part.triangles = mesh.triangles; }
                Matrix4x4 inv = part.filter.transform.worldToLocalMatrix;
                Vector3 origin = inv.MultiplyPoint3x4(ray.origin), direction = inv.MultiplyVector(ray.direction);
                if (!mesh.bounds.IntersectRay(new Ray(origin, direction))) continue;
                for (int i = 0; i < part.triangles.Length; i += 3)
                {
                    int a=part.triangles[i], b=part.triangles[i+1], c=part.triangles[i+2];
                    Vector3 e1=part.vertices[b]-part.vertices[a], e2=part.vertices[c]-part.vertices[a];
                    Vector3 p=Vector3.Cross(direction,e2); float det=Vector3.Dot(e1,p);
                    if (Mathf.Abs(det)<1e-8f) continue;
                    float inverse=1/det; Vector3 t=origin-part.vertices[a];
                    float u=Vector3.Dot(t,p)*inverse; if(u<0 || u>1) continue;
                    Vector3 q=Vector3.Cross(t,e1); float v=Vector3.Dot(direction,q)*inverse; if(v<0 || u+v>1) continue;
                    float distance=Vector3.Dot(e2,q)*inverse; if(distance<.001f || distance>=best) continue;
                    best=distance; found=part.paintable[i/3];
                    uv=part.uv[a]*(1-u-v)+part.uv[b]*u+part.uv[c]*v;
                }
            }
            if (!found) return false;
            // Preserve world obstruction (walls/NPCs), ignoring only this van's coarse physics hull.
            foreach(var hit in Physics.RaycastAll(ray,best,~0,QueryTriggerInteraction.Ignore))
                if (!hit.collider.transform.IsChildOf(transform)) return false;
            return true;
        }
    }
}
