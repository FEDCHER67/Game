"""План Элитного холма v11 (TASK-000840/841, Вадим 20.10.2026: «не нужно полный круг на 360… петля на 180, заезжаем с той
стороны, подъём круче»): из v74_assets/elite_v10_world.png (6 px/м, левый верх = мир x 1260, y 450 до сдвига).
- западные ворота закрыты: подъезд, шлагбаум, будка охраны и пост убраны, забор сплошной;
- ворота-ловушка перенесены на восточную сторону: въезд от внутреннего кольца на восток через забор, тот же шлагбаум
  (красный + жёлто-чёрный), будка охраны внутри, пост снаружи; полукольцо дороги на карте v77 приходит сюда.
Выход: v77_assets/elite_v11_world.png. v10 не меняется."""
import os
from PIL import Image, ImageDraw, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'v74_assets', 'elite_v10_world.png')
OUT = os.path.join(HERE, 'v77_assets', 'elite_v11_world.png')
assert not os.path.exists(OUT)
HILL, PLATEAU, FENCE = (226, 235, 210, 255), (222, 233, 206, 255), (70, 88, 62, 255)
ROAD, ROAD_EDGE, LAMP = (95, 102, 108, 255), (200, 196, 186, 255), (233, 223, 180, 255)
im = Image.open(SRC).convert('RGBA')
booth = im.crop((452, 543, 518, 580))
post = im.crop((358, 620, 399, 660))
barrier = ImageOps.mirror(im.crop((400, 572, 442, 624)))
dr = ImageDraw.Draw(im)
# 1) запад: подъезд и шлагбаум снаружи — луг холма, внутри — плато, забор сплошной
px_ = im.load()                                                        # снаружи — только не-зелёные пиксели (деревья не режем)
for i in range(330, 397):
    for j in range(520, 670):
        r_, g_, b_, a_ = px_[i, j]
        if not (g_ > r_ + 4 and g_ >= b_) or (abs(r_ - g_) < 14 and abs(g_ - b_) < 14) or g_ < 200 and not (g_ > r_ + 25):
            px_[i, j] = HILL
dr.rectangle([398, 538, 634, 628], fill=PLATEAU)
dr.line([(396, 520), (396, 680)], fill=FENCE, width=4)
# 2) восток: дорога от внутреннего кольца через забор наружу (6,4 м = 38 px)
y = 598
dr.rectangle([1012, y - 22, 1322, y + 22], fill=ROAD_EDGE)
dr.rectangle([1012, y - 19, 1322, y + 19], fill=ROAD)
im.alpha_composite(barrier, (1262, 572))
im.alpha_composite(booth, (1150, 543))
im.alpha_composite(post, (1272, 622))
for x in (1090, 1180):
    dr.ellipse([x - 5, y - 40, x + 5, y - 30], fill=LAMP, outline=(110, 104, 90, 255), width=2)
dr.line([(1260, 520), (1260, y - 23)], fill=FENCE, width=4)
dr.line([(1260, y + 23), (1260, 680)], fill=FENCE, width=4)
im.save(OUT)
print('ok', im.size)
