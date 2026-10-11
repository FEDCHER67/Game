#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Police.Dev
{
    // Test driver for the police timing (PoliceChaseTest): drives the van along a route like the bake's "reference
    // driver" (corners at LateralAccel 5 m/s^2, brakes at Brake 5 m/s^2, full throttle otherwise), through VanController's
    // Throttle / Steer / Handbrake, only while nobody sits in the driver seat (like GreyboxVanAutopilot). Steering is pure
    // pursuit on a look-ahead point; the corner speed caps come from the bake's corner model (PoliceRoadModel).
    [RequireComponent(typeof(VanController))]
    public sealed class RouteVanDriver : MonoBehaviour
    {
        public float LateralAccel = 5f, Brake = 5f;
        public float StopDistance = 8f;

        public bool Driving { get; private set; }
        public bool Arrived { get; private set; }
        public float StartedAt { get; private set; }
        public float ArrivedAt { get; private set; }
        public Vector2 Goal => _route.Points.Count > 0 ? _route.Points[_route.Points.Count - 1] : Vector2.zero;
        /// <summary>Metres left along the route from the van's projected position.</summary>
        public float Remaining => Driving || Arrived ? Mathf.Max(0f, _s[_count - 1] - _progress) : 0f;

        private VanController _van;
        private GreyboxVanSeat _seat;
        private readonly PoliceRoute _route = new();
        private float[] _s = new float[1], _t = new float[1], _v = new float[1], _caps = new float[1];
        private int _count, _seg;
        private float _progress;

        private void Awake()
        {
            _van = GetComponent<VanController>();
            _seat = GetComponent<GreyboxVanSeat>();
        }

        /// <summary>Drive along these plan points (the last is the goal); widths per segment.</summary>
        public void Drive(IReadOnlyList<Vector2> points, IReadOnlyList<float> widths)
        {
            _route.Clear();
            for (int i = 0; i < points.Count; i++) _route.Add(points[i], i > 0 && widths.Count >= i ? widths[i - 1] : 6f);
            _count = _route.Points.Count;
            _s = new float[_count];
            _t = new float[_count];
            _v = new float[_count];
            _caps = new float[_count];
            var car = new CarModel(_van.MaxSpeedKmh, 2f, 0.02f, LateralAccel, Brake, 2.1f);
            PoliceRoadModel.Profile(_route.Points, _route.Widths, car, 0f, 0f, false, _s, _t, _v, _caps);
            _seg = 0;
            _progress = 0f;
            Driving = _count >= 2;
            Arrived = false;
            StartedAt = Time.time;
        }

        public void Stop()
        {
            Driving = false;
            _van.Throttle = 0f;
            _van.Steer = 0f;
            _van.Handbrake = true;
        }

        private void FixedUpdate()
        {
            if (!Driving || (_seat != null && _seat.Driving)) return;
            Vector2 pos = new(transform.position.x, transform.position.z);
            // Progress: the closest point on the next few segments.
            float best = float.MaxValue;
            int bestSeg = _seg;
            float bestT = 0f;
            for (int i = _seg; i < Mathf.Min(_count - 1, _seg + 6); i++)
            {
                Vector2 a = _route.Points[i], ab = _route.Points[i + 1] - a;
                float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector2.Dot(pos - a, ab) / ab.sqrMagnitude) : 0f;
                float d = (a + ab * t - pos).sqrMagnitude;
                if (d < best)
                {
                    best = d;
                    bestSeg = i;
                    bestT = t;
                }
            }
            _seg = bestSeg;
            _progress = _s[_seg] + bestT * (_s[_seg + 1] - _s[_seg]);
            float left = _s[_count - 1] - _progress;
            float speed = _van.SpeedKmh / 3.6f;
            if (left < StopDistance || Vector2.Distance(pos, Goal) < StopDistance)
            {
                if (!Arrived)
                {
                    Arrived = true;
                    ArrivedAt = Time.time;
                }
                _van.Steer = 0f;
                _van.Throttle = speed > 1f ? -1f : 0f;
                _van.Handbrake = speed <= 1f;
                if (speed <= 1f) Driving = false;
                return;
            }
            // Speed: every cap ahead reached with braking, and a stop at the goal.
            float wanted = _van.MaxSpeedKmh / 3.6f;
            for (int i = _seg + 1; i < _count; i++)
            {
                float ahead = _s[i] - _progress;
                if (ahead > 150f) break;
                float cap = i == _count - 1 ? 0f : _caps[i];
                wanted = Mathf.Min(wanted, Mathf.Sqrt(cap * cap + 2f * Brake * Mathf.Max(0f, ahead - 3f)));
            }
            // Pure pursuit steering.
            float look = 5f + 0.4f * Mathf.Max(0f, speed);
            Vector2 target = PointAt(_progress + look);
            Vector2 fwd = new Vector2(transform.forward.x, transform.forward.z).normalized;
            Vector2 to = target - pos;
            float alpha = Vector2.SignedAngle(to, fwd) * Mathf.Deg2Rad; // + = target to the right
            float steerDeg = Mathf.Atan2(2f * 3.1f * Mathf.Sin(alpha), Mathf.Max(3f, to.magnitude)) * Mathf.Rad2Deg;
            float maxAngle = Mathf.Lerp(_van.MaxSteerAngle, _van.HighSpeedSteerAngle, Mathf.InverseLerp(10f, 90f, Mathf.Abs(_van.SpeedKmh)));
            _van.Steer = Mathf.Clamp(steerDeg / Mathf.Max(1f, maxAngle), -1f, 1f);
            _van.Handbrake = false;
            _van.Throttle = Mathf.Clamp((wanted - speed) / 2f, -1f, 1f);
        }

        private Vector2 PointAt(float along)
        {
            along = Mathf.Clamp(along, 0f, _s[_count - 1]);
            int i = _seg;
            while (i < _count - 2 && _s[i + 1] < along) i++;
            float len = _s[i + 1] - _s[i];
            return Vector2.Lerp(_route.Points[i], _route.Points[i + 1], len > 1e-4f ? (along - _s[i]) / len : 0f);
        }
    }
}
#endif
