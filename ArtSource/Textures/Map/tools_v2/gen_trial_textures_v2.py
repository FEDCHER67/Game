"""Textures for the STYLE_BIBLE_v2 trial frame (bible 3.3 and 9.1), written straight into the Unity import folder.

    python ArtSource/Textures/Map/tools_v2/gen_trial_textures_v2.py [--out <dir>]

* PT_Paving_v2.png  - one paving tile, 512 x 512 px, white base, seam grid of straight lines only (bible 3.3:
  multiplied by the `paving` swatch, seams 0.02 m at 1.5 m tiles ~ 7 px, delta L* about -5 on `paving`, map mean >= 0.92).
  Material tiling sets the tile size: 1.5 m on the square, 1.0 m on sidewalks.
* Look_SkyGradient_v2.png - 64 x 1024 lat-long gradient for Skybox/Panoramic: zenith #5B9BDB -> 30 deg #8DBBE8 ->
  horizon #D7E5F1 -> below the horizon #DCE3E6 (bible 9.1).
Deterministic: same inputs, same bytes. No noise anywhere.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=str(ROOT / 'Assets/OnlyVolunteers/Art/StyleKit_v2/Textures'))
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)


def lab_to_srgb8(L):
    """Grey with CIELAB lightness L -> sRGB 0..255."""
    fy = (L + 16) / 116
    Y = fy ** 3 if fy ** 3 > 0.008856 else (L / 903.3)
    c = 12.92 * Y if Y <= 0.0031308 else 1.055 * Y ** (1 / 2.4) - 0.055
    return int(round(c * 255))


def srgb_to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055) * 255.0


# ---------------------------------------------------------------- paving tile
N = 512
SEAM_PX = 7                                  # 0.02 m on a 1.5 m tile = 6.8 px (on a 1.0 m sidewalk tile it reads 0.014 m)
# Seam multiplier chosen so that paving #DED2BD (L* 84.6) drops to about L* 79.6 (delta -5) in linear light.
paving_L, seam_L = 84.6, 79.6
ratio = ((seam_L + 16) / 116) ** 3 / ((paving_L + 16) / 116) ** 3
seam = int(round(float(lin_to_srgb(np.array(ratio)))))
img = np.full((N, N), 255, np.uint8)
h = SEAM_PX // 2
img[:h + 1, :] = seam
img[N - h:, :] = seam
img[:, :h + 1] = seam
img[:, N - h:] = seam
Image.fromarray(np.stack([img] * 3, -1), 'RGB').save(out / 'PT_Paving_v2.png', optimize=False)
print('PT_Paving_v2.png seam value', seam, 'mean', round(float(img.mean()) / 255, 4))

# ---------------------------------------------------------------- sky gradient (lat-long, top row = zenith)
W, H = 64, 1024
stops = [(90.0, '#5B9BDB'), (30.0, '#8DBBE8'), (0.0, '#D7E5F1'), (-6.0, '#DCE3E6'), (-90.0, '#DCE3E6')]


def hexrgb(s):
    return np.array([int(s[i:i + 2], 16) for i in (1, 3, 5)], float)


rows = np.zeros((H, 3))
for y in range(H):
    elev = 90.0 - (y + 0.5) / H * 180.0
    for (e0, c0), (e1, c1) in zip(stops, stops[1:]):
        if e1 <= elev <= e0:
            t = (e0 - elev) / (e0 - e1)
            t = t * t * (3 - 2 * t)              # smoothstep between stops: no visible kinks
            a, b = srgb_to_lin(hexrgb(c0)), srgb_to_lin(hexrgb(c1))
            rows[y] = lin_to_srgb(a + (b - a) * t)
            break
sky = np.repeat(rows[:, None, :], W, axis=1).round().astype(np.uint8)
Image.fromarray(sky, 'RGB').save(out / 'Look_SkyGradient_v2.png', optimize=False)
print('Look_SkyGradient_v2.png', W, 'x', H)
