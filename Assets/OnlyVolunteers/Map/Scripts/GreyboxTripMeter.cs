using UnityEngine;
using OnlyVolunteers.Vehicles;

namespace OnlyVolunteers.Map
{
    // Grey-box driving test helper: trip timer/odometer (T resets) and F1-F8 teleports to key points of the map plan.
    [RequireComponent(typeof(VanController))]
    public sealed class GreyboxTripMeter : MonoBehaviour
    {
        [System.Serializable]
        public sealed class Spot
        {
            public string Name;
            public Vector3 Position;
            public float Yaw;
        }

        public Spot[] Spots = new Spot[0];
        [Tooltip("Optional: when the pawn is on foot, F1-F8 move the pawn instead of the van.")]
        public GreyboxVanSeat Seat;

        private VanController _van;
        private float _tripStart;
        private float _tripDistance;
        private Vector3 _lastPosition;
        private string _lastSpot = "-";

        private void Awake()
        {
            _van = GetComponent<VanController>();
            ResetTrip();
        }

        private void Update()
        {
            Vector3 p = transform.position;
            _tripDistance += Vector3.Distance(new Vector3(p.x, 0f, p.z), new Vector3(_lastPosition.x, 0f, _lastPosition.z));
            _lastPosition = p;

            if (Input.GetKeyDown(KeyCode.T)) ResetTrip();
            for (int i = 0; i < Spots.Length && i < 8; i++)
            {
                if (Input.GetKeyDown(KeyCode.F1 + i))
                {
                    if (Seat != null && !Seat.Driving && Seat.Pawn != null)
                        Seat.Pawn.Teleport(Spots[i].Position + Quaternion.Euler(0f, Spots[i].Yaw, 0f) * Vector3.right * 4f + Vector3.up * 0.1f, Spots[i].Yaw);
                    else
                    {
                        _van.ResetUpright(Spots[i].Position + Vector3.up * 0.5f, Spots[i].Yaw);
                        if (TryGetComponent(out SeaReturnTracker tracker)) tracker.Rebase();
                    }
                    _lastSpot = Spots[i].Name;
                    ResetTrip();
                }
            }
        }

        private void ResetTrip()
        {
            _tripStart = Time.time;
            _tripDistance = 0f;
            _lastPosition = transform.position;
        }

        private void OnGUI()
        {
            float t = Time.time - _tripStart;
            float avg = t > 0.5f ? _tripDistance / t * 3.6f : 0f;
            // Bottom-right, so it does not cover the van's key help in the top-left on narrow game views.
            float h = 64 + 18 * Mathf.Min(Spots.Length, 8);
            var r = new Rect(Screen.width - 330, Screen.height - h - 12, 318, h);
            GUI.Box(r, GUIContent.none);
            GUI.Label(new Rect(r.x + 8, r.y + 4, 300, 20), $"Поездка: {t / 60f:0}:{t % 60f:00.0}  {_tripDistance:0} м  ср. {avg:0} км/ч");
            GUI.Label(new Rect(r.x + 8, r.y + 22, 300, 20), $"T — сброс, старт от: {_lastSpot}");
            GUI.Label(new Rect(r.x + 8, r.y + 40, 300, 20), "Телепорт:");
            for (int i = 0; i < Spots.Length && i < 8; i++)
                GUI.Label(new Rect(r.x + 16, r.y + 58 + 18 * i, 300, 20), $"F{i + 1} — {Spots[i].Name}");
        }
    }
}
