using System;
using System.Collections.Generic;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The physical body of a downed grey-box NPC (NPC capture stage 1): ONE rigidbody with grab points, no bone ragdoll
    // yet (canon section 151, draft section 3; the 11-body ragdoll is stage B8). The limbs only dangle visually.
    // GreyboxNpc switches it on when the NPC goes down (Activate: capsule + Rigidbody on the NPC root, layer NpcBody) and
    // off when it stands up again (Deactivate: both removed, the CharacterController takes over).
    // Grab points are root-local (root at the feet, body along local up): collar, wrists, pelvis, ankles. Holders claim
    // the free point nearest to where they grabbed (within ClaimRadius); one holder per point, at most three per body.
    // PhysicsGrabber (Vadim's LMB grab) holds through IGrabPointTarget with NpcGrabProfile: 350 N per holder, so one
    // player lifts the collar end (~230 N) while the heels drag, and two (700 N > 392 N weight) carry it like a hammock.
    // The NPC logic can take any claim back (RevokeAll on waking, Tear when it kicks free). F9 debug pins (TogglePin) are
    // holders too: they stand in for a second or third player offline.
    // State is plain data (Holders, HolderCount, Grabbable) for a network version later.
    [DisallowMultipleComponent]
    public sealed class GreyboxNpcBody : MonoBehaviour, IGrabPointTarget
    {
        public enum Point { Collar, LeftWrist, RightWrist, Pelvis, LeftAnkle, RightAnkle }

        /// <summary>Grab points in root space, indexed by Point.</summary>
        public static readonly Vector3[] PointLocal =
        {
            new(0f, 1.30f, -0.12f), new(-0.35f, 0.85f, 0f), new(0.35f, 0.85f, 0f),
            new(0f, 0.80f, 0f), new(-0.10f, 0.08f, 0f), new(0.10f, 0.08f, 0f),
        };

        // What the grab hint calls each point (accusative: "схватить (...)").
        private static readonly string[] PointNames = { "шиворот", "запястье", "запястье", "таз", "лодыжку", "лодыжку" };

        public const int MaxHolders = 3;

        [Tooltip("How holders hold a point (Map/Data/NpcGrabProfile.asset). Empty = the same numbers built in code.")]
        public GrabPhysicsProfile GrabProfile;

        [Header("Body")]
        public float Mass = 40f;
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
        public float Friction = 0.5f;
        [Tooltip("Per second, only around the body's long axis: a lone capsule would otherwise roll away like a log.")]
        public float RollDamping = 4f;

        [Header("Grab points")]
        public float ClaimRadius = 0.6f;

        // Plain data. Holders[i] holds Point i (null = free). Grabbable: set by GreyboxNpc (while lying down, and while
        // running for a cargo door; NpcGrabProfile finds both layers, NpcBody and NpcSeated).
        [NonSerialized] public object[] Holders = new object[6];
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
            public int Point;
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
                foreach (object h in Holders) if (h != null) n++;
                return n;
            }
        }

        public bool HeldAt(Point p) => Holders[(int)p] != null;

        /// <summary>Held, and only by the ankles (feet first, head bouncing: costs the NPC condition when fast).</summary>
        public bool OnlyAnklesHeld
        {
            get
            {
                bool ankle = false;
                for (int i = 0; i < Holders.Length; i++)
                {
                    if (Holders[i] == null) continue;
                    if (i != (int)Point.LeftAnkle && i != (int)Point.RightAnkle) return false;
                    ankle = true;
                }
                return ankle;
            }
        }

        // From the physics pose when there is a body (the transform shows the interpolated one).
        public Vector3 PointWorld(int point) =>
            _rb != null ? _rb.position + _rb.rotation * PointLocal[point] : transform.TransformPoint(PointLocal[point]);

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
                    "{\"acquireDistance\":2.2,\"holdDistance\":1.2,\"springStrength\":600,\"dampingRatio\":1," +
                    "\"maxForce\":350,\"maxLinearSpeed\":4.5,\"maxAngularSpeed\":8,\"breakDistance\":2.2," +
                    "\"acquisitionLayers\":{\"m_Bits\":" + OvLayers.NpcMask + "}}", _fallbackProfile);
                return _fallbackProfile;
            }
        }

        private PhysicsMaterial Material => _material != null ? _material : _material = new PhysicsMaterial("NpcBody")
        {
            dynamicFriction = Friction,
            staticFriction = Friction,
            bounciness = 0f,
            frictionCombine = PhysicsMaterialCombine.Average,
            bounceCombine = PhysicsMaterialCombine.Minimum,
        };

        private void Awake()
        {
            if (_rb == null) _freeLayer = gameObject.layer;
        }

        // ---------- On / off ----------

        /// <summary>Becomes a 40 kg physics body where the NPC stands now (lying down is up to physics: a hit topples it).</summary>
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
            _rb.mass = Mass;
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

        /// <summary>Sitting in the cargo bay (awake there): upright, rotation frozen, 1 m capsule, layer NpcSeated (ignores
        /// lying bodies and other sitters). Back to lying: laid on its back where it sat, then the full capsule.</summary>
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

        public void Push(Vector3 impulse, Vector3 worldPoint)
        {
            if (_rb == null) return;
            _rb.AddForceAtPosition(impulse, worldPoint, ForceMode.Impulse);
        }

        public void Kick(Point ankle, Vector3 impulse) => Push(impulse, PointWorld((int)ankle));

        /// <summary>One crawl step: a small hop (so ground friction lets go for a moment) plus a push along the ground.</summary>
        public void Scoot(Vector3 horizontalImpulse, float hopSpeed)
        {
            if (_rb == null) return;
            _rb.AddForce(horizontalImpulse + Vector3.up * (hopSpeed * _rb.mass), ForceMode.Impulse);
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
            if (Impact == null || collision.contactCount == 0) return;
            if (collision.rigidbody != null && collision.rigidbody.isKinematic) return;
            float speed = Mathf.Abs(Vector3.Dot(collision.relativeVelocity, collision.GetContact(0).normal));
            Impact(speed, collision.collider);
        }

        private void OnCollisionStay(Collision collision) => _lastContact = Time.fixedTime;

        // ---------- Claims (IGrabPointTarget) ----------

        public bool TryClaim(object holder, Vector3 hit, out int point, out Vector3 local, out GrabPhysicsProfile profile)
        {
            point = -1;
            local = Vector3.zero;
            profile = Profile;
            if (holder == null || !Grabbable || _rb == null || !isActiveAndEnabled) return false;
            if (HolderCount >= MaxHolders || HolderOf(holder) >= 0) return false;
            point = NearestFree(hit);
            if (point < 0) return false;
            Holders[point] = holder;
            local = PointLocal[point];
            return true;
        }

        public bool IsClaimValid(object holder, int point) =>
            holder != null && point >= 0 && point < Holders.Length && ReferenceEquals(Holders[point], holder) &&
            Grabbable && _rb != null && isActiveAndEnabled;

        public void Release(object holder, int point)
        {
            if (point < 0 || point >= Holders.Length || !ReferenceEquals(Holders[point], holder)) return;
            Holders[point] = null;
            if (holder is DebugPin pin) _pins.Remove(pin);
        }

        /// <summary>Every holder lets go (woke up, stood up, sat up).</summary>
        public void RevokeAll()
        {
            Array.Clear(Holders, 0, Holders.Length);
            _pins.Clear();
        }

        /// <summary>Tears one hold loose: the holder of 'preferred' if there is one, otherwise a random holder.</summary>
        public bool Tear(Point preferred)
        {
            int point = Holders[(int)preferred] != null ? (int)preferred : RandomHeld();
            if (point < 0) return false;
            Release(Holders[point], point);
            return true;
        }

        private int RandomHeld()
        {
            int count = HolderCount;
            if (count == 0) return -1;
            int pick = UnityEngine.Random.Range(0, count);
            for (int i = 0; i < Holders.Length; i++)
                if (Holders[i] != null && pick-- == 0) return i;
            return -1;
        }

        private int HolderOf(object holder)
        {
            for (int i = 0; i < Holders.Length; i++)
                if (ReferenceEquals(Holders[i], holder)) return i;
            return -1;
        }

        private int NearestFree(Vector3 world)
        {
            int best = -1;
            float bestDistance = ClaimRadius;
            for (int i = 0; i < PointLocal.Length; i++)
            {
                if (Holders[i] != null) continue;
                float d = Vector3.Distance(PointWorld(i), world);
                if (d <= bestDistance)
                {
                    best = i;
                    bestDistance = d;
                }
            }
            return best;
        }

        /// <summary>For the grab hint: the name of the point a grab at 'world' would get, or null if it would be refused.</summary>
        public string FreePointName(Vector3 world)
        {
            if (!Grabbable || _rb == null || HolderCount >= MaxHolders) return null;
            int point = NearestFree(world);
            return point >= 0 ? PointNames[point] : null;
        }

        // ---------- F9 debug pins (offline stand-ins for other holders) ----------

        /// <summary>Pins the free point nearest to 'hit', 'lift' metres above where it is now, held with the same profile
        /// as a player's hand. A hit next to an existing pin removes that pin instead. True = pinned.</summary>
        public bool TogglePin(Vector3 hit, float lift)
        {
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin old = _pins[i];
                if (Vector3.Distance(PointWorld(old.Point), hit) <= ClaimRadius)
                {
                    Release(old, old.Point);
                    return false;
                }
            }
            var pin = new DebugPin();
            if (!TryClaim(pin, hit, out int point, out _, out _)) return false;
            pin.Point = point;
            pin.Anchor = PointWorld(point) + Vector3.up * lift;
            _pins.Add(pin);
            return true;
        }

        public void UnpinAll()
        {
            for (int i = _pins.Count - 1; i >= 0; i--)
                Release(_pins[i], _pins[i].Point);
        }

        private void HoldPins()
        {
            GrabPhysicsProfile profile = Profile;
            for (int i = _pins.Count - 1; i >= 0; i--)
            {
                DebugPin pin = _pins[i];
                if (!IsClaimValid(pin, pin.Point) ||
                    !GrabPhysicsSolver.TryCalculate(_rb, PointLocal[pin.Point], pin.Anchor, profile, out Vector3 world, out Vector3 force))
                {
                    Release(pin, pin.Point);
                    _pins.Remove(pin); // a revoked pin is no longer in Holders, so Release did not drop it from the list
                    continue;
                }
                GrabPhysicsSolver.ApplyForce(_rb, world, force);
            }
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        private void OnDrawGizmosSelected()
        {
            for (int i = 0; i < PointLocal.Length; i++)
            {
                Gizmos.color = Holders != null && Holders[i] != null ? Color.red : Color.yellow;
                Gizmos.DrawWireSphere(PointWorld(i), 0.06f);
            }
        }
    }
}
