using System;
using System.Collections.Generic;
using System.Text;

namespace OnlyVolunteers.Session
{
    /// <summary>One customisable part of the player's look. Append only: the order is the wire order.</summary>
    public enum AppearanceSlot { Skin = 0, Hair = 1, HairColour = 2, FacialHair = 3, Top = 4, TopColour = 5, Bottom = 6, BottomColour = 7, Accessory = 8 }

    /// <summary>One selectable option: a stable id (saved and sent), a Russian label for the customiser and, for colour
    /// slots, the swatch colour as #RRGGBB.</summary>
    public sealed class AppearanceOption
    {
        public readonly string Id, Label, Hex;
        public AppearanceOption(string id, string label, string hex = "") { Id = id; Label = label; Hex = hex ?? ""; }
    }

    /// <summary>The player's chosen look (cosmetic only: no stats, no hitbox, speed, strength or economy effect). Ids only;
    /// the avatar binding maps them to meshes/materials. JsonUtility-friendly.</summary>
    [Serializable]
    public sealed class PlayerAppearance
    {
        public int version = AppearanceCatalogV01.Version;
        public string skin = "", hair = "", hairColour = "", facialHair = "", top = "", topColour = "", bottom = "", bottomColour = "", accessory = "";

        public string Get(AppearanceSlot slot)
        {
            switch (slot)
            {
                case AppearanceSlot.Skin: return skin;
                case AppearanceSlot.Hair: return hair;
                case AppearanceSlot.HairColour: return hairColour;
                case AppearanceSlot.FacialHair: return facialHair;
                case AppearanceSlot.Top: return top;
                case AppearanceSlot.TopColour: return topColour;
                case AppearanceSlot.Bottom: return bottom;
                case AppearanceSlot.BottomColour: return bottomColour;
                case AppearanceSlot.Accessory: return accessory;
                default: return "";
            }
        }

        public void Set(AppearanceSlot slot, string id)
        {
            id ??= "";
            switch (slot)
            {
                case AppearanceSlot.Skin: skin = id; break;
                case AppearanceSlot.Hair: hair = id; break;
                case AppearanceSlot.HairColour: hairColour = id; break;
                case AppearanceSlot.FacialHair: facialHair = id; break;
                case AppearanceSlot.Top: top = id; break;
                case AppearanceSlot.TopColour: topColour = id; break;
                case AppearanceSlot.Bottom: bottom = id; break;
                case AppearanceSlot.BottomColour: bottomColour = id; break;
                case AppearanceSlot.Accessory: accessory = id; break;
            }
        }

        public PlayerAppearance Copy() => (PlayerAppearance)MemberwiseClone();

        public bool SameAs(PlayerAppearance other)
        {
            if (other == null) return false;
            foreach (AppearanceSlot s in AppearanceCatalogV01.Slots) if (Get(s) != other.Get(s)) return false;
            return true;
        }
    }

    /// <summary>
    /// Customisation catalogue (v02 since 29.10 evening): the player is a customisable Sausage Buddy (Fedya 29.10) and the
    /// option ids ARE the ids of the PLAYER_SAUSAGE_W86 v01 parts manifest (ArtSource/Characters/PLAYER_SAUSAGE_W86/
    /// PLAYER_SAUSAGE_W86_v01_manifest.json): hair / beard / top / bottom / head x5, skin tones x5, clothing swatches x8
    /// (top and bottom each), plus the hair colour (a tint of the shared hair material). The v01 ids of the afternoon (before
    /// the model existed) are kept as aliases: an old local profile or wire text maps onto the nearest v02 option instead of
    /// a reset. Ids are saved and sent: never rename one, only add. Each slot's default is the manifest's default selection.
    /// </summary>
    public static class AppearanceCatalogV01
    {
        public const int Version = 2;
        public static readonly AppearanceSlot[] Slots =
        {
            AppearanceSlot.Skin, AppearanceSlot.Hair, AppearanceSlot.HairColour, AppearanceSlot.FacialHair, AppearanceSlot.Top,
            AppearanceSlot.TopColour, AppearanceSlot.Bottom, AppearanceSlot.BottomColour, AppearanceSlot.Accessory,
        };

        /// <summary>The manifest's clothing swatches (main tone; the trim and accent tones come from the manifest itself).</summary>
        static readonly AppearanceOption[] Cloth =
        {
            new AppearanceOption("Sw_01", "Белый", "#EAE8E2"), new AppearanceOption("Sw_02", "Серый", "#80848A"),
            new AppearanceOption("Sw_03", "Чёрный", "#2C2E32"), new AppearanceOption("Sw_04", "Красный", "#B23A2C"),
            new AppearanceOption("Sw_05", "Синий", "#3A5692"), new AppearanceOption("Sw_06", "Зелёный", "#526E46"),
            new AppearanceOption("Sw_07", "Жёлтый", "#E8B836"), new AppearanceOption("Sw_08", "Бежевый", "#B09C74"),
        };

