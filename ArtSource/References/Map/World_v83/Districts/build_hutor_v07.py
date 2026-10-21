"""Хутор v07 (TASK-000851, Вадим 20.10.2026: «нормально по природе соедини, а то как будто картинка на картинку наложена»;
«поля ровнее, чуть поменьше»; дома у леса и у горы): раскладка HAMLET_LAYOUT_v06.json; фон картинки полностью прозрачный
(под Хутором видна сама карта — без подложки и края), поля с бороздами (пашня/стерня).
Ранее v06 (TASK-000840/841, Вадим 20.10.2026): раскладка HAMLET_LAYOUT_v05.json — улицы и дома с участками по плану Феди v19,
наши объекты v04 (церковь, база, площадь, кладбище, сад, свинарник, рыбаки), всё налезающее убрано. Стиль как v05.
Ранее v05 (TASK-000828, Вадим 18.10.2026: «текстуры друг на друга наложены», дороги в никуда): как v04, но без подложки
старой карты v11 (вне границы Хутора — прозрачно, на общей карте видна текущая карта), без полупрозрачных пятен рельефа,
без проводов между столбами и линии дренажа; фон внутри — цвет луга текущей карты с мягким краем; концы грунтовок скруглены
и упираются в место (дом, площадку, поле, дорогу). Также пишет ../00_Сборка_общей_карты/v75_assets/hamlet_v05_world.png (5 px/м).
Ранее v04 (TASK-000550): renders HAMLET_LAYOUT_v04.json (GPT v03 with Vadim edits: no barn/shop/obelisk/transformer, a village square) (Working/Reviews/Hamlet_2026-10-14)
as a top-down plan over the approved world map v11, in the flat style of the map. 1 px = 0.1 m. Never overwrites.

  python build_hutor_v04.py   -> Хутор_v04.png (+ Легенда_v04.txt)
"""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
GAME = Path(r'C:\Users\chern_0eqkb03\Desktop\GAME')
WORLD = GAME / r'ArtSource\References\Map\World_v11'
SPEC = GAME / r'Working\Reviews\Hamlet_2026-10-14\HAMLET_LAYOUT_v06.json'
OUT_PNG, OUT_LEG = HERE / 'Хутор_v07.png', HERE / 'Легенда_v07.txt'
OUT_WORLD = HERE.parent / '00_Сборка_общей_карты' / 'v83_assets' / 'hamlet_v07_world.png'
for p in (OUT_PNG, OUT_LEG, OUT_WORLD):
    if p.exists():
        raise SystemExit(f'{p.name} exists')
W = json.load(open(WORLD / 'WORLD_MAP_v11.json', encoding='utf-8'))
L = json.load(open(SPEC, encoding='utf-8'))
X0, X1, Y0, Y1 = 118.0, 442.0, 355.0, 618.0
S = 10.0

Image.MAX_IMAGE_PIXELS = None
big = Image.open(WORLD / 'VOLUNTEERS_MAP_v11_FINAL.png').convert('RGB')
H = big.height
crop = big.crop((int(X0 / 0.2), int(H - Y1 / 0.2), int(X1 / 0.2), int(H - Y0 / 0.2)))
img = Image.new('RGBA', (int((X1 - X0) * S), int((Y1 - Y0) * S)), (226, 235, 210, 0))   # v05: без подложки старой карты (цвет луга, прозрачно)
dr = ImageDraw.Draw(img, 'RGBA')


def PX(p):
    return ((p[0] - X0) * S, (Y1 - p[1]) * S)


