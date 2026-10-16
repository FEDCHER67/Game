using System;
using System.Linq;
using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class BuyerNegotiationAndMeetingTests : BuyerTestSupport
    {
        [TestCase(0)] [TestCase(9)] [TestCase(23)]
        public void BUY05_BothStartingBuyersAvailableAtAnyHour(int hour)
        {
            clock.Now = hour * BuyerCatalog.Hour;
            Assert.That(rules.IsBuyerAvailable(Blood), Is.True); Assert.That(rules.IsBuyerAvailable(Organ), Is.True);
            Assert.That(rules.ScheduleMeeting(Blood, "b", "p1", "base", null), Is.True);
            Assert.That(rules.ScheduleMeeting(Organ, "o", "p2", "base", new[] { "a" }), Is.True);
        }
        [Test]
        public void BUY06_AuthoredLocationAndBaseAreFixedForMeeting()
        {
            rng.Value = 99; Meeting();
            Assert.That(B().Meeting.LocationId, Is.EqualTo("park-b"));
            rng.Value = 0; Group(); rules.FinishGroup(Organ); rules.BeginGroup(Organ, ProductKind.Kidney, "p1");
            Assert.That(B().Meeting.LocationId, Is.EqualTo("park-b"));
            Meeting(Blood); Assert.That(B(Blood).Meeting.LocationId, Is.EqualTo("base"));
        }
        [Test]
        public void BUY07_ArrivesInOneHourAndWaitsThreeWithExactBoundaries()
        {
            rules.ScheduleMeeting(Organ, "m", "p1", "base", new[] { "a" });
            Assert.That(B().Meeting.ArrivalAt, Is.EqualTo(3600)); Assert.That(B().Meeting.ExpiresAt, Is.EqualTo(14400));
            clock.Now = 3599; Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.False);
            clock.Now = 3600; Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.True);
            Assert.That(B().Meeting.Phase, Is.EqualTo(MeetingPhase.Waiting));
        }
        [Test]
        public void BUY08_CancelBeforeArrivalFreeAfterArrivalOnceAndImmediateRebooking()
        {
            rules.ScheduleMeeting(Organ, "early", "p1", "base", new[] { "a" });
            clock.Now = 3599; Assert.That(rules.CancelMeeting(Organ), Is.True); Assert.That(B().Respect, Is.EqualTo(30));
            Meeting(); Assert.That(rules.CancelMeeting(Organ), Is.True); Assert.That(rules.CancelMeeting(Organ), Is.False);
            rules.Tick(); Assert.That(B().Respect, Is.EqualTo(29));
            Assert.That(rules.ScheduleMeeting(Organ, "again", "p1", "base", new[] { "a" }), Is.True);
        }
        [Test]
        public void BUY08_MissingMeetingPenalizesOnceAndAllowsRebooking()
        {
            Meeting(); clock.Now = B().Meeting.ExpiresAt;
            rules.Tick(); rules.Tick(); Assert.That(B().Respect, Is.EqualTo(29));
            Assert.That(B().Meeting.HadInteraction, Is.False);
            Assert.That(rules.ScheduleMeeting(Organ, "next", "p1", "base", new[] { "a" }), Is.True);
        }
        [Test]
        public void BUY08_LoadingGoodsRecordsInteractionAndTimeoutReleasesThem()
        {
            Meeting(); string id = Add(); Assert.That(rules.LoadItem(Organ, id, "p1"), Is.True);
            Assert.That(B().Meeting.HadInteraction, Is.True); clock.Now = B().Meeting.ExpiresAt;
            rules.Tick(); rules.Tick(); Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(I(id).MeetingId, Is.Empty);
        }
        [Test]
        public void BUY08_NegotiatedMeetingWithoutSaleIsNotMissed()
        {
            Meeting(); Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.True);
            rng.Value = 99; Assert.That(rules.AskMeeting(Organ, "p1", 20), Is.True);
            Assert.That(rules.FinishGroup(Organ), Is.True); clock.Now = B().Meeting.ExpiresAt;
            rules.Tick(); rules.Tick(); Assert.That(B().Respect, Is.EqualTo(30));
            Assert.That(B().Meeting.PenaltyApplied, Is.False); Assert.That(B().Meeting.HadSale, Is.False);
        }
        [Test]
        public void BUY08_AttendanceWithoutNegotiationPreventsMissPenaltyAndSurvivesSave()
        {
            Meeting(); Assert.That(rules.RecordMeetingAttendance(Organ, "p2"), Is.True);
            var saved = rules.Snapshot; rules = new BuyerRules(clock, rng, saved);
            clock.Now = B().Meeting.ExpiresAt; rules.Tick();
            Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(B().Meeting.HadInteraction, Is.True);
        }
        [Test]
        public void BUY08_AttendanceRequiresPresentPlayerWithinWait()
        {
            rules.ScheduleMeeting(Organ, "m", "p1", "base", new[] { "a" });
            Assert.That(rules.RecordMeetingAttendance(Organ, "p1"), Is.False);
            clock.Now = 3600; rules.SetPresentParticipants("p1");
            Assert.That(rules.RecordMeetingAttendance(Organ, "p2"), Is.False);
            clock.Now = 14400; Assert.That(rules.RecordMeetingAttendance(Organ, "p1"), Is.False);
            Assert.That(B().Respect, Is.EqualTo(29)); Assert.That(B().Meeting.HadInteraction, Is.False);
        }
        [TestCase(false)] [TestCase(true)]
        public void BUY08_BUY21_FailedDealCostsExactlyOneIncludingCancelOrTimeout(bool cancel)
        {
            Meeting(); Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.True);
            rng.Value = 99; rules.AskMeeting(Organ, "p1", 20); rules.AskMeeting(Organ, "p1", 10);
            Assert.That(B().Respect, Is.EqualTo(29));
            if (cancel) Assert.That(rules.CancelMeeting(Organ), Is.True);
            clock.Now = B().Meeting.ExpiresAt; rules.Tick(); rules.Tick();
            Assert.That(B().Respect, Is.EqualTo(29)); Assert.That(B().Meeting.PenaltyApplied, Is.False);
        }
        [TestCase(false)] [TestCase(true)]
        public void BUY08_BUY20_WalkingAwayAfterFivePercentRefusalIsFree(bool cancel)
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99;
            rules.AskMeeting(Organ, "p1", 5); Assert.That(rules.LeaveNegotiation(Organ, "p1"), Is.True);
            if (cancel) Assert.That(rules.CancelMeeting(Organ), Is.True);
            clock.Now = B().Meeting.ExpiresAt; rules.Tick();
            Assert.That(B().Respect, Is.EqualTo(30)); Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).BannedUntil, Is.Zero);
        }
        [TestCase(false,false,false)] [TestCase(true,false,false)]
        [TestCase(false,true,false)] [TestCase(true,true,false)]
        [TestCase(false,false,true)] [TestCase(true,false,true)]
        [TestCase(false,true,true)] [TestCase(true,true,true)]
        public void BUY08_CancelAndCompleteAfterSaleAreFree(bool cancel, bool nextGroup, bool expired)
        {
            Meeting(); Sell(); string remaining = Add(ProductKind.Liver); rules.LoadItem(Organ, remaining, "p1");
            if (nextGroup) Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.True);
            if (expired) clock.Now = B().Meeting.ExpiresAt;
            int before = B().Respect;
            Assert.That(cancel ? rules.CancelMeeting(Organ) : rules.CompleteMeeting(Organ), Is.True);
            Assert.That(B().Respect, Is.EqualTo(before)); Assert.That(B().Meeting.Phase, Is.EqualTo(MeetingPhase.Completed));
            Assert.That(B().Meeting.ActiveGroup, Is.Null); Assert.That(I(remaining).MeetingId, Is.Empty);
            Assert.That(I(remaining).Sold, Is.False); Assert.That(rules.CancelMeeting(Organ), Is.False);
            Assert.That(rules.CompleteMeeting(Organ), Is.False);
            Assert.That(rules.ScheduleMeeting(Organ, "next", "p1", "base", new[] { "a" }), Is.True);
        }
        [Test]
        public void BUY08_SuccessfulMeetingCanCompleteWithoutCancelPenaltyAndRebook()
        {
            Meeting(); Assert.That(rules.CompleteMeeting(Organ), Is.False); Sell();
            Assert.That(rules.CompleteMeeting(Organ), Is.True); Assert.That(B().Respect, Is.EqualTo(32));
            Assert.That(rules.CompleteMeeting(Organ), Is.False);
            Assert.That(rules.ScheduleMeeting(Organ, "next", "p1", "base", new[] { "a" }), Is.True);
        }
        [Test]
        public void BUY09_ParallelMeetingsPerBuyerOnlyOneEach()
        {
            Meeting(); long expiry = B().Meeting.ExpiresAt; Meeting(Blood);
            Assert.That(B().Meeting.ExpiresAt, Is.EqualTo(expiry));
            Assert.That(rules.ScheduleMeeting(Organ, "duplicate", "p1", "base", new[] { "a" }), Is.False);
            Assert.That(rules.ScheduleMeeting(Blood, "duplicate2", "p2", "base", null), Is.False);
        }
        [Test]
        public void BUY10_OnlyPhysicalHolderLoadsAndOnlyNegotiatorConfirms()
        {
            Meeting(); Group(); string id = Add(holder: "p2");
            Assert.That(rules.LoadItem(Organ, id, "p1"), Is.False); Assert.That(rules.LoadItem(Organ, id, "p2"), Is.True);
            Assert.That(rules.ConfirmSale(Request(new[] { id }, player: "p2")).Error, Is.EqualTo(SaleError.NotNegotiator));
            Assert.That(I(id).Sold, Is.False); Assert.That(rules.ConfirmSale(Request(new[] { id })).Success, Is.True);
        }
        [TestCase(Blood, ProductKind.Kidney)] [TestCase(Blood, ProductKind.Liver)]
        [TestCase(Blood, ProductKind.Lungs)] [TestCase(Blood, ProductKind.Heart)]
        [TestCase(Blood, ProductKind.Eye)] [TestCase(Blood, ProductKind.Brain)]
        [TestCase(Organ, ProductKind.BloodBag)] [TestCase(Organ, ProductKind.IntroSyringe)]
        public void BUY10_BUY48_LoadRejectsKindsBuyerDoesNotBuyWithoutPenalty(string buyer, ProductKind kind)
        {
            Meeting(buyer); string id = Add(kind); int before = B(buyer).Respect;
            Assert.That(rules.LoadItem(buyer, id, "p1", out var error), Is.False);
            Assert.That(error, Is.EqualTo(SaleError.InvalidRequest));
            Assert.That(rules.LoadItem(buyer, id, "p1"), Is.False);
            Assert.That(I(id).MeetingId, Is.Empty); Assert.That(I(id).Sold, Is.False);
            Assert.That(B(buyer).Respect, Is.EqualTo(before)); Assert.That(B(buyer).Meeting.HadInteraction, Is.False);
            Assert.That(rules.Snapshot.WrongItemAttempts, Is.Empty);
        }
        [TestCase(0,40,20,5)] [TestCase(20,55,35,15)] [TestCase(40,70,50,25)]
        [TestCase(60,85,65,40)] [TestCase(80,95,80,60)]
        public void BUY18_BUY19_AllChanceCellsAndEverySkillRank(int respect, int five, int ten, int twenty)
        {
            int[] asks = {5,10,20}, expected = {five,ten,twenty};
            for (int skill = 0; skill <= 3; skill++) for (int a = 0; a < 3; a++)
                Assert.That(BuyerCatalog.NegotiationChance(respect, skill, asks[a]), Is.EqualTo(Math.Min(95, expected[a] + 5 * skill)));
        }
        [TestCase(34, NegotiationPhase.Agreed)] [TestCase(35, NegotiationPhase.CounterOffered)]
        public void BUY18_RngUsesStrictChanceBoundary(int roll, NegotiationPhase expected)
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = roll;
            Assert.That(rules.AskMeeting(Organ, "p1", 10), Is.True); Assert.That(B().Meeting.Negotiations[0].Phase, Is.EqualTo(expected));
        }
        [Test]
        public void BUY20_FirstRefusalAllowsCounterOrOnlySmallerSecondAsk()
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99;
            rules.AskMeeting(Organ, "p1", 20); int calls = rng.Calls;
            Assert.That(B().Meeting.Negotiations[0].CounterPercent, Is.EqualTo(10));
            Assert.That(rules.AskMeeting(Organ, "p1", 20), Is.False); Assert.That(rng.Calls, Is.EqualTo(calls));
            Assert.That(rules.AcceptMeetingPrice(Organ, "p1"), Is.True);
            Assert.That(B().Meeting.Negotiations[0].AgreedPercent, Is.EqualTo(10));
        }
        [Test]
        public void BUY20_FivePercentRefusalLeavesBaseOrWalkAway()
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99; rules.AskMeeting(Organ, "p1", 5);
            Assert.That(rules.AskMeeting(Organ, "p1", 5), Is.False); Assert.That(rules.AskMeeting(Organ, "p1", 0), Is.False);
            Assert.That(rules.AcceptMeetingPrice(Organ, "p1"), Is.True); Assert.That(B().Meeting.Negotiations[0].AgreedPercent, Is.Zero);
            rules.FinishGroup(Organ); rules.BeginGroup(Organ, ProductKind.Liver, "p1"); rules.AskMeeting(Organ, "p1", 5);
            Assert.That(rules.LeaveNegotiation(Organ, "p1"), Is.True);
            Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.False);
        }
        [Test]
        public void BUY21_SecondRefusalBansOnlyThatTypeThreeHoursKeepsGoods()
        {
            Meeting(); string id = Add(); rules.LoadItem(Organ, id, "p1"); rules.BeginGroup(Organ, ProductKind.Kidney, "p1");
            rng.Value = 99; rules.AskMeeting(Organ, "p1", 20); rules.AskMeeting(Organ, "p1", 10);
            Assert.That(B().Respect, Is.EqualTo(29)); Assert.That(I(id).Sold, Is.False);
            Assert.That(B().Counters.Single(c => c.Kind == ProductKind.Kidney).BannedUntil, Is.EqualTo(clock.Now + 10800));
            Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.False);
            Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.True); rules.FinishGroup(Organ);
            rules.CancelMeeting(Organ); rules.ScheduleMeeting(Organ, "new", "p1", "base", new[] { "a" });
            clock.Now += 3600; Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.False);
            clock.Now = 14400; Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.True);
        }
        [Test]
        public void BUY21_FailedTypeReleasesOnlyItsGoodsImmediatelySoTheyCanBeStashed()
        {
            rules = new BuyerRules(clock, rng, Seed(45)); Order(); Meeting();
            string kidney1 = Add(tier: QualityTier.Good, packaged: true), kidney2 = Add(holder: "p2"), liver = Add(ProductKind.Liver);
            rules.LoadItem(Organ, kidney1, "p1"); rules.LoadItem(Organ, kidney2, "p2"); rules.LoadItem(Organ, liver, "p1");
            rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99; rules.AskMeeting(Organ, "p1", 20);
            Assert.That(I(kidney1).MeetingId, Is.EqualTo(B().Meeting.Id), "First refusal does not release goods.");
            rules.AskMeeting(Organ, "p1", 10);
            Assert.That(B().Respect, Is.EqualTo(44)); Assert.That(I(kidney1).MeetingId, Is.Empty); Assert.That(I(kidney2).MeetingId, Is.Empty);
            Assert.That(I(kidney1).Sold, Is.False); Assert.That(I(kidney2).HolderId, Is.EqualTo("p2"));
            Assert.That(I(liver).MeetingId, Is.EqualTo(B().Meeting.Id));
            Assert.That(rules.DepositInStash("order", kidney1, "p1"), Is.True);
            Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.True); rules.AcceptMeetingPrice(Organ, "p1");
            Assert.That(rules.ConfirmSale(Request(new[] { liver })).Success, Is.True);
        }
        [Test]
        public void BUY21_FailedBloodNegotiationBansBloodOnly()
        {
            Meeting(Blood); string id = Add(ProductKind.BloodBag); rules.LoadItem(Blood, id, "p1");
            rules.BeginGroup(Blood, ProductKind.BloodBag, "p1"); rng.Value = 99;
            rules.AskMeeting(Blood, "p1", 20); rules.AskMeeting(Blood, "p1", 10);
            Assert.That(B(Blood).Respect, Is.EqualTo(29)); Assert.That(I(id).MeetingId, Is.Empty);
            Assert.That(B(Blood).Counters.Single(c => c.Kind == ProductKind.BloodBag).BannedUntil, Is.EqualTo(clock.Now + 10800));
            Assert.That(rules.BeginGroup(Blood, ProductKind.BloodBag, "p1"), Is.False);
            Assert.That(B().Counters.All(c => c.BannedUntil == 0), Is.True);
            rng.Value = 0; Meeting(); Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.True);
            clock.Now = B(Blood).Meeting.ExpiresAt; rules.Tick(); Assert.That(B(Blood).Respect, Is.EqualTo(29));
        }
        [TestCase("p2")] [TestCase("unknown")]
        public void BUY22_BUY41_AbsentParticipantCannotTakeOverMeeting(string player)
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99; rules.AskMeeting(Organ, "p1", 20);
            rules.SetPresentParticipants("p1"); long expiry = B().Meeting.ExpiresAt;
            Assert.That(rules.ChangeNegotiator(Organ, player), Is.False);
            Assert.That(B().Meeting.NegotiatorId, Is.EqualTo("p1")); Assert.That(B().Meeting.ExpiresAt, Is.EqualTo(expiry));
            Assert.That(B().Meeting.Negotiations.Single().NegotiatorId, Is.EqualTo("p1"));
            Assert.That(B().Meeting.Negotiations.Single().AttemptsUsed, Is.EqualTo(1));
        }
        [Test]
        public void BUY22_BUY41_HandoffKeepsAttemptAndTimerButUsesNewSkill()
        {
            var seed = Seed(); seed.Participants[1].NegotiationLevel = 3; rules = new BuyerRules(clock, rng, seed);
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99; rules.AskMeeting(Organ, "p1", 20);
            long expiry = B().Meeting.ExpiresAt;
            rules.SetPresentParticipants("p2"); Assert.That(rules.ChangeNegotiator(Organ, "p2"), Is.True);
            Assert.That(B().Meeting.Negotiations[0].AttemptsUsed, Is.EqualTo(1)); Assert.That(B().Meeting.ExpiresAt, Is.EqualTo(expiry));
            rng.Value = 49; Assert.That(rules.AskMeeting(Organ, "p2", 10), Is.True);
            Assert.That(B().Meeting.Negotiations[0].Phase, Is.EqualTo(NegotiationPhase.Agreed));
            Assert.That(B().Meeting.Negotiations[0].AttemptsUsed, Is.EqualTo(2));
        }
        [Test]
        public void BUY45_ReopeningAddingGoodsAndChangingPlayerCannotRestartChain()
        {
            Meeting(); rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); rng.Value = 99; rules.AskMeeting(Organ, "p1", 20);
            string id = Add(holder: "p2"); rules.LoadItem(Organ, id, "p2"); rules.ChangeNegotiator(Organ, "p2");
            rules.FinishGroup(Organ); Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p2"), Is.True);
            var n = B().Meeting.Negotiations.Single(); Assert.That(n.AttemptsUsed, Is.EqualTo(1)); Assert.That(n.LastAsk, Is.EqualTo(20));
            Assert.That(rules.AskMeeting(Organ, "p2", 20), Is.False); rules.AcceptMeetingPrice(Organ, "p2");
            rules.FinishGroup(Organ); rules.BeginGroup(Organ, ProductKind.Kidney, "p2");
            Assert.That(B().Meeting.Negotiations.Single().AgreedPercent, Is.EqualTo(10));
        }
        [Test]
        public void BUY50_CurrentGroupFinishesAfterTimeoutButNextCannotStart()
        {
            Meeting(); clock.Now = B().Meeting.ExpiresAt - 1;
            rules.BeginGroup(Organ, ProductKind.Kidney, "p1"); string id = Add(); rules.LoadItem(Organ, id, "p1");
            clock.Now += 100; Assert.That(B().Meeting.Phase, Is.EqualTo(MeetingPhase.Expired));
            Assert.That(rules.ScheduleMeeting(Organ, "conflict", "p1", "base", new[] { "a" }), Is.False);
            Assert.That(rules.AcceptMeetingPrice(Organ, "p1"), Is.True);
            Assert.That(rules.ConfirmSale(Request(new[] { id })).Success, Is.True);
            Assert.That(rules.BeginGroup(Organ, ProductKind.Liver, "p1"), Is.False);
            Assert.That(rules.BeginGroup(Organ, ProductKind.Kidney, "p1"), Is.False);
            Assert.That(B().Respect, Is.EqualTo(32));
        }
    }
}
