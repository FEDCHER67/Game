using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Keeps grey-box labels facing the active camera.
    public sealed class GreyboxBillboard : MonoBehaviour
    {
        private void LateUpdate()
        {
            Camera cam = Camera.main;
            if (cam != null)
                transform.rotation = Quaternion.LookRotation(transform.position - cam.transform.position);
        }
    }
}
