using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Test-scene camera: smooth chase view behind the van, or first-person from the driver's seat.
    public sealed class VanCameraRig : MonoBehaviour
    {
        public enum Mode { Chase, Cockpit }

        public Transform Van;
        public Transform DriverEye;
        public Mode CurrentMode = Mode.Chase;
        public float ChaseDistance = 7.5f;
        public float ChaseHeight = 2.8f;
        public float ChaseLookHeight = 1.2f;
        public float ChaseSharpness = 6f;
        public float MouseSensitivity = 2.2f;

        private float _yawOffset;
        private float _pitch;

        public void ToggleMode()
        {
            CurrentMode = CurrentMode == Mode.Chase ? Mode.Cockpit : Mode.Chase;
            _yawOffset = 0f;
            _pitch = 0f;
        }

        private void LateUpdate()
        {
            if (Van == null) return;
            bool look = Cursor.lockState == CursorLockMode.Locked || Input.GetMouseButton(1);
            if (look)
            {
                _yawOffset += Input.GetAxisRaw("Mouse X") * MouseSensitivity;
                _pitch = Mathf.Clamp(_pitch - Input.GetAxisRaw("Mouse Y") * MouseSensitivity, -55f, 60f);
            }

            if (CurrentMode == Mode.Cockpit && DriverEye != null)
            {
                _yawOffset = Mathf.Clamp(_yawOffset, -120f, 120f);
                transform.SetPositionAndRotation(DriverEye.position,
                    Van.rotation * Quaternion.Euler(_pitch, _yawOffset, 0f));
                return;
            }

            if (!look)
                _yawOffset = Mathf.LerpAngle(_yawOffset, 0f, 1.5f * Time.deltaTime);
            float yaw = Van.eulerAngles.y + _yawOffset;
            Quaternion orbit = Quaternion.Euler(Mathf.Clamp(_pitch, -10f, 45f), yaw, 0f);
            Vector3 target = Van.position + Vector3.up * ChaseLookHeight;
            Vector3 desired = target + orbit * new Vector3(0f, ChaseHeight - ChaseLookHeight, -ChaseDistance);
            float k = 1f - Mathf.Exp(-ChaseSharpness * Time.deltaTime);
            transform.position = Vector3.Lerp(transform.position, desired, k);
            transform.rotation = Quaternion.LookRotation(target - transform.position, Vector3.up);
        }
    }
}
