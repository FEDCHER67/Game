using System;
using UnityEngine;

namespace OnlyVolunteers.Characters.Npc
{
    // One per rig (the Sausage Buddy now, Vadim's NPC later): the 11 ragdoll bodies of a Mixamo-named skeleton (design doc
    // docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §2). Parts are written by Editor/NpcRagdollBuilder from the rig's
    // sampled Idle pose (never from the prefab's stored pose: the Buddy v04 FBX keeps its Hips ~11.5 m below the root); the
    // settings below the parts are hand-tuned and survive a rebuild. Shapes and joint frames are in each bone's own frame
    // without its scale (the bone's rotation, metres, origin at the bone): the runtime divides by the bone's lossy scale
    // (100 on the Buddy). Masses are design values (28 kg in all, the stage-1 stunned mass), not measured.
    // The clip section (get-ups, the cargo sit-up, sit idle and knock; step 3) is written by
    // Map/Editor/GreyboxBuddySetup.InstallClips from SausageBuddy/Animations/clips.json. Step 4: the Groggy struggle
    // (NpcStruggle), the hop out of a standing van and the trip (NpcGetUp, NpcRagdoll.Stumble).
    [CreateAssetMenu(menuName = "VOLUNTEERS ONLY/NPC Ragdoll Profile")]
    public sealed class NpcRagdollProfile : ScriptableObject
    {
        public enum Kind : byte { Pelvis, Chest, Head, UpperArm, ForeArm, Thigh, Calf }
        public enum JointKind : byte { None, Hinge, Ball }
        // Grab handles (§3.4 A5): good = the stage-1 hand, medium = thighs, bad = pelvis and belly (one hand cannot lift them).
        public enum Handle : byte { Good, Medium, Bad }

        [Serializable]
        public sealed class Part
        {
            public string Name;
            public Kind Kind;
            [Tooltip("Arms and legs only; ignored for the pelvis, chest and head.")]
            public NpcSide Side;
            public string Bone;
            [Tooltip("Index of the parent part (its joint's connected body); -1 for the pelvis. Parents come first.")]
            public int Parent = -1;
            public float Mass;
            [Header("Capsule (bone frame, metres)")]
            public Vector3 Center;
            [Tooltip("The bone's axis the capsule lies along: 0 X, 1 Y, 2 Z.")]
            public int Direction = 1;
            public float Radius;
            [Tooltip("Tip to tip.")]
            public float Height;
            [Tooltip("Unit vector, bone frame: along the limb toward its end; the spine's up for the pelvis and chest.")]
            public Vector3 Up = Vector3.up;
            [Header("Box on a child bone (the foot), no body of its own")]
            public string BoxBone = "";
            public Vector3 BoxCenter;
            public Quaternion BoxRotation = Quaternion.identity;
            public Vector3 BoxSize;
            [Tooltip("The box's centre in the character frame of the Idle pose (where it lies along the frame's axes).")]
            public Vector3 BoxPoseCenter;
            [Header("Joint to the parent (this bone's frame)")]
            public JointKind Joint;
            [Tooltip("Hinge: the flexion axis (a positive turn about it, Unity's sense, is flexion). Ball: along the bone.")]
            public Vector3 Axis = Vector3.right;
            [Tooltip("Hinge: along the bone (twist). Ball: perpendicular to the bone.")]
            public Vector3 Secondary = Vector3.up;
            [Tooltip("Degrees from the joint's zero (Reference). Hinge: extension (-) .. flexion (+); ball: twist.")]
            public float LowX, HighX;
            [Tooltip("Hinge: twist and side bend, +-. Ball: the swing cone.")]
            public float LimitY, LimitZ;
            [Tooltip("The joint's zero: this bone's rotation relative to the parent part's bone (Idle; the shoulders: arms out).")]
            public Quaternion Reference = Quaternion.identity;
            [Header("Idle pose, character frame (root at the feet, facing +Z)")]
            public Vector3 PosePosition;
            public Quaternion PoseRotation = Quaternion.identity;
            [Header("Grab")]
            public Handle Handle;
            [Tooltip("Accusative, for \"ЛКМ — взять за ...\"; the chest and the foot have their own words (NpcRagdoll).")]
            public string Hint = "";
        }

        public Part[] Parts = Array.Empty<Part>();

