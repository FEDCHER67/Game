using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>Claude rework of G35 after Fedya's 2026-10-18 playtest (real virtual Mouse/Keyboard; i10 map).</summary>
    public sealed partial class CaptureDeliveryPlayTests
    {
        private static IEnumerator FreshSlot(string slot)
        {
            CaptureTestHooks.SaveSlot = slot;
            string path = System.IO.Path.Combine(Application.persistentDataPath, "OnlyVolunteers", slot);
            if (System.IO.File.Exists(path)) System.IO.File.Delete(path);
            yield return LoadScene();
        }

        /// <summary>Fedya: "the straps don't work at all". Fails on the G35 build: its strap hit colliders use the table
        /// FBX's non-readable meshes, which have no collision data in a player.</summary>
        [UnityTest, Order(10), Timeout(240000)]
        public IEnumerator Rework_StrapsPrepRealInput_BandAndBuckle_AllTools_TiesCut_StruggleHeld()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("straps", 200f);
        }

        /// <summary>Fedya: a thrown ragdoll nudges the gurney a little; it never slides, tips or pushes the player.</summary>
        [UnityTest, Order(11), Timeout(180000)]
        public IEnumerator Rework_GurneyNudgedByThrownRagdoll_NeverPushesPlayer()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("gurney", 120f);
        }

        /// <summary>Fedya: R on a corpse in the field packs it into the bag ragdoll as well; E carries it, G puts it down.</summary>
        [UnityTest, Order(12), Timeout(180000)]
        public IEnumerator Rework_FieldCorpse_RPacksIntoBagRagdoll_ECarry()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("bag-field", 120f);
        }

        /// <summary>Round 2: walking into the gurney = 10-15 % walk speed and it moves along; LMB hold = 40-50 %, solid from
        /// every side (real virtual mouse for the hold).</summary>
        [UnityTest, Order(13), Timeout(240000)]
        public IEnumerator Round2_GurneyWalkPushAndLmbPush_SpeedsSolidSmooth()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("gurney2", 180f);
        }

        /// <summary>Round 2: carrying a body bag (E) caps the player at the speed the bag follows smoothly (measured).</summary>
        [UnityTest, Order(14), Timeout(240000)]
        public IEnumerator Round2_BagCarrySpeedCap_BagFollowsSmoothly()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("carry-speed", 180f);
        }

        /// <summary>Round 2 items 9-11: bags on the tray from the start; the kit is one hotbar slot (2 cycles the tools), LMB
        /// uses a tool; a field-filled blood syringe is poured into a table bag (same animation, counted once, saved); both
        /// syringes point the needle away from the player.</summary>
        [UnityTest, Order(15), Timeout(240000)]
        public IEnumerator Round2_FieldKitHotbar_FieldSyringeIntoTableBag_NeedleForward()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("field-blood", 200f);
        }

        /// <summary>Round 2 item 8: off the table (taken off, dropped, folded, on its side) no rib or organ is drawn.</summary>
        [UnityTest, Order(16), Timeout(240000)]
        public IEnumerator Round2_CorpseOffTable_InternalsNeverShow()
        {
            yield return FreshSlot("capture_stageA_rework_test.json");
            yield return Run("internals", 150f);
        }
    }
}
