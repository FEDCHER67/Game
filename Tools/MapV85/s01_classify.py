"""Step 1: surface classes of the 2D map v85 on the 1 m grid (from the 1 px/m render of the same SVG).

Output: out/classes_v85.png (indexed, row 0 = north like the map), class table in W85Build/Data/<REV>/classes.json.
W86 (2026-10-22): the 1 px picture frame (rows / columns 0 and last) is replaced by the neighbouring row / column (it was meadow /
asphalt -> a 1 m land lip round the sea and a 12 m wall on the north edge, RELIEF_SCAN §7 E); the title box (top-left, white) is filled
with the classes around it (nearest outside cell); the Downtown v37 land interface (common.downtown_v37_land, written by
s04_downtown) is applied when it exists.
Classes are only used where the generator has no vector data (master SVG of Vadim is not in the repo):
sea / inland water / sand / mountains / rocks / steppe / tree canopy / dirt tracks / Rough dry ground.
"""
import os

import numpy as np
from PIL import Image

from common import MAP_PREVIEW, WORK, W, H, save_json, apply_land_override, downtown_v37_land

TITLE_BOX = (77, 901, 432, 944)                                         # world x0, y0, x1, y1 of the white title box of the picture

CLASSES = ['meadow', 'sea', 'water', 'sand', 'asphalt', 'mountain', 'rock', 'steppe', 'tree', 'dirt', 'dry_ground', 'object', 'hill_tint', 'swamp']
PALETTE = [(223, 234, 206), (171, 211, 225), (110, 170, 220), (247, 242, 224), (95, 102, 108), (205, 206, 196), (150, 152, 145),
           (217, 212, 174), (79, 125, 80), (229, 210, 164), (170, 166, 158), (200, 90, 90), (172, 193, 148), (60, 90, 70)]


def flood_from_border(m):
    """Large connected blue areas = sea (lakes/rivers are far smaller)."""
    from scipy import ndimage
    lab, n = ndimage.label(m)
    size = ndimage.sum(m, lab, range(1, n + 1))
    big = [i + 1 for i, s_ in enumerate(size) if s_ > 15000]                 # open sea (frame/legend cut the border)
    return np.isin(lab, big)


def classify():
    from scipy import ndimage
    im = np.asarray(Image.open(MAP_PREVIEW).convert('RGB')).astype(np.int16)
    assert im.shape[:2] == (H, W), im.shape
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(-1), im.min(-1)
    sat = mx - mn
    cls = np.zeros((H, W), np.uint8)
    blue = (B > R + 12) & (B >= G) & (B > 150)
    sea = flood_from_border(ndimage.binary_opening(blue, iterations=1)) & blue
    cls[blue] = 2
    cls[sea] = 1
    cls[(R > 240) & (G > 234) & (B > 212) & (B < 232) & (R - B > 14)] = 3                          # white sand #F7F2E0
    cls[(mx < 125) & (sat < 22)] = 4                                                               # asphalt #5F666C
    grey = (np.abs(R - G) <= 5) & (B < G - 3) & (B > G - 18) & (R > 165) & (R < 242)
    cls[grey] = 5                                                                                  # faceted mountains (#B3B6A7..#EDEDE4)
    cls[(np.abs(R - G) <= 8) & (np.abs(G - B) <= 8) & (R > 140) & (R < 205) & ~grey] = 6           # grey rocks / cliffs
    cls[(R > 205) & (R < 225) & (G > 200) & (G < 220) & (B > 160) & (B < 185) & (R >= G)] = 7      # steppe #D9D4AE
    cls[(G > R + 10) & (G > B + 10) & (mx < 175)] = 8                                              # tree crowns (dark greens)
    cls[(R > 215) & (G > 195) & (B > 150) & (B < 185) & (R - B > 40) & (cls == 0)] = 9             # dirt / village street #E5D2A4
    cls[(np.abs(R - 170) < 14) & (np.abs(G - 166) < 14) & (np.abs(B - 158) < 14)] = 10              # Rough dry ground #AAA69E
    cls[(G > R + 8) & (G > B + 15) & (mx >= 175) & (mx < 205)] = 12                                # hill contour fills
    cls[(np.abs(R - 125) < 14) & (np.abs(G - 158) < 14) & (np.abs(B - 131) < 14)] = 13             # swamp #7D9E83
    cls[(sat > 70) & (cls == 0)] = 11                                                              # roofs, props, labels
    cls = cls[::-1].copy()                                                                         # row j = world y
    return fix_frame(cls)


def fix_frame(cls):
    """picture frame -> neighbour row / column; title box -> nearest class outside the box."""
    from scipy import ndimage
    cls[H - 1] = cls[H - 2]
    cls[0] = cls[1]
    cls[:, 0] = cls[:, 1]
    cls[:, W - 1] = cls[:, W - 2]
    x0, y0, x1, y1 = TITLE_BOX
    box = np.zeros(cls.shape, bool)
    box[y0:y1, x0:x1] = True
    _, (iy, ix) = ndimage.distance_transform_edt(box, return_indices=True)
    cls[box] = cls[iy[box], ix[box]]
    # NW corner: the picture has a 62 x 90 m sea rectangle there (straight 5 m cliffs, RELIEF_SCAN #8 / #17) -> a curved shore
    yy, xx = np.mgrid[0:H, 0:W]
    corner = (xx < 62) & (yy > 860) & (cls == 1)
    shore_x = 62.0 - 62.0 * np.clip((yy - 868.0) / 80.0, 0, 1) ** 0.7
    cls[corner & (xx >= shore_x)] = 7
    return cls


def main():
    cls = apply_land_override(classify())
    os.makedirs(WORK, exist_ok=True)
    np.save(os.path.join(WORK, 'classes_v85.npy'), cls)
    img = Image.fromarray(cls[::-1], 'P')
    img.putpalette([c for p in PALETTE for c in p] + [0] * (768 - 3 * len(PALETTE)))
    img.save(os.path.join(WORK, 'classes_v85.png'))
    counts = {n: int((cls == i).sum()) for i, n in enumerate(CLASSES)}
    dt = downtown_v37_land()
    save_json('classes.json', {'grid_m': 1.0, 'size': [W, H], 'classes': CLASSES, 'palette': PALETTE, 'pixel_counts': counts,
                               'frame_fixed': True, 'title_box_filled': list(TITLE_BOX),
                               'downtown_v37_land': dt['path'] if dt else None})
    print(counts)


if __name__ == '__main__':
    main()
