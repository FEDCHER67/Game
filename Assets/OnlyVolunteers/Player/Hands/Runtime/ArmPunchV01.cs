using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    public enum PunchPhaseV01 : byte { None, Windup, Strike, Contact, Retract }

    /// <summary>
    /// One accepted Q swing as presentation data (Fedya 30.10): who swung which arm, whether the existing authoritative hit
    /// path confirmed a contact, and where (the hit point, or the end of the swing for a miss) as a world offset from the
    /// swinger's feet. The game rules never read it: the hit, the stun and every consequence stay in the existing
    /// interactor / NPC code. Sequence is the swinger's own counter: one accepted swing = one cue = one burst of stars on
    /// every machine (PunchLedgerV01 drops repeats).
    /// </summary>
    public struct PunchCueV01
    {
        public ushort Sequence;
        /// <summary>0 right, 1 left (StretchArmRigV01.Side).</summary>
        public byte Side;
        public bool Landed;
        /// <summary>0..1: the share of a full stun the contact produced (smaller star burst for a weak repeat hit).</summary>
        public float Strength;
        public Vector3 Offset;
    }

    /// <summary>
    /// The punch's key poses in time (no clock: t = seconds since the swing was accepted). Anticipation (the fist cocks
    /// back), strike (out to the target), contact (a short hold where the stars burst), retract (back to what the arm did
    /// before). The whole swing is shorter than the fist cooldown, so swings never overlap.
    /// </summary>
    public static class ArmPunchV01
    {
        public const float Windup = 0.07f, Strike = 0.07f, Contact = 0.07f, Retract = 0.24f;
        public const float Duration = Windup + Strike + Contact + Retract;
        /// <summary>When the fist arrives: the stars of a landed hit burst here.</summary>
        public const float ContactTime = Windup + Strike;

        public static PunchPhaseV01 Phase(float t)
        {
            if (float.IsNaN(t) || t < 0f || t >= Duration) return PunchPhaseV01.None;
            if (t < Windup) return PunchPhaseV01.Windup;
            if (t < ContactTime) return PunchPhaseV01.Strike;
            if (t < ContactTime + Contact) return PunchPhaseV01.Contact;
            return PunchPhaseV01.Retract;
        }

        public static bool Active(float t) => Phase(t) != PunchPhaseV01.None;

        /// <summary>Where the fist is along its path: 0 = where the arm was (start / end), Cock = pulled back, 1 = the strike
        /// end. Windup eases from 0 to the cock, the strike snaps out (ease-out with a little overshoot), contact recoils a
        /// touch, retract eases home.</summary>
        public static void Pose(float t, out float fromStart, out float cock, out float strike)
        {
            fromStart = 0f; cock = 0f; strike = 0f;
            switch (Phase(t))
            {
                case PunchPhaseV01.Windup:
                {
                    float u = ArmStretchMath.SmoothStep(t / Windup);
                    cock = u; fromStart = 1f - u; break;
                }
                case PunchPhaseV01.Strike:
                {
                    float u = (t - Windup) / Strike;
                    float e = 1f - (1f - u) * (1f - u) * (1f - u); // ease-out cubic
                    strike = e * 1.06f;
                    cock = 1f; break;
                }
                case PunchPhaseV01.Contact:
                {
                    float u = (t - ContactTime) / Contact;
                    strike = Mathf.Lerp(1.06f, 0.97f, ArmStretchMath.SmoothStep(u));
                    cock = 1f; break;
                }
                case PunchPhaseV01.Retract:
                {
                    float u = ArmStretchMath.SmoothStep((t - ContactTime - Contact) / Retract);
                    strike = 0.97f * (1f - u); fromStart = u; cock = 1f - u; break;
                }
            }
        }

        /// <summary>Blends the three key points by <see cref="Pose"/>: the back point (start/cock mix) toward the strike
        /// point by the strike share; continuous over every phase boundary. The strike's overshoot (share up to 1.06) pushes
        /// a little past the strike point along cock → strike.</summary>
        public static Vector3 Blend(float t, Vector3 start, Vector3 cockPoint, Vector3 strikePoint)
        {
            Pose(t, out float a, out float c, out float s);
            float rest = 1f - s;
            float sum = a + c;
            Vector3 back = sum > 1e-5f ? (start * a + cockPoint * c) / sum : start;
            return back * rest + strikePoint * s;
        }

        /// <summary>How tightly the fist is closed (fist through the strike, opening a little on the way home).</summary>
        public static float Curl(float t) => Phase(t) == PunchPhaseV01.Retract
            ? Mathf.Lerp(1f, 0.6f, (t - ContactTime - Contact) / Retract) : 1f;
    }

    /// <summary>Receiver side of the punch cue: one per swinger. Accepts a sequence once; a repeat or an older one (the
    /// unsigned 16-bit counter wraps) is dropped, so a duplicate packet never doubles the stars.</summary>
    public sealed class PunchLedgerV01
    {
        private bool any;
        private ushort last;

        public bool Accept(ushort sequence)
        {
            if (any && (short)(sequence - last) <= 0) return false;
            any = true;
            last = sequence;
            return true;
        }

        public void Reset() { any = false; last = 0; }
    }

    /// <summary>
    /// First-person hands visibility (Fedya 30.10): no idle hands. The right hand shows while it holds a one-hand item (or
    /// is part of a two-hand hold); the left only during a two-hand hold; the punching arm shows for its swing. Third
    /// person is not affected (friends always see both arms).
    /// </summary>
    public static class FirstPersonHandsRuleV01
    {
        /// <param name="punchSide">-1 no punch, 0 right, 1 left.</param>
        public static void Engaged(bool rightHolds, bool leftHolds, bool twoHanded, int punchSide, out bool right, out bool left)
        {
            bool two = twoHanded && rightHolds && leftHolds;
            right = rightHolds || punchSide == 0;
            left = two || punchSide == 1;
        }

        /// <summary>Which arm swings: the right, unless it holds a one-hand item and the left is free (then the left, so
        /// the item stays in the right hand). In a two-hand hold the right lets go for the swing and comes back.</summary>
        public static int PunchSide(bool rightHolds, bool leftHolds, bool twoHanded)
        {
            bool two = twoHanded && rightHolds && leftHolds;
            if (two) return 0;
            if (rightHolds && !leftHolds) return 1;
            return 0;
        }
    }
}
