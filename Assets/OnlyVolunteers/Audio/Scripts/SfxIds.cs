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

        // Vehicle beds and actions (VehicleEngineAudio)
        public const string VanEngineIdle = "van_engine_idle";
        public const string VanEngineLow = "van_engine_low";
        public const string VanEngineHigh = "van_engine_high";
        public const string VanDriveDirt = "van_drive_dirt";
        public const string VanDriveGrass = "van_drive_grass";
        public const string VanBodyRattle = "van_body_rattle";
        public const string VanEngineStart = "van_engine_start";
        public const string VanEngineStop = "van_engine_stop";
        public const string VanHandbrake = "van_handbrake";
        public const string PoliceEngineIdle = "police_engine_idle";
        public const string PoliceEngineLow = "police_engine_low";
        public const string PoliceEngineHigh = "police_engine_high";
        public const string PoliceEngineStart = "police_engine_start";
        public const string VanTireSkid = "van_tire_skid";
        public const string VanTireChirp = "van_tire_chirp";
        public const string VanBrakeSqueak = "van_brake_squeak";

        // Vehicle collisions (VehicleImpactAudio)
        public const string VanHitMetalLight = "van_hit_metal_light";
        public const string VanHitMetalHeavy = "van_hit_metal_heavy";
        public const string VanHitWood = "van_hit_wood";
        public const string VanHitConcrete = "van_hit_concrete";
        public const string VanHitPlastic = "van_hit_plastic";
        public const string VanHitGlass = "van_hit_glass";
        public const string VanHitFoliage = "van_hit_foliage";

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

        // Police: the siren loop (PoliceUnit plays Clips[0] on its own looping AudioSource)
        public const string PoliceSiren = "police_siren";

        // In the library, not hooked to anything yet
        public const string NpcGasp = "npc_gasp";
        public const string NpcHurt = "npc_hurt";
        public const string PoliceWhistle = "police_whistle";
        public const string VanHorn = "van_horn";
        public const string PhoneBuzz = "phone_buzz";
        public const string CashRegister = "cash_register";
        public const string UiPickup = "ui_pickup";
        public const string UiError = "ui_error";

        // Operation table: OperationSfx plays these when the library has clips, its own synth otherwise.
        // CoolerLid and Heartbeat have clips but no OperationCue yet.
        public const string OperationStrap = "operation_strap";
        public const string OperationTick = "operation_tick";
        public const string OperationSlit = "operation_slit";
        public const string OperationYelp = "operation_yelp";
        public const string OperationBoing = "operation_boing";
        public const string OperationPop = "operation_pop";
        public const string OperationRip = "operation_rip";
        public const string OperationTape = "operation_tape";
        public const string OperationCoolerLid = "operation_cooler_lid";
        public const string OperationHeartbeat = "operation_heartbeat";

        // Surface skids and water set (water gameplay hooks are added later).
        public const string VanSkidGravel = "van_skid_gravel";
        public const string VanSkidGrass = "van_skid_grass";
        public const string VanSkidSand = "van_skid_sand";
        public const string VanSkidMud = "van_skid_mud";
        public const string VanGravelSpray = "van_gravel_spray";
        public const string StepWater = "step_water";
        public const string StepWaterRun = "step_water_run";
        public const string WaterWade = "water_wade";
        public const string AmbStream = "amb_stream";
        public const string AmbRiver = "amb_river";
        public const string AmbWaterfall = "amb_waterfall";
        public const string AmbLakeShore = "amb_lake_shore";
        public const string SplashSmall = "splash_small";
        public const string SplashBig = "splash_big";
        public const string WaterJumpIn = "water_jump_in";
        public const string WaterGetOut = "water_get_out";
        public const string WaterDrip = "water_drip";
        public const string SwimStroke = "swim_stroke";
        public const string SwimLoop = "swim_loop";
        public const string VanWaterEnter = "van_water_enter";
        public const string VanWaterDrive = "van_water_drive";
        public const string VanPuddle = "van_puddle";
    }
}
