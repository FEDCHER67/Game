using System;
using System.Collections.Generic;
using OnlyVolunteers.Story;

namespace OnlyVolunteers.Economy
{
    public enum DeliveryState
    {
        /// <summary>Paid, the game hour has not passed yet.</summary>
        Pending = 0,
        /// <summary>Due, but every delivery anchor of the base is occupied (or the base has none in this scene): it waits.</summary>
        Waiting = 1,
        /// <summary>The closed paid crate stands at an anchor.</summary>
        Arrived = 2,
        /// <summary>Unpacked: the item (or its labelled placeholder) stands where the crate was opened.</summary>
        Opened = 3,
    }

    /// <summary>One paid equipment order (§4.1): payment, delivery and its permanent id are made in one commit.</summary>
    [Serializable]
    public sealed class DeliveryOrder
    {
        public string id = "";
        /// <summary>The client's request key: repeating the request answers with this order instead of a second one.</summary>
        public string key = "";
        public string itemId = "";
        public string baseId = "";
        public int price;
        public double orderedAt;
        public double dueAt;
        public int state;
        public int anchorSlot = -1;
        /// <summary>Where the crate (Arrived) or the unpacked item (Opened) stands, world metres; yaw in degrees.</summary>
        public float x, y, z, yaw;

        public DeliveryState State { get => (DeliveryState)state; set => state = (int)value; }
        public DeliveryOrder Copy() => (DeliveryOrder)MemberwiseClone();
    }

    /// <summary>What the server measured on the van at the moment of the commit (§6.3).</summary>
    public struct VanShopCheck
    {
        public bool InZone;
        public bool Handbrake;
        public bool Stopped;

        public static VanShopCheck Ready => new VanShopCheck { InZone = true, Handbrake = true, Stopped = true };
    }

    public enum PurchaseError
    {
        None, InvalidRequest, NotReady, WorkshopLocked, LegacyDebugProfile, VanNotInZone, HandbrakeOff, VanMoving,
        AlreadyMax, TierChanged, UnknownItem, ItemUnavailable, BaseNotOwned, BaseNoDelivery, StoryLocked, AlreadyOwned,
        NotForSale, PriceChanged, InsufficientFunds, LevelLocked,
        /// <summary>A cargo-body step needs the previous one first (catalogue refs.requires; van cargo, Fedya 29.10).</summary>
        RequiresUpgrade,
    }

    public sealed class PurchaseResult
    {
        public bool Ok;
        /// <summary>The same request was already committed: nothing changed now, the first outcome stands.</summary>
        public bool Replayed;
        public PurchaseError Error;
        public int Price;
        public int Balance;
        public string DeliveryId = "";
        public string Message = "";

        public static string Explain(PurchaseError e)
        {
            switch (e)
            {
                case PurchaseError.None: return "";
                case PurchaseError.NotReady: return "Сохранение ещё загружается — попробуй через секунду";
                case PurchaseError.WorkshopLocked: return "Мастерская ещё закрыта (поручение механика)";
                case PurchaseError.LegacyDebugProfile: return "Этот слот в отладочном профиле бусика (старый StartAtMax): сначала переведи его на прогрессию";
                case PurchaseError.VanNotInZone: return "Фургон не в ремонтной зоне мастерской";
                case PurchaseError.HandbrakeOff: return "Поставь фургон на ручник";
                case PurchaseError.VanMoving: return "Фургон ещё едет — остановись";
                case PurchaseError.AlreadyMax: return "Эта ветка уже на ступени III";
                case PurchaseError.TierChanged: return "Ступень уже изменилась — проверь карточку";
                case PurchaseError.UnknownItem: return "Такого товара нет";
                case PurchaseError.ItemUnavailable: return "Позиция пока недоступна";
                case PurchaseError.BaseNotOwned: return "Эта база команде не принадлежит";
                case PurchaseError.BaseNoDelivery: return "На эту базу оборудование не доставляют";
                case PurchaseError.StoryLocked: return "Недвижимость откроется после знакомства с первым органным скупщиком";
                case PurchaseError.AlreadyOwned: return "Уже куплено";
                case PurchaseError.NotForSale: return "Не продаётся";
                case PurchaseError.PriceChanged: return "Цена изменилась — проверь карточку";
                case PurchaseError.InsufficientFunds: return "Недостаточно общих денег";
                case PurchaseError.LevelLocked: return "Требуется более высокий уровень команды";
                case PurchaseError.RequiresUpgrade: return "Сначала нужна предыдущая ступень";
                default: return "Неверный запрос";
            }
        }
    }

