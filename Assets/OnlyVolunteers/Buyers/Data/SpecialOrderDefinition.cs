using UnityEngine;

namespace OnlyVolunteers.Buyers.Data
{
    [CreateAssetMenu(menuName = "OnlyVolunteers/Buyers/Special Order Definition")]
    public sealed class SpecialOrderDefinition : ScriptableObject
    {
        public int schemaVersion = 1;
        public string id;
        public string displayNameRu;
        public string displayNameEn;
        public string offeringBuyerId;
        public bool availableInFirstVersion;
        public string targetNpcTypeId;
        [Tooltip("The order instance must bind the individual NPC from its clue; type alone is insufficient.")]
        public bool requiresClueTargetIdentity;
        public int organItemId;
        public int minimumTier;
        public string packaging;
        [Tooltip("Active-world game hours, counted after haggling and explicit acceptance.")]
        public int deadlineGameHours;
        [Tooltip("Fractional premium: 0.25 means +25%, not 25x.")]
        public float premium;
        public string[] clueTextIds;
        public string cluePhotoId;
        public string stashId;
        public UnlockCondition unlockCondition;
        public string[] authoringNotes;
    }
}
