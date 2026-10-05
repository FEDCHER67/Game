namespace OnlyVolunteers.Audio
{
    // Event ids of SfxLibrary. Gameplay code plays these; SfxLibraryImporter maps each to a file-name prefix
    // (docs/drafts/SFX_HOOKUP_DRAFT.md has the table). Plain constants: no string is built per call.
    public static class SfxIds
    {
        // Q hit, by zone (WeaponStun.HitZone)
        public const string HitHead = "hit_head";
        public const string HitTorso = "hit_torso";
        public const string HitLimb = "hit_limb";

        // A downed body landing
        public const string ThudGround = "thud_ground";
        public const string ThudVan = "thud_van_floor";

        // Van doors (VanDoor): front hinge pair, rear hinge pair, sliding door
        public const string DoorFrontOpen = "door_front_open";
        public const string DoorFrontClose = "door_front_close";
        public const string DoorFrontSlam = "door_front_slam";
        public const string DoorRearOpen = "door_rear_open";
        public const string DoorRearClose = "door_rear_close";
        public const string DoorRearSlam = "door_rear_slam";
        public const string DoorSlideOpen = "door_slide_open";
        public const string DoorSlideClose = "door_slide_close";

        // Footsteps of the first-person player, by surface (SfxSurfaces)
        public const string StepAsphalt = "step_asphalt";
        public const string StepGrass = "step_grass";
        public const string StepSand = "step_sand";
        public const string StepMetal = "step_metal";

        // NPC voice (GreyboxNpc)
        public const string NpcScream = "npc_scream";
        public const string NpcMumble = "npc_mumble";
        public const string NpcWhimper = "npc_whimper";

        // Items
        public const string OrganSquish = "organ_squish";

        // In the library, not hooked to anything yet
        public const string NpcGasp = "npc_gasp";
        public const string PoliceSiren = "police_siren";
        public const string PhoneBuzz = "phone_buzz";
        public const string CashRegister = "cash_register";
    }
}
