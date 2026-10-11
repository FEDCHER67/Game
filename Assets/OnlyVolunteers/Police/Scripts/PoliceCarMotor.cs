using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // Arcade police car (design section 2.1-2.2): a Rigidbody on four raycast springs, no WheelColliders and no
    // VanController (GreyboxNpc and the crowd take FindAnyObjectByType<VanController> for the players' van).
    // - Drive: a(v) = A - K v, braking Brake m/s^2, top speed from the brain (MaxSpeed). In play PoliceDirector sets A, K,
    //   LateralGrip and Brake once a second from the van (PoliceConfig balance: a little under the van's); the serialized
    //   numbers are only the fallback without a van.
    // - Grip: sideways velocity cancelled up to LateralGrip m/s^2 (x0.25 for 1.5 s after a spin-out); yaw from a bicycle
    //   model (steering 35 deg at low speed down to 12 deg at 90 km/h).
    // - Path: follows a PoliceRoute (A* from PoliceMapData, or a closed patrol loop) with a look-ahead of 6 + 0.5 v m,
    //   cuts the inside of bends by up to (road width / 2 - 0.9 m) or keeps right on patrol, and plans its speed with the
    //   same corner model as the bake (PoliceRoadModel), braking ahead of each bend. Direct mode steers at a point.
    // - Reverses when its target is behind it (leaving a parking space nose-in, stuck against a wall).
    // - Rights itself after 3 s on its side or roof; knocks over free crowd NPCs it hits above 15 km/h, like the van.
    [RequireComponent(typeof(Rigidbody))]
    public sealed class PoliceCarMotor : MonoBehaviour
    {
        public enum DriveMode : byte { Stop, Route, Direct }

        [Header("Body")]
        public float Mass = 1300f;
        public Vector3 CenterOfMass = new(0f, 0.45f, 0.1f);
        [Tooltip("Wheel contact points (local x, z); the springs hang from SpringTop above the ground line.")]
        public Vector2 WheelOffset = new(0.72f, 1.35f);
        public float SpringTop = 0.7f, SpringRest = 0.82f, SpringRate = 26600f, SpringDamping = 3500f;

        [Header("Drive")]
        public float Accel = 3.0f, AccelPerMps = 0.03f, Brake = 8f, LateralGrip = 7.5f;
        public float SteerLow = 35f, SteerHigh = 12f, Wheelbase = 2.7f;
        [Tooltip("Share of LateralGrip the speed planner takes bends at. The bake's corner model assumes the full road width " +
                 "(outside - apex - outside); the car keeps to the centre and the inside, so it plans a little slower.")]
        [Range(0.3f, 1f)] public float CornerPlanFactor = 0.7f;
        public float ReverseSpeed = 3f;
        [Tooltip("Path look-ahead: base metres + metres per m/s, capped. Short enough that the car keeps inside the road at " +
                 "bends (pure pursuit cuts a bend by about 0.3 x the look-ahead) and gets back onto it quickly after a K-turn.")]
        public float LookBase = 4f, LookPerMps = 0.3f, LookMax = 11f;
        [Tooltip("Corner cutting (chases): the car's centre stays at least this far inside the road edge (m). Lamps, signs and " +
                 "facades stand right at the kerb in the old town: 2.2 m keeps the car body about 1.3 m off it.")]
        public float CutMargin = 2.2f;
        public float KnockSpeedKmh = 15f;
        [Tooltip("Feelers at the front corners steer round lamp posts, parked cars and facade corners in the car's path (m of " +
                 "aim-point shift at most).")]
        public bool AvoidObstacles = true;
        public float AvoidShift = 2.5f;

        // ---------- What the brain asks for ----------
        [System.NonSerialized] public DriveMode Mode = DriveMode.Stop;
        [System.NonSerialized] public float MaxSpeed;            // m/s
        [System.NonSerialized] public bool CutCorners, KeepRight;
        [System.NonSerialized] public Vector2 DirectPoint;
        [System.NonSerialized] public float StopAtEnd = 1f;      // m/s at the end of an open route (0 = stop there)
        [System.NonSerialized] public bool Handbrake;

        public readonly PoliceRoute Route = new();
        public Rigidbody Body { get; private set; }
        public float Speed => Body != null ? Vector3.Dot(Body.linearVelocity, transform.forward) : 0f;
        public float SpeedKmh => Speed * 3.6f;
        public Vector2 Position2 => new(transform.position.x, transform.position.z);
        public Vector2 Forward2 => new Vector2(transform.forward.x, transform.forward.z).normalized;
        public bool Grounded { get; private set; }
        public bool Flipped => transform.up.y < 0.3f;
        /// <summary>Metres along the route from its start to the car (projected), and the route length.</summary>
        public float Progress { get; private set; }
        public float RouteLength => _s.Length > 0 && _count > 0 ? _s[_count - 1] : 0f;
        public bool AtRouteEnd => Mode == DriveMode.Route && !Route.Loop && RouteLength - Progress < 3f;
        public int Laps { get; private set; }
        public int StuckEpisodes { get; private set; }
        public int Flips { get; private set; }
        public int Hops { get; private set; }

        private CarModel _model;
        private float[] _s = new float[0], _t = new float[0], _v = new float[0], _caps = new float[0];
        private int _count, _seg;
        private float _spinUntil;
        private float _stuckSince = -1f, _flippedSince = -1f;
        private bool _reversing;
        private float _reverseTime, _reverseMax;
        private int _stuckTries;
        private Vector2 _watchPos;
        private float _watchSince = -1f;
        private float _nextPedCheck;
        private bool _pedAhead;
        private readonly RaycastHit[] _hit = new RaycastHit[1];

        public bool PedestrianAhead => _pedAhead;
        public bool Reversing => _reversing;
        /// <summary>In a K-turn or still turning round slowly toward its target: the brain should not swap routes now.</summary>
        public bool Manoeuvring => _reversing || (Mathf.Abs(Speed) < 2.5f && _alphaAbs > 60f);
        private float _alphaAbs;
        /// <summary>The last solid thing it hit harder than 1.5 m/s (not the ground): name and game time (tests, debugging).</summary>
        public string LastHit { get; private set; } = "";

        private void OnCollisionEnter(Collision collision)
        {
            if (collision.relativeVelocity.magnitude < 1.5f || collision.collider is TerrainCollider) return;
            LastHit = $"{collision.collider.name} {collision.relativeVelocity.magnitude:0.0} m/s @{Time.time:0.0}";
        }

        private void Awake()
        {
            Body = GetComponent<Rigidbody>();
            Body.mass = Mass;
            Body.centerOfMass = CenterOfMass;
            Body.interpolation = RigidbodyInterpolation.Interpolate;
            Body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            Body.linearDamping = 0f; // the drive model's K term is the drag
            Body.angularDamping = 0.5f;
            // Standing crowd NPCs (CharacterControllers, layer NpcBody) and sitters do not stop the car: it knocks the standing
            // ones over by script. Lying bodies (the capsule and the stage-9 ragdoll, same layer) still meet it: their
            // colliders include Vehicle with a higher override priority (NpcRagdoll.CollideWithVehicles; GPT review
            // 2026-10-07, finding 3: the car used to drive through them).
            Body.excludeLayers = OvLayers.NpcMask;
            BuildModel();
        }

        private void BuildModel() => _model = new CarModel(120f, Accel, AccelPerMps, LateralGrip * CornerPlanFactor, Brake, 1.8f);

        /// <summary>Drive numbers from the brain's balance (PoliceDirector): full-throttle a(v) = accel - accelPerMps v,
        /// lateral grip and braking (m/s^2). The current route's bend speeds are planned again when they change.</summary>
        public void SetPerformance(float accel, float accelPerMps, float lateralGrip, float brake)
        {
            if (Mathf.Abs(accel - Accel) < 1e-3f && Mathf.Abs(accelPerMps - AccelPerMps) < 1e-5f &&
                Mathf.Abs(lateralGrip - LateralGrip) < 1e-3f && Mathf.Abs(brake - Brake) < 1e-3f) return;
            Accel = Mathf.Max(0.1f, accel);
            AccelPerMps = Mathf.Max(0f, accelPerMps);
            LateralGrip = Mathf.Max(1f, lateralGrip);
            Brake = Mathf.Max(1f, brake);
            BuildModel();
            if (_count >= 2 && _count == Route.Points.Count) RouteChanged(true);
        }

        // ---------- Routes ----------

        /// <summary>Takes over Route (filled by the caller) and precomputes its bend caps with the bake's corner model.</summary>
        public void RouteChanged(bool keepProgress = false)
        {
            _count = Route.Points.Count;
            if (_s.Length < _count)
            {
                int size = Mathf.NextPowerOfTwo(_count);
                _s = new float[size];
                _t = new float[size];
                _v = new float[size];
                _caps = new float[size];
            }
            _model.VMax = PoliceConfig.Kmh(120f);
            if (_count >= 2)
                PoliceRoadModel.Profile(Route.Points, Route.Widths, _model, 0f, float.NaN, true, _s, _t, _v, _caps);
            if (!keepProgress)
            {
                _seg = 0;
                Laps = 0;
            }
            _seg = Mathf.Clamp(_seg, 0, Mathf.Max(0, _count - 2));
            Locate(true);
        }

        /// <summary>Starts a closed route at the point nearest the car.</summary>
        public void StartLoopNearest()
        {
            RouteChanged();
            float best = float.MaxValue;
            for (int i = 0; i < _count - 1; i++)
            {
                float d = SegDistance(i, Position2, out _);
                if (Vector2.Dot(Route.Points[i + 1] - Route.Points[i], Forward2) < 0f) d += 1.5f; // the leg the car faces
                if (d < best)
                {
                    best = d;
                    _seg = i;
                }
            }
            Locate(false);
        }

        // Projected progress: the closest point on the next few segments (never a jump to another part of the route:
        // out-and-back loops pass the same road twice; there a segment against the car's heading counts 1.5 m farther, so
        // the way back is taken once the car has turned round).
        private void Locate(bool wide)
        {
            if (_count < 2)
            {
                Progress = 0f;
                return;
            }
            Vector2 p = Position2;
            int bestSeg = _seg;
            float bestD = float.MaxValue, bestT = 0f;
            int window = wide ? _count : 6;
            Vector2 heading = Forward2;
            for (int k = 0; k < window; k++)
            {
                int i = _seg + k;
                if (Route.Loop) i %= _count - 1;
                else if (i > _count - 2) break;
                float d = SegDistance(i, p, out float t);
                if (Vector2.Dot(Route.Points[i + 1] - Route.Points[i], heading) < 0f) d += 1.5f;
                if (d < bestD - 0.01f)
                {
                    bestD = d;
                    bestSeg = i;
                    bestT = t;
                }
            }
            if (Route.Loop && bestSeg < _seg && _seg - bestSeg > (_count - 1) / 2) Laps++;
            _seg = bestSeg;
            Progress = _s[_seg] + bestT * (_s[_seg + 1] - _s[_seg]);
        }

        private float SegDistance(int i, Vector2 p, out float t)
        {
            Vector2 a = Route.Points[i], ab = Route.Points[i + 1] - a;
            float len2 = ab.sqrMagnitude;
            t = len2 > 1e-6f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / len2) : 0f;
            return Vector2.Distance(a + ab * t, p);
        }

        // Point at distance 'along' on the route (wraps on a loop, clamps on an open route); the segment it lies on.
        private Vector2 PointAt(float along, out int seg)
        {
            float total = _s[_count - 1];
            if (Route.Loop && total > 0f) along = Mathf.Repeat(along, total);
            else along = Mathf.Clamp(along, 0f, total);
            seg = 0;
            int lo = 0, hi = _count - 2;
            while (lo < hi)
            {
                int mid = (lo + hi + 1) / 2;
                if (_s[mid] <= along) lo = mid;
                else hi = mid - 1;
            }
            seg = lo;
            float len = _s[seg + 1] - _s[seg];
            float f = len > 1e-4f ? (along - _s[seg]) / len : 0f;
            return Vector2.Lerp(Route.Points[seg], Route.Points[seg + 1], f);
        }

        // ---------- Physics ----------

        private void FixedUpdate()
        {
            using Unity.Profiling.ProfilerMarker.AutoScope scope = PoliceDirector.Marker.Auto();
            float dt = Time.fixedDeltaTime;
            int grounded = Suspension();
            Grounded = grounded >= 2;
            Upright(dt);
            if (_count != Route.Points.Count) RouteChanged(true); // the route was refilled without RouteChanged: never index past it
            if (Mode == DriveMode.Route && _count >= 2) Locate(false);

            Vector2 target;
            float desired;
            switch (Mode)
            {
                case DriveMode.Route when _count >= 2:
                    target = RouteTarget(out desired);
                    break;
                case DriveMode.Direct:
                    target = DirectPoint;
                    desired = MaxSpeed;
                    break;
                default:
                    target = Position2 + Forward2 * 5f;
                    desired = 0f;
                    break;
            }
            if (_pedAhead) desired = Mathf.Min(desired, KeepRight ? 0f : PoliceConfig.Kmh(15f));
            desired = Mathf.Min(desired, _carAheadSpeed);
            if (Mode != DriveMode.Stop && !_reversing && AvoidObstacles) Whiskers(ref target, ref desired);
            Drive(target, desired, dt);
        }

        // Two feelers from the front corners at bumper height, as long as about 0.6 s of driving: a lamp post, a parked
        // car, a pole or a facade corner in the car's own path pushes the aim point to the other side; both feelers
        // touching (a wall ahead) also slows the car so it can stop in time. Terrain, vehicles and people are ignored
        // (the van is the target; people have their own check).
        private void Whiskers(ref Vector2 target, ref float desired)
        {
            float v = Mathf.Max(0f, Speed);
            float len = Mathf.Clamp(2.5f + v * 0.6f, 3f, 16f);
            float left = Whisker(-WheelOffset.x - 0.15f, len), right = Whisker(WheelOffset.x + 0.15f, len);
            if (left >= len && right >= len) return;
            float pushL = 1f - left / len, pushR = 1f - right / len;
            var side = new Vector2(transform.right.x, transform.right.z);
            if (side.sqrMagnitude < 1e-4f) return;
            side.Normalize();
            float reach = Mathf.Min(AvoidShift, Vector2.Distance(target, Position2) * 0.5f);
            target += side * (pushL - pushR) * reach;
            if (pushL > 0f && pushR > 0f)
                desired = Mathf.Min(desired, Mathf.Max(2f, Mathf.Sqrt(2f * Brake * 0.7f * Mathf.Max(0f, Mathf.Min(left, right) - 2f))));
        }

        private float Whisker(float x, float len)
        {
            Vector3 origin = transform.TransformPoint(new Vector3(x, 0.65f, WheelOffset.y + 0.7f));
            if (Physics.Raycast(origin, transform.forward, out RaycastHit hit, len, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore) &&
                !(hit.collider is TerrainCollider) && hit.rigidbody != Body)
                return hit.distance;
            return len;
        }

        // Look-ahead point (+ corner cut or keep-right) and the speed the corner model allows from here.
        private Vector2 RouteTarget(out float desired)
        {
            float v = Mathf.Max(0f, Speed);
            float look = Mathf.Min(LookMax, LookBase + LookPerMps * v);
            // A dead-end turnaround ahead: aim at it until slow, then the target swings behind and the K-turn starts.
            if (v > 2.5f)
            {
                float toReversal = ReversalAhead(look);
                if (toReversal >= 0f) look = Mathf.Max(1f, toReversal);
            }
            Vector2 target = PointAt(Progress + look, out int seg);
            // Slow and well off the path's direction (a K-turn, back onto the road after one): a farther point, outside the
            // turning circle (radius ~3.9 m), so the car swings round once instead of see-sawing at a point it cannot reach.
            if (v < 6f && look < 9f)
            {
                Vector2 to = target - Position2;
                if (to.sqrMagnitude > 1e-4f && Mathf.Abs(Vector2.SignedAngle(to, Forward2)) > 50f)
                {
                    look = 9f;
                    target = PointAt(Progress + look, out seg);
                }
            }
            float width = Route.Widths.Count > seg ? Route.Widths[seg] : 6f;
            Vector2 along = Route.Points[seg + 1] - Route.Points[seg];
            along = along.sqrMagnitude > 1e-6f ? along.normalized : Forward2;
            Vector2 right = new(along.y, -along.x);
            if (KeepRight)
                target += right * Mathf.Min(1.2f, width * 0.25f);
            else if (CutCorners)
            {
                // Inside of the next bend within the look-ahead: shift toward it, by up to (width / 2 - 0.9 m).
                float turn = TurnAhead(seg, look + 15f);
                float cut = Mathf.Max(0f, width * 0.5f - CutMargin) * Mathf.Clamp01(Mathf.Abs(turn) / 45f);
                target += (turn > 0f ? -right : right) * cut;
            }
            // Speed: every cap ahead (and the end of an open route) reached with braking.
            desired = MaxSpeed;
            float horizon = 160f;
            float total = _s[_count - 1];
            // From two vertices back: a car cutting a bend projects past its apex before it has turned.
            int i = Route.Loop ? (_seg - 2 + (_count - 1)) % (_count - 1) : Mathf.Max(0, _seg - 2);
            for (int k = 0; k < _count; k++, i++)
            {
                if (Route.Loop) i %= _count - 1;
                else if (i >= _count) break;
                float ahead = _s[i] - Progress;
                if (Route.Loop && ahead < -total * 0.5f) ahead += total;
                if (ahead < -8f) continue;
                ahead = Mathf.Max(0f, ahead);
                if (ahead > horizon) break;
                float cap = _caps[i];
                if (Reversal(i)) cap = Mathf.Min(cap, 1.5f); // a dead end turnaround: nearly stop, then a K-turn
                bool end = !Route.Loop && i == _count - 1;
                if (end) cap = Mathf.Min(cap, StopAtEnd);
                // Planned with 80 % of the brakes, so the car is at the cap before the bend, not in it (bends 3 m early; the
                // end of an open route exactly there: a parking space is filled, not stopped short of).
                desired = Mathf.Min(desired, Mathf.Sqrt(cap * cap + 2f * Brake * 0.8f * Mathf.Max(0f, end ? ahead : ahead - 3f)));
            }
            return target;
        }

        // Metres to the next reversal vertex within 'within' m (-1 = none).
        private float ReversalAhead(float within)
        {
            float total = _s[_count - 1];
            int i = _seg + 1;
            for (int k = 0; k < _count; k++, i++)
            {
                if (Route.Loop) i %= _count - 1;
                else if (i >= _count - 1) break;
                float ahead = _s[i] - Progress;
                if (Route.Loop && ahead < 0f) ahead += total;
                if (ahead > within) break;
                if (Reversal(i)) return ahead;
            }
            return -1f;
        }

        // The route turns back on itself at vertex i (out and back to a dead end).
        private bool Reversal(int i)
        {
            if (i <= 0 && !Route.Loop || i >= _count - 1) return false;
            int prev = i - 1 < 0 ? _count - 2 : i - 1;
            Vector2 a = Route.Points[i] - Route.Points[prev], b = Route.Points[i + 1] - Route.Points[i];
            return a.sqrMagnitude > 1e-4f && b.sqrMagnitude > 1e-4f && Vector2.Angle(a, b) > 150f;
        }

        // Signed turn (degrees, + = left) summed over the vertices in the next 'within' metres.
        private float TurnAhead(int seg, float within)
        {
            float sum = 0f;
            float total = _s[_count - 1];
            int i = _seg + 1;
            for (int k = 0; k < 12; k++, i++)
            {
                if (Route.Loop) i %= _count - 1;
                else if (i >= _count - 1) break;
                float ahead = _s[i] - Progress;
                if (Route.Loop && ahead < 0f) ahead += total;
                if (ahead > within) break;
                int prev = i - 1 < 0 ? _count - 2 : i - 1;
                Vector2 a = Route.Points[i] - Route.Points[prev], b = Route.Points[i + 1] - Route.Points[i];
                sum += Vector2.SignedAngle(a, b);
            }
            return sum;
        }

        private void Drive(Vector2 target, float desired, float dt)
        {
            Vector3 vel = Body.linearVelocity;
            Vector3 fwd = transform.forward, right = transform.right;
            float vf = Vector3.Dot(vel, fwd);
            Vector2 to = target - Position2;
            float dist = to.magnitude;
            float alpha = dist > 0.1f ? Vector2.SignedAngle(to, Forward2) : 0f; // + = target to the right
            _alphaAbs = Mathf.Abs(alpha);
            // K-turn: the target is close behind (nose-in parking, a dead end, an overshot junction): back up, swinging the
            // nose toward it, until it is ahead again (at most 4 s); a stuck episode asks for 1.5 s.
            if (_reversing)
            {
                _reverseTime += dt;
                if ((Mathf.Abs(alpha) < 60f && _reverseTime > 0.5f) || _reverseTime > _reverseMax || Mode == DriveMode.Stop) _reversing = false;
            }
            else if (Mode != DriveMode.Stop && desired > 0.5f && Mathf.Abs(alpha) > 110f && dist < 20f && vf < 2.5f)
                BackUp(4f);
            bool reverse = _reversing;
            StuckCheck(desired, vf);
            Watchdog(desired);

            float steerMax = Mathf.Lerp(SteerLow, SteerHigh, Mathf.InverseLerp(PoliceConfig.Kmh(10f), PoliceConfig.Kmh(90f), Mathf.Abs(vf)));
            float steer;
            float wanted;
            if (reverse)
            {
                steer = -Mathf.Sign(alpha) * steerMax;  // backing up turns the nose toward the target
                wanted = -ReverseSpeed;
            }
            else
            {
                // Pure pursuit: the steering angle that puts the car on an arc through the target.
                float ld = Mathf.Max(3f, dist);
                steer = Mathf.Atan2(2f * Wheelbase * Mathf.Sin(alpha * Mathf.Deg2Rad), ld) * Mathf.Rad2Deg;
                steer = Mathf.Clamp(steer, -steerMax, steerMax);
                wanted = desired;
                // The target is behind (a route that turns back, a goal it overshot): pure pursuit would barely steer and
                // carve a wide arc off the road. Full lock toward it and slow right down; slow enough, the K-turn takes over.
                if (Mathf.Abs(alpha) > 100f)
                {
                    steer = Mathf.Sign(alpha) * steerMax;
                    wanted = Mathf.Min(wanted, 3f);
                }
            }
            if (!Grounded) return;
            // Longitudinal.
            float accel;
            if (Handbrake || Mode == DriveMode.Stop) accel = -Mathf.Clamp(vf / dt, -Brake, Brake);
            else if (wanted >= 0f)
                accel = vf < wanted ? Mathf.Min(_model.Accel(Mathf.Max(0f, vf)), (wanted - vf) * 3f) : -Mathf.Min(Brake, (vf - wanted) * 6f);
            else
                accel = vf > wanted ? -Mathf.Min(Brake, (vf - wanted) * 3f) : 0f;
            Vector3 flatFwd = Vector3.ProjectOnPlane(fwd, Vector3.up).normalized;
            Body.AddForce(flatFwd * accel, ForceMode.Acceleration);
            // Lateral grip.
            float grip = Time.time < _spinUntil ? LateralGrip * 0.25f : LateralGrip;
            float vs = Vector3.Dot(vel, right);
            Body.AddForce(right * Mathf.Clamp(-vs / dt, -grip, grip), ForceMode.Acceleration);
            // Yaw from the bicycle model, limited by the grip.
            float yawRate = vf * Mathf.Tan(steer * Mathf.Deg2Rad) / Wheelbase;
            float maxRate = grip * 1.05f / Mathf.Max(1f, Mathf.Abs(vf));
            yawRate = Mathf.Clamp(yawRate, -maxRate, maxRate);
            if (Time.time >= _spinUntil)
            {
                Vector3 av = Body.angularVelocity;
                av.y = Mathf.MoveTowards(av.y, yawRate, 10f * dt);
                Body.angularVelocity = av;
            }
            Body.AddForce(-transform.up * (25f * vel.magnitude)); // a little downforce, like the van
        }

        private int Suspension()
        {
            int grounded = 0;
            Vector3 up = transform.up;
            for (int i = 0; i < 4; i++)
            {
                float x = (i & 1) == 0 ? -WheelOffset.x : WheelOffset.x, z = i < 2 ? WheelOffset.y : -WheelOffset.y;
                Vector3 top = transform.TransformPoint(new Vector3(x, SpringTop, z));
                if (Physics.RaycastNonAlloc(top, -up, _hit, SpringRest, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore) == 0) continue;
                grounded++;
                float compression = SpringRest - _hit[0].distance;
                float speed = Vector3.Dot(Body.GetPointVelocity(top), up);
                float force = Mathf.Max(0f, compression * SpringRate - speed * SpringDamping);
                Body.AddForceAtPosition(up * force, top);
            }
            return grounded;
        }

        // On its side or roof for 3 s: back on the wheels where it is, facing the way it was going.
        private void Upright(float dt)
        {
            if (!Flipped)
            {
                _flippedSince = -1f;
                return;
            }
            if (_flippedSince < 0f) _flippedSince = Time.time;
            if (Time.time - _flippedSince < 3f) return;
            _flippedSince = -1f;
            Flips++;
            Vector3 f = Vector3.ProjectOnPlane(transform.forward, Vector3.up);
            if (f.sqrMagnitude < 1e-3f) f = Vector3.ProjectOnPlane(transform.up, Vector3.up);
            Teleport(transform.position + Vector3.up * 1.5f, f.sqrMagnitude > 1e-3f ? Quaternion.LookRotation(f).eulerAngles.y : transform.eulerAngles.y);
        }

        // Wants to move but does not (a wall, a tree): reverse for 1.5 s; the third time in a row, if no camera sees it
        // or the place ahead, hop 8 m along the route.
        private void StuckCheck(float desired, float vf)
        {
            bool wants = Mode != DriveMode.Stop && desired > 1f && !Handbrake;
            if (!wants || Mathf.Abs(vf) > 1f || Reversing)
            {
                if (!wants || Mathf.Abs(vf) > 2f) _stuckTries = 0;
                _stuckSince = -1f;
                return;
            }
            if (_stuckSince < 0f) _stuckSince = Time.time;
            if (Time.time - _stuckSince < 2.5f) return;
            _stuckSince = -1f;
            _stuckTries++;
            if (_stuckTries == 1) StuckEpisodes++;
            if (_stuckTries < 3)
            {
                BackUp(1.5f);
                return;
            }
            _stuckTries = 0;
            TryHop();
        }

        // Wants to drive but has got nowhere for 6 s (see-sawing, pinned against something while rolling a little): a stuck
        // episode too; hop along the route when nobody sees it, else back up once more.
        private void Watchdog(float desired)
        {
            bool wants = Mode != DriveMode.Stop && desired > 1f && !Handbrake;
            if (!wants || _watchSince < 0f)
            {
                _watchSince = Time.time;
                _watchPos = Position2;
                return;
            }
            if (Time.time - _watchSince < 6f) return;
            bool stuck = (Position2 - _watchPos).sqrMagnitude < 9f;
            _watchSince = Time.time;
            _watchPos = Position2;
            if (!stuck) return;
            StuckEpisodes++;
            if (!TryHop()) BackUp(2f);
        }

        // 8 m on along the route, when no camera sees the car or the place ahead (Route mode only). True when it hopped.
        private bool TryHop()
        {
            if (Mode != DriveMode.Route || _count < 2) return false;
            Vector2 ahead = PointAt(Progress + 8f, out int seg);
            CrowdDirector crowd = CrowdDirector.Instance;
            if (crowd != null && (crowd.Visible(transform.position, 0f) || crowd.Visible(crowd.Ground(ahead), 0f))) return false;
            Vector2 dir = Route.Points[seg + 1] - Route.Points[seg];
            float yaw = dir.sqrMagnitude > 1e-4f ? Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg : transform.eulerAngles.y;
            float h = crowd != null ? crowd.Ground(ahead).y : transform.position.y;
            Teleport(new Vector3(ahead.x, h + 0.6f, ahead.y), yaw);
            Hops++;
            return true;
        }

        public void Teleport(Vector3 position, float yaw)
        {
            Body.linearVelocity = Vector3.zero;
            Body.angularVelocity = Vector3.zero;
            Body.position = position;
            Body.rotation = Quaternion.Euler(0f, yaw, 0f);
            transform.SetPositionAndRotation(position, Body.rotation);
            _reversing = false;
            if (Mode == DriveMode.Route && _count >= 2) Locate(true);
        }

        private void BackUp(float seconds)
        {
            _reversing = true;
            _reverseTime = 0f;
            _reverseMax = seconds;
        }

        /// <summary>A hard knock: the tyres let go for 1.5 s and the car spins.</summary>
        public void SpinOut()
        {
            _spinUntil = Time.time + 1.5f;
            Body.AddTorque(Vector3.up * Random.Range(-1f, 1f) * 4f, ForceMode.VelocityChange);
        }

        // ---------- Pedestrians ----------

        private void Update()
        {
            if (Time.time < _nextPedCheck) return;
            using Unity.Profiling.ProfilerMarker.AutoScope scope = PoliceDirector.Marker.Auto();
            _nextPedCheck = Time.time + 0.2f;
            _pedAhead = false;
            Vector3 p = transform.position, f = transform.forward;
            float v = Speed;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || npc.State != NpcState.Free || PoliceOfficer.IsOfficer(npc)) continue;
                Vector3 rel = npc.transform.position - p;
                if (Mathf.Abs(rel.y) > 2f) continue;
                float along = Vector3.Dot(rel, f), across = Mathf.Abs(Vector3.Dot(rel, transform.right));
                if (along < -2.2f || across > 1.6f) continue;
                if (along < 2.6f && v * 3.6f > KnockSpeedKmh)
                {
                    // Noted first: KnockOver raises GreyboxNpc.Incident at once, and the police must know it was their car.
                    PoliceDirector.NotePoliceKnock(npc.transform.position);
                    // The car's own colliders get the knock grace (the parts born inside it pass out); 2026-10-11, was
                    // 0.9 x its velocity with the grace on the van's colliders instead (GreyboxNpc.KnockOver(Rigidbody)).
                    npc.KnockOver(Body);
                    continue;
                }
                if (along > 0f && along < 6f + Mathf.Max(0f, v) * 0.6f) _pedAhead = true;
            }
            // Another police car in the way (two cars meeting at the same junction or on one van's tail): no faster than it
            // moves along this car's way, so they do not crash into each other.
            _carAheadSpeed = float.PositiveInfinity;
            PoliceDirector director = PoliceDirector.Instance;
            if (director == null) return;
            foreach (PoliceUnit u in director.Units)
            {
                if (u == null || u.Motor == this) continue;
                Vector3 rel = u.transform.position - p;
                if (Mathf.Abs(rel.y) > 3f) continue;
                float along = Vector3.Dot(rel, f), across = Mathf.Abs(Vector3.Dot(rel, transform.right));
                if (along < 1f || across > 2.4f || along > 6f + Mathf.Max(0f, v) * 0.9f) continue;
                float theirs = Vector3.Dot(u.Motor.Body.linearVelocity, f);
                // At least a crawl (2 m/s): two cars nose to nose never lock each other for good (a bump at walking pace).
                _carAheadSpeed = Mathf.Min(_carAheadSpeed, Mathf.Max(2f, theirs - 1f));
            }
        }

        private float _carAheadSpeed = float.PositiveInfinity;

        private void OnDrawGizmosSelected()
        {
            if (Route.Points.Count < 2) return;
            Gizmos.color = new Color(0.2f, 0.4f, 1f);
            float y = transform.position.y + 0.5f;
            for (int i = 0; i < Route.Points.Count - 1; i++)
                Gizmos.DrawLine(new Vector3(Route.Points[i].x, y, Route.Points[i].y), new Vector3(Route.Points[i + 1].x, y, Route.Points[i + 1].y));
        }
    }
}
