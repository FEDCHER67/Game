"""Итоговый лист выбранных текстур (TASK-000811): по одной плитке на выбор, подписи «где применяем», внизу — что ещё сделать."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = r'C:\Users\chern_0eqkb03\Desktop\GAME\Assets\OnlyVolunteers\Art'
SK = A + r'\StyleKit_v3\Textures'
D = A + r'\Map\Textures\Detail'
G = A + r'\Map\Textures\ground'
FA = A + r'\Map\Textures\facades'
RF = A + r'\Map\Textures\roofs'
PR = A + r'\Map\Textures\Props'
C = os.path.join(HERE, 'candidates_paving_v01')
AS = os.path.join(HERE, 'candidates_asphalt_v01')


def sk(d, v):
    return SK + '\\%s\\%s_v%02d_albedo.png' % (d, d, v)


GROUPS = [
    ('Земля (8 слоёв террейна)', [
        (D + r'\TL_meadow_albedo.png', 'L01 Луг', 'meadow'),
        (D + r'\TL_worn_grass_albedo.png', 'L02 Сухая трава', 'Неблагополучный'),
        (sk('1b_dirt_road', 7), 'L03 Грунт', 'грунтовки, тропы'),
        (os.path.join(HERE, 'TL_forest_floor_albedo_v02_brighter.png'), 'L04 Подстилка +10%', 'лес'),
        (D + r'\TL_sand_albedo.png', 'L05 Песок', 'пляж, берега'),
        (sk('1d_gravel', 7), 'L06 Гравий', 'обочины, осыпи'),
        (None, 'L07 Скалы', 'СДЕЛАТЬ Rock_Macro'),
        (D + r'\TL_park_grass_albedo.png', 'L08 Газон', 'парки, виллы'),
    ]),
    ('Дороги и площади', [
        (os.path.join(AS, '2a_asphalt_v07_A5d12_albedo.png'), 'Асфальт −12%', 'все дороги'),
        (sk('2a_asphalt', 1), 'Старый асфальт', 'Неблагоп. + трещины'),
        (os.path.join(C, 'S1_sidewalk_oar_1p5m_albedo.png'), 'Тротуар S1', 'как One-Armed Robber'),
        (os.path.join(C, 'M3_plaza_1m_granite_bands_albedo.png'), 'Площадь M3', 'модерн, гранит'),
        (sk('2c_cobblestone', 7), 'Брусчатка', 'акценты площади'),
        (sk('3c_concrete_panels', 7), 'Бетон', 'плиты, блоки, тоннель'),
        (G + r'\ground_curb_concrete_albedo.png', 'Бордюр', 'бордюры'),
        (G + r'\ground_rubber_playground_albedo.png', 'Резина', 'спортплощадки'),
    ]),
    ('Стены', [
        (sk('3b_plaster_stucco', 1), 'Штукатурка W-1', 'Даунтаун, виллы (цвет — в материале)'),
        (sk('3b_plaster_stucco', 7), 'Штукатурка W-5', 'старые дома'),
        (sk('3a_brick', 7), 'Кирпич K-4', 'Даунтаун, приглушённый'),
        (FA + r'\facade_brick_soviet_albedo.png', 'Силикатный K-5', 'Неблагополучный'),
        (sk('3c_concrete_panels', 7), 'Панели P-5', 'панельки + PanelTrim'),
        (sk('3d_cinder_blocks', 7), 'Шлакоблок Z-4', 'Стройка, гаражи'),
        (sk('5a_wood_planks_fences', 7), 'Доски D-3', 'Хутор, заборы'),
        (sk('5a_wood_planks_fences', 2), 'Доски D-1', 'пирсы, настилы'),
    ]),
    ('Крыши, металл, кора', [
        (sk('4a_clay_roof_tiles', 7), 'Черепица R-4', 'приглушённая'),
        (sk('4b_slate_shingles', 7), 'Сланец S-3', 'Даунтаун'),
        (RF + r'\roof_slate_wavy_albedo.png', 'Шифер S-4', 'Хутор'),
        (sk('4d_flat_bitumen_roof', 3), 'Плоская T-2', 'плоские крыши'),
        (sk('4c_corrugated_metal', 7), 'Профлист M-3', 'склады, бытовки'),
        (FA + r'\facade_corrugated_metal_albedo.png', 'Ржавый M-4', 'гаражи Неблагополучного'),
        (sk('6a_painted_metal_panels', 7), 'Металл C-3', 'контейнеры, будки'),
        (PR + r'\TX_Bark_Albedo_v01.png', 'Кора O-4', 'сосны; +O-3, берёза O-5'),
    ]),
]
TODO = ('ЕЩЁ СДЕЛАТЬ (нет у нас): скалы Rock_Macro · трим фасадов · трим панелек · разметка и трещины дорог (декали) · стекло башен · '
        'плитка бассейнов · сетка-рабица · ткань маркиз · мазут · мокрый берег и пена · борозды полей · пальмы · люки и знаки')
T, PAD, LW = 150, 10, 0
cols = 8
W = cols * (T + PAD) + PAD
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
f = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 13)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 12)
H = 60 + len(GROUPS) * (T + 86) + 70
im = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(im)
d.text((PAD, 14), 'ВЫБРАННЫЕ ТЕКСТУРЫ КАРТЫ — на одобрение (18.10)', font=F, fill=(30, 40, 46))
y = 52
for gname, items in GROUPS:
    d.text((PAD, y), gname, font=F, fill=(46, 80, 110))
    y += 30
    for i, (path, title, use) in enumerate(items):
        x = PAD + i * (T + PAD)
        if path and os.path.exists(path):
            t = Image.open(path).convert('RGB')
            t = t.crop((0, 0, min(t.width, 512), min(t.height, 512))).resize((T, T))
            im.paste(t, (x, y))
        else:
            d.rectangle((x, y, x + T, y + T), fill=(255, 236, 230), outline=(200, 60, 40), width=3)
            d.text((x + 10, y + T // 2 - 8), 'СДЕЛАТЬ', font=F, fill=(200, 60, 40))
        d.text((x, y + T + 4), title, font=f, fill=(30, 40, 46))
        d.text((x, y + T + 21), use[:24], font=fs, fill=(70, 78, 84))
        if len(use) > 24:
            d.text((x, y + T + 36), use[24:48], font=fs, fill=(70, 78, 84))
    y += T + 56
words, line, lines = TODO.split(' '), '', []
for w_ in words:
    if d.textlength(line + ' ' + w_, font=f) > W - 2 * PAD:
        lines.append(line)
        line = w_
    else:
        line = (line + ' ' + w_).strip()
lines.append(line)
for k, ln in enumerate(lines):
    d.text((PAD, y + k * 18), ln, font=f, fill=(170, 50, 30))
out = os.path.join(HERE, 'SUMMARY_textures_for_approval_v01.jpg')
im.save(out, quality=90)
print(out, im.size)