bg = (226, 235, 210, 255)                                            # v05: цвет луга текущей карты
interior = [(150, 377), (372, 377), (372, 596), (182, 600), (176, 586), (156, 576), (146, 540), (146, 440)]
from PIL import ImageFilter
_m = Image.new('L', img.size, 0)
ImageDraw.Draw(_m).polygon([PX(p) for p in interior], fill=255)
_m = _m.filter(ImageFilter.GaussianBlur(25))                            # мягкий край ~2,5 м
pass                                                                # v07: фон полностью прозрачный — под Хутором сама карта
dr = ImageDraw.Draw(img, 'RGBA')
# soft terrain shading (rises and dips), drawn first
for t in []:                                                           # v05: пятен рельефа нет (рельеф — в 3D)
    if t.get('polygon_m'):
        h = t.get('height_delta_m') or 0
        col = (196, 212, 170, 60) if h >= 0 else (170, 196, 176, 60)
        xs = [q[0] for q in t['polygon_m']]; ys = [q[1] for q in t['polygon_m']]
        dr.ellipse([PX((min(xs), max(ys))), PX((max(xs), min(ys)))], fill=col)

STYLE = {  # kind: (layer, fill, outline)
    'yard': (0, (219, 230, 199), None),
    'cultivated_field': (0, (214, 196, 140), (170, 150, 100)), 'vegetable_garden': (0, (206, 222, 180), (170, 196, 146)),
    'open_working_grass': (0, (222, 232, 200), None), 'overgrown_beds': (0, (196, 210, 168), (170, 186, 140)),
    'mud_patch': (0, (176, 152, 118), None), 'wheel_rut': (0, (166, 142, 108), None), 'dung_patch': (0, (150, 128, 96), None),
    'village_square': (0, (226, 214, 190), (176, 160, 130)), 'meeting_forecourt': (0, (218, 210, 196), (170, 160, 146)), 'manoeuvring_apron': (0, (224, 212, 186), (170, 150, 120)),
    'van_loading_pad': (0, (228, 216, 190), (150, 130, 100)), 'cemetery': (0, (214, 220, 200), (110, 110, 110)),
    'orchard': (0, (214, 228, 190), (180, 200, 160)), 'pond': (0, (168, 212, 228), (120, 170, 196)),
    'small_pig_pen': (0, (214, 196, 168), (140, 110, 80)), 'pedestrian_path': (0, None, None),
    'tree': (1, (118, 164, 104), (90, 136, 80)), 'soft_shrub_cluster': (1, (128, 176, 108), (96, 140, 86)),
    'reed_clump': (1, (160, 190, 120), (130, 160, 100)),
    'church': (3, (214, 208, 226), (70, 60, 70)), 'grandfather_base': (3, (176, 196, 186), (60, 70, 70)),
    'house': (3, (206, 178, 150), (70, 60, 50)), 'communal_barn': (3, (160, 128, 108), (70, 60, 50)),
    'village_shop': (3, (222, 170, 150), (70, 60, 50)), 'water_tower': (3, (176, 188, 200), (70, 80, 90)),
    'hay_shelter': (2, (200, 178, 120), (90, 80, 60)), 'shed': (2, (178, 142, 102), (80, 60, 40)),
    'chicken_coop': (2, (196, 160, 118), (80, 60, 40)), 'pig_shelter': (2, (170, 130, 100), (80, 60, 40)),
    'round_hay_bale': (2, (232, 196, 110), (170, 140, 70)), 'haystack': (2, (228, 196, 110), (170, 140, 70)),
    'parked_tractor': (2, (200, 60, 50), (90, 40, 30)), 'farm_trailer': (2, (120, 140, 120), (60, 70, 60)),
    'rusted_car': (2, (150, 110, 90), (80, 60, 50)), 'bus_stop': (2, (120, 150, 170), (60, 70, 80)),
    'transformer_box': (2, (150, 160, 150), (70, 80, 70)), 'obelisk': (2, (200, 196, 190), (90, 90, 90)),
    'old_well': (2, (150, 170, 190), (90, 100, 110)), 'grave': (2, (180, 176, 168), (110, 110, 110)),
    'fishing_platform': (2, (178, 142, 102), (90, 70, 50)), 'upturned_boat': (2, (90, 130, 170), (50, 70, 90)),
    'fishing_nets': (2, (90, 110, 120), None), 'net_drying_rack': (2, (120, 100, 80), None),
    'gathering_table': (2, (150, 112, 76), (80, 60, 40)), 'bench': (2, (170, 130, 90), (80, 60, 40)),
    'wooden_utility_pole': (4, (60, 48, 40), None), 'pole_lamp': (4, (240, 210, 90), (90, 70, 40)),
}
DEFAULT_SMALL = (2, (176, 150, 116), (100, 84, 64))
objs = sorted(L['objects'], key=lambda o: 0 if o['kind'] in ('yard', 'open_working_grass') else 1)
for layer in range(5):
    if layer == 1:                                                    # v07: борозды на полях (пашня темнее, стерня светлее)
        for o in objs:
            if o['kind'] == 'cultivated_field' and o.get('field_type'):
                xs = [p[0] for p in o['polygon_m']]; ys = [p[1] for p in o['polygon_m']]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if o['field_type'] == 'plowed':
                    dr.polygon([PX(p) for p in o['polygon_m']], fill=(170, 140, 104), outline=(130, 106, 76))
                    col = (140, 112, 80)
                else:
                    col = (190, 170, 112)
                st_ = o.get('furrow_step_m', 2.5)
                yy = y0 + st_ / 2
                while yy < y1:
                    dr.line([PX((x0 + 0.6, yy)), PX((x1 - 0.6, yy))], fill=col, width=4)
                    yy += st_
                dr.polygon([PX(p) for p in o['polygon_m']], outline=(150, 160, 110), width=5)   # межа с травой
        for st in L['streets']:                                       # streets between ground and trees
            dr.line([PX(p) for p in st['polyline_m']], fill=(230, 208, 164), width=int(st['width_m'] * S), joint='curve')
            for e in (st['polyline_m'][0], st['polyline_m'][-1]):        # v05: скруглённые концы
                ex, ey = PX(e); rr = st['width_m'] * S / 2
                dr.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=(230, 208, 164))
        for dn in []:                                                  # v05: линии дренажа нет
            pts = dn['polyline_m']
            dr.line([PX(p) for p in pts], fill=(120, 160, 150), width=3)
        for pa in L.get('pedestrian_access', []):
            dr.line([PX(p) for p in pa['polyline_m']], fill=(216, 200, 170), width=int(pa.get('width_m', 1.5) * S))
        for o in objs:
            if o['kind'] == 'pedestrian_path' and o.get('polyline_m'):
                pts = o['polyline_m']
                for a, b in zip(pts, pts[1:]):
                    n = max(1, int(math.dist(a, b) / 1.5))
                    for k in range(0, n, 2):
                        p0 = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                        p1 = (a[0] + (b[0] - a[0]) * (k + 1) / n, a[1] + (b[1] - a[1]) * (k + 1) / n)
                        dr.line([PX(p0), PX(p1)], fill=(216, 200, 170), width=12)   # v05: тропа, не синий пунктир
    if layer == 1:                                                    # tree crowns from crown_diameter_m (the polygon is the trunk)
        TCOL = {'shade': ((112, 160, 98), (84, 128, 74)), 'fruit': ((150, 196, 120), (110, 150, 90)),
                'birch': ((176, 210, 150), (130, 170, 110)), 'willow': ((140, 182, 122), (100, 146, 90))}
        for o in sorted((q for q in objs if q['kind'] == 'tree'), key=lambda q: -q.get('crown_diameter_m', 4)):
            r = o.get('crown_diameter_m', 4.0) / 2
            f, ol = TCOL.get(o.get('tree_type'), ((118, 164, 104), (90, 136, 80)))
            x, y = PX(o['centre_m'])
            dr.ellipse([x - r * S, y - r * S, x + r * S, y + r * S], fill=f, outline=ol, width=2)
        for o in (q for q in objs if q['kind'] == 'soft_shrub_cluster'):
            w, l = o['size_m']; x, y = PX(o['centre_m'])
            dr.ellipse([x - w * S * 0.7, y - l * S * 0.7, x + w * S * 0.7, y + l * S * 0.7], fill=(128, 176, 108), outline=(96, 140, 86))
    for o in objs:
        if o['kind'] in ('tree', 'soft_shrub_cluster'):
            continue
        lay, fill, out = STYLE.get(o['kind'], DEFAULT_SMALL)
        if lay != layer or not o.get('polygon_m') or fill is None:
            continue
        if o['kind'].endswith('spawn_marker') or o['kind'] == 'npc_gathering_marker':
            continue
        dr.polygon([PX(p) for p in o['polygon_m']], fill=fill, outline=out, width=2 if lay == 3 else 1)
    if layer == 3:                                                    # wires above the roofs, then poles on top
        ids = {o['id']: o for o in objs}
        for w in []:                                                   # v05: проводов нет
            a, b = ids.get(w['from_id']), ids.get(w['to_id'])
            if a and b:
                dr.line([PX(a['centre_m']), PX(b['centre_m'])], fill=(70, 70, 76), width=2)
