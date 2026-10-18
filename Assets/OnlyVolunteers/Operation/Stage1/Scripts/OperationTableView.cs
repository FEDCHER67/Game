using System.Collections.Generic;
using FishNet.Object;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    public enum HintTone { Neutral, Good, Warn, Bad }
    /// <summary>Two table screens (Fedya, v04 playtest): PREP shows the whole patient, all five straps and the tray
    /// (straps, anesthesia, blood); OPERATION is the close v04 top-down framing (cutting, cords, pulling organs).</summary>
    public enum TableCamera { Prep, Operation }

    /// <summary>Local table mode: shared camera, free cursor, real physics raycast against the actual colliders (tools,
    /// straps, body parts, incisions, cords, organs, bags, tray, items), hover highlight, keys 1-4, LMB/RMB intents.
    /// It only sends requests; it never edits patient state.</summary>
    [DefaultExecutionOrder(11000)]
    public sealed class OperationTableView : MonoBehaviour
    {
        public struct Hover
        {
            public bool hit;
            public OpTarget target;
            public Vector3 point;
            public Vector3 normal;
            public Collider collider;
            public OperationTool tool;
            public OperationPhysicalItem item;
            public Renderer[] renderers;
        }

        [SerializeField] private NetworkOperationTable table;
        private NetworkPlayer player;
        private NetworkInventory inventory;
        private KccFirstPersonInput input;
        private InventoryInput inventoryInput;
        private PhoneController phone;
        private NetworkGrabber grabber;
        private Camera cam;
        private OperationHud hud;
        private bool active;
        private float blend;
        private float fov0 = 60f;
        private bool restoring;
        private bool priorMove, priorLook, priorInventory, priorSession;
        private float wasdHeld;
        private int wasdFrames;
        private float zoom, zoomTarget, zoomVelocity;
        private Vector3 focusLocal;
        private Hover hover;
        private Renderer[] tinted;
        private bool pressed;
        private uint pressId;
        private OpTarget pressTarget;
        private float pressMouseY;
        private bool stroke;
        private int strokeOrgan = -1;
        private float pull;
        private uint sequence;
        private float nextSend;
        private readonly RaycastHit[] hits = new RaycastHit[32];
        private readonly List<Vector3> offLineDots = new();
        private OpHint serverHint;
        private int serverHintArg;
        private float serverHintAt = -10f;
        private TableCamera cameraMode;
        private ToolSlot lastSlot;
        /// <summary>The wheel only fine-tunes a view: PREP may come this share of the way in, OPERATION back out this share.</summary>
        private const float PrepFineZoom = 0.4f, OperationFineOut = 0.3f;

        public bool Active => active;
        public float Blend => blend;
        public NetworkPlayer LocalPlayer => player;
        public int LocalClientId => player != null ? player.OwnerId : -999;
        public Camera ViewCamera => cam;
        public NetworkOperationTable Table => table;
        public Hover Current => hover;
        public bool Pressed => pressed;
        public OpTarget PressTarget => pressTarget;
        public bool Stroking => stroke;
        public int StrokeOrgan => strokeOrgan;
        public float PullDrag => pull;
        public float Zoom => zoom;
        public TableCamera CameraMode => cameraMode;
        /// <summary>The view's camera pose now (the current screen with its fine zoom), what the camera blends to.</summary>
        public Pose ViewPose => new Pose(ViewPosition(zoom), table.CameraPose.rotation);
        private float PrepZoom => table.Tuning.minZoom < 0f ? table.Tuning.minZoom : 0f;
        public IReadOnlyList<Vector3> OffLineDots => offLineDots;
        public bool PromptVisible { get; private set; }
        public Vector2 CursorScreen => OpsInput.Position;
        /// <summary>Set by the dev scenario driver: renders the HUD into the game camera (for captures).</summary>
        public bool CaptureMode { get; set; }
        public OperationHud Hud => hud;

        private void OnEnable() { if (table != null) table.HintReceived += OnHint; }
        private void OnDisable() { if (table != null) table.HintReceived -= OnHint; Exit(); }
        private void OnHint(OpHint hint, int arg) { serverHint = hint; serverHintArg = arg; serverHintAt = Time.unscaledTime; hud?.OnServerHint(hint, arg); }

        private void FindPlayer()
        {
            foreach (var p in FindObjectsByType<NetworkPlayer>())
                if (p.IsOwner && p.IsClientInitialized)
                {
                    player = p; cam = p.ViewCamera; inventory = p.GetComponent<NetworkInventory>();
                    input = p.GetComponent<KccFirstPersonInput>(); inventoryInput = p.GetComponent<InventoryInput>();
                    grabber = p.GetComponent<NetworkGrabber>();
                    phone = FindAnyObjectByType<PhoneController>();
                    if (hud == null) { hud = new GameObject("[Operation] HUD").AddComponent<OperationHud>(); hud.Bind(this); }
                    break;
                }
        }

        public OperationTool HeldTool
        {
            get
            {
                foreach (var t in table.FindToolsCached()) if (t != null && t.Holder == LocalClientId && t.Mode == ToolMode.Held) return t;
                return null;
            }
        }
        public ToolSlot LocalSlot { get { var t = HeldTool; return t != null ? t.Slot : ToolSlot.Hands; } }
        public OperationPhysicalItem HeldItem => inventory != null && inventory.PhysicalItem != null ? inventory.PhysicalItem.GetComponent<OperationPhysicalItem>() : null;

        // ---------- enter / exit ----------
        public void Enter()
        {
            if (active || player == null || table.State == null) return;
            if (Vector3.Distance(player.MotorPosition, table.transform.position) > table.Tuning.tableReach) return;
            active = true; restoring = false; blend = 0f; wasdHeld = 0f; wasdFrames = 0;
            if (table.Tuning.sharedAbdomen) focusLocal = table.Tuning.cameraLookAt;
            // Stepping up to the table opens the PREP screen (whole patient, every strap, the tray).
            cameraMode = TableCamera.Prep; zoom = zoomTarget = PrepZoom; lastSlot = LocalSlot;
            table.RequestJoin(true);
            table.RequestCameraMode(TableCamera.Prep);
            priorMove = input.MovementLocked; priorLook = input.LookSuspended; fov0 = cam.fieldOfView;
            input.MovementLocked = true; input.LookSuspended = true;
            priorInventory = inventoryInput != null && inventoryInput.enabled;
            if (inventoryInput != null) inventoryInput.enabled = false;
            if (NetworkSession.Active != null) { priorSession = NetworkSession.Active.enabled; NetworkSession.Active.enabled = false; }
            if (phone != null) phone.enabled = false;
            player.SetLocalHudVisible(false);
            if (grabber != null) grabber.InputSuppressed = true;
            Cursor.lockState = CursorLockMode.None; Cursor.visible = false;
            hud?.Toast("Ты у стола", HintTone.Neutral);
        }
        public void Exit()
        {
            if (!active) return;
            active = false; restoring = true;
            if (pressed) { pressed = false; SendPointer(); }
            stroke = false; Untint();
            if (ring != null) ring.gameObject.SetActive(false);
            if (table != null && table.IsClientInitialized) table.RequestJoin(false);
            if (input != null) { input.MovementLocked = priorMove; input.LookSuspended = priorLook; }
            if (inventoryInput != null) inventoryInput.enabled = priorInventory;
            if (NetworkSession.Active != null) NetworkSession.Active.enabled = priorSession;
            if (phone != null) phone.enabled = true;
            if (player != null) player.SetLocalHudVisible(true);
            if (grabber != null) grabber.InputSuppressed = false;
        }

        // ---------- per frame ----------
        private void Update()
        {
            if (table == null || !table.IsClientInitialized) return;
            if (player == null) { FindPlayer(); if (player == null) return; }
            var key = OpsInput.Keyboard; var mouse = OpsInput.Mouse;
            if (key == null || mouse == null) return;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (key.f9Key.wasPressedThisFrame) { table.RequestDev(9); hud?.Toast("DEV: пациент на столе", HintTone.Neutral); }
            if (key.f10Key.wasPressedThisFrame) { table.RequestDev(10); hud?.Toast("DEV: новый пациент", HintTone.Neutral); }
#endif
            if (!active)
            {
                PromptVisible = ComputePrompt();
                // E already used this frame (a body bag lifted, a van door) never also steps up to the table.
                if (PromptVisible && key.eKey.wasPressedThisFrame && OnlyVolunteers.Map.GreyboxInput.EFree) Enter();
                return;
            }
            PromptVisible = false;
            if (key.escapeKey.wasPressedThisFrame || key.eKey.wasPressedThisFrame) { Exit(); return; }
            bool wasd = key.wKey.isPressed || key.aKey.isPressed || key.sKey.isPressed || key.dKey.isPressed;
            // walking away: held > 0.2 s (and over a few frames, so one slow frame is not a "hold")
            if (wasd) { if (wasdFrames++ > 0) wasdHeld += Time.unscaledDeltaTime; } else { wasdHeld = 0f; wasdFrames = 0; }
            if (wasdHeld > 0.2f && wasdFrames >= 3) { Exit(); return; }
            if (Vector3.Distance(player.MotorPosition, table.transform.position) > table.Tuning.tableReach) { Exit(); return; }
            if (player.HandsBusy) return;

            Ray ray = cam.ScreenPointToRay(mouse.position.ReadValue());
            ResolveHover(ray);

            float scroll = mouse.scroll.ReadValue().y;
            if (Mathf.Abs(scroll) > 0.01f)
            {
                ZoomRange(out float lo, out float hi);
                if (scroll > 0f)
                {
                    if (cameraMode == TableCamera.Operation && zoomTarget >= 0f) focusLocal = table.transform.InverseTransformPoint(hover.point);
                    zoomTarget = zoomTarget < 0f ? Mathf.Min(Mathf.Min(0f, hi), zoomTarget + 0.18f) : Mathf.Min(hi, zoomTarget + 0.18f);
                }
                else
                {
                    zoomTarget = Mathf.Max(lo, zoomTarget - 0.18f);
                    if (zoomTarget < 0f) focusLocal = table.Tuning.cameraLookAt;
                }
            }

            // Tab: PREP <-> OPERATION; taking the scalpel opens OPERATION, a syringe PREP (the hands keep the screen,
            // so pulling an organ right after a cut stays in OPERATION).
            if (key.tabKey.wasPressedThisFrame) SetCameraMode(cameraMode == TableCamera.Prep ? TableCamera.Operation : TableCamera.Prep);
            var slotNow = LocalSlot;
            if (slotNow != lastSlot)
            {
                if (slotNow == ToolSlot.Scalpel || slotNow == ToolSlot.Suture) SetCameraMode(TableCamera.Operation);
                else if (slotNow == ToolSlot.Anesthesia || slotNow == ToolSlot.Blood) SetCameraMode(TableCamera.Prep);
                lastSlot = slotNow;
            }

            if (key.digit1Key.wasPressedThisFrame) Select(ToolSlot.Hands);
            if (key.digit2Key.wasPressedThisFrame) Select(ToolSlot.Anesthesia);
            if (key.digit3Key.wasPressedThisFrame) Select(ToolSlot.Blood);
            if (key.digit4Key.wasPressedThisFrame) Select(ToolSlot.Scalpel);
            if (key.digit5Key.wasPressedThisFrame) Select(ToolSlot.Suture);
            if (mouse.rightButton.wasPressedThisFrame) { table.RequestReturn(); hud?.Pulse(); }

            if (mouse.leftButton.wasPressedThisFrame) Press(mouse);
            if (pressed && !mouse.leftButton.isPressed) { pressed = false; stroke = false; strokeOrgan = -1; pull = 0f; SendPointer(); }
            if (pressed && pressTarget.kind == TargetKind.Organ)
                pull = (mouse.position.ReadValue().y - pressMouseY) / Mathf.Max(1f, cam.pixelHeight * table.Tuning.pullScreenFraction) * table.Tuning.pullDistance;
            if (stroke) TrackStroke();
            if (Time.unscaledTime >= nextSend) SendPointer();
            Highlight();
        }

        public void SetCameraMode(TableCamera mode)
        {
            if (mode == cameraMode) return;
            cameraMode = mode;
            if (pressed) { pressed = false; stroke = false; strokeOrgan = -1; SendPointer(); }
            table.RequestCameraMode(mode);
            zoomTarget = mode == TableCamera.Prep ? PrepZoom : 0f;
            focusLocal = table.Tuning.cameraLookAt;
        }
        private void ZoomRange(out float lo, out float hi)
        {
            float wide = table.Tuning.minZoom;
            if (cameraMode == TableCamera.Prep && wide < 0f) { lo = wide; hi = wide * (1f - PrepFineZoom); return; }
            lo = wide < 0f ? wide * OperationFineOut : 0f;
            hi = table.Tuning.maxZoom;
        }
        private Vector3 ViewPosition(float z)
        {
            var anchor = table.CameraPose;
            var tuning = table.Tuning;
            Vector3 focus = table.transform.TransformPoint(focusLocal);
            // Wheel in: toward the cursor point. Negative (v04): up and toward the feet, the PREP / wide framing.
            return z < 0f && tuning.minZoom < 0f && tuning.wideCameraOffset != Vector3.zero
                ? anchor.position + table.transform.TransformVector(tuning.wideCameraOffset) * (z / tuning.minZoom)
                : anchor.position + (focus - anchor.position) * z;
        }

        private void Select(ToolSlot slot)
        {
            var tool = table.ToolOf(slot);
            if (slot != ToolSlot.Hands && tool != null && tool.Holder >= 0 && tool.Holder != LocalClientId)
            { hud?.Toast("Это сейчас у P" + (tool.Holder + 1), HintTone.Warn); return; }
            table.RequestSelect(slot);
        }

        private void Press(Mouse mouse)
        {
            var held = HeldItem;
            if (held != null)
            {
                if (hover.target.kind == TargetKind.Tray || hover.target.kind == TargetKind.BloodBag || hover.target.kind == TargetKind.Item)
                    table.RequestClick(new OpTarget(TargetKind.Tray, hover.target.kind == TargetKind.Tray ? hover.target.index : 0).Code, Local(hover.point), null);
                else hud?.Toast("Кликни по лотку — положить", HintTone.Neutral);
                return;
            }
            switch (hover.target.kind)
            {
                case TargetKind.Strap:
                    if (cameraMode == TableCamera.Prep) table.RequestClick(hover.target.Code, Local(hover.point), null);
                    return;
                case TargetKind.Tool:
                case TargetKind.BloodBag:
                    table.RequestClick(hover.target.Code, Local(hover.point), null);
                    return;
                case TargetKind.Item:
                    table.RequestClick(hover.target.Code, Local(hover.point), hover.item != null ? hover.item.NetworkObject : null);
                    return;
                case TargetKind.Tray:
                    return;
            }
            pressed = true; pressId++; pressTarget = hover.target; pressMouseY = mouse.position.ReadValue().y; pull = 0f;
            offLineDots.Clear();
            if ((LocalSlot == ToolSlot.Scalpel || LocalSlot == ToolSlot.Suture) && pressTarget.kind == TargetKind.Incision && table.AnatomyReady)
            { stroke = true; strokeOrgan = pressTarget.index; }
            SendPointer();
        }

        private void TrackStroke()
        {
            if (strokeOrgan < 0 || !table.AnatomyReady || table.State == null) return;
            Vector3 local = table.SiteLocal(strokeOrgan, hover.point);
            Vector2 g = table.GuideCoordinates(strokeOrgan, local);
            float tolerance = table.Tuning.sharedAbdomen ? OperationAbdomenGeometry.Tolerance(table.Tuning, strokeOrgan) : table.Tuning.cutTolerance;
            if (Mathf.Abs(g.y) > tolerance && table.GuideProgress(strokeOrgan) < 1f)
            {
                if (offLineDots.Count == 0 || Vector3.Distance(offLineDots[offLineDots.Count - 1], hover.point) > 0.006f)
                { offLineDots.Add(hover.point); if (offLineDots.Count > 80) offLineDots.RemoveAt(0); }
            }
        }

        private Vector3 Local(Vector3 world) => table.transform.InverseTransformPoint(world);

        private void SendPointer()
        {
            nextSend = Time.unscaledTime + table.Tuning.inputInterval;
            if (!active && !pressed) { table.RequestPointer(++sequence, pressId, false, 0, 0, Local(hover.point), 0f); return; }
            table.RequestPointer(++sequence, pressId, pressed, pressTarget.Code, hover.target.Code, Local(hover.point), pull);
        }

        // ---------- hover ----------
        private void ResolveHover(Ray ray)
        {
            var previous = hover;
            hover = default;
            if (stroke && strokeOrgan >= 0 && table.AnatomyReady)
            {
                // During a stroke the blade stays on the incision's own skin plane (precise, never blocked by an arm).
                var plane = new Plane(table.OrganNormal(strokeOrgan), table.Tuning.sharedAbdomen
                    ? table.GuidePosition(strokeOrgan, 0f) : table.SitePoint(strokeOrgan, Vector3.zero));
                if (plane.Raycast(ray, out float d))
                {
                    hover.hit = true; hover.point = ray.GetPoint(d); hover.normal = plane.normal;
                    hover.target = new OpTarget(TargetKind.Incision, strokeOrgan);
                    return;
                }
            }
            // Never the ribcage's 96 SurgicalBone pieces (bone tools query them on their own): they would fill this buffer.
            int count = Physics.RaycastNonAlloc(ray, hits, 8f, ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Collide);
            // Nearest target wins, with two readable exceptions: the generic tray zone only when nothing else is on the
            // ray, and the patient's body hull loses to anything lying on it (straps, incisions, cords, organs) up to
            // 7 cm behind its surface. The hull capsules are deliberately a little fat.
            // An open strap standing up in front of the tray must not hide the bag or tool behind it.
            Hover bestOther = default, bestBody = default, bestTray = default, bestOpenStrap = default;
            float dOther = float.PositiveInfinity, dBody = float.PositiveInfinity, dTray = float.PositiveInfinity, dOpenStrap = float.PositiveInfinity;
            var st = table.State;
            bool anyCord = false; OpTarget cordTarget = default; RaycastHit cordHit = default;
            for (int i = 0; i < count; i++)
            {
                var h = hits[i];
                if (h.collider == null || (player != null && h.collider.transform.IsChildOf(player.transform))) continue;
                if (!Classify(h.collider, out var t, out var tool, out var item, out var renderers)) continue;
                // The broad guide volume supports strokes, but starting a v02 liver stroke must be near its visible line.
                // Its old forgiving volume otherwise masks both kidneys' bodies.
                if (table.Tuning.anatomicalLayout && t.kind == TargetKind.Incision && t.index == 2)
                {
                    var guidePlane = new Plane(table.OrganNormal(2), table.GuidePosition(2, 0f));
                    if (guidePlane.Raycast(ray, out float guideDistance))
                    {
                        var coordinates = table.GuideCoordinates(2, table.SiteLocal(2, ray.GetPoint(guideDistance)));
                        if (Mathf.Abs(coordinates.y) > 0.010f) continue;
                    }
                }
                if (t.kind == TargetKind.Cord && (!anyCord || h.distance < cordHit.distance)) { anyCord = true; cordTarget = t; cordHit = h; }
                var candidate = new Hover { hit = true, target = t, point = h.point, normal = h.normal.sqrMagnitude > 0.5f ? h.normal : table.transform.up, collider = h.collider, tool = tool, item = item, renderers = renderers };
                if (t.kind == TargetKind.Tray) { if (h.distance < dTray) { dTray = h.distance; bestTray = candidate; } }
                else if (t.kind == TargetKind.Strap && st != null && t.index < 5 && !st.restraints[t.index]) { if (h.distance < dOpenStrap) { dOpenStrap = h.distance; bestOpenStrap = candidate; } }
                else if (t.kind == TargetKind.Body) { if (h.distance < dBody) { dBody = h.distance; bestBody = candidate; } }
                else if (h.distance < dOther) { dOther = h.distance; bestOther = candidate; }
            }
            if (bestOpenStrap.hit && (!bestOther.hit || dOpenStrap < dOther) && (!bestBody.hit || dOpenStrap < dBody))
            {
                // the open strap is in front: it wins unless a tray object sits right behind it
                bool trayObjectBehind = bestOther.hit && (bestOther.target.kind == TargetKind.BloodBag || bestOther.target.kind == TargetKind.Tool || bestOther.target.kind == TargetKind.Item) && dOther - dOpenStrap < 0.6f;
                if (!trayObjectBehind) { bestOther = bestOpenStrap; dOther = dOpenStrap; }
            }
            else if (bestOpenStrap.hit && !bestOther.hit) { bestOther = bestOpenStrap; dOther = dOpenStrap; }
            bool throughOpening = table.Tuning.anatomicalLayout && st != null && st.zoneOpened && table.Abdomen != null && table.Abdomen.OpeningContains(ray);
            if (bestOther.hit && (!bestBody.hit || dOther <= dBody + 0.07f || (throughOpening && (bestOther.target.kind == TargetKind.Organ || bestOther.target.kind == TargetKind.Cord)))) hover = bestOther;
            else if (bestBody.hit) hover = bestBody;
            else if (bestOther.hit) hover = bestOther;
            else if (bestTray.hit) hover = bestTray;
            // A cord anywhere on the ray wins over the organ body behind or around it: snipping never stabs the organ.
            if (anyCord && (hover.target.kind == TargetKind.Organ || (table.Tuning.anatomicalLayout && st != null && st.zoneOpened && (hover.target.kind == TargetKind.Incision || hover.target.kind == TargetKind.Body))))
            {
                var tag = cordHit.collider.GetComponentInParent<OperationTargetTag>();
                hover = new Hover { hit = true, target = cordTarget, point = cordHit.point, normal = cordHit.normal, collider = cordHit.collider, renderers = tag != null ? tag.highlight : null };
            }
            if (!hover.hit)
            {
                var pad = new Plane(table.transform.up, table.transform.TransformPoint(new Vector3(0, table.Tuning.padTop + 0.05f, 0)));
                if (pad.Raycast(ray, out float d)) hover.point = ray.GetPoint(d);
                else hover.point = previous.point;
                hover.normal = table.transform.up;
            }
        }

        private bool Classify(Collider c, out OpTarget target, out OperationTool tool, out OperationPhysicalItem item, out Renderer[] renderers)
        {
            target = OpTarget.None; tool = null; item = null; renderers = null;
            bool own = c.TryGetComponent(out OperationTargetTag tag);
            if (!own) tag = c.GetComponentInParent<OperationTargetTag>();
            if (tag != null && (tag.kind != TargetKind.Body || own))
            {
                if (tag.kind == TargetKind.Strap && cameraMode != TableCamera.Prep) return false;
                if (table.Tuning.anatomicalLayout && tag.kind == TargetKind.Incision && LocalSlot != ToolSlot.Scalpel && LocalSlot != ToolSlot.Suture) return false;
                target = tag.Target; renderers = tag.highlight; return true;
            }
            tool = c.GetComponentInParent<OperationTool>();
            if (tool != null)
            {
                if (tool.Table != table || tool.Mode == ToolMode.Held) { tool = null; return false; }
                target = new OpTarget(TargetKind.Tool, (int)tool.Slot);
                renderers = tool.GetComponentsInChildren<Renderer>();
                return true;
            }
            item = c.GetComponentInParent<OperationPhysicalItem>();
            if (item != null && item.Holder == null)
            {
                target = new OpTarget(TargetKind.Item);
                renderers = item.GetComponentsInChildren<Renderer>();
                return true;
            }
            item = null;
            return false;
        }

        private LineRenderer ring;
        /// <summary>Body parts have no separate renderer to tint: a small ring on the skin marks the spot instead.</summary>
        private void HoverRing()
        {
            if (ring == null)
            {
                ring = OperationVisuals.Line("[Operation] hover ring", null, OperationVisuals.Unlit("hoverring", Color.white), 0.004f, 28);
                ring.loop = true; ring.useWorldSpace = false; ring.alignment = LineAlignment.TransformZ;
                for (int i = 0; i < 28; i++) { float a = i / 28f * Mathf.PI * 2f; ring.SetPosition(i, new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f) * 0.024f); }
            }
            bool show = active && hover.hit && hover.target.kind == TargetKind.Body;
            ring.gameObject.SetActive(show);
            if (!show) return;
            ring.transform.SetPositionAndRotation(hover.point + hover.normal * 0.004f, Quaternion.LookRotation(-hover.normal));
            var tone = hud != null ? OperationHud.ToneColor(hud.CurrentTone) : Color.white;
            ring.startColor = ring.endColor = tone;
            ring.sharedMaterial.color = tone; ring.sharedMaterial.SetColor("_BaseColor", tone);
        }
        private void Highlight()
        {
            HoverRing();
            var want = hover.renderers;
            if (want == tinted) return;
            Untint();
            if (want != null) OperationVisuals.Tint(want, new Color(1f, 0.93f, 0.55f), 0.45f);
            tinted = want;
        }
        private void Untint() { if (tinted != null) OperationVisuals.Untint(tinted); tinted = null; }

        public bool TryLocalHeldPose(OperationToolKind kind, out Pose pose)
        {
            // In the skin while the press draws blood from an arm or injects into an injection site.
            bool inSkin = pressed && hover.hit && hover.target.kind == TargetKind.Body &&
                ((kind == OperationToolKind.BloodSyringe && pressTarget.ArmSide >= 0) || (kind == OperationToolKind.Syringe && pressTarget.IsInjectionSite));
            pose = table.HeldToolPose(kind, hover.point, hover.hit ? hover.normal : table.transform.up, inSkin);
            return true;
        }

        // ---------- first person prompt ----------
        private bool ComputePrompt()
        {
            if (cam == null || player.HandsBusy || !OpsInput.CursorLocked || table.State == null) return false;
            if (Vector3.Distance(player.MotorPosition, table.transform.position) > table.Tuning.enterDistance) return false;
            var ray = new Ray(cam.transform.position, cam.transform.forward);
            int count = Physics.RaycastNonAlloc(ray, hits, 3.5f, ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Ignore);
            float best = float.PositiveInfinity; Collider first = null;
            for (int i = 0; i < count; i++)
            {
                if (hits[i].collider == null || hits[i].collider.transform.IsChildOf(player.transform) || hits[i].distance >= best) continue;
                best = hits[i].distance; first = hits[i].collider;
            }
            if (first != null)
            {
                // A loose item in reach belongs to the inventory's E pickup.
                var worldItem = first.GetComponentInParent<WorldItem>();
                if (worldItem != null && inventory != null && best <= inventory.Reach) return false;
                // A body that is not this table's patient (a corpse taken off it, a body bag) belongs to E carry / LMB.
                var body = first.GetComponentInParent<OperationPatientRagdoll>();
                if (body != null && (table.PatientObject == null || body.gameObject != table.PatientObject.gameObject)) return false;
                if (first.transform.IsChildOf(table.transform)) return true;
                if (table.PatientObject != null && first.transform.IsChildOf(table.PatientObject.transform)) return true;
                var tool = first.GetComponentInParent<OperationTool>();
                if (tool != null && tool.Table == table) return true;
            }
            Vector3 to = table.transform.position + table.transform.up * 0.7f - cam.transform.position;
            return Vector3.Angle(cam.transform.forward, to) < 28f;
        }

        // ---------- camera ----------
        private void LateUpdate()
        {
            if (player == null || cam == null || table == null) return;
            if (active && grabber != null) grabber.InputSuppressed = true;
            float speed = 1f / Mathf.Max(0.05f, table.Tuning.cameraBlendSeconds);
            blend = Mathf.MoveTowards(blend, active ? 1f : 0f, Time.unscaledDeltaTime * speed);
            if (!active && blend <= 0f)
            {
                if (restoring) { restoring = false; cam.fieldOfView = fov0; }
                return;
            }
            zoom = Mathf.SmoothDamp(zoom, zoomTarget, ref zoomVelocity, 0.14f, Mathf.Infinity, Time.unscaledDeltaTime);
            var anchor = table.CameraPose;
            Vector3 position = ViewPosition(zoom);
            float t = blend * blend * (3f - 2f * blend);
            // The KCC wrote the eye pose earlier this frame; blend from it.
            cam.transform.SetPositionAndRotation(Vector3.Lerp(cam.transform.position, position, t), Quaternion.Slerp(cam.transform.rotation, anchor.rotation, t));
            cam.fieldOfView = Mathf.Lerp(fov0, table.Tuning.cameraFieldOfView, t);
            var item = HeldItem;
            if (active && item != null) item.transform.position = hover.point + table.transform.up * 0.1f;
        }
    }
}
