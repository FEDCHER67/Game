using System;
using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The physical body of a downed grey-box NPC (NPC capture stage 1): ONE rigidbody, no bone ragdoll yet (canon section
    // 151, draft section 3; the 11-body ragdoll is stage B8). The limbs only dangle visually.
    // GreyboxNpc switches it on when the NPC goes down (Activate: capsule + Rigidbody on the NPC root, layer NpcBody) and
    // off when it stands up again (Deactivate: both removed, the CharacterController takes over).
    // Grab anywhere (Fedya's second playtest, 2026-10-05): a holder claims the point of the body's axis nearest to where its
    // ray hit, i.e. any point of the capsule, projected onto the axis (a pull through the axis never rolls the body like a
    // log). Up to MaxHolders holders, one slot each, no spacing rule (two players may hold the same spot). Point and
    // PointLocal are only anatomical landmarks now: GreyboxVanCargo's in-bay test (pelvis, collar), GreyboxNpc's ankle
    // kicks and Tear's preference.
    // Lever rule, no lift assist: lying stunned the body weighs DownedMass (28 kg, W 275 N); awake (sitting in the bay,
    // escaping) it has Mass (40 kg). PhysicsGrabber holds a claim with NpcGrabProfile: up to 200 N up/down and 220 N
    // sideways per hand, spring 1200, damping ratio 0.6. A body lying on the ground turns about the centre of its other
    // end cap (0.28 m from the feet; 1.22 m from the feet for the head end), at any tilt, its centre of mass 0.47 m from that
    // pivot. Lifting a point s (m from the feet) on the head side needs W*0.47/(s-0.28), on the foot side W*0.47/(1.22-s),
    // at the centre of mass the whole W:
    // - head top 110 N, collar 127 N, shin 133 N, ankle 113 N: one hand lifts them easily (55-67% of its 200 N);
    // - between 0.574 and 0.926 m (hips, belly; the hint adds "тяжело") one hand is not enough and the point stays down;
    //   two hands there (400 N) lift it;
    // - one hand never lifts the whole body clear (200 N < W), two at the ends carry it (collar 151 N + ankle 124 N).
    // Grip: static 1.6, sliding 0.5, combined by Average: ~1.1 / 0.55 on default ground (0.6), so the far end pivots
    // instead of sliding. The van's floor, bumper top, steps and rear wheel housings use a Minimum-combined 0.3 material
    // (VanInteriorColliders), which wins over Average, so a body leaning on the floor edge slides in when pushed.
    // The NPC logic can take any claim back (RevokeAll on waking, Tear when it kicks free). F9 debug pins (TogglePin) are
    // holders too: they stand in for a second or third player offline.
    // State is plain data (Claims, HolderCount, Grabbable) for a network version later.
    [DisallowMultipleComponent]
    public sealed class GreyboxNpcBody : MonoBehaviour, IGrabPointTarget
    {
        public enum Point { Collar, LeftWrist, RightWrist, Pelvis, LeftAnkle, RightAnkle }

        /// <summary>Anatomical landmarks in root space (root at the feet, body along local up), indexed by Point. Not grab
        /// points any more (a hand holds wherever it grabbed, on the axis): GreyboxVanCargo tests the pelvis and collar for
        /// "in the bay", GreyboxNpc kicks at an ankle, Tear prefers holds near a landmark.</summary>
        public static readonly Vector3[] PointLocal =
        {
            new(0f, 1.30f, -0.12f), new(-0.35f, 0.85f, 0f), new(0.35f, 0.85f, 0f),
            new(0f, 0.80f, 0f), new(-0.10f, 0.08f, 0f), new(0.10f, 0.08f, 0f),
        };

        public const int MaxHolders = 3;
        // m along the axis: claims stay this far inside the capsule's ends; a claim below FootZone is a feet hold
        // (OnlyAnklesHeld); Tear takes the hold nearest its landmark within TearRadius; F9 on a pin within PinToggleRadius
        // removes it.
        public const float EndInset = 0.05f, FootZone = 0.45f, TearRadius = 0.45f, PinToggleRadius = 0.25f;

        // Grab hint zones by height along the body (m from the feet on the 1.5 m body, scaled with Height), accusative.
        private static readonly (float from, string name)[] Zones =
        {
            (1.30f, "голову"), (1.12f, "плечи"), (0.95f, "грудь"), (0.62f, "таз"), (0.25f, "ноги"), (float.NegativeInfinity, "ступни"),
        };

        [Tooltip("How holders hold a point (Map/Data/NpcGrabProfile.asset). Empty = the same numbers built in code.")]
        public GrabPhysicsProfile GrabProfile;

        [Header("Body")]
        [Tooltip("Awake mass (sitting in the cargo bay, escaping).")]
        public float Mass = 40f;
        [Tooltip("Mass while lying stunned: light enough for one hand to lift an end, never the middle (lever rule, see header).")]
        public float DownedMass = 28f;
        public float LinearDamping = 0.05f;
        public float AngularDamping = 0.5f;
        public float MaxDepenetration = 3f;
        public int SolverIterations = 10;
        public float Height = 1.5f;
        public float Radius = 0.28f;
        [Tooltip("Capsule height while sitting in the cargo bay (roof 1.43 m above the floor).")]
        public float SeatedHeight = 1.0f;
        [Tooltip("m/s: a sitter knocked down with no room to lie flat grows back to full length this fast (SetSeated).")]
        public float UnseatGrowSpeed = 2f;
        [Tooltip("Sliding friction (dragging along the ground or the cargo floor).")]
        public float Friction = 0.5f;
        [Tooltip("Static friction: holds the far end in place while the other end is lifted, so the body pivots on it.")]
        public float StaticFriction = 1.6f;
        [Tooltip("Per second, only around the body's long axis: a lone capsule would otherwise roll away like a log.")]
        public float RollDamping = 4f;
        [Header("Sound (optional, Sfx)")]
        [Tooltip("m/s along the contact normal: slower landings make no thud.")]
        public float ThudMinSpeed = 1.2f;
        [Tooltip("m/s: at and above this the thud plays at full volume.")]
        public float ThudFullSpeed = 6f;

        /// <summary>One hold: who holds, and where (Rigidbody space, ON the body axis: x = z = 0).</summary>
        public struct Claim
        {
            public object Holder;
            public Vector3 Local;
        }

        // Plain data. Claims[slot]: Holder null = free slot. Grabbable: set by GreyboxNpc (while lying down, and while
        // running for a cargo door; NpcGrabProfile finds both layers, NpcBody and NpcSeated).
        [NonSerialized] public readonly Claim[] Claims = new Claim[MaxHolders];
        [NonSerialized] public bool Grabbable;

        /// <summary>Hit something: (impact speed along the contact normal, the other collider). Kinematic bodies (players'
        /// KCC capsules) do not count.</summary>
        public event Action<float, Collider> Impact;

        private static GrabPhysicsProfile _fallbackProfile;
        private static PhysicsMaterial _material;

        // Serialized so a script reload in Play mode keeps the references (the components themselves survive it).
        [SerializeField, HideInInspector] private Rigidbody _rb;
        [SerializeField, HideInInspector] private CapsuleCollider _capsule;
        [SerializeField, HideInInspector] private bool _seated;
        [SerializeField, HideInInspector] private int _freeLayer;
        // Lying down from sitting with no free spot: the capsule's current length while it grows back to Height.
        private bool _growing;
        private float _shapeHeight;
        private readonly List<Collider> _ignored = new();
        private float _restoreIgnoredAt;
        private float _lastContact = -1f;
        private readonly List<DebugPin> _pins = new();

        private sealed class DebugPin
        {
            public int Slot;
            public Vector3 Anchor;
        }

        public bool Active => _rb != null;
        public bool Seated => _seated && _rb != null;
        public Rigidbody Rigidbody => _rb;
        public GrabPhysicsProfile Profile => GrabProfile != null ? GrabProfile : FallbackProfile;
        public Vector3 CenterOfMass => _rb != null ? _rb.worldCenterOfMass : transform.TransformPoint(0f, Height * 0.5f, 0f);
        /// <summary>Touched anything in the last physics tick or so (ground, van floor, another body).</summary>
        public bool Grounded => _rb != null && Time.fixedTime - _lastContact <= Time.fixedDeltaTime * 1.5f;

        public int HolderCount
        {
            get
            {
                int n = 0;
                for (int i = 0; i < Claims.Length; i++)
                    if (Claims[i].Holder != null) n++;
                return n;
            }
        }

        /// <summary>Held, and only by the feet (every hold below FootZone; feet first, head bouncing: costs the NPC
        /// condition when fast).</summary>
        public bool OnlyAnklesHeld
        {
            get
            {
                bool held = false;
                for (int i = 0; i < Claims.Length; i++)
                {
                    if (Claims[i].Holder == null) continue;
                    if (Claims[i].Local.y >= FootZone) return false;
                    held = true;
                }
                return held;
            }
        }

        // From the physics pose when there is a body (the transform shows the interpolated one).
        public Vector3 PointWorld(int point) =>
            _rb != null ? _rb.position + _rb.rotation * PointLocal[point] : transform.TransformPoint(PointLocal[point]);

        /// <summary>World position of the hold in a slot (physics pose).</summary>
        public Vector3 ClaimWorld(int slot) =>
            _rb != null ? _rb.position + _rb.rotation * Claims[slot].Local : transform.TransformPoint(Claims[slot].Local);

        // The NpcGrabProfile numbers in code, for scenes built before the asset existed. GrabPhysicsProfile keeps its
        // fields private (Vadim's), so they are filled by name from JSON; if a name ever changes, that field keeps its default.
        public static GrabPhysicsProfile FallbackProfile
        {
            get
            {
                if (_fallbackProfile != null) return _fallbackProfile;
                _fallbackProfile = ScriptableObject.CreateInstance<GrabPhysicsProfile>();
                _fallbackProfile.name = "NpcGrabProfile (code)";
                _fallbackProfile.hideFlags = HideFlags.DontSave;
                JsonUtility.FromJsonOverwrite(
                    "{\"acquireDistance\":2.2,\"holdDistance\":2.5,\"springStrength\":1200,\"dampingRatio\":0.6," +
                    "\"maxForce\":200,\"maxLinearSpeed\":4.5,\"maxAngularSpeed\":8,\"breakDistance\":2.2," +
                    "\"soloHorizontalMaxForce\":220," +
                    "\"acquisitionLayers\":{\"m_Bits\":" + OvLayers.NpcMask + "}}", _fallbackProfile);
                return _fallbackProfile;
            }
        }

        private PhysicsMaterial Material => _material != null ? _material : _material = new PhysicsMaterial("NpcBody")
        {
            dynamicFriction = Friction,
            staticFriction = Mathf.Max(Friction, StaticFriction),
            bounciness = 0f,
            frictionCombine = PhysicsMaterialCombine.Average,
            bounceCombine = PhysicsMaterialCombine.Minimum,
        };

        private void Awake()
        {
            if (_rb == null) _freeLayer = gameObject.layer;
        }

        // ---------- On / off ----------

        /// <summary>Becomes a DownedMass physics body where the NPC stands now (lying down is up to physics: a hit topples it).</summary>
        public void Activate(Vector3 velocity, Vector3 angularVelocity)
        {
            if (_rb == null) _freeLayer = gameObject.layer;
            // Collider first: the Rigidbody computes its centre of mass and inertia from it.
            if (_capsule == null) _capsule = gameObject.AddComponent<CapsuleCollider>();
            if (_rb == null) _rb = gameObject.AddComponent<Rigidbody>();
            _seated = false;
            _growing = false;
            gameObject.layer = OvLayers.NpcBody;
            _capsule.enabled = true;
            _capsule.sharedMaterial = Material;
            SetShape(Height);
            _rb.mass = DownedMass;
            _rb.linearDamping = LinearDamping;
            _rb.angularDamping = AngularDamping;
            _rb.interpolation = RigidbodyInterpolation.Interpolate;
            _rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            _rb.maxDepenetrationVelocity = MaxDepenetration;
            _rb.solverIterations = SolverIterations;
            _rb.constraints = RigidbodyConstraints.None;
            _rb.linearVelocity = velocity;
            _rb.angularVelocity = angularVelocity;
            _rb.WakeUp();
            _lastContact = -1f;
        }

        /// <summary>Back to a plain (CharacterController) NPC: claims revoked, Rigidbody and capsule removed.
        /// Removed at once (DestroyImmediate), so the NPC can be hit down again in the same frame; never call this from
        /// a collision callback.</summary>
        public void Deactivate()
        {
            RevokeAll();
            _ignored.Clear(); // the pairs die with the capsule
            _seated = false;
            _growing = false;
            if (_rb != null) DestroyImmediate(_rb);
            if (_capsule != null) DestroyImmediate(_capsule);
            _rb = null;
            _capsule = null;
            gameObject.layer = _freeLayer;
        }

        /// <summary>Sitting in the cargo bay (awake there, Mass): upright, rotation frozen, 1 m capsule, layer NpcSeated
        /// (ignores lying bodies and other sitters). Back to lying (DownedMass): laid on its back where it sat, then the full
        /// capsule.</summary>
        public void SetSeated(bool seated)
        {
            if (_rb == null || seated == _seated) return;
            _seated = seated;
            Vector3 position;
            Quaternion rotation;
            if (seated)
            {
                // Lying: the centre is one radius above the floor; sit there, facing where the head was.
                Vector3 centre = _rb.worldCenterOfMass;
                Vector3 facing = Flat(_rb.rotation * Vector3.up);
                if (facing.sqrMagnitude < 1e-4f) facing = Flat(_rb.rotation * Vector3.forward);
                rotation = facing.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(facing.normalized) : Quaternion.identity;
                position = centre - Vector3.up * (Radius - 0.02f);
                _growing = false;
                SetShape(SeatedHeight);
                _rb.mass = Mass;
                _rb.constraints = RigidbodyConstraints.FreezeRotation;
                gameObject.layer = OvLayers.NpcSeated;
            }
            else
            {
                // Falls back where it sat, lying flat (the long capsule never stands under the roof): feet in front, head
                // behind if there is room, otherwise the other way round, along the van, or shifted a little (FindLyingSpot,
                // tested before the switch, so its own sitting capsule is not in the way). With no room anywhere (wedged
                // between the partition and bodies) it lies down as a short capsule that grows back to full length over a
                // few ticks, so physics eases it free instead of shoving it out of a wall at once.
                Vector3 facing = Flat(_rb.rotation * Vector3.forward);
                facing = facing.sqrMagnitude > 1e-4f ? facing.normalized : Vector3.forward;
                Vector3 seat = _rb.position + Vector3.up * (Radius + 0.02f);
                bool fits = FindLyingSpot(seat, facing, out Vector3 feet, out Vector3 centre);
                rotation = Quaternion.LookRotation(Vector3.up, -feet);
                position = centre + feet * (Height * 0.5f);
                _growing = !fits;
                _shapeHeight = fits ? Height : Radius * 2f + 0.01f;
                SetShape(_shapeHeight, Height * 0.5f);
                _rb.mass = DownedMass;
                _rb.constraints = RigidbodyConstraints.None;
                gameObject.layer = OvLayers.NpcBody;
            }
            _rb.angularVelocity = Vector3.zero;
            _rb.position = position;
            _rb.rotation = rotation;
            transform.SetPositionAndRotation(position, rotation);
            _rb.WakeUp();
        }

        private void SetShape(float height) => SetShape(height, height * 0.5f);

        // centreY: the capsule's middle above the root (feet); a short capsule growing back keeps the full body's middle.
        private void SetShape(float height, float centreY)
        {
            _capsule.direction = 1;
            _capsule.radius = Radius;
            _capsule.height = height;
            _capsule.center = new Vector3(0f, centreY, 0f);
        }

        // Everything a lying body collides with, except sitters (NpcSeated ignores NpcBody) and the bay's query volumes.
        private const int LyingBlockMask = ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.NpcSeated));
        private static readonly float[] LyingShifts = { 0f, 0.35f, -0.35f, 0.7f, -0.7f };
        private static readonly Collider[] LyingHits = new Collider[8];

        // Where a sitter at 'seat' (lying axis height) can lie down: feet toward 'facing', away from it, then along the van's
        // long axis (the bay is only 1.6 m wide), in place first, then shifted along that direction. False = nowhere free;
        // then feet/centre are the in-place pose along the van (or 'facing' outside one).
        private bool FindLyingSpot(Vector3 seat, Vector3 facing, out Vector3 feet, out Vector3 centre)
        {
            Vector3 along = Vector3.Cross(Vector3.up, facing); // outside a van: across the facing
            foreach (VanCargoSpace space in VanCargoSpace.All)
                if (space != null && space.isActiveAndEnabled && space.Contains(seat, 0.3f))
                {
                    Vector3 axis = Flat(space.Rotation * Vector3.forward);
                    if (axis.sqrMagnitude > 1e-4f) along = axis.normalized;
                    break;
                }
            if (Vector3.Dot(along, facing) < 0f) along = -along;
            Vector3[] directions = { facing, -facing, along, -along };
            foreach (float shift in LyingShifts)
                foreach (Vector3 direction in directions)
                {
                    Vector3 c = seat + direction * shift;
                    if (!LyingFits(c, direction)) continue;
                    feet = direction;
                    centre = c;
                    return true;
                }
            feet = along;
            centre = seat;
            return false;
        }

        // Whether the full lying capsule (axis through 'centre' along 'direction') overlaps nothing but this NPC itself.
        private bool LyingFits(Vector3 centre, Vector3 direction)
        {
            Vector3 half = direction * Mathf.Max(0f, Height * 0.5f - Radius);
            int count = Physics.OverlapCapsuleNonAlloc(centre - half, centre + half, Radius - 0.02f, LyingHits, LyingBlockMask,
                QueryTriggerInteraction.Ignore);
            bool free = true;
            for (int i = 0; i < count; i++)
            {
                if (free && !LyingHits[i].transform.IsChildOf(transform)) free = false;
                LyingHits[i] = null;
            }
            return free;
        }

        // ---------- Forces (called by GreyboxNpc) ----------

        // GreyboxNpc's hit, kick and crawl numbers were tuned on the 40 kg body: impulses scale with the current mass, so a
        // lighter downed body (0.7) gets the same velocity change as before (hit 60 -> 42 N·s, still 1.5 m/s; kick 25 ->
        // 17.5 N·s, 0.63 m/s; crawl speed unchanged).
        private float LimpScale => _rb != null && Mass > 0f ? _rb.mass / Mass : 1f;

        public void Push(Vector3 impulse, Vector3 worldPoint)
        {
            if (_rb == null) return;
            _rb.AddForceAtPosition(impulse * LimpScale, worldPoint, ForceMode.Impulse);
        }

        public void Kick(Point ankle, Vector3 impulse) => Push(impulse, PointWorld((int)ankle));

        /// <summary>One crawl step: a small hop (so ground friction lets go for a moment) plus a push along the ground.</summary>
        public void Scoot(Vector3 horizontalImpulse, float hopSpeed)
        {
            if (_rb == null) return;
            _rb.AddForce(horizontalImpulse * LimpScale + Vector3.up * (hopSpeed * _rb.mass), ForceMode.Impulse);
        }

        /// <summary>Contacts with these colliders are ignored for a while (the van that just knocked the NPC over, so the body
        /// is not born inside its bumper), then restored.</summary>
        public void IgnoreFor(IEnumerable<Collider> others, float seconds)
        {
            if (!IsLive(_capsule)) return;
            foreach (Collider c in others)
            {
                if (!IsLive(c) || c.isTrigger || c is WheelCollider || c == _capsule || _ignored.Contains(c)) continue;
                Physics.IgnoreCollision(_capsule, c, true);
                _ignored.Add(c);
            }
            _restoreIgnoredAt = Time.time + seconds;
        }

        private void RestoreIgnored()
        {
            if (IsLive(_capsule))
                foreach (Collider c in _ignored)
                    if (IsLive(c))
                        Physics.IgnoreCollision(_capsule, c, false);
            _ignored.Clear();
        }

        private static bool IsLive(Collider c) => c != null && c.enabled && c.gameObject.activeInHierarchy;

        private void FixedUpdate()
        {
            if (_rb == null) return;
            if (_ignored.Count > 0 && Time.time >= _restoreIgnoredAt) RestoreIgnored();
            if (_growing && _capsule != null)
            {
                _shapeHeight = Mathf.MoveTowards(_shapeHeight, Height, UnseatGrowSpeed * Time.fixedDeltaTime);
                SetShape(_shapeHeight, Height * 0.5f);
                _growing = _shapeHeight < Height;
            }
            if (!_seated && RollDamping > 0f)
            {
                Vector3 axis = _rb.rotation * Vector3.up;
                float spin = Vector3.Dot(_rb.angularVelocity, axis);
                _rb.angularVelocity -= axis * (spin * Mathf.Clamp01(RollDamping * Time.fixedDeltaTime));
            }
            HoldPins();
        }

        private void OnCollisionEnter(Collision collision)
        {
            _lastContact = Time.fixedTime;
            if (collision.contactCount == 0) return;
            if (collision.rigidbody != null && collision.rigidbody.isKinematic) return;
            ContactPoint contact = collision.GetContact(0);
            float speed = Mathf.Abs(Vector3.Dot(collision.relativeVelocity, contact.normal));
            Thud(speed, collision.collider, contact.point);
            Impact?.Invoke(speed, collision.collider);
        }

        // A body landing: on the van (layer Vehicle: floor, bumper, wheel housings) or on anything else, louder the
        // harder it lands. Sitters make none (they are placed, not dropped). The library's cooldown stops bounce spam.
        private void Thud(float speed, Collider other, Vector3 point)
        {
            if (_seated || speed < ThudMinSpeed || other == null) return;
            string id = other.gameObject.layer == OvLayers.Vehicle ? SfxIds.ThudVan : SfxIds.ThudGround;
            float loud = Mathf.InverseLerp(ThudMinSpeed, Mathf.Max(ThudMinSpeed + 0.01f, ThudFullSpeed), speed);
            Sfx.PlayAt(id, point, Mathf.Lerp(0.35f, 1f, loud));
        }

        private void OnCollisionStay(Collision collision) => _lastContact = Time.fixedTime;

        // ---------- Claims (IGrabPointTarget) ----------

        /// <summary>Claims the point of the body axis nearest to 'hit' for 'holder' (one slot per holder, at most
        /// MaxHolders). point = the slot, local = the point in Rigidbody space.</summary>
        public bool TryClaim(object holder, Vector3 hit, out int point, out Vector3 local, out GrabPhysicsProfile profile)
        {
            point = -1;
            local = Vector3.zero;
            profile = Profile;
            if (holder == null || !Grabbable || _rb == null || _capsule == null || !isActiveAndEnabled || SlotOf(holder) >= 0)
                return false;
            point = FreeSlot(); // -1 when MaxHolders already hold it
            if (point < 0) return false;
            local = AxisLocal(hit);
            Claims[point] = new Claim { Holder = holder, Local = local };
            return true;
        }

        public bool IsClaimValid(object holder, int point) =>
            holder != null && point >= 0 && point < Claims.Length && ReferenceEquals(Claims[point].Holder, holder) &&
            Grabbable && _rb != null && isActiveAndEnabled;

        public void Release(object holder, int point)
        {
            if (point < 0 || point >= Claims.Length || !ReferenceEquals(Claims[point].Holder, holder)) return;
            Claims[point] = default;
            if (holder is DebugPin pin) _pins.Remove(pin);
        }

        /// <summary>Every holder lets go (woke up, stood up, sat up).</summary>
        public void RevokeAll()
        {
            Array.Clear(Claims, 0, Claims.Length);
            _pins.Clear();
        }

        /// <summary>Tears one hold loose: the hold nearest the landmark 'preferred' along the body (within TearRadius; an
        /// ankle kick tears feet-side holds first), otherwise a random one.</summary>
        public bool Tear(Point preferred)
        {
            int slot = NearestClaim(PointLocal[(int)preferred].y, TearRadius);
            if (slot < 0) slot = RandomHeld();
            if (slot < 0) return false;
            Release(Claims[slot].Holder, slot);
            return true;
        }

        private int NearestClaim(float along, float radius)
        {
            int best = -1;
            float bestDistance = radius;
            for (int i = 0; i < Claims.Length; i++)
            {
                if (Claims[i].Holder == null) continue;
                float d = Mathf.Abs(Claims[i].Local.y - along);
                if (d <= bestDistance)
                {
                    best = i;
                    bestDistance = d;
                }
            }
            return best;
        }

        private int RandomHeld()
        {
            int count = HolderCount;
            if (count == 0) return -1;
            int pick = UnityEngine.Random.Range(0, count);
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder != null && pick-- == 0) return i;
            return -1;
        }

        private int SlotOf(object holder)
        {
            for (int i = 0; i < Claims.Length; i++)
                if (ReferenceEquals(Claims[i].Holder, holder)) return i;
            return -1;
        }

        private int FreeSlot()
        {
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder == null) return i;
            return -1;
        }

        // The point of the capsule's axis nearest to a world point, in Rigidbody space, kept EndInset inside its ends. From
        // the physics pose, not the interpolated transform (up to 9 cm apart at 4.5 m/s). Uses the capsule's current shape,
        // so it is also right for a seated (1 m) or a growing capsule.
        private Vector3 AxisLocal(Vector3 world)
        {
            float along = (Quaternion.Inverse(_rb.rotation) * (world - _rb.position)).y;
            float half = _capsule.height * 0.5f, mid = _capsule.center.y;
            return new Vector3(0f, Mathf.Clamp(along, mid - half + EndInset, mid + half - EndInset), 0f);
        }

        /// <summary>Static force one hand needs to lift the axis point 's' (m from the feet) of the lying body while its other
        /// end rests on the ground: the body turns about the centre of the other end cap (lever rule, see the header).</summary>
        public float OneHandLoad(float s)
        {
            if (_rb == null) return 0f;
            float weight = _rb.mass * Physics.gravity.magnitude;
            float c = _rb.centerOfMass.y;
            float footPivot = Radius, headPivot = Height - Radius;
            if (s > c) return weight * (c - footPivot) / Mathf.Max(0.05f, s - footPivot);
            if (s < c) return weight * (headPivot - c) / Mathf.Max(0.05f, headPivot - s);
            return weight;
        }

        /// <summary>For the grab hint: where a grab at 'world' would take hold (accusative: "взять за ..."), with " — тяжело"
        /// when one hand cannot lift that point; null if the grab would be refused.</summary>
        public string GrabHintName(Vector3 world)
        {
            if (!Grabbable || _rb == null || _capsule == null || HolderCount >= MaxHolders) return null;
            if (_seated) return "беглеца";
            float s = AxisLocal(world).y;
            float scale = Height / 1.5f;
            string zone = Zones[Zones.Length - 1].name;
            foreach ((float from, string name) in Zones)
                if (s >= from * scale)
                {
                    zone = name;
                    break;
                }
            return OneHandLoad(s) > Profile.MaxForce ? zone + " — тяжело" : zone;
        }

        // ---------- F9 debug pins (offline stand-ins for other holders) ----------

        /// <summary>Pins the axis point nearest to 'hit', 'lift' metres above where it is now, held with the same profile
        /// as a player's hand. A hit within PinToggleRadius of an existing pin removes that pin instead. True = pinned.</summary>
        public bool TogglePin(Vector3 hit, float lift)
        {
            if (_rb == null || _capsule == null) return false;
            Vector3 at = _rb.position + _rb.rotation * AxisLocal(hit);
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin old = _pins[i];
                if (Vector3.Distance(ClaimWorld(old.Slot), at) <= PinToggleRadius)
                {
                    Release(old, old.Slot);
                    return false;
                }
            }
            var pin = new DebugPin();
            if (!TryClaim(pin, hit, out int slot, out _, out _)) return false;
            pin.Slot = slot;
            pin.Anchor = ClaimWorld(slot) + Vector3.up * lift;
            _pins.Add(pin);
            return true;
        }

        public void UnpinAll()
        {
            for (int i = _pins.Count - 1; i >= 0; i--)
                Release(_pins[i], _pins[i].Slot);
        }

        private void HoldPins()
        {
            GrabPhysicsProfile profile = Profile;
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin pin = _pins[i];
                if (!IsClaimValid(pin, pin.Slot))
                {
                    Release(pin, pin.Slot);
                    _pins.Remove(pin); // a revoked pin is no longer in Claims, so Release did not drop it from the list
                    continue;
                }
                // Shaped like a player's hand (PhysicsGrabber's point hold): sideways capped apart when the profile says so.
                Vector3 world = ClaimWorld(pin.Slot);
                Vector3 error = pin.Anchor - world;
                Vector3 velocity = _rb.GetPointVelocity(world);
                Vector3 force;
                bool held = profile.SoloHorizontalMaxForce > 0f
                    ? GrabPhysicsSolver.TryCalculateRelativeGrounded(error, Vector3.zero, velocity, _rb.mass, profile, out force)
                    : GrabPhysicsSolver.TryCalculateRelative(error, Vector3.zero, velocity, _rb.mass, profile, out force);
                if (!held)
                {
                    Release(pin, pin.Slot);
                    continue;
                }
                GrabPhysicsSolver.ApplyForce(_rb, world, force);
            }
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        // Holds red, anatomical landmarks yellow.
        private void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.yellow;
            for (int i = 0; i < PointLocal.Length; i++)
                Gizmos.DrawWireSphere(PointWorld(i), 0.04f);
            if (Claims == null) return;
            Gizmos.color = Color.red;
            for (int i = 0; i < Claims.Length; i++)
                if (Claims[i].Holder != null)
                    Gizmos.DrawWireSphere(ClaimWorld(i), 0.06f);
        }
    }
}
