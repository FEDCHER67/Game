#!/usr/bin/env python3
r"""G33: copy of the G30 numerical core, extended for capture data/economy.
Python 3.9+, standard library only; no Unity.
Run: python C:\Dev\Game\docs\drafts\economy_sim_capture_v01.py
Flags: --self-test; --report (only CAPTURE_DATA_v01.md).
New game tuning inputs are proposed, not approved balance.
"""
import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path('C:/Dev/Game')
REPORT = ROOT / 'docs/reports/CAPTURE_DATA_v01.md'
QUALITY = ('Damaged', 'Acceptable', 'Good', 'Perfect', 'Perfect+')
Q_PRICE = (0.3, 1.0, 1.6, 2.6, 4.2)
PRICE = dict(kidney=250, liver=350, eyes=200, lungs=450, heart=1000, brain=1200)
DISCOVERY = dict(kidney=100, liver=100, eyes=100, lungs=150, heart=200, brain=250)
COUNTS = dict(kidney=2, liver=1, eyes=2, lungs=1, heart=1, brain=1)
XP_ORGAN, XP_BLOOD, XP_FIRST_BLOOD, XP_ORDER = 20, 5, 50, 150
BAG_PRICE, BAG_COST, PACK_COST, GARBAGE_COST = 50, 5, 10, 5
STOCK = (200, 400, 800)  # approximately ten nominal uses
EQUIPMENT = {'knife': 100, 'restraints': 500, 'lamp': 250, 'saw': 1500,
             'hammer': 300, 'tray': 100, 'trolley': 500, 'cooler': 1000,
             'fridge': 5000, 'mop': 100, 'table': 1500, 'helper': 60000,
             'assessment': 90000, 'specialist': 120000, 'perfect_specialist': 180000}
SKILLS = (('Наркоз улучшенный', 1000, 1000), ('Наркоз поздний', 3000, 4000),
          ('Дозировка I', 500, 500), ('Дозировка II', 1000, 1500),
          ('Дозировка III', 2000, 3500), ('Торг I', 500, 500),
          ('Торг II', 1000, 1500), ('Торг III', 2000, 3500))
CHANCES = ((.40, .20, .05), (.55, .35, .15), (.70, .50, .25),
           (.85, .65, .40), (.95, .80, .60))
ASKS = (.05, .10, .20)
HANDLING = {1: .40, 2: .25, 3: .20, 4: .20}  # inherited draft assumptions
SECONDS = {1: 30, 2: 24, 3: 20, 4: 20}  # per actual item, not per type
MIX = {'early': (.15, .60, .20, .05, .00), 'late': (.05, .35, .40, .17, .03)}
SEQUENCE = {'early': ('kidney', 'kidney', 'liver'),
            'late': ('eyes', 'eyes', 'kidney', 'kidney', 'liver', 'brain', 'heart', 'lungs')}
LABEL = {'early': 'Хутор: 2 почки + печень', 'late': 'Позже: 8 органов'}
SOURCE_HASHES = {
    'docs/drafts/economy_sim.py': 'E4B68B9BE4F645863610159BDF81D3FA010C25F1726BE2C9559A45CB018C393F',
    'docs/specs/BUYERS_SPEC_2026-10-15_v02.md': '26C74E19BB5C6D0F105D747561904F28723678E9A6BFC47EE6E37D5EB0339009',
    'docs/specs/OPERATIONS_SPEC_2026-10-15_v01.md': 'B8E73357FE72D8434FE3935C9E1A255637C891A8F133F740703CBCC3F3085AAC',
    'docs/drafts/ECONOMY_PROGRESSION_DRAFT.md': 'EFFC8930B2FA67D325983460E1ABF1AF9B9E7719E078296712D3FC50260F814D'}


def down(q, steps=1):
    out = [0.] * 5
    for i, prob in enumerate(q):
        out[max(0, i - steps)] += prob
    return tuple(out)


def damage(q, probability):
    lower = down(q)
    return tuple((1 - probability) * a + probability * b for a, b in zip(q, lower))


def saturation(index):
    return max(.70, 1 - .05 * index)


