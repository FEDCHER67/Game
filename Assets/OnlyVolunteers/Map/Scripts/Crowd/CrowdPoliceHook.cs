using UnityEngine;

namespace OnlyVolunteers.Map.Crowd
{
    // Placeholder for the police reaction to a district alert: logs what officers would do. Replace with real behaviour
    // (officers heading for the alert, searching, chasing the van) when police gameplay is designed.
    public sealed class CrowdPoliceHook : MonoBehaviour
    {
        private void OnEnable() => CrowdDirector.AlertRaised += React;

        private void OnDisable() => CrowdDirector.AlertRaised -= React;

        private void React(CrowdAlert alert)
        {
            CrowdDirector director = CrowdDirector.Instance;
            int officers = 0;
            if (director != null)
                foreach (CrowdWalker w in director.Walkers)
                    if (w.Role == CrowdRole.Police) officers++;
            Debug.Log($"[Crowd] police hook (placeholder): alert {alert.DistrictId} level {alert.Level}; {officers} officer(s) on foot would " +
                      $"respond to ({alert.Position.x:0}, {alert.Position.z:0}). No police behaviour yet.", this);
        }
    }
}
