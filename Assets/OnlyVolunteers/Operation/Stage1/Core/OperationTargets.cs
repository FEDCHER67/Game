using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>What the cursor is on. Travels over the network as one int (kind &lt;&lt; 16 | index &lt;&lt; 8 | sub).</summary>
    public enum TargetKind : byte { None = 0, Strap = 1, Tool = 2, BloodBag = 3, Tray = 4, Incision = 5, Cord = 6, Organ = 7, Body = 8, Item = 9 }
    public enum BodyPart : byte { Head = 0, Neck = 1, Torso = 2, ShoulderL = 3, ShoulderR = 4, ArmL = 5, ArmR = 6, LegL = 7, LegR = 8 }
    /// <summary>Hotbar slots = keys 1..4.</summary>
    public enum ToolSlot : byte { Hands = 0, Anesthesia = 1, Blood = 2, Scalpel = 3, Suture = 4 }

    [Serializable]
    public struct OpTarget : IEquatable<OpTarget>
    {
        public TargetKind kind;
        public byte index;
        public byte sub;
        public OpTarget(TargetKind kind, int index = 0, int sub = 0) { this.kind = kind; this.index = (byte)index; this.sub = (byte)sub; }
        public static readonly OpTarget None = default;
        public int Code => ((int)kind << 16) | (index << 8) | sub;
        public static OpTarget FromCode(int code)
        {
            int k = (code >> 16) & 0xFF;
            if (k > (int)TargetKind.Item) return None;
            return new OpTarget((TargetKind)k, (code >> 8) & 0xFF, code & 0xFF);
        }
        public bool IsNone => kind == TargetKind.None;
        public BodyPart Part => (BodyPart)index;
        /// <summary>Arm, shoulder or neck: where the anesthesia goes.</summary>
        public bool IsInjectionSite => kind == TargetKind.Body && (Part == BodyPart.Neck || Part == BodyPart.ShoulderL || Part == BodyPart.ShoulderR || Part == BodyPart.ArmL || Part == BodyPart.ArmR);
        /// <summary>0 left arm, 1 right arm, -1 not an arm. Shoulders count as the arm for blood.</summary>
        public int ArmSide => kind != TargetKind.Body ? -1 : Part == BodyPart.ArmL || Part == BodyPart.ShoulderL ? 0 : Part == BodyPart.ArmR || Part == BodyPart.ShoulderR ? 1 : -1;
        public bool Equals(OpTarget other) => Code == other.Code;
        public override bool Equals(object obj) => obj is OpTarget t && Equals(t);
        public override int GetHashCode() => Code;
        public static bool operator ==(OpTarget a, OpTarget b) => a.Code == b.Code;
        public static bool operator !=(OpTarget a, OpTarget b) => a.Code != b.Code;
        public override string ToString() => kind + "/" + index + "/" + sub;
    }

    /// <summary>Hint/rejection reasons the server sends back to one client; the client turns them into Russian text.</summary>
    public enum OpHint : byte
    {
        None, Squirming, PatientDead, NotOnTable, ToolBusy, HandsFull, SyringeEmpty, SyringeFull, SyringeNotFull, NoBags,
        StartAtDot, NeedScalpel, CutCordsFirst, NoBloodLeft, WrongSpot, StockEmpty, Refilled, BagReady,
        // Round 3: a living patient with an open belly keeps his straps; suturing before the opening / after the seam.
        SutureFirst, NothingToSuture, StitchFromTop, SyringeOtherPerson, SyringeUnavailable,
        // WP05: no suture kit left for a new closure.
        NoSutureKit
    }

    /// <summary>Round 3 (Fedya): the straps in play. The torso strap is off for now (OperationTuning.torsoStrap); old saves
    /// with it closed load with it open.</summary>
    public static class OperationStraps
    {
        public static int Count(OperationTuning tuning) => tuning != null && tuning.torsoStrap ? 5 : 4;
        public static bool Active(OperationTuning tuning, int index) => index >= 0 && index < Count(tuning);
        /// <summary>Held down: the torso strap when it exists, otherwise all four limb straps.</summary>
        public static bool Held(OperationState state, OperationTuning tuning) =>
            state != null && (tuning != null && tuning.torsoStrap ? state.Torso : state.LimbsStrapped);
        public static bool AllClosed(OperationState state, OperationTuning tuning)
        {
            if (state == null) return false;
            for (int i = 0; i < Count(tuning); i++) if (!state.restraints[i]) return false;
            return true;
        }
        public static bool AllOpen(OperationState state, OperationTuning tuning)
        {
            if (state == null) return true;
            for (int i = 0; i < Count(tuning); i++) if (state.restraints[i]) return false;
            return true;
        }
    }

    /// <summary>Dev/test hooks living in the Core assembly so PlayMode tests (which cannot see Assembly-CSharp) can drive
    /// the runtime scenario driver and force deterministic death rolls.</summary>
    public interface IOperationScenarioRunner
    {
        bool Busy { get; }
        string LastResult { get; }
        IReadOnlyList<string> Log { get; }
        void Begin(string scenario);
    }

    public static class OperationTestHooks
    {
        public static IOperationScenarioRunner Runner;
        /// <summary>When set (0..1), extraction death rolls use this value instead of Random.value.</summary>
        public static float? ForcedRoll;
        /// <summary>Save slot override so automated runs never touch the player's operation save.</summary>
        public static string SaveSlot;
    }
}
