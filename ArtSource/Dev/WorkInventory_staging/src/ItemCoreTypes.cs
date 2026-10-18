// G39 work inventory core. DTOs contain plain data; the ledger owns all mutation.
// Spec: C:\Dev\Game\docs\specs\WORK_INVENTORY_SPEC_2026-10-18_v01.md
// Plain [Serializable] classes with public fields so JsonUtility and FishNet can carry them later.
using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Items.Core
{
    /// <summary>What an item is for. Rules branch on this, never on the numeric definition id.</summary>
    public enum ItemClass : byte
    {
        Other = 0,
        Organ = 1,
        BloodBag = 2,          // sealed blood portion, no tier, no spoilage
        BloodSyringe = 3,      // reusable; Fill.Amount 0..1 portion, Fill.DonorPatientId
        AnesthesiaSyringe = 4, // reusable; Fill.Amount abstract units, Fill.Formula tier
        AnestheticVial = 5,    // stock for refills; Fill.Amount units
        ZipTies = 6,           // stackable consumable, Count = uses
        OrganPouch = 7,        // empty individual organ bag, stackable
        EmptyBloodBag = 8,     // stackable
        BodyBag = 9,           // stackable consumable
        Cooler = 10,           // two-handed, is a container (8 slots)
        Tool = 11,             // knife, saw, hammer... (later)
        HeadBag = 12,
    }

    public enum OrganKind : byte { Kidney, Liver, Lungs, Heart, Eye, Brain }

    /// <summary>Quality tiers (OPERATIONS §12.1 / BUYERS v02): 1 Damaged/Убитое .. 5 Perfect+/Идеальное.</summary>
    public static class Tier
    {
        public const int Damaged = 1, Acceptable = 2, Good = 3, Perfect = 4, PerfectPlus = 5;
        public static int Clamp(int t) => t < Damaged ? Damaged : t > PerfectPlus ? PerfectPlus : t;
        public static int FromCaptureGrade(int grade) => grade >= 0 && grade <= 4 ? grade + 1 : throw new ArgumentOutOfRangeException(nameof(grade));
        public static int ToCaptureGrade(int tier) => tier >= 1 && tier <= 5 ? tier - 1 : throw new ArgumentOutOfRangeException(nameof(tier));
        public static int DisplayPercent(int tier) => (ToCaptureGrade(tier) + 1) * 20;
    }

    /// <summary>Where an item physically is. Exactly one place at a time.</summary>
    public enum PlaceKind : byte
    {
        None = 0,      // not yet placed / removed (consumed or sold tombstone)
        Container = 1, // ContainerId + Slot
        World = 2,     // loose physical object (a WorldItem NetworkObject on the server)
        Carried = 3,   // two-handed carry by CarrierId (cooler, body bag)
    }

    public enum ContainerKind : byte
    {
        Pockets = 0,        // per player hotbar, 6 slots; the active slot is "in hands"
        VanShelf = 1,       // small items snapped into the van bay rack
        VanCoolerMount = 2, // holds two-handed coolers in the van
        Cooler = 3,         // portable cooler contents, 8 slots
        Fridge = 4,         // stationary refrigerator, 24 slots, needs base power
        Tray = 5,           // operating tray / any uncooled surface tray
        BuyerCase = 6,      // open case at a buyer surface (reservation, not sale)
        Stash = 7,          // special-order dead drop
        ReturnTray = 8,     // unsold-goods tray left at a meeting point
        Kit = 9,           // occupies one of the SIX pocket keys; ordered contents cycle in hand
    }

    /// <summary>Spoilage environment of an item, derived from its direct place.</summary>
    public enum StorageClass : byte { Room = 0, PortableCooler = 1, FridgePowered = 2, FridgeUnpowered = 3 }

    public enum ItemError : byte
    {
        None = 0, NoSuchItem, NoSuchContainer, ContainerClosed, ContainerFull, SlotOccupied, NotAccepted,
        TwoHandedOnly, NotTwoHanded, NotEnough, AlreadyExists, NotOwner, Duplicate, BadRequest,
        StaleRequest, PlayerAbsent, UpgradeRequired, Busy, OutOfReach, NoLineOfSight, InvalidTarget,
        EmptyHandsRequired, NoActiveItem, MissingSupply, FormulaMismatch, BloodExpired, HoldExpired,
        WrongPhase, StockEmpty, NoSurface, BuyerRefused,
    }

    /// <summary>Static per-definition data. Built by the Unity side from ItemDefinition.</summary>
    [Serializable]
    public sealed class ItemDef
    {
        public int Id;                   // existing ItemDefinition.Id (never renumbered)
        public string Key = "";          // stable text key, e.g. "organ.kidney"
        public ItemClass Class;
        public int MaxStack = 1;         // >1 only for stateless consumables
        public bool TwoHanded;           // carried with both hands, never in pockets/shelf
        public int ContainerSlots;       // >0 when the item itself is a container (cooler)
        public OrganKind Organ;          // valid when Class == Organ
        public long BaseValueCents;      // OPERATIONS §15.2 base price, placeholder for the economy pass
        public bool IsMerchandise => Class == ItemClass.Organ || Class == ItemClass.BloodBag || Class == ItemClass.BloodSyringe;
        public bool IsPerishable => Class == ItemClass.Organ;
        public ItemDef Copy() => (ItemDef)MemberwiseClone();
    }

    public interface IItemDefs { bool TryGet(int defId, out ItemDef def); }

    public sealed class ItemDefTable : IItemDefs
    {
        private readonly Dictionary<int, ItemDef> map = new Dictionary<int, ItemDef>();
        public ItemDefTable Add(ItemDef d)
        {
            if (d == null || d.Id <= 0 || string.IsNullOrWhiteSpace(d.Key) || d.MaxStack < 1 || d.BaseValueCents < 0 ||
                !Enum.IsDefined(typeof(ItemClass), d.Class) || d.ContainerSlots < 0 ||
                d.MaxStack > 1 && !ItemCatalog.Stackable(d.Class) ||
                d.Class == ItemClass.Cooler && (!d.TwoHanded || d.ContainerSlots != 8 || d.MaxStack != 1) ||
                d.Class != ItemClass.Cooler && (d.TwoHanded || d.ContainerSlots != 0) ||
                d.Class == ItemClass.Organ && !Enum.IsDefined(typeof(OrganKind), d.Organ))
                throw new ArgumentException("Invalid item definition", nameof(d));
            map.Add(d.Id, d.Copy()); return this;
        }
        public bool TryGet(int defId, out ItemDef def) { bool found = map.TryGetValue(defId, out var value); def = value?.Copy(); return found; }
        public IEnumerable<ItemDef> All { get { foreach (var d in map.Values) yield return d.Copy(); } }
    }

    /// <summary>Organ-only state. Provenance is copied at extraction and never changes.</summary>
    [Serializable]
    public sealed class OrganData
    {
        public OrganKind Kind;
        public int Tier = Core.Tier.Acceptable;
        public double Progress;          // 0..1 toward the next one-grade loss (kept across moves, ops T-05)
        public double SettledAt;         // active-world seconds when Tier/Progress were last brought up to date
        public string DonorPatientId = "";  // PatientId minted at knockdown
        public string DonorPersonId = "";   // stable PersonId of an authored unique NPC, "" for crowd NPCs
        public string DonorRoleKey = "";    // e.g. "HAMLET_BODYBUILDER" lineage key; the twin shares it
        public string DonorNpcType = "";
        public string DonorDistrict = "";
        public long ExtractedAtGameSeconds; // world clock (game time) for receipts/flavour
        public bool Packaged;
        // Cold chain (sales: delivered cooled vs -10%).
        public double ColdSince = -1;    // active seconds when the current cold stint began, -1 when warm
        public double LastColdStint;     // length of the last finished cold stint
        public double WarmSince = -1;    // active seconds when it last left cold storage, -1 = never cold
        public bool CaseColdLatch;       // set when loaded into a BuyerCase, cleared when it leaves the case
        public double LastImpactAt = -1e9;
        public OrganData Copy() => (OrganData)MemberwiseClone();
    }

    /// <summary>Fill state of syringes, vials and blood bags.</summary>
    [Serializable]
    public sealed class FillData
    {
        public float Amount;             // portions (blood) or abstract units (anesthesia)
        public int Formula;              // anesthesia formula tier 0..2
        public string DonorPatientId = "";
        public double FilledAt = -1;     // active seconds when unsealed syringe blood was drawn (ops T-06 expiry)
        public int FillSeq;              // blood syringe: +1 per filling; sale identity of syringe blood = "{itemId}#{FillSeq}"
        public double AgeAtAnchor;       // migration: elapsed blood age when active clock starts at zero
        public FillData Copy() => (FillData)MemberwiseClone();
    }

    [Serializable]
    public sealed class ItemRecord
    {
        public string Id = "";
        public int DefId;
        public int Count = 1;
        public PlaceKind Place;
        public string ContainerId = "";
        public int Slot = -1;
        public string CarrierId = "";
        public bool HasOrgan;            // JsonUtility cannot store null; flags say which block is valid
        public OrganData Organ = new OrganData();
        public bool HasFill;
        public FillData Fill = new FillData();
        public long Revision;
        public ItemRecord Copy()
        {
            var c = (ItemRecord)MemberwiseClone();
            c.Organ = Organ.Copy(); c.Fill = Fill.Copy();
            return c;
        }
    }

    [Serializable]
    public sealed class ContainerRecord
    {
        public string Id = "";
        public ContainerKind Kind;
        public string OwnerId = "";      // player id, cooler item id, meeting id, base id, order id
        public int Capacity;
        public bool Open = true;         // coolers/fridges/cases must be open for hand transfers
        public bool Powered = true;      // fridges only
        public bool UpgradePurchased = true; // false for van shelf/mounts until host purchases the shared upgrade
        public string[] Slots = new string[0];
        public ContainerRecord Copy() { var c = (ContainerRecord)MemberwiseClone(); c.Slots = (string[])Slots.Clone(); return c; }
    }

    /// <summary>Destination of a move request.</summary>
    public struct Destination
    {
        public PlaceKind Place;
        public string ContainerId;
        public int Slot;                 // -1 = first free (or first mergeable stack)
        public string CarrierId;
        public static Destination ToContainer(string id, int slot = -1) => new Destination { Place = PlaceKind.Container, ContainerId = id, Slot = slot };
        public static Destination ToWorld() => new Destination { Place = PlaceKind.World, Slot = -1 };
        public static Destination ToCarry(string playerId) => new Destination { Place = PlaceKind.Carried, CarrierId = playerId, Slot = -1 };
    }

    /// <summary>All tunable placeholders in one place (economy/feel pass later).</summary>
    [Serializable]
    public sealed class WorkItemTuning
    {
        public int PocketSlots = 6;
        public int CoolerSlots = 8;          // OPERATIONS §13.2
        public int FridgeSlots = 24;         // OPERATIONS §13.2
        public double RoomSecondsPerGrade = 300;     // 5 active minutes (OPERATIONS §13.2)
        public double CoolerSecondsPerGrade = 1500;  // 25 active minutes
        public double MinColdStintSeconds = 60;      // flash-cooling right before the case does not count
        public double MaxWarmGapSeconds = 60;        // hand carry from the cooler to the case
        public int KitEntries = 12; // G39 provisional bound; one hotbar key, NOT extra organ pockets
        public double ImpactCooldownSeconds = 0.6;
        public double OrganImpactSpeed = 2.4;
        public double CoolerImpactSpeed = 4;
        public double BloodExpirySeconds = 120;
        public double HoldTimeoutSeconds = 0.5;
        public double TieHoldSeconds = 1;
        public double BloodHoldSeconds = 4.5;
        public double PackHoldSeconds = 1;
        public double TransferHoldSeconds = 1.2;
        public double RefillHoldSeconds = 1;
        public float SyringeCapacity = 3; // existing OperationTuning
        public float InjectionUnitsPerSecond = 0.5f;
        public WorkItemTuning Copy() => (WorkItemTuning)MemberwiseClone();
        public void Validate()
        {
            if (PocketSlots != 6 || CoolerSlots != 8 || FridgeSlots != 24 || KitEntries < 1 || KitEntries > 64 ||
                !Positive(RoomSecondsPerGrade) || !Positive(CoolerSecondsPerGrade) || !Positive(MinColdStintSeconds) ||
                !Positive(MaxWarmGapSeconds) || !Positive(ImpactCooldownSeconds) || !Positive(OrganImpactSpeed) ||
                !Positive(CoolerImpactSpeed) || !Positive(BloodExpirySeconds) || !Positive(HoldTimeoutSeconds) ||
                !Positive(TieHoldSeconds) || !Positive(BloodHoldSeconds) || !Positive(PackHoldSeconds) ||
                !Positive(TransferHoldSeconds) || !Positive(RefillHoldSeconds) || !Positive(SyringeCapacity) || !Positive(InjectionUnitsPerSecond))
                throw new ArgumentException("Invalid inventory tuning");
        }
        private static bool Positive(double v) => v > 0 && !double.IsInfinity(v) && !double.IsNaN(v);
        public double SecondsPerGrade(StorageClass s) =>
            s == StorageClass.FridgePowered ? double.PositiveInfinity :
            s == StorageClass.PortableCooler ? CoolerSecondsPerGrade : RoomSecondsPerGrade;
        public static bool IsCold(StorageClass s) => s == StorageClass.PortableCooler || s == StorageClass.FridgePowered;
    }

    /// <summary>Raised by the ledger so the server adapter can re-quote buyers and refresh views.</summary>
    public struct TierChange { public string ItemId; public int From; public int To; public double At; }

    public struct MoveResult
    {
        public ItemError Error; public string ItemId; public int Slot;
        public string Effect; public double Amount; public string TargetId;
        public bool Replayed;
        public bool Ok => Error == ItemError.None;
        public static MoveResult Fail(ItemError e) => new MoveResult { Error = e, Slot = -1 };
    }
}
