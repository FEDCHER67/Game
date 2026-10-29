using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>Van cargo containment (ECONOMY §6.2, "Решение Феди 29.10 — удержание пленника"): capacity from the paid
    /// steps, the strap book (load order, up to the capacity, stable rings, freed on unload), a strapped captive never tries
    /// to get out, and the one knock gate (tied hands or padded walls only).</summary>
    public sealed class CargoContainmentRulesTests
    {
        private sealed class Npc
        {
            public readonly string Name;
            public Npc(string name) { Name = name; }
            public override string ToString() => Name;
        }

        [TestCase(false, false, 3)]
        [TestCase(true, false, 4)]
        [TestCase(true, true, 5)]
        [TestCase(false, true, 4)]
        public void Capacity_FromThePaidSteps(bool one, bool two, int expected) =>
            Assert.That(CargoContainmentRules.Capacity(one, two), Is.EqualTo(expected));

        [Test]
        public void Knock_BlockedOnlyByTiedHandsOrPaddedWalls()
        {
            Assert.That(CargoContainmentRules.CanKnock(false, false), Is.True, "stock van or containment I: he knocks");
            Assert.That(CargoContainmentRules.CanKnock(false, true), Is.False, "containment II: padded walls");
            Assert.That(CargoContainmentRules.CanKnock(true, false), Is.False, "tied hands");
            Assert.That(CargoContainmentRules.CanKnock(true, true), Is.False);
        }

        [Test]
        public void Escape_OnlyWhenNotStrapped()
        {
            Assert.That(CargoContainmentRules.CanTryEscape(false), Is.True);
            Assert.That(CargoContainmentRules.CanTryEscape(true), Is.False);
        }

        [Test]
        public void Straps_NobodyWithoutTheUpgrade()
        {
            var book = new CargoStrapBook<Npc>();
            var a = new Npc("a");
            Assert.That(book.Update(false, 5, new[] { a }), Is.Empty);
            Assert.That(book.IsStrapped(a), Is.False);
            Assert.That(CargoContainmentRules.CanTryEscape(book.IsStrapped(a)), Is.True, "stock van: the open door still tempts him");
        }

        [Test]
        public void Straps_EveryLoadedUpToTheCapacity_InLoadOrder_StrappedCannotLeave()
        {
            var book = new CargoStrapBook<Npc>();
            Npc a = new Npc("a"), b = new Npc("b"), c = new Npc("c"), d = new Npc("d");
            List<Npc> got = book.Update(true, 3, new[] { a, b });
            Assert.That(got, Is.EqualTo(new[] { a, b }));
            got = book.Update(true, 3, new[] { a, b, c, d });
            Assert.That(got, Is.EqualTo(new[] { c }), "one ring left: the fourth rides unstrapped (overloaded anyway)");
            Assert.That(book.SlotOf(a), Is.EqualTo(0));
            Assert.That(book.SlotOf(b), Is.EqualTo(1));
            Assert.That(book.SlotOf(c), Is.EqualTo(2));
            Assert.That(book.IsStrapped(d), Is.False);
            Assert.That(book.Count, Is.EqualTo(3));
            foreach (Npc n in new[] { a, b, c }) Assert.That(CargoContainmentRules.CanTryEscape(book.IsStrapped(n)), Is.False, n + " is strapped");
            Assert.That(CargoContainmentRules.CanTryEscape(book.IsStrapped(d)), Is.True);
        }

        [Test]
        public void Straps_UnloadFreesTheRing_OthersKeepTheirs_NextOneTakesIt()
        {
            var book = new CargoStrapBook<Npc>();
            Npc a = new Npc("a"), b = new Npc("b"), c = new Npc("c"), d = new Npc("d");
            book.Update(true, 3, new[] { a, b, c, d });
            // b dragged out (unloaded): his ring is free, the others stay where they are, d gets b's ring
            List<Npc> got = book.Update(true, 3, new[] { a, c, d });
            Assert.That(got, Is.EqualTo(new[] { d }));
            Assert.That(book.SlotOf(a), Is.EqualTo(0));
            Assert.That(book.SlotOf(d), Is.EqualTo(1));
            Assert.That(book.SlotOf(c), Is.EqualTo(2));
            Assert.That(book.IsStrapped(b), Is.False, "out of the bay = unstrapped");
            // the same set again changes nothing (no re-strapping every tick)
            Assert.That(book.Update(true, 3, new[] { a, c, d }), Is.Empty);
            Assert.That(book.At(1), Is.SameAs(d));
        }

        [Test]
        public void Straps_CapacityStepsAddRings_UpgradeRemovedFreesAll()
        {
            var book = new CargoStrapBook<Npc>();
            var npcs = new[] { new Npc("1"), new Npc("2"), new Npc("3"), new Npc("4"), new Npc("5"), new Npc("6") };
            book.Update(true, 3, npcs);
            Assert.That(book.Count, Is.EqualTo(3));
            book.Update(true, 5, npcs);
            Assert.That(book.Count, Is.EqualTo(5), "capacity II: five rings");
            Assert.That(book.IsStrapped(npcs[5]), Is.False);
            book.Update(true, 9, npcs);
            Assert.That(book.Count, Is.EqualTo(5), "never above the maximum");
            book.Update(false, 5, npcs);
            Assert.That(book.Count, Is.EqualTo(0));
            Assert.That(book.Update(true, 5, null), Is.Empty);
        }
    }
}
