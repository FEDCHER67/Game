using System.Collections;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.Serialization;

namespace OnlyVolunteers.Map
{
    // Getting into the van (Enter, called by the pawn's GreyboxInteractor on E next to the driver door) and out of it
    // (E while driving, (almost) stopped, on the driver's side). It swaps the live input and camera: the pawn (KCC player
    // with its own camera, or the walker + follow camera) on foot, VanDriveInput + VanCameraRig on Main Camera driving.
    // Exactly one camera and AudioListener stay on.
    // NPC capture stage 1 (canon section 151): the driver is visible in the cab (GreyboxDriverDummy, offline stand-in) and
    // works the doors with the test-scene keys (1 front left, 2 front right, 3 sliding, 4 rear pair, F all; sent as
    // requests to the force-limited doors, VanDriveInput.GreyboxDoorRules). Entering still
    // switches the pawn off, which also drops anything its PhysicsGrabber holds (PhysicsGrabber.OnDisable releases).
    // The van parts the stage needs are added here for scenes built before them (cargo space, interior colliders, rider,
    // autopilot); BuildRevision says which builder made the scene, older scenes get a "rebuild" warning.
    [RequireComponent(typeof(VanController))]
    public sealed class GreyboxVanSeat : MonoBehaviour
    {
        // MapGreyboxBuilder writes this into BuildRevision. 3 = NPC capture stage 1, chunk 3 (van: doors, loading, driver).
        public const int CurrentBuildRevision = 3;

        [FormerlySerializedAs("Walker")] public GreyboxPawn Pawn;
        public VanCameraRig VanCamera;
        public float EnterDistance = 3.5f;
        public float MaxExitSpeedKmh = 12f;
        [Tooltip("Van-local point next to the driver door (left-hand drive).")]
        public Vector3 DoorPoint = new(-1.6f, 0f, 0.6f);
        [Tooltip("Set by MapGreyboxBuilder (CurrentBuildRevision); lower = the scene was built by an older builder.")]
        public int BuildRevision;

        public bool Driving { get; private set; }

