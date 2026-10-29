using System.Collections.Generic;
using System.Text;
using OnlyVolunteers.Economy;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // ECONOMY spec v01 §4, §4.1, §7.1, §11: the phone's shop for large purchases of the team. Every price comes from
    // EconomyPrices; every purchase is an intent to the host (TeamEconomy.Request), which charges the ONE shared fund and
    // answers; nothing is shown as paid before that answer. Consumables are not sold here (pharmacy only, §4.1).
    // Tabs: Equipment (delivered as a paid crate to an owned base after one game hour), Property (bases; opens after the
    // first organ buyer was met), Deliveries (state of every order), DEV (editor / development builds: story and workshop
    // toggles, test money).
    public sealed class ShopApp : PhoneApp
    {
        private enum Tab { Equipment, Property, Deliveries, Dev }

        private static readonly Color Green = PhoneUi.Hex("#1F6F4A");
        private static readonly Color Buy = PhoneUi.Hex("#1F9D55");
        private static readonly Color Confirm = PhoneUi.Hex("#E08A00");
        private static readonly Color Grey = PhoneUi.Hex("#9AA0A8");
        private const float ConfirmSeconds = 4f;

        private Tab tab = Tab.Equipment;
        private RectTransform list;
        private Text subtitle;
        private readonly List<(Tab tab, Image image)> tabButtons = new();
        private string builtSignature = "";
        private string confirmId = "";
        private float confirmUntil;
        private bool busy;
        private int baseIndex;

        public override string Title => "Магазин";
        public override string IconName => "app_shop";

        protected override void Build(RectTransform root)
        {
            const float top = PhoneLayout.HeaderHeight;
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#F2F3F0")).rectTransform.Stretch();
            var tabs = new List<(Tab, string)> { (Tab.Equipment, "Оборуд."), (Tab.Property, "Недвиж."), (Tab.Deliveries, "Доставки") };
            if (Debug.isDebugBuild) tabs.Add((Tab.Dev, "DEV"));
            float width = (PhoneLayout.Width - 28f - (tabs.Count - 1) * 6f) / tabs.Count;
            for (int i = 0; i < tabs.Count; i++)
            {
                Tab t = tabs[i].Item1;
                var button = PhoneUi.TextButton(root, tabs[i].Item2, Grey, Color.white, 14, 16, () => { tab = t; confirmId = ""; Rebuild(); });
                var rect = (RectTransform)button.transform;
                rect.anchorMin = rect.anchorMax = new Vector2(0, 1);
                rect.pivot = new Vector2(0, 1);
                rect.sizeDelta = new Vector2(width, 38);
                rect.anchoredPosition = new Vector2(14 + i * (width + 6f), -(top + 10));
                tabButtons.Add((t, (Image)button.targetGraphic));
            }
            var scroll = PhoneUi.Scroll(root, "List", out list, 8, new RectOffset(14, 14, 4, 16));
            scroll.GetComponent<RectTransform>().Stretch(0, top + 58, 0, 30);
            PhoneUi.Header(root, Title, Green, out subtitle, Phone.Back);
        }

        public override void Show()
        {
            base.Show();
            builtSignature = "";
            Rebuild();
        }

        public override void Tick()
        {
            if (confirmId.Length > 0 && Time.unscaledTime > confirmUntil) confirmId = "";
            if (Signature() != builtSignature) Rebuild();
        }

        private string Signature()
        {
            EconomySnapshot s = EconomyClientView.Current;
            var sb = new StringBuilder();
            sb.Append((int)tab).Append('|').Append(confirmId).Append('|').Append(busy).Append('|').Append(baseIndex);
            if (s == null) return sb.Append("|none").ToString();
            sb.Append('|').Append(s.ready).Append(s.balance).Append('|').Append(s.seq).Append('|').Append(s.workshopUnlocked)
              .Append(s.firstOrganBuyerMet).Append(s.vanLegacyDebugProfile).Append('|').Append(string.Join(",", s.ownedBases));
            foreach (DeliveryOrder d in s.deliveries) sb.Append('|').Append(d.id).Append(d.state);
            if (tab == Tab.Deliveries) sb.Append('|').Append(Mathf.FloorToInt((float)s.worldHours * 20f));
            return sb.ToString();
        }

        // ---------- building ----------

        private void Rebuild()
        {
            builtSignature = Signature();
            foreach ((Tab t, Image image) in tabButtons) image.color = t == tab ? Green : Grey;
            PhoneUi.Clear(list);
            EconomySnapshot s = EconomyClientView.Current;
            subtitle.text = s != null ? "Общий фонд " + PhoneUi.Money(s.balance) : "Нет общего фонда";
            if (s == null || TeamEconomy.Instance == null)
            {
                Info("Магазин работает в игровой сессии с общим фондом команды (карта, сетевая игра).");
                return;
            }
            if (!s.ready) Info("Сохранение загружается…");
            if (s.vanLegacyDebugProfile)
                Action("Бусик в отладочном профиле (старый максимум StartAtMax). Покупки мастерской недоступны, пока слот не переведён на прогрессию: бусик станет ступени 0, деньги и имущество не тронутся.",
                    "Перейти", "switch", () => Send(EconomyRequestKind.SwitchToProgression, "", "", 0));
            switch (tab)
            {
                case Tab.Equipment: BuildEquipment(s); break;
                case Tab.Property: BuildProperty(s); break;
                case Tab.Deliveries: BuildDeliveries(s); break;
                case Tab.Dev: BuildDev(s); break;
            }
        }

        private List<PropertyOffer> DeliveryBases(EconomySnapshot s)
        {
            var bases = new List<PropertyOffer>();
            foreach (PropertyOffer p in EconomyPrices.Properties)
                if (p.AcceptsDeliveries && s.OwnsBase(p.Id)) bases.Add(p);
            return bases;
        }

        private void BuildEquipment(EconomySnapshot s)
        {
            List<PropertyOffer> bases = DeliveryBases(s);
            if (bases.Count == 0) { Info("Нет базы, куда можно доставить оборудование."); return; }
            baseIndex = Mathf.Clamp(baseIndex, 0, bases.Count - 1);
            PropertyOffer target = bases[baseIndex];
            Action("Доставка на базу: <b>" + target.Title + "</b>\nЯщик появится через 1 игровой час; его надо распаковать (E).",
                bases.Count > 1 ? "Сменить" : "", "base", () => { baseIndex = (baseIndex + 1) % bases.Count; confirmId = ""; Rebuild(); });
            foreach (EquipmentOffer item in EconomyPrices.Equipment)
            {
                string id = "eq:" + item.Id;
                string body = item.Effect + (item.Available ? "" : "\n<color=#C0392B>" + item.UnavailableReason + "</color>");
                Row(item.Title, body, item.Available ? PriceLabel(id, item.Price) : "Недоступно",
                    !item.Available ? Grey : confirmId == id ? Confirm : Buy, 96,
                    item.Available ? () => ConfirmThen(id, () => Send(EconomyRequestKind.Equipment, item.Id, target.Id, item.Price)) : null);
            }
        }

        private void BuildProperty(EconomySnapshot s)
        {
            if (!s.firstOrganBuyerMet)
                Info("Покупка помещений откроется после знакомства с первым органным скупщиком (он расскажет о трёх базах).");
            foreach (PropertyOffer p in EconomyPrices.Properties)
            {
                string id = "pr:" + p.Id;
                string tables = p.Tables < 0 ? "столы: без фиксированного лимита" : p.Tables == 0 ? "столов нет" : "столов до " + p.Tables;
                string body = p.Location + " · " + tables + "\n" + (p.Purchasable ? "Пустое помещение — оборудование не включено" : p.StartingKit);
                bool owned = s.OwnsBase(p.Id);
                string label;
                Color color;
                UnityEngine.Events.UnityAction click = null;
                if (owned) { label = "Своё"; color = Grey; }
                else if (!p.Purchasable) { label = "По сюжету"; color = Grey; }
                else if (!s.firstOrganBuyerMet) { label = PhoneUi.Money(p.Price); color = Grey; }
                else
                {
                    label = PriceLabel(id, p.Price);
                    color = confirmId == id ? Confirm : Buy;
                    click = () => ConfirmThen(id, () => Send(EconomyRequestKind.Property, p.Id, "", p.Price));
                }
                Row(p.Title, body, label, color, 104, click);
            }
        }

        private void BuildDeliveries(EconomySnapshot s)
        {
            if (s.deliveries.Count == 0) { Info("Заказов нет. Оборудование заказывается во вкладке «Оборуд.»."); return; }
            for (int i = s.deliveries.Count - 1; i >= 0; i--)
            {
                DeliveryOrder d = s.deliveries[i];
                EquipmentOffer item = EconomyPrices.FindEquipment(d.itemId);
                PropertyOffer place = EconomyPrices.FindProperty(d.baseId);
                string state;
                switch (d.State)
                {
                    case DeliveryState.Pending:
                        int minutes = Mathf.Max(1, Mathf.CeilToInt((float)((d.dueAt - s.worldHours) * 60.0)));
                        state = "в пути · ещё ≈ " + minutes + " игр. мин";
                        break;
                    case DeliveryState.Waiting: state = "<color=#C77700>ждёт свободного места на базе — оплата сохранена</color>"; break;
                    case DeliveryState.Arrived: state = "<color=#1F9D55>ящик на месте — подойди и открой (E)</color>"; break;
                    default: state = "распаковано"; break;
                }
                Row((item != null ? item.Title : d.itemId) + " · " + PhoneUi.Money(d.price),
                    d.id + " → " + (place != null ? place.Title : d.baseId) + "\n" + state, "", Grey, 82, null);
            }
        }

        private void BuildDev(EconomySnapshot s)
        {
            Info("Отладочные переключатели (только редактор / dev-сборка). В обычной игре мастерскую открывает поручение механика (M06), недвижимость — знакомство со скупщиком (M05); эти кнопки сюжет не засчитывают.");
            Action("Мастерская: " + (s.workshopUnlocked ? "<b>открыта</b>" : "<b>закрыта</b>"), s.workshopUnlocked ? "Закрыть" : "Открыть", "dev-ws",
                () => Send(EconomyRequestKind.DevWorkshop, "", "", s.workshopUnlocked ? 0 : 1));
            Action("Ремонтная зона: настоящая — в среднем боксе мастерской к северу от Стройки, над ямой (жёлтые столбы). Для проверки можно поставить временную вокруг фургона.", "Поставить", "dev-zone",
                () => Send(EconomyRequestKind.DevWorkshopZoneAtVan, "", "", 0));
            Action("Первый органный скупщик: " + (s.firstOrganBuyerMet ? "<b>встречен</b>" : "<b>не встречен</b>"), s.firstOrganBuyerMet ? "Сбросить" : "Встретить", "dev-buyer",
                () => Send(EconomyRequestKind.DevOrganBuyer, "", "", s.firstOrganBuyerMet ? 0 : 1));
            Action("Стяжки в полевой набор (аптека отложена).", "+4", "dev-ties",
                () => Send(EconomyRequestKind.DevGiveTies, "", "", 0));
            Action("Новый пустой шприц крови в хотбар (точки ежедневной находки у вагона ещё нет).", "Шприц", "dev-syringe",
                () => Send(EconomyRequestKind.DevGiveBloodSyringe, "", "", 0));
            Action("Следующее утро, 09:00 (день +1): смена конкурента на навесе, замена после гибели.", "Утро", "dev-morning",
                () => Send(EconomyRequestKind.DevNextMorning, "", "", 0));
            Action("Тестовые деньги в общий фонд (строка истории «DEV»).", "+$5 000", "dev-money",
                () => Send(EconomyRequestKind.DevCredit, "", "", 0));
            Action("Заказы в пути прибудут сейчас (час пропускается, повторной оплаты нет).", "Сейчас", "dev-due",
                () => Send(EconomyRequestKind.DevDeliveriesDue, "", "", 0));
        }

        // ---------- widgets ----------

        private string PriceLabel(string id, int price) => confirmId == id ? "Подтвердить" : PhoneUi.Money(price);

        private void ConfirmThen(string id, System.Action send)
        {
            if (busy) return;
            if (confirmId != id)
            {
                confirmId = id;
                confirmUntil = Time.unscaledTime + ConfirmSeconds;
                Rebuild();
                return;
            }
            confirmId = "";
            send();
        }

        private void Send(EconomyRequestKind kind, string arg, string arg2, int expected)
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || busy) return;
            busy = true;
            Phone.PlayTap();
            Rebuild();
            economy.Request(kind, arg, arg2, expected, (ok, message) =>
            {
                busy = false;
                Phone.Toast(message, 3.5f);
                Rebuild();
            });
        }

        private void Info(string text)
        {
            var row = PhoneUi.Panel(list, "Info", PhoneUi.Hex("#E4E8E2"), 14);
            var label = PhoneUi.Label(row.transform, text, 13, PhoneUi.Ink, TextAnchor.UpperLeft);
            label.rectTransform.Stretch(14, 10, 14, 10);
            PhoneUi.Height(row.gameObject, Mathf.Max(52f, 20f + 18f * Mathf.Ceil(text.Length / 44f)));
        }

        private void Action(string text, string button, string id, UnityEngine.Events.UnityAction click)
        {
            var row = PhoneUi.Panel(list, "Action_" + id, Color.white, 14);
            float height = Mathf.Max(64f, 22f + 17f * Mathf.Ceil(text.Length / 34f));
            PhoneUi.Height(row.gameObject, height);
            var label = PhoneUi.Label(row.transform, text, 13, PhoneUi.Ink, TextAnchor.MiddleLeft);
            label.rectTransform.Stretch(14, 6, button.Length > 0 ? 112 : 14, 6);
            if (button.Length == 0) return;
            var b = PhoneUi.TextButton(row.transform, button, busy ? Grey : Green, Color.white, 14, 16, busy ? null : click);
            ((RectTransform)b.transform).Place(new Vector2(1, 0.5f), new Vector2(-56, 0), new Vector2(92, 36));
        }

        private void Row(string title, string body, string button, Color color, float height, UnityEngine.Events.UnityAction click)
        {
            var row = PhoneUi.Panel(list, "Row", Color.white, 14);
            PhoneUi.Height(row.gameObject, height);
            bool hasButton = button.Length > 0;
            PhoneUi.Label(row.transform, title, 15, PhoneUi.Ink, TextAnchor.MiddleLeft, true)
                .rectTransform.Top(8, 22, 14, hasButton ? 118 : 14);
            var detail = PhoneUi.Label(row.transform, body, 12, PhoneUi.Muted, TextAnchor.UpperLeft);
            detail.rectTransform.Top(32, height - 38, 14, hasButton ? 118 : 14);
            if (!hasButton) return;
            var b = PhoneUi.TextButton(row.transform, button, busy && click != null ? Grey : color, Color.white, 14, 16, busy ? null : click);
            ((RectTransform)b.transform).Place(new Vector2(1, 0.5f), new Vector2(-60, 0), new Vector2(100, 38));
            if (click == null) b.interactable = false;
        }
    }
}
