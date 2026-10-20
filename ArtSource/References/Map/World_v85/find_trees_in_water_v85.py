"""Деревья карты, стоящие в воде (море, река, озеро) или на скалах у воды, по готовой картинке (TASK-000854).
Для каждого дерева мастера (круг с обводкой деревьев) берёт 12 точек кольца чуть шире кроны на FINAL png (с учётом сдвига
shift_m); если ≥ 7 из них — вода, дерево попадает в список. Пишет v85_assets/trees_in_water.json (центры в единицах SVG),
build_world_v85.py убирает эти деревья.  Запуск: python find_trees_in_water_v85.py MASTER.svg FINAL.png"""
import json
import math
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from post_shift_v85 import shift_m  # noqa: E402
svg, png = sys.argv[1], sys.argv[2]
s = open(svg, encoding='utf-8').read()
NUM = r'-?\d+(?:\.\d+)?'
TREE = re.compile(r'stroke="(?:#86A274|#6F915E|#3F6343|#5F8452|#4E7A4A|#7E9E62)"')
Image.MAX_IMAGE_PIXELS = None
im = Image.open(png).convert('RGB')
W, H = im.size
px = im.load()


def water(c):
    r, g, b = c
    return b > 185 and b > r + 25 and g > r + 10


st, out = [], []
for q in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', s):
    cl, nm, at, sc = q.groups()
    if nm == 'g':
        if cl:
            st.pop()
        else:
            t = re.search(r'transform="translate\((%s)[ ,]+(%s)\)"' % (NUM, NUM), at)
            b0 = st[-1] if st else (0.0, 0.0, False)
            nb = (b0[0] + (float(t.group(1)) if t else 0), b0[1] + (float(t.group(2)) if t else 0),
                  b0[2] or any(k in at for k in ('rotate', 'matrix', 'scale')))
            if not sc:
                st.append(nb)
        continue
    if cl or nm != 'circle' or not TREE.search(at):
        continue
    ox, oy, rot = st[-1] if st else (0.0, 0.0, False)
    if rot:
        continue
    cx = float(re.search(r'cx="(%s)"' % NUM, at).group(1)) + ox
    cy = float(re.search(r'cy="(%s)"' % NUM, at).group(1)) + oy
    r = float(re.search(r'\sr="(%s)"' % NUM, at).group(1))
    xm, ym = (cx + 350) / 5.0, (3500 - cy) / 5.0
    dx, dy = shift_m(xm, ym)
    X, Y = (xm + dx) * 5, (950 - (ym + dy)) * 5
    n = 0
    for k in range(12):
        a = k * math.pi / 6
        u, v = int(X + (r + 5) * math.cos(a)), int(Y + (r + 5) * math.sin(a))
        if 0 <= u < W and 0 <= v < H and water(px[u, v]):
            n += 1
    if n >= 7:
        out.append([round(cx, 1), round(cy, 1)])
dst = os.path.join(HERE, 'v85_assets', 'trees_in_water.json')
json.dump(out, open(dst, 'w', encoding='utf-8'))
print('trees in water', len(out), '->', dst)