    /// <summary>
    /// The whole economic state of one team world (server side, pure C#): the fund, paid van tiers, story/workshop flags,
    /// owned bases, equipment deliveries and the world game clock they run on. Every purchase checks its preconditions,
    /// then charges and applies in the same call (the server is single-threaded: the first commit wins, a second one that
    /// no longer fits gets "Недостаточно общих денег"). Nothing here touches Unity; TeamEconomy runs it on the host.
    /// </summary>
    public sealed partial class EconomyState
    {
        /// <summary>2 (WP02): + XP spends, first-of-a-kind / first-blood flags (EconomyProgress.cs). A version 1 block loads:
        /// its sale XP lines stay, the first-blood flag is derived from its blood XP lines once.</summary>
        public const int BlockVersion = 2;
        public const string DeliveryIdPrefix = "DLV-";
        private const int BranchCount = 3;

        private readonly int[] vanTiers = new int[BranchCount];
        private readonly List<string> ownedBases = new List<string>();
        private readonly List<DeliveryOrder> deliveries = new List<DeliveryOrder>();
        private readonly List<XpEntry> xp = new List<XpEntry>();
        private long deliverySeq;
        private double worldHours;
        private int worldDay;
        private double timeOfDay = -1;

        public FundLedger Fund { get; private set; } = new FundLedger();
        /// <summary>§10.3.5: an old StartAtMax slot keeps the legacy/debug van profile (old max) until the owner explicitly
        /// moves it to the progression; purchases are refused meanwhile and nothing is refunded or granted.</summary>
        public bool VanLegacyDebugProfile { get; private set; }
        public bool WorkshopUnlocked { get; private set; }
        /// <summary>Story flag "first organ buyer met" (§2, §7.1): opens the property catalogue.</summary>
        public bool FirstOrganBuyerMet { get; private set; }
        /// <summary>Where the balance came from: "new-game", "legacy-host-cash", "none" (old save without cash).</summary>
        public string MigrationSource { get; private set; } = "new-game";
        public double WorldHours => worldHours;
        /// <summary>World calendar: day number and the sky-clock hour (both saved; closed-world time is frozen).</summary>
        public int WorldDay => worldDay;
        public double TimeOfDay => timeOfDay;
        /// <summary>Absolute game hours since 00:00 of day 0 (schedules, the 06:00 mornings of daily finds and recovery).</summary>
        public double AbsoluteHours => worldDay * 24.0 + Math.Max(0.0, timeOfDay);
        /// <summary>Story missions M01-M13: committed in the same state (and save block) as the fund and unlock flags.</summary>
        public StoryState Story { get; private set; } = new StoryState();
        public IReadOnlyList<XpEntry> Xp => xp;
        public IReadOnlyList<string> OwnedBases => ownedBases;
        public IReadOnlyList<DeliveryOrder> Deliveries => deliveries;

        /// <summary>Raised after any committed change (money, tiers, flags, bases, deliveries).</summary>
        public event Action Changed;

        public static EconomyState NewGame()
        {
            var s = new EconomyState();
            // §7.1: the forest wagon is free (prologue), the hamlet hut / shed comes with the van in both grandpa branches.
            s.ownedBases.Add(EconomyPrices.BaseWagon);
            s.ownedBases.Add(EconomyPrices.BaseHamlet);
            return s;
        }

        public int VanTier(VanBranch branch) => (uint)branch < BranchCount ? vanTiers[(int)branch] : 0;
        public bool OwnsBase(string baseId) => ownedBases.Contains(baseId);

        public static string VanKey(VanBranch branch, int tier) => "van:" + branch.ToString().ToLowerInvariant() + ":" + tier;
        public static string PropertyKey(string baseId) => "property:" + baseId;
        public static string EquipmentKey(string requestKey) => "equipment:" + requestKey;

        // ---------- van (§6.1, §6.3) ----------

