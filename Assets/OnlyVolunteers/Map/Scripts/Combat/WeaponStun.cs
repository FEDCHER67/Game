using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Where a hit landed on an NPC. Picked in the NPC's own space (root at the feet, body along local up), so it works the
    // same on a standing, a lying and a sitting NPC. Forgiving on purpose (Fedya's playtest, 2026-10-05: the head was a
    // tiny target): the upper third of the body is the head, and so is anything the swing passes within HeadReach of
    // the head centre; the middle third is the torso, the lower third the limbs.
    public enum HitZone : byte { Head, Torso, Limb }

    public static class HitZones
    {
        public const float HeadShare = 2f / 3f;   // above this share of the body height: head
        public const float TorsoShare = 1f / 3f;  // above this: torso, below: limbs
        public const float HeadReach = 0.45f;     // m from the head centre that still counts as a head hit
        public const float HeadCentreBelowTop = 0.15f;

        /// <summary>Zone from the height above the feet (NPC space, standing body) and the distance of the swing from the
        /// head centre (infinity when unknown).</summary>
        public static HitZone Classify(float height, float bodyHeight, float headDistance = float.PositiveInfinity)
        {
            if (height >= bodyHeight * HeadShare || headDistance <= HeadReach) return HitZone.Head;
            return height >= bodyHeight * TorsoShare ? HitZone.Torso : HitZone.Limb;
        }
    }

    // How long a weapon stuns (NPC capture stage 1, canon section 151): a base duration, a multiplier per hit zone and a
    // random spread. The player never sees seconds, only Strength: 1-5 dots from the mean duration over the three zones.
    // The field defaults are the fist (Q) of before 30.10; WeaponStun.Fist is the fist built in code for scenes without the
    // asset (Map/Data/Fist.asset, made by MapGreyboxBuilder) and ConfigureAsFist gives it the fist's own anti-spam tuning
    // (Fedya 30.10, initial values delegated): a 1.0 s swing cooldown and the repeat-contact stun table, which the field
    // defaults leave off so a future weapon does not inherit them by accident.
    [CreateAssetMenu(menuName = "VOLUNTEERS ONLY/Weapon Stun")]
    public sealed class WeaponStun : ScriptableObject
    {
        [Tooltip("Stun in seconds for a torso-like hit, before the zone multiplier.")]
        public float BaseSeconds = 8f;
        public float HeadMul = 1.5f;
        public float TorsoMul = 1f;
        public float LimbMul = 0.5f;
        [Tooltip("Random spread of every stun, as a fraction (0.15 = +-15%).")]
        [Range(0f, 0.5f)] public float Spread = 0.15f;
        [Tooltip("Seconds between two swings.")]
        public float Cooldown = 0.6f;
        [Tooltip("Metres from the eye (first person) or the body (third person).")]
        public float Reach = 2f;

        [Header("Repeat contacts (fist anti-spam, Fedya 30.10)")]
        [Tooltip("Share of the normal stun of the 1st, 2nd, ... successful contact on the same NPC in one sequence (every " +
                 "attacker counts on the same NPC); the last value repeats. Empty = every contact stuns fully. The fist: " +
                 "1, 0.7, 0.45, 0.25, 0.1, 0.")]
        public float[] RepeatMultipliers = new float[0];
        [Tooltip("The NPC's sequence starts over after this many active seconds without a contact, once it has no stun and " +
                 "no get-up left.")]
        public float RepeatRecoverySeconds = OnlyVolunteers.Capture.FistResistanceRulesV01.DefaultRecoverySeconds;

        private static WeaponStun _fist;

        /// <summary>The fist with the default numbers, made once in code (not an asset, never saved).</summary>
        public static WeaponStun Fist
        {
            get
            {
                if (_fist != null) return _fist;
                _fist = CreateInstance<WeaponStun>();
                _fist.name = "Fist (code)";
                _fist.hideFlags = HideFlags.DontSave;
                ConfigureAsFist(_fist);
                return _fist;
            }
        }

        /// <summary>The fist's own tuning on top of the field defaults (the code fallback and a freshly made Fist.asset):
        /// 1.0 s between accepted swings, the repeat-contact table 100/70/45/25/10/0 % and 8 s recovery.</summary>
        public static void ConfigureAsFist(WeaponStun w)
        {
            if (w == null) return;
            w.Cooldown = 1f;
            w.RepeatMultipliers = (float[])OnlyVolunteers.Capture.FistResistanceRulesV01.DefaultMultipliers.Clone();
            w.RepeatRecoverySeconds = OnlyVolunteers.Capture.FistResistanceRulesV01.DefaultRecoverySeconds;
        }

        public float Multiplier(HitZone zone) => zone switch
        {
            HitZone.Head => HeadMul,
            HitZone.Limb => LimbMul,
            _ => TorsoMul,
        };

        /// <summary>Stun seconds for one hit in this zone, spread included.</summary>
        public float Duration(HitZone zone) =>
            Mathf.Max(0.1f, BaseSeconds * Multiplier(zone) * (1f + Random.Range(-Spread, Spread)));

        /// <summary>Mean stun over head, torso and limbs, without spread: what the strength dots summarize.</summary>
        public float MeanSeconds => BaseSeconds * (HeadMul + TorsoMul + LimbMul) / 3f;

        /// <summary>1-5: under 4 s one dot, then 7, 10 and 14 s; the fist (8 s mean) has three.</summary>
        public int Strength
        {
            get
            {
                float mean = MeanSeconds;
                return mean < 4f ? 1 : mean < 7f ? 2 : mean < 10f ? 3 : mean < 14f ? 4 : 5;
            }
        }

        public string StrengthDots => new string('●', Strength) + new string('○', 5 - Strength);
    }
}
