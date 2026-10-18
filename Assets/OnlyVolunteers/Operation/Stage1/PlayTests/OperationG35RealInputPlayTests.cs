using System.Collections;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    public sealed partial class OperationRealInputPlayTests
    {
        [UnityTest, NUnit.Framework.Order(8), NUnit.Framework.Timeout(240000)]
        public IEnumerator G35_PrepOnlyPreciseStrapsAllToolsAndRightArm() => Run("g35-straps", 220f);
        [UnityTest, NUnit.Framework.Order(9), NUnit.Framework.Timeout(180000)]
        public IEnumerator G35_HeavyGurneyBrakesAgainstLoadingAndMovesWithDeliberateGrab() => Run("g35-brake", 160f);
    }
}
