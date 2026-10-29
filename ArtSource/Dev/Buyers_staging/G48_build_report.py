from pathlib import Path
import json

root=Path('C:/Dev/Game')
data=json.loads((root/'Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json').read_text(encoding='utf-8'))
report=root/'docs/reports/ECONOMY_DATA_G48_RU.md'
text='''# G48 — единые данные экономики v01

28.10.2026, Феде. Расширен существующий `OnlyVolunteers.Buyers.Core`: 96 стабильных ID в `Economy_v01.json`, загрузчик и неизменяемый API чтения. Источник — ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01 целиком, финальные замены §15 имеют приоритет. `noEngineReferences=true`, зависимости/пакеты/asmdef не менялись.

Покрыты расходники, постоянное оборудование, единицы/упаковки, эффект и место продажи, шприцы, 0–III всех трёх веток машины и их профили, грузовые улучшения, базы/вместимость/электричество, персонал, коэффициенты/минимумы покупателей, доставка за игровой час, кейс, почка, поздний стример и четыре VIP. Дополнительно включены базовые цены органов/крови и актуальные множители качества для расчёта наград.

Денежного состояния, записи денег, покупок или адаптеров фонда API не содержит. `BuyerRules`, `BuyerState`, `BuyerOrders`, `BuyerTransactions`, runtime машины/телефона/захвата/операций и сцены G48 не редактировал. Чужие изменения в этих файлах сохранены. Спецификация остаётся untracked; staging/commit/push не выполнялись.

## Проверка

- PASS — Roslyn `unity_compile_check.py --project C:\\Dev\\Game --files <BuyerCatalog.cs, EconomyCatalog.cs, EconomyDataTests.cs> --dependents`: Core, Buyers.Tests, Assembly-CSharp, Assembly-CSharp-Editor; `COMPILE_OK`. Использованы абсолютные пути, TEMP/TMP и .NET-каталоги внутри репозитория.
- PASS — `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\Run-Tests.ps1`: **161 всего, 161 PASS, 0 FAIL, 0 пропусков**. **31 новая** проверка G48 и все **130 существующих** проверок текущей рабочей копии прошли. Параллельный владелец повторной продажи обновил свой прежний тест под $10→$8; этот файл G48 не редактировал.
- Unity EditMode: ОЖИДАНИЕ LOCK. Итог будет внесён после запуска.
- TRX и полный stdout: `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\TestResults\\buyers-results.trx`, `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\test-output.txt`.

Unity preflight: существующий Editor PID 11892, `Game@b321844a`, session `70328105-4aec-4959-bed4-662c662886a7`, путь `C:/Dev/Game`, версия `6000.5.11f1`, Play=false. Lock G48 получен и отпущен после проверки/установки. Unity CLI 1.0.0-beta.14 проверен; Pipeline отсутствует. Использован существующий CoplayDev MCP согласно docs/AgentRules.md и переданному HANDOFF; второй мост не устанавливался. Editor/сцена не переключались; новый процесс Unity не запускался.

## Спецификация → данные → тест

Все новые тесты: `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Tests\\EconomyDataTests.cs`. Одни и те же исходники связаны существующим standalone runner и Editor-only NUnit asmdef.

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
'''
for e in data['entries']:
    values=[]
    if e['price'] is not None: values.append('$'+str(e['price'])+' / '+e['unit']+(' (units='+str(e['quantity'])+')' if e['quantity']!=1 else ''))
    for k,v in e['numbers'].items(): values.append(k+'='+('null (неприменимо/нет фиксированного лимита)' if v is None else str(v)))
    for k,v in e['refs'].items():
        if v: values.append(k+'='+v)
    if e['status']!='confirmed': values.append(e['status'])
    text+='| `'+e['id']+'` | '+'; '.join(values)+' | '+e['spec'].replace(';',', ')+' |\n'
text+='''
## Файлы и границы

Продуктовые файлы G48 (все абсолютные пути проверяются перед завершением):

- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Core\\BuyerCatalog.cs` — только загрузчик/перегрузка формулы и общий helper; чужие ISyringePriceLookup/SyringePrices/SyringePrice сохранены.
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Core\\EconomyCatalog.cs`
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Core\\EconomyCatalog.cs.meta`
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Data\\Economy_v01.json`
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Data\\Economy_v01.json.meta`
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Tests\\EconomyDataTests.cs`
- `C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Tests\\EconomyDataTests.cs.meta`
- `C:\\Dev\\Game\\docs\\reports\\ECONOMY_DATA_G48_RU.md`

Подготовительные скрипты и автоматически изменённые .NET-артефакты находятся в `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\` и `C:\\Dev\\Game\\Temp\\`. Полный пофайловый список, включая каждый существующий созданный/изменённый файл сборки и проверки, — `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\G48-files.txt`. Там же G48-before.json содержит исходные SHA-256 standalone-каталога для сравнения. Подготовительные G48_build_*.py не являются runtime-источником цен; канонический редактируемый источник — JSON.

Проверка существования и границы `C:\\Dev\\Game\\`: ожидает итогового инвентаря. Внешние каталоги не использовались для сохранения результатов; единственное внешнее служебное состояние — предписанный пользователем shared Unity lock.
'''
text=text.replace('**161 всего, 161 PASS, 0 FAIL, 0 пропусков**', '**163 всего, 163 PASS, 0 FAIL, 0 пропусков**')
text=text.replace('и все **130 существующих** проверок текущей рабочей копии прошли.', 'и все **132 остальные** проверки текущей рабочей копии прошли (130 прежних плюс 2 добавленные параллельно).')
text=text.replace('- Unity EditMode: ОЖИДАНИЕ LOCK. Итог будет внесён после запуска.', '- PASS — Unity 6000.5.11f1, EditMode, assembly_names=[OnlyVolunteers.Buyers.Tests]: **163/163 PASS**, 0 FAIL/skip; 31 G48 + 132 остальные. Job `b096fd290bd44395ac4e8c88f99273be`, 17:07 МСК. Полные результаты: `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\G48-unity-editmode.json`. После refresh/compile домен готов; Console errors=0. Play=false, исходная Map_W85_Play_v02 сохранена без переключения/сохранения сцены. Lock отпущен с `-Done` сразу после проверки.')
text=text.replace('Проверка существования и границы `C:\\Dev\\Game\\`: ожидает итогового инвентаря.', 'PASS — каждый путь полного инвентаря проверен: файл существует и находится внутри `C:\\Dev\\Game\\`. Машиночитаемая проверка: `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\G48-path-verification.json`; сводка с SHA-256 исходников: `C:\\Dev\\Game\\ArtSource\\Dev\\Buyers_staging\\G48-verification.json`.')
report.write_text(text,encoding='utf-8')
print(report)
