#!/usr/bin/env python3
"""VOLUNTEERS ONLY - economy and progression pacing simulator.

DRAFT PROPOSAL, NOT APPROVED. Every number below is a tuning proposal for discussion
(see docs/drafts/ECONOMY_PROGRESSION_DRAFT.md), not a confirmed design decision.

Deterministic expected-value model of the main story. The team repeats capture cycles
(find an NPC -> capture -> van -> base -> short procedure -> sell -> dispose of the body);
income buys items from a per-stage shopping list; hidden per-buyer trust counters
(volume x quality, map spec 8.3) open contacts and orders. Road distances are shortest
van routes measured on ArtSource/References/Map/MAP_PLAN_R01_v05.json.
Standard library only, Python 3.8+.

    python docs/drafts/economy_sim.py                    # tables for 1-4 players
    python docs/drafts/economy_sim.py --players 2 --log  # event timeline of one team
    python docs/drafts/economy_sim.py --pace slow        # fast | normal | slow
"""
import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field

# ------------------------------------------------------------------ quality
QUALITY = ("Damaged", "Normal", "Good", "Perfect", "Perfect+")
Q_PRICE = (0.3, 1.0, 1.6, 2.6, 4.2)   # price multiplier per tier
Q_TRUST = (0.5, 1.0, 1.5, 2.5, 4.0)   # hidden trust points per sold organ
GOOD, PERFECT = 2, 3


@dataclass(frozen=True)
class District:
    name: str
    find: float       # minutes to pick a target (duo baseline)
    capture: float    # minutes of physical capture (duo)
    carry: float      # minutes to drag, load and secure (duo)
    quality: tuple    # potential quality distribution over QUALITY (map spec 9.1)
    risk: float       # extra chaos overhead: witnesses, police, guards


DISTRICTS = {
    "village": District("деревня у вагона", 1.0, 2.5, 2.5, (0.15, 0.60, 0.20, 0.05, 0.00), 0.00),
    "bad": District("спальник", 1.5, 3.0, 2.0, (0.20, 0.50, 0.25, 0.05, 0.00), 0.05),
    "old": District("старый город", 2.5, 3.5, 2.5, (0.05, 0.35, 0.40, 0.17, 0.03), 0.10),
    "elite": District("элитка", 5.0, 5.0, 3.0, (0.00, 0.15, 0.40, 0.33, 0.12), 0.20),
}


@dataclass(frozen=True)
class Team:
    find: float      # multiplier on search time
    grab: float      # multiplier on capture + carry time (max 3 holders, canon 110-112)
    drop: float      # chance that rough delivery lowers quality one tier (canon 24, 137)
    overhead: float  # chaos, walks, police, failed tries: share of productive time
    overlap: float   # share of base chores done in parallel with the next hunt


TEAMS = {
    1: Team(1.2, 1.7, 0.40, 0.20, 0.00),
    2: Team(1.0, 1.0, 0.25, 0.35, 0.20),
    3: Team(0.9, 0.85, 0.20, 0.45, 0.45),
    4: Team(0.8, 0.80, 0.20, 0.55, 0.55),
}
PACE = {"fast": 0.5, "normal": 1.0, "slow": 1.6}   # multiplier on the overhead


@dataclass(frozen=True)
class Organ:
    key: str
    name: str
    price: int       # C02 price of one Normal organ, $
    count: int       # organs per NPC (canon 140)
    needs: tuple     # items required to extract it (canon 141)


ORGANS = (
    Organ("kidney", "почки", 250, 2, ()),
    Organ("liver", "печень", 350, 1, ()),
    Organ("lungs", "лёгкие", 450, 1, ("tool1",)),
    Organ("heart", "сердце", 1000, 1, ("tool2", "anest1")),
    Organ("eyes", "глаза", 200, 2, ("tool3",)),
    Organ("brain", "мозг", 1200, 1, ("tool5",)),
)

