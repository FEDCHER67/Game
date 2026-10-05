using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Third-person orbit camera for the grey-box walker. Left click locks the cursor and the mouse turns the view,
    // Esc frees the cursor; the camera is pulled in when a wall gets between it and the character.
    public sealed class GreyboxFollowCamera : MonoBehaviour
    {
        public Transform Target;
        public float Distance = 4.5f;
        public float Height = 1.6f;
        public float Sensitivity = 2.5f;

        private float _yaw;
        private float _pitch = 15f;

        public void SnapBehind(Transform t) => _yaw = t.eulerAngles.y;

        private void LateUpdate()
        {
            if (Target == null) return;
            if (Input.GetMouseButtonDown(0)) Cursor.lockState = CursorLockMode.Locked;
            if (Input.GetKeyDown(KeyCode.Escape)) Cursor.lockState = CursorLockMode.None;
            Cursor.visible = Cursor.lockState != CursorLockMode.Locked;
            if (Cursor.lockState == CursorLockMode.Locked || Input.GetMouseButton(1))
            {
                _yaw += Input.GetAxisRaw("Mouse X") * Sensitivity;
                _pitch = Mathf.Clamp(_pitch - Input.GetAxisRaw("Mouse Y") * Sensitivity, -20f, 70f);
            }

            Quaternion rotation = Quaternion.Euler(_pitch, _yaw, 0f);
            Vector3 pivot = Target.position + Vector3.up * Height;
            Vector3 back = rotation * Vector3.back;
            float distance = Distance;
            foreach (RaycastHit hit in Physics.SphereCastAll(pivot, 0.25f, back, Distance, ~(1 << OvLayers.VehicleInterior),
                         QueryTriggerInteraction.Ignore))
                if (!hit.transform.IsChildOf(Target) && hit.distance < distance)
                    distance = Mathf.Max(0.5f, hit.distance - 0.1f);
            transform.SetPositionAndRotation(pivot + back * distance, rotation);
        }
    }
}
