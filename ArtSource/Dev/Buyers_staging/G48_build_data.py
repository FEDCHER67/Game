"""Rebuild only G48's versioned catalog from the explicitly transcribed spec tables."""
import json
from pathlib import Path

ROOT = Path('C:/Dev/Game')
entries = []


def add(id, category, spec, price=None, unit='', quantity=1, note='', sold='', status='confirmed', numbers=None, refs=None):
    entries.append(dict(id=id, category=category, spec=spec, price=price, unit=unit,
                        quantity=quantity, effect_note=note, where_sold=sold, status=status,
                        numbers=numbers or {}, refs=refs or {}))


consumables = [
    ('syringe_blood', 2, 'syringe', 1, 'Reusable only on the same PersonId; blood only.', 'pharmacy; authored world finds'),
    ('syringe_anaesthesia', 2, 'empty_syringe', 1, 'Reusable only on the same PersonId; anaesthetic bought separately.', 'pharmacy; suitable authored world finds'),
    ('zip_tie', 5, 'tie', 1, 'Hands OR legs of one NPC.', 'pharmacy; underground_supplier'),
    ('zip_tie_pack_4', 20, 'pack', 4, 'Fully restrains two NPCs; no volume discount.', 'pharmacy; underground_supplier'),
    ('blood_bag_empty', 5, 'bag', 1, 'One blood portion.', 'pharmacy after introductory mission'),
    ('organ_bag', 10, 'bag', 1, 'Seals one organ item; does not cool or restore quality.', 'pharmacy'),
    ('body_bag', 5, 'bag', 1, 'Existing body rules apply.', 'pharmacy'),
    ('trash_bag', 5, 'bag', 1, 'Eight eligible trash items; not eight bodies.', 'pharmacy'),
    ('head_bag', 10, 'bag', 1, 'CAPTURE section 5; does not kill by itself.', 'underground_supplier'),
    ('anaesthesia_basic', 200, 'vial', 1, 'About ten nominal uses; no separately sold dose.', 'pharmacy'),
    ('anaesthesia_improved', 400, 'vial', 1, 'Requires the improved formula unlocked with XP; no separately sold dose.', 'pharmacy'),
    ('anaesthesia_late', 800, 'vial', 1, 'Requires the late formula unlocked with XP; no separately sold dose.', 'pharmacy'),
]
for id, price, unit, quantity, note, sold in consumables:
    add(id, 'consumable', '4;5' if id.startswith('syringe_') else '4', price, unit, quantity, note, sold)

equipment = [
    ('knife', 100, 'Reusable replacement basic knife.'),
    ('patient_restraints', 500, 'Set of five reusable table restraints; not capture zip ties.'),
    ('work_lamp', 250, 'Workplace lighting.'),
    ('saw', 1500, 'Procedure also requires story unlock; buying does not unlock brain extraction.'),
    ('hammer', 300, 'Chest procedure; G40 hammer/osteotome contract.'),
    ('osteotome', 100, 'Separate G40 item; not a replacement for the hammer. Initial author balance.'),
    ('tray', 100, 'Storage without cooling.'),
    ('tool_trolley', 500, 'Transports physically accessible tools.'),
    ('portable_fridge', 1000, '8 items; both hands; spoilage step every 25 active minutes.'),
    ('stationary_fridge', 5000, '24 items; spoilage stops while electricity is paid.'),
    ('mop_bucket', 100, 'G40; water is not consumed.'),
    ('operating_table', 1500, 'Physical placement within base capacity.'),
    ('rare_equipment', 90000, 'Appraisal/rare equipment; functions/resources belong to OPERATIONS; not an automatic VIP generator.'),
]
for id, price, note in equipment:
    add(id, 'equipment', '4;4.1', price, 'set' if id in ('patient_restraints', 'mop_bucket') else 'item',
        5 if id == 'patient_restraints' else 1, note,
        'underground_supplier (special tools); phone_delivery (large equipment); exact per-item storefront open')

add('direct_to_bag', 'reserve', '4.1', 1500, 'upgrade', note='Balance reserve only; functional contract not approved.', status='reserved')
add('quick_release', 'reserve', '4.1', 2000, 'upgrade', note='Balance reserve only; functional contract not approved.', status='reserved')
add('delivery_game_hours', 'parameter', '4.1;15.A19', unit='game_hour', numbers={'value': 1}, note='Large equipment; one physical crate on an owned base.')

