using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>MECHANIC_W86 v01 in the workshop (29.10): the upgrade performance whose Poof is the purchase commit (once only,
    /// refused = no puff and no charge, leaving / disconnecting before the Poof = nothing charged and the mechanic free,
    /// save/load never pays twice), the gag schedule (20-45 active s, suppressed, no repeats) and the attention radii
    /// (2.5 m start, 3.5 m release with a delay, sight, level, the conversation participant first).</summary>
    public sealed class WorkshopMechanicV01Tests
    {
        private const string Host = "host", Guest = "guest-1";

        [SetUp]
        public void BindG48() => EconomyPrices.Bind(OnlyVolunteers.Buyers.EconomyCatalog.Load(EconomyCoreTests.G48Path));

        private static EconomyState Open(int money)
        {
            EconomyState s = EconomyState.NewGame();
            s.SetWorkshopUnlocked(true);
            if (s.VanLegacyDebugProfile) s.SwitchToProgression();
            if (money > 0) s.Credit(money, "test", "test money", "test:mechanic-fund");
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

        private static int EnginePrice => EconomyPrices.VanTierPrice(VanBranch.Engine, 1);

        /// <summary>The service's flow: validate (preview), begin, then tick until the cue; commit = the real purchase.</summary>
        private static UpgradePerformance Begin(EconomyState s, LiftSession lift, string who)
        {
            PurchaseResult preview = WorkshopUpgradePreview.VanTier(s, lift, who, VanBranch.Engine, 1, true);
            Assert.That(preview.Ok && !preview.Replayed, Is.True, "preview: " + preview.Message);
            var p = new UpgradePerformance();
            Assert.That(p.TryBegin(who, WorkshopUpgradeRows.VanBranchKind, "0", 1), Is.EqualTo(WorkshopRefusal.None));
            return p;
        }

        private static System.Func<PurchaseResult> Commit(EconomyState s, LiftSession lift, string who, List<int> calls) => () =>
        {
            calls.Add(1);
            return WorkshopRules.TryBuyVanTier(s, lift, who, VanBranch.Engine, 1, true);
        };

        // ---------- the purchase at the Poof ----------

        [Test]
        public void Perform_ChargesAndAppliesExactlyOnce_AtThePoof()
        {
            EconomyState s = Open(EnginePrice + 500);
            LiftSession lift = Raised(Host);
            int before = s.Fund.Balance;
            UpgradePerformance p = Begin(s, lift, Host);
            var calls = new List<int>();
            var commit = Commit(s, lift, Host, calls);

            Assert.That(p.Tick(0.1f, true, false, commit), Is.EqualTo(UpgradeCue.None), "still turning");
            Assert.That(p.Tick(0.1f, true, true, commit), Is.EqualTo(UpgradeCue.Begin), "faces the van: the clip starts");
            float t = 0f;
            while (t + 0.1f < UpgradePerformance.DefaultPoofSeconds - 0.01f)
            {
                Assert.That(p.Tick(0.1f, true, true, commit), Is.EqualTo(UpgradeCue.None));
                t += 0.1f;
            }
            Assert.That(s.Fund.Balance, Is.EqualTo(before), "nothing charged while he aims");
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0), "nothing applied while he aims");
            Assert.That(calls.Count, Is.Zero);

            Assert.That(p.Tick(0.2f, true, true, commit), Is.EqualTo(UpgradeCue.Poof));
            Assert.That(s.Fund.Balance, Is.EqualTo(before - EnginePrice), "charged at the Poof");
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(1), "applied at the Poof");
            // the rest of the clip, big steps, an invalid session afterwards: never a second commit
            for (int i = 0; i < 50; i++) p.Tick(0.5f, i % 2 == 0, i % 3 == 0, commit);
            Assert.That(calls.Count, Is.EqualTo(1));
            Assert.That(p.Commits, Is.EqualTo(1));
            Assert.That(p.Busy, Is.False, "the mechanic is free again");
            Assert.That(s.Fund.Balance, Is.EqualTo(before - EnginePrice));
        }

        [Test]
        public void Perform_RepeatedSelection_RefusedWhileBusy_AndTheBoughtTierOnlyReplays()
        {
            EconomyState s = Open(EnginePrice * 3);
            LiftSession lift = Raised(Host);
            UpgradePerformance p = Begin(s, lift, Host);
            Assert.That(p.TryBegin(Host, WorkshopUpgradeRows.VanBranchKind, "0", 1), Is.EqualTo(WorkshopRefusal.MechanicBusy), "a second click");
            Assert.That(p.TryBegin(Guest, WorkshopUpgradeRows.VanBranchKind, "1", 1), Is.EqualTo(WorkshopRefusal.MechanicBusy), "a second customer");
            var calls = new List<int>();
            p.Tick(0f, true, true, Commit(s, lift, Host, calls));
            p.Tick(UpgradePerformance.DefaultPoofSeconds + 0.01f, true, true, Commit(s, lift, Host, calls));
            int after = s.Fund.Balance;
            // the same row clicked again (a late callback, a stale menu): the preview sees it bought, no new performance
            PurchaseResult again = WorkshopUpgradePreview.VanTier(s, lift, Host, VanBranch.Engine, 1, true);
            Assert.That(again.Ok && again.Replayed, Is.True, again.Message);
            PurchaseResult direct = WorkshopRules.TryBuyVanTier(s, lift, Host, VanBranch.Engine, 1, true);
            Assert.That(direct.Replayed, Is.True);
            Assert.That(s.Fund.Balance, Is.EqualTo(after));
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(1));
            Assert.That(calls.Count, Is.EqualTo(1));
        }

        [Test]
        public void Perform_RefusedAtThePoof_NoPuffNoChargeNoTier()
        {
            EconomyState s = Open(EnginePrice + 10);
            LiftSession lift = Raised(Host);
            UpgradePerformance p = Begin(s, lift, Host);
            // the money is spent elsewhere while he aims
            Assert.That(s.Charge(100, "test", "other spend", "test:other").Ok, Is.True);
            int before = s.Fund.Balance;
            var calls = new List<int>();
            p.Tick(0f, true, true, Commit(s, lift, Host, calls));
            Assert.That(p.Tick(UpgradePerformance.DefaultPoofSeconds, true, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.Failed));
            Assert.That(p.Result.Ok, Is.False);
            Assert.That(p.Result.Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(s.Fund.Balance, Is.EqualTo(before));
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0));
            Assert.That(p.Busy, Is.False, "a refusal frees the mechanic at once");
            Assert.That(calls.Count, Is.EqualTo(1));
        }

        [Test]
        public void Preview_RefusesInvalidSelections_AndNeverTouchesTheState()
        {
            EconomyState s = Open(EnginePrice - 1);
            LiftSession lift = Raised(Host);
            int before = s.Fund.Balance;
            Assert.That(WorkshopUpgradePreview.VanTier(s, lift, Host, VanBranch.Engine, 1, true).Error, Is.EqualTo(PurchaseError.InsufficientFunds));
            Assert.That(WorkshopUpgradePreview.VanTier(s, lift, Guest, VanBranch.Engine, 1, true).Ok, Is.False, "not the session owner");
            Assert.That(WorkshopUpgradePreview.VanTier(s, lift, Host, VanBranch.Engine, 2, true).Error, Is.EqualTo(PurchaseError.TierChanged), "tier order");
            Assert.That(WorkshopUpgradePreview.VanTier(s, lift, Host, VanBranch.Engine, 1, false).Error, Is.EqualTo(PurchaseError.VanNotInZone));
            Assert.That(WorkshopUpgradePreview.VanTier(s, new LiftSession(), Host, VanBranch.Engine, 1, true).Ok, Is.False, "no session");
            s.Credit(10, "test", "top up", "test:top-up");
            int topped = s.Fund.Balance;
            PurchaseResult ok = WorkshopUpgradePreview.VanTier(s, lift, Host, VanBranch.Engine, 1, true);
            Assert.That(ok.Ok, Is.True, ok.Message);
            Assert.That(s.Fund.Balance, Is.EqualTo(topped), "a preview charges nothing");
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0), "a preview applies nothing");
            Assert.That(s.Fund.IsCommitted(EconomyState.VanKey(VanBranch.Engine, 1)), Is.False, "a preview books no key");
            Assert.That(before, Is.LessThan(topped));
            EconomyState locked = EconomyState.NewGame();
            if (locked.VanLegacyDebugProfile) locked.SwitchToProgression();
            locked.Credit(EnginePrice * 2, "test", "money", "test:locked");
            Assert.That(WorkshopUpgradePreview.VanTier(locked, lift, Host, VanBranch.Engine, 1, true).Error, Is.EqualTo(PurchaseError.WorkshopLocked));
        }

        [Test]
        public void Perform_OwnerLeavesBeforeThePoof_NothingCharged_MechanicFree_LiftGoesDown()
        {
            foreach (bool whileTurning in new[] { true, false })
            {
                EconomyState s = Open(EnginePrice * 2);
                LiftSession lift = Raised(Host);
                int before = s.Fund.Balance;
                UpgradePerformance p = Begin(s, lift, Host);
                var calls = new List<int>();
                if (!whileTurning)
                {
                    Assert.That(p.Tick(0f, true, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.Begin));
                    p.Tick(UpgradePerformance.DefaultPoofSeconds * 0.5f, true, true, Commit(s, lift, Host, calls));
                }
                // the server's session recovery: the owner disconnected -> the lift goes down by itself
                lift.Abort("owner disconnected");
                bool valid = lift.Active && lift.Phase == LiftPhase.Up;
                Assert.That(p.Tick(0.1f, valid, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.Cancelled));
                for (int i = 0; i < 20; i++) p.Tick(0.5f, valid, true, Commit(s, lift, Host, calls));
                Assert.That(calls.Count, Is.Zero, "no commit after the owner left");
                Assert.That(s.Fund.Balance, Is.EqualTo(before), "no charge");
                Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(0), "no free upgrade");
                Assert.That(p.Busy, Is.False, "the mechanic is not stuck busy");
                Assert.That(lift.Phase, Is.EqualTo(LiftPhase.Lowering));
                while (lift.HoldsVan) lift.Tick(0.5f, false);
                Assert.That(lift.Active, Is.False, "the session ended at the bottom");
                Assert.That(p.TryBegin(Guest, WorkshopUpgradeRows.VanBranchKind, "0", 1), Is.EqualTo(WorkshopRefusal.None), "the next customer gets him");
            }
        }

        [Test]
        public void Perform_DoneBeforeThePoofCancels_DoneAfterItKeepsThePurchase()
        {
            EconomyState s = Open(EnginePrice * 2);
            LiftSession lift = Raised(Host);
            int before = s.Fund.Balance;
            UpgradePerformance p = Begin(s, lift, Host);
            var calls = new List<int>();
            p.Tick(0f, true, true, Commit(s, lift, Host, calls));
            Assert.That(p.Cancel("done"), Is.True, "before the poof: cancelled");
            Assert.That(p.Tick(5f, true, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.None));
            Assert.That(calls.Count, Is.Zero);
            Assert.That(s.Fund.Balance, Is.EqualTo(before));

            UpgradePerformance q = Begin(s, lift, Host);
            q.Tick(0f, true, true, Commit(s, lift, Host, calls));
            Assert.That(q.Tick(UpgradePerformance.DefaultPoofSeconds, true, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.Poof));
            Assert.That(q.Cancel("done"), Is.False, "after the poof the purchase stands");
            Assert.That(s.VanTier(VanBranch.Engine), Is.EqualTo(1));
            Assert.That(s.Fund.Balance, Is.EqualTo(before - EnginePrice));
            Assert.That(calls.Count, Is.EqualTo(1));
        }

        [Test]
        public void Perform_SaveLoad_MidPerformanceHoldsNothing_AfterThePoofOnceOnly()
        {
            EconomyState s = Open(EnginePrice * 2);
            LiftSession lift = Raised(Host);
            int before = s.Fund.Balance;
            UpgradePerformance p = Begin(s, lift, Host);
            var calls = new List<int>();
            p.Tick(0f, true, true, Commit(s, lift, Host, calls));
            p.Tick(1f, true, true, Commit(s, lift, Host, calls));
            // a save while he aims: the purchase is not in it
            EconomyState mid = EconomyState.FromSave(s.ToSave());
            Assert.That(mid.Fund.Balance, Is.EqualTo(before));
            Assert.That(mid.VanTier(VanBranch.Engine), Is.EqualTo(0));
            Assert.That(p.Tick(1f, true, true, Commit(s, lift, Host, calls)), Is.EqualTo(UpgradeCue.Poof));
            // a save after the poof, loaded twice: the tier once, the charge once; buying it again only replays
            EconomyState loaded = EconomyState.FromSave(EconomyState.FromSave(s.ToSave()).ToSave());
            Assert.That(loaded.VanTier(VanBranch.Engine), Is.EqualTo(1));
            Assert.That(loaded.Fund.Balance, Is.EqualTo(before - EnginePrice));
            LiftSession again = Raised(Host);
            PurchaseResult replay = WorkshopRules.TryBuyVanTier(loaded, again, Host, VanBranch.Engine, 1, true);
            Assert.That(replay.Replayed, Is.True);
            Assert.That(loaded.Fund.Balance, Is.EqualTo(before - EnginePrice));
        }

        [Test]
        public void Perform_TurnTimeout_StartsTheAimAnyway_AndTimingMatchesTheClip()
        {
            var p = new UpgradePerformance();
            Assert.That(UpgradePerformance.DefaultPoofSeconds, Is.EqualTo(1.70f).Within(0.001f), "Mech_Upgrade_Perform_v01 Poof = frame 52 at 30 fps");
            Assert.That(p.ClipSeconds, Is.EqualTo(4.5667f).Within(0.001f));
            Assert.That(p.TryBegin(Host, "van_branch", "0", 1), Is.EqualTo(WorkshopRefusal.None));
            Assert.That(p.TryBegin("", "van_branch", "0", 1), Is.EqualTo(WorkshopRefusal.InvalidRequest));
            int serial = p.Serial;
            UpgradeCue cue = UpgradeCue.None;
            float t = 0f;
            while (cue == UpgradeCue.None && t < 10f) { cue = p.Tick(0.1f, true, false, () => null); t += 0.1f; }
            Assert.That(cue, Is.EqualTo(UpgradeCue.Begin));
            Assert.That(t, Is.EqualTo(p.MaxTurnSeconds).Within(0.11f));
            Assert.That(p.Tick(UpgradePerformance.DefaultPoofSeconds, true, true, () => null), Is.EqualTo(UpgradeCue.Failed), "a null result counts as refused");
            Assert.That(p.Serial, Is.EqualTo(serial));
        }

        // ---------- gags ----------

        [Test]
        public void Gags_Every20To45ActiveSeconds_NeverTheSameTwiceInARow()
        {
            for (int seed = 0; seed < 20; seed++)
            {
                var clock = new MechanicGagClock(seed);
                float t = 0f, last = 0f;
                int previous = -1, count = 0;
                while (t < 900f)
                {
                    t += 0.1f;
                    int gag = clock.Tick(0.1f, true, false);
                    if (gag < 0) continue;
                    float gap = t - last;
                    Assert.That(gap, Is.InRange(19.9f, 45.2f), $"seed {seed}: gap {gap:0.0} s");
                    Assert.That(gag, Is.InRange(0, 1));
                    Assert.That(gag, Is.Not.EqualTo(previous), "no repeat");
                    previous = gag;
                    last = t;
                    count++;
                }
                Assert.That(count, Is.InRange(900 / 45, 900 / 20), "seed " + seed);
            }
        }

        [Test]
        public void Gags_SuppressedInDialogueServiceOrAttention_WaitForAvailability_QuietAfterwards()
        {
            var clock = new MechanicGagClock(7, 2, 20f, 20f, 4f);
            // dialogue / hand-in / service: the clock does not run at all
            for (int i = 0; i < 1000; i++) Assert.That(clock.Tick(0.1f, true, true), Is.EqualTo(-1));
            Assert.That(clock.UntilNext, Is.EqualTo(20f).Within(0.001f));
            // walking / in a work clip: active time counts, but a due gag waits
            for (int i = 0; i < 260; i++) Assert.That(clock.Tick(0.1f, false, false), Is.EqualTo(-1));
            Assert.That(clock.UntilNext, Is.LessThanOrEqualTo(0f));
            // suppressed again just as he becomes available: the quiet time comes first
            clock.Tick(0.1f, true, true);
            float quiet = 0f;
            int gag = -1;
            while (gag < 0 && quiet < 10f) { gag = clock.Tick(0.1f, true, false); quiet += 0.1f; }
            Assert.That(gag, Is.GreaterThanOrEqualTo(0));
            Assert.That(quiet, Is.EqualTo(4f).Within(0.21f), "4 s quiet after a suppression");
        }

        // ---------- attention ----------

        private static AttentionCandidate At(string id, float d, bool visible = true, bool talking = false, float dy = 0f) =>
            new AttentionCandidate { Id = id, Dx = d * 0.6f, Dz = d * 0.8f, Dy = dy, Visible = visible, Talking = talking };

        [Test]
        public void Attention_StartsAt2p5_HoldsTo3p5_ReleasesAfterTheDelay()
        {
            var a = new MechanicAttention();
            Assert.That(a.Tick(0.1f, new[] { At("p", 2.6f) }), Is.Empty, "2.6 m: not yet");
            Assert.That(a.Tick(0.1f, new[] { At("p", 2.45f) }), Is.EqualTo("p"), "2.45 m: attends");
            // hysteresis: walking back and forth between 2.5 and 3.5 m keeps him attending (no stop/start jitter)
            for (int i = 0; i < 40; i++) Assert.That(a.Tick(0.1f, new[] { At("p", i % 2 == 0 ? 3.0f : 3.45f) }), Is.EqualTo("p"));
            // beyond 3.5 m: kept for the release delay, then released
            Assert.That(a.Tick(0.3f, new[] { At("p", 3.6f) }), Is.EqualTo("p"));
            Assert.That(a.Tick(0.2f, new[] { At("p", 3.6f) }), Is.EqualTo("p"));
            Assert.That(a.Tick(0.2f, new[] { At("p", 3.6f) }), Is.Empty, "released after 0.6 s");
            // a brief step out and back in does not release
            a.Tick(0.1f, new[] { At("p", 2f) });
            a.Tick(0.4f, new[] { At("p", 3.8f) });
            Assert.That(a.Tick(0.1f, new[] { At("p", 3.2f) }), Is.EqualTo("p"));
            Assert.That(a.Lost, Is.Zero);
            Assert.That(MechanicAttention.DefaultStart, Is.EqualTo(2.5f));
            Assert.That(MechanicAttention.DefaultRelease, Is.EqualTo(3.5f));
        }

        [Test]
        public void Attention_NotThroughWallsOrFloors_TalkerFirst_StableBetweenTwo()
        {
            var a = new MechanicAttention();
            Assert.That(a.Tick(0.1f, new[] { At("p", 1.5f, visible: false) }), Is.Empty, "behind a wall / outside the workshop");
            Assert.That(a.Tick(0.1f, new[] { At("p", 1.5f, dy: 1.6f) }), Is.Empty, "another level (pit, roof)");
            // two customers: the first one stays even when the second comes nearer
            Assert.That(a.Tick(0.1f, new[] { At("a", 2.2f) }), Is.EqualTo("a"));
            Assert.That(a.Tick(0.1f, new[] { At("a", 2.2f), At("b", 1.0f) }), Is.EqualTo("a"), "stable");
            // the one who opens the conversation wins
            Assert.That(a.Tick(0.1f, new[] { At("a", 2.2f), At("b", 1.0f, talking: true) }), Is.EqualTo("b"));
            // and keeps him even a bit beyond 3.5 m (the menu is open), and without a clear sight line
            Assert.That(a.Tick(0.1f, new[] { At("a", 1.0f), At("b", 4.2f, visible: false, talking: true) }), Is.EqualTo("b"));
            // the menu closed and b walked off: back to the nearest (a) after the release delay
            a.Tick(0.4f, new[] { At("a", 1.0f), At("b", 5f) });
            Assert.That(a.Tick(0.4f, new[] { At("a", 1.0f), At("b", 5f) }), Is.EqualTo("a"));
            // equal distances: the smaller id, every time (stable selection)
            var c = new MechanicAttention();
            Assert.That(c.Tick(0.1f, new[] { At("zed", 2f), At("amy", 2f) }), Is.EqualTo("amy"));
        }
    }
}
