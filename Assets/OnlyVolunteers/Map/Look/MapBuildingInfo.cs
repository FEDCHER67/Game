using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // What a look building is, kept on its (collider-only) object after the render meshes are merged per district:
    // plan id, type, district, label and the world-space door poses for NPCs, interactions and spawns.
    public sealed class MapBuildingInfo : MonoBehaviour
    {
        public string Id, Kind, Type, District, Label, Style, SignText;
        public int Floors;
        public float Height, PadY;
        public Vector3[] Doors = new Vector3[0];
        public Quaternion[] DoorFacing = new Quaternion[0];
        public Vector2[] Footprint = new Vector2[0];
    }
}
