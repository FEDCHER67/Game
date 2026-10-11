using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Chats with quick replies. The scrap buyer (canon §51–52) can be called; nobody spawns yet.
    public sealed class MessagesApp : PhoneApp
    {
        private const float ActionHeight = 96f;
        private const float BuyerTravelSeconds = 45f;
        private const float BuyerPatienceSeconds = 40f;
        private static readonly Color Green = PhoneUi.Hex("#1F9D55");
        private static readonly Regex Tags = new("<.*?>");

        private enum Kind { Buyer, Request, Grandpa, Mom }
        private enum BuyerState { Idle, Answering, OnTheWay, Waiting }

        private sealed class Message
        {
            public bool Mine;
            public bool Card;
            public string Text;
        }

        private sealed class Thread
        {
            public Kind Kind;
            public string Name;
            public string Initial;
            public Color Color;
            public int Unread;
            public bool Typing;
            public bool Asked;
            public readonly List<Message> Messages = new();
        }

        private readonly List<Thread> threads = new();
        private readonly List<(float time, Action action)> scheduled = new();
        private readonly string[] buyerReplies =
        {
            "On my way. Old van, you know it.",
            "Coming. Don't let it get warm.",
            "10 minutes. Maybe 20. Van is being weird."
        };
        private Thread open;
        private Thread pendingOpen;
        private BuyerState buyer = BuyerState.Idle;
        private float buyerTimer;
        private int replyIndex;

        private Text title;
        private RectTransform listView;
        private RectTransform listContent;
        private RectTransform threadView;
        private ScrollRect chatScroll;
        private RectTransform chatContent;
        private RectTransform actionBar;
        private Text buyerButtonLabel;
        private Button buyerButton;
        private int scrollFrames;

        public bool RequestAnswered { get; private set; }
        // Newest incoming message, shown on the home screen notification card.
        public string LatestThread { get; private set; } = "Mom";
        public string LatestText { get; private set; } = "";
        public override string Title => "Messages";
        public override string IconName => "app_messages";

        public override int Badge
        {
            get
            {
                int sum = 0;
                foreach (var thread in threads) sum += thread.Unread;
                return sum;
            }
        }

        public MessagesApp()
        {
            var scrap = AddThread(Kind.Buyer, "Scrap Guy", "S", "#FF8A3D");
            Them(scrap, "Got stuff? I take everything. Bad prices, fast pickup.");
            scrap.Unread = 1;
            var request = AddThread(Kind.Request, "Unknown number", "?", "#2B2D33");
            request.Messages.Add(new Message
            {
                Card = true,
                Text = "<color=#FFC23D><b>PRIVATE REQUEST</b></color>\nHeart\nO−\nPerfect+\nOffer: <b>$25,000</b>"
            });
            request.Unread = 1;
            var grandpa = AddThread(Kind.Grandpa, "Grandpa (van)", "G", "#8D6E63");
            Them(grandpa, "The van is still for sale. Cash only.");
            var mom = AddThread(Kind.Mom, "Mom", "M", "#E0457B");
            Them(mom, "Are you eating? Kevin's mom says he got a job. Did YOU get a job?");
            LatestText = mom.Messages[0].Text;
            mom.Unread = 1;
        }

        private Thread AddThread(Kind kind, string name, string initial, string color)
        {
            var thread = new Thread { Kind = kind, Name = name, Initial = initial, Color = PhoneUi.Hex(color) };
            threads.Add(thread);
            return thread;
        }

        private static void Them(Thread thread, string text) =>
            thread.Messages.Add(new Message { Text = text });

        // ---------- UI ----------

        protected override void Build(RectTransform root)
        {
            PhoneUi.Panel(root, "Background", Color.white).rectTransform.Stretch();
            listView = PhoneUi.Rect("List", root).Stretch(0, PhoneLayout.HeaderHeight, 0, 0);
            PhoneUi.Scroll(listView, "Threads", out listContent).GetComponent<RectTransform>().Stretch();

            threadView = PhoneUi.Rect("Thread", root).Stretch(0, PhoneLayout.HeaderHeight, 0, 0);
            PhoneUi.Panel(threadView, "ChatBackground", PhoneUi.Hex("#EEE8DF")).rectTransform.Stretch();
            chatScroll = PhoneUi.Scroll(threadView, "Chat", out chatContent, 8, new RectOffset(0, 0, 14, 14));
            chatScroll.GetComponent<RectTransform>().Stretch(0, 0, 0, ActionHeight);
            var bar = PhoneUi.Panel(threadView, "Actions", Color.white);
            actionBar = bar.rectTransform.Bottom(0, ActionHeight);
            PhoneUi.Panel(actionBar, "Line", PhoneUi.Hex("#E2E2E2")).rectTransform.Top(0, 1);

            title = PhoneUi.Header(root, Title, Green, out _, Phone.Back);
            threadView.gameObject.SetActive(false);
        }

        public MessagesApp OpenThread(string name)
        {
            pendingOpen = threads.Find(t => t.Name == name);
            if (Root.gameObject.activeSelf && pendingOpen != null)
            {
                ShowThread(pendingOpen);
                pendingOpen = null;
            }
            return this;
        }

        public override void Show()
        {
            base.Show();
            if (pendingOpen != null)
                ShowThread(pendingOpen);
            else if (open != null)
                ShowThread(open);
            else
                ShowList();
            pendingOpen = null;
        }

        public override bool Back()
        {
            if (open == null)
                return false;
            ShowList();
            return true;
        }

        private void ShowList()
        {
            open = null;
            threadView.gameObject.SetActive(false);
            listView.gameObject.SetActive(true);
            title.text = Title;
            PhoneUi.Clear(listContent);
            foreach (var thread in threads)
                BuildRow(thread);
        }

        private void BuildRow(Thread thread)
        {
            var row = PhoneUi.Button(listContent, "Row_" + thread.Name, Color.white, 0, () => ShowThread(thread));
            PhoneUi.Height(row.gameObject, 78);
            var avatar = PhoneUi.Panel(row.transform, "Avatar", thread.Color);
            avatar.sprite = PhoneUi.Circle;
            avatar.rectTransform.Place(new Vector2(0, 0.5f), new Vector2(42, 0), new Vector2(50, 50));
            PhoneUi.Label(avatar.transform, thread.Initial, 22, Color.white, TextAnchor.MiddleCenter, false, true)
                .rectTransform.Stretch();
            PhoneUi.Label(row.transform, thread.Name, 17, PhoneUi.Ink, TextAnchor.MiddleLeft, true)
                .rectTransform.Top(14, 24, 80, 50);
            var last = thread.Messages[thread.Messages.Count - 1];
            string preview = Tags.Replace(last.Text, "").Replace("\n", " · ");
            var previewLabel = PhoneUi.Label(row.transform, (last.Mine ? "You: " : "") + preview, 14,
                PhoneUi.Muted, TextAnchor.MiddleLeft);
            previewLabel.verticalOverflow = VerticalWrapMode.Truncate;
            previewLabel.rectTransform.Top(40, 22, 80, 50);
            if (thread.Unread > 0)
            {
                var dot = PhoneUi.Panel(row.transform, "Unread", PhoneUi.Hex("#25C26A"));
                dot.sprite = PhoneUi.Circle;
                dot.rectTransform.Place(new Vector2(1, 0.5f), new Vector2(-28, 0), new Vector2(24, 24));
                PhoneUi.Label(dot.transform, thread.Unread.ToString(), 13, Color.white, TextAnchor.MiddleCenter, true)
                    .rectTransform.Stretch();
            }
            PhoneUi.Panel(row.transform, "Line", PhoneUi.Hex("#EDEDED")).rectTransform.Bottom(0, 1, 80, 0);
        }

        private void ShowThread(Thread thread)
        {
            open = thread;
            thread.Unread = 0;
            listView.gameObject.SetActive(false);
            threadView.gameObject.SetActive(true);
            title.text = thread.Name;
            RebuildChat();
            RebuildActions();
        }

        private void RebuildChat()
        {
            PhoneUi.Clear(chatContent);
            foreach (var message in open.Messages)
                AddBubble(message.Text, message.Mine, message.Card);
            if (open.Typing)
                AddBubble("• • •", false, false);
            scrollFrames = 3;
        }

        private void AddBubble(string text, bool mine, bool card)
        {
            var row = PhoneUi.Rect("Row", chatContent);
            var layout = row.gameObject.AddComponent<HorizontalLayoutGroup>();
            layout.childAlignment = mine ? TextAnchor.UpperRight : TextAnchor.UpperLeft;
            layout.padding = new RectOffset(12, 12, 0, 0);
            layout.childControlWidth = layout.childControlHeight = true;
            layout.childForceExpandWidth = layout.childForceExpandHeight = false;

            Color fill = card ? PhoneUi.Hex("#1B1B22") : mine ? PhoneUi.Hex("#D3F8C4") : Color.white;
            // The rounded fill sits on a child that ignores layout, so only the text sizes the bubble.
            var bubble = PhoneUi.Rect("Bubble", row);
            var background = PhoneUi.Panel(bubble, "Fill", fill, 16);
            background.rectTransform.Stretch();
            background.gameObject.AddComponent<LayoutElement>().ignoreLayout = true;
            var inner = bubble.gameObject.AddComponent<VerticalLayoutGroup>();
            inner.padding = new RectOffset(14, 14, 9, 10);
            inner.childControlWidth = inner.childControlHeight = true;
            inner.childForceExpandWidth = true;
            inner.childForceExpandHeight = false;
            var label = PhoneUi.Label(bubble.transform, text, card ? 17 : 16, card ? Color.white : PhoneUi.Ink,
                TextAnchor.UpperLeft);
            if (card)
                label.lineSpacing = 1.15f;
            var element = bubble.gameObject.AddComponent<LayoutElement>();
            element.preferredWidth = Mathf.Min(label.preferredWidth, 250f) + 30f;
            element.flexibleWidth = 0f;
        }

        private void RebuildActions()
        {
            for (int i = actionBar.childCount - 1; i >= 1; i--)
                UnityEngine.Object.Destroy(actionBar.GetChild(i).gameObject);
            buyerButton = null;
            buyerButtonLabel = null;
            switch (open.Kind)
            {
                case Kind.Buyer:
                    buyerButton = ActionButton("CALL BUYER", Green, 0, 1, CallBuyer);
                    buyerButtonLabel = buyerButton.GetComponentInChildren<Text>();
                    UpdateBuyerButton();
                    break;
                case Kind.Request when !RequestAnswered:
                    ActionButton("Deal", Green, 0, 2, () => AnswerRequest(true));
                    ActionButton("Not now", PhoneUi.Hex("#9AA0A8"), 1, 2, () => AnswerRequest(false));
                    break;
                case Kind.Grandpa when !open.Asked:
                    ActionButton("Still selling the van?", PhoneUi.Hex("#8D6E63"), 0, 1, () =>
                        Say(open, "Still selling the van?", 2.2f, "Yes. $4,000. Cash only. Don't ask about the smell."));
                    break;
                case Kind.Mom when !open.Asked:
                    ActionButton("I volunteer now.", PhoneUi.Hex("#E0457B"), 0, 1, () =>
                        Say(open, "I volunteer now.", 2.6f, "Proud of you sweetie! Eat something."));
                    break;
                default:
                    var note = PhoneUi.Label(actionBar, "No quick replies", 14, PhoneUi.Muted, TextAnchor.MiddleCenter);
                    note.rectTransform.Stretch();
                    break;
            }
        }

        private Button ActionButton(string text, Color color, int index, int count, UnityEngine.Events.UnityAction click)
        {
            var button = PhoneUi.TextButton(actionBar, text, color, Color.white, 17, 26, click);
            var rect = (RectTransform)button.transform;
            float width = (PhoneLayout.Width - 28f - (count - 1) * 10f) / count;
            rect.anchorMin = rect.anchorMax = new Vector2(0, 0.5f);
            rect.pivot = new Vector2(0, 0.5f);
            rect.sizeDelta = new Vector2(width, 54);
            rect.anchoredPosition = new Vector2(14 + index * (width + 10f), 0);
            return button;
        }

        // ---------- conversation logic ----------

        private void Say(Thread thread, string mine, float delay, string reply, Action after = null)
        {
            thread.Asked = true;
            thread.Messages.Add(new Message { Mine = true, Text = mine });
            Reply(thread, delay, reply, after);
            Refresh(thread);
        }

        private void Reply(Thread thread, float delay, string text, Action after = null)
        {
            float now = Time.unscaledTime;
            scheduled.Add((now + Mathf.Max(0.3f, delay - 1.2f), () => { thread.Typing = true; Refresh(thread); }));
            scheduled.Add((now + delay, () =>
            {
                thread.Typing = false;
                Receive(thread, text);
                after?.Invoke();
            }));
        }

        private void Receive(Thread thread, string text)
        {
            Them(thread, text);
            LatestThread = thread.Name;
            LatestText = text;
            bool reading = Phone.IsOpen && Root.gameObject.activeInHierarchy && open == thread;
            if (!reading)
            {
                thread.Unread++;
                Phone.Notify(thread.Name, text, IconName);
            }
            Refresh(thread);
        }

        private void Refresh(Thread thread)
        {
            if (!Root.gameObject.activeInHierarchy)
                return;
            if (open == thread)
            {
                RebuildChat();
                RebuildActions();
            }
            else if (open == null)
                ShowList();
        }

        private void CallBuyer()
        {
            if (buyer != BuyerState.Idle)
                return;
            var scrap = threads[0];
            buyer = BuyerState.Answering;
            scrap.Messages.Add(new Message { Mine = true, Text = "Got stock." });
            Reply(scrap, 1.8f, "I'll take whatever you have.");
            Reply(scrap, 3.6f, buyerReplies[replyIndex++ % buyerReplies.Length], () =>
            {
                buyer = BuyerState.OnTheWay;
                buyerTimer = BuyerTravelSeconds;
                Refresh(scrap);
            });
            Refresh(scrap);
        }

        private void AnswerRequest(bool deal)
        {
            RequestAnswered = true;
            var thread = threads[1];
            Say(thread, deal ? "Deal." : "Not now.", 2.4f, deal
                ? "Fresh. Perfect+. Bench by the park. Come alone."
                : "Offer stands. For now.");
        }

        private void UpdateBuyerButton()
        {
            if (buyerButton == null)
                return;
            buyerButton.interactable = buyer == BuyerState.Idle;
            buyerButtonLabel.text = buyer switch
            {
                BuyerState.Answering => "CALLING…",
                BuyerState.OnTheWay => "ON THE WAY · " + Clock(buyerTimer),
                BuyerState.Waiting => "HE'S WAITING · " + Clock(buyerTimer),
                _ => "CALL BUYER"
            };
        }

        private static string Clock(float seconds)
        {
            int s = Mathf.Max(0, Mathf.CeilToInt(seconds));
            return (s / 60) + ":" + (s % 60).ToString("00");
        }

        public override void BackgroundTick()
        {
            float now = Time.unscaledTime;
            for (int i = 0; i < scheduled.Count; i++)
            {
                if (scheduled[i].time > now)
                    continue;
                var action = scheduled[i].action;
                scheduled.RemoveAt(i--);
                action();
            }

            if (buyer != BuyerState.OnTheWay && buyer != BuyerState.Waiting)
                return;
            buyerTimer -= Time.unscaledDeltaTime;
            if (buyerTimer > 0f)
                return;
            var scrap = threads[0];
            if (buyer == BuyerState.OnTheWay)
            {
                buyer = BuyerState.Waiting;
                buyerTimer = BuyerPatienceSeconds;
                Receive(scrap, "I'm here. Where's the stuff?");
            }
            else
            {
                buyer = BuyerState.Idle;
                Receive(scrap, "Nobody here. Leaving. Text me when you're serious.");
            }
        }

        public override void Tick()
        {
            UpdateBuyerButton();
            if (scrollFrames > 0 && threadView.gameObject.activeInHierarchy)
            {
                scrollFrames--;
                LayoutRebuilder.ForceRebuildLayoutImmediate(chatContent);
                chatScroll.verticalNormalizedPosition = 0f;
            }
        }
    }
}
