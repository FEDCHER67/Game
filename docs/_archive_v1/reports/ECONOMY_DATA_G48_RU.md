# G48 — единые данные экономики v01

28.10.2026, Феде. Расширен существующий `OnlyVolunteers.Buyers.Core`: 96 стабильных ID в `Economy_v01.json`, загрузчик и неизменяемый API чтения. Источник — ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01 целиком, финальные замены §15 имеют приоритет. `noEngineReferences=true`, зависимости/пакеты/asmdef не менялись.

Покрыты расходники, постоянное оборудование, единицы/упаковки, эффект и место продажи, шприцы, 0–III всех трёх веток машины и их профили, грузовые улучшения, базы/вместимость/электричество, персонал, коэффициенты/минимумы покупателей, доставка за игровой час, кейс, почка, поздний стример и четыре VIP. Дополнительно включены базовые цены органов/крови и актуальные множители качества для расчёта наград.

Денежного состояния, записи денег, покупок или адаптеров фонда API не содержит. `BuyerRules`, `BuyerState`, `BuyerOrders`, `BuyerTransactions`, runtime машины/телефона/захвата/операций и сцены G48 не редактировал. Чужие изменения в этих файлах сохранены. Спецификация остаётся untracked; staging/commit/push не выполнялись.

## Проверка

- PASS — Roslyn `unity_compile_check.py --project C:\Dev\Game --files <BuyerCatalog.cs, EconomyCatalog.cs, EconomyDataTests.cs> --dependents`: Core, Buyers.Tests, Assembly-CSharp, Assembly-CSharp-Editor; `COMPILE_OK`. Использованы абсолютные пути, TEMP/TMP и .NET-каталоги внутри репозитория.
- PASS — `C:\Dev\Game\ArtSource\Dev\Buyers_staging\Run-Tests.ps1`: **163 всего, 163 PASS, 0 FAIL, 0 пропусков**. **31 новая** проверка G48 и все **132 остальные** проверки текущей рабочей копии прошли (130 прежних плюс 2 добавленные параллельно). Параллельный владелец повторной продажи обновил свой прежний тест под $10→$8; этот файл G48 не редактировал.
- PASS — Unity 6000.5.11f1, EditMode, assembly_names=[OnlyVolunteers.Buyers.Tests]: **163/163 PASS**, 0 FAIL/skip; 31 G48 + 132 остальные. Job `b096fd290bd44395ac4e8c88f99273be`, 17:07 МСК. Полные результаты: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\G48-unity-editmode.json`. После refresh/compile домен готов; Console errors=0. Play=false, исходная Map_W85_Play_v02 сохранена без переключения/сохранения сцены. Lock отпущен с `-Done` сразу после проверки.
- TRX и полный stdout: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\TestResults\buyers-results.trx`, `C:\Dev\Game\ArtSource\Dev\Buyers_staging\test-output.txt`.

Unity preflight: существующий Editor PID 11892, `Game@b321844a`, session `70328105-4aec-4959-bed4-662c662886a7`, путь `C:/Dev/Game`, версия `6000.5.11f1`, Play=false. Lock G48 получен и отпущен после проверки/установки. Unity CLI 1.0.0-beta.14 проверен; Pipeline отсутствует. Использован существующий CoplayDev MCP согласно docs/AgentRules.md и переданному HANDOFF; второй мост не устанавливался. Editor/сцена не переключались; новый процесс Unity не запускался.

## Спецификация → данные → тест

Все новые тесты: `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\EconomyDataTests.cs`. Одни и те же исходники связаны существующим standalone runner и Editor-only NUnit asmdef.

