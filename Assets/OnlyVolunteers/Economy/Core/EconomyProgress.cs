using System;
using System.Collections.Generic;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Economy
{
    public enum SkillError { None, UnknownSkill, NoParticipant, AlreadyMax, RankChanged, InsufficientXp }

    public sealed class SkillPurchaseResult
    {
        public bool Ok;
        /// <summary>This rank was already bought: nothing spent now, the first outcome stands.</summary>
        public bool Replayed;
        public SkillError Error;
        public string Skill = "";
        public string Participant = "";
        public int Rank;
        public int Cost;
        public long FreeXp;
        public string Message = "";
    }

    /// <summary>The outcome of one sale booked with its XP (unit overload of EconomyState.CommitSale).</summary>
    public struct SaleCommit
    {
        public FundResult Fund;
        /// <summary>XP granted to each present participant (for a replay: the original grant).</summary>
        public int XpEach;
        public int TeamXp;
        public int LevelBefore;
        public int LevelAfter;
        public bool FirstBlood;
        /// <summary>The fund cannot hold this amount: nothing was booked.</summary>
        public bool Overflow;
        public bool Ok => Fund.Ok;
        public bool LevelUp => Fund.Status == FundStatus.Committed && LevelAfter > LevelBefore;
    }

    /// <summary>
    /// WP02 — the ONE XP store of a team world (CORE_LOOP v01 §3, §4; ECONOMY v01 §3.4), in the same EconomyState and save
    /// block as the fund, so money and XP of one sale commit together under one key:
    /// - lifetime team XP = the sum of the XP lines (each present participant gets the grant; the team gets the sum);
    /// - free team XP = lifetime − the XP spend lines (skills); spending never lowers the level;
    /// - level 1..4 from lifetime XP: 0 / 500 / 1 500 / 3 500 (CORE §4, Proposed);
    /// - once-per-world flags: the first blood (+50) and the first unit of each organ kind (+100 … +250);
    /// - skills bought from free XP, atomically and idempotently (one deterministic key per rank): the team's dosage
    ///   (500 / 1 000 / 2 000) and anaesthesia formula (1 000 / 3 000) and every participant's own bargaining rank
    ///   (500 / 1 000 / 2 000), keyed by the participant's stable id ("host" or the client's persistent GUID).
    /// </summary>
    public sealed partial class EconomyState
    {
        public const string XpCategoryBlood = "blood";
        public const string XpCategoryOrgan = "organ";
        public const string SkillDosage = "dosage";
        public const string SkillFormula = "formula";
        public const string SkillBargain = "bargain";
        public const int OrganUnitXp = 20, BloodUnitXp = 5, FirstBloodBonus = 50, TimelyOrderBonus = 150;
        /// <summary>Lifetime team XP at which levels 1, 2, 3 and 4 begin (CORE_LOOP §4, Proposed).</summary>
        public static readonly int[] LevelThresholds = { 0, 500, 1500, 3500 };
        public const string LegacyBuyerFundsKey = "migration:buyers:shared-funds";
        public const string LegacyBuyerXpKey = "migration:buyers:xp";
        public const string LegacyBuyerSpentKey = "migration:buyers:xp-spent";
        public const string LegacyBuyerRankKeyPrefix = "migration:buyers:rank:";
        public const string LegacyTeamParticipant = "legacy-team";

        private readonly List<XpSpend> xpSpends = new List<XpSpend>();
        private readonly List<string> firstKinds = new List<string>();

        public bool FirstBloodGranted { get; private set; }
        public IReadOnlyList<XpSpend> XpSpends => xpSpends;
        public IReadOnlyList<string> FirstKinds => firstKinds;
        public bool FirstKindGranted(ProductKind kind) => firstKinds.Contains(kind.ToString());

        public long LifetimeXp
        {
            get { long t = 0; foreach (XpEntry e in xp) t += Math.Max(0, e.amount); return t; }
        }

        public long SpentXp
        {
            get { long t = 0; foreach (XpSpend s in xpSpends) t += Math.Max(0, s.amount); return t; }
        }

        public long FreeXp => Math.Max(0, LifetimeXp - SpentXp);
        public int Level => LevelFor(LifetimeXp);
        public static int TopLevel => LevelThresholds.Length;

        public static int LevelFor(long lifetimeXp)
        {
            int level = 1;
            for (int i = 1; i < LevelThresholds.Length; i++) if (lifetimeXp >= LevelThresholds[i]) level = i + 1;
            return level;
        }

        /// <summary>Lifetime XP where the level after this one begins; -1 at the top level.</summary>
        public static int NextLevelAt(int level) => level >= 1 && level < LevelThresholds.Length ? LevelThresholds[level] : -1;

        // ---------- sales with XP ----------

        /// <summary>The XP one present participant gets for these units (in sale order) on top of this world's flags:
        /// organ 20, blood (bag or syringe) 5; the first blood of the world +50 once; the first unit of an organ kind its
        /// first-of-a-kind bonus once (later units of the same batch do not); a timely special order +150.</summary>
        public int PlanSaleXp(IList<ProductKind> units, bool timelyOrder, out List<string> newKinds, out bool firstBlood)
        {
            newKinds = new List<string>();
            firstBlood = false;
            long each = 0;
            if (units != null)
                foreach (ProductKind unit in units)
                {
                    if (BuyerCatalog.IsOrgan(unit))
                    {
                        each += OrganUnitXp;
                        string name = unit.ToString();
                        if (!firstKinds.Contains(name) && !newKinds.Contains(name)) { newKinds.Add(name); each += BuyerCatalog.FirstTypeBonus(unit); }
                    }
                    else
                    {
                        each += BloodUnitXp;
                        if (!FirstBloodGranted && !firstBlood) { firstBlood = true; each += FirstBloodBonus; }
                    }
                }
            if (timelyOrder) each += TimelyOrderBonus;
            return (int)Math.Min(int.MaxValue, each);
        }

        /// <summary>A sale booked ONCE: the money into the fund, the XP to every present participant and the first-of-a-kind /
        /// first-blood flags, all under one transaction key (CP-02, CP-03). A duplicate key books nothing and answers with
        /// the original XP; a refusal (invalid amount, a fund that cannot hold it) books nothing. The level change is part
        /// of the same commit (it is derived from lifetime XP).</summary>
        public SaleCommit CommitSale(int amount, string kind, string title, string key, IList<ProductKind> units, bool timelyOrder, IList<string> participants)
        {
            var result = new SaleCommit { LevelBefore = Level, LevelAfter = Level };
            if (string.IsNullOrEmpty(key) || units == null || units.Count == 0)
            {
                result.Fund = new FundResult(FundStatus.Invalid, Fund.Balance, null);
                return result;
            }
            if (Fund.IsCommitted(key))
            {
                result.Fund = Fund.Credit(amount > 0 ? amount : 1, kind, title, key); // Duplicate: nothing moves
                foreach (XpEntry e in xp)
                    if (e.key == key) { result.XpEach = e.amount; result.TeamXp += e.amount; }
                return result;
            }
            if (amount > 0 && (long)Fund.Balance + amount > int.MaxValue)
            {
                result.Overflow = true;
                result.Fund = new FundResult(FundStatus.Invalid, Fund.Balance, null);
                return result;
            }
            int each = PlanSaleXp(units, timelyOrder, out List<string> newKinds, out bool firstBlood);
            FundResult paid = Fund.Credit(amount, kind, title, key);
            result.Fund = paid;
            if (paid.Status != FundStatus.Committed) return result;
            var who = new List<string>();
            if (participants != null)
                foreach (string p in participants)
                    if (!string.IsNullOrEmpty(p) && !who.Contains(p)) who.Add(p);
            if (who.Count == 0) who.Add("host");
            string category = CategoryOf(units);
            if (each > 0)
                foreach (string p in who)
                {
                    xp.Add(new XpEntry { key = key, participant = p, category = category, amount = each, worldHours = worldHours });
                    result.TeamXp += each;
                }
            result.XpEach = each;
            foreach (string k in newKinds) firstKinds.Add(k);
            if (firstBlood) FirstBloodGranted = true;
            result.FirstBlood = firstBlood;
            result.LevelAfter = Level;
            Changed?.Invoke();
            return result;
        }

        private static string CategoryOf(IList<ProductKind> units)
        {
            bool organ = false, blood = false;
            foreach (ProductKind u in units) { if (BuyerCatalog.IsOrgan(u)) organ = true; else blood = true; }
            return organ && blood ? "mixed" : organ ? XpCategoryOrgan : XpCategoryBlood;
        }

        /// <summary>A first-blood bonus granted outside this state (the C01 syringe record of an older save): the world flag
        /// is set once, so no second +50 follows.</summary>
        public bool ReconcileFirstBlood(bool grantedElsewhere)
        {
            if (!grantedElsewhere || FirstBloodGranted) return false;
            FirstBloodGranted = true;
            Changed?.Invoke();
            return true;
        }

        // ---------- skills bought with free XP ----------

        public static bool IsSkill(string skill) => skill == SkillDosage || skill == SkillFormula || skill == SkillBargain;
        /// <summary>The bargaining rank belongs to one participant; dosage and formulas to the team.</summary>
        public static bool IsPersonalSkill(string skill) => skill == SkillBargain;
        public static int SkillMaxRank(string skill) => skill == SkillFormula ? 2 : IsSkill(skill) ? 3 : 0;

        /// <summary>CORE_LOOP §3: dosage 500 / 1 000 / 2 000, formulas 1 000 (improved) / 3 000 (late), bargaining
        /// 500 / 1 000 / 2 000 per participant. 0 for an unknown skill or rank.</summary>
        public static int SkillCost(string skill, int rank)
        {
            if (skill == SkillFormula) return rank == 1 ? 1000 : rank == 2 ? 3000 : 0;
            if (skill == SkillDosage || skill == SkillBargain) return rank == 1 ? 500 : rank == 2 ? 1000 : rank == 3 ? 2000 : 0;
            return 0;
        }

        public static string SkillKey(string skill, string participant, int rank) =>
            "skill:" + skill + ":" + (string.IsNullOrEmpty(participant) ? "team" : participant) + ":" + rank;

        private static string Owner(string skill, string participant) => IsPersonalSkill(skill) ? (participant ?? "") : "";

        /// <summary>The bought rank (0 = none). Team skills ignore the participant.</summary>
        public int SkillRank(string skill, string participant = "")
        {
            string owner = Owner(skill, participant);
            int rank = 0;
            foreach (XpSpend s in xpSpends)
                if (s.skill == skill && s.participant == owner && s.rank > rank) rank = s.rank;
            return rank;
        }

        /// <summary>Buys the next rank of a skill from the team's FREE XP (CP-01, CP-08). expectedRank is the rank the buyer
        /// saw as next: no skipping, no second payment (a rank already bought answers Replayed), and the free XP is checked
        /// at the moment of the commit, so two purchases never pay with the same XP. Lifetime XP and the level do not change.</summary>
        public SkillPurchaseResult TryBuySkill(string skill, string participant, int expectedRank)
        {
            var r = new SkillPurchaseResult { Skill = skill ?? "", Rank = expectedRank };
            if (!IsSkill(skill)) return SkillFail(r, SkillError.UnknownSkill);
            string owner = Owner(skill, participant);
            r.Participant = owner;
            if (IsPersonalSkill(skill) && string.IsNullOrEmpty(owner)) return SkillFail(r, SkillError.NoParticipant);
            int current = SkillRank(skill, owner);
            if (expectedRank >= 1 && expectedRank <= current)
            {
                r.Ok = true; r.Replayed = true; r.Cost = SkillCost(skill, expectedRank); r.FreeXp = FreeXp;
                r.Message = "Уже открыто: " + SkillTitle(skill) + " " + expectedRank;
                return r;
            }
            int max = SkillMaxRank(skill);
            if (current >= max) return SkillFail(r, SkillError.AlreadyMax);
            if (expectedRank != current + 1) return SkillFail(r, SkillError.RankChanged);
            int cost = SkillCost(skill, expectedRank);
            r.Cost = cost;
            if (cost <= 0) return SkillFail(r, SkillError.UnknownSkill);
            if (FreeXp < cost) return SkillFail(r, SkillError.InsufficientXp);
            xpSpends.Add(new XpSpend { key = SkillKey(skill, owner, expectedRank), skill = skill, participant = owner, rank = expectedRank, amount = cost, worldHours = worldHours });
            r.Ok = true;
            r.FreeXp = FreeXp;
            r.Message = "Открыто: " + SkillTitle(skill) + " " + expectedRank + " (−" + cost + " XP, свободно " + FreeXp + ")";
            Changed?.Invoke();
            return r;
        }

        public static string SkillTitle(string skill) =>
            skill == SkillDosage ? "Дозировка" : skill == SkillFormula ? "Формула наркоза" : skill == SkillBargain ? "Торг" : skill;

        private SkillPurchaseResult SkillFail(SkillPurchaseResult r, SkillError error)
        {
            r.Ok = false;
            r.Error = error;
            r.FreeXp = FreeXp;
            switch (error)
            {
                case SkillError.UnknownSkill: r.Message = "Такого навыка нет"; break;
                case SkillError.NoParticipant: r.Message = "Личный навык: неизвестно, кто покупает"; break;
                case SkillError.AlreadyMax: r.Message = SkillTitle(r.Skill) + ": уже максимум"; break;
                case SkillError.RankChanged: r.Message = SkillTitle(r.Skill) + ": ступень уже изменилась — проверь карточку"; break;
                case SkillError.InsufficientXp: r.Message = "Не хватает свободного XP: нужно " + r.Cost + ", есть " + FreeXp; break;
            }
            return r;
        }

        // ---------- once-only migration of the old BuyerWorldState money / XP ----------

        /// <summary>Moves a pre-WP02 BuyerWorldState snapshot's money, XP, bargaining ranks and first flags into this world
        /// once, under fixed keys (a repeat books nothing). Lifetime and free XP come out exactly as the snapshot had them:
        /// personal XP lines per participant, any remainder as one "legacy-team" line; the spent part pays the saved ranks
        /// at their prices as far as it reaches, the rest is one legacy spend line. Nothing is invented: a negative or
        /// fractional amount, or one the fund cannot hold, throws.</summary>
        public bool MigrateBuyerLegacy(BuyerLegacyProgress legacy)
        {
            if (legacy == null || legacy.Empty) return false;
            bool changed = false;
            if (legacy.SharedFunds != 0 && !Fund.IsCommitted(LegacyBuyerFundsKey))
            {
                if (legacy.SharedFunds < 0 || legacy.SharedFunds != decimal.Truncate(legacy.SharedFunds) || legacy.SharedFunds > int.MaxValue - (decimal)Fund.Balance)
                    throw new OverflowException("legacy buyer funds cannot move into the fund: " + legacy.SharedFunds);
                Fund.Credit((int)legacy.SharedFunds, "migration", "Перенос денег старого учёта покупателей в общий фонд", LegacyBuyerFundsKey);
                changed = true;
            }
            if (legacy.LifetimeXp < 0 || legacy.FreeXp < 0 || legacy.FreeXp > legacy.LifetimeXp)
                throw new ArgumentOutOfRangeException(nameof(legacy), "legacy buyer XP is inconsistent");
            if (!xp.Exists(e => e.key == LegacyBuyerXpKey))
            {
                long personal = 0;
                foreach (var p in legacy.Participants)
                    if (p != null && !string.IsNullOrEmpty(p.Id) && p.PersonalXp > 0)
                    {
                        xp.Add(new XpEntry { key = LegacyBuyerXpKey, participant = p.Id, category = "legacy", amount = checked((int)p.PersonalXp), worldHours = worldHours });
                        personal += p.PersonalXp;
                        changed = true;
                    }
                long rest = legacy.LifetimeXp - personal;
                if (rest > 0)
                {
                    xp.Add(new XpEntry { key = LegacyBuyerXpKey, participant = LegacyTeamParticipant, category = "legacy", amount = checked((int)rest), worldHours = worldHours });
                    changed = true;
                }
            }
            if (!xpSpends.Exists(s => s.key == LegacyBuyerSpentKey || s.key.StartsWith(LegacyBuyerRankKeyPrefix, StringComparison.Ordinal)))
            {
                long budget = legacy.LifetimeXp - legacy.FreeXp;
                foreach (var p in legacy.Participants)
                {
                    if (p == null || string.IsNullOrEmpty(p.Id)) continue;
                    int ranks = Math.Max(0, Math.Min(SkillMaxRank(SkillBargain), p.NegotiationLevel));
                    for (int rank = SkillRank(SkillBargain, p.Id) + 1; rank <= ranks; rank++)
                    {
                        int paid = (int)Math.Min(budget, SkillCost(SkillBargain, rank));
                        budget -= paid;
                        xpSpends.Add(new XpSpend { key = LegacyBuyerRankKeyPrefix + p.Id + ":" + rank, skill = SkillBargain, participant = p.Id, rank = rank, amount = paid, worldHours = worldHours });
                        changed = true;
                    }
                }
                if (budget > 0)
                {
                    xpSpends.Add(new XpSpend { key = LegacyBuyerSpentKey, skill = "legacy", participant = "", rank = 0, amount = checked((int)budget), worldHours = worldHours });
                    changed = true;
                }
            }
            if (legacy.FirstBloodSold && !FirstBloodGranted) { FirstBloodGranted = true; changed = true; }
            foreach (ProductKind kind in legacy.FirstOrganTypes)
                if (!firstKinds.Contains(kind.ToString())) { firstKinds.Add(kind.ToString()); changed = true; }
            if (changed) Changed?.Invoke();
            return changed;
        }

        // ---------- save / snapshot ----------

        private void WriteProgress(EconomySaveData data)
        {
            data.xpSpends = new List<XpSpend>(xpSpends.Count);
            foreach (XpSpend s in xpSpends) data.xpSpends.Add(s.Copy());
            data.firstKinds = new List<string>(firstKinds);
            data.firstBloodGranted = FirstBloodGranted;
        }

        /// <summary>blockVersion 2 restores the fields as saved. A version 1 block (before WP02) had no spends and no flags:
        /// its first blood is derived once from its blood XP lines (the C01 sale always granted it with the first blood XP).</summary>
        private void ReadProgress(EconomySaveData data)
        {
            if (data.xpSpends != null)
                foreach (XpSpend s in data.xpSpends)
                    if (s != null && !string.IsNullOrEmpty(s.key) && !xpSpends.Exists(x => x.key == s.key)) xpSpends.Add(s.Copy());
            if (data.firstKinds != null)
                foreach (string k in data.firstKinds)
                    if (!string.IsNullOrEmpty(k) && !firstKinds.Contains(k)) firstKinds.Add(k);
            FirstBloodGranted = data.firstBloodGranted;
            if (data.blockVersion < 2) FirstBloodGranted |= xp.Exists(e => e.category == XpCategoryBlood && e.amount > 0);
        }

        private void SnapshotProgress(EconomySnapshot s)
        {
            long lifetime = LifetimeXp;
            s.lifetimeXp = (int)Math.Min(int.MaxValue, lifetime);
            s.freeXp = (int)Math.Min(int.MaxValue, FreeXp);
            s.level = LevelFor(lifetime);
            s.nextLevelAt = NextLevelAt(s.level);
            s.firstBloodGranted = FirstBloodGranted;
            s.firstKinds = new List<string>(firstKinds);
            s.skills = new List<SkillRankView>();
            foreach (XpSpend spend in xpSpends)
            {
                if (!IsSkill(spend.skill)) continue;
                SkillRankView view = s.skills.Find(v => v.skill == spend.skill && v.participant == spend.participant);
                if (view == null) s.skills.Add(new SkillRankView { skill = spend.skill, participant = spend.participant, rank = spend.rank });
                else if (spend.rank > view.rank) view.rank = spend.rank;
            }
        }
    }

    /// <summary>WP02: the buyer rules' view of the team economy (IBuyerEconomy) over the ONE EconomyState: BuyerWorldState
    /// keeps no money or XP, every buyer sale is booked here (fund + XP + flags under the sale key).</summary>
    public sealed class EconomyBuyerLedger : IBuyerEconomy
    {
        private readonly EconomyState state;
        private readonly object gate = new object();

        public EconomyBuyerLedger(EconomyState state) { this.state = state ?? throw new ArgumentNullException(nameof(state)); }

        public EconomyState State => state;

        public BuyerBookingResult Book(BuyerSaleBooking booking)
        {
            if (booking == null || string.IsNullOrEmpty(booking.Key) || booking.Units == null || booking.Units.Count == 0) return default;
            if (booking.Amount > int.MaxValue) throw new OverflowException("the sale does not fit the fund: " + booking.Amount);
            if (booking.Amount <= 0 || booking.Amount != decimal.Truncate(booking.Amount)) return default; // the fund holds whole dollars
            lock (gate)
            {
                SaleCommit c = state.CommitSale((int)booking.Amount, "sale", booking.Title, booking.Key, booking.Units, booking.TimelyOrder, booking.Participants);
                if (c.Overflow) throw new OverflowException("the fund cannot hold this sale");
                return new BuyerBookingResult
                {
                    Committed = c.Fund.Status == FundStatus.Committed,
                    Replayed = c.Fund.Status == FundStatus.Duplicate,
                    XpEach = c.XpEach,
                    TeamXp = c.TeamXp,
                };
            }
        }

        public int BargainRank(string participantId)
        {
            lock (gate) return state.SkillRank(EconomyState.SkillBargain, participantId);
        }

        public bool TryBuyBargainRank(string participantId, int nextRank)
        {
            lock (gate)
            {
                SkillPurchaseResult r = state.TryBuySkill(EconomyState.SkillBargain, participantId, nextRank);
                return r.Ok && !r.Replayed;
            }
        }

        public void MigrateLegacy(BuyerLegacyProgress legacy)
        {
            lock (gate) state.MigrateBuyerLegacy(legacy);
        }
    }
}
