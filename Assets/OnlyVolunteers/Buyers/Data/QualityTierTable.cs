using System;
using UnityEngine;

namespace OnlyVolunteers.Buyers.Data
{
    [CreateAssetMenu(menuName = "OnlyVolunteers/Buyers/Quality Tier Table")]
    public sealed class QualityTierTable : ScriptableObject
    {
        public int schemaVersion = 1;
        public string id;
        public QualityTierEntry[] tiers;
        public string[] authoringNotes;
    }

    [Serializable]
    public sealed class QualityTierEntry
    {
        public int tier;
        public string displayNameEn;
        public string displayNameRu;
        public string percentLabel;
        public float multiplier;
        public Color colour;
    }
}