| § | Данные | Тест |
|---|---|---|
| 4, расходники | 12 записей consumable, упаковки/продавцы/эффекты | Spec4_ConsumablesTable |
| 4, оборудование | 13 записей equipment, ёмкости/руки/порча | Spec4_PermanentEquipmentTable |
| 4.1 / 15 A19 | delivery_game_hours; inactive reserve | Spec41_DeliveryAndInactiveReserve |
| 5 / 15 A29 | оба syringe_*; цены продажи крови отдельно | Spec5_SyringesAreTwoDollarsAndBloodSaleIsSeparate |
| 6.1 / 15 A32, цены | 12 van_*_0..3, девять платных покупок | Spec61_VanPricesTable |
| 6.1, пресеты | speed/torque/brakes/handbrake/grip/antiroll/steering | Spec61_VanDrivePresetTable |
| 6.2 | van_storage, van_capacity_1/2 | Spec62_CargoUpgradeTable |
| 7.1 / 15 C5 | base_*; пределы столов; §2 мирная цена машины | Spec71_BasePricesAndCapacityTable |
| 7.2 | дневные счета по базе; 1/3/7 дней, 45 минут, 6/1 ч | Spec72_ElectricityTable |
| 7.3 | staff_*: найм, доля прибыли, ошибки | Spec73_StaffTable |
| 8.1 / 15 B2 | buyer_*: ×1/1.5/2.2, минимумы 1/2/3 | Spec81_BuyerCoefficientAndQualityFloorTable |
| 3.2–3.3 / 5.3 | sale_product, quality_* | Spec32_OrganBaseAndQualityTables |
| 9.1–9.2 | mission_kidney_order; формула, Good, +25%, 48 ч | Spec92_KidneyOrderRewardAndRequirements |
| 9.3 / 15 B12–B13 | mission_medic_case: max(0,1000−200n) | Spec93_MedicCaseRewardFormula |
| 9.4 / 15 D5–D6 | четыре mission_vip_*, органы/грейды/премии | Spec94_VipOrderTable |
| API | JSON, независимость экземпляров, readonly, unknown/open, ступени, формула, VIP | Api_* (16 случаев вместе с параметрами) |

## API для Claude

Namespace `OnlyVolunteers.Buyers`. Загрузить один раз и держать экземпляр:

```csharp
var economy = BuyerCatalog.LoadEconomy(economyTextAsset.text);
// Also: EconomyCatalog.FromJson(json), EconomyCatalog.Load(absoluteJsonPath).
decimal price = economy.GetPrice("syringe_blood");
var item = economy.GetItem("zip_tie_pack_4"); // Price, Quantity=4, Unit, EffectNote, WhereSold.
var next = economy.GetNextVanTier("engine", currentTier); // null at III.
decimal nextPrice = next.Price.Value;
decimal torque = next.Number("torque_multiplier");
decimal basePrice = economy.GetBasePrice("base_rough");
decimal coefficient = economy.BuyerCoefficient("buyer_medic");
QualityTier minimum = economy.BuyerFloor("buyer_mafia");
decimal reward = economy.MissionReward("mission_medic_case", replacements: 2); // 600; no payout.
```

Полный набор: `Entries`, `Get`, `GetPrice`, `TryGetPrice`, `GetItem`, `GetNextVanTier`, `GetBase`, `GetBasePrice`, `GetBuyer`, `BuyerCoefficient`, `BuyerFloor`, `GetMission`, `MissionReward`, `QualityMultiplier`, `DeliveryGameHours`. Запись возвращает только get-свойства и readonly коллекции `Numbers`/`References`; `Number(key)`/`Reference(key)` читают вложенные поля. `Spec` хранит происхождение каждой записи. `Quantity` — число единиц в продаваемой упаковке, `Price` — стоимость всей упаковки.

`BuyerCatalog.UnitPrice(economy, buyerId, kind, tier, negotiatedPercent, onTimeSpecial, deliveredCooled, unitsAlreadySold, isSpecial, introductoryBloodSale=true)` использует тот же общий расчёт факторов Buyers, актуальные JSON-цены/качество и коэффициент покупателя. Возвращает неокруглённую цену единицы. `MissionReward` округляет один раз (половины от нуля), VIP-премию прибавляет после множителей; кейс не умножает. Это прогноз, он не завершает/не оплачивает миссию. PersonId, уникальность, права, состояние сроков и покупки проверяет владелец runtime.

`GetNextVanTier` принимает `engine`, `handling`, `brakes` и фактический текущий уровень 0..3. Ветви независимы. В ответе — цена следующей ступени и только свойства своей ветви; параметры относительны новому профилю 0. Старый `BuyerCatalog.UnitPrice` без economy сохраняет совместимость старого G27; новые потребители должны передавать загруженный catalog. Старые authoring JSON/SO Buyers не переимпортированы и не являются источником новых чисел. `EconomyPrices` Claude должен читать этот API, без копирования таблиц. Его временные c01_blood_first/c01_blood_repeat соответствуют blood_syringe_first/blood_syringe_repeat; это не новые Inventory ID.

Importer не менялся: новый JSON остаётся обычным TextAsset; Core принимает его текст напрямую. SO/автоматический import-hook и второй набор runtime-правил не добавлены. Гарантии этой задачи — данные/чистые расчёты, не интеграция магазина, фонда, доставки, NPC, сетевого сохранения или вождения.

## Открытое

