using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Local placeholder money. Who owns money in co-op (shared or per player) is not decided yet.
    public sealed class PhoneWallet
    {
        public sealed class Entry
        {
            public string Title;
            public string Detail;
            public int Amount;
        }

        public int Bank { get; private set; } = 1251;
        public int Cash { get; private set; } = 85;
        public int Version { get; private set; }
        public readonly List<Entry> History = new()
        {
            new Entry { Title = "Scrap Guy", Detail = "Blood · 2 bags", Amount = 180 },
            new Entry { Title = "Gas station", Detail = "Card payment", Amount = -35 },
            new Entry { Title = "Pharmacy", Detail = "Bandages, painkillers, gloves", Amount = -22 },
            new Entry { Title = "Scrap Guy", Detail = "Blood · 1 bag", Amount = 90 },
            new Entry { Title = "Mom", Detail = "\"for food, not nonsense\"", Amount = 38 },
            new Entry { Title = "ShadyBank", Detail = "Welcome bonus", Amount = 1000 }
        };

        public bool TryPay(int amount, string title, string detail)
        {
            if (amount > Bank)
                return false;
            Bank -= amount;
            History.Insert(0, new Entry { Title = title, Detail = detail, Amount = -amount });
            Version++;
            return true;
        }
    }

    // Canon §58: cash on hand can be lost; deposits happen at ATMs, not in the app.
    public sealed class BankApp : PhoneApp
    {
        private static readonly Color Navy = PhoneUi.Hex("#22307F");
        private Text balance;
        private Text cash;
        private RectTransform history;
        private int builtVersion = -1;

        public override string Title => "Bank";
        public override string IconName => "app_bank";

        protected override void Build(RectTransform root)
        {
            const float top = PhoneLayout.HeaderHeight;
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#F2F3F7")).rectTransform.Stretch();

            var card = PhoneUi.Panel(root, "Card", PhoneUi.Hex("#4153C8"), 22);
            card.rectTransform.Top(top + 14, 148, 14, 14);
            PhoneUi.Label(card.transform, "Account balance", 14, new Color(1, 1, 1, 0.75f))
                .rectTransform.Top(16, 20, 20, 80);
            balance = PhoneUi.Label(card.transform, "", 38, Color.white, TextAnchor.MiddleLeft, false, true);
            balance.rectTransform.Top(38, 52, 20, 20);
            cash = PhoneUi.Label(card.transform, "", 15, Color.white, TextAnchor.MiddleLeft, true);
            cash.rectTransform.Top(96, 22, 20, 20);
            PhoneUi.Label(card.transform, "•••• 0666", 13, new Color(1, 1, 1, 0.6f), TextAnchor.MiddleRight)
                .rectTransform.Top(118, 20, 20, 18);
            PhoneUi.Picture(card.transform, "Coin", PhoneUi.Icon(IconName)).rectTransform
                .Place(new Vector2(1, 1), new Vector2(-42, -40), new Vector2(56, 56));

            PhoneUi.Label(root, "Cash on you can be lost if you get busted. Deposit it at an ATM.", 13,
                PhoneUi.Muted, TextAnchor.UpperLeft).rectTransform.Top(top + 172, 38, 20, 20);

            var deposit = PhoneUi.TextButton(root, "Deposit cash", Navy, Color.white, 15, 22,
                () => Phone.Toast("Deposits only at an ATM."));
            ((RectTransform)deposit.transform).Top(top + 214, 46, 14, 206);
            var atm = PhoneUi.TextButton(root, "Find ATM", PhoneUi.Hex("#DDE1F3"), Navy, 15, 22, () =>
            {
                Phone.OpenApp(Phone.Map);
                Phone.Toast("No ATMs on this test site yet.");
            });
            ((RectTransform)atm.transform).Top(top + 214, 46, 206, 14);

            PhoneUi.Label(root, "History", 17, PhoneUi.Ink, TextAnchor.MiddleLeft, false, true)
                .rectTransform.Top(top + 274, 26, 20, 20);
            var scroll = PhoneUi.Scroll(root, "History", out history, 0, new RectOffset(14, 14, 0, 10));
            scroll.GetComponent<RectTransform>().Stretch(0, top + 304, 0, 30);

            var header = PhoneUi.Header(root, "ShadyBank", Navy, out var subtitle, Phone.Back);
            subtitle.text = "Your money. No questions.";
        }

        public override void Show()
        {
            base.Show();
            var wallet = Phone.Wallet;
            balance.text = PhoneUi.Money(wallet.Bank);
            cash.text = "Cash on you: " + PhoneUi.Money(wallet.Cash);
            if (builtVersion == wallet.Version)
                return;
            builtVersion = wallet.Version;
            PhoneUi.Clear(history);
            foreach (var entry in wallet.History)
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
