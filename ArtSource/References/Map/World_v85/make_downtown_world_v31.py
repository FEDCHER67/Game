"""Картинка Даунтауна для общей карты v85 (TASK-000854): план v31 (без одиночных домов за кольцом) — та же
обработка, что build_world_v22.py делала для v26 (прозрачен луг вокруг, канал и подписи срезаны, 1 px = 1 ед. карты).
v85: подписи-направления плана («↖ Неблагополучный район», «← Интернациональная стройка», «Элитный холм →», «↓ Городской
пляж ↓») не вырезаются прямоугольниками (прямоугольник у «Элитный холм →» вырезал кусок улицы и тротуара у въезда с
Элиты) — план перерисовывается из SVG без этих подписей. -> v85_assets/downtown_v31_world.png"""
import io
import os
import re
import subprocess

from PIL import Image, ImageDraw

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
DST = os.path.join(MAP, '00_Сборка_общей_карты', 'v85_assets', 'downtown_v31_world.png')
if os.path.exists(DST):
    raise SystemExit('exists')
Image.MAX_IMAGE_PIXELS = None
SVG = os.path.join(MAP, 'Город', 'Город_Downtown_v31.svg')
svg = io.open(SVG, encoding='utf-8').read()
svg, n = re.subn(r'<text[^>]*>(?:↖ Неблагополучный район|← Интернацио-|нальная стройка|Элитный холм →|↓ Городской пляж ↓)</text>', '', svg)
assert n == 5, n
tmp_png = os.path.join(MAP, '00_Сборка_общей_карты', 'v85_assets', '_downtown_v31_nolabels.png')
html = tmp_png[:-4] + '.html'
io.open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0">' + svg + '</body></html>')
subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu', '--hide-scrollbars',
                '--screenshot=' + tmp_png, '--window-size=3341,1898', 'file:///' + html.replace('\\', '/')],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.remove(html)
dt = Image.open(tmp_png).convert('RGB')
os.remove(tmp_png)
dm = Image.new('L', dt.size, 0)
dp, dmp = dt.load(), dm.load()
for y in range(0, int(1252 * 1.3)):
    for x in range(dt.width):
        r, g, b = dp[x, y]
        if abs(r - 227) + abs(g - 235) + abs(b - 212) > 10:
            dmp[x, y] = 255
for box in ((2050, 0, 3341, 100),):                                   # только рамка заголовка плана
    ImageDraw.Draw(dm).rectangle(box, fill=0)
dts = dt.resize((int(dt.width / 1.3), int(dt.height / 1.3)), Image.LANCZOS)
im = dts.convert('RGBA')
im.putalpha(dm.resize(dts.size, Image.LANCZOS))
im.save(DST)
print('ok', im.size, 'labels removed', n)
