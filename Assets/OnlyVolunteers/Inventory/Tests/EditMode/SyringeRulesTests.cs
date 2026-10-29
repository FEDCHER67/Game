using System;
using NUnit.Framework;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Inventory.Tests
{
    public sealed class SyringeRulesTests
    {
        private sealed class Payout : ISyringeSalePayout
        {
            public int Calls; public bool Ok = true; public SyringeSaleReceipt Last;
            public bool TryCommit(SyringeSaleReceipt sale, SyringeSalesSave next, SyringeInstance after)
            { Calls++; Last = sale; Assert.True(next.SoldPortions.Contains(sale.PortionId)); return Ok; }
        }
        private sealed class Prices : ISyringePriceLookup
        {
            public string Id; public int Calls;
            public bool TryGetPrice(string id, out int dollars) { Calls++; Id = id; dollars = 37; return true; }
        }
        private sealed class Catalog : IItemCatalog
        {
            public bool TryGet(int id, out ItemInfo info) { info = new ItemInfo(id, 1, 1, SyringeKind.Blood); return true; }
        }
        private static T RoundTrip<T>(T value)
        {
#if G49_STANDALONE
            var options = new System.Text.Json.JsonSerializerOptions { IncludeFields = true };
            return System.Text.Json.JsonSerializer.Deserialize<T>(System.Text.Json.JsonSerializer.Serialize(value, options), options);
#else
            return UnityEngine.JsonUtility.FromJson<T>(UnityEngine.JsonUtility.ToJson(value));
#endif
        }
        private static SyringeInstance Full(string person = "person-a", int portion = 1)
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            s.PersonId = person; s.Fill = 1;
            s.Portion = new BloodPortion { Id = person + "/blood/" + portion, PersonId = person, FreshSeconds = 120 };
            return s;
        }
        [TearDown] public void ResetPrices() { BuyerCatalog.SyringePrices = null; }

        [TestCase(SyringeKind.Blood)] [TestCase(SyringeKind.Anaesthesia)]
        public void FirstSuccessfulUseBindsAndSamePersonRemainsValid(SyringeKind kind)
        {
            var s = SyringeInstance.New(kind); int calls = 0;
            Assert.AreEqual(SyringeUseResult.Success, SyringeRules.TryUse(s, kind, "a", true, true, () => { calls++; return true; }));
            Assert.AreEqual("a", s.PersonId);
            Assert.AreEqual(SyringeUseResult.Success, SyringeRules.TryUse(s, kind, "a", true, true, () => { calls++; return true; }));
            Assert.AreEqual(2, calls);
        }
        [TestCase(false, true)] [TestCase(true, false)]
        public void DeadOrInvalidTargetNeverInvokesProcedure(bool alive, bool valid)
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            SyringeRules.TryUse(s, s.Kind, "a", alive, valid, () => { Assert.Fail("draw must not run"); return true; });
            Assert.IsEmpty(s.PersonId);
        }
        [Test] public void FailedAttemptHoverAndCancellationDoNotBind()
        {
            var s = SyringeInstance.New(SyringeKind.Blood);
            Assert.AreEqual(SyringeUseResult.Success, SyringeRules.Check(s, s.Kind, "a", true, true));
            Assert.AreEqual(SyringeUseResult.Failed, SyringeRules.TryUse(s, s.Kind, "a", true, true, () => false));
            s.Fill = .4f; s.PendingPersonId = "a"; SyringeRules.CancelDraw(s);
            Assert.IsEmpty(s.PersonId); Assert.IsEmpty(s.PendingPersonId); Assert.AreEqual(0, s.Fill);
        }
        [Test] public void AnotherPersonRefusedBeforeAnyDrawOrDose()
        {
            var s = Full(); int calls = 0;
            Assert.AreEqual(SyringeUseResult.OtherPerson, SyringeRules.TryUse(s, s.Kind, "person-b", true, true, () => { calls++; return true; }));
            Assert.AreEqual(0, calls); Assert.AreEqual(1, s.Fill);
            Assert.AreEqual("Этот шприц уже использован на другом человеке", SyringeRules.OtherPersonNotice);
        }
        [Test] public void TypesCannotBeInterchangedAndGonePersonNeverMakesNew()
        {
            var s = Full();
            Assert.AreEqual(SyringeUseResult.WrongType, SyringeRules.Check(s, SyringeKind.Anaesthesia, s.PersonId, true, true));
            Assert.AreEqual(SyringeUseResult.InvalidTarget, SyringeRules.Check(s, s.Kind, s.PersonId, false, true));
            SyringeRules.Empty(s);
            Assert.AreEqual(SyringeUseResult.OtherPerson, SyringeRules.Check(s, s.Kind, "replacement-npc", true, true));
        }
        [Test] public void HandOverDropEmptyPackAndSaveKeepSameInstanceAndBinding()
        {
            var s = Full(); string id = s.ItemId;
            var a = new InventoryModel(2, 2, new Catalog()); var b = new InventoryModel(2, 2, new Catalog());
            Assert.AreEqual(1, a.TryAdd(new ItemStack(303, 1, 2, s)));
            ItemStack dropped = RoundTrip(a.TakeFromSlot(0, 1));
            Assert.AreEqual(1, b.TryAdd(dropped));
            var moved = b.GetSlot(0).Syringe;
            var packed = SyringeRules.Pack(moved);
            Assert.True(packed.Sealed); Assert.AreEqual(s.Portion.Id, packed.Id);
            SyringeRules.Empty(moved);
            var block = RoundTrip(new SyringeSaveBlock { Items = { moved } });
            Assert.AreEqual(id, block.Items[0].ItemId); Assert.AreEqual("person-a", block.Items[0].PersonId);
            var world = RoundTrip(new SyringeSaveBlock { WorldItems = { new SyringeWorldSave {
                Item = moved.Copy(), DefinitionId = 303, X = 4, Y = 2, Z = -1 } } });
            Assert.AreEqual(id, world.WorldItems[0].Item.ItemId); Assert.AreEqual("person-a", world.WorldItems[0].Item.PersonId);
            Assert.AreEqual(4, world.WorldItems[0].X);
        }
        [Test] public void SyringesNeverMergeAndDuplicateInstancePickupIsRejected()
        {
            var model = new InventoryModel(3, 3, new Catalog());
            Assert.AreEqual(2, model.TryAdd(303, 2, 2));
            Assert.AreNotEqual(model.GetSlot(0).Syringe.ItemId, model.GetSlot(1).Syringe.ItemId);
            Assert.AreEqual(0, model.TryAdd(model.GetSlot(0)));
        }
        [Test] public void UnknownLegacyHistoryIsNeverCleanedOnLoad()
        {
            var s = RoundTrip(SyringeSaveBlock.Legacy("old", SyringeKind.Blood));
            Assert.AreEqual(SyringeUseResult.LegacyUnknown, SyringeRules.Check(s, s.Kind, "a", true, true));
        }
        [TestCase(SyringeReturnChoice.TakeEmpty)] [TestCase(SyringeReturnChoice.LeaveWithBuyer)]
        public void FirstSaleReturnChoiceSameItemBindingAndOnePayout(SyringeReturnChoice choice)
        {
            var s = Full(); string id = s.ItemId; var p = new Payout(); var sales = new SyringeSaleRules();
            var blood = s.Portion;
            Assert.True(sales.TryConfirm("sale", blood, s, 4, p, out var r, choice));
            Assert.AreEqual(10, p.Last.Amount); Assert.AreEqual(55, r.XpEach); Assert.AreEqual(4, r.Participants);
            Assert.AreEqual(id, s.ItemId); Assert.AreEqual("person-a", s.PersonId); Assert.IsNull(s.Portion);
            Assert.AreEqual(choice == SyringeReturnChoice.LeaveWithBuyer, s.Discarded);
            Assert.True(sales.TryConfirm("sale", blood, s, 4, p, out _)); Assert.AreEqual(1, p.Calls);
        }
        [Test] public void DefaultReturnsEmptyAndTeamFlagSurvivesLoadNewSyringeAndNewParticipant()
        {
            var s = Full(); var p = new Payout(); var sales = new SyringeSaleRules();
            Assert.True(sales.TryConfirm("one", s.Portion, s, 1, p, out var first));
            Assert.AreEqual(SyringeReturnChoice.TakeEmpty, first.ReturnChoice); Assert.False(s.Discarded);
            sales = new SyringeSaleRules(RoundTrip(sales.Snapshot)); s = Full("other-npc");
            Assert.True(sales.TryConfirm("two", s.Portion, s, 2, p, out var second));
            Assert.AreEqual(8, p.Last.Amount); Assert.AreEqual(5, second.XpEach); Assert.AreEqual(2, p.Calls);
        }
        [Test] public void OnePortionCannotBePaidAsSyringeThenBagOrWithAnotherTransactionId()
        {
            var s = Full(); var blood = s.Portion.Copy(); var p = new Payout(); var sales = new SyringeSaleRules();
            Assert.True(sales.TryConfirm("one", s.Portion, s, 1, p, out _));
            blood.Sealed = true;
            Assert.False(sales.TryConfirm("bag", blood, null, 1, p, out _));
            s.Portion = blood.Copy(); s.Portion.Sealed = false;
            Assert.False(sales.TryConfirm("new-id", s.Portion, s, 1, p, out _)); Assert.AreEqual(1, p.Calls);
        }
        [Test] public void BagFirstDoesNotRepeatFirstBloodXpAndPackedPortionCannotStayInSyringe()
        {
            var s = Full(); var portion = SyringeRules.Pack(s); var p = new Payout(); var sales = new SyringeSaleRules();
            Assert.False(sales.TryConfirm("invalid", portion, s, 1, p, out _));
            Assert.True(sales.TryConfirm("bag", portion, null, 1, p, out var bag)); Assert.AreEqual(55, bag.XpEach);
            s = Full("next"); Assert.True(sales.TryConfirm("syringe", s.Portion, s, 1, p, out var r));
            Assert.AreEqual(10, r.Amount); Assert.AreEqual(5, r.XpEach);
        }
        [Test] public void FailedPayoutLeavesPortionBindingAndFirstFlagUntouched()
        {
            var s = Full(); var p = new Payout { Ok = false }; var sales = new SyringeSaleRules();
            Assert.False(sales.TryConfirm("sale", s.Portion, s, 1, p, out _));
            Assert.NotNull(s.Portion); Assert.False(sales.Snapshot.FirstSyringeSold); Assert.AreEqual("person-a", s.PersonId);
        }
        [Test] public void FreshnessUsesOnlyActiveSecondsAndExpiredSaleNeverCallsPayout()
        {
            var s = Full(); var p = new Payout();
            SyringeRules.TickFreshness(s, 0); Assert.AreEqual(120, s.Portion.FreshSeconds);
            SyringeRules.TickFreshness(s, 120);
            Assert.False(new SyringeSaleRules().TryConfirm("expired", s.Portion, s, 1, p, out _)); Assert.AreEqual(0, p.Calls);
        }
        [TestCase(SyringeKind.Blood, "syringe_blood")] [TestCase(SyringeKind.Anaesthesia, "syringe_anaesthesia")]
        public void PriceUsesOneLookupById(SyringeKind kind, string id)
        {
            Assert.AreEqual(2, SyringeRules.Price(kind));
            var prices = new Prices(); BuyerCatalog.SyringePrices = prices;
            Assert.AreEqual(37, SyringeRules.Price(kind)); Assert.AreEqual(id, prices.Id); Assert.AreEqual(1, prices.Calls);
        }
        [Test] public void SaleReadsG48IdOnceAndDoesNotAcceptClientMoney()
        {
            var prices = new Prices(); BuyerCatalog.SyringePrices = prices; var s = Full(); var p = new Payout();
            Assert.True(new SyringeSaleRules().TryConfirm("one", s.Portion, s, 1, p, out _));
            Assert.AreEqual("c01_blood_first", prices.Id); Assert.AreEqual(1, prices.Calls); Assert.AreEqual(37, p.Last.Amount);
        }
        [Test] public void G48JsonAdapterReadsActualSyringeAndC01DataByAlias()
        {
            var catalog = EconomyCatalog.Load("C:/Dev/Game/Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json");
            BuyerCatalog.SyringePrices = new G48SyringePriceLookup(catalog);
            Assert.AreEqual(2, SyringeRules.Price(SyringeKind.Blood)); Assert.AreEqual(2, SyringeRules.Price(SyringeKind.Anaesthesia));
            Assert.AreEqual(10, BuyerCatalog.SyringePrice("c01_blood_first")); Assert.AreEqual(8, BuyerCatalog.SyringePrice("c01_blood_repeat"));
        }
        [Test] public void ConcurrentConfirmationsOfSamePortionBookOnePayout()
        {
            var s = Full(); var blood = s.Portion; var sales = new SyringeSaleRules(); var p = new Payout();
            int success = 0;
            System.Threading.Tasks.Parallel.For(0, 2, n => {
                if (sales.TryConfirm("concurrent-" + n, blood, s, 1, p, out _)) System.Threading.Interlocked.Increment(ref success);
            });
            Assert.AreEqual(1, success); Assert.AreEqual(1, p.Calls);
        }
        [Test] public void DailyStartJoinLoadSameIdNoDoublingAndNewSyringeAtSix()
        {
            var d = new DailySyringeFindSave(); long now = 6 * 3600;
            Assert.True(DailySyringeFindRules.Advance(d, "world", now, true)); string id = d.Uncollected.ItemId;
            Assert.IsEmpty(d.Uncollected.PersonId); Assert.IsNull(d.Uncollected.Portion);
            Assert.False(DailySyringeFindRules.Advance(d, "world", now, true)); d = RoundTrip(d);
            Assert.False(DailySyringeFindRules.Advance(d, "world", now, true)); Assert.AreEqual(id, d.Uncollected.ItemId);
            Assert.NotNull(DailySyringeFindRules.Collect(d, id));
            Assert.False(DailySyringeFindRules.Advance(d, "world", now + 86399, true));
            Assert.True(DailySyringeFindRules.Advance(d, "world", now + 86400, true)); Assert.AreNotEqual(id, d.Uncollected.ItemId);
        }
        [Test] public void UncollectedNeverPilesUpAndClosedWorldNeverGrantsOrBackfills()
        {
            var d = new DailySyringeFindSave();
            Assert.False(DailySyringeFindRules.Advance(d, "w", 21600, false)); Assert.IsNull(d.Uncollected);
            Assert.True(DailySyringeFindRules.Advance(d, "w", 21600, true)); string id = d.Uncollected.ItemId;
            Assert.False(DailySyringeFindRules.Advance(d, "w", 21600 + 5 * 86400, true)); Assert.AreEqual(id, d.Uncollected.ItemId);
            DailySyringeFindRules.Collect(d, id);
            Assert.False(DailySyringeFindRules.Advance(d, "w", 21600 + 5 * 86400, true)); Assert.IsNull(d.Uncollected);
        }
        [Test] public void BeforeSixAndAdditionalAuthoredSpotsDoNotGuaranteeExtraItems()
        {
            Assert.AreEqual(-1, DailySyringeFindRules.MorningId(21599)); Assert.AreEqual(0, DailySyringeFindRules.MorningId(21600));
            var spot = new SyringeFindSpot { Id = "authored-bin", Kind = SyringeKind.Anaesthesia };
            Assert.False(spot.Enabled);
        }
    }
}