profiles = {
    'engine': dict(price=[0, 1500, 2250, 3250], speed_kmh=[70, 85, 100, 115], torque_multiplier=[1, 1.12, 1.25, 1.40]),
    'handling': dict(price=[0, 1000, 1750, 2750], lateral_grip_multiplier=[1, 1.06, 1.12, 1.20], anti_roll_multiplier=[1, 1.12, 1.25, 1.40], steering_response_multiplier=[1, 1.10, 1.20, 1.30], high_speed_steering_add_degrees=[0, 1, 2, 3]),
    'brakes': dict(price=[0, 750, 1250, 2000], brake_torque_multiplier=[1, 1.15, 1.30, 1.45], handbrake_multiplier=[1, 1.08, 1.16, 1.24], longitudinal_grip_multiplier=[1, 1.05, 1.10, 1.15]),
}
for branch, values in profiles.items():
    for tier in range(4):
        add(f'van_{branch}_{tier}', 'van_tier', '6.1;15.A32', values['price'][tier], 'tier',
            note='Relative to new tier 0; independent branches; sequential purchases; first playtest preset.',
            sold='workshop', numbers={'tier': tier, **{k: v[tier] for k, v in values.items() if k != 'price'}}, refs={'branch': branch})
add('van_storage', 'cargo', '6.2', 1500, 'upgrade', note='No fridges included; does not add NPC capacity or cooling.', sold='workshop', numbers={'small_slots': 12, 'fridge_mounts': 2, 'mounted_fridge_items_total': 16})
add('van_capacity_1', 'cargo', '6.2', 2000, 'upgrade', note='3 to 4 lying NPCs.', sold='workshop', numbers={'from_npcs': 3, 'to_npcs': 4})
add('van_capacity_2', 'cargo', '6.2', 4000, 'upgrade', note='4 to 5 lying NPCs; requires capacity I.', sold='workshop', numbers={'from_npcs': 4, 'to_npcs': 5}, refs={'requires': 'van_capacity_1'})
add('van_initial_purchase', 'purchase', '2', 400, 'van_and_hamlet_base', note='Peaceful grandfather branch only; alternative branch remains. Intro battery/tyres already in yard.')

for id, price, cap, electric, note in [
    ('base_wagon', 0, 0, 0, 'Free blood prologue; not an organ laboratory.'),
    ('base_hamlet', 0, 1, 50, 'Included with van in either branch; old table and rusty knife; no lamp/restraints.'),
    ('base_rough', 8100, 2, 100, 'Empty room; equipment separate.'),
    ('base_downtown', 33750, 3, 200, 'Empty room; equipment separate.'),
    ('base_lab', 135000, None, 500, 'Quiet Valley; no fixed design table limit; actual space/performance still apply.'),
]:
    add(id, 'base', '7.1;7.2;15.C5', price, 'premises', note=note, sold='phone_property_catalog' if price else 'story', numbers={'table_capacity': cap, 'electricity_per_game_day': electric})
for id, price, share, error, note in [
    ('staff_assistant', 60000, 0.10, None, 'Moves/prepares/removes patients; no surgery/cleaning/outdoor disposal.'),
    ('staff_specialist', 120000, 0.20, 0.05, 'One-step error probability per extraction.'),
    ('staff_specialist_flawless', 180000, 0.20, 0, 'No execution errors; does not improve innate quality.'),
]:
    add(id, 'staff', '7.3', price, 'initial_hire', note=note, sold='phone_staff_catalog; equipped owned base', numbers={'profit_share': share, 'one_step_error_probability': error})
for id, value, unit, spec, note in [
    ('electricity_day_real_minutes', 45, 'active_real_minute', '7.2', 'One game day of active world time; no offline billing.'),
    ('electricity_prepay_1', 1, 'game_day', '7.2', 'Prepay separately per base.'),
    ('electricity_prepay_3', 3, 'game_day', '7.2', 'Prepay separately per base.'),
    ('electricity_prepay_7', 7, 'game_day', '7.2', 'Prepay separately per base.'),
    ('electricity_warning_6', 6, 'game_hour_before_cutoff', '7.2', 'Phone warning.'),
    ('electricity_warning_1', 1, 'game_hour_before_cutoff', '7.2', 'Phone warning.'),
    ('portable_fridge_capacity', 8, 'item', '4;6.2', 'Physical capacity; blood occupies slots too.'),
    ('portable_fridge_hands', 2, 'hand', '4', 'Both hands occupied.'),
    ('portable_fridge_spoil_minutes', 25, 'active_real_minute', '4', 'One spoilage step.'),
    ('stationary_fridge_capacity', 24, 'item', '4', 'Cooling requires paid electricity.'),
    ('trash_bag_capacity', 8, 'eligible_trash_item', '4', 'Not body capacity.'),
    ('anaesthesia_basic_nominal_uses', 10, 'approximate_use', '4', 'Approximate; not a separately sold dose.'),
    ('special_order_game_hours', 48, 'game_hour', '9.1', 'Deadline begins on explicit acceptance after negotiation.'),
    ('special_order_on_time_multiplier', 1.25, 'multiplier', '3.3;9.1', 'No saturation; late loses only on-time uplift.'),
    ('uncooled_multiplier', 0.9, 'multiplier', '3.3', 'Cooled delivery uses 1.'),
]:
    add(id, 'parameter', spec, unit=unit, note=note, numbers={'value': value})

