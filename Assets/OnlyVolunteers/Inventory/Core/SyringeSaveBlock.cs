using System;
using System.Collections.Generic;

namespace OnlyVolunteers.Inventory
{
    [Serializable]
    public sealed class SyringeWorldSave
    {
        public int DefinitionId;
        public SyringeInstance Item;
        public float X, Y, Z;
        public float Qx, Qy, Qz, Qw = 1;
    }
    /// <summary>Embed once in the existing team save. No balance, cash migration or offline clock.</summary>
    [Serializable]
    public sealed class SyringeSaveBlock
    {
        public int Version = 1;
        public List<SyringeInstance> Items = new List<SyringeInstance>();
        public List<SyringeWorldSave> WorldItems = new List<SyringeWorldSave>();
        public SyringeSalesSave Sales = new SyringeSalesSave();
        public DailySyringeFindSave Daily = new DailySyringeFindSave();
        // Missing history is never silently promoted to a new syringe.
        public static SyringeInstance Legacy(string itemId, SyringeKind kind, string provenPersonId = null) =>
            new SyringeInstance { ItemId = itemId, Kind = kind, PersonId = provenPersonId ?? "", LegacyUnknown = string.IsNullOrWhiteSpace(provenPersonId) };
    }
}
