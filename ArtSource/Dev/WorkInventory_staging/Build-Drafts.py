"""G39 authoring drafts only; no Unity assets. Run from anywhere inside C:/Dev/Game."""
import csv
import json
from pathlib import Path

root = Path('C:/Dev/Game/docs/drafts/work_inventory')
root.mkdir(parents=True, exist_ok=True)
rows = [
    (101, 'organ.heart', 'Organ', 1, False, 0, 'Heart', 'Сердце', 'Heart'),
    (102, 'organ.kidney', 'Organ', 1, False, 0, 'Kidney', 'Почка', 'Kidney'),
    (103, 'organ.liver', 'Organ', 1, False, 0, 'Liver', 'Печень', 'Liver'),
    (104, 'organ.lungs', 'Organ', 1, False, 0, 'Lungs', 'Парные лёгкие', 'Paired lungs'),
    (105, 'organ.brain', 'Organ', 1, False, 0, 'Brain', 'Мозг', 'Brain'),
    (106, 'organ.eye', 'Organ', 1, False, 0, 'Eye', 'Глаз', 'Eye'),
    (109, 'blood.intro_syringe', 'BloodSyringe', 1, False, 0, None, 'Учебный шприц крови', 'Intro blood syringe'),
    (110, 'blood.bag', 'BloodBag', 1, False, 0, None, 'Пакет крови', 'Sealed blood bag'),
    (111, 'tool.blood_syringe', 'BloodSyringe', 1, False, 0, None, 'Шприц для крови', 'Blood syringe'),
    (112, 'tool.anesthesia_syringe', 'AnesthesiaSyringe', 1, False, 0, None, 'Шприц наркоза', 'Anesthesia syringe'),
    (113, 'supply.anesthetic_vial', 'AnestheticVial', 1, False, 0, None, 'Флакон наркоза', 'Anesthetic vial'),
    (114, 'supply.zip_ties', 'ZipTies', 20, False, 0, None, 'Стяжки', 'Zip ties'),
    (115, 'supply.organ_pouch', 'OrganPouch', 10, False, 0, None, 'Пакеты для органов', 'Organ pouches'),
    (116, 'supply.empty_blood_bag', 'EmptyBloodBag', 10, False, 0, None, 'Пустые пакеты крови', 'Empty blood bags'),
    (117, 'supply.head_bag', 'HeadBag', 5, False, 0, None, 'Мешки на голову', 'Head bags'),
    (201, 'tool.scalpel', 'Tool', 1, False, 0, None, 'Скальпель', 'Scalpel'),
    (202, 'supply.body_bag', 'BodyBag', 5, False, 0, None, 'Мешки для тел', 'Body bags'),
    (301, 'container.cooler', 'Cooler', 1, True, 8, None, 'Переносной холодильник', 'Portable cooler'),
]
fields = ['id', 'key', 'class', 'maxStack', 'twoHanded', 'containerSlots', 'organKind', 'nameRu', 'nameEn']
items = [dict(zip(fields, r)) for r in rows]
for i in items:
    i['stage'] = 'B' if i['id'] == 117 else 'A'
    i['iconKey'] = i['key']

