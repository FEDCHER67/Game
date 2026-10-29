using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Text.RegularExpressions;

namespace OnlyVolunteers.Buyers
{
    /// <summary>Immutable economy metadata. IDs are catalog keys, never Inventory ItemIds.
    /// Null means inapplicable/open, never free. Units are explicit; money is whole dollars.</summary>
    public sealed class EconomyEntry
    {
        public string Id { get; }
        public string Category { get; }
        public string Spec { get; }
        public decimal? Price { get; }
        public string Unit { get; }
        public decimal Quantity { get; }
        public string EffectNote { get; }
        public string WhereSold { get; }
        public string Status { get; }
        public IReadOnlyDictionary<string, decimal?> Numbers { get; }
        public IReadOnlyDictionary<string, string> References { get; }

        internal EconomyEntry(EconomyCatalog.Record record)
        {
            Id = record.id; Category = record.category; Spec = record.spec; Price = record.price;
            Unit = record.unit; Quantity = record.quantity; EffectNote = record.effect_note;
            WhereSold = record.where_sold; Status = record.status;
            Numbers = new ReadOnlyDictionary<string, decimal?>(new Dictionary<string, decimal?>(record.numbers, StringComparer.Ordinal));
            References = new ReadOnlyDictionary<string, string>(new Dictionary<string, string>(record.refs, StringComparer.Ordinal));
        }

        public decimal Number(string key)
        {
            if (!Numbers.TryGetValue(key, out var value)) throw new KeyNotFoundException(Id + ": unknown number " + key);
            return value ?? throw new InvalidOperationException(Id + "/" + key + " is open or inapplicable; see spec " + Spec);
        }

        public string Reference(string key) => References.TryGetValue(key, out var value)
            ? value : throw new KeyNotFoundException(Id + ": unknown reference " + key);
    }

    /// <summary>Read-only extension of Buyers Core. Load a JSON text once and retain this instance.
    /// Does not own funds, purchases, deliveries, saves or scene objects. No global mutable default.
    /// Unity callers can pass TextAsset.text; standalone callers can use Load(absolutePath).</summary>
    public sealed class EconomyCatalog
    {
        private readonly Dictionary<string, EconomyEntry> byId = new Dictionary<string, EconomyEntry>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> aliases = new Dictionary<string, string>(StringComparer.Ordinal);
        public int SchemaVersion { get; }
        public string Id { get; }
        public string Spec { get; }
        public IReadOnlyList<EconomyEntry> Entries { get; }
        public decimal DeliveryGameHours => Get("delivery_game_hours").Number("value");

        private EconomyCatalog(Document data)
        {
            Require(data != null && data.schemaVersion == 1, "Expected economy schemaVersion 1.");
            Require((data.id == "economy_v01" || data.id == "economy_v02") && !string.IsNullOrWhiteSpace(data.spec), "Missing or unsupported economy identity/spec.");
            Require(data.entries != null && data.entries.Length > 0, "Economy entries must not be empty.");
            SchemaVersion = data.schemaVersion; Id = data.id; Spec = data.spec;
            var entries = new List<EconomyEntry>();
            foreach (var record in data.entries)
            {
                Require(record != null && ValidId(record.id), "Every economy id must be lowercase snake_case.");
                Require(!byId.ContainsKey(record.id), "Duplicate economy id: " + record.id);
                Require(!string.IsNullOrWhiteSpace(record.category) && !string.IsNullOrWhiteSpace(record.spec), record.id + ": missing category/spec.");
                Require(record.status == "confirmed" || record.status == "reserved" || record.status == "open", record.id + ": invalid status.");
                Require(record.price == null || record.price >= 0, record.id + ": price must not be negative.");
                Require(record.quantity > 0 && record.numbers != null && record.refs != null && record.unit != null && record.effect_note != null && record.where_sold != null, record.id + ": missing metadata.");
                Require(record.status != "open" || record.price == null && record.numbers.Count == 0, record.id + ": open values must not invent numbers.");
                foreach (var number in record.numbers)
                    Require(ValidId(number.Key) && (!number.Value.HasValue || number.Value.Value >= 0), record.id + ": invalid number " + number.Key);
                foreach (var reference in record.refs)
                    Require(ValidId(reference.Key) && reference.Value != null, record.id + ": invalid reference " + reference.Key);
                if (record.category == "consumable" || record.category == "equipment" || record.category == "van_tier" ||
                    record.category == "base" || record.category == "cargo" || record.category == "staff" || record.category == "sale_product")
                    Require(record.price.HasValue && !string.IsNullOrWhiteSpace(record.unit), record.id + ": missing price/unit.");
                var entry = new EconomyEntry(record); byId.Add(entry.Id, entry); entries.Add(entry);
            }
            Entries = new ReadOnlyCollection<EconomyEntry>(entries);
            if (data.aliases != null)
                foreach (var alias in data.aliases)
                {
                    Require(ValidId(alias.Key) && !byId.ContainsKey(alias.Key) &&
                        alias.Value != null && byId.ContainsKey(alias.Value), "Invalid economy alias: " + alias.Key);
                    aliases.Add(alias.Key, alias.Value);
                }
            // Fail at load time for broken formula links, not halfway through a quote.
            foreach (var entry in entries)
            {
                if (entry.Category == "mission" && entry.Reference("reward_kind") == "organ")
                {
                    OfCategory(entry.Reference("buyer"), "buyer"); OfCategory(entry.Reference("product"), "sale_product");
                    Require(entry.Number("minimum_tier") >= 1 && entry.Number("minimum_tier") <= 5, entry.Id + ": invalid quality floor.");
                }
                if (entry.Category == "van_tier")
                    Require(entry.Number("tier") >= 0 && entry.Number("tier") <= 3 &&
                        entry.Id == "van_" + entry.Reference("branch") + "_" + entry.Number("tier"), entry.Id + ": inconsistent van id/tier.");
            }
        }

