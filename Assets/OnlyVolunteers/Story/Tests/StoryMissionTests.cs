using NUnit.Framework;
using OnlyVolunteers.Economy;
using UnityEngine;

namespace OnlyVolunteers.Story.Tests
{
    /// <summary>STORY_MISSIONS_SPEC v01: four journal states derived from persistent facts (§2.1), persistence and late join
    /// (§2.3, §17.1), M05 acquaintance unlocks (§8), M06 hand-in validation / concurrency / schedule / recovery (§9, SM-19..22).
    /// Pure state only: the scene, capture physics and co-op are checked by hand (manual guide).</summary>
    public sealed class StoryMissionTests
    {
        [OneTimeSetUp]
        public void BindG48() => EconomyPrices.Bind(OnlyVolunteers.Buyers.EconomyCatalog.Load(
            System.IO.Path.Combine(Application.dataPath, "OnlyVolunteers/Buyers/Data/Economy_v01.json")));

        private static EconomyState Reconciled()
        {
            EconomyState s = EconomyState.NewGame();
            s.ReconcileStory(teamVanInWorld: true, tutorialSaleCommitted: false);
            return s;
        }

        private static RivalHandInCheck Valid(StoryState story) => new RivalHandInCheck
        {
            ActorValid = true, TargetFound = true, PersonId = story.RivalPersonId, Alive = true, HandsTied = true, FeetTied = true, InZone = true,
        };

