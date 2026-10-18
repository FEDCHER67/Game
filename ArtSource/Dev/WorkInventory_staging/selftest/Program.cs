// G39 console runner: the same independent scenarios are also exposed as NUnit test cases.
using System;
using WorkInventory.Checks;
internal static class Program
{
    private static int Main()
    {
        int passed = 0, failed = 0;
        foreach (var test in Scenarios.All())
        {
            try { test.Run(); passed++; Console.WriteLine("PASS " + test.Name); }
            catch (Exception e) { failed++; Console.WriteLine("FAIL " + test.Name + ": " + e); }
        }
        Console.WriteLine($"RESULT {(failed == 0 ? "PASS" : "FAIL")} {passed}/{passed + failed}");
        return failed == 0 ? 0 : 1;
    }
}
