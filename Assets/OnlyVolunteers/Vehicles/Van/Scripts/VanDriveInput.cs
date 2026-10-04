using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Keyboard driving, door and upgrade controls for the standalone van test scene (not networked).
    [RequireComponent(typeof(VanController))]
    public sealed class VanDriveInput : MonoBehaviour
    {
        public VanDoor FrontLeft;
        public VanDoor FrontRight;
        public VanDoor Slide;
        public VanDoor RearLeft;
        public VanDoor RearRight;
        public VanCameraRig CameraRig;
        [Tooltip("Optional. Taken from this object, or added if the van has none (test scene only).")]
        public VanUpgrades Upgrades;

        private VanController _van;
        private Vector3 _spawnPosition;
        private float _spawnYaw;
        private bool _showHelp = true;

        private void Awake()
        {
            _van = GetComponent<VanController>();
            if (Upgrades == null && !TryGetComponent(out Upgrades))
                Upgrades = gameObject.AddComponent<VanUpgrades>();
            _spawnPosition = transform.position;
            _spawnYaw = transform.eulerAngles.y;
        }

        private void Update()
        {
            float throttle = 0f;
            if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) throttle += 1f;
            if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) throttle -= 1f;
            float steer = 0f;
            if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) steer += 1f;
            if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) steer -= 1f;
            _van.Throttle = throttle;
            _van.Steer = steer;
            _van.Handbrake = Input.GetKey(KeyCode.Space);

            if (Input.GetKeyDown(KeyCode.Alpha1)) Toggle(FrontLeft);
            if (Input.GetKeyDown(KeyCode.Alpha2)) Toggle(FrontRight);
            if (Input.GetKeyDown(KeyCode.Alpha3)) Toggle(Slide);
            if (Input.GetKeyDown(KeyCode.Alpha4)) { Toggle(RearLeft); Toggle(RearRight); }
            if (Input.GetKeyDown(KeyCode.F)) ToggleAll();
            if (Input.GetKeyDown(KeyCode.Alpha7)) CycleUpgrade(VanUpgradeCategory.Engine);
            if (Input.GetKeyDown(KeyCode.Alpha8)) CycleUpgrade(VanUpgradeCategory.Brakes);
            if (Input.GetKeyDown(KeyCode.Alpha9)) CycleUpgrade(VanUpgradeCategory.Handling);
            if (Input.GetKeyDown(KeyCode.C) && CameraRig != null) CameraRig.ToggleMode();
            if (Input.GetKeyDown(KeyCode.R)) ResetVan();
            if (Input.GetKeyDown(KeyCode.H)) _showHelp = !_showHelp;
            if (Input.GetMouseButtonDown(0)) Cursor.lockState = CursorLockMode.Locked;
            if (Input.GetKeyDown(KeyCode.Escape)) Cursor.lockState = CursorLockMode.None;
            Cursor.visible = Cursor.lockState != CursorLockMode.Locked;
        }

        private static void Toggle(VanDoor door)
        {
            if (door != null) door.Toggle();
        }

        private void ToggleAll()
        {
            bool anyClosed = Closed(FrontLeft) || Closed(FrontRight) || Closed(Slide) || Closed(RearLeft) || Closed(RearRight);
            foreach (VanDoor d in new[] { FrontLeft, FrontRight, Slide, RearLeft, RearRight })
            {
                if (d == null) continue;
                if (anyClosed) d.Open(); else d.Close();
            }
        }

        private static bool Closed(VanDoor d) => d != null && !d.IsOpen;

        // 0 -> 1 -> 2 -> 3 -> 0
        private void CycleUpgrade(VanUpgradeCategory category)
        {
            Upgrades.TrySetLevel(category, (Upgrades.GetLevel(category) + 1) % (VanUpgrades.MaxLevel + 1));
        }

        // R puts the van back on its wheels where it is (or at spawn if it fell off the world).
        private void ResetVan()
        {
            Vector3 p = transform.position.y < -20f ? _spawnPosition : transform.position + Vector3.up * 1.2f;
            float yaw = transform.position.y < -20f ? _spawnYaw : transform.eulerAngles.y;
            _van.ResetUpright(p, yaw);
        }

        private void OnGUI()
        {
            GUI.Label(new Rect(16, 12, 300, 24), $"{Mathf.Abs(_van.SpeedKmh):0} км/ч (макс. {_van.MaxSpeedKmh:0})");
            int max = VanUpgrades.MaxLevel;
            GUI.Label(new Rect(16, 34, 640, 24),
                $"Двигатель {Upgrades.GetLevel(VanUpgradeCategory.Engine)}/{max} · " +
                $"Тормоза {Upgrades.GetLevel(VanUpgradeCategory.Brakes)}/{max} · " +
                $"Управление {Upgrades.GetLevel(VanUpgradeCategory.Handling)}/{max}");
            if (!_showHelp) return;
            GUI.Label(new Rect(16, 56, 640, 160),
                "WASD / стрелки — ехать, Space — ручник, R — поставить на колёса\n" +
                "1 — левая передняя, 2 — правая передняя, 3 — сдвижная, 4 — задние, F — все двери\n" +
                "7 / 8 / 9 — уровень двигателя / тормозов / управления (0→1→2→3→0)\n" +
                "C — камера сзади / из кабины, ЛКМ — захват мыши, Esc — отпустить, H — скрыть подсказку");
        }
    }
}
