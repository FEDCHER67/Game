using System.Globalization;

namespace OnlyVolunteers.Session
{
    /// <summary>Which game a start menu launches (31.10): the v1 map (W86, MainMenu_v01) or the V2 game (MainMenu_V2_v01).</summary>
    public enum GameEditionV01 { V1Map = 0, V2 = 1 }

    /// <summary>
    /// Where a start menu sends its worlds (Fedya 31.10, menu for V2), pure: the game scene Play loads, the menu scene the
    /// pause menu returns to, the save files of the five world slots, and whether the v1 prologue may run at all.
    /// V1 (the default, MainMenu_v01) is exactly the old behaviour: the W86 map, slot 1 = the existing map save,
    /// ov_world_N for 2–5, the prologue at the wagon for a new world. V2 (MainMenu_V2_v01): HangarLab_v01 (the base, 31.10; was VanOnly_v01), five new empty
    /// slots in their own files (ov_v2_world_N), never the v1 map save, and the prologue never runs (explicit flag, not
    /// only a scene path). The runtime (WorldLaunchV01) holds the target the menu set on Awake.
    /// </summary>
    public sealed class WorldLaunchTargetV01
    {
        public const string V1MapScene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        public const string V1MenuScene = "Assets/OnlyVolunteers/Scenes/Menu/MainMenu_v01.unity";
        /// <summary>V2 start location (Fedya 31.10): the base hangar. VanOnly_v01 stays in the V2 build as a test floor.</summary>
        public const string V2GameScene = "Assets/OnlyVolunteers/Scenes/Dev/HangarLab_v01.unity";
        public const string V2VanOnlyScene = "Assets/OnlyVolunteers/Scenes/Dev/VanOnly_v01.unity";
        public const string V2MenuScene = "Assets/OnlyVolunteers/Scenes/Menu/MainMenu_V2_v01.unity";

        /// <summary>v1 slot 1 = the existing map save (the play scene's own file names), never renamed.</summary>
        public const string V1Slot1Editor = "capture_stageA_editor_W85_v02.json", V1Slot1Build = "capture_stageA_W85_v02.json";

        public GameEditionV01 Edition { get; }
        public string GameScene { get; }
        public string MenuScene { get; }
        /// <summary>The v1 prologue hook may run for a new world (V1 only; V2 never).</summary>
        public bool PrologueAllowed { get; }

        WorldLaunchTargetV01(GameEditionV01 edition, string gameScene, string menuScene, bool prologueAllowed)
        {
            Edition = edition; GameScene = gameScene; MenuScene = menuScene; PrologueAllowed = prologueAllowed;
        }

        public static readonly WorldLaunchTargetV01 V1 = new WorldLaunchTargetV01(GameEditionV01.V1Map, V1MapScene, V1MenuScene, true);
        public static readonly WorldLaunchTargetV01 V2 = new WorldLaunchTargetV01(GameEditionV01.V2, V2GameScene, V2MenuScene, false);

        /// <summary>A menu's target: its edition's defaults, with the game scene and the return menu overridden when given
        /// (empty = the default). The prologue follows the edition only.</summary>
        public static WorldLaunchTargetV01 For(GameEditionV01 edition, string gameScene, string menuScene)
        {
            var d = edition == GameEditionV01.V2 ? V2 : V1;
            return new WorldLaunchTargetV01(d.Edition, string.IsNullOrEmpty(gameScene) ? d.GameScene : gameScene,
                string.IsNullOrEmpty(menuScene) ? d.MenuScene : menuScene, d.PrologueAllowed);
        }

        /// <summary>Slot files (slot 0..4). V1: slot 0 = the map save, slots 1–4 = ov_world_2..5. V2: ov_v2_world_1..5.
        /// The editor adds "_editor" like the other editor saves.</summary>
        public static string SlotFileName(GameEditionV01 edition, int slot, bool editor)
        {
            if (edition == GameEditionV01.V2)
                return "ov_v2_world_" + (System.Math.Max(0, slot) + 1).ToString(CultureInfo.InvariantCulture) + (editor ? "_editor.json" : ".json");
            if (slot <= 0) return editor ? V1Slot1Editor : V1Slot1Build;
            return "ov_world_" + (slot + 1).ToString(CultureInfo.InvariantCulture) + (editor ? "_editor.json" : ".json");
        }

        /// <summary>The prologue hook's guard: the target allows it (V1 only), a NEW world was launched from the menu and not
        /// yet claimed, and the loaded scene is the v1 map.</summary>
        public static bool PrologueMayRun(bool prologueAllowed, bool launched, bool newWorld, bool claimed, string scenePath) =>
            prologueAllowed && launched && newWorld && !claimed && scenePath == V1MapScene;

        public override string ToString() => Edition + " → " + GameScene + " (menu " + MenuScene + ", prologue " + (PrologueAllowed ? "on" : "off") + ")";
    }
}
