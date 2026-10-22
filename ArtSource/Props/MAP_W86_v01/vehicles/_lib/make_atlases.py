"""Writes the family palette atlases MW86_<Family>_<Variant>.png (512 x 512, sRGB) - system Python 3 + Pillow + numpy.

usage: python make_atlases.py <out_dir> [<out_dir2> ...]
Deterministic: the same palette module always gives byte-identical PNGs.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mw86_palette as P  # noqa: E402


def region_px(reg):
    u0, v0, u1, v1 = P.REGIONS[reg]
    N = P.ATLAS_PX
    x0, x1 = int(round(u0 * N)), int(round(u1 * N))
    y0, y1 = int(round((1 - v1) * N)), int(round((1 - v0) * N))     # image rows from the top
    return x0, y0, x1, y1


def planks(w, h, c0, c1, count, seam_px, axis):
    img = np.zeros((h, w, 3), np.uint8)
    img[:, :] = P.hex_rgb(c0)
    n = w if axis == 'u' else h
    for k in range(1, count + 1):
        p = int(round(k * n / count)) - seam_px // 2
        p = max(0, min(n - seam_px, p))
        if axis == 'u':
            img[:, p:p + seam_px] = P.hex_rgb(c1)
        else:
            img[p:p + seam_px, :] = P.hex_rgb(c1)
    return img


def hazard(w, h, c0, c1, stripe_px):
    yy, xx = np.mgrid[0:h, 0:w]
    band = ((xx + yy) // stripe_px) % 2
    img = np.zeros((h, w, 3), np.uint8)
    img[band == 0] = P.hex_rgb(c0)
    img[band == 1] = P.hex_rgb(c1)
    return img


def field(w, h, seed, blur, cells=(10, 5)):
    rng = np.random.default_rng(seed)
    small = rng.random((cells[1], cells[0])).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC)
    im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, np.float32) / 255.0


def camo(w, h, cols, seed, blur):
    base, c1, c2, c3 = cols
    img = np.zeros((h, w, 3), np.uint8)
    img[:, :] = P.hex_rgb(base)
    f1 = field(w, h, seed, blur, (12, 6))
    f2 = field(w, h, seed + 1, blur, (14, 7))
    f3 = field(w, h, seed + 2, blur * 0.7, (18, 9))
    img[f1 > np.quantile(f1, 0.62)] = P.hex_rgb(c1)
    img[f2 > np.quantile(f2, 0.70)] = P.hex_rgb(c2)
    img[f3 > np.quantile(f3, 0.90)] = P.hex_rgb(c3)
    return img


def build(family, variant):
    N = P.ATLAS_PX
    img = np.zeros((N, N, 3), np.uint8)
    img[:, :] = P.hex_rgb(P.CORE['chalk'])
    for i, name in enumerate(P.cells(family)):
        c, r = i % P.COLS, i // P.COLS
        img[r * P.CELL_PX:(r + 1) * P.CELL_PX, c * P.CELL_PX:(c + 1) * P.CELL_PX] = P.hex_rgb(P.cell_hex(family, name, variant))
    for pname, (reg, kind, colours, prm) in P.FAMILY_PATTERNS.get(family, {}).items():
        x0, y0, x1, y1 = region_px(reg)
        w, h = x1 - x0, y1 - y0
        cols = colours[variant]
        if kind == 'planks':
            tile = planks(w, h, cols[0], cols[1], prm['count'], prm['seam_px'], prm['axis'])
        elif kind == 'hazard':
            tile = hazard(w, h, cols[0], cols[1], prm['stripe_px'])
        elif kind == 'camo':
            tile = camo(w, h, cols, prm['seed'], prm['blur'])
        else:
            raise ValueError(kind)
        img[y0:y1, x0:x1] = tile
    return Image.fromarray(img, 'RGB')


def main(out_dirs):
    written = []
    for fam in P.FAMILY_PAINTS:
        for v in P.VARIANTS:
            im = build(fam, v)
            for d in out_dirs:
                d = Path(d)
                d.mkdir(parents=True, exist_ok=True)
                p = d / f'MW86_{fam}_{v}.png'
                im.save(p, optimize=True)
                written.append(str(p))
    print('\n'.join(written))


if __name__ == '__main__':
    main(sys.argv[1:] or [str(Path(__file__).resolve().parent / 'atlases')])
