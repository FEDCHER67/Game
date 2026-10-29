from pathlib import Path
import hashlib
import json

root = Path('C:/Dev/Game').resolve()
sources = {
 'Assets/OnlyVolunteers/Buyers/Core/BuyerCatalog.cs': 'G49: один интерфейс/lookup цен с разрешённым fallback; изменения G48 сохранены.',
 'Assets/OnlyVolunteers/Buyers/Core/BuyerRules.cs': 'Снят запрет второй продажи порции в шприце.',
 'Assets/OnlyVolunteers/Buyers/Core/BuyerState.cs': 'Добавлены идентификаторы порции и физического шприца в проекцию товара.',
 'Assets/OnlyVolunteers/Buyers/Core/BuyerTransactions.cs': 'Повторная цена C01 и запрет повторной продажи PortionId, без изменений проводки денег.',
 'Assets/OnlyVolunteers/Buyers/Tests/BuyerPriceAndProgressionTests.cs': 'Прежнее одноразовое ожидание обновлено по прямому разрешению под $10→$8.',
 'Assets/OnlyVolunteers/Buyers/Tests/BuyerSyringeTests.cs': 'Новые регрессии повторной продажи и общего PortionId.',
 'Assets/OnlyVolunteers/Capture/Scripts/CaptureFieldKit.cs': 'Проверка экземпляра до действий, прогресс/отмена/упаковка, убраны бесплатные запасы.',
 'Assets/OnlyVolunteers/Capture/Scripts/CaptureNpc.cs': 'Адаптер существующего забора к проверяемому экземпляру, сохранён timestamp анимации.',
 'Assets/OnlyVolunteers/Capture/Scripts/CaptureSyringeBindings.cs': 'Новая часть FieldKit: серверная проверка выбранного экземпляра и восстановление привязки.',
 'Assets/OnlyVolunteers/Inventory/Core/InventoryModel.cs': 'Перенос того же экземпляра, запрет merge/повторного добавления ItemId.',
 'Assets/OnlyVolunteers/Inventory/Core/ItemStack.cs': 'Метаданные экземпляра и тип шприца в per-type информации.',
 'Assets/OnlyVolunteers/Inventory/Core/OnlyVolunteers.Inventory.Core.asmdef': 'Ссылка на существующий Buyers Core для единственного API цен; engine-free сохранён.',
 'Assets/OnlyVolunteers/Inventory/Core/SyringeInstance.cs': 'Новые данные экземпляра/порции и чистые правила привязки/отмены/упаковки.',
 'Assets/OnlyVolunteers/Inventory/Core/SyringeSaveBlock.cs': 'Новый блок существующего сейва, включая данные мировых drops; без денег.',
 'Assets/OnlyVolunteers/Inventory/Core/SyringeSaleRules.cs': 'Новый pure C01 confirm/receipt, возврат/списание, один вызов payout.',
 'Assets/OnlyVolunteers/Inventory/Core/DailySyringeFindRules.cs': 'Новая ежедневная выдача 06:00 и данные авторских дополнительных точек.',
 'Assets/OnlyVolunteers/Inventory/Core/G48SyringePriceLookup.cs': 'Новый адаптер одного lookup G48 с aliases C01.',
 'Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset': 'Добавлены ссылки на два новых определения шприцев.',
 'Assets/OnlyVolunteers/Inventory/Items/Item_SyringeBlood_G49.asset': 'Новое определение 303, blood, размер 1, stack 1, цена из API.',
 'Assets/OnlyVolunteers/Inventory/Items/Item_SyringeAnaesthesia_G49.asset': 'Новое определение 304, anaesthesia, размер 1, stack 1, цена из API.',
 'Assets/OnlyVolunteers/Inventory/Runtime/ItemDefinition.cs': 'Тип шприца, ограничение stack и чтение цены по ID.',
 'Assets/OnlyVolunteers/Inventory/Runtime/ItemStackSerializers.cs': 'FishNet round-trip экземпляра, PersonId, PortionId и состояния содержимого.',
 'Assets/OnlyVolunteers/Inventory/Runtime/LocalInventory.cs': 'Pickup/drop переносит метаданные вместо создания нового экземпляра.',
 'Assets/OnlyVolunteers/Inventory/Runtime/OfflineWorldItem.cs': 'Хранение и выдача того же экземпляра локального drop.',
 'Assets/OnlyVolunteers/Inventory/Runtime/WorldItem.cs': 'Серверные метаданные экземпляра для защищённого NetworkInventory hook.',
 'Assets/OnlyVolunteers/Inventory/Tests/EditMode/OnlyVolunteers.Inventory.Tests.asmdef': 'Ссылка для тестирования реального API цен Buyers.',
 'Assets/OnlyVolunteers/Inventory/Tests/EditMode/SyringeRulesTests.cs': '25 новых EditMode случаев правил, payout, save/load, находок и G48.',
 'Assets/OnlyVolunteers/Operation/Stage1/Core/OnlyVolunteers.Operation.Core.asmdef': 'Ссылка на engine-free данные предметных экземпляров.',
 'Assets/OnlyVolunteers/Operation/Stage1/Core/OperationState.cs': 'Состояние экземпляров/порций в существующем сейве; запрещён забор из трупа.',
 'Assets/OnlyVolunteers/Operation/Stage1/Core/OperationTargets.cs': 'Добавлены причины отказа без перенумерации старых enum.',
 'Assets/OnlyVolunteers/Operation/Stage1/Core/OperationSyringeRules.cs': 'Новые проверяемые входы перед FillBlood и инъекцией, без сброса счётчика.',
 'Assets/OnlyVolunteers/Operation/Stage1/Scripts/NetworkOperationTable.cs': 'Минимальные серверные проверки, перенос PortionId в пакет и сохранение экземпляра при смене NPC.',
 'Assets/OnlyVolunteers/Operation/Stage1/Scripts/OperationHud.cs': 'Текст двух отказов, без изменения UI layout.',
 'Assets/OnlyVolunteers/Operation/Stage1/Scripts/OperationPhysicalItem.cs': 'Метаданные физического экземпляра в snapshot и подпись пустого шприца.',
 'Assets/OnlyVolunteers/Operation/Stage1/Tests/OnlyVolunteers.Operation.Tests.asmdef': 'Ссылка на экземпляры для реальных operation-тестов.',
 'Assets/OnlyVolunteers/Operation/Stage1/Tests/OperationRulesTests.cs': 'Прежнее ожидание забора из трупа исправлено по прямому разрешению.',
 'Assets/OnlyVolunteers/Operation/Stage1/Tests/OperationSyringeTests.cs': '6 новых тестов применения/лимитов/отмены/операционного сейва.',
 'Working/Tests/G49/G49.Tests.csproj': 'Связанные оригинальные исходники Buyers/Inventory для чистых .NET проверок.',
 'Working/Tests/G49/Compile-G49.py': 'Roslyn-проверка реальных исходников с текущими asmdef в памяти, без второго Unity.',
 'Working/Tests/G49/Verify-G49Files.py': 'Этот проверяющий скрипт; абсолютные пути и sha256 исходников.',
 'docs/reports/SYRINGE_RULE_G49_RU.md': 'Основной отчёт для Феди, правила → тесты, ограничения и плейтест.',
 'docs/reports/SYRINGE_RULE_G49_HOOKS_RU.md': 'Часть отчёта: точные НЕ применённые вставки для Claude.',
}
entries = {}
for relative, reason in sources.items():
    path = root / relative
    entries[str(path)] = reason
    if relative.startswith('Assets/') and path.with_name(path.name + '.meta').exists() and relative in {
        'Assets/OnlyVolunteers/Buyers/Tests/BuyerSyringeTests.cs',
        'Assets/OnlyVolunteers/Capture/Scripts/CaptureSyringeBindings.cs',
        'Assets/OnlyVolunteers/Inventory/Tests/EditMode/SyringeRulesTests.cs',
        'Assets/OnlyVolunteers/Operation/Stage1/Core/OperationSyringeRules.cs',
        'Assets/OnlyVolunteers/Operation/Stage1/Tests/OperationSyringeTests.cs',
    } | {p for p in sources if '/Inventory/Core/' in p and p.endswith('Rules.cs')} | {
        'Assets/OnlyVolunteers/Inventory/Core/SyringeInstance.cs',
        'Assets/OnlyVolunteers/Inventory/Core/SyringeSaveBlock.cs',
        'Assets/OnlyVolunteers/Inventory/Core/G48SyringePriceLookup.cs',
    } | {p for p in sources if p.endswith('_G49.asset')}:
        entries[str(path) + '.meta'] = 'Новая Unity identity соответствующего файла; старые GUID не менялись.'