for id, core_id, coefficient, floor in [('buyer_blood', 'C01', None, None), ('buyer_first', 'ORGANS_01', 1, 1), ('buyer_medic', '', 1.5, 2), ('buyer_mafia', '', 2.2, 3)]:
    add(id, 'buyer', '8.1;15.B2', note='Organ coefficient and quality floor are inapplicable to blood. Existing core ID, when assigned, is metadata only.', numbers={'coefficient': coefficient, 'minimum_tier': floor}, refs={'existing_core_id': core_id})
for kind, price in [('kidney', 250), ('liver', 350), ('eyes', 200), ('brain', 1200), ('heart', 1000), ('lungs', 450), ('blood_bag_sealed', 50), ('blood_syringe_first', 10), ('blood_syringe_repeat', 8)]:
    add(kind, 'sale_product', '3.2;3.3;5.3', price, 'paired_item' if kind in ('eyes', 'lungs') else 'item', note='Sale base value, not a shop purchase. Eyes/lungs are indivisible pairs.')
for tier, name, mult in [(1, 'damaged', .5), (2, 'acceptable', 1), (3, 'good', 1.5), (4, 'perfect', 2.6), (5, 'perfect_plus', 6)]:
    add('quality_' + name, 'quality', '3.2', unit='discrete_tier', numbers={'tier': tier, 'percent_label': tier * 20, 'multiplier': mult})

add('mission_medic_case', 'mission', '9.3;15.B12;15.B13', note='Fixed reward, no deadline, no organ formula/commission; replacements never debit money.', numbers={'fixed_reward': 1000, 'replacement_deduction': 200}, refs={'reward_kind': 'courier'})
for id, buyer, organ, floor, bonus, target, spec in [
    ('mission_kidney_order', 'buyer_first', 'kidney', 3, 0, 'HAMLET_BODYBUILDER', '9.1;9.2'),
    ('mission_streamer_order', 'buyer_medic', 'brain', 4, 0, 'OLD_STREAMER', '9.1;9.2'),
    ('mission_vip_beastman', 'buyer_mafia', 'heart', 4, 15000, 'VIP_BEASTMAN', '9.4;15.D5;15.D6'),
    ('mission_vip_speedster', 'buyer_mafia', 'lungs', 3, 10000, 'VIP_SPEEDSTER', '9.4;15.D5;15.D6'),
    ('mission_vip_blindfold', 'buyer_mafia', 'eyes', 4, 15000, 'VIP_BLINDFOLD', '9.4;15.D5;15.D6'),
    ('mission_vip_altgirl', 'buyer_mafia', 'brain', 3, 10000, 'BAD_ALTGIRL', '9.4;15.D5;15.D6'),
]:
    add(id, 'mission', spec, note='One individually sealed organ from the required PersonId; base organ formula plus on-time-only fixed bonus; no saturation.', numbers={'minimum_tier': floor, 'on_time_fixed_bonus': bonus}, refs={'reward_kind': 'organ', 'buyer': buyer, 'product': organ, 'target_npc_type': target})

for id, spec, note in [
    ('van_glass_price', '14.1', 'Protection, durability and price require a transport/police contract.'),
    ('van_hidden_compartment_price', '14.1', 'Effect and price not assigned; not an active shop upgrade.'),
    ('unpacked_blood_freshness_seconds', '5.2', 'Proposed 120 seconds in source is explicitly not confirmed here.'),
    ('streamer_search_hours', '9.2;14.1', 'NPC content dependency; do not reuse bodybuilder hours.'),
]:
    add(id, 'open', spec, note=note, status='open')

catalog = dict(schemaVersion=1, id='economy_v01', spec='ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01;15 overrides earlier sections', entries=entries)
destination = ROOT / 'Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json'
destination.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{destination}: {len(entries)} stable ids')