        static readonly Dictionary<AppearanceSlot, AppearanceOption[]> options = new Dictionary<AppearanceSlot, AppearanceOption[]>
        {
            [AppearanceSlot.Skin] = new[]
            {
                new AppearanceOption("Skin_01", "Светлая", "#F4B094"), new AppearanceOption("Skin_02", "Сосисочная (как у NPC)", "#EC986A"),
                new AppearanceOption("Skin_03", "Смуглая", "#CE8A60"), new AppearanceOption("Skin_04", "Тёмная", "#A06646"),
                new AppearanceOption("Skin_05", "Очень тёмная", "#68422E"),
            },
            [AppearanceSlot.Hair] = new[]
            {
                new AppearanceOption("Hair_01", "Лысый"), new AppearanceOption("Hair_02", "Ёжик"), new AppearanceOption("Hair_03", "Пробор"),
                new AppearanceOption("Hair_04", "Чёлка"), new AppearanceOption("Hair_05", "Кок"),
            },
            [AppearanceSlot.HairColour] = new[]
            {
                new AppearanceOption("hc_darkbrown", "Каштановые", "#5C402E"), new AppearanceOption("hc_black", "Чёрные", "#23201E"),
                new AppearanceOption("hc_lightbrown", "Русые", "#7A5536"), new AppearanceOption("hc_blond", "Светлые", "#C9A86A"),
                new AppearanceOption("hc_ginger", "Рыжие", "#A4532A"),
            },
            [AppearanceSlot.FacialHair] = new[]
            {
                new AppearanceOption("Beard_01", "Без бороды"), new AppearanceOption("Beard_02", "Щетина"), new AppearanceOption("Beard_03", "Усы"),
                new AppearanceOption("Beard_04", "Борода"), new AppearanceOption("Beard_05", "Эспаньолка"),
            },
            [AppearanceSlot.Top] = new[]
            {
                new AppearanceOption("Top_01", "Футболка"), new AppearanceOption("Top_02", "Худи"), new AppearanceOption("Top_03", "Рабочая куртка"),
                new AppearanceOption("Top_04", "Олимпийка"), new AppearanceOption("Top_05", "Рубашка"),
            },
            [AppearanceSlot.TopColour] = Cloth,
            [AppearanceSlot.Bottom] = new[]
            {
                new AppearanceOption("Bottom_01", "Джинсы"), new AppearanceOption("Bottom_02", "Спортивные штаны"), new AppearanceOption("Bottom_03", "Карго"),
                new AppearanceOption("Bottom_04", "Шорты"), new AppearanceOption("Bottom_05", "Рабочие брюки"),
            },
            [AppearanceSlot.BottomColour] = Cloth,
            [AppearanceSlot.Accessory] = new[]
            {
                new AppearanceOption("Head_01", "Ничего"), new AppearanceOption("Head_02", "Кепка"), new AppearanceOption("Head_03", "Шапка"),
                new AppearanceOption("Head_04", "Бандана"), new AppearanceOption("Head_05", "Очки"),
            },
        };

        /// <summary>The manifest's default selection.</summary>
        static readonly Dictionary<AppearanceSlot, string> defaults = new Dictionary<AppearanceSlot, string>
        {
            [AppearanceSlot.Skin] = "Skin_02", [AppearanceSlot.Hair] = "Hair_03", [AppearanceSlot.HairColour] = "hc_darkbrown",
            [AppearanceSlot.FacialHair] = "Beard_01", [AppearanceSlot.Top] = "Top_01", [AppearanceSlot.TopColour] = "Sw_01",
            [AppearanceSlot.Bottom] = "Bottom_01", [AppearanceSlot.BottomColour] = "Sw_05", [AppearanceSlot.Accessory] = "Head_01",
        };