def write(name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

write('item_definitions_G39.json', {'schemaVersion': 1, 'qualityScale': 'tiers 1-5; capture grade + 1', 'items': items})
with (root / 'item_definitions_G39.csv').open('w', encoding='utf-8-sig', newline='') as f:
    out = csv.DictWriter(f, fieldnames=list(items[0])); out.writeheader(); out.writerows(items)

hints = {
    'Organ': ('ЛКМ — положить · ПКМ (держать) — упаковать · G — положить под ноги', 'LMB — place · Hold RMB — package · G — set down'),
    'BloodBag': ('Кровь запечатана · ЛКМ — положить или предложить C01', 'Sealed blood · LMB — place or offer to C01'),
    'BloodSyringe': ('ЛКМ (держать) — набрать кровь · ПКМ (держать) — перелить в пакет; испорченную кровь — вылить', 'Hold LMB — draw blood · Hold RMB — fill a bag; discard expired blood'),
    'AnesthesiaSyringe': ('ЛКМ (держать) — применить · ПКМ (держать) — наполнить из флакона', 'Hold LMB — use · Hold RMB — refill from a vial'),
    'AnestheticVial': ('Запас наркоза · Возьми шприц и держи ПКМ для наполнения', 'Anesthetic stock · Hold the syringe and hold RMB to refill'),
    'ZipTies': ('ЛКМ (держать) — связать руки или ноги · G — положить', 'Hold LMB — tie hands or feet · G — set down'),
    'OrganPouch': ('Возьми орган и держи ПКМ, чтобы упаковать', 'Hold an organ and hold RMB to package it'),
    'EmptyBloodBag': ('Возьми полный шприц крови и держи ПКМ', 'Hold a full blood syringe and hold RMB'),
    'BodyBag': ('ЛКМ (держать) — упаковать тело с открытыми ремнями', 'Hold LMB — bag a body with its straps open'),
    'HeadBag': ('Предмет следующего этапа · G — положить', 'For a later stage · G — set down'),
    'Tool': ('ЛКМ (держать) — разрезать стяжку', 'Hold LMB — cut a zip tie'),
    'Cooler': ('E — поставить · ЛКМ — бросить · Для инструмента освободи обе руки', 'E — set down · LMB — throw · Set it down before using tools'),
}
errors = {
    'None': ('', ''),
    'NoSuchItem': ('Уже забрали', 'Already taken'),
    'NoSuchContainer': ('Контейнер недоступен', 'Container unavailable'),
    'ContainerClosed': ('Сначала открой', 'Open it first'),
    'ContainerFull': ('Нет места', 'No room'),
    'SlotOccupied': ('Место занято', 'Slot occupied'),
    'NotAccepted': ('Сюда не подходит', 'This does not belong here'),
    'TwoHandedOnly': ('Сначала поставь груз', 'Set the load down first'),
    'NotTwoHanded': ('Возьми этот предмет в карман', 'Put this item in a pocket'),
    'NotEnough': ('Недостаточно', 'Not enough'),
    'AlreadyExists': ('Этот предмет уже получен', 'This item was already obtained'),
    'NotOwner': ('Это не твой предмет', 'This is not your item'),
    'Duplicate': ('Действие уже выполнено', 'Already done'),
    'BadRequest': ('Не удалось выполнить действие', 'Cannot perform that action'),
    'StaleRequest': ('Повтори действие', 'Try the action again'),
    'PlayerAbsent': ('Вещи игрока недоступны до его возвращения', 'These belongings return with their player'),
    'UpgradeRequired': ('Сначала купи полку для бусика', 'Buy the van shelf upgrade first'),
    'Busy': ('Сначала закончи текущее действие', 'Finish the current action first'),
    'OutOfReach': ('Подойди ближе', 'Move closer'),
    'NoLineOfSight': ('Что-то мешает', 'Something is in the way'),
    'InvalidTarget': ('Сейчас здесь не применить', 'Cannot use it here right now'),
    'EmptyHandsRequired': ('Сначала отпусти тело', 'Release the body first'),
    'NoActiveItem': ('Возьми предмет в руки', 'Hold an item first'),
    'MissingSupply': ('Нет нужного расходника', 'Required supply missing'),
    'FormulaMismatch': ('В шприце другой состав', 'The syringe contains another formula'),
    'BloodExpired': ('Кровь свернулась — её можно только вылить', 'Blood expired — discard it'),
    'HoldExpired': ('Действие прервано — начни снова', 'Action interrupted — start again'),
    'WrongPhase': ('Начни действие заново', 'Start the action again'),
    'StockEmpty': ('Запас кончился', 'Empty'),
    'NoSurface': ('Нужна поверхность', 'Aim at a surface'),
    'BuyerRefused': ('Товар уже недоступен для передачи', 'These goods can no longer be transferred'),
}
write('localization_G39.json', {
    'schemaVersion': 1,
    'items': {i['key']: {'ru': i['nameRu'], 'en': i['nameEn'], 'hintRu': hints[i['class']][0], 'hintEn': hints[i['class']][1]} for i in items},
    'refusals': {k: {'ru': v[0], 'en': v[1]} for k, v in errors.items()},
    'hints': {
        'pockets.full': {'ru': 'Карманы полны', 'en': 'Pockets full'},
        'kit.cycle': {'ru': 'Нажимай номер слота: стяжки → наркоз → кровь → пакеты → мешки → прочие расходники → пустые руки', 'en': 'Press the slot key: ties → anesthesia → blood → bags → body bags → other supplies → empty hands'},
        'organ.cold': {'ru': 'В холоде', 'en': 'Chilled'},
        'organ.warm': {'ru': 'Тает', 'en': 'Warming'},
        'organ.orderMatch': {'ru': 'Подходит к заказу ✓', 'en': 'Matches the order ✓'},
        'container.open': {'ru': 'E — открыть ({used}/{capacity})', 'en': 'E — open ({used}/{capacity})'},
        'container.close': {'ru': 'E — закрыть ({used}/{capacity})', 'en': 'E — close ({used}/{capacity})'},
        'cooler.lift': {'ru': 'Держать E — поднять двумя руками', 'en': 'Hold E — lift with both hands'},
        'throw.charge': {'ru': 'Держать G — бросить', 'en': 'Hold G — throw'},
    },
})

containers = [
    ('Pockets', 'pockets:{playerId}', 6, False), ('Kit', 'kit:{playerId}', 12, False),
    ('VanShelf', 'vanshelf:{vanId}', 12, True), ('VanCoolerMount', 'vanmount:{vanId}:{0|1}', 1, True),
    ('Cooler', '{coolerItemId}', 8, False), ('Fridge', 'fridge:{baseId}:{n}', 24, False),
    ('Tray', 'tray:{tableId}', 6, False), ('BuyerCase', 'case:{meetingId}', 8, False),
    ('Stash', 'stash:{stashId}', 4, False), ('ReturnTray', 'return:{pointId}:{n}', 8, False),
]
write('containers_G39.json', {
    'schemaVersion': 1,
    'notes': ['Kit occupies one of six numbered slots, default index 5. Twelve internal entries are a G39 provisional bound.',
              'Shelf and both cooler mounts use one purchased upgrade. Without it, cargo remains in World.',
              'Return overflow uses additional 8-slot trays. No item is silently destroyed.'],
    'containers': [dict(zip(['kind', 'idPattern', 'capacity', 'requiresVanStorageUpgrade'], c)) for c in containers],
})
write('quality_and_tuning_G39.json', {
    'schemaVersion': 1,
    'tiers': [dict(captureGrade=g, tier=g+1, percent=p, nameRu=ru, nameEn=en, multiplier=m) for g,p,ru,en,m in [
        (0,20,'Убитое','Damaged',.3), (1,40,'Сойдёт','Acceptable',1), (2,60,'Хорошее','Good',1.6), (3,80,'Отличное','Perfect',2.6), (4,100,'Идеальное','Perfect+',4.2)]],
    'provisionalSpec7': dict(roomSecondsPerGrade=300, coolerSecondsPerGrade=1500, poweredFridgePauses=True, minColdStintSeconds=60, maxWarmGapSeconds=60,
        organImpactSpeed=2.4, coolerImpactSpeed=4, impactCooldownSeconds=.6, bloodExpirySeconds=120, kitEntries=12),
    'toolTiming': dict(holdTimeoutSeconds=.5, tieHoldSeconds=1, bloodHoldSeconds=4.5, packHoldSeconds=1, refillHoldSeconds=1, transferHoldSeconds=1.2,
        syringeCapacity=3, injectionUnitsPerSecond=.5),
    'notes': ['Active-world seconds only; disconnected personal inventory is suspended. No offline decay.', 'Percent is a tier label, not a continuous quality value.', 'Packaging does not change spoilage.']
})
print(f'Wrote {len(items)} items, {len(containers)} container kinds and {len(errors)} refusal entries to {root}')
