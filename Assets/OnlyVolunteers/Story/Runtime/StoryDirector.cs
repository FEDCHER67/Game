using System.Collections.Generic;
using FishNet.Connection;
using OnlyVolunteers.Buyers.Runtime;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Story
{
    /// <summary>
    /// The story runtime of a session (STORY_MISSIONS_SPEC v01), one per TeamEconomy (added by TeamEconomy.Ensure, every
    /// machine). Server: reconciles world facts once per loaded state, ticks the M06 replacement clock, keeps the ONE M06
    /// rival (an existing crowd template with the authored PersonId) at his Stroyka canopy 08:00-18:00 / off-shift spot
    /// while he is free, reports an authoritative death once, and handles the story requests (mechanic, first organ buyer,
    /// C01 placeholder sale, capture DEV aids) by measuring actor, target and zone itself. Every commit goes through the
    /// economy state (EconomyState story / sale methods), so it is saved with the fund in the same save block. Clients:
    /// in-world prompts and E / Shift+E intents only; the answer comes from the host.
    /// Placeholders: the mechanic and C01 have no character yet (anchor posts + titles); the C01 sale is a stand-in for the
    /// unimplemented call / arrival; the first buyer's office is the existing W86 crate.
    /// </summary>
    [DefaultExecutionOrder(-60)]
    public sealed class StoryDirector : MonoBehaviour
    {
        public const float MechanicRadius = 3f, C01Radius = 2.6f, BuyerRadius = 3.2f, ServerTolerance = 1.5f;
        /// <summary>A free rival is only moved to his schedule spot when no player can see the jump.</summary>
        public const float UnobservedRadius = 30f;

        private TeamEconomy economy;
        private EconomyState reconciledFor;
        private float nextServerTick;
        private float nextRivalSearch;
        private GreyboxNpc rival;
        private bool warnedNoTemplate;
        // client prompt
        private string prompt = "";
        private string answer = "";
        private bool answerOk;
        private float answerUntil;
        private bool busy;
        private GUIStyle style;

        private void Awake()
        {
            economy = GetComponent<TeamEconomy>();
            TeamEconomy.StoryHandler = Handle;
        }

        private void OnDestroy()
        {
            if (TeamEconomy.StoryHandler == (System.Func<EconomyRequestBroadcast, NetworkConnection, EconomyState, (bool, string)>)Handle) TeamEconomy.StoryHandler = null;
        }

        private void Update()
        {
            if (economy != null && economy.ServerReady && Time.unscaledTime >= nextServerTick)
            {
                nextServerTick = Time.unscaledTime + 0.5f;
                ServerTick(economy.ServerState);
            }
            ClientPrompts();
        }

        // ================================================================== server

        private void ServerTick(EconomyState state)
        {
            CaptureDirector capture = CaptureDirector.Instance;
            if (capture != null && !capture.Loaded) return; // the save restores captured NPCs first: never spawn before it
            if (reconciledFor != state)
            {
                reconciledFor = state;
                bool vanInWorld = capture != null && FindAnyObjectByType<VanController>() != null;
                bool tutorial = capture != null && capture.Syringes != null && capture.Syringes.Sales != null && capture.Syringes.Sales.FirstSyringeSold;
                if (state.ReconcileStory(vanInWorld, tutorial)) Debug.Log("[STORY] reconciled world facts: " + Facts(state), this);
            }
            state.TickStory();
            if (capture != null) ManageRival(state, capture);
        }

        private static string Facts(EconomyState s)
        {
            var list = new List<string>();
            foreach (StoryFactRecord f in s.Story.Facts) list.Add(f.key);
            return string.Join(", ", list);
        }

        private void ManageRival(EconomyState state, CaptureDirector capture)
        {
            StoryState story = state.Story;
            if (story.HasFact(StoryFacts.RivalDelivered) || story.Rival.Life == RivalLife.Resolved) return;
            string id = story.RivalPersonId;
            if ((rival == null || TagOf(rival) != id) && Time.unscaledTime >= nextRivalSearch)
            {
                nextRivalSearch = Time.unscaledTime + 1.5f;
                rival = FindRival(id);
            }
            if (story.Rival.Life == RivalLife.AtLarge)
            {
                string why = null;
                if (rival != null && rival.TryGetComponent(out CaptureNpc c) && c.State != null && !c.State.alive) why = "погиб";
                else if (OnTable(capture, id, out bool tableAlive) && !tableAlive) why = "умер на столе";
                else if (CorpseOf(capture, id)) why = "погиб";
                if (why != null)
                {
                    if (state.ReportRivalLost(id, why)) Debug.Log($"[STORY] M06 target {id} lost ({why}): replacement from the next 06:00, generation {story.Rival.generation + 1}", this);
                    return;
                }
            }
            if (story.Rival.Life != RivalLife.AtLarge || OnTable(capture, id, out _)) return;
            RivalPlace place = RivalRules.PlaceAt(RivalRules.HourOfDay(state.AbsoluteHours));
            StoryAnchor spot = StoryAnchor.Find(place == RivalPlace.Canopy ? StoryAnchor.RivalCanopy : StoryAnchor.RivalOffShift)
                               ?? StoryAnchor.Find(StoryAnchor.RivalCanopy);
            if (spot == null) return;
            if (rival == null)
            {
                // Not captured, not on the table, not a corpse, not in the world: the free original is absent (a fresh
                // session or a load: free NPCs are crowd, not saved). One instance of the CURRENT generation, never a clone.
                rival = Spawn(id, spot);
                return;
            }
            rival.TryGetComponent(out CaptureNpc cap);
            bool captured = rival.State != NpcState.Free || rival.InCargo || (cap != null && cap.Ties.Any);
            bool moving = rival.TryGetComponent(out CharacterController cc) && cc.velocity.sqrMagnitude > 0.25f;
            if (!RivalRules.RoutineMayMove(rival.State == NpcState.Free, moving, captured, true, false)) return;
            Vector3 at = spot.transform.position;
            if ((rival.transform.position - at).sqrMagnitude < 16f) return;
            if (PlayerNear(rival.transform.position, UnobservedRadius) || PlayerNear(at, UnobservedRadius)) return;
            Place(rival, at, spot.transform.rotation);
            Debug.Log($"[STORY] rival {id} back at his {(place == RivalPlace.Canopy ? "canopy (shift 08-18)" : "off-shift spot")}", this);
        }

        private static string TagOf(GreyboxNpc npc) => npc != null && npc.TryGetComponent(out PatientTag t) ? t.PatientId : "";

        private static GreyboxNpc FindRival(string id)
        {
            GreyboxNpc keep = null;
            foreach (PatientTag tag in FindObjectsByType<PatientTag>(FindObjectsInactive.Exclude))
            {
                if (tag == null || tag.PatientId != id || !tag.TryGetComponent(out GreyboxNpc npc)) continue;
                if (keep == null) { keep = npc; continue; }
                // Two bodies with one PersonId must never exist: keep the captured / restored one, drop a free duplicate.
                GreyboxNpc free = npc.State == NpcState.Free && !npc.InCargo ? npc : keep.State == NpcState.Free && !keep.InCargo ? keep : null;
                if (free == null) { Debug.LogError($"[STORY] two captured bodies with PersonId {id}: {keep.name}, {npc.name}"); continue; }
                Debug.LogWarning($"[STORY] duplicate free body of {id} removed ({free.name})");
                if (free == keep) keep = npc;
                Destroy(free.gameObject);
            }
            return keep;
        }

        private static bool OnTable(CaptureDirector capture, string id, out bool alive)
        {
            alive = true;
            var table = capture.Table;
            if (table == null || !table.HasPatient || table.State == null || table.State.patientId != id) return false;
            alive = table.State.alive;
            return true;
        }

        private static bool CorpseOf(CaptureDirector capture, string id)
        {
            if (capture.Disposal == null) return false;
            foreach (CaptureCorpse corpse in capture.Disposal.Corpses) if (corpse != null && corpse.PatientId == id) return true;
            return false;
        }

        private GreyboxNpc Spawn(string id, StoryAnchor spot)
        {
            GameObject template = PickTemplate();
            if (template == null)
            {
                if (!warnedNoTemplate) { warnedNoTemplate = true; Debug.LogWarning("[STORY] no crowd template: the M06 rival cannot appear in this scene"); }
                return null;
            }
            Transform parent = template.transform.parent != null ? template.transform.parent.parent : null;
            GameObject go = Instantiate(template, spot.transform.position + Vector3.up * 0.05f, spot.transform.rotation, parent);
            go.name = "Story_" + id;
            if (go.TryGetComponent(out CrowdWalker walker)) Destroy(walker);
            if (!go.TryGetComponent(out PatientTag tag)) tag = go.AddComponent<PatientTag>();
            tag.PatientId = id;
            go.SetActive(true);
            var npc = go.GetComponent<GreyboxNpc>();
            if (npc == null) { Destroy(go); return null; }
            // No crowd walker: a plain free GreyboxNpc stands at his spot (gravity, idle clip), and still flees, is stunned,
            // captured and tied like anyone (the same lifecycle as a restored captive, CaptureSave.Respawn).
            Debug.Log($"[STORY] M06 rival {id} appears at {spot.Id} {spot.transform.position} (template {template.name})", this);
            return npc;
        }

        private static GameObject PickTemplate()
        {
            var crowd = CrowdDirector.Instance;
            if (crowd == null || crowd.Templates == null) return null;
            GameObject first = null;
            foreach (GameObject t in crowd.Templates)
            {
                if (t == null || t.GetComponent<GreyboxNpc>() == null) continue;
                first ??= t;
                var a = t.GetComponentInChildren<Animator>(true);
                string n = (a != null ? a.gameObject.name : t.name).ToUpperInvariant();
                if (n.Contains("CONSTR")) return t;
            }
            return first;
        }

        private static void Place(GreyboxNpc npc, Vector3 at, Quaternion rotation)
        {
            var controller = npc.GetComponent<CharacterController>();
            bool was = controller != null && controller.enabled;
            if (controller != null) controller.enabled = false;
            npc.transform.SetPositionAndRotation(at + Vector3.up * 0.05f, rotation);
            if (controller != null) controller.enabled = was;
            Physics.SyncTransforms();
        }

        private static bool PlayerNear(Vector3 p, float radius)
        {
            var capture = CaptureDirector.Instance;
            if (capture != null && capture.Pawn != null && (capture.Pawn.Position - p).sqrMagnitude < radius * radius) return true;
            Camera cam = Camera.main;
            return cam != null && (cam.transform.position - p).sqrMagnitude < radius * radius;
        }

        /// <summary>The host's own requests (direct on the server, or its local client connection).</summary>
        private static bool FromHost(NetworkConnection from) =>
            from == null || from.IsLocalClient || (FishNet.InstanceFinder.ClientManager != null && from == FishNet.InstanceFinder.ClientManager.Connection);

        private static Vector3? ActorPosition(NetworkConnection from)
        {
            var capture = CaptureDirector.Instance;
            if (FromHost(from) && capture != null && capture.Pawn != null && capture.Pawn.Controlled) return capture.Pawn.Position;
            if (from != null && from.FirstObject != null) return from.FirstObject.transform.position;
            return null;
        }

        private static bool Within(Vector3? actor, Vector3 point, float radius) =>
            actor.HasValue && (actor.Value - point).sqrMagnitude <= radius * radius;

        private static bool NearMechanic(Vector3? actor, Vector3 point) =>
            actor.HasValue && OnlyVolunteers.Economy.MechanicTalkReach.ServerAccepts(actor.Value.x - point.x, actor.Value.y - point.y, actor.Value.z - point.z);

        // ---------- requests ----------

        private (bool, string) Handle(EconomyRequestBroadcast m, NetworkConnection from, EconomyState state)
        {
            var kind = (EconomyRequestKind)m.Kind;
            switch (kind)
            {
                case EconomyRequestKind.StoryMechanic: return Mechanic(from, state);
                case EconomyRequestKind.StoryMeetOrganBuyer: return MeetBuyer(from, state);
                case EconomyRequestKind.StoryC01Sale: return C01Sale(from, state, m.Arg == "1" ? SyringeReturnChoice.LeaveWithBuyer : SyringeReturnChoice.TakeEmpty);
                case EconomyRequestKind.DevGiveTies:
                {
                    var capture = CaptureDirector.Instance;
                    if (capture == null || capture.Kit == null) return (false, "Нет полевого набора в этой сцене");
                    capture.Kit.Ties += 4;
                    return (true, "DEV: +4 стяжки (теперь " + capture.Kit.Ties + ")");
                }
                case EconomyRequestKind.DevGiveBloodSyringe:
                {
                    var inv = CaptureDirector.Instance != null && CaptureDirector.Instance.Kit != null && CaptureDirector.Instance.Kit.Inventory != null ? CaptureDirector.Instance.Kit.Inventory.Model : null;
                    if (inv == null) return (false, "Нет инвентаря карты");
                    int price;
                    try { price = SyringeRules.Price(SyringeKind.Blood); } catch (System.Exception) { price = 0; }
                    bool added = inv.TryAdd(new ItemStack(SyringeRules.BloodDefinitionId, 1, price, SyringeInstance.New(SyringeKind.Blood))) == 1;
                    return added ? (true, "DEV: новый пустой шприц крови в хотбаре") : (false, "Нет места в хотбаре");
                }
                case EconomyRequestKind.DevNextMorning:
                {
                    state.DevJumpToNextDay(9.0);
                    var clock = FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
                    if (clock != null) clock.SetHour(9f);
                    return (true, "DEV: следующее утро, 09:00 (день " + state.WorldDay + ")");
                }
                default: return (false, "Неверный запрос");
            }
        }

        private (bool, string) Mechanic(NetworkConnection from, EconomyState state)
        {
            StoryAnchor mechanic = StoryAnchor.Find(StoryAnchor.WorkshopMechanic);
            if (mechanic == null) return (false, "В этой сцене нет механика");
            Vector3? actor = ActorPosition(from);
            // he walks a short workshop route (MECHANIC_W86 v01): near his body counts as well as near his anchor
            // (29.10) the same reach as his conversation menu (MechanicTalkReach: the crosshair reaches 4.5 m, the open menu
            // keeps a leash), so a line chosen in the open menu is never refused for distance
            var brain = OnlyVolunteers.Economy.WorkshopMechanicBrainV01.Instance;
            bool nearBody = brain != null && brain.HasBody && NearMechanic(actor, brain.BodyPosition);
            if (!nearBody && !NearMechanic(actor, mechanic.transform.position)) return (false, RivalRules.Explain(HandInRefusal.ActorInvalid));
            JournalState m06 = state.Story.StateOf(MissionId.M06);
            if (m06 != JournalState.Active)
            {
                EconomyState.StoryResult a = state.AcceptMechanicTask();
                Debug.Log($"[STORY] M06 at the mechanic: {(a.Ok ? (a.Replayed ? "replayed" : "ACCEPTED") : "refused")} - {a.Message}", this);
                return (a.Ok, a.Message);
            }
            RivalHandInCheck check = MeasureHandIn(actor, out GreyboxNpc body);
            EconomyState.StoryResult r = state.CompleteRivalHandIn(check);
            Debug.Log($"[STORY] M06 hand-in {check.PersonId}: {(r.Ok ? (r.Replayed ? "replayed" : "COMPLETED, workshop unlocked") : "refused")} - {r.Message} " +
                      $"(found {check.TargetFound}, alive {check.Alive}, hands {check.HandsTied}, feet {check.FeetTied}, zone {check.InZone}, van {check.InVan}, held {check.Held})", this);
            if (r.Ok && !r.Replayed && body != null) ResolveRival(body);
            return (r.Ok, r.Message);
        }

        /// <summary>The server's own measurement of the hand-in: the body in the western receiving zone (the current target
        /// first, else whoever lies there, which is then the wrong person), its capture facts and who moves it.</summary>
        private RivalHandInCheck MeasureHandIn(Vector3? actor, out GreyboxNpc body)
        {
            body = null;
            var check = new RivalHandInCheck { ActorValid = actor.HasValue };
            var economyState = economy != null ? economy.ServerState : null;
            string id = economyState != null ? economyState.Story.RivalPersonId : "";
            StoryAnchor zone = StoryAnchor.Find(StoryAnchor.RivalHandIn);
            var capture = CaptureDirector.Instance;
            if (capture != null && OnTable(capture, id, out bool tableAlive))
            {
                check.TargetFound = true; check.PersonId = id; check.Alive = tableAlive; check.OnTable = true;
                return check;
            }
            GreyboxNpc target = rival != null && TagOf(rival) == id ? rival : FindRival(id);
            GreyboxNpc other = null;
            if (zone != null)
                foreach (CaptureNpc c in CaptureNpc.All)
                    if (c != null && c.Npc != null && !c.Admitted && c.Npc != target && zone.Contains(BodyCenter(c.Npc))) { other = c.Npc; break; }
            bool targetInZone = target != null && zone != null && zone.Contains(BodyCenter(target));
            GreyboxNpc measured = targetInZone ? target : other ?? target;
            if (measured == null) return check;
            body = measured;
            check.TargetFound = true;
            check.PersonId = TagOf(measured);
            measured.TryGetComponent(out CaptureNpc facts);
            check.Alive = facts == null || facts.Alive;
            check.HandsTied = facts != null && facts.Ties.hands;
            check.FeetTied = facts != null && facts.Ties.feet;
            check.InZone = zone != null && zone.Contains(BodyCenter(measured));
            check.InVan = measured.InCargo;
            check.Held = measured.PhysicalBody != null && measured.PhysicalBody.Active && measured.PhysicalBody.HolderCount > 0;
            return check;
        }

        private static Vector3 BodyCenter(GreyboxNpc npc)
        {
            var body = npc.PhysicalBody;
            return body != null && body.Active ? body.Landmark(OnlyVolunteers.Characters.Npc.NpcLandmark.Pelvis) : npc.Center;
        }

        /// <summary>Off-screen authored custody (spec §9 Proposed): the delivered rival leaves capture circulation at once —
        /// after the commit, in the same frame, so the save of this commit no longer contains him.</summary>
        private void ResolveRival(GreyboxNpc body)
        {
            var capture = CaptureDirector.Instance;
            string id = TagOf(body);
            if (capture != null) capture.Facts.Remove(id);
            if (body.TryGetComponent(out CaptureNpc c)) c.Admitted = true;
            Destroy(body.gameObject);
            if (rival == body) rival = null;
            capture?.Toast("Механик забрал конкурента. Мастерская открыта!", CaptureHud.Good, 5f);
        }

        private (bool, string) MeetBuyer(NetworkConnection from, EconomyState state)
        {
            var crate = FirstBuyerCrateV01.Instance;
            if (crate == null) return (false, "Скупщика здесь нет");
            if (!Within(ActorPosition(from), crate.transform.position, BuyerRadius + ServerTolerance)) return (false, "Подойди к ящику скупщика");
            EconomyState.StoryResult r = state.CommitFirstOrganBuyerAcquaintance("acquaintance at the first-buyer crate (office placeholder)");
            Debug.Log($"[STORY] M05 acquaintance: {(r.Ok ? (r.Replayed ? "replayed" : "COMMITTED") : "refused")} - {r.Message}", this);
            return (r.Ok, r.Message);
        }

        /// <summary>C01 placeholder sale (spec M01 step 5, economy §5.3): blood in the HELD syringe, at C01's arrival point,
        /// confirmed by an explicit interaction. The map inventory is the host's local hotbar, so only the host can sell
        /// here until the networked inventory carries the map hotbar. One payout per PortionId (EconomySyringePayout).</summary>
        private (bool, string) C01Sale(NetworkConnection from, EconomyState state, SyringeReturnChoice choice)
        {
            var capture = CaptureDirector.Instance;
            StoryAnchor c01 = StoryAnchor.Find(StoryAnchor.C01ArrivalB02);
            if (capture == null || c01 == null) return (false, "C01 здесь нет");
            if (!FromHost(from)) return (false, "Продать C01 пока может только хост (инвентарь карты локальный)");
            if (!Within(ActorPosition(from), c01.transform.position, C01Radius + ServerTolerance)) return (false, "Подойди к C01");
            InventoryModel inv = capture.Kit != null && capture.Kit.Inventory != null ? capture.Kit.Inventory.Model : null;
            if (inv == null) return (false, "Нет инвентаря");
            int slot = inv.SelectedIndex;
            SyringeInstance syringe = inv.GetSlot(slot).Syringe;
            if (syringe == null || syringe.Kind != SyringeKind.Blood || syringe.Discarded) return (false, "C01: «Покажи кровь — возьми шприц с кровью в руку»");
            if (syringe.LegacyUnknown) return (false, "C01: «Откуда этот шприц? Не возьму» (история шприца неизвестна)");
            if (syringe.Portion == null) return (false, "C01: «Шприц пустой»");
            if (!syringe.Portion.Saleable) return (false, "C01: «Кровь уже испортилась — не возьму»");
            capture.Syringes.Sales.FirstBloodXpGranted |= state.FirstBloodGranted; // WP02: the world's ONE first-blood flag (economy)
            var rules = new SyringeSaleRules(capture.Syringes.Sales);
            int quote;
            try { quote = rules.Quote; } catch (System.Exception e) { return (false, "Цена C01 недоступна: " + e.Message); }
            List<string> participants = economy.ServerParticipants();
            string portion = syringe.Portion.Id, person = syringe.PersonId, item = syringe.ItemId;
            bool applied = false;
            var payout = new EconomySyringePayout(state, participants, (next, after) =>
            {
                applied = true;
                capture.Syringes.Sales = next;
                if (after != null && after.Discarded) inv.TakeFromSlot(slot, 1); // "leave with the buyer": this instance leaves the world
            });
            bool ok = rules.TryConfirm("c01:" + portion, syringe.Portion, syringe, Mathf.Clamp(participants.Count, 1, 4), payout, out SyringeSaleReceipt receipt, choice);
            if (!ok) return (false, rules.IsSold(portion) ? "C01: «Эту кровь я уже купил»" : "C01 не взял кровь");
            bool replay = !applied || payout.Last.Replayed; // a known transaction id answers with its receipt, nothing is paid
            Debug.Log($"[STORY] C01 sale: portion {portion} of {person}, syringe {item}: ${receipt.Amount} (quote ${quote}), XP {receipt.XpEach} x {participants.Count}, " +
                      $"{(choice == SyringeReturnChoice.TakeEmpty ? "syringe back (same id/person)" : "syringe left with C01")}; fund ${state.Fund.Balance}", this);
            string text = "C01 заплатил $" + receipt.Amount + (receipt.XpEach > 5 ? " · +" + receipt.XpEach + " XP (первая кровь)" : " · +" + receipt.XpEach + " XP") +
                          (choice == SyringeReturnChoice.TakeEmpty ? " · пустой шприц у тебя (тот же, привязан к этому человеку)" : " · шприц остался у C01");
            return (true, replay ? "Уже продано" : text);
        }

        // ================================================================== client prompts

        private void ClientPrompts()
        {
            prompt = "";
            if (OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            EconomySnapshot snap = EconomyClientView.Current;
            if (snap == null || !snap.ready || economy == null) return;
            var capture = CaptureDirector.Instance;
            Vector3 me;
            if (capture != null) { if (capture.Pawn == null || !capture.Pawn.Controlled) return; me = capture.Pawn.Position; }
            else if (Camera.main != null) me = Camera.main.transform.position; else return;
            Keyboard key = OpsInput.Keyboard;
            bool e = key != null && key.eKey.wasPressedThisFrame && GreyboxInput.EFree && !busy;
            bool shift = key != null && (key.leftShiftKey.isPressed || key.rightShiftKey.isPressed);

            // the mechanic's E (accept M06 / hand the rival over) is a line of his conversation menu now (WorkshopMechanicV01,
            // Fedya 29.10): the same StoryMechanic request, handled by Mechanic() below. Scenes without the menu keep the prompt.
            StoryAnchor mechanic = StoryAnchor.Find(StoryAnchor.WorkshopMechanic);
            if (mechanic != null && (mechanic.transform.position - me).sqrMagnitude <= MechanicRadius * MechanicRadius)
            {
                if (WorkshopMechanicPresent()) return;
                JournalState m06 = EntryState(snap, MissionId.M06);
                prompt = m06 == JournalState.Offered ? "<b>E</b> — поговорить с механиком (поручение)" :
                         m06 == JournalState.Active ? "<b>E</b> — сдать конкурента механику (он должен лежать связанным в зоне приёма)" :
                         m06 == JournalState.Completed ? "Механик: «Мастерская открыта — заезжай в ремонтную зону»" : "<b>E</b> — поговорить с механиком";
                if (e && m06 != JournalState.Completed) Send(EconomyRequestKind.StoryMechanic, "");
                return;
            }
            StoryAnchor c01 = StoryAnchor.Find(StoryAnchor.C01ArrivalB02);
            if (c01 != null && (c01.transform.position - me).sqrMagnitude <= C01Radius * C01Radius)
            {
                prompt = "C01 (заглушка): <b>E</b> — продать кровь в шприце (пустой шприц себе) · <b>Shift+E</b> — продать и оставить шприц C01";
                if (e) Send(EconomyRequestKind.StoryC01Sale, shift ? "1" : "0");
                return;
            }
            var crate = FirstBuyerCrateV01.Instance;
            JournalState m05 = EntryState(snap, MissionId.M05);
            if (crate != null && m05 == JournalState.Active && (crate.transform.position - me).sqrMagnitude <= BuyerRadius * BuyerRadius)
            {
                prompt = "<b>E</b> — познакомиться со скупщиком органов";
                if (e) Send(EconomyRequestKind.StoryMeetOrganBuyer, "");
            }
        }

        private static WorkshopMechanicV01 menu;
        private static float menuLook;

        private static bool WorkshopMechanicPresent()
        {
            if (menu == null && Time.unscaledTime >= menuLook) { menuLook = Time.unscaledTime + 2f; menu = FindAnyObjectByType<WorkshopMechanicV01>(); }
            return menu != null;
        }

        private static JournalState EntryState(EconomySnapshot snap, MissionId id)
        {
            if (snap.journal != null && snap.journal.missions != null)
                foreach (StoryJournalEntry m in snap.journal.missions) if (m.id == id.ToString()) return m.State;
            return JournalState.Locked;
        }

        private void Send(EconomyRequestKind kind, string arg)
        {
            GreyboxInput.UseE();
            busy = true;
            economy.Request(kind, arg, "", 0, (ok, text) =>
            {
                busy = false;
                answer = text;
                answerOk = ok;
                answerUntil = Time.unscaledTime + 5f;
                var capture = CaptureDirector.Instance;
                capture?.Toast(text, ok ? CaptureHud.Good : CaptureHud.Warn, 4.5f);
            });
        }

        private void OnGUI()
        {
            bool showAnswer = CaptureDirector.Instance == null && Time.unscaledTime < answerUntil;
            if (prompt.Length == 0 && !showAnswer) return;
            style ??= new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontSize = 19, richText = true, wordWrap = true };
            string text = prompt.Length > 0 ? prompt : "<color=" + (answerOk ? "#5BE07A" : "#FF8A5B") + ">" + answer + "</color>";
            var r = new Rect(Screen.width * 0.1f, Screen.height * 0.66f, Screen.width * 0.8f, 56f);
            style.normal.textColor = new Color(0f, 0f, 0f, 0.85f);
            GUI.Label(new Rect(r.x + 2f, r.y + 2f, r.width, r.height), StripColor(text), style);
            style.normal.textColor = new Color(1f, 0.93f, 0.75f);
            GUI.Label(r, text, style);
        }

        private static string StripColor(string s) => System.Text.RegularExpressions.Regex.Replace(s, "<.*?>", "");
    }
}
