using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>Workshop_W86 (Fedya 29.10): the mechanic's conversation lines per state, the ONE lift session (start
    /// checks, timing, nobody pushed, owner-only, cancel / disconnect lowers it) and the purchase gating on the lift (session,
    /// unlock, zone, tier order, funds, once per world).</summary>
    public sealed class WorkshopRulesV01Tests
    {
        [SetUp]
        public void BindG48() => EconomyPrices.Bind(OnlyVolunteers.Buyers.EconomyCatalog.Load(EconomyCoreTests.G48Path));

        private static EconomyState Open(int money)
        {
            EconomyState s = EconomyState.NewGame();
            s.SetWorkshopUnlocked(true);
            if (money > 0) s.Credit(money, "test", "test money", "test:workshop-fund");
            return s;
        }

        private static LiftSession Raised(string owner)
        {
            var l = new LiftSession();
            Assert.That(l.TryStart(owner, LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.None));
            l.Tick(l.SwingSeconds + l.Seconds + 0.1f, false);
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Up));
            return l;
        }

        // ---------- the conversation ----------

        [Test]
        public void Menu_AlwaysChatAndBye_StoryLineByM06State_UpgradeOnlyWhenOpen()
        {
            Assert.That(MechanicDialogue.Options(JournalState.Locked, false), Is.EqualTo(new[] { MechanicOption.Chat, MechanicOption.Bye }));
            Assert.That(MechanicDialogue.Options(JournalState.Offered, false), Is.EqualTo(new[] { MechanicOption.Chat, MechanicOption.AcceptRival, MechanicOption.Bye }));
            Assert.That(MechanicDialogue.Options(JournalState.Active, false), Is.EqualTo(new[] { MechanicOption.Chat, MechanicOption.HandInRival, MechanicOption.Bye }));
            Assert.That(MechanicDialogue.Options(JournalState.Completed, true), Is.EqualTo(new[] { MechanicOption.Chat, MechanicOption.UpgradeVan, MechanicOption.Bye }));
            // the DEV unlock toggle opens the workshop without the story: the M06 line stays as it is
            Assert.That(MechanicDialogue.Options(JournalState.Offered, true), Is.EqualTo(new[] { MechanicOption.Chat, MechanicOption.AcceptRival, MechanicOption.UpgradeVan, MechanicOption.Bye }));
            // a completed M06 without the unlock (not reachable in the story) offers no upgrade
            Assert.That(MechanicDialogue.Options(JournalState.Completed, false), Has.No.Member(MechanicOption.UpgradeVan));
        }

        [Test]
        public void Menu_ChatLine_ExistsForEveryState_AndVaries()
        {
            foreach (JournalState m in new[] { JournalState.Locked, JournalState.Offered, JournalState.Active, JournalState.Completed })
                foreach (bool open in new[] { false, true })
                {
                    string a = MechanicDialogue.ChatLine(m, open, 0), b = MechanicDialogue.ChatLine(m, open, 1);
                    Assert.That(a, Is.Not.Empty, m + " / " + open);
                    Assert.That(a, Is.Not.EqualTo(b), "two variants per state");
                    Assert.That(MechanicDialogue.ChatLine(m, open, -3), Is.Not.Empty, "any turn number is safe");
                }
            Assert.That(MechanicDialogue.Title(MechanicOption.UpgradeVan), Is.EqualTo("Улучшить бусик"));
            Assert.That(MechanicDialogue.Title(MechanicOption.Bye), Is.EqualTo("Пока"));
        }

        // ---------- the lift session ----------

        [Test]
        public void Start_ChecksEachConditionInOrder_AndBooksNothingWhenRefused()
        {
            var cases = new (System.Func<LiftStartCheck, LiftStartCheck> make, WorkshopRefusal want)[]
            {
                (c => { c.Ready = false; return c; }, WorkshopRefusal.NotReady),
                (c => { c.WorkshopUnlocked = false; return c; }, WorkshopRefusal.WorkshopLocked),
                (c => { c.ActorNear = false; return c; }, WorkshopRefusal.TooFar),
                (c => { c.VanFound = false; return c; }, WorkshopRefusal.NoVan),
                (c => { c.VanInZone = false; return c; }, WorkshopRefusal.VanNotInZone),
                (c => { c.VanAligned = false; return c; }, WorkshopRefusal.VanNotAligned),
                (c => { c.SomeoneDriving = true; return c; }, WorkshopRefusal.VanDriven),
                (c => { c.VanStopped = false; return c; }, WorkshopRefusal.VanMoving),
                (c => { c.BodyInWay = true; return c; }, WorkshopRefusal.BodyInWay),
            };
            foreach (var (make, want) in cases)
            {
                var l = new LiftSession();
                Assert.That(l.TryStart("host", make(LiftStartCheck.Good)), Is.EqualTo(want));
                Assert.That(l.Active, Is.False, want + ": no session");
                Assert.That(l.HoldsVan, Is.False, want + ": the van is not taken");
                Assert.That(WorkshopRules.Explain(want), Is.Not.Empty);
            }
            Assert.That(new LiftSession().TryStart("", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.InvalidRequest));
        }

        [Test]
        public void Lift_ArmsSwingInFirst_ThenRisesTravelInSeconds_PausesWhileBlocked_NeverOvershoots()
        {
            var l = new LiftSession();
            Assert.That(l.Travel, Is.EqualTo(1.6f));
            Assert.That(l.Seconds, Is.EqualTo(4f));
            Assert.That(l.TryStart("host", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.None));
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Raising));
            Assert.That(l.HoldsVan, Is.True);
            l.Tick(l.SwingSeconds * 0.5f, false);
            Assert.That(l.Swing, Is.EqualTo(0.5f).Within(1e-4f));
            Assert.That(l.Height, Is.EqualTo(0f), "the arms swing in under the sills before anything rises");
            l.Tick(l.SwingSeconds * 0.5f + l.Seconds * 0.5f, false);
            Assert.That(l.Swing, Is.EqualTo(1f));
            Assert.That(l.Height, Is.EqualTo(l.Travel * 0.5f).Within(1e-3f));
            Assert.That(l.Tick(10f, true), Is.False, "blocked: nobody is pushed, nothing moves");
            Assert.That(l.Height, Is.EqualTo(l.Travel * 0.5f).Within(1e-3f));
            Assert.That(l.Tick(10f, false), Is.True);
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Up));
            Assert.That(l.Height, Is.EqualTo(1.6f));
        }

        [Test]
        public void Lift_TravelAndTimingAreData_BadValuesFallBack()
        {
            var big = new LiftSession(2.2f, 6f, 0f);
            big.TryStart("host", LiftStartCheck.Good);
            big.Tick(3f, false);
            Assert.That(big.Height, Is.EqualTo(1.1f).Within(1e-4f), "2.2 m in 6 s, no arm swing");
            var bad = new LiftSession(-1f, 0f, -2f);
            Assert.That(bad.Travel, Is.EqualTo(LiftSession.DefaultTravel));
            Assert.That(bad.Seconds, Is.EqualTo(LiftSession.DefaultSeconds));
            Assert.That(bad.SwingSeconds, Is.EqualTo(LiftSession.DefaultSwingSeconds));
        }

        [Test]
        public void OneSessionAtATime_OthersRefused_OwnerMayReopen()
        {
            LiftSession l = Raised("host");
            Assert.That(l.TryStart("guid-b", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.Busy));
            Assert.That(l.TryStart("host", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.None), "the owner comes back to the screen");
            Assert.That(l.Owner, Is.EqualTo("host"));
            Assert.That(l.Finish("guid-b"), Is.EqualTo(WorkshopRefusal.NotOwner));
            Assert.That(l.CanBuy("guid-b"), Is.EqualTo(WorkshopRefusal.NotOwner));
            Assert.That(l.CanBuy("host"), Is.EqualTo(WorkshopRefusal.None));
        }

        [Test]
        public void Done_LowersAndEndsAtTheBottom_ThenANewSessionMayStart()
        {
            LiftSession l = Raised("host");
            Assert.That(l.Finish("host"), Is.EqualTo(WorkshopRefusal.None));
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Lowering));
            Assert.That(l.CanBuy("host"), Is.EqualTo(WorkshopRefusal.NotRaised), "no purchases on the way down");
            Assert.That(l.TryStart("guid-b", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.Busy), "still lowering");
            l.Tick(1f, true);
            Assert.That(l.HoldsVan, Is.True, "blocked under the van: it waits");
            l.Tick(l.Seconds, false);
            Assert.That(l.Height, Is.EqualTo(0f));
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Lowering), "down, the arms still under the sills");
            Assert.That(l.HoldsVan, Is.True, "the van stays held until the arms are out of the wheel path");
            l.Tick(l.SwingSeconds, false);
            Assert.That(l.Swing, Is.EqualTo(0f));
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Down));
            Assert.That(l.Height, Is.EqualTo(0f));
            Assert.That(l.Active, Is.False);
            Assert.That(l.HoldsVan, Is.False, "the van gets its physics back");
            Assert.That(l.Finish("host"), Is.EqualTo(WorkshopRefusal.NoSession));
            Assert.That(l.TryStart("guid-b", LiftStartCheck.Good), Is.EqualTo(WorkshopRefusal.None));
        }

        [Test]
        public void OwnerLeavesMidRise_LiftGoesDownFromWhereItIs_VanNeverLeftUp()
        {
            var l = new LiftSession();
            l.TryStart("guid-a", LiftStartCheck.Good);
            l.Tick(l.SwingSeconds + 1f, false);
            float h = l.Height;
            Assert.That(h, Is.GreaterThan(0f).And.LessThan(l.Travel));
            l.Abort("owner disconnected");
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Lowering));
            Assert.That(l.LastEnd, Is.EqualTo("owner disconnected"));
            Assert.That(l.CanBuy("guid-a"), Is.EqualTo(WorkshopRefusal.NotRaised));
            for (int i = 0; i < 100 && l.HoldsVan; i++) l.Tick(0.1f, false);
            Assert.That(l.HoldsVan, Is.False);
            Assert.That(l.Active, Is.False);
            l.Abort("again");
            Assert.That(l.Phase, Is.EqualTo(LiftPhase.Down), "aborting an idle lift does nothing");
        }

        [Test]
        public void ClientMirror_SetClampsHeight()
        {
            var l = new LiftSession();
            l.Set(LiftPhase.Up, 9f, 3f, "host");
            Assert.That(l.Height, Is.EqualTo(l.Travel));
            Assert.That(l.Swing, Is.EqualTo(1f));
            Assert.That(l.Active && l.HoldsVan, Is.True);
            l.Set(LiftPhase.Down, -1f, -1f, null);
            Assert.That(l.Height, Is.EqualTo(0f));
            Assert.That(l.Active, Is.False);
        }

        // ---------- purchases on the lift ----------

        [Test]
        public void Buy_OnlyWhileUp_ByTheOwner_ThroughTheVanTierRules_OncePerWorld()
        {
            EconomyState s = Open(100000);
            var l = new LiftSession();
            int price1 = EconomyPrices.VanTierPrice(VanBranch.Engine, 1);
            Assert.That(price1, Is.GreaterThan(0));
            PurchaseResult r = WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Engine, 1, true);
            Assert.That(r.Ok, Is.False, "no session");
            Assert.That(s.Fund.Balance, Is.EqualTo(100000));
            l.TryStart("host", LiftStartCheck.Good);
            Assert.That(WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Engine, 1, true).Ok, Is.False, "still raising");
            l.Tick(l.SwingSeconds + l.Seconds, false);
            Assert.That(WorkshopRules.TryBuyVanTier(s, l, "guid-b", VanBranch.Engine, 1, true).Ok, Is.False, "not the owner");
            Assert.That(s.Fund.Balance, Is.EqualTo(100000), "refusals book nothing");

            r = WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Engine, 1, true);
            Assert.That(r.Ok, Is.True, r.Message);
            Assert.That(r.Replayed, Is.False);
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(1));
            Assert.That(s.Fund.Balance, Is.EqualTo(100000 - price1));
            // the same request again (a double click, a resend after a lag): answered, not charged twice
            PurchaseResult again = WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Engine, 1, true);
            Assert.That(again.Ok && again.Replayed, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(100000 - price1));
            Assert.That(s.Fund.IsCommitted(EconomyState.VanKey(VanBranch.Engine, 1)), Is.True);
        }

        [Test]
        public void Buy_Gating_Unlocked_Zone_TierOrder_Funds()
        {
            LiftSession l = Raised("host");
            EconomyState locked = EconomyState.NewGame();
            locked.Credit(100000, "test", "", "t");
            Assert.That(WorkshopRules.TryBuyVanTier(locked, l, "host", VanBranch.Brakes, 1, true).Error, Is.EqualTo(PurchaseError.WorkshopLocked));

            EconomyState s = Open(100000);
            Assert.That(WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Brakes, 1, false).Error, Is.EqualTo(PurchaseError.VanNotInZone));
            Assert.That(WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Brakes, 2, true).Error, Is.EqualTo(PurchaseError.TierChanged), "no skipping a tier");
            Assert.That(s.Fund.Balance, Is.EqualTo(100000));

            EconomyState poor = Open(1);
            PurchaseResult r = WorkshopRules.TryBuyVanTier(poor, l, "host", VanBranch.Brakes, 1, true);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(poor.Fund.Balance, Is.EqualTo(1));
            Assert.That(poor.VanTier(VanBranch.Brakes), Is.EqualTo(0));

            for (int t = 1; t <= EconomyPrices.VanMaxTier; t++)
                Assert.That(WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Brakes, t, true).Ok, Is.True, "tier " + t);
            Assert.That(WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Brakes, 4, true).Error, Is.EqualTo(PurchaseError.AlreadyMax));
            Assert.That(s.Fund.Balance, Is.EqualTo(100000 - EconomyPrices.VanBranchTotal(VanBranch.Brakes)));
        }

        [Test]
        public void Buy_LegacyStartAtMaxSlot_IsRefused_NothingCharged()
        {
            EconomyState s = FundMigration.LoadOrMigrate(null, true, 50000);
            s.SetWorkshopUnlocked(true);
            LiftSession l = Raised("host");
            PurchaseResult r = WorkshopRules.TryBuyVanTier(s, l, "host", VanBranch.Handling, 1, true);
            Assert.That(r.Error, Is.EqualTo(PurchaseError.LegacyDebugProfile));
            Assert.That(s.Fund.Balance, Is.EqualTo(50000));
        }

        // ---------- the upgrade screen's rows ----------

        [Test]
        public void Rows_VanBranchesWithCataloguePrices_AndMoreGroupsPlugIn()
        {
            EconomyState s = Open(100000);
            WorkshopRules.TryBuyVanTier(s, Raised("host"), "host", VanBranch.Handling, 1, true);
            List<WorkshopUpgradeRow> all = WorkshopUpgradeRows.Build(s.ToSnapshot(5, true));
            // the van branches first; the cargo body rows (Fedya 29.10) follow them (VanCargoUpgradesV01Tests)
            List<WorkshopUpgradeRow> rows = all.Where(r => r.Kind == WorkshopUpgradeRows.VanBranchKind).ToList();
            Assert.That(all.Take(3), Is.EqualTo(rows));
            Assert.That(rows.Select(r => r.Branch), Is.EqualTo(new[] { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes }));
            foreach (WorkshopUpgradeRow r in rows)
            {
                Assert.That(r.Kind, Is.EqualTo(WorkshopUpgradeRows.VanBranchKind));
                Assert.That(r.MaxTier, Is.EqualTo(3));
                Assert.That(r.NextPrice, Is.EqualTo(EconomyPrices.VanTierPrice(r.Branch, r.Tier + 1)), r.Title + ": price from the catalogue");
                Assert.That(r.Blocked, Is.Empty);
            }
            Assert.That(rows[1].Tier, Is.EqualTo(1));
            Assert.That(rows[1].Expected, Is.EqualTo(2));

            // a later upgrade group (storage, capacity, containment ...) is one more provider: the screen code stays as it is
            Assert.That(WorkshopUpgradeRows.Providers.Count, Is.EqualTo(2), "van branches + cargo body");
            WorkshopUpgradeRows.Providers.Add(snap => new[] { new WorkshopUpgradeRow { Kind = "test_group", Arg = "x", Group = "Test", Title = "Test row", MaxTier = 2, NextPrice = 7 } });
            try
            {
                List<WorkshopUpgradeRow> more = WorkshopUpgradeRows.Build(s.ToSnapshot(5, true));
                Assert.That(more.Count, Is.EqualTo(all.Count + 1));
                Assert.That(more[more.Count - 1].Kind, Is.EqualTo("test_group"));
            }
            finally { WorkshopUpgradeRows.Providers.RemoveAt(WorkshopUpgradeRows.Providers.Count - 1); }

            EconomyState legacy = FundMigration.LoadOrMigrate(null, true, 0);
            legacy.SetWorkshopUnlocked(true);
            Assert.That(WorkshopUpgradeRows.Build(legacy.ToSnapshot(5, true)).All(r => r.Blocked.Length > 0), Is.True, "legacy slot: every row explains why not");
            EconomyState shut = EconomyState.NewGame();
            Assert.That(WorkshopUpgradeRows.Build(shut.ToSnapshot(5, true)).All(r => r.Blocked.Length > 0), Is.True, "locked workshop: no buyable row");
        }
    }
}
