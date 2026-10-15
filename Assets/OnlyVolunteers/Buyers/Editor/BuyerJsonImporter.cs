using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using OnlyVolunteers.Buyers.Data;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Buyers.Editor
{
    /// <summary>Explicit authoring import only. No automatic import, startup hook or gameplay rules.</summary>
    public static class BuyerJsonImporter
    {
        private const string DataPath = "Assets/OnlyVolunteers/Buyers/Data/";
        private const string ItemPath = "Assets/OnlyVolunteers/Inventory/Items/";

        private static readonly ImportSpec[] Manifest =
        {
            new ImportSpec("Buyer_C01_v01", typeof(BuyerDefinition)),
            new ImportSpec("Buyer_FirstOrganFence_v01", typeof(BuyerDefinition)),
            new ImportSpec("SpecialOrder_HamletBodybuilderKidney_v01", typeof(SpecialOrderDefinition)),
            new ImportSpec("SpecialOrder_OldStreamerBrain_v01", typeof(SpecialOrderDefinition)),
            new ImportSpec("QualityTierTable_v01", typeof(QualityTierTable)),
            new ImportSpec("RespectLevelTable_v01", typeof(RespectLevelTable))
        };

        [MenuItem("OnlyVolunteers/Buyers/Import JSON v01")]
        public static void ImportV01()
        {
            var staged = new List<ScriptableObject>();
            try
            {
                var inventoryIds = ReadInventoryIds();
                var contentIds = new HashSet<string>(StringComparer.Ordinal);
                // Parse and validate ALL sources and existing destinations before the first write.
                foreach (var spec in Manifest)
                {
                    string source = Path.Combine(Path.GetDirectoryName(Application.dataPath), DataPath + spec.Name + ".json");
                    string json = File.ReadAllText(source, Encoding.UTF8);
                    var header = JsonUtility.FromJson<Header>(json);
                    Require(header != null && header.schemaVersion == 1, spec.Name + ": expected schemaVersion 1.");
                    Require(header != null && !string.IsNullOrWhiteSpace(header.id) && contentIds.Add(header.id), spec.Name + ": missing or duplicate id.");
                    var value = ScriptableObject.CreateInstance(spec.Type);
                    staged.Add(value);
                    JsonUtility.FromJsonOverwrite(json, value);
                    value.name = spec.Name;
                    Validate(value, inventoryIds);
                    WarnPlaceholders(value);

                    string destination = DataPath + spec.Name + ".asset";
                    var existing = AssetDatabase.LoadMainAssetAtPath(destination);
                    Require(existing == null || existing.GetType() == spec.Type, destination + ": incompatible existing asset type.");
                    Require(existing != null || !File.Exists(Path.ChangeExtension(source, ".asset")), destination + ": existing file is not a loadable asset; resolve it before import.");
                }

                for (int i = 0; i < Manifest.Length; i++)
                {
                    string destination = DataPath + Manifest[i].Name + ".asset";
                    var existing = AssetDatabase.LoadMainAssetAtPath(destination);
                    if (existing == null)
                    {
                        AssetDatabase.CreateAsset(staged[i], destination);
                    }
                    else
                    {
                        // Update in place: keep the destination's GUID and all external references.
                        EditorUtility.CopySerialized(staged[i], existing);
                        EditorUtility.SetDirty(existing);
                    }
                    AssetDatabase.SaveAssetIfDirty(existing != null ? existing : staged[i]);
                }
                Debug.Log("Buyers v01: imported 6 data assets. Resolve PLACEHOLDER warnings and unresolved blood item IDs before gameplay integration. Late streamer order remains outside the first-version offer pool.");
            }
            catch (Exception exception)
            {
                Debug.LogError("Buyers JSON import failed: " + exception.Message + "\nValidation precedes writes; an I/O failure during saving can leave a partial import. Fix the cause and rerun the menu.");
            }
            finally
            {
                foreach (var value in staged)
                    if (value != null && !AssetDatabase.Contains(value))
                        UnityEngine.Object.DestroyImmediate(value);
            }
        }

        private static HashSet<int> ReadInventoryIds()
        {
            var ids = new HashSet<int>();
            string absolute = Path.Combine(Application.dataPath, "OnlyVolunteers/Inventory/Items");
            foreach (string file in Directory.GetFiles(absolute, "Item_*.asset", SearchOption.TopDirectoryOnly))
            {
                string path = ItemPath + Path.GetFileName(file);
                var item = AssetDatabase.LoadMainAssetAtPath(path);
                Require(item != null, path + ": could not load inventory definition.");
                var serialized = new SerializedObject(item);
                var id = serialized.FindProperty("id");
                Require(id != null && id.propertyType == SerializedPropertyType.Integer, path + ": missing integer id.");
                Require(id.intValue > 0 && ids.Add(id.intValue), path + ": invalid or duplicate item id.");
            }
            Require(ids.Count > 0, "No existing inventory Item_*.asset IDs found.");
            return ids;
        }

        private static void Validate(ScriptableObject value, HashSet<int> inventoryIds)
        {
            if (value is BuyerDefinition buyer)
            {
                Names(buyer.displayNameRu, buyer.displayNameEn);
                Require(buyer.minimumTier >= 0 && buyer.minimumTier <= 5, buyer.id + ": invalid minimum tier.");
                Require(buyer.meetingType == "base" || buyer.meetingType == "point", buyer.id + ": invalid meeting type.");
                Require(buyer.workingHours != null && buyer.workingHours.startHour >= 0 && buyer.workingHours.startHour < 24 && buyer.workingHours.endHour >= 0 && buyer.workingHours.endHour <= 24, buyer.id + ": invalid hours.");
                Require(!string.IsNullOrWhiteSpace(buyer.voiceId), buyer.id + ": missing voice id.");
                Conditions(buyer.unlockCondition);
                TextIds(buyer.textIds);
                Require(buyer.acceptedMerchandise != null && buyer.acceptedMerchandise.Length > 0, buyer.id + ": empty merchandise.");
                var keys = new HashSet<string>(StringComparer.Ordinal);
                foreach (var item in buyer.acceptedMerchandise)
                {
                    Require(item != null && !string.IsNullOrWhiteSpace(item.merchandiseId) && keys.Add(item.merchandiseId), buyer.id + ": missing or duplicate merchandise key.");
                    Require(item.packaging == "none" || item.packaging == "sealed_blood_bag" || item.packaging == "filled_syringe" || item.packaging == "sealed_individual_organ_bag", buyer.id + ": invalid packaging descriptor.");
                    Require(item.hasQuality ? buyer.minimumTier >= 1 : buyer.minimumTier == 0, buyer.id + ": quality applicability mismatch.");
                    Require(Finite(item.fixedBasePriceDollars) && item.fixedBasePriceDollars >= 0, buyer.id + ": invalid price data.");
                    if (item.itemIdUnresolved)
                    {
                        Require(item.itemId == 0 && !item.hasQuality, buyer.id + ": unresolved IDs are allowed only for explicitly flagged blood entries.");
                        Debug.LogWarning(buyer.id + "/" + item.merchandiseId + ": Inventory item ID unresolved (0). This is authoring data, not a usable Inventory ID.");
                    }
                    else
                        Require(inventoryIds.Contains(item.itemId), buyer.id + ": unknown Inventory item id " + item.itemId);
                }
            }
            else if (value is SpecialOrderDefinition order)
            {
                Names(order.displayNameRu, order.displayNameEn);
                Require(!string.IsNullOrWhiteSpace(order.offeringBuyerId) && !string.IsNullOrWhiteSpace(order.targetNpcTypeId), order.id + ": missing provider/target.");
                Require(inventoryIds.Contains(order.organItemId), order.id + ": unknown organ item id.");
                Require(order.minimumTier >= 1 && order.minimumTier <= 5, order.id + ": invalid organ tier.");
                Require(order.packaging == "sealed_individual_organ_bag", order.id + ": expected sealed individual organ packaging.");
                Require(order.deadlineGameHours > 0 && Finite(order.premium) && order.premium >= 0, order.id + ": invalid deadline/premium.");
                Require(!string.IsNullOrWhiteSpace(order.stashId) && !string.IsNullOrWhiteSpace(order.cluePhotoId), order.id + ": missing stash/photo id.");
                Require(order.requiresClueTargetIdentity, order.id + ": specific clue NPC identity must be required.");
                Conditions(order.unlockCondition);
                TextIds(order.clueTextIds);
            }
            else if (value is QualityTierTable quality)
            {
                Require(quality.tiers != null && quality.tiers.Length == 5, "Expected exactly five quality tiers.");
                for (int i = 0; i < quality.tiers.Length; i++)
                {
                    var tier = quality.tiers[i];
                    Require(tier != null && tier.tier == i + 1, "Quality tiers must be ordered 1..5.");
                    Names(tier.displayNameRu, tier.displayNameEn);
                    Require(!string.IsNullOrWhiteSpace(tier.percentLabel) && Finite(tier.multiplier) && tier.multiplier > 0, "Invalid tier label/multiplier.");
                    Require(Unit(tier.colour.r) && Unit(tier.colour.g) && Unit(tier.colour.b) && Unit(tier.colour.a), "Color channels must be finite and within 0..1.");
                }
            }
            else if (value is RespectLevelTable respect)
            {
                Require(respect.minimum == 0 && respect.maximum == 100 && respect.initialValue >= respect.minimum && respect.initialValue <= respect.maximum, "Invalid respect range/start.");
                Require(respect.levels != null && respect.levels.Length == 5, "Expected exactly five respect levels.");
                int next = respect.minimum;
                for (int i = 0; i < respect.levels.Length; i++)
                {
                    var level = respect.levels[i];
                    Require(level != null && level.level == i + 1 && level.minimumInclusive == next && level.maximumInclusive >= next && level.maximumInclusive <= respect.maximum, "Respect ranges must be ordered, contiguous and nonoverlapping.");
                    Names(level.displayNameRu, level.displayNameEn);
                    next = level.maximumInclusive + 1;
                }
                Require(next == respect.maximum + 1, "Respect ranges must cover the complete scale.");
            }
        }

        private static void Conditions(UnlockCondition condition)
        {
            Require(condition != null && condition.all != null && condition.all.Length > 0, "Missing unlock requirements.");
            foreach (var requirement in condition.all)
            {
                Require(requirement != null && !string.IsNullOrWhiteSpace(requirement.subjectId), "Missing unlock subject.");
                Require(requirement.kind == "contact_available" || requirement.kind == "first_successful_blood_sale" || requirement.kind == "respect_at_least" || requirement.kind == "owns_tool" || requirement.kind == "district_access", "Unknown declarative unlock kind.");
                Require(requirement.minimumValue >= 0, "Invalid unlock threshold.");
            }
        }

        private static void TextIds(string[] ids)
        {
            Require(ids != null && ids.Length > 0, "Missing text IDs.");
            foreach (string id in ids) Require(!string.IsNullOrWhiteSpace(id), "Empty text ID.");
        }

        private static void Names(string ru, string en)
        {
            Require(!string.IsNullOrWhiteSpace(ru) && !string.IsNullOrWhiteSpace(en), "Missing RU/EN display names.");
        }

        private static void WarnPlaceholders(ScriptableObject value)
        {
            var iterator = new SerializedObject(value).GetIterator();
            while (iterator.Next(true))
                if (iterator.propertyType == SerializedPropertyType.String && iterator.stringValue.StartsWith("PLACEHOLDER.", StringComparison.Ordinal))
                    Debug.LogWarning(value.name + "/" + iterator.propertyPath + ": unresolved " + iterator.stringValue);
        }

        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Unit(float value) => Finite(value) && value >= 0 && value <= 1;
        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidDataException(message);
        }

        [Serializable]
        private sealed class Header
        {
            public int schemaVersion;
            public string id;
        }

        private sealed class ImportSpec
        {
            public readonly string Name;
            public readonly Type Type;
            public ImportSpec(string name, Type type) { Name = name; Type = type; }
        }
    }
}