- `van_glass_price`, `van_hidden_compartment_price`: цена/эффект не назначены, `status=open`, `price=null`; не продавать.
- `unpacked_blood_freshness_seconds`: Proposed 120 секунд не превращены в подтверждённое значение.
- `streamer_search_hours`: часы/область/фото/конкретный NPC относятся к контенту и не придуманы. Подтверждённый провайдер позднего заказа — медик.
- Лаборатория: `table_capacity=null` означает отсутствие фиксированного проектного лимита, а не ноль и не обещание бесконечной производительности. Для C01 organ coefficient/minimum неприменимы; у помощника ошибка извлечения неприменима — тоже null.
- §4.1 называет категории продавцов, но не назначает каждый вид оборудования конкретному прилавку. Сохранены underground_supplier/phone_delivery с явным `exact per-item storefront open`.
- `direct_to_bag` $1500 и `quick_release` $2000 — `reserved`, не активные GetItem-позиции. Приблизительные 10 применений базового флакона остаются приблизительными.
- Не назначались физические Inventory ItemId, голоса, геометрия/якоря/тайники и общая миссионная XP-система. Экономические string ID — ключи каталога, не обещание существующего ресурса.

## Полный список ID → значения → §

`price` — доллары за указанную единицу/упаковку. Остальные числа указаны с именами полей; комиссия/вероятность — доли единицы. Для unit/quantity/effect/seller см. ту же запись JSON. Все ключи каталога — lowercase snake_case; ссылки на прежние Core/NPC ID сохраняют существующие имена.

