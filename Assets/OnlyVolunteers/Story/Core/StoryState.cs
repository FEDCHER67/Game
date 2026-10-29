using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Story
{
    [Serializable]
    public sealed class StoryFactRecord
    {
        public string key = "";
        public string source = "";
        public double worldHours;
    }

    /// <summary>A retained phone message (spec §2.2): its id is its identity, so a load or a late join shows the same
    /// message once instead of flooding the thread. Informational only: never proof of completion.</summary>
    [Serializable]
    public sealed class StoryMessage
    {
        public string id = "";
        public string thread = "";
        public string text = "";
        public double worldHours;
        public StoryMessage Copy() => (StoryMessage)MemberwiseClone();
    }

    public enum RivalLife { AtLarge = 0, Dead = 1, Resolved = 2 }

    /// <summary>M06 target identity (spec §9): one active generation. A replacement is only made after an authoritative
    /// death (or genuine loss) of the current generation, eligible from the next 06:00 and appearing at the next shift.</summary>
    [Serializable]
    public sealed class RivalTargetSave
    {
        public int generation = 1;
        public int life;
        /// <summary>Absolute world hours (day * 24 + hour) from which the replacement may appear; -1 = none pending.</summary>
        public double replacementFrom = -1;
        public string recovery = "";
        public RivalLife Life { get => (RivalLife)life; set => life = (int)value; }
        public RivalTargetSave Copy() => (RivalTargetSave)MemberwiseClone();
    }

    /// <summary>The story block of the host-world save (inside EconomySaveData.story). JsonUtility-friendly.</summary>
    [Serializable]
    public sealed class StorySaveData
    {
        public int version;
        public List<StoryFactRecord> facts = new List<StoryFactRecord>();
        public List<string> accepted = new List<string>();
        public List<string> receipts = new List<string>();
        public List<string> objectives = new List<string>();
        public List<StoryMessage> messages = new List<StoryMessage>();
        public RivalTargetSave rival = new RivalTargetSave();
    }

    [Serializable]
    public sealed class StoryJournalEntry
    {
        public string id = "";
        public string title = "";
        public int state;
        public int content;
        public string substate = "";
        public List<string> objectives = new List<string>();
        public JournalState State => (JournalState)state;
    }

    /// <summary>What every client sees (inside the economy snapshot): derived journal + retained messages. Display only.</summary>
    [Serializable]
    public sealed class StoryJournalView
    {
        public List<StoryJournalEntry> missions = new List<StoryJournalEntry>();
        public List<StoryMessage> messages = new List<StoryMessage>();
        public string rivalPersonId = "";
        public int rivalGeneration;
        public int rivalLife;
    }

    /// <summary>
    /// Server-side story state of one team world (pure C#): committed facts, accepted missions, objective events committed
    /// once by persistent id, retained messages and the M06 target generation. Journal states are DERIVED from facts on
    /// every read, so a valid early world action reconciles a later formal step (spec §2.1) and a reload cannot replay
    /// anything. The owner (EconomyState) commits it in the same change as funds / unlock flags and the same save block.
    /// </summary>
    public sealed class StoryState
    {
        public const int Version = 1;
        public const string RivalPersonIdBase = "M06_RIVAL";
        public const int MaxMessages = 120;

        private readonly List<StoryFactRecord> facts = new List<StoryFactRecord>();
        private readonly HashSet<string> accepted = new HashSet<string>(StringComparer.Ordinal);
        private readonly HashSet<string> receipts = new HashSet<string>(StringComparer.Ordinal);
        private readonly HashSet<string> objectives = new HashSet<string>(StringComparer.Ordinal);
        private readonly List<StoryMessage> messages = new List<StoryMessage>();

        public RivalTargetSave Rival { get; private set; } = new RivalTargetSave();
        public IReadOnlyList<StoryFactRecord> Facts => facts;
        public IReadOnlyList<StoryMessage> Messages => messages;

        public bool HasFact(string key) => facts.Exists(f => f.key == key);
        public string FactSource(string key) => facts.Find(f => f.key == key)?.source ?? "";
        public bool IsAccepted(MissionId id) => accepted.Contains(id.ToString());
        public bool HasReceipt(string key) => !string.IsNullOrEmpty(key) && receipts.Contains(key);
        public bool ObjectiveDone(MissionId id, string objective) => objectives.Contains(id + "/" + objective);

        /// <summary>Commits a fact once; false = it was already there (the first source stands).</summary>
        public bool AddFact(string key, string source, double worldHours)
        {
            if (string.IsNullOrEmpty(key) || HasFact(key)) return false;
            facts.Add(new StoryFactRecord { key = key, source = source ?? "", worldHours = worldHours });
            return true;
        }

        /// <summary>An event id committed once (objective events, hand-ins, acquaintance); false = already committed.</summary>
        public bool CommitReceipt(string key) => !string.IsNullOrEmpty(key) && receipts.Add(key);

        public bool MarkObjective(MissionId id, string objective) => !string.IsNullOrEmpty(objective) && objectives.Add(id + "/" + objective);

        /// <summary>Retains one message by id (a repeat of the same id is ignored: no thread flood on load / replays).</summary>
        public bool PostMessage(string id, string thread, string text, double worldHours)
        {
            if (string.IsNullOrEmpty(id) || messages.Exists(m => m.id == id)) return false;
            messages.Add(new StoryMessage { id = id, thread = thread ?? "", text = text ?? "", worldHours = worldHours });
            if (messages.Count > MaxMessages) messages.RemoveRange(0, messages.Count - MaxMessages);
            // The receipt keeps the identity even after the visible list is trimmed (spec §17.1: history trimming erases nothing).
            receipts.Add("msg:" + id);
            return true;
        }

        public bool MessageDelivered(string id) => receipts.Contains("msg:" + id);

        public JournalState StateOf(MissionId id)
        {
            MissionDef def = StoryMissions.Get(id);
            if (HasFact(def.Completes)) return JournalState.Completed;
            foreach (string need in def.Requires) if (!HasFact(need)) return JournalState.Locked;
            if (def.RequiresAcceptance && !IsAccepted(id)) return JournalState.Offered;
            return JournalState.Active;
        }

        /// <summary>Accepts an Offered mission once (any participant, no vote). Accepting again is a harmless replay.</summary>
        public bool Accept(MissionId id)
        {
            if (StateOf(id) != JournalState.Offered) return false;
            accepted.Add(id.ToString());
            return true;
        }

        // ---------- M06 target ----------

        public string RivalPersonId => PersonIdFor(Rival.generation);
        public static string PersonIdFor(int generation) => generation <= 1 ? RivalPersonIdBase : RivalPersonIdBase + "_G" + generation;
        public static bool IsRivalPersonId(string id) => !string.IsNullOrEmpty(id) && (id == RivalPersonIdBase || id.StartsWith(RivalPersonIdBase + "_G", StringComparison.Ordinal));

        /// <summary>Authoritative death (or genuine loss) of the CURRENT generation before the hand-in: the replacement is
        /// eligible from the next 06:00 (spec §9 recovery). Old generations, a resolved target or a second report are ignored.</summary>
        public bool MarkRivalLost(string personId, double absoluteHours, string reason)
        {
            if (Rival.Life != RivalLife.AtLarge || personId != RivalPersonId || HasFact(StoryFacts.RivalDelivered)) return false;
            Rival.Life = RivalLife.Dead;
            Rival.replacementFrom = RivalRules.NextMorning(absoluteHours);
            Rival.recovery = reason ?? "";
            return true;
        }

        /// <summary>The replacement generation, once, when its time has come (from 06:00 and inside the 08-18 shift).</summary>
        public bool TryAdvanceRivalGeneration(double absoluteHours)
        {
            if (Rival.Life != RivalLife.Dead || Rival.replacementFrom < 0 || absoluteHours < Rival.replacementFrom) return false;
            if (!RivalRules.OnShift(RivalRules.HourOfDay(absoluteHours))) return false;
            Rival.generation++;
            Rival.Life = RivalLife.AtLarge;
            Rival.replacementFrom = -1;
            return true;
        }

        public void MarkRivalResolved() => Rival.Life = RivalLife.Resolved;

        // ---------- journal ----------

        public StoryJournalView ToJournal(int messageCount)
        {
            var view = new StoryJournalView { rivalPersonId = RivalPersonId, rivalGeneration = Rival.generation, rivalLife = Rival.life };
            foreach (MissionDef def in StoryMissions.All)
            {
                JournalState s = StateOf(def.Id);
                var e = new StoryJournalEntry { id = def.Id.ToString(), title = def.Title, state = (int)s, content = (int)def.Content, substate = Substate(def, s) };
                foreach (ObjectiveDef o in def.Objectives) e.objectives.Add((ObjectiveDone(def.Id, o.Id) || s == JournalState.Completed ? "✓ " : "• ") + o.Text);
                view.missions.Add(e);
            }
            for (int i = Math.Max(0, messages.Count - messageCount); i < messages.Count; i++) view.messages.Add(messages[i].Copy());
            return view;
        }

        private string Substate(MissionDef def, JournalState s)
        {
            string content = def.Content == ContentStatus.Playable ? "" : StoryMissions.ContentName(def.Content) + ". ";
            if (s == JournalState.Completed)
            {
                string src = FactSource(def.Completes);
                return content + (src == StoryFacts.SourceBuildProvided ? "Засчитано по факту сборки: " + def.Note : "");
            }
            if (s == JournalState.Locked)
            {
                var missing = new List<string>();
                foreach (string need in def.Requires) if (!HasFact(need)) missing.Add(need);
                return content + "Ждёт: " + string.Join(", ", missing);
            }
            if (def.Id == MissionId.M06 && s == JournalState.Active)
            {
                if (Rival.Life == RivalLife.Dead) return "Восстановление: " + (Rival.recovery.Length > 0 ? Rival.recovery + ". " : "") +
                    "Замена появится у навеса со следующего утра (с 06:00, в смену 08:00–18:00)";
                return "Цель: " + RivalPersonId + (Rival.generation > 1 ? " (замена " + Rival.generation + ")" : "");
            }
            return content + def.Note;
        }

        // ---------- save ----------

        public StorySaveData ToSave()
        {
            var data = new StorySaveData { version = Version, rival = Rival.Copy() };
            foreach (StoryFactRecord f in facts) data.facts.Add(new StoryFactRecord { key = f.key, source = f.source, worldHours = f.worldHours });
            data.accepted.AddRange(accepted);
            data.receipts.AddRange(receipts);
            data.objectives.AddRange(objectives);
            foreach (StoryMessage m in messages) data.messages.Add(m.Copy());
            return data;
        }

        /// <summary>null / version 0 = a save written before the story block: an empty story (facts are then reconciled
        /// from the world by the owner, never invented from a dummy figure).</summary>
        public static StoryState FromSave(StorySaveData data)
        {
            var s = new StoryState();
            if (data == null || data.version < 1) return s;
            if (data.facts != null) foreach (StoryFactRecord f in data.facts) if (f != null) s.AddFact(f.key, f.source, f.worldHours);
            if (data.accepted != null) foreach (string a in data.accepted) if (!string.IsNullOrEmpty(a)) s.accepted.Add(a);
            if (data.receipts != null) foreach (string r in data.receipts) if (!string.IsNullOrEmpty(r)) s.receipts.Add(r);
            if (data.objectives != null) foreach (string o in data.objectives) if (!string.IsNullOrEmpty(o)) s.objectives.Add(o);
            if (data.messages != null) foreach (StoryMessage m in data.messages) if (m != null && !string.IsNullOrEmpty(m.id) && !s.messages.Exists(x => x.id == m.id)) s.messages.Add(m.Copy());
            s.Rival = data.rival != null ? data.rival.Copy() : new RivalTargetSave();
            if (s.Rival.generation < 1) s.Rival.generation = 1;
            return s;
        }
    }
}