generated = set()
for directory in [root/'Working/Tests/G49', root/'Temp/G49']:
    generated.update(p for p in directory.rglob('*') if p.is_file() and str(p) not in entries)
assemblies = ['OnlyVolunteers.Buyers.Core','OnlyVolunteers.Inventory.Core','OnlyVolunteers.Inventory',
              'OnlyVolunteers.Operation.Core','OnlyVolunteers.Capture.Core','OnlyVolunteers.Economy.Core',
              'Assembly-CSharp','OnlyVolunteers.Buyers.Tests','OnlyVolunteers.Inventory.Tests','OnlyVolunteers.Operation.Tests']
for assembly in assemblies:
    for ext in ['.dll','.pdb']:
        p = root/'Temp/bin/Debug'/(assembly+ext)
        if p.exists(): generated.add(p)
    directory = root/'Temp/obj'/assembly
    if directory.exists(): generated.update(p for p in directory.rglob('*') if p.is_file())

inventory = root/'docs/reports/SYRINGE_RULE_G49_FILES.md'
audit = root/'Working/Tests/G49/path-verification.json'
entries[str(inventory)] = 'Этот перечень всех файлов и причин изменений.'
entries[str(audit)] = 'Машиночитаемая проверка существования и границы C:/Dev/Game.'
for p in generated:
    entries.setdefault(str(p), 'Локальный результат/служебный файл проверок; не игровой исходник.')

