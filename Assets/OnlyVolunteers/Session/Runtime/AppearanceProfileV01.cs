using System;
using OnlyVolunteers.Economy;
using UnityEngine;

namespace OnlyVolunteers.Session
{
    /// <summary>
    /// The local player's own look, stored on HIS machine (PlayerPrefs) under his stable player GUID
    /// (TeamEconomy.LocalPlayerGuid; "-player-guid" builds on one PC keep separate looks). It is never part of the shared
    /// world economy and never copied from the host: every join sends it (NetworkPlayer), so joining a friend's world uses
    /// the joiner's own appearance and a reconnect brings back the same one. A missing/old/unknown value loads as the
    /// sanitized default.
    /// </summary>
    public static class AppearanceProfileV01
    {
        public static event Action<PlayerAppearance> Changed;

        /// <summary>Server side, this session: the accepted looks by stable participant id (reset with the domain).</summary>
        public static AppearanceBook ServerBook { get; private set; } = new AppearanceBook();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { Changed = null; ServerBook = new AppearanceBook(); }

        static string Key => AppearanceRules.ProfileKey(TeamEconomy.LocalPlayerGuid);

        public static bool HasSaved => PlayerPrefs.HasKey(Key);

        public static PlayerAppearance Load()
        {
            AppearanceRules.TryDecode(PlayerPrefs.GetString(Key, ""), out var a);
            return a;
        }

        public static void Save(PlayerAppearance appearance)
        {
            var a = AppearanceRules.Sanitize(appearance);
            PlayerPrefs.SetString(Key, AppearanceRules.Encode(a));
            PlayerPrefs.Save();
            Changed?.Invoke(a.Copy());
        }

        /// <summary>The wire text this player sends when he joins.</summary>
        public static string LocalWire => AppearanceRules.Encode(Load());

        /// <summary>A swatch colour of the look (colour slots), or the fallback.</summary>
        public static Color Swatch(PlayerAppearance a, AppearanceSlot slot, Color fallback)
        {
            var o = a != null ? AppearanceCatalogV01.Find(slot, a.Get(slot)) : null;
            return o != null && ColorUtility.TryParseHtmlString(o.Hex, out var c) ? c : fallback;
        }
    }
}
