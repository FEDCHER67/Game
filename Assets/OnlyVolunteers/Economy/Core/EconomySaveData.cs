using System;
using System.Collections.Generic;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Economy
{
    /// <summary>The economy block of the team save (inside CaptureSaveData.economy). blockVersion 0 = the block is absent
    /// (a save written before the shared fund): FundMigration converts it once. JsonUtility-friendly: public fields only.</summary>
    [Serializable]
    public sealed class EconomySaveData
    {
        public int blockVersion;
        public string migrationSource = "";
        public int balance;
        public long seq;
        public List<FundEntry> history = new List<FundEntry>();
        /// <summary>Every committed transaction key, also those whose line left the visible history (§10.4).</summary>
        public List<string> committedKeys = new List<string>();
        public int vanEngine;
        public int vanHandling;
        public int vanBrakes;
        public bool vanLegacyDebugProfile;
        /// <summary>Bought van cargo-body upgrades (ECONOMY §6.2 + containment, Fedya 29.10): catalogue ids such as
        /// van_capacity_1 / van_containment_2. Absent in older blocks: empty, nothing granted.</summary>
        public List<string> vanCargo = new List<string>();
        public bool workshopUnlocked;
        public bool firstOrganBuyerMet;
        public List<string> ownedBases = new List<string>();
        public List<DeliveryOrder> deliveries = new List<DeliveryOrder>();
        public long deliverySeq;
        public double worldHours;
        /// <summary>World calendar (STORY / daily finds): the day number and the sky-clock hour of the last frame. -1 = a
        /// block written before the calendar (the first clock reading starts it, day 0).</summary>
        public int worldDay;
        public double timeOfDay = -1;
        /// <summary>Sale XP, one line per participant per committed transaction key (same key as the fund line). WP02: the
        /// team's lifetime XP is the sum of these lines (participant = a stable player id: "host" or the client's GUID;
        /// older saves may hold "client:N" lines, kept as statistics).</summary>
        public List<XpEntry> xp = new List<XpEntry>();
        /// <summary>WP02 (blockVersion 2): XP spent on skills, one line per bought rank. Free XP = lifetime − these.</summary>
        public List<XpSpend> xpSpends = new List<XpSpend>();
        /// <summary>WP02: product kinds whose first-of-a-kind bonus was granted in this world (ProductKind names).</summary>
        public List<string> firstKinds = new List<string>();
        /// <summary>WP02: the one first-blood bonus (+50) of this world was granted (any blood sale: syringe or bag).</summary>
        public bool firstBloodGranted;
        /// <summary>Story missions M01-M13 (facts, acceptance, receipts, retained messages, M06 target generation).
        /// version 0 = a save from before the story block.</summary>
        public StorySaveData story = new StorySaveData();
    }

    /// <summary>One committed XP grant (ECONOMY §3.4): never stored as money, never repeated for the same key.</summary>
    [Serializable]
    public sealed class XpEntry
    {
        public string key = "";
        public string participant = "";
        public string category = "";
        public int amount;
        public double worldHours;
    }

    [Serializable]
    public sealed class XpTotal
    {
        public string participant = "";
        public int total;
    }

    /// <summary>WP02: one bought skill rank paid from the team's free XP (CORE_LOOP §3). key = skill:&lt;id&gt;:&lt;who&gt;:&lt;rank&gt;
    /// (a rank is paid once); participant = "" for a team skill, the buyer's stable id for a personal bargaining rank.</summary>
    [Serializable]
    public sealed class XpSpend
    {
        public string key = "";
        public string skill = "";
        public string participant = "";
        public int rank;
        public int amount;
        public double worldHours;
        public XpSpend Copy() => (XpSpend)MemberwiseClone();
    }

    /// <summary>What clients see of one bought rank.</summary>
    [Serializable]
    public sealed class SkillRankView
    {
        public string skill = "";
        public string participant = "";
        public int rank;
    }

    /// <summary>What every client sees (the server sends it after each commit): the fund, recent lines, van tiers, flags,
    /// bases and deliveries. Display only: clients never change money from it.</summary>
    [Serializable]
    public sealed class EconomySnapshot
    {
        public bool ready;
        public int balance;
        public long seq;
        public List<FundEntry> recent = new List<FundEntry>();
        public int vanEngine;
        public int vanHandling;
        public int vanBrakes;
        public bool vanLegacyDebugProfile;
        /// <summary>Bought van cargo-body upgrade ids (display; every machine applies them to its van view).</summary>
        public List<string> vanCargo = new List<string>();
        public bool workshopUnlocked;
        public bool firstOrganBuyerMet;
        public List<string> ownedBases = new List<string>();
        public List<DeliveryOrder> deliveries = new List<DeliveryOrder>();
        public double worldHours;
        public int worldDay;
        public double timeOfDay = -1;
        public List<XpTotal> xp = new List<XpTotal>();
        /// <summary>WP02: team XP and level (display only; the server's EconomyState is the authority).</summary>
        public int lifetimeXp;
        public int freeXp;
        public int level = 1;
        /// <summary>Lifetime XP of the next level, -1 at the top level.</summary>
        public int nextLevelAt = -1;
        public bool firstBloodGranted;
        public List<string> firstKinds = new List<string>();
        public List<SkillRankView> skills = new List<SkillRankView>();
        /// <summary>V2 base shop items the team owns (GearCatalogV2 ids; display only).</summary>
        public List<string> gear = new List<string>();
        public bool OwnsGear(string id) => gear != null && gear.Contains(id);
        /// <summary>The derived story journal and retained story messages (late join gets it with the first snapshot).</summary>
        public StoryJournalView journal = new StoryJournalView();

        public int VanTier(VanBranch branch) =>
            branch == VanBranch.Engine ? vanEngine : branch == VanBranch.Handling ? vanHandling : vanBrakes;
        public bool OwnsBase(string id) => ownedBases != null && ownedBases.Contains(id);
        public bool OwnsVanCargo(string id) => vanCargo != null && vanCargo.Contains(id);
        /// <summary>A bought rank as the snapshot shows it (team skills: participant "").</summary>
        public int SkillRank(string skill, string participant = "")
        {
            if (skills != null)
                foreach (SkillRankView s in skills)
                    if (s != null && s.skill == skill && s.participant == (participant ?? "")) return s.rank;
            return 0;
        }
    }

    /// <summary>
    /// §10.3, once per save: the shared fund replaces the old per-player cash.
    /// 1. An economy block already exists: it is the only source (old cash, the bank placeholder and LocalInventory's start
    ///    money are never added again).
    /// 2. No block, legacy hasCash = true: the host's saved cash moves into the fund once (key migration:legacy-host-cash).
    /// 3. No block, no hasCash: the fund starts at $0 with one system line saying no saved money was found.
    /// An old save (no block) also keeps the legacy / debug van profile (it ran StartAtMax): no paid tiers, no refund.
    /// The caller writes the result back as one block (marker, source and balance together), so a reload never migrates
    /// twice. Connecting clients' temporary per-player cash is never an input here.
    /// </summary>
    public static class FundMigration
    {
        public const string LegacyCashKey = "migration:legacy-host-cash";
        public const string NoCashKey = "migration:no-saved-cash";
        public const string SourceLegacyCash = "legacy-host-cash";
        public const string SourceNone = "none";

        public static bool HasBlock(EconomySaveData block) => block != null && block.blockVersion >= 1;

        public static EconomyState LoadOrMigrate(EconomySaveData block, bool legacyHasCash, int legacyCash)
        {
            if (HasBlock(block)) return EconomyState.FromSave(block);
            EconomyState s = EconomyState.NewGame();
            if (legacyHasCash)
            {
                int cash = Math.Max(0, legacyCash);
                s.MarkMigrated(SourceLegacyCash, true);
                if (cash > 0) s.Fund.Credit(cash, "migration", "Перенос сохранённой налички хоста в общий фонд", LegacyCashKey);
                else s.Fund.Note("migration", "Сохранённая наличка хоста была $0", LegacyCashKey);
            }
            else
            {
                s.MarkMigrated(SourceNone, true);
                s.Fund.Note("migration", "Сохранённых денег не найдено — фонд начат с $0", NoCashKey);
            }
            return s;
        }
    }

    /// <summary>The latest economy snapshot on this machine, for HUD and phone (display only). TeamEconomy sets it; the
    /// runtime resets it at play start (this assembly has no engine reference for its own reset hook).</summary>
    public static class EconomyClientView
    {
        public static EconomySnapshot Current { get; private set; }
        public static bool Available => Current != null;
        public static int Balance => Current != null ? Current.balance : 0;
        public static int Version { get; private set; }
        public static event Action Changed;

        public static void Set(EconomySnapshot snapshot)
        {
            Current = snapshot;
            Version++;
            Changed?.Invoke();
        }

        public static void ResetForPlay()
        {
            Current = null;
            Version++;
            Changed = null;
        }
    }

    /// <summary>Server-side entry points for assemblies that cannot see the runtime (NetworkInventory's legacy cash API):
    /// TeamEconomy sets them while it is the authority; null = no shared fund in this scene (old per-player behaviour).</summary>
    public static class EconomyServerHooks
    {
        /// <summary>(amount, title, key) → committed or duplicate.</summary>
        public static Func<int, string, string, bool> Credit;
        public static Func<int, string, string, bool> Charge;

        public static void ResetForPlay()
        {
            Credit = null;
            Charge = null;
        }
    }
}
