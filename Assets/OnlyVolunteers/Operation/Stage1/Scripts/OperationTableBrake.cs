using System.Reflection;
using FishNet.Object;
using KinematicCharacterController;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>The gurney's brake and push (Claude rework of G35; round 2 after Fedya's build_v02 playtest, 2026-10-18).
    /// The gurney is a heavy, upright, dynamic server body (rotation X/Z frozen, never tips) and always solid for the
    /// player (PlayerPushPolicy): he can never walk through it, and it never moves into him (KeepOffPlayers).
    /// - Walking into it WITHOUT holding it: the player slows to PushSpeed (12.5 % of his walk speed, Fedya: 10-15 %) and the
    ///   gurney moves along with him at that speed: the server sets its velocity to the player's own speed toward it plus a
    ///   small gap keeper (it stays TargetGap ahead, so the two never collide and nothing jitters). The push needs the
    ///   player's movement intent into it; when he stops or turns away it stops within a few cm (the parked drag).
    /// - Holding it with LMB (the existing NetworkPhysicsBody hold): the player is capped at HeldSpeed (45 %, Fedya:
    ///   40-50 %) in any direction and the hold's own spring moves it; being solid, he cannot pass through it from any side.
    /// - Parked: the wheel contacts are frictionless and a horizontal drag (implicit, stable at any strength) stops it,
    ///   stiction keeps a leaning body from making it creep; a thrown ragdoll still nudges it a little.
    /// The local player's speed cap is applied on his own machine (OperationPlayerSpeed); the push itself runs on the
    /// server from the pushing motor (in the solo host build that is the host's own player). Position replicates through
    /// the table's existing NetworkTransform.</summary>
    [DefaultExecutionOrder(100)] // after the KCC system (-100) moved the players and after NetworkPhysicsBody (0)
    public sealed class OperationTableBrake : MonoBehaviour
    {
        public const float MinMass = 160f;
        /// <summary>Horizontal drag per second while parked (implicit: v /= 1 + k·dt): after a push ends it stops within
        /// ~3 cm, a thrown ragdoll's knock dies within a centimetre or two.</summary>
        public const float ParkedDrag = 20f;
        public const float ParkedYawDamping = 40f;
        public const float StictionSpeed = 0.004f;
        /// <summary>Walking into it: 12.5 % of the walk speed (Fedya: 10-15 %).</summary>
        public const float PushSpeed = OperationPlayerSpeed.WalkSpeed * 0.125f;
        /// <summary>Holding it with LMB: 45 % of the walk speed (Fedya: 40-50 %).</summary>
        public const float HeldSpeed = OperationPlayerSpeed.WalkSpeed * 0.45f;
        /// <summary>The push keeps the gurney this far ahead of the pushing capsule; it engages a little further out.</summary>
        public const float TargetGap = 0.035f, EngageGap = 0.09f, ApproachGap = 0.6f, GapGain = 14f;
        /// <summary>How squarely the player must walk into it (cosine between his walk and the way into the gurney) to push.</summary>
        public const float IntoPush = 0.5f;
        /// <summary>Set by the game mode (Capture): true while a player carries any body within 'range' of 'point'; the
        /// table then brakes fully (kinematic), like while its own patient is carried onto it.</summary>
        public static System.Func<Vector3, float, bool> CarryingNear;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => CarryingNear = null;
        /// <summary>The pre-existing rolling damping while it is deliberately held (G35 values).</summary>
        public const float RollingDamping = 2.5f, RollingAngularDamping = 8f;
        private const RigidbodyConstraints Upright = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;
        private static readonly FieldInfo ClientHeldField = typeof(NetworkGrabber).GetField("clientHeld", BindingFlags.Instance | BindingFlags.NonPublic);

        private NetworkOperationTable table;
        private NetworkPhysicsBody handle;
        private Rigidbody body;
        private bool held, applied;
        private Collider[] wheels = new Collider[0];
        private PhysicsMaterial[] wheelMaterials = new PhysicsMaterial[0];
        private PhysicsMaterial parkedWheels;

        public bool Parked => !held;
        public Rigidbody Body => body;
        /// <summary>Server: the gurney is being pushed by a walking player this physics step.</summary>
        public bool Pushed { get; private set; }
        /// <summary>Server: the last commanded push speed, m/s.</summary>
        public float PushVelocity { get; private set; }

        private void Awake()
        {
            table = GetComponent<NetworkOperationTable>(); handle = GetComponent<NetworkPhysicsBody>(); body = GetComponent<Rigidbody>();
            if (body == null) return;
            body.mass = Mathf.Max(body.mass, MinMass);
            body.constraints = (body.constraints & ~RigidbodyConstraints.FreezePosition & ~RigidbodyConstraints.FreezeRotationY) | Upright;
            var list = new System.Collections.Generic.List<Collider>();
            foreach (var c in GetComponentsInChildren<Collider>(true)) if (c.name.StartsWith("WheelContact")) list.Add(c);
            wheels = list.ToArray(); wheelMaterials = new PhysicsMaterial[wheels.Length];
            for (int i = 0; i < wheels.Length; i++) wheelMaterials[i] = wheels[i].sharedMaterial;
            parkedWheels = new PhysicsMaterial("Gurney parked wheels (drag is the brake)")
            { dynamicFriction = 0f, staticFriction = 0f, frictionCombine = PhysicsMaterialCombine.Minimum, bounciness = 0f, bounceCombine = PhysicsMaterialCombine.Minimum };
            Apply(false);
        }

        private void OnDestroy() { if (parkedWheels != null) Destroy(parkedWheels); }


        // ---------- geometry ----------
        private Collider[] own = new Collider[0];
        private Collider[] Own
        {
            get
            {
                if (own.Length == 0 && body != null)
                    own = System.Array.FindAll(GetComponentsInChildren<Collider>(), c => c.attachedRigidbody == body && !c.isTrigger && !(c is MeshCollider m && !m.convex) && c.GetComponent<OperationTargetTag>() == null);
                return own;
            }
        }
        private Bounds OwnBounds(out bool any)
        {
            var bounds = new Bounds(transform.position, Vector3.zero); any = false;
            foreach (var c in Own) if (c != null && c.enabled) { if (!any) { bounds = c.bounds; any = true; } else bounds.Encapsulate(c.bounds); }
            return bounds;
        }

        /// <summary>Clearance between a character capsule and the gurney's solid colliders (negative = overlapping) and the
        /// horizontal unit direction from the gurney toward the capsule there.</summary>
        public bool Gap(KinematicCharacterMotor motor, out float gap, out Vector3 normal)
        {
            gap = float.MaxValue; normal = Vector3.zero;
            if (motor == null || motor.Capsule == null) return false;
            var capsule = motor.Capsule;
            Vector3 up = motor.CharacterUp, basePos = motor.TransientPosition;
            float r = capsule.radius;
            Vector3 bottom = basePos + motor.TransientRotation * capsule.center - up * Mathf.Max(0f, capsule.height * 0.5f - r);
            Vector3 top = basePos + motor.TransientRotation * capsule.center + up * Mathf.Max(0f, capsule.height * 0.5f - r);
            var bounds = OwnBounds(out bool any);
            if (!any) return false;
            bounds.Expand(2f * (r + ApproachGap));
            if (!bounds.Contains(bottom) && !bounds.Contains(top) && !bounds.Contains((bottom + top) * 0.5f)) return false;
            Vector3 bestFrom = Vector3.zero, bestAt = Vector3.zero;
            const int Samples = 6;
            foreach (var c in Own)
            {
                if (c == null || !c.enabled) continue;
                for (int i = 0; i < Samples; i++)
                {
                    Vector3 p = Vector3.Lerp(bottom, top, i / (Samples - 1f));
                    Vector3 q = c.ClosestPoint(p);
                    float d = Vector3.Distance(p, q) - r;
                    if (d < gap) { gap = d; bestFrom = q; bestAt = p; }
                }
            }
            if (gap == float.MaxValue) return false;
            normal = bestAt - bestFrom; normal.y = 0f;
            if (normal.sqrMagnitude < 1e-6f) { normal = bestAt - bounds.center; normal.y = 0f; }
            if (normal.sqrMagnitude < 1e-6f) normal = transform.forward;
            normal.Normalize();
            return true;
        }

        /// <summary>Whether this machine's player holds this gurney with the LMB grab (NetworkGrabber's client-side hold).</summary>
        public bool LocalHolds(KccFirstPersonInput input)
        {
            if (input == null || table == null || ClientHeldField == null) return false;
            var grabber = input.GetComponent<NetworkGrabber>();
            if (grabber == null) grabber = input.GetComponentInParent<NetworkGrabber>();
            if (grabber == null) return false;
            var heldObject = ClientHeldField.GetValue(grabber) as NetworkObject;
            return heldObject != null && heldObject == table.NetworkObject;
        }

        // ---------- local player: the speed cap ----------
        private void Update()
        {
            var input = OperationPlayerSpeed.Local;
            if (input == null || input.Character == null || body == null) return;
            if (LocalHolds(input)) { OperationPlayerSpeed.Request(input, this, HeldSpeed); return; }
            var motor = input.Character.Motor;
            if (!Gap(motor, out float gap, out Vector3 normal) || gap > ApproachGap) return;
            Vector3 intent = OperationPlayerSpeed.MoveIntent(input.Character);
            if (intent.sqrMagnitude < 0.01f || Vector3.Dot(intent.normalized, -normal) < IntoPush) return;
            // Slowing down over the last half metre, then the push speed against it.
            float t = Mathf.InverseLerp(EngageGap, ApproachGap, gap);
            OperationPlayerSpeed.Request(input, this, Mathf.Lerp(PushSpeed, OperationPlayerSpeed.WalkSpeed * 1.1f, t * t));
        }

        // ---------- server ----------
        private readonly Collider[] near = new Collider[16];
        /// <summary>The gurney never moves INTO a player standing against it (objects never push the player): the part of
        /// its velocity toward a touching player capsule is removed before the physics step. Moving away is free.</summary>
        private void KeepOffPlayers()
        {
            var bounds = OwnBounds(out bool any);
            if (!any) return;
            int n = Physics.OverlapBoxNonAlloc(bounds.center, bounds.extents + Vector3.one * 0.12f, near, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore);
            Vector3 v = body.linearVelocity;
            for (int i = 0; i < n; i++)
            {
                var capsule = near[i] as CapsuleCollider;
                if (capsule == null) continue;
                var motor = capsule.GetComponent<KinematicCharacterMotor>();
                if (motor == null || !Gap(motor, out float gap, out Vector3 toward) || gap > 0.06f) continue;
                float into = Vector3.Dot(v, toward);
                if (into > 0f) v -= toward * into;
            }
            body.linearVelocity = v;
        }

        /// <summary>The walking push: summed over the players whose motor walks into the gurney this step. It goes the way the
        /// player walks (not along the contact normal, which swings around the tray's corners), at his own speed plus the gap
        /// keeper, so the gurney stays TargetGap ahead of him.</summary>
        private Vector3 PushFromPlayers(float maxSpeed)
        {
            Vector3 push = Vector3.zero;
            foreach (var motor in KinematicCharacterSystem.CharacterMotors)
            {
                if (motor == null || !motor.isActiveAndEnabled) continue;
                if (!(motor.CharacterController is ExampleCharacterController character)) continue;
                if (!Gap(motor, out float gap, out Vector3 normal) || gap > EngageGap) continue;
                Vector3 intent = OperationPlayerSpeed.MoveIntent(character);
                if (intent.sqrMagnitude < 0.01f) continue;
                Vector3 dir = intent.normalized;
                float into = Vector3.Dot(dir, -normal);
                if (into < IntoPush) continue;
                float toward = Mathf.Max(0f, Vector3.Dot(motor.BaseVelocity, dir));
                float speed = Mathf.Clamp(toward + GapGain * (TargetGap - gap) / Mathf.Max(into, 0.5f), 0f, maxSpeed);
                push += dir * speed;
            }
            return Vector3.ClampMagnitude(push, maxSpeed);
        }

        private void Apply(bool nowHeld)
        {
            held = nowHeld; applied = true;
            body.linearDamping = RollingDamping;
            body.angularDamping = nowHeld ? RollingAngularDamping : ParkedYawDamping;
            for (int i = 0; i < wheels.Length; i++) if (wheels[i] != null) wheels[i].sharedMaterial = nowHeld ? wheelMaterials[i] : parkedWheels;
        }

        private void FixedUpdate()
        {
            Pushed = false;
            if (table == null || !table.IsServerInitialized || body == null) return;
            bool nowHeld = handle != null && handle.HasHolder;
            if (!applied || nowHeld != held) Apply(nowHeld);
            if (body.isKinematic) return;
            // Walking into it (held or not): along the push its speed is the pusher's own plus the gap keeper, so he never
            // collides with it; held, the hold's spring still steers it (and pulls it when he walks backwards).
            Vector3 v = body.linearVelocity;
            Vector3 push = PushFromPlayers(held ? HeldSpeed * 1.3f : PushSpeed * 1.3f);
            if (push.sqrMagnitude > 1e-6f)
            {
                Vector3 dir = push.normalized;
                Vector3 flat = new Vector3(v.x, 0f, v.z);
                Vector3 side = flat - dir * Vector3.Dot(flat, dir);
                if (!held) side /= 1f + ParkedDrag * Time.fixedDeltaTime; // sideways it still drags
                Vector3 h = dir * push.magnitude + side;
                body.linearVelocity = new Vector3(h.x, v.y, h.z);
                Pushed = true; PushVelocity = push.magnitude;
            }
            else if (!held)
            {
                // Parked: the wheels drag on the floor. Horizontal only, so gravity still settles the gurney.
                float k = 1f / (1f + ParkedDrag * Time.fixedDeltaTime);
                float vx = v.x * k, vz = v.z * k;
                // Stiction: a body merely leaning on it (a few newtons) never makes it creep; a thrown body is far above it.
                if (vx * vx + vz * vz < StictionSpeed * StictionSpeed) { vx = 0f; vz = 0f; }
                body.linearVelocity = new Vector3(vx, v.y, vz);
                PushVelocity = 0f;
            }
            if (!held) { var w = body.angularVelocity; if (Mathf.Abs(w.y) < 0.02f) body.angularVelocity = new Vector3(w.x, 0f, w.z); }
            KeepOffPlayers();
        }
    }
}
