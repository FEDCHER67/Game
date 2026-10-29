using UnityEngine;

namespace OnlyVolunteers.Economy.Pharmacy
{
    /// <summary>
    /// Scene bookkeeping of the pharmacy site step (W85PlayIntegrator, step 8b): which map meshes of the host house 04-H3
    /// (and its facade kit / front garden) were replaced by cut copies, their original meshes, the objects switched off
    /// for the street path. The step restores all of it first on every run, then cuts again from the originals, so a rerun
    /// never cuts a cut mesh or leaves duplicates. No runtime behaviour.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PharmacySiteRecordV01 : MonoBehaviour
    {
        public MeshFilter[] Filters = new MeshFilter[0];
        public Mesh[] FilterOriginals = new Mesh[0];
        public MeshCollider[] Colliders = new MeshCollider[0];
        public Mesh[] ColliderOriginals = new Mesh[0];
        public GameObject[] Hidden = new GameObject[0];
        public BoxCollider[] Boxes = new BoxCollider[0];
        public Vector3[] BoxCentres = new Vector3[0];
        public Vector3[] BoxSizes = new Vector3[0];
        public bool[] BoxEnabled = new bool[0];
        [TextArea(3, 12)] public string Notes = "";
    }
}