        private static EconomyState RoundTrip(EconomyState s) =>
            EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(s.ToSave())));

        // ---------- journal ----------

        [Test]
        public void Journal_FourStates_ComeFromFacts()
        {
            var story = new StoryState();
            Assert.That(story.StateOf(MissionId.M01), Is.EqualTo(JournalState.Active));
            Assert.That(story.StateOf(MissionId.M05), Is.EqualTo(JournalState.Locked));
            Assert.That(story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Locked));
            story.AddFact(StoryFacts.VanOwned, "test", 0);
            Assert.That(story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Offered));
            Assert.That(story.Accept(MissionId.M06), Is.True);
            Assert.That(story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Active));
            Assert.That(story.Accept(MissionId.M06), Is.False, "accepting again is a no-op");
            story.AddFact(StoryFacts.RivalDelivered, "test", 0);
            Assert.That(story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Completed));
            Assert.That(StoryMissions.All.Length, Is.EqualTo(16), "M01-M12 plus M13A-D");
        }

        [Test]
        public void Journal_EarlyFactReconcilesALaterStep_WithoutRepetition()
        {
            var story = new StoryState();
            // M04's outcome exists before M03 is formally complete (e.g. a repaired van found early): M04 shows Completed
            // as soon as its prerequisite is met, without asking for the repair again.
            story.AddFact(StoryFacts.IntroRepairComplete, "early", 0);
            Assert.That(story.StateOf(MissionId.M04), Is.EqualTo(JournalState.Completed));
            Assert.That(story.StateOf(MissionId.M03), Is.EqualTo(JournalState.Active));
        }

        [Test]
        public void PharmacyStepsAreOnHold_AndNoPharmacyAnchorIsRequired()
        {
            MissionDef m02 = StoryMissions.Get(MissionId.M02);
            Assert.That(m02.Content, Is.EqualTo(ContentStatus.OnHold));
            Assert.That(m02.Note, Does.Contain("on hold"));
            Assert.That(StoryMissions.Get(MissionId.M01).Content, Is.EqualTo(ContentStatus.FoundationOnly));
        }

        [Test]
        public void Persistence_RoundTrip_KeepsEverything_AndMessagesDoNotFlood()
        {
            EconomyState s = Reconciled();
            s.AcceptMechanicTask();
            int messages = s.Story.Messages.Count;
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.Story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Active));
            Assert.That(loaded.Story.Messages.Count, Is.EqualTo(messages));
            Assert.That(loaded.Story.FactSource(StoryFacts.VanOwned), Is.EqualTo(StoryFacts.SourceBuildProvided));
            // reconciling the loaded world again adds nothing and posts nothing
            Assert.That(loaded.ReconcileStory(true, false), Is.False);
            Assert.That(loaded.AcceptMechanicTask().Replayed, Is.True);
            Assert.That(loaded.Story.Messages.Count, Is.EqualTo(messages));
        }

        [Test]
        public void LateJoin_SnapshotCarriesCurrentJournalAndMessages()
        {
            EconomyState s = Reconciled();
            s.AcceptMechanicTask();
            EconomySnapshot snap = JsonUtility.FromJson<EconomySnapshot>(JsonUtility.ToJson(s.ToSnapshot(40, true)));
            StoryJournalEntry m06 = snap.journal.missions.Find(m => m.id == "M06");
            Assert.That(m06.State, Is.EqualTo(JournalState.Active));
            Assert.That(snap.journal.messages.Exists(m => m.id == "m06.task"), Is.True);
            Assert.That(snap.journal.rivalPersonId, Is.EqualTo(StoryState.RivalPersonIdBase));
        }

        [Test]
        public void OldSaveWithoutStoryBlock_LoadsEmpty_AndKeepsItsFlags()
        {
            EconomyState s = EconomyState.NewGame();
            s.SetWorkshopUnlocked(true); // e.g. an old DEV toggle in a test save
            EconomySaveData block = s.ToSave();
            block.story = null;
            block.timeOfDay = -1;
            EconomyState loaded = EconomyState.FromSave(JsonUtility.FromJson<EconomySaveData>(JsonUtility.ToJson(block)));
            Assert.That(loaded.WorkshopUnlocked, Is.True, "an existing save is never weakened");
            Assert.That(loaded.Story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Locked), "a debug flag is not a story completion");
            Assert.That(loaded.Story.Facts.Count, Is.EqualTo(0));
        }

        // ---------- M05 ----------

        [Test]
        public void M05_LockedBeforeReferral_ThenUnlocksPropertyAndMechanicReferralOnce()
        {
            EconomyState s = EconomyState.NewGame();
            Assert.That(s.CommitFirstOrganBuyerAcquaintance("test").Ok, Is.False);
            Assert.That(s.FirstOrganBuyerMet, Is.False);
            s.ReconcileStory(true, false);
            Assert.That(s.Story.StateOf(MissionId.M05), Is.EqualTo(JournalState.Active));
            EconomyState.StoryResult first = s.CommitFirstOrganBuyerAcquaintance("test");
            Assert.That(first.Ok && !first.Replayed, Is.True);
            Assert.That(s.FirstOrganBuyerMet, Is.True);
            Assert.That(s.Story.HasFact(StoryFacts.MechanicReferral), Is.True);
            int messages = s.Story.Messages.Count;
            Assert.That(s.CommitFirstOrganBuyerAcquaintance("again").Replayed, Is.True);
            Assert.That(s.Story.Messages.Count, Is.EqualTo(messages));
            Assert.That(s.Story.StateOf(MissionId.M05), Is.EqualTo(JournalState.Completed));
        }

        [Test]
        public void M05_DebugToggleIsNotTheAcquaintance()
        {
            EconomyState s = Reconciled();
            s.SetFirstOrganBuyerMet(true);
            Assert.That(s.Story.StateOf(MissionId.M05), Is.EqualTo(JournalState.Active));
            Assert.That(s.Story.HasFact(StoryFacts.MechanicReferral), Is.False);
        }

        [Test]
        public void M05_PropertyHasNoHiddenM06Requirement_AndM06DoesNotNeedM05()
        {
            EconomyState s = Reconciled();
            s.CommitFirstOrganBuyerAcquaintance("test");
            s.Credit(10000, "test", "", "test:money");
            Assert.That(s.TryBuyProperty(EconomyPrices.BaseRough, EconomyPrices.FindProperty(EconomyPrices.BaseRough).Price).Ok, Is.True);
            Assert.That(s.WorkshopUnlocked, Is.False);
            EconomyState other = Reconciled(); // no acquaintance at all
            Assert.That(other.AcceptMechanicTask().Ok, Is.True, "the referral is guidance, not a gate");
        }

        // ---------- M06 hand-in ----------

        [Test]
        public void M06_ValidHandIn_UnlocksWorkshopOnce_NoCashNoXp()
        {
            EconomyState s = Reconciled();
            s.AcceptMechanicTask();
            int balance = s.Fund.Balance;
            EconomyState.StoryResult r = s.CompleteRivalHandIn(Valid(s.Story));
            Assert.That(r.Ok && !r.Replayed, Is.True, r.Message);
            Assert.That(s.WorkshopUnlocked, Is.True);
            Assert.That(s.Story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Completed));
            Assert.That(s.Story.Rival.Life, Is.EqualTo(RivalLife.Resolved));
            Assert.That(s.Fund.Balance, Is.EqualTo(balance), "no cash bounty");
            Assert.That(s.Xp.Count, Is.EqualTo(0), "no XP");
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.WorkshopUnlocked && loaded.Story.StateOf(MissionId.M06) == JournalState.Completed, Is.True);
            Assert.That(loaded.CompleteRivalHandIn(Valid(loaded.Story)).Replayed, Is.True, "a reload cannot hand him in again");
        }

        [Test]
        public void M06_InvalidHandIns_AreRefused_TargetStays()
        {
            EconomyState s = Reconciled();
            Assert.That(s.CompleteRivalHandIn(Valid(s.Story)).Ok, Is.False, "not accepted yet");
            s.AcceptMechanicTask();
            void Refused(RivalHandInCheck c, HandInRefusal expected)
            {
                Assert.That(RivalRules.Validate(s.Story, c), Is.EqualTo(expected));
                Assert.That(s.CompleteRivalHandIn(c).Ok, Is.False);
            }
            RivalHandInCheck v = Valid(s.Story);
            var wrong = v; wrong.PersonId = "PATIENT-123"; Refused(wrong, HandInRefusal.WrongPerson);
            var dead = v; dead.Alive = false; Refused(dead, HandInRefusal.Dead);
            var hands = v; hands.HandsTied = false; Refused(hands, HandInRefusal.HandsFree);
            var feet = v; feet.FeetTied = false; Refused(feet, HandInRefusal.FeetFree);
            var outside = v; outside.InZone = false; Refused(outside, HandInRefusal.NotInZone);
            var van = v; van.InVan = true; Refused(van, HandInRefusal.InVan);
            var held = v; held.Held = true; Refused(held, HandInRefusal.Held);
            var actor = v; actor.ActorValid = false; Refused(actor, HandInRefusal.ActorInvalid);
            var none = new RivalHandInCheck { ActorValid = true }; Refused(none, HandInRefusal.NoTarget);
            Assert.That(s.WorkshopUnlocked, Is.False);
            Assert.That(s.Story.StateOf(MissionId.M06), Is.EqualTo(JournalState.Active));
            Assert.That(s.Story.Rival.Life, Is.EqualTo(RivalLife.AtLarge), "a refused target remains in the world");
        }

        [Test]
        public void M06_ConcurrentConfirmations_OneHandover()
        {
            EconomyState s = Reconciled();
            s.AcceptMechanicTask();
            int changes = 0;
            s.Changed += () => changes++;
            EconomyState.StoryResult a = s.CompleteRivalHandIn(Valid(s.Story));
            EconomyState.StoryResult b = s.CompleteRivalHandIn(Valid(s.Story));
            Assert.That(a.Ok && !a.Replayed, Is.True);
            Assert.That(b.Ok && b.Replayed, Is.True);
            Assert.That(changes, Is.EqualTo(1), "one commit");
            Assert.That(System.Linq.Enumerable.Count(s.Story.Messages, m => m.id == "m06.done"), Is.EqualTo(1));
        }

        [Test]
        public void M06_CaptureBeforeAcceptanceQualifiesAfterAccepting()
        {
            EconomyState s = Reconciled();
            RivalHandInCheck capturedEarly = Valid(s.Story);
            Assert.That(RivalRules.Validate(s.Story, capturedEarly), Is.EqualTo(HandInRefusal.NotAccepted));
            s.AcceptMechanicTask();
            Assert.That(s.CompleteRivalHandIn(capturedEarly).Ok, Is.True, "the same valid original qualifies; nothing has to be repeated");
        }

        [Test]
        public void M06_AcceptNeedsTheVan_NotM05()
        {
            EconomyState s = EconomyState.NewGame();
            Assert.That(s.AcceptMechanicTask().Ok, Is.False, "no van: locked");
            s.ReconcileStory(true, false);
            Assert.That(s.AcceptMechanicTask().Ok, Is.True);
        }

        // ---------- schedule and recovery ----------

        [Test]
        public void Schedule_Canopy0800To1800_AndCaptureAlwaysWins()
        {
            Assert.That(RivalRules.PlaceAt(7.99), Is.EqualTo(RivalPlace.OffShift));
            Assert.That(RivalRules.PlaceAt(8.0), Is.EqualTo(RivalPlace.Canopy));
            Assert.That(RivalRules.PlaceAt(17.99), Is.EqualTo(RivalPlace.Canopy));
            Assert.That(RivalRules.PlaceAt(18.0), Is.EqualTo(RivalPlace.OffShift));
            Assert.That(RivalRules.HourOfDay(24 * 3 + 9.5), Is.EqualTo(9.5).Within(1e-9));
            Assert.That(RivalRules.RoutineMayMove(true, false, false, true, false), Is.True);
            Assert.That(RivalRules.RoutineMayMove(false, false, true, true, false), Is.False, "captured / in the van: never teleported at a shift change");
            Assert.That(RivalRules.RoutineMayMove(true, false, true, true, false), Is.False, "tied but on his feet");
            Assert.That(RivalRules.RoutineMayMove(true, true, false, true, false), Is.False, "fleeing");
            Assert.That(RivalRules.RoutineMayMove(true, false, false, false, false), Is.False, "dead");
            Assert.That(RivalRules.RoutineMayMove(true, false, false, true, true), Is.False, "resolved");
        }

        [Test]
        public void Recovery_DeadTarget_OneReplacementNextMorningShift_NoDuplicate()
        {
            var story = new StoryState();
            string gen1 = story.RivalPersonId;
            Assert.That(story.TryAdvanceRivalGeneration(100), Is.False, "a living (or captured) original is never replaced");
            Assert.That(story.MarkRivalLost("SOMEONE_ELSE", 14, "x"), Is.False);
            Assert.That(story.MarkRivalLost(gen1, 14, "погиб"), Is.True);       // day 0, 14:00
            Assert.That(story.MarkRivalLost(gen1, 15, "again"), Is.False, "one recovery");
            Assert.That(story.Rival.replacementFrom, Is.EqualTo(30).Within(1e-9), "day 1, 06:00");
            Assert.That(story.TryAdvanceRivalGeneration(29.9), Is.False);
            Assert.That(story.TryAdvanceRivalGeneration(31.0), Is.False, "07:00: eligible but before the 08:00 shift");
            Assert.That(story.TryAdvanceRivalGeneration(32.0), Is.True);
            Assert.That(story.TryAdvanceRivalGeneration(33.0), Is.False, "exactly one new generation");
            Assert.That(story.Rival.generation, Is.EqualTo(2));
            Assert.That(story.RivalPersonId, Is.Not.EqualTo(gen1));
            story.AddFact(StoryFacts.VanOwned, "t", 0);
            story.Accept(MissionId.M06);
            var oldBody = new RivalHandInCheck { ActorValid = true, TargetFound = true, PersonId = gen1, Alive = true, HandsTied = true, FeetTied = true, InZone = true };
            Assert.That(RivalRules.Validate(story, oldBody), Is.EqualTo(HandInRefusal.WrongPerson), "an old generation never qualifies");
        }

        [Test]
        public void Recovery_SurvivesSaveLoad_AndClosedWorldTimeDoesNotAdvance()
        {
            EconomyState s = Reconciled();
            s.ObserveClock(14.0);
            Assert.That(s.ReportRivalLost(s.Story.RivalPersonId, "погиб"), Is.True);
            EconomyState loaded = RoundTrip(s);
            Assert.That(loaded.AbsoluteHours, Is.EqualTo(s.AbsoluteHours).Within(1e-9), "a closed world does not age");
            Assert.That(loaded.TickStory(), Is.False);
            Assert.That(loaded.ReportRivalLost(loaded.Story.RivalPersonId, "again"), Is.False);
            loaded.ObserveClock(23.0);
            loaded.ObserveClock(1.0); // midnight: day 1
            Assert.That(loaded.WorldDay, Is.EqualTo(1));
            loaded.ObserveClock(8.5);
            Assert.That(loaded.TickStory(), Is.True);
            Assert.That(loaded.TickStory(), Is.False);
            Assert.That(loaded.Story.Rival.generation, Is.EqualTo(2));
            Assert.That(RoundTrip(loaded).Story.Rival.generation, Is.EqualTo(2));
        }
    }
}
