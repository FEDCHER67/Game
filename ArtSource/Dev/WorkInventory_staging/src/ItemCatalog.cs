using System;

namespace OnlyVolunteers.Items.Core
{
    public static class ItemCatalog
    {
        public static bool Stackable(ItemClass c) => c == ItemClass.ZipTies || c == ItemClass.OrganPouch ||
            c == ItemClass.EmptyBloodBag || c == ItemClass.BodyBag || c == ItemClass.HeadBag;
        public static bool HasFill(ItemClass c) => c == ItemClass.BloodBag || c == ItemClass.BloodSyringe ||
            c == ItemClass.AnesthesiaSyringe || c == ItemClass.AnestheticVial;
        // The first five groups implement Fedya's explicit order. Additional supplies follow them.
        public static int KitOrder(ItemClass c)
        {
            switch (c)
            {
                case ItemClass.ZipTies: return 0;
                case ItemClass.AnesthesiaSyringe: return 1;
                case ItemClass.BloodSyringe: return 2;
                case ItemClass.EmptyBloodBag: return 3;
                case ItemClass.BloodBag: return 4;
                case ItemClass.BodyBag: return 5;
                case ItemClass.OrganPouch: return 6;
                case ItemClass.HeadBag: return 7;
                case ItemClass.AnestheticVial: return 8;
                default: return -1;
            }
        }
        public static ItemDefTable CreateDefaults()
        {
            var t = new ItemDefTable();
            void Add(int id, string key, ItemClass cls, int stack = 1, long cents = 0, OrganKind organ = default) =>
                t.Add(new ItemDef { Id = id, Key = key, Class = cls, MaxStack = stack, BaseValueCents = cents,
                    Organ = organ, TwoHanded = cls == ItemClass.Cooler, ContainerSlots = cls == ItemClass.Cooler ? 8 : 0 });
            Add(101, "organ.heart", ItemClass.Organ, cents:100000, organ:OrganKind.Heart);
            Add(102, "organ.kidney", ItemClass.Organ, cents:25000, organ:OrganKind.Kidney);
            Add(103, "organ.liver", ItemClass.Organ, cents:35000, organ:OrganKind.Liver);
            Add(104, "organ.lungs", ItemClass.Organ, cents:45000, organ:OrganKind.Lungs);
            Add(105, "organ.brain", ItemClass.Organ, cents:120000, organ:OrganKind.Brain);
            Add(106, "organ.eye", ItemClass.Organ, cents:20000, organ:OrganKind.Eye);
            Add(109, "blood.intro_syringe", ItemClass.BloodSyringe, cents:1000);
            Add(110, "blood.bag", ItemClass.BloodBag, cents:5000);
            Add(111, "tool.blood_syringe", ItemClass.BloodSyringe);
            Add(112, "tool.anesthesia_syringe", ItemClass.AnesthesiaSyringe);
            Add(113, "supply.anesthetic_vial", ItemClass.AnestheticVial, cents:20000);
            Add(114, "supply.zip_ties", ItemClass.ZipTies, 20, 1000);
            Add(115, "supply.organ_pouch", ItemClass.OrganPouch, 10, 1000);
            Add(116, "supply.empty_blood_bag", ItemClass.EmptyBloodBag, 10, 500);
            Add(117, "supply.head_bag", ItemClass.HeadBag, 5, 1000);
            Add(201, "tool.scalpel", ItemClass.Tool, cents:40000);
            Add(202, "supply.body_bag", ItemClass.BodyBag, 5);
            Add(301, "container.cooler", ItemClass.Cooler, cents:100000);
            return t;
        }
        // Caller supplies the body's already-degraded tier. This only carries its unfinished interval.
        public static double CorpseProgress(double elapsedSinceDeath, double grace = 45, double interval = 40)
        {
            if (!Finite(elapsedSinceDeath) || elapsedSinceDeath < 0 || !Finite(grace) || grace < 0 || !Finite(interval) || interval <= 0)
                throw new ArgumentOutOfRangeException(nameof(elapsedSinceDeath));
            return elapsedSinceDeath <= grace ? 0 : ((elapsedSinceDeath - grace) % interval) / interval;
        }
        public static bool Finite(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
        public static string OrderSource(OrganData o) => string.IsNullOrEmpty(o.DonorRoleKey) ? o.DonorPatientId : o.DonorRoleKey;
        public static bool MatchesOrder(OrganData o, string source, string npcType, OrganKind kind, int minimumTier, bool packaging) =>
            o != null && !string.IsNullOrEmpty(source) && OrderSource(o) == source && o.DonorNpcType == npcType &&
            o.Kind == kind && o.Tier >= minimumTier && (!packaging || o.Packaged);
    }
}
