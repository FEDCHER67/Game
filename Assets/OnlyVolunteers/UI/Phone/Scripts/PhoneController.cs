using System;
using System.Collections.Generic;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Local, presentation-only phone: Tab takes it out of the pocket. The game keeps running,
    // but the player stands still and the hands are busy while it is out.
    public sealed class PhoneController : MonoBehaviour
    {
        private const KeyCode ToggleKey = KeyCode.Tab;
        private const float SlideTime = 0.09f;
        private static readonly Vector2 HiddenPosition = new(300f, -1000f);
        private static readonly Vector2 HandPosition = new(300f, 40f);
        private static readonly Vector2 CameraPosition = new(0f, 70f);
        private const float Frame = 17f; // metal rim + bezel around the 392 x 852 screen

        private readonly List<PhoneApp> apps = new();
        private KccFirstPersonInput playerInput;
        private RectTransform holder;
        private RectTransform screen;
        private RectTransform appLayer;
        private Text clock;
        private Text hint;
        private Image toastPanel;
        private Text toastText;
        private float toastUntil;
        private RectTransform banner;
        private Image bannerIcon;
        private Text bannerTitle;
        private Text bannerBody;
        private float bannerUntil;
        private Vector2 slideVelocity;
        private float rotation;
        private float rotationVelocity;
        private AudioSource audioSource;
        private AudioClip shutterClip;
        private AudioClip notifyClip;
        private AudioClip tapClip;
        private GameObject ownedEventSystem;
        private PhoneApp current;

        public bool IsOpen { get; private set; }
        public event Action<bool> OpenChanged;
        public Camera ViewCamera { get; private set; }
        public PhoneWallet Wallet { get; private set; }
        public PhotoAlbum Album { get; private set; }
        public PhoneHome Home { get; private set; }
        public MessagesApp Messages { get; private set; }
        public CameraApp CameraApp { get; private set; }
        public GalleryApp Gallery { get; private set; }
        public MapApp Map { get; private set; }
        public BankApp Bank { get; private set; }
        public MarketApp Market { get; private set; }

        public static PhoneController Create(Camera viewCamera, KccFirstPersonInput input)
        {
            var phone = new GameObject("[Phone]").AddComponent<PhoneController>();
            phone.Init(viewCamera, input);
            return phone;
        }

        private void Init(Camera viewCamera, KccFirstPersonInput input)
        {
            ViewCamera = viewCamera;
            playerInput = input;
            Wallet = new PhoneWallet();
            Album = new PhotoAlbum();
            EnsureEventSystem();
            BuildFrame();
            BuildAudio();

            Home = Add(new PhoneHome());
            Messages = Add(new MessagesApp());
            CameraApp = Add(new CameraApp());
            Gallery = Add(new GalleryApp());
            Map = Add(new MapApp());
            Bank = Add(new BankApp());
            Market = Add(new MarketApp());
            foreach (var app in new PhoneApp[] { Messages, CameraApp, Gallery, Map, Bank, Market })
                Home.Place(app);

            current = Home;
            holder.anchoredPosition = HiddenPosition;
            holder.gameObject.SetActive(false);
        }

        private T Add<T>(T app) where T : PhoneApp
        {
            app.Attach(this, appLayer);
            apps.Add(app);
            return app;
        }

        public void Install(PhoneApp app)
        {
            Add(app);
            Home.Place(app);
        }

        // ---------- open / close / navigation ----------

        public void SetOpen(bool open)
        {
            if (IsOpen == open)
                return;
            IsOpen = open;
            if (open && !holder.gameObject.activeSelf)
            {
                holder.gameObject.SetActive(true);
                current.Show();
            }
            ApplyLook();
            OpenChanged?.Invoke(open);
        }

        public void OpenApp(PhoneApp app)
        {
            if (app == null || app == current)
                return;
            current.Hide();
            current = app;
            current.Show();
            ApplyLook();
        }

        public void GoHome() => OpenApp(Home);

        public void Back()
        {
            if (current.Back())
                return;
            if (current != Home)
                GoHome();
            else
                SetOpen(false);
        }

        private void ApplyLook()
        {
            bool look = IsOpen && current.WantsLook;
            if (playerInput != null)
            {
                playerInput.LookSuspended = IsOpen && !look;
                playerInput.MovementLocked = IsOpen;
            }
            hint.rectTransform.anchoredPosition = new Vector2(look ? CameraPosition.x : HandPosition.x, 16);
            hint.text = look
                ? "<b>LMB</b>  photo      <b>RMB</b>  back      <b>TAB</b>  hide"
                : "<b>TAB</b>  hide      <b>RMB</b>  back      <b>hold</b>  move icon";
        }

        private void Update()
        {
            // isActiveAndEnabled: on the map the whole pawn is switched off while driving the van.
            bool controlAllowed = playerInput == null || playerInput.isActiveAndEnabled;
            if (!controlAllowed)
            {
                if (IsOpen) SetOpen(false);
            }
            else if (Input.GetKeyDown(ToggleKey))
                SetOpen(!IsOpen);
            else if (IsOpen)
            {
                if (current.WantsLook && Input.GetMouseButtonDown(0))
                    current.Primary();
                if (Input.GetMouseButtonDown(1) || Input.GetKeyDown(KeyCode.Backspace))
                    Back();
            }

            // Index loop: an install from PayMarket adds to the list during the tick.
            for (int i = 0; i < apps.Count; i++)
                apps[i].BackgroundTick();
            if (IsOpen || holder.gameObject.activeSelf)
                current.Tick();

            Animate();
            clock.text = DateTime.Now.ToString("HH:mm");
            UpdateToastAndBanner();
        }

        private void Animate()
        {
            if (!holder.gameObject.activeSelf)
                return;
            bool cameraMode = IsOpen && current.WantsLook;
            Vector2 target = !IsOpen ? HiddenPosition : cameraMode ? CameraPosition : HandPosition;
            float targetRotation = !IsOpen ? -8f : 0f;
            float dt = Time.unscaledDeltaTime;
            holder.anchoredPosition = Vector2.SmoothDamp(holder.anchoredPosition, target,
                ref slideVelocity, SlideTime, Mathf.Infinity, dt);
            rotation = Mathf.SmoothDampAngle(rotation, targetRotation, ref rotationVelocity, SlideTime * 1.4f,
                Mathf.Infinity, dt);
            holder.localRotation = Quaternion.Euler(0, 0, rotation);
            float scale = Mathf.MoveTowards(holder.localScale.x, cameraMode ? 1.06f : 1f, dt * 2f);
            holder.localScale = new Vector3(scale, scale, 1f);
            hint.enabled = IsOpen;

            if (!IsOpen && holder.anchoredPosition.y < HiddenPosition.y + 40f)
            {
                current.Hide();
                holder.gameObject.SetActive(false);
            }
        }

        // ---------- notifications ----------

        public void Toast(string text, float seconds = 2.2f)
        {
            toastText.text = text;
            toastUntil = Time.unscaledTime + seconds;
        }

        // A message from the game world: a banner when the phone is in the pocket, a toast otherwise.
        public void Notify(string title, string body, string icon)
        {
            audioSource.PlayOneShot(notifyClip, 0.6f);
            if (IsOpen)
            {
                Toast(title + ": " + body, 3f);
                return;
            }
            bannerIcon.sprite = PhoneUi.Icon(icon);
            bannerTitle.text = title;
            bannerBody.text = body;
            bannerUntil = Time.unscaledTime + 4.5f;
        }

        public void PlayShutter() => audioSource.PlayOneShot(shutterClip, 0.8f);
        public void PlayTap() => audioSource.PlayOneShot(tapClip, 0.5f);

        private void UpdateToastAndBanner()
        {
            float alpha = Mathf.Clamp01((toastUntil - Time.unscaledTime) * 4f);
            toastPanel.gameObject.SetActive(alpha > 0f);
            toastPanel.color = new Color(0.07f, 0.07f, 0.09f, 0.88f * alpha);
            toastText.color = new Color(1, 1, 1, alpha);

            bool showBanner = !IsOpen && Time.unscaledTime < bannerUntil;
            float x = Mathf.MoveTowards(banner.anchoredPosition.x, showBanner ? -230f : 260f,
                Time.unscaledDeltaTime * 2600f);
            banner.anchoredPosition = new Vector2(x, banner.anchoredPosition.y);
            banner.gameObject.SetActive(x < 255f);
        }

        // ---------- construction ----------

        private void EnsureEventSystem()
        {
            if (EventSystem.current != null || FindAnyObjectByType<EventSystem>() != null)
                return;
            ownedEventSystem = new GameObject("[Phone] EventSystem", typeof(EventSystem),
                typeof(StandaloneInputModule));
        }

        private void BuildFrame()
        {
            gameObject.layer = 5;
            var canvas = gameObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 60;
            var scaler = gameObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 1f;
            gameObject.AddComponent<GraphicRaycaster>();

            holder = PhoneUi.Rect("Phone", transform);
            holder.anchorMin = holder.anchorMax = new Vector2(0.5f, 0f);
            holder.pivot = new Vector2(0.5f, 0f);
            holder.sizeDelta = new Vector2(PhoneLayout.Width + Frame * 2, PhoneLayout.Height + Frame * 2);

            // Silver metal frame with a light bevel, side buttons, thin black bezel.
            Color steel = PhoneUi.Hex("#A7ACB3");
            PhoneUi.Panel(holder, "VolumeUp", steel, 3).rectTransform
                .Place(new Vector2(0, 0.78f), new Vector2(-1, 0), new Vector2(8, 58));
            PhoneUi.Panel(holder, "VolumeDown", steel, 3).rectTransform
                .Place(new Vector2(0, 0.69f), new Vector2(-1, 0), new Vector2(8, 58));
            PhoneUi.Panel(holder, "Power", steel, 3).rectTransform
                .Place(new Vector2(1, 0.72f), new Vector2(1, 0), new Vector2(8, 96));
            PhoneUi.Panel(holder, "Rim", PhoneUi.Hex("#8E949C"), 64).rectTransform.Stretch();
            PhoneUi.Panel(holder, "RimLight", PhoneUi.Hex("#E6E8EB"), 62).rectTransform.Stretch(1.5f, 1.5f, 1.5f, 1.5f);
            PhoneUi.Panel(holder, "RimBody", PhoneUi.Hex("#BCC0C6"), 61).rectTransform.Stretch(3, 3, 3, 3);
            PhoneUi.Panel(holder, "Bezel", PhoneUi.Hex("#08080A"), 58).rectTransform.Stretch(7, 7, 7, 7);

            var screenImage = PhoneUi.Panel(holder, "Screen", Color.black, 48);
            screen = screenImage.rectTransform.Stretch(Frame, Frame, Frame, Frame);
            screen.gameObject.AddComponent<Mask>().showMaskGraphic = true;

            var wallpaper = PhoneUi.Picture(screen, "Wallpaper", PhoneUi.Icon("wallpaper"));
            wallpaper.preserveAspect = false;
            wallpaper.rectTransform.Stretch();
            appLayer = PhoneUi.Rect("Apps", screen).Stretch();

            BuildStatusBar();
            PhoneUi.Panel(screen, "Island", PhoneUi.Hex("#030304"), 14).rectTransform
                .Place(new Vector2(0.5f, 1), new Vector2(0, -17), new Vector2(96, 27));

            toastPanel = PhoneUi.Panel(screen, "Toast", Color.black, 20);
            toastPanel.rectTransform.Place(new Vector2(0.5f, 0), new Vector2(0, 92), new Vector2(330, 44));
            toastText = PhoneUi.Label(toastPanel.transform, "", 15, Color.white, TextAnchor.MiddleCenter);
            toastText.rectTransform.Stretch(12, 0, 12, 0);
            toastPanel.gameObject.SetActive(false);

            var homeBar = PhoneUi.HitArea(screen, "HomeBar", () => { if (current != Home) GoHome(); });
            ((RectTransform)homeBar.transform).Place(new Vector2(0.5f, 0), new Vector2(0, 12), new Vector2(180, 24));
            PhoneUi.Panel(homeBar.transform, "Pill", new Color(1, 1, 1, 0.8f), 3).rectTransform
                .Place(new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(124, 5));

            hint = PhoneUi.Label(transform, "", 17, new Color(1, 1, 1, 0.9f), TextAnchor.MiddleCenter);
            hint.rectTransform.Place(new Vector2(0.5f, 0), new Vector2(560, 18), new Vector2(560, 28));
            hint.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(1.5f, -1.5f);
            hint.enabled = false;
            hint.transform.SetAsFirstSibling();

            BuildBanner();
        }

        private void BuildStatusBar()
        {
            var bar = PhoneUi.Rect("StatusBar", screen).Top(0, PhoneLayout.StatusHeight + 4);
            clock = PhoneUi.Label(bar, "12:00", 15, Color.white, TextAnchor.MiddleLeft, true);
            clock.rectTransform.Stretch(34, 4, 0, 0);
        }

        private void BuildBanner()
        {
            var panel = PhoneUi.Panel(transform, "Banner", PhoneUi.Hex("#15161A", 0.94f), 22);
            banner = panel.rectTransform;
            banner.anchorMin = banner.anchorMax = new Vector2(1, 0);
            banner.pivot = new Vector2(0.5f, 0);
            banner.sizeDelta = new Vector2(400, 86);
            banner.anchoredPosition = new Vector2(260f, 70f);
            bannerIcon = PhoneUi.Picture(banner, "Icon", PhoneUi.Icon("app_messages"));
            bannerIcon.rectTransform.Place(new Vector2(0, 0.5f), new Vector2(42, 0), new Vector2(52, 52));
            bannerTitle = PhoneUi.Label(banner, "", 18, Color.white, TextAnchor.MiddleLeft, true);
            bannerTitle.rectTransform.Top(12, 26, 80, 70);
            bannerBody = PhoneUi.Label(banner, "", 15, new Color(1, 1, 1, 0.78f), TextAnchor.UpperLeft);
            bannerBody.rectTransform.Top(40, 40, 80, 16);
            var key = PhoneUi.Panel(banner, "Key", new Color(1, 1, 1, 0.16f), 6);
            key.rectTransform.Place(new Vector2(1, 1), new Vector2(-38, -24), new Vector2(50, 24));
            PhoneUi.Label(key.transform, "TAB", 12, Color.white, TextAnchor.MiddleCenter, true)
                .rectTransform.Stretch();
            banner.gameObject.SetActive(false);
        }

        private void BuildAudio()
        {
            audioSource = gameObject.AddComponent<AudioSource>();
            audioSource.playOnAwake = false;
            audioSource.spatialBlend = 0f;
            var noise = new System.Random(5);
            float lowA = 0f, lowB = 0f;
            shutterClip = Synth("PhoneShutter", 0.32f, t =>
            {
                float n = (float)(noise.NextDouble() * 2.0 - 1.0);
                // Band-passed noise: difference of two one-pole low-passes (~4.5 kHz and ~900 Hz).
                lowA += (n - lowA) * 0.48f;
                lowB += (n - lowB) * 0.12f;
                float band = lowA - lowB;
                float Click(float start, float decay, float pitch, float gain)
                {
                    float u = t - start;
                    if (u < 0f) return 0f;
                    float env = Mathf.Exp(-u / decay);
                    return gain * env * (band * 1.6f + 0.55f * Mathf.Sin(2f * Mathf.PI * pitch * u));
                }
                float u2 = t - 0.085f;
                float body = u2 > 0f ? 0.35f * Mathf.Sin(2f * Mathf.PI * 150f * u2) * Mathf.Exp(-u2 / 0.025f) : 0f;
                float shimmer = 0.06f * band * Mathf.Exp(-t / 0.12f);
                return Mathf.Clamp(Click(0f, 0.006f, 2600f, 0.75f) + Click(0.085f, 0.009f, 1850f, 0.95f) +
                    body + shimmer, -0.95f, 0.95f);
            });
            tapClip = Synth("PhoneTap", 0.03f, t =>
                (float)(noise.NextDouble() * 2.0 - 1.0) * 0.25f * Mathf.Exp(-t * 300f) +
                0.35f * Mathf.Sin(2f * Mathf.PI * 3200f * t) * Mathf.Exp(-t * 220f));
            notifyClip = Synth("PhoneNotify", 0.42f, t =>
            {
                float a = Mathf.Sin(2f * Mathf.PI * 880f * t) * Mathf.Exp(-t * 14f);
                float u = t - 0.11f;
                float b = u > 0f ? Mathf.Sin(2f * Mathf.PI * 1318.5f * u) * Mathf.Exp(-u * 9f) : 0f;
                return (a + b) * 0.3f;
            });
        }

        private static AudioClip Synth(string name, float duration, Func<float, float> wave)
        {
            const int rate = 44100;
            int count = Mathf.CeilToInt(rate * duration);
            var data = new float[count];
            for (int i = 0; i < count; i++)
                data[i] = wave(i / (float)rate);
            var clip = AudioClip.Create(name, count, 1, rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private void OnDestroy()
        {
            if (playerInput != null)
                playerInput.LookSuspended = false;
            foreach (var app in apps)
                app.Dispose();
            Album?.Dispose();
            if (ownedEventSystem != null)
                Destroy(ownedEventSystem);
            if (shutterClip != null) Destroy(shutterClip);
            if (notifyClip != null) Destroy(notifyClip);
            if (tapClip != null) Destroy(tapClip);
        }
    }
}
