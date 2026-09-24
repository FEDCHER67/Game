using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    public static class GrabPhysicsSolver
    {
        public static bool TryCalculate(Rigidbody body, Vector3 localGrabPoint, Vector3 target,
            GrabPhysicsProfile profile, out Vector3 worldGrabPoint, out Vector3 force)
        {
            worldGrabPoint = body.transform.TransformPoint(localGrabPoint);
            Vector3 error = target - worldGrabPoint;
            if (!IsFinite(error) || error.sqrMagnitude > profile.BreakDistance * profile.BreakDistance)
            {
                force = Vector3.zero;
                return false;
            }

            return TryCalculate(error, body.GetPointVelocity(worldGrabPoint), body.mass, profile,
                out force);
        }

        public static bool TryCalculate(Vector3 error, Vector3 pointVelocity, float mass,
            GrabPhysicsProfile profile, out Vector3 force)
        {
            force = Vector3.zero;
            if (!IsFinite(error) || error.sqrMagnitude > profile.BreakDistance * profile.BreakDistance)
                return false;

            float damping = 2f * profile.DampingRatio *
                Mathf.Sqrt(profile.SpringStrength * Mathf.Max(0.01f, mass));
            Vector3 rawForce = error * profile.SpringStrength - pointVelocity * damping;
            if (!IsFinite(rawForce))
                return false;

            force = Vector3.ClampMagnitude(rawForce, profile.MaxForce);
            return true;
        }

        public static void ApplyForce(Rigidbody body, Vector3 worldGrabPoint, Vector3 force)
        {
            body.WakeUp();
            body.AddForceAtPosition(force, worldGrabPoint, ForceMode.Force);
        }

        public static void LimitVelocities(Rigidbody body, GrabPhysicsProfile profile)
        {
            if (body.linearVelocity.sqrMagnitude > profile.MaxLinearSpeed * profile.MaxLinearSpeed)
                body.linearVelocity = body.linearVelocity.normalized * profile.MaxLinearSpeed;
            if (body.angularVelocity.sqrMagnitude > profile.MaxAngularSpeed * profile.MaxAngularSpeed)
                body.angularVelocity = body.angularVelocity.normalized * profile.MaxAngularSpeed;
        }

        public static bool IsFinite(Vector3 value) =>
            !float.IsNaN(value.x) && !float.IsInfinity(value.x) &&
            !float.IsNaN(value.y) && !float.IsInfinity(value.y) &&
            !float.IsNaN(value.z) && !float.IsInfinity(value.z);
    }
}