        /// <summary>Buys the next tier of one branch. expectedNextTier is the tier the buyer saw on the card: the server
        /// checks it against its own current tier (no skipping, no double tier). The charge key is deterministic
        /// (van:engine:2): a tier is paid once per team world whatever the clients send.</summary>
        public PurchaseResult TryBuyVanTier(VanBranch branch, int expectedNextTier, VanShopCheck check)
        {
            if ((uint)branch >= BranchCount) return Fail(PurchaseError.InvalidRequest);
            int current = vanTiers[(int)branch];
            if (expectedNextTier >= 1 && expectedNextTier <= current && Fund.IsCommitted(VanKey(branch, expectedNextTier)))
                return Replay(EconomyPrices.VanTierPrice(branch, expectedNextTier), "Уже куплено: " + EconomyPrices.BranchTitle(branch) + " " + EconomyPrices.TierName(expectedNextTier));
            if (!WorkshopUnlocked) return Fail(PurchaseError.WorkshopLocked);
            if (VanLegacyDebugProfile) return Fail(PurchaseError.LegacyDebugProfile);
            if (!check.InZone) return Fail(PurchaseError.VanNotInZone);
            if (!check.Handbrake) return Fail(PurchaseError.HandbrakeOff);
            if (!check.Stopped) return Fail(PurchaseError.VanMoving);
            if (current >= EconomyPrices.VanMaxTier) return Fail(PurchaseError.AlreadyMax);
            int next = current + 1;
            if (expectedNextTier != next) return Fail(PurchaseError.TierChanged);
            int price = EconomyPrices.VanTierPrice(branch, next);
            if (price <= 0) return Fail(PurchaseError.ItemUnavailable);
            string title = EconomyPrices.BranchTitle(branch) + " " + EconomyPrices.TierName(next);
            FundResult paid = Fund.TryCharge(price, "van", "Мастерская: " + title, VanKey(branch, next));
            if (paid.Status == FundStatus.Insufficient) return Fail(PurchaseError.InsufficientFunds, price);
            if (!paid.Ok) return Fail(PurchaseError.InvalidRequest, price);
            vanTiers[(int)branch] = next;
            Changed?.Invoke();
            return Done(price, "Установлено: " + title + " (−" + Money(price) + ")");
        }

        /// <summary>§10.3.5: the owner moves an old StartAtMax slot to the progression: the van starts at tier 0 of every
        /// branch; money, items and bases are not touched; the old profile is remembered in the history.</summary>
        public bool SwitchToProgression()
        {
            if (!VanLegacyDebugProfile) return false;
            VanLegacyDebugProfile = false;
            for (int i = 0; i < BranchCount; i++) vanTiers[i] = 0;
            Fund.Note("system", "Слот переведён на прогрессию бусика (был отладочный максимум StartAtMax)", "progression:switch:" + Fund.Seq);
            Changed?.Invoke();
            return true;
        }

        // ---------- story / workshop flags ----------

        public void SetWorkshopUnlocked(bool value)
        {
            if (WorkshopUnlocked == value) return;
            WorkshopUnlocked = value;
            Changed?.Invoke();
        }

        public void SetFirstOrganBuyerMet(bool value)
        {
            if (FirstOrganBuyerMet == value) return;
            FirstOrganBuyerMet = value;
            Changed?.Invoke();
        }

        // ---------- property (§7.1) ----------

        public PurchaseResult TryBuyProperty(string baseId, int expectedPrice)
        {
            PropertyOffer offer = EconomyPrices.FindProperty(baseId);
            if (offer == null) return Fail(PurchaseError.InvalidRequest);
            if (ownedBases.Contains(baseId))
                return Fund.IsCommitted(PropertyKey(baseId)) ? Replay(offer.Price, "Уже куплено: " + offer.Title) : Fail(PurchaseError.AlreadyOwned);
            if (!offer.Purchasable) return Fail(PurchaseError.NotForSale);
            if (offer.Price <= 0) return Fail(PurchaseError.ItemUnavailable);
            if (!FirstOrganBuyerMet) return Fail(PurchaseError.StoryLocked);
            if (expectedPrice != offer.Price) return Fail(PurchaseError.PriceChanged, offer.Price);
            FundResult paid = Fund.TryCharge(offer.Price, "property", "Недвижимость: " + offer.Title, PropertyKey(baseId));
            if (paid.Status == FundStatus.Insufficient) return Fail(PurchaseError.InsufficientFunds, offer.Price);
            if (!paid.Ok) return Fail(PurchaseError.InvalidRequest, offer.Price);
            ownedBases.Add(baseId);
            Changed?.Invoke();
            return Done(offer.Price, "Куплено: " + offer.Title + " (−" + Money(offer.Price) + "). Помещение пустое — оборудование заказывается отдельно");
        }

        // ---------- equipment and delivery (§4, §4.1) ----------

