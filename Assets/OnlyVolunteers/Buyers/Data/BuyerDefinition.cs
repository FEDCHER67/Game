using UnityEngine;

namespace OnlyVolunteers.Buyers.Data
{
    [CreateAssetMenu(menuName = "OnlyVolunteers/Buyers/Buyer Definition")]
    public sealed class BuyerDefinition : ScriptableObject
    {
        public int schemaVersion = 1;
        public string id;
        public string displayNameRu;
        public string displayNameEn;
        public MerchandiseDefinition[] acceptedMerchandise;
        [Tooltip("1..5 for organs; 0 means not applicable to blood, never an organ tier.")]
        public int minimumTier;
        public WorkingHours workingHours;
        [Tooltip("base or point; presentation resolves an authored location.")]
        public string meetingType;
        public bool saturationEnabled;
        public string voiceId;
        public UnlockCondition unlockCondition;
        public string[] textIds;
        public string[] authoringNotes;
    }
}
