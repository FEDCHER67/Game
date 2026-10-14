using UnityEngine;
namespace OnlyVolunteers.Sky22V05
{
    public abstract class SkyDistrictSource22 : MonoBehaviour
    {
        public virtual bool Ready => true;
        public abstract SkyMood22 Sample(Vector3 position);
        public virtual void AfterAtmosphere(Camera camera, SkyState22 state) { }
        public virtual void AfterCamera(Camera camera) { }
    }
}
