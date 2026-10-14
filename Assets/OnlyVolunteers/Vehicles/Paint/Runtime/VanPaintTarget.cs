using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    [RequireComponent(typeof(MeshCollider))]
    public sealed class VanPaintTarget : MonoBehaviour
    {
        [SerializeField] VanPaintSurface surface;
        [SerializeField] bool[] paintableTriangles;
        public VanPaintSurface Surface => surface;
        public void Configure(VanPaintSurface owner, bool[] allowed) { surface = owner; paintableTriangles = allowed; }
        public bool Accepts(int triangle) => triangle >= 0 && triangle < paintableTriangles.Length && paintableTriangles[triangle];
    }
}
