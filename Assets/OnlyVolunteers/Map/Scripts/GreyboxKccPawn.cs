using System.Reflection;
using KinematicCharacterController;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Player;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Lets Vadim's first-person KCC player (Player_KCC_Baseline) be the grey-box pawn. Added only to the prefab instance in
    // our scene; his prefab and scripts stay untouched. Out of control = the whole player is inactive (no capsule left in
    // the van, no second camera or listener). Teleports go through the motor: the KCC system puts a moved transform back.
    [RequireComponent(typeof(KccFirstPersonInput))]
    public sealed class GreyboxKccPawn : GreyboxPawn
    {
        // The view direction is private in KccFirstPersonInput (read once in Awake); NetworkPlayer sets it the same way.
        private static readonly FieldInfo YawField = typeof(KccFirstPersonInput).GetField("_yaw", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly FieldInfo PitchField = typeof(KccFirstPersonInput).GetField("_pitch", BindingFlags.Instance | BindingFlags.NonPublic);

        [Tooltip("Capsule radius of the map player (Vadim's prefab: 0.5). 0.35 lets a crouched player pass between the van's " +
                 "wheel arches (1.04 m). Applied at runtime to this instance only; <= 0 keeps the prefab's size.")]
        public float CapsuleRadius = 0.35f;

        [Header("Footsteps (optional, Sfx)")]
        [Tooltip("Metres between footfalls at walking speed (WalkSpeed) and at a sprint (RunSpeed); lerped between. The " +
                 "KCC player walks 4.7 m/s and sprints 8.2 m/s (KccFirstPersonInput): about 2.4 and 3 steps a second.")]
        public float StepLength = 2f;
        public float RunStepLength = 2.75f;
        public float WalkSpeed = 4.7f;
        public float RunSpeed = 8.2f;
        [Tooltip("Volume of a crouched step (sneaking), against 1 for a sprint.")]
        [Range(0f, 1f)] public float CrouchVolume = 0.4f;
        [Tooltip("m/s of fall speed for a full-volume landing step.")]
        public float LandingSpeed = 5f;

        private KccFirstPersonInput _kcc;
        private float _stepDistance;
        private bool _wasGrounded = true;
        private float _fallSpeed;

        private KccFirstPersonInput Kcc => _kcc != null ? _kcc : _kcc = GetComponent<KccFirstPersonInput>();

        // The radius lives here, not as a default in ExampleCharacterController: his other scenes keep their 0.5 capsule.
        // ApplyCapsuleRadius works whichever Awake (this, the character's, the motor's) runs first.
        private void Awake()
        {
            if (CapsuleRadius > 0f && Kcc != null && Kcc.Character != null)
                Kcc.Character.ApplyCapsuleRadius(CapsuleRadius);
        }

        // After every Awake: the motor builds CollidableLayers from the layer matrix in its own Awake, where Player x
        // VehicleInterior is off. The van's step ramps live on VehicleInterior (PhysX ignores that layer, so only queries
        // see them): this player's motor walks on them, Vadim's prefabs and other scenes are untouched. Nothing else uses
        // that layer as a collider (the cargo-bay volumes are maths, VanCargoSpace). The KCC cannot step onto the van's
        // own colliders (a dynamic rigidbody: no step handling there), hence ramps rather than MaxStepHeight.
        private void Start()
        {
            KinematicCharacterMotor motor = Kcc != null && Kcc.Character != null ? Kcc.Character.Motor : null;
            if (motor != null) motor.CollidableLayers |= 1 << OvLayers.VehicleInterior;
        }

        // Footfalls by distance walked on stable ground, the surface under the feet picking the sound (SfxSurfaces:
        // the van's metal, a Terrain's splat layer, a material name); a landing is one louder step. Reads the motor only.
        private void Update()
        {
            KinematicCharacterMotor motor = Kcc != null && Kcc.Character != null ? Kcc.Character.Motor : null;
            if (motor == null || Driving) return;
            bool grounded = motor.GroundingStatus.IsStableOnGround;
            Vector3 velocity = motor.BaseVelocity;
            if (!grounded)
            {
                _fallSpeed = Mathf.Max(_fallSpeed, -Vector3.Dot(velocity, motor.CharacterUp));
                _wasGrounded = false;
                return;
            }
            if (!_wasGrounded)
            {
                _wasGrounded = true;
                if (_fallSpeed > 1.5f) Step(motor, Mathf.Clamp01(_fallSpeed / Mathf.Max(0.1f, LandingSpeed)));
                _fallSpeed = 0f;
                _stepDistance = 0f;
            }
            float speed = Vector3.ProjectOnPlane(velocity, motor.CharacterUp).magnitude;
            if (speed < 0.3f)
            {
                _stepDistance = 0f; // standing: the next walk starts with a step soon
                return;
            }
            float run = Mathf.InverseLerp(WalkSpeed, RunSpeed, speed);
            float stride = Mathf.Lerp(StepLength, RunStepLength, run);
            _stepDistance += speed * Time.deltaTime;
            if (_stepDistance < stride) return;
            _stepDistance -= stride;
            float volume = Kcc.Character.CurrentStance == Stance.Crouch ? CrouchVolume : Mathf.Lerp(0.6f, 1f, run);
            Step(motor, volume);
        }

        private static void Step(KinematicCharacterMotor motor, float volume)
        {
            CharacterGroundingReport ground = motor.GroundingStatus;
            Vector3 feet = ground.FoundAnyGround ? ground.GroundPoint : motor.TransientPosition;
            Sfx.PlayAt(SfxSurfaces.StepId(SfxSurfaces.At(ground.GroundCollider, feet)), feet, volume);
        }

        public override Transform Body => Kcc.Character.transform;
        public override Camera ViewCamera => Kcc.ViewCamera;
        public override float Radius => Kcc.Character.Motor.Capsule != null ? Kcc.Character.Motor.Capsule.radius : CapsuleRadius > 0f ? CapsuleRadius : 0.5f;
        public override Stance Stance => Driving ? Stance.Seated : Kcc.Character.CurrentStance;

        public override void SetControlled(bool on) => gameObject.SetActive(on);

        public override void Teleport(Vector3 position, float yawDegrees)
        {
            Quaternion rotation = Quaternion.Euler(0f, yawDegrees, 0f);
            // A fresh state also drops the velocity, grounding and any rigidbody the player stood on (e.g. the van roof).
            Kcc.Character.Motor.ApplyState(new KinematicCharacterMotorState { Position = position, Rotation = rotation }, true);
            YawField?.SetValue(Kcc, Mathf.Repeat(yawDegrees, 360f));
            PitchField?.SetValue(Kcc, 0f);
            // Drop any van the player was riding in at once (no carried velocity); it re-acquires next tick if still inside.
            if (Body.TryGetComponent(out GreyboxCargoRider rider)) rider.OnTeleported();
            if (Body.TryGetComponent(out SeaReturnTracker tracker)) tracker.Rebase();
        }
    }
}