# ------------------------------------------------------------ blood, buyers, orders
BAGS_PER_NPC = 3
BAG_PRICE = 50          # C01 pays per filled special bag
BAG_COST = 5            # empty bag at the pharmacy P03
FIRST_C01_PAYMENT = 50  # one-off payment for the syringe blood (map spec 6.1)
C03_FACTOR = 1.5        # C03 pays more than C02 but takes only Good+ (map spec 8.1)
C02_ORDER_BONUS = 0.15  # C02 repeat orders for specific organs after trust step 1
SPECIAL_MULT = 3.0      # C03 special order vs C03 regular price
ELITE_MULT = 4.0        # elite/VIP orders vs C03 regular price
SPECIAL_RATE = 1.5      # special orders offered per hour after C03 step 1
ELITE_RATE = 1.0        # extra elite orders per hour after C03 step 2
ORDER_CAP = 2.0         # unfilled offers expire: at most this many wait
FIRST_ORDER_CASH = 200  # bonus for the first specific order of C02 (map spec 7, step 4)
FIRST_ORDER_TRUST = 5
SPECIAL_TRUST = 6       # extra trust per filled special order

# Hidden trust thresholds (map spec 8.3: per buyer, volume x quality, no visible bar).
TRUST = {
    "C01_hint": 9,       # bags sold: C01 mentions C02 (only after the van)
    "C02_orders": 15,    # C02 starts repeat orders for specific organs
    "C02_phone": 58,     # C02 gives the hospital contact's phone
    "C03_special": 12,   # C03 special orders
    "C03_elite": 210,    # C03 elite/VIP orders
    "C03_final": 290,    # final VIP order: main resident of the elite hill
}

# ------------------------------------------------------------------- map, van
SPEED = 600.0       # m/min: stock van city average incl. turns and acceleration (36 km/h)
ENGINE_STEP = 67.0  # m/min per engine level (~+4 km/h average, VanUpgradeConfig +10/20/30 top)
DIST = {            # metres, shortest van routes on MAP_PLAN_R01_v05 road graph
    ("B02", "bad"): 1380, ("B02", "P04"): 1038,
    ("B03", "bad"): 450, ("B03", "P04"): 861, ("B03", "old"): 1114, ("B03", "P09"): 1009,
    ("B04", "old"): 400, ("B04", "P09"): 201, ("B04", "P04"): 1233, ("B04", "elite"): 838,
    ("B05", "old"): 974, ("B05", "P09"): 1240, ("B05", "P04"): 2272, ("B05", "elite"): 1105,
}

# ------------------------------------------------------------------- purchases
ITEMS = {  # key: (name, price $, spending category)
    "van": ("бусик деда (мирная ветка)", 400, "транспорт"),
    "fridge1": ("базовый холодильник", 300, "оборудование"),
    "tool1": ("инструмент ур.1", 400, "инструменты"),
    "engine1": ("двигатель ур.1", 900, "бусик"),
    "B03": ("гараж B03", 3000, "базы"),
    "tint": ("тонировка", 2000, "бусик"),
    "brakes1": ("тормоза ур.1", 800, "бусик"),
    "handling1": ("управляемость ур.1", 800, "бусик"),
    "tool2": ("инструмент ур.2", 1500, "инструменты"),
    "anest1": ("анестезия ур.1", 1500, "оборудование"),
    "hidden": ("тайники в бусике", 2000, "бусик"),
    "engine2": ("двигатель ур.2", 2500, "бусик"),
    "fridge2": ("медицинский холодильник", 3000, "оборудование"),
    "tool3": ("инструмент ур.3", 3000, "инструменты"),
    "B04": ("дом B04", 14000, "базы"),
    "brakes2": ("тормоза ур.2", 1500, "бусик"),
    "handling2": ("управляемость ур.2", 1500, "бусик"),
    "anest2": ("анестезия ур.2", 4000, "оборудование"),
    "engine3": ("двигатель ур.3", 6000, "бусик"),
    "pistol": ("первый пистолет", 6000, "снаряжение"),
    "B05": ("промкомплекс B05", 30000, "базы"),
    "cleaner": ("уборщик", 8000, "персонал"),
    "packer": ("упаковщик", 8000, "персонал"),
    "driver": ("водитель", 12000, "персонал"),
    "surgeon": ("хирург", 20000, "персонал"),
    "brakes3": ("тормоза ур.3", 4000, "бусик"),
    "handling3": ("управляемость ур.3", 4000, "бусик"),
    "tool5": ("инструмент ур.5 (лазер)", 20000, "инструменты"),
    "scanner": ("прибор оценки NPC", 25000, "снаряжение"),
}
B06_PRICE = 100000      # optional prestige property, outside the main story
FUN_SHARE = 0.08        # share of income put aside for fun purchases from S2 on (canon 89)
FUN_ITEMS = (           # bought in this order from the fun budget; secondary system
    ("маски", 200), ("одежда", 600), ("кастомизация бусика", 1500), ("вещи для базы", 3000),
    ("смешные предметы", 5000), ("золотой скальпель ур.4", 10000), ("обстановка B05", 20000),
)

