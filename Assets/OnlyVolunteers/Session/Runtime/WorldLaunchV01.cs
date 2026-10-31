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
    /// the same CaptureSaveStore format, backups and atomic writes). The file names follow the launching menu's edition
    /// (<see cref="WorldLaunchTargetV01.SlotFileName"/>). V1 (MainMenu_v01): slot 1 IS the existing map save (editor:
    /// capture_stageA_editor_W85_v02.json, build: capture_stageA_W85_v02.json, the play scene's own names), so the world
    /// Fedya already plays shows up as card 1 and is never lost or renamed; slots 2–5 are ov_world_N.json (the editor uses
    /// ov_world_N_editor.json like the other editor saves). V2 (MainMenu_V2_v01, 31.10): five own files ov_v2_world_1..5,
    /// never the v1 map save. Cards read the file header only through CaptureSaveStore.Probe: name, Solo/Co-op, date, play
    /// time. Delete removes ONE slot's file, its backups and pointer.
    /// </summary>
    public static class WorldSlotsV01
    {
        public const int Count = MainMenuFlowV2.SlotCount;

        public static string Folder => Path.Combine(Application.persistentDataPath, "OnlyVolunteers");

        static GameEditionV01 Edition => WorldLaunchV01.Target.Edition;

        public static string FileName(int slot) =>
#if UNITY_EDITOR
            WorldLaunchTargetV01.SlotFileName(Edition, slot, true);
#else
            WorldLaunchTargetV01.SlotFileName(Edition, slot, false);
#endif

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
                else if (slot == 0 && Edition == GameEditionV01.V1Map) card.Name = "Мир карты (старое сохранение)";
                card.Mode = WorldModeRules.Status(data.world);
                if (card.Mode == WorldModeStatus.NoWorld) card.Mode = WorldModeStatus.LegacyNeedsChoice;
                if (Edition == GameEditionV01.V2 && card.Mode == WorldModeStatus.LegacyNeedsChoice) NoModeV2(card); // V2 has no old worlds
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
                if (Edition == GameEditionV01.V2) NoModeV2(card);
            }
            return card;
        }

        /// <summary>V2: every world is made with its mode; a file without one is shown but never loaded (no "old world" choice).</summary>
        static void NoModeV2(WorldSlotCard card)
        {
            card.Mode = WorldModeStatus.NoWorld;
            if (!card.Loadable) return;
            card.Loadable = false;
            card.Problem = "В сохранении нет режима мира: загрузить нельзя.";
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
    /// <see cref="W86PrologueHookV01"/> starts the opening of a NEW world (V1 only). Starting the map straight from the editor
    /// (no menu) leaves everything as before (Active = false).
    /// 31.10 (menu for V2): the start menu sets its <see cref="Target"/> on Awake (<see cref="Configure"/>): the game scene
    /// Play loads, the menu the pause menu returns to, the slot files and the prologue flag. The default is V1 (the W86 map
    /// and MainMenu_v01), so a menu that sets nothing behaves exactly as before.
    /// </summary>
    public static class WorldLaunchV01
    {
        /// <summary>The v1 (W86) map: V1's game scene and the only scene the prologue hook ever runs in.</summary>
        public const string MapScenePath = WorldLaunchTargetV01.V1MapScene;
        /// <summary>The v1 start menu (V1's return target).</summary>
        public const string MenuScenePath = WorldLaunchTargetV01.V1MenuScene;
        public const ushort DefaultPort = 7791;

        /// <summary>The launching menu's target (V1 until a menu configures another). Kept across Clear, so the pause menu
        /// returns to the menu that launched the game.</summary>
        public static WorldLaunchTargetV01 Target { get; private set; } = WorldLaunchTargetV01.V1;
        /// <summary>The scene Play loads (V1: <see cref="MapScenePath"/>).</summary>
        public static string GameScenePath => Target.GameScene;
        /// <summary>The menu the pause menu's Главное меню loads (the launching menu).</summary>
        public static string ReturnMenuPath => Target.MenuScene;
        /// <summary>The v1 prologue may run (V1 only).</summary>
        public static bool PrologueAllowed => Target.PrologueAllowed;

        /// <summary>The start menu's Awake: which game it launches and where to come back.</summary>
        public static void Configure(WorldLaunchTargetV01 target)
        {
            Target = target ?? WorldLaunchTargetV01.V1;
            Debug.Log("[OV World] launch target " + Target);
        }

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
        static void ResetStatics() { Clear(); Target = WorldLaunchTargetV01.V1; }

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
            if (!PrologueAllowed) skipIntro = true; // V2: no prologue at all (the hook checks PrologueAllowed as well)
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
            Debug.Log($"[OV World] launch slot {slot + 1} ({SlotFile}) {(isNew ? "NEW" : "load")} as {Role}, port {Port}, participants {Participants}, skip intro {skip}, scene {GameScenePath}");
        }

        static bool Load(out string error)
        {
            error = "";
            string scene = GameScenePath;
            // V2 builds made from scene copies (VadimBuilds: the V2 menu + Build_Hangar / Build_VanOnly, 31.10): the build's
            // game scene is index 1 when the configured path is not in the build
            if (!Application.CanStreamedLevelBeLoaded(scene) && Target.Edition == GameEditionV01.V2 && SceneManager.sceneCountInBuildSettings > 1)
            {
                Debug.Log($"[OV World] {scene} is not in this build: loading build scene 1 instead");
                SceneManager.LoadScene(1, LoadSceneMode.Single);
                return true;
            }
            if (!Application.CanStreamedLevelBeLoaded(scene))
            {
                error = Target.Edition == GameEditionV01.V2 ? "Сцена игры не добавлена в сборку (Build Settings)." : "Сцена карты не добавлена в сборку (Build Settings).";
                Clear();
                return false;
            }
            SceneManager.LoadScene(scene, LoadSceneMode.Single);
            return true;
        }

        /// <summary>Pause menu → Главное меню: the caller saved the world first; networking stops with the map scene. Loads
        /// the menu that launched the game (<see cref="ReturnMenuPath"/>; scene 0 when that menu is not in the build).</summary>
        public static void ReturnToMenu()
        {
            string menu = ReturnMenuPath;
            Clear();
            var nm = FishNet.InstanceFinder.NetworkManager;
            if (nm != null)
            {
                if (nm.ClientManager.Started) nm.ClientManager.StopConnection();
                if (nm.ServerManager.Started) nm.ServerManager.StopConnection(true);
            }
            Time.timeScale = 1f;
            AudioListener.pause = false;
            if (Application.CanStreamedLevelBeLoaded(menu)) SceneManager.LoadScene(menu, LoadSceneMode.Single);
            else SceneManager.LoadScene(0, LoadSceneMode.Single);
        }
    }
}
