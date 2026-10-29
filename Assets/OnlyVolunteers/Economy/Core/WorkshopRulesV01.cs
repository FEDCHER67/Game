using System;
using System.Collections.Generic;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Economy
{
    /// <summary>One line of the mechanic's E conversation (Workshop_W86, STORY M06 + ECONOMY §6.3).</summary>
    public enum MechanicOption : byte
    {
        /// <summary>A short placeholder chat line that fits the mission state (no gate, no reward).</summary>
        Chat = 0,
        /// <summary>M06 offered: take the rival task (the existing StoryMechanic request).</summary>
        AcceptRival = 1,
        /// <summary>M06 active: hand the rival over (the same StoryMechanic request; the server measures the western bay).</summary>
        HandInRival = 2,
        /// <summary>The workshop is open (M06 done, or the DEV unlock toggle): put the team van on the lift and upgrade it.</summary>
        UpgradeVan = 3,
        Bye = 4,
    }

    /// <summary>The mechanic's conversation (pure): which lines it offers in which state, their titles and the placeholder
    /// chat. The M06 commits stay the story's own (EconomyState.AcceptMechanicTask / CompleteRivalHandIn through
    /// StoryDirector); this only decides what the menu shows.</summary>
    public static class MechanicDialogue
    {
        public static List<MechanicOption> Options(JournalState m06, bool workshopUnlocked)
        {
            var list = new List<MechanicOption> { MechanicOption.Chat };
            if (m06 == JournalState.Offered) list.Add(MechanicOption.AcceptRival);
            else if (m06 == JournalState.Active) list.Add(MechanicOption.HandInRival);
            if (workshopUnlocked) list.Add(MechanicOption.UpgradeVan);
            list.Add(MechanicOption.Bye);
            return list;
        }

        public static string Title(MechanicOption o)
        {
            switch (o)
            {
                case MechanicOption.Chat: return "Как дела?";
                case MechanicOption.AcceptRival: return "Есть работа? (взять поручение)";
                case MechanicOption.HandInRival: return "Конкурент доставлен (сдать)";
                case MechanicOption.UpgradeVan: return "Улучшить бусик";
                default: return "Пока";
            }
        }

        private static readonly string[] LockedLines =
        {
            "Механик: «Мастерская? Работы сейчас по горло. Заглядывай позже — может, и для вас дело найдётся.»",
            "Механик: «Масло, гайки, ржавчина. Жизнь механика. Ты что-то хотел?»",
        };
        private static readonly string[] OfferedLines =
        {
            "Механик: «Слушай, есть одна проблема. Конкурент под навесом на Стройке переманивает моих клиентов.»",
            "Механик: «Поможете мне с конкурентом — открою вам мастерскую. По-соседски.»",
        };
        private static readonly string[] ActiveLines =
        {
            "Механик: «Ну что, привезли его? Связанным, в западный бокс — там зона приёма.»",
            "Механик: «Он работает под навесом на Стройке с восьми до шести. Потом уходит к общаге.»",
        };
        private static readonly string[] OpenLines =
        {
            "Механик: «Загоняй бусик в средний бокс, на подъёмник — посмотрим, что можно сделать.»",
            "Механик: «Движок, руль, тормоза — всё сделаю, были бы деньги.»",
        };

        /// <summary>The placeholder chat line for this state; turn picks one of the variants (0, 1, 2 ...).</summary>
        public static string ChatLine(JournalState m06, bool workshopUnlocked, int turn)
        {
            string[] lines = workshopUnlocked ? OpenLines : m06 == JournalState.Offered ? OfferedLines : m06 == JournalState.Active ? ActiveLines : LockedLines;
            return lines[(turn % lines.Length + lines.Length) % lines.Length];
        }
    }

    /// <summary>The workshop lift (Workshop_W86 middle bay): down, rising, raised, lowering.</summary>
    public enum LiftPhase : byte { Down = 0, Raising = 1, Up = 2, Lowering = 3 }

    public enum WorkshopRefusal : byte
    {
        None = 0, InvalidRequest, NotReady, WorkshopLocked, Busy, NoVan, VanNotInZone, VanMoving, VanDriven, BodyInWay, TooFar,
        NotOwner, NotRaised, NoSession, VanNotAligned,
        /// <summary>The mechanic is already performing an upgrade (one at a time; MECHANIC_W86 v01).</summary>
        MechanicBusy,
    }

    /// <summary>What the server measured for a lift start (the requester's own position, the team van, the bay).</summary>
    public struct LiftStartCheck
    {
        public bool Ready;
        public bool WorkshopUnlocked;
        public bool ActorNear;
        public bool VanFound;
        public bool VanInZone;
        /// <summary>Over the pads within the tolerance (it is settled onto them while it rises).</summary>
        public bool VanAligned;
        public bool VanStopped;
        public bool SomeoneDriving;
        /// <summary>A player or a free NPC stands where the van and the lift arms move.</summary>
        public bool BodyInWay;

        public static LiftStartCheck Good => new LiftStartCheck
        { Ready = true, WorkshopUnlocked = true, ActorNear = true, VanFound = true, VanInZone = true, VanAligned = true, VanStopped = true };
    }

    /// <summary>
    /// The ONE upgrade session of the workshop lift (pure, server side): one owner at a time raises the team van, buys tiers
    /// while it is up and lowers it with "Done". Raising = the four arms swing in under the sills (<see cref="SwingSeconds"/>),
    /// then carriages, arms and van rise <see cref="Travel"/> m in <see cref="Seconds"/> s; lowering is the reverse (down, then
    /// the arms swing out of the wheel path) and the session ends when the arms are stowed. Travel and timing come from the
    /// lift data (Workshop_W86_lift_v01.json via the integrator), defaults below. Nothing moves while something is in the
    /// way (nobody is ever pushed). When the owner leaves (walks away, disconnects, cancels) the lift goes down on its own:
    /// the van is never left held or lifted.
    /// </summary>
    public sealed class LiftSession
    {
        public const float DefaultTravel = 1.6f;
        public const float DefaultSeconds = 4f;
        public const float DefaultSwingSeconds = 1.5f;
        private const float Epsilon = 1e-4f;

        public float Travel { get; }
        public float Seconds { get; }
        public float SwingSeconds { get; }

        public LiftSession(float travel = DefaultTravel, float seconds = DefaultSeconds, float swingSeconds = DefaultSwingSeconds)
        {
            Travel = travel > 0.05f && travel < 5f ? travel : DefaultTravel;
            Seconds = seconds > 0.1f ? seconds : DefaultSeconds;
            SwingSeconds = swingSeconds >= 0f ? swingSeconds : DefaultSwingSeconds;
        }

        public LiftPhase Phase { get; private set; } = LiftPhase.Down;
        /// <summary>Lift height above the floor, 0..Travel (metres).</summary>
        public float Height { get; private set; }
        /// <summary>Arms: 0 = stowed along the van (out of the wheel path), 1 = swung in under the sills.</summary>
        public float Swing { get; private set; }
        /// <summary>The participant id of the session owner ("" = no session).</summary>
        public string Owner { get; private set; } = "";
        public bool Active => Owner.Length > 0;
        /// <summary>The van is on the lift (kinematic, nobody drives it) from the start until the arms are stowed again.</summary>
        public bool HoldsVan => Active || Phase != LiftPhase.Down || Height > 0f || Swing > 0f;
        /// <summary>The last reason the session ended or was refused (for logs).</summary>
        public string LastEnd { get; private set; } = "";

        public WorkshopRefusal TryStart(string owner, in LiftStartCheck c)
        {
            if (string.IsNullOrEmpty(owner) || owner.Length > 64) return WorkshopRefusal.InvalidRequest;
            if (Active && Owner == owner && (Phase == LiftPhase.Up || Phase == LiftPhase.Raising)) return WorkshopRefusal.None; // the owner reopens the screen
            if (HoldsVan) return WorkshopRefusal.Busy;
            if (!c.Ready) return WorkshopRefusal.NotReady;
            if (!c.WorkshopUnlocked) return WorkshopRefusal.WorkshopLocked;
            if (!c.ActorNear) return WorkshopRefusal.TooFar;
            if (!c.VanFound) return WorkshopRefusal.NoVan;
            if (!c.VanInZone) return WorkshopRefusal.VanNotInZone;
            if (!c.VanAligned) return WorkshopRefusal.VanNotAligned;
            if (c.SomeoneDriving) return WorkshopRefusal.VanDriven;
            if (!c.VanStopped) return WorkshopRefusal.VanMoving;
            if (c.BodyInWay) return WorkshopRefusal.BodyInWay;
            Owner = owner;
            Phase = LiftPhase.Raising;
            LastEnd = "";
            return WorkshopRefusal.None;
        }

        /// <summary>Advances the lift by dt seconds unless blocked. True when the phase changed (Raising -> Up, Lowering ->
        /// Down, which also ends the session).</summary>
        public bool Tick(float dt, bool blocked)
        {
            if (blocked || dt <= 0f || float.IsNaN(dt)) return false;
            float swingStep = SwingSeconds > 0f ? dt / SwingSeconds : 1f;
            switch (Phase)
            {
                case LiftPhase.Raising:
                    if (Swing < 1f)
                    {
                        // the arms first; any time left over in this step goes into the rise
                        float need = (1f - Swing) * SwingSeconds;
                        Swing = Math.Min(1f, Swing + swingStep);
                        if (Swing < 1f - Epsilon) return false;
                        Swing = 1f;
                        dt = Math.Max(0f, dt - need);
                    }
                    Height = Math.Min(Travel, Height + Travel / Seconds * dt);
                    if (Height >= Travel - Epsilon) { Height = Travel; Phase = LiftPhase.Up; return true; }
                    return false;
                case LiftPhase.Lowering:
                    if (Height > 0f)
                    {
                        float need = Height / (Travel / Seconds);
                        Height = Math.Max(0f, Height - Travel / Seconds * dt);
                        if (Height > Epsilon) return false;
                        Height = 0f;
                        dt = Math.Max(0f, dt - need);
                        swingStep = SwingSeconds > 0f ? dt / SwingSeconds : 1f;
                    }
                    Swing = Math.Max(0f, Swing - swingStep);
                    if (Swing <= Epsilon) { Swing = 0f; Phase = LiftPhase.Down; Owner = ""; return true; }
                    return false;
                default:
                    return false;
            }
        }

        /// <summary>"Done" from the owner: the lift goes down (from wherever it is).</summary>
        public WorkshopRefusal Finish(string requester)
        {
            if (!Active) return WorkshopRefusal.NoSession;
            if (requester != Owner) return WorkshopRefusal.NotOwner;
            Lower("done");
            return WorkshopRefusal.None;
        }

        /// <summary>The owner left (disconnect, walked away, server stop): down on its own, nothing else changes.</summary>
        public void Abort(string why)
        {
            if (!HoldsVan) return;
            Lower(why);
        }

        private void Lower(string why)
        {
            LastEnd = why ?? "";
            if (Phase == LiftPhase.Down && Height <= 0f && Swing <= 0f) { Owner = ""; return; }
            Phase = LiftPhase.Lowering;
        }

        /// <summary>Purchases only while the van is up, and only by the session owner.</summary>
        public WorkshopRefusal CanBuy(string requester)
        {
            if (!Active) return WorkshopRefusal.NoSession;
            if (requester != Owner) return WorkshopRefusal.NotOwner;
            return Phase == LiftPhase.Up ? WorkshopRefusal.None : WorkshopRefusal.NotRaised;
        }

        /// <summary>Clients: the server's state as received (phase, height, arm swing, owner).</summary>
        public void Set(LiftPhase phase, float height, float swing, string owner)
        {
            Phase = phase;
            Height = Math.Max(0f, Math.Min(Travel, height));
            Swing = Math.Max(0f, Math.Min(1f, swing));
            Owner = owner ?? "";
        }
    }

    /// <summary>Workshop purchase gating on the lift: the lift session first, then the existing van tier rules of
    /// EconomyState.TryBuyVanTier (unlock, zone, tier order, funds; deterministic key van:&lt;branch&gt;:&lt;tier&gt; = paid
    /// once per world). The lift holds the van, so it counts as braked and standing.</summary>
    public static class WorkshopRules
    {
        public static string Explain(WorkshopRefusal r)
        {
            switch (r)
            {
                case WorkshopRefusal.None: return "";
                case WorkshopRefusal.NotReady: return PurchaseResult.Explain(PurchaseError.NotReady);
                case WorkshopRefusal.WorkshopLocked: return "Механик: «Сначала дело с конкурентом — потом мастерская.»";
                case WorkshopRefusal.Busy: return "Подъёмник занят: бусиком уже занимаются";
                case WorkshopRefusal.NoVan: return "Бусика нет поблизости";
                case WorkshopRefusal.VanNotInZone: return "Загони бусик в средний бокс, в жёлтую зону над ямой";
                case WorkshopRefusal.VanMoving: return "Бусик ещё катится — останови его";
                case WorkshopRefusal.VanDriven: return "Выйди из бусика — за рулём нельзя на подъёмник";
                case WorkshopRefusal.BodyInWay: return "Отойдите от бусика и подъёмника";
                case WorkshopRefusal.TooFar: return "Подойди к механику";
                case WorkshopRefusal.NotOwner: return "Бусиком сейчас занимается другой игрок";
                case WorkshopRefusal.NotRaised: return "Подожди, пока подъёмник поднимет бусик";
                case WorkshopRefusal.NoSession: return "Подъёмник не занят";
                case WorkshopRefusal.VanNotAligned: return "Поставь бусик ровно над ямой, носом к задней стене (или задом) — колёса по краям ямы";
                case WorkshopRefusal.MechanicBusy: return "Механик уже колдует над бусиком — секунду";
                default: return "Неверный запрос";
            }
        }

        public static PurchaseResult Refused(WorkshopRefusal r, EconomyState state) => new PurchaseResult
        {
            Ok = false, Error = PurchaseError.InvalidRequest, Balance = state != null ? state.Fund.Balance : 0, Message = Explain(r),
        };

        /// <summary>Server: one van tier bought on the lift by the requester (vanInZone = the server's own measurement).</summary>
        public static PurchaseResult TryBuyVanTier(EconomyState state, LiftSession session, string requester, VanBranch branch, int expectedNextTier, bool vanInZone)
        {
            if (state == null || session == null) return Refused(WorkshopRefusal.InvalidRequest, state);
            WorkshopRefusal gate = session.CanBuy(requester);
            if (gate != WorkshopRefusal.None) return Refused(gate, state);
            var check = new VanShopCheck { InZone = vanInZone, Handbrake = true, Stopped = true };
            return state.TryBuyVanTier(branch, expectedNextTier, check);
        }

        /// <summary>Server: one cargo-body upgrade (capacity / containment; ECONOMY §6.2, Fedya 29.10) bought on the lift by
        /// the requester: the lift session first, then EconomyState.TryBuyVanCargo (unlock, zone, prerequisite, price shown,
        /// funds; deterministic key van:cargo:&lt;id&gt; = paid once per world).</summary>
        public static PurchaseResult TryBuyVanCargo(EconomyState state, LiftSession session, string requester, string cargoId, int expectedPrice, bool vanInZone)
        {
            if (state == null || session == null) return Refused(WorkshopRefusal.InvalidRequest, state);
            WorkshopRefusal gate = session.CanBuy(requester);
            if (gate != WorkshopRefusal.None) return Refused(gate, state);
            var check = new VanShopCheck { InZone = vanInZone, Handbrake = true, Stopped = true };
            return state.TryBuyVanCargo(cargoId, expectedPrice, check);
        }
    }

    /// <summary>One row of the workshop's upgrade screen. Kind + Arg name the server handler (van_branch + "0"/"1"/"2";
    /// van_cargo + the catalogue id) and Expected is what the server re-checks: the tier the buyer sees as next, or, for a
    /// single purchase (<see cref="Single"/>), the price shown.</summary>
    public sealed class WorkshopUpgradeRow
    {
        public string Kind = "";
        public string Arg = "";
        public string Group = "";
        public string Title = "";
        public int Tier;
        public int MaxTier;
        /// <summary>Price of the next tier through the catalogue (EconomyPrices); -1 at the top or when unbound / open.</summary>
        public int NextPrice = -1;
        /// <summary>A one-step purchase (cargo body: bought / not bought): the screen shows its price or "installed", not a
        /// tier arrow, and Expected is the price.</summary>
        public bool Single;
        public int Expected => Single ? NextPrice : Tier + 1;
        public bool AtMax => Tier >= MaxTier;
        /// <summary>Filled by the runtime (it knows the van's tuning): what the next tier changes.</summary>
        public string Effect = "";
        /// <summary>Why it cannot be bought now ("" = buyable when the money suffices).</summary>
        public string Blocked = "";
        /// <summary>Van branch rows: the branch (other kinds ignore it).</summary>
        public VanBranch Branch;
    }

    /// <summary>The upgrade screen's rows, built from the catalogue by providers: the van branches (engine / handling /
    /// brakes, tiers 0-III, G48 prices) and the cargo body (capacity I / II, containment I / II, storage greyed: Fedya
    /// 29.10). Further upgrade groups add a provider (rows from their catalogue ids) and a server handler for their Kind;
    /// the screen itself lists whatever rows it gets.</summary>
    public static class WorkshopUpgradeRows
    {
        public const string VanBranchKind = "van_branch";
        public const string VanCargoKind = "van_cargo";
        public static readonly VanBranch[] Branches = { VanBranch.Engine, VanBranch.Handling, VanBranch.Brakes };

        public static readonly List<Func<EconomySnapshot, IEnumerable<WorkshopUpgradeRow>>> Providers =
            new List<Func<EconomySnapshot, IEnumerable<WorkshopUpgradeRow>>> { VanBranchRows, VanCargoRows };

        public static List<WorkshopUpgradeRow> Build(EconomySnapshot snapshot)
        {
            var rows = new List<WorkshopUpgradeRow>();
            if (snapshot == null) return rows;
            foreach (var provider in Providers)
            {
                if (provider == null) continue;
                IEnumerable<WorkshopUpgradeRow> got = provider(snapshot);
                if (got != null) rows.AddRange(got);
            }
            return rows;
        }

        public static IEnumerable<WorkshopUpgradeRow> VanBranchRows(EconomySnapshot snapshot)
        {
            foreach (VanBranch b in Branches)
            {
                int tier = snapshot.VanTier(b);
                var row = new WorkshopUpgradeRow
                {
                    Kind = VanBranchKind, Arg = ((int)b).ToString(System.Globalization.CultureInfo.InvariantCulture), Group = "Бусик",
                    Title = EconomyPrices.BranchTitle(b), Tier = tier, MaxTier = EconomyPrices.VanMaxTier, Branch = b,
                };
                row.NextPrice = row.AtMax ? -1 : EconomyPrices.VanTierPrice(b, tier + 1);
                if (snapshot.vanLegacyDebugProfile) row.Blocked = PurchaseResult.Explain(PurchaseError.LegacyDebugProfile);
                else if (!snapshot.workshopUnlocked) row.Blocked = PurchaseResult.Explain(PurchaseError.WorkshopLocked);
                else if (row.AtMax) row.Blocked = "максимум";
                else if (row.NextPrice <= 0) row.Blocked = PurchaseResult.Explain(PurchaseError.ItemUnavailable);
                yield return row;
            }
        }

        /// <summary>The cargo body, one single-purchase row per catalogue id (VanCargo.Ids order). Storage stays listed with
        /// its price but blocked ("not available yet": no fridge in the game); a step whose prerequisite is missing says
        /// which one comes first.</summary>
        public static IEnumerable<WorkshopUpgradeRow> VanCargoRows(EconomySnapshot snapshot)
        {
            foreach (string id in VanCargo.Ids)
            {
                VanCargoOffer offer = VanCargo.Find(id);
                bool owned = snapshot.OwnsVanCargo(id);
                var row = new WorkshopUpgradeRow
                {
                    Kind = VanCargoKind, Arg = id, Group = "Кузов", Title = offer.Title, Single = true,
                    Tier = owned ? 1 : 0, MaxTier = 1, NextPrice = owned ? -1 : offer.Price, Effect = offer.Effect,
                };
                if (owned) row.Blocked = "установлено";
                else if (snapshot.vanLegacyDebugProfile) row.Blocked = PurchaseResult.Explain(PurchaseError.LegacyDebugProfile);
                else if (!snapshot.workshopUnlocked) row.Blocked = PurchaseResult.Explain(PurchaseError.WorkshopLocked);
                else if (!offer.Purchasable) row.Blocked = offer.UnavailableReason;
                else if (offer.Requires.Length > 0 && !snapshot.OwnsVanCargo(offer.Requires)) row.Blocked = "Сначала нужно: " + VanCargo.Title(offer.Requires);
                yield return row;
            }
        }
    }
}