        /// <summary>v01 ids (29.10 afternoon, before the model) → the nearest v02 option.</summary>
        static readonly Dictionary<string, string> legacy = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["skin_01"] = "Skin_01", ["skin_02"] = "Skin_02", ["skin_03"] = "Skin_02", ["skin_04"] = "Skin_04", ["skin_05"] = "Skin_05",
            ["hair_short"] = "Hair_03", ["hair_messy"] = "Hair_04", ["hair_buzz"] = "Hair_02", ["hair_slick"] = "Hair_05", ["hair_bald"] = "Hair_01",
            ["fh_none"] = "Beard_01", ["fh_stubble"] = "Beard_02", ["fh_moustache"] = "Beard_03", ["fh_beard"] = "Beard_04", ["fh_goatee"] = "Beard_05",
            ["top_tshirt"] = "Top_01", ["top_hoodie"] = "Top_02", ["top_workjacket"] = "Top_03", ["top_vest"] = "Top_04", ["top_shirt"] = "Top_05",
            ["bottom_jeans"] = "Bottom_01", ["bottom_track"] = "Bottom_02", ["bottom_cargo"] = "Bottom_03", ["bottom_shorts"] = "Bottom_04", ["bottom_work"] = "Bottom_05",
            ["acc_none"] = "Head_01", ["acc_cap"] = "Head_02", ["acc_beanie"] = "Head_03", ["acc_bandana"] = "Head_04", ["acc_glasses"] = "Head_05",
            ["c_white"] = "Sw_01", ["c_grey"] = "Sw_02", ["c_black"] = "Sw_03", ["c_maroon"] = "Sw_04", ["c_navy"] = "Sw_05", ["c_teal"] = "Sw_05",
            ["c_olive"] = "Sw_06", ["c_mustard"] = "Sw_07",
        };

        public static IReadOnlyList<AppearanceOption> Options(AppearanceSlot slot) =>
            options.TryGetValue(slot, out var list) ? list : Array.Empty<AppearanceOption>();

        public static string DefaultId(AppearanceSlot slot)
        {
            if (defaults.TryGetValue(slot, out string id)) return id;
            var o = Options(slot);
            return o.Count > 0 ? o[0].Id : "";
        }

        /// <summary>A v01 id of this slot → its v02 option id; null when it is not a known old id.</summary>
        public static string Migrate(AppearanceSlot slot, string id)
        {
            if (string.IsNullOrEmpty(id) || !legacy.TryGetValue(id, out string to)) return null;
            return IsValid(slot, to) ? to : null;
        }

        public static AppearanceOption Find(AppearanceSlot slot, string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (var o in Options(slot)) if (o.Id == id) return o;
            return null;
        }

        public static bool IsValid(AppearanceSlot slot, string id) => Find(slot, id) != null;

        /// <summary>Colour slots work on any body; mesh slots need the chosen model's parts.</summary>
        public static bool IsColourSlot(AppearanceSlot slot) =>
            slot == AppearanceSlot.Skin || slot == AppearanceSlot.HairColour || slot == AppearanceSlot.TopColour || slot == AppearanceSlot.BottomColour;

