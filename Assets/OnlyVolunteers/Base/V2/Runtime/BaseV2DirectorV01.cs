using System;
using System.Collections.Generic;
using FishNet;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Economy;
using UnityEngine;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>Client -> server: buy one V2 shop item (the display the buyer aims at); Expected = the price shown.</summary>
    public struct GearRequestBroadcast : IBroadcast
    {
        public string Key;
        public string ItemId;
        public int Expected;
    }

    public struct GearResultBroadcast : IBroadcast
    {
        public string Key;
        public bool Ok;
        public string Message;
    }

    /// <summary>
    /// The V2 base (hangar) services of P1 (Fedya 31.10), one per base scene (placed by BaseV2BuilderV01):
    /// - the workshop is open from the start in V2 (BaseV2Rules.OpenWorkshop on the server once the team fund is ready;
    ///   the v1 map keeps its M06 gate: this component is only in V2 base scenes);
    /// - the shop's purchase channel: FishNet broadcasts like TeamEconomy / WorkshopServiceV01 (no NetworkObject; the solo
    ///   host runs the same path). A client sends an intent (item id + the price it showed, never an amount); the server
    ///   measures the buyer at the display itself (reach + a clear line of sight) and commits through
    ///   EconomyState.TryBuyGear: one request = at most one charge (deterministic key gear:&lt;id&gt;), a refusal charges
    ///   nothing; the team save is written by the existing economy commit (TeamEconomy.ServerCommitted);
    /// - who owns what (server state on the host, the snapshot on a client);
    /// - the baton component on the local Capture V2 hands (it checks ownership itself);
    /// - P1 test money (host only, F8): +$1 000 with a ledger line saying so, because V2 has no mission income yet.
    /// Host / solo only in practice: V2 clients cannot enter gameplay yet (V2 menu), so client paths are untested.
    /// </summary>
    [DefaultExecutionOrder(-120)]
    public sealed class BaseV2DirectorV01 : MonoBehaviour
    {
        public static BaseV2DirectorV01 Instance { get; private set; }

        [Tooltip("F8 gives the team +$1 000 test money (host). V2 has no mission income yet; remove with the mission payouts.")]
        public bool TestCashKey = true;
        public int TestCashAmount = 1000;
        [Tooltip("The held baton (BaseV2BuilderV01 makes the mesh and material).")]
        public Mesh BatonMesh;
        public Material BatonMaterial;

        private NetworkManager manager;
        private bool bound;
        private EconomyState openedFor;
        private readonly Dictionary<string, Action<bool, string>> pending = new Dictionary<string, Action<bool, string>>();
        private readonly RaycastHit[] sight = new RaycastHit[16];
        private CaptureV2BatonV01 baton;
        private float nextHandsLook;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Instance = null;

        private void OnEnable() => Instance = this;

        private void OnDisable()
        {
            Unbind();
            if (Instance == this) Instance = null;
        }

        public static bool Authority
        {
            get
            {
                NetworkManager nm = InstanceFinder.NetworkManager;
                return nm == null || nm.IsServerStarted || !nm.IsClientStarted;
            }
        }

        /// <summary>The team owns this V2 item (host: the server state; client: the last snapshot).</summary>
        public static bool TeamOwns(string itemId)
        {
            TeamEconomy e = TeamEconomy.Instance;
            if (e != null && e.ServerReady) return e.ServerState.OwnsGear(itemId);
            EconomySnapshot s = EconomyClientView.Current;
            return s != null && s.ready && s.OwnsGear(itemId);
        }

        public static bool EconomyReady
        {
            get
            {
                TeamEconomy e = TeamEconomy.Instance;
                if (e != null && e.ServerReady) return true;
                EconomySnapshot s = EconomyClientView.Current;
                return s != null && s.ready;
            }
        }

        public static int Balance
        {
            get
            {
                TeamEconomy e = TeamEconomy.Instance;
                if (e != null && e.ServerReady) return e.ServerState.Fund.Balance;
                return EconomyClientView.Balance;
            }
        }

        // ================================================================== binding

        private void Bind()
        {
            NetworkManager nm = InstanceFinder.NetworkManager;
            if (nm == null || bound && nm == manager) return;
            Unbind();
            manager = nm;
            manager.ServerManager.RegisterBroadcast<GearRequestBroadcast>(OnServerRequest);
            manager.ClientManager.RegisterBroadcast<GearResultBroadcast>(OnClientResult);
            bound = true;
        }

        private void Unbind()
        {
            if (!bound || manager == null) { bound = false; return; }
            manager.ServerManager.UnregisterBroadcast<GearRequestBroadcast>(OnServerRequest);
            manager.ClientManager.UnregisterBroadcast<GearResultBroadcast>(OnClientResult);
            bound = false;
        }

        // ================================================================== per frame

        private void Update()
        {
            Bind();
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy != null && economy.ServerReady && openedFor != economy.ServerState)
            {
                openedFor = economy.ServerState;
                bool opened = BaseV2Rules.OpenWorkshop(openedFor);
                Debug.Log($"[BASEV2] V2 base: workshop {(opened ? "opened (no M06 gate in V2)" : "already open")}; fund ${openedFor.Fund.Balance}, engine tier {openedFor.VanTier(VanBranch.Engine)}, " +
                          $"gear owned: {(openedFor.OwnsGear(GearCatalogV2.Baton) ? GearCatalogV2.Baton : "none")}", this);
            }
            InstallBaton();
            if (TestCashKey && economy != null && economy.ServerReady && !OnlyVolunteers.UI.OvMenuGate.Blocking)
            {
                UnityEngine.InputSystem.Keyboard k = UnityEngine.InputSystem.Keyboard.current;
                if (k != null && k.f8Key.wasPressedThisFrame) GiveTestCash();
            }
        }

        /// <summary>Host: P1 test money (V2 has no mission income yet). A ledger line names it as test money.</summary>
        public bool GiveTestCash()
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.ServerReady) return false;
            FundResult r = economy.ServerCredit(TestCashAmount, "test", "Тест P1: +" + EconomyState.Money(TestCashAmount) + " (временно, пока нет денег за миссии)", "test:p1cash:" + Guid.NewGuid().ToString("N"));
            Debug.Log($"[BASEV2] F8 test money: {(r.Ok ? "+" + TestCashAmount : "refused " + r.Status)}; fund ${economy.ServerState.Fund.Balance}", this);
            CaptureDirector.Instance?.Toast("Тестовые деньги P1: +" + EconomyState.Money(TestCashAmount) + " (фонд " + EconomyState.Money(economy.ServerState.Fund.Balance) + ")", CaptureHud.Good, 3f);
            return r.Ok;
        }

        private void InstallBaton()
        {
            if (baton != null || Time.unscaledTime < nextHandsLook) return;
            nextHandsLook = Time.unscaledTime + 1f;
            var hands = OnlyVolunteers.Capture.V2.CaptureV2Rig.Instance != null ? OnlyVolunteers.Capture.V2.CaptureV2Rig.Instance.Hands : null;
            if (hands == null) return;
            if (!hands.TryGetComponent(out baton)) baton = hands.gameObject.AddComponent<CaptureV2BatonV01>();
            baton.Director = this;
            Debug.Log($"[BASEV2] baton ready on {hands.name} (X draws it once the team owns it)", this);
        }

        // ================================================================== purchase (any machine)

        /// <summary>Asks the server to buy itemId at the price this machine shows. done(ok, text) runs here with the answer
        /// (at once on the host). One call = one request.</summary>
        public void RequestBuy(string itemId, int expectedPrice, Action<bool, string> done)
        {
            Bind();
            string key = Guid.NewGuid().ToString("N");
            var m = new GearRequestBroadcast { Key = key, ItemId = itemId ?? "", Expected = expectedPrice };
            if (Authority)
            {
                (bool ok, string text) = Process(m, manager != null ? manager.ClientManager.Connection : null);
                done?.Invoke(ok, text);
            }
            else if (manager != null && manager.IsClientStarted)
            {
                if (done != null) pending[key] = done;
                manager.ClientManager.Broadcast(m);
            }
            else done?.Invoke(false, "Нет связи с хостом");
        }

        private void OnServerRequest(NetworkConnection c, GearRequestBroadcast m, Channel channel)
        {
            if (c == null || !c.IsActive) return;
            (bool ok, string text) = Process(m, c);
            manager.ServerManager.Broadcast(c, new GearResultBroadcast { Key = m.Key, Ok = ok, Message = text });
        }

        private void OnClientResult(GearResultBroadcast r, Channel channel)
        {
            if (Authority) return;
            if (r.Key != null && pending.TryGetValue(r.Key, out Action<bool, string> done))
            {
                pending.Remove(r.Key);
                try { done(r.Ok, r.Message); } catch (Exception e) { Debug.LogException(e, this); }
            }
        }

        private (bool, string) Process(GearRequestBroadcast m, NetworkConnection from)
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) return (false, "Экономика не запущена");
            if (!economy.ServerReady) return (false, PurchaseResult.Explain(PurchaseError.NotReady));
            if (string.IsNullOrEmpty(m.Key) || m.Key.Length > 64 || m.ItemId == null || m.ItemId.Length > 64) return (false, "Неверный запрос");
            ShopDisplayItemV2 display = ShopDisplayItemV2.Find(m.ItemId);
            GearShopCheck check = display != null ? Measure(display, from) : default;
            PurchaseResult r = economy.ServerState.TryBuyGear(m.ItemId, m.Expected, check);
            Debug.Log($"[BASEV2] shop: {economy.ServerParticipantId(from)} buys {m.ItemId} (${m.Expected}): " +
                      $"{(r.Ok ? "PAID $" + r.Price : "refused " + r.Error + " (" + r.Message + ")")} (reach {check.InReach}, sight {check.SightClear}); fund ${economy.ServerState.Fund.Balance}", this);
            return (r.Ok, r.Message);
        }

        /// <summary>The server's own measurement: the buyer's feet within the display's reach and a clear line from about
        /// eye height to the item (the display's own colliders and players aside).</summary>
        private GearShopCheck Measure(ShopDisplayItemV2 display, NetworkConnection from)
        {
            Vector3? at = TeamEconomy.ServerActorPosition(from);
            if (!at.HasValue) return default;
            Vector3 feet = at.Value;
            // the host's ServerActorPosition is the pawn's feet (the camera only without a pawn)
            bool cameraPoint = CaptureDirector.Instance == null || CaptureDirector.Instance.Pawn == null;
            Vector3 eye = cameraPoint ? feet : feet + Vector3.up * 1.6f;
            Vector3 item = display.AimPoint;
            Vector3 flat = item - feet;
            flat.y = 0f;
            var check = new GearShopCheck { InReach = flat.magnitude <= display.Reach + 0.4f };
            Vector3 d = item - eye;
            float len = d.magnitude;
            check.SightClear = true;
            if (len > 0.05f)
            {
                int n = Physics.RaycastNonAlloc(eye, d / len, sight, len, OnlyVolunteers.Map.OvLayers.ShootMask & ~(1 << OnlyVolunteers.Map.OvLayers.RemotePlayer), QueryTriggerInteraction.Ignore);
                for (int i = 0; i < n; i++)
                {
                    Collider c = sight[i].collider;
                    if (c == null || display.Owns(c)) continue;
                    if (sight[i].distance > len - 0.15f) continue;
                    check.SightClear = false;
                    break;
                }
            }
            return check;
        }
    }
}
