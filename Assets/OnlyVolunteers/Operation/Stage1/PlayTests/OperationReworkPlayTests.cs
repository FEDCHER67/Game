using System.Collections;
using UnityEngine.TestTools;

namespace OnlyVolunteers.Operation.Stage1.Tests
{
    /// <summary>Claude rework of G35 after Fedya's 2026-10-18 playtest (approved v02 dev scene, real virtual input).</summary>
    public sealed partial class OperationRealInputPlayTests
    {
        /// <summary>Item 5: an organ has the same size in the body, on the tray, in the hand and as an inventory drop.</summary>
        [UnityTest, NUnit.Framework.Order(10), NUnit.Framework.Timeout(240000)]
        public IEnumerator Rework_OrganSameSizeInBodyTrayHandAndDrop() => Run("cl-organ-scale", 200f);
        /// <summary>v03 art evidence: syringe v02 mid-draw, blood bag v05 0/50/100 %, open belly, closed back.</summary>
        [UnityTest, NUnit.Framework.Order(11), NUnit.Framework.Timeout(240000)]
        public IEnumerator Rework_ArtV03_SyringeBagBellyBack() => Run("cl-art-v03", 200f);
    }
}
