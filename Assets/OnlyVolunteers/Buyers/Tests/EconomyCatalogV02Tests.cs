using System;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class EconomyCatalogV02Tests
    {
        private static string DataPath(string name, [CallerFilePath] string source = "") =>
            Path.GetFullPath(Path.Combine(Path.GetDirectoryName(source), "..", "Data", name));
        private EconomyCatalog catalog;

        [SetUp] public void Load() => catalog = EconomyCatalog.Load(DataPath("Economy_v02.json"));

        [Test]
        public void V01KeysAndEveryHistoricalPriceStillResolveInV02()
        {
            var previous = EconomyCatalog.Load(DataPath("Economy_v01.json"));
            Assert.That(catalog.Id, Is.EqualTo("economy_v02"));
            Assert.That(catalog.SchemaVersion, Is.EqualTo(1));
            // 99 G53 entries + the two containment steps of the van cargo upgrades (Fedya 29.10, ECONOMY §6.2)
            Assert.That(catalog.Entries.Count, Is.EqualTo(101));
            foreach (EconomyEntry old in previous.Entries)
            {
                EconomyEntry current = catalog.Get(old.Id);
                Assert.That(current.Id, Is.EqualTo(old.Id), old.Id);
                Assert.That(current.Price, Is.EqualTo(old.Price), old.Id);
                Assert.That(current.Unit, Is.EqualTo(old.Unit), old.Id);
                if (old.Id != "patient_restraints") Assert.That(current.Quantity, Is.EqualTo(old.Quantity), old.Id);
                foreach (var number in old.Numbers)
                    Assert.That(current.Numbers[number.Key], Is.EqualTo(number.Value), old.Id + "/" + number.Key);
            }
        }

        [TestCase("patient_restraints", 500, 4)]
        [TestCase("suture_kit", 5, 1)]
        [TestCase("patch", 5, 1)]
        public void OperationsSection3_PricesAndPackSizes(string id, int price, int quantity)
        {
            EconomyEntry entry = catalog.GetItem(id);
            Assert.That(entry.Price, Is.EqualTo(price));
            Assert.That(entry.Quantity, Is.EqualTo(quantity));
            Assert.That(entry.Status, Is.EqualTo("confirmed"));
        }

        [TestCase("direct_to_bag", 1500, 2)]
        [TestCase("quick_release", 2000, 3)]
        [TestCase("packing_station", 2500, 4)]
        public void OperationsSection6_CoreSection4_DevicePricesAndGates(string id, int price, int level)
        {
            EconomyEntry entry = catalog.GetItem(id);
            Assert.That(entry.Price, Is.EqualTo(price));
            Assert.That(entry.Number("required_level"), Is.EqualTo(level));
            Assert.That(entry.Status, Is.EqualTo("reserved"));
            Assert.That(entry.Reference("unavailable_reason_ru"), Does.Contain("не реализована"));
        }

        [Test]
        public void OnlyThreeDevicesIntroduceLevelGates()
        {
            Assert.That(catalog.Entries.Where(e => e.Numbers.ContainsKey("required_level")).Select(e => e.Id),
                Is.EquivalentTo(new[] { "direct_to_bag", "quick_release", "packing_station" }));
            Assert.That(catalog.DeliveryGameHours, Is.EqualTo(1));
            Assert.That(catalog.Get("quick_release").Number("restraint_count"), Is.EqualTo(4));
            Assert.That(catalog.Get("quick_release").Number("active_seconds"), Is.EqualTo(1));
            Assert.That(catalog.Get("packing_station").Number("input_capacity"), Is.EqualTo(4));
            Assert.That(catalog.Get("packing_station").Number("active_seconds_per_item"), Is.EqualTo(2));
            Assert.That(catalog.GetPrice(catalog.Get("packing_station").Reference("bag")), Is.EqualTo(10));
        }

        // ECONOMY §6.2 cargo table + "Решение Феди 29.10 — удержание пленника": prices, prerequisites, all sold at the workshop.
        [TestCase("van_storage", 1500, "")]
        [TestCase("van_capacity_1", 2000, "")]
        [TestCase("van_capacity_2", 4000, "van_capacity_1")]
        [TestCase("van_containment_1", 1500, "")]
        [TestCase("van_containment_2", 2500, "van_containment_1")]
        public void Spec62_CargoUpgradesWithContainment_PricesAndPrerequisites(string id, int price, string requires)
        {
            EconomyEntry entry = catalog.Get(id);
            Assert.That(entry.Category, Is.EqualTo("cargo"));
            Assert.That(entry.Price, Is.EqualTo(price), id);
            Assert.That(entry.Status, Is.EqualTo("confirmed"), id);
            Assert.That(entry.WhereSold, Is.EqualTo("workshop"), id);
            Assert.That(entry.References.TryGetValue("requires", out string got) ? got : "", Is.EqualTo(requires), id);
        }

        [Test]
        public void Spec62_CargoCategoryHoldsExactlyTheFiveUpgrades_ContainmentTitlesInRussian()
        {
            Assert.That(catalog.Entries.Where(e => e.Category == "cargo").Select(e => e.Id),
                Is.EquivalentTo(new[] { "van_storage", "van_capacity_1", "van_capacity_2", "van_containment_1", "van_containment_2" }));
            Assert.That(catalog.Get("van_containment_1").Reference("title_ru"), Is.EqualTo("Фиксаторы кузова"));
            Assert.That(catalog.Get("van_containment_2").Reference("title_ru"), Is.EqualTo("Мягкий отсек"));
            Assert.That(catalog.Entries.Where(e => e.Category == "cargo").Sum(e => e.Price.Value), Is.EqualTo(11500));
        }

        [TestCase("restraints5")]
        [TestCase("restraints4")]
        public void SavedRestraintAliasesResolveToOneProduct(string alias)
        {
            Assert.That(catalog.ResolveId(alias), Is.EqualTo("patient_restraints"));
            Assert.That(catalog.GetItem(alias), Is.SameAs(catalog.GetItem("patient_restraints")));
            Assert.That(catalog.TryGetPrice(alias, out decimal price), Is.True);
            Assert.That(price, Is.EqualTo(500));
        }

        [TestCase("patient_restraints", "knife")]
        [TestCase("old_key", "missing")]
        [TestCase("bad-key", "knife")]
        public void InvalidAliasNeverHidesACatalogProblem(string alias, string target)
        {
            string json = File.ReadAllText(DataPath("Economy_v02.json"));
            int start = json.IndexOf("\"aliases\"", StringComparison.Ordinal);
            json = json.Substring(0, start) + "\"aliases\": {\"" + alias + "\":\"" + target + "\"}}";
            Assert.Throws<InvalidDataException>(() => EconomyCatalog.FromJson(json));
        }
    }
}