# animals as small dots
for o in objs:
    if o['kind'] in ('chicken_spawn_marker', 'pig_spawn_marker'):
        x, y = PX(o['centre_m'])
        col = (250, 250, 246) if 'chicken' in o['kind'] else (236, 170, 170)
        for dx, dy in ((-6, 0), (5, -4), (3, 6)):
            dr.ellipse([x + dx - 4, y + dy - 4, x + dx + 4, y + dy + 4], fill=col, outline=(90, 80, 70))
for o in objs:                                                         # NPC idle spots on the square
    if o['kind'] == 'npc_gathering_marker':
        x, y = PX(o['centre_m'])
        dr.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(120, 90, 200), outline=(255, 255, 255), width=2)
# numbers on the anchors and places
font = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 26)
NUM = [('grandfather_base', 'Хижина деда — база 2'), ('church', 'Церковь'), ('village_square', 'Площадь: стол под большим деревом, лавки, сюда сходятся NPC (фиолетовые точки)'),
       ('cemetery', 'Кладбище'),
       ('water_tower', 'Водонапорная башня'), ('old_well', 'Старый колодец'), ('pond', 'Пруд'), ('orchard', 'Небольшой старый сад'),
       ('small_pig_pen', 'Свинарник'), ('bus_stop', 'Автобусная остановка'),
       ('fishing_platform', 'Рыбацкое место за асфальтом'), ('rusted_car', 'Заброшенный двор: ржавая машина'),
       ('hay_shelter', 'Навес для сена')]
