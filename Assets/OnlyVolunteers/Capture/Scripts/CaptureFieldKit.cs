using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Capture
{
    public enum FieldTool : byte { Hands = 0, Ties = 1, Anesthesia = 2, Blood = 3 }

    /// <summary>The player's field kit (capture → delivery stage A, D1, D2, D7): zip ties, the anesthesia syringe and the
    /// blood syringe, usable anywhere (on the ground, in the van). Round 2 (Fedya, 2026-10-18, WORK_INVENTORY_SPEC decision
    /// 1): the kit is ONE item of the map's existing inventory hotbar (LocalInventory: 1-6 / the wheel select a slot, G drops,
    /// E picks up), in slot 2. Selecting it takes the zip ties in hand; pressing 2 again cycles ties → anesthesia syringe →
    /// blood syringe → empty hands → ties… Slot 1 stays empty = bare hands. Tool in hand + LEFT mouse button on the NPC under
    /// the crosshair = use (timed actions are holds); dragging only with empty hands (the grabbers step aside while a tool
    /// is in hand, CaptureGrabArbiter; no LMB-carry + RMB-inject combo, decision 3). The old Z/X/C keys and the bottom tool
    /// cards are gone. A blood syringe filled in the field is emptied at the table: aim it at an empty bag on the tray and click LMB
    /// (NetworkOperationTable.ServerFieldTransfer: the same smooth plunger/bag animation; the portion was counted on the NPC
    /// when drawn, the bag value once when sealed). The dose and blood rules are the table's own (OperationRules on the
    /// NPC's OperationState). Input: the Input System through OpsInput (the scenario driver's virtual devices drive it).</summary>
    [DefaultExecutionOrder(50)]
    public sealed class CaptureFieldKit : MonoBehaviour
    {
        public const float Reach = 2.6f;
        /// <summary>ItemDefinition id of the field kit in the shared ItemDatabase (Capture/Data/Items_v01) and its hotbar slot.</summary>
        public const int KitItemId = 301, KitSlot = 1;
        public int Ties = CaptureRules.StartingTies;
        public float AnesthesiaBarrel;
        public float AnesthesiaStock;
        public float BloodFill;
        /// <summary>Legacy (before round 2 a full field syringe became a "bag" here); kept for old saves only.</summary>
        public int BloodBags;
        public FieldTool Tool { get; private set; }

        private OperationTuning tuning;
        private GreyboxKccPawn pawn;
        private CaptureHud hud;
        private CaptureViewModel viewModel;
        private LocalInventory inventory;
        private bool itemsReady, warnedItems;
        private int pendingSelect = -1;
        private int lastSelected = -1;
        /// <summary>The tool in hand while the kit slot is selected (cycled by pressing its key again).</summary>
        private FieldTool kitTool = FieldTool.Ties;
        private float holdTime;
        private CaptureNpc holdTarget;
        private TieTarget holdTie;
        private float nextRefusalAt;
        private bool bloodLatched;
        private string refusal;
        private float refusalUntil;
        public bool Using { get; private set; }
        public CaptureNpc Aimed { get; private set; }
        public GreyboxNpc AimedNpc { get; private set; }
        public TieTarget AimedPart { get; private set; }
        /// <summary>The empty table bag under the crosshair (blood syringe), -1 when none.</summary>
        public int AimedBag { get; private set; } = -1;
        /// <summary>Round 3 (Fedya): the table patient's body part (BodyPart) under the crosshair of a player standing by the
        /// table (not in its E view), -1 when none. The kit works on him through the table's server rules.</summary>
        public int AimedTablePart { get; private set; } = -1;
        private bool holdTable;
        /// <summary>The field syringe is emptying into a table bag right now.</summary>
        public bool Transferring { get; private set; }
        public float HoldProgress => holdTarget != null || holdTable ? holdTime / CaptureRules.TieSeconds : 0f;
        /// <summary>Set by the table bridge while the operation table view owns the screen and the mouse.</summary>
        public bool Suspended { get; set; }
        public LocalInventory Inventory => inventory;

        public void Init(OperationTuning operationTuning, GreyboxKccPawn owner, CaptureHud ui, GameObject anesthesiaModel, GameObject bloodModel)
        {
            tuning = operationTuning;
            pawn = owner;
            hud = ui;
            if (AnesthesiaBarrel <= 0f && AnesthesiaStock <= 0f)
            {
                AnesthesiaBarrel = tuning.syringeCapacity;
                AnesthesiaStock = tuning.anesthesiaStock;
            }
            inventory = pawn != null ? pawn.GetComponentInChildren<LocalInventory>(true) : null;
            if (inventory == null) inventory = FindAnyObjectByType<LocalInventory>(FindObjectsInactive.Include);
            viewModel = new CaptureViewModel(pawn != null ? pawn.ViewCamera : null, anesthesiaModel, bloodModel);
        }

        public void Restore(FieldKitSave s)
        {
            if (s == null) return;
            Ties = s.ties;
            if (s.anesthesiaBarrel >= 0f) AnesthesiaBarrel = s.anesthesiaBarrel;
            if (s.anesthesiaStock >= 0f) AnesthesiaStock = s.anesthesiaStock;
            BloodFill = s.bloodFill;
            BloodBags = s.bloodBags;
            // A pre-round-2 save may hold finished field "bags": the first goes back into the (empty) syringe, so its blood
            // can still be poured into a table bag; the counter keeps the rest.
            if (BloodBags > 0 && BloodFill <= 0f) { BloodFill = 1f; BloodBags--; }
            Select((FieldTool)Mathf.Clamp(s.tool, 0, 3), false);
        }

        public FieldKitSave Snapshot() => new FieldKitSave
        {
            ties = Ties, anesthesiaBarrel = AnesthesiaBarrel, anesthesiaStock = AnesthesiaStock,
            bloodFill = BloodFill, bloodBags = BloodBags, tool = (int)Tool,
        };

        private bool CarryingBag
        {
            get
            {
                var d = CaptureDirector.Instance;
                return d != null && d.Disposal != null && d.Disposal.Hands != null && d.Disposal.Hands.Carrying != null;
            }
        }
        private bool Active => pawn != null && pawn.Controlled && !Suspended && OpsInput.CursorLocked && pawn.ViewCamera != null && !CarryingBag;

        // ---------- the inventory item ----------
        /// <summary>The kit is in the hotbar (slot 2 when free; slot 1 stays bare hands). Re-added when missing (a fresh game,
        /// a load: the map inventory itself is not saved).</summary>
        private void EnsureItems()
        {
            var model = inventory != null ? inventory.Model : null;
            if (model == null) return;
            itemsReady = true;
            int prior = model.SelectedIndex;
            if (KitSlotIndex < 0)
            {
                if (KitSlot < model.SlotCount && model.GetSlot(KitSlot).IsEmpty) model.Select(KitSlot);
                else for (int i = 1; i < model.SlotCount; i++) if (model.GetSlot(i).IsEmpty) { model.Select(i); break; }
                if (model.TryAdd(KitItemId, 1, 0) <= 0 && !warnedItems)
                {
                    warnedItems = true;
                    Debug.LogWarning($"[CAPTURE] the field kit item {KitItemId} could not be added to the hotbar (ItemDatabase or space)");
                }
            }
            model.Select(pendingSelect >= 0 ? pendingSelect : prior);
            pendingSelect = -1;
            lastSelected = model.SelectedIndex;
        }

        private int KitSlotIndex
        {
            get
            {
                var model = inventory != null ? inventory.Model : null;
                if (model == null) return -1;
                for (int i = 0; i < model.SlotCount; i++) { var st = model.GetSlot(i); if (!st.IsEmpty && st.ItemId == KitItemId) return i; }
                return -1;
            }
        }

        /// <summary>The kit slot's key (1-based digit) pressed this frame.</summary>
        private static bool SlotKeyPressed(int slot)
        {
            var key = OpsInput.Keyboard;
            if (key == null || slot < 0 || slot > 7) return false;
            return key[Key.Digit1 + slot].wasPressedThisFrame;
        }

        /// <summary>Which tool the hotbar puts in hand: the kit slot gives the cycled tool; entering it starts at the ties,
        /// its key again moves on (… blood syringe → empty hands → ties).</summary>
        private FieldTool SelectedTool(bool allowCycle)
        {
            var model = inventory != null ? inventory.Model : null;
            if (model == null) return Tool;
            int kit = KitSlotIndex, selected = model.SelectedIndex;
            if (kit < 0 || selected != kit) { lastSelected = selected; return FieldTool.Hands; }
            if (lastSelected != kit) kitTool = FieldTool.Ties;
            else if (allowCycle && SlotKeyPressed(kit)) kitTool = kitTool == FieldTool.Ties ? FieldTool.Anesthesia : kitTool == FieldTool.Anesthesia ? FieldTool.Blood : kitTool == FieldTool.Blood ? FieldTool.Hands : FieldTool.Ties;
            lastSelected = selected;
            return kitTool;
        }

        /// <summary>Takes a tool in hand: the kit slot with that tool (Hands: bare hands, an empty slot). Scripts and saves.</summary>
        public void Select(FieldTool tool, bool announce = true)
        {
            var model = inventory != null ? inventory.Model : null;
            int slot = -1;
            if (model != null)
            {
                if (tool == FieldTool.Hands) { for (int i = 0; i < model.SlotCount; i++) if (model.GetSlot(i).IsEmpty) { slot = i; break; } }
                else slot = KitSlotIndex;
            }
            kitTool = tool == FieldTool.Hands ? FieldTool.Ties : tool;
            if (!itemsReady) { pendingSelect = slot; lastSelected = slot; SetTool(tool, false); return; }
            if (slot >= 0) model.Select(slot);
            lastSelected = model != null ? model.SelectedIndex : -1;
            SetTool(slot >= 0 || model == null ? tool : FieldTool.Hands, announce);
        }

        private void SetTool(FieldTool tool, bool announce)
        {
            if (Tool == tool) return;
            Tool = tool;
            holdTime = 0f;
            holdTarget = null;
            holdTable = false;
            if (Tool == FieldTool.Anesthesia) Refill(announce);
            viewModel?.Show(Tool);
            if (announce && Tool == FieldTool.Ties && Ties <= 0) Refuse("Стяжки кончились");
        }

        /// <summary>The barrel fills from the field stock whenever the syringe is taken out.</summary>
        private void Refill(bool announce)
        {
            float missing = tuning.syringeCapacity - AnesthesiaBarrel;
            if (missing <= 0.001f) return;
            float add = Mathf.Min(missing, AnesthesiaStock);
            if (add <= 0f)
            {
                if (announce) Refuse("Наркоз кончился — пополнишь на базе");
                return;
            }
            AnesthesiaStock -= add;
            AnesthesiaBarrel += add;
            if (announce) hud?.Toast("Шприц заправлен", CaptureHud.Neutral, 1.4f);
        }

        /// <summary>Back at the base: the field stock is topped up (placeholder until syringe stock and refills are
        /// decided, spec §11 / ops T-06).</summary>
        public void RestockAtBase()
        {
            bool changed = AnesthesiaStock < tuning.anesthesiaStock - 0.01f;
            AnesthesiaStock = Mathf.Max(AnesthesiaStock, tuning.anesthesiaStock);
            if (changed) hud?.Toast("Аптечка пополнена", CaptureHud.Good, 1.6f);
        }

        /// <summary>The hotbar's own number keys, read here too through OpsInput (InventoryInput reads them only while the OS
        /// cursor is locked; the same selection twice is harmless): the kit's cycling sees every press, and a scripted
        /// driver's virtual keyboard selects slots exactly like a player.</summary>
        private void SelectByKeys()
        {
            var key = OpsInput.Keyboard; var model = inventory != null ? inventory.Model : null;
            if (key == null || model == null || !OpsInput.CursorLocked) return;
            for (int i = 0; i < model.SlotCount && i < 8; i++)
                if (key[Key.Digit1 + i].wasPressedThisFrame && model.SelectedIndex != i) { inventory.RequestSelect(i); break; }
        }

        private void Update()
        {
            if (OnlyVolunteers.UI.OvMenuGate.Blocking) return; // W86 pause menu: no slot keys / tool use
            if (!itemsReady) EnsureItems();
            Mouse mouse = OpsInput.Mouse;
            bool active = Active;
            if (active && itemsReady) SelectByKeys();
            if (itemsReady) SetTool(SelectedTool(active), active);
            viewModel?.SetVisible(active && Tool != FieldTool.Hands);
            if (!active || mouse == null)
            {
                Using = false;
                holdTarget = null;
                holdTable = false;
                holdTime = 0f;
                Aimed = null;
                AimedNpc = null;
                AimedBag = -1;
                AimedTablePart = -1;
                UpdateHud(false);
                return;
            }

            FindTarget();
            bool pressed = mouse.leftButton.isPressed;
            Using = Transferring;
            if (!Transferring)
            {
                if (pressed && Tool != FieldTool.Hands) Use(mouse.leftButton.wasPressedThisFrame);
                else
                {
                    holdTarget = null;
                    holdTable = false;
                    holdTime = 0f;
                }
            }
            viewModel?.Tick(Tool, Using, Tool == FieldTool.Anesthesia ? AnesthesiaBarrel / Mathf.Max(0.01f, tuning.syringeCapacity) : BloodFill, Tool == FieldTool.Anesthesia);
            UpdateHud(true);
        }

        private void FindTarget()
        {
            Aimed = null;
            AimedNpc = null;
            AimedPart = TieTarget.None;
            AimedBag = -1;
            AimedTablePart = -1;
            Transform eye = pawn.ViewCamera.transform;
            if (Tool == FieldTool.Blood) AimedBag = FindBag(eye);
            if (AimedBag < 0) AimedTablePart = FindTablePatient(eye);
            if (AimedTablePart >= 0) return;
            int mask = OvLayers.ShootMask;
            if (!UnityEngine.Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, Reach, mask, QueryTriggerInteraction.Ignore)) return;
            var npc = hit.collider.GetComponentInParent<GreyboxNpc>();
            if (npc == null) return;
            AimedNpc = npc;
            Aimed = CaptureNpc.Of(npc);
            AimedPart = PartOf(npc, hit.collider, hit.point);
        }

        /// <summary>The table's empty-bag target (its trigger) under the crosshair, nothing solid in front of it.</summary>
        private int FindBag(Transform eye)
        {
            var table = CaptureDirector.Instance != null ? CaptureDirector.Instance.Table : null;
            if (table == null) return -1;
            var hits = UnityEngine.Physics.RaycastAll(eye.position, eye.forward, Reach, ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Collide);
            System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
            foreach (var hit in hits)
            {
                if (hit.collider.TryGetComponent(out OperationTargetTag tag) && tag.kind == TargetKind.BloodBag) return tag.index;
                if (hit.collider.isTrigger || hit.collider.transform.IsChildOf(pawn.transform)) continue;
                if (hit.collider.attachedRigidbody != null && hit.collider.attachedRigidbody.GetComponentInParent<NetworkOperationTable>() == table) continue; // the tray rim
                return -1;
            }
            return -1;
        }

        /// <summary>Round 3: the table patient's body part (his OperationPatientRig hit triggers) under the crosshair,
        /// nothing solid but his own body in front of it; -1 when none or when nobody is on the table.</summary>
        private int FindTablePatient(Transform eye)
        {
            var table = CaptureDirector.Instance != null ? CaptureDirector.Instance.Table : null;
            if (table == null || table.PatientObject == null || table.State == null) return -1;
            Transform patient = table.PatientObject.transform;
            var hits = UnityEngine.Physics.RaycastAll(eye.position, eye.forward, Reach, ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Collide);
            System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
            foreach (var hit in hits)
            {
                bool own = hit.collider.transform.IsChildOf(patient);
                if (own && hit.collider.TryGetComponent(out OperationTargetTag tag) && tag.kind == TargetKind.Body) return tag.index;
                if (own || hit.collider.isTrigger || hit.collider.transform.IsChildOf(pawn.transform)) continue;
                return -1;
            }
            return -1;
        }

        private static TieTarget PartOf(GreyboxNpc npc, Collider collider, Vector3 point)
        {
            NpcRagdoll rag = npc.Ragdoll;
            if (rag != null && rag.Active && rag.Profile != null)
            {
                int part = rag.PartOf(collider);
                if (part >= 0 && part < rag.Profile.Parts.Length)
                {
                    var kind = rag.Profile.Parts[part].Kind;
                    if (kind == NpcRagdollProfile.Kind.UpperArm || kind == NpcRagdollProfile.Kind.ForeArm) return TieTarget.Hands;
                    if (kind == NpcRagdollProfile.Kind.Thigh || kind == NpcRagdollProfile.Kind.Calf) return TieTarget.Feet;
                }
                return TieTarget.None;
            }
            // The capsule: the lower third is the legs.
            return npc.ZoneAt(point) == HitZone.Limb ? TieTarget.Feet : TieTarget.None;
        }

        private void Use(bool justPressed)
        {
            if (Tool == FieldTool.Blood && AimedBag >= 0) { if (justPressed) PourIntoBag(AimedBag); return; }
            if (AimedTablePart >= 0) { UseOnTable((BodyPart)AimedTablePart, justPressed); return; }
            CaptureNpc target = Aimed;
            if (target == null)
            {
                if (justPressed) Refuse(AimedNpc != null ? (AimedNpc.State == NpcState.Free ? "Сначала оглуши его (Q)" : "Он ещё не пойман") : "Наведи на человека");
                return;
            }
            switch (Tool)
            {
                case FieldTool.Ties: UseTies(target, justPressed); break;
                case FieldTool.Anesthesia: UseAnesthesia(target, justPressed); break;
                case FieldTool.Blood: UseBlood(target, justPressed); break;
            }
        }

        private void PourIntoBag(int bag)
        {
            var table = CaptureDirector.Instance != null ? CaptureDirector.Instance.Table : null;
            if (BloodFill < 1f) { Refuse(BloodFill > 0.01f ? "Шприц набран не до конца — сначала добери порцию" : "Шприц пуст"); return; }
            if (table == null || !table.BagFree(bag)) { Refuse("Этот пакет уже занят"); return; }
            if (!table.ServerFieldTransfer(bag, f =>
            {
                BloodFill = Mathf.Clamp01(f);
                Transferring = f > 0.0001f;
                if (!Transferring) CaptureDirector.Instance?.Toast("Кровь перелита в пакет (+1)", CaptureHud.Good);
            })) { Refuse("Сейчас нельзя — пакет занят"); return; }
            Transferring = true;
            Debug.Log($"[CAPTURE] field syringe -> table bag {bag}");
        }

        private void UseTies(CaptureNpc target, bool justPressed)
        {
            if (Ties <= 0) { if (justPressed) Refuse("Стяжки кончились"); return; }
            if (!target.CanBeTied) { if (justPressed) Refuse("Связать можно только лежачего"); return; }
            TieTarget tie = CaptureRules.ChooseTie(target.Ties, AimedPart);
            if (tie == TieTarget.None) { if (justPressed) Refuse("Он уже связан по рукам и ногам"); return; }
            if (holdTarget != target || holdTie != tie)
            {
                holdTarget = target;
                holdTable = false;
                holdTie = tie;
                holdTime = 0f;
            }
            Using = true;
            holdTime += Time.deltaTime;
            if (holdTime < CaptureRules.TieSeconds) return;
            target.Tie(tie);
            Ties--;
            holdTime = 0f;
            holdTarget = null;
            CaptureDirector.Instance?.Toast(tie == TieTarget.Hands ? "Руки стянуты!" : "Ноги стянуты!", CaptureHud.Good);
            CaptureSounds.Zip(target.Npc.Center);
        }

        private void UseAnesthesia(CaptureNpc target, bool justPressed)
        {
            if (!target.Alive) { if (justPressed) Refuse("Он мёртв — наркоз уже не нужен"); return; }
            if (AnesthesiaBarrel <= 0.0001f) { if (justPressed) Refuse("Шприц пуст — возьми другой слот и снова этот, чтобы заправить"); return; }
            float amount = Mathf.Min(AnesthesiaBarrel, tuning.dosePerSecond * Time.deltaTime);
            AnesthesiaBarrel -= amount;
            target.QueueDose(amount);
            Using = true;
        }

        private void UseBlood(CaptureNpc target, bool justPressed)
        {
            // One portion per syringe (round 2): a full syringe is emptied into a bag at the table first.
            if (BloodFill >= 1f) { if (justPressed) Refuse("Шприц полон — перелей кровь в пустой пакет на столе"); return; }
            // One portion per press: a new portion needs a new press (no sliding into the lethal third by holding on).
            if (justPressed) bloodLatched = false;
            if (bloodLatched) return;
            FieldRefusal why = target.CanDrawBlood();
            if (why != FieldRefusal.None)
            {
                if (justPressed || Time.time >= nextRefusalAt)
                {
                    nextRefusalAt = Time.time + 1.2f;
                    Refuse(why == FieldRefusal.Dead ? "Из трупа кровь не идёт" :
                           why == FieldRefusal.NoBloodLeft ? "Больше нельзя — он не выдержит" :
                           "Дёргается! Усыпи или свяжи ему руки");
                }
                return;
            }
            Using = true;
            if (target.DrawBlood(ref BloodFill, Time.deltaTime))
            {
                BloodFill = 1f;
                bloodLatched = true;
                int portions = target.State.bloodPortions;
                CaptureDirector.Instance?.Toast(portions >= tuning.fatalPortion ? "Третья порция… он не выжил" :
                    portions == tuning.weakenedPortion ? "Шприц полон. Он совсем бледный — перелей кровь в пакет на столе" : "Шприц полон — перелей кровь в пакет на столе",
                    portions >= tuning.fatalPortion ? CaptureHud.Bad : CaptureHud.Good);
            }
        }

        // ---------- round 3: the kit on the table patient ----------

        /// <summary>A player by the table (not in its view) uses the kit on the strapped patient: ties on a limb, the
        /// anaesthesia syringe on an injection site, the blood syringe on an arm. Dose and portions are the table's own
        /// server rules (NetworkOperationTable.ServerFieldDose / ServerFieldDrawBlood); the barrel and the fill stay in this kit.</summary>
        private void UseOnTable(BodyPart part, bool justPressed)
        {
            var d = CaptureDirector.Instance;
            var table = d != null ? d.Table : null;
            if (table == null || table.State == null) return;
            OpHint why = OpHint.None;
            switch (Tool)
            {
                case FieldTool.Ties:
                {
                    if (Ties <= 0) { if (justPressed) Refuse("Стяжки кончились"); return; }
                    TieTarget tie = d.Bridge != null ? d.Bridge.TableTieFor(part) : TieTarget.None;
                    if (tie == TieTarget.None) { if (justPressed) Refuse("Стяжку — на руку или ногу (или он уже связан)"); return; }
                    if (!holdTable || holdTie != tie) { holdTable = true; holdTarget = null; holdTie = tie; holdTime = 0f; }
                    Using = true;
                    holdTime += Time.deltaTime;
                    if (holdTime < CaptureRules.TieSeconds) return;
                    holdTime = 0f;
                    holdTable = false;
                    if (!d.Bridge.TieTablePatient(tie)) return;
                    Ties--;
                    d.Toast(tie == TieTarget.Hands ? "Руки стянуты!" : "Ноги стянуты!", CaptureHud.Good);
                    CaptureSounds.Zip(table.PatientObject != null ? table.PatientObject.transform.position : table.transform.position);
                    return;
                }
                case FieldTool.Anesthesia:
                {
                    if (AnesthesiaBarrel <= 0.0001f) { if (justPressed) Refuse("Шприц пуст — возьми другой слот и снова этот, чтобы заправить"); return; }
                    float amount = Mathf.Min(AnesthesiaBarrel, tuning.dosePerSecond * Time.deltaTime);
                    float accepted = table.ServerFieldDose(part, amount, out why);
                    if (why == OpHint.None) { AnesthesiaBarrel -= accepted; Using = accepted > 0f; return; }
                    break;
                }
                case FieldTool.Blood:
                {
                    if (BloodFill >= 1f) { if (justPressed) Refuse("Шприц полон — перелей кровь в пустой пакет на столе"); return; }
                    if (justPressed) bloodLatched = false;
                    if (bloodLatched) return;
                    why = table.ServerFieldDrawBlood(part, ref BloodFill, Time.deltaTime, out bool portion);
                    if (why != OpHint.None) break;
                    Using = true;
                    if (!portion) return;
                    BloodFill = 1f;
                    bloodLatched = true;
                    int portions = table.State.bloodPortions;
                    d.Toast(portions >= tuning.fatalPortion ? "Третья порция… он не выжил" : "Шприц полон — перелей кровь в пустой пакет на столе",
                        portions >= tuning.fatalPortion ? CaptureHud.Bad : CaptureHud.Good);
                    return;
                }
                default: return;
            }
            if (justPressed || Time.time >= nextRefusalAt)
            {
                nextRefusalAt = Time.time + 1.2f;
                Refuse(TableRefusal(why));
            }
        }

        private string TableRefusal(OpHint why) => why switch
        {
            OpHint.WrongSpot => Tool == FieldTool.Anesthesia ? "Коли в руку, плечо или шею" : "Кровь берут из руки",
            OpHint.PatientDead => "Он мёртв — наркоз уже не нужен",
            OpHint.NotOnTable => "Он ещё не лёг на стол",
            OpHint.SyringeFull => "Шприц полон — перелей кровь в пакет",
            OpHint.NoBloodLeft => "Больше нельзя — он не выдержит",
            OpHint.Squirming => "Дёргается! Усыпи его или пристегни эту руку",
            _ => "Сейчас нельзя",
        };

        private void Refuse(string text)
        {
            refusal = text;
            refusalUntil = Time.unscaledTime + 1.8f;
            CaptureSounds.Error();
        }

        // ---------- HUD ----------

        private void UpdateHud(bool active)
        {
            if (hud == null) return;
            if (!active)
            {
                hud.Card(null, null);
                hud.Ring(-1f, Color.white, "");
                hud.Dose(false, 0f, 0f, 0f, 0f);
                hud.Hint(null);
                return;
            }
            CaptureNpc t = Aimed;
            if (t != null) hud.Card(CardTitle(t), CardBody(t));
            else hud.Card(null, null);
            if (Tool == FieldTool.Ties && (holdTarget != null || holdTable)) hud.Ring(HoldProgress, CaptureHud.Good, holdTie == TieTarget.Hands ? "стягиваю руки…" : "стягиваю ноги…");
            else if (Tool == FieldTool.Blood && Transferring) hud.Ring(1f - BloodFill, CaptureHud.Bad, "переливаю в пакет…");
            else if (Tool == FieldTool.Blood && Using) hud.Ring(BloodFill, CaptureHud.Bad, "набираю кровь…");
            else hud.Ring(-1f, Color.white, "");
            OperationState onTable = AimedTablePart >= 0 && CaptureDirector.Instance != null && CaptureDirector.Instance.Table != null ? CaptureDirector.Instance.Table.State : null;
            OperationState dosed = t != null ? t.State : onTable;
            hud.Dose(Tool == FieldTool.Anesthesia && dosed != null && dosed.alive, dosed != null ? dosed.residual : 0f,
                tuning.suitableMinimum, tuning.suitableMaximum, tuning.overdoseAbove);
            string hint = Time.unscaledTime < refusalUntil ? refusal : null;
            if (hint == null && Tool == FieldTool.Blood && AimedBag >= 0)
                hint = BloodFill >= 1f ? "ЛКМ — перелить кровь в пакет" : "Шприц не полон: сначала набери порцию";
            if (hint == null && onTable != null && Tool != FieldTool.Hands)
                hint = Tool == FieldTool.Ties ? $"ЛКМ (держать) — стяжка на пациента  ·  стяжек {Ties}"
                     : Tool == FieldTool.Anesthesia ? $"ЛКМ (держать) — колоть наркоз в руку/шею · следи за шкалой  ·  шприц {AnesthesiaBarrel:0.0}"
                     : BloodFill >= 1f ? "Шприц полон — перелей кровь в пустой пакет на столе"
                     : "ЛКМ (держать) по руке — набрать кровь";
            if (hint == null && t != null && Tool != FieldTool.Hands)
                hint = Tool == FieldTool.Ties ? "ЛКМ (держать) — стянуть " + (CaptureRules.ChooseTie(t.Ties, AimedPart) == TieTarget.Feet ? "ноги" : "руки") + $"  ·  стяжек {Ties}"
                     : Tool == FieldTool.Anesthesia ? $"ЛКМ (держать) — колоть наркоз · следи за шкалой  ·  шприц {AnesthesiaBarrel:0.0}, запас {AnesthesiaStock:0.0}"
                     : BloodFill >= 1f ? "Шприц полон — перелей кровь в пустой пакет на столе"
                     : "ЛКМ (держать) — набрать кровь";
            if (hint == null && Tool != FieldTool.Hands)
                hint = Tool == FieldTool.Ties ? $"Стяжки: {Ties}  ·  ЛКМ по лежачему"
                     : Tool == FieldTool.Anesthesia ? $"Шприц наркоза: {AnesthesiaBarrel:0.0}, запас {AnesthesiaStock:0.0}  ·  ЛКМ по человеку"
                     : BloodFill >= 1f ? "Шприц полон  ·  ЛКМ по пустому пакету на столе"
                     : $"Шприц для крови: {Mathf.RoundToInt(BloodFill * 100f)}%  ·  ЛКМ по человеку";
            hud.Hint(hint);
        }

        private string CardTitle(CaptureNpc t)
        {
            string id = t.PatientId.Length > 5 ? t.PatientId.Substring(t.PatientId.Length - 5).ToUpperInvariant() : t.PatientId;
            return (t.Alive ? "Пойман" : "Труп") + " · №" + id;
        }

        private string CardBody(CaptureNpc t)
        {
            var s = t.State;
            string status = !s.alive ? "<color=#FF4D5E>мёртв</color>" :
                s.Sleeping ? $"<color=#7FB2FF>спит {Mathf.FloorToInt(s.sleepRemaining / 60f)}:{Mathf.FloorToInt(s.sleepRemaining % 60f):00}</color>" :
                t.Npc.State == NpcState.Down ? (t.Npc.Phase == StunPhase.Out ? "в отключке" : "<color=#FFB13B>очухивается</color>") :
                "<color=#FF4D5E>в сознании</color>";
            string dose = !s.alive ? "" : s.residual > tuning.suitableMaximum ? "  ·  <color=#FF4D5E>наркоза многовато!</color>" :
                s.residual >= tuning.suitableMinimum ? "  ·  наркоз в норме" : s.residual > 0.05f ? "  ·  наркоза мало" : "";
            string ties = t.Ties.Any ? t.Ties.ToString() : "не связан";
            return CaptureDirector.DistrictName(t.Facts.districtId) + " · " + CaptureDirector.TypeName(t.Facts.npcTypeId) + "\n" +
                   status + dose + "\n" +
                   "кровь " + s.bloodPortions + "/3  ·  " + ties + "\n" +
                   "состояние " + Mathf.RoundToInt(t.Facts.condition);
        }

        private void OnDisable()
        {
            viewModel?.SetVisible(false);
            if (hud != null) UpdateHud(false);
        }
    }
}