def decay_steps(seconds, first_loss=85):
    # OPERATIONS T-04 is a proposed boundary, not a confirmed convention.
    return 0 if seconds < first_loss else 1 + int((seconds - first_loss) // 40)


def xp(players, organs, bags, seen=(), first_blood=False, orders=0):
    """Aggregate a sold batch; discovery once per type, not per physical unit."""
    personal = XP_ORGAN * len(organs) + XP_BLOOD * bags + XP_ORDER * orders
    personal += sum(DISCOVERY[k] for k in set(organs) - set(seen))
    personal += XP_FIRST_BLOOD if first_blood and bags else 0
    return players * personal


def safe_negotiation(respect, rank):
    probs = [min(.95, p + .05 * rank) for p in CHANCES[respect - 1]]
    # On first refusal accept base price (unresolved counteroffer assumed base).
    gains = [p * ask for p, ask in zip(probs, ASKS)]
    i = max(range(3), key=lambda j: gains[j])
    return 1 + gains[i], ASKS[i]


def risky_negotiation(respect, rank, first=2, second=1):
    assert second < first
    p = [min(.95, x + .05 * rank) for x in CHANCES[respect - 1]]
    failure = (1 - p[first]) * (1 - p[second])
    receipt = p[first] * (1 + ASKS[first]) + (1 - p[first]) * p[second] * (1 + ASKS[second])
    return receipt, failure  # unsold inventory retained on failure


def schedule(stage, players):
    t, seen, out = 0, set(), []
    for kind in SEQUENCE[stage]:
        zone = 'abdomen' if kind in ('kidney', 'liver') else 'chest' if kind in ('heart', 'lungs') else 'skull' if kind == 'brain' else 'eyes'
        if zone not in seen:
            t += {'abdomen': 20, 'chest': 35, 'skull': 35, 'eyes': 0}[zone]
            seen.add(zone)
        t += SECONDS[players]
        out.append((kind, t))
    return out


def death_branches(stage, players, blood, eye_modifier=False, death_rolls=True):
    """Exact mutually exclusive branches; death never deletes remaining outputs."""
    remaining, branches, kidneys = 1., [], 0
    for kind, t in schedule(stage, players):
        if kind == 'kidney':
            kidneys += 1
        chance = (.10 if kidneys == 1 else .20) if kind == 'kidney' else .30 if kind == 'liver' else 1. if kind in ('brain', 'heart', 'lungs') else 0.
        if kind in ('kidney', 'liver') or (kind == 'eyes' and eye_modifier):
            chance = min(1., chance + .10 * blood)
        if not death_rolls:
            chance = 0.
        if remaining * chance:
            branches.append((remaining * chance, t))
        remaining *= 1 - chance
    if remaining:
        branches.append((remaining, None))
    return branches


def organ_branches(stage, players, blood=2, death_rolls=True, storage_steps=0,
                   first_loss=85, eye_modifier=False):
    base_q = damage(MIX[stage], HANDLING[players])
    result = []
    for prob, death_at in death_branches(stage, players, blood, eye_modifier, death_rolls):
        rows = []
        for kind, t in schedule(stage, players):
            steps = storage_steps + (decay_steps(t - death_at, first_loss) if death_at is not None and t > death_at else 0)
            rows.append((kind, down(base_q, steps)))
        result.append((prob, rows))
    return result


def nominal_uses(stage, players, duration):
    """Stop anesthesia consumption at the first death, including terminal removal."""
    total = schedule(stage, players)[-1][1]
    return sum(prob * math.ceil((total if death_at is None else death_at) / duration)
               for prob, death_at in death_branches(stage, players, 2))


def convolve(a, b):
    out = [0.] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def sorted_type_value(branches, kind, batch=1, saturated=True):
    """Exact expected best-first saturation, including shared death correlation.

    For each grade threshold, convolve the distribution of the number of organs
    above it. The top N saturation weights multiply each quality-price increment.
    NPCs and intrinsic item grades are independent conditional on death branch.
    """
    count = sum(k == kind for k, _ in branches[0][1])
    weights = [saturation(i) if saturated else 1. for i in range(count * batch)]
    prefix = [0.]
    for w in weights:
        prefix.append(prefix[-1] + w)
    value = Q_PRICE[0] * prefix[-1]
    for threshold in range(1, 5):
        one_npc = [0.] * (count + 1)
        for branch_prob, rows in branches:
            pmf = [1.]
            for k, q in rows:
                if k == kind:
                    p = sum(q[threshold:])
                    pmf = convolve(pmf, [1 - p, p])
            for i, p in enumerate(pmf):
                one_npc[i] += branch_prob * p
        whole = [1.]
        for _ in range(batch):
            whole = convolve(whole, one_npc)
        value += (Q_PRICE[threshold] - Q_PRICE[threshold - 1]) * sum(p * prefix[n] for n, p in enumerate(whole))
    return PRICE[kind] * value


@dataclass(frozen=True)
class Value:
    gross: float
    net: float
    organs: float
    xp: int
    death_loss: float
    damaged: float
    mean_q: float


def npc_value(stage, players, blood=2, batch=1, rank=0, saturated=True,
              death_rolls=True, storage_steps=0, cooler=True, first_loss=85,
              eye_modifier=False):
    branches = organ_branches(stage, players, blood, death_rolls, storage_steps, first_loss, eye_modifier)
    organs = sum(sorted_type_value(branches, k, batch, saturated) for k in set(SEQUENCE[stage])) / batch
    organs *= 1. if cooler else .90
    factor, _ = safe_negotiation(2, rank)
    gross = (organs + blood * BAG_PRICE) * factor
    # Manual work, no ordinary organ bags, one garbage bag, 2/3 initial uses.
    costs = blood * BAG_COST + GARBAGE_COST + sum(prob * math.ceil((schedule(stage, players)[-1][1] if death_at is None else death_at) / 90) for prob, death_at in death_branches(stage, players, blood, eye_modifier, death_rolls)) * STOCK[0] / 10
    pre = organ_branches(stage, players, blood, False, storage_steps, first_loss, eye_modifier)
    no_death = sum(sorted_type_value(pre, k, batch, saturated) for k in set(SEQUENCE[stage])) / batch
    death_loss = (no_death * (1. if cooler else .90) - organs) * factor
    n = len(SEQUENCE[stage])
    damaged = sum(p * sum(q[0] for _, q in rows) for p, rows in branches) / n
    mean_q = sum(p * sum(sum(a * b for a, b in zip(q, Q_PRICE)) for _, q in rows) for p, rows in branches) / n
    return Value(gross, gross - costs, organs, xp(players, SEQUENCE[stage], blood, seen=DISCOVERY), death_loss, damaged, mean_q)


def earned(npcs, stage, players, normalized=False, order_every=0):
    if not npcs:
        personal = 55 if stage == 'early' else 0
    elif stage == 'early':
        # Tutorial syringe 55; NPC1 one bag, subsequent NPCs two bags.
        personal = 55 + 200 + 65 + (npcs - 1) * 70
    else:
        # New stage: zero free XP, kidney/liver/blood flags already used.
        personal = 700 + 170 * npcs
    if order_every:
        personal += XP_ORDER * (npcs // order_every)
    return personal * (2 if normalized else players)


def affordable(cost, stage, players, normalized=False, order_every=0):
    return next(n for n in range(10000) if earned(n, stage, players, normalized, order_every) >= cost)


def fmt(x, digits=0):
    return f'{0 if abs(x) < 1e-8 else x:,.{digits}f}'.replace(',', ' ')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(map(str, headers)) + ' |',
                       '| ' + ' | '.join('---' for _ in headers) + ' |'] +
                      ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def self_test():
    checks = 0
    def check(condition):
        nonlocal checks
        if not condition:
            raise AssertionError('Rule check failed')
        checks += 1
    check(sum(PRICE[k] * n for k, n in COUNTS.items()) == 3900)
    check(sum(PRICE[k] * n for k, n in COUNTS.items()) * 1.6 == 6240)
    check(xp(2, SEQUENCE['early'], 1, first_blood=True) == 630)
    check(xp(4, SEQUENCE['early'], 2, seen=DISCOVERY) == 280)
    check(xp(2, ('kidney', 'kidney'), 0) == 280)
    check(xp(1, ('kidney',), 0, seen=DISCOVERY, orders=1) == 170)
    check(sum(x[1] for x in SKILLS) == 11000)
    check([round(saturation(i), 2) for i in range(9)] == [1, .95, .9, .85, .8, .75, .7, .7, .7])
    for blood, expected in ((0, .496), (1, .664), (2, .79)):
        branches = death_branches('early', 1, blood)
        check(math.isclose(sum(p for p, t in branches if t is not None), expected))
    check([decay_steps(t) for t in (45, 84, 85, 124, 125)] == [0, 0, 1, 1, 2])
    check(down((0, 1, 0, 0, 0), 10) == (1., 0., 0., 0., 0.))
    check(math.isclose(safe_negotiation(2, 0)[0], 1.035))
    check(math.isclose(safe_negotiation(2, 3)[0], 1.06))
    # Best grade must take the first saturation weight, regardless of loading.
    fixture = [(1., [('kidney', (0, 0, 0, 0, 1)), ('kidney', (1, 0, 0, 0, 0))])]
    check(math.isclose(sorted_type_value(fixture, 'kidney'), 250 * (4.2 + .95 * .3)))
    check(math.isclose(sorted_type_value(fixture, 'kidney', 4), 250 * (4.2 * 3.7 + .3 * 2.95)))
    for stage in SEQUENCE:
        for p in range(1, 5):
            v = npc_value(stage, p)
            check(v.net < v.gross and v.death_loss >= -1e-8)
            check(npc_value(stage, p, batch=8).gross < v.gross)
            check(npc_value(stage, p, rank=3).xp == v.xp)
            check(npc_value(stage, p, storage_steps=4).xp == v.xp)
            check(affordable(4000, stage, p) >= affordable(1000, stage, p))
            for prob, rows in organ_branches(stage, p):
                check(prob >= 0 and all(math.isclose(sum(q), 1.) for _, q in rows))
    check(math.isclose(nominal_uses('early', 1, 90), 1.42))
    check(math.isclose(nominal_uses('late', 1, 90), 2.21))
    check(math.isclose(nominal_uses('late', 1, 300), 1.0))
    for stage in SEQUENCE:
        for players in range(1, 5):
            for _, _, cost in SKILLS:
                n = affordable(cost, stage, players)
                check(earned(n, stage, players) >= cost and (n == 0 or earned(n - 1, stage, players) < cost))
    # Exact count PMF formula versus independent enumeration for two organs.
    qa, qb = (.1, .2, .3, .25, .15), (.2, .4, .2, .1, .1)
    fixture = [(1., [('kidney', qa), ('kidney', qb)])]
    brute = 250 * sum(a * b * (max(Q_PRICE[i], Q_PRICE[j]) + .95 * min(Q_PRICE[i], Q_PRICE[j]))
                      for i, a in enumerate(qa) for j, b in enumerate(qb))
    check(math.isclose(brute, sorted_type_value(fixture, 'kidney')))
    return checks

# G33 extension to the copied G30 model; legacy functions remain above.
import hashlib
import json
import re
from contextlib import contextmanager

REPORT = ROOT / 'docs/reports/CAPTURE_DATA_v01.md'
MESSAGE_JSON = ROOT / 'docs/drafts/capture_messages.json'
MESSAGE_MD = ROOT / 'docs/drafts/CAPTURE_MESSAGES_DRAFT.md'
DATA = ROOT / 'Assets/OnlyVolunteers/Capture/Data'
CONSUMABLE_JSON = DATA / 'CaptureConsumables_v01.json'
UPGRADE_JSON = DATA / 'VanCargoUpgrades_v01.json'
OUTPUTS = (MESSAGE_MD, MESSAGE_JSON, CONSUMABLE_JSON, UPGRADE_JSON,
           DATA / 'README_v01.md', ROOT / 'docs/drafts/economy_sim_capture_v01.py', REPORT)
SOURCE_HASHES.update({
    'docs/specs/CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md':
        '61A27D8D6A5B2FE65DAD3CA067614E98B4094F709E1EBCD33216AAF489BB6087',
    'docs/drafts/economy_sim_v02.py':
        'B7EA7364A5DD5152408859552F95A74BB18E9CA5167B96DCD7684E05C27EF4DD',
    'docs/reports/ECONOMY_XP_CHECK_v02.md':
        '345BE13EC898A44C13661D666141A72E1847C529FDEE3A50C67825CF8A89B86A',
    'docs/drafts/BUYER_MESSAGES_DRAFT.md':
        'F503394C8FDE408533F1B3E3FECAFAF5295EAE2969A44DA7818BCD07DC64C8BB',
    'docs/drafts/buyer_messages.json':
        '1759CEC72B4DBE84924FE7483F0EA7265253DF9DAFFF072B0BA1774250F02C5F',
})
# Capture §6: approved qualitative district rows, proposed numerical weights.
DISTRICT_MIX = {'early': (0., .25, .75, 0., 0.), 'late': (0., 0., .50, .50, 0.)}
DISTRICT_LABEL = {'early': 'Хутор: 3 органа + 2 крови', 'late': 'Даунтаун: 8 органов + 2 крови'}
CONDITION_BASELINE = 85  # proposed, no D8 loss
NPCS_PER_POWER_DAY = 3  # proposed throughput, not measured
POWER_PER_DAY = {'early': 50, 'late': 200}  # confirmed ops §14
TIE_APPLICATIONS = 2  # proposed: hands AND feet
FLOOR_SATURATION = .70  # confirmed floor; applying it to all units is stress


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate JSON object key: ' + key)
        out[key] = value
    return out


def read_json(path):
    def invalid_constant(value):
        raise ValueError('Nonstandard JSON number: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique_object, parse_constant=invalid_constant)


def catalogs():
    return read_json(CONSUMABLE_JSON), read_json(UPGRADE_JSON)


def condition_steps(condition):
    if not 0 <= condition <= 100:
        raise ValueError('Condition outside capture D8')
    return 0 if condition >= 75 else 1 if condition >= 50 else 2 if condition >= 25 else 3


@contextmanager
def capture_quality(stage, condition):
    previous = MIX[stage]
    MIX[stage] = down(DISTRICT_MIX[stage], condition_steps(condition))
    try:
        yield
    finally:
        MIX[stage] = previous


def capture_value(stage, players, market='floor', condition=CONDITION_BASELINE,
                  head_bag=False, blood=2, cooler=True, batch=1,
                  first_loss=85, eye_modifier=False, negotiation=True):
    if stage not in DISTRICT_MIX or players not in (1, 2, 3, 4):
        raise ValueError('Unsupported scenario')
    if market not in ('floor', 'fresh', 'batch'):
        raise ValueError('Unsupported market')
    supplies, _ = catalogs()
    by_id = {item['id']: item for item in supplies['items']}
    with capture_quality(stage, condition):
        inherited = npc_value(stage, players, blood=blood, batch=batch,
                              saturated=market != 'floor', cooler=cooler,
                              first_loss=first_loss, eye_modifier=eye_modifier)
    # Constant 70% weight commutes with expectation and best-first sorting.
    organs = inherited.organs * (FLOOR_SATURATION if market == 'floor' else 1.)
    factor = safe_negotiation(2, 0)[0] if negotiation else 1.
    gross = (organs + blood * BAG_PRICE) * factor
    direct_cost = inherited.gross - inherited.net
    ties = TIE_APPLICATIONS * by_id['ZIP_TIES']['price']['dollars']
    bag = by_id['HEAD_BAG']['price']['dollars'] if head_bag else 0.
    power = POWER_PER_DAY[stage] / NPCS_PER_POWER_DAY
    return dict(gross=gross, legacy_cost=direct_cost, ties=ties, bag=bag,
                power=power, net=gross-direct_cost-ties-bag-power,
                sales=len(SEQUENCE[stage])+blood,
                xp=xp(players, SEQUENCE[stage], blood, seen=DISCOVERY))


def threshold(cost, margin):
    return max(0, math.ceil((cost - 1e-9) / margin)) if margin > 0 else None


def price_targets():
    _, upgrades = catalogs()
    first, second = (row['price']['dollars'] for row in upgrades['levels'])
    return first, second, first + second


def funding(value):
    first, second, total = price_targets()
    n1, n2, nt = (threshold(cost, value['net']) for cost in (first, second, total))
    return n1, n2, nt, nt - n1


def sale_cell(n, value):
    return f"{n} / {n * value['sales']}"


def capture_checks():
    checks = 0
    def check(condition, why):
        nonlocal checks
        if not condition:
            raise AssertionError(why)
        checks += 1
    supplies, upgrades = catalogs()
    rows = read_json(MESSAGE_JSON)
    ids = [row['id'] for row in rows]
    check(len(ids) == len(set(ids)) == 73, 'Text ID count/uniqueness')
    old_ids = {r['id'] for r in read_json(ROOT / 'docs/drafts/buyer_messages.json')}
    check(not set(ids) & old_ids, 'Buyer text ID collision')
    check(set(ids) == set(re.findall(r'^- \x60([^\x60]+)\x60$',
          MESSAGE_MD.read_text(encoding='utf-8'), re.M)), 'MD top ID list differs')
    for row in rows:
        check(set(row) == {'id','buyer','situation','ru','en','placeholders'}, 'Message shape')
        check(bool(re.fullmatch(r'capture\.[a-z0-9_.]+', row['id'])), 'ID style')
        check(bool(row['ru'].strip()) and bool(row['en'].strip()), 'Missing locale')
        ru = set(re.findall(r'\{([a-z_]+)\}', row['ru']))
        en = set(re.findall(r'\{([a-z_]+)\}', row['en']))
        check(ru == en == set(row['placeholders']), 'Placeholder mismatch')
        check(row['buyer'] in ('NPC','SYSTEM'), 'Unknown speaker')
        check(max(len(row['ru']),len(row['en'])) <= 100, 'Line too long')
    counts = {}
    for row in rows:
        counts[row['situation']] = counts.get(row['situation'], 0) + 1
    for recurring in ('van_knock','van_plead','van_threat','hands_tied','feet_tied',
                      'hands_and_feet_tied','bag_muffled','bag_disoriented','bag_bonk',
                      'bag_feet_pull','bag_feet_hop','bag_feet_fall','asleep_mumble',
                      'anesthesia_waking','van_over_capacity','blood_target_struggling',
                      'blood_target_dead','zip_ties_empty','undress_cloud','hat_falls','glasses_fall'):
        check(counts.get(recurring, 0) >= 2, 'Missing variants: ' + recurring)
    items = {row['id']: row for row in supplies['items']}
    check(len(items) == len(supplies['items']) == 6, 'Supply identity/count')
    check(items['ZIP_TIES']['price']['dollars'] == 5, 'D2 price')
    check(items['HEAD_BAG']['price']['status'] == 'proposed', 'Bag price authority')
    check(items['HEAD_BAG']['buildStage'] == 'B', 'D14 bag stage')
    for item in items.values():
        check(item['stackSize']['status'] == 'proposed', 'Stack authority')
        check(bool(item['specDecisionRefs']), 'Decision trace')
        check(item['inventoryItemId'] is None, 'Do not allocate Inventory ID')
        check(all(s['channel'] in ('pharmacy','underground_seller') for s in item['soldAt']), 'Shop')
        check(all(item[k].strip() for k in ('displayNameRu','displayNameEn',
              'descriptionRu','descriptionEn')), 'Missing bilingual item')
    for item_id in ('ANESTHETIC_STOCK_INITIAL','ANESTHETIC_STOCK_IMPROVED',
                    'ANESTHETIC_STOCK_LATE','EMPTY_BLOOD_BAG'):
        price = items[item_id]['price']
        check(price['kind'] == 'spec_reference' and 'dollars' not in price, 'Duplicate price')
        check(price['source']['section'] == '15.4', 'Wrong source section')
        check(price['source']['row'] in (ROOT / price['source']['path']).read_text(encoding='utf-8'),
              'Price row not found')
    check(upgrades['stockCapacity']['value'] == 3, 'D5 stock')
    check(upgrades['capacityPerLevel']['value'] == 1, 'D5 increment')
    check(upgrades['maximumCapacity']['value'] == 5, 'D5 maximum')
    check(upgrades['buildStage'] == 'B', 'D14 upgrade stage')
    check([x['capacity'] for x in upgrades['levels']] == [4,5], 'D5 levels')
    check([x['requiresPreviousLevel'] for x in upgrades['levels']] == [0,1], 'Prerequisite')
    cumulative = 0
    for level in upgrades['levels']:
        cumulative += level['price']['dollars']
        check(level['price']['status'] == 'proposed', 'Upgrade price authority')
        check(level['cumulativePrice']['dollars'] == cumulative, 'Cumulative pricing')
    check([condition_steps(x) for x in (100,75,74,50,49,25,24,0)] ==
          [0,0,1,1,2,2,3,3], 'D8 boundaries')
    check(math.isclose(850*sum(a*b for a,b in zip(DISTRICT_MIX['early'],Q_PRICE)),1232.5),
          'Independent Hamlet fixture')
    check(math.isclose(3900*sum(a*b for a,b in zip(DISTRICT_MIX['late'],Q_PRICE)),8190),
          'Independent Downtown fixture')
    for stage in DISTRICT_MIX:
        for players in range(1,5):
            v = capture_value(stage,players)
            check(math.isfinite(v['net']) and 0 < v['net'] < v['gross'], 'Margin')
            check(v['sales'] == (5 if stage == 'early' else 10), 'Output count')
            check(math.isclose(capture_value(stage,players,head_bag=True)['net'],
                  v['net']-items['HEAD_BAG']['price']['dollars']), 'Bag debit')
            check(capture_value(stage,players,condition=60)['net'] < v['net'], 'D8')
            for cost in price_targets():
                n = threshold(cost,v['net'])
                check(n*v['net']+1e-8 >= cost > (n-1)*v['net'], 'Threshold minimality')
            n1,n2,nt,extra = funding(v)
            check(math.isclose(n1*v['net']-price_targets()[0]+extra*v['net'],
                  nt*v['net']-price_targets()[0]) and nt*v['net'] >= price_targets()[2],
                  'Sequential carryover')
    check(capture_value('early',3)['net'] == capture_value('early',4)['net'], 'No party cash multiplier')
    check(threshold(2500,1000) == 3 and threshold(7500,1000) == 8, 'Funding fixture')
    check(threshold(2500,0) is None and threshold(2500,-1) is None, 'Unprofitable scenario')
    for path in OUTPUTS[:-1]:
        check(path.resolve().is_relative_to(ROOT.resolve()) and path.is_file(), 'Output outside repo/missing')
    check({p.suffix for p in DATA.iterdir() if p.is_file()} <= {'.json','.md'}, 'Data file types')
    return checks

REPORT_INTRO = "# [G33] Capture data v01 — тексты, расходники, кузов\n\nДата: 18 октября 2026. Статус: редакционные данные и расчётные предложения. Спецификации не изменены. Деньги — общий фонд, без множителя числа игроков. Новые игровые числа/политики помечены proposed; арифметические итоги — derived. Интеграции в игру нет.\n\n## 1. Источники и приоритет\n\n- C:\\Dev\\Game\\docs\\specs\\CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md — прочитан целиком; D1–D14 имеют приоритет для захвата/доставки.\n- C:\\Dev\\Game\\docs\\specs\\OPERATIONS_SPEC_2026-10-15_v01.md — §§5, 10–15, 16.3: кровь, наркоз, качество, цены, закупки.\n- C:\\Dev\\Game\\docs\\specs\\BUYERS_SPEC_2026-10-15_v02.md — продажи, насыщение, общий фонд, XP.\n- C:\\Dev\\Game\\docs\\drafts\\BUYER_MESSAGES_DRAFT.md и C:\\Dev\\Game\\docs\\drafts\\buyer_messages.json — стиль и форма локализации.\n- C:\\Dev\\Game\\Assets\\OnlyVolunteers\\Buyers\\Data\\*.json — прочитаны все шесть таблиц; образец camelCase, displayNameRu/En, существующий merchandiseId blood_bag.\n- C:\\Dev\\Game\\docs\\drafts\\economy_sim_v02.py и C:\\Dev\\Game\\docs\\reports\\ECONOMY_XP_CHECK_v02.md — численное ядро и явно подписанные прежние допущения.\n\nВ копии симулятора сохранены исходное численное ядро и 157 его проверок; старый генератор отчёта заменён на G33. Оригинал и его отчёт защищены SHA-256. Предложения G30 о другом XP, кулере 10 слотов, late-запасе за $400 и другой порче не приняты молча. Capture §6 заменяет старое G30 распределение качества.\n\nStage A: стяжки, сон/пробуждение, подсказки, облако, аксессуары, сток 3. Stage B: мешок/комбинации и расширения кузова. Наличие данных не включает Stage B. Вместимость — лежащие NPC, не сидячие пассажиры.\n\n## 2. Тексты\n\nСозданы 73 пары RU/EN в 30 ситуациях. Все новые ID стоят первым блоком CAPTURE_MESSAGES_DRAFT.md. JSON сохраняет ровно поля buyer_messages: id, buyer, situation, ru, en, placeholders. Префикс capture.* — строчные слова через точки, варианты _01/_02. Поле buyer: NPC/SYSTEM обозначает говорящего; нового покупателя тел нет.\n\n| Состояние | Варианты / правило |\n| --- | --- |\n| Проснулся в кузове | 3 стука, 3 просьбы, 3 угрозы/жалобы |\n| Руки / ноги / обе пары | По 3; руки не обещают остановку бега, ноги — прыжки, обе — гусеница |\n| Мешок | 3 приглушённые, 3 дезориентация, 3 после столкновения |\n| Мешок + ноги | 2 попытки снять, 2 прыжки, 3 падения; руки свободны, мешок остаётся |\n| Мешок + руки / полный буррито | По 2 дополнительных |\n| Сон / пробуждение после наркоза | По 4 |\n| Тесно / дёргается / труп / нет стяжек | 3 / 3 / 2 / 3 |\n| Связать руки/ноги, срезать, мешок | 6 prompts с локализованной кнопкой {interact} |\n| Облако / шапка / очки | По 3; ещё 1 системная подсказка для обоих упавших аксессуаров |\n\nProposed подача: выбирать без немедленного повтора, не накладывать несколько реплик одного NPC; числовой cooldown не выбран. Сон подавляет бодрые реплики; мешок требует приглушения. Аксессуары комментирует только бодрый NPC с соответствующей вещью; системная подсказка «шапка и очки» — только при падении обоих. Одежду полностью закрывает облако; после него тот же NPC в пациентских шортах. Аксессуары остаются мусором/уликами без денежного лута.\n\nОтказ «дёргается» относится к забору крови, а не к запрету всех действий с бодрым NPC. Отказ для трупа приоритетнее движения. Реплики не обнуляют остаток наркоза, не называют реальных препаратов/доз и не обещают безопасную инъекцию. Срезание требует допустимого ножа/скальпеля; отдельный полевой нож пока не решён.\n\n## 3. Расходники\n\n| ID | Цена / источник | Магазин | Стек | Расход |\n| --- | --- | --- | --- | --- |\n| ZIP_TIES | $5 за руки ИЛИ ноги — confirmed D2 / §5.1 | Аптека — proposed точная полка | 20 — proposed | 1 пара на применение, confirmed; обе пары $10 derived |\n| HEAD_BAG | $5 — proposed capture §5.1 | Подполье — proposed, магазин открыт в §11 | 10 — proposed | 1 надевание без возврата — proposed; Stage B |\n| ANESTHETIC_STOCK_INITIAL | Ссылка ops §15.4, Initial anesthetic stock, about ten nominal uses | Аптека — proposed | 1 ёмкость — proposed | Переменный по удержанию, ops §10.2 |\n| ANESTHETIC_STOCK_IMPROVED | Ссылка ops §15.4, Improved anesthetic stock, about ten nominal uses | Подполье — proposed | 1 ёмкость — proposed | Переменный; нужен навык ops §16.3 |\n| ANESTHETIC_STOCK_LATE | Ссылка ops §15.4, Late anesthetic stock, about ten nominal uses | Подполье — proposed | 1 ёмкость — proposed | Переменный; нужен навык ops §16.3 |\n| EMPTY_BLOOD_BAG | Ссылка ops §15.4, Empty blood bag | Аптека — confirmed §15.5 | 20 пустых — proposed | 1 пакет на порцию; не путать с выходом blood_bag |\n\nСсылочные цены JSON не содержат новых сумм. Разрешаются по точным файлу, разделу и строке таблицы; отсутствие суммы не означает бесплатно. У прочитанных операций нет утверждённого каталожного ID этих запасов. Новые ID — ключи authoring; inventoryItemId: null не назначает предмет 0. Ссылки не создают вторые экземпляры существующих товаров.\n\nОбщие каналы ops §15.5 сохранены: аптека — кровь/начальные припасы; подполье — специальный ассортимент; телефон — крупное оборудование. Точный ассортимент расходников, кроме пакетов крови, proposed. Телефонные заказы расходников не добавлены. Невозврат срезанных стяжек и снятого мешка proposed; снять мешок игрок может всегда. Мешок сам не убивает.\n\nСимулятор сохраняет исходные константы operations: $200/$400/$800 за приблизительно десять номинальных применений и $5 за пустой пакет (ops §§10.2, 15.4), $50 за заполненный (ops §§5.2, 15.2). Это ссылка на исходную экономику для расчёта, не новая цена в capture JSON. Запас не превращён в десять фиксированных бесплатных активаций; полевой stock/refill остаётся открытым.\n\n## 4. Цены кузова — proposed\n\n| Уровень | Всего лежащих NPC | Доплата | Всего со стока |\n| --- | --- | --- | --- |\n| Сток | 3 — confirmed D5 | Покупка самого фургона здесь не оценивается | — |\n| 1 | 4 — derived 3+1 | $2 500 — proposed | $2 500 — derived |\n| 2 | 5 — confirmed предел D5 | $5 000 — proposed | $7 500 — derived |\n\nProposed: последовательные уровни за общий фонд. L1 дороже кулера $1 000 и пилы/стола $1 500; L2 равен холодильнику $5 000, но оба намного ниже помощника $60 000 (ops §15.3). Удобство перевозки конкурирует с оснащением. Прирост полной загрузки: 3→4 = +33⅓%, 4→5 = +25%, 3→5 = +66⅔% (derived). Это не множитель денег/XP и не доказанная окупаемость во времени.\n\nProposed закупка: телефонный заказ крупного модуля, физический ящик у базы, затем монтаж по ещё не выбранному правилу — применение ops §15.5. Конкретные продавец, монтаж и его время не выдуманы. Дополнительных XP/районных замков нет. Четыре игрока не требуют четырёх грузовых мест: предел считает NPC.\n\n## 5. Допущения симуляции\n\nВсе отсутствующие в спеках сценарные параметры ниже — proposed, не статистика игры.\n\n- Два режима: Хутор — 2 почки + печень и 2 пакета крови; Даунтаун — 8 органов и 2 крови. Тип обычный, без сдвигов органов. Каждый выход продан. Инструменты, рабочая база и кулер уже приобретены. Свободный денежный остаток 0; он копится только на кузов. Доходов от тела, карманов или аксессуаров нет.\n- Capture §6: Хутор 75% Good / 25% Acceptable — proposed веса самой спеки; Даунтаун 50% Good / 50% Perfect — равные доли D9. Condition 85 — proposed сценарий, по D8 без потери. Condition 60 в чувствительности снимает ступень. Границы 75/50/25 не менялись. На каждый орган один штраф ступени с proposed вероятностью G30 40/25/20/20% для 1/2/3/4 игроков.\n- Сохранён последовательный темп G30: proposed 30/24/20/20 с на орган; открытие живота +20 с, головы/груди по +35 с однократно. Это не замер и не модель параллельных зон. Две крови до операции; брюшные риски 30/40/50%, глаза 0%. T-03 для глаз проверяется отдельно. Первая потеря в теле через 85 с — proposed T-04 после confirmed грейса 45 с, затем шаг 40 с. Альтернатива — первая потеря через 45 с. Смерть не удаляет оставшийся товар.\n- Извлечённый орган сразу охлаждается; доставка менее 25 минут при нулевом накопленном прогрессе. Кулер имеет подтверждённые 8 слотов; кровь едет отдельно и холода не требует. Для накопленной партии нужен соответствующий объём хранения. Ожидание NPC, маршрут и сохранность condition не измерены; вместимость кузова не останавливает пробуждение или порчу очереди.\n- Транспортная политика proposed: руки + ноги на каждого NPC, 2 × $5 = $10 стяжек. Мешок в основе отсутствует; чувствительность добавляет proposed $5. Наркоз в пути не добавлен — NPC едет связанным. За столом расход initial-запаса считается ядром G30 до первой смерти. Повторные применения — упрощение денежного расхода, не инструкция вводить полную порцию поверх остатка.\n- Прямые расходы G30: пустые пакеты крови, номинально потраченный initial-запас, один мусорный пакет $5 на NPC (последнее proposed; это мелкий мусор, не вместимость для тела). Обычных органных пакетов нет. Свет: confirmed $50/Хутор, $200/Даунтаун за сутки 45 активных минут; делится на proposed 3 NPC за этот срок. Улучшение не получает авансом ускорение оборота.\n- Запасы амортизированы по ожидаемому расходу. Целые закупки запаса $200 и текущие остатки могут сдвинуть порог. Разовый резерв и стоимость первоначального оснащения не спрятаны в марже; таблица начинается с уже работающего бизнеса.\n- Основная таблица: консервативный stress, все органы на подтверждённом полу насыщения 70%. Это не цена первого органа дня. Кровь не насыщается. Респект 2, навык торга 0: одна безопасная попытка, при отказе принять базу — proposed встречная цена; ожидаемый множитель 1.035. Реальный рост респекта не симулируется. Отдельно проверен нулевой торг.\n- Деньги не умножаются на игроков. Отличия составов только из proposed скорости/ошибок. XP соответствует BUYERS v02, но кузов покупается за деньги. Персонал/комиссии, новые базы, другие покупки, аресты, пропуски встреч и потерянный товар исключены: частоты не заданы.\n- Порог N = ceil(цена / ожидаемая чистая маржа). Это арифметика средних, не медиана случайной игры. L1 = ceil(A/M), L2 отдельно = ceil(B/M), оба = ceil((A+B)/M). После L1 остаток сохранён, дополнительных NPC = Nоба − NL1. Продажа означает физический предмет, не встречу/группу: 5 продаж/NPC в Хуторе, 10 в Даунтауне. Один предмет учитывается один раз.\n\n"
# G33 report implementation follows.

def build_report(checks):
    lines = [REPORT_INTRO.rstrip(), '']
    add = lines.append
    first, second, total = price_targets()
    def tab(headers, rows):
        add(table(headers, rows))
        add('')
    add('## 6. Основной расчёт: все органы на полу насыщения 70%')
    add('')
    tab(['Режим','Игроков','$ выручка/NPC','$ прямые G30','$ стяжки','$ свет/NPC','$ остаток/NPC'],
        [(DISTRICT_LABEL[s],p,fmt(v['gross'],2),fmt(v['legacy_cost'],2),
          fmt(v['ties'],2),fmt(v['power'],2),fmt(v['net'],2))
         for s in DISTRICT_MIX for p in range(1,5) for v in [capture_value(s,p)]])
    add('Ячейки ниже — **NPC / проданных предметов**. L2 отдельно: только дополнительная цена при пустом фонде; '
        'оба: действительный суммарный путь со стока. Последний столбец сохраняет остаток после L1.')
    add('')
    tab(['Режим','Игроков','L1: NPC / продажи','L2 отдельно от 0: NPC / продажи',
         'Оба: NPC / продажи','Ещё NPC после L1'],
        [(DISTRICT_LABEL[s],p,sale_cell(n1,v),sale_cell(n2,v),sale_cell(nt,v),extra)
         for s in DISTRICT_MIX for p in range(1,5) for v in [capture_value(s,p)]
         for n1,n2,nt,extra in [funding(v)]])
    add('Другие траты удлиняют путь. При фактической торговле партиями покупка может стать доступна только после группы/рейса. '
        'N считает проданный выход целого NPC, не гарантированную минуту покупки. '
        'Порог считается по неокруглённой марже; экранные суммы округлены только для таблиц.')
    add('')
    add('## 7. Чувствительность и размер рейса')
    add('')
    tab(['Режим','Игроков','Свежий день: $/NPC','Свежий день: оба NPC','Пол: оба NPC',
         'Пол + condition 60: $/NPC / оба NPC','Пол + мешок: оба NPC','Пол без торга: оба NPC'],
        [(DISTRICT_LABEL[s],p,fmt(fresh['net'],2),funding(fresh)[2],funding(base)[2],
          f"{fmt(low['net'],2)} / {funding(low)[2]}",funding(bag)[2],funding(nohaggle)[2])
         for s in DISTRICT_MIX for p in range(1,5)
         for fresh,base,low,bag,nohaggle in [(
             capture_value(s,p,market='fresh'),capture_value(s,p),
             capture_value(s,p,condition=60),capture_value(s,p,head_bag=True),
             capture_value(s,p,negotiation=False))]])
    add('Свежий день — отдельный ориентир: нулевые счётчики перед одним NPC; '
        'вторая почка/глаз уже под 95%, лучшие качества первыми. '
        'Повторять эту маржу можно только после реального сброса в 00:00. Основная таблица пола не требует скрытого сброса.')
    add('')
    tab(['Режим','Игроков','Партия 3: $/NPC','Партия 4: $/NPC','Партия 5: $/NPC'],
        [(DISTRICT_LABEL[s],p,*(fmt(capture_value(s,p,market='batch',batch=b)['net'],2) for b in (3,4,5)))
         for s in DISTRICT_MIX for p in range(1,5)])
    add('Партии 3/4/5 — отдельный proposed сценарий сбыта в одни сутки со свежими счётчиками, '
        'по точному G30 best-first насыщению каждого вида. '
        'Это не дополнительная постоянная маржа поверх основной таблицы. При большем рейсе маржа/NPC снижается, '
        'а число NPC растёт; кровь без насыщения. Нужны хранение и обработка всей партии, не один бесплатный кулер.')
    add('')
    tab(['Даунтаун, игроков','Пол: оба NPC','Пол + T-03 глаза: оба NPC',
         'Пол + первая порча в 45 с: оба NPC','Пол без кулера: оба NPC'],
        [(p,funding(capture_value('late',p))[2],funding(capture_value('late',p,eye_modifier=True))[2],
          funding(capture_value('late',p,first_loss=45))[2],
          funding(capture_value('late',p,cooler=False))[2]) for p in range(1,5)])
    add('Без кулера проверен confirmed штраф продажи −10%, без неизмеренных дорожных ступеней порчи. '
        'T-03/T-04 — чувствительность предложенных правил. Расширение может увеличить очередь и реальные потери; '
        'эти цифры не доказывают окупаемость в игровом времени.')
    add('')
    supplies,_ = catalogs()
    tie_price = next(x['price']['dollars'] for x in supplies['items'] if x['id']=='ZIP_TIES')
    blood_margin = 2*(BAG_PRICE-BAG_COST)-TIE_APPLICATIONS*tie_price-GARBAGE_COST
    add('Контроль только крови в бесплатном вагоне, одинаковый для всех составов 1–4: '
        'proposed 2 порции, 2 применения стяжек, 1 мусорный пакет, без торга/наркоза, свет 0. '
        f'Остаток {fmt(blood_margin)} USD/NPC; L1 {threshold(first,blood_margin)} NPC / '
        f'{2*threshold(first,blood_margin)} пакетов, L2 отдельно {threshold(second,blood_margin)} NPC / '
        f'{2*threshold(second,blood_margin)} пакетов; оба {threshold(total,blood_margin)} NPC / '
        f'{2*threshold(total,blood_margin)} пакетов. Это медленный ориентир, не выдача бесплатных шприцев '
        'и не доступность Stage B с начала. Разовый учебный шприц $10/XP не засчитан повторяемым доходом.')
    add('')
    add('## 8. Вывод и открытые вопросы')
    add('')
    add('Предложение $2 500 + $5 000 проходит грубую проверку на исходных ценах и capture-качестве: '
        'несколько ранних успешных NPC либо короткая покупка на развитой базе. '
        'Это удобство после оснащения, не самостоятельная поздняя денежная цель. '
        'Падение condition удлиняет путь; сначала проверить состояние/очередь, затем править цену. '
        'Баланс не объявляется утверждённым.')
    add('')
    for question in (
        'Утвердить ли $2 500/$5 000, последовательность и телефонный канал? '
        'Должен ли последний уровень быть поздней денежной целью, если полные наборы делают его доступным быстро?',
        'Мешок: утвердить ли proposed $5 и подпольного продавца? Возвращается ли он после снятия? '
        'Также подтвердить невозврат стяжек и proposed размеры стеков.',
        'Где улучшенный/поздний запас, как устроены полевой шприц/stock/refill (capture §11, ops T-06)? '
        'Ссылки нужно связать с единым каталогом, не создавать дубликаты.',
        'Какое связывание достаточно для крови по D7/CD-05: руки, ноги или обе пары? '
        'Тексты не обещают, что одна стяжка полностью обездвиживает.',
        'Нож/скальпель — существующий допустимый предмет или отдельный полевой инструмент? '
        'Где монтируется модуль кузова и как восстанавливается неудачный монтаж/сохранение? '
        'Новых цен/таймеров монтажа здесь нет.',
        'Нужны реальные время маршрута/очереди, condition, параллельность, частоты ошибок/утраты товара '
        'и целые остатки расходников для окончательных порогов и окупаемости.',
        'Частоты barks/голосовая подача требуют игрового прослушивания. '
        'Тексты Stage B не звучат в Stage A; шапка/очки срабатывают только по фактической вещи.',
    ):
        add('- ' + question)
    add('')
    add('## 9. Проверка и воспроизведение')
    add('')
    add('Plain Python 3.9+, только стандартная библиотека; проверено Python 3.12.10. Рабочий каталог C:\\Dev\\Game:')
    add('')
    add('~~~text')
    add('python C:\\Dev\\Game\\docs\\drafts\\economy_sim_capture_v01.py --self-test')
    add('python C:\\Dev\\Game\\docs\\drafts\\economy_sim_capture_v01.py')
    add('python C:\\Dev\\Game\\docs\\drafts\\economy_sim_capture_v01.py --report')
    add('~~~')
    add('')
    add(f'**PASS:** до генерации выполнено {checks} проверок, включая 157 исходного ядра. '
        'Дополнительно: строгий JSON с проверкой дублированных ключей, уникальные ID без коллизий с buyer_messages, '
        'обе локали/плейсхолдеры/краткость, MD список ID, повторные варианты, '
        'реальные строки цен operations без новых сумм, proposed-метки, D5/D8/D14, '
        'независимые известные стоимостные фикстуры, минимальность порогов и последовательный денежный остаток.')
    add('')
    add(f'**PASS:** SHA-256 всех {len(SOURCE_HASHES)} источников сверяются до и после генерации; '
        'оригинальный симулятор/отчёт и спецификации не перезаписываются. '
        '--report пишет только CAPTURE_DATA_v01.md. Все семь результатов проверяются на существование '
        'и принадлежность C:\\Dev\\Game. Data содержит только JSON/MD. Это проверка модели/данных, не игры.')
    add('')
    add('**NOT RUN:** Unity, запуск игры, мультиплеер, импорт/компиляция, плейтест/прослушивание '
        '(по заданию Unity не открывалась). Operation, map scenes, van/NPC/capture code, анимации и модели '
        'не редактировались. Чужие исходные изменения не включены в результат. Git stage/commit/push не выполнялись.')
    add('')
    add('## 10. Полный список созданных файлов')
    add('')
    for path in OUTPUTS:
        add('- ' + chr(96) + str(path) + chr(96))
    add('')
    return '\n'.join(lines)


def verify_sources():
    for relative,expected in SOURCE_HASHES.items():
        actual = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest().upper()
        if actual != expected:
            raise RuntimeError('Source changed since reading: ' + str(ROOT/relative))


def verify_outputs():
    for path in OUTPUTS:
        path.resolve().relative_to(ROOT.resolve())
        if not path.is_file():
            raise RuntimeError('Missing allowed output: ' + str(path))


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='G33 capture data and cargo economy; no Unity.')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--report',action='store_true')
    args = parser.parse_args()
    verify_sources()
    checks = self_test() + capture_checks()
    verify_sources()
    if args.self_test:
        print(f'PASS: {checks} checks; {len(SOURCE_HASHES)} source hashes unchanged.')
        return
    report = build_report(checks)
    verify_sources()
    if args.report:
        REPORT.resolve().relative_to(ROOT.resolve())
        REPORT.write_text(report,encoding='utf-8')
        verify_outputs()
        verify_sources()
        print(f'PASS: {checks} checks; {len(SOURCE_HASHES)} source hashes unchanged.')
        for path in OUTPUTS:
            print(path.resolve())
    else:
        print(report)


if __name__ == '__main__':
    main()



