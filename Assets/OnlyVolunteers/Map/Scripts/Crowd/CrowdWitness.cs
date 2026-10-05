using UnityEngine;

namespace OnlyVolunteers.Map.Crowd
{
    public enum CrowdRole : byte { Walker, Police }

    // One raised district alert (CrowdDirector.AlertRaised).
    public struct CrowdAlert
    {
        public int District, Level;
        public string DistrictId, DistrictName, Via;
        public NpcIncident Kind;
        public Vector3 Position;
        public CrowdWalker Reporter;
        public float Time;
    }

    // Who saw it. On every GreyboxNpc.Incident (a free NPC knocked down, an NPC loaded into a van) each crowd walker
    // checks: within its view range (day/evening), inside its view cone, a clear line from its eyes to the victim (NPC
    // bodies, players and the van do not block, buildings and terrain do). A walker that saw it reacts after a short
    // delay and runs to report (CrowdWalker.Witness); a police officer that saw it raises the alert on the spot.
    // Only what is really seen counts: the hotspots' expected eyes are planning estimates, not extra witnesses.
    public static class CrowdWitness
    {
        public static void Evaluate(CrowdDirector director, GreyboxNpc victim, NpcIncident kind)
        {
            if (director == null || victim == null || director.Map == null) return;
            Vector3 target = victim.Center;
            float range = director.ViewRange;
            float cos = Mathf.Cos(director.ViewHalfAngle * Mathf.Deg2Rad);
            int seen = 0;
            for (int i = director.Walkers.Count - 1; i >= 0; i--)
            {
                CrowdWalker w = director.Walkers[i];
                if (w == null || w.Npc == victim || !w.CanWitness) continue;
                float reach = w.Role == CrowdRole.Police ? range * director.PoliceRangeFactor : range;
                if (!Sees(w, target, reach, cos)) continue;
                seen++;
                w.Witness(kind, target);
            }
            if (seen > 0)
                Debug.Log($"[Crowd] {victim.name} {(kind == NpcIncident.Captured ? "captured" : "stunned")} at ({target.x:0}, {target.z:0}): {seen} witness(es)", victim);
        }

        public static bool Sees(CrowdWalker w, Vector3 target, float range, float cosHalfAngle)
        {
            Vector3 eye = w.Eye;
            Vector3 to = target - eye;
            float distance = to.magnitude;
            if (distance > range) return false;
            if (distance > 1.5f)
            {
                Vector3 flat = new(to.x, 0f, to.z);
                Vector3 forward = w.transform.forward;
                forward.y = 0f;
                // Lying on the beach: looks up, sees all around.
                if (!w.LyingDown && flat.sqrMagnitude > 1e-4f && Vector3.Dot(forward.normalized, flat.normalized) < cosHalfAngle) return false;
            }
            return !Physics.Linecast(eye, target, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore);
        }
    }
}
