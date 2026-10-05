using System.Collections.Generic;
using KinematicCharacterController;
using OnlyVolunteers.Player;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Lets the KCC player ride in a van's cargo bay (stage 1, offline). Sits on the moving part of the player (the motor).
    // Inside = the capsule centre is in a VanCargoSpace box. While inside, the motor is attached to the van's Rigidbody
    // even in the air (bumps, braking), jumping is off, the sea return is off (the van's own tracker handles the sea) and
    // the player never pushes rigidbodies (KCC RigidbodyInteractionType None, the prefab default, enforced).
    // Exit = outside the box plus ExitMargin for ExitDelay (hysteresis, so standing in the doorway does not flicker).
    // Dropping the override lets the KCC keep the van's velocity (PreserveAttachedRigidbodyMomentum), so jumping out of a
    // moving van carries on smoothly (KccFirstPersonInput.AllowAirSpeed keeps its air speed cap from clipping it). Teleports
    // call OnTeleported: the attachment is dropped at once, without that velocity. While inside, the view turns with the
    // van (KccFirstPersonInput.AddYaw), so a passenger keeps facing the same way through a turn.
    // While riding, the physics engine ignores contacts between our capsule and the van's colliders. The KCC moves by its
    // own queries (unaffected by IgnoreCollision), but its kinematic capsule sits at the start-of-tick pose during the
    // physics step (custom interpolation): at 40 km/h it lags the van by ~0.22 m per tick, and a van wall overlapping a
    // kinematic body would be shoved hard (jitter, the van "hitting" its own passenger).
    // Known limit (KCC on a dynamic rigidbody): the player's own steps are swept against the van's colliders at their
    // pre-physics-step pose, so at speed the player stops ~speed*dt short of the cab partition and buzzes a few cm when
    // walking into the rear doors. Standing or crouching still is clean. A PhysicsMover proxy (draft B5) would fix it.
    [RequireComponent(typeof(KinematicCharacterMotor))]
    public sealed class GreyboxCargoRider : MonoBehaviour
    {
        public float ExitMargin = 0.3f;
        public float ExitDelay = 0.2f;

        /// <summary>The cargo bay the player is riding in, or null.</summary>
        public VanCargoSpace Carrier => _riding ? _space : null;
        public bool Inside => _riding;

        private KinematicCharacterMotor _motor;
        private KccFirstPersonInput _input;
        private SeaReturnTracker _tracker;
        private VanCargoSpace _space;
        // Separate from _space: a destroyed van compares equal to null but its override still has to be cleared.
        private bool _riding;
        private float _outsideFor;
        private bool _trackerPaused;
        private float _vanYaw;
        private RigidbodyInteractionType _savedInteraction;
        private readonly List<Collider> _ignored = new();

        // In OnEnable rather than Awake (same moment at start): it also runs after a script reload in Play mode.
        private void OnEnable()
        {
            if (_motor == null) _motor = GetComponent<KinematicCharacterMotor>();
            if (_input == null) _input = GetComponentInParent<KccFirstPersonInput>(true);
        }

        private void OnDisable() => Detach(false);

        // Per rendered frame, from the van's interpolated transform, so the view turns as smoothly as the van is drawn.
        private void Update()
        {
            if (!_riding || !_space || _input == null) return;
            float yaw = VanYaw();
            _input.AddYaw(Mathf.DeltaAngle(_vanYaw, yaw));
            _vanYaw = yaw;
        }

        private float VanYaw()
        {
            Vector3 forward = Vector3.ProjectOnPlane(_space.transform.forward, Vector3.up);
            return forward.sqrMagnitude > 1e-6f ? Mathf.Atan2(forward.x, forward.z) * Mathf.Rad2Deg : _vanYaw;
        }

        public void OnTeleported() => Detach(false);

        private void FixedUpdate()
        {
            if (_motor == null || _motor.Capsule == null) return;
            Vector3 centre = _motor.TransientPosition + _motor.TransientRotation * _motor.Capsule.center;
            if (_riding)
            {
                // The van was destroyed or switched off under us.
                if (!_space || !_space.isActiveAndEnabled || _space.Body == null)
                {
                    Detach(true);
                    return;
                }
                if (_space.Contains(centre, ExitMargin)) _outsideFor = 0f;
                else if ((_outsideFor += Time.fixedDeltaTime) >= ExitDelay)
                {
                    Detach(true);
                    return;
                }
                Hold();
                return;
            }
            foreach (VanCargoSpace space in VanCargoSpace.All)
                if (space != null && space.isActiveAndEnabled && space.Body != null && space.Upright && space.Contains(centre))
                {
                    Attach(space);
                    return;
                }
        }

        private void Attach(VanCargoSpace space)
        {
            _space = space;
            _riding = true;
            _outsideFor = 0f;
            _vanYaw = VanYaw();
            _savedInteraction = _motor.RigidbodyInteractionType;
            _tracker = GetComponent<SeaReturnTracker>();
            _trackerPaused = _tracker != null && _tracker.enabled;
            if (_trackerPaused) _tracker.enabled = false;
            // Active colliders only: Unity refuses IgnoreCollision on inactive ones (and deactivation resets it anyway).
            foreach (Collider c in space.Body.GetComponentsInChildren<Collider>())
                if (Active(c) && !c.isTrigger && !(c is WheelCollider))
                {
                    Physics.IgnoreCollision(_motor.Capsule, c, true);
                    _ignored.Add(c);
                }
            Hold();
        }

        private static bool Active(Collider c) => c != null && c.enabled && c.gameObject.activeInHierarchy;

        // Re-applied every tick while inside, in case something else touched these in between.
        private void Hold()
        {
            _motor.AttachedRigidbodyOverride = _space.Body;
            _motor.RigidbodyInteractionType = RigidbodyInteractionType.None;
            if (_input != null) _input.JumpBlocked = true;
        }

        // exited: the player left the van (or the van went away) rather than being teleported or switched off. Then the
        // van's velocity is kept (the motor adds it next tick; the air speed cap is widened to match) and the sea
        // tracker forgets its pre-van history (the van may have driven across the map since). Teleports rebase the
        // tracker themselves right after this, and a disabled player has nothing to rebase.
        private void Detach(bool exited)
        {
            if (!_riding) return;
            _riding = false;
            _space = null;
            _outsideFor = 0f;
            if (exited && _motor != null && _input != null)
                _input.AllowAirSpeed(Vector3.ProjectOnPlane(_motor.BaseVelocity + _motor.AttachedRigidbodyVelocity, _motor.CharacterUp).magnitude);
            if (_motor != null)
            {
                _motor.AttachedRigidbodyOverride = null;
                _motor.RigidbodyInteractionType = _savedInteraction;
                // Skipped when either side is inactive (e.g. the player is being switched off for the driver seat):
                // Unity refuses the call then, and deactivation has already reset the pair.
                if (Active(_motor.Capsule))
                    foreach (Collider c in _ignored)
                        if (Active(c))
                            Physics.IgnoreCollision(_motor.Capsule, c, false);
            }
            _ignored.Clear();
            if (_input != null) _input.JumpBlocked = false;
            if (_trackerPaused && _tracker != null)
            {
                _tracker.enabled = true;
                if (exited) _tracker.Rebase();
            }
            _trackerPaused = false;
        }
    }
}
