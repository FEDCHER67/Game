using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Capture.Tests
{
    public sealed partial class CaptureDeliveryPlayTests
    {
        [UnityTest, Order(5), Timeout(300000)]
        public IEnumerator Rework_BagIsTheRagdoll_TakeOffTable_RPack_ECarry_LmbDrag_Throw_River_SaveReload()
        {
            CaptureTestHooks.SaveSlot = "capture_stageA_corpse_test.json";
            string path = System.IO.Path.Combine(Application.persistentDataPath, "OnlyVolunteers", CaptureTestHooks.SaveSlot);
            if (System.IO.File.Exists(path)) System.IO.File.Delete(path);
            yield return LoadScene(); yield return Run("corpse", 240f);
            yield return LoadScene(); yield return Run("corpse-reload", 30f);
        }
        [UnityTest, Order(6), Timeout(180000)]
        public IEnumerator G35_UnbaggedRagdollRealMouseDrops_RiverLakeCanal()
        {
            CaptureTestHooks.SaveSlot = "capture_stageA_water_test.json";
            string path = System.IO.Path.Combine(Application.persistentDataPath, "OnlyVolunteers", CaptureTestHooks.SaveSlot);
            if (System.IO.File.Exists(path)) System.IO.File.Delete(path);
            yield return LoadScene(); yield return Run("water", 160f);
        }
    }
}
