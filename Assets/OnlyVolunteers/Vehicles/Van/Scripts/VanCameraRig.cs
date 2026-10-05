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
        // Chase view obstruction: a sphere this big from the look point to the camera stops short of walls, terrain, the
        // bridge deck and props; never closer than MinDistance. The van, its cargo-bay volumes, the player and NPCs do not
        // count (layer names as in OvLayers / VanInteriorColliders, so the van keeps no dependency on the map code).
        private const float CollisionRadius = 0.25f, CollisionSkin = 0.1f, MinDistance = 0.5f;
        private int _blockMask;

        private void Awake() =>
            _blockMask = ~LayerMask.GetMask("Vehicle", "VehicleInterior", "Player", "NpcBody", "NpcSeated");

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
            bool pulledIn = Unobstructed(target, ref desired);
            float k = 1f - Mathf.Exp(-ChaseSharpness * Time.deltaTime);
            Vector3 next = Vector3.Lerp(transform.position, desired, k);
            // Pulled in by a wall closer than the smoothed camera: snap there instead of gliding through the wall. Else the
            // smoothed path itself can cut through a corner (turning in a narrow street, cockpit to chase by a facade).
            if (pulledIn && (desired - target).sqrMagnitude < (next - target).sqrMagnitude) next = desired;
            else Unobstructed(target, ref next);
            transform.position = next;
            transform.rotation = Quaternion.LookRotation(target - transform.position, Vector3.up);
        }

        // Moves 'camera' toward 'target' to just short of the first obstruction between them; true if it moved.
        private bool Unobstructed(Vector3 target, ref Vector3 camera)
        {
            Vector3 offset = camera - target;
            float distance = offset.magnitude;
            if (distance < 0.01f) return false;
            Vector3 dir = offset / distance;
            if (!Physics.SphereCast(target, CollisionRadius, dir, out RaycastHit hit, distance, _blockMask, QueryTriggerInteraction.Ignore))
                return false;
            camera = target + dir * Mathf.Max(MinDistance, hit.distance - CollisionSkin);
            return true;
        }
    }
}
