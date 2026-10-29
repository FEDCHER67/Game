using System;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Session
{
    /// <summary>The world's play mode, chosen once before the world starts (PLAYER stage brief §2). Saved: append only.</summary>
    public enum WorldMode : byte { Unset = 0, Solo = 1, Multiplayer = 2 }

    /// <summary>What a loaded world's mode is. NoWorld = no world save is loaded (test/dev scenes): network behaviour as before.</summary>
    public enum WorldModeStatus { NoWorld = 0, LegacyNeedsChoice = 1, Solo = 2, Multiplayer = 3 }

    public enum JoinVerdict { Accept = 0, RejectSoloWorld = 1, RejectFull = 2 }

    public enum ModeChange { Unchanged = 0, Refused = 1 }

    /// <summary>
    /// The world-profile block of one world save (inside CaptureSaveData.world). blockVersion 0 = absent: the save was written
    /// before modes existed (a legacy world). Holds the immutable mode and the opening/tutorial state.
    /// </summary>
    [Serializable]
    public sealed class WorldProfileSaveBlock
    {
        public const int CurrentBlockVersion = 1;
        public int blockVersion;
        public int mode;
        public string createdUtc = "";
        /// <summary>The mode was set by the owner's explicit one-time choice for a legacy world (never automatically).</summary>
        public bool migratedFromLegacy;
        public string migratedUtc = "";
        public PrologueSaveData prologue = new PrologueSaveData();
        /// <summary>The name the owner gave the world in the start menu (29.10, append only; "" = an older world).</summary>
        public string worldName = "";

        public WorldMode Mode => (WorldMode)mode;

        public WorldProfileSaveBlock Copy()
        {
            var c = (WorldProfileSaveBlock)MemberwiseClone();
            c.prologue = prologue != null ? prologue.Copy() : new PrologueSaveData();
            return c;
        }
    }

    /// <summary>
    /// Pure rules of the immutable Solo / Multiplayer world mode:
    /// - chosen once at world creation (<see cref="CreateNew"/>); no menu, reload or network request changes it afterwards
    ///   (<see cref="RequestChange"/> is always refused or a no-op);
    /// - a Solo world refuses every remote client; a Multiplayer world stays Multiplayer with any number of participants,
    ///   including a lone host (the mode is never derived from the participant count);
    /// - a legacy world (no block) is flagged for the owner's explicit one-time choice (<see cref="ResolveLegacy"/>); nothing
    ///   assigns it a mode silently. Until the choice it keeps today's behaviour (joins as before) and its card says so.
    /// </summary>
    public static class WorldModeRules
    {
        public const int MaxParticipants = 4;

        /// <summary>A new world's block (new WorldId/slot handling stays with the save owner). Unset is not a choice.</summary>
        public static WorldProfileSaveBlock CreateNew(WorldMode mode, string utc)
        {
            if (mode != WorldMode.Solo && mode != WorldMode.Multiplayer) throw new ArgumentException("a new world needs Solo or Multiplayer", nameof(mode));
            var b = new WorldProfileSaveBlock
            {
                blockVersion = WorldProfileSaveBlock.CurrentBlockVersion, mode = (int)mode, createdUtc = utc ?? "",
            };
            b.prologue = PrologueState.New().ToSave();
            return b;
        }

        /// <summary>null = no world loaded. A block without version or mode = a legacy world waiting for the choice.</summary>
        public static WorldModeStatus Status(WorldProfileSaveBlock block)
        {
            if (block == null) return WorldModeStatus.NoWorld;
            if (block.blockVersion <= 0) return WorldModeStatus.LegacyNeedsChoice;
            switch (block.Mode)
            {
                case WorldMode.Solo: return WorldModeStatus.Solo;
                case WorldMode.Multiplayer: return WorldModeStatus.Multiplayer;
                default: return WorldModeStatus.LegacyNeedsChoice;
            }
        }

        public static bool NeedsMigrationChoice(WorldProfileSaveBlock block) => Status(block) == WorldModeStatus.LegacyNeedsChoice;

        /// <summary>The owner's explicit one-time choice for a legacy world. Only a legacy world; only Solo/Multiplayer. The
        /// legacy world's prologue is marked as already played (an old world never gets the opening retro-fitted).</summary>
        public static bool ResolveLegacy(WorldProfileSaveBlock block, WorldMode choice, string utc)
        {
            if (block == null || !NeedsMigrationChoice(block)) return false;
            if (choice != WorldMode.Solo && choice != WorldMode.Multiplayer) return false;
            block.prologue = PrologueState.FromSave(block.blockVersion <= 0 ? null : block.prologue).ToSave();
            block.blockVersion = WorldProfileSaveBlock.CurrentBlockVersion;
            block.mode = (int)choice;
            block.migratedFromLegacy = true;
            block.migratedUtc = utc ?? "";
            return true;
        }

        /// <summary>Any later request (menu, reload, network) to change the mode of a world that has one: same mode =
        /// Unchanged, anything else = Refused. The block is never touched.</summary>
        public static ModeChange RequestChange(WorldProfileSaveBlock block, WorldMode requested) =>
            block != null && Status(block) != WorldModeStatus.LegacyNeedsChoice && block.Mode == requested ? ModeChange.Unchanged : ModeChange.Refused;

        public static bool IsSolo(WorldProfileSaveBlock block) => Status(block) == WorldModeStatus.Solo;

        /// <summary>Server, when a connection arrives. The host's own local client is always accepted. participantsNow =
        /// players already in (without this one).</summary>
        public static JoinVerdict DecideJoin(WorldModeStatus status, bool hostOwnClient, int participantsNow, int maxParticipants = MaxParticipants)
        {
            if (hostOwnClient) return JoinVerdict.Accept;
            if (status == WorldModeStatus.Solo) return JoinVerdict.RejectSoloWorld;
            if (participantsNow >= maxParticipants) return JoinVerdict.RejectFull;
            return JoinVerdict.Accept;
        }

        /// <summary>Player-facing reason for a refused join (shown on the host; the client sees the disconnect).</summary>
        public static string Explain(JoinVerdict verdict)
        {
            switch (verdict)
            {
                case JoinVerdict.RejectSoloWorld: return "Это одиночный мир: подключиться к нему нельзя.";
                case JoinVerdict.RejectFull: return "В мире уже 4 игрока.";
                default: return "";
            }
        }

        /// <summary>The mode line of a world card.</summary>
        public static string CardLabel(WorldModeStatus status)
        {
            switch (status)
            {
                case WorldModeStatus.Solo: return "Одиночный";
                case WorldModeStatus.Multiplayer: return "Совместный";
                case WorldModeStatus.LegacyNeedsChoice: return "Старый мир: режим не выбран";
                default: return "";
            }
        }
    }
}
