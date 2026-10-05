using System.Reflection;
using KinematicCharacterController;
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

        private KccFirstPersonInput _kcc;

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