# Minutes at the base per NPC (canon 40: an early operation takes 20-40 s per organ).
UNLOAD, BLOOD_DRAW, PACKING, C01_VISIT = 0.8, 0.4, 0.4, 0.3
CALM = (1.0, 0.6, 0.3)  # NPC fixed on the table before/with anesthesia levels 0-2 (canon 43-44)
OP_PER_ORGAN = 0.4      # per organ type; a hired surgeon takes 70% of routine cutting
DISPOSAL = 2.0          # bins or water near the base (canon 61); 0 with a cleaner
PROLOGUE_CHORES = 0.5 + 0.8 + 0.3  # unload, blood into bags, C01 visit share
LOSS, LOSS_HIDDEN = 0.06, 0.04  # torn bags, evacuations, arrests, spoiled goods
GRANDPA_BEAT = 7        # walk to P02, talk, pay, starter repair (minutes)
KILL_EXTRA_REPAIR = 3   # repair without grandpa's hints (assumption)
FINAL_PLAN, FINAL_CAPTURE = 15, 25  # final VIP mission: scouting + capture (x team.grab)


@dataclass(frozen=True)
class Stage:
    sid: str
    title: str
    hunt: str       # district where the team hunts
    intro: float    # minutes of fixed story beats at the stage start
    beats: str
    shop: tuple     # shopping list in priority order
    gate: tuple     # ("item", key) or ("trust", buyer, TRUST key)
    target: tuple   # proposed minutes for 2-3 players (low, high)


STAGES = (
    Stage("S0", "Пролог: кровь -> бусик", "village", 10,
          "объявление P01, кровь из шприцев, вводная сделка C01, пакеты в аптеке P03",
          ("van",), ("item", "van"), (40, 50)),
    Stage("S1", "Бусик, приёмка C02, хижина B02", "bad", 12,
          "намёк C01, приёмка P04 и C02, первый заказ, хижина B02",
          ("fridge1", "tool1", "engine1", "B03"), ("item", "B03"), (90, 120)),
    Stage("S2", "Гараж B03 в спальнике", "bad", 5, "переезд в B03",
          ("tint", "brakes1", "handling1", "tool2", "anest1", "hidden", "engine2"),
          ("trust", "C02", "C02_phone"), (150, 180)),
    Stage("S3", "C03, старый город, дом B04", "old", 6, "первая встреча с C03 у P09",
          ("fridge2", "tool3", "B04", "brakes2", "handling2", "anest2", "engine3", "pistol", "B05"),
          ("item", "B05"), (210, 270)),
    Stage("S4", "Промкомплекс B05, персонал, автоматизация", "old", 8, "переезд в B05, найм",
          ("cleaner", "brakes3", "packer", "handling3", "driver", "surgeon", "tool5"),
          ("trust", "C03", "C03_elite"), (210, 270)),
    Stage("S5", "Элитка и VIP-финал", "elite", 5, "первые элитные заказы C03",
          ("scanner",), ("trust", "C03", "C03_final"), (120, 150)),
)

