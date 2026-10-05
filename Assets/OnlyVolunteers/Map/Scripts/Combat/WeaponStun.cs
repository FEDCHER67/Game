using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Where a hit landed on an NPC. Picked from the height of the hit point in the NPC's own space (root at the feet, body
    // along local up), so it works the same on a standing, a lying and a sitting NPC (HitZones.FromLocalHeight).
    public enum HitZone : byte { Head, Torso, Limb }

    public static class HitZones
    {
        public const float HeadAbove = 1.2f;  // m above the feet, NPC-local
        public const float TorsoAbove = 0.6f;

        public static HitZone FromLocalHeight(float height) =>
            height > HeadAbove ? HitZone.Head : height >= TorsoAbove ? HitZone.Torso : HitZone.Limb;
    }

    // How long a weapon stuns (NPC capture stage 1, canon section 151): a base duration, a multiplier per hit zone and a
    // random spread. The player never sees seconds, only Strength: 1-5 dots from the mean duration over the three zones.
    // The field defaults are the fist (Q); WeaponStun.Fist is the same fist built in code for scenes without the asset
    // (Map/Data/Fist.asset, made by MapGreyboxBuilder).
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
                return _fist;
            }
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