        private const float ExitStepUp = 1.2f, ExitMinNormalY = 0.7f, ExitHeight = 1.8f, ExitClearance = 0.25f;
        // What the exit ground ray sees (not NPCs, not the cargo-bay volumes) and what may not be at the exit point (the
        // pawn's own capsule and the cargo-bay volumes aside).
        private const int ExitGroundMask = ~((1 << OvLayers.VehicleInterior) | OvLayers.NpcMask);
        private const int ExitBlockMask = ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.Player));
        private readonly Collider[] _overlaps = new Collider[16];

        private VanController _van;
        private VanDriveInput _input;
        private VanCargoSpace _space;
        private Camera _mainCamera;
        private AudioListener _mainListener;

        private void Awake()
        {
            _van = GetComponent<VanController>();
            _input = GetComponent<VanDriveInput>();
            // Before any Start: free NPCs make their CharacterControllers ignore every van collider in their Start, the
            // new steps and partition included. Both are idempotent and may already be on a newer Van.prefab.
            if (!TryGetComponent(out VanCargoSpace _))
                gameObject.AddComponent<VanCargoSpace>();
            if (!TryGetComponent(out VanInteriorColliders _))
                gameObject.AddComponent<VanInteriorColliders>();
            if (Pawn != null) Pawn.Seat = this; // the pawn reports Stance.Seated while we drive
            if (VanCamera != null)
            {
                _mainCamera = VanCamera.GetComponent<Camera>();
                _mainListener = VanCamera.GetComponent<AudioListener>();
            }
        }

        private void Start()
        {
            SetDriving(false);
            // Scenes built before GreyboxInteractor: E on foot lives there now. The interactor finds the pawn's
            // InventoryInput in its Start and takes its E over (ExternalPickup), so one press never does two things.
            if (Pawn != null && !Pawn.Body.TryGetComponent(out GreyboxInteractor _))
            {
                var interactor = Pawn.Body.gameObject.AddComponent<GreyboxInteractor>();
                interactor.Pawn = Pawn;
                interactor.Seat = this;
                interactor.Cargo = TryGetComponent(out GreyboxVanCargo cargo) ? cargo : gameObject.AddComponent<GreyboxVanCargo>();
            }
            // Scenes built before the cargo rider (NPC capture stage 1): ride in the cargo bay without a rebuild.
            if (Pawn is GreyboxKccPawn && !Pawn.Body.TryGetComponent(out GreyboxCargoRider _))
                Pawn.Body.gameObject.AddComponent<GreyboxCargoRider>();
            // Offline test drive (P) so the only player can ride in the cargo bay of a moving van.
            if (!TryGetComponent(out GreyboxVanAutopilot _))
                gameObject.AddComponent<GreyboxVanAutopilot>();
            // The driver as others would see them, and the driver's door keys (requests, rear pair together).
            if (!TryGetComponent(out GreyboxDriverDummy dummy))
                dummy = gameObject.AddComponent<GreyboxDriverDummy>();
            if (dummy.Seat == null) dummy.Seat = this;
            if (dummy.ViewCamera == null) dummy.ViewCamera = VanCamera;
            if (_input != null)
            {
                _input.GreyboxDoorRules = true;
                // The driver door swings through the exit point: it passes through the pawn as before instead of stalling
                // on it (cargo doors do stall on players, stage 1).
                foreach (VanDoor front in new[] { _input.FrontLeft, _input.FrontRight })
                    if (front != null) front.BlockMask &= ~OvLayers.PlayerMask;
            }
            if (BuildRevision < CurrentBuildRevision)
                Debug.LogWarning($"[Greybox] This map scene was built before NPC capture stage 1 (builder revision {BuildRevision} < " +
                                 $"{CurrentBuildRevision}); it runs with runtime fallbacks. Rebuild it: OnlyVolunteers/Map/Build Rough Greybox (latest plan).");
        }

        private void Update()
        {
            // The frame the interactor used E to get in must not also get straight back out.
            if (Pawn == null || !Driving || !Input.GetKeyDown(KeyCode.E) || !GreyboxInput.EFree) return;
            if (Mathf.Abs(_van.SpeedKmh) <= MaxExitSpeedKmh) GetOut();
        }

        public bool CanEnter => !Driving && NearDoor();

        public void Enter()
        {
            if (!CanEnter) return;
            GreyboxInput.UseE();
            SetDriving(true);
            StartCoroutine(SwingDriverDoor());
        }

        // Not from inside the cargo bay: most of the bay is within EnterDistance of the driver door, and getting in from
        // there would be a free way out through the cab partition (a shut bay must stay shut).
        private bool NearDoor() => Pawn != null && Pawn.Controlled &&
            Vector3.Distance(Pawn.Position, transform.TransformPoint(DoorPoint)) <= EnterDistance && !InCargoBay(Pawn.Position);

        // The pawn's position is at its feet on the floor: test half a metre up (as GreyboxVanCargo.AtInsideHandle).
        private bool InCargoBay(Vector3 feet) =>
            (_space != null || TryGetComponent(out _space)) && _space.Contains(feet + transform.up * 0.5f);

        private void GetOut()
        {
            // The driver door; parked against a wall, a fence, a facade or an NPC: the passenger side, then behind the van.
            // Never into the sea: if every dry place is blocked, the first dry one as before; all wet: stay in.
            Vector3? fallback = null;
            Vector3 p = default;
            float yaw = 0f;
            bool found = false;
            for (int i = 0; i < 3 && !found; i++)
            {
                float side = i == 0 ? 1f : -1f;
                Vector3 candidate = i < 2 ? ExitPoint(side) : RearExitPoint();
                if (SeaReturnZone.InSea(candidate)) continue;
                candidate = OnExitGround(candidate);
                float candidateYaw = i < 2 ? transform.eulerAngles.y - 90f * side : transform.eulerAngles.y + 180f;
                if (fallback == null)
                {
                    fallback = candidate;
                    yaw = candidateYaw;
                }
                if (ExitBlocked(candidate)) continue;
                p = candidate;
                yaw = candidateYaw;
                found = true;
            }
            if (!found)
            {
                if (fallback == null) return;
                p = fallback.Value;
            }
            // Teleport first: the KCC player is still inactive, so it wakes up already outside the van.
            GreyboxInput.UseE();
            Pawn.Teleport(p, yaw);
            SetDriving(false);
            StartCoroutine(SwingDriverDoor());
        }

        // side 1 = driver door, -1 = the mirrored passenger point. DoorPoint was set for the 0.3 m walker; a fatter capsule
        // (KCC 0.5 m) steps out further so it does not touch the van.
        private Vector3 ExitPoint(float side)
        {
            var local = new Vector3(DoorPoint.x * side, DoorPoint.y, DoorPoint.z);
            return transform.TransformPoint(local) - transform.right * (side * Mathf.Max(0f, Pawn.Radius - 0.3f));
        }

        // Behind the rear doors and their step (the builder's foot spawn uses the same 4.6 m for the 0.5 m KCC).
        private Vector3 RearExitPoint() => transform.TransformPoint(new Vector3(0f, DoorPoint.y, -(4.1f + Pawn.Radius)));

        // The ground by the door, not an awning, a bus-stop roof or a branch above it (the look map), nor an NPC's head, a
        // fence or a wall top: the highest walkable surface at most ExitStepUp above the van's floor level.
        private Vector3 OnExitGround(Vector3 p)
        {
            float ground = float.NegativeInfinity;
            foreach (RaycastHit hit in Physics.RaycastAll(p + Vector3.up * 3f, Vector3.down, 10f, ExitGroundMask, QueryTriggerInteraction.Ignore))
            {
                if (hit.point.y > p.y + ExitStepUp || hit.normal.y <= ExitMinNormalY) continue;
                if (hit.collider.transform.IsChildOf(transform) || hit.collider.GetComponentInParent<GreyboxNpc>() != null) continue;
                ground = Mathf.Max(ground, hit.point.y);
            }
            if (!float.IsNegativeInfinity(ground)) p.y = ground + 0.05f;
            return p;
        }

        // Something (other than this van) in the pawn's capsule at the exit point, or a wall between the cab and it: parked
        // against a facade, the exit point is inside the building, whose hollow shell the capsule alone does not touch.
        private bool ExitBlocked(Vector3 feet)
        {
            float radius = Pawn.Radius;
            Vector3 low = feet + Vector3.up * (radius + ExitClearance);
            Vector3 high = feet + Vector3.up * Mathf.Max(radius + ExitClearance, ExitHeight - radius);
            int n = Physics.OverlapCapsuleNonAlloc(low, high, radius, _overlaps, ExitBlockMask, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
                if (!Ours(_overlaps[i].transform)) return true;
            Vector3 from = transform.position + transform.up * 1.2f, to = feet + Vector3.up * 1.2f;
            Vector3 d = to - from;
            foreach (RaycastHit hit in Physics.RaycastAll(from, d.normalized, d.magnitude, ExitBlockMask & ~OvLayers.NpcMask, QueryTriggerInteraction.Ignore))
                if (!Ours(hit.collider.transform)) return true;
            return false;
        }

        // This van (body, doors, steps, interior colliders) or the pawn's own body, wherever it was switched off.
        private bool Ours(Transform t) =>
            t.IsChildOf(transform) || Pawn != null && (t.IsChildOf(Pawn.transform) || t.IsChildOf(Pawn.Body));

        private void SetDriving(bool driving)
        {
            Driving = driving;
            // On foot with the KCC player, Main Camera sits wherever it was left (the world origin at first); start the
            // chase blend from the player's eye instead of flying in across the map.
            if (driving && VanCamera != null && Pawn != null && Pawn.ViewCamera != null)
                VanCamera.transform.SetPositionAndRotation(Pawn.ViewCamera.transform.position, Pawn.ViewCamera.transform.rotation);
            // Disabling the KCC input frees the cursor; keep it captured so the van camera can be steered right away.
            bool locked = Cursor.lockState == CursorLockMode.Locked;
            if (Pawn != null) Pawn.SetControlled(!driving);
            if (driving && locked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }
            if (_input != null) _input.enabled = driving;
            if (!driving)
            {
                _van.Throttle = 0f;
                _van.Steer = 0f;
                _van.Handbrake = true;
            }
            if (VanCamera != null) VanCamera.enabled = driving;
            // Main Camera renders and listens while driving, and on foot only for a pawn without its own camera.
            bool main = driving || Pawn == null || Pawn.ViewCamera == null;
            if (_mainCamera != null) _mainCamera.enabled = main;
            if (_mainListener != null) _mainListener.enabled = main;
        }

        private IEnumerator SwingDriverDoor()
        {
            VanDoor door = _input != null ? _input.FrontLeft : null;
            if (door == null) yield break;
            door.Open();
            yield return new WaitForSeconds(0.9f);
            door.Close();
        }

        private void OnGUI()
        {
            // On foot the hints come from GreyboxInteractor.
            if (!Driving) return;
            const string hint = "E — выйти из бусика (на малой скорости)     1–4, F — двери";
            var style = new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0f, Screen.height - 70f, Screen.width - 340f, 30f), hint, style); // left of the trip panel
        }
    }
}
