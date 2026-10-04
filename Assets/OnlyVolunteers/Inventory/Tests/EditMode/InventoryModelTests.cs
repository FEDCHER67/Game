using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Inventory.Tests
{
    public sealed class InventoryModelTests
    {
        private const int Heart = 1;   // size 2, unstackable
        private const int Kidney = 2;  // size 1, unstackable
        private const int Bag = 3;     // size 1, stack 5
        private const int Gurney = 4;  // size 50: never fits

        private sealed class TestCatalog : IItemCatalog
        {
            private readonly Dictionary<int, ItemInfo> items = new Dictionary<int, ItemInfo>
            {
                { Heart, new ItemInfo(Heart, 2, 1) },
                { Kidney, new ItemInfo(Kidney, 1, 1) },
                { Bag, new ItemInfo(Bag, 1, 5) },
                { Gurney, new ItemInfo(Gurney, 50, 1) },
            };

            public bool TryGet(int itemId, out ItemInfo info) => items.TryGetValue(itemId, out info);
        }

        private static InventoryModel Create(int slots = 6, int capacity = 10) =>
            new InventoryModel(slots, capacity, new TestCatalog());

        [Test]
        public void AddsToFirstEmptySlotAndTracksCapacity()
        {
            var inv = Create();
            inv.Select(2);
            inv.TakeFromSlot(2, 1); // no-op on empty slot

            Assert.AreEqual(1, inv.TryAdd(Heart, 1, 1000));
            Assert.AreEqual(new ItemStack(Heart, 1, 1000), inv.GetSlot(2), "empty selected slot is preferred");
            Assert.AreEqual(1, inv.TryAdd(Kidney, 1, 250));
            Assert.AreEqual(new ItemStack(Kidney, 1, 250), inv.GetSlot(0));
            Assert.AreEqual(3, inv.UsedCapacity);
        }

        [Test]
        public void StacksOnlyWithSameIdAndValue()
        {
            var inv = Create();
            Assert.AreEqual(3, inv.TryAdd(Bag, 3, 5));
            Assert.AreEqual(4, inv.TryAdd(Bag, 4, 5));
            Assert.AreEqual(new ItemStack(Bag, 5, 5), inv.GetSlot(0));
            Assert.AreEqual(new ItemStack(Bag, 2, 5), inv.GetSlot(1));
            Assert.AreEqual(1, inv.TryAdd(Bag, 1, 50));
            Assert.AreEqual(new ItemStack(Bag, 1, 50), inv.GetSlot(2), "different value does not merge");
        }

        [Test]
        public void RespectsCapacityAndPartialAdds()
        {
            var inv = Create(slots: 6, capacity: 5);
            Assert.AreEqual(2, inv.TryAdd(Heart, 1, 1000) + inv.TryAdd(Heart, 1, 1000));
            Assert.AreEqual(0, inv.TryAdd(Heart, 1, 1000), "size 2 does not fit in 1 free unit");
            Assert.AreEqual(1, inv.TryAdd(Bag, 4, 5), "partial add fills the remaining unit");
            Assert.AreEqual(0, inv.FreeCapacity);
        }

        [Test]
        public void RejectsUnknownOversizedAndInvalidCounts()
        {
            var inv = Create();
            Assert.AreEqual(0, inv.TryAdd(999, 1, 10));
            Assert.AreEqual(0, inv.TryAdd(Gurney, 1, 10));
            Assert.AreEqual(0, inv.TryAdd(Kidney, 0, 10));
            Assert.AreEqual(0, inv.TryAdd(Kidney, -3, 10));
            Assert.AreEqual(0, inv.UsedCapacity);
        }

        [Test]
        public void RunsOutOfSlots()
        {
            var inv = Create(slots: 2, capacity: 100);
            Assert.AreEqual(2, inv.TryAdd(Kidney, 3, 250));
            Assert.AreEqual(0, inv.CountThatFits(Kidney, 1, 250));
        }

        [Test]
        public void TakeFromSlotSplitsAndEmpties()
        {
            var inv = Create();
            inv.TryAdd(Bag, 4, 5);
            Assert.AreEqual(new ItemStack(Bag, 1, 5), inv.TakeFromSlot(0, 1));
            Assert.AreEqual(3, inv.GetSlot(0).Count);
            Assert.AreEqual(new ItemStack(Bag, 3, 5), inv.TakeFromSlot(0, 10));
            Assert.IsTrue(inv.GetSlot(0).IsEmpty);
            Assert.AreEqual(0, inv.UsedCapacity);
            Assert.IsTrue(inv.TakeFromSlot(-1, 1).IsEmpty);
            Assert.IsTrue(inv.TakeFromSlot(6, 1).IsEmpty);
        }

        [Test]
        public void SelectionClampsAndWraps()
        {
            var inv = Create(slots: 4);
            Assert.IsFalse(inv.Select(4));
            Assert.IsFalse(inv.Select(-1));
            Assert.AreEqual(0, inv.SelectedIndex);
            inv.SelectNext(-1);
            Assert.AreEqual(3, inv.SelectedIndex);
            inv.SelectNext(1);
            Assert.AreEqual(0, inv.SelectedIndex);
        }

        [Test]
        public void MostValuableUsesUnitValueAndLowestIndexOnTie()
        {
            var inv = Create(capacity: 100);
            Assert.AreEqual(-1, inv.MostValuableSlot());
            Assert.IsTrue(inv.MostValuableItem().IsEmpty);

            inv.TryAdd(Bag, 5, 300);     // slot 0: total 1500, unit 300
            inv.TryAdd(Kidney, 1, 650);  // slot 1
            inv.TryAdd(Heart, 1, 650);   // slot 2, same unit value as slot 1
            Assert.AreEqual(1, inv.MostValuableSlot());
            Assert.AreEqual(new ItemStack(Kidney, 1, 650), inv.MostValuableItem());
            Assert.AreEqual(new ItemStack(Kidney, 1, 650), inv.GetSlot(1), "query does not remove");
        }

        [Test]
        public void ConfiscateRemovesOneUnit()
        {
            var inv = Create();
            inv.TryAdd(Bag, 3, 40);
            inv.TryAdd(Kidney, 1, 20);
            Assert.AreEqual(new ItemStack(Bag, 1, 40), inv.ConfiscateMostValuable());
            Assert.AreEqual(2, inv.GetSlot(0).Count);
            Assert.AreEqual(3, inv.UsedCapacity);
        }

        [Test]
        public void ArrestPenaltyTakesTenPercentCashAndMostValuable()
        {
            var inv = Create();
            inv.AddCash(1999);
            inv.TryAdd(Heart, 1, 4200);
            inv.TryAdd(Kidney, 1, 250);

            ArrestResult result = inv.ApplyArrestPenalty();

            Assert.AreEqual(199, result.CashTaken, "rounded down");
            Assert.AreEqual(1800, inv.Cash);
            Assert.AreEqual(new ItemStack(Heart, 1, 4200), result.Confiscated);
            Assert.IsTrue(inv.GetSlot(0).IsEmpty);
            Assert.AreEqual(Kidney, inv.GetSlot(1).ItemId);
        }

        [Test]
        public void ArrestPenaltyOnEmptyInventory()
        {
            var inv = Create();
            ArrestResult result = inv.ApplyArrestPenalty();
            Assert.AreEqual(0, result.CashTaken);
            Assert.IsTrue(result.Confiscated.IsEmpty);
        }

        [Test]
        public void CashSpendingAndOverflow()
        {
            var inv = Create();
            inv.AddCash(100);
            inv.AddCash(-50);
            Assert.IsFalse(inv.TrySpendCash(101));
            Assert.IsFalse(inv.TrySpendCash(-1));
            Assert.IsTrue(inv.TrySpendCash(40));
            Assert.AreEqual(60, inv.Cash);
            inv.AddCash(int.MaxValue);
            Assert.AreEqual(int.MaxValue, inv.Cash);
        }

        [Test]
        public void EventsReportChangedSlotsSelectionAndCash()
        {
            var inv = Create();
            var slots = new List<int>();
            int selected = -1, cash = -1;
            inv.SlotChanged += slots.Add;
            inv.SelectionChanged += i => selected = i;
            inv.CashChanged += c => cash = c;

            inv.TryAdd(Kidney, 2, 250);
            inv.Select(3);
            inv.AddCash(7);

            CollectionAssert.AreEqual(new[] { 0, 1 }, slots);
            Assert.AreEqual(3, selected);
            Assert.AreEqual(7, cash);
        }

        [Test]
        public void ClearEmptiesEverything()
        {
            var inv = Create();
            inv.TryAdd(Bag, 7, 5);
            inv.Clear();
            Assert.AreEqual(0, inv.UsedCapacity);
            for (int i = 0; i < inv.SlotCount; i++)
                Assert.IsTrue(inv.GetSlot(i).IsEmpty);
        }
    }
}
