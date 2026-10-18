"""Сдвиги v57 (TASK-000781), растровая деформация готовой картинки 5 px/м (все координаты скрипта карты — ДО сдвига).
Смещение точки (м):
  юго-восток (Даунтаун, пляж, Элит): dx = +20, dy = -15 (правее и ниже, дальше от холма B), маска m1 = r(x, 690, 770) * (1 - r(y, 470, 560));
  Неблагополучный и север над ним: dy = +10 (выше, дальше от холма B), маска m2 = r(x, 600, 640) * (1 - r(x, 1000, 1040)) * r(y, 600, 640) * (1 - r(y, 878, 904)) (берег не двигается).
Запад, холм B (кроме подножий), Порт и Трамдуро не двигаются. Без numpy: PIL MESH."""
from PIL import Image


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shift_m(x, y):
    m1 = r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))
    m2 = r(x, 600.0, 640.0) * (1.0 - r(x, 1000.0, 1040.0)) * r(y, 600.0, 640.0) * (1.0 - r(y, 878.0, 904.0))   # северный берег и пирс на месте
    return 20.0 * m1, -15.0 * m1 + 10.0 * m2


def shift_image(im, top_px=1125, cell=20):
    W, H = im.size

    def src(X, Y):
        dx, dy = shift_m(X / 5.0, (3500.0 + top_px - Y) / 5.0)
        return X - dx * 5.0, Y + dy * 5.0

    mesh = []
    for y0 in range(0, H, cell):
        y1 = min(H, y0 + cell)
        for x0 in range(0, W, cell):
            x1 = min(W, x0 + cell)
            ul, ll, lr, ur = src(x0, y0), src(x0, y1), src(x1, y1), src(x1, y0)
            mesh.append(((x0, y0, x1, y1), (ul[0], ul[1], ll[0], ll[1], lr[0], lr[1], ur[0], ur[1])))
    return im.convert('RGB').transform((W, H), Image.MESH, mesh, Image.BILINEAR)
