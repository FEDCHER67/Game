using System.Globalization;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// The V2 base workshop's arrival and service (Fedya 31.10, plan P1 "Workshop arrival"), on top of the existing ONE
    /// server-owned lift session (WorkshopServiceV01: lift, van held kinematic, nobody pushed, owner leash / disconnect
    /// lowers, the mechanic's performance commits at the Poof with the puff) and mechanic B (WorkshopMechanicV01 body +
    /// WorkshopMechanicBrainV01 route; its v1 E conversation is off here):
    /// 1. the team van with a driver, in the dock zone, lined up with the lift and at most 0.5 m/s for 0.5 s (DockTrackerV2)
    ///    docks once per visit: throttle off, handbrake on;
    /// 2. the driver steps out at a free spot beside the bay (<see cref="ExitSpots"/>, clear of the van, the arms and the
    ///    posts: GreyboxVanSeat.ExitTo), a player riding in the bay likewise;
    /// 3. the lift session starts for that player (retried while the van settles; a refusal is said, never forced);
    /// 4. raised: the mechanic greets in a world-space bubble ("Что будем улучшать сегодня?") and the upgrade menu opens:
    ///    the engine group only (price, current and next tier, the effect in km/h and pull), "Купить" = the mechanic
    ///    performs it (puff, one charge), "Готово" / Esc lowers the van and releases it; get in and drive out.
    /// Nothing lifts a moving van or one with someone under it (the session's own checks). Host / solo only in P1 (V2
    /// clients cannot enter gameplay yet; the van is not a network object).
    /// </summary>
    [DefaultExecutionOrder(-20)]
    public sealed class WorkshopDockV2 : MonoBehaviour
    {
        public static WorkshopDockV2 Instance { get; private set; }

        public WorkshopServiceV01 Service;
        public WorkshopMechanicV01 Mechanic;
        public SpeechBubbleV2 Bubble;
        [Tooltip("Where the occupants step out (feet; forward = where they face). The first free one is used.")]
        public Transform[] ExitSpots = new Transform[0];
        public string Greeting = "Что будем улучшать сегодня?";
        public float MaxSpeed = DockTrackerV2.DefaultMaxSpeed;
        public float StableSeconds = DockTrackerV2.DefaultStableSeconds;
        [Tooltip("Seconds the lift start is retried after the dock (the van settles on its handbrake).")]
        public float StartTimeout = 6f;

        public enum Stage : byte { Idle, Starting, Raising, Menu, Lowering }

        private DockTrackerV2 tracker;
        private VanController van;
        private float nextVanSearch, nextStart, startDeadline, hintUntil;
        private string lastRefusal = "";
        private bool menuOpen, busy, savedMove, savedLook, savedVisible;
        private CursorLockMode savedLock;
        private KccFirstPersonInput walker;
        private string status = "";
        private bool statusOk;
        private float statusUntil;
        private GUIStyle label, title, small, button;

        public Stage Current { get; private set; }
        public int Docks { get; private set; }
        public string LastSignalNote { get; private set; } = "";
        /// <summary>The last dock measurement (tests and the log).</summary>
        public string Probe { get; private set; } = "";
        public bool MenuOpen => menuOpen;
        public string LastStatus => status;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Instance = null;

        private void OnEnable()
        {
            Instance = this;
            tracker = new DockTrackerV2(MaxSpeed, StableSeconds);
        }

        private void OnDisable()
        {
            CloseMenu(false);
            if (Instance == this) Instance = null;
        }

        private VanController FindVan()
        {
            if (van == null && Time.unscaledTime >= nextVanSearch)
            {
                van = FindAnyObjectByType<VanController>();
                nextVanSearch = Time.unscaledTime + 2f;
            }
            return van;
        }

        // ================================================================== per frame

        private void Update()
        {
            if (Service == null) return;
            LiftSession s = Service.Session;
            if (WorkshopServiceV01.Authority) ServerTick(s);
            // the menu belongs to the session owner on this machine
            if (Current == Stage.Raising && s.Phase == LiftPhase.Up && Service.MineSession) Raised();
            if (menuOpen && !Service.MineSession && !busy) { CloseMenu(false); Current = s.HoldsVan ? Stage.Lowering : Stage.Idle; }
            if (Current == Stage.Lowering && !s.HoldsVan)
            {
                Current = Stage.Idle;
                Toast(true, "Готово: бусик опущен — садись и выезжай");
            }
            if (menuOpen) MenuKeys();
        }

        private void ServerTick(LiftSession s)
        {
            VanController v = FindVan();
            if (v == null) return;
            var body = v.GetComponent<Rigidbody>();
            var seat = v.GetComponent<GreyboxVanSeat>();
            Vector3 centre = body != null ? body.worldCenterOfMass : v.transform.position;
            bool inZone = Service.Zone != null ? Service.Zone.Contains(centre) : false;
            if (s.Active || s.HoldsVan)
            {
                tracker.Step(inZone, false, 99f, false, Time.deltaTime); // keeps it disarmed until the van leaves the zone
                tracker.Disarm();
                if (Current == Stage.Starting) Current = s.Phase == LiftPhase.Up ? Stage.Raising : Stage.Raising;
                return;
            }
            if (Current == Stage.Raising || Current == Stage.Menu) { CloseMenu(false); Current = Stage.Idle; }
            if (Current == Stage.Starting) { TryStart(); return; }
            Vector3 vel = body != null ? body.linearVelocity : Vector3.zero;
            vel.y = 0f;
            Transform park = Service.VanPark != null ? Service.VanPark : Service.transform;
            Vector3 local = park.InverseTransformPoint(v.transform.position);
            float yaw = Mathf.DeltaAngle(park.eulerAngles.y, v.transform.eulerAngles.y);
            Vector3 tol = Service.PadTolerance;
            bool aligned = DockTrackerV2.Aligned(local.x, local.z, yaw, tol.x, tol.y, tol.z);
            bool driver = seat != null && seat.Driving;
            DockSignal sig = tracker.Step(inZone, aligned, vel.magnitude, driver, Time.deltaTime);
            Probe = $"zone {inZone} (centre {Service.Zone.transform.InverseTransformPoint(centre).z:+0.00;-0.00} along), aligned {aligned} (root across {local.x:+0.00;-0.00}, along {local.z:+0.00;-0.00}, yaw {yaw:+0;-0}), " +
                    $"speed {vel.magnitude:0.00} m/s, driver {driver}, armed {tracker.Armed}, stable {tracker.Stable:0.00} s -> {sig}";
            if (sig == DockSignal.NeedsAlign && Time.unscaledTime >= hintUntil)
            {
                hintUntil = Time.unscaledTime + 4f;
                LastSignalNote = $"not aligned: across {local.x:0.00} m, along {local.z:0.00} m, yaw {yaw:0} deg";
                Toast(false, "Механик: «Ровнее! Заезжай прямо между стойками подъёмника»");
                Debug.Log("[BASEV2] dock: in the zone and slow but " + LastSignalNote, this);
            }
            if (sig == DockSignal.Dock) Dock(v, seat, vel.magnitude, local, yaw);
        }

        /// <summary>Docked: stop, everyone out at a free spot, then ask for the lift.</summary>
        private void Dock(VanController v, GreyboxVanSeat seat, float speed, Vector3 local, float yaw)
        {
            Docks++;
            v.Throttle = 0f;
            v.Handbrake = true;
            Transform spot = FreeSpot();
            float faceYaw = spot != null ? Quaternion.LookRotation(Flat(v.transform.position - spot.position)).eulerAngles.y : 0f;
            bool driverOut = spot != null && seat != null && seat.ExitTo(spot.position, faceYaw);
            // a player riding in the bay steps out too (the host's own body; remote riders: P1 is host-only)
            var capture = CaptureDirector.Instance;
            if (spot != null && capture != null && capture.Pawn != null && !driverOut &&
                capture.Pawn.Body.TryGetComponent(out GreyboxCargoRider rider) && rider.Inside)
                capture.Pawn.Teleport(spot.position, faceYaw);
            Debug.Log($"[BASEV2] dock #{Docks}: van {v.name} at {speed:0.00} m/s, off the lift centre {local.x:+0.00;-0.00} m across, {local.z:+0.00;-0.00} m along, yaw {yaw:+0;-0}; " +
                      $"driver out {(driverOut ? "at " + spot.name : "no")}; asking for the lift", this);
            Current = Stage.Starting;
            nextStart = Time.unscaledTime + 0.4f;
            startDeadline = Time.unscaledTime + StartTimeout;
            lastRefusal = "";
        }

        private Transform FreeSpot()
        {
            Transform first = null;
            foreach (Transform t in ExitSpots)
            {
                if (t == null) continue;
                first ??= t;
                Vector3 p = t.position;
                int mask = ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.Player) | (1 << OvLayers.RemotePlayer));
                if (!Physics.CheckCapsule(p + Vector3.up * 0.55f, p + Vector3.up * 1.45f, 0.4f, mask, QueryTriggerInteraction.Ignore)) return t;
            }
            return first;
        }

        private void TryStart()
        {
            if (Time.unscaledTime < nextStart) return;
            nextStart = Time.unscaledTime + 0.3f;
            Service.Request(WorkshopRequestKind.Start, "", 0, (ok, text) =>
            {
                if (ok) { Current = Stage.Raising; Debug.Log("[BASEV2] dock: the lift session started — " + text, this); return; }
                lastRefusal = text;
                if (Time.unscaledTime < startDeadline) return;
                Current = Stage.Idle;
                Toast(false, "Механик не поднял бусик: " + text);
                Debug.Log("[BASEV2] dock: the lift did not start in " + StartTimeout + " s: " + text, this);
            });
        }

        private void Raised()
        {
            Current = Stage.Menu;
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            Transform speaker = brain != null && brain.HasBody ? brain.Body : Service.ControlPoint;
            // beside his head on the side away from the lift (the post he stands at would hide half of it)
            Vector3 away = speaker != null && Service.VanPark != null ? Flat(speaker.position - Service.VanPark.position).normalized * 0.75f : Vector3.zero;
            if (Bubble != null) Bubble.Say(Greeting, speaker, 6f, away);
            Debug.Log($"[BASEV2] the van is up ({Service.Height:0.00} m): the mechanic says «{Greeting}», menu open", this);
            OpenMenu();
        }

        // ================================================================== menu

        private void OpenMenu()
        {
            if (menuOpen) return;
            menuOpen = true;
            busy = false;
            Service.Request(WorkshopRequestKind.Talk, "1", 0, null);
            var capture = CaptureDirector.Instance;
            walker = capture != null && capture.Pawn != null
                ? capture.Pawn.GetComponentInParent<KccFirstPersonInput>() ?? capture.Pawn.GetComponentInChildren<KccFirstPersonInput>() : null;
            if (walker != null) { savedMove = walker.MovementLocked; savedLook = walker.LookSuspended; walker.MovementLocked = true; walker.LookSuspended = true; }
            savedLock = Cursor.lockState; savedVisible = Cursor.visible;
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            OnlyVolunteers.UI.OvMenuGate.Blocking = true;
        }

        private void CloseMenu(bool lower)
        {
            if (!menuOpen) return;
            menuOpen = false;
            if (lower && Service != null && Service.MineSession)
            {
                Current = Stage.Lowering;
                Service.Request(WorkshopRequestKind.Done, "", 0, (ok, text) => { if (!ok && !string.IsNullOrEmpty(text)) Toast(false, text); });
            }
            Service?.Request(WorkshopRequestKind.Talk, "0", 0, null);
            if (walker != null) { walker.MovementLocked = savedMove; walker.LookSuspended = savedLook; walker = null; }
            Cursor.lockState = savedLock; Cursor.visible = savedVisible;
            OnlyVolunteers.UI.OvMenuGate.Blocking = false;
        }

        private void MenuKeys()
        {
            Keyboard k = Keyboard.current;
            if (k == null || busy) return;
            if (k.escapeKey.wasPressedThisFrame) { OnlyVolunteers.UI.OvMenuGate.ConsumeEscape(); CloseMenu(true); return; }
            if (k.digit1Key.wasPressedThisFrame || k.enterKey.wasPressedThisFrame) BuyEngine();
            else if (k.digit2Key.wasPressedThisFrame) CloseMenu(true);
        }

        /// <summary>The engine row as the menu shows it (any machine; prices from the catalogue, tiers from the fund state).</summary>
        public struct EngineRow
        {
            public int Tier, Next, Price, Balance;
            public bool AtMax, Affordable;
            public string Now, Then;
        }

        public EngineRow Row()
        {
            var r = new EngineRow();
            TeamEconomy e = TeamEconomy.Instance;
            EconomySnapshot snap = EconomyClientView.Current;
            r.Tier = e != null && e.ServerReady ? e.ServerState.VanTier(VanBranch.Engine) : snap != null ? snap.VanTier(VanBranch.Engine) : 0;
            r.Balance = BaseV2DirectorV01.Balance;
            r.AtMax = r.Tier >= EconomyPrices.VanMaxTier;
            r.Next = r.Tier + 1;
            r.Price = r.AtMax ? 0 : EconomyPrices.VanTierPrice(VanBranch.Engine, r.Next);
            r.Affordable = !r.AtMax && r.Price > 0 && r.Balance >= r.Price;
            VanController v = FindVan();
            VanUpgradeConfig config = v != null && v.TryGetComponent(out VanUpgrades up) ? up.Config : null;
            r.Now = VanUpgradeConfig.DescribeProgression(config, VanUpgradeCategory.Engine, r.Tier);
            r.Then = r.AtMax ? "" : VanUpgradeConfig.DescribeProgression(config, VanUpgradeCategory.Engine, r.Next);
            return r;
        }

        /// <summary>"Купить": the mechanic performs the next engine tier (validated now, committed once at his Poof).</summary>
        public bool BuyEngine()
        {
            if (busy || !menuOpen && !scriptMenu) return false;
            EngineRow r = Row();
            if (r.AtMax) { Show(false, "Двигатель уже на ступени III"); return false; }
            if (Service.Phase != LiftPhase.Up) { Show(false, WorkshopRules.Explain(WorkshopRefusal.NotRaised)); return false; }
            busy = true;
            Show(true, "Механик прицеливается ключом…");
            Service.Request(WorkshopRequestKind.Buy, WorkshopUpgradeRows.VanBranchKind + "|" + ((int)VanBranch.Engine).ToString(CultureInfo.InvariantCulture), r.Next,
                (ok, text) => { busy = false; Show(ok, text); });
            return true;
        }

        private bool scriptMenu;

        /// <summary>Test hooks: the menu's buttons without the mouse.</summary>
        public bool ScriptBuyEngine() { scriptMenu = true; try { return BuyEngine(); } finally { scriptMenu = false; } }
        public void ScriptDone() { if (menuOpen) CloseMenu(true); else if (Service.MineSession) { Current = Stage.Lowering; Service.Request(WorkshopRequestKind.Done, "", 0, null); } }
        public bool Busy => busy;

        private void Show(bool ok, string text)
        {
            status = text ?? "";
            statusOk = ok;
            statusUntil = Time.unscaledTime + 6f;
            Toast(ok, status);
        }

        private static void Toast(bool ok, string text)
        {
            if (string.IsNullOrEmpty(text)) return;
            CaptureDirector.Instance?.Toast(text, ok ? CaptureHud.Good : CaptureHud.Warn, 4f);
        }

        private static Vector3 Flat(Vector3 v)
        {
            v.y = 0f;
            return v.sqrMagnitude > 1e-6f ? v : Vector3.forward;
        }

        private void Styles()
        {
            if (label != null) return;
            label = new GUIStyle(GUI.skin.label) { fontSize = 18, richText = true, wordWrap = true };
            label.normal.textColor = new Color(0.95f, 0.93f, 0.86f);
            small = new GUIStyle(label) { fontSize = 14 };
            small.normal.textColor = new Color(0.78f, 0.8f, 0.76f);
            title = new GUIStyle(label) { fontSize = 22, fontStyle = FontStyle.Bold, wordWrap = false };
            title.normal.textColor = new Color(1f, 0.78f, 0.35f);
            button = new GUIStyle(GUI.skin.button) { fontSize = 17, fontStyle = FontStyle.Bold, richText = true };
        }

        private void OnGUI()
        {
            if (!menuOpen) return;
            Styles();
            float w = Mathf.Min(720f, Screen.width - 40f), h = Mathf.Min(400f, Screen.height - 40f);
            // right half of the screen: the raised van and the mechanic stay visible on the left
            var r = new Rect(Screen.width - w - 30f, (Screen.height - h) * 0.5f, w, h);
            GUI.color = new Color(0.1f, 0.09f, 0.07f, 0.93f);
            GUI.DrawTexture(r, Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUILayout.BeginArea(new Rect(r.x + 18f, r.y + 12f, r.width - 36f, r.height - 24f));
            EngineRow row = Row();
            string phase = Service.Phase == LiftPhase.Up ? "<color=#5BE07A>поднят</color>" : Service.Phase == LiftPhase.Raising ? "поднимается…" : Service.Phase == LiftPhase.Lowering ? "опускается…" : "внизу";
            GUILayout.Label("МАСТЕРСКАЯ — бусик на подъёмнике", title);
            GUILayout.Label("Подъёмник: " + phase + " · общий фонд <b>" + EconomyState.Money(row.Balance) + "</b>", label);
            GUILayout.Space(6f);
            GUILayout.Label("<b>Двигатель</b> (скорость и тяга)", label);
            GUILayout.Label("Сейчас: ступень " + EconomyPrices.TierName(row.Tier) + " — " + row.Now, label);
            if (row.AtMax) GUILayout.Label("<color=#5BE07A>Ступень III — максимум</color>", label);
            else
            {
                GUILayout.Label("После: ступень " + EconomyPrices.TierName(row.Next) + " — " + row.Then, label);
                string lack = row.Affordable ? "" : " <color=#FF6A50>(не хватает " + EconomyState.Money(Mathf.Max(0, row.Price - row.Balance)) + ")</color>";
                GUILayout.Label("Цена: <b>" + EconomyState.Money(row.Price) + "</b> (" + GearCatalogV2.PlaceholderPrice + ")" + lack, label);
            }
            GUILayout.Space(8f);
            GUILayout.BeginHorizontal();
            GUI.enabled = !busy && !row.AtMax && Service.Phase == LiftPhase.Up;
            if (GUILayout.Button(row.AtMax ? "Максимум" : "1 · Купить ступень " + EconomyPrices.TierName(row.Next), button, GUILayout.Height(40f))) BuyEngine();
            GUI.enabled = !busy;
            if (GUILayout.Button("2 · Готово — опустить бусик", button, GUILayout.Height(40f))) CloseMenu(true);
            GUI.enabled = true;
            GUILayout.EndHorizontal();
            if (Time.unscaledTime < statusUntil && status.Length > 0)
                GUILayout.Label("<color=" + (statusOk ? "#5BE07A" : "#FF8A5B") + ">" + status + "</color>", label);
            GUILayout.Label("Тормоза и управление — позже. Esc или 2 — опустить бусик и уйти.", small);
            GUILayout.EndArea();
        }
    }
}
