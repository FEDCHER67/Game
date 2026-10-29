using System;
using FishNet.Connection;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Economy.Pharmacy
{
    /// <summary>
    /// The city pharmacy's cash desk (Pharmacy_W86, Rough 04-H3): E at the purchase point opens the counter list - the nine
    /// G48 consumables with their English names and dollar prices (PharmacyRules, prices through EconomyPrices = the same
    /// values the printed counter cards show). Buy = one unit of a line (ties also as the pack of four line).
    /// Server (the host) commits: it measures the buyer at the desk itself, the room for the goods (G49 syringes: a free
    /// hotbar slot; ties / anaesthetic: the field kit; body bags: the disposal stock; the three bags without a game use yet:
    /// the team's bought count), then PharmacyRules.TryBuy charges the shared fund through EconomyState.Charge (key per
    /// request: a repeated request is not charged or delivered twice; a refusal books nothing), and only a fresh commit
    /// delivers (a NEW SyringeInstance into the hotbar, ties / vial doses into the kit, a bag into the disposal stock). The
    /// economy commit triggers the team save (TeamEconomy -> ServerCommitted), which also writes the kit, stock and hotbar.
    /// Network (PharmacyNetV01): any player's Buy is an intent to the server, which measures THAT player at the desk and
    /// delivers into THAT player's holder: the host's hotbar / field kit, a client's own NetworkInventory (syringes); the
    /// body bags and the team supplies are team stock. The field kit exists only for the host on the map so far: a client
    /// is refused kit goods (ties, anaesthetic vials) before anything is charged. Opening hours (PharmacyHours): outside
    /// 08:00-20:00 the server refuses every new purchase, also from a list that was opened before closing time.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PharmacyCounterV01 : MonoBehaviour
    {
        public const float ServerTolerance = 1.0f;
        public static PharmacyCounterV01 Instance { get; private set; }

        [Tooltip("Reach around the purchase point (flat metres).")]
        public float Radius = 1.5f;

        private bool open, busy;
        private int selected;
        private string prompt = "", status = "";
        private bool statusOk;
        private float statusUntil;
        private Vector2 scroll;
        private KccFirstPersonInput walker;
        private bool savedMove, savedLook, savedVisible;
        private CursorLockMode savedLock;
        private GUIStyle label, title, small, button, row;

        private void OnEnable() => Instance = this;

        private void OnDisable()
        {
            if (open) Close();
            if (Instance == this) Instance = null;
        }

        // ================================================================== client

        private static Vector3? PlayerFeet()
        {
            var capture = CaptureDirector.Instance;
            if (capture != null && capture.Pawn != null && capture.Pawn.Controlled) return capture.Pawn.Position;
            return null;
        }

        private bool InReach(Vector3 p, float extra)
        {
            Vector3 d = p - transform.position;
            float r = Radius + extra;
            return d.x * d.x + d.z * d.z <= r * r && Mathf.Abs(d.y) < 1.5f;
        }

        private void Update()
        {
            prompt = "";
            PharmacyNetV01.Ensure(this);
            Vector3? me = PlayerFeet();
            Keyboard key = OpsInput.Keyboard;
            if (open)
            {
                OnlyVolunteers.UI.OvMenuGate.Blocking = true;
                if (!me.HasValue || !InReach(me.Value, 0.6f)) { Close(); return; }
                if (key == null) return;
                if (key.escapeKey.wasPressedThisFrame) { OnlyVolunteers.UI.OvMenuGate.ConsumeEscape(); Close(); return; }
                if (key.eKey.wasPressedThisFrame || key.tabKey.wasPressedThisFrame) { GreyboxInput.UseE(); Close(); return; }
                int n = PharmacyRules.Offers.Count;
                if (key.upArrowKey.wasPressedThisFrame || key.wKey.wasPressedThisFrame) selected = (selected + n - 1) % n;
                if (key.downArrowKey.wasPressedThisFrame || key.sKey.wasPressedThisFrame) selected = (selected + 1) % n;
                if (key.enterKey.wasPressedThisFrame || key.numpadEnterKey.wasPressedThisFrame || key.spaceKey.wasPressedThisFrame) Buy(PharmacyRules.Offers[selected]);
                return;
            }
            if (!me.HasValue || OnlyVolunteers.UI.OvMenuGate.Blocking || !InReach(me.Value, 0f)) return;
            bool shopOpen = PharmacyNetV01.OpenNow;
            prompt = shopOpen ? "<b>E</b> — касса аптеки (список товаров)" : PharmacyHours.ClosedText + " — касса не работает";
            if (key != null && key.eKey.wasPressedThisFrame && GreyboxInput.EFree)
            {
                GreyboxInput.UseE();
                if (shopOpen) Open();
                else CaptureDirector.Instance?.Toast(PharmacyHours.ClosedText, CaptureHud.Warn, 2.5f);
            }
        }

        private void Open()
        {
            open = true;
            EconomyCatalogSource.Ensure();
            walker = null;
            foreach (var k in FindObjectsByType<KccFirstPersonInput>())
                if (k.isActiveAndEnabled) { walker = k; break; }
            if (walker != null)
            {
                savedMove = walker.MovementLocked; savedLook = walker.LookSuspended;
                walker.MovementLocked = true; walker.LookSuspended = true;
            }
            savedLock = Cursor.lockState; savedVisible = Cursor.visible;
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            OnlyVolunteers.UI.OvMenuGate.Blocking = true;
        }

        private void Close()
        {
            if (!open) return;
            open = false;
            if (walker != null) { walker.MovementLocked = savedMove; walker.LookSuspended = savedLook; walker = null; }
            Cursor.lockState = savedLock; Cursor.visible = savedVisible;
            OnlyVolunteers.UI.OvMenuGate.Blocking = false;
        }

        private void Buy(PharmacyOffer offer)
        {
            if (busy || offer == null) return;
            int shown = offer.Price;
            string request = Guid.NewGuid().ToString("N");
            PharmacyNetV01 net = PharmacyNetV01.Ensure(this);
            if (net == null) { Show(false, "В этой сцене нет аптеки"); return; }
            busy = true;
            // the buyer's intent: catalogue key, the price on its card, a fresh request id (the server commits it once)
            net.Request(PharmacyRequestKind.Buy, offer.CatalogId, shown, (ok, text) =>
            {
                busy = false;
                Show(ok, text);
            }, request);
        }

        private void Show(bool ok, string text)
        {
            status = text;
            statusOk = ok;
            statusUntil = Time.unscaledTime + 4f;
            CaptureDirector.Instance?.Toast(text, ok ? CaptureHud.Good : CaptureHud.Warn, 3.5f);
        }

        // ================================================================== server

        /// <summary>Server: one purchase for the requester's player at the desk (see the class summary). hourOfDay = the
        /// server's game clock (outside the opening hours a new request is refused, nothing booked).</summary>
        public static (bool ok, string text) ServerBuy(string catalogId, int shownPrice, string requestId, NetworkConnection from, double hourOfDay)
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) return (false, "Экономика не запущена");
            if (!economy.ServerReady) return (false, PurchaseResult.Explain(PurchaseError.NotReady));
            PharmacyCounterV01 desk = Instance;
            if (desk == null) return (false, "В этой сцене нет аптеки");
            Vector3? actor = TeamEconomy.ServerActorPosition(from);
            if (!actor.HasValue || !desk.InReach(actor.Value, ServerTolerance)) return (false, "Подойди к кассе аптеки");
            PharmacyOffer offer = PharmacyRules.Find(catalogId);
            if (offer == null) return (false, PharmacyRules.Explain(PharmacyRefusal.UnknownItem));
            bool host = TeamEconomy.IsHostConnection(from);

            var capture = CaptureDirector.Instance;
            CaptureFieldKit kit = host && capture != null ? capture.Kit : null;
            CaptureCorpseDisposal disposal = capture != null ? capture.Disposal : null;
            InventoryModel inv = kit != null && kit.Inventory != null ? kit.Inventory.Model : null;
            NetworkInventory remoteInv = null;
            if (!host)
            {
                remoteInv = from != null && from.FirstObject != null ? from.FirstObject.GetComponentInChildren<NetworkInventory>(true) : null;
                inv = remoteInv != null ? remoteInv.ServerModel : null;
            }
            float room;
            switch (offer.Goods)
            {
                case PharmacyGoods.BloodSyringe:
                case PharmacyGoods.AnaesthesiaSyringe:
                    if (inv == null) return (false, host ? "Нет инвентаря на карте" : "У твоего игрока нет инвентаря на сервере");
                    room = inv.CountThatFits(SyringeDefinition(offer.Goods), 1, Math.Max(0, offer.Price));
                    break;
                case PharmacyGoods.Ties:
                case PharmacyGoods.AnaesthesiaStock:
                    if (!host) return (false, "Полевой набор на карте пока только у хоста: стяжки и наркоз покупает хост");
                    if (kit == null) return (false, "Нет полевого набора на карте");
                    room = float.MaxValue;
                    break;
                case PharmacyGoods.BodyBag:
                    if (disposal == null) return (false, "Нет запаса мешков на карте");
                    room = float.MaxValue;
                    break;
                case PharmacyGoods.TableSupply:
                    if (SupplyTable() == null) return (false, "Операционный стол команды ещё не готов — некуда доставить");
                    room = float.MaxValue;
                    break;
                default:
                    room = float.MaxValue;
                    break;
            }

            PharmacyPurchase r = PharmacyRules.TryBuy(economy.ServerState, offer.CatalogId, shownPrice, requestId, room, hourOfDay);
            if (!r.Ok)
            {
                Debug.Log($"[PHARMACY] {offer.CatalogId}: refused {r.Refusal} (shown ${shownPrice}, catalogue ${offer.Price}, room {room}, hour {hourOfDay:0.00}, {(host ? "host" : "client " + (from != null ? from.ClientId : -1))}); fund ${r.Balance}");
                return (false, r.Message);
            }
            if (r.Replayed) return (true, "Уже оплачено");
            string got = remoteInv != null ? DeliverRemote(offer, remoteInv) : Deliver(offer, kit, disposal, inv, economy.ServerState);
            Debug.Log($"[PHARMACY] PAID ${r.Price} {offer.CatalogId} ({r.Key}) for {(host ? "host" : "client " + from.ClientId)} -> {got}; fund ${r.Balance}");
            return (true, $"Куплено: {offer.Title} — {PharmacyRules.Money(r.Price)} · {got}");
        }

        /// <summary>A client's purchase: syringes into its own NetworkInventory; bags into the team stock / supply.</summary>
        private static string DeliverRemote(PharmacyOffer offer, NetworkInventory inv)
        {
            switch (offer.Goods)
            {
                case PharmacyGoods.BloodSyringe:
                case PharmacyGoods.AnaesthesiaSyringe:
                {
                    SyringeKind kind = offer.Goods == PharmacyGoods.BloodSyringe ? SyringeKind.Blood : SyringeKind.Anaesthesia;
                    bool added = inv.ServerTryAdd(new ItemStack(SyringeDefinition(offer.Goods), 1, Math.Max(0, offer.Price), SyringeInstance.New(kind))) == 1;
                    if (!added) Debug.LogError("[PHARMACY] paid syringe did not fit the client's inventory after the room check: " + offer.CatalogId);
                    return added ? "новый шприц в твоём инвентаре" : "шприц не поместился (ошибка)";
                }
                default:
                {
                    var capture = CaptureDirector.Instance;
                    return Deliver(offer, null, capture != null ? capture.Disposal : null, null, TeamEconomy.Instance != null ? TeamEconomy.Instance.ServerState : null);
                }
            }
        }

        private static int SyringeDefinition(PharmacyGoods g) =>
            g == PharmacyGoods.BloodSyringe ? SyringeRules.BloodDefinitionId : SyringeRules.AnaesthesiaDefinitionId;

        private static string Deliver(PharmacyOffer offer, CaptureFieldKit kit, CaptureCorpseDisposal disposal, InventoryModel inv, EconomyState state)
        {
            switch (offer.Goods)
            {
                case PharmacyGoods.BloodSyringe:
                case PharmacyGoods.AnaesthesiaSyringe:
                {
                    SyringeKind kind = offer.Goods == PharmacyGoods.BloodSyringe ? SyringeKind.Blood : SyringeKind.Anaesthesia;
                    bool added = inv.TryAdd(new ItemStack(SyringeDefinition(offer.Goods), 1, Math.Max(0, offer.Price), SyringeInstance.New(kind))) == 1;
                    if (!added) Debug.LogError("[PHARMACY] paid syringe did not fit after the room check: " + offer.CatalogId);
                    return added ? "новый шприц в хотбаре" : "шприц не поместился (ошибка)";
                }
                case PharmacyGoods.Ties:
                    kit.Ties += Mathf.RoundToInt(offer.Units);
                    return "стяжек в наборе: " + kit.Ties;
                case PharmacyGoods.AnaesthesiaStock:
                    kit.AnesthesiaStock += offer.Units;
                    return $"наркоза в запасе: {kit.AnesthesiaStock:0.#} доз";
                case PharmacyGoods.BodyBag:
                    disposal.Stock += 1;
                    return "мешков для тел: " + disposal.Stock;
                case PharmacyGoods.TableSupply:
                {
                    OperationWorldState w = SupplyTable();
                    if (w == null) { Debug.LogError("[PHARMACY] paid table supply but the table is gone: " + offer.CatalogId); return "стол не найден (ошибка)"; }
                    if (offer.CatalogId == OperationSupplies.SutureKitId) { w.sutureKits += Mathf.RoundToInt(offer.Units); return "наборов для шва на столе: " + w.sutureKits; }
                    w.patches += Mathf.RoundToInt(offer.Units);
                    return "пластырей на столе: " + w.patches;
                }
                default:
                    return "в запасе команды: " + PharmacyRules.Bought(state, offer.CatalogId) + " (в игре пока не используется)";
            }
        }

        /// <summary>The stock the closing supplies go to (rule, Fedya 29.10 / G53): the team's operating table of this map - the
        /// capture director's table at base 2 (the one table the map has); in a scene without it, the first operating table
        /// found. Its world state is saved with the table, so a bought kit survives a reload. Null = no table (nothing sold).</summary>
        private static OperationWorldState SupplyTable()
        {
            var capture = CaptureDirector.Instance;
            NetworkOperationTable table = capture != null ? capture.Table : null;
            if (table == null) table = FindAnyObjectByType<NetworkOperationTable>();
            if (table == null || !table.IsServerInitialized) return null;
            OperationWorldState w = table.ServerWorld;
            return w != null && w.hasSupplies ? w : null;
        }

        /// <summary>What the team holds of an offer's goods now (host view; "" when unknown).</summary>
        private static string Holding(PharmacyOffer offer)
        {
            var capture = CaptureDirector.Instance;
            CaptureFieldKit kit = capture != null ? capture.Kit : null;
            switch (offer.Goods)
            {
                case PharmacyGoods.Ties: return kit != null ? "в наборе " + kit.Ties : "";
                case PharmacyGoods.AnaesthesiaStock: return kit != null ? $"запас {kit.AnesthesiaStock:0.#} доз" : "";
                case PharmacyGoods.BodyBag: return capture != null && capture.Disposal != null ? "мешков " + capture.Disposal.Stock : "";
                case PharmacyGoods.TableSupply:
                {
                    OperationWorldState w = SupplyTable();
                    if (w == null) return "на стол команды";
                    return "на столе " + (offer.CatalogId == OperationSupplies.SutureKitId ? w.sutureKits : w.patches);
                }
                case PharmacyGoods.TeamSupply:
                {
                    var state = TeamEconomy.Instance != null ? TeamEconomy.Instance.ServerState : null;
                    return state != null ? "куплено " + PharmacyRules.Bought(state, offer.CatalogId) + " · пока без применения" : "пока без применения";
                }
                default:
                {
                    InventoryModel inv = kit != null && kit.Inventory != null ? kit.Inventory.Model : null;
                    return inv != null ? (inv.CountThatFits(SyringeDefinition(offer.Goods), 1, 0) > 0 ? "есть место в хотбаре" : "хотбар полон") : "";
                }
            }
        }

        // ================================================================== UI

        private void Styles()
        {
            if (label != null) return;
            label = new GUIStyle(GUI.skin.label) { fontSize = 18, richText = true, alignment = TextAnchor.MiddleLeft };
            label.normal.textColor = new Color(0.95f, 0.93f, 0.86f);
            small = new GUIStyle(label) { fontSize = 14 };
            small.normal.textColor = new Color(0.75f, 0.8f, 0.78f);
            title = new GUIStyle(label) { fontSize = 22, fontStyle = FontStyle.Bold };
            title.normal.textColor = new Color(0.55f, 0.9f, 0.62f);
            button = new GUIStyle(GUI.skin.button) { fontSize = 16, fontStyle = FontStyle.Bold };
            row = new GUIStyle(GUI.skin.box);
        }

        private void OnGUI()
        {
            Styles();
            if (!open)
            {
                if (prompt.Length == 0) return;
                var p = new Rect(Screen.width * 0.1f, Screen.height * 0.66f, Screen.width * 0.8f, 40f);
                var s = new GUIStyle(label) { alignment = TextAnchor.MiddleCenter, fontSize = 19 };
                s.normal.textColor = new Color(0f, 0f, 0f, 0.85f);
                GUI.Label(new Rect(p.x + 2f, p.y + 2f, p.width, p.height), "E — касса аптеки (список товаров)", s);
                s.normal.textColor = new Color(1f, 0.93f, 0.75f);
                GUI.Label(p, prompt, s);
                return;
            }
            float w = Mathf.Min(760f, Screen.width - 40f), h = Mathf.Min(620f, Screen.height - 40f);
            var r = new Rect((Screen.width - w) * 0.5f, (Screen.height - h) * 0.5f, w, h);
            GUI.color = new Color(0.08f, 0.11f, 0.1f, 0.94f);
            GUI.DrawTexture(r, Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUILayout.BeginArea(new Rect(r.x + 18f, r.y + 12f, r.width - 36f, r.height - 24f));
            GUILayout.Label("+  PHARMACY — counter", title);
            int balance = EconomyClientView.Balance;
            bool ready = EconomyClientView.Current != null && EconomyClientView.Current.ready;
            GUILayout.Label(ready ? "Общие деньги команды: <b>" + EconomyState.Money(balance) + "</b>" : "Экономика ещё загружается…", label);
            if (!EconomyPrices.Bound) GUILayout.Label("<color=#FF8A5B>" + EconomyPrices.NotLoadedReason + "</color>", label);
            bool shopOpen = PharmacyNetV01.OpenNow;
            if (!shopOpen) GUILayout.Label("<color=#FF8A5B><b>" + PharmacyHours.ClosedText + "</b> — " + PharmacyHours.SignText + "</color>", label);
            GUILayout.Space(6f);
            scroll = GUILayout.BeginScrollView(scroll);
            for (int i = 0; i < PharmacyRules.Offers.Count; i++)
            {
                PharmacyOffer o = PharmacyRules.Offers[i];
                int price = o.Price;
                GUILayout.BeginHorizontal(row);
                string mark = i == selected ? "<color=#8CF0A0>▶</color> " : "   ";
                GUILayout.Label(mark + "<b>" + o.Title + "</b>  —  <b>" + PharmacyRules.Money(price) + "</b> " + o.Unit, label, GUILayout.Width(w - 300f));
                GUILayout.Label(Holding(o), small, GUILayout.Width(170f));
                GUI.enabled = !busy && price > 0 && ready && shopOpen;
                if (GUILayout.Button("Buy", button, GUILayout.Width(70f), GUILayout.Height(30f))) { selected = i; Buy(o); }
                GUI.enabled = true;
                GUILayout.EndHorizontal();
            }
            GUILayout.EndScrollView();
            GUILayout.Space(4f);
            if (Time.unscaledTime < statusUntil)
                GUILayout.Label("<color=" + (statusOk ? "#5BE07A" : "#FF8A5B") + ">" + status + "</color>", label);
            GUILayout.Label("Мышь — Buy · ↑/↓ и Enter — купить выбранное · E / Esc — отойти от кассы. Покупка — одна штука (стяжки — ещё и упаковкой по 4).", small);
            GUILayout.EndArea();
        }
    }
}
