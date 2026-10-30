#!/usr/bin/env python3
r"""G30: VOLUNTEERS ONLY economy/XP check v02; Python 3.8+, standard library.
Copied from economy_sim.py and reworked for BUYERS v02 / OPERATIONS v01.
This replaces the obsolete campaign pacing model, not the source file.
Run: python C:\Dev\Game\docs\drafts\economy_sim_v02.py
Flags: --self-test; --report (writes only the fixed report path).
All probabilities not supplied by the specs are explicit scenario assumptions.
"""
import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path('C:/Dev/Game')
REPORT = ROOT / 'docs/reports/ECONOMY_XP_CHECK_v02.md'
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



def build_report(checks):
    out = []
    def add(text=''):
        out.append(text)
    def tab(headers, rows):
        add(table(headers, rows))
        add()
    add('# [G30] VOLUNTEERS ONLY — проверка экономики и XP v02')
    add('Дата: 16 октября 2026. Расчётный отчёт; предложения не утверждены. Спецификации не изменены. Все суммы — доллары общего фонда, XP — свободный/пожизненный опыт команды до покупок, если не указано иначе. Unity не запускалась.')
    add()
    add('## 1. Источники, приоритет и границы модели')
    for path in SOURCE_HASHES:
        add(f'- `{ROOT / path}`')
    add()
    add('BUYERS v02 §«Решение v02 — опыт» заменяет старые XP из OPERATIONS §16.1 и её устаревшие оценки 17 NPC. Цены/качество/порча/риски/расходы — OPERATIONS §§5, 10–17. Старый ECONOMY_PROGRESSION_DRAFT и economy_sim.py используются только как источник явно отмеченных допущений качества и грубого обращения. Их вывод о 15–17 часах здесь не подтверждается: новая модель считает NPC и сделки, а не кампанию.')
    add('В копии заменён прежний расчёт кампании: убраны 3 обязательных пакета крови, качество-зависимый респект, выдуманные C03 ×1.5/×3/×4, денежная покупка рецептов и старые цены персонала/холодильников. Третий забор крови смертелен; базовая модель использует два. Обычная продажа органов не требует пакета. Спецзаказ требует пакет за $10; первый шприц стоит $10 и не торгуется.')
    add()
    add('## 2. Явные допущения')
    add('- Все игроки присутствуют в сессии при продаже. Деньги не умножаются на состав. Все восемь органов могут быть извлечены и проданы, включая Damaged; смерть не удаляет товар и сама по себе не отнимает XP. Кражи, аресты, потерянные предметы и пропущенные встречи не имеют заданной частоты и не включены скрытым общим процентом потерь.')
    add('- Хутор: почка → почка → печень. Позже: глаз → глаз → почка → почка → печень → мозг → сердце → парные лёгкие. Пила/молоток уже куплены; новые виды считаются доступными только на позднем этапе. Сначала безопасные глаза, затем брюшная зона, затем самые дорогие терминальные органы. Это выбранная стратегия, не требование спеки.')
    add('- Длительность каждого фактического органа: 30/24/20/20 секунд для 1/2/3/4 игроков. По одному открытию брюшной зоны +20 секунд, черепа +35, груди +35. Четвёртый не ускоряет работу за столом относительно третьего. Расчёт не моделирует реальную параллельность зон; нет замеров удобства или скорости.')
    add('- Первая потеря ступени в теле через 85 секунд после смерти, далее каждые 40: это предложенная граница T-04, а не отдельное Confirmed. Для чувствительности ниже также проверена первая потеря через 45 секунд. Извлечённый орган сразу убирают; в основных таблицах нет дальнейшей порчи на доставке, доставка в переносном холодильнике занимает менее 25 минут. Предшествующая дробная порча равна нулю.')
    add('- Распределение врождённого качества Хутора взято из village старого скрипта: 15/60/20/5/0%; позднее из old: 5/35/40/17/3%. На каждый орган независимо накладывается один штраф ступени с вероятностью 40/25/20/20% по составу из старого черновика. Это сценарий умеренно неаккуратной игры, не статистика релиза. Качества независимы при фиксированной ветви смерти; общая смерть связывает органы NPC.')
    add('- До операций собраны два пакета крови. Шансы брюшных извлечений 30/40/50%; для глаз оставлен Confirmed 0%. Неутверждённое T-03 (+10 п.п. за кровь также к глазам) показано отдельно. При извлечении мозг/сердце/лёгкие смертельны; повторных роллов на трупе нет. Передозировка/шок не включены без частот ошибок и спасений.')
    add('- Основной денежный столбец: свежие суточные счётчики, органы одного NPC продаются от лучших к худшим, респект 2. Торг безопасный: один запрос с максимальной ожидаемой прибавкой, при отказе согласие на исходную цену. Точная встречная цена пока открыта в спеке; здесь она принята равной базе. Кровь торгуется отдельно по той же политике.')
    add('- «После прямых расходов»: минус $5 за пустой пакет крови, $5 за один мусорный пакет на NPC, номинальный наркоз $20 за применение. В каждой ветви смерти число применений = ceil(время до смерти либо конца операции / 90 секунд); наркоз после смерти не расходуется. Повторное введение без дополнительной задержки/ошибки; из ветвей получается среднее дробное потребление. Один мусорный пакет на NPC — допущение, не утверждённая вместимость для тела. Никаких обычных органных пакетов. Электричество, амортизация, поездки и персонал в этом столбце ещё не вычтены.')
    add('- NPC в таблицах доступности — целые пороги накопления при успешной продаже всех выходов; не медиана случайной игры. Покупки других веток исключены только в первой таблице; отдельная очередь покупок ниже учитывает совместные траты. Качество и насыщение XP не меняют.')
    add()
    add('## 3. Контроль правил и цен')
    tab(['Вид', 'Штук', 'База за штуку', 'Good за штуку', 'Бонус нового вида / игрок'],
        [(k, COUNTS[k], PRICE[k], fmt(PRICE[k] * 1.6), DISCOVERY[k]) for k in COUNTS])
    add('Полный набор: $3 900 при Acceptable, $6 240 при Good. Брюшной набор: $850 / $1 360. Это до насыщения, крови и расходов. За каждый проданный орган +20 XP каждому; за пакет/учебный шприц +5, первая кровь +50; своевременный спецзаказ дополнительно +150 каждому. Бонусы вида: общие флаги сохранения, один раз, включая парные органы.')
    tab(['Оборудование', 'Цена из OPERATIONS'], [(k, fmt(v)) for k, v in EQUIPMENT.items()])
    add('Запасы наркоза: $200/$400/$800 за приблизительно десять номинальных применений; ориентир $20/$40/$80 за применение. Электричество за 45 активных реальных минут: Хутор $50, спальник $100, Даунтаун $200, лаборатория $500. Помощник удерживает 10%, специалист 20% только относимой прибыли; совместно 30%, не по полной ставке за каждого сотрудника. Эти покупки/накладные не маскируются под стоимость одного NPC.')
    add()
    add('### 3.1 Идеальный XP-ориентир v02, до реалистичных денежных потерь')
    tab(['Игроков', '1-й NPC Хутора: XP команды', 'Повтор Хутора, 2 крови', 'Полный набор, без крови', 'Полный набор + 2 крови', 'Новые поздние виды, разово'],
        [(p, xp(p, SEQUENCE['early'], 1, first_blood=True), 70*p, 160*p, 170*p, 700*p) for p in range(1, 5)])
    add('Первый столбец буквально воспроизводит пример спеки: 315 XP на игрока, без отдельного учебного шприца. В основной доступности навыков учебный шприц уже продан: он дал 55 XP/игрока и использовал флаг первой крови. Первый операционный NPC с одним пакетом даёт ещё 265, итого 320. Бонус первой крови дважды не начисляется. В таблице цены навыков N отсчитывается от первого операционного NPC, учебный NPC не включён; для числа всех захваченных NPC добавить один, если обучение использует отдельного NPC.')
    add()
    add('## 4. Ожидаемые XP и деньги на одного повторного NPC')
    rows = []
    for stage in SEQUENCE:
        for p in range(1, 5):
            v = npc_value(stage, p)
            rows.append((LABEL[stage], p, v.xp, fmt(v.gross), fmt(v.net), fmt(v.death_loss), f'{100*v.damaged:.1f}%'))
    tab(['Этап', 'Игроков', 'XP команды', 'Выручка', 'После прямых расходов', 'Потеря выручки из-за смерти', 'Доля Damaged на выходе'], rows)
    add('Смертельные броски меняют денежную цену через ступени порчи; XP в этих строках сохраняется, потому что все предметы всё равно продаются. Если предмет не довезён/не продан, орган теряет 20 × число игроков XP плюс возможный бонус первого вида, пакет — 5 × число игроков. Число игроков само по себе не меняет цены; отличия денег здесь вызваны только сценарными временем/повреждениями.')
    add()
    add('### 4.1 Реалистичный состав качества при продаже')
    rows = []
    for stage in SEQUENCE:
        for p in range(1, 5):
            q = [sum(prob * sum(dist[g] for _, dist in organs) for prob, organs in organ_branches(stage, p)) / len(SEQUENCE[stage]) for g in range(5)]
            rows.append((LABEL[stage], p, *(f'{100*x:.1f}%' for x in q)))
    tab(['Этап', 'Игроков', *QUALITY], rows)
    add('Это доли предметов, а не доли выручки; дорогие органы могут портиться сильнее дешёвых из-за порядка извлечения. Поэтому среднюю ступень нельзя бездумно умножить на $3 900.')
    add()
    add('## 5. Через сколько NPC доступны навыки')
    add('Хутор с новой игры: X(N)=P×(250+70N), N≥1; отдельно X(0)=55P за учебный шприц. Поздний этап: начинаем с нуля свободного XP, бонусы крови/почек/печени уже использованы, прочие виды ещё новые: X(N)=P×(700+170N), N≥1. Это два отдельных режима, а не прогноз момента переезда. Если поздние виды уже открыты, убрать 700P и считать ceil(цена/(170P)).')
    for stage in SEQUENCE:
        add(f'### {LABEL[stage]} — накопление только на выбранную ветку')
        tab(['Навык', 'Цена узла', 'Сумма с предшественниками', '1 игрок', '2 игрока', '3 игрока', '4 игрока'],
            [(name, cost, cumulative, *(affordable(cumulative, stage, p) for p in range(1, 5))) for name, cost, cumulative in SKILLS] +
            [('Все три ветки', '—', 11000, *(affordable(11000, stage, p) for p in range(1, 5)))])
    add('### 5.1 Общая очередь трат: нельзя тратить один и тот же XP дважды')
    queue = [('Дозировка I', 500), ('Улучшенный наркоз', 1500), ('Торг I', 2000),
             ('Дозировка II', 3000), ('Торг II', 4000), ('Поздний наркоз', 7000),
             ('Дозировка III', 9000), ('Торг III', 11000)]
    tab(['Покупка', 'Накоплено и потрачено всего', 'Хутор N: 1/2/3/4', 'Позже N: 1/2/3/4'],
        [(name, cost, ' / '.join(str(affordable(cost, 'early', p)) for p in range(1, 5)),
          ' / '.join(str(affordable(cost, 'late', p)) for p in range(1, 5))) for name, cost in queue])
    add('При покупке XP вычитается только из свободного остатка, пожизненный не уменьшается. Разница между последними N даёт число дополнительных NPC после предыдущей покупки. «Дозировка III за 2 000» или «поздний наркоз за 3 000 с нуля» без предшественников — неверный расчёт.')
    add()
    add('## 6. Насыщение: партии и типы')
    add('Один покупатель, одни игровые сутки, свежие счётчики перед партией. Каждый тип отдельно: 100/95/90/85/80/75/70%, затем 70%. Лучшие качества первыми; расчёт использует распределение числа предметов выше каждой ступени, учитывает общую ветвь смерти внутри NPC. Партия не пересекает полночь. Среднее на NPC ниже сравнивается с продажами в разные дни без насыщения; перенос между встречами в те же сутки счётчик не сбрасывает.')
    rows = []
    for stage in SEQUENCE:
        for p in range(1, 5):
            clean = npc_value(stage, p, saturated=False).gross
            vals = [npc_value(stage, p, batch=b).gross for b in (1, 2, 4, 8)]
            rows.append((LABEL[stage], p, fmt(clean), *(fmt(x) for x in vals), f'{100*(1-vals[-1]/clean):.1f}%'))
    tab(['Этап', 'Игроков', '$/NPC без насыщения', '1 NPC', '2 NPC', '4 NPC', '8 NPC', 'Потеря, 8 NPC'], rows)
    tab(['Одного вида в сутки', 'Средняя цена от базы, одинаковое качество'],
        [(n, f'{100*sum(saturation(i) for i in range(n))/n:.2f}%') for n in (1, 2, 4, 8, 16, 32)])
    add('Кровь и спецзаказы не насыщаются. XP остаётся 70P/170P на NPC при любой партии. Реальная частота зависит от маршрута: сутки = 45 минут активного мира, поэтому 8 NPC за одни сутки — стресс-сценарий накопленного запаса, а не обещанный обычный темп. Один переносной холодильник вмещает 8 предметов: поздний NPC с кровью даёт 10, ранний 5. Для 8 поздних NPC нужны 80 слотов (например, 10 переносных или 4 стационарных); большой батч не обеспечивается покупкой одного кулера.')
    add()
    add('## 7. Торг без навыка и на максимуме')
    tab(['Респект', 'Без навыка: запрос', 'Ожид. множитель', 'Макс.: запрос', 'Ожид. множитель', 'Прирост к выручке без навыка'],
        [(r, f'+{safe_negotiation(r, 0)[1]:.0%}', f'{safe_negotiation(r, 0)[0]:.4f}',
          f'+{safe_negotiation(r, 3)[1]:.0%}', f'{safe_negotiation(r, 3)[0]:.4f}',
          f'{100*(safe_negotiation(r, 3)[0]/safe_negotiation(r, 0)[0]-1):.2f}%') for r in range(1, 6)])
    rows = []
    for stage in SEQUENCE:
        for p in range(1, 5):
            a, b = npc_value(stage, p), npc_value(stage, p, rank=3)
            extra = b.gross - a.gross
            rows.append((LABEL[stage], p, fmt(a.gross), fmt(b.gross), fmt(extra, 1), math.ceil(500/extra)))
    tab(['Этап, респект 2', 'Игроков', 'Без навыка', 'Торг III', 'Разница / NPC', 'NPC для доп. $500'], rows)
    add('Последний столбец — ориентир денежной пользы, а не возврат 3 500 XP в долларах: курса обмена нет. При респекте 2 безопасные множители рангов 0/I/II/III: 1.035/1.040/1.050/1.060. Максимум навыка не означает гарантированные +20%; потолок вероятности 95%, не 100%.')
    tab(['Респект', 'Навык', '20% → 10%: получено на текущей встрече / база', 'Два отказа: доля срывов'],
        [(r, rank, f'{risky_negotiation(r, rank)[0]:.4f}', f'{risky_negotiation(r, rank)[1]:.1%}') for r in (2, 5) for rank in (0, 3)])
    add('На срыве товар сохраняется; таблица не считает его стоимость безвозвратно потерянной. Но текущая выручка и XP равны нулю по этой группе, −1 респект и запрет типа на 3 игровых часа (=5.625 реальной минуты); далее порча. Не включены новые встреча/дорога. Даже при максимальном навыке спам второй попытки имеет цену. Стартовый респект 30 (+2 знакомство) означает уровень 2; остальные уровни — независимая чувствительность, не вечный стартовый уровень.')
    add()
    add('## 8. Смертельные броски, кровь и хранение')
    tab(['Кровь до операции', 'Почка 1 / почка 2 / печень', 'Смерть к концу брюшного набора'],
        [(b, f'{10+10*b}% / {20+10*b}% / {30+10*b}%', f'{100*sum(p for p,t in death_branches("early", 1, b) if t is not None):.1f}%') for b in (0, 1, 2)])
    add('Для полного набора смерть неизбежна из-за терминальных органов. Важно время первой смерти. Для Хутора при базовом темпе все оставшиеся органы успевают до первой потери ступени; поэтому высокий процент смертей здесь не равен высокому проценту денежной потери.')
    rows = []
    for p in range(1, 5):
        vals = [npc_value('late', p, blood=b) for b in (0, 1, 2)]
        rows.append((p, *(fmt(v.net) for v in vals), fmt(vals[2].net-vals[0].net),
                     fmt(npc_value('late', p, eye_modifier=True).net), fmt(npc_value('late', p, first_loss=45).net)))
    tab(['Игроков', 'Позже, чистыми, 0 крови', '1 кровь', '2 крови', '2 против 0', '2 крови + T-03 на глаза', '2 крови, первая порча в 45 с'], rows)
    add('Чувствительность 45 с меняет только границу первой ступени, далее шаг 40 с. Это проверка неопределённости T-04. T-03 делает ранние глаза рискованными после забора крови; нельзя молча выдать этот пресет за принятое правило. Сбор после операций не моделируется: получение двух пакетов с уже мёртвого NPC спецификацией не гарантировано.')
    rows = []
    for stage in SEQUENCE:
        for p in range(1, 5):
            cool = npc_value(stage, p)
            room = npc_value(stage, p, storage_steps=2, cooler=False)
            long_cool = npc_value(stage, p, storage_steps=1)
            rows.append((LABEL[stage], p, fmt(cool.gross), fmt(room.gross), fmt(long_cool.gross), cool.xp))
    tab(['Этап', 'Игроков', '10 мин в кулере / powered fridge', '10 мин без охлаждения, −2 ступени и −10%', '25 мин в кулере, −1 ступень', 'XP одинаков'], rows)
    add('Интервалы хранения здесь начинаются после извлечения при нулевом накопленном прогрессе. Это отдельные сценарии: в настоящей поездке органы извлекаются в разное время. Стационарный powered fridge останавливает порчу, кулер только замедляет её; одно не заменяет другое. Отключённый fridge портит как комната.')
    add()
    add('## 9. Спецзаказы и отдача навыков')
    add('Первый заказ — конкретная почка HAMLET_BODYBUILDER, минимум Good. При Good $250×1.6×1.25=$500; после обязательного пакета $490 до прочих расходов; с согласованными +20% $600, без кулера $540. При опоздании премия 25% исчезает, торг сохраняется: $480 при тех же Good/+20%, а +150 XP и +5 респекта за срок отсутствуют. Насыщения нет. Нельзя одновременно засчитать эту почку обычной продажей и спецзаказом.')
    add('В срок добавляется 150P XP сверх обычных 20P за эту же почку: эквивалент 2.14 повторных ранних NPC или 0.88 позднего NPC. Респект первого органного покупателя: 30+2 знакомство; первый ранний NPC +5 (первая почка +2, вторая +1, первая печень +2), второй +3 → 40. Без провалов первый заказ доступен после двух ранних NPC. Кровь продаётся C01 и не повышает респект органного покупателя.')
    tab(['Игроков', 'Все навыки: ранние NPC без заказов', 'Если один своевременный заказ каждые 3 NPC', 'Позже без заказов', 'Позже заказ каждые 3 NPC'],
        [(p, affordable(11000, 'early', p), affordable(11000, 'early', p, order_every=3),
          affordable(11000, 'late', p), affordable(11000, 'late', p, order_every=3)) for p in range(1, 5)])
    add('Частота раз в 3 NPC — только чувствительность. В спеке нет такого расписания; один активный слот, конкретный NPC, утро 06–10 и срок 48 игровых часов (=90 активных реальных минут) не позволяют начислять +150 за каждый случайный орган. Следующий специализированный покупатель пока не имеет утверждённых цен, поэтому не добавлен множитель его рынка.')
    add('### 9.1 Наркоз: XP открывает покупку, а не бесплатный расходник')
    tab(['Этап', 'Игроков', 'Операции, секунд', 'Initial: ожид. применения / $', 'Improved: ожид. применения / $', 'Late: ожид. применения / $'],
        [(LABEL[stage], p, schedule(stage, p)[-1][1],
          *(f'{nominal_uses(stage,p,seconds):.2f} / {nominal_uses(stage,p,seconds)*cost:.2f}' for seconds, cost in ((90,20),(180,40),(300,80))))
         for stage in SEQUENCE for p in range(1,5)])
    add('При нулевой вероятности ошибки поздний наркоз в этих сценариях не окупается денежно: он дороже или равен коротким применениям. Даже если полная процедура длиннее 300 секунд, после терминального извлечения наркоз уже не нужен; расчёт прекращает расход при первой смерти. Его ценность — меньше вмешательств, меньше риска пробуждения/смешанной дозы, больше свободы рук. Без вероятности передозировки/ошибки и её зависимости от ширины 1/1.25/1.5/2 нельзя доказать экономическую окупаемость дозировки. Эти неизвестные не заменены выдуманной гарантированной прибавкой качества.')
    add('Разница найма error-free специалиста $60 000: в контрольном полностью Good наборе устранение 5% одношаговых ошибок даёт $117 выручки, после 20% комиссии $93.60, окупаемость 642 набора с округлением вверх. Реальные сроки могут быть ещё хуже из-за Damaged-пола, порчи, насыщения и общей доли помощника. Ускорение/удобство здесь не оценено.')
    add()
    add('## 10. Проблемы и предлагаемые числа — только для обсуждения')
    add('1. **XP резко зависит от состава, денежный прогресс — гораздо слабее.** Новые поздние виды дают квартету 2 800 XP разом; первый полный поздний NPC даёт 3 480 XP при нулевом входном свободном XP. Соло на всю текущую линейку в раннем режиме нужно 154 NPC, квартету 36. Предлагается сохранить базу дуэта, но фиксировать командное вознаграждение: 40 XP/орган, 10/пакет, новинки 200/200/200/300/400/500, первая кровь 100, своевременный заказ 300. Личный вклад = командная награда / P, дробные остатки сохранять. Это осознанное изменение Confirmed v02, поэтому только предложение, не текущий расчёт. Состав на момент продажи больше не ускоряет/тормозит общий unlock.')
    add('2. **Слишком ранний каталог может открыть дорогую ветку до её обучения.** Предложенная нормализация снимает квартетный всплеск без увеличения solo-гринда. Цены навыков пока оставить 1 000/3 000, 500/1 000/2 000, 500/1 000/2 000; сначала тестировать нормализацию отдельно, не менять сразу обе стороны экономики.')
    tab(['Порог при фиксированной командной награде дуэта', 'Хутор NPC, любой состав', 'Позже NPC, любой состав'],
        [(name, affordable(cost, 'early', 2, normalized=True), affordable(cost, 'late', 2, normalized=True))
         for name, cost in (('Дозировка I / Торг I',500),('Улучшенный наркоз',1000),('Макс. дозировка / торг',3500),('Поздний наркоз с предшественником',4000),('Вся линейка',11000))])
    add('3. **XP и деньги расходятся при массовом сбыте плохого товара.** Даже восемь Damaged-органов дают 160 XP/игрока. Сохранить качество-независимые XP и предел насыщения −30% в первом тесте; не вводить второй денежный/XP штраф без данных. Для организации хранения предложить стартовую вместимость кулера **10 вместо 8**, чтобы один полный NPC + 2 крови помещался; цена **$1 000 без изменения**. Текущая вместимость 8 уже достаточна для всех органов, если не требующая охлаждения кровь едет отдельно в обычном инвентаре. Поэтому 10 слотов — только предложение удобства, не обязательное исправление экономики.')
    add('4. **Кровь до сложной операции может уменьшать итоговый доход.** Высокие шансы ранней смерти + длинная последовательная работа особенно бьют по соло. Сначала проверить выбранный порядок и реальную параллельность. Изолированный пресет для плейтеста: grace **90 вместо 45 секунд**, шаг порчи **60 вместо 40**, первая потеря в **150 секунд**. Никаких удалений органов при смерти; шансы 10/20/30 и +10 п.п. за кровь пока оставить.')
    rows = []
    for p in range(1,5):
        branches = organ_branches('late', p)
        base_q = damage(MIX['late'], HANDLING[p])
        tuned = []
        for prob, death_at in death_branches('late', p, 2):
            organs = []
            for kind, t in schedule('late', p):
                steps = 0 if death_at is None or t-death_at < 150 else 1+int((t-death_at-150)//60)
                organs.append((kind, down(base_q, steps)))
            tuned.append((prob, organs))
        revenue = (sum(sorted_type_value(tuned,k) for k in COUNTS)+100)*safe_negotiation(2,0)[0]
        rows.append((p, fmt(npc_value('late',p).gross), fmt(revenue), fmt(revenue-npc_value('late',p).gross)))
    tab(['Игроков', 'Поздняя текущая выручка', 'Пресет 90 с / 60 с', 'Прирост / NPC'], rows)
    add('5. **Длинная формула не даёт чистой денежной экономии.** Предложить цену late-запаса **$400 вместо $800** за те же ~10 номинальных применений; improved оставить $400. Это $40 за применение: в позднем сценарии при двух предварительных порциях крови late обойдётся примерно в $40 против $34–44.20 на initial. Повторные применения прекращаются при смерти; скидка не гарантирует денежного превосходства во всех режимах. Стоимость XP late 3 000 пока оставить; измерить провалы/пробуждения и число вмешательств. Для дозировки до появления кривой ошибок цены 500/1 000/2 000 оставить, требование телеметрии: число недосыпов/передозировок на 100 NPC по рангу.')
    add('6. **Торг III: 3 500 XP ради примерно 2–3% выручки.** Максимальный безопасный торг полезен, но может проигрывать более заметной длительности/дозировке по приоритету. Контрольный вариант — цены **300/600/1 200 XP (всего 2 100)** при прежних +5/+5/+5 п.п. Проверять отдельно от XP-нормализации; уверенного «никогда не окупается» нет, потому что навык приносит постоянный денежный плюс и XP не имеет денежного курса.')
    add('7. **Error-free специалист слишком дорог для одной лишь защиты качества.** Предложить цену **$135 000 вместо $180 000**, basic оставить $120 000, комиссия 20% без изменения. Премия $15 000 / $93.60 ≈ **161 Good-набор** даже в благоприятном контрольном расчёте; если целевой остаток кампании меньше, следующая проверяемая точка **$130 000**, премия ≈107 наборов. Не объявлять окупаемость за кампанию без её реального объёма.')
    add('8. **Первый спецзаказ даёт больше двух ранних NPC повторного XP.** Пока оставить +150/игрока; при нормализации +300 команде. Если тест с фактической частотой заказов показывает рывки, пробный бонус **+100/игрока** (или **200 команде** при нормализации), не менять +25% денег, 48 часов и один активный слот. Частоту предложений сначала измерить; не добавлять без запроса суточный лимит.')
    add('Предложения выше — независимые варианты. Основные таблицы §§3–9 используют только действующие цены/XP и явно обозначенные допущения. Таблицы альтернатив отдельно подписаны; спецификации не правились.')
    add()
    add('## 11. Воспроизведение и фактические проверки')
    add('Запуск из любого каталога, только стандартная библиотека Python:')
    add('```text\npython C:\\Dev\\Game\\docs\\drafts\\economy_sim_v02.py\npython C:\\Dev\\Game\\docs\\drafts\\economy_sim_v02.py --self-test\npython C:\\Dev\\Game\\docs\\drafts\\economy_sim_v02.py --report\n```')
    add(f'**PASS:** встроенная проверка выполнена до генерации отчёта: {checks} проверок. Контроль цен $3 900/$6 240, пример 630 XP, единичные бонусы вида/заказа, ступени насыщения, сортировка по качеству (включая независимый перебор 25 сочетаний), смерти 49.6/66.4/79%, границы порчи, ожидаемый торг, неизменность XP при порче/насыщении и пороги предшественников. Это расчётные проверки модели, не тесты реализации игры.')
    add('**PASS:** перед записью отчёта проверены SHA-256 всех четырёх источников относительно прочитанных оригиналов. **NOT RUN:** Unity, мультиплеер, игровой плейтест, измерение длительности кампании. Остались неизвестными реальные распределения качества/ошибок, время и параллельность операций, встречная цена, частота заказов и условия следующего покупателя.')
    add('Созданы/изменены только два файла (оба проверяются на существование и расположение в C:\\Dev\\Game при --report):')
    add('- `C:\\Dev\\Game\\docs\\drafts\\economy_sim_v02.py`')
    add('- `C:\\Dev\\Game\\docs\\reports\\ECONOMY_XP_CHECK_v02.md`')
    import re
    return re.sub(r'\n{3,}', '\n\n', '\n\n'.join(out)) + '\n'


def verify_sources():
    import hashlib
    for relative, expected in SOURCE_HASHES.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()
        if actual != expected:
            raise RuntimeError('Source changed since reading: ' + str(ROOT / relative))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    checks = self_test()
    verify_sources()
    if args.self_test:
        verify_sources()
        print(f'PASS: {checks} rule checks; all four sources unchanged.')
        return
    report = build_report(checks)
    if args.report:
        verify_sources()
        for path in (Path(__file__).resolve(), REPORT.resolve()):
            path.relative_to(ROOT.resolve())
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report, encoding='utf-8')
        for path in (Path(__file__).resolve(), REPORT.resolve()):
            if not path.is_file():
                raise RuntimeError('Missing output: ' + str(path))
        print(f'PASS: {checks} checks; four sources unchanged. Verified files:')
        print(Path(__file__).resolve())
        print(REPORT.resolve())
    else:
        print(report)


if __name__ == '__main__':
    main()