UNLOCKS = (  # (buyer, TRUST key, flag, event text)
    ("C02", "C02_orders", "c02_orders", "C02: повторные заказы на конкретные органы"),
    ("C02", "C02_phone", "c03_phone", "C02 даёт номер больничного контакта C03"),
    ("C03", "C03_special", "c03_special", "C03: специальные заказы"),
    ("C03", "C03_elite", "c03_elite", "C03: элитные VIP-заказы"),
    ("C03", "C03_final", "c03_final", "C03: финальный VIP-заказ"),
)


@dataclass
class State:
    t: float = 0.0
    cash: float = 0.0
    fun: float = 0.0        # fun budget not yet spent
    fun_next: int = 0       # index of the next FUN_ITEMS entry
    npcs: int = 0
    orders: float = 0.0
    owned: set = field(default_factory=set)
    flags: set = field(default_factory=set)
    trust: Counter = field(default_factory=Counter)
    credit: list = field(default_factory=lambda: [0.0, 0.0])  # special, elite offers
    income: Counter = field(default_factory=Counter)
    spend: Counter = field(default_factory=Counter)
    events: list = field(default_factory=list)              # (minute, text, novelty)
    b06_at: float = None

    def event(self, text, novelty=True):
        self.events.append((self.t, text, novelty))


def level(owned, prefix):
    return sum(f"{prefix}{i}" in owned for i in (1, 2, 3))


def shift(q, p, up=False):
    """Move probability mass one quality tier down (or up) with chance p."""
    out = [x * (1 - p) for x in q]
    for i, x in enumerate(q):
        j = min(i + 1, 4) if up else max(i - 1, 0)
        out[j] += x * p
    return out


def base_for(stage, owned):
    return {"S0": "B01", "S1": "B02", "S2": "B03"}.get(
        stage.sid, ("B04" if "B04" in owned else "B03") if stage.sid == "S3" else "B05")


def has_medical_storage(owned):
    return "fridge2" in owned or "packer" in owned


def sales_time(st, base, speed):
    """Minutes per NPC spent on selling trips (batched by storage)."""
    if "driver" in st.owned:
        return 0.5
    owned = st.owned
    batch = 6 if "packer" in owned else 4 if "fridge2" in owned else 3 if "fridge1" in owned else 1
    c02_trip = 2 * DIST[(base, "P04")] / speed + 2.0
    if "c03" not in st.flags:
        return c02_trip / batch
    c03_trip = 2 * DIST[(base, "P09")] / speed + 2.5
    return c03_trip / batch + c02_trip / (2 * batch)


def quality(district, team, owned, scan):
    spoil = 0.0 if has_medical_storage(owned) else 0.05 if "fridge1" in owned else 0.25
    q = shift(district.quality, 0.15, up=True) if scan else list(district.quality)
    return shift(shift(q, team.drop), spoil)


def sell_organs(st, organs, q, minutes, gross):
    rows = [(o, i, o.count * q[i]) for o in organs for i in range(5) if q[i] > 0]
    frac_e = frac_s = 0.0
    if "c03_special" in st.flags:
        st.credit[0] = min(ORDER_CAP, st.credit[0] + SPECIAL_RATE * minutes / 60)
        if "c03_elite" in st.flags:
            st.credit[1] = min(ORDER_CAP, st.credit[1] + ELITE_RATE * minutes / 60)
        top = sum(n for _, i, n in rows if i >= PERFECT)
        if top > 0:
            avail = top * (0.9 if has_medical_storage(st.owned) else 0.5)
            fill_e = min(st.credit[1], avail)
            fill_s = min(st.credit[0], avail - fill_e)
            st.credit[1] -= fill_e
            st.credit[0] -= fill_s
            frac_e, frac_s = fill_e / top, fill_s / top
            st.orders += fill_e + fill_s
            st.trust["C03"] += SPECIAL_TRUST * (fill_e + fill_s)
    bonus = 1 + C02_ORDER_BONUS if "c02_orders" in st.flags else 1.0
    for organ, i, n in rows:
        value = organ.price * Q_PRICE[i]
        if i >= PERFECT and (frac_e or frac_s):
            gross["C03: спецзаказы"] += n * value * C03_FACTOR * (
                frac_e * ELITE_MULT + frac_s * SPECIAL_MULT)
            st.trust["C03"] += n * (frac_e + frac_s) * Q_TRUST[i]
            n *= 1 - frac_e - frac_s
        if "c03" in st.flags and i >= GOOD:
            gross["C03: обычные"] += n * value * C03_FACTOR
            st.trust["C03"] += n * Q_TRUST[i]
        else:
            gross["C02"] += n * value * bonus
            st.trust["C02"] += n * Q_TRUST[i]
    if "first_order" not in st.flags:
        st.flags.add("first_order")
        gross["C02: первый заказ"] += FIRST_ORDER_CASH
        st.trust["C02"] += FIRST_ORDER_TRUST
        st.event("первая процедура в B02, первый заказ C02 закрыт")


