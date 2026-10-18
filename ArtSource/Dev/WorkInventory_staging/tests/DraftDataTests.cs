using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using NUnit.Framework;
using OnlyVolunteers.Items.Core;
using OnlyVolunteers.Buyers;

namespace WorkInventory.Tests
{
    public sealed class DraftDataTests
    {
        private const string Root = @"C:\Dev\Game\docs\drafts\work_inventory\";
        [Test]
        public void BothRuntimeAssembliesAreNetStandardAndEngineFree()
        {
            foreach (var assembly in new[] { typeof(ItemLedger).Assembly, typeof(BuyerRules).Assembly })
            {
                var target = (System.Runtime.Versioning.TargetFrameworkAttribute)Attribute.GetCustomAttribute(assembly, typeof(System.Runtime.Versioning.TargetFrameworkAttribute));
                Assert.That(target.FrameworkName, Is.EqualTo(".NETStandard,Version=v2.1"));
                Assert.That(assembly.GetReferencedAssemblies().Any(a => a.Name.StartsWith("Unity", StringComparison.Ordinal) || a.Name.StartsWith("FishNet", StringComparison.Ordinal)), Is.False);
            }
        }
        [Test]
        public void AllDraftDefinitionsExactlyMatchCore()
        {
            using (var json = JsonDocument.Parse(File.ReadAllText(Root + "item_definitions_G39.json")))
            {
                var rows = json.RootElement.GetProperty("items").EnumerateArray().ToArray(); var defs = ItemCatalog.CreateDefaults();
                Assert.That(rows.Length, Is.EqualTo(18)); Assert.That(rows.Select(r => r.GetProperty("id").GetInt32()).Distinct().Count(), Is.EqualTo(18));
                foreach (var r in rows)
                {
                    Assert.That(defs.TryGet(r.GetProperty("id").GetInt32(), out var d), Is.True);
                    Assert.That(r.GetProperty("key").GetString(), Is.EqualTo(d.Key)); Assert.That(r.GetProperty("class").GetString(), Is.EqualTo(d.Class.ToString()));
                    Assert.That(r.GetProperty("maxStack").GetInt32(), Is.EqualTo(d.MaxStack)); Assert.That(r.GetProperty("twoHanded").GetBoolean(), Is.EqualTo(d.TwoHanded));
                    Assert.That(r.GetProperty("containerSlots").GetInt32(), Is.EqualTo(d.ContainerSlots));
                    Assert.That(r.GetProperty("organKind").GetString(), Is.EqualTo(d.Class == ItemClass.Organ ? d.Organ.ToString() : null));
                }
            }
        }
        [Test]
        public void EveryItemAndRefusalHasBothLanguages()
        {
            using (var json = JsonDocument.Parse(File.ReadAllText(Root + "localization_G39.json")))
            {
                foreach (var d in ItemCatalog.CreateDefaults().All)
                {
                    var text = json.RootElement.GetProperty("items").GetProperty(d.Key);
                    foreach (string key in new[] { "ru", "en", "hintRu", "hintEn" }) Assert.That(text.GetProperty(key).GetString(), Is.Not.Empty);
                }
                foreach (ItemError error in Enum.GetValues(typeof(ItemError)))
                {
                    var text = json.RootElement.GetProperty("refusals").GetProperty(error.ToString());
                    if (error != ItemError.None) foreach (string key in new[] { "ru", "en" }) Assert.That(text.GetProperty(key).GetString(), Is.Not.Empty);
                }
            }
        }
        [Test]
        public void QualityDraftMapsAllFiveScalesWithoutExtraTier()
        {
            using (var json = JsonDocument.Parse(File.ReadAllText(Root + "quality_and_tuning_G39.json")))
            {
                var tiers = json.RootElement.GetProperty("tiers").EnumerateArray().ToArray(); Assert.That(tiers.Length, Is.EqualTo(5));
                foreach (var t in tiers) Assert.That(t.GetProperty("tier").GetInt32(), Is.EqualTo(Tier.FromCaptureGrade(t.GetProperty("captureGrade").GetInt32())));
            }
        }
    }
}