        [Header("Bodies (§2.3)")]
        public float LinearDamping = 0.05f;
        public float AngularDamping = 0.6f;
        [Tooltip("m/s: no explosions when a body is born inside a wall or the van.")]
        public float MaxDepenetration = 3f;
        public float MaxAngularVelocity = 20f;
        public int SolverIterations = 12;
        public int SolverVelocityIterations = 4;
        [Tooltip("With the project's 0.005 a jointed chain is slow to sleep.")]
        public float SleepThreshold = 0.02f;
        [Tooltip("Arms and legs: inertia tensor times this (calmer flailing, fewer solver fights).")]
        public float LimbInertiaScale = 1.5f;
        [Tooltip("The stage-1 NpcBody material (combined by Average; honest only with Improved Patch Friction on).")]
        public float StaticFriction = 1f;
        public float DynamicFriction = 0.3f;

        [Header("Joints (§2.2)")]
        public float ProjectionDistance = 0.05f;
        public float ProjectionAngle = 10f;

        [Header("Grab handles (§3.4 A5): N per hand, x = up/down, y = sideways")]
        public Vector2 GoodForce = new(240f, 260f);
        public Vector2 MediumForce = new(200f, 220f);
        public Vector2 BadForce = new(150f, 200f);
        [Tooltip("Top share of the chest along the spine that is the collar band (good); the rest is the belly (bad).")]
        [Range(0f, 1f)] public float CollarBand = 0.4f;

        [Header("Hold (§3.2, assist A1)")]
        [Tooltip("Damp a hold with HoldMass instead of the held bone's own mass (a 1 kg forearm would let the hold bounce).")]
        public bool UseHoldMass = true;
        public float HoldMass = 14f;

        // Assists A2-A4 (design §3.4): each one switchable for A/B. Model-based starting values, tuned by Fedya's playtest.
        [Header("A2 force spreading")]
        [Tooltip("A hand on a limb or the head pushes only part of its force into that bone; the rest goes up the chain to " +
                 "the trunk, at the joints, so a 1 kg forearm does not stretch away from the shoulder under 240 N.")]
        public bool SpreadForce = true;
        [Tooltip("Share of the hand's force that goes to the parent chain (split evenly over the bones up to the trunk).")]
        [Range(0f, 0.9f)] public float SpreadShare = 0.4f;

        [Header("A3 held weight relief")]
        public bool WeightRelief = true;
        [Tooltip("While held, every body gets this share of its weight upward, by the number of holders (0, 1, 2, 3); gone " +
                 "the moment the last hand lets go (a dropped body falls at full g).")]
        public float[] Relief = { 0f, 0.20f, 0.35f, 0.45f };
        [Tooltip("Off: a hand on a bad handle (the pelvis, the belly) brings no relief, so one hand there still cannot lift " +
                 "the hips (A5; with relief it lifted them 0.21 m in the smoke test, 0.08 m without).")]
        public bool BadHandleRelief = false;

        [Header("A4 carry tone (joint drives while held)")]
        public bool CarryTone = true;
        [Tooltip("Any holder: the waist and the neck keep the trunk and the head roughly in line (Nm/rad, Nm, Nm·s/rad). " +
                 "The neck is driven only in flexion: the head still twists and flops sideways.")]
        public float HeldSpring = 60f;
        public float HeldMaxTorque = 40f;
        public float HeldDamper = 2f;
        [Tooltip("Two or more holders, one above the pelvis (head, chest, arms) and one below (legs): the trunk becomes a " +
                 "hammock with little sag. Arms and knees stay floppy.")]
        public float CarryWaistSpring = 400f;
        public float CarryHipSpring = 300f;
        public float CarryMaxTorque = 90f;
        public float CarryDamper = 20f;
        [Tooltip("Degrees of hip flexion the carried legs are held at (the carried pose: straight trunk, slight hip flexion).")]
        public float CarryHipFlexion = 10f;

        [Header("Going down (§4.2)")]
        [Tooltip("m/s: the animation's own bone motion carried into the bodies is clamped to this.")]
        public float BoneMotionMax = 6f;
        [Tooltip("m: bone motion is tracked only for NPCs this close to the player.")]
        public float TrackRadius = 30f;
        [Tooltip("rad/s: a vehicle knock spins the pelvis at most this fast (the limbs flail by themselves).")]
        public float KnockSpin = 3f;

        [Header("Waking: the blend from the lying pose to the clip (get-up, sit-up; §4.4 step 7)")]
        public float WakeBlend = 0.35f;
        [Tooltip("The neck and head arrive last.")]
        public float WakeBlendHead = 0.5f;
        [Tooltip("Lying on its belly in the cargo bay the sit-up (it starts on the back) blends this many times longer: the " +
                 "body rolls over during the blend.")]
        public float RollBlendScale = 1.8f;

