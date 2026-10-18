"""Сдвиг v56 (TASK-000775): Даунтаун, пляж, Элитный холм и всё юго-восточнее — на 20 м правее (дальше от холма B и Стройки).
Растровая деформация готовой картинки 5 px/м: dx = 20 * r(x, 690, 770) * (1 - r(y, 470, 560)) м; запад (x < 690) и север
(y > 560: холм B, Порт, Неблагополучный, Трамдуро) не двигаются, между ними — плавная полоса. Без numpy: PIL MESH."""
from PIL import Image

SHIFT_M = 20.0


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def dx_m(x, y):
    return SHIFT_M * r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))


def shift_image(im, top_px=1125, cell=20):
    """im: картинка 5 px/м, мир y = (3500 + top_px - py) / 5. Возвращает сдвинутую (та же величина)."""
    W, H = im.size

    def src(X, Y):
        return X - dx_m(X / 5.0, (3500.0 + top_px - Y) / 5.0) * 5.0, Y

    mesh = []
    for y0 in range(0, H, cell):
        y1 = min(H, y0 + cell)
        for x0 in range(0, W, cell):
            x1 = min(W, x0 + cell)
            ul, ll, lr, ur = src(x0, y0), src(x0, y1), src(x1, y1), src(x1, y0)
            mesh.append(((x0, y0, x1, y1), (ul[0], ul[1], ll[0], ll[1], lr[0], lr[1], ur[0], ur[1])))
    return im.convert('RGB').transform((W, H), Image.MESH, mesh, Image.BILINEAR)
