"""Картинка Даунтауна для общей карты v84 (TASK-000852): план v30 (без отростков бульвара за кольцом) — та же
обработка, что build_world_v22.py делала для v26 (прозрачен луг вокруг, канал и подписи срезаны, 1 px = 1 ед. карты).
-> v84_assets/downtown_v30_world.png"""
import os
from PIL import Image, ImageDraw

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
DST = os.path.join(MAP, '00_Сборка_общей_карты', 'v84_assets', 'downtown_v30_world.png')
if os.path.exists(DST):
    raise SystemExit('exists')
Image.MAX_IMAGE_PIXELS = None
dt = Image.open(os.path.join(MAP, 'Город', 'Город_Downtown_v30.png')).convert('RGB')
dm = Image.new('L', dt.size, 0)
dp, dmp = dt.load(), dm.load()
for y in range(0, int(1252 * 1.3)):
    for x in range(dt.width):
        r, g, b = dp[x, y]
        if abs(r - 227) + abs(g - 235) + abs(b - 212) > 10:
            dmp[x, y] = 255
for box in ((2050, 0, 3341, 100), (0, 860, 200, 945), (3170, 1000, 3341, 1050), (320, 20, 600, 80)):
    ImageDraw.Draw(dm).rectangle(box, fill=0)
dts = dt.resize((int(dt.width / 1.3), int(dt.height / 1.3)), Image.LANCZOS)
im = dts.convert('RGBA')
im.putalpha(dm.resize(dts.size, Image.LANCZOS))
im.save(DST)
print('ok', im.size, 'v27', Image.open(os.path.join(MAP, '00_Сборка_общей_карты', 'v49_assets', 'downtown_v27_world.png')).size)
