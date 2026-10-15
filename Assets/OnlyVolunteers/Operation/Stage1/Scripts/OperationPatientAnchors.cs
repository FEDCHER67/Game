using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Imported incision transforms are the only source of anatomy positions and normals.</summary>
    public sealed class OperationPatientAnchors : MonoBehaviour
    {
        [SerializeField] private Transform[] incisions = new Transform[3];
        // FBX bones are in centimetres (lossy scale 100). Authored once from the import, never inferred from body coordinates.
        [SerializeField] private float markerUnitsPerMetre = 0.01f;
        public bool Valid => incisions.Length == 3 && incisions[0] != null && incisions[1] != null && incisions[2] != null;
        public Transform Marker(int organ) => incisions[organ];
        public Vector3 Point(int organ, Vector3 metres) => Marker(organ).TransformPoint(metres * markerUnitsPerMetre);
        public Vector3 LocalMetres(int organ, Vector3 world) => Marker(organ).InverseTransformPoint(world) / markerUnitsPerMetre;
        public Vector3 Normal(int organ) => Marker(organ).localToWorldMatrix.inverse.transpose.MultiplyVector(Vector3.forward).normalized;
    }
}
