using System.Collections.Generic;
using NUnit.Framework;
using WorkInventory.Checks;

namespace WorkInventory.Tests
{
    public sealed class AcceptanceTests
    {
        public static IEnumerable<TestCaseData> Cases()
        { foreach (var scenario in Scenarios.All()) yield return new TestCaseData(scenario).SetName(scenario.Name); }
        [TestCaseSource(nameof(Cases))]
        public void InventoryRule(Scenario scenario) => scenario.Run();
    }
}