| ID | Значения | § |
|---|---|---|
| `syringe_blood` | $2 / syringe | 4, 5 |
| `syringe_anaesthesia` | $2 / empty_syringe | 4, 5 |
| `zip_tie` | $5 / tie | 4 |
| `zip_tie_pack_4` | $20 / pack (units=4) | 4 |
| `blood_bag_empty` | $5 / bag | 4 |
| `organ_bag` | $10 / bag | 4 |
| `body_bag` | $5 / bag | 4 |
| `trash_bag` | $5 / bag | 4 |
| `head_bag` | $10 / bag | 4 |
| `anaesthesia_basic` | $200 / vial | 4 |
| `anaesthesia_improved` | $400 / vial | 4 |
| `anaesthesia_late` | $800 / vial | 4 |
| `knife` | $100 / item | 4, 4.1 |
| `patient_restraints` | $500 / set (units=5) | 4, 4.1 |
| `work_lamp` | $250 / item | 4, 4.1 |
| `saw` | $1500 / item | 4, 4.1 |
| `hammer` | $300 / item | 4, 4.1 |
| `osteotome` | $100 / item | 4, 4.1 |
| `tray` | $100 / item | 4, 4.1 |
| `tool_trolley` | $500 / item | 4, 4.1 |
| `portable_fridge` | $1000 / item | 4, 4.1 |
| `stationary_fridge` | $5000 / item | 4, 4.1 |
| `mop_bucket` | $100 / set | 4, 4.1 |
| `operating_table` | $1500 / item | 4, 4.1 |
| `rare_equipment` | $90000 / item | 4, 4.1 |
| `direct_to_bag` | $1500 / upgrade; reserved | 4.1 |
| `quick_release` | $2000 / upgrade; reserved | 4.1 |
| `delivery_game_hours` | value=1 | 4.1, 15.A19 |
| `van_engine_0` | $0 / tier; tier=0; speed_kmh=70; torque_multiplier=1; branch=engine | 6.1, 15.A32 |
| `van_engine_1` | $1500 / tier; tier=1; speed_kmh=85; torque_multiplier=1.12; branch=engine | 6.1, 15.A32 |
| `van_engine_2` | $2250 / tier; tier=2; speed_kmh=100; torque_multiplier=1.25; branch=engine | 6.1, 15.A32 |
| `van_engine_3` | $3250 / tier; tier=3; speed_kmh=115; torque_multiplier=1.4; branch=engine | 6.1, 15.A32 |
| `van_handling_0` | $0 / tier; tier=0; lateral_grip_multiplier=1; anti_roll_multiplier=1; steering_response_multiplier=1; high_speed_steering_add_degrees=0; branch=handling | 6.1, 15.A32 |
| `van_handling_1` | $1000 / tier; tier=1; lateral_grip_multiplier=1.06; anti_roll_multiplier=1.12; steering_response_multiplier=1.1; high_speed_steering_add_degrees=1; branch=handling | 6.1, 15.A32 |
| `van_handling_2` | $1750 / tier; tier=2; lateral_grip_multiplier=1.12; anti_roll_multiplier=1.25; steering_response_multiplier=1.2; high_speed_steering_add_degrees=2; branch=handling | 6.1, 15.A32 |
| `van_handling_3` | $2750 / tier; tier=3; lateral_grip_multiplier=1.2; anti_roll_multiplier=1.4; steering_response_multiplier=1.3; high_speed_steering_add_degrees=3; branch=handling | 6.1, 15.A32 |
| `van_brakes_0` | $0 / tier; tier=0; brake_torque_multiplier=1; handbrake_multiplier=1; longitudinal_grip_multiplier=1; branch=brakes | 6.1, 15.A32 |
| `van_brakes_1` | $750 / tier; tier=1; brake_torque_multiplier=1.15; handbrake_multiplier=1.08; longitudinal_grip_multiplier=1.05; branch=brakes | 6.1, 15.A32 |
| `van_brakes_2` | $1250 / tier; tier=2; brake_torque_multiplier=1.3; handbrake_multiplier=1.16; longitudinal_grip_multiplier=1.1; branch=brakes | 6.1, 15.A32 |
| `van_brakes_3` | $2000 / tier; tier=3; brake_torque_multiplier=1.45; handbrake_multiplier=1.24; longitudinal_grip_multiplier=1.15; branch=brakes | 6.1, 15.A32 |
| `van_storage` | $1500 / upgrade; small_slots=12; fridge_mounts=2; mounted_fridge_items_total=16 | 6.2 |
| `van_capacity_1` | $2000 / upgrade; from_npcs=3; to_npcs=4 | 6.2 |
| `van_capacity_2` | $4000 / upgrade; from_npcs=4; to_npcs=5; requires=van_capacity_1 | 6.2 |
| `van_initial_purchase` | $400 / van_and_hamlet_base | 2 |
| `base_wagon` | $0 / premises; table_capacity=0; electricity_per_game_day=0 | 7.1, 7.2, 15.C5 |
| `base_hamlet` | $0 / premises; table_capacity=1; electricity_per_game_day=50 | 7.1, 7.2, 15.C5 |
| `base_rough` | $8100 / premises; table_capacity=2; electricity_per_game_day=100 | 7.1, 7.2, 15.C5 |
| `base_downtown` | $33750 / premises; table_capacity=3; electricity_per_game_day=200 | 7.1, 7.2, 15.C5 |
| `base_lab` | $135000 / premises; table_capacity=null (неприменимо/нет фиксированного лимита); electricity_per_game_day=500 | 7.1, 7.2, 15.C5 |
| `staff_assistant` | $60000 / initial_hire; profit_share=0.1; one_step_error_probability=null (неприменимо/нет фиксированного лимита) | 7.3 |
| `staff_specialist` | $120000 / initial_hire; profit_share=0.2; one_step_error_probability=0.05 | 7.3 |
| `staff_specialist_flawless` | $180000 / initial_hire; profit_share=0.2; one_step_error_probability=0 | 7.3 |
| `electricity_day_real_minutes` | value=45 | 7.2 |
| `electricity_prepay_1` | value=1 | 7.2 |
| `electricity_prepay_3` | value=3 | 7.2 |
| `electricity_prepay_7` | value=7 | 7.2 |
| `electricity_warning_6` | value=6 | 7.2 |
| `electricity_warning_1` | value=1 | 7.2 |
| `portable_fridge_capacity` | value=8 | 4, 6.2 |
| `portable_fridge_hands` | value=2 | 4 |
| `portable_fridge_spoil_minutes` | value=25 | 4 |
| `stationary_fridge_capacity` | value=24 | 4 |
| `trash_bag_capacity` | value=8 | 4 |
| `anaesthesia_basic_nominal_uses` | value=10 | 4 |
| `special_order_game_hours` | value=48 | 9.1 |
| `special_order_on_time_multiplier` | value=1.25 | 3.3, 9.1 |
| `uncooled_multiplier` | value=0.9 | 3.3 |
| `buyer_blood` | coefficient=null (неприменимо/нет фиксированного лимита); minimum_tier=null (неприменимо/нет фиксированного лимита); existing_core_id=C01 | 8.1, 15.B2 |
| `buyer_first` | coefficient=1; minimum_tier=1; existing_core_id=ORGANS_01 | 8.1, 15.B2 |
| `buyer_medic` | coefficient=1.5; minimum_tier=2 | 8.1, 15.B2 |
| `buyer_mafia` | coefficient=2.2; minimum_tier=3 | 8.1, 15.B2 |
| `kidney` | $250 / item | 3.2, 3.3, 5.3 |
| `liver` | $350 / item | 3.2, 3.3, 5.3 |
| `eyes` | $200 / paired_item | 3.2, 3.3, 5.3 |
| `brain` | $1200 / item | 3.2, 3.3, 5.3 |
| `heart` | $1000 / item | 3.2, 3.3, 5.3 |
| `lungs` | $450 / paired_item | 3.2, 3.3, 5.3 |
| `blood_bag_sealed` | $50 / item | 3.2, 3.3, 5.3 |
| `blood_syringe_first` | $10 / item | 3.2, 3.3, 5.3 |
| `blood_syringe_repeat` | $8 / item | 3.2, 3.3, 5.3 |
| `quality_damaged` | tier=1; percent_label=20; multiplier=0.5 | 3.2 |
| `quality_acceptable` | tier=2; percent_label=40; multiplier=1 | 3.2 |
| `quality_good` | tier=3; percent_label=60; multiplier=1.5 | 3.2 |
| `quality_perfect` | tier=4; percent_label=80; multiplier=2.6 | 3.2 |
| `quality_perfect_plus` | tier=5; percent_label=100; multiplier=6 | 3.2 |
| `mission_medic_case` | fixed_reward=1000; replacement_deduction=200; reward_kind=courier | 9.3, 15.B12, 15.B13 |
| `mission_kidney_order` | minimum_tier=3; on_time_fixed_bonus=0; reward_kind=organ; buyer=buyer_first; product=kidney; target_npc_type=HAMLET_BODYBUILDER | 9.1, 9.2 |
| `mission_streamer_order` | minimum_tier=4; on_time_fixed_bonus=0; reward_kind=organ; buyer=buyer_medic; product=brain; target_npc_type=OLD_STREAMER | 9.1, 9.2 |
| `mission_vip_beastman` | minimum_tier=4; on_time_fixed_bonus=15000; reward_kind=organ; buyer=buyer_mafia; product=heart; target_npc_type=VIP_BEASTMAN | 9.4, 15.D5, 15.D6 |
| `mission_vip_speedster` | minimum_tier=3; on_time_fixed_bonus=10000; reward_kind=organ; buyer=buyer_mafia; product=lungs; target_npc_type=VIP_SPEEDSTER | 9.4, 15.D5, 15.D6 |
| `mission_vip_blindfold` | minimum_tier=4; on_time_fixed_bonus=15000; reward_kind=organ; buyer=buyer_mafia; product=eyes; target_npc_type=VIP_BLINDFOLD | 9.4, 15.D5, 15.D6 |
| `mission_vip_altgirl` | minimum_tier=3; on_time_fixed_bonus=10000; reward_kind=organ; buyer=buyer_mafia; product=brain; target_npc_type=BAD_ALTGIRL | 9.4, 15.D5, 15.D6 |
| `van_glass_price` | open | 14.1 |
| `van_hidden_compartment_price` | open | 14.1 |
| `unpacked_blood_freshness_seconds` | open | 5.2 |
| `streamer_search_hours` | open | 9.2, 14.1 |

