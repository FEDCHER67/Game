using System;
using UnityEngine;

namespace OnlyVolunteers.Buyers.Data
{
    [CreateAssetMenu(menuName = "OnlyVolunteers/Buyers/Respect Level Table")]
    public sealed class RespectLevelTable : ScriptableObject
    {
        public int schemaVersion = 1;
        public string id;
        public int minimum;
        public int maximum;
        public int initialValue;
        public RespectLevelEntry[] levels;
    }

    [Serializable]
    public sealed class RespectLevelEntry
    {
        public int level;
        public string displayNameRu;
        public string displayNameEn;
        public int minimumInclusive;
        public int maximumInclusive;
    }
}
