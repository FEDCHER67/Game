using OnlyVolunteers.Inventory;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// Test-scene-only first-person walker (CharacterController + mouse look) with one context key, E:
    /// pick up / put down the patient, put him on the table, hold to strap, start the operation, otherwise pick up items.
    /// The real game will route the same table calls through its own player/interactor; this class is not that player.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class OperationTestPlayer : MonoBehaviour
    {
        [SerializeField] private Camera viewCamera;
        [SerializeField] private OperationTable table;
        [SerializeField] private OperationSession session;
        [SerializeField, Min(0.5f)] private float walkSpeed = 4.5f;
        [SerializeField, Min(0.01f)] private float lookSensitivity = 0.12f;
        [SerializeField, Min(0.5f)] private float reach = 2.6f;

        private CharacterController controller;
        private InventoryInput inventoryInput;
        private OperationPatient carried;
        private float pitch;
        private float verticalSpeed;
        private string prompt = "";

        public Camera ViewCamera => viewCamera;
        public LocalInventory Inventory { get; private set; }
        public bool ControlsEnabled { get; set; } = true;

        public void Configure(Camera view, OperationTable operationTable, OperationSession operationSession)
        {
            viewCamera = view;
            table = operationTable;
            session = operationSession;
        }

        private void Awake()
        {
            controller = GetComponent<CharacterController>();
            Inventory = GetComponent<LocalInventory>();
            inventoryInput = GetComponent<InventoryInput>();
            // E is shared: this script decides what it does and falls back to the inventory pickup.
            if (inventoryInput != null) inventoryInput.ExternalPickup = true;
        }

        private void Update()
        {
            Keyboard keyboard = Keyboard.current;
            Mouse mouse = Mouse.current;
            if (keyboard == null || mouse == null) return;
            if (!ControlsEnabled)
            {
                prompt = "";
                return;
            }

            if (Cursor.lockState != CursorLockMode.Locked)
            {
                prompt = "Клик — захватить мышь";
                if (mouse.leftButton.wasPressedThisFrame) LockCursor(true);
                return;
            }
            if (keyboard.escapeKey.wasPressedThisFrame)
            {
                LockCursor(false);
                return;
            }

            Look(mouse.delta.ReadValue());
            Move(keyboard);
            Interact(keyboard);
        }

        public static void LockCursor(bool locked)
        {
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }

        private void Look(Vector2 delta)
        {
            transform.Rotate(0f, delta.x * lookSensitivity, 0f);
            pitch = Mathf.Clamp(pitch - delta.y * lookSensitivity, -80f, 80f);
            if (viewCamera != null) viewCamera.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        private void Move(Keyboard keyboard)
        {
            Vector2 input = new Vector2(
                (keyboard.dKey.isPressed ? 1f : 0f) - (keyboard.aKey.isPressed ? 1f : 0f),
                (keyboard.wKey.isPressed ? 1f : 0f) - (keyboard.sKey.isPressed ? 1f : 0f));
            Vector3 planar = (transform.right * input.x + transform.forward * input.y) * walkSpeed;
            // Carrying a body slows you down (canon: a grown man is heavy).
            if (carried != null) planar *= 0.6f;
            verticalSpeed = controller.isGrounded ? -1f : verticalSpeed - 9.81f * Time.deltaTime;
            controller.Move((planar + Vector3.up * verticalSpeed) * Time.deltaTime);
        }

        private void Interact(Keyboard keyboard)
        {
            bool press = keyboard.eKey.wasPressedThisFrame;
            bool hold = keyboard.eKey.isPressed;
            bool nearTable = table != null && Vector3.Distance(Flat(transform.position), Flat(table.transform.position)) <= reach;

            if (carried != null)
            {
                if (nearTable && table.Patient == null)
                {
                    prompt = "[E] Положить на стол";
                    if (press)
                    {
                        table.Accept(carried);
                        carried = null;
                    }
                }
                else
                {
                    prompt = "[E] Бросить";
                    if (press)
                    {
                        carried.Drop(transform.forward * 1.5f + Vector3.up);
                        carried = null;
                    }
                }
                return;
            }

            if (nearTable && table.Patient != null)
            {
                if (!table.Ready)
                {
                    prompt = $"[удерживай E] Пристегнуть ремни  {Mathf.RoundToInt(table.StrapProgress * 100f)}%   (скатится через {table.RollOffIn:0} с)";
                    if (hold) table.HoldStrap(Time.deltaTime);
                    return;
                }
                prompt = table.Patient.KidneysLeft > 0 ? "[E] Оперировать" : "[E] Оперировать (почек больше нет)";
                if (press && session != null) session.Begin(this, table);
                return;
            }

            OperationPatient patient = LookedAtPatient();
            if (patient != null)
            {
                prompt = "[E] Взять пациента";
                if (press)
                {
                    carried = patient;
                    patient.BeginCarry(transform, new Vector3(0f, 1.05f, 0.8f));
                }
                return;
            }

            prompt = "";
            if (press && inventoryInput != null) inventoryInput.PickupNow();
        }

        private OperationPatient LookedAtPatient()
        {
            if (viewCamera == null) return null;
            Ray ray = new Ray(viewCamera.transform.position, viewCamera.transform.forward);
            if (!Physics.SphereCast(ray, 0.25f, out RaycastHit hit, reach, ~0, QueryTriggerInteraction.Ignore)) return null;
            OperationPatient patient = hit.collider.GetComponentInParent<OperationPatient>();
            return patient != null && !patient.OnTable && !patient.Carried ? patient : null;
        }

        private static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0f, v.z);

        private void OnGUI()
        {
            if (!ControlsEnabled) return;
            if (Cursor.lockState == CursorLockMode.Locked)
                GUI.Label(new Rect(Screen.width * 0.5f - 4f, Screen.height * 0.5f - 10f, 20f, 20f), "+", OperationGui.Center(18));
            if (prompt.Length > 0)
                GUI.Label(new Rect(0f, Screen.height * 0.62f, Screen.width, 40f), prompt, OperationGui.Center(22));
            GUI.Label(new Rect(12f, 10f, 700f, 24f), "WASD — ходить, мышь — смотреть, E — действие, Esc — отпустить мышь", OperationGui.Left(14));
        }
    }
}