        public PurchaseResult TryOrderEquipment(string itemId, string baseId, int expectedPrice, string requestKey)
        {
            if (string.IsNullOrEmpty(requestKey)) return Fail(PurchaseError.InvalidRequest);
            DeliveryOrder existing = deliveries.Find(d => d.key == requestKey);
            if (existing != null)
            {
                PurchaseResult again = Replay(existing.price, "Заказ уже оформлен");
                again.DeliveryId = existing.id;
                return again;
            }
            EquipmentOffer item = EconomyPrices.FindEquipment(itemId);
            if (item == null) return Fail(PurchaseError.UnknownItem);
            int requiredLevel = EconomyOffersV02.RequiredLevel(item);
            if (Level < requiredLevel)
            {
                PurchaseResult locked = Fail(PurchaseError.LevelLocked, item.Price);
                locked.Message = "Требуется уровень команды " + requiredLevel + " (сейчас " + Level + ")";
                return locked;
            }
            if (!item.Available || item.Price <= 0 || double.IsNaN(EconomyPrices.DeliveryGameHours))
            {
                PurchaseResult unavailable = Fail(PurchaseError.ItemUnavailable, item.Price);
                if (!string.IsNullOrEmpty(item.UnavailableReason)) unavailable.Message = item.UnavailableReason;
                return unavailable;
            }
            PropertyOffer place = EconomyPrices.FindProperty(baseId);
            if (place == null || !ownedBases.Contains(baseId)) return Fail(PurchaseError.BaseNotOwned);
            if (!place.AcceptsDeliveries) return Fail(PurchaseError.BaseNoDelivery);
            if (expectedPrice != item.Price) return Fail(PurchaseError.PriceChanged, item.Price);
            FundResult paid = Fund.TryCharge(item.Price, "equipment", "Заказ: " + item.Title + " → " + place.Title, EquipmentKey(requestKey));
            if (paid.Status == FundStatus.Insufficient) return Fail(PurchaseError.InsufficientFunds, item.Price);
            if (!paid.Ok) return Fail(PurchaseError.InvalidRequest, item.Price);
            var order = new DeliveryOrder
            {
                id = DeliveryIdPrefix + (++deliverySeq).ToString("D4"), key = requestKey, itemId = item.Id, baseId = baseId,
                price = item.Price, orderedAt = worldHours, dueAt = worldHours + EconomyPrices.DeliveryGameHours,
                State = DeliveryState.Pending,
            };
            deliveries.Add(order);
            Changed?.Invoke();
            PurchaseResult ok = Done(item.Price, "Заказано: " + item.Title + " → " + place.Title + ". Ящик через 1 игровой час");
            ok.DeliveryId = order.id;
            return ok;
        }

        /// <summary>The world game clock (§10.2: it only runs while the world is open). Negative steps are ignored.</summary>
        public void AdvanceWorldTime(double hours)
        {
            if (!(hours > 0) || double.IsInfinity(hours)) return;
            worldHours += hours;
            Fund.Now = worldHours;
        }

        /// <summary>The sky clock's hour this frame: a fall by more than 12 h is midnight (the next day). No Changed event (it
        /// runs every frame); the value is saved with the next commit / autosave.</summary>
        public void ObserveClock(double hour)
        {
            if (double.IsNaN(hour) || double.IsInfinity(hour)) return;
            hour %= 24.0;
            if (hour < 0) hour += 24.0;
            if (timeOfDay >= 0 && hour < timeOfDay - 12.0) worldDay++;
            timeOfDay = hour;
        }

        /// <summary>No sky clock in the scene: the calendar runs on the same active-world hours as deliveries.</summary>
        public void AdvanceCalendar(double hours)
        {
            if (!(hours > 0) || double.IsInfinity(hours)) return;
            double t = Math.Max(0.0, timeOfDay) + hours;
            while (t >= 24.0) { t -= 24.0; worldDay++; }
            timeOfDay = t;
        }

        /// <summary>DEV aid only (refused by a release server): the next calendar day at this hour.</summary>
        public void DevJumpToNextDay(double hour)
        {
            worldDay++;
            timeOfDay = Math.Max(0.0, Math.Min(23.99, hour));
            Changed?.Invoke();
        }

        /// <summary>Orders whose hour has passed and that have no crate in the world yet (Pending or Waiting).</summary>
        public List<DeliveryOrder> DueDeliveries()
        {
            var due = new List<DeliveryOrder>();
            foreach (DeliveryOrder d in deliveries)
                if ((d.State == DeliveryState.Pending || d.State == DeliveryState.Waiting) && worldHours >= d.dueAt) due.Add(d);
            return due;
        }

        public DeliveryOrder FindDelivery(string id) => deliveries.Find(d => d.id == id);

