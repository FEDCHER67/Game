using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Session.Tests
{
    /// <summary>Menu for V2 (Fedya 31.10): the V1 menu keeps the W86 map, its old save as slot 1 and the prologue; the V2 menu
    /// launches the base hangar (HangarLab_v01, 31.10; VanOnly before) with five own slot files and never runs the prologue.</summary>
    public sealed class WorldLaunchTargetTests
    {
        [Test]
        public void V1_target_is_the_old_map_menu_and_prologue()
        {
            var t = WorldLaunchTargetV01.V1;
            Assert.AreEqual(GameEditionV01.V1Map, t.Edition);
            Assert.AreEqual("Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity", t.GameScene);
            Assert.AreEqual("Assets/OnlyVolunteers/Scenes/Menu/MainMenu_v01.unity", t.MenuScene);
            Assert.True(t.PrologueAllowed);
        }

        [Test]
        public void V2_target_is_the_hangar_base_and_the_v2_menu_without_prologue()
        {
            var t = WorldLaunchTargetV01.V2;
            Assert.AreEqual(GameEditionV01.V2, t.Edition);
            Assert.AreEqual("Assets/OnlyVolunteers/Scenes/Dev/HangarLab_v01.unity", t.GameScene, "Fedya 31.10: Играть starts in the base");
            Assert.AreEqual("Assets/OnlyVolunteers/Scenes/Menu/MainMenu_V2_v01.unity", t.MenuScene);
            Assert.False(t.PrologueAllowed);
        }

        [Test]
        public void For_uses_the_edition_defaults_and_overrides_only_given_paths()
        {
            var v1 = WorldLaunchTargetV01.For(GameEditionV01.V1Map, "", null);
            Assert.AreEqual(WorldLaunchTargetV01.V1MapScene, v1.GameScene);
            Assert.AreEqual(WorldLaunchTargetV01.V1MenuScene, v1.MenuScene);
            Assert.True(v1.PrologueAllowed);

            var v2 = WorldLaunchTargetV01.For(GameEditionV01.V2, "", "Assets/Some/OtherMenu.unity");
            Assert.AreEqual(WorldLaunchTargetV01.V2GameScene, v2.GameScene);
            Assert.AreEqual("Assets/Some/OtherMenu.unity", v2.MenuScene, "the pause menu returns to the launching menu");
            Assert.False(v2.PrologueAllowed);

            var v2map = WorldLaunchTargetV01.For(GameEditionV01.V2, WorldLaunchTargetV01.V1MapScene, "");
            Assert.False(v2map.PrologueAllowed, "the prologue follows the edition, not the scene");
        }

        [Test]
        public void V1_slot_files_are_unchanged()
        {
            Assert.AreEqual("capture_stageA_editor_W85_v02.json", WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, 0, true));
            Assert.AreEqual("capture_stageA_W85_v02.json", WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, 0, false));
            for (int i = 1; i < MainMenuFlowV2.SlotCount; i++)
            {
                Assert.AreEqual("ov_world_" + (i + 1) + "_editor.json", WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, i, true));
                Assert.AreEqual("ov_world_" + (i + 1) + ".json", WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, i, false));
            }
        }

        [Test]
        public void V2_has_five_own_slot_files_that_never_touch_v1_saves()
        {
            var v1 = new HashSet<string>();
            for (int i = 0; i < MainMenuFlowV2.SlotCount; i++)
            {
                v1.Add(WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, i, true));
                v1.Add(WorldLaunchTargetV01.SlotFileName(GameEditionV01.V1Map, i, false));
            }
            var v2 = new HashSet<string>();
            for (int i = 0; i < MainMenuFlowV2.SlotCount; i++)
            {
                string editor = WorldLaunchTargetV01.SlotFileName(GameEditionV01.V2, i, true);
                string build = WorldLaunchTargetV01.SlotFileName(GameEditionV01.V2, i, false);
                Assert.AreEqual("ov_v2_world_" + (i + 1) + "_editor.json", editor);
                Assert.AreEqual("ov_v2_world_" + (i + 1) + ".json", build);
                Assert.False(v1.Contains(editor) || v1.Contains(build), "V2 slot " + (i + 1) + " must not be a v1 file");
                Assert.False(editor.Contains("capture_stageA"), "never the v1 map save");
                v2.Add(editor); v2.Add(build);
            }
            Assert.AreEqual(2 * MainMenuFlowV2.SlotCount, v2.Count, "every V2 slot has its own files");
        }

        [Test]
        public void Prologue_runs_only_for_a_new_v1_world_on_the_v1_map()
        {
            string map = WorldLaunchTargetV01.V1MapScene;
            Assert.True(WorldLaunchTargetV01.PrologueMayRun(true, true, true, false, map));
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(true, false, true, false, map), "not launched from a menu");
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(true, true, false, false, map), "a loaded world");
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(true, true, true, true, map), "already claimed");
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(true, true, true, false, WorldLaunchTargetV01.V2GameScene), "not the v1 map");
        }

        [Test]
        public void Prologue_never_runs_for_a_v2_launch_even_on_the_v1_map()
        {
            var v2 = WorldLaunchTargetV01.V2;
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(v2.PrologueAllowed, true, true, false, WorldLaunchTargetV01.V1MapScene));
            Assert.False(WorldLaunchTargetV01.PrologueMayRun(v2.PrologueAllowed, true, true, false, v2.GameScene));
        }
    }
}
