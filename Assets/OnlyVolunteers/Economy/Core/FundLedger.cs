using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Economy
{
    /// <summary>One line of the team's money history (the phone shows these). amount is signed: + income, − spend,
    /// 0 for a system note (e.g. "no saved money found" at migration).</summary>
    [Serializable]
    public sealed class FundEntry
    {
        public string key = "";
        public string kind = "";
        public string title = "";
        public int amount;
        public int balanceAfter;
        public long seq;
        public double worldHours;

        public FundEntry Copy() => (FundEntry)MemberwiseClone();
    }

    public enum FundStatus { Committed, Duplicate, Insufficient, Invalid }

    public readonly struct FundResult
    {
        public readonly FundStatus Status;
        public readonly int Balance;
        public readonly FundEntry Entry;

        public FundResult(FundStatus status, int balance, FundEntry entry)
        {
            Status = status;
            Balance = balance;
            Entry = entry;
        }

        /// <summary>The money moved (now or, for a duplicate key, the first time): the caller may act on it.</summary>
        public bool Ok => Status == FundStatus.Committed || Status == FundStatus.Duplicate;
        public bool Replayed => Status == FundStatus.Duplicate;
    }

    /// <summary>
    /// The team's ONE shared fund (ECONOMY spec §3.1, §10.1): a balance that never goes negative, a short visible history
    /// (at most HistoryLimit lines) and the set of committed transaction keys. A key commits once: repeating it is a no-op
    /// that answers "duplicate" (the first outcome stands), also after the line has dropped out of the visible history
    /// (§10.4: clearing the feed never removes the protection). Refusals are not recorded, so a refused key may be retried.
    /// Pure C#: the server owns one instance (TeamEconomy); tests drive it directly.
    /// </summary>
    public sealed class FundLedger
    {
        public const int HistoryLimit = 200;

        private readonly List<FundEntry> history = new List<FundEntry>();
        private readonly HashSet<string> committed = new HashSet<string>(StringComparer.Ordinal);

        public int Balance { get; private set; }
        public long Seq { get; private set; }
        /// <summary>World game hours stamped on new lines (EconomyState keeps it current).</summary>
        public double Now { get; set; }
        /// <summary>Oldest first.</summary>
        public IReadOnlyList<FundEntry> History => history;
        public IEnumerable<string> CommittedKeys => committed;
        public int CommittedCount => committed.Count;

        public event Action<FundEntry> Committed;

        public bool IsCommitted(string key) => !string.IsNullOrEmpty(key) && committed.Contains(key);

        public FundResult Credit(int amount, string kind, string title, string key)
        {
            if (amount <= 0 || string.IsNullOrEmpty(key)) return new FundResult(FundStatus.Invalid, Balance, null);
            if (committed.Contains(key)) return new FundResult(FundStatus.Duplicate, Balance, Find(key));
            Balance = (int)Math.Min(int.MaxValue, (long)Balance + amount);
            return new FundResult(FundStatus.Committed, Balance, Commit(key, kind, title, amount));
        }

        public FundResult TryCharge(int amount, string kind, string title, string key)
        {
            if (amount <= 0 || string.IsNullOrEmpty(key)) return new FundResult(FundStatus.Invalid, Balance, null);
            if (committed.Contains(key)) return new FundResult(FundStatus.Duplicate, Balance, Find(key));
            if (amount > Balance) return new FundResult(FundStatus.Insufficient, Balance, null);
            Balance -= amount;
            return new FundResult(FundStatus.Committed, Balance, Commit(key, kind, title, -amount));
        }

        /// <summary>A zero-amount system line (migration notes, story / progression events). Commits its key once too.</summary>
        public FundResult Note(string kind, string title, string key)
        {
            if (string.IsNullOrEmpty(key)) return new FundResult(FundStatus.Invalid, Balance, null);
            if (committed.Contains(key)) return new FundResult(FundStatus.Duplicate, Balance, Find(key));
            return new FundResult(FundStatus.Committed, Balance, Commit(key, kind, title, 0));
        }

        private FundEntry Commit(string key, string kind, string title, int signedAmount)
        {
            var entry = new FundEntry
            {
                key = key, kind = kind ?? "", title = title ?? "", amount = signedAmount, balanceAfter = Balance,
                seq = ++Seq, worldHours = Now,
            };
            committed.Add(key);
            history.Add(entry);
            if (history.Count > HistoryLimit) history.RemoveRange(0, history.Count - HistoryLimit);
            Committed?.Invoke(entry);
            return entry;
        }

        private FundEntry Find(string key)
        {
            for (int i = history.Count - 1; i >= 0; i--)
                if (history[i].key == key) return history[i];
            return null;
        }

        /// <summary>The newest count lines, newest first (copies).</summary>
        public List<FundEntry> Recent(int count)
        {
            var list = new List<FundEntry>(Math.Min(count, history.Count));
            for (int i = history.Count - 1; i >= 0 && list.Count < count; i--) list.Add(history[i].Copy());
            return list;
        }

        // ---------- save ----------

        public void WriteTo(EconomySaveData data)
        {
            data.balance = Balance;
            data.seq = Seq;
            data.history = new List<FundEntry>(history.Count);
            foreach (FundEntry e in history) data.history.Add(e.Copy());
            data.committedKeys = new List<string>(committed);
        }

        public static FundLedger ReadFrom(EconomySaveData data)
        {
            var ledger = new FundLedger { Balance = Math.Max(0, data.balance) };
            long seq = data.seq;
            if (data.history != null)
                foreach (FundEntry e in data.history)
                {
                    if (e == null) continue;
                    ledger.history.Add(e.Copy());
                    if (!string.IsNullOrEmpty(e.key)) ledger.committed.Add(e.key);
                    seq = Math.Max(seq, e.seq);
                }
            if (data.committedKeys != null)
                foreach (string k in data.committedKeys)
                    if (!string.IsNullOrEmpty(k)) ledger.committed.Add(k);
            if (ledger.history.Count > HistoryLimit) ledger.history.RemoveRange(0, ledger.history.Count - HistoryLimit);
            ledger.Seq = seq;
            return ledger;
        }
    }
}