        public bool MarkWaiting(string id)
        {
            DeliveryOrder d = FindDelivery(id);
            if (d == null || d.State != DeliveryState.Pending) return false;
            d.State = DeliveryState.Waiting;
            Changed?.Invoke();
            return true;
        }

        public bool MarkArrived(string id, int slot, float x, float y, float z, float yaw)
        {
            DeliveryOrder d = FindDelivery(id);
            if (d == null || (d.State != DeliveryState.Pending && d.State != DeliveryState.Waiting) || worldHours < d.dueAt) return false;
            d.State = DeliveryState.Arrived;
            d.anchorSlot = slot;
            d.x = x; d.y = y; d.z = z; d.yaw = yaw;
            Changed?.Invoke();
            return true;
        }

        public bool MarkOpened(string id, float x, float y, float z, float yaw)
        {
            DeliveryOrder d = FindDelivery(id);
            if (d == null || d.State != DeliveryState.Arrived) return false;
            d.State = DeliveryState.Opened;
            d.anchorSlot = -1;
            d.x = x; d.y = y; d.z = z; d.yaw = yaw;
            Changed?.Invoke();
            return true;
        }

        /// <summary>Dev aid: the next pending orders are due right now (the hour is skipped, nothing is paid again).</summary>
        public int DevMakeDeliveriesDue()
        {
            int n = 0;
            foreach (DeliveryOrder d in deliveries)
                if (d.State == DeliveryState.Pending && d.dueAt > worldHours) { d.dueAt = worldHours; n++; }
            if (n > 0) Changed?.Invoke();
            return n;
        }

        // ---------- income (sales, rewards) ----------

        /// <summary>A sale or reward paid once into the fund, whatever the team size (§3.1).</summary>
        public FundResult Credit(int amount, string kind, string title, string key)
        {
            FundResult r = Fund.Credit(amount, kind, title, key);
            if (r.Status == FundStatus.Committed) Changed?.Invoke();
            return r;
        }

        /// <summary>A sale paid once into the fund TOGETHER with a flat XP amount (one line per present participant) under one
        /// transaction key: a replay (duplicate key) neither pays nor grants XP again; nothing is booked on a refusal.
        /// WP02: prefer the unit overload (EconomyProgress.cs), which computes the XP and the once-per-world bonuses itself;
        /// a "blood" grant here still marks the world's first blood as granted.</summary>
        public FundResult CommitSale(int amount, string kind, string title, string key, string xpCategory, int xpEach, IList<string> participants)
        {
            FundResult r = Fund.Credit(amount, kind, title, key);
            if (r.Status != FundStatus.Committed) return r;
            if (xpEach > 0 && participants != null)
                foreach (string who in participants)
                    if (!string.IsNullOrEmpty(who) && !xp.Exists(e => e.key == key && e.participant == who))
                        xp.Add(new XpEntry { key = key, participant = who, category = xpCategory ?? "", amount = xpEach, worldHours = worldHours });
            if (xpEach > 0 && xpCategory == XpCategoryBlood) FirstBloodGranted = true;
            Changed?.Invoke();
            return r;
        }

        public int XpOf(string participant, string category = null)
        {
            int total = 0;
            foreach (XpEntry e in xp) if (e.participant == participant && (category == null || e.category == category)) total += e.amount;
            return total;
        }

        public FundResult Charge(int amount, string kind, string title, string key)
        {
            FundResult r = Fund.TryCharge(amount, kind, title, key);
            if (r.Status == FundStatus.Committed) Changed?.Invoke();
            return r;
        }

        // ---------- story missions (STORY_MISSIONS_SPEC v01) ----------

        public struct StoryResult
        {
            public bool Ok;
            public bool Replayed;
            public string Message;
            public static StoryResult Done(string m) => new StoryResult { Ok = true, Message = m };
            public static StoryResult Again(string m) => new StoryResult { Ok = true, Replayed = true, Message = m };
            public static StoryResult No(string m) => new StoryResult { Ok = false, Message = m };
        }

