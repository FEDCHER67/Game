using System.Collections.Generic;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Inventory;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // ECONOMY spec v01 §3.1, §11 (2026-10-28): the team has ONE shared fund (TeamEconomy, host-authoritative). Whenever
    // it runs, Bank and Cash both read it and the history is its real transaction lines; there is no bank-versus-pocket
    // split and no payment from here (purchases go to the host as intents: TeamEconomy.Request).
    // Without an economy (scenes with no session) the old local placeholders stay: "Cash on you" = the bound inventory
    // (Pocket) or $85, the bank $1 251 and its placeholder history.
    public sealed class PhoneWallet
    {
        public sealed class Entry
        {
            public string Title;
            public string Detail;
            public int Amount;
        }

        private const int PlaceholderCash = 85;

        private int placeholderBank = 1251;
        private int version;

        /// <summary>The team's shared fund is running (then it is the only balance).</summary>
        public bool HasTeamFund => EconomyClientView.Available;
        public int Bank => HasTeamFund ? EconomyClientView.Balance : placeholderBank;
        public IInventoryView Pocket { get; set; }
        public int Cash => HasTeamFund ? EconomyClientView.Balance : Pocket != null ? Pocket.Cash : PlaceholderCash;
        /// <summary>Changes when the shown history changes (the fund's transaction sequence, or a placeholder payment).</summary>
        public long Version => HasTeamFund ? EconomyClientView.Current.seq : -1 - version;
        public readonly List<Entry> History = new()
        {
            new Entry { Title = "Scrap Guy", Detail = "Blood · 2 bags", Amount = 180 },
            new Entry { Title = "Gas station", Detail = "Card payment", Amount = -35 },
            new Entry { Title = "Pharmacy", Detail = "Bandages, painkillers, gloves", Amount = -22 },
            new Entry { Title = "Scrap Guy", Detail = "Blood · 1 bag", Amount = 90 },
            new Entry { Title = "Mom", Detail = "\"for food, not nonsense\"", Amount = 38 },
            new Entry { Title = "ShadyBank", Detail = "Welcome bonus", Amount = 1000 }
        };

        /// <summary>The team's real money lines (newest first) while the fund runs, else the placeholder history.</summary>
        public List<Entry> Lines()
        {
            if (!HasTeamFund) return History;
            var lines = new List<Entry>();
            foreach (FundEntry e in EconomyClientView.Current.recent)
                lines.Add(new Entry { Title = e.title, Detail = KindName(e.kind) + " · фонд после: " + PhoneUi.Money(e.balanceAfter), Amount = e.amount });
            return lines;
        }

        private static string KindName(string kind) => kind switch
        {
            "sale" => "Продажа",
            "van" => "Мастерская",
            "equipment" => "Оборудование",
            "property" => "Недвижимость",
            "migration" => "Перенос старых денег",
            "phone" => "Приложение",
            "dev" => "DEV",
            "system" => "Система",
            _ => kind,
        };

        /// <summary>Placeholder payment, only without a team fund (with one, ask the host: TeamEconomy.Request).</summary>
        public bool TryPay(int amount, string title, string detail)
        {
            if (HasTeamFund || amount > placeholderBank)
                return false;
            placeholderBank -= amount;
            History.Insert(0, new Entry { Title = title, Detail = detail, Amount = -amount });
            version++;
            return true;
        }
    }

    // Canon §58: cash on hand can be lost; deposits happen at ATMs, not in the app.
    public sealed class BankApp : PhoneApp
    {
        private static readonly Color Navy = PhoneUi.Hex("#22307F");
        private Text balance;
        private Text cash;
        private Text cardTitle;
        private Text note;
        private Text depositLabel;
        private Text atmLabel;
        private RectTransform history;
        private long builtVersion = long.MinValue;

        public override string Title => "Bank";
        public override string IconName => "app_bank";

        protected override void Build(RectTransform root)
        {
            const float top = PhoneLayout.HeaderHeight;
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#F2F3F7")).rectTransform.Stretch();

            var card = PhoneUi.Panel(root, "Card", PhoneUi.Hex("#4153C8"), 22);
            card.rectTransform.Top(top + 14, 148, 14, 14);
            cardTitle = PhoneUi.Label(card.transform, "Account balance", 14, new Color(1, 1, 1, 0.75f));
            cardTitle.rectTransform.Top(16, 20, 20, 80);
            balance = PhoneUi.Label(card.transform, "", 38, Color.white, TextAnchor.MiddleLeft, false, true);
            balance.rectTransform.Top(38, 52, 20, 20);
            cash = PhoneUi.Label(card.transform, "", 15, Color.white, TextAnchor.MiddleLeft, true);
            cash.rectTransform.Top(96, 22, 20, 20);
            PhoneUi.Label(card.transform, "•••• 0666", 13, new Color(1, 1, 1, 0.6f), TextAnchor.MiddleRight)
                .rectTransform.Top(118, 20, 20, 18);
            PhoneUi.Picture(card.transform, "Coin", PhoneUi.Icon(IconName)).rectTransform
                .Place(new Vector2(1, 1), new Vector2(-42, -40), new Vector2(56, 56));

            note = PhoneUi.Label(root, "Cash on you can be lost if you get busted. Deposit it at an ATM.", 13,
                PhoneUi.Muted, TextAnchor.UpperLeft);
            note.rectTransform.Top(top + 172, 38, 20, 20);

            // With the team fund: Shop / deliveries; without it the old placeholder buttons.
            var deposit = PhoneUi.TextButton(root, "Deposit cash", Navy, Color.white, 15, 22, () =>
            {
                if (Phone.Wallet.HasTeamFund) Phone.OpenApp(Phone.Shop);
                else Phone.Toast("Deposits only at an ATM.");
            });
            ((RectTransform)deposit.transform).Top(top + 214, 46, 14, 206);
            depositLabel = deposit.GetComponentInChildren<Text>();
            var atm = PhoneUi.TextButton(root, "Find ATM", PhoneUi.Hex("#DDE1F3"), Navy, 15, 22, () =>
            {
                if (Phone.Wallet.HasTeamFund) { Phone.OpenApp(Phone.Shop); return; }
                Phone.OpenApp(Phone.Map);
                Phone.Toast("No ATMs on this test site yet.");
            });
            ((RectTransform)atm.transform).Top(top + 214, 46, 206, 14);
            atmLabel = atm.GetComponentInChildren<Text>();

            PhoneUi.Label(root, "History", 17, PhoneUi.Ink, TextAnchor.MiddleLeft, false, true)
                .rectTransform.Top(top + 274, 26, 20, 20);
            var scroll = PhoneUi.Scroll(root, "History", out history, 0, new RectOffset(14, 14, 0, 10));
            scroll.GetComponent<RectTransform>().Stretch(0, top + 304, 0, 30);

            var header = PhoneUi.Header(root, "ShadyBank", Navy, out var subtitle, Phone.Back);
            subtitle.text = "Your money. No questions.";
        }

        private int shownCash = int.MinValue;
        private bool shownFund;

        // W86: the real cash can change while the app is open (a sale): keep the line current.
        public override void Tick()
        {
            var wallet = Phone.Wallet;
            if (cash != null && (wallet.Cash != shownCash || wallet.HasTeamFund != shownFund)) ShowCash();
            if (wallet.Version != builtVersion) BuildHistory();
        }

        private void ShowCash()
        {
            var wallet = Phone.Wallet;
            shownCash = wallet.Cash;
            shownFund = wallet.HasTeamFund;
            balance.text = PhoneUi.Money(wallet.Bank);
            if (shownFund)
            {
                int waiting = 0;
                foreach (DeliveryOrder d in EconomyClientView.Current.deliveries)
                    if (d.State == DeliveryState.Pending || d.State == DeliveryState.Waiting) waiting++;
                cardTitle.text = "Общий фонд команды";
                cash.text = waiting > 0 ? "Ожидаемых поставок: " + waiting : "Одни деньги на всю команду";
                note.text = "Продажи и покупки всей команды идут через этот фонд. Ниже — реальные записи.";
                depositLabel.text = "Магазин";
                atmLabel.text = "Доставки";
            }
            else
            {
                cardTitle.text = "Account balance";
                cash.text = "Cash on you: " + PhoneUi.Money(shownCash);
                note.text = "Cash on you can be lost if you get busted. Deposit it at an ATM.";
                depositLabel.text = "Deposit cash";
                atmLabel.text = "Find ATM";
            }
        }

        public override void Show()
        {
            base.Show();
            ShowCash();
            BuildHistory();
        }

        private void BuildHistory()
        {
            var wallet = Phone.Wallet;
            if (builtVersion == wallet.Version)
                return;
            builtVersion = wallet.Version;
            PhoneUi.Clear(history);
            foreach (var entry in wallet.Lines())
            {
                var row = PhoneUi.Panel(history, "Entry", Color.white, 14);
                PhoneUi.Height(row.gameObject, 58);
                PhoneUi.Label(row.transform, entry.Title, 15, PhoneUi.Ink, TextAnchor.MiddleLeft, true)
                    .rectTransform.Top(8, 22, 16, 100);
                var detail = PhoneUi.Label(row.transform, entry.Detail, 13, PhoneUi.Muted);
                detail.verticalOverflow = VerticalWrapMode.Truncate;
                detail.rectTransform.Top(30, 20, 16, 100);
                var amount = PhoneUi.Label(row.transform, (entry.Amount > 0 ? "+" : "") + PhoneUi.Money(entry.Amount),
                    16, entry.Amount > 0 ? PhoneUi.Hex("#1F9D55") : PhoneUi.Ink, TextAnchor.MiddleRight, true);
                amount.rectTransform.Stretch(0, 0, 16, 0);
                var gap = PhoneUi.Rect("Gap", history);
                PhoneUi.Height(gap.gameObject, 8);
            }
        }
    }
}
