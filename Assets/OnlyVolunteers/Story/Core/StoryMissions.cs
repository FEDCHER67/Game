using System;

namespace OnlyVolunteers.Story
{
    /// <summary>The story chain M01-M13 (STORY_MISSIONS_SPEC_2026-10-28_v01 §3). M13 is four independent VIP orders.</summary>
    public enum MissionId { M01, M02, M03, M04, M05, M06, M07, M08, M09, M10, M11, M12, M13A, M13B, M13C, M13D }

    /// <summary>The four journal states shown to players. Waiting / ready-to-commit / recovering are objective substates
    /// (StoryJournalEntry.Substate), not extra states.</summary>
    public enum JournalState { Locked = 0, Offered = 1, Active = 2, Completed = 3 }

    /// <summary>How much of a mission exists in this build. Only Playable missions have runtime triggers.</summary>
    public enum ContentStatus { Playable = 0, FoundationOnly = 1, OnHold = 2 }

    /// <summary>Persistent world facts behind progression (spec §2.1, §17.1). A fact is committed once with its source;
    /// journal states are derived from facts, never from visible messages.</summary>
    public static class StoryFacts
    {
        public const string TutorialSale = "tutorial_sale";              // M01: the first committed C01 syringe sale
        public const string FirstBagSale = "first_bag_sale";             // M02
        public const string GrandpaLead = "grandpa_lead";                // M02 -> M03 (informational)
        public const string VanOwned = "van_owned";                      // M03
        public const string IntroRepairComplete = "intro_repair_complete"; // M04
        public const string OrganContact = "organ_contact";              // M04: C01's organ-buyer referral
        public const string FirstOrganBuyerMet = "first_organ_buyer_met"; // M05: authoritative acquaintance
        public const string MechanicReferral = "mechanic_referral";      // M05 (guidance only, not a gate for M06)
        public const string RivalDelivered = "m06_rival_delivered";      // M06
        public const string FirstBuyerMeetings3 = "first_buyer_meetings_3"; // M07
        public const string BodybuilderKidney = "bodybuilder_kidney";    // M08
        public const string CourierCase = "courier_case";                // M09 (medic contact)
        public const string MedicMeetings7 = "medic_meetings_7";         // M10 (mafioso contact)
        public const string MafiaFirstDrop = "mafia_first_drop";         // M11
        public const string StreamerOrder = "streamer_order";            // M12
        public const string LabOwned = "lab_owned";
        public const string VipBeastman = "vip_beastman", VipSpeedster = "vip_speedster", VipBlindfold = "vip_blindfold", VipAltgirl = "vip_altgirl";

        /// <summary>Source of a fact that the current build provides without its mission content (the team van is in the
        /// world and drivable from the start because M03/M04 are not implemented). Shown in the journal, never hidden.</summary>
        public const string SourceBuildProvided = "build-provided (mission content not implemented)";
    }

    public sealed class ObjectiveDef
    {
        public string Id;
        public string Text;
        public ObjectiveDef(string id, string text) { Id = id; Text = text; }
    }

    public sealed class MissionDef
    {
        public MissionId Id;
        public string Title = "";
        public string Giver = "";
        public ContentStatus Content;
        /// <summary>All of these facts are needed before the mission leaves Locked.</summary>
        public string[] Requires = Array.Empty<string>();
        /// <summary>True: Offered until a participant explicitly accepts (M06 at the mechanic); false: Active as soon as unlocked.</summary>
        public bool RequiresAcceptance;
        /// <summary>The fact whose commit completes the mission (early valid facts reconcile it, spec §2.1).</summary>
        public string Completes = "";
        public ObjectiveDef[] Objectives = Array.Empty<ObjectiveDef>();
        public string Note = "";
    }

    /// <summary>The mission chain as data (spec §3-§16). Only M05 (acquaintance commit) and M06 are Playable here; the rest
    /// expose their gates and facts so the journal, save and later content share one foundation.</summary>
    public static class StoryMissions
    {
        public const string OnHoldPharmacy = "on hold: аптека будет в городе, её сюжетная роль отложена (Федя 28.10)";

