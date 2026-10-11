using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // App store: other apps (taxi etc.) are installed from here. Their contents are placeholders.
    public sealed class MarketApp : PhoneApp
    {
        private const float InstallSeconds = 7f;     // download + install, deliberately not instant
        private const float DownloadShare = 0.8f;

        private sealed class Listing
        {
            public string Name;
            public string Icon;
            public string Color;
            public int Price;
            public string StubText;
            public float Progress = -1f;
            public PhoneApp Installed;
            public Text ButtonLabel;
            public Button Button;
        }

        private readonly List<Listing> listings = new()
        {
            new Listing
            {
                Name = "Taxi", Icon = "app_taxi", Color = "#D99A00",
                StubText = "No drivers in your area.\nTry walking."
            },
            new Listing
            {
                Name = "ShadyShop", Icon = "app_shop", Color = "#E0457B",
                StubText = "The store is restocking.\nCome back after the next update."
            },
            new Listing
            {
                Name = "City News", Icon = "app_news", Color = "#4A5468", Price = 2,
                StubText = "Today: nothing happened.\nProbably."
            }
        };

        private RectTransform list;

        public override string Title => "PayMarket";
        public override string IconName => "app_market";

        protected override void Build(RectTransform root)
        {
            const float top = PhoneLayout.HeaderHeight;
            PhoneUi.Panel(root, "Background", Color.white).rectTransform.Stretch();
            var search = PhoneUi.Panel(root, "Search", PhoneUi.Hex("#ECEDF1"), 22);
            search.rectTransform.Top(top + 12, 44, 14, 14);
            PhoneUi.Label(search.transform, "Search apps & games", 15, PhoneUi.Muted).rectTransform.Stretch(20, 0, 16, 0);
            PhoneUi.Label(root, "Recommended for volunteers", 17, PhoneUi.Ink, TextAnchor.MiddleLeft, false, true)
                .rectTransform.Top(top + 70, 26, 18, 18);
            var scroll = PhoneUi.Scroll(root, "Listings", out list, 4, new RectOffset(0, 0, 4, 10));
            scroll.GetComponent<RectTransform>().Stretch(0, top + 102, 0, 30);
            foreach (var listing in listings)
                BuildRow(listing);

            var header = PhoneUi.Header(root, Title, PhoneUi.Hex("#16191F"), out var subtitle, Phone.Back);
            subtitle.text = "Apps for busy volunteers";
        }

        private void BuildRow(Listing listing)
        {
            var row = PhoneUi.Rect("Row_" + listing.Name, list);
            PhoneUi.Height(row.gameObject, 84);
            PhoneUi.Picture(row, "Icon", PhoneUi.Icon(listing.Icon)).rectTransform
                .Place(new Vector2(0, 0.5f), new Vector2(50, 0), new Vector2(60, 60));
            PhoneUi.Label(row, listing.Name, 18, PhoneUi.Ink, TextAnchor.MiddleLeft, true)
                .rectTransform.Stretch(94, 0, 124, 0);

            listing.Button = PhoneUi.TextButton(row, "", PhoneUi.Hex("#1F9D55"), Color.white, 15, 18, () => Press(listing));
            ((RectTransform)listing.Button.transform).Place(new Vector2(1, 0.5f), new Vector2(-62, 0), new Vector2(104, 38));
            listing.ButtonLabel = listing.Button.GetComponentInChildren<Text>();
            PhoneUi.Panel(row, "Line", PhoneUi.Hex("#EDEDED")).rectTransform.Bottom(0, 1, 94, 0);
            UpdateButton(listing);
        }

        private void Press(Listing listing)
        {
            if (listing.Installed != null)
            {
                Phone.OpenApp(listing.Installed);
                return;
            }
            if (listing.Progress >= 0f)
                return;
            if (listing.Price > 0 && !Phone.Wallet.TryPay(listing.Price, "PayMarket", listing.Name))
            {
                Phone.Toast("Not enough money. Go volunteer.");
                return;
            }
            listing.Progress = 0f;
        }

        public override void BackgroundTick()
        {
            foreach (var listing in listings)
            {
                if (listing.Progress < 0f || listing.Installed != null)
                    continue;
                listing.Progress += Time.unscaledDeltaTime / InstallSeconds;
                if (listing.Progress >= 1f)
                {
                    listing.Installed = new StubApp(listing.Name, listing.Icon, PhoneUi.Hex(listing.Color),
                        listing.StubText);
                    Phone.Install(listing.Installed);
                    Phone.Toast(listing.Name + " installed");
                }
            }
        }

        public override void Tick()
        {
            foreach (var listing in listings)
                UpdateButton(listing);
        }

        private static void UpdateButton(Listing listing)
        {
            var image = (Image)listing.Button.targetGraphic;
            if (listing.Installed != null)
            {
                listing.ButtonLabel.text = "Open";
                image.color = PhoneUi.Hex("#3D74B5");
            }
            else if (listing.Progress >= 0f)
            {
                listing.ButtonLabel.text = listing.Progress < DownloadShare
                    ? Mathf.FloorToInt(listing.Progress / DownloadShare * 100f) + "%"
                    : "Installing…";
                image.color = PhoneUi.Hex("#9AA0A8");
            }
            else
            {
                listing.ButtonLabel.text = listing.Price > 0 ? PhoneUi.Money(listing.Price) : "Install";
                image.color = PhoneUi.Hex("#1F9D55");
            }
        }
    }
}
