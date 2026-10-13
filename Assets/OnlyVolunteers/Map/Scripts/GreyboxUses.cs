using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    /// <summary>An extra E action for the on-foot pawn, offered by another system (the Field Clinic's operating table).
    /// GreyboxInteractor stays the only E handler: it asks these right after the cargo bay's inside handle, and the first
    /// one that offers an action gets the key and shows its label in the same hint line.</summary>
    public interface IGreyboxUse
    {
        bool Offer(GreyboxPawn pawn, out string label);
        void Use(GreyboxPawn pawn);
    }

    public static class GreyboxUses
    {
        public static readonly List<IGreyboxUse> All = new();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();
    }
}
