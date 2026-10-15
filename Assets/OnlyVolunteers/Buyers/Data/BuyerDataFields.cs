using System;

namespace OnlyVolunteers.Buyers.Data
{
    // Serialization contracts only. Evaluation and trading rules belong to Buyers/Core (G27).
    [Serializable]
    public sealed class MerchandiseDefinition
    {
        public string merchandiseId;
        [UnityEngine.Tooltip("Existing Inventory ItemDefinition.Id; 0 is explicitly unresolved, not a new ID.")]
        public int itemId;
        public bool itemIdUnresolved;
        public bool hasQuality;
        [UnityEngine.Tooltip("none, sealed_blood_bag, filled_syringe, or sealed_individual_organ_bag. These are packaging descriptors, not Inventory IDs.")]
        public string packaging;
        public bool introductoryOnly;
        public bool hagglingAllowed;
        public bool hasFixedBasePrice;
        public float fixedBasePriceDollars;
    }

    [Serializable]
    public sealed class WorkingHours
    {
        public bool allDay;
        public int startHour;
        public int endHour;
    }

    [Serializable]
    public sealed class UnlockCondition
    {
        [UnityEngine.Tooltip("Declarative all-of requirements; consumers must resolve every condition, including PLACEHOLDER IDs.")]
        public UnlockRequirement[] all;
    }

    [Serializable]
    public sealed class UnlockRequirement
    {
        [UnityEngine.Tooltip("contact_available, first_successful_blood_sale, respect_at_least, owns_tool, or district_access.")]
        public string kind;
        public string subjectId;
        public int minimumValue;
    }
}
