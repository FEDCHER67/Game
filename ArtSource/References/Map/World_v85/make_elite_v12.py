"""План Элитного холма v12 (TASK-000854, Вадим 20.10.2026: «пересмотри каждый пиксель, убери лишнюю хуйню»): из v11.
В v10 надпись «07 ELITE HILL» плана была закрыта светлой заплаткой-прямоугольником — она резала скалы, горизонтали и дерево.
Здесь участок заплатки возвращён из v09 (скалы, горизонтали, деревья целые), а сама надпись с кружком «07» стёрта и
заполнена цветом окружающего склона (заливка от краёв внутрь — без пятен и прямоугольников). Выход: v85_assets/elite_v12_world.png."""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
V09 = os.path.join(HERE, 'v22_assets', 'elite_v09_world_white.png')
V11 = os.path.join(HERE, 'v77_assets', 'elite_v11_world.png')
OUT = os.path.join(HERE, 'v85_assets', 'elite_v12_world.png')
assert not os.path.exists(OUT)
a = Image.open(V09).convert('RGBA')
b = Image.open(V11).convert('RGBA')
pa, pb = a.load(), b.load()
W, H = a.size
# 1) где v11 отличается от v09 (заплатка v10) — берём v09
for y in range(40, 260):
    for x in range(200, 900):
        ca, cb = pa[x, y], pb[x, y]
        if sum(abs(ca[i] - cb[i]) for i in range(3)) > 2:
            pb[x, y] = ca
# 2) маска надписи и кружка «07» по картинке v09: только в кружке и в рамке букв (скалы выше букв не трогаем)
TXT = (346, 118, 756, 194)
BADGE = (384, 155, 37)
LET = (418, 126, 752, 192)
mask = Image.new('L', (W, H), 0)
pm = mask.load()


def greenish(c):
    r, g, bl = c[:3]
    return g >= r + 3 and g >= bl + 10 and (r + g + bl) / 3 < 229


for y in range(TXT[1], TXT[3]):
    for x in range(TXT[0], TXT[2]):
        c = pa[x, y]
        r, g, bl = c[:3]
        bg = abs(r - 224) < 6 and abs(g - 233) < 6 and abs(bl - 208) < 7
        inb = (x - BADGE[0]) ** 2 + (y - BADGE[1]) ** 2 <= BADGE[2] ** 2
        inl = LET[0] <= x < LET[2] and LET[1] <= y < LET[3]
        tree = g >= r + 10 and r > 120 and (r + g + bl) / 3 < 215 and y > 176   # крона дерева под кружком — не трогаем
        rock = abs(r - g) < 10 and r >= bl - 2 and 90 < (r + g + bl) / 3 < 215 and y < 152   # низ скал над буквами — не трогаем
        if (inb and not tree) or (inl and not (bg or rock)):            # обрывки горизонталей между буквами — тоже (без пятен)
            pm[x, y] = 255
mask = mask.filter(ImageFilter.MaxFilter(3))
pm = mask.load()
# 3) заливка маски от краёв внутрь: цвет = среднее известных соседей-склона (горизонтали в среднее не берём — без полос)
todo = {(x, y) for y in range(TXT[1] - 2, TXT[3] + 2) for x in range(TXT[0] - 2, TXT[2] + 2) if pm[x, y]}
n0 = len(todo)
while todo:
    layer = []
    for (x, y) in todo:
        nb = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and (x + dx, y + dy) not in todo]
        if len(nb) < 2:
            continue
        cs = [pb[q] for q in nb]
        plain = [c for c in cs if not greenish(c) and not (abs(c[0] - c[1]) < 10 and (c[0] + c[1] + c[2]) / 3 < 215)]   # без горизонталей и скал
        cs = plain or cs
        layer.append(((x, y), tuple(sum(c[i] for c in cs) // len(cs) for i in range(3)) + (255,)))
    if not layer:
        break
    for q, c in layer:
        pb[q] = c
        todo.discard(q)
# 4) лёгкое сглаживание только залитого (без полос от послойной заливки)
reg = (TXT[0] - 4, TXT[1] - 4, TXT[2] + 4, TXT[3] + 4)
sm = b.crop(reg).filter(ImageFilter.GaussianBlur(2.2))
mk = mask.crop(reg).filter(ImageFilter.GaussianBlur(1.5))
b.paste(sm, reg[:2], mk)
b.save(OUT)
print('ok', b.size, 'label pixels filled', n0)
