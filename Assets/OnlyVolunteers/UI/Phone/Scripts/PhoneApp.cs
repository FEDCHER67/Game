using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // One screen of the phone. Built once on first open, then shown/hidden.
    public abstract class PhoneApp
    {
        protected PhoneController Phone { get; private set; }
        public RectTransform Root { get; private set; }
        public abstract string Title { get; }
        public abstract string IconName { get; }
        public virtual int Badge => 0;
        // True when the app needs mouse look (camera viewfinder) instead of a free cursor.
        public virtual bool WantsLook => false;

        public void Attach(PhoneController phone, RectTransform screen)
        {
            Phone = phone;
            Root = PhoneUi.Rect("App_" + Title, screen).Stretch();
            Build(Root);
            Root.gameObject.SetActive(false);
        }

        protected abstract void Build(RectTransform root);
        public virtual void Show() => Root.gameObject.SetActive(true);
        public virtual void Hide() => Root.gameObject.SetActive(false);
        // Visible frames only.
        public virtual void Tick() { }
        // Every frame, also while the phone is in the pocket.
        public virtual void BackgroundTick() { }
        // Left mouse button while WantsLook.
        public virtual void Primary() { }
        // Returns true if the app consumed "back" internally (e.g. closing a sub-page).
        public virtual bool Back() => false;
        public virtual void Dispose() { }
    }

    // Placeholder for apps installed from PayMarket; real content comes later.
    public sealed class StubApp : PhoneApp
    {
        private readonly string title;
        private readonly string icon;
        private readonly Color color;
        private readonly string message;

        public StubApp(string title, string icon, Color color, string message)
        {
            this.title = title;
            this.icon = icon;
            this.color = color;
            this.message = message;
        }

        public override string Title => title;
        public override string IconName => icon;

        protected override void Build(RectTransform root)
        {
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#F3F1EC")).rectTransform.Stretch();
            PhoneUi.Header(root, title, color, out var subtitle, Phone.GoHome);
            PhoneUi.Picture(root, "Icon", PhoneUi.Icon(icon)).rectTransform
                .Place(new Vector2(0.5f, 0.5f), new Vector2(0, 90), new Vector2(128, 128));
            var label = PhoneUi.Label(root, message, 19, PhoneUi.Ink, TextAnchor.UpperCenter);
            label.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0, -60), new Vector2(320, 140));
            PhoneUi.Label(root, "Coming in a future update", 14, PhoneUi.Muted, TextAnchor.MiddleCenter)
                .rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0, -150), new Vector2(320, 24));
        }
    }
}
