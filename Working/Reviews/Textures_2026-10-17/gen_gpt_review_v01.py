"""Лист проверки текстур от GPT (TASK-000825): как 22 новые текстуры выглядят «в деле» — дома с фасадами (вид в лоб),
улица сверху (разметка, износ, люки рядом с нашими асфальтом и тротуаром), остальные — плитками в своём окружении.
Запуск: python -I gen_gpt_review_v01.py <папка gpt_missing_v02_2026-10-18>. Только читает PNG/JSON. PIL без numpy."""
import json
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

GPT = os.path.abspath(sys.argv[1])
TX = os.path.join(GPT, 'Textures')
HERE = os.path.dirname(os.path.abspath(__file__))
A = r'C:\Users\chern_0eqkb03\Desktop\GAME\Assets\OnlyVolunteers\Art'
SK = A + r'\StyleKit_v3\Textures'
D = A + r'\Map\Textures\Detail'
RF = A + r'\Map\Textures\roofs'
ASPH = os.path.join(HERE, 'candidates_asphalt_v01', '2a_asphalt_v07_A5d12_albedo.png')
S1 = os.path.join(HERE, 'candidates_paving_v01', 'S1_sidewalk_oar_1p5m_albedo.png')
M3 = os.path.join(HERE, 'candidates_paving_v01', 'M3_plaza_1m_granite_bands_albedo.png')
UV = json.load(open(os.path.join(GPT, 'ATLAS_UV.json'), encoding='utf-8'))
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
FB = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 15)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 13)
_cache = {}


def img(path):
    if path not in _cache:
        _cache[path] = Image.open(path).convert('RGBA')
    return _cache[path]


def gpt(name):
    return img(os.path.join(TX, name + '.png'))


def tile_area(src, tile_w_m, tile_h_m, w_px, h_px, ppm, tint=None):
    t = src.resize((max(1, round(tile_w_m * ppm)), max(1, round(tile_h_m * ppm))), Image.LANCZOS)
    if tint:
        r_, g_, b_, a_ = t.split()
        t = Image.merge('RGBA', (r_.point(lambda v: int(v * tint[0])), g_.point(lambda v: int(v * tint[1])),
                                 b_.point(lambda v: int(v * tint[2])), a_))
    out = Image.new('RGBA', (w_px, h_px))
    for x in range(0, w_px, t.width):
        for y in range(0, h_px, t.height):
            out.paste(t, (x, y))
    return out


def element(atlas, name):
    for e in UV[atlas]['elements']:
        if e['element'] == name:
            x0, y0, x1, y1 = e['content_px']
            return gpt(atlas).crop((x0, y0, x1, y1)), e.get('nominal_metres')
    raise KeyError(name)