        /// <summary>Reconciles facts the world already proves (spec §2.1). teamVanInWorld: this build places the team van at
        /// base 2, drivable from the start (M03/M04 content not implemented), so van ownership and the intro repair are
        /// recorded as build-provided facts and C01's organ referral (the M04 outcome) follows once. tutorialSaleCommitted:
        /// the saved C01 syringe-sale record already holds a committed sale (M01). Idempotent; Changed only for new facts.</summary>
        public bool ReconcileStory(bool teamVanInWorld, bool tutorialSaleCommitted)
        {
            bool changed = false;
            if (teamVanInWorld)
            {
                changed |= Story.AddFact(StoryFacts.VanOwned, StoryFacts.SourceBuildProvided, worldHours);
                changed |= Story.AddFact(StoryFacts.IntroRepairComplete, StoryFacts.SourceBuildProvided, worldHours);
            }
            if (tutorialSaleCommitted && Story.AddFact(StoryFacts.TutorialSale, "saved C01 sale record", worldHours))
            {
                Story.MarkObjective(MissionId.M01, "sale");
                changed = true;
            }
            if (Story.HasFact(StoryFacts.VanOwned) && Story.HasFact(StoryFacts.IntroRepairComplete) &&
                Story.AddFact(StoryFacts.OrganContact, "C01 referral after the van repair", worldHours))
            {
                Story.PostMessage("c01.organ_referral", "C01", "C01: «Раз у вас есть колёса — есть человек, который берёт органы. Скажи, что от меня.» (контора — заглушка: ящик у сарая базы 2)", worldHours);
                changed = true;
            }
            if (Story.StateOf(MissionId.M06) == JournalState.Offered)
                changed |= Story.PostMessage("m06.available", "Механик", "В мастерской к северу от Стройки, у дороги к неблагополучному району, работает механик — говорят, ему нужна помощь. Загляни к нему.", worldHours);
            if (changed) Changed?.Invoke();
            return changed;
        }

        /// <summary>M01 outcome: the team's first committed C01 syringe sale (called in the same frame as that sale's commit).</summary>
        public bool CommitTutorialSale(string source)
        {
            if (!Story.AddFact(StoryFacts.TutorialSale, source, worldHours)) return false;
            Story.MarkObjective(MissionId.M01, "sale");
            Story.PostMessage("m01.receipt", "C01", "C01: «Спасибо. Будет ещё — приноси, повторно плачу $8.» (аптека и пакеты — on hold)", worldHours);
            Changed?.Invoke();
            return true;
        }

        /// <summary>M05: the authoritative first acquaintance with the first organ buyer (a real interaction at his trade
        /// surface, or his first committed purchase). Opens the property catalogue (FirstOrganBuyerMet) and leaves the
        /// mechanic referral, all once. Locked until C01's organ referral exists; a debug toggle never calls this.</summary>
        public StoryResult CommitFirstOrganBuyerAcquaintance(string source)
        {
            if (Story.HasFact(StoryFacts.FirstOrganBuyerMet)) return StoryResult.Again("Вы уже знакомы со скупщиком");
            if (Story.StateOf(MissionId.M05) == JournalState.Locked)
                return StoryResult.No("Скупщик: «Я тебя не знаю.» (нужна рекомендация C01 после ремонта бусика)");
            Story.AddFact(StoryFacts.FirstOrganBuyerMet, source, worldHours);
            Story.MarkObjective(MissionId.M05, "meet");
            FirstOrganBuyerMet = true;
            Story.AddFact(StoryFacts.MechanicReferral, "first organ buyer", worldHours);
            Story.PostMessage("m05.trade", "Скупщик органов", "Скупщик: «Беру почки и печень. Цена — по качеству, холод помогает, торг — по уважению.»", worldHours);
            Story.PostMessage("m05.properties", "Скупщик органов", "Скупщик: «Захотите место побольше — смотрите помещения: Rough, Downtown, лаборатория.» (Телефон → Магазин → Недвиж.)", worldHours);
            Story.PostMessage("m05.mechanic", "Скупщик органов", "Скупщик: «Бусик подтянуть — к механику в мастерскую к северу от Стройки, у дороги. Только у него сейчас проблемы с конкурентом.»", worldHours);
            Changed?.Invoke();
            return StoryResult.Done("Знакомство со скупщиком: открыт каталог недвижимости, есть наводка на механика");
        }

        /// <summary>M06 accepted at the mechanic (any participant, after van acquisition; the M05 referral is guidance only).</summary>
        public StoryResult AcceptMechanicTask()
        {
            JournalState s = Story.StateOf(MissionId.M06);
            if (s == JournalState.Completed) return StoryResult.Again("Механик: «Мастерская открыта — заезжай в ремонтную зону.»");
            if (s == JournalState.Active) return StoryResult.Again("Механик: «Привези его живым и связанным — руки и ноги.»");
            if (s == JournalState.Locked) return StoryResult.No("Механик: «Без машины мне тебе предложить нечего.»");
            Story.Accept(MissionId.M06);
            Story.MarkObjective(MissionId.M06, "accept");
            Story.PostMessage("m06.task", "Механик", "Механик: «Мой навес на Стройке занял конкурент — работает там с 08:00 до 18:00. Привези его живым, руки и ноги связаны, в западный бокс мастерской (жёлтая разметка на полу). Тогда открою мастерскую.»", worldHours);
            Changed?.Invoke();
            return StoryResult.Done("Поручение механика принято");
        }

