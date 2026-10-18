"""Сводный лист текстур v02 (TASK-000818): ЧТО ЕСТЬ (выбранные плитки, «где применяем») и ЧЕГО НЕТ (делает GPT в Work-чате).
Отличия от v01: ряд «Неблагополучный: хрущёвки» (KH1-KH4 + превью фасадов), брёвна; в недостающих — фасады с окнами и стекло
башен; убраны трим панелек (есть KH1) и атлас пальм (есть модели пальм). Второй выход — STYLE_textures_have_v02.jpg
(только «ЕСТЬ», для GPT как образец стиля)."""
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
KH = os.path.join(HERE, 'candidates_rough_soviet_v01')


def sk(d, v):
    return SK + '\\%s\\%s_v%02d_albedo.png' % (d, d, v)


HAVE = [
    ('Земля (слои террейна)', [
        (D + r'\TL_meadow_albedo.png', 'L01 Луг', 'луга, горы'),
        (D + r'\TL_worn_grass_albedo.png', 'L02 Сухая трава', 'Неблагополучный, степь'),
        (sk('1b_dirt_road', 7), 'L03 Грунт', 'грунтовки, тропы'),
        (os.path.join(HERE, 'TL_forest_floor_albedo_v02_brighter.png'), 'L04 Подстилка +10%', 'лес'),
        (D + r'\TL_sand_albedo.png', 'L05 Песок', 'пляж, берега'),
        (sk('1d_gravel', 7), 'L06 Гравий', 'обочины, осыпи'),
        (None, 'L07 Скалы', 'НЕТ → GPT (№1)'),
        (D + r'\TL_park_grass_albedo.png', 'L08 Газон', 'парки, виллы'),
    ]),
    ('Дороги и площади', [
        (os.path.join(AS, '2a_asphalt_v07_A5d12_albedo.png'), 'Асфальт −12%', 'все дороги'),
        (sk('2a_asphalt', 1), 'Старый асфальт', 'Неблагополучный'),
        (os.path.join(C, 'S1_sidewalk_oar_1p5m_albedo.png'), 'Тротуар S1', 'как One-Armed Robber'),
        (os.path.join(C, 'M3_plaza_1m_granite_bands_albedo.png'), 'Площадь M3', 'модерн, гранит'),
        (sk('2c_cobblestone', 7), 'Брусчатка', 'акценты площади'),
        (sk('3c_concrete_panels', 7), 'Бетон', 'плиты, тоннель, порт'),
        (G + r'\ground_curb_concrete_albedo.png', 'Бордюр', 'бордюры'),
        (G + r'\ground_rubber_playground_albedo.png', 'Резина', 'спортплощадки'),
    ]),
    ('Стены', [
        (sk('3b_plaster_stucco', 1), 'Штукатурка W-1', 'Даунтаун, Элит (цвет — в материале)'),
        (sk('3b_plaster_stucco', 7), 'Штукатурка W-5', 'старые дома'),
        (sk('3a_brick', 7), 'Кирпич K-4', 'Даунтаун'),
        (sk('3c_concrete_panels', 7), 'Бетон. панели P-5', 'Трамдуро, КПП, порт'),
        (sk('3d_cinder_blocks', 7), 'Шлакоблок Z-4', 'Стройка, гаражи'),
        (sk('5a_wood_planks_fences', 7), 'Доски D-3', 'Хутор, заборы'),
        (sk('5a_wood_planks_fences', 2), 'Доски D-1', 'пирсы, настилы'),
        (sk('5b_logs', 7), 'Брёвна B-7', 'Хутор, сараи'),
    ]),
    ('Неблагополучный: хрущёвки (свои)', [
        (os.path.join(KH, 'KH1_panel_grey_seams_albedo.png'), 'KH1 Панель', 'все корпуса'),
        (os.path.join(KH, 'KH2_panel_small_tiles_albedo.png'), 'KH2 Плитка', 'часть корпусов'),
        (os.path.join(KH, 'KH3_silicate_brick_white_albedo.png'), 'KH3 Силикат', 'кирпичные, будки'),
        (os.path.join(KH, 'KH4_red_brick_muted_albedo.png'), 'KH4 Красный', 'запасной'),
        ('PREVIEW', '', ''),
    ]),
    ('Крыши, металл, кора', [
        (sk('4a_clay_roof_tiles', 7), 'Черепица R-4', 'Элит, Даунтаун'),
        (sk('4b_slate_shingles', 7), 'Сланец S-3', 'Даунтаун'),
        (RF + r'\roof_slate_wavy_albedo.png', 'Шифер S-4', 'Хутор'),
        (sk('4d_flat_bitumen_roof', 3), 'Плоская T-2', 'плоские крыши'),
        (sk('4c_corrugated_metal', 7), 'Профлист M-3', 'склады, бытовки'),
        (FA + r'\facade_corrugated_metal_albedo.png', 'Ржавый M-4', 'гаражи Неблагоп.'),
        (sk('6a_painted_metal_panels', 7), 'Металл C-3', 'контейнеры, ворота КПП'),
        (PR + r'\TX_Bark_Albedo_v01.png', 'Кора O-4', 'сосны; +O-3, берёза'),
    ]),
]
MISSING = [
    ('1', 'Скалы', 'горы, обрывы, камни у моря'),
    ('2', 'Фасады с окнами', 'Даунтаун, витрины, Хутор, Элит, склады'),
    ('3', 'Стекло башен', 'башни-близнецы, офисы'),
    ('4', 'Карниз и цоколь', 'края крыш, низ домов'),
    ('5', 'Разметка дорог', 'полосы, зебра, стоп, стрелки, P, H'),
    ('6', 'Трещины, заплатки', 'декали асфальта'),
    ('7', 'Плитка бассейна', 'Элит, фонтаны'),
    ('8', 'Сетка-рабица', 'Стройка, граница, площадки'),
    ('9', 'Ткань маркиз', 'зонты, навесы'),
    ('10', 'Мазут', 'порт'),
    ('11', 'Пена прибоя, водопад', 'маски для воды'),
    ('12', 'Поля: пашня, стерня', 'Хутор, Тихая долина'),
    ('13', 'Люки, решётки, знаки', 'улицы'),
]
FOOT = ('Сделаю сам: мокрый песок у воды (наш песок темнее), окна хрущёвок (как на листе KH). Убрал из списка: трим панелек — есть KH1; '
        'атлас пальм — есть модели пальм. Вода моря — доделываю, лист воды пришлю отдельно.')