def put(canvas, atlas, name, cx_m, cy_m, ppm, rot=0, size_m=None):
    el, nom = element(atlas, name)
    w_m, h_m = size_m or nom
    el = el.resize((max(1, round(w_m * ppm)), max(1, round(h_m * ppm))), Image.LANCZOS)
    if rot:
        el = el.rotate(rot, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(el, (int(cx_m * ppm - el.width / 2), int(cy_m * ppm - el.height / 2)))


# ---------------------------------------------------------------- 1) дома, вид в лоб (18 px/м)
PB = 18


def building(parts, width_bays, bay_w=3.5):
    """parts: снизу вверх [(тайл, высота этажа м, число этажей, оттенок)]; возвращает RGBA."""
    w = round(width_bays * bay_w * PB)
    h = sum(round(fh * PB) * n for _, fh, n, _ in parts)
    out = Image.new('RGBA', (w, h))
    y = h
    for tex, fh, n, tint in parts:
        hh = round(fh * PB) * n
        y -= hh
        out.alpha_composite(tile_area(tex, bay_w, fh, w, hh, PB, tint), (0, y))
    return out


def trim_band(part, w_px, h_m):
    """Полоса из FacadeTrim: part='top' (карниз+тяга, верхние 35 %) или 'bottom' (цоколь, нижние 25 %)."""
    t = gpt('FacadeTrim')
    crop = t.crop((0, 0, t.width, int(t.height * 0.35))) if part == 'top' else t.crop((0, int(t.height * 0.75), t.width, t.height))
    return tile_area(crop, 2.0, h_m, w_px, round(h_m * PB), PB)


CREAM, PEACH, WHITE = (1.0, 0.93, 0.80), (1.0, 0.86, 0.76), (1.03, 1.03, 1.02)
blds = []
b = building([(gpt('Facade_DT_shop'), 4.0, 1, None), (gpt('Facade_DT_plaster'), 3.5, 4, CREAM)], 5)
c = trim_band('top', b.width, 0.9)
x = Image.new('RGBA', (b.width, b.height + c.height))
x.alpha_composite(c, (0, 0))
x.alpha_composite(b, (0, c.height))
aw = Image.new('RGBA', (round(3.5 * PB), round(1.0 * PB)))                     # маркиза над одной витриной
aw.alpha_composite(tile_area(gpt('Fabric_red'), 1.2, 1.2, aw.width, aw.height, PB), (0, 0))
x.alpha_composite(aw, (round(3.5 * PB), x.height - round(4.0 * PB) + 2))
blds.append((x, '2а штукатурка (кремовая — цвет в материале) + 2в витрины + 4 карниз + 9 маркиза'))
b = building([(gpt('Facade_DT_shop'), 4.0, 1, None), (gpt('Facade_DT_brick'), 3.5, 3, None)], 4)
c = trim_band('top', b.width, 0.9)
x = Image.new('RGBA', (b.width, b.height + c.height))
x.alpha_composite(c, (0, 0))
x.alpha_composite(b, (0, c.height))
blds.append((x, '2б кирпич + витрины'))
blds.append((building([(gpt('TowerGlass'), 3.5, 9, None)], 3), '3 стекло башен (кусок)'))
b = building([(gpt('Facade_Hamlet_wood'), 3.0, 2, None)], 3, bay_w=3.0)
roof_h = round(3.2 * PB)
x = Image.new('RGBA', (b.width + 16, b.height + roof_h))
roof = tile_area(img(RF + r'\roof_slate_wavy_albedo.png'), 2.0, 2.0, x.width, roof_h, PB)
mask = Image.new('L', roof.size, 0)
ImageDraw.Draw(mask).polygon([(0, roof_h), (x.width, roof_h), (x.width // 2, 0)], fill=255)
x.paste(roof, (0, 0), mask)
x.alpha_composite(b, (8, roof_h))
blds.append((x, '2г Хутор, доски (+ наш шифер)'))
b = building([(gpt('Facade_Elite_villa'), 3.5, 2, None)], 4)
c = trim_band('top', b.width, 0.6)
x = Image.new('RGBA', (b.width, b.height + c.height))
x.alpha_composite(c, (0, 0))
x.alpha_composite(b, (0, c.height))
blds.append((x, '2д вилла Элит'))
blds.append((building([(gpt('Facade_Warehouse'), 3.5, 2, None)], 6), '2е склад (порт, стройка)'))

# ---------------------------------------------------------------- 2) улица сверху (14 px/м)
PS = 14
SW_M, SH_M = 56.0, 22.0
street = tile_area(img(S1), 3.0, 3.0, round(SW_M * PS), round(SH_M * PS), PS)
road_y0, road_y1 = 4.8, 17.1
road = tile_area(img(ASPH), 4.0, 4.0, street.width, round((road_y1 - road_y0) * PS), PS)
street.alpha_composite(road, (0, round(road_y0 * PS)))
sd = ImageDraw.Draw(street)
for yy in (4.5, 17.1):                                                           # бордюры
    sd.rectangle((0, round(yy * PS), street.width, round((yy + 0.3) * PS)), fill=(206, 205, 198, 255))
for xx in range(0, 56, 4):                                                       # осевая двойная жёлтая
    put(street, 'RoadMarks', 'yellow_double_solid', xx + 2, 10.95, PS)
for yy in (7.3, 14.6):                                                           # белые края полос у парковки
    for xx in range(0, 56, 4):
        if not (28 <= xx < 36):
            put(street, 'RoadMarks', 'white_solid', xx + 2, yy, PS, rot=90)
put(street, 'RoadMarks', 'zebra', 31.5, 10.95, PS, rot=90, size_m=(7.3, 3.0))  # переход поперёк дороги
put(street, 'RoadMarks', 'stop_line', 28.8, 12.85, PS, rot=90)
put(street, 'RoadMarks', 'stop_line', 34.2, 9.05, PS, rot=90)
put(street, 'RoadMarks', 'arrow_straight_right', 24.0, 12.85, PS, rot=-90)
put(street, 'RoadMarks', 'arrow_left', 39.0, 9.05, PS, rot=90)
for k, xx in enumerate((3.0, 8.2, 13.4, 18.6)):                                 # парковочные места + P
    put(street, 'RoadMarks', 'parking_bay', xx + 2.5, 6.05, PS, rot=90, size_m=(2.5, 5.0))
put(street, 'RoadMarks', 'letter_P', 10.7, 6.05, PS, rot=90, size_m=(1.0, 1.4))
put(street, 'RoadWear', 'cracks_1', 9.0, 9.0, PS)
put(street, 'RoadWear', 'cracks_3', 46.0, 12.6, PS)
put(street, 'RoadWear', 'asphalt_patch_1', 41.0, 9.4, PS)
put(street, 'RoadWear', 'asphalt_patch_2', 15.0, 13.0, PS)
put(street, 'RoadWear', 'oil_under_car', 16.0, 6.1, PS)
put(street, 'RoadWear', 'puddle', 50.0, 15.8, PS)
put(street, 'RoadWear', 'broken_asphalt_edge', 52.0, 5.4, PS)
put(street, 'StreetUtility', 'round_manhole', 20.0, 9.3, PS)
put(street, 'StreetUtility', 'storm_grate', 26.0, 16.7, PS, size_m=(0.8, 0.55))

# ---------------------------------------------------------------- 3) остальное в окружении (ячейки 270 px)
C = 270
cells = []
cells.append((tile_area(gpt('Rock_Macro'), 8.0, 8.0, C, C, C / 16.0), '1 скалы, 16 x 16 м (повтор 8 м)'))
pool = tile_area(img(M3), 1.0, 1.0, C, C, C / 12.0)                            # площадь M3 вокруг, бассейн 8 x 5 м
pw, ph = round(8 * C / 12.0), round(5 * C / 12.0)
p_img = tile_area(gpt('PoolTile'), 1.0, 1.0, pw, ph, C / 12.0)
water = Image.new('RGBA', p_img.size, (56, 191, 227, 95))
p_img.alpha_composite(water)
pool.alpha_composite(p_img, ((C - pw) // 2, (C - ph) // 2))
cells.append((pool, '7 бассейн в площади M3 (под водой)'))
fence = tile_area(img(D + r'\TL_meadow_albedo.png'), 3.0, 3.0, C, C, C / 3.0)
fence.alpha_composite(tile_area(gpt('FenceNet'), 1.0, 1.0, C, C, C / 3.0))
cells.append((fence, '8 рабица 3 x 3 м на фоне луга'))
fab = Image.new('RGBA', (C, C), (240, 240, 236, 255))
for k, n in enumerate(('Fabric_blue', 'Fabric_red', 'Fabric_green')):
    t = tile_area(gpt(n), 1.2, 1.2, C - 20, 70, (C - 20) / 3.6)
    fab.alpha_composite(t, (10, 15 + k * 85))
cells.append((fab, '9 маркизы 3,6 м (повтор 1,2 м)'))
fl = Image.new('RGBA', (C, C))
fl.alpha_composite(tile_area(gpt('Field_plowed'), 4.0, 4.0, C // 2, C, C / 12.0), (0, 0))
fl.alpha_composite(tile_area(gpt('Field_stubble'), 4.0, 4.0, C - C // 2, C, C / 12.0), (C // 2, 0))
cells.append((fl, '12 пашня | стерня, 6 x 12 м'))
oil = Image.new('RGBA', (C, C))
oil.alpha_composite(tile_area(img(SK + r'\3c_concrete_panels\3c_concrete_panels_v07_albedo.png'), 4.0, 4.0, C // 2, C, C / 6.0), (0, 0))
oil.alpha_composite(tile_area(img(D + r'\TL_sand_albedo.png'), 8.0, 8.0, C - C // 2, C, C / 6.0), (C // 2, 0))
for k, (n, xm, ym) in enumerate((('tar_spot_1', 1.5, 1.5), ('tar_spot_2', 4.5, 1.8), ('tar_spot_4', 1.4, 4.4), ('tar_spot_5', 4.4, 4.5))):
    put(oil, 'OilTar', n, xm, ym, C / 6.0, size_m=(1.4, 1.2))
cells.append((oil, '10 мазут на бетоне и песке'))
shore = Image.new('RGBA', (C, C))
wr = Image.open(os.path.join(HERE, 'water', 'water_calm_v09_s.png')).convert('RGBA').crop((830, 470, 1200, 675)).resize((C, C))
shore.alpha_composite(wr)
sand = tile_area(img(D + r'\TL_sand_albedo.png'), 8.0, 8.0, C, C // 3, C / 6.0)
shore.alpha_composite(sand, (0, 0))
foam = Image.open(os.path.join(TX, 'WaterFX_shore_foam.png')).convert('L').resize((C, C // 2))
white = Image.new('RGBA', foam.size, (248, 250, 248, 255))
shore.paste(white, (0, C // 3 - C // 4), foam)
cells.append((shore, '11а пена прибоя у кромки (маска)'))
fall = Image.new('RGBA', (C, C), (40, 150, 200, 255))
fm = Image.open(os.path.join(TX, 'WaterFX_waterfall.png')).convert('L').resize((C, C)).point(lambda v: int(v * 0.85))
fall.paste(Image.new('RGBA', (C, C), (240, 248, 250, 255)), (0, 0), fm)
cells.append((fall, '11б струи водопада (маска)'))
signs = Image.new('RGBA', (C, C), (200, 214, 222, 255))
sg = ImageDraw.Draw(signs)
for k, n in enumerate(('sign_STOP', 'sign_pedestrian_crossing', 'sign_parking_P', 'sign_no_entry')):
    xx = 35 + k * 66
    sg.rectangle((xx - 2, 120, xx + 2, C - 10), fill=(110, 112, 110, 255))
    put(signs, 'StreetUtility', n, xx / 60.0, 95 / 60.0, 60.0, size_m=(0.75, 0.75))
put(signs, 'StreetUtility', 'blank_house_number_plate', 1.0, 0.5, 60.0, size_m=(1.0, 0.5))
cells.append((signs, '13 знаки на столбах, табличка дома'))

# ---------------------------------------------------------------- лист
W = 1900
base_y = 40 + 30 + max(b_.height for b_, _ in blds)
H = base_y + 60 + 34 + street.height + 40 + 2 * (C + 52) + 150
sheet = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(sheet)
d.text((10, 10), 'ТЕКСТУРЫ ОТ GPT «В ДЕЛЕ» (18.10): дома с фасадами, улица сверху, остальное в окружении. Номера — как в задании GPT.', font=F, fill=(46, 80, 110))
sky = Image.new('RGB', (W - 20, base_y - 40 + 8), (200, 222, 236))
sheet.paste(sky, (10, 40))
x = 30
for b_, lab in blds:
    sheet.paste(b_, (x, base_y - b_.height), b_)
    for k, ln in enumerate((lab[:44], lab[44:88])):
        if ln:
            d.text((x, base_y + 12 + k * 16), ln, font=fs, fill=(30, 40, 46))
    x += b_.width + 34
d.rectangle((10, base_y, W - 10, base_y + 8), fill=(120, 122, 118))
y = base_y + 60
d.text((10, y), 'Улица сверху, 56 x 22 м: наш асфальт и тротуар S1 + 5 разметка (жёлтая двойная, зебра, стоп, стрелки, парковка, P) + 6 трещины, заплатки, лужа, масло + 13 люк и ливнёвка', font=FB, fill=(30, 40, 46))
y += 26
sheet.paste(street.convert('RGB'), (10, y))
notes = [
    'Проверка Claude: размеры как в задании, швов нет,',
    'у атласов прозрачный фон, элементы не касаются краёв.',
    '',
    'Замечания:',
    '• 11б водопад: у GPT повтор только по X, а наш шейдер',
    '  прокручивает струи вниз — сделал свою бесшовную',
    '  маску в том же стиле (WaterFX_waterfall_v02_tileY).',
    '• 3 стекло башен очень простое (тёмное стекло + рамы)',
    '  — для стилизации норм; если хочешь — попросим блики.',
    '• 2а штукатурка нейтральная: цвет каждого дома',
    '  задаём в материале (на листе — кремовый).',
    '• Совет GPT: рамы, подоконники, карнизы, бордюры —',
    '  геометрией. Согласен: карниз и цоколь (4) берём',
    '  текстурой на эту геометрию.',
]
for k, ln in enumerate(notes):
    d.text((10 + street.width + 30, y + k * 19), ln, font=FB if k in (0, 3) else fs, fill=(30, 40, 46) if k != 3 else (170, 50, 30))
y += street.height + 30
for n, (im_, lab) in enumerate(cells):
    r_, c_ = divmod(n, 6)
    xx = 10 + c_ * (C + 40)
    yy = y + r_ * (C + 52)
    sheet.paste(im_.convert('RGB'), (xx, yy))
    d.text((xx, yy + C + 4), lab, font=fs, fill=(30, 40, 46))
sheet = sheet.crop((0, 0, W, y + 2 * (C + 52) + 10))
out = os.path.join(HERE, 'SHEET_07_gpt_textures_in_context_v01.jpg')
sheet.save(out, quality=90)
print(out, sheet.size)
