using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Offline test helper for NPC capture stage 1: drives the van with nobody in the driver seat, so the only player can
    // ride in the cargo bay (GreyboxCargoRider) at speed, through turns and braking, or step out of a moving van.
    // P cycles off -> 15 km/h -> 40 km/h -> off. On: hold the speed with gentle S-turns. Off: brake hard, then the
    // handbrake. Inactive while someone drives (VanDriveInput owns the van then) and switches itself off when they do.
    [RequireComponent(typeof(VanController))]
    public sealed class GreyboxVanAutopilot : MonoBehaviour
    {
        public KeyCode Key = KeyCode.P; // not F10: on Windows the editor can swallow it as the menu-bar key
        public float[] SpeedsKmh = { 15f, 40f };
        [Tooltip("Steer input amplitude of the S-turns (0..1).")]
        public float SteerAmplitude = 0.2f;
        public float SteerPeriod = 8f;

        private VanController _van;
        private GreyboxVanSeat _seat;
        private GreyboxCargoRider _rider;
        private int _mode; // 0 = off, i > 0 = SpeedsKmh[i - 1]
        private bool _braking;
        private float _phase;

        private void Awake()
        {
            _van = GetComponent<VanController>();
            _seat = GetComponent<GreyboxVanSeat>();
        }

        private bool SomeoneDrives => _seat != null && _seat.Driving;

        private void Update()
        {
            if (SomeoneDrives)
            {
                _mode = 0;
                _braking = false;
                return;
            }
            if (!Input.GetKeyDown(Key)) return;
            _mode = (_mode + 1) % (SpeedsKmh.Length + 1);
            _braking = _mode == 0;
            if (_mode == 1) _phase = 0f;
        }

        private void FixedUpdate()
        {
            if (SomeoneDrives) return;
            float speed = _van.SpeedKmh;
            if (_mode > 0)
            {
                float target = SpeedsKmh[_mode - 1];
                _van.Handbrake = false;
                _van.Throttle = Mathf.Clamp((target - speed) / 8f, -1f, 1f);
                _phase += Time.fixedDeltaTime;
                _van.Steer = SteerAmplitude * Mathf.Sin(_phase * 2f * Mathf.PI / Mathf.Max(1f, SteerPeriod));
                return;
            }
            if (!_braking) return;
            _van.Steer = 0f;
            // A negative throttle only brakes while rolling forward; below that it would reverse.
            if (speed > 1.5f)
            {
                _van.Throttle = -1f;
                return;
            }
            _van.Throttle = 0f;
            _van.Handbrake = true;
            _braking = false;
        }

        private void OnGUI()
        {
            if (SomeoneDrives) return;
            string text;
            if (_mode > 0) text = $"Тест-автопилот: {SpeedsKmh[_mode - 1]:0} км/ч ({Key} — дальше / стоп)";
            else if (_braking) text = "Тест-автопилот: торможение";
            else if (SpeedsKmh.Length > 0 && RiderInside()) text = $"{Key} — тест-автопилот ({SpeedsKmh[0]:0} / {SpeedsKmh[SpeedsKmh.Length - 1]:0} км/ч)";
            else return;
            var style = new GUIStyle(GUI.skin.label) { fontSize = 16, alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0f, 40f, Screen.width, 26f), text, style);
        }

        private bool RiderInside()
        {
            if (_rider == null && _seat != null && _seat.Pawn != null)
                _seat.Pawn.Body.TryGetComponent(out _rider);
            return _rider != null && _rider.Inside;
        }
    }
}