        public static EconomyCatalog FromJson(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) throw new ArgumentException("Economy JSON is required.", nameof(json));
            var serializer = new DataContractJsonSerializer(typeof(Document), new DataContractJsonSerializerSettings { UseSimpleDictionaryFormat = true });
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(json)))
                return new EconomyCatalog((Document)serializer.ReadObject(stream));
        }

        public static EconomyCatalog Load(string absolutePath)
        {
            if (string.IsNullOrWhiteSpace(absolutePath) || !Path.IsPathRooted(absolutePath))
                throw new ArgumentException("An absolute economy JSON path is required.", nameof(absolutePath));
            return FromJson(File.ReadAllText(absolutePath, Encoding.UTF8));
        }

        /// <summary>Saved aliases resolve directly to a canonical key; no chains or duplicate products.</summary>
        public string ResolveId(string id) => id != null && aliases.TryGetValue(id, out var canonical) ? canonical : id;

        public EconomyEntry Get(string id) => id != null && byId.TryGetValue(ResolveId(id), out var entry)
            ? entry : throw new KeyNotFoundException("Unknown economy id: " + id);
        public decimal GetPrice(string id) => Get(id).Price ?? throw new InvalidOperationException(id + ": price is open or inapplicable.");
        public bool TryGetPrice(string id, out decimal price)
        {
            price = 0;
            if (id == null || !byId.TryGetValue(ResolveId(id), out var entry) || !entry.Price.HasValue) return false;
            price = entry.Price.Value; return true;
        }
        public EconomyEntry GetItem(string id)
        {
            var entry = Get(id);
            if (entry.Category != "consumable" && entry.Category != "equipment") throw new ArgumentException(id + ": not a shop item.", nameof(id));
            return entry;
        }
        private EconomyEntry OfCategory(string id, string category)
        {
            var entry = Get(id);
            if (entry.Category != category) throw new ArgumentException(id + ": expected " + category, nameof(id));
            return entry;
        }
        public EconomyEntry GetNextVanTier(string branch, int currentTier)
        {
            if (branch != "engine" && branch != "handling" && branch != "brakes") throw new ArgumentException("Unknown van branch: " + branch, nameof(branch));
            if (currentTier < 0 || currentTier > 3) throw new ArgumentOutOfRangeException(nameof(currentTier));
            return currentTier == 3 ? null : OfCategory("van_" + branch + "_" + (currentTier + 1), "van_tier");
        }
        public EconomyEntry GetBase(string id) => OfCategory(id, "base");
        public decimal GetBasePrice(string id) => GetBase(id).Price.Value;
        public EconomyEntry GetBuyer(string id) => OfCategory(id, "buyer");
        public decimal BuyerCoefficient(string id) => GetBuyer(id).Number("coefficient");
        public QualityTier BuyerFloor(string id) => (QualityTier)(int)GetBuyer(id).Number("minimum_tier");
        public EconomyEntry GetMission(string id) => OfCategory(id, "mission");
        public decimal QualityMultiplier(QualityTier tier)
        {
            switch (tier)
            {
                case QualityTier.Damaged: return Get("quality_damaged").Number("multiplier");
                case QualityTier.Acceptable: return Get("quality_acceptable").Number("multiplier");
                case QualityTier.Good: return Get("quality_good").Number("multiplier");
                case QualityTier.Perfect: return Get("quality_perfect").Number("multiplier");
                case QualityTier.PerfectPlus: return Get("quality_perfect_plus").Number("multiplier");
                default: throw new ArgumentOutOfRangeException(nameof(tier));
            }
        }
        internal static string ProductId(ProductKind kind)
        {
            switch (kind)
            {
                case ProductKind.Kidney: return "kidney";
                case ProductKind.Liver: return "liver";
                case ProductKind.Lungs: return "lungs";
                case ProductKind.Heart: return "heart";
                case ProductKind.Eye: return "eyes";
                case ProductKind.Brain: return "brain";
                case ProductKind.BloodBag: return "blood_bag_sealed";
                case ProductKind.IntroSyringe: return "blood_syringe_first";
                default: throw new ArgumentOutOfRangeException(nameof(kind));
            }
        }

        /// <summary>Pure projected reward, rounded once, never a payment. Defaults to the mission's minimum quality.
        /// On-time fixed VIP bonus is added after all organ factors. Courier has no deadline or organ factors.</summary>
        public decimal MissionReward(string id, bool onTime = true, int replacements = 0,
            QualityTier? quality = null, bool deliveredCooled = true, int negotiatedPercent = 0)
        {
            if (replacements < 0) throw new ArgumentOutOfRangeException(nameof(replacements));
            var mission = GetMission(id);
            if (mission.Reference("reward_kind") == "courier")
                return Math.Max(0, mission.Number("fixed_reward") - mission.Number("replacement_deduction") * replacements);
            QualityTier minimum = (QualityTier)(int)mission.Number("minimum_tier");
            QualityTier actual = quality ?? minimum;
            if (actual < minimum) throw new ArgumentOutOfRangeException(nameof(quality), id + ": below mission minimum.");
            ProductKind kind = ProductKind.Kidney;
            bool found = false;
            foreach (ProductKind candidate in Enum.GetValues(typeof(ProductKind)))
                if (ProductId(candidate) == mission.Reference("product")) { kind = candidate; found = true; break; }
            Require(found, id + ": unsupported product.");
            decimal organ = BuyerCatalog.UnitPrice(this, mission.Reference("buyer"), kind, actual,
                negotiatedPercent, onTime, deliveredCooled, 0, true);
            return Math.Round(organ + (onTime ? mission.Number("on_time_fixed_bonus") : 0), 0, MidpointRounding.AwayFromZero);
        }

        private static bool ValidId(string id) => id != null && Regex.IsMatch(id, "^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$");
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }

        [DataContract]
        internal sealed class Document
        {
            [DataMember(IsRequired = true)] public int schemaVersion { get; set; }
            [DataMember(IsRequired = true)] public string id { get; set; }
            [DataMember(IsRequired = true)] public string spec { get; set; }
            [DataMember(IsRequired = true)] public Record[] entries { get; set; }
            [DataMember(EmitDefaultValue = false)] public Dictionary<string, string> aliases { get; set; }
        }
        [DataContract]
        internal sealed class Record
        {
            [DataMember(IsRequired = true)] public string id { get; set; }
            [DataMember(IsRequired = true)] public string category { get; set; }
            [DataMember(IsRequired = true)] public string spec { get; set; }
            [DataMember(IsRequired = true)] public decimal? price { get; set; }
            [DataMember(IsRequired = true)] public string unit { get; set; }
            [DataMember(IsRequired = true)] public decimal quantity { get; set; }
            [DataMember(IsRequired = true)] public string effect_note { get; set; }
            [DataMember(IsRequired = true)] public string where_sold { get; set; }
            [DataMember(IsRequired = true)] public string status { get; set; }
            [DataMember(IsRequired = true)] public Dictionary<string, decimal?> numbers { get; set; }
            [DataMember(IsRequired = true)] public Dictionary<string, string> refs { get; set; }
        }
    }
}
