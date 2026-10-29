using System;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Economy
{
    /// <summary>The three independent paid branches of the team van (ECONOMY_SALES_PROGRESSION_SPEC v01 §6.1).
    /// Values are save/array indices.</summary>
    public enum VanBranch { Engine = 0, Handling = 1, Brakes = 2 }

    /// <summary>A large piece of permanent equipment ordered through the phone (§4 table, §4.1 delivery).</summary>
    public sealed class EquipmentOffer
    {
        public string Id;
        /// <summary>The catalogue key the price comes from (Buyers/Data/Economy_v02.json).</summary>
        public string CatalogId;
        public string Title;
        /// <summary>-1 = no price (catalogue not loaded, or the catalogue value is open): never orderable.</summary>
        public int Price = -1;
        public string Effect;
        /// <summary>False: listed with its price but not orderable yet (UnavailableReason says why).</summary>
        public bool Available = true;
        public string UnavailableReason = "";
    }

    /// <summary>A base of the team (§7.1). Free bases come with the story; the three paid ones are bought in the phone.</summary>
    public sealed class PropertyOffer
    {
        public string Id;
        public string CatalogId;
        public string Title;
        public string Location;
        /// <summary>-1 = no price (catalogue not loaded).</summary>
        public int Price = -1;
        /// <summary>Operating tables at most; -1 = no fixed design limit (the lab).</summary>
        public int Tables;
        public bool Purchasable;
        /// <summary>Equipment crates can be delivered here (the forest wagon is a blood-prologue spot, not a lab).</summary>
        public bool AcceptsDeliveries;
        public string StartingKit;
    }

    /// <summary>A consumable sold physically at the pharmacy / underground seller (§4 first table). Listed here so every
    /// price lives in one table; the phone does NOT sell these (no instant phone restock, §4.1).</summary>
    public sealed class ConsumableOffer
    {
        public string Id;
        public string CatalogId;
        public string Title;
        public int Price = -1;
        public string Where;
    }

    /// <summary>
    /// The ONE price accessor of the economy. Every number comes from the catalogue (Buyers/Data/Economy_v02.json,
    /// EconomyCatalog) bound once by the runtime bootstrap (EconomyCatalogSource.Ensure, called by TeamEconomy.Ensure).
    /// This class keeps only the explicit mapping from the saved economy ids (van:engine:2, rough, cooler_portable...) to
    /// the G48 keys, plus the Russian presentation text; it holds no price table of its own. Unbound (no catalogue) or an
    /// open catalogue value = no price: the offer is unavailable and purchases are refused, never priced from a fallback.
    /// </summary>
    public static class EconomyPrices
    {
        public const int VanMaxTier = 3;
        public const string NotLoadedReason = "Цены не загружены (каталог экономики G48)";

        private static EconomyCatalog catalog;

        /// <summary>The bound G48 catalogue (null before the bootstrap).</summary>
        public static EconomyCatalog Catalog => catalog;
        public static bool Bound => catalog != null;

        /// <summary>§4.1: a large order arrives as one paid crate after one game hour (G48 delivery_game_hours).</summary>
        public static double DeliveryGameHours => catalog != null ? (double)catalog.DeliveryGameHours : double.NaN;

        public static string BranchKey(VanBranch branch) =>
            branch == VanBranch.Engine ? "engine" : branch == VanBranch.Handling ? "handling" : "brakes";

        /// <summary>G48 key of one van tier: van_engine_2 etc.</summary>
        public static string VanCatalogId(VanBranch branch, int tier) => "van_" + BranchKey(branch) + "_" + tier;

        /// <summary>Price of buying this tier (1..3) of a branch; -1 for tier 0 (part of the van), out of range or unbound.</summary>
        public static int VanTierPrice(VanBranch branch, int tier)
        {
            if ((uint)branch > 2 || tier < 1 || tier > VanMaxTier) return -1;
            return Whole(VanCatalogId(branch, tier));
        }

        public static int VanBranchTotal(VanBranch branch)
        {
            int total = 0;
            for (int t = 1; t <= VanMaxTier; t++)
            {
                int p = VanTierPrice(branch, t);
                if (p < 0) return -1;
                total += p;
            }
            return total;
        }

        /// <summary>§2: the peaceful van purchase from grandpa (G48 van_initial_purchase); -1 when unbound.</summary>
        public static int VanInitialPrice => Whole("van_initial_purchase");

        public static string BranchTitle(VanBranch branch) =>
            branch == VanBranch.Engine ? "Двигатель" : branch == VanBranch.Handling ? "Управление" : "Тормоза";

        public static string TierName(int tier) => tier <= 0 ? "0" : tier == 1 ? "I" : tier == 2 ? "II" : "III";

        // ---------- bases (§7.1) ----------

        public const string BaseWagon = "forest_wagon";
        public const string BaseHamlet = "hamlet_shed";
        public const string BaseRough = "rough";
        public const string BaseDowntown = "downtown";
        public const string BaseLab = "quiet_valley_lab";

        /// <summary>§7.1 / §15 C5 (G48 base_*): the three paid ones are $8 100 / $33 750 / $135 000.</summary>
        public static PropertyOffer[] Properties { get; private set; } = BuildProperties(null);

        // ---------- permanent equipment (§4 second table) ----------

        public static EquipmentOffer[] Equipment { get; private set; } = BuildEquipment(null);

        /// <summary>§4 first table: pharmacy / underground seller only, never the phone. Same unit price singly or packed.</summary>
        public static ConsumableOffer[] Consumables { get; private set; } = BuildConsumables(null);

        /// <summary>Paid placeholder apps of the phone's PayMarket (the server charges by name, never a client amount). Not an
        /// economy-spec item, so not in G48: a phone placeholder that keeps its own price until PHONE defines one.</summary>
        private static readonly string[] PhoneAppNames = { "City News" };
        private static readonly int[] PhoneAppPrices = { 2 };

        /// <summary>The bootstrap binds the loaded catalogue once (null unbinds: everything becomes unavailable).</summary>
        public static void Bind(EconomyCatalog loaded)
        {
            catalog = loaded;
            Properties = BuildProperties(loaded);
            Equipment = EconomyOffersV02.Equipment(loaded, BuildEquipment(loaded));
            Consumables = EconomyOffersV02.Consumables(loaded, BuildConsumables(loaded));
        }

        public static EquipmentOffer FindEquipment(string id) =>
            string.IsNullOrEmpty(id) ? null : Array.Find(Equipment, e => e.Id == id || e.Id == EconomyOffersV02.ResolveSavedId(id));

        public static PropertyOffer FindProperty(string id) =>
            string.IsNullOrEmpty(id) ? null : Array.Find(Properties, p => p.Id == id);

        public static ConsumableOffer FindConsumable(string id) =>
            string.IsNullOrEmpty(id) ? null : Array.Find(Consumables, c => c.Id == id);

        /// <summary>Price of a paid PayMarket app, or -1 when it is not a paid app.</summary>
        public static int PhoneAppPrice(string name)
        {
            int i = Array.IndexOf(PhoneAppNames, name);
            return i < 0 ? -1 : PhoneAppPrices[i];
        }

        /// <summary>Whole-dollar catalogue price of a G48 key; -1 when unbound, unknown or open (price null).</summary>
        public static int Whole(string catalogId) => WholeFrom(catalog, catalogId);

        private static int WholeFrom(EconomyCatalog c, string catalogId)
        {
            if (c == null || string.IsNullOrEmpty(catalogId)) return -1;
            try
            {
                if (!c.TryGetPrice(catalogId, out decimal price) || price < 0 || price != decimal.Truncate(price) || price > int.MaxValue) return -1;
                return (int)price;
            }
            catch (Exception) { return -1; }
        }

        private static int Tables(EconomyCatalog c, string catalogId, int fallbackWhenUnbound)
        {
            if (c == null) return fallbackWhenUnbound;
            try
            {
                EconomyEntry e = c.Get(catalogId);
                return e.Numbers.TryGetValue("table_capacity", out decimal? v) && v.HasValue ? (int)v.Value : -1;
            }
            catch (Exception) { return fallbackWhenUnbound; }
        }

        private static bool CatalogStatusOpen(EconomyCatalog c, string catalogId)
        {
            if (c == null) return true;
            try
            {
                string s = c.Get(catalogId).Status ?? "";
                return s == "open" || s == "reserved";
            }
            catch (Exception) { return true; }
        }

        // ---------- explicit id mapping (saved economy id -> G48 key) + presentation ----------

        private static PropertyOffer[] BuildProperties(EconomyCatalog c)
        {
            PropertyOffer P(string id, string key, string title, string location, bool purchasable, bool deliveries, string kit) => new PropertyOffer
            {
                Id = id, CatalogId = key, Title = title, Location = location, Purchasable = purchasable, AcceptsDeliveries = deliveries,
                StartingKit = kit, Price = c != null ? WholeFrom(c, key) : -1, Tables = Tables(c, key, 0),
            };
            return new[]
            {
                P(BaseWagon, "base_wagon", "Лесной вагон", "Лес", false, false, "Кровяной пролог; не органная лаборатория"),
                P(BaseHamlet, "base_hamlet", "Хижина и сарай Хутора", "Хутор", false, true, "Старый стол и ржавый нож; без лампы и креплений"),
                P(BaseRough, "base_rough", "Помещение в Rough", "Неблагополучный район (Rough)", true, true, "Пустое рабочее помещение"),
                P(BaseDowntown, "base_downtown", "Помещение в Downtown", "Даунтаун", true, true, "Пустое рабочее помещение"),
                P(BaseLab, "base_lab", "Лаборатория", "Тихая долина (Quiet Valley)", true, true, "Пустое пригодное помещение"),
            };
        }

        private static EquipmentOffer[] BuildEquipment(EconomyCatalog c)
        {
            EquipmentOffer E(string id, string key, string title, string effect, string unavailable = null)
            {
                int price = c != null ? WholeFrom(c, key) : -1;
                string why = c == null ? NotLoadedReason : unavailable ?? (price < 0 || CatalogStatusOpen(c, key) ? "Цена в каталоге не назначена" : "");
                return new EquipmentOffer { Id = id, CatalogId = key, Title = title, Effect = effect, Price = price, Available = why.Length == 0, UnavailableReason = why };
            }
            return new[]
            {
                E("knife", "knife", "Замена базового ножа", "Многоразовый физический инструмент"),
                E("restraints5", "patient_restraints", "Комплект пяти креплений пациента", "Оснастка стола; не пять стяжек для захвата"),
                E("work_lamp", "work_lamp", "Рабочая лампа", "Освещение рабочего места"),
                E("saw", "saw", "Пила", "Процедура после сюжетного открытия; сама мозг не открывает"),
                E("hammer", "hammer", "Молоток", "Грудная процедура (комплект с остеотомом)"),
                E("osteotome", "osteotome", "Остеотом", "Отдельный предмет, не замена молотка"),
                E("tray", "tray", "Лоток", "Хранение без охлаждения"),
                E("tool_cart", "tool_trolley", "Инструментальная тележка", "Подвоз физически доступных инструментов"),
                E("cooler_portable", "portable_fridge", "Переносной холодильник", "8 предметов; занимает обе руки; порча раз в 25 активных минут"),
                E("cooler_stationary", "stationary_fridge", "Стационарный холодильник", "24 предмета; с оплаченным электричеством порча остановлена"),
                E("mop_bucket", "mop_bucket", "Швабра с ведром", "Уборка; вода не расходуется"),
                E("operating_table", "operating_table", "Операционный стол", "Ставится в пределах вместимости базы"),
                E("rare_equipment", "rare_equipment", "Оценочное / редкое оборудование", "Функции по спецификации операций",
                    "Функции и ресурсы ещё не определены спецификацией операций"),
            };
        }

        private static ConsumableOffer[] BuildConsumables(EconomyCatalog c)
        {
            ConsumableOffer C(string id, string key, string title, string where) =>
                new ConsumableOffer { Id = id, CatalogId = key, Title = title, Where = where, Price = c != null ? WholeFrom(c, key) : -1 };
            return new[]
            {
                C("syringe_blood", "syringe_blood", "Шприц крови", "Аптека; находки"),
                C("syringe_anesthesia", "syringe_anaesthesia", "Шприц наркоза, пустой", "Аптека; находки"),
                C("zip_tie", "zip_tie", "Стяжка", "Аптека / подпольный продавец"),
                C("zip_tie_x4", "zip_tie_pack_4", "Четыре стяжки", "Аптека / подпольный продавец"),
                C("blood_bag_empty", "blood_bag_empty", "Пустой пакет крови", "Аптека после вводной миссии"),
                C("organ_pack", "organ_bag", "Индивидуальный пакет органа", "Аптека"),
                C("body_bag", "body_bag", "Мешок для тела", "Аптека"),
                C("trash_bag", "trash_bag", "Мусорный пакет", "Аптека"),
                C("head_sack", "head_bag", "Мешок на голову", "Подпольный продавец"),
                C("anesthesia_basic", "anaesthesia_basic", "Начальный наркоз, флакон", "Аптека"),
                C("anesthesia_improved", "anaesthesia_improved", "Улучшенный наркоз, флакон", "Аптека (после формулы)"),
                C("anesthesia_late", "anaesthesia_late", "Поздний наркоз, флакон", "Аптека (после поздней формулы)"),
            };
        }
    }
}