T, PAD = 150, 10
W = 8 * (T + PAD) + PAD
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
FB = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 30)
f = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 13)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 12)
SHEET_KH = Image.open(os.path.join(HERE, 'SHEET_05b_rough_khrushchyovka.jpg')).convert('RGB')
PREV = [SHEET_KH.crop((24, 312, 758, 680)), SHEET_KH.crop((794, 312, 1528, 680))]   # фасады KH1 и KH3


def wrap(d, text, font, width):
    words, line, lines = text.split(' '), '', []
    for w_ in words:
        if d.textlength((line + ' ' + w_).strip(), font=font) > width:
            lines.append(line)
            line = w_
        else:
            line = (line + ' ' + w_).strip()
    lines.append(line)
    return lines


def draw_have(d, im, y, title_suffix=''):
    for gname, items in HAVE:
        d.text((PAD, y), gname, font=F, fill=(46, 80, 110))
        y += 30
        for i, (path, title, use) in enumerate(items):
            x = PAD + i * (T + PAD)
            if path == 'PREVIEW':
                pw = (W - PAD - x - PAD) // 2
                for k, pv in enumerate(PREV):
                    t = pv.resize((pw, int(pw * pv.height / pv.width)))
                    t = t.crop((0, 0, pw, min(t.height, T)))
                    im.paste(t, (x + k * (pw + PAD), y))
                d.text((x, y + T + 4), 'Как выглядит на доме: KH1 панельная, KH3 кирпичная', font=f, fill=(30, 40, 46))
                break
            if path and os.path.exists(path):
                t = Image.open(path).convert('RGB')
                t = t.crop((0, 0, min(t.width, 512), min(t.height, 512))).resize((T, T))
                im.paste(t, (x, y))
            else:
                d.rectangle((x, y, x + T, y + T), fill=(255, 236, 230), outline=(200, 60, 40), width=3)
                d.text((x + 12, y + T // 2 - 12), 'НЕТ', font=F, fill=(200, 60, 40))
            d.text((x, y + T + 4), title, font=f, fill=(30, 40, 46))
            for k, ln in enumerate(wrap(d, use, fs, T)[:2]):
                d.text((x, y + T + 21 + k * 14), ln, font=fs, fill=(70, 78, 84))
        y += T + 56
    return y


MH = 104
H = 60 + len(HAVE) * (T + 86) + 40 + 2 * (MH + PAD) + 70
im = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(im)
d.text((PAD, 14), 'ТЕКСТУРЫ КАРТЫ v02 (18.10): ЧТО ЕСТЬ и ЧЕГО НЕТ', font=F, fill=(30, 40, 46))
y = draw_have(d, im, 52)
d.text((PAD, y), 'ЧЕГО НЕТ — делает GPT в Work-чате (папка 6)', font=F, fill=(170, 50, 30))
y += 30
for n, (num, name, use) in enumerate(MISSING):
    r_, c_ = divmod(n, 7)
    bw = (W - PAD - 7 * PAD) // 7
    x = PAD + c_ * (bw + PAD)
    yy = y + r_ * (MH + PAD)
    d.rectangle((x, yy, x + bw, yy + MH), fill=(255, 236, 230), outline=(200, 60, 40), width=3)
    d.text((x + 8, yy + 4), num, font=FB, fill=(200, 60, 40))
    for k, ln in enumerate(wrap(d, name, f, bw - 16)[:2]):
        d.text((x + 8, yy + 42 + k * 16), ln, font=f, fill=(120, 30, 20))
    for k, ln in enumerate(wrap(d, use, fs, bw - 16)[:2]):
        d.text((x + 8, yy + 76 + k * 13), ln, font=fs, fill=(90, 60, 50))
y += 2 * (MH + PAD) + 6
for k, ln in enumerate(wrap(d, FOOT, f, W - 2 * PAD)):
    d.text((PAD, y + k * 18), ln, font=f, fill=(46, 80, 110))
out = os.path.join(HERE, 'SUMMARY_textures_have_missing_v02.jpg')
im.save(out, quality=90)
print(out, im.size)

# Образец стиля для GPT: только «ЕСТЬ».
H2 = 60 + len(HAVE) * (T + 86)
im2 = Image.new('RGB', (W, H2), (240, 240, 236))
d2 = ImageDraw.Draw(im2)
d2.text((PAD, 14), 'VOLUNTEERS ONLY — утверждённые текстуры (образец стиля)', font=F, fill=(30, 40, 46))
y2 = draw_have(d2, im2, 52)
im2 = im2.crop((0, 0, W, y2))
out2 = os.path.join(HERE, 'STYLE_textures_have_v02.jpg')
im2.save(out2, quality=90)
print(out2, im2.size)