        public static readonly MissionDef[] All =
        {
            new MissionDef { Id = MissionId.M01, Title = "Первая кровь у вагона", Giver = "C01", Content = ContentStatus.FoundationOnly,
                Completes = StoryFacts.TutorialSale,
                Objectives = new[] { new ObjectiveDef("sign", "Найти табличку и номер C01"), new ObjectiveDef("syringe", "Найти пустой шприц крови"),
                    new ObjectiveDef("sale", "Продать C01 кровь в шприце") },
                Note = "Табличка, звонок и приезд C01 не реализованы; продажа C01 — заглушка у базы 2" },
            new MissionDef { Id = MissionId.M02, Title = "Аптека, пакеты и наводка на деда", Giver = "C01", Content = ContentStatus.OnHold,
                Requires = new[] { StoryFacts.TutorialSale }, Completes = StoryFacts.FirstBagSale,
                Objectives = new[] { new ObjectiveDef("pharmacy", "Купить пакет в аптеке — " + OnHoldPharmacy), new ObjectiveDef("bag_sale", "Продать C01 запечатанный пакет крови") },
                Note = OnHoldPharmacy },
            new MissionDef { Id = MissionId.M03, Title = "Бусик деда, хижина и сарай", Giver = "Дед", Content = ContentStatus.FoundationOnly,
                Completes = StoryFacts.VanOwned,
                Objectives = new[] { new ObjectiveDef("yard", "Дойти до двора деда"), new ObjectiveDef("van", "Купить бусик за $400 или забрать его") },
                Note = "Покупка/забор бусика не реализованы: в сборке бусик выдан сразу" },
            new MissionDef { Id = MissionId.M04, Title = "Вводный ремонт", Giver = "Дед / записка", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.VanOwned }, Completes = StoryFacts.IntroRepairComplete,
                Objectives = new[] { new ObjectiveDef("battery", "Поставить аккумулятор"), new ObjectiveDef("tyres", "Поставить две шины") },
                Note = "Ремонт не реализован: бусик в сборке уже на ходу" },
            new MissionDef { Id = MissionId.M05, Title = "Первый органный скупщик", Giver = "Скупщик органов", Content = ContentStatus.Playable,
                Requires = new[] { StoryFacts.OrganContact }, Completes = StoryFacts.FirstOrganBuyerMet,
                Objectives = new[] { new ObjectiveDef("meet", "Познакомиться со скупщиком (ящик у сарая базы 2 — заглушка конторы)") },
                Note = "Контора на Стройке и обзор трёх баз не реализованы; знакомство — у ящика скупщика" },
            new MissionDef { Id = MissionId.M06, Title = "Конкурент механика", Giver = "Механик", Content = ContentStatus.Playable,
                Requires = new[] { StoryFacts.VanOwned }, RequiresAcceptance = true, Completes = StoryFacts.RivalDelivered,
                Objectives = new[] { new ObjectiveDef("accept", "Поговорить с механиком у мастерской"),
                    new ObjectiveDef("find", "Найти конкурента у навеса на Стройке (08:00–18:00)"),
                    new ObjectiveDef("tie", "Связать ему руки и ноги"),
                    new ObjectiveDef("deliver", "Привезти живым в западную зону приёма мастерской и сдать (E у механика)") },
                Note = "Без денег, XP и бесплатных улучшений: открывается мастерская" },
            new MissionDef { Id = MissionId.M07, Title = "Три встречи со скупщиком", Giver = "Скупщик органов", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.FirstOrganBuyerMet }, Completes = StoryFacts.FirstBuyerMeetings3, Note = "Встречи со скупщиком не реализованы" },
            new MissionDef { Id = MissionId.M08, Title = "Почка качка из Хутора", Giver = "Скупщик органов", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.FirstBuyerMeetings3 }, RequiresAcceptance = true, Completes = StoryFacts.BodybuilderKidney, Note = "Спецзаказ не реализован" },
            new MissionDef { Id = MissionId.M09, Title = "Кейс в тайник медика", Giver = "Скупщик органов", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.BodybuilderKidney }, RequiresAcceptance = true, Completes = StoryFacts.CourierCase, Note = "Курьерский кейс не реализован" },
            new MissionDef { Id = MissionId.M10, Title = "Семь встреч с медиком", Giver = "Медик", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.CourierCase }, Completes = StoryFacts.MedicMeetings7, Note = "Медик не реализован" },
            new MissionDef { Id = MissionId.M11, Title = "Первая закладка мафиози", Giver = "Мафиози", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.MedicMeetings7 }, Completes = StoryFacts.MafiaFirstDrop, Note = "Тайники мафиози не реализованы" },
            new MissionDef { Id = MissionId.M12, Title = "Поздний заказ стримера (по желанию)", Giver = "Медик", Content = ContentStatus.FoundationOnly,
                Requires = new[] { StoryFacts.CourierCase }, RequiresAcceptance = true, Completes = StoryFacts.StreamerOrder, Note = "Заказ стримера не реализован" },
            Vip(MissionId.M13A, "VIP: сердце BEASTMAN", StoryFacts.VipBeastman),
            Vip(MissionId.M13B, "VIP: лёгкие SPEEDSTER", StoryFacts.VipSpeedster),
            Vip(MissionId.M13C, "VIP: глаза BLINDFOLD", StoryFacts.VipBlindfold),
            Vip(MissionId.M13D, "VIP: мозг ALTGIRL", StoryFacts.VipAltgirl),
        };

        private static MissionDef Vip(MissionId id, string title, string fact) => new MissionDef
        {
            Id = id, Title = title, Giver = "Мафиози", Content = ContentStatus.FoundationOnly,
            Requires = new[] { StoryFacts.LabOwned, StoryFacts.MafiaFirstDrop }, RequiresAcceptance = true, Completes = fact,
            Note = "VIP-заказы не реализованы",
        };

        public static MissionDef Get(MissionId id)
        {
            foreach (MissionDef m in All) if (m.Id == id) return m;
            throw new ArgumentOutOfRangeException(nameof(id));
        }

        public static bool TryParse(string text, out MissionId id) => Enum.TryParse(text, false, out id) && Enum.IsDefined(typeof(MissionId), id);

        public static string StateName(JournalState s) =>
            s == JournalState.Locked ? "Закрыто" : s == JournalState.Offered ? "Предложено" : s == JournalState.Active ? "Активно" : "Выполнено";

        public static string ContentName(ContentStatus c) =>
            c == ContentStatus.Playable ? "играбельно" : c == ContentStatus.OnHold ? "отложено" : "только основа (контент не реализован)";

    }
}
