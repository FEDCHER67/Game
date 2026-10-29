using System.Collections.Generic;
using System.Globalization;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// The workshop's repair zone (ECONOMY spec §6.3): a van whose centre of mass is inside this box, standing on the
    /// handbrake, can buy paid tiers (the server re-checks at the commit: TeamEconomy.MeasureVan). The box is this
    /// transform's frame: Size wide / long, from 1 m below to Size.y above the transform. The workshop is a service on the
    /// construction site (Стройка): the play scene Map_W85_Play_v02 has one under W86_Workshop_Anchors (middle bay apron of
    /// 03-01-workshop; W85PlayIntegrator.PlaceWorkshopZoneInOpenScene, also step 8b of a full Make); in editor / dev builds the
    /// phone's DEV tab can still put a provisional zone around the van. Paid tiers open with M06 (WorkshopUnlocked).
    /// </summary>
    public sealed class WorkshopZone : MonoBehaviour
    {
        public static readonly List<WorkshopZone> All = new List<WorkshopZone>();

        public Vector3 Size = new Vector3(7f, 4f, 9f);
        [Tooltip("The workshop lift serves this zone: tiers are bought only on the lift, through the mechanic (WorkshopServiceV01); the old U / Enter panel shows a hint.")]
        public bool LiftOnly;
        public string Title = "Мастерская — ремонтная зона";
        [Tooltip("Build yellow corner posts and a floating title at runtime.")]
        public bool ShowMarkers = true;

        private static WorkshopZone devZone;
        private bool markersBuilt;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            All.Clear();
            devZone = null;
        }

        private void OnEnable() { if (!All.Contains(this)) All.Add(this); }
        private void OnDisable() => All.Remove(this);

        private void Start()
        {
            if (ShowMarkers && !markersBuilt) BuildMarkers();
        }

        public bool Contains(Vector3 world)
        {
            Vector3 p = transform.InverseTransformPoint(world);
            return Mathf.Abs(p.x) <= Size.x * 0.5f && Mathf.Abs(p.z) <= Size.z * 0.5f && p.y >= -1f && p.y <= Size.y;
        }

        public static WorkshopZone Containing(Vector3 world)
        {
            foreach (WorkshopZone z in All)
                if (z != null && z.isActiveAndEnabled && z.Contains(world)) return z;
            return null;
        }

        public static WorkshopZone Nearest(Vector3 world, float maxDistance)
        {
            WorkshopZone best = null;
            float bestD = maxDistance * maxDistance;
            foreach (WorkshopZone z in All)
            {
                if (z == null || !z.isActiveAndEnabled) continue;
                float d = (z.transform.position - world).sqrMagnitude;
                if (d <= bestD) { bestD = d; best = z; }
            }
            return best;
        }

        /// <summary>Dev aid: (re)places the provisional zone centred on this point (the van). Not saved.</summary>
        public static WorkshopZone PlaceDev(Vector3 position, float yaw)
        {
            if (devZone == null)
            {
                var go = new GameObject("[Economy] Workshop zone (DEV, provisional)");
                devZone = go.AddComponent<WorkshopZone>();
                devZone.Title = "Мастерская (DEV-зона)";
            }
            devZone.transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            devZone.BuildMarkers();
            return devZone;
        }

        private void BuildMarkers()
        {
            markersBuilt = true;
            Transform old = transform.Find("Markers");
            if (old != null) Destroy(old.gameObject);
            var root = new GameObject("Markers").transform;
            root.SetParent(transform, false);
            var block = new MaterialPropertyBlock();
            block.SetColor("_BaseColor", new Color(1f, 0.78f, 0.1f));
            block.SetColor("_Color", new Color(1f, 0.78f, 0.1f));
            for (int i = 0; i < 4; i++)
            {
                float x = (i % 2 == 0 ? -0.5f : 0.5f) * Size.x, z = (i < 2 ? -0.5f : 0.5f) * Size.z;
                Vector3 top = transform.TransformPoint(new Vector3(x, 3f, z));
                float groundY = Physics.Raycast(top, Vector3.down, out RaycastHit hit, 8f, ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.Vehicle) | (1 << OvLayers.Player)), QueryTriggerInteraction.Ignore)
                    ? hit.point.y : transform.position.y;
                GameObject post = GameObject.CreatePrimitive(PrimitiveType.Cube);
                post.name = "Post" + i;
                Destroy(post.GetComponent<Collider>());
                post.transform.SetParent(root, true);
                post.transform.position = new Vector3(top.x, groundY + 0.6f, top.z);
                post.transform.rotation = transform.rotation;
                post.transform.localScale = new Vector3(0.14f, 1.2f, 0.14f);
                if (post.TryGetComponent(out Renderer r)) r.SetPropertyBlock(block);
            }
            EconomyLabel.Create(root, Title.ToUpperInvariant(), transform.InverseTransformPoint(transform.position + Vector3.up * 3.2f), 0.09f, new Color(1f, 0.85f, 0.3f));
        }

        private void OnDrawGizmos()
        {
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.color = new Color(1f, 0.78f, 0.1f, 0.35f);
            Gizmos.DrawWireCube(new Vector3(0f, (Size.y - 1f) * 0.5f, 0f), new Vector3(Size.x, Size.y + 1f, Size.z));
        }
    }

    /// <summary>
    /// The in-world workshop prompt (every machine): shown while the team van is in a repair zone and the local player
    /// drives it or stands near it (or stands near an empty zone). Lists the three branches with the current and next
    /// tier, the full price and what changes (§11 "Покупка улучшения"); U picks a branch, Enter buys it. The client only
    /// sends the intent; the host re-checks zone, handbrake, tier and fund at the commit.
    /// </summary>
    public sealed class WorkshopPrompt : MonoBehaviour
    {
        private static readonly VanBranch[] Branches = { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes };

        private VanController van;
        private GreyboxVanSeat seat;
        private float nextSearch;
        private bool visible;
        private bool vanInZone;
        private bool liftZone;
        private int selected;
        private bool busy;
        private string message = "";
        private bool messageOk;
        private float messageUntil;
        private GUIStyle box;
        private GUIStyle text;

        private void Update()
        {
            visible = false;
            if (OnlyVolunteers.UI.OvMenuGate.Blocking || !EconomyClientView.Available) return;
            if (van == null && Time.unscaledTime >= nextSearch)
            {
                nextSearch = Time.unscaledTime + 2f;
                van = FindAnyObjectByType<VanController>();
                seat = van != null ? van.GetComponent<GreyboxVanSeat>() : null;
            }
            if (van == null || WorkshopZone.All.Count == 0) return;
            Rigidbody body = van.GetComponent<Rigidbody>();
            Vector3 centre = body != null ? body.worldCenterOfMass : van.transform.position;
            WorkshopZone zone = WorkshopZone.Containing(centre);
            vanInZone = zone != null;
            liftZone = zone != null && zone.LiftOnly;
            bool driving = seat != null && seat.Driving;
            Vector3 me = seat != null && seat.Pawn != null && !driving ? seat.Pawn.Position
                : Camera.main != null ? Camera.main.transform.position : centre;
            if (vanInZone) visible = driving || (me - centre).sqrMagnitude < 10f * 10f;
            else visible = WorkshopZone.Nearest(me, 9f) != null;
            if (!visible || !vanInZone || liftZone) return;
            if (Input.GetKeyDown(KeyCode.U)) selected = (selected + 1) % Branches.Length;
            if ((Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter)) && !busy) Buy(Branches[selected]);
        }

        private void Buy(VanBranch branch)
        {
            EconomySnapshot snap = EconomyClientView.Current;
            TeamEconomy economy = TeamEconomy.Instance;
            if (snap == null || economy == null) return;
            int next = snap.VanTier(branch) + 1;
            if (next > EconomyPrices.VanMaxTier) { Show(false, PurchaseResult.Explain(PurchaseError.AlreadyMax)); return; }
            busy = true;
            economy.Request(EconomyRequestKind.VanTier, ((int)branch).ToString(CultureInfo.InvariantCulture), "", next, (ok, text) =>
            {
                busy = false;
                Show(ok, text);
            });
        }

        private void Show(bool ok, string text)
        {
            message = text;
            messageOk = ok;
            messageUntil = Time.unscaledTime + 5f;
        }

        private static VanUpgradeCategory Category(VanBranch b) =>
            b == VanBranch.Engine ? VanUpgradeCategory.Engine : b == VanBranch.Handling ? VanUpgradeCategory.Handling : VanUpgradeCategory.Brakes;

        private void OnGUI()
        {
            if (!visible || OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            EconomySnapshot snap = EconomyClientView.Current;
            if (snap == null) return;
            box ??= new GUIStyle(GUI.skin.box) { alignment = TextAnchor.UpperLeft, richText = true, fontSize = 16, padding = new RectOffset(14, 14, 10, 10) };
            text ??= new GUIStyle(GUI.skin.label) { richText = true, fontSize = 16, wordWrap = true };
            var sb = new System.Text.StringBuilder();
            sb.Append("<b>МАСТЕРСКАЯ</b> · общий фонд <b>").Append(EconomyState.Money(snap.balance)).Append("</b>\n");
            if (!vanInZone) sb.Append("Заезжай фургоном в ремонтную зону (жёлтые столбы) и поставь его на ручник.\n");
            else if (liftZone)
            {
                bool held = WorkshopServiceV01.Instance != null && WorkshopServiceV01.Instance.Session.HoldsVan;
                sb.Append(held ? "Бусик на подъёмнике — механик занимается им.\n"
                               : "Бусик над ямой. Выйди и поговори с механиком (<b>E</b>) — «Улучшить бусик»: он поднимет его на подъёмник.\n");
            }
            else
            {
                VanUpgradeConfig config = van != null && van.TryGetComponent(out VanUpgrades up) ? up.Config : null;
                if (!snap.workshopUnlocked) sb.Append("<color=#FFB13B>Мастерская закрыта: сначала поручение механика (M06 — привезти его конкурента). Журнал: телефон → Задания.</color>\n");
                if (snap.vanLegacyDebugProfile) sb.Append("<color=#FFB13B>Бусик в отладочном профиле (старый максимум). Телефон → Магазин: «Перейти на прогрессию».</color>\n");
                bool handbrake = van != null && van.Handbrake;
                bool stopped = van != null && Mathf.Abs(van.SpeedKmh) < 1.5f;
                sb.Append(handbrake && stopped ? "<color=#5BE07A>Фургон в зоне, на ручнике</color>\n" : "<color=#FFB13B>Остановись и поставь на ручник (Space / выйди из машины)</color>\n");
                for (int i = 0; i < Branches.Length; i++)
                {
                    VanBranch b = Branches[i];
                    int tier = snap.VanTier(b);
                    string mark = i == selected ? "<color=#FFD24A>▶</color> " : "   ";
                    sb.Append(mark).Append("<b>").Append(EconomyPrices.BranchTitle(b)).Append("</b> ").Append(EconomyPrices.TierName(tier));
                    if (tier >= EconomyPrices.VanMaxTier) { sb.Append(" — максимум\n"); continue; }
                    int price = EconomyPrices.VanTierPrice(b, tier + 1);
                    sb.Append(" → ").Append(EconomyPrices.TierName(tier + 1)).Append("  <b>").Append(EconomyState.Money(price)).Append("</b>")
                      .Append(price > snap.balance ? " <color=#FF4D5E>(не хватает)</color>" : "").Append('\n')
                      .Append("      ").Append(VanUpgradeConfig.DescribeProgression(config, Category(b), tier + 1)).Append('\n');
                }
                sb.Append(busy ? "Отправляю…" : "<b>U</b> — выбрать ветку · <b>Enter</b> — купить выбранную");
            }
            if (Time.unscaledTime < messageUntil)
                sb.Append("\n<color=").Append(messageOk ? "#5BE07A" : "#FF4D5E").Append('>').Append(message).Append("</color>");
            string content = sb.ToString();
            float width = Mathf.Min(620f, Screen.width - 40f);
            float height = box.CalcHeight(new GUIContent(content), width) + 6f;
            GUI.Box(new Rect(20f, Screen.height * 0.30f, width, height), content, box);
        }
    }
}
