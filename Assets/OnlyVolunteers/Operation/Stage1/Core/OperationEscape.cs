using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Round 4: the Escape_v01 clips as data (docs/reviews/escape_anims_v01/CONTRACT.md). Times are AUTHORED seconds
    /// (30 fps clips); gameplay plays them at tuning.escapeSpeed. Straps: 0 left arm, 1 right arm, 2 left leg, 3 right leg.
    /// Append only: the ids travel in OperationState.escapeClip (network and saves).</summary>
    public static class OperationEscape
    {
        public const int UnbuckleArmRByL = 0, UnbuckleArmLByR = 1, TugArmR = 2, TugArmL = 3, SitUp = 4,
            UnbuckleLegL = 5, UnbuckleLegR = 6, UnbuckleLegsBoth = 7, TugLegs = 8, SwingOffR = 9, HopRunR = 10,
            SlumpLieReachR = 11, SlumpLieReachL = 12, SlumpSit = 13, SwingOffL = 14, HopRunL = 15,
            SlumpEdgeR = 16, SlumpEdgeL = 17, StumbleOffR = 18, StumbleOffL = 19, Count = 20;
        /// <summary>Pose stages: lying (LIE), sitting up on the pad (SIT), sitting on the pad edge (EDGE_X).</summary>
        public const int Lying = 0, Sitting = 1, Edge = 2;

        public struct Clip
        {
            public string name;
            public float seconds;
            public int endStage;
            /// <summary>StrapOpen events: strap index and authored time (up to two).</summary>
            public int strapA, strapB;
            public float openA, openB;
            /// <summary>Straps (bit per index) that must be closed / open while the clip plays.</summary>
            public int mustClose, mustOpen;
            public bool slump;
            public bool loop;
        }

        private const int ArmL = 1, ArmR = 2, LegL = 4, LegR = 8, Arms = ArmL | ArmR, All = 15;
        private static Clip C(string name, float seconds, int endStage, int close = 0, int open = 0, int strapA = -1, float openA = 0f,
            int strapB = -1, float openB = 0f, bool slump = false, bool loop = false) => new Clip
        {
            name = name, seconds = seconds, endStage = endStage, mustClose = close, mustOpen = open,
            strapA = strapA, openA = openA, strapB = strapB, openB = openB, slump = slump, loop = loop,
        };

        /// <summary>Animator state names = the clip names without "_v01" (OperationStage1EscapeClips builds them).</summary>
        public static readonly Clip[] Clips =
        {
            C("Esc_Lie_UnbuckleArmR_ByL", 2.60f, Lying, ArmR, ArmL, 1, 1.40f),
            C("Esc_Lie_UnbuckleArmL_ByR", 2.60f, Lying, ArmL, ArmR, 0, 1.40f),
            C("Esc_Lie_TugArmR_Loop", 2.00f, Lying, ArmR, ArmL, loop: true),
            C("Esc_Lie_TugArmL_Loop", 2.00f, Lying, ArmL, ArmR, loop: true),
            C("Esc_SitUp", 1.00f, Sitting, 0, Arms),
            C("Esc_Sit_UnbuckleLegL", 2.30f, Sitting, LegL, Arms, 2, 1.35f),
            C("Esc_Sit_UnbuckleLegR", 2.30f, Sitting, LegR, Arms, 3, 1.35f),
            C("Esc_Sit_UnbuckleLegsBoth", 2.60f, Sitting, LegL | LegR, Arms, 3, 1.08f, 2, 1.42f),
            C("Esc_Sit_TugLegs_Loop", 1.60f, Sitting, 0, Arms, loop: true),
            C("Esc_SwingOff_R", 1.20f, Edge, 0, All),
            C("Esc_HopRun_R", 1.50f, Edge, 0, All),
            C("Esc_Slump_LieReachR", 1.30f, Lying, slump: true),
            C("Esc_Slump_LieReachL", 1.30f, Lying, slump: true),
            C("Esc_Slump_Sit", 1.40f, Lying, slump: true),
            C("Esc_SwingOff_L", 1.20f, Edge, 0, All),
            C("Esc_HopRun_L", 1.50f, Edge, 0, All),
            C("Esc_Slump_Edge_R", 2.00f, Lying, slump: true),
            C("Esc_Slump_Edge_L", 2.00f, Lying, slump: true),
            C("Esc_Stumble_Off_R", 1.60f, Edge, slump: true),
            C("Esc_Stumble_Off_L", 1.60f, Edge, slump: true),
        };

        public static bool Valid(int clip) => clip >= 0 && clip < Count;
        public static bool IsHopRun(int clip) => clip == HopRunR || clip == HopRunL;
        public static bool IsStumble(int clip) => clip == StumbleOffR || clip == StumbleOffL;
        /// <summary>+1 his right (camera side), -1 his left (instrument-stand side), 0 for clips with no side.</summary>
        public static int Side(int clip) => clip == SwingOffR || clip == HopRunR || clip == SlumpEdgeR || clip == StumbleOffR ? 1
            : clip == SwingOffL || clip == HopRunL || clip == SlumpEdgeL || clip == StumbleOffL ? -1 : 0;

        /// <summary>Table-local hand-off root at the end of HopRun (contract "HopRun root hand-off"): position on the floor
        /// and yaw about the table's up.</summary>
        public static Vector3 Run0Local(int side) => side < 0 ? new Vector3(1.644f, 0f, -1.167f) : new Vector3(-1.669f, 0f, -1.137f);
        public static float Run0Yaw(int side) => side < 0 ? 130f : 230f;

        /// <summary>The interrupt clip for a clip cut at authored time t (contract "Interrupt"); -1: not interruptible now
        /// (in the air, or already running).</summary>
        public static int SlumpFor(int clip, float t)
        {
            switch (clip)
            {
                case UnbuckleArmRByL: case TugArmR: return SlumpLieReachR;
                case UnbuckleArmLByR: case TugArmL: return SlumpLieReachL;
                case SitUp: case UnbuckleLegL: case UnbuckleLegR: case UnbuckleLegsBoth: case TugLegs: return SlumpSit;
                case SwingOffR: return t < 0.76f ? SlumpSit : SlumpEdgeR;
                case SwingOffL: return t < 0.76f ? SlumpSit : SlumpEdgeL;
                case HopRunR: return t < 0.30f ? SlumpEdgeR : t >= 0.47f && t <= 0.98f ? StumbleOffR : -1;
                case HopRunL: return t < 0.30f ? SlumpEdgeL : t >= 0.47f && t <= 0.98f ? StumbleOffL : -1;
            }
            return -1;
        }

        /// <summary>Escape time from waking to the run hand-off at authored speed, without tug loops (contract table).</summary>
        public static float PlanSeconds(bool[] restraints)
        {
            if (restraints[0] && restraints[1]) return float.PositiveInfinity;
            float t = 0f;
            if (restraints[0] || restraints[1]) t += Clips[UnbuckleArmRByL].seconds;
            t += Clips[SitUp].seconds;
            if (restraints[2] && restraints[3]) t += Clips[UnbuckleLegsBoth].seconds;
            else if (restraints[2] || restraints[3]) t += Clips[UnbuckleLegL].seconds;
            return t + Clips[SwingOffR].seconds + Clips[HopRunR].seconds;
        }
    }

    public sealed partial class OperationRules
    {
        /// <summary>Round 4 (server input): the exit side the patient takes when he swings off: +1 his right, -1 his left.
        /// The table sets it each tick to the side away from the nearest player.</summary>
        public int PreferredEscapeSide { get; set; } = 1;

        private bool EscapeClipAvailable(int clip) => OperationEscape.Valid(clip) && (tuning.escapeMissingClips & (1 << clip)) == 0;
        private int Mask(int closedOrOpen, bool closed)
        {
            int bits = 0;
            for (int i = 0; i < 4; i++) if (State.restraints[i] == closed) bits |= 1 << i;
            return bits & closedOrOpen;
        }
        private bool Allowed(OperationEscape.Clip c) => Mask(c.mustOpen, false) == c.mustOpen &&
            // a required-closed strap may already be open once its own StrapOpen event has passed
            (Mask(c.mustClose, true) | OpenedByClip(c)) == c.mustClose;
        private int OpenedByClip(OperationEscape.Clip c)
        {
            int bits = 0;
            if (c.strapA >= 0 && State.escapeClipTime >= c.openA) bits |= 1 << c.strapA;
            if (c.strapB >= 0 && State.escapeClipTime >= c.openB) bits |= 1 << c.strapB;
            return bits & c.mustClose;
        }

        /// <summary>Round 4: the escape as a chain of the Escape_v01 clips (contract "Gameplay chaining"). The server owns the
        /// clip and its time; every peer plays the same clip from it. Straps open exactly at the clips' StrapOpen events
        /// (PatientCue.Unbuckled + LastUnbuckledStrap/Hand, as before). An interrupt (asleep again, held, a strap closed under
        /// him) plays the matching slump; HopRun's end hands him to the field running (PatientCue.RanOff).</summary>
        private void TickEscapeClips(float seconds, bool active)
        {
            float speed = Mathf.Max(0.1f, tuning.escapeSpeed);
            if (OperationEscape.Valid(State.escapeClip))
            {
                var clip = OperationEscape.Clips[State.escapeClip];
                if (!clip.slump && (!active || !Allowed(clip)))
                {
                    int slump = OperationEscape.SlumpFor(State.escapeClip, State.escapeClipTime);
                    if (slump >= 0)
                    {
                        // A v01b slump not imported yet (edge / stumble): the sitting slump instead.
                        if (!EscapeClipAvailable(slump)) slump = OperationEscape.SlumpSit;
                        if (EscapeClipAvailable(slump)) { StartEscapeClip(slump); Emit(PatientCue.EscapeSlump); }
                        else StopEscapeClips();
                        return;
                    }
                    // -1: in the air or already running: he goes on regardless.
                }
                float before = State.escapeClipTime;
                State.escapeClipTime += seconds * speed;
                OpenAt(clip.strapA, clip.openA, before);
                OpenAt(clip.strapB, clip.openB, before);
                if (State.escapeClipTime < clip.seconds) return;
                int finished = State.escapeClip;
                float leftover = State.escapeClipTime - clip.seconds; // carried into the next clip: the chain keeps the contract time
                State.escapeStage = clip.endStage;
                State.escapeClip = -1; State.escapeClipTime = 0f;
                if (OperationEscape.IsHopRun(finished)) { RunOff(false); return; }
                if (OperationEscape.IsStumble(finished)) { RunOff(true); return; }
                if (clip.slump) { State.escapeSide = 0; return; }
                chainLeftover = Mathf.Clamp(leftover, 0f, 0.1f);
            }
            if (!active) { chainLeftover = 0f; return; }
            int next = NextEscapeClip();
            if (next >= 0) StartEscapeClip(next);
            chainLeftover = 0f;
        }
        private float chainLeftover;

        /// <summary>The hand that opens a strap: the other wrist's hand for an arm, the same side's hand for a leg (0 left, 1 right).</summary>
        private static int StrapHand(int strap) => strap == 0 ? 1 : strap == 1 ? 0 : strap == 2 ? 0 : 1;
        private void OpenAt(int strap, float at, float before)
        {
            int hand = StrapHand(strap);
            if (strap < 0 || before >= at || State.escapeClipTime < at || !State.restraints[strap]) return;
            State.restraints[strap] = false;
            LastUnbuckledStrap = strap; LastUnbuckledHand = hand;
            Emit(PatientCue.Unbuckled); Emit(PatientCue.StrapChanged);
        }

        /// <summary>The next clip for the current pose and straps (no tug loops: Fedya wants him quick).</summary>
        public int NextEscapeClip()
        {
            var r = State.restraints;
            switch (State.escapeStage)
            {
                case OperationEscape.Lying:
                    if (r[0] && r[1]) return -1; // both wrists strapped: no escape (Op_Panic / Op_Struggle)
                    if (r[1]) return OperationEscape.UnbuckleArmRByL;
                    if (r[0]) return OperationEscape.UnbuckleArmLByR;
                    return OperationEscape.SitUp;
                case OperationEscape.Sitting:
                    if (r[0] || r[1]) return -1; // cannot happen through Allowed; stay put
                    if (r[2] && r[3]) return OperationEscape.UnbuckleLegsBoth;
                    if (r[2]) return OperationEscape.UnbuckleLegL;
                    if (r[3]) return OperationEscape.UnbuckleLegR;
                    int side = PreferredEscapeSide < 0 && EscapeClipAvailable(OperationEscape.SwingOffL) && EscapeClipAvailable(OperationEscape.HopRunL) ? -1 : 1;
                    State.escapeSide = side;
                    return side < 0 ? OperationEscape.SwingOffL : OperationEscape.SwingOffR;
                case OperationEscape.Edge:
                    return State.escapeSide < 0 ? OperationEscape.HopRunL : OperationEscape.HopRunR;
            }
            return -1;
        }

        private void StartEscapeClip(int clip)
        {
            if (State.escapeStage == OperationEscape.Lying && !OperationEscape.Clips[clip].slump) Emit(PatientCue.EscapeAttempt);
            State.escapeClip = clip; State.escapeClipTime = chainLeftover; chainLeftover = 0f;
            Emit(PatientCue.EscapeStep);
        }

        /// <summary>Stops the choreography without a slump (he is lying anyway, e.g. put to sleep before the first clip).</summary>
        public void StopEscapeClips()
        {
            State.escapeClip = -1; State.escapeClipTime = 0f; State.escapeStage = OperationEscape.Lying; State.escapeSide = 0;
        }

        /// <summary>End of HopRun (on his feet at RUN0) or of Stumble_Off (face down beside the table): off the table, a
        /// field NPC again (the table and the capture bridge hand him over on PatientCue.RanOff).</summary>
        private void RunOff(bool stumbled)
        {
            State.onTable = State.aligned = false; State.knockedOut = false; State.escapeProgress = 0f; State.escapes++;
            State.unbuckleProgress = 0f; State.ranOff = !stumbled;
            State.escapeStage = OperationEscape.Lying; State.escapeClip = -1; State.escapeClipTime = 0f;
            System.Array.Clear(State.restraints, 0, State.restraints.Length);
            Emit(PatientCue.RanOff); Emit(PatientCue.Escaped);
        }
    }
}