        // One clip of the get-up and cargo sets: the Animator state that plays it and the numbers the code needs. Written
        // by GreyboxBuddySetup.InstallClips from SausageBuddy/Animations/clips.json (do not edit by hand).
        [Serializable]
        public sealed class ClipInfo
        {
            [Tooltip("Animator state (and clip) name; empty = not installed.")]
            public string State = "";
            public float Seconds;
            [Tooltip("The Hips bone's position at frame 0, in the clip's root space (§4.4 step 4).")]
            public Vector3 HipsStart;
            [Tooltip("Get-ups: share of the clip at which the feet are planted and the CharacterController comes on.")]
            [Range(0f, 1f)] public float Stable;
            [Tooltip("Seconds into the clip of its events (the knock: the three strikes on the wall).")]
            public float[] Events = Array.Empty<float>();
            [Tooltip("Step 5 (Roles): the clips.json role (NpcAnimContract), the ground speed the clip was authored for (m/s, " +
                     "locomotion: the driver plays it at speed / this; 0 = not a locomotion clip) and whether it loops.")]
            public string Role = "";
            public float Speed;
            public bool Loop;

            public bool Ready => !string.IsNullOrEmpty(State) && Seconds > 0f;
        }

        [Header("Clips (§4.4, §4.5): written by GreyboxBuddySetup.InstallClips from clips.json")]
        public ClipInfo GetUpBack = new();
        public ClipInfo GetUpBelly = new();
        public ClipInfo SitUp = new();
        public ClipInfo SitIdle = new();
        public ClipInfo Knock = new();
        [Tooltip("Step 4 hooks for the cloud animators' clips (§4.5, §5.1), not installed yet: a passenger running for the door " +
                 "loops Escape_Scramble, one leaving a standing van plays Cargo_JumpOut. Both are used as soon as the rig's " +
                 "controller has a state of this name (a clips.json entry with this state; Seconds 0 = the clip's own length); " +
                 "until then the procedural versions play (the sunk run, NpcGetUp's hop). JumpOut: in place, no Hips travel (the " +
                 "code moves the root from the door sill to the ground over the clip), ending in the Run pose.")]
        public ClipInfo Scramble = new() { State = "Escape_Scramble" };
        public ClipInfo JumpOut = new() { State = "Cargo_JumpOut" };
        [Tooltip("Sitting in the cargo bay the visual turns this many degrees (yaw): the sit clips face the clip's -X, so " +
                 "turned they face the seated capsule's forward (the existing turn-to-the-door logic).")]
        public float SeatYaw;
        [Tooltip("And moves this far (root space) so the seated figure is centred on the seated capsule.")]
        public Vector3 SeatOffset;
        [Tooltip("The seated figure's floor footprint around the root (root space, x and z), with the visual turned and " +
                 "moved: the sit-up keeps it inside the cargo bay.")]
        public Vector2 SeatMin, SeatMax;

        public bool HasGetUps => GetUpBack.Ready && GetUpBelly.Ready;
        public bool HasSeat => SitUp.Ready && SitIdle.Ready;

        [Header("Every clip of clips.json by its role (step 5, NpcAnimDriver): written by GreyboxBuddySetup.InstallClips")]
        [Tooltip("Locomotion clips not in clips.json (the Buddy FBX's Panic_Run_Loop, Walk_v02) were authored for these ground " +
                 "speeds (m/s); a clips.json entry with a speed replaces them.")]
        public float WalkSpeed = 1.5f;
        public float RunSpeed = 3.2f;
        public ClipInfo[] Roles = Array.Empty<ClipInfo>();

        /// <summary>The clips.json clip of this role (NpcAnimContract roles), or null.</summary>
        public ClipInfo Role(string role)
        {
            if (Roles == null || string.IsNullOrEmpty(role)) return null;
            foreach (ClipInfo c in Roles)
                if (c != null && c.Role == role) return c;
            return null;
        }

        // Step 5: a crowd activity whose clips sit or lean on a prop behind the NPC (clips.json "placement"): CrowdWalker
        // finds it near the slot and stands Gap in front of it, facing away (none found: it only stands there).
        [Serializable]
        public sealed class ActivityPlacement
        {
            [Tooltip("The CrowdActivity's name.")]
            public string Activity = "";
            [Tooltip("Part of the prop collider's name (\"bench\": the nearest such collider within Reach); empty: the wall " +
                     "straight behind the slot, within Reach.")]
            public string Prop = "";
            [Tooltip("m above the ground the prop is looked for at (the seat, the wall at the hood).")]
            public float Height;
            [Tooltip("m between the prop's face and the NPC's root (the clip's contract).")]
            public float Gap;
            public float Reach;
        }

