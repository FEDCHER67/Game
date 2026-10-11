using System;

namespace OnlyVolunteers.Characters.Npc
{
    /// <summary>Whose run an NPC runs (the Run state's Gait blend): a civilian's panic run, a police officer's, a fat one's.</summary>
    public enum NpcGait : byte { Civilian, Police, PoliceFat }

    /// <summary>The contract's one-shot clips (Animator triggers). Each plays the clip of its role (NpcAnimContract.RoleOf).</summary>
    public enum NpcAnimTrigger : byte { KnockOnWall, HitFront, HitBack, HitHead, Stagger, Beat, ShakeFist, Trip }

    // Stage 9 step 5 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §5.4): the NPC Animator contract in one place. NpcAnimDriver
    // writes it at runtime and the editor's NpcAnimatorBuilder builds SausageBuddy_Greybox.controller from it, so the two
    // always agree; Vadim's NPC uses the same controller (the same clips play on his rig, design §1.3).
    // Parameters (v1 of §5.4 plus Gait, Aim and Driven): Speed (m/s), SpeedMul (the locomotion clip's playback: speed / its
    // authored speed), Panic (fleeing; in a van: escaping), StunPhase (StunPhase: 0 None, 1 Out, 2 Groggy, 3 Awake),
    // Carried (held: the capsule's struggle layer), InCargo (sitting or escaping in a van), Activity (CrowdActivity, -1 none),
    // Ragdoll (the body is physical; the Animator is off then), GetUp (the GetUpKind playing: 1 back, 2 belly, 3 sit-up in a
    // van, 4 jump-out of a van), Gait (NpcGait), Aim (a police officer aims: upper body), Driven (an NpcAnimDriver drives this
    // Animator; off, the controller only plays states asked for by name, as the player's Buddy and the locomotion preview do).
    // Triggers: the get-up kinds (GetUpBack, GetUpBelly, SitUp, JumpOut = GetUpKind 1-4; a puppet enters those states by
    // them, the NPC itself starts them at frame 0 with Play, NpcAnimDriver.PlayGetUp) and the one-shots (NpcAnimTrigger).
    // Roles: what clips.json calls each clip (Animations/clips.json "role"); activities are "<CrowdActivity>/Enter|Loop|Exit".
    public static class NpcAnimContract
    {
        public const string Speed = "Speed", SpeedMul = "SpeedMul", Panic = "Panic", StunPhase = "StunPhase", Carried = "Carried",
            InCargo = "InCargo", Activity = "Activity", Ragdoll = "Ragdoll", GetUp = "GetUp", Gait = "Gait", Aim = "Aim",
            Driven = "Driven";

        /// <summary>Trigger of each GetUpKind (index = the kind; None has none).</summary>
        public static readonly string[] GetUpTriggers = { null, "GetUpBack", "GetUpBelly", "SitUp", "JumpOut" };

        /// <summary>Trigger name of each NpcAnimTrigger (index = the enum).</summary>
        public static readonly string[] Triggers = { "KnockOnWall", "HitFront", "HitBack", "HitHead", "Stagger", "Beat", "ShakeFist", "Trip" };

        // Locomotion (m/s): moving from WalkFrom, running from RunFrom or when panicking (the controller and the driver's
        // SpeedMul use the same numbers).
        public const float WalkFrom = 0.15f, RunFrom = 2.5f;

        // States the code itself names (the rest are named after their clips by clips.json).
        public const string IdleState = "Idle", WalkState = "Walk", RunState = "Run", DownState = "Down", RagdollState = "Ragdoll",
            EscapeFallbackState = "Escape_Run", CargoFallbackState = "Cargo_Sit", EmptyState = "Empty";
        public const string UpperBodyLayer = "UpperBody", StruggleLayer = "Struggle";

        // Roles of clips.json.
        public const string RoleIdle = "Idle", RoleWalk = "Walk", RoleRun = "Run", RoleRunCop = "RunCop", RoleRunCopFat = "RunCopFat";
        public const string RoleGetUpBack = "GetUpBack", RoleGetUpBelly = "GetUpBelly", RoleSitUp = "SitUp", RoleSitIdle = "SitIdle",
            RoleKnock = "Knock", RoleScrambleStart = "ScrambleStart", RoleScramble = "Scramble", RoleJumpOut = "JumpOut";
        public const string RoleHitFront = "HitFront", RoleHitBack = "HitBack", RoleHitHead = "HitHead", RoleStagger = "Stagger",
            RolePunch = "Punch", RoleShakeFist = "ShakeFist", RoleTrip = "Trip", RoleStruggle = "Struggle", RoleAimRaise = "AimRaise",
            RoleAim = "Aim";
        public const string EnterPhase = "Enter", LoopPhase = "Loop", ExitPhase = "Exit";

        /// <summary>The role whose clip a one-shot trigger plays.</summary>
        public static string RoleOf(NpcAnimTrigger trigger) => trigger switch
        {
            NpcAnimTrigger.KnockOnWall => RoleKnock,
            NpcAnimTrigger.HitFront => RoleHitFront,
            NpcAnimTrigger.HitBack => RoleHitBack,
            NpcAnimTrigger.HitHead => RoleHitHead,
            NpcAnimTrigger.Stagger => RoleStagger,
            NpcAnimTrigger.Beat => RolePunch,
            NpcAnimTrigger.ShakeFist => RoleShakeFist,
            NpcAnimTrigger.Trip => RoleTrip,
            _ => throw new ArgumentOutOfRangeException(nameof(trigger)),
        };

        /// <summary>The role of a get-up kind's clip (None: null).</summary>
        public static string RoleOf(GetUpKind kind) => kind switch
        {
            GetUpKind.Back => RoleGetUpBack,
            GetUpKind.Belly => RoleGetUpBelly,
            GetUpKind.SitUp => RoleSitUp,
            GetUpKind.JumpOut => RoleJumpOut,
            _ => null,
        };

        /// <summary>The role of an activity's clip: "BenchSit/Loop".</summary>
        public static string ActivityRole(string activity, string phase) => activity + "/" + phase;
    }
}
