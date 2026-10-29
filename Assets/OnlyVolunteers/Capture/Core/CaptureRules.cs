using System;
using System.Collections.Generic;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Zip ties on one NPC (D2; the head bag is stage B).</summary>
    [Serializable]
    public struct Restraints
    {
        public bool hands;
        public bool feet;
        public bool Both => hands && feet;
        public bool Any => hands || feet;
        public override string ToString() => Both ? "руки и ноги связаны" : hands ? "руки связаны" : feet ? "ноги связаны" : "не связан";
    }

    public enum TieTarget : byte { None, Hands, Feet }
    public enum FieldRefusal : byte { None, Dead, Squirming, NoBloodLeft, NotCaught, AlreadyTied, Empty, Full }

    /// <summary>Pure field rules of capture → delivery stage A (spec §5.2 rows hands / feet / both, D1, D7, D10).
    /// Anesthesia and blood themselves use the unchanged OperationRules (same dose, sleep, overdose and portion rules as
    /// the table), here only who may be tied or bled.</summary>
    public static class CaptureRules
    {
        /// <summary>Seconds of holding the use button to put on one zip tie (~1 s).</summary>
        public const float TieSeconds = 1f;
        /// <summary>Hands + feet tied: carrying him is easier (proposed preset −30 % resistance).</summary>
        public const float BothTiedResistance = 0.7f;
        public const int StartingTies = 10;
        public const int TiePrice = 5;

        /// <summary>D7 / CD-05: blood only from a living body that does not fight: asleep (anesthesia), knocked out cold
        /// (the limp first part of a stun) or with his hands tied; never from a corpse; at most until the fatal portion.</summary>
        public static FieldRefusal CanDrawBlood(OperationState s, bool knockedOutCold, Restraints r, int fatalPortion)
        {
            if (s == null) return FieldRefusal.NotCaught;
            if (!s.alive) return FieldRefusal.Dead;
            if (s.bloodPortions >= fatalPortion) return FieldRefusal.NoBloodLeft;
            if (s.Sleeping || knockedOutCold || r.hands) return FieldRefusal.None;
            return FieldRefusal.Squirming;
        }

        /// <summary>A tie goes on a downed (lying, held or asleep) body only; aiming at the legs ties the feet, at the
        /// arms the hands; anywhere else the first free pair (hands first).</summary>
        public static TieTarget ChooseTie(Restraints r, TieTarget aimed)
        {
            if (aimed == TieTarget.Hands && !r.hands) return TieTarget.Hands;
            if (aimed == TieTarget.Feet && !r.feet) return TieTarget.Feet;
            return !r.hands ? TieTarget.Hands : !r.feet ? TieTarget.Feet : TieTarget.None;
        }

        public static Restraints Apply(Restraints r, TieTarget tie)
        {
            if (tie == TieTarget.Hands) r.hands = true;
            else if (tie == TieTarget.Feet) r.feet = true;
            return r;
        }

        /// <summary>Feet tied: he cannot get up and run; he stays down and crawls (row "feet").</summary>
        public static bool StaysDown(Restraints r) => r.feet;
        /// <summary>Hands + feet: he cannot get out of the van on his own (row "both").</summary>
        public static bool CanLeaveVanAlone(Restraints r) => !r.Both;
        /// <summary>Hands tied: no grabbing the world, doors or players, no knocking on the van wall (row "hands").</summary>
        public static bool CanUseHands(Restraints r) => !r.hands;
        public static float CarryResistance(Restraints r) => r.Both ? BothTiedResistance : 1f;

        /// <summary>Closing a table strap cuts the matching tie: an arm strap the hands, a leg strap the feet
        /// (straps 0 L arm, 1 R arm, 2 L leg, 3 R leg, 4 torso).</summary>
        public static Restraints AfterStraps(Restraints r, bool[] straps)
        {
            if (straps == null || straps.Length < 4) return r;
            if (straps[0] || straps[1]) r.hands = false;
            if (straps[2] || straps[3]) r.feet = false;
            return r;
        }
    }

    // ---------- data that travels with the body and into the save (spec §3, D13) ----------

    /// <summary>Capture-side facts of one identity; the anesthesia / blood / organ counters live in its OperationState
    /// (the same object the table later operates on).</summary>
    [Serializable]
    public sealed class CaptureFacts
    {
        public string patientId = "";
        public string districtId = "";
        public string npcTypeId = "";
        /// <summary>Crowd template visual the NPC was made from (for re-creating him after a load).</summary>
        public string visual = "";
        public float condition = 100f;
        public Restraints restraints;
        public bool rolled;
        public int[] intrinsic = new int[CaptureGrades.Organs];
        /// <summary>Round 4 (Fedya): he has been on the table: back in the field he keeps the patient look (his body in the
        /// patient trunks, his own skin and face), never the crowd template's clothes again.</summary>
        public bool undressed;
    }

    [Serializable]
    public sealed class CaptureNpcSave
    {
        public CaptureFacts facts = new CaptureFacts();
        public OperationState operation;
        public byte stage;
        public byte npcState;
        public float stunLeft;
        public float stunTotal;
        public bool inCargo;
        /// <summary>Pelvis position and head direction (world; van-local when inCargo).</summary>
        public Vector3 pelvis;
        public Vector3 headDirection = Vector3.forward;
        public bool faceUp = true;
        /// <summary>Round 4: re-created on his feet (he ran off the table): 'pelvis' is the floor point, 'headDirection' his facing.</summary>
        public bool standing;
        /// <summary>Fist repeat resistance (Fedya 30.10, FistResistanceRulesV01): contacts in the NPC's current sequence and
        /// the active seconds still needed for its quiet time. Older saves have neither: 0 = a fresh sequence.</summary>
        public int fistContacts;
        public float fistRecoverLeft;
    }

    [Serializable]
    public sealed class FieldKitSave
    {
        public int ties = CaptureRules.StartingTies;
        public float anesthesiaBarrel = -1f;
        public float anesthesiaStock = -1f;
        public float bloodFill;
        public int bloodBags;
        public int tool;
        /// <summary>G49: the syringe instances the field kit was holding (identity, PersonId, portion); null = none / legacy.</summary>
        public OnlyVolunteers.Inventory.SyringeInstance bloodSyringe;
        public OnlyVolunteers.Inventory.SyringeInstance anaesthesiaSyringe;
    }

    [Serializable]
    public sealed class CaptureSaveData
    {
        /// <summary>2 (ECONOMY spec v01, 2026-10-28): + the team economy block. Version 1 saves still load: their cash is
        /// migrated into the shared fund once (FundMigration).</summary>
        public const int CurrentVersion = 2;
        public const int OldestLoadableVersion = 1;
        public int version = CurrentVersion;
        public string scene = "";
        public string savedUtc = "";
        public float playTime;
        public Vector3 playerPosition;
        public float playerYaw;
        public bool playerDriving;
        public Vector3 vanPosition;
        public Quaternion vanRotation = Quaternion.identity;
        public bool slideOpen;
        public bool rearOpen;
        public float timeOfDay = -1f;
        public List<CaptureNpcSave> npcs = new List<CaptureNpcSave>();
        public OperationWorldState table;
        public CaptureFacts tablePatient;
        public FieldKitSave kit = new FieldKitSave();
        public int bodyBags = 2;
        public List<CaptureCorpseSave> corpses = new List<CaptureCorpseSave>();
        public List<string> completedPatients = new List<string>();
        /// <summary>W86: the host player's cash (his NetworkInventory: the first-buyer crate pays into it). hasCash false =
        /// a save written before cash was saved: the load keeps the cash he has and restores the rest as before.</summary>
        public bool hasCash;
        public int cash;
        /// <summary>v2: the team's shared fund, its history and transaction keys, paid van tiers, workshop / story flags,
        /// owned bases and equipment deliveries (OnlyVolunteers.Economy). blockVersion 0 = absent (a v1 save). From v2 on
        /// hasCash / cash are no longer written (false / 0): this block is the only money source.</summary>
        public OnlyVolunteers.Economy.EconomySaveData economy = new OnlyVolunteers.Economy.EconomySaveData();
        /// <summary>G49 (same atomic file as the fund): syringe instances in the host's hotbar (Items) and lying in the
        /// world (WorldItems), the C01 sale record (receipts, sold portions, first-sale flag) and the one daily-find record.
        /// Absent in older saves: empty defaults, no syringe is invented for them.</summary>
        public OnlyVolunteers.Inventory.SyringeSaveBlock syringes = new OnlyVolunteers.Inventory.SyringeSaveBlock();
        /// <summary>PLAYER stage (29.10): the world profile — the immutable Solo/Multiplayer mode and the opening/tutorial
        /// state (OnlyVolunteers.Session.WorldSessionV01). blockVersion 0 = absent (an older save): a legacy world, flagged
        /// for the owner's one-time mode choice, never assigned a mode silently.</summary>
        public OnlyVolunteers.Session.WorldProfileSaveBlock world = new OnlyVolunteers.Session.WorldProfileSaveBlock();
    }

    /// <summary>Dev/test hooks in the Core assembly so PlayMode tests (which cannot see Assembly-CSharp) can drive the
    /// capture scenario driver.</summary>
    public static class CaptureTestHooks
    {
        public static IOperationScenarioRunner Runner;
        /// <summary>Save file override so automated runs never touch the player's capture save.</summary>
        public static string SaveSlot;

        // This project enters Play mode without a domain reload: statics must be reset by hand.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { Runner = null; SaveSlot = null; }
    }
}
