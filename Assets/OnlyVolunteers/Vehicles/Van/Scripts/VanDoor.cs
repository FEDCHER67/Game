using System.Collections.Generic;
using KinematicCharacterController;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Animated van door. Hinge doors swing about the van's up axis through their pivot;
    // the sliding door first pops outward, then runs back along its rail. Motion is expressed
    // in van-local space, so it stays correct while the van drives.
    // NPC capture stage 1 (draft section 3): a kinematic drive with a force limit instead of a joint (a jointed door on a
    // child of the moving van body jitters).
    // - Explicit state: TargetOpen / Openness / IsStalled, changed by Request(open). A driver button and the handle in the
    //   cargo bay ask for a state, so they never fight like two toggles would. Toggle/Open/Close stay for old callers.
    // - The pose advances in FixedUpdate. Before every step the door's next pose is checked against bodies on BlockMask
    //   (players, NPC bodies, seated NPCs): OverlapBox, then ComputePenetration at the current and the next pose. A body
    //   the step would push deeper into blocks it: the door does not advance (IsStalled) and pushes that body away with
    //   at most MaxPush (300 N hinge, 250 N slide); kinematic bodies (the KCC player) block, and an opening door moves a
    //   KCC player out of its way (KinematicCharacterMotor.MoveCharacter) so it goes on next tick. Bodies the door moves
    //   away from or slides along never block, so a body leaning on a closed door does not stop it from opening.
    // - A closing door stalled for StallBackoffAfter seconds backs off BackoffFraction and tries again: a foot in the door
    //   (canon section 138). A closing door that meets a body faster than ShoveSpeed shoves it (ShoveImpulse).
    // - The drawn pose is interpolated between physics ticks, like the van body itself; physics always sees the tick pose.
    public sealed class VanDoor : MonoBehaviour
    {
        public enum Kind { Hinge, Slide }

        public Kind DoorKind = Kind.Hinge;
        public Transform Van;
        [Tooltip("Hinge: opening angle in degrees. Direction is picked so the free edge moves toward OutwardHint.")]
        public float OpenAngle = 70f;
        [Tooltip("Hinge: van-local direction the free edge should move when opening.")]
        public Vector3 OutwardHint = Vector3.right;
        [Tooltip("Slide: van-local offset after the outward pop.")]
        public Vector3 SlidePop = new(0.07f, 0f, 0f);
        [Tooltip("Slide: van-local offset when fully open.")]
        public Vector3 SlideTravel = new(0.07f, 0f, -1.02f);
        [Range(0.05f, 0.6f)] public float PopFraction = 0.22f;
        public float Duration = 0.85f;

        [Header("Blocking (NPC capture stage 1)")]
        [Tooltip("Bodies that stop the door: layers 8 Player, 12 NpcBody, 13 NpcSeated (OvLayers).")]
        public LayerMask BlockMask = (1 << 8) | (1 << 12) | (1 << 13);
        [Tooltip("Most force (N) the door pushes a blocking body with; 0 = by kind: 300 hinge, 250 slide.")]
        public float MaxPush;
        [Tooltip("A closing door stalled this long backs off and tries again.")]
        public float StallBackoffAfter = 0.6f;
        [Range(0f, 1f)] public float BackoffFraction = 0.15f;
        [Tooltip("A closing door meeting a body faster than this (m/s) shoves it.")]
        public float ShoveSpeed = 1f;
        [Tooltip("N·s, along the door's push direction.")]
        public float ShoveImpulse = 15f;

        // Plain state (a network door mask later). TargetOpen: where the door is going; Openness 0 closed .. 1 open.
        [System.NonSerialized] public bool TargetOpen;
        public float Openness => _t;
        public bool IsStalled { get; private set; }
        // The requested state, as before.
        public bool IsOpen => TargetOpen;
        public float PushLimit => MaxPush > 0f ? MaxPush : DoorKind == Kind.Hinge ? 300f : 250f;

        private const float DepthSlack = 0.001f;

        private Vector3 _closedLocalPos;
        private Quaternion _closedLocalRot;
        private float _signedAngle;
        private float _t;
        private float _prevT;   // pose at the previous physics tick (drawn pose blends from it)
        private float _shownT;  // pose the transform shows now
        private float _stalledFor;
        private float _backoffTo = -1f; // >= 0 while backing off after a stall
        private Rigidbody _vanBody;
        private BoxCollider _box;
        private readonly Collider[] _hits = new Collider[16];
        private readonly HashSet<Collider> _blocking = new();
        private readonly HashSet<Collider> _blockingNow = new();

        private void Awake()
        {
            _closedLocalPos = transform.localPosition;
            _closedLocalRot = transform.localRotation;
            if (Van == null)
                Van = GetComponentInParent<Rigidbody>() != null ? GetComponentInParent<Rigidbody>().transform : transform.root;
            _signedAngle = DoorKind == Kind.Hinge ? ChooseHingeSign() : 0f;
            // The physics pose of the van comes from its body (the transform of an interpolated body shows the drawn pose).
            _vanBody = Van.GetComponent<Rigidbody>();
            _box = GetComponent<BoxCollider>();
        }

        /// <summary>Ask for a state. Repeating the same request changes nothing.</summary>
        public void Request(bool open)
        {
            if (open == TargetOpen) return;
            TargetOpen = open;
            _stalledFor = 0f;
            _backoffTo = -1f;
        }

        public void Toggle() => Request(!TargetOpen);
        public void Open() => Request(true);
        public void Close() => Request(false);

        private void FixedUpdate()
        {
            _prevT = _t;
            Step(Time.fixedDeltaTime);
            if (_shownT != _t) Apply(_t); // physics simulates the tick pose, never an interpolated one
        }

        private void Update()
        {
            if (_prevT == _t) return; // at rest: the last tick already applied _t
            float a = Mathf.Clamp01((Time.time - Time.fixedTime) / Mathf.Max(1e-4f, Time.fixedDeltaTime));
            Apply(Mathf.Lerp(_prevT, _t, a));
        }

        private void Step(float dt)
        {
            float goal = _backoffTo >= 0f ? _backoffTo : TargetOpen ? 1f : 0f;
            if (Mathf.Approximately(_t, goal))
            {
                _t = goal;
                _backoffTo = -1f;
                IsStalled = false;
                _stalledFor = 0f;
                _blocking.Clear();
                return;
            }
            float next = Mathf.MoveTowards(_t, goal, dt / Mathf.Max(0.01f, Duration));
            // Backing off moves away from what stopped the door; only real moves are checked.
            bool closing = next < _t;
            if (_backoffTo < 0f && Blocked(_t, next, dt, closing))
            {
                IsStalled = true;
                _stalledFor += dt;
                if (closing && _stalledFor >= StallBackoffAfter && BackoffFraction > 0f)
                {
                    _backoffTo = Mathf.Min(1f, _t + BackoffFraction);
                    _stalledFor = 0f;
                    _blocking.Clear(); // the next hit after backing off is a new hit (and shoves again)
                }
                return;
            }
            IsStalled = false;
            _stalledFor = 0f;
            _t = next;
        }

        // Would moving from openness 'from' to 'to' push deeper into a body? Pushes every such body away (and shoves
        // it when a closing door meets it fast); the van takes the reaction.
        private bool Blocked(float from, float to, float dt, bool closing)
        {
            _blockingNow.Clear();
            if (_box == null || !_box.enabled || BlockMask.value == 0)
            {
                _blocking.Clear();
                return false;
            }
            WorldPose(from, out Vector3 p0, out Quaternion r0);
            WorldPose(to, out Vector3 p1, out Quaternion r1);
            Vector3 scale = transform.lossyScale;
            Vector3 centre = p1 + r1 * Vector3.Scale(_box.center, scale);
            Vector3 half = Abs(Vector3.Scale(_box.size, scale)) * 0.5f;
            int count = Physics.OverlapBoxNonAlloc(centre, half, _hits, r1, BlockMask, QueryTriggerInteraction.Ignore);
            bool blocked = false;
            for (int i = 0; i < count; i++)
            {
                Collider other = _hits[i];
                _hits[i] = null;
                // Our own van, and free crowd NPCs (their CharacterController ignores the van by design).
                if (other == null || other.transform.IsChildOf(Van) || other is CharacterController) continue;
                ColliderPose(other, out Vector3 op, out Quaternion or);
                if (!Physics.ComputePenetration(_box, p1, r1, other, op, or, out Vector3 dir, out float depth1)) continue;
                float depth0 = Physics.ComputePenetration(_box, p0, r0, other, op, or, out _, out float d0) ? d0 : 0f;
                if (depth1 <= depth0 + DepthSlack) continue; // moving away from it, or along it
                blocked = true;
                _blockingNow.Add(other);
                Rigidbody rb = other.attachedRigidbody;
                if (rb == null || rb.isKinematic)
                {
                    // The KCC player. An opening door moves it out of the way (else the rear pair stalls for good on
                    // whoever opened it from right behind the van); a closing one stalls on it: the foot in the door.
                    // Either way the door waits this tick, so it never overlaps the kinematic capsule (that would shove
                    // the van); the player moves at the start of the next tick and the door goes on.
                    if (!closing) NudgeCharacter(other, dir, depth1);
                    continue;
                }
                // dir moves the door out of the body, so the body goes the other way.
                Vector3 push = -dir;
                Vector3 at = other.ClosestPoint(centre);
                float force = PushLimit * Mathf.Clamp01(depth1 / 0.03f);
                rb.AddForceAtPosition(push * force, at, ForceMode.Force);
                if (_vanBody != null) _vanBody.AddForceAtPosition(-push * force, at, ForceMode.Force);
                if (closing && !_blocking.Contains(other) && DoorPointSpeed(at, p0, r0, p1, r1, dt, push) > ShoveSpeed)
                {
                    rb.AddForceAtPosition(push * ShoveImpulse, at, ForceMode.Impulse);
                    if (_vanBody != null) _vanBody.AddForceAtPosition(-push * ShoveImpulse, at, ForceMode.Impulse);
                }
            }
            _blocking.Clear();
            _blocking.UnionWith(_blockingNow);
            return blocked;
        }

        // Moves a KCC character out of an opening door's next pose: along the floor (perpendicular to the van's up), by the
        // depth plus a few centimetres, through the motor so its own collision solving applies (a wall behind it stops it).
        private void NudgeCharacter(Collider other, Vector3 doorOut, float depth)
        {
            if (!other.TryGetComponent(out KinematicCharacterMotor motor) || !motor.isActiveAndEnabled) return;
            Vector3 away = Vector3.ProjectOnPlane(-doorOut, Van.up);
            float flat = away.magnitude;
            if (flat < 0.1f) return; // the door presses it straight down or up: nothing sensible, it just blocks
            motor.MoveCharacter(motor.TransientPosition + away / flat * ((depth + 0.04f) / Mathf.Max(0.3f, flat)));
        }

        // Speed (m/s) along 'along' of the door point at 'world', between the two poses.
        private static float DoorPointSpeed(Vector3 world, Vector3 p0, Quaternion r0, Vector3 p1, Quaternion r1, float dt, Vector3 along)
        {
            Vector3 local = Quaternion.Inverse(r1) * (world - p1);
            Vector3 before = p0 + r0 * local;
            return Vector3.Dot(world - before, along) / Mathf.Max(1e-4f, dt);
        }

        // A body's physics pose: its Rigidbody's when the collider sits on it, otherwise the transform's.
        private static void ColliderPose(Collider c, out Vector3 position, out Quaternion rotation)
        {
            Rigidbody rb = c.attachedRigidbody;
            if (rb != null && rb.transform == c.transform)
            {
                position = rb.position;
                rotation = rb.rotation;
                return;
            }
            position = c.transform.position;
            rotation = c.transform.rotation;
        }

        // World pose of this door's transform at openness t, on the van body's physics pose.
        private void WorldPose(float t, out Vector3 position, out Quaternion rotation)
        {
            LocalPose(t, out Vector3 lp, out Quaternion lr);
            Transform parent = transform.parent;
            // Van-root space first: the hierarchy between the van root and this door does not move.
            Vector3 rootPos = Van.InverseTransformPoint(parent.TransformPoint(lp));
            Quaternion rootRot = Quaternion.Inverse(Van.rotation) * (parent.rotation * lr);
            if (_vanBody != null)
            {
                position = _vanBody.position + _vanBody.rotation * rootPos;
                rotation = _vanBody.rotation * rootRot;
                return;
            }
            position = Van.TransformPoint(rootPos);
            rotation = Van.rotation * rootRot;
        }

        private void Apply(float t)
        {
            LocalPose(t, out Vector3 lp, out Quaternion lr);
            transform.SetLocalPositionAndRotation(lp, lr);
            _shownT = t;
        }

        private void LocalPose(float t, out Vector3 localPosition, out Quaternion localRotation)
        {
            Transform parent = transform.parent;
            if (DoorKind == Kind.Hinge)
            {
                Vector3 axis = parent.InverseTransformDirection(Van.up);
                localPosition = _closedLocalPos;
                localRotation = Quaternion.AngleAxis(_signedAngle * Ease(t), axis) * _closedLocalRot;
                return;
            }

            Vector3 offset = t < PopFraction
                ? Vector3.Lerp(Vector3.zero, SlidePop, Ease(t / PopFraction))
                : Vector3.Lerp(SlidePop, SlideTravel, Ease((t - PopFraction) / (1f - PopFraction)));
            localPosition = _closedLocalPos + parent.InverseTransformVector(Van.TransformVector(offset));
            localRotation = _closedLocalRot;
        }

        private static float Ease(float x)
        {
            x = Mathf.Clamp01(x);
            return x * x * (3f - 2f * x);
        }

        private static Vector3 Abs(Vector3 v) => new(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));

        // Pick +angle or -angle so the door's centre moves toward OutwardHint (works for any import axes).
        private float ChooseHingeSign()
        {
            Renderer r = GetComponent<Renderer>();
            if (r == null)
                return OpenAngle;
            Vector3 pivot = transform.position;
            Vector3 centre = r.bounds.center;
            Vector3 outward = Van.TransformDirection(OutwardHint);
            Vector3 plus = Quaternion.AngleAxis(OpenAngle, Van.up) * (centre - pivot);
            Vector3 minus = Quaternion.AngleAxis(-OpenAngle, Van.up) * (centre - pivot);
            return Vector3.Dot(plus - (centre - pivot), outward) >= Vector3.Dot(minus - (centre - pivot), outward)
                ? OpenAngle
                : -OpenAngle;
        }
    }
}