lines = ['# G49 — файлы и проверка путей', '',
         'Все перечисленные пути абсолютные, проверяются внутри C:\\Dev\\Game. Исходники чужой параллельной работы не включены как изменения G49. BuyerCatalog содержит также сохранённую добавку G48.', '',
         'Unity автоматически обновляет совместные Library/кеши импорта; это не ручные изменения ассетов/сцен. Ни один защищённый файл Claude скрипт не изменяет.', '',
         '## Исходники, данные, отчёты', '', '| Абсолютный путь | Причина |', '|---|---|']
for path, reason in entries.items():
    if Path(path) not in generated:
        lines.append(f'| {path} | {reason} |')
lines += ['', '## Локальные результаты и генерируемые файлы проверки', '']
for path in sorted(generated): lines.append(str(path))
inventory.write_text('\n'.join(lines)+'\n',encoding='utf-8')
audit.write_text('{}\n',encoding='utf-8')
records = []
for name, reason in entries.items():
    p = Path(name).resolve()
    inside = root in p.parents
    exists = p.is_file()
    records.append({'path':str(p),'exists':exists,'insideGame':inside,
                    'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if exists and p != audit else None,
                    'reason':reason})
    if not inside or not exists: raise RuntimeError(f'Invalid output path: {p}')
audit.write_text(json.dumps({'allExistUnderGame':True,'count':len(records),'files':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'allExistUnderGame':True,'count':len(records),'inventory':str(inventory),'audit':str(audit)},ensure_ascii=False))
