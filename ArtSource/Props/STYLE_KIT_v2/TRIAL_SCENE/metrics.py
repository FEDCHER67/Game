"""Frame metrics in the bible's terms: L* bands (B1+B2 = L* >= 78), green / warm pixel shares (OKLCh hue), mean L*."""
import sys, json
import numpy as np
from PIL import Image


def srgb_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def metrics(path, crop=None, sky_mask=False):
    im = Image.open(path).convert('RGB')
    if crop:
        im = im.crop(crop)
    a = np.asarray(im, dtype=np.float64)
    r, g, b = srgb_lin(a[..., 0]), srgb_lin(a[..., 1]), srgb_lin(a[..., 2])
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    L = 116 * f - 16
    l_ = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = np.hypot(A, B)
    H = np.degrees(np.arctan2(B, A)) % 360
    mx, mn = a.max(-1), a.min(-1)
    dd = mx - mn + 1e-9
    hsv_h = np.where(mx == a[..., 0], ((a[..., 1] - a[..., 2]) / dd) % 6,
                     np.where(mx == a[..., 1], (a[..., 2] - a[..., 0]) / dd + 2, (a[..., 0] - a[..., 1]) / dd + 4)) * 60
    hsv_s = (mx - mn) / (mx + 1e-9)
    n = L.size
    out = {'B1+B2': float((L >= 78).sum() / n), 'B1': float((L >= 90).sum() / n), 'B3': float(((L >= 64) & (L < 78)).sum() / n),
           'B4+B5': float(((L >= 30) & (L < 64)).sum() / n), 'B6': float((L < 30).sum() / n),
           # definitions calibrated to the critique's numbers (refs 26/30 % green, 36/26 % warm)
           'green': float(((hsv_h >= 70) & (hsv_h < 170) & (hsv_s > 0.2)).sum() / n),
           'warm': float((((H < 100) | (H >= 340)) & (C > 0.015)).sum() / n),
           'meanL': float(L.mean())}
    return out


if __name__ == '__main__':
    res = {}
    for p in sys.argv[1:]:
        m = metrics(p)
        res[p] = m
        print(f"{p.split('/')[-1]:45s} B1+B2 {m['B1+B2']*100:5.1f}%  B3 {m['B3']*100:5.1f}%  B4+B5 {m['B4+B5']*100:5.1f}%  B6 {m['B6']*100:4.1f}%  green {m['green']*100:5.1f}%  warm {m['warm']*100:5.1f}%  L* {m['meanL']:5.1f}")