legend = []
n = 0
for kind, text in NUM:
    o = next((q for q in objs if q['kind'] == kind), None)
    if o is None:
        continue
    n += 1
    c = o.get('centre_m') or [sum(q[0] for q in o['polygon_m']) / len(o['polygon_m']), sum(q[1] for q in o['polygon_m']) / len(o['polygon_m'])]
    x, y = PX(c)
    dr.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(40, 52, 70), outline=(255, 255, 255), width=3)
    dr.text((x, y), str(n), fill=(255, 255, 255), font=font, anchor='mm')
    legend.append(f'{n:02d} — {text}.')
for o in objs:                                                         # house ids, small
    if o['kind'] == 'house':
        x, y = PX(o['centre_m'])
        dr.text((x, y), o['id'].split('-')[-1], fill=(60, 40, 30), font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20), anchor='mm')
img.save(OUT_PNG)
OUT_WORLD.parent.mkdir(exist_ok=True)
img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(OUT_WORLD)
from collections import Counter
c = Counter(o['kind'] for o in objs)
with open(OUT_LEG, 'w', encoding='utf-8-sig') as f:
    f.write('ХУТОР v07 — как v06 + поля меньше и ровнее (с бороздами), +3 дома у леса, +2 у горы; фон прозрачный (без подложки)\n')
    f.write('\n'.join(legend) + '\n\n')
    f.write(f"Домов: {c['house']} (по плану Феди; H19 заброшен) + хижина деда. Деревьев {c['tree']}, кустов {c['soft_shrub_cluster']}, "
            f"столбов {c['wooden_utility_pole']} с фонарями {c['pole_lamp']}, рулонов сена {c['round_hay_bale']}, огородов {c['vegetable_garden']}.\n")
    f.write('Куры — белые точки, свиньи — розовые. Рельеф (бугры, низины) на плане не рисуется — он в 3D.\n')
print('ok', dict(c))