def cycle(st, stage, team, pace):
    """One NPC: hunt, transport, procedure, sales. Advances time and money."""
    owned = st.owned
    blood_only = "c02" not in st.flags
    district = DISTRICTS["village" if blood_only else stage.hunt]
    base = base_for(stage, owned)
    speed = SPEED + ENGINE_STEP * level(owned, "engine")
    scan = "scanner" in owned and stage.hunt in ("old", "elite") and not blood_only
    hunt = (district.find * team.find * (0.8 if scan else 1.0)
            + (district.capture + district.carry) * team.grab)
    organs = [] if blood_only else [o for o in ORGANS if all(n in owned for n in o.needs)]
    if organs:
        drive = 2 * DIST[(base, stage.hunt)] / speed
        ops = OP_PER_ORGAN * len(organs) * (0.3 if "surgeon" in owned else 1.0)
        chores = (UNLOAD + CALM[level(owned, "anest")] + ops + BLOOD_DRAW + C01_VISIT
                  + (0.0 if "packer" in owned else PACKING)
                  + (0.0 if "cleaner" in owned else DISPOSAL))
        sales = sales_time(st, base, speed)
    else:
        drive, sales, chores = 0.0, 0.0, PROLOGUE_CHORES
    chores *= 1 - team.overlap
    van_bonus = 0.05 * ("tint" in owned) + 0.01 * (level(owned, "brakes") + level(owned, "handling"))
    overhead = max(0.0, team.overhead + district.risk - van_bonus) * PACE[pace]
    minutes = (hunt + drive + chores + sales) * (1 + overhead)
    st.t += minutes
    st.npcs += 1

    gross = Counter({"C01: кровь": BAGS_PER_NPC * BAG_PRICE})
    st.trust["C01"] += BAGS_PER_NPC
    if organs:
        sell_organs(st, organs, quality(district, team, owned, scan), minutes, gross)
    total = sum(gross.values())
    loss = total * (LOSS_HIDDEN if "hidden" in owned else LOSS)
    fun = (total - loss) * (0.0 if stage.sid in ("S0", "S1") else FUN_SHARE)
    bags = BAGS_PER_NPC * BAG_COST
    st.income.update(gross)
    st.spend.update({"потери": loss, "пакеты": bags})
    st.fun += fun
    st.cash += total - loss - fun - bags


def check_unlocks(st):
    for buyer, key, flag, text in UNLOCKS:
        if flag not in st.flags and st.trust[buyer] >= TRUST[key]:
            st.flags.add(flag)
            st.event(text)


def shop(st, queue):
    while queue:
        key = queue[0]
        name, price, category = ITEMS[key]
        if key not in st.owned:
            if st.cash < price:
                return
            st.cash -= price
            st.spend[category] += price
            st.owned.add(key)
            st.event(f"куплено: {name} (${ru(price)})")
            if key == "van":
                st.t += GRANDPA_BEAT
        queue.pop(0)


def buy_fun(st):
    while st.fun_next < len(FUN_ITEMS) and st.fun >= FUN_ITEMS[st.fun_next][1]:
        name, price = FUN_ITEMS[st.fun_next]
        st.fun -= price
        st.fun_next += 1
        st.spend["весёлые покупки"] += price
        st.event(f"весёлая покупка: {name} (${ru(price)})")


