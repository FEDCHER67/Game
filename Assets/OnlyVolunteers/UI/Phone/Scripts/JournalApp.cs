using System.Collections.Generic;
using System.Text;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Story;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // STORY_MISSIONS_SPEC v01 §2.2 / §17: the team journal on the existing phone. Display only: it reads the host's
    // snapshot (EconomyClientView.Current.journal, also sent to a late joiner on Hello) — four states Locked / Offered /
    // Active / Completed with the objective substate (waiting, recovery, "content not implemented"), and the retained story
    // messages (by id, so a load does not flood the list). Nothing here completes a mission; actions happen in the world.
    public sealed class JournalApp : PhoneApp
    {
        private enum Tab { Missions, Messages }

        private static readonly Color Header = PhoneUi.Hex("#5A3E8C");
        private static readonly Color Grey = PhoneUi.Hex("#9AA0A8");

        private Tab tab = Tab.Missions;
        private RectTransform list;
        private Text subtitle;
        private readonly List<(Tab tab, Image image)> tabButtons = new();
        private string builtSignature = "";
        private int seenMessages;

        public override string Title => "Задания";
        // Placeholder icon (no journal icon art yet): the news icon.
        public override string IconName => "app_news";

        public override int Badge
        {
            get
            {
                var j = EconomyClientView.Current?.journal;
                int n = j != null && j.messages != null ? j.messages.Count : 0;
                return Mathf.Max(0, n - seenMessages);
            }
        }

        protected override void Build(RectTransform root)
        {
            const float top = PhoneLayout.HeaderHeight;
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#F1EFF5")).rectTransform.Stretch();
            var tabs = new List<(Tab, string)> { (Tab.Missions, "Задания"), (Tab.Messages, "Сообщения") };
            float width = (PhoneLayout.Width - 28f - (tabs.Count - 1) * 6f) / tabs.Count;
            for (int i = 0; i < tabs.Count; i++)
            {
                Tab t = tabs[i].Item1;
                var button = PhoneUi.TextButton(root, tabs[i].Item2, Grey, Color.white, 14, 16, () => { tab = t; Rebuild(); });
                var rect = (RectTransform)button.transform;
                rect.anchorMin = rect.anchorMax = new Vector2(0, 1);
                rect.pivot = new Vector2(0, 1);
                rect.sizeDelta = new Vector2(width, 38);
                rect.anchoredPosition = new Vector2(14 + i * (width + 6f), -(top + 10));
                tabButtons.Add((t, (Image)button.targetGraphic));
            }
            var scroll = PhoneUi.Scroll(root, "List", out list, 8, new RectOffset(14, 14, 4, 16));
            scroll.GetComponent<RectTransform>().Stretch(0, top + 58, 0, 30);
            PhoneUi.Header(root, Title, Header, out subtitle, Phone.Back);
        }

        public override void Show()
        {
            base.Show();
            builtSignature = "";
            Rebuild();
        }

        public override void Tick()
        {
            if (Signature() != builtSignature) Rebuild();
        }

        private string Signature()
        {
            var s = EconomyClientView.Current;
            var sb = new StringBuilder().Append((int)tab);
            if (s == null || s.journal == null) return sb.Append("|none").ToString();
            foreach (StoryJournalEntry m in s.journal.missions) sb.Append('|').Append(m.state).Append(m.substate.Length).Append(m.objectives.Count);
            sb.Append('|').Append(s.journal.messages.Count).Append(s.journal.messages.Count > 0 ? s.journal.messages[s.journal.messages.Count - 1].id : "");
            return sb.ToString();
        }

        private void Rebuild()
        {
            builtSignature = Signature();
            foreach ((Tab t, Image image) in tabButtons) image.color = t == tab ? Header : Grey;
            PhoneUi.Clear(list);
            var s = EconomyClientView.Current;
            if (s == null || s.journal == null)
            {
                subtitle.text = "Нет игровой сессии";
                Card("Журнал работает в игровой сессии команды (карта, сетевая игра).", "", 60);
                return;
            }
            int done = 0;
            foreach (StoryJournalEntry m in s.journal.missions) if (m.State == JournalState.Completed) done++;
            subtitle.text = "Выполнено " + done + " из " + s.journal.missions.Count;
            if (tab == Tab.Messages) { BuildMessages(s.journal); return; }
            // Active first, then offered, then completed, then locked (spec order within each group).
            foreach (JournalState group in new[] { JournalState.Active, JournalState.Offered, JournalState.Completed, JournalState.Locked })
                foreach (StoryJournalEntry m in s.journal.missions)
                {
                    if (m.State != group) continue;
                    string color = group == JournalState.Active ? "#1F7A3F" : group == JournalState.Offered ? "#C77700" : group == JournalState.Completed ? "#5A6270" : "#9AA0A8";
                    var body = new StringBuilder();
                    body.Append("<color=").Append(color).Append('>').Append(StoryMissions.StateName(m.State)).Append("</color>");
                    if (m.substate.Length > 0) body.Append(" · ").Append(m.substate);
                    if (group == JournalState.Active || group == JournalState.Offered)
                        foreach (string o in m.objectives) body.Append('\n').Append(o);
                    string text = body.ToString();
                    Card("<b>" + m.id + " — " + m.title + "</b>", text, 44f + 16f * Mathf.Ceil(text.Length / 40f) + 6f * m.objectives.Count);
                }
        }

        private void BuildMessages(StoryJournalView journal)
        {
            seenMessages = journal.messages.Count;
            if (journal.messages.Count == 0) { Card("Сообщений пока нет.", "", 52); return; }
            for (int i = journal.messages.Count - 1; i >= 0; i--)
            {
                StoryMessage m = journal.messages[i];
                Card("<b>" + m.thread + "</b>", m.text, 40f + 16f * Mathf.Ceil(m.text.Length / 40f));
            }
        }

        private void Card(string title, string body, float height)
        {
            var row = PhoneUi.Panel(list, "Card", Color.white, 14);
            PhoneUi.Height(row.gameObject, Mathf.Max(52f, height));
            PhoneUi.Label(row.transform, title, 14, PhoneUi.Ink, TextAnchor.UpperLeft, true).rectTransform.Top(8, 20, 14, 14);
            if (body.Length == 0) return;
            var detail = PhoneUi.Label(row.transform, body, 12, PhoneUi.Muted, TextAnchor.UpperLeft);
            detail.supportRichText = true;
            detail.rectTransform.Top(30, Mathf.Max(20f, height - 36f), 14, 14);
        }
    }
}
