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
            SlumpEdgeR = 16, SlumpEdgeL = 17, StumbleOffR = 18, StumbleOffL = 19,
            // K10 (Fedya 29.10): the PANIC v02 variants of the same steps (dumb, clumsy, comic) for the opened patient; the
            // HopRun variants clutch the belly. Same strap logic as their v01 base; timings from the tuning (the v02 manifest).
            PanicUnbuckleArmRByL = 20, PanicUnbuckleArmLByR = 21, PanicTugArmR = 22, PanicTugArmL = 23, PanicSitUp = 24,
            PanicUnbuckleLegL = 25, PanicUnbuckleLegR = 26, PanicUnbuckleLegsBoth = 27, PanicTugLegs = 28, PanicSwingOffR = 29,
            PanicSwingOffL = 30, PanicStumbleOffR = 31, PanicStumbleOffL = 32, ClutchHopRunR = 33, ClutchHopRunL = 34, Count = 35;
        /// <summary>The v01 clips are ids 0..V01Count-1; the K10 panic variants follow.</summary>
        public const int V01Count = 20, FirstPanic = 20, PanicCount = Count - FirstPanic;
        /// <summary>The v01 clip each panic variant stands in for (index = id - FirstPanic).</summary>
        private static readonly int[] PanicBase =
        {
            UnbuckleArmRByL, UnbuckleArmLByR, TugArmR, TugArmL, SitUp, UnbuckleLegL, UnbuckleLegR, UnbuckleLegsBoth, TugLegs,
            SwingOffR, SwingOffL, StumbleOffR, StumbleOffL, HopRunR, HopRunL,
        };
        public static bool IsPanic(int clip) => clip >= FirstPanic && clip < Count;
        /// <summary>The v01 clip of an id (itself for a v01 clip).</summary>
        public static int BaseOf(int clip) => IsPanic(clip) ? PanicBase[clip - FirstPanic] : clip;
        /// <summary>The panic variant of a v01 clip, -1 if it has none (the slumps).</summary>
        public static int PanicOf(int baseClip)
        {
            for (int k = 0; k < PanicBase.Length; k++) if (PanicBase[k] == baseClip) return FirstPanic + k;
            return -1;
        }
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

        /// <summary>Animator state names = the clip names without "_v01" / "_v02" (OperationStage1EscapeClips builds them).</summary>
        public static readonly Clip[] Clips = WithPanic(new[]
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
        });

        /// <summary>K10: the v01 table plus one entry per panic variant: the base clip's data under the state name
        /// "&lt;base&gt;_Panic" (HopRun: "&lt;base&gt;_BellyClutch") with the Escape_Panic_v02 lengths
        /// (escape_clips_manifest_v02.json; StrapOpen times unchanged from v01). tuning.escapePanicTiming (written by the import
        /// from the same manifest) overrides them.</summary>
        private static Clip[] WithPanic(Clip[] v01)
        {
            var all = new Clip[Count];
            for (int i = 0; i < v01.Length; i++) all[i] = v01[i];
            for (int k = 0; k < PanicBase.Length; k++)
            {
                int b = PanicBase[k];
                var c = v01[b];
                bool hop = b == HopRunR || b == HopRunL;
                c.name += hop ? "_BellyClutch" : "_Panic";
                c.seconds = PanicSeconds(b, c.seconds);
                all[FirstPanic + k] = c;
            }
            return all;
        }
        /// <summary>Escape_Panic_v02 clip lengths (authored seconds) by v01 base; TugLegs has no v02 clip (v01 length).</summary>
        private static float PanicSeconds(int baseClip, float v01) => baseClip switch
        {
            UnbuckleArmRByL or UnbuckleArmLByR => 3.00f,
            TugArmR or TugArmL => 2.00f,
            SitUp => 1.20f,
            UnbuckleLegL or UnbuckleLegR => 2.40f,
            UnbuckleLegsBoth => 2.80f,
            SwingOffR or SwingOffL => 1.40f,
            StumbleOffR or StumbleOffL => 1.80f,
            HopRunR or HopRunL => 1.50f,
            _ => v01,
        };
        /// <summary>K10: the doomed runner's field run loop (Esc_Run_BellyClutch_Loop_Panic_v02, in place, 3.2 m/s like
        /// Flee_Run_v01); the field NPC plays it instead of its run clips (CaptureNpc).</summary>
        public const string RunClutchLoop = "Esc_Run_BellyClutch_Loop_Panic";

        public static bool Valid(int clip) => clip >= 0 && clip < Count;
        public static bool IsHopRun(int clip) { clip = BaseOf(clip); return clip == HopRunR || clip == HopRunL; }
        public static bool IsStumble(int clip) { clip = BaseOf(clip); return clip == StumbleOffR || clip == StumbleOffL; }
        /// <summary>+1 his right (camera side), -1 his left (instrument-stand side), 0 for clips with no side.</summary>
        public static int Side(int clip)
        {
            clip = BaseOf(clip);
            return clip == SwingOffR || clip == HopRunR || clip == SlumpEdgeR || clip == StumbleOffR ? 1
                : clip == SwingOffL || clip == HopRunL || clip == SlumpEdgeL || clip == StumbleOffL ? -1 : 0;
        }

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

        private bool EscapeClipAvailable(int clip) => OperationEscape.Valid(clip) && (OperationEscape.IsPanic(clip)
            ? (tuning.escapePanicMissing & (1 << (clip - OperationEscape.FirstPanic))) == 0
            : (tuning.escapeMissingClips & (1 << clip)) == 0);

        /// <summary>K10: the clip data as played: a panic variant takes its imported timings (tuning.escapePanicTiming:
        /// seconds, openA, openB per variant; 0 = the v01 value).</summary>
        public OperationEscape.Clip ClipData(int clip)
        {
            var c = OperationEscape.Clips[clip];
            if (!OperationEscape.IsPanic(clip) || tuning.escapePanicTiming == null) return c;
            int k = (clip - OperationEscape.FirstPanic) * 3;
            if (k + 2 >= tuning.escapePanicTiming.Length) return c;
            if (tuning.escapePanicTiming[k] > 0.05f) c.seconds = tuning.escapePanicTiming[k];
            if (tuning.escapePanicTiming[k + 1] > 0f) c.openA = tuning.escapePanicTiming[k + 1];
            if (tuning.escapePanicTiming[k + 2] > 0f) c.openB = tuning.escapePanicTiming[k + 2];
            return c;
        }

        /// <summary>K10 (Fedya 29.10): the opened, unsewn living patient frees himself in a PANIC: the panic v02 variant of a
        /// step when it is imported, else the v01 clip. A sewn-up patient (ordinary OB-02 escape) keeps v01.</summary>
        public int Styled(int clip)
        {
            if (clip < 0 || !State.alive || !State.CavityOpen || OperationEscape.IsPanic(clip)) return clip;
            int panic = OperationEscape.PanicOf(clip);
            return panic >= 0 && EscapeClipAvailable(panic) ? panic : clip;
        }
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
                var clip = ClipData(State.escapeClip);
                if (!clip.slump && (!active || !Allowed(clip)))
                {
                    // K10: a panic variant is interrupted like its v01 base, at the same share of the clip.
                    int baseClip = OperationEscape.BaseOf(State.escapeClip);
                    float baseTime = State.escapeClipTime * OperationEscape.Clips[baseClip].seconds / Mathf.Max(0.01f, clip.seconds);
                    int slump = Styled(OperationEscape.SlumpFor(baseClip, baseTime));
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
            int next = Styled(NextEscapeClip()); // K10: the panic variant for the opened patient (v01 if not imported)
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
            ArmShockRun(); // K10: he runs off with the belly open: pain shock within 2..12 m
            Emit(PatientCue.RanOff); Emit(PatientCue.Escaped);
        }

        // ---------- K10 (Fedya 29.10, variant В): the doomed run of an opened patient ----------

        /// <summary>Server RNG (0..1) for the doomed-run distance; null = UnityEngine.Random.value. Tests pin it.</summary>
        public System.Func<float> ShockRunRandom { get; set; }

        /// <summary>A step longer than this (one physics step) is a teleport (respawn, put down, van load), not running.</summary>
        public const float ShockRunMaxStep = 1.5f;

        /// <summary>K10: a LIVING patient leaving the table with the belly opened and not sewn (CavityOpen) is doomed: rolls
        /// the pain-shock distance once (tuning 2..12 m). Idempotent: an armed run is never re-rolled or restarted. Called by
        /// the escape exits (RunOff, Escape) and by the table when it lets a living patient go (carried or fallen off).
        /// True = he is on the doomed run.</summary>
        public bool ArmShockRun()
        {
            if (!State.alive) return false;
            if (State.shockRunMeters > 0f) return true;
            if (!State.CavityOpen) return false;
            float r = Mathf.Clamp01(ShockRunRandom != null ? ShockRunRandom() : UnityEngine.Random.value);
            float min = Mathf.Max(0.1f, tuning.shockRunMinMeters), max = Mathf.Max(min, tuning.shockRunMaxMeters);
            State.shockRunMeters = Mathf.Lerp(min, max, r);
            State.shockRunCovered = 0f; State.shockRunTime = 0f;
            return true;
        }

        /// <summary>K10: one step of the doomed patient's OWN escape locomotion, fed by whoever moves his body (server side:
        /// the field NPC while he runs or crawls away; the dev-scene table counts the seconds only). metres: horizontal
        /// travel of the step (ShockRunStep, teleports are 0); seconds: time spent in it. NOT fed while he is carried, in the
        /// van, lying stunned or asleep (ShockRunCounts), so a recapture stays possible. Pain shock (DeathCause.Shock, the
        /// existing death) once the rolled distance is covered, or after tuning.shockRunMaxSeconds of such locomotion (stuck
        /// against something). True = he died in this step.</summary>
        public bool AdvanceShockRun(float metres, float seconds)
        {
            if (!State.ShockRun || State.onTable || State.Sleeping) return false;
            if (Finite(metres) && metres > 0f) State.shockRunCovered += metres;
            if (Finite(seconds) && seconds > 0f) State.shockRunTime += seconds;
            if (State.shockRunCovered < State.shockRunMeters && State.shockRunTime < Mathf.Max(0.1f, tuning.shockRunMaxSeconds)) return false;
            Die(DeathCause.Shock);
            return true;
        }

        /// <summary>K10: does this body state count as his own escape locomotion? On his feet or crawling by himself; never
        /// carried, in a vehicle or being repositioned.</summary>
        public static bool ShockRunCounts(bool onFeet, bool crawling, bool carried, bool inVehicle) =>
            !carried && !inVehicle && (onFeet || crawling);

        /// <summary>K10: horizontal metres between two body positions of one physics step; 0 for a teleport.</summary>
        public static float ShockRunStep(Vector3 from, Vector3 to)
        {
            Vector3 d = to - from; d.y = 0f;
            float m = d.magnitude;
            return Finite(m) && m <= ShockRunMaxStep ? m : 0f;
        }

        /// <summary>K10: sewn up again (caught and brought back to the table): the normal escape rules apply again.</summary>
        private void ClearShockRun() { State.shockRunMeters = 0f; State.shockRunCovered = 0f; State.shockRunTime = 0f; }
    }
}
