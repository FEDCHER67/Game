"""Общая карта v86 (TASK-000907, Вадим 22.10.2026: «поставь последнюю версию Даунтауна, которую мы собирали недавно»):
карта v85 (VOLUNTEERS_MAP_FINAL_v85.png) + Даунтаун план v37.
- Город v37 вырос на 52 м вверх и 54 м вниз и отодвинут от холма на 20 м: старые объекты плана (площадь, базы) на карте ниже
  на 360 ед. (72 м); новый верх города на 100 ед. ниже старого.
- Пляж и море под городом сдвинуты вниз на 630 ед. (126 м) без изменений (пляж тот же); к Тихой долине и к Элитному холму
  сдвиг плавно сходит на нет, скалы долины и марина Элиты на месте; холст карты ниже на 630 ед. (море).
- Старый город под новым убран (газон), дороги с холма продлены вниз до новой верхней улицы N0, въезды со Стройки и с Элиты
  продлены до W1/E1.
Растровая сборка по FINAL v85 (1 px = 1 ед. карты); план: x карты = x плана + 3969,5, y = y плана + 2749,5 (было + 2389,5)."""
import io
import os
import re
import subprocess

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
SRC = r'C:\Users\chern_0eqkb03\Desktop\GAME\ArtSource\References\Map\World_v85\VOLUNTEERS_MAP_FINAL_v85.png'
OUT = os.path.join(MAP, '00_Сборка_общей_карты', 'VOLUNTEERS_MAP_FINAL_v86.png')
OUTP = os.path.join(MAP, '00_Сборка_общей_карты', 'VOLUNTEERS_MAP_PREVIEW_v86.png')
for p in (OUT, OUTP):
    if os.path.exists(p):
        raise SystemExit('exists ' + p)

DX, DY_OLD, DY = 3969.5, 2389.5, 2749.5
XMIN, YMIN = -110, -330
SHIFT = 630
CUT = 3655                                   # край тротуара старой нижней улицы S1 (план 1265)

base = Image.open(SRC).convert('RGB')
W0, H0 = base.size
sea = base.getpixel((5200, H0 - 40))
out = Image.new('RGB', (W0, H0 + SHIFT), sea)
out.paste(base, (0, 0))


def shift_of(x):
    if 3850 <= x <= 6500:
        return SHIFT
    if 3450 < x < 3850:
        return int(SHIFT * (x - 3450) / 400.0)
    if 6500 < x < 7150:                       # до легенды и масштаба карты (x >= 7200) не доходит
        return int(SHIFT * (7150 - x) / 650.0)
    return 0


LAWN = (224, 234, 207)
SAND = (247, 242, 224)


def first_sand(x):
    for y in range(3300, 4200):
        c = base.getpixel((x, y))
        if abs(c[0] - SAND[0]) + abs(c[1] - SAND[1]) + abs(c[2] - SAND[2]) < 14:
            return y
    return 4200


def cut_of(x):
    """Срез над пляжем: в городе — край тротуара S1; по краям — над пальмами пляжа (весь пляж уходит вниз целиком)."""
    if 3929 <= x <= 6349:
        return CUT
    return min(CUT, first_sand(x) - 46)


# 1) пляж и море ниже: по колонкам, зазор заполняется растянутой полосой над срезом
for x in range(W0):
    s = shift_of(x)
    if s <= 0:
        continue
    c = cut_of(x)
    out.paste(base.crop((x, c, x + 1, H0)), (x, c + s))
    out.paste(Image.new('RGB', (1, s), LAWN), (x, c))

# 2) старый город убрать: газон цвета луга над городом
d = ImageDraw.Draw(out)
d.rectangle((4010, 2385, 6268, CUT + 5), fill=LAWN)                 # тело старого города
d.rectangle((3929, 3088, 4016, CUT + 5), fill=LAWN)                 # старая W2 выше новой
d.rectangle((6262, 3088, 6349, CUT + 5), fill=LAWN)                 # старая E2 выше новой

# 3) дороги с холма: концы над старым верхом города -> вниз до новой улицы N0
ASPH = (0x5F, 0x66, 0x6C)


def near(c, t, tol=16):
    return abs(c[0] - t[0]) + abs(c[1] - t[1]) + abs(c[2] - t[2]) < tol


def runs_row(y, x0, x1):
    res, start = [], None
    for x in range(x0, x1):
        a = near(base.getpixel((x, y)), ASPH)
        if a and start is None:
            start = x
        if not a and start is not None:
            if x - start > 20:
                res.append((start, x - 1))
            start = None
    return res


def n0_y(plan_x):
    if plan_x < 445:
        return -150
    if plan_x < 1550:
        return -190
    return -110


ends = runs_row(2378, 3900, 6400)
print('road ends above old top', ends)
CURB = base.getpixel((5000, 2394)) if False else (0xDE, 0xDB, 0xD2)
for a, b in ends:
    xc = (a + b) / 2.0
    w = b - a + 1
    y1 = n0_y(xc - DX) + DY
    d.rectangle((a - 5, 2370, b + 5, y1), fill=CURB)
    d.rectangle((a, 2370, b, y1), fill=ASPH)

# 4) въезды со Стройки (запад, асфальт) и с Элиты (восток, камень) на старом уровне бульвара — дотянуть до W1 / E1
d.rectangle((3878, 3127, 4016, 3175), fill=(211, 210, 195))
d.rectangle((3878, 3133, 4016, 3163), fill=ASPH)
d.rectangle((6262, 3120, 6362, 3150), fill=(140, 130, 113))
d.rectangle((6262, 3125, 6362, 3150), fill=(180, 168, 144))

# 5) город v37 без подписей и пляжа, луг прозрачный, 1 px = 1 ед.
svg = io.open(os.path.join(MAP, 'Город', 'Город_Downtown_v37.svg'), encoding='utf-8').read()
svg = re.sub(r'<g id="title">.*?</g>', '', svg, flags=re.S)
svg = re.sub(r'<image [^>]*/>', '', svg)
tmp = os.path.join(MAP, '00_Сборка_общей_карты', '_dt_v37_world.png')
html = tmp[:-4] + '.html'
io.open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0">' + svg + '</body></html>')
PX = 1.3
H_PLAN = 1535 + 795
subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu', '--hide-scrollbars',
                '--screenshot=' + tmp, '--window-size=%d,%d' % (int(2570 * PX), int((H_PLAN - YMIN) * PX)), 'file:///' + html.replace('\\', '/')],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.remove(html)
dt = Image.open(tmp).convert('RGB')
os.remove(tmp)
ycut = int((1535 - YMIN) * PX)                                  # только город: до края тротуара набережной S0
dt = dt.crop((0, 0, dt.width, ycut))
mask = Image.new('L', dt.size, 0)
dp, mp = dt.load(), mask.load()
for y in range(dt.height):
    for x in range(dt.width):
        r, g, b = dp[x, y]
        if abs(r - 227) + abs(g - 235) + abs(b - 212) > 10 and abs(r - 255) + abs(g - 255) + abs(b - 255) > 6:
            mp[x, y] = 255
size = (int(dt.width / PX), int(dt.height / PX))
dts = dt.resize(size, Image.LANCZOS).convert('RGBA')
dts.putalpha(mask.resize(size, Image.LANCZOS))
# деревья плана за городом не нужны на карте (на карте свои)
out.paste(dts, (int(XMIN + DX), int(YMIN + DY)), dts)
out.save(OUT)
out.resize((out.width // 5, out.height // 5), Image.LANCZOS).save(OUTP)
print('ok', out.size, OUT)