        public ActivityPlacement[] Placements = Array.Empty<ActivityPlacement>();

        // Step 5 hook: a small hand prop shown while a crowd activity plays (clips.json "props": the SmokeCorner cigarette;
        // the bone and offset from the clip's README). NpcAnimDriver puts it under the bone (Prefab, else a plain white
        // cylinder of Size) and takes it away when the activity ends.
        [Serializable]
        public sealed class ActivityProp
        {
            public string Activity = "";
            [Tooltip("The bone's name (mixamorig:RightHand...).")]
            public string Bone = "";
            [Tooltip("Local position (m) and rotation (degrees) in the bone's space.")]
            public Vector3 Position, Rotation;
            [Tooltip("Without a prefab: the cylinder's size in metres (diameter, length, diameter).")]
            public Vector3 Size = new(0.008f, 0.07f, 0.008f);
            public GameObject Prefab;
        }

        public ActivityProp[] Props = Array.Empty<ActivityProp>();

        public ActivityProp PropOf(string activity)
        {
            if (Props == null) return null;
            foreach (ActivityProp p in Props)
                if (p != null && p.Activity == activity) return p;
            return null;
        }

        public ActivityPlacement PlacementOf(string activity)
        {
            if (Placements == null) return null;
            foreach (ActivityPlacement p in Placements)
                if (p != null && p.Activity == activity) return p;
            return null;
        }

        [Header("Sitting in the cargo bay (§4.5)")]
        [Tooltip("Seconds between knocks on the van wall (the Knock clip) while sitting in a slow or parked van.")]
        public Vector2 KnockInterval = new(4f, 9f);
        [Tooltip("m/s: below this the van counts as slow enough to knock.")]
        public float KnockVanSpeed = 2f;
        [Tooltip("Volume (0-1) of each strike: the van-floor thud, no knock sound in the library yet.")]
        public float KnockVolume = 0.45f;

        [Header("Getting up (§4.4)")]
        [Tooltip("Settle: the get-up starts once the pelvis is slower than this (m/s)...")]
        public float SettleSpeed = 0.5f;
        [Tooltip("...or after this many seconds.")]
        public float SettleMax = 1f;
        [Tooltip("Lying on its side (|front . up| below this) it is rolled onto the nearer of back or belly first.")]
        public float SideLimit = 0.3f;
        [Tooltip("Seconds of that roll, and its angular acceleration (rad/s2) on the pelvis and the chest.")]
        public float SideRollTime = 0.3f;
        public float SideRollAccel = 14f;
        [Tooltip("No room for the standing CharacterController where it would get up (and 0.3 / 0.6 m around): it crawls " +
                 "this long and looks again, at most GetUpRetries times; then it gets up where it lies.")]
        public float GetUpCrawlTime = 0.5f;
        public int GetUpRetries = 3;
        [Tooltip("The crawl hop: N·s along the ground (scaled with the mass like every push, reference 40 kg) and m/s up.")]
        public float GetUpCrawlPush = 40f;
        public float GetUpCrawlHop = 0.6f;

        [Header("Pushes on one part (step 3)")]
        [Tooltip("A blow (Q) gives the struck part at most this speed (m/s); the rest of the impulse goes to every body by " +
                 "its mass, so a punch on a 1 kg forearm jolts the body instead of whipping the limb.")]
        public float HitPartSpeed = 6f;
        [Tooltip("A van door pushing a part: the part itself takes at most this acceleration (m/s2) of the push, the rest " +
                 "pushes the whole body (the door's 250-300 N were tuned on the 28-40 kg capsule).")]
        public float DoorPartAccel = 30f;
        [Tooltip("And at most this speed change (m/s) of a closing door's shove.")]
        public float DoorPartShove = 1.5f;

