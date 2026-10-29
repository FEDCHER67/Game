using FishNet.Broadcast;

namespace OnlyVolunteers.Economy
{
    public enum EconomyRequestKind : byte
    {
        /// <summary>A client connected: send it the current snapshot. WP02: Arg = the client's persistent player GUID (its
        /// stable participant id for XP and personal ranks).</summary>
        Hello = 0,
        /// <summary>Arg = VanBranch number, Expected = the tier shown on the card.</summary>
        VanTier = 1,
        /// <summary>Arg = equipment id, Arg2 = base id, Expected = the price shown.</summary>
        Equipment = 2,
        /// <summary>Arg = base id, Expected = the price shown.</summary>
        Property = 3,
        /// <summary>Arg = PayMarket app name (the server knows its price).</summary>
        PhoneApp = 4,
        /// <summary>The host moves an old StartAtMax slot to the paid progression (§10.3.5).</summary>
        SwitchToProgression = 5,
        /// <summary>WP02: buy the next rank of a skill from the team's free XP. Arg = skill id (dosage / formula / bargain),
        /// Expected = the rank shown as next. A personal rank (bargain) goes to the requester's stable id.</summary>
        Skill = 6,
        // ---- story (STORY_MISSIONS_SPEC v01): the server measures actor, target and zone itself ----
        /// <summary>E at the mechanic: accept M06 (Offered) or try the rival hand-in (Active).</summary>
        StoryMechanic = 10,
        /// <summary>E at the first organ buyer's trade surface: the M05 acquaintance.</summary>
        StoryMeetOrganBuyer = 11,
        /// <summary>E at C01's placeholder: sell the blood in the held syringe. Arg = "0" take the empty syringe back (default),
        /// "1" leave it with the buyer.</summary>
        StoryC01Sale = 12,
        // ---- dev toggles: editor / development builds only, refused by a release server ----
        DevWorkshop = 20,
        DevOrganBuyer = 21,
        DevCredit = 22,
        DevDeliveriesDue = 23,
        DevWorkshopZoneAtVan = 24,
        /// <summary>DEV: +4 zip ties into the field kit (the pharmacy that sells them is on hold).</summary>
        DevGiveTies = 25,
        /// <summary>DEV: one NEW empty blood syringe into the host's hotbar (no authored daily-find anchor yet).</summary>
        DevGiveBloodSyringe = 26,
        /// <summary>DEV: the next morning 09:00 (calendar day + 1, sky clock set).</summary>
        DevNextMorning = 27,
    }

    /// <summary>Client → server: an intent (never an amount or a new balance, ECONOMY §10.1). Key = the request's id: the
    /// same key repeated answers with the first outcome.</summary>
    public struct EconomyRequestBroadcast : IBroadcast
    {
        public byte Kind;
        public string Key;
        public string Arg;
        public string Arg2;
        public int Expected;
    }

    /// <summary>Server → clients: the economy snapshot as JSON (EconomySnapshot), after every commit and on join.</summary>
    public struct EconomySnapshotBroadcast : IBroadcast
    {
        public string Json;
    }

    /// <summary>Server → the requester: the outcome of one request.</summary>
    public struct EconomyResultBroadcast : IBroadcast
    {
        public string Key;
        public bool Ok;
        public string Message;
    }
}