## Файлы и границы

Продуктовые файлы G48 (все абсолютные пути проверяются перед завершением):

- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerCatalog.cs` — только загрузчик/перегрузка формулы и общий helper; чужие ISyringePriceLookup/SyringePrices/SyringePrice сохранены.
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\EconomyCatalog.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\EconomyCatalog.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Economy_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Economy_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\EconomyDataTests.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\EconomyDataTests.cs.meta`
- `C:\Dev\Game\docs\reports\ECONOMY_DATA_G48_RU.md`

Подготовительные скрипты и автоматически изменённые .NET-артефакты находятся в `C:\Dev\Game\ArtSource\Dev\Buyers_staging\` и `C:\Dev\Game\Temp\`. Полный пофайловый список, включая каждый существующий созданный/изменённый файл сборки и проверки, — `C:\Dev\Game\ArtSource\Dev\Buyers_staging\G48-files.txt`. Там же G48-before.json содержит исходные SHA-256 standalone-каталога для сравнения. Подготовительные G48_build_*.py не являются runtime-источником цен; канонический редактируемый источник — JSON.

PASS — каждый путь полного инвентаря проверен: файл существует и находится внутри `C:\Dev\Game\`. Машиночитаемая проверка: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\G48-path-verification.json`; сводка с SHA-256 исходников: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\G48-verification.json`. Внешние каталоги не использовались для сохранения результатов; единственное внешнее служебное состояние — предписанный пользователем shared Unity lock.
