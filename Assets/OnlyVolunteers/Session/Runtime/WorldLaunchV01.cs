using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using OnlyVolunteers.Capture;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Session
{
    /// <summary>
    /// The five world slots of the start menu (29.10) as files next to the existing saves (persistentDataPath/OnlyVolunteers,
    /// the same CaptureSaveStore format, backups and atomic writes). Slot 1 IS the existing map save (editor:
    /// capture_stageA_editor_W85_v02.json, build: capture_stageA_W85_v02.json, the play scene's own names), so the world
    /// Fedya already plays shows up as card 1 and is never lost or renamed. Slots 2–5 are new files (ov_world_N.json; the
    /// editor uses ov_world_N_editor.json like the other editor saves). Cards read the file header only through
    /// CaptureSaveStore.Probe: name, Solo/Co-op, date, play time. Delete removes ONE slot's file, its backups and pointer.
    /// </summary>
    public static class WorldSlotsV01
    {
        public const int Count = MainMenuFlowV2.SlotCount;
#if UNITY_EDITOR
        const string Slot1 = "capture_stageA_editor_W85_v02.json";
#else
        const string Slot1 = "capture_stageA_W85_v02.json";
#endif

        public static string Folder => Path.Combine(Application.persistentDataPath, "OnlyVolunteers");

        public static string FileName(int slot)
        {
            if (slot <= 0) return Slot1;
#if UNITY_EDITOR
            return "ov_world_" + (slot + 1).ToString(CultureInfo.InvariantCulture) + "_editor.json";
#else
            return "ov_world_" + (slot + 1).ToString(CultureInfo.InvariantCulture) + ".json";
#endif
        }

        public static string BasePath(int slot) => Path.Combine(Folder, FileName(slot));

        /// <summary>The file this slot reads/writes now (a recovery "new file" pointer is honoured, as in CaptureDirector).</summary>
        public static string ActivePath(int slot) => CaptureSaveStore.ResolveActive(BasePath(slot));

        public static List<WorldSlotCard> Cards()
        {
            var list = new List<WorldSlotCard>();
            for (int i = 0; i < Count; i++) list.Add(Card(i));
            return list;
        }

        public static WorldSlotCard Card(int slot)
        {
            var card = new WorldSlotCard { Index = slot, Name = MainMenuFlowV2.DefaultName(slot) };
            string path;
            try { path = ActivePath(slot); } catch (Exception) { return card; }
            if (!File.Exists(path)) return card;
            card.Occupied = true;
            SaveFileProbe probe;
            try { probe = CaptureSaveStore.Probe(path); }
            catch (Exception e) { card.Loadable = false; card.Problem = "Файл не читается: " + e.Message; return card; }
            card.Loadable = probe.Loadable;
            if (!probe.Loadable) card.Problem = CaptureSaveStore.Explain(probe);
            CaptureSaveData data = probe.Data;
            if (data != null)
            {
                if (data.world != null && !string.IsNullOrEmpty(data.world.worldName)) card.Name = data.world.worldName;
                else if (slot == 0) card.Name = "Мир карты (старое сохранение)";
                card.Mode = WorldModeRules.Status(data.world);
                if (card.Mode == WorldModeStatus.NoWorld) card.Mode = WorldModeStatus.LegacyNeedsChoice;
                if (DateTime.TryParse(data.savedUtc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out DateTime utc))
                {
                    card.SavedTicksUtc = utc.ToUniversalTime().Ticks;
                    card.SavedText = utc.ToLocalTime().ToString("dd.MM.yyyy HH:mm", CultureInfo.InvariantCulture) + " · " + PlayTime(data.playTime);
                }
                else card.SavedText = PlayTime(data.playTime);
            }
            else
            {
                card.Mode = WorldModeStatus.LegacyNeedsChoice;
                try { card.SavedTicksUtc = File.GetLastWriteTimeUtc(path).Ticks; } catch (Exception) { }
            }
            return card;
        }

        public static string PlayTime(float seconds)
        {
            int m = Mathf.Max(0, Mathf.RoundToInt(seconds / 60f));
            return m < 60 ? "в игре " + m + " мин" : "в игре " + (m / 60) + " ч " + (m % 60) + " мин";
        }

        /// <summary>The player's explicit Delete (after the confirm): this slot's file(s), backups and pointer only.</summary>
        public static bool Delete(int slot, out string error)
        {
            error = "";
            try
            {
                string active = ActivePath(slot), basePath = BasePath(slot);
                CaptureSaveStore.DeleteWithBackups(active);
                if (active != basePath && File.Exists(basePath)) CaptureSaveStore.DeleteWithBackups(basePath);
                string pointer = CaptureSaveStore.PointerPath(basePath);
                if (File.Exists(pointer)) File.Delete(pointer);
                Debug.Log($"[OV World] slot {slot + 1} deleted ({Path.GetFileName(active)})");
                return true;
            }
            catch (Exception e) { error = e.Message; Debug.LogWarning("[OV World] delete failed: " + e); return false; }
        }
    }

    public enum LaunchRole : byte { None = 0, SoloHost = 1, CoopHost = 2 }

    /// <summary>
    /// What the start menu chose for the world it is about to load (29.10). The map reads it once: CaptureDirector saves to
    /// <see cref="SlotFile"/> (instead of the scene's default file) and hosts on all interfaces only for a co-op world;
    /// <see cref="W86PrologueHookV01"/> starts the opening of a NEW world. Starting the map straight from the editor (no
    /// menu) leaves everything as before (Active = false).
    /// </summary>
    public static class WorldLaunchV01
    {
        public const string MapScenePath = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        public const string MenuScenePath = "Assets/OnlyVolunteers/Scenes/Menu/MainMenu_v01.unity";
        public const ushort DefaultPort = 7791;

        public static bool Active { get; private set; }
        public static int Slot { get; private set; } = -1;
        public static string SlotFile { get; private set; } = "";
        public static bool NewWorld { get; private set; }
        public static bool SkipIntro { get; private set; }
        public static LaunchRole Role { get; private set; }
        public static ushort Port { get; private set; } = DefaultPort;
        public static string WorldName { get; private set; } = "";
        /// <summary>The lobby's ready participants at the start (the intro's staging; 1 for solo).</summary>
        public static int Participants { get; private set; } = 1;
        /// <summary>The opening of this new world was handed to the prologue hook (once per launch).</summary>
        public static bool PrologueClaimed { get; set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { Clear(); }

        static void Clear()
        {
            Active = false; Slot = -1; SlotFile = ""; NewWorld = false; SkipIntro = false; Role = LaunchRole.None;
            Port = DefaultPort; WorldName = ""; Participants = 1; PrologueClaimed = false;
        }

        /// <summary>A new world: the mode is fixed here (WorldSessionV01.BeginNewWorld), the slot must be empty.</summary>
        public static bool StartNew(int slot, WorldMode mode, string name, bool skipIntro, int participants, ushort port, out string error)
        {
            error = "";
            if (slot < 0 || slot >= WorldSlotsV01.Count) { error = "Нет такого слота."; return false; }
            if (File.Exists(WorldSlotsV01.ActivePath(slot))) { error = "Слот уже занят: новый мир не записывается поверх старого."; return false; }
            WorldSessionV01.BeginNewWorld(mode);
            if (WorldSessionV01.Current != null) WorldSessionV01.Current.worldName = MainMenuFlowV2.CleanName(name, slot);
            Set(slot, true, skipIntro, mode, participants, port, MainMenuFlowV2.CleanName(name, slot));
            return Load(out error);
        }

        /// <summary>An existing world (its own mode from the save; a legacy world's one-time choice when given).</summary>
        public static bool StartLoad(int slot, WorldMode modeForNetwork, WorldMode legacyChoice, int participants, ushort port, out string error)
        {
            error = "";
            if (slot < 0 || slot >= WorldSlotsV01.Count) { error = "Нет такого слота."; return false; }
            if (!File.Exists(WorldSlotsV01.ActivePath(slot))) { error = "Сохранение этого мира не найдено."; return false; }
            if (legacyChoice != WorldMode.Unset) WorldSessionV01.RequestLegacyChoice(legacyChoice);
            Set(slot, false, false, modeForNetwork, participants, port, WorldSlotsV01.Card(slot).Name);
            return Load(out error);
        }

        static void Set(int slot, bool isNew, bool skip, WorldMode mode, int participants, ushort port, string name)
        {
            Active = true; Slot = slot; SlotFile = WorldSlotsV01.FileName(slot); NewWorld = isNew; SkipIntro = skip;
            Role = mode == WorldMode.Multiplayer ? LaunchRole.CoopHost : LaunchRole.SoloHost;
            Port = port == 0 ? DefaultPort : port; WorldName = name ?? ""; Participants = Mathf.Max(1, participants);
            PrologueClaimed = false;
            Debug.Log($"[OV World] launch slot {slot + 1} ({SlotFile}) {(isNew ? "NEW" : "load")} as {Role}, port {Port}, participants {Participants}, skip intro {skip}");
        }

        static bool Load(out string error)
        {
            error = "";
            if (!Application.CanStreamedLevelBeLoaded(MapScenePath))
            {
                error = "Сцена карты не добавлена в сборку (Build Settings).";
                Clear();
                return false;
            }
            SceneManager.LoadScene(MapScenePath, LoadSceneMode.Single);
            return true;
        }

        /// <summary>Pause menu → Главное меню: the caller saved the world first; networking stops with the map scene.</summary>
        public static void ReturnToMenu()
        {
            Clear();
            var nm = FishNet.InstanceFinder.NetworkManager;
            if (nm != null)
            {
                if (nm.ClientManager.Started) nm.ClientManager.StopConnection();
                if (nm.ServerManager.Started) nm.ServerManager.StopConnection(true);
            }
            Time.timeScale = 1f;
            AudioListener.pause = false;
            if (Application.CanStreamedLevelBeLoaded(MenuScenePath)) SceneManager.LoadScene(MenuScenePath, LoadSceneMode.Single);
            else SceneManager.LoadScene(0, LoadSceneMode.Single);
        }
    }
}
