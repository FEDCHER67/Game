using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Economy
{
    /// <summary>Where an upgrade performance of the mechanic is (Workshop_W86, MECHANIC_W86 v01).</summary>
    public enum UpgradeStage : byte
    {
        None = 0,
        /// <summary>Accepted (validated, nothing charged): the mechanic turns to the van.</summary>
        Turning = 1,
        /// <summary>Mech_Upgrade_Perform plays: "watch this", the wrench up as a sight, ~1 s of aiming. Nothing charged yet.</summary>
        Aiming = 2,
        /// <summary>After the Poof: the purchase was committed (or refused); the clip plays out (lower, blow, pleased).</summary>
        After = 3,
    }

    /// <summary>What one tick of the performance produced (the server turns it into presentation and replies).</summary>
    public enum UpgradeCue : byte
    {
        None = 0,
        /// <summary>He faces the van: the upgrade clip starts now.</summary>
        Begin = 1,
        /// <summary>The Poof: the purchase was committed now (fund charged once, tier applied): show the puff on the van.</summary>
        Poof = 2,
        /// <summary>The Poof moment came but the commit was refused (funds, tier changed, lift down...): no puff, no charge.</summary>
        Failed = 3,
        /// <summary>Ended before the Poof (owner left / disconnected / "Done", lift lowered): nothing charged, nothing applied.</summary>
        Cancelled = 4,
        /// <summary>The clip played out after a committed purchase: the mechanic is free again.</summary>
        Finished = 5,
    }

    /// <summary>
    /// The mechanic's upgrade performance (pure, server side): ONE selected upgrade at a time is turned into a short comic
    /// action whose Poof moment is the purchase commit. Timeline: TryBegin (validated by the caller, nothing charged) ->
    /// Turning (until he faces the van, at most <see cref="MaxTurnSeconds"/>) -> Aiming (the clip from its first frame;
    /// <see cref="PoofSeconds"/> = the clip's Poof event, 1.70 s) -> the commit callback runs EXACTLY ONCE at the Poof
    /// (Poof = paid and applied, Failed = refused, no puff) -> After (the rest of the clip) -> free. Leaving before the Poof
    /// (owner gone, session no longer valid) cancels with nothing charged. Animation events never reach this class: only
    /// the server's own clock does, so repeated clicks, client callbacks, late joins and save/load cannot pay twice (the
    /// economy's deterministic purchase key is the second guard).
    /// </summary>
    public sealed class UpgradePerformance
    {
        /// <summary>Mech_Upgrade_Perform_v01: event Poof at frame 52 of 1..138 at 30 fps = 1.70 s after the clip starts.</summary>
        public const float DefaultPoofSeconds = 1.70f;
        /// <summary>Mech_Upgrade_Perform_v01 length (frames 1..138 at 30 fps).</summary>
        public const float DefaultClipSeconds = 4.5667f;
        /// <summary>Longest turn toward the van before the aim starts anyway (he is usually there already).</summary>
        public const float DefaultMaxTurnSeconds = 2.5f;

        public float PoofSeconds { get; }
        public float ClipSeconds { get; }
        public float MaxTurnSeconds { get; }

        public UpgradePerformance(float poofSeconds = DefaultPoofSeconds, float clipSeconds = DefaultClipSeconds, float maxTurnSeconds = DefaultMaxTurnSeconds)
        {
            PoofSeconds = poofSeconds > 0f ? poofSeconds : DefaultPoofSeconds;
            ClipSeconds = clipSeconds > PoofSeconds ? clipSeconds : Math.Max(DefaultClipSeconds, PoofSeconds + 0.5f);
            MaxTurnSeconds = maxTurnSeconds >= 0f ? maxTurnSeconds : DefaultMaxTurnSeconds;
        }

        public UpgradeStage Stage { get; private set; } = UpgradeStage.None;
        public bool Busy => Stage != UpgradeStage.None;
        /// <summary>Before the Poof (turning or aiming): nothing has been charged yet.</summary>
        public bool Pending => Stage == UpgradeStage.Turning || Stage == UpgradeStage.Aiming;
        public string Owner { get; private set; } = "";
        public string Kind { get; private set; } = "";
        public string Arg { get; private set; } = "";
        public int Expected { get; private set; }
        /// <summary>Seconds since the clip started (Aiming / After), 0 while turning.</summary>
        public float Age { get; private set; }
        /// <summary>Increments with every accepted performance (the presentation's action identity).</summary>
        public int Serial { get; private set; }
        /// <summary>The commit's result of the current / last performance (null before its Poof).</summary>
        public PurchaseResult Result { get; private set; }
        /// <summary>How many times the commit callback ran (all performances): one per performance that reached its Poof.</summary>
        public int Commits { get; private set; }
        /// <summary>Why the last performance ended ("" while one runs).</summary>
        public string LastEnd { get; private set; } = "";

        private float turnAge;

        /// <summary>Accepts a validated selection (the caller's preview passed; nothing is charged here). Refused while a
        /// performance runs: a second click / a second customer never starts a second one.</summary>
        public WorkshopRefusal TryBegin(string owner, string kind, string arg, int expected)
        {
            if (string.IsNullOrEmpty(owner) || owner.Length > 64 || string.IsNullOrEmpty(kind)) return WorkshopRefusal.InvalidRequest;
            if (Busy) return WorkshopRefusal.MechanicBusy;
            Owner = owner;
            Kind = kind;
            Arg = arg ?? "";
            Expected = expected;
            Stage = UpgradeStage.Turning;
            Age = 0f;
            turnAge = 0f;
            Result = null;
            LastEnd = "";
            Serial++;
            return WorkshopRefusal.None;
        }

        /// <summary>Advances the performance. valid: the owner is present and his lift session still holds the raised van;
        /// facingVan: the mechanic stands at his service point facing it. commit runs once at the Poof and returns the
        /// economy's result (null counts as refused).</summary>
        public UpgradeCue Tick(float dt, bool valid, bool facingVan, Func<PurchaseResult> commit)
        {
            if (!Busy || float.IsNaN(dt) || dt < 0f) return UpgradeCue.None;
            switch (Stage)
            {
                case UpgradeStage.Turning:
                    if (!valid) { End("cancelled while turning"); return UpgradeCue.Cancelled; }
                    turnAge += dt;
                    if (!facingVan && turnAge < MaxTurnSeconds) return UpgradeCue.None;
                    Stage = UpgradeStage.Aiming;
                    Age = 0f;
                    return UpgradeCue.Begin;
                case UpgradeStage.Aiming:
                    if (!valid) { End("cancelled before the poof"); return UpgradeCue.Cancelled; }
                    Age += dt;
                    if (Age < PoofSeconds) return UpgradeCue.None;
                    // the Poof: the stage moves on BEFORE the commit runs, so nothing can run it a second time
                    Stage = UpgradeStage.After;
                    Commits++;
                    PurchaseResult r = commit != null ? commit() : null;
                    Result = r ?? new PurchaseResult { Ok = false, Error = PurchaseError.InvalidRequest, Message = "Покупка не прошла" };
                    if (Result.Ok && !Result.Replayed) return UpgradeCue.Poof;
                    End("refused at the poof: " + Result.Error);
                    return UpgradeCue.Failed;
                case UpgradeStage.After:
                    Age += dt;
                    if (Age < ClipSeconds) return UpgradeCue.None;
                    End("done");
                    return UpgradeCue.Finished;
                default:
                    return UpgradeCue.None;
            }
        }

        /// <summary>Stops a performance from outside ("Done", server stop). Before the Poof: true = cancelled, nothing charged.
        /// After the Poof the purchase stands; the presentation just ends.</summary>
        public bool Cancel(string why)
        {
            if (!Busy) return false;
            bool pending = Pending;
            End(why ?? "cancelled");
            return pending;
        }

        private void End(string why)
        {
            Stage = UpgradeStage.None;
            LastEnd = why ?? "";
            turnAge = 0f;
        }
    }

    /// <summary>Workshop purchase checks without committing anything (the selection's validation before the performance).</summary>
    public static class WorkshopUpgradePreview
    {
        /// <summary>The very rules of <see cref="WorkshopRules.TryBuyVanTier"/> run on a throw-away copy of the state (save
        /// round trip): Ok = the purchase would go through right now. The real state is never touched.</summary>
        public static PurchaseResult VanTier(EconomyState state, LiftSession session, string requester, VanBranch branch, int expectedNextTier, bool vanInZone)
        {
            if (state == null || session == null) return WorkshopRules.Refused(WorkshopRefusal.InvalidRequest, state);
            EconomyState copy = EconomyState.FromSave(state.ToSave());
            return WorkshopRules.TryBuyVanTier(copy, session, requester, branch, expectedNextTier, vanInZone);
        }

        /// <summary>The cargo-body purchase (<see cref="WorkshopRules.TryBuyVanCargo"/>) on a throw-away copy of the state.</summary>
        public static PurchaseResult CargoUpgrade(EconomyState state, LiftSession session, string requester, string cargoId, int expectedPrice, bool vanInZone)
        {
            if (state == null || session == null) return WorkshopRules.Refused(WorkshopRefusal.InvalidRequest, state);
            EconomyState copy = EconomyState.FromSave(state.ToSave());
            return WorkshopRules.TryBuyVanCargo(copy, session, requester, cargoId, expectedPrice, vanInZone);
        }
    }

    /// <summary>
    /// When the mechanic does his optional wrench gags (Mech_Gag_WrenchGun / Mech_Gag_CockNod): every
    /// <see cref="MinInterval"/>..<see cref="MaxInterval"/> ACTIVE seconds (the clock only runs while he is not suppressed:
    /// no dialogue, hand-in, service session, upgrade or attention), and only fires when he is available (idle at a stop or
    /// at home, not walking or in a work clip; a due gag waits for that). After a suppression a short quiet time passes
    /// first. The same gag never plays twice in a row.
    /// </summary>
    public sealed class MechanicGagClock
    {
        public const float DefaultMinInterval = 20f, DefaultMaxInterval = 45f, DefaultQuietAfterBusy = 4f;

        public float MinInterval { get; }
        public float MaxInterval { get; }
        public float QuietAfterBusy { get; }
        public int GagCount { get; }
        /// <summary>Active seconds left until the next gag is due (&lt;= 0: due, waiting for availability).</summary>
        public float UntilNext { get; private set; }
        public float Quiet { get; private set; }
        public int Last { get; private set; } = -1;
        public int Fired { get; private set; }

        private readonly Random random;

        public MechanicGagClock(int seed, int gagCount = 2, float minInterval = DefaultMinInterval, float maxInterval = DefaultMaxInterval, float quietAfterBusy = DefaultQuietAfterBusy)
        {
            random = new Random(seed);
            GagCount = Math.Max(1, gagCount);
            MinInterval = Math.Max(1f, minInterval);
            MaxInterval = Math.Max(MinInterval, maxInterval);
            QuietAfterBusy = Math.Max(0f, quietAfterBusy);
            UntilNext = NextInterval();
        }

        private float NextInterval() => MinInterval + (float)random.NextDouble() * (MaxInterval - MinInterval);

        /// <summary>One step: returns the gag to play now (0..GagCount-1) or -1.</summary>
        public int Tick(float dt, bool available, bool suppressed)
        {
            if (float.IsNaN(dt) || dt <= 0f) return -1;
            if (suppressed) { Quiet = QuietAfterBusy; return -1; }
            if (Quiet > 0f) { Quiet = Math.Max(0f, Quiet - dt); return -1; }
            UntilNext -= dt;
            if (UntilNext > 0f || !available) return -1;
            int gag = GagCount == 1 ? 0 : Last < 0 ? random.Next(GagCount) : random.Next(GagCount - 1);
            if (GagCount > 1 && Last >= 0 && gag >= Last) gag++; // never the same one twice in a row
            Last = gag;
            Fired++;
            UntilNext = NextInterval();
            return gag;
        }
    }

    /// <summary>One player the mechanic may attend to (server measurement, flat offsets from the mechanic).</summary>
    public struct AttentionCandidate
    {
        public string Id;
        /// <summary>Horizontal offset from the mechanic (metres).</summary>
        public float Dx, Dz;
        /// <summary>Height difference (feet to feet): another floor / the pit / a roof is not "the same level".</summary>
        public float Dy;
        /// <summary>Inside the workshop and a clear sight line (no wall, floor or van between them).</summary>
        public bool Visible;
        /// <summary>This player has the mechanic's conversation open.</summary>
        public bool Talking;

        public float Distance => (float)Math.Sqrt(Dx * Dx + Dz * Dz);
    }

    /// <summary>
    /// Who the mechanic attends to (pure): a player within <see cref="StartRadius"/> (2.5 m, horizontal, same level, clear
    /// sight) catches his attention; he keeps it until that player is beyond <see cref="ReleaseRadius"/> (3.5 m) or out of
    /// sight for <see cref="ReleaseDelay"/> seconds (no stop/start jitter at the edge). The conversation participant always
    /// wins (within the release radius plus <see cref="TalkSlack"/>, sight not required: the menu is open); otherwise the
    /// current target stays (stable), else the nearest eligible one (ties: the smaller id). Proximity never opens a menu.
    /// </summary>
    public sealed class MechanicAttention
    {
        public const float DefaultStart = 2.5f, DefaultRelease = 3.5f, DefaultReleaseDelay = 0.6f, DefaultMaxLevel = 1.0f, DefaultTalkSlack = 1.0f;

        public float StartRadius { get; }
        public float ReleaseRadius { get; }
        public float ReleaseDelay { get; }
        public float MaxLevel { get; }
        public float TalkSlack { get; }

        public MechanicAttention(float start = DefaultStart, float release = DefaultRelease, float releaseDelay = DefaultReleaseDelay, float maxLevel = DefaultMaxLevel, float talkSlack = DefaultTalkSlack)
        {
            StartRadius = start > 0f ? start : DefaultStart;
            ReleaseRadius = Math.Max(StartRadius, release);
            ReleaseDelay = Math.Max(0f, releaseDelay);
            MaxLevel = maxLevel > 0f ? maxLevel : DefaultMaxLevel;
            TalkSlack = Math.Max(0f, talkSlack);
        }

        /// <summary>The attended player's id ("" = nobody).</summary>
        public string Target { get; private set; } = "";
        public bool Active => Target.Length > 0;
        /// <summary>Seconds the current target has been out of range / sight (released at ReleaseDelay).</summary>
        public float Lost { get; private set; }

        private bool SameLevel(in AttentionCandidate c) => Math.Abs(c.Dy) <= MaxLevel;
        private bool Holds(in AttentionCandidate c) =>
            SameLevel(c) && (c.Talking ? c.Distance <= ReleaseRadius + TalkSlack : c.Visible && c.Distance <= ReleaseRadius);
        private bool Catches(in AttentionCandidate c) =>
            SameLevel(c) && (c.Talking ? c.Distance <= ReleaseRadius + TalkSlack : c.Visible && c.Distance <= StartRadius);

        public string Tick(float dt, IReadOnlyList<AttentionCandidate> candidates)
        {
            if (float.IsNaN(dt) || dt < 0f) dt = 0f;
            int current = -1, talker = -1, nearest = -1;
            for (int i = 0; candidates != null && i < candidates.Count; i++)
            {
                AttentionCandidate c = candidates[i];
                if (string.IsNullOrEmpty(c.Id)) continue;
                if (c.Id == Target) current = i;
                if (c.Talking && Holds(c) && (talker < 0 || Better(c, candidates[talker]))) talker = i;
                if (Catches(c) && (nearest < 0 || Better(c, candidates[nearest]))) nearest = i;
            }
            // the conversation participant first (a second customer never steals the face of the one who talks)
            if (talker >= 0 && (current < 0 || !candidates[current].Talking || !Holds(candidates[current])))
            {
                Target = candidates[talker].Id;
                Lost = 0f;
                return Target;
            }
            if (Active)
            {
                if (current >= 0 && Holds(candidates[current])) { Lost = 0f; return Target; }
                Lost += dt;
                if (Lost < ReleaseDelay) return Target;
                Target = "";
                Lost = 0f;
            }
            if (nearest >= 0) { Target = candidates[nearest].Id; Lost = 0f; }
            return Target;
        }

        public void Clear() { Target = ""; Lost = 0f; }

        private static bool Better(in AttentionCandidate a, in AttentionCandidate b)
        {
            float da = a.Distance, db = b.Distance;
            if (Math.Abs(da - db) > 0.01f) return da < db;
            return string.CompareOrdinal(a.Id, b.Id) < 0;
        }
    }

    /// <summary>Why E at the mechanic did not open his conversation (None = it opens).</summary>
    public enum MechanicTalkRefusal : byte
    {
        None = 0,
        /// <summary>No local player body (in the van, dead, the menu camera).</summary>
        NoPlayer = 1,
        /// <summary>Another menu owns the keyboard (pause, phone, pharmacy, a save prompt).</summary>
        MenuOpen = 2,
        /// <summary>Another floor: the pit, the roof, a balcony.</summary>
        OtherLevel = 3,
        TooFar = 4,
        /// <summary>The van right here owns E (get in, a door, its handle) and the player is not looking at him.</summary>
        VanOwnsE = 5,
        /// <summary>Another interaction used this E press first (carrying a body bag drops it, ...).</summary>
        ETaken = 6,
        /// <summary>The team fund has not reached this machine yet (a client right after joining).</summary>
        EconomyLoading = 7,
    }

    /// <summary>What the local machine knows when E is pressed near the mechanic (feet and eye relative to HIS feet).</summary>
    public struct MechanicTalkInput
    {
        public bool HasPlayer, MenuOpen, ETaken, EconomyReady, VanOffersE;
        /// <summary>Player feet minus mechanic feet (metres).</summary>
        public float Dx, Dy, Dz;
        /// <summary>Player eye minus mechanic feet, and the unit view direction (the crosshair ray).</summary>
        public float EyeX, EyeY, EyeZ, ViewX, ViewY, ViewZ;
        public bool HasView;
        /// <summary>Nothing solid between the eye and his chest (the runtime's line of sight; only matters beyond Radius).</summary>
        public bool SightClear;
    }

    /// <summary>
    /// The E conversation with the workshop mechanic (Fedya 29.10: "E at the mechanic does nothing"). He walks a route now,
    /// stands, attends, works or walks, so reach is measured from HIS BODY wherever it is, horizontally (the old 3 m sphere
    /// from the feet also failed on a step), never from a physics collider (his capsule is off while he walks or a player is
    /// right on him). Reach: within <see cref="Radius"/> flat metres on the same level, or looking at him (the crosshair ray
    /// passes within <see cref="AimTolerance"/> of his body between feet and head) up to <see cref="AimRadius"/> with a
    /// clear sight line. The van owns E only when the player is NOT looking at the mechanic. The server accepts the
    /// mission request within <see cref="ServerReach"/> (the client's leash plus slack). Pure: no Unity types.
    /// </summary>
    public static class MechanicTalkReach
    {
        public const float Radius = 3.0f;
        public const float AimRadius = 4.5f;
        public const float AimTolerance = 0.5f;
        public const float BodyHeight = 1.85f;
        public const float MaxLevel = 1.4f;
        /// <summary>The open conversation closes beyond this from him AND from where it was opened.</summary>
        public const float Leash = AimRadius + 1.0f;
        public const float ServerReach = Leash + 1.5f;

        public static float Flat(float dx, float dz) => (float)Math.Sqrt(dx * dx + dz * dz);

        public static bool SameLevel(float dy) => Math.Abs(dy) <= MaxLevel;

        /// <summary>Standing close enough (no aim needed).</summary>
        public static bool Near(float dx, float dy, float dz) => SameLevel(dy) && Flat(dx, dz) <= Radius;

        /// <summary>The view ray from the eye (relative to his feet) passes his body (a vertical segment at x = z = 0 from
        /// the feet to <see cref="BodyHeight"/>) within <see cref="AimTolerance"/>, in front of the eye and within
        /// <see cref="AimRadius"/> along the ray.</summary>
        public static bool Aimed(float ex, float ey, float ez, float vx, float vy, float vz)
        {
            float len = (float)Math.Sqrt(vx * vx + vy * vy + vz * vz);
            if (len < 1e-4f || float.IsNaN(len)) return false;
            vx /= len; vy /= len; vz /= len;
            float flat2 = vx * vx + vz * vz;
            if (flat2 < 1e-4f) return false; // looking straight up / down
            // closest approach of the ray's ground track to his axis
            float t = -(ex * vx + ez * vz) / flat2;
            if (t < 0f || t > AimRadius) return false;
            float px = ex + vx * t, pz = ez + vz * t, py = ey + vy * t;
            if (px * px + pz * pz > AimTolerance * AimTolerance) return false;
            return py >= -0.1f && py <= BodyHeight + 0.15f;
        }

        public static MechanicTalkRefusal Check(in MechanicTalkInput i)
        {
            if (!i.HasPlayer) return MechanicTalkRefusal.NoPlayer;
            if (i.MenuOpen) return MechanicTalkRefusal.MenuOpen;
            if (!SameLevel(i.Dy)) return MechanicTalkRefusal.OtherLevel;
            bool aimed = i.HasView && Aimed(i.EyeX, i.EyeY, i.EyeZ, i.ViewX, i.ViewY, i.ViewZ);
            bool near = Flat(i.Dx, i.Dz) <= Radius;
            if (!near && !(aimed && i.SightClear)) return MechanicTalkRefusal.TooFar;
            if (i.VanOffersE && !aimed) return MechanicTalkRefusal.VanOwnsE;
            if (i.ETaken) return MechanicTalkRefusal.ETaken;
            if (!i.EconomyReady) return MechanicTalkRefusal.EconomyLoading;
            return MechanicTalkRefusal.None;
        }

        /// <summary>The open conversation stays while the player is within the leash of him or of where it was opened.</summary>
        public static bool KeepOpen(float toBodyX, float toBodyZ, float toOpenX, float toOpenZ) =>
            Flat(toBodyX, toBodyZ) <= Leash || Flat(toOpenX, toOpenZ) <= Leash;

        /// <summary>Server: the requester is close enough to the mechanic (or his home anchor) for the M06 request.</summary>
        public static bool ServerAccepts(float dx, float dy, float dz) => Math.Abs(dy) <= MaxLevel + 1f && Flat(dx, dz) <= ServerReach;
    }
}