        /// <summary>M06 hand-in, validated against the CURRENT target generation: success completes M06, resolves the target
        /// (out of circulation; committed before any presentation) and sets WorkshopUnlocked once. No cash, XP or upgrade.
        /// A second confirmation after success answers with the same outcome (one handover).</summary>
        public StoryResult CompleteRivalHandIn(RivalHandInCheck check)
        {
            HandInRefusal why = RivalRules.Validate(Story, check);
            if (why == HandInRefusal.AlreadyDone) return StoryResult.Again(RivalRules.Explain(why));
            if (why != HandInRefusal.None) return StoryResult.No(RivalRules.Explain(why));
            Story.AddFact(StoryFacts.RivalDelivered, "hand-in " + check.PersonId, worldHours);
            Story.CommitReceipt("m06:handover:" + check.PersonId);
            foreach (ObjectiveDef o in StoryMissions.Get(MissionId.M06).Objectives) Story.MarkObjective(MissionId.M06, o.Id);
            Story.MarkRivalResolved();
            WorkshopUnlocked = true;
            Story.PostMessage("m06.done", "Механик", "Механик: «Вот это разговор. Дальше я сам. Мастерская открыта — заезжай в ремонтную зону и ставь на ручник.»", worldHours);
            Changed?.Invoke();
            return StoryResult.Done("Конкурент сдан: мастерская открыта");
        }

        /// <summary>Authoritative death / genuine loss of the current M06 target before the hand-in: recovery starts once.</summary>
        public bool ReportRivalLost(string personId, string reason)
        {
            if (!Story.MarkRivalLost(personId, AbsoluteHours, reason)) return false;
            Story.PostMessage("m06.recovery.g" + Story.Rival.generation, "Механик", "Механик: «Слышал, с ним беда (" + reason + "). Ничего — на навес завтра утром придёт другой.»", worldHours);
            Changed?.Invoke();
            return true;
        }

        /// <summary>Story clock work (server, called periodically): the M06 replacement generation when it is due.</summary>
        public bool TickStory()
        {
            if (!Story.TryAdvanceRivalGeneration(AbsoluteHours)) return false;
            Story.PostMessage("m06.replacement.g" + Story.Rival.generation, "Механик", "Механик: «На навесе новый тип, работает до 18:00. Мне подойдёт и он.»", worldHours);
            Changed?.Invoke();
            return true;
        }

        // ---------- save / snapshot ----------

        public EconomySaveData ToSave()
        {
            var data = new EconomySaveData
            {
                blockVersion = BlockVersion,
                migrationSource = MigrationSource,
                vanEngine = vanTiers[(int)VanBranch.Engine],
                vanHandling = vanTiers[(int)VanBranch.Handling],
                vanBrakes = vanTiers[(int)VanBranch.Brakes],
                vanLegacyDebugProfile = VanLegacyDebugProfile,
                workshopUnlocked = WorkshopUnlocked,
                firstOrganBuyerMet = FirstOrganBuyerMet,
                ownedBases = new List<string>(ownedBases),
                deliverySeq = deliverySeq,
                worldHours = worldHours,
                worldDay = worldDay,
                timeOfDay = timeOfDay,
                story = Story.ToSave(),
            };
            foreach (DeliveryOrder d in deliveries) data.deliveries.Add(d.Copy());
            foreach (XpEntry e in xp) data.xp.Add(new XpEntry { key = e.key, participant = e.participant, category = e.category, amount = e.amount, worldHours = e.worldHours });
            WriteProgress(data);
            WriteVanCargo(data);
            Fund.WriteTo(data);
            return data;
        }

