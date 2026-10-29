using System;

namespace OnlyVolunteers.Story
{
    public enum RivalPlace { Canopy, OffShift }

    /// <summary>What the server measured at the moment of an M06 hand-in (spec §9: PersonId / generation, alive, both ties
    /// from capture data, inside the western receiving zone, a valid interacting participant, nobody else moving him).</summary>
    public struct RivalHandInCheck
    {
        public bool ActorValid;
        public bool TargetFound;
        public string PersonId;
        public bool Alive;
        public bool HandsTied;
        public bool FeetTied;
        public bool InZone;
        public bool InVan;
        public bool Held;
        public bool OnTable;
    }

    public enum HandInRefusal
    {
        None, ActorInvalid, NotAccepted, AlreadyDone, NoTarget, WrongPerson, Dead, HandsFree, FeetFree, NotInZone, InVan, Held, OnTable,
    }

    /// <summary>Pure M06 rules: the 08:00-18:00 canopy shift, the next-morning replacement time and hand-in validation.</summary>
    public static class RivalRules
    {
        public const double ShiftStart = 8, ShiftEnd = 18, ReplacementMorning = 6;

        public static double HourOfDay(double absoluteHours)
        {
            double h = absoluteHours % 24.0;
            return h < 0 ? h + 24.0 : h;
        }

        public static bool OnShift(double hourOfDay) => hourOfDay >= ShiftStart && hourOfDay < ShiftEnd;
        public static RivalPlace PlaceAt(double hourOfDay) => OnShift(hourOfDay) ? RivalPlace.Canopy : RivalPlace.OffShift;

        /// <summary>The next 06:00 strictly after the loss (absolute world hours).</summary>
        public static double NextMorning(double absoluteHours)
        {
            double day = Math.Floor(absoluteHours / 24.0);
            double morning = day * 24.0 + ReplacementMorning;
            return morning > absoluteHours ? morning : morning + 24.0;
        }

        /// <summary>The routine may move the rival only while he is free on his feet: capture, transport, sleep, death and
        /// resolved custody always win over the clock (a shift change never teleports a captive or makes a second rival).</summary>
        public static bool RoutineMayMove(bool free, bool fleeing, bool captured, bool alive, bool resolved) =>
            free && !fleeing && !captured && alive && !resolved;

        public static HandInRefusal Validate(StoryState story, RivalHandInCheck c)
        {
            if (story == null) return HandInRefusal.NotAccepted;
            if (story.HasFact(StoryFacts.RivalDelivered)) return HandInRefusal.AlreadyDone;
            if (!c.ActorValid) return HandInRefusal.ActorInvalid;
            if (story.StateOf(MissionId.M06) != JournalState.Active) return HandInRefusal.NotAccepted;
            if (!c.TargetFound) return HandInRefusal.NoTarget;
            if (c.PersonId != story.RivalPersonId || story.Rival.Life != RivalLife.AtLarge) return HandInRefusal.WrongPerson;
            if (!c.Alive) return HandInRefusal.Dead;
            if (c.OnTable) return HandInRefusal.OnTable;
            if (c.InVan) return HandInRefusal.InVan;
            if (!c.InZone) return HandInRefusal.NotInZone;
            if (!c.HandsTied) return HandInRefusal.HandsFree;
            if (!c.FeetTied) return HandInRefusal.FeetFree;
            if (c.Held) return HandInRefusal.Held;
            return HandInRefusal.None;
        }

        public static string Explain(HandInRefusal r)
        {
            switch (r)
            {
                case HandInRefusal.None: return "";
                case HandInRefusal.ActorInvalid: return "Подойди к механику сам";
                case HandInRefusal.NotAccepted: return "Сначала возьми поручение у механика";
                case HandInRefusal.AlreadyDone: return "Конкурент уже сдан — мастерская открыта";
                case HandInRefusal.NoTarget: return "В зоне приёма нет конкурента";
                case HandInRefusal.WrongPerson: return "Механик: «Это не он. Мне нужен тот, кто занял мой навес»";
                case HandInRefusal.Dead: return "Механик: «Мёртвый мне не нужен — живым и связанным»";
                case HandInRefusal.HandsFree: return "Механик: «Свяжи ему руки»";
                case HandInRefusal.FeetFree: return "Механик: «Свяжи ему ноги»";
                case HandInRefusal.NotInZone: return "Положи его в зону приёма в западном боксе мастерской (жёлтая разметка)";
                case HandInRefusal.InVan: return "Выгрузи его из бусика в зону приёма";
                case HandInRefusal.OnTable: return "Он на операционном столе";
                case HandInRefusal.Held: return "Отпусти его — пусть лежит в зоне приёма";
                default: return "Нельзя";
            }
        }
    }
}
