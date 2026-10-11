using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // Why a car stopped being after a suspect: Evaded = nobody saw it for EvadeTime and it was more than EvadeDistance from
    // every police car (the GTA-like rule); Base = it stayed inside its base's safe disc (canon 76: the car waited at the
    // edge, then left); Lost = a search or a response ran out on its own; CrewDown = the whole crew lies on the ground;
    // Ordered = the suspect is no longer wanted (cleared, arrested).
    public enum GiveUpCause : byte { Evaded, Base, Lost, CrewDown, Ordered }

    // What happened, for HUD, sounds, tests and later systems (an arrest scene, music, the network). Plain static events;
    // reset on every Play (no stale subscribers after a domain-reload-free enter).
    public static class PoliceEvents
    {
        /// <summary>A car started a pursuit of the van (or a suspect on foot).</summary>
        public static event System.Action<PoliceUnit> PursuitStarted;

        /// <summary>A car that had the suspect in sight gave up: why, and how far (m along the road) the suspect still was
        /// from the team's home base door at that moment (+inf when unknown; information only, no rule reads it).</summary>
        public static event System.Action<PoliceUnit, GiveUpCause, float> PursuitEnded;

        /// <summary>A bump worth a laugh: who, where, relative speed (m/s).</summary>
        public static event System.Action<PoliceUnit, Vector3, float> Slapstick;

        /// <summary>Three hits landed: the officer wants to arrest the pawn (placeholder: penalty + station respawn).</summary>
        public static event System.Action<GreyboxPawn, PoliceOfficer> ArrestRequested;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            PursuitStarted = null;
            PursuitEnded = null;
            Slapstick = null;
            ArrestRequested = null;
        }

        internal static void RaisePursuitStarted(PoliceUnit unit) => PursuitStarted?.Invoke(unit);
        internal static void RaisePursuitEnded(PoliceUnit unit, GiveUpCause cause, float metres) => PursuitEnded?.Invoke(unit, cause, metres);
        internal static void RaiseSlapstick(PoliceUnit unit, Vector3 where, float speed) => Slapstick?.Invoke(unit, where, speed);
        internal static void RaiseArrest(GreyboxPawn pawn, PoliceOfficer officer) => ArrestRequested?.Invoke(pawn, officer);
    }
}
