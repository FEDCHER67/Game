using System;
using FishNet.Connection;
using OnlyVolunteers.Story;
using UnityEngine;

namespace OnlyVolunteers.Session
{
    /// <summary>
    /// Host side: the world profile of the loaded world (its immutable Solo/Multiplayer mode and the opening/tutorial state).
    /// One owner for the running game; the world save reads it in (CaptureSave.Read → <see cref="ServerLoad"/>) and writes it
    /// out (CaptureSave.Write → <see cref="ServerSaveBlock"/>) inside the same atomic file as the fund.
    /// - null (no world loaded: the network test scene, a dev map started without the new-game flow) = NoWorld: nothing changes.
    /// - The start menu calls <see cref="BeginNewWorld"/> (mode chosen once) or <see cref="RequestLegacyChoice"/> (the owner's
    ///   explicit one-time choice for an old world) BEFORE the world scene loads.
    /// </summary>
    public static class WorldSessionV01
    {
        static WorldProfileSaveBlock current;
        static WorldMode pendingLegacyChoice;

        public static WorldProfileSaveBlock Current => current;
        public static WorldModeStatus Status => WorldModeRules.Status(current);
        public static bool SoloWorld => Status == WorldModeStatus.Solo;
        /// <summary>The live opening/tutorial rules of this world (null without a world profile).</summary>
        public static PrologueState Prologue { get; private set; }
        public static event Action Changed;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { current = null; Prologue = null; pendingLegacyChoice = WorldMode.Unset; Changed = null; }

        /// <summary>Start menu, new world: the mode is fixed here, once, before the world scene loads.</summary>
        public static void BeginNewWorld(WorldMode mode)
        {
            current = WorldModeRules.CreateNew(mode, DateTime.UtcNow.ToString("o"));
            Prologue = PrologueState.FromSave(current.prologue);
            pendingLegacyChoice = WorldMode.Unset;
            Debug.Log($"[OV World] new world, mode={mode}");
            Changed?.Invoke();
        }

        /// <summary>Start menu, loading an old world: the owner's explicit choice, applied when that save is read.</summary>
        public static void RequestLegacyChoice(WorldMode choice) => pendingLegacyChoice = choice;

        /// <summary>The save was read: its block becomes the live profile (a legacy block stays legacy unless the owner chose).</summary>
        public static void ServerLoad(WorldProfileSaveBlock block)
        {
            current = block != null ? block.Copy() : new WorldProfileSaveBlock();
            if (pendingLegacyChoice != WorldMode.Unset && WorldModeRules.NeedsMigrationChoice(current))
            {
                bool ok = WorldModeRules.ResolveLegacy(current, pendingLegacyChoice, DateTime.UtcNow.ToString("o"));
                Debug.Log($"[OV World] legacy world: owner chose {pendingLegacyChoice} (applied={ok})");
            }
            pendingLegacyChoice = WorldMode.Unset;
            Prologue = WorldModeRules.NeedsMigrationChoice(current) ? null : PrologueState.FromSave(current.prologue);
            Prologue?.AfterLoad();
            Debug.Log($"[OV World] loaded world mode={Status}, prologue={(Prologue != null ? Prologue.Stage.ToString() : "-")}");
            Changed?.Invoke();
        }

        /// <summary>What the save writes: the live profile with the current prologue, or an absent block (blockVersion 0) when
        /// this world has none — so an old world stays flagged for the owner's choice and is never assigned a mode here.</summary>
        public static WorldProfileSaveBlock ServerSaveBlock()
        {
            if (current == null) return new WorldProfileSaveBlock();
            var copy = current.Copy();
            if (Prologue != null) copy.prologue = Prologue.ToSave();
            return copy;
        }

        public static void Clear() { current = null; Prologue = null; Changed?.Invoke(); }

        /// <summary>Server, a remote connection arrived: the world-mode join rule. The host's own local client is always in.
        /// participantsNow = players already in. On a refusal the caller kicks the connection and shows the reason.</summary>
        public static JoinVerdict ServerDecideJoin(NetworkConnection connection, int participantsNow)
        {
            // FishNet reuses the server-side connection object for the host's own client once its id is known (call this
            // from ClientLoadedStartScenes, not from the first transport event).
            bool hostOwn = connection != null && (connection.IsHost || connection.IsLocalClient);
            return WorldModeRules.DecideJoin(Status, hostOwn, participantsNow);
        }
    }
}