        /// <summary>Restores a saved block exactly; tiers are clamped to 0..III (a load never stacks anything on top).</summary>
        public static EconomyState FromSave(EconomySaveData data)
        {
            var s = new EconomyState
            {
                Fund = FundLedger.ReadFrom(data),
                MigrationSource = string.IsNullOrEmpty(data.migrationSource) ? "saved" : data.migrationSource,
                VanLegacyDebugProfile = data.vanLegacyDebugProfile,
                WorkshopUnlocked = data.workshopUnlocked,
                FirstOrganBuyerMet = data.firstOrganBuyerMet,
                deliverySeq = Math.Max(0, data.deliverySeq),
                worldHours = Math.Max(0, data.worldHours),
                worldDay = Math.Max(0, data.worldDay),
                timeOfDay = data.timeOfDay >= 0 && data.timeOfDay < 24 ? data.timeOfDay : -1,
                Story = StoryState.FromSave(data.story),
            };
            if (data.xp != null)
                foreach (XpEntry e in data.xp)
                    if (e != null && !string.IsNullOrEmpty(e.key) && !s.xp.Exists(x => x.key == e.key && x.participant == e.participant)) s.xp.Add(e);
            s.ReadProgress(data);
            s.ReadVanCargo(data);
            s.vanTiers[(int)VanBranch.Engine] = Clamp(data.vanEngine);
            s.vanTiers[(int)VanBranch.Handling] = Clamp(data.vanHandling);
            s.vanTiers[(int)VanBranch.Brakes] = Clamp(data.vanBrakes);
            if (data.ownedBases != null)
                foreach (string b in data.ownedBases)
                    if (!string.IsNullOrEmpty(b) && !s.ownedBases.Contains(b)) s.ownedBases.Add(b);
            if (!s.ownedBases.Contains(EconomyPrices.BaseWagon)) s.ownedBases.Insert(0, EconomyPrices.BaseWagon);
            if (!s.ownedBases.Contains(EconomyPrices.BaseHamlet)) s.ownedBases.Insert(1, EconomyPrices.BaseHamlet);
            if (data.deliveries != null)
                foreach (DeliveryOrder d in data.deliveries)
                    if (d != null && !string.IsNullOrEmpty(d.id) && s.deliveries.Find(x => x.id == d.id) == null)
                    {
                        DeliveryOrder restored = d.Copy();
                        restored.itemId = EconomyOffersV02.ResolveSavedId(restored.itemId);
                        s.deliveries.Add(restored);
                        // A save whose counter lags its own orders (hand-edited / partly written) must never mint an id twice.
                        if (d.id.StartsWith(DeliveryIdPrefix, StringComparison.Ordinal) &&
                            long.TryParse(d.id.Substring(DeliveryIdPrefix.Length), out long n) && n > s.deliverySeq) s.deliverySeq = n;
                    }
            s.Fund.Now = s.worldHours;
            return s;
        }

        internal void MarkMigrated(string source, bool legacyVanProfile)
        {
            MigrationSource = source;
            VanLegacyDebugProfile = legacyVanProfile;
        }

        public EconomySnapshot ToSnapshot(int recentLines, bool ready)
        {
            var s = new EconomySnapshot
            {
                ready = ready,
                balance = Fund.Balance,
                seq = Fund.Seq,
                recent = Fund.Recent(recentLines),
                vanEngine = vanTiers[(int)VanBranch.Engine],
                vanHandling = vanTiers[(int)VanBranch.Handling],
                vanBrakes = vanTiers[(int)VanBranch.Brakes],
                vanLegacyDebugProfile = VanLegacyDebugProfile,
                workshopUnlocked = WorkshopUnlocked,
                firstOrganBuyerMet = FirstOrganBuyerMet,
                ownedBases = new List<string>(ownedBases),
                worldHours = worldHours,
                worldDay = worldDay,
                timeOfDay = timeOfDay,
                journal = Story.ToJournal(30),
            };
            foreach (DeliveryOrder d in deliveries) s.deliveries.Add(d.Copy());
            var seen = new List<string>();
            foreach (XpEntry e in xp)
                if (!seen.Contains(e.participant)) { seen.Add(e.participant); s.xp.Add(new XpTotal { participant = e.participant, total = XpOf(e.participant) }); }
            SnapshotProgress(s);
            SnapshotVanCargo(s);
            return s;
        }

        private static int Clamp(int tier) => Math.Max(0, Math.Min(EconomyPrices.VanMaxTier, tier));

        private PurchaseResult Fail(PurchaseError error, int price = 0) =>
            new PurchaseResult { Ok = false, Error = error, Price = price, Balance = Fund.Balance, Message = PurchaseResult.Explain(error) };

        private PurchaseResult Done(int price, string message) =>
            new PurchaseResult { Ok = true, Price = price, Balance = Fund.Balance, Message = message };

        private PurchaseResult Replay(int price, string message) =>
            new PurchaseResult { Ok = true, Replayed = true, Price = price, Balance = Fund.Balance, Message = message };

        public static string Money(int amount) => "$" + amount.ToString("N0", System.Globalization.CultureInfo.InvariantCulture);
    }
}
