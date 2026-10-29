using System;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>
    /// Fist anti-spam (Fedya 30.10, initial tuning delegated): repeated fist contacts on the same NPC stun less and less.
    /// Plain data on the NPC (GreyboxNpc.Fist), shared by every attacker: the number of successful fist contacts in the
    /// current sequence and the active game seconds since the last one. Saved with a captured NPC (CaptureNpcSave) as
    /// remaining active seconds, never as an absolute clock.
    /// </summary>
    [Serializable]
    public struct FistResistanceV01
    {
        /// <summary>Successful fist contacts in the current sequence (0 = fresh: the next contact is the first).</summary>
        public int contacts;
        /// <summary>Active game seconds since the last successful contact.</summary>
        public float quietSeconds;
    }

    /// <summary>What one authorised fist contact did (the NPC's answer to the hit path).</summary>
    public struct FistContactV01
    {
        /// <summary>1-based place of this contact in the NPC's sequence.</summary>
        public int Index;
        /// <summary>Share of the normal stun this contact gave (the table's value).</summary>
        public float Multiplier;
        /// <summary>Stun seconds this contact contributed (normal weapon/zone/spread result x multiplier; 0 = none).</summary>
        public float Stun;
        /// <summary>The contact knocked the NPC down / re-stunned it (false for a zero-stun contact).</summary>
        public bool Stunned;
    }

    /// <summary>
    /// Pure rules of the fist's repeat resistance. The sequence advances only on a successful, authorised contact (never
    /// on a miss, a rejected or duplicate request or a presentation callback). It starts over only when BOTH hold: at
    /// least RecoverySeconds of active time without a contact, and the NPC has no stun and no get-up left. Each contact's
    /// stun = the normal weapon/zone/spread result x the table value (the last value repeats: 0 from the sixth on).
    /// </summary>
    public static class FistResistanceRulesV01
    {
        public static readonly float[] DefaultMultipliers = { 1f, 0.7f, 0.45f, 0.25f, 0.1f, 0f };
        public const float DefaultRecoverySeconds = 8f;

        /// <summary>Multiplier of the index-th contact (1-based); the last table value repeats; no table = 1.</summary>
        public static float Multiplier(int index, float[] table)
        {
            if (table == null || table.Length == 0) return 1f;
            int i = Mathf.Clamp(index - 1, 0, table.Length - 1);
            return Mathf.Max(0f, table[i]);
        }

        /// <summary>Per frame (and before every contact): active time passes; a quiet, recovered NPC starts over.
        /// <paramref name="busy"/>: stun left or a get-up still running.</summary>
        public static void Tick(ref FistResistanceV01 s, float dt, bool busy, float recoverySeconds)
        {
            if (s.contacts <= 0) { s.contacts = 0; return; }
            if (dt > 0f && !float.IsNaN(dt)) s.quietSeconds += dt;
            if (!busy && s.quietSeconds >= Mathf.Max(0f, recoverySeconds)) { s.contacts = 0; s.quietSeconds = 0f; }
        }

        /// <summary>One successful, authorised contact: recovery is checked first (without advancing time), then the
        /// sequence advances and the quiet time restarts (also when the multiplier is already 0). Returns the multiplier.</summary>
        public static float Contact(ref FistResistanceV01 s, bool busy, float recoverySeconds, float[] table, out int index)
        {
            Tick(ref s, 0f, busy, recoverySeconds);
            s.contacts = Mathf.Max(0, s.contacts) + 1;
            s.quietSeconds = 0f;
            index = s.contacts;
            return Multiplier(index, table);
        }

        /// <summary>The stun left after a contribution (the existing non-additive rule): a positive contribution raises the
        /// remaining stun to it when longer, never shortens it; a zero contribution changes nothing.</summary>
        public static float StunAfter(float stunLeft, float contribution) =>
            contribution > 0f ? Mathf.Max(stunLeft, contribution) : stunLeft;

        /// <summary>Whether a contact with this contribution knocks down / re-stuns (a zero one never restarts a knockdown,
        /// a get-up or the stun phase).</summary>
        public static bool Stuns(float contribution) => contribution > 0f;

        /// <summary>Save form: remaining active seconds until the quiet-time half of the recovery is met.</summary>
        public static float RecoverLeft(in FistResistanceV01 s, float recoverySeconds) =>
            s.contacts > 0 ? Mathf.Max(0f, recoverySeconds - s.quietSeconds) : 0f;

        /// <summary>From the save (missing fields in an older save read as 0 = a fresh sequence).</summary>
        public static FistResistanceV01 FromSave(int contacts, float recoverLeft, float recoverySeconds) => contacts > 0
            ? new FistResistanceV01 { contacts = contacts, quietSeconds = Mathf.Clamp(recoverySeconds - Mathf.Max(0f, recoverLeft), 0f, recoverySeconds) }
            : default;
    }

    public enum FistSwingResult : byte { Accepted, CoolingDown, Duplicate }

    /// <summary>
    /// One player's fist swing gate on the authority: one cooldown across every target, measured between accepted swing
    /// starts in active game time. A swing that misses still consumes it; presses during the cooldown are dropped (never
    /// queued). Every request carries an id from that player's increasing counter: a repeated or older id is a replay and
    /// returns the outcome recorded for it (or Duplicate when it is no longer remembered) with replay = true; the caller
    /// never swings for a replay.
    /// </summary>
    public sealed class FistSwingGateV01
    {
        private const int Remember = 8;
        private readonly uint[] ids = new uint[Remember];
        private readonly FistSwingResult[] results = new FistSwingResult[Remember];
        private int count;
        private uint lastId;
        private bool any;
        private float next = float.NegativeInfinity;
        private uint issued;

        /// <summary>Game time the next swing may start.</summary>
        public float NextAllowed => next;

        /// <summary>The local player's next request id (solo / host input).</summary>
        public uint NextRequestId() => ++issued;

        /// <summary>True only for a fresh request that may swing now.</summary>
        public bool TryAccept(uint requestId, float now, float cooldown) =>
            Request(requestId, now, cooldown, out bool replay) == FistSwingResult.Accepted && !replay;

        public FistSwingResult Request(uint requestId, float now, float cooldown, out bool replay)
        {
            replay = any && requestId <= lastId;
            if (replay)
            {
                for (int i = 0; i < count; i++) if (ids[i] == requestId) return results[i];
                return FistSwingResult.Duplicate;
            }
            any = true;
            lastId = requestId;
            FistSwingResult r;
            if (now < next) r = FistSwingResult.CoolingDown;
            else
            {
                next = now + Mathf.Max(0f, cooldown);
                r = FistSwingResult.Accepted;
            }
            int slot = count < Remember ? count++ : (int)(requestId % Remember);
            ids[slot] = requestId;
            results[slot] = r;
            return r;
        }
    }
}