def gate_met(st, stage):
    if stage.gate[0] == "item":
        return stage.gate[1] in st.owned
    return st.trust[stage.gate[1]] >= TRUST[stage.gate[2]]


@dataclass
class StageResult:
    stage: Stage
    minutes: float
    end: float
    npcs: int
    income: float
    bought: list


def run(players, pace="normal", kill_grandpa=False):
    team, st, results, queue = TEAMS[players], State(), [], []
    for stage in STAGES:
        t0, n0, inc0, own0 = st.t, st.npcs, sum(st.income.values()), set(st.owned)
        queue += stage.shop          # unbought items of the previous stage stay first
        if stage.sid == "S0":
            st.cash += FIRST_C01_PAYMENT
            st.income["C01: кровь"] += FIRST_C01_PAYMENT
            st.t += stage.intro
            st.event("вводная сделка C01, первые пакеты", novelty=False)
            if kill_grandpa:
                st.owned.add("van")
                st.event("бусик забран у деда силой")
                st.t += GRANDPA_BEAT + KILL_EXTRA_REPAIR
        elif stage.sid == "S1":
            while st.trust["C01"] < TRUST["C01_hint"]:   # C01 must know the team first
                cycle(st, stage, team, pace)
            st.t += stage.intro
            st.flags.add("c02")
            st.event("контакт C02 на приёмке P04; хижина B02 занята")
        else:
            st.t += stage.intro
            if stage.sid == "S3":
                st.flags.add("c03")
            st.event(f"{stage.sid}: {stage.beats}")
        shop(st, queue)
        while not gate_met(st, stage):
            cycle(st, stage, team, pace)
            check_unlocks(st)
            shop(st, queue)
            buy_fun(st)
            if st.b06_at is None and st.cash >= B06_PRICE:
                st.b06_at = st.t
            if st.t > 100 * 60:
                raise RuntimeError(f"{stage.sid} never ends: check prices and thresholds")
        if stage.sid == "S5":
            st.t += FINAL_PLAN + FINAL_CAPTURE * team.grab
            st.event("финальный VIP-заказ выполнен")
        bought = [ITEMS[k][0] for k in ITEMS if k in st.owned - own0]
        results.append(StageResult(stage, st.t - t0, st.t, st.npcs - n0,
                                   sum(st.income.values()) - inc0, bought))
    return st, results


# ------------------------------------------------------------------- reports
def ru(x, digits=0):
    """Russian number format, as in the draft document: 12 345,6."""
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",")


def hm(minutes):
    m = int(round(minutes))
    return f"{m // 60}:{m % 60:02d}"


def b06_note(st, results):
    """When the optional B06 becomes affordable: during the story or after the finale."""
    if st.b06_at is not None:
        return hm(st.b06_at)
    last = results[-1]
    net_per_hour = last.income * (1 - LOSS_HIDDEN - FUN_SHARE) / (last.minutes / 60)
    return f"~{ru((B06_PRICE - st.cash) / net_per_hour, 1)} ч игры после финала"


def novelty_gap(st):
    times = [0.0] + sorted(t for t, _, novelty in st.events if novelty)
    gaps = [(b - a, a) for a, b in zip(times, times[1:])]
    return max(gaps) if gaps else (0.0, 0.0)


def npc_value(district_key, players, organ_keys, with_c03):
    """Expected $ and trust per NPC (blood + organs), no special orders, medical fridge."""
    st = State(owned={"fridge2"}, flags={"first_order"} | ({"c03"} if with_c03 else set()))
    organs = [o for o in ORGANS if o.key in organ_keys]
    gross = Counter({"blood": BAGS_PER_NPC * (BAG_PRICE - BAG_COST)})
    sell_organs(st, organs, quality(DISTRICTS[district_key], TEAMS[players], st.owned, False),
                0.0, gross)
    return sum(gross.values()), st.trust["C02"], st.trust["C03"]


