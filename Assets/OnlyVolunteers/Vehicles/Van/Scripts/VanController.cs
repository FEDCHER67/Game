using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Wheel-collider driving for the van. Input is supplied through Throttle/Steer/Handbrake
    // by a separate input component, so the same controller can later be driven over the network.
    [RequireComponent(typeof(Rigidbody))]
    public sealed class VanController : MonoBehaviour
    {
        [System.Serializable]
        public sealed class Axle
        {
            public WheelCollider Left;
            public WheelCollider Right;
            public Transform LeftVisual;
            public Transform RightVisual;
            public bool Steering;
            public bool Motor;
            public bool Handbrake;
            [HideInInspector] public Quaternion LeftOffset = Quaternion.identity;
            [HideInInspector] public Quaternion RightOffset = Quaternion.identity;
        }

        public Axle Front = new() { Steering = true, Motor = true };
        public Axle Rear = new() { Handbrake = true };
        public Vector3 CenterOfMass = new(0f, 0.55f, -0.1f);

        [Header("Drive")]
        public float MotorTorque = 1250f;
        public float MaxSpeedKmh = 105f;
        public float ReverseSpeedKmh = 25f;
        public float BrakeTorque = 4200f;
        public float HandbrakeTorque = 6000f;
        public float CoastBrakeTorque = 120f;

        [Header("Steering")]
        public float MaxSteerAngle = 34f;
        public float HighSpeedSteerAngle = 11f;
        public float SteerSpeed = 3.5f;
        public Transform SteeringWheel;
        [Tooltip("Steering column axis in van-local space.")]
        public Vector3 SteeringWheelAxis = new(0f, 0.469f, -0.883f);
        public float SteeringWheelMaxDegrees = 300f;

        [Header("Stability")]
        public float AntiRoll = 9000f;
        public float Downforce = 25f;
        [Range(0.3f, 1f)] public float HandbrakeRearGrip = 0.55f;

        public float Throttle { get; set; }
        public float Steer { get; set; }
        public bool Handbrake { get; set; }
        public float SpeedKmh => Vector3.Dot(_body.linearVelocity, transform.forward) * 3.6f;

        private Rigidbody _body;
        private float _steer;
        private Quaternion _steeringWheelBase;
        private float _rearSidewaysStiffness;

        private void Awake()
        {
            _body = GetComponent<Rigidbody>();
            _body.centerOfMass = CenterOfMass;
            CacheVisualOffsets(Front);
            CacheVisualOffsets(Rear);
            if (SteeringWheel != null)
                _steeringWheelBase = SteeringWheel.localRotation;
            if (Rear.Left != null)
                _rearSidewaysStiffness = Rear.Left.sidewaysFriction.stiffness;
        }

        private static void CacheVisualOffsets(Axle axle)
        {
            if (axle.Left != null && axle.LeftVisual != null)
                axle.LeftOffset = Quaternion.Inverse(axle.Left.transform.rotation) * axle.LeftVisual.rotation;
            if (axle.Right != null && axle.RightVisual != null)
                axle.RightOffset = Quaternion.Inverse(axle.Right.transform.rotation) * axle.RightVisual.rotation;
        }

        private void FixedUpdate()
        {
            float speed = SpeedKmh;
            float throttle = Mathf.Clamp(Throttle, -1f, 1f);

            // W accelerates forward; S brakes while rolling forward, then reverses. Symmetric for reverse.
            float motor = 0f;
            float brake = 0f;
            if (throttle > 0.01f)
            {
                if (speed < -1f) brake = BrakeTorque * throttle;
                else if (speed < MaxSpeedKmh) motor = MotorTorque * throttle;
            }
            else if (throttle < -0.01f)
            {
                if (speed > 1f) brake = BrakeTorque * -throttle;
                else if (speed > -ReverseSpeedKmh) motor = MotorTorque * 0.7f * throttle;
            }
            else
            {
                brake = CoastBrakeTorque;
            }

            float speedT = Mathf.InverseLerp(10f, 90f, Mathf.Abs(speed));
            float maxAngle = Mathf.Lerp(MaxSteerAngle, HighSpeedSteerAngle, speedT);
            _steer = Mathf.MoveTowards(_steer, Mathf.Clamp(Steer, -1f, 1f), SteerSpeed * Time.fixedDeltaTime);

            ApplyAxle(Front, motor, brake, _steer * maxAngle);
            ApplyAxle(Rear, motor, brake, _steer * maxAngle);
            ApplyAntiRoll(Front);
            ApplyAntiRoll(Rear);
            _body.AddForce(-transform.up * Downforce * _body.linearVelocity.magnitude);
        }

        private void ApplyAxle(Axle axle, float motor, float brake, float steerAngle)
        {
            ApplyWheel(axle, axle.Left, motor, brake, steerAngle);
            ApplyWheel(axle, axle.Right, motor, brake, steerAngle);
        }

        private void ApplyWheel(Axle axle, WheelCollider w, float motor, float brake, float steerAngle)
        {
            if (w == null) return;
            w.motorTorque = axle.Motor ? motor * 0.5f : 0f;
            w.brakeTorque = brake + (axle.Handbrake && Handbrake ? HandbrakeTorque : 0f);
            if (axle.Steering) w.steerAngle = steerAngle;
            if (axle.Handbrake)
            {
                WheelFrictionCurve side = w.sidewaysFriction;
                side.stiffness = _rearSidewaysStiffness * (Handbrake ? HandbrakeRearGrip : 1f);
                w.sidewaysFriction = side;
            }
        }

        private void ApplyAntiRoll(Axle axle)
        {
            if (axle.Left == null || axle.Right == null) return;
            float travelL = Travel(axle.Left, out bool groundedL);
            float travelR = Travel(axle.Right, out bool groundedR);
            float force = (travelL - travelR) * AntiRoll;
            if (groundedL) _body.AddForceAtPosition(axle.Left.transform.up * -force, axle.Left.transform.position);
            if (groundedR) _body.AddForceAtPosition(axle.Right.transform.up * force, axle.Right.transform.position);
        }

        private static float Travel(WheelCollider w, out bool grounded)
        {
            grounded = w.GetGroundHit(out WheelHit hit);
            if (!grounded) return 1f;
            return (-w.transform.InverseTransformPoint(hit.point).y - w.radius) / w.suspensionDistance;
        }

        private void LateUpdate()
        {
            SyncVisuals(Front);
            SyncVisuals(Rear);
            if (SteeringWheel != null)
            {
                Vector3 axis = SteeringWheel.parent.InverseTransformDirection(transform.TransformDirection(SteeringWheelAxis));
                SteeringWheel.localRotation = Quaternion.AngleAxis(-_steer * SteeringWheelMaxDegrees, axis) * _steeringWheelBase;
            }
        }

        private static void SyncVisuals(Axle axle)
        {
            Sync(axle.Left, axle.LeftVisual, axle.LeftOffset);
            Sync(axle.Right, axle.RightVisual, axle.RightOffset);
        }

        private static void Sync(WheelCollider w, Transform visual, Quaternion offset)
        {
            if (w == null || visual == null) return;
            w.GetWorldPose(out Vector3 pos, out Quaternion rot);
            visual.SetPositionAndRotation(pos, rot * offset);
        }

        public void ResetUpright(Vector3 position, float yawDegrees)
        {
            _body.linearVelocity = Vector3.zero;
            _body.angularVelocity = Vector3.zero;
            _body.position = position;
            _body.rotation = Quaternion.Euler(0f, yawDegrees, 0f);
            transform.SetPositionAndRotation(position, _body.rotation);
        }
    }
}
