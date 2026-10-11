using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // District theme -> kit; roles a district kit lacks come from the default kit.
    [CreateAssetMenu(menuName = "OnlyVolunteers/Map/Facade Kit Set (style v3)", fileName = "FacadeKitSet")]
    public sealed class FacadeKitSet : ScriptableObject
    {
        public FacadeKit Default;
        public List<DistrictKit> Districts = new();

        public FacadeKit For(string district)
        {
            foreach (DistrictKit d in Districts)
                if (d != null && d.District == district && d.Kit != null)
                    return d.Kit;
            return Default;
        }
    }

    [Serializable]
    public sealed class DistrictKit
    {
        public string District;
        public FacadeKit Kit;
    }
}