        // Step 4 (§4.3): the Groggy ragdoll moves on its joint drives (NpcStruggle). Joint angles in degrees, springs in
        // Nm/rad, torques in Nm. Starting values, tuned by Fedya's playtest.
        [Header("Groggy: the struggle on the joint drives (§4.3, step 4; NpcStruggle)")]
        [Tooltip("Off: a Groggy ragdoll lies limp as in steps 1-3 (its kicks are the ankle impulse alone).")]
        public bool Struggle = true;
        [Tooltip("Not held: the neck and the waist keep this weak tone; the head comes up HeadLift (neck flexion on the back, " +
                 "extension on the belly) and turns LookAround to either side.")]
        public float GroggyTone = 30f;
        public float HeadLift = 30f;
        public float LookAround = 35f;
        [Tooltip("Lying, not crawling (a cargo bay, in the air): the arms paw about a reaching pose (shoulders and elbows), " +
                 "at a frequency picked per NPC within PawFrequency (Hz).")]
        public float PawSpring = 40f;
        public float PawAmplitude = 35f;
        public Vector2 PawFrequency = new(0.6f, 1.2f);
        [Tooltip("And the legs bicycle slowly (hips and knees).")]
        public float LegSpring = 30f;
        public float LegAmplitude = 25f;
        [Tooltip("Held (the carried struggle): the arms and legs swing this many times wider and 1.3 times faster, and the " +
                 "waist wriggles Wriggle degrees (side bend and twist) inside the carry tone, so A4 keeps the trunk (and a split " +
                 "pair's hammock) carryable.")]
        public float HeldAmplitude = 1.5f;
        public float Wriggle = 10f;
        [Tooltip("A kick (GreyboxNpc picks the moment and rolls the tear, KickTearChance): one leg chambers and lashes out for " +
                 "KickSeconds; its reaction jerks the holders' hands.")]
        public float KickSpring = 250f;
        public float KickMaxTorque = 60f;
        public float KickSeconds = 0.25f;
        [Tooltip("m/s: the kick's ankle impulse (GreyboxNpc.KickImpulse) gives the shin at most this on top of the motors (it " +
                 "used to be the whole kick: ~8 m/s on the 2.2 kg shin).")]
        public float KickPartSpeed = 3f;
        [Tooltip("Crawling (Groggy, not held, touching the ground): the arms reach over the head and pull in turn, the legs " +
                 "push, the head leads. The trunk is dragged along in step with the pulls toward this speed (m/s; GreyboxNpc " +
                 "scales it for an open cargo door), with at most CrawlMaxForce (N; a lying 28 kg body needs ~220 N to start " +
                 "sliding on default ground). Replaces the capsule-era crawl hops on the ragdoll.")]
        public float CrawlSpeed = 0.5f;
        public float CrawlMaxForce = 320f;
        [Tooltip("Seconds of one cycle of both arms; the crawling limbs' spring.")]
        public float CrawlCycle = 0.9f;
        public float CrawlSpring = 60f;
        [Tooltip("Degrees: the pull goes at most this far off the head's direction toward the crawl direction, so a body " +
                 "facing the wrong way curves round head first instead of being dragged backwards (it folds then).")]
        public float CrawlVeer = 60f;

        [Header("Out of a standing van, the trip (§4.5, §4.6; step 4)")]
        [Tooltip("Van still: the procedural hop out of a cargo door (until a Cargo_JumpOut clip is installed): seconds, how " +
                 "far out it lands (m) and the arc's height (m).")]
        public float HopSeconds = 0.45f;
        public float HopReach = 0.7f;
        public float HopApex = 0.2f;
        [Tooltip("A trip (the fat police officer, GreyboxNpc.Stumble): the body pitches forward about its feet at this many " +
                 "rad/s, the shins keep this share of the running velocity (the feet caught).")]
        public float StumblePitch = 2.5f;
        public float StumbleFeet = 0.2f;

        public float TotalMass
        {
            get
            {
                float m = 0f;
                foreach (Part p in Parts) m += p != null ? p.Mass : 0f;
                return m;
            }
        }

        public int IndexOf(Kind kind, NpcSide side = NpcSide.Left)
        {
            bool paired = kind >= Kind.UpperArm;
            for (int i = 0; i < Parts.Length; i++)
                if (Parts[i] != null && Parts[i].Kind == kind && (!paired || Parts[i].Side == side))
                    return i;
            return -1;
        }

        public Vector2 Force(Handle handle) => handle switch
        {
            Handle.Medium => MediumForce,
            Handle.Bad => BadForce,
            _ => GoodForce,
        };

        /// <summary>A3: the share of the weight taken off while 'holders' hands hold it (0 when off or unheld).</summary>
        public float ReliefFor(int holders)
        {
            if (!WeightRelief || holders <= 0 || Relief == null || Relief.Length == 0) return 0f;
            return Mathf.Clamp01(Relief[Mathf.Min(holders, Relief.Length - 1)]);
        }

        public static Vector3 AxisVector(int direction) => direction == 0 ? Vector3.right : direction == 2 ? Vector3.forward : Vector3.up;
    }
}
