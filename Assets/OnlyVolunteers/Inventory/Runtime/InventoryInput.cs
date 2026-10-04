using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Owner-only Input System bindings for the hotbar. Keeps its own actions so it does not touch
    /// the shared InputSystem_Actions asset or the legacy-input player scripts.
    /// Default keys: E pick up, G drop one, 1-8 select, mouse wheel cycles.
    /// </summary>
    public sealed class InventoryInput : MonoBehaviour
    {
        [SerializeField] private NetworkInventory inventory;
        [Tooltip("View used for the pickup ray and drop direction. Defaults to the first child camera.")]
        [SerializeField] private Camera viewCamera;
        [SerializeField] private bool requireLockedCursor = true;

        [SerializeField] private InputAction pickup = new InputAction("Pickup", InputActionType.Button, "<Keyboard>/e");
        [SerializeField] private InputAction drop = new InputAction("Drop", InputActionType.Button, "<Keyboard>/g");
        [SerializeField] private InputAction cycle = new InputAction("CycleSlot", InputActionType.Value, "<Mouse>/scroll/y");
        [SerializeField] private InputAction[] selectSlot =
        {
            new InputAction("Slot1", InputActionType.Button, "<Keyboard>/1"),
            new InputAction("Slot2", InputActionType.Button, "<Keyboard>/2"),
            new InputAction("Slot3", InputActionType.Button, "<Keyboard>/3"),
            new InputAction("Slot4", InputActionType.Button, "<Keyboard>/4"),
            new InputAction("Slot5", InputActionType.Button, "<Keyboard>/5"),
            new InputAction("Slot6", InputActionType.Button, "<Keyboard>/6"),
            new InputAction("Slot7", InputActionType.Button, "<Keyboard>/7"),
            new InputAction("Slot8", InputActionType.Button, "<Keyboard>/8"),
        };

        private void Awake()
        {
            if (inventory == null) inventory = GetComponentInParent<NetworkInventory>();
            if (viewCamera == null) viewCamera = GetComponentInChildren<Camera>(true);
        }

        private void OnEnable()
        {
            pickup.Enable();
            drop.Enable();
            cycle.Enable();
            foreach (InputAction action in selectSlot) action.Enable();
        }

        private void OnDisable()
        {
            pickup.Disable();
            drop.Disable();
            cycle.Disable();
            foreach (InputAction action in selectSlot) action.Disable();
        }

        private void Update()
        {
            if (inventory == null || !inventory.IsOwner) return;
            if (requireLockedCursor && Cursor.lockState != CursorLockMode.Locked) return;

            for (int i = 0; i < selectSlot.Length && i < inventory.SlotCount; i++)
                if (selectSlot[i].WasPressedThisFrame())
                    inventory.RequestSelect(i);

            float scroll = cycle.ReadValue<float>();
            if (scroll > 0.01f) inventory.RequestSelectNext(-1);
            else if (scroll < -0.01f) inventory.RequestSelectNext(1);

            Camera view = viewCamera != null && viewCamera.enabled ? viewCamera : Camera.main;
            if (view == null) return;
            var ray = new Ray(view.transform.position, view.transform.forward);
            if (pickup.WasPressedThisFrame()) inventory.RequestPickup(ray);
            if (drop.WasPressedThisFrame()) inventory.RequestDropSelected(ray);
        }
    }
}
