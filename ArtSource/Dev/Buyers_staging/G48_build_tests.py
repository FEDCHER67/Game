"""Install the G48 NUnit table/API checks; same sources run in Unity and the existing standalone runner."""
from pathlib import Path
path = Path('C:/Dev/Game/Assets/OnlyVolunteers/Buyers/Tests/EconomyDataTests.cs')
path.write_text(r'''using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using NUnit.Framework;

namespace OnlyVolunteers.Buyers.Tests
{
    public sealed class EconomyDataTests
    {
        private EconomyCatalog data;
        private static string DataPath([CallerFilePath] string source = "") =>
            Path.GetFullPath(Path.Combine(Path.GetDirectoryName(source), "..", "Data", "Economy_v01.json"));
        private static string Json() => File.ReadAllText(DataPath());
        [SetUp] public void LoadCatalog() { data = BuyerCatalog.LoadEconomy(Json()); }

        private void Prices(string section, string category, string[] ids, int[] expected)
        {
            Assert.That(data.Entries.Count(e => e.Category == category), Is.EqualTo(ids.Length), section + ": table row count");
            for (int i = 0; i < ids.Length; i++)
                Assert.That(data.GetPrice(ids[i]), Is.EqualTo(expected[i]), section + ": " + ids[i]);
        }

        [Test] public void Spec4_ConsumablesTable()
        {
            string[] ids = { "syringe_blood", "syringe_anaesthesia", "zip_tie", "zip_tie_pack_4", "blood_bag_empty", "organ_bag", "body_bag", "trash_bag", "head_bag", "anaesthesia_basic", "anaesthesia_improved", "anaesthesia_late" };
            Prices("§4 consumables", "consumable", ids, new[] {2,2,5,20,5,10,5,5,10,200,400,800});
            foreach (string id in ids)
            {
                var item = data.GetItem(id);
                Assert.That(item.EffectNote, Is.Not.Empty, "§4 effect: " + id);
                Assert.That(item.WhereSold, Does.Contain(id == "head_bag" ? "underground_supplier" : "pharmacy"), "§4 seller: " + id);
                Assert.That(item.Quantity, Is.EqualTo(id == "zip_tie_pack_4" ? 4 : 1), "§4 pack units: " + id);
                Assert.That(item.Unit, Is.Not.Empty, "§4 unit: " + id);
            }
            Assert.That(data.GetPrice("zip_tie_pack_4") / data.GetItem("zip_tie_pack_4").Quantity, Is.EqualTo(data.GetPrice("zip_tie")), "§15 A27/A28 no pack discount");
            foreach (string id in new[] {"anaesthesia_basic", "anaesthesia_improved", "anaesthesia_late"})
                Assert.That(data.GetItem(id).Unit, Is.EqualTo("vial"), "§15 A34 whole vials only: " + id);
            Assert.That(data.Get("trash_bag_capacity").Number("value"), Is.EqualTo(8), "§4 eligible trash capacity");
            Assert.That(data.Get("anaesthesia_basic_nominal_uses").Number("value"), Is.EqualTo(10), "§4 approximate nominal uses");
        }

        [Test] public void Spec4_PermanentEquipmentTable()
        {
            string[] ids = {"knife","patient_restraints","work_lamp","saw","hammer","osteotome","tray","tool_trolley","portable_fridge","stationary_fridge","mop_bucket","operating_table","rare_equipment"};
            Prices("§4 equipment", "equipment", ids, new[] {100,500,250,1500,300,100,100,500,1000,5000,100,1500,90000});
            foreach (string id in ids)
            {
                Assert.That(data.GetItem(id).EffectNote, Is.Not.Empty, "§4 equipment effect: " + id);
                Assert.That(data.GetItem(id).WhereSold, Does.Contain("exact per-item storefront open"), "§4.1 does not assign every equipment seller: " + id);
            }
            Assert.That(data.GetItem("patient_restraints").Quantity, Is.EqualTo(5), "§4 five table restraints");
            string[] metrics = {"portable_fridge_capacity","portable_fridge_hands","portable_fridge_spoil_minutes","stationary_fridge_capacity"};
            int[] values = {8,2,25,24};
            for (int i=0; i<metrics.Length; i++) Assert.That(data.Get(metrics[i]).Number("value"), Is.EqualTo(values[i]), "§4 " + metrics[i]);
        }

        [Test] public void Spec41_DeliveryAndInactiveReserve()
        {
            Assert.That(data.DeliveryGameHours, Is.EqualTo(1), "§4.1 / §15 A19: game hours, not real seconds");
            Assert.That(data.Get("delivery_game_hours").Unit, Is.EqualTo("game_hour"));
            Assert.That(data.Get("direct_to_bag").Status, Is.EqualTo("reserved"));
            Assert.That(data.GetPrice("direct_to_bag"), Is.EqualTo(1500));
            Assert.That(data.Get("quick_release").Status, Is.EqualTo("reserved"));
            Assert.That(data.GetPrice("quick_release"), Is.EqualTo(2000));
            Assert.Throws<ArgumentException>(() => data.GetItem("quick_release"), "Reserve is not an active shop item");
        }

        [Test] public void Spec5_SyringesAreTwoDollarsAndBloodSaleIsSeparate()
        {
            foreach (string id in new[] {"syringe_blood", "syringe_anaesthesia"})
            {
                Assert.That(data.GetPrice(id), Is.EqualTo(2), "§5 / §15 A29: " + id);
                Assert.That(data.GetItem(id).EffectNote, Does.Contain("same PersonId"), "§5 per-person reuse: " + id);
            }
            Assert.That(data.GetPrice("blood_syringe_first"), Is.EqualTo(10), "§5.3 first sale");
            Assert.That(data.GetPrice("blood_syringe_repeat"), Is.EqualTo(8), "§5.3 repeat sale");
        }

        [Test] public void Spec61_VanPricesTable()
        {
            string[] branches = {"engine", "handling", "brakes"};
            int[,] expected = {{0,1500,2250,3250},{0,1000,1750,2750},{0,750,1250,2000}};
            int[] totals = {7000,5500,4000};
            Assert.That(data.Entries.Count(e => e.Category == "van_tier"), Is.EqualTo(12), "§6.1 three branches, four tiers each");
            for (int b=0;b<branches.Length;b++)
            {
                decimal sum=0;
                for (int t=0;t<4;t++)
                {
                    string id = "van_" + branches[b] + "_" + t;
                    Assert.That(data.GetPrice(id), Is.EqualTo(expected[b,t]), "§6.1 price " + id);
                    sum += data.GetPrice(id);
                }
                Assert.That(sum, Is.EqualTo(totals[b]), "§15 A32 branch total " + branches[b]);
            }
            Assert.That(data.Entries.Where(e => e.Category == "van_tier").Sum(e => e.Price.Value), Is.EqualTo(16500), "§6.1 nine paid upgrades total");
        }

        [Test] public void Spec61_VanDrivePresetTable()
        {
            string[] branches = {"engine","engine","brakes","brakes","brakes","handling","handling","handling","handling"};
            string[] keys = {"speed_kmh","torque_multiplier","brake_torque_multiplier","handbrake_multiplier","longitudinal_grip_multiplier","lateral_grip_multiplier","anti_roll_multiplier","steering_response_multiplier","high_speed_steering_add_degrees"};
            decimal[,] expected = {{70,85,100,115},{1,1.12m,1.25m,1.40m},{1,1.15m,1.30m,1.45m},{1,1.08m,1.16m,1.24m},{1,1.05m,1.10m,1.15m},{1,1.06m,1.12m,1.20m},{1,1.12m,1.25m,1.40m},{1,1.10m,1.20m,1.30m},{0,1,2,3}};
            for(int row=0;row<keys.Length;row++) for(int t=0;t<4;t++)
                Assert.That(data.Get("van_" + branches[row] + "_" + t).Number(keys[row]), Is.EqualTo(expected[row,t]), "§6.1 preset " + keys[row] + " tier " + t);
        }

        [Test] public void Spec62_CargoUpgradeTable()
        {
            Prices("§6.2 cargo", "cargo", new[] {"van_storage","van_capacity_1","van_capacity_2"}, new[] {1500,2000,4000});
            Assert.That(data.Get("van_storage").Number("small_slots"), Is.EqualTo(12));
            Assert.That(data.Get("van_storage").Number("fridge_mounts"), Is.EqualTo(2));
            Assert.That(data.Get("van_storage").Number("mounted_fridge_items_total"), Is.EqualTo(16));
            for(int t=1;t<=2;t++)
            {
                Assert.That(data.Get("van_capacity_"+t).Number("from_npcs"), Is.EqualTo(t+2), "§6.2 previous capacity " + t);
                Assert.That(data.Get("van_capacity_"+t).Number("to_npcs"), Is.EqualTo(t+3), "§6.2 new capacity " + t);
            }
            Assert.That(data.Get("van_capacity_2").Reference("requires"), Is.EqualTo("van_capacity_1"));
        }

        [Test] public void Spec71_BasePricesAndCapacityTable()
        {
            string[] ids = {"base_wagon","base_hamlet","base_rough","base_downtown","base_lab"};
            Prices("§7.1 / §15 C5 bases", "base", ids, new[] {0,0,8100,33750,135000});
            for(int i=0;i<4;i++) Assert.That(data.GetBase(ids[i]).Number("table_capacity"), Is.EqualTo(i), "§7.1 capacity " + ids[i]);
            Assert.That(data.GetBase("base_lab").Numbers["table_capacity"], Is.Null, "§7.1 no fixed lab design limit; never zero capacity");
            Assert.That(data.GetPrice("van_initial_purchase"), Is.EqualTo(400), "§2 peaceful van + hamlet; no second premises payment");
            Assert.That(data.GetBasePrice("base_rough")+data.GetBasePrice("base_downtown")+data.GetBasePrice("base_lab"), Is.EqualTo(176850), "§7.1 final base sum");
        }

        [Test] public void Spec72_ElectricityTable()
        {
            string[] ids = {"base_wagon","base_hamlet","base_rough","base_downtown","base_lab"};
            int[] expected = {0,50,100,200,500};
            for(int i=0;i<ids.Length;i++) Assert.That(data.GetBase(ids[i]).Number("electricity_per_game_day"), Is.EqualTo(expected[i]), "§7.2 daily electricity " + ids[i]);
            foreach(int day in new[] {1,3,7}) Assert.That(data.Get("electricity_prepay_"+day).Number("value"), Is.EqualTo(day), "§7.2 prepaid days");
            foreach(int hour in new[] {6,1}) Assert.That(data.Get("electricity_warning_"+hour).Number("value"), Is.EqualTo(hour), "§7.2 warnings");
            Assert.That(data.Get("electricity_day_real_minutes").Number("value"), Is.EqualTo(45), "§7.2 active real minutes per game day");
        }

        [Test] public void Spec73_StaffTable()
        {
            string[] ids = {"staff_assistant","staff_specialist","staff_specialist_flawless"};
            Prices("§7.3 staff", "staff", ids, new[] {60000,120000,180000});
            decimal[] shares = {.1m,.2m,.2m};
            for(int i=0;i<ids.Length;i++) Assert.That(data.Get(ids[i]).Number("profit_share"), Is.EqualTo(shares[i]), "§7.3 profit share " + ids[i]);
            Assert.That(data.Get(ids[0]).Numbers["one_step_error_probability"], Is.Null, "Assistant does not extract organs");
            Assert.That(data.Get(ids[1]).Number("one_step_error_probability"), Is.EqualTo(.05m));
            Assert.That(data.Get(ids[2]).Number("one_step_error_probability"), Is.Zero);
        }

        [Test] public void Spec81_BuyerCoefficientAndQualityFloorTable()
        {
            string[] ids = {"buyer_first","buyer_medic","buyer_mafia"}; decimal[] coefficients = {1,1.5m,2.2m};
            for(int i=0;i<ids.Length;i++)
            {
                Assert.That(data.BuyerCoefficient(ids[i]), Is.EqualTo(coefficients[i]), "§8.1 / §15 B2 coefficient " + ids[i]);
                Assert.That((int)data.BuyerFloor(ids[i]), Is.EqualTo(i+1), "§8.1 floor " + ids[i]);
            }
            Assert.That(data.GetBuyer("buyer_first").Reference("existing_core_id"), Is.EqualTo(BuyerCatalog.OrganBuyer));
            Assert.That(data.GetBuyer("buyer_blood").Reference("existing_core_id"), Is.EqualTo(BuyerCatalog.BloodBuyer));
            Assert.Throws<InvalidOperationException>(() => data.BuyerCoefficient("buyer_blood"), "Blood has no organ coefficient");
            Assert.Throws<InvalidOperationException>(() => data.BuyerFloor("buyer_blood"), "Blood has no organ quality floor");
        }

        [Test] public void Spec32_OrganBaseAndQualityTables()
        {
            string[] ids = {"kidney","liver","eyes","brain","heart","lungs","blood_bag_sealed","blood_syringe_first","blood_syringe_repeat"};
            Prices("§3.2/§5.3 sale bases", "sale_product", ids, new[] {250,350,200,1200,1000,450,50,10,8});
            decimal[] multipliers = {.5m,1,1.5m,2.6m,6};
            for(int tier=1;tier<=5;tier++) Assert.That(data.QualityMultiplier((QualityTier)tier), Is.EqualTo(multipliers[tier-1]), "§3.2 current multiplier tier " + tier);
            Assert.That(data.GetPrice("kidney")*2+new[] {"liver","eyes","brain","heart","lungs"}.Sum(data.GetPrice), Is.EqualTo(3700), "§3.2 seven items; paired eyes/lungs");
            Assert.That(data.Get("eyes").Unit, Is.EqualTo("paired_item")); Assert.That(data.Get("lungs").Unit, Is.EqualTo("paired_item"));
        }

        [Test] public void Spec92_KidneyOrderRewardAndRequirements()
        {
            var mission = data.GetMission("mission_kidney_order");
            Assert.That(mission.Reference("buyer"), Is.EqualTo("buyer_first"));
            Assert.That(mission.Reference("target_npc_type"), Is.EqualTo(BuyerCatalog.OrderNpcType(OrderTemplate.HamletKidney)));
            Assert.That(mission.Number("minimum_tier"), Is.EqualTo((int)BuyerCatalog.OrderMinimum(OrderTemplate.HamletKidney)));
            Assert.That(data.MissionReward(mission.Id), Is.EqualTo(469), "§9.2 250 × 1.5 × 1.25, round once; no invented fixed reward");
            Assert.That(data.MissionReward(mission.Id, onTime:false), Is.EqualTo(375), "§9.1 late order loses only +25%");
            Assert.That(data.Get("special_order_game_hours").Number("value"), Is.EqualTo(48));
        }

        [Test] public void Spec93_MedicCaseRewardFormula()
        {
            int[] replacements={0,1,2,5,6,int.MaxValue}; int[] expected={1000,800,600,0,0,0};
            for(int i=0;i<replacements.Length;i++)
                Assert.That(data.MissionReward("mission_medic_case", replacements:replacements[i]), Is.EqualTo(expected[i]), "§9.3 max(0,1000-200*n), n="+replacements[i]);
            Assert.That(data.MissionReward("mission_medic_case", onTime:false, deliveredCooled:false, negotiatedPercent:20), Is.EqualTo(1000), "§9.3 courier ignores organ factors and deadlines");
        }

        [Test] public void Spec94_VipOrderTable()
        {
            string[] ids={"mission_vip_beastman","mission_vip_speedster","mission_vip_blindfold","mission_vip_altgirl"};
            string[] targets={"VIP_BEASTMAN","VIP_SPEEDSTER","VIP_BLINDFOLD","BAD_ALTGIRL"};
            string[] organs={"heart","lungs","eyes","brain"}; int[] floors={4,3,4,3}; int[] bonus={15000,10000,15000,10000};
            int[] payouts={22150,11856,16430,14950}; int[] late={5720,1485,1144,3960};
            for(int i=0;i<ids.Length;i++)
            {
                var mission=data.GetMission(ids[i]);
                Assert.That(mission.Reference("target_npc_type"), Is.EqualTo(targets[i]), "§9.4 target " + ids[i]);
                Assert.That(mission.Reference("product"), Is.EqualTo(organs[i]), "§9.4 organ " + ids[i]);
                Assert.That(mission.Reference("buyer"), Is.EqualTo("buyer_mafia"), "§15 D1 provider " + ids[i]);
                Assert.That(mission.Number("minimum_tier"), Is.EqualTo(floors[i]), "§15 D5 floor " + ids[i]);
                Assert.That(mission.Number("on_time_fixed_bonus"), Is.EqualTo(bonus[i]), "§15 D6 bonus " + ids[i]);
                Assert.That(data.MissionReward(ids[i]), Is.EqualTo(payouts[i]), "§12.5 rounded projection " + ids[i]);
                Assert.That(data.MissionReward(ids[i], onTime:false), Is.EqualTo(late[i]), "§9.4 late: zero fixed bonus, zero uplift " + ids[i]);
            }
            Assert.That(ids.Sum(id=>data.GetMission(id).Number("on_time_fixed_bonus")), Is.EqualTo(50000), "§9.4 fixed bonuses total, not multiplied");
        }

        [TestCase("engine",0,1500)] [TestCase("engine",1,2250)] [TestCase("engine",2,3250)]
        [TestCase("handling",0,1000)] [TestCase("handling",1,1750)] [TestCase("handling",2,2750)]
        [TestCase("brakes",0,750)] [TestCase("brakes",1,1250)] [TestCase("brakes",2,2000)]
        public void Api_NextVanTierIsSequentialAndHasItsProfile(string branch,int current,int price)
        {
            var next=data.GetNextVanTier(branch,current);
            Assert.That(next.Id, Is.EqualTo("van_"+branch+"_"+(current+1)));
            Assert.That(next.Price, Is.EqualTo(price)); Assert.That(next.Number("tier"), Is.EqualTo(current+1));
            Assert.That(next.Numbers.Count, Is.GreaterThan(1), "Next tier includes profile and price");
        }

        [Test] public void Api_MaxVanTierAndInvalidInputs()
        {
            Assert.That(data.GetNextVanTier("engine",3), Is.Null);
            Assert.Throws<ArgumentOutOfRangeException>(()=>data.GetNextVanTier("engine",-1));
            Assert.Throws<ArgumentOutOfRangeException>(()=>data.GetNextVanTier("engine",4));
            Assert.Throws<ArgumentException>(()=>data.GetNextVanTier("unknown",0));
            Assert.Throws<KeyNotFoundException>(()=>data.GetPrice("missing"));
            Assert.Throws<ArgumentException>(()=>data.GetBasePrice("syringe_blood"));
            Assert.Throws<ArgumentOutOfRangeException>(()=>data.MissionReward("mission_medic_case",replacements:-1));
            Assert.Throws<ArgumentOutOfRangeException>(()=>data.MissionReward("mission_kidney_order",quality:QualityTier.Damaged));
        }

        [Test] public void Api_OpenValuesStayOpenAndAreNeverFreePurchases()
        {
            string[] ids={"van_glass_price","van_hidden_compartment_price","unpacked_blood_freshness_seconds","streamer_search_hours"};
            foreach(string id in ids)
            {
                Assert.That(data.Get(id).Status, Is.EqualTo("open"), id); Assert.That(data.Get(id).Price, Is.Null, id);
                Assert.That(data.TryGetPrice(id,out _), Is.False, id); Assert.Throws<InvalidOperationException>(()=>data.GetPrice(id),id);
            }
            Assert.That(data.TryGetPrice("base_wagon",out var zero), Is.True); Assert.That(zero, Is.Zero);
            Assert.That(data.TryGetPrice("missing",out _), Is.False);
        }

        [Test] public void Api_EntriesAndNestedValuesCannotBeMutated()
        {
            Assert.Throws<NotSupportedException>(()=>((IList<EconomyEntry>)data.Entries).Clear());
            Assert.Throws<NotSupportedException>(()=>((IDictionary<string,decimal?>)data.Get("van_engine_1").Numbers)["torque_multiplier"]=99);
            Assert.Throws<NotSupportedException>(()=>((IDictionary<string,string>)data.GetMission("mission_kidney_order").References)["buyer"]="buyer_mafia");
            Assert.That(data.Get("van_engine_1").Number("torque_multiplier"), Is.EqualTo(1.12m));
        }

        [Test] public void Api_LoadsActualJsonAndKeepsInstancesIndependent()
        {
            var changed=EconomyCatalog.FromJson(Json().Replace("\"price\": 2,", "\"price\": 3,"));
            Assert.That(changed.GetPrice("syringe_blood"), Is.EqualTo(3), "Price read from JSON, not a copied C# table");
            Assert.That(data.GetPrice("syringe_blood"), Is.EqualTo(2), "No global mutable catalog");
            Assert.That(EconomyCatalog.Load(DataPath()).Id, Is.EqualTo("economy_v01"));
            Assert.Throws<ArgumentException>(()=>EconomyCatalog.Load("relative.json"));
        }

        [Test] public void Api_RejectsMalformedSchemaDuplicateIdsAndInventedOpenNumbers()
        {
            Assert.Throws<ArgumentException>(()=>EconomyCatalog.FromJson(""));
            Assert.Throws<InvalidDataException>(()=>EconomyCatalog.FromJson(Json().Replace("\"schemaVersion\": 1", "\"schemaVersion\": 99")));
            Assert.Throws<InvalidDataException>(()=>EconomyCatalog.FromJson(Json().Replace("\"id\": \"syringe_anaesthesia\"", "\"id\": \"syringe_blood\"")));
            Assert.Throws<InvalidDataException>(()=>EconomyCatalog.FromJson(Json().Replace("\"id\": \"syringe_blood\"", "\"id\": \"BAD_ID\"")));
            Assert.Throws<InvalidDataException>(()=>EconomyCatalog.FromJson(Json().Replace("\"price\": 2,", "\"price\": -1,")));
            Assert.Throws<InvalidDataException>(()=>EconomyCatalog.FromJson(Json().Replace("\"status\": \"confirmed\"", "\"status\": \"open\"")));
        }

        [Test] public void Api_ExistingBuyersFormulaUsesCatalogFactors()
        {
            decimal[] expected={375,562.5m,825}; string[] buyers={"buyer_first","buyer_medic","buyer_mafia"};
            for(int i=0;i<buyers.Length;i++) Assert.That(BuyerCatalog.UnitPrice(data,buyers[i],ProductKind.Kidney,QualityTier.Good,0,false,true,0,false), Is.EqualTo(expected[i]), "§3.3 Good kidney " + buyers[i]);
            Assert.That(BuyerCatalog.UnitPrice(data,"buyer_mafia",ProductKind.Kidney,QualityTier.Good,0,true,true,6,true), Is.EqualTo(1031.25m), "§3.3 special has no saturation");
            Assert.That(BuyerCatalog.UnitPrice(data,"buyer_first",ProductKind.Kidney,QualityTier.Good,0,false,false,1,false), Is.EqualTo(320.625m));
            Assert.That(BuyerCatalog.UnitPrice(data,"buyer_blood",ProductKind.IntroSyringe,QualityTier.PerfectPlus,20,true,false,6,false,false), Is.EqualTo(8));
            Assert.That(BuyerCatalog.UnitPrice(data,"buyer_blood",ProductKind.BloodBag,QualityTier.Damaged,20,true,false,6,false), Is.EqualTo(60));
            Assert.Throws<ArgumentOutOfRangeException>(()=>BuyerCatalog.UnitPrice(data,"buyer_mafia",ProductKind.Kidney,QualityTier.Acceptable,0,false,true,0,false));
            Assert.Throws<ArgumentOutOfRangeException>(()=>BuyerCatalog.UnitPrice(data,"buyer_first",ProductKind.Kidney,QualityTier.Good,7,false,true,0,false));
        }

        [Test] public void Api_VipFixedBonusIsNotMultiplied()
        {
            decimal expected=Math.Round(1000m*6m*2.2m*1.25m*.9m*1.2m+15000m,0,MidpointRounding.AwayFromZero);
            Assert.That(data.MissionReward("mission_vip_beastman",quality:QualityTier.PerfectPlus,deliveredCooled:false,negotiatedPercent:20), Is.EqualTo(expected));
        }
    }
}
''', encoding='utf-8')
print(path)
