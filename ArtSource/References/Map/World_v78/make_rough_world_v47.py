"""Картинка Неблагополучного для общей карты v78 (TASK-000845): план v47 (арки А4 выше, А5 ниже, проходы юг–север перекрыты гаражами) — та же обработка,
что делала build_world_v22.py для v45 (прозрачность вне района, бежевая дорога плана -> земля, без легенды). -> v78_assets/rough_v47_world.png"""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
DST = os.path.join(MAP, '00_Сборка_общей_карты', 'v78_assets', 'rough_v47_world.png')
if os.path.exists(DST):
    raise SystemExit('exists')
S8, CX, CY, OX, OY = 1.08, 1290, 900, 110, 80
M = 0.1238


def T(x, y):
    return (CX + S8 * (x - CX) + OX, CY + S8 * (y - CY) + OY)


DISTRICT = [(36, 40), (772, 40), (772, 18), (1565, 18), (1565, 208), (2559, 208), (2559, 1047), (2445, 1047),
            (2445, 1743), (137, 1743), (137, 1068), (36, 1068)]
rough = Image.open(os.path.join(MAP, 'Неблагополучный район', 'Неблагополучный_район_v47.png')).convert('RGB')
poly = [T(*p) for p in DISTRICT]
inner = Image.new('L', rough.size, 0)
ImageDraw.Draw(inner).polygon(poly, fill=255)
ImageDraw.Draw(inner).line(poly + [poly[0]], fill=0, width=240, joint='curve')
inner = inner.filter(ImageFilter.GaussianBlur(70))
solid = Image.new('L', rough.size, 0)
pm = Image.new('L', rough.size, 0)
ImageDraw.Draw(pm).polygon(poly, fill=255)
sp, rp, pmp = solid.load(), rough.load(), pm.load()
for y in range(rough.height):
    for x in range(rough.width):
        if not pmp[x, y]:
            continue
        r, g, b = rp[x, y]
        if (abs(r - 233) < 10 and abs(g - 216) < 10 and abs(b - 172) < 10) or (abs(r - 176) < 6 and abs(g - 166) < 6 and abs(b - 140) < 6):
            rp[x, y] = (170, 166, 158)
            continue
        ground = (abs(r - 170) < 8 and abs(g - 166) < 8 and abs(b - 158) < 8) or \
                 (166 <= r <= 188 and 156 <= g <= 174 and 112 <= b <= 132) or \
                 (172 <= r <= 188 and 168 <= g <= 184 and 159 <= b <= 175)
        if not ground:
            sp[x, y] = 255
alpha = ImageChops.lighter(inner, solid)
alpha.paste(0, (1735, 0, rough.width, 232))
k = M * 5
rs = rough.resize((int(rough.width * k), int(rough.height * k)), Image.LANCZOS)
im = rs.convert('RGBA')
im.putalpha(alpha.resize(rs.size, Image.LANCZOS))
im.save(DST)
old = Image.open(os.path.join(MAP, '00_Сборка_общей_карты', 'v22_assets', 'rough_v45_world.png'))
print('ok', im.size, 'v45', old.size)