        public static string SlotLabel(AppearanceSlot slot)
        {
            switch (slot)
            {
                case AppearanceSlot.Skin: return "Кожа";
                case AppearanceSlot.Hair: return "Причёска";
                case AppearanceSlot.HairColour: return "Цвет волос";
                case AppearanceSlot.FacialHair: return "Борода и усы";
                case AppearanceSlot.Top: return "Верх";
                case AppearanceSlot.TopColour: return "Цвет верха";
                case AppearanceSlot.Bottom: return "Низ";
                case AppearanceSlot.BottomColour: return "Цвет низа";
                case AppearanceSlot.Accessory: return "Головной убор";
                default: return slot.ToString();
            }
        }
    }

    /// <summary>Pure rules of the look: defaults, validation, the compact wire text sent over the network, and option
    /// cycling for the customiser. Never throws on bad input: anything unknown becomes that slot's default.</summary>
    public static class AppearanceRules
    {
        public const string WirePrefix = "ova1";
        /// <summary>A wire text longer than this is refused outright (a client cannot make the server parse megabytes).</summary>
        public const int MaxWireLength = 400;
        /// <summary>Local profile key (PlayerPrefs on the player's own machine) for one stable player GUID: two test builds with
        /// different "-player-guid" values on one PC keep separate looks.</summary>
        public const string ProfileKeyPrefix = "ov_appearance_v1_";

        public static string ProfileKey(string playerGuid) => ProfileKeyPrefix + (playerGuid ?? "");

        public static PlayerAppearance Default()
        {
            var a = new PlayerAppearance();
            foreach (var s in AppearanceCatalogV01.Slots) a.Set(s, AppearanceCatalogV01.DefaultId(s));
            return a;
        }

        /// <summary>A valid copy: null → default look; every unknown/missing id (an older or newer build's cosmetic, a typo,
        /// tampering) → that slot's default; known ids are kept. <paramref name="replaced"/> lists the slots that were fixed.</summary>
        public static PlayerAppearance Sanitize(PlayerAppearance input, List<AppearanceSlot> replaced = null)
        {
            if (input == null)
            {
                if (replaced != null) replaced.AddRange(AppearanceCatalogV01.Slots);
                return Default();
            }
            var a = new PlayerAppearance();
            foreach (var s in AppearanceCatalogV01.Slots)
            {
                string id = input.Get(s);
                if (AppearanceCatalogV01.IsValid(s, id)) a.Set(s, id);
                else if (AppearanceCatalogV01.Migrate(s, id) is string moved) a.Set(s, moved); // a v01 id: its nearest v02 option
                else { a.Set(s, AppearanceCatalogV01.DefaultId(s)); replaced?.Add(s); }
            }
            return a;
        }

        public static string Encode(PlayerAppearance appearance)
        {
            var a = Sanitize(appearance);
            var sb = new StringBuilder(WirePrefix);
            foreach (var s in AppearanceCatalogV01.Slots) sb.Append(';').Append(a.Get(s));
            return sb.ToString();
        }

        /// <summary>Parses a wire text. False (and the default look) for garbage: null, too long, no prefix. True otherwise,
        /// with unknown ids replaced by defaults; fields a newer build appended are ignored, missing ones get defaults.</summary>
        public static bool TryDecode(string wire, out PlayerAppearance appearance, List<AppearanceSlot> replaced = null)
        {
            appearance = Default();
            if (string.IsNullOrEmpty(wire) || wire.Length > MaxWireLength) return false;
            string[] parts = wire.Split(';');
            if (parts.Length < 1 || parts[0] != WirePrefix) return false;
            var raw = new PlayerAppearance();
            for (int i = 0; i < AppearanceCatalogV01.Slots.Length; i++)
                raw.Set(AppearanceCatalogV01.Slots[i], i + 1 < parts.Length ? parts[i + 1] : "");
            appearance = Sanitize(raw, replaced);
            return true;
        }

        /// <summary>Options the customiser may offer: colour slots always, mesh slots only when <paramref name="present"/>
        /// says the avatar has that part (null = nothing of the model is present yet, only colours are offered).</summary>
        public static List<AppearanceOption> Selectable(AppearanceSlot slot, Func<AppearanceSlot, string, bool> present)
        {
            var list = new List<AppearanceOption>();
            foreach (var o in AppearanceCatalogV01.Options(slot))
                if (AppearanceCatalogV01.IsColourSlot(slot) || (present != null && present(slot, o.Id))) list.Add(o);
            return list;
        }

        /// <summary>The next/previous selectable option (wraps). Returns the current id when nothing else can be chosen.</summary>
        public static string Cycle(AppearanceSlot slot, string current, int direction, Func<AppearanceSlot, string, bool> present)
        {
            var list = Selectable(slot, present);
            if (list.Count == 0) return string.IsNullOrEmpty(current) ? AppearanceCatalogV01.DefaultId(slot) : current;
            int i = list.FindIndex(o => o.Id == current);
            if (i < 0) return list[0].Id;
            int n = list.Count, step = direction >= 0 ? 1 : -1;
            return list[((i + step) % n + n) % n].Id;
        }
    }

    /// <summary>Stable player ids as the economy uses them (TeamEconomy.ServerParticipantId): "host" for the host's own
    /// client, the client's persistent GUID after its Hello.</summary>
    public static class PlayerIds
    {
        public const string Host = "host";

        /// <summary>The same character rule as TeamEconomy.ValidGuid (8..40 letters, digits, '-' or '_'), plus "host".</summary>
        public static bool IsValid(string id)
        {
            if (id == Host) return true;
            if (string.IsNullOrEmpty(id) || id.Length < 8 || id.Length > 40) return false;
            foreach (char ch in id) if (!(char.IsLetterOrDigit(ch) || ch == '-' || ch == '_')) return false;
            return true;
        }
    }

    /// <summary>
    /// Server side: the looks of this session's players by stable id. Each player's look comes ONLY from that player's own
    /// submission (sent by his client from his local profile on every join); a reconnect replaces his own entry and never
    /// copies another player's (the host's) look. A player without a submission is shown with the default look.
    /// </summary>
    public sealed class AppearanceBook
    {
        readonly Dictionary<string, PlayerAppearance> byPlayer = new Dictionary<string, PlayerAppearance>(StringComparer.Ordinal);

        public int Count => byPlayer.Count;
        public bool Has(string playerId) => playerId != null && byPlayer.ContainsKey(playerId);

        /// <summary>Validates and stores one player's own look. False (nothing stored) for an invalid id or a garbage wire
        /// text; <paramref name="applied"/> is the sanitized look that is stored and broadcast.</summary>
        public bool Submit(string playerId, string wire, out PlayerAppearance applied)
        {
            applied = AppearanceRules.Default();
            if (!PlayerIds.IsValid(playerId)) return false;
            if (!AppearanceRules.TryDecode(wire, out applied)) return false;
            byPlayer[playerId] = applied.Copy();
            return true;
        }

        /// <summary>A copy of the player's look, or the default look — never someone else's.</summary>
        public PlayerAppearance Get(string playerId) =>
            playerId != null && byPlayer.TryGetValue(playerId, out var a) ? a.Copy() : AppearanceRules.Default();

        public string WireOf(string playerId) => AppearanceRules.Encode(Get(playerId));
    }
}