def print_tables(pace, players_list):
    print(f"VOLUNTEERS ONLY: симуляция экономики и темпа. ЧЕРНОВИК, НЕ УТВЕРЖДЕНО. Темп: {pace}")
    print("\nОсновная история, часы (быстрый / обычный / медленный темп):")
    for p in (1, 2, 3, 4):
        hours = [run(p, pc)[0].t / 60 for pc in ("fast", "normal", "slow")]
        print(f"  {p} игр.: " + " / ".join(f"{ru(h, 1):>4}" for h in hours))
    for p in players_list:
        st, results = run(p, pace)
        print(f"\n{p} игр., темп {pace}: этапы")
        print(f"  {'этап':4} {'мин':>4} {'к концу':>7} {'NPC':>4} {'NPC/ч':>5} {'выручка $':>9} "
              f"{'$/ч':>7}  цель 2-3 игр.")
        for r in results:
            rate = 60 / r.minutes
            lo, hi = r.stage.target
            print(f"  {r.stage.sid:4} {r.minutes:4.0f} {hm(r.end):>7} {r.npcs:4d} "
                  f"{ru(r.npcs * rate, 1):>5} {ru(r.income):>9} {ru(r.income * rate):>7}  "
                  f"{lo}-{hi}  {r.stage.title}")
        gap, at = novelty_gap(st)
        print(f"  итого {hm(st.t)} ч, NPC {st.npcs}, спецзаказов {st.orders:.0f}, "
              f"макс. пауза без новинок {gap:.0f} мин (с {hm(at)}), "
              f"B06 по деньгам: {b06_note(st, results)}")


def print_details(players, pace):
    st, results = run(players, pace)
    print(f"\n{players} игр., темп {pace}: покупки по этапам")
    for r in results:
        print(f"  {r.stage.sid}: " + (", ".join(r.bought) if r.bought else "-"))
    total = sum(st.income.values())
    print("\nВыручка за игру:")
    for k, v in st.income.most_common():
        print(f"  {k:18} ${ru(v):>9}  {ru(100 * v / total, 1):>4}%")
    print("Расходы за игру:")
    for k, v in st.spend.most_common():
        print(f"  {k:18} ${ru(v):>9}")
    print(f"  {'остаток на руках':18} ${ru(st.cash):>9}")
    kill_st, _ = run(players, pace, kill_grandpa=True)

    def first(state, marker):
        return next(t for t, text, _ in state.events if marker in text)
    print(f"\nВетка с дедом: бусик мирно {first(st, 'бусик деда') + GRANDPA_BEAT:.0f} мин / "
          f"силой {first(kill_st, 'силой') + GRANDPA_BEAT + KILL_EXTRA_REPAIR:.0f} мин; "
          f"контакт C02 мирно {first(st, 'контакт C02'):.0f} мин / "
          f"силой {first(kill_st, 'контакт C02'):.0f} мин")
    keys = ("kidney", "liver", "lungs", "heart", "eyes")
    names = ", ".join(o.name for o in ORGANS if o.key in keys)
    print(f"\nОдин NPC без спецзаказов (кровь + {names}):")
    for d in ("bad", "old", "elite"):
        v02, t02, _ = npc_value(d, players, keys, False)
        v03, t02b, t03 = npc_value(d, players, keys, True)
        print(f"  {DISTRICTS[d].name:13} всё в C02: ${ru(v02):>6}, доверие C02 +{ru(t02, 1):>4} | "
              f"с C03: ${ru(v03):>6}, доверие C03 +{ru(t03, 1):>4}, C02 +{ru(t02b, 1):>4}")


def print_log(players, pace):
    st, _ = run(players, pace)
    print(f"\nХронология, {players} игр., темп {pace}:")
    for t, text, _ in st.events:
        print(f"  {hm(t):>6}  {text}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--players", type=int, choices=(1, 2, 3, 4))
    parser.add_argument("--pace", choices=tuple(PACE), default="normal")
    parser.add_argument("--log", action="store_true", help="print the event timeline")
    args = parser.parse_args()
    players_list = (args.players,) if args.players else (1, 2, 3, 4)
    print_tables(args.pace, players_list)
    print_details(args.players or 2, args.pace)
    if args.log:
        print_log(args.players or 2, args.pace)


if __name__ == "__main__":
    main()
